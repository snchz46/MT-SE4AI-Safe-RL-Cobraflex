# Scenario Library

**Status:** Living document — Phase 2 deliverable, closed at G2; updated through G3 and G4  
**Last update:** 13.05.2026
**Approved at Gate:** G2 (initial), G4 (final)

## Purpose

This document is the canonical specification of the validation scenarios used to evaluate the system. Each scenario is a reproducible experiment with explicit initial conditions, perturbations, termination criteria, primary metrics, and pass/fail criteria.

A scenario is *closed* when its YAML definition under `scenarios/<category>/sc_<category>_NN.yaml` has been validated by `tools/check_scenario_yaml.py` and approved at the corresponding Gate review.

## Categories

- **Nominal (NOM)** — operational conditions within the ODD.
- **Edge (EDGE)** — at the boundary of the ODD, designed to stress specific cage rules.
- **Perturbed (PERT)** — sensor noise, latency, or other perturbations applied during operation.

## Scenario template

Every scenario specifies, at minimum:

| Field | Meaning |
| ------- | --------- |
| `id` | The identifier (SC-NOM-01, etc.) |
| `category` | nominal, edge, or perturbed |
| `description` | Free-text |
| `initial_conditions` | Vehicle pose, velocity, environment state |
| `perturbations` | What is applied during the run, when, with what magnitude |
| `termination` | How the run ends (timeout, event, completion) |
| `metrics_primary` | The metrics that determine pass/fail |
| `metrics_secondary` | Additional metrics reported but not used for verdict |
| `pass_criterion_per_run` | When a single run passes |
| `pass_criterion_per_scenario` | When the scenario as a whole is satisfied |
| `references_SR` | Which SRs this scenario verifies |
| `n_runs_recommended` | Suggested number of runs for statistical validity |

The full YAML schema is in `scenarios/_schema.yaml`.

---

## SC-NOM-01 — Straight nominal

**Description.** Vehicle initialises at the start of a straight section with zero offset and zero heading error. Nominal commanded speed (0.4 m/s). No perturbations. Run for the time required to traverse the straight twice.

**Initial conditions.**

- Pose: `(x=0, y=0, θ=0)` ± uniform noise `[-0.02 m, +0.02 m]` lateral, `[-2 deg, +2 deg]` heading.
- Speed: 0.

**Perturbations.** None.

**Termination.** After 30 seconds of simulated time, or upon lane exit.

**Metrics primary.** M-P1 (lateral RMSE), M-P2 (completion rate), M-P6 (stall rate), M-I1 (intervention rate).

**Pass criterion per run.** Lateral RMSE < 0.05 m, completion = 1, no emergency stop, M-P6 = 0%.

**Pass criterion per scenario.** ≥ 95% of runs pass.

**References SR.** SR-001, SR-006, SR-009.

**Cage rules exercised.** C-01 (boundary), C-06 (rate limiter, always active under enforcement mode). C-03 is exercised indirectly through SR-003 verification across nominal runs.

**Recommended runs.** 50 per mode (enforcement, monitoring).

---

## SC-NOM-02 — Curved nominal

**Description.** Vehicle initialises at the entry of a curved section. Negotiates the curve at nominal speed.

**Initial conditions.** Pose at curve entry, zero offset, zero heading. Speed: 0.3 m/s.

**Perturbations.** None.

**Termination.** Curve fully traversed plus 5 m of subsequent straight, or lane exit.

**Metrics primary.** M-P1, M-P2, M-P6, M-S1, M-I1.

**Pass criterion per run.** Lateral RMSE < 0.07 m, max lateral offset < 0.16 m, completion = 1, M-P6 = 0%.

**Pass criterion per scenario.** ≥ 95% of runs pass.

**References SR.** SR-001, SR-003, SR-004, SR-009.

**Recommended runs.** 50 per mode.

---

## SC-NOM-03 — Full circuit

**Description.** Vehicle completes three full laps of the closed circuit (alternating straights and curves). Tests consistency over extended duration.

