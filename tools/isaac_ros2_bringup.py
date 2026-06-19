"""Bring up the CobraFlex robot in Isaac Sim with a ROS2 bridge, driven by /cmd_vel.

This is the Isaac-Sim equivalent of the Gazebo `robot.gazebo` plugins: it wires a
ROS2 Bridge OmniGraph so the **same** ROS2 nodes used against Gazebo keep working
unchanged. Topic contract reproduced:

    subscribes : /cmd_vel        (geometry_msgs/Twist)  -> drives the 4 wheels
    publishes  : /clock          (rosgraph_msgs/Clock)  -> sim time
                 /odom           (nav_msgs/Odometry)
                 /tf             (tf2_msgs/TFMessage)
                 /joint_states   (sensor_msgs/JointState)

Drive train: a ScriptNode runs the differential-drive kinematics and commands all
four wheels (left = front_left+rear_left, right = front_right+rear_right), matching
the Gazebo DiffDrive plugin (wheel_radius 0.03725 m, wheel_separation 0.154 m).

Usage (source ROS2 first so the bridge talks to your system Jazzy):

    source /opt/ros/jazzy/setup.bash
    ~/isaacsim/python.sh tools/isaac_ros2_bringup.py            # GUI window
    ~/isaacsim/python.sh tools/isaac_ros2_bringup.py --headless # no window
    ~/isaacsim/python.sh tools/isaac_ros2_bringup.py --test     # headless self-test, exits

Then drive it from another sourced terminal exactly like with Gazebo, e.g.:

    ros2 run teleop_twist_keyboard teleop_twist_keyboard
    # or your stack:  ros2 launch cobraflex_rl <your_launch>   (cmd_vel consumer unchanged)
"""
import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--headless", action="store_true", help="run without a window")
parser.add_argument("--test", action="store_true",
                    help="headless: build graph, play a few seconds, report, exit")
parser.add_argument("--turn", action="store_true",
                    help="headless: command a differential turn and report yaw rate")
parser.add_argument("--shot", default="",
                    help="headless: render a top-down snapshot to this PNG and exit")
parser.add_argument("--cam-shot", default="",
                    help="headless: render the lane camera view (at CAM_POSE) to "
                    "this PNG and exit")
args, _ = parser.parse_known_args()
args.test = args.test or args.turn

from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp(
    {"headless": args.headless or args.test or bool(args.shot)
     or bool(args.cam_shot)})

import omni.graph.core as og  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402
from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.ros2.bridge")
simulation_app.update()


def _check_ros2_bridge() -> bool:
    """True if the ROS2 bridge loaded (its OG node types are registered)."""
    try:
        og.Controller.edit(
            {"graph_path": "/_ros2_probe", "evaluator_name": "execution"},
            {og.Controller.Keys.CREATE_NODES: [
                ("c", "isaacsim.ros2.bridge.ROS2Context")]},
        )
        st = omni.usd.get_context().get_stage()
        if st and st.GetPrimAtPath("/_ros2_probe"):
            st.RemovePrim("/_ros2_probe")
        return True
    except Exception:
        return False


if not _check_ros2_bridge():
    print(
        "\n[bringup] ERROR: the Isaac ROS2 bridge failed to load (its OG nodes are\n"
        "  not registered), so the bring-up cannot build the ROS2 graph.\n"
        "  Cause: ROS2 libraries not on the path (e.g. 'libament_index_cpp.so: cannot\n"
        "  open shared object file' / 'ROS2 Bridge startup failed' above).\n\n"
        "  Fix — before launching Isaac, EITHER source your system ROS2:\n"
        "      source /opt/ros/jazzy/setup.bash\n"
        "  OR use Isaac's bundled ROS2 libs:\n"
        "      export ROS_DISTRO=jazzy RMW_IMPLEMENTATION=rmw_fastrtps_cpp\n"
        "      export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:"
        "<isaac_root>/exts/isaacsim.ros2.core/jazzy/lib\n"
        "  then relaunch. (See the bridge error printed above for the exact path.)\n")
    simulation_app.close()
    raise SystemExit(2)

