"""Export a generated track as a portable mesh (OBJ always; USD if pxr available).

The Isaac bring-up builds the track geometry procedurally in memory; this writes
it to a standalone file you can hand to someone else. The geometry matches
tools/isaac_ros2_bringup.py:_add_track_geometry (asphalt ribbon + white edge /
centre-line strips + a green off-road quad), derived from the centreline YAML.

Run:
    python  scripts/export_track_mesh.py --name complex_b          # -> .obj + .mtl
    ~/isaacsim/python.sh scripts/export_track_mesh.py --name complex_b   # also .usda

Output: experiments/sim/tracks/<name>/<name>.obj (+ .mtl) [+ <name>.usda].
The frame is Z-up, metres (Isaac/USD native; in Blender pick "Z up" on import).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import yaml

REPO = Path(__file__).resolve().parents[1]
LW = 0.01            # line width (m)
MATS = {             # name -> (r, g, b)
    "asphalt": (0.02, 0.02, 0.02),
    "line": (0.9, 0.9, 0.9),
    "grass": (0.32, 0.42, 0.24),
}


def _ribbon(inner, outer, z):
    n = len(inner)
    out = []
    for i in range(n):
        j = (i + 1) % n
        out.append([(inner[i][0], inner[i][1], z), (outer[i][0], outer[i][1], z),
                    (outer[j][0], outer[j][1], z), (inner[j][0], inner[j][1], z)])
    return out


def _dashes(P, nrm, z, dash=0.10, gap=0.10):
    seg = np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    out, pos = [], 0.0
    while pos < s[-1]:
        ia = int(np.searchsorted(s, pos)) % len(P)
        ib = int(np.searchsorted(s, min(pos + dash, s[-1]))) % len(P)
        pa, pb, na = P[ia], P[ib], nrm[ia]
        out.append([(pa[0] + LW / 2 * na[0], pa[1] + LW / 2 * na[1], z),
                    (pa[0] - LW / 2 * na[0], pa[1] - LW / 2 * na[1], z),
                    (pb[0] - LW / 2 * na[0], pb[1] - LW / 2 * na[1], z),
                    (pb[0] + LW / 2 * na[0], pb[1] + LW / 2 * na[1], z)])
        pos += dash + gap
    return out


def build_meshes(name):
    tdir = REPO / "experiments/sim/tracks" / name
    meta = yaml.safe_load((tdir / f"{name}_meta.yaml").read_text())
    cl = yaml.safe_load((tdir / f"{name}_centerline.yaml").read_text())
    P = np.array(cl["centerline"]["points"], dtype=float)
    rw = float(meta.get("road_width", 0.52))
    two_lane = int(meta.get("lanes", 2)) == 2
    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    t /= (np.linalg.norm(t, axis=1, keepdims=True) + 1e-9)
    nrm = np.stack([-t[:, 1], t[:, 0]], axis=1)
    left, right = P + rw / 2 * nrm, P - rw / 2 * nrm
    x0, y0, x1, y1 = meta["world_bbox"]

    groups = {
        "grass": [[(x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)]],
        "asphalt": _ribbon(left, right, 0.001),
        "line": (_ribbon(left + LW / 2 * nrm, left - LW / 2 * nrm, 0.003)
                 + _ribbon(right + LW / 2 * nrm, right - LW / 2 * nrm, 0.003)
                 + (_dashes(P, nrm, 0.003) if two_lane else [])),
    }
    return groups, meta


def write_obj(groups, obj_path: Path):
    mtl_path = obj_path.with_suffix(".mtl")
    mtl_path.write_text("".join(
        f"newmtl {n}\nKd {r:.3f} {g:.3f} {b:.3f}\nKa {r:.3f} {g:.3f} {b:.3f}\nd 1\n\n"
        for n, (r, g, b) in MATS.items()))
    lines = [f"# track mesh, Z-up, metres\nmtllib {mtl_path.name}\n"]
    vi = 1
    for mat, quads in groups.items():
        lines.append(f"usemtl {mat}\no {mat}\n")
        for q in quads:
            for v in q:
                lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
            lines.append(f"f {vi} {vi+1} {vi+2} {vi+3}\n")
            vi += 4
    obj_path.write_text("".join(lines))
    nq = sum(len(q) for q in groups.values())
    print(f"[export] wrote {obj_path}  (+ {mtl_path.name})  {nq} quads")


def write_usd(groups, usd_path: Path):
    try:
        from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    except ImportError:
        print("[export] pxr not available -> skipping USD "
              "(run with ~/isaacsim/python.sh for a .usda)")
        return
    stage = Usd.Stage.CreateNew(str(usd_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    root = UsdGeom.Xform.Define(stage, "/Track")
    stage.SetDefaultPrim(root.GetPrim())
    for mat, quads in groups.items():
        if not quads:
            continue
        mtl = UsdShade.Material.Define(stage, f"/Track/Mat_{mat}")
        sh = UsdShade.Shader.Define(stage, f"/Track/Mat_{mat}/S")
        sh.CreateIdAttr("UsdPreviewSurface")
        sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(*MATS[mat]))
        sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
        mtl.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
        pts, counts, idx, k = [], [], [], 0
        for q in quads:
            for v in q:
                pts.append(Gf.Vec3f(float(v[0]), float(v[1]), float(v[2])))
            idx += [k, k + 1, k + 2, k + 3]
            counts.append(4)
            k += 4
        m = UsdGeom.Mesh.Define(stage, f"/Track/{mat}")
        m.CreatePointsAttr(pts)
        m.CreateFaceVertexCountsAttr(counts)
        m.CreateFaceVertexIndicesAttr(idx)
        UsdShade.MaterialBindingAPI(m.GetPrim()).Apply(m.GetPrim())
        UsdShade.MaterialBindingAPI(m.GetPrim()).Bind(mtl)
    stage.GetRootLayer().Save()
    print(f"[export] wrote {usd_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="complex_b")
    args = ap.parse_args()
    groups, _ = build_meshes(args.name)
    tdir = REPO / "experiments/sim/tracks" / args.name
    write_obj(groups, tdir / f"{args.name}.obj")
    write_usd(groups, tdir / f"{args.name}.usda")


if __name__ == "__main__":
    main()
