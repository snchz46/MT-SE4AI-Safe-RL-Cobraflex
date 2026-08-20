"""
visual_domain_randomization — per-episode visual-degradation sampler for E-training.

Track 'E' (D-41/D-42): SR-012 mitigates H-10 partly through a *training constraint* —
the camera policy is trained under randomised visual degradations so it is robust
across the SC-PERT-04..06 envelope (glare, low-light, motion blur). This module is
the **sampler**: given a numpy ``Generator`` it draws a per-episode degradation spec
(mode + level), which the training env then applies to each camera frame via
:func:`cobraflex_rl.visual_degradation.degrade`.

Pure (numpy ``Generator`` + stdlib), deterministic given the RNG, host-testable. The
Gazebo camera env that draws a spec at ``reset()`` and applies it in the observation
bridge is the Ubuntu part.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from cobraflex_rl.visual_degradation import MODES, TRAINABLE_MODES, degrade


@dataclass(frozen=True)
class DegradationSpec:
    """A drawn per-episode degradation.

    Two independent terms, applied in this order:

    ``base_mode``/``base_level``
        the episode's **operating point** — what the camera sees on a normal
        day. Drawn on its own schedule (see :class:`DomainRandomizationConfig`),
        because a photometric operating point is not an event that sometimes
        happens; it is the condition the vehicle is always in.
    ``mode``/``level``
        the H-10 **stressor** drawn on top: glare, dusk, motion blur. These are
        events, and the existing ``p_degrade`` schedule is right for them.

    Both default to absent, which is exactly the old one-term behaviour.
    """

    mode: Optional[str]
    level: float
    base_mode: Optional[str] = None
    base_level: float = 0.0

    @property
    def is_clean(self) -> bool:
        return self.mode is None and self.base_mode is None


@dataclass(frozen=True)
class DomainRandomizationConfig:
    """Sampler configuration.

    Attributes
    ----------
    p_degrade:
        Probability that an episode receives a degradation at all (otherwise clean).
    modes:
        Degradation modes to draw from (a subset of
        :data:`cobraflex_rl.visual_degradation.TRAINABLE_MODES`). Defaults to the
        frozen H-10 trio ``MODES`` so an existing training config is unchanged;
        a sim-to-real run opts into ``low_contrast`` by naming it explicitly
        (``domain_randomization.modes`` in the training YAML).
    level_range:
        ``(low, high)`` within ``[0, 1]`` for the sampled intensity.
    base_mode:
        Optional **operating-point** mode applied to every drawn episode with
        probability ``p_base``, *before* the stressor above. ``None`` (default)
        reproduces the old single-term sampler exactly, down to the RNG stream.

        This exists because putting ``low_contrast`` in ``modes`` misrepresents
        it. The sampler draws one stressor per episode, so a four-mode list at
        ``p_degrade 0.5`` would show the policy the physical track's photometry
        in ~12 % of episodes — as if a mid-grey floor were a rare event. It is
        not an event; M-7 measured it as the constant condition of the hall
        (road grey 106 ± 3 across a 1521-frame circuit survey). Drawn as a base
        term with ``base_level_range=(0.0, 1.0)`` the policy instead sees the
        whole road-albedo axis every episode, from the Gazebo render at one end
        to the measured hall at the other, with the H-10 stressors still landing
        on top at their own rate.
    p_base:
        Probability the base term is drawn when ``base_mode`` is set. Default
        1.0: with a level range that includes 0 (the identity), a Bernoulli gate
        on top only removes coverage.
    base_level_range:
        ``(low, high)`` within ``[0, 1]`` for the base term's intensity.
    base_level_focus_range:
        Optional **second** band for the base term, drawn with probability
        ``p_base_focus`` in place of ``base_level_range``. ``None`` (default)
        keeps the single-band sampler, RNG stream included.

        This exists because a uniform draw over the whole road-albedo axis spends
        half its episodes far from where the vehicle actually lives. The 19.08
        fine-tune ran 285k steps of uniform ``[0, 1]`` and reached only 28 %
        retention of the sim arm's lane response at the measured hall point —
        the gate wants 50 %. Splitting the draw concentrates the mass where
        deployment is (``base_level_focus_range`` ~ the hall band) while keeping
        a deliberate minority at the Gazebo render itself, because every scored
        campaign still evaluates there and level 0 must stay in distribution.

        The two bands are *not* required to be disjoint or ordered; they are two
        uniform draws with a Bernoulli between them, and overlapping them simply
        reweights the overlap.
    p_base_focus:
        Probability the focus band is used when it is set. Default 0.75.
    """

    p_degrade: float = 0.5
    modes: Tuple[str, ...] = MODES
    level_range: Tuple[float, float] = (0.2, 1.0)
    base_mode: Optional[str] = None
    p_base: float = 1.0
    base_level_range: Tuple[float, float] = (0.0, 1.0)
    base_level_focus_range: Optional[Tuple[float, float]] = None
    p_base_focus: float = 0.75

    def __post_init__(self) -> None:
        if not 0.0 <= self.p_degrade <= 1.0:
            raise ValueError("p_degrade must be in [0, 1]")
        if not 0.0 <= self.p_base <= 1.0:
            raise ValueError("p_base must be in [0, 1]")
        if not self.modes:
            raise ValueError("modes must be non-empty")
        unknown = [m for m in self.modes if m not in TRAINABLE_MODES]
        if self.base_mode is not None and self.base_mode not in TRAINABLE_MODES:
            unknown = unknown + [self.base_mode]
        if unknown:
            raise ValueError(
                f"unknown modes {unknown}; trainable modes are {TRAINABLE_MODES}"
            )
        if not 0.0 <= self.p_base_focus <= 1.0:
            raise ValueError("p_base_focus must be in [0, 1]")
        if self.base_level_focus_range is not None and self.base_mode is None:
            raise ValueError(
                "base_level_focus_range set without base_mode: there is no base "
                "term for it to reweight"
            )
        ranges = [
            ("level_range", self.level_range),
            ("base_level_range", self.base_level_range),
        ]
        if self.base_level_focus_range is not None:
            ranges.append(("base_level_focus_range", self.base_level_focus_range))
        for name, (lo, hi) in ranges:
            if not (0.0 <= lo <= hi <= 1.0):
                raise ValueError(f"{name} must satisfy 0 <= low <= high <= 1")


class VisualDomainRandomizer:
    """Draws per-episode :class:`DegradationSpec`s and applies them to camera frames."""

    def __init__(self, config: Optional[DomainRandomizationConfig] = None) -> None:
        self.config = config or DomainRandomizationConfig()

    def sample(self, rng: np.random.Generator) -> DegradationSpec:
        """Draw a per-episode degradation spec using the numpy ``Generator`` ``rng``.

        Deterministic given the generator's state, so a seeded training run is
        reproducible (cf. the F3 seed/reproducibility policy, docs/09 §7.2.7).

        The base term is drawn first, but **only consumes RNG when it is
        configured** — so a config without ``base_mode`` draws the identical
        numbers it drew before this term existed, and every past run stays
        reproducible from its seed.
        """
        cfg = self.config
        base_mode: Optional[str] = None
        base_level = 0.0
        if cfg.base_mode is not None and rng.random() < cfg.p_base:
            base_mode = cfg.base_mode
            lo, hi = cfg.base_level_range
            # The focus band only consumes its Bernoulli when configured, so a
            # single-band config draws the identical numbers it drew before.
            if (
                cfg.base_level_focus_range is not None
                and rng.random() < cfg.p_base_focus
            ):
                lo, hi = cfg.base_level_focus_range
            base_level = float(rng.uniform(lo, hi))
        if rng.random() >= cfg.p_degrade:
            return DegradationSpec(
                mode=None, level=0.0, base_mode=base_mode, base_level=base_level
            )
        mode = cfg.modes[int(rng.integers(0, len(cfg.modes)))]
        lo, hi = cfg.level_range
        level = float(rng.uniform(lo, hi))
        return DegradationSpec(
            mode=mode, level=level, base_mode=base_mode, base_level=base_level
        )

    def apply(self, img: np.ndarray, spec: DegradationSpec) -> np.ndarray:
        """Apply a spec to a frame; a clean spec returns an unchanged copy.

        Operating point first, stressor second — the physical order. The camera
        sees a mid-grey floor, and *then* glare or motion blur happens to that
        image; degrading a black road and lifting it afterwards would model the
        sensor as sitting in front of the world instead of behind it.
        """
        if spec.is_clean:
            return img.copy()
        out = img
        if spec.base_mode is not None:
            out = degrade(out, spec.base_mode, spec.base_level)
        if spec.mode is not None:
            out = degrade(out, spec.mode, spec.level)
        return out.copy() if out is img else out
