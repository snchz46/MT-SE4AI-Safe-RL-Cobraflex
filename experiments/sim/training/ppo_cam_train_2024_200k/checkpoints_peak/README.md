# checkpoints_peak — best-checkpoint candidates (run ppo_cam_train_2024_200k)

The 200k run suffered a non-recovering late-training policy collapse
(ep_rew 288 @ 139k -> 56 @ 200k; approx_kl spike 0.227 at the 156k onset).
These step-checkpoints were copied out of the rotating
`policy/checkpoints/cobraflex_ppo_lane_*_steps.zip` scratch (shared prefix,
overwritten by any later run) before they could be lost:

- `cobraflex_ppo_cam_lane_2024_139k_peak.zip`  — ep_rew_mean peak (288.5 @ 139264)
- `cobraflex_ppo_cam_lane_2024_155k_prefall.zip` — last row before the collapse (279.1 @ 155648)

Binaries are gitignored (repo convention); integrity + provenance via
`SHA256SUMS` and the run's `metadata.json`/`learning_curve.csv`. The closing
eval (`experiments/sim/runs/rl_cam_eval_2024_*`) decides final-vs-peak
selection; the decision and criterion are recorded in docs/CHANGELOG.md.
