# DECISIONS.md — Project decision log

<!--
Status: decisions through D-69. D-47..D-49 close/reconcile GE4; D-50..D-58 cover the Isaac posterior; D-59/D-60 cover Gazebo 2-D and PPO/SAC; D-61 reconciles the implemented Jazzy/Harmonic stack and supersedes D-13's preliminary Humble distribution choice; D-62..D-66 build and qualify the 2-D arm; D-67 makes it the research trunk (conditionally); D-68 audits the heading-recovery metric; D-69 closes the simulation programme — verdict of record re-pointed, SR-009/SR-010 TBDs closed.
Last update: 2026-07-31.
-->

## Purpose of this file

This file is the **central decision log** of the project. Every technical,
methodological, or scope decision that has impact on the trajectory of the
work is documented here with a unique identifier (`D-NN`), regardless of
whether the decision is confirmed, deferred to a later phase, or eventually
revised.

The file serves three functions that the methodology of Chapter 3 makes
explicit. First, it acts as an *auditable instrument* to mitigate author
bias (cf. §3.2.3): a third party who replicated the exercise on the
project artefacts can inspect here what was decided and why, without
having to reconstruct it from the chapters. Second, it acts as a
*measurement instrument for the framework's adoption cost* (cf. §3.7,
criterion 4): the weight of registered decisions is one of the indicators
that Chapter 11 retakes when evaluating the framework. Third, it acts as
*operational memory* during development: when a later decision depends on
an earlier one, it is cited by ID rather than reopening the discussion.

The format of each entry is consistent and inspired by the *Architecture
Decision Records* (ADR) proposed by Michael Nygard, adapted to the
vocabulary of this thesis. Each decision includes a small metadata table
(section where it is documented in the chapters, current status, decision
date, planned review date if applicable) and a prose body with four
blocks: *decision* (declarative, one or two sentences), *alternatives
considered and rejected* (with reasons), *rationale* (the answer to "why
this and not that?" if the committee asks), and *consequences* (what it
implies for the rest of the project).

When a decision cites the literature, it uses the format `Author (year)`
consistent with the chapters.

---

## Decision index

| ID | Title | Chapter / Section | Status |
| --- | --- | --- | --- |
| D-01 | No *end-to-end* architecture for the integration of the RL *policy* | §3.5.1 (additional motivation in §3.4) | SUPERSEDED by D-41 |
| D-02 | Three chained hypotheses (H1, H2, H3) | §1.3 | CONFIRMED |
| D-03 | Seven specific objectives (OE1–OE7) with 1:1 mapping to chapters | §1.4 | CONFIRMED |
| D-04 | Bounded scope: SAE Level 2, single *lane-following* case, controlled track | §1.6 | CONFIRMED |
| D-05 | Epistemological positioning: *design science research* | §3.2.1 | CONFIRMED |
| D-06 | Evaluation strategy: single case + structural plausibility | §3.2.2 | CONFIRMED |
| D-07 | A1 — Splitting level L4 into Cage Spec + Training Spec | §3.4.1 | CONFIRMED |
| D-08 | A2 — Splitting level L4' into Cage Unit Tests + Policy Behavioral Evaluation | §3.4.2 | CONFIRMED |
| D-09 | A3 — New transversal Runtime Monitoring level | §3.4.3 | CONFIRMED |
| D-10 | A4 — Bidirectional traceability as hard constraint enforced by tooling | §3.4.4 | CONFIRMED |
| D-11 | A5 — Bounded operational validation with sim-to-real gap characterization | §3.4.5 | CONFIRMED |
| D-12 | Adopted simulator: Gazebo (supersedes CARLA in preliminary version) | §3.6.1 | CONFIRMED |
| D-13 | Middleware: ROS2 Humble distribution | §3.6.2 | SUPERSEDED by D-61 |
| D-14 | Learning algorithm: PPO | §3.6.3 | CONFIRMED |
| D-15 | Technology stack: Stable-Baselines3 + PyTorch + pytest + Python 3.10+ | §3.6.4 | CONFIRMED |
| D-16 | Physical platform: 1:14 scale radio-controlled vehicle | §3.6.5 | CONFIRMED |
| D-17 | QED deferred to Phase 4: conceptual inspiration with calibration pending | §3.6.6 | DEFERRED |
| D-18 | Documentation in plain-text Markdown (no industrial MBSE) | §3.6.7 | CONFIRMED |
| D-19 | Five meta-evaluation criteria for the framework | §3.7 | CONFIRMED |
| D-25 | Non-cage mitigations (training constraint, cage architecture) are first-class implementation types alongside numbered cage rules | §4.6 (SR implementation taxonomy) | CONFIRMED |
| D-26 | Severity homothety convention: hazards rated under the analogue-real-vehicle interpretation, not at the 1:14 scale | §4.4.2 | CONFIRMED |
| D-27 | Selective STPA-light pass applied to H-01, H-02, H-04 instead of full STPA | §4.5 | CONFIRMED |
| D-28 | SR-CL-A requires a deterministic cage rule in the C-01..C-06 range | §4.7.1 | CONFIRMED |
| D-29 | SR-CL-A requires ≥25 runs per scenario family for statistical discrimination | §4.7.1 | CONFIRMED |
| D-30 | A negative verdict on any SR-CL-A invalidates the global verdict of the thesis on the system | §4.7.1 | CONFIRMED |
| D-31 | Deliberate exclusion of non-functional AI-specific hazard families (adversarial attacks, distribution shift, explainability, dataset bias, low-magnitude brittleness) from the F1 Hazard Register | §4.9 | CONFIRMED |
| D-32 | Integration of the ROS2 workspace under `src/` by fresh copy of `cobraflex` + `cobraflex_rl`; third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) deferred | infrastructure | CONFIRMED |
| D-33 | Phase 1 ODD-Spec closes 3 of 12 TBDs against the actual `src/` workspace (Q1, Q2, Q3); the remaining 9 are explicitly deferred per phase | §11 of `docs/08_odd_specification.md` | CONFIRMED |
| D-34 | Cage active in enforcement mode during PPO training (in-process, TS-01) | §7 Training Spec (TS-01) | CONFIRMED |
| D-35 | Frontier (out-of-ODD) scenario family as a non-verdict-bearing cage-efficacy contrast (M-S5) | `docs/05` (Frontier scenarios); §8.2.2–§8.2.3 | CONFIRMED |
| D-36 | Seed policy for F4 campaigns: main seed 2024 certifies the D-29/D-30 verdict; cage-dependent seed 123 only in the D-35 frontier contrast, never pooled into the global verdict | §7.5.3 (seed selection); §8.2 (sim-eval campaign) | CONFIRMED |
| D-37 | F4 realises ODD-1..4 on the single oval world at a fixed-speed (ACT_DIM=1) operating point; ODD-1/2 covered, ODD-3 partial (geometry yes, speed envelope no), ODD-4 deferred | `docs/08` §12; `docs/05` Track mapping; §8 | CONFIRMED |
| D-38 | Indeterminate (None) per-run verdicts are excluded from the pass fraction and propagate as `insufficient_evidence`, not as a failure; `run_campaign.py` reconciled to the `verdict_aggregation.py` spine | §8.2 (sim-eval aggregation); `tools/run_campaign.py`; `docs/07` | CONFIRMED |
| D-39 | SR-006 (actuator smoothness) verified directly on its committed-steer rate metric (non-safety-override steps), reported outside the D-30 per-scenario aggregation (precedent D-35); not by `ALL`-scenario inheritance | §8.5/§8.7; `tools/sr006_smoothness.py`; `docs/07` | CONFIRMED |
| D-41 | Track 'E' (parallel, end-to-end front-camera): **supersedes D-01**; camera→action policy behind a retained modular cage; phases E0..E6 / gates GE0..GE6, commit prefix `E2:` | `docs/00`; `docs/01`; §3.5.1 | CONFIRMED |
| D-42 | Track 'E' cage operates on an independent state estimate, not the camera (preserves cage independence; distinguishes H-06 cage-state from H-11 camera-perception) | `docs/04`; `docs/02` | SUPERSEDED by D-43 |
| D-43 | Track 'E' cage state comes from a dedicated deterministic vision lane-estimator (separate from the policy CNN), not ground truth — for generalisation to any road with visible lines; accepts common-cause + new hazard H-12 | `docs/04`; `docs/09` §10; `docs/02` | CONFIRMED |
| D-44 | Isaac-Sim RL training runs **in-process** (the gym env drives a live Isaac `World` via `IsaacSimInterface` — `set_world_pose` teleport / `world.step` / Replicator Lane Cam), **not** over the ROS2 bring-up; this supplies the per-episode reset the bring-up's `gz service set_pose` path could not, and decouples training from the bring-up command (shared scene only, `tools/isaac_scene.py`) | `docs/14`; `tools/isaac_train.py`; `tools/isaac_scene.py`; `src/cobraflex_rl/.../isaac_interface.py` | CONFIRMED |
| D-45 | Track-'E' GE4 safety verdict scored on the SR limit predicate, not the absence of a controlled stop (`emergency == False` dropped from the 8 adverse safety scenarios; a safe stop within limits = pass) | `scenarios_complex_b/*`; `docs/07`; Ch.8 §8.9 | CONFIRMED |
| D-46 | Two-sided D-29 coverage for the camera-stressor SRs: SR-012/013/014 take their nominal family from the clean-input SC-NOM-01 (no-false-trigger baseline), adverse from SC-PERT-04..13 — D-29-feasible without weakening the gate | `docs/03`; `docs/07`; `scenarios_complex_b` | CONFIRMED |
| D-47 | Score SR-002/SR-003 on their own predicate, not the oval-legacy recovery clause | `docs/07`; Ch.8 §8.9 | CONFIRMED |
| D-48 | GE4-V2 SR-001 route: in-ODD IC clip; conservative lane-selection reverted | `docs/11`; `docs/12`; Ch.8 §8.9 | CLOSED |
| D-49 | Freeze 1-D steering-only for GE4; keep 2-D outside the verdict | `docs/09`; `docs/07`; D-59 | CONFIRMED |
| D-50 | Isaac full-authority 2-D environment and multi-circuit sampling | `docs/13`; `docs/14` | VERIFIED |
| D-51 | Re-cut `complex_e` clockwise for steering-handedness balance | `docs/13` | ACCEPTED |
| D-52 | Isaac iteration 2: entropy bonus, graceful stop and nominal evaluator | `docs/13` | ACCEPTED |
| D-53 | Isaac iteration 3: visual-first DR curriculum | `docs/13` | ACCEPTED |
| D-54 | Calibrate Isaac yaw authority | `docs/13` | ACCEPTED |
| D-55 | Isaac-specific cage heading calibration and residual perception risk | `docs/13`; `docs/12` | ACCEPTED |
| D-56 | Add 2-D `stall_penalty` against the parked optimum | `docs/10`; `docs/13` | ACCEPTED |
| D-57 | Debias estimator heading for the Isaac renderer | `docs/12`; `docs/13` | ACCEPTED |
| D-58 | Add reusable hard-section random-spawn curriculum | `docs/09`; `docs/13`; Ch.7 | CONFIRMED |
| D-59 | Add posterior Gazebo 2-D config and separate portable/non-portable Isaac findings | `docs/11`; `docs/13` | ACCEPTED |
| D-60 | Select PPO/SAC through the shared trainer config | `docs/11` §4.2 | ACCEPTED |
| D-61 | Implemented middleware baseline is ROS2 Jazzy + Gazebo Sim Harmonic | Ch.6 §6.2.1; `docs/15` | CONFIRMED |
| D-62 | T3 temporal heading-consistency gate for the H-12 curve over-read | `docs/12`; `docs/11` | ACCEPTED |
| D-63 | SC-PERT-03 2-D negative test: adversary not induced at the preregistered λ | Ch.8 §8.9.7 | SUPERSEDED by D-64 |
| D-64 | Close SC-PERT-03 metrology with a scripted stall stimulus | Ch.8 §8.9.7 | CONFIRMED |
| D-65 | First full 2-D verdict campaign (margin022) | `docs/11`; Ch.8 | ACCEPTED |
| D-66 | Competent 2-D camera policy: PPO at cap 0.22, checkpoint 550k | `docs/11`; Ch.7 | CONFIRMED |
| D-67 | Research trunk of record moves to the 2-D PPO camera policy | `docs/16` §8 | CONFIRMED (condition met, D-69) |
| D-68 | Heading-recovery band referenced to each run's own envelope | `docs/06`; `docs/05` | ACCEPTED |
| D-69 | Verdict of record re-pointed to the 2-D PPO 550k campaign; SR-009/SR-010 TBDs closed; simulation programme declared complete | `docs/07`; `docs/02`–`docs/08` | ACCEPTED |

> **Renumbering note (11.06.2026, pre-merge).** The E-track decisions above were
> originally allocated **D-38 / D-39 / D-40** on the `e2e-camera` branch, while
> `main` independently allocated **D-38 / D-39** to the F4 aggregation decisions
> (indeterminate verdicts = insufficient evidence; SR-006 own-metric). To keep
> IDs unique on the merged trunk, the E-track decisions were renumbered
> **D-38→D-41, D-39→D-42, D-40→D-43** across all living documents, scenario
> YAMLs, code comments and the manuscript. Git commits dated 09–11.06.2026 with
> the `E2:`/`E3:` prefix and the frozen evidence artifacts under
> `experiments/sim/runs/cv_estimator_val_*` cite the **old** numbers (history
> and evidence are not rewritten); read them through this mapping. `main`'s
> D-38/D-39 keep their meanings unchanged.

---

## Decisions

### D-01 — No *end-to-end* architecture for the integration of the RL *policy*

| Field | Value |
| --- | --- |
| Section | §3.5.1 (additional motivation in §3.4) |
| Status | SUPERSEDED by D-41 (camera track adopts a camera→action policy behind the retained modular cage) |
| Date | D9 (Phase 0) |
| Planned review | None (foundational architectural decision) |

**Decision.** The system does NOT adopt an *end-to-end* approach where a
single neural network maps camera pixels directly to actuation commands.
The architecture maintains an explicit modular decomposition —perception,
PPO *policy*, rule-based cage, actuation, logger— in which the
reinforcement-learned component occupies a bounded position within the
ROS2 graph.

**Alternatives considered and rejected.** *End-to-end* approach in the
PilotNet style (Bojarski et al., 2016), where a CNN processes
image→steering-command directly, rejected for the two reasons articulated
by Salay et al. (2017): *end-to-end* architectures challenge the stable
hierarchical decomposition assumption that underpins much of classical
functional safety methodology, and they typically require training sets
exponentially larger than modular architectures to achieve equivalent
performance (Shalev-Shwartz and Shashua, 2016).

**Rationale.** This thesis is a methodological piece of work whose
contribution is the adapted V-Model framework, not a novel *end-to-end*
system. The modular architecture is moreover a necessary condition for
several adaptations of the framework: A1 separates Cage Spec from
Training Spec, which is only possible if cage and *policy* are distinct
modules; A2 separates Cage Unit Tests from Policy Behavioral Evaluation,
which requires that the cage be independently verifiable; A4 (mandatory
traceability) is trivial over modular components and difficult over a
unified black box. Adopting *end-to-end* would render several adaptations
of the proposed framework unviable.

**Consequences.** The system produces evidence for the safety case more
easily; but it bears the additional cost of maintaining several
components and their interfaces. The PPO policy operates on observations
processed by a simplified perception module, not on pixels directly.

**References.** Salay, Queiroz, and Czarnecki (2017); Bojarski et al.
(2016); Shalev-Shwartz and Shashua (2016).

---

### D-02 — Three chained hypotheses (H1, H2, H3)

| Field | Value |
| --- | --- |
| Section | §1.3 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |
| Planned review | After Gate 0 (Phase 1 close), if SR formulation motivates it |

**Decision.** The thesis adopts a structure of three chained hypotheses:
H1 (construct: there exists a small enumerable set of adaptations that
cover the failure modes of RL/AI components without breaking the standard's
structure); H2 (operationalisability: each adaptation is operationalisable
as concrete artefacts with cost proportional to the rest of the project);
and H3 (utility: the resulting framework produces traceable evidence that
allows a grounded verdict on the system's behaviour to be issued). All
three are evaluated at the close of the work in Chapter 11.

**Alternatives considered and rejected.** Single hypothesis ("the adapted
V-Model allows incorporating RL components into autonomous driving systems
without sacrificing traceability"), rejected because it collapses the
three levels into a single binary verdict and loses granularity in
evaluation: H1 may turn out true and H3 false, which would be an
interesting result but invisible under a single-hypothesis formulation.

**Rationale.** The chained structure allows partial verdicts in Chapter
11. If H1 is confirmed but H2 fails, the contribution remains valid at
the conceptual framework level although the operationalisation requires
revision. If H1 and H2 are confirmed but H3 fails, useful evidence for
future refinements by third parties remains.

**Consequences.** Chapter 11 must issue three separate, argued verdicts.
The meta-criteria of §3.7 (cf. D-19) must map to the three hypotheses
explicitly.

---

### D-03 — Seven specific objectives (OE1–OE7) with 1:1 mapping to chapters

| Field | Value |
| --- | --- |
| Section | §1.4 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |
| Planned review | None |

**Decision.** The general objective is decomposed into seven specific
objectives OE1–OE7, each uniquely assigned to one chapter of the
methodological/experimental block (Chapters 3–11).

**Alternatives considered and rejected.** Three to five specific
objectives with n:m mapping to chapters (a more common format in master's
theses at some Spanish schools). Rejected because the n:m mapping dilutes
verifiability: which chapter "fulfils" each objective? The 1:1 mapping
makes the defence easier because each objective has an entire chapter as
explicit fulfilment evidence.

**Rationale.** Standard structure of research theses with methodological
contribution. At the end, each OE has a clear verdict of fulfilment based
on the content of the corresponding chapter.

**Consequences.** Chapter 11 must review OE1–OE7 systematically and issue
a verdict for each. If a specific school requires fewer objectives, the
natural fusion would be OE1+OE2 (framework characterisation + proposal)
and OE5+OE6 (gap characterisation + validation verdict).

---

### D-04 — Bounded scope: SAE Level 2, single *lane-following* case, controlled track

| Field | Value |
| --- | --- |
| Section | §1.6 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |
| Planned review | None (foundational scope decision) |

**Decision.** The project is explicitly bounded along three axes: single
case of application (no multi-case study, no comparison against a control
group with classical V-Model); lane-following task on a delimited track
(no planning, no interaction with other agents); SAE Level 2 (continuous
assistance under human supervision, not SAE 4–5).

**Alternatives considered and rejected.** Multi-case study (rejected for
superficiality incompatible with the rigour the framework itself demands).
Comparison against a control group with classical V-Model (rejected:
would require a double project, infeasible for an individual thesis).
Level SAE 4 (rejected: would require reformulating A1 for more exhaustive
safety cases and A4 to extend traceability to runtime reasoning, not only
to design artefacts).

**Rationale.** A case of application that covers the complete cycle from
HARA to physical deployment with sim-to-real gap characterisation is
already an ambitious commitment for a master's thesis. A deep single case
is preferable to several superficial cases. Generalisation is argued by
structural plausibility (D-06), not by multi-case empirical evidence.

**Consequences.** Chapter 12 must explicitly distinguish which parts of
the framework are reasonably transferable to other domains (other scales,
other tasks, other SAE levels) and which require reformulation. Chapter
11 evaluates the framework with N=1 limitations declared explicitly.

---

### D-05 — Epistemological positioning: *design science research*

| Field | Value |
| --- | --- |
| Section | §3.2.1 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** The thesis is inscribed in the tradition of *design science
research* (Hevner et al., 2004) or, in a closely related formulation,
*constructive research* (March and Smith, 1995). The academic
contribution is an *artefact* —the adapted V-Model framework, articulated
as five adaptations A1–A5 plus its templates and validators— that
addresses a problem previously identified in the literature, evaluated
through a case of application.

**Alternatives considered and rejected.** Classical empirical thesis
(discover a phenomenon, refute a statistical hypothesis), rejected
because there is no phenomenon to discover, there is an artefact to
build. Deductive theoretical thesis, rejected because the problem is not
analytically demonstrable —it involves engineering and methods decisions
that are only evaluated by construction and application—.

**Rationale.** The problem this thesis addresses is one of engineering
and method: how to adapt an ISO 26262 lifecycle to accommodate RL
components. The natural answer is to build a framework and demonstrate
its functioning, which precisely defines design science research. This
has three practical consequences that Chapter 3 develops: the thesis does
not seek the typical contribution of an empirical thesis; the evaluation
is performed on the artefact, which requires Chapter 11; generalisation
is argued by structural plausibility, not by statistical induction.

**Consequences.** Chapter 11 is dedicated to evaluating the framework as
an artefact (cf. D-19). The generalisation argument in Chapter 12 follows
the structural plausibility logic (D-06).

**References.** Hevner et al. (2004); March and Smith (1995).

---

### D-06 — Evaluation strategy: single case + structural plausibility argument

| Field | Value |
| --- | --- |
| Section | §3.2.2 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** The framework is evaluated on a single case of application
(consistent with D-04). Generalisation to other domains is argued by
*structural plausibility*: the A1–A5 adaptations attack assumptions of
the V-Model that fail for any system with a learned component, not only
for *lane-following*. The inference is by plausibility, not by controlled
multi-case experimentation.

**Alternatives considered and rejected.** Multi-case study (rejected:
superficiality incompatible with the rigour of the framework). Comparison
against a control group where the classical V-Model would be applied to
the same system (rejected: would require a double project, infeasible
for an individual thesis).

**Rationale.** Inherent to *design science research* (D-05). A complete
deep case is preferable to several superficial cases for validating a
methodological framework. External validity is bounded explicitly and
discussed in §3.9 and Chapter 12.

**Consequences.** Chapter 11 evaluates the framework with N=1, declaring
explicitly the limits of inference. Chapter 12 distinguishes which parts
of the framework are reasonably transferable and which require
reformulation. The defence of the work must articulate the structural
plausibility argument when the committee asks about generalisation.

**References.** Hevner et al. (2004); March and Smith (1995).

---

### D-07 — A1: Splitting level L4 (*Module Design*) into Cage Spec + Training Spec

| Field | Value |
| --- | --- |
| Section | §3.4.1 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** Level L4 of the classical V-Model is split into L4a (Cage
Specification, classical deterministic module specification) and L4b
(Training Specification, *meta-design* of the training process). The
Cage Spec follows the traditional module-spec format: each rule Cᵢ is a
pure, testable function with defined inputs and outputs. The Training
Spec specifies the process (reward function, state and action spaces,
training ODD, hyperparameters, convergence criteria, active constraints),
not the learned behaviour.

**Alternatives considered and rejected.** Keep L4 unsplit (rejected:
forcing the *policy* into a classical specification breaks the integrity
of the process; exempting it breaks traceability). Three levels
L4a/L4b/L4c adding a separate "data spec" (rejected: redundant with
Training Spec).

**Rationale.** Consistent with the *three-stage realization principle*
of ISO/IEC TR 5469:2024 (clause 7), which distinguishes the phases of
acquisition from inputs, induction of knowledge from data, and
processing and generation of outputs. Also consistent with the
distinction between Class I elements (cage, traditional verification
applicable) and Class II (policy, specific techniques required) in the
same TR. It allows applying classical techniques where they apply and
statistical techniques where they are needed, without forcing metaphors.

**Consequences.** Two separately versioned artefacts are produced:
`cage_specification.md` (with C-01..C-0n formally defined) and
`training_specification.md` (with reward function, hyperparameters, ODD,
and convergence criteria). The H↔SR↔C traceability must distinguish
Class I from Class II components.

**References.** Kuutti et al. (2019b, 2021); ISO/IEC TR 5469:2024.

---

### D-08 — A2: Splitting level L4' (*Unit Testing*) into Cage Unit Tests + Policy Behavioral Evaluation

| Field | Value |
| --- | --- |
| Section | §3.4.2 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** Level L4' of the classical V-Model is split into L4a'
(Cage Unit Tests, deterministic pass/fail suite using pytest over each
cage rule) and L4b' (Policy Behavioral Evaluation, statistical
characterisation of the *policy*'s behaviour over the *scenario library*
with means, variances, percentiles, and confidence intervals).

**Alternatives considered and rejected.** Keep L4' unsplit (rejected:
there is no "correct output" for unit tests on the *policy*; any
classical unit test on it would be invalid by construction). Replace L4'
entirely with statistical evaluation (rejected: the cage admits classical
tests and it is appropriate to keep them as Class I verification).

**Rationale.** Symmetric mirror of D-07. It acknowledges that classical
verification is not applicable to learned components but remains
applicable to the cage. The asymmetry is consistent with the Class I/II
distinction in ISO/IEC TR 5469:2024. The statistical characterisation is
inspired by QED (Gao et al., 2021) and *Behavior Metrics* (Paniego et
al., 2024), open instruments for quantitative evaluation.

**Consequences.** Two evaluation suites are produced:
`tests/cage/test_rules.py` (deterministic, executable in CI) and Chapter
8 as a structured Policy Behavioral Evaluation. Definitive adoption of
QED as official metric is deferred to Phase 4 (D-17).

**References.** Gao et al. (2021); Paniego et al. (2024); ISO/IEC TR
5469:2024.

---

### D-09 — A3: New transversal Runtime Monitoring level

| Field | Value |
| --- | --- |
| Section | §3.4.3 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** A horizontal level —*Runtime Monitoring*— is added to the
adapted V-Model, represented as a transversal band beneath the V (not as
a sub-level hanging from the implementation vertex). The level is fed by
cage intervention logs during operation and feeds back to higher
validation levels (L1' and, eventually, L2 when unanticipated hazards
emerge).

**Alternatives considered and rejected.** Extended right arm of the V in
the style of Wang et al. (2024) (rejected: breaks the visual symmetry of
the V, hinders readability). Closed feedback loop external to the V
(rejected: graphically denser, requires explicit legend). Not adding A3
and leaving monitoring as a generic recommended practice (rejected: turns
runtime monitoring into an intention rather than an auditable level of
the cycle).

**Rationale.** Static validation is insufficient for systems operating
in environments not completely specified (SOTIF philosophy, ISO
21448:2022). Runtime monitoring elevates this philosophy from recommended
practice to explicit architectural level of the lifecycle. A direct
technical antecedent is found in Mohseni et al. (2019), who conceptualise
the *monitoring function* as an architectural category in its own right
and review three families of techniques to implement it (uncertainty
estimation, in-distribution error detectors, OOD detectors). The
reformulation of the V-Model with a continuous operation phase by Wang
et al. (2024) and Ullrich et al. (2025) reinforces the direction.

**Consequences.** The Logger Node of the ROS2 architecture (Chapter 5)
is the primary instrument of A3, not an auxiliary component. Chapter 10
incorporates the concept of "continuous validation as partial substitute
for complete static validation". The initial version of the framework
is bounded to a rules-based cage plus aggregated logging; incorporating
uncertainty or distribution detectors remains a natural extension line
(Chapter 12).

**References.** Mohseni et al. (2019); Wang et al. (2024); Ullrich et al.
(2025); ISO 21448:2022.

---

### D-10 — A4: Bidirectional traceability as hard constraint enforced by tooling

| Field | Value |
| --- | --- |
| Section | §3.4.4 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** Bidirectional traceability H↔SR↔C↔SC↔M is a hard
constraint, not a good practice. Every cage rule must be traced to SRs;
every SR to hazards or an explicit accepted-risk argument; every scenario
to SRs; every metric to SRs. An automated script
(`check_traceability.py`) runs on every commit and daily, failing if it
detects orphans in any direction.

**Alternatives considered and rejected.** Traceability as documentary
good practice in the AMLAS style (Paterson et al., 2025), rejected
because it depends on manual reviews auditable a posteriori, which is
infeasible to guarantee in an individual thesis. Partial traceability
only from SRs to cage, rejected because it leaves the right branch of
the V without automated audit.

**Rationale.** In systems with learned components, the temptation to
attribute behaviours to "emergent properties" of learning is high.
Without strict automated traceability, any behaviour can be justified
retrospectively as "something the *policy* learned", which empties the
concept of engineering responsibility of content. The philosophy is
close to the GSN (*Goal Structuring Notation*) patterns of AMLAS but
goes one step further by turning traceability into a property
verifiable by automated tooling rather than reviewable documentary
practice.

**Consequences.** Phase 1 (HARA + SR) becomes simpler because it forces
the author to think "what cage rule am I going to have for this?" from
the very first SR. The result is more operational, less abstract SRs.
Two artefacts are produced: `traceability_matrix.csv` (living matrix)
and `check_traceability.py` (automated validator), plus Annex F as the
consolidated version at close.

**References.** Paterson et al. (2025) AMLAS; Koopman (2023) UL 4600.

---

### D-11 — A5: Bounded operational validation with explicit sim-to-real gap characterization