import math  # noqa: E402

import omni.kit.app  # noqa: E402
import omni.kit.commands  # noqa: E402

# Shared physics-scene builder (URDF->USD import, track geometry, robot spawn,
# wheel velocity drives + low-friction materials). Its omni/pxr imports are
# deferred into its functions, so importing the module here — after SimulationApp
# exists — is safe. The in-process RL trainer (tools/isaac_train.py) imports the
# same module so the two paths can never drift on drivetrain/scene parameters.
import isaac_scene  # noqa: E402
from isaac_scene import (  # noqa: E402
    REPO,
    WHEEL_FRICTION,
    WHEEL_JOINTS,
    WHEEL_RADIUS,
    WHEEL_SCRIPT,
    WHEEL_SEPARATION,
    articulation_root,
    build_world,
    find_prim,
    make_camera_prim,
)

# Backwards-compatible private aliases used by add_sensors/main below.
_find_prim = find_prim
_make_camera_prim = make_camera_prim

# Drivetrain / friction / wheel-link constants now live in isaac_scene (imported
# above) so the bring-up and the in-process trainer share a single source.

# Sensors (off in --test/--turn; they need rendering).
SENSORS = os.environ.get("BRINGUP_SENSORS", "1") != "0"
# Robot TF tree: off by default -> let robot_state_publisher (URDF + Isaac's
# /joint_states) own it, exactly like the Gazebo setup. See build_ros2_graph.
PUBLISH_ROBOT_TF = os.environ.get("BRINGUP_ROBOT_TF", "0") != "0"
# ZED Mini front stereo pair: scene camera, NOT on the RL path (only the Lane Cam
# is). Two render products roughly double the camera render cost, so allow
# dropping them with BRINGUP_ZED=0 (the Lane Cam is always kept).
ZED = os.environ.get("BRINGUP_ZED", "1") != "0"
# Each entry mirrors the Gazebo <sensor> on that link: same ROS2 topics + frame
# ids (src/cobraflex/urdf/robot.gazebo, config/gz_bridge.yaml) so existing nodes
# consume them unchanged. Tuple: (optical frame for the camera prim, hfov rad,
# width, height, image topic, info topic). hfov from robot.gazebo.
CAMERAS = []
if ZED:
    # ZED Mini stereo pair (63 mm baseline), per-eye 640x480, hfov 1.3962634 rad
    # (80 deg). zed-ros2 topic convention: camera/{left,right}/{image_raw,camera_info}.
    CAMERAS += [
        ("zedm_left_camera_frame_optical", 1.3962634, 640, 480,
         "camera/left/image_raw", "camera/left/camera_info"),
        ("zedm_right_camera_frame_optical", 1.3962634, 640, 480,
         "camera/right/image_raw", "camera/right/camera_info"),
    ]
# Lane Cam (IMX219-160 mirror), 640x360, hfov 1.5707963 rad (90 deg): the RL/CV
# perception camera. Its info topic is camera/camera_info (matches robot.gazebo;
# the former mono ZED freed that name when it became the left/right stereo pair).
CAMERAS += [
    ("camera_link_optical_lane", 1.5707963, 640, 360,
     "camera/image_raw_lane", "camera/camera_info"),
]
IMU_LINK = "imu_link"
IMU_TOPIC = "imu"
LIDAR_LINK = "lidar_link"
LIDAR_TOPIC = "scan"
# SLAMTEC RPLIDAR S2E config ships with Isaac (in the default profile search path):
# 360 deg 2D rotary, nearRange 0.05 m, 10 Hz -- matches the Gazebo RPLiDAR's close
# detection. The stock Example_Rotary_2D only detected from 1 m. Override via env.
LIDAR_CONFIG = os.environ.get("LIDAR_CONFIG", "RPLIDAR_S2E")

# REPO / robot paths / drivetrain constants (WHEEL_RADIUS/SEPARATION/JOINTS) and
# the diff-drive WHEEL_SCRIPT are imported from isaac_scene above. GRAPH_PATH is
# the ROS2 action-graph root and stays here (ROS-specific to this bring-up).
GRAPH_PATH = "/World/ActionGraph"


