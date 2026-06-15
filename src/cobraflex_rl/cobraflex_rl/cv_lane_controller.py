"""
cv_lane_controller — the logical (non-learned) camera lane-keeper.

Shared by the deployment node (cobraflex/lane_keeper_gazebo_node.py) and the
scored evaluation (cobraflex_rl/eval_cv_controller.py) so both drive with the
*identical* control law — the single source of truth for the RL baseline.

It is the fair, classical counterpart to the RL camera agent: it reads the same
deterministic CV lane estimator the safety cage uses (`CvLaneEstimator`, D-43),
which projects the white markings to the ground plane with the calibrated
camera model and returns metric ``ey``/``epsi``/``curvature`` (validated to
~mm vs the sim oracle), and closes a PD loop with curvature feedforward:

    steer = -(kp·ey + kd·epsi) + kff·(v·κ)

Sign conventions (shared with PolylineTracker): ey + = left of lane centre,
epsi + = yawed left, κ + = left bend; Twist.angular.z + = turn left.

This replaces the original histogram pure-P controller, whose uncalibrated
"lane centre = image centre" set-point could not hold the lane above ~0.1 m/s
(it carried a perspective-dependent steady-state offset and understeered the
curves). On the nominal oval at 0.2 m/s the CV+PD law tracks to RMSE ~10 mm
(req < 50 mm), on par with the RL agent — a like-for-like reference.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np

from .cv_lane_estimator import CvLaneEstimator

# Tunable gains; recorded in each run's metadata so the law that drove it is
# exactly reproducible.
CONTROLLER_DEFAULTS: Dict[str, float] = {
    "kp_ey": 6.0,        # proportional on lateral offset ey [m] (+left)
    "kd_epsi": 1.6,      # on heading error epsi [rad] (+yawed left)
    "kff_curv": 1.0,     # curvature feedforward gain (×speed): yaw_ff = kff·v·κ
    "max_angular_z": 0.90,
}


class CVLaneController:
    """Calibrated-CV + PD lane-keeper. ``compute(frame_bgr) -> (angular_z, detected)``.

    ``angular_z`` is in [-max_angular_z, max_angular_z]; the env / node publishes
    it as Twist.angular.z. No usable lane this frame → (0.0, False) (the caller
    holds the cruise speed or stops, as it sees fit).
    """

    def __init__(self, speed: float = 0.2, estimator: Optional[CvLaneEstimator] = None,
                 **params: Any) -> None:
        self.p = {**CONTROLLER_DEFAULTS, **params}
        self.speed = float(speed)
        self.estimator = estimator or CvLaneEstimator()
        self.dbg: Dict[str, Any] = {}

    def compute(self, frame_bgr: Optional[np.ndarray]) -> Tuple[float, bool]:
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            self.dbg = {"ok": False, "reason": "no_frame"}
            return 0.0, False
        est = self.estimator.estimate(frame_bgr)
        if not est.ok:
            self.dbg = {"ok": False, "reason": est.reason}
            return 0.0, False
        p = self.p
        ff = float(p["kff_curv"]) * self.speed * float(est.curvature)
        angular = -(float(p["kp_ey"]) * float(est.ey)
                    + float(p["kd_epsi"]) * float(est.epsi)) + ff
        m = float(p["max_angular_z"])
        self.dbg = {"ok": True, "ey": round(est.ey, 4), "epsi": round(est.epsi, 4),
                    "kappa": round(est.curvature, 3), "ff": round(ff, 3),
                    "nL": est.n_lines}
        return float(np.clip(angular, -m, m)), True