**Initial conditions.** Lap start position, zero offset, zero heading. Speed: 0.

**Perturbations.** None.

**Termination.** 3 laps completed, or lane exit, or timeout (120 s).

**Metrics primary.** M-P1, M-P2, M-P6, M-S1, M-S3, M-I5 (smoothness over extended duration).

**Pass criterion per run.** 3 laps completed without emergency stop, lateral RMSE < 0.06 m, M-P6 = 0%, no SR-006 violation across the run.

**Pass criterion per scenario.** ≥ 90% of runs pass.

**References SR.** SR-001, SR-002, SR-003, SR-004, SR-006, SR-008, SR-009.

**Recommended runs.** 20 per mode.

---

## SC-EDGE-01 — Initial heading perturbation

**Description.** Vehicle initialises with a 15-degree heading error but zero lateral offset. Tests the policy's ability to recover heading without lane exit, and the activation of C-02 / C-03.

**Initial conditions.** Pose: `(x=0, y=0, θ=15 deg)`. Speed: 0.3 m/s.

**Perturbations.** None.

**Termination.** Straight fully traversed, or lane exit.

**Metrics primary.** M-I1 (especially for C-02, C-03), M-S3, M-P7 (heading variability — verifies SR-011 anti-oscillation), time-to-recovery (heading < 3 deg).

**Pass criterion per run.** No emergency stop; heading recovered to < 3 deg within 2 s; no lane exit; M-P7 95th percentile below `σ_θ_max` after the initial transient (first 0.5 s excluded from the M-P7 verdict to admit the legitimate corrective response).

**Pass criterion per scenario.** ≥ 90% of runs pass.

**References SR.** SR-002, SR-003, SR-011.

**Recommended runs.** 30 per mode.

---

## SC-EDGE-02 — Initial lateral perturbation

**Description.** Vehicle initialises with a 0.12 m lateral offset (near C-01 warning) but zero heading. Tests recovery without touching boundary, activation of C-01 / C-03.

**Initial conditions.** Pose: `(x=0, y=0.12, θ=0)`. Speed: 0.3 m/s.

**Perturbations.** None.

**Termination.** Straight fully traversed, or lane exit.

**Metrics primary.** M-I1 (C-01, C-03), M-S1, time-to-recovery (offset < 0.05 m).

**Pass criterion per run.** Max offset never exceeds 0.16 m; offset recovered to < 0.05 m within 3 s.

**Pass criterion per scenario.** ≥ 90% of runs pass.

**References SR.** SR-001, SR-003.

**Recommended runs.** 30 per mode.

---

## SC-EDGE-03 — Speed perturbation

**Description.** During nominal operation on a straight, a 200 ms throttle pulse is injected (as if an exogenous action forced sudden acceleration). Tests C-04.

**Initial conditions.** Nominal start as in SC-NOM-01.

**Perturbations.** At t = 5 s, throttle override to maximum for 200 ms, then released.

**Termination.** Straight fully traversed, or lane exit.

**Metrics primary.** M-I1 (C-04), duration of speed excess, lateral RMSE during incident.

**Pass criterion per run.** Speed exceeds `v_max(κ)` for less than 250 ms; no lane exit.

**Pass criterion per scenario.** ≥ 90% of runs pass.

**References SR.** SR-004.

**Recommended runs.** 20 per mode.

---

## SC-EDGE-04 — Compound state

**Description.** Vehicle initialises with both 10-degree heading error and 0.08 m lateral offset. Neither is severe alone, but the combination can lead to compound state (H-04). The cage should activate C-05 if irrecoverable, or recover before reaching that state.

**Initial conditions.** Pose: `(x=0, y=0.08, θ=10 deg)`. Speed: 0.3 m/s.

**Perturbations.** None.

**Termination.** Straight fully traversed, lane exit, or emergency stop completion.

