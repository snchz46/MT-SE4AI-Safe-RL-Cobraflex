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

A companion CSV (`docs/data/safety_requirements.csv`) is generated automatically from the machine-readable table at the bottom of this document by `tools/sync_safety_requirements.py`.

## Pattern catalogue

The SRs use a small set of recurring patterns:

- **Direct threshold** — a measurable variable shall not exceed (or shall not fall below) a fixed value at any time.
- **Predictive threshold** — a forward-looking estimate shall remain within bounds.
- **Bounded derivative** — the change of a variable between two time steps shall not exceed a bound.
- **Availability** — a service or signal shall be available within timing constraints.
- **Emergency mode** — under specified conditions, a specified mode shall be entered.
- **Operational envelope** — the joint state of variables shall remain within a defined region.
- **Liveness** — a measurable progress quantity shall not remain below a threshold for longer than a specified window. Distinct from the other patterns above, which are all *safety* (a forbidden condition shall not occur); liveness asserts that a desired condition *shall* occur within bounded time.
- **Bounded variance** — a derived statistic (typically standard deviation) of a state variable over a sliding window shall not exceed a threshold. A strengthening of "direct threshold" that catches *within-band oscillation* — a signal that is bounded in magnitude but exhibits high-frequency content.

---

## SR-001 — Lane departure prevention (direct)

**Statement.** Under the operational ODD, the absolute lateral offset of the vehicle relative to the road centreline shall not exceed `d_max` at any time during autonomous operation.

**Pattern.** Direct threshold.

**Parameters.**

- `d_max = 0.16 m`, derived as `ODD-1.ROAD_WIDTH/2 − Δ = 0.25 − 0.09 = 0.16 m`, where `ODD-1.ROAD_WIDTH = 0.50 m` per the ODD Specification (`docs/08_odd_specification.md` §4.2) and `Δ = 0.09 m` aggregates three independent contributions: lateral-noise estimator uncertainty ≈ 0.01 m, drift over one nominal control latency `v_max · ODD-1.LATENCY_NOMINAL = 0.5 m/s · 50 ms = 0.025 m`, and the half-width of the CobraFlex 1:14 lateral footprint ≈ 0.05 m. The arithmetic sum is 0.085 m; `Δ` is **rounded up to 0.09 m** to absorb the residual uncertainty in each of the three contributions (each value is itself a first-order estimate). The round-up is conservative: it shrinks `d_max` by 5 mm relative to the arithmetic floor.

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

**Statement.** The system shall transition into an emergency mode when any of the following triggers fires:

