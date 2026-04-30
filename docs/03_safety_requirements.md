# Safety Requirements Specification

**Status:** Living document — Phase 1 deliverable
**Last update:** [date]
**Approved at Gate:** G1 (pending)

## Purpose

This document specifies the Safety Requirements (SRs) derived from the Hazard Register. Each SR satisfies four criteria:

1. **Falsifiable** — expressed as a condition that can be confirmed or denied through measurement.
2. **Operative** — implementable by a concrete mechanism (cage rule, training constraint, scenario test).
3. **Traceable** — references at least one hazard, and is referenced by at least one cage rule and at least one scenario.
4. **Atomic** — captures a single property rather than several.

A companion CSV (`docs/data/safety_requirements.csv`) is generated automatically from this Markdown.

## Pattern catalogue

The SRs use a small set of recurring patterns:

- **Direct threshold** — a measurable variable shall not exceed (or shall not fall below) a fixed value at any time.
- **Predictive threshold** — a forward-looking estimate shall remain within bounds.
- **Bounded derivative** — the change of a variable between two time steps shall not exceed a bound.
- **Availability** — a service or signal shall be available within timing constraints.
- **Emergency mode** — under specified conditions, a specified mode shall be entered.
- **Operational envelope** — the joint state of variables shall remain within a defined region.

---

## SR-001 — Lane departure prevention (direct)

**Statement.** Under the operational ODD, the absolute lateral offset of the vehicle relative to the lane centreline shall not exceed `d_max` at any time during autonomous operation.

**Pattern.** Direct threshold.

**Parameters.**
- `d_max = 0.16 m` (lane width 0.40 m, safety margin 0.04 m absorbing the joint uncertainty of LiDAR-observed lateral noise around 0.01 m and a control latency of 50 ms).

**References hazard.** H-01.

**Implemented by.** C-01 (lane boundary hard limit).

**Verified by scenarios.** SC-NOM-01, SC-NOM-02, SC-EDGE-02.

**Verifying metric.** M-S1 (max lateral offset).

**Satisfaction criterion.** Across all runs of the verifying scenarios in enforcement mode, the maximum observed value of M-S1 shall not exceed `d_max` in any single time step. Verdict aggregated across all runs.

---

## SR-002 — Heading stability

**Statement.** Under the operational ODD, the absolute heading error of the vehicle relative to the lane direction shall not exceed `θ_max` at any time during autonomous operation.

**Pattern.** Direct threshold.

**Parameters.**
- `θ_max = 25 degrees (0.44 rad)` — chosen as the angle beyond which the kinematic model of the vehicle predicts non-recoverable lane departure within the response time of the cage.

**References hazard.** H-02.

**Implemented by.** C-02 (heading error limit).

**Verified by scenarios.** SC-EDGE-01, SC-EDGE-04.

**Verifying metric.** M-P4 (heading error max).

**Satisfaction criterion.** Across all runs of the verifying scenarios in enforcement mode, the maximum observed value of M-P4 shall not exceed `θ_max`.

---

## SR-003 — Predictive lane departure prevention (TTLC)

**Statement.** At every time step during autonomous operation, the estimated time-to-lane-crossing (TTLC), computed from the current state under the assumption of zero corrective action, shall remain greater than or equal to `t_min`. The 5th percentile of TTLC over all nominal runs shall remain at least 0.5 s.

**Pattern.** Predictive threshold.

**Parameters.**
- `t_min = 1.0 s` — sum of approximately 0.3 s margin for the cage to apply a complete correction and approximately 0.7 s margin for the policy to recover.
- 5th percentile floor: 0.5 s.

**References hazard.** H-01 (primarily), H-02 (partially).

**Implemented by.** C-03 (predictive TTLC).

**Verified by scenarios.** SC-NOM-02, SC-EDGE-01.

**Verifying metric.** M-S4 (TTLC 5th percentile).

**Satisfaction criterion.** TTLC ≥ `t_min` in at least 95% of all time steps across the verifying scenarios; the 5th percentile of TTLC shall be ≥ 0.5 s.

---

## SR-004 — Speed compliance

**Statement.** The forward speed of the vehicle shall not exceed `v_max(κ)`, a curvature-dependent ceiling derived from the kinematic envelope of the platform.

**Pattern.** Direct threshold (parameterised by curvature).

**Parameters.**
- `v_max_straight = 0.5 m/s` (on straight sections, |κ| < 0.05 rad/m).
- `v_max_curve = 0.25 m/s` (on curved sections, |κ| ≥ 0.05 rad/m).
- Smooth interpolation: `v_max(κ) = max(v_max_curve, v_max_straight − k_κ · |κ|)` with `k_κ = 0.3 m/s per unit curvature`.

