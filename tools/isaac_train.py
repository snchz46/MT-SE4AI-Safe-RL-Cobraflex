"""In-process PPO training inside Isaac Sim (Gazebo-free RL training path).

Run with Isaac Sim's bundled python (which must also have stable-baselines3 +
gymnasium installed):

    # DEFAULT (D-50): full-authority 2-D action (steering + throttle) camera PPO
    # on the multi-circuit scene complex_b,complex_d,complex_e
    # (train_isaac_2d.yaml). 1st run: re-import USD.
    BRINGUP_REIMPORT=1 ~/isaacsim/python.sh tools/isaac_train.py
    # Single-track 1-D camera PPO (the frozen Gazebo E-main recipe):
    ~/isaacsim/python.sh tools/isaac_train.py --track complex_b \\
        --train-config src/cobraflex_rl/config/train_ppo_camera.yaml
    # F3 state-vector on the oval — override everything:
    ~/isaacsim/python.sh tools/isaac_train.py --track oval \\
        --train-config      src/cobraflex_rl/config/train_ppo.yaml \\
        --centerline-config src/cobraflex_rl/config/oval_right_lane_centerline.yaml \\
        --road-centerline-config ''

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

Track selection: ``--track`` (or the ``TRACK`` env) selects the *visual* scene
track(s) (isaac_scene.build_world). A comma-separated list builds a multi-track
scene and the env samples one circuit per episode (D-50); the per-track env
geometry is then resolved BY CONVENTION from
``src/cobraflex_rl/config/<name>_right_lane_centerline.yaml`` (reward lane) +
``<name>_centerline.yaml`` (road centre, off-road check), shifted by the same
world offsets the scene applied. With a single track the explicit
``--centerline-config``/``--road-centerline-config`` flags select the geometry
as before — they must correspond to the track.
"""
import argparse
import os
import sys

# --- Isaac must come up before any omni/isaacsim/pxr import -------------------
from isaacsim import SimulationApp  # noqa: E402


def _preparse_render(argv):
    """SimulationApp must be configured *before* argparse runs in main(), so peek
    at the render mode (and nothing else) from argv / the ISAAC_RENDER env var.
    'gui' opens the native viewport (slower, for human visual assessment);
    'headless' (default) renders nothing and trains as fast as the host allows."""
    mode = os.environ.get("ISAAC_RENDER", "headless")
    for i, a in enumerate(argv):
        if a == "--render" and i + 1 < len(argv):
            mode = argv[i + 1]
        elif a.startswith("--render="):
            mode = a.split("=", 1)[1]
    return mode.strip().lower()


RENDER_MODE = _preparse_render(sys.argv[1:])
simulation_app = SimulationApp({"headless": RENDER_MODE != "gui"})
print(f"[isaac_train] render mode: {RENDER_MODE} "
      f"(headless={RENDER_MODE != 'gui'})", flush=True)

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
from stable_baselines3.common.callbacks import (  # noqa: E402
    BaseCallback,
    CallbackList,
    CheckpointCallback,
)
from stable_baselines3.common.monitor import Monitor  # noqa: E402
from stable_baselines3.common.vec_env import (  # noqa: E402
    DummyVecEnv,
    VecEnv,
    VecFrameStack,
    VecNormalize,
)

from cobraflex_rl.callbacks import (  # noqa: E402
    ActionSampleCallback,
    LearningCurveCallback,
    ProgressBarCallback,
)
from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv  # noqa: E402
from cobraflex_rl.isaac_interface import IsaacSimInterface  # noqa: E402
from cobraflex_rl.run_io import git_commit, sha256_file  # noqa: E402

SCENARIO_ID = "SC-NOM-01"


# --- PPO stability resolvers (mirror cobraflex_rl.train_ppo). isaac_train reads
# the SAME train config, so it must honour the same target_kl / lr_schedule /
# reward-normalization keys — otherwise it is the same brakeless PPO that the
# Gazebo 1M pilot collapsed under (approx_kl runaway) and sawtoothed (critic
# chasing returns ~700). Kept in lockstep with train_ppo's _resolve_* helpers. --
def _linear_schedule(initial_value):
    """initial_value at the start of training, linearly annealed to 0 at the end."""

    def schedule(progress_remaining):
        return float(progress_remaining) * float(initial_value)

    return schedule


