"""
run_io — pure (ROS-free) helpers for writing reproducible run metadata:
content hashing and git-commit lookup. Shared by `train_ppo` (training run
registration, §7.2.8), `eval_policy` (§7.5 evaluation runs) and
`cage_logger_node` (Phase-5 runs on the car) so all three produce the same
reproducibility fields (see `experiments/README.md`).
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

# Launch arguments recorded verbatim (as strings) into a physical run's
# metadata.json under "contract". These are the values that decide what the car
# actually did: the actuation map, the perception contract, the control rate.
# Recorded as given rather than coerced, because the point is to capture what
# the launch was TOLD, not what the node made of it.
CONTRACT_KEYS = (
    "algorithm",
    "max_speed_mps",
    "throttle_deadband",
    "control_rate_hz",
    "steering_to_yaw_rate_gain",
    "heading_fit_mode",
    "heading_gain",
    "heading_temporal_window",
    "white_sat_max",
    "white_val_min",
    "camera_topic",
    "odom_topic",
    "speed_map",
    "throttle_map",
)

# Deliberately NOT here: the Layer-2 settings that decided the 26.08 session
# (`lane_camera_capture_fps`, the ZED `area_memory` / `reset_odom_with_loop_closure`
# overrides). This is a Layer-3 launch and cannot know what Layer 2 was actually
# started with, and a recorded default that might be wrong is worse evidence
# than none. `tools/run_physical_lap.sh` reads them off the RUNNING nodes with
# `ros2 param get` and writes them to the run's `layer2.json`.


def sha256_file(path: PathLike) -> Optional[str]:
    """Return the hex SHA-256 of a file, or None if it cannot be read."""
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def git_commit(cwd: PathLike) -> str:
    """Return the current HEAD commit hash, or "unknown" if git is unavailable
    or `cwd` is not inside a repository."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return completed.stdout.strip() if completed.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def resolve_repo_path(relative: str, start: PathLike = __file__) -> Optional[Path]:
    """Walk up from ``start`` until ``relative`` exists below a parent; else None.

    The same walk-up `cage_ros_node._resolve_cage_yaml` and
    `deploy_cobraflex.launch.py._default_evidence_dir` use, so a run's metadata
    hashes the file the cage actually loaded rather than a second copy that
    happens to be installed elsewhere in the overlay.
    """
    for parent in Path(start).resolve().parents:
        candidate = parent / relative
        if candidate.exists():
            return candidate
    return None


def physical_run_metadata(
    run_id: str,
    mode: str,
    *,
    cage_yaml: Optional[PathLike] = None,
    policy_checkpoint: Optional[PathLike] = None,
    rectify_calibration: Optional[PathLike] = None,
    contract: Optional[dict] = None,
    status: str = "running",
) -> dict:
    """Reproducibility metadata for a run on the physical platform.

    CLAUDE.md requires every run under ``experiments/physical/runs/`` to record
    git commit, cage YAML hash, policy checkpoint hash, scenario hash, seed and
    timestamp. Until 27.08.2026 the physical runs recorded four fields
    (``mode``, ``run_id``, ``created_utc``, ``cycles_logged``) and nothing else,
    so the provenance of the 18.08 and 26.08 track sessions had to be written
    into `docs/17` by hand — see §8's preamble, and §8.9's last-but-two bullet.
    This closes that gap on the logging side.

    Two fields of the sim schema are deliberately absent rather than null:
    ``scenario_yaml_hash`` and ``seed``. A physical run is not a scenario
    execution — there is no YAML to instantiate and no seed to draw from — and
    emitting them as ``None`` would make a hardware run look like a scored
    scenario that failed to record them. When physical scenarios exist
    (`verdict_phys`), they get added here with real values.

    ``contract`` is the deployed launch contract, verbatim as strings: what the
    launch was actually told, not what a default would have been.
    """
    return {
        "run_id": run_id,
        "platform": "physical",
        "mode": mode,
        "status": status,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path(__file__).resolve().parent),
        "cage_yaml": str(cage_yaml) if cage_yaml else None,
        "cage_yaml_hash": sha256_file(cage_yaml) if cage_yaml else None,
        "policy_checkpoint": str(policy_checkpoint) if policy_checkpoint else None,
        "policy_checkpoint_hash": (
            sha256_file(policy_checkpoint) if policy_checkpoint else None
        ),
        "rectify_calibration": (
            str(rectify_calibration) if rectify_calibration else None
        ),
        "rectify_calibration_hash": (
            sha256_file(rectify_calibration) if rectify_calibration else None
        ),
        "contract": dict(contract or {}),
    }
