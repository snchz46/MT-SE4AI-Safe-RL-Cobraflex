"""Entrypoint for `python -m tools.launch_gui` (and direct execution)."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_path() -> None:
    """Make `tools.launch_gui` importable when this file is run directly
    (e.g. `python tools/launch_gui/__main__.py`)."""
    here = Path(__file__).resolve().parent
    repo_root = here.parent.parent
    sys.path.insert(0, str(repo_root))


if __package__ in (None, ""):
    _bootstrap_path()
    from tools.launch_gui.app import main  # type: ignore
else:
    from .app import main


if __name__ == "__main__":
    main()
