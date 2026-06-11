"""
scenario_runner — pure derivation of a single scenario *run configuration* from
its YAML dict and a repetition index: the env ``reset`` options (spawn
arc-length, deterministic heading error and lateral offset, plus the per-rep
randomisation jitter that makes the N runs independent), the commanded speed,
and the step horizon from the scenario timeout.

Kept ROS-free so the ``(scenario, rep) -> run-config`` mapping is unit-tested
without Gazebo; ``eval_policy`` applies the result to ``GazeboLaneEnv.reset``.
The randomisation jitter is seeded deterministically from ``(id, rep, base_seed)``
so a given rep is byte-for-byte reproducible across processes and hosts.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .scenario_perturbations import NONE as NO_PERTURBATION
from .scenario_perturbations import ScenarioPerturbation, resolve_perturbation


@dataclass
class RunConfig:
    scenario_id: str
    reset_options: Dict[str, float]
    fixed_speed: float
    max_steps: int
    pass_criterion_per_run: str
    # Runtime perturbation for this (scenario, rep): observation noise / actuation
    # latency / throttle pulse, level-resolved by rep. NONE for unperturbed runs.
    perturbation: ScenarioPerturbation = field(default=NO_PERTURBATION)
    # Stable per-rep env seed (drives the obs-noise stream so each rep is
    # independent yet reproducible). Same basis as the initial-condition jitter.
    env_seed: int = 0


def run_seed(scenario_id: str, rep: int, base_seed: int) -> int:
    """Stable 32-bit seed for a (scenario, rep) cell. Uses SHA-256 rather than
    Python's salted ``hash`` so the jitter is reproducible across interpreter
    runs (the reproducibility-metadata contract for campaign runs)."""
    digest = hashlib.sha256(f"{scenario_id}:{rep}:{base_seed}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _jitter(randomisation: Any, rng: "np.random.Generator") -> Tuple[float, float]:
    """(lateral_offset_m, heading_deg) jitter from a scenario's ``randomisation``
    block. Missing/``none`` randomisation yields no jitter (deterministic run)."""
    dlat = 0.0
    dpsi_deg = 0.0
    if isinstance(randomisation, dict):
        lat = randomisation.get("lateral_offset_uniform_m")
        if lat and len(lat) == 2:
            dlat = float(rng.uniform(float(lat[0]), float(lat[1])))
        head = randomisation.get("heading_uniform_deg")
        if head and len(head) == 2:
            dpsi_deg = float(rng.uniform(float(head[0]), float(head[1])))
    return dlat, dpsi_deg


def derive_run_config(
    scenario: Dict[str, Any],
    rep: int,
    *,
    control_dt: float = 0.10,
    base_seed: int = 0,
) -> RunConfig:
    """Derive the env-facing run configuration for repetition ``rep`` of
    ``scenario``. The seed pose (``pose.y`` lateral, ``pose.theta_deg`` heading)
    is read from ``initial_conditions``; the per-rep jitter is added on top."""
    sid = str(scenario["id"])
    track = scenario.get("track") or {}
    ic = scenario.get("initial_conditions") or {}
    pose = ic.get("pose") or {}

    start_s = float(track.get("start_s_m", 0.0))
    seed_lat = float(pose.get("y", 0.0))
    seed_theta_deg = float(pose.get("theta_deg", 0.0))

    rng = np.random.default_rng(run_seed(sid, rep, base_seed))
    dlat, dpsi_deg = _jitter(ic.get("randomisation"), rng)

    reset_options = {
        "start_s_m": start_s,
        "lateral_offset_m": seed_lat + dlat,
        "heading_error_rad": math.radians(seed_theta_deg + dpsi_deg),
    }

    speed = float(scenario.get("commanded_speed_mps", 0.2))
    timeout_s = float((scenario.get("termination") or {}).get("timeout_s", 0.0))
    max_steps = int(round(timeout_s / control_dt)) if timeout_s > 0 else 0

    perturbation = resolve_perturbation(
        scenario.get("perturbations"), rep, control_dt=control_dt
    )

    return RunConfig(
        scenario_id=sid,
        reset_options=reset_options,
        fixed_speed=speed,
        max_steps=max_steps,
        pass_criterion_per_run=str(scenario.get("pass_criterion_per_run", "")),
        perturbation=perturbation,
        env_seed=run_seed(sid, rep, base_seed),
    )
