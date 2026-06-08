# Change Log

This document records every change made to the living documents under `docs/` and to `cage/cage.yaml`.

Each entry has the following structure:

```text
## [DD.MM.2026] — Short summary

**Document(s) affected:** ...  
**Phase:** F0 / F1 / ...  
**Gate context:** before/after Gate G?  
**Author:** Samuel Sanchez  

### Change

What was changed, where.

### Rationale

Why the change was made; which evidence motivated it.

### Impact

Which other artefacts are affected; what re-runs are required.

### Verification

Result of `tools/check_traceability.py` after the change.
```

---

## [08.06.2026] — F4: Frontier cage-efficacy scenario family (SC-FRONT-01…06 + M-S5) registered; Gazebo executor live

**Document(s) affected:**
`docs/05_scenario_library.md` (Frontier category + study section + 6 SC-FRONT entries; count 11→17),
`docs/06_metrics_catalogue.md` (new M-S5), `scenarios/_schema.yaml`,
`tools/check_scenario_yaml.py`, `tools/check_traceability.py`, `docs/DECISIONS.md` (D-35 + index),
`docs/07_traceability_matrix.md` (D-35 carve-out note),
`manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_08_experimental_evaluation.md`,
`CLAUDE.md`.
New code/scenarios this entry documents: `scenarios/frontier/sc_front_01…06.yaml`,
`tools/run_campaign.py` (`execute_run` + frontier-plot hook), `tools/frontier_contrast.py`,
`tools/plot_frontier.py`, `tools/README.md`,
`src/cobraflex_rl/cobraflex_rl/scenario_metrics.py`, `…/eval_policy.py`.
**Phase:** F4.
**Gate context:** before G4.
**Author:** Samuel.

### Change

- **New Frontier (FRONT) scenario family — SC-FRONT-01…06.** Out-of-ODD /
  cage-efficacy scenarios: an out-of-ODD pair (01–03: lateral 0.16 m / heading 32° /
  compound) where the start is already past the boundary, and an in-ODD-drift pair
  (04–06: 0.10 m + 8°/22°/14° outward) where the cage responds **graded** rather than
  with an immediate stop. All on the oval (`start_s=0.0`, 0.2 m/s, 15 s), 25 runs/mode.
  Registered in `docs/05` (new category, study section, per-scenario entries; total
  scenario count **11 → 17**). They reference existing SR-001/002/005/007/008 — no new SR.
- **New safety metric M-S5 — Road-edge departure** (`road_edge_contact = max|ey| ≥
  road_half_m`, road half-width ≈ 0.26 m, beyond the 0.1225 m lane edge) — the
  cage-efficacy harm proxy, mirroring the M-S3/`emergency` per-run-event ↔ aggregate-rate
  pattern. `max_excursion_m` documented as the realised value of M-S1. Added to `docs/06`.
- **Gazebo executor live.** `run_campaign.execute_run` now drives
  `ros2 launch cobraflex_rl eval_scenario_batch.launch.py` per matrix cell (per-run
  `GZ_PARTITION` isolation, orphan-`gz` reaping, retries, resume) — **no longer a stub.**
- **Scenario-evaluation framework.** `scenario_metrics.py` (`max_excursion_m`,
  `road_edge_contact`, `time_to_recovery_heading`) wired into
  `eval_policy._evaluate_scenario`; `tools/frontier_contrast.py` aggregates the paired
  enforcement-vs-monitoring benefit (`M-S5(monitoring) − M-S5(enforcement)`).
- **Validators/schema taught the FRONT family.** `FRONT` added to the id/category
  allowlists in `check_scenario_yaml.py` and to `RX_SC`/`RX_SC_DEF` in
  `check_traceability.py`; `road_edge_contact`/`max_excursion_m` whitelisted as per-run
  bare-name fields; `_schema.yaml` documents the category and tokens.
- **Decision D-35 recorded** in `docs/DECISIONS.md` (+ index row, + D-34 index row backfilled):
  the frontier scenario family and its **non-verdict-bearing** cage-efficacy semantics —
  the explicit D-30 carve-out that a frontier result never vetoes the global verdict. A
  matching note added to `docs/07` explains the deliberate SC-FRONT absence from the verdict matrix.
- **Cage-efficacy figures wired into the campaign.** `tools/plot_frontier.py` renders the paired
  enforcement-vs-monitoring figures (`fig_frontier_excursion`, `fig_frontier_cage_benefit`)
  **aggregating over the N reps per cell** (mean ± std + road-edge-contact rate) — the same script
  serves the rep00 pilot and the full 25-rep campaign. `run_campaign.py` auto-invokes it after a
  frontier campaign (best-effort; `--no-frontier-plots` to skip; falls back to printing the manual
  command when matplotlib is absent, e.g. the headless ROS host).

### Rationale

The frontier family answers *what the cage is worth*: on an out-of-ODD start the policy is
not designed to recover, so the monitoring arm (no-cage counterfactual) is expected to
reach the road edge while enforcement is not — the contrast is the H-04 cage-value
evidence. The scenarios, the M-S5 harm proxy and a pilot campaign already existed as
**committed run artifacts** (`experiments/sim/campaign_frontier`, today's `F4:` commits) but
were **unregistered** — invisible to the traceability spine and rejected by the scenario
validator (`id must match SC-{NOM|EDGE|PERT}-NN`). This entry closes that orphan gap.

### Impact

- Frontier evidence is **not** folded into the global G4 verdict (D-30; recorded as decision
  **D-35**); it is reported as a per-arm enforcement-vs-monitoring contrast. The 6 × 25 × 2 =
  **300** frontier runs are separate from the ~1100-run verdict-bearing (NOM/EDGE/PERT) campaign.
- No hazard / SR / cage-rule IDs added or changed; one metric added (M-S5).
- Still pending (Ubuntu+Jazzy host): the full verdict-bearing campaign → per-SR sim
  verdicts in `docs/07` (all still `TBD`); scaling the frontier pilot (rep00, seeds 123 &
  2024) to the recommended 25 reps incl. SC-FRONT-01/02/03; the QED-metric decision
  (D-17/D-21/D-22).

### Verification

`python tools/check_scenario_yaml.py --strict` → PASSED, 0 error(s), 0 warning(s).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s)
(Defined scenarios now 17 incl. SC-FRONT-01…06; Defined metrics incl. M-S5).

---

