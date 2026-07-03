"""Shared Isaac-Sim scene builder for the CobraFlex robot (bring-up + training).

This module owns the **physics scene**: the URDF→USD import, the generated
track geometry, the robot spawn, the wheel velocity drives and the low-friction
wheel/ground contact materials. It is the single source of the drivetrain
constants (``WHEEL_RADIUS``/``WHEEL_SEPARATION``/``WHEEL_JOINTS`` order) so the
ROS2 bring-up demo and the in-process RL trainer can never drift apart — a drift
there would silently invalidate a trained policy.

It is consumed by two entry points:

- ``tools/isaac_ros2_bringup.py`` — adds a ROS2-bridge OmniGraph on top (same
  topic contract as Gazebo) and free-runs ``world.step()``.
- ``tools/isaac_train.py`` — adds an in-process Replicator render product on the
  Lane Cam and drives the gym env directly (no ROS round-trip, no ``gz`` CLI).

**Import-order contract:** every ``omni``/``isaacsim``/``pxr`` import lives
*inside* a function, never at module top level, because Isaac requires
``SimulationApp`` to be instantiated before any such import. The entry point
owns ``SimulationApp``; importing this module is therefore always safe.
"""
import math
import os
import shutil

# --- Drivetrain (matches src/cobraflex/urdf/robot.gazebo and the handover spec) -
WHEEL_RADIUS = 0.03725          # m
WHEEL_SEPARATION = 0.154        # m
# Order matters: jointNames[i] is commanded with velCmd[i]; the trainer resolves
# the articulation DOF indices in this exact order.
WHEEL_JOINTS = [
    "front_left_wheel_joint", "rear_left_wheel_joint",     # left side
    "front_right_wheel_joint", "rear_right_wheel_joint",   # right side
]
WHEEL_LINKS = ["front_left_wheel", "rear_left_wheel",
               "front_right_wheel", "rear_right_wheel"]

# PhysX velocity control needs a drive with damping on each wheel joint. The URDF
# `continuous` joints import without gains, so a commanded wheel velocity would
# produce no torque and the robot would not move. Apply a stiffness-0 /
# high-damping angular drive => pure velocity tracking.
WHEEL_DRIVE_DAMPING = 1.0e4
WHEEL_DRIVE_MAX_FORCE = 1.0e3

# A 4-wheel skid-steer yaws by scrubbing all four wheels sideways. PhysX grips
# harder than Gazebo's ODE, so the wheel+ground friction is lowered so the robot
# yaws again (measured: f=0.05 -> 0.53 rad/s against an ideal 2.9 rad/s command).
WHEEL_FRICTION = float(os.environ.get("WHEEL_FRICTION", "0.05"))
GROUND_FRICTION = float(os.environ.get("GROUND_FRICTION", "0.05"))

# Differential-drive kinematics ScriptNode body (used by the ROS2 bring-up graph;
# the in-process trainer implements the same map in Python in IsaacSimInterface).
# twist (v=linear.x, w=angular.z) -> wheel speeds. Output order == WHEEL_JOINTS.
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

# --- Lane Cam (IMX219-160 mirror): the RL/CV perception camera ----------------
LANE_CAM_FRAME = "camera_link_optical_lane"
LANE_CAM_HFOV = 1.5707963        # rad (90 deg)
LANE_CAM_W = 640
LANE_CAM_H = 360

# Gap between adjacent circuits in a multi-track scene (D-50). Set to the Lane
# Cam far-clip distance (15 m, cf. make_camera_prim's clipping range): a
# neighbouring circuit is therefore never inside the camera frustum from any
# driving position on the active one, so each circuit renders exactly as it
# would alone.
TRACK_GAP_M = 15.0

# --- Paths / stage layout -----------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URDF = os.path.join(REPO, "src/cobraflex/urdf/cobraflex_isaac.urdf")
USD_OUT = os.path.join(REPO, "src/cobraflex/urdf/isaac_usd")
ROBOT_PATH = "/World/Cobraflex"
SPAWN_Z = 0.06                   # spawn height (m); also the per-episode teleport z

# --- Randomizable prim paths (single source for isaac_dr.dr_scene_paths) ------
# Lights + physics materials + geometry-mode track materials. Kept here so the
# scene builder and the domain randomizer can never drift on a path string.
DOME_LIGHT_PATH = "/World/DomeLight"
DISTANT_LIGHT_PATH = "/World/DistantLight"
GROUND_MATERIAL_PATH = "/World/groundMat"
WHEEL_MATERIAL_PATH = "/World/PhysicsMaterials/Wheel"
TRACK_ASPHALT_MATERIAL = "/World/Track/MatAsphalt"
TRACK_LINE_MATERIAL = "/World/Track/MatLine"
TRACK_GRASS_MATERIAL = "/World/Track/MatGrass"


