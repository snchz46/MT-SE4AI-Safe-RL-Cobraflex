#!/usr/bin/env python3
"""
measure_yaw_authority — why does the achieved yaw rate saturate at ~0.10 rad/s?

docs/17 §13.4 measured the plant on the 31.08 bare-policy run: commanded yaw
against achieved yaw over 5327 moving cycles, ratio 0.85 at small commands
collapsing to 0.18 above 0.5 rad/s, achieved yaw flat at ~0.10 rad/s. At the
deployed 0.22 m/s that is R_min = 2.2 m against the ~1.0 m the tightest curve of
ODD-3 needs, and it is the whole explanation of the two reproducible departures.

§13.4 named three candidates and proposed reading a front-wheel angle with a
protractor. **That test does not apply to this platform**: the URDF carries four
`continuous` wheel joints and a DiffDrive plugin, and the chassis is skid-steer —
there is no steering angle to read. The yaw comes from a left/right wheel-speed
differential, so the discriminator has to be measured there:

    the driver clamps       -> the WHEEL DIFFERENTIAL saturates with the command
    the wheels scrub/slip   -> the differential stays linear while the ACHIEVED
                               yaw saturates

This sweeps a list of commanded yaw rates and reports both, side by side.

RUN IT TWICE.
  1. `--mode blocks`  car on blocks, wheels free. Odometry is meaningless here
     and is reported as such; the wheel differential is the driver's intent,
     uncontaminated by the floor. This half alone answers "does the driver
     clamp?".
  2. `--mode ground`  car on the floor, clear space, same sweep. Both columns
     are meaningful. Differential linear + achieved yaw flat = slip.

WHERE THE NUMBERS COME FROM
  `/cobraflex/wheel_speeds` is a Twist that does NOT carry speeds: the driver
  packs the firmware's `odl`/`odr` into linear.x / linear.y, and those are
  CUMULATIVE per-side odometers in integer centimetres (docs/17 §5). This tool
  therefore differentiates them; the quantisation is 1 cm per side, which is why
  each step runs for several seconds rather than one.

SAFETY
  * Publishes straight to /cmd_vel. The cage is NOT in this path, by design:
    the quantity under test is the driver's kinematics, not the controller's.
  * Refuses to run if anything else publishes to /cmd_vel, so it cannot fight a
    live deploy. --force overrides.
  * Zero Twist on exit, including on Ctrl-C, and between every step.
"""
from __future__ import annotations

import argparse
import math
import time

# --------------------------------------------------------------------------
# Pure arithmetic, kept ROS-free so `--selftest` can exercise it off-vehicle.
# --------------------------------------------------------------------------


def _yaw(q) -> float:
    s = 2.0 * (q.w * q.z + q.x * q.y)
    c = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(s, c)


def integrate_yaw(samples) -> tuple:
    """(yaw turned in rad, seconds) from [(t, yaw)], unwrapped across +/-pi."""
    if len(samples) < 2:
        return 0.0, 0.0
    total = 0.0
    for (_, y0), (_, y1) in zip(samples, samples[1:]):
        d = y1 - y0
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
        total += d
    return total, samples[-1][0] - samples[0][0]


def differential_rate(samples) -> tuple:
    """(d(odr-odl)/dt, d(odr+odl)/2dt, seconds) from [(t, odl, odr)].

    Units follow the input: the firmware's odometers are centimetres, so the
    returned rates are cm/s. First and last sample only — these are cumulative
    counters, so the endpoints are the measurement and anything in between is
    quantisation noise.
    """
    if len(samples) < 2:
        return float("nan"), float("nan"), 0.0
    t0, l0, r0 = samples[0]
    t1, l1, r1 = samples[-1]
    dt = t1 - t0
    if dt <= 0.0:
        return float("nan"), float("nan"), 0.0
    return ((r1 - r0) - (l1 - l0)) / dt, ((r1 - r0) + (l1 - l0)) / (2.0 * dt), dt


def linearity(rows) -> dict:
    """Is column `y` proportional to column `wz` across the sweep?

    rows: [(wz, y)] with y already sign-corrected. Returns the per-step ratios
    and the ratio of the largest command's ratio to the smallest's — 1.0 means
    perfectly linear, well under 1.0 means the channel saturates.
    """
    good = [(w, y) for w, y in rows
            if w and y == y and abs(w) > 1e-9]  # y == y drops NaN
    if len(good) < 2:
        return {"ratios": [], "fade": float("nan")}
    ratios = [(w, y / w) for w, y in good]
    first = ratios[0][1]
    last = ratios[-1][1]
    fade = (last / first) if first else float("nan")
    return {"ratios": ratios, "fade": fade}


