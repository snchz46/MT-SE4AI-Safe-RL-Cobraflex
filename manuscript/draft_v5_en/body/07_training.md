# Chapter 7 — Training specification and execution

## 7.1 Purpose of the chapter

This chapter covers the second half of adaptation A1: the Training Specification. It is a meta-specification, not a specification of behaviour. It does not say what the policy will do in a given state, because it cannot. What it does is fix the process that produces the policy: observation and action spaces, reward function, termination criteria, the role of the cage during training, hyperparameters, seeds and how checkpoints are kept. Someone with this document and the code can repeat the process, but they cannot predict the result. That difference is exactly the point of the adaptation.

The full hyperparameter table and the comparison between algorithms, with its eight configurations and the checkpoints that were evaluated, are in Appendix H.

## 7.2 Process specification

### 7.2.1 Observation and action

The observation of the reference system is the front camera image, reduced to 84×84 in greyscale and stacked over four consecutive frames so that the policy gets information about motion. The stacking is not a small implementation detail. Without it, the policy cannot tell a static situation from a moving one, and the heading error becomes partly unobservable. The network is a standard convolutional network of the kind used for control from pixels.

The action space is a configuration choice, not something fixed for the whole work, and how it changed between its two values is one of the main threads of this chapter. For most of the project the action was one-dimensional: steering only, with a fixed forward speed. This reduces the problem to lateral control and keeps a clean line between what the reward guides and what the cage guarantees. The final reference configuration is two-dimensional, with steering and throttle, a speed ceiling of 0.22 m/s and a dead band in the throttle command. This matters a lot. In 1-D, the cage's speed rules can never do anything, because speed is not something the policy decides. Only when the policy controls speed can those rules really step in.

### 7.2.2 Reward function

The reward has four terms: progress along the circuit, which is the task signal; a penalty on lateral error, which keeps the vehicle centred in the lane; a penalty on heading error, which keeps it aligned with the track; and a penalty on changes in the command, which discourages jerky driving. In the two-dimensional configuration a fifth term is added to stop the policy from simply stopping. Without it, a policy that controls the throttle finds out that parking avoids all the penalties. This is a textbook case of the reward exploitation hazard that the hazard register had predicted.

The link between reward and safety needs to be stated clearly, because it is one of the most important design decisions of this work: the reward has no safety terms. It does not penalise cage activations, and it does not reward staying away from the limits. The reason is a split of responsibilities: the reward guides, the cage guarantees. This has a useful side effect for the experiments. Since the policy was not trained to please the cage, how often the cage intervenes is a clean measure of how good the learned driving is.

### 7.2.3 The cage during training

The cage is active in the training loop and filters the command before it reaches the simulated vehicle. This has clear advantages: episodes are not wasted on crashes, and the agent learns the dynamics of the system as it will be deployed. It also has a cost that this work did not fully expect, and that Chapter 8 reports as a finding. If the cage shapes the command during training, the policy learns against a system that already includes the cage, so what gets optimised is the pair and not the policy alone.

### 7.2.4 Reproducibility

Every training run records the seed, the configuration version, the *hash* of the cage parameter file, the code revision and a timestamp. Checkpoints are saved at fixed intervals, and each one has a cryptographic identifier that links it to its configuration. If an evaluation tries to load a checkpoint with a configuration that does not match, it fails with an error instead of quietly producing an invalid result. It is a simple mechanism, and it prevented at least one serious mix-up during the project.

The text uses descriptive names for trainings, checkpoints and campaigns, while figures and appendices use the short labels from the repository. Table 7.1 connects the two.

| Label in figures and appendices | Name in the text | What it is |
| --- | --- | --- |
| `F-track` | State track (control arm) | The policy observes a state vector projected from the true pose, on the oval circuit; it isolates the effect of the cage (§1.6.3). Campaign: `campaign`. |
| `track E`, `E-track` | Camera track | The policy observes the front-camera image; the reference system of the thesis. |
| `E-main`, `1-D PPO`, `297k` | One-dimensional camera policy | PPO, steering only at a fixed 0.20 m/s on `complex_b`; checkpoint kept at the reward peak, 297,000 steps (§7.3). Run: `ppo_newcam_complex_b_2024_1M`. |
| `seed 2024`, `42`, `23`, `666`, `123` | The five seeds | Copies of that training that differ only in the seed (§7.4). Runs: `ppo_newcam_complex_b_<seed>`. |
| `GE4-V2`, `campaign_e_v2` | Campaign of the one-dimensional policy | Second version of the scenario campaign of gate G4, run on `E-main`: 1,970 runs, kept frozen as the gate record. |
| `margin022`, `2-D SAC` | First two-dimensional campaign | SAC, steering and throttle, speed cap 0.22 m/s, which is 0.03 m/s below the 0.25 m/s curve ceiling of C-04 (hence the name); checkpoint at 75,000 steps; 1,970 runs (§7.5.1). Run: `sac_gz2d_entfix_margin022_2024_75k`; campaign: `campaign_2d_margin022`. |
| `2-D PPO 550k`, `cap 0.22` | Reference policy and reference campaign | PPO, steering and throttle, speed cap 0.22 m/s; checkpoint at 550,000 steps chosen by closed-loop driving (§7.5.2); its 1,890-run campaign gives the verdict (Chapter 8). Run: `ppo_gz2d_cap022_1M_2024`; campaign: `campaign_2d_ppo550k`. |
| `sim-to-real v2`, `1650k` | Policy retrained for transfer | Two-dimensional PPO retrained with per-episode mirroring and randomisation of photometry and camera geometry, 2.5 million steps; checkpoint at 1,650,000 steps deployed on the vehicle (§9.3.4). Its `v2` has nothing to do with `GE4-V2`. Run: `ppo_gz2d_sim2real_v2_2024`. |

