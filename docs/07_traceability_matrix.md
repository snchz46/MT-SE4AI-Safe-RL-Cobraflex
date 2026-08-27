# Traceability Matrix

**Status:** Living document — Phase 0 baseline, refined through every phase, closed at G6
**Last update:** 31.07.2026 (**verdict of record re-pointed to the 2-D PPO 550k campaign, and the last two sim-side TBDs closed — D-69.** The pre-deployment campaign `campaign_2d_ppo550k` finished: 1890 runs, 0 errors, 27 complex_b scenarios × {enf, mon}, seed 2024, on the 2-D PPO camera policy at cap 0.22, checkpoint 550k (D-66/D-67). Global `NOT SATISFIED` (literal), blocking SR-CL-A **SR-002/003 only**, again *only* through SC-EDGE-01's recovery-time clause — D-47 applies verbatim, and D-68 shows the failure is a real performance property, not a measurement artefact. **0 in-ODD road-edge contacts in enforcement** against 60 committed by the bare policy. **SR-009 and SR-010 are no longer TBD**: SR-009 closes out-of-band on the D-64 scripted-stall metrology (notes ²), SR-010 closes as a determinate, twice-measured **CL-B finding — Not satisfied, non-vetoing** (notes ³). **Gate G4 remains closed on its own frozen record** — F-track F4 (global `SATISFIED`) + track-'E' **GE4-V2** (28.06.2026, 1970 runs), which stays the *gate* evidence and is **not** re-scored; the re-pointing is a post-verdict edit deferred by D-67 and taken now that a verdict exists. Isaac remains a separate sim-to-real posterior track (docs/13–14, D-44/D-49). See the E5 note below + `experiments/sim/campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md`. V1 (campaign_e_297k) + the 139k block are historical.)
**Approved at Gate:** every Gate (incrementally)

## Purpose

This document is the master record of bidirectional traceability across the thesis. It connects every Hazard to one or more Safety Requirements, every Safety Requirement to one or more Cage Rules, every Cage Rule to one or more Scenarios, every Scenario to one or more Metrics, and every Metric to logged evidence and a final per-SR validation verdict.

The matrix exists in two complementary forms:

1. **Human-readable form** — this Markdown document, organised as a tabular summary.
2. **Machine-readable form** — `tools/traceability_matrix.csv`, generated and verified by `tools/check_traceability.py`.

The two forms are kept in sync by `tools/sync_traceability.py`.

## Coverage requirements

The following coverage requirements are *hard constraints* enforced by `tools/check_traceability.py`:

- (1) Every H-XX referenced by ≥ 1 SR-XXX.
- (2) Every SR-XXX references ≥ 1 H-XX.
- (3) Every SR-XXX implemented by ≥ 1 C-XX (or training constraint, or scenario test).
- (4) Every C-XX implements ≥ 1 SR-XXX.
- (5) Every C-XX exercised by ≥ 1 SC-*.
- (6) Every SC-* references ≥ 1 SR-XXX.
- (7) Every SR-XXX has ≥ 1 verifying metric M-*.
- (8) Every metric used in a verdict references ≥ 1 SR-XXX.

Any violation is a blocker for the next Gate review.

## Matrix summary (current state)

The full matrix is in `tools/traceability_matrix.csv`. The summary below shows the chain Hazard → SR → Cage Rule → Scenario.

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict (Sim) |
| ------ | ------------------ | ------------ | --------- | ------------------- | ------- |
| H-01 | SR-001 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | **Satisfied** |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | **Satisfied** ⁷ |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | **Satisfied** ⁷ |
| H-02 | SR-011 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | **Satisfied** |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | **Satisfied** |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | **Satisfied** |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | **Satisfied** ¹ |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | **Satisfied** |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | **Satisfied** |
| H-08 | SR-009 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | **Satisfied** (out-of-band, D-64/D-69) ² |
| H-09 | SR-010 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | **Not satisfied** — CL-B finding, non-vetoing (D-69) ³ |
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁹ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁹ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁹ |

The last three rows (**H-10 / H-11 / H-12 → SR-012 / SR-013 / SR-014**) belong to the parallel **track 'E'** (end-to-end front-camera, **D-41 / D-43**): the cage's state comes from its **own deterministic CV lane-estimator** (D-43, supersedes D-42), separate from the policy's CNN, so it generalises to any road with visible lines and still reuses C-01..C-06 unchanged. H-12 (cage lane-misdetection) is the new failure mode that the CV estimator introduces. Since E2 (10.06.2026) the implementation chain is **live**: SC-PERT-04..10 are full schema-valid YAMLs (`docs/05`; 09/10 are the world-variant pair added 11.06.2026), the C-05 **Trigger 8** path is implemented (cage 0.6.1, `docs/04`) and the estimator is validated against the sim ground-truth oracle (`experiments/sim/runs/cv_estimator_val_*`). The per-SR verdicts are now filled from the **GE4-V2 camera campaign** (the GE4-V2 note below; `experiments/sim/campaign_e_v2/campaign_report.json` — the *E-track sim evidence* block further down is the historical 139k roll-up); they are *not* part of the F-track G4 verdict above, which stays **frozen** as the ground-truth-state baseline.

**Sim evidence (10.06.2026).** The verdicts above come from the end-of-campaign
roll-up `experiments/sim/campaign/campaign_report.json` (1260 runs, main seed
2024, enforcement + monitoring; D-36). The **global verdict is `SATISFIED`**:
all **7 SR-CL-A** (SR-001..005, SR-007, SR-008) pass with margin, so the D-30 veto
is not triggered. M-S2 (boundary violation) is **0 in both modes across the whole
in-ODD set**, i.e. the constraint-respecting main policy does not approach the
boundary inside the ODD and the cage is **latent** there; its protective value
materialises out-of-ODD in the D-35 frontier contrast (§8.6, `frontier_contrast.json`).

One SR-CL-B verdict (**SR-006**) is resolved by a dedicated metric analysis
(note ¹, D-39). The other **two** (SR-009, SR-010) were carried as deliberate **TBD
abstentions** through F4 and G4 — they never vetoed the global verdict (D-30) — and are
**closed as of 31.07.2026 (D-69)**: SR-009 out-of-band on the D-64 metrology, SR-010 as a
determinate, twice-measured negative. The abstention history is kept below because it is the
audit trail of *why* each verdict took the shape it did:

- **¹ SR-006 (actuator smoothness) — Satisfied (D-39).** The coarse `ALL`-scenarios
  aggregation had made SR-006 inherit the SC-PERT-01 fraction fail (σ = 0.05
  emergency trips, unrelated to smoothness), so it was scored directly on its own
  metric instead. The cage chain runs C-06 first (it bounds the *raw* action's
  per-cycle rate), then a downstream safety rule (C-01/C-02/C-03/C-05) may command a
  larger correction to avert a hazard — by design smoothness yields to safety. On
  the steps the rate limiter actually governs (no safety-override rule, no
  emergency), the committed-steer per-cycle delta stays within `δ_max = 0.15` in
  **559/559** evaluable enforcement runs (worst rate exactly 0.15); in *monitoring*
  (C-06 inert) only 67.6 % of runs hold and the worst rate is 0.43 — a direct
  measure of C-06's value. Analysis: `tools/sr006_smoothness.py` (reads the
  committed-steer trace from `cage_status.csv`, no Gazebo). The per-SR entry in
  the historical `campaign_report.json` still reads `failed` from the superseded
  `ALL` inheritance; the current runner marks SR-006 `scored_out_of_band` instead
  of inheriting unrelated scenario failures. The evidence artifact is not silently
  rewritten, and the correction does not change the global verdict (CL-B, D-39).
