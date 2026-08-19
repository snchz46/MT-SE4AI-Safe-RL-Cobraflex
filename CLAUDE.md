# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Keep lean (<250 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-07-30.

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

> **THESIS TRUNK (D-67, 30.07.2026) — read this before citing any result.** The **2-D PPO camera
> policy** (cap 0.22, checkpoint 550k, D-66) is the **research trunk of record**: what the defense
> presents, and what the framework is evaluated/verified against. Everything earlier is
> **development history**, not a parallel result: F-track = method validation (perfect perception
> control arm); 1-D GE4-V2 = predecessor + verification data (it closed G4, and that gate record
> stands); SAC/cap probes + margin022 = findings-with-fixes. **Condition met (31.07.2026, D-69):**
> the 550k campaign finished — 1890 runs, 0 errors, global `NOT SATISFIED` **literal** (SR-002/003
> via SC-EDGE-01's recovery clause only, D-47/D-68), **0 in-ODD road-edge contacts** in enforcement
> vs 60 by the bare policy, out-of-ODD 56 vs GE4-V2's 117. `verdict of record` in docs/02–08 **now
> points here**; GE4-V2 stays the frozen G4 gate record and is not re-scored. Narrative: docs/16 §8.
> This reclassification is **repo-only**: it must not be written into `manuscript/` (author
> instruction) — the manuscript edits made were only corrections of claims the closure falsified.

> **Two orthogonal axes — don't conflate them.** *Observation:* **F-track** (state-vector,
> frozen baseline) vs **E-track** (camera, verdict closed). *Simulator:* **Gazebo** carries every
> result and **all thesis verdicts** — the E verdict **closed in Gazebo** with GE4-V2 on the
> complex_b 297k E-main (28.06.2026) and **G4 closed 02.07.2026** (docs/07); **Isaac**
> (D-44) is **posterior work** — a sim-to-real / physical-platform bridge, **not the E
> verdict**. Gazebo checkpoints don't transfer to Isaac: the posterior Isaac policies are
> independent 2-D retrains (D-49), not a re-do of the 297k E-main; any new variant must likewise
> retrain. Isaac lives
> in docs/13–14 (note: `E4: Migration to Isaac Sim` commits tag this posterior
> work under the E gate, but its eval is not GE4).

- **Single trunk since 2026-06-11:** `e2e-camera` merged into `main`. The F-track results are
  **frozen as the ground-truth baseline** (control arm for "what does camera perception cost");
  track 'E' (end-to-end front camera) continues on top. Totals: **12 hazards, 14 SR, 6 cage rules,
  28 scenarios, 19 metrics** (check_traceability PASS; SC-PERT-11/12/13 + SC-FRONT-07 documented in docs/05 02.07.2026).
- **F-track ground state — method validation (D-67). F4 campaign closed 2026-06-10, G3 passed 2026-06-03.**
  Oval scenario library **24 scenarios**; the campaign runner + pure-Python verdict spine (D-29/D-30) and the
  live Gazebo executor (`run_campaign.execute_run` → `eval_scenario_batch.launch.py`, GZ_PARTITION isolation,
  orphan-gz reaping, retries, resume) were all built here — that machinery is what every later arm reuses.
  Verdict-bearing run: **1260 runs**, seed 2024 (D-36), every scenario × {enf, mon}; **global `SATISFIED`**,
  all 7 SR-CL-A (`experiments/sim/campaign/campaign_report.json`). Central finding: **M-S2 = 0 in both modes
  in-ODD** — with perfect perception the cage is **latent**; its value only shows out-of-ODD (frontier
  contrast: seed-123 cage removes 96–100% of road-edge contacts). SR-006 Satisfied via D-39; D-38 reconciled
  the aggregator's indeterminate→fail collapse; the two CL-B TBDs (SR-009/010) closed at G4 as documented
  non-vetoing abstentions (D-30), materially answered on the E arm. Detail: CHANGELOG 03.06–10.06 "F4" +
  02.07 "G4"; docs/07.
