from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

import numpy as np


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

    def track(self, x: float, y: float, yaw: float) -> TrackState:
        position = np.array([x, y], dtype=float)
        best_index = 0
        best_fraction = 0.0
        best_projection = self.points[0]
        best_error = np.zeros(2, dtype=float)
        best_distance_sq = float("inf")

        for index, (start, vector, length) in enumerate(
            zip(self.points[:-1], self.segment_vectors, self.segment_lengths)
        ):
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

        segment_vector = self.segment_vectors[best_index]
        segment_length = self.segment_lengths[best_index]
        track_heading = float(self.segment_headings[best_index])
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
