"""Deterministic in-process nominal evaluation of an Isaac-trained checkpoint.

The Isaac counterpart of the Gazebo nominal eval (SC-NOM-01 style): loads a PPO
checkpoint, rebuilds the SAME in-process env the trainer used (isaac_scene +
IsaacSimInterface + GazeboLaneEnv) but **nominal** — every randomization block
(visual/dynamics/scene DR, spawn perturbation) is forced off — and rolls the
policy deterministically for N episodes on EACH circuit of the scene, pinned via
``options={"circuit_index": i}``. Reports per-circuit laps (arc-length unwrap of
``info["s"]``), mean/max |ey|, speed, cage interventions per rule, emergencies
and termination reasons; writes a JSON record next to the run artefacts.

Run with Isaac Sim's bundled python (training must NOT be running — one Isaac
instance per GPU):

    ~/isaacsim/python.sh tools/isaac_eval.py \\
        --checkpoint policy/checkpoints/ppo_isaac2d_2024_1M_225000_steps.zip
    # non-default scene/config:
    ~/isaacsim/python.sh tools/isaac_eval.py --checkpoint <ckpt.zip> \\
        --track complex_b,complex_d,complex_e --episodes 3 --mode enforcement

Frame stacking replicates the trainer's VecFrameStack semantics manually
(reset -> zeros + newest frame in the last channel slot), so the CNN sees the
exact observation layout it was trained on; VecNormalize needs no stats here
(norm_obs=False on the training path).
"""
import argparse
import os
import sys

from isaacsim import SimulationApp


def _parse_args(argv):
    p = argparse.ArgumentParser(description="In-process Isaac nominal eval.")
    p.add_argument("--checkpoint", default=None,
                   help="PPO .zip to evaluate (required for --controller ppo)")
    p.add_argument("--controller", choices=["ppo", "cv"], default="ppo",
                   help="'cv' drives the non-learned CVLaneController baseline "
                        "(pure pursuit on the D-43 estimator) instead of a "
                        "checkpoint — the Isaac feasibility/reference probe.")
    p.add_argument("--cv-speed", type=float, default=0.2,
                   help="fixed cruise speed (m/s) for --controller cv")
    p.add_argument("--cv-yaw-boost", type=float, default=1.0,
                   help="multiply the CV controller's commanded angular rate "
                        "(Isaac's skid-steer delivers ~18%% of the commanded "
                        "yaw at friction 0.05 — docs/13 physics tuning; needs "
                        "cage.yaw_gain headroom in the config)")
    p.add_argument("--dump-frames", type=int, default=0, metavar="N",
                   help="keep a ring of the last N raw Lane-Cam frames and a "
                        "per-step trace; dump them on episode end (PNG + CSV "
                        "under <out-dir>/<subject>_frames/) — perception "
                        "post-mortem, mirrors the Gazebo eval's frame dump")
    p.add_argument("--train-config", type=str, default=None,
                   help="train YAML for env params (default: train_isaac_2d.yaml)")
    p.add_argument("--track", type=str,
                   default=os.environ.get("TRACK", "complex_b,complex_d,complex_e"))
    p.add_argument("--episodes", type=int, default=3,
                   help="episodes per circuit (deterministic policy)")
    p.add_argument("--max-steps", type=int, default=None,
                   help="step cap per episode (default: cfg max_episode_steps)")
    p.add_argument("--mode", choices=["enforcement", "monitoring"],
                   default="enforcement")
    p.add_argument("--seed", type=int, default=2024)
    p.add_argument("--out", type=str, default=None,
                   help="output JSON (default: experiments/sim/eval_isaac/<ckpt>_<mode>.json)")
    return p.parse_args(argv)


ARGS = _parse_args(sys.argv[1:])
simulation_app = SimulationApp({"headless": True})

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
simulation_app.update()

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