- **Track 'E' (camera) — GE4-V2, the frozen G4 gate record (2026-06-28); G4 CLOSED 02.07.2026 (docs/07). Superseded as *verdict of record* by the 2-D trunk below (D-69) and NOT re-scored.**
  D-41 architecture; the cage reads a **dedicated deterministic CV lane-estimator** (D-43), not the camera.
  **GE4-V2 on the 297k E-main: 1970 runs** (seed 2024, 28 complex_b scenarios × {enforcement, monitoring},
  0 errors; `experiments/sim/campaign_e_v2/campaign_report.json` + `failure_mode_breakdown.json` + 7 figures).
  **Global `NOT SATISFIED` (literal), blocking SR-002/003 only** — both fail *only* SC-EDGE-01's oval-legacy
  2.0 s recovery-time clause (max M-P4 = 14.4° ≤ 25°, 0 emergency) and are **Satisfied on their own criterion
  (D-47)** → no SR-CL-A safety predicate breached; verdict recorded as literal + reconciliation annotated
  (user decision). **SR-001 Satisfied** — ruta-1 clipped SC-EDGE-02's IC to the ODD (V1 spilled 9/30 spawns
  out-of-ODD) → 28/30; the 2 residuals are the **D-43/H-12 confident under-read** at the recovery-basin edge
  (~0.120 m). Ruta-2b was **unnecessary + reverted** (D-48; opt-in flag default False, docs/12 §4.4).
  **SR-012/013/014 Satisfied**; SR-010 **genuine CL-B** (30/85 in-ODD co-activation breaches); SR-009 stall arm
  N/A-by-construction (D-49). In-ODD safety holds: **0 in-ODD road-edge contacts**; the cage **removes**
  perception-degradation failures the bare policy commits (cleanest SC-PERT-13 40/40 enf vs 0/40 mon) — this is
  where the latent→active flip is first measured. The 117 enf road-edge contacts are all out-of-ODD.
  Multi-seed N=5 closed (13.07): 3/5 constraint-respecting, 666 cage-dependent, 23 cage–CV conflict — the
  training curve does **not** classify the basin. Historical campaigns: `campaign_e_297k/` (V1), `campaign_e/`
  (139k, 1660 runs). Detail: docs/11 §8.4–8.5 + ch.8 §8.9 + CHANGELOG 27–28.06 / 13.07.
- **Track 'E' E-main predecessor — 425k oval peak (2026-06-15).** Superseded by the 297k on 2026-06-22; its GE4 re-run
  was prepared but **never launched**. Full detail docs/11 §8.3.
