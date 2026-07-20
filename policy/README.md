# Policy

Reinforcement learning policy: PD baseline, PPO/SAC training artifacts and the
checkpoint registry. **Status reconciled 2026-07-20.** The live training/eval code moved to the ROS2 package
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
- `tests/` — the pure-Python suite covering the whole
  `cobraflex_rl` package (reward, cage bridge, camera/CV perception, scenario
  + campaign spine). The latest fully green repo-host baseline is **517 passed**
  (15.07.2026). A 20.07 collection attempt on this Windows/Python 3.14 host
  stopped at the ROS/ament-dependent `test_eval_policy_2d.py` import because
  `ament_index_python` is unavailable; see `docs/15` §6. Test-to-artifact map:
  `docs/15_implementation_inventory.md` §6.2.

## Algorithm

PPO via Stable-Baselines3 (decisions D-14/D-15). F-track: `MlpPolicy` over the
6-dim state vector. Track 'E': `CnnPolicy` (NatureCNN) over 4 stacked 84×84
grayscale camera frames. Since 15.07.2026 the trainer also builds **SAC** from
the same entry point, selected by the training config's `algorithm: ppo|sac`
key (D-60; posterior algorithm comparison — every thesis verdict is PPO).
The completed Gazebo study includes SAC auto-entropy and fixed
`ent_coef = 0.005` runs, a 100k→200k replay-buffer probe, and tuned 2-D SAC.
These change the optimiser/data regime, not the environment, reward, cage or
metrics. Full deep dive (architecture, hyperparameter provenance, Gazebo wiring):
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
(reward v1.2, docs/10 §5); the config-gated 2-D extension applies the same
principle to raw `throttle_delta` and adds `stall_penalty`.

## Status

F3 closed (main run `ppo_train_2024_200k`, seed study N=5). Track 'E' closed
at G4 (E-main `cobraflex_ppo_newcam_complex_b_2024_297k_peak`, GE4-V2 verdict
of record, PPO 1-D at fixed 0.20 m/s).

Post-G4 evidence is separate:

- **PPO camera 1-D N=5:** 3/5 constraint-respecting; seed 666 cage-dependent;
  seed 23 cage–CV conflict. This characterises training variance and is not
  pooled into GE4.
- **Gazebo PPO 2-D:** the historical 0.5 m/s full-authority run peaked at 654.4
  at 510k and drove competently in monitoring; no full-horizon enforcement run
  is claimed, and the result is not attributed to the current 0.25 m/s configs.
- **Gazebo SAC 1-D:** auto peak 720 at 89k; fixed-entropy peak 722.5 at 83k.
  The entfix N=3 study was 3/3 enforcement-clean and rescued PPO-hard seed 666;
  paired nominal enforcement+monitoring is complete for 2/2 evaluated pairs,
  with seed 42 monitoring pending. A 200k replay buffer held reward through 180k;
  this bounded seed-2024 probe supports replay eviction as the explanation for
  the slower decay, without establishing transfer to 2-D or a longer horizon.
- **Gazebo SAC 2-D:** fixed entropy produced the first full-horizon enforcement
  runs (seeds 2024 and 42, zero emergencies). Current configs cap authority at
  **0.25 m/s**. A **0.22 m/s** eval probe removed one speed-margin conflict but
  did not remove a D-43 CV heading over-read.
- **SAC SC-PERT subset:** two seeds, 200 cells combined; enforcement 100/100
  PASS versus monitoring 68/100. Subset roll-ups are globally `INCOMPLETE` by
  construction and are not verdict campaigns.
- **Isaac:** independent PPO 2-D retrains under the separate **0.5 m/s**
  full-authority contract (D-49/D-50, `docs/13`–`14`). Gazebo checkpoints do
  not transfer.

The 2-D action makes SR-009's stall arm well-posed, but the dedicated two-arm
SC-PERT-03 run remains pending; no new SR-009 closure is claimed. Its execution
surface is now fixed before training: λ=4.0, 50k one-shot continuation,
`M-P6 > 50.0` (percentage scale), 20 runs per arm/mode, and a manifest that
hashes parent/derived checkpoints/configs plus VecNormalize/protocol/scenario.

The live config tree also contains
`train_sac_camera_2d_tuned_entfix_margin022.yaml`, a **preregistered but
untrained** fresh-policy contract. It bounds the parent at 75k and uses a 150k
buffer, so the parent plus the fixed 50k SC-PERT continuation (125k total)
remain resident without replay eviction. It leaves 0.03 m/s below the canonical C-04
curve ceiling, fingerprints that map into new SB3 checkpoints, rejects all
historical 0.25 checkpoints, and requires a checkpoint-bound D-43 preflight
before campaign execution. This is qualification infrastructure, not new
training evidence.

## Configuration provenance note

The live config tree contains the PPO camera configs plus
`train_sac_camera{,_entfix}.yaml` and
`train_sac_camera_2d{,_tuned,_tuned_entfix}.yaml`. Seed-specific and buffer-probe
configs are archived beside later run artifacts. The five named
`*_pilot25k.yaml` files referenced by the 15.07 pilot metadata are **not** in the
current config tree; the metadata/hash preserves the evidence identity, but exact
reproduction requires restoring hash-matched snapshots. Their contents must not
be reconstructed by guesswork.
