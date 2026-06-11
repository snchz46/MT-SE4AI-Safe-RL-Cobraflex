"""Domain model: Launch, LogEntry, and pure utilities (no Qt UI imports)."""

from __future__ import annotations

import re
import time as _time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QProcess


_LOG_LINE_RE = re.compile(r"\[([A-Z]+)\]\s*\[([^\]]+)\]:?\s*(.*)")


@dataclass
class LogEntry:
    time: float       # unix seconds (wall clock)
    level: str        # "INFO" | "WARN" | "ERROR" | "DEBUG" | …
    node: str
    msg: str
    raw: str = ""     # original line; preserved for fallback rendering

    @classmethod
    def parse(cls, line: str) -> "LogEntry":
        """Parse `[LEVEL] [node]: msg`. Anything that doesn't match is
        treated as INFO from `—` so it still shows up filtered/searchable."""
        m = _LOG_LINE_RE.match(line)
        if m:
            return cls(time=_time.time(), level=m.group(1),
                       node=m.group(2), msg=m.group(3), raw=line)
        return cls(time=_time.time(), level="INFO", node="—", msg=line, raw=line)

    def fmt_time(self) -> str:
        return _time.strftime("%H:%M:%S", _time.localtime(self.time))


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
    file_format: str = "py"        # "py" or "xml"
    state: str = "stopped"         # "stopped" | "running" | "failed"
    pid: Optional[int] = None
    uptime: int = 0
    exit_code: Optional[int] = None
    last_error: Optional[str] = None
    logs: List[LogEntry] = field(default_factory=list)
    # Args spec: list of {key, default, value, kind, options?, help?}
    # kind in {"bool", "enum", "number", "string"}
    args: List[dict] = field(default_factory=list)
    # Preset spec: list of {name, args: {key: value}}
    presets: List[dict] = field(default_factory=list)
    _process: Optional[QProcess] = field(default=None, repr=False)
    _stopping: bool = field(default=False, repr=False)
    _setsid_applied: bool = field(default=False, repr=False)
    # PIDs of descendants that escaped the process group (e.g. gz sim).
    # Populated at stop() so _force_kill_if_alive can reach them even after
    # the ros2 launch parent process has already exited.
    _stray_pids: List[int] = field(default_factory=list, repr=False)


def args_to_overrides(args: List[dict]) -> List[str]:
    """Return only `key:=value` strings for args differing from default."""
    out: List[str] = []
    for a in args:
        v = a.get("value", "")
        d = a.get("default", "")
        if v != d and v != "":
            out.append(f"{a['key']}:={v}")
    return out


def build_command(launch: Launch) -> str:
    """Compose the equivalent `ros2 launch ...` line for this launch."""
    file_arg = (launch.file_path.name if launch.file_path
                else f"{launch.name}.launch.{launch.file_format}")
    parts = ["ros2", "launch", launch.pkg, file_arg]
    parts.extend(args_to_overrides(launch.args))
    return " ".join(parts)


def instantiate_args(spec: List[dict]) -> List[dict]:
    """Clone an args spec and seed `value` from `default`."""
    out = []
    for a in spec:
        b = dict(a)
        b["value"] = b.get("default", "")
        out.append(b)
    return out
