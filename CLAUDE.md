# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Keep lean (<250 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-06-12.

## What this repo is

Master's thesis (Samuel Sanchez, HS Esslingen, Automotive Systems M.Sc.,
supervisor Prof. Dr.-Ing. Ralf Schüler) on **runtime safety cages + RL
for lane-following**, applied to the CobraFlex 1:14 platform under a
**SE4AI** (Systems Engineering for AI) methodology. Validated in
Gazebo and, eventually, on the physical platform.

The defining commitment is **traceability**:

```text
Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict
```

Every artifact has an ID, every Gate review fails if the traceability
script reports orphans on either side.

## Phase status (snapshot)

- **Single trunk since 2026-06-11:** `e2e-camera` merged into `main`. The F-track results are
  **frozen as the ground-truth baseline** (control arm for "what does camera perception cost");
  track 'E' (end-to-end front camera) continues on top. Totals: **12 hazards, 14 SR, 6 cage rules,
  24 scenarios, 19 metrics** (check_traceability PASS).
- **F-track ground state — F4 Sim eval, campaign closed (2026-06-10). G3 passed 2026-06-03.**
  Scenario library **24 scenarios**; ODD-2 adverse profiles closed (D-33); campaign runner +
  pure-Python verdict spine (D-29/D-30) built and unit-tested. **Gazebo executor is live** —
  `run_campaign.execute_run` drives `eval_scenario_batch.launch.py` (GZ_PARTITION isolation,
  orphan-gz reaping, retries, resume). **Campaign done (2026-06-10):** the verdict-bearing
  run completed — **1260 runs**, main seed 2024 (D-36), every scenario × {enforcement,
  monitoring}; roll-up at `experiments/sim/campaign/campaign_report.json`, frontier contrast
  (25 reps) at `experiments/sim/campaign_frontier/frontier_contrast.json`. **Global verdict
  `SATISFIED`** — all 7 SR-CL-A satisfied (D-30 veto clear); `docs/07` verdicts filled (8
  Satisfied + SR-011; **2 SR-CL-B held TBD** — SR-009/010). Central finding: M-S2 = 0 in
  both modes in-ODD (cage **latent**, policy never nears the boundary); cage value shows
  out-of-ODD in the frontier contrast (seed-123 cage removes 96–100% of road-edge contacts).
  `docs/07` verdicts filled: 7/7 SR-CL-A + SR-011 + **SR-006 Satisfied (D-39**, scored on
  its committed-steer rate metric via `tools/sr006_smoothness.py`: 559/559 enforcement vs
  67.6% monitoring; no C-06 defect — large jumps are correct downstream safety overrides).
  Aggregator indeterminate→fail collapse **reconciled (D-38)**.
  **Remaining F4 work (needs Ubuntu re-run):** SR-010 — SC-EDGE-05 induced **zero
  co-activation** as-run (parameterised_grid ICs not injected by the runner) + add its two
  counters to the run-record, then re-run; SR-009 — run SC-PERT-03's stall-variant arm +
  group the two arms in the driver (`criterion_eval.evaluate_labelled` already exists).
  Follow-up (here): re-point SR-006 in `run_campaign.aggregate_sr` so `campaign_report.json`
  stops reading `failed` (CL-B; global unaffected). Plus the QED-metric decision
  (D-17/D-21/D-22); G4 is **not yet formally passed** pending the two TBDs. See CHANGELOG 03.06–10.06 "F4".
- **Track 'E' (camera) — GE4 (eval) campaign closed 2026-06-12; global `NOT SATISFIED` (availability cost, not a safety breach).**
  D-41 architecture; the cage reads a **dedicated deterministic CV lane-estimator** (D-43), not the camera.
  139k-peak checkpoint (`cobraflex_ppo_cam_lane_2024_139k_peak`, §7.7.7). **E-campaign: 1660 runs**
  (seed 2024, 24 scenarios × {enforcement, monitoring}, cage v0.6.1, 0 errors;
  `experiments/sim/campaign_e/campaign_report.json`). **`NOT SATISFIED`** but the cage's core safety
  holds: across all 830 enforcement runs **0 road-edge contacts**, M-S1 < d_max in-ODD (the 9 exceptions
  are SC-FRONT-01 out-of-ODD spawns *at* d_max). The 3 SR-CL-A vetoes (SR-001/SC-EDGE-02, SR-012+SR-014/SC-PERT-04)
  are **safe controlled stops** scored as fails by the scenarios' `emergency == False` clause (13/13 + 20/20
  enforcement fails are emergency-only). **Central finding: the cage flips latent→active under the camera** —
  the SR-013/Trigger-8 stop becomes the in-ODD safety mechanism (cleanest contrast SC-PERT-07: enf 20/20 vs
  mon 0/20, real M-S1 breaches prevented). Breakdown `failure_mode_breakdown.json` (`tools/campaign_e_failure_modes.py`).
  Indeterminate (D-38 class): SC-EDGE-05 (schema), SC-PERT-03/05 (labelled `low:/high:` criterion unwired);
  SR-006 'failed' = same D-39 aggregator artifact (CL-B). **GE4 not formally passed** pending: (a) own-criterion
  reconciliation à la D-39 (re-score SR-012/SR-001-camera on M-S1≤d_max ∧ M-S2=0 — **flagged decision, NOT applied**);
  (b) wire `evaluate_labelled`; (c) SC-EDGE-05 grid; (d) multi-seed N=5 (host-deferred). See CHANGELOG 12.06
  'E4/GE4' + docs/07 E-track evidence + ch.8 §8.9.
