# Chapter 3 — Methodology

## 3.1 Purpose of the chapter

This chapter presents the main methodological contribution of the thesis: the adapted V-Model. It is a life cycle framework for systems that include components trained with reinforcement learning inside functions that affect safety. The chapter defines the framework used in the rest of the work, explains the decisions behind it, and relates each decision to the standards and to the literature from Chapter 2. It does not present experimental results or implementation details.

Two things are often mixed up and should be kept apart. The *research methodology* — how this work produces knowledge that can be generalised — is covered in §3.2. The *system engineering methodology* — how the technical system is built from requirements to deployment — runs from §3.3 to §3.8. Chapters 4 to 10 put into practice what is defined here, and Chapter 11 evaluates the framework based on that practice.

## 3.2 Research approach

### 3.2.1 Type of research

The work follows the *design science research* tradition (March and Smith, 1995; Hevner et al., 2004). In this tradition, the academic contribution is not an empirical claim tested against reality, and not a logical statement proved by deduction. It is an artefact that solves a known problem, and its usefulness is evaluated through one or more application cases.

The artefact here is the adapted V-Model: five adaptations A1–A5 to the ISO 26262 V-Model, with the templates and checkers that implement them. Three consequences follow. The thesis does not aim to find a phenomenon or reject a statistical hypothesis, but to build a useful artefact and show that it works. The evaluation looks at the artefact and not only at the system built with it, which is where Chapter 11 comes from. And generalisation is argued through structure — the adaptations target assumptions that fail for any system with a learned component — and not through statistics over many cases.

### 3.2.2 Evaluation strategy: one case study

The framework is evaluated on a single case: lane following on a 1:14 scale vehicle, trained with PPO in Gazebo and supervised by a deterministic safety cage. The reason is feasibility. A case that covers the whole cycle, from HARA to deployment, is already a lot of work for a master's thesis. Doing several would make each one shallow, which does not fit the rigour that the framework itself asks for. One deep case is better than several shallow ones. The price is lower external validity. This is reduced in two ways: the structural argument, and a clear statement in Chapter 12 of which parts of the framework can be reused and which parts need to be rethought.

### 3.2.3 Role of the author

The author designs the framework, builds the system and evaluates the result. That creates a built-in risk of confirmation bias, which has to be admitted before trying to reduce it, and it is handled on three levels. The first is two-way traceability as a hard constraint (A4). A checker reports orphans without the author being involved, so it acts as an independent reviewer at very low cost. The second is the dated decision log, which records what was decided, what was rejected and why, so that others can audit it later. The third is the list of limitations (§3.9 and Chapter 11), written as critically as if the solution came from someone else. None of these removes the bias, and nothing could: what they do is leave it open to what an independent person can check in the version-controlled artefacts.

## 3.3 The classical V-Model and its hidden assumptions

The V-Model comes from systems engineering (Forsberg and Mooz, 1991) and is the reference process model in ISO 26262. It organises development into five levels, with a two-way link between specification (left branch, going down) and verification and validation (right branch, going up).

<img src="../figures/fig_3_1_adopted_classical_v_model.png" alt="Figure 3.1 — V-Model adopted by ISO 26262, instantiated on the lane-following case." width="480"/>

*Figure 3.1 — V-Model adopted by ISO 26262 (simplified), applied to the lane-following case.*

The model relies on five assumptions. They are rarely written down, but the whole structure depends on them. Salay, Queiroz and Czarnecki (2017) were the first to identify them systematically. The assumptions S1–S5 below are a practical rewrite of their analysis, set up so that each one has a matching adaptation in §3.4.

| Assumption | Statement | Why it fails for an RL component |
| --- | --- | --- |
| S1 | Every module has a complete and deterministic specification written in advance | The policy has no designed specification: it comes out of training. No document says "when the input is Y, produce Z" |
| S2 | The behaviour can be derived reliably from the specification | The behaviour can be observed *post hoc* but cannot be predicted analytically |
| S3 | Unit tests check compliance with finite coverage | There is no "correct" output for each input, only statistically plausible outputs |
| S4 | Static verification is enough to guarantee the properties | The policy can pass the tests and still fail in operation, because of state distributions that were not tested |
| S5 | The operating environment is close enough to the test environment | The gap between simulation and reality can be large and go unnoticed |

