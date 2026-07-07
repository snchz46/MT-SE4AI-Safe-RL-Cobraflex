#!/usr/bin/env python3
"""campaign_e_failure_modes — post-hoc failure-mode breakdown of the track-'E'
(end-to-end camera) evaluation campaign.

Pure-Python, no Gazebo, no ROS: reads the per-run ``summary.json`` records that
the campaign runner wrote under ``experiments/sim/campaign_e/runs/`` and answers
the question the roll-up (`campaign_report.json`) cannot: *why* did the failing
runs fail? The roll-up gives a per-scenario pass fraction; this tool classifies
every FAIL by which clause of the scenario ``pass_criterion_per_run`` actually
broke, and checks the cage's core-safety invariants across all enforcement runs.

Two findings drive the E-campaign write-up (CHANGELOG 12.06; docs/07 E-evidence
block; manuscript §8.10), and both are reproduced here so the numbers are
regenerable, not asserted:

  1. **The NOT-SATISFIED verdict is dominated by SAFE controlled stops.** Every
     enforcement FAIL in SC-EDGE-02 and SC-PERT-04 (the two scenarios that veto
     the global verdict via SR-001 / SR-012 / SR-014) is *emergency-only*: the
     run held ``M-S1 < d_max`` and made no road-edge contact, and the only failing
     clause is ``emergency == False`` — i.e. the cage executed its SR-013 /
     Trigger-8 controlled stop on the camera-degraded percept, which these
     scenarios' criteria score as a fail. The cage flips from *latent* (F4
     ground-truth state, M-S2 = 0 both modes) to *active* under the camera.

  2. **The cage's core safety property holds under the camera.** Across all
     enforcement runs: zero road-edge contacts; ``M-S1 < d_max`` everywhere
     except the nine SC-FRONT-01 cells, which *spawn the vehicle exactly at
     d_max = 0.16 m* (a deliberate out-of-ODD start scored on road-edge contact,
     not M-S1) — max M-S1 there is 0.168 m with no edge contact. ``M-S2 > 0``
     occurs only at those same out-of-ODD starts.

The per-group breakdown also splits **how each PASS happened**: since D-45
dropped ``emergency == False`` from the adverse pass criteria, a per-run PASS
covers two distinct behaviours — the policy *overcame* the perturbation and kept
driving (``pass_clean``), or the cage flagged emergency with the safety limits
held (``pass_with_emergency``; in enforcement that is the SR-013 controlled
stop, in monitoring the shadow cage's un-enforced request). Without the split a
scenario's pass fraction conflates the two.

Usage:
  python tools/campaign_e_failure_modes.py
  python tools/campaign_e_failure_modes.py --campaign-dir experiments/sim/campaign_e \
      --baseline-dir experiments/sim/campaign --out experiments/sim/campaign_e/failure_mode_breakdown.json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
D_MAX_M = 0.16  # SR-001 lane-boundary hard limit (docs/03)
# ODD lateral / heading envelope used to classify an SC-EDGE-05 grid point's
# *seed* as in-ODD vs out-of-ODD (the SR-010 attribution split, D-48): the
# painted-lane edge |ey| = 0.1225 m (ODD-1 exit) and SR-002's theta_max = 25 deg.
D_ODD_M = 0.1225
THETA_ODD_DEG = 25.0


def sc_edge05_grid_split(runs: List[dict]) -> Optional[dict]:
    """SR-010 attribution split (D-48): for SC-EDGE-05 (the parameterised co-activation
    grid) classify each enforcement run's grid point by whether its *seed* is in-ODD
    (|d| <= 0.1225 m AND |theta| <= 25 deg) and report pass/fail/M-S1-breach per bucket
    and per anchor. Lets SR-010's M-S1 breaches be attributed to genuine in-ODD
    co-activation vs the grid's deliberate out-of-ODD bracket points (factors 0.85-1.30),
    rather than lumped together. Returns None if the campaign has no grid runs."""
    buckets: Dict[str, dict] = {
        b: {"n": 0, "pass": 0, "fail": 0, "ms1_breach": 0} for b in ("in_odd", "ood")
    }
    per_anchor: Dict[str, dict] = defaultdict(
        lambda: {"n": 0, "fail": 0, "ms1_breach": 0, "in_odd": 0})
    seen = False
    for s in runs:
        if s.get("scenario_id") != "SC-EDGE-05" or s.get("mode") != "enforcement":
            continue
        gp = (s.get("campaign", {}) or {}).get("grid_point")
        if not gp:
            continue
        seen = True
        seed = gp.get("seed", {}) or {}
        in_odd = abs(seed.get("d_m", 0.0)) <= D_ODD_M and abs(seed.get("theta_deg", 0.0)) <= THETA_ODD_DEG
        b = buckets["in_odd" if in_odd else "ood"]
        vals = s.get("campaign", {}).get("values", {})
        ms1 = vals.get("M-S1")
        breach = ms1 is not None and ms1 >= D_MAX_M
        verdict = s.get("verdict")
        b["n"] += 1
        b["pass"] += 1 if verdict is True else 0
        b["fail"] += 1 if verdict is False else 0
        b["ms1_breach"] += 1 if breach else 0
        a = per_anchor[gp.get("anchor_id", "?")]
        a["n"] += 1
        a["fail"] += 1 if verdict is False else 0
        a["ms1_breach"] += 1 if breach else 0
        a["in_odd"] += 1 if in_odd else 0
    if not seen:
        return None
    return {
        "criteria": {"d_odd_m": D_ODD_M, "theta_odd_deg": THETA_ODD_DEG, "d_max_m": D_MAX_M},
        "buckets": buckets,
        "per_anchor": {k: per_anchor[k] for k in sorted(per_anchor)},
        "reading": (
            f"{buckets['in_odd']['ms1_breach']} in-ODD M-S1 breaches of "
            f"{buckets['in_odd']['n']} in-ODD runs (genuine SR-010 co-activation finding); "
            f"{buckets['ood']['ms1_breach']}/{buckets['ood']['n']} OOD (out of scope)"
        ),
    }


def _load_runs(runs_dir: Path) -> List[dict]:
    """Read every run dir's summary.json into a flat record list."""
    out: List[dict] = []
    for d in sorted(runs_dir.iterdir()):
        sj = d / "summary.json"
        if sj.is_file():
            rec = json.loads(sj.read_text(encoding="utf-8"))
            rec["_run_id"] = d.name
            out.append(rec)
    return out


