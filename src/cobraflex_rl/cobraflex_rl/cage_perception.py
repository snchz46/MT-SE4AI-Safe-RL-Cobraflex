"""
cage_perception — the cage's perception supervisor for track 'E' (D-40).

Composes, per control cycle, the three host-tested kernels around the CV
lane-estimator into the cage-facing contract:

* :class:`~cobraflex_rl.cv_lane_estimator.CvLaneEstimator` produces the lane
  estimate from the (possibly degraded) camera frame;
* :class:`~cobraflex_rl.perception_health.PerceptionHealthMonitor` (SR-013,
  H-11) judges loss — stale/dropped frame, low confidence, missing features;
* :class:`~cobraflex_rl.lane_plausibility.LanePlausibilityCheck` (SR-014,
  H-12) judges a *suspect* estimate — out-of-ODD geometry or a temporal jump.

The output is exactly what `SafetyCageNode.step` consumes: the cage `state`
built from the CV estimate (when there is a trustworthy one) and the
``perception_invalid`` boolean for C-05 Trigger 8. The cage itself never sees
the camera (camera-agnostic, docs/04 §C-05).

Pure logic (no ROS) — host-testable; used in-process by `gazebo_lane_env` and
by the ROS estimator node alike.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .cv_lane_estimator import (
    CvLaneEstimate,
    CvLaneEstimator,
)
from .lane_plausibility import LaneEstimate, LanePlausibilityCheck
from .perception_health import PerceptionHealthMonitor, PerceptionSample


@dataclass(frozen=True)
class CagePerceptionResult:
    """Per-cycle supervisor verdict.

    estimate:
        The CV lane estimate this cycle (``ok`` may be False).
    state_available:
        True when the estimate is usable as the cage state this cycle.
    perception_invalid:
        The C-05 Trigger 8 flag (latched persistence handled by the monitors'
        consecutive-cycle counters; the emergency latch itself is C-05's).
    health_reason / plausibility_reason:
        Diagnostic strings for the cycle log.
    """

    estimate: CvLaneEstimate
    state_available: bool
    perception_invalid: bool
    health_reason: str
    plausibility_reason: str


class CagePerceptionSupervisor:
    def __init__(
        self,
        estimator: Optional[CvLaneEstimator] = None,
        health: Optional[PerceptionHealthMonitor] = None,
        plausibility: Optional[LanePlausibilityCheck] = None,
    ) -> None:
        self.estimator = estimator or CvLaneEstimator()
        self.health = health or PerceptionHealthMonitor()
        self.plausibility = plausibility or LanePlausibilityCheck()

    def reset(self) -> None:
        """Per-episode reset (fresh persistence counters, no stale reference)."""
        self.health.reset()
        self.plausibility.reset()

    def update(
        self,
        frame_bgr: Optional[np.ndarray],
        *,
        frame_timestamp_s: float,
        now_s: float,
        speed_mps: float,
    ) -> CagePerceptionResult:
        """Run one cycle: estimate from ``frame_bgr`` (None = no frame arrived),
        then judge health (SR-013) and plausibility (SR-014)."""
        if frame_bgr is not None:
            estimate = self.estimator.estimate(frame_bgr)
        else:
            estimate = CvLaneEstimate(ok=False, reason="no_frame")

        sample = PerceptionSample(
            timestamp_s=frame_timestamp_s,
            frame_received=frame_bgr is not None,
            confidence=estimate.confidence,
            feature_count=estimate.feature_count if estimate.ok else 0,
        )
        health = self.health.update(sample, now_s=now_s)

        plaus_reason = "not_evaluated"
        plaus_reject = False
        state_available = False
        if estimate.ok:
            plaus = self.plausibility.update(
                LaneEstimate(
                    ey=estimate.ey,
                    heading=estimate.epsi,
                    lane_width=estimate.lane_width,
                    curvature=estimate.curvature,
                    timestamp_s=frame_timestamp_s,
                ),
                speed_mps=speed_mps,
                now_s=now_s,
            )
            plaus_reason = plaus.reason
            plaus_reject = plaus.reject
            state_available = plaus.plausible and health.valid

        return CagePerceptionResult(
            estimate=estimate,
            state_available=state_available,
            perception_invalid=bool(health.emergency or plaus_reject),
            health_reason=health.reason,
            plausibility_reason=plaus_reason,
        )
