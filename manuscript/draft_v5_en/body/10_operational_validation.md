# Chapter 10 — Operational validation

## 10.1 From results to declaration

The previous chapters produce measurements; this one turns them into a **validation declaration** with its limits incorporated into the statement. It is the materialisation of the first half of adaptation A5: the validation conclusion stops being "the system is safe" and becomes a bounded claim about which requirements are satisfied, under which domain, with which evidence and with which residual risks declared.

## 10.2 Inventory of evidence

The declaration rests on three blocks of evidence, all of them with version-controlled artefacts and with their reproducibility metadata — code revision, identifier of the cage configuration, identifier of the checkpoint, seed and timestamp — recorded run by run.

The **perfect perception arm** provides 1,260 runs with a global verdict of satisfied, and its function is that of a control: it fixes what happens when perception is not a problem. The **camera arm** provides the scenario campaigns over a policy learned from pixels, culminating in the **reference campaign of 1,890 runs without errors** that supports the verdict of this chapter. The **study of variability between seeds** provides the characterisation that the behaviour is not homogeneous between repetitions of the training procedure.

**Physical evidence exists, it is bring-up evidence and it is not verdict evidence.** The chain has been executed on the real vehicle and it has driven — 18.05 m of the circuit in a single segment, without activating any safety rule (Chapter 9) — but that is **a bring-up run**: **no physical run has been executed under the protocol of the scenario library**, in enforcement and with the perception contract under which the campaigns were scored. The physical column of the following table is declared **not executed** for that reason, which is different from and more precise than the absence of data: having driven is not having scored, and filling the column with measurements taken outside the protocol would be precisely the kind of claim that the framework exists to prevent.

## 10.3 Consolidated verdict table

| Requirement | Class | Control arm | **Camera arm (reference campaign)** | Physical *(out of scope — §12.4 T2)* |
| --- | :-: | --- | --- | --- |
| SR-001 lateral deviation | A | Satisfied | **Satisfied** | not executed |
| SR-002 heading stability | A | Satisfied | Literal: fail (recovery clause); **own criterion: satisfied** | not executed |
| SR-003 predictive time to departure | A | Satisfied | Literal: fail (same clause); **own criterion: satisfied** | not executed |
| SR-004 speed ceiling | A | Satisfied | **Satisfied** (rule never activated; see §10.4) | not executed |
| SR-005 emergency stop | A | Satisfied | **Satisfied** | not executed |
| SR-006 actuation smoothness | B | Satisfied (own metric) | **Satisfied** (840/840 in enforcement) | not executed |
| SR-007 state validity | A | Satisfied | **Satisfied** | not executed |
| SR-008 external stop | A | Satisfied | **Satisfied** | not executed |
| SR-009 *liveness* | B | Documented abstention | **Satisfied** (own metrology) | not executed |
| SR-010 rule composition | B | Documented abstention | **Not satisfied** — finding, non-vetoing | not executed |
| SR-011 heading variance | B | Satisfied | **Satisfied** on its own metric (3.77° < 5°) | not executed |
| SR-012 following under a degraded camera | A | n/a | **Satisfied** | not executed |
| SR-013 safe perception degradation | A | n/a | **Satisfied** | not executed |
| SR-014 estimator plausibility | A | n/a | **Satisfied** | not executed |

*Table 10.1 — Consolidated verdicts per requirement. The physical column is not scored in this work: no run on hardware was executed under the scenario protocol, and all of them were executed in monitoring (§10.4e). It is declared "not executed" and not "pending", so as not to suggest a measurement in progress.*

Reading it by subsets: **thirteen of the fourteen requirements have a verdict of satisfied** on their documented criterion; **one is not satisfied**, of class B and non-vetoing, reported as such and not reconciled; **none is without a verdict, omitted or pending** in the simulation column. The coverage criterion of the framework evaluation that demanded a verdict for 100 % of the requirements — even if the verdict were uncomfortable — is met, and it is met including the uncomfortable verdict.

