# V-Model Adapted for Systems with Learned Components

**Status:** Living document — Phase 0 deliverable  
**Last update:** 11.05.2026  
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
| ------------------------- | ---------------- |
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
<!--
## Anticipated defense questions

**Q1. Why adapt the V-Model at all instead of adopting an ML-native lifecycle (CRISP-DM, MLOps, the "W-model", or SOTIF / ISO PAS 8800)?**
Because the V-Model is the lingua franca of automotive systems engineering and ISO 26262, which is the frame this thesis (and its committee) works in. The five adaptations import precisely what an ML lifecycle adds — a data-derived component (A1), statistical rather than pass/fail evaluation (A2), runtime evidence as validation (A3) — *without* discarding the bidirectional traceability spine on which the safety argument rests. SOTIF / ISO 8800 are treated as complementary (cited in Ch. 5), not as replacements.

**Q2. Isn't "Runtime Monitoring as a new V level" (A3) just operational telemetry under a new name?**
The novelty is not that logs are collected but that the cage's structured intervention logs are treated as *validation evidence mapped to specific SRs* via the Traceability Matrix — they feed the per-SR verdict, closing the Hazard→…→Verdict chain. Classical V-Models treat runtime data as post-deployment, outside validation. Honest caveat: whether A3 is a permanent V level or a project-specific extension is itself an open question flagged for G1.

**Q3. A1 specifies "the procedure that produces the policy" rather than the policy — isn't that an admission that you cannot specify the safety-critical component?**
Yes, and that is the methodological point. A learned controller is not fully specifiable at design time, so meta-design (specifying environment, reward, observation/action spaces, termination) is the honest substitute. Crucially, the safety case does not rest on the policy's internal correctness: A1 keeps the Cage Specification and the Training Specification as separate artefacts precisely so the guarantee lives in the cage's explicitly specified envelope, not in the unspecifiable half.

**Q4. A4 makes traceability a hard, mechanically-checked constraint — does `check_traceability.py` actually demonstrate safety?**
It demonstrates *coverage*, not *sufficiency*: no hazard without an SR, no SR without a mechanism, a scenario and a metric — no orphan claims on either branch. It does not prove the thresholds are correct; that is the scenario campaign's job. The distinction is stated openly: the check is a necessary gate, not a safety proof.

**Q5. Most quantitative claims live in "In-simulation Validation" (A5) with only *bounded* physical validation — isn't a largely sim-based thesis weak?**
A5 deliberately yields a *pair* of statements — what the simulation evidence supports, and how it transfers to hardware with what gap — rather than a single "validated" verdict. The bounded physical transfer characterises the sim-to-real gap on an exported scenario subset rather than re-proving every claim (scoping decision D-11). The contribution is the SE4AI method plus the cage, demonstrated primarily in simulation and probed on the platform.

**Q6. A2's "statistical pass/fail" is not deterministic like a unit test — how is that reproducible?**
A2 separates the two kinds of evidence on exactly this axis: cage unit tests are deterministic pass/fail, while policy behavioural evaluation is a statistical statement over many seeded runs (e.g. mean lateral RMSE, a TTLC percentile). Reproducibility is preserved through fixed seeds and per-run metadata (git commit, cage-YAML hash, checkpoint hash, scenario hash), so the statistical claim is itself re-derivable.

--->

## Change log

See `docs/CHANGELOG.md` for the history of changes to this document.
