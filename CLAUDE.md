# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Keep lean (<250 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-08-24.

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
> **Active work since 08.2026 is Phase 5** (physical deployment, `E5:` commits): the trunk policy
> drove the real track on 18.08 and did **not** transfer (D-71), and the sim-to-real **v2** policy
> (D-72) answers that. Everything under Phase 5 — v2, `campaign_v2`, every physical measurement —
> is **posterior evidence**: it re-scores no gate and does not touch the D-69 verdict of record.

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
- **F-track ground state — method validation (D-67). F4 closed 2026-06-10, G3 passed 2026-06-03.**
  Oval library **24 scenarios**; the campaign runner + pure-Python verdict spine (D-29/D-30) and the live
  Gazebo executor (`run_campaign.execute_run` → `eval_scenario_batch.launch.py`, GZ_PARTITION isolation,
  orphan-gz reaping, retries, resume) were built here — that machinery is what every later arm reuses.
  Verdict-bearing run: **1260 runs**, seed 2024 (D-36), every scenario × {enf, mon}; **global `SATISFIED`**,
  all 7 SR-CL-A (`experiments/sim/campaign/campaign_report.json`). Central finding: **M-S2 = 0 in both modes
  in-ODD** — with perfect perception the cage is **latent**; its value only shows out-of-ODD (seed-123 cage
  removes 96–100 % of road-edge contacts). SR-006 Satisfied via D-39; D-38 reconciled the aggregator's
  indeterminate→fail collapse. Detail: CHANGELOG 03.06–10.06 "F4" + 02.07 "G4"; docs/07.
- **GE4-V2 — the frozen G4 gate record (2026-06-28; G4 CLOSED 02.07.2026, docs/07). Superseded as *verdict of
  record* by the 2-D trunk (D-69) and NOT re-scored.** D-41 architecture; the cage reads a **dedicated
  deterministic CV lane-estimator** (D-43), not the camera. **1970 runs** on the 297k E-main (seed 2024,
  28 complex_b scenarios × {enf, mon}, 0 errors; `experiments/sim/campaign_e_v2/`). Global **`NOT SATISFIED`
  (literal), blocking SR-002/003 only** — both fail *only* SC-EDGE-01's oval-legacy 2.0 s recovery clause
  (max M-P4 14.4° ≤ 25°, 0 emergency) and are **Satisfied on their own criterion (D-47)** → no SR-CL-A safety
  predicate breached. SR-001 Satisfied (ruta-1 clipped SC-EDGE-02's IC to the ODD → 28/30; the 2 residuals are
  the D-43/H-12 confident under-read; ruta-2b unnecessary + reverted, D-48). SR-012/013/014 Satisfied; SR-010
  genuine CL-B (30/85 in-ODD co-activation); SR-009 N/A-by-construction (D-49). **0 in-ODD road-edge contacts**;
  the cage **removes** perception-degradation failures the bare policy commits (SC-PERT-13 40/40 enf vs 0/40
  mon) — the latent→active flip, first measured here. The 117 enf contacts are all out-of-ODD. Multi-seed N=5
  (13.07): 3/5 constraint-respecting — the training curve does **not** classify the basin. Historical:
  `campaign_e_297k/` (V1), `campaign_e/` (139k). Detail: docs/11 §8.4–8.5; CHANGELOG 27–28.06 / 13.07.
- **E-main lineage (development history).** 425k oval peak (15.06; GE4 re-run prepared, never launched,
  docs/11 §8.3) → **complex_b 297k peak** (22.06, perimeter 19.22 m, 2.2× the oval):
  `ppo_newcam_complex_b_2024_1M` stopped by hand at ~662k, `ep_rew_mean` peaks **822.9 @ ~297k**, peak rescued
  and hash-verified (`44c8e912…`, gitignored) — **the chain holds by hash, not by path** (docs/11 §8 path note).
  Nominal SC-NOM-01 enforcement: 4.88 laps, |ey| **10.9 mm**, 0 emergencies, cage latent in-ODD both modes;
  **RL beats the CV baseline on the same track** (10.9 vs 17.2 mm), reversing the oval finding. Laps are not
  comparable across tracks.
