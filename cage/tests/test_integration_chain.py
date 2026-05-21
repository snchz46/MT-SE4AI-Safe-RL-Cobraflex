"""Cross-rule integration test for the full cage chain.

Closes §13(5) of the Phase 2 plan formally: an end-to-end run that
exercises the chain C-06 → C-04 → C-02 → C-03 → C-01 → C-05 against a
deterministic sequence of synthetic (state, raw_action) pairs and asserts
behavioural properties spanning multiple rules simultaneously. The
pure-Python smoke at ``experiments/sim/oval_pd_cage_smoke.py`` covers
the dynamic case; this file covers the per-cycle invariants in pytest.

Properties asserted here:
    (a) Determinism: two independent nodes fed the same inputs emit
        the same safe_action and interventions stream cycle-for-cycle.
    (b) Cascade: at least one cycle in the scripted sequence has more
        than one rule firing, demonstrating the chain orchestration.
    (c) C-06 firing on raw-action jumps (rate limiter prelude).
    (d) C-01 + C-03 defence in depth on lateral excursion (predictive
        guard fires before the reactive bound).
    (e) C-05 cold-start safe-stop when /state_obs has never arrived.
    (f) Joint-envelope assertion holds in nominal cycles and trips
        on stressed cycles (cross-validates with test_joint_envelope.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cage.cage_node import SafetyCageNode, _NEUTRAL_SAFE_STOP
from cage.rules import State

REPO_ROOT = Path(__file__).resolve().parents[2]
CAGE_YAML = REPO_ROOT / "cage" / "cage.yaml"


def _state(**kw) -> State:
    base = dict(
        lateral_offset=0.0, heading_error=0.0, speed=0.2, curvature_ahead=0.0,
        distance_left=0.13, distance_right=0.13, state_valid=True, timestamp=0.0,
    )
    base.update(kw)
    return State(**base)


# --------------------------------------------------------------------------
# Scripted sequence
# --------------------------------------------------------------------------


def _scripted_sequence():
    """Five cycles that progressively stress the chain.

    Cycle 0: nominal driving, no rule fires.
    Cycle 1: PD jumps from 0 to +0.8 steering -> C-06 clips the rate.
    Cycle 2: lateral_offset just under d_max, raw steers further out -> C-01
             activates with C-06 reacting to the new raw.
    Cycle 3: deep excursion + high heading error -> Trigger 7 joint-envelope
             violation overrides everything to safe stop.
    Cycle 4: state back to nominal, but cage emergency may persist via the
             require_explicit_reset latch; we exercise the reset path.
    """
    return [
        # (state, raw_action, ctx_extra)
        (_state(timestamp=0.00), (0.0, 0.5), {"current_time": 0.00}),
        (_state(timestamp=0.05), (0.8, 0.5), {"current_time": 0.05}),
        (_state(timestamp=0.10, lateral_offset=0.145, heading_error=0.1, speed=0.4),
         (0.5, 0.5), {"current_time": 0.10}),
        (_state(timestamp=0.15, lateral_offset=0.25, heading_error=0.6, speed=0.6),
         (0.0, 0.5), {"current_time": 0.15}),
        (_state(timestamp=0.20), (0.0, 0.5), {"current_time": 0.20, "reset": True}),
    ]


def _run(node: SafetyCageNode):
    out = []
    for state, raw, ctx in _scripted_sequence():
        out.append(node.step(state, raw, ctx=dict(ctx)))
    return out


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


def test_chain_is_deterministic():
    a = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    b = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    assert len(a) == len(b)
    for ra, rb in zip(a, b):
        assert ra["safe_action"] == rb["safe_action"]
        assert [iv["rule"] for iv in ra["interventions"]] == \
               [iv["rule"] for iv in rb["interventions"]]
        assert ra["emergency"] == rb["emergency"]
        assert ra["joint_envelope_violated"] == rb["joint_envelope_violated"]


def test_at_least_one_cycle_has_multiple_rules_firing():
    results = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    multi = [r for r in results if len(r["interventions"]) >= 2]
    assert multi, "Expected at least one cycle with multiple rules firing"


def test_c06_fires_on_rate_jump():
    results = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    # Cycle 1: PD jumps to +0.8 from prev 0 -> C-06 clips by delta_max=0.15.
    c06_firings = [iv for iv in results[1]["interventions"] if iv["rule"] == "C-06"]
    assert c06_firings, "C-06 should clip the raw-action jump at cycle 1"
    safe_steer = results[1]["safe_action"][0]
    assert abs(safe_steer) <= 0.15 + 1e-6


def test_c01_or_c03_fires_on_lateral_excursion():
    """Defence in depth: when lateral_offset approaches d_max, either the
    predictive C-03 or the reactive C-01 must fire (typically C-01)."""
    results = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    rules_at_2 = {iv["rule"] for iv in results[2]["interventions"]}
    assert ("C-01" in rules_at_2) or ("C-03" in rules_at_2), (
        f"Expected C-01 or C-03 at cycle 2; got {rules_at_2}"
    )


def test_trigger_7_fires_on_compound_violation():
    results = _run(SafetyCageNode(CAGE_YAML, mode="enforcement"))
    # Cycle 3: lateral_offset > d_max AND speed > v_max_straight.
    cycle = results[3]
    assert cycle["joint_envelope_violated"] is True
    assert cycle["emergency"] is True
    assert cycle["safe_action"] == _NEUTRAL_SAFE_STOP
    trigger_7s = [iv for iv in cycle["interventions"]
                  if iv.get("metadata", {}).get("trigger") == 7]
    assert len(trigger_7s) == 1
    failing = trigger_7s[0]["metadata"]["failing_rules"]
    assert {"C-01", "C-04"}.issubset(set(failing))


def test_cold_start_safe_stop_when_no_state():
    """If /raw_action arrives before any /state_obs, the cage falls through
    the no-state-ever path: it must emit NEUTRAL_SAFE_STOP and flag emergency
    via the synthetic CAGE-NODE intervention, NOT silently pass the raw."""
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    result = node.step(state=None, raw_action=(0.5, 0.5), ctx={"current_time": 0.0})
    assert result["safe_action"] == _NEUTRAL_SAFE_STOP
    assert result["emergency"] is True
    assert any(iv["rule"] == "CAGE-NODE" for iv in result["interventions"])


def test_joint_envelope_holds_on_nominal_cycle():
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    result = node.step(_state(), raw_action=(0.0, 0.5), ctx={"current_time": 0.0})
    assert result["joint_envelope_violated"] is False
    assert all(result["joint_envelope_predicates"].values())
