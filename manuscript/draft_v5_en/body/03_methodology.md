# Chapter 3 — Methodology

## 3.1 Purpose of the chapter

This chapter presents the central methodological contribution of the thesis: the adapted V-Model, a life cycle framework designed for systems that incorporate components trained by reinforcement learning inside functions with safety implications. It establishes the framework that governs the rest of the work, justifies the decisions that configure it, and positions each one with respect to the standards and to the literature of Chapter 2; it does not present experimental results or implementation details.

Two levels that are often confused should be separated. The *research methodology* — how generalisable knowledge is produced from the work — is discussed in §3.2. The *system engineering methodology* — how the technical artefact is produced from the requirements to the deployment — occupies §3.3 to §3.8. The first one answers "what does this thesis contribute to knowledge?"; the second one, "how is the system built?". Chapters 4 to 10 are the experimental materialisation of what is defined here, and Chapter 11 evaluates the framework in the light of that materialisation.

## 3.2 Epistemological positioning

### 3.2.1 Type of research

The work belongs to the tradition of *design science research* (Hevner et al., 2004) or, in a close formulation, *constructive research* (March and Smith, 1995). In that tradition the academic contribution is not an empirical proposition contrasted against reality, nor a logical proposition proved deductively, but an artefact that addresses a previously identified problem and whose usefulness is evaluated through one or several application cases.

The artefact is the adapted V-Model — five adaptations A1–A5 over the ISO 26262 V-Model — together with the templates, validators and derived artefacts that materialise it. This characterisation has three consequences. First: the thesis does not look for the typical contribution of an empirical thesis — discovering a phenomenon, refuting a statistical hypothesis — but for the production of a useful artefact and the demonstration of its operation. Second: the evaluation is made on the artefact and not only on the system built with it, which requires a chapter devoted to evaluating the framework itself (Chapter 11). Third: generalisation is argued by structural plausibility — the adaptations attack V-Model assumptions that fail for any system with a learned component — and not by statistical induction over multiple cases.

### 3.2.2 Evaluation strategy: a single case study

The framework is evaluated through a single case: lane following on a 1:14 scale vehicle, trained by PPO in Gazebo and supervised by a deterministic safety cage. The reason is feasibility: a case that covers the complete cycle — from HARA to deployment — is already an ambitious commitment for a master's thesis, and multiplying it would introduce a superficiality that is incompatible with the rigour that the framework itself demands. A deep case is preferable to several shallow ones. The cost is in external validity, and it is mitigated in two ways: the structural plausibility argument, and the explicit recognition, in Chapter 12, of which parts of the framework are transferable and which ones require rethinking.

### 3.2.3 Role of the author

The author is at the same time the designer of the framework, the implementer of the system and the evaluator of the result. That triple condition introduces a structural confirmation bias that should be recognised before any attempt to neutralise it. The mitigation is articulated on three levels: bidirectional traceability as a hard constraint (A4), enforced by an automatic validator that exposes any orphan without intervention from the author and acts as a low-cost external auditor; the dated decision log, which documents not only what was decided but also which alternatives were discarded and why, and which can be audited afterwards by third parties; and the explicit declaration of limitations (§3.9 and Chapter 11) with the same honesty that would be reserved for someone else's solution. The three mechanisms do not eliminate the bias — none of them can — but they bound it to what an independent third party could audit over the version-controlled artefacts.

## 3.3 The classical V-Model and its implicit assumptions

The V-Model, with its root in systems engineering (Forsberg and Mooz, 1991), formalised in ISO/IEC/IEEE 15288 and adopted by ISO 26262, structures the process in five hierarchical levels with a bidirectional correspondence between specification (descending branch) and verification/validation (ascending branch).

<img src="../figures/fig_3_1_adopted_classical_v_model.png" alt="Figure 3.1 — V-Model adopted by ISO 26262, instantiated on the lane-following case." width="480"/>

*Figure 3.1 — V-Model adopted by ISO 26262 (simplified), instantiated on the lane-following case.*

It operates on five assumptions that are rarely made explicit but that support its whole structure. Their systematic identification has a founding antecedent in Salay, Queiroz and Czarnecki (2017); the assumptions S1–S5 that follow are an operational reformulation of that analysis, articulated so that each one admits a corresponding adaptation in §3.4.

