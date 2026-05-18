"""
End-to-end pipeline integration test — PD baseline → SafetyCageNode → CageLogger.

This is the closest pure-Python analogue to the Milestone M1 demo. It
runs a synthetic 200-cycle (10 s) trajectory in which the simulated
lateral offset slowly grows past the cage's d_max threshold, verifying
that:

    - the PD produces sensible raw actions
    - the cage intervenes when offset exceeds the lane bound
    - the logger captures the full per-cycle stream
    - the resulting CSV is well-formed and matches the cycle count

The "vehicle" here is a kinematic stub (offset advances linearly with
steering bias) — it does not represent the Gazebo dynamics. The point
is to exercise the wiring, not the physics. The full Gazebo loop is the
job of the ROS2 wrapper and is out of scope for pytest.
"""

import csv
from pathlib import Path

import pytest

from cage import SafetyCageNode
from cage.logger import CageLogger
from cage.rules import State
from policy.baseline_pd import BaselinePD

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"
PD_YAML = Path(__file__).resolve().parent.parent.parent / "policy" / "baseline_pd.yaml"


def _kinematic_step(state: State, action_steering: float, dt: float) -> State:
    """Toy first-order kinematics: lateral_offset drifts with a fixed
    rate while steering nudges it linearly. Speed and curvature held
    constant. Sufficient to drive the cage rules into firing without
    pulling in a real bicycle model."""
    drift_rate = 0.02  # m/s, slow leftward drift (simulates banked surface)
    steering_effect = -0.5 * action_steering  # negative steering pushes right
    new_offset = state.lateral_offset + (drift_rate + steering_effect) * dt
    return State(
        lateral_offset=new_offset,
        heading_error=state.heading_error,
        speed=state.speed,
        curvature_ahead=state.curvature_ahead,
        state_valid=True,
        timestamp=state.timestamp + dt,
    )


def test_pd_cage_logger_pipeline(tmp_path):
    cage = SafetyCageNode(CAGE_YAML, mode="enforcement")
    pd = BaselinePD.from_yaml(PD_YAML)
    log_dir = tmp_path / "pipeline_run"

    state = State(speed=0.3, curvature_ahead=0.0, state_valid=True)
    dt = 0.05  # 20 Hz
    n_cycles = 200  # 10 s

    cage_intervened = False
    with CageLogger(log_dir, run_id="pipeline_test", metadata={"scenario": "drift_oval"}) as log:
        for i in range(n_cycles):
            current_t = i * dt
            raw_action = pd.step(state, current_t=current_t)
            result = cage.step(state=state, raw_action=raw_action, ctx={"current_time": current_t})
            log.add_cycle(result)
            if result["interventions"]:
                cage_intervened = True
            # Advance kinematic stub using the action actually emitted
            state = _kinematic_step(state, result["safe_action"][0], dt)

    # The drift should grow enough that at least one cage rule fires
    assert cage_intervened, "Cage never intervened across 10 s of drifting"

    # Logger CSV well-formed
    rows = list(csv.DictReader((log_dir / "cage_status.csv").open()))
    assert len(rows) == n_cycles
    assert rows[0]["cage_version"] == "0.5.0"
    assert all(r["mode"] == "enforcement" for r in rows)

    # At least one row records a non-empty rules_fired
    fired_rows = [r for r in rows if r["rules_fired"]]
    assert len(fired_rows) > 0

    # Metadata captures the cycle count
    import json
    meta = json.loads((log_dir / "metadata.json").read_text())
    assert meta["cycles_logged"] == n_cycles
    assert meta["scenario"] == "drift_oval"


def test_pipeline_monitoring_mode_does_not_modify_action(tmp_path):
    """In monitoring mode, the action sent to the kinematic step is the
    raw PD action; the cage logs interventions but does not alter the
    command stream."""
    cage = SafetyCageNode(CAGE_YAML, mode="monitoring")
    pd = BaselinePD.from_yaml(PD_YAML)
    log_dir = tmp_path / "monitoring_run"

    state = State(lateral_offset=0.20, speed=0.3, state_valid=True)
    raw_action = pd.step(state, current_t=0.0)
    with CageLogger(log_dir) as log:
        result = cage.step(state=state, raw_action=raw_action, ctx={"current_time": 0.0})
        log.add_cycle(result)

    assert result["mode"] == "monitoring"
    assert result["safe_action"] == raw_action  # raw passes through
    # But interventions were still recorded (cage would have fired in enforcement)
    assert len(result["interventions"]) > 0
