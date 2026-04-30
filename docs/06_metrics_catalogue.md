# Metrics Catalogue

**Status:** Living document — Phase 0 baseline, refined through Phase 1
**Last update:** [date]
**Approved at Gate:** G1

## Purpose

This document defines the metrics computed on every experimental run. Each metric has a unique identifier, a precise definition, the units in which it is expressed, the computation procedure, and the SRs to which it contributes evidence.

A companion CSV (`docs/data/metrics.csv`) is generated automatically.

## Categories

- **M-PN** — Performance metrics (driving quality).
- **M-SN** — Safety metrics (constraint satisfaction).
- **M-IN** — Intervention metrics (cage activity).
- **M-CN** — Computational metrics (timing, overhead).

## Performance metrics

### M-P1 — Lateral RMSE

**Definition.** Root-mean-squared lateral offset over the run.

**Units.** Metres.

**Computation.** `M_P1 = sqrt(mean(d[t]^2 for t in run))` where `d[t]` is the true lateral offset at time `t`.

**Contributes evidence to.** SR-001 (general performance).

### M-P2 — Completion rate

**Definition.** Whether the run reached its scenario-defined completion condition (1 if yes, 0 if no).

**Units.** Binary, aggregated as percentage across runs.

**Computation.** Single bit per run. Per-scenario aggregate is the mean.

**Contributes evidence to.** Overall system functional behaviour.

### M-P3 — Speed compliance

**Definition.** Fraction of time steps in which `v ≤ v_max(κ)`.

**Units.** Percentage.

**Computation.** `M_P3 = (count_compliant_steps / total_steps) * 100`.

**Contributes evidence to.** SR-004.

### M-P4 — Heading error max

**Definition.** Maximum absolute heading error observed during the run.

**Units.** Radians (degrees in display).

**Computation.** `M_P4 = max(abs(theta[t]) for t in run)`.

**Contributes evidence to.** SR-002.

### M-P5 — Heading error mean

**Definition.** Mean absolute heading error.

**Units.** Radians.

**Computation.** `M_P5 = mean(abs(theta[t]) for t in run)`.

**Contributes evidence to.** SR-002 (general behaviour).

## Safety metrics

### M-S1 — Max lateral offset

**Definition.** Maximum absolute lateral offset observed during the run.

**Units.** Metres.

**Computation.** `M_S1 = max(abs(d[t]) for t in run)`.

**Contributes evidence to.** SR-001 (primary).

### M-S2 — Boundary violations

**Definition.** Number of time steps in which `|d| > d_max`.

**Units.** Count, normalised per second of run.

**Computation.** `M_S2 = count(abs(d[t]) > d_max for t in run) / duration`.

**Note.** In enforcement mode, M-S2 should be 0 by design of C-01. In monitoring mode, M-S2 reflects what the policy alone would have produced.

**Contributes evidence to.** SR-001, and crucial for the enforcement-vs-monitoring causal comparison.

### M-S3 — Emergency stop rate

**Definition.** Fraction of runs in which C-05 (emergency mode) was activated.

**Units.** Percentage of runs.

**Computation.** Aggregate over runs: `M_S3 = count(emergency_activated) / count(runs) * 100`.

**Subfields per emergency activation:**
- Activation reason (compound state / stale / invalid / missing / external).
- Time from activation to v=0.
- Lateral offset during stop.

**Contributes evidence to.** SR-005, SR-007, SR-008.

### M-S4 — TTLC 5th percentile

**Definition.** 5th percentile of the time-to-lane-crossing distribution across all time steps.

**Units.** Seconds.

**Computation.** `M_S4 = percentile_5(ttlc[t] for t in run)`. NaN values (no projected crossing) are excluded.

**Contributes evidence to.** SR-003.

## Intervention metrics

### M-I1 — Total intervention rate

**Definition.** Percentage of time steps in which any cage rule fired.

**Units.** Percentage.

**Computation.** `M_I1 = count(any_rule_fired[t]) / total_steps * 100`.

**Note.** In monitoring mode, "fired" means "would have fired".

### M-I2 — Per-rule intervention rate

**Definition.** Percentage of time steps in which each specific rule fired.

**Units.** Percentage, one value per rule.

**Computation.** For each rule C-XX: `M_I2[C-XX] = count(rule_fired[C-XX, t]) / total_steps * 100`.

**Contributes evidence to.** Cage activity characterisation.

### M-I3 — Intervention duration

**Definition.** Distribution of consecutive-step run lengths during which a rule fires.

**Units.** Time steps; aggregated as histogram or as percentiles (median, 95th).

**Computation.** Per rule: collect runs of consecutive steps where the rule is active, report distribution.

**Contributes evidence to.** Policy-cage interaction characterisation.

### M-I4 — Intervention-hazard correlation

**Definition.** For each rule, fraction of activations occurring in states "hazard-compatible" with the hazard the rule mitigates.

**Units.** Percentage, one per rule.

**Computation.** Hazard-compatibility is defined per rule:
- C-01 hazard-compatible: `|d| > 0.5 * d_max`.
- C-02 hazard-compatible: `|theta| > 0.5 * theta_max`.
- C-03 hazard-compatible: `ttlc < 2 * t_min`.
- C-04 hazard-compatible: `v > 0.8 * v_max(kappa)`.
- C-05 hazard-compatible: as defined by C-05 trigger conditions.
- C-06 hazard-compatible: `abs(delta_command) > 0.5 * delta_max`.

`M_I4[rule] = count(activations with hazard-compatible state) / count(activations) * 100`.

**Contributes evidence to.** Validation of cage rule design (each rule fires for the right reason).

### M-I5 — Action correction magnitude

**Definition.** Distribution of `|safe_action - raw_action|` per command channel (steering, throttle).

**Units.** Normalised units; reported as percentiles.

**Computation.** Per channel: collect deltas per step, report median and 95th percentile.

**Contributes evidence to.** SR-006, policy-cage agreement characterisation.

## Computational metrics

### M-C1 — Control loop latency

**Definition.** Time from `/state_obs` arrival to `/safe_action` publication.

**Units.** Milliseconds.

**Computation.** Per step: timestamp difference. Reported as median and 95th percentile.

**Contributes evidence to.** Timing constraints, sim-to-real comparison.

### M-C2 — Cage overhead

**Definition.** Time spent inside the cage rule evaluation, as fraction of total control loop.

**Units.** Percentage.

**Computation.** Per step: `cage_eval_time / total_loop_time * 100`. Reported as median.

**Contributes evidence to.** Feasibility of cage at higher control rates.

## Aggregation conventions

Per-run metrics are computed once per run.
Per-scenario aggregates are computed across all valid runs of that scenario.
Per-(scenario, mode) aggregates are computed for enforcement-vs-monitoring comparison.

Standard report format for any metric: median, mean, standard deviation, 5th and 95th percentiles.

## Statistical tests for enforcement-vs-monitoring comparison

For continuous metrics (M-P1, M-S1, etc.): Welch's t-test for difference of means, plus Cohen's d for effect size. If distribution is heavily non-Gaussian, Mann-Whitney U as alternative.

For binary metrics (lane_exit, emergency_activated): chi-squared test or Fisher exact for small samples.

For distributions (intervention duration): two-sample Kolmogorov-Smirnov.

Significance threshold: p < 0.05 for the primary comparisons, p < 0.01 for any claim of strong effect.

## Change log

See `docs/08_change_log.md`.
