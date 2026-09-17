# Chapter 4 — Operational domain, hazard analysis and safety requirements

## 4.1 Purpose of the chapter

This chapter covers the upper left branch of the adapted V-Model. It contains the stakeholder requirements (level L1), expressed as the operational domain, and the system safety requirements (level L2), derived step by step from a hazard analysis. It is the first chapter where the framework of Chapter 3 is no longer just a proposal: it produces artefacts that adaptation A4 checks as a hard constraint.

The official content of each artefact is kept in a version-controlled living document. This chapter shows the final form and the reasoning behind it. The full hazard register, with the root cause hypothesis and cross references for each entry, is in Appendix A. The full *rationale* for each requirement, including how each threshold was derived, is in Appendix B. The complete operational domain specification, with its twelve open questions and how they were closed, is in Appendix D.

## 4.2 Intended function and system requirements

The intended function is to keep the vehicle inside its lane along a closed track, under controlled conditions, without human help during the episode. The function is simple on purpose. The interest of the thesis is not in how advanced the function is, but in how rigorous the cycle that builds and validates it is.

Four system requirements come from this function, before any safety considerations. The vehicle must follow the lane with a limited lateral error. It must finish the route without stopping for no reason. It must run in real time within the stated control cycle. And it must log its behaviour so that the evidence can be reconstructed later. The first three are functional. The fourth comes directly from adaptation A3 and would not appear in a classical cycle.

## 4.3 Operational domain

### 4.3.1 Four domains

The operational domain is split into the four nested domains shown in Figure 4.1. Each one isolates one source of complexity. This makes it possible to link an observed change in safety or performance to one cause, and not to a mix of causes:

- **ODD-1 — nominal.** Reference layout, clean conditions, no stressors. This is the baseline.
- **ODD-2 — adverse.** The same layout with stressors on the perception channel. On the camera track these are visual problems: glare, low light, motion blur, and worn or covered markings.
- **ODD-3 — demanding layout.** A winding, tight layout in clean conditions, with a speed limit that depends on curvature.
- **ODD-4 — combined.** The ODD-3 layout combined with the ODD-2 stressors.

<img src="../figures/fig_4_1_odd_taxonomy.png" alt="Figure 4.1 — ODD taxonomy retained and the four stratified domains." width="580"/>

*Figure 4.1 — The ODD taxonomy used and the four domains. On the left, the PAS 1883 / ISO 34503 dimensions used to describe each domain. On the right, the 2 × 2 split whose pairwise comparisons let Chapter 8 link an effect to a single source of complexity: ODD-1 against ODD-2 isolates the stressors on straight track, ODD-1 against ODD-3 isolates the harder layout in clean conditions, and ODD-3 against ODD-4 adds stressors on curves.*

Each domain sets named parameters: lane and road width, friction coefficient, maximum curvature, speed range, control latency, and the size of the observation and the action. This way any later claim can point to a specific value and not to a vague description.

### 4.3.2 Domain attributes and scenario stressors

One distinction is kept strictly throughout this work, because mixing the two often leads to wrong conclusions. A domain attribute defines where the system is *allowed* to operate. A scenario stressor is a disturbance added inside that domain to trigger a specific failure mode. If a stressor inside the domain causes the vehicle to leave the lane, that is a system failure. If the same departure is caused by a starting condition outside the domain, it is not, and counting it as a failure would make the verdict invalid. This distinction is the basis for the "inside/outside the ODD" split that Chapter 8 uses to read all its results.

### 4.3.3 Physical domain

For deployment on the real platform, a matching domain is planned, as close as the hardware allows. It has the same scenario type, exclusions and exit hypotheses, but it differs in the vehicle's dynamic limits, the sensing and actuation interfaces, and the normal loop latency. One domain parameter, the maximum commanded lateral acceleration, cannot be measured in simulation at all, because there it would simply follow from the friction coefficient that the simulated world assumes. It stays open and explicitly waits for a physical calibration. It is the only domain question that this work leaves open, and it is marked as open instead of being estimated.

## 4.4 Hazard analysis

### 4.4.1 Procedure

The analysis follows the structure of a HARA as in ISO 26262 (Figure 4.2 shows the procedure as applied), with three simplifications that need to be stated. It is applied to one function and one element instead of a full vehicle. The operational situations come from the four domains instead of from a usage catalogue. And instead of assigning an integrity level, it uses a custom two-class criticality scale, which suits a scale vehicle with no consequences for people. These simplifications change the scope of the reasoning, not its structure: situation, hazard, severity, exposure, controllability, criticality, mitigation.

<img src="../figures/fig_4_2_hara_procedure.png" alt="Figure 4.2 — The HARA procedure as applied." width="560"/>

*Figure 4.2 — The HARA procedure as applied: five steps from listing the functions to documenting the consequence and the root-cause hypothesis. A light systemic pass refines the constraints on selected hazards, and the output is the hazard register.*

Each hazard is rated on three axes with explicit scales: severity (from S0, no injury, to S3, a serious consequence on the full-size equivalent), exposure (from E0 to E4, based on how often the situation happens inside the domain) and controllability (from C0 to C3, based on how well the system or a supervisor can avoid the damage). Together they give the criticality, which decides whether the hazard needs a deterministic rule, a training constraint, or both.

### 4.4.2 Hazard register

The register, summarised in Table 4.1, contains twelve hazards: nine at system level, shared by both tracks, and three specific to the camera track. The numbering is stable. Once an identifier is assigned it is never reused or renamed, even if the hazard is dropped in a later review. The table is the short version. The extended register, with the root cause hypothesis and the operational consequence of each entry, is in Appendix A.

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

*Table 4.1 — Hazard register, short version (extended register in Appendix A).*

