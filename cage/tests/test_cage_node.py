"""
Integration tests for SafetyCageNode — composition of all six rules.

Coverage:
    - pass-through when no rule fires
    - C-04 reduces throttle when speed exceeds ceiling
    - C-01 corrects steering when lateral offset exceeds bound
    - C-06 clips action delta across consecutive cycles
    - C-05 emergency overrides every upstream correction
    - monitoring mode logs but does not modify safe_action
    - prev_action tracks the emitted action across cycles
    - reset_emergency clears once trigger has also cleared
"""

from pathlib import Path

import pytest

from cage import SafetyCageNode
from cage.rules import State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture
def node():
    return SafetyCageNode(CAGE_YAML, mode="enforcement")


@pytest.fixture
def node_monitoring():
    return SafetyCageNode(CAGE_YAML, mode="monitoring")


def test_pass_through_when_state_is_safe(node):
    state = State(speed=0.2)
    result = node.step(state, raw_action=(0.0, 0.4))
    assert result["safe_action"] == (0.0, 0.4)
    assert result["interventions"] == []
    assert result["emergency"] is False


def test_c04_reduces_throttle_above_ceiling(node):
    # Prime prev_action with the raw to keep C-06 from firing on first cycle
    node.step(State(speed=0.4), raw_action=(0.0, 0.5))
    state = State(speed=0.6)  # above v_max_straight=0.5
    result = node.step(state, raw_action=(0.0, 0.5))
    _, throttle = result["safe_action"]
    assert throttle < 0.5
    rules_fired = [iv["rule"] for iv in result["interventions"]]
    assert "C-04" in rules_fired


def test_c01_corrects_steering_above_lane_bound(node):
    state = State(lateral_offset=0.16, speed=0.3)
    result = node.step(state, raw_action=(0.0, 0.4))
    steering, _ = result["safe_action"]
    assert steering < 0.0  # correction back toward centre
    rules_fired = [iv["rule"] for iv in result["interventions"]]
    assert "C-01" in rules_fired


def test_c06_clips_large_action_delta(node):
    # First cycle establishes prev_action = (0,0)
    node.step(State(), raw_action=(0.0, 0.0))
    # Second cycle commands a huge jump — C-06 must clip the delta
    result = node.step(State(), raw_action=(1.0, 1.0))
    steering, throttle = result["safe_action"]
    assert steering <= 0.15 + 1e-9  # delta_max_steering
    assert throttle <= 0.10 + 1e-9  # delta_max_throttle
    rules_fired = [iv["rule"] for iv in result["interventions"]]
    assert "C-06" in rules_fired


def test_c05_emergency_overrides_other_corrections(node):
    # Construct a state that triggers C-05 by invalid flag AND also exceeds C-01
    state = State(lateral_offset=0.5, heading_error=1.0, speed=0.6, state_valid=False)
    result = node.step(state, raw_action=(0.0, 0.5))
    assert result["emergency"] is True
    _, throttle = result["safe_action"]
    assert throttle < 0.0  # emergency brake


def test_monitoring_mode_passes_through(node_monitoring):
    state = State(lateral_offset=0.5, speed=0.8)
    raw = (0.0, 0.9)
    result = node_monitoring.step(state, raw_action=raw)
    assert result["safe_action"] == raw
    # Interventions still recorded (informational)
    assert len(result["interventions"]) > 0
    assert result["mode"] == "monitoring"


def test_prev_action_tracks_emitted_action(node):
    node.step(State(), raw_action=(0.1, 0.2))
    assert node.prev_action == (0.1, 0.2)
    node.step(State(), raw_action=(0.05, 0.15))
    assert node.prev_action == (0.05, 0.15)


def test_prev_action_in_monitoring_tracks_raw(node_monitoring):
    state = State(lateral_offset=0.5)
    raw = (0.7, 0.4)
    node_monitoring.step(state, raw_action=raw)
    assert node_monitoring.prev_action == raw  # monitoring → raw stored


def test_reset_emergency_clears_when_trigger_also_cleared(node):
    # Trigger
    node.step(State(state_valid=False), raw_action=(0.0, 0.5))
    # Reset alone with trigger still present → still active
    node.reset_emergency()
    r1 = node.step(State(state_valid=False), raw_action=(0.0, 0.5))
    assert r1["emergency"] is True
    # Reset + cleared trigger → exits emergency
    node.reset_emergency()
    r2 = node.step(State(state_valid=True), raw_action=(0.0, 0.5))
    assert r2["emergency"] is False


def test_cage_version_propagates_to_result(node):
    result = node.step(State(), raw_action=(0.0, 0.0))
    assert result["cage_version"] == "0.4.0"
