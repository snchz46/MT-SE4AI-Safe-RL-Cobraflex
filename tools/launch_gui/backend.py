"""Backends: MockBackend (offline previews) and RosBackend (real ros2 launch)."""

from __future__ import annotations

import os
import random
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List

from PySide6.QtCore import QProcess, QTimer

from .constants import (
    FORCE_KILL_TIMEOUT_MS,
    LOGS_MAX_PER_LAUNCH,
    MOCK_LOG_TICK_MS,
    PROCESS_START_TIMEOUT_MS,
)
from .discovery import discover_launches
from .meta import LAUNCH_META
from .model import Launch, LogEntry, args_to_overrides, instantiate_args


LOG_TEMPLATES = [
    ("INFO", "cage_ros_node", "rule C-01 lane_boundary OK"),
    ("INFO", "cage_ros_node", "rule C-04 heading_window OK"),
    ("INFO", "lane_perception", "frame OK — 2 lane candidates"),
    ("INFO", "pd_baseline", "steer = {:+.3f} rad, throttle = {:.2f}"),
    ("INFO", "cage_logger", "wrote 32 rows to cage_log.csv"),
    ("WARN", "lane_perception", "frame 312 — low contrast, conf 0.61"),
]

INITIAL_MOCK_LOGS = [
    "[INFO] [cage_ros_node]: Loaded cage v0.5.1",
    "[INFO] [lane_perception]: subscribed to /camera/image_raw",
    "[INFO] [pd_baseline]: PD controller v0.8.0 ready",
    "[INFO] [cage_logger]: writing CSV to experiments/sim/runs/ros_run_2026-05-24/cage_log.csv",
    "[INFO] [cage_ros_node]: rule C-01 lane_boundary OK",
]

FAILED_MOCK_LOGS = [
    "[INFO] [cobraflex_driver]: opening serial port /dev/ttyACM1 @ 115200",
    "[ERROR] [cobraflex_driver]: failed to open /dev/ttyACM1: [Errno 2] No such file or directory",
    "[ERROR] [cobraflex_driver]: assertion failed: serial port required for bringup",
]


def _make_mock_launches() -> List[Launch]:
    """Hardcoded mirror of the real project's launches for offline previews."""
    specs: List[dict] = [
        {"pkg": "safety_cage", "name": "lane_following",
         "state": "running", "pid": 12345, "uptime": 151, "logs": INITIAL_MOCK_LOGS},
        {"pkg": "cobraflex_rl", "name": "train_lane"},
        {"pkg": "cobraflex", "name": "gazebo"},
        {"pkg": "cobraflex", "name": "gazebo_mesh"},
        {"pkg": "cobraflex", "name": "lane_keeper_gazebo"},
        {"pkg": "cobraflex", "name": "mapping"},
        {"pkg": "cobraflex", "name": "navigation"},
        {"pkg": "cobraflex", "name": "description"},
        {"pkg": "cobraflex", "name": "rsp"},
        {"pkg": "cobraflex", "name": "cobraflex_bringup",
         "state": "failed", "logs": FAILED_MOCK_LOGS, "exit_code": 134},
        {"pkg": "cobraflex", "name": "cobraflex_driver"},
        {"pkg": "cobraflex", "name": "cobraflex_sensors"},
        {"pkg": "cobraflex", "name": "cobraflex_automatic"},
        {"pkg": "cobraflex", "name": "cobraflex_lane_keeper"},
        {"pkg": "cobraflex", "name": "cobraflex_mapping"},
    ]
    out: List[Launch] = []
    for s in specs:
        pkg, name = s["pkg"], s["name"]
        key = f"{pkg}/{name}"
        meta = LAUNCH_META.get(key, {})
        logs = [LogEntry.parse(l) for l in s.get("logs", [])]
        last_error = next((e.raw for e in reversed(logs) if e.level == "ERROR"), None)
        out.append(Launch(
            id=f"{pkg}__{name}", pkg=pkg, name=name,
            desc=meta.get("description", "(no description)"),
            tags=list(meta.get("tags", [])),
            phase=meta.get("phase", ""),
            starred=bool(meta.get("starred", False)),
            state=s.get("state", "stopped"),
            pid=s.get("pid"), uptime=s.get("uptime", 0),
            exit_code=s.get("exit_code"), last_error=last_error,
            logs=logs,
            args=instantiate_args(meta.get("args", [])),
            presets=list(meta.get("presets", [])),
        ))
    return out


