"""In-process PPO training inside Isaac Sim (Gazebo-free RL training path).

Run with Isaac Sim's bundled python (which must also have stable-baselines3 +
gymnasium installed):

    ~/isaacsim/python.sh tools/isaac_train.py                     # state-vector (F3)
    TRACK=complex_b ~/isaacsim/python.sh tools/isaac_train.py \\
        --train-config      src/cobraflex_rl/config/train_ppo_camera.yaml \\
        --centerline-config src/cobraflex_rl/config/complex_b_right_lane_centerline.yaml \\
        --road-centerline-config src/cobraflex_rl/config/complex_b_centerline.yaml

This is option-2 of the Gazebo→Isaac migration: instead of driving Isaac over a
ROS2 bridge and resetting episodes via ``gz service set_pose`` (Gazebo-only, and
*not* exposed by tools/isaac_ros2_bringup.py), the gym env drives the live Isaac
``World`` directly through :class:`~cobraflex_rl.isaac_interface.IsaacSimInterface`:
per-episode teleport = ``set_world_pose``, actuation = wheel ``ArticulationAction``,
advance = ``world.step()``, camera = a Replicator render product on the Lane Cam.
No ``gz`` CLI, no ROS round-trip — training and the bring-up command are fully
decoupled (they share only the physics scene, ``tools/isaac_scene.py``).

The SB3 wiring (PPO, frame-stack for the camera obs, callbacks, reproducibility
metadata) mirrors ``cobraflex_rl/train_ppo.py`` so checkpoints are comparable.

NB: ``TRACK`` selects the *visual* scene track (isaac_scene.build_world); the
``--centerline-config`` selects the env's *geometry* — they must correspond.
"""
import argparse
import os
import sys

# --- Isaac must come up before any omni/isaacsim/pxr import -------------------
from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp({"headless": True})

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
simulation_app.update()

# --- Now the rest (omni + our packages). Make cage/ + cobraflex_rl importable -
import math  # noqa: E402

import omni.usd  # noqa: E402

import isaac_scene  # noqa: E402  (sibling module in tools/)

REPO = isaac_scene.REPO
for _p in (REPO, os.path.join(REPO, "src", "cobraflex_rl")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import json  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.env_checker import check_env  # noqa: E402
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback  # noqa: E402
from stable_baselines3.common.monitor import Monitor  # noqa: E402
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack  # noqa: E402

from cobraflex_rl.callbacks import (  # noqa: E402
    ActionSampleCallback,
    LearningCurveCallback,
    ProgressBarCallback,
)
from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv  # noqa: E402
from cobraflex_rl.isaac_interface import IsaacSimInterface  # noqa: E402
from cobraflex_rl.run_io import git_commit, sha256_file  # noqa: E402

SCENARIO_ID = "SC-NOM-01"


def parse_args(argv):
    p = argparse.ArgumentParser(description="In-process Isaac-Sim PPO trainer.")
    p.add_argument("--train-config", type=str,
                   default=os.path.join(REPO, "src/cobraflex_rl/config/train_ppo.yaml"))
    p.add_argument("--centerline-config", type=str,
                   default=os.path.join(
                       REPO, "src/cobraflex_rl/config/oval_right_lane_centerline.yaml"))
    p.add_argument("--road-centerline-config", type=str, default=None,
                   help="Road-centre centerline YAML for off-road geometry "
                        "(self-approaching circuits, e.g. complex_b).")
    p.add_argument("--model-path", type=str, default=None)
    p.add_argument("--run-id", type=str, default=None)
    p.add_argument("--resume-from", type=str, default=None)
    return p.parse_args(argv)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve_save_path(path: Path) -> Path:
    return path if path.suffix == ".zip" else path.with_suffix(".zip")


def resolve_cage_yaml(train_cfg) -> Path:
    explicit = train_cfg.get("cage", {}).get("yaml_path", "") or ""
    if explicit and Path(explicit).is_file():
        return Path(explicit)
    return Path(REPO) / "cage" / "cage.yaml"


def repo_subdir(*parts) -> Path:
    target = Path(REPO).joinpath(*parts)
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_isaac_interface(train_cfg):
    """Build the physics scene, init the articulation + (optional) Lane Cam
    render product, and wrap them in an IsaacSimInterface."""
    from isaacsim.core.prims import SingleArticulation

    obs_cfg = dict(train_cfg.get("observation", {}))
    camera_obs = str(obs_cfg.get("type", "state")) == "camera"

    world, _track_meta = isaac_scene.build_world()
    stage = omni.usd.get_context().get_stage()

    # The Lane Cam USD prim is a stage edit — do it before world.reset(). The
    # Replicator render product is created *after* reset (proven order, cf. the
    # bring-up's --cam-shot path).
    cam_path = None
    if camera_obs:
        cam_path = isaac_scene.make_lane_camera(stage)
        if cam_path is None:
            raise RuntimeError(
                f"Lane Cam frame '{isaac_scene.LANE_CAM_FRAME}' not found in the "
                "stage; cannot build the camera render product.")

    world.reset()

    annotator = None
    if camera_obs:
        enable_extension("omni.replicator.core")
        import omni.replicator.core as rep
        rp = rep.create.render_product(
            cam_path, (isaac_scene.LANE_CAM_W, isaac_scene.LANE_CAM_H))
        annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        annotator.attach(rp)

    art_root = isaac_scene.articulation_root(stage)
    articulation = SingleArticulation(prim_path=art_root, name="cobra")
    articulation.initialize()
    wheel_dof_indices = [articulation.get_dof_index(j) for j in isaac_scene.WHEEL_JOINTS]
    print(f"[isaac_train] articulation root {art_root}; wheel dof {wheel_dof_indices}")

    physics_dt = float(getattr(world, "get_physics_dt", lambda: 1.0 / 60.0)())

    interface = IsaacSimInterface(
        world,
        articulation,
        wheel_dof_indices,
        wheel_radius=isaac_scene.WHEEL_RADIUS,
        wheel_separation=isaac_scene.WHEEL_SEPARATION,
        physics_dt=physics_dt,
        spawn_z=isaac_scene.SPAWN_Z,
        annotator=annotator,
    )
    # Warm-up: settle physics + populate the first camera frame before training.
    for _ in range(5):
        interface.wait_for_initial_data()
    return interface, camera_obs


def write_metadata(run_dir, run_id, seed, train_cfg, centerline_path, cage_yaml,
                   model_path, total_timesteps, status):
    metadata = {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "mode": str(train_cfg.get("cage", {}).get("mode", "enforcement")),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(run_dir),
        "cage_yaml": str(cage_yaml),
        "cage_yaml_hash": sha256_file(cage_yaml),
        "scenario_yaml_hash": sha256_file(centerline_path),
        "policy_checkpoint": str(resolve_save_path(model_path)),
        "policy_checkpoint_hash": sha256_file(resolve_save_path(model_path)),
        "seed": seed,
        "platform": "sim-isaac",
        "total_timesteps": total_timesteps,
        "policy": str(train_cfg.get("policy", "MlpPolicy")),
        "observation": dict(train_cfg.get("observation", {})),
        "domain_randomization": dict(train_cfg.get("domain_randomization", {})),
        "status": status,
    }
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)


