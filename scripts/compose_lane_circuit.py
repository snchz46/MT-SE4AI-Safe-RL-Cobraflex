"""Compose Gazebo lane-following world from modular road tiles.

Takes a tile sequence (currently the `oval_R080` preset) and emits:
    1. A Gazebo Sim `.world` file that reuses the plugin set of
       `src/cobraflex/worlds/obstacles.world` and places one box per
       tile with the corresponding PNG as albedo_map.
    2. The matching centerline polyline YAML consumed by the cage and by
       lane_perception_node.

The two artefacts are derived from the SAME geometric model, so the
visual road (PNG) and the logical centerline cannot drift apart.

Tile geometry conventions (see materials/road_assets/road_curves/README.md):
    - Straight tile: a rectangle of width 0.52 m (two-lane road) and
      configurable length L. Entry at bottom-mid, exit at top-mid.
    - Curve tile: a tight bounding box around the arc (computed in
      make_road_curves.py). Entry at the original (0, 0) of the
      arc-drawing frame, which is offset from the bbox centre.

Run:
    python scripts/compose_lane_circuit.py [--preset oval_R080]
                                            [--straight-length 1.5]
                                            [--theme clean|worn|wet]
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

REPO_ROOT = Path(__file__).resolve().parents[1]

ROAD_WIDTH_M = 0.52
HALF_ROAD_M = ROAD_WIDTH_M / 2
TILE_THICKNESS_M = 0.002
LIFT_Z_M = 0.001

OBSTACLES_WORLD_PLUGINS = """\
    <plugin
      filename="gz-sim-physics-system"
      name="gz::sim::systems::Physics">
    </plugin>
    <plugin
      filename="gz-sim-user-commands-system"
      name="gz::sim::systems::UserCommands">
    </plugin>
    <plugin
      filename="gz-sim-scene-broadcaster-system"
      name="gz::sim::systems::SceneBroadcaster">
    </plugin>
    <plugin
      filename="gz-sim-sensors-system"
      name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin
      filename="gz-sim-imu-system"
      name="gz::sim::systems::Imu">
    </plugin>
"""

GROUND_PLANE_BLOCK = """\
    <model name='ground_plane'>
      <static>true</static>
      <link name='link'>
        <collision name='collision'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>50 50</size>
            </plane>
          </geometry>
          <surface>
            <friction><ode/></friction>
            <bounce/>
            <contact/>
          </surface>
        </collision>
        <visual name='visual'>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>50 50</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.3 0.55 0.3 1</ambient>
            <diffuse>0.3 0.55 0.3 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
          </material>
        </visual>
      </link>
    </model>
"""

SUN_LIGHT_BLOCK = """\
    <light name='sun' type='directional'>
      <pose>0 0 10 0 0 0</pose>
      <cast_shadows>false</cast_shadows>
      <intensity>1</intensity>
      <direction>-0.4 0.1 -0.9</direction>
      <diffuse>0.9 0.9 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <linear>0.01</linear>
        <constant>0.9</constant>
        <quadratic>0.001</quadratic>
      </attenuation>
    </light>