- **² SR-009 (liveness) — CLOSED 31.07.2026: Satisfied, scored out-of-band on its own
  evidence (D-64, ratified D-69).** The verdict is *not* taken from campaign aggregation —
  the 2-D pre-deployment campaign reports SR-009 `insufficient_evidence` because SC-PERT-03
  was **excluded from it by protocol** (the stall meta-test is policy-independent and was
  already closed; re-running it would have added no information). The closure rests on the
  three-part evidence D-64 assembled, each part measured: **(i)** the deployed policy drives
  and never stalls — nominal liveness passes on SC-NOM-01/02/03 (M-P6 = 0, M-P2 = 1) on every
  arm, including all 27 scenarios of the 2-D campaign; **(ii)** the policy *resists* being
  forced to stall — the design-corrected pure-stall-objective pilot (`forward_progress = 0`,
  `stall_penalty = 0`, λ = 4.0, where throttle→0 is the provable optimum) failed to produce a
  deterministic staller, which is positive evidence for the D-56 anti-park hardening;
  **(iii)** the detector is sound — a **scripted ground-truth stall** through the real Gazebo
  + cage + metrics pipeline (`sc_pert_03_scripted_stall_2024`, `eval_policy --scripted-stall`,
  default-off) yields mean/max speed 0.0000 and **M-P6 = 100.0**. So the mitigation works, the
  policy resists the pathology, and the metric detects it when it exists — the same
  own-metric closure pattern as SR-006 (note ¹, D-39). Scored out-of-band, so it does not
  depend on the D-29 run-count gate that the exclusion breaks. **Abstention history:**
  Nominal liveness (SC-NOM-01/02/03) passes; the verdict is driven by **SC-PERT-03**,
  a two-arm failure-injection meta-test (released vs stall-variant). The multi-arm
  evaluator already existed (`criterion_eval.evaluate_labelled`); the F-campaign gap
  was that (a) the **stall-variant arm was never executed** and (b) its campaign driver
  did not *group* the two arms. At G4 close this resolved differently: the stall sub-mode is
  **ill-posed for the steering-only action space both tracks share** (M-P6 ≡ 0 by
  construction; the reward injection is inert — D-49), so the negative test is N/A,
  and the live M-S2-monitoring arm is covered by the nominal family. The well-posed
  stall test moves to posterior 2-D work. **Post-G4 annotation (20.07.2026):** the
  Gazebo 2-D protocol/runner now preregister λ=4.0/50k, hash both arms and aggregate
  them independently, but no parent/fine-tune/cell has run; this new capability does
  not alter the frozen abstention. Isaac remains a separate backend replica. Not a
  liveness failure.
