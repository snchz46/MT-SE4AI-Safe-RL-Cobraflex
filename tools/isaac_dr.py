"""Per-episode domain randomization for in-process Isaac-Sim training.

Complements the image-level visual DR (``visual_domain_randomization.py``, which
corrupts the *rendered frame*) with **physics** and **scene** randomization
applied once on every episode reset — so the trained policy sees a *distribution*
of dynamics and appearances instead of a single (un-calibrated) nominal. These
are the sim-to-real levers #2 (dynamics DR) and #4 (scene DR); the actuation
latency (#3) is sampled here and read back by the interface.

Three independent, config-gated aspects, all re-sampled per episode:

- **dynamics** — wheel/ground friction, a base-mass scale, and a yaw-rate gain
  on the commanded angular velocity. Widens the un-calibrated skid-steer yaw
  response (cf. the ``WHEEL_FRICTION`` note in ``isaac_scene.py``) until
  real-platform system-ID lands and the nominal can be pinned.
- **latency** — a per-episode actuation delay (N control cycles). Sampled here;
  the interface buffers wheel commands and applies the N-steps-old one.
- **scene** — dome/distant light intensity + tint, and the asphalt / lane-line /
  grass diffuse colours, for CnnPolicy appearance robustness (shadows, exposure
  and surface-colour shifts the image-level degradation cannot reproduce).

Reproducible via a seeded ``numpy`` Generator (seed mirrors the PPO seed). Every
``pxr`` import is deferred into a method per ``isaac_scene``'s import-order
contract, so importing this module off the Isaac host stays safe (pytest, the
campaign runner) — only ``numpy`` is pulled in at module top level.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np


class IsaacDomainRandomizer:
    """Sample + apply per-episode physics/scene randomization on a live world.

    Parameters
    ----------
    stage:
        The live USD stage (``omni.usd.get_context().get_stage()``).
    articulation:
        The robot ``SingleArticulation`` (for mass scaling; best-effort).
    dynamics_cfg, scene_cfg:
        The ``dynamics_randomization`` / ``scene_randomization`` config blocks
        (plain dicts from the train YAML). Each is inert unless ``enabled``.
    seed:
        Seeds the internal ``numpy`` Generator (mirror the PPO seed for a
        reproducible episode-parameter stream).
    scene_paths:
        Prim-path map from :func:`isaac_scene.dr_scene_paths` (material/light/
        articulation-root paths to randomize). A missing key disables that aspect.
    logger:
        Optional object with ``info``/``warning`` (the interface's print-logger);
        used to surface a best-effort mass-DR no-op once.
    """

    def __init__(
        self,
        stage,
        articulation,
        *,
        dynamics_cfg: Optional[Mapping[str, Any]] = None,
        scene_cfg: Optional[Mapping[str, Any]] = None,
        seed: int = 0,
        scene_paths: Optional[Mapping[str, str]] = None,
        logger=None,
    ) -> None:
        self._stage = stage
        self._articulation = articulation
        self._dyn = dict(dynamics_cfg or {})
        self._scene = dict(scene_cfg or {})
        self._dyn_on = bool(self._dyn.get("enabled", False))
        self._scene_on = bool(self._scene.get("enabled", False))
        self._rng = np.random.default_rng(int(seed))
        self._paths = dict(scene_paths or {})
        self._logger = logger

        # Per-episode dynamics outputs the interface reads after randomize_episode().
        self.yaw_scale: float = 1.0
        self.latency_steps: int = 0

        # Nominals captured lazily on the first scene/mass randomize so we scale
        # about the as-built values rather than a guessed constant.
        self._dome_nom: Optional[float] = None
        self._sun_nom: Optional[float] = None
        self._link_base_mass: Optional[Dict[str, float]] = None
        self._mass_warned = False

    @property
    def active(self) -> bool:
        return self._dyn_on or self._scene_on

    # --- top-level -----------------------------------------------------------
    def randomize_episode(self) -> None:
        """Re-sample + apply all enabled DR aspects for a fresh episode."""
        if self._dyn_on:
            self._randomize_dynamics()
        if self._scene_on:
            self._randomize_scene()

    def _u(self, rng_range: Optional[Sequence[float]]) -> float:
        """Uniform sample from a 2-tuple; 1.0 when the range is absent."""
        if not rng_range:
            return 1.0
        lo, hi = float(rng_range[0]), float(rng_range[1])
        return float(self._rng.uniform(lo, hi))

    # --- dynamics ------------------------------------------------------------
    def _randomize_dynamics(self) -> None:
        # yaw-gain + latency are pure-Python outputs consumed by the interface.
        self.yaw_scale = self._u(self._dyn.get("yaw_scale_range"))
        lr = self._dyn.get("latency_steps_range")
        if lr:
            lo, hi = int(lr[0]), int(lr[1])
            self.latency_steps = int(self._rng.integers(lo, hi + 1))
        else:
            self.latency_steps = 0
        # friction + mass touch USD/PhysX.
        fr = self._dyn.get("friction_range")
        if fr:
            self._set_friction(self._u(fr))
        mr = self._dyn.get("mass_scale_range")
        if mr:
            self._set_mass_scale(self._u(mr))

    def _set_friction(self, friction: float) -> None:
        """Set static+dynamic friction on the wheel and ground physics materials.

        Both are set to the *same* value: the wheel material binds with
        ``combine=min`` against the ground (see ``isaac_scene.configure_wheel_
        material``), so randomizing only one would be clamped by the other."""
        from pxr import UsdPhysics

        for key in ("wheel_material", "ground_material"):
            path = self._paths.get(key)
            if not path:
                continue
            prim = self._stage.GetPrimAtPath(path)
            if not prim or not prim.IsValid():
                continue
            mat = UsdPhysics.MaterialAPI(prim)
            mat.CreateStaticFrictionAttr().Set(float(friction))
            mat.CreateDynamicFrictionAttr().Set(float(friction))

    def _set_mass_scale(self, scale: float) -> None:
        """Scale every rigid-body link mass under the articulation by ``scale``.

        Best-effort: links whose mass is auto-derived from collision density
        carry no explicit ``physics:mass`` (Get() is 0/None) and are skipped; if
        *no* link has an explicit mass the pass is a no-op (warned once)."""
        from pxr import UsdPhysics

        root = self._paths.get("articulation_root")
        if not root:
            return
        root_prim = self._stage.GetPrimAtPath(root)
        if not root_prim or not root_prim.IsValid():
            return

        if self._link_base_mass is None:
            # Capture as-built explicit masses once, so repeated episodes scale
            # the nominal rather than compounding previous scales.
            self._link_base_mass = {}
            for prim in self._stage.Traverse():
                if not prim.GetPath().pathString.startswith(root):
                    continue
                if not prim.HasAPI(UsdPhysics.MassAPI):
                    continue
                attr = UsdPhysics.MassAPI(prim).GetMassAttr()
                val = attr.Get() if attr else None
                if val:  # explicit, non-zero mass
                    self._link_base_mass[prim.GetPath().pathString] = float(val)
            if not self._link_base_mass and not self._mass_warned:
                self._mass_warned = True
                if self._logger is not None:
                    self._logger.warning(
                        "mass DR is a no-op: no link carries an explicit "
                        "physics:mass (masses are density-derived). Set explicit "
                        "link masses in the URDF to enable mass randomization."
                    )

        for path, base in self._link_base_mass.items():
            prim = self._stage.GetPrimAtPath(path)
            if prim and prim.IsValid():
                UsdPhysics.MassAPI(prim).CreateMassAttr().Set(float(base * scale))

    # --- scene ---------------------------------------------------------------
    def _randomize_scene(self) -> None:
        self._randomize_lights()
        self._randomize_track_colors()

    def _randomize_lights(self) -> None:
        from pxr import Gf, UsdLux

        tint = float(self._scene.get("light_tint", 0.0))
        for path_key, scale_key, nom_attr in (
            ("dome_light", "dome_intensity_scale", "_dome_nom"),
            ("distant_light", "sun_intensity_scale", "_sun_nom"),
        ):
            path = self._paths.get(path_key)
            if not path:
                continue
            prim = self._stage.GetPrimAtPath(path)
            if not prim or not prim.IsValid():
                continue
            light = UsdLux.LightAPI(prim)
            inten = light.GetIntensityAttr()
            nom = getattr(self, nom_attr)
            if nom is None:
                got = inten.Get() if inten else None
                nom = float(got) if got is not None else 1000.0
                setattr(self, nom_attr, nom)
            inten.Set(float(nom * self._u(self._scene.get(scale_key))))
            if tint > 0.0:
                c = 1.0 + self._rng.uniform(-tint, tint, size=3)
                light.GetColorAttr().Set(
                    Gf.Vec3f(float(c[0]), float(c[1]), float(c[2]))
                )

    def _randomize_track_colors(self) -> None:
        from pxr import Gf, UsdShade

        # (base diffuse colour, jitter cfg key, brighten-only). Asphalt is near
        # black, so it is only lifted upward (a symmetric jitter would clip to 0).
        specs = (
            ("asphalt_material", (0.0, 0.0, 0.0), "asphalt_jitter", True),
            ("line_material", (0.9, 0.9, 0.9), "line_jitter", False),
            ("grass_material", (0.32, 0.42, 0.24), "grass_jitter", False),
        )
        for path_key, base_rgb, jitter_key, brighten_only in specs:
            jit = float(self._scene.get(jitter_key, 0.0))
            if jit <= 0.0:
                continue
            path = self._paths.get(path_key)
            if not path:
                continue
            shader = UsdShade.Shader.Get(self._stage, path + "/S")
            if not shader or not shader.GetPrim().IsValid():
                continue
            inp = shader.GetInput("diffuseColor")
            if not inp:
                continue
            base = np.asarray(base_rgb, dtype=float)
            if brighten_only:
                col = np.clip(base + float(self._rng.uniform(0.0, jit)), 0.0, 1.0)
            else:
                col = np.clip(base + self._rng.uniform(-jit, jit, size=3), 0.0, 1.0)
            inp.Set(Gf.Vec3f(float(col[0]), float(col[1]), float(col[2])))