"""

STRAIGHT_THEME_TEXTURES = {
    # `clean` is regenerated at the exact requested length by
    # _ensure_clean_straight_png so the dashed centreline pace stays at
    # the design 10 cm dash + 10 cm gap (no UV compression). The variant
    # themes still use the 10 m source PNGs and will appear compressed
    # on short tiles; regenerate them with road_variants/make_*.py if
    # visual fidelity matters for an experiment.
    "clean": None,  # filled in at runtime
    "worn": "road_assets/road_variants/two_same_02_patched.png",
    "tee": "road_assets/road_variants/two_same_03_tee_junction.png",
    "wet": "road_assets/road_variants/two_opp_02_wet.png",
    "dirt": "road_assets/road_variants/single_03_dirt_road.png",
}


# Geometry constants for the procedural straight texture (mirror
# materials/road_assets/road_textures/make_road_textures.py).
_TEX_PX_PER_M = 500
_TEX_ASPHALT = (0, 0, 0)
_TEX_LINE_WHITE = (255, 255, 255)
_TEX_LINE_WIDTH_M = 0.01
_TEX_DASH_MARK_M = 0.10
_TEX_DASH_GAP_M = 0.10
_TEX_LANE_USEFUL_M = 0.245
_TEX_TWO_LANE_WIDTH_M = 2 * _TEX_LANE_USEFUL_M + 3 * _TEX_LINE_WIDTH_M  # 0.52


def _ensure_clean_straight_png(length_m: float, base_dir: Path) -> Path:
    """Generate (or reuse) the two-lane clean straight texture at exact length.

    Returns the absolute path. The texture lives next to the other
    road_textures so it gets installed by setup.py automatically.
    """
    out_dir = base_dir / "road_assets" / "road_textures"
    out_dir.mkdir(parents=True, exist_ok=True)
    length_label = f"{length_m:.2f}".replace(".", "p").rstrip("0").rstrip("p") or "0"
    name = f"road_two_lane_same_direction_0p52m_x_{length_label}m.png"
    path = out_dir / name
    if path.exists():
        return path

    if not _PIL_AVAILABLE:
        raise RuntimeError(
            "Pillow is required to generate the straight texture at custom "
            "length. Install with `pip install pillow`."
        )

    def m_to_px(m: float) -> int:
        return int(round(m * _TEX_PX_PER_M))

    width_px = m_to_px(_TEX_TWO_LANE_WIDTH_M)
    length_px = m_to_px(length_m)
    img = Image.new("RGB", (width_px, length_px), _TEX_ASPHALT)
    draw = ImageDraw.Draw(img)

    # Continuous edge lines (left and right)
    line_w_px = m_to_px(_TEX_LINE_WIDTH_M)
    draw.rectangle([(0, 0), (line_w_px - 1, length_px - 1)], fill=_TEX_LINE_WHITE)
    draw.rectangle(
        [(width_px - line_w_px, 0), (width_px - 1, length_px - 1)],
        fill=_TEX_LINE_WHITE,
    )

    # Dashed centreline
    cx = width_px // 2
    half_l = line_w_px // 2
    half_r = line_w_px - half_l
    dash_px = m_to_px(_TEX_DASH_MARK_M)
    gap_px = m_to_px(_TEX_DASH_GAP_M)
    period_px = dash_px + gap_px
    y = 0
    while y < length_px:
        y_end = min(y + dash_px, length_px)
        draw.rectangle(
            [(cx - half_l, y), (cx + half_r - 1, y_end - 1)], fill=_TEX_LINE_WHITE
        )
        y += period_px

    img.save(path, "PNG", optimize=True)
    return path


def _wrap_pi(theta: float) -> float:
    return math.atan2(math.sin(theta), math.cos(theta))


def _curve_bbox(radius_m: float, angle_deg: float) -> Tuple[float, float, float, float]:
    """Bounding box of a left-turn arc in its local frame (entry at (0,0))."""
    outer_r = radius_m + HALF_ROAD_M
    inner_r = max(0.0, radius_m - HALF_ROAD_M)
    cx = -radius_m
    cy = 0.0
    theta_start = -math.pi / 2
    theta_end = theta_start + math.radians(angle_deg)
    xs: List[float] = []
    ys: List[float] = []
    n = 400
    for i in range(n + 1):
        t = theta_start + (theta_end - theta_start) * i / n
        for r in (outer_r, inner_r):
            xs.append(cx + r * math.cos(t))
            ys.append(cy + r * math.sin(t))
    margin = 0.02
    return (
        min(xs) - margin,
        min(ys) - margin,
        max(xs) + margin,
        max(ys) + margin,
    )


def _straight_tile(length_m: float, theme: str, texture_uri: str) -> dict:
    return {
        "kind": "straight",
        "bbox_w": ROAD_WIDTH_M,
        "bbox_h": length_m,
        # Straight PNG: road runs along the image's V axis (image height),
        # so in tile-local frame the entry sits at the bottom-mid and the
        # heading there is +Y (math). The bbox is centred on the road
        # midpoint, so the bbox-relative entry offset is (0, -L/2).
        "entry_in_bbox": (0.0, -length_m / 2.0),
        "entry_heading_local": math.pi / 2.0,
        "exit_displacement_local": (0.0, length_m, 0.0),
        "texture_uri": texture_uri,
        "centreline": {"type": "line", "length": length_m},
    }


def _curve_tile(radius_m: float, angle_deg: float, mirror_right: bool = False) -> dict:
    """Curve tile metadata derived from materials/.../make_road_curves.py.

    The script draws the arc with `theta_start = -pi/2`, i.e. the
    centreline ENTRY of the arc is at LOCAL (-R, -R) with TANGENT +X,
    NOT at LOCAL (0, 0) with tangent +Y as the README narrative
    misleadingly suggests. The composer uses the script's drawing
    convention as the source of truth so that the asphalt in the PNG
    lines up with the polyline ground-truth used by the cage.
    """
    xmin, ymin, xmax, ymax = _curve_bbox(radius_m, angle_deg)
    bbox_w = xmax - xmin
    bbox_h = ymax - ymin
    bbox_cx_local = (xmin + xmax) / 2.0
    bbox_cy_local = (ymin + ymax) / 2.0

    angle_rad = math.radians(angle_deg)
    theta_start = -math.pi / 2.0
    theta_end = theta_start + angle_rad

    cx_local = -radius_m
    cy_local = 0.0
    entry_local = (
        cx_local + radius_m * math.cos(theta_start),
        cy_local + radius_m * math.sin(theta_start),
    )
    exit_local = (
        cx_local + radius_m * math.cos(theta_end),
        cy_local + radius_m * math.sin(theta_end),
    )
    # Tangent of an arc parametrised by theta is (-sin theta, cos theta)
    # for left-turn (CCW). Heading = atan2(tangent_y, tangent_x).
    entry_heading_local = math.atan2(math.cos(theta_start), -math.sin(theta_start))
    exit_heading_local = math.atan2(math.cos(theta_end), -math.sin(theta_end))

    entry_in_bbox = (
        entry_local[0] - bbox_cx_local,
        entry_local[1] - bbox_cy_local,
    )
    exit_displacement_local = (
        exit_local[0] - entry_local[0],
        exit_local[1] - entry_local[1],
        _wrap_pi(exit_heading_local - entry_heading_local),
    )

    if mirror_right:
        # Mirror across local X axis to flip a left curve into a right one.
        entry_in_bbox = (entry_in_bbox[0], -entry_in_bbox[1])
        entry_heading_local = -entry_heading_local
        exit_displacement_local = (
            exit_displacement_local[0],
            -exit_displacement_local[1],
            -exit_displacement_local[2],
        )

    r_int = int(round(radius_m * 100))
    a_int = int(round(angle_deg))
    texture = (
        f"road_assets/road_curves/curve_R{r_int:03d}cm_A{a_int:03d}deg.png"
    )

    return {
        "kind": "curve",
        "bbox_w": bbox_w,
        "bbox_h": bbox_h,
        "entry_in_bbox": entry_in_bbox,
        "entry_heading_local": entry_heading_local,
        "exit_displacement_local": exit_displacement_local,
        "texture_uri": texture,
        "extra_yaw": 0.0,
        "centreline": {
            "type": "arc",
            "radius": radius_m,
            "angle_rad": angle_rad,
            "direction": "left" if not mirror_right else "right",
        },
    }


def oval_preset(
    radius_m: float, straight_length_m: float, theme: str, straight_texture_uri: str
) -> List[dict]:
    return [
        _straight_tile(straight_length_m, theme, straight_texture_uri),
        _curve_tile(radius_m, 180.0, mirror_right=False),
        _straight_tile(straight_length_m, theme, straight_texture_uri),
        _curve_tile(radius_m, 180.0, mirror_right=False),
    ]


def _rotate(v: Tuple[float, float], theta: float) -> Tuple[float, float]:
    c, s = math.cos(theta), math.sin(theta)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def walk_sequence(tiles: Iterable[dict]) -> List[dict]:
    """Walk the tile chain, attaching world pose and centerline samples.

    The tile yaw is `world_th - entry_heading_local`, so the tile's
    local frame is rotated to make its local entry heading coincide
    with the current world heading. Straight tiles have
    entry_heading_local = +pi/2 (road runs +Y in local); curve tiles
    have entry_heading_local = 0 (the PNG arc enters with tangent +X
    in local, per make_road_curves.py).

    Initial world heading is +X (yaw=0) so the polyline matches the
    DiffDrive /odom convention (robot spawns at odom (0,0,yaw=0)
    facing +X).
    """
    world_x, world_y, world_th = 0.0, 0.0, 0.0
    placements: List[dict] = []

    for tile in tiles:
        psi_local = tile["entry_heading_local"]
        yaw = _wrap_pi(world_th - psi_local + tile.get("extra_yaw", 0.0))

        ex, ey = tile["entry_in_bbox"]
        rot_e = _rotate((ex, ey), yaw)
        bbox_cx = world_x - rot_e[0]
        bbox_cy = world_y - rot_e[1]

        polyline = _sample_centreline(tile, world_x, world_y, world_th)

        placements.append({
            "tile": tile,
            "bbox_center": (bbox_cx, bbox_cy),
            "yaw": yaw,
            "entry_world": (world_x, world_y, world_th),
            "polyline": polyline,
        })

        dx_l, dy_l, dth_l = tile["exit_displacement_local"]
        rot_d = _rotate((dx_l, dy_l), yaw)
        world_x += rot_d[0]
        world_y += rot_d[1]
        world_th = _wrap_pi(world_th + dth_l)

    return placements


def _sample_centreline(
    tile: dict, entry_x: float, entry_y: float, entry_heading: float
) -> List[Tuple[float, float]]:
    cl = tile["centreline"]
    if cl["type"] == "line":
        length = cl["length"]
        n = max(2, int(round(length / 0.1)))
        forward = (math.cos(entry_heading), math.sin(entry_heading))
        points: List[Tuple[float, float]] = []
        for i in range(n):
            s = (i / n) * length
            points.append((entry_x + forward[0] * s, entry_y + forward[1] * s))
        return points

    if cl["type"] == "arc":
        radius = cl["radius"]
        angle = cl["angle_rad"]
        direction = cl["direction"]
        left = (-math.sin(entry_heading), math.cos(entry_heading))
        if direction == "right":
            left = (-left[0], -left[1])
        centre = (entry_x + radius * left[0], entry_y + radius * left[1])
        start_angle = math.atan2(entry_y - centre[1], entry_x - centre[0])
        n = max(8, int(round(radius * angle / 0.1)))
        points = []
        sign = 1.0 if direction == "left" else -1.0
        for i in range(n):
            a = start_angle + sign * angle * (i / n)
            points.append((centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)))
        return points

    raise ValueError(f"Unknown centreline type: {cl['type']}")


def _texture_uri(world_dir: Path, texture_base: Path, texture_relpath: str) -> str:
    """Path relative to the world file, with POSIX separators.

    Gazebo resolves <albedo_map> against the world file's directory, so a
    relative path keeps the .world portable across hosts and across the
    source-tree vs colcon-install layouts (both preserve the same
    cobraflex/worlds <-> cobraflex/materials sibling relationship).
    """
    abs_tex = (texture_base / texture_relpath).resolve()
    rel = os.path.relpath(abs_tex, start=world_dir.resolve())
    return rel.replace(os.sep, "/")


def emit_world_sdf(
    world_name: str,
    placements: List[dict],
    texture_base: Path,
    world_dir: Path,
) -> str:
    parts = [
        "<?xml version=\"1.0\" ?>\n",
        "<sdf version='1.8'>\n",
        f"  <world name='{world_name}'>\n",
        "    <physics name='1ms' type='ignored'>\n",
        "      <max_step_size>0.001</max_step_size>\n",
        "      <real_time_factor>1</real_time_factor>\n",
        "    </physics>\n",
        OBSTACLES_WORLD_PLUGINS,
        GROUND_PLANE_BLOCK,
    ]

    for i, pl in enumerate(placements):
        tile = pl["tile"]
        bx, by = pl["bbox_center"]
        yaw = pl["yaw"]
        tex = _texture_uri(world_dir, texture_base, tile["texture_uri"])
        size_x = tile["bbox_w"]
        size_y = tile["bbox_h"]

        parts.append(f"""\
    <model name='tile_{i:02d}_{tile['kind']}'>
      <static>true</static>
      <pose>{bx:.4f} {by:.4f} {LIFT_Z_M:.4f}  0 0 {yaw:.6f}</pose>
      <link name='link'>
        <visual name='visual'>
          <geometry>
            <box>
              <size>{size_x:.4f} {size_y:.4f} {TILE_THICKNESS_M:.4f}</size>
            </box>
          </geometry>
          <material>
            <diffuse>1 1 1 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
            <pbr>
              <metal>
                <albedo_map>{tex}</albedo_map>
              </metal>
            </pbr>
          </material>
        </visual>
      </link>
    </model>
