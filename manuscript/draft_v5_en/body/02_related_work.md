# Chapter 2 — State of the art

## 2.1 Purpose and structure of the chapter

This chapter puts the relevant literature into a map and, most importantly, points out the places where lines of work do not connect, which is what this thesis tries to handle together. The review is selective: it focuses on work from the last seven years and on work that has clearly influenced the academic or standards discussion. It goes from general to specific: reinforcement learning in driving (§2.2), groups of safety approaches (§2.3), scenario-based validation (§2.4), standards (§2.5), life cycle adaptations (§2.6) and the sim-to-real gap (§2.7). It ends with a summary that places the thesis in this map (§2.8).

## 2.2 Reinforcement learning in autonomous driving

Machine learning for vehicle control has developed in three waves. The first was behaviour cloning, or *imitation learning*. It showed that a network could map pixels to steering commands, but it broke easily when the vehicle moved away from the states the expert had shown. The second was deep reinforcement learning (DRL), which aimed to fix that problem by letting the agent explore the results of its own decisions (Kuutti et al., 2021a). The third wave is still ongoing. It mixes both approaches and adds world models and explicit safety representations.

<img src="../figures/fig_2_1_classical_rl_framework.png" alt="Figure 2.1 — The classical reinforcement learning framework." width="400"/>

*Figure 2.1 — The classical reinforcement learning framework (Sutton and Barto, 2018). The agent chooses an action `At` in state `St` and receives the reward for it. Its goal is to maximise the total reward over a long sequence of transitions.*

Two algorithms appear in most recent work. PPO (Schulman et al., 2017) trains in a stable way thanks to its clipped loss. This is useful when reproducibility matters and when sensitivity to hyperparameters causes practical problems. SAC (Haarnoja et al., 2018) optimises a maximum-entropy objective that encourages exploration and robustness, and because it is *off-policy* it needs fewer samples. This work uses both, and Chapter 7 compares them in experiments.

For lane following specifically, Cheng et al. (2025) show on a small physical platform (Duckiebot) that camera-based DRL policies trained in simulation can keep the lane on a real track. For the harder navigation task, however, domain randomization alone does not transfer, and what makes it work is image style transfer with CycleGAN. Zhao et al. (2024) look at decision making on highways with constrained CMDP-type policies and a *replay buffer*. The trend is clear. For short decision horizons and limited domains, DRL gives good results. For long horizons and open domains, the community agrees that DRL alone is not enough without extra guarantees.

End-to-end driving from vision has its own history, and the main track of this thesis builds on it. ALVINN (Pomerleau, 1989) used a very small network on 30×32 pixels. DAVE-2 (Bojarski et al., 2016), later called PilotNet, scaled the idea to real roads with behaviour cloning. Kendall et al. (2019) then used DRL to train lane following from a single camera image on a real vehicle. At the same time, domain randomization, both visual (Tobin et al., 2017) and dynamic (Peng et al., 2018), became the usual way to make learned perception less fragile. The argument against end-to-end learning is just as old and is about sample complexity. Shalev-Shwartz and Shashua (2016) show that splitting the problem through a semantic abstraction needs far fewer examples than a network that must learn the same function end to end. This supports keeping any component that needs a safety argument, here the envelope, outside the network. This thesis follows that line, but its contribution is not the end-to-end driver. It is the safety tooling around it. The runtime envelope does not use the learned network. It works on a classical, deterministic lane estimator that uses a different algorithm. Visual degradation also becomes something that scenarios control and evaluate, and not only noise added during training.

All of this work shares the same basic problem: the behaviour of the policy cannot be derived from a specification written beforehand. That breaks the main assumption of the classical functional safety frameworks.

## 2.3 Safety approaches for systems with learned components

The literature can be grouped into four families. Each one looks at the problem from a different point in the life cycle.

**(a) Safe RL: safety inside training.** The classical taxonomy comes from García and Fernández (2015). It has two axes: changing the optimisation criterion and changing the exploration process. Recent work adds explicit safety information to the state space or the value function. The SRPL framework (Mani et al., 2025) adds to the state a learned model that predicts future constraint violations. Keswani and Bhattacharyya (2025) test it on real driving datasets and report statistically significant gains in success rate and cost compared with the same safe RL optimisers without it. They also say that these gains depend on the optimiser and on the dataset. The idea is elegant, but it has the same basic limit as the whole family: the guarantee is statistical, it depends on the training distribution, and it does not carry over automatically to a different operational domain.