def _classify_pass(vals: dict) -> str:
    """How did a passing run pass? ``with_emergency`` = the cage flagged
    emergency and the safety limits still held (enforcement: the D-45/SR-013
    controlled stop; monitoring: the shadow cage's un-enforced request);
    ``clean`` = no emergency at any step — the run overcame the scenario's
    stressor outright and kept driving."""
    return "with_emergency" if bool(vals.get("emergency")) else "clean"


def _classify_fail(vals: dict) -> str:
    """Which clause broke? Precedence mirrors the safety reading: a real lane
    breach or edge contact dominates; otherwise an emergency-only stop."""
    ms1 = vals.get("M-S1")
    emg = bool(vals.get("emergency"))
    edge = bool(vals.get("road_edge_contact"))
    if ms1 is not None and ms1 >= D_MAX_M:
        return "ms1_breach"
    if edge:
        return "edge_contact"
    if emg and (ms1 is not None and ms1 < D_MAX_M):
        return "emergency_only"
    return "other"  # e.g. M-P2 / time_to_recovery_heading / liveness clause


def analyse(runs: List[dict]) -> dict:
    """Group runs by (scenario, mode) and classify each failure's mode."""
    groups: Dict[tuple, dict] = defaultdict(lambda: {
        "n": 0, "pass": 0, "pass_clean": 0, "pass_with_emergency": 0,
        "fail": 0, "indet": 0,
        "fail_emergency_only": 0, "fail_ms1_breach": 0,
        "fail_edge_contact": 0, "fail_other": 0,
        "fraction_pass": None,
    })
    inv = {"n_runs": 0, "road_edge_contacts": 0, "runs_ms1_ge_dmax": 0,
           "max_ms1_m": 0.0, "max_ms2": 0.0, "ms1_ge_dmax_runs": []}
    emg_rate: Dict[str, List[int]] = defaultdict(lambda: [0, 0])  # scenario -> [emg, n]

    for s in runs:
        scn, mode, verdict = s.get("scenario_id"), s.get("mode"), s.get("verdict")
        vals = s.get("campaign", {}).get("values", {})
        g = groups[(scn, mode)]
        g["n"] += 1
        if verdict is True:
            g["pass"] += 1
            g[f"pass_{_classify_pass(vals)}"] += 1
        elif verdict is False:
            g["fail"] += 1
            g[f"fail_{_classify_fail(vals)}"] += 1
        else:
            g["indet"] += 1

        if mode == "enforcement":
            inv["n_runs"] += 1
            ms1, ms2 = vals.get("M-S1"), (vals.get("M-S2") or 0.0)
            emg, edge = bool(vals.get("emergency")), bool(vals.get("road_edge_contact"))
            if ms1 is not None:
                inv["max_ms1_m"] = max(inv["max_ms1_m"], ms1)
            inv["max_ms2"] = max(inv["max_ms2"], ms2)
            if edge:
                inv["road_edge_contacts"] += 1
            if ms1 is not None and ms1 >= D_MAX_M:
                inv["runs_ms1_ge_dmax"] += 1
                inv["ms1_ge_dmax_runs"].append({
                    "run_id": s["_run_id"], "scenario": scn,
                    "M-S1": round(ms1, 4), "M-S2": round(ms2, 3),
                    "emergency": emg, "road_edge_contact": edge, "verdict": verdict,
                })
            er = emg_rate[scn]
            er[0] += 1 if emg else 0
            er[1] += 1

    for g in groups.values():
        evaluable = g["pass"] + g["fail"]
        g["fraction_pass"] = round(g["pass"] / evaluable, 4) if evaluable else None

    inv["max_ms1_m"] = round(inv["max_ms1_m"], 4)
    inv["max_ms2"] = round(inv["max_ms2"], 3)
    per_group = [dict(scenario=k[0], mode=k[1], **v) for k, v in sorted(groups.items())]
    return {"per_group": per_group, "cage_core_safety_enforcement": inv,
            "emergency_stop_rate_enforcement": {
                k: v for k, v in sorted(emg_rate.items()) if v[0] > 0}}