*Table 7.1 — Names of trainings, checkpoints and campaigns. Conventions: `k` after a number counts thousands of training steps (`550k` = 550,000; `@297k` = at 297,000 steps); `1-D` and `2-D` give the size of the action (steering; steering and throttle); `cap` is the speed ceiling of the action; `complex_b` is the winding circuit (perimeter 19.22 m) and `oval` the oval one (R = 0.8 m); `newcam` in a run name marks runs made after the switch to the dedicated lane camera.*

## 7.3 Results: the one-dimensional camera policy

The first camera policy that drives well is trained on the winding circuit with a one-dimensional action. Its mean episode reward rises to a peak of ≈ 823 at around 297,000 steps, stays high for about 150,000 more steps, and then drops. The cause matters. The critic loss stays very small during the whole run, so the problem is not an unstable value function. It is that exploration shrinks once the policy's standard deviation is annealed too far. That is why the policy kept is the one at the peak and not the one at the end.

<img src="../figures/fig_7_1_convergence_newcam_notitle.png" alt="Figure 7.1 — Convergence of the one-dimensional camera training." width="540"/>

*Figure 7.1 — Convergence of the one-dimensional camera policy (`E-main`, Table 7.1): reward and mean episode length against steps. Peak ≈ 823 and a high plateau. The later collapse in exploration led to stopping the run by hand and keeping the checkpoint at the peak.*

<img src="../figures/fig_7_2_intervention_newcam_notitle.png" alt="Figure 7.2 — Cage activity during training." width="540"/>

*Figure 7.2 — Cage activity during the one-dimensional training. Top: the total intervention rate falls from ~87 % to ~40 %, while the emergency rate is zero from the start. Bottom: the per-rule breakdown shows what that rate is made of. It is the rate limiter. The safety rules C-01, C-02, C-03 and C-05 drop to zero in the first steps and stay there.*

A second result of this training, shown in detail in Figure 7.2, is that policy and cage adapt to each other. The intervention rate falls from ~87 % at the start to ~40 %, mostly from the rate limiter, while the safety rules drop to zero. This means the policy learns to respect the safety constraints (it does not go near the edge), but its steering is still jerky and the limiter keeps smoothing it.

The deterministic nominal evaluation against a classical controller on the same circuit, shown in Table 7.2, gives the result that justifies the cost of the learned component:

| Metric (nominal scenario) | Classical baseline | **1-D camera RL** |
| --- | --- | --- |
| Laps completed | 4.85 | 4.88 |
| Mean lateral error | 17.2 mm | 10.9 mm |
| Maximum lateral error | 57.3 mm | 48.2 mm |
| Emergency stops | 0 | 0 |
| Cage intervention | 0 % | 43.5 % (limiter only) |

*Table 7.2 — Nominal evaluation: camera policy against the classical baseline on the same circuit.*

The agent is more precise than the classical baseline: 37 % less mean lateral error, over the same distance and with zero emergencies. This is the opposite of what happened on the oval, where the classical controller was more precise. On a winding layout, the look-ahead point of the classical method becomes less reliable, while the network keeps its line. Two more observations come with this result. The cage stays latent inside the domain in both modes: zero emergencies and no safety rule activations, only the rate limiter, and enforcement and monitoring give almost the same laps and errors. And the cost of the learned agent is smoothness, not safety. It triggers the limiter in 43 % of the steps, against 0 % for the classical controller. This intervention is harmless: it absorbs the jerky steering without hurting precision.

## 7.4 Variation between seeds

A result from a single seed says nothing about a stochastic procedure. Repeating the training with five seeds, shown in Figure 7.3, gives the most uncomfortable and probably the most useful finding of the chapter: the training curve does not tell how the policy behaves. Three of the five seeds respect the constraints (the cage stays latent), while the other two rely heavily on the cage, with hundreds of safety interventions. This difference cannot be predicted from the training reward. Seeds with almost identical curves end up on different sides.

<img src="../figures/fig_7_8_multiseed_newcam_notitle.png" alt="Figure 7.3 — Comparison across five seeds." width="540"/>

*Figure 7.3 — Five seeds of the same procedure (Table 7.1; `@297k` marks the step of each peak). Top: the reward. The curves are similar and their peaks range from 713 to 823, with none clearly better than the others. Bottom: the cage intervention rate for the same runs, which does separate them. The information that tells the behaviours apart is in the bottom panel, not the top one, and it is exactly the panel that a selection by reward ignores.*