*Table 3.1 — The five assumptions of the classical V-Model and how they fail for learned components.*

The gap is practical and not only conceptual: of the Part 6 software techniques that apply at unit level, about 40 % do not apply to ML components at all (§2.6). That is the reason for a complementary framework.

These five failures are not a reason to drop the V-Model. They are a reason to adapt it. The core of this work is to keep the V structure, and with it the consistency with ISO 26262. Only the changes needed to fit the policy into the cycle are added, and they must not break traceability or the honesty of the process.

## 3.4 The five adaptations

### 3.4.1 A1 — Splitting the module design

**Problem.** The module design level (L4) assumes that every module can have a complete, deterministic specification written beforehand. This is not true for the policy. It is not possible to write "the policy must produce `a = f(s)` such that…" because `f` is the result of the optimisation, not something that goes into it.

**Adaptation.** L4 is split into two different sublevels. L4a — Cage Specification is a classical specification. It is deterministic and modular, and each cage rule is a pure, testable function with defined inputs and outputs, designed in the traditional way. L4b — Training Specification is a *meta-specification*. It does not describe how the policy behaves. It describes the process that produces the policy: reward function, state and action spaces, training ODD, convergence criteria, algorithm, and constraints active during training.

This split fits the three-stage realisation principle of ISO/IEC TR 5469:2024, which separates data acquisition, knowledge induction from data and human knowledge, and processing and output generation. The TR says that this principle is not a life cycle, so A1 extends the idea to the design process. Artefacts: the cage specification with its formally defined rules (Chapter 5) and the training specification (Chapter 7).

### 3.4.2 A2 — From unit testing to behavioural evaluation

**Problem.** A unit test checks a module against its specification using cases with expected outputs. For the policy there is no "expected output" for a given state, only plausible distributions that depend on the state.

**Adaptation.** This level is split in the same way as A1. L4a' — Cage Unit Tests are classical unit tests for each rule, with synthetic state vectors, expected deterministic behaviour and a pass/fail result, just like in the classical V. L4b' — Policy Behavioral Evaluation is a statistical evaluation over state distributions, for example "over N states sampled from the ODD, the policy produces actions that meet property X with frequency Y". This is not verification in the logical sense. It is a statistical description of behaviour.

The adaptation accepts that classical verification does not work for learned components. The thesis does not try to force it. It uses a suitable tool instead, and keeps classical verification where it still works, which is the cage. This difference matches, by analogy, the technology classes of TR 5469. The cage is a conventional rule-based component and can be fully developed and reviewed with existing functional safety practice, like Class I technology. The policy is at best a Class II element, whose required properties can only be approached with extra methods such as the statistical evaluation of A2.

### 3.4.3 A3 — Runtime monitoring as continuous validation

**Problem.** The V-Model assumes that validation ends before deployment. Once validated, the system is deployed and maintained. There is no level for continuous validation after deployment.

**Adaptation.** A horizontal level called Runtime Monitoring is added. It is fed by the cage's intervention logs during operation, and it sends that information back to validation continuously. This level accepts three facts that are specific to AI systems: the operating distribution can be different from the test distribution; failure modes that the hazard analysis did not predict can appear; and safety evidence has to be collected over time.

In this work the logging node is not a helper component. It is the main tool of this level. The logs it produces during the experimental campaigns are continuous validation evidence within the project period, and in a real deployment the same mechanism would keep producing evidence with no end date. The adaptation fits the SOTIF approach and the operation phase that Wang et al. (2024) use to organise SOTIF research. From Mohseni et al. (2019) it takes the idea of the *monitoring function* as its own architectural category, and goes one step further: monitoring stops being only a technical mechanism and becomes an explicit level of the life cycle, with version-controlled artefacts and a defined place in the traceability matrix.

