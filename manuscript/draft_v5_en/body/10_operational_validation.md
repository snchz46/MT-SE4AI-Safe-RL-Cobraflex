# Chapter 10 — Operational validation

## 10.1 From results to a validation statement

The earlier chapters produce measurements. This chapter turns them into a validation statement that includes its own limits. It is the first half of adaptation A5 in practice: the conclusion is no longer "the system is safe" but a bounded claim about which requirements are met, in which domain, with what evidence, and with which residual risks stated.

## 10.2 The evidence

The statement is based on three sets of evidence. All of them have version-controlled artefacts, and every run records its reproducibility metadata: code revision, cage configuration identifier, checkpoint identifier, seed and timestamp.

The perfect perception arm gives 1,260 runs with a global verdict of satisfied. It works as a control: it shows what happens when perception is not a problem. The camera arm gives the scenario campaigns on a policy that learned from pixels, ending with the reference campaign of 1,890 runs without errors that supports the verdict of this chapter. The study of variation between seeds shows that behaviour is not the same across repeated runs of the training procedure.

**Physical evidence exists, but it comes from bring-up and is not verdict evidence.** The chain has run on the real vehicle and it has driven 18.05 m of the circuit in one segment without triggering any safety rule (Chapter 9). But that was a bring-up run. No physical run has been done under the scenario library protocol, in enforcement mode, and with the perception contract used to score the campaigns. For that reason the physical column of the table below is marked not executed. This is different from, and more precise than, saying there is no data: having driven is not the same as having scored, and filling the column with measurements taken outside the protocol would be exactly the kind of claim the framework is meant to prevent.

## 10.3 Final verdict table

| Requirement | Class | Control arm | **Camera arm (reference campaign)** | Physical *(out of scope — §12.4 T2)* |
| --- | :-: | --- | --- | --- |
| SR-001 lateral deviation | A | Satisfied | Satisfied | not executed |
| SR-002 heading stability | A | Satisfied | Literal: fail (recovery clause); own criterion: satisfied | not executed |
| SR-003 predictive time to departure | A | Satisfied | Literal: fail (same clause); own criterion: satisfied | not executed |
| SR-004 speed ceiling | A | Satisfied | Satisfied (rule not activated in the campaign; see §10.4b and §10.4f) | not executed |
| SR-005 emergency stop | A | Satisfied | Satisfied | not executed |
| SR-006 actuation smoothness | B | Satisfied (own metric) | Satisfied (840/840 in enforcement) | not executed |
| SR-007 state validity | A | Satisfied | Satisfied | not executed |
| SR-008 external stop | A | Satisfied | Satisfied | not executed |
| SR-009 *liveness* | B | Documented abstention | Satisfied (own measurements) | not executed |
| SR-010 rule composition | B | Documented abstention | Not satisfied — finding, does not block | not executed |
| SR-011 heading variance | B | Satisfied | Satisfied on its own metric (3.77° < 5°) | not executed |
| SR-012 following under a degraded camera | A | n/a | Satisfied | not executed |
| SR-013 safe perception degradation | A | n/a | Satisfied | not executed |
| SR-014 estimator plausibility | A | n/a | Satisfied | not executed |

*Table 10.1 — Final verdicts per requirement. The physical column is not scored in this work: no run on hardware was done under the scenario protocol, and all of them were done in monitoring mode (§10.4e). It is marked "not executed" and not "pending", so as not to suggest a measurement in progress.*

<img src="../figures/fig_10_1_traceability_case_sr001.png" alt="Figure 10.1 — The traceability chain instantiated end to end." width="520"/>

*Figure 10.1 — One row of Table 10.1 followed backwards to the evidence behind it. The core commitment of the work, `Hazard → Requirement → Rule → Scenario → Metric → Evidence → Verdict`, shown for the most important requirement. Every link is an identifier in a versioned artefact, and `check_traceability.py` blocks the review gate if an orphan appears in either direction. This is how a cell of the table becomes auditable. The evidence is the reference campaign (`campaign_2d_ppo550k`, `2-D PPO 550k`; Table 7.1).*

Looking at it in groups: thirteen of the fourteen requirements are satisfied on their documented criterion. One is not satisfied. It is class B, does not block the verdict, and is reported as it is, without being explained away. None is left without a verdict, left out, or pending in the simulation column. The coverage criterion from the framework evaluation, which asked for a verdict on 100 % of the requirements even if the verdict was uncomfortable, is met, and it is met including the uncomfortable verdict.

