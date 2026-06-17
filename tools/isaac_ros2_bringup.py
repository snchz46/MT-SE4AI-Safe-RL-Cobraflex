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
from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig  # noqa: E402
from isaacsim.core.utils.stage import add_reference_to_stage  # noqa: E402
from pxr import Gf, UsdGeom, UsdPhysics  # noqa: E402

# PhysX velocity control needs a drive with damping on each wheel joint. The URDF
# `continuous` joints import without gains ("Stiffness and damping not available"),
# so a commanded wheel velocity would produce no torque and the robot would not
# move. Apply a stiffness-0 / high-damping angular drive => pure velocity tracking.
WHEEL_DRIVE_DAMPING = 1.0e4
WHEEL_DRIVE_MAX_FORCE = 1.0e3

# A 4-wheel skid-steer yaws by scrubbing all four wheels sideways. PhysX grips
# harder than Gazebo's ODE, so with the wheels' default (high) friction the turn
# that worked in Gazebo barely responds here. Lowering the wheel+ground friction
# frees the lateral scrub so the robot yaws again (measured: f=0.5 -> 0.09 rad/s,
# f=0.1 -> 0.26, f=0.05 -> 0.53, against an ideal 2.9 rad/s test command). Both
# wheel and ground are set so the contact pair is fully controlled; combine="min".
# (An asymmetric low-front/grippy-rear split was tried and made the yaw unstable.)
WHEEL_FRICTION = float(os.environ.get("WHEEL_FRICTION", "0.05"))
GROUND_FRICTION = float(os.environ.get("GROUND_FRICTION", "0.05"))
WHEEL_LINKS = ["front_left_wheel", "rear_left_wheel",
               "front_right_wheel", "rear_right_wheel"]

# Sensors (off in --test/--turn; they need rendering). Each entry mirrors the
# Gazebo <sensor> on that link: same ROS2 topics + frame ids so existing nodes
# (lane_keeper, etc.) consume them unchanged. hfov from robot.gazebo.
SENSORS = os.environ.get("BRINGUP_SENSORS", "1") != "0"
# Robot TF tree: off by default -> let robot_state_publisher (URDF + Isaac's
# /joint_states) own it, exactly like the Gazebo setup. See build_ros2_graph.
PUBLISH_ROBOT_TF = os.environ.get("BRINGUP_ROBOT_TF", "0") != "0"
CAMERAS = [
    # (link frame for the camera prim, hfov rad, width, height, image topic, info topic)
    ("camera_link_optical", 1.3962634, 640, 480,
     "camera/image_raw", "camera/camera_info"),
    ("camera_link_optical_lane", 1.5707963, 640, 360,
     "camera/image_raw_lane", "camera/camera_info_lane"),
]
IMU_LINK = "imu_link"
IMU_TOPIC = "imu"
LIDAR_LINK = "lidar_link"
LIDAR_TOPIC = "scan"
# SLAMTEC RPLIDAR S2E config ships with Isaac (in the default profile search path):
# 360 deg 2D rotary, nearRange 0.05 m, 10 Hz -- matches the Gazebo RPLiDAR's close
# detection. The stock Example_Rotary_2D only detected from 1 m. Override via env.
LIDAR_CONFIG = os.environ.get("LIDAR_CONFIG", "RPLIDAR_S2E")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URDF = os.path.join(REPO, "src/cobraflex/urdf/cobraflex_isaac.urdf")
USD_OUT = os.path.join(REPO, "src/cobraflex/urdf/isaac_usd")
ROBOT_PATH = "/World/Cobraflex"
GRAPH_PATH = "/World/ActionGraph"

WHEEL_RADIUS = 0.03725          # m   (matches robot.gazebo)
WHEEL_SEPARATION = 0.154        # m   (matches robot.gazebo)
# Order matters: jointNames[i] is commanded with velCmd[i].
WHEEL_JOINTS = [
    "front_left_wheel_joint", "rear_left_wheel_joint",     # left side
    "front_right_wheel_joint", "rear_right_wheel_joint",   # right side
]

# Differential-drive kinematics: twist (v=linear.x, w=angular.z) -> wheel speeds.
# Left wheels share v_l, right wheels share v_r. Output order matches WHEEL_JOINTS.
WHEEL_SCRIPT = f"""
def compute(db):
    lin = db.inputs.linVel
    ang = db.inputs.angVel
    v = float(lin[0])
    w = float(ang[2])
    r = {WHEEL_RADIUS}
    half = {WHEEL_SEPARATION} / 2.0
    v_l = (v - w * half) / r
    v_r = (v + w * half) / r
    db.outputs.velCmd = [v_l, v_l, v_r, v_r]
    return True
"""


