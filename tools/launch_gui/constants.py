"""Magic numbers and shared config tables."""

from __future__ import annotations

# Toast lifecycle
TOAST_DURATION_MS = 4200

# Restart sequence: stop, wait, run
RESTART_DELAY_MS = 600

# Force-kill grace period after SIGINT
FORCE_KILL_TIMEOUT_MS = 5000

# QProcess.waitForStarted timeout
PROCESS_START_TIMEOUT_MS = 3000

# Logs buffer cap per launch (older entries are evicted FIFO)
LOGS_MAX_PER_LAUNCH = 500

# Command palette modal
PALETTE_WIDTH = 560
PALETTE_HEIGHT = 420
PALETTE_MAX_ITEMS = 30

# Logs panel max-height (pinned bottom)
LOGS_PANEL_MAX_HEIGHT = 280

# Window
DEFAULT_WINDOW_WIDTH = 1240
DEFAULT_WINDOW_HEIGHT = 860
MIN_WINDOW_WIDTH = 1100
MIN_WINDOW_HEIGHT = 760

# Tick intervals (ms)
UPTIME_TICK_MS = 1000
MOCK_LOG_TICK_MS = 2200

# Phase chip colors
PHASE_COLORS = {
    "F1": {"bg": "#1b3b3a", "fg": "#5eead4", "bd": "#0f5b58"},
    "F2": {"bg": "#2a1e3f", "fg": "#c4b5fd", "bd": "#4c2f80"},
    "F3": {"bg": "#0f2a4f", "fg": "#79b8ff", "bd": "#1f4f8f"},
}

# Filter chips (id, label) — display order
FILTER_CHIPS = [
    ("F2", "F2 demo"),
    ("F3", "F3 training"),
    ("Sim", "Sim"),
    ("Hardware", "Hardware"),
    ("Utils", "Utils"),
]

# Default active chips; Hardware off by default to reduce visual noise.
DEFAULT_ACTIVE_CHIPS = frozenset({"F2", "F3", "Sim", "Utils"})

# Log level chips
LOG_LEVELS = ("ALL", "INFO", "WARN", "ERROR")
LOG_LEVEL_COLORS = {
    "INFO":  "#56d364",
    "WARN":  "#f0a040",
    "ERROR": "#f85149",
    "DEBUG": "#79c0ff",
}
