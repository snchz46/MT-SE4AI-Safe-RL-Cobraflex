# Appendix H — Training specification: detail

## H.1 Reward function

The reward is identical on both tracks and is computed over the
**ground-truth** state plus progress, and is agnostic to the observation:

```text
r = w_fwd · max(progress, 0)
  - w_ey  · |ey|
  - w_eps · |epsi|
  - w_ds  · |Δsteering|
  - w_term · [terminated_off_road]
```

where `progress` is the normalised advance along the centre
line, `Δsteering` is the change in the raw steering of the policy
(not the post-cage one; §7.2.2), and `[terminated_off_road]` is 1 only if the
episode ends by leaving the road (not by a C-05 emergency; §7.2.4).
The nominal weights (subject to experimental tuning) are:

| Parameter | Value | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Rewards real progress (≈1.0/step at cruise) |
| `w_ey` (lateral_error) | 2.5 | Main penalty: lateral offset |
| `w_eps` (heading_error) | 0.75 | Secondary penalty: heading |
| `w_ds` (steer_delta) | 0.20 | Actuation smoothness (over the raw Δsteering, v1.2; §7.2.2) |
| `w_term` (termination) | 25.0 | Discourages leaving the road |

The forward term uses normalised progress (not speed): since the
speed is fixed, a term `w_fwd·speed` would be a constant that does not
discriminate between behaviours and left `explained_variance ≈ 0` (F3 review,
first run). The high termination penalty (25.0) prioritises staying on the
**road**; only the road departure applies it — the C-05
emergency ends the episode with no penalty (the intervention of the cage is dynamics, not
punishment; D-34, §7.2.4). The weights are `[provisional, M-P1..M-P4]`; detail
in `docs/10_reward_function.md`.

## H.2 Hyperparameters

The table lists the complete effective configuration. The E-main column is
the one of the camera run `ppo_newcam_complex_b_2024_1M`; the F baseline is the one of the
state run `ppo_train_2024_200k`.

| Parameter | E-main (camera) | Baseline (F, state) | Source / note |
| --- | --- | --- | --- |
| `policy` | CnnPolicy | MlpPolicy | policy network |
| `total_timesteps` | 1,000,000 (planned; stopped at ≈662k) | 200,000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴, linear anneal | 3×10⁻⁴ constant | E: `lr_schedule: linear` |
| `target_kl` | 0.5 | — (no brake) | E: trust region brake (§7.3) |
| `normalize_reward` | True (`VecNormalize`) | False | E: stabilises the critic (§7.3) |
| `clip_range_vf` | 0.2 | null | E: value clip over the normalised reward |
| `gamma` | 0.99 | 0.99 | = SB3 default |
| `n_steps` | 1,024 | 1,024 | ≈ 1 episode |
| `batch_size` | 64 | 64 | = SB3 default |
| `n_epochs` | 10 | 10 | SB3 default |
| `gae_lambda` | 0.95 | 0.95 | SB3 default |
| `clip_range` | 0.2 | 0.2 | SB3 default |
| `ent_coef` | 0.0 | 0.0 | no entropy bonus |
| `vf_coef` | 0.5 | 0.5 | SB3 default |
| `max_grad_norm` | 0.5 | 0.5 | SB3 default |
| `device` | auto (CUDA if present) | cpu | E: the CNN benefits from a GPU |

The four stability levers of the E-main run (`target_kl`, linear LR
anneal, `VecNormalize(norm_reward)` and `clip_range_vf`) do not exist in the
F baseline: they were added after observing that PPO over a CNN with visual
randomization is markedly less stable than over the state vector (§7.3).
`norm_obs` is kept False, so that evaluation/inference is not
affected and `ep_rew_mean` in the curve stays raw (comparable with the
baseline). The camera budget is ≥ 1M steps (D-41 accepts the higher
data demand of the end-to-end approach); a pilot of ~20k validates the loop
before committing the budget.

## H.3 Comparative study of algorithms and checkpoints

Chain run → checkpoint → evaluation of the later study. All the evaluation
values come from the nominal scenario with the randomization switched off. The peak indicated
belongs to the training curve and does not always coincide with the checkpoint
cadence, so the final selection is resolved by closed-loop evaluation.

| Action · configuration | Training evidence | Checkpoint evaluated | SC-NOM-01, enforcement | SC-NOM-01, monitoring |
| --- | --- | --- | --- | --- |
| **1-D**, SAC `auto`, seed 2024 · `sac_newcam_complex_b_2024_1M` | peak 720.0 @ 89,089; manual stop at 307,201 of the 1M planned | 75k (`58631022…`) | 5.12 laps; 19.8 mm; 0 emerg.; 48.3 % C-06 | 5.13 laps; 23.3 mm; 0 emerg. |
| **1-D**, `ent_coef=0.005`, seed 2024 · `sac_newcam_entfix_complex_b_2024_1M` | peak 722.5 @ 82,945; without the abrupt collapse; stop at 260,097 | 75k (`b74505ac…`) | 5.04 laps; 21.6 mm; 0 emerg.; 9.1 % C-06 | 5.04 laps; 21.6 mm; 0 emerg. |
| **1-D**, `ent_coef=0.005`, seed 42 · `sac_newcam_entfix_complex_b_42_120k` | peak 744.3 @ 87,041; replica bounded to 120,833 | 75k (`4d09e43c…`) | 4.63 laps; **12.3 mm**; 0 emerg.; **2.3 % C-06** | **pending: no nominal `_mon` run exists** |
| **1-D**, `ent_coef=0.005`, seed 666 · `sac_newcam_entfix_complex_b_666_120k` | peak 606.9 @ 80,897; replica bounded to 120,833 | 75k (`18c80fce…`) | 5.00 laps; 14.0 mm; 0 emerg.; 5.3 % C-06 | 5.00 laps; 14.0 mm; 0 emerg.; 6.2 % C-06 counterfactual |
| **1-D**, `ent_coef=0.005`, buffer 200k, seed 2024 · `sac_newcam_entfix_buf200_2024_180k` | sustained band 690–745; peak 744.7 @ 155,649; stop at 180,225 | 150k (`a5c5f3c4…`) | 4.94 laps; 26.9 mm; 0 emerg.; 14.4 % C-06 | not executed |
| **2-D**, SAC `auto`, seed 2024 · `sac_gz2d_tuned_complex_b_2024_1M` | collapse–recovery cycles; peak 527.0 @ 153,601; stop at 250,881 | edge 175k (`e8934d51…`) | 3.45 laps; 34.8 mm; 1 C-05 stop | 4.31 laps; 32.3 mm; 0 emerg. |
| **2-D**, `ent_coef=0.005`, seed 2024 · `sac_gz2d_tuned_entfix_2024_1M` | peak 558.7 @ 77,825; rise without abrupt cycles; stop at 176,129 | 75k (`b76724c7…`) | **4.32 laps; 17.1 mm; 0 emerg.**; 17.1 % C-06 | 4.31 laps; 16.3 mm; 0 emerg. |
| **2-D**, `ent_coef=0.005`, seed 42 · `sac_gz2d_tuned_entfix_42_120k` | peak 270.9 @ 47,105; replica bounded to 120,833 | 50k (`cbde3836…`) | **4.97 laps; 18.2 mm; 0 emerg.**; 46.4 % C-06 | 4.84 laps; 22.6 mm; 39 steps with a counterfactual C-05 trigger |

*Chain run → checkpoint → evaluation of the later SAC
study. The intervention percentages in monitoring are counterfactual
activations: they are logged, but the action of the cage is not applied.*
