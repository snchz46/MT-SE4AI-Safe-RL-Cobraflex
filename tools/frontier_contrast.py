#!/usr/bin/env python3
"""
frontier_contrast — paired enforcement-vs-monitoring analysis of the F4 frontier
/ out-of-ODD cage-efficacy study.

The frontier scenarios are NOT scored by the D-29/D-30 SR-verdict machinery
(run_campaign.py); their value is the *paired contrast* between the two cage
modes on the same policy: monitoring is the no-cage counterfactual (the raw
policy is applied, the cage observes only), enforcement is the cage acting. This
tool reads the per-run ``summary.json`` files a frontier campaign produced and
quantifies, per (scenario, policy seed), the harm the cage prevents:

  * road-edge contact rate  — fraction of runs that reached the road edge (crash)
  * max-excursion           — how far out the vehicle got (median / mean)
  * emergency rate          — fraction of runs in which C-05 fired

and the cage benefit = monitoring(no-cage) − enforcement(cage) on each.

Pure stdlib; the parsing + aggregation are unit-tested without ROS.

Usage:
  python tools/frontier_contrast.py experiments/sim/campaign_frontier/runs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# run_id format from run_campaign.run_id_for:
#   camp_<sid>_<controller>_<who>_<mode>_rep<NN>   (who = seed<N> | pd)
_RUN_ID_RE = re.compile(
    r"^camp_.+_(?:rl|pd)_(?P<who>seed\d+|pd)_(?P<mode>enforcement|monitoring)_rep(?P<rep>\d+)$"
)


@dataclass
class RunRecord:
    """One frontier run's outcome (max excursion + road-edge contact)."""
    scenario: str
    seed: str          # "2024" / "123" / "pd"
    mode: str          # enforcement | monitoring
    rep: int
    max_excursion_m: Optional[float]
    road_edge_contact: Optional[bool]
    emergency: Optional[bool]
    termination_reason: str
    verdict: Optional[bool]


def parse_run(run_id: str, summary: Dict[str, object]) -> Optional[RunRecord]:
    """Build a RunRecord from a run dir name + its summary.json dict. Returns None
    if the dir name is not a campaign run id (e.g. a stray manual run)."""
    m = _RUN_ID_RE.match(run_id)
    if not m:
        return None
    who = m.group("who")
    seed = who[4:] if who.startswith("seed") else who
    campaign = summary.get("campaign") or {}
    values = campaign.get("values") or {}
    return RunRecord(
        scenario=str(summary.get("scenario_id", "")),
        seed=seed,
        mode=str(summary.get("mode", m.group("mode"))),
        rep=int(m.group("rep")),
        max_excursion_m=_as_float(values.get("max_excursion_m")),
        road_edge_contact=_as_bool(values.get("road_edge_contact")),
        emergency=_as_bool(values.get("emergency")),
        termination_reason=str(campaign.get("termination_reason", "")),
        verdict=summary.get("verdict") if isinstance(summary.get("verdict"), bool) else None,
    )


def _as_float(v: object) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _as_bool(v: object) -> Optional[bool]:
    return bool(v) if isinstance(v, bool) else None


def load_runs(runs_dir: Path) -> List[RunRecord]:
    """Load every campaign run under ``runs_dir`` (each a subdir with summary.json)."""
    out: List[RunRecord] = []
    for sub in sorted(Path(runs_dir).glob("*/")):
        sp = sub / "summary.json"
        if not sp.is_file():
            continue
        rec = parse_run(sub.name, json.loads(sp.read_text(encoding="utf-8")))
        if rec is not None:
            out.append(rec)
    return out


def _median(xs: Sequence[float]) -> Optional[float]:
    ys = sorted(xs)
    n = len(ys)
    if n == 0:
        return None
    mid = n // 2
    return ys[mid] if n % 2 else 0.5 * (ys[mid - 1] + ys[mid])


def _mean(xs: Sequence[float]) -> Optional[float]:
    return sum(xs) / len(xs) if xs else None


