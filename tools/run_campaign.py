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
import hashlib
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
    perturbations: Dict[str, object] = field(default_factory=dict)
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
        perturbations = data.get("perturbations", {}) or {}
        out[data["id"]] = Scenario(
            id=data["id"],
            category=data.get("category", ""),
            is_stub=data.get("status") == "stub",
            references_SR=list(data.get("references_SR", []) or []),
            pass_criterion_per_run=str(data.get("pass_criterion_per_run", "")),
            pass_criterion_per_scenario=str(data.get("pass_criterion_per_scenario", "")),
            n_runs=dict(data.get("n_runs_recommended", {}) or {}),
            track=dict(data.get("track", {}) or {}),
            perturbations=(dict(perturbations) if isinstance(perturbations, dict) else {}),
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
    arm: Optional[str] = None  # labelled policy arm (SC-PERT-03), else None


def policy_arms(scenario: Scenario) -> List[Dict[str, object]]:
    """Explicit policy arms for a pre-run fine-tune scenario, else ``[]``."""
    perturb = scenario.perturbations
    if str(perturb.get("type", "")) != "pre_run_policy_finetune":
        return []
    arms = list(perturb.get("arms", []) or [])
    if not arms or any(not isinstance(a, dict) or not str(a.get("id", "")) for a in arms):
        raise ValueError(f"{scenario.id}: invalid pre_run_policy_finetune arms")
    ids = [str(a["id"]) for a in arms]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{scenario.id}: duplicate policy-arm id")
    return arms


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
            arms = policy_arms(scen)
            if arms:
                per_arm = [int(a.get("runs_per_mode", 0)) for a in arms]
                if any(count <= 0 for count in per_arm) or sum(per_arm) != int(
                    scen.n_runs.get(mode, 0)
                ):
                    raise ValueError(
                        f"{sid}: arm runs_per_mode must be positive and sum to "
                        f"n_runs_recommended.{mode}"
                    )
                if reps_cap is not None:
                    # A cap applies symmetrically, preserving the paired design.
                    per_arm = [min(count, reps_cap) for count in per_arm]
            for controller in controllers:
                if arms and controller != "rl":
                    raise ValueError(f"{sid}: policy fine-tune arms require controller=rl")
                seed_axis: Sequence[Optional[int]] = seeds if controller == "rl" else [None]
                for seed in seed_axis:
                    if arms:
                        for arm, count in zip(arms, per_arm):
                            for rep in range(count):
                                runs.append(RunSpec(
                                    sid, mode, controller, seed, rep, str(arm["id"])
                                ))
                    else:
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


# SRs verified by a dedicated out-of-band metric analysis rather than the
# per-scenario pass/fail aggregation. SR-006 (C-06 committed-steer smoothness)
# lists ``ALL`` scenarios and would otherwise inherit every unrelated scenario
# fail; D-39 scores it via tools/sr006_smoothness.py. Marking it here stops the
# campaign report reading a spurious ``failed`` (D-39 follow-up; CL-B, global
# unaffected — the verdict of record is docs/07 note ¹).
OUT_OF_BAND_SRS = frozenset({"SR-006"})


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

    SRs in ``OUT_OF_BAND_SRS`` (SR-006, D-39) are scored by a dedicated metric
    tool, not this per-scenario aggregation, so they short-circuit to a
    ``scored_out_of_band`` status (verdict None — neither pass nor fail) instead
    of inheriting unrelated per-scenario fails.
    """
    if sr_id in OUT_OF_BAND_SRS:
        return SRResult(
            sr_id, criticality, "scored_out_of_band", run_count_ok=True,
            families_covered=[], failing_scenarios=[], indeterminate_scenarios=[],
            notes=("scored out-of-band on its own metric (tools/sr006_smoothness.py, "
                   "D-39); not aggregated from per-scenario verdicts (CL-B)"),
        )
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


def resolve_config_path(name: str) -> Path:
    """Absolute path for a scenario ``track`` config filename (centerline /
    road_centerline), resolved against the cobraflex_rl share/config (what the
    launch default uses) with a source-tree fallback. Mirrors resolve_world_path
    so a complex_b campaign cell fails at plan time, not mid-Gazebo, if a
    centerline YAML is missing."""
    candidate = Path(name)
    if candidate.is_absolute() and candidate.is_file():
        return candidate
    try:  # pragma: no cover - needs a sourced ROS2 env
        from ament_index_python.packages import get_package_share_directory

        share = Path(get_package_share_directory("cobraflex_rl")) / "config" / name
        if share.is_file():
            return share
    except Exception:
        pass
    src = REPO / "src" / "cobraflex_rl" / "config" / name
    if src.is_file():
        return src
    raise FileNotFoundError(f"scenario centerline config not found: {name}")


def run_id_for(run_spec: RunSpec, protocol_hash: str = "") -> str:
    """Deterministic, collision-free run id for a matrix cell, so the executor
    can locate the run dir it just produced and the campaign tree is traceable."""
    who = "pd" if run_spec.controller == "pd" else f"seed{run_spec.seed}"
    sid = run_spec.scenario_id.replace("SC-", "").replace("-", "").lower()
    arm = f"_{run_spec.arm}" if run_spec.arm else ""
    protocol = f"_proto{protocol_hash[:12]}" if run_spec.arm and protocol_hash else ""
    return (
        f"camp_{sid}_{run_spec.controller}_{who}_{run_spec.mode}{arm}"
        f"{protocol}_rep{run_spec.rep:02d}"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _config_requires_d43_preflight(path: Path) -> bool:
    """Return whether an opted-in posterior config requires the D-43 gate.

    Historical F/GE4 configs have no ``campaign_contract`` and deliberately
    stay outside this posterior guard.  A malformed opted-in contract is an
    error rather than being treated as ``False``.
    """

    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"training config is not a YAML mapping: {path}")
    contract = data.get("campaign_contract")
    if contract is None:
        return False
    if not isinstance(contract, dict):
        raise ValueError(f"campaign_contract is not a mapping: {path}")
    required = contract.get("d43_preflight_required")
    if required is not True:
        raise ValueError(
            "an opted-in campaign_contract must set "
            f"d43_preflight_required=true: {path}"
        )
    return True


def validate_d43_preflight_report(
    report_path: Path,
    expected_targets: Sequence[Dict[str, str]],
) -> Dict[str, object]:
    """Validate a fail-closed D-43 authorisation for concrete checkpoints.

    A report may contain a reference matrix with unrelated blocked policies;
    authorisation is therefore input-specific.  Every requested checkpoint +
    training-config pair must have its own valid ``SC-NOM-01`` enforcement
    input marked ``PASS``.  An aggregate ``INVALID`` report can never authorise
    execution, even if one embedded input happens to pass.
    """

    report_path = Path(report_path).resolve()
    if not report_path.is_file():
        raise ValueError(f"D-43 preflight report not found: {report_path}")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"D-43 preflight report is not valid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise ValueError("D-43 preflight report must be a JSON object")
    if report.get("schema_version") != "d43-preflight/v1":
        raise ValueError(
            "D-43 preflight schema must be 'd43-preflight/v1', got "
            f"{report.get('schema_version')!r}"
        )
    if report.get("verdict") == "INVALID" or report.get("invalid_reasons"):
        raise ValueError(
            "D-43 preflight report is INVALID and cannot authorise a campaign"
        )
    inputs = report.get("inputs")
    if not isinstance(inputs, list):
        raise ValueError("D-43 preflight report has no inputs[] list")

    matches: List[Dict[str, str]] = []
    for target in expected_targets:
        checkpoint_hash = str(target["checkpoint_sha256"]).lower()
        config_hash = str(target["train_config_sha256"]).lower()
        match = None
        for item in inputs:
            if not isinstance(item, dict) or item.get("verdict") != "PASS":
                continue
            provenance = item.get("provenance")
            if not isinstance(provenance, dict) or provenance.get("valid") is not True:
                continue
            if (
                str(provenance.get("policy_checkpoint_hash", "")).lower()
                != checkpoint_hash
                or str(provenance.get("train_config_hash", "")).lower()
                != config_hash
                or provenance.get("scenario_id") != "SC-NOM-01"
                or provenance.get("mode") != "enforcement"
                or provenance.get("status") != "completed"
            ):
                continue
            match = {
                "label": str(target.get("label", "policy")),
                "checkpoint_sha256": checkpoint_hash,
                "train_config_sha256": config_hash,
                "input_path": str(item.get("path", "")),
                "input_csv_sha256": str(item.get("sha256", "")),
                "input_metadata_sha256": str(
                    provenance.get("metadata_sha256", "")
                ),
            }
            break
        if match is None:
            raise ValueError(
                "D-43 preflight has no provenance-valid PASS for "
                f"{target.get('label', 'policy')} checkpoint {checkpoint_hash} "
                f"with train-config {config_hash}"
            )
        matches.append(match)

    return {
        "schema_version": report["schema_version"],
        "report": str(report_path),
        "report_sha256": _file_sha256(report_path),
        "report_verdict": str(report.get("verdict")),
        "status": "PASS_FOR_SELECTED_CHECKPOINTS",
        "matches": matches,
    }


def _read_summary(output_root: Path, run_id: str) -> Optional[Dict[str, object]]:
    """Load a run's summary.json (None when missing/unreadable)."""
    summary_path = Path(output_root) / run_id / "summary.json"
    if summary_path.is_file():
        with summary_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    return None


def _live_training_pids() -> List[str]:
    """PIDs of any `train_ppo` process currently running on this host.

    Exists because `_reap_orphan_gazebo` below cannot tell a training's Gazebo
    from an orphan: both match `gz sim .* cobraflex/share/cobraflex/worlds`, and
    the reaper sends SIGKILL. On 21.08.2026 starting a single-scenario campaign
    beside a running 2.5M-step training killed the training's simulator at
    startup — `gazebo` exit -9, `train_ppo` exit -2 — and cost 20k steps back to
    the last checkpoint.

    The reaper's own docstring states its assumption ("after a run returns there
    must be no gz server we still need"); it is sound, and holds whenever a
    campaign owns the machine. This guard makes the assumption checkable instead
    of leaving it to the operator's memory.
    """
    import subprocess

    # Verified by `comm`, never by cmdline alone. `pgrep -f` also matches any
    # shell whose command-line *text* contains the pattern — the wrapper that
    # launched the trainer, a monitor watching for it, or the checking command
    # itself. `reap_sim.sh` documents this, and the 29.07 concurrency incident
    # was misdiagnosed for the same reason ("the matching process was the
    # checker itself, because its own cmdline carried the search pattern").
    # A first cut of this guard reproduced the bug and blocked three campaign
    # runs with no training running at all.
    proc = subprocess.run(
        ["pgrep", "-f", r"lib/cobraflex_rl/train_ppo"],
        capture_output=True, text=True, check=False,
    )
    live: List[str] = []
    for pid in proc.stdout.split():
        if not pid.strip():
            continue
        comm = subprocess.run(
            ["ps", "-o", "comm=", "-p", pid],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        # ps truncates comm to 15 chars; the trainer reports `train_ppo`, and a
        # bare interpreter invocation would report `python3`.
        if comm.startswith("train_ppo") or comm.startswith("python3"):
            live.append(pid)
    return live


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
    # The GUI client (`gz sim -g`) carries no world path, so the server pattern
    # above misses it. With --gui it ignores the launch's on-exit Shutdown the
    # same way the server does and lingers, so a fresh window opens every run and
    # they pile up (multiple Gazebo instances). The server cmdline is `gz sim -r
    # -s …`, never `-g`, so this is GUI-only — a campaign owns the only gz GUI.
    subprocess.run(["pkill", "-9", "-f", r"gz sim -g"], check=False)
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
    model_paths_by_arm: Optional[Dict[str, Path]] = None,
    train_configs_by_arm: Optional[Dict[str, Path]] = None,
    protocol_manifest: Optional[Path] = None,
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

    if run_spec.arm and not protocol_manifest:
        raise ValueError(f"{scenario.id}: a completed protocol manifest is required")
    protocol_hash = _file_sha256(Path(protocol_manifest)) if protocol_manifest else ""
    run_id = run_id_for(run_spec, protocol_hash=protocol_hash)
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
    if run_spec.arm:
        if not model_paths_by_arm or run_spec.arm not in model_paths_by_arm:
            raise ValueError(f"{scenario.id}: no checkpoint registered for arm {run_spec.arm!r}")
        checkpoint = Path(model_paths_by_arm[run_spec.arm])
        if train_configs_by_arm and run_spec.arm in train_configs_by_arm:
            train_config = str(train_configs_by_arm[run_spec.arm])
    else:
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
    if run_spec.arm:
        cmd.extend([
            f"criterion_arm:={run_spec.arm}",
            f"protocol_manifest:={Path(protocol_manifest)}",
        ])
    # World-variant scenarios (SC-PERT-09/10: worn / wet oval textures) name a
    # non-default world in their track block; everything else keeps the launch
    # default so the F-track cells are byte-identical to the pre-E behaviour.
    world_name = str(scenario.track.get("world") or "").strip()
    if world_name and world_name != "lane_following_oval.world":
        cmd.append(f"world:={resolve_world_path(world_name)}")
    # Track geometry (complex_b camera campaign): pass the lane centerline, the
    # road-centre centerline (off-road geometry on self-approaching circuits,
    # docs/11 §3.5) and the SDF world_name for the gz teleport services. Each is
    # appended only when the scenario's track block sets it, so oval cells stay
    # byte-identical (empty -> eval_policy's oval defaults).
    centerline = str(scenario.track.get("centerline") or "").strip()
    if centerline and centerline != "oval_right_lane_centerline.yaml":
        cmd.append(f"centerline:={resolve_config_path(centerline)}")
    road_centerline = str(scenario.track.get("road_centerline") or "").strip()
    if road_centerline:
        cmd.append(f"road_centerline:={resolve_config_path(road_centerline)}")
    sdf_world_name = str(scenario.track.get("world_name") or "").strip()
    if sdf_world_name:
        cmd.append(f"world_name:={sdf_world_name}")
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
    # Group per (scenario, mode, arm). Ordinary scenarios use arm=None. Keeping
    # SC-PERT-03 arms separate is essential: pooling 80% stall-variant passes
    # with 100% released passes would otherwise produce a misleading 90% pass.
    groups: Dict[tuple, List[RunOutcome]] = {}
    for o in outcomes:
        groups.setdefault(
            (o.run_spec.scenario_id, o.run_spec.mode, o.run_spec.arm), []
        ).append(o)

    scenario_results: Dict[str, ScenarioResult] = {}   # verdict_mode results, by scenario
    runs_per_scenario: Dict[str, int] = {}
    per_scenario_report: List[Dict[str, object]] = []
    grouped_results: Dict[tuple, List[ScenarioResult]] = {}
    for (sid, mode, arm), group in sorted(
        groups.items(), key=lambda item: tuple("" if x is None else str(x) for x in item[0])
    ):
        scen = scenarios.get(sid)
        if scen is None:
            continue
        verdicts = [o.verdict for o in group]  # three-valued: True | False | None
        result = aggregate_scenario(scen, mode, verdicts)
        n_error = sum(1 for o in group if o.error is not None)
        # D-45 made a safe controlled stop a passing outcome on the adverse
        # criteria, so a bare n_pass conflates two behaviours; n_pass_emergency
        # counts the passes where the cage flagged emergency (enforcement: the
        # SR-013 controlled stop) vs those that overcame the scenario without it.
        n_pass_emergency = sum(
            1 for o in group
            if o.verdict is True and bool(
                ((o.summary.get("campaign") or {}).get("values") or {}).get("emergency"))
        )
        per_scenario_report.append({
            "scenario": sid, "mode": mode, "arm": arm, "n_runs": result.n_runs,
            "n_pass": result.n_pass, "n_pass_emergency": n_pass_emergency,
            "n_fail": result.n_fail,
            "n_indeterminate": result.n_indeterminate,
            "fraction_pass": (round(result.fraction_pass, 4)
                              if result.fraction_pass is not None else None),
            "verdict": result.verdict, "n_error": n_error,
        })
        grouped_results.setdefault((sid, mode), []).append(result)

    # Conjoin arm-level verdicts, while ordinary one-arm(None) scenarios pass
    # through unchanged. Counts remain visible as totals for D-29 sufficiency.
    for (sid, mode), results in grouped_results.items():
        if mode != verdict_mode:
            continue
        verdicts = [r.verdict for r in results]
        combined_verdict: Optional[bool]
        if any(v is False for v in verdicts):
            combined_verdict = False
        elif any(v is None for v in verdicts):
            combined_verdict = None
        else:
            combined_verdict = True
        combined = ScenarioResult(
            scenario_id=sid,
            mode=mode,
            n_runs=sum(r.n_runs for r in results),
            n_pass=sum(r.n_pass for r in results),
            n_fail=sum(r.n_fail for r in results),
            n_indeterminate=sum(r.n_indeterminate for r in results),
            verdict=combined_verdict,
        )
        scenario_results[sid] = combined
        runs_per_scenario[sid] = combined.n_runs

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
        writer.writerow(["scenario", "mode", "arm", "controller", "seed", "rep",
                         "verdict", "emergency", "error"])
        for o in outcomes:
            rs = o.run_spec
            # How a pass happened (D-45): verdict=True + emergency=True is the
            # cage's controlled stop; verdict=True + emergency=False overcame the
            # scenario. Empty when the run has no metric record (e.g. errored).
            vals = (o.summary.get("campaign") or {}).get("values") or {}
            writer.writerow([rs.scenario_id, rs.mode, rs.arm or "", rs.controller, rs.seed, rs.rep,
                             o.verdict, vals.get("emergency", ""), o.error or ""])


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
    p.add_argument("--force-beside-training", action="store_true",
                   help="run even though a train_ppo process is alive. The "
                        "orphan-Gazebo reaper cannot distinguish a training's "
                        "simulator from an orphan and will SIGKILL it.")
    p.add_argument("--dry-run", action="store_true",
                   help="build the matrix + D-29 feasibility and stop (no Gazebo).")
    # Track-'E' camera campaign knobs (F-track defaults preserved).
    p.add_argument("--train-config", default="",
                   help="training config YAML for the eval env (empty = package "
                        "default; pass train_ppo_camera.yaml for the E-track).")
    p.add_argument("--checkpoint-template", default=DEFAULT_CHECKPOINT_TEMPLATE,
                   help="checkpoint filename template with {seed} "
                        "(E-track: cobraflex_ppo_cam_lane_{seed}_200k.zip).")
    p.add_argument("--model-path", default="",
                   help="explicit checkpoint .zip path (overrides --checkpoint-template / "
                        "the seed template; e.g. the gitignored complex_b 297k peak under "
                        "experiments/sim/training/.../checkpoints_peak/). Single-policy campaigns.")
    p.add_argument("--scenario-dir", default="",
                   help="scenario library root (dir of <category>/*.yaml). Empty = the "
                        "oval `scenarios/`; pass `scenarios_complex_b` for the camera campaign.")
    p.add_argument(
        "--two-arm-manifest", type=Path, default=None,
        help="completed protocol_manifest.json from sc_pert_03_protocol.py; "
             "required when executing SC-PERT-03",
    )
    p.add_argument(
        "--d43-preflight-report", type=Path, default=None,
        help=(
            "d43-preflight/v1 JSON produced by tools/d43_preflight.py. "
            "Required by opted-in posterior campaign_contract configs; the "
            "report must contain a provenance-valid PASS for the exact "
            "checkpoint and train-config hashes selected here."
        ),
    )
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
    scenarios = load_scenarios(Path(args.scenario_dir) if args.scenario_dir else SCENARIO_DIR)
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

    arm_runs = [r for r in matrix if r.arm]
    protocol_manifest_path: Optional[Path] = None
    protocol_data: Optional[Dict[str, object]] = None
    arm_model_paths: Dict[str, Path] = {}
    arm_train_configs: Dict[str, Path] = {}
    if arm_runs:
        if args.two_arm_manifest is None:
            print("\nERROR: SC-PERT-03 execution requires --two-arm-manifest from\n"
                  "  python tools/sc_pert_03_protocol.py prepare ...")
            return 2
        import sc_pert_03_protocol as two_arm

        protocol_manifest_path = Path(args.two_arm_manifest).resolve()
        try:
            protocol_data = two_arm.validate_manifest(
                protocol_manifest_path, require_completed=True
            )
        except two_arm.ProtocolError as exc:
            print(f"\nERROR: invalid two-arm manifest: {exc}")
            return 2
        arm_model_paths = two_arm.model_paths_by_arm(protocol_data)
        arm_train_configs = {
            "released": Path(protocol_data["parent"]["train_config"]),
            "stall_variant": Path(protocol_data["derived"]["train_config"]),
        }
        manifest_scenario = Path(protocol_data["scenario"]["path"]).resolve()
        selected_arm_scenarios = {
            scenarios[r.scenario_id].path.resolve()
            for r in arm_runs if scenarios[r.scenario_id].path is not None
        }
        if selected_arm_scenarios != {manifest_scenario}:
            print("\nERROR: manifest scenario does not match the selected scenario library")
            return 2
        if {r.seed for r in arm_runs} != {int(protocol_data["seed"])}:
            print("\nERROR: SC-PERT-03 campaign seed must match the manifest parent seed")
            return 2
        for run in arm_runs:
            if scenarios[run.scenario_id].pass_criterion_per_run != protocol_data["criterion"]:
                print("\nERROR: SC-PERT-03 criterion differs from the completed manifest")
                return 2

    # Fail fast before launching dozens of cells: an empty/bad --train-config makes
    # every RL launch reject a malformed `train_config:=` arg (one cryptic error per
    # cell). The camera eval requires it, so catch it once here.
    plain_rl_runs = [r for r in matrix if r.controller == "rl" and not r.arm]
    if plain_rl_runs:
        if not str(args.train_config).strip():
            print("\nERROR: --train-config is empty. Pass the camera eval config, e.g.\n"
                  "  source /opt/ros/jazzy/setup.bash\n"
                  "  --train-config $(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config/train_ppo_camera.yaml")
            return 2
        if not Path(args.train_config).is_file():
            print(f"\nERROR: --train-config file not found: {args.train_config!r}")
            return 2

    # Posterior 2-D configs opt into a fail-closed D-43 preflight.  Bind the
    # authorisation to the exact selected checkpoint *and* train-config hashes;
    # this check runs before orphan reaping or any Gazebo process is started.
    d43_targets: List[Dict[str, str]] = []
    try:
        if plain_rl_runs and _config_requires_d43_preflight(Path(args.train_config)):
            plain_config = Path(args.train_config).resolve()
            plain_checkpoints = {
                (
                    Path(args.model_path).resolve()
                    if args.model_path
                    else checkpoint_for_seed(run.seed, args.checkpoint_template).resolve()
                )
                for run in plain_rl_runs
            }
            for checkpoint in sorted(plain_checkpoints, key=str):
                if not checkpoint.is_file():
                    raise ValueError(
                        f"checkpoint selected for D-43 preflight not found: {checkpoint}"
                    )
                d43_targets.append({
                    "label": f"campaign policy {checkpoint.name}",
                    "checkpoint_sha256": _file_sha256(checkpoint),
                    "train_config_sha256": _file_sha256(plain_config),
                })

        if arm_runs and protocol_data is not None:
            parent_config = Path(protocol_data["parent"]["train_config"]).resolve()
            if _config_requires_d43_preflight(parent_config):
                d43_targets.append({
                    "label": "SC-PERT-03 released parent",
                    "checkpoint_sha256": str(
                        protocol_data["parent"]["checkpoint_sha256"]
                    ),
                    "train_config_sha256": str(
                        protocol_data["parent"]["train_config_sha256"]
                    ),
                })

        d43_authorisation: Optional[Dict[str, object]] = None
        if d43_targets:
            if args.d43_preflight_report is None:
                raise ValueError(
                    "selected campaign contract requires --d43-preflight-report"
                )
            d43_authorisation = validate_d43_preflight_report(
                args.d43_preflight_report, d43_targets
            )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"\nERROR: D-43 preflight blocked campaign execution: {exc}")
        return 2

    # Execution path (Ubuntu+Jazzy host): drive each matrix cell through Gazebo,
    # then aggregate per-run -> per-scenario -> per-SR (D-29) -> global (D-30).
    runs_root = args.out / "runs"
    # Clear any gz servers a previously-crashed campaign left orphaned, so we
    # start from a clean memory baseline (each orphan is ~2 GB).
    if not args.force_beside_training:
        training = _live_training_pids()
        if training:
            print(
                "\nERROR: a training process is running on this host (pid(s) "
                + ", ".join(training) + ").\n"
                "This campaign reaps orphaned Gazebo servers with "
                "`pkill -9 -f 'gz sim.*cobraflex/share/cobraflex/worlds'`, which "
                "matches a TRAINING's simulator as well as an orphan's, and would "
                "kill it.\n"
                "Wait for the training to finish, or pass --force-beside-training "
                "if you have verified it is safe."
            )
            return 2
    _reap_orphan_gazebo()
    print(f"\nExecuting {len(matrix)} run(s) -> {runs_root}\n" + "=" * 56)

    def _progress(i: int, total: int, outcome: RunOutcome) -> None:
        rs = outcome.run_spec
        tag = ("ERROR" if outcome.error else
               {True: "PASS", False: "FAIL", None: "INDET"}[outcome.verdict])
        arm = f" {rs.arm}" if rs.arm else ""
        line = f"[{i:>4}/{total}] {rs.scenario_id} {rs.mode}{arm} seed{rs.seed} rep{rs.rep:02d} -> {tag}"
        print(line + (f"  ({outcome.error})" if outcome.error else ""))

    model_path_override = Path(args.model_path) if args.model_path else None
    executor: Executor = (
        lambda rs, sc, **kw: execute_run(
            rs, sc, gui=args.gui, rviz=args.rviz, resume=args.resume,
            retries=args.retries, train_config=args.train_config,
            checkpoint_template=args.checkpoint_template,
            model_path=model_path_override,
            model_paths_by_arm=arm_model_paths,
            train_configs_by_arm=arm_train_configs,
            protocol_manifest=protocol_manifest_path,
            **kw)
    )
    outcomes = run_matrix(
        matrix, scenarios, runs_root, executor=executor,
        continue_on_error=not args.stop_on_error, settle_s=args.settle,
        on_progress=_progress,
    )

    report = aggregate_campaign(outcomes, scenarios, srs, verdict_mode=args.verdict_mode)
    if protocol_data is not None and protocol_manifest_path is not None:
        import sc_pert_03_protocol as two_arm
        report["two_arm_protocol"] = {
            "manifest": str(protocol_manifest_path),
            "manifest_sha256": two_arm.sha256_file(protocol_manifest_path),
            "criterion": protocol_data["criterion"],
            "lambda_stall": protocol_data["lambda_stall"],
            "parent_checkpoint_sha256": protocol_data["parent"]["checkpoint_sha256"],
            "derived_checkpoint_sha256": protocol_data["derived"]["checkpoint_sha256"],
            "parent_train_config_sha256": protocol_data["parent"]["train_config_sha256"],
            "derived_train_config_sha256": protocol_data["derived"]["train_config_sha256"],
        }
    if d43_authorisation is not None:
        report["d43_preflight"] = d43_authorisation
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