| Field | Value |
| --- | --- |
| Section | §3.4.5 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** Level L1' (Acceptance Testing) of the classical V-Model is
reformulated as **Operational Validation** with two mandatory
components: L1'-a (Scenario-Based System Validation, equivalent to
classical acceptance testing structured by scenarios linked to SRs, with
ODD coverage metrics in the line of De Gelder et al., 2024) and L1'-b
(Sim-to-Real Gap Characterization, explicit and empirical
quantification of the gap between training environment and operational
environment for each relevant metric and failure mode). The validation
conclusion is NOT "the system is safe" but rather "the system satisfies
the SRs under conditions of ODD X with a measured gap of Y with respect
to training conditions, and with the following residual risks
documented".

**Alternatives considered and rejected.** Keep L1' as binary acceptance
testing (rejected: implicitly assumes that testing conditions are
representative of operational ones, which is false for systems trained
in simulation). Qualitative validation without gap metrics (rejected:
incompatible with UL 4600's claim-argument-evidence principle).

**Rationale.** For a system trained in simulation, testing conditions
in simulation are not representative of physical operational conditions.
The gap is a first-order risk; an "acceptance test passed" in simulation
does not imply safe operation in the real world. Adaptation A5 makes
this bias visible and measurable. Consistent with SOTIF philosophy and
with the claim-argument-evidence principle of UL 4600.

**Consequences.** Chapter 9 is dedicated to the sim-to-real gap with
metrics M-T1 to M-T4 that quantify it. Chapter 10 issues a bounded
verdict with a residual risks table (Annex H). The choice of Gazebo as
simulator (D-12) makes this characterisation particularly relevant.

**References.** De Gelder et al. (2024); ISO 21448:2022; Koopman (2023).

---

### D-12 — Adopted simulator: Gazebo (supersedes CARLA in preliminary version)

| Field | Value |
| --- | --- |
| Section | §3.6.1 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) — internal review D9+ |
| Planned review | None (validated after comparative analysis) |

**Decision.** The adopted simulator is Gazebo (Koenig and Howard, 2004)
in its modern variant with native ROS2 integration, operated through a
gymnasium-Gazebo-ROS2 interface that reuses an environment previously
built by the author in earlier research work. This decision supersedes a
preliminary choice of CARLA registered in an initial version of Chapter
3 and requires updating all simulator mentions in Chapters 1, 2, and 3.

**Alternatives considered and rejected.** **CARLA** (Dosovitskiy et al.,
2017): strongest candidate and dominant choice in recent autonomous
driving research; offers superior sensor fidelity and a mature benchmark
ecosystem; rejected because it requires a ROS2 bridge with its own
complications, does not allow reuse of the author's prior work, and its
higher compute cost is an operational drag. **Highway-Env** and other
Gym-derived environments (no realistic sensors, abstract observation
space, not suitable for camera-based policies). **LGSVL** (project
discontinued in 2022, ecosystem in decay). **AirSim** (aerospace focus,
secondary automotive support, development on hold).

**Rationale.** Four reasons articulated in §3.6.1: native ROS2
integration without intermediate bridge layers, which reduces the
failure surface and improves the reliability of the M-I integration
metrics; reuse of the author's prior work, consistent with the *design
science* approach (the contribution is not in the simulator but in the
framework); availability of the gymnasium-Gazebo-ROS2 interface that
cleanly separates algorithm, environment, and system, facilitating A1;
more modest compute requirements, relevant for an individual thesis
without access to dedicated infrastructure.

**Acknowledged trade-offs.** Visual fidelity inferior to that of the
Unreal Engine motor underlying CARLA (consequence: the sim-to-real gap
may be more pronounced in the camera's visual features; A5 makes this
effect visible and measurable). The specific autonomous-driving research
community uses CARLA predominantly, which limits the immediate
availability of reusable scenario libraries in Gazebo format
(consequence: the project's *scenario library* must be built explicitly
in Chapter 6).

**Consequences.** Chapters 1, 2, and 3 are updated consistently. QED
(Gao et al., 2021) becomes conceptual inspiration with weights to be
recalibrated (D-17), because its original calibration is on CARLA.
Chapter 12 includes as a natural extension line the replication of the
experiment on CARLA to compare gap magnitudes between simulators with
different visual fidelity.

**References.** Koenig and Howard (2004); Dosovitskiy et al. (2017) as
rejected alternative and as state-of-the-art reference in §2.4.

---

### D-13 — Middleware: ROS2 Humble distribution

| Field | Value |
| --- | --- |
| Section | §3.6.2 |
| Status | SUPERSEDED by D-61 |
| Date | D9 (Phase 0) |

**Decision.** ROS2 Humble distribution (LTS) as the communication
middleware between project nodes.

**Alternatives considered and rejected.** ROS1 Noetic (EOL in 2025, no
support successor; rejected). Proprietary middleware based on ZMQ or gRPC
(rejected: discards existing tooling, prohibitive development cost).

**Rationale.** ROS2 is the de facto standard in robotics research since
the ROS1→ROS2 transition around 2020. The publish/subscribe model fits
naturally with the cage's monitor-actuator architecture: the *policy*
publishes candidate actions, the cage subscribes, evaluates, and
publishes effective actions. Bag recording support allows implementing
the A3 Logger Node without additional code. The Humble distribution is
adopted for compatibility with the Gazebo version of the reused
environment (D-12) and with the SBC embedded in the physical car.

**Consequences.** The entire architecture of Chapter 5 is ROS2 from its
inception. Inspection tools (rqt, ros2 topic, ros2 bag) are usable as is,
without additional development.

**Supersession note (20.07.2026).** The ROS2 architectural choice remains, but
the distribution named here was a preliminary decision and was not the stack
used for implementation or evidence. D-61 records the realised Ubuntu 24.04 +
ROS2 Jazzy + Gazebo Sim Harmonic baseline.

---

### D-14 — Learning algorithm: PPO (*Proximal Policy Optimization*)

| Field | Value |
| --- | --- |
| Section | §3.6.3 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** PPO (Schulman et al., 2017) as the reinforcement learning
algorithm, implemented via Stable-Baselines3.

**Alternatives considered and rejected.** **SAC** (Haarnoja et al.,
2018): competitive in sample efficiency and hyperparameter robustness,
but its *off-policy* character makes the Training Spec less interpretable
—the notion of "which policy produced which experience" blurs in the
*replay buffer*— and its stochastic nature with *temperature tuning*
adds complexity to experimental design; rejected. **DDPG / TD3**:
deterministic *off-policy*, more unstable than SAC and superseded by it
in almost all benchmarks; rejected. **A3C / A2C**: less sample-efficient
and virtually abandoned in favour of PPO since 2018; rejected.

**Rationale.** Four reasons consistent with the methodological framework.
*Training stability*: the *clipped surrogate objective* limits update
divergence without requiring explicit KL constraint, which reduces
hyperparameter sensitivity and improves reproducibility —an important
property for an individual work with limited compute for exhaustive
*sweeps*—. *Training Spec interpretability*: being *on-policy*, the
hyperparameters have relatively direct semantic meaning (rollout size,
epochs per update, clipping ratio, entropy coefficient), which makes
writing the L4b Training Spec as a readable document easier. *Open-tool
support*: the Stable-Baselines3 implementation is mature and admits
direct integration with Gazebo through the gymnasium-Gazebo-ROS2
interface. *Compatibility with extensions*: if future iterations of the
thesis explored *constrained RL* (in the style of RECPO from Zhao et
al., 2024), PPO admits natural extension to CMDP.

**Consequences.** The Training Spec of Chapter 7 is readable for a
reviewer without deep RL training. The hyperparameters documented in
`training_specification.md` have meaning traceable to properties of the
training loop.

**References.** Schulman et al. (2017); Haarnoja et al. (2018) as rejected
alternative; Zhao et al. (2024) RECPO as future extension.

---

### D-15 — Technology stack: Stable-Baselines3 + PyTorch + pytest + Python 3.10+