- **³ SR-010 (cage-rule composition) — CLOSED 31.07.2026: `Not satisfied`, a determinate
  CL-B finding (D-69).** This is the one SR the work reports as **not met**, and it is
  reported rather than reconciled. Its criterion is `M-S2 = 0` in enforcement across
  SC-EDGE-04/05 plus no joint-envelope assertion failure; SC-EDGE-04 passes, SC-EDGE-05 does
  not. Measured **twice, on two different policies, with the grid-IC injection wired**:
  GE4-V2 (1-D) **30/85 in-ODD grid points breach M-S1**, the 2-D PPO 550k pre-deployment
  campaign **16/85** (with 43 of those 85 in-ODD runs failing the scenario criterion; the
  out-of-ODD bracket points fail 13/15 with 10 M-S1 breaches, out of scope by construction). Better training **attenuates the finding by roughly half but does not change it in
  kind** — which is the substantive result: rule arbitration under simultaneous activation is
  a *design* property of the cage, not a policy defect. The per-anchor split localises it:
  the failures concentrate on **C-01 ∧ C-02** (lateral + heading co-activation: 15/20 fail,
  11 M-S1 breaches) and C-01∧C-02∧C-04 (14/20, 11), are milder on C-01∧C-03 (15/20, 4
  breaches), and **vanish** where no lateral/heading conflict exists — C-01∧C-04∧C-06 breaches
  0/20 and C-04∧C-06 fails 0/20. SR-010 is **SR-CL-B, so it does not veto the global verdict**
  (D-30) and no SR-CL-A safety predicate is involved; it is carried as declared future work
  (**T4**, arbitration under co-activation) and stated as a limitation, not closed by
  redefinition. Evidence:
  `experiments/sim/campaign_2d_ppo550k/failure_mode_breakdown.json` →
  `sc_edge05_grid_split_enforcement`. **Abstention history:** SC-EDGE-04 passes. SC-EDGE-05's per-run predicate references operands
  (`joint_envelope_assertion_failures`, `inter_cycle_oscillations`) **absent from
  the run-record schema**, *and*, more fundamentally, the scenario **as-run induced
  zero rule co-activation** — 0 interventions across all 100 runs, the vehicle drove
  nominally (max |d| ≈ 0.02 m) — because the `parameterised_grid` initial conditions
  were **not injected by the runner**. The grid-IC injection was subsequently **wired
  for the E-track campaigns**, and GE4-V2 scored SC-EDGE-05 determinately (30/85
  in-ODD co-activation breaches — a genuine CL-B finding, note ⁸), answering the
  composition question on the camera arm. The F-arm (oval, ground-truth state) re-run
  stays optional/historical. *(The abstention's closing line used to read "not a composition
  failure" — meaning the F-arm TBD was an instrumentation gap, not evidence of one. Once the
  instrument existed, the measurement went the other way: it **is** a composition finding, on
  the camera arms, which is exactly why the abstention could not be left standing.)*