**(b) Safety cages and runtime filters.** This family complements the first one. It works at inference time and treats the policy as a black box whose outputs need to be filtered. Kuutti et al. (2019) take the *safety cage*, an idea already proposed for autonomous vehicles in earlier work, and apply it to a controller based on a deep network. The cage is a deterministic module that watches the network's outputs and replaces them with a safer action when the proposed behaviour would go past its limits. Since its rules are easy to interpret, classical functional safety validation methods can be used on it. The same paper already uses the interventions to retrain the network. Kuutti et al. (2021b) then put the cages inside reinforcement learning training, where they play two roles: containment and weak supervision of the agent. In that setup the cage does not only contain the agent but also *shapes* how it behaves. This double role shows up again, without being planned, in the findings of Chapter 8.

<img src="../figures/fig_2_2_safety_cage_idea.png" alt="Figure 2.2 — The safety cage applied to the classical RL framework." width="400"/>

*Figure 2.2 — The safety cage applied to the classical reinforcement learning framework.*

A related line proposes *predictive safety filters* based on model predictive control. Instead of checking each action on its own, the filter predicts what the proposed action will lead to. If a safe backup trajectory into the safe set still exists, the action is applied. If not, it is replaced by the closest input that keeps such a trajectory (Tearle et al., 2021). The strength of this approach is its formal clarity. Its practical weakness is that it needs a fairly accurate dynamic model, which is hard to get with noisy perception. The architecture goes back to the Simplex pattern (Sha, 2001), where a complex controller is supervised by a simple, verified one, and to the related formal method of *shielding* (Alshiekh et al., 2018). A shield intervenes as little as possible: it only overrides an action when that action would break the safety specification. The cage in this thesis is a Simplex instance with deterministic rules. It sits between the cage of Kuutti et al., from which it takes verifiable containment, and the formal *shield*, whose idea of minimal intervention it copies in its rate-limiting rule.

**(c) Robustness against perturbations.** He et al. (2024) test a Q-learning controller on TORCS against two threat models, with a result that matters for method: perturbations on the sensors have almost no effect (attack success rate close to zero, because the action space is discrete), while directly changing the action works between 60 % and 78 % of the time. Discretisation gives *accidental* robustness on one channel and leaves the other one open. Wei et al. (2026) attack the same problem from the defence side: they focus observation perturbations on a few safety-critical moments with a limited budget and train with a dual *replay buffer* of normal and adversarial experience. The lesson is direct: testing a policy must include how it reacts to inputs and outputs outside the normal distribution, and the cage must be designed on the assumption that both the policy and its interfaces can fail.

**(d) Runtime monitoring.** This family cuts across the other three and is about detecting errors while the system is running. Mohseni et al. (2019) organise the field around five gaps that ML opens in the classical standards: specification, transparency, verification, performance and *runtime monitoring*. They link the techniques for each gap to classical safety engineering strategies such as safe fail and safety margins. What matters most for this thesis is that they treat monitoring as its own architectural category, with three groups of techniques: uncertainty estimation, in-distribution error detection and out-of-distribution detection. Adaptation A3 in Chapter 3 takes this idea directly. Vasudevan et al. (2021) continue the line and propose evidential deep learning (Sensoy et al., 2018) to quantify uncertainty in a way that explicitly follows ISO 26262.

The four families complement each other. They are not alternatives, and a mature system should use parts of all of them. The literature, however, usually presents them as separate contributions, with no framework that brings them together inside a life cycle with traceability and a safety case. This is one of the gaps this thesis identifies.

## 2.4 Scenario-based validation

The previous section is about how to *build* safe systems. This line is about how to *evaluate* them. The main question is what it means to validate a system whose operational domain is continuous and, strictly speaking, infinite. The most common answer is to test against a curated library of representative situations instead of trying to cover everything.

The theoretical problem behind this is coverage. De Gelder et al. (2024) propose metrics for what it means for a scenario database to *cover* the domain: whether it captures all relevant aspects of the ODD, described with tags, and whether it covers the driving data it came from in time and in actors involved. They also argue that simply counting concrete parameterised scenarios cannot give a meaningful coverage number. Without such metrics, any library can be called "sufficient" with circular arguments. In practice, CARLA (Dosovitskiy et al., 2017) has become the reference urban simulator: Gao et al. (2021) build on it a combined metric calibrated against human raters, and Paniego et al. (2024) publish an open tool that organises how metrics are collected and aggregated in simulation, for both CARLA and Gazebo.

