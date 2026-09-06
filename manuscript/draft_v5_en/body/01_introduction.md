# Chapter 1 — Introduction

## 1.1 Context and motivation

In one decade, autonomous driving has moved from a laboratory demonstration to a partial commercial product. Advanced driver-assistance systems (ADAS) are deployed in millions of units, and level 4 projects already operate in restricted fleets (Kootbally et al., 2024). Two trends have consolidated in parallel within this movement: the growing use of machine learning components in critical perception, prediction and decision modules — deep networks (Kuutti et al., 2019a) and, more recently, policies trained by reinforcement learning (García and Fernández, 2015) — and the tightening of the regulatory frameworks for functional safety.

<img src="../figures/fig_1_1_sae_automation_levels.png" alt="Figure 1.1 — SAE levels of driving automation." width="400"/>

*Figure 1.1 — SAE levels of driving automation.*

Both trends are individually sound, and they create a structural tension when they meet. The classical frameworks, with ISO 26262:2018 at the head, were designed for systems whose behaviour can be derived from a specification written in advance, verified through tests with expected outputs, and validated statically before deployment. Learned components break all three assumptions: their behaviour emerges from a stochastic optimisation, their output does not admit the classical notion of a "correct answer", and their robustness outside the training distribution can only be characterised empirically (Wäschle et al., 2022; Paterson et al., 2025). The earliest systematic analysis of this tension is the one by Salay, Queiroz and Czarnecki (2017), which identified five concrete areas of impact on ISO 26262 — from the appearance of new hazard types to the inapplicability of approximately 40 % of the software techniques prescribed in its Part 6 — and which is the direct conceptual antecedent of this work. Industry has answered with two partial strategies: containment through monitor-actuator architectures or *safety cages* (Kuutti et al., 2019b, 2021), and characterisation through scenario-based validation (De Gelder et al., 2024). Their coherent integration inside a traceable development cycle is still an open problem.

On the normative side, the institutional answer is still maturing. Since 2022, ISO 21448 (SOTIF) has recognised that static validation is not sufficient when the operational domain cannot be specified exhaustively (Wang et al., 2024); ISO/IEC TR 5469:2024 offers the first systematic guidance on AI in safety functions, and classifies AI technology elements according to their verifiability; UL 4600 formalises the *safety case* as the central mechanism of evidence (Koopman, 2023). All three are high-level guides: they state principles, but they do not prescribe a concrete, executable life cycle that can be applied to a real project. This thesis is placed exactly in that gap.

## 1.2 Problem statement

**General level.** The canonical functional safety methodologies of the automotive industry — in particular the V-Model adopted by ISO 26262 — cannot be applied without modification to systems that incorporate components trained by reinforcement learning. Applying them unchanged leads to one of two predictable failures: forcing the RL component into a specification that it cannot satisfy, which breaks the honesty of the process; or exempting it from the process, which breaks traceability. Neither is acceptable in a system with safety consequences.

**Specific level.** The individual adaptations proposed in the literature — safety cages to contain policies (Kuutti et al., 2019b, 2021), predictive safety filters (Tearle et al., 2021), scenario-based evaluation (De Gelder et al., 2024) — attack individual facets of the problem, but they are not integrated by default into a unified life cycle with explicit bidirectional traceability. There are proposals that do address the complete cycle, most notably Ullrich et al. (2025) on the expansion of the classical V-Model for systems with AI, and the earlier work on adapting ISO 26262 to ML (Salay et al., 2017; Vasudevan et al., 2021), but they remain on an abstract level, without an executable operationalisation and without a documented end-to-end application case. The space that this thesis occupies is the executable materialisation of a framework of that kind, validated by applying it to a concrete case.

**Concrete level.** For such a framework to be evaluable, it has to be executed on a case that is complex enough to exhibit the characteristic problems — specification of learned behaviour, sim-to-real gap, monitoring in operation — and bounded enough to be manageable by a single researcher. The case chosen here is a lane-following system on a 1:14 scale vehicle, trained in Gazebo with PPO over a gymnasium–Gazebo–ROS2 interface. In its main instantiation the *policy* is end-to-end from the front camera: a CNN that learns perception and maps image to action, with the deterministic cage operating on its own vision-based lane estimator, separate from the network. This deliberately brings perception into the loop, which is the more demanding case. A second instantiation on a privileged state vector is kept as a control arm, which isolates the effect of the cage and quantifies the cost of perception.

The main research question is formulated as follows:

> **Is it possible to adapt the canonical ISO 26262 V-Model through a finite and traceable set of modifications, so that it accommodates components trained by reinforcement learning inside a development cycle with a safety case, without abandoning the principles of bidirectional specification↔V&V correspondence that give the standard its value?**

Subordinate to it, there is a validation question:

> **When the resulting framework is applied to a concrete lane-following case with a PPO policy and a rule-based cage, does it produce coherent and traceable evidence about the behaviour of the system, including an honest characterisation of the sim-to-real gap?**

## 1.3 Hypotheses

- **H1 (construct).** It is possible to identify a small and enumerable set of adaptations to the classical V-Model — here, five — that cover the characteristic failure modes of RL/AI components without breaking the general structure of the standard.
- **H2 (operability).** Each adaptation can be operationalised as a concrete set of artefacts — documents, tests, automatic validators — that can be produced and maintained with an effort proportional to the rest of the project, and not as a prohibitive overhead.
- **H3 (usefulness).** The resulting framework, applied to the case study, produces traceable evidence that allows a well-founded verdict to be issued on the behaviour of the system, including the validity limits of that verdict.

All three are evaluated at the close of the work (Chapter 11): H1 by structural inspection of the framework, H2 by the adoption cost recorded in the decision log along the project, and H3 by the verdict coverage reached over the Safety Requirements.

## 1.4 Objectives

### 1.4.1 General objective

To design, implement and evaluate a methodological framework — the *adapted V-Model* — for the development of autonomous driving systems that incorporate components trained by reinforcement learning, articulating within a single cycle the practices of safety cage, scenario-based validation, runtime monitoring and bidirectional traceability, in coherence with ISO 26262, ISO 21448, ISO/IEC TR 5469 and UL 4600.

### 1.4.2 Specific objectives

- **SO1.** To characterise formally the implicit assumptions of the classical V-Model that fail when a component trained by reinforcement learning is introduced into a safety module. *(§3.3.)*
- **SO2.** To propose and justify a finite set of adaptations that attack those assumptions while keeping coherence with the standards. *(§3.4.)*
- **SO3.** To operationalise each adaptation into concrete artefacts — specifications, tests, validators, metrics — and to define their production flow. *(§3.5; chapters 4–8 as execution.)*
- **SO4.** To apply the framework to the case study, in its main camera instantiation and in the state-vector one used as a baseline, until a functional and evaluable system with complete traceability is obtained. *(Chapters 4–8.)*
- **SO5.** To characterise quantitatively the gap between the training environment and the operational one, fulfilling adaptation A5. *(Chapter 9.)*
- **SO6.** To issue a well-founded verdict on the fulfilment of the Safety Requirements, with an explicit declaration of its validity limits. *(Chapter 10.)*
- **SO7.** To evaluate the framework itself: adoption cost, coverage, and the criteria under which it is considered sufficient or insufficient. *(Chapter 11.)*

## 1.5 Contributions

The main contribution is methodological, not technical. The resulting lane-following system is not by itself a relevant contribution, since better trained variants exist on more capable vehicles. What this thesis contributes is the framework that this system materialises, and the documented evidence of its application.

Five contributions are claimed, labelled C1–C5. They are not the same thing as the five *adaptations* A1–A5 that make up the framework and that are defined in §3.4: the adaptations are the content of the artefact, the contributions are what this work claims to add on top of the state of the art. A1–A5 always denote adaptations, in this chapter and in every chapter that follows.

- **C1 — Unified methodological framework.** An adapted V-Model with five explicit modifications (A1–A5): splitting the module design into *Cage Specification* and *Training Specification*; splitting the unit test into *Cage Unit Tests* and *Policy Behavioral Evaluation*; introducing a runtime monitoring level as continuous validation; bidirectional traceability as a hard constraint; and reformulating the operational validation with an explicit characterisation of the sim-to-real gap.
- **C2 — Executable operationalisation.** Each modification comes with the artefacts that materialise it, with reusable templates and automatic validators, in particular the traceability checker that turns traceability into a mechanical gate constraint.
- **C3 — Complete and reproducible case study.** Application of the framework to a system implemented from scratch, in two instantiations whose contrast isolates the cost of camera perception, with versioned artefacts, training and evaluation scripts, and published run data.
- **C4 — Empirical characterisation of the sim-to-real gap** in steps of increasing fidelity: Gazebo (reference campaign) → a higher-fidelity simulator (Isaac Sim, PhysX + RTX) → physical platform. The third step closes as a bring-up and not as a results campaign, and Chapters 9 and 10 state that limit rather than absorbing it.
- **C5 — Self-evaluation of the framework:** adoption cost, points where it worked as expected and points where it revealed limitations, as evidence for later refinements by third parties.

## 1.6 Scope and limitations

### 1.6.1 Scope

The framework is applied to a single system — lane following with PPO and a cage — on a single platform — a 1:14 RC vehicle on a controlled track — without a comparison against a baseline system developed with the classical V. The target function is lane following on a delimited track with controlled lighting and weather: planning, interaction with other vehicles and operation on public roads are not addressed. Conceptually, the system belongs to the space of SAE level 2 functions; the extension to levels 4–5 is out of scope.

