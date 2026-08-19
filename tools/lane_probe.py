#!/usr/bin/env python3
"""
lane_probe — read the CV lane estimator's INTERNALS on the real track.

`/state_obs` carries only [ey, epsi, speed, curvature, half-ey, half+ey, 1] and
`half` there is the *nominal* road width, a constant. The quantity that settles
the M-6 question is not published at all: `CvLaneEstimate.lane_width`, the lane
separation the estimator actually measures, `(left.c0 - right.c0)*cos(heading)`.

That number is the scale factor, measured directly:

    measured_lane_width / true_lane_width  ==  the ey scale

and unlike an offset sweep it has **no yaw confound and no positioning error** —
you do not have to place the car anywhere in particular, or square it, or trust
a tape held against a moving chassis. You measure the painted lane once with a
ruler and read the ratio.

This runs a SECOND estimator in-process on the same camera topic, with the live
node's parameters. It changes nothing: no rebuild, no relaunch, the deployed
chain is untouched and never sees this process.

It also histograms `CvLaneEstimate.reason`, which is what explains dropped
cycles. Note `lane_width_tol_m = 0.10` around a nominal 0.245 m: a pair is
REJECTED unless its measured separation lands in [0.145, 0.345] m. If the scale
really is ~0.66 then a true 0.245 m lane measures ~0.162 m — inside that window,
but with only 17 mm to spare. That is a testable explanation for intermittent
`state_available == False` on a parked car.

    python3 tools/lane_probe.py --true-width 0.245
"""
from __future__ import annotations

