# Safety Requirements Specification

**Status:** Living document — Phase 1 deliverable  
**Last update:** 13.05.2026  
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

**Statement.** Under the operational ODD, the absolute lateral offset of the vehicle relative to the road centreline shall not exceed `d_max` at any time during autonomous operation.

**Pattern.** Direct threshold.

**Parameters.**

- `d_max = 0.16 m`, derived as `ODD-1.ROAD_WIDTH/2 − Δ = 0.25 − 0.09 = 0.16 m`, where `ODD-1.ROAD_WIDTH = 0.50 m` per the ODD Specification (`docs/08_odd_specification.md` §4.2) and `Δ = 0.09 m` aggregates three independent contributions: lateral-noise estimator uncertainty ≈ 0.01 m, drift over one nominal control latency `v_max · ODD-1.LATENCY_NOMINAL = 0.5 m/s · 50 ms = 0.025 m`, and the half-width of the CobraFlex 1:14 lateral footprint ≈ 0.05 m.

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

- `θ_max = 25 degrees (0.44 rad)`. The value is derived from a bicycle-model recoverability calculation. Under a bicycle model with wheelbase `L ≈ 0.15 m` for the 1:14 CobraFlex, maximum steering angle `δ_max ≈ 0.5 rad`, nominal forward speed `v = 0.3 m/s`, and cage response time `τ_cage = 0.05 s` (one control cycle), the maximum recoverable heading error is the angle from which a saturated steering correction returns the heading to zero before the lateral position reaches `d_max = 0.16 m` (SR-001). The first-order lateral displacement induced by a heading error θ over the response time τ_cage is `Δd ≈ v · sin(θ) · τ_cage`; the additional displacement until heading returns to zero under saturated correction is bounded by `v² · sin(θ) / (δ_max · v / L) = v · L · sin(θ) / δ_max`. The 25° value falls comfortably inside this envelope with margin of approximately a factor of two; the calculation is to be reproduced in the manuscript appendix.

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

- `t_min = 1.0 s` — decomposed as approximately 0.3 s for the cage to apply a saturated correction (cage-internal, defensible by the kinematic model: a saturated correction at gain 1.5 brings lateral offset back inside the safe band within roughly six control cycles at 20 Hz) plus approximately 0.7 s for the policy to resume nominal lane-following after a temporary cage override. The 0.7 s policy-side component is **provisional**: it is a first-cut estimate that depends on the trained policy's recovery behaviour and is observable only after a training prototype is available (Phase 3). The value will be revisited at the close of Phase 3 against the empirical recovery-time distribution and adjusted upward if the prototype's 95th percentile recovery time exceeds 0.7 s.
- 5th percentile floor: 0.5 s. This meta-criterion on the TTLC distribution guards against the case where the policy operates consistently in a marginal regime (median TTLC just above `t_min` but with a long left tail). The floor is set at half of `t_min` as a conservative default.

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

- `v_max_straight = 0.5 m/s` (on straight sections, |κ| < 0.05 rad/m). The value is the platform-envelope upper bound under nominal operation, mirrored from `ODD-1.V_MAX`. Final calibration depends on measurement M-4 (speed-vs-curvature characterisation); the parameter is conservative pending that measurement.
- `v_max_curve = 0.25 m/s` (on curved sections, |κ| ≥ 0.05 rad/m). The value reflects the kinematic envelope at the tightest curvature on the track; below this speed, the platform should track the curve without losing traction under the simulated friction coefficient. The exact relationship between speed, curvature and skid threshold depends on `ODD-3.FRICTION` (TBD-Q1 in the ODD specification) and `ODD-3.KAPPA_MAX` (TBD-Q9). The value is conservative pending measurement M-4.
- Smooth interpolation: `v_max(κ) = max(v_max_curve, v_max_straight − k_κ · |κ|)` with `k_κ = 0.3 m/s per unit curvature`. The coefficient is set so that the linear interpolation crosses the curve cap exactly at `|κ| = (v_max_straight − v_max_curve) / k_κ ≈ 0.83 rad/m`, which is the working assumption for the tightest curve on the `odd3_curvy_loop` map; the value will be tightened once `ODD-3.KAPPA_MAX` is measured.

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

