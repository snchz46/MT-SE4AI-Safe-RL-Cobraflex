#!/usr/bin/env python3
"""
m2_from_csv.py
--------------
Convert the per-cycle latency CSV produced by
`cage/ros2/m2_latency_logger.py` into the `latency_obs_to_safe_action_ms`
block of `experiments/calibration/M2_results.json`.

Expected CSV layout:

    cycle_idx,obs_stamp_s,action_stamp_s,latency_ms
    0,1717081234.000000000,1717081234.041823000,41.8230
    1,1717081234.050000000,1717081234.094117000,44.1170
    ...

Usage:

    python tools/calibration_helpers/m2_from_csv.py \\
        --input-csv /tmp/m2_latency.csv \\
        --results-json experiments/calibration/M2_results.json

After this script writes, run
`python tools/apply_calibration.py --measurement M-2` to validate
the decision rule and emit the propagation report.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import List


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS = REPO_ROOT / "experiments" / "calibration" / "M2_results.json"


def load_latencies_ms(csv_path: Path) -> List[float]:
    lat: List[float] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "latency_ms" not in reader.fieldnames:
            raise ValueError(
                f"{csv_path}: expected column 'latency_ms' (found {reader.fieldnames})"
            )
        for row in reader:
            try:
                lat.append(float(row["latency_ms"]))
            except ValueError:
                continue
    return lat


def percentile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolation percentile, q in [0, 100]."""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (q / 100.0) * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-csv", required=True, type=Path,
                   help="CSV produced by m2_latency_logger.py")
    p.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS,
                   help=f"target M2_results.json (default: {DEFAULT_RESULTS})")
    p.add_argument("--platform", choices=["sim", "physical"], default="sim",
                   help="platform on which the measurement ran (default: sim)")
    p.add_argument("--executed-on", default="",
                   help="ISO date string YYYY-MM-DD (defaults to today)")
    p.add_argument("--executed-by", default="",
                   help="name of the experimenter")
    p.add_argument(
        "--actuator-latency-csv", type=Path, default=None,
        help=(
            "optional second CSV with `latency_ms` column for the "
            "safe_action -> actuator response leg; if omitted, the "
            "actuator block in M2_results.json keeps its `null` placeholders"
        ),
    )
    args = p.parse_args(argv)

    if not args.input_csv.exists():
        print(f"ERROR: --input-csv {args.input_csv} not found", file=sys.stderr)
        return 1
    if not args.results_json.exists():
        print(f"ERROR: --results-json {args.results_json} does not exist", file=sys.stderr)
        return 1

    lats = load_latencies_ms(args.input_csv)
    if len(lats) < 100:
        print(
            f"WARNING: only {len(lats)} latency samples in {args.input_csv}; "
            f"the protocol asks for >= 2000 cycles for stable tail-percentile estimates.",
            file=sys.stderr,
        )
    lats.sort()

    stats = {
        "median": round(percentile(lats, 50), 3),
        "p05": round(percentile(lats, 5), 3),
        "p95": round(percentile(lats, 95), 3),
        "p99": round(percentile(lats, 99), 3),
        "max": round(lats[-1], 3) if lats else 0.0,
    }
    n_cycles = len(lats)

    actuator_block = {
        "median": None,
        "p95": None,
        "comment": "null if not measured (sim-only run)",
    }
    if args.actuator_latency_csv is not None and args.actuator_latency_csv.exists():
        act_lats = sorted(load_latencies_ms(args.actuator_latency_csv))
        actuator_block = {
            "median": round(percentile(act_lats, 50), 3),
            "p95": round(percentile(act_lats, 95), 3),
            "comment": f"computed from {args.actuator_latency_csv}",
        }

    from datetime import date
    executed_on = args.executed_on or date.today().isoformat()

    data = json.loads(args.results_json.read_text(encoding="utf-8"))
    data["executed_on"] = executed_on
    data["executed_by"] = args.executed_by
    data["platform"] = args.platform
    data["n_cycles"] = n_cycles
    data["latency_obs_to_safe_action_ms"] = stats
    data["latency_safe_action_to_actuator_ms"] = actuator_block
    args.results_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"Processed {n_cycles} cycles from {args.input_csv}")
    print(
        f"  median={stats['median']} ms, "
        f"p05={stats['p05']} ms, p95={stats['p95']} ms, "
        f"p99={stats['p99']} ms, max={stats['max']} ms"
    )
    print(f"Wrote {args.results_json.relative_to(REPO_ROOT)}")
    print("Next: python tools/apply_calibration.py --measurement M-2")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
