"""
scenario_metrics — scenario-specific verdict metrics that are *not* part of the
generic per-run catalogue (``campaign_metrics`` / docs/06). These are the custom
tokens that appear in a scenario's ``pass_criterion_per_run`` and have to be
computed from the per-step records before ``criterion_eval`` can score the run.

Currently implemented:
  * ``time_to_recovery_heading`` (SC-EDGE-01) — recovery time of the heading
    error after an initial-heading perturbation.

Pure: per-step records + params in, scalars out; unit-tested without ROS.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence


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
