# Appendix C — Instrument choices and normative mapping

Complete development of §3.6 and §3.8. Each choice is presented with its justification and with the discarded alternatives and the reason for discarding them, so that the decision is auditable and not merely declared.

# C.1 Instruments


This section documents the instrument choices that articulate the methodological
framework on the case study. The intention is not to enumerate
tools, but to justify each choice against the discarded
alternatives, leaving an auditable record of decisions that would otherwise
remain implicit. Each subsection follows a uniform pattern:
tool chosen, justification, discarded alternatives with the reason
for discarding them.

## C.1 Simulator

**Choice: Gazebo** (Koenig and Howard, 2004), in its modern variant with
native ROS2 integration, operated through a
gymnasium-Gazebo-ROS2 interface that reuses an environment previously built by
the author in earlier research work. The choice is
justified by four reasons that should be stated honestly, given
that it differs from the dominant practice in autonomous driving
research, where CARLA is the reference simulator.

First, *native ROS2 integration*. Gazebo is co-developed with ROS by
Open Robotics and shares primitives (topics, transforms, visualisation
tools) with no need for intermediate bridge layers. The whole
project architecture described in Chapter 5 — perception, policy,
cage, actuation, logger — is ROS2 by design; hosting the simulator
in the same graph removes failure surface and reduces the ambiguity
about where latencies or desynchronisations occur, which has
direct consequences for the fidelity of the integration metrics
(M-I).

Second, *reuse of the author's earlier work*. The author has
a Gazebo environment previously built for a related task, with the
scale vehicle modelled and the controlled track configured.
Reusing this environment, instead of rebuilding it from scratch on another
platform, frees project time to concentrate on the
methodological contribution — the adaptations A1–A5 and their materialisation —
which is the real object of the thesis. This decision is coherent with the
*design science* approach made explicit in §3.2.1: the contribution is not in the
simulator but in the framework, and the instrument choice must minimise
the accidental cost.

Third, *gymnasium-Gazebo-ROS2 interface for training*. The
interface that joins the training loop (Stable-Baselines3 over
gymnasium) with the simulator (Gazebo, through ROS2) is available as
open tooling and allows a clean separation between algorithm, environment
and system. This makes it easier to fulfil adaptation A1 (Training
Specification as meta-design): the hyperparameters, the reward
function and the training ODD are specified in a separate Python
module, without coupling to the underlying simulator.

Fourth, *more modest computation requirements*. Gazebo runs on
less demanding hardware than CARLA, which is relevant for an
individual thesis without access to dedicated computation infrastructure and allows
the iteration cycle to be accelerated during the development of the Training Spec.

This choice carries two trade-offs that should be recognised
openly. On the one hand, the visual fidelity of Gazebo is lower than
the one offered by the Unreal Engine underlying CARLA; for a policy
based on a monocular camera, this can translate into a more pronounced
sim-to-real gap than would be observed with a photorealistic simulator.
Adaptation A5 of the framework — empirical characterisation of the gap — is
designed precisely to make this effect visible and to measure it, not to
hide it (cf. §3.9 and Chapter 9). On the other hand, the specific research
community of autonomous driving mostly uses
CARLA, which limits the immediate availability of reusable scenario
libraries in Gazebo format; this means that the scenario library of the
project has to be built explicitly, which falls within the
scope of Chapter 6.

Alternatives considered and discarded. **CARLA** (Dosovitskiy et al.,
2017) is the strongest candidate and the default choice in
recent autonomous driving research; it offers superior sensor
fidelity and a mature benchmark ecosystem, but it requires a
ROS2 *bridge* with its own complications, and its higher computation cost is an
operational obstacle for an individual thesis. **Highway-Env** and other environments
derived from Gym, without realistic sensors and with an abstract observation
space, are not suitable for camera-based policies. **LGSVL**, a
project discontinued in 2022 with a decaying ecosystem.
**AirSim**, with an aerospace focus, secondary automotive support and
development on hold.

## C.2 Middleware

