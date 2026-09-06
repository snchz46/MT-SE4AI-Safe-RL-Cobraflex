# Chapter 8 — Experimental evaluation

## 8.1 Purpose of the chapter

This chapter occupies the levels of behavioural evaluation of the policy (L4b') and of scenario-based validation (L2'). It is where adaptation A2 is materialised: statistical characterisation replaces classical verification for the learned component, while the cage keeps its deterministic verification from Chapter 6.

The experimental design is presented first — the scenario library, the two operating modes and the verdict aggregation rule — then the results of the reference campaign, and finally the three findings that the campaign produced and that were not in the script. The complete scenario-by-scenario breakdown is collected in Appendix I.

## 8.2 Experimental design

### 8.2.1 The scenario library

The library contains twenty-eight scenarios distributed in four families with different functions. The nominal ones verify basic competence and the absence of false triggers with a clean input; they include a 300 s endurance test whose function is to detect cumulative degradation. The edge ones inject adverse initial conditions inside or at the boundary of the domain: high initial heading, initial lateral offset, compound state, and a co-activation grid whose explicit purpose is to force the simultaneous activation of two or more rules. The perturbed ones apply stressors on the perception channel — glare, low illumination, blur, worn markings, occlusion, an injected false lane and their combinations. And the frontier ones place the vehicle *outside* the domain in order to measure the effectiveness of the cage where the policy is not required to work.

Each scenario declares initial conditions, perturbation, termination criterion, primary metrics and an explicit pass criterion. No run is interpreted without that criterion written in advance.

### 8.2.2 The two modes as a counterfactual

Each scenario is executed in enforcement — the cage corrects — and in monitoring — the cage evaluates the same rules and logs the same activations, but does not modify the command. The comparison between the two, over the same scenario and the same seed, is the central instrument of the chapter: it does not compare two different systems but the same system with and without the envelope, which removes the most obvious confounder. Everything this chapter claims about "the contribution of the cage" rests on that contrast.

### 8.2.3 Aggregation rule and treatment of indeterminacy

A verdict per requirement is composed from the verdicts of its scenarios under two rules declared in advance. The first one is evidence sufficiency: a requirement only receives a verdict if its coverage reaches a minimum number of runs distributed between a nominal family and an adverse one; otherwise it is marked as insufficient evidence, which is not the same as a failure. The second one is a veto rule: only class A requirements can invalidate the global verdict.

One implementation subtlety turned out to be important. An indeterminate per-run verdict — when the criterion of the scenario references a quantity that the log does not capture — is not a failure: it is excluded from the denominator and propagated as insufficient evidence. Collapsing it into a failure, as an early version of the aggregator did, produces "unsatisfied" requirements that are in reality instrumentation gaps. The distinction looks pedantic until one sees that it is exactly what separates a gap from a result: the two requirements that this work closes in a non-trivial way — one satisfied and one not — do so because the instrumentation gap was closed and the measurement could really be taken.

## 8.3 The reference campaign

The reference campaign executes 1,890 runs without errors: twenty-seven scenarios by two modes, with the repetitions that each scenario declares, over the two-dimensional policy selected in Chapter 7. One scenario is excluded by protocol — the *stall* meta-test, closed separately with its own metrology, as explained in §8.6. The cage configuration is identical to that of the previous campaign, so that the contrast between the two is a contrast of policy, not of instrument.

### 8.3.1 Global verdict

The literal global verdict is `NOT SATISFIED`, composed as Table 8.1 shows, and it is blocked by two class A requirements — heading stability and predictive time to lane departure — exclusively through a single scenario and a single clause. It is worth breaking it down, because the difference between "the system is not safe" and what really happens is the whole difference of the chapter:

| | Count | Requirements |
| --- | :-: | --- |
| Class A satisfied | 8 / 10 | SR-001, 004, 005, 007, 008, 012, 013, 014 |
| Class A with a **literal** failure | 2 / 10 | SR-002, SR-003 — through one scenario and one clause only; satisfied on their own criterion |
| Class B with a **literal** failure | 1 / 4 | SR-011 — the same inherited clause; satisfied on its own metric (3.77° < 5°) |
| Class B **not satisfied** | 1 / 4 | SR-010 — co-activation grid; the one negative verdict of the work (§8.6) |
| Class B closed out of band | 2 / 4 | SR-006 and SR-009 — satisfied on their own metrology (§8.6.1) |

