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
<!-- Subsequent entries appended below -->
