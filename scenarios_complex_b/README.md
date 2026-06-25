# scenarios_complex_b — complex_b variant of the scenario library (DRAFT)

Parallel scenario set for the **track-'E' camera campaign** on the **complex_b**
circuit. The E-main policy `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` was
trained on complex_b and must be evaluated there. The oval set in `../scenarios/`
is **frozen F4 / 139k-campaign evidence and is left untouched**.

## What is done (mechanical, correct)
Every scenario's `track:` block is re-pointed to complex_b:
- `world: lane_following_oval_complex.world`
- `world_name: lane_following_complex_b`  (SDF name for the gz teleport services)
- `centerline: complex_b_right_lane_centerline.yaml`  (reward target / Frenet frame)
- `road_centerline: complex_b_centerline.yaml`  (off-road geometry, docs/11 §3.5)

The campaign plumbing is wired end-to-end (and dry-run-validated):
`tools/run_campaign.py` (`--scenario-dir`, `--model-path`, resolves + passes
centerline/road_centerline/world_name) → `eval_scenario_batch.launch.py`
(new `centerline`/`road_centerline`/`world_name` args) → `eval_policy`.

## Verdict scoring — D-45 (controlled safe stop = pass on the SR limit)
The per-run pass criterion of the eight **adverse safety** scenarios (SC-EDGE-02,
SC-EDGE-03, SC-PERT-01, SC-PERT-02, SC-PERT-04, SC-PERT-06, SC-PERT-09, SC-PERT-10)
**drops `emergency == False`**: a cage-commanded controlled stop is a *safe outcome*,
so the run passes if the safety limit held (`M-S1 < 0.16`, plus `road_edge_contact ==
False` where present). A real breach (`M-S1 >= d_max` / road-edge) still fails.
SC-PERT-07 (SR-013, stop *required*: `emergency == True`) and the nominal scenarios
(gated by `M-P2 == 1`) are unchanged. This clears the SR-CL-A vetoes behind the 139k
`NOT SATISFIED`, but is **not** sufficient for `SATISFIED`: SR-013's D-29 family
coverage gap and the SC-PERT-05 / SC-EDGE-05 indeterminates remain. See
`docs/DECISIONS.md` D-45.

## Geometry pass (start points) — DONE; confirm in Gazebo
Static analysis of `complex_b_right_lane_centerline.yaml` (closed loop, perimeter
**19.93 m**, 384 pts): **s=0 is a LEFT curve** (R≈1.13 m) — *not* a straight, so the
oval `start_s_m: 0.0` "straight start" was wrong. The clean **straight is s≈1–5 m**
(dead-straight s≈2–4), **curve entry s≈5**, the scallop curves s≈5.5–9 and 15–19, the
sole RIGHT curve (self-approach pinch) s≈12.6. Applied:
- **`start_s_m: 0.0 → 2.0`** for every straight-start scenario (mid-straight, ~3 m runway).
- **SC-NOM-02 `1.5 → 5.0`** (oval "curve entry"; 1.5 is a straight on complex_b).
- **SC-NOM-03** kept **0.0** (full-circuit run covers the whole loop regardless of start).

Two oval assumptions turned out **inert** on inspection (no edit needed):
- **`straight_completed` event** is **not consumed** by `scenario_runner` — the run is
  bounded by `timeout_s` only (`max_steps = timeout_s / 0.10`). It is decorative.
- **`perturbations.at_time_s = 5 s`** is only **1 m** of travel at 0.2 m/s, so the
  stressor lands ~1 m after the (now-correct) start — on the straight. OK as-is.
- **`pose` lateral/heading** are relative offsets (same lane width) — transfer.

## STILL OPEN before a verdict run
- **D-29 coverage of the camera SRs — RESOLVED (2026-06-25, documented exception).**
  `--dry-run` feasibility shows **SR-012 / SR-013 / SR-014 have `nominal = 0`** — they are
  verified by adverse (PERT) scenarios only, because a clean nominal run cannot exercise
  "degraded visual input / loss of perception / suspect estimate". As SR-CL-A they would
  read INCOMPLETE under the strict nominal+adverse D-29 rule. **Resolution: documented D-29
  exception for the camera-stressor SRs** — their *nominal companion is the clean-input
  SC-NOM-01 297k eval* (D-46: SC-NOM-01 is the no-false-trigger anchor for the camera SRs,
  exercising them in the clean-input regime), so the nominal arm IS covered, just not via a
  scenario that `references_SR: [SR-012/013/014]`. The adverse arm is the SC-PERT family.
  This is the same shape as the F4 D-29 reasoning; record it in the GE4 verdict write-up.
  **SC-PERT-07 reps bumped 20 → 25** (SR-013 sole dedicated scenario, SR-CL-A min 25). ✓
