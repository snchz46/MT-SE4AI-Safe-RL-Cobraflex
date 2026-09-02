# Tools

Verification and synchronisation utilities for the repository.

> **Status (2026-09-01).** The campaign tooling below served three evaluation arms:
> the **2-D PPO 550k campaign** (`campaign_2d_ppo550k/` — **the verdict of record**,
> D-69), the **track-'E' camera campaign** (`campaign_e_v2/`, GE4-V2 — the frozen G4
> gate record) and the **F-track baseline** (`campaign/`, frozen). The `isaac_*`
> scripts belong to the posterior sim-to-real track (docs/13–14); the deployment
> scripts — `run_deploy_gate.sh`, `run_physical_lap.sh`, `preflight_deploy.py`,
> `score_lane_capture.py`, `sim2real_probe.py`, `select_sim2real_checkpoint.py`,
> `measure_yaw_authority.py` — belong to **Phase 5**, which closed 01.09.2026
> (docs/17). Phase-5 tooling produced posterior evidence only: it re-scores no gate.

## Traceability & registers

- `check_traceability.py` — verifies bidirectional traceability between hazards, SRs, cage rules, scenarios and metrics. Hard gate before every Gate review. Run: `python tools/check_traceability.py`. Use `--strict` to fail on warnings.
- `check_scenario_yaml.py` — validates scenario YAML files against the executable schema. Default mode accepts explicitly deferred stubs with warnings; use `--strict` to fail on those warnings in later scenario-library gates.
- `sync_hazard_register.py` — extracts the machine-readable table from `docs/02_hazard_register.md` and writes `docs/data/hazard_register.csv`. Run: `python tools/sync_hazard_register.py [--verbose]`.
- `sync_safety_requirements.py` — extracts the machine-readable table from `docs/03_safety_requirements.md` and writes `docs/data/safety_requirements.csv`. Run: `python tools/sync_safety_requirements.py [--verbose]`.
- `traceability_matrix.csv` — machine-readable form of the traceability matrix, kept in sync with `docs/07_traceability_matrix.md`.
- `close_odd_tbds.py` — historical helper that substituted resolved TBD values into `docs/08` (later closures were done by hand — see docs/08 §0.1 v0.5 note).

## Campaign & evaluation

- `run_campaign.py` — orchestrates a scenario-validation campaign (run matrix → per-run → per-scenario → per-SR D-29 / global D-30 verdicts). `--dry-run` validates the plan + D-29 feasibility without Gazebo. SC-PERT-03 expands into separately-scored `released`/`stall_variant` arms and requires `--two-arm-manifest`; a config whose `campaign_contract` requires D-43 qualification also requires `--d43-preflight-report` with a provenance-valid nominal-enforcement `PASS` for the exact checkpoint **and train-config hashes**. The check happens before Gazebo and is recorded in the campaign report; the per-run CSV records the arm and emergency outcome.
- `sc_pert_03_protocol.py` — preregisters and prepares the SC-PERT-03 2-D negative test. `prepare` fixes λ=4.0/50k/criterion/run counts against a concrete parent checkpoint plus paired VecNormalize/replay state; `run` launches the frozen fine-tune at most once; `finalize` hashes the derived checkpoint, VecNormalize, replay and metadata. The completed manifest is the campaign runner's two-arm policy map.
- `campaign_e_failure_modes.py` — post-hoc breakdown of a camera campaign: classifies every FAIL by broken clause (`ms1_breach` / `edge_contact` / `emergency_only` / `other`), splits every PASS by mode (`pass_clean` vs `pass_with_emergency`), checks the cage core-safety invariants across enforcement runs, computes the F4→E baseline contrast and the SC-EDGE-05 in-ODD/OOD grid split (SR-010, D-48). Pure Python, any host. Run: `python tools/campaign_e_failure_modes.py --campaign-dir experiments/sim/campaign_e_v2`.
- `sim2real_probe.py` — offline sim-to-real transfer gate for a camera checkpoint (M-7/D-71). Scores the policy's **lane response** on recorded physical frames (steering swing, lane-independent bias, bias/swing, share of right turns) against the same policy's response on Gazebo frames, and fails closed. Open-loop on recorded frames, so it can *falsify* transfer but not establish it — a necessary condition to check before booking track time, never instead of driving. `--rectify` undistorts the physical frames into the canonical sim camera using the M-6 intrinsics. Run: `python tools/sim2real_probe.py --checkpoint <ckpt>.zip --real experiments/physical/datasets/circuit_export --sim <gazebo frames dir>`. Exit 0 PASS / 1 INVALID / 2 BLOCKED.
- `sr006_smoothness.py` — SR-006 (C-06 committed-steer smoothness) scored out-of-band on its own metric across campaign runs (D-39); avoids SR-006 inheriting unrelated per-scenario fails via its `ALL` scenario listing.
- `frontier_contrast.py` — text aggregation of the frontier (SC-FRONT) cage-efficacy study as the paired enforcement-vs-monitoring contrast (D-35): per-cell road-edge-contact rate and max-excursion reduction.
- `plot_frontier.py` — figure companion to `frontier_contrast.py`: renders `fig_frontier_*.png` from `<campaign-dir>/runs/*/summary.json`, aggregating over the N reps per cell. Auto-invoked by `run_campaign.py`; needs matplotlib (use the figure host).
- `plot_camera_comparison.py` — track-'E' comparison figures (camera policy vs CV baseline vs F-track) from eval/campaign summaries.
- `plot_f3_figures.py` — F3 training/eval figure set (learning curves, multi-seed panel; historical baseline).

