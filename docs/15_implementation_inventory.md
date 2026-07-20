# Implementation Inventory — Every Module, Script and Test, Mapped to Its Purpose

| Field | Value |
| --- | --- |
| Artifact | Cross-cutting implementation inventory (defense-preparation deliverable) |
| Version | v1.1 |
| Date | 2026-07-20 |
| Author | Samuel Sanchez |
| Status | LIVING — regenerate the §6 test counts before each Gate/defense rehearsal |
| Sibling document | [docs/16_defense_compendium.md](16_defense_compendium.md) (the *why* + literature; this document is the *what/where/verified-by*) |

> **Purpose.** One place that answers, for every piece of code in this repository:
> *what is it, where does it live, what does it do, which spec governs it, and
> which test proves it works.* The per-topic engineering detail stays in
> docs/00–14; this inventory is the map. Use it when a defense question starts
> with "where is…", "what does the script X do…", or "how do you know Y works".
>
> **Latest fully green host baseline (2026-07-15):**
> `pytest` → **517 passed** (CHANGELOG 15.07.2026);
> `python tools/check_traceability.py` → **All checks PASSED, 0 warnings**
> (12 hazards, 14 SRs, 6 cage rules, all scenarios/metrics linked).
> A 20.07 collection attempt on this Windows/Python 3.14 host found 496 tests
> before `policy/tests/test_eval_policy_2d.py` failed to import because
> `ament_index_python` is unavailable. That is an environment/dependency limit,
> not a newer green count or a regression verdict.

---

## 1. The three runtime dataflows

Everything in the repo serves one of three executable loops. Knowing which loop
a module belongs to answers most "how is it wired" questions.

### 1.1 F2 deployment graph (ROS2 topics, five nodes)

The original demonstration pipeline — every component is a separate ROS2 node
communicating over topics (full loop: `ros2 launch cobraflex lane_keeper_gazebo.launch.py`):

```text
/odom ─► lane_perception_node ─► /state_obs ─► pd_baseline_node ─► /raw_action
                                     │                                  │
                                     └────────────► cage_ros_node ◄─────┘
                                                        │
                                     /safe_action ◄─────┴─► /cage_status
                                          │                     │
                                 vehicle_control_node      cage_logger_node
                                          │                     │
                                       /cmd_vel               CSV log
```

### 1.2 F3/E training & evaluation loop (in-process, D-34)

For RL training and all scored evaluation, the cage is **not** on topics: it is
called synchronously inside the gym environment (decision D-34/TS-01 —
determinism under a fixed seed, no topic asynchrony, identical cage class +
`cage.yaml` as deployment). Only Gazebo I/O crosses a process boundary:

```text
SB3 PPO/SAC ──action──► GazeboLaneEnv.step()
                       │  1. clip / map action
                       │  2. SafetyCageNode.step(state, raw_action)   [in-process]
                       │  3. safe_action → Twist(/cmd_vel)            [RosGazeboInterface]
                       │  4. step_ros(control_dt=0.1 s sim time)
                       │  5. PolylineTracker ← /odom_truth (ground truth)
                       │  6. compute_reward(...)  → SB3
                       └─ reset(): gz set_pose teleport + odom recalibration + fresh cage
```

### 1.3 Track-'E' camera path (D-41/D-43)

In camera mode the policy observation and the cage state both derive from the
**same (possibly degraded) frame**, through one shared pipeline — the
deliberate common-cause design of D-43:

```text
/camera/image_raw_lane (640×360 @ 20 Hz, bridged from Gazebo)
        │
        ▼
CameraPipeline: [degradation injector: scenario stressor | training DR | none]
        │
        ├──► native degraded frame ──► CvLaneEstimator ──► CagePerceptionSupervisor
        │                              (classical CV)       (SR-013 health + SR-014
        │                                                    plausibility) ──► cage state
        │                                                    or perception_invalid → C-05 T8
        └──► grayscale 84×84 downsample ──► policy obs ──► VecFrameStack(k=4) ──► CnnPolicy
Ground truth (/odom_truth + PolylineTracker) stays OUT of this path:
reward + termination + metrics oracle only.
```

---

## 2. `cage/` — the pure-Python safety cage

No ROS2 dependency anywhere in this package; that is what makes the cage
independently unit-testable (A2) and shareable bit-identically between the ROS2
node and the in-process training loop.

