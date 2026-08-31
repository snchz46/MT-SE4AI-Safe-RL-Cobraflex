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


# ------------------------------------------------- the lap04 deadlock (31.08.2026)
# `lap04_20260831T102651Z` stopped with the car OUTSIDE the lane. C-01 was then
# active on every subsequent cycle, so the C-01..C-04 guard could never clear and
# the proxy issued nothing for 2287 cycles (~250 s) with 24 of its 30-reset budget
# unused. The guard is correct as a default and stays the default; these tests pin
# BOTH halves — that the deadlock is real, and that narrowing the set escapes it.


def test_a_car_stopped_outside_the_lane_deadlocks_the_default_guard():
    """The measured lap04 failure: C-01 latched active on a stationary car."""
    p = ResetPolicy(min_healthy_seconds=1.0, min_interval_seconds=0.0, max_resets=30)
    for t in range(0, 300):                       # 30 s at 10 Hz, car stopped
        d = _tick(p, t * 0.1, active_rules=("C-01",), speed_mps=0.0)
        assert not d.issue
        assert "cage rules active: C-01" in d.reason
    assert p.resets_issued == 0
    assert not p.budget_exhausted                 # budget was never the constraint


def test_narrowing_the_blocking_set_turns_the_deadlock_into_a_livelock():
    """The obvious escape does NOT work, and this pins why.

    Dropping C-01/C-02 (the "vacuous at v=0" argument) does let a reset through —
    and then lets one through every `min_interval_seconds` for as long as the
    budget lasts, because the car is still off-lane so the cage re-latches at
    once. Replaying lap04's own bag through both policies (14738 real messages)
    measured 6 resets for the default, budget spare, against 30 for the narrowed
    set with the budget gone by t+178 s of a 555 s run: thirty release-and-
    relatch lurches instead of one stuck car. Worse, not better.
    """
    p = ResetPolicy(min_healthy_seconds=1.0, min_interval_seconds=3.0,
                    max_resets=30, blocking_rules=("C-03", "C-04"))
    for i in range(1200):                      # 120 s at 10 Hz, pose never changes
        _tick(p, i * 0.1, active_rules=("C-01",), speed_mps=0.0)
    assert p.resets_issued >= 25, p.resets_issued
    assert p.budget_exhausted

    # ...whereas the default simply withholds, forever. One stuck car.
    q = ResetPolicy(min_healthy_seconds=1.0, min_interval_seconds=3.0, max_resets=30)
    for i in range(1200):
        _tick(q, i * 0.1, active_rules=("C-01",), speed_mps=0.0)
    assert q.resets_issued == 0


def test_narrowing_does_not_disarm_the_other_guards():
    """Escaping the deadlock must not become 'reset whenever latched'."""
    p = ResetPolicy(min_healthy_seconds=1.0, min_interval_seconds=0.0,
                    blocking_rules=("C-03", "C-04"))
    # still moving → withheld even with no blocking rule active
    assert not _tick(p, 0.0, speed_mps=0.5).issue
    assert "still moving" in _tick(p, 0.5, speed_mps=0.5).reason
    # a rule that IS in the narrowed set still blocks
    assert "cage rules active: C-03" in _tick(
        p, 1.0, active_rules=("C-03",), speed_mps=0.0).reason
    # perception still invalid still blocks
    assert "perception still invalid" in _tick(
        p, 1.5, perception_invalid=True, speed_mps=0.0).reason


def test_the_default_blocking_set_is_unchanged():
    """A regression here silently changes what `auto` is allowed to release."""
    from cobraflex_rl.cage_reset_proxy import BLOCKING_RULES
    assert BLOCKING_RULES == ("C-01", "C-02", "C-03", "C-04")
    assert ResetPolicy().blocking_rules == BLOCKING_RULES
