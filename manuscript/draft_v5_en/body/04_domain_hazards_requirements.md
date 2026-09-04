# Chapter 4 — Operational domain, hazard analysis and safety requirements

## 4.1 Purpose of the chapter

This chapter materialises the upper left branch of the adapted V-Model: the stakeholder requirements (level L1), made concrete in the operational domain, and the system safety requirements (level L2), derived systematically from a hazard analysis. It is the first chapter where the framework of Chapter 3 stops being a proposal and produces artefacts on which adaptation A4 operates as a hard constraint.

The canonical content of each artefact lives as a version-controlled living document; what is presented here is the consolidated form and the reasoning that produces it. The complete hazard register, with the root cause hypothesis and the cross references of each entry, is given in **Appendix A**; the full *rationale* requirement by requirement, with the derivation of each threshold, in **Appendix B**; and the complete specification of the operational domain, with its twelve open questions and their closure, in **Appendix D**.

## 4.2 Intended function and system requirements

The **intended function** is to keep the vehicle inside its lane along a delimited track, under controlled conditions, without human intervention during the episode. It is deliberately modest: the interest of the thesis is not in the sophistication of the function but in the rigour of the cycle that produces and validates it.

Four system requirements are derived from that function, and they precede any safety consideration: the vehicle must **follow the lane** with a bounded lateral error; it must **complete the route** without stopping unduly; it must **operate in real time** within the declared control cycle; and it must **log its behaviour** so that the evidence can be reconstructed afterwards. The first three are functional; the fourth one is a direct consequence of adaptation A3 and would not appear in a classical cycle.

## 4.3 Operational domain

### 4.3.1 Four-domain structure

The specification of the operational domain is stratified into four nested domains, each of which isolates one axis of complexity. This makes it possible to attribute an observed change in safety or performance to a **single** cause and not to a confounded combination:

- **ODD-1 — nominal.** Reference geometry, clean conditions, no stressors. This is the baseline.
- **ODD-2 — adverse.** The same geometry with stressors on the perception channel. On the camera track that axis **is** visual degradation: glare, low illumination, motion blur, worn or occluded markings.
- **ODD-3 — demanding geometry.** A winding and tight layout in clean conditions, with a speed envelope that depends on curvature.
- **ODD-4 — combined.** Cartesian product of the ODD-3 geometry with the ODD-2 stressors.

Each domain fixes named parameters — lane and road width, friction coefficient, maximum curvature, speed envelope, control latency, dimensionality of the observation and of the action — so that any later claim can refer to a concrete value and not to a qualitative description.

### 4.3.2 Domain attributes versus scenario stressors

One distinction is kept with discipline throughout this work, because confusing the two is a common source of invalid conclusions: a **domain attribute** defines where the system is *authorised* to operate; a **scenario stressor** is a perturbation injected inside that domain in order to provoke a concrete failure mode. An excursion induced by a stressor inside the domain is a system failure; the same excursion caused by an initial condition outside the domain is not, and counting it as one would invalidate the verdict. This distinction supports the "inside/outside the ODD" partition through which Chapter 8 reads all of its results.

### 4.3.3 Physical domain

For the deployment on the real platform an analogous domain is foreseen, the closest one that can be realised on hardware. It shares the scenario type, the exclusions and the exit hypotheses, but differs in the dynamic envelope of the vehicle, in the sensing and actuation interfaces, and in the nominal loop latency. One single domain parameter — the maximum commanded lateral acceleration — is **unmeasurable in simulation by construction**, because in the simulator it would be a consequence of the friction coefficient that the world itself assumes; it remains open and explicitly pending a physical calibration. It is the only domain question that this work closes as pending, and it is declared as such instead of being estimated.

## 4.4 Hazard analysis

### 4.4.1 Procedure

The analysis follows the structure of a HARA according to ISO 26262, **simplified** at three points that should be declared: it is applied to a single function and a single element instead of to a complete vehicle; the operational situations are enumerated from the four domains instead of being derived from a usage catalogue; and the assignment of an integrity level is replaced by a two-class criticality classification of our own, appropriate for a scale vehicle with no consequences for people. The simplifications do not affect the structure of the reasoning — situation, hazard, severity, exposure, controllability, criticality, mitigation — but its scope.

Each hazard is classified along three axes with explicit rubrics: **severity** (from S0, no injury, to S3, a serious consequence on the full-scale analogue), **exposure** (from E0 to E4, according to the frequency of the situation inside the domain) and **controllability** (from C0 to C3, according to the ability of the system or of a supervisor to avoid the damage). The combination produces the criticality, and this determines whether the hazard requires mitigation by a deterministic rule, by a training constraint, or by both.

