# Chapter 7 — Training specification and execution

## 7.1 Purpose of the chapter

This chapter develops the second half of adaptation A1: the **Training Specification**. It is a meta-specification, not a behaviour specification. It does not say what the policy will do for a given state — it cannot say it — but it fixes precisely the **process that produces it**: observation and action spaces, reward function, termination criteria, role of the cage during training, hyperparameters, seeds and checkpoint policy. A reader who has this document and the code can reproduce the process; they cannot predict the result. That asymmetry is exactly the point of the adaptation.

The complete hyperparameter table and the comparative study between algorithms, with its eight configurations and its evaluated checkpoints, are given in **Appendix H**.

## 7.2 Specification of the process

### 7.2.1 Observation and action

The observation of the reference system is the **front camera image**, reduced to 84×84 in grey scale and stacked over four consecutive frames in order to give the policy motion information. The stacking is not an implementation detail: without it the policy cannot distinguish a static situation from a dynamic one, and the heading error becomes partially unobservable. The network is a standard convolutional network of the type used in control from pixels.

The action space is **configuration, not a constant of the work**, and the path between its two values is one of the argument lines of this chapter. During most of the project the action was **one-dimensional** — steering only, with fixed longitudinal speed — which reduces the problem to lateral control and keeps clean the separation between what the reward guides and what the cage guarantees. The final reference configuration is **two-dimensional** — steering and throttle — with a speed ceiling of 0.22 m/s and a dead band in the throttle command. The consequence is substantive: in 1-D the speed rules of the cage are **structurally inert**, because speed is not a decision variable; only with longitudinal authority can they really arbitrate.

### 7.2.2 Reward function

The reward combines four terms: **progress** along the arc of the circuit, which is the task signal; **penalty on the lateral error**, which centres it in the lane; **penalty on the heading error**, which aligns it with the tangent; and **penalty on the command variation**, which discourages jerky driving. In the two-dimensional configuration a fifth term is added against the degenerate optimum of **stopping**: without it, a policy with authority over the throttle discovers that parking avoids all the penalties, a textbook case of the reward exploitation hazard that the hazard register anticipated.

The relation between reward and safety should be made explicit, because it is one of the most important design decisions of this work: **the reward contains no safety terms**. It does not penalise the activation of the cage and it does not reward staying away from the limit. The reason is separation of responsibilities — the reward guides, the cage guarantees — and it has a valuable experimental consequence: since the policy was not trained to please the cage, the frequency with which the cage intervenes is an **uncontaminated measure** of the quality of the learned driving.

### 7.2.3 The cage during training

The cage is **active in the training loop**, filtering the command before it reaches the simulated vehicle. The decision has obvious advantages: episodes are not wasted on catastrophic excursions and the agent experiences the dynamics of the system as it will be deployed. It also has a cost that this work did not fully anticipate and that Chapter 8 documents as a finding: if the cage integrates the command during training, **the policy learns against a system that already includes the cage**, and what is optimised is the pair and not the policy alone.

### 7.2.4 Reproducibility

Every training run records the seed, the configuration version, the *hash* of the cage parameter file, the code revision and a timestamp. Checkpoints are saved at a fixed cadence and each one carries a cryptographic identifier that links it to its configuration; an evaluation that tries to load a checkpoint with an incompatible configuration **fails explicitly** instead of producing a silently invalid result. It is a modest mechanism that avoided at least one serious confusion during the project.

## 7.3 Results: the one-dimensional camera policy

The first competent camera policy is trained on the winding circuit with a one-dimensional action. Its mean episode reward rises to a **peak of ≈ 823 at around 297,000 steps** and keeps a high band for about 150,000 more steps, after which it **decays**. The diagnosis matters: the critic loss stays tiny during the whole run, so **this is not value function instability but exploration contraction** once the standard deviation of the policy is annealed too far. That is why the policy that is kept is the one at the peak and not the one at the end.

<img src="../figures/fig_7_1_convergence_newcam.png" alt="Figure 7.1 — Convergence of the one-dimensional camera training." width="540"/>

*Figure 7.1 — Convergence of the one-dimensional camera policy: reward and mean episode length against steps. Peak ≈ 823 and a high plateau; the later exploration collapse motivated the manual stop and the selection of the checkpoint at the peak.*

A second result of this training is the **co-adaptation between policy and cage**: the intervention rate falls from ~87 % at the start to ~40 %, **dominated by the rate limiter**, while the safety rules fall to zero. The reading is that the policy learns to respect the safety constraints — it does not approach the edge — but its steering command is still jerky and the limiter smooths it continuously.

The deterministic nominal evaluation against a classical controller on the same circuit gives the result that justifies the cost of the learned component:

| Metric (nominal scenario) | Classical baseline | **1-D camera RL** |
| --- | --- | --- |
| Laps completed | 4.85 | 4.88 |
| Mean lateral error | 17.2 mm | **10.9 mm** |
| Maximum lateral error | 57.3 mm | 48.2 mm |
| Emergency stops | 0 | **0** |
| Cage intervention | 0 % | 43.5 % (limiter only) |

*Table 7.1 — Nominal evaluation: camera policy against the classical baseline on the same circuit.*

The agent **beats the classical baseline in tracking precision** — 37 % less mean lateral error, over the same distance travelled and with zero emergencies — which **reverses the finding obtained on the oval**, where the classical controller was the more precise one: on a winding geometry the look-ahead point of the classical method degrades while the network holds the line. Two qualitative observations accompany the result. The cage stays **latent inside the domain in both modes**: zero emergencies and no activation of the safety rules, only of the rate limiter; enforcement and monitoring give almost identical laps and errors. And the cost of the learned agent **is not safety but smoothness**: it triggers the limiter in 43 % of the steps against 0 % for the classical controller, a benign intervention that absorbs the jerk without damaging precision.

