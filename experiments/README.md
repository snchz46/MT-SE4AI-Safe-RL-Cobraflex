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
- **Phase 4 (in progress):** the Gazebo executor (`tools/run_campaign.py::execute_run`) is
  **live** — it drives `eval_scenario_batch.launch.py` per (scenario, mode, rep) cell. A
  **pilot** frontier cage-efficacy campaign has run (`sim/campaign_frontier/`, rep00, seeds
  123 & 2024). The remaining F4 run is the full verdict-bearing campaign (~1100 runs across
  the 11 NOM/EDGE/PERT scenarios × modes) that fills the per-SR sim verdicts in `docs/07`.
  See "Running the F4 campaign" below.
- **Phase 5 (planned):** physical CobraFlex experiments, ~30–60 runs across selected
  scenarios; `physical/runs/` is currently empty.

## Running the F4 campaign (Ubuntu + Jazzy)

The campaign executor needs the ROS2 + Gazebo host — it cannot run on the figure/Windows
host. Pre-flight verified 08.06.2026: launch arg contract matches `execute_run`, `eval_policy`
entry point registered, all 17 scenarios on `lane_following_oval.world`, checkpoints present,
dry-run D-29-feasible, and the pilot frontier campaign already produced valid runs.

**1. Build & source the workspace** (once per shell):

```bash
source /opt/ros/jazzy/setup.bash
cd <repo>
pip install -e .                     # so the nodes + runner can import `cage`
rosdep install --from-paths src --ignore-src -r -y
./scripts/download_meshes.sh         # 87 MB lidar mesh (gitignored)
colcon build --symlink-install
source install/setup.bash
```

**2. Validate the plan** (no Gazebo, runs anywhere) — every SR must read `[OK]`:

```bash
python tools/run_campaign.py --seeds 2024 --dry-run
```

**3. Smoke-test the host end-to-end** before committing hours (expect 2 runs PASS/FAIL, *not*
ERROR, and a `summary.json` under `runs/<run_id>/`):

```bash
python tools/run_campaign.py --scenarios SC-NOM-01 --seeds 2024 \
    --modes enforcement --reps 2 --out experiments/sim/campaign
```

**3b. Smoke-test the newly-wired perturbations** before trusting them — they are unit-tested but
**not yet Gazebo-validated**. Confirm the stressor actually fires: each `summary.json` carries a
`"perturbation"` block recording the level, and the perturbed runs should differ from nominal
(SC-PERT-02 → more cage activity / different |ey|; SC-PERT-01 → noisy intervention pattern):

```bash
python tools/run_campaign.py --scenarios SC-PERT-01,SC-PERT-02,SC-EDGE-03 --seeds 2024 \
    --modes enforcement --reps 2 --out experiments/sim/campaign
```

**4a. Verdict-bearing campaign — Gazebo-proven scenarios** (the initial-condition scenarios;
fills the SR verdicts these cover). Once 3b passes on the host, add
`SC-PERT-01,SC-PERT-02,SC-EDGE-03` to `--scenarios`:

```bash
python tools/run_campaign.py \
  --scenarios SC-NOM-01,SC-NOM-02,SC-NOM-03,SC-EDGE-01,SC-EDGE-02,SC-EDGE-04 \
  --seeds 2024 --modes enforcement,monitoring \
  --resume --out experiments/sim/campaign
```

> **Runtime perturbations now wired (validate on the host first) — SC-PERT-01, SC-PERT-02,
> SC-EDGE-03.** Observation noise, actuation latency and the throttle pulse are injected from the
> `perturbations:` block (unit-tested; **not yet Gazebo-validated** — smoke-test per step 3b
> before adding to 4a). **Still unwired (different mechanisms): SC-EDGE-05** (initial-condition
> grid) and **SC-PERT-03** (pre-run stall-variant checkpoint) — see the coverage note below.

**4b. Frontier cage-efficacy study** — the D-35 paired contrast (6 × 25 × 2 modes × 2 seeds);
auto-renders the figures on exit:

```bash
python tools/run_campaign.py \
  --scenarios SC-FRONT-01,SC-FRONT-02,SC-FRONT-03,SC-FRONT-04,SC-FRONT-05,SC-FRONT-06 \
  --seeds 2024,123 --modes enforcement,monitoring \
  --resume --out experiments/sim/campaign_frontier
```

**Before you start — known limits:**

- **Scenario execution coverage.** The runtime perturbation injection
  (`scenario_perturbations.py` → `scenario_runner` → `gazebo_lane_env`) reads the
  `perturbations:` block and applies observation noise, actuation latency and the throttle pulse;
  the verdict is still measured on the *true* pose. Status:
  - **Proven (Gazebo):** SC-NOM-01/02/03, SC-EDGE-01/02/04, SC-FRONT-01..06.
  - **Wired, pending Gazebo smoke-test (step 3b):** SC-PERT-01 (noise), SC-PERT-02 (latency),
    SC-EDGE-03 (throttle pulse — but the fixed-speed actuation caps speed at `fixed_speed`
    ≈ 0.2 m/s < `v_max` 0.5 m/s, so the override reaches C-04 yet drives little real over-speed;
    SR-004's strength here is limited until variable-speed actuation is added).
  - **Still unwired (different mechanisms):** SC-EDGE-05 (initial-condition grid expansion in the
    runner) and SC-PERT-03 (a fine-tuned stall-variant checkpoint + two-arm eval).
  - **`--dry-run` "D-29-feasible" counts runs, not whether a stressor fires** — validate the
    perturbed scenarios per 3b before trusting their verdicts.
  - **Latency granularity:** at 10 Hz control, `actuation_latency` resolves in whole control
    periods — 100 ms = 1 step, 50 ms is sub-cycle (≈ 0). Documented in `scenario_perturbations`.
- **Serial + long.** Runs are strictly serial (one Gazebo at a time); budget tens of hours for
  4a. `--resume` skips cells whose `summary.json` already exists, so it survives interruptions;
  `--settle 3` + per-run `GZ_PARTITION` + orphan-`gz` reaping keep memory bounded. Run each
  invocation under `--dry-run` first to see its exact run count.
- **RL only.** `execute_run` drives the PPO policy; the PD-baseline arm is **not** wired
  (`--controllers pd` raises `NotImplementedError`). The PD comparison uses the existing F2/F3
  eval runs (`sim/runs/ros_run_*`, `rl_eval_*`), not this campaign.
- **Seed split is deliberate.** The verdict campaign (4a) uses only seed 2024 (the main policy);
  seed 123 (the cage-dependent outlier) appears **only** in the frontier contrast (4b), per D-35.
- **Figures.** If matplotlib is absent on the ROS host, 4b prints the `plot_frontier.py` command
  to render `fig_frontier_*` on the figure host instead (see `tools/README.md`).

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