def _add_camera_graph(idx, camera_path, frame_id, width, height, img_topic, info_topic):
    keys = og.Controller.Keys
    g = f"/World/SensorGraphs/Camera_{idx}"
    og.Controller.edit(
        {"graph_path": g, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("Tick", "omni.graph.action.OnPlaybackTick"),
                ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                ("RunOnce", "isaacsim.core.nodes.OgnIsaacRunOneSimulationFrame"),
                ("RenderProduct", "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                ("RGB", "isaacsim.ros2.bridge.ROS2CameraHelper"),
                ("Info", "isaacsim.ros2.bridge.ROS2CameraInfoHelper"),
            ],
            keys.SET_VALUES: [
                ("RenderProduct.inputs:cameraPrim", camera_path),
                ("RenderProduct.inputs:width", width),
                ("RenderProduct.inputs:height", height),
                ("RGB.inputs:topicName", img_topic),
                ("RGB.inputs:type", "rgb"),
                ("RGB.inputs:frameId", frame_id),
                ("Info.inputs:topicName", info_topic),
                ("Info.inputs:frameId", frame_id),
            ],
            keys.CONNECT: [
                ("Tick.outputs:tick", "RunOnce.inputs:execIn"),
                ("RunOnce.outputs:step", "RenderProduct.inputs:execIn"),
                ("RenderProduct.outputs:execOut", "RGB.inputs:execIn"),
                ("RenderProduct.outputs:renderProductPath", "RGB.inputs:renderProductPath"),
                ("RenderProduct.outputs:execOut", "Info.inputs:execIn"),
                ("RenderProduct.outputs:renderProductPath", "Info.inputs:renderProductPath"),
                ("Context.outputs:context", "RGB.inputs:context"),
                ("Context.outputs:context", "Info.inputs:context"),
            ],
        },
    )


def _add_lidar_graph(lidar_path, frame_id, topic):
    keys = og.Controller.Keys
    g = "/World/SensorGraphs/Lidar"
    og.Controller.edit(
        {"graph_path": g, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("Tick", "omni.graph.action.OnPlaybackTick"),
                ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                ("RunOnce", "isaacsim.core.nodes.OgnIsaacRunOneSimulationFrame"),
                ("RenderProduct", "isaacsim.core.nodes.IsaacCreateRenderProduct"),
                ("LaserScan", "isaacsim.ros2.bridge.ROS2RtxLidarHelper"),
            ],
            keys.SET_VALUES: [
                ("RenderProduct.inputs:cameraPrim", lidar_path),
                ("LaserScan.inputs:topicName", topic),
                ("LaserScan.inputs:type", "laser_scan"),
                ("LaserScan.inputs:frameId", frame_id),
            ],
            keys.CONNECT: [
                ("Tick.outputs:tick", "RunOnce.inputs:execIn"),
                ("RunOnce.outputs:step", "RenderProduct.inputs:execIn"),
                ("RenderProduct.outputs:execOut", "LaserScan.inputs:execIn"),
                ("RenderProduct.outputs:renderProductPath", "LaserScan.inputs:renderProductPath"),
                ("Context.outputs:context", "LaserScan.inputs:context"),
            ],
        },
    )


def _add_imu_graph(imu_path, frame_id, topic):
    keys = og.Controller.Keys
    g = "/World/SensorGraphs/Imu"
    og.Controller.edit(
        {"graph_path": g, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("Tick", "omni.graph.action.OnPlaybackTick"),
                ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                ("SimTime", "isaacsim.core.nodes.IsaacReadSimulationTime"),
                ("ReadIMU", "isaacsim.sensors.physics.IsaacReadIMU"),
                ("PublishImu", "isaacsim.ros2.bridge.ROS2PublishImu"),
            ],
            keys.SET_VALUES: [
                ("ReadIMU.inputs:imuPrim", [imu_path]),
                ("PublishImu.inputs:topicName", topic),
                ("PublishImu.inputs:frameId", frame_id),
            ],
            keys.CONNECT: [
                ("Tick.outputs:tick", "ReadIMU.inputs:execIn"),
                ("ReadIMU.outputs:execOut", "PublishImu.inputs:execIn"),
                ("ReadIMU.outputs:orientation", "PublishImu.inputs:orientation"),
                ("ReadIMU.outputs:linAcc", "PublishImu.inputs:linearAcceleration"),
                ("ReadIMU.outputs:angVel", "PublishImu.inputs:angularVelocity"),
                ("Context.outputs:context", "PublishImu.inputs:context"),
                ("SimTime.outputs:simulationTime", "PublishImu.inputs:timeStamp"),
            ],
        },
    )


