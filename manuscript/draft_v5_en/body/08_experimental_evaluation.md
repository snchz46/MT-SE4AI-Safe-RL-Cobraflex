# Chapter 8 — Experimental evaluation

## 8.1 Purpose of the chapter

This chapter covers two levels: behavioural evaluation of the policy (L4b') and scenario-based validation (L2'). It is where adaptation A2 becomes concrete. For the learned component, statistical characterisation takes the place of classical verification, while the cage keeps the deterministic verification from Chapter 6.

The chapter first presents the experimental design: the scenario library, the two operating modes and the rule for combining verdicts. Then it gives the results of the reference campaign, and finally the three findings that came out of the campaign without being planned. The full scenario-by-scenario results are in Appendix I.

## 8.2 Experimental design

### 8.2.1 The scenario library

The library has twenty-eight scenarios in four families, each with a different purpose. The nominal scenarios check basic competence and that nothing triggers without reason on a clean input. They include a 300 s endurance test meant to catch degradation that builds up over time. The edge scenarios add difficult starting conditions inside or at the boundary of the domain: a large initial heading error, an initial lateral offset, a compound state, and a co-activation grid whose explicit purpose is to make two or more rules fire at the same time. The perturbed scenarios add stressors to the perception channel: glare, low light, blur, worn markings, occlusion, an injected false lane, and combinations of these. The frontier scenarios put the vehicle *outside* the domain to measure how well the cage works where the policy is not required to work.

Each scenario states its starting conditions, perturbation, end condition, main metrics and an explicit pass criterion. No run is interpreted unless that criterion was written beforehand.

### 8.2.2 The two modes as a counterfactual

Each scenario runs in enforcement mode, where the cage corrects the command, and in monitoring mode, where the cage checks the same rules and logs the same activations but does not change the command. Comparing the two, on the same scenario and the same seed, is the main tool of this chapter. It does not compare two different systems, but the same system with and without the envelope, which removes the most obvious confounding factor. Everything this chapter says about "what the cage contributes" is based on this comparison.

### 8.2.3 How verdicts are combined, and what to do with indeterminate results

The verdict for a requirement is built from the verdicts of its scenarios, using two rules defined in advance. The first is about having enough evidence. A requirement only gets a verdict if it has at least a minimum number of runs, spread across a nominal family and an adverse one. Otherwise it is marked as insufficient evidence, which is not the same as a failure. The second is a veto rule: only class A requirements can make the global verdict fail.

One implementation detail turned out to be important. A per-run verdict can be indeterminate when the scenario's criterion uses a quantity that the log does not record; that is not a failure, it is removed from the denominator and passed on as insufficient evidence. An early version of the aggregator counted it as a failure, producing "unsatisfied" requirements that were really gaps in the instrumentation. It sounds minor, but it is exactly what separates a gap from a result: the two requirements this work closes in a non-trivial way, one satisfied and one not, could only be closed after the gap was fixed and the measurement really taken.

## 8.3 The reference campaign

The reference campaign runs 1,890 runs with no errors: twenty-seven scenarios in two modes, with the number of repetitions each scenario defines, using the two-dimensional policy chosen in Chapter 7. One scenario is left out by protocol: the *stall* meta-test, which was closed separately with its own measurements, as explained in §8.6. The cage configuration is the same as in the previous campaign, so any difference between the two comes from the policy and not from the measuring tool.

### 8.3.1 Global verdict

The literal global verdict is `NOT SATISFIED`, built as shown in Table 8.1. It is blocked by two class A requirements, heading stability and predictive time to lane departure, and only through one scenario and one clause. It is worth examining in detail, because the difference between "the system is not safe" and what actually happens is the central point of the chapter:

| | Count | Requirements |
| --- | :-: | --- |
| Class A satisfied | 8 / 10 | SR-001, 004, 005, 007, 008, 012, 013, 014 |
| Class A with a **literal** failure | 2 / 10 | SR-002, SR-003 — through one scenario and one clause only; satisfied on their own criterion |
| Class B with a **literal** failure | 1 / 4 | SR-011 — the same inherited clause; satisfied on its own metric (3.77° < 5°) |
| Class B **not satisfied** | 1 / 4 | SR-010 — co-activation grid; the only negative verdict of the work (§8.6) |
| Class B closed out of band | 2 / 4 | SR-006 and SR-009 — satisfied on their own measurements (§8.6.1) |

*Table 8.1 — How the global verdict of the reference campaign is built.*

