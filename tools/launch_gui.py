"""CobraFlex Launch Manager — GUI to start/stop ROS2 launches without a terminal.

Two backends:
    MockBackend  — fake data, runs on any OS. Used for visual previews.
    RosBackend   — discovers src/*/launch/*.launch.{py,xml} and runs them via
                   QProcess. Linux only (Windows lacks os.setsid / killpg).

Mode is auto-detected: if `ros2` is in PATH, RosBackend is used; otherwise
the GUI falls back to MockBackend. Pass --mock to force mock.

    pip install PySide6
    python tools/launch_gui.py          # auto: real on Linux/ROS2, mock on Windows
    python tools/launch_gui.py --mock   # force mock for visual preview
"""

from __future__ import annotations

import argparse
import ast
import os
import random
import re
import shutil
import signal
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QEvent, QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineWidgets import QWebEngineView
    _WEBENGINE_AVAILABLE = True
except ImportError:
    _WEBENGINE_AVAILABLE = False


# ─── Model ───────────────────────────────────────────────────────────────────

@dataclass
class Launch:
    id: str
    pkg: str
    name: str
    desc: str
    tags: List[str] = field(default_factory=list)
    phase: str = ""
    starred: bool = False
    file_path: Optional[Path] = None
    file_format: str = "py"  # "py" or "xml"
    state: str = "stopped"
    pid: Optional[int] = None
    uptime: int = 0
    logs: List[str] = field(default_factory=list)
    _process: Optional[QProcess] = field(default=None, repr=False)


# Per-launch metadata: tags drive filter chips, starred → PINNED section, phase
# → coloured chip on the card. Keys are "package/launch_name". Anything not
# listed gets defaults from the discovery code (no tags, not starred).
LAUNCH_META: Dict[str, dict] = {
    "safety_cage/lane_following": {
        "starred": True, "phase": "F2", "tags": ["F2", "Sim"],
        "description": "F2 end-to-end demo: Gazebo + perception + PD + cage + logger",
    },
    "cobraflex_rl/train_lane": {
        "starred": True, "phase": "F3", "tags": ["F3", "Sim"],
        "description": "PPO training, headless Gazebo (D-34, TS-01 open)",
    },
    "cobraflex/gazebo": {
        "tags": ["Sim"],
        "description": "Gazebo simulation with obstacles.world (basic URDF)",
    },
    "cobraflex/gazebo_mesh": {
        "tags": ["Sim"],
        "description": "Gazebo with lane_following_oval.world + mesh URDF",
    },
    "cobraflex/lane_keeper_gazebo": {
        "tags": ["Sim"],
        "description": "Lane keeper standalone (no cage) in Gazebo",
    },
    "cobraflex/mapping": {
        "tags": ["Sim"],
        "description": "SLAM mapping in simulation with RViz",
    },
    "cobraflex/navigation": {
        "tags": ["Sim"],
        "description": "Nav2 + RViz in simulation",
    },
    "cobraflex/description": {
        "tags": ["Utils"],
        "description": "Robot description (URDF) + joint_state_publisher_gui + RViz",
    },
    "cobraflex/rsp": {
        "tags": ["Utils"],
        "description": "robot_state_publisher only",
    },
    "cobraflex/cobraflex_bringup": {
        "tags": ["Hardware"],
        "description": "Physical robot: description + serial driver",
    },
    "cobraflex/cobraflex_driver": {
        "tags": ["Hardware"],
        "description": "Serial driver for the CobraFlex JSON protocol (/dev/ttyACM1)",
    },
    "cobraflex/cobraflex_description": {
        "tags": ["Hardware"],
        "description": "Hardware URDF + RSP + JSP + optional RViz",
    },
    "cobraflex/cobraflex_sensors": {
        "tags": ["Hardware"],
        "description": "SLLIDAR A2M8 + ZED Mini camera drivers",
    },
    "cobraflex/cobraflex_automatic": {
        "tags": ["Hardware"],
        "description": "Sensors + lidar-based obstacle avoidance",
    },
    "cobraflex/cobraflex_lane_keeper": {
        "tags": ["Hardware"],
        "description": "Lane keeper on the physical robot",
    },
    "cobraflex/cobraflex_mapping": {
        "tags": ["Hardware"],
        "description": "SLAM mapping on the physical robot",
    },
}


FILTER_CHIPS = [
    ("F2", "F2 demo"),
    ("F3", "F3 training"),
    ("Sim", "Sim"),
    ("Hardware", "Hardware"),
    ("Utils", "Utils"),
]


PHASE_COLORS = {
    "F2": {"bg": "#2a1e3f", "fg": "#c4b5fd", "bd": "#4c2f80"},
    "F3": {"bg": "#0f2a4f", "fg": "#79b8ff", "bd": "#1f4f8f"},
}


# ─── Discovery (RosBackend) ──────────────────────────────────────────────────

def _extract_doc(path: Path, fmt: str) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if fmt == "py":
        try:
            doc = ast.get_docstring(ast.parse(text))
        except SyntaxError:
            doc = None
        if doc:
            return doc.strip().split("\n", 1)[0].rstrip(".")
    else:
        for m in re.finditer(r"<!--\s*(.+?)\s*-->", text, re.DOTALL):
            line = m.group(1).strip().split("\n", 1)[0].strip()
            line = line.strip(" =-*#").strip()
            if line:
                return line
    return None


