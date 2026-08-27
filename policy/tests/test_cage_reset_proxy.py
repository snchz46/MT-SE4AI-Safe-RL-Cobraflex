"""Host-side tests for the guarded operator-proxy reset policy.

This node publishes into a chain that drives a real car, and what it publishes
clears an emergency latch. Every guard below is one the operator applied by
hand on 26.08.2026; a regression here is a car that un-latches while a cage
rule is still asking for something.
"""
import pytest

from cobraflex_rl.cage_reset_proxy import ResetPolicy


def _tick(policy, now, **kw):
    kw.setdefault("emergency", True)
    kw.setdefault("perception_invalid", False)
    return policy.update(now, **kw)


def test_never_issues_without_a_latched_emergency():
    p = ResetPolicy(min_healthy_seconds=0.5)
    for t in (0.0, 1.0, 2.0, 3.0):
        d = _tick(p, t, emergency=False)
        assert not d.issue and d.reason == "no emergency latched"
    assert p.resets_issued == 0


def test_withholds_while_the_trigger_is_still_active():
    p = ResetPolicy(min_healthy_seconds=0.5)
    for t in (0.0, 0.5, 1.0):
        d = _tick(p, t, perception_invalid=True)
        assert not d.issue and "perception still invalid" in d.reason


def test_issues_only_after_the_healthy_hold_elapses():
    p = ResetPolicy(min_healthy_seconds=1.0)
    assert not _tick(p, 10.0).issue          # hold starts here
    assert not _tick(p, 10.5).issue
    d = _tick(p, 11.0)
    assert d.issue and p.resets_issued == 1


def test_a_flicker_restarts_the_hold():
    """C-05's asymmetric exit exists to stop oscillation at the trigger
    boundary; the healthy-hold is that argument expressed in time."""
    p = ResetPolicy(min_healthy_seconds=1.0)
    _tick(p, 0.0)
    _tick(p, 0.9, perception_invalid=True)   # one bad cycle
    assert not _tick(p, 1.0).issue
    assert not _tick(p, 1.5).issue
    assert _tick(p, 2.0).issue


def test_blocking_rules_withhold_but_c06_does_not():
    p = ResetPolicy(min_healthy_seconds=0.5)
    d = _tick(p, 0.0, active_rules=["C-05", "C-02"])
    assert not d.issue and "C-02" in d.reason
    # C-06 is active on ~3.4 % of moving cycles by design — blocking on it
    # would mean never resetting.
    _tick(p, 1.0, active_rules=["C-05", "C-06"])
    assert _tick(p, 1.6, active_rules=["C-05", "C-06"]).issue


def test_a_moving_car_is_never_reset():
    p = ResetPolicy(min_healthy_seconds=0.5, max_speed_mps=0.02)
    d = _tick(p, 0.0, speed_mps=0.18)
    assert not d.issue and "still moving" in d.reason
    assert not _tick(p, 1.0, speed_mps=0.18).issue
    _tick(p, 2.0, speed_mps=0.0)
    assert _tick(p, 2.6, speed_mps=0.0).issue


def test_rate_limit_between_resets():
    p = ResetPolicy(min_healthy_seconds=0.2, min_interval_seconds=3.0)
    _tick(p, 0.0)
    assert _tick(p, 0.3).issue
    _tick(p, 1.0)
    d = _tick(p, 1.5)
    assert not d.issue and "rate limited" in d.reason
    _tick(p, 3.2)
    assert _tick(p, 3.5).issue


def test_budget_is_hard():
    p = ResetPolicy(min_healthy_seconds=0.0, min_interval_seconds=0.0, max_resets=2)
    issued = sum(1 for t in range(10) if _tick(p, float(t)).issue)
    assert issued == 2
    assert p.budget_exhausted
    assert "budget spent" in _tick(p, 20.0).reason


def test_the_hold_timer_runs_before_the_decision_point():
    """update() must be called every cycle, including while healthy and
    un-latched, or the first post-trigger cycle looks like a full hold."""
    p = ResetPolicy(min_healthy_seconds=1.0)
    for t in (0.0, 0.5, 1.0, 1.5):
        _tick(p, t, emergency=False)         # healthy, nothing latched yet
    d = _tick(p, 1.6)                        # latch observed here
    assert d.issue, d.reason
