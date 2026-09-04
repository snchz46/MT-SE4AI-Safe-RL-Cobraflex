# Chapter 5 — Architectural design and cage specification

## 5.1 Purpose of the chapter

This chapter occupies the levels of architectural design (L3) and of module specification in its classical form (L4a). It produces the artefact where adaptation A1 is materialised for the first time: the **Cage Specification**, a deterministic and modular specification written in the traditional sense, as opposed to the process specification that Chapter 7 will devote to the policy.

What is developed here is the design philosophy of the safety envelope, the conceptual challenges that its construction raises, the derivation of the rules from the requirements, the design of each rule, the version-controlled parameterisation and the ROS2 architecture that hosts it. The complete parameter specification, with the numerical derivation of each threshold and its calibration status, is given in **Appendix E**.

## 5.2 Design philosophy: the cage as a runtime shield

### 5.2.1 Choice of mechanism

According to Chapter 2, the space of mechanisms for making a learned policy safe admits four families. This thesis adopts the **runtime shield** as the dominant mechanism, for three reasons.

First, **verifiability**. A cage of hand-written rules is a classical component: it admits deterministic unit testing, static analysis and inspection. In the terms of TR 5469 it is a Class I element, while the policy is Class II. That asymmetry is precisely what allows the combined system to keep a verifiable core.

Second, **independence from the training**. A guarantee obtained by modifying the learning objective is statistical and conditioned on the training distribution; a guarantee obtained by runtime filtering rests on the state observed in each cycle, independently of how the policy was trained — and therefore it still holds if the policy is retrained, replaced or degraded.

Third, **compatibility with the framework**. As a natural by-product of its operation, the shield produces an intervention log that is exactly the evidence that the runtime monitoring level (A3) needs. The cage is not only a safety mechanism: it is the **measuring instrument** for the behaviour of the policy.

### 5.2.2 What the cage is not

Three delimitations avoid excessive readings. The cage **is not a controller**: it does not author behaviour, it corrects unsafe commands; if the policy drives well, the cage should stay inactive, and Chapter 8 will show that under clean nominal conditions this is what happens. The cage **is not a formal guarantee**: its rules are heuristics with thresholds derived from requirements, not invariants proved over a dynamic model; what it offers is measurable containment, not proof. And the cage **does not remove the need to train well**: it is the last line, not the first, and a system whose safety depended entirely on it would be a badly trained system — a claim that Chapter 8 forces us to qualify in an uncomfortable way.

## 5.3 Conceptual challenges of the design

Building an envelope of rules raises six problems that are not of implementation but of design, and whose explicit resolution is part of the contribution of this chapter.

**Priority and order between rules.** Several rules can activate in the same cycle on the same actuation channel. A **declared, fixed-order evaluation chain** is adopted, with the rate limiter first — it bounds the raw command before any safety rule reasons over it — and the emergency mode last, because it must be able to overwrite any previous correction. In between, the lateral limit rule is evaluated after the heading rule, so that the harder bound on the more critical variable has the last word among the operational rules.

**Design of the corrective action.** A correction can be added to the command of the policy or overwrite it. **Overwriting** is chosen, in order to avoid policy and cage competing in the same space and producing a sum that neither of them intended. The magnitude of the correction is proportional to the excess over the threshold, not a fixed value: a constant correction would generate discontinuities at the activation boundary.

**Reactive rules and predictive rules.** Rules that observe the current state act late by construction: when the offset reaches the threshold, the dynamics are already compromised. A **predictive** rule is therefore added, which propagates the state over a short horizon and acts on the estimated time to lane departure. Reactive and predictive are complementary: the first bounds the present, the second buys margin.

**Hysteresis and prevention of spurious switching.** A single threshold produces repeated activation and deactivation in its neighbourhood, with an oscillating resulting command that is a hazard in itself. Each rule with a threshold incorporates a **hysteresis band**: it activates above one value and deactivates below a lower one, with state memory between cycles.

**Saturation and conflict resolution.** The composition of corrections can exceed the physical range of the actuator. Saturation is applied **at the end of the chain**, on the composed command, and not rule by rule, so that the result is predictable independently of how many rules intervened.