# ─── Abstract base ──────────────────────────────────────────────────────────

class Backend:
    """Common interface. Subclasses populate `launches` in `setup()`.

    Two callbacks are wired by the UI:
        on_state_changed(launch)        — state / pid / uptime / exit_code changed
        on_log_line(launch, entry)      — a single log line arrived
    """

    mode_label: str = ""

    def __init__(self) -> None:
        self.launches: List[Launch] = []
        self.on_state_changed: Callable[[Launch], None] = lambda _l: None
        self.on_log_line: Callable[[Launch, LogEntry], None] = lambda _l, _e: None

    def setup(self) -> None: ...
    def run(self, launch: Launch) -> None: ...
    def stop(self, launch: Launch) -> None: ...
    def shutdown(self) -> None: ...


# ─── MockBackend ────────────────────────────────────────────────────────────

class MockBackend(Backend):
    mode_label = "MOCK"

    def __init__(self) -> None:
        super().__init__()
        self._timers: Dict[str, QTimer] = {}

    def setup(self) -> None:
        self.launches = _make_mock_launches()
        for l in self.launches:
            if l.state == "running":
                self._start_log_timer(l)

    def run(self, launch: Launch) -> None:
        launch.state = "running"
        launch.pid = random.randint(10000, 99999)
        launch.uptime = 0
        launch.exit_code = None
        launch.last_error = None
        launch._stopping = False
        entry = LogEntry.parse(f"[INFO] [demo]: started {launch.pkg}/{launch.name} (PID {launch.pid})")
        launch.logs.append(entry)
        self.on_state_changed(launch)
        self._start_log_timer(launch)

    def stop(self, launch: Launch) -> None:
        launch._stopping = True
        entry = LogEntry.parse(f"[INFO] [demo]: stopped {launch.pkg}/{launch.name}")
        launch.logs.append(entry)
        launch.state = "stopped"
        launch.pid = None
        launch.uptime = 0
        if launch.id in self._timers:
            self._timers.pop(launch.id).stop()
        self.on_state_changed(launch)

    def shutdown(self) -> None:
        for t in self._timers.values():
            t.stop()
        self._timers.clear()

    def _start_log_timer(self, launch: Launch) -> None:
        t = QTimer()
        t.timeout.connect(lambda: self._tick_log(launch))
        t.start(MOCK_LOG_TICK_MS)
        self._timers[launch.id] = t

    def _tick_log(self, launch: Launch) -> None:
        lvl, node, msg = random.choice(LOG_TEMPLATES)
        if "{" in msg:
            msg = msg.format(random.uniform(-0.1, 0.1), random.uniform(0.2, 0.5))
        entry = LogEntry(time=time.time(), level=lvl, node=node, msg=msg,
                         raw=f"[{lvl}] [{node}]: {msg}")
        launch.logs.append(entry)
        if len(launch.logs) > LOGS_MAX_PER_LAUNCH:
            launch.logs.pop(0)
        self.on_log_line(launch, entry)


# ─── RosBackend ─────────────────────────────────────────────────────────────

