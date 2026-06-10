"""
scenario_metrics — scenario-specific verdict metrics that are *not* part of the
generic per-run catalogue (``campaign_metrics`` / docs/06). These are the custom
tokens that appear in a scenario's ``pass_criterion_per_run`` and have to be
computed from the per-step records before ``criterion_eval`` can score the run.

Currently implemented:
  * ``time_to_recovery_heading`` (SC-EDGE-01) — recovery time of the heading
    error after an initial-heading perturbation.
  * Frontier / out-of-ODD verdict metrics (the cage-efficacy study): the maximum
    lateral excursion, whether the run reached the road edge (the harm proxy),
    and whether the cage's emergency rule (C-05) fired. These drive the paired
    enforcement-vs-monitoring contrast that quantifies the cage's value.

Pure: per-step records + params in, scalars out; unit-tested without ROS.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence


def max_excursion_m(records: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Maximum absolute lateral offset ``max|ey|`` (m) reached over the run — how
    far out the vehicle got. None for an empty run."""
    if not records:
        return None
    return max(abs(float(r.get("ey", 0.0))) for r in records)


def emergency_triggered(records: Sequence[Dict[str, Any]]) -> bool:
    """Whether the cage latched a C-05 emergency at any step of the run."""
    return any(bool(r.get("emergency")) for r in records)


def road_edge_contact(records: Sequence[Dict[str, Any]], road_half_m: float) -> Optional[bool]:
    """Whether the vehicle reached the road edge (``max|ey| >= road_half_m``) — the
    harm proxy for the cage-efficacy contrast. Under enforcement the cage should
    keep this False (it stops/steers before the edge); under monitoring (no cage
    action) a frontier run is expected to reach the edge. None for an empty run."""
    mx = max_excursion_m(records)
    if mx is None:
        return None
    return mx >= road_half_m


def time_to_recovery_heading(
    records: Sequence[Dict[str, Any]],
    *,
    threshold_rad: float = 0.05,
    settle_s: float = 0.5,
    control_dt: float = 0.10,
) -> Optional[float]:
    """Seconds from run start until ``|epsi|`` first drops below
    ``threshold_rad`` *and stays* below it for ``settle_s`` — i.e. the heading is
    recovered and held, not just momentarily crossing the band. Returns the time
    at the start of that sustained interval.

    ``math.inf`` if the heading never recovers for a full settle window: a clause
    like ``time_to_recovery_heading < 2.0`` then evaluates to a real *fail*
    (``inf < 2.0`` is False) rather than the indeterminate that ``None`` would
    produce in ``criterion_eval``'s three-valued logic. ``None`` only for an
    empty run (no data at all).
    """
    n = len(records)
    if n == 0:
        return None
    settle_steps = max(1, int(round(settle_s / control_dt)))
    below = [abs(float(r.get("epsi", 0.0))) < threshold_rad for r in records]
    for i in range(n - settle_steps + 1):
        if all(below[i : i + settle_steps]):
            return i * control_dt
    return math.inf