def ensure_robot_usd() -> str:
    """Convert the URDF to USD if needed and return the .usda path.

    An existing USD package is reused as-is. After editing cobraflex_isaac.urdf
    the cached USD is stale, so set BRINGUP_REIMPORT=1 to force a fresh
    URDF->USD import (or just delete src/cobraflex/urdf/isaac_usd/).
    """
    from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig

    out = os.path.join(USD_OUT, "cobraflex_isaac", "cobraflex_isaac.usda")
    if os.path.exists(out) and os.environ.get("BRINGUP_REIMPORT", "0") == "0":
        return out
    os.makedirs(USD_OUT, exist_ok=True)
    # The Isaac 6 importer refuses to overwrite an existing package and writes
    # a suffixed cobraflex_isaac_1/ beside it instead — that run then uses the
    # suffixed copy while the canonical (git-tracked) package and every later
    # cached run silently keep the stale USD. Remove it so BRINGUP_REIMPORT=1
    # genuinely replaces the canonical package.
    pkg_dir = os.path.dirname(out)
    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    cfg = URDFImporterConfig(urdf_path=URDF, usd_path=USD_OUT,
                             merge_fixed_joints=False, merge_mesh=False, fix_base=False)
    return URDFImporter(cfg).import_urdf()


def articulation_root(stage) -> str:
    from pxr import UsdPhysics
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            return prim.GetPath().pathString
    return ROBOT_PATH


def configure_wheel_drives(stage) -> int:
    """Add a velocity (stiffness=0) angular drive to each wheel joint."""
    from pxr import UsdPhysics
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
    from pxr import PhysxSchema, Sdf, UsdPhysics, UsdShade
    from omni.physx.scripts import physicsUtils

    mat_path = WHEEL_MATERIAL_PATH
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


