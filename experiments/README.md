# Experiments

Experimental data and analysis scripts.

> **Status (2026-07).** The evidence of record is the **track-'E' end-to-end camera
> campaign** `sim/campaign_e_v2/` (GE4-V2, 1970 runs, 28.06.2026; G4 closed
> 02.07.2026). The F-track state-vector campaigns (`sim/campaign/`,
> `sim/campaign_frontier/`) are **frozen as the ground-truth baseline** — the
> control arm for "what does camera perception cost" — and are not re-run.
> Next phase: Isaac Sim / sim-to-real (`sim/eval_isaac/`, docs/13–14).

## Organisation

- `sim/runs/` — single evaluation runs: F2 PD closed-loop (`ros_run_*`), F3 state
  evals (`rl_eval_*`), track-'E' camera evals (`rl_cam_eval_*`, `rl_newcam_eval_*`),
  CV-estimator oracle validation (`cv_estimator_val_*`).
- `sim/training/` — training runs with metadata + learning curves (`ppo_train_*`
  F-track; `ppo_newcam_*` track 'E'; `ppo_gz2d_*` Gazebo 2-D posterior;
  `{ppo,sac}_cam_pilot25k_*` + `pilot25k_ppo_vs_sac_*` the D-60 algorithm-switch
  verification pair; peak checkpoints under `checkpoints_peak/`).
- `sim/eval_gz2d/` — Gazebo 2-D (steer+throttle) posterior-baseline evals
  (`rl_gz2d_eval_*`, D-49/D-59; not GE4 evidence).
- `sim/campaign_e_v2/` — **GE4-V2, the verdict of record** (track 'E', complex_b
  297k E-main): `campaign_report.json` (per-scenario/per-SR/global roll-up),
  `campaign_runs.csv`, `failure_mode_breakdown.json` (failure classes + pass-mode
  split: emergency-stop pass vs overcame-the-perturbation pass) and figures.
- `sim/campaign_e_297k/` — GE4-V1 (superseded by V2: ruta-1 IC clip, D-45 scoring).
- `sim/campaign_e/` — historical 139k camera campaign (availability-cost reading).
- `sim/campaign/` — **F4 verdict campaign, frozen baseline** (1260 runs, seed 2024,
  global `SATISFIED`, cage latent in-ODD).
- `sim/campaign_frontier/` — F4 out-of-ODD cage-efficacy contrast (D-35).
- `sim/tracks/` — track sources (complex_b centerlines etc.).
- `sim/eval_isaac/` — Isaac Sim posterior-track evals (D-44/D-50; not GE4 evidence).
- `physical/` — physical CobraFlex experiments (F5, pending).
- `calibration/`, `odd_inspection/` — M-1/M-2 calibration data, ODD TBD closures.
- `analysis/` — metric/figure scripts and notebooks.

## Naming convention

Campaign cells are written by `tools/run_campaign.py` as one directory per
(scenario, mode, rep):

```
experiments/sim/campaign_e_v2/runs/camp_pert04_rl_seed2024_enforcement_rep00/
    summary.json          # per-run metrics + three-valued verdict + criterion clauses
    cage_status.csv       # per-step trace (ey, epsi, actions, interventions, emergency)
    metadata.json
```

Single evals under `sim/runs/<run_id>/` follow the same file schema.

## metadata.json schema

Every run produces a `metadata.json` with at minimum:

```json
{
    "run_id": "run_007",
    "scenario_id": "SC-NOM-01",
    "mode": "enforcement",
    "timestamp_iso": "...",
    "duration_s": 30.0,
    "git_commit": "...",
    "cage_yaml_hash": "...",
    "policy_checkpoint": "...",
    "policy_checkpoint_hash": "...",
    "scenario_yaml_hash": "...",
    "seed": 42,
    "platform": "sim" or "cobraflex",
    "battery_voltage_v": null,
    "ambient_temperature_c": null,
    "status": "completed" or "failed_*"
}
```

