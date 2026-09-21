# Chapter 1 — Introduction

## 1.1 Context and motivation

In about ten years, autonomous driving has gone from lab demos to something that is partly on the market. Most manufacturers already sell advanced driver-assistance systems (ADAS) at SAE level 2 and are working towards levels 3 and 4, and the first level 4 systems already exist. Two trends have grown at the same time. The first is the use of machine learning in perception, decision and control modules that are critical for safety: deep networks, which Kuutti et al. (2021a) review for vehicle control, and more recently policies trained with reinforcement learning. The second is that the rules for functional safety have become stricter.

<img src="../figures/fig_1_1_sae_automation_levels.png" alt="Figure 1.1 — SAE levels of driving automation." width="400"/>

*Figure 1.1 — SAE levels of driving automation.*

Each trend makes sense on its own, but together they cause a problem. The classical frameworks, led by ISO 26262:2018, were made for systems whose behaviour can be derived from a specification written beforehand, checked with tests that have expected outputs, and validated before deployment. Learned components break all three assumptions. Their behaviour comes out of a stochastic optimisation, there is no clear "correct answer" to compare their output with, and their robustness outside the training data can only be measured empirically. One of the first systematic studies of this problem is Salay, Queiroz and Czarnecki (2017). They found five specific areas where ML affects ISO 26262. These range from new types of hazard to the finding that about 40 % of the Part 6 software techniques at unit level do not apply to ML components at all. That paper is the direct starting point of this work. Research and industry have responded with two partial strategies. One is containment, with monitor-actuator architectures or *safety cages* (Kuutti et al., 2019, 2021b). The other is scenario-based validation (De Gelder et al., 2024). How to combine both inside a development cycle with traceability is still an open question.

The standards are also still catching up. Since 2022, ISO 21448 (SOTIF) accepts that static validation is not enough when the operational domain cannot be fully specified. ISO/IEC TR 5469:2024 gives the first systematic guidance on AI in safety functions and classifies AI technology elements by how well they can be verified. UL 4600 makes the *safety case* the main way to present evidence (Koopman, 2023). All three are high-level guides. They give principles, but they do not describe a concrete life cycle that someone can run on a real project. This thesis works in that gap.

## 1.2 Problem statement

**General level.** The standard functional safety methods of the automotive industry, especially the V-Model used by ISO 26262, cannot be used as they are for systems that include components trained with reinforcement learning. If they are used without changes, one of two things happens. Either the RL component is forced into a specification it cannot meet, and the process stops being honest about what the system does. Or the component is left out of the process, and traceability is lost. Neither option is acceptable for a system with safety consequences.

**Specific level.** The literature proposes several separate fixes: safety cages to contain policies (Kuutti et al., 2019, 2021b), predictive safety filters (Tearle et al., 2021) and scenario-based evaluation (De Gelder et al., 2024). Each one deals with part of the problem, but they are not combined into one life cycle with explicit traceability in both directions. Some work does look at the whole cycle, mainly Ullrich et al. (2025), who extend the classical V-Model for AI systems, and earlier work on adapting ISO 26262 to ML (Salay et al., 2017; Vasudevan et al., 2021). These proposals stay abstract. They do not provide an executable version or a complete, documented application case. This thesis builds an executable version of that kind of framework and tests it by applying it to a real case.

**Concrete level.** To evaluate such a framework, it has to be applied to a case with two properties. The case must be complex enough to show the typical problems, which are specifying learned behaviour, the sim-to-real gap and monitoring during operation. It must also be small enough for one researcher to handle. The case chosen here is lane following on a 1:14 scale vehicle, trained in Gazebo with PPO through a gymnasium–Gazebo–ROS2 interface. In the main version, the *policy* is end-to-end from the front camera: a CNN learns perception and maps the image to an action. The deterministic cage does not use the network. It uses its own vision-based lane estimator. This puts perception inside the loop on purpose, because that is the harder case. A second version uses a privileged state vector and serves as a control arm. It isolates the effect of the cage and shows how much perception costs.

The main research question is:

> **Can the ISO 26262 V-Model be adapted with a small, traceable set of changes so that it can include components trained with reinforcement learning inside a development cycle with a safety case, while keeping the two-way link between specification and V&V that makes the standard valuable?**

A second question checks whether the framework works in practice:

> **When the framework is applied to a lane-following case with a PPO policy and a rule-based cage, does it produce consistent and traceable evidence about how the system behaves, including an honest description of the sim-to-real gap?**