- `θ_warning = 20 degrees`. Set strictly below `θ_max = 25°` (SR-002) to provide an early-warning band of approximately 5° during which the compound trigger can engage before the heading-stability limit is breached.
- `d_warning = 0.12 m`. Set strictly below `d_max = 0.16 m` (SR-001) to provide an early-warning lateral band of 0.04 m, equivalent to roughly two control-cycles of drift at maximum operating speed.
- `Δt_max = 0.2 s` = 4 control cycles. The sustained-condition requirement (STPA-informed, cf. Hazard Register §H-04) guards against transient glitches triggering emergency mode unnecessarily: a single noisy state observation that briefly violates both warning thresholds should not trigger emergency, but a genuine compound state persisting across four cycles or more should. An instantaneous trigger (Δt_max = 0) would produce spurious activations under benign sensor noise.
- `a_min = 0.3 m/s²` (minimum deceleration during emergency). The value is **provisional pending measurement M-3** (maximum platform deceleration). The choice is conservative: the kinematic stopping time at `v = v_max_straight = 0.5 m/s` is `t_stop = v / a_min ≈ 1.67 s`, which is consistent with SR-008's `t_stop_max = 1.7 s`. If M-3 demonstrates a higher achievable deceleration on the platform, `a_min` may be raised in a subsequent revision (with consequent tightening of `t_stop_max` in SR-008); if M-3 demonstrates a lower achievable deceleration, `a_min` must be reduced and the operating-speed envelope tightened accordingly.

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

- `δ_max_steering = 0.15` (normalised units per 50 ms cycle). Set as a **conservative default**: it bounds the rate of change to 15 % of the full command range per cycle, so a fully saturated change from −1 to +1 requires at least 14 cycles (0.7 s) — sufficiently aggressive to allow legitimate corrections, sufficiently smooth to attenuate outlier commands and oscillations. Final calibration depends on measurement M-5 (actuator rate envelope): the value must remain comfortably below the steering servo's physical δ-per-cycle envelope. After the first training prototype (Phase 3), the value will also be cross-checked against the 95th-percentile delta of the policy's natural action distribution; if the policy's natural deltas exceed 0.15 frequently, the rate limiter is doing more than catching outliers and either the limit must be relaxed or the policy must be retrained with explicit smoothness regularisation.
- `δ_max_throttle = 0.10` (normalised units per 50 ms cycle). Same logic as steering, with a tighter default because throttle changes have larger inertial consequences (acceleration spikes) than steering changes.

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

- `staleness_max = 200 ms` = 4 control cycles at 20 Hz. Conservative operational default: a sensor whose most recent reading is older than four control cycles is treated as no longer reflecting the present state of the vehicle. The value is mirrored in `cage/cage.yaml` (`control.staleness_max_ms`) and in `ODD-1.STALENESS_MAX`.
- `N_missing_max = 5 cycles` = 250 ms of consecutive missing observations before emergency mode triggers. Slightly looser than `staleness_max` because gap-counting requires more cycles to be confident the messages are genuinely absent rather than briefly delayed. The pair (`staleness_max`, `N_missing_max`) provides defence in depth: the former catches stale-but-arriving observations, the latter catches outright message loss.
- Plausible ranges: defined per state field in `cage/cage.yaml` (see `state_validity_ranges`). The ranges are deliberately broader than the operational envelope of each state (e.g. lateral offset ±0.30 m vs `d_max = 0.16 m`) so that range violations are unambiguous sensor faults, not normal-operation excursions.

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

- `t_stop_max = 1.7 s`. The value is derived from SR-005's minimum deceleration `a_min = 0.3 m/s²` at the maximum nominal operating speed `v_max_straight = 0.5 m/s` (SR-004): the kinematic stopping time is `v / a_min = 0.5 / 0.3 ≈ 1.67 s`, rounded conservatively to 1.7 s to absorb actuator response latency and measurement granularity. *Consistency note:* the previous baseline value (`t_stop_max = 1.5 s`) was mutually inconsistent with SR-005 at `v_max_straight`; the value was raised to 1.7 s in the 13.05.2026 revision (see CHANGELOG) to close the inconsistency. If M-3 demonstrates a higher achievable deceleration and `a_min` is subsequently raised, `t_stop_max` is to be tightened correspondingly in a single coordinated revision of SR-005 and SR-008.
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

See `docs/CHANGELOG.md`.