def _resolve_learning_rate(train_cfg):
    """Return the LR (float) or a linear-anneal schedule per ``lr_schedule``."""
    base_lr = float(train_cfg.get("learning_rate", 3.0e-4))
    if str(train_cfg.get("lr_schedule", "constant")).lower() == "linear":
        return _linear_schedule(base_lr)
    return base_lr


def _resolve_target_kl(train_cfg):
    """Trust-region KL early-stop (SB3 ``target_kl``); None disables it."""
    value = train_cfg.get("target_kl", None)
    return float(value) if value is not None else None


def _resolve_clip_range_vf(train_cfg):
    """Value-function clipping (SB3 ``clip_range_vf``); None disables it. Only
    meaningful alongside ``normalize_reward`` (normalized critic scale)."""
    value = train_cfg.get("clip_range_vf", None)
    return float(value) if value is not None else None


class ObsPreviewCallback(BaseCallback):
    """Live preview of the agent's camera observation — the exact (possibly
    degraded) grayscale frame the CNN sees this step — upscaled into an OpenCV
    window, refreshed every ``every`` env steps. For visual sanity-checking at
    the cost of compute; needs OpenCV + a display, else it disables itself."""

    def __init__(self, every: int = 15, scale: int = 5) -> None:
        super().__init__()
        self.every = max(1, int(every))
        self.scale = max(1, int(scale))
        self._cv2 = None
        self._ok = False
        self._win = "agent obs (CNN input)"

    def _on_training_start(self) -> None:
        try:
            import cv2

            self._cv2 = cv2
            cv2.namedWindow(self._win, cv2.WINDOW_NORMAL)
            self._ok = True
            print("[isaac_train] --show-obs window open", flush=True)
        except Exception as exc:  # pragma: no cover - display/cv2 absent
            print(f"[isaac_train] --show-obs disabled ({exc})", flush=True)
            self._ok = False

    def _frame_from_obs(self, obs):
        arr = np.asarray(obs)
        if arr.ndim == 4:  # (n_env, H, W, stack) — most recent frame, env 0
            arr = arr[0]
        if arr.ndim != 3:
            return None
        # channels-last (H, W, C) vs channels-first (C, H, W): pick the newest frame
        if arr.shape[-1] in (1, 3, 4):
            return arr[:, :, -1]
        if arr.shape[0] in (1, 3, 4):
            return arr[-1]
        return None

    def _on_step(self) -> bool:
        if not self._ok or self.num_timesteps % self.every != 0:
            return True
        frame = self._frame_from_obs(self.locals.get("new_obs"))
        if frame is None:
            return True
        frame = frame.astype(np.uint8)
        big = self._cv2.resize(
            frame, (frame.shape[1] * self.scale, frame.shape[0] * self.scale),
            interpolation=self._cv2.INTER_NEAREST)
        self._cv2.imshow(self._win, big)
        self._cv2.waitKey(1)
        return True

    def _on_training_end(self) -> None:
        if self._ok:
            try:
                self._cv2.destroyWindow(self._win)
            except Exception:  # pragma: no cover - best effort
                pass


class StopFileCallback(BaseCallback):
    """Graceful early stop: `touch <run_dir>/STOP` ends learn() at the next
    check, so the final model save + metadata write in main() still run.
    Needed because SIGINT hard-kills the kit process before any Python
    `finally` executes (verified 03.07.2026 on the 1M run: no metadata, no
    final save) — signals are NOT a usable stop mechanism under Isaac."""

    def __init__(self, stop_file, check_every: int = 256) -> None:
        super().__init__()
        self.stop_file = Path(stop_file)
        self.check_every = max(1, int(check_every))

    def _on_step(self) -> bool:
        if self.num_timesteps % self.check_every == 0 and self.stop_file.exists():
            print(f"[isaac_train] STOP file {self.stop_file} found -> ending "
                  "training gracefully (model + metadata will be written)",
                  flush=True)
            return False
        return True