| Assumption | Statement | Why it fails for an RL component |
| --- | --- | --- |
| S1 | Every module has a complete and deterministic specification written in advance | The policy has no pre-designed specification: it emerges from the training. There is no document saying "when the input is Y, produce Z" |
| S2 | The behaviour can be faithfully derived from the specification | The behaviour is observable *post hoc* but not predictable analytically |
| S3 | Unit tests verify compliance with finite coverage | There is no "correct" output defined per input: only statistically plausible outputs |
| S4 | Static verification is enough to guarantee the properties | The policy can pass the tests and fail in operation because of state distributions that were not covered |
| S5 | The operational environment is sufficiently similar to the testing one | The gap between simulation and reality can be large and silent |

*Table 3.1 — The five assumptions of the classical V-Model and how they fail for learned components.*

The quantitative extent of the problem is illustrated by the finding of Salay et al. about the 75 software techniques prescribed in Part 6 of ISO 26262: close to 40 % do not apply to ML components without modification, distributed between techniques that are directly reusable, adaptable with modification, and inapplicable because they are oriented towards imperative languages. That void is operational, not only conceptual, and it is what motivates a complementary framework.

The five failures are not an argument for abandoning the V-Model but for adapting it. The methodological core of this work consists in keeping the structure of the V — and with it the coherence with ISO 26262 — while introducing the minimum modifications necessary for the policy to fit inside the cycle without breaking the traceability or the honesty of the process.

## 3.4 The five adaptations

### 3.4.1 A1 — Splitting the module design

**Problem.** The module design level (L4) assumes that every module admits a complete, deterministic specification that can be written in advance. For the policy the assumption breaks: it is not possible to write "the policy must produce `a = f(s)` such that…" because `f` is the result of the optimisation, not its input.

**Adaptation.** L4 is split into two conceptually different sublevels. L4a — Cage Specification is classical specification: deterministic and modular, where each cage rule is a pure, testable function with defined inputs and outputs, designed in the traditional sense. L4b — Training Specification is a *meta-specification*: it does not specify the behaviour of the policy but the process that produces it — reward function, state and action spaces, training ODD, convergence criteria, algorithm, constraints active during the training.

The separation is coherent with the three-stage realisation principle of ISO/IEC TR 5469:2024, which distinguishes acquisition from inputs, induction of knowledge from data, and generation of outputs; A1 brings that distinction to the level of the design process. Artefacts: the cage specification with its formally defined rules (Chapter 5) and the training specification (Chapter 7).

### 3.4.2 A2 — From unit testing to behavioural evaluation

**Problem.** The unit test verifies a module against its specification through cases with expected outputs. For the policy there is no "expected output" for a given state: only plausible distributions conditioned on the state.

**Adaptation.** The level is split in correspondence with A1. L4a' — Cage Unit Tests: classical unit tests over each rule, with synthetic state vectors, expected deterministic behaviour and a binary verdict; identical in philosophy to those of the classical V. L4b' — Policy Behavioral Evaluation: statistical evaluation over state distributions — "over N states sampled from the ODD, the policy produces actions that satisfy property X with frequency Y". This is not verification in the logical sense, it is statistical characterisation of the behaviour.

The adaptation recognises that classical verification is not applicable to learned components. The thesis does not force the metaphor: it replaces it with an appropriate tool, and keeps classical verification where it is still applicable, namely the cage. The asymmetry is coherent with the Class I / Class II element distinction of TR 5469: the cage operates as a Class I element, the policy as a Class II element.

### 3.4.3 A3 — Runtime monitoring as continuous validation

**Problem.** The V-Model assumes that validation is completed before deployment: once validated, the system is deployed and maintained. There is no level devoted to continuous post-deployment validation.

**Adaptation.** A horizontal level is added — Runtime Monitoring — fed by the intervention logs of the cage during operation, which feeds validation back continuously. The level recognises three facts that are specific to systems with AI: the operational distribution can differ from the testing one; failure modes that were not anticipated in the hazard analysis can emerge; and safety evidence has to be accumulated over time.

In this work the logging node is not an auxiliary component but the primary instrument of the level: the logs it produces during the experimental campaigns are continuous validation evidence within the project window, and in a real deployment the same mechanism would generate evidence indefinitely. The adaptation is coherent with the SOTIF philosophy and with the V-Model reformulation of Wang et al. (2024), and it inherits from Mohseni et al. (2019) the categorisation of the *monitoring function* as an architectural category in its own right, taking it one step further: it raises it from a technical mechanism to an explicit level of the life cycle, with version-controlled artefacts and a defined role in the traceability matrix.

### 3.4.4 A4 — Mandatory traceability as a hard constraint

**Problem.** Traceability between levels is recommended but, in practice, not required: glue logic can exist without an explicit parent requirement. In classical systems this is tolerable because the behaviour can be inspected in its entirety.

