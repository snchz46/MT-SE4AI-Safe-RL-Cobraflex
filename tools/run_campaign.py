#!/usr/bin/env python3
"""
run_campaign — orchestrate the Phase-4 scenario-validation campaign and
aggregate per-run → per-scenario → per-SR → global verdicts.

The tool has two layers:

  * **PURE core (no ROS).** Scenario/SR loading, run-matrix generation, per-run
    verdict evaluation from the scenarios' pass-criterion strings, and the
    aggregation that follows D-29 (run counts by SR criticality) and D-30
    (an SR-CL-A failure vetoes the global verdict). Per-run verdicts are
    *three-valued* (True/False/None): an indeterminate (None) run — an
    instrumentation gap or an errored run — is **excluded** from the pass
    fraction rather than collapsed to a fail, so a scenario with no evaluable
    runs is *indeterminate* and propagates as ``insufficient_evidence``, never as
    a safety violation. This matches the unit-tested D-29/D-30 spine
    `cobraflex_rl/verdict_aggregation.py` (reconciliation recorded as **D-38**).
    Unit-tested in `policy/tests/test_run_campaign.py`; runnable on any host.

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
import json
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
ADVERSE_PREFIXES = ("SC-EDGE", "SC-PERT", "SC-FRONT")


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
@dataclass
class Scenario:
    """One scenario YAML as the campaign driver consumes it."""
    id: str
    category: str
    is_stub: bool
    references_SR: List[str] = field(default_factory=list)
    pass_criterion_per_run: str = ""
    pass_criterion_per_scenario: str = ""
    n_runs: Dict[str, int] = field(default_factory=dict)  # mode -> count
    track: Dict[str, object] = field(default_factory=dict)
    path: Optional[Path] = None  # source YAML, for the Gazebo executor

    @property
    def family(self) -> str:
        if self.id.startswith(NOMINAL_PREFIXES):
            return "nominal"
        if self.id.startswith(ADVERSE_PREFIXES):
            return "adverse"
        return "unknown"


def load_scenarios(scenario_dir: Path = SCENARIO_DIR) -> Dict[str, Scenario]:
    """Load every scenario YAML under scenarios/, keyed by scenario id."""
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
            path=path,
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
    """One executable (scenario, mode, rep) cell of the campaign matrix."""
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
    reps_cap: Optional[int] = None,
) -> List[RunSpec]:
    """Cartesian campaign matrix: scenario × mode × controller × (seed for rl) ×
    repetition (n_runs_recommended[mode]). Stubs are skipped unless requested.
    ``reps_cap`` caps the per-scenario repetitions (for a quick validation subset
    below the full D-29 counts)."""
    runs: List[RunSpec] = []
    for sid, scen in scenarios.items():
        if scen.is_stub and not include_stubs:
            continue
        for mode in modes:
            n = int(scen.n_runs.get(mode, 0))
            if reps_cap is not None:
                n = min(n, reps_cap)
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
    """Aggregated per-(scenario, mode) verdict counts and scenario verdict."""
    scenario_id: str
    mode: str
    n_runs: int
    n_pass: int
    n_fail: int
    n_indeterminate: int
    verdict: Optional[bool]   # True | False | None (None == indeterminate/insufficient)

    @property
    def evaluable(self) -> int:
        """Runs that produced a pass-or-fail verdict (indeterminate excluded)."""
        return self.n_pass + self.n_fail

    @property
    def fraction_pass(self) -> Optional[float]:
        """Pass fraction over *evaluable* runs; None if every run was indeterminate.

        Indeterminate runs (a per-run verdict of ``None`` — the metric was not
        computable, an instrumentation gap, or the run errored) are excluded from
        the denominator, matching the D-29/D-30 spine
        (`cobraflex_rl/verdict_aggregation.evaluate_scenario`). Counting them inside
        the denominator would collapse "no evidence" into "failed" (cf. D-38)."""
        return (self.n_pass / self.evaluable) if self.evaluable else None


def aggregate_scenario(
    scenario: Scenario, mode: str, run_verdicts: Sequence[Optional[bool]]
) -> ScenarioResult:
    """Reduce three-valued per-run verdicts (True/False/None) to a scenario result.

    The pass fraction is taken over the *evaluable* (pass+fail) runs; if every run
    was indeterminate the scenario verdict is ``None`` (insufficient evidence), not
    a fail. This mirrors `verdict_aggregation.evaluate_scenario` (D-38)."""
    n = len(run_verdicts)
    n_pass = sum(1 for v in run_verdicts if v is True)
    n_fail = sum(1 for v in run_verdicts if v is False)
    n_indet = n - n_pass - n_fail
    evaluable = n_pass + n_fail
    if evaluable == 0:
        verdict: Optional[bool] = None  # all indeterminate -> insufficient evidence
    else:
        verdict = evaluate_criterion(
            scenario.pass_criterion_per_scenario, {"fraction_pass": n_pass / evaluable}
        )
    return ScenarioResult(scenario.id, mode, n, n_pass, n_fail, n_indet, verdict)


@dataclass
class SRResult:
    """Per-SR roll-up across its verifying scenarios (the docs/07 verdict input)."""
    sr_id: str
    criticality: str
    status: str                 # satisfied | failed | insufficient_evidence | not_run
    run_count_ok: bool          # D-29 run-count + family coverage met
    families_covered: List[str]
    failing_scenarios: List[str] = field(default_factory=list)
    indeterminate_scenarios: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def verdict(self) -> Optional[bool]:
        """Three-valued convenience view of ``status``: True (satisfied),
        False (failed), None (insufficient_evidence / not_run)."""
        if self.status == "satisfied":
            return True
        if self.status == "failed":
            return False
        return None


def aggregate_sr(
    sr_id: str,
    criticality: str,
    sr_scenarios: Sequence[str],
    scenario_objs: Dict[str, Scenario],
    scenario_results: Dict[str, ScenarioResult],
    runs_per_scenario: Dict[str, int],
    verdict_mode: str = "enforcement",
) -> SRResult:
    """Per-SR status + D-29 sufficiency, following the verdict_aggregation spine.

    Precedence (mirrors `verdict_aggregation.sr_verdict`, D-38): a real scenario
    *failure* dominates; otherwise the D-29 run-count/coverage gate; otherwise an
    *indeterminate* scenario (per-run verdicts all None — an instrumentation gap,
    not a violation) yields ``insufficient_evidence``; otherwise ``satisfied``.
    Crucially an indeterminate scenario is **never** scored as a failure.
    ``run_count_ok`` is the D-29 sufficiency flag: each contributing family must
    reach MIN_RUNS_BY_CRITICALITY, and an SR-CL-A must additionally be covered in
    >=1 nominal AND >=1 adverse family.
    """
    min_runs = MIN_RUNS_BY_CRITICALITY.get(criticality, 0)
    families: set[str] = set()
    failing: List[str] = []
    indeterminate: List[str] = []
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
        if res.verdict is False:
            failing.append(sid)
        elif res.verdict is None:
            indeterminate.append(sid)
        if runs_per_scenario.get(sid, 0) < min_runs:
            enough_runs = False

    coverage_ok = True
    if criticality == "SR-CL-A":
        coverage_ok = ("nominal" in families) and ("adverse" in families)
    run_count_ok = enough_runs and coverage_ok and any_executed

    if not any_executed:
        status = "not_run"
        notes = "no executable scenario yet (all stubs/missing)"
    elif failing:
        status = "failed"
        notes = f"failing scenario(s): {sorted(failing)}"
    elif not run_count_ok:
        status = "insufficient_evidence"
        notes = "D-29 not met (insufficient runs or family coverage)"
    elif indeterminate:
        status = "insufficient_evidence"
        notes = f"indeterminate scenario(s) - instrumentation gap, not a failure: {sorted(indeterminate)}"
    else:
        status = "satisfied"
        notes = ""
    return SRResult(sr_id, criticality, status, run_count_ok, sorted(families),
                    sorted(failing), sorted(indeterminate), notes)


def global_verdict(sr_results: Sequence[SRResult]) -> Dict[str, object]:
    """D-30: the global verdict is 'SATISFIED' iff every SR-CL-A is satisfied
    (and its run-count is sufficient). A failing SR-CL-A vetoes it ('NOT
    SATISFIED'); an SR-CL-A whose evidence is merely *indeterminate* or
    under-covered makes it 'INCOMPLETE' (not a safety violation). This three-way
    distinction mirrors `verdict_aggregation.global_verdict` (failed → failed,
    insufficient → incomplete; D-38). SR-CL-B/C contribute nuance, not vetoes."""
    cl_a = [r for r in sr_results if r.criticality == "SR-CL-A"]
    failed = [r.sr_id for r in cl_a if r.status == "failed"]
    incomplete = [r.sr_id for r in cl_a
                  if r.status in ("insufficient_evidence", "not_run")
                  or (r.status == "satisfied" and not r.run_count_ok)]
    if failed:
        verdict = "NOT SATISFIED"
    elif incomplete:
        verdict = "INCOMPLETE"
    else:
        verdict = "SATISFIED"
    return {
        "verdict": verdict,
        "blocking_sr_cl_a": failed,
        "incomplete_sr_cl_a": incomplete,
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
            if fam not in families:
                gaps.append(f"{sid}:family={fam}")
                continue
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
CHECKPOINT_DIR = REPO / "experiments" / "sim"


DEFAULT_CHECKPOINT_TEMPLATE = "cobraflex_ppo_lane_{seed}_200k.zip"


def checkpoint_for_seed(
    seed: Optional[int], template: str = DEFAULT_CHECKPOINT_TEMPLATE
) -> Path:
    """The trained PPO checkpoint for a policy seed. The default template is
    the F3 multi-seed set; the track-'E' camera campaign passes its own
    (e.g. ``cobraflex_ppo_cam_lane_{seed}_200k.zip``)."""
    return CHECKPOINT_DIR / template.format(seed=seed)


def resolve_world_path(world_name: str) -> Path:
    """Absolute path for a scenario's ``track.world`` name.

    Prefers the installed cobraflex share (what the launch default uses); falls
    back to the source tree, which is content-identical under
    ``--symlink-install``. Raises if the world doesn't exist anywhere — better
    to fail the cell at plan time than launch Gazebo into a missing file.
    """
    candidate = Path(world_name)
    if candidate.is_absolute() and candidate.is_file():
        return candidate
    try:  # pragma: no cover - needs a sourced ROS2 env
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("cobraflex")) / "worlds" / world_name
        if share.is_file():
            return share
    except Exception:
        pass
    src = REPO / "src" / "cobraflex" / "worlds" / world_name
    if src.is_file():
        return src
    raise FileNotFoundError(f"scenario world not found: {world_name}")


def run_id_for(run_spec: RunSpec) -> str:
    """Deterministic, collision-free run id for a matrix cell, so the executor
    can locate the run dir it just produced and the campaign tree is traceable."""
    who = "pd" if run_spec.controller == "pd" else f"seed{run_spec.seed}"
    sid = run_spec.scenario_id.replace("SC-", "").replace("-", "").lower()
    return f"camp_{sid}_{run_spec.controller}_{who}_{run_spec.mode}_rep{run_spec.rep:02d}"


def _read_summary(output_root: Path, run_id: str) -> Optional[Dict[str, object]]:
    """Load a run's summary.json (None when missing/unreadable)."""
    summary_path = Path(output_root) / run_id / "summary.json"
    if summary_path.is_file():
        with summary_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    return None


def _reap_orphan_gazebo() -> int:
    """Kill any lingering ``gz sim`` server for a cobraflex world.

    The launch's on-exit Shutdown does NOT reliably kill the ``gz sim`` ruby
    server: it ignores SIGINT and is frequently reparented to init, surviving the
    ``ros2 launch`` exit. Across a campaign these orphans accumulate at ~2 GB each
    and exhaust RAM (observed: 14 orphans = 25 GB, system thrashing). Campaign
    runs are strictly serial (subprocess.run blocks, with a settle between), so
    after a run returns there must be no gz server we still need — reap it. Scoped
    to the cobraflex worlds path so an unrelated gz the user started is untouched.
    Returns the pkill return code (0 = killed something, 1 = nothing to kill)."""
    import subprocess
    proc = subprocess.run(
        ["pkill", "-9", "-f", r"gz sim.*cobraflex/share/cobraflex/worlds"],
        check=False,
    )
    return proc.returncode


def execute_run(
    run_spec: RunSpec,
    scenario: Scenario,
    *,
    output_root: Path,
    model_path: Optional[Path] = None,
    gui: bool = False,
    rviz: bool = False,
    timeout_s: int = 900,
    resume: bool = False,
    retries: int = 2,
    train_config: str = "",
    checkpoint_template: str = DEFAULT_CHECKPOINT_TEMPLATE,
) -> Dict[str, object]:  # pragma: no cover - drives Gazebo, host-only
    """Drive one scenario run in Gazebo (headless) and return its ``summary.json``.

    Shells out to ``ros2 launch cobraflex_rl eval_scenario_batch.launch.py`` for
    the (scenario, mode, rep) cell — the launch injects the scenario's initial
    conditions through ``eval_policy`` and auto-shuts-down on completion — then
    reads back the per-run metric catalogue + verdict the node wrote. RL only;
    the PD-baseline arm is a separate node (deferred).

    With ``resume=True`` a cell whose ``summary.json`` already exists is read back
    without re-launching, so an interrupted long campaign continues where it
    stopped instead of re-running completed cells.
    """
    import os
    import subprocess
    import time

    run_id = run_id_for(run_spec)
    if resume:
        cached = _read_summary(output_root, run_id)
        if cached is not None:
            return cached

    if run_spec.controller != "rl":
        raise NotImplementedError(
            "execute_run drives the RL policy via eval_policy; the PD-baseline "
            "arm uses pd_baseline_node and is not wired yet (use --controllers rl)."
        )
    if scenario.path is None:
        raise ValueError(f"{scenario.id}: scenario has no source path to run")
    checkpoint = (
        Path(model_path) if model_path
        else checkpoint_for_seed(run_spec.seed, checkpoint_template)
    )
    if not checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found for seed {run_spec.seed}: {checkpoint}")

    output_root = Path(output_root)
    cmd = [
        "ros2", "launch", "cobraflex_rl", "eval_scenario_batch.launch.py",
        f"model_path:={checkpoint}",
        f"scenario:={scenario.path}",
        f"mode:={run_spec.mode}",
        f"rep:={run_spec.rep}",
        f"run_id:={run_id}",
        f"output_root:={output_root}",
        f"gui:={'true' if gui else 'false'}",
        f"rviz:={'true' if rviz else 'false'}",
        f"train_config:={train_config}",
    ]
    # World-variant scenarios (SC-PERT-09/10: worn / wet oval textures) name a
    # non-default world in their track block; everything else keeps the launch
    # default so the F-track cells are byte-identical to the pre-E behaviour.
    world_name = str(scenario.track.get("world") or "").strip()
    if world_name and world_name != "lane_following_oval.world":
        cmd.append(f"world:={resolve_world_path(world_name)}")
    # Isolate this run's Gazebo transport in its own partition, so a lingering
    # gz server from the previous run (the EmitEvent(Shutdown) teardown can lag
    # past ros2 launch's exit) cannot cross-talk with this one via gz's
    # aggressive discovery — the cause of the inter-run odom "jump". Within the
    # run all components inherit the same partition and talk to each other fine.
    env = dict(os.environ)
    env["GZ_PARTITION"] = run_id

    # Retry on a flaky Gazebo boot: a run occasionally produces no summary even
    # with launch rc=0 (e.g. /odom never arrived within the env's wait, so reset
    # raised). These are transient and recover on a fresh launch, so re-attempt a
    # few times before recording the cell as a hard failure — important for an
    # unattended multi-hundred-run campaign. Success = "the node wrote a
    # summary.json"; the launch rc is not gated on (Gazebo teardown can be non-zero
    # even on a completed run).
    last_rc: Optional[int] = None
    for attempt in range(retries + 1):
        proc = subprocess.run(cmd, timeout=timeout_s, env=env)
        last_rc = proc.returncode
        summary = _read_summary(output_root, run_id)
        # Reap the gz server the launch leaves orphaned (see _reap_orphan_gazebo)
        # before returning or retrying — otherwise every run leaks ~2 GB.
        _reap_orphan_gazebo()
        if summary is not None:
            return summary
        if attempt < retries:
            time.sleep(3.0)  # let Gazebo fully die before re-launching
    raise RuntimeError(
        f"run produced no summary.json after {retries + 1} attempts "
        f"(last launch rc={last_rc}): {output_root / run_id / 'summary.json'}"
    )


# --------------------------------------------------------------------------- #
# Orchestration (drives the matrix, aggregates per D-29/D-30)
# --------------------------------------------------------------------------- #
@dataclass
class RunOutcome:
    """Result of executing one RunSpec: the per-run verdict or the error."""
    run_spec: RunSpec
    verdict: Optional[bool]            # per-run pass (eval_policy's 3-valued result)
    summary: Dict[str, object] = field(default_factory=dict)
    error: Optional[str] = None


Executor = Callable[..., Dict[str, object]]


def run_matrix(
    matrix: Sequence[RunSpec],
    scenarios: Dict[str, Scenario],
    output_root: Path,
    executor: Executor = execute_run,
    *,
    continue_on_error: bool = True,
    settle_s: float = 0.0,
    on_progress: Optional[Callable[[int, int, RunOutcome], None]] = None,
) -> List[RunOutcome]:
    """Execute every matrix cell through ``executor`` and collect per-run
    verdicts. ``executor`` is injectable so the orchestration is unit-tested with
    a stub (no Gazebo). A failed run is recorded as an outcome with ``error`` set
    (and ``verdict=None``) unless ``continue_on_error`` is False. ``settle_s``
    pauses between runs to let the previous Gazebo fully tear down before the
    next launch (belt-and-suspenders alongside the per-run GZ_PARTITION)."""
    import time

    outcomes: List[RunOutcome] = []
    total = len(matrix)
    for i, run_spec in enumerate(matrix, start=1):
        scenario = scenarios[run_spec.scenario_id]
        try:
            summary = executor(run_spec, scenario, output_root=output_root)
            verdict = summary.get("verdict") if isinstance(summary, dict) else None
            outcome = RunOutcome(run_spec, verdict if isinstance(verdict, bool) else None, dict(summary))
        except Exception as exc:  # noqa: BLE001 - record and continue the campaign
            if not continue_on_error:
                raise
            outcome = RunOutcome(run_spec, None, {}, error=f"{type(exc).__name__}: {exc}")
        outcomes.append(outcome)
        if on_progress is not None:
            on_progress(i, total, outcome)
        if settle_s > 0 and i < total:
            time.sleep(settle_s)
    return outcomes


def aggregate_campaign(
    outcomes: Sequence[RunOutcome],
    scenarios: Dict[str, Scenario],
    srs: Dict[str, Dict[str, object]],
    verdict_mode: str = "enforcement",
) -> Dict[str, object]:
    """Aggregate per-run outcomes into per-scenario, per-SR (D-29) and global
    (D-30) verdicts. A per-run ``verdict`` of None (indeterminate or errored) is
    *excluded* from the scenario pass fraction (not counted as a fail), matching
    the verdict_aggregation spine (D-38); its count is surfaced in
    ``n_indeterminate`` and, when it came from an executor error, ``n_error``."""
    # Group per (scenario, mode).
    groups: Dict[tuple, List[RunOutcome]] = {}
    for o in outcomes:
        groups.setdefault((o.run_spec.scenario_id, o.run_spec.mode), []).append(o)

    scenario_results: Dict[str, ScenarioResult] = {}   # verdict_mode results, by scenario
    runs_per_scenario: Dict[str, int] = {}
    per_scenario_report: List[Dict[str, object]] = []
    for (sid, mode), group in sorted(groups.items()):
        scen = scenarios.get(sid)
        if scen is None:
            continue
        verdicts = [o.verdict for o in group]  # three-valued: True | False | None
        result = aggregate_scenario(scen, mode, verdicts)
        n_error = sum(1 for o in group if o.error is not None)
        per_scenario_report.append({
            "scenario": sid, "mode": mode, "n_runs": result.n_runs,
            "n_pass": result.n_pass, "n_fail": result.n_fail,
            "n_indeterminate": result.n_indeterminate,
            "fraction_pass": (round(result.fraction_pass, 4)
                              if result.fraction_pass is not None else None),
            "verdict": result.verdict, "n_error": n_error,
        })
        if mode == verdict_mode:
            scenario_results[sid] = result
            runs_per_scenario[sid] = result.n_runs

    sr_results: List[SRResult] = []
    for sr_id, sr in sorted(srs.items()):
        crit = str(sr["criticality"])
        sr_scen = expand_sr_scenarios(sr["scenarios"], list(scenarios))
        sr_results.append(aggregate_sr(
            sr_id, crit, sr_scen, scenarios, scenario_results, runs_per_scenario,
            verdict_mode=verdict_mode,
        ))

    gv = global_verdict(sr_results)
    return {
        "verdict_mode": verdict_mode,
        "global": gv,
        "per_scenario": per_scenario_report,
        "per_sr": [
            {"sr": r.sr_id, "criticality": r.criticality, "status": r.status,
             "verdict": r.verdict, "run_count_ok": r.run_count_ok,
             "families": r.families_covered,
             "failing_scenarios": r.failing_scenarios,
             "indeterminate_scenarios": r.indeterminate_scenarios, "notes": r.notes}
            for r in sr_results
        ],
        "n_runs": len(outcomes),
        "n_error": sum(1 for o in outcomes if o.error is not None),
    }


def write_report(report: Dict[str, object], outcomes: Sequence[RunOutcome], out_dir: Path) -> None:
    """Write the campaign report (JSON) + a flat per-run CSV under ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "campaign_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    with (out_dir / "campaign_runs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scenario", "mode", "controller", "seed", "rep", "verdict", "error"])
        for o in outcomes:
            rs = o.run_spec
            writer.writerow([rs.scenario_id, rs.mode, rs.controller, rs.seed, rs.rep,
                             o.verdict, o.error or ""])


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """CLI for the campaign driver."""
    p = argparse.ArgumentParser(description="Phase-4 scenario validation campaign.")
    p.add_argument("--controllers", default="rl",
                   help="rl | pd | rl,pd (PD arm not wired yet — use rl).")
    p.add_argument("--seeds", default="2024",
                   help="policy seeds for the rl arm (checkpoints cobraflex_ppo_lane_<seed>_200k.zip).")
    p.add_argument("--modes", default="enforcement,monitoring")
    p.add_argument("--verdict-mode", default="enforcement")
    p.add_argument("--scenarios", default="",
                   help="comma list of scenario ids to run (default: all non-stub).")
    p.add_argument("--reps", type=int, default=None,
                   help="cap per-scenario repetitions (default: full D-29 n_runs_recommended).")
    p.add_argument("--gui", action="store_true", help="show the Gazebo GUI per run (slow).")
    p.add_argument("--rviz", action="store_true", help="show RViz per run (to spot-check spawn/odom).")
    p.add_argument("--resume", action="store_true",
                   help="skip cells whose summary.json already exists (resume a long campaign).")
    p.add_argument("--settle", type=float, default=3.0,
                   help="seconds to pause between runs for clean Gazebo teardown (default 3).")
    p.add_argument("--retries", type=int, default=2,
                   help="re-attempts for a run that produced no summary (flaky Gazebo boot).")
    p.add_argument("--stop-on-error", action="store_true",
                   help="abort the campaign on the first failed run (default: record + continue).")
    p.add_argument("--out", type=Path, default=REPO / "experiments" / "sim" / "campaign")
    p.add_argument("--no-frontier-plots", dest="frontier_plots", action="store_false",
                   help="skip auto-rendering the frontier cage-efficacy figures after the run.")
    p.set_defaults(frontier_plots=True)
    p.add_argument("--dry-run", action="store_true",
                   help="build the matrix + D-29 feasibility and stop (no Gazebo).")
    # Track-'E' camera campaign knobs (F-track defaults preserved).
    p.add_argument("--train-config", default="",
                   help="training config YAML for the eval env (empty = package "
                        "default; pass train_ppo_camera.yaml for the E-track).")
    p.add_argument("--checkpoint-template", default=DEFAULT_CHECKPOINT_TEMPLATE,
                   help="checkpoint filename template with {seed} "
                        "(E-track: cobraflex_ppo_cam_lane_{seed}_200k.zip).")
    return p.parse_args(argv)


def render_frontier_plots(out_dir: Path) -> None:
    """Best-effort: render the frontier cage-efficacy figures (`tools/plot_frontier.py`)
    after a campaign that included SC-FRONT scenarios. matplotlib may be absent on the
    headless ROS host — then print the command to render them on the figure host instead.
    Never raises: a plotting issue must not fail a completed campaign."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import plot_frontier

        figs = plot_frontier.render(out_dir)
        if figs:
            print("\nFrontier cage-efficacy figures:")
            for f in figs:
                print(f"  {f}")
    except Exception as exc:  # noqa: BLE001 - never fail the campaign on a plotting issue
        print(f"\n[frontier figures not rendered here: {type(exc).__name__}: {exc}]")
        print("  render them on a host with matplotlib via:")
        print(f"    python tools/plot_frontier.py --campaign-dir {out_dir}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Drive the campaign: plan the matrix, execute (resume-aware), aggregate, report."""
    args = _parse_args(argv)
    scenarios = load_scenarios()
    srs = load_srs()
    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    matrix = build_matrix(scenarios, controllers, seeds, modes, reps_cap=args.reps)
    only = {s.strip() for s in args.scenarios.split(",") if s.strip()}
    if only:
        matrix = [r for r in matrix if r.scenario_id in only]

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

    # Execution path (Ubuntu+Jazzy host): drive each matrix cell through Gazebo,
    # then aggregate per-run -> per-scenario -> per-SR (D-29) -> global (D-30).
    runs_root = args.out / "runs"
    # Clear any gz servers a previously-crashed campaign left orphaned, so we
    # start from a clean memory baseline (each orphan is ~2 GB).
    _reap_orphan_gazebo()
    print(f"\nExecuting {len(matrix)} run(s) -> {runs_root}\n" + "=" * 56)

    def _progress(i: int, total: int, outcome: RunOutcome) -> None:
        rs = outcome.run_spec
        tag = ("ERROR" if outcome.error else
               {True: "PASS", False: "FAIL", None: "INDET"}[outcome.verdict])
        line = f"[{i:>4}/{total}] {rs.scenario_id} {rs.mode} seed{rs.seed} rep{rs.rep:02d} -> {tag}"
        print(line + (f"  ({outcome.error})" if outcome.error else ""))

    executor: Executor = (
        lambda rs, sc, **kw: execute_run(
            rs, sc, gui=args.gui, rviz=args.rviz, resume=args.resume,
            retries=args.retries, train_config=args.train_config,
            checkpoint_template=args.checkpoint_template, **kw)
    )
    outcomes = run_matrix(
        matrix, scenarios, runs_root, executor=executor,
        continue_on_error=not args.stop_on_error, settle_s=args.settle,
        on_progress=_progress,
    )

    report = aggregate_campaign(outcomes, scenarios, srs, verdict_mode=args.verdict_mode)
    write_report(report, outcomes, args.out)

    gv = report["global"]
    print("\n" + "=" * 56)
    print(f"Campaign global verdict ({report['verdict_mode']}): {gv['verdict']}")
    print(f"  SR-CL-A: {gv['n_sr_cl_a']}  failing: {gv['blocking_sr_cl_a']}"
          f"  incomplete: {gv['incomplete_sr_cl_a']}")
    print(f"  runs: {report['n_runs']}  errors: {report['n_error']}")
    print(f"  report: {args.out / 'campaign_report.json'}")

    # If the campaign included frontier scenarios, render the cage-efficacy figures
    # (D-35 paired enforcement-vs-monitoring contrast). Best-effort — see the helper.
    if args.frontier_plots and any(r.scenario_id.startswith("SC-FRONT") for r in matrix):
        render_frontier_plots(args.out)

    return 0 if gv["verdict"] == "SATISFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