def ensure_robot_usd() -> str:
    """Convert the URDF to USD if needed and return the .usda path."""
    out = os.path.join(USD_OUT, "cobraflex_isaac", "cobraflex_isaac.usda")
    if os.path.exists(out):
        return out
    os.makedirs(USD_OUT, exist_ok=True)
    cfg = URDFImporterConfig(urdf_path=URDF, usd_path=USD_OUT,
                             merge_fixed_joints=False, merge_mesh=False, fix_base=False)
    return URDFImporter(cfg).import_urdf()


def articulation_root(stage) -> str:
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            return prim.GetPath().pathString
    return ROBOT_PATH


def configure_wheel_drives(stage) -> int:
    """Add a velocity (stiffness=0) angular drive to each wheel joint."""
    n = 0
    for prim in stage.Traverse():
        if prim.IsA(UsdPhysics.RevoluteJoint) and prim.GetName() in WHEEL_JOINTS:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
            drive.CreateTypeAttr().Set("force")
            drive.CreateStiffnessAttr().Set(0.0)
            drive.CreateDampingAttr().Set(WHEEL_DRIVE_DAMPING)
            drive.CreateMaxForceAttr().Set(WHEEL_DRIVE_MAX_FORCE)
            n += 1
    return n


def configure_wheel_material(stage, friction: float) -> int:
    """Bind a low-friction material to the wheel colliders so the robot can yaw."""
    from pxr import PhysxSchema, Sdf, UsdShade
    from omni.physx.scripts import physicsUtils

    mat_path = "/World/PhysicsMaterials/Wheel"
    p = UsdShade.Material.Define(stage, mat_path).GetPrim()
    m = UsdPhysics.MaterialAPI.Apply(p)
    m.CreateStaticFrictionAttr().Set(friction)
    m.CreateDynamicFrictionAttr().Set(friction)
    m.CreateRestitutionAttr().Set(0.0)
    PhysxSchema.PhysxMaterialAPI.Apply(p).CreateFrictionCombineModeAttr().Set("min")

    # Bind to the wheel *collision* prims (the Cylinder colliders), not the link.
    wheel_links = set(WHEEL_LINKS)
    n = 0
    for prim in stage.Traverse():
        if not prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        a = prim
        while a and a.GetPath() != a.GetPath().GetParentPath():
            if a.GetName() in wheel_links:
                physicsUtils.add_physics_material_to_prim(stage, prim, Sdf.Path(mat_path))
                n += 1
                break
            a = a.GetParent()
    return n


def _flat_material(stage, path, rgb):
    from pxr import Gf, Sdf, UsdShade
    mtl = UsdShade.Material.Define(stage, path)
    s = UsdShade.Shader.Define(stage, path + "/S")
    s.CreateIdAttr("UsdPreviewSurface")
    s.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    s.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
    s.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    mtl.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(), "surface")
    return mtl


def _bind(prim, mtl):
    from pxr import UsdShade
    UsdShade.MaterialBindingAPI(prim).Apply(prim)
    UsdShade.MaterialBindingAPI(prim).Bind(mtl)


def _ribbon_mesh(stage, path, inner, outer, z, mtl):
    """Closed quad ribbon between two parallel polylines at height z."""
    from pxr import UsdGeom
    n = len(inner)
    pts, counts, idx = [], [], []
    for i in range(n):
        pts.append((float(inner[i][0]), float(inner[i][1]), z))
        pts.append((float(outer[i][0]), float(outer[i][1]), z))
    for i in range(n):
        a, b = 2 * i, 2 * i + 1
        c, d = 2 * ((i + 1) % n) + 1, 2 * ((i + 1) % n)
        idx += [a, b, c, d]
        counts.append(4)
    m = UsdGeom.Mesh.Define(stage, path)
    m.CreatePointsAttr(pts)
    m.CreateFaceVertexCountsAttr(counts)
    m.CreateFaceVertexIndicesAttr(idx)
    _bind(m.GetPrim(), mtl)
    return m


