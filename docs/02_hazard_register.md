# Hazard Register

**Status:** Living document — Phase 1 deliverable  
**Last update:** 13.05.2026  
**Approved at Gate:** G1 (pending)  

## Purpose

This document is the canonical record of the hazards identified for the lane-following function within its declared ODD. It is produced through a simplified HARA following the structure of ISO 26262, complemented by a lightweight STPA pass on selected hazards.

The format is structured to enable mechanical extraction into the Traceability Matrix. A companion CSV (`docs/data/hazard_register.csv`) is generated automatically from this Markdown by `tools/sync_hazard_register.py`.

## Rating scales

**Severity (S)** — ISO 26262 scale:

- S1: light, manageable injury (analogue interpretation: minor scratches in scaled context)
- S2: severe injury, survivable (analogue: noticeable mechanical damage)
- S3: life-threatening or fatal injury (analogue: full loss of platform integrity)

**Exposure (E)** — frequency of the situation:

- E1: very rare (probability < 1% of operating time)
- E2: low (1–10%)
- E3: medium (10–50%)
- E4: high (>50%)

**Controllability (C)** — driver's or system's ability to avoid harm:

- C1: simply controllable (>99% of cases)
- C2: normally controllable (>90%)
- C3: difficult to control (<90%)

**Criticality** — derived qualitative aggregation of S, E, C, used for prioritisation only.

**Severity convention.** All severity ratings in this register use the *analogue real-vehicle interpretation*: the rating is assigned as if the function being demonstrated were deployed on a full-scale road vehicle carrying humans, not at the 1:14 scale at which the experiment runs. This convention preserves the conceptual mapping with ISO 26262 automotive practice and the case for the cage's existence; it is registered as decision D-03 and discussed as a limitation in §4.9 of the manuscript.

---

## H-01 — Unintended lane exit

**Description.** The vehicle crosses a lane boundary laterally without intent, losing the operational reference of the lane centre.

**Consequence (analogue real-vehicle interpretation).** Lateral collision with adjacent traffic, road edges, or fixed obstacles outside the lane.

**Consequence (scaled context).** Loss of the ability to follow the track; physical contact with track edges.

**Hypothesised root causes.**

- Policy producing accumulating lateral offset without correction.
- Sensor noise inducing biased state estimation.
- Sudden curvature changes that the policy cannot anticipate at the operating frequency.
- Compound state in which heading error and lateral offset combine unfavourably.

**Rating.** S=3, E=3, C=2 (with predictive constraint), Criticality=High.

**Rating rationale.** S=3 follows from the analogue-real-vehicle convention: lateral lane departure on a real road can produce a fatal collision with adjacent traffic or fixed obstacles. E=3 ("medium", 10–50 % of operating time) reflects the well-documented tendency of under-trained or out-of-distribution RL policies to accumulate lateral offset without effective correction (Wäschle et al., 2022; Wang et al., 2024). C=2 is conditional on the operational reliability of the TTLC predictor (verified by SR-003 / metric M-S4): if the predictor degrades — for example under state-estimation noise that biases the kinematic projection — the effective controllability degrades to C=3.

**Mitigated by.** SR-001 (lane departure prevention, direct), SR-003 (TTLC-based predictive constraint).

**STPA-light findings (systematic pass — four UCA categories applied to each principal control action).**

*Steering action.*

- *UCA1: action not provided when needed.* Policy fails to issue a corrective steering command when the vehicle is drifting toward a boundary; cause: policy has not learned the corrective response, or the relevant input feature is masked by sensor noise. → Mitigated by C-01 (fires at boundary regardless of policy behaviour) and by C-03 (fires preemptively under TTLC criterion).
- *UCA2: action provided when not needed.* Policy issues a corrective steering command that pushes the vehicle further from centre; cause: convergence to a reward-exploiting equilibrium. → Mitigated indirectly by C-01 (corrects the resulting trajectory).
- *UCA3: action provided with inappropriate magnitude.* Policy issues a corrective command of insufficient strength; cause: under-training or operation in unseen state distribution. → Mitigated by C-01 with amplification proportional to boundary proximity.
- *UCA4: action provided at the wrong time.* Corrective command arrives after the boundary has been crossed; cause: state-observation latency. → Mitigated by C-03's predictive horizon.

*Throttle action.*

- *UCA1: action not provided when needed.* Vehicle does not slow when approaching a tight curve where lane exit is imminent. → Mitigated by C-04 (speed ceiling).
- *UCA3/UCA4: throttle magnitude or timing errors.* Less critical for H-01 because throttle's effect on lateral offset is indirect; speed compliance through C-04 reduces overall risk.

