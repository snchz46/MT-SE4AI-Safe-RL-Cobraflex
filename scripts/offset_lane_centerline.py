"""Generate a lane-centerline YAML from the road-centerline YAML by
offsetting every point perpendicular to the local heading.

Use case: the F2 demo originally tracked the road centerline (between
the two lanes). The Gazebo robot is now spawned on a single lane (right
or left). The path-following stack needs a centerline that matches the
lane the robot actually drives on, otherwise ey is non-zero from t=0
and the PD saturates against C-05 on its first cycle.

The output preserves the lane_width / road_width fields and the
original closure (first point repeated at the end) so PolylineTracker
behaves identically.

Sign convention for ``side``:
    "right": offset to the right of the motion direction (the side the
             driver would be on in countries that drive on the right).
    "left":  the opposite.

For an oval traversed counter-clockwise viewed from +z, ``right`` is
the outer side of the oval and the resulting centerline has larger
curve radii than the input.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import List, Tuple

import yaml


Vec2 = Tuple[float, float]


def _wrap_index(i: int, n: int, closed: bool) -> int:
    if closed:
        return i % n
    return max(0, min(n - 1, i))


def offset_polyline(
    points: List[Vec2],
    distance: float,
    side: str,
) -> List[Vec2]:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    # Right of motion is obtained by rotating the unit tangent by -90 deg:
    # tangent (tx, ty) -> (ty, -tx). Sign +1 selects "right"; -1 selects
    # "left" (rotation by +90 deg).
    sign = +1.0 if side == "right" else -1.0

    n = len(points)
    closed = n >= 2 and math.isclose(points[0][0], points[-1][0]) and math.isclose(
        points[0][1], points[-1][1]
    )
    # When closed, drop the duplicated last point for tangent computation
    # and re-append it at the end so the offset polyline is also closed.
    base = points[:-1] if closed else points
    m = len(base)

    out: List[Vec2] = []
    for i in range(m):
        prev = base[_wrap_index(i - 1, m, closed)]
        nxt = base[_wrap_index(i + 1, m, closed)]
        tx = nxt[0] - prev[0]
        ty = nxt[1] - prev[1]
        norm = math.hypot(tx, ty)
        if norm < 1e-12:
            tx, ty = 1.0, 0.0
        else:
            tx /= norm
            ty /= norm
        # Right normal (rotate tangent by -90 deg): (ty, -tx).
        # Left normal: (-ty, tx). The ``sign`` selects between them.
        nx = sign * ty
        ny = -sign * tx
        out.append((base[i][0] + distance * nx, base[i][1] + distance * ny))

    if closed:
        out.append(out[0])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("src/cobraflex_rl/config/oval_centerline.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("src/cobraflex_rl/config/oval_right_lane_centerline.yaml"),
    )
    parser.add_argument("--side", choices=("left", "right"), default="right")
    parser.add_argument(
        "--distance",
        type=float,
        default=None,
        help="Offset in metres. Defaults to lane_width/2 from the input YAML.",
    )
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)

    raw_points = [tuple(p) for p in cfg["centerline"]["points"]]
    lane_width = float(cfg["lane_width"])
    distance = args.distance if args.distance is not None else lane_width / 2.0

    new_points = offset_polyline(raw_points, distance=distance, side=args.side)

    # Recompute perimeter for the new polyline so the field stays honest.
    perimeter = 0.0
    for i in range(1, len(new_points)):
        dx = new_points[i][0] - new_points[i - 1][0]
        dy = new_points[i][1] - new_points[i - 1][1]
        perimeter += math.hypot(dx, dy)

    geometry_label = f"{cfg['centerline'].get('geometry', 'oval')}_{args.side}_lane"
    payload = {
        "centerline": {
            "geometry": geometry_label,
            "straight_length_m": cfg["centerline"].get("straight_length_m"),
            "curve_radius_m": cfg["centerline"].get("curve_radius_m"),
            "perimeter_m": round(perimeter, 4),
            "num_points": len(new_points),
            "source_centerline": str(args.input),
            "lateral_offset_m": distance,
            "offset_side": args.side,
            "points": [[round(x, 4), round(y, 4)] for x, y in new_points],
        },
        "lane_width": lane_width,
        "road_width": float(cfg.get("road_width", lane_width)),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        handle.write(
            "# Generated by scripts/offset_lane_centerline.py from\n"
            f"#   {args.input}\n"
            f"# Offset {distance:.4f} m to the {args.side} of motion.\n"
            "# Re-run that script to regenerate after editing the source.\n\n"
        )
        yaml.safe_dump(payload, handle, sort_keys=False)

    print(f"Wrote {len(new_points)} points to {args.output}")
    print(f"Perimeter: {perimeter:.4f} m  (input had {cfg['centerline'].get('perimeter_m')} m)")


if __name__ == "__main__":
    main()