def _add_track_geometry(stage, meta, tdir):
    """Build the road + lane lines as USD geometry (crisp at any zoom, no texture
    aliasing) from the centreline. Better than a baked texture for Isaac."""
    import numpy as np
    import yaml
    from pxr import UsdGeom

    cl = yaml.safe_load(open(os.path.join(tdir, f"{meta['name']}_centerline.yaml")))
    P = np.array(cl["centerline"]["points"], dtype=float)
    rw = float(meta.get("road_width", 0.52))
    two_lane = int(meta.get("lanes", 2)) == 2
    lw = 0.01                                  # line width (m)

    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-9)
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)
    left = P + (rw / 2.0) * nrm
    right = P - (rw / 2.0) * nrm

    asphalt = _flat_material(stage, "/World/Track/MatAsphalt", (0.0, 0.0, 0.0))
    white = _flat_material(stage, "/World/Track/MatLine", (0.9, 0.9, 0.9))
    grass = _flat_material(stage, "/World/Track/MatGrass", (0.32, 0.42, 0.24))

    # Off-road backdrop (one big quad just under the asphalt).
    x0, y0, x1, y1 = meta["world_bbox"]
    g = UsdGeom.Mesh.Define(stage, "/World/Track/Offroad")
    g.CreatePointsAttr([(x0, y0, 0.0006), (x1, y0, 0.0006),
                        (x1, y1, 0.0006), (x0, y1, 0.0006)])
    g.CreateFaceVertexCountsAttr([4])
    g.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    _bind(g.GetPrim(), grass)

    _ribbon_mesh(stage, "/World/Track/Asphalt", left, right, 0.0010, asphalt)
    _ribbon_mesh(stage, "/World/Track/EdgeL",
                 left + (lw / 2) * nrm, left - (lw / 2) * nrm, 0.0030, white)
    _ribbon_mesh(stage, "/World/Track/EdgeR",
                 right + (lw / 2) * nrm, right - (lw / 2) * nrm, 0.0030, white)

    if two_lane:                               # dashed centre line, one mesh of quads
        seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        dash, gap = 0.10, 0.10
        pts, counts, idx, k = [], [], [], 0
        pos = 0.0
        while pos < s[-1]:
            a0, a1 = pos, min(pos + dash, s[-1])
            ia = int(np.searchsorted(s, a0)) % len(P)
            ib = int(np.searchsorted(s, a1)) % len(P)
            pa, pb, na = P[ia], P[ib], nrm[ia]
            quad = [pa + (lw / 2) * na, pa - (lw / 2) * na,
                    pb - (lw / 2) * na, pb + (lw / 2) * na]
            for q in quad:
                pts.append((float(q[0]), float(q[1]), 0.0030))
            idx += [k, k + 1, k + 2, k + 3]
            counts.append(4)
            k += 4
            pos += dash + gap
        m = UsdGeom.Mesh.Define(stage, "/World/Track/Centre")
        m.CreatePointsAttr(pts)
        m.CreateFaceVertexCountsAttr(counts)
        m.CreateFaceVertexIndicesAttr(idx)
        _bind(m.GetPrim(), white)
    print(f"[bringup] track '{meta['name']}' built as geometry "
          f"({meta['size_m'][0]:.1f}x{meta['size_m'][1]:.1f} m, "
          f"{'2-lane' if two_lane else '1-lane'})")


def _add_track_texture(stage, meta, tdir):
    from pxr import Gf, Sdf, UsdShade
    png = os.path.join(tdir, meta["texture"])
    cx, cy = meta["center_m"]
    w, h = meta["size_m"]
    hw, hh = w / 2.0, h / 2.0
    quad = UsdGeom.Mesh.Define(stage, "/World/Track")
    quad.CreatePointsAttr([(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)])
    quad.CreateFaceVertexCountsAttr([4])
    quad.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    st = UsdGeom.PrimvarsAPI(quad.GetPrim()).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    st.Set([(0, 0), (1, 0), (1, 1), (0, 1)])
    UsdGeom.Xformable(quad.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(cx, cy, 0.0015))
    mtl = UsdShade.Material.Define(stage, "/World/Track/Mat")
    surf = UsdShade.Shader.Define(stage, "/World/Track/Mat/Surface")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
    streader = UsdShade.Shader.Define(stage, "/World/Track/Mat/St")
    streader.CreateIdAttr("UsdPrimvarReader_float2")
    streader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    tex = UsdShade.Shader.Define(stage, "/World/Track/Mat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(png)
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        streader.ConnectableAPI(), "result")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        tex.ConnectableAPI(), "rgb")
    mtl.CreateSurfaceOutput().ConnectToSource(surf.ConnectableAPI(), "surface")
    _bind(quad.GetPrim(), mtl)
    print(f"[bringup] track '{meta['name']}' loaded as texture "
          f"({w:.1f}x{h:.1f} m)")