- **Trigger A (compound state, low-energy):** `|θ| > θ_warning AND |d| > d_warning`, sustained for at least `Δt_max` consecutive seconds.
- **Trigger B (compound state, high-energy):** `|θ| > θ_warning AND |d| > d_warning AND v > v_warning`, sustained for at least `Δt_max_fast` consecutive seconds. Trigger B is the high-speed shortcut: at elevated speed, the kinematic margin is smaller and the persistence requirement is shortened accordingly. (Triggers C–F covering staleness, invalid range, missing messages, and external stop are specified in SR-007 / SR-008 respectively and use C-05's broader trigger set.)

The emergency mode is characterised by:

- a deceleration of at least `a_min` until full stop,
- the steering command frozen at its value at the instant of transition,
- an emergency signal published on the dedicated topic.

**Pattern.** Emergency mode (composite trigger, deterministic response).

**Parameters.**

- `θ_warning = 20 degrees`. Set strictly below `θ_max = 25°` (SR-002) to provide an early-warning band of approximately 5° during which the compound trigger can engage before the heading-stability limit is breached.
- `d_warning = 0.12 m`. Set strictly below `d_max = 0.16 m` (SR-001) to provide an early-warning lateral band of 0.04 m, equivalent to roughly two control-cycles of drift at maximum operating speed.
- `v_warning = 0.4 m/s` (80 % of `v_max_straight`). Above this speed, the compound state with heading and lateral warning is treated as high-energy: at `v_warning · sin(θ_warning) · Δt_max ≈ 0.4 · 0.34 · 0.2 ≈ 0.027 m`, the additional drift accumulated during the standard persistence interval already approaches half of the early-warning band, so the kinematic margin to recover compound state under correction is materially smaller than at low speed. Trigger B closes this gap with a shorter persistence requirement.
- `Δt_max = 0.2 s` = 4 control cycles (Trigger A). The sustained-condition requirement (STPA-informed, cf. Hazard Register §H-04) guards against transient glitches triggering emergency mode unnecessarily: a single noisy state observation that briefly violates both warning thresholds should not trigger emergency, but a genuine compound state persisting across four cycles or more should.
- `Δt_max_fast = 0.1 s` = 2 control cycles (Trigger B). At high speed, the kinematic margin halves with the persistence requirement; two cycles is the minimum to distinguish persistent compound state from single-cycle sensor noise while preserving the time-to-action budget under elevated speed.
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

## SR-009 — Minimum forward progress (liveness)

**Statement.** Under the operational ODD, the vehicle shall accumulate at least `Δs_min` of forward longitudinal progress in any sliding window of `t_window` seconds that is *eligible* — i.e., the window lies entirely within an interval during which (i) the system is in nominal mode, (ii) no external stop signal is active, and (iii) at least `Δt_settle` seconds have elapsed since the most recent transition into nominal mode.

**Pattern.** Liveness.

**Parameters.**

- `Δs_min = 0.10 m` (10 cm of forward progress per window). Derived from the lower bound of meaningful forward motion: at the minimum operationally useful speed `v_min ≈ 0.05 m/s` over the window `t_window = 2 s`, the kinematic floor is `0.05 · 2 = 0.10 m`. Below this threshold the vehicle is effectively stationary at the operating timescale.
- `t_window = 2.0 s` = 40 control cycles at 20 Hz. Long enough to admit legitimate transient slowdowns (curve negotiation, recovery after a cage intervention) without false-positive stall detection, short enough that a converged-to-inaction policy is detected within a single test scenario.
- `Δt_settle = 1.0 s` = 20 control cycles. *Settling clause to resolve conflict with SR-005 / SR-008.* When the system transitions back into nominal mode after an emergency mode (SR-005) or a controlled stop (SR-008), the vehicle is at `v = 0` and must ramp up. A naive sliding window evaluated at `t = 0+` after the transition would catch a ramp-up phase whose progress is by construction below `Δs_min` (e.g., linear ramp from `v = 0` to `v_min` over 1 s yields `≈ 0.075 m`, below the floor). `Δt_settle = 1.0 s` is set to the upper bound of the expected ramp-up duration: at `a_min = 0.3 m/s²` (SR-005) the time to reach `v_min = 0.05 m/s` from rest is `v_min/a_min ≈ 0.17 s`; the floor is set 5× higher to absorb actuator-response latency, command-smoothing through C-06, and policy-side ramp-up that may be slower than `a_min` allows. The settling window does **not** suspend SR-005 or SR-008 — those continue to apply at every instant — it only suspends the SR-009 liveness check.

**References hazard.** H-08.

**Implemented by.** *Training constraint* (reward shaping). The mitigation lives at the policy-training specification level rather than at the runtime cage level: the reward function shall include a non-trivial positive progress term and/or a stall penalty calibrated such that the optimal policy under finite training does not converge to inaction. A runtime cage rule that forced `throttle > 0` would be ortogonal to the cage's filosofía (correct unsafe commands, not inject progress) and is therefore explicitly out of scope; the cage instead provides *observation* of stall through M-P6 and the optional emission of a stall-detection signal that is consumed by the test harness (not by the vehicle-control node).

**Verified by scenarios.** SC-NOM-01, SC-NOM-02, SC-NOM-03 (nominal scenarios; M-P6 and M-S2-monitoring are both computed across the eligible interval of each run). SC-PERT-03 (reward-injection negative test, ensures the verification machinery detects induced stall — see scenario library).

**Verifying metric.** M-P6 (stall rate, catches the inaction sub-mode of H-08) **and** M-S2 measured under monitoring mode (catches the adversarial-direction sub-mode by quantifying how often the policy alone — without cage corrections — would have breached the boundary). The two metrics together cover both sub-modes of H-08; either being non-zero on the released policy is grounds for retraining.

**Satisfaction criterion.** Across all runs of the verifying scenarios under the released policy: (i) M-P6 shall be 0 %, i.e., no eligible sliding window of `t_window` records less than `Δs_min` of forward progress; (ii) the ratio `M-S2(monitoring) / M-S2(enforcement)` shall not be substantially elevated relative to a reference baseline policy — a sustained increase indicates the policy depends on cage corrections to a degree that suggests adversarial behaviour rather than benign reliance.

**Conflict-resolution note.** SR-009 deliberately yields to SR-005 and SR-008. During emergency mode (SR-005), during stop-signal-driven deceleration (SR-008), and during the post-transition settling window (`Δt_settle`), the liveness check is suspended. This priority ordering is by design: a transient absence of progress while the cage executes a legitimate safety response is not a SR-009 violation, even though it superficially resembles one.

---

## SR-010 — Cage rule composition consistency

**Statement.** When two or more cage rules activate within the same control cycle, the cage's deterministic evaluation pipeline (specified in §Evaluation order of the Cage Specification) shall produce a final command that satisfies the safe-envelope predicate of every individually activated rule, and the cage's intervention pattern across consecutive cycles shall not exhibit sustained oscillation between contradictory rules.

**Pattern.** Operational envelope (joint cage-output consistency) + bounded oscillation (inter-cycle stability).

**Parameters.**

- **Evaluation order.** The composition of rule corrections is defined by the deterministic pipeline declared in §Evaluation order of `docs/04_cage_specification.md`. In short: (i) C-05 short-circuits all subsequent rules; (ii) C-01 and C-02 operate co-equally on steering with additive combination; (iii) C-03's correction is max-merged with C-01's (worst-case envelope wins); (iv) C-04 operates independently on throttle; (v) C-06 is applied last and bounds the rate of the final command. This ordering is the source of truth; SR-010 asserts properties *over* this composition rather than dictating a different one.
- **Joint-envelope assertion.** At the end of every control cycle, the emitted command `command_out` shall satisfy the safe-envelope predicate `P_R(command_out)` of every rule R that fired in the cycle. Formally: `∄ R : fired(R, cycle) ∧ ¬P_R(command_out) ∧ ¬emergency_active`. If the assertion fails, the cage shall (a) log the failure with the offending rule set, and (b) fall back to C-05 (emergency mode) for the remainder of the run.
- **Bounded inter-cycle oscillation.** The rule-activation pattern across cycles shall not exhibit alternation at a frequency above `f_osc_max = 5 Hz` between contradictory rules. *Contradictory* means: rules whose corrections push the command in opposite directions on the same channel (e.g., C-01 firing left in cycle `n` and C-01 firing right in cycle `n+1`).

**References hazard.** H-09.

**Implemented by.** *Cage architecture* — specifically the post-C-06 joint-envelope assertion and the fallback logic, neither of which is a numbered cage rule but rather a structural property of the cage pipeline. The implementation lives in `cage/cage_node.py::end_of_cycle_check()` and is documented in §Joint-envelope assertion of `docs/04_cage_specification.md`. *Verified by scenario test* and dedicated cage unit tests enumerating rule-pair and rule-triple activation combinations.

**Verified by scenarios.** SC-EDGE-04 (compound state, where multiple cage rules are expected to activate simultaneously), SC-EDGE-05 (cage rule co-activation matrix, dedicated to enumerating pair and triple activations), and unit tests under `cage/tests/test_evaluation_order.py`.

**Verifying metric.** M-S2 (boundary violations) and M-I3 (intervention duration). M-S2 detects joint-envelope failures: if the cage emits a command outside any active rule's envelope, the boundary violation count is non-zero. M-I3 detects oscillation: a sustained alternation between two contradictory rules appears as a bimodal intervention-duration distribution with both modes ≤ 2 cycles.

**Satisfaction criterion.** Across all runs of the verifying scenarios in enforcement mode: (i) M-S2 = 0 (zero boundary violations of any lane or heading limit); (ii) no run logs a joint-envelope assertion failure; (iii) the M-I3 distribution per rule does not show a peak at ≤ 2 cycles paired with consecutive opposite-direction firings exceeding `f_osc_max`. The cage unit-test suite shall pass for every documented rule-pair and rule-triple activation combination.

---

## SR-011 — Heading stability without sustained oscillation

**Statement.** Under the operational ODD and in eligible nominal-mode intervals, the heading-error signal `θ(t)` shall satisfy two conditions: (i) the magnitude bound of SR-002 (`|θ| ≤ θ_max`), and (ii) the standard deviation of θ over any sliding window of `t_psd = 1.0 s` shall not exceed `σ_θ_max`.

**Pattern.** Bounded variance (a strengthening of the magnitude bound in SR-002 to also constrain in-band oscillation).

**Parameters.**

- `σ_θ_max = 0.087 rad (5 degrees)`. The value is set such that a bounded oscillation of amplitude `A` at frequency `f` produces `σ_θ ≈ A/√2`; thus `σ_θ_max = 5°` admits oscillations up to ≈ 7° amplitude, which is well below `θ_max = 25°` but tight enough to flag the within-bounds-but-oscillatory failure mode described in H-02. The choice will be revisited after Phase 3 against the trained policy's natural heading-variance distribution; if the policy's median `σ_θ` already lies well below 5°, the limit may be tightened.
- `t_psd = 1.0 s` = 20 control cycles. The window must be long enough to capture at least one full period of the lowest-frequency oscillation of concern (≈ 1 Hz, the timescale at which sustained heading oscillation becomes perceptually and dynamically significant) and short enough to avoid masking by drift on longer timescales.
- **Eligibility carve-outs.** The verdict on σ_θ excludes (i) the first 0.5 s of any nominal interval (admits the legitimate corrective response after a perturbation, in symmetry with SR-009's settling logic), (ii) any interval during which C-02 is actively firing (the rule's intervention transient is not a SR-011 violation), and (iii) any emergency-mode interval.

**References hazard.** H-02 (oscillation branch; SR-002 covers the divergence branch).

**Implemented by.** C-06 (rate limiter, indirect — bounds the rate of policy commands and thus attenuates high-frequency content in θ) *and* a *training constraint* on the reward function: the reward shall include a heading-variance penalty calibrated such that the optimal policy under finite training does not exhibit sustained in-band oscillation. The runtime cage does not directly enforce SR-011 — the cage attenuates but cannot remove a policy's tendency to oscillate — so the principal mitigation lives at the training level.

**Verified by scenarios.** SC-EDGE-01 (initial heading perturbation, the principal stress test for heading dynamics), SC-EDGE-04 (compound state, secondary).

**Verifying metric.** M-P7 (heading variability — 95th-percentile σ_θ over eligible windows).

**Satisfaction criterion.** Across all runs of the verifying scenarios under the released policy, M-P7 (95th percentile across eligible windows) shall be ≤ `σ_θ_max`.

---

## Machine-readable Safety Requirements Table

| SR ID | Statement | Pattern | Hazards | implementation_type | Scenarios | Metric | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SR-001 | Lane departure prevention (direct) | Direct threshold | H-01 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | Open | d_max = 0.16 m |
| SR-002 | Heading stability | Direct threshold | H-02 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | Open | θ_max = 25 deg |
| SR-003 | Predictive lane departure prevention (TTLC) | Predictive threshold | H-01, H-02 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | Open | t_min = 1.0 s; provisional |
| SR-004 | Speed compliance | Direct threshold | H-03 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | Open | Curvature-parameterised ceiling |
| SR-005 | Emergency mode for compound state | Emergency mode | H-04, H-07 | C-05 | SC-EDGE-04 | M-S3 | Open | Δt_max = 0.2 s; a_min provisional |
| SR-006 | Actuator smoothness | Bounded derivative | H-05 | C-06 | ALL | M-I5 | Open | Always active |
| SR-007 | State validity and freshness | Availability + emergency | H-06 | C-05 | SC-PERT-02 | M-S3 | Open | staleness_max = 200 ms |
| SR-008 | Controlled stop on demand | Emergency mode | H-07 | C-05 | SC-NOM-03, SC-EDGE-04 | M-S3 | Open | t_stop_max = 1.7 s |
| SR-009 | Minimum forward progress (liveness) | Liveness | H-08 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | Open | Δs_min = 0.10 m / t_window = 2.0 s / Δt_settle = 1.0 s |
| SR-010 | Cage rule composition consistency | Operational envelope + bounded oscillation | H-09 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | Open | Joint-envelope assertion + f_osc_max = 5 Hz |
| SR-011 | Heading stability without sustained oscillation | Bounded variance | H-02 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | Open | σ_θ_max = 5°, t_psd = 1.0 s |

---

## Bidirectional coverage

Bidirectional coverage between hazards and SRs is verified by `tools/check_traceability.py`:

- Every H-XX is referenced by at least one SR (no orphan hazards).
- Every SR-XXX references at least one H-XX (no SRs floating in vacuum).

Current coverage at the time of this document's last update: see the change log entry.

## Open SRs under consideration

- *SR-???* on calibration drift detection during physical operation. To be registered if Phase 5 reveals the need.

## Change log

See `docs/CHANGELOG.md`.