| Field | Value |
| --- | --- |
| Section | §3.6.4 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** Project technology stack: Stable-Baselines3 as PPO
implementation; PyTorch as neural network backend; pytest as testing
framework for Cage Unit Tests (L4a' of the adapted V) and general
regression suite; Python 3.10+ with quality tooling ruff (linting), mypy
(type checking), and pre-commit (commit-time automation).

**Alternatives considered and rejected.** Stable-Baselines (v2) on
TensorFlow (rejected: community migrated to SB3/PyTorch). RLlib on Ray
(rejected: unnecessary complexity for an individual project). Standard
unittest (rejected: pytest has better ergonomics and fixtures).

**Rationale.** Tooling decisions well established in contemporary
research, all with auditable code. Stable-Baselines3 admits direct
integration with gymnasium-Gazebo-ROS2 (cf. D-12). PyTorch is the de
facto standard in recent research and has mature profiling tools.
pytest with fixtures simplifies the Cage Unit Tests of A2 (D-08).

**Consequences.** Project templates and CI/CD are built on this stack.
Project reproducibility requires documenting these dependencies in
`pyproject.toml` and pinning them in `requirements.lock`.

---

### D-16 — Physical platform: 1:14 scale radio-controlled vehicle

| Field | Value |
| --- | --- |
| Section | §3.6.5 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** 1:14 scale RC vehicle instrumented with monocular front
camera, IMU for attitude estimation, motor encoder for longitudinal
velocity, and SBC with ROS2 support for embedded compute.

**Alternatives considered and rejected.** 1:5 scale (rejected: dynamic
discrepancies dominant against simulation, higher cost, higher
operational risk). 1:1 scale (rejected: prohibitive cost, operational
risk, legal requirements outside the scope). 1:24 scale or smaller
(rejected: dynamics too distant from a real car to be informative about
the sim-to-real gap).

**Rationale.** Three reasons articulated in §3.6.5. *Cost*: a 1:14 is
manageable, parts are affordable, and the operational damage risk is
bounded. *Operational safety*: low speeds, low kinetic energy,
negligible third-party risk on a closed track. *Simulation
transferability*: the dynamics of a 1:14 admit reasonable approximation
in Gazebo through a plugin-based model with adjustable parameters (mass,
load distribution, tyre friction, actuation parameters), while larger
scales would introduce dynamic discrepancies that would dominate the
sim-to-real gap.

**Consequences.** Detailed specifications (motor, ESC, low-level
controller, camera, compute platform) are documented in Chapter 5 and
the corresponding Annex. The sim-to-real gap characterised in Chapter 9
is specific to this scale and not directly extrapolable to larger scales;
this limitation is declared explicitly in §3.9 and discussed in Chapter
12.

---

### D-17 — QED deferred to Phase 4: conceptual inspiration with calibration pending

| Field | Value |
| --- | --- |
| Section | §3.6.6 |
| Status | DEFERRED |
| Date | D9 (Phase 0) |
| Planned review | Phase 4 (when the trained *policy* and a reference set of human evaluations are available) |

**Decision.** The composite QED metric (Gao et al., 2021) is considered
as *conceptual inspiration* of the project: a metric calibrated against
human evaluators for autonomous driving tasks. Direct adoption requires
nuance because QED was developed and calibrated on CARLA, while the
adopted simulator is Gazebo (D-12); the conceptual formula can transfer,
but the calibrated weights would need to be recomputed for the
*lane-following* scenario in Gazebo to obtain a metric with equivalent
meaning. Behavior Metrics (Paniego et al., 2024) is considered as an
auxiliary quantitative evaluation tool, given that its design is
relatively agnostic to the underlying simulator. The decision on
definitive adoption as the project's official metric is deferred to
Phase 4.

**Rationale.** It is not appropriate to commit to a metric calibrated on
another platform without verification. Deferring allows taking the
decision when the trained *policy* and a reference set of human
evaluations on the actually adopted simulator are available.

**Consequences.** Chapter 4 defines the project's official metrics
(M-P, M-S, M-I, M-C, M-T) without committing to QED as mandatory. Phase
4 retakes the decision and either confirms it or replaces it with a
proprietary composite metric with explicit calibration.

**References.** Gao et al. (2021); Paniego et al. (2024).

---

### D-18 — Documentation in plain-text Markdown (no industrial MBSE)

| Field | Value |
| --- | --- |
| Section | §3.6.7 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |

**Decision.** All project artefacts —documents, code, templates,
traceability matrix, validation scripts— live in a single Git repository
in plain-text format. Markdown with minimal extensions: citations in
`Author (year)` format, LaTeX equations, figures as SVG/PNG in dedicated
folder. Industrial MBSE tools (Cameo, Capella, or similar) are NOT
adopted.

**Alternatives considered and rejected.** SysML + industrial MBSE in the
style of Sprockhoff et al. (2023), rejected for significant cognitive
and economic cost, licences inaccessible for an individual thesis,
negative ROI in a single-author project. Documentation in Word/Google
Docs, rejected because it is not granularly versionable, not
line-auditable, not integrable with CI/CD.

**Rationale.** The repository *is* the project. An individual thesis
obtains a better cost/benefit ratio with versioned text files,
maintaining functional equivalence in terms of traceability (via
`traceability_matrix.csv` + `check_traceability.py`, cf. D-10) and
consistency (via automated peer review on each commit). Conjecture,
declared in §3.6.7: scaling the framework to a medium-sized industrial
team would motivate the move to MBSE.

**Consequences.** All the traceability of D-10 is materialised in text
files plus a Python script. Diagrams are kept as editable SVG. The
thesis is fully reproducible from the repository: anyone with Git and a
text editor can inspect the entire work.

**References.** Sprockhoff et al. (2023) as explicit contrast.

---

### D-19 — Five meta-evaluation criteria for the framework

| Field | Value |
| --- | --- |
| Section | §3.7 |
| Status | CONFIRMED |
| Date | D9 (Phase 0) |
| Planned review | Chapter 11 (application of criteria at the close of the work) |

**Decision.** The framework itself is evaluated at the close of the work
(Chapter 11) through five meta-criteria with concrete indicators.
*Traceability integrity*: number of orphans in the last execution of
`check_traceability.py`; success criterion: zero. *SR coverage by
experimental evidence*: percentage of SRs with a pass/fail verdict
backed by quantitative evidence; success criterion: 100% with verdict,
even if fail. *Hazard anticipation degree*: proportion of hazards
anticipated in HARA versus unanticipated ones that emerge in operation.
*Adoption cost*: time spent on framework artefacts versus pure
technical artefacts, recorded in this DECISIONS.md. *Matrix
productivity*: number of technical changes whose impact analysis was
accelerated by traceability.

**Alternatives considered and rejected.** Binary evaluation of the
framework "worked / did not work" (rejected: low granularity, loses
information about which parts worked). Single quantitative evaluation
NPS-type or equivalent (rejected: the framework is not a commercial
product). Purely qualitative evaluation (rejected: does not admit clear
refutation, vulnerable to author bias).

**Rationale.** A successful methodological framework applied to a modest
system, and a brilliant system produced in spite of the framework, are
two distinct outcomes that must be distinguishable. The five criteria
separate framework efficacy from technical system efficacy. Consistent
with design science research (D-05): evaluation of the artefact is
distinct from evaluation of its application.

**Consequences.** Chapter 11 retakes the five criteria and issues a
grounded verdict on each. This DECISIONS.md serves as the measurement
instrument for adoption cost (criterion 4): each added decision
documents time invested in framework versus time invested in technique.

---

### D-25 — Non-cage mitigations are first-class implementation types

| Field | Value |
| --- | --- |
| Section | §4.6 (SR implementation taxonomy) |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** A safety requirement may declare its implementation via one of three mechanisms: (a) a numbered cage rule `C-XX`; (b) a *training constraint* — typically a reward-shaping term tuned during policy training; or (c) a *cage architecture property* — a structural invariant of the cage pipeline (e.g., joint-envelope assertion, oscillation monitor) that is not itself a numbered rule. The machine-readable hazard and SR tables surface this distinction in the `implementation_type` column; `check_traceability.py` recognises all three as valid implementations.

**Alternatives considered and rejected.** Forcing every SR to be implemented by a numbered cage rule, rejected because H-08 (reward exploitation) has its root cause in the training reward and not in any runtime command — mitigating it with a cage rule would be orthogonal to the cage's design philosophy of *correcting unsafe commands* rather than *injecting progress* or *replacing intent*. Treating the cage architecture property of H-09 (composition consistency) as a new C-07, rejected because it is not a per-cycle rule with observed variable and correction strategy but a structural assertion over the existing six rules' joint behaviour.

**Rationale.** Hazards that arise from training pathologies (H-08) or from rule-composition effects (H-09) do not admit per-cycle reactive mitigation. Forcing them into the cage-rule mould either fabricates artificial rules with degraded semantics, or hides the mitigation in implicit assumptions. The three-way taxonomy makes the location of each mitigation explicit and auditable.

**Consequences.** SR-009 declares `implementation_type = training`; SR-010 declares `implementation_type = arbiter`; SR-011 splits across `C-06 + training`. The cage specification (`docs/04_cage_specification.md`) gains a non-numbered §Joint-envelope assertion section. The Training Specification (Phase 3, not yet written) acquires reward-design requirements traceable from SR-009 and SR-011.

---

### D-26 — Severity homothety convention (analogue real-vehicle interpretation)

| Field | Value |
| --- | --- |
| Section | §4.4.2 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** Severity ratings in the Hazard Register use the *analogue real-vehicle interpretation*: each hazard is rated as if the function under demonstration were deployed on a full-scale road vehicle carrying humans, not at the 1:14 scale at which the CobraFlex experiment runs. A hazard such as H-01 (lateral lane exit) is rated S=3 because lane departure on a real road can produce a fatal collision, even though the scaled platform itself cannot physically harm anyone.

**Alternatives considered and rejected.** Rating each hazard at the actual scale of the experiment (1:14, harmless platform), rejected because it would produce a HARA dominated by S=1 hazards, eliminating the analytical pressure that justifies the cage's existence and breaking the conceptual mapping with ISO 26262 automotive practice — the rating would no longer be interoperable with the safety vocabulary used by evaluators.

**Rationale.** The HARA is at the service of the methodology, not of the platform. The contribution of the thesis is the adapted V-Model applied to a lane-following case study whose safety properties stand in for the safety properties of a full-scale system. Honest rating under the analogue interpretation, with the convention documented as a limitation (§4.9), is preferable to rating that produces methodologically uninformative levels.

**Consequences.** All S/E/C ratings in `docs/02_hazard_register.md` are written under this convention; the convention is documented in the §Rating scales section of that file and discussed as a limitation in §4.9 of the manuscript. Any future replication on a full-scale vehicle would reuse the same Hazard Register entries with the convention naturally satisfied.

---

### D-27 — Selective STPA-light pass instead of full STPA

| Field | Value |
| --- | --- |
| Section | §4.5 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** The thesis applies a *STPA-light* pass — the four canonical UCA categories (action not provided when needed; action provided when not needed; action provided with inappropriate magnitude; action provided at the wrong time) systematically over the two principal control actions (steering, throttle) — to a selected subset of hazards (H-01, H-02, H-04), rather than performing a complete STPA over the entire system control structure.

**Alternatives considered and rejected.** Full STPA covering all hazards and the full hierarchical control model, rejected because the marginal informational return on hazards H-03, H-05, H-06, H-07 is low (their causal structure is sufficiently localised — speed ceiling, rate limiter, state-validity triggers, stop mechanism — that the UCA perspective adds no actionable insight). Omitting STPA entirely, rejected because the unsafe-control-action perspective adds value specifically for hazards driven by the policy's control actions (H-01, H-02) and for hazards where action mitigation collapses into substitution (H-04).

**Rationale.** The added value of STPA over HARA is concentrated in hazards whose causal structure is *systemic* rather than *localised*. Investing analytical effort uniformly across all hazards would dilute the benefit and inflate the analysis cost without proportional improvement in coverage. Restricting to H-01, H-02, H-04 captures the principal STPA findings (UCA enumeration, trigger persistence in H-04, asymmetric reset in H-04) without committing to a full hierarchical control model that the thesis scope does not require.

**Consequences.** §4.5 of the manuscript documents the scope decision explicitly; H-03, H-05, H-06, H-07 are listed as out-of-scope with rationale. H-08 (training-time pathology) and H-09 (composition hazard) are also excluded from STPA scope on structural grounds: H-08's causal mechanism is not a control-action defect, and H-09 is a composition-level hazard whose treatment lives at the cage-architecture level. The limitation is registered in §4.5.3 and reflected in the "STPA scope statement" of `docs/02_hazard_register.md`.

---

### D-28 — SR-CL-A requires a deterministic cage rule in the C-01..C-06 range

| Field | Value |
| --- | --- |
| Section | §4.7.1 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** Every Safety Requirement classified as SR-CL-A (highest criticality) must be implemented by at least one deterministic cage rule in the C-01..C-06 range of the Cage Specification. SR-CL-B may admit looser implementation strategies (monitoring with flag emission rather than command override); SR-CL-C accepts soft mitigations.

**Alternatives considered and rejected.** Allowing SR-CL-A implementation by training constraints alone, rejected because training constraints are statistical and policy-dependent — they cannot guarantee per-cycle satisfaction. Allowing SR-CL-A implementation by runtime monitoring alone, rejected for the same reason: monitoring detects violations but does not prevent them. A deterministic cage rule is the only mechanism that can claim per-cycle enforcement.

**Rationale.** Criticality is a statement about the consequence of violation, not about the difficulty of implementation. SR-CL-A by construction reflects hazards whose violation cannot be tolerated even in rare cases (S ≥ S3, or E ≥ E3 paired with C ≤ C2). A non-deterministic mitigation strategy is incompatible with that intolerance. The cage rules in C-01..C-06 are designed precisely as deterministic per-cycle enforcers and are the appropriate implementation mechanism for SR-CL-A.

**Consequences.** SR-001..SR-008 (mostly SR-CL-A) map to C-01..C-06 deterministic rules. SR-009 (SR-CL-B, training) and SR-010 (arbiter property) are exempt from this requirement by their non-SR-CL-A classification, as documented in §4.7.1 and consistent with D-25's three-way implementation taxonomy.

---

### D-29 — SR-CL-A requires ≥25 runs per scenario family for statistical discrimination

| Field | Value |
| --- | --- |
| Section | §4.7.1 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** A Safety Requirement classified as SR-CL-A must be verified in at least one nominal scenario family and at least one adverse scenario family, with a minimum of twenty-five independent runs per family for the resulting verdict to be considered statistically discriminating. SR-CL-B accepts ten runs per family; SR-CL-C accepts informal evidence.

**Alternatives considered and rejected.** Uniform sample sizes across all criticality levels (e.g., ten runs everywhere), rejected because the verdict on a SR-CL-A requirement carries higher consequences than on a SR-CL-B and warrants tighter statistical bands; conversely, demanding ≥25 runs for SR-CL-C would inflate the experimental campaign without proportional benefit. Setting the threshold by formal power analysis on each metric, rejected for F1 closure because the metrics' empirical distributions are not yet known; the ≥25 default is a conservative placeholder that can be tightened in Phase 4 if the data warrants.

**Rationale.** Twenty-five runs is the conventional lower bound at which 95 % confidence intervals on a binomial outcome have width comparable to the effect sizes of interest in this domain (cf. Paniego et al., 2024 for related sample-size conventions in scaled-vehicle benchmarking). It is large enough to surface rare-failure modes that ten-run campaigns systematically miss, and small enough to keep the Phase 4 simulation budget tractable given the scenario library size.

**Consequences.** The Phase 4 scenario campaign budget is determined by this convention: |SR-CL-A| × |nominal families| × 25 + |SR-CL-A| × |adverse families| × 25 + |SR-CL-B| × 10. The convention is referenced from the Phase 4 plan and from the verdict-aggregation logic of Chapter 10. Failure to reach the run count for any SR-CL-A blocks the global verdict.

---

### D-30 — A negative verdict on any SR-CL-A invalidates the global verdict

| Field | Value |
| --- | --- |
| Section | §4.7.1 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** A negative verdict on any single SR-CL-A in the Phase 4 / Phase 5 verification campaign invalidates the global verdict of the thesis on the system, regardless of how many other SRs are satisfied. The global verdict can only read "satisfied" if every SR-CL-A is satisfied; SR-CL-B and SR-CL-C verdicts contribute nuance but not vetoes.

**Alternatives considered and rejected.** Verdict-by-majority across all SRs, rejected because it would allow a critical safety failure on a SR-CL-A to be diluted by success on lower-criticality SRs — exactly the failure mode that the criticality classification is designed to prevent. Verdict-by-weighted-average across all SRs, rejected for the same reason and additionally because the weighting choice would be arbitrary.

**Rationale.** Criticality classification's only operational meaning is differential consequence: SR-CL-A failures matter categorically more than SR-CL-B or SR-CL-C failures, and the verdict logic must reflect that. A veto rule on SR-CL-A is the only logic that preserves the semantic intent of the classification. The thesis prefers honest local failure to inflated global success.

**Consequences.** Chapter 10's verdict-aggregation logic implements the veto. If a SR-CL-A verdict is negative, the thesis reports the negative outcome explicitly in the Limitations chapter and discusses its consequences for the methodological claim, rather than claiming a partial success. This convention aligns with the "honest verdict" principle of A5 (D-11) and with the meta-evaluation criteria of D-19.

---

### D-31 — Deliberate exclusion of non-functional AI-specific hazard families

| Field | Value |
| --- | --- |
| Section | §4.9 |
| Status | CONFIRMED |
| Date | F1 (13.05.2026) |

**Decision.** The F1 Hazard Register deliberately excludes five families of AI-specific hazards that are out of scope for this thesis: adversarial attacks on the perception or policy networks; distribution shift in the policy's input space; insufficient explainability of policy decisions; biases in the training dataset; brittleness to low-magnitude perturbations on otherwise nominal inputs. These families are acknowledged as legitimate hazards in the recent AI safety literature (Wang et al., 2024; Wäschle et al., 2022) but are documented as scope exclusions rather than addressed by SRs.

**Alternatives considered and rejected.** Attempting to cover the full AI-hazard taxonomy of Wang et al. (2024), rejected because each family requires distinct analytical machinery (adversarial robustness analysis, drift detection, interpretability tooling, dataset audit) whose effort is comparable to the entire current scope of the thesis. Silently omitting these families, rejected because the omission would surface at evaluation time as an unacknowledged limitation. The chosen middle ground — explicit registration as scope exclusions with literature citation — is honest about coverage without inflating effort.

**Rationale.** The thesis contribution is the methodological framework, demonstrated on a bounded lane-following case. Generalisation to the full AI-hazard space is a research agenda in itself and is acknowledged in Chapter 12 as future work. The exclusion preserves analytical depth on the hazards that are in scope, which is preferable to shallow treatment of a larger set.

**Consequences.** §4.9 of the manuscript declares the limitation and references this decision. Chapter 12 mentions the families as natural extension axes. The argument of relative completeness in §4.7.2 explicitly says "relative to the bounded scope" and not "absolute", with this decision as the principal qualifier.

---

### D-32 — ROS2 workspace integrated under `src/` by fresh copy

| Field | Value |
| --- | --- |
| Section | infrastructure (not a manuscript section) |
| Status | CONFIRMED |
| Date | F1 (14.05.2026) |

**Decision.** The ROS2 packages of the simulator and physical-platform stack —previously developed by the author in `E:\CAST\Cobra Flex Drivers & SW\src`— are integrated into this repository under a top-level `src/` directory following the canonical colcon workspace layout. Two of the author's own packages are tracked: `src/cobraflex` (URDF/SDF, launch files, perception nodes, configs) and `src/cobraflex_rl` (RL training infrastructure, gymnasium-Gazebo-ROS2 interface). Two third-party driver packages —`sllidar_ros2` (Slamtec) and `zed-ros2-wrapper` (Stereolabs)— are deliberately **not** brought into this repository; they are deferred for a later decision on whether to add them as git submodules pinned to specific upstream commits or to manage them via `rosdep`.

The copy is a *fresh* copy (no `git subtree` / no preserved upstream git history); the prior repo remains the canonical history for pre-thesis development and is referenced by path in this decision and in the CHANGELOG entry of the integration commit.

**Alternatives considered and rejected.** *Git submodule of the entire prior repo*, rejected because the prior repo mixes the author's own work with several third-party driver checkouts; vendoring those drivers as nested submodules would force the supervisor to run `git submodule update --init --recursive` and would risk silent breakage when upstream pushes incompatible changes. *Git subtree*, rejected for the same reason plus the operational friction of subtree pull/push for an evaluator who is not expected to be git-savvy. *Keep src/ outside the repo and document the path*, rejected because thesis reproducibility benefits from a single `git clone` producing a buildable workspace.

**Rationale.** A thesis repository is a one-shot reproducibility artefact, not a living monorepo. Optimising for "supervisor clones once, builds once, runs" outweighs the value of preserving granular pre-thesis git history. Third-party drivers are deferred because they may or may not be needed depending on which physical-platform experiments end up in scope; pulling them in now would add ~150 MB of upstream code that the thesis does not modify.

**Consequences.** The repository grows from ~52 KB to roughly 110 MB, dominated by `src/cobraflex/meshes/rplidar-a2m4-r1.stl` (87 MB visualisation mesh; the actual cobraflex work is < 25 MB). `pytest` discovery is constrained to `cage/tests` via a new `pytest.ini` at the root so that the ament_python tests under `src/cobraflex/test/` do not pollute the safety-side test suite (they require `ament_pep257`/`ament_flake8`/`ament_copyright` which are part of the ROS2 toolchain and not in the safety-side dev environment). `.gitignore` is extended with per-package ROS2 patterns (`src/*/build/`, `src/*/install/`, `src/*/log/`, and generated msg/srv bindings). The 87 MB mesh is acceptable for now but flagged as a candidate for Git LFS migration before publishing the repository externally; if the supervisor wants a leaner clone, the mesh can be replaced by a `scripts/download_meshes.sh` download stub.

---

### D-33 — Phase 1 closes 3 of 12 ODD-Spec TBDs; the remaining 9 are explicitly deferred per phase

| Field | Value |
| --- | --- |
| Section | §11 of `docs/08_odd_specification.md` |
| Status | CONFIRMED |
| Date | F1 (14.05.2026) |

**Decision.** The Phase 1 closure of `docs/08_odd_specification.md` resolves three of the twelve TBD-Q* placeholders against the actual configuration of the `src/cobraflex` and `src/cobraflex_rl` workspace; the remaining nine are explicitly deferred to later phases with a per-TBD rationale. The deferral is permitted by the closure criterion of `experiments/odd_inspection/README.md`, which accepts a mixture of resolved and explicitly-deferred TBDs at Gate G1 provided that each deferral is registered as a decision.

| TBD | Resolution path | Phase |
| --- | --------------- | ----- |
| Q1 FRICTION | Resolved: 1.0 (Gazebo ODE default, `<friction><ode/></friction>` in all current worlds) | F1 |
| Q2 A_LAT_MAX (ODD-1) | Resolved: 9.81 m/s² (derived: Q1 × g) | F1 |
| Q3 CORRIDOR_EDGE | Resolved: 0.1225 m (= LANE_EDGE; `gazebo_lane_env.py` terminates at the geometric lane edge with no separate margin) | F1 |
| Q4 odd2_nominal_adverse | **Resolved at F4 entry (03.06.2026):** σ_lateral=0.03 m + faded-marking/non-uniform-light world; spec in `src/cobraflex_rl/config/adverse_profiles.yaml`, mirrored in ODD-Spec §5.5. | F4 ✔ |
| Q5 odd2_adverse_with_latency | **Resolved at F4 entry (03.06.2026):** +100 ms latency (SC-PERT-02 high) / 20 ms jitter / 0.02 steer actuation noise; `adverse_profiles.yaml`. | F4 ✔ |
| Q6 odd2_adverse_with_obstacle | **Resolved (spec) at F4 entry (03.06.2026):** 1 static 0.10 m box, ~0.05 m lane intrusion at mid-straight; `adverse_profiles.yaml`. **Execution deferred** — the 6-dim obs has no obstacle channel (§5.1 specifies 8-dim), so the campaign skips it until obstacle perception is wired. | F4 ✔ (exec deferred) |
| Q7 odd2_adverse_full | **Resolved at F4 entry (03.06.2026):** union of Q4 + Q5 + Q6 (`adverse_profiles.yaml`); inherits Q6's execution deferral. | F4 ✔ |
| Q8 ROAD_LENGTH (ODD-3) | **Deferred to F2 / F3**: the `odd3_curvy_loop` world is not yet implemented in `src/cobraflex/worlds/` (only `empty.world`, `obstacles.world`, `test_world.sdf` exist; the current centerline is a 3 m straight). | F2/F3 |
| Q9 KAPPA_MAX (ODD-3) | **Deferred to F2 / F3**: depends on the same `odd3_curvy_loop` world being built; cross-validated against M-4 once both are available. | F2/F3 |
| Q10 A_LAT_MAX (ODD-3) | **Deferred to F2 / F3**: derived from Q1, V_MAX_CURVE, and Q9; closes when Q9 closes. | F2/F3 |
| Q11 STUCK_TIMEOUT | **Deferred to F2 / F3**: declared as `n/a` for ODD-1 and ODD-2 in the master parameter table; only relevant for ODD-3 and ODD-4, which are deferred. The current env wrapper does not implement an explicit stuck criterion (only `max_episode_steps × control_dt = 50 s` truncation, raised from 40 s in F3 when `max_episode_steps` went 400→500), so when ODD-3 is built either the env wrapper acquires a stuck check or Q11 stays "n/a — subsumed by truncation". | F2/F3 |
| Q12 ODD-4 stressors | **Resolved at F4 entry (03.06.2026):** ODD-4 adds no stressor beyond ODD-2 — it is the pure cross-product of ODD-3 geometry × ODD-2 stressors (ODD-Spec §7.1; `adverse_profiles.yaml` odd4_profiles). | F4 ✔ |

**Alternatives considered and rejected.** *Block G1 until all 12 TBDs are closed*, rejected because nine of the TBDs depend on artefacts that the project plan does not produce until F2-F4: the ODD-3 curvy world (F2 cage testing or F3 scenario library), and the ODD-2/ODD-4 stressor profiles (F4 scenario library). Demanding their closure at F1 would either force premature design choices on artefacts that should be informed by F2-F3 results, or invent placeholder values whose only justification would be "to close the row in the table". Either path degrades the engineering quality of the TBD closure. *Resolve the deferred TBDs with placeholder values "to be revised"*, rejected for the same reason. *Drop the deferred TBDs from the ODD-Spec entirely*, rejected because the master parameter table needs the cell references in ODD-2, ODD-3, ODD-4 columns even if the values are not yet known; replacing them with "?" would lose the explicit traceability of which downstream parameter expects which upstream value.

**Rationale.** Each deferred TBD is closed at the phase where its source artefact is first produced. This aligns the ODD-Spec maturation with the V-Model adaptation: Q4-Q7, Q12 close at F4 entry alongside the Scenario Library (level L2'); Q8-Q11 close at F2/F3 entry alongside the curvy-world implementation. The ODD-Spec moves from version 0.1 (draft) to 0.2 (F1 close, three TBDs resolved) to 0.3 (F3 close, ODD-3 TBDs resolved) to 1.0 (F4 close, all TBDs resolved, signed off at G4). This per-phase progression is consistent with the "version increments per change" convention declared in the ODD-Spec cover block.

**Consequences.** `experiments/odd_inspection/odd_tbds.yaml` is committed with Q1/Q2/Q3 populated and the remaining nine entries left with `value: null` plus the rationale strings in their `notes:` field referring back to this decision. `tools/close_odd_tbds.py --apply` patches the ODD-Spec to substitute the three resolved TBDs into the body and into §11; the remaining `TBD-Q4..Q12` literals stay in the document and re-running the script after later closures is idempotent. The ODD-Spec is bumped from v0.1 to v0.2 with the closure log entry referencing this decision. M-4 (which depends on the `odd3_curvy_loop` map) inherits the deferral: it cannot run at F1 and is re-scheduled together with ODD-3 closure.

**Status update (F4 entry, 03.06.2026).** Q4–Q7 and Q12 are now **resolved** (table above), leaving only Q10 (A_LAT_MAX ODD-3, deferred to M-4 physical calibration). The F4 closures were applied **by hand** to `docs/08` (§5.5, §7.2, §11, cover block), **not** via `close_odd_tbds.py --apply`: contrary to the idempotency note above, the tool's blanket `TBD-QN` regex substitution would now clobber the *prose mentions* of already-closed TBDs in the §0.1 change log ("F1 partial closure of TBD-Q1…") and the §9 source column ("closes TBD-Q8"). `experiments/odd_inspection/odd_tbds.yaml` is kept in sync as the provenance record. Hardening the tool to skip prose mentions / a fenced placeholder region is tracked as a separate follow-up.

---

---

### D-34 — Cage active in enforcement mode during PPO training

**Context.** The PPO training loop (`GazeboLaneEnv.step`) needs to decide
whether to route actions through the safety cage or bypass it entirely.
Two strategies are viable:

- **Strategy A — Cage offline:** training env publishes directly to
  `/cmd_vel`; cage is only active at evaluation time. Simpler to implement
  (no extra ROS2 synchronisation in the training loop), but the policy
  learns a distribution of states that excludes cage interventions, which
  may cause the policy to be over-confident near cage activation boundaries
  during deployment.
- **Strategy B — Cage in the loop:** training env publishes raw actions to
  `/raw_action`, subscribes to `/safe_action`, and passes the *caged* action
  to the vehicle. The policy learns under the actual deployed envelope.
  Reward is computed on the post-cage action (or optionally on both), which
  makes the reward design more complex but aligns training with deployment.

**Decision.** **Strategy B** — cage in enforcement mode during training —
is the F3 default, consistent with `policy/README.md` ("The cage is active
during training in enforcement mode by default") and with the traceability
chain SR-009 → Training Specification requirement that the policy is
evaluated under the same constraints as deployed.

The intervention of the cage during training is treated as part of the
environment dynamics, not as a penalty signal. The reward function sees the
*safe* action actually applied, not the raw action the policy requested; the
delta between raw and safe action is an optional auxiliary signal for
diagnostic logging only.

**Implementation (TS-01, in-process).** `GazeboLaneEnv` invokes the cage
**in-process** rather than over ROS2 topics: it constructs a
`cage.cage_node.SafetyCageNode` from the same `cage/cage.yaml` as deployment
and calls `SafetyCageNode.step(state, raw_action, ctx)` each control cycle —
the identical call `cage_ros_node` makes internally. Per cycle `step()`:
1. builds the cage `State` from the tracker output (mirroring
   `lane_perception_node`: `lateral_offset`, `heading_error`, `speed`,
   `curvature_ahead`, boundary distances against the road half-width),
2. forms `raw_action = (policy_steering, throttle_nominal)` (the policy
   controls steering only, §7.2.2),
3. calls `cage.step(...)` to obtain the safe action,
4. maps the safe `(steering, throttle)` to `/cmd_vel` by replicating
   `vehicle_control_node` (throttle→speed, `angular.z = steering·yaw_gain`,
   emergency→controlled stop),
5. computes the reward on the safe action and resulting state.
A fresh `SafetyCageNode` is created per episode so no latched C-05 emergency
or rate-limiter history leaks across the independent RL rollouts. The pure
(ROS-free) mapping glue lives in
`src/cobraflex_rl/cobraflex_rl/cage_bridge.py`.

**Why in-process, not the topic round-trip originally sketched.** The
training env is a synchronous `gym.Env` loop driving Gazebo directly; a
per-step publish-`/raw_action` / await-`/safe_action` handshake with a
separate `cage_ros_node` would inject asynchrony (harming determinism under
the fixed seed of §7.2.7), add latency, and require co-launching extra nodes.
The in-process call yields **byte-identical cage behaviour** (same class, same
YAML) while staying synchronous and deterministic, and needs no launch
changes — `train_lane.launch.py` already runs only Gazebo + `train_ppo`, the
env publishes `/cmd_vel` itself, so there is no `vehicle_control_node` to
co-launch and no double-actuation. This satisfies SR-009 (policy trained under
the deployed envelope) at the behavioural level, which is what the
traceability chain requires.

**Rationale (unchanged).** Deployment of a policy trained offline from the
cage would require post-hoc analysis of distribution shift at cage boundaries,
adding complexity at evaluation time. Training under the cage is the simpler
and more conservative choice: what the policy learns is what gets deployed.

**Status.** CONFIRMED and IMPLEMENTED (F3 task TS-01, in-process). Verified by
`policy/tests/test_cage_bridge.py` (mapping mirrors + a C-01 correction routed
through `SafetyCageNode`); end-to-end training-loop validation on the
Gazebo/Jazzy host is the F3 first-run task.

**F3 first-run refinements (01.06.2026).** End-to-end bring-up of the in-process
loop on the Gazebo/Jazzy host added three behaviours, none of which alters the
cage class or `cage/cage.yaml`:

- *Episode termination on C-05.* A latched C-05 emergency now ends the episode
  immediately (`terminated=True`, `info.termination_reason="cage_emergency"`):
  the policy reached a state the cage could only answer with an emergency stop,
  and the frozen remainder carries no learning signal (and previously burned the
  full horizon). Crucially, this termination is **penalty-free** — consistent
  with the D-34 principle that the cage's intervention is part of the dynamics
  and is *not* an explicit penalty signal: `compute_reward` receives
  `done=off_road`, so only a genuine off-road failure (which predates the cage
  in the loop) incurs the termination penalty, while a C-05 emergency simply
  ends the episode (the policy forgoes future reward, value bootstraps from 0,
  but is not punished). The corrective interventions C-01..C-04/C-06 likewise
  stay transparent. (Observed: ~every early-policy episode ends in C-05 at
  `|ey|≈0.16`, with C-01/C-02/C-03/C-06 firing throughout — confirming the cage
  is actively steering, not merely emergency-stopping.)
- *Spawn-pose settle.* `reset()` calibrates the odom→world offset against a
  wall-clock-settled post-teleport pose (`_calibrate_spawn_settled`) rather than
  immediately: a `set_pose` teleport reaches `/odom_truth` a few sim steps after
  the gz service returns, and calibrating against the stale pre-teleport sample
  injected impossible step-1 `ey` and degenerate 1-step rollouts.
- *Pacing.* Per-step waiting advances by simulation time (odom header stamps),
  keeping the control cadence correct if the sim runs faster than real time; the
  reset settle uses wall-clock. A `sim_real_time_factor` knob exists but is left
  at 1 (real-time) pending a safe faster-than-real-time path — a runtime
  `set_physics` unthrottle froze the sim (`real_time_update_rate=0`), so the
  world-file RTF (load-time) remains the open lever, deferred as it changes the
  world hash.

---

### D-35 — Frontier (out-of-ODD) scenario family as a non-verdict-bearing cage-efficacy contrast

| Field | Value |
| --- | --- |
| Section | `docs/05` (Frontier scenarios); manuscript §8.2.2–§8.2.3 |
| Status | CONFIRMED |
| Date | F4 (08.06.2026) |
| Planned review | None (scenario-family methodology decision) |

**Decision.** A fourth scenario family, **Frontier (SC-FRONT)**, is added to the
scenario library alongside Nominal / Edge / Perturbed. Frontier scenarios initialise
the vehicle **at or beyond the ODD-1 boundary** (`|ey| > 0.1225 m` and/or heading
beyond C-02's `θ_max = 25°`), where the lane-following policy is not designed to
recover — recovery is the cage's responsibility (C-01 / C-02 / C-05). They are
evaluated as a **paired enforcement-vs-monitoring contrast** on a dedicated harm-proxy
metric **M-S5 (road-edge departure)**, and their evidence is **explicitly excluded
from the global SR-verdict aggregation of D-30**: a frontier result never vetoes the
global verdict and never contributes a per-SR pass/fail. The measured cage benefit is
the counterfactual difference `M-S5(monitoring) − M-S5(enforcement)`.

**Alternatives considered and rejected.**
- *Fold the frontier scenarios into the EDGE family and the D-29/D-30 verdict.*
  Rejected: EDGE scenarios sit within or at the ODD boundary and carry pass/fail
  criteria the constraint-respecting policy is expected to meet; frontier starts are
  deliberately out-of-ODD, where the policy is *not* expected to recover, so a
  `fraction_pass` verdict on the policy would be ill-posed and a monitoring-arm
  "failure" (reaching the road edge) is the *intended* demonstration, not a defect.
  Aggregating that into D-30 would let a designed-for outcome veto the global verdict.
- *Demonstrate cage value only through the existing M-S2 enforcement-vs-monitoring
  delta on EDGE/PERT scenarios (§8.2.2).* Rejected as insufficient: inside the ODD the
  constraint-respecting policy rarely breaches the lane boundary, so the M-S2 delta is
  often null (the policy suffices) — precisely the defence objection of §7.5.2. A
  frontier family forces the regime where the cage's contribution is non-null and
  measurable.
- *Introduce a new hazard / SR / cage rule for road-edge departure.* Rejected: no new
  requirement is created — frontier scenarios verify the existing SR-001 / SR-002 /
  SR-005 / SR-007 / SR-008 (cage containment). M-S5 is a measurement instrument, and
  road-edge departure is a more severe instance of the already-registered H-01 / H-04.

**Rationale.** The thesis must answer the standing defence question "if the policy is
good, what is the cage for?" (§7.5.2, §8.2.2). Inside the ODD the honest answer is
often "nothing — the policy suffices"; the cage's value materialises only where the
policy leaves its design envelope. The frontier family constructs exactly that regime
and measures the cage's protective contribution as a clean counterfactual (same start,
cage enforcing vs cage observing-only). Keeping this evidence *out* of the D-30 verdict
preserves the semantic integrity of both: the global verdict stays a statement about
the policy+cage system *inside* its ODD, while the frontier contrast is a separate,
honest statement about the cage's marginal value *beyond* it (the H-04 cage-value
evidence).

**Consequences.**
- Six scenarios `SC-FRONT-01..06` are added under `scenarios/frontier/` and documented
  in `docs/05` (out-of-ODD pair 01–03; in-ODD-drift pair 04–06, where the cage responds
  graded rather than with an immediate stop). Scenario count 11 → 17; no new H/SR/C.
- One safety metric **M-S5 — Road-edge departure** is added to `docs/06`
  (`road_edge_contact = max|ey| ≥ road_half_m`), the per-run boolean behind the
  contrast, mirroring the M-S3/`emergency` event↔rate pattern; `max_excursion_m` is the
  realised value of M-S1.
- The frontier 6 × 25 × 2 = 300 runs are budgeted **separately** from the ~1100-run
  verdict-bearing campaign (D-29) and do **not** enter `traceability_matrix.csv` /
  `docs/07` verdict rows. The cage-benefit aggregation is produced by
  `tools/frontier_contrast.py`.
- The scenario validators (`check_scenario_yaml.py`, `check_traceability.py`) and
  `scenarios/_schema.yaml` recognise the FRONT family and the per-run bare tokens
  `road_edge_contact` / `max_excursion_m`.
- Reported in manuscript §8.2.2–§8.2.3 as the cage-value evidence. The full 25-rep study
  is pending on the Ubuntu+Jazzy host; a pilot (rep00, seeds 123 & 2024) exists under
  `experiments/sim/campaign_frontier`.

---

### D-36 — Seed policy for F4 campaigns: main seed 2024 certifies the verdict; cage-dependent seed 123 only in the frontier contrast

| Field | Value |
| --- | --- |
| Section | §7.5.3 (multi-seed selection); §8.2 (sim-eval campaign); `tools/run_campaign.py` seed axis |
| Status | CONFIRMED |
| Date | F4 (08.06.2026) |
| Planned review | None (campaign-methodology decision) |

**Decision.** The Phase-4 **verdict-bearing campaign** (D-29 run counts → D-30 global
verdict) is executed with the single G3-selected main policy **seed 2024** as the
certified configuration. The cage-dependent **seed 123** (58.8 % cage intervention,
§7.5.3) is run **only** in the D-35 **frontier** cage-efficacy contrast — where the
per-seed panels require it — and, optionally, in a separately-reported robustness sweep
with its own `--out` directory. Seed 123 is **never pooled into the D-30 verdict
aggregation**.

**Alternatives considered and rejected.**
- *Run both seeds (`--seeds 2024,123`) in the verdict-bearing campaign.* Rejected:
  `aggregate_campaign` (`tools/run_campaign.py`) groups per-run outcomes by
  `(scenario, mode)` and pools **all seeds and reps** into one `fraction_pass` per
  scenario. Seed 123's deliberately cage-dependent behaviour (it relies on the cage for
  58.8 % of steps) would therefore be averaged into the per-scenario verdict and could
  drag an SR-CL-A scenario below its pass threshold — vetoing the global verdict (D-30)
  on the basis of a policy the thesis did **not** select for delivery. The verdict must
  characterise the *certified* configuration.
- *Certify with seed 123, or re-open the main-seed choice here.* Rejected: at G3 seed
  2024 was fixed as the main run (best reward + PPO health; 4/5 seeds
  constraint-respecting, §7.5.3, Fig 7.8). The campaign executes that decision; it does
  not re-litigate it.
- *Drop seed 123 from F4 entirely.* Rejected: the D-35 frontier study is a **per-seed
  paired contrast** whose entire point is that a cage-dependent policy (123) is rescued
  by the cage in regimes where a constraint-respecting one (2024) needs no help.
  `tools/plot_frontier.py` renders one panel per seed and labels 123 explicitly as the
  "policy dependiente de la cage"; without 123 the cage-benefit figure loses its
  contrast and reduces to the null-delta objection of §7.5.2.

**Rationale.** Because the aggregator treats seeds and reps interchangeably as
"independent runs" for the D-29 count, the lever that controls *what the verdict
certifies* is simply **which seeds enter which campaign**. Keeping the two campaigns on
disjoint seed sets — verdict = {2024}, frontier = {2024, 123} — preserves the semantics
that D-30 and D-35 each established: the global verdict is a statement about the
*delivered* policy+cage system inside its ODD, while the frontier contrast is a separate,
honest statement about the cage's marginal value for a weak policy beyond it. The
separation needs no new code — only distinct `--out` directories (`campaign` vs
`campaign_frontier`), which the repo layout already provides.

**Consequences.**
- Verdict-bearing campaign: `--controllers rl --seeds 2024 --out experiments/sim/campaign`
  (the ~1260-run matrix reported by `--dry-run`), feeding the per-SR sim-verdict rows of
  `docs/07`.
- Frontier campaign: `--controllers rl --seeds 2024,123 --scenarios SC-FRONT-01..06
  --reps 25 --out experiments/sim/campaign_frontier`. The two-seed axis makes the
  realised budget `6 × 25 reps × 2 modes × 2 seeds = 600 runs` (D-35's "300" counted a
  single seed); the pilot already exercised both arms (rep00, seeds 123 & 2024).
- Any seed-123 data over the NOM/EDGE/PERT families is run under a separate `--out`
  (e.g. `experiments/sim/campaign_seed123`) and reported as a **secondary robustness
  sweep**, never merged into the D-30 aggregation that closes G4.
- No new H/SR/C/SC/M artefacts and no `traceability_matrix.csv` rows. Cites D-29, D-30,
  D-34, D-35.

---

### D-37 — F4 realises the ODD-1..4 stratification on a single oval world at a fixed-speed (ACT_DIM=1) operating point

| Field | Value |
| --- | --- |
| Section | `docs/08` §12 (single-world reconciliation); `docs/05` Track-mapping note; manuscript §8 / §1.6.3 / Cap. 11 |
| Status | CONFIRMED |
| Date | F4 (08.06.2026) |
| Planned review | F5 (physical ODD), or when a variable-speed `ACT_DIM=2` policy is trained |

**Decision.** The F4 **simulation** evaluation realises all four ODDs on the single oval
world `lane_following_oval.world` (preset `oval_R080`; *Option A* of the `docs/05`
Track-mapping note) at **one operating point** — fixed forward speed **0.2 m/s**,
**steering-only** action (`ACT_DIM = 1`), 6-dim observation, no obstacles. **ODD-1 and
ODD-2** are claimed **covered** (with the geometry/observation caveats of §12.2); **ODD-3**
is **partial** — its curve geometry is exercised (SC-NOM-02/03) but its defining
2-dimensional curvature-dependent speed envelope (`v_max(κ)`, `ODD-3.V_MAX_CURVE`) is not;
**ODD-4** (adverse × curvy) is **not exercised** (no scenario combines a curve start with
an adverse stressor). The ODD-spec parameters are **not** rewritten; `docs/08` §12 records
the evaluated subset and its gaps (append-only).

**Alternatives considered and rejected.**
- *Two worlds — ODD-1/2 on the dedicated straight, ODD-3/4 on the oval, as the spec
  geometry implies.* Rejected: the F3 policy and the F2 PD baseline were trained and
  validated on the oval only; a second world forces a parallel training+eval pipeline and
  breaks the RL↔PD comparison on identical geometry (Option A). The straight world is
  reserved for the F5 physical subset.
- *Descope ODD-3/ODD-4 to future work entirely.* Rejected: F4 does exercise the oval's
  curve geometry under the cage (SC-NOM-02 curve entry, SC-NOM-03 full loop), so a blanket
  descope understates the evidence. The honest position is ODD-3 partial + ODD-4 deferred,
  with the speed-envelope gap named.
- *Rewrite the ODD-spec numbers (ROAD_LENGTH, ACT_DIM, V_MAX) to match the oval operating
  point.* Rejected: `docs/08`'s own convention (§1 TEACHER NOTE) requires numerical
  authority to flow spec → evidence; editing the spec to fit the campaign would invert that
  and silently change the thresholds that SR-001 / SR-004 and Cage Rule C-04 cite.

**Rationale.** The ODD-spec defines the *intended* domain; the campaign samples a
sub-region of it. Conflating the two would either overstate coverage (claiming the 2-dim
ODD-3 envelope is validated) or corrupt the upstream thresholds. An append-only
reconciliation (§12) keeps the spec authoritative and the F4 coverage auditable — the same
honesty pattern as D-11 (bounded validation + explicit gap) and D-33 (TBDs closed/deferred
explicitly). The single-world choice is itself the RL↔PD-comparability decision (Option A);
D-37 records what that choice costs in ODD coverage so the G4 reviewer sees it stated, not
inferred.

**Consequences.**
- `docs/08` gains §12 (append-only): the ODD→oval realisation table (§12.1) and the
  declared coverage gaps (§12.2). Version 0.5 → 0.6. **No ODD parameter value changes.**
- The manuscript's ODD-coverage claim (Cap. 8) must read ODD-1/2 covered, ODD-3 partial,
  ODD-4 deferred, and report the fixed-speed / single-world gaps in Limitations
  (§1.6.3 / Cap. 11). *(Manuscript edit pending — see follow-up.)*
- A variable-speed (`ACT_DIM = 2`) policy that closes the ODD-3/ODD-4 speed envelope, and
  an adverse-curvy scenario for ODD-4, are future work (F5+).
- No new H/SR/C/SC/M artefacts and no `traceability_matrix.csv` rows. Cites D-11, D-33,
  D-34, D-35, D-36.

---


### D-38 — Indeterminate per-run verdicts are insufficient evidence, not failures (aggregator reconciliation)

| Field | Value |
| --- | --- |
| Section | §8.2 (sim-eval aggregation); `tools/run_campaign.py`; `docs/07` |
| Status | CONFIRMED |
| Date | F4 (10.06.2026) |

**Decision.** A per-run verdict of `None` (indeterminate — the run's pass-criterion
referenced a metric absent from the run-record schema, the criterion is not scorable
in the single-run evaluator, or the run errored) is **excluded from the denominator**
of a scenario's pass fraction and **propagated as `insufficient_evidence`**, never
collapsed into a failure. A scenario whose runs are *all* indeterminate has verdict
`None` (not `False`); an SR verified only by such a scenario reads
`insufficient_evidence`; and at the global level an under-evidenced **SR-CL-A** makes
the verdict `INCOMPLETE` rather than `NOT SATISFIED`. A *genuine* scenario failure
still dominates an indeterminate sibling (failed > insufficient). The two campaign
aggregators are reconciled to this single semantics: `tools/run_campaign.py`'s
`aggregate_scenario`/`aggregate_sr`/`global_verdict` now mirror the unit-tested
D-29/D-30 spine `src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py`.

**Alternatives considered and rejected.**
- *Keep the two aggregators as-is.* Rejected: `run_campaign.py` computed
  `fraction_pass = n_pass / n_total`, counting `None` runs inside the denominator and
  thus collapsing "no evidence" into "0 % pass → fail". This silently mis-reported two
  instrumentation gaps (SC-EDGE-05, SC-PERT-03) as safety violations, dragging SR-009
  and SR-010 to `false` — an honesty defect the spine already avoided.
- *Make `run_campaign.py` import `verdict_aggregation.py` directly.* Rejected for now:
  the spine lives inside the `cobraflex_rl` ROS package with package-relative imports
  (`.criterion_eval`, `.scenario_loader`) and a different data shape (`ScenarioRuns`),
  whereas `run_campaign.py` is deliberately ROS-free and importable by file path from
  `tools/`. Replicating the *semantics* (with cross-references in code) keeps the tool
  self-contained while removing the divergence; a later refactor to a shared module is
  left open.
- *Treat an errored run as a failure.* Rejected: an executor crash is missing evidence,
  not a demonstrated unsafe behaviour; it is counted as indeterminate and surfaced
  separately via `n_error`.

**Rationale.** The traceability commitment requires that a verdict mean what it says: a
`failed` SR is a demonstrated safety violation, an `insufficient_evidence` SR is a gap
in instrumentation or coverage. Conflating the two would either fabricate a violation
(as happened for SR-009/SR-010) or, symmetrically, risk laundering a gap into a pass.
The D-29/D-30 spine was designed with three-valued logic precisely for this; the fix
brings the campaign runner into line with it rather than inventing a third rule.

**Consequences.**
- `tools/run_campaign.py`: `ScenarioResult` gains `n_fail`/`n_indeterminate` and a
  three-valued `verdict`/`fraction_pass` (over evaluable runs); `SRResult` carries a
  `status` ∈ {satisfied, failed, insufficient_evidence, not_run} plus failing/
  indeterminate scenario lists; `global_verdict` distinguishes `NOT SATISFIED` (an
  SR-CL-A failed) from `INCOMPLETE` (an SR-CL-A under-evidenced). The per-scenario and
  per-SR report schemas gain the corresponding fields.
- `experiments/sim/campaign/campaign_report.json` **regenerated from the raw
  `campaign_runs.csv` per-run verdicts — no Gazebo re-run** (the per-run `None`s were
  already recorded). SC-EDGE-05 and SC-PERT-03 now read `verdict: null`
  (`fraction_pass: null`); SR-009 and SR-010 move from `false` to
  `insufficient_evidence`. SR-006 remains `failed` here (it inherits the SC-PERT-01
  fraction fail, a separate per-metric-aggregation issue, not a `None`) — **resolved
  to Satisfied by D-39**, which scores SR-006 on its own metric.
- **The global verdict is unchanged: `SATISFIED`, all 7 SR-CL-A satisfied** (D-30 veto
  clear). Only the classification of three non-blocking SR-CL-B verdicts is affected.
- Tests added in `policy/tests/test_run_campaign.py` and
  `policy/tests/test_verdict_aggregation.py` for the "all runs `None` →
  insufficient_evidence, not failed" case and the failed-dominates-indeterminate
  precedence.
- The `docs/07` "Aggregator caveat" is removed (the divergence it documented is
  resolved). No new H/SR/C/SC/M artefacts, no `traceability_matrix.csv` rows. Cites
  D-29, D-30.

---

### D-39 — SR-006 (actuator smoothness) verified on its own metric, not by scenario inheritance

| Field | Value |
| --- | --- |
| Section | §8.5/§8.7 (sim-eval); `tools/sr006_smoothness.py`; `src/cobraflex_rl/cobraflex_rl/campaign_metrics.py`; `docs/07` |
| Status | CONFIRMED |
| Date | F4 (10.06.2026) |

**Decision.** SR-006 (actuator smoothness, C-06) is verified **directly on its own
metric** — the per-cycle rate of the committed steering command — pooled across runs,
**not** by inheriting the pass/fail of the scenarios it maps to. Because C-06 is
"always active", SR-006 maps to *all* scenarios; the D-30 per-scenario aggregation
therefore made it inherit *any* failing scenario, and it was dragged to `failed` by
SC-PERT-01 (whose σ = 0.05 failures are emergency trips under observation noise,
unrelated to actuator smoothness). The cage chain is C-06 → C-04 → C-02 → C-03 →
C-01 → C-05: C-06 bounds the *raw* action's per-cycle rate first, then a downstream
safety rule (C-01/C-02/C-03/C-05) may command a larger correction to avert an
imminent hazard — **smoothness yields to safety by design**. SR-006 is therefore
measured on the steps the rate limiter actually governs (no downstream safety-override
rule, no emergency): it holds iff the committed-steer per-cycle delta stays within
`δ_max_steering = 0.15` (`cage.yaml`) on those steps. The analysis is a dedicated tool
`tools/sr006_smoothness.py` reporting **outside** the D-30 per-scenario aggregation,
exactly as the frontier M-S5 contrast does (precedent **D-35**).

**Evidence.** On the main-seed campaign logs (`cage_status.csv`): enforcement
**559/559** evaluable runs hold (worst non-override rate exactly 0.15); monitoring
(C-06 inert) only **67.6 %** hold (worst rate 0.43) — a direct measure of C-06's
contribution. Verdict: **Satisfied** (enforcement).

**Alternatives considered and rejected.**
- *Keep SR-006 under the `ALL`-scenario inheritance.* Rejected: it conflates an
  unrelated scenario failure (SC-PERT-01 noise-induced emergency trips) with a
  smoothness verdict — the same honesty defect D-38 fixed for indeterminates, here for
  a genuine-but-irrelevant failure.
- *Measure SR-006 on the final committed steer over **all** steps.* Rejected: that
  penalises the cage for the *correct* behaviour of a downstream safety rule overriding
  C-06 to prevent lane/heading/TTLC hazards; it would report a safety success as a
  smoothness failure (worst all-step rate 0.97, all on C-01/C-02/C-03 intervention
  steps).
- *Add a smoothness pass-criterion to every scenario YAML.* Rejected as redundant and
  error-prone; one always-active metric is better verified once, pooled, like M-S5.

**Consequences.**
- `campaign_metrics.compute_run_metrics` M-I5 gains `steer_rate_max`,
  `steer_rate_p95`, `steer_rate_max_smoothness`, `steer_rate_smoothness_ok`,
  `delta_max_steer` (pure, unit-tested in `policy/tests/test_campaign_metrics.py`).
- `tools/sr006_smoothness.py` added (reads `cage_status.csv`; no Gazebo).
- `docs/07`: SR-006 verdict TBD → **Satisfied** (note ¹).
- **Follow-up (open):** `tools/run_campaign.py` still scores SR-006 by `ALL`-scenario
  inheritance, so `campaign_report.json` per-SR SR-006 reads `failed`; re-point SR-006
  to this metric in `aggregate_sr` (a "metric-verified SR" path) so the report agrees.
  SR-006 is **SR-CL-B**, so neither the current nor the corrected value changes the
  **global verdict (`SATISFIED`, D-30)**. Cites D-30, D-35, D-38.

---

## Future and pending decisions

The following decisions are explicitly deferred to later phases and will
be documented here when taken.

| Provisional ID | Subject | Decision phase |
| --- | --- | --- |
| D-20 (provisional) | Closing definitive IDs in the traceability matrix (SR-001..SR-00*k*, C-01..C-0*n*) | Phase 1 (D15–D19) |
| D-21 (provisional) | Confirmation or replacement of QED as official metric (cf. D-17) | Phase 4 |
| D-22 (provisional) | Adoption of Behavior Metrics as official auxiliary tool | Phase 4 |
| D-23 (provisional) | Decision on merging `V-Model_Adaptado.md` with Chapter 3 or keeping it as annex | Phase 6 |
| D-24 (provisional) | Definitive bibliographic style (numerical IEEE vs author-year APA) | Phase 6 |

---

## Conventions for using this file

**How to add a decision.** Every new decision is added at the end of the
"Decisions" section with the next available identifier (D-NN). A row is
also added to the "Decision index" at the start of the file. The "Last
update" in the HTML comment of the header is updated.

**How to modify a decision.** Recorded decisions are not overwritten. If
a decision changes, a new entry is added that **supersedes** the
previous one, indicating explicitly "Supersedes D-NN". The previous
decision changes its status to "SUPERSEDED by D-MM" but its content is
preserved. This convention preserves the auditable history and allows
reconstructing the trajectory of decisions a posteriori.

**Possible statuses.** *CONFIRMED*: decision taken and current.
*DEFERRED*: decision deferred to a later phase, with an estimated review
date. *TENTATIVE*: preliminary decision in validation phase.
*SUPERSEDED*: replaced by a later decision.

**Relation to the traceability matrix.** Decisions in this file do NOT
enter the `traceability_matrix.csv` matrix unless they generate H, SR,
C, SC, or M artefacts. However, matrix artefacts may cite decisions in
this file in their *justification* field via the reference `cf. D-NN`.

**Adoption cost (criterion D-19).** Each new entry adds between ten and
twenty minutes of adoption cost (drafting + review). This cost is
explicitly considered when evaluating the framework in Chapter 11.


---

### D-41 — Track 'E': parallel end-to-end front-camera lane-following (supersedes D-01)

| Field | Value |
| --- | --- |
| Section | `docs/00` (Parallel track E); `docs/01` (E-phase numbering); manuscript §3.5.1 (supersedes D-01) |
| Status | CONFIRMED |
| Date | F4 / E0 (09.06.2026) |
| Planned review | GE0 (track-entry gate) |

**Supersedes D-01.**

**Decision.** A parallel development track — **track 'E'** — is opened on branch
`e2e-camera` to re-develop the lane-following function with an **end-to-end
front-camera policy**: the RL policy maps the front-camera image directly to the
action, *learning* perception instead of consuming the hand-built state vector
(`/state_obs`) of the F-track. This **supersedes D-01**'s prohibition on pixels
entering the learned component. The **modular safety architecture is retained**: a
rule-based **cage remains a distinct, independently-verifiable module** that mediates
actuation (D-42), so the *system* is not end-to-end from pixels to actuators — only
the *policy*'s perception is. The track carries its own phase/gate numbering —
**E0..E6 / GE0..GE6**, commit prefix **`E2:`** — re-traverses the V's left arm
(HARA → SRS → Cage → Training Spec) for the new front-end, and **shares the global,
never-reused artefact ID space** (`docs/01`). The F-track continues independently on
`main` (F4 → G4); its F2/F3/F4 evidence is frozen, not invalidated.

**Alternatives considered and rejected.**
- *Keep D-01 and reject the camera track.* Rejected: the camera variant is a second
  instantiation of the SE4AI method on a harder perception problem and strengthens the
  generality claim; foreclosing it on a Phase-0 decision taken before the cage was even
  demonstrated would be premature.
- *Full PilotNet-style end-to-end (pixels → actuation, no cage).* Rejected for exactly
  D-01's original reasons (Salay et al. 2017; Shalev-Shwartz & Shashua 2016) **and**
  because it would delete the cage — the thesis's contribution. D-41 supersedes only the
  "no pixels into the policy" clause, never the modular-cage commitment.
- *Scoped relaxation that leaves D-01 CONFIRMED for the F-track.* Considered; rejected in
  favour of a clean formal supersession so the decision ledger carries a single current
  architectural stance going forward rather than two conditionally-active ones. The
  F-track evidence stands on its own run metadata regardless of D-01's status.

**Rationale.** D-01 rejected end-to-end because it would make framework adaptations
A1/A2/A4 unviable (D-07/D-08/D-10). That rationale is **answered, not ignored**: A1 (Cage
Spec ≠ Training Spec) holds because cage and policy remain distinct modules; A2 (cage
independently verifiable) holds because the cage runs on an **independent state estimate**
(D-42), fully separable from the camera policy; A4 (traceability) holds because the
H/SR/C/SC/M chain and the cage rules C-01..C-06 are unchanged. The policy was *already* a
black box in the F-track; moving its *input* from a hand-built state vector to pixels does
not reduce cage verifiability, because the cage never depended on the policy's internals or
inputs. What the track accepts as a known cost is D-01's *other* concern — the larger
training-set requirement of end-to-end perception (Shalev-Shwartz & Shashua 2016) —
budgeted into the E-training phase.

**Consequences.**
- Branch `e2e-camera`, commit prefix `E2:`. `docs/01` gains the E-phase/gate scheme;
  `docs/00` gains a "Parallel track E" section.
- D-01 status → **SUPERSEDED by D-41**; manuscript §3.5.1 to be revised to record the
  supersession and the retained-cage argument *(manuscript edit pending — follow-up)*.
- Shared-register left-arm extensions: H-10/H-11 (`docs/02`), SR-012/SR-013 (`docs/03`),
  SC-PERT-04..07 (`docs/05`); cage C-01..C-06 and metrics reused (D-42).
- Deferred to later E-phases: camera-observation / CNN env design (`docs/09`), reward
  (`docs/10`), Gazebo camera sensor + perception/`policy`, PPO retraining, un-stubbing
  SC-PERT-04..07.
- Cites D-31 (the new perception hazards are functional sensor/environment failure modes,
  narrower than D-31's still-excluded non-functional AI families), D-42, D-07/D-08/D-10.

---

### D-42 — Track 'E' cage operates on an independent state estimate, not the camera

| Field | Value |
| --- | --- |
| Section | `docs/04` (cage independence); `docs/02` (H-06 vs H-11) |
| Status | SUPERSEDED by D-43 (cage state moves from privileged ground truth to a dedicated deterministic vision lane-estimator, for generalisation) |
| Date | F4 / E0 (09.06.2026) |
| Planned review | GE2 (cage integration on the camera track) |

**Decision.** On track 'E' the safety cage continues to evaluate its rules C-01..C-06
over an **independent state estimate** — its own state pipeline (and, in simulation,
privileged ground-truth) — **not** over the camera image or the policy's learned
perception. The camera-to-action policy and the cage therefore consume **disjoint
inputs**: the policy sees pixels, the cage sees state. C-01..C-06 are reused unchanged.

**Alternatives considered and rejected.**
- *Cage derives its state from the same camera/perception as the policy.* Rejected: it
  injects perception error into the safety monitor and couples the cage to the very
  component it is meant to bound — destroying the A2 "independently-verifiable cage"
  property and the central thesis argument that the cage is independent of the controller
  *and its perception*. It would also turn a camera failure into a common-cause failure of
  policy *and* cage at once.
- *Hybrid (some rules on state, others on camera).* Rejected: partial coupling still
  breaks independence for the camera-fed rules and complicates traceability for no benefit.

**Rationale.** The thesis's safety claim rests on the cage being an *independent* runtime
monitor. Keeping the cage on an independent state estimate is precisely what makes D-41's
supersession of D-01 safe: pixels may enter the *policy*, but they never enter the *safety
envelope*. This yields a clean hazard separation — **H-06** (operation under invalid /
unobservable *cage* state: the cage's own pipeline failing) and **H-11** (loss of valid
*camera* perception: the policy's input failing) become genuinely distinct hazards with
distinct mitigations rather than one conflated failure. Under camera degradation the policy
may command poorly, but the cage — seeing valid independent state — still bounds the
trajectory (the core cage-value demonstration, now under a perception stressor).

**Consequences.**
- C-01..C-06 reused unchanged; **no new numbered cage rule** required for H-10 (mitigated
  by the existing cage + training augmentation).
- H-11's "safe degradation on loss of valid perception" (SR-013) is realised by a
  **perception-health supervisor** that raises an existing C-05 emergency trigger, keeping
  the cage itself camera-agnostic. The final mechanism is fixed in `docs/04` at GE2
  (candidate mini-ADR if it warrants its own rule).
- Requires an independent state source on the camera track (sim ground-truth initially; a
  robust independent estimator for physical deployment — deferred to E-physical).
- Cites D-41, D-01 (the superseded decision whose modular-safety intent D-42 preserves),
  D-08 (A2).

---

### D-43 — Track 'E' cage state comes from a dedicated deterministic vision lane-estimator (supersedes D-42)

| Field | Value |
| --- | --- |
| Section | `docs/04` (cage perception); `docs/09` §10; `docs/02` (H-10/H-11/H-12) |
| Status | CONFIRMED |
| Date | E1 (09.06.2026) |
| Planned review | GE2 (CV-estimator integration + accuracy vs the ground-truth oracle) |

**Supersedes D-42.**

**Decision.** On track 'E' the cage's independent state (the `ey/epsi/…` that C-01..C-06
consume) is produced by a **dedicated, deterministic (classical computer-vision)
lane-detection pipeline**, separate from the policy's learned CNN — **not** by
privileged ground truth and **not** by the policy's perception. This supersedes D-42's
"cage on ground truth, never the camera". The goal is generalisation: the cage, like the
policy, must work on **any road with visible lane lines** without an authored centerline.
Ground truth remains available **in simulation only**, as (a) the training **reward**
signal and (b) an **oracle** to measure the CV estimator's error; neither policy nor cage
consumes ground truth at **runtime**. C-01..C-06 are reused unchanged — only the *source*
of the `state` they receive changes (CV estimator instead of `PolylineTracker(/odom_truth)`).

**Alternatives considered and rejected.**
- *Keep D-42 (cage on privileged ground truth).* Rejected for the generalisation goal:
  ground truth needs an authored centerline per world, so the cage could not protect on an
  arbitrary / real road with no centerline — only the policy would generalise, not the
  safety net.
- *Cage shares the policy's CNN perception.* Rejected: it couples the safety monitor to the
  learned, opaque controller and destroys the A2 "independently-verifiable cage" property.
  A *separate, deterministic* CV pipeline keeps the cage independent of the **policy** and
  auditable, even though it now uses vision.
- *Hybrid (ground truth in sim now, CV interface later).* Considered; rejected as the
  primary path because deferring the estimator would leave the generalisation claim
  unverified and re-open the design at E-physical. The CV estimator is built now; ground
  truth stays as the sim oracle that validates it.

**Rationale.** "Any road, sees lines → drives" requires the *whole* system — policy and
cage — to key on visible lane lines, not on an authored centerline. A deterministic CV
lane detector for the cage preserves what D-42 actually protected (independence from the
*learned policy* + auditability: a classical algorithm is inspectable, unlike the CNN)
while extending it to ungrounded roads. It also yields a **cross-check**: divergence
between the policy's behaviour and the cage's CV estimate is a safety signal (a CNN
hallucinating a lane the CV does not see is bounded by C-01/C-02 on the CV state).

**Consequences (including the honest trade-off).**
- **Common-cause failure (accepted).** A camera fault (glare / occlusion / dropout —
  H-10/H-11) can now blind **both** the policy and the cage at once — the isolation D-42
  provided is given up. Mitigations: (i) the cage detector is *deterministic*, with failure
  modes that differ from the CNN's, partially decorrelating the two; (ii) when valid lines
  are absent for the cage detector, the safe action is an **open-loop controlled stop**
  (SR-013 / C-05), which needs no perception — so "no lines ⇒ stop" is the designed
  behaviour, matching the track's intent.
- **New hazard.** A confidently *wrong* CV lane estimate (a *plausible but false* lane)
  would make the cage enforce a wrong envelope — impossible under ground-truth D-42. To be
  registered as **H-12 (cage lane-misdetection)** with **SR-014** (cage-estimator
  plausibility / temporal-consistency check + conservative-on-uncertainty fall-back to C-05).
- The cage's `state` source becomes the CV-estimator node (Ubuntu); C-01..C-06 and the
  reward (`docs/10`) are unchanged. `docs/04`, `docs/09` §10 and the H-10/H-11/SR-012/SR-013
  framing are revised from "cage on ground truth" to "cage on its own CV estimate".
- D-42 status → **SUPERSEDED by D-43**.
- Cites D-41, D-42 (superseded), D-08 (A2), D-01 (whose modular, auditable-cage spirit is
  retained: the cage is still a distinct, deterministic, inspectable module).

---

### D-44 — Isaac-Sim RL training is in-process, decoupled from the ROS2 bring-up

**Status.** CONFIRMED (2026-06-19). Platform decision for the Gazebo→Isaac migration of
the RL **training** loop; does not touch any H/SR/C/M identifier.

**Context.** `tools/isaac_ros2_bringup.py` reproduces the Gazebo *steady-state* topic
contract (`/cmd_vel` in; `/odom_truth`, `/camera/image_raw_lane`, `/clock`,
`/joint_states`, `/tf` out) over a ROS2-bridge OmniGraph, and free-runs `world.step()`.
But RL training needs one more operation the bring-up does **not** expose: a per-episode
**reset/teleport**. `GazeboLaneEnv.reset()` performs it through
`RosGazeboInterface.set_vehicle_pose()` → `gz service /world/<name>/set_pose`
(`gz.msgs.Pose`, via the `gz` CLI) — a Gazebo Transport service with no Isaac equivalent
(no `gz` server runs alongside Isaac). The same applies to `set_physics` (RTF) and the
`pose/info` entity-id lookup. So driving training over the bring-up would leave every
episode unable to respawn.

**Decision.** Run training **in-process inside the Isaac Sim Python app** (option 2),
driving the gym env directly against the live `World` rather than over ROS2:

- A new `IsaacSimInterface` (`src/cobraflex_rl/cobraflex_rl/isaac_interface.py`)
  duck-types the exact surface `GazeboLaneEnv` calls, so the env is **unchanged**. Its
  operations are direct Isaac calls: per-episode reset = `articulation.set_world_pose` +
  zeroed velocities; actuation = the diff-drive twist → 4 wheel `ArticulationAction`
  (same kinematics as the bring-up `WHEEL_SCRIPT`); advance = `world.step()` over
  `control_dt / physics_dt` sub-steps; pose/speed read straight from the articulation
  root (ground truth → the odom→world calibration the Gazebo path needs is a no-op); the
  Lane Cam frame comes from a Replicator `rgb` render product (RGBA→BGR to match
  `camera_pipeline.decode_image`).
- The physics scene (URDF→USD, track geometry, robot spawn, wheel drives/materials) is
  extracted into a shared `tools/isaac_scene.py`, imported by **both** the bring-up and
  the new trainer `tools/isaac_train.py`, so the two paths share **one** source for the
  drivetrain constants (`WHEEL_RADIUS`/`WHEEL_SEPARATION`/`WHEEL_JOINTS` order) — a drift
  there would silently invalidate a trained policy.
- `GazeboLaneEnv`'s only hard `rclpy` coupling (the `RosGazeboInterface` type import) is
  moved under `TYPE_CHECKING`, so the env imports on the Isaac host without `rclpy`.

**Rationale.** It is the standard, far faster Isaac-Lab-style pattern (no async ROS↔gz
bridge, no `gz` CLI subprocess per reset), and it removes the *only* training blocker in
one move. Training and the bring-up command become independent: the bring-up keeps its
"same ROS2 nodes as Gazebo" demo/eval role; training no longer needs a running bring-up.

**Consequences / honest trade-offs.**
- The bring-up is now a thin ROS2/sensor layer over `isaac_scene.build_world`; its observed
  behaviour is unchanged (scene functions moved, not altered).
- **Not yet host-validated.** This was authored on a Windows machine where Isaac does not
  run; only `py_compile` + an rclpy-free import check of the env/interface were possible.
  The Isaac API calls (`set_world_pose`, `get_world_pose`, `get_linear_velocity`,
  `set_joint_velocities`, the Replicator render-product/annotator flow) must be confirmed
  on the Ubuntu+Isaac host, and SB3+gymnasium must be installed into Isaac's bundled
  python. The stale cached `isaac_usd/` should be re-imported (`BRINGUP_REIMPORT=1`).
- The in-process camera renders once per control step (~10 Hz at `control_dt` 0.10), which
  the env consumes one-frame-per-cycle; this is below the handover's ≥20 Hz steady-state
  camera target but matches what training actually samples.
- Cites D-34 (in-loop cage during training), D-41/D-43 (camera track + CV-estimator cage),
  D-32 (third-party drivers untracked — here, Isaac/SB3 are host-installed, not vendored).

**Validation positioning (added 2026-06-20).** Within the V-Model's A5 (Bounded Operational
Validation, `docs/00`), Isaac is positioned as a **higher-fidelity intermediate rung** of the
sim-to-real characterisation (PhysX physics + RTX rendering), **not** as the thesis verdict
environment. **Gazebo remains the primary, verdict-bearing environment**; its results are the
thesis's *provisional principal evidence*. Because a Gazebo checkpoint does **not** transfer to
Isaac (different physics + renderer — see `docs/13` §"Speed and fidelity"), an Isaac campaign is
a re-training/re-evaluation from scratch, so for now Isaac evidence is kept **for internal
valuation**. Should the Isaac campaign mature into the stronger result, the thesis is re-stated
with those figures as final, with the Gazebo campaign retained as the provisional baseline. The
simulator axis (Gazebo↔Isaac) is **orthogonal** to the F/E observation-track axis. Reflected in
`docs/00` (A5 + mapping table), Ch.1 (outline §1.7 + contribution A4), Ch.6 §6.7, Ch.8 §8.8.

---

### D-45 — Track-'E' GE4 safety verdict scored on the SR limit predicate, not the absence of a controlled stop

| Field | Value |
| --- | --- |
| Section | `scenarios_complex_b/*` (per-run criteria); `tools/run_campaign.py` (`evaluate_criterion`); `docs/07` (E-track verdicts); Ch.8 §8.9; `scenarios_complex_b/README.md` |
| Status | CONFIRMED |
| Date | track 'E' / GE4 (24.06.2026) |

**Decision.** For the track-'E' camera GE4 campaign (the complex_b 297k E-main), a per-run
**controlled safe stop scores as a pass iff the SR's own safety-limit predicate held** — the
lane envelope `M-S1 < d_max` (0.16 m) and, where applicable, `road_edge_contact == False`. The
`emergency == False` clause is **dropped** from the eight adverse safety scenarios (SC-EDGE-02,
SC-EDGE-03, SC-PERT-01, SC-PERT-02, SC-PERT-04, SC-PERT-06, SC-PERT-09, SC-PERT-10): a
cage-commanded controlled stop is a **safe outcome of the mitigation**, not a safety breach. A
genuine breach (`M-S1 >= d_max`, or a road-edge contact) still fails. Scenarios where stopping
is the *required* behaviour (SC-PERT-07 / SR-013: `emergency == True`) and the nominal/availability
scenarios (SC-NOM-01/02/03, already gated by completion `M-P2 == 1`) are **unchanged**.

**Rationale.** Under the camera (D-41/D-43) the cage flips latent→active in-ODD: the
SR-013/Trigger-8 controlled stop becomes the in-ODD safety mechanism. The original criteria
conflated "the policy never needed the cage" with "the cage kept the system safe" — they scored a
*safe controlled stop* as a fail purely on `emergency == False`, even when `M-S1 < d_max` and no
road-edge contact held throughout. On the (superseded) 139k campaign that artifact accounted for
**13/13** SC-EDGE-02 + **20/20** SC-PERT-04 enforcement fails (emergency-only, limits respected;
**0** road-edge contacts across all 830 enforcement runs). That is an **availability** cost (the
vehicle stopped), not a safety violation, and the thesis verdict is a **safety** verdict (D-28,
D-30). The safety truth is the limit predicate; `emergency` is only the mechanism that enforces it.

**Alternatives considered and rejected.**
- *Keep `emergency == False` in the adverse safety criteria.* Rejected: scores the cage's correct
  safe-stop behaviour as a safety failure — the same honesty defect D-38 (indeterminate-as-fail)
  and D-39 (irrelevant-failure inheritance) fixed, here for a safe-outcome-as-fail.
- *Re-score out-of-band with a dedicated tool (the D-39 `tools/sr006_smoothness.py` pattern).*
  Rejected here: D-39 needed an out-of-band tool because the oval scenarios were **frozen** F4
  evidence; the complex_b scenarios are **DRAFT** (not yet verdict-run), so the correct criterion
  belongs in the source YAML — the single source of truth that `evaluate_criterion` reads directly.
- *Make `emergency` a global don't-care across all scenarios.* Rejected: nominal scenarios
  (SC-NOM-*) legitimately require completion (`M-P2 == 1`, which already fails an early stop), and
  SR-013 (SC-PERT-07) legitimately *requires* the stop.

**Consequences.**
- Clears the three SR-CL-A vetoes that drove the 139k `NOT SATISFIED` (SR-001/SC-EDGE-02,
  SR-012+SR-014/SC-PERT-04), reframing them as satisfied-on-safety with the controlled stop logged
  as an availability cost.
- **Does not by itself reach `SATISFIED`.** SR-013 stays `INCOMPLETE` under D-29 family coverage
  (its only scenario SC-PERT-07 is adverse-only; perception-loss has no natural nominal companion),
  and the indeterminate scenarios remain (SC-PERT-05 labelled `low:/high:` criterion unwired;
  SC-EDGE-05 grid ICs not injected). The 297k GE4 global verdict therefore moves
  `NOT SATISFIED` → at best `INCOMPLETE` until those are addressed.
- For the SR-007 staleness scenarios (SC-PERT-01/02) the dropped clause removes the implicit
  "no false-trigger" assertion; the run now passes on the lane envelope alone, with spurious-stop
  behaviour relegated to the availability axis (consistent with the safety/availability split above).
- Applies to the **complex_b camera GE4** set only. The frozen oval `scenarios/` and the 139k
  campaign evidence are **not** rewritten (read through this decision). `docs/05` documents the
  oval criteria; the variant deviation is documented in `scenarios_complex_b/README.md`.
- All inputs are logged per-run evidence (`M-S1`, `road_edge_contact`, `emergency` in
  `summary.json`), so the verdict stays computable and auditable (traceability intact).
  Cites D-28, D-30, D-38, D-39, D-41, D-43.

---

### D-46 — Two-sided D-29 coverage for the camera-stressor SRs (clean-input nominal anchor)

| Field | Value |
| --- | --- |
| Section | `docs/03` (SR register SR-012/013/014 Scenarios) → `docs/data/safety_requirements.csv`; `docs/07`; `scenarios_complex_b/nominal/sc_nom_01.yaml` |
| Status | CONFIRMED |
| Date | track 'E' / GE4 (24.06.2026) |

**Decision.** SR-012 / SR-013 / SR-014 (the track-'E' camera-stressor SRs, adverse by
construction) take their **D-29 nominal family from the clean-input nominal run SC-NOM-01**,
with the adverse family from the SC-PERT camera scenarios (SC-PERT-04..13). This makes all
three D-29-feasible (≥ 25 runs in a nominal **and** an adverse family) without weakening the
gate — mirroring how the F-track SR-001 is covered (SC-NOM-01/02 nominal + SC-EDGE-02 adverse).

**Rationale.** A clean nominal run cannot exercise "degraded / lost / suspect visual input",
so the camera SRs were authored adverse-only and read INCOMPLETE on the 139k roll-up
(`nominal = 0`). But D-29's nominal family is the **baseline arm of a two-sided test**, not a
"repeat the hazard under clean input" requirement: for a safety mechanism the two necessary
tests are (i) it does **not** regress / false-trigger under valid input — the nominal arm
(SC-NOM-01: lane kept, `emergency == False`, zero spurious controlled stops) — and (ii) it
responds **correctly** under the stressor — the adverse arm (SC-PERT-04..13). SC-NOM-01 is the
genuine no-false-positive control for SR-013/014 and the un-stressed competence baseline for
SR-012. The 139k `nominal = 0` was a coverage-authoring gap, not a missing-evidence gap.

**Alternatives considered and rejected.**
- *Documented D-29 exception (waive the nominal family for camera SRs).* Rejected: the nominal
  arm is genuinely meaningful (no-false-trigger), so satisfying D-29 honestly beats waiving it.
- *A new dedicated nominal camera scenario.* Rejected: SC-NOM-01 already **is** the clean-input
  nominal of the same perception→control loop; a duplicate adds nothing.

**Consequences.**
- `docs/03` SR register: SR-012/013/014 Scenarios gain SC-NOM-01 (→ CSV regenerated); `docs/07`
  matrix + footnote ⁶ updated; SC-NOM-01 (complex_b) `references_SR` gains SR-012/013/014
  (bidirectional, D-10).
- `--dry-run` D-29 feasibility: SR-012/013/014 nominal family **0 → 50** (SC-NOM-01), adverse
  ≥ 25 (incl. SC-PERT-13, D-45-era) → **feasible, GAP cleared**.
- A coverage/plan change, **not** evidence: the verdict is still scored when the 297k GE4
  campaign runs. Cites D-29, D-30, D-43, D-45.

---

### D-47 — SR-002 / SR-003 scored on their own satisfaction criterion, not SC-EDGE-01's oval-legacy recovery-time clause

| Field | Value |
| --- | --- |
| Section | `docs/07` (E-track GE4 note + footnote ⁷); `docs/11` §8.4; `scenarios_complex_b/edge/sc_edge_01.yaml`; Ch.8 §8.9 |
| Status | CONFIRMED |
| Date | track 'E' / GE4 validation (27.06.2026) |

**Decision.** In the complex_b 297k GE4 roll-up, **SR-002 (heading stability) and SR-003
(predictive TTLC) are scored on their documented satisfaction criteria** — `M-P4 ≤ θ_max = 25°`
(SR-002) and `TTLC ≥ t_min` (SR-003, docs/03) — **not** on SC-EDGE-01's per-run clause
`time_to_recovery_heading < 2.0 s`. Re-scored thus, **both are `Satisfied`**, and the only
blocking SR-CL-A in the 297k global `NOT SATISFIED` is **SR-001** (SC-EDGE-02, a genuine
in-ODD boundary-band lateral-recovery failure).

**Rationale.** SC-EDGE-01 (15° heading-error start) records **9/30** enforcement "fails", but
every one fails *only* the `time_to_recovery_heading < 2.0 s` clause: from the trace, **M-P4 =
14.3°** (the vehicle never exceeds its 15° start, far inside θ_max = 25°), **max M-S1 = 0.035 m**
(≪ d_max = 0.16 m), **0 emergencies**, **0 road-edge contacts**. The heading is recovered cleanly
and no safety limit is approached — SR-002 and SR-003 hold on their own predicates. The 2.0 s
recovery-time bar is a **performance overlay copied verbatim from the frozen oval scenario set**;
it is not part of either SR's `docs/03` satisfaction criterion, and SR-003's 0.7 s policy-side
component is itself marked *provisional, revisit at Phase-3 close*. Scoring an SR by a scenario
clause stricter than (and orthogonal to) the SR's own limit is the same honesty defect addressed
by **D-39** (SR-006: irrelevant-failure inheritance, re-scored out-of-band) and **note ⁴** (SR-012:
safe-stop-as-fail). This is the own-criterion reconciliation **flagged but not applied** in the
prior GE4 write-up (CLAUDE.md), now applied with the trace evidence in hand.

**Alternatives considered and rejected.**
- *Keep the 2.0 s bar and report SR-002/003 as failed.* Rejected: scores a clean,
  limit-respecting heading recovery as a safety-requirement violation — the verdict is a
  **safety** verdict (D-28/D-30), and both SRs' safety predicates are met with wide margin.
- *Tighten the bar / retune 2.0 s for complex_b geometry.* Rejected as the verdict mechanism:
  recovery-time is a policy **performance** metric, not a safety limit, and tuning it cannot
  change an SR verdict — the SR criterion is the limit predicate. (A retuned recovery-time bar
  may still be reported as an availability/performance observation.)
- *Edit SC-EDGE-01's per-run clause to drop the 2.0 s term.* Deferred: the scenario stays as the
  performance probe; the SR verdict is taken on the SR criterion via this decision (mirrors how
  D-39 left the oval scenario frozen and re-scored out-of-band). A future scenario refactor may
  split the safety predicate from the performance overlay.

**Consequences.**
- V1-297k GE4 blocking SR-CL-A: {SR-001, SR-002, SR-003} → {SR-001} after this D-47. **In the V2
  run (D-48 V2 OUTCOME) SR-001 then closed via ruta-1 (28/30), so the V2 literal blocking set is
  {SR-002, SR-003} only** — both reconciled Satisfied here. So after D-47, *no SR-CL-A safety
  predicate is breached* in V2; the global `NOT SATISFIED` is held purely by the SC-EDGE-01
  recovery-time clause. Heading stability and predictive lane-departure prevention **hold** under
  the camera.
- The **F4→E PASS→FAIL flip list drops SC-EDGE-01**; only SC-EDGE-02 + SC-FRONT-01/03/04/06
  remain as genuine camera-cage recovery failures (all lateral, consistent with the D-43
  shared-perception mechanism — heading/TTLC are unaffected).
- All inputs are logged per-run evidence (`M-P4` recomputable from `epsi` in `cage_status.csv`,
  `max_abs_ey_m`, `emergency_steps` in `summary.json`); the reconciliation is auditable.
  Cites D-28, D-30, D-38, D-39, D-43, D-45; SR-002/SR-003 (`docs/03`).

---

### D-48 — GE4-V2 prep: SR-001's SC-EDGE-02 failure is an H-12 estimator under-read (not perception loss); in-ODD IC clip applied, estimator fix scoped

| Field | Value |
| --- | --- |
| Section | `scenarios_complex_b/edge/sc_edge_02.yaml`; `src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py` (target); `docs/07` GE4 note; `docs/11` §8.4; H-12 / SR-014 (`docs/02`/`docs/03`) |
| Status | CLOSED (V2 ran 28.06.2026: ruta-1 alone closed SR-001 28/30; ruta-2b reverted after closed-loop regression — see the V2 OUTCOME bullet; residual = 2 boundary-edge breaches, carried) |
| Date | track 'E' / GE4-V2 validation (27.06.2026; outcome 28.06.2026) |

**Context.** SR-001 is the **only** blocking SR-CL-A in the 297k GE4 V1 verdict (D-47), carried
entirely by SC-EDGE-02 (SC-NOM-01/02 pass clean). Trace analysis of the 297k V1 run gives a sharp,
reproducible picture that **corrects the D-43 "perception loss" framing**.

**Findings (from `experiments/sim/campaign_e_297k/runs/camp_edge02_*` traces).**
- **Sharp recovery-basin boundary at ey ≈ 0.120 m.** Every rep spawning at |ey0| ≤ 0.1201 m
  recovers (M-S1 ≈ start, pass); every rep at |ey0| ≥ 0.1202 m diverges to M-S1 ≈ 0.31 m and
  contacts the edge. Of the 12 V1 fails, **9 spawn out-of-ODD** (>0.1225 m, the painted lane edge;
  the V1 IC's symmetric ±0.02 band on a 0.12 m seed spilled there) and **3 sit in a ~2 mm in-ODD
  sliver** (0.1202–0.1224 m).
- **The estimator under-reads — it does not go blind (uniform across all 12 fails).** `cv_ok`
  stays True and `cv_perception_invalid` never sets; yet `cv_ey ≈ 0.04 m` (near-centred) while the
  true `ey` reaches ≈ 0.30 m (max |cv_ey − ey| ≈ 0.265 m). The CV estimator locks onto the wrong
  lane reference once the vehicle is ~half-a-lane off-centre and reports a confident, near-centred
  offset, so C-01/C-05 are fed a false in-band state and never intervene. The mis-lock is present
  already at frame 1 (the spawn frame), so it is not tracking drift.
- **SR-014 cannot catch it.** `LanePlausibilityCheck` gates geometric range and inter-frame jumps;
  the wrong estimate is **self-consistent on both** (|cv_ey| < ey_max, smooth frame-to-frame), so
  neither gate fires. This is a latent **H-12** (cage lane-misdetection) realization the current
  SR-014 design does not cover.

**Decision.**
- **Ruta 1 (applied).** SC-EDGE-02's IC randomisation is clipped to keep every spawn in-ODD —
  seed 0.12 m + `[-0.02, +0.0025]` → `[0.10, 0.1225]` (was `[-0.02, +0.02]`). SR-001 is scoped
  "under the ODD", so the 9 out-of-ODD V1 fails must not be charged to it. This is a validation
  fix, not a relaxation: the in-ODD sliver (0.1202–0.1224 m) is retained as the genuine residual.
  *Not sufficient alone:* even all-in-ODD, the recovery basin (~0.120 m) leaves the 0.120–0.1225 m
  band failing, so SC-EDGE-02 still misses the 0.90 bar until ruta 2b widens the basin.
- **Ruta 2b (attempted, then REVERTED — no robust single-frame fix exists).** A Gazebo frame dump
  pinned the cause: past its own left line the vehicle sees a third (next-left) line forming a
  *competing* plausible pair whose centre is opposite-signed and marginally nearer, so the legacy
  `min |centre|` rule locks the neighbour (the under-read). A conservative rule (pick the
  larger-`|centre|` pair when pairs straddle the vehicle with opposite-sign centres) fixed the
  single-frame dump (cv_ey +0.14/+0.18 at ey 0.12/0.16) and passed unit tests — **but regressed in
  the actual campaign:** a *centred* vehicle under a small heading error splits its lines into the
  *same* opposite-sign pairs, so the rule fires a spurious C-01/C-05 emergency. Caught by verifying
  the first V2 launch's early output: **SC-EDGE-01 emergency at step 1** (V1: clean 150 steps). A
  **heading gate** (apply only when the line slope/heading is small) only *relocated* the false
  trigger to step 8 (when the recovering heading drops below the gate); a 9-run closed-loop smoke
  confirmed SC-EDGE-01 still emergencies and **SC-NOM-02 (a clean nominal curve in V1) regressed**.
  The geometric ambiguity (centred-with-heading ≡ off-centre) is **irreducible single-frame**; a
  real fix needs **temporal lane tracking**, which still would not fix the SC-EDGE-02 *spawn* frame
  (no prior) and so **would not close SR-001 anyway**. **Decision:** `conservative_lane_selection`
  default **False** (legacy nearest-centre restored); kept opt-in only for the regression tests /
  future work. *At revert time* SR-001 was expected to stay a fail (the H-12 under-read being a real,
  un-cheaply-patchable D-43 limitation) — **but the V2 run showed ruta-1 alone closes SR-001 (28/30);
  see the V2 OUTCOME bullet below.** The under-read remains real but is only a 2-breach boundary
  residual once scoped to the ODD. **Ruta 2a (retrain) stays out of scope.**

**Consequences / readiness.**
- The D-43 "common cause / estimator loses the lane" narrative is corrected to an **H-12
  under-read / wrong-lane lock** in `docs/07` + `docs/11` §8.4 (it holds for the in-ODD SC-EDGE-02;
  the deep-OOD frontier contacts past the painted lane are a separate, un-reverified regime).
- **SR-012 / SR-014 D-29 run-count gate cleared (CL-A).** Their V1 `INCOMPLETE` (run_count_ok=False)
  was not a criterion failure: the verifying scenarios **SC-PERT-08/09/10** ran **20 enforcement
  reps < the 25 CL-A minimum** (the SC-PERT-07 bump of the same kind had been missed for these
  three). All three pass 20/20 in V1, so their reps are bumped **20 → 25** (enf + mon); in V2 the
  two SRs reach D-29 coverage and read satisfied. With this + SR-001 (ruta 1/2b) + SR-002/003
  (D-47), the **CL-A path to a SATISFIED V2 global is clear** (the residual risk is only whether
  SR-001's in-ODD sliver recovers vs safe-stops in the closed loop).
- **CL-B items (do not gate the global safety verdict) — addressed (docs/07 note ⁸):**
  *SR-011* — its SC-EDGE-01 "fail" is the **same recovery-time artifact** as SR-002/003 (measured
  max σ_θ over 1 s = 3.0° < the 5° M-P7 limit); reconciled on its own criterion à la D-47 (note ⁸).
  *SR-006* — the D-39 committed-steer artifact: `run_campaign.aggregate_sr` now returns it
  `scored_out_of_band` (`OUT_OF_BAND_SRS`, +unit test) instead of inheriting its `ALL`-scenario
  fails, so the V2 report no longer reads `failed`.
- **SR-010 attribution gap CLOSED (on existing V1 data).** `grid_point` *is* persisted (nested under
  `summary.json["campaign"]`), so `tools/campaign_e_failure_modes.py` gained `sc_edge05_grid_split`
  (in-ODD = |d| ≤ 0.1225 m ∧ |θ| ≤ 25°). The split **corrects the earlier "largely OOD" guess**:
  **30 of 85 in-ODD grid points breach M-S1** (a *genuine* SR-010 in-ODD co-activation finding) vs
  10/15 OOD bracket points. SR-010 is a **real CL-B result**, not an artifact — plausibly reduced in
  V2 by ruta-2b (the under-read that hid lateral drift also hides co-activation drift). The
  attribution is the closure; the residual is a real finding for the V2 run to re-measure.
- **SR-009 stall sub-mode is N/A for the steering-only action space (resolved, see D-49).** SC-PERT-03
  is a *negative* test that fine-tunes a policy under `r' = r − λ·|throttle|` to induce a stall. But
  the track-E policy is **steering-only** (`ACT_DIM = 1`, ED-2) with throttle fixed at cruise, so
  (a) the reward term `λ·|throttle|` is a **constant** → inert, no gradient effect, and (b) the policy
  has **no speed authority** → it cannot converge to inaction → **M-P6 ≡ 0 by construction**. The
  stall fine-tune was therefore **not launched** (it would produce an identical policy and SC-PERT-03
  would still not fire). SR-009's stall arm is N/A-by-construction; its live arm — M-S2 under
  monitoring (H-08 adversarial-direction sub-mode) — is covered by the nominal/monitoring runs. The
  well-posed stall test is deferred to the 2-D-action Isaac work (**D-49**).
- **V2 OUTCOME (28.06.2026) — ruta-2b was unnecessary; SR-001 closed by ruta-1 alone.** GE4-V2 ran
  with the legacy (honest) estimator: **1970 runs, 0 errors** (`experiments/sim/campaign_e_v2/`).
  **SC-EDGE-02 passes 28/30 → SR-001 Satisfied.** The earlier prediction that SR-001 would "fail
  again" was **wrong**: ruta-1 (in-ODD IC clip) removed the 9/30 out-of-ODD spawns that SR-001 must
  not be charged for, leaving only 2 residual breaches at 0.118/0.121 m (the recovery-basin edge). So
  the whole ruta-2b estimator effort was **not needed** — and revertng it was doubly correct (it both
  regressed *and* was unnecessary). The literal global is `NOT SATISFIED` blocking **SR-002/003 only**
  (the SC-EDGE-01 recovery-time clause, reconciled Satisfied by D-47), with SR-012/013/014 now covered.
  The D-43 under-read is real but, scoped to the ODD, only a 2-breach boundary residual. The
  early-output verification on the *first* V2 launch caught the ruta-2b regression and aborted it (the
  check working as intended); the relaunch with the legacy estimator confirmed SC-EDGE-01 runs clean
  150 steps. Verdict of record: literal `NOT SATISFIED` + reconciliation (docs/07, docs/11 §8.4).
- The fix supersedes the earlier "estimator goes blind" reading; the SR-014 plausibility check
  remains blind to a *self-consistent* wrong-lock, so an SR-014 strengthening (absolute-offset
  corroboration, not temporal-jump only) and/or an explicit H-12 mitigation entry is still worth
  considering — flagged, not opened here.
  Cites D-41, D-43, D-45, D-47; H-12, SR-001, SR-014.

---

### D-49 — Action space stays steering-only (1-D) for the track-E Gazebo verdict; throttle-as-action (2-D) stays outside GE4 as posterior work

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (`action_space`); `docs/09` §3 (ED-2); `docs/13`/`docs/14` (Isaac posterior); D-59 (Gazebo 2-D posterior); SR-009 (`docs/03`); `docs/07` note ⁸ |
| Status | CONFIRMED for the verdict (steering-only retained for E/GE4); 2-D implemented later as posterior work in Isaac and Gazebo |
| Date | track 'E' / GE4-V2 (27.06.2026) |

**Decision.** The track-E camera policy keeps the **steering-only 1-D action space** (`ACT_DIM = 1`,
throttle fixed at cruise) for the whole Gazebo E verdict, per the original **ED-2** design choice
(`docs/09` §3: steering-only, fixed speed — lower dimensionality, faster learning, PD baseline stable
at fixed speed). Expanding **the verdict** to a **2-D action (steering + throttle)** is deferred;
at the time of this decision the separate posterior retrain was assigned to Isaac
(`docs/13`/`docs/14`), where it would not disturb the frozen Gazebo verdicts. D-59 later added a
Gazebo counterpart under the same posterior-only boundary.

**Rationale.** The question surfaced from SR-009: its H-08 *stall* sub-mode (M-P6) and its negative
test SC-PERT-03 are **ill-posed for a steering-only policy** — with no speed authority the policy
cannot converge to inaction (M-P6 ≡ 0 by construction) and the SC-PERT-03 reward injection
`r' = r − λ·|throttle|` is a constant (inert). Making them well-posed needs throttle-as-action. But
doing that **now** would (i) invalidate the **frozen F-track baseline** and the controlled F-vs-E
"cost of camera" comparison (both built on the same 1-D action), (ii) force a **full E-main retrain**
(larger than ruta-2a, explicitly out of scope), (iii) require **re-calibrating the cage speed rules**
(C-04/C-05/C-06) and the throttle-override perturbation (SC-EDGE-03), all of which assume exogenous
throttle, (iv) **re-run every GE4 campaign**, and (v) change the thesis question itself — with the
policy controlling throttle the cage's speed rules *arbitrate against* the policy, a different (richer)
safety problem than the cage-as-filter study the thesis poses. The cost is disproportionate to closing
one CL-B SR that resolves cleanly as N/A (note ⁸).

**Consequences.**
- SR-009 stall arm is **N/A-by-construction** (M-P6 ≡ 0; steering-only) and its M-S2-monitoring
  arm is covered; SC-PERT-03 is documented **N/A for this action space** (not `insufficient_evidence`).
- **Posterior work (originally Isaac; Gazebo counterpart added by D-59):** a 2-D action makes
  SR-009's liveness well-posed (real stall test, genuine
  C-04/C-05 exercise) and is closer to real driving. The throttle→speed plumbing already exists
  (`docs/09`: `linear.x = fixed_speed · clamp(throttle/throttle_nominal, [0.35, 1])`; the cage already
  modulates speed), so the cost is the **retrain + re-baseline**, not the wiring. Captured in
  `docs/13`/`docs/14` and D-59 after E4 closed.
  Cites ED-2 (`docs/09`), D-44 (Isaac), D-47, D-48; SR-009, H-08.

**Scope clarification (20.07.2026).** “Deferred” froze the **verdict contract**, not the
simulator executable forever. D-59 subsequently instantiated the same 2-D action in Gazebo and
PPO/SAC policies were trained and evaluated there as posterior E5 evidence. This does not turn
those runs into a re-run of GE4, and it does not change the G4 disposition of SR-009: the
SC-PERT-03 two-arm stall injection still has not been executed for a 2-D policy. Its
preregistered execution path is now implemented (`lambda_stall = 4.0`, 50k one-shot
continuation, `M-P6 > 50.0` on the metric's 0–100 scale, 20 cells per arm/mode, hash-pinned
manifest and independent arm aggregation). This fixes the former 0.50/50 % unit mismatch
before any result existed. The Gazebo posterior makes the test technically well-posed and
reproducible; it does not retroactively alter the 1-D verdict where M-P6 ≡ 0, nor close SR-009
until the prepared protocol is actually executed.

---

### D-50 — Isaac full-authority training environment: 2-D action (steering + throttle) + multi-circuit per-episode sampling

| Field | Value |
| --- | --- |
| Section | `gazebo_lane_env.py` (`action:` block, `circuits=`), `cage_bridge.py` (2-D maps), `rewards.py` (`throttle_delta`), `tools/isaac_scene.py` (multi-track scene, `load_circuits`), `tools/isaac_train.py` (defaults), `src/cobraflex_rl/config/train_isaac_2d.yaml`, `scripts/generate_complex_track.py` (`complex_d`/`complex_e`) |
| Status | VERIFIED on the Ubuntu + Isaac host 03.07.2026 (URDF→USD PASS; multi-circuit scene + Lane-Cam far-clip isolation confirmed by renders; 20k full-authority pilot `isaac2d_pilot_20k` completed end-to-end; C-04/C-06 interplay probed, no oscillation — closure note below. Authored 02.07.2026: design + code + unit tests on the Windows host) |
| Date | Isaac posterior track (02.07.2026, G4 closed) |

**Decision.** The Isaac posterior track (D-44) takes up the D-49 deferral: the training environment
now supports a **config-gated 2-D action** — `action.type: steer_throttle` — and **multi-circuit
per-episode track sampling**, both **inert by default** so every frozen F/E-track config, run and
verdict stays bit-identical (the default `action.type` is `steer`, the 1-D ED-2 contract; regression
suite 498-green). `tools/isaac_train.py` defaults to the new
[`train_isaac_2d.yaml`](../src/cobraflex_rl/config/train_isaac_2d.yaml) on the multi-track scene
`complex_b,complex_d,complex_e` — a bare `isaac_train.py` is the full-authority camera run.

**Design (2-D action).**
- The policy emits `[steer, throttle] ∈ [-1, 1]²` (symmetric Box, SB3-friendly); throttle maps to the
  **cage scale** `u = (a+1)/2 ∈ [0, 1]` (`policy_throttle_to_cage`). The cage rules already operate on
  a `(steering, throttle)` tuple on exactly this scale — C-04 attenuates throttle at
  `k_throttle_per_mps = 5.0` per m/s excess, C-06 rate-limits it at `0.10`/cycle — so **no cage code or
  cage.yaml change** is needed; `cage.yaml` 0.6.1 is consumed as-is (thresholds stay
  `[provisional]`, now actually exercised).
- Actuation uses a new linear map (`target_speed_from_throttle_2d`):
  `speed = max_speed_mps · u`, **full stop below `throttle_deadband` (0.05)** and **no lower speed
  clamp** — unlike the 1-D deployment map (floor `0.35·cruise`), the cage's attenuation has authority
  all the way to zero. `max_speed_mps = 0.5` **= C-04's `v_max_straight` = ODD-1.V_MAX**: the 1-D
  actuation capped speed at `fixed_speed = 0.20` **below every C-04 ceiling** (curve floor 0.25), which
  is why the speed rules were *structurally latent* (M-S2 ≡ 0 in-ODD, F4/GE4 central finding). With
  0.5 m/s authority the policy can genuinely exceed the curve ceiling and C-05's high-energy warning
  band (`v_warning` 0.4), so **the cage speed rules arbitrate against the policy for real** — the
  richer safety question D-49 anticipated.
- C-06's throttle rate limit then bounds commanded acceleration to
  `max_speed · 0.10 / control_dt = 0.5 m/s²` at 10 Hz — inside the platform's measured 0.53 m/s²
  (docs/14 §2.3); the alignment is pinned by a unit test.
- **Reward** gains a `throttle_delta` term (weight default **0.0** → legacy returns bit-identical) on
  the **raw policy** throttle delta — the longitudinal mirror of the v1.2 steering-smoothness
  rationale (C-06 absorbs post-cage deltas for free, §7.5.2). `fixed_speed` stays the progress
  normaliser (≈1.0 per cruise step); the `[-2, 2]` progress clip deliberately caps the speed incentive
  at 2·cruise = 0.4 m/s = `v_warning`, so reward alone never pushes past the warning band — ceilings
  are probed by exploration, answered by the cage.
- SC-EDGE-03's throttle-override perturbation keeps precedence over the policy throttle (eval
  stressor); `raw_throttle`/`safe_throttle`/`throttle_correction` are logged in `info` on both paths
  and `action_samples.csv` gains a `raw_throttle` column (readers are column-name based).

**Design (multi-circuit).** `GazeboLaneEnv(circuits=[...])` pre-builds per-circuit trackers and
samples one circuit per episode via the seeded `np_random` (`options["circuit_index"]` pins it for
deterministic eval; `info` carries `circuit_index`/`circuit_name`). `isaac_scene.add_track` accepts a
comma-separated `TRACK` list and lays the circuits out with **`TRACK_GAP_M = 15 m`** between bounding
boxes — the Lane-Cam far-clip distance, so a neighbouring circuit is never inside the frustum and each
circuit renders exactly as it would alone. Track materials stay at the **shared fixed prim paths**, so
`isaac_dr`'s scene randomization re-colours all circuits coherently per episode; one union grass
backdrop covers the gaps. `isaac_scene.load_circuits` resolves per-track env geometry from the
config-dir naming convention (`<name>_right_lane_centerline.yaml` + `<name>_centerline.yaml`) and
shifts it by the same scene offsets — geometry and rendering cannot drift. Run metadata records
per-circuit YAML paths + hashes.

**New tracks.** `complex_a`/`complex_c` (existing presets, now generated) violate the monocular
**curvature boundary** (docs/12 §4.7: driven-lane R < ~0.9 m ⇒ false C-02/C-05 emergencies), so they
suit only ground-truth-cage or monitoring runs. Two new **CV-safe presets** were designed against that
boundary for the camera training set: `complex_d` (bottom straight + wide single-valley "V" top;
centre/driven-lane R_min 0.884/0.932 m) and `complex_e` (top straight + soft double-dent "W" bottom;
0.787/0.907 m) — complex_b, the proven GE4-V2 circuit, is 0.876/0.998 m. All 2-lane, 0.52 m road,
right-lane driven, both handedness. *(complex_e re-cut **clockwise** 03.07.2026: D-51 supersedes
its geometry — R_min 1.079/0.956 m.)*

**Consequences.**
- SR-009's stall/liveness sub-mode is **well-posed** on this action space (a true stop is
  commandable; M-P6 becomes meaningful) and SC-PERT-03 becomes exercisable — on the *Isaac* policy,
  as posterior work; **G4 and the Gazebo verdicts are not reopened** (D-49 stands for track E).