## Camera / CV estimator (track 'E')

- `validate_cv_estimator.py` — GE2 oracle validation of the cage's deterministic CV lane-estimator (D-43) against ground truth under controlled degradations (the evidence behind the glare 0.3/0.6 levels used by SC-PERT-04/12/13).
- `d43_preflight.py` — offline campaign-qualification gate over one or more nominal `cage_status.csv` traces. It compares CV vs Gazebo-oracle state in a centred band, reports the separate lateral under-read residual, binds inputs to sibling run metadata/checkpoint hashes, and exits 0 `PASS`, 2 `BLOCKED`, or 1 `INVALID`. Example: `python tools/d43_preflight.py <run-dir> --output <report.json>`.
- `calibrate_d43_c02.py` — bounded Gazebo calibration of the D-43 heading interface against canonical C-02. It builds disjoint seed-2024/seed-42 calibration-validation cells, injects real heading faults during motion through a calibration-only eval hook, logs GT solely as an offline oracle, and writes raw CSV, hash-bound JSON, Markdown/PNG evidence. Default estimator settings reproduce the frozen baseline; select the qualified Gazebo candidate with `--heading-fit-mode joint_pair_quadratic --heading-gain 1.60`. Run the 28-cell matrix with `python tools/calibrate_d43_c02.py --collect --steps 40 --injection-step 12 --heading-fit-mode joint_pair_quadratic --heading-gain 1.60`.
- `capture_camera_frames.py` — grabs native camera frames from a running sim (calibration / estimator debugging).
- `apply_calibration.py` — applies M-1/M-2 calibration results to config parameters.

## Physical deployment (Phase 5, docs/17)