def parse_args(argv):
    p = argparse.ArgumentParser(description="In-process Isaac-Sim PPO trainer.")
    # The Isaac 2-D full-authority config (D-50) is the default; it carries the
    # PPO stability keys (target_kl, lr_schedule, normalize_reward,
    # clip_range_vf) plus the `action: steer_throttle` block. Override with
    # train_ppo_camera.yaml (frozen 1-D E-main recipe) or train_ppo.yaml (F3
    # state-vector, no stability keys).
    p.add_argument("--train-config", type=str,
                   default=os.path.join(REPO, "src/cobraflex_rl/config/train_isaac_2d.yaml"))
    # Single-track geometry flags. With a multi-track --track (comma list) these
    # are IGNORED — the per-track geometry comes from the config-dir naming
    # convention instead (see module docstring).
    p.add_argument("--centerline-config", type=str,
                   default=os.path.join(
                       REPO, "src/cobraflex_rl/config/complex_b_right_lane_centerline.yaml"))
    p.add_argument("--road-centerline-config", type=str,
                   default=os.path.join(REPO, "src/cobraflex_rl/config/complex_b_centerline.yaml"),
                   help="Road-centre centerline YAML for off-road geometry "
                        "(self-approaching circuits, e.g. complex_b). Single-track only.")
    p.add_argument("--track", type=str,
                   default=os.environ.get("TRACK", "complex_b,complex_d,complex_e"),
                   help="Visual scene track(s) for isaac_scene.build_world (sets "
                        "the TRACK env). A comma-separated list builds a "
                        "multi-track scene with per-episode circuit sampling "
                        "(D-50). Defaults to the TRACK env if set, else the "
                        "CV-safe trio complex_b,complex_d,complex_e. A single "
                        "name must match the --centerline-config geometry.")
    p.add_argument("--model-path", type=str, default=None)
    p.add_argument("--run-id", type=str, default=None)
    p.add_argument("--resume-from", type=str, default=None)
    # --- visual assessment (at the cost of compute) -------------------------
    p.add_argument("--render", choices=["headless", "gui"], default="headless",
                   help="'gui' opens the native Isaac viewport to watch the car "
                        "drive (slow); 'headless' (default) renders nothing. "
                        "Parsed before SimulationApp; repeated here for --help.")
    p.add_argument("--show-obs", action="store_true",
                   help="Live OpenCV window of the exact camera frame the CNN "
                        "sees each step (camera obs only). Needs OpenCV + a "
                        "display; disables itself otherwise.")
    p.add_argument("--obs-preview-every", type=int, default=15,
                   help="Refresh the --show-obs window every N env steps.")
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


def build_isaac_interface(train_cfg, render_always: bool = False, seed: int = 0):
    """Build the physics scene, init the articulation + (optional) Lane Cam
    render product, and wrap them in an IsaacSimInterface. When the train config
    enables ``dynamics_randomization`` and/or ``scene_randomization``, an
    :class:`isaac_dr.IsaacDomainRandomizer` (seeded by ``seed``) is attached so
    each episode reset re-samples physics/scene/latency (sim-to-real DR)."""
    from isaacsim.core.prims import SingleArticulation

    obs_cfg = dict(train_cfg.get("observation", {}))
    camera_obs = str(obs_cfg.get("type", "state")) == "camera"

    world, track_metas = isaac_scene.build_world()
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

    # Physics/scene/latency domain randomization (sim-to-real levers #2/#3/#4),
    # attached only when enabled in the config so existing deterministic runs and
    # the Gazebo path are unaffected. Seeded by `seed` for a reproducible episode
    # stream that mirrors the PPO seed.
    randomizer = None
    dyn_cfg = dict(train_cfg.get("dynamics_randomization", {}))
    scene_cfg = dict(train_cfg.get("scene_randomization", {}))
    if dyn_cfg.get("enabled") or scene_cfg.get("enabled"):
        from isaac_dr import IsaacDomainRandomizer  # sibling module in tools/
        randomizer = IsaacDomainRandomizer(
            stage,
            articulation,
            dynamics_cfg=dyn_cfg,
            scene_cfg=scene_cfg,
            seed=seed,
            scene_paths=isaac_scene.dr_scene_paths(stage, art_root),
        )
        print(f"[isaac_train] domain randomization active "
              f"(dynamics={bool(dyn_cfg.get('enabled'))}, "
              f"scene={bool(scene_cfg.get('enabled'))}, seed={seed})")

    interface = IsaacSimInterface(
        world,
        articulation,
        wheel_dof_indices,
        wheel_radius=isaac_scene.WHEEL_RADIUS,
        wheel_separation=isaac_scene.WHEEL_SEPARATION,
        physics_dt=physics_dt,
        spawn_z=isaac_scene.SPAWN_Z,
        annotator=annotator,
        render_always=render_always,
        randomizer=randomizer,
    )
    # Warm-up: settle physics + populate the first camera frame before training.
    for _ in range(5):
        interface.wait_for_initial_data()
    return interface, camera_obs, track_metas