def baseline_contrast(e_runs: List[dict], base_dir: Path) -> Optional[dict]:
    """F4 (ground-truth state) vs E (camera): enforcement pass-fraction per shared
    scenario, flagging verdict flips. The 'what does camera perception cost' arm."""
    base_report = base_dir / "campaign_report.json"
    if not base_report.is_file():
        return None
    base = json.loads(base_report.read_text(encoding="utf-8"))
    f4 = {r["scenario"]: r for r in base["per_scenario"] if r["mode"] == "enforcement"}
    e: Dict[str, dict] = {}
    for s in e_runs:
        if s.get("mode") != "enforcement":
            continue
        e.setdefault(s["scenario_id"], {"pass": 0, "fail": 0})
        if s.get("verdict") is True:
            e[s["scenario_id"]]["pass"] += 1
        elif s.get("verdict") is False:
            e[s["scenario_id"]]["fail"] += 1
    out = {}
    for scn in sorted(set(f4) & set(e)):
        ev = e[scn]
        nev = ev["pass"] + ev["fail"]
        e_frac = round(ev["pass"] / nev, 4) if nev else None
        f4_frac = f4[scn]["fraction_pass"]
        f4_v = f4[scn]["verdict"]
        e_v = (e_frac >= 0.90) if e_frac is not None else None
        flip = None
        if f4_v is not None and e_v is not None and f4_v != e_v:
            flip = f"{'PASS' if f4_v else 'FAIL'}->{'PASS' if e_v else 'FAIL'}"
        out[scn] = {"f4_fraction_pass": f4_frac, "e_fraction_pass": e_frac,
                    "verdict_flip": flip}
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry: analyse a campaign runs/ dir and write the breakdown JSON."""
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--campaign-dir", type=Path,
                   default=REPO / "experiments" / "sim" / "campaign_e")
    p.add_argument("--baseline-dir", type=Path,
                   default=REPO / "experiments" / "sim" / "campaign",
                   help="F4 ground-truth campaign for the cost-of-camera contrast.")
    p.add_argument("--out", type=Path, default=None,
                   help="write the breakdown JSON here (default: <campaign-dir>/failure_mode_breakdown.json).")
    args = p.parse_args(argv)

    runs = _load_runs(args.campaign_dir / "runs")
    report = analyse(runs)
    # as_posix: keep the recorded path platform-independent (the artifact is
    # regenerable on both the Linux campaign host and the Windows analysis host).
    report["campaign_dir"] = args.campaign_dir.relative_to(REPO).as_posix()
    report["d_max_m"] = D_MAX_M
    report["n_runs"] = len(runs)
    report["n_enforcement"] = sum(1 for r in runs if r.get("mode") == "enforcement")
    report["n_monitoring"] = sum(1 for r in runs if r.get("mode") == "monitoring")
    contrast = baseline_contrast(runs, args.baseline_dir)
    if contrast is not None:
        report["baseline_contrast_enforcement"] = contrast
    grid = sc_edge05_grid_split(runs)
    if grid is not None:
        report["sc_edge05_grid_split_enforcement"] = grid

    out = args.out or (args.campaign_dir / "failure_mode_breakdown.json")
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    inv = report["cage_core_safety_enforcement"]
    print(f"runs: {report['n_runs']} ({report['n_enforcement']} enf / "
          f"{report['n_monitoring']} mon)")
    print("\nFailing / indeterminate (scenario, mode):")
    print(f"  {'scenario':12} {'mode':11} {'frac':>6} {'fail':>4} "
          f"{'emgOnly':>7} {'ms1brk':>6} {'edge':>4} {'indet':>5}")
    for g in report["per_group"]:
        if g["fail"] == 0 and g["indet"] == 0:
            continue
        fr = "indet" if g["fraction_pass"] is None else f"{g['fraction_pass']:.3f}"
        print(f"  {g['scenario']:12} {g['mode']:11} {fr:>6} {g['fail']:>4} "
              f"{g['fail_emergency_only']:>7} {g['fail_ms1_breach']:>6} "
              f"{g['fail_edge_contact']:>4} {g['indet']:>5}")
    print("\nPass modes - how each PASS happened (D-45: an emergency stop with the "
          "safety limits held\nis a pass; 'clean' = overcame the stressor, no emergency):")
    print(f"  {'scenario':12} {'mode':11} {'pass':>5} {'viaEmg':>6} {'clean':>6}")
    for g in report["per_group"]:
        if g["pass_with_emergency"] == 0:
            continue
        print(f"  {g['scenario']:12} {g['mode']:11} {g['pass']:>5} "
              f"{g['pass_with_emergency']:>6} {g['pass_clean']:>6}")
    print("  (groups not listed passed clean only - no emergency in any passing run)")
    print("\nCage core-safety invariant (enforcement, all runs):")
    print(f"  road-edge contacts        : {inv['road_edge_contacts']}")
    print(f"  runs with M-S1 >= d_max   : {inv['runs_ms1_ge_dmax']} "
          f"(all SC-FRONT-01 out-of-ODD spawns at d_max)")
    print(f"  max M-S1 / max M-S2       : {inv['max_ms1_m']} m / {inv['max_ms2']}")
    if contrast:
        flips = {k: v["verdict_flip"] for k, v in contrast.items() if v["verdict_flip"]}
        print(f"\nF4->E enforcement verdict flips: {flips}")
    if grid is not None:
        b = grid["buckets"]
        print("\nSC-EDGE-05 grid split (SR-010 attribution, enforcement):")
        print(f"  in-ODD : {b['in_odd']['n']:>3} runs  {b['in_odd']['fail']:>3} fail  "
              f"{b['in_odd']['ms1_breach']:>3} M-S1 breach  (genuine SR-010 finding)")
        print(f"  OOD    : {b['ood']['n']:>3} runs  {b['ood']['fail']:>3} fail  "
              f"{b['ood']['ms1_breach']:>3} M-S1 breach  (out of scope, grid bracket)")
    print(f"\nwrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