The `metadata.json` is what makes a run reproducible: with the same git commit, same hashes, same seed, the run can be reproduced.

Training runs (`sim/training/<run_id>/`) additionally record the training-config
provenance: `train_config` + `train_config_hash` (sha256 of the train YAML),
the `action` contract (`{}` = the frozen 1-D steering-only contract; the D-50/D-59
2-D runs record `steer_throttle` + `max_speed_mps`/`throttle_deadband`), the
`reward` weights and the PPO `hyperparameters`. Runs recorded before 07.07.2026
lack the `train_config*`/`action`/`reward` keys.

## Phase status

- **F2–F4 (closed, frozen baseline):** PD pipeline validation, PPO state-vector
  training (seed 2024 main, multi-seed N=5) and the F4 verdict campaign
  (`sim/campaign/`, global `SATISFIED`, 2026-06-10). Not re-run; serves as the
  control arm.
- **Track 'E' (closed, verdict of record):** camera training on complex_b
  (`ppo_newcam_complex_b_2024_1M`, 297k peak) and the GE4-V2 campaign
  (`sim/campaign_e_v2/`, 1970 runs, 0 errors). Global `NOT SATISFIED` *literal*
  — blocking SR-002/003 on the oval-legacy recovery-time clause only, Satisfied
  on their own criterion (D-47); no SR-CL-A safety predicate breached. G4 closed
  02.07.2026. See `docs/11` §8 and `docs/07`.
- **Isaac / sim-to-real (open, posterior):** URDF import, in-process RL training,
  2-D action retrain (D-49/D-50). Does not reopen G4.
- **F5 (planned):** physical CobraFlex experiments; `physical/runs/` empty.

## Running a campaign (Ubuntu + Jazzy host)

The executor drives Gazebo and needs the ROS2 host (build/source per
`CLAUDE.md`). Validate any invocation with `--dry-run` first (pure plan + D-29
feasibility, runs anywhere).

**Track-'E' camera campaign** (the GE4-V2 form of record):

```bash
python tools/run_campaign.py \
  --scenario-dir scenarios_complex_b \
  --model-path experiments/sim/training/ppo_newcam_complex_b_2024_1M/checkpoints_peak/cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip \
  --train-config $(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config/train_ppo_camera.yaml \
  --seeds 2024 --modes enforcement,monitoring \
  --resume --out experiments/sim/campaign_e_v2
```

Post-hoc analysis (pure Python, any host):

```bash
python tools/campaign_e_failure_modes.py --campaign-dir experiments/sim/campaign_e_v2
```

**F-track baseline form** (historical; kept for reproducibility of
`sim/campaign/`): same runner without `--scenario-dir`/`--model-path`, oval
scenario library `scenarios/`.

Operational notes (both forms):

- **Serial + long.** One Gazebo at a time; `--resume` skips completed cells,
  `--settle` + per-run `GZ_PARTITION` + orphan-`gz` reaping keep memory bounded.
- **Camera runs are real-time-bound** (sim clock factor 1): budget accordingly
  (~40 s scenarios × ~2000 cells for the full E matrix).
- **RL only.** The PD arm is not wired into the runner; PD evidence lives in the
  F2/F3 runs under `sim/runs/`.
- **Perturbation status:** all scenario mechanisms of the E library are wired and
  Gazebo-validated (runtime visual degradation, world variants, IC grids;
  SC-PERT-03's two-arm stall design is recorded indeterminate per D-38/D-49).

## Data not in version control

The raw logs (CSV files) are too large for version control. They live under `*/raw_logs/` directories which are in `.gitignore`. Only the aggregated metric tables, plots and final analysis are tracked.

## Reproducibility

Reproducing any run requires:

1. `git checkout` of the recorded `git_commit`.
2. The same `cage.yaml` (verified by hash).
3. The same scenario YAML (verified by hash).
4. The same policy checkpoint (verified by hash).
5. The same seed.

The reproducibility check is part of every Gate review.
