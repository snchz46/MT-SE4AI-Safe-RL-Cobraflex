"""
cv_lane_estimator — the cage's deterministic classical-CV lane estimator (D-40).

Track 'E': the safety cage's state (`ey`/`epsi`/lane width/curvature) comes from
this dedicated, *deterministic* vision pipeline — not from privileged ground
truth (impossible on a real road, D-40 supersedes D-39) and not from the
policy's CNN (would couple the safety monitor to the learned controller, A2).
Every stage is classical and inspectable:

1. **White mask** — HSV threshold (low saturation, high value), the same proven
   recipe as `cobraflex.lane_keeper_gazebo_node`.
2. **Row scan** — sample image rows between a near and a far look-ahead
   distance; per row, white runs whose metric width is plausible for a lane
   marking become candidate line points (pixel → ground via
   :mod:`cobraflex_rl.camera_geometry`, closed-form for the pitch-only mount).
3. **Line clustering** — candidates cluster by lateral intercept; each cluster
   gets a least-squares line fit ``Y = a + b·X`` in the ground frame.
4. **Lane selection** — among adjacent line pairs with a plausible separation,
   pick the pair whose centre is nearest the vehicle (the driven lane).
5. **State** — ``ey`` (+left, vehicle relative to lane centre), ``epsi``
   (vehicle yaw minus lane heading), lane width, curvature (from a quadratic
   fit of the lane-centre points when the look-ahead span allows), plus the
   ``confidence`` / ``feature_count`` that feed the SR-013 health monitor and
   the :class:`~cobraflex_rl.lane_plausibility.LanePlausibilityCheck` (SR-014).

Sign conventions match `PolylineTracker` (the sim oracle that validates this
estimator, D-40): ``ey`` + = vehicle left of lane centre; ``epsi`` + = vehicle
yawed left of the lane direction; curvature + = left bend.

Pure numpy + OpenCV (`cv2`) — host-testable without ROS; the synthetic-frame
unit tests in ``policy/tests/test_cv_lane_estimator.py`` render known lane
geometries through the same camera model and verify recovery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

try:  # cv2 only needed for BGR→HSV; the rest is numpy
    import cv2
except ImportError:  # pragma: no cover - exercised only on hosts without cv2
    cv2 = None

from .camera_geometry import CameraModel


@dataclass(frozen=True)
class CvLaneEstimatorConfig:
    """Tunables of the deterministic pipeline. Defaults mirror the proven
    `lane_keeper_gazebo_node` thresholds and the ODD-1 lane geometry."""

    # Mask thresholds are TIGHTER than lane_keeper_gazebo_node's (70/150):
    # the pale grass beside the road has S≈48, V≈176 and passed that mask,
    # merging the road-edge line with the grass at far rows and biasing
    # ey/epsi (found in the GE2 oracle validation, see
    # experiments/sim/runs/cv_estimator_val_*). Painted lines are S≈0-15,
    # V≈200-240.
    white_sat_max: int = 30          # HSV S ≤ → white candidate
    white_val_min: int = 170         # HSV V ≥ → white candidate
    near_distance_m: float = 0.15    # row scan: nearest ground distance
    far_distance_m: float = 1.00     # row scan: farthest ground distance
    n_scan_rows: int = 24            # rows sampled between near and far
    min_marking_width_m: float = 0.004   # white run plausible as a line marking
    max_marking_width_m: float = 0.10
    cluster_tol_m: float = 0.08      # lateral intercept tolerance per cluster
    min_points_per_line: int = 4     # cluster size to accept a line fit
    lane_width_nominal_m: float = 0.245  # ODD-1 lane width
    lane_width_tol_m: float = 0.10   # accepted pair separation = nominal ± tol
    min_rows_for_curvature: int = 8  # quadratic fit needs enough X span
    max_abs_y_m: float = 1.5         # discard candidates far off to the side


@dataclass(frozen=True)
class CvLaneEstimate:
    """One frame's estimate. ``ok`` False ⇒ no usable lane pair this frame
    (the numeric fields then hold zeros and must not be consumed)."""

    ok: bool
    ey: float = 0.0
    epsi: float = 0.0
    lane_width: float = 0.0
    curvature: float = 0.0
    confidence: float = 0.0
    feature_count: int = 0
    n_lines: int = 0
    reason: str = ""
    # Per-line ground-frame fits (a, b) of Y = a + b·X, for debugging/overlay.
    line_fits: Tuple[Tuple[float, float], ...] = field(default_factory=tuple)


class CvLaneEstimator:
    def __init__(
        self,
        camera: Optional[CameraModel] = None,
        config: Optional[CvLaneEstimatorConfig] = None,
    ) -> None:
        self.camera = camera or CameraModel()
        self.config = config or CvLaneEstimatorConfig()
        if self.config.far_distance_m <= self.config.near_distance_m:
            raise ValueError("far_distance_m must exceed near_distance_m")
        # Precompute the scan rows (image v) for the configured look-ahead band.
        v_near = self.camera.distance_to_row(self.config.near_distance_m)
        v_far = self.camera.distance_to_row(self.config.far_distance_m)
        v_lo = max(0.0, min(v_near, self.camera.height_px - 1.0))
        v_hi = max(0.0, min(v_far, self.camera.height_px - 1.0))
        rows = np.linspace(v_lo, v_hi, self.config.n_scan_rows)
        self._scan_rows = np.unique(np.round(rows).astype(int))

    # ------------------------------------------------------------------ mask
    def white_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Binary mask of white-marking pixels (uint8 0/255)."""
        if frame_bgr.ndim == 2:  # already grayscale: value-only threshold
            return ((frame_bgr >= self.config.white_val_min) * 255).astype(np.uint8)
        if cv2 is not None:
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            sat, val = hsv[:, :, 1], hsv[:, :, 2]
        else:  # numpy fallback (max/min channel approximation of S and V)
            f = frame_bgr.astype(np.float32)
            val = f.max(axis=2)
            cmin = f.min(axis=2)
            with np.errstate(divide="ignore", invalid="ignore"):
                sat = np.where(val > 0, (val - cmin) / val * 255.0, 0.0)
            val = val.astype(np.uint8)
            sat = sat.astype(np.uint8)
        mask = (sat <= self.config.white_sat_max) & (val >= self.config.white_val_min)
        return (mask * 255).astype(np.uint8)

    # ------------------------------------------------------- candidate points
    def _row_candidates(self, mask: np.ndarray) -> List[Tuple[float, float, int]]:
        """White-run centres per scan row → ground points (X, Y, row_v)."""
        cfg = self.config
        cam = self.camera
        points: List[Tuple[float, float, int]] = []
        h, w = mask.shape[:2]
        for v in self._scan_rows:
            if not 0 <= v < h:
                continue
            row = mask[v] > 0
            if not row.any():
                continue
            # Run-length encode the boolean row.
            padded = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
            starts = np.flatnonzero(padded == 1)
            ends = np.flatnonzero(padded == -1)
            res = cam.lateral_resolution(float(v))  # m per pixel at this row
            for s, e in zip(starts, ends):
                width_m = (e - s) * res
                if not cfg.min_marking_width_m <= width_m <= cfg.max_marking_width_m:
                    continue
                u_center = 0.5 * (s + e - 1)
                x, y = cam.pixel_to_ground(u_center, float(v))
                if abs(y) > cfg.max_abs_y_m:
                    continue
                points.append((x, y, int(v)))
        return points

    # ------------------------------------------------------------- clustering
    @staticmethod
    def _fit_cluster(pts: List[Tuple[float, float]]) -> Tuple[float, float, float]:
        """Least-squares polynomial Y(X) = c0 + c1·X + c2·X² for one cluster.

        Degree adapts to the evidence: quadratic once the cluster spans enough
        look-ahead to constrain curvature (the oval's KAPPA_MAX = 1.25 1/m
        bends a line by ~0.9 m over the 1.2 m scan band — a linear model both
        misses the curvature and biases the intercept), linear for short
        spans, constant for near-degenerate ones.
        """
        xs = np.array([p[0] for p in pts])
        ys = np.array([p[1] for p in pts])
        span = float(xs.ptp()) if len(xs) > 1 else 0.0
        if len(pts) >= 5 and span > 0.25:
            c2, c1, c0 = np.polyfit(xs, ys, 2)
            return float(c0), float(c1), float(c2)
        if len(pts) >= 2 and span > 1e-6:
            c1, c0 = np.polyfit(xs, ys, 1)
            return float(c0), float(c1), 0.0
        return float(ys.mean()), 0.0, 0.0

    def _cluster_lines(
        self, points: Sequence[Tuple[float, float, int]]
    ) -> List[dict]:
        """Greedy near-to-far clustering with polynomial prediction.

        Each cluster keeps a running fit ``Y = c0 + c1·X + c2·X²``; a candidate
        joins the cluster whose prediction at its X is nearest (within
        ``cluster_tol_m``). Near-to-far ordering grounds each cluster on the
        most metrically reliable rows before extrapolating outward.
        """
        cfg = self.config
        clusters: List[dict] = []  # each: {"pts": [...], "c0","c1","c2"}
        for x, y, _ in sorted(points, key=lambda p: p[0]):
            best = None
            best_d = cfg.cluster_tol_m
            for cl in clusters:
                y_pred = cl["c0"] + cl["c1"] * x + cl["c2"] * x * x
                d = abs(y - y_pred)
                if d < best_d:
                    best, best_d = cl, d
            if best is None:
                clusters.append({"pts": [(x, y)], "c0": y, "c1": 0.0, "c2": 0.0})
                continue
            best["pts"].append((x, y))
            best["c0"], best["c1"], best["c2"] = self._fit_cluster(best["pts"])
        return [cl for cl in clusters if len(cl["pts"]) >= cfg.min_points_per_line]

    # ------------------------------------------------------------------ main
    def estimate(self, frame_bgr: np.ndarray) -> CvLaneEstimate:
        cfg = self.config
        mask = self.white_mask(frame_bgr)
        points = self._row_candidates(mask)
        if not points:
            return CvLaneEstimate(ok=False, reason="no_line_features")

        lines = self._cluster_lines(points)
        if len(lines) < 2:
            return CvLaneEstimate(
                ok=False,
                feature_count=len(points),
                n_lines=len(lines),
                reason="fewer_than_two_lines",
            )

        # Order lines right→left by intercept (Y at the vehicle, X=0);
        # examine adjacent pairs for a plausible lane.
        lines.sort(key=lambda cl: cl["c0"])
        best_pair = None
        best_center = None
        for right, left in zip(lines[:-1], lines[1:]):
            sep = left["c0"] - right["c0"]
            if abs(sep - cfg.lane_width_nominal_m) > cfg.lane_width_tol_m:
                continue
            center = 0.5 * (left["c0"] + right["c0"])
            if best_center is None or abs(center) < abs(best_center):
                best_pair = (right, left)
                best_center = center
        if best_pair is None:
            return CvLaneEstimate(
                ok=False,
                feature_count=len(points),
                n_lines=len(lines),
                reason="no_plausible_lane_pair",
            )

        # Lane-centre polynomial = mean of the two line fits; the state is
        # read off its coefficients at the vehicle (X=0).
        right, left = best_pair
        c0 = 0.5 * (left["c0"] + right["c0"])
        c1 = 0.5 * (left["c1"] + right["c1"])
        c2 = 0.5 * (left["c2"] + right["c2"])
        heading = float(np.arctan(c1))
        ey = -float(c0)
        epsi = -heading
        lane_width = float((left["c0"] - right["c0"]) * np.cos(heading))

        pair_pts = right["pts"] + left["pts"]
        xs = np.array([p[0] for p in pair_pts])
        n_rows_spanned = len(np.unique(np.round(xs, 3)))
        if n_rows_spanned >= cfg.min_rows_for_curvature and float(xs.ptp()) > 0.2:
            curvature = float(2.0 * c2)
        else:
            curvature = 0.0  # not enough span to trust a curvature estimate

        n_pair_points = len(pair_pts)
        confidence = min(1.0, n_pair_points / (2.0 * len(self._scan_rows)))
        return CvLaneEstimate(
            ok=True,
            ey=ey,
            epsi=epsi,
            lane_width=lane_width,
            curvature=curvature,
            confidence=float(confidence),
            feature_count=n_pair_points,
            n_lines=len(lines),
            reason="ok",
            line_fits=tuple((cl["c0"], cl["c1"]) for cl in lines),
        )
