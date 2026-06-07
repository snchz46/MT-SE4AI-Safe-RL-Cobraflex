# Experiments

Experimental data and analysis scripts.

## Organisation

- `sim/` — simulation experiments. One subdirectory per `(scenario, mode)` combination, with one subdirectory per run.
- `physical/` — physical experiments on the CobraFlex 1:14 platform.
- `analysis/` — scripts and notebooks that compute metrics and produce figures.

## Naming convention

```
experiments/sim/SC-NOM-01_enforcement/run_007/
    state_obs.csv
    raw_action.csv
    safe_action.csv
    cage_status.csv
    metadata.json
```

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

## Phase status

- **Phases 2–3 (done):** F2 PD-baseline closed-loop runs (`sim/runs/ros_run_*`) and the F3
  PPO training (`sim/training/ppo_train_*`) + evaluation (`sim/runs/rl_eval_*`) cycles are
  logged here.
- **Phase 4 (in progress):** the scenario-validation campaign is planned at ~900 runs across
  the 11 scenarios × modes; the Gazebo executor (`tools/run_campaign.py::execute_run`) is
  still a stub on the Ubuntu host, so no campaign runs are accumulated yet.
- **Phase 5 (planned):** physical CobraFlex experiments, ~30–60 runs across selected
  scenarios; `physical/runs/` is currently empty.

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