| File | Role | Spec | Tests |
| --- | --- | --- | --- |
| [cage_node.py](../cage/cage_node.py) | `SafetyCageNode`: composes the six rules in the fixed order **C-06 → C-04 → C-02 → C-03 → C-01 → C-05**; missing-state counter (Trigger 5); SR-010 joint-envelope assertion + oscillation persistence; enforcement/monitoring modes; strict `compatible_sr_spec_version` check (`IncompatibleCageConfigError`) | docs/04 | `test_cage_node.py`, `test_cage_node_missing_state.py`, `test_joint_envelope.py`, `test_oscillation.py`, `test_sr_spec_version_check.py`, `test_integration_chain.py` |
| [rules/base.py](../cage/rules/base.py) | Shared `State` / `Action` / `Decision` types and the rule contract (`evaluate`, `safe_envelope_predicate_holds`) | docs/04 | exercised by every rule test |
| [rules/c01_lane_boundary.py](../cage/rules/c01_lane_boundary.py) | C-01 reactive lateral-offset bound with hysteresis (SR-001/H-01) | docs/04 §C-01 | `test_c01_lane_boundary.py` |
| [rules/c02_heading_limit.py](../cage/rules/c02_heading_limit.py) | C-02 reactive heading bound with hysteresis (SR-002/H-02) | docs/04 §C-02 | `test_c02_heading_limit.py` |
| [rules/c03_ttlc.py](../cage/rules/c03_ttlc.py) | C-03 predictive time-to-lane-crossing (SR-003/H-01,H-02); `compute_ttlc` + urgency-scaled correction | docs/04 §C-03 | `test_c03_ttlc.py` |
| [rules/c04_speed_ceiling.py](../cage/rules/c04_speed_ceiling.py) | C-04 curvature-parameterised speed ceiling, throttle-only correction (SR-004/H-03) | docs/04 §C-04 | `test_c04_speed_ceiling.py` |
| [rules/c05_emergency.py](../cage/rules/c05_emergency.py) | C-05 emergency mode: 8 triggers, latching, explicit-reset exit, brake + frozen steering (SR-005/007/008/013/014) | docs/04 §C-05 | `test_c05_emergency.py`, `test_c05_triggers_extended.py`, `test_c05_perception_trigger.py` |
| [rules/c06_rate_limiter.py](../cage/rules/c06_rate_limiter.py) | C-06 per-cycle command-delta clamp, always active (SR-006/H-05) | docs/04 §C-06 | `test_c06_rate_limiter.py` |
| [logger.py](../cage/logger.py) | `CageLogger`: per-cycle CSV + run metadata writer; one schema shared by tests, the ROS2 logger node and the campaign analysis | experiments/README | `test_logger.py`, `test_pipeline.py` |
| [cage.yaml](../cage/cage.yaml) | **Single source of truth for every threshold** (v0.6.1); every parameter carries its SR derivation and `[provisional, M-X]` calibration status as an inline comment; referenced by SHA-256 in every run's metadata | docs/04, docs/03 | `test_cage_rules.py` (load + instantiate every rule from the real YAML) |
| `cage_isaac.yaml` | Isaac-track variant (posterior work, D-55/D-57 calibration deltas only) | docs/13 | loaded by the Isaac tools |
| `ros2/` | M-1/M-2 calibration logger helper scripts (not in the colcon workspace) | experiments/calibration | — |