def discover_launches(workspace: Path) -> List[Launch]:
    src = workspace / "src"
    out: List[Launch] = []
    if not src.is_dir():
        return out
    for pkg_dir in sorted(src.iterdir()):
        if not pkg_dir.is_dir():
            continue
        launch_dir = pkg_dir / "launch"
        if not launch_dir.is_dir():
            continue
        pkg = pkg_dir.name
        for f in sorted(launch_dir.iterdir()):
            stem = f.name
            if stem.endswith(".launch.py"):
                fmt, name = "py", stem[: -len(".launch.py")]
            elif stem.endswith(".launch.xml"):
                fmt, name = "xml", stem[: -len(".launch.xml")]
            else:
                continue
            key = f"{pkg}/{name}"
            meta = LAUNCH_META.get(key, {})
            desc = meta.get("description") or _extract_doc(f, fmt) or "(no description)"
            out.append(Launch(
                id=f"{pkg}__{name}",
                pkg=pkg, name=name, desc=desc,
                tags=list(meta.get("tags", [])),
                phase=meta.get("phase", ""),
                starred=bool(meta.get("starred", False)),
                file_path=f, file_format=fmt,
            ))
    out.sort(key=lambda l: (not l.starred, l.pkg, l.name))
    return out


# ─── Backend abstraction ─────────────────────────────────────────────────────

class Backend:
    def __init__(self) -> None:
        self.launches: List[Launch] = []
        self.on_state_changed: Callable[[Launch], None] = lambda l: None
        self.on_log_line: Callable[[Launch, str], None] = lambda l, s: None

    def setup(self) -> None: ...
    def run(self, launch: Launch) -> None: ...
    def stop(self, launch: Launch) -> None: ...
    def shutdown(self) -> None: ...


# ─── MockBackend ─────────────────────────────────────────────────────────────

LOG_TEMPLATES = [
    ("INFO", "cage_ros_node", "rule C-01 lane_boundary OK"),
    ("INFO", "cage_ros_node", "rule C-04 heading_window OK"),
    ("INFO", "lane_perception", "frame OK — 2 lane candidates"),
    ("INFO", "pd_baseline", "steer = {:+.3f} rad, throttle = {:.2f}"),
    ("INFO", "cage_logger", "wrote 32 rows to cage_log.csv"),
]

INITIAL_MOCK_LOGS = [
    "[INFO] [cage_ros_node]: Loaded cage v0.5.1",
    "[INFO] [lane_perception]: subscribed to /camera/image_raw",
    "[INFO] [pd_baseline]: PD controller v0.8.0 ready",
    "[INFO] [cage_logger]: writing CSV to experiments/sim/runs/ros_run_*/cage_log.csv",
    "[INFO] [cage_ros_node]: rule C-01 lane_boundary OK",
]


