# Metrics Catalogue

**Status:** Living document — Phase 0 baseline, refined through Phase 1; M-S5 added in F4; **verified at G4**  
**Last update:** 07.07.2026 (current-state framing note added)  
**Approved at Gate:** G1  

## Purpose

This document defines the metrics computed on every experimental run. Each metric has a unique identifier, a precise definition, the units in which it is expressed, the computation procedure, and the SRs to which it contributes evidence.

A companion CSV (`docs/data/metrics.csv`) is generated automatically.

> **Current-state framing (G4 closed, 02.07.2026).** The metrics are **track-neutral** and
> computed identically for the archived F-track baseline and the **track-'E' verdict of record**
> (GE4-V2, `docs/07`). One metric carries a track-specific caveat worth preserving: **M-P6
> (stall rate)** is **N/A-by-construction on the frozen 1-D steering-only action** — with no
> speed authority the policy cannot converge to inaction, so M-P6 ≡ 0 and its negative test
> SC-PERT-03 is inert (**D-49**). M-P6 becomes **well-posed only on the 2-D action** (steering +
> throttle) of the Isaac posterior track, where a true stop is commandable (**D-50**; SR-009's
> liveness sub-mode is then genuinely testable). **M-S5 (road-edge departure)** is the headline
> metric of the out-of-ODD Frontier cage-efficacy study (paired enforcement-vs-monitoring
> contrast, not folded into the global verdict — D-35).

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

### M-P6 — Stall rate

**Definition.** Fraction of *eligible* nominal-mode time steps in which the trailing sliding window of `t_window` seconds has accumulated less than `Δs_min` of forward longitudinal progress. A time step is *eligible* if it is in nominal mode (not emergency, no active stop signal) **and** at least `Δt_settle` seconds have elapsed since the most recent transition into nominal mode.

**Units.** Percentage (0 % = no stall observed; 100 % = full-run stall under nominal mode).

**Computation.** For each control step `t` in the run: (i) determine eligibility per the definition above; (ii) compute trailing-window progress `Δs(t) = ∫_{t-t_window}^{t} v(τ) dτ`; (iii) flag as stall step if `Δs(t) < Δs_min`. Aggregate as `M_P6 = (stall_steps / eligible_steps) * 100`. If `eligible_steps == 0` (e.g., scenario entirely in emergency mode), `M_P6` is undefined and the verdict for SR-009 falls through to scenario semantics.

**Contributes evidence to.** SR-009.

### M-P7 — Heading variability

**Definition.** Standard deviation of the heading-error signal θ over sliding windows of `t_psd = 1.0 s` (20 control cycles at 20 Hz). Reported as the 95th percentile of the per-step values across the eligible portion of the run.

**Units.** Radians (degrees in display).

**Computation.** For each control step `t` with `t > t_psd`, compute `σ_θ(t) = std(θ[t - t_psd : t])`. Aggregate over the run as `M_P7 = percentile_95(σ_θ(t) for eligible t)`. Eligibility excludes (i) emergency mode, (ii) the first `t_psd` seconds of any nominal interval (insufficient history), and (iii) any active stop-signal period. A run with no eligible window produces `M_P7 = undefined`.

**Rationale.** Distinguishes a vehicle whose heading is *bounded but oscillating* (high `σ_θ`, low `M-P4 - M-P5`) from one whose heading is *bounded and stable* (low `σ_θ`). M-P4 and M-P5 alone cannot make this distinction.

**Contributes evidence to.** SR-002 (general behaviour), SR-011 (oscillation detection).

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