**Choice: PPO** — *Proximal Policy Optimization* — (Schulman et al.,
2017). PPO is chosen for four reasons that are coherent with the
methodological framework. First, *training stability*: the *clipped
surrogate objective* limits the update divergence without requiring
an explicit KL constraint, which reduces the sensitivity to
hyperparameters and improves reproducibility — an important property for an
individual work with limited compute for exhaustive *sweeps*.
Second, *interpretability of the Training Spec*: being *on-policy*, the
hyperparameters have a relatively direct semantic meaning
(rollout size, epochs per update, clipping ratio, entropy
coefficient), which makes it easier to write the Training Spec of level L4b as
a readable document. Third, *support in open tools*: the
Stable-Baselines3 implementation is mature, widely used, and
admits direct integration with Gazebo through the
gymnasium-Gazebo-ROS2 interface mentioned in §3.6.1. Fourth,
*compatibility with extensions*: if in future iterations the thesis were to
explore *constrained RL* (in the style of the RECPO of Zhao et al., 2024),
PPO admits a natural extension to CMDP.

Alternatives considered and discarded: **SAC** (Haarnoja et al., 2018)
is competitive in sample efficiency and in robustness to hyperparameters,
but its *off-policy* character makes the Training Spec less interpretable
— the notion of "which policy produced which experience" is blurred in the
*replay buffer* — and its stochastic nature with *temperature tuning*
adds complexity to the experiment design; **DDPG / TD3** (deterministic
*off-policy*) are less stable than SAC and have been superseded by it in
almost all benchmarks; **A3C / A2C** are less sample-efficient
and have been virtually abandoned in favour of PPO since 2018.

## C.4 Learning loop and implementation tools

- **Stable-Baselines3** as the PPO implementation. Justification:
  stability, community, integration with *gym* / *gymnasium*, auditable
  code.
- **PyTorch** as the neural network backend. Justification: standard
  in contemporary research, native integration with
  Stable-Baselines3, mature profiling tools.
- **pytest** as the testing framework for the Cage Unit Tests (L4a' of the
  adapted V-Model) and for the general regression suite.
- **Python 3.10+** with quality tools: `ruff` (linting),
  `mypy` (type checking), `pre-commit` for automation on commits.

## C.5 Physical platform

The 1:14 scale radio-controlled vehicle is selected over alternatives
of other scales for three reasons: *cost* — a 1:14 vehicle can be handled easily, the
parts are affordable and the risk of damage in operation is bounded; *operational
safety* — low speeds, low kinetic energy, negligible risk
to third parties on a closed track; and *transferability of the
simulation* — the dynamics of a 1:14 vehicle admit a reasonable approximation in
Gazebo through a plugin-based vehicle model with adjustable
parameters (mass, load distribution, tyre friction,
actuation parameters), while larger scales (1:5, 1:1)
would introduce dynamic discrepancies that would dominate the
sim-to-real gap. The detailed specifications of the car (motor, ESC,
low-level controller, camera, embedded computation platform) are
documented in Chapter 5 and in the corresponding appendix.

<img src="../figures/fig_3_5_vehicle_cad.png" alt="Figure 3.5 — Photograph of the 1:14 RC vehicle instrumented with the camera and IMU." width="300"/>

*Figure 3.5 — photograph/diagram of the 1:14 RC vehicle instrumented with the camera, IMU, encoder and SBC, with labels on each component.*

## C.6 Measurement instrumentation

The primary instrument for evidence capture is the Logger Node of the
ROS2 architecture, already described in adaptation A3 (§3.4.3). The Logger
Node records all the relevant interactions on the bus — observations,
*policy* actions, cage decisions, interventions, vehicle states —
with timestamps that allow later reconstruction.

The concrete metrics computed from the logs are defined
formally in Chapter 4 and are grouped into five families by their
nature: M-P (performance: tracking error, trajectory completeness),
M-S (safety: cage intervention rate, number of violations per SR),
M-I (integration: latencies, jitter, throughput), M-C (behaviour:
lateral stability, control smoothness), and M-T (transfer:
sim-vs-real divergence for each of the previous metrics, metrics specific
to the A5 gap). The detail is deferred to Chapter 4.