## 7.4 Variability between seeds

A result with a single seed says nothing about a stochastic procedure. Replication over five seeds produces the most uncomfortable and probably the most useful finding of the chapter: **the training curve does not classify the behaviour**. Three of the five seeds turn out to be constraint-respecting — the cage stays latent — while the other two depend on the cage substantially, with hundreds of safety interventions, and **that difference is not predictable from the training reward**: seeds with practically indistinguishable curves fall on different sides.

The methodological consequence is direct and applies to the rest of the work: **the policy cannot be selected by reward**. It has to be selected by closed-loop evaluation over scenarios, with the intervention rate of the cage as a first-order criterion. It is a concrete example of what the framework is meant to produce: an acceptance criterion that no training metric would have produced.

## 7.5 The reference policy: two-dimensional action

### 7.5.1 Motivation and choice of algorithm

The first attempt at a complete campaign over a two-dimensional action was executed with a **doubly suboptimal** policy: an algorithm outside its regime, a short training, and, worse, a checkpoint **after the peak** instead of at the peak. Its result left a well-posed question: were the observed failures **of the two-dimensional action** or **of that policy**? To answer it, a two-dimensional policy was trained properly, with two changes, both of them measured.

**Algorithm.** A policy trained with the on-policy method reaches a mean reward of **1755 at around 472,000 steps** with a high and stable plateau, while the off-policy method never exceeds ~200 and does not manage to master the circuit. **Speed ceiling.** A single-variable comparison shows that at 0.5 m/s the policy peaks at 654 and drives dirty — it overshoots the tight curves — against 1421 at 0.22 m/s, where it takes them cleanly.

An honesty warning about the figures: the reward **is not comparable one to one between action spaces**, because the episode ceiling doubles when moving to two dimensions. The factor of ~2 with respect to the one-dimensional policy is mostly greater survival and horizon, not "twice as good driving".

<img src="../figures/auto/fig_ppo2d_training_curve.png" alt="Figure 7.2 — Training curve of the two-dimensional reference policy." width="600"/>

*Figure 7.2 — Training reward of the **two-dimensional** reference policy against the one-dimensional one and against the off-policy variant. Peak 1755 and a high stable plateau, against the post-peak collapse of the first one and the ceiling of ~200 of the second one. The candidate checkpoints evaluated are marked.*

### 7.5.2 Checkpoint selection: by driving, not by reward

During the whole training the cage stays **latent in safety**: no activation of the lateral limit, heading, predictive or emergency rules; only of the rate limiter. The selection was resolved by evaluating three candidates in closed loop, and the result confirms the lesson of §7.4 as clearly as possible: **the checkpoint at the reward peak is the worst of the three** — fourteen safety interventions and 49 mm maximum lateral error — while the one at 550,000 steps wins clearly: **5.32 laps, 8.6 mm mean error, 27 mm maximum, zero emergencies and zero safety interventions**.

Selecting by reward would have chosen the worst candidate. It is a bias control documented **before** the verdict campaign was executed, and it is the direct answer to the objection that the best arm might have been selected after the fact.

### 7.5.3 What the policy does with longitudinal authority

<img src="../figures/auto/fig_ppo2d_action_distribution.png" alt="Figure 7.3 — Distribution of the two-dimensional raw action." width="640"/>

*Figure 7.3 — Distribution of the **raw action** at the start against the end of training, one panel per dimension. In **steering**, the initial all-or-nothing command dissolves (36.9 % → 7.1 % of saturated samples). In **throttle**, the evolution is the opposite, towards saturation (48.2 % → 89.6 %): the policy learns to ask for the ceiling almost always.*

The honest reading of the longitudinal authority is that the policy uses it to **set the speed regime, not to draw a profile**. There is modulation and it is well localised — the 8.3 % of steps with reduced throttle are concentrated at high curvature and rise to 35.6 % at the tightest apex — but its **magnitude is marginal**: the throttle drops to 0.81 and the speed falls only from 0.218 to 0.216 m/s. The policy arrives at the tightest curves practically at the ceiling. This apparently minor observation explains one result of Chapter 8: the speed rule of the cage **never activates during the whole campaign**.

### 7.5.4 Authorisation before the campaign

Before executing the verdict campaign, the policy passed a **preflight check bound by cryptographic identifier** to its checkpoint and to its configuration, which verifies that the measurement interface of the cage — the lane estimator and its heading reading — behaves as it should: real heading failures detected, zero false positives over safe centred cycles, and bounded delay. The check **passed in all seven of its tests**, and it is what authorises the campaign.

The order matters methodologically: the policy is selected by nominal evaluation, the instrumentation is verified separately and bound by *hash*, and only then is the campaign executed. None of the three steps can be reordered without weakening the evidence.

## 7.6 Synthesis

The chapter leaves three results that the next one uses. First, a competent camera policy exists and the reference against a classical method is established. Second, **the training curve does not classify the behaviour**: the selection has to be made by closed-loop driving, and that criterion, applied to the reference policy, discarded precisely the checkpoint that the reward would have chosen. Third, the reference policy has longitudinal authority but uses it to set the regime, not to modulate, which conditions which cage rules actually get exercised.

Chapter 8 submits that policy to the scenario campaign and produces the verdict.
