"""Headless smoke-test: import cobraflex_isaac.urdf into Isaac Sim and report.

Run with Isaac Sim's bundled python:
    ~/isaacsim/python.sh tools/isaac_import_check.py

Uses the Isaac Sim 6.0 importer API (URDFImporter / URDFImporterConfig) to
convert the generated URDF to USD, then walks the resulting stage to confirm the
articulation root, every link, every joint and the referenced meshes made it in.
Writes the converted asset under src/cobraflex/urdf/isaac_usd/ and exits non-zero
on any failure.
"""
import os
import sys

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
simulation_app.update()

import omni.usd  # noqa: E402
from isaacsim.asset.importer.urdf import (  # noqa: E402
    URDFImporter,
    URDFImporterConfig,
)
from pxr import Usd, UsdGeom, UsdPhysics  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URDF = os.path.join(REPO, "src/cobraflex/urdf/cobraflex_isaac.urdf")
USD_OUT = os.path.join(REPO, "src/cobraflex/urdf/isaac_usd")

EXPECTED_LINKS = {
    "base_footprint", "base_link", "body_link",
    "front_left_wheel", "front_right_wheel",
    "rear_left_wheel", "rear_right_wheel",
    "lidar_link",
    # ZED Mini front stereo pair (zed_macro.urdf.xacro, model=zedm).
    "zedm_camera_link", "zedm_camera_center",
    "zedm_left_camera_frame", "zedm_left_camera_frame_optical",
    "zedm_right_camera_frame", "zedm_right_camera_frame_optical",
    # Lane Cam + IMU.
    "camera_link_lane", "camera_link_optical_lane", "imu_link",
}
EXPECTED_WHEEL_JOINTS = {
    "front_left_wheel_joint", "front_right_wheel_joint",
    "rear_left_wheel_joint", "rear_right_wheel_joint",
}


def main() -> int:
    print(f"[check] URDF: {URDF}")
    print(f"[check] exists: {os.path.exists(URDF)}")
    os.makedirs(USD_OUT, exist_ok=True)

    cfg = URDFImporterConfig(
        urdf_path=URDF,
        usd_path=USD_OUT,
        # Faithful import: keep fixed joints, keep the base free to move.
        merge_fixed_joints=False,
        merge_mesh=False,
        fix_base=False,
    )
    usd_path = URDFImporter(cfg).import_urdf()
    print(f"[check] converted USD: {usd_path}")
    if not usd_path or not os.path.exists(usd_path):
        print("[FAIL] import_urdf produced no USD file")
        return 1

    # Load all payloads so geometry (geometries.usd) and physics sublayers are
    # traversable; the converter packages them as deferred payloads.
    stage = Usd.Stage.Open(usd_path, load=Usd.Stage.LoadAll)
    if stage is None:
        print("[FAIL] could not open converted stage")
        return 1

    all_prim_names, rigid_links = set(), set()
    found_joints, rev_joints = set(), set()
    found_meshes = 0
    art_root = False
    # Include instance proxies: the converter makes geometry instanceable, so its
    # Mesh prims live in prototypes that a default Traverse() skips.
    for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
        name = prim.GetName()
        all_prim_names.add(name)
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            art_root = True
        if name in EXPECTED_LINKS and prim.HasAPI(UsdPhysics.RigidBodyAPI):
            rigid_links.add(name)
        if prim.IsA(UsdGeom.Mesh):
            found_meshes += 1
        if prim.IsA(UsdPhysics.Joint):
            found_joints.add(name)
        if prim.IsA(UsdPhysics.RevoluteJoint):
            rev_joints.add(name)

    # Massless frames (base_footprint, *_optical, imu_link) carry no inertia or
    # geometry, so the importer realizes them as Xform frames rather than rigid
    # bodies. They must still exist as prims to preserve the kinematic frames.
    missing_frames = EXPECTED_LINKS - all_prim_names
    print(f"[check] articulation_root_present = {art_root}")
    print(f"[check] mass-bearing rigid-body links: {sorted(rigid_links)}")
    print(f"[check] all {len(EXPECTED_LINKS)} link frames present: {not missing_frames} "
          f"(missing: {sorted(missing_frames)})")
    print(f"[check] mesh prims imported: {found_meshes}")
    print(f"[check] joints in stage: {sorted(found_joints)}")
    print(f"[check] revolute (wheel) joints: {sorted(rev_joints)}")

    ok = (art_root
          and not missing_frames
          and found_meshes >= 5
          and EXPECTED_WHEEL_JOINTS.issubset(rev_joints))
    print("[RESULT]", "PASS" if ok else "FAIL")
    return 0 if ok else 1


try:
    rc = main()
except Exception:  # noqa: BLE001 - surface any import error before shutdown
    import traceback
    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
