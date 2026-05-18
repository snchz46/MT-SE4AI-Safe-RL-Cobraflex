"""
Tests for SR-010 Part 2 — inter-cycle oscillation detection.

Coverage:
    - history is empty until rules start firing
    - non-alternating corrections → rate stays 0, no trigger
    - fast alternation below t_osc_persist → rate exceeds but no emergency
    - fast alternation above t_osc_persist → ctx["oscillation_detected"]
      becomes True and C-05 fires the `triggered-oscillation` reason
    - rate computation is per-rule (C-01 alternating must not pollute
      C-02 history)
"""

from pathlib import Path

import pytest

from cage import SafetyCageNode
from cage.rules import State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


def _make_node():
    return SafetyCageNode(CAGE_YAML, mode="enforcement")


def _trigger_c01_with_offset(node, current_t, offset):
    """One step that drives C-01 into firing with a signed correction."""
    return node.step(
        state=State(lateral_offset=offset, speed=0.2),
        raw_action=(0.0, 0.4),
        ctx={"current_time": current_t},
    )


def test_no_history_when_no_rule_fires():
    node = _make_node()
    r = node.step(State(speed=0.2), raw_action=(0.0, 0.4), ctx={"current_time": 0.0})
    assert r["oscillation_rates_hz"]["C-01"] == 0.0
    assert r["oscillation_persistent"] is False


def test_non_alternating_corrections_no_oscillation():
    node = _make_node()
    # Repeatedly push to the same side — C-01 fires with same sign
    for i in range(20):
        r = _trigger_c01_with_offset(node, current_t=i * 0.05, offset=0.16)
    # Same-sign sequence → 0 alternations → rate 0
    assert r["oscillation_rates_hz"]["C-01"] == 0.0
    assert r["emergency"] is False


def test_fast_alternation_logs_without_emergency_below_persistence():
    node = _make_node()
    # Alternate every cycle for less than t_osc_persist (3 s)
    # Total span: 1.5 s (30 cycles at 50 ms)
    for i in range(30):
        offset = 0.16 if i % 2 == 0 else -0.16
        r = _trigger_c01_with_offset(node, current_t=i * 0.05, offset=offset)
    # Rate should clearly exceed f_osc_max (5 Hz); roughly ~20 Hz in steady state
    assert r["oscillation_rates_hz"]["C-01"] > 5.0
    # But persistence (3 s) not yet reached → no emergency yet
    assert r["emergency"] is False
    assert r["oscillation_persistent"] is False


def test_sustained_alternation_triggers_emergency():
    node = _make_node()
    fired_emergency_at = None
    # Run 4 seconds (80 cycles at 50 ms). Should trigger before then.
    for i in range(80):
        offset = 0.16 if i % 2 == 0 else -0.16
        r = _trigger_c01_with_offset(node, current_t=i * 0.05, offset=offset)
        if r["emergency"]:
            fired_emergency_at = i * 0.05
            break
    assert fired_emergency_at is not None, "Emergency was never triggered despite sustained oscillation"
    # Must occur AFTER violation has persisted t_osc_persist (3 s) but with
    # some leeway because the first cycle that exceeds f_osc_max is not at t=0.
    assert fired_emergency_at > 3.0
    # The fired reason must be the oscillation trigger
    c05_iv = next(iv for iv in r["interventions"] if iv["rule"] == "C-05")
    assert "oscillation" in c05_iv["reason"]


def test_alternation_in_one_rule_does_not_pollute_others():
    node = _make_node()
    for i in range(20):
        offset = 0.16 if i % 2 == 0 else -0.16
        r = _trigger_c01_with_offset(node, current_t=i * 0.05, offset=offset)
    assert r["oscillation_rates_hz"]["C-01"] > 0.0
    assert r["oscillation_rates_hz"]["C-02"] == 0.0
    assert r["oscillation_rates_hz"]["C-03"] == 0.0