For additional quantitative evaluation over the *scenario library*, the
composite QED metric (Gao et al., 2021) is considered as a conceptual
inspiration: a composite metric calibrated against human evaluators
for autonomous driving tasks. Direct adoption requires
qualification, because QED was developed and calibrated on CARLA, while
the simulator adopted in this thesis is Gazebo; the conceptual formula
can be transferred, but the calibrated weights would have to be recomputed for
the lane-following scenario in Gazebo if a metric with an
equivalent meaning is wanted. *Behavior Metrics* (Paniego et al., 2024) is
considered as an auxiliary tool for quantitative evaluation, given
that its design is relatively agnostic to the underlying simulator. The
decision on definitive adoption as the official metric of the project is
deferred to Phase 4, when the trained *policy* is available and it can be
calibrated against the human evaluation of the author.

## C.7 Documentation, version control and reproducibility

All the artefacts of the project — documents, code, templates,
traceability matrix, validation scripts — live in a single
Git repository with the following philosophy: the repository *is* the
project. The conscious choice is *plain text first*: the
artefacts are written in Markdown with minimal extensions (citations in
the format `[Surname (year)]`, LaTeX equations, figures as SVG/PNG in a
dedicated folder), not in industrial MBSE tools of the
Cameo or Capella kind.

This choice differs from the MBSE proposal of Sprockhoff et al. (2023)
for systems with AI components, which defends SysML and structured
tools as the backbone of the life cycle. The difference is
one of *adoption cost*: an individual thesis without access to industrial
licences obtains a better cost/benefit ratio with version-controlled
text files, keeping functional equivalence in terms of
traceability (through `traceability_matrix.csv` + `check_traceability.py`)
and consistency (through automated peer review on every commit).
The decision is documented in `DECISIONS.md` with its explicit
justification and with the conjecture that scaling the framework to a
medium-sized industrial team would indeed motivate the change to MBSE.

---

# C.2 Relation to the standards


The adapted V-Model is related to the normative state of the art in
AI system safety. This section places each adaptation in the
regulatory ecosystem, distinguishing what is coherent with each
standard and what goes beyond it. The review follows the chronological order of
publication, which coincides approximately with the order of industrial
adoption.

## C.1 ISO 26262:2018 — Functional Safety for Road Vehicles

ISO 26262:2018 establishes the classical V-Model applied to the automotive
industry. The thesis takes it as a starting point and as a framework to which it intends
to stay faithful in its general structure.

- **Coherent:** the backbone of five levels L1–L5, the notion
  of a safety requirement, the principle of bidirectional correspondence
  specification↔V&V, the derivation of requirements from the HARA with
  the assignment of ASIL levels.
- **Beyond:** ISO 26262 does not consider learned modules. The
  adaptations A1, A2 and A3 are explicit extensions to accommodate
  RL components without breaking the general structure of the standard. The
  philosophy is one of additive *tailoring*: nothing is removed; only what is
  strictly necessary is added.

## C.2 ISO 21448:2022 — SOTIF (Safety Of The Intended Functionality)

ISO 21448:2022 introduces the notion of safety beyond faults,
including the use of functions under unanticipated conditions, and is the
institutional answer to the fact that systems with perception and
ML-based decision making can behave incorrectly without
any component having "failed" in the classical sense (Wang et al.,
2024).

- **Coherent:** adaptation A5 (bounded operational validation and
  characterisation of the sim-to-real gap) is directly consistent with
  the SOTIF philosophy that static validation is insufficient
  when the ODD is not completely specified. Adaptation A3
  (continuous runtime monitoring) is coherent with the SOTIF principle
  of managing *triggering conditions* discovered in operation.
- **Beyond:** A3 proposes runtime monitoring as an explicit
  architectural level of the life cycle, not only as a practice
  recommended in operation.

## C.3 ISO/IEC TR 5469:2024 — AI Functional Safety

