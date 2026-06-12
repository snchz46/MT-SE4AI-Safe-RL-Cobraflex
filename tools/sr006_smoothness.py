#!/usr/bin/env python3
"""
sr006_smoothness — dedicated verification analysis for SR-006 (actuator
smoothness, C-06 rate limiter), computed from the committed-steer trace logged in
each run's ``cage_status.csv``.

Why a dedicated tool (cf. D-39, precedent D-35 / ``frontier_contrast.py``).
SR-006 maps to *all* scenarios because C-06 is "always active"; the per-scenario
``fraction_pass`` aggregation (D-30) therefore made SR-006 inherit *any* failing
scenario — e.g. SC-PERT-01's σ=0.05 emergency trips, which are unrelated to
actuator smoothness. SR-006 is a per-step, per-run *metric* property, not a
scenario pass/fail, so it is verified here directly and reported outside the D-30
per-scenario aggregation (exactly as the frontier M-S5 contrast is, D-35).

What it measures. The cage chain is C-06 → C-04 → C-02 → C-03 → C-01 → C-05: C-06
bounds the *raw* action's per-cycle rate first, then a downstream safety rule
(C-01 lane / C-02 heading / C-03 TTLC / C-05 emergency) may command a larger
correction to avert an imminent hazard — by design, smoothness yields to safety.
So the rate limiter governs only the steps where no safety-override rule fired;
SR-006 holds iff, on those steps, the committed-steer per-cycle delta stays within
``delta_max_steer`` (cage.yaml ``c06_rate_limiter.delta_max_steering_per_cycle``,
0.15). Steps with a downstream override (or an emergency) are reported separately
as the regime where a larger correction is the *correct* behaviour.

Pure-Python: reuses ``cobraflex_rl.campaign_metrics.compute_run_metrics`` and reads
only the committed ``cage_status.csv`` logs — no Gazebo, no re-run.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
_PKG = REPO_ROOT / "src" / "cobraflex_rl"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from cobraflex_rl.campaign_metrics import compute_run_metrics  # noqa: E402

DEFAULT_CAMPAIGN = REPO_ROOT / "experiments" / "sim" / "campaign" / "runs"
DELTA_MAX_STEER = 0.15        # SR-006 / C-06 per-cycle steering bound (cage.yaml)
PASS_FRACTION = 0.95          # per-scenario-style threshold for the SR verdict


def _records_from_csv(path: Path) -> List[Dict[str, object]]:
    """Parse a ``cage_status.csv`` into the record shape ``compute_run_metrics``
    expects (``interventions`` as a list of rule ids; ``emergency`` as bool)."""
    records: List[Dict[str, object]] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            iv_raw = (row.get("interventions") or "").strip()
            interventions = [r for r in iv_raw.split(";") if r] if iv_raw else []
            em = (row.get("emergency") or "0").strip()
            records.append({
                "ey": float(row["ey"]), "epsi": float(row["epsi"]),
                "speed": float(row.get("speed", 0.0) or 0.0),
                "raw_steer": float(row.get("raw_steer", 0.0) or 0.0),
                "safe_steer": float(row.get("safe_steer", 0.0) or 0.0),
                "steer_correction": float(row.get("steer_correction", 0.0) or 0.0),
                "interventions": interventions,
                "emergency": em not in ("0", "", "False", "false"),
            })
    return records


def analyse(runs_dir: Path, mode: str = "enforcement",
            delta_max: float = DELTA_MAX_STEER) -> Dict[str, object]:
    """Pool the committed-steer smoothness check over every ``mode`` run under
    ``runs_dir``. Returns the SR-006 verdict and supporting numbers."""
    params = {"delta_max_steer": delta_max}
    n_runs = 0
    n_ok = 0
    worst_smoothness = 0.0
    worst_committed = 0.0
    breaching: List[str] = []
    for status_csv in sorted(runs_dir.glob(f"*_{mode}_*/cage_status.csv")):
        records = _records_from_csv(status_csv)
        if len(records) < 2:
            continue
        mi5 = compute_run_metrics(records, params=params)["metrics"]["M-I5"]
        n_runs += 1
        worst_smoothness = max(worst_smoothness, mi5["steer_rate_max_smoothness"])
        worst_committed = max(worst_committed, mi5["steer_rate_max"])
        if mi5["steer_rate_smoothness_ok"]:
            n_ok += 1
        else:
            breaching.append(status_csv.parent.name)
    fraction = (n_ok / n_runs) if n_runs else None
    verdict = (fraction is not None and fraction >= PASS_FRACTION)
    return {
        "sr": "SR-006",
        "mode": mode,
        "delta_max_steer": delta_max,
        "n_runs": n_runs,
        "n_smoothness_ok": n_ok,
        "fraction_smoothness_ok": round(fraction, 4) if fraction is not None else None,
        "pass_fraction_threshold": PASS_FRACTION,
        "worst_rate_non_override": round(worst_smoothness, 4),
        "worst_rate_committed_all": round(worst_committed, 4),
        "breaching_runs": breaching,
        "verdict": "satisfied" if verdict else "not_satisfied",
        "note": (
            "smoothness measured on steps with no downstream safety-override rule "
            "(C-01/C-02/C-03/C-05) and no emergency; larger committed-steer rates "
            "on override steps are correct safety precedence (D-39)"
        ),
    }


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """CLI for the SR-006 analysis."""
    p = argparse.ArgumentParser(description="SR-006 committed-steer smoothness analysis (D-39).")
    p.add_argument("--runs", type=Path, default=DEFAULT_CAMPAIGN,
                   help="campaign runs/ directory (default: experiments/sim/campaign/runs).")
    p.add_argument("--mode", default="enforcement", choices=["enforcement", "monitoring"])
    p.add_argument("--delta-max", type=float, default=DELTA_MAX_STEER)
    p.add_argument("--json", action="store_true", help="emit JSON only.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Score the SR-006 committed-steer-rate criterion (D-39) across campaign runs."""
    args = _parse_args(argv)
    if not args.runs.is_dir():
        print(f"runs directory not found: {args.runs}", file=sys.stderr)
        return 2
    report = analyse(args.runs, mode=args.mode, delta_max=args.delta_max)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"SR-006 (actuator smoothness) — {report['mode']} runs: {report['n_runs']}")
    print(f"  bound delta_max_steer            : {report['delta_max_steer']}")
    print(f"  worst rate, non-override steps   : {report['worst_rate_non_override']}")
    print(f"  worst rate, all committed steps  : {report['worst_rate_committed_all']}")
    print(f"  runs within bound (non-override) : {report['n_smoothness_ok']}/{report['n_runs']} "
          f"(fraction {report['fraction_smoothness_ok']}, threshold {report['pass_fraction_threshold']})")
    if report["breaching_runs"]:
        print(f"  breaching runs                   : {report['breaching_runs'][:10]}")
    print(f"  VERDICT                          : {report['verdict'].upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