- A policy trained under this config is a **new baseline** (new action space, new simulator, new
  circuits) — never comparable run-for-run with the 297k E-main.
- C-04/C-05/C-06 speed parameters remain `[provisional]`; first 2-D pilots should watch the
  C-04-attenuation/C-06-rate interplay (5.0 per-m/s gain over a 0.5 m/s span is a strong proportional
  correction) and re-tune via the cage.yaml update procedure if it oscillates — that is now a
  *measurable* behaviour instead of a latent one.
- Host-deferred (per D-44 precedent): `py_compile` + rclpy-free imports + 498 unit tests pass on the
  authoring host (incl. 16 end-to-end env tests driving the real cage through a fake interface: C-04
  fires on overspeed, C-06 clips throttle jumps, stall reachable, circuit sampling reproducible);
  the live Isaac flow (USD multi-track build, Replicator, SB3-in-Isaac) must be confirmed on the
  Ubuntu + Isaac host.
- **Host-deferral CLOSED 03.07.2026 — live-validated on the Ubuntu + Isaac 6 host.** pytest 503-green
  there too; `isaac_import_check.py` PASS; the three-circuit scene builds at the exact designed
  offsets (+0.0 / +24.766 / +49.724 m, 15 m bbox gaps, one union grass backdrop) and per-circuit
  Lane-Cam renders confirm the far-clip isolation (no neighbour in frame, incl. the tightest case:
  complex_e's start looking at complex_d's bbox ~16.2 m away). 20k full-authority pilot
  `experiments/sim/training/isaac2d_pilot_20k/` (seed 2024, config = `train_isaac_2d.yaml` with
  `total_timesteps: 20000` only) completed: `ep_len_mean` 13.5 → 35.6 (episodes survive spawn
  priming), `ep_rew_mean` 7.8 → 28.5, `raw_throttle` logged, per-circuit hashes + `action` block in
  the metadata, **C-04 active on 0.7–1.8 % of steps** (the latent→measured flip this decision
  predicted; emergencies ≤ 6.5 %). **C-04/C-06 interplay probed** (scripted full-throttle run,
  `isaac2d_pilot_20k/validation/throttle_probe.csv`): acceleration is slip-limited by the 0.05 sim
  friction to ~0.49 m/s² (numerically coincident with C-06's 0.5 m/s² commanded bound); the straight
  ceiling is reached with **zero speed-rule chatter**, and when the contextual ceiling drops below
  the commanded speed C-04 escalates within one cycle to a C-05 emergency stop (safe u = −0.5) —
  **no C-04/C-06 sawtooth observed; no cage.yaml re-tune needed** (thresholds stay `[provisional]`).
  Throughput on this scene (multi-track + full DR + 2-D, RTX 5060): ~25 env-steps/s steady-state
  headless → budget ~11 h for the 1M run on this GPU class.
  Cites D-44, D-49, ED-2 (`docs/09`); SR-004, SR-009, H-03, H-08; docs/12 §4.7.

### D-51 — complex_e re-cut clockwise: steering-handedness balance for the Isaac multi-track trio

| Field | Value |
| --- | --- |
| Section | `scripts/generate_complex_track.py` (`_complex_e_cw_waypoints()`, `TRACKS["complex_e"]`); regenerated `experiments/sim/tracks/complex_e/`; `src/cobraflex_rl/config/complex_e_centerline.yaml` + `complex_e_right_lane_centerline.yaml` |
| Status | ACCEPTED — regenerated + live-verified on the Isaac host 03.07.2026 |
| Date | Isaac posterior track (03.07.2026) |

**Decision.** The D-50 CV-safe trio was steering-imbalanced: all three circuits were
counter-clockwise, so the driven right lane accumulated **36.5 m of left-turning arc vs 4.5 m
right (8.1:1)** across the trio — a camera policy trained on it would overfit left-steer
commands (user direction 03.07.2026: invert one circuit so the opposite steering commands get
trained; visually complex_d/complex_e were also near-identical silhouettes). `complex_e` is
re-cut as the **clockwise** member — same design family (top straight, wide U-turn ends, "W"
bottom with a central counter-steer crest) driven the other way round: per-lap driven turning
arc **2.6 m left / 10.4 m right**; trio balance now **28.3 m / 14.2 m ≈ 2:1**, with ~⅓ of
episodes fully immersed in a right-turn-dominant circuit.

**Why a re-design, not a plain mirror.** Handedness flips which side of the U-turns the driven
right lane takes: CCW puts it OUTSIDE (driven R = centre + 0.1225 m — how the old
0.787-m-centre complex_e was CV-safe at 0.907 m driven), CW puts it INSIDE (driven = centre −
0.1225 m). The plain mirror measured **0.667 m driven** — well under the docs/12 §4.7 ~0.9 m
monocular boundary (false C-02/C-05 emergencies). So the end U-turns widened to **R = 1.4 m
semicircles** (driven ≈ 1.28 m) and the bottom became an analytic **cosine W** (amplitude
0.145 m, half-period 1.305 m → nominal extremum R 1.19 m centre / ≈1.06 m driven at the two
lows), joined to the arc bottoms through short straight buffers landing on horizontal-tangent
cosine peaks.

**Catmull-Rom lesson (why the preset is a dense analytic builder, not hand waypoints).** Twelve
sparse-waypoint candidates all failed the boundary (measured R_min 0.44–0.89 m): uniform
Catmull-Rom kinks wherever curvature flips sign (tangent magnitude ∝ neighbour spacing →
overshoot at the joins) and a 3-point curved feature runs ~2–3× tighter than its circumradius.
`_complex_e_cw_waypoints()` therefore samples the analytic composite (straight + circle arcs +
cosine W) every 0.25 m — the spline then follows it to ~1 %.

**Verified.** Generator: 411 points, perimeter 20.55 m, centre R_min 1.08 m, both handedness
TRUE. Shipped YAMLs: clockwise (negative signed area); driven R_min 0.956 m (design estimator)
/ 0.904 m on the rounded YAML — complex_d reads 0.895 m on the same yardstick. pytest 503
green; `check_traceability` PASS; live Isaac multi-track scene re-rendered + lane-cam from the
new start (scene offset shifts +49.72 → +49.92 m; Lane-Cam far-clip isolation still holds).
A second 20k full-authority pilot on the CW trio completed end-to-end
(`experiments/sim/training/isaac2d_pilot_20k_d51/`, seed 2024: metadata records the NEW
complex_e lane hash `a271bc48ef…` at offset +49.9151; episodes healthy throughout — ep_len_mean
15–25, no spawn deaths; cage live, C-04 0.8–1.6 %/step; scene renders archived under its
`validation/`). Its end-of-run reward (13.6) sits below the pre-D-51 pilot's (28.5) — expected
at a 20k budget now that ~⅓ of episodes land on an unseen opposite-handed circuit; not a
health signal.

**Consequences.** The D-50 20k pilot (`isaac2d_pilot_20k`) ran on the ORIGINAL CCW complex_e —
its per-circuit metadata hashes are a historical snapshot; the 1M full-authority run trains on
the CW geometry. D-50's complex_e description is superseded (annotated in place);
complex_a–complex_d assets untouched; Gazebo verdicts untouched.
Cites D-50; docs/12 §4.7; docs/13.

### D-52 — Isaac 2-D training iteration 2: entropy bonus (ent_coef 0.01) after run-1 exploration collapse; STOP-file graceful stop; in-process nominal evaluator

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/config/train_isaac_2d.yaml` (`ent_coef` 0.0 → 0.01); `tools/isaac_train.py` (`StopFileCallback`); new `tools/isaac_eval.py`; run records `experiments/sim/training/ppo_isaac2d_2024_1M/` + `experiments/sim/eval_isaac/` |
| Status | ACCEPTED — run 2 (`ppo_isaac2d_v2_2024_1M`) launched 03.07.2026 23:46 on this basis |
| Date | Isaac posterior track (03.07.2026) |

**Run-1 outcome (the evidence).** `ppo_isaac2d_2024_1M` (seed 2024, commit `e51984f6`, the D-50
full-authority config on the D-51 trio) was stopped at **~88 % (880k)** after `ep_rew_mean`
peaked at **61.5 @ ~208k** and decayed to a noisy 20–40 plateau. PPO health shows the mechanism:
the policy std fell **0.99 → 0.095 by 36 % → 0.023 by 88 %** (entropy +2.8 → −1.86) with
`ent_coef 0.0` — **exploration collapse**, the same failure family as the Gazebo 1M (D-46 era),
now on a much harder task (2-D action + three circuits incl. opposite handedness + full DR).
**Nominal eval** (new `tools/isaac_eval.py`, DR/spawn-perturbation off, deterministic, 3 ep ×
3 circuits, enforcement): the **225k peak checkpoint** manages ≤ **0.45 laps** (crawl speeds
0.09–0.25 m/s, 7/9 episodes end in a C-05 cage emergency); the **875k final** is *worse*
(mostly 25–80 steps, 8/9 emergencies, faster-but-blinder) — the plateau decay was real
capability loss, so the peak-rescue playbook (297k precedent) applies but the rescued policy
is nowhere near robust. The cage held throughout: only 2/18 nominal episodes ended off-road.

**Decision.** Iteration 2 changes **one substantive lever**: `ent_coef 0.0 → 0.01` — an entropy
bonus sized to keep the 2-D Gaussian stochastic long enough to discover the full-lap mode
instead of freezing into crawl-and-die. Everything else (reward weights, DR, v3 stability
stack, circuits, seed 2024) stays identical for attributability. Two tooling fixes ride along:
(1) **`StopFileCallback`** — `touch <run_dir>/STOP` ends `learn()` gracefully (model + metadata
written, status `interrupted`); needed because SIGINT hard-kills the kit process before any
Python `finally` (verified on run 1: its metadata had to be reconstructed post-hoc, 297k
precedent). (2) **`tools/isaac_eval.py`** — the in-process nominal evaluator used above
(per-circuit laps via arc-length unwrap, |ey|, speed, per-rule interventions, emergencies;
JSON record with ckpt hash + git commit), the D-50 "follow-on eval tooling" first slice.

**Exit criteria for iteration 2.** Watch std (should stabilise ≫ 0.1) and `ep_rew_mean`; a
healthy run should show nominal-eval laps ≥ 1 on complex_b/d and ≥ 0.5 on complex_e at its
peak checkpoint. If run 2 still collapses or plateaus lap-less, next levers (in order):
reward rebalance (termination penalty vs progress incentive), DR curriculum (start narrow,
widen), longer horizon (>1M).
Cites D-49, D-50, D-51; docs/10; docs/13; §7.7.8 (Gazebo 1M sawtooth/collapse precedent).

### D-53 — Isaac 2-D training iteration 3: DR curriculum (stage 1 = visual-only DR) after run 2 falsified the exploration hypothesis

| Field | Value |
| --- | --- |
| Section | new `src/cobraflex_rl/config/train_isaac_2d_stage1.yaml`; run records `experiments/sim/training/ppo_isaac2d_v2_2024_1M/` + `experiments/sim/eval_isaac/` |
| Status | ACCEPTED — stage-1 run (`ppo_isaac2d_stage1_2024_1M`) launched 04.07.2026 05:09 |
| Date | Isaac posterior track (04.07.2026) |

**Run-2 outcome (the evidence).** `ppo_isaac2d_v2_2024_1M` (D-52: `ent_coef 0.01`, all else =
run 1) did what the lever promised — std decayed ~5× slower (0.79 @ 103k, 0.34 @ 206k,
0.12 @ 411k, 0.094 @ 516k vs run 1's 0.095 by 360k) — and **still never found the lap mode**:
`ep_rew_mean` peaked lower (43.5 @ 258k vs 61.5) and plateaued in the 18–32 band. Stopped at
**52 % (518k)** by the pre-declared rule via the new STOP file (first live use: graceful end,
model + metadata written, `status: interrupted`). **Nominal eval:** the 250k peak checkpoint is
*worse* than run 1's (6/6 C-05 emergencies, ≤ 0.25 laps — either 5–29-step dashes or a
920-step crawl at 0.058 m/s); the final model is degenerate (8-step dashes or a **0.021 m/s
stall-crawl** at |ey| 112 mm until C-05 fires — the SR-009/M-P6 stall mode is now an observed
behaviour on the 2-D action, not a hypothetical).

**Decision.** Exploration was the wrong (or at least insufficient) bottleneck — with sustained
exploration the policy still cannot master even the nominal slice while training under the
FULL sim-to-real DR (dynamics + scene + visual) from step 0. Iteration 3 therefore switches
lever to the **DR curriculum**: **stage 1** trains with **visual (H-10) DR only** — exactly the
proven Gazebo E-main recipe, which reached 4.88 laps — on the D-51 trio, via the new
`train_isaac_2d_stage1.yaml` (deltas vs `train_isaac_2d.yaml`: `dynamics_randomization` +
`scene_randomization` OFF, own `model_path`; `ent_coef 0.01` kept — harmless, and D-52's
attribution chain stays clean). **Stage 2** (once stage 1 produces a lap-completing champion):
`--resume-from` that checkpoint under the full-DR `train_isaac_2d.yaml` to re-widen toward
sim-to-real.

**Exit criteria for stage 1.** Nominal-eval laps ≥ 1 on complex_b/d and ≥ 0.5 on complex_e at
the peak checkpoint. **Watch item:** if stage 1 also converges to crawl/stall (its final-model
signature above), the DR was never the binding constraint and the next lever is the **reward
rebalance** — a stall penalty below `throttle_deadband` and/or a higher `forward_progress`
weight (docs/10 procedure).
Cites D-50, D-51, D-52; SR-009 (M-P6); docs/10; docs/11 (E-main recipe).

### D-54 — Isaac yaw-authority calibration: cage `yaw_gain` 0.8 → 2.4 (CV-parity feasibility campaign)

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/config/train_isaac_2d.yaml` + `train_isaac_2d_stage1.yaml` (`cage.yaw_gain`); `tools/isaac_eval.py` (`--controller cv`, `--cv-speed`, `--cv-yaw-boost`, `--dump-frames`); probes under `experiments/sim/eval_isaac/` |
| Status | ACCEPTED — validated by CV parity probes 04.07.2026; v4 training launched on it |
| Date | Isaac posterior track (04.07.2026) |

**Finding.** After stages 1/1b plateaued at ~0.63 laps, the control experiment that
discriminates RL-vs-environment ran: the **non-learned CVLaneController** (pure pursuit on
the D-43 estimator — 4.85 laps / 17 mm on Gazebo complex_b) was driven through the SAME
in-process Isaac env (`isaac_eval --controller cv`). Result: it **dies at the first curve it
meets on every circuit** (complex_b 45 steps, complex_d 42; complex_e tracks its long
straight at |ey| 3.8 mm then dies at its first turn). Cause: the Isaac skid-steer delivers
only **~18 % of commanded yaw** at the calibrated friction 0.05 (docs/13 `--turn` test:
2.9 rad/s commanded → 0.53 achieved), and `yaw_gain 0.8` caps the command itself — the
achievable yaw sits below the requirement of every curve (v/R ≈ 0.17 rad/s at cruise).
Every controller — CV and all three RL runs — was walled by actuation, not by learning.

**Decision.** Raise the Isaac configs' `cage.yaw_gain` to **2.4** (3× command headroom; the
plant's attenuation then leaves ~0.4–0.5 rad/s achievable). Boost sweep on complex_b
(`--cv-yaw-boost` k∈{2,3,4,5}): k=2 → 0.27 laps; **k≥3 saturates at 0.42–0.44 laps with
mm-clean tracking (|ey| 13–14 mm)** — a 10× track-coverage gain that then exposed the
SECOND wall (D-55). Speed (0.09–0.19 m/s) and friction (0.03/0.05) sweeps left the second
wall's location invariant — confirming the yaw fix is the right and complete actuation-side
correction. Gazebo configs untouched (their plant delivers commanded yaw ~1:1).
Cites D-43, D-50, D-53; docs/12 §7.5 (CV baseline); docs/13 (physics tuning, --turn).

### D-55 — Isaac cage variant `cage/cage_isaac.yaml`: C-02 heading thresholds re-calibrated for the Isaac renderer; residual localized perception failure documented

| Field | Value |
| --- | --- |
| Section | new `cage/cage_isaac.yaml` (theta_max 25°→40°, theta_warning 20°→35°, both `[provisional, Isaac]`); Isaac train configs (`cage.yaml_path`); post-mortem evidence `experiments/sim/eval_isaac/cv_controller_0.2mps_frames/` + parity JSONs |
| Status | ACCEPTED — canonical `cage/cage.yaml` (Gazebo, verdicts) UNTOUCHED |
| Date | Isaac posterior track (04.07.2026) |

**Finding (the second wall).** With yaw fixed (D-54), every CV probe still died by
**C-05 at one fixed location** (complex_b s ≈ 8.3–8.5 m, the right-U-turn exit), invariant
to speed and friction, while driving mm-clean: the dumped trace shows TRUE ey −27 mm /
epsi −6.4° at the kill, killed by `C-02|C-05`. The cage's own estimate at that moment:
**`cv_epsi` over-reads by ~+19° persistently on curves** on Isaac pixels (measured −0.30 rad
at true +0.03) — the docs/12 §4.7 monocular over-read, re-based by the Isaac renderer, which
pushes complex_b's knife-edge geometry (driven R_min 0.998 vs boundary ~0.9) over the 25°
Gazebo-calibrated `theta_max`. The dumped death frame shows the lane fleeing the image at
the U-turn exit.

**Decision.** A dedicated **`cage/cage_isaac.yaml`** (selected via the Isaac configs'
`cage.yaml_path`) carries `theta_max` **40°** / `theta_warning` **35°**, `[provisional,
Isaac renderer calibration]` — sized as Gazebo 25° + measured over-read ~19° − margin.
C-01 (lane boundary) and C-03 (TTLC) keep full sensitivity, so real departures remain
guarded; C-02 at 40° still catches genuine heading runaway (H-02) net of the over-read.
Threshold escalation beyond 40° is **futile and refused**: at 45° the kill becomes pure
C-05 with no C-02 — the D-43 supervisor rejects the wild fits at that viewpoint and the
**missing-state budget** (5 cycles) stops the run, i.e. the cage correctly refuses
prolonged blind driving. **Residual (documented, accepted):** at that ONE viewpoint the
fixed-line CV controller is a coin flip — 0.971 laps (one C-03-working, zero-emergency
near-lap) vs ~0.45 across repeats; an RL policy can learn lines/speeds that keep the
estimator plausible (operationally, CV-safe driving), which the fixed controller cannot.
The deep fix — supervisor/estimator re-calibration for the Isaac renderer — is future
work (D-43 territory), required before any Isaac EVALUATION verdict; for TRAINING the
residual is acceptable noise.
Cites D-43, D-54; docs/12 §4.7; H-02, H-12, SR-002.

### D-56 — reward `stall_penalty`: the 2-D action's degenerate "park" optimum made unprofitable

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/cobraflex_rl/rewards.py` (new `stall_penalty` / `stall_progress_min` keys, default 0.0 → bit-identical); `policy/tests/test_rewards.py` (+3); Isaac configs (`stall_penalty: 0.5`, `stall_progress_min: 0.25`, `[provisional]`) |
| Status | ACCEPTED — v6 (`ppo_isaac2d_v6_2024_1M`) launched 05.07.2026 10:48 on it |
| Date | Isaac posterior track (05.07.2026) |

**Evidence.** v5 (full 1M on the D-54/55 env + widened budgets) trained to the loop's
all-time reward record (227.8 @ 844k, ep_len 389) — but its nominal evals expose the
inflation: alongside honest 0.6-lap drives sit **1747–2200-step idles at 0.005–0.03 m/s**
(truncation without progress). The park mode is the mirror of v4's fast-and-reckless
optimum: near-zero progress collects ~0/step but avoids the −25 termination AND — with the
D-55 blind-stretch budgets — the cage no longer executes a stopped vehicle promptly. The
reward's "each on-track step net-positive" design (D-34) closed the die-early incentive
but left not-driving free. SR-009's stall concern (M-P6), observed twice (run-2 final,
v5), is now a measured training attractor.

**Decision.** New reward term: a per-step `stall_penalty` charged while normalised
progress < `stall_progress_min` (0.25 ≈ 0.05 m/s at cruise — slow-but-driving at
≥ 0.05 m/s is never charged; parking for an episode now costs ~−0.5 × steps, strictly
worse than any driving-and-failing trajectory). Default weight 0.0 → every pre-D-56
config/return bit-identical (pytest 506, incl. 3 new pins). v6 = v5 + this term (single
attributable delta).
Cites D-34 (§7.2.3 net-positive design), D-50, D-53 (pre-declared reward-rebalance lever),
D-55; SR-009 (M-P6); docs/10.

### D-57 — perception fix: estimator heading de-bias for the Isaac renderer (the binding constraint, attacked directly)

| Field | Value |
| --- | --- |
| Section | `cv_lane_estimator.py` (new `heading_bias_rad`, default 0.0 → Gazebo bit-identical); `gazebo_lane_env.py` + `tools/isaac_eval.py` (config-gated `cage.perception_heading_bias_rad`); `policy/tests/test_cv_lane_estimator.py` (+2); Isaac configs; new `train_isaac_2d_d57.yaml` |
| Status | ACCEPTED — CV-validated; v7 (`ppo_isaac2d_d57_2024_1M`) launched 05.07.2026 19:59 |
| Date | Isaac posterior track (05.07.2026) |

**Root-cause measurement.** The D-56 conclusion (config levers exhausted; wall = perception)
was acted on, not deferred. Instrumenting the CV controller's per-step cage estimate on
complex_b (`…/cv_controller_0.2mps_frames/trace.csv`) shows `cv_epsi` carries a **systematic
negative bias vs true heading**: mean **−4.8°** on the straight, heading-≈0 stretches
(correlation with true only +0.47), worsening to **−13 to −17°** at the complex_b U-turn exit
(s≈8.4 m) where the IPM shear compounds it. This is a **camera-extrinsic calibration mismatch**:
`camera_geometry`'s IPM (pitch 0.30 rad, height 0.077 m) is Gazebo-calibrated, and the Isaac
RTX render of the same URDF yields a rotated near-field lane slope. It is the exact quantity
that trips C-02/C-05 at that viewpoint and caps every controller.

**Decision.** A config-gated `heading_bias_rad` subtracts the calibrated offset from the
estimator's heading (`heading -= heading_bias_rad`), so a straight-ahead vehicle reads epsi ≈ 0.
Default 0.0 → the Gazebo estimator and every D-43 verdict are bit-identical (2 new unit tests
pin inert-at-0 + exact-shift); the Isaac path sets **+0.084** (the measured straight bias),
threaded via `cage.perception_heading_bias_rad` into both the env's cage supervisor and the CV
baseline. This is calibration, not masking: C-01 (offset), health and plausibility keep full
sensitivity; only the heading readout is de-biased.

**CV validation (partial — honest).** With the de-bias the CV reference reaches **0.977 laps**
on complex_b (vs 0.45 typical / 0.97 once pre-fix), but 2/3 episodes still die at the U-turn:
the static offset removes the dominant systematic component, **not** the curve-compounded IPM
shear (a full fix needs pitch/height re-calibration of `camera_geometry` for Isaac — deeper
D-43 work, future). But a *trained* policy — unlike the fixed-line CV — can learn a line/speed
that keeps the de-biased estimator plausible through the U-turn. **v7 tests exactly this:** the
champion **stage-1 recipe** (visual-DR-only, yaw 0.8, canonical 25° cage, ent 0.01, no D-54/55/56
env deltas — the recipe that produced the 0.63 champion) **+ the D-57 de-bias only** (single
attributable delta vs the champion). Success criterion: nominal-eval laps > 0.63 (beats the
standing champion) toward ≥ 1.
Cites D-43 (estimator), D-54/55/56 (levers now behind the perception fix); H-02, SR-002;
docs/12 §4.7.

**v6 RESULT + config-lever exhaustion (05.07.2026).** v6 removed the park exploit (0 stall
episodes in eval, vs v5's) but **overcorrected to v4's fast-and-reckless mode**: at
`stall_penalty 0.5` the policy floors the throttle and dies at the FIRST curve (nominal
eval: complex_b/d 0.04 laps / 36–45 steps at 0.19–0.21 m/s; peak-550k *worse* than final).
This closes the config-lever campaign (D-52..D-56) with a clear, non-obvious finding:

| iter | delta vs prev | nominal champion (laps) | failure |
| --- | --- | --- | --- |
| stage-1 | curriculum (visual-DR-only, yaw 0.8, canonical cage) | **0.63** | perception wall @ s≈8.4 m |
| v4 | +yaw 2.4, +cage_isaac 40° | 0.31 | first-curve (speed) |
| v5 | +wide blind budgets | 0.62 *but stall-inflated* | park exploit + perception wall |
| v6 | +stall_penalty 0.5 | 0.31 | first-curve (speed, overcorrected) |

**The env "fixes" (D-54/55/56) each helped the hand-tuned CV controller drive farther yet
made the RL OUTCOME worse or no better** — the champion across all 6 iterations remains
**stage-1** (0.63 laps, hash `c61d4a7e`), trained on the *un-fixed* env. Interpretation: the
extra yaw authority + widened budgets expand the action/□tolerance space into regions PPO
exploits badly (oversteer → C-02/C-05; idle → park), while the one thing that stops even the
clean stage-1 driver — the **monocular estimator's persistent ~+19° over-read at the
complex_b U-turn exit (s≈8.4 m)** — is untouched by any of these levers. Both the CV
reference (0.45 typical, 0.97 once) and every RL policy cap at this viewpoint. **Config-space
is exhausted; the binding constraint is proven to be perception.** The pre-declared next
lever is therefore the deep one (D-43 territory): estimator/renderer re-calibration for the
Isaac RTX pixels at the failing viewpoint (frames + per-step cv_ey/cv_epsi traces archived
under `experiments/sim/eval_isaac/cv_controller_0.2mps_frames/`), which is **required before
any Isaac evaluation verdict** regardless. Until then the Isaac champion is stage-1 — a caged
2-D camera policy that drives ~⅔ of a lap under full H-10 visual DR on three circuits
(incl. one opposite-handed) it never memorised — a legitimate sim-to-real demonstrator, not
a verdict.

**Addendum (05.07.2026) — blind-stretch budgets widened; threshold/budget levers now
exhausted.** Two further `[provisional, Isaac]` calibrations after v4's results:
(1) `cage_isaac.yaml` `n_missing_max_cycles` 5→13 + `staleness_max_s` 0.5→1.3 (Trigger 5/3);
(2) new config-gated env key `cage.perception_min_invalid_cycles` (unset = the Gazebo-tuned
supervisor default 4, bit-identical; Isaac configs set 12) so the D-43 supervisor's
invalid-persistence bridges the blind stretch instead of latching Trigger 8. Validation:
the wider budgets do NOT rescue estimator-consuming controllers — the CV now drives blind
into a real off-road (0.488 laps) and the pre-fix stage-1 champion stays at ~0.64 (its
learned line still dies there) — but they change what a policy TRAINED under them can
learn: the cage no longer executes a mid-line vehicle 0.4–0.5 s into the blind stretch, so
estimator-friendly lines are explorable. v4 (trained pre-widening) confirmed the training
coupling matters: it converged fast-and-reckless (0.30–0.35 m/s, killed at first-curve
entry, ≤0.31 laps nominal — worse than stage-1 despite the fixed plant). v5 = v4 + these
budgets (single delta) launched 05.07.2026 02:53. If v5 still caps below a lap, the next
lever is the deep one: estimator/renderer investigation at the failing viewpoint (frames
archived under `experiments/sim/eval_isaac/cv_controller_0.2mps_frames/`).

**Stage-1/1b CLOSURE (04.07.2026).** Stage 1b (+1M resume) plateaued below stage-1's band
(no new records in 519k extension steps; stopped by rule via STOP file at 1.52M) and its
best checkpoints eval at the same **~0.63-lap wall** as stage-1's. The wall was then
root-caused NOT to RL at all — see **D-54/D-55**: the non-learned CV reference controller
(4.85 laps on Gazebo complex_b) dies at the FIRST curve in Isaac (yaw-authority ceiling)
and, once yaw-boosted, at one fixed track location (perception failure on the Isaac
renderer). Iterations 1–3's lap ceiling was an environment defect, not a training defect.

**Stage-1 RESULT (04.07.2026) — curriculum hypothesis CONFIRMED; extended +1M (stage 1b).**
`ppo_isaac2d_stage1_2024_1M` completed the full 1M healthy: records almost to the end
(`ep_rew_mean` 10 → 223.4 peak @ 747k, final band 150–190; `ep_len_mean` peak 334; std annealed
0.73 → 0.034 WITHOUT collapse — reward kept rising as std fell; emergencies 0.1–1 %). At the
same 53k mark where runs 1–2 sat at 20–22 reward, stage 1 was at 52.3 — the removed
dynamics/scene DR was the binding constraint, as D-53 predicted. **Nominal eval:** the FINAL
model (not an earlier peak — no late capability decay this time) is the overall champion:
complex_b 0.46–0.63 laps (618–888 steps), complex_d 0.37–0.63 (405–934), complex_e 0.02–0.31;
episodes now reach the ~800-step/lap scale (user calibration 04.07.2026) at conservative
speeds (0.14–0.19 m/s). Failure signature is localised, not diffuse: **exactly one C-05 per
episode** ends an otherwise-clean run (C-02 nearly absent; C-06 smooths 70–80 % of steps);
|ey| 15–58 mm. The 725k near-peak checkpoint evals slightly worse — training-reward peak ≠
nominal champion. Still short of the ≥ 1-lap criterion → per the user's instruction (extend
steps if 1M falls short with slope remaining), **stage 1b launched 04.07.2026 13:03**:
`--resume-from` the stage-1 final under the same stage-1 config (+1M → 2M total; SB3
`reset_num_timesteps=False` adds the config's budget; LR resumes at ~1.5e-4 annealing to 0;
`ent_coef 0.01` carried inside the checkpoint), run `ppo_isaac2d_stage1b_2024_1M`. Stage 2
(full-DR fine-tune) queues behind whichever stage-1x checkpoint first meets the lap criterion.

### D-58 — hard-section spawn curriculum: `spawn_perturbation.random_start_s` (reusable training technique)

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (new `random_start_s` flag, default False → bit-identical); Isaac configs (`spawn_perturbation.random_start_s: true`); run `ppo_isaac2d_kin2_2024_1M` |
| Status | CONFIRMED (06.07.2026) — cracked the U-turn: kin2 cracked the U-turn: 275k peak 0.95 laps (near-full), 386k consistent 0.63 ×3/4 clean — both >= 0.63 champion, all cross the U-turn (slow to ~0.15 m/s). Consistency-vs-peak tradeoff; next: more steps/tune then curriculum up |
| Date | Isaac posterior track (06.07.2026) |

**Motivation (diagnostic finding).** The Isaac U-turn diagnostic (D-54..D-57 + the T1–T6
ladder) traced the ~0.4–0.6-lap wall to a **chicken-and-egg exploration gap**, not to the
task, the action dim, perception, or the cage: the tight complex_b U-turn (driven R ≈ 0.97 m)
is reached only *after* the policy survives the whole preceding straight, so early in training
it almost never gets there → **no gradient at the hardest section → it never learns the
slow-and-turn**, dies there, and the loop repeats. Every controller (2-D, 1-D, even the
perfect-state T5) capped at the U-turn; only the hand-coded CV (0.97) cleared it.

**Technique.** `spawn_perturbation.random_start_s` (config-gated, default **False** → every
existing config/RNG stream and all Gazebo/F-E verdicts bit-identical): when set, an episode
with no explicit `start_s` in `reset(options)` spawns at a **uniform random arc-length** along
the driven centreline (via `tracker.pose_at_arclength`, aligned to the local track heading +
the usual spawn perturbation) instead of always the start line. The policy then practises
**every part of the track — including the hard section — from step 0**, breaking the
chicken-egg. Deterministic eval and F4 scenario spawns are untouched (they pass an explicit
`start_s`/`circuit_index`, which takes precedence). 508 pytest green.

**Reusable beyond this case.** This is a general curriculum lever for any circuit with a
section the policy rarely reaches under start-line spawning (tight apex, chicane, adverse
camber). It is cheaper and less intrusive than reward shaping or per-section fine-tuning: one
config flag, no reward/geometry change, and it composes with DR and multi-circuit sampling.
Future trainings on harder circuits (complex_a/c, the CV-unsafe tight ones) or on the physical
platform's hard corners should reach for this first. **Caveat:** it changes the training-time
episode-length/return distribution (episodes start mid-track), so those training curves are
NOT comparable across the flag — judge only by deterministic nominal eval (laps from the start
line), never by training `ep_rew_mean`/`ep_len_mean`.

**Status note.** As of 06.07.2026 kin2 (2-D + yaw 0.8 champion recipe + `random_start_s`,
complex_b, 1M) shows the strongest Isaac training signal yet (ep_len_mean 269 with ~0 % cage
emergencies at 220k) but has NOT yet been nominal-evaluated; the lap verdict came in POSITIVE: kin2 @293k (vs champion 1M) hit **0.76 laps enforcement**
(truncated at the episode cap, still driving at 0.15 m/s — it learned to SLOW for the U-turn),
beating the 0.63 champion and clearing the U-turn for the first time; monitoring 0.55/0.66/0.47.
Inconsistent (2/3 episodes still die at the U-turn) → resumed with `max_episode_steps` 1024→2048
toward reliability + full laps. The finding
(under-visited hard sections need spawn diversity) stands on the T1–T6 + T5 evidence.
Cites D-54 (yaw), D-57 (perception), the T1–T6 ladder; SR-... none (posterior, no ID change).

### D-59 — Gazebo 2-D action config: which Isaac 2-D findings port to Gazebo (backend-agnostic vs renderer/kinematic-specific)

| Field | Value |
| --- | --- |
| Section | new `src/cobraflex_rl/config/train_ppo_camera_2d.yaml`; docs/11 §9 + docs/13 command reference (isaac_eval / kin2 curriculum / STOP) |
| Status | ACCEPTED — additive, no code change (the 2-D path is shared, D-50); pytest 52 (2-D env / rewards / cage_bridge) + a YAML-load smoke green; check_traceability PASS |
| Date | Isaac posterior track (06.07.2026) |

**Context.** The 2-D action (steering + throttle) was built for the Isaac in-process trainer
(D-50) but lives entirely in **shared** code: `GazeboLaneEnv` parses `action.type`, `cage_bridge`
maps throttle → cage `u` → speed (`policy_throttle_to_cage` / `target_speed_from_throttle_2d`),
`rewards` carries `throttle_delta` / `stall_penalty`, and `RosGazeboInterface.send_action`
already publishes a variable `linear.x`. So a Gazebo 2-D run needs only a **config**, not new
code. Motivation: a clean Gazebo counterpart to the Isaac 2-D track — Gazebo's DiffDrive
delivers ~1:1 yaw and its CV estimator is Gazebo-calibrated, so it isolates the 2-D action +
reward shaping + spawn curriculum WITHOUT the Isaac yaw-authority and renderer-perception
confounds (D-54/D-55/D-57) that dominated the Isaac U-turn diagnostic.

**Decision — the finding filter.** `train_ppo_camera_2d.yaml` = `train_ppo_camera.yaml` (the
frozen Gazebo E-main) + only the Isaac 2-D findings that are properties of the **action space /
reward** (backend-agnostic), and NONE of the Isaac-renderer/kinematic calibrations:

| Isaac finding | Port to Gazebo? | Why |
| --- | --- | --- |
| 2-D action, `max_speed_mps 0.5` (D-50) | **KEEP** | action-space design; cage speed rules (C-04/C-05/C-06) arbitrate, a true stop is commandable (SR-009 well-posed) |
| `ent_coef 0.0 → 0.01` (D-52) | **KEEP** | the 2-D Gaussian collapses exploration regardless of backend |
| `reward.throttle_delta 0.10` (D-50) | **KEEP** | longitudinal smoothness, mirror of `steer_delta` |
| `reward.stall_penalty 0.5` (D-56) | **KEEP** | the degenerate "park" optimum is a reward/action property — it will appear in Gazebo too |
| `cage.yaw_gain 2.4` (D-54) | **DROP → 0.8** | Isaac skid-steer delivers ~18 % of commanded yaw (needed a 3× boost); Gazebo DiffDrive ~1:1 → 2.4 would oversteer |
| `cage_isaac.yaml` θ_max 40° (D-55) | **DROP → canonical 25°** | the 40° absorbed the Isaac RTX heading over-read; Gazebo's estimator is 25°-calibrated |
| `perception_heading_bias_rad 0.084` (D-57) | **DROP → 0.0** | Gazebo is the calibration reference — no renderer bias to remove |
| `perception_min_invalid_cycles 12` (D-55) | **DROP → default 4** | the widened blind-stretch budget was for the Isaac renderer |

`random_start_s` (D-58) is exposed but default **False** (clean attribution + comparability;
flip it if the Gazebo 2-D run also caps at complex_b's U-turn). The `stall_penalty 0.5` carries
a caveat: in Isaac v6 it overcorrected to fast-and-reckless, but that was entangled with the
D-55 *loosened* Isaac cage (blind-stretch budgets that stopped executing a stalled car
promptly); Gazebo runs the canonical **tight** cage, so re-check and lower toward 0.2 if the
2-D policy goes reckless.

**Consequences.** Purely **additive** — the 1-D configs (`train_ppo_camera.yaml`,
`train_ppo.yaml`) have no `action:` block, so the env falls to the frozen 1-D contract,
bit-identical (`test_default_config_keeps_the_frozen_1d_contract`); GE4-V2 and every F/E
artefact are untouched, no re-runs. A policy trained here is a **new posterior baseline**, not a
re-run of the frozen GE4-V2 1-D verdict (D-49); it evaluates with the same config via
`eval_policy`. The deployed `vehicle_control_node` ROS graph (the F2 demo) stays 1-D — 2-D is
in-process training/eval only, mirroring Isaac (out of scope). Only `--train-config` selects it.

**Amendment / evidence follow-up (13–19.07.2026; no change to GE4).** The values above record
the 06.07 design point; the executed Gazebo sequence refined it as follows:

- **0.5 m/s is the historical full-authority PPO arm.** `ppo_gz2d_complex_b_2024` trained with
  that cap (628736 steps; reward peak 654.4 @ 510k). Its monitoring eval was competent
  (525k: 4.66 laps, 21.0 mm), but none of four enforcement runs completed: some crossed the
  speed envelope directly, while others escalated marginal/confident CV reads into C-05 stops
  at the higher-speed regime. On 13.07 the dedicated
  Gazebo 2-D configs were therefore revised to the **current 0.25 m/s cap**. Likewise,
  `random_start_s: false` remains the environment's inert default; the dedicated posterior
  configs used for the completed Gazebo 2-D trainings explicitly set it **true** (D-58).
- **0.22 m/s was an eval-only sensitivity probe, not a new default.** With the auto-SAC 150k
  checkpoint, reducing 0.25→0.22 removed the zero-margin C-04/C-05 stop and completed all
  4400 steps. The auto-175k checkpoint still stopped at either cap on the known D-43 confident
  heading over-read. The probe therefore separates **cap equals C-04 ceiling** from the
  cap-independent CV residual; lowering speed alone is not a D-43 mitigation.
- **A 2-D policy can nevertheless be nominally compatible with enforcement.** SAC-entfix
  produced two full-horizon SC-NOM-01 enforcement evals under the 0.25 contract: seed-2024
  75k (4.32 laps, 17.1 mm, 0 emergencies, 17.1% C-06 only) and seed-42 50k
  (4.97 laps, 18.2 mm, 0 emergencies, 46.4% C-06 only). The former self-limited its raw
  command to ≈0.244 m/s.

The amendment narrows, rather than removes, the D-59 prerequisite: preregister a non-zero
speed margin or recalibrate the `[provisional]` envelope, fix the exact config provenance, and
address/characterise D-43 before any 2-D campaign. No 2-D campaign or SC-PERT-03 cell has run;
these nominal posterior evals do not enter the GE4 verdict chain.

**Qualification implementation (20.07.2026).** The non-zero-margin alternative is now
preregistered, without rewriting the evidence configs: the new, **untrained**
`train_sac_camera_2d_tuned_entfix_margin022.yaml` fixes the action cap at 0.22 m/s, asserts a
minimum 0.03 m/s gap to C-04's 0.25 m/s curve ceiling, requires a fresh **bounded 75k** parent,
and fingerprints the map/horizons into its SB3 checkpoints. Its 150k replay buffer covers the
75k parent plus the fixed 50k stall continuation (125k total) without eviction. Evaluation rejects a missing/mismatched fingerprint, so a
historical 0.25 checkpoint cannot be relabelled as margin-qualified. The contract also declares
a D-43 preflight mandatory.

`tools/d43_preflight.py` operationalises that second prerequisite against the logged Gazebo
oracle. Its reference report over four enforcement traces classifies both entfix full-horizon
checkpoints as individual `PASS`, and both auto-175k variants (0.25 and the 0.22 sensitivity
probe) as `BLOCKED` on centred CV/heading conflicts; the aggregate is therefore intentionally
`BLOCKED`. The 0.40 rad disagreement gate is anchored just above the final clean GE2 maximum
0.38734 and below C-02's 0.4363 rad hard limit; direct envelope crossings, false rules and
emergencies remain zero-tolerance checks. Thus D-43 is **characterised and fail-closed, not
claimed fixed**. A full campaign requires a new margin022-trained checkpoint and a `PASS`
input bound to that exact checkpoint **and train-config hash**. `run_campaign.py` now checks
that provenance before orphan reaping/Gazebo startup and records the matched report/input in
`campaign_report.json`; unrelated `PASS` inputs cannot authorise another policy. Cites the derived reports under
`experiments/sim/eval_gz2d/`.

**D-43 heading-interface follow-up (21.07.2026).** The original near-secant
readout failed the controlled-heading baseline (3/5 held-out real faults; safe/fault
overlap), so neither C-02 nor its threshold was relaxed. An opt-in estimator
candidate instead fits the two selected lane boundaries jointly with separate
intercepts and a shared quadratic tangent/curvature, then applies a global
Gazebo heading gain of 1.60. A repeated 28-cell campaign injected six
positive/negative heading failures per split *during motion* (minimum 0.220 m/s)
and continued through the controlled stop. Held-out result: 6/6 detected, no
false C-02/C-05 over 392 centred-safe cycles, no M-S2/road-edge event, 0.10 s
maximum detection delay and 0.10 s stopping upper bound. Evidence and hashes are
in `d43_c02_calibration_20260721T082128Z`; the canonical 25-degree limit is unchanged.

Only the fresh, still-untrained margin022 contract opts into this candidate.
Frozen defaults keep every GE4/G4 run bit-identical, and the result is scoped to
the hashed Gazebo Lane Cam + `complex_b` envelope (through the tested driven-lane
anchor `|kappa| = 1.031 1/m`, exact per-cycle local GT maximum 0.978 1/m),
not Isaac or arbitrary tighter roads. D-59's
checkpoint-bound preflight remains mandatory after training: this closes the
measurement-interface blocker, not the absent checkpoint/policy evidence.
Cites D-49, D-50, D-52, D-54, D-55, D-56, D-57, D-58; docs/11 §9; docs/13.

### D-60 — SB3 algorithm switch in the shared trainer: `algorithm: ppo|sac` config key (not a separate SAC entry point)

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/cobraflex_rl/train_ppo.py` (+ `callbacks.py`, `training_metrics.py`, `eval_policy.py`, `launch/train_lane.launch.py`); `train_sac_camera.yaml`; 25k pilot variants/evidence under `experiments/sim/training/pilot25k_ppo_vs_sac_2024/` (temporary pilot YAMLs not retained; follow-up below); docs/11 §4.2 |
| Status | ACCEPTED — pytest 517 green; offline + live-Gazebo SAC smokes; 25k verification pilot pair completed 15.07.2026 (`experiments/sim/training/pilot25k_ppo_vs_sac_2024/`) |
| Date | posterior track (15.07.2026) |

**Context.** The E-track training loop was PPO-only (`train_ppo.py` hard-constructed SB3 `PPO`).
An off-policy, sample-efficient counterpart (SAC) is wanted for an algorithm comparison on the
frozen 1-D camera architecture. Two candidate shapes: (a) a separate `train_sac` entry point /
command, or (b) a config key inside the existing trainer.

**Decision.** **(b) — a single `algorithm: ppo|sac` key in the training config** (default
`ppo`), because the comparison is only meaningful if the two arms share everything but the
update rule: env, wrappers (`Monitor`/`VecFrameStack`/`VecNormalize`), reward, cage wiring,
seed handling, LR (+ `lr_schedule: linear`), device, evidence pipeline. A second entry point
would have to duplicate that stack and let it drift. SAC's off-policy knobs live in an optional
`sac:` block (`buffer_size`, `learning_starts`, `tau`, `train_freq`, `gradient_steps`,
`ent_coef: auto`, `target_update_interval`) with SB3-standard defaults except `buffer_size`,
capped at 100k — on the 84×84×4 uint8 camera obs a transition holds ~56 KB, so SB3's 1M
default would demand ~56 GB RAM; the key must stay explicit in camera configs. PPO-only keys
(`n_steps`, `clip_range`, `target_kl`, `clip_range_vf`, …) are ignored under SAC and kept in
the SAC configs so a diff against the PPO twin shows only the switch.

Implementation notes that carry design weight: (1) **SB3 wrapper-order incompatibility found
and fixed** — with SAC + image obs + `VecNormalize`, SB3 adds `VecTransposeImage` *outside*
`VecNormalize` while the off-policy replay buffer stores VecNormalize's *original*
(channels-last) obs and crashes; the trainer applies the transpose *inside* the normalizer on
the SAC+camera path only. The PPO wrapper stack is byte-identical to the frozen runs.
(2) `learning_curve.csv` keeps the exact PPO column schema under SAC (`value_loss` ←
`train/critic_loss`, `entropy` ← `train/ent_coef`, PPO-only columns NaN; rows throttled to one
per 1024-step window since SAC ends a "rollout" every `train_freq` steps) — every downstream
curve reader stays algorithm-agnostic. (3) `eval_policy` resolves the SB3 class from the
config's `algorithm` key (or `--algorithm`); `metadata.json` records `algorithm` +
per-algorithm hyperparameters; the checkpoint registry id becomes `cobraflex_<algo>_lane`.

**Verification (25k pilot pair, complex_b, seed 2024, enforcement, DR on, 1-D).** Both learn
healthily from pixels; SAC overtakes PPO from ~15k and ends `ep_rew_mean` **161.7 vs 131.7**
(+23%), `ep_len_mean` 186 vs 162, slightly lower cage-intervention rate (0.85 vs 0.91,
C-06-dominated as usual early), ~0 emergencies both; wall-clock identical (~7 steps/s,
render-bound — the GPU absorbs SAC's per-step gradient update). 25k is far below the 1-D
convergence regime (PPO ~823 @ ~297k): this is an implementation sanity check + early signal,
**not** an algorithm verdict.

**Follow-up evidence (17–20.07.2026).** The pilots were elevated to long, bounded Gazebo runs
in both action spaces. Their `1M` names record the planned budget; each was deliberately stopped
once the regime was characterised, so none is a completed-million-step claim.

- With `ent_coef: auto`, 1-D SAC peaked at 720 @ 89k and 2-D tuned SAC at 527 @ 154k, then
  suffered an abrupt cliff or collapse–recover cycles as the learned temperature approached
  zero. Fixing `ent_coef: 0.005` preserved the peak zone (1-D 722.5 @ 83k; 2-D 558.7 @ 78k)
  and removed the abrupt collapse. The 2-D entfix checkpoints produced the two full-horizon
  enforcement evals recorded in the D-59 amendment.
- A slower post-peak decay survived entfix. The single-variable 1-D probe
  `buffer_size: 100000→200000` held the 690–745 reward band through 180k, whereas the 100k
  twin had fallen ~35% after the buffer filled. The evidence therefore separates two
  mechanisms over the observed 1-D horizon: **abrupt collapse = temperature→0; the slow
  decay is consistent with replay eviction of the founding data**. The replay conclusion is
  bounded to seed 2024 through 180k; transfer to 2-D remains a hypothesis, not a result.

**Consequence update.** The algorithm study remains posterior and does not promote SAC into the
G4-closed verdict. If a further 2-D retrain is justified, the predeclared variant is entfix plus
a replay buffer at least as long as its bounded horizon, followed by seed replication and
behavioural checkpoint selection. Before that run, archive the exact config beside its evidence
and link each eval metadata record to the training config/checkpoint hashes; the temporary 25k
pilot configs were not retained as repository files, so hashes and prose alone are not an
acceptable provenance pattern for the next experiment.

**Consequences.** Purely **additive**: `algorithm` defaults to `ppo`, old configs load
unchanged, and the frozen PPO artefacts (GE4-V2, E-main, multiseed) are untouched — no re-runs.
A SAC policy is a **new posterior baseline** evaluated through the same harness; it does not
enter the G4-closed verdict chain unless a future decision promotes an algorithm-comparison
study. `train_lane.launch.py` now exposes `train_config:=`/`run_id:=`/`model_path:=` (needed to
select the algorithm at launch; bare launch behaviour unchanged).
Cites D-36 (seed), D-41/D-43 (architecture unchanged), D-49 (1-D contract); docs/11 §4.2;
CHANGELOG 15.07.2026.

---

### D-61 — Realised middleware baseline: ROS2 Jazzy + Gazebo Sim Harmonic supersedes the preliminary Humble distribution choice

| Field | Value |
| --- | --- |
| Section | Ch.6 §6.2.1; `README.md`; `AGENTS.md`; `docs/15_implementation_inventory.md` |
| Status | CONFIRMED — reconciles the decision log with the implemented and evidence-bearing host stack |
| Date | implementation baseline documented 28.05.2026; decision-log reconciliation 20.07.2026 |

**Context.** D-13 selected ROS2 Humble during Phase 0, before the repository's
simulator stack was integrated. The realised system, build commands and all
Gazebo evidence use **Ubuntu 24.04 LTS + ROS2 Jazzy + Gazebo Sim Harmonic** via
`ros_gz_sim` / `ros_gz_bridge`; Ch.6 §6.2.1 already records that implementation
and explicitly identifies the earlier Humble + Gazebo Classic wording as
inconsistent.

**Decision.** Keep ROS2 as the middleware architecture, but supersede D-13's
distribution-specific choice with **ROS2 Jazzy** and its supported **Gazebo Sim
Harmonic** pairing. This is a documentation reconciliation of the stack actually
used, not a runtime migration performed after the campaigns.

**Rationale.** Jazzy is the distribution installed on the Ubuntu 24.04 evidence
host and matches the repository's `ros_gz_*` integration. Retaining Humble as a
current confirmed decision would contradict the executable setup, manuscript and
reproducibility instructions.

**Consequences.** No experimental artifact, checkpoint, scenario, metric or
verdict changes. Commands and future reproductions use `/opt/ros/jazzy`; the
architectural reasoning in D-13 (ROS2 pub/sub, bags and inspection tooling)
remains valid. Historical Phase-0 provenance is preserved by marking D-13
superseded rather than rewriting its original rationale.

---

### D-62 — T3 temporal heading-consistency gate: the structural fix for the H-12 curve over-read (opt-in, posterior margin022)

| Field | Value |
| --- | --- |
| Section | `docs/12_cv_lane_keeper.md` §4.10; Ch.7 §7.5.5; `cv_lane_estimator.py` |
| Status | CONFIRMED — nominal D-43 preflight flips BLOCKED → PASS on the margin022 closed loop (24.07.2026) |
| Date | 24.07.2026 |

**Context.** The D-43/C-02 calibration (D-43 follow-up, 21.07.2026) PASSed on the
bounded calibration matrix with `joint_pair_quadratic` + gain `1.60`, but the
*checkpoint-bound nominal* D-43 preflight — the gate the margin022 contract
requires before a 2-D campaign — **BLOCKED** on the margin022 closed-loop trace
(`experiments/sim/eval_gz2d/d43_preflight_margin022_2024_75k.json`): 13 centred
false triggers, all C-02, at two tight `complex_b` apices (s ≈ 8.9, 16.1), one
escalating to a C-05 emergency (SR-010 Part-1 joint-envelope assertion). Root
cause is the **H-12 single-frame overlap**: at those apices a *centred, well-
aligned* vehicle produces a raw CV heading (up to ≈ 0.44 rad after gain) that
*exceeds* a genuine mid-curve heading fault's reading. No scalar gain separates
them, and single-frame curvature subtraction was already rejected (§4.8) because
the per-frame `c2` is noise-corrupted and masks real faults. Proven
non-separable on the data: centred-curve raw heading 0.2743 > real-fault raw
0.2394.

**Decision.** Add an **opt-in temporal gate** to `CvLaneEstimator`
(`heading_temporal_window > 0`) that caps the reported `|epsi|` to
`heading_temporal_cap_rad` (0.32, below C-02's `theta_activate` = 0.4014)
**only while the estimator's own `ey` confirms lane-following** across the
window — centred (`|ey| ≤ 0.08`), drift-free (window span ≤ 0.03 m) — **and real
curvature is present** (median `|curvature| ≥ 0.30`). Default `window = 0`
disables it, so every frozen GE4/G4 config is bit-identical; only the posterior
margin022 cage block opts in (window 4). The estimator gains a per-episode
`reset()`, called from `CagePerceptionSupervisor.reset()`. Eval-time cage
readout only — the policy observes the CNN camera, never `cv_epsi`, so this is
not a training/observation change and needs **no retrain**; the campaign-contract
fingerprint (action + sac + contract block, not `cage`) is unchanged, so the
existing checkpoint still validates.

**Rationale — why temporal separates what single-frame cannot.** A genuine
heading error *moves the vehicle*: `ey` drifts > the bound within one control
cycle (measured: the held-out D-43/C-02 faults jump `cv_ey` > 40 mm in one
frame at onset). The curvature-induced geometric over-read leaves a *centred,
non-drifting* vehicle. Gating the cap on confirmed lane-following therefore
**cannot mask a fault** — a fault breaks the gate the instant it exists — while
it removes the false triggers. This is the temporal escape flagged as the only
structural fix in the D-48 note (§4.4). No detection delay is added: the cap is
instantaneous and a fault bypasses it (the calibration budget is ≤ 0.2 s = 2
cycles; measured max delay stays 0.1 s).

**Evidence.** Offline over the labelled held-out (seed 42) D-43/C-02 cells and
the margin022 nominal trace, then confirmed in a fresh Gazebo closed-loop
re-eval with T3 on: **all 7 preflight checks PASS** (0/0 everywhere;
`d43_preflight_margin022_2024_75k_t3.json`), max centred `|epsi|` error 0.361 rad
(< 0.40), **0 C-02, 0 C-05, 0 emergencies** in the whole 4400-step trace, 52
apex frames capped at exactly ±0.320 with the vehicle at `|ey|` ≈ 5 mm; held-out
faults still **6/6 detected, ≤ 1-cycle delay, 0 false triggers**. The re-eval is
cleaner than the blocked original (3.99 vs 2.44 laps; the cage no longer
false-brakes at apices), `mean |ey|` 16.9 mm, `max |ey|` 67 mm. Unit tests in
`policy/tests/test_cv_lane_estimator.py` cover the gate, the no-mask guarantee,
reset, and default-off bit-identity (589/589 suite green).

**Consequences.** The margin022 nominal D-43 preflight is satisfied; the fresh-
parent → nominal-PASS → fine-tune → campaign path is unblocked. Scope is the
hash-bound Gazebo Lane-Cam / `complex_b` envelope (same as §4.8/§4.9); no Isaac
parameter is reused. The gate is a conservative *availability* trade at worst
(a confirmed-tracking vehicle's heading is never allowed to trip C-02); C-01
(lateral) and C-03 (TTLC) keep full sensitivity, and the SR-014 plausibility
temporal check remains the backstop for the wrong-side lock. Cites D-43 (the CV
interface), D-48 (the flagged temporal fix), §4.8/§4.9 (rejected single-frame
routes).

---

### D-63 — SC-PERT-03 posterior 2-D negative test: released arm PASS, stall adversary not induced at the preregistered λ (not retuned)

| Field | Value |
| --- | --- |
| Section | `experiments/sim/campaign_sac_pert03/SC_PERT_03_ANALYSIS.md`; Ch.8 §8.9.6 |
| Status | CONFIRMED — 80-run campaign executed cleanly (0 errors); recorded as a characterised result |
| Date | 24.07.2026 |

**Context.** SC-PERT-03 is the SR-009 stall/liveness negative test for the 2-D
(steer+throttle) action. It has a *control* arm (`released` = the deployed
margin022 policy: must make progress, M-P2=1, and never stall, M-P6≈0) and an
*adversarial* arm (`stall_variant` = a 50k fine-tune with a throttle penalty
`r' = r − λ_stall·|throttle|`, which must reach M-P6 > 50 % so the cage's stall
handling is actually exercised). The protocol fixes λ_stall = 4.0 **a priori**
with `adaptive_tuning: false`, precisely so the adversary cannot be fished for a
convenient outcome. Executed on the margin022 parent (4f3b56e2) + its T3-gated
D-43 preflight authorisation (D-62); 80 runs (20 reps × 2 arms × 2 modes).

**Decision / finding.** Report the campaign as-is: **released arm PASS**
(enforcement 18/20 = 0.90, monitoring 20/20 = 1.00 — deployed-policy liveness
confirmed), **stall_variant arm inconclusive** because the preregistered λ = 4.0
did **not** manufacture a deterministic staller (M-P6 max 0.79 %, mean 0.03 %
across 40 runs; the fine-tuned checkpoint 56d235da, genuinely distinct from the
parent, still drives ~0.34 laps at |ey|≈0.02 m). **λ is NOT retuned** to force a
staller — that is exactly the post-hoc fishing the fixed-a-priori protocol
forbids.

**Rationale — why λ = 4.0 did not induce a stall.** The parent config uses
`normalize_reward: true` (VecNormalize) + `clip_reward: 10.0`. The fixed additive
penalty is applied to the *raw* reward, then divided by the running return std
(~10²–10³) and clipped, diluting λ to a small fraction of the normalized
advantage. Training rollouts still went short/negative (`ep_rew_mean → −100`,
`ep_len ≈ 60`: exploration under the penalty ran the *stochastic* policy
off-road), but the *deterministic* mean-action policy that is evaluated kept the
base policy's competent driving. A genuine deterministic staller would need a
larger λ or λ on the unnormalized reward — a protocol change, not a retune.

**Relation to SR-009.** For the frozen 1-D steering-only action the stall arm is
N/A-by-construction (M-P6 ≡ 0, no throttle authority; D-49). The 2-D action
(D-50) makes stalling commandable in principle, so SC-PERT-03 is well-posed, but
the adversary could not be produced at the preregistered λ, so the
stall-*detection* half is untested-in-practice. The released arm's M-P6 ≈ 0
directly confirms the deployed policy's liveness, which is what SR-009 asserts of
the actual system.

**Consequences.** Does not reopen G4 (posterior E5). No SR verdict, scenario or
metric changes; `check_traceability.py` unaffected. A residual T3 finding is
recorded (2/20 released-enforcement false emergencies from a rare apex-exit CV-ey
transient that breaks T3's drift gate by design — the conservative, no-mask side
of D-62, not loosened). Any future attempt to exercise the stall-detection arm
must **re-preregister** a new protocol with an explicit, justified λ (or an
unnormalized-reward penalty), not silently retune this one. Cites D-49 (1-D N/A),
D-50 (2-D well-posed), D-62 (the authorising T3 preflight).

---

### D-64 — SC-PERT-03 metrology closed by a scripted stall stimulus; the trained policy provably resists stalling (v1 was a mis-designed adversary, not a cage result)

| Field | Value |
| --- | --- |
| Section | `experiments/sim/runs/sc_pert_03_scripted_stall_2024/`; Ch.8 §8.9.7; `eval_policy.py` (`--scripted-stall`) |
| Status | CONFIRMED — stall detector M-P6 fires on a ground-truth stall (M-P6 = 100.0); the fine-tuned adversary would not stall |
| Date | 25.07.2026 |

**Context.** SC-PERT-03's stall_variant arm was recorded inconclusive at D-63 (the
preregistered λ=4.0 did not induce a stall). Rather than retune λ (forbidden), the
question was reframed to *"was the adversary construction correct?"* — and it was
not. SR-009 states its liveness mitigation is a **training-level reward shaping**
(the `stall_penalty` term), **not a cage rule** (*"a cage rule that forced
throttle > 0 would be orthogonal to the cage's philosophy … out of scope; the cage
instead provides observation of stall through M-P6"*). So SC-PERT-03 is a
**metrology test**: does M-P6 *detect* an induced stall? The v1 adversary reward
was internally contradictory — it inherited `stall_penalty = 0.5` (the SR-009
mitigation, which *opposes* stalling) alongside `lambda_stall = 4.0`, and the
a-priori λ derivation ignored `clip_reward = 10.0` (caps the penalty) and
`normalize_reward` (dilutes it). A construction-validity defect in the test harness,
independent of the cage.

**Decision.** (1) A design-corrected **pure-stall-objective pilot**
(`forward_progress = 0`, `stall_penalty = 0`, λ = 4.0 → throttle→0 is the provable
optimum) was run as a one-way construct-validity gate (15k fine-tune from the
margin022 parent). It did **not** produce a deterministic staller: `ep_rew_mean`
fell to −300 and `ep_len` stayed ≈ 241 (a stalled car would truncate at 2048), i.e.
the policy kept driving despite the throttle penalty. Root cause: resuming a
competent driver with a driving-filled SAC replay buffer biases against discovering
the stopping optimum. **This is recorded as a finding, not iterated** — the
difficulty of forcing a stall is positive evidence the deployed policy robustly
resists the park-hack it was hardened against (D-56). (2) The stall **detector**
(M-P6) was then validated *directly* with a **scripted ground-truth stall** — a new
opt-in `eval_policy --scripted-stall` mode commands a full stop
(`[steer 0, throttle −1]` → speed 0) every step, through the real Gazebo + cage +
metrics pipeline. Result (`sc_pert_03_scripted_stall_2024`, complex_b, 400 steps,
enforcement): **mean/max speed 0.0000, M-P6 = 100.0, 0 emergencies** → the detector
fires on a genuine stall.

**Rationale — why this is legitimate, not gaming.** The cage (object under test) is
untouched. The scripted stall is a *metrology stimulus* (a known-stall input to test
the detector), not a fished-for adversary; it is the cleanest possible test of "does
M-P6 flag a stall?" — a ground-truth stall with no training stochasticity. The v1
inconclusive and the pilot's negative result are both preserved. `--scripted-stall`
is default-off, so every verdict run is bit-identical.

**Consequences — the SR-009 story is now complete and three-part.** (i) The deployed
policy drives and never stalls (released arm PASS, M-P6 = 0, D-63) → the training
mitigation works. (ii) The policy *resists* being forced to stall (the pilot) →
extra robustness evidence. (iii) M-P6 correctly *detects* a stall when one exists
(scripted stimulus, M-P6 = 100) → the verification machinery is sound. Does not
reopen G4 (posterior E5). No SR verdict, scenario or metric changes;
`check_traceability.py` unaffected. Supersedes the interim `V2_DESIGN_GOAL.md`
proposal (its root-cause analysis is captured here). Cites D-56 (the anti-park
mitigation), D-63 (the v1 inconclusive), SR-009 (metrology framing).

---

### D-65 — First full 2-D verdict campaign (margin022): NOT SATISFIED literal, but in-ODD safety holds and the cage's value is larger than in 1-D

| Field | Value |
| --- | --- |
| Section | `experiments/sim/campaign_2d_margin022/CAMPAIGN_2D_ANALYSIS.md`; Ch.8 §8.9.8 |
| Status | CONFIRMED — 1970 runs, 0 errors; literal NOT SATISFIED reconciled (no in-ODD breach) |
| Date | 26.07.2026 |

**Context.** The margin022 2-D (steer+throttle) qualification (nominal D-43 PASS via T3,
D-62; SC-PERT-03 closed, D-64) unblocked the **first full verdict campaign on the 2-D
action** — 28 complex_b scenarios × {enforcement, monitoring}, seed 2024, 1970 runs.
Posterior E5; does not reopen the frozen 1-D E verdict (GE4-V2, D-49).

**Decision.** Record the campaign as **NOT SATISFIED (literal)** with a full reconciliation
(mirroring the GE4-V2 precedent, D-47): the global fails because 8/14 SRs fail, but the 8
failures trace to only four scenarios and **none is an in-ODD safety breach**.

**Evidence.**
- **Core safety holds:** enforcement road-edge contacts — **in-ODD = 0**, out-of-ODD = 50
  (frontier/edge stress). The cage produces zero in-ODD road-edge contacts, as in 1-D.
- **Cage value, measured and larger than 1-D:** the bare 2-D policy commits **98 in-ODD
  road-edge contacts**; the cage **removes all of them** (0 in enforcement) via **433
  controlled emergency stops**. The 2-D policy is materially weaker than the frozen 1-D
  policy, so the cage genuinely does more work — the central thesis claim demonstrated where
  the policy needs it.
- **Per-SR:** SR-002/005/007/008/009 ← **SC-NOM-03** (5/25 cage emergencies on the 300 s
  endurance run; 0 road-edge, max \|ey\| 88 mm — safe stops failing the completed/no-emergency
  clauses, an *availability* cost). SR-012/014 ← **SC-PERT-05** (severe low-light: 30/40 cage
  emergencies, 0 road-edge — the cage correctly stopping under degraded perception, SR-013/014
  Trigger-8, the cage *working*). SR-010 ← **SC-EDGE-05** (genuine CL-B co-activation, same as
  1-D). SR-009 ← **SC-PERT-03** (the stall construct, documented D-64).

**Consequences.** The 2-D result is **safety preserved, availability reduced**: the cage keeps
every in-ODD case safe while the weaker, throttle-commanding 2-D policy trips it into more safe
stops than the 1-D policy did. No SR verdict/scenario/metric in the manuscript changes;
`check_traceability.py` unaffected. The literal NOT SATISFIED is not a safety failure — it is
availability + one CL-B (SR-010) + the documented stall construct (SR-009). Cites D-47 (literal
+ reconciliation precedent), D-49 (frozen 1-D verdict), D-62/D-64 (the qualification), SR-010
(the CL-B co-activation), M-S5 (road-edge metric).

---

### D-66 — A competent 2-D camera policy: PPO (not SAC) at cap 0.22 — and why the reward-peak checkpoint is not the best one

| Field | Value |
| --- | --- |
| Section | `experiments/sim/training/ppo_gz2d_cap022_1M_2024/`; Ch.7 §7.5.5; `manuscript/figures/auto/fig_ppo2d_training_curve.png` |
| Status | CONFIRMED — best deterministic checkpoint selected (550k); its D-43 preflight PASS; **verdict campaign closed 31.07.2026** (1890 runs, 0 errors; `CAMPAIGN_2D_PPO550K_ANALYSIS.md`) |
| Date | 27.07.2026 |

**Context.** The margin022 2-D verdict (D-65) ran on a materially weak policy: SAC, 75k, and — worse
— the *decayed* final checkpoint (peak was ~54k, ep_rew 199; the campaign used the 75k, ep_rew 131).
The 2-D availability shortfall was suspected to be under-training, not a limit of the 2-D action.

**Decision.** Train a proper 2-D policy and select its best checkpoint by driving quality, not
training reward. (1) **Algorithm: PPO, not SAC.** A fresh PPO 2-D 1M (cap 0.22, checkpoints/25k)
reached **ep_rew_mean 1755 @ 472k** and a *stable high plateau*; SAC 2-D never exceeded ~200 (it
crashes at ~0.28 laps — off-policy camera SAC does not master the track). (2) **Cap 0.22, not 0.5.**
A *single-variable* config diff (only `action.max_speed_mps` changed) shows PPO at 0.5 peaks at 654
(drives >1 lap but *sloppily* — high lateral/heading penalty on the tight complex_b curves) vs 1421+
at 0.22 (traces the curves cleanly); per-step reward 1.165 (2-D @0.22) vs 1.040 (1-D) — the ~2× total
is mostly the 2048-vs-1024 episode-step cap + longer survival, not "2× better driving." (3) **Best
checkpoint by reward AND cage %.** During training the cage is *latent for safety* throughout
(C-01/02/03/05 = 0, 0 emergencies — the policy respects the constraints); only C-06 (rate limiter)
fires. Deterministic nominal evals of three candidates were decisive: the **reward-peak 475k is NOT
the best** (14 safety interventions, max\|ey\| 49 mm), while **550k wins** (5.32 laps, mean \|ey\|
8.6 mm, max 27 mm, **0 emergencies, 0 safety interventions**, lowest C-06). Selecting on reward alone
would have picked the worst of the three.

**Evidence.** `fig_ppo2d_training_curve.png` (PPO 2-D vs 1-D E-main vs SAC 2-D). Candidate evals
`rl_ppo2d_cap022_{400k,475k,550k}_nom_4k4`. 550k D-43 preflight (cage = joint_pair_quadratic + gain
1.60 + T3, identical to margin022 for comparability) **PASS** (7/7,
`d43_preflight_ppo2d_cap022_550k.json`). Verdict campaign on 550k launched
(`experiments/sim/campaign_2d_ppo550k/`, 27 complex_b scenarios × {enf, mon} = 1890 runs; SC-PERT-03
excluded — the stall meta-test is policy-independent and closed at D-64; SR-009 stays D-29-feasible).

**Consequences.** This is the good 2-D policy the campaign should contrast against the weak margin022
(D-65): same cage, same scenarios, better driver → tests whether the D-65 availability failures were
policy-quality (they should clear) or structural (perception/co-activation, should persist). Also of
note: the 1-D E-main *collapses* after its peak (exploration collapse, 823 → 114) while the 2-D @0.22
stays stable — plausibly because the slow cap makes the driving objective a wide, forgiving basin.
Posterior E5; frozen 1-D verdict untouched.

**Outcome (31.07.2026) — the hypothesis held in both directions.** 1890 runs, 0 errors. Global
`NOT SATISFIED` **literal**, blocked by SR-002/003 **only**, and only through SC-EDGE-01's inherited
2.0 s recovery clause (0 emergencies there, max M-S1 0.043 m ≪ 0.16, max heading 14.2° ≤ 25°) — the
D-47 reconciliation applies verbatim, and SR-011 with it (σ_θ 3.77° < 5°). 8/10 SR-CL-A Satisfied;
SR-009 `insufficient_evidence` by protocol (SC-PERT-03 excluded). **In-ODD road-edge contacts in
enforcement: 0** (the bare policy commits 60, all removed, with 406 controlled stops vs margin022's
433). Availability failures **cleared** — SC-NOM-03 20/25 → 25/25 with zero emergencies,
SC-PERT-05 30/40 → 40/40, all 12 SC-PERT enforcement verdicts True — while the **structural**
residuals persisted: SC-EDGE-01's clause and SC-EDGE-05 co-activation (SR-010, attenuated 30/85 →
16/85 in-ODD M-S1 breaches but unchanged in kind). Out-of-ODD contacts 56 vs GE4-V2's 117. Full
analysis: `experiments/sim/campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md`; write-up Ch.8 §8.9.9.

Cites D-60 (algorithm switch), D-59 (the 0.22 cap / speed-envelope), D-62 (T3 preflight), D-65
(the weak-policy campaign this contrasts), D-47 (the reconciliation applied).

---

### D-67 — Research trunk of record moves to the 2-D PPO camera policy; everything before it is reclassified as development history

| Field | Value |
| --- | --- |
| Section | Repo-wide scoping decision. Affects `README.md`, `CLAUDE.md`, `docs/16` §8; **deliberately NOT applied to `manuscript/`** |
| Status | ACCEPTED as a scoping decision. The condition it was written under **has since been met**: the `campaign_2d_ppo550k` verdict closed 31.07.2026 and is not materially worse than GE4-V2 (see the risk note at the end of this entry) |
| Date | 30.07.2026 |

**Context.** The repository accumulated four successive research arms, each of which was at some point
"the" result: the **F-track** state-vector policy on the oval (ground truth observations, G3/F4,
verdict `SATISFIED`), the **1-D camera E-main** (GE4-V2 on the complex_b 297k peak, 1970 runs, the
`verdict of record` that closed **G4** on 02.07.2026), the posterior **SAC / algorithm probes** and
the weak **2-D margin022** campaign (D-65), and finally the **competent 2-D PPO** policy at cap 0.22,
checkpoint 550k (D-66), whose verdict campaign is what closes this arm. Every spec document
(`docs/02`, `03`, `04`, `05`, `06`, `08`) still names GE4-V2 as the *verdict of record*, and the
manuscript's Chapter 8 is still organised with the F-track as §8.1–8.8 and the whole camera track
demoted to §8.9 — i.e. the document structure is the **inverse** of the current research priority.
Presenting all four arms as parallel results would produce a defense narrative with four competing
headline numbers and a thesis long past the point of usefulness.

**Decision.** The **2-D PPO camera policy (D-66, checkpoint 550k) is the research trunk of record**:
the artefact the defense presents, and the one against which the developed framework — cage, D-43
perception supervisor, scenario library, metrics catalogue, verdict spine — is evaluated and verified.
Everything preceding it is reclassified from *parallel result* to **development history**: the path
that had to be walked to reach the 2-D policy. Concretely:

| Arm | Old role | New role |
| --- | --- | --- |
| F-track (state-vector, oval) | Frozen ground-truth baseline / control arm | **Method-validation stage.** Proves the framework works when perception is perfect — the reference that isolates what camera perception costs. Not a headline result |
| 1-D camera E-main (GE4-V2, G4) | **Verdict of record** | **Predecessor + verification data.** Its D-47 verdict reconciliation, its latent→active cage flip and its SR-010 co-activation finding remain load-bearing *method* evidence |
| SAC / algorithm + cap probes (D-59/D-60), margin022 (D-65) | Posterior E5 results | **Findings: problems encountered and how they were overcome.** Entropy collapse, replay eviction, the speed-envelope kill, the weak/decayed-checkpoint trap |
| **2-D PPO 550k (D-66)** | Posterior E5 contrast | **THE result.** Evaluation + verification of the framework |

**Two things this decision does NOT do.**

1. **It does not reopen G4, and it does not retroactively relabel the GE4-V2 verdict.** G4 closed on
   evidence that was valid when it closed; the gate record stands. "Verdict of record" as used in
   `docs/02–08` remains historically correct **for that gate**. What changes is which arm the *thesis*
   presents as its result. Whether those spec documents get re-pointed at the 2-D campaign is a
   separate, deliberate edit to be made **after** the 550k verdict exists — not now, and not silently.
2. **It is not applied to `manuscript/`.** By explicit author instruction (30.07.2026), the
   reclassification is recorded in the repository only. The manuscripts feeding the thesis and the
   paper must not carry the reasoning, the four-arm comparison, or the superseded results as prose —
   that is precisely the text bloat this decision exists to prevent. In the thesis, the earlier arms
   appear (if at all) as *findings and fixes* in the development narrative and as verification
   cross-checks, never as a second results chapter.

**Consequence — the largest pending action, deliberately deferred.** Chapter 8's structure
(§8.1–8.8 = F-track results, §8.9 = camera track) contradicts this decision, and the 2-D PPO campaign
has no chapter section at all. Restructuring it is a substantial authoring task that only makes sense
once the 550k verdict is in hand; it is explicitly *not* attempted here. Same for the `docs/02–08`
"verdict of record" pointers.

**Risk to state plainly.** This decision was recorded while the campaign that justifies it was still
running. If the 550k campaign comes back materially worse than the 1-D E-main — for instance if the
in-ODD safety guarantee does not hold, where GE4-V2's did — the trunk claim has to be revisited rather
than defended. The honest version of the defense narrative depends on the verdict, not on this entry.

**Resolved (31.07.2026).** The campaign closed and the risk did not materialise: in-ODD road-edge
contacts in enforcement are **0**, as in GE4-V2; the literal `NOT SATISFIED` reconciles through the
*same* inherited SC-EDGE-01 clause under the same D-47 precedent; availability is *better* than the
2-D predecessor (all 12 SC-PERT enforcement verdicts True) and the only structural residual, SR-010
co-activation, is attenuated rather than worsened. The trunk claim stands on the verdict, not on this
entry. Two follow-ups this now unblocks, both still deliberate edits rather than automatic ones:
re-pointing the `verdict of record` in `docs/02`–`docs/08`, and restructuring Chapter 8. Evidence:
`experiments/sim/campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md` (D-66).

Cites D-66 (the policy and its checkpoint selection), D-65 (the weak 2-D predecessor), D-49 (the
frozen 1-D action), D-47 (the verdict-reconciliation precedent this arm will need again), D-43
(the perception supervisor being verified), D-29/D-30 (the verdict spine).

---

### D-68 — The heading-recovery metric measured ripple, not recovery: band referenced to the run's own envelope

| Field | Value |
| --- | --- |
| Section | `src/cobraflex_rl/cobraflex_rl/scenario_metrics.py`; SC-EDGE-01 (`scenarios*/edge/sc_edge_01.yaml`); `tools/rescore_recovery_clause.py`; Ch.8 §8.9.9 |
| Status | ACCEPTED — metric corrected, applies to **future** scoring; historical campaign records are not re-scored |
| Date | 31.07.2026 |

**Context.** `time_to_recovery_heading` (SC-EDGE-01's clause operand) returned the first time
`|epsi|` drops below a **fixed** 0.05 rad (2.86°) band *and holds it for 0.5 s*. That band was
calibrated on the F-track PD controller on the oval, where every run recovers in 0.6–0.7 s with a
3× margin, and it was never re-derived when the camera track moved to `complex_b`. The clause is the
sole cause of the literal `NOT SATISFIED` in both camera campaigns (GE4-V2 and the 2-D PPO 550k), so
it is worth knowing whether it measures what it claims.

**The defect, demonstrated on runs with nothing to recover from.** Heading error ripples about zero
with a controller- and track-dependent amplitude (median `|epsi|` 1.2–1.4°, but p90 3.0–4.8°).
Requiring *five consecutive* samples under a fixed 2.86° therefore tests **ripple amplitude**, not
recovery. Applied to **unperturbed** scenarios the clause fails outright: on the oval's SC-NOM-02
(sustained curve, no perturbation) **50/50 F-track runs "never recover"**, median 12.2 s. On
`complex_b` SC-NOM-02 it false-positives on 7/50 (2-D 550k) and 3/50 (1-D E-main). A metric that
reports "never recovered" for a run that was never perturbed is measuring the wrong thing.

**Decision.** The recovery band becomes the run's **own steady-state envelope**:
`band = clamp(p95(|epsi|) over the run's last 50 %, floor = 0.05 rad, cap = 0.0873 rad)`.
The floor is the v1 bar, so v2 can never be *more permissive* on a well-damped run; the cap is
SR-011's `σ_θ_max` = 5°, so a policy cannot buy itself a wider band by oscillating more — past that
bar the run is an SR-011 finding, which is where such behaviour belongs. Physically: a perturbation
is recovered when the heading is back inside the envelope the vehicle occupies in normal operation.
v1 remains selectable (`ripple_reference=False`, or an explicit `threshold_rad`) so the historical
records stay bit-exactly reproducible — verified: **120/120 runs** re-derive their stored value.

**Pre-registration and the anti-gaming guard.** The rule above was written down and applied **once**,
before looking at what it did to any verdict, and it was **not** iterated against the failing runs.
Its acceptance test was fixed in advance: the false-positive rate on unperturbed scenarios must
collapse. It did — oval SC-NOM-02 goes 0/50 → **50/50**.

**Consequence — and this is the point worth stating plainly: no current verdict changes.**
Re-scored under v2 (`tools/rescore_recovery_clause.py`, report in
`experiments/sim/campaign_2d_ppo550k/rescore_recovery_clause_d68.json`):

| campaign | SC-EDGE-01 v1 | SC-EDGE-01 v2 |
| --- | --- | --- |
| F4 (oval, state) | 30/30 PASS | 30/30 PASS |
| GE4-V2 (1-D camera) | 17/30 fail | **28/30 PASS** |
| margin022 (2-D, weak) | 30/30 PASS | 30/30 PASS |
| **2-D PPO 550k** | 8/30 fail | **15/30 fail** |

The correction helps the **frozen historical arm** (GE4-V2) more than the current one, and the 2-D
PPO 550k still fails the clause under the corrected metric. Two things follow. First, the fix cannot
be read as tuning the criterion to pass the arm the thesis presents — it does not. Second, and more
useful: the 550k's SC-EDGE-01 failure is **not a measurement artefact**. Its recovery genuinely
*rings* — the trace shows 13.6° → 1.4° → back out to 5.9° → settling only at ~2.5 s, on a **straight**
(reference curvature 0.00 along the whole stretch), which is the closed-loop signature of the
bang-bang command stream and C-06 slew limiting documented in Hallazgo 14. It remains a
**performance**, not a safety, property: M-P4 max 14.2° ≤ 25°, M-S1 max 0.043 m ≪ 0.16 m, σ_θ 3.77° <
5°. The D-47 reconciliation therefore still carries the verdict, now on firmer ground than "the
clause is inherited".

**What is deliberately NOT done.** GE4-V2 and F4 are **not** re-scored: verdicts stand as scored with
the metric in force when the gate closed (D-30/D-47 precedent), and G4's record is untouched. The
re-score report is an annotation, not a replacement. Whether SC-EDGE-01's 2.0 s **bound** should also
be re-derived for the actuator regime (C-06 caps steering slew at 0.15/cycle, so an out-and-back
correction plus the 0.5 s hold has a floor near 1.2–1.6 s) is a **separate** decision, deliberately
left open here: this entry fixes a measurement defect, not a pass bar.

Cites D-47 (reconciliation precedent), D-30 (aggregation semantics), D-39 (out-of-band scoring of a
metric the per-scenario aggregation mis-attributes), D-66 (the campaign that surfaced it).

---

### D-69 — The simulation programme closes: verdict of record re-pointed to the 2-D PPO 550k campaign, and the last two SR-CL-B TBDs closed (one Satisfied, one reported as `Not satisfied`)

| Field | Value |
| --- | --- |
| Section | `docs/07`; framing notes of `docs/02`–`docs/06`, `docs/08` v0.9.1; `tools/traceability_matrix.csv` |
| Status | ACCEPTED — the D-67 condition is met and the two deferred follow-ups it recorded are taken |
| Date | 31.07.2026 |

**Context.** `campaign_2d_ppo550k` — the last simulation campaign before physical
deployment — finished on 31.07.2026 with 1890 runs and 0 errors. Two edits had been
deliberately deferred, both recorded rather than done silently: **D-67** declared the 2-D
PPO policy the research trunk **conditionally**, because at the time the arm had a nominal
evaluation and a D-43 preflight but *no verdict*, and it stated that if the campaign returned
a worse in-ODD safety picture than GE4-V2's the trunk decision must be **revisited rather
than defended**. Separately, SR-009 and SR-010 had been carried as documented, non-vetoing
**TBD abstentions** since F4 — through G4, which closed without them.

**Decision — three parts.**

**(1) The verdict of record is the 2-D PPO 550k campaign.** `docs/02`–`docs/08` now name it;
**GE4-V2 remains the frozen G4 gate record** and is **not** re-scored, so the gate still
rests on the evidence it actually closed on. The D-67 condition is checked, not assumed: the
in-ODD safety picture is **not worse** — enforcement in-ODD road-edge contacts are **0 on both
arms**, and out-of-ODD the 2-D arm more than halves them (56 vs 117). The literal global verdict
is `NOT SATISFIED` on both arms, blocked by the same two SRs through the same single clause on
the same single scenario, so D-47 transfers verbatim rather than being re-argued.

**(2) SR-009 → Satisfied, scored out-of-band (ratifying D-64).** The 2-D campaign reports
SR-009 `insufficient_evidence` because SC-PERT-03 was excluded from it by protocol; that is a
statement about the campaign's coverage, not about the requirement. The verdict is taken from
the dedicated evidence D-64 assembled — nominal liveness passes on every arm (M-P6 = 0), the
policy **resists** being forced to stall (the pure-stall-objective pilot failed to produce a
staller), and the detector **fires on a ground-truth stall** (scripted stimulus through the
real Gazebo + cage + metrics pipeline, M-P6 = 100.0). Mitigation works, pathology resisted,
metric sound. This is the same out-of-band pattern as SR-006/D-39 and it is used for the same
reason: per-scenario aggregation is the wrong instrument for this requirement.

**(3) SR-010 → `Not satisfied`, and reported as such.** The scenario-side gap that justified
the abstention is gone — the grid-IC injection is wired and SC-EDGE-05 genuinely induces
co-activation — so the requirement was measured, twice, and **fails its own criterion**
(`M-S2 = 0` does not hold): **30/85** in-ODD grid points breach M-S1 on the 1-D arm, **16/85**
on the 2-D arm, concentrated on **C-01 ∧ C-02** (15/20 fail, 11 breaches) and vanishing where
no lateral/heading conflict exists (C-04 ∧ C-06: 0/20 fail). Better training halves it and does
not change it in kind, which is the substantive finding: **arbitration under simultaneous
activation is a design property of the cage, not a policy defect.** It is SR-CL-B and
non-vetoing (D-30), and it is carried as declared future work (**T4**).

**Rationale — why closing a TBD as a failure is the point, not a problem.** A TBD says "we do
not know"; the thesis is only entitled to that while the instrument is genuinely missing. Both
instruments now exist, so continuing to abstain would convert an honest gap into a convenient
one. Recording SR-010 as the single `Not satisfied` verdict in the matrix costs nothing the
work is entitled to keep — it is CL-B, it vetoes no global verdict, and no SR-CL-A safety
predicate is involved — and it buys the register's credibility: the same document that reports
0 in-ODD road-edge contacts also reports the one requirement that is not met.

**What is deliberately NOT done.** (a) **G4 is not reopened.** The gate closed on F4 + GE4-V2,
that evidence is unchanged, and closing a documented non-vetoing abstention with *more*
evidence cannot retroactively weaken a gate that passed without it. (b) **No historical
campaign is re-scored** (D-30/D-47/D-68 precedent). (c) **TBD-Q10 (`ODD-3.A_LAT_MAX`) stays
open**, and no simulation number is invented for it: it is unmeasurable in simulation by
construction (D-33), since in Gazebo it is a consequence of the friction coefficient the world
assumes. (d) **The `verdict_phys` column stays `tbd` throughout** — Phase 5 is scaffolded
end-to-end but has not been run on hardware (`docs/17`). (e) **Chapter 8 is not restructured**
so the camera track leads; that authoring task, the other item D-67 deferred, remains open and
is a manuscript decision rather than an evidence one. (f) **No ODD parameter, SR threshold,
cage rule or `cage.yaml` value changes** on this evidence.

**Verification.** `python tools/check_traceability.py` → All checks PASSED, 0 warnings. The
C-04 claim added to `docs/08` §6.5 is measured, not inferred: C-04 fires **zero** times across
all 1890 runs in both modes (enforcement ledger `C-06 181620, C-03 764, C-02 721, C-05 361,
C-01 159`).

Cites D-67 (the conditional trunk decision and the two deferred follow-ups), D-66 (the policy
and checkpoint), D-64 (SR-009's metrology), D-47 + D-68 (the SR-002/003 reconciliation and the
audited clause metric), D-30 (CL-B non-veto), D-39 (out-of-band precedent), D-33 (Q10's
hardware dependency), D-49 (the frozen 1-D verdict).