""")

    parts.append(SUN_LIGHT_BLOCK)
    parts.append("  </world>\n</sdf>\n")
    return "".join(parts)


def emit_centerline_yaml(
    placements: List[dict],
    lane_width: float,
    road_width: float,
    preset: str,
    straight_length: float,
    radius_m: float,
) -> dict:
    points: List[Tuple[float, float]] = []
    for pl in placements:
        points.extend(pl["polyline"])
    points.append(points[0])

    perimeter = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        perimeter += math.hypot(dx, dy)

    return {
        "centerline": {
            "geometry": preset,
            "straight_length_m": straight_length,
            "curve_radius_m": radius_m,
            "perimeter_m": round(perimeter, 4),
            "num_points": len(points),
            "points": [[round(x, 4), round(y, 4)] for x, y in points],
        },
        "lane_width": lane_width,
        "road_width": road_width,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", default="oval_R080", choices=["oval_R080", "oval_R050", "oval_R120"])
    parser.add_argument("--straight-length", type=float, default=1.5)
    parser.add_argument("--theme", default="clean", choices=list(STRAIGHT_THEME_TEXTURES.keys()))
    parser.add_argument("--world-name", default="lane_following_oval")
    parser.add_argument(
        "--world-out",
        type=Path,
        default=REPO_ROOT / "src" / "cobraflex" / "worlds" / "lane_following_oval.world",
    )
    parser.add_argument(
        "--centerline-out",
        type=Path,
        default=REPO_ROOT / "src" / "cobraflex_rl" / "config" / "oval_centerline.yaml",
    )
    parser.add_argument(
        "--texture-base",
        type=Path,
        default=REPO_ROOT / "src" / "cobraflex" / "materials",
        help=(
            "Filesystem path under which the road_assets directory lives. "
            "Absolute paths are baked into the world so it remains valid "
            "wherever Gazebo is launched from."
        ),
    )
    parser.add_argument("--lane-width", type=float, default=0.245)
    args = parser.parse_args()

    radius_map = {"oval_R080": 0.80, "oval_R050": 0.50, "oval_R120": 1.20}
    radius_m = radius_map[args.preset]

    texture_base = args.texture_base.resolve()
    if args.theme == "clean":
        clean_path = _ensure_clean_straight_png(args.straight_length, texture_base)
        straight_uri = str(clean_path.relative_to(texture_base)).replace(os.sep, "/")
    else:
        straight_uri = STRAIGHT_THEME_TEXTURES[args.theme]

    tiles = oval_preset(radius_m, args.straight_length, args.theme, straight_uri)
    placements = walk_sequence(tiles)

    args.world_out.parent.mkdir(parents=True, exist_ok=True)
    world_dir = args.world_out.resolve().parent
    world_sdf = emit_world_sdf(args.world_name, placements, texture_base, world_dir)
    args.world_out.write_text(world_sdf, encoding="utf-8")

    centerline_yaml = emit_centerline_yaml(
        placements,
        lane_width=args.lane_width,
        road_width=ROAD_WIDTH_M,
        preset=args.preset,
        straight_length=args.straight_length,
        radius_m=radius_m,
    )
    args.centerline_out.parent.mkdir(parents=True, exist_ok=True)
    with args.centerline_out.open("w", encoding="utf-8") as handle:
        handle.write(
            "# Generated by scripts/compose_lane_circuit.py.\n"
            "# Geometry derived from road_assets tile sizes; do not edit by hand.\n\n"
        )
        yaml.safe_dump(centerline_yaml, handle, sort_keys=False)

    print(f"World      -> {args.world_out}")
    print(f"Centerline -> {args.centerline_out}")
    print(f"Preset     : {args.preset}  radius={radius_m} m  L={args.straight_length} m")
    print(f"Tiles      : {len(placements)}")
    print(f"Perimeter  : {centerline_yaml['centerline']['perimeter_m']:.4f} m")
    print(f"Theme      : {args.theme}")


if __name__ == "__main__":
    main()