In the blocking scenario, the only clause broken across its thirty enforcement runs is the one on heading recovery time (Table 8.2). None of the safety clauses are broken in any of them:

| Quantity | Observed | Limit |
| --- | ---: | ---: |
| Emergency stops | 0 | — |
| Maximum lateral excursion | 0.043 m | 0.16 m |
| Maximum heading error | 14.2° | 25° |
| Maximum heading standard deviation | 3.77° | 5° |

*Table 8.2 — The scenario that blocks the verdict: what is measured and what is broken.*

So both requirements are met on their own documented criterion. The heading requirement says the error must not go above 25°, and the measured maximum is 14.2°. The predictive requirement asks for a time margin that is never lost, and the vehicle stays at a quarter of the lateral limit. The 2.0 s recovery clause is a performance requirement inherited from an older library. It is not the safety condition of either requirement.

The verdict is recorded as literal, with the explanation noted next to it, and it is not rewritten as satisfied. This was a conscious decision. A framework whose value is that no claim goes without evidence would lose its meaning if it rewrote the verdict every time it was uncomfortable. Instead, the text explains exactly what is broken and what is not.

### 8.3.2 The clause, audited instead of excused

The same clause blocked the verdict in two campaigns in a row. That is a reason to suspect the clause, not only the system. It was audited, and it had a real defect. Its recovery band was a *fixed* value, calibrated on an older controller and an older layout. Since the heading error oscillates around zero with an amplitude that depends on the controller and the layout, asking for several consecutive samples inside that band measured the ripple, not the recovery. When applied to runs with no perturbation at all, the metric said that 100 % of them "never recover".

The fix sets the band relative to the steady-state envelope of each run. It was applied once, with its acceptance criterion fixed beforehand: the false positives on unperturbed scenarios had to go away, and they did. Two conclusions follow. First, re-scoring this campaign with the corrected metric still fails the scenario, while the previous policy would pass. The fix therefore helps the option the thesis does *not* present, and cannot be seen as a convenient adjustment. Second, the failure is not a measurement error. This policy's recovery really does *ring* (13.6° → 1.4° → 5.9°, settling towards 2.5 s), and it does so on a straight section: that is what the jerky command documented in §8.5 looks like in closed loop. It is a performance property, not a safety one, and the explanation now rests on firmer ground than "the clause is inherited".

The 2.0 s limit was left unchanged on purpose: the audit fixes a measurement, it does not lower the bar.

## 8.4 The safety invariant

This is the main result of the work. It counts contacts with the road edge and splits the runs by whether their starting condition is inside or outside the operational domain:

| | Inside the ODD (555 runs/mode) | Outside the ODD (390 runs/mode) |
| --- | ---: | ---: |
| **Enforcement** (cage active) | **0** | 56 |
| Monitoring (cage inactive) | 60 | 217 |

*Table 8.3 — Contacts with the road edge by mode and by whether the run starts inside the domain. The 945 runs of each mode split into 555 inside the domain (nominal and perturbed families) and 390 outside (edge and frontier families).*

**Inside the operational domain, with the cage active, there is not a single contact with the road edge.** The policy alone makes sixty, and the cage removes all of them at the cost of 406 controlled stops. Outside the domain, where the system is not required to work, the improvement over the previous policy is large: 56 contacts against 117, concentrated exactly where the boundary conditions are hardest.

<img src="../figures/fig_8_1_safety_invariant.png" alt="Figure 8.1 — Road edge contacts by mode and by domain membership." width="560"/>

*Figure 8.1 — Contacts with the road edge by mode and by whether the run starts inside the operational domain, for the reference campaign and the two earlier ones, `margin022` and `GE4-V2` (Table 7.1). The "inside the ODD, enforcement" block is zero in all three. The differences between policies are outside the domain.*

### 8.4.1 Latent inside, active where perception gets worse

In the clean nominal scenario the cage is latent, with the figures §7.5.2 already gave when the checkpoint was chosen: only the rate limiter acts. But comparing the modes scenario by scenario (Table 8.4) shows where the cage stops being latent:

| Scenario | Enforcement | Monitoring |
| --- | ---: | ---: |
| Compound state | 30/30 | 0/30 |
| Frontier (lateral approach) | 25/25 | 0/25 |
| Worn markings | 25/25 | 0/25 |
| **Degraded markings + glare** | **40/40** | **20/40** |
| 300 s endurance | 25/25 | 8/25 |

*Table 8.4 — Scenarios the cage rescues: runs passed in each mode.*

