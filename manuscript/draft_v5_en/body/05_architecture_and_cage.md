# Chapter 5 — Architectural design and cage specification

## 5.1 Purpose of the chapter

This chapter covers two levels: architectural design (L3) and module specification in its classical form (L4a). It produces the first artefact where adaptation A1 becomes concrete: the Cage Specification. This is a deterministic, modular specification written in the traditional way, unlike the process specification that Chapter 7 writes for the policy.

The chapter covers the design idea behind the safety envelope, the conceptual problems that come up when building it, how the rules are derived from the requirements, the design of each rule, the version-controlled parameters, and the ROS2 architecture that runs it. The full parameter specification, with the numerical derivation of each threshold and its calibration status, is in Appendix E.

## 5.2 Design idea: the cage as a runtime shield

### 5.2.1 Choice of mechanism

As Chapter 2 showed, there are four families of mechanisms for making a learned policy safe. This thesis uses the runtime shield as the main mechanism, for three reasons.

The first reason is verifiability. A cage made of hand-written rules is a classical component. It can be unit tested deterministically, analysed statically and inspected. In TR 5469 terms (used by analogy, since the TR classifies AI technology), it matches Class I, while the policy is at best Class II. This difference is what lets the combined system keep a core that can be verified.

The second reason is independence from training. A guarantee that comes from changing the learning objective is statistical and depends on the training distribution. A guarantee that comes from runtime filtering depends on the state observed in each cycle, no matter how the policy was trained. So it still holds if the policy is retrained, replaced or gets worse.

The third reason is that it fits the framework. As a side effect of how it works, the shield produces an intervention log, and that log is exactly the evidence the runtime monitoring level (A3) needs. The cage is not only a safety mechanism. It is also the tool that measures how the policy behaves.

### 5.2.2 What the cage is not

Three clarifications help avoid reading too much into it. The cage is not a controller. It does not create behaviour; it corrects unsafe commands. If the policy drives well, the cage should stay inactive, and Chapter 8 shows that this is what happens under clean nominal conditions. The cage is not a formal guarantee. Its rules are heuristics with thresholds taken from the requirements, not invariants proved on a dynamic model. It gives containment that can be measured, not proof. And the cage does not remove the need to train well. It is the last line of defence, not the first, and a system whose safety depended completely on the cage would be a badly trained system. Chapter 8 forces an uncomfortable correction to this last claim.

## 5.3 Design problems

Building an envelope of rules brings up six problems. They are design problems, not implementation problems, and solving them explicitly is part of what this chapter contributes.

**Priority and order between rules.** Several rules can fire in the same cycle on the same actuation channel. The chosen solution is a fixed, declared evaluation order. The rate limiter comes first, so it limits the raw command before any safety rule looks at it. Emergency mode comes last, because it must be able to override any earlier correction. In between, the lateral limit rule runs after the heading rule, so the harder limit on the more critical variable has the final say among the operational rules.

**Design of the correction.** A correction can be added to the policy's command or replace it. Replacing is chosen, so that policy and cage do not compete in the same space and produce a sum that neither intended. The size of the correction depends on how far the value is past the threshold, not a fixed amount. A constant correction would create jumps at the activation boundary.

**Reactive and predictive rules.** Rules that look at the current state always act late: by the time the offset reaches the threshold, the dynamics are already in trouble. So a predictive rule is added. It projects the state over a short horizon and acts on the estimated time to lane departure. The two types work together: the reactive rule limits the present, and the predictive rule buys extra margin.

**Hysteresis and avoiding flickering.** A single threshold makes a rule switch on and off repeatedly around that value, and the resulting oscillating command is a hazard in itself. Every rule with a threshold therefore has a hysteresis band. It switches on above one value and off below a lower one, and it remembers its state between cycles.

**Saturation and conflicts.** The combined corrections can go beyond the physical range of the actuator. Saturation is applied at the end of the chain, on the combined command, and not rule by rule. This keeps the result predictable no matter how many rules acted.