from cobraflex_rl.gazebo_lane_env import GazeboLaneEnv  # noqa: E402
from cobraflex_rl.isaac_interface import IsaacSimInterface  # noqa: E402
from cobraflex_rl.run_io import git_commit, sha256_file  # noqa: E402


def _build_nominal_interface(camera_obs: bool):
    """isaac_train.build_isaac_interface minus the domain randomizer."""
    from isaacsim.core.prims import SingleArticulation

    world, track_metas = isaac_scene.build_world()
    stage = omni.usd.get_context().get_stage()
    cam_path = isaac_scene.make_lane_camera(stage) if camera_obs else None
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
    wheel_dof = [articulation.get_dof_index(j) for j in isaac_scene.WHEEL_JOINTS]
    physics_dt = float(getattr(world, "get_physics_dt", lambda: 1.0 / 60.0)())
    interface = IsaacSimInterface(
        world, articulation, wheel_dof,
        wheel_radius=isaac_scene.WHEEL_RADIUS,
        wheel_separation=isaac_scene.WHEEL_SEPARATION,
        physics_dt=physics_dt, spawn_z=isaac_scene.SPAWN_Z,
        annotator=annotator, render_always=False, randomizer=None)
    for _ in range(5):
        interface.wait_for_initial_data()
    return interface, track_metas


def _perimeter(points: np.ndarray) -> float:
    closed = np.vstack([points, points[:1]])
    return float(np.linalg.norm(np.diff(closed, axis=0), axis=1).sum())


class _FrameStacker:
    """Replicates the training obs pipeline for eval. The env emits
    channels-LAST (84, 84, 1); VecFrameStack stacks the last axis ->
    (84, 84, 4); SB3's internal VecTransposeImage then gives the CnnPolicy its
    channels-first (4, 84, 84) space (verified on the saved model). Here:
    stack channels-last exactly like VecFrameStack (reset -> zeros + newest
    frame in the last slot) and transpose explicitly before predict."""

    def __init__(self, n_stack: int):
        self.n = int(n_stack)
        self._buf = None

    def _chw(self) -> np.ndarray:
        return np.transpose(self._buf, (2, 0, 1)).copy()

    def reset(self, frame: np.ndarray) -> np.ndarray:
        h, w, c = frame.shape
        self._buf = np.zeros((h, w, c * self.n), dtype=frame.dtype)
        self._buf[:, :, -c:] = frame
        return self._chw()

    def step(self, frame: np.ndarray) -> np.ndarray:
        c = frame.shape[-1]
        self._buf = np.roll(self._buf, -c, axis=-1)
        self._buf[:, :, -c:] = frame
        return self._chw()