def add_sensors(stage) -> None:
    """Create the two cameras + RTX lidar + IMU and wire their ROS2 publish graphs."""
    for idx, (frame, hfov, w, h, img_topic, info_topic) in enumerate(CAMERAS):
        frame_path = _find_prim(stage, frame)
        if not frame_path:
            print(f"[bringup] WARN camera frame {frame} not found, skipping")
            continue
        cam_path = _make_camera_prim(stage, frame_path, hfov, w, h)
        _add_camera_graph(idx, cam_path, frame, w, h, img_topic, info_topic)
        print(f"[bringup] camera on {frame} -> /{img_topic} ({w}x{h})")

    lidar_parent = _find_prim(stage, LIDAR_LINK)
    if lidar_parent:
        _, lidar_prim = omni.kit.commands.execute(
            "IsaacSensorCreateRtxLidar", path="/RtxLidar",
            parent=lidar_parent, config=LIDAR_CONFIG)
        _add_lidar_graph(lidar_prim.GetPath().pathString, LIDAR_LINK, LIDAR_TOPIC)
        print(f"[bringup] RTX lidar ({LIDAR_CONFIG}) on {LIDAR_LINK} -> /{LIDAR_TOPIC}")
    else:
        print(f"[bringup] WARN {LIDAR_LINK} not found, lidar skipped")

    imu_parent = _find_prim(stage, IMU_LINK)
    if imu_parent:
        from isaacsim.sensors.experimental.physics import IMU
        imu_path = imu_parent + "/Imu_Sensor"
        IMU.create(imu_path, translations=[[0.0, 0.0, 0.0]])
        _add_imu_graph(imu_path, IMU_LINK, IMU_TOPIC)
        print(f"[bringup] IMU on {IMU_LINK} -> /{IMU_TOPIC}")
    else:
        print(f"[bringup] WARN {IMU_LINK} not found, IMU skipped")


def build_scene():
    """Build the shared physics scene, then add this bring-up's ROS2 sensor
    graphs on top.

    The physics scene itself — world, lights, ground, track geometry, robot
    spawn, wheel velocity drives and the low-friction wheel/ground materials —
    lives in ``isaac_scene.build_world`` so the in-process RL trainer
    (``tools/isaac_train.py``) reuses the exact same physics. This bring-up's
    only addition is the ROS2 sensor publish graphs (cameras/lidar/IMU), which
    are skipped on the physics-only ``--test``/``--turn`` paths.
    """
    world, _track_meta = build_world()
    stage = omni.usd.get_context().get_stage()
    if SENSORS and not args.test:
        add_sensors(stage)
    return world


