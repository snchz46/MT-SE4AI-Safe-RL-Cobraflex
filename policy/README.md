# Policy

Reinforcement learning policy: PD baseline, PPO training artifacts and the
checkpoint registry. **The live training/eval code moved to the ROS2 package
`src/cobraflex_rl/`** (this directory keeps the pure-Python pieces + evidence).

## Files

- `baseline_pd.py` — pure-Python PD controller (F2 baseline; gains in
  `baseline_pd.yaml`). The known-competent control arm that validated the
  F2 pipeline and calibrated the reward (docs/10 §7).
- `train.py` — thin historical shim; the real trainer is
  `src/cobraflex_rl/cobraflex_rl/train_ppo.py`
  (`ros2 launch cobraflex_rl train.launch.py`). The env is
  `cobraflex_rl/gazebo_lane_env.py`, the reward `cobraflex_rl/rewards.py`.
- `checkpoints/` — trained checkpoints (`.zip`, gitignored binaries) +
  `checkpoint_registry.csv` (seed, steps, timestamp, git commit, cage-YAML
  hash per row — the reproducibility ledger).
- `tests/` — the 357-test pure-Python suite covering the whole
  `cobraflex_rl` package (reward, cage bridge, camera/CV perception, scenario
  + campaign spine). Test-to-artifact map: `docs/15_implementation_inventory.md` §6.2.

## Algorithm

PPO via Stable-Baselines3 (decisions D-14/D-15). F-track: `MlpPolicy` over the
6-dim state vector. Track 'E': `CnnPolicy` (NatureCNN) over 4 stacked 84×84
grayscale camera frames. Since 15.07.2026 the trainer also builds **SAC** from
the same entry point, selected by the training config's `algorithm: ppo|sac`
key (D-60; posterior algorithm-comparison groundwork — every thesis verdict is
PPO). Full deep dive (architecture, hyperparameter provenance, Gazebo wiring):
`docs/16_defense_compendium.md` §3; training operations (+ the algorithm
switch, `docs/11_camera_rl_training.md` §4.2).

## Training Specification

Normative source: Training Specification, manuscript Chapter 7 (§7.2–§7.5).
Supporting rationale: `docs/09_environment_design.md` (env) and
`docs/10_reward_function.md` (reward v1.2).

## Cage during training

The cage is active in enforcement mode during training, invoked **in-process**
with the same `SafetyCageNode` class and `cage.yaml` as deployment (D-34 /
TS-01). Cage interventions are never penalised by the reward; the one
deliberate exception is the smoothness term on the *raw* steering delta
(reward v1.2, docs/10 §5).

## Status

F3 closed (main run `ppo_train_2024_200k`, seed study N=5). Track 'E' closed
at G4 (E-main `cobraflex_ppo_newcam_complex_b_2024_297k_peak`, GE4-V2 verdict
of record). Posterior: Isaac 2-D retrain (D-49/D-50, `docs/13`–`14`).