def main() -> int:
    cfg_path = ARGS.train_config or os.path.join(
        REPO, "src/cobraflex_rl/config/train_isaac_2d.yaml")
    with open(cfg_path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    # Nominal: every randomization off; cage mode per CLI.
    for key in ("domain_randomization", "dynamics_randomization",
                "scene_randomization", "spawn_perturbation"):
        cfg.setdefault(key, {})["enabled"] = False
    cfg.setdefault("cage", {})["mode"] = ARGS.mode

    os.environ["TRACK"] = ARGS.track
    track_names = isaac_scene.parse_track_names(ARGS.track)
    camera_obs = str(cfg.get("observation", {}).get("type", "state")) == "camera"
    max_steps = int(ARGS.max_steps or cfg.get("max_episode_steps", 1024))

    interface, track_metas = _build_nominal_interface(camera_obs)
    circuits, circuits_meta = isaac_scene.load_circuits(track_names, track_metas)
    env = GazeboLaneEnv(ros_interface=interface, cfg=cfg, circuits=circuits)

    model = controller = None
    yaw_gain = float(cfg.get("cage", {}).get("yaw_gain", 0.8))
    max_speed = float(cfg.get("action", {}).get("max_speed_mps", 0.5))
    if ARGS.controller == "cv":
        # Non-learned reference: pure-pursuit CVLaneController on the raw Lane-Cam
        # frame, at a fixed cruise (throttle = 2·v/max_speed − 1 on the 2-D map;
        # steer = angular/yaw_gain inverts safe_action_to_cmd_2d).
        from cobraflex_rl.cv_lane_controller import CVLaneController
        controller = CVLaneController(speed=float(ARGS.cv_speed))
        cv_throttle = float(np.clip(2.0 * ARGS.cv_speed / max_speed - 1.0, -1.0, 1.0))
        subject = f"cv_controller_{ARGS.cv_speed:g}mps"
        print(f"[isaac_eval] CV controller @ {ARGS.cv_speed} m/s | mode {ARGS.mode} | "
              f"{ARGS.episodes} ep x {len(circuits)} circuits x <= {max_steps} steps")
    else:
        if not ARGS.checkpoint:
            raise SystemExit("--checkpoint is required for --controller ppo")
        model = PPO.load(ARGS.checkpoint, device=str(cfg.get("device", "auto")))
        subject = Path(ARGS.checkpoint).stem
        print(f"[isaac_eval] ckpt {ARGS.checkpoint} | mode {ARGS.mode} | "
              f"{ARGS.episodes} ep x {len(circuits)} circuits x <= {max_steps} steps")
    n_stack = int(cfg.get("observation", {}).get("camera", {}).get("frame_stack", 4))
    stacker = _FrameStacker(n_stack) if (camera_obs and model is not None) else None

    results = []
    for ci, circuit in enumerate(circuits):
        perimeter = _perimeter(np.asarray(circuit["centerline"], dtype=float))
        for ep in range(ARGS.episodes):
            obs, info = env.reset(seed=ARGS.seed + ep,
                                  options={"circuit_index": ci})
            stacked = stacker.reset(obs) if stacker else obs
            cv_detected = 0
            frame_ring = []          # (step, frame) ring when --dump-frames
            trace_rows = []
            prev_s = None
            progress = 0.0
            abs_ey, speeds = [], []
            rule_counts = {}
            emergencies = 0
            reward_sum = 0.0
            termination = "step_cap"
            steps = 0
            for _ in range(max_steps):
                if controller is not None:
                    frame_res = interface.get_camera_frame()
                    frame = frame_res[0] if frame_res is not None else None
                    ang, detected = controller.compute(frame)
                    cv_detected += int(bool(detected))
                    action = np.array(
                        [np.clip(ang * ARGS.cv_yaw_boost / yaw_gain, -1.0, 1.0),
                         cv_throttle],
                        dtype=np.float32)
                else:
                    ang = detected = None
                    frame = None
                    if ARGS.dump_frames:
                        frame_res = interface.get_camera_frame()
                        frame = frame_res[0] if frame_res is not None else None
                    action, _ = model.predict(stacked, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                stacked = stacker.step(obs) if stacker else obs
                if ARGS.dump_frames:
                    if frame is not None:
                        frame_ring.append((steps, np.asarray(frame).copy()))
                        frame_ring = frame_ring[-ARGS.dump_frames:]
                    trace_rows.append((
                        steps, round(float(info.get("s", 0.0)), 3),
                        round(float(info.get("ey", 0.0)), 4),
                        round(float(info.get("epsi", 0.0)), 4),
                        round(float(info.get("cv_ey", float("nan"))), 4),
                        round(float(info.get("cv_epsi", float("nan"))), 4),
                        int(bool(info.get("perception_invalid", False))),
                        round(float(info.get("speed", 0.0)), 3),
                        None if ang is None else round(float(ang), 4),
                        "|".join(info.get("cage_interventions", [])),
                        int(bool(info.get("cage_emergency", False))),
                    ))
                steps += 1
                reward_sum += float(reward)
                s = float(info.get("s", 0.0))
                if prev_s is not None:
                    ds = s - prev_s
                    if ds < -perimeter / 2.0:
                        ds += perimeter
                    elif ds > perimeter / 2.0:
                        ds -= perimeter
                    progress += ds
                prev_s = s
                abs_ey.append(abs(float(info.get("ey", 0.0))))
                speeds.append(float(info.get("speed", 0.0)))
                for rule in info.get("cage_interventions", []):
                    rule_counts[rule] = rule_counts.get(rule, 0) + 1
                if info.get("cage_emergency", False):
                    emergencies += 1
                if terminated or truncated:
                    termination = info.get(
                        "termination_reason", "terminated" if terminated else "truncated")
                    break
            results.append({
                "circuit": circuit["name"],
                "episode": ep,
                "steps": steps,
                "termination": termination,
                "laps": round(progress / perimeter, 3),
                "progress_m": round(progress, 2),
                "mean_abs_ey_mm": round(1000.0 * float(np.mean(abs_ey)), 1),
                "max_abs_ey_mm": round(1000.0 * float(np.max(abs_ey)), 1),
                "mean_speed_mps": round(float(np.mean(speeds)), 3),
                "reward_sum": round(reward_sum, 1),
                "emergency_steps": emergencies,
                "interventions_per_rule": dict(sorted(rule_counts.items())),
                **({"cv_detected_frac": round(cv_detected / max(1, steps), 3)}
                   if controller is not None else {}),
            })
            if ARGS.dump_frames and trace_rows:
                import csv as _csv
                dump_dir = (Path(REPO) / "experiments" / "sim" / "eval_isaac"
                            / f"{subject}_frames" / f"{circuit['name']}_ep{ep}")
                dump_dir.mkdir(parents=True, exist_ok=True)
                try:
                    import cv2
                    for st, fr in frame_ring:
                        cv2.imwrite(str(dump_dir / f"frame_{st:04d}.png"), fr)
                except Exception as exc:  # pragma: no cover
                    print(f"[isaac_eval] frame dump failed: {exc}")
                with (dump_dir / "trace.csv").open("w", newline="") as fh:
                    w = _csv.writer(fh)
                    w.writerow(["step", "s_m", "ey_m", "epsi_rad", "cv_ey_m",
                                "cv_epsi_rad", "perception_invalid", "speed_mps",
                                "cv_angular", "interventions", "emergency"])
                    w.writerows(trace_rows)
                print(f"[isaac_eval] dumped {len(frame_ring)} frames + trace "
                      f"to {dump_dir}")
            r = results[-1]
            print(f"[isaac_eval] {r['circuit']} ep{ep}: {r['steps']} steps, "
                  f"{r['laps']} laps, |ey| {r['mean_abs_ey_mm']} mm, "
                  f"v {r['mean_speed_mps']} m/s, term={r['termination']}, "
                  f"emerg={r['emergency_steps']}", flush=True)

    out = Path(ARGS.out) if ARGS.out else (
        Path(REPO) / "experiments" / "sim" / "eval_isaac"
        / f"{subject}_{ARGS.mode}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "controller": ARGS.controller,
        "cv_speed_mps": ARGS.cv_speed if controller is not None else None,
        "checkpoint": str(ARGS.checkpoint) if ARGS.checkpoint else None,
        "checkpoint_hash": sha256_file(ARGS.checkpoint) if ARGS.checkpoint else None,
        "train_config": cfg_path,
        "mode": ARGS.mode,
        "track": ARGS.track,
        "episodes_per_circuit": ARGS.episodes,
        "max_steps": max_steps,
        "seed": ARGS.seed,
        "nominal": True,
        "platform": "sim-isaac",
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(out.parent),
        "circuits": circuits_meta,
        "results": results,
    }
    with out.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    print(f"[isaac_eval] wrote {out}")

    env.close()
    interface.destroy_node()
    return 0


try:
    rc = main()
except Exception:
    import traceback
    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