**Specific problem in RL.** When a component is learned, the temptation to attribute behaviours to "emergent properties" is high. Without strict traceability, any behaviour can be justified retrospectively as something the policy learned, which empties engineering responsibility of its content.

**Adaptation.** Bidirectional traceability moves from good practice to hard constraint, with five simultaneous obligations: every cage rule references at least one safety requirement; every requirement has at least one rule that implements it — or an explicit argument for why it does not require one; every hazard has at least one requirement that mitigates it or a documented accepted risk; every scenario references at least one requirement that it verifies; and every metric references at least one requirement to which it contributes evidence. An automated validator runs on every change and fails if it detects orphans in either direction.

<img src="../figures/fig_3_2_check_traceability_flow.png" alt="Figure 3.2 — Flow of the traceability validator." width="470"/>

*Figure 3.2 — Flow of the traceability validator, in four layers: loading of the living documents; extraction of identifiers defined by regular expressions over the headings; chain of constraints over the graph `H ↔ SR ↔ C ↔ SC` with the subgraph `SR ↔ M` hanging from the requirements node; and final aggregation with three possible outputs — all checks pass, orphan or invalid reference, or a warning in strict mode.*

The design consequence is indirect but important: the constraint simplifies the hazard analysis phase, because it forces the question "which rule am I going to have for this?" from the very first requirement. The result is requirements that are more operational and less abstract. The philosophy is close to the GSN patterns of AMLAS, but A4 goes one step further by turning traceability into a property verifiable by a tool instead of a documentary practice to be reviewed.

### 3.4.5 A5 — Bounded operational validation and gap characterisation

**Problem.** The acceptance test assumes a binary verdict against the requirements of the stakeholders and, implicitly, that the test conditions represent the operational ones. For a system trained in simulation this is false: the gap is a first-order risk, and a test passed in simulation does not imply safe operation in the real world.

**Adaptation.** The level is reformulated as Operational Validation with two mandatory components: scenario-based validation linked to requirements, with coverage metrics over the ODD; and explicit and quantitative characterisation of the gap between the training environment and the operational environment, per metric and per relevant failure mode. The validation conclusion stops being "the system is safe" and becomes: *the system satisfies the requirements under the conditions of ODD X, with a measured gap of Y with respect to the training conditions, and with the following residual risks documented*.

### 3.4.6 Synthesis

| ID | Adaptation | Problem of the classical V | Solution | Artefact |
| --- | --- | --- | --- | --- |
| A1 | Splitting the module design | The policy admits no a priori specification | Cage Spec (classical) + Training Spec (meta-design) | Ch. 5 and 7 |
| A2 | Splitting the unit test | The policy admits no classical unit test | Cage tests + statistical behavioural evaluation | Test suite + Ch. 8 |
| A3 | Runtime monitoring level | Static validation is not sufficient | Intervention logging as continuous evidence | Logging node + data |
| A4 | Mandatory traceability | Orphans hide "emergent properties" | Bidirectional hard constraint `H↔SR↔C↔SC↔M` | Matrix + validator |
| A5 | Bounded validation with gap | The simulation test does not represent operation | Verdict with limits + quantified gap | Ch. 9 and 10 |

*Table 3.2 — The five adaptations to the classical V-Model.*

<img src="../figures/fig_3_3_adapted_v_model.png" alt="Figure 3.3 — Adapted V-Model." width="480"/>

*Figure 3.3 — V-Model adapted to AI. In grey, the elements inherited from the classical V; in colour, those that are new or modified by adaptations A1–A5.*

## 3.5 Operationalisation on the case study

### 3.5.1 System under study and architectural decision

The system is a 1:14 scale radio-controlled vehicle with a monocular front camera as its primary sensor, an inertial unit and a motor encoder, with embedded computation on a board with ROS2 support. It is developed on two parallel platforms: the simulated one — Gazebo with native ROS2 integration, operated through a gymnasium–Gazebo–ROS2 interface that reuses an environment built by the author in earlier work — and the physical one, on a closed track with controlled lighting.

One architectural decision is relevant for the methodology and not only for the system. Initially the project adopted an explicit modular decomposition — perception, policy, cage, actuation and logging — with the learned component in a bounded position, in line with the recommendation of Salay et al. (2017) to avoid ML at the architectural level and to limit it to the unit level. Later on, the main system became an end-to-end camera variant: the policy is a CNN that learns perception and maps image to action.

