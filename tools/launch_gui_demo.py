"""Backwards-compat shim: runs launch_gui.py in --mock mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
if "--mock" not in sys.argv:
    sys.argv.insert(1, "--mock")

from launch_gui import main  # noqa: E402

if __name__ == "__main__":
    main()