class RosBackend(Backend):
    """Wraps `ros2 launch` via QProcess. Linux-only (os.setsid / killpg)."""

    def __init__(self, workspace: Path) -> None:
        super().__init__()
        self.workspace = workspace

    def setup(self) -> None:
        self.launches = discover_launches(self.workspace)

    def run(self, launch: Launch) -> None:
        if launch._process is not None and launch._process.state() != QProcess.NotRunning:
            return
        if launch.file_path is None:
            return
        launch.exit_code = None
        launch.last_error = None
        launch._stopping = False

        proc = QProcess()
        proc.setProgram("ros2")
        proc.setArguments(["launch", launch.pkg, launch.file_path.name,
                           *args_to_overrides(launch.args)])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        # Crucial on Linux: own process group so killpg(SIGINT) reaps the whole
        # ros2 launch + Gazebo + nodes tree on stop.
        if hasattr(proc, "setChildProcessModifier") and hasattr(os, "setsid"):
            proc.setChildProcessModifier(os.setsid)

        proc.readyReadStandardOutput.connect(lambda l=launch, p=proc: self._on_output(l, p))
        proc.finished.connect(lambda code, status, l=launch: self._on_finished(l, code))
        proc.errorOccurred.connect(lambda err, l=launch: self._on_error(l, err))
        proc.start()
        if not proc.waitForStarted(PROCESS_START_TIMEOUT_MS):
            entry = LogEntry.parse(f"[ERROR] [launch_gui]: failed to start — {proc.errorString()}")
            launch.logs.append(entry)
            self.on_log_line(launch, entry)
            return

        launch._process = proc
        launch.state = "running"
        launch.pid = int(proc.processId())
        launch.uptime = 0
        entry = LogEntry.parse(
            f"[INFO] [launch_gui]: ros2 launch {launch.pkg} {launch.file_path.name} (PID {launch.pid})"
        )
        launch.logs.append(entry)
        self.on_log_line(launch, entry)
        self.on_state_changed(launch)

    def stop(self, launch: Launch) -> None:
        proc = launch._process
        if proc is None or proc.state() == QProcess.NotRunning:
            return
        launch._stopping = True
        pid = launch.pid
        if pid and hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                os.killpg(os.getpgid(pid), signal.SIGINT)
                e = LogEntry.parse(f"[INFO] [launch_gui]: SIGINT -> pgid({pid})")
                launch.logs.append(e); self.on_log_line(launch, e)
            except OSError as err:
                e = LogEntry.parse(f"[WARN] [launch_gui]: killpg failed ({err}); terminating QProcess")
                launch.logs.append(e); self.on_log_line(launch, e)
                proc.terminate()
        else:
            proc.terminate()
        QTimer.singleShot(FORCE_KILL_TIMEOUT_MS, lambda l=launch: self._force_kill_if_alive(l))

    def shutdown(self) -> None:
        for launch in list(self.launches):
            if launch.state == "running":
                self.stop(launch)
        for launch in list(self.launches):
            proc = launch._process
            if proc is not None and proc.state() != QProcess.NotRunning:
                if not proc.waitForFinished(2000):
                    proc.kill()
                    proc.waitForFinished(1000)

    def _force_kill_if_alive(self, launch: Launch) -> None:
        proc = launch._process
        if proc is None or proc.state() == QProcess.NotRunning:
            return
        pid = launch.pid
        if pid and hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                e = LogEntry.parse(f"[WARN] [launch_gui]: SIGTERM -> pgid({pid})")
                launch.logs.append(e); self.on_log_line(launch, e)
            except OSError:
                pass
        proc.kill()

    def _on_output(self, launch: Launch, proc: QProcess) -> None:
        data = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if not line:
                continue
            entry = LogEntry.parse(line)
            launch.logs.append(entry)
            if len(launch.logs) > LOGS_MAX_PER_LAUNCH:
                launch.logs.pop(0)
            if entry.level == "ERROR":
                launch.last_error = line
            self.on_log_line(launch, entry)

    def _on_finished(self, launch: Launch, code: int) -> None:
        e = LogEntry.parse(f"[INFO] [launch_gui]: exited (code={code})")
        launch.logs.append(e); self.on_log_line(launch, e)
        # User-initiated stop or clean exit → stopped. Non-zero crash → failed.
        if launch._stopping or code == 0:
            launch.state = "stopped"
            launch.exit_code = None
        else:
            launch.state = "failed"
            launch.exit_code = code
        launch.pid = None
        launch.uptime = 0
        launch._process = None
        launch._stopping = False
        self.on_state_changed(launch)

    def _on_error(self, launch: Launch, err) -> None:
        e = LogEntry.parse(f"[ERROR] [launch_gui]: QProcess error: {err}")
        launch.logs.append(e); self.on_log_line(launch, e)


def detect_backend(force_mock: bool, workspace: Path) -> Backend:
    """Pick MockBackend or RosBackend based on flag + ros2 availability."""
    if force_mock or shutil.which("ros2") is None:
        b = MockBackend()
        if force_mock:
            b.mode_label = "MOCK"
        else:
            print("[launch_gui] ros2 not in PATH — falling back to mock backend.",
                  file=sys.stderr)
            b.mode_label = "MOCK (no ros2)"
        return b
    return RosBackend(workspace)
