# Chapter 2 — State of the art

## 2.1 Purpose and structure of the chapter

This chapter organises the relevant literature into a coherent map and, above all, identifies the seams between lines of work that the thesis intends to address in a unified way. The review is selective, not exhaustive: it gives priority to work from the last seven years and to work with a visible influence on the academic or normative discussion. It moves from the general to the particular — reinforcement learning in driving (§2.2), families of safety approaches (§2.3), scenario-based validation (§2.4), standards (§2.5), life cycle adaptations (§2.6) and the sim-to-real gap (§2.7) — and closes with a critical synthesis that positions the thesis (§2.8).

## 2.2 Reinforcement learning in autonomous driving

The use of machine learning in vehicle control has evolved in three waves. The first one, behaviour cloning and *imitation learning*, showed that a network could map pixels to steering commands, but it suffered from fragility under deviations from the expert state. The second one, deep reinforcement learning (DRL), promised to overcome that limitation by letting the agent explore the consequences of its decisions actively (Kuutti et al., 2019a). The third one, still in progress, combines both through hybrid schemes and integrates world models and explicit safety representations.

<img src="../figures/fig_2_1_classical_rl_framework.png" alt="Figure 2.1 — The classical reinforcement learning framework." width="400"/>

*Figure 2.1 — The classical reinforcement learning framework (Sutton and Barto, 1998). The agent chooses an action `At` in state `St` and receives the corresponding reward; its objective is to maximise the accumulated reward over a long sequence of transitions.*

Two algorithms dominate recent work. PPO (Schulman et al., 2017) offers training stability thanks to its clipped loss, which makes it attractive when reproducibility matters and sensitivity to hyperparameters is an operational problem. SAC (Haarnoja et al., 2018) optimises a maximum-entropy objective that favours exploration and robustness and, being *off-policy*, is more sample-efficient. Both are used in this work and compared experimentally in Chapter 7.

In the concrete domain of lane following, Cheng et al. (2025) show the feasibility of pure DRL trained with domain randomization and deployed on a physical platform, and Zhao et al. (2024) address highway decision making through constrained CMDP-type policies with a *replay buffer*. The trend is clear: for short decision horizons and bounded domains, DRL gives solid results; for long horizons and open domains, the community recognises that it is not sufficient without additional guarantee mechanisms.

The end-to-end vision variant has its own lineage, which the primary track of this thesis takes up again: ALVINN (Pomerleau, 1989), with a tiny network over 30×32 pixels; PilotNet/DAVE-2 (Bojarski et al., 2016), which scaled it by behaviour cloning to real roads; and Kendall et al. (2019), who closed the circle with DRL by training lane following from a monocular image on a real vehicle. In parallel, domain randomization — visual (Tobin et al., 2017) and dynamic (Peng et al., 2018) — became the standard mitigation for the fragility of learned perception. This thesis is placed in that line, but its contribution is not the end-to-end driver itself: it is the safety instrumentation around it. The runtime envelope does not share the learned network — it reasons over a classical, deterministic lane estimator that is independent by algorithm — and visual degradation becomes an evaluation axis controlled by scenario, and not only training noise.

The structural problem shared by all this work is the same: the behaviour of the policy cannot be derived from a specification written in advance, which breaks the founding assumption of the classical functional safety frameworks.

## 2.3 Safety approaches for systems with learned components

The literature can be organised into four families, each one attacking the problem from a different angle of the life cycle.

**(a) Safe RL: safety built into the training.** The classical taxonomy is the one by García and Fernández (2015), which distinguishes two axes: modification of the optimisation criterion and modification of the exploration process. Recent work incorporates explicit safety representations in the state space or in the value function; Keswani and Bhattacharyya (2025) encode proximity to unsafe states as a learned predictive representation, with significant improvements over baselines that are not informed by safety. The approach is elegant, but it shares a structural limitation with the whole paradigm: the guarantee remains statistical and dependent on the training distribution, and it does not transfer automatically to a shifted operational domain.

**(b) Safety cages and runtime filters.** Complementary to the previous family, this one operates at inference time and treats the policy as a black box whose outputs must be filtered. Kuutti et al. (2019b) introduce the *safety cage* applied to autonomous vehicles: a deterministic module that monitors the outputs of the network and replaces them when the proposed behaviour would violate an invariant; because it is written with explicit rules, it is entirely verifiable by classical techniques. Kuutti et al. (2021) extend the idea to a double role — containment at deployment and weak supervision during training — which establishes a path in which the cage does not only contain but also *shapes* the behaviour of the agent. That duality reappears, without being sought, among the findings of Chapter 8.