def _add_track_geometry(stage, meta, tdir, offset=(0.0, 0.0)):
    """Build the road + lane lines as USD geometry (crisp at any zoom, no texture
    aliasing) from the centreline, shifted by ``offset`` (multi-track scenes,
    D-50). Better than a baked texture for Isaac. The green off-road backdrop is
    NOT built here — one union quad covers all circuits (see
    ``_add_offroad_backdrop``)."""
    import numpy as np
    import yaml
    from pxr import UsdGeom

    cl = yaml.safe_load(open(os.path.join(tdir, f"{meta['name']}_centerline.yaml")))
    P = np.array(cl["centerline"]["points"], dtype=float)
    P = P + np.asarray(offset, dtype=float)
    rw = float(meta.get("road_width", 0.52))
    two_lane = int(meta.get("lanes", 2)) == 2
    lw = 0.01                                  # line width (m)
    scope = f"/World/Track/{meta['name']}"     # per-track prim scope

    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-9)
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)
    left = P + (rw / 2.0) * nrm
    right = P - (rw / 2.0) * nrm

    # Materials live at the FIXED paths shared by every circuit (idempotent
    # re-define), so isaac_dr's colour jitter applies to all of them at once.
    asphalt = _flat_material(stage, TRACK_ASPHALT_MATERIAL, (0.0, 0.0, 0.0))
    white = _flat_material(stage, TRACK_LINE_MATERIAL, (0.9, 0.9, 0.9))

    _ribbon_mesh(stage, scope + "/Asphalt", left, right, 0.0010, asphalt)
    _ribbon_mesh(stage, scope + "/EdgeL",
                 left + (lw / 2) * nrm, left - (lw / 2) * nrm, 0.0030, white)
    _ribbon_mesh(stage, scope + "/EdgeR",
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
        m = UsdGeom.Mesh.Define(stage, scope + "/Centre")
        m.CreatePointsAttr(pts)
        m.CreateFaceVertexCountsAttr(counts)
        m.CreateFaceVertexIndicesAttr(idx)
        _bind(m.GetPrim(), white)
    print(f"[scene] track '{meta['name']}' built as geometry "
          f"({meta['size_m'][0]:.1f}x{meta['size_m'][1]:.1f} m, "
          f"{'2-lane' if two_lane else '1-lane'}, "
          f"offset ({offset[0]:+.1f}, {offset[1]:+.1f}))")


def _add_offroad_backdrop(stage, world_bboxes, margin: float = 20.0):
    """One green quad under ALL circuits (union bbox + margin) so everything a
    pitched camera sees to the horizon is grass, exactly like a single-track
    scene — including the inter-track gaps."""
    from pxr import UsdGeom

    x0 = min(b[0] for b in world_bboxes) - margin
    y0 = min(b[1] for b in world_bboxes) - margin
    x1 = max(b[2] for b in world_bboxes) + margin
    y1 = max(b[3] for b in world_bboxes) + margin
    grass = _flat_material(stage, TRACK_GRASS_MATERIAL, (0.32, 0.42, 0.24))
    g = UsdGeom.Mesh.Define(stage, "/World/Track/Offroad")
    g.CreatePointsAttr([(x0, y0, 0.0006), (x1, y0, 0.0006),
                        (x1, y1, 0.0006), (x0, y1, 0.0006)])
    g.CreateFaceVertexCountsAttr([4])
    g.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    _bind(g.GetPrim(), grass)


def _add_track_texture(stage, meta, tdir, offset=(0.0, 0.0)):
    from pxr import Gf, Sdf, UsdGeom, UsdShade
    png = os.path.join(tdir, meta["texture"])
    cx, cy = meta["center_m"]
    cx, cy = cx + float(offset[0]), cy + float(offset[1])
    w, h = meta["size_m"]
    hw, hh = w / 2.0, h / 2.0
    scope = f"/World/Track/{meta['name']}"
    quad = UsdGeom.Mesh.Define(stage, scope)
    quad.CreatePointsAttr([(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)])
    quad.CreateFaceVertexCountsAttr([4])
    quad.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    st = UsdGeom.PrimvarsAPI(quad.GetPrim()).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
    st.Set([(0, 0), (1, 0), (1, 1), (0, 1)])
    UsdGeom.Xformable(quad.GetPrim()).AddTranslateOp().Set(Gf.Vec3d(cx, cy, 0.0015))
    mtl = UsdShade.Material.Define(stage, scope + "/Mat")
    surf = UsdShade.Shader.Define(stage, scope + "/Mat/Surface")
    surf.CreateIdAttr("UsdPreviewSurface")
    surf.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
    streader = UsdShade.Shader.Define(stage, scope + "/Mat/St")
    streader.CreateIdAttr("UsdPrimvarReader_float2")
    streader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    tex = UsdShade.Shader.Define(stage, scope + "/Mat/Tex")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(png)
    tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        streader.ConnectableAPI(), "result")
    surf.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        tex.ConnectableAPI(), "rgb")
    mtl.CreateSurfaceOutput().ConnectToSource(surf.ConnectableAPI(), "surface")
    _bind(quad.GetPrim(), mtl)
    print(f"[scene] track '{meta['name']}' loaded as texture "
          f"({w:.1f}x{h:.1f} m, offset ({offset[0]:+.1f}, {offset[1]:+.1f}))")


def track_offsets(metas):
    """World offset (dx, dy) per track for a multi-track scene: the first track
    keeps its native coordinates (existing single-track runs are unchanged) and
    each subsequent one is laid out to +X with a TRACK_GAP_M gap between
    bounding boxes. Single source for the scene builder AND the trainer (which
    must shift the matching centerline configs by the same offsets)."""
    offsets = []
    cursor = None
    for meta in metas:
        x0, _y0, x1, _y1 = meta["world_bbox"]
        if cursor is None:
            offsets.append((0.0, 0.0))
        else:
            dx = cursor + TRACK_GAP_M - x0
            offsets.append((dx, 0.0))
        cursor = x1 + offsets[-1][0]
    return offsets


def parse_track_names(raw=None):
    """TRACK env (or an explicit string) → list of track names. Accepts a
    comma-separated list for multi-track scenes: TRACK=complex_b,complex_d."""
    if raw is None:
        raw = os.environ.get("TRACK", "complex_a")
    return [t.strip() for t in str(raw).split(",") if t.strip()]