- **SC-PERT-09 / SC-PERT-10 — DONE (2026-06-25).** complex_b texture-variant worlds
  built (texture-only, D-37 Option A): `lane_following_complex_b_worn_{25,50,75}.world`
  (faded markings, 25 = barely discernible … 75 = mildest) and
  `lane_following_complex_b_particles.world` (road clutter / debris distractors). The
  dead oval `_worn`/`_wet` references are gone. **SC-PERT-09** = worn markings, points at
  the mid level `_worn_50` as the canonical verdict run; **SC-PERT-10** = particles
  (repurposed from the never-existing "wet" — no wet texture was ever produced; clutter is
  the matched concept). Textures live in `src/cobraflex/materials/road_assets/tracks/` and
  are synced to `install/` (colcon build of `cobraflex`).
  - **Worn 3-level pilot — DONE (2026-06-25, Gazebo, 297k enf rep0, monotonic gradient):**
    | level | cv_ok frac | steps | emergency | M-S1 | reading |
    |---|---|---|---|---|---|
    | `_worn_25` (faintest) | 0/1 | 1 | step 1 | 0.007 | perception **lost** → instant controlled stop |
    | `_worn_50` (mid) | partial | 40 | step 40 | 0.113 | perception **degraded** → stop at ~4 s |
    | `_worn_75` (mildest) | 150/150 | 150 (full) | none | 0.050 | perception **fine** → drives clean, 5 cm |
    Clean monotone envelope: as the markings fade the CV estimator loses the lane and the
    cage fail-safes to a Trigger-8 controlled stop rather than driving blind (all pass under
    D-45: M-S1 < d_max, no road-edge). SC-PERT-09 keeps `_worn_50` as the canonical verdict
    level; the 25/75 worlds are the pilot endpoints. To sweep all three in one verdict run,
    extend the `world_variant` block to a world list (runner change — deferred).
- **SC-PERT-05 (`low:/high:`) — DONE (2026-06-25, verified already wired).** The labelled
  two-arm criterion IS resolved per-run: `resolve_perturbation` tags each rep with
  `level_index = rep % n_levels` (low arm = level 0.2, high arm = level 0.5) and
  `eval_policy._evaluate_scenario` scores the matching arm via `criterion_eval.labelled_arms`
  (the `is_labelled(expr) and pert.active` branch). Empirically confirmed rep 0/2 → `low`,
  1/3 → `high`. The earlier "not wired" note predated this wiring. (`evaluate_labelled` /
  `evaluate_labelled` per-scenario pooling also exists for non-level-resolvable arms.)