ISO/IEC TR 5469:2024 is the most specific normative document
published to date on the use of AI in safety functions.
Its main contribution for the proposed framework is threefold:
classification of elements into Class I and II, the *three-stage realization
principle* (clause 7) and the desirable properties of AI components
(robustness, specifiability, verifiability, interpretability).

- **Coherent:** the PPO *policy* of the thesis classifies as a
  Class II element of TR 5469 — it does not admit complete classical verification — and
  adaptation A2 (statistical Policy Behavioral Evaluation) is
  congruent with this classification. Mandatory bidirectional
  traceability (A4) operationalises the *specifiability* principle of the
  TR. The split into Cage Spec / Training Spec (A1) articulates at
  the level of the design process the distinction of the *three-stage realization
  principle* between the acquisition, induction and processing phases.
- **Beyond:** the explicit separation between Cage Spec (Class I
  element) and Training Spec (meta-design for a Class II element) in
  separate version-controlled documents is an operational refinement of the
  TR, not present in the normative document at that granularity.

## C.4 ISO/PAS 8800:2024 — Road Vehicles, Safety and AI

ISO/PAS 8800:2024 is the automotive specialisation of the generic
framework of TR 5469. It indicates which ISO 26262 clauses are kept,
which are *tailored* and which are replaced when there is an AI
component. Its early application to a real case (BSI/CAM, 2024, on a
stop sign detector) is the first public template
for articulating ISO 26262 + SOTIF + ISO/PAS 8800.

- **Coherent:** the additive *tailoring* philosophy of the adapted
  V-Model coincides with that of ISO/PAS 8800. The five adaptations
  A1–A5 can reasonably be aligned with the areas that the standard
  identifies as critical (definition of the operating environment,
  systematic analysis of insufficiencies, post-deployment monitoring).
- **Beyond:** the operationalisation of the framework in a complete case
  from HARA to physical deployment, with an empirical characterisation
  of the gap, is more concrete than the examples published to
  date.

## C.5 UL 4600 — Standard for Safety for the Evaluation of Autonomous Products

UL 4600 (Koopman, 2023) emphasises the notion of the *safety case* and
structured evidence as the central assurance mechanism for
autonomous products.

- **Coherent:** the Traceability Matrix H↔SR↔C↔SC↔M is a
  micro safety case in the line of UL 4600: every safety *claim*
  is supported by an explicit argument (the cage rule, the
  scenario, the metric) and by traceable evidence (the logs, the
  experimental results).
- **Beyond:** A4 turns traceability into a hard constraint
  enforced by an automated tool (`check_traceability.py`), and not
  into a documentary good practice to be reviewed.

## C.6 AMLAS — Assurance of Machine Learning for Autonomous Systems

AMLAS, consolidated by Paterson et al. (2025), is not a formal
standard but a methodology with GSN (*Goal Structuring
Notation*) patterns specific to building safety arguments over ML
components. It is being incorporated as an input to emerging
standards, in particular ISO/PAS 8800.

- **Coherent:** the claim-argument-evidence philosophy of AMLAS
  coincides with the bidirectional traceability proposed as A4. The
  data-centric life cycle that AMLAS articulates (requirements
  definition, data management, learning, verification,
  deployment, monitoring) broadly coincides with the
  phase structure of the project described in §3.5.3.
- **Beyond:** AMLAS is mainly tested on supervised
  models; the framework proposed in this thesis is an explicit
  articulation for RL *policies*, a domain still poorly covered by
  AMLAS.

## C.7 The simplified HARA and its relation to the formal version of the standard

Clause 6 of Part 3 of ISO 26262:2018 prescribes the formal HARA
method applied to automotive *items*: situation analysis,
systematic identification of hazards associated with the functions of the
item, classification of each hazard along three axes — severity (S, scale
S0–S3), exposure (E, scale E0–E4) and controllability (C, scale
C0–C3) — and derivation of the *ASIL* (Automotive Safety Integrity Level,
QM/A/B/C/D) through a combination table of S×E×C. The ASIL
determines the rigour required from the rest of the life cycle, including
design measures, verification techniques and test coverage.