### 3.4.4 A4 — Required traceability as a hard constraint

**Problem.** Traceability between levels is recommended but in practice not enforced. Glue code can exist without a parent requirement. In classical systems this is acceptable, because the whole behaviour can be inspected.

**Specific problem in RL.** When a component is learned, it is tempting to explain behaviours as "emergent properties". Without strict traceability, any behaviour can be explained afterwards as something the policy learned, and engineering responsibility loses its meaning.

**Adaptation.** Two-way traceability changes from good practice to a hard constraint, with five obligations that all apply at once. Every cage rule points to at least one safety requirement. Every requirement has at least one rule that implements it, or an explicit reason why it does not need one. Every hazard has at least one requirement that reduces it, or a documented accepted risk. Every scenario points to at least one requirement that it verifies. Every metric points to at least one requirement for which it provides evidence. An automatic checker runs on every change and fails if it finds orphans in either direction.

<img src="../figures/fig_3_2_check_traceability_flow.png" alt="Figure 3.2 — Flow of the traceability validator." width="470"/>

*Figure 3.2 — Flow of the traceability checker, in four layers: loading the living documents; extracting identifiers with regular expressions over the headings; checking the chain of constraints over the graph `H ↔ SR ↔ C ↔ SC`, with the subgraph `SR ↔ M` attached to the requirements node; and combining the results into one of three outputs: all checks pass, orphan or invalid reference, or a warning in strict mode.*

This has an indirect but important effect on design. The constraint makes the hazard analysis easier, because from the very first requirement it forces the question "which rule will handle this?". The result is requirements that are more practical and less abstract. The idea is close to the GSN patterns of AMLAS, but A4 goes one step further by making traceability something a tool can check, instead of a documentation practice that someone has to review.

### 3.4.5 A5 — Bounded operational validation and gap measurement

**Problem.** The acceptance test assumes a pass/fail verdict against the stakeholders' requirements and, without saying it, assumes that test conditions represent real operating conditions. For a system trained in simulation this is false. The gap is a major risk, and passing a test in simulation does not mean the system is safe in the real world.

**Adaptation.** This level becomes Operational Validation, with two required parts. The first is scenario-based validation linked to requirements, with coverage metrics over the ODD. The second is an explicit, quantitative measurement of the gap between the training environment and the operating environment, for each metric and each relevant failure mode. The conclusion is no longer "the system is safe". It becomes: *the system meets the requirements under the conditions of ODD X, with a measured gap of Y compared with the training conditions, and with the following residual risks documented*.

### 3.4.6 Summary

| ID | Adaptation | Problem of the classical V | Solution | Artefact |
| --- | --- | --- | --- | --- |
| A1 | Splitting the module design | The policy has no a priori specification | Cage Spec (classical) + Training Spec (meta-design) | Ch. 5 and 7 |
| A2 | Splitting the unit test | The policy cannot be unit tested in the classical way | Cage tests + statistical behavioural evaluation | Test suite + Ch. 8 |
| A3 | Runtime monitoring level | Static validation is not enough | Intervention logging as continuous evidence | Logging node + data |
| A4 | Required traceability | Orphans hide "emergent properties" | Two-way hard constraint `H↔SR↔C↔SC↔M` | Matrix + checker |
| A5 | Bounded validation with gap | The simulation test does not represent operation | Verdict with limits + measured gap | Ch. 9 and 10 |

*Table 3.2 — The five adaptations to the classical V-Model.*

<img src="../figures/fig_3_3_adapted_v_model.png" alt="Figure 3.3 — Adapted V-Model." width="480"/>

*Figure 3.3 — V-Model adapted to AI. Grey elements come from the classical V; coloured elements are new or changed by adaptations A1–A5.*

## 3.5 Applying the framework to the case study

### 3.5.1 System under study and architecture decision

The system is a 1:14 scale radio-controlled vehicle. Its main sensor is a single front camera, and it also has an inertial unit and a motor encoder, with onboard computing on a board that supports ROS2. It is developed on two platforms in parallel. One is simulated: Gazebo with native ROS2 integration, run through a gymnasium–Gazebo–ROS2 interface that reuses an environment the author built in earlier work. The other is physical: a closed track with controlled lighting.