- **Track 'E' camera switch + 425k retrain (2026-06-15, supersedes 139k as E-main; §7.7.8).** Perception
  re-pointed to a dedicated **Lane Cam** (IMX219-160 mirror, 640×360, HFOV ≈90°, mounted 5 cm lower at body
  front: `camera_geometry` h≈0.077 m, pitch 0.25 rad) → 139k obs distribution stale → retrain from scratch.
  New main run `ppo_newcam_train_2024_750k` (seed 2024, CnnPolicy, DR p=0.5 level 0.2–0.8): `ep_rew_mean`
  peaks **335.6 @ ≈425k** (>288.5 old `cam` peak), degrades to ~256 by 750k (checkpoint-on-peak). New E-main
  checkpoint `cobraflex_ppo_newcam_lane_2024_425k_peak.zip` (hash `953ba930…`, **gitignored**, sync manually).
  Nominal eval (SC-NOM-01, seed 2024, 4400 steps, DR off): enforcement `rl_cam_eval_2024_425k_4k4` = **11.16 laps,
  mean |ey| 12.4 mm, 0 emergencies** (C-06 + 5× C-02); monitoring `…_4k4_mon` = 11.17 laps, 0 emergencies.
  **Big win: the 139k curve-apex SR-014/Trigger-8 controlled stop is GONE** (4.69→11+ laps); cage latent in-ODD
  both modes (M-S2=0), F-track signature. **GE4 re-run with 425k prepared+dry-run-validated, NOT launched**
  (≈220 h → dedicated host); §8.9 + docs/07 + `campaign_e/` still report the 139k campaign until re-run lands.
- **F2 evidence:** `ros_run_20260523T153003Z` — 9.91 laps, 845 s,
  0 emergencies, cage v0.5.1, PD v0.8.0.
- **F3 evidence (closed):** main run `ppo_train_2024_200k` (seed 2024, 200k, reward v1.2,
  extended logging; `ep_rew_mean`→536.8, `ep_len_mean`→500, `explained_variance`→0.67) + eval `rl_eval_2024_200k_4k4`
  (SC-NOM-01, 11.2 laps, 0 emergencies, |ey| 9.9 mm vs PD 23 mm, 0% cage). Seed 2024 chosen as main (best reward + PPO health of the 5). Training Spec Ch.7 §7.2–§7.5 complete.
  **Multi-seed (N=5):** seeds {42,123,2024,23,666} trained — 4/5 constraint-respecting,
  1/5 cage-dependent (seed 123, 58.8% cage) per §7.5.3 + Fig 7.8.
- **Authoritative status sources:** [docs/CHANGELOG.md](docs/CHANGELOG.md)
  and `git log --oneline` (`F4:` = F-track ground state; `E4:` = current track-'E' eval work).

## Repo map