def load_circuits(track_names, track_metas, config_dir=None):
    """Multi-track env geometry (D-50): for each scene track, load the two
    centerline YAMLs by the config-dir naming convention
    (``<name>_right_lane_centerline.yaml`` = reward lane,
    ``<name>_centerline.yaml`` = road centre) and shift their points by the
    world offset the scene builder applied (``meta["offset_xy"]``), so the env
    geometry and the rendered track coincide exactly.

    Returns ``(circuits, circuits_meta)`` — the ``GazeboLaneEnv(circuits=...)``
    input and the reproducibility record (paths + sha256 hashes). Pure
    python/numpy/yaml — usable (and unit-testable) off the Isaac host.
    """
    import hashlib

    import numpy as np
    import yaml

    def _sha256(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    if config_dir is None:
        config_dir = os.path.join(REPO, "src", "cobraflex_rl", "config")
    meta_by_name = {m["name"]: m for m in track_metas}
    circuits, circuits_meta = [], []
    for name in track_names:
        meta = meta_by_name.get(name)
        if meta is None:
            raise RuntimeError(
                f"scene did not build track '{name}' (missing assets under "
                f"experiments/sim/tracks/{name}/ — run "
                f"scripts/generate_complex_track.py --name {name})")
        lane_path = os.path.join(config_dir, f"{name}_right_lane_centerline.yaml")
        road_path = os.path.join(config_dir, f"{name}_centerline.yaml")
        for path in (lane_path, road_path):
            if not os.path.isfile(path):
                raise RuntimeError(
                    f"missing centerline config {path} for track '{name}' "
                    "(derive it with scripts/offset_lane_centerline.py)")
        with open(lane_path, "r", encoding="utf-8") as fh:
            lane_cfg = yaml.safe_load(fh)
        with open(road_path, "r", encoding="utf-8") as fh:
            road_cfg = yaml.safe_load(fh)
        offset = np.asarray(meta.get("offset_xy", (0.0, 0.0)), dtype=float)
        lane_width = float(lane_cfg["lane_width"])
        circuits.append({
            "name": name,
            "centerline": np.asarray(
                lane_cfg["centerline"]["points"], dtype=float) + offset,
            "lane_width": lane_width,
            "road_width": float(lane_cfg.get("road_width", lane_width)),
            "road_centerline": np.asarray(
                road_cfg["centerline"]["points"], dtype=float) + offset,
        })
        circuits_meta.append({
            "name": name,
            "offset_xy": [float(offset[0]), float(offset[1])],
            "lane_centerline_yaml": lane_path,
            "lane_centerline_hash": _sha256(lane_path),
            "road_centerline_yaml": road_path,
            "road_centerline_hash": _sha256(road_path),
        })
    return circuits, circuits_meta


def add_track(stage):
    """Build the generated track(s) (scripts/generate_complex_track.py).
    Geometry by default (crisp vector lines); TRACK_MODE=texture for the baked
    PNG. The TRACK env selects the track dir(s) — a comma-separated list builds
    a multi-track scene (D-50) with TRACK_GAP_M between circuits and one shared
    off-road backdrop. Returns a list of meta dicts (possibly empty), each with
    ``offset_xy`` added and ``start_xy``/``world_bbox`` shifted to world
    coordinates."""
    import yaml

    names = parse_track_names()
    loaded = []
    for name in names:
        tdir = os.path.join(REPO, "experiments/sim/tracks", name)
        meta_path = os.path.join(tdir, f"{name}_meta.yaml")
        if not os.path.exists(meta_path):
            print(f"[scene] no track '{name}' at {meta_path}, skipping")
            continue
        loaded.append((yaml.safe_load(open(meta_path)), tdir))
    if not loaded:
        return []

    offsets = track_offsets([meta for meta, _ in loaded])
    texture_mode = os.environ.get("TRACK_MODE", "geom") == "texture"
    metas = []
    for (meta, tdir), (dx, dy) in zip(loaded, offsets):
        if texture_mode:
            _add_track_texture(stage, meta, tdir, offset=(dx, dy))
        else:
            _add_track_geometry(stage, meta, tdir, offset=(dx, dy))
        out = dict(meta)
        out["offset_xy"] = [dx, dy]
        out["start_xy"] = [meta["start_xy"][0] + dx, meta["start_xy"][1] + dy]
        x0, y0, x1, y1 = meta["world_bbox"]
        out["world_bbox"] = [x0 + dx, y0 + dy, x1 + dx, y1 + dy]
        out["center_m"] = [meta["center_m"][0] + dx, meta["center_m"][1] + dy]
        metas.append(out)
    _add_offroad_backdrop(stage, [m["world_bbox"] for m in metas])
    return metas


def find_prim(stage, name: str) -> str:
    for prim in stage.Traverse():
        if prim.GetName() == name:
            return prim.GetPath().pathString
    return ""


# Backwards-compatible private alias (the bring-up referenced _find_prim).
_find_prim = find_prim


def make_camera_prim(stage, parent_path, hfov, width, height):
    """Define a USD Camera under the ROS optical frame with matching intrinsics."""
    from pxr import Gf, UsdGeom
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


_make_camera_prim = make_camera_prim


def make_lane_camera(stage):
    """Create the Lane Cam USD Camera prim under its optical frame and return its
    path (for an in-process Replicator render product), or None if the frame is
    absent. Intrinsics match the ROS2 bring-up's lane camera (640x360, HFOV 90)."""
    frame_path = find_prim(stage, LANE_CAM_FRAME)
    if not frame_path:
        return None
    return make_camera_prim(stage, frame_path, LANE_CAM_HFOV, LANE_CAM_W, LANE_CAM_H)


def dr_scene_paths(stage, articulation_root_path: str) -> dict:
    """Prim-path map for :class:`isaac_dr.IsaacDomainRandomizer`.

    Lights + physics materials are always present; the geometry-mode track
    materials exist only when the track was built as vector geometry (the
    default; ``TRACK_MODE=texture`` omits them, so those keys are dropped and the
    colour DR for them becomes a no-op). ``articulation_root`` is for mass DR."""
    paths = {
        "dome_light": DOME_LIGHT_PATH,
        "distant_light": DISTANT_LIGHT_PATH,
        "wheel_material": WHEEL_MATERIAL_PATH,
        "ground_material": GROUND_MATERIAL_PATH,
        "articulation_root": articulation_root_path,
    }
    for key, path in (
        ("asphalt_material", TRACK_ASPHALT_MATERIAL),
        ("line_material", TRACK_LINE_MATERIAL),
        ("grass_material", TRACK_GRASS_MATERIAL),
    ):
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            paths[key] = path
    return paths


def build_world():
    """Build the physics scene (world, lights, ground, track, robot, drives,
    friction) shared by the bring-up and the trainer. Does **not** add ROS2
    sensor graphs — that stays in the bring-up.

    Robot spawn: ``CAM_POSE="x,y,yaw"`` if set, else the FIRST track's start
    line, else the origin (the per-episode RL teleport overrides this
    immediately). Returns ``(world, track_metas)`` where ``track_metas`` is the
    (possibly empty) list from :func:`add_track` — one meta per circuit, offsets
    baked in.
    """
    import omni.usd
    from isaacsim.core.api import World
    from isaacsim.core.api.materials import PhysicsMaterial
    from isaacsim.core.api.objects.ground_plane import GroundPlane
    from isaacsim.core.prims import SingleXFormPrim
    from isaacsim.core.utils.stage import add_reference_to_stage
    from pxr import Gf, UsdLux

    world = World(stage_units_in_meters=1.0)
    stage = omni.usd.get_context().get_stage()

    # Lighting: the explicit GroundPlane leaves the stage with no light, so the
    # RTX viewport renders all black. Add a dome + distant light.
    dome = UsdLux.DomeLight.Define(stage, DOME_LIGHT_PATH)
    dome.CreateIntensityAttr(1000.0)
    sun = UsdLux.DistantLight.Define(stage, DISTANT_LIGHT_PATH)
    sun.CreateIntensityAttr(3000.0)
    sun.CreateAngleAttr(0.53)

    # Explicit ground with a known friction so the wheel/ground contact pair is
    # fully under our control (combine=min on the wheel material then wins).
    gmat = PhysicsMaterial(GROUND_MATERIAL_PATH,
                           static_friction=GROUND_FRICTION,
                           dynamic_friction=GROUND_FRICTION, restitution=0.0)
    GroundPlane("/World/groundPlane", z_position=0.0, physics_material=gmat)

    track_metas = add_track(stage)

    usd_path = ensure_robot_usd()
    add_reference_to_stage(usd_path, ROBOT_PATH)
    cam_pose = os.environ.get("CAM_POSE", "")
    if cam_pose:
        sx, sy, yaw = (float(v) for v in cam_pose.split(","))
        quat = Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(yaw)).GetQuat()
        SingleXFormPrim(ROBOT_PATH, position=(sx, sy, SPAWN_Z),
                        orientation=(quat.GetReal(), *quat.GetImaginary()))
    elif track_metas:
        sx, sy = track_metas[0]["start_xy"]
        yaw = float(track_metas[0]["start_yaw"])
        quat = Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(yaw)).GetQuat()
        SingleXFormPrim(ROBOT_PATH, position=(sx, sy, SPAWN_Z),
                        orientation=(quat.GetReal(), *quat.GetImaginary()))
    else:
        SingleXFormPrim(ROBOT_PATH, position=(0.0, 0.0, SPAWN_Z))

    nd = configure_wheel_drives(stage)
    nm = configure_wheel_material(stage, WHEEL_FRICTION)
    print(f"[scene] velocity drives on {nd} wheel joints; friction "
          f"{WHEEL_FRICTION} (combine=min) on {nm} wheel colliders, "
          f"ground {GROUND_FRICTION}")
    return world, track_metas
