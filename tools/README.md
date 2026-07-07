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

- `run_campaign.py` — orchestrates a scenario-validation campaign (run matrix → per-run → per-scenario → per-SR D-29 / global D-30 verdicts). `--dry-run` validates the plan + D-29 feasibility without Gazebo (runs anywhere); a real run drives Gazebo on the Ubuntu+Jazzy host. Track-'E' knobs: `--scenario-dir scenarios_complex_b`, `--model-path <checkpoint.zip>`, `--train-config train_ppo_camera.yaml`. The per-run CSV carries an `emergency` column and the report an `n_pass_emergency` count, splitting how each pass happened (D-45: controlled stop vs overcame). After a campaign that includes frontier scenarios it auto-renders the cage-efficacy figures (`--no-frontier-plots` to skip).
- `campaign_e_failure_modes.py` — post-hoc breakdown of a camera campaign: classifies every FAIL by broken clause (`ms1_breach` / `edge_contact` / `emergency_only` / `other`), splits every PASS by mode (`pass_clean` vs `pass_with_emergency`), checks the cage core-safety invariants across enforcement runs, computes the F4→E baseline contrast and the SC-EDGE-05 in-ODD/OOD grid split (SR-010, D-48). Pure Python, any host. Run: `python tools/campaign_e_failure_modes.py --campaign-dir experiments/sim/campaign_e_v2`.
- `sr006_smoothness.py` — SR-006 (C-06 committed-steer smoothness) scored out-of-band on its own metric across campaign runs (D-39); avoids SR-006 inheriting unrelated per-scenario fails via its `ALL` scenario listing.
- `frontier_contrast.py` — text aggregation of the frontier (SC-FRONT) cage-efficacy study as the paired enforcement-vs-monitoring contrast (D-35): per-cell road-edge-contact rate and max-excursion reduction.
- `plot_frontier.py` — figure companion to `frontier_contrast.py`: renders `fig_frontier_*.png` from `<campaign-dir>/runs/*/summary.json`, aggregating over the N reps per cell. Auto-invoked by `run_campaign.py`; needs matplotlib (use the figure host).
- `plot_camera_comparison.py` — track-'E' comparison figures (camera policy vs CV baseline vs F-track) from eval/campaign summaries.
- `plot_f3_figures.py` — F3 training/eval figure set (learning curves, multi-seed panel; historical baseline).

## Camera / CV estimator (track 'E')

- `validate_cv_estimator.py` — GE2 oracle validation of the cage's deterministic CV lane-estimator (D-43) against ground truth under controlled degradations (the evidence behind the glare 0.3/0.6 levels used by SC-PERT-04/12/13).
- `capture_camera_frames.py` — grabs native camera frames from a running sim (calibration / estimator debugging).
- `apply_calibration.py` — applies M-1/M-2 calibration results to config parameters.

## Isaac Sim (posterior track, docs/13–14)

- `build_isaac_urdf.py`, `isaac_import_check.py`, `isaac_scene.py`, `isaac_ros2_bringup.py` — URDF export, import validation, scene/bring-up.
- `isaac_train.py`, `isaac_eval.py`, `isaac_dr.py` — in-process RL training (defaults to the 2-D action config, D-50), evaluation and domain randomisation.

## CI integration

These scripts are designed to be runnable in a CI pipeline. The recommended integration:

- Pre-commit hook: `check_traceability.py` runs on changes to `docs/`.
- Pre-push hook: full test suite runs.
- Nightly build: full traceability + scenario YAML validation + cage unit tests.
