# Appendix C — Instrument choices and normative mapping

This appendix gives the full version of §3.6 and §3.8. Each choice comes with its justification, the alternatives that were rejected and why, so that the decision can be audited and is not just stated.

# C.1 Instruments

This section covers the tools used to apply the methodological framework to the case study. The aim is not to list tools, but to justify each choice against the rejected alternatives and leave an auditable record of decisions that would otherwise stay unexplained. Every subsection follows the same pattern: tool chosen, justification, and rejected alternatives with the reason.

## C.1.1 Simulator

**Choice: Gazebo** (Koenig and Howard, 2004), in its modern version with native ROS2 integration, used through a gymnasium-Gazebo-ROS2 interface that reuses an environment the author built in earlier research work. There are four reasons, and they should be stated clearly, because the choice is different from common practice in autonomous driving research, where CARLA is the reference simulator.

First, *native ROS2 integration*. Open Robotics develops Gazebo together with ROS, and the two share basic building blocks (topics, transforms, visualisation tools) with no need for bridge layers in between. The whole project architecture described in Chapter 5 (perception, policy, cage, actuation, logger) is ROS2 by design. Running the simulator in the same graph removes possible failure points and makes it clearer where delays or desynchronisation happen, which directly affects how reliable the integration metrics (M-I) are.

Second, *reuse of the author's earlier work*. The author already had a Gazebo environment built for a similar task, with the scale vehicle modelled and the controlled track set up. Reusing it, instead of rebuilding it from scratch on another platform, leaves more project time for the methodological contribution (the adaptations A1–A5 and how they are put into practice), which is the real subject of the thesis. This fits the *design science* approach of §3.2.1: the contribution is in the framework, not in the simulator, and the choice of tool should keep costs that add nothing to a minimum.

Third, *a gymnasium-Gazebo-ROS2 interface for training*. The interface that connects the training loop (Stable-Baselines3 on gymnasium) with the simulator (Gazebo, through ROS2) is available as open tooling and keeps algorithm, environment and system cleanly separated. This makes it easier to meet adaptation A1 (Training Specification as meta-design): the hyperparameters, the reward function and the training ODD are defined in a separate Python module that does not depend on the simulator underneath.

Fourth, *lower computing requirements*. Gazebo runs on less powerful hardware than CARLA. This matters for an individual thesis without dedicated computing infrastructure, and it allows faster iteration while the Training Spec is being developed.

The choice has two downsides that should be admitted openly. First, Gazebo's visual quality is lower than that of the Unreal Engine behind CARLA. For a policy based on a single camera, this can lead to a larger sim-to-real gap than a photorealistic simulator would show. Adaptation A5 of the framework (empirical measurement of the gap) is designed exactly to make this effect visible and measure it, not to hide it (see §3.9 and Chapter 9). Second, most of the autonomous driving research community uses CARLA, so there are no ready-made scenario libraries in Gazebo format. The project's scenario library therefore has to be built from scratch, which is part of the scope of Chapter 6.

Alternatives considered and rejected. CARLA (Dosovitskiy et al., 2017) is the strongest option and the default choice in recent autonomous driving research. It offers better sensor quality and a mature benchmark ecosystem, but it needs a ROS2 *bridge* that brings its own problems, and its higher computing cost is a practical obstacle for an individual thesis. Highway-Env and other Gym-based environments have no realistic sensors and use an abstract observation space, so they are not suitable for camera-based policies. LGSVL is a project that was discontinued in 2022, with an ecosystem that is falling apart. **AirSim** focuses on aerial vehicles, with car support as a secondary feature, and its development is on hold.

## C.1.2 Reinforcement-learning algorithm

**Choice: PPO**, *Proximal Policy Optimization* (Schulman et al., 2017). PPO is chosen for four reasons that fit the methodological framework. First, *stable training*: the *clipped surrogate objective* limits the size of each policy update without an explicit KL constraint. This supports stable training and reproducibility, which matters for individual work with little compute for full *sweeps*. Second, *a Training Spec that is easy to interpret*: because PPO is *on-policy*, its hyperparameters have a fairly direct meaning (rollout size, epochs per update, clipping ratio, entropy coefficient), which makes it easier to write the Training Spec of level L4b as a readable document. Third, *good support in open tools*: the Stable-Baselines3 implementation is mature, widely used, and integrates directly with Gazebo through the gymnasium-Gazebo-ROS2 interface mentioned in §3.6. Fourth, *compatibility with extensions*: if the thesis later explored *constrained RL* (like RECPO by Zhao et al., 2024), PPO can be extended naturally to CMDP.