def write_metadata(run_dir, run_id, seed, train_cfg, train_cfg_path, centerline_path,
                   cage_yaml, model_path, total_timesteps, status, circuits_meta=None):
    metadata = {
        "run_id": run_id,
        "scenario_id": SCENARIO_ID,
        "mode": str(train_cfg.get("cage", {}).get("mode", "enforcement")),
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(run_dir),
        "train_config": str(train_cfg_path),
        "train_config_hash": sha256_file(train_cfg_path),
        "cage_yaml": str(cage_yaml),
        "cage_yaml_hash": sha256_file(cage_yaml),
        # Single-track runs: hash of the one centerline YAML (legacy field).
        # Multi-track runs record per-circuit paths + hashes in "circuits".
        "scenario_yaml_hash": (
            sha256_file(centerline_path) if circuits_meta is None else None
        ),
        "circuits": circuits_meta,
        "policy_checkpoint": str(resolve_save_path(model_path)),
        "policy_checkpoint_hash": sha256_file(resolve_save_path(model_path)),
        "seed": seed,
        "platform": "sim-isaac",
        "total_timesteps": total_timesteps,
        "hyperparameters": {
            "learning_rate": float(train_cfg.get("learning_rate", 3.0e-4)),
            "lr_schedule": str(train_cfg.get("lr_schedule", "constant")).lower(),
            "gamma": float(train_cfg.get("gamma", 0.99)),
            "n_steps": int(train_cfg.get("n_steps", 1024)),
            "batch_size": int(train_cfg.get("batch_size", 64)),
            "n_epochs": int(train_cfg.get("n_epochs", 10)),
            "gae_lambda": float(train_cfg.get("gae_lambda", 0.95)),
            "clip_range": float(train_cfg.get("clip_range", 0.2)),
            "ent_coef": float(train_cfg.get("ent_coef", 0.0)),
            "vf_coef": float(train_cfg.get("vf_coef", 0.5)),
            "max_grad_norm": float(train_cfg.get("max_grad_norm", 0.5)),
            "target_kl": _resolve_target_kl(train_cfg),
            "clip_range_vf": _resolve_clip_range_vf(train_cfg),
            "normalize_reward": bool(train_cfg.get("normalize_reward", False)),
        },
        "policy": str(train_cfg.get("policy", "MlpPolicy")),
        "observation": dict(train_cfg.get("observation", {})),
        "action": dict(train_cfg.get("action", {})),
        # Reward weights (docs/10 + the D-50/D-56 2-D terms) — kept in lockstep
        # with train_ppo._write_training_metadata.
        "reward": dict(train_cfg.get("reward", {})),
        "domain_randomization": dict(train_cfg.get("domain_randomization", {})),
        "dynamics_randomization": dict(train_cfg.get("dynamics_randomization", {})),
        "scene_randomization": dict(train_cfg.get("scene_randomization", {})),
        "status": status,
    }
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)


