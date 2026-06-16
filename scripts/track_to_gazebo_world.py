"""Emit a Gazebo .world for a generated complex track (one textured ground box).

Companion to scripts/generate_complex_track.py. Reuses the plugin set / ground /
sun and the box-UV convention of scripts/compose_lane_circuit.py so the road
renders matte and correctly oriented, and the camera-CV lane keeper sees the same
white-on-black markings it does on the oval worlds.

Run:
    python scripts/generate_complex_track.py --name complex_a
    python scripts/track_to_gazebo_world.py --name complex_a
    # -> src/cobraflex/worlds/lane_following_complex_a.world
    #    src/cobraflex/materials/road_assets/tracks/complex_a.png  (copied)
"""
from __future__ import annotations

import argparse
import math
import shutil
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import compose_lane_circuit as clc  # noqa: E402  reuse the proven world template


def emit(name: str) -> Path:
    tdir = REPO / "experiments/sim/tracks" / name
    meta = yaml.safe_load((tdir / f"{name}_meta.yaml").read_text())
    cx, cy = meta["center_m"]
    w_m, h_m = meta["size_m"]

    # Copy the texture next to the other road assets so the .world can reference
    # it with the same kind of relative path the oval worlds use.
    tex_dir = REPO / "src/cobraflex/materials/road_assets/tracks"
    tex_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(tdir / meta["texture"], tex_dir / meta["texture"])

    world_dir = REPO / "src/cobraflex/worlds"
    world_path = world_dir / f"lane_following_{name}.world"
    tex_uri = clc._texture_uri(
        world_dir, REPO / "src/cobraflex/materials",
        f"road_assets/tracks/{meta['texture']}")

    # Box-UV convention (see compose_lane_circuit.emit_world_sdf): image height
    # aligns with local +X, so swap size dims and rotate yaw +pi/2 to land the
    # top-down texture north-up in the world.
    yaw = math.pi / 2.0
    size_x, size_y = h_m, w_m

    parts = [
        "<?xml version=\"1.0\" ?>\n",
        "<sdf version='1.8'>\n",
        f"  <world name='lane_following_{name}'>\n",
        "    <physics name='1ms' type='ignored'>\n",
        "      <max_step_size>0.001</max_step_size>\n",
        "      <real_time_factor>1</real_time_factor>\n",
        "    </physics>\n",
        clc.OBSTACLES_WORLD_PLUGINS,
        clc.GROUND_PLANE_BLOCK,
        f"""\
    <model name='track_{name}'>
      <static>true</static>
      <pose>{cx:.4f} {cy:.4f} {clc.LIFT_Z_M:.4f}  0 0 {yaw:.6f}</pose>
      <link name='link'>
        <visual name='visual'>
          <geometry>
            <box>
              <size>{size_x:.4f} {size_y:.4f} {clc.TILE_THICKNESS_M:.4f}</size>
            </box>
          </geometry>
          <material>
            <diffuse>1 1 1 1</diffuse>
            <specular>0.05 0.05 0.05 1</specular>
            <pbr>
              <metal>
                <albedo_map>{tex_uri}</albedo_map>
                <roughness>0.9</roughness>
                <metalness>0.0</metalness>
              </metal>
            </pbr>
          </material>
        </visual>
      </link>
    </model>
""",
        clc.SUN_LIGHT_BLOCK,
        "  </world>\n</sdf>\n",
    ]
    world_path.write_text("".join(parts))

    # Recommended spawn: start-line point. Two-lane -> nudge into the right lane;
    # single-lane -> stay on the road centre (the only lane).
    sx, sy = meta["start_xy"]
    yaw0 = float(meta["start_yaw"])
    off = (meta.get("road_width", clc.ROAD_WIDTH_M) / 4.0
           if meta.get("lanes", 2) == 2 else 0.0)
    rx, ry = sx + off * math.sin(yaw0), sy - off * math.cos(yaw0)
    print(f"[world] wrote {world_path.relative_to(REPO)}")
    print(f"[world] texture -> {(tex_dir / meta['texture']).relative_to(REPO)}")
    print("[world] launch the PD lane keeper with:")
    print(f"    ros2 launch cobraflex lane_keeper_gazebo.launch.py \\\n"
          f"        world:=$(ros2 pkg prefix cobraflex)/share/cobraflex/worlds/"
          f"lane_following_{name}.world \\\n"
          f"        spawn_x:={rx:.3f} spawn_y:={ry:.3f} spawn_z:=0.05 "
          f"spawn_yaw:={yaw0:.3f}")
    return world_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="complex_a")
    emit(ap.parse_args().name)


if __name__ == "__main__":
    main()