**Emergency mode and state validity.** The emergency mode is defined with entry by a compound *trigger*, deterministic behaviour — deceleration at a minimum rate with frozen steering — and an explicit exit. Its triggers include not only the unrecoverable compound state, but also the **invalidity of the state itself**: a stale observation, fields outside the plausible range, or loss of perception. This last part is the chain of trust of the system: if the cage cannot trust the state it observes, the safe response is not to correct the command but to **stop the vehicle in a controlled way**.

## 5.4 From requirements to rules

The mapping from requirements to rules follows an explicit procedure: for each requirement, the observable variable that expresses its predicate is identified, together with the mechanism capable of keeping it within limits and the actuation channel on which to act. When no such mechanism exists without violating the philosophy of the cage — the case of *liveness*, where a rule that forced positive throttle would be authorising behaviour instead of correcting it — the requirement is implemented at another level and this is declared.

| Requirement | Rule | Observed variable | Channel |
| --- | --- | --- | --- |
| SR-001 | C-01 — hard lateral limit | lateral offset | steering |
| SR-002 | C-02 — heading error limit | heading error | steering |
| SR-003 | C-03 — predictive time-to-departure limit | projected time to crossing | steering |
| SR-004 | C-04 — speed ceiling | speed and local curvature | throttle |
| SR-005, SR-007, SR-008, SR-013, SR-014 | C-05 — emergency mode | compound state, validity, estimator health | both |
| SR-006, SR-011 | C-06 — rate limiter | command variation between cycles | both |
| SR-009 | — | — | training constraint |
| SR-010 | — | — | arbitration property of the chain |
| SR-012 | C-01, C-02, C-03 over the estimated state | estimated offset and heading | steering |

*Table 5.1 — Traceability from requirements to cage rules.*

Three observations. The first one: **six rules cover fourteen requirements**, because the same rule can implement several of them and one requirement can require several rules. The second one: two requirements are not implemented by a rule, and the framework forces this to be declared in the matrix with the implementation type made explicit — training constraint and arbitration property — instead of inventing a rule that covers them nominally. Labelling the type is more honest than forcing the metaphor. The third one: the requirements of the camera track **do not add rules**: they reuse the existing ones over a state with a different origin, which is a design result in itself — the cage is agnostic to the origin of the state.

## 5.5 The six rules

Each rule is specified with the same format: requirement implemented, observed variable, activation logic, corrective strategy and parameters. The uniformity makes comparison and cross-verification easier. The complete numerical values are in Appendix E.

**C-01 — Hard lateral limit.** It observes the signed lateral offset. Hysteretic activation above a threshold placed below the limit of the requirement, with a lower deactivation band and memory between cycles. The correction is proportional to the excess, in the direction that returns the vehicle to the centre, and is applied by overwriting the steering; the throttle is left untouched. If the emergency mode is active, C-01 does not act.

**C-02 — Heading error limit.** Analogous logic over the orientation error, with its own hysteresis band and gain. C-01 and C-02 can activate at the same time; in the chosen order C-02 is evaluated first, so that the final correction is the composition of both and C-01 keeps the last word. This co-activation is exactly the scenario that hazard H-09 anticipates, and Chapter 8 measures it.

**C-03 — Predictive time-to-crossing limit.** It propagates the lateral state over a short horizon with a simple kinematic model and estimates the time until the lane boundary is crossed. If it falls below the minimum, it applies a correction proportional to the urgency. Its value is that it buys margin before C-01 has to act; its cost is the dependence on a propagation model whose validity degrades with curvature.

**C-04 — Speed ceiling.** It bounds the commanded speed by a ceiling that depends on the local curvature, interpolated between a straight-line value and a curve value. It acts on the throttle. It is the only rule that **never activates** in the reference campaign, for a reason that is documented in Chapter 8 and that is a declared limitation of the operating point, not of the rule.

**C-05 — Emergency mode.** This is the most complex rule and the only one that can overwrite all the others. It is triggered by eight conditions grouped in three families: **unrecoverable compound state** — sustained high heading and offset; **state invalidity** — stale observation, fields out of range, lost messages; and **perception health** — the lane estimator reports that it cannot produce a reliable estimate, or the estimate fails the plausibility check. The behaviour is deterministic: deceleration at a minimum rate with frozen steering until the vehicle stops. The last three families are what makes the system **degrade to a safe stop** instead of acting on a corrupted perception, and they are the materialisation of the camera track requirements.

