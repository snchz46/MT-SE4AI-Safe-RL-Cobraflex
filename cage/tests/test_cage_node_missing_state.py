"""
Integration tests for SafetyCageNode's missing-state handling
(C-05 Trigger 5). The cage_node counts consecutive step() calls that
arrived without a fresh state observation; once the counter exceeds
`cage.n_missing_max_cycles`, the chain receives `ctx["missing_state"]=True`
and C-05 fires.
"""

from pathlib import Path

import pytest

from cage import SafetyCageNode
from cage.rules import State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture
def node():
    return SafetyCageNode(CAGE_YAML, mode="enforcement")


def test_missing_counter_starts_at_zero_after_first_state(node):
    node.step(State(), raw_action=(0.0, 0.0))
    assert node.cycles_since_last_state == 0


def test_missing_counter_increments_on_none_state(node):
    node.step(State(), raw_action=(0.0, 0.0))
    node.step(state=None, raw_action=(0.0, 0.0))
    assert node.cycles_since_last_state == 1
    node.step(state=None, raw_action=(0.0, 0.0))
    assert node.cycles_since_last_state == 2


def test_missing_counter_resets_when_state_returns(node):
    node.step(State(), raw_action=(0.0, 0.0))
    node.step(state=None, raw_action=(0.0, 0.0))
    node.step(state=None, raw_action=(0.0, 0.0))
    node.step(State(), raw_action=(0.0, 0.0))
    assert node.cycles_since_last_state == 0


def test_missing_state_eventually_triggers_emergency(node):
    n_max = node.n_missing_max_cycles
    node.step(State(), raw_action=(0.0, 0.0))
    # Run n_max+1 cycles without state
    for _ in range(n_max):
        r = node.step(state=None, raw_action=(0.0, 0.0))
        # Up to and including n_max → counter ≤ n_max, no missing trigger yet
        assert r["emergency"] is False
    # One more → counter exceeds n_max, missing trigger fires
    r = node.step(state=None, raw_action=(0.0, 0.0))
    assert r["emergency"] is True
    assert any(
        "missing-state" in iv["reason"]
        for iv in r["interventions"]
        if iv["rule"] == "C-05"
    )


def test_no_state_ever_received_returns_safe_stop(node):
    r = node.step(state=None, raw_action=(0.5, 0.8))
    assert r["emergency"] is True
    assert r["safe_action"] == (0.0, -0.5)
    rule_ids = [iv["rule"] for iv in r["interventions"]]
    assert "CAGE-NODE" in rule_ids


def test_state_none_after_valid_state_uses_last_known(node):
    valid = State(lateral_offset=0.05, speed=0.3)
    node.step(valid, raw_action=(0.0, 0.5))
    r = node.step(state=None, raw_action=(0.0, 0.5))
    # The chain runs against the cached state (no emergency for one missing cycle)
    assert r["emergency"] is False
    assert r["cycles_since_last_state"] == 1
