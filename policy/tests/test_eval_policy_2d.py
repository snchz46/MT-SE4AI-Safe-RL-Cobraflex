"""
Unit tests for the 2-D-action (steer + throttle) readiness of the §7.5 eval
harness helpers in cobraflex_rl.eval_policy. Runs without ROS/Gazebo.

These lock in the three eval-side fixes made when the Gazebo 2-D posterior
baseline (train_ppo_camera_2d.yaml, D-49..D-58) was launched:

  1. eval must silence BOTH spawn randomisers — ``enabled`` (heading/lateral
     jitter) AND ``random_start_s`` (the D-58 curriculum lever). The latter is
     read by the env independently of ``enabled``, so a nominal eval of the 2-D
     config would otherwise spawn at a random arc-length (non-reproducible).
  2. the per-step record + CSV must carry the throttle channels (the cage's
     longitudinal arbitration is the 2-D run's new SR-CL / SR-009 evidence),
     staying 0-valued/backward-compatible on the frozen 1-D path.
"""

import csv
import sys
from pathlib import Path

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.eval_policy import (  # noqa: E402
    _disable_spawn_perturbation,
    _record_from_info,
    _write_cage_status_csv,
)


def test_disable_spawn_perturbation_zeroes_random_start_s():
    """Both spawn randomisers off — the D-58 lever must not survive into eval."""
    cfg = {
        "spawn_perturbation": {
            "enabled": True,
            "random_start_s": True,
            "heading_rad": 0.15,
            "lateral_m": 0.05,
        }
    }
    _disable_spawn_perturbation(cfg)
    spawn = cfg["spawn_perturbation"]
    assert spawn["enabled"] is False
    assert spawn["random_start_s"] is False
    # Untouched knobs stay (they are inert once enabled is False).
    assert spawn["heading_rad"] == 0.15


def test_disable_spawn_perturbation_missing_block():
    """A config without a spawn_perturbation block still yields both flags off."""
    cfg = {}
    _disable_spawn_perturbation(cfg)
    assert cfg["spawn_perturbation"]["enabled"] is False
    assert cfg["spawn_perturbation"]["random_start_s"] is False


def test_record_carries_throttle_channels():
    """The 2-D throttle stream (raw/safe/correction) reaches the per-step record."""
    info = {"raw_throttle": 0.7, "safe_throttle": 0.4, "throttle_correction": -0.3}
    rec = _record_from_info(episode=0, step=3, info=info)
    assert rec["raw_throttle"] == 0.7
    assert rec["safe_throttle"] == 0.4
    assert rec["throttle_correction"] == -0.3


def test_record_throttle_defaults_zero_on_1d():
    """Frozen 1-D path (no throttle keys in info) → 0-valued, schema-compatible."""
    rec = _record_from_info(episode=0, step=0, info={})
    assert rec["raw_throttle"] == 0.0
    assert rec["safe_throttle"] == 0.0
    assert rec["throttle_correction"] == 0.0


def test_cage_status_csv_has_throttle_columns(tmp_path):
    """The written CSV header + row include the throttle channels."""
    rec = _record_from_info(
        episode=0,
        step=0,
        info={"raw_throttle": 0.9, "safe_throttle": 0.5, "throttle_correction": -0.4},
    )
    out = tmp_path / "cage_status.csv"
    _write_cage_status_csv(out, [rec])
    with out.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {"raw_throttle", "safe_throttle", "throttle_correction"} <= set(rows[0])
    assert float(rows[0]["raw_throttle"]) == 0.9
    assert float(rows[0]["throttle_correction"]) == -0.4