## 1.3 Hypotheses

- **H1 (construct).** A small, countable set of changes to the classical V-Model (five in this work) is enough to cover the typical failure modes of RL/AI components without breaking the overall structure of the standard.
- **H2 (operability).** Each change can be turned into concrete artefacts, such as documents, tests and automatic checkers. These can be produced and maintained with an effort in line with the rest of the project, rather than as a large extra cost.
- **H3 (usefulness).** When the framework is applied to the case study, it produces traceable evidence that supports a well-founded verdict on the behaviour of the system, including the limits of that verdict.

The three hypotheses are evaluated at the end of the work (Chapter 11). H1 is checked by looking at the structure of the framework, H2 by the adoption cost recorded in the decision log during the project, and H3 by how many Safety Requirements received a verdict.

## 1.4 Objectives

### 1.4.1 General objective

To design, implement and evaluate a methodological framework, the *adapted V-Model*, for developing autonomous driving systems that include components trained with reinforcement learning. The framework brings together safety cages, scenario-based validation, runtime monitoring and two-way traceability in a single cycle, and stays consistent with ISO 26262, ISO 21448, ISO/IEC TR 5469 and UL 4600.

### 1.4.2 Specific objectives

- **SO1.** To describe precisely which hidden assumptions of the classical V-Model stop working when a component trained with reinforcement learning is added to a safety module. *(§3.3.)*
- **SO2.** To propose and justify a limited set of changes that address those assumptions and stay consistent with the standards. *(§3.4.)*
- **SO3.** To turn each change into concrete artefacts (specifications, tests, checkers, metrics) and to define how they are produced. *(§3.5; chapters 4–8 carry it out.)*
- **SO4.** To apply the framework to the case study, both in the main camera version and in the state-vector version used as a baseline, until the system works, can be evaluated and has complete traceability. *(Chapters 4–8.)*
- **SO5.** To measure the gap between the training environment and the real operating environment, as required by adaptation A5. *(Chapter 9.)*
- **SO6.** To give a well-founded verdict on whether the Safety Requirements are met, and to state clearly where that verdict stops being valid. *(Chapter 10.)*
- **SO7.** To evaluate the framework itself: what it costs to adopt, what it covers, and under which criteria it is enough or not enough. *(Chapter 11.)*

## 1.5 Contributions

The main contribution is a method, not a technical result. The lane-following system is not an important contribution by itself, since better trained versions exist on more capable vehicles. What this thesis adds is the framework behind the system and the documented evidence of how it was applied.

The thesis claims five contributions, C1–C5. They are different from the five *adaptations* A1–A5 that make up the framework and are defined in §3.4. The adaptations are the content of the framework. The contributions are what this work adds to the state of the art. In this chapter and in all later chapters, A1–A5 always means the adaptations.

- **C1 — A single methodological framework.** An adapted V-Model with five explicit changes (A1–A5): module design is split into *Cage Specification* and *Training Specification*; unit testing is split into *Cage Unit Tests* and *Policy Behavioral Evaluation*; a runtime monitoring level is added as continuous validation; two-way traceability becomes a hard requirement; and operational validation is redefined so that it includes an explicit description of the sim-to-real gap.
- **C2 — An executable version.** Each change comes with the artefacts that implement it, including reusable templates and automatic checkers. The most important one is the traceability checker, which turns traceability into a gate that a script can pass or fail.
- **C3 — A complete, reproducible case study.** The framework is applied to a system built from scratch, in two versions whose comparison shows the cost of camera perception. Artefacts, training and evaluation scripts are versioned, and the run data is published.
- **C4 — Measurement of the sim-to-real gap.**  Gazebo (reference campaign) → the physical platform. The second step ends as a bring-up and not as a results campaign. Chapters 9 and 10 say this openly instead of hiding it.
- **C5 — Self-evaluation of the framework:** what it cost to adopt, where it worked as expected and where it showed its limits, so that others can improve it later.

## 1.6 Scope and limitations

### 1.6.1 Scope

The framework is applied to one system (lane following with PPO and a cage) on one platform (a 1:14 RC vehicle on a controlled track). There is no comparison with a similar system developed with the classical V-Model. The function is lane following on a closed track with controlled lighting and weather. Planning, interaction with other vehicles and driving on public roads are not covered. In terms of SAE levels, the system is a level 2 function. Levels 4–5 are out of scope.

### 1.6.2 Known limitations

