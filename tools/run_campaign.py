#!/usr/bin/env python3
"""
run_campaign — orchestrate the Phase-4 scenario-validation campaign and
aggregate per-run → per-scenario → per-SR → global verdicts.

The tool has two layers:

  * **PURE core (no ROS).** Scenario/SR loading, run-matrix generation, per-run
    verdict evaluation from the scenarios' pass-criterion strings, and the
    aggregation that follows D-29 (run counts by SR criticality) and D-30
    (an SR-CL-A failure vetoes the global verdict). Unit-tested in
    `policy/tests/test_run_campaign.py`; runnable on any host.

  * **EXECUTOR seam.** ``execute_run(run_spec) -> metrics`` actually drives one
    scenario run. The real executor invokes Gazebo via ``eval_policy`` with the
    scenario's ``track`` (world/centerline/start_s), mode (enforcement vs
    monitoring), perturbations and controller — that part needs the
    Ubuntu+Jazzy host. ``--dry-run`` skips execution entirely and only validates
    the campaign **plan** (the run matrix + the D-29 coverage feasibility),
    which is useful before committing the ~1100-run budget and runs anywhere.

Usage:
  python tools/run_campaign.py --dry-run
  python tools/run_campaign.py --controllers rl,pd --seeds 42,123,2024 \
      --modes enforcement,monitoring --out experiments/sim/campaign
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import yaml

REPO = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO / "scenarios"
SR_CSV = REPO / "docs" / "data" / "safety_requirements.csv"

# D-29: minimum independent runs per scenario family for the per-SR verdict to be
# statistically discriminating, keyed by criticality class. SR-CL-C accepts
# informal evidence (0 = no hard count requirement).
MIN_RUNS_BY_CRITICALITY: Dict[str, int] = {
    "SR-CL-A": 25,
    "SR-CL-B": 10,
    "SR-CL-C": 0,
}

# NOM = nominal family; EDGE/PERT = adverse family (D-29 requires an SR-CL-A to be
# covered in >=1 nominal AND >=1 adverse family).
NOMINAL_PREFIXES = ("SC-NOM",)
ADVERSE_PREFIXES = ("SC-EDGE", "SC-PERT")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
@dataclass
class Scenario:
    id: str
    category: str
    is_stub: bool
    references_SR: List[str] = field(default_factory=list)
    pass_criterion_per_run: str = ""
    pass_criterion_per_scenario: str = ""
    n_runs: Dict[str, int] = field(default_factory=dict)  # mode -> count
    track: Dict[str, object] = field(default_factory=dict)

    @property
    def family(self) -> str:
        if self.id.startswith(NOMINAL_PREFIXES):
            return "nominal"
        if self.id.startswith(ADVERSE_PREFIXES):
            return "adverse"
        return "unknown"


def load_scenarios(scenario_dir: Path = SCENARIO_DIR) -> Dict[str, Scenario]:
    out: Dict[str, Scenario] = {}
    for path in sorted(scenario_dir.glob("*/*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "id" not in data:
            continue
        out[data["id"]] = Scenario(
            id=data["id"],
            category=data.get("category", ""),
            is_stub=data.get("status") == "stub",
            references_SR=list(data.get("references_SR", []) or []),
            pass_criterion_per_run=str(data.get("pass_criterion_per_run", "")),
            pass_criterion_per_scenario=str(data.get("pass_criterion_per_scenario", "")),
            n_runs=dict(data.get("n_runs_recommended", {}) or {}),
            track=dict(data.get("track", {}) or {}),
        )
    return out


def load_srs(csv_path: Path = SR_CSV) -> Dict[str, Dict[str, object]]:
    """SR id -> {criticality, scenarios(list)}; from the canonical SR register CSV."""
    out: Dict[str, Dict[str, object]] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            scen = [s.strip() for s in (row.get("scenarios") or "").split(",") if s.strip()]
            out[row["id"]] = {
                "criticality": row.get("criticality", "").strip(),
                "scenarios": scen,
            }
    return out


def expand_sr_scenarios(sr_scenarios: Sequence[str], all_scenario_ids: Sequence[str]) -> List[str]:
    """Expand the ``"ALL"`` convention (docs/05): an SR exercised by every scenario
    — notably SR-006, the always-active rate limiter — lists ``ALL`` instead of
    enumerating them. Any other token is passed through unchanged."""
    if any(str(s).upper() == "ALL" for s in sr_scenarios):
        return list(all_scenario_ids)
    return list(sr_scenarios)


# --------------------------------------------------------------------------- #
# Run matrix
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RunSpec:
    scenario_id: str
    mode: str          # enforcement | monitoring
    controller: str    # rl | pd
    seed: Optional[int]  # policy seed for rl; None for pd
    rep: int           # 0..n_runs-1


def build_matrix(
    scenarios: Dict[str, Scenario],
    controllers: Sequence[str],
    seeds: Sequence[int],
    modes: Sequence[str],
    include_stubs: bool = False,
) -> List[RunSpec]:
    """Cartesian campaign matrix: scenario × mode × controller × (seed for rl) ×
    repetition (n_runs_recommended[mode]). Stubs are skipped unless requested."""
    runs: List[RunSpec] = []
    for sid, scen in scenarios.items():
        if scen.is_stub and not include_stubs:
            continue
        for mode in modes:
            n = int(scen.n_runs.get(mode, 0))
            for controller in controllers:
                seed_axis: Sequence[Optional[int]] = seeds if controller == "rl" else [None]
                for seed in seed_axis:
                    for rep in range(n):
                        runs.append(RunSpec(sid, mode, controller, seed, rep))
    return runs


# --------------------------------------------------------------------------- #
# Verdict evaluation (pure)
# --------------------------------------------------------------------------- #
_METRIC_TOKEN = re.compile(r"\bM-([A-Z]\d+)\b")


def evaluate_criterion(expr: str, values: Dict[str, object]) -> bool:
    """Evaluate a scenario pass-criterion string against a values dict.

    The criterion uses metric ids (``M-P1``), bare names (``emergency``,
    ``fraction_pass``) and the connectives AND/OR/NOT — e.g.
    ``"M-P1 < 0.05 AND M-P2 == 1 AND emergency == False"``. Metric ids are
    rewritten to valid identifiers (``M-P1`` -> ``M_P1``) and the expression is
    evaluated in a sandbox with no builtins. Inputs come from the repo's own
    trusted YAMLs, never from user input.
    """
    if not expr.strip():
        raise ValueError("empty criterion")
    safe = f" {expr} ".replace(" AND ", " and ").replace(" OR ", " or ").replace(" NOT ", " not ")
    safe = _METRIC_TOKEN.sub(lambda m: f"M_{m.group(1)}", safe)
    ns = {k.replace("-", "_"): v for k, v in values.items()}
    return bool(eval(safe, {"__builtins__": {}}, ns))  # noqa: S307 (sandboxed, trusted input)


# --------------------------------------------------------------------------- #
# Aggregation (pure): per-scenario, per-SR (D-29), global (D-30)
# --------------------------------------------------------------------------- #
@dataclass
class ScenarioResult:
    scenario_id: str
    mode: str
    n_runs: int
    n_pass: int
    verdict: bool

    @property
    def fraction_pass(self) -> float:
        return self.n_pass / self.n_runs if self.n_runs else 0.0


def aggregate_scenario(
    scenario: Scenario, mode: str, run_pass_flags: Sequence[bool]
) -> ScenarioResult:
    n = len(run_pass_flags)
    n_pass = sum(1 for f in run_pass_flags if f)
    fraction_pass = n_pass / n if n else 0.0
    verdict = evaluate_criterion(
        scenario.pass_criterion_per_scenario, {"fraction_pass": fraction_pass}
    )
    return ScenarioResult(scenario.id, mode, n, n_pass, verdict)


@dataclass
class SRResult:
    sr_id: str
    criticality: str
    verdict: bool
    run_count_ok: bool          # D-29 run-count + family coverage met
    families_covered: List[str]
    notes: str = ""


def aggregate_sr(
    sr_id: str,
    criticality: str,
    sr_scenarios: Sequence[str],
    scenario_objs: Dict[str, Scenario],
    scenario_results: Dict[str, ScenarioResult],
    runs_per_scenario: Dict[str, int],
    verdict_mode: str = "enforcement",
) -> SRResult:
    """Per-SR verdict + D-29 sufficiency.

    The SR is *satisfied* iff every executed scenario that verifies it passes
    (in ``verdict_mode``). ``run_count_ok`` is the D-29 sufficiency flag: each
    contributing family must reach MIN_RUNS_BY_CRITICALITY, and an SR-CL-A must
    additionally be covered in >=1 nominal AND >=1 adverse family.
    """
    min_runs = MIN_RUNS_BY_CRITICALITY.get(criticality, 0)
    families: set[str] = set()
    all_pass = True
    any_executed = False
    enough_runs = True
    for sid in sr_scenarios:
        scen = scenario_objs.get(sid)
        if scen is None or scen.is_stub:
            enough_runs = False  # a stub cannot contribute runs yet
            continue
        res = scenario_results.get(sid)
        if res is None:
            enough_runs = False
            continue
        any_executed = True
        families.add(scen.family)
        if not res.verdict:
            all_pass = False
        if runs_per_scenario.get(sid, 0) < min_runs:
            enough_runs = False

    coverage_ok = True
    if criticality == "SR-CL-A":
        coverage_ok = ("nominal" in families) and ("adverse" in families)

    verdict = all_pass and any_executed
    run_count_ok = enough_runs and coverage_ok and any_executed
    notes = ""
    if not any_executed:
        notes = "no executable scenario yet (all stubs/missing)"
    elif not run_count_ok:
        notes = "D-29 not met (insufficient runs or family coverage)"
    return SRResult(sr_id, criticality, verdict, run_count_ok, sorted(families), notes)


def global_verdict(sr_results: Sequence[SRResult]) -> Dict[str, object]:
    """D-30: the global verdict is 'satisfied' iff every SR-CL-A is satisfied
    (and its run-count is sufficient). SR-CL-B/C contribute nuance, not vetoes."""
    cl_a = [r for r in sr_results if r.criticality == "SR-CL-A"]
    blocking = [r for r in cl_a if not (r.verdict and r.run_count_ok)]
    return {
        "verdict": "SATISFIED" if not blocking else "NOT SATISFIED",
        "blocking_sr_cl_a": [r.sr_id for r in blocking],
        "n_sr_cl_a": len(cl_a),
    }


# --------------------------------------------------------------------------- #
# Dry-run plan / D-29 feasibility (pure, runnable anywhere)
# --------------------------------------------------------------------------- #
def plan_feasibility(
    scenarios: Dict[str, Scenario],
    srs: Dict[str, Dict[str, object]],
    verdict_mode: str = "enforcement",
) -> List[Dict[str, object]]:
    """For each SR, report whether the *current* (non-stub) scenario library can,
    in principle, satisfy D-29: enough runs per family in ``verdict_mode`` and
    (for SR-CL-A) nominal+adverse coverage. Surfaces coverage gaps caused by the
    still-stubbed scenarios before any run is launched."""
    report: List[Dict[str, object]] = []
    for sr_id, sr in sorted(srs.items()):
        crit = str(sr["criticality"])
        min_runs = MIN_RUNS_BY_CRITICALITY.get(crit, 0)
        families: Dict[str, int] = {"nominal": 0, "adverse": 0}
        gaps: List[str] = []
        sr_scen = expand_sr_scenarios(sr["scenarios"], list(scenarios))
        for sid in sr_scen:
            scen = scenarios.get(sid)
            if scen is None:
                gaps.append(f"{sid}:missing")
                continue
            if scen.is_stub:
                gaps.append(f"{sid}:stub")
                continue
            runs = int(scen.n_runs.get(verdict_mode, 0))
            fam = scen.family
            if runs >= min_runs:
                families[fam] = max(families[fam], runs)
            else:
                gaps.append(f"{sid}:{runs}<{min_runs}")
        if crit == "SR-CL-A":
            feasible = families["nominal"] >= min_runs and families["adverse"] >= min_runs
        else:
            feasible = (families["nominal"] + families["adverse"]) >= min_runs
        report.append({
            "sr": sr_id, "criticality": crit, "min_runs": min_runs,
            "feasible": feasible, "families": dict(families), "gaps": gaps,
        })
    return report


# --------------------------------------------------------------------------- #
# Executor seam (ROS / Gazebo — Ubuntu host)
# --------------------------------------------------------------------------- #
def execute_run(run_spec: RunSpec, scenario: Scenario) -> Dict[str, object]:  # pragma: no cover
    """Drive one scenario run in Gazebo and return its computed metrics.

    NOT IMPLEMENTED here: this is the ROS/Gazebo layer. It must invoke
    ``eval_policy`` with the scenario's ``track`` (world/centerline/start_s_m),
    the run mode (``--mode enforcement|monitoring`` — the cage already supports
    monitoring, see cage_node.py), the controller (rl/pd), the policy seed, and
    the scenario perturbations, then parse the run's metrics. Implement on the
    Ubuntu+Jazzy host as the next step; ``--dry-run`` does not call this.
    """
    raise NotImplementedError(
        "execute_run requires the Gazebo executor (eval_policy with "
        "--mode/--start-s/--perturbation); run on the Ubuntu+Jazzy host."
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase-4 scenario validation campaign.")
    p.add_argument("--controllers", default="rl,pd")
    p.add_argument("--seeds", default="42,123,2024")
    p.add_argument("--modes", default="enforcement,monitoring")
    p.add_argument("--verdict-mode", default="enforcement")
    p.add_argument("--out", type=Path, default=REPO / "experiments" / "sim" / "campaign")
    p.add_argument("--dry-run", action="store_true",
                   help="build the matrix + D-29 feasibility and stop (no Gazebo).")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    scenarios = load_scenarios()
    srs = load_srs()
    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    matrix = build_matrix(scenarios, controllers, seeds, modes)

    n_full = sum(1 for s in scenarios.values() if not s.is_stub)
    n_stub = sum(1 for s in scenarios.values() if s.is_stub)
    print("Phase-4 campaign plan")
    print("=" * 56)
    print(f"scenarios: {len(scenarios)} ({n_full} executable, {n_stub} stub)")
    print(f"controllers={controllers}  seeds={seeds}  modes={modes}")
    print(f"total executable runs in matrix: {len(matrix)}")

    print("\nD-29 feasibility (verdict mode = %s):" % args.verdict_mode)
    feas = plan_feasibility(scenarios, srs, verdict_mode=args.verdict_mode)
    for row in feas:
        flag = "OK " if row["feasible"] else "GAP"
        print(f"  [{flag}] {row['sr']} ({row['criticality']}, min {row['min_runs']}/family)"
              f" families={row['families']}"
              + (f"  gaps={row['gaps']}" if row["gaps"] else ""))
    n_gap = sum(1 for r in feas if not r["feasible"])
    print(f"\n{n_gap} SR(s) not yet D-29-feasible — see the gaps above "
          "(insufficient runs per family, or missing nominal+adverse coverage).")

    if args.dry_run:
        print("\n--dry-run: plan only, no Gazebo execution.")
        return 0

    # Execution path (Ubuntu+Jazzy host): execute_run per matrix entry, then
    # aggregate. Left as the executor-wiring step.
    raise SystemExit(
        "Execution path not wired on this host. Use --dry-run for planning, or "
        "implement execute_run() on the Ubuntu+Jazzy host (see its docstring)."
    )


if __name__ == "__main__":
    raise SystemExit(main())
