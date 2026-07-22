#!/usr/bin/env python3
"""Bounded Gazebo calibration of the D-43 heading interface to C-02.

The collector drives the existing ``eval_cv_controller`` launch, hence camera
frames pass through the real Gazebo renderer, CvLaneEstimator, perception
supervisor and canonical cage.  Ground truth is consumed only afterwards as an
oracle.  Calibration scenarios are generated inside the evidence directory;
they are deliberately not part of the verdict scenario library.

Exit codes: 0 PASS, 2 BLOCKED, 1 invalid/incomplete evidence.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO = Path(__file__).resolve().parents[1]
SCHEMA = "d43-c02-calibration/v2"
THETA_MAX = 0.4363
D_MAX = 0.16
ROAD_HALF_M = 0.26
CONTROL_DT = 0.1
NOMINAL_EY = 0.08
NOMINAL_EPSI = 0.10
RAW_FIELDS = (
    "timestamp", "split", "cell_id", "scenario", "seed", "section", "condition",
    "visual_mode", "visual_level", "target_speed_mps", "start_s_m", "step",
    "x_gt", "y_gt", "yaw_gt", "ey_gt", "epsi_gt", "curvature_gt",
    "curvature_anchor_gt",
    "ey_cv", "epsi_cv", "ey_error", "epsi_error", "cv_confidence",
    "cv_lane_width", "cv_curvature", "speed_mps", "c01", "c02", "c03",
    "c04", "c05", "emergency", "road_edge_contact", "m_s1", "m_s2",
)


@dataclass(frozen=True)
class Cell:
    cell_id: str
    split: str
    seed: int
    section: str
    start_s_m: float
    curvature_gt: float
    speed_mps: float
    heading_rad: float
    visual_mode: str = "clean"
    visual_level: float = 0.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bundle(paths: Iterable[Path]) -> str:
    """Hash an ordered set of named files without losing file boundaries."""
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        h.update(path.name.encode("utf-8"))
        h.update(b"\0")
        h.update(bytes.fromhex(sha256(path)))
    return h.hexdigest()


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    return proc.stdout.strip() or "unknown"


def load_points(path: Path) -> list[tuple[float, float]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [(float(p[0]), float(p[1])) for p in data["centerline"]["points"]]


def section_anchors(points: list[tuple[float, float]]) -> dict[str, tuple[float, float]]:
    """Return straight, representative-curve and max-curvature arclength anchors."""
    if len(points) < 5:
        raise ValueError("centerline needs at least five points")
    closed = points + ([points[0]] if points[0] != points[-1] else [])
    seg = [math.dist(a, b) for a, b in zip(closed, closed[1:])]
    s = [0.0]
    for length in seg:
        s.append(s[-1] + length)
    samples: list[tuple[float, float]] = []
    for i in range(1, len(closed) - 1):
        a, b, c = closed[i - 1], closed[i], closed[i + 1]
        ab, bc, ac = math.dist(a, b), math.dist(b, c), math.dist(a, c)
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        kappa = 0.0 if min(ab, bc, ac) < 1e-9 else 2.0 * cross / (ab * bc * ac)
        samples.append((s[i], kappa))
    straight = min(samples, key=lambda pair: abs(pair[1]))
    demanding = max(samples, key=lambda pair: abs(pair[1]))
    target = 0.5 * abs(demanding[1])
    odd_curve = min(samples, key=lambda pair: abs(abs(pair[1]) - target))
    return {"straight": straight, "odd_curve": odd_curve, "demanding": demanding}


def curvature_at_s(
    points: list[tuple[float, float]], s_m: float, lookahead_segments: int = 1,
) -> float:
    """PolylineTracker-compatible local signed curvature at arclength ``s_m``."""
    closed = points + ([points[0]] if points[0] != points[-1] else [])
    lengths = [math.dist(a, b) for a, b in zip(closed, closed[1:])]
    headings = [math.atan2(b[1] - a[1], b[0] - a[0])
                for a, b in zip(closed, closed[1:])]
    cumulative = [0.0]
    for length in lengths:
        cumulative.append(cumulative[-1] + length)
    if not lengths or cumulative[-1] <= 0.0:
        return 0.0
    s = float(s_m) % cumulative[-1]
    start = min(len(lengths) - 1, bisect.bisect_right(cumulative, s) - 1)
    steps = min(int(lookahead_segments), len(lengths) - 1)
    end = (start + steps) % len(headings)
    arc = sum(lengths[(start + k) % len(lengths)] for k in range(steps))
    if arc <= 1e-9 or end == start:
        return 0.0
    dpsi = math.atan2(
        math.sin(headings[end] - headings[start]),
        math.cos(headings[end] - headings[start]),
    )
    return dpsi / arc


def build_matrix(anchors: dict[str, tuple[float, float]]) -> list[Cell]:
    """Balanced 28-cell matrix: calibration seed 2024, held-out seed 42."""
    cells: list[Cell] = []
    for split, seed in (("calibration", 2024), ("validation", 42)):
        specs: list[tuple[str, float, str, float]] = []
        for section in anchors:
            for speed in (0.10, 0.22):
                specs.append((section, speed, "clean", 0.0))
            specs.extend((section, 0.22, "clean", 0.0) for _ in range(2))
        specs += [("demanding", 0.22, "glare_overexposure", 0.3),
                  ("demanding", 0.22, "motion_blur", 0.3)]
        for index, (section, speed, visual, level) in enumerate(specs):
            # The duplicate clean cells at each section are the two real-fault arms.
            duplicate_index = sum(1 for x in specs[:index] if x == (section, speed, visual, level))
            heading = (0.48, -0.48)[duplicate_index - 1] if visual == "clean" and speed == 0.22 and duplicate_index in (1, 2) else 0.0
            start_s, kappa = anchors[section]
            cells.append(Cell(f"{split[:3]}_{index:02d}", split, seed, section,
                              start_s, kappa, speed, heading, visual, level))
    return cells


def scenario_yaml(cell: Cell, steps: int, control_dt: float) -> dict[str, Any]:
    perturbations: Any = "none"
    if cell.visual_mode != "clean":
        perturbations = {"type": "visual_degradation", "mode": cell.visual_mode,
                         "level_levels": [cell.visual_level]}
    return {
        "id": f"CAL-D43-C02-{cell.cell_id.upper()}", "category": "calibration_only",
        "track": {"world": "lane_following_oval_complex.world",
                  "centerline": "complex_b_right_lane_centerline.yaml",
                  "start_s_m": cell.start_s_m},
        "commanded_speed_mps": cell.speed_mps,
        "description": "Non-verdict D-43/C-02 calibration cell.",
        "initial_conditions": {
            # Heading faults are injected during motion by the calibration-only
            # eval hook, never hidden in the spawn transient.
            "pose": {"x": 0.0, "y": 0.0, "theta_deg": 0.0},
            "speed_mps": 0.0,
            "randomisation": {"lateral_offset_uniform_m": [0.0, 0.0],
                              "heading_uniform_deg": [0.0, 0.0]},
        },
        "perturbations": perturbations,
        "termination": {"type": "time_or_event", "timeout_s": steps * control_dt,
                        "events": ["lane_exit", "emergency_stop"]},
        "metrics_primary": ["M-S1", "M-S2"], "metrics_secondary": [],
        "pass_criterion_per_run": "calibration_only",
        "pass_criterion_per_scenario": "calibration_only",
        "references_SR": ["SR-002", "SR-005", "SR-008"],
        "n_runs_recommended": {"enforcement": 1, "monitoring": 0},
    }


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def ingest_cell(
    cell: Cell, trace: Path, centerline_points: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    rows = []
    with trace.open(newline="", encoding="utf-8") as handle:
        for source in csv.DictReader(handle):
            rules = set(filter(None, source.get("interventions", "").split(";")))
            ey_gt, epsi_gt = float(source["ey"]), float(source["epsi"])
            curvature_gt = curvature_at_s(centerline_points, float(source["s"]))
            ey_cv, epsi_cv = float(source["cv_ey"]), float(source["cv_epsi"])
            contact = abs(ey_gt) >= ROAD_HALF_M
            sim_time = source.get("sim_time_s", "")
            timestamp = (
                float(sim_time)
                if sim_time and math.isfinite(float(sim_time))
                else float(source.get("step", 0)) * 0.1
            )
            row = {
                "timestamp": timestamp,
                "split": cell.split, "cell_id": cell.cell_id,
                "scenario": f"CAL-D43-C02-{cell.cell_id.upper()}", "seed": cell.seed,
                "section": cell.section,
                "condition": "heading_fault" if abs(epsi_gt) >= THETA_MAX else "gt_safe",
                "visual_mode": cell.visual_mode, "visual_level": cell.visual_level,
                "target_speed_mps": cell.speed_mps, "start_s_m": cell.start_s_m,
                "step": int(source["step"]), "x_gt": float(source["x"]),
                "y_gt": float(source["y"]), "yaw_gt": float(source["yaw"]),
                "ey_gt": ey_gt, "epsi_gt": epsi_gt,
                "curvature_gt": curvature_gt,
                "curvature_anchor_gt": cell.curvature_gt,
                "ey_cv": ey_cv, "epsi_cv": epsi_cv, "ey_error": ey_cv - ey_gt,
                "epsi_error": epsi_cv - epsi_gt,
                "cv_confidence": float(source["cv_confidence"]),
                "cv_lane_width": float(source["cv_lane_width"]),
                "cv_curvature": float(source["cv_curvature"]),
                "speed_mps": float(source["speed"]),
                **{f"c0{i}": int(f"C-0{i}" in rules) for i in range(1, 6)},
                "emergency": int(_bool(source["emergency"])),
                "road_edge_contact": int(contact), "m_s1": abs(ey_gt),
                "m_s2": int(abs(ey_gt) > D_MAX),
            }
            rows.append(row)
    return rows


def analyse(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"schema": SCHEMA, "status": "INVALID", "splits": {}}
    for split in ("calibration", "validation"):
        subset = [r for r in rows if r["split"] == split]
        safe = [r for r in subset if abs(r["ey_gt"]) <= NOMINAL_EY and abs(r["epsi_gt"]) <= NOMINAL_EPSI]
        faults = [r for r in subset if abs(r["epsi_gt"]) >= THETA_MAX]
        fault_cells = sorted({r["cell_id"] for r in faults})
        detected = {r["cell_id"] for r in faults if r["c02"] or r["c05"]}
        delays = []
        stopping_times = []
        injection_speeds = []
        for cell_id in fault_cells:
            cell_rows = [r for r in faults if r["cell_id"] == cell_id]
            all_cell_rows = [r for r in subset if r["cell_id"] == cell_id]
            fault_start = min(r["timestamp"] for r in cell_rows)
            before_fault = [r for r in all_cell_rows if r["timestamp"] < fault_start]
            if before_fault:
                injection_speeds.append(
                    max(before_fault, key=lambda r: r["timestamp"])["speed_mps"]
                )
            hits = [r["timestamp"] for r in cell_rows if r["c02"] or r["c05"]]
            if hits:
                first_hit = min(hits)
                delays.append(first_hit - fault_start)
                stopped = [r["timestamp"] for r in all_cell_rows
                           if r["timestamp"] >= first_hit and r["speed_mps"] <= 0.02]
                if stopped:
                    # Rows are sampled after actuation. If speed is already zero
                    # on the trigger row, the conservative measured upper bound
                    # is one control cycle rather than an artificial 0.0 s.
                    stopping_times.append(min(stopped) - first_hit + CONTROL_DT)
        result["splits"][split] = {
            "samples": len(subset), "safe_centered_samples": len(safe),
            "heading_fault_cells": len(fault_cells),
            "detected_heading_fault_cells": len(detected),
            "false_c02_steps": sum(r["c02"] for r in safe),
            "false_c05_steps": sum(r["c05"] for r in safe),
            "missed_heading_fault_cells": sorted(set(fault_cells) - detected),
            "max_detection_delay_s": max(delays) if delays else None,
            "max_stopping_time_s": max(stopping_times) if stopping_times else None,
            "min_fault_injection_speed_mps": (
                min(injection_speeds) if injection_speeds else None
            ),
            "road_edge_contacts": sum(r["road_edge_contact"] for r in subset),
            "max_m_s1_m": max((r["m_s1"] for r in subset), default=None),
            "m_s2_steps": sum(r["m_s2"] for r in subset),
            "safe_abs_epsi_cv_max": max((abs(r["epsi_cv"]) for r in safe), default=None),
            "fault_abs_epsi_cv_min": min((abs(r["epsi_cv"]) for r in faults), default=None),
            "global_separation_margin_rad": (
                min((abs(r["epsi_cv"]) for r in faults), default=math.inf)
                - max((abs(r["epsi_cv"]) for r in safe), default=-math.inf)
            ),
            "safe_error_by_curvature": {
                str(k): {
                    "n": len(group),
                    "mean_epsi_error_rad": sum(r["epsi_error"] for r in group) / len(group),
                    "min_epsi_error_rad": min(r["epsi_error"] for r in group),
                    "max_epsi_error_rad": max(r["epsi_error"] for r in group),
                } for k in sorted({r["curvature_anchor_gt"] for r in safe})
                if (group := [r for r in safe if r["curvature_anchor_gt"] == k])
            },
        }
    val = result["splits"]["validation"]
    if not val["samples"] or not val["safe_centered_samples"] or not val["heading_fault_cells"]:
        result["blockers"] = ["held-out coverage incomplete"]
        return result
    blockers = []
    if val["missed_heading_fault_cells"]: blockers.append("heading false negative")
    if val["false_c02_steps"] or val["false_c05_steps"]: blockers.append("false C-02/C-05 in centred band")
    if val["road_edge_contacts"]: blockers.append("road-edge contact")
    if val["max_m_s1_m"] is not None and val["max_m_s1_m"] >= 0.16: blockers.append("real envelope crossing")
    if val["max_detection_delay_s"] is None or val["max_detection_delay_s"] > 0.2:
        blockers.append("heading detection delay exceeds the C-05 persistence budget")
    if val["max_stopping_time_s"] is None or val["max_stopping_time_s"] > 1.7:
        blockers.append("controlled stopping time incompatible with SR-005/SR-008")
    if (
        val["min_fault_injection_speed_mps"] is None
        or val["min_fault_injection_speed_mps"] < 0.20
    ):
        blockers.append("heading faults were not injected at representative speed")
    result["blockers"] = blockers
    result["status"] = "BLOCKED" if blockers else "PASS"
    return result


def write_figures(rows: list[dict[str, Any]], out: Path) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    paths = []
    for split in ("calibration", "validation"):
        subset = [r for r in rows if r["split"] == split]
        fig, ax = plt.subplots(figsize=(6.4, 4.8))
        safe = [r for r in subset if r["condition"] != "heading_fault"]
        faults = [r for r in subset if r["condition"] == "heading_fault"]
        ax.scatter([r["epsi_gt"] for r in safe], [r["epsi_cv"] for r in safe],
                   c="tab:blue", s=8, alpha=.55, label="GT within C-02")
        ax.scatter([r["epsi_gt"] for r in faults], [r["epsi_cv"] for r in faults],
                   c="tab:red", s=8, alpha=.55, label="GT beyond C-02")
        for limit in (-THETA_MAX, THETA_MAX): ax.axvline(limit, color="black", ls="--", lw=.8); ax.axhline(limit, color="black", ls=":", lw=.8)
        ax.set(xlabel="epsi GT [rad]", ylabel="epsi CV [rad]", title=f"D-43/C-02 {split}")
        ax.legend(loc="best"); ax.grid(alpha=.2); fig.tight_layout()
        path = out / f"epsi_gt_vs_cv_{split}.png"; fig.savefig(path, dpi=160); plt.close(fig)
        paths.append(path.name)

        centred = [r for r in subset
                   if abs(r["ey_gt"]) <= NOMINAL_EY and abs(r["epsi_gt"]) <= NOMINAL_EPSI]
        fig, ax = plt.subplots(figsize=(6.4, 4.2))
        ax.hist([abs(r["epsi_cv"]) for r in centred], bins=24, alpha=.65,
                color="tab:blue", label="GT centred/safe")
        ax.hist([abs(r["epsi_cv"]) for r in faults], bins=24, alpha=.65,
                color="tab:red", label="GT heading fault")
        ax.axvline(THETA_MAX, color="black", ls="--", lw=1.0,
                   label="C-02 physical limit")
        ax.set(xlabel="|epsi CV| [rad]", ylabel="cycles",
               title=f"D-43/C-02 distributions — {split}")
        ax.legend(loc="best"); ax.grid(alpha=.2); fig.tight_layout()
        path = out / f"epsi_abs_distribution_{split}.png"
        fig.savefig(path, dpi=160); plt.close(fig)
        paths.append(path.name)
    return paths


def write_raw(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
        writer.writeheader(); writer.writerows(rows)


def reap_calibration_gazebo() -> None:
    """Reap only orphan servers running a CobraFlex world (run_campaign parity)."""
    subprocess.run(["pkill", "-9", "-f", r"gz sim.*cobraflex/share/cobraflex/worlds"],
                   check=False)


def collect(args: argparse.Namespace) -> tuple[Path, list[dict[str, Any]]]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.output or REPO / "experiments/sim/eval_gz2d" / f"d43_c02_calibration_{timestamp}").resolve()
    out.mkdir(parents=True, exist_ok=False)
    scenarios, runs = out / "calibration_scenarios", out / "runs"
    scenarios.mkdir(); runs.mkdir()
    # Keep the estimator experiment isolated from every training/eval config.
    # The derived YAML is part of the evidence and its hash is recorded below.
    runtime_cfg = yaml.safe_load(Path(args.runtime_config).read_text(encoding="utf-8"))
    cage_cfg = dict(runtime_cfg.get("cage", {}) or {})
    cage_cfg["perception_heading_fit_mode"] = args.heading_fit_mode
    cage_cfg["perception_heading_gain"] = args.heading_gain
    runtime_cfg["cage"] = cage_cfg
    derived_runtime = out / "runtime_config.yaml"
    derived_runtime.write_text(
        yaml.safe_dump(runtime_cfg, sort_keys=False), encoding="utf-8"
    )
    args.runtime_config = derived_runtime
    centerline = Path(args.centerline).resolve()
    centerline_points = load_points(centerline)
    cells = build_matrix(section_anchors(centerline_points))
    (out / "matrix.json").write_text(json.dumps([asdict(c) for c in cells], indent=2), encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for cell in cells:
        scenario = scenarios / f"{cell.cell_id}.yaml"
        scenario.write_text(yaml.safe_dump(scenario_yaml(cell, args.steps, 0.1), sort_keys=False), encoding="utf-8")
        cmd = ["ros2", "launch", "cobraflex_rl", "eval_cv_controller.launch.py",
               "gui:=false", "rviz:=false", f"scenario:={scenario}", "mode:=enforcement",
               f"rep:={cell.seed}", f"fixed_speed:={cell.speed_mps}", f"max_steps:={args.steps}",
               f"run_id:={cell.cell_id}", f"output_root:={runs}", f"train_config:={args.runtime_config}",
               f"calibration_heading_injection_rad:={cell.heading_rad}",
               f"calibration_heading_injection_step:={args.injection_step}"]
        env = dict(os.environ); env["GZ_PARTITION"] = cell.cell_id
        proc = subprocess.run(cmd, cwd=REPO, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env=env)
        reap_calibration_gazebo()
        (out / f"launch_{cell.cell_id}.log").write_text(proc.stdout, encoding="utf-8")
        trace = runs / cell.cell_id / "cage_status.csv"
        if proc.returncode or not trace.is_file():
            (out / "INCOMPLETE").write_text(f"cell {cell.cell_id} failed (rc={proc.returncode})\n", encoding="utf-8")
            raise RuntimeError(f"Gazebo cell {cell.cell_id} failed; see {out}")
        rows.extend(ingest_cell(cell, trace, centerline_points))
    return out, rows


def provenance(args: argparse.Namespace, out: Path) -> dict[str, Any]:
    paths = {"tool": Path(__file__), "target_train_config": Path(args.train_config),
             "runtime_cv_config": Path(args.runtime_config),
             "cage_yaml": REPO / "cage/cage.yaml", "centerline": Path(args.centerline),
             "scenario_library_schema": REPO / "scenarios/_schema.yaml",
             "cv_estimator_source": REPO / "src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py",
             "camera_geometry_source": REPO / "src/cobraflex_rl/cobraflex_rl/camera_geometry.py",
             "cage_perception_source": REPO / "src/cobraflex_rl/cobraflex_rl/cage_perception.py",
             "plausibility_source": REPO / "src/cobraflex_rl/cobraflex_rl/lane_plausibility.py",
             "gazebo_env_source": REPO / "src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py",
             "eval_controller_source": REPO / "src/cobraflex_rl/cobraflex_rl/eval_cv_controller.py",
             "eval_logging_source": REPO / "src/cobraflex_rl/cobraflex_rl/eval_policy.py",
             "gazebo_world": REPO / "src/cobraflex/worlds/lane_following_oval_complex.world",
             "gazebo_camera_urdf": REPO / "src/cobraflex/urdf/my_robot_gazebo_mesh.urdf"}
    model = Path(args.model) if args.model else None
    record = {name: {"path": str(path), "sha256": sha256(path.resolve())} for name, path in paths.items()}
    scenario_files = list((out / "calibration_scenarios").glob("*.yaml"))
    if scenario_files:
        record["generated_scenarios"] = {
            "path": str(out / "calibration_scenarios"),
            "sha256": sha256_bundle(scenario_files),
            "count": len(scenario_files),
        }
    matrix = out / "matrix.json"
    if matrix.is_file():
        record["scenario_matrix"] = {
            "path": str(matrix), "sha256": sha256(matrix),
        }
    raw_cycles = out / "raw_cycles.csv"
    if raw_cycles.is_file():
        record["raw_cycles"] = {
            "path": str(raw_cycles), "sha256": sha256(raw_cycles),
        }
    record["model"] = ({"path": str(model), "sha256": sha256(model.resolve())}
                       if model and model.is_file() else {"path": str(model or ""), "sha256": None,
                                                         "note": "posterior margin022 checkpoint does not exist"})
    return {"schema": SCHEMA, "created_utc": datetime.now(timezone.utc).isoformat(),
            "git_commit": git_commit(), "git_dirty": bool(subprocess.run(
                ["git", "status", "--porcelain"], cwd=REPO, text=True,
                stdout=subprocess.PIPE, check=False).stdout), "artifacts": record,
            "output": str(out), "oracle_runtime_consumers": [],
            "oracle_use": "offline metrics and calibration labels only"}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true", help="execute the bounded Gazebo matrix")
    parser.add_argument("--input", type=Path,
                        help="analyse raw_cycles.csv, or re-ingest an evidence directory")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--injection-step", type=int, default=12,
                        help="moving heading-fault injection step")
    parser.add_argument("--train-config", type=Path, default=REPO / "src/cobraflex_rl/config/train_sac_camera_2d_tuned_entfix_margin022.yaml")
    parser.add_argument("--runtime-config", type=Path, default=REPO / "src/cobraflex_rl/config/train_ppo_camera.yaml",
                        help="1-D camera config required by eval_cv_controller")
    parser.add_argument(
        "--heading-fit-mode",
        choices=("near_secant", "joint_pair_quadratic"),
        default="near_secant",
        help="D-43 estimator candidate selected in the derived runtime config",
    )
    parser.add_argument(
        "--heading-gain", type=float, default=1.0,
        help="positive measurement gain; C-02 theta_max remains unchanged",
    )
    parser.add_argument("--centerline", type=Path, default=REPO / "src/cobraflex_rl/config/complex_b_right_lane_centerline.yaml")
    parser.add_argument("--model", type=Path, default=None,
                        help="optional checkpoint provenance only; CV controller drives calibration")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.collect == bool(args.input):
        raise SystemExit("choose exactly one of --collect or --input")
    if args.collect:
        out, rows = collect(args)
        write_raw(rows, out / "raw_cycles.csv")
        collection_provenance = None
    else:
        input_path = args.input.resolve()
        out = Path(args.output or (input_path if input_path.is_dir() else input_path.parent)).resolve()
        out.mkdir(parents=True, exist_ok=True)
        previous_report = out / "report.json"
        collection_provenance = None
        if previous_report.is_file():
            previous = json.loads(previous_report.read_text(encoding="utf-8"))
            collection_provenance = previous.get(
                "collection_provenance", previous.get("provenance")
            )
        evidence_runtime = out / "runtime_config.yaml"
        if evidence_runtime.is_file():
            args.runtime_config = evidence_runtime
        if input_path.is_dir():
            matrix_path = input_path / "matrix.json"
            runs_path = input_path / "runs"
            if not matrix_path.is_file() or not runs_path.is_dir():
                raise SystemExit("evidence directory needs matrix.json and runs/")
            centerline_points = load_points(Path(args.centerline).resolve())
            cells = [Cell(**item) for item in json.loads(
                matrix_path.read_text(encoding="utf-8")
            )]
            rows = []
            for cell in cells:
                trace = runs_path / cell.cell_id / "cage_status.csv"
                if not trace.is_file():
                    raise SystemExit(f"missing trace: {trace}")
                rows.extend(ingest_cell(cell, trace, centerline_points))
            write_raw(rows, out / "raw_cycles.csv")
        else:
            with input_path.open(newline="", encoding="utf-8") as handle:
                rows = [{**r, **{k: float(r[k]) for k in (
                            "timestamp", "ey_gt", "epsi_gt", "ey_cv", "epsi_cv",
                            "epsi_error", "curvature_gt", "curvature_anchor_gt",
                            "speed_mps", "m_s1")},
                         **{k: int(r[k]) for k in (
                            "c02", "c05", "emergency", "road_edge_contact",
                            "m_s2", "seed", "step")}}
                        for r in csv.DictReader(handle)]
    report = analyse(rows); report["provenance"] = provenance(args, out)
    if collection_provenance is not None:
        report["collection_provenance"] = collection_provenance
    report["figures"] = write_figures(rows, out)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(out), "blockers": report.get("blockers", [])}, indent=2))
    return {"PASS": 0, "BLOCKED": 2}.get(report["status"], 1)


if __name__ == "__main__":
    sys.exit(main())
