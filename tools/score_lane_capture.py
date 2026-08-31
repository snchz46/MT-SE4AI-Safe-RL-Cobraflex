#!/usr/bin/env python3
"""
score_lane_capture — score a true-position lane capture against the acceptance
tests D-75/D-76/D-77 left open, and answer the one question the 31.08 session
could not: WHICH line pair is the true one at each point of the track.

WHY THIS EXISTS. docs/17 §10.6 closed the 31.08 track session with a diagnosis
and no cause: the estimator is trustworthy near the centre, the policy runs wide
in curves, and eight single-component hypotheses died against driving data. D-77
then answered the *consistency* half offline — `labels.csv`'s `line_c0_m` replays
the pairing exactly — and left *accuracy* owed: a reported `ey` cannot be scored
against a label the same estimator produced. So the capture declares the offset
the car is pushed at (`--true-ey`) and marks arc-length anchors at numbered floor
stations, and this tool scores the result.

WHAT IT REFUSES TO DO. It does not average over the circuit. The whole point of
the 31.08 sweep's limitation ("one location", SWEEP_NOTE) is that a global mean
hides a local failure: the estimator paired 95.4 % of circuit frames while being
unusable right-of-centre at one spot. Every statistic here is therefore reported
PER STATION SEGMENT, and the summary names the worst segment rather than the mean.

Run it on a capture directory produced by
``tools/record_lane_dataset.py --true-ey ... --station-arc ...``.
Columns it needs are degraded gracefully: without ``true_ey_m`` it scores
consistency only, without ``station``/``s_m`` it cannot run the closed-loop test.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics as st
from pathlib import Path
from typing import Dict, List, Optional

NOMINAL_LANE_W = 0.245      # CvLaneEstimatorConfig.lane_width_nominal_m
PAIR_TOL = 0.040            # M-7 §3b: "paired the RIGHT two lines" criterion
RELOC_DISP = 0.060          # D-77: above the 43 mm off-centre noise span
RELOC_RATE = 1.0            # D-77: m/s apparent lateral, vs a 0.22 m/s car


def _f(row: dict, key: str) -> Optional[float]:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load(path: Path) -> List[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def interpolate_arc(rows: List[dict]) -> None:
    """Fill ``s_interp`` on every row from the station anchors.

    Between two station events the arc length is linear in TIME, which assumes a
    roughly constant push speed over one inter-station stretch — the reason the
    stations are placed a few metres apart rather than one per lap. Rows before
    the first station or after the last keep ``None``: extrapolating past an
    anchor is exactly the kind of unmeasured guess this tool exists to avoid.
    """
    marks = []  # (index, stamp, s)
    last = None
    for i, r in enumerate(rows):
        stn = _f(r, "station")
        s = _f(r, "s_m")
        if stn is None or s is None or stn == 0:
            continue
        if stn != last:
            marks.append((i, _f(r, "stamp_s"), s))
            last = stn
    for r in rows:
        r["s_interp"] = None
    for (i0, t0, s0), (i1, t1, s1) in zip(marks[:-1], marks[1:]):
        if None in (t0, t1) or t1 <= t0:
            continue
        for r in rows[i0:i1]:
            t = _f(r, "stamp_s")
            if t is None:
                continue
            r["s_interp"] = s0 + (s1 - s0) * (t - t0) / (t1 - t0)
    return None


def segments(rows: List[dict]) -> Dict[int, List[dict]]:
    out: Dict[int, List[dict]] = {}
    for r in rows:
        stn = _f(r, "station")
        if stn is None:
            continue
        out.setdefault(int(stn), []).append(r)
    return out


def paired(r: dict) -> bool:
    return (r.get("paired") or "").strip() == "1"


def report_accuracy(rows: List[dict], true_w: float) -> None:
    """Reported ey vs the tape, and pairing correctness, PER STATION SEGMENT."""
    have_truth = any(_f(r, "true_ey_m") is not None for r in rows)
    print("\n" + "=" * 78)
    print("ACCURACY — reported ey against the tape, per station segment")
    print("=" * 78)
    if not have_truth:
        print("  no `true_ey_m` column: this capture was recorded without")
        print("  --true-ey, so accuracy CANNOT be scored. Consistency only below.")
        return
    segs = segments(rows)
    print(f"{'stn':>4}{'n':>6}{'paired':>8}{'right pair':>12}"
          f"{'ey err mean':>13}{'ey err p95':>12}{'width err':>11}")
    worst = (None, -1.0)
    for stn in sorted(segs):
        rs = segs[stn]
        if stn == 0 or not rs:
            continue
        p = [r for r in rs if paired(r)]
        errs, werrs, right = [], [], 0
        for r in p:
            ey, tey = _f(r, "ey_m"), _f(r, "true_ey_m")
            w = _f(r, "lane_width_m")
            if None in (ey, tey):
                continue
            errs.append(abs(ey - tey))
            if w is not None:
                werrs.append(abs(w - true_w))
                if abs(w - true_w) <= PAIR_TOL:
                    right += 1
        if not errs:
            print(f"{stn:>4}{len(rs):>6}{'—':>8}{'—':>12}{'no paired frames':>36}")
            continue
        errs.sort()
        mean_e = st.mean(errs)
        p95 = errs[min(len(errs) - 1, int(0.95 * len(errs)))]
        print(f"{stn:>4}{len(rs):>6}{100*len(p)/len(rs):>7.1f}%"
              f"{100*right/max(1,len(p)):>11.1f}%"
              f"{mean_e*1000:>12.1f}mm{p95*1000:>11.1f}mm"
              f"{(st.mean(werrs)*1000 if werrs else float('nan')):>10.1f}mm")
        if mean_e > worst[1]:
            worst = (stn, mean_e)
    if worst[0] is not None:
        print(f"\n  WORST SEGMENT: station {worst[0]}, mean |ey error| "
              f"{worst[1]*1000:.1f} mm. That is the number that matters — a good "
              f"circuit mean\n  is exactly what hid this failure on 18.08 (M-7 §3).")


def report_relocations(rows: List[dict]) -> None:
    """D-76/D-77: unphysical relocations of the selected lane centre, and — with
    truth available — whether the relocation moved TOWARD or AWAY from the tape."""
    print("\n" + "=" * 78)
    print("CONSISTENCY — unphysical relocations of the selected lane centre")
    print("=" * 78)
    prev = prevt = prev_err = None
    n = reloc = away = 0
    worst = 0.0
    worst_rate = 0.0
    for r in rows:
        if not paired(r):
            prev = None
            continue
        ey, t = _f(r, "ey_m"), _f(r, "stamp_s")
        if None in (ey, t):
            prev = None
            continue
        tey = _f(r, "true_ey_m")
        err = None if tey is None else abs(ey - tey)
        if prev is not None and prevt is not None and 0 < t - prevt < 0.5:
            n += 1
            d = abs(ey - prev)
            rate = d / (t - prevt)
            if d > RELOC_DISP and rate > RELOC_RATE:
                reloc += 1
                worst = max(worst, d)
                worst_rate = max(worst_rate, rate)
                if err is not None and prev_err is not None and err > prev_err:
                    away += 1
        prev, prevt, prev_err = ey, t, err
    if not n:
        print("  no consecutive paired frames — nothing to score.")
        return
    print(f"  transitions scored        {n}")
    print(f"  unphysical relocations    {reloc}  ({100*reloc/n:.2f} %)"
          f"   [> {RELOC_DISP*1000:.0f} mm at > {RELOC_RATE:.1f} m/s apparent]")
    print(f"  worst single-frame jump   {worst*1000:.1f} mm")
    print(f"  worst apparent lateral rate {worst_rate:.2f} m/s"
          f"   ({worst_rate/0.22:.0f}x the car's 0.22 m/s top speed)")
    if reloc:
        print(f"  of those, moved AWAY from the tape: {away}/{reloc}"
              + ("" if away else "  (no truth column, or none did)"))
    print("\n  D-77 set the physical `perception_jump_tol_m` to 0.05 so a caught")
    print("  frame suppresses /state_obs without raising /emergency. A relocation")
    print("  count that stays high here means the SELECTION is still wrong, which")
    print("  D-77 explicitly did not fix — only declared.")


def report_closed_loop(rows: List[dict], perimeter: float) -> None:
    """D-75's geometry-independent test: over a closed circuit ∮κ·ds = 2π."""
    print("\n" + "=" * 78)
    print("D-75 CLOSED-LOOP CURVATURE — the test no confound survives")
    print("=" * 78)
    have = [r for r in rows if r.get("s_interp") is not None
            and _f(r, "curvature_1pm") is not None and paired(r)]
    if len(have) < 20:
        print("  needs `station`/`s_m` (from --station-arc) plus `curvature_1pm`.")
        print("  Not scorable from this capture.")
        return
    turn = aturn = 0.0
    ds_total = 0.0
    for a, b in zip(have[:-1], have[1:]):
        ds = b["s_interp"] - a["s_interp"]
        if ds <= 0 or ds > 0.5:
            continue
        k = _f(a, "curvature_1pm") or 0.0
        turn += k * ds
        aturn += abs(k) * ds
        ds_total += ds
    if ds_total <= 0:
        print("  no usable arc-length increments.")
        return
    laps = ds_total / perimeter
    expected = laps * 2 * math.pi
    ratio = aturn / expected if expected else float("nan")
    print(f"  arc length covered        {ds_total:.2f} m  ({laps:.2f} laps of {perimeter} m)")
    print(f"  turning implied by geometry {expected:.2f} rad")
    print(f"  measured  ∫|κ|ds          {aturn:.2f} rad   ratio {ratio:.2f}")
    print(f"  measured  ∫κ ds (signed)  {turn:.2f} rad")
    verdict = ("PASS — κ is a road property here"
               if 0.75 <= ratio <= 1.35 else
               "FAIL — κ still over-reads; D-75 stays blocked and C-04 stays un-armable")
    print(f"\n  ACCEPTANCE (ratio in 0.75..1.35): {verdict}")
    print("  |κ| is an UPPER bound (it cannot cancel), so a ratio near 1 with a")
    print("  signed integral near 2π·laps is the strong result.")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("capture", help="capture directory (containing labels.csv)")
    p.add_argument("--true-width", type=float, default=0.250,
                   help="ruler lane width (m); 0.250 measured on the track")
    p.add_argument("--perimeter", type=float, default=19.28)
    a = p.parse_args(argv)

    path = Path(a.capture)
    csv_path = path if path.suffix == ".csv" else path / "labels.csv"
    if not csv_path.exists():
        print(f"no labels.csv at {csv_path}")
        return 2
    rows = load(csv_path)
    if not rows:
        print("labels.csv is empty")
        return 2
    interpolate_arc(rows)

    print(f"\ncapture: {csv_path}   rows: {len(rows)}   "
          f"paired: {sum(1 for r in rows if paired(r))}")
    cols = set(rows[0].keys())
    for need, why in (("true_ey_m", "accuracy"), ("station", "closed loop"),
                      ("line_c0_m", "pairing replay"),
                      ("curvature_1pm", "closed loop")):
        if need not in cols:
            print(f"  MISSING column `{need}` — {why} degraded. Recorded with an "
                  f"older tools/record_lane_dataset.py?")

    report_accuracy(rows, a.true_width)
    report_relocations(rows)
    report_closed_loop(rows, a.perimeter)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