The supersession is safe because the safety architecture is not replaced: the cage is kept and operates on its own deterministic lane estimator — a classical vision chain, separate from the CNN and therefore neither ground truth nor a learned network — so that the pixels enter the policy but the envelope reasons over an auditable and independent state. The adaptations that motivated the original decision are still valid: A1, because cage and policy are still different modules; A2, because the cage is verifiable independently of the policy; and A4, because the traceability chain does not change. The cost accepted is the other original reason — the larger training volume that the end-to-end approach demands — which is budgeted in Chapter 7. The state track is kept frozen as a control arm in order to isolate the cost of perception.

### 3.5.2 Mapping of the framework onto the case

| Level of the adapted V-Model | Artefact in the case study | Chapter |
| --- | --- | --- |
| L1 — Stakeholder requirements | ODD + use case | 4 |
| L2 — System safety requirements | `SR-001..SR-014` derived from the HARA | 4 |
| L3 — Architectural design | ROS2 graph (perception, policy, cage, actuation, logging) | 5 |
| L4a — Cage Specification | Rules `C-01..C-06` | 5 |
| L4b — Training Specification | Reward, training ODD, hyperparameters, criteria | 7 |
| L5 — Implementation | ROS2 cage node + trained policy | 6, 7 |
| L4a' — Cage unit tests | Deterministic cage suite | 6 |
| L4b' — Policy behavioural evaluation | Statistical analysis over the scenario library | 8 |
| L3' — Integration test | Tests of the complete chain | 6 |
| L2' — Scenario-based test | Families `SC-NOM` / `SC-EDGE` / `SC-PERT` / `SC-FRONT` | 6, 8 |
| L1' — Operational validation | Campaign + sim-to-real gap + verdict per requirement | 9, 10 |
| Runtime monitoring (A3) | Logging node + intervention logs (transversal) | 5–10 |

*Table 3.3 — Mapping of the framework onto the case study.*

The mapping is the first check that the framework can be operationalised: every level of the V has an identifiable artefact, a chapter where it is developed, and a position in the traceability matrix.

### 3.5.3 Phase structure

The project is organised in seven sequential phases, each one with defined deliverables and a review gate at its close that decides whether to proceed to the next one. The phase structure is orthogonal to the V-Model: one phase produces artefacts of several levels at the same time, and one level can be built across several phases. In summary: the initial phase establishes the framework and the templates; the next one produces the ODD, the hazard analysis and the requirements; the third one develops the cage and its tests; the fourth one defines the training specification and the scenario library; the fifth one executes the training and the behavioural evaluation; the sixth one deploys physically and characterises the gap; and the last one consolidates the evidence and closes the matrix.

<img src="../figures/fig_3_4_project_phases.png" alt="Figure 3.4 — Project phases against the levels of the adapted V-Model." width="480"/>

*Figure 3.4 — Project phases against the levels of the adapted V-Model. The monitoring band extends horizontally because it becomes operative as soon as the cage node exists and persists until the close; the traceability band shows how the chain `H ↔ SR ↔ C ↔ SC ↔ M` is completed phase by phase.*

One point deserves emphasis because it is where the framework stops being a proposal and becomes practice: A4 comes fully into force from the hazard analysis phase onwards. The validator runs on every change of the hazard register and of the requirements specification, requiring that every hazard link to at least one requirement that mitigates it — or to a documented accepted risk — and vice versa. From that moment the cycle "document → link → validate" runs on every commit.

## 3.6 Instrument choices

Each instrument choice is justified against the alternatives that were discarded, so that decisions which would otherwise remain implicit leave an auditable record. Only the simulator is argued here, because it is the choice the methodology depends on: it is what adaptation A5 has to measure the gap against. The remaining ones — the learning algorithm and library, the physical platform, the measurement instrumentation and the reproducibility tooling — are argued with the same structure in Appendix C, together with the clause-by-clause normative mapping. The middleware is not argued separately because its choice sits inside the simulator's: native ROS2 integration is precisely the first of the four reasons above.

**Simulator: Gazebo.** The choice differs from dominant practice, where CARLA is the reference, and it rests on four reasons. *Native ROS2 integration*: Gazebo is co-developed with ROS and shares primitives without intermediate layers; since the whole architecture is ROS2 by design, hosting the simulator in the same graph removes failure surface and reduces the ambiguity about where latencies occur, which directly affects the fidelity of the integration metrics. *Reuse of earlier work*: the author has an environment with the vehicle modelled and the track configured; reusing it frees time for the methodological contribution, which is the real object of the thesis — coherent with the *design science* approach, where the contribution is not in the instrument. *Available training interface*, which allows a clean separation of algorithm, environment and system, and therefore facilitates A1. *Modest computation requirements*, which is relevant for an individual thesis without dedicated infrastructure.