def _selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond

    turned, dt = integrate_yaw([(0.0, 3.0), (1.0, -3.0)])  # wraps through +pi
    check("integrate_yaw unwraps across pi", abs(turned - 0.2832) < 1e-3 and dt == 1.0)
    turned, _ = integrate_yaw([(0.0, 0.0), (1.0, 0.5), (2.0, 1.0)])
    check("integrate_yaw accumulates", abs(turned - 1.0) < 1e-9)
    d, f, dt = differential_rate([(0.0, 0.0, 0.0), (2.0, 10.0, 30.0)])
    check("differential_rate: (30-10)/2 = 10 cm/s", abs(d - 10.0) < 1e-9)
    check("differential_rate: forward (30+10)/4 = 10 cm/s", abs(f - 10.0) < 1e-9)
    check("differential_rate: window", dt == 2.0)
    lin = linearity([(0.1, 1.0), (0.2, 2.0), (0.4, 4.0)])
    check("linearity: proportional -> fade 1.0", abs(lin["fade"] - 1.0) < 1e-9)
    lin = linearity([(0.1, 1.0), (0.8, 2.0)])  # saturating
    check("linearity: saturating -> fade 0.25", abs(lin["fade"] - 0.25) < 1e-9)
    check("linearity: tolerates NaN", linearity([(0.1, float("nan"))])["ratios"] == [])
    print("\nselftest:", "OK" if ok else "FAILURES")
    return 0 if ok else 1


