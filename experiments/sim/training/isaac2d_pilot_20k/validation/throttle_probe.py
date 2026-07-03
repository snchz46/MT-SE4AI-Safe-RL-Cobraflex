"""One-off D-50 validation probe: C-04 (speed attenuation) vs C-06 (throttle
rate limit) interplay on the live Isaac env.

Steps the real 2-D env with a scripted action [steer=0, throttle=+1] from the
complex_b start (pinned circuit, DR + spawn perturbation disabled) and logs
speed / raw / safe throttle / interventions per step to a CSV. Shows whether
the commanded speed ramps cleanly to the 0.5 m/s straight ceiling and what
happens when the curve ceiling (0.25 m/s) drops below the commanded speed.

Run:  ~/isaacsim/python.sh throttle_probe.py out.csv
"""
import csv
import os
import sys

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

REPO = "/media/samuel/Fast_SSD/SE4AI/thesis_repo"
for p in (os.path.join(REPO, "tools"), REPO, os.path.join(REPO, "src", "cobraflex_rl")):
    if p not in sys.path:
        sys.path.insert(0, p)

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
simulation_app.update()

import numpy as np  # noqa: E402
import omni.usd  # noqa: E402
import yaml  # noqa: E402

import isaac_scene  # noqa: E402

rc = 1
try:
    out_csv = sys.argv[1] if len(sys.argv) > 1 else "throttle_probe.csv"
    cfg_path = os.path.join(REPO, "src/cobraflex_rl/config/train_isaac_2d.yaml")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    # Deterministic probe: no DR, no spawn perturbation, no reward normalization.
    for k in ("domain_randomization", "dynamics_randomization",
              "scene_randomization", "spawn_perturbation"):
        cfg.setdefault(k, {})["enabled"] = False

    os.environ["TRACK"] = "complex_b,complex_d,complex_e"
    from isaacsim.core.prims import SingleArticulation

    world, track_metas = isaac_scene.build_world()
    stage = omni.usd.get_context().get_stage()
    cam_path = isaac_scene.make_lane_camera(stage)
    world.reset()

    enable_extension("omni.replicator.core")
    import omni.replicator.core as rep

    rp = rep.create.render_product(
        cam_path, (isaac_scene.LANE_CAM_W, isaac_scene.LANE_CAM_H))
    annotator = rep.AnnotatorRegistry.get_annotator("rgb")
    annotator.attach(rp)

    art_root = isaac_scene.articulation_root(stage)
    articulation = SingleArticulation(prim_path=art_root, name="cobra")
    articulation.initialize()
    wheel_dof = [articulation.get_dof_index(j) for j in isaac_scene.WHEEL_JOINTS]
    physics_dt = float(getattr(world, "get_physics_dt", lambda: 1.0 / 60.0)())

    from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv
    from cobraflex_rl.isaac_interface import IsaacSimInterface

    interface = IsaacSimInterface(
        world, articulation, wheel_dof,
        wheel_radius=isaac_scene.WHEEL_RADIUS,
        wheel_separation=isaac_scene.WHEEL_SEPARATION,
        physics_dt=physics_dt, spawn_z=isaac_scene.SPAWN_Z,
        annotator=annotator, render_always=False, randomizer=None)
    for _ in range(5):
        interface.wait_for_initial_data()

    circuits, _meta = isaac_scene.load_circuits(
        isaac_scene.parse_track_names(), track_metas)
    env = GazeboLaneEnv(ros_interface=interface, cfg=cfg, circuits=circuits)

    obs, _ = env.reset(seed=2024, options={"circuit_index": 0})
    action = np.array([0.0, 1.0], dtype=np.float32)
    rows = []
    for t in range(150):
        obs, r, term, trunc, info = env.step(action)
        rows.append((
            t,
            f"{info.get('speed', float('nan')):.4f}",
            f"{info.get('raw_throttle', float('nan')):.4f}",
            f"{info.get('safe_throttle', float('nan')):.4f}",
            f"{info.get('lateral_error', float('nan')):.4f}"
            if "lateral_error" in info else "",
            "|".join(info.get("cage_interventions", [])),
            int(bool(info.get("cage_emergency", False))),
            info.get("termination_reason", ""),
        ))
        if term or trunc:
            break
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["step", "speed_mps", "raw_throttle", "safe_throttle",
                    "lateral_error", "interventions", "emergency", "termination"])
        w.writerows(rows)
    print(f"[probe] {len(rows)} steps -> {out_csv}; "
          f"last: speed={rows[-1][1]} safe_u={rows[-1][3]} term={rows[-1][7]!r}")
    env.close()
    interface.destroy_node()
    rc = 0
except Exception:
    import traceback

    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