**C-06 — Rate limiter.** It bounds the variation of the command between consecutive cycles, in steering and in throttle. It is evaluated first, over the raw command. It is formally the rule with the lowest criticality — it implements class B requirements of smoothness and variance — and Chapter 8 will show that this classification **seriously underestimates its real role** in the final system.

## 5.6 Parameterisation, versioning and modes

All thresholds live in a **version-controlled parameter file**, not in the code. The separation has three operational consequences. First: every experimental run records the *hash* of the file together with the rest of the reproducibility metadata, so that a result is linked unambiguously to the exact configuration that produced it. Second: thresholds pending physical calibration are marked explicitly in the file itself, so that their provisional character is visible to whoever reads it and is not buried in the documentation. Third: the versioning follows a backward compatibility policy — when a new feature is introduced, its default values must leave it **inert** for earlier configurations — so that a historical campaign can be re-run without a later feature altering its result.

The cage also admits two **operating modes**, which are the basis of the whole experimental design of this work. In **enforcement** mode the corrections are applied to the command that reaches the vehicle. In **monitoring** mode the cage evaluates exactly the same rules and logs exactly the same activations, but **does not modify the command**: the policy drives alone. The contrast between both modes on the same scenario and the same seed is the instrument with which Chapter 8 measures the contribution of the cage, and its methodological value is that it is a clean counterfactual — not a comparison between different systems, but between the same system with and without the envelope active.

## 5.7 ROS2 architecture

### 5.7.1 Decomposition into nodes

The system is decomposed into nodes with a single responsibility, communicating through explicit topics. The data chain is linear and auditable: perception produces the state; the policy consumes the state and produces a raw command; the cage consumes the raw command and the state and produces a safe command plus a record of the cage status; the vehicle control translates the safe command into actuation setpoints; and the logging node persists the cage status to disk.

<img src="../figures/Lane_camera_agent-cage.png" alt="Figure 5.1 — Node chain of the system." width="480"/>

*Figure 5.1 — Node chain: perception, policy, cage, vehicle control and logging. The command of the policy never reaches the actuator without passing through the cage.*

The architectural property that matters is that **the command of the policy does not reach the actuator without going through the cage**. This is not a coding convention: it is a topological property of the graph, verifiable by inspection of the connections, and it means that there is no path through which an unfiltered command could reach the vehicle.

### 5.7.2 Architecture of the camera track

The camera track keeps the same topology with two substantive differences. The policy receives **the image** instead of the state vector, and the cage obtains its state from its **own lane estimator**, a classical computer vision chain that processes the same image with a deterministic algorithm that is independent of the network.

This decision is the most delicate design point of the work, and its trade-off should be stated precisely. The advantage is that the safety envelope **does not inherit the failure modes of the network**: it reasons over a state produced by an auditable algorithm, which can be inspected line by line and verified against a reference. The cost is a **common cause**: both consume the same image, so a sufficiently severe degradation of the visual channel blinds both at the same time. The design does not hide that cost; it mitigates it with the health and plausibility trigger family of C-05 — which degrades to a controlled stop when the estimator cannot produce a reliable estimate — and declares it as a residual risk, with its own registered hazard (H-12) for the case in which the estimate is wrong *but plausible*, which is the case that no internal consistency check can catch.

## 5.8 Traceability and automatic verification

With the rules specified, the matrix covers its second section: the correspondence between requirements and rules. The validator checks mechanically that every rule implements at least one requirement, that every requirement is implemented by a rule or declares explicitly its alternative implementation type, and that every rule is exercised by at least one scenario. Any violation **blocks the review gate**.

The design effect that this produces deserves to be underlined, because it is one of the claims that Chapter 11 evaluates: the constraint forces the implementation path to be decided **at the moment of writing the requirement**, not afterwards. The observable result is a set of requirements that are more operational, and a set of rules with no orphan functionality — there is no rule in the cage that does not respond to a requirement traceable up to a registered hazard.

With the specification defined, Chapter 6 addresses its implementation and verification.