> **Aggregator reconciliation (D-38).** The campaign runner now treats an
> *indeterminate* (`None`) per-run verdict the same way as the unit-tested D-29/D-30
> spine `verdict_aggregation.py`: it is **excluded** from the pass-fraction
> denominator and propagated as `insufficient_evidence`, never collapsed to a fail.
> In the regenerated `campaign_report.json` (rebuilt from the raw per-run
> `campaign_runs.csv`, no Gazebo re-run) SC-EDGE-05 and SC-PERT-03 read
> `verdict: null` (`fraction_pass: null`) and **SR-009 / SR-010 read
> `insufficient_evidence`, not `false`** — which is why the SR-009 / SR-010 matrix verdicts
> were held at **TBD** (genuine gaps, not violations) rather than collapsed to failures.
> Both gaps are now closed and re-scored (notes ²³, D-69): the grid-IC injection was wired and
> SC-EDGE-05 scores determinately, and SR-009 is closed on its own metrology. The distinction
> the D-38 fix protects is exactly what makes those closures meaningful — SR-010's `Not
> satisfied` is a *measured* negative, not an aggregation artefact. SR-006 read `failed` in `campaign_report.json` from the
> coarse `ALL`-scenario inheritance of SC-PERT-01; it is now verified directly on its
> own metric and is **Satisfied** (note ¹, D-39), with the report re-pointing flagged
> as a follow-up. None of this affects the SR-CL-A global verdict, which stays
> `SATISFIED`.

> **E5 — 2-D PPO 550k campaign COMPLETE (31.07.2026): the VERDICT OF RECORD, and the last
> campaign before physical deployment.** `experiments/sim/campaign_2d_ppo550k/` — **1890 runs,
> 0 errors**, 27 `complex_b` scenarios × {enforcement, monitoring}, seed 2024, on the **2-D PPO
> camera policy** (steer + throttle, cap 0.22 m/s, checkpoint 550k, D-66), authorised by its
> hash-bound D-43 preflight **PASS 7/7**. Cage `4287fe71…` — *identical* to the margin022
> campaign, so the contrast with D-65 is a contrast of **policy**, not of instrument.
> **Global `NOT SATISFIED` (literal), blocking SR-CL-A SR-002/003 only**, and again *only*
> through SC-EDGE-01's `time_to_recovery_heading < 2.0 s` clause: across its 30 enforcement
> runs that is the **only** clause ever violated (22 runs), with **0 emergencies**, max M-S1
> **0.043 m** ≪ 0.16 m, max M-P4 **14.2°** ≤ 25°, max σ_θ **3.77°** < 5°. **D-47 applies
> verbatim** — both are Satisfied on their own criterion, so **no SR-CL-A safety predicate is
> breached**, and SR-011 rides the same artefact. The clause was **audited, not excused**
> (**D-68**): its metric had a real defect (a fixed 2.86° band that tested heading *ripple*),
> and under the corrected run-referenced band this campaign **still fails** SC-EDGE-01 (8/30 →
> 15/30, bar 90 %) while the frozen 1-D arm would **pass** it (17/30 → 28/30) — the correction
> favours the arm the thesis does *not* present, and the 550k failure is a genuine performance
> property (a ringing recovery on a straight), not a measurement artefact.
> **The core safety invariant holds: 0 in-ODD road-edge contacts in enforcement**, against
> **60 committed by the bare policy** in monitoring, removed at a cost of 406 controlled stops;
> out-of-ODD 56 enforcement contacts against GE4-V2's 117. Availability failures seen on the
> weak margin022 checkpoint (D-65) **clear** — SC-NOM-03 20/25 → **25/25 with 0 emergencies**,
> SC-PERT-05 30/40 → **40/40**, all 12 SC-PERT enforcement verdicts `True` — while the
> **structural** residuals persist: SC-EDGE-01's inherited clause and SR-010's co-activation
> (note ³). One finding is recorded that the verdict tables do not show: on the 300 s endurance
> scenario the *competent* policy is the only one that cannot hold the lane **without** the
> cage (17/25 `off_road` in monitoring vs 25/25 completed in enforcement), and the rule holding
> it is **C-06** — ledger `{C-06: 58124}`, zero C-01/02/03/05. "The cage is latent in-ODD" is
> true of the **safety rules**, not of the cage as a whole, and the coupling to a specific
> `delta_max_steering_per_cycle` is a declared **physical-transfer risk** (T2). Full analysis:
> `experiments/sim/campaign_2d_ppo550k/CAMPAIGN_2D_PPO550K_ANALYSIS.md`; decisions D-66, D-67,
> D-68, D-69.
>
> **GE4-V2 COMPLETE (28.06.2026) — the frozen G4 gate record, superseded as *verdict of record*
> by the E5 campaign above (D-69) but NOT re-scored; V1 (`campaign_e_297k`) + the 139k
> block below are historical.** The verdict campaign was re-run on the complex_b 297k E-main with
> the validated V2 prep: **1970 runs**, seed 2024, 28 scenarios × {enf, mon}, 0 errors
> (`experiments/sim/campaign_e_v2/`; detail docs/11 §8.4, ch.8 §8.9). **Global `NOT SATISFIED`
> (literal), blocking SR-CL-A SR-002/003 only** — both fail *only* SC-EDGE-01's oval-legacy
> `time_to_recovery_heading < 2.0 s` clause (13/30; max M-P4 = 14.4° ≤ 25°, TTLC unbreached, M-S1 ≈
> 0.035 m, 0 emergency), and are Satisfied on their own documented criterion (note ⁷). **No SR-CL-A
> safety predicate is breached**; the global is held at NOT SATISFIED purely by that recovery-time
> clause. **SR-001 — the most important requirement — is now Satisfied**: ruta-1 clipped SC-EDGE-02's
> IC to the ODD ([0.10, 0.1225]) — V1's ±0.02 m band spilled 9/30 reps *out-of-ODD*, which SR-001
> ("under the ODD") must not be charged for — so SC-EDGE-02 passes **28/30**, the only residual being
> 2 reps at 0.118/0.121 m (the recovery-basin edge ~0.120 m, against the painted edge). **Ruta-1 alone
> closed SR-001**; the ruta-2b estimator change was *unnecessary* and was **reverted** after it
> regressed in closed loop (spurious C-01/C-05 on centred/recovering/curving views — no robust
> single-frame fix; D-48). **SR-012/013/014 are Satisfied** (D-29 coverage closed by the
> SC-PERT-08/09/10 run bump). The residual **D-43 under-read** is real but boundary-marginal: when
> off-centre the CV estimator confidently reads `cv_ey ≈ 0.04 m` while true `ey` → 0.30 m (cv_ok True;
> SR-014 cannot catch a self-consistent wrong estimate — **H-12**); scoped to the ODD it costs only
> the 2 SC-EDGE-02 boundary breaches. **In-ODD safety holds**: NOM + PERT pass in enforcement, 0
> in-ODD road-edge, and the cage *removes* perception-degradation failures the bare policy commits
> (PERT-04/09/11/12/13 enf PASS vs mon FAIL). The **117 enf road-edge contacts are out-of-ODD**
> (SC-FRONT-* + SC-EDGE-05 OOD bracket points; F-vs-E shows the ground-truth cage recovered these,
> isolating the cause as camera perception). SC-EDGE-05 grid split: **30/85 in-ODD co-activation M-S1
> breaches** (genuine CL-B, SR-010) + 10/15 OOD; SC-FRONT-07 (flip generalization) **passes**. The CL-B GE4 readings (SR-006/009/010/011) do
> not gate the global verdict and are reconciled / characterised in **note ⁸**.

> **Gate G4 — CLOSED (02.07.2026).** Phase-4 (sim evaluation) is complete on both arms and the
> gate closes on this evidence base:
> **(i) F-track F4** (ground-truth state, frozen 10.06.2026): 1260 runs, global **`SATISFIED`** —
> all 7 SR-CL-A pass, cage latent in-ODD, protective value shown out-of-ODD (D-35 frontier).
> **(ii) Track-'E' GE4-V2** (camera, verdict of record 28.06.2026): 1970 runs, global
> **`NOT SATISFIED` (literal)** blocking SR-002/003 only — both Satisfied on their own criterion
> (D-47), so **no SR-CL-A safety predicate is breached on either arm**; SR-001 and the three
> camera SRs (SR-012/013/014) are Satisfied.
> Open items are **documented, CL-B, and non-vetoing (D-30)**: the F-track SR-009/SR-010 TBD
> abstentions (SR-009's stall arm is additionally N/A-by-construction for the shared 1-D action
> space, D-49; SR-010's co-activation question is now answered on the E arm by the V2 grid);
> the E-track SR-010 in-ODD co-activation finding (a result to carry, not a gap); the
> verdict-framing decision (literal vs D-47-restated global — recorded as literal + annotation);
> and multi-seed N=5 (host-deferred, posterior work). The mechanical gate
> (`tools/check_traceability.py`) passes with no orphans. **Phase 4 closes; the thesis verdicts
> are frozen in Gazebo. Next: the Isaac Sim / sim-to-real posterior track** (docs/13–14, D-44) —
> physical-platform bridge, 2-D action retrain (D-49) and the sim-to-real gap study; it does not
> reopen G4.
>
> **Post-gate note (31.07.2026, D-69).** The two open items this gate record lists as
> abstentions have since been **closed on posterior E5 evidence** — SR-009 out-of-band (D-64)
> and SR-010 as a determinate CL-B negative (notes ²³). This **does not reopen G4**: the gate
> closed on the F4 + GE4-V2 evidence base described above, that evidence is unchanged and
> un-re-scored, and closing a documented non-vetoing abstention with *more* evidence cannot
> retroactively weaken a gate that passed without it.

**E-track sim evidence — historical 139k campaign (12.06.2026; superseded by GE4-V2
above).** The matrix verdicts for H-10/11/12 → SR-012/013/014 now read **GE4-V2**
(`experiments/sim/campaign_e_v2/campaign_report.json`); this block records the *first*
GE4 roll-up, kept as the policy-evolution contrast: `experiments/sim/campaign_e/campaign_report.json`
(**1660 runs**, seed 2024, checkpoint `cobraflex_ppo_cam_lane_2024_139k_peak.zip`,
cage 0.6.1; enforcement + monitoring; 0 errors), with the clause-level breakdown
`experiments/sim/campaign_e/failure_mode_breakdown.json` (regenerable via
`tools/campaign_e_failure_modes.py`). The 139k **global camera-track verdict was
`NOT SATISFIED`** (D-30): SR-001, SR-012, SR-014 failed their scenario criteria and
SR-013 was D-29 under-covered. Two facts qualified it:

- **The cage's core safety property holds under the camera.** Across all 830
  enforcement runs there are **0 road-edge contacts**, and M-S1 < `d_max` in every
  run except the 9 SC-FRONT-01 cells that *spawn the vehicle at `d_max` = 0.16 m*
  (out-of-ODD start, scored on road-edge contact; max M-S1 there 0.168 m). The
  camera never produced a lane breach in enforcement — it **degraded to safe stops**.
- **The cage flips latent → active.** In F4 (ground-truth state) the cage is *latent*
  in-ODD (M-S2 = 0 in both modes). Under the camera the SR-013 / Trigger-8 controlled
  stop becomes the operative mechanism; its protective value is unambiguous in
  **SC-PERT-07** (perception loss): enforcement **20/20** vs monitoring **0/20**, the
  20 monitoring fails being genuine M-S1 breaches the open-loop stop prevents.

The F-track SR verdicts (SR-001..011) above are **unaffected** — the F4 evidence is
frozen; the E re-runs of F-track scenarios are reported only as a contrast in §8.9.

> ⁴ **SR-012 / SR-014 (camera lane-keeping / estimator plausibility) — GE4-V2: Satisfied**
> (SC-PERT-04..13 pass in enforcement, SC-PERT-08 false-lane 25/25, D-29 coverage closed by
> the SC-PERT-08/09/10 rep bump; D-45 criteria). *Historical 139k reading:* Not satisfied
> as-scored; own-criterion reconciliation flagged. Both vetoed via the same two
> scenarios. SC-EDGE-02 (**13/13** enforcement fails) and SC-PERT-04 (**20/20**) fail
> *only* on the `emergency == False` clause: M-S1 < `d_max`, no road-edge contact —
> the cage executed its SR-013 controlled stop on a camera-degraded percept and the
> scenario criterion scores that safe stop as a fail. SR-012's *own* stated criterion
> (M-S1 ≤ `d_max` ∧ M-S2 = 0 in enforcement) is met everywhere. SR-014's *primary*
> plausibility scenario SC-PERT-08 (false-lane injection) passes **20/20**; its
> camera-track failure is the secondary inheritance of SC-PERT-04. As with SR-006
> (note ¹, D-39), re-scoring these on their own safety-limit criterion — treating the
> controlled stops as the specified SR-013 behaviour — is **D-45**, applied to the
> complex_b GE4 criteria; the 139k matrix above still reads the pre-D-45 as-scored verdict
> (it scores a superseded policy). SC-PERT-05 (low-light, two-arm `low:/high:` criterion)
> was *indeterminate* in the 139k roll-up (labelled evaluator unwired — D-38 class); the
> evaluator is now **wired** (`eval_policy` picks the rep's level arm via
> `criterion_eval.labelled_arms`), so the 297k run scores it. SC-PERT-03 (finetune arms,
> not level-resolvable) stays grouped by the driver (separate item).
>
> ⁵ **SR-013 (safe degradation on perception loss) — GE4-V2: Satisfied** (SC-PERT-07
> 25/25 + SC-PERT-13 40/40 in enforcement; the D-46 two-sided coverage closes the D-29
> gate). *Historical 139k reading:* verified on its scenario, D-29 under-covered —
> SC-PERT-07 passed **20/20** in enforcement (the open-loop stop fired within budget,
> M-S1 < `d_max`, no edge contact) but the roll-up listed SR-013 INCOMPLETE because a
> single adverse scenario/family did not meet the CL-A D-29 gate (≥ 25 runs in a nominal
> *and* an adverse family). Not a failure: it needed the broader coverage V2 supplied.
>
> ⁶ **SC-PERT-11 / 12 / 13 (markings / image / combined camera degradation) — added
> 2026-06-24, not yet run.** New complex_b camera scenarios (`scenarios_complex_b/`):
> SC-PERT-11 worn/segmented lane markings (world-variant `complex_b_gaps.world`),
> SC-PERT-12 camera image degradation (glare injector on normal markings), SC-PERT-13
> both compounded. They broaden the SR-012 / SR-014 adverse family and give **SR-013 a
> second adverse scenario** (SC-PERT-13), addressing the ⁵ adverse-side under-coverage.
> All three score under degraded markings as a face of **H-10** (in-ODD per ODD-2 §5.4).
> **Scored in GE4-V2**: SC-PERT-11 **30/30**, SC-PERT-12 **40/40**, SC-PERT-13 **40/40**
> in enforcement — vs monitoring 0/30, 23/40 and 0/40, the cleanest in-ODD measure of the
> cage's value under camera degradation (the SR-013/Trigger-8 stop prevents the excursions
> the bare policy commits). The nominal-family gap for SR-012/013/014 is closed by
> **D-46**: SC-NOM-01 (clean input) is their nominal family — the no-false-trigger /
> baseline-competence arm — with SC-PERT-04..13 the adverse arm, so all three meet D-29.
>
> ⁷ **SR-002 / SR-003 (heading stability / predictive TTLC) — Satisfied on own criterion; the
> SC-EDGE-01 "fail" is an oval-legacy performance bar (D-39 class, D-47).** SC-EDGE-01 (15°
> heading-error start) shows **13/30** enforcement "fails" in V2 (9/30 in V1), but all fail *only*
> the scenario clause `time_to_recovery_heading < 2.0 s` — a bar that is **neither SR's documented
> satisfaction criterion**. **SR-002** is `M-P4 ≤ θ_max = 25°`: measured **max M-P4 = 14.4°** over the
> failing runs (the vehicle never exceeds its 15° start). **SR-003** is `TTLC ≥ t_min`, whose 0.7 s
> policy-side component docs/03 flags *provisional, revisit at Phase-3 close*; the vehicle never
> approaches the lane (M-S1 ≈ 0.035 m, 0 emergency, 0 edge contact). On their own safety-limit criteria
> both are **Satisfied** — the 2.0 s recovery-time clause is a performance overlay copied verbatim from
> the oval set, not a safety predicate. Re-scored on own criterion à la note ¹ (D-39) / note ⁴
> (SR-012). In **V2 these are the *only* literal blocking SR-CL-A** (SR-001 closed by ruta-1), so the
> global `NOT SATISFIED` rests entirely on this clause — no safety predicate is breached. See **D-47**.
> **Re-measured on the verdict of record (2-D PPO 550k, 31.07.2026):** the same two SRs, the same
> single scenario, the same single clause — 22/30 enforcement runs violate `time_to_recovery_heading`
> and **nothing else** (0 emergencies, max M-S1 0.043 m ≪ 0.16 m, max M-P4 **14.2°** ≤ 25°). The
> reconciliation is therefore not a one-campaign convenience: it reproduces across policy, action
> space and checkpoint. What *did* change is that the clause was audited (**D-68**) — its band
> measured ripple rather than recovery — and under the corrected metric this arm still fails while
> the 1-D arm would pass, so the failure is a genuine, reportable **performance** property of the
> 2-D policy's bang-bang command stream, not a metric artefact. The 2.0 s **bound** was deliberately
> left untouched: D-68 fixes a measurement, not a pass bar.
>
> ⁹ **The verdict of record is the 2-D PPO 550k campaign (31.07.2026, D-69).** SR-012/013/014 are
> Satisfied on **both** camera arms; the rows above cite the E5 campaign as current evidence and
> retain GE4-V2 as the frozen G4 gate record. Re-pointing was deferred by **D-67** precisely
> because, at the time, the 2-D arm had a nominal evaluation and a D-43 preflight but **no
> verdict** — D-67 stated that if the campaign returned a worse in-ODD safety picture than
> GE4-V2's the trunk decision had to be revisited rather than defended. It did not: in-ODD
> enforcement road-edge contacts are **0** on both arms, and out-of-ODD the 2-D arm more than
> halves them (56 vs 117). The condition is met, so the deferred edit is taken.
>
> ⁸ **CL-B GE4 readings (do not gate the global safety verdict) — reconciled / characterised
> (D-48).** **SR-011** (heading-variance) reads `failed` only by inheriting SC-EDGE-01's
> recovery-time clause; on its own metric the measured max σ_θ over 1 s is **3.0° < the 5° M-P7
> limit**, so it is Satisfied (same artifact as SR-002/003, note ⁷). **SR-006** (committed-steer
> smoothness) is scored **out-of-band** on its own metric (`tools/sr006_smoothness.py`, D-39);
> `run_campaign.aggregate_sr` now returns it as `scored_out_of_band` (`OUT_OF_BAND_SRS`) instead of
> letting its `ALL`-scenario mapping inherit unrelated fails — the V2 report no longer reads
> `failed`. **SR-010**: the `grid_point` in-ODD/OOD attribution is now wired
> (`tools/campaign_e_failure_modes.py` → `sc_edge05_grid_split`). The split **corrects the earlier
> "largely OOD" guess** — of SC-EDGE-05's 100 enforcement runs, **30 of 85 in-ODD grid points breach
> M-S1** (a *genuine* SR-010 co-activation finding) vs 10/15 OOD bracket points (factors 0.85–1.30,
> out of scope). SR-010 is therefore a **real CL-B co-activation result**, not an artifact, to
> re-measure on the V2 run (legacy estimator — the ruta-2b estimator change was reverted after it
> regressed in closed loop, D-48). **SR-009** — its stall sub-mode is **N/A for the
> steering-only action space** (ED-2 / D-49): the policy controls steering only (`ACT_DIM = 1`),
> throttle is fixed cruise, so the vehicle cannot converge to inaction — **M-P6 ≡ 0 by construction**,
> and SC-PERT-03's reward-injection (`r' = r − λ·|throttle|`) is **inert** (a constant on a fixed
> throttle), so the stall negative test is not applicable to this policy class. SR-009's *live* arm —
> M-S2 under monitoring (the adversarial-direction sub-mode of H-08) — **is** covered by the
> nominal/monitoring runs. So SR-009 is **satisfied-by-construction on the stall arm + covered on the
> M-S2 arm** for track E; the well-posed stall test is deferred to the 2-D-action Isaac work (D-49).

