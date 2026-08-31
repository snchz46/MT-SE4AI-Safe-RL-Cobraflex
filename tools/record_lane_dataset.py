#!/usr/bin/env python3
"""
record_lane_dataset — capture a LABELLED real-lane dataset for closing the
appearance gap, without the I/O load that crashed the Jetson on 18.08.2026.

Why not `ros2 bag record`. Raw 640x360 bgr8 at 20 Hz is 13.8 MB/s to eMMC, and
the 18.08 attempt ran it alongside the full deploy chain (ZED wrapper, torch,
rviz, estimator, cage). The board crashed. Three fixes, all here:

  * PNG instead of raw           ~200 kB vs 691 kB per frame
  * 5 Hz instead of 20           a hand-swept car at 20 Hz is 4x redundant
  * labels computed INLINE       so /state_obs need not be recorded at all, and
                                 the deploy chain need not run at all
                                 -> ~1 MB/s, about 14x less than the bag

Only the camera is required. No deploy launch, no policy node, no cage.

Why labels come free. `CvLaneEstimator` at its shipped thresholds reads this
circuit's lane width to within 2.9 mm of a ruler over 95.4% of frames (M-7 §3),
so it is a trustworthy teacher for real imagery. Each saved frame gets its ey,
epsi, lane width, pairing state and failure reason written to `labels.csv`,
flushed per row — a crash costs at most the frame in flight.

THE POINT OF THE LIVE COVERAGE BARS. The 18.08 recording spanned the lane but
90% of its frames sat within +/-72 mm of centre, so it contains almost no
examples of *returning* from an excursion — the exact behaviour the trunk policy
lacks. This tool prints, live, how many frames you have in each |ey| band and
on each side, so you can see where you are short and move there. Chasing the
bars is the job; the centre fills itself in as you cross it.

Target band: sweep to about +/-80 mm. That is NOT the lane edge and NOT C-01's
160 mm d_max — it is where the estimator stops pairing the right two lines on
this track (see BANDS below for the measurement). Frames further out are
rejected by the width gate rather than saved with a confident wrong label, and
`rejects.csv` records every one so the wall stays visible instead of looking
like the tool ignoring you.

    python3 tools/record_lane_dataset.py --out experiments/physical/datasets/lane_01
"""
from __future__ import annotations

import argparse
import csv
import math
import select
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "src" / "cobraflex_rl",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# |ey| bands in mm. Revised 18.08.2026 after the first pass measured where the
# LABELS stop being trustworthy, which is much closer in than where the cage
# acts: of 1205 hand-swept frames, the share whose measured lane width lands
# within 40 mm of the ruler's 250 runs 92% at 0-40 mm, 29% at 40-80, and 6% at
# 80-120 — where 4 lines are in view and the estimator systematically pairs the
# wrong two (184 mm, sd 24; not noise, and not explained by heading). So the
# usable capture range is about +/-80 mm, NOT the +/-160 mm of C-01's d_max.
# The 80-120 band is kept to make that wall visible, not to be filled.
BANDS = [(0, 30), (30, 55), (55, 80), (80, 120)]
TARGET_PER_BAND_PER_SIDE = 200   # ~40 s of 5 Hz sweeping in each