**Note.** In enforcement mode, M-S2 should be 0 by design of C-01 (single-rule activation) and SR-010 (multi-rule activation — the joint-envelope assertion guarantees the final command satisfies C-01's envelope even under co-activation with other rules). In monitoring mode, M-S2 reflects what the policy alone would have produced.

**Contributes evidence to.** SR-001 (primary), SR-010 (joint-envelope assertion under multi-rule activation), and crucial for the enforcement-vs-monitoring causal comparison.

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

### M-S5 — Road-edge departure

**Definition.** Whether the vehicle reached the drivable-road edge during the run — the harm proxy for the frontier cage-efficacy study. A per-run boolean recorded as `road_edge_contact`, true iff the maximum absolute lateral offset reached the road half-width. Distinct from M-S2 (which counts *lane*-boundary breaches at `d_max`): M-S5 marks the more severe *road*-edge departure and is the verdict driver of the SC-FRONT-* scenarios.

**Units.** Binary per run (`road_edge_contact`); aggregated as percentage of runs (departure rate) per (scenario, mode).

**Computation.** Per run: `road_edge_contact = (max(abs(ey[t]) for t in run) >= road_half_m)`, with `road_half_m = 0.5 · road_width` (the oval right-lane road edge, ≈ 0.26 m — beyond the 0.1225 m lane edge). Per-(scenario, mode) aggregate: `M_S5 = count(road_edge_contact) / count(runs) * 100`. The companion `max_excursion_m = max(abs(ey[t]))` reported alongside in those scenarios is the realised value of M-S1 (max lateral offset).

**Note — paired enforcement-vs-monitoring contrast.** Reported as the no-cage counterfactual difference, **not** by the global `fraction_pass` aggregation: on a frontier (out-of-ODD) start the monitoring arm (cage observes only) is expected to reach the edge while the enforcement arm should not. The measured cage benefit is `M_S5(monitoring) − M_S5(enforcement)`, computed by `tools/frontier_contrast.py`. This is the H-04 cage-value evidence (cf. D-35).

**Contributes evidence to.** SR-001, SR-005, SR-007, SR-008 (cage containment beyond the ODD).

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

<!--
## Anticipated defense questions

**Q1. M-S2 "should be 0 by design" in enforcement mode — if a metric is constructed to be zero, what does measuring it prove?**
M-S2 = 0 in enforcement is the *claim under test*, not an assumption: it becomes non-zero if C-01 or the SR-010 joint-envelope composition fails, which is exactly what M-S2 exists to catch. Its scientific value is in the *contrast* — M-S2(monitoring) quantifies what the policy alone would have done — so a zero in enforcement beside a non-zero in monitoring is a positive result, not a tautology.

**Q2. Why add M-S5 (road-edge departure) when M-S1 (max lateral offset) already exists — isn't it derivable from M-S1?**
M-S5 is a thresholded boolean on M-S1 (`road_edge_contact = max|ey| ≥ road_half`), but it is conceptually distinct: M-S2 counts *lane*-edge breaches at `d_max`, whereas M-S5 marks the more severe *road*-edge departure used as the harm proxy for the frontier study. It is reported as a paired enforcement-vs-monitoring rate (`frontier_contrast.py`), which a continuous RMSE-style metric cannot express as cleanly; M-S1 is reported alongside as `max_excursion_m`.

**Q3. M-P6 and M-P7 are "undefined" when there are no eligible windows — doesn't an undefined metric break the verdict pipeline?**
Undefined is handled explicitly: when `eligible_steps == 0` (e.g. a run entirely in emergency mode) the SR-009 verdict falls through to scenario semantics rather than coercing a misleading 0 % or 100 %. The eligibility carve-outs (settling window, emergency, stop-signal) are defined so that "undefined" means "this run carries no liveness evidence", not "pass" — which prevents a silent false-pass.

**Q4. The statistical tests carry assumptions (Welch's t assumes approximate normality of the means) — are the sample sizes and distributions adequate?**
The catalogue pre-commits to alternatives: Mann-Whitney U for heavily non-Gaussian distributions, Fisher exact for small-sample binary outcomes, Kolmogorov–Smirnov for distributions. Thresholds are tiered (p < 0.05 for primary comparisons, p < 0.01 for any strong-effect claim) and Cohen's d is always reported, so significance is never claimed on a p-value alone. The run counts (`docs/05`, D-29) are set to keep these tests valid.

**Q5. M-C1 / M-C2 (latency, cage overhead) — are these even measured in simulation, and do they transfer to the physical platform?**
They are measured in simulation as median and 95th-percentile per step and are primarily a *feasibility* argument — the cage is cheap enough to run at the control rate, and at higher rates. Their sim-to-real transfer is exactly one of the gap statements that A5 / Phase 5 is meant to characterise; the simulation figures are a baseline, not a hardware claim.

**Q6. Each metric lists the SRs it "contributes evidence to" — what stops a metric from being gamed (a good number with unsafe behaviour)?**
The metric set is deliberately multi-angle per hazard: H-08 needs *two* metrics — M-P6 for the stall sub-mode and M-S2-in-monitoring for the adversarial-direction sub-mode — because either alone is gameable. Safety is guaranteed by the cage, not by any metric, so a metric exploit cannot produce unsafe runtime behaviour; it can only fail to *detect*, which the negative tests (SC-PERT-03) and the monitoring-mode contrasts are built to surface.

--->

## Change log

See `docs/CHANGELOG.md`.