*Table 8.1 — Composition of the global verdict of the reference campaign.*

In the blocking scenario, the only clause violated over its thirty enforcement runs is the one on heading recovery time (Table 8.2). The safety clauses are not touched in any of them:

| Quantity | Observed | Limit |
| --- | ---: | ---: |
| Emergency stops | 0 | — |
| Maximum lateral excursion | 0.043 m | 0.16 m |
| Maximum heading error | 14.2° | 25° |
| Maximum heading standard deviation | 3.77° | 5° |

*Table 8.2 — The scenario that blocks the verdict: what is measured and what is violated.*

The two requirements are therefore satisfied on their own documented criterion: the heading one requires that the error does not exceed 25°, and the measured maximum is 14.2°; the predictive one requires a time margin that is never compromised, with the vehicle at a quarter of the lateral limit. The 2.0 s recovery clause is an inherited performance requirement from an earlier library, not the safety predicate of either of them.

The verdict is recorded as literal, with the reconciliation annotated, and not reformulated as satisfied. This is a deliberate decision: a framework whose value consists in leaving no claim without evidence would lose its meaning if it rewrote the verdict every time it turned out to be uncomfortable. What is done instead is to explain exactly what is violated and what is not.

### 8.3.2 The clause, audited instead of excused

The fact that the same clause blocked the verdict in two successive campaigns is a reason to suspect the clause, and not only the system. It was audited, and it had a real defect: its recovery band was a *fixed* value calibrated on an earlier controller and an earlier geometry, so that — given that the heading error oscillates around zero with an amplitude that depends on the controller and on the layout — requiring several consecutive samples inside that band measured the ripple, not the recovery. Applied to runs with no perturbation at all, the metric reported that 100 % of them "never recover".

The correction references the band to the steady-state envelope of each run, and it was applied once, with its acceptance criterion fixed in advance: the false positives on unperturbed scenarios must disappear. They disappear. Two conclusions, both relevant. The first one: re-scored with the corrected metric, this campaign still fails the scenario, while the previous policy would pass it — that is, the correction favours the arm that the thesis does not present, and therefore it cannot be read as an adjustment made for convenience. The second one: the failure is not a measurement artefact. The recovery of this policy really does *ring* — 13.6° → 1.4° → 5.9°, settling towards 2.5 s — and it does so on a straight section, which is the closed-loop signature of the jerky command that §8.5 documents. It is a performance property, not a safety one, and the reconciliation rests on firmer ground than "the clause is inherited".

The 2.0 s limit was deliberately left intact: the audit corrects a measurement, it does not lower a bar.

## 8.4 The safety invariant

This is the central result of the work. Counting the contacts with the road edge and separating the runs by whether their initial condition is inside or outside the operational domain:

| | Inside the ODD | Outside the ODD |
| --- | ---: | ---: |
| **Enforcement** (cage active) | **0** | 56 |
| Monitoring (cage inactive) | 60 | 217 |

*Table 8.3 — Contacts with the road edge by mode and by domain membership.*

**Inside the operational domain, with the cage active, not a single contact with the road edge is recorded**; the policy on its own commits sixty, and the cage removes all of them at the cost of 406 controlled stops. Outside the domain — where the system is not required to work — the improvement over the previous policy is large: 56 contacts against 117, concentrated precisely where the boundary stress is hardest.

<img src="../figures/fig_8_2_safety_invariant.png" alt="Figure 8.1 — Road edge contacts by mode and by domain membership." width="560"/>

*Figure 8.1 — Contacts with the road edge by mode and by membership of the operational domain, with the earlier campaigns overlaid. The "inside the ODD, enforcement" block is zero in all of them; the difference between policies is outside the domain.*

### 8.4.1 Latent inside, active where perception degrades

In the clean nominal scenario the cage is latent: the policy drives 5.32 laps with 8.6 mm mean lateral error, zero emergencies and zero safety interventions; only the rate limiter acts. But the contrast between modes, scenario by scenario (Table 8.4), shows where it stops being latent:

| Scenario | Enforcement | Monitoring |
| --- | ---: | ---: |
| Compound state | 30/30 | 0/30 |
| Frontier (lateral approach) | 25/25 | 0/25 |
| Worn markings | 25/25 | 0/25 |
| **Degraded markings + glare** | **40/40** | **20/40** |
| 300 s endurance | 25/25 | 8/25 |

*Table 8.4 — Scenarios that the cage rescues: runs passed by mode.*

This is the empirical content of the central claim: the cage removes failures that the policy commits on its own, and it does so through the intended mechanism — the controlled stop under unreliable perception — exactly in the scenarios where the visual channel degrades. The cage does not improve the driving; it bounds the consequence of the driving failing.

<img src="../figures/fig_8_1_campaign_pass_fraction.png" alt="Figure 8.2 — Pass fraction by scenario and mode." width="600"/>

*Figure 8.2 — Fraction of runs passed per scenario, enforcement against monitoring, sorted by the contribution of the cage. The scenarios in the upper part are those where the envelope makes the difference between completing and not completing.*

## 8.5 The uncomfortable finding: the rate limiter holds the lane

The 300 s endurance test produces an inversion that the verdict tables do not show, and that turned out to be the most informative finding of the campaign. With the cage active, the twenty-five runs complete without appreciable excursions. With the cage inactive, seventeen out of twenty-five end off the road — a rate that none of the earlier policies, including the worst ones, exhibited.

Four measurements bound the cause.

**It is not accumulated drift: it is geometrically deterministic.** The seventeen departures occur in exactly two arcs of the circuit — the two tightest apexes — and in the last seconds before them the jerk of the command is *smaller* than the average of the run. It is not oscillation: it is a sustained and confident oversteer.

**The only thing that differs between modes is the rate limiter** (Table 8.5). Same policy, same layout, same speed at the apex:

| At the tightest apex | Enforcement | Monitoring |
| --- | ---: | ---: |
| Raw steering command (max.) | 1.00 | 1.00 |
| **Applied** command (max.) | **0.84** | 1.00 |
| Applied variation per cycle | ≤ 0.15 | up to 2.0 |
| Maximum lateral error | 36 mm | 145 mm → off the road |

*Table 8.5 — Enforcement and monitoring at the apex: the only difference is the limiter.*

**No safety rule intervenes.** Over the twenty-five enforcement runs the intervention log is exclusively from the rate limiter, with zero activations of the lateral limit, heading, predictive and emergency rules. The rule that keeps the vehicle in the lane at those apexes is, formally, a class B smoothness rule.

**The raw command of this policy is roughly twice as abrupt** as that of its predecessors and it saturates the limiter in 77.5 % of the steps. Speed does not explain it: the previous policy drives 7 % slower and survives; and the comparison between modes keeps the speed constant within the same policy.

**Interpretation, with its limits declared.** The natural reading is co-adaptation: the policy was trained with the cage in the actuation chain, where the limiter integrates whatever it commands; under that closed loop an almost all-or-nothing command is not penalised, and the policy emits it. With the cage active, the pair drives better than any other configuration in this work; without it, the same command leaves the lane roughly once every three laps. The cage is not only filtering this policy: it has shaped what the policy learned to emit.

Two honest limits on that reading. The dependency is measured; its origin is inferred, and proving the causality would require an ablation — retraining with the limiter out of the loop — that has not been executed. And exposure matters: the short nominal scenario passes 50/50 in monitoring, so a brief nominal evaluation cannot detect this property; only the endurance test reveals it.

There are three consequences for reading the rest of the work. "The cage is latent inside the domain" is still true of the safety rules, but it must not be read as "the cage is idle": in this policy the latency of the safety rules is *produced* by the limiter acting upstream. The classification of the smoothness requirement as class B underestimates what that rule is doing. And on the physical platform, where the actuator dynamics are not the simulated limiter, a policy so coupled to one concrete parameter of the envelope constitutes a transfer risk, which is declared explicitly in Chapter 12.

## 8.6 The negative verdict: rule composition

Of the fourteen requirements, one is closed as not satisfied, and it is reported as such instead of being reconciled.