<img src="../figures/fig_2_2_safety_cage_idea.png" alt="Figure 2.2 — The safety cage applied to the classical RL framework." width="400"/>

*Figure 2.2 — The safety cage applied to the classical reinforcement learning framework.*

A related line proposes *predictive safety filters* based on model predictive control: instead of evaluating actions pointwise, the filter projects the consequences of the proposed action and admits it only if the predicted trajectory stays in the safe set (Tearle et al., 2021). Its advantage is formal elegance; its practical disadvantage is the dependence on a sufficiently accurate dynamic model, which is difficult to obtain with noisy perception. The architectural lineage goes back to the Simplex pattern (Sha, 2001) — a complex controller supervised by a simple and verified one — and to its modern formalisation as *shielding* (Alshiekh et al., 2018), which corrects the action only to the minimum extent necessary. The cage of this thesis is an instance of the Simplex pattern with deterministic rules, placed between the cage of Kuutti et al., from which it inherits verifiable containment, and the formal *shield*, whose discipline of minimal intervention it replicates in its rate-limiting rule.

**(c) Robustness against perturbations.** He et al. (2024) study empirically a Q-learning controller on TORCS against two threat models. The finding is counter-intuitive and methodologically important: perturbations on the sensors hardly affect the system — the attack success rate is close to zero because of the discretisation of the action space — while the direct alteration of the action succeeds between 60 % and 78 % of the time. Discretisation emerges as *accidental* robustness against one channel and leaves the other one exposed. Wei et al. (2026) attack that asymmetry by concentrating the attacks on critical states under a limited budget and training over a dual *replay buffer*. The methodological implication is direct: the characterisation of the policy must include its response to inputs and outputs outside the nominal distribution, and the cage must be designed assuming that both the policy and its interfaces can fail.

**(d) Runtime monitoring.** Transversal to the previous three, this family deals with detecting errors during operation itself. Mohseni et al. (2019) organise the solution space around the five gaps that ML introduces over the classical standards — specification, transparency, verification, performance and *runtime monitoring* — and map each one to Varshney's four safety strategies. Their key contribution for this thesis is the identification of the monitoring function as an architectural category in its own right, with three families of techniques to materialise it: uncertainty estimation, in-distribution error detection and out-of-distribution detection. Adaptation A3 in Chapter 3 inherits that philosophy directly. Vasudevan et al. (2021) extend the line by proposing evidential deep learning to quantify uncertainty in explicit compliance with ISO 26262.

The four families are complementary, not alternative: a mature system should incorporate elements of all of them. The literature, however, tends to present them as isolated contributions, without a framework that articulates their integration inside a life cycle with traceability and a safety case. That is one of the gaps this thesis identifies.

## 2.4 Scenario-based validation

While the previous section deals with how to *build* safe systems, this line deals with how to *evaluate* them. The central question is what it means to validate a system whose operational domain is continuous and, strictly speaking, infinite; the dominant answer is to evaluate against a curated library of representative situations instead of attempting exhaustive coverage.

The underlying theoretical problem is the notion of coverage. De Gelder et al. (2024) formalise what it means for a library to *cover* the domain, distinguishing coverage over scenario parameters, over interactions between agents and over classes of critical events. Without coverage metrics, any library can be defended as "sufficient" through circular arguments. On the operational side, CARLA (Dosovitskiy et al., 2017) has become the reference urban simulator; Gao et al. (2021) propose on top of it a composite metric calibrated against human evaluators, and Paniego et al. (2024) publish an open tool that systematises the capture and aggregation of metrics both in simulation and on physical platforms.

An emerging line uses reinforcement learning itself to generate test scenarios. Giamattei et al. (2025) replicate and extend earlier work and find something counter-intuitive: once the biases in collision measurement are controlled, RL does not beat random sampling; only after cleaning the reward function and adapting the algorithm to the continuous space does its theoretical advantage become an empirical improvement. The practical lesson — the quality of the failure metric weighs more than the nominal sophistication of the method — is directly applicable to the design of the campaign in Chapter 8.

