"""One-off validation render: aerial view of the D-50 multi-track scene.

The bring-up's --shot positions its camera from a single track's meta (13 m up),
which cannot frame the ~60 m three-circuit scene. This script reuses the exact
shared scene builder (isaac_scene.build_world, same code path as the trainer)
and renders one wide top-down PNG framing the union bbox.

Run:  TRACK=complex_b,complex_d,complex_e ~/isaacsim/python.sh multi_aerial_shot.py out.png
"""
import math
import os
import sys

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

sys.path.insert(0, "/media/samuel/Fast_SSD/SE4AI/thesis_repo/tools")

from isaacsim.core.utils.extensions import enable_extension  # noqa: E402

enable_extension("isaacsim.asset.importer.urdf")
simulation_app.update()

import isaac_scene  # noqa: E402

rc = 1
try:
    out_png = sys.argv[1] if len(sys.argv) > 1 else "multi_aerial.png"
    world, metas = isaac_scene.build_world()
    if not metas:
        raise RuntimeError("no tracks built — set TRACK")
    world.reset()

    import omni.replicator.core as rep
    from PIL import Image

    x0 = min(m["world_bbox"][0] for m in metas)
    x1 = max(m["world_bbox"][2] for m in metas)
    y0 = min(m["world_bbox"][1] for m in metas)
    y1 = max(m["world_bbox"][3] for m in metas)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    # Square render: the top-down look_at camera's image-up convention maps
    # world X to the short axis, so a square frame is orientation-proof.
    W, H = 1600, 1600
    focal, aperture = 18.0, 20.955
    hfov = 2.0 * math.atan(aperture / (2.0 * focal))
    span = max(x1 - x0, y1 - y0) + 8.0
    z = (span / 2.0) / math.tan(hfov / 2.0)
    print(f"[multi_shot] union bbox x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}] "
          f"cam=({cx:.2f},{cy:.2f},{z:.1f})")
    cam = rep.create.camera(position=(cx, cy, z), look_at=(cx, cy, 0.0),
                            focal_length=focal)
    rp = rep.create.render_product(cam, (W, H))
    annot = rep.AnnotatorRegistry.get_annotator("rgb")
    annot.attach(rp)
    for _ in range(60):
        world.step(render=True)
    Image.fromarray(annot.get_data()[..., :3]).save(out_png)
    print(f"[multi_shot] saved {out_png}")
    for m in metas:
        print(f"[multi_shot] {m['name']}: offset_xy={m['offset_xy']} "
              f"start_xy={m['start_xy']} start_yaw={m['start_yaw']}")
    rc = 0
except Exception:
    import traceback

    traceback.print_exc()
    rc = 2
finally:
    simulation_app.close()
sys.exit(rc)