def _bar(n: int, target: int, width: int = 18) -> str:
    f = min(1.0, n / target) if target else 0.0
    done = int(f * width)
    return "[" + "#" * done + "." * (width - done) + "]"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, help="output directory (created)")
    p.add_argument("--rate", type=float, default=5.0, help="frames saved per second")
    p.add_argument("--seconds", type=float, default=0.0, help="0 = until Ctrl-C")
    p.add_argument("--image-topic", default="camera/image_raw_lane")
    p.add_argument("--white-sat-max", type=int, default=-1,
                   help="-1 keeps the D-43 default 30 (best on this circuit, M-7 §3)")
    p.add_argument("--true-width", type=float, default=0.250,
                   help="ruler-measured lane width, metres, centre-to-centre. Used "
                        "as a LABEL SANITY GATE: a frame whose measured width is "
                        "off by more than --width-tol is discarded, because that is "
                        "the signature of the estimator pairing the wrong two lines "
                        "(typically the adjacent lane once you sweep far enough out) "
                        "and returning a confident, wrong ey.")
    p.add_argument("--width-tol", type=float, default=0.040,
                   help="tolerance for the gate above, metres. The 18.08 capture had "
                        "only 44%% of frames inside +/-40 mm.")
    p.add_argument("--rectify", default="",
                   help="M-6 calibration JSON (experiments/calibration/"
                        "M6_results.json). STRONGLY RECOMMENDED: the deployed "
                        "estimator runs rectified, and §8.3's parked A/B measured "
                        "perception-invalid 45%% -> 5.5%% and C-01 102 -> 0 firings "
                        "from rectification alone. Capturing unrectified labels a "
                        "dataset with an estimator that is NOT the one driving.")
    p.add_argument("--save-unpaired", action="store_true",
                   help="also save frames the estimator could not pair. Off by "
                        "default: those frames have no trustworthy label, and a "
                        "training set is worth less with wrong labels than with "
                        "fewer. They are still counted in the summary.")
    # --- true-position capture (D-78) -------------------------------------
    # The accuracy question D-76 left open — WHICH line pair is the true one at
    # each point of the track — cannot be answered by a label the estimator
    # produced itself. These three arguments make the recording self-scoring:
    # the operator declares the offset the car is being pushed at, and marks
    # arc-length anchors as it passes numbered floor stations. Both are omitted
    # by default, so the appearance-gap use of this tool is unchanged.
    p.add_argument("--no-frames", action="store_true",
                   help="write labels.csv only, no PNGs. THE RIGHT CHOICE FOR A "
                        "MEASUREMENT LAP: every statistic score_lane_capture.py "
                        "computes comes from the CSV, so 20 Hz costs ~400 kB per "
                        "lap instead of ~600 MB — and the eMMC pressure that "
                        "crashed the Jetson on 18.08 does not recur. Use frames "
                        "only for the appearance-gap datasets, which need them.")
    p.add_argument("--true-ey", type=float, default=None,
                   help="TRUE lateral offset (m, + = car LEFT of centre) the car "
                        "is being pushed at for this run, tape-measured. Recorded "
                        "per frame as ground truth. Push a CONSTANT offset per run "
                        "and repeat the lap at 0, +/-0.06, +/-0.10 m.")
    p.add_argument("--station-arc", default="",
                   help="comma-separated arc-lengths (m) of the numbered floor "
                        "stations, in pass order, e.g. '0,4.8,9.6,14.4'. Press "
                        "ENTER as the car's reference point passes each one; the "
                        "CSV then carries a true arc-length per frame, which is "
                        "what makes the closed-loop integral of D-75 computable "
                        "without any odometry.")
    p.add_argument("--perimeter", type=float, default=19.28,
                   help="circuit perimeter (m) for the closed-loop check; "
                        "19.28 measured on the physical track (docs/17 8)")
    a = p.parse_args(argv)
    station_arc = [float(x) for x in a.station_arc.split(",") if x.strip()]

    import rclpy
    import cv2
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from cobraflex_rl.camera_pipeline import decode_image
    from cobraflex_rl.cv_lane_estimator import CvLaneEstimator, CvLaneEstimatorConfig

    out = Path(a.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    csv_path = out / "labels.csv"
    new = not csv_path.exists()
    fh = open(csv_path, "a", newline="")
    wr = csv.writer(fh)
    if new:
        # line_c0_m: the ground-frame intercept of EVERY detected line, not just
        # the selected pair. It is the input to the pair-selection decision, and
        # recording it is what lets the pairing be replayed and scored offline on
        # a host with no frames and no Jetson (D-77). It was absent from this
        # tool while `circuit_export/labels.csv` carried it, so that column came
        # from an untracked variant — the provenance gap this closes.
        # curvature_1pm + s_m + true_ey_m: the D-75/D-76 acceptance tests.
        wr.writerow(["frame", "stamp_s", "ey_m", "epsi_rad", "lane_width_m",
                     "paired", "n_lines", "confidence", "reason", "line_c0_m",
                     "curvature_1pm", "true_ey_m", "station", "s_m"])
        fh.flush()

    rej_path = out / "rejects.csv"
    rej_new = not rej_path.exists()
    rfh = open(rej_path, "a", newline="")
    rwr = csv.writer(rfh)
    if rej_new:
        rwr.writerow(["stamp_s", "why", "ey_m", "epsi_rad", "lane_width_m",
                      "n_lines", "confidence", "reason"])
        rfh.flush()

    cfg = {}
    if a.white_sat_max >= 0:
        cfg["white_sat_max"] = a.white_sat_max
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**cfg))

    # Rectification, built once so a bad path fails here and not mid-sweep. The
    # remap is the same call `cv_lane_estimator_node` makes, BORDER_REPLICATE
    # included: a black wedge in the near-field corner reads as a dark object
    # rather than as more road.
    rect_maps = None
    if a.rectify:
        from cobraflex_rl.camera_geometry import (
            CameraModel, rectification_maps_from_calibration,
        )
        rect_maps = rectification_maps_from_calibration(a.rectify, CameraModel())
        print(f"rectifying with {a.rectify}")
    else:
        print("WARNING: capturing UNRECTIFIED. The deployed estimator rectifies, "
              "so these labels come from a different estimator than the one that "
              "drives. Pass --rectify experiments/calibration/M6_results.json.")

    rclpy.init(args=None)
    node = Node("record_lane_dataset")
    holder = {"msg": None}
    node.create_subscription(Image, a.image_topic,
                             lambda m: holder.__setitem__("msg", m),
                             qos_profile_sensor_data)

    counts = {(lo, hi, side): 0 for lo, hi in BANDS for side in ("L", "R")}
    n_saved = n_unpaired = n_badwidth = 0
    station = 0
    # A TRUE-POSITION run is a MEASUREMENT, not a training set, and the two want
    # opposite things from the reject filters. The appearance-gap use drops
    # unpaired and bad-width frames because a wrong label poisons training. An
    # accuracy measurement needs exactly those frames: they ARE the pairing
    # failures being quantified, and dropping them reproduces the selection bias
    # that made the 31.08 event frames unusable (docs/17 10.6). So --true-ey
    # forces the complete population through.
    measuring = a.true_ey is not None
    if measuring:
        print(f"\nTRUE-POSITION RUN: true_ey = {a.true_ey*1000:+.1f} mm")
        print("  every frame is kept, INCLUDING unpaired and bad-width ones —")
        print("  they are the failures being measured. This dataset is evidence,")
        print("  NOT a training set; do not feed it to the appearance-gap work.")
        if not a.no_frames:
            print("  NOTE: --no-frames is usually what you want here — the whole")
            print("  score comes from the CSV, and 20 Hz with PNGs is ~600 MB/lap.")
        if station_arc:
            print(f"  {len(station_arc)} stations declared; press ENTER at each.")
        else:
            print("  no --station-arc given: arc length will be unavailable, so the")
            print("  D-75 closed-loop integral cannot be scored from this run.")
    last_reject = None
    idx = len(list((out / "frames").glob("*.png")))
    period = 1.0 / max(0.1, a.rate)
    t_next = time.time()
    t_stop = time.time() + a.seconds if a.seconds > 0 else float("inf")
    t_print = 0.0

    print(f"\nsaving to {out}  ({a.rate:g} Hz, PNG, labels flushed per frame)")
    print("sweep the car SLOWLY side to side; fill the bars, the centre fills itself")
    print("target is about +/-160 mm — lane edge plus a little, NOT the track edge\n")
    try:
        while rclpy.ok() and time.time() < t_stop:
            rclpy.spin_once(node, timeout_sec=0.02)
            # Station marking: ENTER on stdin advances the arc-length anchor.
            # Non-blocking, so a run with no stations behaves exactly as before.
            # The operator presses as the car's reference point passes each
            # numbered floor mark; no odometry, no extra terminal, no hardware.
            if station_arc and sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.readline()
                if station < len(station_arc):
                    station += 1
                    print(f"  ** STATION {station}/{len(station_arc)} at "
                          f"s = {station_arc[station-1]:.2f} m")
                    if station == len(station_arc):
                        print("     (last station — lap closed; Ctrl-C when done)")
                else:
                    print("  ** all stations already marked; press ignored")
            now = time.time()
            if now < t_next:
                continue
            msg = holder["msg"]
            if msg is None:
                continue
            t_next = now + period
            try:
                frame = decode_image(msg.data, int(msg.height), int(msg.width),
                                     msg.encoding, int(msg.step))
            except ValueError:
                continue
            if rect_maps is not None:
                frame = cv2.remap(frame, rect_maps[0], rect_maps[1],
                                  cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE)
            e = est.estimate(frame)
            paired = bool(e.ok and e.reason != "single_line" and e.n_lines >= 2)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            if not paired:
                n_unpaired += 1
                rwr.writerow([f"{stamp:.3f}", "unpaired", f"{e.ey:.5f}",
                              f"{e.epsi:.5f}", f"{e.lane_width:.5f}", e.n_lines,
                              f"{e.confidence:.3f}", e.reason]); rfh.flush()
                if not (a.save_unpaired or measuring):
                    continue
            elif abs(e.lane_width - a.true_width) > a.width_tol:
                # Confidently wrong, not merely uncertain: the pair is not the two
                # lines of this lane. Keeping it would poison the training set.
                n_badwidth += 1
                rwr.writerow([f"{stamp:.3f}", "bad_width", f"{e.ey:.5f}",
                              f"{e.epsi:.5f}", f"{e.lane_width:.5f}", e.n_lines,
                              f"{e.confidence:.3f}", e.reason]); rfh.flush()
                last_reject = (e.ey * 1000.0, e.lane_width * 1000.0, e.n_lines)
                if not measuring:
                    continue
            name = f"{idx:06d}.png"
            if not a.no_frames:
                cv2.imwrite(str(out / "frames" / name), frame)
            wr.writerow([name, f"{stamp:.3f}", f"{e.ey:.5f}", f"{e.epsi:.5f}",
                         f"{e.lane_width:.5f}", int(paired), e.n_lines,
                         f"{e.confidence:.3f}", e.reason,
                         ";".join(f"{c0:.5f}" for c0, _ in e.line_fits),
                         f"{e.curvature:.5f}",
                         "" if a.true_ey is None else f"{a.true_ey:.5f}",
                         station,
                         "" if not station else f"{station_arc[station-1]:.3f}"])
            fh.flush()
            idx += 1
            n_saved += 1
            if paired:
                mm = e.ey * 1000.0
                side = "L" if mm >= 0 else "R"
                for lo, hi in BANDS:
                    if lo <= abs(mm) < hi:
                        counts[(lo, hi, side)] += 1
                        break
            if now - t_print > 2.0:
                t_print = now
                print(f"\n  saved {n_saved}   skipped: unpaired {n_unpaired}, "
                      f"bad-width {n_badwidth}   latest ey {e.ey*1000:+6.1f} mm "
                      f"(w {e.lane_width*1000:.0f})")
                if last_reject:
                    print(f"    last REJECT: ey {last_reject[0]:+.0f} mm, width "
                          f"{last_reject[1]:.0f} mm, {last_reject[2]} lines seen"
                          "  <- if this tracks you, that offset is past the")
                    print("       estimator's reliable range; stop going further out")
                for lo, hi in BANDS:
                    l = counts[(lo, hi, "L")]
                    r = counts[(lo, hi, "R")]
                    tag = ("  <- labels unreliable past here, expect rejects"
                           if lo >= 80 else "")
                    print(f"    {lo:3d}-{hi:3d} mm   L {_bar(l, TARGET_PER_BAND_PER_SIDE)} {l:4d}"
                          f"   R {_bar(r, TARGET_PER_BAND_PER_SIDE)} {r:4d}{tag}")
    except KeyboardInterrupt:
        pass
    finally:
        fh.close()
        rfh.close()
        node.destroy_node()
        rclpy.shutdown()
        print(f"\n=== {out} ===")
        print(f"  frames saved         {n_saved}")
        print(f"  skipped, unpaired    {n_unpaired}")
        print(f"  skipped, bad width   {n_badwidth}"
              "   (wrong lines paired — would have been confidently mislabelled)")
        tot = sum(counts.values())
        for lo, hi in BANDS:
            l, r = counts[(lo, hi, "L")], counts[(lo, hi, "R")]
            print(f"  {lo:3d}-{hi:3d} mm   left {l:5d}   right {r:5d}"
                  + ("   THIN" if min(l, r) < TARGET_PER_BAND_PER_SIDE // 2 else ""))
        if tot:
            outer = sum(counts[(lo, hi, s)] for lo, hi in BANDS if lo >= 55 for s in "LR")
            print(f"  share at |ey| >= 55 mm: {100.0*outer/tot:.1f}%"
                  "   (recovery behaviour lives here; the 18.08 first pass had ~13%)")
            L = sum(counts[(lo, hi, "L")] for lo, hi in BANDS)
            R = sum(counts[(lo, hi, "R")] for lo, hi in BANDS)
            print(f"  left/right balance: {L} / {R}"
                  + ("   SKEWED — the policy already biases left; fix this"
                     if max(L, R) > 1.5 * max(1, min(L, R)) else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