This is the evidence behind the main claim. The cage removes failures that the policy makes on its own, and it does so through the intended mechanism, the controlled stop when perception is unreliable, in exactly the scenarios where the visual channel degrades. The cage does not make the driving better. It limits what happens when the driving fails.

<img src="../figures/fig_8_2_campaign_pass_fraction.png" alt="Figure 8.2 — Pass fraction by scenario and mode." width="600"/>

*Figure 8.2 — Share of runs passed per scenario in the reference campaign (`2-D PPO 550k`, Table 7.1; scenario IDs without the `SC-` prefix), enforcement against monitoring, sorted by how much the cage contributes. In the scenarios at the top, the envelope makes the difference between finishing and not finishing.*

## 8.5 The uncomfortable finding: the rate limiter keeps the car in the lane

The 300 s endurance test shows a reversal that the verdict tables hide, and it turned out to be the most informative finding of the campaign. With the cage active, all twenty-five runs finish without any real excursion. With the cage inactive, seventeen out of twenty-five end off the road. None of the earlier policies, not even the worst ones, did this.

Four measurements narrow down the cause.

**It is not drift building up over time. It happens at fixed places.** The seventeen departures happen at exactly two points of the circuit, the two tightest apexes. In the last seconds before them, the jerk of the command is *lower* than the run's average. It is not oscillation. It is steady, confident oversteering.

**The only difference between the modes is the rate limiter** (Table 8.5). Same policy, same layout, same speed at the apex:

| At the tightest apex | Enforcement | Monitoring |
| --- | ---: | ---: |
| Raw steering command (max.) | 1.00 | 1.00 |
| **Applied** command (max.) | **0.84** | 1.00 |
| Applied change per cycle | ≤ 0.15 | up to 2.0 |
| Maximum lateral error | 36 mm | 145 mm → off the road |

*Table 8.5 — Enforcement and monitoring at the apex: the only difference is the limiter.*

<img src="../figures/auto/fig_8_3_c06_load_bearing.png" alt="Figure 8.3 — The endurance scenario with and without the cage acting." width="620"/>

*Figure 8.3 — The endurance scenario (`SC-NOM-03`, 300 s), all fifty runs of the reference campaign. Left: the largest lateral excursion of each run. The crosses are the runs that ended off the road, where the value is the point at which the run was cut short and not how far the vehicle would have gone, so the two marker types are not the same quantity. Right: the intervention ledger. With the cage acting it contains the rate limiter and nothing else — 58,124 cycles of C-06 against zero activations of C-01, C-02, C-03 and C-05 — while the same command stream, merely observed, applies changes of up to 2.0 per cycle against the 0.15 bound. This is the evidence behind the claim that the safety rules are latent *because* the limiter acts first.*

**No safety rule steps in** (Figure 8.3). In the twenty-five enforcement runs, the intervention log contains only the rate limiter, with zero activations of the lateral limit, heading, predictive and emergency rules. The rule that keeps the vehicle in the lane at those apexes is, on paper, a class B smoothness rule.

**This policy's raw command is about twice as abrupt** as that of the earlier policies, and it saturates the limiter in 77.5 % of the steps. Speed does not explain it. The previous policy drives 7 % slower and stays on the road, and in the comparison between modes the speed is the same because it is the same policy.

**Interpretation, and its limits.** The most likely explanation is co-adaptation. The policy was trained with the cage in the actuation chain, where the limiter smooths whatever the policy commands. In that closed loop, an almost all-or-nothing command is not penalised, so the policy produces it. With the cage active, the pair drives better than any other configuration in this work. Without it, the same command leaves the lane about once every three laps. The cage is not only filtering this policy. It has shaped what the policy learned to output.

There are two limits to this explanation. The dependency is measured, but its origin is inferred. Proving the cause would need an ablation (retraining with the limiter out of the loop), and that has not been done. Exposure also matters. The short nominal scenario passes 50/50 in monitoring, so a short nominal evaluation cannot detect this property. Only the endurance test shows it.

This has three consequences for reading the rest of the work. "The cage is latent inside the domain" is still true for the safety rules, but it must not be read as "the cage does nothing": for this policy, the safety rules are latent *because* the limiter acts first. The class B label of the smoothness requirement underestimates what that rule is doing. And on the physical platform, where the actuator dynamics are not the simulated limiter, a policy so tied to one specific parameter of the envelope is a transfer risk. Chapter 12 states this explicitly.