The version adopted in this thesis is explicitly called a *simplified
HARA* and is documented as such in the header of the Hazard
Register. The differences with respect to the formal standard are three and are
stated here honestly:

- **S/E/C scales preserved but reinterpreted for the scaled
  context.** The three scales are kept with the granularity of the
  standard (S1–S3, E1–E4, C1–C3), but the qualitative definitions of
  each level are reinterpreted for a 1:14 scale vehicle on a closed
  track: S3 stops meaning "fatal injury" and comes to
  mean "total loss of the integrity of the platform", E3
  keeps the meaning of "10–50 % of the operating time" but
  referred to the declared ODD, and C2 keeps the meaning of
  "controllable in > 90 % of the cases" referred to the rule-based cage
  instead of to the human driver. The reinterpreted rubric is versioned
  together with the register and remains auditable.

- **No formal ASIL is issued; it is replaced by a qualitative
  "Criticality".** The product of the simplified HARA is, for each
  hazard, a qualitative criticality label on four levels
  (Low, Medium, Medium-High, High), derived by qualitative
  aggregation of the S/E/C triple and used exclusively for
  prioritising the mitigation work. The choice not to issue
  a letter ASIL recognises that the ASIL is a
  legal-normative construct oriented towards industrial certification, not towards the
  methodological demonstration that the thesis pursues. Issuing an
  "ASIL B" for a scale car would introduce a false precision
  that the framework prefers to avoid; the qualitative criticality is honest
  about what is being measured and about the use it will be given.
  The derived Safety Requirements carry, separately, their own
  three-level criticality rubric SR-CL-A/B/C defined in
  §4.7.1 of Chapter 4 with different operational consequences
  (minimum rigour of implementation and of verification).

- **Complement with STPA-light over selected hazards.** The simplified
  HARA is complemented with an *STPA-light* analysis applied to
  the hazards of high criticality, bounded to the four categories of
  *unsafe control actions* — action not provided when needed,
  provided when it should not be, provided with an inadequate magnitude, provided
  at the wrong time. This complement captures failure modes
  of a systemic type that a pure HARA, centred on consequences,
  tends to under-represent. The incorporation of STPA is a common
  methodological loan in recent practice on the safety of
  systems with AI components and is documented as such, not as part
  of the formal HARA of ISO 26262.

What the simplified HARA *preserves* is what is methodologically
essential: the systematic enumeration of hazards from the analysis
of the item, the classification prior to the derivation of requirements, the
bidirectional traceability from each hazard to its mitigating SRs
(adaptation A4), and the auditable documentation of each classification
decision. The structure of the process — situation → hazards →
classification → SRs — is identical to that of the standard; what is modulated
is the nature of the final product (qualitative criticality instead
of ASIL) and the complementation with STPA-light over the hazards of
higher relative severity.

The division of work with respect to ISO 21448 (SOTIF) stays
coherent with the usual split in industrial practice: the
simplified HARA identifies systematic failures of the system — the
traditional focus of ISO 26262 — while the *insufficiencies of the
intended functionality* — behaviours that are correct with respect to the
specification but hazardous in operation, the focus of SOTIF — are
covered through adaptation A5 (empirical characterisation of the
sim-to-real gap) and adaptation A3 (runtime monitoring over intervention
logs), and not by the HARA itself. This split is made
explicit in the traceability matrix: the H↔SR hazards cover the
ISO 26262 component of the problem, and the column of "expected evidence
mode" (test / statistical analysis / runtime) covers the SOTIF
component where it applies.

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figure 3.6 — Diagram of the normative pyramid." width="500"/>

*Figure 3.6 — diagram of the normative pyramid: ISO 26262 at the base as the life cycle, SOTIF as the complement for unanticipated conditions, TR 5469 as the AI umbrella, PAS 8800 as the automotive specialisation, UL 4600 as the enclosing safety case, AMLAS as transversal argumentation patterns. On top of that pyramid, the five adaptations A1–A5 marked with their scope of application. Suggested position: close of §3.8. Pending for Phase 6.*

---