**No `TBD` verdict remains in the simulation column (31.07.2026, D-69).** Every SR now carries a
determinate, evidence-backed `verdict_sim`: eleven **Satisfied**, two **Satisfied on their own
criterion** with the literal failure recorded and reconciled (SR-002/003, note ⁷ + D-47/D-68), and
one **Not satisfied** reported as a limitation (SR-010, note ³). The `verdict_phys` column stays
`tbd` throughout, and since 08.2026 for a narrower reason than "not run": Phase 5 **has driven on
hardware** — 18.05 m of the real circuit in one uninterrupted segment with no safety rule fired
(docs/17 §8.10) — but **no scenario has been executed under protocol**, in enforcement and on the
D-43 perception contract every campaign was scored under. Driving is not scoring; a physical
verdict read off out-of-protocol runs would be fabricated, exactly as an estimated one would be.
Two rows are **qualified but not re-scored** by that hardware evidence: **SR-004** is satisfied via
C-04, and in the deployed physical configuration C-04 **cannot fire at all** (`v_max_curve_mps`
0.25 > the deployed 0.22 m/s), so the simulation coverage gap is a rule that does not protect a
real physical case; and the policy this matrix scores (the 2-D 550k trunk) is **not** the policy
that drives — it does not transfer (D-71), and what deploys is the v2 retrain (D-72). The one open ODD parameter, `ODD-3.A_LAT_MAX`
(**TBD-Q10**, docs/08 §11), is likewise hardware-gated by construction (**D-33**): it is
unmeasurable in simulation, so no simulation campaign — this one included — could have closed it.

