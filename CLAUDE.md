# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Keep lean (<250 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-07-02.

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

> **Two orthogonal axes — don't conflate them.** *Observation:* **F-track** (state-vector,
> frozen baseline) vs **E-track** (camera, verdict closed). *Simulator:* **Gazebo** carries every
> result and **all thesis verdicts** — the E verdict **closed in Gazebo** with GE4-V2 on the
> complex_b 297k E-main (28.06.2026) and **G4 closed 02.07.2026** (docs/07); **Isaac**
> (D-44) is **posterior work** — a sim-to-real / physical-platform bridge, **not the E
> verdict**. Gazebo checkpoints don't transfer to Isaac, so an Isaac E-policy is a *future
> retrain* (with the 2-D action expansion, D-49), not a re-do of the 297k E-main. Isaac lives
> in docs/13–14 (note: `E4: Migration to Isaac Sim` commits tag this posterior
> work under the E gate, but its eval is not GE4).

- **Single trunk since 2026-06-11:** `e2e-camera` merged into `main`. The F-track results are
  **frozen as the ground-truth baseline** (control arm for "what does camera perception cost");
  track 'E' (end-to-end front camera) continues on top. Totals: **12 hazards, 14 SR, 6 cage rules,
  28 scenarios, 19 metrics** (check_traceability PASS; SC-PERT-11/12/13 + SC-FRONT-07 documented in docs/05 02.07.2026).
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
  The two F-arm CL-B TBDs (SR-009/010) closed at G4 as **documented non-vetoing abstentions**
  (D-30), materially answered on the E arm: SR-009's stall arm is **N/A-by-construction** for the
  shared 1-D steering-only action (M-P6 ≡ 0, D-49) and SR-010's co-activation question was answered
  by GE4-V2's wired SC-EDGE-05 grid (30/85 in-ODD breaches, genuine CL-B finding). The F-arm
  SC-EDGE-05 grid re-run stays optional/historical. See CHANGELOG 03.06–10.06 "F4" + 02.07 "G4".
- **Track 'E' (camera) — GE4-V2 verdict of record (2026-06-28); G4 CLOSED 02.07.2026 (docs/07).**
  D-41 architecture; the cage reads a **dedicated deterministic CV lane-estimator** (D-43), not the camera.
  **GE4-V2 on the 297k E-main: 1970 runs** (seed 2024, 28 complex_b scenarios × {enforcement, monitoring},
  0 errors; `experiments/sim/campaign_e_v2/campaign_report.json` + `failure_mode_breakdown.json` + 7 figures).
  **Global `NOT SATISFIED` (literal), blocking SR-002/003 only** — both fail *only* SC-EDGE-01's oval-legacy
  2.0 s recovery-time clause (max M-P4 = 14.4° ≤ 25°, 0 emergency) and are **Satisfied on their own criterion
  (D-47)** → no SR-CL-A safety predicate breached; verdict recorded as literal + reconciliation annotated
  (user decision). **SR-001 Satisfied** — ruta-1 clipped SC-EDGE-02's IC to the ODD (V1 spilled 9/30 spawns
  out-of-ODD) → 28/30; the 2 residuals are the **D-43/H-12 confident under-read** at the recovery-basin edge
  (~0.120 m). Ruta-2b (conservative lane-selection) was **unnecessary + reverted** after closed-loop
  regression (D-48; opt-in flag kept, default False — docs/12 §4.4). **SR-012/013/014 Satisfied** (D-29
  coverage closed); SR-010 **genuine CL-B** (30/85 in-ODD co-activation grid breaches); SR-009 stall arm
  N/A-by-construction (D-49). In-ODD safety holds: 0 in-ODD road-edge contacts; the cage **removes**
  perception-degradation failures the bare policy commits (PERT-04/09/11/12/13 enf PASS vs mon FAIL;
  cleanest SC-PERT-13 40/40 vs 0/40) — the latent→active flip is now measured on the E-main. The 117 enf
  road-edge contacts are all out-of-ODD (SC-FRONT-* + OOD grid points). Historical: V1 297k
  (`campaign_e_297k/`) and the 139k campaign (`campaign_e/`, 1660 runs, availability-cost reading).
  Deferred to posterior work: multi-seed N=5. See CHANGELOG 27–28.06 + docs/11 §8.4 + ch.8 §8.9.
