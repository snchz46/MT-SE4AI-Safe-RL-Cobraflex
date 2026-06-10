"""
Unit tests for cobraflex_rl.polyline_tracker.pose_at_arclength — the arc-length
spawn helper the F4 scenario executor uses to place the vehicle at a scenario's
``track.start_s_m`` (and optional lateral offset) instead of always at the first
centerline point. Needs numpy (the tracker is numpy-backed).
"""

import math
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

np = pytest.importorskip("numpy")

from cobraflex_rl.polyline_tracker import PolylineTracker  # noqa: E402


def _straight():
    # 3 m straight along +x, 1 m segments.
    return PolylineTracker(np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]))


def _unit_square():
    # Closed 4x1 m square loop (perimeter 4 m), CCW from origin.
    return PolylineTracker(
        np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]])
    )


def test_arclength_zero_is_first_point():
    x, y, heading = _straight().pose_at_arclength(0.0)
    assert (x, y) == pytest.approx((0.0, 0.0))
    assert heading == pytest.approx(0.0)


def test_arclength_interpolates_within_segment():
    x, y, heading = _straight().pose_at_arclength(1.5)
    assert (x, y) == pytest.approx((1.5, 0.0))
    assert heading == pytest.approx(0.0)  # tangent along +x


def test_open_polyline_clamps_overrun():
    # s beyond the 3 m length clamps to the final point, no wrap.
    x, y, _ = _straight().pose_at_arclength(10.0)
    assert (x, y) == pytest.approx((3.0, 0.0))


def test_closed_polyline_wraps_modulo_perimeter():
    sq = _unit_square()
    # s = 4.5 wraps to s = 0.5 → halfway up the first (bottom) edge.
    x, y, heading = sq.pose_at_arclength(4.5)
    assert (x, y) == pytest.approx((0.5, 0.0))
    assert heading == pytest.approx(0.0)


def test_closed_polyline_heading_turns_with_segment():
    sq = _unit_square()
    # s = 1.5 is on the right edge (x=1, going +y) → heading +pi/2.
    x, y, heading = sq.pose_at_arclength(1.5)
    assert (x, y) == pytest.approx((1.0, 0.5))
    assert heading == pytest.approx(math.pi / 2)


def test_lateral_offset_shifts_along_left_normal():
    # On the bottom edge (heading +x), the left normal is +y.
    x, y, _ = _unit_square().pose_at_arclength(0.5, lateral_offset=0.2)
    assert (x, y) == pytest.approx((0.5, 0.2))
    # Negative offset shifts right (−y).
    x2, y2, _ = _unit_square().pose_at_arclength(0.5, lateral_offset=-0.2)
    assert (x2, y2) == pytest.approx((0.5, -0.2))
