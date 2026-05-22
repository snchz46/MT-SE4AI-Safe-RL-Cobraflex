from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Optional, Tuple

import numpy as np


# Window radius (segments) used to smooth track_heading. With a discretised
# centerline polyline (~0.1 m / segment on the F2 oval) the per-segment
# heading is piecewise-constant and steps by ~7 deg on the R=0.8 m curve.
# Averaging over the 2*radius+1 neighbouring segments yields a heading
# that varies continuously with arc length, which is what a path-tracking
# PD needs for its heading-error finite difference to be meaningful.
_HEADING_SMOOTHING_RADIUS = 2

# Search radius (in segments) for the local nearest-segment search after
# the tracker has acquired a previous best index. The global O(N) sweep
# can leapfrog to a non-adjacent segment whenever two segments happen to
# be near-equidistant — on the F2 right-lane oval this manifests as a
# multi-segment jump in segment_index between consecutive cycles, which
# slams a step into ey/epsi and saturates the PD. Constraining the search
# to the immediate neighbourhood of the previous index enforces continuity
# at the cost of an explicit reset when the robot is teleported.
_LOCAL_SEARCH_RADIUS = 6


def wrap_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


@dataclass
class TrackState:
    ey: float
    epsi: float
    s: float
    segment_index: int
    segment_fraction: float
    track_heading: float
    closest_point: Tuple[float, float]


class PolylineTracker:
    def __init__(self, polyline: np.ndarray):
        points = np.asarray(polyline, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("Polyline must have shape (N, 2).")
        if points.shape[0] < 2:
            raise ValueError("Polyline must contain at least two points.")

        self.points = points
        self.segment_vectors = self.points[1:] - self.points[:-1]
        self.segment_lengths = np.linalg.norm(self.segment_vectors, axis=1)

        if np.any(self.segment_lengths < 1e-9):
            raise ValueError("Polyline contains a zero-length segment.")

        self.segment_headings = np.arctan2(
            self.segment_vectors[:, 1], self.segment_vectors[:, 0]
        )
        self.cumulative_lengths = np.concatenate(
            ([0.0], np.cumsum(self.segment_lengths))
        )

        # Closed polylines (oval, lap) wrap segment indices modulo N.
        self._closed = bool(
            np.allclose(self.points[0], self.points[-1], atol=1e-6)
        )
        self._prev_best_index: Optional[int] = None

    def reset_tracking(self) -> None:
        """Drop the cached best_index so the next track() call does a
        global search. Call after warping the tracked entity (e.g. lap
        reset) so we do not constrain the search to a stale neighbourhood.
        """
        self._prev_best_index = None

    def track(self, x: float, y: float, yaw: float) -> TrackState:
        position = np.array([x, y], dtype=float)
        n_segments = len(self.segment_vectors)

        if self._prev_best_index is None:
            indices: Iterable[int] = range(n_segments)
        elif self._closed:
            base = self._prev_best_index
            indices = [
                (base + k) % n_segments
                for k in range(-_LOCAL_SEARCH_RADIUS, _LOCAL_SEARCH_RADIUS + 1)
            ]
        else:
            lo = max(0, self._prev_best_index - _LOCAL_SEARCH_RADIUS)
            hi = min(n_segments, self._prev_best_index + _LOCAL_SEARCH_RADIUS + 1)
            indices = range(lo, hi)

        best_index = 0
        best_fraction = 0.0
        best_projection = self.points[0]
        best_error = np.zeros(2, dtype=float)
        best_distance_sq = float("inf")

        for index in indices:
            start = self.points[index]
            vector = self.segment_vectors[index]
            length = self.segment_lengths[index]

            relative = position - start
            projection_fraction = float(
                np.dot(relative, vector) / max(length * length, 1e-12)
            )
            projection_fraction = float(np.clip(projection_fraction, 0.0, 1.0))
            projection = start + projection_fraction * vector
            error = position - projection
            distance_sq = float(np.dot(error, error))

            if distance_sq < best_distance_sq:
                best_distance_sq = distance_sq
                best_index = index
                best_fraction = projection_fraction
                best_projection = projection
                best_error = error

        self._prev_best_index = best_index

        segment_vector = self.segment_vectors[best_index]
        segment_length = self.segment_lengths[best_index]
        track_heading = self._smoothed_heading(best_index)
        cross_z = segment_vector[0] * best_error[1] - segment_vector[1] * best_error[0]
        ey = float(cross_z / segment_length)
        epsi = wrap_angle(yaw - track_heading)
        s = float(self.cumulative_lengths[best_index] + best_fraction * segment_length)

        return TrackState(
            ey=ey,
            epsi=epsi,
            s=s,
            segment_index=best_index,
            segment_fraction=best_fraction,
            track_heading=track_heading,
            closest_point=(float(best_projection[0]), float(best_projection[1])),
        )

    def _smoothed_heading(self, segment_index: int) -> float:
        n = len(self.segment_headings)
        if self._closed:
            indices = [
                (segment_index + k) % n
                for k in range(-_HEADING_SMOOTHING_RADIUS, _HEADING_SMOOTHING_RADIUS + 1)
            ]
            headings = self.segment_headings[indices]
        else:
            lo = max(0, segment_index - _HEADING_SMOOTHING_RADIUS)
            hi = min(n, segment_index + _HEADING_SMOOTHING_RADIUS + 1)
            headings = self.segment_headings[lo:hi]
        cs = float(np.cos(headings).sum())
        sn = float(np.sin(headings).sum())
        return math.atan2(sn, cs)