### 1.6.2 Acknowledged limitations

- **Author bias.** The same person designs, implements and evaluates the framework, which introduces confirmation bias. Partial mitigation: strict auditable traceability and a dated decision log.
- **N = 1.** General conclusions about the usefulness of the framework cannot be derived from a single case. Generalisation is argued by *structural plausibility* — the adaptations attack assumptions that fail in any system with a learned component — and not by statistical evidence.
- **Adoption cost not compared.** The effort spent on the artefacts of the framework is documented, but without a control group.
- **Non-exhaustive adaptations.** The five proposed here are the ones the author considers most relevant for this case; others would be defensible.
- **Scale platform.** The findings on the sim-to-real gap are specific to a 1:14 vehicle on a controlled track.
- **The physical step closes as a bring-up.** The deployment chain runs on the real vehicle and produces calibration results and structural findings, but no scenario has been scored on hardware and the cage has never modified an action there. The physical column of the verdict table is therefore declared *not executed* (§10.4) and every driving figure in Chapter 9 is preliminary. This is a limit of the evidence, not of the framework, and it is stated as such wherever it applies.

These limitations are developed in §3.9 and in Chapter 11.

### 1.6.3 Deliberate abstractions of the case study

Beyond the above, the case study incorporates technical abstractions that are not simplifications of convenience but experimental controls: each one fixes one layer of the system so that the layer studied in this thesis can be isolated. The system is understood as a stack:

> `perception → state (ey, epsi, v, κ) → [ policy + cage ] → actuation → dynamics`

The contribution lies in the `[policy + cage]` block, and the cage rules are defined over the abstract state in both tracks. There are three abstractions.

**Two observation tracks.** The main system is the camera track: the policy drives from the image and the cage reads its own deterministic CV estimator, so that perception enters the scope as a central contribution. In parallel, the state track obtains `(ey, epsi, v)` by projecting the true pose onto the centre line, which fixes the perception layer in order to isolate the effect of the cage and to measure its cost (the delta between both tracks). The cage is agnostic to the origin of the state, and the safety verdicts are always measured on the true pose: leaving the lane is a physical fact, not an artefact of the estimator.

**Authority of the policy over speed.** The work goes through two contracts. During most of the project the learned component controls steering only and the speed is kept constant, which reduces the problem to lateral control and preserves the separation "the reward guides, the cage guarantees". The final reference campaign extends the action to steering plus throttle, so that the policy acquires longitudinal authority; Chapter 8 shows that this authority changes the role of the cage in a measurable way.

**Two track geometries and one platform.** The state track is validated on an oval (R = 0.8 m) and the camera track on the `complex_b` circuit, which is winding and self-approaching (perimeter 19.22 m); both use the 1:14 vehicle. Generalisation to other geometries is argued by structural plausibility, reinforced by that second geometry, and not by exhaustive evidence.

These boundaries do not weaken the central claim — that the cage adds measurable and traceable safety to a learned component — they make it *clean*: by fixing the neighbouring layers, the effect of the cage can be attributed without confusion instead of being masked by perception noise or by the transfer to hardware. Each boundary is discussed again, in its experimental context, in §8.2 and §8.8.

## 1.7 Structure of the document

The thesis is organised in twelve chapters grouped in four blocks, summarised in Figure 1.2. Block I — Framework contains this introduction, the state of the art (Chapter 2) and the methodology (Chapter 3), which is the central academic contribution. Block II — Specification covers the operational domain, the hazard analysis and the derivation of requirements (Chapter 4), and the architectural design with the cage specification (Chapter 5). Block III — Implementation and evaluation goes through the implementation and verification (Chapter 6), the training specification and its execution (Chapter 7), the experimental evaluation campaign (Chapter 8) and the characterisation of the sim-to-real gap in steps of increasing fidelity (Chapter 9). Block IV — Closure presents the operational validation and the consolidated verdict table (Chapter 10), the discussion of the framework against its own criteria (Chapter 11), and the conclusions and future work (Chapter 12).

<img src="../figures/fig_1_2_document_roadmap.png" alt="Figure 1.2 — Reading map of the document." width="620"/>

*Figure 1.2 — Reading map of the document: the four blocks, the twelve chapters, what each one leaves behind, and the level of the adapted V-Model that it occupies. The formal correspondence between levels and artefacts is not repeated here — it is given in Table 3.3, once the framework has been defined.*

The appendices collect the evidence material that supports the body without interrupting it: the extended hazard register (A), the requirements specification with its rationale (B), the instrument choices and the normative mapping (C), the operational domain specification (D), the cage parameters (E), the traceability matrix (F), the complete positioning space (G), the detail of the training specification (H) and the scenario-by-scenario breakdown of the reference campaign (I).