## [07.06.2026] — F3: Ch.7 main seed switched 42 → 2024 (best of the 5); figs + text repointed

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.5, §7.2.7, §7.2.8,
§7.4, §7.5.1–§7.5.3), `manuscript/figures/fig_7_1..fig_7_6` (regenerated),
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md`, `CLAUDE.md`.
**Phase:** F3 (recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Chapter 7 main run changed from seed 42 to `ppo_train_2024_200k` (seed 2024).**
  Of the five trained seeds, 2024 has the **highest reward (536.8)** and the **best
  PPO health (`explained_variance` 0.67)** while tying the best safety (0% cage, 0
  emergencies) with near-best tracking (9.9 mm). Seed 23 tracks marginally tighter
  (6.7 mm) but its value-function fit is weak (`explained_variance` 0.22), so 2024 is
  the more defensible all-around main.
- **Figs 7.1–7.6 regenerated** from the seed-2024 train + eval runs (`--train-run
  ppo_train_2024_200k --rl-run rl_eval_2024_200k_4k4 --pd-run ros_run_20260523T153003Z`).
  Fig 7.8 (multi-seed) unchanged.
- **§7.4/§7.5.1–§7.5.2 text repointed** to seed 2024: convergence (`ep_rew` 20.9→536.8,
  saturation ~75k), `explained_variance` (0.67, max 0.81), intervention co-adaptation
  (~90%→3.4%), entropy (1.42→−1.52), eval (11.2 laps, mean |ey| 9.9 mm, max 23 mm,
  **0% cage / 0 interventions**, raw |Δ| 0.030, sign-flips 1.1%).
- **Stale "Nota de cobertura" (§7.2.8) corrected** — it claimed the definitive cycle
  used the legacy 4-column schema; all five seeds carry the extended instrumentation.
- **`docs/09` (ED-10), `docs/10`, `CLAUDE.md` synced** to the seed-2024 smoothness /
  cage numbers (0.030 / 1.1% / 0% vs the old 0.031 / 3.3% / 0.023%).

### Impact

- The §7.5.3 multi-seed table / Fig 7.8 still report all five seeds (incl. seed 42);
  only the *main* detailed run changed. The F4 campaign should use the seed-2024
  checkpoint as the RL controller.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --train-run … --rl-run … --pd-run …` → figs 7.1–7.6.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [07.06.2026] — F3: seed-666 cycle added; multi-seed complete (N=5, 4/5 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 5 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Fifth and final training cycle `ppo_train_666_200k`** (seed 666, 200k, reward
  v1.2) + eval `rl_eval_666_200k_4k4`. Constraint-respecting: ep_rew 529.3, training
  intervention → 11 %, eval cage 1.55 % (**C-06 only**, smoothing), mean |ey| 8.0 mm,
  max 26 mm, 0 emergencies, 11.1 laps.
- **Multi-seed campaign complete at N = 5: 4/5 constraint-respecting (42, 2024, 23,
  666), 1/5 cage-dependent (123).** §7.5.3 table (5 columns), analysis, caption and
  Fig. 7.8 updated to five seeds; §7.2.7 records N = 5 reached. The 4-vs-1 bimodality
  (seed 123 the lone outlier) fixes the observed `w_ds` / M-P4 distribution at 80 % CR.

### Impact

- Multi-seed reporting closed: five seeds reported individually in Ch.7 (§7.5.3,
  Fig. 7.8). Seed 42 remains the §7.5.1–§7.5.2 main; median±band deliberately omitted
  (bimodal — would mask the two basins). `w_ds` sensitivity analysis stays for Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>,<23>,<666>` → fig_7_8 (5 lines).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-23 cycle added; multi-seed now 4 seeds (3/4 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 4 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Fourth training cycle `ppo_train_23_200k`** (seed 23, 200k, reward v1.2) + eval
  `rl_eval_23_200k_4k4`. Constraint-respecting, with the **tightest tracking** of the
  four: ep_rew 535, training intervention → 5 %, eval cage 0 %, mean |ey| **6.7 mm**,
  max 22 mm, 0 emergencies, 11.1 laps.
- **Multi-seed result is now 3/4 constraint-respecting (42, 2024, 23), 1/4
  cage-dependent (123).** §7.5.3 table (4 columns + basin row), analysis and Fig. 7.8
  updated; §7.2.7 notes four seeds trained. The 3-vs-1 split (seed 123 the lone
  outlier) sharpens the `w_ds` / M-P4 sensitivity point.

### Impact

- Four seeds reported individually in Ch.7 (§7.5.3, Fig. 7.8). Seed 23 is the best
  tracker (6.7 mm), but seed 42 remains the §7.5.1–§7.5.2 main. N≥5 (a fifth seed) +
  median±band stay for Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>,<23>` → fig_7_8 (4 lines).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-2024 cycle added; multi-seed comparison now 3 seeds (2/3 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 3 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Third training cycle `ppo_train_2024_200k`** (seed 2024, 200k, reward v1.2) +
  eval `rl_eval_2024_200k_4k4`. It converges **constraint-respecting**, like seed 42
  (marginally cleaner): ep_rew 537, training intervention → 3 %, eval cage **0 %**,
  mean |ey| **9.9 mm**, max 23 mm, 0 emergencies, 11.2 laps.
- **Multi-seed result is now 2/3 constraint-respecting (42, 2024), 1/3
  cage-dependent (123).** §7.5.3 table + analysis + Fig. 7.8 updated to three seeds;
  §7.2.7 notes seed 23 (4th) in progress. The 2-vs-1 split sharpens the `w_ds`
  (M-P4) sensitivity point: the smoothness weight yields constraint-respecting in the
  majority of seeds but not reliably.

### Impact

- Three seeds reported individually in Ch.7 (§7.5.3, Fig. 7.8). Seed 2024 is
  marginally the best policy (537, 0 % cage, 9.9 mm); seed 42 remains the
  §7.5.1–§7.5.2 main. N≥5 consolidation (seed 23 + one more) stays in Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>` → fig_7_8_multiseed.png
(3 lines). `python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-123 cycle + multi-seed comparison (constraint-respecting vs cage-dependent); Fig. 7.8 + §7.5.3

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, new §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (new),
`tools/plot_f3_figures.py` (`--seed-runs` / `fig_multiseed`).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3 — adds the multi-seed evidence deferred at §7.2.7.
**Author:** Samuel.

### Change

- **Second training cycle `ppo_train_123_200k`** (seed 123, 200k, reward v1.2, same
  config) + eval `rl_eval_123_200k_4k4`. It converges to a **cage-dependent** basin,
  in contrast to seed 42's **constraint-respecting** one:
  - seed 42: ep_rew 530, training intervention → 5 %, eval cage 0.02 %, mean |ey| 11.6 mm.
  - seed 123: ep_rew 443, training intervention → 74 %, eval cage **58.8 %** (C-06 58 %,
    C-01 6 %, C-03 3 %), mean |ey| **90.7 mm**, max |ey| **145 mm**. Both: 0 emergencies, ~11 laps.
- **New §7.5.3** reports the comparison: both policies are safe (the cage guarantees
  it), but seed 123's worse policy needs the cage *actively* — C-01/C-03 prevent lane
  departure in real time — the strongest cage-utility evidence so far, which the
  nominal-only seed-42 result could not provide. Framed as the `w_ds` (smoothness
  weight) sensitivity flagged by M-P4.
- **Fig. 7.8** (multi-seed reward + intervention overlay) + `tools/plot_f3_figures.py
  --seed-runs` to generate it. §7.2.7 updated (seed 123 done, 2024 pending;
  bimodality → report seeds individually, not only a median).

### Rationale

The nominal seed-42 evaluation showed the cage latent (0.02 %), so its protective
value had to be argued indirectly. Seed 123 — same code, different basin — drives
poorly enough (90 mm mean offset, peaks crossing the lane half-width) that the cage
intervenes 58.8 % of steps, with C-01/C-03 actively preventing lane departure. The
two seeds together show the cage's value *depends on the policy* and that it performs
at both ends (latent vs active protector).

### Impact

- Multi-seed evidence now in Ch.7 (§7.5.3, Fig. 7.8). N≥5 consolidation (seed 2024 and
  beyond) stays in Ch.8; bimodality → seeds reported individually.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs experiments/sim/training/ppo_train_42_200k,experiments/sim/training/ppo_train_123_200k`
→ fig_7_8_multiseed.png. Chapter figure refs monotonic 7.1→7.8.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [04.06.2026] — F4: SR-002/005/007 nominal-family coverage added; scenario library now 11/11 D-29-feasible

**Document(s) affected:**
`docs/03_safety_requirements.md` (SR-002/005/007 Scenarios += SC-NOM-03),
`docs/data/safety_requirements.csv` (regenerated),
`docs/05_scenario_library.md` (SC-NOM-03 References SR + nominal-coverage note),
`scenarios/nominal/sc_nom_03.yaml` (references_SR += SR-005/007; M-P4 gate).
**Phase:** F4 (entry).
**Gate context:** after G3 — closes the 3 D-29 nominal-coverage gaps the campaign
dry-run surfaced; the scenario library is now fully D-29-feasible.
**Author:** Samuel.

### Change

- **SR-002 / SR-005 / SR-007 gain nominal-family coverage via SC-NOM-03** (the
  full-circuit run, 25 nominal runs), so each of these SR-CL-A is now verified in a
  nominal *and* an adverse family (D-29). SR-002 (heading) is verified positively —
  M-P4 promoted to primary with a `M-P4 < 0.436` (θ_max = 25°) gate. SR-005
  (compound-state emergency) and SR-007 (state staleness) are verified as
  **no-false-activation** checks: their hazards do not arise in nominal, so the
  nominal evidence is `emergency == False` / M-S3 = 0 over the run (documented in
  docs/05). A pre-existing docs/03↔docs/05 inconsistency (SC-NOM-03 already
  referenced SR-002 on the scenario side but not in the SR register) is resolved.
- `safety_requirements.csv` regenerated from docs/03 via
  `tools/sync_safety_requirements.py`.

### Rationale

The dry-run showed SR-002/005/007 (all SR-CL-A) verified only in adverse families,
failing D-29's nominal+adverse requirement. SC-NOM-03 already exercises the relevant
metrics (M-P4 heading, M-S3 emergency) over an extended nominal run, so it is the
natural nominal carrier. The no-false-activation framing keeps the emergency-SR
nominal evidence honest rather than fabricating a positive demonstration of a hazard
that cannot occur in nominal.

### Impact

- `run_campaign --dry-run`: **0 GAP — 11/11 SRs D-29-feasible** (was 3 GAP). The
  scenario library is ready for the campaign (pending the Gazebo executor).
- No hazard / SR / cage-rule / metric / scenario IDs added or changed; only the
  SR↔scenario links and SC-NOM-03's metrics/gate.

### Verification

`python tools/sync_safety_requirements.py` → 11 SRs written.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).
`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 0 warnings.
`python tools/run_campaign.py --dry-run` → 0 SR not feasible (11/11).

---

## [04.06.2026] — F4: 7 scenario stubs promoted to full YAMLs; dry-run resolves D-29 run-count gaps

**Document(s) affected:**
`scenarios/{nominal,edge,perturbed}/*.yaml` (7 stubs → full: SC-NOM-02/03,
SC-EDGE-02/03/04, SC-PERT-01/02), `docs/05_scenario_library.md` (SC-EDGE-03 /
SC-NOM-03 run counts → 25), `tools/run_campaign.py` ("ALL" convention + message),
`policy/tests/test_run_campaign.py`.
**Phase:** F4 (entry).
**Gate context:** after G3 — the `run_campaign --dry-run` had flagged the 7 stubs
as blocking SR coverage; this promotes them and closes the run-count gaps.
**Author:** Samuel.

### Change

- **7 stub scenarios promoted to full, schema-valid YAMLs** (SC-NOM-02 curved
  nominal, SC-NOM-03 full circuit, SC-EDGE-02 lateral, SC-EDGE-03 speed pulse,
  SC-EDGE-04 compound, SC-PERT-01 sensor noise, SC-PERT-02 latency), translated
  from docs/05 onto the oval track mapping, with a small per-run randomisation so
  the runs are **independent** (D-29) and pass criteria on catalogued M-* metrics.
  `check_scenario_yaml.py` now reports 0 warnings (was 7 stubs).
- **Run-count reconciliation for D-29.** SC-EDGE-03 (verifies SR-004) and SC-NOM-03
  (verifies SR-008) bumped 20 → 25 runs/mode, the SR-CL-A minimum (D-29); docs/05
  updated to match.
- **`run_campaign.py`:** handle the docs/05 "ALL" scenario convention (SR-006, the
  always-active rate limiter, is verified by every scenario), and fix the stale
  "blocked by stubs" message.

### Rationale

The `--dry-run` planner showed 8/11 SRs not D-29-feasible because the verifying
scenarios were stubs. Promoting them + the two run-count bumps + the SR-006 fix
brings it to **8/11 feasible**. The remaining 3 gaps (SR-002, SR-005, SR-007) are
**structural**: each is verified only in adverse (EDGE/PERT) scenarios, while D-29
requires an SR-CL-A to be covered in a nominal family too. Closing those needs a
scenario↔SR mapping decision (add a nominal reference, or argue the SR is
inherently adverse) — deferred to the supervisor.

### Impact

- D-29 feasibility: 3/11 → **8/11** SRs feasible (dry-run). Remaining GAPs: SR-002,
  SR-005, SR-007 (no nominal-family coverage — design decision).
- No hazard / SR / cage-rule / `cage.yaml` / metric / scenario IDs added or changed;
  only the 7 YAML bodies and two run counts changed. The 11 scenario IDs stay
  consistent with docs/05 and the traceability matrix.

### Verification

`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 0 warnings.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).
`python -m pytest policy/tests/test_run_campaign.py` → 11 passed.
`python tools/run_campaign.py --dry-run` → 11/11 executable, 8/11 SRs D-29-feasible.

---

## [04.06.2026] — F4: scenario track-mapping reconciliation + campaign-runner core (plan + D-29/D-30 aggregation)

**Document(s) affected:**
`docs/05_scenario_library.md` (new "Track mapping" section),
`scenarios/{nominal,edge,perturbed}/*.yaml` (11 files: explicit `track` block +
`commanded_speed_mps`), `tools/run_campaign.py` (new),
`policy/tests/test_run_campaign.py` (new).
**Phase:** F4 (entry).
**Gate context:** after G3 — prepares the L2′ campaign for launch: pins the
scenarios to the trained world and provides the orchestration/verdict spine.
**Author:** Samuel.

### Change

- **Scenario↔world reconciliation (Option A — run on the oval).** The scenarios
  were specified (Phase 2) in abstract geometry without a world, while the policy
  and PD baseline were trained/validated only on the oval. Every scenario YAML now
  carries an explicit `track` block (`world: lane_following_oval.world`,
  `centerline: oval_right_lane_centerline.yaml`, `start_s_m` = 0.0 straight start /
  1.5 curve entry for SC-NOM-02) and `commanded_speed_mps: 0.2` (the env fixed
  speed, superseding the per-scenario 0.3–0.4 prose). Documented authoritatively in
  a new "Track mapping" section of `docs/05`. `straight_road.world` is reserved for
  the Phase-5 physical subset. No retraining needed — the policy already drives the
  oval's κ=0 straights.
- **Campaign-runner core `tools/run_campaign.py`.** Pure, ROS-free orchestration +
  aggregation: scenario/SR loading, run-matrix generation
  (scenario × mode × controller × seed × rep), per-run verdict from the
  pass-criterion strings (sandboxed eval), and aggregation per **D-29** (≥25
  runs/family for SR-CL-A, 10 for SR-CL-B, nominal+adverse coverage) and **D-30**
  (any SR-CL-A failure vetoes the global verdict). A `--dry-run` planner validates
  the run matrix and the D-29 feasibility against the current library before any
  run is launched. The Gazebo executor (`execute_run`: mode/start_s/perturbation
  via `eval_policy`) is a documented stub for the Ubuntu+Jazzy host.

### Rationale

Launching F4 needs two things this change provides: (a) the scenarios must point at
the world the policy actually runs on (they did not), and (b) an orchestration spine
that turns the campaign into per-SR and global verdicts under the agreed counting
(D-29) and veto (D-30) rules. The `--dry-run` surfaces, before spending the run
budget, that 8 of 11 SRs are not yet feasible because the scenarios that verify them
are still stubs — making "promote the 7 stub scenarios" the concrete next F4 task.

### Impact

- `--dry-run` on the current library: 11 scenarios (4 executable, 7 stub),
  1760 matrix runs, 3/11 SRs D-29-feasible (SR-009/010/011), 8 GAP (stub-blocked).
- Known refinement: the SR-006 "ALL"-scenario convention (docs/05) is not yet
  special-cased in the runner (shows as a gap).
- No hazard / SR / cage-rule / `cage.yaml` / metric IDs added or changed; the 11
  scenario IDs are unchanged (only their YAML bodies gained the `track` block).

### Verification

`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 7 warnings (the
pre-existing stubs). `python -m pytest policy/tests/test_run_campaign.py` →
11 passed. `python -m py_compile tools/run_campaign.py` → OK.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [04.06.2026] — F3: extended training instrumentation + re-instrumented seed-42 cycle; Ch.7 figures 7.1–7.7

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.6 hyperparameter table,
§7.2.7 multi-seed note, §7.2.8 CSV schema, §7.4 + Figures 7.2–7.4, §7.5 + §7.5.2),
`manuscript/figures/fig_7_1..fig_7_7*.png` (regenerated + renumbered to reading order),
`src/cobraflex_rl/cobraflex_rl/training_metrics.py` (new), `.../callbacks.py`,
`.../train_ppo.py`, `tools/plot_f3_figures.py`,
`policy/tests/test_training_metrics.py` (new),
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md` (§5), `CLAUDE.md`.
**Phase:** F3 (Training Spec / Ch.7 refinement; recorded during F4).
**Gate context:** after G3 — closes the co-adaptation-evidence gap left open at G3 (the
training-time cage-intervention curve was never logged, so the cage's contribution had to
be argued indirectly).
**Author:** Samuel.

### Change

- **Extended PPO learning-curve logger.** `LearningCurveCallback` now records, per rollout,
  the PPO-health scalars (`value_loss`, `entropy = −entropy_loss`, `approx_kl`,
  `clip_fraction`, `std`) and the safety-cage activity (`intervention_rate`,
  `emergency_rate`, per-rule `int_rate_C-01..C-06`) — a superset of the legacy 4-column
  schema (§7.2.8). New `ActionSampleCallback` → `action_samples.csv` (subsampled raw
  steering). Aggregation lives in the pure, dependency-free `training_metrics.py`
  (unit-tested in `policy/tests/test_training_metrics.py`, 10 tests).
- **Re-instrumented definitive cycle.** `ppo_train_42_200k` (run_id
  `ppo_train_20260603T203630Z`, seed 42, 200k, reward v1.2) + eval `rl_eval_42_200k_4k4`
  (run_id `rl_eval_20260604T083959Z`) replace the prior seed-42/200k run (retained as
  `*_old`): same config, now with the full logging. §7.4/§7.5 rewritten around it.
- **Figures 7.1–7.7, renumbered to reading order.** New training-dynamics figures —
  7.2 (cage intervention + per-rule co-adaptation), 7.3 (value-loss/entropy), 7.4 (action
  distribution) — and the eval figures renumbered (7.5 trajectory, 7.6 tracking error,
  7.7 Gazebo capture). `tools/plot_f3_figures.py` emits all six auto-generated figures.
- **§7.2.6 hyperparameter table** completed to the full effective SB3 2.8.0 config
  (`n_epochs`, `gae_lambda`, `clip_range`, `ent_coef`, `vf_coef`, `max_grad_norm`,
  `normalize_advantage`) + `MlpPolicy` architecture note.
- **Number sync** to the new run in `docs/09` (ED-10), `docs/10` (§5) and `CLAUDE.md`.

### Rationale

At G3 the nominal evaluation showed ~0% cage interventions, so co-adaptation could only be
argued indirectly. The direct signal — the cage intervention rate *during training* — was
not logged. The extended logger captures it: the new cycle shows the intervention rate
falling monotonically from ~89% to ~4.7% (Figure 7.2), entropy decaying 1.42 → −1.56
(Figure 7.3) and the raw action distribution moving from bang-bang to smooth (Figure 7.4) —
the constraint-respecting co-adaptation the methodology predicts.

### Impact

- **Result (re-instrumented run):** `ep_rew_mean` → 530.2, `ep_len_mean` → 500,
  `explained_variance` → 0.55; eval 11.03 laps, 0 emergencies, mean |ey| 11.6 mm (×2.0 vs
  PD), cage 0.023% (one C-06 step). Slightly less precise than the prior seed-42 run
  (6.5 mm) — run-to-run variance, not budget: 200k is saturated (plateau from ~83k).
- Additional seeds (123, 2024, …) under the **same** config are in progress; the
  median±band overlay and the §7.2.7 cross-seed consolidation are deferred to that set
  (Ch.8).
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python -m pytest policy/tests/test_training_metrics.py` → **10 passed**.
`python -m py_compile` on `training_metrics.py`, `callbacks.py`, `train_ppo.py`,
`plot_f3_figures.py` → OK. `tools/plot_f3_figures.py` regenerates `fig_7_1..fig_7_6` with
the new names. `python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F4: SR criticality single-sourced into the SR register CSV

**Document(s) affected:**
`docs/03_safety_requirements.md` (machine-readable SR table → new Criticality column),
`tools/sync_safety_requirements.py` (`column_mapping` + `fieldnames`),
`docs/data/safety_requirements.csv` (regenerated; new `criticality` column),
`src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py`,
`policy/tests/test_verdict_aggregation.py`.
**Phase:** F4.
**Gate context:** after G3 — closes the follow-up flagged in the 03.06 "verdict spine" entry
(drop the injected criticality map once the SR sync pipeline carries the column).
**Author:** Samuel.

### Change

Restored single-source-of-truth for the SR criticality class (SR-CL-A/B/C), which until now
lived only in the manuscript SRS table (ch.4 §4.7 "Criticidad") and was duplicated in code:

- Added a **Criticality** column to the machine-readable SR table in
  `docs/03_safety_requirements.md`, with values mirrored from ch.4: SR-001..SR-005, SR-007,
  SR-008 = SR-CL-A; SR-006, SR-009, SR-010, SR-011 = SR-CL-B (7× A, 4× B).
- Extended `tools/sync_safety_requirements.py` (`column_mapping` + `fieldnames`) to extract and
  emit a `criticality` column, and regenerated `docs/data/safety_requirements.csv`.
- `verdict_aggregation.load_sr_registry` now reads criticality from the CSV; the hard-coded
  `SR_CRITICALITY` map (previously cited to ch.4 / D-28) and its guard test
  `test_sr_criticality_matches_csv` are deleted. The criticality-count assertion
  (7× SR-CL-A, 4× SR-CL-B) is retained, now sourced from the CSV-built registry.

### Rationale

The injected map duplicated a fact that belongs in the generated register; the duplication was
only kept honest by a guard test. Carrying `criticality` through the Markdown→CSV sync removes
both the duplication and the guard, so the D-29 run-count gate and D-30 SR-CL-A veto read the
same source the manuscript does.

### Impact

- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed; SR semantics
  unchanged — only the criticality attribute is relocated to its single source.
- One CSV column added (`criticality`). `load_sr_registry` is its only consumer and is updated;
  an empty/absent column falls back to SR-CL-C, preserving the previous default for unknown SRs.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
`python -m pytest -q` → **233 passed** (guard test removed, count assertion retained and now
CSV-sourced; net test count unchanged).

---

## [03.06.2026] — F4: verdict spine (campaign metrics, criterion eval, scenario loader, SR verdict aggregation)

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/campaign_metrics.py`, `…/criterion_eval.py`,
`…/scenario_loader.py`, `…/verdict_aggregation.py` (all new),
`policy/tests/test_campaign_metrics.py`, `…/test_criterion_eval.py`,
`…/test_scenario_loader.py`, `…/test_verdict_aggregation.py` (all new).
**Phase:** F4.
**Gate context:** after G3 — the pure-Python core of the scenario-campaign verdict pipeline
(deliverable 2; the Gazebo-coupled driver + env stressor hooks are Phase C, deferred).
**Author:** Samuel.

### Change

The ROS-free, unit-tested core that turns per-run results into per-SR and global verdicts.
Mirrors the pure style of `eval_metrics.py` so it runs under `pytest` on any host (the Gazebo
campaign driver, Phase C, will feed it):

- **`campaign_metrics.py`** — full per-run metric catalogue (docs/06): M-P1/P3/P4/P5/P6/P7,
  M-S1/S2/S3/S4, M-I1/I2/I3/I4/I5, M-C1/C2, computed from the `cage_status.csv` per-step record
  schema. Reports an `availability` map for metrics needing data absent from that schema (M-S4
  needs a ttlc series; M-P3 and M-I4's C-04 arm need per-step curvature; M-C* unmeasured in sim;
  M-I5 is steering-only). Plus `aggregate_metric` (median/mean/std/p5/p95).
- **`criterion_eval.py`** — safe, `eval()`-free, **three-valued** evaluator for the
  `pass_criterion_*` strings (conjunction of comparisons; labelled multi-arm for SC-PERT-03). An
  unavailable metric yields *indeterminate* (None), never a false fail.
- **`scenario_loader.py`** — scenario YAML → typed `RunSpec`; skips stubs; exposes the
  nominal/adverse `family` the D-29 gate needs.
- **`verdict_aggregation.py`** — per-scenario (`fraction_pass`) → per-SR → global verdict,
  implementing **D-29** (SR-CL-A needs ≥25 runs in a nominal AND an adverse family; SR-CL-B ≥10
  in ≥1 family; SR-CL-C informal) and **D-30** (any SR-CL-A failure vetoes the global verdict).
  SR criticality is injected from `SR_CRITICALITY` (cited to the ch.4 SRS table / D-28) with a
  guard test asserting it matches `docs/data/safety_requirements.csv`.

### Rationale

The verdict logic is the reusable, correctness-critical heart of the F4 campaign and is pure
data-in/data-out, so it is built and **unit-tested on the Windows host** (the Gazebo campaign
cannot run here). Per-run verdicts are produced by `criterion_eval` on each run's metrics and
fed into `verdict_aggregation` as data, keeping the D-29/D-30 logic testable with synthetic
inputs.

### Impact

- **Finding (surfaced by a test):** SR-002, SR-005, SR-007 (all SR-CL-A) are mapped only to
  *adverse* scenario families in the SRS, so the D-29 "nominal AND adverse" gate **cannot be met
  as currently mapped** — each needs a nominal verifying scenario, or a documented D-29 exception
  for inherently-adverse requirements. Flagged for review; not changed here.
- Phase C (deferred, to run on the Ubuntu host): extend `GazeboLaneEnv` with stressor hooks
  (deterministic ICs, perception noise, action latency, throttle pulse) + a `run_campaign.py`
  driver writing `experiments/sim/<SC>_<mode>/run_NNN/` and calling this spine.
- Follow-ups flagged: harden `close_odd_tbds.py` (prose-mention substitution footgun); add a
  `criticality` column to the SR sync pipeline so `verdict_aggregation` can drop the injected map.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python -m pytest -q` → **233 passed** (58 new across the four modules; no regression).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F4: ODD-2 adverse stressor profiles closed (TBD-Q4–Q7, Q12)

**Document(s) affected:**
`src/cobraflex_rl/config/adverse_profiles.yaml` (new),
`docs/08_odd_specification.md` (§5.5, §7.2, §11, cover block → v0.5),
`docs/DECISIONS.md` (D-33 status table + status-update note),
`experiments/odd_inspection/odd_tbds.yaml` (Q4–Q7, Q12 values).
**Phase:** F4.
**Gate context:** after G3 — F4-entry prerequisite (the adverse scenario families need
parameterised stressor profiles before the campaign can run).
**Author:** Samuel.

### Change

- **New machine-readable source of truth** `src/cobraflex_rl/config/adverse_profiles.yaml`:
  per-profile stressor parameters for the ODD-2 named profiles (+ the ODD-4 cross-product),
  to be consumed by the F4 campaign runner for stressor injection.
- **ODD-Spec TBD closures (D-33):**
  - **Q4** `odd2_nominal_adverse` — σ_lateral=0.03 m (SC-PERT-01 mid level) + faded markings
    / non-uniform light via `lane_following_oval_worn.world`.
  - **Q5** `odd2_adverse_with_latency` — +100 ms latency (SC-PERT-02 high, over the 50 ms
    nominal) + 20 ms jitter + 0.02 steering actuation noise.
  - **Q6** `odd2_adverse_with_obstacle` — 1 static 0.10 m box, ~0.05 m lane intrusion at
    mid-straight. **Specified only; execution deferred** — the F3 policy observes a 6-dim
    vector with no obstacle channel (§5.1 specifies an 8-dim ODD-2 obs); the campaign skips
    `execution: deferred` profiles until obstacle perception is wired.
  - **Q7** `odd2_adverse_full` — union of Q4+Q5+Q6 (inherits Q6's execution deferral).
  - **Q12** ODD-4 — no additional stressors; the ODD-4 profiles are the pure cross-product
    of ODD-3 geometry × ODD-2 stressors.
  - ODD-Spec §5.5 table now mirrors `adverse_profiles.yaml` with per-column values; §7.2
    ODD-4 table and §11 resolution rows filled; cover block → **v0.5**, **11 of 12** TBDs
    resolved (only Q10 remains, deferred to M-4 physical calibration).

### Rationale

The ODD-2 adverse profiles parameterise the perturbed/adverse scenario families the F4
campaign verifies. Magnitudes are grounded in the existing scenarios (σ from SC-PERT-01,
latency from SC-PERT-02) and the 50 ms `*.LATENCY_NOMINAL`, not invented.

Closed **by hand** rather than via `tools/close_odd_tbds.py --apply`: the dry-run showed the
tool's blanket `TBD-QN` substitution would (a) repeat one value across the three σ/latency/
jitter columns of the §5.5 table, and (b) **corrupt prose mentions of already-closed TBDs** —
the §0.1 change-log rows and the §9 source column — because it cannot tell a placeholder cell
from a documentation mention. `odd_tbds.yaml` is kept in sync as provenance; D-33 records the
decision and flags hardening the tool as a separate follow-up.

### Impact

- Closes the F4-entry ODD prerequisite. Remaining F4 work unchanged (campaign runner +
  per-SR verdicts **D-29/D-30**, QED decision, sim verdicts in `docs/07`).
- Obstacle scenarios are spec'd but not executed by the campaign (no obstacle perception);
  flagged in `adverse_profiles.yaml`, §5.5, and the D-33 table.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
`python tools/check_scenario_yaml.py` → **PASSED, 0 errors, 7 warning(s)** (deferred stubs).
`adverse_profiles.yaml` and `odd_tbds.yaml` parse as valid YAML.

---

## [03.06.2026] — F4 entry: Gate G3 passed, F3 closed; scenario library completed (SC-EDGE-05, SC-PERT-03)

**Document(s) affected:**
`scenarios/edge/sc_edge_05.yaml` (new), `scenarios/perturbed/sc_pert_03.yaml` (new),
`CLAUDE.md` (phase snapshot → F4).
**Phase:** F4 (entry).
**Gate context:** **Gate G3 passed 2026-06-03**, closing F3 (PPO training). This is the
F3→F4 transition the prior 03.06 entry left pending ("the closing commit / F4 entry").
**Author:** Samuel.

### Change

- **Gate G3 / F3 close-out.** F3 (PPO training) is closed. Closing evidence: the
  definitive reward-v1.2 cycle `ppo_train_42_200k` (seed 42/200k, saturated) and its
  re-evaluation `rl_eval_42_200k_4k4` (SC-NOM-01, 11.2 laps, 0 emergencies, 0% cage
  intervention); the Training Spec (Ch.7 §7.2–§7.5) is complete; the mechanical gate
  `tools/check_traceability.py` passes with 0 warnings. Phase enters **F4 — Sim eval**
  (scenario-based validation campaign; closes at G4).
- **Scenario library completed to 11/11 documented.** The two documented scenarios
  that had no YAML file are now full, schema-valid executable YAMLs translated from
  `docs/05_scenario_library.md`:
  - `SC-EDGE-05` (cage-rule co-activation matrix, SR-010): parameterised
    `(d, θ, v, dκ/dt)` grid with the five documented pair/triple co-activation anchors;
    primary metrics M-S2/M-I2/M-I3; ≥100 runs per mode (5 reps × ≥20 grid points);
    per-run verdict = no joint-envelope assertion failure, M-S2 = 0, no inter-cycle
    oscillation; ≥95% of grid points pass.
  - `SC-PERT-03` (reward-injection stall test, **negative** test for SR-009): two-arm
    (released vs ~50k-step stall-fine-tuned) design; primary metrics M-P6/M-P2; 40 runs
    per mode (20+20), 80 total; verdict = stall variant M-P6 > 0.50 while released
    M-P6 = 0 and M-P2 = 1; ≥90% of runs pass.

### Rationale

"Initiating F4" requires (a) formally closing F3 at G3 and (b) bringing the scenario
library — the L2′ artefact F4 executes — to full documented coverage. SC-EDGE-05 and
SC-PERT-03 were the only two documented scenarios with no YAML at all (the other seven
non-F2 scenarios remain explicit stubs, full YAMLs deferred); they are written first
because they carry the most design content and verify the two SRs (SR-010 joint-envelope,
SR-009 stall) least served by off-the-shelf tooling.

### Impact

- **F4 scope now open.** Remaining F4 entry work (not in this change): the ODD-2 adverse
  scenario profiles (TBD-Q4–Q7, Q12 — `docs/DECISIONS.md`), the multi-run campaign runner
  + per-SR verdict aggregation (run-count convention D-29, veto rule D-30), the QED-metric
  decision (D-17/D-21/D-22), and filling the sim verdicts in `docs/07_traceability_matrix.md`.
  The seven sibling scenario stubs (NOM-02/03, EDGE-02/03/04, PERT-01/02) are promoted to
  full YAMLs as the campaign reaches them.
- No hazard / SR / cage-rule / `cage.yaml` / metric IDs added or changed. No scenario IDs
  added — SC-EDGE-05 and SC-PERT-03 were already in the traceability matrix; only their
  YAML *implementations* are new.

### Verification

`python tools/check_scenario_yaml.py` → **PASSED, 0 errors, 7 warning(s)** (the two
"documented but has no YAML file yet" warnings for SC-EDGE-05/SC-PERT-03 are cleared; the
7 remaining are the deferred sibling stubs).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F3 definitive cycle: seed-42/200k under reward v1.2 (native smoothness, 0 cage interventions)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md`
(§7.2.4–§7.2.7, §7.4, §7.5, §7.5.2),
`manuscript/figures/auto/fig_7_1_convergence.png`,
`manuscript/figures/auto/fig_7_2_trajectory.png`,
`manuscript/figures/auto/fig_7_2b_tracking_error.png`,
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md`,
`CLAUDE.md` (status snapshot).
**Phase:** F3.
**Gate context:** after G2 — closes the reward-v1.2 backlog item from the two prior
02.06 entries; supersedes the 250k/seed-123 (reward v1.0) cycle.
**Author:** Samuel.

### Change

- **New definitive training cycle `ppo_train_42_200k`** (run_id
  `ppo_train_20260602T145922Z`, seed 42, 200 000 timesteps, **reward v1.2**,
  commit 666249c, ~6.2 h real, fps≈9, 196 iterations of 1 024). It **supersedes**
  both prior cycles — the preliminary 50k (not saturated) and the 250k/seed-123
  reward-v1.0 cycle (saturated but C-06-dependent). §7.4/§7.5 rewritten around it.
- **Convergence (§7.4.1):** `ep_rew_mean` 24.8 → plateau **535.2** (max 535.2);
  `ep_len_mean` 48.0 → **500.0**. `ep_len_mean` reaches 500 by ~71k timesteps,
  `ep_rew_mean` hits 90% of final (~482) by ~84k, then climbs gently to 535.2 over
  the plateau (episode length pinned at 500 throughout). `explained_variance`
  averages 0.56 on the plateau, final **0.63** (max 0.82) — above the 0.5 threshold.
- **Re-evaluation `rl_eval_42_200k_4k4`** (run_id `rl_eval_20260603T075419Z`,
  SC-NOM-01, 1 deterministic episode of 4 400 steps ≈ **11.17** continuous laps,
  checkpoint hash 150e496d…). §7.5.1/§7.5.2 refreshed.
- **Hyperparameters §7.2.6:** `total_timesteps` 250 000 → **200 000**; §7.2.7 seed
  note now seed 42 under reward v1.2.
- **Figures regenerated** from the new cycle + eval:
  `python tools/plot_f3_figures.py --train-run experiments/sim/training/ppo_train_42_200k --rl-run experiments/sim/runs/rl_eval_42_200k_4k4 --pd-run experiments/sim/runs/ros_run_20260523T153003Z`
  (explicit pins **required**: the re-checked-in seed runs share one mtime, so
  `plot_f3_figures.py`'s mtime auto-pick is ambiguous).
- **ED-10 / `docs/10`:** the reward-v1.2 effect, previously "pending re-train", is
  marked **confirmed**.

### Rationale

The two 02.06 entries left an open loop: reward v1.2 (raw-Δsteer smoothness term,
`w_ds` 0.10→0.20) was wired and unit-tested, but its effect on native RL smoothness
"required a new training cycle". This cycle is that re-train, and it confirms the
hypothesis: the policy now steers smoothly on its own (sign-flips **1.1%** vs ~46%,
**0%** ±1 saturation, mean |Δraw| **0.027** — below C-06's 0.15 limit), so the cage
never has to rate-limit it in nominal.

### Impact

- **Result:** PPO matches the PD on safety (**0 C-05 emergencies over 11.2 laps**)
  and beats it on tracking (mean |ey| 23 mm → **6.5 mm**, ×3.6, max 18 mm; mean
  |epsi| 4.3° → **1.9°**, ×2.3). Cage intervention 0.047% (PD) → **0%** (PPO):
  `raw ≡ safe` at every one of the 4 400 steps. The 89.0%/all-C-06 of the prior
  reward-v1.0 cycle is **superseded** — the cage is now a latent safeguard in
  nominal, its protective value reserved for the Ch.8 edge/perturbed scenarios.
- The other seed runs checked in alongside (`*_old` training dirs: 2024/200k,
  123/250k, 42/50k — reward-v1.0 or under-trained) are retained for the record;
  **only seed-42/200k is the definitive reward-v1.2 run.** Multi-seed (N≥5) stays
  deferred to Ch.8 (§7.2.7).
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
Chapter §7.4/§7.5 quantitative claims reproduce from
`experiments/sim/training/ppo_train_42_200k/learning_curve.csv` and
`experiments/sim/runs/rl_eval_42_200k_4k4/cage_status.csv`.

---

## [02.06.2026] — F3 reward v1.2: smoothness term on the raw policy Δsteer (penalise bang-bang)

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/rewards.py`,
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_rewards.py`,
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.3, §7.2.5, §7.5.2),
`docs/10_reward_function.md`, `docs/09_environment_design.md` (ED-10).
**Phase:** F3.
**Gate context:** after G2 — non-blocking refinement from the §7.5.2 backlog (not required for G3).
**Author:** Samuel.

### Change

- The smoothness reward term `w_ds·|Δsteer|` now measures the **raw** policy
  steering delta (pre-cage) instead of the post-cage applied delta. `GazeboLaneEnv`
  tracks `prev_policy_steer` separately from `prev_steer` (the latter still feeds
  the `prev_steer` observation as the applied steering).
- `w_ds` raised **0.10 → 0.20** in `train_ppo.yaml` (`[provisional, M-P4]`).
- Tests: `test_steer_delta_*` updated to the 0.20 weight; new
  `test_raw_bang_bang_costs_more_than_smooth_ramp` pins that a raw sign-flip
  (|Δ|=2.0) costs far more than a within-C-06 ramp (|Δ|=0.15). 11/11 pass.

### Rationale

The F3 definitive evaluation (§7.5.2) showed the policy emitting bang-bang raw
steering (sign-flip 46% of steps, ±1 saturation 27%, mean |Δraw|≈0.54) that the
rate-limiter **C-06** absorbed into a smooth post-cage signal. Because the old
term was computed post-cage (per the reward-on-safe-action convention, D-34), the
smoothed result was near-identical whether or not the policy oscillated, so the
penalty never bit — the policy drove C-06 to its limit ~89% of steps for free.
Measuring the raw delta (a deliberate, scoped exception to D-34, this term only)
makes the policy pay for its own jerk; it does **not** penalise the cage's action.

### Impact

- The change is wired and unit-tested, but its effect on native RL smoothness
  **requires a new training cycle** on the Ubuntu+Jazzy host — not verifiable on
  the current dev host. The evaluated policy in §7.5 corresponds to the previous
  reward (post-cage, `w_ds=0.10`) and is unchanged.
- Weights remain `[provisional, M-P4]`; the Ch.8 sensitivity analysis confirms
  them before freeze.

### Verification

`policy/tests/test_rewards.py`: 11/11 pass. `tools/check_traceability.py`: PASS
(no ID changes; reward weights are not traceability nodes).

---

## [02.06.2026] — F3 §7.4/§7.5 update: definitive 250k PPO cycle (saturated) + re-evaluation

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md`
(§7.1, §7.2.4, §7.2.6, §7.2.7, §7.4, §7.5, internal appendix),
`manuscript/figures/fig_7_1_convergence.png` (+ `figures/auto/` copy),
`manuscript/figures/fig_7_2_trajectory.png` (+ `figures/auto/` copy),
`manuscript/figures/fig_7_2b_tracking_error.png` (+ `figures/auto/` copy),
`policy/checkpoints/checkpoint_registry.csv` (250k row), `CLAUDE.md` (status snapshot).
**Phase:** F3.
**Gate context:** after G2 — supersedes the preliminary 50k cycle that did not saturate.
**Author:** Samuel.

### Change

- **Definitive training cycle `ppo_train_20260601T184341Z`** (seed 123,
  250 000 timesteps, ~7.8 h real, fps≈9, 245 iterations of 1 024). §7.4 rewritten
  around it; it **supersedes** the preliminary 50k cycle (`ppo_train_20260601T150552Z`,
  seed 42), which was competent but **not saturated**.
- **Convergence (§7.4.1):** `ep_rew_mean` 32.4 → plateau **534.7** (max 535.6);
  `ep_len_mean` 48.4 → **500.0** (the full truncation horizon, ≈1.14 laps/episode).
  `ep_len_mean` reaches 500 by ~62k timesteps and `ep_rew_mean` hits 99% of final
  by ~72k — a stable plateau thereafter (with a minor reward dip ~120k–150k to ~490
  that does not affect episode length). The 50k-cycle "no plateau" limitation is
  **resolved**.
- **Stability (§7.4.2):** `explained_variance` sustained >0.4 from ~150k, mean **0.78**
  over the last 20 iterations (range 0.63–0.88) — the convergence criterion now holds.
- **Re-evaluation `rl_eval_20260602T070417Z`** (policy `cobraflex_ppo_lane` from the
  250k cycle, SC-NOM-01, 1 deterministic episode of 4 400 steps ≈ 11.0 continuous
  laps). §7.5.1/§7.5.2 refreshed.
- **Hyperparameters §7.2.6:** `total_timesteps` 50 000 → **250 000**; §7.2.7 seed
  note (definitive seed 123, preliminary seed 42); §7.2.4 horizon note (500-step
  horizon now saturates).
- **Figures regenerated** from the 250k cycle + new eval via
  `python tools/plot_f3_figures.py --train-run … --rl-run … --pd-run …`
  (explicit `--train-run` is **required**: `plot_f3_figures.py` auto-picks the
  latest run by mtime, which is a stray 5-row aborted run `ppo_train_20260602T070504Z`;
  the previously committed `fig_7_1_convergence.png` had been generated from it and
  showed a 4k-timestep stub — now fixed). The tracked `manuscript/figures/` copies
  (the ones the chapter `<img>` references) were overwritten with the corrected
  renders.
- **`checkpoint_registry.csv`** carries the 250k row (seed 123, commit a15412c).
- **Fig 7.3 / videos:** the Gazebo capture and `manuscript/media/*.mp4` remain from
  the preliminary eval (`rl_eval_20260601T172201Z`); caption clarified as a
  representative, visually-equivalent capture (no new screenshot on this host).

### Rationale

The 50k cycle (§7.4.2, prior entry) ended without saturation — `ep_rew_mean` was
still rising at budget exhaustion — flagged as a documented limitation [M-P6/M-P7].
A 250k cycle was run to confirm convergence; it saturates with wide margin, so the
Training Spec now reports a converged policy.

### Impact

- **Result:** PPO still matches the PD on safety (**0 C-05 emergencies over 11.0
  laps**) and beats it on tracking (mean |ey| 23 mm → **8.7 mm**, max 25 mm; mean
  |epsi| 4.4° → **2.1°**). Cage intervention 0.047% (PD) → **89.0%** (PPO) —
  **entirely C-06**: raw steering is bang-bang (sign-flips 46.4% of steps, ±1
  saturation 27.2%, mean |raw| 0.53, mean |Δraw| 0.54), smoothed by the rate
  limiter (mean |safe| 0.28, max 0.80; ~89% of steps exactly at the 0.15/cycle
  limit). No C-01..C-05 fire.
- Lap count 11.04 (440 s) vs PD 9.91 (845 s): durations differ, so the raw count
  is not 1:1; the comparable claim is both ran fault-free.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
Chapter §7.4/§7.5 quantitative claims reproduce from
`experiments/sim/training/ppo_train_20260601T184341Z/learning_curve.csv` and
`experiments/sim/runs/rl_eval_20260602T070417Z/cage_status.csv`.

---

## [01.06.2026] — F3 doc reconciliation: `max_episode_steps` 400→500 propagation + status sync

**Document(s) affected:**
`docs/08_odd_specification.md` (→ v0.4), `docs/09_environment_design.md` (→ v0.2),
`docs/10_reward_function.md` (version log), `docs/DECISIONS.md` (D-33 Q11 row),
`experiments/odd_inspection/odd_tbds.yaml` (TBD-Q11 source),
`manuscript/chapters/chapter_07_training_specification.md` (§7.4.3),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (default), `CLAUDE.md`.
**Phase:** F3.
**Gate context:** before the F3 closing commit / F4 entry — a consistency pass over
the §7.2.4 `max_episode_steps` 400→500 change and the F3 status snapshot.
**Author:** Samuel.

### Change

- **`max_episode_steps` 400→500 propagation.** Training Spec §7.2.4 set the episode
  horizon to 500 steps (50 s ≈ 1.14 laps; the value the first run actually used).
  Realigned every downstream reference still reading 400 / 40 s / 0.47 laps:
  `docs/09` truncation line (→ v0.2), `docs/08` §6.8 prose + master-parameter table
  + TBD-Q11 row (→ v0.4, F2-closure history preserved), `docs/DECISIONS.md` D-33
  Q11 row, and `experiments/odd_inspection/odd_tbds.yaml` (the source
  `close_odd_tbds.py` reads). The ODD `STUCK_TIMEOUT` closure is **unchanged**
  (n/a, subsumed by env truncation) — only the illustrative seconds figure moved
  40→50 s. Code default `gazebo_lane_env.py` 400→500 (behaviour-neutral:
  `train_ppo.yaml` already sets 500).
- **`docs/09` spawn perturbation** marked **implemented** (was "Pending"): it is
  enabled in `train_ppo.yaml` and described in §7.3.
- **`docs/10`** version log gains the forward-driver **v1.1** entry (progress reward;
  weights still v1.0).
- **Chapter 7 §7.4.3** "0 emergencias en 500 pasos" → "0 emergencias en las 11.5
  vueltas / 4 400 pasos", matching the §7.5 evaluation it cites.
- **`CLAUDE.md`** phase-status snapshot refreshed (TS-01 done; F3 training+eval
  evidence IDs; first 50k cycle not saturated, longer run planned); hazard range
  H-01..H-07 → H-01..H-09; docs range 00–08 → 00–10; docs/09 + docs/10 added to the
  reference table.

### Rationale

The §7.2.4 horizon change (committed in `train_ppo.yaml`, reflected in the
working-tree chapter edit) had not propagated to the ODD spec, the environment-
design doc, or the decision log, leaving "400 / 40 s / 0.47 laps" in four files.
This is a pre-commit consistency pass so the F3 closing commit is internally
coherent. No semantic decision was changed — only stale figures realigned to the
normative §7.2/§7.3.

### Impact

- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.
- No behavioural change: the first run already used 500; the code-default edit is
  inert because the config sets the key.
- Confirmed the chapter §7.5.2 quantitative claims (raw sign-flip 46.9 %, ±1
  saturation 24.0 %, mean |raw| 0.47, mean |safe| 0.28 / max 0.82, 85.9 % of steps
  at the C-06 rate limit, 0 emergencies) reproduce exactly from
  `experiments/sim/runs/rl_eval_20260601T172201Z/cage_status.csv`.

### Verification

`/usr/bin/pytest -q` → **174 passed**. `python tools/check_traceability.py` →
**All checks PASSED. 0 warning(s).**

---

## [01.06.2026] — F3 §7.5 evidence: first PPO evaluation on SC-NOM-01 (RL vs PD)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.5.1, §7.5.2),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (pose in `info`),
`src/cobraflex_rl/cobraflex_rl/eval_policy.py` (x/y/yaw columns),
`src/cobraflex_rl/launch/eval_lane.launch.py` (new).
**Phase:** F3.
**Gate context:** after G2; first §7.5 evaluation of the trained PPO policy.
**Author:** Samuel.

### Change

- **Evaluation run `rl_eval_20260601T172201Z`** (policy
  `ppo_train_20260601T150552Z`, seed 42, SC-NOM-01, 1 deterministic episode of
  4 400 steps ≈ 11.5 continuous laps). §7.5.1/§7.5.2 of the Training Spec filled
  with the measured results. (Short check run `rl_eval_20260601T170402Z`, 500
  steps, preceded it.)
- **Eval logging:** `GazeboLaneEnv` now exposes world pose `x, y, yaw` in `info`;
  `eval_policy` writes them as columns in `cage_status.csv` (enables the §7.5
  trajectory overlay, Figure 7.2). New `eval_lane.launch.py` (gazebo gui + eval)
  and `eval_policy --max-steps` to extend the horizon for the lap-count run.

### Rationale

§7.5 requires an empirical comparison of the trained policy against the PD
baseline (`ros_run_20260523T153003Z`) on the nominal scenario.

### Impact

- **Result:** PPO matches the PD on safety (**0 C-05 emergencies over 11.5 laps**)
  and **beats it on tracking** (mean |ey| 23 mm → 9.2 mm; mean |epsi| 4.4° →
  2.0°). Cage intervention rate 0.047% (PD) → 85.9% (PPO) — **entirely C-06**
  (rate limiter): the PPO's raw steering is bang-bang (sign-flips 46.9% of steps,
  saturates ±1 on 24.0%), which the cage smooths. No C-01..C-05 fire — the policy
  stays well inside the lane. This validates the cage as an active safeguard over
  a learned policy and motivates a future raw-Δsteer penalty.
- Lap count 11.53 (440 s) vs PD 9.91 (845 s): durations differ, so the raw count
  is not 1:1; the comparable claim is both ran fault-free and the PPO sustained
  >11 continuous laps without an emergency.
- No hazard / SR / cage-rule / cage.yaml changes.

### Verification

`pytest` → **174 passed**. `python tools/check_traceability.py` → **PASSED, 0 warnings**.

---

## [01.06.2026] — F3 learning fix: curvature preview in observation + progress reward

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/rewards.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_rewards.py`,
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.1, §7.2.3, §7.2.4),
`docs/09_environment_design.md` (obs, Q2, ED-7/8/9),
`docs/10_reward_function.md` (formula v1.1).
**Phase:** F3.
**Gate context:** after G2; first training run did not learn (`ep_rew_mean` flat,
`explained_variance ≈ 0`, `std` pinned at 1.0) — root-caused to MDP design, not
the cage.
**Author:** Samuel.

### Change

- **Observation: curvature preview (4 → 6 dims).** `obs` becomes
  `[ey, epsi, speed, prev_steer, kappa_near, kappa_far]`, where the two new
  components are the signed centerline curvature (rad/m, + = left) at a near and
  a far look-ahead (`observation.curvature_lookahead_{near,far}`, default 3/8
  segments). The cage already consumed `curvature_ahead` internally; the policy
  did not, so it could not anticipate the R=0.8 m bend.
- **Reward: progress instead of speed (v1.1).** The forward term changes from
  `w_fwd·speed` (cage-fixed, near-constant ≈0.2) to `w_fwd·max(progress, 0)`,
  where `progress` is the normalised centerline advance per cycle (≈1.0 at
  cruise; the env unwraps the closed-loop `s` reset). Weights unchanged (v1.0).
  `compute_reward`'s `speed` parameter renamed to `progress`.

### Rationale

With speed fixed by the cage, the old forward term did not depend on the policy,
and the reactive 4-dim observation gave the policy no way to anticipate the
curve — together these flattened the return's dependence on the actions
(`explained_variance ≈ 0`). Curvature preview gives the policy the information to
act; progress reward makes the return discriminate behaviour (survive + advance)
and keeps every on-track step net-positive, which also closes the perverse
incentive that the penalty-free C-05 termination ([01.06] bring-up entry) would
otherwise create. Empirically the policy then learned: `ep_rew_mean` 29→57,
`ep_len_mean` 46→78, `explained_variance` 0→0.29, `std` starting to fall, with
episodes completing laps and ending by truncation (18% of training).

### Impact

- Old policy checkpoints (4-dim obs) are **incompatible**; retrain fresh.
- No hazard / SR / cage-rule IDs touched; the cage and `cage/cage.yaml` are
  unchanged. Observation/reward are env-side (Training Spec §7.2), not cage.
- Spec drift closed across Training Spec §7.2.1/§7.2.3/§7.2.4, `docs/09` (ED-7/8/9),
  `docs/10` (v1.1).

### Verification

`pytest` → **174 passed** (incl. updated `test_rewards.py`).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [01.06.2026] — F3 training-loop bring-up: C-05 episode termination + spawn-settle + sim-time pacing

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/ros_interface.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`docs/DECISIONS.md` (D-34 addendum).
**Phase:** F3.
**Gate context:** after G2; first end-to-end run of the in-process cage training
loop (TS-01) on the Gazebo/Jazzy host.
**Author:** Samuel.

### Change

- **Episode termination on C-05 emergency.** `GazeboLaneEnv.step` now sets
  `terminated=True` the instant the cage latches a C-05 emergency, in addition
  to the pre-existing off-road condition `|ey| > road_width/2`. A latched
  emergency freezes the car, so the remaining steps carried no learning signal
  and burned the full `max_episode_steps` per failed rollout. `info` now carries
  `termination_reason ∈ {cage_emergency, off_road, truncated}`. Both conditions
  set `terminated` (value bootstraps from 0); they differ only in the reward. Per
  D-34, the C-05 emergency carries **no** termination penalty (the cage's action
  is not punished — the episode simply ends, so the policy only forgoes future
  reward); only a genuine off-road failure, which predates the cage in the loop,
  incurs the penalty (`done=off_road` to `compute_reward`). The corrective
  interventions C-01..C-04/C-06 likewise remain transparent dynamics.
- **Spawn-pose settle fix.** A `set_pose` teleport propagates to `/odom_truth` a
  few sim steps *after* the gz service returns, so calibrating the odom→world
  offset immediately latched the previous-crash pose — producing impossible
  multi-metre `ey` and degenerate 1-step `off_road` terminations that polluted
  the PPO rollouts. `reset()` now uses `_calibrate_spawn_settled`, which
  recalibrates against a wall-clock-settled stationary pose and self-corrects if
  a stale offset was latched.
- **Sim-time control pacing.** `RosGazeboInterface.step_ros` advances by
  *simulation* time (odom header stamps) with an odom-backlog drain and a
  wall-clock fallback, instead of blocking on wall-clock; the reset settle uses a
  dedicated wall-clock `spin_wall`. A session-only `sim_real_time_factor` knob
  (default 1 = real-time) is applied via `/world/.../set_physics`. A runtime
  unthrottle is currently avoided (gz froze on `real_time_update_rate=0`), so
  headless training still runs at real-time pending the world-RTF lever.
- Transient `debug_reset_timing` / `debug_cage` console instrumentation was used
  during bring-up and removed after validation (cage confirmed intervening:
  C-01/C-02/C-03/C-06 per step, C-05 closing failed episodes).

### Rationale

The first end-to-end run of the in-process cage training loop (D-34 / TS-01)
exposed three bring-up issues: failed rollouts wasting the full horizon, a spawn
calibration race injecting garbage transitions, and real-time-locked episode
pacing. The C-05 termination and spawn-settle changes are correctness/quality;
the pacing change is groundwork for faster-than-real-time training.

### Impact

- Training throughput: failed rollouts end on emergency (seconds, not the full
  horizon); the degenerate 1-step `off_road` episodes are gone.
- Reward semantics: a C-05 emergency ends the episode with **no** termination
  penalty (only off-road failures are penalised), keeping cage interventions
  penalty-free per D-34. Cage behaviour and `cage/cage.yaml` are unchanged.
- No hazard / SR / cage-rule IDs added or changed; no scenario or metric changes.
- Re-runs: none required for traceability; the F3 first training run subsumes
  this as its starting code state.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [29.05.2026] — F3 off-host prep: training run registration (§7.2.8) + .bak hygiene

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/run_io.py` (new),
`src/cobraflex_rl/cobraflex_rl/callbacks.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`policy/tests/test_run_io.py` (new),
`experiments/sim/training/.gitkeep` (new), `.gitignore`.
**Phase:** F3.
**Gate context:** after G2; off-host preparation so the first training run is turnkey.
**Author:** Samuel.

### Change

- **§7.2.8 training run registration**: `train_ppo` now writes
  `experiments/sim/training/<run_id>/` with `learning_curve.csv`
  (`[timestep, ep_rew_mean, ep_len_mean, explained_variance]`, via the new
  `LearningCurveCallback`) and `metadata.json` (git commit; cage/scenario/policy
  hashes; seed; hyperparameters). Periodic checkpoints go to `policy/checkpoints/`
  (SB3 `CheckpointCallback`, every `n_steps`) and a row is appended to
  `checkpoint_registry.csv` on completion — so the Gazebo/Jazzy run produces its
  §7.4 evidence automatically.
- New pure `run_io` (sha256 + git commit), shared by `train_ppo` and
  `eval_policy` (de-duplicated); `test_run_io.py` (3 tests).
- **`.gitignore`**: ignore `*.bak` so `check_traceability`'s transient
  `docs/08_..md.bak` backup never shows in `git status`.

### Verification

- `pytest cage/tests policy/tests` → 174 passed (+3 in `test_run_io.py`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- The training loop still requires the Gazebo/Jazzy host; the pure pieces
  (`run_io`, metrics) are verified here, the callback/registration syntax-checked.

---

## [29.05.2026] — F3 Week-8 wrap: seed, spawn perturbation, §7.5 eval harness, §7.2.4 reconciled

**Document(s) affected:** `src/cobraflex_rl/config/train_ppo.yaml`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/eval_metrics.py` (new),
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`policy/tests/test_eval_metrics.py` (new),
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.4).
**Phase:** F3.
**Gate context:** after G2; closing the off-host Week-8 (D36–D40) items before the first training run.
**Author:** Samuel.

### Change

- **seed = 42** (§7.2.7): added `seed` to `train_ppo.yaml` and passed it to
  `PPO(...)`. SB3 seeds python/numpy/torch + the action space and propagates to
  `env.reset(seed=...)`, so the spawn perturbation is reproducible too.
- **Spawn perturbation** (§7.3): `GazeboLaneEnv.reset` applies a random
  per-episode start perturbation (lateral ±0.05 m perpendicular to the tangent,
  heading ±0.15 rad) via `self.np_random`; configurable under
  `spawn_perturbation` in `train_ppo.yaml`, disabled for deterministic eval.
- **§7.5 evaluation harness**: new pure `eval_metrics.summarize_eval` (laps,
  cage intervention rate, emergencies, mean/abs ey & epsi) + `test_eval_metrics.py`
  (7 tests); `eval_policy.py` rewritten to disable spawn perturbation, collect
  per-step records, and write `cage_status.csv` + `summary.json` + `metadata.json`
  under `experiments/sim/runs/<run_id>/`. Evaluation runs through `GazeboLaneEnv`,
  i.e. under the same in-process cage as deployment (D-34, SR-009).
- **§7.2.4 reconciled**: termination text updated from `|ey| > lane_width/2` to
  the implemented `|ey| > road_width/2`, with rationale and a cross-ref to
  `docs/09_environment_design.md` (ED-4).

### Verification

- `pytest cage/tests policy/tests` → 171 passed (+7 in `test_eval_metrics.py`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- The training/eval loops still require the Gazebo/Jazzy host; the pure pieces
  (metrics, reward, cage bridge) are verified here.

---

## [29.05.2026] — F3 D39 closed: reward unit tests + environment/reward design docs

**Document(s) affected:** `policy/tests/test_rewards.py` (new),
`docs/09_environment_design.md` (new),
`docs/10_reward_function.md` (new).
**Phase:** F3.
**Gate context:** after G2; Week-8 (D36–D40) infrastructure deliverables.
**Author:** Samuel.

### Change

- Closed F3 day **D39**: added `policy/tests/test_rewards.py` — 10
  synthetic-state unit tests for `compute_reward` (forward-progress, ey/epsi/
  Δsteer penalties, termination penalty, negative-speed clamp, linear
  composition, `w_ey`>`w_eps` dominance, YAML reward-block completeness). The
  reward function previously had no tests.
- Added the **D36** deliverable `docs/09_environment_design.md`:
  observation/action spaces, wrapper structure, reset/episode, actuation
  mapping, cage-in-loop, design decisions + rejected alternatives, traceability,
  anticipated defense Q&A.
- Added `docs/10_reward_function.md`: formula, components, weights v1.0 +
  rationale, simplicity argument, cage interaction, degeneration / reward-hacking
  analysis, verification, anticipated defense Q&A.
- Numbered `docs/0X` are kept in **English** (repo convention); the Spanish
  working copies live, gitignored, in `docs/.phases/Fase 3/`
  (`environment_design_v0.1.md`, `reward_function_design.md`).

### Rationale

D39's reward test suite was the one Week-8 deliverable that is pure and closable
off-host; it guards spec (§7.2.3) ↔ implementation consistency. The two design
docs are defense-preparation back-up for the viva, expanding §7.2–§7.3 with the
"why" and the rejected alternatives at a depth the thesis chapter does not
carry. They are rationale documents; §7.2 remains the normative source.

### Verification

- `pytest cage/tests policy/tests` → 164 passed (154 + 10 in `test_rewards.py`).
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.

---

## [29.05.2026] — F3 TS-01: cage wired into PPO training (in-process, D-34)

**Document(s) affected:** `docs/DECISIONS.md` (D-34),
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.5 + checklist),
`src/cobraflex_rl/cobraflex_rl/cage_bridge.py` (new),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_cage_bridge.py` (new).
**Phase:** F3.
**Gate context:** after G2, before the first PPO training run.
**Author:** Samuel.

### Change

Implemented TS-01: `GazeboLaneEnv` now routes the policy action through the
safety cage in `enforcement` mode (D-34). The cage is invoked **in-process** —
the env builds a cage `State` from the tracker, forms
`raw_action = (policy_steering, throttle_nominal)`, calls the same
`cage.cage_node.SafetyCageNode.step()` (with the same `cage/cage.yaml`) that
`cage_ros_node` wraps in deployment, and maps the safe `(steering, throttle)`
to `/cmd_vel` by replicating `vehicle_control_node` (throttle→speed,
`angular.z = steering·yaw_gain`, emergency→stop). Reward is computed on the
safe action. A fresh `SafetyCageNode` is built per episode (no latched C-05 /
rate-limiter state across rollouts). New ROS-free glue `cage_bridge.py`; new
`cage:` block in `train_ppo.yaml` (with an `enabled:false` debug fallback).
D-34's implementation note + Status and §7.2.5 were updated to record the
in-process mechanism instead of the topic round-trip originally sketched.

### Rationale

The env is a synchronous `gym.Env` loop; a per-step `/raw_action`→`/safe_action`
ROS handshake with a separate node would add asynchrony (harming determinism
under seed=42, §7.2.7), latency, and launch complexity. The in-process call is
byte-identical in cage behaviour (same class + YAML), stays deterministic, and
needs no launch changes (the env publishes `/cmd_vel` itself, so there is no
`vehicle_control_node` to co-launch and no double-actuation). Satisfies SR-009
(train under the deployed envelope) at the behavioural level. User-approved
this session.

### Impact

- Training now runs under the cage; the first PPO run can proceed (still
  pending, together with §7.4/§7.5 and `experiments/sim/training/` registration).
- Actuation constants `throttle_nominal` / `yaw_gain` / `min_speed_scale` are
  duplicated from `vehicle_control_node` defaults in `train_ppo.yaml`; keep in
  sync if those change.
- No cage code changed → cage v0.5.1 and all SR thresholds unchanged.

### Verification

- `pytest cage/tests policy/tests` → 154 passed (was 144; +10 in
  `test_cage_bridge.py`, incl. a C-01 correction routed through
  `SafetyCageNode`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- End-to-end training-loop validation on the Gazebo/Jazzy host is deferred to
  the F3 first-run task (ROS2/Gazebo cannot launch on the dev Windows host).

---

## [23.05.2026] — F3 kickoff: Training Specification, training pipeline fixes, D-34

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md`,
`docs/DECISIONS.md` (D-34), `src/cobraflex_rl/cobraflex_rl/ros_interface.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`src/cobraflex_rl/launch/train_lane.launch.py`,
`CLAUDE.md`.
**Phase:** F3.
**Gate context:** G2 passed; F3 entry.
**Author:** Samuel.

### Change

Gate G2 passed on the strength of `ros_run_20260523T153003Z` (9.91 laps,
0 emergencies, 144 tests, traceability PASS). F3 starts.

**Training Specification (Chapter 7 §7.2, artefact A1):** complete
8-component spec written before first training run, covering observation
space, action space, reward function (weights v1.0), termination/truncation
criteria, cage-in-training mode (D-34), PPO hyperparameters (v1.0),
seed/reproducibility policy, and checkpoint registry.

**D-34 (cage active during training):** documented in DECISIONS.md.
Strategy B chosen: training env routes through `/raw_action → cage →
/safe_action`. Implementation is F3 task TS-01.

**Training pipeline bug fixes:**
- `ros_interface.py`: world_name default `"road_carpet_world"` →
  `"lane_following_oval"` (wrong world would have caused service failures).
- `train_ppo.py`, `eval_policy.py`: centerline default `"centerline.yaml"`
  (3-point straight) → `"oval_right_lane_centerline.yaml"`.
- `train_lane.launch.py`: replaced stub (wrong `gazebo.launch.py` +
  `obstacles.world`) with correct `gazebo_mesh.launch.py` + oval world
  + `headless` arg for faster training.

### Rationale

The training pipeline had accumulated stub code from F1 that pointed to
wrong worlds and wrong centerlines. These would have caused silent failures
(training on a 3-point straight, or failing to find the Gazebo service)
on the first F3 training attempt. Fixing before training is cheaper than
debugging after.

### Verification

- AST OK on all modified Python files.
- `pytest cage/tests policy/tests` → 144 passed (no new tests; fixes are
  config/default changes that only activate at ROS2 runtime).
- `python3 tools/check_traceability.py --strict` → all checks PASS.

---

## [23.05.2026] — lane_perception_node: speed spike rejection filter

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/lane_perception_node.py`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Added Gazebo odometry spike rejection to `LanePerceptionNode`.
Speed is now filtered in two steps:

1. **Spike rejection:** if `speed_raw > speed_spike_factor × max(speed_smooth, 0.01)`,
   the sample is discarded (held at `speed_smooth`) and a `WARNING` is logged.
   Default `speed_spike_factor = 5.0`; calibratable as a ROS2 parameter.

2. **EMA smoothing:** the (possibly clamped) raw value is fed into an EMA with
   the same `ema_alpha` parameter already used for `ey`/`epsi`.

`_speed_smooth` is reset to `None` on warp detection alongside `_ey_smooth`
and `_epsi_smooth`.

### Rationale

Run `ros_run_20260523T150400Z` (14.3 min, 10+ laps) ended at t = 724.45 s
with a single-sample odom spike of 32.5 m/s (actual cruise speed 0.07 m/s).
The cage correctly fired C-04 + C-03 + C-05, latching the vehicle stopped for
the remaining 2.3 min. Lane position at the moment was ey = −17 mm,
epsi = −4° — a false positive caused by a Gazebo physics artifact, not a real
safety event. With `speed_spike_factor = 5.0`, the spike (32.5 >> 0.35 m/s
threshold) is rejected and C-04/C-03 do not fire.

### Impact

Nominal runs are unaffected (no spike → rejection branch never taken).
EMA adds at most ~5 ms of smoothing lag at 20 Hz, negligible for the PD controller.
No cage YAML or SR changes required; this is a sensor pre-processing fix.

### Verification

- `pytest cage/tests policy/tests` → 144 passed.
- AST check on modified node: OK.
- Simulated spike scenario: speed_raw = 32.5, speed_smooth = 0.07, factor = 5.0
  → threshold = 0.35 → spike rejected, WARNING emitted, speed_smooth unchanged.
- **ROS2/Gazebo validation run `ros_run_20260523T153003Z`:** 14.1 min (845.5 s),
  16 910 cycles, **0 emergencies**, speed max 0.200 m/s. Same 8-intervention
  pattern (C-02 × 1, C-06;C-02 × 5, C-06 × 2) as the G2 evidence run. The
  run covered the same elapsed-time window (~845 s) where the prior spike had
  occurred, with no C-03/C-04/C-05 activation.

---

## [23.05.2026] — F2 pipeline hardening: logger flush, watchdogs, wraparound guards, packaging fixes

**Document(s) affected:** `cage/logger.py`, `cage/tests/test_pipeline.py`,
`policy/baseline_pd.py`,
`src/cobraflex_rl/cobraflex_rl/cage_logger_node.py`,
`src/cobraflex_rl/cobraflex_rl/lane_perception_node.py`,
`src/cobraflex_rl/cobraflex_rl/vehicle_control_node.py`,
`src/cobraflex_rl/package.xml`,
`src/safety_cage/safety_cage/cage_ros_node.py`,
`src/safety_cage/launch/lane_following.launch.py`,
`manuscript/chapters/chapter_06_implementation.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Pipeline-wide audit and hardening pass before F3. No nominal-behaviour
changes; every fix is either a fail-safe that only activates on failure
(watchdogs, wraparound guards, polling unpause) or a packaging/observability
improvement.

CageLogger (`cage/logger.py`): line-buffered file open so each
`writerow` is flushed to disk immediately, eliminating tail-truncation
on abrupt termination; warns when overwriting an existing CSV.

cage_logger_node: 5 s wall-clock watchdog that surfaces silent
upstream failures (no /cage_status received vs. count stuck);
`output_dir` resolved to absolute path; new `cage_mode` parameter
stamped into every CSV row and into `metadata.json`.

vehicle_control_node: 10 Hz wall-clock watchdog that publishes
`cmd_vel=(0, 0)` if no `/safe_action` arrives within 0.5 s, preventing
the Gazebo DiffDrive plugin from holding a stale command after an
upstream crash.

lane_perception_node: warp detection (>0.5 m odom jump) resets the
`PolylineTracker` neighbourhood cache and the EMA, with WARN log;
EMA on `epsi` rewritten to operate on the wrapped delta so the
smoothed estimate tracks the shortest-arc trajectory across the ±pi
seam.

cage_ros_node: dropped the redundant `ctx["reset"]` pass-through and
the dead `require_state_for_first_cycle` parameter.

policy/baseline_pd.py: `psi_dot` finite-difference now uses
`wrap_angle(psi - prev_psi)` so a heading that crosses ±pi does not
produce a spurious 120 rad/s derivative.

lane_following.launch.py: replaced the hardcoded 4 s TimerAction +
fixed world name with a polling loop that retries the gz unpause
service every 0.5 s for up to 30 s; world name is now an explicit
`world_name` launch argument.

cobraflex_rl/package.xml: declared previously-missing `std_msgs` and
`cobraflex_safety_msgs` dependencies.

Chapter 6 manuscript: §6.5.3 pruned to match real coverage (no
`hypothesis`); §6.5.4 rewritten around the existing
`test_pipeline.py` instead of the aspirational `pytest-launch_testing`
suite; §6.5.5 acknowledges that the pre-commit hook and GitHub
Actions workflow are F3 work; Listing 6.1 added with the actual
`LaneBoundaryRule.evaluate` skeleton.

### Rationale

The earlier "no se genera CSV" report and the latent C-05 risk from
the unwrapped heading derivative motivated the audit. The fixes
target three failure modes: silent data loss (logger flush), silent
pipeline failures (three watchdogs, polling unpause), and latent
correctness bugs that F2 happens not to hit but F3 with arbitrary
spawn orientations will (wraparound in PD and perception). Pruning
the manuscript brings §6.5 in line with what the repo actually
implements, so Gate 2 evidence does not over-promise.

### Impact

Nominal pipeline produces bit-identical CSV content (only the `mode`
column now reads `"enforcement"` instead of empty). Watchdogs are
dormant in nominal operation. The new package.xml deps unblock
`rosdep install` on a clean machine. No re-run of historical
scenarios needed; the run candidate `ros_run_20260523T073134Z`
remains the Gate-2 evidence.

### Verification

- `pytest cage/tests policy/tests` -> 144 passed (143 existing + 1 new
  `test_pipeline_handles_missing_state_until_first_obs`).
- `python3 tools/check_traceability.py --strict` -> all checks PASS,
  0 warnings.
- `python3 tools/check_scenario_yaml.py` -> PASS, 0 errors.
- AST OK on all 5 modified pipeline nodes.

## [23.05.2026] — Chapter 6: promoted definitivo pre-F3 run to all §6.3.5/§6.5.4/§6.6 placeholders

**Document(s) affected:** `manuscript/chapters/chapter_06_implementation.md`,
`experiments/sim/runs/ros_run_20260523T153003Z/summary.json`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Replaced all numerical references previously sourced from `ros_run_20260523T073134Z`
(4.50 laps, 379.8 s, 7 597 cycles) with values from the definitive pre-F3 run
`ros_run_20260523T153003Z` (9.91 laps, 845.4 s, 16 910 cycles, 0 emergencies).

Sections updated: §6.3.5 (logger throughput), §6.5.4 (throughput test body and
latency figure), §6.6.1 (demostración integrada), §6.6.2 (all three preliminary
metrics). Test count updated from 143 → 144 in §6.5.2 and the internal appendix.

Created `experiments/sim/runs/ros_run_20260523T153003Z/summary.json` with the
full metrics (laps, distance, dt stats, intervention breakdown, signal ranges).

### Rationale

The new run includes the speed-spike rejection filter and ran for ~14 min without
any emergency, providing 2.2× more evidence than the prior 6.3 min run. The
same pipeline, same cage YAML and same PD gains — only the odom spike filter
is new. All three §6.6.2 metrics improve: intervention rate drops from 0.105%
to 0.047%, completion extends from 4.50 to 9.91 laps.

### Verification

- `python3 tools/check_traceability.py --strict` → all checks PASS, 0 warnings.
- `grep -n "T073134Z\|379\.8\|7 597\|4\.50 vueltas\|0\.105%\|53\.0 ms\|143 casos"` → 0 matches.

---

## [23.05.2026] — Chapter 6 §6.3.5/§6.4.2/§6.5.2/§6.5.4/§6.6: resolved [COMPLETAR FASE 2] placeholders with run candidate data

**Document(s) affected:** `manuscript/chapters/chapter_06_implementation.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Replaced the numerical `[COMPLETAR FASE 2]` placeholders in §6.3.5
(logger throughput), §6.4.2 (PD gains v0.8.0), §6.5.2 (test counts:
61 per-rule, 132 cage suite, 143 with PD), §6.5.4 (cycle latency
50.0/50.0/53.0 ms, 0 dropped log lines), §6.6.1 (4.50 laps over
target 3, 0 emergency cycles, 8 cage interventions distributed
across C-02 and C-06), and §6.6.2 (intervention rate 0.105%,
completion rate provisional 100% with N=1). Updated the chapter's
internal appendix to mark these placeholders as done and to add a
new pending item for the N≥30 multi-run completion-rate campaign.

### Rationale

The run `ros_run_20260523T073134Z` (PD 0.8.0, cage 0.5.1, SC-NOM-01,
enforcement) is the Gate-2 candidate evidence; backfilling the
chapter with its measured values is required before tagging G2.
Honest scoping: the multi-run completion-rate campaign (N=30) is
explicitly flagged as outstanding rather than fabricated, and the
spawn perturbation described in §6.6.1 is noted as not applied in
this run.

### Impact

Chapter 6 numerical placeholders are now closed; outstanding items
for G2 are Figura 6.1, Listing 6.1, multi-run completion campaign,
cross-chapter consistency check with Chapter 5, and pre-existing
`colcon test` lint failures in `cobraflex`.

### Verification

- `python3 tools/check_traceability.py --strict` -> all checks PASS, 0 warnings.
- Manual grep confirms no remaining numerical `[COMPLETAR FASE 2]`
  markers; only the convention preamble (line 8), the Figura 6.1
  placeholder (line 107), and the Fase-6 polish line (line 757) remain.

## [23.05.2026] — Gate 2 candidate evidence: ROS oval run completes >3 laps without emergency

**Document(s) affected:** `experiments/sim/runs/ros_run_20260523T073134Z/metadata.json`, `experiments/sim/runs/ros_run_20260523T073134Z/summary.json`, `docs/04_cage_specification.md`, `experiments/sim/oval_pd_cage_smoke.py`, `tools/check_scenario_yaml.py`, `tools/README.md`, `scenarios/README.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Added reproducibility metadata and a summary file for the ROS2/Gazebo run
`ros_run_20260523T073134Z`. The run is the first Gate-2 candidate evidence
for the full F2 pipeline: baseline PD 0.8.0, cage YAML 0.5.1, right-lane
oval centerline, cage in enforcement mode.

The committed `summary.json` declares the evidence segment explicitly: the
full monotonic timestamp segment, lines 2–7598 of `cage_status.csv`.

### Rationale

The closure segment runs for 379.799 s, covers an estimated 4.504501 laps
against the ODD-3 perimeter of 8.0232 m, and records zero emergency-mode
cycles. Cage activity is limited to 8 intervention cycles, all C-02/C-06
bounded corrections, with no C-01, C-03 or C-05 activation in nominal
lane-following.

### Impact

This provides the empirical evidence needed for the F2 end-to-end demo
criterion. The pure-Python `oval_pd_cage_smoke.py` docstring is updated to
classify it as a kinematic chain sanity check rather than the Gate-2 closure
demo, because it does not model the current ROS2/Gazebo stack. The evidence
is not yet a full Gate-2 closure by itself: Chapter 5/6 placeholders and the
inherited `colcon test` lint failures in `src/cobraflex` remain to be addressed
or explicitly scoped before tagging G2. The scenario YAML validator promised
by `scenarios/README.md` is added in Phase-2 scope: default mode accepts
explicit stubs with warnings, while `--strict` turns those warnings into
failures for later gates.

### Verification

- `pytest cage/tests policy/tests` -> 143 passed.
- `python3 tools/check_traceability.py --strict` -> all checks PASS, 0 warnings.
- `python3 tools/check_scenario_yaml.py` -> PASS, 0 errors, warnings for deferred stubs/missing later-phase YAMLs.
- `colcon build --packages-select cobraflex_safety_msgs safety_cage cobraflex_rl cobraflex --symlink-install` -> 4 packages finished.
- `colcon test --packages-select cobraflex_safety_msgs safety_cage cobraflex_rl cobraflex` -> package tests execute, but `cobraflex` fails pre-existing lint/pep257 checks.

## [22.05.2026] — PD Baseline 0.6.0: zero kd_y and kp_h — polyline signals unreliable at curves (Phase 2)

**Document(s) affected:** `policy/baseline_pd.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

`kd_y` 0.5 → 0.0; `kp_h` 1.0 → 0.0; `version` bumped from `0.5.0` to `0.6.0`.

### Rationale

Two consecutive sim runs (`ros_run_20260522T175259Z`, `ros_run_20260522T180231Z`)
showed emergency stop at the first oval curve (t ≈ 13.75 s, κ ≈ 1.08 rad/m),
car never completing a lap — F2 FAIL.

Root cause: the polyline tracker (±6 segment local search) jumps segments at
curve entries, producing step discontinuities in both `ey` and `epsi` within
a single 50 ms cycle.

- `kd_y`: `ey` jumps ±0.15 m → `y_dot ≈ ±3 m/s` → `kd_y × y_dot ≈ 1.5`,
  saturating steering alone. Fix: `kd_y → 0.0`.
- `kp_h`: even with `kd_y = 0`, `epsi` steps ±0.25–0.36 rad at curve entries.
  Combined with feedforward (0.49) and kp_y term (0.28), total reaches 1.13 →
  saturation → C-06 + C-03 + C-05 chain. Fix: `kp_h → 0.0`.

Both fixes follow the same reasoning as `kd_h → 0.0` in v0.5.0: piecewise-
constant polyline signals are not reliable inputs for PD terms. The effective
controller is now `steering = kappa_ff·κ − kp_y·ey`, which stays below 1.0
for all physically reachable (ey, κ) on the F2 oval.

Also: `_LOCAL_SEARCH_RADIUS` in `polyline_tracker.py` reduced 6 → 2. The
local search radius controls how many adjacent segments are considered per
cycle. With radius=6, the tracker could jump up to 6 segments (0.66 m) in
one cycle — the F2 oval's 0.11 m/segment spacing combined with near-equidistant
geometry at curve entry allows this. Those multi-segment jumps produce the
ey/epsi discontinuities described above. Radius=2 (0.22 m, 22× headroom over
the 0.01 m/cycle at 0.2 m/s) enforces continuity while tolerating a 20× speed
increase before the constraint binds.

### Impact

`policy/baseline_pd.yaml` and `src/cobraflex_rl/cobraflex_rl/polyline_tracker.py`.
No cage rules, SRs, or hazards affected. Re-run oval scenario to verify lap
completion.

### Verification

`python3 tools/check_traceability.py` — no ID references changed.

---

## [22.05.2026] — PD Baseline 0.7.0: restore kp_h=0.3 — heading correction safe with bounded search radius (Phase 2)

**Document(s) affected:** `policy/baseline_pd.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

`kp_h` 0.0 → 0.3; `version` bumped from `0.6.0` to `0.7.0`.

### Rationale

Third sim run (`ros_run_20260522T180853Z`) showed that with `kp_h=0.0` the car's
heading drifts at curves (epsi reaches 0.25–0.35 rad), which alone triggers C-05
`theta_warning` (threshold 0.349 rad = 20°). Without proportional heading
correction the curvature feedforward + kp_y lateral correction cannot damp the
heading drift fast enough on the R=0.9225 m curve.

After reducing `_LOCAL_SEARCH_RADIUS` from 6 to 2 (v0.6.0 / polyline_tracker.py),
the maximum epsi jump from a 2-segment advance is ~0.094 rad. At `kp_h=0.3`:

```
kp_h × Δepsi_max = 0.3 × 0.094 = 0.028   (negligible for saturation)
worst-case total  = kappa_ff(0.487) + kp_y×ey_max(0.366) + kp_h×epsi_max(0.028)
                  = 0.881 < 1.0  ✓
```

The heading term is now safe to restore at a smaller gain, and necessary to
prevent the C-05 theta_warning chain.

### Impact

`policy/baseline_pd.yaml` only. No cage rules, SRs, or hazards affected.
`policy/tests/test_baseline_pd.py` updated: `test_heading_has_no_effect_with_kp_h_zero`
renamed to `test_heading_error_produces_corrective_steering` to reflect kp_h=0.3.

### Verification

`python3 tools/check_traceability.py` — no ID references changed.

---

## [18.05.2026] — Cage 0.5.0: SR-010 Part 2 — inter-cycle oscillation detection (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Bumped `cage.version` from `0.4.0` to `0.5.0`. Added a new top-level
`cage.oscillation` subsection with three parameters:

- `f_osc_max_hz: 5.0` — alternation-rate threshold (per-rule, on the sign
  of the steering correction) above which the cage logs the cycle.
- `t_osc_window_s: 1.0` — sliding window over which the alternation
  rate is computed.
- `t_osc_persist_s: 3.0` — sustained-violation duration above which the
  oscillation triggers C-05 emergency mode via a new
  `oscillation_detected` trigger.

### Rationale

Implements SR-010 Part 2 (Inter-cycle oscillation check) as documented
in §"Joint-envelope assertion and conflict resolution" of the cage
specification. Detects pathological policy-cage feedback where the cage
fires alternately left/right on the same rule across consecutive
cycles, which the safety analysis treats as evidence of a degenerate
loop requiring human intervention. SR-010 Part 1 (end-of-cycle
joint-envelope assertion / C-05 Trigger 7) remains deferred because the
per-rule `safe_envelope_predicate_holds(state, action)` API it requires
does not yet exist on the rule contract.

### Impact

- `SafetyCageNode` now maintains a per-rule signed-correction history
  (`_osc_history`) and a per-rule violation start timestamp
  (`_osc_violation_start`). The new `step()` result also exposes
  `oscillation_rates_hz` (per-rule current rates) and
  `oscillation_persistent` (the boolean fed to C-05) for the logger.
- `EmergencyRule._evaluate_triggers` reads `ctx["oscillation_detected"]`
  and contributes it to the `any` aggregate; new explicit branch in
  `evaluate()` emits the `triggered-oscillation` reason when fired.
- Defaults on `SafetyCageNode.__init__` make the feature inert
  (`f_osc_max=inf`) when the YAML lacks the `oscillation` subsection,
  preserving backward compatibility with 0.4.0 YAMLs.

### Verification

- `pytest cage/tests/` — full suite passes including the new
  `test_oscillation.py` cases (no fire below threshold, log without
  emergency at fast rates, emergency once persistence exceeds
  `t_osc_persist_s`).
- `tools/check_traceability.py` — unchanged (SR-010 is in the registry;
  no new SR added).

---

## [18.05.2026] — Cage 0.4.0: complete C-05 trigger set (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Bumped `cage.version` from `0.3.0` to `0.4.0`. Added two parameters under
`c05_emergency`:

- `v_warning_mps: 0.4` — speed threshold above which the compound trigger
  uses the high-energy persistence (SR-005 Trigger B). 80 % of
  `v_max_straight_mps`.
- `delta_t_max_fast_s: 0.1` — shorter persistence applied when the
  high-energy variant fires.

### Rationale

Both parameters complete the C-05 trigger set per the cage specification
(`docs/04_cage_specification.md` §C-05): Trigger 2 (high-energy compound)
joins the already-implemented Triggers 1 (low-energy compound), 3
(stale), 4 (invalid), 5 (missing-state via the cage_node counter) and 6
(external stop). Trigger 7 (joint-envelope assertion of SR-010) remains
deferred because the per-rule predicate API it requires does not yet
exist.

### Impact

- `EmergencyRule.__init__` now reads `v_warning_mps` and
  `delta_t_max_fast_s`. Both have constructor defaults (`inf` and the
  low-energy persistence respectively) so older YAMLs continue to load,
  but the high-energy trigger is effectively disabled in that case.
- `SafetyCageNode.step()` now accepts `state=None` to flag a missing
  observation; consecutive `None` calls feed the missing-state trigger
  (5) once they exceed `cage.n_missing_max_cycles`.
- No re-run of validation campaigns required (no existing parameter
  value changed).

### Verification

- `pytest cage/tests/` — all rule and integration tests pass, including
  new tests for the high-energy trigger and the missing-state counter.
- `tools/check_traceability.py` — unchanged (no SR or cage rule added or
  modified at the registry level).

---

## [18.05.2026] — Cage 0.3.0: parameters required by executable rules (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

Bumped `cage.version` from `0.2.0` to `0.3.0`. Added three parameters needed
by the first executable cut of the rule logic (no existing parameter values
were modified):

- `c03_ttlc.d_max_m: 0.16` — TTLC projection needs the lane half-width;
  duplicated here with the explicit comment that it must mirror
  `c01_lane_boundary.d_max_m` (coupling documented in-place).
- `c03_ttlc.v_min_estimate_mps: 0.05` — kinematic floor below which
  `compute_ttlc` returns infinity (avoids division by near-zero lateral
  velocity at standstill).
- `c04_speed_ceiling.k_throttle_per_mps: 5.0` — proportional gain that
  maps speed excess over `v_max(κ)` to throttle reduction in the
  correction formula `throttle_safe = max(0, throttle_raw − k·excess)`.

The three parameters are required by the rule implementations under
`cage/rules/c03_ttlc.py` and `cage/rules/c04_speed_ceiling.py` checked
in alongside this bump. Their default values follow the Phase 2 plan
(`docs/.phases/Fase 2/fase_2_detallada.md` §5.3 and §5.4); both
`d_max_m` and `k_throttle_per_mps` are inherited as-is, and
`v_min_estimate_mps` reuses the value documented under the same plan
section. All three remain candidates for revision once the calibration
campaign (M-1..M-5) closes and the policy-side margins of SR-003 are
exercised.

- Rule constructors `TTLCRule.__init__` and `SpeedCeilingRule.__init__`
  now read these keys; older YAMLs without them will fail to instantiate.
- No change to traceability matrix — no SR or hazard added.
- No re-run of validation campaigns required (no value of any existing
  parameter changed).

- `pytest cage/tests/` — all rule unit tests pass.
- `tools/check_traceability.py` — unchanged (no SR or cage rule added or
  modified at the registry level).

---

## [30.04.2026] — Initial baseline (Phase 0)

**Document(s) affected:** all `docs/*.md` files.  
**Phase:** F0.  
**Gate context:** before G0.  
**Author:** Samuel.  

Initial creation of living documents from Phase 0 templates. Hazard Register seeded with H-01 to H-07. SRS seeded with SR-001 to SR-008. Cage Specification seeded with C-01 to C-06. Scenario Library seeded with 9 scenarios across 3 categories. Metrics catalogue seeded with M-P, M-S, M-I, M-C families. Traceability Matrix seeded with the chains derived from the above.

Establish the baseline that subsequent phases will refine. The numerical thresholds in the SRS are first-cut estimates derived from the platform geometry and the kinematic envelope; they will be refined in Phase 1 as the analysis matures.

None upstream (this is the baseline). Downstream: Phase 1 will refine numerical parameters and may add or merge hazards based on closer analysis.

`tools/check_traceability.py` reports: 0 orphans on hazards, 0 orphans on SRs, 0 orphans on cage rules, 0 orphans on scenarios, 0 orphans on metrics. Coverage requirements (1)–(8) all satisfied.

---

## [30.04.2026] — Update of chapter 3

**Document(s) affected:** chapter_03_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 3 Metodology with comparison between classical V model and adapted for this thesis

---
---

## [02.05.2026] — Update of chapter 1

**Document(s) affected:** chapter_01_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 1 and double check all references

---
---

## [02.05.2026] — Update of chapter 2

**Document(s) affected:** chapter_02_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 2 with related work, double check of references pending

---
---

## [02.05.2026] — Rename of templates + added 00_odd_specification.md

**Document(s) affected:** chapter_02_metodology.md  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Added 00_odd_specification.md, changed of names of templates for better understanding

---
---

## [04.05.2026] — Update of Chapters 1, 2 & 3 with new papers

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapters 1,2 and 3 with related work, double check of references pending

---
---

## [11.05.2026] — Update of Chapters 1, 2 & 3

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapters 1,2 and 3

---
---

## [11.05.2026] — Added HARA script check

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

---
---

## [13.05.2026] — Gate 0 closed

**Document(s) affected:** -  
**Phase:** F1  
**Gate context:** after G0  
**Author:** Samuel Sanchez

---

## [13.05.2026] — Pre-G1 consolidation: rating fixes, SR consistency, STPA expansion, chapter cleanup

**Document(s) affected:** `docs/02_hazard_register.md`, `docs/03_safety_requirements.md`, `docs/05_scenario_library.md`, `manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Pre-G1 consolidation pass over the safety analysis and requirements artefacts, applying the recommendations of `docs/.phases/Fase 1/phase1_refinement_notes.md` and the defaults of `docs/.phases/Fase 1/phase1_supervisor_briefing.md` to bring the F1 deliverables to G1-ready state. Specific edits:

*Hazard Register (`docs/02_hazard_register.md`).* Removed stray `**PLACEHOLDERS**` scaffold line; updated `Last update` to 13.05.2026; added explicit "Severity convention" note documenting the analogue-real-vehicle interpretation (decision D-03, Decision 1 default of the supervisor briefing). Added per-hazard "Rating rationale" paragraphs to H-01..H-07 with written justification for each S/E/C level. Applied three rating consolidations recommended by the refinement notes: H-03 split rating `S=2 (S=3 in tight curves)` → conservative single `S=3` (worst case in curve) with tightened description; H-05 `S=2` → `S=1` aligned with analogue-real-vehicle convention (abrupt actuation is primarily a comfort-and-wear hazard); H-06 `E=1 to E=2` → single `E=2` dominated by physical-deployment scenario. Added to H-01 a note that C=2 is conditional on TTLC predictor reliability. Added to H-02 the explicit rationale for not upgrading severity despite escalation into H-01 (Decision 2 default). Expanded STPA-light findings for H-01, H-02 and H-04 from shallow notes to a systematic pass across the four UCA categories applied to each principal control action (Decision 5 default: into the living document). H-04 STPA section additionally registers two design findings outside the standard UCA grid (trigger persistence requirement and asymmetric exit via explicit reset). Updated STPA scope statement accordingly.

*Safety Requirements Specification (`docs/03_safety_requirements.md`).* Updated `Last update` to 13.05.2026. **Critical consistency fix**: SR-008 `t_stop_max` raised from `1.5 s` to `1.7 s` to resolve a numerical inconsistency with SR-005 (`a_min = 0.3 m/s²` at `v_max_straight = 0.5 m/s` implies a stopping time of approximately 1.67 s, which the previous `t_stop_max = 1.5 s` violated). The fix follows option (a) of Decision 6 in the supervisor briefing. Expanded parameter rationales: SR-002 now includes a bicycle-model recoverability derivation for `θ_max = 25°`; SR-003 marks the policy-side component of `t_min` (`0.7 s`) as provisional pending the first F3 training prototype; SR-004 documents the rationale for the curvature-decay coefficient `k_κ = 0.3` and the pending-measurement status of `v_max_curve` and `v_max_straight` (measurement M-4); SR-005 documents the provisional status of `a_min` pending measurement M-3 and the STPA-informed rationale for `Δt_max = 0.2 s`; SR-006 declares `δ_max` values as conservative defaults pending M-5 and post-prototype cross-check; SR-007 expands the rationale of `staleness_max` and `N_missing_max` and clarifies the deliberate width of plausible state ranges.

*Scenario Library (`docs/05_scenario_library.md`).* SC-NOM-01 now declares explicit "Cage rules exercised" (C-01, C-06) to clear the `check_traceability.py` warning on Constraint (5) for C-06.

*Chapter 4 (`manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`).* Closed nine `[COMPLETAR FASE 1 / Dxx]` markers across §4.4.3, §4.4.4, §4.5.2, §4.5.3, §4.6.3, §4.6.4, §4.7.2, §4.8.2 and §4.8.3. Updated the Hazard Register compact table in §4.4.3 to reflect the consolidated H-03 / H-05 / H-06 ratings. Wrote §4.4.4 (HARA coverage argument in three axes), §4.5.2 (STPA-light results synthesis), §4.7.2 (relative completeness argument). Wrote a synthesis paragraph in §4.6.4 with summary rationale for SR-002..SR-008 to complement the SR-001 worked example. Updated §4.6.3 table to reflect the SR-008 `t_stop_max = 1.7 s` value and the provisional flag on SR-005 `a_min`. Removed obsolete `[COMPLETAR FASE 1 / Dxx]` markers from §4.4, §4.5, §4.6 and §4.8 headings.

*Chapter 3 (`manuscript/chapters/chapter_03_methodology.md`).* Closed the `[COMPLETAR FASE 1 — IDs definitivos]` marker in §3.5.2 by substituting the placeholder identifiers `SR-001..SR-00k` and `C-01..C-0n` with the definitive ranges `SR-001..SR-008` and `C-01..C-06`.

The refinement notes and the supervisor briefing for F1 identified a list of edits required before G1 can close. Most are textual or methodological (rating justifications, per-SR rationale) but one is a critical numerical fix (SR-005 ↔ SR-008 inconsistency) that the briefing's Decision 6 had pre-committed to resolve under option (a). The consolidation pass applies all the edits that do not depend on pending platform measurements (M-1 through M-5), leaving the platform-dependent parameters (`a_min`, `v_max_curve`, `δ_max`) explicitly flagged as provisional in both the SRS and Chapter 4.

Downstream: the cage parameters in `cage/cage.yaml` (`a_min_mps2 = 0.3`, `c04_speed_ceiling.*`, `c06_rate_limiter.*`) remain numerically unchanged in this pass; they are flagged as provisional in the SRS and will be revised after M-3, M-4 and M-5 are executed (with corresponding bump to `cage.yaml` version 0.2.0 at that point). The Hazard Register STPA expansion is purely documentary and does not introduce new SRs or new cage rules. The scenario library change adds explicit C-06 mention to SC-NOM-01 without altering its run semantics.

After the pass:

- `python tools/check_traceability.py` is expected to PASS without warnings (Constraint 5 warning on C-06 resolved by the SC-NOM-01 edit).
- `pytest cage/tests/` is expected to PASS unchanged (no cage logic affected).

Both verifications are to be re-run as the final step of this consolidation.

---

## [13.05.2026] — cage.yaml v0.2.0: parameter-rationale consolidation

**Document(s) affected:** `cage/cage.yaml`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Bumped `cage.version` from `"0.1.0"` to `"0.2.0"`. No parameter values
were modified; the bump is a documentation-precision revision that
adds per-rule rationale comments linking each parameter to the
corresponding SR rationale in `docs/03_safety_requirements.md` and
flagging the parameters that remain provisional pending the pre-G1
measurement campaign (`experiments/calibration/`). Specifically:

- C-01 `d_max_m`: flagged `[provisional, M-1, M-2]` (lateral noise σ
  and end-to-end control latency).
- C-03 `t_min_s`: flagged as having a provisional policy-side
  component (0.7 s of the 1.0 s total) pending the F3 prototype.
- C-04 `v_max_straight_mps`, `v_max_curve_mps`, `k_kappa_*`: flagged
  `[provisional, M-4]` and dependent on ODD TBD-Q1 / TBD-Q9.
- C-05 `a_min_mps2`: flagged `[provisional, M-3]` with explicit
  consistency note referencing SR-008 `t_stop_max = 1.7 s` (the
  kinematic stopping time at `v_max_straight = 0.5 m/s` is 1.67 s).
- C-06 `delta_max_steering_per_cycle`, `delta_max_throttle_per_cycle`:
  flagged `[provisional, M-5 + F3 prototype]`.

The header description is expanded to declare that the SR-005 ↔ SR-008
consistency reconciliation is documented in the immediately preceding
CHANGELOG entry, and that the next planned bump (0.3.0) will follow
the closure of M-1 through M-5 with the corresponding parameter
revisions.

The supervisor briefing for F1 (`docs/.phases/Fase 1/phase1_supervisor_briefing.md`
"What I will produce after this session" item 3) commits to a 0.2.0
bump with the "revised parameters". Because the parameter revisions
that depend on platform measurements have not yet been executed, the
0.2.0 bump is restricted to rationale consolidation and traceability
to the SRS; the numerical revisions will produce the 0.3.0 bump after
the M-1 to M-5 campaign closes. This convention preserves semantic
versioning meaning: 0.2.0 marks the F1 rationale closure, 0.3.0 marks
the F1 numerical closure, and any minor bumps in between (0.2.1 etc.)
record purely cosmetic edits to comments or formatting.

Downstream: the cage logic and the unit tests are unaffected (no
parameter values changed); `pytest cage/tests/` continues to pass.
The hash of `cage/cage.yaml` referenced in the metadata of every
experimental run changes, which is correct semantic behaviour (the
file content has changed, the metadata correctly records that).

`pytest cage/tests/` → 13 passed (re-run after the bump).

---

## [13.05.2026] — Calibration campaign infrastructure (M-1..M-5)

**Document(s) affected:** `experiments/calibration/` (new directory).  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Created `experiments/calibration/` with one protocol document per
measurement and a top-level `README.md` that orchestrates the
campaign:

- `README.md`: campaign overview, effort table, execution-status
  table, output-format conventions, closure criterion.
- `M1_lidar_static_noise.md`: procedure, expected JSON schema,
  decision rule for confirming or revising SR-001 `d_max` margin.
- `M2_control_latency.md`: protocol for measuring end-to-end
  control latency, decision rule confirming or revising the
  `LATENCY_NOMINAL = 50 ms` assumption.
- `M3_max_deceleration.md`: protocol for measuring achievable
  deceleration, decision rule coordinating SR-005 `a_min` and
  SR-008 `t_stop_max` revisions.
- `M4_speed_vs_curvature.md`: protocol for the empirical
  v_max(κ) curve, decision rule for SR-004.
- `M5_actuator_rate.md`: protocol for measuring actuator rate
  envelope, decision rule for SR-006.

Each protocol document follows the same structure: Goal, Closes,
Effort, Procedure, Expected output JSON schema, Decision rule,
Results table (to be filled in upon execution), and Propagation
actions on completion. The propagation actions are explicit about
which artefacts (SRS section, cage.yaml block, manuscript section,
ODD-Spec parameter, CHANGELOG entry) must be updated when a
measurement closes.

The supervisor briefing for F1 (item 4 of "What I will produce after
this session") commits to "a documented set of measurement reports
under `experiments/calibration/` covering M-1 through M-5". The
measurements themselves require platform/simulator access and are
deferred to execution by the student; the *protocols* — which fix the
procedure, the output format, and the decision rule before
execution — are produced now so that the campaign can run with
explicit pre-registered criteria, removing degrees of freedom that
would otherwise enable post-hoc rationalisation of marginal results.

The "no measurement results yet" status is recorded transparently in
the README's execution-status table; the campaign closes (and the
G1 sign-off can proceed) when all five rows report `done` and the
corresponding propagation actions have been taken.

No downstream artefact is affected by the scaffold itself. When the
campaign executes, the propagation actions per protocol will affect
`docs/03_safety_requirements.md`, `cage/cage.yaml` (bump to 0.3.0),
`docs/08_odd_specification.md`, the relevant manuscript chapters, and
this CHANGELOG.

`tools/check_traceability.py` → all checks PASS, 0 warnings (no
artefacts cited by the validator are modified).
`pytest cage/tests/` → 13 passed (no cage logic affected).

---

## [13.05.2026] — SRS audit pass: hazard chain consolidated to 9H / 11SR / 11SC / 18M

**Document(s) affected:** `docs/02_hazard_register.md`, `docs/03_safety_requirements.md`, `docs/04_cage_specification.md`, `docs/05_scenario_library.md`, `docs/06_metrics_catalogue.md`, `docs/DECISIONS.md`, `tools/check_traceability.py`, `tools/sync_hazard_register.py`, `tools/sync_safety_requirements.py` (new).
**Phase:** F1.
**Gate context:** before G1.
**Author:** Samuel Sanchez.

Exhaustive audit of the hazard ↔ SR ↔ cage ↔ scenario ↔ metric chain identified seven bidirectional-traceability inconsistencies and six coverage gaps. Resolved by:

- **New hazards.** H-08 (Progress stall via reward exploitation, covering both stall and adversarial-direction sub-modes), H-09 (Cage rule composition hazard). Both promoted from the "Open hazards under consideration" section.
- **New SRs.** SR-009 (Minimum forward progress, liveness pattern, with `Δt_settle = 1.0 s` carve-out to resolve conflict with SR-005 / SR-008), SR-010 (Cage rule composition consistency, reformulated to match the cage spec's deterministic single-pass pipeline rather than strict priority + iteration), SR-011 (Heading stability without sustained oscillation, closes the in-band branch of H-02 that SR-002's magnitude bound did not constrain).
- **New metrics.** M-P6 (Stall rate, verifies SR-009), M-P7 (Heading variability, verifies SR-011). M-S2 "Contributes evidence to" extended to SR-010.
- **New scenarios.** SC-EDGE-05 (cage rule co-activation matrix, dedicated SR-010 verifier), SC-PERT-03 (reward-injection negative test that validates M-P6 by inducing stall on a fine-tuned policy variant).
- **Cage specification.** New §Joint-envelope assertion and conflict resolution section; new Trigger 7 in C-05 (joint-envelope failure → emergency); C-05 trigger list expanded with the high-energy Trigger B (`v > v_warning`, `Δt_max_fast = 0.1 s`) matching the new SR-005 dual-trigger.
- **Schema rename.** `related_cage_rules` → `implementation_type` in both machine-readable tables; admits `C-XX` lists, `training`, and `arbiter` markers. `owner` column removed (always the same author). Both sync scripts and downstream docs updated; `check_traceability.py` recognises the new categorical markers.
- **Tooling.** `tools/sync_safety_requirements.py` implemented analogously to `sync_hazard_register.py`. `tools/check_traceability.py` splitter bug fixed via new `extract_section_blocks()` helper — the last section of each kind no longer absorbs trailing machine-readable tables.
- **Methodological decision.** D-25 registered in `docs/DECISIONS.md`: non-cage mitigations (training constraint, cage architecture property) are first-class implementation types alongside numbered cage rules.

The audit was prompted by the user-reported empirical observation that an RL policy in past testing converged to inaction when the reward function over-penalised forward motion — registered as H-08. H-09 was already on the "Open hazards" list and registered as a side-effect of explicitly modelling cage composition. The bidirectional inconsistencies (e.g., SR-009 declaring `Verified by SC-NOM-01..03` while those scenarios did not reciprocally list SR-009) were latent because `check_traceability.py` only verified one direction of each chain.

- Final counts: 9 hazards, 11 SRs, 6 cage rules (unchanged), 11 scenarios, 18 metrics, 8 SR patterns (added Liveness, Bounded variance).
- `cage/cage.yaml` requires a parameter addition on the next bump (`v_warning`, `delta_t_max_fast`, `f_osc_max`, `t_osc_window`, `t_osc_persist`); deferred to a separate change.
- `cage/cage_node.py` acquires deferred F2 work: the end-of-cycle joint-envelope assertion logic and the inter-cycle oscillation monitor.
- The Training Specification (Phase 3, not yet written) acquires two reward-design constraints traceable from SR-009 (progress / anti-stall term) and SR-011 (heading-variance penalty).

`python tools/check_traceability.py --strict` → all checks PASS, 0 errors, 0 warnings, across 9 hazards / 11 SRs / 6 cage rules / 11 scenarios / 18 metrics.

---

## [14.05.2026] — Chapter 4 sync + traceability matrix update + decision renumbering

**Document(s) affected:** `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`, `docs/07_traceability_matrix.md`, `docs/DECISIONS.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Closing edit pass for the F1 audit findings of 14.05.2026 covering three coordinated changes:

*Chapter 4 sync to 9 hazards / 11 SRs.* Before this pass, Chapter 4 still described the F0 baseline of 7 hazards (H-01..H-07) and 8 SRs (SR-001..SR-008) while the canonical artefacts had already moved to 9 hazards and 11 SRs after the 13.05.2026 audit. The sync updates the compact tables in §4.4.3 (Hazard Register: add H-08 stall and H-09 cage rule conflict) and §4.6.3 (SRS: add SR-009 liveness, SR-010 composition consistency, SR-011 bounded-variance heading) including parameter columns; rewrites the coverage argument in §4.4.4 across the four-function eje plus the new meta-architectural eje for H-09; adds explicit out-of-STPA-scope rationale for H-08 (training-time pathology) and H-09 (composition hazard) in §4.5.1; expands §4.6.4's per-SR rationale synthesis to cover SR-009, SR-010 and SR-011; revises §4.7.2's relative-completeness argument from 7×8 to 9×11; expands the H↔SR matrix in §4.8.2 from 7×8 to 9×11 with the three new full-coverage cells (H-02↔SR-011, H-08↔SR-009, H-09↔SR-010); updates §4.10 synthesis to nine hazards and eleven SRs with explicit mention of the non-cage implementation types (training, arbiter). The pending-work appendix is updated to mark D12-D17 items as completed where the 13.05.2026 audit closed them.

*Traceability matrix human-readable update.* `docs/07_traceability_matrix.md` §"Matrix summary" extended from 8 to 11 rows: added H-02↔SR-011↔(C-06 + training)↔SC-EDGE-01/04↔M-P7, H-08↔SR-009↔training↔SC-NOM-01/02/03 + SC-PERT-03↔M-P6 + M-S2(monitoring), and H-09↔SR-010↔arbiter↔SC-EDGE-04/05↔M-S2 + M-I3. Row 1 (H-01↔SR-001) corrected to list only C-01 in the Cage Rule column (was incorrectly "C-01, C-03" — C-03 belongs to SR-003's row). Added explanatory paragraph below the table noting the three valid implementation kinds (numbered rule, `training`, `arbiter`) per D-25.

*Decision renumbering D-03..D-08 → D-26..D-31.* Chapter 4 was citing decisions D-03..D-08 with one set of meanings (HARA convention, STPA scope, SR-CL-A consequences, AI-hazard exclusion) while the DECISIONS.md index had since reassigned D-03..D-08 to a different set of decisions (OE1–OE7 mapping, SAE Level 2 scope, design science positioning, A1, A2). The chapter's internal decisions are now registered at D-26 (severity homothety convention), D-27 (selective STPA-light), D-28 (SR-CL-A requires deterministic cage rule), D-29 (SR-CL-A requires ≥25 runs), D-30 (SR-CL-A veto on global verdict) and D-31 (deliberate exclusion of non-functional AI-hazard families). Each new decision gets a full entry in DECISIONS.md following the project's ADR template (decision / alternatives / rationale / consequences). The chapter's in-text references at lines 339, 549, 763-764 and 1024 are updated to the new IDs; the decisions appendix at the end of Chapter 4 (lines 1197-1213) is rewritten to reflect the new numbering and to note that D-20..D-24 remain provisional placeholders for future cierres. Two stale "decision D-02 simulador Gazebo" references (lines 89 and 1174) are corrected to D-12 (the current Gazebo decision in DECISIONS.md).

The F1 audit of 14.05.2026 identified Chapter 4 as desynchronised with the canonical artefacts (described 7 hazards while the registers had 9), the traceability matrix summary as showing only 8 of 11 rows, and the Chapter 4 in-text decision references as colliding with the DECISIONS.md numbering. All three issues are now closed. The pre-existing measurement campaign M-1..M-5 (still pending execution) remains the principal blocker for Gate G1 sign-off; the present edit pass clears the documentation-side blockers identified in the audit.

Downstream: no cage logic, no scenario library, no SRS / Hazard Register canonical artefacts touched — the canonical sources of truth were already at 9H/11SR. The manuscript and the human-readable traceability matrix are now consistent with those sources. Chapter 5 (Cage Specification) referenced from §4.10 already documents the non-cage implementation types via D-25; no Chapter 5 edit follows from this sync.

`python tools/check_traceability.py` → all checks PASS, 0 warnings, 9 hazards / 11 SRs / 6 cage rules / 11 scenarios / 18 metrics.  
`pytest cage/tests/` → 13 passed (no cage logic affected).

---

## [14.05.2026] — F1 soft-blockers closure: typo Cap. 3, cross-checks Cap. 4, §4.10 transition

**Document(s) affected:** `manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Closing the soft-blocker items identified in the audit of 14.05.2026 — the work that does not depend on simulator/physical access nor on supervisor sign-off, and therefore can be done before the M-1..M-5 campaign runs.

*Chapter 3 typo fix.* §3.5.3 stated *"diez fases secuenciales (Fase 0 a Fase 9)"* — the project has seven phases (F0..F6), each with a gate G0..G6. Corrected to *"siete fases secuenciales (Fase 0 a Fase 6), … con un gate de revisión (G0 a G6) al cierre"*. This aligns with the appendix figure 7 (project_phases) which already shows F0..F6 with gates G0..G6, with Cap. 3 §3.5.4 (which already names F1 as the upper-left branch of the V), and with the `docs/.phases/Fase 0..6/` directory structure.

*Chapter 4 D18 cross-checks.* Two checklist items closed:

- **§3.7 meta-criteria vs §4.4–§4.8.** The five meta-criteria of §3.7.1 evaluated retrospectively at Cap. 11 are: (1) integrity of traceability — instantiated by the bidirectional matrix of §4.8 and validated continuously by `check_traceability.py`; (2) SR coverage by experimental evidence — set up by §4.7.1's SR-CL-A verification rules and D-30's veto on global verdict; (3) hazard-anticipation degree — set up by §4.4.4's three-axis coverage argument; (4) adoption cost and (5) matrix productivity — meta-evaluative, recorded in `DECISIONS.md`, do not need direct reflection in Cap. 4. An explicit cross-reference paragraph was added at the end of §4.7.1 anchoring meta-criteria 1, 2, 3 to their Cap. 4 antecedents.

- **A1–A5 coherence vs §3.4.** Before the pass, only A3 and A4 were cited by name in Cap. 4 (lines 104, 875, 888). A1, A2, A5 were instantiated implicitly via D-25's three-way implementation taxonomy, the "Verificación" column linking to scenarios, and the bounded ODD respectively. Explicit citations now added: A1 in §4.6.3 (paragraph after the SRS table, connecting D-25 with the Cage Spec / Training Spec split of §3.4.1); A2 in §4.6.3 (connecting the ≥25-runs convention of D-29 with the L4b' policy-behavioral-evaluation split of §3.4.2); A5 in §4.3.1 (connecting the bounded ODD + ODD-PHYS-1 sim-to-real gap deferral with §3.4.5). No contradictions detected between §4.5/§4.6 and §3.4.

*Chapter 4 D19-D20 transition refinement.* §4.10 closed with an explicit paragraph anchoring the chapter's completion to the formal F1 closure ritual: Gate G1 with supervisor sign-off, the two cuantitativos pre-requisites (M-1..M-5 campaign and ODD-Spec TBD-Q1..Q12 closure), the bump of `cage/cage.yaml` to 0.3.0, and the *post-G1* state that Cap. 5 assumes when picking up at the L3/L4a levels.

*Chapter 4 internal checklist.* The appendix at the end of Cap. 4 (lines 1116-1175) is updated: D18 items marked `[x]` with the cross-check summary; D19-D20 `[x]` on the §4.10 closure; the figure-insertion and prose-polish items relabelled `[PULIDO FASE 6]` to make their deferral explicit.

The audit of 14.05.2026 identified these four items as actionable now (no external dependencies). The remaining F1 blockers are the M-1..M-5 measurement campaign, the ODD-Spec TBDs against the simulator's `.world` / `.material` files, the Gate G1 presentation material, and the supervisor session itself.

Downstream: no canonical artefacts (Hazard Register, SRS, cage.yaml, traceability matrix, DECISIONS.md) are touched by this pass — only the manuscript chapters and the CHANGELOG. `check_traceability.py` and `pytest cage/tests/` continue to pass unchanged.

`python tools/check_traceability.py` → all checks PASS, 0 warnings.  
`pytest cage/tests/` → 13 passed.

---

## [14.05.2026] — ROS2 workspace integration under `src/` (cobraflex + cobraflex_rl)

**Document(s) affected:** root structure (new `src/` directory), `.gitignore`, `pytest.ini` (new), `docs/DECISIONS.md`.  
**Phase:** F1.  
**Gate context:** before G1 (infrastructure prerequisite for closing ODD-Spec TBDs).  
**Author:** Samuel Sanchez.

Integrated the ROS2 packages of the author's prior simulator + physical-platform stack into this repository under the canonical colcon workspace layout. Tracked packages:

- **`src/cobraflex`** — URDF/SDF of the CobraFlex 1:14 platform, Gazebo worlds (`empty.world`, `obstacles.world`, `test_world.sdf`), launch files, perception/control nodes, configs, rviz layouts, mesh visualisations.
- **`src/cobraflex_rl`** — RL training infrastructure, gymnasium-Gazebo-ROS2 interface, launch files for training campaigns.

Source: `E:\CAST\Cobra Flex Drivers & SW\src` at the working-tree snapshot of 14.05.2026. The fresh-copy integration mode is registered as decision D-32. Files filtered out during the copy: `.vscode/`, `.pytest_cache/`, `__pycache__/`, `build/`, `install/`, `log/`, `*.egg-info/`, `*.pyc`. Total: 65 files (51 in cobraflex, 14 in cobraflex_rl), 110 MB total of which 87 MB is the lidar visualisation mesh `rplidar-a2m4-r1.stl`.

Third-party drivers **deferred** (not brought into this repo): `sllidar_ros2` (Slamtec, https://github.com/Slamtec/sllidar_ros2.git, HEAD 3430009) and `zed-ros2-wrapper` (Stereolabs, https://github.com/stereolabs/zed-ros2-wrapper.git, HEAD 0719912). The decision on whether to add these as git submodules or to install them via `rosdep` is left for a later session once the actual physical-platform experiments are scoped.

*Tooling adjustments.*

- `.gitignore` extended with per-package ROS2 build patterns (`src/*/build/`, `src/*/install/`, `src/*/log/`) and with the generated rosidl bindings glob (`src/*/msg/_*.py`, `src/*/srv/_*.py`, `src/*/action/_*.py`).
- `pytest.ini` added at the repo root to constrain `pytest` auto-discovery to `cage/tests`. Without this, running `pytest` from the root would attempt to collect the ament_python tests under `src/cobraflex/test/` (`test_copyright.py`, `test_flake8.py`, `test_pep257.py`) and fail with `ModuleNotFoundError: No module named 'ament_pep257'` because the ament test infrastructure is not part of the safety-side dev environment. The ROS2 tests inside `src/` continue to run via `colcon test` from a ROS2 environment, as intended.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings (no traceability artefacts touched).
- `python -m pytest` (from root, after `pytest.ini`) → 13 passed; only `cage/tests/` discovered.
- `python -m pytest cage/tests/` → 13 passed (explicit invocation also works).
- `python tools/apply_calibration.py` → exit 0, "not_executed" × 5 (unchanged).
- No internal `.git`/`build`/`install`/`log`/`__pycache__`/`.pytest_cache` directories under `src/` after the copy (verified by `find`).

*Open follow-ups.*

- Decide whether `src/cobraflex/meshes/rplidar-a2m4-r1.stl` (87 MB) stays in git or moves to Git LFS / external download. Acceptable for now but worth revisiting before any externally-published version of the repo.
- Decide submodule vs. rosdep for `sllidar_ros2` and `zed-ros2-wrapper` once physical-platform scope is fixed.
- Update README with the `colcon build` workflow when the supervisor needs the buildable-from-clone path documented (deferred to F2 entry — Phase 2 starts working against the cage_node inside the ROS2 graph).
- Reconcile Cap. 3 §3.6.1's reference to "Gazebo" with the actual simulator declared in `src/cobraflex/worlds/` (Gazebo .world / .sdf) and in the ODD-Spec (which currently says "MuJoCo material spec" — this label may need correction during the ODD-Spec TBD closure).

---

## [14.05.2026] — Post-integration follow-ups: heavy mesh, MuJoCo→Gazebo, README build instructions

**Document(s) affected:** `.gitignore`, `docs/08_odd_specification.md`, `experiments/odd_inspection/odd_tbds.yaml`, `experiments/odd_inspection/README.md`, `README.md`, new `scripts/download_meshes.sh`, new `src/cobraflex/meshes/README.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Three coordinated follow-ups closing the gaps identified at the end of the `src/` integration entry above.

*Follow-up 1 — Heavy mesh `rplidar-a2m4-r1.stl` (87 MB) untracked.* The Slamtec RPLidar A2 visualisation mesh is the single biggest file in the repository at 87 MB out of the 110 MB total of `src/cobraflex/`. The file is upstream-distributed by Slamtec, does not change with the thesis work, and exceeds the 50 MB soft-limit that GitHub flags. Action taken:

- `git rm --cached src/cobraflex/meshes/rplidar-a2m4-r1.stl` to stop tracking; the file remains on the working tree for the local build and continues to be referenced by the URDF.
- `.gitignore` extended with `src/cobraflex/meshes/rplidar-a2m4-r1.stl`.
- `scripts/download_meshes.sh` created as the canonical mechanism for fetching the mesh on a fresh clone. The current implementation is a stub that prints clear manual-acquisition instructions because the Slamtec CAD URLs are not publicly stable; when a stable mirror is decided (a thesis-controlled release artefact, an S3 bucket, etc.), the URL slot in the script is filled in and `curl` does the rest. The script is idempotent and skips files already present at expected size.
- `src/cobraflex/meshes/README.md` documents which meshes are tracked (the three CobraFlex CAD parts at ~23 MB total + the 78 KB ZED Mini reference) and which are externally-obtained (the RPLidar mesh), with explicit instructions and rationale.

The mesh is still in the repository's git history at commit 029ad28 ("F1: added ROS src folders for cobraflex and cobraflex_rl"). Removing it from history requires `git filter-repo` or equivalent and is a destructive operation deferred until publication, when the repository will be reviewed for size and external-distribution cleanliness in one pass.

*Follow-up 2 — Simulator label "MuJoCo" → "Gazebo".* The Phase 0 ODD-Spec was drafted before the simulator choice was finalised and referred to "MuJoCo material specification" / "MuJoCo map files" / "MuJoCo map geometry" / "MuJoCo `<geom>`". The actual simulator now packaged in `src/cobraflex/worlds/` is Gazebo (`.world` / `.sdf` files with the SDFormat `<surface><friction>` block), consistent with decision D-12 (§3.6.1 of Chapter 3). The label "MuJoCo" is replaced throughout the ODD-Spec body (§4.1, §4.2, §9 master parameter table, §11 TBD-Q1 row), in the YAML template `experiments/odd_inspection/odd_tbds.yaml` (inline examples), and in the README of `experiments/odd_inspection/` (workflow + Sources-by-TBD-group table). The TBD parameter values themselves are unchanged — only the *source* annotations are corrected. `grep -rn "MuJoCo" docs/ experiments/odd_inspection/` returns zero matches post-edit.

*Follow-up 3 — Repository README updated with ROS2 build instructions.* The top-level `README.md` previously had no mention of the `src/` workspace. Added: a row for `src/` and `scripts/` in the Repository Structure table; a new "ROS2 Workspace (`src/`)" section between "Identifier Conventions" and "Reproducibility" with:

- Package roster (cobraflex, cobraflex_rl) with a brief role description per package.
- Prerequisites (Ubuntu 22.04, ROS2 Humble, gazebo-ros-pkgs, colcon, rosdep).
- One-time setup commands (`rosdep install --from-paths src --ignore-src -r -y` and `./scripts/download_meshes.sh`).
- Build commands (`source /opt/ros/humble/setup.bash && colcon build --symlink-install && source install/setup.bash`).
- Launch examples for bringup, training, and the M-2 calibration logger.
- A note on the deferred third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) referencing decision D-32.

The intention is that an evaluator following the README from "Repository Structure" to "ROS2 Workspace" can clone, build, and run a launch file in one sequence, without re-reading the full Chapter 6 of the manuscript.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings.
- `python -m pytest` (from root) → 13 passed; only `cage/tests/` discovered.
- `python tools/apply_calibration.py` → exit 0, 5 × not_executed (unchanged).
- `python tools/close_odd_tbds.py` → exit 2, "nothing to do" (unchanged, YAML still null).
- `./scripts/download_meshes.sh` on a host that already has the file → `✓ rplidar-a2m4-r1.stl already present (91076984 bytes)`. The idempotent branch works.
- `grep -rn "MuJoCo" docs/ experiments/odd_inspection/ src/cobraflex/meshes/README.md` → no matches.

---

## [14.05.2026] — ODD-Spec TBD closure (3 of 12 at F1; remaining 9 deferred per phase)

**Document(s) affected:** `docs/08_odd_specification.md` (bumped 0.1 → 0.2), `experiments/odd_inspection/odd_tbds.yaml`, `docs/DECISIONS.md` (new D-33).  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Phase 1 partial closure of the ODD-Spec TBDs against the actual `src/cobraflex` and `src/cobraflex_rl` workspace integrated in the preceding commit. Three TBDs resolved by inspection of the simulator files; the remaining nine are explicitly deferred to later phases per decision D-33.

*Resolved at F1.*

- **TBD-Q1 FRICTION = 1.0**. All three world files under `src/cobraflex/worlds/` (`empty.world`, `obstacles.world`, `test_world.sdf`) use the empty Gazebo SDF block `<surface><friction><ode/></friction></surface>`. Gazebo ODE defaults `mu1 = mu2 = 1.0` when no explicit `<mu>`/`<mu2>` is specified, so the effective surface friction on the simulated road is 1.0. Documented as such in the YAML `source` field with a note flagging that the value comes from a Gazebo default rather than an explicit declaration.
- **TBD-Q2 A_LAT_MAX (ODD-1) = 9.81 m/s²**. Derived: `μ · g = 1.0 × 9.81`. This is the Coulomb no-skid ceiling on the lateral acceleration the policy can command without losing traction; the actually-commanded a_lat in ODD-1 is much smaller because curvature is zero and the bicycle-model steering geometry dominates.
- **TBD-Q3 CORRIDOR_EDGE = 0.1225 m**. From `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` line 93: `terminated = abs(track_state.ey) > (self.lane_width * 0.5)` with `lane_width = 0.245 m` from `src/cobraflex_rl/config/centerline.yaml`. Therefore `CORRIDOR_EDGE = LANE_WIDTH / 2 = 0.1225 m`, which equals `LANE_EDGE`; the ODD-Spec note "if the two differ, document the rationale" resolves to "they do not differ".

*Deferred per phase.* Q4–Q7 and Q12 (ODD-2 / ODD-4 stressor profiles) deferred to F4 because the scenario YAMLs do not yet exist under `src/cobraflex_rl/config/` — they will be specified jointly with the Scenario Library construction. Q8–Q11 deferred to F2 / F3 because the `odd3_curvy_loop` Gazebo world is not yet implemented (only `empty.world`, `obstacles.world`, `test_world.sdf` exist, and the current `centerline.yaml` is a 3 m straight). The deferral is registered as decision D-33 in `docs/DECISIONS.md` with a per-TBD rationale and target phase.

*Tooling executed.* `python tools/close_odd_tbds.py --apply` substituted `TBD-Q1 → 1.0`, `TBD-Q2 → 9.81`, `TBD-Q3 → 0.1225` in the body of the ODD-Spec (§4.2, §4.5, §4.8, §4.9 prose; §9 master parameter table; §11 resolution rows) and left a `.bak` of the pre-edit document next to the original. The remaining `TBD-Q4..Q12` literals stay in the document as designed; re-running the script after later closures is idempotent.

*Versioning.* The ODD-Spec moves from v0.1 (Phase 0 draft) to v0.2 (F1 partial closure). The cover-block status changes from *"DRAFT — contains TBD values that must be filled before Gate 1"* to *"DRAFT — 3 of 12 TBDs resolved at F1 (Q1, Q2, Q3); remaining 9 explicitly deferred per phase (Q4–Q7, Q12 to F4; Q8–Q11 to F2/F3) — see decision D-33"*. The §0.1 change-log row for v0.2 records the substantive change.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings (no traceability artefacts touched; the ODD-Spec is not part of the traceability graph as a node, only as an upstream parameter source cited from the SRS).
- `python -m pytest` → 13 passed.
- `grep -n "TBD-Q[123]\b" docs/08_odd_specification.md` → only matches inside the §0.1 change log row and the §11 resolution rows; zero remaining TBD-Q1/Q2/Q3 literals in the body. Q4–Q12 still present with their original counts.
- ODD-Spec v0.2 file size: 28.4 KB (up from 27.2 KB v0.1, due to the resolution-column text in §11).

*Open items propagated.*

- M-4 (speed-vs-curvature, `apply_calibration.py` decision rule for SR-004) inherits the Q8/Q9 deferral: it cannot run at F1 because `odd3_curvy_loop` is not yet built. M-4 re-scheduled together with ODD-3 closure at F2/F3 entry.
- The Phase 1 closure criterion of `experiments/odd_inspection/README.md` is now satisfied: every TBD is either *resolved* (Q1, Q2, Q3) or *explicitly deferred via a registered decision* (Q4–Q12 via D-33).

---
<!-- Subsequent entries appended below -->