| Path | Role |
| --- | --- |
| `docs/` | Living engineering documents (00–10 + CHANGELOG, DECISIONS) |
| `cage/` | Pure-Python safety cage (rules C-01..C-06, cage_node, logger, YAML config). Importable without ROS2. |
| `cage/ros2/` | ROS2 helper scripts (M-1/M-2 calibration loggers). Not in colcon workspace yet. |
| `policy/` | RL policy: PD baseline, PPO training, checkpoints (gitignored binaries) |
| `src/` | colcon ROS2 workspace — packages below |
| `src/cobraflex` | URDF/SDF, Gazebo worlds, perception/control nodes, rviz, meshes |
| `src/cobraflex_rl` | RL gym wrapper, training launches, PD baseline node, vehicle control, lane perception, cage logger node |
| `src/safety_cage` | ROS2 wrapper exposing the pure-Python cage as a node |
| `src/cobraflex_safety_msgs` | Custom safety msg definitions |
| `scenarios/` | YAML scenario library: `nominal/`, `edge/`, `perturbed/` (schema `_schema.yaml`) |
| `experiments/` | Calibration data, ODD inspection, sim+physical run outputs |
| `tools/` | Traceability + sync scripts (manuscript Markdown → CSV) |
| `tests/` | Placeholder dirs (`integration/`, `unit/`) — currently empty, not in pytest testpaths |
| `manuscript/` | Thesis chapters + figures — authoritative source for hazard/SR tables |
| `scripts/` | Workspace bootstrap (`download_meshes.sh`, oval centerline generator, lane-circuit composer) |

`build/`, `install/`, `log/`, `.venv/`, mesh blobs, bag files, checkpoint
binaries, and `experiments/**/raw_logs/` are gitignored.

## Identifier conventions (memorize)

| Prefix | Meaning |
| --- | --- |
| `H-XX` | Hazard (e.g. `H-01`) |
| `SR-XXX` | Safety Requirement (e.g. `SR-001`) |
| `C-XX` | Cage rule (`C-01` lane bdry, `C-02` heading, `C-03` TTLC, `C-04` speed, `C-05` emergency, `C-06` rate limiter) |
| `SC-*` | Scenario (e.g. `SC-NOM-01`) |
| `M-*` | Metric (e.g. `M-S1`) |
| `F-X` / `G-X` / `D-NN` | Phase / Gate / Decision |

Full spec: [docs/01_id_conventions.md](docs/01_id_conventions.md).
Commits are prefixed with the current phase tag (`F2: feat:`, `F2: fix:`, etc.).

## How changes flow

1. Edit Markdown source (often `manuscript/chapters/*.md` for hazards/SRs,
   or `docs/0X_*.md` for engineering specs).
2. If hazards/SRs touched, regenerate CSVs:
   `python tools/sync_hazard_register.py` (and `sync_safety_requirements.py`).
3. Record the change in [docs/CHANGELOG.md](docs/CHANGELOG.md) with
   Phase / Gate / Rationale / Impact / Verification blocks.
4. Run `python tools/check_traceability.py` — must pass before any Gate.
5. Commit with `FN:` prefix matching the current phase.

Architectural decisions go in [docs/DECISIONS.md](docs/DECISIONS.md) as
`D-NN` ADR-style entries — cite by ID rather than re-arguing.

## Commands

Python-side (cage + policy, no ROS2 needed):

```bash
pip install -e .                                  # editable install (pyproject.toml)
pip install -r requirements.txt
pytest                                            # only cage/tests + policy/tests (see pytest.ini)
pytest cage/tests/test_cage_node.py              # run a single test file
pytest cage/tests/test_pipeline.py::test_pd_cage_logger_pipeline  # single test
python tools/check_traceability.py                # hard gate before any review
```

ROS2-side (Ubuntu 24.04 + Jazzy; installed at `/opt/ros/jazzy`):

```bash
rosdep install --from-paths src --ignore-src -r -y
./scripts/download_meshes.sh                      # 87 MB lidar visual, gitignored
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch cobraflex bringup.launch.py
ros2 launch cobraflex_rl train.launch.py
```

`pytest` from the root is configured to **skip** `src/` (those packages
use `ament_python` + `colcon test`, not bare pytest).

## F2 pipeline architecture

`SafetyCageNode` ([cage/cage_node.py](cage/cage_node.py)) is pure-Python (no ROS2). It chains six rules in fixed order: **C-06 → C-04 → C-02 → C-03 → C-01 → C-05**. Core call: `node.step(state, raw_action) → dict` (keys: `safe_action`, `interventions`, `emergency`). `State` and `Action` types are in [cage/rules/base.py](cage/rules/base.py).

The F2 ROS2 demo wires five nodes over these topics:

```
/odom → lane_perception_node → /state_obs
/state_obs → pd_baseline_node → /raw_action
/raw_action + /state_obs → cage_ros_node → /safe_action + /cage_status
/safe_action → vehicle_control_node → /cmd_vel
/cage_status → cage_logger_node → CSV
```

Full loop: `ros2 launch cobraflex lane_keeper_gazebo.launch.py`. The ROS2 nodes import `cage` via a path-walk bootstrap — run `pip install -e .` once before `colcon build` to make the import reliable.

## Environment & host constraints