def add_track(stage):
    """Build a generated track (scripts/generate_complex_track.py). Geometry by
    default (crisp vector lines); TRACK_MODE=texture for the baked PNG. Returns the
    track meta dict (start pose etc.) or None."""
    import yaml

    track = os.environ.get("TRACK", "complex_a")
    if not track:
        return None
    tdir = os.path.join(REPO, "experiments/sim/tracks", track)
    meta_path = os.path.join(tdir, f"{track}_meta.yaml")
    if not os.path.exists(meta_path):
        print(f"[bringup] no track '{track}' at {meta_path}, skipping")
        return None
    meta = yaml.safe_load(open(meta_path))
    if os.environ.get("TRACK_MODE", "geom") == "texture":
        _add_track_texture(stage, meta, tdir)
    else:
        _add_track_geometry(stage, meta, tdir)
    return meta


def _find_prim(stage, name: str) -> str:
    for prim in stage.Traverse():
        if prim.GetName() == name:
            return prim.GetPath().pathString
    return ""


def _make_camera_prim(stage, parent_path, hfov, width, height):
    """Define a USD Camera under the ROS optical frame with matching intrinsics."""
    cam_path = parent_path + "/Camera"
    cam = UsdGeom.Camera.Define(stage, cam_path)
    # USD cameras look down local -Z; the ROS optical frame has +Z forward, so
    # rotate 180 deg about X to point the camera along the optical viewing axis.
    UsdGeom.Xformable(cam.GetPrim()).AddOrientOp().Set(Gf.Quatf(0, 1, 0, 0))
    aperture = 20.955
    cam.GetHorizontalApertureAttr().Set(aperture)
    cam.GetVerticalApertureAttr().Set(aperture * height / width)
    cam.GetFocalLengthAttr().Set(aperture / (2.0 * math.tan(hfov / 2.0)))
    cam.GetClippingRangeAttr().Set(Gf.Vec2f(0.1, 15.0))
    return cam_path


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
    from isaacsim.core.api import World
    from isaacsim.core.api.objects.ground_plane import GroundPlane
    from isaacsim.core.api.materials import PhysicsMaterial

    world = World(stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()

    # Lighting: the explicit GroundPlane (vs add_default_ground_plane) leaves the
    # stage with no light, so the RTX viewport renders all black. Add a dome +
    # distant light so the GUI shows the scene.
    from pxr import UsdLux
    dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
    dome.CreateIntensityAttr(1000.0)
    sun = UsdLux.DistantLight.Define(stage, "/World/DistantLight")
    sun.CreateIntensityAttr(3000.0)
    sun.CreateAngleAttr(0.53)

    # Explicit ground with a known friction so the wheel/ground contact pair is
    # fully under our control (combine=min on the wheel material then wins).
    gmat = PhysicsMaterial("/World/groundMat",
                           static_friction=GROUND_FRICTION,
                           dynamic_friction=GROUND_FRICTION, restitution=0.0)
    GroundPlane("/World/groundPlane", z_position=0.0, physics_material=gmat)

    # Track: textured ground quad (off by setting TRACK="").
    track_meta = add_track(stage)

    usd_path = ensure_robot_usd()
    add_reference_to_stage(usd_path, ROBOT_PATH)
    # Spawn at CAM_POSE="x,y,yaw" if set (camera-visibility checks), else the track
    # start line (on the centreline), else the origin.
    from isaacsim.core.prims import SingleXFormPrim
    from pxr import Gf
    cam_pose = os.environ.get("CAM_POSE", "")
    if cam_pose:
        sx, sy, yaw = (float(v) for v in cam_pose.split(","))
        quat = Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(yaw)).GetQuat()
        SingleXFormPrim(ROBOT_PATH, position=(sx, sy, 0.06),
                        orientation=(quat.GetReal(), *quat.GetImaginary()))
    elif track_meta:
        sx, sy = track_meta["start_xy"]
        yaw = float(track_meta["start_yaw"])
        quat = Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(yaw)).GetQuat()
        SingleXFormPrim(ROBOT_PATH, position=(sx, sy, 0.06),
                        orientation=(quat.GetReal(), *quat.GetImaginary()))
    else:
        SingleXFormPrim(ROBOT_PATH, position=(0.0, 0.0, 0.06))
    nd = configure_wheel_drives(stage)
    nm = configure_wheel_material(stage, WHEEL_FRICTION)
    print(f"[bringup] velocity drives on {nd} wheel joints; friction "
          f"{WHEEL_FRICTION} (combine=min) on {nm} wheel colliders, "
          f"ground {GROUND_FRICTION}")
    # Sensors render off-screen; skip them in the physics-only --test/--turn paths.
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