Alternatives considered and rejected: SAC (Haarnoja et al., 2018) is competitive in sample efficiency and stable across random seeds, but being *off-policy* makes the Training Spec harder to interpret (the idea of "which policy produced which experience" gets lost in the *replay buffer*), and its stochastic nature with *temperature tuning* makes the experiment design more complex. DDPG / TD3 (deterministic and *off-policy*) were outperformed by SAC on the harder benchmark tasks of Haarnoja et al. (2018), where DDPG is also described as sensitive to hyperparameters. A3C / A2C were less sample-efficient than PPO in the benchmarks of Schulman et al. (2017).

## C.1.3 Learning loop and implementation tools

- **Stable-Baselines3** as the PPO implementation. Reason: stability, community, integration with *gym* / *gymnasium*, and auditable code.
- **PyTorch** as the neural network backend. Reason: it is the standard in current research, integrates natively with Stable-Baselines3 and has mature profiling tools.
- **pytest** as the testing framework for the Cage Unit Tests (L4a' of the adapted V-Model) and for the general regression suite.
- **Python 3.10+** with quality tools: `ruff` (linting), `mypy` (type checking) and `pre-commit` to automate checks on every commit.

## C.1.4 Physical platform

The 1:14 scale radio-controlled vehicle is chosen over other scales for three reasons. *Cost*: a 1:14 vehicle is easy to handle, parts are cheap and the risk of damage during use is limited. *Operational safety*: low speeds, low kinetic energy and a negligible risk to other people on a closed track. *Transferability from simulation*: the dynamics of a 1:14 vehicle can be approximated reasonably well in Gazebo with a plugin-based vehicle model and adjustable parameters (mass, load distribution, tyre friction, actuation parameters), while larger scales (1:5, 1:1) would add dynamic differences that would dominate the sim-to-real gap. The detailed specifications of the car (motor, ESC, low-level controller, camera, onboard computing platform) are in Chapter 5 and in the corresponding appendix.

<img src="../figures/fig_3_5_vehicle_cad.png" alt="Figure 3.5 — Photograph of the 1:14 RC vehicle instrumented with the camera and IMU." width="300"/>

*Figure 3.5 — The 1:14 RC vehicle instrumented with camera, IMU, encoder and SBC, with each component labelled.*

## C.1.5 Measurement instrumentation

The main tool for collecting evidence is the Logger Node of the ROS2 architecture, already described in adaptation A3 (§3.4.3). The Logger Node records everything relevant that passes through the bus (observations, *policy* actions, cage decisions, interventions, vehicle states) with timestamps, so that it can be reconstructed later.

The concrete metrics calculated from the logs are formally defined in Chapter 4 and grouped into five families: M-P (performance: tracking error, trajectory completeness), M-S (safety: cage intervention rate, number of violations per SR), M-I (integration: latencies, jitter, throughput), M-C (behaviour: lateral stability, control smoothness) and M-T (transfer: difference between simulation and reality for each of the previous metrics, and metrics specific to the A5 gap). The details are in Chapter 4.

For additional quantitative evaluation on the *scenario library*, the composite QED metric (Gao et al., 2021) is taken as inspiration. It is a composite metric calibrated against human raters for autonomous driving tasks. It cannot be adopted as it is, because QED was developed and calibrated on CARLA and this thesis uses Gazebo. The formula can be transferred, but the calibrated weights would have to be recalculated for the lane-following scenario in Gazebo to get a metric with the same meaning. *Behavior Metrics* (Paniego et al., 2024) is considered as a helper tool for quantitative evaluation, since it already works with two simulators, CARLA and Gazebo. The decision to adopt it as the project's official metric is postponed to Phase 4, when the trained *policy* is available and it can be calibrated against the author's own judgement.

## C.1.6 Documentation, version control and reproducibility

All project artefacts (documents, code, templates, traceability matrix, validation scripts) live in a single Git repository, based on one idea: the repository *is* the project. The deliberate choice is *plain text first*: artefacts are written in Markdown with minimal extensions (citations in the format `[Surname (year)]`, LaTeX equations, SVG/PNG figures in their own folder), not in industrial MBSE tools such as Cameo or Capella.

This choice differs from the MBSE proposal of Sprockhoff et al. (2023) for systems with AI components, which argues for SysML and structured tools as the backbone of the life cycle. The difference is about *adoption cost*: for an individual thesis without industrial licences, version-controlled text files give better value for money, and they do the same job for traceability (with `traceability_matrix.csv` + `check_traceability.py`) and consistency (with automated review on every commit). The decision is recorded in `DECISIONS.md` with its justification and with the assumption that applying the framework in a medium-sized industrial team would make a move to MBSE worthwhile.

---

# C.2 Relation to the standards

The adapted V-Model builds on the current state of the standards for AI system safety. This section places each adaptation within that landscape and separates what is consistent with each standard from what goes further. The review follows the order of publication, which roughly matches the order in which industry adopted them.

## C.2.1 ISO 26262:2018 — Functional Safety for Road Vehicles

ISO 26262:2018 applies the classical V-Model to the automotive industry. The thesis takes it as its starting point and as a framework whose general structure it aims to keep.

- **Consistent:** the five-level structure L1–L5, the idea of a safety requirement, the principle of a two-way link between specification and V&V, and the derivation of requirements from the HARA with assignment of ASIL levels.
- **Goes further:** ISO 26262 does not consider learned modules. Adaptations A1, A2 and A3 are explicit extensions that bring in RL components without breaking the general structure of the standard. The approach is additive *tailoring*: nothing is removed, and only what is strictly needed is added.

## C.2.2 ISO 21448:2022 — SOTIF (Safety Of The Intended Functionality)

ISO 21448:2022 extends safety beyond faults, including the use of functions under unexpected conditions. It is the official response to the fact that systems with ML-based perception and decision making can behave wrongly without any component having "failed" in the classical sense (Wang et al., 2024).

- **Consistent:** adaptation A5 (bounded operational validation and measurement of the sim-to-real gap) matches directly the SOTIF idea that static validation is not enough when the ODD is not fully specified. Adaptation A3 (continuous runtime monitoring) matches the SOTIF principle of managing *triggering conditions* found during operation.
- **Goes further:** A3 proposes runtime monitoring as an explicit architectural level of the life cycle, not only as a recommended practice during operation.

## C.2.3 ISO/IEC TR 5469:2024 — AI Functional Safety

ISO/IEC TR 5469:2024 is so far the most specific standards document on the use of AI in safety functions. It contributes three things to the proposed framework: the classification of AI technology by usage level and by technology class (Class I, II and III; clause 6), the *three-stage realization principle* (clause 7), and the properties and risk factors of AI systems (clause 8: level of automation and control, transparency and explainability, complexity of the environment and vague specifications, resilience to adversarial inputs, AI hardware, and maturity of the technology).

- **Consistent:** the thesis's PPO *policy* is at best a Class II element of TR 5469 (existing functional safety standards only cover part of its required properties, and complementary methods are needed), and adaptation A2 (statistical Policy Behavioral Evaluation) is one of those complementary methods. Required two-way traceability (A4) has no direct counterpart among the TR's properties; its anchor in the standards is argued in C.2.5 and C.2.6. The split into Cage Spec / Training Spec (A1) takes the distinction made by the *three-stage realization principle* between data acquisition, knowledge induction and processing, and applies it to the design process, which the TR itself does not present as a life cycle.
- **Goes further:** explicitly separating the Cage Spec (a conventional element that, by analogy, matches Class I) and the Training Spec (meta-design for a Class II element) into separate version-controlled documents is a practical refinement of the TR, which the standard does not detail at that level.

## C.2.4 ISO/PAS 8800:2024 — Road Vehicles, Safety and AI

ISO/PAS 8800:2024 is the automotive document on safety and AI, closely linked to the general concepts of TR 5469. It extends ISO 26262 and ISO 21448 to AI elements: functional safety risks are handled by *tailoring* the relevant clauses of ISO 26262 (Parts 4, 6 and 8), and functional insufficiencies by extending the SOTIF concepts. An example use case published by BSI for the UK CCAV (Hawkins, 2025), on an ML traffic-sign detector with stop-sign requirements, shows how ISO 26262, SOTIF and ISO/PAS 8800 are combined on an ML component.

- **Consistent:** the additive *tailoring* of the adapted V-Model matches that of ISO/PAS 8800. The five adaptations A1–A5 can reasonably be aligned with the areas the standard identifies as critical (definition of the operating environment, systematic analysis of insufficiencies, monitoring after deployment).
- **Goes further:** applying the framework to a complete case, from HARA to physical deployment and with an empirical measurement of the gap, is more concrete than the examples published so far.

## C.2.5 UL 4600 — Standard for Safety for the Evaluation of Autonomous Products

UL 4600 (UL Standards, 2023; Koopman, 2023) focuses on the *safety case* and on structured evidence as the main way to provide assurance for autonomous products.

- **Consistent:** the Traceability Matrix H↔SR↔C↔SC↔M is a small safety case in the spirit of UL 4600: every safety *claim* is backed by an explicit argument (the cage rule, the scenario, the metric) and by traceable evidence (the logs, the experimental results).
- **Goes further:** A4 turns traceability into a hard constraint enforced by an automated tool (`check_traceability.py`), instead of a documentation practice that someone has to review.

## C.2.6 AMLAS — Assurance of Machine Learning for Autonomous Systems

AMLAS, consolidated by Paterson et al. (2025), is not a formal standard but a method with GSN (*Goal Structuring Notation*) patterns for building safety arguments about ML components. It is being used as input to new standards, in particular ISO/PAS 8800.

- **Consistent:** the claim-argument-evidence approach of AMLAS matches the two-way traceability proposed as A4. The data-centred life cycle that AMLAS sets out (requirements definition, data management, learning, verification, deployment, monitoring) broadly matches the project phases described in §3.5.3.
- **Goes further:** AMLAS has mostly been tested on supervised models. The framework in this thesis is designed explicitly for RL *policies*, an area that AMLAS still covers poorly.

## C.2.7 The simplified HARA and how it relates to the formal version of the standard

Clause 6 of Part 3 of ISO 26262:2018 defines the formal HARA method for automotive *items*: situation analysis, systematic identification of the hazards linked to the item's functions, classification of each hazard along three axes (severity S, scale S0–S3; exposure E, scale E0–E4; controllability C, scale C0–C3) and derivation of the *ASIL* (Automotive Safety Integrity Level, QM/A/B/C/D) through a table that combines S×E×C. The ASIL sets the level of rigour required for the rest of the life cycle, including design measures, verification techniques and test coverage.

The version used in this thesis is explicitly called a *simplified HARA*, and is labelled that way in the header of the Hazard Register. There are three differences from the formal standard, stated here openly:

- **The S/E/C scales are kept but reinterpreted for a scale vehicle.** The three scales keep the granularity of the standard (S1–S3, E1–E4, C1–C3), but the definitions of each level are adapted to a 1:14 scale vehicle on a closed track. S3 no longer means "fatal injury" but "total loss of the integrity of the platform". E3 is defined as "10–50 % of the operating time" within the declared ODD (a banding specific to this project: in the standard's duration-based exposure classes, E3 corresponds to 1–10 % and E4 to more than 10 % of the average operating time). C2 keeps the meaning of "controllable in > 90 % of the cases", but with respect to the rule-based cage instead of the human driver. This adapted rubric is versioned together with the register and can be audited.

- **No formal ASIL is assigned; a qualitative "Criticality" is used instead.** For each hazard, the simplified HARA produces a qualitative criticality label with four levels (Low, Medium, Medium-High, High), obtained by combining S, E and C qualitatively, and used only to prioritise mitigation work. No ASIL letter is assigned because the ASIL is a legal and normative construct meant for industrial certification, not for the methodological demonstration that the thesis aims at. Giving a scale car an "ASIL B" would suggest a precision that is not there, which the framework prefers to avoid. The qualitative criticality is honest about what is measured and what it is used for. Separately, the Safety Requirements have their own criticality rubric with two classes, SR-CL-A and SR-CL-B, defined in §4.5.3 of Chapter 4 and with different practical consequences (minimum rigour of implementation and verification).

- **An STPA-light analysis is added for selected hazards.** The simplified HARA is complemented by an *STPA-light* analysis applied to high-criticality hazards and limited to the four categories of *unsafe control actions*: action not given when needed, given when it should not be, given with the wrong magnitude, and given at the wrong time. This adds systemic failure modes that a pure HARA, focused on consequences, tends to under-represent. Using STPA is a common methodological borrowing in recent safety practice for systems with AI components, and it is documented as such, not as part of the formal ISO 26262 HARA.

What the simplified HARA *keeps* is what matters most in the method: the systematic listing of hazards based on the analysis of the item, their classification before requirements are derived, two-way traceability between each hazard and the SRs that mitigate it (adaptation A4), and an auditable record of every classification decision. The process structure (situation → hazards → classification → SRs) is the same as in the standard. What changes is the type of final output (qualitative criticality instead of ASIL) and the addition of STPA-light for the hazards with the highest relative severity.

The split of work with ISO 21448 (SOTIF) follows the usual division in industry. The simplified HARA identifies systematic failures of the system, which is the traditional focus of ISO 26262. The *insufficiencies of the intended functionality*, meaning behaviour that is correct according to the specification but hazardous in operation, which is the focus of SOTIF, are covered by adaptation A5 (empirical measurement of the sim-to-real gap) and adaptation A3 (runtime monitoring over intervention logs), not by the HARA. This split is visible in the traceability matrix: the H↔SR links cover the ISO 26262 part of the problem, and the "expected evidence mode" column (test / statistical analysis / runtime) covers the SOTIF part where it applies.

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figure 3.6 — Diagram of the normative pyramid." width="500"/>

*Figure 3.6 — Normative pyramid: ISO 26262 at the base as the life cycle, SOTIF as the complement for unexpected conditions, TR 5469 as the general AI layer, PAS 8800 as the automotive AI extension, UL 4600 as the safety case around everything, and AMLAS as argumentation patterns that apply across all of them. The five adaptations A1–A5 are marked on the pyramid with their scope of application.*

---