- **Track 'E' E-main → complex_b 297k peak (2026-06-22, supersedes the 425k; §7.7.8/docs/11 §8).** Training moved to
  the **complex_b** circuit (perimeter 19.22 m, 2.2× the oval). Run `ppo_newcam_complex_b_2024_1M` (seed 2024, CnnPolicy,
  v3 stability stack: target_kl 0.5 + linear LR + VecNormalize + clip_range_vf) stopped manually ~662k of 1M: `ep_rew_mean`
  peaks **822.9 @ ~297k** (value_loss tiny all run — exploration collapse, not the v2 sawtooth), decays to ~113 by 662k.
  Peak rescued + verified (`num_timesteps==296960`): `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` in
  `experiments/sim/training/ppo_newcam_complex_b_2024/checkpoints_peak/` (hash `44c8e912…`, gitignored; run-record
  `metadata.json` reconstructed, status interrupted). **Path caveat:** the 1970 GE4-V2 run metadata record the older
  `…_2024_1M/…` directory, renamed since — the chain holds **by hash, not by path** (docs/11 §8 path note). **Nominal eval (SC-NOM-01, seed 2024, 4400 steps, DR off, complex_b):** enforcement
  `rl_newcam_eval_2024_cb297k_4k4` = **4.88 laps, mean |ey| 10.9 mm, 0 emergencies** (43.5% C-06 only); monitoring `…_mon`
  = 4.89 laps, 12.9 mm, 0 emerg. **Cage latent in-ODD both modes** (no C-01/02/03/05, F-track signature; 139k curve-apex stop
  gone). **RL beats the CV baseline on the same track** (10.9 vs 17.2 mm |ey|), reversing the oval finding. Laps NOT comparable
  across tracks (~94 m ≈ the 425k's 98 m). GE4 closure on this checkpoint = the **GE4-V2 campaign above** (verdict of record);
  docs/07 matrix rows, ch.8 §8.9 and the traceability CSV all read V2 now.
- **THE 2-D TRUNK — PPO cap 0.22, checkpoint 550k (D-66; trunk per D-67). CAMPAIGN CLOSED 31.07.2026 — this is
  the VERDICT OF RECORD (D-69), and the last simulation campaign before physical deployment.** Fresh PPO 2-D 1M
  on complex_b: `ep_rew_mean` peaks **1755 @ 472k**, stable plateau (SAC 2-D never exceeds ~200); cage **latent for
  safety** across training (C-01/02/03/05 = 0). Checkpoint chosen **by driving + cage %, not reward** — the reward-peak
  475k is the *worst* candidate (14 safety interventions, max |ey| 49 mm); **550k** wins: nominal `SC-NOM-01` enforcement
  = **5.32 laps, |ey| 8.6 mm (max 27), 0 emergencies, 0 safety interventions** (C-06 only). D-43 preflight **PASS 7/7**.
  **Verdict:** `experiments/sim/campaign_2d_ppo550k/` — **1890 runs, 0 errors** (27 complex_b scenarios × {enf, mon},
  seed 2024; SC-PERT-03 excluded — closed D-64). Global **`NOT SATISFIED` literal, blocking SR-002/003 only**, again
  *only* via SC-EDGE-01's recovery-time clause (0 emergencies, max M-S1 0.043 m, max M-P4 14.2°) → **D-47 verbatim**,
  no SR-CL-A safety predicate breached. **0 in-ODD road-edge contacts in enforcement** (bare policy commits 60);
  out-of-ODD 56 vs GE4-V2's 117. margin022's availability failures **clear** (SC-NOM-03 25/25, SC-PERT-05 40/40, all 12
  SC-PERT enf `True`); the **structural** ones persist (SC-EDGE-01 clause; SR-010 co-activation 16/85 in-ODD, halved
  from 30/85 but unchanged in kind → T4). **Two findings that outrank the verdict table:** (i) **C-06 is load-bearing** —
  on the 300 s endurance run the ledger is `{C-06: 58124}` with zero C-01/02/03/05, yet cage-off the same policy goes
  `off_road` 17/25 (|ey| 145 mm vs 36 mm); "cage latent in-ODD" is about the **safety rules**, not the cage, and the
  coupling to `delta_max_steering_per_cycle` is a **physical-transfer risk** (T2). Origin (co-adaptation) is *inferred* —
  the ablation was not run. (ii) **C-04 never fires** (0/1890 runs, both modes): 0.22 < `V_MAX_CURVE` 0.25, so the ODD-3
  speed ceiling stays untested from above even with speed authority. Analysis:
  `campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md`. A 29.07 concurrency incident quarantined 222 runs
  (`_quarantine_20260729_concurrent_writers/`, operator error, not a code defect; re-executed under a flock'd serial driver).
- **TBD status (D-69, 31.07.2026): no `TBD` remains in the sim column.** SR-009 → **Satisfied**, scored out-of-band on
  the D-64 metrology (nominal liveness M-P6=0 on every arm; the policy resists a forced stall; the detector reads
  M-P6=100.0 on a scripted ground-truth stall). SR-010 → **`Not satisfied`**, the one reported negative: CL-B,
  non-vetoing (D-30), twice-measured, concentrated on **C-01 ∧ C-02** co-activation, carried as future work T4.
  **Still open on purpose:** the whole `verdict_phys` column (Phase 5 scaffolded, **not run on hardware**, docs/17) and
  **TBD-Q10** (`ODD-3.A_LAT_MAX`) — unmeasurable in simulation by construction (D-33), so docs/08 stays below v1.0 by
  design (now v0.9.1). Also still open: the **Chapter 8 restructure** so the camera track leads instead of sitting in
  §8.9 — the other follow-up D-67 deferred; an authoring decision, not an evidence one.
- **Posterior E5 — algorithm/action probes, now reclassified as findings (D-67; does not reopen G4).** Closed PPO camera
  N=5 nominal battery; SAC 1-D/2-D studies (D-60): `ent_coef=0.005` removes the entropy-collapse cliff, a 200k replay
  buffer holds the peak band (eviction was the slow decay); two 1-D SAC SC-PERT subsets 100/100 enf vs 68/100 mon (probes,
  not verdicts). First full 2-D campaign **margin022** (SAC 75k, D-65): NOT SATISFIED literal but **0 in-ODD road-edge
  contacts** — the bare policy commits 98, the cage removes all via 433 controlled stops. That weak-and-*decayed*
  checkpoint is what motivated D-66.
- **Phase 5 — physical deployment (docs/17). RUN ON THE TRACK (18.08.2026, M-7/D-71).**
  Chain complete: `csi_camera_node` → `rl_policy_node` → `cv_lane_estimator_node` → `cage_ros_node` →
  `vehicle_control_node` → `cobraflex_ros_driver`. **Headline: the D-43 estimator reads lane WIDTH correctly and lateral
  OFFSET badly; the 550k trunk camera policy does NOT transfer; the cage contained it.** At the
  **default** `white_sat_max = 30` it pairs 95.4 % of circuit frames and reads width **252.9 mm vs
  a ruler 250**. But `ey` measured hands-off against a tape (15 points over ±100 mm,
  `M7_offset_response.csv`) is **0.68–0.83 × true − 10 mm**, robust to every filtering (r up to
  0.99) — so **C-01's 160 mm fires at a true 207–241 mm**, leaving 14–48 mm to the road edge
  instead of 95. Width is a *difference* straddling the optical axis, `ey` an *absolute* off-axis
  position, and the unmodelled barrel distortion (`k1 = −0.339`) compresses the second only. Two
  further estimator defects: **repeatability** — re-placing at the same tape offset elsewhere moves
  the reading a mean 13.2 mm, worst 29.4 (tape ~2 mm) — and **pairing collapse beyond ~±55 mm**
  (width-sane share 18 % → 30 % → 87 % → 95 % rejected across 0–30/30–55/55–80/80–120 mm bands,
  `n_lines` mostly 4 = wrong pair). All three sit inside the band where C-01 and C-05 act.
  **M-6's propagated `ey` under-read of 0.72 is CONFIRMED** by that tape measurement (an
  intra-session retraction of it, made from the lane-width figure, is itself withdrawn — see D-71 §2);
  the camera measurement (fx 395.93, HFOV 77.89°, pitch 17.84°) stands, its mechanism is `cx` +
  distortion rather than a pure `fx` scale, and its operative conclusion — **undistort, do not just
  re-parameterise** — stands verbatim,
  and its real cost is heading **noise**: `joint_pair_quadratic`/1.6 sd 14.3°, 7.8 % past C-02's 25°,
  vs `near_secant`/1.0's 5.3° / 0.8 %. **Method lesson (D-71 §3): match the measurement to the
  quantity** — three single-pose conclusions (sat 45, a 0–12 % scale error, a +17.28° heading bias)
  were overturned by a recorded circuit, and a fourth (`ey` reads true) by realising lane width had
  been used as a proxy for something it cannot measure. A claim that survives every filtering of the
  data is the only kind that held up. **§5 yaw resolved:**
  neither 0.159 nor 0.154 — the plant is compressive (0.48→0.34); 0.4954 confirmed while moving and
  already compensated by `steering_to_yaw_rate_gain 1.615`. Open: the appearance gap (off-track
  fine-tune / DR against real imagery, raw material in `experiments/physical/bags/`), which heading
  config to deploy, localised colour-gate failures. Sim results and the D-69 verdict unaffected.
  Detail: [M-7](experiments/calibration/M7_track_perception.md) + [M-6](experiments/calibration/M6_camera_hfov.md)
  + docs/17 §2/§5/§6c/§6d.
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

```text
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
| Defense compendium (deep dives, threshold provenance, **what counts as a result vs a finding**) | [docs/16_defense_compendium.md](docs/16_defense_compendium.md) |
| Physical deployment / Phase-5 bring-up (camera + driver + layering) | [docs/17_physical_deployment.md](docs/17_physical_deployment.md) |
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