**Versioning discipline** (defense-relevant): parameter changes bump
`cage.version`; changed SR thresholds bump `compatible_sr_spec_version`, which
the loader cross-checks against `_ACCEPTED_SR_SPEC_VERSIONS`
([cage_node.py:40](../cage/cage_node.py)) — an old YAML against a new SRS
**refuses to load** rather than silently enforcing stale thresholds. New
features must default inert for older YAMLs (precedent 0.4.0→0.5.0; repeated
at 0.6.0's `perception_trigger_enabled`, code default `false`).

## 3. `src/safety_cage/` and `src/cobraflex/` — ROS2 wrapper and platform

| Component | Role |
| --- | --- |
| `safety_cage/cage_ros_node.py` | Thin ROS2 wrapper around the **same** `SafetyCageNode` class: subscribes `/raw_action` + `/state_obs` + `/external_stop`, publishes `/safe_action` + `/cage_status` + `/emergency`. No rule logic is re-implemented — the wrapper only does topic plumbing, so the unit-tested class is what actually runs |
| `cobraflex/urdf/` | Robot description (`my_robot_gazebo_mesh.urdf` xacro): differential/skid-steer, 4 fixed wheels (no steering axle — matches the physical CobraFlex), front lane camera mount (pitch 0.30 rad) |
| `cobraflex/worlds/` | Gazebo SDF worlds: `lane_following_oval` (F-track, R=0.8 m bends), `lane_following_oval_complex` (`lane_following_complex_b`, 19.22 m perimeter, the E-main track) + variants (worn lines, particles, gaps) for the perturbed scenarios |
| `cobraflex/lane_keeper_gazebo_node.py` | The classical-CV camera lane-keeper deployment node (track-'E' baseline; docs/12) |
| `cobraflex/launch/`, `config/gz_bridge.yaml` | Bring-up + ros_gz bridge wiring (odometry, camera, cmd_vel, clock) |
| `cobraflex_safety_msgs/` | Custom safety message definitions (`CageStatus` etc.) |

## 4. `src/cobraflex_rl/cobraflex_rl/` — the RL package, module by module

The package `__init__` is **lazy** (PEP 562): importing `cobraflex_rl` never
pulls in `rclpy`, so every pure module below is testable on any host — this is
the mechanism behind the "host-testable kernel + thin ROS shell" pattern used
throughout.

### 4.1 Training / evaluation loop

| Module | Role |
| --- | --- |
| [gazebo_lane_env.py](../src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py) | `GazeboLaneEnv(gym.Env)` — the single environment for both tracks: obs switch (6-dim state vector ↔ 84×84 grayscale camera), in-process cage (D-34), scenario hooks via `reset(options)` (spawn arc-length/offset/heading, runtime perturbations, visual injectors), off-road/emergency termination, progress reward plumbing. Config-gated posterior extensions: 2-D action (`steer_throttle`, D-50) and multi-circuit sampling — inert by default so frozen runs stay bit-identical |
| [ros_interface.py](../src/cobraflex_rl/cobraflex_rl/ros_interface.py) | `RosGazeboInterface(Node)` — the only ROS/gz touchpoint: subscribes `/odom_truth` (+ camera), publishes `/cmd_vel`, paces the loop on **sim time** (odom header stamps), teleports via `gz service /world/<w>/set_pose` (4 retries), sets RTF via `set_physics`, per-episode odom→world offset calibration |
| [isaac_interface.py](../src/cobraflex_rl/cobraflex_rl/isaac_interface.py) | Duck-typed Isaac-Sim counterpart of `RosGazeboInterface` (same method surface) so the env runs unchanged in-process inside Isaac (D-44) |
| [cage_bridge.py](../src/cobraflex_rl/cobraflex_rl/cage_bridge.py) | Pure glue env↔cage: builds the cage `State`, maps throttle↔cage scale, mirrors `vehicle_control_node`'s actuation constants (`yaw_gain=0.8`, `throttle_nominal=0.5`, `min_speed_scale=0.35`) so training actuation == deployment actuation; 2-D maps for D-50 |
| [polyline_tracker.py](../src/cobraflex_rl/cobraflex_rl/polyline_tracker.py) | `PolylineTracker` — Frenet projection of a world pose onto the centerline polyline: `ey`, `epsi`, arc-length `s`, curvature preview, `pose_at_arclength` (scenario spawns), `distance_to` (off-road check on self-approaching circuits). Pure NumPy |
| [rewards.py](../src/cobraflex_rl/cobraflex_rl/rewards.py) | `compute_reward` — reward v1.2 (docs/10): progress − w·\|ey\| − w·\|epsi\| − w·\|Δsteer_raw\| − termination; config-gated 2-D extension adds raw `throttle_delta` and `stall_penalty`; the default-zero `lambda_stall·\|throttle\|` hook exists only for SC-PERT-03's preregistered negative test |
| [campaign_contract.py](../src/cobraflex_rl/cobraflex_rl/campaign_contract.py) | Pure guard for opted-in posterior campaign configs: checks the 0.22-vs-C-04 speed margin and bounded 75k+50k/150k-replay chain, fingerprints the action/horizon contract into fresh SB3 checkpoints, rejects historical/mismatched checkpoints, and declares the D-43 preflight prerequisite |
| [train_ppo.py](../src/cobraflex_rl/cobraflex_rl/train_ppo.py) | Training entry point: config/centerline load, env build + `check_env`, `VecFrameStack`/`VecNormalize` wrapping, SB3 construction — **PPO or SAC via the config's `algorithm:` key (D-60, docs/11 §4.2)** — all hyperparameters from YAML (`target_kl` / `lr_schedule` / `clip_range_vf` PPO stability levers; SAC knobs in the `sac:` block; SAC+camera transpose-inside-VecNormalize fix), `--resume-from` + paired `--resume-vecnormalize`/replay, final paired VecNormalize/replay capture, campaign-contract binding, reproducibility `metadata.json` + checkpoint-registry append |
| [callbacks.py](../src/cobraflex_rl/cobraflex_rl/callbacks.py) | SB3 callbacks: progress bar (algorithm-labelled), `LearningCurveCallback` (reward + algorithm health scalars + per-rule cage-intervention rates per rollout → `learning_curve.csv`; per-algorithm scalar map + `min_row_interval` throttle for SAC's per-step rollout cadence), `ActionSampleCallback` (raw-steering and, for 2-D, raw-throttle evidence) |
| [training_metrics.py](../src/cobraflex_rl/cobraflex_rl/training_metrics.py) | Pure schema/aggregation behind the learning-curve CSV (testable without SB3); per-algorithm SB3 scalar maps (`SB3_SCALAR_COLUMNS[_SAC/_BY_ALGO]` — identical CSV columns for PPO and SAC) |
| [eval_policy.py](../src/cobraflex_rl/cobraflex_rl/eval_policy.py) | Scored deterministic evaluation of a checkpoint through the *same* env + cage; resolves PPO/SAC, validates opted-in campaign fingerprints, scores an explicit preregistered criterion arm when requested, and emits config/checkpoint/protocol hashes under `experiments/sim/runs/<run_id>/` |
| [eval_metrics.py](../src/cobraflex_rl/cobraflex_rl/eval_metrics.py) | Pure aggregation: laps, intervention rate, emergencies, tracking error |
| [run_io.py](../src/cobraflex_rl/cobraflex_rl/run_io.py) | SHA-256 file hashing + git-commit lookup for run metadata (shared by train/eval) |

### 4.2 Track-'E' perception (policy obs + cage state)

| Module | Role |
| --- | --- |
| [camera_pipeline.py](../src/cobraflex_rl/cobraflex_rl/camera_pipeline.py) | The **single degradation point**: ROS image decode → optional injector → (native frame for the cage CV, 84×84 grayscale obs for the policy). Constants `OBS_WIDTH/HEIGHT=84`, `FRAME_STACK=4` |
| [camera_geometry.py](../src/cobraflex_rl/cobraflex_rl/camera_geometry.py) | Closed-form pinhole ground-plane projection for the pitch-only mount (pixel row → ground distance, column → lateral offset). Fully analytic ⇒ auditable |
| [cv_lane_estimator.py](../src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py) | The cage's deterministic classical-CV lane estimator (D-43): HSV white mask (+ vegetation-hue exclusion) → row scan → metric ground points → line clustering → lane-pair selection → `ey/epsi/lane width/curvature` + confidence. Single-line fallback; near-field heading secant with curvature correction (docs/12 §4) |
| [cage_perception.py](../src/cobraflex_rl/cobraflex_rl/cage_perception.py) | `CagePerceptionSupervisor`: composes estimator + health + plausibility into the cage contract — a trusted `State`, or `perception_invalid` for C-05 Trigger 8 |
| [perception_health.py](../src/cobraflex_rl/cobraflex_rl/perception_health.py) | SR-013 health monitor (H-11): stale/dropped frame, low confidence, missing features, with an invalid-persistence budget |
| [lane_plausibility.py](../src/cobraflex_rl/cobraflex_rl/lane_plausibility.py) | SR-014 plausibility / temporal-consistency check (H-12): geometric ODD ranges + frame-to-frame jump limits on a *confident but possibly wrong* estimate |
| [visual_degradation.py](../src/cobraflex_rl/cobraflex_rl/visual_degradation.py) | Pure-numpy degradations: glare, low-light, motion-blur (H-10 envelope) + eval-only occlusion (H-11) and false-lane (H-12) |
| [visual_domain_randomization.py](../src/cobraflex_rl/cobraflex_rl/visual_domain_randomization.py) | Per-episode DR sampler over the H-10 trio (training-side SR-012 mitigation); seeded via the env's `np_random` |
| [cv_lane_estimator_node.py](../src/cobraflex_rl/cobraflex_rl/cv_lane_estimator_node.py) | ROS2 deployment wrapper: publishes the CV estimate as `/state_obs` (replaces `lane_perception_node` on track 'E') |
| [cv_lane_controller.py](../src/cobraflex_rl/cobraflex_rl/cv_lane_controller.py) | The classical (non-learned) camera lane-keeping control law — single source shared by the deployment node and the scored eval (docs/12 §3, §6) |
| [eval_cv_controller.py](../src/cobraflex_rl/cobraflex_rl/eval_cv_controller.py) | Scores the CV controller through the same `GazeboLaneEnv` harness as the RL policy — the apples-to-apples camera baseline |
| [cage_viz.py](../src/cobraflex_rl/cobraflex_rl/cage_viz.py) | Optional RViz publisher (`/cage/markers`, `/agent/obs_image`) of what cage + agent perceive; `viz:` flag, off for headless campaigns |

### 4.3 Scenario / campaign spine (all pure Python — runnable on any host)

| Module | Role |
| --- | --- |
| [scenario_loader.py](../src/cobraflex_rl/cobraflex_rl/scenario_loader.py) | Parses `scenarios/**/*.yaml` into typed `RunSpec`s; maps scenario → nominal/adverse family for the D-29 gate; rejects stubs |
| [scenario_runner.py](../src/cobraflex_rl/cobraflex_rl/scenario_runner.py) | `(scenario, rep) → run config`: env reset options (spawn s/offset/heading + per-rep jitter), commanded speed, step horizon |
| [scenario_perturbations.py](../src/cobraflex_rl/cobraflex_rl/scenario_perturbations.py) | Runtime stressors: obs noise (SC-PERT-01), actuation latency (SC-PERT-02), throttle override (SC-EDGE-03), onset-timed visual degradations |
| [campaign_metrics.py](../src/cobraflex_rl/cobraflex_rl/campaign_metrics.py) | Full per-run metric catalogue M-P*/M-S*/M-I* (docs/06) from per-step records |
| [scenario_metrics.py](../src/cobraflex_rl/cobraflex_rl/scenario_metrics.py) | Scenario-specific verdict tokens (e.g. `time_to_recovery_heading` for SC-EDGE-01) |
| [criterion_eval.py](../src/cobraflex_rl/cobraflex_rl/criterion_eval.py) | Safe (no `eval()`) three-valued evaluator for `pass_criterion_per_run` strings — `True`/`False`/`None` (indeterminate) |
| [verdict_aggregation.py](../src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py) | Rolls run → scenario → SR → global verdicts: D-29 run-count gate (≥25 nominal + ≥25 adverse for SR-CL-A), D-30 SR-CL-A veto, D-38 `insufficient_evidence` propagation |

### 4.4 F2 ROS2 nodes (deployment graph, §1.1)

| Module | Role |
| --- | --- |
| [lane_perception_node.py](../src/cobraflex_rl/cobraflex_rl/lane_perception_node.py) | `/odom` → `/state_obs` (ground-truth state vector from the authored centerline) |
| [pd_baseline_node.py](../src/cobraflex_rl/cobraflex_rl/pd_baseline_node.py) | Wraps `policy.baseline_pd.BaselinePD` → `/raw_action` |
| [vehicle_control_node.py](../src/cobraflex_rl/cobraflex_rl/vehicle_control_node.py) | `/safe_action` → `/cmd_vel`; honours `/emergency` (forces stop) |
| [cage_logger_node.py](../src/cobraflex_rl/cobraflex_rl/cage_logger_node.py) | `/cage_status` → CSV via the same `cage.logger.CageLogger` schema as the tests |

## 5. `policy/` and `tools/`

### 5.1 `policy/`

| File | Role |
| --- | --- |
| [baseline_pd.py](../policy/baseline_pd.py) | Pure-Python PD controller (F2 baseline; gains in `baseline_pd.yaml`). The known-competent control arm that validated the pipeline and calibrated the reward |
| `train.py` | Thin shim (historical entry point; the real trainer is `cobraflex_rl/train_ppo.py`) |
| `checkpoints/` | Trained checkpoints (`.zip`, gitignored blobs) + `checkpoint_registry.csv` (seed, steps, timestamp, git commit, cage-YAML hash per row) |
| `tests/` | Pure-Python tests covering the RL package and campaign spine (included in the 517-pass host baseline; see §6) |

### 5.2 `tools/` — every script, what it does, how

| Script | What it does / how it works |
| --- | --- |
| [check_traceability.py](../tools/check_traceability.py) | **The hard Gate gate.** Parses docs/02/03/04/05/06 + `cage/cage.yaml` + `scenarios/*.yaml` + `tools/traceability_matrix.csv` and enforces 8 bidirectional constraints (every H referenced by ≥1 SR, every SR references ≥1 H, every cage rule implements ≥1 SR, every rule referenced by ≥1 scenario, every scenario references ≥1 SR, every SR has ≥1 metric, every referenced metric defined, matrix present). Any orphan on either side fails the Gate |
| [sync_hazard_register.py](../tools/sync_hazard_register.py) / [sync_safety_requirements.py](../tools/sync_safety_requirements.py) | Regenerate `docs/data/*.csv` from the Markdown source tables (manuscript / docs/03). Direction is always **Markdown → CSV**; hand-editing the CSVs is prohibited (single-source-of-truth rule) |
| [check_scenario_yaml.py](../tools/check_scenario_yaml.py) | Validates every scenario YAML against the executable schema (`scenarios/_schema.yaml`); `--strict` turns deferred-stub warnings into failures |
| [run_campaign.py](../tools/run_campaign.py) | Orchestrates a full validation campaign: builds the run matrix (scenario × mode × reps, plus explicit SC-PERT-03 policy arms), executes through the Gazebo launcher, scores and aggregates run → arm → scenario → SR → global verdicts. A completed two-arm manifest is required for SC-PERT-03; opted-in 0.22 campaign contracts also require a checkpoint-bound D-43 `PASS` report |
| [sc_pert_03_protocol.py](../tools/sc_pert_03_protocol.py) | One-shot SC-PERT-03 preparation: validates the fixed λ/criterion/run counts, derives a 50k stall config from one 2-D parent, restores and hashes paired VecNormalize/replay state, freezes the ROS command, and hashes parent/derived checkpoint/config/state plus protocol/scenario in `protocol_manifest.json` |
| [d43_preflight.py](../tools/d43_preflight.py) | ROS-free preflight over nominal `cage_status.csv`: compares CV state with the Gazebo oracle in a centred band, characterises lateral under-read, blocks false C-01/02/03/C-05 behaviour, and emits a checkpoint-bound JSON report (`PASS`, `BLOCKED`, or `INVALID`) |
| [frontier_contrast.py](../tools/frontier_contrast.py) | Paired enforcement-vs-monitoring analysis of the out-of-ODD frontier study (D-35): road-edge-contact rate, max excursion, emergency rate per (scenario, seed) |
| [sr006_smoothness.py](../tools/sr006_smoothness.py) | Dedicated SR-006 verification on its own committed-steer-rate metric (D-39), computed from `cage_status.csv` traces — outside the per-scenario aggregation that would let unrelated failures contaminate it |
| [campaign_e_failure_modes.py](../tools/campaign_e_failure_modes.py) | Post-hoc classification of every campaign FAIL by *which clause* of the pass criterion broke + cage core-safety invariant checks; regenerable numbers behind the E-campaign write-up |
| [plot_f3_figures.py](../tools/plot_f3_figures.py) / [plot_frontier.py](../tools/plot_frontier.py) / [plot_camera_comparison.py](../tools/plot_camera_comparison.py) | Figure generators (Ch.7 training evidence; frontier cage-efficacy; F4-vs-E campaign contrast) — all read committed run artifacts, never live sims, so figures are re-derivable |
| [validate_cv_estimator.py](../tools/validate_cv_estimator.py) | D-43's oracle validation: teleports the robot over a pose grid, compares `CvLaneEstimator` (ey, epsi) against the `PolylineTracker` ground truth, clean + degraded; evidence under `experiments/sim/runs/cv_estimator_val_*` |
| [capture_camera_frames.py](../tools/capture_camera_frames.py) | Camera evidence tool: saves PNG frames (optionally over teleport poses) — proved lane-line visibility at E2 |
| [apply_calibration.py](../tools/apply_calibration.py) | Ingests the M-1..M-5 calibration campaign results, validates schemas, applies the decision rules from the protocol docs, and reports which `[provisional]` SRS/cage parameters should change (prose edits stay manual) |
| [close_odd_tbds.py](../tools/close_odd_tbds.py) | Idempotently substitutes resolved TBD-Q1..Q12 values into designated placeholder cells of docs/08 (never rewrites prose mentions) |
| [build_isaac_urdf.py](../tools/build_isaac_urdf.py), [isaac_import_check.py](../tools/isaac_import_check.py), [isaac_scene.py](../tools/isaac_scene.py), [isaac_ros2_bringup.py](../tools/isaac_ros2_bringup.py), [isaac_train.py](../tools/isaac_train.py), [isaac_eval.py](../tools/isaac_eval.py), [isaac_dr.py](../tools/isaac_dr.py) | The Isaac posterior track (docs/13–14): flatten xacro → importable URDF; headless import smoke-test; shared physics scene (single source of drivetrain constants); ROS2-bridge bring-up reproducing the Gazebo topic contract; in-process PPO training (D-44); deterministic nominal eval; physics/scene domain randomization |
| `reap_sim.sh`, `cam_evidence_session.sh`, `update_traceability.sh` | Shell helpers: orphan-Gazebo cleanup; camera evidence session; traceability regen wrapper |

### 5.3 Configuration files (what governs a run)

| Config | Governs |
| --- | --- |
| `cage/cage.yaml` (v0.6.1) | Every cage threshold; hash-pinned per run |
| `src/cobraflex_rl/config/train_ppo.yaml` | F-track training: MlpPolicy, 6-dim obs, hyperparameters, reward weights, cage block, spawn perturbation |
| `src/cobraflex_rl/config/train_ppo_camera.yaml` | E-track training: CnnPolicy, camera obs block (84×84 gray, k=4, `/camera/image_raw_lane`), H-10 domain randomization, PPO stability levers (`target_kl: 0.5`, `lr_schedule: linear`, `normalize_reward` + `clip_range_vf: 0.2`), `sim_real_time_factor: 1` |
| `train_ppo_camera_2d.yaml`, `train_isaac_2d*.yaml`, `train_isaac_kin2_curric.yaml` | Posterior 2-D variants (D-49/D-50/D-59). Current Gazebo config cap = 0.25 m/s; Isaac full-authority contract = 0.5 m/s |
| `train_sac_camera.yaml`, `train_sac_camera_entfix.yaml` | Gazebo SAC 1-D (D-60): auto-entropy and fixed `ent_coef = 0.005` variants; explicit replay buffer because camera transitions are large |
| `train_sac_camera_2d.yaml`, `train_sac_camera_2d_tuned.yaml`, `train_sac_camera_2d_tuned_entfix.yaml` | Historical/current Gazebo SAC 2-D evidence configs: base, SAC-canonical tuned, and fixed-entropy variants on the 0.25 m/s action cap |
| `train_sac_camera_2d_tuned_entfix_margin022.yaml` | **Preregistered, untrained** fresh-policy contract: entfix parent bounded to 75k with a 0.22 m/s cap, 0.03 m/s minimum margin to C-04, 150k replay covering parent + 50k fine-tune, checkpoint fingerprint, historical-checkpoint rejection and mandatory D-43 preflight |
| `scenarios/_sc_pert_03_protocol.yaml` | Fixed two-arm negative-test protocol: λ=4.0, 50k one-shot continuation, M-P6 percentage criterion and 20 runs per arm/mode |
| Per-run archived configs under `experiments/sim/training/sac_*` | Seed-specific entfix configs and the 200k replay-buffer probe (for example `sac_newcam_entfix_buf200_2024_180k/train_sac_camera_entfix_buf200k.yaml`) preserve the exact run surface alongside metadata/hash |
| `experiments/sim/training/pilot25k_ppo_vs_sac_2024/` | The 25k PPO-vs-SAC verification battery is archived as evidence. Its metadata records config paths/hashes, but the five named `*_pilot25k.yaml` source files are **not present in the current config tree**; exact reconstruction from filenames alone is not claimed. This is a provenance gap to close by restoring hash-matched snapshots, not by inventing live configs |
| `*_centerline.yaml` (oval, complex_a..e, flips) | Track geometry: reward/lane centerline points, `lane_width`, `road_width`; road-centre variants for the off-road check |
| `scenarios/{nominal,edge,perturbed,frontier}/*.yaml` | Executable scenario definitions: initial conditions, perturbations, timeout, `pass_criterion_per_run/scenario`, SR links (schema: `scenarios/_schema.yaml`) |
| `policy/baseline_pd.yaml` | PD gains |

---

## 6. Test inventory — what each test file proves

Latest fully green host baseline (2026-07-15): **517 passed** from the repo root
(CHANGELOG 15.07.2026; `pytest.ini` scopes collection to `cage/tests` +
`policy/tests` + `tools/tests`; `src/` packages are colcon/ament territory,
deliberately excluded). Per-directory counts below are retained only where they
have been re-verified; do not sum the older headings into a newer total.

On this Windows/Python 3.14 host on 20.07, collection reached **496 tests** and
then failed while importing `policy/tests/test_eval_policy_2d.py` because
`ament_index_python` is missing. Use the Ubuntu/Jazzy-capable environment to
regenerate the suite count; the partial collection is not a failed product test.

### 6.1 `cage/tests/` (139 tests) — the cage's verification evidence

| Test file | Proves | Traces to |
| --- | --- | --- |
| `test_c01_lane_boundary.py` | C-01 activation/hysteresis bands, correction sign & saturation, disable flag | SR-001, H-01 |
| `test_c02_heading_limit.py` | Same contract on heading error | SR-002, H-02 |
| `test_c03_ttlc.py` | `compute_ttlc` edge cases (v≈0 → ∞, diverging heading → ∞), urgency ramp, predictive fire | SR-003 |
| `test_c04_speed_ceiling.py` | `v_max(κ)` interpolation floor, throttle-only correction | SR-004 |
| `test_c05_emergency.py` | Triggers 1/3/4/6, persistence requirement, latching + explicit-reset exit, steering freeze | SR-005, SR-007 |
| `test_c05_triggers_extended.py` | Trigger 2 (high-energy, shorter persistence) and Trigger 5 (missing state) | SR-005, SR-007 |
| `test_c05_perception_trigger.py` | Trigger 8 (perception invalid) incl. the `perception_trigger_enabled` back-compat gate | SR-013, SR-014, D-43 |
| `test_c06_rate_limiter.py` | Per-component delta clipping, first-cycle pass-through, disable | SR-006 |
| `test_cage_node.py` | Chain composition in the fixed order, enforcement vs monitoring semantics, `prev_action` tracking, C-05 override wins | docs/04 §Evaluation order |
| `test_cage_node_missing_state.py` | Missing-state counter; "no state ever" → neutral safe stop | SR-007 |
| `test_joint_envelope.py` | SR-010 Part 1: per-rule envelope predicates, post-chain assertion → C-05 Trigger 7, rule pairs/triples | SR-010 |
| `test_oscillation.py` | SR-010 Part 2: alternation-rate window, persistence → emergency, stale-timestamp filtering (the 0.5.1 bug regression test) | SR-010 |
| `test_integration_chain.py` | End-to-end synthetic trajectory across all six rules simultaneously (Phase-2 plan §13(5)) | docs/04 |
| `test_pipeline.py` | PD → cage → logger, 200-cycle synthetic run (pure-Python analogue of the M1 demo) | F2 milestone |
| `test_cage_rules.py` | The real `cage.yaml` loads and instantiates every rule | config integrity |
| `test_logger.py` | CSV schema stability of the cage log | evidence chain |
| `test_sr_spec_version_check.py` | `IncompatibleCageConfigError` on missing/unknown `compatible_sr_spec_version` | config governance |

### 6.2 `policy/tests/` — RL package + campaign spine

| Test file | Proves | Traces to |
| --- | --- | --- |
| `test_baseline_pd.py` | PD control law arithmetic | F2 baseline |
| `test_rewards.py` | Every reward term's weight/sign, termination penalty, progress clamp, config completeness, and default-inert SC-PERT-03 throttle injection | docs/10 §7 |
| `test_cage_bridge.py` | Throttle↔speed maps mirror `vehicle_control_node`; cage invocation contract | D-34 |
| `test_polyline_tracker.py` | Arc-length spawn helper (`pose_at_arclength`) | F4 executor |
| `test_gazebo_lane_env_2d.py` | D-50 2-D action + multi-circuit sampling with the **real** cage in loop, against a fake sim interface | D-49/D-50 |
| `test_eval_policy_2d.py` | 2-D eval action-shape guard and config propagation; requires the ROS/ament import surface during collection | D-50/D-59 |
| `test_camera_geometry.py` | Analytic invariants of the pixel↔ground mapping | D-43 |
| `test_camera_pipeline.py` | Decode → single degradation point → both consumers | D-43 |
| `test_cv_lane_estimator.py` | Estimator recovers known synthetic lane geometries rendered through its own camera model | D-43, SR-014 |
| `test_cage_perception.py` | Supervisor composition → cage state / `perception_invalid` | SR-013/014 |
| `test_perception_health.py` | Stale/dropped/low-confidence detection + persistence budget | SR-013, H-11 |
| `test_lane_plausibility.py` | Geometric + temporal plausibility rejection | SR-014, H-12 |
| `test_visual_degradation.py` / `..._eval_modes.py` | H-10 degradation primitives; eval-only occlusion/false-lane | SR-012, SC-PERT-04..08 |
| `test_visual_domain_randomization.py` | Seeded per-episode DR sampling over the H-10 envelope | SR-012 |
| `test_scenario_loader.py` / `test_scenario_runner.py` / `test_scenario_perturbations.py` | Real scenario YAMLs parse; (scenario, rep) → run config determinism; perturbation injection | docs/05 |
| `test_campaign_metrics.py` / `test_criterion_eval.py` / `test_verdict_aggregation.py` | Metric catalogue arithmetic; safe three-valued criterion evaluation; D-29 gate + D-30 veto + D-38 propagation | docs/06/07 |
| `test_run_campaign.py` | The campaign runner's pure core, including SC-PERT-03 arm expansion, independent per-arm aggregation and manifest checks | D-29/D-30, SR-009 |
| `test_campaign_contract.py` | 0.22 speed-margin delta, canonical C-04 gap, checkpoint fingerprint binding/rejection and historical-config compatibility | D-59 |
| `tools/tests/test_d43_preflight.py` | D-43 schema/coverage failure modes, GE2-anchored heading tolerance, per-input PASS/BLOCK discrimination and metadata provenance | D-43, H-12 |
| `test_frontier_contrast.py` / `test_failure_modes_grid_split.py` | Frontier paired contrast; SC-EDGE-05 in-ODD/OOD attribution split | D-35, D-48 |
| `test_eval_metrics.py` / `test_training_metrics.py` / `test_run_io.py` | Eval aggregation; learning-curve schema; hashing/git metadata | §7.5, §7.2.8 |

### 6.3 `tools/tests/` (7 tests)

| Test file | Proves |
| --- | --- |
| `test_close_odd_tbds.py` | The TBD substitution only rewrites designated placeholder cells, never prose (idempotency contract) |

### 6.4 What the pytest suite does *not* cover (honest scope)

- **ROS2 topic plumbing and Gazebo behaviour** — covered instead by the live
  runs (F2 evidence run, the campaign executor's 1260 + 1970 scored runs) per
  the project rule "typecheck/pytest ≠ feature works" for ROS2 nodes.
- `tests/integration/`, `tests/unit/` at repo root are **empty placeholders**
  (not in `pytest.ini` testpaths).
- Environment-conditional optional dependencies can skip or block collection;
  the current Windows example is the missing `ament_index_python` import above.

---

## 7. From a run to a verdict — the evidence spine

The chain that turns "we ran the sim" into "SR-001: Satisfied" (this is the
core defense narrative for RQ-traceability):

1. **Scenario YAML** (`scenarios/…`) declares initial conditions, stressors,
   `pass_criterion_per_run` (e.g. `M-P1 < 0.05 AND emergency == False`), reps,
   and the SR(s) it verifies.
2. **`run_campaign.py`** expands the matrix (× enforcement/monitoring × reps ×
   seed) and drives the Gazebo executor; each run lands under
   `experiments/sim/campaign*/runs/<run_id>/` with `summary.json` +
   `metadata.json` (git commit, cage-YAML hash, checkpoint hash, scenario hash,
   seed — the reproducibility contract of `experiments/README.md`).
3. **`campaign_metrics` / `scenario_metrics`** compute the per-run metric
   catalogue from the step records.
4. **`criterion_eval`** scores the criterion string → True/False/**None**
   (indeterminate; D-38: excluded from the pass fraction, propagates as
   `insufficient_evidence`, never silently a fail).
5. **`verdict_aggregation`** rolls up per-scenario pass fractions → per-SR
   verdicts under the **D-29** run-count gate; any SR-CL-A failure **vetoes**
   the global verdict (**D-30**).
6. **`docs/07_traceability_matrix.md`** records the verdicts;
   **`check_traceability.py`** proves no artifact is orphaned end-to-end
   (Hazard → SR → Rule → Scenario → Metric → Evidence → Verdict).
7. Figures/analyses (`plot_*`, `frontier_contrast`, `sr006_smoothness`,
   `campaign_e_failure_modes`) read only committed artifacts, so every reported
   number is regenerable.

---

## 8. Deliberately not built / external

| Item | Why |
| --- | --- |
| `sllidar_ros2`, `zed-ros2-wrapper` drivers | Third-party, intentionally untracked (D-32); installed externally |
| Mesh blobs, checkpoints, raw logs, `build/install/log`, `.venv*` | Gitignored; binaries pinned by hash/registry instead |
| A second terminal C-06 pass | Declared F2 approximation in docs/04 §Known approximation; gated on Phase-4 log evidence |
| Isaac ↔ Gazebo checkpoint transfer | Not possible (different renderers/physics); independent Isaac retrains/evals already exist, but remain new posterior baselines rather than transfers or GE4 re-runs (docs/13–14, D-49/D-50) |

## Version log

- **v1.0 (2026-07-07):** first complete inventory. Test/traceability baselines
  verified on the Windows host this date (503 passed / 5 skipped; traceability
  PASS, 0 warnings).
- **v1.1 (2026-07-20):** adds the live PPO/SAC and Gazebo/Isaac contract split,
  current SAC/entfix/buffer config surfaces and 2-D evidence paths; removes the
  false implication that absent pilot YAML filenames are live configs and records
  that provenance gap explicitly. Updates the latest fully green suite to 517
  passed (15.07 host) and records the current Windows `ament_index_python`
  collection limitation without treating it as a regression.