# --------------------------------------------------------------------------


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n")[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=("blocks", "ground"), default="blocks",
                   help="blocks = wheels free, odometry meaningless but the "
                        "wheel differential is the driver's intent; "
                        "ground = both columns meaningful.")
    p.add_argument("--wz-list", default="0.1,0.2,0.3,0.5,0.8",
                   help="commanded yaw rates, rad/s, comma separated. The "
                        "31.08 bins, so the results line up with §13.4.")
    p.add_argument("--vx", type=float, default=0.168,
                   help="forward speed, m/s. Default is the mean moving speed "
                        "of the run §13.4 analysed, so the comparison holds. "
                        "vx=0 makes all four wheels scrub and measures static "
                        "friction instead — see measure_yaw_gain's warning.")
    p.add_argument("--seconds", type=float, default=6.0,
                   help="per step. The odometers quantise at 1 cm/side, so "
                        "short steps measure quantisation.")
    p.add_argument("--settle", type=float, default=1.0,
                   help="seconds of command before the measurement window "
                        "opens, so the step response is not in the average.")
    p.add_argument("--wheels-topic", default="/cobraflex/wheel_speeds")
    p.add_argument("--odom-topic", default="/odometry/filtered")
    p.add_argument("--cmd-topic", default="/cmd_vel")
    p.add_argument("--force", action="store_true",
                   help="run even if another node publishes to the cmd topic")
    p.add_argument("--selftest", action="store_true",
                   help="exercise the arithmetic off-vehicle and exit")
    a = p.parse_args(argv)

    if a.selftest:
        return _selftest()

    wz_list = [float(x) for x in a.wz_list.split(",") if x.strip()]
    if not wz_list:
        print("--wz-list is empty")
        return 2

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSPresetProfiles
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry

    rclpy.init(args=None)
    node = Node("measure_yaw_authority")
    pub = node.create_publisher(Twist, a.cmd_topic, 10)

    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)
    others = node.count_publishers(a.cmd_topic) - 1
    if others > 0 and not a.force:
        print(f"REFUSING: {others} other publisher(s) on {a.cmd_topic}.\n"
              "Stop the deploy before measuring, or pass --force if you are certain.")
        node.destroy_node(); rclpy.shutdown()
        return 2

    wheels: list = []
    odom: list = []
    node.create_subscription(
        Twist, a.wheels_topic,
        lambda m: wheels.append((time.time(), m.linear.x, m.linear.y)), 10)
    node.create_subscription(
        Odometry, a.odom_topic,
        lambda m: odom.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                               _yaw(m.pose.pose.orientation))),
        QoSPresetProfiles.SENSOR_DATA.value)
    for _ in range(40):
        rclpy.spin_once(node, timeout_sec=0.05)
    if not wheels:
        print(f"no messages on {a.wheels_topic} — is cobraflex_ros_driver up?")
        node.destroy_node(); rclpy.shutdown()
        return 1
    if a.mode == "ground" and not odom:
        print(f"no odometry on {a.odom_topic} — is the EKF up?")
        node.destroy_node(); rclpy.shutdown()
        return 1

    def stop(n=10):
        z = Twist()
        for _ in range(n):
            pub.publish(z)
            time.sleep(0.02)

    where = ("ON BLOCKS — wheels must be FREE and clear"
             if a.mode == "blocks" else
             "ON THE FLOOR — it will drive; keep the space clear")
    print(f"\n*** {where} ***")
    print(f"    {len(wz_list)} steps x {a.settle + a.seconds:.0f} s at "
          f"vx {a.vx:.3f} m/s, wz {wz_list}")
    print("    the safety cage is bypassed; Ctrl-C stops and zeroes\n")
    for n in (3, 2, 1):
        print(f"    {n}...")
        time.sleep(1.0)

    results = []
    try:
        for wz in wz_list:
            tw = Twist()
            tw.linear.x = float(a.vx)
            tw.angular.z = float(wz)
            t_open = None
            w_mark = o_mark = 0
            t0 = time.time()
            while time.time() - t0 < a.settle + a.seconds:
                pub.publish(tw)
                rclpy.spin_once(node, timeout_sec=0.02)
                if t_open is None and time.time() - t0 >= a.settle:
                    t_open = time.time()
                    w_mark, o_mark = len(wheels), len(odom)
                time.sleep(0.03)
            w_seg = wheels[w_mark:]
            o_seg = odom[o_mark:]
            stop(5)
            time.sleep(0.8)  # let it settle before the next step
            diff, fwd, wdt = differential_rate(w_seg)
            turned, odt = integrate_yaw(o_seg)
            achieved = (turned / odt) if odt > 0 else float("nan")
            results.append({"wz": wz, "diff": diff, "fwd": fwd, "n_w": len(w_seg),
                            "achieved": achieved, "n_o": len(o_seg), "dt": wdt})
            print(f"    wz {wz:+.2f} -> differential {diff:+8.2f} cm/s"
                  f"   forward {fwd:6.2f} cm/s"
                  + ("" if a.mode == "blocks" else
                     f"   achieved yaw {achieved:+.3f} rad/s"))
    except KeyboardInterrupt:
        print("\ninterrupted — stopping")
    finally:
        stop()
    node.destroy_node()
    rclpy.shutdown()

    if not results:
        return 1

    print()
    print("=" * 78)
    print(f"YAW AUTHORITY — {a.mode}, vx {a.vx:.3f} m/s   (docs/17 §13.4 follow-up)")
    print("=" * 78)
    print(f"  {'wz cmd':>8} {'differential':>14} {'diff/wz':>10} "
          f"{'achieved yaw':>14} {'ach/wz':>9}")
    for r in results:
        ach = "        n/a" if a.mode == "blocks" else f"{r['achieved']:+14.3f}"
        rat = "      n/a" if a.mode == "blocks" else f"{r['achieved']/r['wz']:9.2f}"
        print(f"  {r['wz']:+8.2f} {r['diff']:+14.2f} {r['diff']/r['wz']:10.1f} "
              f"{ach} {rat}")

    lin_d = linearity([(r["wz"], r["diff"]) for r in results])
    print()
    print(f"  differential fade (last ratio / first): {lin_d['fade']:.2f}")
    if a.mode == "ground":
        lin_a = linearity([(r["wz"], r["achieved"]) for r in results])
        print(f"  achieved-yaw fade                    : {lin_a['fade']:.2f}")
        print(f"  §13.4 measured this fade at 0.18/0.85 = 0.21 on the driven run.")

    print()
    print("  READING IT")
    if lin_d["fade"] == lin_d["fade"] and lin_d["fade"] > 0.8:
        print("  * The wheel differential tracks the command across the sweep, so the")
        print("    driver's /cmd_vel -> RPM conversion is NOT clamping. If the achieved")
        print("    yaw still saturates on the ground, the deficit is SLIP/SCRUB at the")
        print("    contact patch — a property of this floor and these tyres, and not a")
        print("    software constant that can be corrected.")
    else:
        print("  * The wheel differential ITSELF fades with the command, so the ceiling")
        print("    is upstream of the floor: a clamp or a scale error in the driver's")
        print("    /cmd_vel -> RPM conversion, or an RPM limit in the firmware. That is")
        print("    correctable, and it would mean the policy never had the authority it")
        print("    was trained with. Compare against Cobra_Driver/movtion_module.h's")
        print("    setpointA = rosX - rosZ*TRACK_WIDTH/2, *60/(pi*WHEEL_D).")
    if a.mode == "blocks":
        print("  * Re-run with --mode ground to get the second column; on blocks the")
        print("    odometry has nothing to integrate and is reported as n/a.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
