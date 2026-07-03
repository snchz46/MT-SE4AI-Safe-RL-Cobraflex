"""Generate a complex closed lane-following track (left+right, open+tight curves).

Unlike the oval presets, this builds a single closed loop from a Catmull-Rom
spline through hand-placed waypoints, so the centreline has corners of *both*
handedness and a range of radii (tight hairpins + open sweeps) — an agent can't
overfit a single turn direction.

Outputs (under experiments/sim/tracks/<name>/ by default):
  * <name>.png            -- top-down road texture, same look as the Gazebo road
                             tiles (black asphalt, 1 cm white solid edges, 10/10 cm
                             dashed white centreline, 0.52 m road width).
  * <name>_centerline.yaml -- centreline polyline in the schema the cage /
                             lane_perception consume (same as the oval YAMLs).
  * <name>_meta.yaml      -- texture origin + size in metres, for placing the
                             textured plane in Isaac (tools/isaac_ros2_bringup.py).

Run:
    python scripts/generate_complex_track.py [--name complex_a] [--px-per-m 300]
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

# Road appearance — mirrors materials/road_assets/road_tiles/make_road_tiles.py
ASPHALT = (0, 0, 0)
OFFROAD = (90, 110, 70)        # muted grass/green so off-track is clearly distinct
LINE_WHITE = (255, 255, 255)
LINE_WIDTH_M = 0.01
DASH_MARK_M = 0.10
DASH_GAP_M = 0.10
ROAD_WIDTH_M = 0.52
HALF_ROAD_M = ROAD_WIDTH_M / 2.0
LANE_USEFUL_M = 0.245
MARGIN_M = 0.6                 # off-road border around the loop
SAMPLE_SPACING_M = 0.05        # centreline resample spacing

def _complex_e_cw_waypoints(step=0.25, r_end=1.4, cx=2.9, cy=0.2, y_top=1.6,
                            amp=0.145, half_period=1.305, w_halfspan=2.61):
    """complex_e v2 (D-51): the CLOCKWISE member of the CV-safe trio.

    Mirrored handedness vs complex_b/d (both CCW), so the multi-track trainer
    sees right-turn-dominant laps too. CW means the driven right lane runs
    INSIDE the end U-turns, so the ends must be wide: semicircles R=1.4 m
    centred (±cx, cy) leave a driven radius ≈ 1.28 m. The bottom is a cosine
    "W" (lows at ±half_period, central counter-steer crest at 0; nominal
    κ_max = amp·(π/half_period)² → R 1.19 m) joined to the arc bottoms through
    short straight buffers at y = cy − r_end (the joins land on horizontal-
    tangent cosine peaks). Measured on the resampled centreline: R_min
    1.079 m centre / 0.956 m driven right lane — above the docs/12 §4.7
    ~0.9 m monocular boundary.

    Sampled ANALYTICALLY every ~step m (not sparse hand points) because
    Catmull-Rom through sparse waypoints kinks wherever curvature flips sign:
    every sparse variant of this shape measured R_min ~0.5–0.8 m at the
    arc→W joins; through ~0.25 m samples the spline follows the analytic
    curve to ~1 %.
    """
    pts = []
    n = int(round(2 * cx / step))                      # top straight, L -> R
    for i in range(n):
        pts.append((-cx + i * (2 * cx / n), y_top))
    n = int(round(math.pi * r_end / step))             # right end, +90 -> -90 deg
    for i in range(n):
        a = math.pi / 2 - i * math.pi / n
        pts.append((cx + r_end * math.cos(a), cy + r_end * math.sin(a)))
    y0 = cy - r_end                                    # W join level (arc bottom)
    nb = max(1, int(round((cx - w_halfspan) / step)))  # straight buffer, in
    for i in range(nb):
        pts.append((cx - i * (cx - w_halfspan) / nb, y0))
    n = int(round(2 * w_halfspan / step))              # cosine W, R -> L
    for i in range(n):
        x = w_halfspan - i * (2 * w_halfspan / n)
        pts.append((x, y0 - amp + amp * math.cos(math.pi * x / half_period)))
    for i in range(nb):                                # straight buffer, out
        pts.append((-w_halfspan - i * (cx - w_halfspan) / nb, y0))
    n = int(round(math.pi * r_end / step))             # left end, -90 -> +90 deg
    for i in range(n):
        a = -math.pi / 2 - i * math.pi / n
        pts.append((-cx + r_end * math.cos(a), cy + r_end * math.sin(a)))
    return pts


# Closed-loop waypoint presets (metres). Catmull-Rom through them, so colinear
# runs render as straights and the curvature (handedness + radius) varies.
TRACKS = {
    # Kidney with a bottom right-hand S — both handedness, radii ~0.4–5 m.
    "complex_a": [
        (-3.2, 1.2), (-1.4, 1.9), (0.7, 2.0), (2.5, 1.1), (3.0, -0.5),
        (1.8, -1.2), (0.6, -0.5), (-0.8, -1.2), (-2.5, -1.5), (-3.5, -0.2),
    ],
    # Long pure straight along the bottom (~2.8 m, 5 colinear pts); the top side
    # is an "M" — two open humps with a central valley (the former 3-curve
    # serpentine had its middle hump removed). Curves softened so the tightest
    # radius is ~0.9 m (was ~0.43 m): the monocular CV cage-estimator's heading
    # over-reads ∝ curvature × near-look-ahead, and at the old radii that
    # apparent heading exceeded C-02's theta_max and latched false emergencies
    # even with the car tracking to mm. See docs/12 §"Curvature boundary".
    "complex_b": [
        (-2.8, -1.5), (-1.4, -1.5), (0.0, -1.5), (1.4, -1.5), (2.8, -1.5),
        (3.7, -0.8), (3.9, 0.3), (3.4, 1.1),     # right end -> up (rounded U-turn)
        (2.0, 1.35),                             # M: right hump
        (0.0, 0.8),                              # M: central valley (pronounced —
                                                 # the loop's main counter-steer)
        (-2.0, 1.35),                            # M: left hump
        (-3.4, 1.1), (-3.9, 0.3), (-3.7, -0.8),  # left end -> down (rounded U-turn)
    ],
    # Technical: full top sweep, right-hander down, gentle bottom chicane (S).
    "complex_c": [
        (-3.3, 0.3), (-2.7, 1.5), (-0.9, 1.9), (1.0, 1.7), (2.6, 0.9),
        (3.2, -0.4), (2.2, -1.3), (0.6, -1.0), (-0.9, -1.5), (-2.7, -1.3),
    ],
    # --- CV-safe presets (D-50 multi-track camera training) -------------------
    # complex_a/complex_c violate the monocular curvature boundary (docs/12
    # §4.7: driven-lane R < ~0.9 m ⇒ the cage's CV heading over-read exceeds
    # C-02's theta_max ⇒ false emergencies while tracking to mm), so they suit
    # only ground-truth-cage / monitoring runs. The two presets below keep the
    # complex_b philosophy (long straight + wide U-turn ends + counter-steer
    # features, both handedness) with driven right-lane R_min ≥ 0.90 m, so the
    # camera-track cage stays honest:
    #   complex_d  R_min centre 0.884 / driven right lane 0.932 m  (CCW)
    #   complex_e  R_min centre 1.079 / driven right lane 0.956 m  (CW, v2 D-51)
    # (complex_b, the proven GE4-V2 circuit, is 0.876 / 0.998 m, CCW.)
    #
    # complex_d — long bottom straight; the top is a single wide, shallow
    # central valley (a "V", vs complex_b's two-hump "M"): one pronounced
    # right-hand counter-steer between the two left U-turns.
    "complex_d": [
        (-3.0, -1.6), (-1.5, -1.6), (0.0, -1.6), (1.5, -1.6), (3.0, -1.6),
        (3.9, -0.9), (4.1, 0.2), (3.4, 1.1),
        (2.2, 1.55), (1.1, 1.25),
        (0.0, 0.95),
        (-1.1, 1.25), (-2.2, 1.55),
        (-3.4, 1.1), (-4.1, 0.2), (-3.9, -0.9),
    ],
    # complex_e v2 (D-51) — the CLOCKWISE circuit: complex_b and complex_d are
    # both CCW (driven turning arc ~13 m left vs ~2 m right EACH), so the
    # original CCW complex_e made the whole training trio left-turn-dominant
    # (8:1). This one is driven clockwise — top straight L->R, wide R=1.4 m
    # end U-turns (the driven right lane is now INSIDE them), cosine-"W"
    # bottom with a central counter-steer crest — flipping every lap to
    # right-turn-dominant (driven arc 2.6 m left / 10.5 m right; trio balance
    # now ~2:1). Waypoints come from the analytic builder above (dense
    # sampling — sparse Catmull-Rom kinks at curvature sign flips).
    "complex_e": _complex_e_cw_waypoints(),
}


def catmull_rom_closed(points: np.ndarray, samples_per_seg: int = 40) -> np.ndarray:
    """Sample a closed Catmull-Rom spline through *points* (N,2)."""
    n = len(points)
    out = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i % n]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        for t in np.linspace(0.0, 1.0, samples_per_seg, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1)
                              + (-p0 + p2) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def resample_by_arclength(curve: np.ndarray, spacing: float) -> np.ndarray:
    """Resample a closed curve to roughly uniform arc-length spacing."""
    seg = np.linalg.norm(np.diff(np.vstack([curve, curve[:1]]), axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    total = s[-1]
    n = max(8, int(round(total / spacing)))
    targets = np.linspace(0.0, total, n, endpoint=False)
    pts = []
    for st in targets:
        j = np.searchsorted(s, st) - 1
        j = min(max(j, 0), len(curve) - 1)
        s0, s1 = s[j], s[j + 1]
        f = 0.0 if s1 == s0 else (st - s0) / (s1 - s0)
        a = curve[j]
        b = curve[(j + 1) % len(curve)]
        pts.append(a + f * (b - a))
    return np.array(pts), total


def normals(curve: np.ndarray) -> np.ndarray:
    """Unit left-normals along a closed curve."""
    t = np.roll(curve, -1, axis=0) - np.roll(curve, 1, axis=0)
    t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-9)
    return np.stack([-t[:, 1], t[:, 0]], axis=1)


def signed_curvature(curve: np.ndarray) -> np.ndarray:
    p_prev = np.roll(curve, 1, axis=0)
    p_next = np.roll(curve, -1, axis=0)
    d1 = curve - p_prev
    d2 = p_next - curve
    a = np.linalg.norm(d1, axis=1)
    b = np.linalg.norm(d2, axis=1)
    cross = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    chord = np.linalg.norm(p_next - p_prev, axis=1)
    denom = (a * b * chord) + 1e-9
    return 2.0 * cross / denom        # 1/radius, signed (+left, -right)


def build(name: str, waypoints, px_per_m: int, out_dir: Path, ss: int = 2,
          road_width: float = ROAD_WIDTH_M, two_lane: bool = True,
          *, draw_center: bool = True, draw_left_edge: bool = True,
          draw_right_edge: bool = True,
          erase_center=None, erase_left=None, erase_right=None,
          write_aux: bool = True):
    """Render the track texture (+ optional centreline/meta YAML).

    The ``draw_center`` / ``draw_left_edge`` / ``draw_right_edge`` toggles
    (default all on = the normal two-lane road) let a caller render a
    **missing-marking variant** of an existing track — same geometry, same
    pixel grid — by removing a whole lane line.

    For a *partial* degradation (the realistic case: only some stretches of a
    line are worn away, the agent meets gaps mid-track) pass
    ``erase_center`` / ``erase_left`` / ``erase_right`` as lists of centreline
    arc-length intervals ``[(s0, s1), ...]`` in metres; the line is painted
    everywhere except those spans. ``write_aux=False`` writes only the PNG (the
    variant reuses the base track's centreline/meta)."""
    half_road = road_width / 2.0
    wp = np.array(waypoints, dtype=float)
    dense = catmull_rom_closed(wp)
    center, perimeter = resample_by_arclength(dense, SAMPLE_SPACING_M)
    nrm = normals(center)
    left = center + half_road * nrm
    right = center - half_road * nrm

    kappa = signed_curvature(center)
    rad = 1.0 / (np.abs(kappa) + 1e-9)
    turning = kappa[np.abs(kappa) > 0.2]   # ignore near-straight
    has_left = bool(np.any(turning > 0))
    has_right = bool(np.any(turning < 0))
    print(f"[track] points={len(center)} perimeter={perimeter:.2f} m")
    print(f"[track] curve radius: min={rad.min():.2f} m  max(turning)~{rad[np.abs(kappa)>0.2].max():.2f} m")
    print(f"[track] left turns={has_left}  right turns={has_right}")

    # World extent -> image. Render at ss× resolution and downsample with LANCZOS
    # (supersampling anti-aliasing) so the road edges / lane lines aren't jagged.
    allpts = np.vstack([left, right])
    xmin, ymin = allpts.min(axis=0) - MARGIN_M
    xmax, ymax = allpts.max(axis=0) + MARGIN_M
    W_m, H_m = xmax - xmin, ymax - ymin
    rppm = px_per_m * ss
    W_px, H_px = int(round(W_m * rppm)), int(round(H_m * rppm))

    def to_px(p):
        # world (x right, y up) -> image (x right, y down)
        u = (p[:, 0] - xmin) * rppm
        v = (ymax - p[:, 1]) * rppm
        return np.stack([u, v], axis=1)

    img = Image.new("RGB", (W_px, H_px), OFFROAD)
    draw = ImageDraw.Draw(img)

    # Road ribbon: filled polygon [left forward .. right backward]
    lpx, rpx, cpx = to_px(left), to_px(right), to_px(center)
    poly = [tuple(p) for p in lpx] + [tuple(p) for p in rpx[::-1]]
    draw.polygon(poly, fill=ASPHALT)
    # Close the start/finish seam (the polygon's two end caps leave a wedge gap
    # at the loop join) so the ribbon is continuous.
    draw.polygon([tuple(lpx[-1]), tuple(lpx[0]), tuple(rpx[0]), tuple(rpx[-1])],
                 fill=ASPHALT)

    lw = max(1, int(round(LINE_WIDTH_M * rppm)))
    # Per-point centreline arc-length s[i] (s[-1] = perimeter): drives the dash
    # spacing AND lets a caller place line GAPS by feature (erase_* intervals).
    seg = np.linalg.norm(np.diff(np.vstack([center, center[:1]]), axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])

    def _in_any(si, intervals):
        return any(lo <= si <= hi for lo, hi in intervals)

    def _overlaps(a0, a1, intervals):
        return any(not (a1 < lo or a0 > hi) for lo, hi in intervals)

    # Solid white edges. Fully toggleable (draw_left/right_edge) AND partially
    # eraseable over a list of centreline arc-length intervals (erase_left/right):
    # a missing-marking track keeps the line everywhere except a few worn-away
    # patches, so the agent meets gaps mid-track rather than a wholesale removal.
    edge_specs = []
    if draw_left_edge:
        edge_specs.append((lpx, list(erase_left or [])))
    if draw_right_edge:
        edge_specs.append((rpx, list(erase_right or [])))
    for edge, erase in edge_specs:
        if not erase:
            seq = [tuple(p) for p in edge] + [tuple(edge[0])]
            draw.line(seq, fill=LINE_WHITE, width=lw, joint="curve")
            continue
        run = []                                   # current contiguous painted span
        for i in range(len(edge) + 1):             # +1 closes the start/finish seam
            si = s[i] if i < len(edge) else s[-1]
            if _in_any(si, erase):
                if len(run) >= 2:
                    draw.line(run, fill=LINE_WHITE, width=lw, joint="curve")
                run = []
            else:
                run.append(tuple(edge[i % len(edge)]))
        if len(run) >= 2:
            draw.line(run, fill=LINE_WHITE, width=lw, joint="curve")
    # Dashed white centreline — only on a two-lane road. A single-lane road has
    # just the two edges so the camera-CV lane keeper never sees an adjacent lane
    # to confuse with on tight curves. A dash overlapping an erase_center
    # interval is skipped (a worn-away patch of the centre line).
    erase_c = list(erase_center or [])
    dash, gap = DASH_MARK_M, DASH_GAP_M
    pos = 0.0
    while two_lane and draw_center and pos < s[-1]:
        a0, a1 = pos, min(pos + dash, s[-1])
        if not _overlaps(a0, a1, erase_c):
            ja = np.searchsorted(s, a0) - 1
            jb = np.searchsorted(s, a1) - 1
            idx = list(range(max(ja, 0), min(jb + 2, len(center))))
            if len(idx) >= 2:
                seq = [tuple(p) for p in cpx[idx]]
                draw.line(seq, fill=LINE_WHITE, width=lw, joint="curve")
        pos += dash + gap

    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{name}.png"
    if ss > 1:
        fw, fh = int(round(W_m * px_per_m)), int(round(H_m * px_per_m))
        img = img.resize((fw, fh), Image.LANCZOS)
    img.save(png_path)

    # Centreline YAML (cage / lane_perception schema)
    cl_yaml = {
        "centerline": {
            "geometry": f"complex_spline:{name}",
            "perimeter_m": round(float(perimeter), 4),
            "num_points": int(len(center)),
            "points": [[round(float(x), 4), round(float(y), 4)] for x, y in center],
        },
        "lane_width": (LANE_USEFUL_M if two_lane else round(road_width, 4)),
        "road_width": round(road_width, 4),
    }
    if write_aux:
        (out_dir / f"{name}_centerline.yaml").write_text(yaml.safe_dump(cl_yaml, sort_keys=False))

    # Meta for Isaac plane placement: texture covers [xmin,xmax]x[ymin,ymax] at z=0.
    meta = {
        "name": name,
        "texture": f"{name}.png",
        "px_per_m": px_per_m,
        "lanes": 2 if two_lane else 1,
        "road_width": round(road_width, 4),
        "size_m": [round(float(W_m), 4), round(float(H_m), 4)],
        "center_m": [round(float((xmin + xmax) / 2), 4), round(float((ymin + ymax) / 2), 4)],
        "world_bbox": [round(float(xmin), 4), round(float(ymin), 4),
                       round(float(xmax), 4), round(float(ymax), 4)],
        # A start pose on the centreline (point 0) + heading along the track.
        "start_xy": [round(float(center[0, 0]), 4), round(float(center[0, 1]), 4)],
        "start_yaw": round(float(math.atan2(center[1, 1] - center[0, 1],
                                            center[1, 0] - center[0, 0])), 4),
    }
    if write_aux:
        (out_dir / f"{name}_meta.yaml").write_text(yaml.safe_dump(meta, sort_keys=False))
    print(f"[track] wrote {png_path} ({W_px}x{H_px}px)"
          + (f", centerline + meta in {out_dir}" if write_aux else " (texture only)"))
    return png_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="complex_a", choices=list(TRACKS) + ["all"])
    ap.add_argument("--px-per-m", type=int, default=500)
    ap.add_argument("--ss", type=int, default=2, help="supersampling factor (AA)")
    ap.add_argument("--lanes", type=int, default=2, choices=(1, 2),
                    help="1 = single lane (two edges, no centre line); 2 = two-lane")
    ap.add_argument("--road-width", type=float, default=None,
                    help="override road width (m); default 0.52 two-lane / 0.30 single")
    # Missing-marking variants (track 'E' degraded-markings scenarios): same
    # geometry, one lane line erased. Use with --name-suffix + --texture-only so
    # the variant PNG sits beside the base track and reuses its centreline.
    ap.add_argument("--name-suffix", default="",
                    help="suffix for the output filename (e.g. _nocenter); reuses the base geometry")
    ap.add_argument("--no-center", action="store_true",
                    help="omit the dashed centre line (missing-marking variant)")
    ap.add_argument("--no-left-edge", action="store_true",
                    help="omit the left solid edge line")
    ap.add_argument("--no-right-edge", action="store_true",
                    help="omit the right solid edge line")
    ap.add_argument("--erase-center", default="",
                    help="dashed-centre GAPS as arc-length intervals 's0:s1,s0:s1' (m) — worn patches")
    ap.add_argument("--erase-left", default="",
                    help="left-edge GAPS as arc-length intervals 's0:s1,...' (m)")
    ap.add_argument("--erase-right", default="",
                    help="right-edge GAPS as arc-length intervals 's0:s1,...' (m)")
    ap.add_argument("--texture-only", action="store_true",
                    help="write only the PNG (skip centreline/meta) — for a variant of an existing track")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    two_lane = args.lanes == 2
    rw = args.road_width or (ROAD_WIDTH_M if two_lane else 0.30)

    def _intervals(spec):
        out = []
        for part in str(spec or "").split(","):
            part = part.strip()
            if part:
                lo, hi = part.split(":")
                out.append((float(lo), float(hi)))
        return out

    repo = Path(__file__).resolve().parents[1]
    names = list(TRACKS) if args.name == "all" else [args.name]
    for name in names:
        out_dir = Path(args.out) if args.out else repo / "experiments/sim/tracks" / name
        build(name + args.name_suffix, TRACKS[name], args.px_per_m, out_dir, ss=args.ss,
              road_width=rw, two_lane=two_lane,
              draw_center=not args.no_center,
              draw_left_edge=not args.no_left_edge,
              draw_right_edge=not args.no_right_edge,
              erase_center=_intervals(args.erase_center),
              erase_left=_intervals(args.erase_left),
              erase_right=_intervals(args.erase_right),
              write_aux=not args.texture_only)


if __name__ == "__main__":
    main()
