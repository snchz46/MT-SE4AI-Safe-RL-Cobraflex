# Experiments

Experimental data and analysis scripts.

> **Status (2026-09-01 — the evidence base is final).** The **verdict of record** is
> `sim/campaign_2d_ppo550k/` — the 2-D PPO camera policy at cap 0.22, checkpoint 550k
> (1890 runs, 31.07.2026, **D-69**), the last simulation campaign before physical
> deployment. **`sim/campaign_e_v2/` (GE4-V2, 1970 runs, 28.06.2026) remains the frozen
> G4 gate record** — G4 closed 02.07.2026 — and is **not** re-scored; D-69 re-pointed the
> verdict of record on top of it (D-67 reclassifies everything earlier as development
> history). The F-track state-vector campaigns (`sim/campaign/`, `sim/campaign_frontier/`)
> are **frozen as the ground-truth baseline** — the control arm for "what does camera
> perception cost" — and are not re-run. Post-G4 evidence also covers Gazebo PPO/SAC camera
> policies in 1-D and 2-D and the separate Isaac 2-D retrains; these are posterior studies
> and do **not** replace or reopen GE4.
>
> **Phase 5 (`physical/`) is closed and is posterior evidence throughout.** It re-scores no
> gate and does not touch the D-69 verdict. `verdict_phys` is open by design: no scenario
> has ever been scored on hardware, every physical run was in `monitoring`, and the cage has
> never modified an action on hardware. Consolidated ledger: **docs/17 §14**.

## Organisation

- `sim/runs/` — single evaluation runs: F2 PD closed-loop (`ros_run_*`), F3 state
  evals (`rl_eval_*`), track-'E' camera evals (`rl_cam_eval_*`, `rl_newcam_eval_*`),
  SAC 1-D/2-D evals (`rl_sac*`), and CV-estimator oracle validation
  (`cv_estimator_val_*`).
- `sim/training/` — training runs with metadata + learning curves (`ppo_train_*`
  F-track; `ppo_newcam_*` track 'E'; `ppo_gz2d_*` Gazebo 2-D posterior;
  `{ppo,sac}_cam_pilot25k_*` / `{ppo,sac}_gz2d_pilot25k_*` + `pilot25k_ppo_vs_sac_*`
  the D-60 verification battery; `sac_newcam_*` the 1-D SAC auto/entfix/seed/buffer
  studies; `sac_gz2d_tuned_*` the 2-D SAC studies; peak checkpoints under
  `checkpoints_peak/`).
- `sim/eval_gz2d/` — Gazebo 2-D (steer+throttle) posterior-baseline evals
  (`rl_gz2d_eval_*`, D-49/D-59; not GE4 evidence) plus derived D-43 preflight
  reports. `d43_preflight_reference_gazebo_2d.json` compares four enforcement
  traces: both entfix checkpoints pass individually, while auto-175k at 0.25
  and its 0.22 cap probe block; its aggregate verdict is therefore `BLOCKED`.
  `d43_underread_ge4v2_edge02.json` quantifies 3573 under-read cycles in 27/60
  GE4-V2 SC-EDGE-02 runs, but is `INVALID` as a new-campaign authorisation
  because the reconstructed E-main metadata lacks `train_config_hash`.
- `sim/campaign_2d_ppo550k/` — **the VERDICT OF RECORD** (D-69, 31.07.2026): the 2-D
  PPO camera policy at cap 0.22, checkpoint 550k, **1890 runs** (27 complex_b scenarios
  × {enf, mon}, seed 2024, 0 errors; SC-PERT-03 excluded by protocol, D-64). Global
  `NOT SATISFIED` *literal*, blocking SR-002/003 only through SC-EDGE-01's recovery
  clause (D-47 verbatim); **0 in-ODD road-edge contacts in enforcement** against 60 by
  the bare policy, 56 out-of-ODD. Narrative: `CAMPAIGN_2D_PPO550K_ANALYSIS.md`.
- `sim/campaign_e_v2/` — **GE4-V2, the frozen G4 gate record** (track 'E', complex_b
  297k E-main; 1970 runs, 28.06.2026). Superseded as *verdict of record* by the 2-D
  campaign above and **not re-scored**. `campaign_report.json` (per-scenario/per-SR/global
  roll-up), `campaign_runs.csv`, `failure_mode_breakdown.json` (failure classes +
  pass-mode split: emergency-stop pass vs overcame-the-perturbation pass) and figures.
- `sim/campaign_2d_margin022/` — the first full 2-D verdict campaign (SAC 75k, D-65):
  `NOT SATISFIED` literal, 0 in-ODD road-edge contacts against the bare policy's 98.
  A finding-with-fix, not a verdict — it is what motivated D-66.
- `sim/campaign_v2/` — the same 27 × 2 × seed-2024 matrix re-run on the v2 1650k
  deployment checkpoint. **Posterior; it does not re-score G4** and was not a
  prerequisite for driving (docs/17 §7.6).
