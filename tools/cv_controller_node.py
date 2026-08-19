#!/usr/bin/env python3
"""
cv_controller_node — drive the physical car with the classical CV lane-keeper,
BEHIND THE SAFETY CAGE, as the control arm for the RL policy.

Why this exists. On 18.08.2026 the 2-D PPO trunk was shown not to transfer to the
physical circuit (M-7 §6, D-71): its steering keeps the right sign but is swamped
by a constant left bias 2.1x the whole lane-dependent swing. That is a statement
about the *policy*. It becomes a much stronger thesis statement once paired with
its control arm — the deterministic pure-pursuit controller of docs/12, reading
the same D-43 estimator, on the same track, through the same cage.

`cobraflex_rl.cv_lane_controller.CVLaneController` is a library with no console
script (it is used inside the Gazebo eval harness). This is a thin ROS node
around it, deliberately kept OUT of the colcon package so it needs no rebuild in
a field session. If it proves out, promote it into `cobraflex_rl` properly.

    camera/image_raw_lane -> [this node] -> /raw_action -> cage_ros_node -> ...

It publishes exactly what `rl_policy_node` publishes, so the rest of the deployed
chain — cage, vehicle_control, driver — is untouched and the cage is fully in the
loop.

THE TWO UNIT CONVERSIONS, spelled out because this is precisely the class of
silent defect docs/17 §6b catalogues (three of four defects found there were unit
or domain errors that ran and drove wrongly rather than failing):

  1. Throttle. `/raw_action.linear.x` is the cage's NORMALISED throttle u in
     [0, 1], not a speed and not the policy's symmetric a in [-1, 1]. With
     `speed_map:=linear_2d` the deployed chain applies `speed = max_speed * u`,
     so u = speed_mps / max_speed_mps.
  2. Steering. `CVLaneController.compute` returns a YAW RATE in rad/s.
     `/raw_action.angular.z` carries the cage's normalised steering, which
     `vehicle_control_node` multiplies by `steering_to_yaw_rate_gain`. In
     simulation that gain is 0.8, which is the mapping the cage's C-01/C-02
     corrections were calibrated against — so the normalised steering is
     `angular_z / 0.8`. On hardware the deploy default 1.615 then compensates the
     chassis' measured 0.4954 scrub deficit, and 0.4954 * 1.615 = 0.8 restores
     the commanded yaw. Do NOT divide by 1.615 here: that would compensate twice.

SAFETY
  * Refuses to start if anything else publishes /raw_action (i.e. if
    `rl_policy_node` is running). Launch the deploy with `policy:=false` if it
    has one, or stop the deploy and run the estimator+cage stack separately.
  * `--dry-run` publishes to /raw_action_dryrun instead, so the whole controller
    can be characterised with nothing actuating. Sweep the car across the lane by
    hand and regress steering against `ey`: that is the exact test the RL policy
    failed (M-7 §6), so it makes the control arm a like-for-like comparison.

STATUS: WRITTEN 18.08.2026, NEVER RUN AGAINST A FRAME. The session ended in a
crash before it could be tested. Its startup path executes; its control loop has
not. Treat every number it produces as unverified until that changes.
  * Publishes nothing on a frame with no usable lane, exactly like
    `rl_policy_node`: the cage's missing-action path is the intended response,
    not a zero command.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "src" / "cobraflex_rl",):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

SIM_STEERING_TO_YAW_GAIN = 0.8   # see conversion 2 above; NOT the deploy's 1.615


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--speed", type=float, default=0.15,
                   help="commanded speed in m/s before the cage (default 0.15; the "
                        "2-D contract's ceiling is 0.22)")
    p.add_argument("--max-speed", type=float, default=0.22,
                   help="must match the deploy's max_speed_mps, or the throttle "
                        "domain is wrong")
    p.add_argument("--rate", type=float, default=10.0,
                   help="control rate; 10 Hz is the trained control_dt and the rate "
                        "C-06's per-cycle steering budget is sized for")
    p.add_argument("--image-topic", default="camera/image_raw_lane")
    p.add_argument("--raw-action-topic", default="/raw_action")
    p.add_argument("--seconds", type=float, default=0.0,
                   help="stop after N seconds (0 = run until Ctrl-C). A bounded run "
                        "is the safe way to try this on the ground the first time.")
    p.add_argument("--dry-run", action="store_true",
                   help="publish to /raw_action_dryrun; nothing actuates")
    p.add_argument("--white-sat-max", type=int, default=-1,
                   help="-1 keeps the D-43 default 30, which M-7 §3 measured as the "
                        "best value on this circuit (95.4%% paired, lane width within "
                        "2.9 mm of a ruler). Only override with circuit-wide evidence.")
    p.add_argument("--white-val-min", type=int, default=-1)
    p.add_argument("--look-ahead", type=float, default=0.40)
    p.add_argument("--pursuit-gain", type=float, default=1.0)
    p.add_argument("--max-angular-z", type=float, default=0.90)
    p.add_argument("--heading-fit-mode", default="joint_pair_quadratic")
    p.add_argument("--heading-gain", type=float, default=1.6)
    p.add_argument("--heading-temporal-window", type=int, default=4)
    a = p.parse_args(argv)

    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from sensor_msgs.msg import Image
    from cobraflex_rl.camera_pipeline import decode_image
    from cobraflex_rl.cv_lane_controller import CVLaneController
    from cobraflex_rl.cv_lane_estimator import CvLaneEstimator, CvLaneEstimatorConfig

    topic = "/raw_action_dryrun" if a.dry_run else a.raw_action_topic

    cfg = dict(heading_fit_mode=a.heading_fit_mode, heading_gain=a.heading_gain,
               heading_temporal_window=a.heading_temporal_window)
    if a.white_sat_max >= 0:
        cfg["white_sat_max"] = a.white_sat_max
    if a.white_val_min >= 0:
        cfg["white_val_min"] = a.white_val_min
    est = CvLaneEstimator(config=CvLaneEstimatorConfig(**cfg))
    ctrl = CVLaneController(speed=a.speed, estimator=est,
                            look_ahead_m=a.look_ahead, pursuit_gain=a.pursuit_gain,
                            max_angular_z=a.max_angular_z)

    rclpy.init(args=None)
    node = Node("cv_controller_node")
    pub = node.create_publisher(Twist, topic, 10)
    frame_holder = {"msg": None}
    node.create_subscription(Image, a.image_topic,
                             lambda m: frame_holder.__setitem__("msg", m),
                             qos_profile_sensor_data)

    for _ in range(20):
        rclpy.spin_once(node, timeout_sec=0.05)
    others = node.count_publishers(topic) - 1
    if others > 0:
        print(f"REFUSING: {others} other publisher(s) on {topic} — rl_policy_node is\n"
              "probably running. Two controllers on /raw_action interleave silently.")
        node.destroy_node(); rclpy.shutdown()
        return 2

    u = max(0.0, min(1.0, a.speed / a.max_speed)) if a.max_speed > 0 else 0.0
    print(f"\ncv_controller_node -> {topic}")
    print(f"  speed {a.speed:.3f} m/s of max {a.max_speed:.3f}  =>  cage throttle u = {u:.3f}")
    print(f"  steering published as yaw/{SIM_STEERING_TO_YAW_GAIN} (the sim gain the cage "
          f"was calibrated against)")
    print(f"  look-ahead {a.look_ahead:.2f} m, pursuit gain {a.pursuit_gain:.2f}, "
          f"|wz| <= {a.max_angular_z:.2f} rad/s")
    print(f"  estimator: white_sat_max={cfg.get('white_sat_max','default')}, "
          f"{a.heading_fit_mode}/{a.heading_gain}")
    if a.dry_run:
        print("  DRY RUN — nothing actuates.")
    print("  Ctrl-C to stop.\n")

    period = 1.0 / max(1e-3, a.rate)
    n_pub = n_skip = 0
    t_last = time.time()
    reasons: dict = {}
    t_stop = time.time() + a.seconds if a.seconds > 0 else float("inf")
    try:
        while rclpy.ok() and time.time() < t_stop:
            rclpy.spin_once(node, timeout_sec=0.01)
            now = time.time()
            if now - t_last < period:
                continue
            t_last = now
            msg = frame_holder["msg"]
            if msg is None:
                continue
            try:
                frame = decode_image(msg.data, int(msg.height), int(msg.width),
                                     msg.encoding, int(msg.step))
            except ValueError:
                continue
            wz, ok = ctrl.compute(frame)
            if not ok:
                n_skip += 1
                r = ctrl.dbg.get("reason", "?")
                reasons[r] = reasons.get(r, 0) + 1
                continue          # cage's missing-action path, as rl_policy_node does
            t = Twist()
            t.linear.x = u
            t.angular.z = max(-1.0, min(1.0, wz / SIM_STEERING_TO_YAW_GAIN))
            pub.publish(t)
            n_pub += 1
            if n_pub % 20 == 0:
                d = ctrl.dbg
                print(f"  ey {d.get('ey',0)*1000:+6.1f} mm  y_L {d.get('y_l',0)*1000:+7.1f} mm"
                      f"  -> wz {wz:+.3f} rad/s  steer {t.angular.z:+.3f}"
                      f"   (pub {n_pub}, skip {n_skip})")
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\npublished {n_pub}, skipped {n_skip}"
              + (f"  reasons: {reasons}" if reasons else ""))
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