Three entries need a comment, because they would not appear in a classical analysis. H-08 is specific to the learned component. It is reward exploitation: the policy ends up doing nothing, or doing something harmful, because that earns more reward than normal lane following. H-09 is specific to the *mitigation*. If two or more cage rules fire in the same cycle and their combined output is a command outside the safe envelope, the cage is no longer a guarantee and becomes a source of unsafe commands. Recording the hazards created by the safety mechanism itself is a basic matter of honesty, and Chapter 8 shows that this was not just a formal precaution. H-12 is the camera-track version of the same idea: the cage estimator produces a lane that is false but looks plausible, and applies a wrong envelope over the real lane.

### 4.4.3 Systemic analysis

For the most critical hazards, a light systemic analysis based on control theory is also carried out. It looks at unsafe control actions in the whole loop, instead of failure modes of single components. It found two types of hazard that the component-based analysis had missed: hazards from acting on invalid information (an outdated process model) and hazards from not acting when action was needed. Both types were turned into requirements that are now part of the core of the cage. The pass is *light*, and it is described that way: it does not build the full hierarchical control model and does not list all causal scenarios.

## 4.5 Deriving the safety requirements

### 4.5.1 Procedure and quality criteria

Each hazard is turned into one or more requirements using the procedure in Figure 4.3. There are four required criteria, and the document template enforces them. Falsifiability: the requirement is a measurable condition with a defined way to reach a verdict. Operability: it can be implemented by a concrete mechanism, such as a rule, a training constraint or a scenario test. Traceability: it points to at least one hazard and is pointed to by at least one rule and one scenario. Atomicity: it describes only one property.

<img src="../figures/fig_4_3_sr_derivation.png" alt="Figure 4.3 — The safety-requirement derivation procedure." width="560"/>

*Figure 4.3 — Deriving a safety requirement from a hazard, in four steps. Two guards make the result defensible. Thresholds are set from the physics of the ODD and never from how well the trained policy performed, which would be circular. And the criticality class decides how the requirement is implemented: every class A requirement ends up in a deterministic rule.*

Falsifiability is worth stressing, because everything else depends on it. A requirement like "the vehicle shall drive safely" cannot be falsified, so it cannot be verified or traced: no measurement could ever contradict it. Requiring a named threshold, a metric and a verdict procedure is what makes the traceability matrix a useful tool instead of a paperwork exercise.

### 4.5.2 Requirements specification

The register has fourteen requirements. Table 4.2 shows the short version. The full *rationale* for each one, including how each threshold was derived and a discussion of the values marked provisional until physical calibration, is in Appendix B.

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

*Table 4.2 — Safety requirements specification, short version (full rationale in Appendix B).*

One threshold in the table needs a note, because it is the only one the implementation changes. SR-007 sets the maximum age of the state observation at `200 ms`, which is four cycles of the control loop at 20 Hz. The matching C-05 trigger runs at 10 Hz on the camera track and uses `0.5 s`. This is the same tolerance expressed in cycles (five), not a weaker requirement. The equivalence is recorded in the parameter file and in Appendix D. It is pointed out here so that the reader does not see a contradiction where there is only a stated change of parameters.

### 4.5.3 Criticality classes

The requirements are split into two classes, which affect the global verdict differently. Class A contains the requirements that express actual safety conditions. If one of them is violated, the global verdict of the campaign is invalid. Class B contains requirements for desirable quality properties, such as smoothness, no oscillation, *liveness* and consistent rule composition. Their violation is reported, but it does not block the verdict.

This split is not a way out. It makes it possible to report an unmet requirement honestly without having to call a system unsafe when all its safety conditions are met. Chapter 8 uses this distinction exactly once, and does so openly and with a reason.

## 4.6 Two-way traceability matrix

The matrix is where A4 becomes concrete. It records the full chain `Hazard → Requirement → Rule → Scenario → Metric → Evidence → Verdict` and is kept in two forms: a readable table, and a machine-readable version that the checker uses.

In this chapter the matrix covers only its first part: the links between hazards and requirements. Every hazard in the register has at least one requirement that reduces it, and every requirement comes from at least one hazard, with no orphans in either direction. Two hazards, H-01 and H-02, are covered by more than one requirement, because each can happen in more than one way. H-01 is covered by a hard offset limit and also by the predictive time-to-departure check. H-02 is covered by a limit on magnitude and a limit on variance, which cover the divergent and the oscillating versions of the same hazard.

The checker applies eight coverage constraints and fails the review gate if any of them is broken. The complete matrix, including the parts filled in by later chapters and the final verdicts, is in Appendix F.

## 4.7 Limitations of the analysis

- **Limited scope of the hazard analysis.** The HARA covers lane following on a scale platform. Neither the operational situations nor the severity scales can be used for a road vehicle without review.
- **Severities by analogy.** Severities are set by comparison with a real vehicle, not by measuring physical consequences on the scale platform. This is a stated convention, not a measurement.
- **Light systemic pass.** The control-theory analysis is not complete. It was run on the most critical hazards and found two new types, but the catalogue cannot be called closed.
- **Provisional thresholds.** Several thresholds are marked provisional until they are calibrated on the physical platform. The framework requires this status to be visible in the artefact itself, not left unstated, and the process to resolve it is defined: measure, update the parameter file, version it, re-run the affected scenarios and record the change.
- **Completeness cannot be proved.** No procedure can prove that the hazard catalogue is complete. What is claimed, and checked automatically, is that no identified hazard is left without mitigation and without evidence.

With the domain defined, the hazards listed and the requirements derived, Chapter 5 moves to the design level: the system architecture and the specification of the cage that has to enforce these requirements at runtime.