The `Cage Rule(s)` column accepts three implementation kinds (cf. D-25 in `docs/DECISIONS.md`): a numbered rule `C-XX`, a `training` constraint discharged at policy-training time (SR-009), or an `arbiter` property of the cage pipeline (SR-010). SR-011 is implemented jointly by `C-06` (runtime attenuation of high-frequency content) and a training-side heading-variance penalty.

The **Frontier** scenarios (`SC-FRONT-01..06`, `docs/05`) exercise SR-001/002/005/007/008 but are **deliberately absent** from this matrix and from `traceability_matrix.csv`: per **D-35** they form an out-of-ODD cage-efficacy study reported as a paired enforcement-vs-monitoring contrast on **M-S5** (road-edge departure), *not* a pass/fail verdict folded into the D-30 aggregation. The cage's marginal value beyond the ODD is reported separately via `tools/frontier_contrast.py` and manuscript §8.2.2–§8.2.3, and never vetoes the global verdict.

## Verdict possibilities

- **Satisfied** — the criterion holds with margin across all relevant runs in enforcement mode.
- **Partially satisfied** — the criterion holds in most conditions but with documented exceptions in specific scenarios; rationale and impact analysis required.
- **Not satisfied** — the criterion does not hold; documented analysis of why and consequences for the work's claims.

