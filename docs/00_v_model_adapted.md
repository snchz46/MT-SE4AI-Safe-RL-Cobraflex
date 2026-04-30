# V-Model Adapted for Systems with Learned Components

**Status:** Living document — Phase 0 deliverable
**Last update:** [date]
**Approved at Gate:** G0 (pending)

## Purpose

This document formalises the adaptation of the classical V-Model to systems whose central components are not fully specified at design time but learned from data. It serves as the methodological backbone of the thesis: every chapter, every artefact, every experimental design choice can be mapped back to a level of this V-Model.

The classical V-Model has, on its left branch, the levels of System Requirements, System Design, Module Design, and Implementation; on its right branch, the corresponding levels of Unit Testing, Integration Testing, System Testing, and Acceptance Testing. The diagonal of the V represents the bidirectional traceability between specification and verification.

When the central component is a learned controller, this structure is necessary but insufficient. Five specific adaptations are introduced.

## Adaptation A1 — Module Design split

Module Design splits into two distinct artefacts:

- **Cage Specification** — the design of the safety cage as an explicitly specified mechanism. Every cage rule is derived from one or more Safety Requirements, has documented logic, and is implemented as auditable code with deterministic behaviour.
- **Training Specification (meta-design)** — the specification of the conditions under which the policy is trained: environment, reward function, observation space, action space, hyperparameter ranges, termination criteria. This is *meta-design* in the sense that what is specified is not the policy itself but the procedure by which it comes into being.

Both artefacts are necessary. Neither alone covers what classical Module Design covered for fully specified controllers.

## Adaptation A2 — Unit Testing split

Unit Testing splits into:

- **Cage Unit Tests** — deterministic tests that verify each cage rule against its specification on synthetic inputs. These tests are pass/fail in the classical sense.
- **Policy Behavioural Evaluation** — statistical evaluation of the trained policy against expected behavioural properties. The verdict is not pass/fail per individual evaluation but a statistical statement over many runs (e.g. mean lateral RMSE, percentile of TTLC).

Both feed into the right branch of the V, but they produce evidence of different kinds.

## Adaptation A3 — Runtime Monitoring as a new V level

A new level is added between Integration Testing and System Testing on the right branch: **Runtime Monitoring**. This level is novel because in classical V-Models, runtime evidence is treated as deployment data, not as part of the validation chain. Here, the structured intervention logs produced by the safety cage during operation are treated as continuous validation evidence, mapped to specific Safety Requirements via the Traceability Matrix.

## Adaptation A4 — Mandatory bidirectional traceability

Bidirectional traceability is reformulated from a soft expectation to a hard constraint. The Traceability Matrix (`docs/07_traceability_matrix.md` and the corresponding CSV under `tools/`) must satisfy at all times:

- Every hazard is referenced by at least one Safety Requirement.
- Every Safety Requirement is implemented by at least one cage rule (or training constraint, or scenario test).
- Every cage rule is exercised by at least one scenario.
- Every scenario references at least one Safety Requirement.
- No orphans on either direction of any of these chains.

Compliance is verified mechanically by `tools/check_traceability.py` before every Gate review.

## Adaptation A5 — Bounded Operational Validation with sim-to-real characterisation

Operational Validation, which classically lives at the top right of the V, is split into:

- **In-simulation Validation** — the principal experimental campaign, where most quantitative claims are sustained.
- **Bounded Physical Validation** — a bounded transfer to the CobraFlex 1:14 platform, where the goal is not to reproduce all simulation results but to characterise the sim-to-real gap quantitatively for the principal metrics and to confirm the functional correctness of the safety cage on real hardware.

The output of A5 is not a single "validated" verdict but a pair of statements: what the simulation evidence supports, and how that evidence transfers to the physical setup with which gap.

## Mapping to thesis chapters

| V-Model level (adapted) | Thesis chapter |  
|-------------------------|----------------|
| System Requirements + ODD | Ch. 4 (Systems Engineering Challenges) and Ch. 5 (SE4AI Framework, ODD section) |
| Hazard Register (HARA) | Ch. 5 (HARA section) |
| Safety Requirements Specification | Ch. 5 (SRS section) |
| Cage Specification (A1) | Ch. 5 (Cage Specification section) |
| Training Specification (A1) | Ch. 6 (Pragmatic Aspects, RL section) |
| Implementation | Ch. 6 (simulator, sensors, ROS2 architecture) |
| Cage Unit Tests (A2) | Ch. 6 (Acceptance criteria) and `cage/tests/` |
| Policy Behavioural Evaluation (A2) | Ch. 8 (Results, per-ODD analysis) |
| Integration Testing | Ch. 8 (Results, end-to-end pipeline) |
| Runtime Monitoring (A3) | Ch. 8 (Results, intervention log analysis) |
| In-simulation Validation (A5) | Ch. 8 (Results, scenario campaign) |
| Bounded Physical Validation (A5) | Ch. 9 (Sim-to-Real Transfer) |
| Traceability (A4) | Ch. 10 (Contribution) and Appendix F (full matrix) |

## Open questions

- Whether Runtime Monitoring (A3) should be considered a permanent V level or a project-specific extension. To be discussed at G1.
- Whether the Training Specification (A1) should include reward shaping decisions or only the specification before the policy is trained. Tentative answer: reward decisions go into the Training Specification, with rationale.

## Change log

See `docs/08_change_log.md` for the history of changes to this document.
