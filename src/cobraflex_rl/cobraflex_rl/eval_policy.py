"""
eval_policy — evaluate a trained PPO lane-following policy and emit the §7.5
evidence (Training Specification §7.5.1): completed laps, cage intervention
rate, emergencies, and mean tracking error, written as a reproducible run under
`experiments/sim/runs/<run_id>/`.

The policy is evaluated through `GazeboLaneEnv`, so it runs under the **same**
in-process cage as training and deployment (D-34). Spawn perturbation is
disabled so the start is deterministic and comparable with the PD baseline run.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ament_index_python.packages import PackageNotFoundError, get_package_share_directory
import numpy as np
import rclpy
from rclpy.utilities import remove_ros_args
from stable_baselines3 import PPO
import yaml

from .campaign_metrics import compute_run_metrics
from .criterion_eval import evaluate as evaluate_criterion
from .criterion_eval import is_labelled
from .eval_metrics import summarize_eval
from .gazebo_lane_env import GazeboLaneEnv
from .ros_interface import RosGazeboInterface
from .run_io import git_commit, sha256_file
from .scenario_metrics import (
    max_excursion_m,
    road_edge_contact,
    time_to_recovery_heading,
)
from .scenario_runner import derive_run_config


PACKAGE_NAME = "cobraflex_rl"
SCENARIO_ID = "SC-NOM-01"


def resolve_share_directory() -> Path:
    try:
        return Path(get_package_share_directory(PACKAGE_NAME))
    except PackageNotFoundError:
        return Path(__file__).resolve().parents[1]


def resolve_runs_dir(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "experiments" / "sim" / "runs").is_dir():
            return parent / "experiments" / "sim" / "runs"
    return Path.cwd() / "experiments" / "sim" / "runs"


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_args(args: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate PPO lane-following policy.")
    parser.add_argument("--centerline-config", type=str, default=None)
    parser.add_argument("--train-config", type=str, default=None)
    parser.add_argument("--model-path", type=str, default=None)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument(
        "--max-steps", type=int, default=None,
        help="Override max_episode_steps for the eval (e.g. 4400 ≈ 10 continuous "
             "laps for the §7.5.1 lap-count comparison vs the PD). Default: the "
             "value in train_ppo.yaml.",
    )
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--output-root", type=str, default=None,
                        help="Directory holding run subdirs (default experiments/sim/runs).")
    # F4 scenario-campaign mode. With --scenario the run is driven by an SC-*
    # YAML (initial conditions, commanded speed, timeout) instead of the nominal
    # SC-NOM-01 defaults, and the output carries the full per-run metric
    # catalogue + the pass_criterion verdict.
    parser.add_argument("--scenario", type=str, default=None,
                        help="Path to a scenario YAML (scenarios/<cat>/*.yaml). "
                             "Omit for the legacy SC-NOM-01 §7.5 eval.")
    parser.add_argument("--mode", type=str, default=None,
                        choices=["enforcement", "monitoring"],
                        help="Cage mode override (default: train_ppo.yaml cage.mode).")
    parser.add_argument("--rep", type=int, default=0,
                        help="Repetition index — seeds the per-run randomisation jitter.")
    parser.add_argument("--base-seed", type=int, default=0,
                        help="Base seed folded into the per-rep jitter (reproducibility).")
    cleaned_args = remove_ros_args(args=args)
    if cleaned_args and not cleaned_args[0].startswith("-"):
        cleaned_args = cleaned_args[1:]
    return parser.parse_args(cleaned_args)


def resolve_load_path(path: Path) -> Path:
    if path.exists():
        return path
    return path if path.suffix == ".zip" else path.with_suffix(".zip")


def _disable_spawn_perturbation(train_cfg: Dict[str, Any]) -> None:
    spawn_cfg = dict(train_cfg.get("spawn_perturbation", {}))
    spawn_cfg["enabled"] = False
    train_cfg["spawn_perturbation"] = spawn_cfg


def _record_from_info(episode: int, step: int, info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "episode": episode,
        "step": step,
        # World pose (x, y) → §7.5 trajectory overlay (RL vs PD on the oval);
        # ey/epsi/s are the Frenet/cage state at the same step.
        "x": float(info.get("x", 0.0)),
        "y": float(info.get("y", 0.0)),
        "yaw": float(info.get("yaw", 0.0)),
        "ey": float(info.get("ey", 0.0)),
        "epsi": float(info.get("epsi", 0.0)),
        "s": float(info.get("s", 0.0)),
        "speed": float(info.get("speed", 0.0)),
        "raw_steer": float(info.get("raw_steer", 0.0)),
        "safe_steer": float(info.get("safe_steer", 0.0)),
        "steer_correction": float(info.get("steer_correction", 0.0)),
        "interventions": list(info.get("cage_interventions", [])),
        "emergency": bool(info.get("cage_emergency", False)),
    }


def _write_cage_status_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    fields = [
        "episode", "step", "x", "y", "yaw", "ey", "epsi", "s", "speed",
        "raw_steer", "safe_steer", "steer_correction",
        "interventions", "emergency",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for r in records:
            writer.writerow([
                r["episode"], r["step"],
                f"{r['x']:.6f}", f"{r['y']:.6f}", f"{r['yaw']:.6f}",
                f"{r['ey']:.6f}", f"{r['epsi']:.6f}", f"{r['s']:.6f}",
                f"{r['speed']:.6f}", f"{r['raw_steer']:.6f}",
                f"{r['safe_steer']:.6f}", f"{r['steer_correction']:.6f}",
                ";".join(r["interventions"]), int(r["emergency"]),
            ])


def _print_summary(summary: Dict[str, Any]) -> None:
    print("\n===== §7.5 evaluation summary (RL + cage) =====")
    print(f"  episodes / steps    : {summary['episodes']} / {summary['total_steps']}")
    print(f"  completed laps      : {summary['completed_laps']:.2f}")
    print(f"  cage emergencies    : {summary['emergency_steps']} steps")
    print(f"  cage interventions  : {summary['intervention_rate_pct']:.3f}% of steps "
          f"({summary['interventions_per_rule']})")
    print(f"  mean ey / |ey|      : {summary['mean_ey_m']:.4f} / {summary['mean_abs_ey_m']:.4f} m")
    print(f"  mean |epsi|         : {summary['mean_abs_epsi_rad']:.4f} rad")
    print(f"  duration            : {summary['duration_s']:.1f} s")
    print("===============================================\n")


def main(args: Optional[Sequence[str]] = None) -> None:
    cli_args = parse_args(args)
    rclpy.init(args=args)

    share_dir = resolve_share_directory()
    centerline_path = Path(cli_args.centerline_config or share_dir / "config" / "oval_right_lane_centerline.yaml")
    train_cfg_path = Path(cli_args.train_config or share_dir / "config" / "train_ppo.yaml")

    centerline_cfg = load_yaml(centerline_path)
    train_cfg = load_yaml(train_cfg_path)
    # Evaluation starts from the deterministic scenario/nominal spawn (random
    # spawn perturbation off); the F4 scenario path injects its initial
    # conditions through reset(options=...) instead (§7.5, D-34).
    _disable_spawn_perturbation(train_cfg)

    # F4 scenario mode: derive the run config (initial conditions, commanded
    # speed, horizon) from the SC-* YAML for this repetition. Absent --scenario,
    # the legacy SC-NOM-01 §7.5 eval runs unchanged.
    run_config = None
    scenario_id = SCENARIO_ID
    reset_options: Optional[Dict[str, Any]] = None
    if cli_args.scenario:
        scenario_cfg = load_yaml(Path(cli_args.scenario))
        control_dt = float(train_cfg.get("control_dt", 0.1))
        run_config = derive_run_config(
            scenario_cfg, cli_args.rep, control_dt=control_dt, base_seed=cli_args.base_seed
        )
        scenario_id = run_config.scenario_id
        reset_options = {**run_config.reset_options, "perturbation": run_config.perturbation}
        train_cfg["fixed_speed"] = run_config.fixed_speed
        if not (cli_args.max_steps and cli_args.max_steps > 0) and run_config.max_steps > 0:
            train_cfg["max_episode_steps"] = run_config.max_steps

    # Cage mode override (enforcement vs monitoring campaign axis).
    if cli_args.mode:
        cage_cfg = dict(train_cfg.get("cage", {}))
        cage_cfg["mode"] = cli_args.mode
        train_cfg["cage"] = cage_cfg

    # Explicit --max-steps always wins (e.g. the §7.5.1 long lap-count run).
    if cli_args.max_steps is not None and cli_args.max_steps > 0:
        train_cfg["max_episode_steps"] = int(cli_args.max_steps)

    model_path = Path(cli_args.model_path or train_cfg.get("model_path", "cobraflex_ppo_lane"))
    model_path = model_path.expanduser()
    seed = int(train_cfg.get("seed", 42))
    # Env reset seed: in scenario mode use the per-rep env_seed so the obs-noise
    # stream (SC-PERT-01) is independent across reps yet reproducible; otherwise
    # the legacy policy seed (§7.5 eval).
    reset_seed = run_config.env_seed if run_config is not None else seed

    interface: Optional[RosGazeboInterface] = None
    env: Optional[GazeboLaneEnv] = None
    records: List[Dict[str, Any]] = []

    try:
        interface = RosGazeboInterface()
        if not interface.wait_for_initial_data(timeout_sec=10.0):
            raise RuntimeError("Timed out waiting for /odom data.")

        centerline_points = np.asarray(centerline_cfg["centerline"]["points"], dtype=float)
        lane_width = float(centerline_cfg["lane_width"])
        road_width = float(centerline_cfg.get("road_width", lane_width))

        env = GazeboLaneEnv(
            ros_interface=interface,
            centerline=centerline_points,
            lane_width=lane_width,
            road_width=road_width,
            cfg=train_cfg,
        )
        perimeter = float(env.tracker.cumulative_lengths[-1])

        # Load on CPU: the lane-following policy is a tiny MLP, CPU inference at
        # 20 Hz is ample, and it avoids GPU VRAM exhaustion across the hundreds of
        # back-to-back runs of a campaign (the "CUDA out of memory" on the 4th
        # consecutive run that defaulting to the GPU caused).
        model = PPO.load(str(resolve_load_path(model_path)), device="cpu")

        last_terminated = False
        last_info: Dict[str, Any] = {}
        for episode in range(cli_args.episodes):
            observation, info = env.reset(seed=reset_seed + episode, options=reset_options)
            terminated = False
            truncated = False
            step_index = 0
            print(f"Episode {episode + 1}")

            while not (terminated or truncated):
                action, _ = model.predict(observation, deterministic=True)
                observation, reward, terminated, truncated, info = env.step(action)
                step_index += 1
                records.append(_record_from_info(episode, step_index, info))
                print(
                    f"step={step_index:04d} ey={info['ey']:.4f} "
                    f"epsi={info['epsi']:.4f} speed={info['speed']:.4f} "
                    f"reward={reward:.4f} interv={info.get('cage_interventions', [])}"
                )
            last_terminated = terminated
            last_info = info

        summary = summarize_eval(records, perimeter=perimeter, cycle_dt_s=env.control_dt)
        if run_config is not None and run_config.perturbation.active:
            # Record which perturbation level this rep ran (σ / latency / pulse) so
            # the per-run summary.json is self-describing for the analysis.
            summary["perturbation"] = {
                "kind": run_config.perturbation.kind,
                "level": run_config.perturbation.level_label,
            }
        _print_summary(summary)
        # `completed` (M-P2): the run reached its horizon / goal without a
        # road-boundary termination. Used only in the scenario verdict.
        campaign = None
        if run_config is not None:
            campaign = _evaluate_scenario(
                records, run_config, completed=not last_terminated,
                control_dt=env.control_dt, road_half_m=0.5 * env.road_width,
                termination_reason=str(last_info.get("termination_reason", "")),
            )
            _print_verdict(scenario_id, campaign)
        _write_run(
            cli_args=cli_args,
            train_cfg=train_cfg,
            centerline_path=centerline_path,
            model_path=resolve_load_path(model_path),
            seed=seed,
            records=records,
            summary=summary,
            scenario_id=scenario_id,
            campaign=campaign,
        )
    finally:
        if env is not None:
            env.close()
        if interface is not None:
            interface.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def _jsonable(value: Any) -> Any:
    """JSON-safe copy: non-finite floats (e.g. time_to_recovery_heading == inf
    when the heading never recovers) -> None, recursively through dicts/lists."""
    import math as _math
    if isinstance(value, float):
        return value if _math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _evaluate_scenario(
    records: List[Dict[str, Any]],
    run_config: Any,
    *,
    completed: bool,
    control_dt: float,
    road_half_m: Optional[float] = None,
    termination_reason: str = "",
) -> Dict[str, Any]:
    """Compute the full per-run metric catalogue + scenario-specific metrics and
    score the scenario's ``pass_criterion_per_run`` (three-valued; an unavailable
    metric is 'indeterminate', a real breach is a fail)."""
    res = compute_run_metrics(records, params={"control_dt": control_dt}, completed=completed)
    metrics = res["metrics"]
    values: Dict[str, Any] = dict(metrics)
    values["emergency"] = any(bool(r.get("emergency")) for r in records)
    values["time_to_recovery_heading"] = time_to_recovery_heading(records, control_dt=control_dt)
    # Frontier / out-of-ODD tokens (cage-efficacy contrast): how far out it got
    # and whether it reached the road edge (the harm proxy).
    values["max_excursion_m"] = max_excursion_m(records)
    values["road_edge_contact"] = (
        road_edge_contact(records, road_half_m) if road_half_m else None
    )

    expr = run_config.pass_criterion_per_run
    if is_labelled(expr):
        verdict, clauses, note = None, [], "labelled multi-arm criterion (PERT-03) not scored in single-run eval"
    else:
        result = evaluate_criterion(expr, values)
        verdict, clauses, note = result["passed"], result["clauses"], result.get("error")

    return {
        "scenario_id": run_config.scenario_id,
        "criterion": expr,
        "verdict": verdict,           # True / False / None (indeterminate)
        "clauses": _jsonable(clauses),
        "values": _jsonable(values),
        "availability": res["availability"],
        "termination_reason": termination_reason,
        "note": note,
    }


def _print_verdict(scenario_id: str, campaign: Dict[str, Any]) -> None:
    label = {True: "PASS", False: "FAIL", None: "INDETERMINATE"}[campaign["verdict"]]
    print(f"\n===== {scenario_id} per-run verdict: {label} =====")
    print(f"  criterion: {campaign['criterion']}")
    for c in campaign["clauses"]:
        mark = {True: "ok ", False: "FAIL", None: "n/a "}.get(c.get("passed"))
        print(f"   [{mark}] {c.get('clause')}  (lhs={c.get('lhs')})")
    vals = campaign.get("values", {})
    if campaign.get("termination_reason") or vals.get("max_excursion_m") is not None:
        print(f"  termination={campaign.get('termination_reason')!r}  "
              f"max_excursion={vals.get('max_excursion_m')} m  "
              f"road_edge_contact={vals.get('road_edge_contact')}")
    if campaign.get("note"):
        print(f"  note: {campaign['note']}")
    print("=" * 47 + "\n")


def _write_run(
    cli_args: argparse.Namespace,
    train_cfg: Dict[str, Any],
    centerline_path: Path,
    model_path: Path,
    seed: int,
    records: List[Dict[str, Any]],
    summary: Dict[str, Any],
    scenario_id: str = SCENARIO_ID,
    campaign: Optional[Dict[str, Any]] = None,
) -> None:
    runs_dir = resolve_runs_dir(cli_args.output_root)
    run_id = cli_args.run_id or "rl_eval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = str(train_cfg.get("cage", {}).get("mode", "enforcement"))
    cage_yaml = Path(train_cfg.get("cage", {}).get("yaml_path", "") or "")
    if not cage_yaml.is_file():
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "cage" / "cage.yaml"
            if candidate.is_file():
                cage_yaml = candidate
                break

    _write_cage_status_csv(out_dir / "cage_status.csv", records)

    summary_out = dict(summary)
    summary_out.update({"run_id": run_id, "scenario_id": scenario_id, "mode": mode})
    if campaign is not None:
        summary_out["verdict"] = campaign["verdict"]
        summary_out["campaign"] = campaign
    with (out_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary_out, handle, indent=2)

    metadata = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "mode": mode,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "duration_s": summary["duration_s"],
        "git_commit": git_commit(out_dir),
        "cage_yaml": str(cage_yaml),
        "cage_yaml_hash": sha256_file(cage_yaml),
        "policy_checkpoint": str(model_path),
        "policy_checkpoint_hash": sha256_file(model_path),
        "centerline_yaml_hash": sha256_file(centerline_path),
        "scenario_yaml": str(cli_args.scenario or ""),
        "scenario_yaml_hash": sha256_file(Path(cli_args.scenario)) if cli_args.scenario else sha256_file(centerline_path),
        "rep": int(getattr(cli_args, "rep", 0)),
        "seed": seed,
        "platform": "sim",
        "status": "completed",
    }
    with (out_dir / "metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    print(f"Wrote evaluation run to {out_dir}")


if __name__ == "__main__":
    main()
