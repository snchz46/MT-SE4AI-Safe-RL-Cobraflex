# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Keep lean (<250 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-08-31.

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
  13.2 mm, worst 29.4, against a ~2 mm tape) and **pairing collapse beyond ~±55 mm**. **All three of
  those offset defects were measured UNRECTIFIED and are SUPERSEDED for the deployed path (31.08, see
  below) — do not tune C-01/C-05 from them.** M-6's 0.72 read as CONFIRMED here; its *conclusion* —
  **undistort, do not just re-parameterise** — is what 31.08 vindicated, and that stands,
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
  C-04→C-03→C-05 — **also fixed that afternoon**; (iv) **C-04's dead zone**: `v_max_curve_mps` 0.25 > deployed 0.22, so C-04 **cannot fire on commanded motion** (the 01.09 audit later found it firing on ZED **velocity artefacts** — 58/40 cycles at a reported 0.25–1.30 m/s — so the literal "never" is false) — D-69's finding (ii) is no
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
- **Session instrumentation prepared 27.08 (docs/17 §9) — EXECUTED 31.08; the bullet below is its
  outcome.** Four evidence gaps closed in code, none touching the cage: `cage_logger_node
  platform:=physical` (commit + cage/checkpoint/rectify hashes + contract, written at start-up too);
  **`frame_capture_node`** — lane frames around each `/perception_invalid`//`emergency` edge from a RAM
  ring buffer, instead of the 13.8 MB/s bag that crashed the Jetson on 18.08 (§8.9's twice-asked item);
  **`cage_reset_proxy_node`** (`observe` default, **outside** the cage, `cage.yaml` untouched and a test
  pins it); **`tools/run_physical_lap.sh`** (one run id for bag+CSV+frames+resets, probes the *running*
  Layer 2 into `layer2.json`). **All three nodes were launched for the first time on 31.08 and two needed
  fixes on the spot** (`cage_logger_node` died in its constructor; `cage_reset_proxy_node` deadlocked) —
  the 27.08 note that none had been launched, and its **"~20 MB/run" estimate for `frame_capture_node`,
  are both superseded**: the measured cost is 301 KB/PNG and the day wrote 1002 MB. Of the two hand
  measurements nothing automates, `lanecheck --true-ey` (M-7 §3b) **was done** — it is the 31.08 offset
  sweep — and **floor mark + tape is still outstanding**. Both pending decisions were **taken**: **D-73**
  (ZED loop closure off as deployment configuration — the cage reads velocity, so drift beats jumps; the
  price is that odometry can no longer say whether a lap closed) and **D-74** (C-05 unchanged, reset path
  outside the cage, `observe` by default; whether C-05 should ever gain a bounded recovery is **deferred**
  — sim cannot validate it, because the latch is nearly inert there).
- **The manuscript now carries Phase 5, and carries it as BRING-UP (27.08).** `manuscript/` had gone stale in a way that mattered: Ch. 9 asserted *"no se ha ejecutado sobre hardware"* and named the
  HFOV check as still pending **after** M-6 had run it and refuted it, and the gap table called the 550k *"la que se despliega"*. Corrected across draft_v5 (abstract, preface, 09/10/12) and chapters (07/09/10/12), plus docs/07/08/09/11/12/16 — `docs/11` §8.6 is new (the v2 run). **Two classes of physical evidence are labelled differently and must stay that way:** calibration + structural findings (M-6, M-7, D-71, the two A/B pairs, C-04's dead zone) are **results**; driving figures and the gap table's physical column are **PRELIMINAR, N=1, `monitoring`, unscored** and the campaign supersedes them. No hazard/SR/scenario/metric/verdict added or re-valued (CSVs re-run: 12/14, no diff); D-67's reclassification stayed repo-only. **Page budget not re-checked** (needs Word COM) and no figure regenerated.
- **31.08.2026 track session (docs/17 §10) — the goal was NOT met, and the failure is now located
  between two components rather than in one.** Second driving session, first launch of the §9
  instrumentation. Best **14.56 m** (lap02, 4 resets) against 26.08's 18.05 m; four laps, one sweep.
  **(i) The M-7 §4 `ey` under-read DOES NOT SURVIVE RECTIFICATION** — nine-point tape sweep, hands-off,
  on the ground, rectified: scale **1.058** left / **0.991** right, intercept gone, so **C-01 fires at a
  true 151/158 mm with ~100 mm of margin**, not 207–241 mm with 14–48. M-7 §4 now carries a superseded
  banner; it characterised the *raw* path and its prescription (*undistort*) is what this vindicates.
  **(ii) A different defect in the same band:** right of centre the estimator swings **43.3 mm on a
  STATIONARY car** (sd 6.2–8.4 vs 0.5–0.9 mirrored, reproducible) with `/perception_invalid` **never
  firing** — confidently wrong (H-12/D-43); it predicted lap01's stop before it happened. **(iii) Eight
  single-component hypotheses, all refuted by measurement.** The surviving diagnosis: M-7 saw 0.8 % of
  frames past C-02 with a car *pushed by hand* near the centre; *driving itself*, the same configuration
  gives **6.8–11.6 %** — **the estimator's reliable envelope and the policy's driving envelope do not
  overlap well enough**, neither component individually defective. **(iv)** C-02 failures are **sustained**
  (99 % in episodes ≥ 2, one of 45 cycles), C-04 still cannot fire *on commanded motion* (0.25 > 0.22; the 01.09 audit found it firing 58/40 cycles on ZED **velocity artefacts**, so the literal "can never fire" is false) while |ey| grows
  monotonically with curvature to 63 mm, and **`monitoring` does not mean the cage cannot stop the car**
  (`vehicle_control_node` zeroes `/cmd_vel` on latched `/emergency` in both modes, by design). What
  unblocks a lap is a **full-circuit recording with true position**, not another single-component fix —
  event frames are failure *neighbourhoods* and their statistics do not generalise. Posterior evidence:
  re-scores nothing, `verdict_phys` still open. Four follow-ups closed on the compute host the same day
  (CHANGELOG `[31.08.2026 · later]`): 962 MB of event PNGs untracked (`.gitignore` covered
  `datasets/*/frames/` but not `runs/*/frames/`); `frame_capture` repriced 4000 → 600 frames (~1.2 GB →
  ~185 MB at a measured 301 KB/PNG) with saturation now reported — **all four driving runs saturated the
  8-event cap**, so those frames are *truncated* as well as biased; **`preflight_deploy.py lanecheck`
  given a span check** because `sd_ey ≤ 10 mm` returned **PASS on the 43.3 mm swing** (the new gate also
  fails the 5.3 mm reading docs/17 §8.2 records as a PASS — probable false negative); and
  `rl_policy_node` re-seeding its k=4 stack on `/cage_reset`. **None of those nodes has been launched
  since — logic only.** **(v) Analysed further on the compute host, and it changes the reading:
  `kappa_ahead` OVER-READS BY ~3×** — on a closed circuit `∮κ·ds = 2π` per lap, and the logged `|κ|`
  integrates to **3.04×** (lap02) and **2.92×** (lap04) the turning the 19.28 m circuit can contain,
  with the over-read's tail growing with offset (8.4 % → 53.9 % of cycles above `ODD-3.KAPPA_MAX`).
  So the estimator misreads **offset, heading AND curvature** off-centre — one failure in three
  channels — and **any physical analysis binned on `κ` is binned on a corrupted signal**, including
  docs/17 §8.8's "tightest curve" and this session's "|ey| grows with curvature". That settles both
  open decisions: **D-75** (C-04 un-armable — 0 of 2484 moving cycles reach the 0.25 floor, max
  0.228 m/s; `cage.yaml` untouched, re-arming blocked on the capture session) and **D-76** (widen the
  estimator before narrowing the policy; the policy does not consume the estimator, so the stops are
  produced by the *measurement* in a region the policy legitimately visits).
- **31.08.2026 true-position capture (D-78 executed → D-79, docs/17 §12, `CAPTURE_NOTE_20260831.md`)
  — D-78's acceptance criterion FAILS at ~2×, and the failure is a property of PLACE, not of motion.**
  Camera only (19.38 Hz, 45.5 % of a core), no policy/cage/ZED/launch, rectified; arc length from four
  tape-measured floor stations, offset held by a **chassis pointer against the painted line** (no chalk —
  one transfer error fewer). Four laps + four parked probes, ~11 500 frames, ~1.4 MB (`--no-frames`).
  **(i)** `∫|κ|ds/(laps·2π)` = **1.97 / 2.01 / 2.25 / 2.37** against a band of 0.75–1.35 fixed in
  advance (1.78–2.22 on right-pair frames only) — the first `κ` measurement owing nothing to odometry,
  policy or cage; D-75's ~3× becomes **~2×** and **C-04 stays un-armable**. Offset dependence
  confirmed: 0 → −65 mm takes paired frames 68.2 → 46.6 %. **(ii)** The **operator's shadow** was worth
  a third of it (pushed alongside vs from outside the lane: paired 55.4 → 69.1 %, |ey| error 54.6 →
  31.9 mm) → protocol is now *push from outside the lane*, and 18.08's `circuit_export` 95.3 % is no
  longer clean. **(iii) THE CORE FINDING:** each lap's 5th segment is the **start of the straight** —
  where the 31.08 sweep and every `lanecheck` were taken — and it is excellent (96.7 % paired, **7.2 mm**
  error at −65) while moving segments run 37.9–60.2 %. **Parked inside the bad stretches** at true 0:
  `seg23_b` **0.0 % paired** (273/273 frames see one line), `seg23_a` 17.3 % / 711 mm span, `seg34_a`
  99.4 % paired but **+43.7 mm** wrong, `seg34_b` 100 % paired and **−39.7 mm wrong with sd 3.1 mm**.
  So the location every earlier single-pose conclusion came from is the estimator's **best point** —
  their content stands, their generalisation to the circuit is **retracted**. **(iv)** Mechanism is
  **candidate generation, not pair selection**: at the failing spots the candidates are stripe *edges*
  (two lines 50 mm apart = one stripe), adjacent markings, or one stripe, and the surviving pair carries
  a plausible 279–301 mm width with its midpoint displaced 40–50 mm. **D-76's order stands, its target
  moves to line extraction**; a temporal continuity prior over the selected pair is **rejected** — the
  wrong pair is stable to 3.1 mm. **(v)** No dispersion gate can catch a bias (`seg34_b` passes
  `sd_ey ≤ 10 mm`, fails the new span gate by 1.3 mm) → `lanecheck --true-ey` at **several** locations.
  Per-segment map **does not reproduce** (only 2→3 poor and the start straight good repeat across three
  laps; 3→4 swings 75.4/98.6/70.7 %). Posterior evidence: nothing re-scored, `verdict_phys` open, the
  `+60`/`±100` laps and an inspection of the four spots still owed.
- **31.08.2026 evening driving session (D-80, docs/17 §13) — three ways the cage stops the car, all
  of them the measurement. THE BARE-POLICY ARM IS WITHDRAWN (01.09, author's call).** Six Layer-3
  launches produced data (ten were started); **three caged runs stand** and are the content: all
  `monitoring` + rectified + `near_secant` on the v2 1650k checkpoint, Layer 2 without lidar (loop
  **9.2–9.4 Hz**; the venv is **torch 2.13.0+cpu**, which explains §8.10's bottleneck). **Three
  blockers, none of them the policy:** (i) D-74's **1 s healthy hold is not satisfiable in motion** —
  9 resets against **623 withholds**, 48 % of them the hold failing to complete; the STPA-argued
  threshold had never been exercised while driving; (ii) **removing C-01 from
  `reset_proxy_blocking_rules` does not escape the lap04 deadlock** — the documented escape burned
  **30/30 resets in a minute**, each re-latching, car stable at `ey` = −296 mm → tested and
  **rejected**, default stays (note it also carried `healthy_seconds:=0.3`, so it is **not** a
  controlled pair with run 1); (iii) at a 0.3 s hold **C-02 fires on noise** — over its 1066 active
  cycles the car sits at a mean `ey` = **−20 mm**, well inside the lane, with sd(`epsi`) **19.1°**
  against M-6's **5.3°** for the same config at the start of the straight → the heading channel
  degrades off that spot like offset and curvature, a **fourth** confirmation of D-79 and the first
  in heading while driving. **WITHDRAWN with the bare arm** (`lap_bare_20260831T150050Z`, 641 s, the
  operator repositioned the car by hand throughout): the 99 %-latched/97 %-driving inversion, the
  ≈109 m, the single latch at t+6.4 s, the **yaw plateau at 0.10 rad/s** with `R_min` = 2.2 m, the
  frozen-estimate signature, and D-76's **positive control** — D-76 is again an argument from
  architecture supported by D-79. `control_emergency_topic` stands as a launch argument.
  **What replaces the yaw claim:** M-7 §5 (18.08) measured achieved/commanded falling
  **0.482 → 0.436 → 0.341**, so the plant is **compressive**; where that compression ends is
  **unmeasured**, and `tools/measure_yaw_authority.py` (bench, on blocks) is how to settle it.
- **01.09.2026 — the evidence is CLOSED and the project is in WRITE-UP. Two artefacts: an audit of
  D-80, and the consolidated gap ledger (docs/17 §14).** No further debugging is planned; submission
  is ~15.09.2026. **The audit** re-derived every §13 number from the committed CSVs before the
  manuscript was allowed to cite them. For the three caged runs the core replicates exactly. (§13.4 also
  reproduced to the digit — and its run was withdrawn hours later, so that reproduction establishes
  only that the arithmetic was right about a contaminated input.) Corrected in place: the withhold population is **623, not 453** (the published
  197/121/83/51 is a *prefix* — the hold is 48 % of withholds, so the finding strengthens);
  `lap_mon_escape` **also carried `healthy_seconds:=0.3`**, so it is not a controlled pair with run 1;
  run 3's window is the mild end of 1066 C-02 cycles (sd `epsi` **19.1°**); the session was **ten**
  launches, not six. **New findings (as they stand after the 01.09 withdrawal):** (i) **C-04 does
  fire — 58 and 40 cycles in the two surviving caged runs, 100 % of them at 0.25–1.30 m/s**,
  impossible under power, and in `lap_mon_escape` they **enter the reset-withhold path** — a velocity
  artefact blocking recovery from the rule it raised (D-75's decision stands, its literal "can never
  fire" does not); (ii) `frame_capture_node` **saturated its 600-frame budget in all six runs** — the
  repricing fixed disk cost, not sampling bias; (iv) **two launches ran concurrently**
  (`…T140749Z`/`…T141134Z`, same window, 36 % of inter-arrivals < 20 ms), third instance after I-1 and
  29.07, both CSVs unanalysable. **The ledger** (docs/17 §14) puts all **13 measured gap terms** in
  one table ordered by cost, and §14.1 scores the a-priori list of §5 against them: it got the terms
  simulation can model (appearance, timing, gains) and **missed every term that stopped the vehicle**
  — handedness, an inherited intrinsics error, place-dependent estimator accuracy, the missing
  operational story for a correct latch, a velocity sensor feeding the cage. Four of six are
  perception; none is the policy. §5 is kept unedited and points at §14.
- **The manuscript now carries all of it, and one falsified claim is retracted (01.09).** M-7 §4's
  under-read (`0.68–0.83× − 10 mm` → C-01 at a true 207–241 mm) was asserted in the **abstract**, in
  **H13 of the conclusions** and in **both chapter 9s**; it characterises the *unrectified* path and
  is superseded by the 31.08 rectified sweep (scale 1.058/0.991, no intercept → C-01 at a true
  151/158 mm, ~100 mm margin). Retracted in all four places with the finding kept — the raw figure is
  preserved as the evidence that motivated rectifying. Added: draft_v5 ch.9 §§9.3.6–9.3.8 (place not
  motion; the bare arm; the yaw ceiling + Tabla 9.2), the `R_min` row in the gap table, the a-priori
  vs measured result in §9.5, **H15** in the conclusions (*the ODD can be declared without the
  platform being able to reach it*), T2 widened to five conditions, and the stale *"ausencia total de
  evidencia física"* in ch.11 fixed. `chapters/ch09` mirrored, including that D-70's "0.4954× linear
  deficit" is superseded by the saturation. DOCX builds clean (33 captions, 16 figures);
  `check_traceability.py` PASS.
- **`campaign_v2` — posterior evidence; it does NOT re-score G4.** The same 27 × 2 × seed-2024 matrix
  (1890 runs, SC-PERT-03 excluded per D-64) on the 1650k checkpoint, behind the `flock` guard;
  `experiments/sim/campaign_v2/` held **20 runs** at the 24.08 commit. Not a prerequisite for driving
  (docs/17 §7.6). SC-FRONT-07 is **no longer an OOD probe** for this policy — read it as a regression test.

### Next steps (as of 01.09.2026 — WRITE-UP ONLY; submission ~15.09.2026)

**Physical work is CLOSED and the evidence base is final.** No further track or bench measurement
will be taken. A session was prepared on 01.09 and **never executed**; its runbook has been deleted
by the author, and the tests it described survive where they belong — as the manuscript's named
future-work items with their discriminators (ch.12 T2/T3, docs/17 §13.4). Do not propose another
run, do not reopen a decision — **cite D-71…D-80 and docs/17 §14, don't re-litigate**. Everything
below is authoring work.

1. **Page budget — the one blocking unknown.** `tools/build_thesis_docx.py` was retyped by the
   author to **Arial 11 pt / 1.15 / 1.0" left margin** (now committed, `accfe642`), far denser than
   the guidelines' 12 pt TNR / 1.5 against which the 80–100 page budget was set; ch.9 grew and then
   shrank again on 01.09, and chapters 9–12 were rewritten again on 02.09. `tools/thesis_page_budget.py`
   needs **Word COM (pywin32), NOT installed on this host** — run it on a host with Word before
   trimming or adding anything. The last measured 96 pages is from the 31.07 build under the old
   settings and must not be quoted (`manuscript/README.md` now says so).
2. **Front matter — submission date SET to 15.09.2026** on 02.09.2026 (author's instruction), in
   both `front/00_cover.md` and `front/05_declaration.md`. If it moves, change **both**: the DOCX
   build copies them through verbatim and nothing catches a mismatch. **Still blank:** the cover's
   matriculation number (`[por completar]`) and the preface's personal acknowledgements.
3. **The Chapter 8 restructure** — camera track leads instead of sitting in §8.9 — remains open and
   is an authoring decision. Largest optional item; skip it if the budget is tight.
4. **The physical evidence is smaller than it was on 31.08, deliberately, and the withdrawals are
   recorded.** Three landed on 01.09: M-7 §4's `ey` under-read (superseded by the rectified sweep,
   docs/17 §10.2), the D-67 reclassification (repo-only, unchanged), and — the large one —
   **`lap_bare_20260831T150050Z` in full**, because the operator repositioned the car by hand
   throughout it (docs/17 §13.2/§13.4/§13.6; D-80 partially void). Anything citing the 99 %/97 %
   inversion, the ≈109 m, the 0.10 rad/s yaw plateau or `R_min` = 2.2 m is retracted and must not
   return. The actuation deficit now rests on **M-7 §5** alone: compressive, 0.482 → 0.436 → 0.341,
   with its endpoint unmeasured. `tools/measure_yaw_authority.py` (**tracked**, selftest 8/8, ROS path
   never run) is kept as the discriminator that was written but not used. **H15 of the conclusions
   went with it** — the earlier note in this file recording H15 as *added* is superseded by the
   withdrawal; draft_v5 ch.12 carries R1–R14 and no R15/H15.
5. **Standing:** `verdict_phys` is open by design; every physical figure is labelled PRELIMINAR /
   N=1 / `monitoring` / unscored; the cage has **never modified an action on hardware**. Nothing in
   Phase 5 re-scores a gate. This file is ~600 lines against its own <250 budget; the split into
   `CLAUDE_*.md` is overdue and is itself an authoring decision.
6. **Repo-wide consistency pass done 02.09.2026** (CHANGELOG `[02.09.2026]`). Docs and manuscript
   were swept for retracted claims, stale status and duplicates. Fixed: the M-7 §4 under-read still
   asserted as current in `docs/12` §5, `docs/17` §2/§9.4 and the calibration README; C-04's literal
   *"can never fire"* in `docs/04`, `docs/07`, `docs/17` §8.8 and both chapter 9s and 10s; D-80's
   Finding 1 never amended by its own 01.09 audit (453→**623** withholds, sd 17.2→**19.1°**,
   `lap_mon_escape` not a controlled pair, six→**ten** launches); the 0.4954 yaw gain presented as
   linear in `docs/08`/`docs/14` where M-7 §5 measured it compressive; "verdict of record" still
   pointing at GE4-V2 in `experiments/`, `tools/` and `scenarios_complex_b/` READMEs; `chapters/ch11`
   six weeks behind `draft_v5/11`; and `AGENTS.md`, a stale duplicate of this file, collapsed to a
   pointer. Also settled that day: the submission date (item 2) and `git worktree prune`, which
   removed two dead registrations pointing at Windows `B:`/`E:` paths. **Left in place on purpose:**
   the **1.1 GB stale worktree directory** at `.claude/worktrees/reverent-feistel-49fec5` — a
   01.06.2026 snapshot of the whole repo, hidden from `git status` by `.git/info/exclude`. Its
   content is all in git history; deleting it is a one-line `rm -rf` whenever the space is wanted.

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
| `docs/` | Living engineering documents (00–17 + CHANGELOG, DECISIONS) |
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
| Physical track sessions (what drove, what stopped it, what was refuted) | [docs/17 §8](docs/17_physical_deployment.md) (26.08) + [§10](docs/17_physical_deployment.md) (31.08) |
| True-position capture runbook + scorer (D-78) | [docs/17 §11](docs/17_physical_deployment.md) + [tools/score_lane_capture.py](tools/score_lane_capture.py) |
| Lane-estimator calibration — **read the §4 superseded banner first** | [M-7](experiments/calibration/M7_track_perception.md) + [31.08 sweep](experiments/physical/runs/lanesweep_20260831T094110Z/SWEEP_NOTE.md) |
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