def build_ros2_graph(art_root: str, tf_root: str):
    keys = og.Controller.Keys
    nodes = [
        ("Tick", "omni.graph.action.OnPlaybackTick"),
        ("Context", "isaacsim.ros2.bridge.ROS2Context"),
        ("SimTime", "isaacsim.core.nodes.IsaacReadSimulationTime"),
        ("PublishClock", "isaacsim.ros2.bridge.ROS2PublishClock"),
        ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
        ("WheelScript", "omni.graph.scriptnode.ScriptNode"),
        ("Articulation", "isaacsim.core.nodes.IsaacArticulationController"),
        ("ComputeOdom", "isaacsim.core.nodes.IsaacComputeOdometry"),
        ("PublishOdom", "isaacsim.ros2.bridge.ROS2PublishOdometry"),
        ("PublishOdomTF", "isaacsim.ros2.bridge.ROS2PublishRawTransformTree"),
        # Ground-truth odometry: IsaacComputeOdometry reads the actual sim pose, so
        # this mirrors the Gazebo OdometryPublisher /odom_truth that RL training uses.
        ("PublishOdomTruth", "isaacsim.ros2.bridge.ROS2PublishOdometry"),
        ("PublishJointState", "isaacsim.ros2.bridge.ROS2PublishJointState"),
    ]
    values = [
        ("SubscribeTwist.inputs:topicName", "cmd_vel"),
        ("WheelScript.inputs:script", WHEEL_SCRIPT),
        ("Articulation.inputs:robotPath", art_root),
        ("Articulation.inputs:jointNames", WHEEL_JOINTS),
        ("ComputeOdom.inputs:chassisPrim", [art_root]),
        ("PublishOdom.inputs:topicName", "odom"),
        ("PublishOdom.inputs:odomFrameId", "odom"),
        ("PublishOdom.inputs:chassisFrameId", "base_footprint"),
        # odom -> base_footprint TF (PublishOdometry only emits the /odom message,
        # not the transform). robot_state_publisher then hangs base_footprint->links
        # off this, so RViz can resolve odom -> any link.
        ("PublishOdomTF.inputs:parentFrameId", "odom"),
        ("PublishOdomTF.inputs:childFrameId", "base_footprint"),
        ("PublishOdomTF.inputs:topicName", "tf"),
        ("PublishOdomTruth.inputs:topicName", "odom_truth"),
        ("PublishOdomTruth.inputs:odomFrameId", "odom"),
        ("PublishOdomTruth.inputs:chassisFrameId", "base_footprint"),
        ("PublishJointState.inputs:topicName", "joint_states"),
        ("PublishJointState.inputs:targetPrim", [art_root]),
    ]
    connect = [
        ("Tick.outputs:tick", "PublishClock.inputs:execIn"),
        ("Context.outputs:context", "PublishClock.inputs:context"),
        ("SimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
        ("Tick.outputs:tick", "SubscribeTwist.inputs:execIn"),
        ("Context.outputs:context", "SubscribeTwist.inputs:context"),
        ("SubscribeTwist.outputs:execOut", "WheelScript.inputs:execIn"),
        ("SubscribeTwist.outputs:linearVelocity", "WheelScript.inputs:linVel"),
        ("SubscribeTwist.outputs:angularVelocity", "WheelScript.inputs:angVel"),
        ("WheelScript.outputs:execOut", "Articulation.inputs:execIn"),
        ("WheelScript.outputs:velCmd", "Articulation.inputs:velocityCommand"),
        ("Tick.outputs:tick", "ComputeOdom.inputs:execIn"),
        ("ComputeOdom.outputs:execOut", "PublishOdom.inputs:execIn"),
        ("Context.outputs:context", "PublishOdom.inputs:context"),
        ("SimTime.outputs:simulationTime", "PublishOdom.inputs:timeStamp"),
        ("ComputeOdom.outputs:position", "PublishOdom.inputs:position"),
        ("ComputeOdom.outputs:orientation", "PublishOdom.inputs:orientation"),
        ("ComputeOdom.outputs:linearVelocity", "PublishOdom.inputs:linearVelocity"),
        ("ComputeOdom.outputs:angularVelocity", "PublishOdom.inputs:angularVelocity"),
        ("ComputeOdom.outputs:execOut", "PublishOdomTruth.inputs:execIn"),
        ("Context.outputs:context", "PublishOdomTruth.inputs:context"),
        ("SimTime.outputs:simulationTime", "PublishOdomTruth.inputs:timeStamp"),
        ("ComputeOdom.outputs:position", "PublishOdomTruth.inputs:position"),
        ("ComputeOdom.outputs:orientation", "PublishOdomTruth.inputs:orientation"),
        ("ComputeOdom.outputs:linearVelocity", "PublishOdomTruth.inputs:linearVelocity"),
        ("ComputeOdom.outputs:angularVelocity", "PublishOdomTruth.inputs:angularVelocity"),
        ("Tick.outputs:tick", "PublishOdomTF.inputs:execIn"),
        ("Context.outputs:context", "PublishOdomTF.inputs:context"),
        ("SimTime.outputs:simulationTime", "PublishOdomTF.inputs:timeStamp"),
        ("ComputeOdom.outputs:position", "PublishOdomTF.inputs:translation"),
        ("ComputeOdom.outputs:orientation", "PublishOdomTF.inputs:rotation"),
        ("Tick.outputs:tick", "PublishJointState.inputs:execIn"),
        ("Context.outputs:context", "PublishJointState.inputs:context"),
        ("SimTime.outputs:simulationTime", "PublishJointState.inputs:timeStamp"),
    ]
    # Robot TF tree: off by default. Isaac's ROS2PublishTransformTree rejects the
    # massless base_footprint frame and skips the empty optical frames (the camera
    # image frame_ids), so it yields an incomplete, disconnected tree. The Gazebo-
    # style robot_state_publisher (reads the URDF + Isaac's /joint_states) publishes
    # the full tree incl. base_footprint + *_optical. Isaac keeps odom->base_footprint
    # + joint_states + sensors. Enable this only for a quick standalone partial tree.
    if PUBLISH_ROBOT_TF:
        nodes.append(("PublishTF", "isaacsim.ros2.bridge.ROS2PublishTransformTree"))
        values += [("PublishTF.inputs:topicName", "tf"),
                   ("PublishTF.inputs:targetPrims", [tf_root])]
        connect += [("Tick.outputs:tick", "PublishTF.inputs:execIn"),
                    ("Context.outputs:context", "PublishTF.inputs:context"),
                    ("SimTime.outputs:simulationTime", "PublishTF.inputs:timeStamp")]

    og.Controller.edit(
        {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: nodes,
            keys.CREATE_ATTRIBUTES: [
                ("WheelScript.inputs:linVel", "double[3]"),
                ("WheelScript.inputs:angVel", "double[3]"),
                ("WheelScript.outputs:velCmd", "double[]"),
            ],
            keys.SET_VALUES: values,
            keys.CONNECT: connect,
        },
    )


def main() -> int:
    world = build_scene()
    stage = omni.usd.get_context().get_stage()
    art_root = articulation_root(stage)
    tf_root = _find_prim(stage, "base_footprint") or art_root
    print(f"[bringup] articulation root: {art_root}; tf root: {tf_root}")
    build_ros2_graph(art_root, tf_root)
    print("[bringup] ROS2 action graph built at", GRAPH_PATH)

    world.reset()
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()

    if args.shot:
        # Top-down snapshot to verify the track/scene visually (headless).
        import numpy as np
        import omni.replicator.core as rep
        from PIL import Image
        cx, cy = 0.0, 0.0
        meta_path = os.path.join(REPO, "experiments/sim/tracks",
                                 os.environ.get("TRACK", "complex_a"),
                                 f"{os.environ.get('TRACK', 'complex_a')}_meta.yaml")
        if os.path.exists(meta_path):
            import yaml
            cx, cy = yaml.safe_load(open(meta_path))["center_m"]
        cam = rep.create.camera(position=(cx, cy, 13.0), look_at=(cx, cy, 0.0))
        rp = rep.create.render_product(cam, (1600, 1000))
        annot = rep.AnnotatorRegistry.get_annotator("rgb")
        annot.attach(rp)
        for _ in range(60):
            world.step(render=True)
        data = annot.get_data()
        Image.fromarray(data[..., :3]).save(args.shot)
        print(f"[bringup] snapshot saved to {args.shot}")
        return 0

    if args.cam_shot:
        # Render exactly what the Lane Cam sees from the current robot pose, to
        # check the lane stays in frame on tight curves.
        import omni.replicator.core as rep
        from PIL import Image
        cam_path = _find_prim(stage, "camera_link_optical_lane")
        cam_path = cam_path + "/Camera" if cam_path else None
        if not cam_path or not stage.GetPrimAtPath(cam_path):
            print("[bringup] lane camera prim not found")
            return 1
        rp = rep.create.render_product(cam_path, (640, 360))   # lane cam resolution
        annot = rep.AnnotatorRegistry.get_annotator("rgb")
        annot.attach(rp)
        for _ in range(60):
            world.step(render=True)
        data = annot.get_data()
        Image.fromarray(data[..., :3]).save(args.cam_shot)
        print(f"[bringup] lane camera view saved to {args.cam_shot} "
              f"(CAM_POSE={os.environ.get('CAM_POSE', '')})")
        return 0

    if not args.test:
        print("[bringup] running. Drive with: ros2 run teleop_twist_keyboard "
              "teleop_twist_keyboard")
        # Always render when sensors are on (cameras/lidar publish from the render
        # pipeline) even in --headless; otherwise render only for the GUI.
        render = SENSORS or not args.headless
        while simulation_app.is_running():
            world.step(render=render)
        return 0

    # --test: command the wheels directly through the articulation (no ROS needed)
    # and confirm the robot actually translates -> proves the drivetrain works.
    from isaacsim.core.prims import SingleArticulation
    from isaacsim.core.utils.types import ArticulationAction

    art = SingleArticulation(prim_path=art_root, name="cobra")
    art.initialize()
    dof_idx = [art.get_dof_index(j) for j in WHEEL_JOINTS]
    print(f"[bringup] wheel dof indices: {dof_idx}")

    import math

    def yaw_of(quat) -> float:
        w, x, y, z = (float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3]))
        return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))

    for _ in range(30):                       # settle onto the ground
        world.step(render=False)

    if args.turn:
        # Differential command: left wheels slow, right wheels fast -> yaw left.
        wl, wr = 8.0, 20.0                     # rad/s
        v_exp = WHEEL_RADIUS * (wl + wr) / 2.0
        yaw_exp = WHEEL_RADIUS * (wr - wl) / WHEEL_SEPARATION   # ideal diff-drive
        action = ArticulationAction(joint_velocities=[wl, wl, wr, wr],
                                    joint_indices=dof_idx)
        p0, q0 = art.get_world_pose()
        steps, dt = 180, 1.0 / 60.0
        for _ in range(steps):
            art.apply_action(action)
            world.step(render=False)
        p1, q1 = art.get_world_pose()
        dyaw = math.atan2(math.sin(yaw_of(q1) - yaw_of(q0)),
                          math.cos(yaw_of(q1) - yaw_of(q0)))
        yaw_rate = dyaw / (steps * dt)
        disp = math.hypot(float(p1[0] - p0[0]), float(p1[1] - p0[1]))
        eff = yaw_rate / yaw_exp if yaw_exp else 0.0
        print(f"[bringup] turn: friction={WHEEL_FRICTION} v_exp={v_exp:.2f} "
              f"disp={disp:.2f}m yaw_exp={yaw_exp:.2f} yaw_meas={yaw_rate:.2f} "
              f"rad/s eff={eff:.0%}")
        ok = abs(yaw_rate) > 0.3 * abs(yaw_exp)
        print("[RESULT]", "PASS" if ok else "FAIL",
              "(robot yaws under differential command)" if ok
              else "(turn suppressed - lower WHEEL_FRICTION)")
        return 0 if ok else 1

    p0, _ = art.get_world_pose()
    spin = 25.0                               # rad/s on all four wheels -> forward
    action = ArticulationAction(joint_velocities=[spin] * 4, joint_indices=dof_idx)
    for _ in range(220):
        art.apply_action(action)
        world.step(render=False)
    p1, _ = art.get_world_pose()

    disp = math.hypot(float(p1[0] - p0[0]), float(p1[1] - p0[1]))
    print(f"[bringup] base displacement under wheel command: {disp:.3f} m")
    ok = disp > 0.05
    print("[RESULT]", "PASS" if ok else "FAIL",
          "(wheels drive the base)" if ok else "(no motion - check drives)")
    return 0 if ok else 1


try:
    rc = main()
except Exception:
    import traceback
    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