Two cells need a comment. The two requirements with a literal failure keep that failure in the record, next to the explanation. They are not rewritten. And the speed ceiling is marked satisfied with an important condition, explained in the statement below: it is satisfied without ever having been tested.

## 10.4 Bounded validation statement

> **Statement.** Within the specified operational domain, on a single circuit in simulation, with the two-dimensional camera policy chosen by closed-loop evaluation and with the cage configuration identified by its *hash*, the system meets thirteen of its fourteen safety requirements on their documented criterion. The literal global verdict of the campaign is `NOT SATISFIED`, and this is caused entirely by one performance clause (heading recovery time) in one scenario, without any class A safety condition being broken.
>
> **Inside the operational domain and with the cage active, there is no contact with the road edge** over 945 enforcement runs. The same policy without the cage makes sixty. The requirement that is not met is the one on consistent rule composition when rules fire at the same time. It is class B, was measured on two different policies, was cut in half by better training, and stays the same in kind. It is stated as a design limitation of the envelope and as future work.

**Explicit limits of this statement.** They are listed here, as part of the statement, and not in a separate section, because each one limits a specific claim made above.

**(a) Scope.** The statement is valid in simulation, on one circuit, and with one seed in the verdict campaign. Variation between seeds is studied separately and is not uniform.

**(b) What was not tested.** The cage's speed ceiling did not fire once in the 1,890 runs, because the policy's operating speed stays below the lower limit of that envelope. The requirement is satisfied trivially, and its rule has never been tested from above. This is a limitation of the operating point, not of the specification, and it is stated so that it is not read as evidence of robustness.

**(c) The measured dependency.** For this policy, staying in the lane on the tightest curves depends on the rate limiter. The dependency is measured, and its origin is inferred.

**(d) Transfer.** Physical evidence exists but is not scored, and no claim in this statement applies to the real platform. What can be claimed, and is claimed in Chapter 9 and not here, is that the policy behind this verdict does not transfer to the real vehicle, and that the one that does is a later retraining. The thing validated in this statement and the thing that drives on hardware are not the same.

**(e) What the hardware has not tested at all, which is the biggest limit of this work.** All physical runs were done in monitoring mode. In that mode the cage checks, publishes and logs its rules but does not change the action, so the safe action is identical to the policy's raw action in every logged cycle. As a result, the envelope has never acted on the real vehicle. What the physical step measures is what the cage *would have said*, plus the availability cost of its emergency latch. What it does not measure is how the cage changes the trajectory of a physical vehicle, which is exactly the property this statement certifies in simulation. This is a limit of scope and not a negative result: there is no physical evidence against the envelope, no physical evidence for it, and there will be none until a scored run is done in enforcement mode.

**(f) One rule that the hardware did test.** The speed ceiling is marked satisfied here without having fired once, and Chapter 9 adds two points measured in Phase 5 that limit this cell without re-scoring it. First, in the deployed physical configuration the rule cannot fire on commanded motion, because its curve ceiling (0.25 m/s) is above the deployed cap (0.22 m/s). What was a coverage gap in simulation is, in the tightest curve of the real circuit, a rule that does not protect a case that really exists. Second, and worse: the rule did fire, 58 and 40 cycles in the two caged runs that passed the audit, and 100 % of the time because of velocity errors from the pose sensor (0.25–1.30 m/s reported, which the vehicle cannot reach under its own power). In one of those runs, the false activations blocked the reset path of the very rule they had triggered. For this statement, that means one specific and limited thing: the verdict on this requirement depends entirely on the fact that its trigger condition was never reached in simulation, and not on evidence that the rule acts correctly when it is reached. It is the requirement with the weakest support in the table, and it is marked as such.

## 10.5 From the statement to the methodological thesis

The statement above is what the framework promised to produce: not a yes-or-no judgement, but a bounded statement that can be traced back to its evidence and that says clearly what it does not cover. Its form matters as much as its content, because that is what separates an honest validation from a stamp of approval. Every claim can be followed back to a set of logged runs, and every limit is written inside the statement, not in a separate section that a reader in a hurry could skip.

One point, which Chapter 11 returns to, is worth stressing. The framework produced a negative global verdict, an unmet requirement and a rule that was never tested, and all three are in the statement. A traceability framework that only produced good results would be suspicious by nature. The value of this one lies exactly in the fact that the bad results made it to the final page.