- **Author bias.** The same person designs, builds and evaluates the framework, so there is a risk of confirmation bias. This is partly reduced by strict traceability that others can audit and by a dated decision log.
- **N = 1.** One case is not enough to draw general conclusions about the framework. The argument for generalisation is *structural*: the adaptations target assumptions that fail in any system with a learned component. It is not a statistical argument.
- **Adoption cost without comparison.** The effort spent on the framework's artefacts is recorded, but there is no control group.
- **The adaptations are not a complete list.** The five chosen here are the ones the author considers most relevant for this case. Others could also be justified.
- **Scale platform.** The findings on the sim-to-real gap apply to a 1:14 vehicle on a controlled track.
- **The physical step ends as a bring-up.** The deployment chain runs on the real vehicle and gives calibration results and structural findings, but no scenario has been scored on hardware and the cage has never changed an action there. Hence the physical column of the verdict table is marked *not executed* (§10.4d–e) and every driving figure in Chapter 9 is preliminary. This is a limit of the evidence, not of the framework.

These limitations are discussed further in §3.9 and in Chapter 11.

### 1.6.3 Intended simplifications of the case study

The case study also contains technical simplifications. They were not chosen for convenience. They are experimental controls: each one fixes one layer of the system so that the layer this thesis studies can be looked at on its own. The system can be seen as a stack:

> `perception → state (ey, epsi, v, κ) → [ policy + cage ] → actuation → dynamics`

The contribution is in the `[policy + cage]` block, and in both tracks the cage rules are written over the abstract state. There are three simplifications.

**Two observation tracks.** The main system is the camera track. The policy drives from the image, and the cage reads its own deterministic CV estimator, so perception is a central part of the work. Next to it, the state track gets `(ey, epsi, v)` by projecting the true pose onto the centre line. This fixes the perception layer, which makes it possible to isolate the effect of the cage and to measure the cost of perception as the difference between the two tracks. The cage does not care where the state comes from. The safety verdicts are always measured on the true pose, because leaving the lane is a physical fact and not an estimator error.

**Speed authority of the policy.** The work uses two contracts. For most of the project, the learned component only controls steering and the speed stays constant. This reduces the problem to lateral control and keeps the rule "the reward guides, the cage guarantees". In the final reference campaign the action includes both steering and throttle, so the policy also controls speed. Chapter 8 shows that this changes the role of the cage in a way that can be measured.

**Two track layouts, one platform.** The state track is validated on an oval (R = 0.8 m) and the camera track on the `complex_b` circuit, which is winding and comes close to itself (perimeter 19.22 m). Both use the 1:14 vehicle. The argument for other layouts is structural, supported by the second layout, and not based on exhaustive evidence.

These limits do not weaken the main claim, which is that the cage adds measurable and traceable safety to a learned component. They make it *clean*. Because the neighbouring layers are fixed, the effect of the cage can be attributed clearly, without being hidden by perception noise or by the transfer to hardware. Each limit is discussed again in its experimental context in §8.2 and §8.8.

## 1.7 Structure of the document

The thesis has twelve chapters grouped into four parts, each opened by a divider page and shown in Figure 1.2. Part I — Framework contains this introduction, the state of the art (Chapter 2) and the methodology (Chapter 3), which is the main academic contribution. Part II — Specification covers the operational domain, the hazard analysis and the derivation of requirements (Chapter 4), and the architecture with the cage specification (Chapter 5). Part III — Implementation and evaluation covers implementation and verification (Chapter 6), the training specification and its execution (Chapter 7), the experimental evaluation campaign (Chapter 8), and the measurement of the sim-to-real gap in steps of increasing realism (Chapter 9). Part IV — Closure presents operational validation and the full verdict table (Chapter 10), a discussion of the framework against its own criteria (Chapter 11), and the conclusions and future work (Chapter 12).

<img src="../figures/fig_1_2_document_roadmap.png" alt="Figure 1.2 — Reading map of the document." width="620"/>

*Figure 1.2 — Reading map of the document: the four parts, the twelve chapters, what each chapter produces, and which level of the adapted V-Model it belongs to. The formal mapping between levels and artefacts is not repeated here. It is given in Table 3.3, after the framework has been defined.*

The appendices contain the supporting material, so that the main text can stay readable: the extended hazard register (A), the requirements specification with its rationale (B), the choice of instruments and the mapping to the standards (C), the operational domain specification (D), the cage parameters (E), the traceability matrix (F), the full positioning space (G), the details of the training specification (H) and the scenario-by-scenario results of the reference campaign (I).
