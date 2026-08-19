"""
Unit tests for tools/sim2real_probe.py — the offline sim-to-real transfer gate
(M-7/D-71). Pure logic only: scoring, label parsing and the verdict. Loading a
checkpoint or decoding frames is exercised by running the tool, not here.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from sim2real_probe import (  # noqa: E402
    _read_labels,
    _score,
    _sim_labels,
    verdict_for,
)

# The two arms actually measured on 18-19.08.2026. The gate must separate them.
SIM_CONTROL = {
    "swing": 0.363, "bias": 0.1037, "bias_over_swing": 0.29,
    "right_fraction": 0.486, "sign_correct": True,
}
TRUNK_ON_REAL = {
    "swing": 0.097, "bias": 0.1425, "bias_over_swing": 1.47,
    "right_fraction": 0.008, "sign_correct": True,
}


def test_score_recovers_a_synthetic_lane_response():
    ey = np.linspace(-100.0, 100.0, 400)
    steer = -0.002 * ey + 0.05
    s = _score(ey, steer)
    assert s["sign_correct"]
    assert s["slope_per_mm"] == pytest.approx(-0.002, abs=1e-6)
    assert s["bias"] == pytest.approx(0.05, abs=1e-6)
    # swing spans the 2nd-98th percentile of ey, not its full range
    assert s["swing"] == pytest.approx(0.002 * (ey[-1] - ey[0]) * 0.96, rel=0.02)
    assert s["r_squared"] == pytest.approx(1.0, abs=1e-9)


def test_score_flags_a_wrong_sign_response():
    ey = np.linspace(-100.0, 100.0, 400)
    s = _score(ey, +0.002 * ey)          # steers left when already left of centre
    assert not s["sign_correct"]


def test_score_reports_a_frozen_output_as_zero_swing():
    ey = np.linspace(-100.0, 100.0, 400)
    s = _score(ey, np.full_like(ey, 0.12))
    assert s["swing"] == pytest.approx(0.0, abs=1e-9)
    assert s["bias_over_swing"] == float("inf")


def test_verdict_passes_the_sim_control_arm():
    verdict, reasons, _ = verdict_for(SIM_CONTROL, SIM_CONTROL)
    assert verdict == "PASS", reasons


def test_verdict_blocks_the_trunk_on_real_frames():
    """The regression that matters: the checkpoint that did not drive on
    18.08.2026 must be blocked from recorded frames alone."""
    verdict, reasons, retention = verdict_for(TRUNK_ON_REAL, SIM_CONTROL)
    assert verdict == "BLOCKED"
    assert retention == pytest.approx(0.267, abs=0.01)
    assert len(reasons) == 3          # weak swing, dominant bias, never turns right


def test_verdict_blocks_a_wrong_sign_response_that_is_otherwise_healthy():
    arm = dict(SIM_CONTROL, sign_correct=False)
    verdict, reasons, _ = verdict_for(arm, SIM_CONTROL)
    assert verdict == "BLOCKED"
    assert any("WRONG SIGN" in r for r in reasons)


def test_verdict_falls_back_to_an_absolute_floor_without_a_sim_arm():
    verdict, reasons, retention = verdict_for(TRUNK_ON_REAL, None)
    assert verdict == "BLOCKED" and retention is None
    assert any("absolute floor" in r for r in reasons)


def test_read_labels_keeps_only_measured_offsets(tmp_path):
    """Single-line fallbacks infer ey from the running width estimate rather
    than measuring it; regressing steering against them would fit a partly
    invented label."""
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "frame,ey_m,paired,reason\n"
        "a.png,0.012,1,ok\n"
        "b.png,-0.030,1,single_line\n"
        "c.png,0.000,0,no_plausible_lane_pair\n"
        "d.png,-0.045,1,ok\n"
    )
    labels = _read_labels(csv_path)
    assert set(labels) == {"a.png", "d.png"}
    assert labels["d.png"] == pytest.approx(-45.0)


def test_sim_labels_parse_the_pose_from_the_filename():
    names = [
        Path("clean_0.0_s12.00_ey+0.060_dpsi+0.00.png"),
        Path("clean_0.0_s12.00_ey-0.060_dpsi+0.10.png"),
        Path("not_a_probe_frame.png"),
    ]
    both = _sim_labels(names, heading_zero_only=False)
    assert len(both) == 2 and both["clean_0.0_s12.00_ey+0.060_dpsi+0.00.png"] == 60.0
    only_straight = _sim_labels(names, heading_zero_only=True)
    assert list(only_straight) == ["clean_0.0_s12.00_ey+0.060_dpsi+0.00.png"]
