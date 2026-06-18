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


def _dense_straight(length=5.0, step=0.05):
    # Fine-grained straight along +x (mirrors the dense complex_b centerline,
    # ~0.05 m segments) so the progress cap has sub-segment granularity to act on.
    n = int(round(length / step)) + 1
    return PolylineTracker(np.array([[i * step, 0.0] for i in range(n)]))


def test_progress_bound_is_opt_in_default_none():
    # Default tracker (the convex F-track oval path) is unbounded — no behaviour
    # change unless max_advance_m is set.
    assert _straight().max_advance_m is None


def test_max_advance_makes_projection_lag_a_fast_query():
    # A query racing forward faster than the cap (the agent driving straight off
    # a curve) must leave the projection behind, so the Euclidean gap grows and
    # off-road can fire — instead of the projection chasing onto a folded-back
    # section and collapsing ey.
    free = _dense_straight()                       # unbounded (legacy)
    capped = _dense_straight()
    capped.max_advance_m = 0.02                     # tighter than the 0.05 m segment
    free.track(0.0, 0.0, 0.0)
    capped.track(0.0, 0.0, 0.0)
    sf = sc = 0.0
    for k in range(1, 16):
        q = 0.10 * k                                # would chase >1 segment/step
        sf = free.track(q, 0.0, 0.0).s
        sc = capped.track(q, 0.0, 0.0).s
    assert sf == pytest.approx(1.5, abs=0.1)        # unbounded chases the query
    assert sc < sf - 0.5                            # capped lags (chase prevented)


def test_max_advance_leaves_legitimate_cruise_unlagged():
    # One segment per step is legitimate cruise; the cap must NOT introduce lag
    # (else it would manufacture false off-road terminations in-lane).
    free = _dense_straight()
    capped = _dense_straight()
    capped.max_advance_m = 0.02
    free.track(0.0, 0.0, 0.0)
    capped.track(0.0, 0.0, 0.0)
    sf = sc = 0.0
    for k in range(1, 16):
        q = 0.05 * k                                # one 0.05 m segment per step
        sf = free.track(q, 0.0, 0.0).s
        sc = capped.track(q, 0.0, 0.0).s
    assert sc == pytest.approx(sf, abs=1e-9)        # no lag, no false trigger


def test_reset_tracking_clears_progress_state():
    capped = _dense_straight()
    capped.max_advance_m = 0.02
    capped.track(0.0, 0.0, 0.0)
    capped.track(0.04, 0.0, 0.0)
    assert capped._prev_s is not None
    capped.reset_tracking()
    assert capped._prev_s is None


def test_distance_to_is_global_and_stateless():
    tr = _dense_straight()                      # straight along +x, y=0, x in [0,5]
    assert tr.distance_to(2.5, 0.3) == pytest.approx(0.3, abs=1e-6)   # perpendicular
    assert tr.distance_to(6.0, 0.0) == pytest.approx(1.0, abs=1e-6)   # clamps past the end
    tr.track(0.0, 0.0, 0.0)                     # prior tracking must not bias it
    assert tr.distance_to(2.5, 0.3) == pytest.approx(0.3, abs=1e-6)


def test_distance_to_finds_globally_nearest_on_folded_path():
    # A path that folds back on itself (two rows 0.2 m apart): off-road must be
    # judged against the *nearest* road point, not the stateful tracked segment.
    pts = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 0.2], [0.0, 0.2]])
    tr = PolylineTracker(pts)
    tr.track(0.0, 0.0, 0.0)                     # prime on the bottom row
    assert tr.distance_to(0.5, 0.15) == pytest.approx(0.05, abs=1e-6)  # near the top row