def main(argv):
    cli = parse_args(argv)
    train_cfg = load_yaml(cli.train_config)
    centerline_cfg = load_yaml(cli.centerline_config)

    seed = int(train_cfg.get("seed", 42))
    total_timesteps = int(train_cfg.get("total_timesteps", 50000))
    run_id = cli.run_id or "isaac_ppo_train_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")
    run_dir = repo_subdir("experiments", "sim", "training", run_id)
    checkpoints_dir = repo_subdir("policy", "checkpoints")
    cage_yaml = resolve_cage_yaml(train_cfg)

    model_path = Path(cli.model_path or train_cfg.get("model_path", "cobraflex_ppo_lane"))
    model_path = model_path.expanduser()
    model_path.parent.mkdir(parents=True, exist_ok=True)

    road_centerline_points = None
    if cli.road_centerline_config:
        road_centerline_points = np.asarray(
            load_yaml(cli.road_centerline_config)["centerline"]["points"], dtype=float)

    status = "failed"
    env = None
    interface = None
    try:
        interface, camera_obs = build_isaac_interface(train_cfg)

        centerline_points = np.asarray(centerline_cfg["centerline"]["points"], dtype=float)
        lane_width = float(centerline_cfg["lane_width"])
        road_width = float(centerline_cfg.get("road_width", lane_width))

        env = GazeboLaneEnv(
            ros_interface=interface,
            centerline=centerline_points,
            lane_width=lane_width,
            road_width=road_width,
            cfg=train_cfg,
            road_centerline=road_centerline_points,
        )
        check_env(env, warn=True, skip_render_check=True)

        policy_name = str(train_cfg.get("policy", "MlpPolicy"))
        obs_cfg = dict(train_cfg.get("observation", {}))
        if camera_obs:
            frame_stack = int(obs_cfg.get("camera", {}).get("frame_stack", 4))
            train_env = VecFrameStack(
                DummyVecEnv([lambda: Monitor(env)]), n_stack=frame_stack)
        else:
            train_env = env

        if cli.resume_from:
            model = PPO.load(cli.resume_from, env=train_env,
                             device=str(train_cfg.get("device", "cpu")), verbose=1)
            print(f"[isaac_train] resumed PPO from {cli.resume_from} at "
                  f"{model.num_timesteps} steps")
        else:
            model = PPO(
                policy=policy_name,
                env=train_env,
                learning_rate=float(train_cfg.get("learning_rate", 3.0e-4)),
                gamma=float(train_cfg.get("gamma", 0.99)),
                n_steps=int(train_cfg.get("n_steps", 1024)),
                batch_size=int(train_cfg.get("batch_size", 64)),
                device=str(train_cfg.get("device", "cpu")),
                seed=seed,
                verbose=1,
            )

        checkpoint_freq = int(train_cfg.get("checkpoint_freq", train_cfg.get("n_steps", 1024)))
        callback = CallbackList([
            ProgressBarCallback(total_timesteps=total_timesteps),
            LearningCurveCallback(csv_path=run_dir / "learning_curve.csv"),
            ActionSampleCallback(
                csv_path=run_dir / "action_samples.csv",
                sample_every=int(train_cfg.get("action_sample_every", 10)),
            ),
            CheckpointCallback(save_freq=checkpoint_freq, save_path=str(checkpoints_dir),
                               name_prefix="cobraflex_ppo_lane"),
        ])

        model.learn(total_timesteps=total_timesteps, callback=callback,
                    reset_num_timesteps=not cli.resume_from)
        model.save(str(model_path))
        status = "completed"
        print(f"[isaac_train] saved PPO model to {resolve_save_path(model_path)}")
        print(f"[isaac_train] learning curve + metadata under {run_dir}")
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass
        if interface is not None:
            interface.destroy_node()
        write_metadata(run_dir, run_id, seed, train_cfg, Path(cli.centerline_config),
                       cage_yaml, model_path, total_timesteps, status)
    return 0 if status == "completed" else 1


_argv = [a for a in sys.argv[1:]]
try:
    rc = main(_argv)
except Exception:
    import traceback
    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
