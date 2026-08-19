#!/usr/bin/env python3
"""
measure_offset_response — the hands-off test M-7 §3b leaves outstanding.

THE QUESTION. Two hand-swept sessions measured the estimator's pairing collapsing
with lateral offset: the share of frames whose measured lane width lands within
40 mm of the ruler's 250 falls 18% -> 30% -> 87% -> 95% REJECTED across the
0-30 / 30-55 / 55-80 / 80-120 mm bands. If that is real, the estimator feeding
C-01 (d_max 160 mm) and C-05 (d_warning 120 mm) is trustworthy only within about
+/-55 mm — inside the entire band where those rules act.

But both sweeps moved the car BY HAND, and sliding a chassis tilts it.
`camera_geometry` reads a constant 0.30 rad pitch, not the TF, so a couple of
degrees of tilt mis-projects every ground point. Camera pitch and height are not
observable from those logs, so the |ey| dependence is confounded with handling.

This separates them. Park the car on the ground at a tape-measured offset, TAKE
YOUR HANDS OFF, and sample. Repeat at several offsets. Nothing is touched while
measuring, so any degradation that survives is the estimator's, not yours.

WHAT IT MEASURES, and why it is stronger than the sweep. §3b scored frames on
lane width, which is an indirect proxy. Here the tape gives ground truth for `ey`
directly, so the output is the estimator's actual **transfer function** —
reported vs true — and with it the real trigger points of C-01 and C-05, measured
rather than inferred.

MEASURING true ey. Lay a tape across the lane, perpendicular to it. Note the
reading at the INNER EDGE of each white line; the midpoint of those two readings
is the lane centre. Read where the car's longitudinal centreline sits. The signed
difference is `ey`, POSITIVE when the car is LEFT of centre — the estimator's
convention, verified on the bench (ey +0.20 -> steering -0.12 -> turns right).

    # one point, then another, then another; the curve accumulates
    python3 tools/measure_offset_response.py --true-ey 0
    python3 tools/measure_offset_response.py --true-ey 40
    python3 tools/measure_offset_response.py --true-ey -40
    ...
    python3 tools/measure_offset_response.py --report      # just print the curve

Suggested points: 0, +/-40, +/-60, +/-80, +/-100 mm. Both signs at every
magnitude — the two sides are not interchangeable, and the first pass had almost
nothing on the left.
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "src" / "cobraflex_rl",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

DEFAULT_OUT = _REPO / "experiments" / "calibration" / "M7_offset_response.csv"
TRUE_WIDTH_MM = 250.0
WIDTH_TOL_MM = 40.0
COLS = ["true_ey_mm", "n_frames", "paired_pct", "width_sane_pct", "width_mean_mm",
        "width_sd_mm", "ey_mean_mm", "ey_sd_mm", "epsi_mean_deg", "epsi_sd_deg",
        "conf_mean", "stamp"]


def _load(path: Path):
    if not path.exists():
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def _report(rows) -> None:
    if not rows:
        print("no points recorded yet")
        return
    rows = sorted(rows, key=lambda r: float(r["true_ey_mm"]))
    print("\n" + "=" * 88)
    print("OFFSET RESPONSE — hands-off, tape-referenced")
    print("=" * 88)
    print(f"{'true ey':>8} {'n':>5} {'paired':>7} {'w-sane':>7} {'width':>8} "
          f"{'ey rep':>8} {'ey sd':>7} {'epsi':>8} {'err':>8}")
    print("-" * 88)
    for r in rows:
        t = float(r["true_ey_mm"]); rep = float(r["ey_mean_mm"])
        print(f"{t:+8.0f} {int(r['n_frames']):5d} {float(r['paired_pct']):6.0f}% "
              f"{float(r['width_sane_pct']):6.0f}% {float(r['width_mean_mm']):8.1f} "
              f"{rep:+8.1f} {float(r['ey_sd_mm']):7.1f} "
              f"{float(r['epsi_mean_deg']):+8.1f} {rep - t:+8.1f}")
    pts = [(float(r["true_ey_mm"]), float(r["ey_mean_mm"])) for r in rows
           if float(r["width_sane_pct"]) >= 50.0]
    print("-" * 88)
    if len(pts) >= 3:
        mx = statistics.mean([a for a, _ in pts]); my = statistics.mean([b for _, b in pts])
        sxx = sum((a - mx) ** 2 for a, _ in pts)
        sxy = sum((a - mx) * (b - my) for a, b in pts)
        if sxx > 0:
            k = sxy / sxx
            c = my - k * mx
            print(f"  transfer over the {len(pts)} trustworthy points (width-sane >= 50%):")
            print(f"      reported_ey = {k:.3f} * true_ey {c:+.1f} mm")
            if abs(k) > 1e-3:
                print(f"  => C-01's d_max 0.16 m actually fires at a true "
                      f"{(160.0 - c) / k:.0f} mm")
                print(f"     C-05's d_warning 0.12 m at a true {(120.0 - c) / k:.0f} mm")
            if abs(k - 1.0) <= 0.06 and abs(c) <= 10.0:
                print("  => the estimator reports lateral offset correctly where it is "
                      "trustworthy.")
    else:
        print("  need at least 3 points with width-sane >= 50% for a transfer fit")
    bad = [r for r in rows if float(r["width_sane_pct"]) < 50.0]
    if bad:
        edge = min(abs(float(r["true_ey_mm"])) for r in bad)
        print(f"  first |true ey| where the estimate stops being trustworthy: "
              f"{edge:.0f} mm")
        print(f"     C-05 warns at 120 mm and C-01 limits at 160 mm — both "
              f"{'BEYOND' if edge < 120 else 'within'} that.")
    print("=" * 88)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--true-ey", type=float,
                   help="tape-measured offset in MILLIMETRES, signed; + = car left "
                        "of the lane centre. Omit with --report.")
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--report", action="store_true", help="print the curve and exit")
    p.add_argument("--image-topic", default="camera/image_raw_lane")
    p.add_argument("--white-sat-max", type=int, default=-1)
    p.add_argument("--save-frames", type=int, default=12,
                   help="frames to keep per point, under <out>/frames/. 0 disables. "
                        "The 18.08 series did NOT save any, so its tape ground truth "
                        "could not be replayed against a corrected estimator — the "
                        "one dataset with real ground truth was single-use.")
    a = p.parse_args(argv)

    out = Path(a.out)
    if a.report:
        _report(_load(out))
        return 0
    if a.true_ey is None:
        p.error("--true-ey is required unless --report")

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from cobraflex_rl.camera_pipeline import decode_image
    from cobraflex_rl.cv_lane_estimator import CvLaneEstimator, CvLaneEstimatorConfig

    cfg = {}
    if a.white_sat_max >= 0:
        cfg["white_sat_max"] = a.white_sat_max
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**cfg))

    rclpy.init(args=None)
    node = Node("measure_offset_response")
    buf = []
    node.create_subscription(Image, a.image_topic, lambda m: buf.append(m),
                             qos_profile_sensor_data)
    print(f"\n*** HANDS OFF THE CAR — sampling {a.seconds:.0f} s at a true ey of "
          f"{a.true_ey:+.0f} mm ***")
    for n in (3, 2, 1):
        print(f"    {n}...")
        time.sleep(1.0)

    ests = []
    keep = []
    end = time.time() + a.seconds
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        while buf:
            m = buf.pop(0)
            try:
                f = decode_image(m.data, int(m.height), int(m.width),
                                 m.encoding, int(m.step))
            except ValueError:
                continue
            ests.append(est.estimate(f))
            if a.save_frames and len(keep) < a.save_frames:
                keep.append(f)
    node.destroy_node()
    rclpy.shutdown()

    if not ests:
        print("no frames — is csi_camera_node running?")
        return 1
    paired = [e for e in ests if e.ok and e.reason != "single_line" and e.n_lines >= 2]
    pct_p = 100.0 * len(paired) / len(ests)
    if not paired:
        print(f"\n{len(ests)} frames, 0 paired — nothing to record at this offset.")
        print("That IS the answer for this point, but record it only once you are")
        print("sure the car is where you think: check the lane is in view at all.")
        return 1
    w = [e.lane_width * 1000.0 for e in paired]
    ey = [e.ey * 1000.0 for e in paired]
    ep = [math.degrees(e.epsi) for e in paired]
    cf = [e.confidence for e in paired]
    sane = 100.0 * sum(1 for x in w if abs(x - TRUE_WIDTH_MM) <= WIDTH_TOL_MM) / len(w)
    sd_ey = statistics.pstdev(ey) if len(ey) > 1 else 0.0

    print(f"\n  frames {len(ests)}, paired {pct_p:.0f}%, width-sane {sane:.0f}%")
    print(f"  reported ey {statistics.mean(ey):+.1f} mm (sd {sd_ey:.1f}) vs a true "
          f"{a.true_ey:+.0f}  ->  error {statistics.mean(ey) - a.true_ey:+.1f} mm")
    print(f"  width {statistics.mean(w):.1f} mm (sd {statistics.pstdev(w):.1f}), "
          f"epsi {statistics.mean(ep):+.2f} deg, confidence {statistics.mean(cf):.3f}")
    if sd_ey > 12.0:
        print("  ** sd_ey above 12 mm on a parked car — something moved. Re-take this")
        print("     point with your hands off and nothing leaning on the chassis. **")

    if keep:
        import cv2
        fdir = out.parent / (out.stem + "_frames") / f"ey_{int(a.true_ey):+05d}"
        fdir.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(keep):
            cv2.imwrite(str(fdir / f"{i:03d}.png"), f)
        print(f"  kept {len(keep)} frames in {fdir}  "
              "(so this point can be replayed against a corrected estimator)")

    new = not out.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a", newline="") as fh:
        wr = csv.writer(fh)
        if new:
            wr.writerow(COLS)
        wr.writerow([f"{a.true_ey:.1f}", len(ests), f"{pct_p:.1f}", f"{sane:.1f}",
                     f"{statistics.mean(w):.1f}", f"{statistics.pstdev(w):.1f}",
                     f"{statistics.mean(ey):.1f}", f"{sd_ey:.1f}",
                     f"{statistics.mean(ep):.2f}",
                     f"{statistics.pstdev(ep) if len(ep) > 1 else 0.0:.2f}",
                     f"{statistics.mean(cf):.3f}",
                     time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())])
    _report(_load(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