**Metrics primary.** Activation of C-05 (M-S3), M-S2 (boundary violations post-cage, verifies SR-010), time-to-recovery, max offset.

**Pass criterion per run.** If C-05 activates, deceleration is orderly (≥ a_min) and no lane exit during stop. If C-05 does not activate, system recovers without lane exit. Across the run, M-S2 = 0 (the cage's final emitted command never breaches the lane boundary even under multi-rule activation).

**Pass criterion per scenario.** ≥ 85% of runs pass.

**References SR.** SR-002, SR-005, SR-008, SR-010, SR-011.

**Recommended runs.** 30 per mode.

---

## SC-EDGE-05 — Cage rule co-activation matrix

**Description.** Systematic stress test of the cage's joint behaviour. Parameterised over a grid of initial conditions designed such that, at `t = 0`, at least two of {C-01, C-02, C-03, C-04, C-06} are in their hazard-compatible state and likely to activate in the same cycle. C-05 is excluded from the matrix because it short-circuits the rest by design. Verifies SR-010 (joint-envelope assertion and inter-cycle oscillation).

**Initial conditions.** Parameterised grid over `(d, θ, v, dκ/dt)` with the following anchor points (each is a pair-activation seed; triples are formed by combining anchors):

- `(d, θ) = (0.10 m, 12 deg)` — likely C-01 + C-02.
- `(d, θ, ttlc_seed) = (0.08 m, 8 deg, 0.9 s)` — likely C-01 + C-03.
- `(v, κ_seed) = (0.45 m/s, 0.6 rad/m)` — likely C-04 + C-06.
- `(d, v, κ_seed) = (0.10 m, 0.45 m/s, 0.6 rad/m)` — likely C-01 + C-04 + C-06 (triple).
- `(d, θ, v) = (0.10 m, 12 deg, 0.45 m/s)` — likely C-01 + C-02 + C-04 (triple).

**Perturbations.** None at runtime; the stress is from initial-condition placement.

**Termination.** Pipeline emits a command satisfying the joint-envelope predicate for `t_psd_settle = 2 s` after entry, **or** joint-envelope assertion failure (Trigger 7 of C-05), **or** lane exit, **or** scenario timeout (10 s).

**Metrics primary.** M-S2 (boundary violations post-cage — SR-010), M-I2 (per-rule intervention rate, to confirm the seeded rules actually fired), M-I3 (intervention duration distribution — detects oscillation), count of joint-envelope assertion failures, count of inter-cycle oscillation events.

**Pass criterion per run.** Joint-envelope assertion never fails, M-S2 = 0, no inter-cycle oscillation flagged.

**Pass criterion per scenario.** ≥ 95% of grid points pass.

**References SR.** SR-010 (primary), SR-001, SR-002, SR-004, SR-006 (secondary — the individual rule envelopes must continue to hold under co-activation).

**Cage rules exercised.** C-01, C-02, C-03, C-04, C-06 in all documented pair and triple combinations.

**Recommended runs.** 5 per grid point × ≥ 20 grid points = ≥ 100 runs per mode.

---

## SC-PERT-01 — Sensor noise

**Description.** Gaussian noise with mean zero and standard deviation σ added to the observed lateral offset. Run at three noise levels.

**Initial conditions.** Nominal start (SC-NOM-01).

**Perturbations.** Continuous throughout the run: `d_observed = d_true + N(0, σ)`. Three levels:

- σ = 0.01 m
- σ = 0.03 m
- σ = 0.05 m

**Termination.** Straight fully traversed, or lane exit.

**Metrics primary.** M-I1 (expected to increase with σ), lateral RMSE, M-S1.

**Pass criterion per run.** For σ=0.01: behaves as nominal. For σ=0.05: documented degradation but no lane exit.

**Pass criterion per scenario.** Per-level pass thresholds documented.

**References SR.** SR-001, SR-007.

**Recommended runs.** 20 per noise level per mode (total 120 runs).

---

## SC-PERT-02 — Latency

**Description.** Artificial latency inserted between `/safe_action` publication and the actuator response. Run at two levels.

**Initial conditions.** Nominal start.

**Perturbations.** Latency injection: 50 ms, then 100 ms.

**Termination.** Straight fully traversed, or lane exit.

**Metrics primary.** M-I1 (expected to increase, particularly for C-03), max offset, M-S3.

**Pass criterion per run.** With 50 ms: stable operation. With 100 ms: documented degradation.

**Pass criterion per scenario.** Per-level pass thresholds documented.

**References SR.** SR-003, SR-007.

**Recommended runs.** 20 per latency level per mode.

---

## SC-PERT-03 — Reward-injection stall test (negative test for SR-009)

**Description.** A *negative* (failure-injection) test that fine-tunes a policy under a deliberately misaligned reward function and verifies that the verification machinery for SR-009 detects the induced failure. The injected reward exaggerates the stall incentive (raises per-step penalty for non-zero throttle or removes the progress term) and the test asserts that M-P6 becomes non-zero on the resulting policy, while the released policy under the standard reward still passes M-P6 = 0. Designed to validate that SR-009's verification can in principle detect the hazard H-08 is designed to flag — without this test, M-P6 = 0 on the released policy could equally mean "the policy is sound" or "the metric never detects anything", and the two are indistinguishable.

**Initial conditions.** Nominal start (SC-NOM-01 layout).

**Perturbations.** *Pre-run.* The policy used in the run is not the released policy but a controlled-stall variant: starting from the released policy checkpoint, a brief fine-tune (≈ 50 k steps) under a reward function modified by `r' = r - λ_stall · |throttle|` with `λ_stall` set such that the resulting policy exhibits clear stall behaviour. The exact `λ_stall` is determined empirically and recorded in the run metadata.

**Termination.** Standard SC-NOM-01 termination (30 s timeout or lane exit).

**Metrics primary.** M-P6 (stall rate on the stall variant — *expected to be high*), M-P6 (stall rate on the released policy under the same scenario — *expected to be 0 %*), M-P2 (completion rate).

**Pass criterion per run.** The stall variant produces M-P6 > 50 % (confirming the metric detects induced stall); the released policy produces M-P6 = 0 % and M-P2 = 1 (confirming the released policy is not in a stall regime).

**Pass criterion per scenario.** Both criteria above met across ≥ 90 % of runs.

**References SR.** SR-009.

**Recommended runs.** 20 per mode (released policy) + 20 per mode (stall variant) = 80 total.

---

## Subset for physical deployment (Phase 5)

Not all scenarios are exported to the physical platform; the budget of physical runs is limited. The selected subset:

- SC-NOM-01 (mandatory): the reference comparison scenario.
- SC-NOM-02 (recommended): if track geometry permits curves.
- SC-EDGE-01 (recommended): tests cage activation under controlled perturbation.

The selection rationale and the physical-specific adaptations are documented in the Phase 5 plan.

## Total scenario count

Current count: 11 scenarios (3 NOM, 5 EDGE, 3 PERT with multiple levels). SC-EDGE-05 and SC-PERT-03 added 13.05.2026 (G-3 and G-4 in the SR audit).

Total recommended runs in simulation, summed across all scenarios and both modes: approximately 1100 runs.

## Convention for `metrics_primary` value `"ALL"`

Some SRs (notably SR-006, the always-active rate limiter) are exercised across every scenario. When a SR is listed in a scenario's `References SR` and the verifying metric is global (i.e., computed identically in every run), the scenario's `metrics_primary` field uses the literal value `"ALL"` to indicate that the SR is verified by the scenario implicitly without requiring a dedicated primary metric. The `check_traceability.py` tool treats `"ALL"` as a valid scenario reference for back-coverage purposes.

## Bidirectional coverage

Every SR is referenced by at least one scenario. Every scenario references at least one SR. Verified by `tools/check_traceability.py`.

## Change log

See `docs/CHANGELOG.md`.