Two cells deserve a note. The two requirements with a **literal failure** keep the failure in the record next to their reconciliation; they are not rewritten. And the speed ceiling is marked as satisfied with an important qualification, developed in the following declaration: it is satisfied **without having been exercised**.

## 10.4 Bounded validation declaration

> **Declaration.** Under the specified operational domain, realised on a single circuit in simulation, with the two-dimensional action camera policy selected by closed-loop evaluation and with the cage configuration identified by its *hash*, the system **satisfies thirteen of its fourteen safety requirements on their documented criterion**. The literal global verdict of the campaign is `NOT SATISFIED`, attributable in its entirety to one performance clause — heading recovery time — on a single scenario, without any class A safety predicate being violated.
>
> **Inside the operational domain and with the cage active, no contact with the road edge is recorded** over 945 enforcement runs; the same policy without the cage commits sixty. The unsatisfied requirement is the one on **consistency of rule composition under simultaneous co-activation**, of class B, measured over two different policies, halved by better training and persistent in nature; it is declared as a design limitation of the envelope and as future work.

**Explicit limits of this declaration.** They are stated inside it and not in a separate section, because each one bounds a concrete claim of the preceding ones.

**(a) On the scope.** It is valid in simulation, on one circuit and with one seed in the verdict campaign; the variability between seeds is characterised separately and **is not homogeneous**.

**(b) On what was not exercised.** The speed ceiling of the cage **did not activate a single time** in the 1,890 runs, because the operating point of the policy stays below the floor of that envelope; the requirement is satisfied trivially and its rule remains **untested from above**. It is a limitation of the operating point, not of the specification, and it is declared so that it is not read as evidence of robustness.

**(c) On the measured dependency.** Lane keeping on the tightest curves rests, in this policy, on the rate limiter; the dependency is measured and its origin is inferred.

**(d) On transfer.** Physical evidence exists but **it is not scored**, and no claim in this declaration extends to the real platform. What can be claimed, and is claimed in Chapter 9 and not here, is that the policy that supports this verdict **does not transfer** to the real vehicle and that the one that does is a later retraining: the object validated in this declaration and the object that drives on hardware **are not the same**.

**(e) On what the hardware has not exercised at all, which is the limit that bounds this work the most.** All the physical runs were executed in **monitoring mode**, in which the cage evaluates, publishes and logs its rules but **does not modify the action**: the safe action emitted coincides with the raw action of the policy in all the logged cycles. As a consequence, **the envelope has never acted on the real vehicle**. What the physical step measures is what the cage *would have said*, plus the availability cost of its emergency latch; what it does **not** measure is the effect of the cage on the trajectory of a physical vehicle, which is precisely the property that this declaration certifies in simulation. It is a limit of scope and not a negative result: there is no physical evidence against the envelope, there is no physical evidence in favour, and there will be none until a scored run is executed in enforcement.

**(f) On one rule that the hardware did interrogate.** The speed ceiling is declared satisfied here without having been activated once, and Chapter 9 adds that in the deployed configuration **it could not activate under any reachable circumstance**. For this declaration that means one concrete and bounded thing: the verdict of that requirement rests entirely on the fact that its trigger condition was not reached, and not on evidence that the rule intervenes correctly when it is reached. It is the requirement with the weakest support in the table, and it is flagged as such.

## 10.5 From the declaration to the methodological thesis

The declaration above is the product that the framework promised: not a binary judgement but a **bounded statement, traceable back to the evidence that supports it and explicit about what it does not cover**. Its form is as relevant as its content, because it is exactly what distinguishes an honest validation from a stamp of approval: every claim can be followed backwards to a set of logged runs, and every limit is stated inside the declaration instead of in a separate section that a hurried reader could skip.

One point that Chapter 11 takes up deserves to be underlined. The framework produced a negative global verdict, an unsatisfied requirement and a rule that was never exercised, and all three are in the declaration. A traceability framework that only produced favourable results would be suspect by construction; the value of this one rests precisely on the fact that the unfavourable ones survived to the final page.