**References hazard.** H-03.

**Implemented by.** C-04 (speed ceiling).

**Verified by scenarios.** SC-NOM-02, SC-EDGE-03.

**Verifying metric.** M-P3 (speed compliance) and the underlying speed log.

**Satisfaction criterion.** Across all runs of the verifying scenarios in enforcement mode, no time step records a forward speed exceeding `v_max(κ)` for the locally observed curvature.

---

## SR-005 — Emergency mode for compound state

**Statement.** If the system simultaneously observes a heading error magnitude greater than `θ_warning` and a lateral offset magnitude greater than `d_warning` for more than `Δt_max` consecutive seconds, the system shall transition into an emergency mode characterised by:
- a deceleration of at least `a_min` until full stop,
- the steering command frozen at its value at the instant of transition,
- an emergency signal published on the dedicated topic.

**Pattern.** Emergency mode (composite trigger, deterministic response).

**Parameters.**
- `θ_warning = 20 degrees`.
- `d_warning = 0.12 m`.
- `Δt_max = 0.2 s`.
- `a_min = 0.3 m/s²`.

**References hazard.** H-04 (primarily), H-07 (partially).

**Implemented by.** C-05 (emergency mode).

**Verified by scenarios.** SC-EDGE-04.

**Verifying metric.** M-S3 (emergency stop rate and behaviour).

**Satisfaction criterion.** In every run where the trigger condition is induced, the emergency mode activates within one control cycle of the trigger condition being met for `Δt_max` seconds; once active, the deceleration is at least `a_min` and the steering remains frozen.

---

## SR-006 — Actuator smoothness

**Statement.** The change in the steering and throttle commands between two consecutive control steps shall not exceed `δ_max` in absolute value.

**Pattern.** Bounded derivative.

**Parameters.**
- `δ_max_steering = 0.15` (normalised units per 50 ms cycle).
- `δ_max_throttle = 0.10` (normalised units per 50 ms cycle).

**References hazard.** H-05.

**Implemented by.** C-06 (actuator rate limiter).

**Verified by scenarios.** All scenarios (the rate limiter is always active).

**Verifying metric.** M-I5 (action correction magnitude).

**Satisfaction criterion.** Across all runs in enforcement mode, no consecutive pair of safe-action commands exceeds `δ_max` in absolute change for either steering or throttle.

---

## SR-007 — State validity and freshness

**Statement.** The cage shall trigger emergency mode if any of the following holds:
- the most recent state observation has a timestamp older than `staleness_max`;
- any field of the state vector falls outside its physically plausible range;
- the state observation has been entirely missing for more than `N_missing_max` consecutive control cycles.

**Pattern.** Availability + emergency mode.

**Parameters.**
- `staleness_max = 200 ms`.
- `N_missing_max = 5 cycles`.
- Plausible ranges: defined per state field in `cage/cage.yaml` (see `state_validity_ranges`).

**References hazard.** H-06.

**Implemented by.** Part of C-05 (emergency mode triggers).

**Verified by scenarios.** SC-PERT-02 (latency injection).

**Verifying metric.** M-S3.

**Satisfaction criterion.** When the trigger condition is induced (synthetically delayed or invalid state observation), the emergency mode activates within one control cycle.

---

## SR-008 — Controlled stop on demand

**Statement.** Upon reception of an external stop signal on the dedicated topic, or upon the controlled completion of an episode, the system shall produce an orderly deceleration to zero forward speed within `t_stop_max` and shall not exceed lateral offset `d_max` during the stopping manoeuvre.

**Pattern.** Emergency mode (external trigger).

**Parameters.**
- `t_stop_max = 1.5 s`.
- `d_max = 0.16 m` (same as SR-001).

**References hazard.** H-07.

**Implemented by.** Part of C-05 (emergency mode triggers) and the vehicle-control node.

**Verified by scenarios.** SC-NOM-03, SC-EDGE-04.

**Verifying metric.** M-S3 and stopping-distance log.

**Satisfaction criterion.** In every run where the stop signal is issued, the vehicle reaches v=0 within `t_stop_max` and never exceeds `d_max` lateral offset during the stop.

---

## Bidirectional coverage

Bidirectional coverage between hazards and SRs is verified by `tools/check_traceability.py`:

- Every H-XX is referenced by at least one SR (no orphan hazards).
- Every SR-XXX references at least one H-XX (no SRs floating in vacuum).

Current coverage at the time of this document's last update: see the change log entry.

## Open SRs under consideration

- *SR-???* on calibration drift detection during physical operation. To be registered if Phase 5 reveals the need.
- *SR-???* on cage rule conflict resolution. To be registered if unit testing reveals such cases.

## Change log

See `docs/08_change_log.md`.