def main(argv):
    cli = parse_args(argv)
    # isaac_scene.add_track reads TRACK from the environment at build_world() time
    # (runtime), so fold the CLI choice in here — before the scene is built — so the
    # visual track matches the --centerline-config geometry and the no-arg default
    # is coherent (complex_b), not isaac_scene's bare complex_a fallback.
    os.environ["TRACK"] = cli.track
    train_cfg = load_yaml(cli.train_config)
    track_names = isaac_scene.parse_track_names(cli.track)
    multi_track = len(track_names) > 1
    if multi_track:
        print(f"[isaac_train] multi-track scene {track_names}: per-episode "
              "circuit sampling; --centerline-config/--road-centerline-config "
              "ignored (config-dir naming convention applies).")

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

    status = "failed"
    circuits_meta = None
    env = None
    interface = None
    try:
        interface, camera_obs, track_metas = build_isaac_interface(
            train_cfg, render_always=(cli.render == "gui"), seed=seed)

        if multi_track:
            circuits, circuits_meta = isaac_scene.load_circuits(
                track_names, track_metas)
            env = GazeboLaneEnv(
                ros_interface=interface,
                cfg=train_cfg,
                circuits=circuits,
            )
        else:
            centerline_cfg = load_yaml(cli.centerline_config)
            road_centerline_points = None
            if cli.road_centerline_config:
                road_centerline_points = np.asarray(
                    load_yaml(cli.road_centerline_config)["centerline"]["points"],
                    dtype=float)
            centerline_points = np.asarray(
                centerline_cfg["centerline"]["points"], dtype=float)
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

        # Optional reward normalization (VecNormalize, norm_reward only): keeps the
        # critic's targets ~O(1) so the large reward scale doesn't destabilise it —
        # the value-function root cause of the Gazebo 1M sawtooth. norm_obs stays
        # False, so eval/inference need no normalization stats. Mirrors train_ppo.
        normalize_reward = bool(train_cfg.get("normalize_reward", False))
        if normalize_reward:
            if not isinstance(train_env, VecEnv):
                train_env = DummyVecEnv([lambda: Monitor(env)])
            train_env = VecNormalize(
                train_env,
                norm_obs=False,
                norm_reward=True,
                gamma=float(train_cfg.get("gamma", 0.99)),
                clip_reward=float(train_cfg.get("clip_reward", 10.0)),
            )

        if cli.resume_from:
            model = PPO.load(cli.resume_from, env=train_env,
                             device=str(train_cfg.get("device", "cpu")), verbose=1)
            # PPO.load restores the checkpoint's hyperparameters; re-apply the
            # trust-region brake from the current config (else resume keeps None).
            model.target_kl = _resolve_target_kl(train_cfg)
            print(f"[isaac_train] resumed PPO from {cli.resume_from} at "
                  f"{model.num_timesteps} steps")
        else:
            model = PPO(
                policy=policy_name,
                env=train_env,
                # learning_rate may be a float or a linear-anneal schedule
                # (lr_schedule: linear); target_kl is the trust-region brake.
                learning_rate=_resolve_learning_rate(train_cfg),
                gamma=float(train_cfg.get("gamma", 0.99)),
                n_steps=int(train_cfg.get("n_steps", 1024)),
                batch_size=int(train_cfg.get("batch_size", 64)),
                n_epochs=int(train_cfg.get("n_epochs", 10)),
                gae_lambda=float(train_cfg.get("gae_lambda", 0.95)),
                clip_range=float(train_cfg.get("clip_range", 0.2)),
                ent_coef=float(train_cfg.get("ent_coef", 0.0)),
                vf_coef=float(train_cfg.get("vf_coef", 0.5)),
                max_grad_norm=float(train_cfg.get("max_grad_norm", 0.5)),
                target_kl=_resolve_target_kl(train_cfg),
                clip_range_vf=_resolve_clip_range_vf(train_cfg),
                device=str(train_cfg.get("device", "cpu")),
                seed=seed,
                verbose=1,
            )

        checkpoint_freq = int(train_cfg.get("checkpoint_freq", train_cfg.get("n_steps", 1024)))
        stop_file = run_dir / "STOP"
        callbacks = [
            StopFileCallback(stop_file),
            ProgressBarCallback(total_timesteps=total_timesteps, tty_fallback=True),
            LearningCurveCallback(csv_path=run_dir / "learning_curve.csv"),
            ActionSampleCallback(
                csv_path=run_dir / "action_samples.csv",
                sample_every=int(train_cfg.get("action_sample_every", 10)),
            ),
            # Per-run checkpoint prefix: the old fixed "cobraflex_ppo_lane" made
            # every run overwrite the previous run's same-step checkpoints.
            CheckpointCallback(save_freq=checkpoint_freq, save_path=str(checkpoints_dir),
                               name_prefix=run_id,
                               save_vecnormalize=normalize_reward),
        ]
        if cli.show_obs:
            if camera_obs:
                callbacks.append(ObsPreviewCallback(every=cli.obs_preview_every))
            else:
                print("[isaac_train] --show-obs ignored: observation.type is not "
                      "'camera' (no frame to preview).", flush=True)
        callback = CallbackList(callbacks)

        model.learn(total_timesteps=total_timesteps, callback=callback,
                    reset_num_timesteps=not cli.resume_from)
        model.save(str(model_path))
        # A STOP-file stop still saves the model and full metadata, but the
        # run record must say so (297k precedent: interrupted, peak rescued).
        status = "interrupted" if stop_file.exists() else "completed"
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
        write_metadata(run_dir, run_id, seed, train_cfg, Path(cli.train_config),
                       Path(cli.centerline_config), cage_yaml, model_path,
                       total_timesteps, status, circuits_meta=circuits_meta)
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