---

## H-02 — Divergent or oscillatory heading error

**Description.** The vehicle exhibits a heading error relative to the lane direction that grows over time or oscillates without converging. Distinct from H-01: a vehicle can be momentarily aligned in lateral position while still presenting a divergent heading that foreshadows future lane exit.

**Consequence (analogue).** Unpredictable trajectory, progressive loss of lane alignment, eventual escalation into H-01.

**Consequence (scaled context).** Same, with possible escalation to mechanical damage if oscillation amplitude grows.

**Hypothesised root causes.**

- Policy poorly conditioned to recover from heading perturbations.
- Oscillatory feedback in lateral control (insufficient damping).
- Initialisation in perturbed state without recovery capability.

**Rating.** S=2, E=3, C=2, Criticality=Medium-High.

**Rating rationale.** S=2 reflects the immediate severity of a heading divergence in isolation (analogue-real-vehicle: erratic trajectory that degrades but does not immediately fail the function). The rating is *not* upgraded to match H-01 because the C rating already accounts for the fact that the cage interrupts the H-02 → H-01 escalation chain via C-02 and C-03 well before lateral exit becomes imminent; promoting S to 3 would double-count the escalation already captured in the controllability column. E=3 follows from the same RL-policy observation as H-01: heading drift and oscillation are common failure modes of policies trained without explicit heading regularisation. C=2 is conditional on C-02 firing within the response time of the cage.

**Mitigated by.** SR-002 (heading stability — divergence branch), SR-003 (TTLC, partial), SR-011 (heading stability — oscillation branch).

**STPA-light findings (systematic pass).**

*Steering action.*