**Emergency mode and state validity.** Emergency mode has an entry condition based on a compound *trigger*, a deterministic behaviour (braking at a minimum rate with steering frozen), and an explicit exit. Its triggers include the unrecoverable compound state, but also cases where the state itself is not valid: an old observation, fields outside a plausible range, or loss of perception. This last group is the system's chain of trust. If the cage cannot trust the state it sees, the safe response is not to correct the command but to stop the vehicle in a controlled way.

## 5.4 From requirements to rules

Requirements are mapped to rules with an explicit procedure. For each requirement, three things are identified: the observable variable that expresses its condition, the mechanism that can keep that variable within limits, and the actuation channel to act on. Sometimes no such mechanism exists without going against the idea of the cage. This is the case for *liveness*: a rule that forced positive throttle would be creating behaviour instead of correcting it. In that case the requirement is implemented at another level, and this is stated.

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

Three comments. First, six rules cover fourteen requirements, because one rule can implement several requirements and one requirement can need several rules. Second, two requirements are not implemented by any rule. The framework makes this visible in the matrix, with the type of implementation stated (training constraint and arbitration property), instead of inventing a rule that covers them only on paper. Naming the type is more honest than forcing a rule. Third, the camera-track requirements do not add new rules. They reuse the existing rules on a state that comes from a different source. This is a design result in itself: the cage does not care where the state comes from.

## 5.5 The six rules

<img src="../figures/fig_5_1_cage_rule_chain.png" alt="Figure 5.1 — The rule chain in evaluation order." width="500"/>

*Figure 5.1 — The six rules in their fixed evaluation order, one pass per cycle. Each rule takes the safe action of the previous rule as its raw action. C-06 first cleans the command into a feasible baseline. C-05 runs last, so its replacement action (steering frozen and braking) overrides every earlier correction. The joint-envelope check at the end of the cycle can still escalate to emergency.*

The six rules run in the fixed order shown in Figure 5.1, one pass per cycle. Each rule is described in the same format: requirement implemented, observed variable, activation logic, correction strategy and parameters. Using the same format makes it easier to compare and cross-check them. The full numerical values are in Appendix E.

**C-01 — Hard lateral limit.** It looks at the signed lateral offset. It activates with hysteresis above a threshold set below the requirement's limit, with a lower deactivation band and memory between cycles. The correction grows with the excess, points back towards the centre, and replaces the steering command. Throttle is not touched. If emergency mode is active, C-01 does nothing.

**C-02 — Heading error limit.** The same logic applied to the orientation error, with its own hysteresis band and gain. C-01 and C-02 can be active at the same time. In the chosen order C-02 runs first, so the final correction combines both and C-01 has the final say. This co-activation is exactly the case that hazard H-09 predicts, and Chapter 8 measures it.

**C-03 — Predictive time-to-crossing limit.** It projects the lateral state over a short horizon with a simple kinematic model and estimates how long it will take to cross the lane boundary. If that time drops below the minimum, it applies a correction that grows with the urgency. Its benefit is that it adds margin before C-01 has to act. Its cost is that it depends on a projection model that gets less accurate as curvature increases.

**C-04 — Speed ceiling.** It limits the commanded speed with a ceiling that depends on the local curvature, interpolated between a value for straight track and a value for curves. It acts on the throttle. It is the only rule that never fires in the reference campaign. Chapter 8 explains why, and the reason is a stated limitation of the operating point, not of the rule.

**C-05 — Emergency mode.** This is the most complex rule and the only one that can override all the others. Eight conditions can trigger it, in three groups. The first is an unrecoverable compound state: high heading error and offset that last over time. The second is an invalid state: an old observation, fields out of range, or lost messages. The third is perception health: the lane estimator reports that it cannot give a reliable estimate, or the estimate fails the plausibility check. The behaviour is deterministic: braking at a minimum rate with steering frozen until the vehicle stops. The last two groups are what make the system fall back to a safe stop instead of acting on bad perception, and they implement the camera-track requirements.

