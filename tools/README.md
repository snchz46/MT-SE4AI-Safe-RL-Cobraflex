# Tools

Verification and synchronisation utilities for the repository.

> **Status (2026-07).** The campaign tooling below served two evaluation arms:
> the **track-'E' camera campaign** (`campaign_e_v2/`, GE4-V2 — the verdict of
> record) and the **F-track baseline** (`campaign/`, frozen). The `isaac_*`
> scripts belong to the posterior sim-to-real track (docs/13–14).

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

- `preflight_deploy.py` — turns the staged bring-up of docs/17 §4 into a PASS/FAIL verdict: `stage0` (camera alone), `stage1` (chain flowing), `stage2` (actuation envelope, **wheels off the ground**), `lanecheck` (parked estimator quiet). Pass `--true-ey <metres>` to `lanecheck` to close the other half of M-7 §3b — whether C-01 fires late — which no run has done yet.
- `run_deploy_gate.sh` — the D-72 sim-to-real gate: swing retention, bias/swing and right-turn share of a checkpoint against real imagery, raw and rectified arms.
- `run_physical_lap.sh` — starts ONE physical run: the evidence bag and the Layer-3 RL chain bound to a single run id and stopped together, after probing the **running** Layer-2 nodes (`capture_fps`, the ZED loop-closure overrides) into the run's `layer2.json`. Warns on the two configurations that ended runs on 26.08 (loop closure on, rviz running). The lane image topic is deliberately *not* bagged — `frame_capture_node` keeps the frames around each perception event instead, from RAM. Example: `tools/run_physical_lap.sh --label lap01 --checkpoint /abs/path/to/ckpt.zip`.
- `record_lane_dataset.py` — labelled real-lane dataset capture (PNG at 5 Hz, labels inline), without the I/O load that crashed the Jetson on 18.08.2026. Camera only; no deploy chain needed.

## Isaac Sim (posterior track, docs/13–14)

- `build_isaac_urdf.py`, `isaac_import_check.py`, `isaac_scene.py`, `isaac_ros2_bringup.py` — URDF export, import validation, scene/bring-up.
- `isaac_train.py`, `isaac_eval.py`, `isaac_dr.py` — in-process RL training (defaults to the 2-D action config, D-50), evaluation and domain randomisation.

## CI integration

These scripts are designed to be runnable in a CI pipeline. The recommended integration:

- Pre-commit hook: `check_traceability.py` runs on changes to `docs/`.
- Pre-push hook: full test suite runs.
- Nightly build: full traceability + scenario YAML validation + cage unit tests.
