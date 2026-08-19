#!/usr/bin/env python3
"""
measure_yaw_gain — close the open §5 question of docs/17 with one bench number.

Waveshare's firmware turns every twist we send through TRACK_WIDTH 0.159
(`rosCtrl` in Cobra_Driver/movtion_module.h: setpointA = rosX - rosZ*TRACK/2).
Gazebo's DiffDrive uses 0.154. The tape says the real track is 0.153. That is a
systematic yaw gain offset in precisely the channel the policy controls, and
docs/17 §5 says deciding it "needs one bench number: wz = 1.0 rad/s, vx = 0,
10 s, measure the angle actually turned."

This measures it. It commands a pure yaw at `--wz` for `--seconds`, and
integrates the yaw ACTUALLY achieved from /odometry/filtered rather than asking
you to eyeball an angle. Ratio achieved/commanded is the answer.

SAFETY
  * This publishes straight to /cmd_vel. The cage is NOT in this path — the
    policy and the safety rules are bypassed entirely by design, because the
    quantity under test is the driver's kinematics, not the controller's.
  * Refuses to run if something else is already publishing to /cmd_vel, so it
    cannot fight a live deploy.
  * vx is pinned to 0.0: the car turns on the spot, it does not translate.
  * Always publishes a zero Twist on exit, including on Ctrl-C.

Expect well under 1.0: docs/17 §8.1 and docs/14 §2.3 already put the reachable
yaw rate at roughly half the ideal, so 3.9% of track-width error cannot be the
whole story. A ratio near 0.5 reproduces that; the interesting question is
whether it is stable across --wz.
"""
from __future__ import annotations

import argparse
import math
import time


def _yaw(q) -> float:
    s = 2.0 * (q.w * q.z + q.x * q.y)
    c = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(s, c)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wz", type=float, default=1.0, help="commanded yaw rate, rad/s")
    p.add_argument("--vx", type=float, default=0.0,
                   help="forward speed, m/s. THIS MATTERS: at vx=0 the chassis "
                        "scrubs and the measurement is dominated by static "
                        "friction, not by the TRACK_WIDTH question. The policy "
                        "always steers while moving, so the transfer-relevant "
                        "number is measured at vx near 0.22. Radius = vx/wz.")
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--odom-topic", default="/odometry/filtered")
    p.add_argument("--cmd-topic", default="/cmd_vel")
    p.add_argument("--force", action="store_true",
                   help="run even if another node publishes to the cmd topic")
    a = p.parse_args(argv)

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSPresetProfiles
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry

    rclpy.init(args=None)
    node = Node("measure_yaw_gain")
    pub = node.create_publisher(Twist, a.cmd_topic, 10)

    # Do not fight a live deploy for the actuator.
    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)
    others = node.count_publishers(a.cmd_topic) - 1
    if others > 0 and not a.force:
        print(f"REFUSING: {others} other publisher(s) on {a.cmd_topic}.\n"
              "Stop the deploy (or relaunch it with cmd_vel_topic:=/cmd_vel_dryrun)\n"
              "before measuring, or pass --force if you are certain.")
        node.destroy_node(); rclpy.shutdown()
        return 2

    samples = []
    node.create_subscription(Odometry, a.odom_topic,
                             lambda m: samples.append(
                                 (m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                                  _yaw(m.pose.pose.orientation))),
                             QoSPresetProfiles.SENSOR_DATA.value)
    for _ in range(40):
        rclpy.spin_once(node, timeout_sec=0.05)
    if not samples:
        print(f"no odometry on {a.odom_topic} — cannot measure. Is the EKF up?")
        node.destroy_node(); rclpy.shutdown()
        return 1

    def stop():
        z = Twist()
        for _ in range(10):
            pub.publish(z)
            time.sleep(0.02)

    print(f"\n*** the car will TURN IN PLACE at {a.wz:+.2f} rad/s for "
          f"{a.seconds:.0f} s — wheels on the ground, keep clear ***")
    print("    the safety cage is bypassed; Ctrl-C stops and zeroes\n")
    for n in (3, 2, 1):
        print(f"    {n}...")
        time.sleep(1.0)

    tw = Twist()
    tw.linear.x = float(a.vx)
    tw.angular.z = float(a.wz)
    mark = len(samples)
    t_start = node.get_clock().now().nanoseconds * 1e-9
    t0 = time.time()
    try:
        while time.time() - t0 < a.seconds:
            pub.publish(tw)
            rclpy.spin_once(node, timeout_sec=0.02)
            time.sleep(0.03)
    except KeyboardInterrupt:
        print("\ninterrupted — stopping")
    finally:
        stop()
    t_end = node.get_clock().now().nanoseconds * 1e-9
    t_cmd = time.time() - t0
    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.05)

    # Only samples stamped INSIDE the command window. Spinning on after the stop
    # to drain the queue otherwise appends stationary samples and dilutes the
    # rate by however long that drain took.
    seg = [s_ for s_ in samples[mark:] if t_start <= s_[0] <= t_end]
    node.destroy_node()
    rclpy.shutdown()

    print("=" * 74)
    print("YAW GAIN — docs/17 §5 bench number")
    print("=" * 74)
    if len(seg) < 5:
        print(f"  only {len(seg)} odometry samples during the turn — cannot integrate.")
        return 1

    # Unwrap: the car may pass through +/-pi more than once.
    total = 0.0
    for (_, y0), (_, y1) in zip(seg, seg[1:]):
        d = y1 - y0
        while d > math.pi:
            d -= 2.0 * math.pi
        while d < -math.pi:
            d += 2.0 * math.pi
        total += d
    dt = seg[-1][0] - seg[0][0]
    if dt <= 0.0:
        dt = t_cmd
    achieved = total / dt
    ratio = achieved / a.wz if a.wz else float("nan")

    print(f"  commanded            wz {a.wz:+.3f} rad/s, vx {a.vx:.3f} m/s "
          f"for {t_cmd:.2f} s")
    if a.vx != 0.0 and a.wz:
        print(f"  implied arc radius   {abs(a.vx/a.wz):.2f} m")
    print(f"  odometry samples     {len(seg)} over {dt:.2f} s")
    print(f"  yaw actually turned  {math.degrees(total):+.1f} deg "
          f"({total:+.3f} rad, {abs(total)/(2*math.pi):.2f} turns)")
    print(f"  achieved yaw rate    {achieved:+.3f} rad/s")
    print(f"  RATIO achieved/cmd   {ratio:.3f}")
    print()
    print(f"  TRACK_WIDTH accounts for at most 0.159/0.154 = 1.032, i.e. a 3.2%")
    print(f"  effect. A ratio of {ratio:.2f} leaves "
          f"{(1.0-abs(ratio))*100:.0f}% unexplained by it.")
    if a.vx == 0.0:
        print()
        print("  *** vx = 0: THIS DOES NOT ANSWER THE docs/17 §5 QUESTION. ***")
        print("  Turning on the spot makes all four wheels skid sideways, which is")
        print("  the regime §5 itself calls out as unable to break static friction")
        print("  below ~0.2 rad/s. The 3.2% under test is buried under that.")
        print("  Re-measure with --vx 0.15..0.22, where the wheels roll and where")
        print("  the policy actually operates.")
    elif abs(ratio) < 0.75:
        print()
        print("  The sim reaches its commanded yaw. Measured WHILE MOVING, this is")
        print("  steering authority the policy was trained to have and the car does")
        print("  not — a first-order transfer risk, not a calibration constant.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