**C-06 — Rate limiter.** It limits how much the command can change between two cycles, for both steering and throttle. It runs first, on the raw command. Formally, it is the least critical rule, since it implements class B requirements on smoothness and variance. Chapter 8 shows that this label greatly underestimates its real role in the final system.

## 5.6 Parameters, versioning and modes

All thresholds are stored in a version-controlled parameter file, not in the code. This has three practical effects. First, every experimental run records the *hash* of the file together with the other reproducibility metadata, so each result is clearly linked to the exact configuration that produced it. Second, thresholds that still need physical calibration are marked in the file itself, so anyone reading it sees that they are provisional, instead of this being hidden somewhere in the documentation. Third, versioning follows a backward compatibility rule: when a new feature is added, its default values must keep it inactive for older configurations. This way an old campaign can be re-run without a newer feature changing its result.

The cage also has two operating modes, and the whole experimental design of this work is built on them. In enforcement mode, the corrections are applied to the command sent to the vehicle. In monitoring mode, the cage checks exactly the same rules and logs exactly the same activations, but does not change the command, so the policy drives alone. Comparing both modes on the same scenario and the same seed is how Chapter 8 measures what the cage contributes. The value of this method is that it gives a clean counterfactual: it does not compare different systems, but the same system with and without the envelope active.

## 5.7 ROS2 architecture

### 5.7.1 Nodes

The system is split into the nodes shown in Figure 5.2. Each node has one job, and they communicate through explicit topics. The data flow is linear and easy to audit. Perception produces the state. The policy reads the state and produces a raw command. The cage reads the raw command and the state and produces a safe command and a cage status record. Vehicle control turns the safe command into actuation setpoints. The logging node writes the cage status to disk.

<img src="../figures/fig_5_2_node_chain.png" alt="Figure 5.2 — Node graph of the system." width="518"/>

*Figure 5.2 — Node graph of the system: perception, policy, cage, vehicle control and logging, with the topics that connect them. In the state track the policy reads the state published by perception. In the camera track it reads the image directly, and the cage gets its state from the CV lane estimator (§5.7.2). The only connection to the platform, `/cmd_vel`, comes from vehicle control, which only receives input from the cage: the policy's command never reaches the actuator without going through it.*

The important architectural property is that the policy's command cannot reach the actuator without passing through the cage. This is not a coding convention. It is a property of the graph's topology that can be checked by looking at the connections, and it means there is no path for an unfiltered command to reach the vehicle.

### 5.7.2 Camera track architecture

The camera track keeps the same topology, with two important differences. The policy gets the image instead of the state vector. And the cage gets its state from its own lane estimator, a classical computer vision pipeline that processes the same image with a deterministic algorithm that does not depend on the network.

This is the most delicate design point of the work, and its trade-off needs to be stated clearly. The benefit is that the safety envelope does not inherit the failure modes of the network. It works on a state produced by an algorithm that can be audited, read line by line and checked against a reference. The cost is a common cause: both use the same image, so a bad enough degradation of the visual channel blinds both at once. The design does not hide this. It reduces the risk with the C-05 health and plausibility triggers, which fall back to a controlled stop when the estimator cannot give a reliable estimate. It also records it as a residual risk, with its own hazard (H-12) for the case where the estimate is wrong *but plausible*. No internal consistency check can catch that case.

## 5.8 Traceability and automatic checks

Now that the rules are specified, the matrix covers its second part: the links between requirements and rules. The checker automatically verifies that every rule implements at least one requirement, that every requirement is implemented by a rule or explicitly states another type of implementation, and that every rule is tested by at least one scenario. Any violation blocks the review gate.

The effect this has on design is worth pointing out, because Chapter 11 evaluates it. The constraint forces the implementation path to be chosen when the requirement is written, not later. The visible result is a set of more practical requirements, and a set of rules with no orphan functionality: every rule in the cage answers a requirement that can be traced back to a registered hazard.

With the specification defined, Chapter 6 covers its implementation and verification.
