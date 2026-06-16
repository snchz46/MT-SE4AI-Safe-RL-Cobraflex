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
args, _ = parser.parse_known_args()
args.test = args.test or args.turn

from isaacsim import SimulationApp  # noqa: E402

simulation_app = SimulationApp({"headless": args.headless or args.test})

import omni.graph.core as og  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402
from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.ros2.bridge")
simulation_app.update()

import omni.kit.app  # noqa: E402
from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig  # noqa: E402
from isaacsim.core.utils.stage import add_reference_to_stage  # noqa: E402
from pxr import UsdPhysics  # noqa: E402

# PhysX velocity control needs a drive with damping on each wheel joint. The URDF
# `continuous` joints import without gains ("Stiffness and damping not available"),
# so a commanded wheel velocity would produce no torque and the robot would not
# move. Apply a stiffness-0 / high-damping angular drive => pure velocity tracking.
WHEEL_DRIVE_DAMPING = 1.0e4
WHEEL_DRIVE_MAX_FORCE = 1.0e3

# Skid-steer turning: the robot yaws by scrubbing its 4 wheels sideways. The
# Gazebo URDF set mu1=mu2=0.8 on the wheels, but those were <gazebo> tags dropped
# for Isaac, so the wheels fall back to the default (grippy) physics material and
# the robot barely turns. Re-apply a wheel friction material; combine mode "min"
# makes the lower of wheel/ground friction win so lateral scrub stays low enough
# to yaw. Tunable via env WHEEL_FRICTION (lower = turns more easily).
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

    usd_path = ensure_robot_usd()
    add_reference_to_stage(usd_path, ROBOT_PATH)
    # Spawn slightly above the ground so wheels settle onto it.
    from isaacsim.core.prims import SingleXFormPrim
    SingleXFormPrim(ROBOT_PATH, position=(0.0, 0.0, 0.06))
    nd = configure_wheel_drives(stage)
    nm = configure_wheel_material(stage, WHEEL_FRICTION)
    print(f"[bringup] velocity drives on {nd} wheel joints; friction "
          f"{WHEEL_FRICTION} (combine=min) on {nm} wheel colliders, "
          f"ground {GROUND_FRICTION}")
    return world


def build_ros2_graph(art_root: str):
    keys = og.Controller.Keys
    og.Controller.edit(
        {"graph_path": GRAPH_PATH, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("Tick", "omni.graph.action.OnPlaybackTick"),
                ("Context", "isaacsim.ros2.bridge.ROS2Context"),
                ("SimTime", "isaacsim.core.nodes.IsaacReadSimulationTime"),
                ("PublishClock", "isaacsim.ros2.bridge.ROS2PublishClock"),
                ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                ("WheelScript", "omni.graph.scriptnode.ScriptNode"),
                ("Articulation", "isaacsim.core.nodes.IsaacArticulationController"),
                ("ComputeOdom", "isaacsim.core.nodes.IsaacComputeOdometry"),
                ("PublishOdom", "isaacsim.ros2.bridge.ROS2PublishOdometry"),
                ("PublishJointState", "isaacsim.ros2.bridge.ROS2PublishJointState"),
                ("PublishTF", "isaacsim.ros2.bridge.ROS2PublishTransformTree"),
            ],
            keys.CREATE_ATTRIBUTES: [
                ("WheelScript.inputs:linVel", "double[3]"),
                ("WheelScript.inputs:angVel", "double[3]"),
                ("WheelScript.outputs:velCmd", "double[]"),
            ],
            keys.SET_VALUES: [
                ("SubscribeTwist.inputs:topicName", "cmd_vel"),
                ("WheelScript.inputs:script", WHEEL_SCRIPT),
                ("Articulation.inputs:robotPath", art_root),
                ("Articulation.inputs:jointNames", WHEEL_JOINTS),
                ("ComputeOdom.inputs:chassisPrim", [art_root]),
                ("PublishOdom.inputs:topicName", "odom"),
                ("PublishOdom.inputs:odomFrameId", "odom"),
                ("PublishOdom.inputs:chassisFrameId", "base_footprint"),
                ("PublishJointState.inputs:topicName", "joint_states"),
                ("PublishJointState.inputs:targetPrim", [art_root]),
                ("PublishTF.inputs:topicName", "tf"),
                ("PublishTF.inputs:targetPrims", [art_root]),
            ],
            keys.CONNECT: [
                # clock
                ("Tick.outputs:tick", "PublishClock.inputs:execIn"),
                ("Context.outputs:context", "PublishClock.inputs:context"),
                ("SimTime.outputs:simulationTime", "PublishClock.inputs:timeStamp"),
                # cmd_vel -> kinematics -> wheels
                ("Tick.outputs:tick", "SubscribeTwist.inputs:execIn"),
                ("Context.outputs:context", "SubscribeTwist.inputs:context"),
                ("SubscribeTwist.outputs:execOut", "WheelScript.inputs:execIn"),
                ("SubscribeTwist.outputs:linearVelocity", "WheelScript.inputs:linVel"),
                ("SubscribeTwist.outputs:angularVelocity", "WheelScript.inputs:angVel"),
                ("WheelScript.outputs:execOut", "Articulation.inputs:execIn"),
                ("WheelScript.outputs:velCmd", "Articulation.inputs:velocityCommand"),
                # odom
                ("Tick.outputs:tick", "ComputeOdom.inputs:execIn"),
                ("ComputeOdom.outputs:execOut", "PublishOdom.inputs:execIn"),
                ("Context.outputs:context", "PublishOdom.inputs:context"),
                ("SimTime.outputs:simulationTime", "PublishOdom.inputs:timeStamp"),
                ("ComputeOdom.outputs:position", "PublishOdom.inputs:position"),
                ("ComputeOdom.outputs:orientation", "PublishOdom.inputs:orientation"),
                ("ComputeOdom.outputs:linearVelocity", "PublishOdom.inputs:linearVelocity"),
                ("ComputeOdom.outputs:angularVelocity", "PublishOdom.inputs:angularVelocity"),
                # joint states + tf
                ("Tick.outputs:tick", "PublishJointState.inputs:execIn"),
                ("Context.outputs:context", "PublishJointState.inputs:context"),
                ("SimTime.outputs:simulationTime", "PublishJointState.inputs:timeStamp"),
                ("Tick.outputs:tick", "PublishTF.inputs:execIn"),
                ("Context.outputs:context", "PublishTF.inputs:context"),
                ("SimTime.outputs:simulationTime", "PublishTF.inputs:timeStamp"),
            ],
        },
    )


def main() -> int:
    world = build_scene()
    stage = omni.usd.get_context().get_stage()
    art_root = articulation_root(stage)
    print(f"[bringup] articulation root: {art_root}")
    build_ros2_graph(art_root)
    print("[bringup] ROS2 action graph built at", GRAPH_PATH)

    world.reset()
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()

    if not args.test:
        print("[bringup] running. Drive with: ros2 run teleop_twist_keyboard "
              "teleop_twist_keyboard")
        while simulation_app.is_running():
            world.step(render=not args.headless)
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