- **Track 'E' E-main predecessor — 425k oval peak (2026-06-15, superseded by 297k on 2026-06-22; detail docs/11 §8.3).**
  Lane-Cam retrain `ppo_newcam_train_2024_750k` → `cobraflex_ppo_newcam_lane_2024_425k_peak.zip` (peak 335.6 @ ≈425k);
  nominal `rl_cam_eval_2024_425k_4k4` = 11.16 laps, |ey| 12.4 mm, 0 emergencies, cage latent. Its GE4 re-run was
  prepared+dry-run-validated but **never launched** (the GE4 closure is now scoped to the 297k E-main below).
- **Track 'E' E-main → complex_b 297k peak (2026-06-22, supersedes the 425k; §7.7.8/docs/11 §8).** Training moved to
  the **complex_b** circuit (perimeter 19.22 m, 2.2× the oval). Run `ppo_newcam_complex_b_2024_1M` (seed 2024, CnnPolicy,
  v3 stability stack: target_kl 0.5 + linear LR + VecNormalize + clip_range_vf) stopped manually ~662k of 1M: `ep_rew_mean`
  peaks **822.9 @ ~297k** (value_loss tiny all run — exploration collapse, not the v2 sawtooth), decays to ~113 by 662k.
  Peak rescued + verified (`num_timesteps==296960`): `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` in
  `…/ppo_newcam_complex_b_2024_1M/checkpoints_peak/` (hash `44c8e912…`, gitignored; run-record `metadata.json` reconstructed,
  status interrupted). **Nominal eval (SC-NOM-01, seed 2024, 4400 steps, DR off, complex_b):** enforcement
  `rl_newcam_eval_2024_cb297k_4k4` = **4.88 laps, mean |ey| 10.9 mm, 0 emergencies** (43.5% C-06 only); monitoring `…_mon`
  = 4.89 laps, 12.9 mm, 0 emerg. **Cage latent in-ODD both modes** (no C-01/02/03/05, F-track signature; 139k curve-apex stop
  gone). **RL beats the CV baseline on the same track** (10.9 vs 17.2 mm |ey|), reversing the oval finding. Laps NOT comparable
  across tracks (~94 m ≈ the 425k's 98 m). GE4 closure on this checkpoint = the **GE4-V2 campaign above** (verdict of record);
  docs/07 matrix rows, ch.8 §8.9 and the traceability CSV all read V2 now.
- **Next phase — Isaac Sim / sim-to-real (posterior track, docs/13–14).** With G4 closed, the open thread is the
  D-44 Isaac bridge: URDF import + ROS2 bring-up + in-process RL training (docs/13), the handover spec (docs/14),
  the **2-D action (steering + throttle) retrain** that makes SR-009's stall test well-posed (D-49), and the
  sim-to-real gap characterisation toward the physical CobraFlex (Phase 5). Isaac work does not reopen G4.
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
- **Gazebo + ROS2 are runnable here for smoke tests** (single short eval cells,
  world-load / camera-bridge / cage checks). The `.venv/` is a husk (no numpy/pytest);
  use system `python3` (after `source /opt/ros/jazzy/setup.bash` it has numpy + pytest).
  Do **not** run multi-hundred-run campaigns or >1 h trainings here — those hand off
  to the user's other machine.
- `.venv/` is the local Python env. `pyproject.toml` exposes `cage`,
  `cage.rules`, `policy` for `pip install -e .`.
- Third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) are
  **intentionally not tracked** (decision D-32) — install externally.

## Where to look first

| You need… | Read |
| --- | --- |
| Methodology overview | [docs/00_v_model_adapted.md](docs/00_v_model_adapted.md) |
| ID rules | [docs/01_id_conventions.md](docs/01_id_conventions.md) |
| Hazards (H-01..H-12) | [docs/02_hazard_register.md](docs/02_hazard_register.md) |
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
| Isaac Sim utils (URDF import, ROS2 bring-up, in-process RL training + DR) | [docs/13_isaacsim_environment.md](docs/13_isaacsim_environment.md) |
| Isaac Sim RL handover spec | [docs/14_isaacsim_handover_spec.md](docs/14_isaacsim_handover_spec.md) |
| Implementation inventory (module/script/test map) | [docs/15_implementation_inventory.md](docs/15_implementation_inventory.md) |
| Defense compendium (deep dives, threshold provenance, literature) | [docs/16_defense_compendium.md](docs/16_defense_compendium.md) |
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

**NEVER run `git commit` or `git push`** (user rule, 2026-06-25). Leave changes in
the working tree; the user reviews and commits manually. Offer to draft the commit
message / CHANGELOG text, but stop short of committing — even an explicit "commit"
request should be confirmed first against this rule.

When the user *does* commit: do not add agent attribution to commit messages. No
`Co-Authored-By: Claude ...`, no "Generated with Claude Code" trailers, no
tool/model signatures. Write the commit message as the human author.
