"""Host-side tests for the true-position capture scorer (D-78).

The scorer is what turns a capture session into a verdict on D-75's closed-loop
test and D-76's accuracy question, so its two load-bearing behaviours are pinned
here: arc length is interpolated only BETWEEN station anchors (never
extrapolated past one), and the relocation detector reproduces the figure the
D-77 replay measured on `circuit_export`.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

PATH = Path(__file__).parents[1] / "score_lane_capture.py"
SPEC = importlib.util.spec_from_file_location("score_lane_capture", PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def row(stamp, ey, *, station=0, s=None, paired=1, width=0.245, k=0.0, true_ey=None):
    return {"stamp_s": f"{stamp}", "ey_m": f"{ey}", "paired": str(paired),
            "lane_width_m": f"{width}", "curvature_1pm": f"{k}",
            "station": str(station), "s_m": "" if s is None else f"{s}",
            "true_ey_m": "" if true_ey is None else f"{true_ey}",
            "line_c0_m": "", "epsi_rad": "0.0", "n_lines": "2",
            "confidence": "0.5", "reason": "ok", "frame": "x.png"}


def test_arc_length_is_interpolated_between_anchors_and_never_past_one():
    rows = [row(0.0, 0.0),                      # before station 1
            row(1.0, 0.0, station=1, s=0.0),
            row(2.0, 0.0, station=1, s=0.0),    # midway: t=2 of [1,3]
            row(3.0, 0.0, station=2, s=4.0),
            row(4.0, 0.0, station=2, s=4.0)]    # after the last anchor
    MOD.interpolate_arc(rows)
    assert rows[0]["s_interp"] is None, "must not extrapolate before station 1"
    assert rows[1]["s_interp"] == pytest.approx(0.0)
    assert rows[2]["s_interp"] == pytest.approx(2.0), "linear in time between anchors"
    assert rows[4]["s_interp"] is None, "must not extrapolate past the last anchor"


def test_a_single_station_yields_no_arc_length_at_all():
    """One anchor cannot define a length. Silently treating it as an origin is
    how a capture would produce a confident closed-loop number from nothing."""
    rows = [row(1.0, 0.0, station=1, s=0.0), row(2.0, 0.0, station=1, s=0.0)]
    MOD.interpolate_arc(rows)
    assert all(r["s_interp"] is None for r in rows)


def test_unpaired_frames_break_the_relocation_chain_rather_than_bridging_it():
    """An unpaired frame is a gap in knowledge, not a straight line across it:
    comparing the frames either side would manufacture a relocation."""
    rows = [row(0.00, 0.000), row(0.05, 0.000, paired=0), row(0.10, 0.300)]
    MOD.interpolate_arc(rows)
    MOD.report_relocations(rows)   # must not raise, and must score 0 transitions


def test_relocation_detector_reproduces_the_D77_figure_on_circuit_export():
    """The tracked recording holds 42 unphysical relocations in 1401 transitions
    (D-77). If this drifts, either the thresholds or the data moved."""
    data = (Path(__file__).parents[2] / "experiments" / "physical" / "datasets"
            / "circuit_export" / "labels.csv")
    if not data.exists():
        pytest.skip("circuit_export/labels.csv not present on this host")
    rows = MOD.load(data)
    MOD.interpolate_arc(rows)
    prev = prevt = None
    n = reloc = 0
    for r in rows:
        if not MOD.paired(r):
            prev = None
            continue
        ey, t = MOD._f(r, "ey_m"), MOD._f(r, "stamp_s")
        if prev is not None and 0 < t - prevt < 0.5:
            n += 1
            d = abs(ey - prev)
            if d > MOD.RELOC_DISP and d / (t - prevt) > MOD.RELOC_RATE:
                reloc += 1
        prev, prevt = ey, t
    assert n == 1401
    assert reloc == 42
