# DECISIONS.md — Project decision log

<!--
Status: D9 (Phase 0 close) + F1 audit additions (D-25..D-33) + F3 (D-34) + F4 (D-35, D-36, D-37, D-38, D-39).
Last update: see Git commit date.
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
| D-01 | No *end-to-end* architecture for the integration of the RL *policy* | §3.5.1 (additional motivation in §3.4) | CONFIRMED |
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
| D-13 | Middleware: ROS2 Humble distribution | §3.6.2 | CONFIRMED |
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

---

## Decisions

### D-01 — No *end-to-end* architecture for the integration of the RL *policy*

| Field | Value |
| --- | --- |
| Section | §3.5.1 (additional motivation in §3.4) |
| Status | CONFIRMED |
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
| Status | CONFIRMED |
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