A newer line uses reinforcement learning to generate test scenarios. Giamattei et al. (2025) replicate and extend earlier work and find something unexpected: once the biases in collision measurement are removed, RL does no better than random sampling. Only after fixing the reward function and adapting the algorithm to the continuous space does its theoretical advantage turn into a real improvement. The practical lesson is that the quality of the failure metric matters more than how advanced the method looks. This lesson applies directly to the design of the campaign in Chapter 8.

The shared limitation of this line is that it covers evaluation but not the life cycle. It is a necessary part of a methodological framework, but it is not a framework by itself.

## 2.5 Standards and normative frameworks

Five documents shape the standards landscape, and none of them covers it completely.

**ISO 26262:2018** (ISO, 2018) sets up the functional safety framework and makes the V-Model the reference life cycle. Its known limitation is that it assumes deterministic systems that can be specified in advance. ISO 21448:2022 (SOTIF) (ISO, 2022) widens the scope to hazardous behaviour that does not come from faults but from limits of the function under conditions nobody anticipated. It is the first official response to the fact that a system with ML can behave wrongly without anything having "failed" in the classical sense. Wang et al. (2024), in a view that is important for this thesis, review SOTIF across development, verification and validation, and operation, and describe the algorithm-level work as a V-Model extended with an operation phase centred on runtime monitoring. ISO/IEC TR 5469:2024 (ISO/IEC, 2024) is the most specific document on AI in safety functions. It classifies AI technology along two axes. One is how the AI is used in the system. The other is a technology class: Class I means the technology can be developed and reviewed with existing functional safety standards. Class II means extra methods are also needed to reach the required properties. Class III means no known methods are enough. The TR puts deep learning models most likely in Class II or III. It also proposes a three-stage realisation principle. ISO/PAS 8800:2024 (ISO, 2024) is the automotive document on AI and is closely linked to TR 5469. It extends ISO 26262 and ISO 21448 to AI elements by adapting the relevant ISO 26262 clauses and extending the SOTIF concepts. An example use case published by BSI for the UK CCAV (Hawkins, 2025), on an ML traffic-sign detector, shows how ISO 26262, SOTIF and PAS 8800 can be combined for an ML component. UL 4600 (UL Standards, 2023) formalises the *safety case* with a claim–argument–evidence structure (Koopman, 2023).

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figure 2.3 — Applicable normative pyramid." width="440"/>

*Figure 2.3 — Normative pyramid: ISO 26262 as the base life cycle, SOTIF as the complement for unexpected conditions, TR 5469 as the general AI layer, PAS 8800 as the automotive AI extension, UL 4600 as the safety case around everything, and AMLAS as argument patterns that apply across all of them.*

Outside the standards, two reviews complete the picture. Wäschle et al. (2022) carry out a systematic review of AI safety in highly automated driving, keeping 102 publications after screening. They separate established approaches from new ML-specific ones and point out that claims about the performance of learned components are always statistical, and that safety standards still need to be extended to AI. Paterson et al. (2025) consolidate AMLAS, a six-stage method with GSN patterns for building safety arguments about ML components, aligned with a data-centred life cycle. AMLAS provides the argumentation part that was missing, and it is now being included in the new standards.

In short, each document covers something necessary: the classical cycle, unexpected conditions, the nature of AI, its automotive extension, how to structure evidence, and argument patterns. None of them gives an executable method that combines them in a real project. That work is left to the engineering team, and it is exactly what this thesis proposes.

## 2.6 V-Model adaptations for systems with AI

The work closest to this thesis is the work that explicitly adapts the life cycle.

Salay, Queiroz and Czarnecki (2017) are the starting point. They go through the ten parts of ISO 26262 and find five areas of impact: hazard identification (including RL-specific failure modes such as *reward hacking*), faults and failure modes, using training sets instead of specifications, the architectural level compared with the implementation unit, and whether the Part 6 techniques still apply. Of the Part 6 software techniques that apply at unit level, which are 34 of the 75, they find that about 40 % do not apply to ML components at all. The main reason is that these techniques were written for imperative programming languages. Assumptions S1–S5 in Chapter 3 restate that analysis in operational form.

Ullrich et al. (2025) are the most relevant current reference. They propose concrete structural changes to the classical V-Model: iterative loops between levels, explicit data-centred phases, runtime monitoring as an extended right arm, and artefacts specific to data-driven development. They also already include explicit stages for moving the system from simulation to real data and for evaluating that move. The difference with this thesis is in the kind of work, not in the goal. Ullrich et al. describe *what* to do, as a framework that can be reused, and only sketch how to apply it. This thesis works on *how* to do it, in three areas they leave open: an executable version of each change, a complete documented case, and an empirical measurement of the sim-to-real gap on a real platform.