- **THE 2-D TRUNK — PPO cap 0.22, checkpoint 550k (D-66; trunk per D-67). CAMPAIGN CLOSED 31.07.2026 — the
  VERDICT OF RECORD (D-69), and the last simulation campaign before physical deployment.** Fresh PPO 2-D 1M on
  complex_b: `ep_rew_mean` peaks **1755 @ 472k** (SAC 2-D never exceeds ~200); cage **latent for safety** across
  training. Checkpoint chosen **by driving + cage %, not reward** — the reward-peak 475k is the *worst*
  candidate (14 safety interventions, max |ey| 49 mm); **550k** wins: `SC-NOM-01` enforcement **5.32 laps,
  |ey| 8.6 mm (max 27), 0 emergencies, 0 safety interventions** (C-06 only). D-43 preflight **PASS 7/7**.
  **Verdict:** `experiments/sim/campaign_2d_ppo550k/` — **1890 runs, 0 errors** (27 complex_b scenarios ×
  {enf, mon}, seed 2024; SC-PERT-03 excluded — closed D-64). Global **`NOT SATISFIED` literal, blocking
  SR-002/003 only**, again *only* via SC-EDGE-01's recovery clause (0 emergencies, max M-S1 0.043 m, max M-P4
  14.2°) → **D-47 verbatim**. **0 in-ODD road-edge contacts in enforcement** (bare policy commits 60);
  out-of-ODD 56 vs GE4-V2's 117. margin022's availability failures **clear**; the **structural** ones persist
  (SC-EDGE-01 clause; SR-010 16/85 in-ODD, halved from 30/85 but unchanged in kind → T4). **Two findings that
  outrank the verdict table:** (i) **C-06 is load-bearing** — the 300 s endurance ledger is `{C-06: 58124}` with
  zero C-01/02/03/05, yet cage-off the same policy goes `off_road` 17/25 (|ey| 145 vs 36 mm); "cage latent
  in-ODD" is about the **safety rules**, not the cage, and the coupling to `delta_max_steering_per_cycle` is a
  **physical-transfer risk** (T2 — and it drove the v2 checkpoint choice below). Co-adaptation is *inferred*;
  the ablation was not run. (ii) **C-04 never fires** (0/1890): 0.22 < `V_MAX_CURVE` 0.25, so the ODD-3 speed
  ceiling stays untested from above. Analysis: `campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md`. A 29.07
  concurrency incident quarantined 222 runs (operator error, not a code defect; re-run under a flock'd driver).
- **TBD status (D-69, 31.07.2026): no `TBD` remains in the sim column.** SR-009 → **Satisfied**, scored
  out-of-band on the D-64 metrology. SR-010 → **`Not satisfied`**, the one reported negative: CL-B, non-vetoing
  (D-30), twice-measured, concentrated on **C-01 ∧ C-02** co-activation, carried as future work T4.
  **Still open on purpose:** the whole `verdict_phys` column — Phase 5 **has driven on the track** (18.08,
  D-71) but **no scenario has been scored on hardware** (docs/17) — and **TBD-Q10** (`ODD-3.A_LAT_MAX`),
  unmeasurable in simulation by construction (D-33), so docs/08 stays below v1.0 by design (v0.9.1). Also open:
  the **Chapter 8 restructure** so the camera track leads instead of sitting in §8.9 — an authoring decision.
- **Posterior E5 probes — findings, not verdicts (D-67; does not reopen G4).** PPO camera N=5 nominal battery;
  SAC 1-D/2-D studies (D-60): `ent_coef=0.005` removes the entropy-collapse cliff, a 200k replay buffer holds
  the peak band. First full 2-D campaign **margin022** (SAC 75k, D-65): NOT SATISFIED literal but **0 in-ODD
  road-edge contacts** — the bare policy commits 98, the cage removes all via 433 controlled stops. That
  weak-and-*decayed* checkpoint is what motivated D-66.

### Phase 5 — physical deployment (ACTIVE; commits tag `E5:`; docs/17)

- **18.08.2026 track run (M-7 / D-71) — the first drive on the real circuit.** Chain complete:
  `csi_camera_node` → `rl_policy_node` → `cv_lane_estimator_node` → `cage_ros_node` →
  `vehicle_control_node` → `cobraflex_ros_driver`. **Headline: the D-43 estimator reads lane WIDTH
  correctly and lateral OFFSET badly; the 550k trunk camera policy does NOT transfer; the cage contained
  it.** At the default `white_sat_max = 30` it pairs 95.4 % of circuit frames and reads width **252.9 mm
  vs a ruler 250**, but `ey` measured hands-off against a tape (15 points over ±100 mm) is
  **0.68–0.83 × true − 10 mm**, robust to every filtering — so **C-01's 160 mm fires at a true
  207–241 mm**, leaving 14–48 mm to the road edge instead of 95 (width is a *difference* straddling the
  optical axis, `ey` an *absolute* off-axis position, and the unmodelled `k1 = −0.339` barrel compresses
  only the second). Two further defects in the same band where C-01/C-05 act: **repeatability** (mean
  13.2 mm, worst 29.4, against a ~2 mm tape) and **pairing collapse beyond ~±55 mm**. **M-6's `ey`
  under-read of 0.72 is CONFIRMED**; its conclusion — **undistort, do not just re-parameterise** — stands,
  and its real cost is heading **noise** (`joint_pair_quadratic`/1.6 sd 14.3°, 7.8 % past C-02's 25°, vs
  `near_secant`/1.0's 5.3° / 0.8 %). §5 yaw resolved: the plant is compressive (0.48→0.34), 0.4954
  confirmed while moving, compensated by `steering_to_yaw_rate_gain 1.615`. **Method lesson (D-71 §3):
  match the measurement to the quantity** — three single-pose conclusions were overturned by a recorded
  circuit, and a fourth by realising lane width cannot measure `ey`. Sim results and the D-69 verdict unaffected. Detail:
  [M-7](experiments/calibration/M7_track_perception.md),
  [M-6](experiments/calibration/M6_camera_hfov.md), docs/17 §2/§5/§6c/§6d.
- **Sim-to-real v2 (D-72) — training closed 23.08.2026, checkpoint chosen, nothing has driven yet.** D-72
  splits the gap into three terms, only the first a property of the track: **handedness** (complex_b is 6.5:1
  left → a constant +0.13 steering prior; now mirrored per episode, measured `mirror_rate` **0.527**),
  **photometry** (75 % of episodes in the measured hall band, 25 % at the Gazebo render) and **camera
  geometry** (mount pitch ±1.5°, height ±10 %, 10 % of episodes on the full measured lens) — so **the
  deployment is meant to run rectified**, one launch argument feeding both `rl_policy_node` and
  `cv_lane_estimator_node`. Run `ppo_gz2d_sim2real_v2_2024(_r2)`: **2,500,544 steps, completed**, resumed at
  600k after I-1 (a campaign's orphan-Gazebo reaper matched the trainer — `GZ_PARTITION` isolates topics, not
  processes; guarded now, with a test pinning the hazard). **Checkpoint of record: 1,650,000**, chosen on
  transfer + cage-independence, never reward — best deployment-arm statistics of the run (r² 0.440, bias/swing
  0.10, right-turn share 62.1 %) and **3.0 %** nominal intervention against the reward peak's **35.0 %**,
  because D-69's T2 named the C-06 `delta_max_steering_per_cycle` coupling a transfer risk. **The handedness
  term is fixed**: 0.07–1.10 bias/swing against **12.9–19.2** for the trunk as deployed on 18.08. D-43
  preflight **PASS** on 325k/1650k/2000k. **I-8 — every nominal eval of this run before 23.08 measured the
  randomisation, not the policy** (`eval_policy` disabled `domain_randomization` but not the two new blocks):
  those |ey| figures are **retracted**; fixed, with two tests. Runbook: docs/17 §7; incidents I-1…I-8 in the
  run's `raw_logs/INCIDENTS.md`.
- **The deployment gate PASSED on real imagery, and the car has been DRIVEN (26.08.2026, docs/17 §8).**
  The frames were never lost — they are on the **Jetson** at
  `experiments/physical/datasets/circuit_export/frames` (**1521 PNG, 439 MB**, temporally ordered, ey span
  505 mm, 95.3 % paired; plus `lane_00_firstpass` 1205 and `lane_A` 631), gitignored by the
  `experiments/physical/datasets/*/frames/` rule, which is why the compute host's search found nothing. The
  23.08/24.08 "frames are lost" and "they are on the Windows host" notes are both **retracted**; this is the
  mistake the three-machine note below warns about. [`run_deploy_gate.sh`](tools/run_deploy_gate.sh) probe
  stages on that recording: **PASS raw** (retention 1.29, bias/swing 0.10) and **PASS rectified** (1.21, 0.17,
  right-turn share 66.6 % vs the sim arm's 66.4 %). Note the Jetson holds only the deployed checkpoint, so the
  selector's ~100-candidate ranking still needs the compute host. **`verdict_phys` remains open**: 19.28 m
  covered is not a scored scenario.
- **The v2 policy transfers — first physical drive that works (26.08.2026, docs/17 §8).** `19.28 m` on the
  real circuit (one perimeter's worth) in `monitoring` + rectified + `near_secant`, `|ey|` median ≈ **9 mm**
  while moving, **no safety rule fired at all** during driving (only C-06, 5–7 % vs the 3.0 % that chose the
  checkpoint in sim → D-69's **T2 did not materialise**). But **not a clean lap**: six segments, **five
  operator `/cage_reset` publications**, and a lane departure in the final curve. Four things stop the car and
  **none is the policy** — (i) **C-05 has no operational story on hardware**: a 120 ms glitch the estimator
  recovered from by itself stops the car permanently, since `require_explicit_reset` assumes an episode that
  ends (**decided 27.08 as D-74: C-05 unchanged, reset path outside the cage**); (ii) **camera starvation**, upstream of (i) — 7.3 Hz against the
  trained 10 Hz, worst gap 995 ms = 171 mm open-loop, cause is CPU (load 5.49/6 cores with layer 3 *not*
  running; killing `rviz2` → 9.5 Hz) — **fixed that afternoon, see the next bullet**; (iii) **ZED pose jumps,
  now measured**: 3621.8 mm in one frame → ekf `vx` −4.03 m/s, and an earlier spike to 5.479 m/s firing
  C-04→C-03→C-05 — **also fixed that afternoon**; (iv) **C-04's dead zone**: `v_max_curve_mps` 0.25 > deployed 0.22, so C-04 **can never fire** — D-69's finding (ii) is no
  longer only a coverage gap, and that tightest curve is where it left the lane **twice**. Also settled on
  hardware: **rectification is decisive** (perception-invalid 45 % → 5.5 %, C-01 fires 102 → 0) and
  **`heading_fit_mode` decides whether it drives at all** (`joint_pair_quadratic` 1.08 m vs `near_secant`
  14.45 m) while being **invisible at rest** — D-71 §3's method lesson again.
- **THE BEST PHYSICAL RUN SO FAR — 18.05 m in ONE segment (26.08 afternoon, analysed 27.08, docs/17 §8.10).**
  Two fixes landed in `624fba1d` *without* being written up, so §8 still said "next work item" / "none
  applied": **camera capture 60 → 30 fps** (delivered 15.2 Hz @134 % of a core → **19.0 Hz @96.5 %**; 60 was
  harmful, not just wasteful — `throttle_fps` sits after `nvvidconv` so `nvargus` never saw the saving) and
  **`zed_deploy_overrides.yaml`** (`area_memory`/`reset_odom_with_loop_closure` false). The two runs are a
  **controlled A/B 13 min apart**: pose steps >50 mm **116 → 0** in 509 s, ekf `|vx|` max 4.50 → **0.213** m/s
  — §8.7's hypothesis *discriminated*, priced in unbounded slow drift. **The camera fix alone does not buy a
  lap**: `cpufix` had the best loop rate of the day (9.59 Hz) and died in 16 s on a pose jump. The lap
  (`track_v2_noloopclosure_20260826T100450Z`, monitoring + rectified + `near_secant`): **18.05 m / 101.1 s,
  one segment, 0 resets, 0 jumps, C-06 the only rule (3.4 % of moving cycles vs 3.0 % in sim)**, `|ey|` median
  18.7 / max 98.7 mm, `cycles_since_last_state` never > 0. **Ended 2.11 m short (314° of 360°) on ONE 400 ms
  `/perception_invalid` pulse**, car 27 mm from centre in the tightest curve (`kappa` 0.75) → C-05 latched.
  Whether it closed the loop **cannot be settled from odometry** (the same fix removed the loop-closure
  correction) — needs a floor mark + tape, §9.4. Bottleneck **moved**: `/state_obs` 9.84 Hz vs `/cage_status`
  8.68 Hz = 12 % of estimator cycles with no control cycle → `rl_policy_node`'s timer (CNN), not the camera.
- **Next session prepared (27.08, docs/17 §9) — target: a complete monitoring lap that explains itself.** Four
  evidence gaps closed in code, none touching the cage: `cage_logger_node platform:=physical` (commit +
  cage/checkpoint/rectify hashes + contract, written at start-up too); **`frame_capture_node`** — lane frames
  around each `/perception_invalid`//`emergency` edge from a RAM ring buffer, ~20 MB/run vs the 13.8 MB/s bag
  that crashed the Jetson on 18.08 (§8.9's twice-asked item); **`cage_reset_proxy_node`** (`observe` default,
  **outside** the cage, `cage.yaml` untouched and a test pins it); **`tools/run_physical_lap.sh`** (one run id
  for bag+CSV+frames+resets, probes the *running* Layer 2 into `layer2.json`). **None of the three new ROS
  nodes has been launched** — pure logic tested (42 new host-side tests), runtime unverified. Two hand
  measurements nothing automates: floor mark + tape, and `lanecheck --true-ey` (M-7 §3b). Both pending
  decisions are now **taken**: **D-73** (ZED loop closure off as deployment configuration — the cage reads
  velocity, so drift beats jumps; the price is that odometry can no longer say whether a lap closed) and
  **D-74** (C-05 unchanged, reset path outside the cage, `observe` by default; whether C-05 should ever gain a
  bounded recovery is **deferred** — sim cannot validate it, because the latch is nearly inert there).
- **The manuscript now carries Phase 5, and carries it as BRING-UP (27.08).** `manuscript/` had gone stale in a way that mattered: Ch. 9 asserted *"no se ha ejecutado sobre hardware"* and named the
  HFOV check as still pending **after** M-6 had run it and refuted it, and the gap table called the 550k *"la que se despliega"*. Corrected across draft_v5 (abstract, preface, 09/10/12) and chapters (07/09/10/12), plus docs/07/08/09/11/12/16 — `docs/11` §8.6 is new (the v2 run). **Two classes of physical evidence are labelled differently and must stay that way:** calibration + structural findings (M-6, M-7, D-71, the two A/B pairs, C-04's dead zone) are **results**; driving figures and the gap table's physical column are **PRELIMINAR, N=1, `monitoring`, unscored** and the campaign supersedes them. No hazard/SR/scenario/metric/verdict added or re-valued (CSVs re-run: 12/14, no diff); D-67's reclassification stayed repo-only. **Page budget not re-checked** (needs Word COM) and no figure regenerated.
- **`campaign_v2` — posterior evidence; it does NOT re-score G4.** The same 27 × 2 × seed-2024 matrix
  (1890 runs, SC-PERT-03 excluded per D-64) on the 1650k checkpoint, behind the `flock` guard;
  `experiments/sim/campaign_v2/` held **20 runs** at the 24.08 commit. Not a prerequisite for driving
  (docs/17 §7.6). SC-FRONT-07 is **no longer an OOD probe** for this policy — read it as a regression test.

### Earlier phase evidence

- **F2:** `ros_run_20260523T153003Z` — 9.91 laps, 845 s, 0 emergencies, cage v0.5.1, PD v0.8.0.
- **F3 (closed):** `ppo_train_2024_200k` (seed 2024, reward v1.2; `ep_rew_mean`→536.8, `ep_len_mean`→500,
  `explained_variance`→0.67) + eval `rl_eval_2024_200k_4k4` (SC-NOM-01, 11.2 laps, 0 emergencies, |ey| 9.9 mm
  vs PD 23 mm, 0 % cage). Multi-seed N=5 {42,123,2024,23,666}: 4/5 constraint-respecting, 1/5 cage-dependent
  (seed 123, 58.8 % cage) per §7.5.3 + Fig 7.8.
- **Authoritative status sources:** [docs/CHANGELOG.md](docs/CHANGELOG.md) and `git log --oneline`
  (`E5:` = current Phase-5 sim-to-real + physical work; `E4:` = track-'E' eval; `F4:` = F-track ground state).

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
- **Three machines, and evidence does not flow between them by git.** The Ubuntu
  compute host (`/home/admit/Samuel/thesis_repo`) runs trainings/campaigns and holds
  the ~100 uncommitted checkpoints; a **Windows host** (`B:/SE4AI/thesis_repo`) holds
  the real lane-camera imagery — `experiments/physical/datasets/*/frames/` is gitignored
  while the `labels.csv` beside it is tracked; the **Jetson** on the car runs the deploy
  chain. Before writing "the data is missing", say **which host** you searched: the
  23.08 "the 18.08 frames are lost" note is that mistake (Phase 5 bullets above).

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
| Sim-to-real v2 runbook + deployment gate (D-72) | [docs/17 §7](docs/17_physical_deployment.md) + [tools/run_deploy_gate.sh](tools/run_deploy_gate.sh) |
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
- **Commit prefix matches phase.** `E5:` for current work (Phase 5 —
  sim-to-real + physical deployment), never bare messages.
  Conventional-Commit body style (`feat:`, `fix:`, `chore:`, `refactor:`).
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
