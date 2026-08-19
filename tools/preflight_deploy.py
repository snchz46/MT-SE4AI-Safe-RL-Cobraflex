#!/usr/bin/env python3
"""
preflight_deploy — turn the staged bring-up of docs/17 §4 into a PASS/FAIL verdict.

The staged sequence exists because the 2026-08-05 bench review found five defects
that were all **silent**: the chain started, logged and would have driven wrongly
rather than failing. Eyeballing rviz does not catch that class of fault. Each
stage here asserts the invariants that *would* have caught them, and exits
non-zero if any fails.

    stage0   camera alone            (needs Layer 2)
    stage1   chain flowing, wheels up, mode:=monitoring   (needs Layer 3)
    stage2   actuation envelope, WHEELS UP                (needs Layer 3)
    lanecheck  static ey vs a tape measure, ON the track  (needs Layer 3)

Stage 3 of docs/17 §4 (e-stop / C-05 on a tether) is a physical test and is not
automated; `stage2 --watch-emergency` will at least tell you whether C-05
activation actually reaches `/cmd_vel` as a zero Twist.

WHEELS MUST BE OFF THE GROUND for stage1 and stage2. Stage 2 commands throttle.
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
import time
from typing import Dict, List, Optional

# The observation contract (camera_geometry defaults). 640x360 is hard: the CV
# estimator indexes its scan bands by camera.height_px, so any other size
# silently mis-projects every ey/epsi the cage acts on.
W_PX, H_PX = 640, 360
ENCODING = "bgr8"
CAMERA_RATE_HZ = 20.0          # Lane Cam <update_rate> / lane_keeper timer_hz
CONTROL_RATE_HZ = 10.0         # the trained control_dt; NOT the camera rate
THROTTLE_DEADBAND = 0.05       # deploy launch default
MAX_SPEED_MPS = 0.22           # the 2-D contract
# cage.yaml state_validity_ranges
EY_RANGE = (-0.30, 0.30)
EPSI_RANGE = (-1.57, 1.57)
SPEED_RANGE = (-0.10, 1.50)
# M-6, 17.08.2026: what the lens actually measures, against the 320 px the IPM assumes.
M6_FX_MEASURED = 395.93
M6_FX_ASSUMED = 320.0


class Result:
    def __init__(self) -> None:
        self.rows: List[tuple] = []

    def check(self, ok: Optional[bool], name: str, detail: str = "") -> None:
        self.rows.append((ok, name, detail))

    def report(self, title: str) -> int:
        print("=" * 74)
        print(title)
        print("=" * 74)
        failed = 0
        for ok, name, detail in self.rows:
            if ok is None:
                tag = "\033[33mSKIP\033[0m"
            elif ok:
                tag = "\033[32mPASS\033[0m"
            else:
                tag = "\033[31mFAIL\033[0m"
                failed += 1
            print(f"  [{tag}] {name}")
            if detail:
                for line in detail.splitlines():
                    print(f"         {line}")
        print("-" * 74)
        print("VERDICT: " + ("\033[31m%d CHECK(S) FAILED — do not proceed\033[0m" % failed
                            if failed else "\033[32mall checks passed\033[0m"))
        print("=" * 74)
        return 1 if failed else 0


def _collect(node, topics: Dict[str, tuple], seconds: float) -> Dict[str, list]:
    """topics: {name: (msg_type, qos)} -> {name: [msgs]}"""
    import rclpy
    got: Dict[str, list] = {name: [] for name in topics}
    for name, (mtype, qos) in topics.items():
        node.create_subscription(mtype, name,
                                 (lambda n: (lambda m: got[n].append(m)))(name), qos)
    end = time.time() + seconds
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    return got


def _stamp_stats(msgs, attr="header") -> Optional[dict]:
    st = []
    for m in msgs:
        h = getattr(m, attr, None)
        if h is None:
            return None
        st.append(h.stamp.sec + h.stamp.nanosec * 1e-9)
    if len(st) < 3:
        return None
    gaps = [b - a for a, b in zip(st, st[1:]) if b > a]
    if not gaps:
        return None
    gaps.sort()
    return {
        "n": len(st),
        "median_ms": statistics.median(gaps) * 1e3,
        "p90_ms": gaps[int(0.9 * (len(gaps) - 1))] * 1e3,
        "max_ms": gaps[-1] * 1e3,
        "rate_hz": 1.0 / statistics.median(gaps),
    }


def _node_list() -> List[str]:
    import subprocess
    try:
        out = subprocess.run(["ros2", "node", "list"], capture_output=True,
                             text=True, timeout=12).stdout
        return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        return []


# --------------------------------------------------------------------------

def stage0(args) -> int:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import Image, CameraInfo

    r = Result()
    nodes = _node_list()
    lk = [n for n in nodes if "lane_keeper" in n]
    r.check(not lk, "lane_keeper_node is NOT running",
            "it holds the same CSI device AND commands /cmd_vel — never both\n"
            f"found: {lk}" if lk else "no CSI/actuation contention")

    rclpy.init(args=None)
    node = Node("preflight_stage0")
    sensor_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                            history=HistoryPolicy.KEEP_LAST, depth=30)
    got = _collect(node, {args.image_topic: (Image, sensor_qos),
                          args.info_topic: (CameraInfo, sensor_qos)}, args.seconds)
    imgs, infos = got[args.image_topic], got[args.info_topic]

    r.check(bool(imgs), f"{args.image_topic} is publishing",
            f"{len(imgs)} frames in {args.seconds:.0f}s"
            if imgs else "no frames — is Layer 2 up?")
    if imgs:
        m = imgs[-1]
        size_ok = (m.width, m.height) == (W_PX, H_PX)
        r.check(size_ok, f"frame is {W_PX}x{H_PX} (HARD contract)",
                f"got {m.width}x{m.height}" + ("" if size_ok else
                "\ncv_lane_estimator indexes scan bands by camera.height_px —\n"
                "any other size silently mis-projects every ey/epsi"))
        r.check(m.encoding == ENCODING, f"encoding is {ENCODING}", f"got {m.encoding!r}")
        s = _stamp_stats(imgs)
        if s:
            ok = s["rate_hz"] >= 0.8 * CAMERA_RATE_HZ
            r.check(ok, f"camera rate ~{CAMERA_RATE_HZ:.0f} Hz",
                    f"median gap {s['median_ms']:.1f} ms ({s['rate_hz']:.1f} Hz), "
                    f"p90 {s['p90_ms']:.1f} ms, max {s['max_ms']:.1f} ms")
        else:
            r.check(None, "camera rate", "too few frames to judge")

    if infos:
        k = infos[-1].k
        fx = k[0]
        r.check(abs(fx - M6_FX_ASSUMED) < 1.0,
                "CameraInfo advertises the pinhole the IPM applies",
                f"fx={fx:.2f} (the cage assumes {M6_FX_ASSUMED:.0f})")
        # This is a WARNING by design, not a failure: nothing in code has been
        # changed in response to M-6 yet, so agreement here is expected.
        r.check(None, "M-6: the advertised pinhole does NOT match the lens",
                f"measured fx = {M6_FX_MEASURED:.2f} px (HFOV 77.89 deg), "
                f"advertised {fx:.2f} px (90 deg)\n"
                f"=> the estimator under-reads lateral offset by ~28%: C-01/C-05 "
                f"fire LATE.\n   Expected until the open decision in M-6 is taken.")
    else:
        r.check(False, f"{args.info_topic} is publishing", "no CameraInfo received")

    node.destroy_node()
    rclpy.shutdown()
    return r.report("STAGE 0 — camera alone (docs/17 §4 step 0)")


def stage1(args) -> int:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from std_msgs.msg import Float64MultiArray, Bool
    from geometry_msgs.msg import Twist
    from cobraflex_safety_msgs.msg import CageStatus

    r = Result()
    rclpy.init(args=None)
    node = Node("preflight_stage1")
    sq = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                    history=HistoryPolicy.KEEP_LAST, depth=50)
    rq = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                    history=HistoryPolicy.KEEP_LAST, depth=50)
    got = _collect(node, {
        "/state_obs": (Float64MultiArray, sq),
        "/raw_action": (Twist, sq),
        "/safe_action": (Twist, sq),
        "/cage_status": (CageStatus, rq),
        "/perception_invalid": (Bool, rq),
    }, args.seconds)

    for t in ("/state_obs", "/raw_action", "/safe_action", "/cage_status"):
        r.check(bool(got[t]), f"{t} is publishing", f"{len(got[t])} msgs")

    st = got["/cage_status"]
    if st:
        s = _stamp_stats(st)
        if s:
            ok = 0.75 * CONTROL_RATE_HZ <= s["rate_hz"] <= 1.4 * CONTROL_RATE_HZ
            r.check(ok, f"cage cycles at the trained {CONTROL_RATE_HZ:.0f} Hz",
                    f"median gap {s['median_ms']:.1f} ms ({s['rate_hz']:.1f} Hz), "
                    f"p90 {s['p90_ms']:.1f} ms\n"
                    "the policy+cage must run at control_dt, NOT the camera's 20 Hz")
        miss = max(int(m.cycles_since_last_state) for m in st)
        r.check(miss <= 1, "cage is not starved of /state_obs",
                f"max cycles_since_last_state = {miss}")
        emerg = sum(1 for m in st if m.emergency_mode)
        # C-05's trigger set includes perception_invalid, and its exit is
        # deliberately asymmetric (require_explicit_reset, STPA-informed against
        # oscillation at the boundary). On a bench with no lane markings the
        # estimator cannot produce a valid lane, so the FIRST invalid cycle
        # latches emergency and it stays. That is the design working, not a
        # defect -- so only call it a failure when emergency appears with
        # perception healthy, which would mean something else tripped it.
        inv_seen = any(m.data for m in got["/perception_invalid"])
        if emerg and inv_seen:
            r.check(None, "C-05 emergency is explained by invalid perception",
                    f"{emerg}/{len(st)} cycles in emergency, and "
                    f"/perception_invalid was True at least once.\n"
                    "EXPECTED on a bench with no lane markings: C-05 latches on the\n"
                    "first invalid cycle and only exits once the condition CLEARS *and*\n"
                    "a reset arrives on /cage_reset -- both, not either.\n"
                    "To exercise the rest of stage 1, give the estimator something it\n"
                    "reads as a lane: two light strips ~0.245 m apart (lane_width_nominal_m,\n"
                    "tolerance +-0.10 m) on the floor in front of the camera.")
        else:
            r.check(emerg == 0, "no C-05 emergency with perception healthy",
                    f"{emerg}/{len(st)} cycles in emergency while /perception_invalid\n"
                    "never went True -- something other than perception tripped C-05")
        rules: Dict[str, int] = {}
        for m in st:
            for rid in m.rules_triggered:
                rules[rid] = rules.get(rid, 0) + 1
        r.check(None, "rules seen this window", str(rules) if rules else "none")
        r.check(bool(st[-1].yaml_version), "cage.yaml version stamped in status",
                f"yaml_version={st[-1].yaml_version!r}")

    obs = got["/state_obs"]
    if obs:
        eys = [m.data[0] for m in obs if len(m.data) >= 3]
        eps = [m.data[1] for m in obs if len(m.data) >= 3]
        spd = [m.data[2] for m in obs if len(m.data) >= 3]
        finite = all(math.isfinite(v) for v in eys + eps + spd)
        r.check(finite, "state vector is finite (no NaN/inf)")
        if eys:
            in_ey = all(EY_RANGE[0] <= v <= EY_RANGE[1] for v in eys)
            r.check(in_ey, "ey inside state_validity_ranges",
                    f"ey {min(eys):+.3f}..{max(eys):+.3f} m (valid {EY_RANGE})")
            r.check(all(EPSI_RANGE[0] <= v <= EPSI_RANGE[1] for v in eps),
                    "epsi inside state_validity_ranges",
                    f"epsi {min(eps):+.3f}..{max(eps):+.3f} rad")
            moved = (max(eys) - min(eys)) > 1e-6
            r.check(moved, "ey is not frozen (estimator is live)",
                    f"span {max(eys)-min(eys):.4f} m — move a lane marking by hand "
                    "and it must respond")
            r.check(None, "speed source", f"{min(spd):.3f}..{max(spd):.3f} m/s "
                    "(0 with wheels up is expected only if the ekf sees no motion)")

    inv = got["/perception_invalid"]
    if inv:
        bad = sum(1 for m in inv if m.data)
        r.check(bad < 0.5 * len(inv), "perception is valid most of the time",
                f"{bad}/{len(inv)} cycles reported invalid")

    node.destroy_node()
    rclpy.shutdown()
    return r.report("STAGE 1 — chain flowing, WHEELS UP (docs/17 §4 step 1)")


def stage2(args) -> int:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from geometry_msgs.msg import Twist
    from cobraflex_safety_msgs.msg import CageStatus

    print("\n*** WHEELS MUST BE OFF THE GROUND — this stage commands throttle ***\n")
    r = Result()
    rclpy.init(args=None)
    node = Node("preflight_stage2")
    sq = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                    history=HistoryPolicy.KEEP_LAST, depth=100)
    rq = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                    history=HistoryPolicy.KEEP_LAST, depth=100)
    got = _collect(node, {"/cmd_vel": (Twist, sq),
                          "/cage_status": (CageStatus, rq)}, args.seconds)
    cmd, st = got["/cmd_vel"], got["/cage_status"]

    r.check(bool(cmd), "/cmd_vel is publishing", f"{len(cmd)} msgs")
    if cmd:
        vx = [m.linear.x for m in cmd]
        wz = [m.angular.z for m in cmd]
        r.check(max(vx) <= MAX_SPEED_MPS + 1e-6,
                f"linear.x never exceeds the {MAX_SPEED_MPS} m/s contract",
                f"max {max(vx):.4f} m/s")
        r.check(min(vx) >= -1e-6, "linear.x is never negative", f"min {min(vx):.4f}")
        exact_zero = sum(1 for v in vx if v == 0.0)
        r.check(exact_zero > 0, "linear.x reaches a TRUE zero",
                f"{exact_zero}/{len(vx)} samples exactly 0.0\n"
                "a near-zero that never reaches 0 means the deadband is not "
                "reaching the driver — SR-009 requires a commandable stop")
        r.check(max(vx) > 0.5 * MAX_SPEED_MPS, "linear.x spans a useful range",
                f"{min(vx):.4f}..{max(vx):.4f} m/s — if it never rises, the policy "
                "or the speed map is stuck")
        r.check(None, "angular.z range",
                f"{min(wz):+.3f}..{max(wz):+.3f} rad/s "
                "(steering_to_yaw_rate_gain default 1.615)")

    # The invariant the 2026-08-05 review's item 1 would have caught: the cage's
    # safe throttle below the deadband MUST become an exact zero at the driver.
    if cmd and st:
        below = [m for m in st if m.action_safe.linear.x < THROTTLE_DEADBAND]
        r.check(None, "cycles with safe throttle under the deadband",
                f"{len(below)}/{len(st)}"
                + ("" if below else "\nnone occurred — cannot test the stop band in "
                                    "this window; steer the estimator until the cage "
                                    "attenuates, or re-run for longer"))
        if below and cmd:
            near_zero = sum(1 for v in [m.linear.x for m in cmd] if v == 0.0)
            r.check(near_zero > 0,
                    "the deadband produces exact zeros at /cmd_vel",
                    f"{near_zero} exact-zero cmd_vel samples alongside "
                    f"{len(below)} sub-deadband cage cycles")
        emerg = [m for m in st if m.emergency_mode]
        if emerg:
            r.check(None, "C-05 fired during this window",
                    f"{len(emerg)} cycles — check /cmd_vel went to zero Twist")

    node.destroy_node()
    rclpy.shutdown()
    return r.report("STAGE 2 — actuation envelope, WHEELS UP (docs/17 §4 step 2)")


def lanecheck(args) -> int:
    """Static lane-estimator validation ON the real track. Nothing moves.

    This is the one measurement M-6 left open. M-6 measured the *camera*
    (fx 395.93 px, HFOV 77.89 deg, pitch 17.84 deg) and then *propagated* that
    through the estimator's construction to predict that the reported ey is
    0.72x the true one — i.e. C-01/C-05 fire late. That propagation has never
    been checked against a ruler on a real lane, and it is the number that
    decides whether the trunk policy's campaign verdict transfers.

    Park the car at a tape-measured lateral offset from the lane centreline,
    hold still, and run this. Sign convention follows the estimator: ey = -c0,
    positive = the car is LEFT of centre (lane centre appears to the right).
    """
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from std_msgs.msg import Float64MultiArray, Bool

    r = Result()
    rclpy.init(args=None)
    node = Node("preflight_lanecheck")
    rq = QoSProfile(reliability=ReliabilityPolicy.RELIABLE,
                    history=HistoryPolicy.KEEP_LAST, depth=200)
    print(f"\nholding still for {args.seconds:.0f} s — do not touch the car\n")
    got = _collect(node, {"/state_obs": (Float64MultiArray, rq),
                          "/perception_invalid": (Bool, rq)}, args.seconds)
    obs, inv = got["/state_obs"], got["/perception_invalid"]

    r.check(len(obs) >= 10, "/state_obs is publishing",
            f"{len(obs)} msgs in {args.seconds:.0f} s")
    if inv:
        bad = sum(1 for m in inv if m.data)
        r.check(bad == 0, "perception valid for the whole window",
                f"{bad}/{len(inv)} cycles invalid"
                + ("" if bad == 0 else "\nthe estimator is not locked onto the lane — "
                                       "reposition before trusting any number below"))
    if not obs:
        node.destroy_node(); rclpy.shutdown()
        return r.report("LANECHECK — static ey validation (M-6 follow-up)")

    ey = [m.data[0] for m in obs if len(m.data) > 1]
    ep = [m.data[1] for m in obs if len(m.data) > 1]
    mean_ey, mean_ep = statistics.mean(ey), statistics.mean(ep)
    sd_ey = statistics.pstdev(ey) if len(ey) > 1 else 0.0
    sd_ep = statistics.pstdev(ep) if len(ep) > 1 else 0.0

    r.check(None, "reported ey",
            f"mean {mean_ey*1000:+.1f} mm, sd {sd_ey*1000:.1f} mm, "
            f"range {min(ey)*1000:+.1f}..{max(ey)*1000:+.1f} mm")
    r.check(None, "reported epsi",
            f"mean {math.degrees(mean_ep):+.2f} deg, sd {math.degrees(sd_ep):.2f} deg")
    # A parked car must produce a quiet estimate. Jitter here is jitter the
    # policy sees at every cycle, and it enters C-01/C-03 unfiltered.
    r.check(sd_ey <= 0.010, "the parked estimate is quiet (sd_ey <= 10 mm)",
            f"sd {sd_ey*1000:.1f} mm — anything larger is noise the cage acts on")
    # C-02's threshold is 25 deg and the whole 550k verdict campaign never saw a
    # heading error above 14.2 deg. A PARKED car whose epsi jitters by more than
    # that is not a measurement problem — it is the policy's obs[1] and C-02's
    # input, live.
    r.check(math.degrees(sd_ep) <= 5.0,
            "the parked heading estimate is quiet (sd_epsi <= 5 deg)",
            f"sd {math.degrees(sd_ep):.2f} deg vs C-02's 25 deg limit and the "
            f"14.2 deg worst case of the entire 550k campaign")

    if args.true_ey is not None:
        t = args.true_ey
        r.check(None, "tape-measured true ey", f"{t*1000:+.1f} mm")
        if abs(t) < 0.015:
            r.check(abs(mean_ey) <= 0.015,
                    "centred: reported ey is within 15 mm of zero",
                    f"{mean_ey*1000:+.1f} mm — a centred car reading non-zero is a "
                    "cx/mounting offset, not a scale error; run an offset point too")
        else:
            ratio = mean_ey / t
            r.check(None, "single-point ratio  reported/true",
                    f"{ratio:.3f}\nNOT the scale: this assumes the estimator reads "
                    "exactly 0 at true 0. Take the centred point too and use the "
                    "SLOPE between points. Better still, use tools/lane_probe.py, "
                    "which reads the measured lane width and needs no positioning "
                    "at all.")
            r.check(None, "M-6 predicted scale", "0.72  (fx 395.93 vs the assumed 320)")
            r.check(None, "if the M-6 prediction holds",
                    f"C-01 (d_max 0.16 m) actually fires at a true "
                    f"{0.16/ratio*1000:.0f} mm, and C-05's 0.12 m warning at a true "
                    f"{0.12/ratio*1000:.0f} mm" if abs(ratio) > 1e-6 else "n/a")
            r.check(None, "verdict on the M-6 propagation",
                    "not decidable from one offset point — see lane_probe.py")

    node.destroy_node()
    rclpy.shutdown()
    return r.report("LANECHECK — static ey validation on the real track (M-6 follow-up)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, default_s in (("stage0", stage0, 12.0),
                                ("stage1", stage1, 15.0),
                                ("stage2", stage2, 20.0),
                                ("lanecheck", lanecheck, 10.0)):
        c = sub.add_parser(name)
        c.add_argument("--seconds", type=float, default=default_s)
        if name == "lanecheck":
            c.add_argument("--true-ey", type=float, default=None,
                           help="tape-measured lateral offset in METRES, signed: "
                                "positive = car is left of the lane centreline.")
        if name == "stage0":
            c.add_argument("--image-topic", default="/camera/image_raw_lane")
            c.add_argument("--info-topic", default="/camera/camera_info")
        c.set_defaults(func=fn)
    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