The common limitation of this line is that it deals with evaluation but not with the life cycle: it is a necessary piece of a methodological framework, but on its own it does not constitute one.

## 2.5 Standards and normative frameworks

Five documents structure the normative space, and none of them closes it.

**ISO 26262:2018** establishes the functional safety framework and formalises the V-Model as the reference life cycle; its acknowledged limitation is that it assumes deterministic systems that can be specified in advance. ISO 21448:2022 (SOTIF) extends the scope to hazardous behaviours that do not come from faults but from limitations of the function under unanticipated conditions — the first institutional answer to the fact that a system with ML can behave incorrectly without anything having "failed" in the classical sense. Wang et al. (2024) propose, in a way that is notable for this thesis, a reformulation of the V-Model with a continuous operation phase that integrates post-deployment monitoring as an extended right arm. ISO/IEC TR 5469:2024 is the most specific document on AI in safety functions: it classifies AI technology elements into classes I and II depending on whether they admit traditional verification — an RL policy typically falls into Class II — and proposes a three-stage realisation principle. ISO/PAS 8800:2024 is its automotive specialisation and indicates which ISO 26262 clauses are kept, which are adapted and which are replaced in the presence of an AI component; its early application to a real case by BSI and the UK CAM (2024) is the first public template for articulating ISO 26262 + SOTIF + PAS 8800 over an ML chain. UL 4600 formalises the *safety case* under the claim–argument–evidence philosophy (Koopman, 2023).

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figure 2.3 — Applicable normative pyramid." width="440"/>

*Figure 2.3 — Normative pyramid: ISO 26262 as the base life cycle, SOTIF as the complement for unanticipated conditions, TR 5469 as the AI umbrella, PAS 8800 as the automotive specialisation, UL 4600 as the enclosing safety case, and AMLAS as transversal argumentation patterns.*

Outside the standards, two syntheses complete the picture. Wäschle et al. (2022) review 145 references on AI safety in highly automated driving in a systematic way, and identify as central gaps the absence of universally accepted metrics and the immaturity of the certification processes. Paterson et al. (2025) consolidate AMLAS, a six-stage methodology with GSN patterns for building safety arguments over ML components, aligned with a data-centric life cycle; it is the argumentation piece that was missing, and it is being incorporated into the emerging standards.

The synthesis is that each document covers a necessary angle — the classical cycle, unanticipated conditions, the nature of AI, its automotive specialisation, the structuring of evidence and the argumentation patterns — but none of them prescribes an executable methodology that integrates them in a concrete project. That integration is left to the engineering team, and it is precisely what this thesis proposes.

## 2.6 V-Model adaptations for systems with AI

The level closest to the contribution of this thesis is the work that adapts the life cycle explicitly.

Salay, Queiroz and Czarnecki (2017) are the founding antecedent. Their analysis over the ten parts of ISO 26262 identifies five areas of impact — hazard identification (including modes specific to RL, such as *reward hacking*), faults and failure modes, the use of training sets in place of specifications, the architectural level versus the implementation unit, and the applicability of the Part 6 techniques — and quantifies that close to 40 % of the 75 software techniques of the standard do not apply to ML components without modification. The five assumptions developed in Chapter 3 are an operational reformulation of that analysis, articulated so that each assumption admits a corresponding adaptation.

Ullrich et al. (2025) are the most relevant reference in the current line: they propose concrete structural modifications to the classical V-Model — iterative cycles between levels, explicit data-centric phases, runtime monitoring as an extended right arm, and artefacts specific to the data-driven paradigm. The difference from this thesis is one of nature, not of objective: Ullrich et al. articulate the *what* at the level of a transferable framework; this thesis articulates the *how* in three dimensions that they leave open — an executable operationalisation of each modification, a concrete end-to-end documented case, and the empirical characterisation of the sim-to-real gap as a mandatory validation level.

Vasudevan et al. (2021) represent an intermediate step, limited to uncertainty management and without a complete application case. Sprockhoff et al. (2023), from the aerospace domain, offer a complementary perspective through model-based systems engineering: their philosophy — the model is the central artefact, not the textual documentation — fits naturally with the strict traceability that AI systems demand, but the adoption curve of the industrial tools makes them not very accessible for smaller-scale projects, where an approach based on version-controlled text files is more practical while keeping functional equivalence.