- `preflight_deploy.py` — turns the staged bring-up of docs/17 §4 into a PASS/FAIL verdict: `stage0` (camera alone), `stage1` (chain flowing), `stage2` (actuation envelope, **wheels off the ground**), `lanecheck` (parked estimator quiet, with a **span** check as well as a dispersion one). `--true-ey <metres>` closes the other half of M-7 §3b — whether C-01 fires late — and **was run on 31.08.2026**: rectified, C-01 fires at a true 151/158 mm, so M-7 §4's under-read does not survive rectification (docs/17 §10.2). Two caveats from D-79: `sd_ey ≤ 10 mm` alone returned PASS on a 43.3 mm swing, which is why the span gate was added; and no dispersion **or** span gate can catch a stable bias, so `--true-ey` must be run at **several** locations — one spot characterises one spot.
- `run_deploy_gate.sh` — the D-72 sim-to-real gate: swing retention, bias/swing and right-turn share of a checkpoint against real imagery, raw and rectified arms.
- `run_physical_lap.sh` — starts ONE physical run: the evidence bag and the Layer-3 RL chain bound to a single run id and stopped together, after probing the **running** Layer-2 nodes (`capture_fps`, the ZED loop-closure overrides) into the run's `layer2.json`. Warns on the two configurations that ended runs on 26.08 (loop closure on, rviz running). The lane image topic is deliberately *not* bagged — `frame_capture_node` keeps the frames around each perception event instead, from RAM. Example: `tools/run_physical_lap.sh --label lap01 --checkpoint /abs/path/to/ckpt.zip`.
- `record_lane_dataset.py` — labelled real-lane dataset capture (PNG at 5 Hz, labels inline), without the I/O load that crashed the Jetson on 18.08.2026. Camera only; no deploy chain needed.
- `score_lane_capture.py` — scores a true-position capture (D-78): arc length from tape-measured floor stations rather than any odometry, per-segment pairing rate and `ey` error against the operator's held offset, and the closed-loop `∮|κ|ds / (laps·2π)` test whose acceptance band was fixed in advance. It is what produced D-79.
- `select_sim2real_checkpoint.py` — ranks training checkpoints for **transfer and cage-independence**, never reward: the criterion that chose the deployed v2 1650k over its reward peak (3.0 % nominal intervention against 35.0 %).
- `sim2real_probe.py` — see *Campaign & evaluation* above; the offline gate `run_deploy_gate.sh` drives.
- `measure_yaw_authority.py` — bench sweep of the wheel differential, the discriminator for where the plant's yaw compression ends (M-7 §5: achieved/commanded falls 0.482 → 0.436 → 0.341, so no constant gain fits it). Self-test passes 8/8; **the ROS path was never run** — Phase 5 closed first, and it is kept as the named discriminator for future work (ch.12 T2).
- `measure_yaw_gain.py`, `measure_offset_response.py` — earlier single-quantity bench probes for the same channel and for the lateral response.
- `calibrate_camera_hfov.py` — the M-6 measurement: effective HFOV and distortion of the physical lane camera against a printed target. It is what refuted the inherited 90°.
- `export_bag_topics.py` — flattens a physical run's rosbag into per-topic CSV for offline analysis.
- `lane_probe.py`, `cv_controller_node.py` — offline/ROS helpers for inspecting the D-43 estimator on recorded or live frames.
- `cam_evidence_session.sh` — wraps a camera-only evidence session (no policy, no cage).

## Isaac Sim (posterior track, docs/13–14)

- `build_isaac_urdf.py`, `isaac_import_check.py`, `isaac_scene.py`, `isaac_ros2_bringup.py` — URDF export, import validation, scene/bring-up.
- `isaac_train.py`, `isaac_eval.py`, `isaac_dr.py` — in-process RL training (defaults to the 2-D action config, D-50), evaluation and domain randomisation.

## Manuscript build

- `build_thesis_docx.py` — renders `manuscript/draft_v5/` (front matter + condensed body + appendices A–I) to a submission `.docx`. **The layout constants at the top of the file are the authority**, and they are deliberately *not* the guidelines' 12 pt Times New Roman at 1.5: the author set **Arial 11 pt, 1.15 line spacing, 1.0" left/right margins**. Changing them changes the page count, so re-run the budget below after any edit. Run: `python tools/build_thesis_docx.py --out <path>.docx`.
- `thesis_page_budget.py` — drives Word to repaginate the built DOCX, exports a PDF and reports where each chapter starts and **how many pages the body occupies** (the 80–100 page acceptance check). Requires **Word COM (pywin32)** and therefore a Windows host — it cannot run on the Ubuntu compute host.

## Analysis & figures

- `plot_campaign_contrast.py` — enforcement-vs-monitoring contrast figures from a campaign report.
- `rescore_recovery_clause.py` — re-scores SC-EDGE-01's heading-recovery clause under the D-68 correction (band referenced to each run's own steady-state envelope). The 2.0 s bound itself is unchanged; this is the audit that showed the clause measured ripple rather than recovery.
- `sync_checkpoint_registry.py` — keeps the checkpoint registry in step with the training runs on disk (checkpoints themselves are gitignored, so the registry is how a run is identified by hash rather than by path).
- `reap_sim.sh` — kills orphaned Gazebo/`gz sim` processes left by an interrupted run. **`GZ_PARTITION` isolates topics, not processes**, so an unguarded reaper will also kill a concurrent trainer — that is incident I-1 (docs/17 §7), and the guard is now pinned by a test.
- `update_traceability.sh` — convenience wrapper: regenerates both registers' CSVs and runs `check_traceability.py`.

## CI integration

These scripts are designed to be runnable in a CI pipeline. The recommended integration:

- Pre-commit hook: `check_traceability.py` runs on changes to `docs/`.
- Pre-push hook: full test suite runs.
- Nightly build: full traceability + scenario YAML validation + cage unit tests.
