"""
cage_reset_proxy — the ROS-free decision half of ``cage_reset_proxy_node``:
when may an operator proxy publish ``/cage_reset``, and when must it refuse.

WHAT THIS IS NOT. It is **not** a change to C-05, and nothing here runs inside
the cage. `docs/17` §8.5 named three candidate answers to "C-05 has no
operational story on hardware" — a bounded auto-recovery on the perception
trigger, an operator reset path, or removing the cause upstream — and recorded
that the choice *needs a decision (D-NN), not a patch*. **D-74 is that
decision** and it picks the second candidate, implemented outside the artefact
under test. `cage.yaml` is untouched; ``require_explicit_reset`` still means what
every scored campaign scored.

Why not the first candidate, in one line: in simulation ``require_explicit_reset``
is nearly inert — a scenario ends and the cage is re-instantiated — so a bounded
recovery inside C-05 would be a change to the verified artefact whose entire
effect is on hardware, validated by nothing.

WHAT IT COSTS. It automates what the operator did by hand five times on
26.08.2026 (§8.5: five `/cage_reset` publications, each with perception already
healthy, no C-01…C-04 active and ``v = 0``) — those same three conditions are
the guards below, plus a rate limit and a hard budget. **A run with this node
enabled is a diagnostic run and cannot be a scored one**, because the vehicle's
stopping behaviour is then partly this node's, not the cage's. The node
therefore defaults to disabled and every decision it takes is written to the
run's evidence directory.

The 26.08 `noloopclosure` lap is the case it is built for: 18.05 m covered,
zero safety rules fired, ended by one 400 ms perception pulse with the car
27 mm from the lane centre and 2.11 m short of the start.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Tuple

#: A reset is withheld while any of these is active. C-05 is excluded because
#: it IS the latched state being cleared, and C-06 because the rate limiter is
#: active on most cycles by design (3.4 % of moving cycles on the 26.08 lap,
#: against the 3.0 % that chose the checkpoint in simulation).
BLOCKING_RULES: Tuple[str, ...] = ("C-01", "C-02", "C-03", "C-04")


@dataclass(frozen=True)
class ResetDecision:
    """Whether to publish ``/cage_reset`` now, and the reason either way."""

    issue: bool
    reason: str


@dataclass
class ResetPolicy:
    """Guarded operator-proxy reset policy.

    All four guards must hold, continuously, for ``min_healthy_seconds`` before
    a reset is issued:

    * the emergency is latched (otherwise there is nothing to clear);
    * ``/perception_invalid`` is false — the trigger has actually cleared;
    * no C-01…C-04 is active — the cage is not asking for something else;
    * the car is stopped.

    ``min_healthy_seconds`` is what stops this becoming the oscillation at the
    trigger boundary that C-05's asymmetric exit exists to prevent: the
    STPA-informed argument in `cage.yaml` §c05_emergency is about re-arming
    while the condition still flickers, and a healthy-hold requirement is the
    same argument expressed in time.
    """

    min_healthy_seconds: float = 1.0
    min_interval_seconds: float = 3.0
    max_resets: int = 6
    max_speed_mps: float = 0.02
    blocking_rules: Sequence[str] = BLOCKING_RULES

    _healthy_since: Optional[float] = field(default=None, init=False)
    _last_reset: Optional[float] = field(default=None, init=False)
    _count: int = field(default=0, init=False)

    @property
    def resets_issued(self) -> int:
        return self._count

    @property
    def budget_exhausted(self) -> bool:
        return self._count >= self.max_resets

    def update(
        self,
        now: float,
        *,
        emergency: bool,
        perception_invalid: bool,
        active_rules: Iterable[str] = (),
        speed_mps: float = 0.0,
    ) -> ResetDecision:
        """Advance the policy by one observation and say what to do.

        Call this on every cage cycle, not only while latched: the healthy-hold
        timer has to be running *before* the decision point, or the first
        cycle after the trigger clears would look like a full hold.
        """
        blocking = sorted(set(active_rules) & set(self.blocking_rules))
        healthy = (
            not perception_invalid
            and not blocking
            and abs(speed_mps) <= self.max_speed_mps
        )
        if healthy:
            if self._healthy_since is None:
                self._healthy_since = now
        else:
            self._healthy_since = None

        if not emergency:
            return ResetDecision(False, "no emergency latched")
        if perception_invalid:
            return ResetDecision(False, "perception still invalid")
        if blocking:
            return ResetDecision(False, "cage rules active: " + ",".join(blocking))
        if abs(speed_mps) > self.max_speed_mps:
            return ResetDecision(
                False, f"still moving ({speed_mps:.3f} m/s)"
            )
        held = now - (self._healthy_since if self._healthy_since is not None else now)
        if held < self.min_healthy_seconds:
            return ResetDecision(
                False, f"healthy for {held:.2f} s of {self.min_healthy_seconds:.2f}"
            )
        if self.budget_exhausted:
            return ResetDecision(
                False, f"budget spent ({self._count}/{self.max_resets} resets)"
            )
        if (
            self._last_reset is not None
            and now - self._last_reset < self.min_interval_seconds
        ):
            return ResetDecision(
                False,
                f"rate limited ({now - self._last_reset:.2f} s since last reset)",
            )

        self._count += 1
        self._last_reset = now
        self._healthy_since = None
        return ResetDecision(
            True,
            f"healthy for {held:.2f} s, reset {self._count}/{self.max_resets}",
        )
