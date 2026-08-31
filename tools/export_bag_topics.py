#!/usr/bin/env python3
"""
export_bag_topics — turn the light topics of a physical rosbag into a tracked CSV,
so an analysis can leave the car.

WHY THIS EXISTS. Evidence does not flow between this project's three machines by
git: the Jetson records, the compute host analyses, and `experiments/physical/runs/
*_bag/` holds 181 MB of `.db3` that has no business in the index. But the analysis
that decides whether the 31.08 departures are a plant-gain problem (D-70: the real
chassis delivers about half the commanded yaw) or a learned-trajectory one needs
the ACHIEVED yaw rate, and `cage_status.csv` — the file that *is* tracked — carries
only cage-side signals: raw/safe steering, ey, epsi, speed, kappa. No odometry.

So the bag is reduced here, on the machine that has it, to a few hundred kB of CSV
that any host can read with no ROS installed and no bag present.

AND IT IS A TRACKED TOOL ON PURPOSE. D-78 §11.6 found that `circuit_export/
labels.csv` carried a `line_c0_m` column that no tracked tool wrote — it came from
an untracked variant on another host, and the analysis resting on it was therefore
not reproducible from the repo. Committing a CSV produced by a throwaway script
would repeat exactly that defect.

    python3 tools/export_bag_topics.py <run>_bag --out <run>/bag_export.csv

Default topics are the pair the yaw analysis needs. One row per message, long
format (topic, field, value), so adding a topic never changes the schema.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# The yaw question: what was commanded, and what the vehicle actually did.
DEFAULT_TOPICS = ("/cmd_vel", "/odometry/filtered")


def _fields(topic: str, msg) -> dict:
    """The scalars worth keeping per message type, flattened.

    Deliberately narrow. A generic serialiser would produce a 40-column file of
    covariance entries nobody reads, and the point of this tool is a CSV small
    enough to live in the index.
    """
    out: dict = {}
    tname = type(msg).__name__
    if tname == "Twist":
        out["linear_x"] = msg.linear.x
        out["angular_z"] = msg.angular.z
    elif tname == "Odometry":
        out["pos_x"] = msg.pose.pose.position.x
        out["pos_y"] = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        out["quat_z"] = q.z
        out["quat_w"] = q.w
        out["vel_x"] = msg.twist.twist.linear.x
        # The achieved yaw rate — the whole reason this tool exists.
        out["yaw_rate"] = msg.twist.twist.angular.z
    elif tname == "Bool":
        out["data"] = 1 if msg.data else 0
    elif tname == "Empty":
        out["data"] = 1
    elif tname == "Float64MultiArray":
        for i, v in enumerate(msg.data):
            out[f"d{i}"] = v
    else:
        return {}
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bag", help="the *_bag directory written by run_physical_lap.sh")
    p.add_argument("--out", required=True, help="output CSV")
    p.add_argument("--topics", default=",".join(DEFAULT_TOPICS),
                   help="comma-separated topic list")
    a = p.parse_args(argv)

    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    wanted = [t.strip() for t in a.topics.split(",") if t.strip()]
    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(a.bag), storage_id="sqlite3"),
        rosbag2_py.ConverterOptions(input_serialization_format="cdr",
                                    output_serialization_format="cdr"),
    )
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    missing = [t for t in wanted if t not in types]
    if missing:
        print(f"not in this bag: {missing}\navailable: {sorted(types)}",
              file=sys.stderr)
        return 2

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["t_s", "topic", "field", "value"])
        while reader.has_next():
            topic, data, stamp = reader.read_next()
            if topic not in wanted:
                continue
            msg = deserialize_message(data, get_message(types[topic]))
            for k, v in _fields(topic, msg).items():
                wr.writerow([f"{stamp * 1e-9:.6f}", topic, k, f"{v:.6f}"])
                n += 1
    size_kb = out.stat().st_size / 1024
    print(f"{n} rows -> {out}  ({size_kb:.0f} kB)")
    for t in wanted:
        print(f"  {t}  ({types[t]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
