"""Background HTTP server that exposes real ROS2 graph data via ros2 CLI.

Endpoint:  GET http://127.0.0.1:9091/api/ros2/graph
Response:  {"ok": bool, "nodes": [...], "edges": [...], "meta": {...}, "error": str|null}

Runs two daemon threads:
  - ros2-graph-refresh  : rebuilds the graph every REFRESH_S seconds
  - ros2-graph-server   : HTTPServer that returns the cached result instantly
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

PORT = 9091
REFRESH_S = 3.0
_SUBPROCESS_TIMEOUT = 6      # seconds per ros2 CLI call
_MAX_WORKERS = 8             # parallel ros2 node info calls

_ROS2: Optional[str] = shutil.which("ros2")

# Topics that clutter the graph without adding insight.
_SKIP_TOPICS = {"/rosout", "/parameter_events", "/rosout_agg"}
_SKIP_PREFIXES = ("/_",)

# Shared cache — written by refresh thread, read by HTTP handler.
_lock = threading.Lock()
_cached: Optional[Dict[str, Any]] = None


# ── CLI helpers ───────────────────────────────────────────────────────────────

def _run(args: List[str]) -> str:
    """Run `ros2 <args>`. Returns stdout, or '' on error/timeout."""
    if not _ROS2:
        return ""
    try:
        r = subprocess.run(
            [_ROS2, *args],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
        return r.stdout
    except Exception:
        return ""


def _skip_topic(name: str) -> bool:
    return name in _SKIP_TOPICS or any(name.startswith(p) for p in _SKIP_PREFIXES)


def _node_info(node_name: str):
    """Parse `ros2 node info <node>`. Returns (name, pub_topics, sub_topics)."""
    pubs: List[str] = []
    subs: List[str] = []
    section = None
    for line in _run(["node", "info", node_name]).splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "Publishers:":
            section = "pub"
        elif s == "Subscribers:":
            section = "sub"
        elif s in ("Service Servers:", "Service Clients:",
                   "Action Servers:", "Action Clients:"):
            section = None
        elif section and s.startswith("/"):
            topic = s.split(":")[0].strip()
            if not _skip_topic(topic):
                (pubs if section == "pub" else subs).append(topic)
    return node_name, pubs, subs


# ── Graph builder ─────────────────────────────────────────────────────────────

def _build_graph() -> Dict[str, Any]:
    if not _ROS2:
        return {
            "ok": False,
            "error": "ros2 not found in PATH — source /opt/ros/jazzy/setup.bash",
            "nodes": [], "edges": [], "meta": _meta(),
        }

    # 1. Node list
    node_names = [
        n.strip()
        for n in _run(["node", "list"]).splitlines()
        if n.strip() and not n.strip().startswith("WARNING")
    ]

    # 2. Topic list with types
    topic_types: Dict[str, str] = {}   # name → msg_type
    for line in _run(["topic", "list", "-t"]).splitlines():
        line = line.strip()
        if not line or line.startswith("WARNING"):
            continue
        if " [" in line:
            name, rest = line.split(" [", 1)
            name = name.strip()
            if not _skip_topic(name):
                topic_types[name] = rest.rstrip("]")
        elif line.startswith("/") and not _skip_topic(line):
            topic_types[line] = ""

    # 3. Per-node pub/sub — parallel
    edges: List[Dict[str, str]] = []
    extra_topics: Dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_node_info, n): n for n in node_names}
        for fut in as_completed(futures):
            name, pubs, subs = fut.result()
            nid = "node_" + name.replace("/", "_")
            for t in pubs:
                tid = "topic_" + t.replace("/", "_")
                edges.append({"s": nid, "t": tid, "k": "pub"})
                if t not in topic_types:
                    extra_topics[t] = ""
            for t in subs:
                tid = "topic_" + t.replace("/", "_")
                edges.append({"s": tid, "t": nid, "k": "sub"})
                if t not in topic_types:
                    extra_topics[t] = ""

    topic_types.update(extra_topics)

    node_entities = [
        {"id": "node_" + n.replace("/", "_"), "label": n, "type": "rosnode"}
        for n in node_names
    ]
    topic_entities = [
        {
            "id": "topic_" + t.replace("/", "_"),
            "label": t,
            "type": "rostopic",
            "msgType": mt,
        }
        for t, mt in topic_types.items()
    ]

    return {
        "ok": True,
        "error": None,
        "nodes": node_entities + topic_entities,
        "edges": edges,
        "meta": _meta(),
    }


def _meta() -> Dict[str, str]:
    return {
        "ros_domain_id": os.environ.get("ROS_DOMAIN_ID", "0"),
        "ros_distro":    os.environ.get("ROS_DISTRO", "—"),
        "hostname":      os.environ.get("HOSTNAME", "localhost"),
        "ros2_available": str(bool(_ROS2)),
    }


# ── HTTP handler ──────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in ("/api/ros2/graph",):
            self.send_response(404)
            self.end_headers()
            return
        with _lock:
            payload = _cached
        if payload is None:
            payload = {"ok": False, "error": "warming up…", "nodes": [], "edges": [], "meta": _meta()}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_: Any) -> None:
        pass  # suppress access logs


# ── Background threads ────────────────────────────────────────────────────────

def _refresh_loop() -> None:
    global _cached
    while True:
        try:
            result = _build_graph()
        except Exception as exc:
            result = {"ok": False, "error": str(exc), "nodes": [], "edges": [], "meta": _meta()}
        with _lock:
            _cached = result
        time.sleep(REFRESH_S)


def start(port: int = PORT) -> int:
    """Start server + refresh loop in daemon threads. Returns the port in use."""
    threading.Thread(target=_refresh_loop, daemon=True, name="ros2-graph-refresh").start()
    server = HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True, name="ros2-graph-server").start()
    return port