The choice carries two trade-offs that should be recognised. The visual fidelity of Gazebo is lower than that of the photorealistic engines; for a camera-based policy this can translate into a more pronounced sim-to-real gap. Adaptation A5 is designed precisely to make that effect visible and to measure it, not to hide it. And the autonomous driving community mostly uses CARLA, so there are no reusable scenario libraries in Gazebo format: the one for this project has to be built explicitly.

Discarded alternatives: CARLA, the strongest candidate, because of its computation cost and because it requires a ROS2 bridge with its own complications; Highway-Env and derivatives, because they lack realistic sensors and work over abstract observations, which makes them unsuitable for camera-based policies; LGSVL, discontinued; and AirSim, with an aerospace focus and development on hold.

## 3.7 How the framework itself will be evaluated

The question in this section is whether the methodology was useful for producing the system, not whether the system turned out to be useful: the two are separable, because a successful framework applied to a modest system is possible, and so is the opposite. The evaluation is articulated in five criteria, each one with an indicator that can be measured at the close:

1. **Traceability integrity.** Indicator: orphans detected by the validator in the last run. Success: zero.
2. **Requirement coverage by evidence.** Indicator: percentage of requirements with a verdict backed by quantitative evidence. Success: 100 % have a verdict, even if the verdict is negative or partial. An uncomfortable verdict is preferable to an omission.
3. **Hazard anticipation.** Indicator: proportion of hazards that actually appeared, against the unanticipated ones that emerged. Success: most of the observed ones were anticipated, and the unanticipated ones are auditable and can be categorised.
4. **Adoption cost.** Indicator: time spent on framework artefacts against purely technical artefacts. Success: cost proportional to the observed benefit.
5. **Productivity of the matrix.** Indicator: technical changes whose impact analysis was accelerated by the matrix. Success: documented cases where it provided observable value.

The evaluation has three declared limits: it is internal to a single project and without a control group, so the inference is by plausibility and not by controlled experimentation; the author bias is bounded but not eliminated; and the experimental window is finite, whereas the benefits of A3 would appear over much longer horizons.

## 3.8 Relation to the standards

The framework does not replace the standards: it articulates them. Each adaptation has an identifiable normative anchor, summarised in Table 3.4; the complete mapping, clause by clause, is given in Appendix C.

| Adaptation | Main normative anchor |
| --- | --- |
| A1 — Cage Spec + Training Spec | TR 5469 §7 (three-stage realisation principle); PAS 8800 (adaptation of the module design) |
| A2 — Cage tests + behavioural evaluation | TR 5469 (Class I / Class II elements); ISO 26262 Part 6 for the classical part |
| A3 — Runtime monitoring | SOTIF (insufficiency of static validation); Wang et al. (2024), continuous operation phase |
| A4 — Hard traceability | ISO 26262 Part 8 (requirements management); AMLAS (GSN patterns); UL 4600 (claim–argument–evidence) |
| A5 — Bounded validation + gap | SOTIF (unanticipated conditions); UL 4600 (declared limits of the safety case) |

*Table 3.4 — Normative anchor of the five adaptations.*

One clarification about the hazard analysis: the HARA adopted here is simplified with respect to the one prescribed by ISO 26262, and it is not developed in parallel to the V but inside it, occupying exactly the position that the standard reserves for the output of the formal HARA. The simplifications and their justification are detailed in Chapter 4.

## 3.9 Limitations of the methodology

It is better to declare them in cold blood, before the reader identifies them in the heat of the closing chapters.

- **Construct validity limited by the single case.** Generalisation rests on structural plausibility, not on multi-case evidence. Mitigation: Chapter 12 distinguishes which parts are transferable and which ones require rethinking.
- **Dependence on a simulation of moderate visual fidelity.** The training runs entirely in Gazebo, which can accentuate the gap in the visual features captured by the camera. Mitigation: A5 makes it visible and Chapter 9 quantifies it; replicating the experiment on a photorealistic simulator remains a natural extension.
- **The five adaptations are not exhaustive.** Others would be defensible — for example a level devoted to data engineering, following the data-centric philosophy of TR 5469 and AMLAS. The five adopted here are justified individually, but there is no argument that they are the only possible ones.
- **The framework does not eliminate the author bias**, it only exposes it to audit.

## 3.10 Transition

With the framework defined, the following chapters execute it. Chapter 4 materialises the upper left branch of the V — operational domain, hazard analysis and requirement derivation — and produces the first artefacts on which A4 operates as a hard constraint. From there on, each chapter occupies one level of the V and closes its correspondence with the symmetric level of the right branch.