Vasudevan et al. (2021) are an intermediate step. Their work is limited to handling uncertainty and has no complete application case. Sprockhoff et al. (2023), from aerospace, add a different view based on model-based systems engineering. Their idea is that the model, not the text documentation, is the central artefact. This fits well with the strict traceability that AI systems need. However, industrial MBSE tools take a long time to learn, which makes them hard to use in smaller projects. There, version-controlled text files are more practical and give the same function.

Apart from these works, there is very little literature on life cycle adaptations compared with the literature on individual aspects. This makes sense, since individual contributions are easier to publish and easier to evaluate cleanly. But it explains why the industrial use of AI in safety functions is still *ad hoc* and depends on the judgement of each team instead of a shared framework.

## 2.7 The sim-to-real gap and how to measure it

Every policy trained in simulation faces the same question when it is deployed: how much of the learned behaviour carries over? The techniques to reduce the gap fall into three groups that work together. Domain randomization trains on many different simulated variants. Domain adaptation adjusts the policy or its representations to the real domain with a small amount of data. System identification improves the simulation by calibrating it with physical data.

But the problem is not only reducing the gap. It is also describing it honestly. A deployed system can work well on average and fail badly under specific conditions that nobody measured. The literature has many proposals for reducing the gap and very few systematic frameworks for *measuring* it in a form that is useful for a safety case. This is why adaptation A5 makes measuring the gap a required level of the life cycle.

The simulator used here is Gazebo (Koenig and Howard, 2004), and the choice is justified in §3.6. What matters for this section is only its consequence: its visual quality is lower than that of the engines behind CARLA, so the gap that A5 asks to measure is expected to be larger. Whatever the simulator, for 1:14 scale vehicles the match between simulated and real dynamics has its own differences — tyre friction, loop delays, noise from the onboard sensors — that need to be measured. Cheng et al. (2025) are the closest precedent, but like the rest of the literature they focus on *reducing* the gap and not on measuring it systematically. That measurement is the topic of Chapter 9.

## 2.8 Critical summary and positioning

The table below summarises the state of the art along seven axes. The full version, with the twenty lines of work reviewed, is in Appendix G.

| Line of work | Safe training | Cage / filter | Scenarios | Life cycle | Explicit traceab. | Sim-to-real gap | E2E case |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Safe RL (García and Fernández; Keswani; Wei) | ✓ | – | – | – | – | – | – |
| Safety cages and filters (Kuutti; Tearle) | partial | ✓ | – | – | – | – | – |
| Scenario-based validation (De Gelder; Gao; Paniego) | – | – | ✓ | – | – | – | – |
| Applied sim-to-real (Cheng et al.) | partial | – | – | – | – | partial | partial |
| Standards and safety case (SOTIF; UL 4600; AMLAS; PAS 8800) | – | – | partial | ✓ | partial | – | partial |
| Life cycle adaptation (Salay; Ullrich; Sprockhoff) | partial | partial | partial | ✓ | partial | partial | – |
| **This thesis** | **partial** | **✓** | **✓** | **✓** | **✓** | **✓** | **partial** |

*Table 2.1 — Positioning of the thesis (short version; full version in Appendix G).*

Three points come out of the table.

**First.** The individual contributions are solid and often go deep. It is not reasonable, or necessary, to try to beat them on any single axis. The thesis uses existing solutions for training (PPO), for containment (the safety cage tradition) and for validation (scenario-based methods).

**Second.** Some proposals do adapt the life cycle, and several of the changes in this thesis already appear there in some form. Runtime monitoring as an extended right arm comes before A3, and the GSN patterns of AMLAS share the same idea as the two-way traceability of A4. So the new part is not the adaptations themselves. It is three things that no earlier work covers together. The first is an executable version: each adaptation is turned into artefacts and checkers instead of staying a recommendation. The second is traceability as a hard constraint: it becomes a property that a tool checks, which goes further than the descriptive level of AMLAS and of model-based engineering. The third is a complete application case, with the problems and real costs documented.

**Third.** Measuring the sim-to-real gap is the least covered axis, for the imbalance described in §2.7. Adaptation A5 and Chapter 9 are a specific contribution on that axis, with external validity limited to a scale vehicle on a controlled track.

With this overview in place, Chapter 3 presents the methodological framework, which is the main academic contribution of the thesis.
