# DECISIONS.md — Project decision log

<!--
Status: D9 (Phase 0 close).
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
