#!/usr/bin/env python3
"""
rescore_recovery_clause — re-score SC-EDGE-01's ``time_to_recovery_heading``
clause under the corrected v2 metric (D-68), offline, without touching a single
campaign artefact.

Why this exists. The v1 metric measured recovery against a **fixed** 0.05 rad
(2.86°) band calibrated on the F-track PD controller on the oval. Heading error
ripples about zero with a run- and controller-dependent amplitude, so requiring a
*sustained* 0.5 s window below a fixed band tests ripple amplitude rather than
recovery — demonstrably: under v1, all 50 **unperturbed** SC-NOM-02 oval runs
"never recover" (median 12.2 s). v2 references the band to each run's own
steady-state ripple, floored at the v1 bar and capped at SR-011's σ_θ_max = 5°
(``scenario_metrics.heading_recovery_band_rad``).

What it reports, per campaign:
  * a **fidelity check** — recomputing v1 from the persisted ``cage_status.csv``
    must reproduce the value stored in each run's ``summary.json`` exactly;
    a mismatch invalidates everything downstream and is reported as such;
  * the SC-EDGE-01 clause under v1 vs v2 (per-run times, pass counts, and the
    per-scenario verdict under the scenario's *own* ``pass_criterion_per_scenario``,
    read from its YAML so this tool cannot disagree with the runner);
  * the **validity check** that motivates the change: the same clause applied to
    scenarios with no heading perturbation at all (SC-NOM-01/02), where any
    "never recovered" is by construction a false positive.

The campaign records are immutable evidence and are **not** rewritten: historical
verdicts stay as they were scored (D-47 precedent). This tool produces the
side-by-side so the change can be judged, not applied retroactively.

Usage:
  python tools/rescore_recovery_clause.py                       # all four campaigns
  python tools/rescore_recovery_clause.py --campaign-dirs a,b --json out.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src" / "cobraflex_rl"))

from cobraflex_rl.scenario_metrics import (  # noqa: E402
    heading_recovery_band_rad,
    time_to_recovery_heading,
)

DEFAULT_CAMPAIGNS = [
    "experiments/sim/campaign",             # F4, state observations, oval
    "experiments/sim/campaign_e_v2",        # GE4-V2, 1-D camera (verdict of record)
    "experiments/sim/campaign_2d_margin022",  # posterior 2-D, weak policy
    "experiments/sim/campaign_2d_ppo550k",  # posterior 2-D, competent policy
]
CLAUSE_BOUND_S = 2.0
# Scenario-level verdict rule: read from the scenario YAML (SC-EDGE-01 uses
# `fraction_pass >= 0.90`) rather than hard-coded, so this tool cannot disagree
# with the runner about what "the scenario passed" means.
SCENARIO_LIBRARIES = ["scenarios_complex_b", "scenarios"]
DEFAULT_SCENARIO_CRITERION = "fraction_pass >= 0.90"
# Scenarios with no heading perturbation: any "never recovered" here is a false
# positive of the metric, which is the evidence that motivates v2.
VALIDITY_SCENARIOS = ["nom01", "nom02"]


def _runs(campaign_dir: Path, scenario_tag: str, mode: str) -> List[Path]:
    return sorted(campaign_dir.glob(f"runs/camp_{scenario_tag}_*_{mode}_*"))


def _scenario_criterion(tag: str, library_hint: str) -> str:
    """The scenario's own ``pass_criterion_per_scenario``, read from whichever
    library defines it (the camera campaigns run `scenarios_complex_b`, F4 runs
    `scenarios`; SC-EDGE-01 carries `fraction_pass >= 0.90` in both)."""
    import yaml  # local import: the tool is otherwise dependency-free

    family = {"nom": "nominal", "edg": "edge", "per": "perturbed", "fro": "frontier"}
    stem = f"sc_{tag[:-2]}_{tag[-2:]}.yaml"
    libs = [library_hint] + [lib for lib in SCENARIO_LIBRARIES if lib != library_hint]
    for lib in libs:
        path = REPO / lib / family.get(tag[:3], "edge") / stem
        if path.is_file():
            spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            criterion = spec.get("pass_criterion_per_scenario")
            if criterion:
                return str(criterion)
    return DEFAULT_SCENARIO_CRITERION


def _trace(run_dir: Path) -> Optional[List[Dict[str, float]]]:
    path = run_dir / "cage_status.csv"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        return [{"epsi": float(row["epsi"])} for row in csv.DictReader(handle)]


def _stored_lhs(run_dir: Path) -> Optional[float]:
    path = run_dir / "summary.json"
    if not path.is_file():
        return None
    campaign = (json.loads(path.read_text(encoding="utf-8")).get("campaign") or {})
    for clause in campaign.get("clauses", []):
        if "recovery" in clause.get("clause", ""):
            return clause.get("lhs")
    return None


def _summarise(times: List[float]) -> Dict[str, object]:
    finite = [t for t in times if math.isfinite(t)]
    return {
        "n": len(times),
        "min": round(min(times), 2) if finite else None,
        "median": round(median(finite), 2) if finite else None,
        "max": (round(max(finite), 2) if len(finite) == len(times) else "inf"),
        "n_over_bound": sum(1 for t in times if not (t < CLAUSE_BOUND_S)),
    }


def scenario_block(campaign_dir: Path, tag: str, mode: str = "enforcement",
                   library_hint: str = "scenarios_complex_b") -> Optional[Dict]:
    v1: List[float] = []
    v2: List[float] = []
    bands: List[float] = []
    mismatches = 0
    checked = 0
    for run_dir in _runs(campaign_dir, tag, mode):
        records = _trace(run_dir)
        if not records:
            continue
        t1 = time_to_recovery_heading(records, control_dt=0.1, ripple_reference=False)
        t2 = time_to_recovery_heading(records, control_dt=0.1)
        stored = _stored_lhs(run_dir)
        if stored is not None and isinstance(stored, (int, float)) and math.isfinite(stored):
            checked += 1
            mismatches += 0 if abs(float(stored) - t1) < 1e-6 else 1
        v1.append(t1)
        v2.append(t2)
        bands.append(heading_recovery_band_rad(records))
    if not v1:
        return None
    from cobraflex_rl.criterion_eval import evaluate  # noqa: E402

    criterion = _scenario_criterion(tag, library_hint)
    block = {
        "scenario": tag,
        "mode": mode,
        "pass_criterion_per_scenario": criterion,
        "fidelity_v1_vs_stored": {"checked": checked, "mismatches": mismatches},
        "band_v2_mean_deg": round(math.degrees(sum(bands) / len(bands)), 2),
        "v1": _summarise(v1),
        "v2": _summarise(v2),
    }
    for key in ("v1", "v2"):
        n = block[key]["n"]
        n_pass = n - block[key]["n_over_bound"]
        fraction = n_pass / n if n else None
        block[key]["fraction_pass"] = round(fraction, 4) if fraction is not None else None
        block[key]["scenario_verdict"] = (
            bool(evaluate(criterion, {"fraction_pass": fraction})["passed"])
            if fraction is not None else None
        )
    return block


def main() -> None:
    ap = argparse.ArgumentParser(description="Re-score SC-EDGE-01's recovery clause (D-68).")
    ap.add_argument("--campaign-dirs", type=str, default=",".join(DEFAULT_CAMPAIGNS))
    ap.add_argument("--json", type=Path, default=None, help="write the full report here")
    args = ap.parse_args()

    report = {
        "metric": "time_to_recovery_heading",
        "clause": f"time_to_recovery_heading < {CLAUSE_BOUND_S}",
        "v1": "fixed band 0.05 rad (2.86 deg), sustained 0.5 s",
        "v2": "band = clamp(p95 |epsi| over the run's last 50%, floor 0.05 rad, cap 0.0873 rad = SR-011 sigma_theta_max)",
        "campaigns": [],
    }
    print(f"clause: {report['clause']}   scenario verdict: each scenario's own pass_criterion_per_scenario\n")
    header = f"{'campaign':<24}{'scen':<8}{'band v2':>9}{'v1 min/med/max':>20}{'v2 min/med/max':>20}{'v1 pass':>10}{'v2 pass':>12}"
    print(header)
    print("-" * len(header))
    for raw in args.campaign_dirs.split(","):
        raw = raw.strip()
        if not raw:
            continue
        campaign_dir = (REPO / raw) if not Path(raw).is_absolute() else Path(raw)
        entry = {"campaign": campaign_dir.name, "scenarios": []}
        library = "scenarios" if campaign_dir.name == "campaign" else "scenarios_complex_b"
        for tag in ["edge01"] + VALIDITY_SCENARIOS:
            block = scenario_block(campaign_dir, tag, library_hint=library)
            if block is None:
                continue
            entry["scenarios"].append(block)
            fmt = lambda b: f"{b['min']}/{b['median']}/{b['max']}"  # noqa: E731
            print(f"{campaign_dir.name:<24}{tag:<8}{block['band_v2_mean_deg']:>8}°"
                  f"{fmt(block['v1']):>20}{fmt(block['v2']):>20}"
                  f"{block['v1']['n'] - block['v1']['n_over_bound']:>6}/{block['v1']['n']:<2}"
                  f"{'PASS' if block['v1']['scenario_verdict'] else 'fail':>5}"
                  f"{block['v2']['n'] - block['v2']['n_over_bound']:>5}/{block['v2']['n']:<2}"
                  f"{'PASS' if block['v2']['scenario_verdict'] else 'fail':>5}")
            if block["fidelity_v1_vs_stored"]["mismatches"]:
                print(f"    !! FIDELITY FAILURE: {block['fidelity_v1_vs_stored']} — "
                      "recomputed v1 does not reproduce the stored clause value")
        report["campaigns"].append(entry)

    total = sum(s["fidelity_v1_vs_stored"]["checked"] for e in report["campaigns"] for s in e["scenarios"])
    bad = sum(s["fidelity_v1_vs_stored"]["mismatches"] for e in report["campaigns"] for s in e["scenarios"])
    print(f"\nfidelity: {total - bad}/{total} runs reproduce their stored v1 value exactly")
    print("note: SC-NOM-01/02 carry no heading perturbation — any 'never recovered' there is a\n"
          "      false positive of the metric, and is what motivates the v2 band (D-68).")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
