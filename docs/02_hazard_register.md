# Hazard Register

**Status:** Living document — Phase 1 deliverable
**Last update:** [date]
**Approved at Gate:** G1 (pending)

## Purpose

This document is the canonical record of the hazards identified for the lane-following function within its declared ODD. It is produced through a simplified HARA following the structure of ISO 26262, complemented by a lightweight STPA pass on selected hazards.

The format is structured to enable mechanical extraction into the Traceability Matrix. A companion CSV (`docs/data/hazard_register.csv`) is generated automatically from this Markdown by `tools/sync_hazard_register.py` (to be implemented).

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

**Mitigated by.** SR-001 (lane departure prevention, direct), SR-003 (TTLC-based predictive constraint).

**STPA-light findings (where applicable).**

- *Unsafe Control Action: action not provided when needed.* Policy fails to produce a corrective steering command when the vehicle is drifting toward a boundary. → Mitigated by C-01 (lane boundary hard limit).
- *Unsafe Control Action: action provided with inappropriate magnitude.* Policy produces a corrective steering command of insufficient magnitude. → Mitigated by C-01 amplification when threshold approached.
- *Unsafe Control Action: action provided at the wrong time.* Corrective command is delayed beyond the time-to-cross. → Mitigated by C-03 (predictive TTLC rule).

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

**Mitigated by.** SR-002 (heading stability), SR-003 (TTLC, partial).

**STPA-light findings.**

- *Unsafe Control Action: action provided with inappropriate magnitude.* Policy oscillates between over- and under-correction. → Mitigated by C-02 (heading limit) and C-06 (rate limiter).

---

## H-03 — Excessive speed for current conditions

**Description.** The vehicle operates at a forward speed that exceeds the safe envelope for the current curvature or visibility of the track.

**Consequence (analogue).** Insufficient stopping distance, amplified disturbance response, eventual escalation into H-01 or H-02.

**Consequence (scaled context).** Lateral slip in tight curves, loss of traction, potential platform damage.

**Hypothesised root causes.**

- Policy learning to prioritise progress without sufficient curvature-dependent penalisation.
- Reward function incentivising forward motion without regard to safety margin.

**Rating.** S=2 (S=3 in tight curves), E=2, C=1 (with speed ceiling), Criticality=Medium.

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

**Mitigated by.** SR-005 (emergency mode for compound state).

**STPA-light findings.**

- *Unsafe Control Action: action provided when policy is no longer trustworthy.* The policy continues to issue commands while the system has entered an unrecoverable state. → Mitigated by C-05 (emergency mode), which substitutes commands rather than modifying them.

---

## H-05 — Excessively abrupt actuator command

**Description.** The policy produces a change in steering or throttle command between two consecutive control steps that exceeds the mechanical envelope of the vehicle or induces dynamic instability.

**Consequence (analogue).** Discomfort, mechanical wear, loss of stability in extreme cases.

**Consequence (scaled context).** Mechanical instability, possible partial wheel lift, oscillations propagating noise into state estimation.

**Hypothesised root causes.**

- Lack of regularisation on action smoothness during training.
- Reward function not penalising action variability.

**Rating.** S=2, E=3, C=1 (with rate limiter), Criticality=Medium.

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

**Rating.** S=3, E=1 (in controlled environments) to E=2 (in physical deployment), C=2 (if detected), Criticality=High.

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

**Mitigated by.** SR-005 (emergency mode), SR-008 (controlled stop on demand).

---

## STPA scope statement

The STPA-light pass covers H-01, H-02 and H-04, where the unsafe-control-action perspective adds value beyond what HARA alone captures. Hazards H-03, H-05, H-06 and H-07 are not analysed with STPA because their causal structure is sufficiently localised that the additional perspective produces no new actionable insight.

## Open hazards under consideration

The following potential hazards are under active consideration but not yet registered:

- *H-?? Cage rule conflict.* The simultaneous activation of multiple cage rules produces a corrected command that is itself unsafe (e.g. infinite loop of corrections). To be registered if any unit test or scenario reveals such a case.
- *H-?? Sensor calibration drift over physical operation.* Specific to physical deployment; to be addressed in Phase 5.

## Change log

See `docs/08_change_log.md`.