### 4.4.2 Hazard register

The register consolidates **twelve hazards**: nine at the system level, common to both tracks, and three specific to the camera track. The numbering is stable: an assigned identifier is neither reused nor renamed, even if the hazard is discarded in later reviews. The table presents the compact form; the extended register, with the root cause hypothesis and the operational consequence of each entry, is in Appendix A.

| ID | Hazard | S | E | C | Criticality |
| --- | --- | :-: | :-: | :-: | --- |
| H-01 | Unintended lateral departure from the lane | S3 | E3 | C2 | High |
| H-02 | Divergent or oscillatory orientation error | S2 | E3 | C2 | Medium-high |
| H-03 | Excessive speed for the local curvature | S3 | E2 | C1 | Medium-high |
| H-04 | Unrecoverable compound state (heading + offset + speed) | S3 | E1 | C3 | High |
| H-05 | Abrupt actuation command between consecutive cycles | S1 | E3 | C1 | Medium |
| H-06 | Operation on a non-observable or corrupted state | S3 | E2 | C2 | High |
| H-07 | Impossibility of performing a controlled stop | S3 | E1 | C1 | High |
| H-08 | *Stall* through reward exploitation | S2 | E3 | C2 | Medium-high |
| H-09 | Conflict between cage rules under co-activation | S3 | E1 | C2 | Medium |
| H-10 | Poor lane perception from degraded visual input | S3 | E3 | C2 | High |
| H-11 | Loss of valid lane perception | S3 | E2 | C2 | High |
| H-12 | Wrong detection by the cage estimator (plausible false lane) | S3 | E2 | C2 | High |

*Table 4.1 — Hazard register in compact form (extended register in Appendix A).*

Three entries deserve a comment because they would not appear in a classical analysis. **H-08** is a hazard specific to the learned component: the exploitation of the reward function, by which the policy converges to inaction or to an adverse behaviour that accumulates more reward than nominal following. **H-09** is a hazard specific to the *mitigation*: if two or more cage rules activate in the same cycle and their composition produces a command outside the safe envelope, the cage stops being a guarantee and becomes a source of unsafe commands. Registering the hazard introduced by the safety mechanism itself is an elementary requirement of honesty, and Chapter 8 will show that it was not a rhetorical precaution. **H-12** is its equivalent on the camera track: the cage estimator produces a false but plausible lane, and imposes a wrong envelope over the true lane.

### 4.4.3 Systemic complement

For the hazards with the highest criticality, a light pass of systemic analysis based on control theory is also executed, which examines the unsafe control actions of the complete loop instead of the failure modes of its components. Its contribution was the identification of two hazard classes that the component-based analysis had not produced: those derived from **acting on invalid information** — an out-of-date process model — and those derived from the **absence of action when it was necessary**. Both classes were materialised in requirements that are today part of the core of the cage. The pass is *light* and it is declared as such: it does not build the complete hierarchical control model and it does not enumerate the causal scenarios exhaustively.

## 4.5 Derivation of safety requirements

### 4.5.1 Procedure and quality criteria

Each hazard is translated into one or more requirements under four mandatory criteria, which the document template makes enforceable: **falsifiability** — expressed as a measurable condition with a defined verdict procedure; **operability** — implementable by a concrete mechanism, whether a rule, a training constraint or a scenario test; **traceability** — it references at least one hazard and is referenced by at least one rule and one scenario; and **atomicity** — it captures a single property.

Falsifiability deserves emphasis because it is the criterion that makes everything else possible. A requirement such as "the vehicle shall drive safely" is not falsifiable and therefore is neither verifiable nor traceable: there is no measurement that could contradict it. The discipline of demanding a named threshold, a metric and a verdict procedure is what turns the traceability matrix into an instrument with content, instead of a documentary exercise.

### 4.5.2 Requirements specification

The register contains **fourteen requirements**. The table presents them in compact form; the complete *rationale* for each one — including the derivation of each threshold and the discussion of the values marked as provisional while waiting for physical calibration — is in Appendix B.