Its criterion requires that, when two or more rules activate in the same cycle, the resulting command satisfies the safe envelope of all of them. The co-activation grid — whose initial conditions are injected explicitly in order to force that case — shows that it is not met: of the 85 grid points located inside the domain, 16 produce violations of the lateral margin. On the previous policy there were 30 out of 85.

The breakdown by rule combination localises the problem with useful precision: the violations concentrate in the co-activation of the lateral limit and heading rules — 15 out of 20 runs fail, with 11 violations — and in the triple that includes them; they are milder when the combination is lateral with predictive (4 violations), and they disappear completely where there is no conflict between lateral and heading correction: the combination of speed with rate limiter produces neither a violation nor a failure.

Training a better policy halves the finding but does not change its nature. That is the substantive conclusion: arbitration under simultaneous activation is a design property of the cage, not a defect of the policy, and the evidence for saying so is that two very different policies produce the same attenuated pattern. It is exactly the hazard that the register anticipated when it included a hazard for the mitigation mechanism itself, and it is carried as declared future work.

The requirement is class B and therefore does not veto the global verdict; no class A safety predicate is involved. The fact that the matrix contains a negative verdict, next to the claim of zero contacts inside the domain, is what gives credit to the second one.

### 8.6.1 The two requirements closed out of band

Two requirements are closed on their own metric instead of by scenario aggregation, and in both cases the reason is documented.

The one on actuation smoothness is verified directly over the trace of the committed command: in enforcement, 840 out of 840 runs respect the per-cycle limit; in monitoring only 263 out of 945. It is, incidentally, the most direct measure of the value of the limiter.

The one on *liveness* is closed on its own metrology. Its scenario — a two-arm meta-test that injects an adverse incentive to stop — was excluded from the campaign because it is independent of the policy and had already been closed separately, with three measured parts: the nominal policy never stops; a deliberate attempt to force it to stop does not succeed, which is positive evidence of the training mitigation; and the detector does trigger on a real stop injected by script. A mitigation that works, a pathology that is resisted, and a healthy metric.

## 8.7 Contrast with the perfect perception arm

The control arm — same cage, same scenarios, but with the state obtained from ground truth instead of from the camera — closes with a global verdict of satisfied and provides a finding that gives meaning to everything above: with perfect perception, the cage is completely latent inside the domain; its boundary violation metric is zero in both modes and the contrast between enforcement and monitoring is null.

The joint reading is the empirical contribution of the work: the value of the cage is a function of the quality of the perception. Where perception is perfect, the envelope has nothing to correct and its value only appears outside the domain. Where perception is a network that learns from degraded pixels, the envelope goes from latent to operative and removes measurable failures. Without the control arm, the result of the camera arm would be ambiguous: it would not be known whether the cage contributes because the problem is hard or because the policy is bad.

## 8.8 Threats to validity

- **A single seed in the verdict campaign.** The reference campaign uses one seed; the variability between seeds is characterised separately (§7.4) and shows that the behaviour is not homogeneous. The generalisation of the verdict to other seeds is not established.
- **A single circuit.** All the reference results come from one geometry. The second geometry of the control arm reinforces the plausibility argument, it does not close it.
- **Laps are not comparable between layouts**, and the lateral error is not comparable between observation modalities. The work avoids those comparisons and flags them where they might be induced.
- **Simulation, not reality.** No result in this chapter is evidence about the physical platform. Chapter 9 characterises what is known and what is not about the jump.
- **The origin of the dependency on the limiter is inferred**, not proved, and the ablation that would prove it has not been executed.
- **One operational incident** during the campaign — two processes writing concurrently to the same directory — affected 222 runs. They were quarantined and re-executed under a serial driver with a lock; the final aggregate covers the 1,890 cells with no errors. It is recorded here because the integrity of the evidence is also a claim that must be supported with evidence.

## 8.9 Synthesis

The reference campaign leaves four results. Inside the domain, with the cage active, zero contacts with the edge, against sixty that the policy commits without it. The cage is latent in its safety rules inside the domain and becomes operative exactly where perception degrades. The rate limiter does lane-keeping work that its classification does not reflect, and that dependency is a declared transfer risk. And one requirement is not satisfied — the composition of rules under co-activation — it is reported as such and carried as future work.

Chapter 9 addresses how much of all this can be expected to survive the jump to the physical platform.