- **SC-EDGE-05 (parameterised_grid) — WIRED + GAZEBO-VALIDATED (2026-06-25); now determinate.**
  No longer indeterminate: the scenario produces a real True/False verdict.
  **(a) Grid expander — DONE & unit-tested.** `scenario_runner.expand_grid` expands the 5
  `grid_anchors` into 20 deterministic grid points (4 boundary-bracket factors 0.85–1.30 per
  anchor, the nominal 1.0 seed always included), and `derive_run_config` dispatches
  `initial_conditions.type: parameterised_grid` to a grid path: `rep % 20` selects the point
  (5 reps × 20 points = the 100-run budget), mapping `d_m → lateral_offset_m` (C-01),
  `theta_deg → heading_error_rad` (C-02), `v_mps → fixed_speed` (C-04). Because `eval_policy`
  already forwards `run_config.reset_options` to `env.reset`, the lateral/heading/speed
  co-activation IC now **actually injects** end-to-end — fixing the F4 "zero co-activation
  as-run" root cause. Carried on `RunConfig.grid_point` (anchor id + expected_activation),
  now also written into the run summary for the SR-010 expected-vs-observed analysis.
  **(b) Per-run counters — DONE & validated.** The cage's per-cycle `joint_envelope_violated` /
  `oscillation_persistent` flags are surfaced in the env `info`, captured in the eval records
  (+ the aligned trace CSV), and aggregated in `_evaluate_scenario` into
  `joint_envelope_assertion_failures` (#violated cycles) and `inter_cycle_oscillations` (rising
  edges) — the exact tokens SC-EDGE-05's criterion reads.
  **Gazebo smoke run (297k, SC-EDGE-05 enf rep0):** step-1 `ey = 0.0850` = the injected grid
  seed (d=0.10 × 0.85), trace CSV aligned, counters match a CSV recount; verdict toggled
  True/False across re-runs of the *same* IC (jev 0↔1) — the C01_C02 factor-0.85 co-activation
  is **borderline**, exactly the run-to-run variability the 5-reps-per-point design samples.
  Tests in `test_scenario_runner.py` (10 new — grid expander, ttlc inversion, curvature finder; 462 pass).
  **(c) Curvature / TTLC seed hooks — DONE (2026-06-25), kappa Gazebo-validated.**
  - **`kappa_seed_rad_m` → curve spawn (the C-04 curvature anchors): DONE & validated.**
    New `PolylineTracker.arclength_at_curvature(target)` scans the track and returns the
    arc-length whose local curvature best matches the seed; `gazebo_lane_env.reset` overrides
    `start_s` with it so the vehicle spawns on a curve of the requested curvature. **Gazebo
    (C04_C06, kappa 0.51):** spawn landed at (-1.64, 1.40) = the κ≈0.51 curve (vs the straight
    s=2 at -0.84,-1.62), and **C-04 fired** (rules C-04,C-05,C-06) — the curvature co-activation
    that was impossible before (the anchor used to spawn on the straight, κ=0). Unit-tested on
    the real complex_b geometry.
  - **`ttlc_seed_s` → heading (the C-03 anchor): IMPLEMENTED + pure-tested; a cage-dynamics
    caveat.** `scenario_runner` inverts C-03's `TTLC = (d_max-|d|)/(v·sin|psi|)` to set the
    heading that yields the seed TTLC (unit-tested: reproduces 0.9 s). **Gazebo (C01_C03):** the
    IC injects (ey≈0.069, ψ≈23.8°) but the **labelled C-03 does not fire** — at the at-rest spawn
    `v≈0` makes C-03's TTLC `inf` (`v < v_min_estimate`), and the strong seeded heading trips the
    earlier-in-chain **C-02** first → emergency in ~3 cycles before speed builds. So the anchor
    co-activates **C-01+C-02**, not the labelled C-01+C-03 (a real chain-order/at-rest finding,
    surfaced by the `grid_point` expected-vs-observed log). Forcing C-03 specifically would need a
    moving-spawn IC (scenario refinement) — noted, low value (SR-010 only needs ≥2 rules, which holds).
- **SC-NOM-03 — DONE (2026-06-25).** `timeout_s 120 → 300 s` (~3 laps at 0.2 m/s over the
  19.93 m perimeter); description + `start_s_m` comment de-oval-ised ("three laps of complex_b").
- **flip (generalization) — DONE & GAZEBO-VALIDATED (2026-06-25): SC-FRONT-07.** A fully
  scored mirrored-geometry frontier scenario. `lane_following_complex_b_flipV.world`
  (texture-only Y-flip) + **matching Y-mirrored scoring centerlines**
  `complex_b_flipV_{,_right_lane}_centerline.yaml` (in `src/cobraflex_rl/config/`, built into
  `install/`; mirror `y → -0.1908 - y` about the track-box centre y=-0.0954 = the bbox centre).
  **Mirror axis confirmed empirically in Gazebo** (step-1 ey ≈ -0.004 → spawn lands on the
  flipped lane), so the metrics are now valid. Scenario `scenarios_complex_b/frontier/sc_front_07.yaml`
  (frontier/cage-efficacy, `references_SR: [SR-001, SR-005]`, criterion `road_edge_contact == False`,
  enf/mon 25/25). **Finding (297k, enf rep0, PASS):** the policy generalizes to the flipped
  **straights** (ey ≈ 2 cm, clean) but the flipped **curves** — reversed handedness, never seen in
  training — exceed its envelope; at step ~195 it drifts to ey 0.11 and the cage controlled-stops it
  (C-03 TTLC + C-05), **no road-edge contact** → the cage holds the OOD generalization gap safely.
  (`…_flipH.world` also exists for the horizontal-mirror variant — same recipe, scenario not yet
  authored.)
- **SC-EDGE-03** — kept on the straight (s=2.0) per its "nominal straight operation"
  text; to stress C-04's curvature-parameterised ceiling, start ~4.5 so the t=5 s pulse
  lands in the s≈5.5 curve.
- **Gazebo confirmation** — the start points above are a static-geometry pass; spot-check
  spawn pose/heading in RViz/Gazebo before the verdict campaign.

## How to run (Ubuntu + ROS2 Jazzy + Gazebo)
```bash
PEAK=experiments/sim/training/ppo_newcam_complex_b_2024_1M/checkpoints_peak/cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip
python tools/run_campaign.py   --scenario-dir scenarios_complex_b   --model-path $PEAK   --train-config $(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config/train_ppo_camera.yaml   --seeds 2024 --modes enforcement,monitoring   --out experiments/sim/campaign_e_297k
# add --dry-run first to print the matrix + D-29 feasibility with no Gazebo.
```