One architecture decision matters for the methodology and not only for the system. At first the project used an explicit modular split (perception, policy, cage, actuation and logging), with the learned component kept in a limited position, following the advice of Salay et al. (2017) to avoid ML at the architectural level and keep it at unit level. Later the main system became an end-to-end camera version, with the policy a CNN that learns perception and maps the image to an action.

The change is safe because the safety architecture stays the same: the cage still works on its own lane estimator, a classical vision pipeline separate from the CNN that is neither ground truth nor a learned network. The pixels go into the policy, but the envelope works on an independent, auditable state. So A1 still holds (cage and policy are still different modules), A2 too (the cage is verified without the policy) and A4 likewise (the traceability chain does not change). The cost accepted is the one the original reason already named: end-to-end learning needs more training, and Chapter 7 plans for it. The state track is kept frozen as a control arm to isolate the cost of perception.

### 3.5.2 Mapping the framework onto the case

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
| L3' — Integration test | Tests of the full chain | 6 |
| L2' — Scenario-based test | Families `SC-NOM` / `SC-EDGE` / `SC-PERT` / `SC-FRONT` | 6, 8 |
| L1' — Operational validation | Campaign + sim-to-real gap + verdict per requirement | 9, 10 |
| Runtime monitoring (A3) | Logging node + intervention logs (across levels) | 5–10 |

*Table 3.3 — Mapping of the framework onto the case study.*

This mapping is the first check that the framework can be put into practice. Every level of the V has an artefact, a chapter where it is developed, and a place in the traceability matrix.

### 3.5.3 Phases

The project has seven phases in sequence, each with defined deliverables and a review gate that decides whether to move on. They are independent of the V-Model levels: one phase can produce artefacts for several levels, and one level can be built over several phases. Figure 3.4 crosses phases against levels: setting up the framework and the templates; ODD, hazard analysis and requirements; the cage and its tests; the training specification and the scenario library; training and behavioural evaluation; physical deployment and gap measurement; and closing the evidence and the matrix.

<img src="../figures/fig_3_4_project_phases.png" alt="Figure 3.4 — Project phases against the levels of the adapted V-Model." width="480"/>

*Figure 3.4 — Project phases compared with the levels of the adapted V-Model. The monitoring band runs horizontally because it starts working as soon as the cage node exists and continues until the end. The traceability band shows how the chain `H ↔ SR ↔ C ↔ SC ↔ M` is completed phase by phase.*

One point is worth stressing, because it is where the framework stops being a proposal and becomes practice. A4 is fully active from the hazard analysis phase onwards. The checker runs on every change to the hazard register and the requirements specification. It requires every hazard to link to at least one requirement that reduces it, or to a documented accepted risk, and the other way round. From then on, the cycle "document → link → check" runs on every commit.

## 3.6 Choice of tools

Each tool choice is explained against the alternatives that were rejected, so that decisions that would otherwise stay implicit leave an auditable record. Only the simulator is discussed here, because the methodology depends on it: it is the reference that A5 measures the gap against. The others (the learning algorithm and library, the physical platform, the measurement equipment and the reproducibility tools) are treated the same way in Appendix C, together with the clause-by-clause mapping to the standards. The middleware is not discussed separately because it comes with the simulator: native ROS2 integration is the first of the reasons below.

**Simulator: Gazebo.** This choice is different from common practice, where CARLA is the reference, and it rests on four reasons that Appendix C.1.1 develops one by one: native ROS2 integration, which keeps the whole system in a single graph and makes the latency metrics trustworthy; reuse of an environment the author had already built, consistent with a *design science* approach in which the tool is not the contribution; an existing training interface that keeps algorithm, environment and system cleanly separated and so makes A1 easier; and modest computing requirements, which matter for an individual thesis without dedicated infrastructure.