## 8.6 The negative verdict: combining rules

Of the fourteen requirements, one is closed as not satisfied, and it is reported that way instead of being explained away.

Its criterion says that when two or more rules fire in the same cycle, the resulting command must stay within the safe envelope of all of them. The co-activation grid, whose starting conditions are set on purpose to force this case, shows that this does not hold. Of the 85 grid points inside the domain, 16 break the lateral margin. With the previous policy it was 30 out of 85.

Looking at which rules fire together shows the problem clearly. The violations are concentrated where the lateral limit and heading rules fire together (15 out of 20 runs fail, with 11 violations) and in the triple that includes them. They are milder when the lateral rule fires with the predictive rule (4 violations). They disappear completely where lateral and heading corrections do not conflict: speed together with the rate limiter produces no violation and no failure.

Training a better policy cuts the problem in half, but it does not change what kind of problem it is. That is the main conclusion. How the cage arbitrates when rules fire together is a design property of the cage, not a defect of the policy. The evidence is that two very different policies show the same pattern, only weaker. This is exactly the hazard the register predicted when it included a hazard for the mitigation mechanism itself, and it is kept as stated future work.

The requirement is class B, so it does not block the global verdict, and no class A safety condition is involved. Having a negative verdict in the matrix, next to the claim of zero contacts inside the domain, is what makes that claim believable.

### 8.6.1 The two requirements closed out of band

Two requirements are closed on their own metric instead of through scenario results. In both cases the reason is documented.

The actuation smoothness requirement is checked directly on the trace of the command that was actually applied, counting only the cycles that the emergency stop does not override. In enforcement, the 840 runs that have such cycles all stay within the per-cycle limit; the remaining 105 end in emergency and contribute no sample. In monitoring, where the cage overrides nothing and all 945 runs score, only 263 stay within it. This is also the most direct measure of what the limiter is worth.

The *liveness* requirement is closed on its own measurements. Its scenario, a two-arm meta-test that adds an incentive to stop, was left out of the campaign because it does not depend on the policy and had already been closed separately, with three measured parts. The nominal policy never stops. A deliberate attempt to make it stop does not work, which is positive evidence that the training mitigation works. And the detector does fire on a real stop injected by a script. So: a mitigation that works, a failure mode that is resisted, and a metric that works.

## 8.7 Comparison with the perfect perception arm

The control arm uses the same cage and the same scenarios, but takes the state from ground truth instead of the camera. It closes with a global verdict of satisfied, and gives a finding that puts everything above into context: with perfect perception the cage is completely latent inside the domain, with its boundary violation metric at zero in both modes and no difference between enforcement and monitoring.

Read together, the two arms give the empirical contribution of the work: how much the cage is worth depends on how good perception is. With perfect perception it has nothing to correct and its value only shows outside the domain; with a network learning from degraded pixels it goes from latent to active and removes measurable failures. Without the control arm there would be no way to tell whether the cage helps because the problem is hard or because the policy is bad.

## 8.8 Threats to validity

- **One seed in the verdict campaign.** The reference campaign uses one seed. Variation between seeds is studied separately (§7.4) and shows that behaviour is not the same across seeds. Whether the verdict holds for other seeds is not established.
- **One circuit.** All reference results come from one layout. The second layout of the control arm makes the argument more plausible, but it does not settle it.
- **Laps cannot be compared between layouts**, and lateral error cannot be compared between observation types. The work avoids these comparisons and points them out where a reader might be tempted to make them.
- **Simulation, not reality.** No result in this chapter is evidence about the physical platform. Chapter 9 describes what is known and what is not about that step.
- **The origin of the dependency on the limiter is inferred**, not proved, and the ablation that would prove it has not been run.
- **One operational incident** during the campaign affected 222 runs: two processes wrote to the same directory at the same time. Those runs were set aside and run again under a serial driver with a lock, and the final results cover all 1,890 cells with no errors. It is recorded here because the integrity of the evidence is also a claim that needs evidence.

## 8.9 Summary

The reference campaign gives four results. Inside the domain, with the cage active, there are zero contacts with the road edge, against sixty that the policy makes without it. The cage's safety rules are latent inside the domain and become active exactly where perception gets worse. The rate limiter does lane-keeping work that its classification does not reflect, and this dependency is a stated transfer risk. And one requirement, rule composition under co-activation, is not satisfied. It is reported as such and kept as future work.

Chapter 9 looks at how much of this can be expected to survive the move to the physical platform.