Beyond these works, the literature on life cycle adaptations is notably scarce compared to the literature devoted to individual aspects. The asymmetry is understandable — individual contributions are easier to publish and admit a cleaner evaluation — but it explains why the industrial adoption of AI in safety functions is still an *ad hoc* process, dependent on the judgement of the team rather than on a shared framework.

## 2.7 The sim-to-real gap and its characterisation

Every policy trained in simulation faces an unavoidable question when it is deployed: to what extent does the learned behaviour transfer? The techniques to reduce the gap fall into three complementary families: domain randomization, which trains over a wide distribution of simulated variants; domain adaptation, which adjusts the policy or its representations to the real domain with limited data; and system identification, which improves the simulation by calibrating it against physical data.

The problem, however, is not only to reduce the gap but to characterise it honestly. A deployed system can behave well on average and catastrophically badly under specific conditions that have not been characterised. The literature is rich in proposals to reduce the gap and poor in systematic frameworks to *measure* it in terms that are useful for a safety case; that gap in the literature is the reason why adaptation A5 incorporates the characterisation of the gap as a mandatory level of the life cycle.

The simulator adopted here is Gazebo (Koenig and Howard, 2004), operated through a gymnasium–Gazebo–ROS2 interface reused from earlier work by the author; the choice is justified in §3.6. It is enough to note here that its visual fidelity is lower than that of the graphics engines behind CARLA, which increases the expected magnitude of the gap that A5 requires to be characterised, and that for 1:14 scale vehicles the correspondence between simulated and real dynamics introduces specific discrepancies — tyre friction, loop latencies, noise of the embedded sensors — that require empirical characterisation independently of the simulator. Cheng et al. (2025) offer the most direct precedent but, like the rest of the literature, they concentrate on the *reduction* of the gap rather than on its systematic characterisation. That is the content of Chapter 9.

## 2.8 Critical synthesis and positioning

The following table summarises the state of the art along seven axes of interest. The complete version, with the twenty-one lines of work reviewed, is given in Appendix G.

| Line of work | Safe training | Cage / filter | Scenarios | Life cycle | Explicit traceab. | Sim-to-real gap | E2E case |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Safe RL (García and Fernández; Keswani; Wei) | ✓ | – | – | – | – | – | – |
| Safety cages and filters (Kuutti; Tearle) | partial | ✓ | – | – | – | – | – |
| Scenario-based validation (De Gelder; Gao; Paniego) | – | – | ✓ | – | – | – | – |
| Applied sim-to-real (Cheng et al.) | partial | – | – | – | – | partial | partial |
| Standards and safety case (SOTIF; UL 4600; AMLAS; PAS 8800) | – | – | partial | ✓ | partial | – | partial |
| Life cycle adaptation (Salay; Ullrich; Sprockhoff) | partial | partial | partial | ✓ | partial | – | – |
| **This thesis** | **partial** | **✓** | **✓** | **✓** | **✓** | **✓** | **partial** |

*Table 2.1 — Positioning space of the thesis (short version; complete in Appendix G).*

Three observations follow from the table.

**First.** The individual contributions are solid and often deep. It is neither reasonable nor necessary to try to improve on them along any individual axis: the thesis adopts existing solutions for training (PPO), for containment (the safety cage tradition) and for validation (the scenario-based methodology).

**Second.** Proposals that adapt the life cycle do exist, and several of the modifications proposed in this thesis have a precedent in them: runtime monitoring as an extended right arm anticipates A3; the GSN patterns of AMLAS share a philosophy with the bidirectional traceability of A4. The novelty is therefore not in having invented the adaptations, but in three dimensions that no previous work covers at the same time: executable operationalisation — each adaptation is materialised in artefacts and validators instead of remaining a recommendation; traceability as a hard constraint — turned into a property verified by a tool, which goes beyond the descriptive level of AMLAS and of model-based engineering; and an end-to-end application case, with the friction points and the real costs documented.

**Third.** The characterisation of the sim-to-real gap is the most weakly covered axis. Techniques to reduce it exist, but frameworks to *measure* it in terms compatible with a safety case are scarce. Adaptation A5 and Chapter 9 are a specific contribution along that axis, with external validity limited to the case of a scale vehicle on a controlled track.

With this panorama established, Chapter 3 develops the methodological framework that constitutes the central academic contribution of the thesis.
