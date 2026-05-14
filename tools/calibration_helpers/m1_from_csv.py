#!/usr/bin/env python3
"""
m1_from_csv.py
--------------
Convert the per-position CSV files produced by
`cage/ros2/m1_lidar_noise_logger.py` into the `positions[]` array of
`experiments/calibration/M1_results.json`.

Expected CSV layout (one file per position):

    stamp_s,lateral_offset_m
    1717081234.000000000,0.001234
    1717081234.050000000,0.000987
    ...

The file name encodes the position label. The convention is
"millimetres in three digits" after `pos_` / `neg_`:

    y0_samples.csv          -> ground_truth_y_m = 0.0
    y_pos100_samples.csv    -> ground_truth_y_m = +0.100 m (100 mm)
    y_neg100_samples.csv    -> ground_truth_y_m = -0.100 m
    y_pos125_samples.csv    -> ground_truth_y_m = +0.125 m (125 mm)

Usage:

    python tools/calibration_helpers/m1_from_csv.py \\
        --input-dir /tmp/m1 \\
        --results-json experiments/calibration/M1_results.json

After this script writes, run
`python tools/apply_calibration.py --measurement M-1` to validate
the decision rule and emit the propagation report.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Pure-Python stats (no numpy needed)
import statistics


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RESULTS = REPO_ROOT / "experiments" / "calibration" / "M1_results.json"


# Recognised filename -> ground-truth position mappings.
# Convention: the digits after `pos_` / `neg_` are millimetres in three
# digits (zero-padded). `y0` is the centred position.
POSITION_PATTERN = re.compile(
    r"^(?P<label>y(?:0|_pos\d{3}|_neg\d{3}))_samples\.csv$",
    re.IGNORECASE,
)


def parse_position_from_label(label: str) -> float:
    """Convert a label like 'y0' / 'y_pos100' / 'y_neg100' to metres.

    Convention: digits encode millimetres (three-digit zero-padded).
    `y_pos100` -> +0.100 m, `y_neg125` -> -0.125 m, `y0` -> 0.0 m.
    """
    label = label.lower()
    if label == "y0":
        return 0.0
    if label.startswith("y_pos"):
        return int(label[5:]) / 1000.0
    if label.startswith("y_neg"):
        return -int(label[5:]) / 1000.0
    raise ValueError(f"unrecognised position label: {label}")


def load_samples(csv_path: Path) -> List[float]:
    """Read one CSV file and return its list of lateral_offset_m samples."""
    samples: List[float] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "lateral_offset_m" not in reader.fieldnames:
            raise ValueError(
                f"{csv_path}: expected column 'lateral_offset_m' "
                f"(found {reader.fieldnames})"
            )
        for row in reader:
            samples.append(float(row["lateral_offset_m"]))
    return samples


def stats_for_position(ground_truth_y: float, samples: List[float]) -> Dict[str, float]:
    """Compute mean, std_dev, p95(|y - mean|), lag-1 autocorrelation."""
    if len(samples) < 2:
        raise ValueError(
            f"position y={ground_truth_y}: only {len(samples)} samples; need >= 2"
        )
    mean = statistics.fmean(samples)
    std = statistics.stdev(samples)
    devs = sorted(abs(s - mean) for s in samples)
    # 95th-percentile absolute deviation
    p95_idx = int(0.95 * (len(devs) - 1))
    p95 = devs[p95_idx]
    # Lag-1 autocorrelation: corr(x[:-1], x[1:])
    if len(samples) >= 3 and std > 0.0:
        n = len(samples) - 1
        m1 = statistics.fmean(samples[:-1])
        m2 = statistics.fmean(samples[1:])
        s1 = statistics.stdev(samples[:-1])
        s2 = statistics.stdev(samples[1:])
        cov = sum((x - m1) * (y - m2) for x, y in zip(samples[:-1], samples[1:])) / (n - 1)
        denom = s1 * s2
        lag1 = (cov / denom) if denom > 0.0 else 0.0
    else:
        lag1 = 0.0
    return {
        "ground_truth_y_m": ground_truth_y,
        "mean_observed_y_m": round(mean, 6),
        "std_dev_m": round(std, 6),
        "p95_abs_deviation_m": round(p95, 6),
        "lag1_autocorr": round(lag1, 4),
    }


def discover_csvs(input_dir: Path) -> List[Tuple[float, Path]]:
    """Find the position-labelled CSV files in `input_dir`."""
    found: List[Tuple[float, Path]] = []
    for csv_path in sorted(input_dir.iterdir()):
        if not csv_path.is_file() or csv_path.suffix.lower() != ".csv":
            continue
        m = POSITION_PATTERN.match(csv_path.name)
        if not m:
            continue
        found.append((parse_position_from_label(m.group("label")), csv_path))
    return found


def write_results(results_json: Path, positions: List[Dict[str, float]],
                  executed_on: str, executed_by: str, samples_per_position: int,
                  perception_version: str) -> None:
    """Update the M1_results.json file in place."""
    data = json.loads(results_json.read_text(encoding="utf-8"))
    data["executed_on"] = executed_on
    data["executed_by"] = executed_by
    data["samples_per_position"] = samples_per_position
    data["perception_pipeline_version"] = perception_version
    data["positions"] = positions
    results_json.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input-dir", required=True, type=Path,
                   help="directory containing the per-position CSV files")
    p.add_argument("--results-json", type=Path, default=DEFAULT_RESULTS,
                   help=f"target M1_results.json (default: {DEFAULT_RESULTS})")
    p.add_argument("--executed-on", default="",
                   help="ISO date string YYYY-MM-DD (defaults to today)")
    p.add_argument("--executed-by", default="",
                   help="name of the experimenter")
    p.add_argument("--perception-version", default="",
                   help="git SHA or descriptor of the perception pipeline version")
    args = p.parse_args(argv)

    if not args.input_dir.is_dir():
        print(f"ERROR: --input-dir {args.input_dir} is not a directory", file=sys.stderr)
        return 1
    if not args.results_json.exists():
        print(f"ERROR: --results-json {args.results_json} does not exist", file=sys.stderr)
        return 1

    csvs = discover_csvs(args.input_dir)
    if len(csvs) == 0:
        print(f"ERROR: no matching CSVs in {args.input_dir} "
              f"(expected y0_samples.csv, y_pos010_samples.csv, y_neg010_samples.csv)",
              file=sys.stderr)
        return 1

    positions: List[Dict[str, float]] = []
    min_samples = None
    for ground_truth_y, csv_path in csvs:
        samples = load_samples(csv_path)
        positions.append(stats_for_position(ground_truth_y, samples))
        if min_samples is None or len(samples) < min_samples:
            min_samples = len(samples)
        print(f"  {csv_path.name}: {len(samples)} samples, "
              f"sigma={positions[-1]['std_dev_m']:.4f} m, "
              f"bias={abs(positions[-1]['mean_observed_y_m'] - ground_truth_y):.4f} m")

    from datetime import date
    executed_on = args.executed_on or date.today().isoformat()

    write_results(
        args.results_json, positions,
        executed_on=executed_on,
        executed_by=args.executed_by,
        samples_per_position=min_samples or 0,
        perception_version=args.perception_version,
    )
    print(f"\nWrote {len(positions)} positions to {args.results_json.relative_to(REPO_ROOT)}")
    print("Next: python tools/apply_calibration.py --measurement M-1")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