import argparse
import collections
import math
import statistics
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "src" / "cobraflex_rl",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=12.0)
    p.add_argument("--image-topic", default="camera/image_raw_lane")
    p.add_argument("--true-width", type=float, default=None,
                   help="ruler-measured lane width in METRES (inner edge to inner "
                        "edge of the two lines, the same convention the estimator "
                        "fits). This is what turns the reading into a scale.")
    p.add_argument("--node", default="/cv_lane_estimator_node",
                   help="live node to copy parameters from; '' to use defaults.")
    a = p.parse_args(argv)

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from cobraflex_rl.camera_pipeline import decode_image
    from cobraflex_rl.cv_lane_estimator import CvLaneEstimator, CvLaneEstimatorConfig

    # Mirror the live node's config when there IS a live node. When there is not
    # — e.g. recording with only csi_camera_node up — fall back to the shipped
    # defaults and say so. An earlier version let `ros2 param get` fail silently
    # and passed the resulting empty string through as heading_fit_mode='',
    # which the estimator rejects at construction.
    VALID_MODES = {"near_secant", "joint_pair_quadratic"}
    cfg_kwargs = {}
    node_present = False
    if a.node:
        import subprocess
        try:
            nodes = subprocess.run(["ros2", "node", "list"], capture_output=True,
                                   text=True, timeout=12).stdout.split()
            node_present = a.node in nodes
        except Exception:
            node_present = False
        if node_present:
            want = {"heading_fit_mode": str, "heading_gain": float,
                    "heading_bias_rad": float, "heading_temporal_window": int,
                    "white_sat_max": int, "white_val_min": int}
            for key, cast in want.items():
                try:
                    out = subprocess.run(["ros2", "param", "get", a.node, key],
                                         capture_output=True, text=True,
                                         timeout=10).stdout
                    val = out.strip().split(":", 1)[-1].strip().strip("\'\"")
                    if not val:
                        continue
                    v = cast(val)
                    if key == "heading_fit_mode" and v not in VALID_MODES:
                        continue
                    if key in ("white_sat_max", "white_val_min") and v < 0:
                        continue          # -1 means "not set" — keep the default
                    cfg_kwargs[key] = v
                except Exception:
                    continue
    if node_present and cfg_kwargs:
        print(f"estimator config mirrored from {a.node}:")
        for k, v in sorted(cfg_kwargs.items()):
            print(f"    {k} = {v!r}")
    else:
        print(f"no live {a.node} — using the shipped CvLaneEstimatorConfig defaults"
              if a.node else "using the shipped CvLaneEstimatorConfig defaults")
        print("    (M-7 §3 measured those defaults as the best values on this circuit)")

    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**cfg_kwargs))
    rclpy.init(args=None)
    node = Node("lane_probe")
    frames = []
    node.create_subscription(Image, a.image_topic,
                             lambda m: frames.append(m), qos_profile_sensor_data)

    print(f"\nsampling {a.image_topic} for {a.seconds:.0f} s — hold still\n")
    ests = []
    end = time.time() + a.seconds
    seen = 0
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        while frames:
            m = frames.pop(0)
            seen += 1
            try:
                frame = decode_image(m.data, int(m.height), int(m.width),
                                     m.encoding, int(m.step))
            except ValueError:
                continue
            ests.append(est.estimate(frame))

    node.destroy_node()
    rclpy.shutdown()

    print("=" * 74)
    print("LANE PROBE — estimator internals on the real track")
    print("=" * 74)
    print(f"  frames received      {seen}")
    print(f"  estimates computed   {len(ests)}")
    if not ests:
        print("  nothing to report — is the camera publishing?")
        return 1

    ok = [e for e in ests if e.ok]
    # CRITICAL: `_single_line_estimate` reports lane_width = self._lane_width_ema,
    # an EMA seeded with lane_width_nominal_m and updated ONLY when a pair is
    # found. With no pair in the whole window it never moves, so the "measured"
    # width is the NOMINAL CONSTANT wearing a measurement's clothes — sd exactly
    # 0.0 is the tell. Scale must come from paired frames only.
    paired = [e for e in ok if e.reason != "single_line" and e.n_lines >= 2]
    single = [e for e in ok if e.reason == "single_line"]
    print(f"  usable (ok=True)     {len(ok)}/{len(ests)}  "
          f"({100.0*len(ok)/len(ests):.0f}%)")
    print(f"    of those, PAIRED   {len(paired)}   (the only ones that measure a width)")
    print(f"    single-line path   {len(single)}"
          + ("   <-- degraded: ey is inferred from the NOMINAL half-lane, which in "
             "a mis-scaled projection is a systematic bias, not just noise"
             if single else ""))
    reasons = collections.Counter(e.reason for e in ests if not e.ok)
    if reasons:
        print("\n  why the rest failed:")
        for r, n in reasons.most_common():
            print(f"    {n:4d}  {r or '(no reason given)'}")
    if not ok:
        print("\n  no usable estimate — nothing below can be computed.")
        return 1

    def stats(vals):
        return (statistics.mean(vals),
                statistics.pstdev(vals) if len(vals) > 1 else 0.0,
                min(vals), max(vals))

    if not paired:
        print("\n  NO PAIRED FRAME IN THIS WINDOW — no lane width was measured.")
        print("  Every number below would come from the single-line fallback, where")
        print("  lane_width is the nominal constant and ey is inferred from it.")
        print("  Reposition so BOTH lines of one lane are in view, then re-run.")
        ey_m, ey_sd, _, _ = stats([e.ey for e in ok])
        ep_m, ep_sd, _, _ = stats([e.epsi for e in ok])
        print(f"\n  (degraded-path ey   {ey_m*1000:+.1f} mm  sd {ey_sd*1000:.1f})")
        print(f"  (degraded-path epsi {math.degrees(ep_m):+.2f} deg  "
              f"sd {math.degrees(ep_sd):.2f})")
        print("=" * 74)
        return 1

    w_m, w_sd, w_lo, w_hi = stats([e.lane_width for e in paired])
    ey_m, ey_sd, _, _ = stats([e.ey for e in paired])
    ep_m, ep_sd, _, _ = stats([e.epsi for e in paired])
    cf_m, _, cf_lo, _ = stats([e.confidence for e in paired])
    nl = collections.Counter(e.n_lines for e in paired)

    print(f"\n  measured lane_width  {w_m*1000:7.1f} mm   sd {w_sd*1000:.1f}   "
          f"range {w_lo*1000:.1f}..{w_hi*1000:.1f}")
    print(f"  ey                   {ey_m*1000:+7.1f} mm   sd {ey_sd*1000:.1f}")
    print(f"  epsi                 {math.degrees(ep_m):+7.2f} deg  "
          f"sd {math.degrees(ep_sd):.2f}")
    print(f"  confidence           {cf_m:7.3f}      min {cf_lo:.3f}")
    print(f"  n_lines              " + ", ".join(f"{k}:{v}" for k, v in sorted(nl.items())))

    # The pair-separation gate that silently drops frames.
    NOMINAL, TOL = 0.245, 0.10
    print(f"\n  pair-separation gate accepts [{(NOMINAL-TOL)*1000:.0f}, "
          f"{(NOMINAL+TOL)*1000:.0f}] mm around the {NOMINAL*1000:.0f} mm nominal")
    margin = min(w_m - (NOMINAL - TOL), (NOMINAL + TOL) - w_m)
    print(f"  measured width sits {margin*1000:.0f} mm from the nearest edge of it"
          + ("  <-- thin; this is what drops cycles" if margin < 0.03 else ""))

    if w_sd == 0.0 and len(paired) > 3:
        print("\n  REFUSING to report a scale: lane_width has sd exactly 0.0 over "
              f"{len(paired)} frames.\n  A real measurement jitters. This is a "
              "constant leaking through.")
        print("=" * 74)
        return 1

    MIN_PAIRED = 20
    if a.true_width is not None and len(paired) < MIN_PAIRED:
        print(f"\n  REFUSING to report a scale from {len(paired)} paired frame(s) "
              f"(need {MIN_PAIRED}).\n  A handful of frames scraped out of a mostly "
              "degraded window are the frames\n  that happened to squeak past the "
              "separation gate — they are biased LOW\n  by selection, not "
              "representative. Reposition for a mostly-paired window.")
        print("=" * 74)
        return 1

    if a.true_width is not None:
        scale = w_m / a.true_width
        print("\n" + "-" * 74)
        print(f"  ruler-measured lane width   {a.true_width*1000:.1f} mm")
        print(f"  SCALE  measured/true        {scale:.3f}")
        print("  expected                     0.98-1.01  (M-7 §3/§4: 252.9 mm over a")
        print("                               recorded circuit, 245.9 mm live — the IPM")
        print("                               reads lateral distance correctly. M-6's")
        print("                               propagated 0.72 is RETRACTED, see D-71.)")
        if 0.93 <= scale <= 1.06:
            print("  => in family. The estimator is reading the lane correctly here.")
        elif scale < 0.93:
            print(f"  => reading {100*(1-scale):.0f}% NARROW. Most likely a local detection "
                  "problem\n     (glare, a dash gap, a pose where the far line is "
                  "clipped), not geometry.\n     Check n_lines and confidence above, and "
                  "move before trusting it.")
        else:
            print(f"  => reading {100*(scale-1):.0f}% WIDE — the pair is probably not the two "
                  "lines of\n     one lane. Check n_lines above.")
        if scale > 0.05:
            print(f"\n  with this scale the cage's thresholds land at TRUE distances:")
            for name, thr in (("C-01 d_max 0.16 m", 0.16),
                              ("C-05 d_warning 0.12 m", 0.12),
                              ("state_validity 0.30 m", 0.30)):
                print(f"    {name:24s} fires at {thr/scale*1000:6.0f} mm true")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
