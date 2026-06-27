"""
cv_lane_estimator — the cage's deterministic classical-CV lane estimator (D-43).

Track 'E': the safety cage's state (`ey`/`epsi`/lane width/curvature) comes from
this dedicated, *deterministic* vision pipeline — not from privileged ground
truth (impossible on a real road, D-43 supersedes D-42) and not from the
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
estimator, D-43): ``ey`` + = vehicle left of lane centre; ``epsi`` + = vehicle
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

    # Saturation cap is TIGHTER than lane_keeper_gazebo_node's 70: the pale
    # grass beside the road has S≈48, V≈176 and passed that mask, merging the
    # road-edge line with the grass at far rows and biasing ey/epsi (found in
    # the GE2 oracle validation, experiments/sim/runs/cv_estimator_val_*).
    # Painted lines are S≈0-15, V≈200-240. The vegetation-hue exclusion below
    # covers the glare case where wash-out drives the grass's S under the cap.
    white_sat_max: int = 30          # HSV S ≤ → white candidate
    white_val_min: int = 150         # HSV V ≥ → white candidate
    # Vegetation exclusion: pixels with a green hue and at least this much
    # saturation are never line candidates, whatever their brightness.
    vegetation_hue_range: tuple = (35, 85)   # OpenCV H in [0, 179]
    vegetation_sat_min: int = 8
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
    # Heading (epsi) is read from a *near-field* secant over X in
    # [near_distance_m, near_distance_m + heading_window_m], curvature-corrected
    # to the slope at the vehicle (see CvLaneEstimator._near_field_slope). The
    # full-band fit's slope-at-vehicle is unusable on a tight circuit (complex_b,
    # r≈0.26 m) where the lane bends ~190° across the 0.15–1.0 m band; the near
    # secant alone still over-reads by curvature × window-centroid (a centred car
    # on the oval curve read ~26° off, tripping a false C-02/C-05 stop), so the
    # 2·c2 curvature term is subtracted. Curvature (also the feedforward term)
    # uses the full-band quadratic c2. 0.0 disables → legacy full-band slope.
    # 0.15 (short): the heading secant must see only the locally-straight stretch
    # in front of the vehicle. At the oval-curve apex the lane is flat for
    # X < ~0.35 m and bends hard only beyond; a longer window folds that bend in
    # and pushed |cv_epsi| past C-02's theta_max (a false emergency while the car
    # tracked to mm). Swept on the cv_ctrl_eval_20260618T182017Z apex frames:
    # 0.15 keeps |cv_epsi| ≤ 0.31, i.e. 0.13 rad under theta_max (0.4363).
    heading_window_m: float = 0.15
    # Single-line fallback (mirrors the proven lane_keeper_gazebo_node
    # single-side mode): when no plausible pair exists, infer the lane centre
    # from the nearest single line + the running lane-width estimate, at
    # halved confidence. In the tight oval curves the dashed separator drops
    # out of the scan band while the solid outer edge survives; without the
    # fallback those stretches read as perception loss.
    single_line_fallback: bool = True
    single_line_confidence_scale: float = 0.5
    # Conservative lane selection (D-48): when two plausible lane pairs straddle
    # the vehicle with opposite-sign centres (a neighbouring-lane line forms a
    # competing pair as the vehicle departs its lane), pick the larger-offset
    # interpretation instead of the nearest-centre one, to counter the SC-EDGE-02
    # H-12 under-read. **DEFAULT OFF (reverted, D-48):** this single-frame rule
    # cannot distinguish a genuinely off-centre vehicle from a *centred* one viewed
    # under a small heading error (the latter splits its lines into the same
    # opposite-sign pairs). It fires a spurious C-01/C-05 emergency whenever a
    # centred/recovering/curving vehicle's heading passes through small angles —
    # confirmed in closed loop (SC-EDGE-01: emergency at step 8 vs V1's clean 150
    # steps; SC-NOM-02 curve regressed). A heading gate only relocated the false
    # trigger. No robust single-frame fix exists; a real fix needs temporal lane
    # tracking (which still would not fix the SC-EDGE-02 *spawn* frame). Kept True-
    # capable only for the opt-in regression tests / future work.
    conservative_lane_selection: bool = False
    # The surviving line must sit roughly half a lane to one side; beyond
    # this slack the side assignment is too ambiguous to trust (H-12 risk —
    # the plausibility temporal check is the backstop).
    single_line_side_slack_m: float = 0.12


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
    # Lane-centre polynomial (c0, c1, c2) of Y(X) = c0 + c1·X + c2·X² in the
    # ground frame (+left). Evaluated *within* the observed look-ahead band it is
    # robust even when the individual coefficients are unstable on a tight curve
    # (they are correlated; the fitted curve stays put, only X=0 extrapolation
    # and the bare c2 swing). The pure-pursuit controller reads it to aim at the
    # lane centre at a look-ahead distance. ey = -c0.
    center_coeffs: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    # Per-line ground-frame fits (a, b) of Y = a + b·X, for debugging/overlay.
    line_fits: Tuple[Tuple[float, float], ...] = field(default_factory=tuple)


class CvLaneEstimator:
    """Deterministic CV lane estimator (D-43): camera frame → CvLaneEstimate.

    Classical pipeline, no learning: white-marking mask → per-scan-row line
    candidates projected to the ground plane → greedy polynomial clustering →
    plausible lane-pair selection (single-line fallback). Stateful only in the
    running lane-width EMA used by the fallback.
    """

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
        # Running lane-width estimate for the single-line fallback, updated
        # whenever a full pair is found (EMA, lane_keeper precedent).
        self._lane_width_ema = float(self.config.lane_width_nominal_m)
        # Debug-only: pixel (u, v) of the per-row white-run centres accepted as
        # candidates this frame. Populated by _row_candidates, read by the lane
        # keeper's debug overlay; does not affect the estimate.
        self.debug_candidates_px: List[Tuple[int, int]] = []

    # ------------------------------------------------------------------ mask
    def white_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Binary mask of white-marking pixels (uint8 0/255)."""
        if frame_bgr.ndim == 2:  # already grayscale: value-only threshold
            return ((frame_bgr >= self.config.white_val_min) * 255).astype(np.uint8)
        if cv2 is not None:
            hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
            hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        else:  # numpy fallback (max/min channel approximation of S and V)
            f = frame_bgr.astype(np.float32)
            val = f.max(axis=2)
            cmin = f.min(axis=2)
            with np.errstate(divide="ignore", invalid="ignore"):
                sat = np.where(val > 0, (val - cmin) / val * 255.0, 0.0)
            val = val.astype(np.uint8)
            sat = sat.astype(np.uint8)
            hue = np.zeros_like(sat)  # fallback path skips the hue exclusion
        mask = (sat <= self.config.white_sat_max) & (val >= self.config.white_val_min)
        # Vegetation exclusion: under glare wash-out the grass's saturation
        # drops below white_sat_max, but as long as any saturation survives the
        # hue still says "green" — never a painted line.
        h_lo, h_hi = self.config.vegetation_hue_range
        mask &= ~((hue >= h_lo) & (hue <= h_hi) & (sat >= self.config.vegetation_sat_min))
        return (mask * 255).astype(np.uint8)

    # ------------------------------------------------------- candidate points
    def _row_candidates(self, mask: np.ndarray) -> List[Tuple[float, float, int]]:
        """White-run centres per scan row → ground points (X, Y, row_v)."""
        cfg = self.config
        cam = self.camera
        points: List[Tuple[float, float, int]] = []
        self.debug_candidates_px = []
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
                self.debug_candidates_px.append((int(round(u_center)), int(v)))
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
        # np.ptp(xs), not xs.ptp(): the ndarray method was removed in NumPy 2.0
        # and this module must run on both the Ubuntu host (1.x) and newer envs.
        span = float(np.ptp(xs)) if len(xs) > 1 else 0.0
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

    def _near_field_slope(self, right: dict, left: dict, full_band_slope: float) -> float:
        """Lane-centre heading slope *at the vehicle* from a short near-window
        **linear** secant.

        Each line is refit linearly over X in ``[near_distance_m,
        near_distance_m + heading_window_m]`` (a short 0.15 m band) and the two
        slopes are averaged. The window is deliberately short — shorter than the
        distance at which the oval-curve lane starts to bend in view — so the fit
        sees only the locally-straight stretch right in front of the vehicle and
        reports its true heading. This was tuned on the dumped failure frames
        (``cv_ctrl_eval_20260618T182017Z``), where at the curve apex both lines
        are flat for X < ~0.35 m and bend hard only beyond it: a longer window
        (or a quadratic over it) folds that far bend into the slope and drove
        ``cv_epsi`` past C-02's theta_max (true heading ≈ 0), latching a false
        emergency. A quadratic over the long scan is worse still — the far points
        whipsaw c0/c1/c2 together.

        On a *uniformly* curved lane the short secant carries a small, bounded
        arc bias (≈ curvature × window-centroid, well under theta_max); on the
        real circuit the near band is locally straight so even that is negligible.
        Falls back to the full-band slope when the window is disabled
        (``heading_window_m <= 0``) or no line has enough near points.
        """
        cfg = self.config
        if cfg.heading_window_m <= 0.0:
            return full_band_slope
        x_max = cfg.near_distance_m + cfg.heading_window_m
        slopes: List[float] = []
        for line in (right, left):
            near = [(x, y) for (x, y) in line["pts"] if x <= x_max]
            if len(near) < 2:
                continue
            xs = np.array([p[0] for p in near])
            ys = np.array([p[1] for p in near])
            if float(np.ptp(xs)) <= 1e-6:
                continue
            slopes.append(float(np.polyfit(xs, ys, 1)[0]))
        if not slopes:
            return full_band_slope
        return float(np.mean(slopes))

    # ------------------------------------------------------------------ main
    def estimate(self, frame_bgr: np.ndarray) -> CvLaneEstimate:
        """One frame → lane estimate (``ok=False`` with a reason when no lane found)."""
        cfg = self.config
        mask = self.white_mask(frame_bgr)
        points = self._row_candidates(mask)
        if not points:
            return CvLaneEstimate(ok=False, reason="no_line_features")

        lines = self._cluster_lines(points)
        if len(lines) < 2:
            if len(lines) == 1:
                return self._single_line_estimate(lines, points, "fewer_than_two_lines")
            return CvLaneEstimate(
                ok=False,
                feature_count=len(points),
                n_lines=len(lines),
                reason="fewer_than_two_lines",
            )

        # Order lines right→left by intercept (Y at the vehicle, X=0);
        # collect every adjacent pair with a plausible lane separation.
        lines.sort(key=lambda cl: cl["c0"])
        plausible: List[Tuple[float, dict, dict]] = []  # (centre, right, left)
        for right, left in zip(lines[:-1], lines[1:]):
            sep = left["c0"] - right["c0"]
            if abs(sep - cfg.lane_width_nominal_m) > cfg.lane_width_tol_m:
                continue
            plausible.append((0.5 * (left["c0"] + right["c0"]), right, left))
        if not plausible:
            return self._single_line_estimate(lines, points, "no_plausible_lane_pair")
        # Lane selection. Default: the driven lane is the pair whose centre is
        # nearest the vehicle (min |centre|). BUT when the vehicle is off-centre
        # past ~half a lane, a neighbouring-lane line forms a *competing* plausible
        # pair on the other side whose centre is marginally nearer — picking it
        # makes the vehicle look centred in the wrong lane while it is actually
        # departing its own (the H-12 under-read, D-48: at ey≈0.12 m the true pair
        # reads +0.14 m but the neighbour pair reads −0.13 m and won by ~10 mm,
        # so C-01/C-05 were never triggered and the car ran off the road). The
        # signature is two plausible pairs with **opposite-sign centres** (genuine
        # left/right ambiguity). In that case pick the most *conservative*
        # interpretation — the largest |centre|, i.e. the largest reported offset —
        # so the safety monitor is never fed a falsely-centred state. This is inert
        # in nominal driving and on curves (a single plausible pair, or pairs that
        # agree on side), and at worst yields a conservative false "off-centre"
        # (an availability cost, a safe outcome) rather than a silent under-read.
        centres = [c for c, _, _ in plausible]
        ambiguous = (
            cfg.conservative_lane_selection
            and max(centres) > 0.0 > min(centres)
        )
        select = max if ambiguous else min
        best_center, *best_pair = select(plausible, key=lambda t: abs(t[0]))
        best_pair = tuple(best_pair)

        # Lane-centre polynomial = mean of the two line fits; the state is
        # read off its coefficients at the vehicle (X=0).
        right, left = best_pair
        c0 = 0.5 * (left["c0"] + right["c0"])
        c1 = 0.5 * (left["c1"] + right["c1"])
        c2 = 0.5 * (left["c2"] + right["c2"])
        # Heading from a curvature-corrected near-field refit (slope at the
        # vehicle) rather than the full-band slope c1, which a tight curve fit
        # biases toward the curve direction.
        c1_heading = self._near_field_slope(right, left, c1)
        heading = float(np.arctan(c1_heading))
        ey = -float(c0)
        epsi = -heading
        lane_width = float((left["c0"] - right["c0"]) * np.cos(heading))

        pair_pts = right["pts"] + left["pts"]
        xs = np.array([p[0] for p in pair_pts])
        n_rows_spanned = len(np.unique(np.round(xs, 3)))
        if n_rows_spanned >= cfg.min_rows_for_curvature and float(np.ptp(xs)) > 0.2:
            curvature = float(2.0 * c2)
        else:
            curvature = 0.0  # not enough span to trust a curvature estimate

        n_pair_points = len(pair_pts)
        confidence = min(1.0, n_pair_points / (2.0 * len(self._scan_rows)))
        # Feed the running width estimate for the single-line fallback.
        self._lane_width_ema = 0.8 * self._lane_width_ema + 0.2 * lane_width
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
            center_coeffs=(float(c0), float(c1), float(c2)),
            line_fits=tuple((cl["c0"], cl["c1"]) for cl in lines),
        )

    def _single_line_estimate(
        self,
        lines: List[dict],
        points: Sequence[Tuple[float, float, int]],
        fail_reason: str,
    ) -> CvLaneEstimate:
        """Fallback when no plausible pair exists (lane_keeper single-side
        precedent): infer the lane centre from the single line nearest a
        half-lane offset, using the running lane-width estimate. The side is
        the line's own sign — trustworthy only while the line sits roughly
        half a lane away (slack-bounded); a wrong-side lock is the H-12 case
        the SR-014 temporal check backstops."""
        cfg = self.config
        if not cfg.single_line_fallback or not lines:
            return CvLaneEstimate(
                ok=False, feature_count=len(points), n_lines=len(lines),
                reason=fail_reason,
            )
        half = self._lane_width_ema / 2.0
        best = min(lines, key=lambda cl: abs(abs(cl["c0"]) - half))
        if abs(abs(best["c0"]) - half) > cfg.single_line_side_slack_m:
            return CvLaneEstimate(
                ok=False, feature_count=len(points), n_lines=len(lines),
                reason=fail_reason,
            )
        side = 1.0 if best["c0"] >= 0 else -1.0  # +1: left line, -1: right line
        center0 = best["c0"] - side * half
        heading = float(np.arctan(best["c1"]))
        xs = np.array([p[0] for p in best["pts"]])
        curvature = (
            float(2.0 * best["c2"])
            if len(xs) >= cfg.min_rows_for_curvature and float(np.ptp(xs)) > 0.2
            else 0.0
        )
        confidence = cfg.single_line_confidence_scale * min(
            1.0, len(best["pts"]) / float(len(self._scan_rows))
        )
        return CvLaneEstimate(
            ok=True,
            ey=-float(center0),
            epsi=-heading,
            lane_width=float(self._lane_width_ema),
            curvature=curvature,
            confidence=float(confidence),
            feature_count=len(best["pts"]),
            n_lines=len(lines),
            reason="single_line",
            center_coeffs=(float(center0), float(best["c1"]), float(best["c2"])),
            line_fits=tuple((cl["c0"], cl["c1"]) for cl in lines),
        )