def _make_mock_launches() -> List[Launch]:
    """Hardcoded mirror of the real project's launches for offline previews."""
    specs = [
        ("safety_cage", "lane_following", "running", 12345, 151, INITIAL_MOCK_LOGS),
        ("cobraflex_rl", "train_lane", "stopped", None, 0, []),
        ("cobraflex", "gazebo", "stopped", None, 0, []),
        ("cobraflex", "gazebo_mesh", "stopped", None, 0, []),
        ("cobraflex", "lane_keeper_gazebo", "stopped", None, 0, []),
        ("cobraflex", "mapping", "stopped", None, 0, []),
        ("cobraflex", "navigation", "stopped", None, 0, []),
        ("cobraflex", "description", "stopped", None, 0, []),
        ("cobraflex", "rsp", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_bringup", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_driver", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_sensors", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_automatic", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_lane_keeper", "stopped", None, 0, []),
        ("cobraflex", "cobraflex_mapping", "stopped", None, 0, []),
    ]
    out = []
    for pkg, name, state, pid, uptime, logs in specs:
        key = f"{pkg}/{name}"
        meta = LAUNCH_META.get(key, {})
        out.append(Launch(
            id=f"{pkg}__{name}", pkg=pkg, name=name,
            desc=meta.get("description", "(no description)"),
            tags=list(meta.get("tags", [])),
            phase=meta.get("phase", ""),
            starred=bool(meta.get("starred", False)),
            state=state, pid=pid, uptime=uptime, logs=list(logs),
        ))
    return out


class MockBackend(Backend):
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
        launch.logs.append(f"[demo] started {launch.pkg}/{launch.name} (PID {launch.pid})")
        self.on_state_changed(launch)
        self._start_log_timer(launch)

    def stop(self, launch: Launch) -> None:
        launch.logs.append(f"[demo] stopped {launch.pkg}/{launch.name} (was PID {launch.pid})")
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
        t.start(2200)
        self._timers[launch.id] = t

    def _tick_log(self, launch: Launch) -> None:
        lvl, node, msg = random.choice(LOG_TEMPLATES)
        if "{" in msg:
            msg = msg.format(random.uniform(-0.1, 0.1), random.uniform(0.2, 0.5))
        line = f"[{lvl}] [{node}]: {msg}"
        launch.logs.append(line)
        if len(launch.logs) > 200:
            launch.logs.pop(0)
        self.on_log_line(launch, line)


# ─── RosBackend ──────────────────────────────────────────────────────────────

class RosBackend(Backend):
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
        proc = QProcess()
        proc.setProgram("ros2")
        proc.setArguments(["launch", launch.pkg, launch.file_path.name])
        proc.setProcessChannelMode(QProcess.MergedChannels)
        if hasattr(proc, "setChildProcessModifier") and hasattr(os, "setsid"):
            proc.setChildProcessModifier(os.setsid)
        proc.readyReadStandardOutput.connect(lambda l=launch, p=proc: self._on_output(l, p))
        proc.finished.connect(lambda code, status, l=launch: self._on_finished(l, code))
        proc.errorOccurred.connect(lambda err, l=launch: self._on_error(l, err))
        proc.start()
        if not proc.waitForStarted(3000):
            launch.logs.append(f"[launch_gui] failed to start: {proc.errorString()}")
            self.on_log_line(launch, launch.logs[-1])
            return
        launch._process = proc
        launch.state = "running"
        launch.pid = int(proc.processId())
        launch.uptime = 0
        launch.logs.append(f"[launch_gui] ros2 launch {launch.pkg} {launch.file_path.name} (PID {launch.pid})")
        self.on_log_line(launch, launch.logs[-1])
        self.on_state_changed(launch)

    def stop(self, launch: Launch) -> None:
        proc = launch._process
        if proc is None or proc.state() == QProcess.NotRunning:
            return
        pid = launch.pid
        if pid and hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                os.killpg(os.getpgid(pid), signal.SIGINT)
                launch.logs.append(f"[launch_gui] SIGINT -> pgid({pid})")
                self.on_log_line(launch, launch.logs[-1])
            except OSError as e:
                launch.logs.append(f"[launch_gui] killpg failed ({e}); terminating QProcess")
                self.on_log_line(launch, launch.logs[-1])
                proc.terminate()
        else:
            proc.terminate()
        QTimer.singleShot(5000, lambda l=launch: self._force_kill_if_alive(l))

    def shutdown(self) -> None:
        for launch in list(self.launches):
            if launch.state == "running":
                self.stop(launch)
        # Give SIGINT a moment, then force-kill anything still alive.
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
                launch.logs.append(f"[launch_gui] SIGTERM -> pgid({pid})")
                self.on_log_line(launch, launch.logs[-1])
            except OSError:
                pass
        proc.kill()

    def _on_output(self, launch: Launch, proc: QProcess) -> None:
        data = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        for line in data.splitlines():
            if not line:
                continue
            launch.logs.append(line)
            if len(launch.logs) > 500:
                launch.logs.pop(0)
            self.on_log_line(launch, line)

    def _on_finished(self, launch: Launch, code: int) -> None:
        launch.logs.append(f"[launch_gui] exited (code={code})")
        self.on_log_line(launch, launch.logs[-1])
        launch.state = "stopped"
        launch.pid = None
        launch.uptime = 0
        launch._process = None
        self.on_state_changed(launch)

    def _on_error(self, launch: Launch, err) -> None:
        launch.logs.append(f"[launch_gui] QProcess error: {err}")
        self.on_log_line(launch, launch.logs[-1])


# ─── QSS ─────────────────────────────────────────────────────────────────────

QSS = """
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 13px; }

QMainWindow { background: #0d1117; }
QWidget#root { background: #0d1117; color: #e6edf3; }

QFrame#hdr { background: #0d1117; border-bottom: 1px solid #161b22; }
QLabel#hdrEyebrow { font-size: 10px; font-weight: 600; color: #6e7681; }
QLabel#hdrTitle { font-size: 20px; font-weight: 600; color: #f0f6fc; }
QLabel#hdrMetaDim { color: #6e7681; font-size: 11px; }
QLabel#hdrMetaMono {
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
    color: #c9d1d9; font-size: 11px;
}
QLabel#hdrMetaDot { color: #30363d; font-size: 11px; }
QFrame#hdrRunning { background: #0f1f17; border: 1px solid #1f3a2a; border-radius: 12px; }
QLabel#hdrRunningText { color: #c9d1d9; font-size: 11px; }

QLabel#phaseChipHdr {
    background: #0f2a4f; color: #79b8ff;
    border: 1px solid #1f4f8f; border-radius: 4px;
    font-size: 11px; font-weight: 700;
    padding: 2px 9px;
}
QLabel#modeBadge {
    background: #2a1e3f; color: #c4b5fd;
    border: 1px solid #4c2f80; border-radius: 4px;
    font-size: 10px; font-weight: 700;
    padding: 2px 7px;
}

QFrame#tabBar { background: #0d1117; border-bottom: 1px solid #161b22; }
QPushButton#tab {
    background: transparent; color: #8b949e;
    border: none; border-bottom: 2px solid transparent;
    padding: 10px 16px; font-size: 13px; font-weight: 500;
    margin: 0;
}
QPushButton#tab:hover { color: #c9d1d9; }
QPushButton#tab:checked {
    color: #2dd4bf; border-bottom: 2px solid #2dd4bf;
}

QFrame#filterBar { background: #0d1117; border-bottom: 1px solid #161b22; }
QFrame#searchWrap { background: #161b22; border: 1px solid #21262d; border-radius: 6px; }
QFrame#searchWrap[focused="true"] { background: #0f1d1c; border-color: #2dd4bf; }
QLabel#searchIcon { color: #6e7681; font-size: 12px; }
QLineEdit#searchInput { background: transparent; border: none; color: #e6edf3; font-size: 13px; }
QLineEdit#searchInput::placeholder { color: #6e7681; }

QPushButton#chip {
    background: #161b22; color: #8b949e;
    border: 1px solid #21262d; border-radius: 14px;
    padding: 5px 14px; font-size: 12px; font-weight: 500;
}
QPushButton#chip:hover { background: #1c232c; color: #c9d1d9; }
QPushButton#chip:checked {
    background: #0f2a4f; color: #79b8ff; border-color: #1f4f8f;
}
QPushButton#chip:checked:hover { background: #133463; }

QLabel#countPill {
    background: #0f1f17; color: #56d364;
    border: 1px solid #1f3a2a; border-radius: 14px;
    padding: 5px 14px; font-size: 11px; font-weight: 500;
}

QLabel#sectionLabel { color: #8b949e; font-size: 10px; font-weight: 700; }
QLabel#sectionGlyph { font-size: 11px; }
QLabel#sectionCount {
    color: #6e7681; font-size: 10px; font-weight: 600;
    background: #161b22; border: 1px solid #21262d;
    border-radius: 9px; padding: 1px 8px;
}
QFrame#sectionRule { background: #161b22; border: none; max-height: 1px; }

QFrame[role="card"] { background: #161b22; border: 1px solid #21262d; border-radius: 8px; }
QFrame[role="card"]:hover { background: #1a212a; border-color: #2f3742; }
QFrame[role="card"][running="true"] {
    border-left: 3px solid #3fb950;
    background: #131c17;
}
QFrame[role="card"][running="true"]:hover {
    background: #16241b; border-color: #2f3742; border-left-color: #56d364;
}
QFrame[role="card"][selected="true"] {
    background: #121a26; border-color: #1f4f8f;
}
QFrame[role="card"][running="true"][selected="true"] {
    background: #121e18; border-color: #21262d; border-left-color: #3fb950;
}

QLabel#cardStar { color: #fbbf24; font-size: 12px; }
QLabel#cardPkg { color: #79c0ff; font-size: 13px; font-weight: 600; }
QLabel#cardSlash { color: #484f58; font-size: 13px; }
QLabel#cardName { color: #2dd4bf; font-size: 13px; font-weight: 500; }
QLabel#cardFmt { color: #6e7681; font-size: 10px; font-weight: 600; }
QLabel#cardDesc { color: #8b949e; font-size: 12px; }
QLabel#statusRunning { color: #56d364; font-size: 11px; font-weight: 600; }
QLabel#statusStopped { color: #6e7681; font-size: 11px; }
QLabel#metaSep { color: #30363d; font-size: 11px; }
QLabel#metaMono {
    color: #8b949e; font-size: 11px;
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}

QFrame#dotHalo { background: rgba(63, 185, 80, 0.18); border: none; border-radius: 7px; }
QFrame#dotGreen { background: #3fb950; border: none; border-radius: 4px; }
QFrame#dotGrey { background: #484f58; border: 1px solid #6e7681; border-radius: 4px; }

QPushButton#btnRun {
    background: #238636; color: #ffffff;
    border: 1px solid #2ea043; border-radius: 5px;
    padding: 0 11px; font-size: 12px; font-weight: 500; min-height: 26px;
}
QPushButton#btnRun:hover { background: #2ea043; }
QPushButton#btnRun:disabled { background: #1a2a1f; color: #4d6356; border-color: #1f3328; }

QPushButton#btnStop {
    background: #da3633; color: #ffffff;
    border: 1px solid #f85149; border-radius: 5px;
    padding: 0 11px; font-size: 12px; font-weight: 500; min-height: 26px;
}
QPushButton#btnStop:hover { background: #f85149; }
QPushButton#btnStop:disabled { background: #2a1d1d; color: #6b4848; border-color: #3a2222; }

QPushButton#btnLogs {
    background: transparent; color: #c9d1d9;
    border: 1px solid #30363d; border-radius: 5px;
    padding: 0 11px; font-size: 12px; font-weight: 500; min-height: 26px;
}
QPushButton#btnLogs:hover { background: #1c232c; border-color: #484f58; }

QLabel#empty {
    color: #6e7681; font-size: 12px;
    border: 1px dashed #21262d; border-radius: 8px;
    padding: 32px;
}

QFrame#logsPanel { background: #0d1117; border-top: 1px solid #161b22; }
QLabel#logsKey { color: #8b949e; font-size: 10px; font-weight: 600; }
QLabel#logsSep { color: #30363d; font-size: 11px; }
QLabel#logsSubject {
    color: #c9d1d9; font-size: 11px; font-weight: 500;
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}
QFrame#logsLive { background: #0f1f17; border: 1px solid #1f3a2a; border-radius: 10px; }
QLabel#logsLiveText { color: #56d364; font-size: 10px; font-weight: 700; }

QPushButton#btnGhost {
    background: transparent; color: #8b949e;
    border: 1px solid #21262d; border-radius: 5px;
    padding: 0 9px; font-size: 11px; min-height: 22px;
}
QPushButton#btnGhost:hover { background: #161b22; border-color: #30363d; color: #c9d1d9; }

QTextEdit#logsBody {
    background: #010409; border: 1px solid #161b22; border-radius: 6px;
    color: #8b949e; padding: 10px 12px;
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
    font-size: 11px;
}

QScrollArea { border: none; background: #0d1117; }
QScrollBar:vertical { background: #0d1117; width: 10px; }
QScrollBar::handle:vertical { background: #21262d; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #30363d; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


# ─── Widgets ─────────────────────────────────────────────────────────────────

def make_green_dot() -> QFrame:
    halo = QFrame()
    halo.setObjectName("dotHalo")
    halo.setFixedSize(14, 14)
    dot = QFrame(halo)
    dot.setObjectName("dotGreen")
    dot.setFixedSize(8, 8)
    dot.move(3, 3)
    return halo


def make_grey_dot() -> QFrame:
    dot = QFrame()
    dot.setObjectName("dotGrey")
    dot.setFixedSize(8, 8)
    return dot


def make_phase_chip(phase: str) -> QLabel:
    lbl = QLabel(phase)
    c = PHASE_COLORS.get(phase, PHASE_COLORS["F3"])
    lbl.setStyleSheet(
        f"background: {c['bg']}; color: {c['fg']}; "
        f"border: 1px solid {c['bd']}; border-radius: 4px; "
        f"padding: 1px 7px; font-size: 10px; font-weight: 700;"
    )
    return lbl


def set_letter_spacing(widget, value: float) -> None:
    f = widget.font()
    f.setLetterSpacing(QFont.AbsoluteSpacing, value)
    widget.setFont(f)


class SectionHeader(QFrame):
    def __init__(self, label: str, count: int, glyph: str = "") -> None:
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(8)
        if glyph:
            g = QLabel(glyph); g.setObjectName("sectionGlyph"); h.addWidget(g)
        lab = QLabel(label); lab.setObjectName("sectionLabel")
        set_letter_spacing(lab, 1.4)
        h.addWidget(lab)
        cnt = QLabel(str(count)); cnt.setObjectName("sectionCount")
        h.addWidget(cnt)
        rule = QFrame(); rule.setObjectName("sectionRule")
        rule.setFixedHeight(1)
        rule.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        h.addWidget(rule, 1)


class LaunchCard(QFrame):
    selected_signal = Signal(str)
    run_signal = Signal(str)
    stop_signal = Signal(str)

    def __init__(self, launch: Launch) -> None:
        super().__init__()
        self.launch = launch
        self.setProperty("role", "card")
        self.setProperty("running", "true" if launch.state == "running" else "false")
        self.setProperty("selected", "false")
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 12)
        outer.setSpacing(16)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.setContentsMargins(0, 0, 0, 0)

        l1 = QHBoxLayout()
        l1.setSpacing(8)
        l1.setContentsMargins(0, 0, 0, 0)
        if launch.starred:
            star = QLabel("⭐"); star.setObjectName("cardStar")
            l1.addWidget(star)
        if launch.phase:
            l1.addWidget(make_phase_chip(launch.phase))
        pkg = QLabel(launch.pkg); pkg.setObjectName("cardPkg"); l1.addWidget(pkg)
        sl = QLabel("/"); sl.setObjectName("cardSlash"); l1.addWidget(sl)
        nm = QLabel(launch.name); nm.setObjectName("cardName"); l1.addWidget(nm)
        if launch.file_format == "xml":
            fmt = QLabel("xml"); fmt.setObjectName("cardFmt"); l1.addWidget(fmt)
        l1.addStretch()
        col.addLayout(l1)

        desc = QLabel(launch.desc); desc.setObjectName("cardDesc"); desc.setWordWrap(True)
        col.addWidget(desc)

        self.status_row = QHBoxLayout()
        self.status_row.setSpacing(6)
        self.status_row.setContentsMargins(0, 3, 0, 0)
        col.addLayout(self.status_row)

        outer.addLayout(col, 1)

        btns_widget = QWidget()
        btns_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btns = QHBoxLayout(btns_widget)
        btns.setSpacing(6); btns.setContentsMargins(0, 0, 0, 0)

        self.run_btn = QPushButton("▶  Run"); self.run_btn.setObjectName("btnRun")
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(lambda: self.run_signal.emit(self.launch.id))

        self.stop_btn = QPushButton("■  Stop"); self.stop_btn.setObjectName("btnStop")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(lambda: self.stop_signal.emit(self.launch.id))

        self.logs_btn = QPushButton("☰  Logs"); self.logs_btn.setObjectName("btnLogs")
        self.logs_btn.setCursor(Qt.PointingHandCursor)
        self.logs_btn.clicked.connect(lambda: self.selected_signal.emit(self.launch.id))

        btns.addWidget(self.run_btn); btns.addWidget(self.stop_btn); btns.addWidget(self.logs_btn)
        outer.addWidget(btns_widget, 0, Qt.AlignTop)

        self.refresh()

    def mousePressEvent(self, e: QMouseEvent) -> None:
        self.selected_signal.emit(self.launch.id)
        super().mousePressEvent(e)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self); self.style().polish(self)

    def refresh(self) -> None:
        while self.status_row.count():
            item = self.status_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if self.launch.state == "running":
            self.status_row.addWidget(make_green_dot())
            self.status_row.addSpacing(2)
            r = QLabel("running"); r.setObjectName("statusRunning"); self.status_row.addWidget(r)
            s1 = QLabel("·"); s1.setObjectName("metaSep"); self.status_row.addWidget(s1)
            pid = QLabel(f"PID {self.launch.pid}"); pid.setObjectName("metaMono")
            self.status_row.addWidget(pid)
            s2 = QLabel("·"); s2.setObjectName("metaSep"); self.status_row.addWidget(s2)
            mm, ss = divmod(self.launch.uptime, 60)
            up = QLabel(f"{mm:02d}:{ss:02d}"); up.setObjectName("metaMono")
            self.status_row.addWidget(up)
            self.run_btn.setEnabled(False); self.stop_btn.setEnabled(True)
            self.setProperty("running", "true")
        else:
            self.status_row.addWidget(make_grey_dot())
            self.status_row.addSpacing(2)
            s = QLabel("stopped"); s.setObjectName("statusStopped"); self.status_row.addWidget(s)
            self.run_btn.setEnabled(True); self.stop_btn.setEnabled(False)
            self.setProperty("running", "false")
        self.status_row.addStretch()
        self.style().unpolish(self); self.style().polish(self)


# ─── Embedded HTML pages (lazy WebEngine) ───────────────────────────────────

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TF_TREE_HTML = ASSETS_DIR / "tf_tree_visualizer.html"
ROS_GRAPH_HTML = ASSETS_DIR / "ros2_graph_explorer.html"


class WebEnginePage(QWidget):
    """Lazy-loaded WebEngine page for a local HTML asset."""

    def __init__(self, html_path: Path) -> None:
        super().__init__()
        self.setObjectName("root")
        self._html_path = html_path
        self._initialized = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        if not _WEBENGINE_AVAILABLE:
            self._show_missing("PySide6 WebEngine is not installed.")
            return
        if not self._html_path.exists():
            self._show_missing(f"Asset not found:\n{self._html_path}")
            return
        view = QWebEngineView()
        view.setUrl(QUrl.fromLocalFile(str(self._html_path)))
        self._layout.addWidget(view)

    def _show_missing(self, reason: str) -> None:
        msg = QLabel(
            f"{reason}\n\n"
            "To enable this tab, install the Qt WebEngine module:\n\n"
            "    pip install PySide6-Addons\n\n"
            "Then restart the launch manager."
        )
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: #6e7681; font-size: 13px; padding: 48px;")
        msg.setWordWrap(True)
        self._layout.addWidget(msg)


# ─── Main window ─────────────────────────────────────────────────────────────

class LaunchGui(QMainWindow):
    def __init__(self, backend: Backend, mode_label: str) -> None:
        super().__init__()
        self.setWindowTitle("CobraFlex · Launch Manager")
        self.setMinimumSize(1100, 760)
        self.resize(1240, 860)

        self.backend = backend
        self.backend.on_state_changed = self._on_backend_state
        self.backend.on_log_line = self._on_backend_log
        self.mode_label = mode_label

        self.launches: List[Launch] = self.backend.launches
        self.query: str = ""
        self.active_chips: Set[str] = {"F2", "F3", "Sim", "Utils"}
        self.selected_id: str = self.launches[0].id if self.launches else ""
        self.card_widgets: Dict[str, LaunchCard] = {}

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        outer.addWidget(self._build_header())
        outer.addWidget(self._build_tab_bar())

        launches_page = QWidget()
        launches_page.setObjectName("root")
        lp = QVBoxLayout(launches_page)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(0)
        lp.addWidget(self._build_filter())
        lp.addWidget(self._build_list(), 1)
        lp.addWidget(self._build_logs())

        self.tf_tree_page = WebEnginePage(TF_TREE_HTML)
        self.ros_graph_page = WebEnginePage(ROS_GRAPH_HTML)

        self.stack = QStackedWidget()
        self.stack.addWidget(launches_page)
        self.stack.addWidget(self.tf_tree_page)
        self.stack.addWidget(self.ros_graph_page)
        outer.addWidget(self.stack, 1)

        self._rebuild_list()
        self._refresh_logs_view()

        self.uptime_timer = QTimer(self)
        self.uptime_timer.timeout.connect(self._tick_uptime)
        self.uptime_timer.start(1000)

    def closeEvent(self, e) -> None:
        self.backend.shutdown()
        super().closeEvent(e)

    # Header ───────────────────────────────────────────────────────
    def _build_header(self) -> QWidget:
        f = QFrame(); f.setObjectName("hdr")
        h = QHBoxLayout(f); h.setContentsMargins(24, 14, 24, 12); h.setSpacing(14)

        left = QVBoxLayout(); left.setSpacing(2)
        eye = QLabel("COBRAFLEX · THESIS"); eye.setObjectName("hdrEyebrow")
        set_letter_spacing(eye, 1.6); left.addWidget(eye)
        title = QLabel("Launch Manager"); title.setObjectName("hdrTitle")
        left.addWidget(title)
        h.addLayout(left); h.addStretch()

        meta = QHBoxLayout(); meta.setSpacing(6)
        for txt, name in [("commit", "hdrMetaDim"), ("0cbd1ad", "hdrMetaMono"),
                          ("·", "hdrMetaDot"), ("jazzy", "hdrMetaMono")]:
            lbl = QLabel(txt); lbl.setObjectName(name); meta.addWidget(lbl)
        h.addLayout(meta)

        if self.mode_label:
            mb = QLabel(self.mode_label); mb.setObjectName("modeBadge")
            h.addWidget(mb)

        phase = QLabel("F3"); phase.setObjectName("phaseChipHdr")
        h.addWidget(phase)

        self.running_pill = QFrame(); self.running_pill.setObjectName("hdrRunning")
        rp = QHBoxLayout(self.running_pill); rp.setContentsMargins(10, 4, 12, 4); rp.setSpacing(6)
        rp.addWidget(make_green_dot())
        self.running_text = QLabel("0 running"); self.running_text.setObjectName("hdrRunningText")
        rp.addWidget(self.running_text)
        h.addWidget(self.running_pill)
        return f

    # Tabs ─────────────────────────────────────────────────────────
    def _build_tab_bar(self) -> QWidget:
        f = QFrame(); f.setObjectName("tabBar")
        h = QHBoxLayout(f); h.setContentsMargins(20, 0, 20, 0); h.setSpacing(2)
        self.tab_buttons: List[QPushButton] = []
        for i, label in enumerate(["Launches", "TF Tree", "ROS Graph"]):
            b = QPushButton(label); b.setObjectName("tab")
            b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == 0)
            b.clicked.connect(lambda checked, idx=i: self._on_tab_changed(idx))
            self.tab_buttons.append(b)
            h.addWidget(b)
        h.addStretch()
        return f

    def _on_tab_changed(self, idx: int) -> None:
        for i, b in enumerate(self.tab_buttons):
            b.setChecked(i == idx)
        page = self.stack.widget(idx)
        if isinstance(page, WebEnginePage):
            page.initialize()
        self.stack.setCurrentIndex(idx)

    # Filter ───────────────────────────────────────────────────────
    def _build_filter(self) -> QWidget:
        f = QFrame(); f.setObjectName("filterBar")
        h = QHBoxLayout(f); h.setContentsMargins(24, 10, 24, 10); h.setSpacing(12)

        self.search_wrap = QFrame(); self.search_wrap.setObjectName("searchWrap")
        self.search_wrap.setProperty("focused", "false")
        self.search_wrap.setFixedHeight(32); self.search_wrap.setMaximumWidth(320)
        sw = QHBoxLayout(self.search_wrap); sw.setContentsMargins(10, 0, 10, 0); sw.setSpacing(8)
        icon = QLabel("🔍"); icon.setObjectName("searchIcon"); sw.addWidget(icon)
        self.search_input = QLineEdit(); self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Filter launches…")
        self.search_input.textChanged.connect(self._on_query_changed)
        self.search_input.installEventFilter(self)
        sw.addWidget(self.search_input)
        h.addWidget(self.search_wrap)

        chip_row = QHBoxLayout(); chip_row.setSpacing(6)
        self.chip_buttons: Dict[str, QPushButton] = {}
        for cid, label in FILTER_CHIPS:
            b = QPushButton(label); b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor); b.setCheckable(True)
            b.setChecked(cid in self.active_chips)
            b.clicked.connect(lambda checked, c=cid: self._on_chip(c, checked))
            self.chip_buttons[cid] = b
            chip_row.addWidget(b)
        h.addLayout(chip_row); h.addStretch()

        self.count_pill = QLabel(); self.count_pill.setObjectName("countPill")
        h.addWidget(self.count_pill)
        return f

    def eventFilter(self, obj, ev):
        if obj is self.search_input:
            if ev.type() == QEvent.Type.FocusIn:
                self.search_wrap.setProperty("focused", "true")
            elif ev.type() == QEvent.Type.FocusOut:
                self.search_wrap.setProperty("focused", "false")
            else:
                return super().eventFilter(obj, ev)
            self.search_wrap.style().unpolish(self.search_wrap)
            self.search_wrap.style().polish(self.search_wrap)
        return super().eventFilter(obj, ev)

    # List ─────────────────────────────────────────────────────────
    def _build_list(self) -> QWidget:
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.list_container = QWidget(); self.list_container.setObjectName("root")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(24, 16, 24, 12); self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.list_container)
        return self.scroll

    def _rebuild_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.card_widgets = {}

        filtered = self._filter_launches()
        starred = [l for l in filtered if l.starred]
        rest = [l for l in filtered if not l.starred]

        if not filtered:
            empty = QLabel("No launches match the current filters.")
            empty.setObjectName("empty"); empty.setAlignment(Qt.AlignCenter)
            self.list_layout.addWidget(empty)
        else:
            if starred:
                self.list_layout.addWidget(SectionHeader("PINNED", len(starred), glyph="⭐"))
                for l in starred:
                    self._add_card(l)
                self.list_layout.addSpacing(10)
                self.list_layout.addWidget(SectionHeader("ALL LAUNCHES", len(rest)))
            for l in rest:
                self._add_card(l)
        self.list_layout.addStretch()

        self.count_pill.setText(f"✓  {len(filtered)} of {len(self.launches)} launches")
        self._refresh_running_pill()

    def _add_card(self, launch: Launch) -> None:
        card = LaunchCard(launch)
        card.set_selected(launch.id == self.selected_id)
        card.selected_signal.connect(self._on_select)
        card.run_signal.connect(self._on_run)
        card.stop_signal.connect(self._on_stop)
        self.card_widgets[launch.id] = card
        self.list_layout.addWidget(card)

    def _filter_launches(self) -> List[Launch]:
        q = self.query.strip().lower()
        out = []
        for l in self.launches:
            tags = l.tags if l.tags else ["_untagged"]
            if not any(t in self.active_chips for t in tags):
                continue
            if q and not (q in l.pkg.lower() or q in l.name.lower() or q in l.desc.lower()):
                continue
            out.append(l)
        return out

    def _refresh_running_pill(self) -> None:
        n = sum(1 for l in self.launches if l.state == "running")
        self.running_text.setText(f"{n} running")

    # Logs ─────────────────────────────────────────────────────────
    def _build_logs(self) -> QWidget:
        f = QFrame(); f.setObjectName("logsPanel"); f.setMaximumHeight(280)
        v = QVBoxLayout(f); v.setContentsMargins(24, 12, 24, 16); v.setSpacing(8)

        head = QHBoxLayout(); head.setSpacing(8)
        key = QLabel("LOGS"); key.setObjectName("logsKey")
        set_letter_spacing(key, 1.4); head.addWidget(key)
        sep = QLabel("·"); sep.setObjectName("logsSep"); head.addWidget(sep)
        self.logs_subject = QLabel("—"); self.logs_subject.setObjectName("logsSubject")
        head.addWidget(self.logs_subject)

        self.logs_live = QFrame(); self.logs_live.setObjectName("logsLive")
        ll = QHBoxLayout(self.logs_live); ll.setContentsMargins(8, 2, 10, 2); ll.setSpacing(5)
        ll.addWidget(make_green_dot())
        live = QLabel("LIVE"); live.setObjectName("logsLiveText")
        set_letter_spacing(live, 1.0); ll.addWidget(live)
        head.addWidget(self.logs_live)
        head.addStretch()

        for label in ("Clear", "Follow ✓", "Wrap"):
            b = QPushButton(label); b.setObjectName("btnGhost"); b.setCursor(Qt.PointingHandCursor)
            if label == "Clear":
                b.clicked.connect(self._clear_logs)
            head.addWidget(b)
        v.addLayout(head)

        self.logs_view = QTextEdit(); self.logs_view.setObjectName("logsBody")
        self.logs_view.setReadOnly(True)
        v.addWidget(self.logs_view, 1)
        return f

    def _selected_launch(self) -> Optional[Launch]:
        for l in self.launches:
            if l.id == self.selected_id:
                return l
        return None

    def _refresh_logs_view(self) -> None:
        sel = self._selected_launch()
        if sel:
            self.logs_subject.setText(f"{sel.pkg} / {sel.name}")
            self.logs_live.setVisible(sel.state == "running")
        else:
            self.logs_subject.setText("—")
            self.logs_live.setVisible(False)
        self.logs_view.clear()
        if sel:
            for line in sel.logs:
                self._append_log_html(line)

    _LINE_RE = re.compile(r"\[([A-Z]+)\]\s*\[([^\]]+)\]:?\s*(.*)")

    def _append_log_html(self, line: str) -> None:
        m = self._LINE_RE.match(line)
        if m:
            lvl, node, msg = m.groups()
            html = (
                f'<span style="color:#56d364;">[{lvl}]</span> '
                f'<span style="color:#79c0ff;">[{node}]</span>'
                f'<span style="color:#c9d1d9;">: {msg}</span>'
            )
        else:
            html = f'<span style="color:#8b949e;">{line}</span>'
        self.logs_view.append(html)
        sb = self.logs_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_logs(self) -> None:
        sel = self._selected_launch()
        if sel:
            sel.logs.clear()
        self.logs_view.clear()

    # Backend callbacks ────────────────────────────────────────────
    def _on_backend_state(self, launch: Launch) -> None:
        if launch.id in self.card_widgets:
            self.card_widgets[launch.id].refresh()
        self._refresh_running_pill()
        if launch.id == self.selected_id:
            self._refresh_logs_view()

    def _on_backend_log(self, launch: Launch, line: str) -> None:
        if launch.id == self.selected_id:
            self._append_log_html(line)

    # User actions ─────────────────────────────────────────────────
    def _on_query_changed(self, text: str) -> None:
        self.query = text
        self._rebuild_list()

    def _on_chip(self, cid: str, checked: bool) -> None:
        if checked:
            self.active_chips.add(cid)
        else:
            self.active_chips.discard(cid)
        self._rebuild_list()

    def _on_select(self, launch_id: str) -> None:
        if self.selected_id == launch_id:
            return
        prev = self.card_widgets.get(self.selected_id)
        if prev:
            prev.set_selected(False)
        self.selected_id = launch_id
        nxt = self.card_widgets.get(launch_id)
        if nxt:
            nxt.set_selected(True)
        self._refresh_logs_view()

    def _on_run(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is None:
            return
        self.backend.run(launch)
        self.selected_id = launch_id
        for lid, card in self.card_widgets.items():
            card.set_selected(lid == launch_id)
        self._refresh_logs_view()

    def _on_stop(self, launch_id: str) -> None:
        launch = next((l for l in self.launches if l.id == launch_id), None)
        if launch is not None:
            self.backend.stop(launch)

    def _tick_uptime(self) -> None:
        for l in self.launches:
            if l.state == "running":
                l.uptime += 1
                card = self.card_widgets.get(l.id)
                if card:
                    card.refresh()


# ─── Entrypoint ──────────────────────────────────────────────────────────────

def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="CobraFlex Launch Manager")
    parser.add_argument("--mock", action="store_true",
                        help="Force mock backend (no ROS2 required)")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="Workspace root (default: repo root inferred from this script)")
    args, _ = parser.parse_known_args()

    use_mock = args.mock or shutil.which("ros2") is None
    if args.mock:
        mode_label = "MOCK"
    elif use_mock:
        print("[launch_gui] ros2 not in PATH — falling back to mock backend.",
              file=sys.stderr)
        mode_label = "MOCK (no ros2)"
    else:
        mode_label = ""

    backend: Backend = MockBackend() if use_mock else RosBackend(args.workspace or _workspace_root())
    backend.setup()

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    win = LaunchGui(backend, mode_label)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