- Dev machine: **Ubuntu 24.04 LTS** with ROS2 Jazzy at `/opt/ros/jazzy`.
- `.venv/` is the local Python env. `pyproject.toml` exposes `cage`,
  `cage.rules`, `policy` for `pip install -e .`.
- Third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) are
  **intentionally not tracked** (decision D-32) — install externally.

## Where to look first

| You need… | Read |
| --- | --- |
| Methodology overview | [docs/00_v_model_adapted.md](docs/00_v_model_adapted.md) |
| ID rules | [docs/01_id_conventions.md](docs/01_id_conventions.md) |
| Hazards (H-01..H-09) | [docs/02_hazard_register.md](docs/02_hazard_register.md) |
| Safety Requirements | [docs/03_safety_requirements.md](docs/03_safety_requirements.md) |
| Cage rule specs | [docs/04_cage_specification.md](docs/04_cage_specification.md) |
| Scenarios | [docs/05_scenario_library.md](docs/05_scenario_library.md) |
| Metrics | [docs/06_metrics_catalogue.md](docs/06_metrics_catalogue.md) |
| Traceability matrix | [docs/07_traceability_matrix.md](docs/07_traceability_matrix.md) |
| ODD spec | [docs/08_odd_specification.md](docs/08_odd_specification.md) |
| RL environment design (F3) | [docs/09_environment_design.md](docs/09_environment_design.md) |
| RL reward function (F3) | [docs/10_reward_function.md](docs/10_reward_function.md) |
| Camera RL training (track 'E') | [docs/11_camera_rl_training.md](docs/11_camera_rl_training.md) |
| Classical CV lane-keeper (track 'E' baseline) | [docs/12_cv_lane_keeper.md](docs/12_cv_lane_keeper.md) |
| Decisions (D-NN) | [docs/DECISIONS.md](docs/DECISIONS.md) |
| What changed when | [docs/CHANGELOG.md](docs/CHANGELOG.md) |
| Manuscript-to-CSV generation | [TRACEABILITY.md](TRACEABILITY.md) |
| Cage runtime details | [cage/README.md](cage/README.md) |
| Policy training details | [policy/README.md](policy/README.md) |
| Experimental runs | [experiments/README.md](experiments/README.md) |
| Tools usage | [tools/README.md](tools/README.md) |

## Working rules of thumb

- **Single source of truth = the Markdown.** Generated CSVs and tables
  must be re-derivable; never hand-edit `docs/data/*.csv` or generated
  figures under `manuscript/figures/auto/`.
- **No orphan IDs.** If you add an `H-`, it needs an `SR-` and a row
  in the hazard register. If you add an `SR-`, it needs a `C-` or an
  explicit "implementation deferred" note (with rationale).
- **Cage backwards compatibility:** when bumping `cage.yaml`'s
  `cage.version`, defaults in `SafetyCageNode.__init__` must keep new
  features inert for older YAMLs (precedent set at 0.4.0→0.5.0).
  When bumping `compatible_sr_spec_version`, also update
  `_ACCEPTED_SR_SPEC_VERSIONS` in `cage/cage_node.py:45` — omitting
  this raises `IncompatibleCageConfigError` at load time.
- **`[provisional, M-X]` parameters:** tags in `cage.yaml` mark
  thresholds awaiting calibration results. Resolution workflow: update
  `cage.yaml` → bump version → run pytest → re-run affected scenarios
  → record in `docs/CHANGELOG.md`.
- **Commit prefix matches phase.** `F2:` for current work, never bare
  messages. Conventional-Commit body style (`feat:`, `fix:`, `chore:`,
  `refactor:`).
- **Don't claim a feature works without running it.** ROS2 nodes
  especially: typecheck/pytest ≠ feature works. If you can't launch
  the world on this host, say so explicitly.
- **Reproducibility metadata.** Each run under `experiments/sim/runs/`
  or `experiments/physical/runs/` records git commit, cage YAML hash,
  policy checkpoint hash, scenario YAML hash, seed, timestamp.

## Out-of-scope reminders

- Don't write CLAUDE.md content that's already in `README.md` or
  `docs/0X_*.md` — link instead.
- Don't add planning/decision/analysis docs unless the user asks.
- Don't introduce abstractions or backward-compat shims preemptively.
- This file is maintained by the `daily-update` scheduled task; if it
  starts drifting >200 lines, split into `CLAUDE_*.md` linked from here.

## Git commits

Do not add agent attribution to commit messages. No `Co-Authored-By: Claude ...`, no "Generated with Claude Code" trailers, no tool/model signatures. Write the commit message as the human author.