def _cell_stats(runs: Sequence[RunRecord]) -> Dict[str, object]:
    """Aggregate one (scenario, seed, mode) cell: excursion stats + contact rate."""
    excursions = [r.max_excursion_m for r in runs if r.max_excursion_m is not None]
    contacts = [r.road_edge_contact for r in runs if r.road_edge_contact is not None]
    emergencies = [r.emergency for r in runs if r.emergency is not None]
    return {
        "n": len(runs),
        "contact_rate": (sum(1 for c in contacts if c) / len(contacts)) if contacts else None,
        "emergency_rate": (sum(1 for e in emergencies if e) / len(emergencies)) if emergencies else None,
        "max_excursion_median": _median(excursions),
        "max_excursion_mean": _mean(excursions),
    }


def contrast(records: Sequence[RunRecord]) -> List[Dict[str, object]]:
    """Per (scenario, seed): enforcement vs monitoring cell stats + the cage
    benefit (monitoring − enforcement) on contact rate and max excursion."""
    groups: Dict[Tuple[str, str], Dict[str, List[RunRecord]]] = {}
    for r in records:
        cell = groups.setdefault((r.scenario, r.seed), {"enforcement": [], "monitoring": []})
        if r.mode in cell:
            cell[r.mode].append(r)

    report: List[Dict[str, object]] = []
    for (scenario, seed), modes in sorted(groups.items()):
        enf = _cell_stats(modes["enforcement"])
        mon = _cell_stats(modes["monitoring"])
        benefit: Dict[str, object] = {}
        if enf["contact_rate"] is not None and mon["contact_rate"] is not None:
            benefit["contact_rate_reduction"] = mon["contact_rate"] - enf["contact_rate"]
        if enf["max_excursion_median"] is not None and mon["max_excursion_median"] is not None:
            benefit["max_excursion_reduction_median"] = (
                mon["max_excursion_median"] - enf["max_excursion_median"]
            )
        report.append({
            "scenario": scenario, "seed": seed,
            "enforcement": enf, "monitoring": mon, "cage_benefit": benefit,
        })
    return report


def _fmt_pct(x: Optional[float]) -> str:
    return "  n/a" if x is None else f"{100 * x:4.0f}%"


def _fmt_m(x: Optional[float]) -> str:
    return " n/a " if x is None else f"{x:.3f}"


def print_report(report: Sequence[Dict[str, object]]) -> None:
    """Console table of the enforcement-vs-monitoring contrast."""
    print("Frontier cage-efficacy contrast (monitoring = no-cage counterfactual)")
    print("=" * 72)
    for row in report:
        enf, mon, ben = row["enforcement"], row["monitoring"], row["cage_benefit"]
        print(f"\n{row['scenario']}  seed={row['seed']}")
        print(f"  enforcement (cage) : n={enf['n']:>3}  contact={_fmt_pct(enf['contact_rate'])}"
              f"  max_exc med={_fmt_m(enf['max_excursion_median'])} m  emerg={_fmt_pct(enf['emergency_rate'])}")
        print(f"  monitoring (no-cage): n={mon['n']:>3}  contact={_fmt_pct(mon['contact_rate'])}"
              f"  max_exc med={_fmt_m(mon['max_excursion_median'])} m  emerg={_fmt_pct(mon['emergency_rate'])}")
        cr = ben.get("contact_rate_reduction")
        me = ben.get("max_excursion_reduction_median")
        tag = ""
        if cr is not None and cr > 0:
            tag = "  <- CAGE PREVENTS CONTACT"
        elif cr == 0 and (me is None or abs(me) < 0.01):
            tag = "  <- policy safe without cage"
        print(f"  cage benefit: contact reduction={_fmt_pct(cr)}  "
              f"max_exc reduction={_fmt_m(me)} m{tag}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry: read frontier runs, build the paired contrast, write JSON."""
    p = argparse.ArgumentParser(description="Frontier cage-efficacy paired contrast.")
    p.add_argument("runs_dir", type=Path, help="campaign frontier runs/ dir (subdirs with summary.json).")
    p.add_argument("--json", type=Path, default=None, help="also write the report as JSON here.")
    args = p.parse_args(argv)

    records = load_runs(args.runs_dir)
    if not records:
        print(f"No campaign runs found under {args.runs_dir}", file=sys.stderr)
        return 1
    report = contrast(records)
    print_report(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
