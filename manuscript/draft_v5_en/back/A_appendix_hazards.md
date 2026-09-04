# Appendix A — Hazard register (extended version)

Complete version of the register summarised in Table 4.1. Each entry keeps its
classification of severity (S), exposure (E) and controllability (C), the operational
domains where it applies, the main operational consequence and the dominant root cause
hypothesis. The numbering is stable and non-reusable: a withdrawn identifier is never
assigned again.

| ID | Hazard (description) | S | E | C | Criticality | Applicable ODDs | Main operational consequence | Dominant root cause hypothesis |
| -- | -------------------- | - | - | - | ---------- | --------------- | --------------------------------- | --------------------------------- |
| H-01 | Unintended lateral departure from the lane during nominal or adverse operation. | S3 | E3 | C2 | High | 1, 2, 3, 4 | Contact with the track edge or departure from the drivable corridor. | Incorrect control action in the presence of a high lateral error. |
| H-02 | Divergent or oscillatory orientation error with respect to the lane trajectory. | S2 | E3 | C2 | Medium-High | 1, 2, 3, 4 | Oscillating trajectory or progressive loss of centring. | Insufficient or oscillating corrective action on the heading error. |
| H-03 | Longitudinal speed excessive for the local curvature or visibility (worst case: tight curve). | S3 (conservative, worst case in a curve) | E2 | C1 | Medium-High | 3, 4 | Insufficient braking distance; tangential departure in a curve. | Reward that prioritises progress with no penalty for curvature. |
| H-04 | Unrecoverable compound state (heading + offset + speed simultaneously high). | S3 | E1 | C3 | High | 1, 2, 3, 4 | High-energy lane departure; loss of functional pose. | Accumulated perturbations not seen during training. |
| H-05 | Excessively abrupt actuation command between two consecutive control cycles. | S1 | E3 | C1 | Medium | 1, 2, 3, 4 | Minor mechanical instability; wear; noise propagated to the state estimation. | Absence of action delta regularisation during training. |
| H-06 | Operation on a non-observable or corrupted state (excessive latency, stale data, out-of-range noise). | S3 | E2 (dominated by the physical deployment) | C2 | High | 2, 4 | Decision based on invalid information; loss of coherence. | Lost ROS2 message, sensor in failure, temporal desynchronisation. |
| H-07 | Impossibility of performing a controlled stop when the conditions require it. | S3 | E1 | C1 | High | 1, 2, 3, 4 | Continued motion with no control basis; impact at the end. | Absence of a stop mechanism; policy not trained to brake. |
| H-08 | Stall through reward exploitation: the policy converges to inaction or to an adverse direction that accumulates more reward than nominal lane following. | S2 | E3 | C2 | Medium-High | 1, 2, 3, 4 | Vehicle stopped or systematically drifting off the safe trajectory; the episode does not progress. | Misaligned reward specification during training; horizon or discount factor that rewards inaction. |
| H-09 | Conflict between cage rules: two or more rules active in the same cycle produce a combined command outside the safe envelope, or an oscillation between contradictory corrections. | S3 (inherits from the most severe hazard whose envelope is broken) | E1 | C2 | Medium | 1, 2, 3, 4 | The cage stops being a guarantee and becomes a source of unsafe commands. | Rules designed in isolation with no explicit arbitration; state coupling between C-04/C-06/C-03; emergency activating during a cascade. |
| H-10 | (Track 'E') Poor lane perception from degraded visual input (glare, exposure, motion blur, low contrast, shadows). | S3 | E3 | C2 | High | 1, 2, 3, 4 | Action on a badly read lane; lateral drift / heading error that escalates to H-01/H-02. | Illumination outside the training distribution; motion blur; reflections/shadows. |
| H-11 | (Track 'E') Loss of valid lane perception (occlusion, absence of features, camera dropout/latency); blinds both policy and cage (common cause, D-43). | S3 | E2 | C2 | High | 1, 2, 3, 4 | Arbitrary commands over a blind perception; without a fallback, an undefined trajectory. | Occlusion; missing features; camera dropout/freeze; extreme wash-out. |
| H-12 | (Track 'E') Wrong detection by the cage: the CV detector of the cage produces a plausible false lane and the cage imposes a wrong envelope. | S3 | E2 | C2 | High | 1, 2, 3, 4 | The cage stops being a guarantee and can take the vehicle out of the true lane. | Misleading markings (branches, old paint); shadows/reflections read as edges; degraded vision that corrupts the detection. |

**Note on three reclassifications.** During the audit of the register, three initially ambiguous
assessments were normalised. H-03 moved from a split severity — not admitted by the
standard — to a single conservative value for the worst case in a curve. H-05 went down from S2 to S1
in order to align with the convention for a real vehicle: abrupt actuation is primarily a
hazard of comfort and wear, not of injury. And H-06 consolidated its exposure into a single
value dominated by the physical deployment. All three are recorded because a silent
reclassification of severity is indistinguishable from an adjustment made for convenience.