The consequence for the method is direct and applies to the rest of the work: the policy cannot be chosen by reward. It has to be chosen by closed-loop evaluation on scenarios, with the cage intervention rate as a main criterion. This is a concrete example of what the framework is supposed to produce: an acceptance criterion that no training metric would have given.

## 7.5 The reference policy: two-dimensional action

### 7.5.1 Motivation and choice of algorithm

The first attempt at a full campaign with a two-dimensional action used a policy that was weak in two ways: an algorithm used outside the range where it works well, and a short training. Worse, the checkpoint came after the peak instead of at the peak. Its result raised a clear question: were the failures caused by the two-dimensional action or by that particular policy? To answer it, a proper two-dimensional policy was trained, with two changes, both measured.

**Algorithm.** PPO, the on-policy method, reaches a mean reward of 1755 at around 472,000 steps (Figure 7.4), with a high and stable plateau. SAC, the off-policy method, never goes above ~200 and never learns to drive the circuit. This is the experimental comparison announced in §2.2, and it settles the algorithm for the rest of the work. **Speed ceiling.** A comparison that changes only this variable shows that at 0.5 m/s the policy peaks at 654 and drives badly (it overshoots the tight curves), against 1421 at 0.22 m/s, where it takes them cleanly.

A warning about these numbers: reward cannot be compared directly between action spaces, because the maximum episode reward doubles when moving to two dimensions. The factor of ~2 compared with the one-dimensional policy comes mostly from surviving longer and a longer horizon, not from "driving twice as well".

<img src="../figures/auto/fig_7_4_ppo2d_training_curve.png" alt="Figure 7.4 — Training curve of the two-dimensional reference policy." width="600"/>

*Figure 7.4 — Training reward of the two-dimensional reference policy (`2-D PPO`) compared with the one-dimensional policy (`E-main`) and with the off-policy version (`margin022`); labels in Table 7.1. Peak 1755 and a high stable plateau, against the collapse after the peak of the first one and the ~200 ceiling of the second. Marked: the three candidate checkpoints evaluated in closed loop, including the selected one, and the checkpoint kept from each of the other two runs.*

### 7.5.2 Choosing the checkpoint: by driving, not by reward

During the whole training, the cage stays latent for safety: the lateral limit, heading, predictive and emergency rules never fire, only the rate limiter does. The choice was made by testing three candidates in closed loop, and the result confirms the lesson of §7.4 very clearly. The checkpoint at the reward peak is the worst of the three, with fourteen safety interventions and a 49 mm maximum lateral error. The one at 550,000 steps clearly wins: 5.32 laps, 8.6 mm mean error, 27 mm maximum, zero emergencies and zero safety interventions.

Choosing by reward would have picked the worst candidate. This is a control against bias that was documented before the verdict campaign was run, and it directly answers the objection that the best option might have been picked after seeing the results.

### 7.5.3 What the policy does with speed control

<img src="../figures/auto/fig_7_5_ppo2d_action_distribution.png" alt="Figure 7.5 — Distribution of the two-dimensional raw action." width="640"/>

*Figure 7.5 — Distribution of the raw action at the start and at the end of training, one panel per dimension. In steering, the early all-or-nothing command goes away (36.9 % → 7.1 % of saturated samples). In throttle, the change goes the other way, towards saturation (48.2 % → 89.6 %): the policy learns to ask for the ceiling almost all the time.*

Figure 7.5 supports a realistic reading of how the policy uses its speed control: it uses it to set the overall speed, not to follow a speed profile. There is some modulation, and it happens in the right places. The 8.3 % of steps with reduced throttle are concentrated at high curvature and rise to 35.6 % at the tightest apex. But the effect is very small: the throttle drops to 0.81 and the speed only falls from 0.218 to 0.216 m/s. The policy enters the tightest curves at almost the ceiling speed. This small detail explains a result in Chapter 8: the cage's speed rule never fires during the whole campaign.

### 7.5.4 Approval before the campaign

Before running the verdict campaign, the policy had to pass a preflight check tied by cryptographic identifier to its checkpoint and configuration. The check makes sure that the cage's measurement interface (the lane estimator and its heading reading) works as it should: real heading failures are detected, there are zero false positives on safe, centred cycles, and the delay stays within limits. The check passed all seven of its tests, and that is what allowed the campaign to start.

The order matters for the method. The policy is chosen by nominal evaluation, the instrumentation is checked separately and tied by *hash*, and only then is the campaign run. None of these three steps can be done in a different order without weakening the evidence.

## 7.6 Summary

This chapter gives three results that the next one builds on. First, a camera policy that drives well exists, and it has been compared with a classical method. Second, the training curve does not tell how the policy behaves. The choice has to be made by closed-loop driving, and when that criterion was applied to the reference policy, it rejected exactly the checkpoint that the reward would have picked. Third, the reference policy controls speed but uses that control to set the overall speed and not to adjust it along the track, which affects which cage rules actually get tested.

Chapter 8 runs that policy through the scenario campaign and produces the verdict.