The choice has two downsides that need to be stated. Gazebo's visual quality is lower than that of photorealistic engines, and for a camera-based policy this can mean a larger sim-to-real gap. Adaptation A5 exists to make this effect visible and to measure it, not to hide it. Also, most of the autonomous driving community uses CARLA, so there are no ready-made scenario libraries for Gazebo, and this project has to build its own.

The rejected alternatives (CARLA, Highway-Env, LGSVL and AirSim) are argued in Appendix C.1.1 as well.

## 3.7 How the framework itself is evaluated

This section asks whether the methodology helped to build the system, not whether the system turned out to be useful. These are two different questions: a good framework can be applied to a modest system, and the other way round. The evaluation uses five criteria, each with an indicator that can be measured at the end:

1. **Traceability integrity.** Indicator: orphans found by the checker in the last run. Success: zero.
2. **Requirement coverage by evidence.** Indicator: percentage of requirements with a verdict supported by quantitative evidence. Success: 100 % have a verdict, even if it is negative or partial. An uncomfortable verdict is better than a missing one.
3. **Hazard anticipation.** Indicator: how many of the hazards that actually appeared were predicted, compared with those that were not. Success: most observed hazards were predicted, and the unexpected ones can be audited and categorised.
4. **Adoption cost.** Indicator: time spent on framework artefacts compared with purely technical artefacts. Success: the cost is in proportion to the benefit observed.
5. **Usefulness of the matrix.** Indicator: technical changes where the matrix made the impact analysis faster. Success: documented cases where it clearly added value.

The evaluation has three stated limits. It is internal to one project and has no control group, so conclusions are based on plausibility and not on controlled experiments. The author bias is limited but not removed. And the experimental period is short, while the benefits of A3 would show up over much longer periods.

## 3.8 Relation to the standards

The framework does not replace the standards. It connects them. Each adaptation has a clear anchor in the standards, summarised in Table 3.4. The full clause-by-clause mapping is in Appendix C.

| Adaptation | Main anchor in the standards |
| --- | --- |
| A1 — Cage Spec + Training Spec | TR 5469 §7 (three-stage realisation principle); PAS 8800 (adapting the module design) |
| A2 — Cage tests + behavioural evaluation | TR 5469 (Class I / Class II elements); ISO 26262 Part 6 for the classical part |
| A3 — Runtime monitoring | SOTIF (static validation is not enough); operation phase as described by Wang et al. (2024) |
| A4 — Hard traceability | ISO 26262 Part 8 (requirements management); AMLAS (GSN patterns); UL 4600 (claim–argument–evidence) |
| A5 — Bounded validation + gap | SOTIF (unexpected conditions); UL 4600 (stated limits of the safety case) |

*Table 3.4 — Anchors in the standards for the five adaptations.*

A note on the hazard analysis: the HARA used here is simpler than the one ISO 26262 prescribes. It is not done alongside the V but inside it, in exactly the place where the standard puts the output of the formal HARA. Chapter 4 describes the simplifications and why they were made.

## 3.9 Limitations of the methodology

The limitations of the *work* are in §1.6.2. The three that affect the *methodology* itself, rather than the case that tests it, are these:

- **Construct validity is limited by having one case.** Generalisation relies on structure, not on evidence from several cases. Mitigation: Chapter 12 separates the parts that can be reused from those that need to be rethought.
- **The simulation has only moderate visual quality.** All training happens in Gazebo, which can make the gap larger for the visual features the camera sees. Mitigation: A5 makes the gap visible and Chapter 9 measures it. Repeating the experiment on a photorealistic simulator is a natural next step.
- **The five adaptations are not a complete list.** Others could be justified, for example a level for data engineering, following the data-centred approach of TR 5469 and AMLAS. Each one is justified, but there is no argument that they are the only possible ones.

## 3.10 Next steps

With the framework defined, the next chapters apply it. Chapter 4 covers the upper left branch of the V (operational domain, hazard analysis and requirement derivation) and produces the first artefacts that A4 checks as a hard constraint. After that, each chapter covers one level of the V and closes its link with the matching level on the right branch.
