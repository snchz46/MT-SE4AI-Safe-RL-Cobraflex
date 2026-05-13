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

**Mitigated by.** SR-002 (heading stability), SR-003 (TTLC, partial).

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

## Machine-readable Hazard Table

| Hazard ID | Description | Severity | Mitigation | related_cage_rules | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| H-01 | Unintended lane exit | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 | Open | TTLC predictive constraint |
| H-02 | Divergent or oscillatory heading error | S2/E3/C2 - Medium-High | SR-002, SR-003 | C-02, C-03 | Open | Heading stability hazard |
| H-03 | Excessive speed for current conditions | S3/E2/C1 - Medium | SR-004 | C-04 | Open | Curvature-dependent speed ceiling |
| H-04 | Compound unrecoverable state | S3/E1/C3 - High | SR-005 | C-05 | Open | Emergency substitution mode |
| H-05 | Excessively abrupt actuator command | S1/E3/C1 - Medium | SR-006 | C-06 | Open | Actuator rate limiting |
| H-06 | Operation under invalid or unobservable state | S3/E2/C2 - High | SR-007 | C-05 | Open | ROS2 state freshness and validity |
| H-07 | Inability to perform a controlled stop | S3/E1/C1 - High | SR-005, SR-008 | C-05 | Open | Emergency stop behaviour |

---

## STPA scope statement

The STPA-light pass covers H-01, H-02 and H-04, where the unsafe-control-action perspective adds value beyond what HARA alone captures. For these three hazards, the pass applies the four canonical UCA categories — *action not provided when needed*, *action provided when not needed*, *action provided with inappropriate magnitude*, *action provided at the wrong time* — systematically to each principal control action (steering, throttle), with the exception of H-04 where the categories collapse into a single substitution-rather-than-modification mitigation (cf. §H-04 above).

Hazards H-03, H-05, H-06 and H-07 are not analysed with STPA because their causal structure is sufficiently localised (speed ceiling, rate limiter, state-validity triggers and stop mechanism respectively) that the additional perspective produces no new actionable insight beyond what the HARA-derived SRs already capture.

The systematic pass does not introduce new cage rules: it produces additional confidence in the existing design and refinements of the SR rationale (notably the Δt_max persistence requirement and the asymmetric reset for emergency mode), both of which are now incorporated into the rationale of SR-005 in the SRS.

## Open hazards under consideration

The following potential hazards are under active consideration but not yet registered:

- *H-?? Cage rule conflict.* The simultaneous activation of multiple cage rules produces a corrected command that is itself unsafe (e.g. infinite loop of corrections). To be registered if any unit test or scenario reveals such a case.
- *H-?? Sensor calibration drift over physical operation.* Specific to physical deployment; to be addressed in Phase 5.

## Change log

See `docs/CHANGELOG.md`.