The thesis can defend "Satisfied" or "Partially satisfied" verdicts with full rigour. "Not satisfied" verdicts are reported honestly and discussed in the Limitations chapter.

## Verdict by source of evidence

Verdicts can be split between simulation evidence and physical evidence:

- **Sim**: as evaluated in Phase 4 across the simulation campaign.
- **Phys**: as evaluated in Phase 5 across the physical experiments, when scope permits.

Some SRs will have only Sim verdicts; SRs verified only in scenarios not exported to physical have no Phys verdict by design, and this is documented.

## Update procedure

When any of the following changes, the matrix is updated and `tools/check_traceability.py` is re-run:

- A hazard is added, modified, or deprecated in the Hazard Register.
- An SR is added, modified, or deprecated in the SRS.
- A cage rule is added, modified, or removed.
- A scenario is added, modified, or removed.
- A metric is added or modified.
- A verdict is filled in based on experimental evidence.

Every update is recorded in `docs/08_change_log.md`.

## Schema of the CSV

`tools/traceability_matrix.csv` has the following columns:

| Column | Type | Description |
| ------ | ---- | ----------- |
| `hazard_id` | string | H-XX |
| `sr_id` | string | SR-XXX |
| `cage_rule_id` | string | C-XX or empty if implementation is not a cage rule |
| `implementation_kind` | string | "cage_rule", "training_constraint", "arbiter", or "scenario_test" (the four kinds D-25 admits; `arbiter` is a structural property of the cage pipeline rather than a numbered rule — SR-010) |
| `scenario_id` | string | SC-* |
| `metric_id` | string | M-* |
| `verdict_sim` | enum | "satisfied", "partial", "not_satisfied", "tbd" |
| `verdict_phys` | enum | same plus "out_of_scope" |
| `evidence_path` | string | relative path to the experiment directory |
| `notes` | string | free text |