| ID | Requirement (short form) | Main threshold | Hazard | Implementation | Class |
| --- | --- | --- | --- | --- | :-: |
| SR-001 | Bounded lateral offset inside the ODD | `d_max = 0.16 m` | H-01 | C-01 | A |
| SR-002 | Bounded orientation error | `θ_max = 25°` | H-02 | C-02 | A |
| SR-003 | Projected time to lane departure above a minimum | `t_min = 1.0 s` | H-01, H-02 | C-03 | A |
| SR-004 | Speed under a curvature-dependent ceiling | `0.25–0.5 m/s` | H-03 | C-04 | A |
| SR-005 | Transition to emergency mode under a compound *trigger* | `θ_warn 20°`, `d_warn 0.12 m` | H-04, H-07 | C-05 | A |
| SR-006 | Bounded command variation between cycles | `δ_max = 0.15` | H-05 | C-06 | B |
| SR-007 | Emergency on a stale or out-of-range observation | `staleness ≤ 200 ms` | H-06 | C-05 | A |
| SR-008 | Controlled stop under an external signal | `t_stop ≤ 1.7 s` | H-07 | C-05 | A |
| SR-009 | Minimum longitudinal progress (*liveness*) | `Δs ≥ 0.10 m / 2 s` | H-08 | training | B |
| SR-010 | Consistent composition of co-active rules | joint envelope | H-09 | arbitration | B |
| SR-011 | Bounded heading variance | `σ_θ ≤ 5°` | H-02 | C-06 + training | B |
| SR-012 | Lane following under degraded visual input | reuses `d_max`, `θ_max` | H-10 | C-01/02/03 + training | A |
| SR-013 | Controlled stop on loss of perception | `≤ 200 ms` | H-11 | C-05 | A |
| SR-014 | Do not impose rules on an implausible estimate | plausibility tolerance | H-12 | C-05 | A |

*Table 4.2 — Safety requirements specification in compact form (complete rationale in Appendix B).*

### 4.5.3 Criticality classes

The requirements are distributed into two classes with different consequences for the global verdict. **Class A** groups those that express a safety predicate proper: their violation invalidates the global verdict of the campaign. **Class B** groups those that express desirable quality properties — smoothness, absence of oscillation, *liveness*, composition consistency — whose violation is reported but **does not veto** the verdict.

The distinction is not an escape route: it is what allows an unsatisfied requirement to be reported honestly without forcing the declaration that a system is unsafe when its safety predicates are fully met. Chapter 8 makes use of that distinction exactly once, and does so explicitly and with argument.

## 4.6 Bidirectional traceability matrix

The matrix is the artefact where A4 is materialised. It records the complete chain `Hazard → Requirement → Rule → Scenario → Metric → Evidence → Verdict` and is maintained in two complementary forms: a readable, tabular one, and a machine-processable one that the validator checks.

In this chapter the matrix covers its first section: the coverage between hazards and requirements. Every hazard in the register has at least one requirement that mitigates it, and every requirement derives from at least one hazard, with no orphans in either direction. Two hazards — H-01 and H-02 — receive mitigation from more than one requirement, which reflects that they admit different branches: H-01 is mitigated by a hard offset limit and also by the predictive time-to-departure criterion; H-02 by a magnitude limit and by a variance limit, which cover respectively the divergent branch and the oscillatory branch of the same hazard.

The validator applies eight coverage constraints and **fails the review gate** if any of them is violated. The complete matrix, with the sections that the following chapters progressively fill in and with the final verdicts, is given in **Appendix F**.

## 4.7 Limitations of the analysis

- **Hazard analysis of bounded scope.** The HARA covers the lane-following function on a scale platform; neither the operational situations nor the severity rubrics can be transferred to a street vehicle without review.
- **Severities by analogy.** The severities are assigned by analogy with a real vehicle, not by a physical consequence measured on the scale platform. This is a declared convention, not a measurement.
- **Light systemic pass.** The control-theory complement is not exhaustive; it was executed over the hazards with the highest criticality and produced two new classes, but it cannot be claimed that the catalogue is closed.
- **Provisional thresholds.** Several thresholds are marked as provisional while waiting for calibration on the physical platform. The framework requires that condition to be visible in the artefact itself instead of remaining implicit, and the resolution cycle is defined: measure, update the parameter file, version it, re-run the affected scenarios and record the change.
- **Completeness cannot be demonstrated.** There is no procedure that proves the hazard catalogue is complete. What is claimed — and checked mechanically — is that **none of the identified hazards is left without mitigation and without evidence**.

With the domain fixed, the hazards catalogued and the requirements derived, Chapter 5 addresses the design level: the architecture of the system and the specification of the cage that has to enforce these requirements at runtime.