- *UCA1: action not provided when needed.* Policy ignores heading error and produces no corrective command; less common because heading error is a strong signal but possible under reward exploitation. → Mitigated by C-02 (heading-limit fallback).
- *UCA3: action provided with inappropriate magnitude (oscillation).* Policy alternates between over- and under-correction, producing sustained oscillation; cause: unstable feedback mode learned during training, common in under-trained policies. → Mitigated by C-02 (intervenes when oscillation amplitude exceeds θ_max) and by C-06 (rate limiter dampens the policy's effective correction gain).
- *UCA4: action provided at the wrong time (phase-shifted correction).* Policy's correction is delayed relative to the heading error, producing the oscillation; cause: state-observation latency or stale internal value function. → Mitigated directly by ensuring state freshness (SR-007) and indirectly by C-02.

*Throttle action.* Less directly relevant. Reducing speed slows the rate at which heading error converts to lateral exit; captured indirectly by SR-004.

---

## H-03 — Excessive speed for current conditions

**Description.** The vehicle operates at a forward speed that exceeds the safe envelope for the current curvature or visibility of the track. The worst case occurs in tight-curvature sections where the kinematic margin between commanded speed and skid threshold collapses; this worst case dominates the rating.

**Consequence (analogue).** Insufficient stopping distance, amplified disturbance response, eventual escalation into H-01 or H-02. In tight curves, tangential exit at high energy.

**Consequence (scaled context).** Lateral slip in tight curves, loss of traction, potential platform damage.

**Hypothesised root causes.**

- Policy learning to prioritise progress without sufficient curvature-dependent penalisation.
- Reward function incentivising forward motion without regard to safety margin.

**Rating.** S=3 (conservative; worst case in tight curves), E=2, C=1 (with speed ceiling), Criticality=Medium.

**Rating rationale.** S=3 is assigned conservatively to the worst case (high-energy tangential exit in a tight curve). The previous split rating "S=2 (S=3 in curve)" is not admissible under ISO 26262, which prescribes one rating per hazard; the conservative consolidation is preferred to splitting H-03 into two sub-hazards because the mitigation logic is unified through SR-004 / C-04 (curvature-dependent ceiling). E=2 reflects that excess-speed conditions arise occasionally during normal operation (1–10 %), driven by curvature transitions where the policy has not yet adapted. C=1 follows from the deterministic nature of the speed ceiling enforced by C-04.

**Mitigated by.** SR-004 (speed compliance).

---

## H-04 — Compound unrecoverable state

**Description.** The vehicle simultaneously enters multiple individually recoverable conditions whose combination exceeds the policy's capacity to recover without external intervention. Typical pattern: large heading error combined with non-trivial lateral offset and elevated speed.

**Consequence (analogue).** High-energy lane exit, loss of functional pose, severe collision.

**Consequence (scaled context).** Catastrophic loss of track-following, possible platform damage.

**Hypothesised root causes.**

- Accumulated perturbations not seen during training.
- Sensor noise compounding with control latency.
- Absence of dedicated training in this combinatorial regime.

**Rating.** S=3, E=1, C=3, Criticality=High.

**Rating rationale.** S=3 follows from the analogue interpretation: a high-energy lane exit from compound state is plausibly fatal in a real-vehicle context. E=1 reflects that the joint occurrence of large heading error, non-trivial lateral offset, and elevated speed is rare (the marginal events are each individually recoverable; only their coincidence is dangerous). C=3 is structural to the hazard's definition: compound state is *defined* as the regime in which the policy alone cannot recover, so controllability without external intervention is poor by construction. This circularity is sustainable because the external intervention (C-05 emergency mode) is supplied by the cage as a deterministic substitution rather than a modification of policy commands.

**Mitigated by.** SR-005 (emergency mode for compound state).

**STPA-light findings (systematic pass).**

In compound state, **all** policy commands are untrustworthy by definition; the four UCA categories collapse because any action provided by the policy in this state is to be treated as potentially incorrect. The mitigation strategy is therefore not to tweak the action but to substitute it entirely (SR-005, C-05, emergency mode).

Two further STPA-informed design findings sit outside the standard UCA grid and deserve explicit registration:

- *Trigger persistence requirement.* The trigger for compound state must require sustained persistence (Δt_max = 0.2 s) so that genuine recoverable transients — for instance a single noisy state observation that briefly violates both θ_warning and d_warning — do not unnecessarily activate emergency mode. An instantaneous trigger (Δt_max = 0) would produce spurious activations under benign sensor noise.
- *Asymmetric exit (explicit reset).* Re-entry to nominal operation requires both that the trigger condition has cleared *and* that an explicit reset signal is received. Without the explicit reset, the system would oscillate between emergency and nominal modes as the trigger condition fluctuates near its boundary. This asymmetry is encoded in C-05 (`require_explicit_reset: true`).

---

## H-05 — Excessively abrupt actuator command

**Description.** The policy produces a change in steering or throttle command between two consecutive control steps that exceeds the mechanical envelope of the vehicle or induces dynamic instability.

**Consequence (analogue).** Discomfort, mechanical wear, loss of stability in extreme cases.

**Consequence (scaled context).** Mechanical instability, possible partial wheel lift, oscillations propagating noise into state estimation.

**Hypothesised root causes.**

- Lack of regularisation on action smoothness during training.
- Reward function not penalising action variability.

**Rating.** S=1, E=3, C=1 (with rate limiter), Criticality=Medium.

**Rating rationale.** S=1 (light, manageable). Under the analogue-real-vehicle interpretation, an abrupt steering or throttle command is primarily a comfort-and-wear hazard rather than an injury hazard: it produces passenger discomfort and accelerated mechanical wear, and in extreme cases can induce dynamic instability — but these are not life-threatening. The previous S=2 over-stated the analogy by including the rare extreme-instability case as if it were typical. E=3 follows from the well-documented tendency of policies trained without action-smoothness regularisation to produce high-variance command sequences. C=1 follows from the deterministic, always-active nature of C-06. The criticality stays at "medium" because it is driven by E, not by S; the downgrade does not weaken the case for C-06.

**Mitigated by.** SR-006 (actuator smoothness).

---

## H-06 — Operation under invalid or unobservable state

**Description.** The vehicle acts on a state vector that does not reflect reality, either because a sensor has stopped publishing, because its values are outside physically plausible ranges, or because message arrival times indicate excessive latency.

**Consequence (analogue).** Policy makes decisions based on incorrect information, producing arbitrary behaviour.

**Consequence (scaled context).** Same. Particularly relevant in physical deployment where ROS2 message drops, sensor failures and temporal desynchronisation are non-negligible.

**Hypothesised root causes.**

- ROS2 message drop.
- Sensor failure.
- Temporal desynchronisation.
- Bug in the perception node.

**Rating.** S=3, E=2 (driven by the physical-deployment scenario), C=2 (if detected), Criticality=High.

**Rating rationale.** S=3 follows from the analogue interpretation: a decision based on invalid state produces arbitrary actuator commands, which under adversarial conditions can be fatally unsafe. The exposure rating is consolidated to a single E=2 (formerly "E=1 in controlled environments to E=2 in physical deployment") because ISO 26262 prescribes one rating per hazard and the physical-deployment scenario dominates: ROS2 message drops, sensor failures, and temporal desynchronisation are non-negligible in physical operation and would be artificially under-represented if the simulation E=1 were the basis of the rating. C=2 is conditional on detection by SR-007 / C-05 triggers (staleness and range checks); without detection, controllability collapses to C=3.

**Mitigated by.** SR-007 (state validity and freshness).

---

## H-07 — Inability to perform a controlled stop

**Description.** The vehicle cannot stop in an orderly manner when conditions demand it (end of track, internal fault detected, external stop signal).

**Consequence (analogue).** Continued motion in the absence of a control basis, collision with track end or surrounding structures.

**Consequence (scaled context).** Same; physical impact at the end of the track.

**Hypothesised root causes.**

- Absence of emergency-stop mechanism.
- Policy not trained to brake on demand.
- Brake actuator that does not produce useful deceleration.

**Rating.** S=3, E=1, C=1 (if mechanism exists), Criticality=High.

**Rating rationale.** S=3 follows from the analogue interpretation: a vehicle that cannot stop on demand is the canonical safety failure (the analogue of a vehicle without functional brakes). E=1 reflects that the conditions demanding a stop (track end, internal fault, external command) are rare in nominal operation. C=1 is conditional on the existence of the stop mechanism: without C-05's stop logic and the vehicle-control node's deceleration capability, controllability collapses to C=3 and the hazard becomes unmitigated.

**Mitigated by.** SR-005 (emergency mode), SR-008 (controlled stop on demand).

---

## H-08 — Progress stall via reward exploitation

**Description.** The policy converges to a degenerate behaviour driven by reward exploitation, manifesting in one of two related modes: (i) **stall** — zero or near-zero throttle, in-place oscillation, or sustained immobility — because the cumulative reward of inaction under the trained reward function exceeds the cumulative reward of active lane-following; or (ii) **adversarial direction** — steering or throttle commands that *systematically* push the vehicle away from the safe trajectory because that behaviour, under the trained reward, accumulates more reward than nominal lane-following (e.g., the policy learns to drift toward a band where a reward-shaping term happens to peak). Both modes share the same root cause — misaligned reward specification — and both are detected at the system level through scenario non-completion or post-cage boundary stress, but each requires a distinct verification metric: M-P6 catches stall, M-S2-in-monitoring-mode catches adversarial direction. Distinct from H-04 (compound state, a recovery failure) and from H-07 (inability to stop, an actuator/mechanism failure): H-08 is a **policy-convergence pathology**, a specification-gaming equilibrium produced during training rather than a runtime fault.

**Consequence (analogue real-vehicle interpretation).** Vehicle stopped or barely moving in a live traffic lane. Rear-end collision risk from following vehicles; obstruction of traffic flow; the function fails silently in the sense that no safety threshold is breached at any instant, but the system has stopped performing its intended task.

**Consequence (scaled context).** Episode does not progress; the platform freezes on track. Indistinguishable at instant level from a normal stop, but detectable as absence of forward motion over a window.

**Hypothesised root causes.**

- Reward function with strong per-step penalties for lateral/heading error but weak or absent positive reward for forward progress, so the optimal policy under finite training is to minimise interaction with the environment.
- Early-termination criteria that penalise risky exploration without compensating reward, biasing the policy toward conservative inaction.
- Discount factor or episode length that makes long-horizon progress less attractive than short-horizon penalty avoidance.

**Rating.** S=2, E=3, C=2 (with liveness check and monitoring-mode boundary check), Criticality=Medium-High.

**Rating rationale.** S=2 under the analogue-real-vehicle interpretation: the stall sub-mode is a severe-injury survivable hazard (rear-end collision is the canonical scenario), and the adversarial-direction sub-mode is upper-bounded by H-01's S=3 but mitigated by the cage's runtime envelope; we retain S=2 because either sub-mode is, on its own, severe-injury survivable rather than universally fatal. E=3 reflects that reward exploitation is well-documented in RL: policies trained under misaligned reward functions routinely converge to either inaction or adversarial behaviour (Skalse et al., 2022, "Defining and Characterizing Reward Hacking"; Krakovna et al., 2020, "Specification gaming examples"). C=2 is conditional on (a) the liveness monitor M-P6 catching the stall sub-mode and (b) the monitoring-mode boundary-violation rate (M-S2 in monitoring mode) catching the adversarial-direction sub-mode by exhibiting elevated values that would have been hazardous without the cage. Without either of these observables, the failure is silent at runtime and C collapses to C=3.

**Mitigated by.** SR-009 (minimum forward progress / liveness).

**STPA-light findings.** Not analysed with STPA: H-08's causal structure is not a control-action defect but a *training-time* convergence pathology. The four UCA categories do not apply because the policy is, from its own perspective, behaving optimally — the unsafe outcome arises from misaligned reward specification rather than mis-issued commands. Mitigation accordingly lives at the training-specification level (reward shaping, scenario test) rather than at the runtime cage level.

---

## H-09 — Cage rule conflict

**Description.** Multiple cage rules activate within the same control cycle and produce a sequence of corrections that interact destructively: the corrected command from one rule violates the precondition of another, producing an oscillation between cage outputs across consecutive cycles, a non-convergent correction within a single cycle, or a final command that — although emitted by the cage — is itself outside any safe envelope. Distinct from each individual hazard H-01..H-08, which assume cage rules acting in isolation; H-09 is the *composition* hazard.

**Consequence (analogue real-vehicle interpretation).** The cage stops being a safety guarantee and becomes a source of unsafe commands. The system's trust assumption — that any command emitted post-cage is safer than the raw policy command — is violated. Downstream consequences inherit the severity of the strongest individual hazard whose safe envelope is breached (worst case S=3, analogous to H-01 or H-04).

**Consequence (scaled context).** Same: oscillation in actuator commands, propagation of noise into state estimation, possible escalation into H-02 (heading oscillation) or H-05 (abrupt actuator command) as side effects.

**Hypothesised root causes.**

- Cage rules designed in isolation without an explicit priority ordering or arbiter, so when two rules disagree on the corrected command, the resolution is implementation-defined.
- State coupling between rules: e.g., the speed ceiling (C-04) lowers speed because curvature is high; the rate limiter (C-06) prevents the deceleration from occurring fast enough; the predictive TTLC rule (C-03) then fires because the un-decelerated trajectory projects a lane crossing.
- Rate limiter (C-06) interacting with hard limits (C-01, C-02) such that the rate-limited correction cannot reach the safe band within a single cycle, requiring multiple cycles and producing an apparent oscillation.
- Emergency mode (C-05) triggering during a cage cascade, with ambiguous interaction between the substitution command and the in-flight corrections from C-01/C-02.

**Rating.** S=3, E=1, C=2 (with explicit arbiter), Criticality=Medium.

**Rating rationale.** S=3 inherits from the strongest individual hazard whose envelope a conflict could breach (H-01, H-04). E=1 reflects that the conflict regime is rare by design — the cage rules are intended to be orthogonal in their trigger conditions — and that empirically the joint-activation pattern requires a specific compound state already covered by H-04's E=1 reasoning. C=2 is conditional on the existence of an explicit priority ordering and convergence guarantee in the cage architecture (cf. SR-010): without these, the cage's resolution is implementation-defined and C collapses to C=3.

**Mitigated by.** SR-010 (cage rule composition consistency).

**STPA-light findings.** Not analysed with the four-UCA grid because H-09 is structurally a *composition* hazard rather than a single control-action defect: the question is not "is action X unsafe in context Y" but "is the joint response of multiple safety mechanisms self-consistent". The STPA literature would treat this through the lens of "unsafe control action arising from coordination" — registered here as a design-level finding to be addressed by SR-010's explicit priority ordering and convergence requirement rather than by additional UCA enumeration.

---

## H-10 — Lane misperception under degraded visual input

> **Track 'E' (end-to-end front-camera), decisions D-38 / D-40.** This hazard exists
> because the policy's input becomes the camera image (it learns perception). It does not
> apply to the F-track, whose policy consumes a hand-built state vector.

**Description.** The camera-based policy produces an erroneous lane/pose estimate because the front-camera image is degraded — glare / over-exposure, under-exposure / low light, motion blur, low contrast, or strong shadows — and therefore computes its steering command from a wrong perception of the lane. Under **D-40** the cage reads its *own* deterministic CV lane detector, which the same degradation also affects (common-cause with the policy); the residual safety is the controlled stop once the lane becomes undetectable (H-11 / SR-013).

**Consequence (analogue real-vehicle interpretation).** The vehicle acts on a misread lane, accumulating lateral offset or heading error and escalating into H-01 / H-02; on a real road, departure into adjacent traffic.

**Consequence (scaled context).** Loss of track-following; physical contact with track edges.

**Hypothesised root causes.**

- Lighting conditions outside the policy's training distribution (sun glare, deep shadow, dusk).
- Motion blur and rolling-shutter artefacts at speed.
- Camera auto-exposure lag after an abrupt brightness change.
- Reflections / specular highlights washing out lane features.

**Rating.** S=3, E=3, C=2, Criticality=High.

**Rating rationale.** S=3 follows the analogue convention (acting on a misread lane is a lane-exit hazard, as H-01). E=3 ("medium", 10–50 %): for a camera-driven system, visually-degrading conditions (glare, shadow transitions, exposure changes, blur at speed) occur in a large fraction of operating time — they are the norm, not the exception. C=2 is conditional on the cage's **deterministic CV lane detector** (D-40) degrading differently from — and more gracefully than — the learned CNN (partially decorrelated failure), so it still bounds the trajectory (C-01/C-02/C-03) while the lane remains detectable; under severe degradation the lane becomes undetectable for the cage too and the safe response is the open-loop controlled stop (H-11 / SR-013). A confidently *wrong* CV detection is the separate hazard H-12.

**Mitigated by.** SR-012 (lane-keeping under degraded visual input), realised by the cage (C-01, C-02, C-03) over its **own CV lane estimate** (D-40) **and** a training constraint (visual-domain augmentation / randomisation during E-training), with the controlled-stop fall-back (SR-013 / C-05) when the lane becomes undetectable.

**STPA-light findings.** Treated by analogy with H-01's steering-action pass: a degraded percept manifests as UCA3 (corrective steering of inappropriate magnitude) and UCA4 (correction at the wrong time), both driven by a wrong input rather than a defective control law. The mitigation is identical in spirit to H-01 — do not trust the percept; bound the resulting trajectory on the cage's CV-derived state (C-01 at the boundary, C-03 preemptively). Under D-40 that state is itself camera-derived, so severe degradation routes to the controlled stop.

---

## H-11 — Loss of valid lane perception

> **Track 'E' (end-to-end front-camera), decisions D-38 / D-40.** Loss of visible lane lines
> blinds the *policy* and (under D-40) the *cage's* CV detector alike (common-cause). H-06
> remains the cage's state-pipeline failure in general; H-11 is specifically "no valid lane
> visible".

**Description.** The camera-based policy loses a valid lane reference entirely — lane markings occluded (debris, glare wash-out, severe shadow), absent (worn or missing paint), or the camera signal drops, freezes, or arrives with excessive latency — so the policy has no trustworthy basis for its action.

**Consequence (analogue real-vehicle interpretation).** Policy commands become arbitrary; absent a safe fallback, an undefined and potentially high-energy trajectory.

**Consequence (scaled context).** Loss of track-following; the platform acts on a blind percept.

**Hypothesised root causes.**

- Occlusion of the lane by debris, another object, or a cast shadow.
- Absent or worn lane features the policy was never trained to handle.
- Camera dropout, frozen frames, or frame latency beyond the control budget.
- Total wash-out under extreme glare or darkness.

**Rating.** S=3, E=2, C=2, Criticality=High.

**Rating rationale.** S=3 follows the analogue convention (an arbitrary command on a blind percept can produce a high-energy lane exit). E=2 ("low", 1–10 %): total loss of valid perception is rarer than degradation (cf. H-10's E=3) — it arises occasionally through occlusion events or signal dropout rather than continuously. C=2 is conditional on the cage's CV-estimator **health check** detecting the loss and commanding an **open-loop controlled stop** (SR-013 → C-05), which needs no perception. Under D-40 the cage's detector goes blind in the same conditions as the policy (common-cause), so the controlled stop — not a steering correction — is the safety response. Without the health check, controllability collapses to C=3.

**Mitigated by.** SR-013 (safe degradation on loss of valid perception), realised by the cage's CV-estimator health check raising the C-05 controlled-stop trigger (D-40, Trigger 8). The stop is open-loop, so it holds even when both policy and cage are blind.

**STPA-light findings.** Treated by analogy with H-04: when perception is invalid, **all** policy commands are untrustworthy by definition, so the four UCA categories collapse — the mitigation is not to tweak a command but to substitute it entirely with a deterministic, open-loop controlled stop (C-05 via the cage's CV-estimator health check, D-40), exactly as H-04 substitutes rather than modifies.

---

## H-12 — Cage lane-misdetection (false safety envelope)

> **Track 'E' (end-to-end front-camera), decision D-40.** New under D-40: the cage's state
> now comes from its own CV lane detector, which can be confidently *wrong*. This failure was
> impossible under the superseded D-39 (cage on privileged ground truth).

**Description.** The cage's deterministic CV lane-estimator produces a *plausible but incorrect* lane (e.g. it locks onto a crack, a shadow line, an old / temporary marking, or a reflection), so C-01..C-06 enforce a **wrong** safety envelope — potentially correcting the vehicle toward the false lane and *away* from the true one.

**Consequence (analogue real-vehicle interpretation).** The cage stops being a safety guarantee and can itself drive the vehicle out of the true lane — the trust assumption "any post-cage command is safer than the raw command" is violated. (Related to H-09, but here the cause is a *perception* error in the cage, not a rule-composition conflict.)

**Consequence (scaled context).** The platform tracks a false line off the true track.

**Hypothesised root causes.**

- Misleading markings: forks, merges, old / temporary paint, construction lines, tar seams.
- Strong shadows or reflections read as lane edges.
- Degraded vision (H-10) that *corrupts* rather than *removes* the detection.

**Rating.** S=3, E=2, C=2, Criticality=High.

**Rating rationale.** S=3: a confidently-wrong envelope can drive a lane exit, inheriting H-01's severity. E=2: misleading markings and shadow-as-edge arise occasionally, not continuously. C=2 is conditional on SR-014's plausibility / temporal-consistency check rejecting suspect detections and falling back to the controlled stop (C-05) instead of enforcing a doubtful envelope; without it, C=3. In simulation the estimator's error is bounded by validating it against the ground-truth oracle (D-40).

**Mitigated by.** SR-014 (cage lane-estimator plausibility / temporal-consistency check + conservative fall-back to C-05).

**STPA-light findings.** A "control action based on a wrong belief" case: the cage acts correctly *given* its (false) state, so the defect is upstream in the cage's perception. The mitigation is to make the cage *distrust* a low-plausibility estimate (SR-014) and substitute the controlled stop (C-05), not to alter the rule logic.

---

## Machine-readable Hazard Table

| Hazard ID | Description | Severity | Mitigation | implementation_type | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| H-01 | Unintended lane exit | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 | Open | TTLC predictive constraint |
| H-02 | Divergent or oscillatory heading error | S2/E3/C2 - Medium-High | SR-002, SR-003, SR-011 | C-02, C-03, C-06 | Open | Heading stability (divergence + oscillation branches) |
| H-03 | Excessive speed for current conditions | S3/E2/C1 - Medium | SR-004 | C-04 | Open | Curvature-dependent speed ceiling |
| H-04 | Compound unrecoverable state | S3/E1/C3 - High | SR-005 | C-05 | Open | Emergency substitution mode |
| H-05 | Excessively abrupt actuator command | S1/E3/C1 - Medium | SR-006 | C-06 | Open | Actuator rate limiting |
| H-06 | Operation under invalid or unobservable state | S3/E2/C2 - High | SR-007 | C-05 | Open | ROS2 state freshness and validity |
| H-07 | Inability to perform a controlled stop | S3/E1/C1 - High | SR-005, SR-008 | C-05 | Open | Emergency stop behaviour |
| H-08 | Progress stall via reward exploitation | S2/E3/C2 - Medium-High | SR-009 | training | Open | Policy convergence to inaction equilibrium |
| H-09 | Cage rule conflict | S3/E1/C2 - Medium | SR-010 | arbiter | Open | Composition hazard across C-01..C-06 |
| H-10 | Lane misperception under degraded visual input | S3/E3/C2 - High | SR-012 | C-01, C-02, C-03 + training | Open | Track 'E' (camera); cage on CV, common-cause; cf. D-38, D-40 |
| H-11 | Loss of valid lane perception | S3/E2/C2 - High | SR-013 | C-05 (CV-estimator health → controlled stop) | Open | Track 'E' (camera); common-cause w/ cage CV; cf. D-40 |
| H-12 | Cage lane-misdetection (false safety envelope) | S3/E2/C2 - High | SR-014 | C-05 (plausibility check → controlled stop) | Open | Track 'E' (camera); new under D-40; cf. H-09 |

---

## STPA scope statement

The STPA-light pass covers H-01, H-02 and H-04, where the unsafe-control-action perspective adds value beyond what HARA alone captures. For these three hazards, the pass applies the four canonical UCA categories — *action not provided when needed*, *action provided when not needed*, *action provided with inappropriate magnitude*, *action provided at the wrong time* — systematically to each principal control action (steering, throttle), with the exception of H-04 where the categories collapse into a single substitution-rather-than-modification mitigation (cf. §H-04 above).

Hazards H-03, H-05, H-06 and H-07 are not analysed with STPA because their causal structure is sufficiently localised (speed ceiling, rate limiter, state-validity triggers and stop mechanism respectively) that the additional perspective produces no new actionable insight beyond what the HARA-derived SRs already capture. H-08 is also outside STPA scope: it is a training-time convergence pathology rather than a runtime control-action defect, so the UCA categories do not apply (see rationale in §H-08). H-09 is registered as a *composition* hazard whose treatment is at the cage-architecture level (priority ordering, arbiter, convergence guarantee) rather than at the per-UCA level; see rationale in §H-09.

The systematic pass does not introduce new cage rules: it produces additional confidence in the existing design and refinements of the SR rationale (notably the Δt_max persistence requirement and the asymmetric reset for emergency mode), both of which are now incorporated into the rationale of SR-005 in the SRS.

**Track 'E' addendum (D-38 / D-40).** The camera-perception hazards H-10, H-11 and H-12 are treated by analogy rather than by a fresh four-UCA enumeration: H-10 mirrors H-01's steering-action pass (a wrong percept produces UCA3/UCA4 corrections, bounded on the cage's CV-derived state, D-40); H-11 mirrors H-04's collapse-to-substitution (no valid lane ⇒ all commands untrustworthy ⇒ open-loop controlled stop via C-05); and H-12 (cage lane-misdetection) is a "wrong-belief" case — the cage acts correctly given a false state, mitigated by SR-014 (distrust low-plausibility detections + controlled stop). None introduces a new cage rule; see §H-10, §H-11 and §H-12.

## Open hazards under consideration

The following potential hazards are under active consideration but not yet registered:

- *H-?? Sensor calibration drift over physical operation.* Specific to physical deployment; to be addressed in Phase 5.
<!--
## Anticipated defense questions

**Q1. Why rate severity as if on a full-scale road vehicle (S3 = potentially fatal) when the platform is a 1:14 RC car that cannot injure anyone?**
The analogue-real-vehicle convention (decision D-03, manuscript §4.9) preserves the conceptual mapping to ISO 26262 and the case for the cage's existence. Rating at 1:14 scale would collapse every hazard to S1 and make the safety analysis vacuous. The convention is registered as a decision and discussed as a limitation — it is a declared interpretive choice, not a hidden inflation.

**Q2. ISO 26262 prescribes one S/E/C rating per hazard, yet several rationales say "C=2, degrading to C=3 if the predictor fails" — is that admissible?**
The *assigned* rating is single-valued; the rationale states the *conditionality* to be transparent about what the rating assumes (e.g. H-01's C=2 is conditional on the TTLC predictor, verified by SR-003 / M-S4). H-03 explicitly consolidated a former "S=2 (S=3 in curve)" split into a single conservative S=3 precisely to honour the one-rating rule.

**Q3. STPA-light is applied to only three of nine hazards — isn't that selective analysis?**
The scope statement justifies each inclusion and exclusion. STPA is applied where the unsafe-control-action lens exposes something HARA misses (H-01, H-02, H-04). For localised hazards (H-03 speed, H-05 rate, H-06 state-validity, H-07 stop) the UCA grid produces no new actionable insight beyond the HARA-derived SR; H-08 is a training-time pathology where the UCA categories do not apply; H-09 is a composition hazard handled at the architecture level. The exclusions are argued, not silent.

**Q4. H-08 (reward exploitation) and H-09 (cage rule conflict) look like late, defensive additions — are they genuine hazards?**
Both are first-class and literature-backed (H-08: Skalse et al. 2022, Krakovna et al. 2020; H-09: coordination / composition UCAs) and, tellingly, each needs a *different* mitigation mechanism than H-01..H-07: H-08 a training constraint (SR-009 — a runtime rule forcing `throttle > 0` would violate cage philosophy), H-09 an arbiter property (SR-010). Their addition reflects SR-audit maturity and is recorded in the changelog.

**Q5. H-04's controllability is C=3 "by construction" because compound state is *defined* as unrecoverable — isn't that circular?**
The register names the circularity and defuses it: the mitigation is not to improve the policy's controllability but to *substitute* the policy entirely (C-05 emergency mode, a deterministic override). C=3 is sustainable precisely because the external intervention is a substitution, not a modification of policy commands.

**Q6. Every hazard is still "Open" with F4 underway — why has none been closed?**
A hazard closes only when its mitigating SR carries a "Satisfied" verdict backed by campaign evidence, and the per-SR sim verdicts in `docs/07` are still TBD pending the full F4 run on the Ubuntu host. Marking them Open is the honest state; closing them on unit-test evidence alone would overclaim (cf. the project rule: do not claim a feature works without running it).

--->
## Change log

See `docs/CHANGELOG.md`.