- `sim/campaign_e_297k/` — GE4-V1 (superseded by V2: ruta-1 IC clip, D-45 scoring).
- `sim/campaign_e/` — historical 139k camera campaign (availability-cost reading).
- `sim/campaign/` — **F4 verdict campaign, frozen baseline** (1260 runs, seed 2024,
  global `SATISFIED`, cage latent in-ODD).
- `sim/campaign_frontier/` — F4 out-of-ODD cage-efficacy contrast (D-35).
- `sim/campaign_sac_pert/`, `sim/campaign_sac_pert_s42/` — posterior SAC
  SC-PERT subsets, 100 cells per seed. Each is deliberately a subset, so its
  global roll-up is `INCOMPLETE`; together they provide enforcement 100/100 PASS
  versus monitoring 68/100, not a replacement verdict campaign.
- `sim/tracks/` — track sources (complex_b centerlines etc.).
- `sim/eval_isaac/` — Isaac Sim posterior-track evals (D-44/D-50; not GE4 evidence).
- `physical/` — **Phase-5 physical CobraFlex experiments (closed 01.09.2026)**.
  `physical/runs/` holds 41 run directories: the 26.08 preflight/lap set, the 31.08
  driving laps (`lap0*`), the offset sweep (`lanesweep_*`) and the 31.08 evening
  session (`lap_mon*`). `physical/datasets/` holds the recorded lane imagery and the
  true-position capture (`truepos_*`, `parked_seg*`, `CAPTURE_NOTE_20260831.md`) —
  note that `datasets/*/frames/` and `runs/*/frames/` are **gitignored and live on the
  Jetson**, so a search on this host finds the notes, not the PNGs. All of it is
  **posterior evidence**: `verdict_phys` is open, no scenario was scored on hardware.
  Consolidated ledger: docs/17 §14.
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
    "platform": "sim",
    "battery_voltage_v": null,
    "ambient_temperature_c": null,
    "status": "completed"
}
```

Allowed `platform` values are `sim`, `sim-isaac`, and `cobraflex`; `status` is
`completed`, `interrupted`, or a `failed_*` value.

`metadata.json` provides the reproducibility identity: git commit, hashes and
seed. Exact reproduction additionally requires every referenced artifact and
hash-matched config snapshot to remain resolvable; the pilot limitation below
is a known exception, so metadata alone is not claimed to reconstruct it.

Training runs (`sim/training/<run_id>/`) additionally record the training-config
provenance: `train_config` + `train_config_hash` (sha256 of the train YAML),
the `action` contract (`{}` = the frozen 1-D steering-only contract; the D-50/D-59
2-D runs record `steer_throttle` + `max_speed_mps`/`throttle_deadband`), the
`reward` weights, `algorithm`, and algorithm-specific hyperparameters (PPO or
the SAC block, including explicit `buffer_size` and `ent_coef`). Runs recorded
before 07.07.2026 lack the `train_config*`/`action`/`reward` keys.

**Pilot provenance limitation.** The 15.07 pilot metadata preserves the
recorded config paths and SHA-256 hashes, but five named `*_pilot25k.yaml`
source files are absent from the current `src/cobraflex_rl/config/` tree. Treat
those pilot curves as archived evidence only until matching config snapshots are
restored. Do not infer or recreate the missing YAML contents from filenames.
Later SAC runs do archive exact seed/probe configs beside their evidence (for
example the 200k-buffer config under
`sim/training/sac_newcam_entfix_buf200_2024_180k/`).

## Phase status

- **F2–F4 (closed, frozen baseline):** PD pipeline validation, PPO state-vector
  training (seed 2024 main, multi-seed N=5) and the F4 verdict campaign
  (`sim/campaign/`, global `SATISFIED`, 2026-06-10). Not re-run; serves as the
  control arm.
- **Track 'E' (closed, frozen G4 gate record):** camera training on complex_b
  (`ppo_newcam_complex_b_2024_1M`, 297k peak) and the GE4-V2 campaign
  (`sim/campaign_e_v2/`, 1970 runs, 0 errors). Global `NOT SATISFIED` *literal*
  — blocking SR-002/003 on the oval-legacy recovery-time clause only, Satisfied
  on their own criterion (D-47); no SR-CL-A safety predicate breached. G4 closed
  02.07.2026. See `docs/11` §8 and `docs/07`.
- **2-D PPO trunk (closed, THE VERDICT OF RECORD):** the research trunk since D-67
  (30.07.2026) and the verdict of record since D-69 (31.07.2026) —
  `sim/campaign_2d_ppo550k/`, 1890 runs, 0 errors, the last simulation campaign before
  physical deployment. Same literal verdict through the same clause; **0 in-ODD
  road-edge contacts in enforcement**. Everything earlier is development history
  (D-67), and GE4-V2 above stays the frozen gate record.
- **Gazebo posterior (17–20.07.2026):** PPO/SAC camera comparisons in 1-D and
  2-D. Evidence-bearing 2-D configs cap speed at **0.25 m/s**; a **0.22 m/s**
  eval-only probe removed one zero-margin speed conflict but not the D-43 CV heading
  over-read. SAC fixed entropy (`ent_coef = 0.005`) and the 200k replay-buffer
  probe separate entropy collapse/replay eviction from reward failure. The
  first full-horizon Gazebo 2-D enforcement runs are SAC-entfix seeds 2024 and
  42. A separate **untrained**, bounded-75k margin022 config now preregisters
  0.03 m/s of C-04 margin, keeps the 75k+50k chain inside a 150k replay buffer,
  and rejects historical checkpoints. SC-PERT-03's λ/criterion and
  two-arm orchestration are prepared but unexecuted. The two-seed SC-PERT
  subset is reported separately above. None is GE4.
- **Isaac / sim-to-real (open, posterior):** URDF import, in-process PPO
  training/evaluation and independent 2-D retrains (D-49/D-50), under a separate
  **0.5 m/s** full-authority contract. Gazebo checkpoints do not transfer; this
  does not reopen G4.
- **F5 / Phase 5 (executed and CLOSED, 01.09.2026):** sim-to-real retrain (v2,
  checkpoint 1650k, D-72) and physical deployment on the real lane circuit. The v2 policy
  **transfers** — 18.05 m in one uninterrupted segment with no safety rule fired (26.08) —
  and what stops the vehicle is the **measurement**, not the control: thirteen gap terms
  measured, four of the six that mattered in the perception chain, **none of them the
  policy** (docs/17 §14). `verdict_phys` stays open **by design**: no scenario was executed
  under protocol, every run was `monitoring`, and the cage has never modified an action on
  hardware. Nothing in Phase 5 re-scores a gate. Decisions D-70…D-80; runbook and record
  in `docs/17`.

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
  SC-PERT-03's two-arm stall design is now preregistered and runner-wired but
  remains unexecuted; the GE4 1-D arm remains N/A-by-construction per D-38/D-49).

The executable qualification sequence is fixed (Ubuntu/Jazzy, after sourcing
the workspace). First train the **bounded fresh 75k** parent; the trainer writes
paired `.vecnormalize.pkl` and `.replay_buffer.pkl` files beside the final model:

```bash
CFG=$(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config
PARENT=$PWD/policy/checkpoints/cobraflex_sac_gz2d_entfix_margin022_2024_75k.zip
ros2 launch cobraflex_rl train_lane.launch.py \
  train_config:=$CFG/train_sac_camera_2d_tuned_entfix_margin022.yaml \
  run_id:=sac_gz2d_entfix_margin022_2024_75k model_path:=$PARENT \
  gui:=false shutdown_on_train_exit:=true
```

Evaluate that exact checkpoint on SC-NOM-01, then produce a D-43 report bound
to its checkpoint/config metadata:

```bash
NOM=rl_sacgz2d_margin022_eval_2024_cb75k_4k4
ros2 run cobraflex_rl eval_policy \
  --train-config $CFG/train_sac_camera_2d_tuned_entfix_margin022.yaml \
  --centerline-config $CFG/complex_b_right_lane_centerline.yaml \
  --road-centerline-config $CFG/complex_b_centerline.yaml \
  --world-name lane_following_complex_b --model-path $PARENT \
  --max-steps 4400 --mode enforcement --run-id $NOM \
  --output-root experiments/sim/runs
D43=experiments/sim/eval_gz2d/margin022_seed2024_d43_preflight.json
python tools/d43_preflight.py experiments/sim/runs/$NOM --output $D43
```

Only a `PASS` report for that same checkpoint may be supplied to the runner.
The committed four-run reference report is deliberately `BLOCKED`; it
characterises historical mechanisms and is not an authorization token.

Then freeze and execute the one-shot stall continuation, followed by the 80
arm-labelled cells (20 × 2 arms × 2 modes):

```bash
PROTO=experiments/sim/sc_pert_03/margin022_seed2024_v1
python tools/sc_pert_03_protocol.py prepare \
  --scenario scenarios_complex_b/perturbed/sc_pert_03.yaml \
  --parent-checkpoint $PARENT \
  --parent-config $CFG/train_sac_camera_2d_tuned_entfix_margin022.yaml \
  --parent-vecnormalize ${PARENT%.zip}.vecnormalize.pkl \
  --parent-replay-buffer ${PARENT%.zip}.replay_buffer.pkl --out $PROTO
python tools/sc_pert_03_protocol.py run --manifest $PROTO/protocol_manifest.json
python tools/run_campaign.py --scenario-dir scenarios_complex_b \
  --scenarios SC-PERT-03 --controllers rl --seeds 2024 \
  --modes enforcement,monitoring --out experiments/sim/campaign_sc_pert_03_gz2d \
  --two-arm-manifest $PROTO/protocol_manifest.json \
  --d43-preflight-report $D43
```

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