Each row of the CSV represents one chain from a hazard to a metric (with possibly intermediate links). A single hazard typically appears in multiple rows because it spans multiple chains.

## Known orphans (must be empty before any Gate)

- (none expected; if any appear, list them here with rationale)

<!--
## Anticipated defense questions

**Q1. Every verdict in the matrix was "TBD" before Phase 4 — so at that point did the traceability matrix prove anything?**
(Historical form of the question; as of 31.07.2026 the sim column is fully filled — see the closure note above.)
It proves the *structure* is complete and orphan-free: the eight coverage constraints, mechanically enforced by `check_traceability.py`, guarantee every hazard has a mitigation path down to a metric. The verdicts are the *evidence* layer, filled in Phase 4 / 5. A complete-but-TBD matrix is the honest pre-campaign state — it guarantees that when evidence arrives there is exactly one place to record each verdict and no claim is left without a home.

**Q2. The Frontier scenarios are "deliberately absent" from the matrix — doesn't omitting scenarios from the master record contradict the no-orphans rule?**
No, because the SRs that FRONT scenarios touch are already covered by in-ODD scenarios, so removing FRONT creates no orphan. They are excluded because they yield a paired M-S5 contrast, not a `fraction_pass` verdict (D-35); folding them in would let an out-of-ODD result veto the in-ODD verdict (D-30). Their evidence lives in manuscript §8.2.2–§8.2.3 and `frontier_contrast.py`, cross-referenced but outside the CSV.

**Q3. The matrix admits three "implementation kinds", including "training constraint" and "arbiter" that are not cage rules — doesn't that weaken the claim that every SR is enforced?**
It makes the claim *honest*. SR-009 (liveness) and SR-011 (oscillation) cannot be discharged by a reactive rule without violating cage philosophy, and SR-010 is a pipeline property rather than a rule. Labelling the kind (D-25) is more truthful than inventing a cage rule; the verification side still demands a scenario and a metric for each, so the chain is unbroken whatever the implementation kind.

**Q4. You allow a "Partially satisfied" verdict — isn't that a loophole to avoid declaring failure?**
"Partial" is bounded by a requirement: it holds in most conditions *with documented exceptions plus an impact analysis*. The document commits to defending only "Satisfied" / "Partial" with rigour and to reporting "Not satisfied" honestly in the Limitations chapter. The grade exists because a binary verdict would force either overclaim or the discarding of genuinely useful evidence (e.g. an SR that holds at σ = 0.01 noise but degrades at σ = 0.05).

**Q5. Sim and Phys verdicts are split, and some SRs will have "no Phys verdict by design" — isn't a requirement without physical evidence unvalidated?**
The split is deliberate and disclosed: an SR verified only in scenarios not exported to the physical subset (`docs/05` Phase-5 subset) carries `out_of_scope` for Phys, not a false pass. The bounded-validation principle (A5 / D-11) means physical evidence characterises the gap on the *exported* subset, not on every SR; which SRs lack Phys evidence is itself recorded, so the limitation is explicit.

**Q6. The Markdown table is hand-summarised but the CSV is generated — how do you guarantee they don't drift?**
`sync_traceability.py` keeps the two forms in sync and `check_traceability.py` verifies the eight constraints on the CSV; the Markdown is the human view, the CSV the checked artefact. The working rule is single-source-of-truth in the Markdown with re-derivable CSVs that are never hand-edited, so any drift surfaces as a check failure that blocks the next Gate.

--->

## Change log

See `docs/CHANGELOG.md`.
