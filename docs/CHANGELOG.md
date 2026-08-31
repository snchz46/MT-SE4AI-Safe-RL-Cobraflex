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

## [31.08.2026] — Four laps, a tape sweep, eight hypotheses and eight refutations: the M-7 `ey` under-read does not survive rectification, and the failure is a mismatch between two envelopes rather than a defect in either

**Document(s) affected:** `experiments/physical/runs/SESSION_20260831.md`,
`experiments/physical/runs/{lanesweep,lap01..lap04,preflight}_20260831*/`,
`src/cobraflex_rl/cobraflex_rl/{cage_logger_node,cage_reset_proxy_node}.py`,
`policy/tests/{test_cage_reset_proxy,test_deploy_evidence_contract}.py`
**Phase:** 5 (physical deployment)
**Gate context:** after G4. **Posterior evidence — re-scores nothing.** `monitoring` only, N=1 per run, no scenario scored.
**Author:** Samuel Sanchez

### Change

Second driving session on the real circuit, using the instrumentation prepared on
27.08 (`cage_logger_node platform:=physical`, `frame_capture_node`,
`cage_reset_proxy_node`, `tools/run_physical_lap.sh`) — the first time any of those
three nodes was launched. **Goal — one complete lap without stops — NOT achieved.**
Best distance **14.56 m** (lap02, 4 resets) against 26.08's 18.05 m one-segment run.

Two fixes were made and committed from the car: `cage_logger_node` died in its
constructor on `platform:=physical` the first time the provenance block was ever
launched (`ros2 launch` types numeric-looking parameters, and `.string_value` on a
DOUBLE returns `""`, so the numeric contract fields would have vanished from
`metadata.json` in silence); and `cage_reset_proxy_node` gained `blocking_rules` as a
parameter, **default unchanged**, documenting the measured deadlock.

### Rationale — what the day established

* **The M-6/M-7 `ey` under-read does not exist rectified.** Nine-point tape sweep,
  hands-off, on the ground: scale **1.058** (left) / **0.991** (right), against 0.72
  propagated by M-6 and 0.68-0.83 measured by M-7. C-01 fires at a true **151 mm** with
  ~100 mm of margin to the road edge, not at 207-241 mm with 14-48 mm. The M-7 §4
  finding is superseded for the rectified configuration, which is the deployed one.
* **The estimator is unstable right-of-centre and confident while wrong.** 43.3 mm of
  swing on a STATIONARY car at -60 mm (sd 8.4 vs 0.5 mm mirrored), reproducible across
  two consecutive runs, `/perception_invalid` False for all 705 cycles — H-12 / D-43.
  The measurement **predicted lap01's stop before it happened**: -58.8 mm was that
  run's max |ey| and the spike fired there.
* **C-02 failures are SUSTAINED, not transient** — 99 % of C-02 cycles sit in episodes
  of >= 2, one of 45 cycles; only 1 of 15 episodes is a single cycle. This is why a
  heading-rate plausibility gate would catch just 12 of 102.
* **C-04's dead zone, again, and now with a cost.** `v_max_curve_mps` 0.25 > deployed
  0.22 means C-04 cannot fire, while |ey| grows monotonically with curvature
  (26 -> 32 -> 33 -> 43 -> **63 mm**). D-69's finding (ii) is no longer only a coverage gap.
* **`monitoring` does not mean the cage cannot stop the car.** `vehicle_control_node`
  forces `/cmd_vel.linear.x = 0` on a latched `/emergency` in BOTH modes, by design. A
  lap "without stops" would require disabling that fail-safe — which would void the lap,
  since the cage is what the thesis evaluates.
* **Eight single-component hypotheses, all refuted by measurement** (starting position;
  heading error scaling with curvature, r = 0.045 over 1208 moving cycles; a degenerate
  frame stack after reset; `white_sat_max` mis-set for the hall; a heading-rate gate; a
  tighter `lane_width_tol_m`; a narrowed reset-proxy guard, which turns deadlock into
  livelock; a different `heading_fit_mode`/gain).
* **The diagnosis that survives.** M-7 measured 0.8 % of frames past C-02 in this exact
  configuration, on a circuit recording of a car **pushed by hand** near the centre.
  Driving itself, the same configuration gives **6.8-11.6 %**. The policy runs wide in
  curves; the estimator is trustworthy near the centre. **The estimator's reliable
  envelope and the policy's driving envelope do not overlap well enough** — which is
  why every single-component hypothesis failed.

### Impact

No hazard, SR, cage rule, scenario, metric or verdict is added or re-valued.
D-69 and GE4-V2 stand; **`verdict_phys` remains open** — no scenario has been scored on
hardware. Driving figures here are **PRELIMINAR, N=1, `monitoring`, unscored**; the
sweep results (scale, right-side instability) are **calibration results** and carry the
same standing as M-6 and M-7. What would unblock a lap is a **full-circuit recording
with true position**, as in M-7 §3 — event frames cannot answer it, being failure
neighbourhoods whose statistics do not generalise. Four items were left for the compute
host and are closed in the `· later` entry above.

### Verification

`python3 tools/check_traceability.py` → All checks PASSED, 0 warnings. `pytest` → 808
passed, 2 skipped at the time of the session commit (`7c496ff5`); the
`cage_logger_node` regression test was verified to FAIL against the previous HEAD
before the fix, and four tests pin both the reset-proxy deadlock and the fact that the
obvious narrowing livelocks.

---

## [31.08.2026 · D-78] — The true-position capture becomes executable and self-scoring: arc length from floor stations instead of odometry, and a provenance gap closed on the way

**Document(s) affected:** `docs/DECISIONS.md` (D-78 — new), `docs/17_physical_deployment.md` §11,
`tools/record_lane_dataset.py`, `tools/score_lane_capture.py` (new),
`tools/tests/test_score_lane_capture.py` (new), `CLAUDE.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4. Preparation only — **nothing captured, nothing launched.** No `cage.yaml`, SR, cage rule, ODD parameter or verdict touched.
**Author:** Samuel Sanchez

### Change

Next-step 1 — the capture session with true position — is now a runbook plus two tools, not an
intention.

**`record_lane_dataset.py` gains a true-position mode.** `--true-ey` records the tape-measured offset
the car is pushed at; `--station-arc` takes the tape-measured centreline arc-lengths of numbered floor
stations, and ENTER on stdin advances the anchor as the car passes each. New CSV columns:
`line_c0_m`, `curvature_1pm`, `true_ey_m`, `station`, `s_m`. Two behaviours matter as much as the
columns:

* **`--true-ey` switches the tool into MEASUREMENT mode, which keeps every frame** — including the
  unpaired and bad-width ones the appearance-gap mode deliberately drops. Those frames *are* the
  pairing failures being counted; dropping them rebuilds the selection bias that made the 31.08 event
  frames unusable (docs/17 §10.6). One tool, two uses, opposite demands on the same filter.
* **`--no-frames`, and 20 Hz.** Every statistic comes from the CSV, so a measurement lap costs
  ~400 kB instead of ~600 MB — the 18.08 eMMC lesson applied rather than restated. The rate must be
  **20 Hz, not the 5 Hz default**: the relocation criterion compares consecutive frames, and at 200 ms
  of dt the 1.0 m/s threshold degenerates into "> 200 mm", blind to most of what §10.7 measured.

**`tools/score_lane_capture.py` (new)** scores a capture in three blocks — accuracy vs the tape
(D-76), unphysical relocations and whether they move *away* from truth (D-77), and D-75's closed-loop
`∮κ·ds` — with **acceptance criteria fixed in advance** and every statistic reported **per station
segment, worst segment named, no circuit mean**. That last rule is not stylistic: the 31.08 sweep's
own stated limitation was "one location", and a circuit average is exactly how a local failure hid
while the estimator paired 95.4 % of frames overall.

**Arc length comes from floor stations, never from odometry.** D-73 turned the ZED's loop closure off
*because* the odometry could not be trusted, so deriving arc length from it would import the very
defect the test must be independent of. The scorer interpolates linearly in time **between**
consecutive anchors and **never past one**.

### Rationale

Eleven single-component hypotheses have now been refuted against data — eight against driving logs
(§10.3), three against the offline replay (§10.7). What has never existed is a measurement of the
estimator's accuracy **around** the circuit: every physical `ey` label so far was produced by the
estimator under test, and the one clean tape measurement covered one location. D-75 also named
`∮κ·ds ≈ 2π` as the precondition before `v_max_curve_mps` may ever be revisited, and that integral is
computable from floor stations with no sensor beyond the camera.

### Impact

**A provenance gap was found and closed.** `circuit_export/labels.csv` carries `line_c0_m` — the
column D-77's entire offline replay rests on — and **no tracked tool wrote it**; it came from an
untracked variant on another host. D-77's analysis stands (the replay reproduces the recorded `ey` on
**1450/1450** frames, strong internal validation), but it was **not reproducible from the repo**,
which is a real defect in a thesis whose defining commitment is traceability. The recorder now writes
it.

**Noted, not changed:** `deploy_cobraflex.launch.py` still declares `heading_fit_mode` default
`joint_pair_quadratic` while every run that actually drove used `near_secant` (§8.4: 14.45 m against
1.08 m). That default is misleading and wants its own decision; it does not affect this session, which
uses no launch.

No hazard, SR, cage rule, scenario, metric or verdict added or re-valued. `verdict_phys` stays open —
this session cannot produce it, the policy does not run. It also does not fix anything: it is the
measurement that says **where** to fix, which is what every previous session was guessing at.

### Verification

`pytest` → **818 passed, 2 skipped** (up from 814: four new tests pin that arc length is never
extrapolated past an anchor, that a single station yields **no** arc length rather than a confident
number from nothing, that an unpaired frame breaks the relocation chain instead of bridging it, and
that the detector reproduces D-77's figures on the tracked `circuit_export` — 1401 transitions, 42
relocations). `python3 tools/check_traceability.py` → **All checks PASSED, 0 warnings.** The scorer was
run end-to-end against `circuit_export`, degraded correctly on the three missing columns, and returned
42 relocations / worst 364.4 mm at 7.15 m/s apparent — matching the independent D-77 replay. Both CLIs
parse. **Nothing was run on the car.**

---

## [31.08.2026 · D-77] — The estimator is widened where it could be: SR-014's inter-frame gate was nine times the physical motion, and a tracked CSV column turned out to be a full-circuit test bench

**Document(s) affected:** `docs/DECISIONS.md` (D-77 — new), `docs/17_physical_deployment.md` §10.7,
`src/cobraflex_rl/cobraflex_rl/{cage_perception,cv_lane_estimator_node}.py`,
`src/cobraflex_rl/launch/deploy_cobraflex.launch.py`, `policy/tests/test_cage_perception.py`,
`CLAUDE.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4. **Physical path only — simulation defaults unchanged, D-69 verdict path bit-identical. `cage/cage.yaml` untouched.**
**Author:** Samuel Sanchez

### Change

**D-76's blocker was half wrong, and that is the enabling find.**
`experiments/physical/datasets/circuit_export/labels.csv` is **tracked**, and its `line_c0_m` column
carries the per-frame lateral intercepts of every detected line — the exact input to the pair-selection
decision. A pure-Python replay from that column **reproduces the recorded `ey` on 1450/1450 paired
frames** (max deviation 0.01 mm, CSV rounding). The *consistency* question is therefore answerable
offline, on a full circuit, on this host, with no frames and no Jetson; only *accuracy* still needs true
position.

Defining an unphysical relocation as the selected pair's centre moving > 60 mm at > 1.0 m/s apparent
lateral rate (60 mm clears the estimator's own 43 mm off-centre noise span; the car cannot move sideways
faster than 0.22 m/s), the recording holds **42 in 1401 transitions**, worst **364 mm in one frame — 47×
the car's top speed**.

**Three fixes tried and refuted before the one that worked.** (i) Temporal continuity in the pair
selection: **no effect at all** — **90 % of the relocations had only ONE plausible pair**, so there was
nothing to choose between; the candidate line *set* changed. This also explains why D-48's `ruta-2b` was
reverted as unnecessary. (ii) Tightening `lane_width_tol_m`: actively harmful — frames with no plausible
pair go **41 → 110 → 231 → 483** across 0.08 → 0.04, confirming the 31.08 refutation of hypothesis 6
from a second direction. (iii) Tightening SR-014's `lane_width_range` alone: forbidden by an invariant
already in the code — the supervisor derives that window from the estimator's pair-acceptance window to
avoid the **E2 dead zone** that deadlocked the cage.

**The finding: SR-014's gate is mis-scaled, not missing.** It is already rate-based —
`allowed_dey = |v|·dt + jump_tol_m` — but at 0.22 m/s and 50 ms the physical term is **11 mm** against a
`jump_tol_m` of **100 mm**: **nine times** the motion it bounds, admitting a 111 mm relocation as
"temporally consistent".

| `jump_tol_m` | relocations caught | good frames suppressed | no pair | added C-05 rejects |
| --- | --- | --- | --- | --- |
| 0.10 (frozen, simulation) | 10 / 42 | 0.00 % | 0 | 0 |
| **0.05 (new physical default)** | **30 / 42** | 0.57 % | 0 | 5 |

`jump_tol_m` is now an optional supervisor argument (`None` = the frozen 0.10) exposed as
`perception_jump_tol_m` on `cv_lane_estimator_node`, following the `perception_min_invalid_cycles`
precedent (`< 0` keeps the default). The physical launch defaults to **0.05**.

### Rationale

The 31.08 sweep observed `/perception_invalid` staying False through a 43 mm swing and concluded the
estimator was "confidently wrong". It is — but the plausibility check meant to catch that is not absent,
it is scaled so loosely that the physical term it is added to is irrelevant. 0.05 is the smallest value
above the measured 43 mm noise span and well below a half-lane relocation; it is a bound, not a fitted
optimum.

### Impact

**This does not make the estimator read correctly off-centre** — the pairing is unchanged and D-76's
diagnosis stands. It converts a **silent wrong answer into a declared unavailability**: a caught frame
sets `plausible=False`, suppressing `/state_obs` via the cage's missing-state path **without** raising
`/emergency` (C-05 still requires `min_implausible_cycles`). That is the right direction for H-12, whose
difficulty is that a wrong estimate is self-consistent and therefore invisible. No hazard, SR, cage
rule, scenario, metric or verdict added or re-valued; `verdict_phys` stays open. **An early sweep of mine
used the checker's generic 0.20–0.80 width default as the baseline; that is not the deployed window
(`nominal ± tol` = 0.145–0.345) and those numbers are withdrawn.**

**Watch item for the next session:** a C-05 latch ends a segment on hardware (D-74), so the **reject
count** is the first thing to read; **0.06** is the fallback if 0.05 proves too tight in motion.
**Nothing here has been launched** — host logic and tests only.

### Verification

`pytest` → **814 passed, 2 skipped** (up from 810: four new tests pin that the default stays 0.10 so the
verdict path is untouched, that the override reaches the checker, that the E2 lane-width invariant
survives the override, and that a 90 mm relocation passes the frozen gate, is caught by the tightened
one, and suppresses state **without** raising C-05). `python3 tools/check_traceability.py` → **All checks
PASSED, 0 warnings.** The replay figures are reproducible from the tracked
`experiments/physical/datasets/circuit_export/labels.csv`; nothing was run on the car.

---

## [31.08.2026 · D-75/D-76] — The two open Phase-5 decisions are taken, and both resolve to "not yet": C-04 is un-armable by measurement, and the curvature its threshold would key on over-reads by ~3×

**Document(s) affected:** `docs/DECISIONS.md` (D-75, D-76 — new),
`docs/04_cage_specification.md` §C-04, `docs/17_physical_deployment.md` §10.4/§10.4b,
`CLAUDE.md`, `docs/CHANGELOG.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4. Posterior evidence. **`cage/cage.yaml` UNCHANGED — deliberately, in both decisions.**
**Author:** Samuel Sanchez

### Change

The two items the 31.08 next-steps list carried as decisions rather than tasks are now taken as
ADRs. Neither changes `cage.yaml`, an SR, a cage rule, an ODD parameter or a verdict.

**D-75 — C-04's dead zone is total, and stays open on purpose.** The ceiling is
`max(v_max_curve, v_max_straight − k_kappa·|κ|)` = `max(0.25, 0.5 − 0.3·|κ|)`, so **0.25 m/s is a
floor no curvature can push it below**, while the deployed policy is capped at 0.22. Measured over
the **2484 moving cycles** of the day: speed median 0.166, p90 0.191, p99 0.209, **max 0.228 m/s**,
and cycles reaching the 0.25 floor: **zero**. C-04 fired 0/1890 in the D-69 campaign and has now
never arbitrated on hardware either. `v_max_curve_mps` stays at 0.25; the non-coverage is recorded
in `docs/04` §C-04 as a stated limitation of the validation.

**The new measurement that decides it — `kappa_ahead` over-reads by ~3×.** On a closed circuit
`∮κ·ds = 2π` per lap. Integrating the logged `|κ|` (an **upper** bound, since `|κ|` cannot cancel)
over the logged distance:

| run | distance | laps of 19.28 m | turning implied by geometry | measured `∫\|κ\|ds` | ratio |
| --- | --- | --- | --- | --- | --- |
| lap01 | 3.05 m | 0.16 | 0.99 rad | 0.32 | 0.33 |
| lap02 | 14.46 m | 0.75 | 4.71 rad | 14.31 | **3.04** |
| lap03 | 5.28 m | 0.27 | 1.72 rad | 1.81 | 1.05 |
| lap04 | 10.64 m | 0.55 | 3.47 rad | 10.11 | **2.92** |

Pooled `|κ|` reads median 0.89, p90 1.52, **max 2.88 m⁻¹** against `ODD-3.KAPPA_MAX` 1.14 (centre) /
1.00 (driven) and the ≈ 0.75 that docs/17 §8.8 gives for the tightest curve. The physical circuit was
built to the complex_b perimeter (19.28 m against 19.22 m), so its geometry is not the explanation.

**D-76 — the "envelope mismatch" has a mechanism, and it sets the order of work.** Binned by lateral
offset, the share of cycles reading `|κ| > 1.14` climbs **8.4 % → 28.0 % → 38.9 % → 38.0 % → 53.9 %**
across `|ey|` of 0–20/20–40/40–60/60–80/80–120 mm. With the stationary sweep's 43.3 mm `ey` swing and
the sustained C-02 episodes, that is **one failure expressed in three channels**: off-centre, the
estimator misreads offset, heading **and curvature** at once and reports none of it invalid (H-12).
Decision: **widen the estimator before narrowing the policy.** The policy does *not* consume the
estimator — the CNN reads the image, the estimator feeds the **cage** — so the chain is: policy runs
wide → estimator degrades in a region it was never characterised in → **the cage arbitrates on
corrupted state** and latches C-05. Narrowing the policy stays the documented fallback, to be argued
as an ODD restriction rather than applied as a silent tuning.

### Rationale

Both decisions resolve to "not yet", for the same reason: the obvious action on each — lower C-04's
threshold; pick a side of the envelope mismatch — keys on `kappa_ahead`, and that signal is not
trustworthy enough to act on. Arming C-04 now would cut throttle on curvature that is not there,
concentrated exactly where the car is already off-centre and already in trouble. The prerequisite is
therefore named and is **not more driving**: the full-circuit capture with true position (docs/17
§10.6), which now carries two acceptance tests — the closed-loop `∮κ·ds ≈ 2π`, and the offset sweep
repeated **around** the circuit rather than at one location.

### Impact

No hazard, SR, cage rule, scenario, metric or verdict added or re-valued; D-69 and GE4-V2 stand;
`verdict_phys` stays open. **A correction propagates, though:** any physical analysis binned on `κ` is
binned on a corrupted signal — docs/17 §8.8's "tightest curve" attribution and the 31.08 session
note's "|ey| grows monotonically with curvature" (26 → 32 → 33 → 43 → 63 mm) both need re-deriving
after the capture session, and are flagged in place. C-04 remains untested from above in simulation
*and* unexercised on hardware; that is now a stated limitation belonging in the defense narrative
next to D-69's finding (ii), and a real answer to "which of your six rules has never fired".
**Caveat carried in D-76:** `|ey|` and true curvature are correlated by driving, so only the
closed-loop integral is free of that confound — the over-read is established, its exact dependence on
offset is not.

### Verification

`python3 tools/check_traceability.py` → **All checks PASSED, 0 warnings**. `pytest` → **810 passed,
2 skipped** (unchanged — no executable logic was touched; `cage.yaml` and `cage/rules/` are
untouched by both ADRs). The curvature figures were computed from the tracked
`experiments/physical/runs/lap0*/cage_status.csv` and are reproducible from them; nothing was run on
the car.

---

## [31.08.2026 · later] — The track session's four open items closed on the compute host: the frame dump is priced in bytes, the preflight gate learns the statistic that caught the estimator, and 962 MB of PNG leaves the index

**Document(s) affected:** `.gitignore`, `tools/preflight_deploy.py`,
`src/cobraflex_rl/cobraflex_rl/{frame_capture,frame_capture_node,rl_policy_node}.py`,
`policy/tests/test_frame_capture.py`, `docs/CHANGELOG.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4 (closed 02.07.2026). Nothing here re-scores a gate; `verdict_phys` stays open.
**Author:** Samuel Sanchez

### Change

The 31.08 track session (`experiments/physical/runs/SESSION_20260831.md`, committed
from the car in `7c496ff5`) closed with four items it could not do on the Jetson.
All four are done here, on the compute host. `cage.yaml` is untouched and no
hazard, SR, cage rule, scenario or metric changed.

1. **962 MB of PNG untracked.** `frame_capture_node`'s event dumps landed in the
   index because `.gitignore` covered `experiments/physical/datasets/*/frames/` but
   not `experiments/physical/runs/*/frames/` — 3248 blobs across five runs, 4.4x the
   "218 MB in `preflight_20260831T092505Z`" the session note recorded. Rule added and
   the frames `git rm --cached`'d. **Fix-forward, by decision: the history is NOT
   rewritten.** `7c496ff5` is already pushed and the session notes cite it, so the
   blobs stay reachable there and a fresh clone still costs them; the files remain on
   disk on this host. The tracked `capture_events.csv` beside each dump carries the
   event index, reason, trigger time and filename of every frame, so the evidence
   chain survives the untracking — the same split the lane datasets already use.

2. **The capture budget is priced.** `max_frames` was 4000 with a docstring promising
   "roughly 20 MB of PNG for the whole run", an estimate built on the 26.08 lap's ONE
   in-motion event. Measured: 301 KB per 640x360 PNG over the day's 3248 frames, so
   the old cap was **~1.2 GB per run** on the eMMC that the 18.08 bag recording had
   already crashed. Default is now 600 frames (~185 MB); the docstring records the
   falsified assumption instead of the estimate. `budget_exhausted` is now reported at
   shutdown, because **all four driving runs saturated the 8-event cap** — which makes
   the frames on disk a *truncated* sample on top of the *biased* one the session note
   already identified (their median lane width reads 193 mm against the same
   estimator's 252.9 mm over a full circuit).

3. **`preflight_deploy.py lanecheck` gains the statistic that catches a pair-flip.**
   The gate returned PASS while the estimator swung **43.3 mm peak-to-peak on a
   stationary car** at a true -60 mm, because `sd_ey <= 10 mm` is the wrong statistic
   for a bimodal excursion: the flip sits ~31 mm off the mode and moves the span far
   more than the sd (8.4 mm, inside the old limit). Replaced by a span check
   (`<= 12 mm`) plus a retightened `sd_ey <= 3 mm`, both set from the sweep's measured
   healthy band (sd 0.5-1.4 mm over a 2.4 mm span). Replayed against
   `lanesweep_20260831T094110Z/lane_sweep.csv`, the new gate PASSES all five
   centred/left points and FAILS all three unstable right-side points; the old gate
   passed all eight. **It also fails the `sd_ey` 5.3 mm reading that docs/17 §8.2
   records as a PASS on 26.08** — that PASS should now be read as a probable false
   negative of the same mechanism, not as evidence the estimator was sound.
   A `COVERAGE` line was added stating what no threshold can fix: the stage samples
   **one** pose, and the sweep found the estimator quiet at centre and to the left and
   unstable from -60 mm rightward with `/perception_invalid` never firing (H-12 /
   D-43), so a car parked near centre passes every check while the region the policy
   drives through in curves is broken.

4. **`rl_policy_node` re-seeds its frame stack on `/cage_reset`.** `_first` was set
   once in the constructor and never again, so after a latched C-05 was cleared the
   k=4 stack straddled the stop and the new segment's first observations concatenated
   frames from either side of a gap of arbitrary wall-clock length — 250 s in lap04's
   proxy deadlock — which never occurs in training. This closes a **contract**
   deviation only: the session refuted it as the cause of the stops (hypothesis 3,
   degenerate stack 0.0 % vs 21.8 % between runs).

### Rationale

Items 1 and 2 are the same defect measured twice: a capture path whose cost nobody
had multiplied out, on a platform with a standing history of disk-pressure failure.
Item 3 is the more serious one — a *preflight gate that returns PASS on the exact
condition it exists to detect* is worse than no gate, and this one did so on the
morning of a session whose lap01 was then stopped at -58.8 mm, the run's max |ey|,
in the band the sweep had just shown to be unstable. Item 4 is bookkeeping against
the trained contract, recorded as such.

### Impact

No re-runs required and no verdict moves: D-69 stands, GE4-V2 stands, `verdict_phys`
stays open. The next track session inherits a stricter preflight, and **it should be
expected to FAIL `lanecheck` where 26.08 passed** — that is the intended behaviour
change, not a regression. The estimator's right-of-centre instability is diagnosed but
NOT fixed; the session note's conclusion stands unchanged — what unblocks a lap is a
full-circuit recording with true position, not another single-component hypothesis.
**None of the three ROS nodes touched here has been launched.** Per the repo's own
rule, typecheck and pytest are not evidence that a node runs: items 2, 3 and 4 are
verified as logic only and remain runtime-unverified until the next session on the car.

### Verification

`python3 tools/check_traceability.py` → **All checks PASSED, 0 warnings** (12 hazards,
14 SRs, 6 cage rules, all constraints OK). `pytest` → **810 passed, 2 skipped** (up
from 808: two new tests pin the byte-priced budget default and the observability of a
saturated one). The `lanecheck` change was replayed offline against the sweep CSV, as
tabulated in item 3; it was not run on the car.

---

## [27.08.2026 · later] — The manuscript and the specs catch up with Phase 5, as BRING-UP evidence: a falsified assumption, a policy that does not transfer, and the first measurement of a transfer risk declared before it was measured

**Document(s) affected:** `manuscript/draft_v5/front/{10_abstract,15_preface}.md`,
`manuscript/draft_v5/body/{09_gap_sim_to_real,10_validacion_operacional,12_conclusiones}.md`,
`manuscript/chapters/{chapter_07_training_specification,chapter_09_sim_to_real_gap,
chapter_10_operational_validation,chapter_12_conclusions_and_future_work}.md`,
`docs/07_traceability_matrix.md`, `docs/08_odd_specification.md`,
`docs/09_environment_design.md`, `docs/11_camera_rl_training.md` (§8.6 new),
`docs/12_cv_lane_keeper.md`, `docs/16_defense_compendium.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4; **no gate re-scored, no simulation verdict touched, no
hazard/SR/scenario/metric added or re-valued**
**Author:** Samuel Sanchez

### Change

1. **Chapter 9 was not merely incomplete — it asserted five things Phase 5 had
   falsified.** Audited and corrected: *"no se ha ejecutado sobre hardware"*;
   *"este capítulo no reporta ningún resultado físico"*; the effective-HFOV
   verification described as still pending; the 550k trunk described as *"la
   política que efectivamente se despliega"*; and the rate-limiter coupling
   described as *"el primer gap a vigilar"*. The same claims propagated to the
   **abstract**, the **preface**, Ch. 10 §10.2/§10.4 and Ch. 12's subordinate
   research question — all corrected.
2. **§9.3 rewritten around what the hardware produced**, in four parts: the
   blocking verification that ran and **failed** (M-6: 77.89°, not 90°; M-7: `ey`
   read at 0.68–0.83 × true − 10 mm, so **C-01 fires at a true 207–241 mm**
   instead of 160, leaving 14–48 mm to the edge instead of 95); the 550k trunk's
   **non-transfer** (D-71) with its cause identified as complex_b's 6.5 : 1
   handedness memorised as a steering prior; the **v2 retrain** (D-72) and its
   checkpoint chosen on cage-independence rather than reward; and the 26.08
   result — **18.05 m in one uninterrupted segment, no safety rule fired**.
3. **The gap table has a physical column, with its premise corrected.** The
   header now states that **the policy that deploys is not the policy that
   produced the verdict**, so the columns are not a like-for-like contrast. The
   2-D intervention figure is separated accordingly: **76.1 %** is the 550k
   trunk's, **3.0 %** is the deployed checkpoint's — against **3.4 %** measured
   on the car.
4. **The Chapter 8 transfer risk (T2) now has a first measurement, and it is
   favourable — not a closure.** It was declared before any hardware existed;
   selecting the checkpoint on cage-independence rather than reward put the
   two figures **four tenths of a percentage point** apart. **N = 1, in
   `monitoring`, unscored**: the physical campaign can still contradict it,
   and every place this appears says so. Recorded in Ch. 9 §9.4, in Ch. 12's
   H12 as a post-scriptum, in T2 of both future-work sections, and in the
   abstract.
5. **Two findings added to Ch. 12 that only hardware could produce.** **H13** — an
   assumption the simulator *inherited* is one the simulator cannot falsify, and
   this one sat in the path of a safety rule. **H14** — a class of defect that
   only appears with a vehicle in front of you: rules correct by specification
   with no defined *operational* behaviour, thresholds that cannot fire in the
   deployed configuration, and sensor failure modes that enter the cage's only
   speed input directly.
6. **`docs/11` §8.6 (new): the sim-to-real v2 run.** The first camera training in
   that document whose objective is transfer rather than the simulation verdict —
   the three-term split, the 2.5M-step run, the **1,650,000** checkpoint and its
   two selection criteria, the **I-8** retraction of every pre-23.08 nominal eval
   of the run, and SC-FRONT-07 changing *meaning* (regression test, no longer an
   OOD probe) for a mirror-invariant policy.
7. **Camera geometry reconciled across `docs/08`, `docs/09`, `docs/12` and
   Ch. 7.** The 90° stays as the **rendered** value every campaign was scored
   under; what is corrected is the claim that it was also the effective HFOV on
   hardware. Deployment **rectifies the real frame into the canonical model**
   rather than re-parameterising the estimator, and the A/B behind that is
   quoted where the estimator is specified. `docs/09` also records the capture
   rate 60 → 30. Ch. 7's mount pitch corrected 0.25 → 0.30 rad (M-6 Part B fitted
   the real mount at 0.3113 rad — essentially right).
8. **`verdict_phys` re-justified, not re-valued, in `docs/07` and `docs/16`.** It
   stays `tbd`, now for a narrower and statable reason: **the physical evidence
   exists and is not scored**. Two matrix rows are *qualified*: SR-004 is
   satisfied via a C-04 that **cannot fire at all** in the deployed physical
   configuration, and the policy the matrix scores is not the policy that drives.

9. **A status pass, applied after the first draft of these edits, separates two
   classes of physical evidence and labels them differently everywhere.**
   *Calibration measurements and structural findings* — a metrology against a
   pattern (M-6), a tape measurement (M-7), a regression over 5665 cycles
   (D-71), two controlled A/B pairs (rectification, ZED loop closure) and an
   arithmetic threshold comparison (C-04's dead zone) — **are results and do
   not depend on any campaign**. *Driving figures* — `|ey|`, distance, the
   C-06 rate, loop cadence, and the whole physical column of the gap table —
   come from **one run, in `monitoring`, outside the scenario protocol**, are
   labelled **PRELIMINAR / N=1**, and the physical campaign will supersede
   them. §9.3 is retitled *bring-up*, §9.5 becomes a *first reading* of
   divergences whose value is to direct the campaign, and §9.6 says the rung
   is **in progress** rather than executed.

### Rationale

The manuscript's honesty discipline cuts both ways. A chapter that says "no
physical evidence" when the car has driven is as wrong as one that reports
estimates as measurements — and the specific sentence "the effective HFOV is the
first thing to measure on hardware" was left standing in the submission draft
*after* that measurement had been taken and had come back wrong. Leaving it there
would have discarded the strongest argument the work has for why A5 makes the
physical rung obligatory.

The gap table needed the opposite correction: it claimed a like-for-like contrast
it can no longer support, because the deployed policy changed. Presenting the
columns side by side with the difference stated in the header is the honest form.

### Impact

* **No hazard, SR, cage rule, scenario, metric or verdict is added or re-valued.**
  `tools/sync_hazard_register.py` and `sync_safety_requirements.py` re-run: **12
  hazards, 14 SRs, no diff** in the generated CSVs.
* **`cage.yaml` untouched**; no version bump.
* **The D-67 reclassification is still repo-only** and was not written into the
  manuscript. Every manuscript edit here is a correction of a claim that Phase-5
  evidence falsified, or the population of a section the chapter itself marked as
  pending.
* **The page budget must be re-checked on the next DOCX build.** `draft_v5`'s body
  grew by roughly 50 lines, concentrated in Ch. 9; `tools/thesis_page_budget.py`
  has not been run (it needs Word COM).
* **The physical campaign is the immediate next work item**, and the manuscript
  now says so in Ch. 12's T2 rather than describing the physical rung as done.
  Ch. 9 §9.2.3 (the Isaac column) remains a skeleton, the hardware/track
  characterisation appendix is still owed, and the physical column of the gap
  table is explicitly provisional.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings**, re-run
after each document. Host-side suite unchanged at **720 passed** (the same 7
environment failures on the Windows host: no `cv2`, no `pgrep`, no
`ament_index_python`).

**Not verified:** no figure was regenerated, and the DOCX was not rebuilt.

---

## [27.08.2026] — The 26.08 afternoon runs analysed: both fixes work, the ZED hypothesis is discriminated, and the next lap is prepared to explain itself

**Document(s) affected:** `docs/17_physical_deployment.md` (§8.10 new, §9 new,
status header, §8.5/§8.6/§8.7 forward pointers), `docs/DECISIONS.md` (**D-73**,
**D-74** new; index table and status line), `docs/CHANGELOG.md`, `CLAUDE.md`,
`cage/logger.py`, `src/cobraflex_rl/cobraflex_rl/{run_io,cage_logger_node}.py`,
`src/cobraflex_rl/cobraflex_rl/{frame_capture,frame_capture_node}.py` (new),
`src/cobraflex_rl/cobraflex_rl/{cage_reset_proxy,cage_reset_proxy_node}.py` (new),
`src/cobraflex_rl/launch/deploy_cobraflex.launch.py`, `src/cobraflex_rl/setup.py`,
`src/cobraflex/launch/cobraflex_sensors.launch.xml`,
`src/cobraflex/config/zed_deploy_overrides.yaml`, `tools/run_physical_lap.sh` (new),
`policy/tests/{test_frame_capture,test_cage_reset_proxy,test_deploy_evidence_contract}.py` (new)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; **no gate re-scored, no simulation verdict touched**
**Author:** Samuel Sanchez

### Change

1. **§8.10 — the two runs committed on 26.08 but never described.**
   `track_v2_cpufix_20260826T095114Z` and `track_v2_noloopclosure_20260826T100450Z`
   entered the repo in `624fba1d` alongside §8, which therefore still ended §8.6
   with "the next work item" and §8.7 with "candidate fixes, none applied" —
   both overtaken by the same commit. Now analysed:
   * **the camera fix** (`lane_camera_capture_fps` 60 → 30) takes the delivered
     rate to **19.0 Hz at 96.5 %** of a core from 15.2 Hz at 134.3 %, and
     `/state_obs` to **9.84 Hz, worst gap 295 ms** (was 7.3 Hz, 995 ms);
   * **the ZED fix** (`zed_deploy_overrides.yaml`) takes single-frame pose steps
     over 50 mm from **116 to 0** in 509 s and the ekf's `vx` from 4.50 m/s to
     **0.213** against a commanded 0.22.
2. **§8.7's hypothesis is discriminated, not merely supported.** The two runs are
   a controlled A/B — same checkpoint, mode, rectification, 13 minutes apart,
   differing only in the override file.
3. **THE RESULT — 18.05 m in one uninterrupted 101 s segment**, no operator reset,
   `|ey|` median **18.7 mm** (max 98.7 against C-01's 160), `|epsi|` max 18.91°
   (against C-02's 25), `cycles_since_last_state` never above 0, and **C-06 the
   only rule touched: 3.4 % of moving cycles against the 3.0 % that chose this
   checkpoint in simulation**. The closest sim-to-hardware agreement in Phase 5,
   and a second confirmation that D-69's T2 did not materialise.
4. **The camera fix alone does not buy a lap.** `cpufix` had the best loop rate of
   the session (9.59 Hz, 4.5 % of cycles over 150 ms) and died in 16 s on a pose
   jump. What was ending runs was never the loop rate.
5. **It is still not a closed lap.** It stopped **2.11 m** from the start having
   turned 314° of 360°, on a **single 400 ms** `/perception_invalid` pulse with
   the car **27 mm** from the lane centre in the tightest curve
   (`kappa_ahead` 0.75 1/m) — the curve §8.8's departures happened in. C-05
   latched and `require_explicit_reset` kept it latched: 0.80 m in the remaining
   396 s. One glitch per lap is now the whole difference between a completed
   circuit and a stopped car.
6. **The bottleneck moved.** `/state_obs` holds 9.84 Hz while `/cage_status` runs
   at 8.68 Hz, i.e. **12 % of estimator cycles never produce a control cycle**.
   `/cage_status` is published from `cage_ros_node._on_raw_action`, so that is
   `rl_policy_node`'s 10 Hz timer slipping — CNN inference, not the camera.
7. **§9 — the next session's runbook**, and the four code changes that close the
   evidence gaps behind it:
   * `cage_logger_node platform:=physical` writes commit, `cage.yaml` hash,
     checkpoint hash, rectification hash and the deployed contract, **at start-up**
     as well as on close (`CageLogger.write_metadata`, atomic). The 18.08
     power-cycle left a run with a CSV and no metadata at all.
   * `frame_capture_node` (new) keeps the lane frames around each
     `/perception_invalid` or `/emergency` edge from a **RAM ring buffer** —
     ~20 MB per run at 26.08's event rate, against ~1.4 GB for the bag that
     crashed the Jetson on 18.08. This is §8.9's open item, asked for twice.
   * `cage_reset_proxy_node` (new, **`observe` by default, outside the cage**)
     logs or — with `auto` — issues the reset the operator made by hand five
     times, under the same three conditions held for 1 s, rate-limited and
     capped. `cage.yaml` is untouched and a test fails if
     `require_explicit_reset` is edited.
   * `tools/run_physical_lap.sh` (new) binds bag, CSV, frames and reset log to
     one run id and probes the **running** Layer-2 nodes for `capture_fps`, the
     ZED overrides, `pub_frame_rate`, `depth_mode` and whether the lidar is up,
     into `layer2.json`.
8. **Layer-2 CPU trimmed, and the big lever deliberately left alone (§9.3b).**
   A separate "RL-only sensors" launch was considered and rejected: only the
   **lidar** is unused by the RL chain — no cage rule reads a `LaserScan` and
   `ekf_hw.yaml` fuses `/zed/zed_node/odom` alone — and it is now one argument
   (`use_lidar`, default `true`, because `cobraflex_automatic` needs it). A
   second launch would duplicate three load-bearing ZED settings, including the
   `publish_tf:=false` that keeps the ekf the single owner of the `odom` edge.
   The CPU that matters is *inside* `zed_node` (51.1 % of a core, §8.6), so
   `zed_deploy_overrides.yaml` gains three publications with no subscriber:
   `general.pub_frame_rate` 15 → 5, `sensors.sensors_pub_rate` 100 → 30
   (`ekf_hw.yaml`'s `imu0` is commented out) and
   `pos_tracking.publish_3d_landmarks` → false. **`depth.depth_mode`
   `NEURAL_LIGHT` → `PERFORMANCE` and `depth_stabilization` 30 → 1 are written
   in as a COMMENTED block, not applied**: both change tracking quality, and the
   tracking pose is the cage's only source of speed (C-03/C-04/C-05). They need
   the same kind of on-car A/B that settled the loop closure.

### Rationale

Two track sessions have now ended on `/perception_invalid` events that cannot be
explained, because the frames were never kept and the provenance was never
written. §8.10's lap is 2.11 m short of the first complete circuit and the reason
it stopped is a 400 ms event with no evidence behind it. The next session is
therefore prepared around one requirement — **a run that explains itself** —
rather than around any new capability.

The reset proxy deliberately sits outside the cage. In simulation
`require_explicit_reset` is nearly inert — a scenario ends and the cage is
re-instantiated — so a bounded recovery inside C-05 would be a change to the
verified artefact whose entire effect is on hardware, validated by nothing. That
argument is D-74; the recovery question itself stays deferred.

### Impact

* **No gate, scenario, metric or SR is affected.** `verdict_phys` stays open;
  this is `monitoring`, on `near_secant` rather than the scored D-43 contract.
* **Two decisions taken, both deployment-side, neither re-valuing a gate.**
  **D-73** — the ZED loop closure is off in deployment: the cage reads velocity,
  so a drifting odometry beats a jumping one, and the price is that
  `/odometry/filtered` can no longer say whether a lap closed (which is exactly
  why §8.10 cannot). **D-74** — C-05's asymmetric exit is correct and stays; the
  missing operational reset path lives outside the cage, disabled by default, and
  **whether C-05 should ever gain a bounded recovery is deferred**, because
  simulation cannot validate such a change.
* **`cage.yaml` unchanged** — no version bump, no `[provisional]` tag resolved.
* Two items remain unverified by construction: the 30 fps capture rate under
  **motion** (the photometric check was made with the car stationary, so it cannot
  see motion blur), and C-04's dead zone, `v_max_curve_mps` 0.25 > the deployed
  0.22.
* **The Layer-2 savings are unquantified.** Every one of them is a publication
  with no subscriber, so the direction is not in doubt, but no `%CPU` was
  measured — and the bottleneck has moved anyway: `/state_obs` holds 9.84 Hz
  while `/cage_status` runs at 8.68 Hz, so the missing cycles are
  `rl_policy_node`'s inference timer, not Layer 2.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings**.

Host-side suite on the Windows host: **720 passed**, including 42 new
(`test_frame_capture` 9, `test_cage_reset_proxy` 9, `test_deploy_evidence_contract`
24 — the last parametrised over every `CONTRACT_KEYS` entry). The 7 failures and 5 collection errors are pre-existing environment gaps on
that host — no `cv2`, no `pgrep`, no `ament_index_python` — not regressions.

**Not verified, and it must be before the session:** none of the three new ROS
nodes has been launched. `frame_capture_node`, `cage_reset_proxy_node` and the
new launch wiring typecheck and their pure logic is tested, but no ROS 2 runtime
exists on the authoring host. Build and smoke-test them on the car —
`colcon build --symlink-install`, then a 60 s Layer-3 launch with the wheels off
the ground, checking that `frames/` and `capture_events.csv` appear on a
deliberate `/frame_capture_trigger` and that `reset_events.csv` records a
withheld reason.

---

## [26.08.2026] — The v2 policy drives the real circuit; the gate passes on real imagery; and four things stop the car, none of them the policy

**Document(s) affected:** `docs/17_physical_deployment.md` (§8 new, §7.2 blocker
cleared, §7.4 step 4 corrected, status header),
`experiments/sim/eval_gz2d/sim2real_probe_v2_circuit_{raw,rectified}.json` (new),
`experiments/physical/runs/preflight_20260826_*` (7 runs, new),
`experiments/physical/runs/track_v2_fulllap{,2,3}_20260826T*` (3 runs + 2 rosbags, new),
`tools/run_deploy_gate.sh` (header comment), `CLAUDE.md`
**Phase:** 5 (physical deployment)
**Gate context:** after G4; **no gate re-scored, no simulation verdict touched**
**Author:** Samuel Sanchez

### Change

1. **The 18.08 circuit frames were never lost.** They are on the **Jetson** —
   `experiments/physical/datasets/circuit_export/frames`, **1521 PNG, 439 MB**,
   temporally ordered — hidden from `git` by the `.gitignore` rule on
   `experiments/physical/datasets/*/frames/`. The 23.08 "frames are gone" note
   searched the compute host. §7.2's BLOCKER is cleared.
2. **The deployment gate PASSES against real imagery, both arms**: raw retention
   **1.29**, bias/swing 0.10; rectified **1.21**, bias/swing 0.17; floors 0.50 and
   1.00. Rectification restores right-turn share **23.2 % → 66.6 %** against the
   sim control arm's 66.4 %. The 23.08 prediction that the `k=4 history` arm would
   be valid on a temporally ordered recording is **confirmed**.
3. **`preflight_deploy.py` stage0/1/2 + lanecheck all PASS on the car.** Stage 2 in
   **enforcement** closes the 2026-08-05 review's item 1 on hardware: **235
   exact-zero `/cmd_vel` samples alongside 235 sub-deadband cage cycles**, until now
   asserted only by unit test.
4. **THE RESULT — the v2 policy drove the real circuit.** **19.28 m** covered (one
   perimeter's worth; complex_b is 19.22 m in simulation), `|ey|` median ≈ **9 mm**
   while moving, and **no safety rule fired at all** during the driving segments —
   only C-06, at 5–7 % of cycles against the 3.0 % that chose this checkpoint in
   simulation. D-69's T2 transfer risk did **not** materialise. D-71's 550k trunk
   did not transfer; this one does.
5. **Rectification is demonstrated on hardware** by a controlled A/B (same mode, same
   fit mode, sequential, car untouched): perception-invalid cycles **45 % → 5.5 %**,
   `ey` mean **−97.7 → +7.7 mm**, `ey` sd 104.5 → 27.8 mm, C-01 fires **102 → 0**.
6. **`heading_fit_mode` decides whether the car can drive at all** — and is invisible
   at rest. `joint_pair_quadratic`/1.6 (the launch default and the trunk's D-43
   contract): 1.08 m. `near_secant`/1.0: 14.45 m. Parked, both are quiet (`sd_epsi`
   0.25° vs 0.80°). D-71 §3's method lesson recurring.
7. **C-05 has no operational story on hardware.** A **120 ms** perception glitch, from
   which the estimator recovered by itself, stops the car permanently: the
   `require_explicit_reset` asymmetric exit is correct for a simulated episode but
   there is nobody on a vehicle to send `/cage_reset`. Confirmed live — `/emergency`
   true while `/perception_invalid` was already false. Lap 3 was driven with **five
   operator resets**, each with perception healthy, no C-01…C-04 active and `v = 0`.
8. **The camera cannot feed the loop, and it is upstream of (7).** 101 `no camera
   frame` warnings in one run; loop at **7.3 Hz** against the trained 10 Hz, gaps p99
   579 ms and **max 995 ms** = 171 mm travelled open-loop at 0.172 m/s, more than
   C-01's whole threshold. Cause is CPU: load 5.49 on 6 cores **with layer 3 not
   running** (`csi_camera_node` 54 %, `rviz2` 52 %, `zed_node` 51 %). Killing `rviz2`
   took the loop to **9.5 Hz** and lengthened every segment.
9. **The ZED pose-jump hazard is measured, not inferred.** A **3621.8 mm displacement
   in one frame** (17.81 m/s implied) drove `/odometry/filtered` `vx` to **−4.03 m/s**;
   an earlier spike put the cage's speed at **5.479 m/s**, 25× the contract, firing
   C-04 → C-03 → C-05. `ekf_hw.yaml` fuses the ZED's pose and not its twist, so
   velocity is a derivative of a signal that teleports — exactly what
   `cobraflex_sensors.launch.xml` has warned since 06.08. Restarting Layer 2 delays
   but does not remove it.
10. **C-04's dead zone now has a physical consequence.** `v_max_curve_mps` 0.25 vs a
    deployed `max_speed_mps` 0.22 means **C-04 can never fire**. D-69's finding (ii)
    recorded this as untested coverage; on the real circuit the vehicle enters its
    tightest curve at full contract speed with no cage-side speed protection — and
    that curve, the re-entry to the straight, is where it left the lane **twice**,
    with C-02 and C-03 firing together at `ey −118.5 mm` / `epsi −25.60°`. First
    genuine safety intervention of the session.

### Rationale

§7.2 had declared the deployment un-authorisable for want of real imagery. Locating
the frames on the correct host made the gate runnable, the gate passed, and the
staged preflight then authorised driving. Everything after that is what the car
itself reported.

### Impact

* **No gate is re-scored and no simulation verdict is touched.** The verdict of
  record stays the 550k trunk's 1890-run campaign (D-67/D-69); this is Phase-5
  posterior evidence, the same posture as D-71.
* **`verdict_phys` stays open.** 19.28 m with five operator resets and a lane
  departure is not a scored scenario, and must not be reported as a clean lap.
* **Three open decisions, none acted on.** C-05's behaviour on hardware against a
  transient recoverable glitch (candidate D-NN — **taken 27.08.2026 as D-74**:
  the operator reset path, implemented outside the cage); whether the deployed
  `heading_fit_mode` default moves off the scored D-43 contract; and whether
  `v_max_curve_mps` drops below the deployed speed so C-04 can act.
* **Next work item is CPU headroom** (item 8), because it is upstream of the
  perception glitches and confounds the curve diagnosis: lowering `max_speed_mps`
  would help curvature, starvation and M-7's pairing collapse simultaneously and so
  cannot discriminate between them. Fix starvation first, then vary speed.
* **Housekeeping surfaced, not fixed**: `cage_logger_node` writes no reproducibility
  metadata (pre-existing, the 18.08 run is identical), and two contradictory D-43
  preflights for the 1650k checkpoint sit side by side — the BLOCKED one is a trace
  retracted by I-8.

### Verification

`pytest` **763 passed**. `python tools/check_traceability.py` — All checks PASSED,
0 warnings. The gate, the four preflight stages and all three track runs were
**executed on the car**, not asserted; provenance (commit, cage-YAML, checkpoint and
calibration hashes) is recorded at the head of docs/17 §8, and the checkpoint hash
matches the one the compute host recorded for the same file.

---

## [23.08.2026] — The v2 run finished at 2.5M; the checkpoint is chosen on transfer and cage-independence, two more failures are documented, and the deployment gate is one command from ready

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`tools/run_deploy_gate.sh` (new), `policy/tests/test_eval_policy_2d.py`,
`experiments/sim/eval_gz2d/d43_preflight_v2_*.json`,
`experiments/sim/campaign_v2/run_campaign_v2.sh` (new),
`experiments/sim/training/ppo_gz2d_sim2real_v2_2024/raw_logs/INCIDENTS.md` (I-7, I-8)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored, no sim verdict touched
**Author:** Samuel Sanchez

### Change

1. **The run completed**: 2,500,544 steps, `status: completed`, 100 checkpoints across
   both segments. Reward ended in its healthy band (~587) with the cage latent
   (C-01/C-03/C-04 at zero, emergencies 0.0008) and `mirror_rate` **0.527** — the
   handedness balance the run exists for, measured rather than assumed.
2. **Checkpoint of record: 1,650,000**, chosen on transfer and cage-independence, not
   reward. Best transfer statistics of the run on the deployment arm (r² **0.440**,
   bias/swing 0.10, right-turn share 62.1 %) and it intervenes on **3.0 %** of nominal
   steps against the reward peak's **35.0 %**. That second number is the decisive one:
   D-69 named the C-06 coupling to `delta_max_steering_per_cycle` a physical-transfer
   risk (T2), so the reward peak's tighter clean-sim tracking (9.6 mm against 19.1) is
   bought with twelve times the cage dependence.
3. **D-43 preflight PASSES** on 325k, 1650k and 2000k (max centred ey error 18–21 mm
   against a 50 mm threshold), which is what authorises a campaign.
4. **I-7 — a third orphaned Gazebo**, alive 2 d 14 h through `shutdown_on_train_exit`.
   The mechanism reduces but does not eliminate the leak; anything starting Gazebo here
   should check first.
5. **I-8 — every nominal eval of this run measured the randomisation, not the policy.**
   `eval_policy` forces `domain_randomization.enabled = False` for evaluation and always
   has; the two blocks added on 20.08 were **not added to that rule**. So seven nominal
   drives ran with the mirror flipped on ~half their episodes and the camera mount
   perturbed on all of them, and the fail-closed D-43 preflight duly reported a **58 mm**
   centred-ey error that was the injected ±10 % height perturbation. The |ey| figures
   from those runs are **retracted**. Fixed, with the semantic reason recorded — a
   mirrored episode on a perturbed camera is not the world an SC-* YAML describes — and
   two tests.
6. **The deployment gate now runs end to end**, which it never had: the repo noted
   `sim2real_probe`'s PASS branch was "asserted by unit test, not by a driven car". A
   surrogate dataset in `record_lane_dataset`'s exact on-disk layout (420 frames +
   labels.csv) exercised all three stages of `tools/run_deploy_gate.sh`, including the
   previously untested `--real` path through the selector, and **three checkpoints
   returned PASS**.
7. **On the gate's own criteria the v2 policy fixes two of the three that killed the
   trunk.** Scored on the surrogate's `repeat-stacked` arm — the meaningful one for an
   unordered pose set — the trunk fails all three (retention 15 %, bias/swing **4.03**,
   right **1.9 %**) exactly as D-71 recorded, while 1650k reads 107 % / **0.04** /
   **48.8 %**. The two structural criteria are robust to the stacking caveat below;
   swing retention is the one still in question.
8. **A caveat that bounds every surrogate number**: the gate scores the `k=4 history`
   arm, which stacks four *consecutive* frames as `rl_policy_node` does. The surrogate
   is an unordered pose set, so that arm stacks four unrelated views and reads as noise —
   its BLOCKED verdicts are an artefact of the dataset, not a finding. The real 18.08
   recording is temporally ordered and the arm will be valid there.
9. **`tools/run_deploy_gate.sh`** reduces the outstanding work to one command once the
   frames exist, and carries the three recovery routes plus the requirement that the
   frames be in temporal order and the pass deliberately weaving.
10. **The 27-scenario campaign is running** on 1650k (`experiments/sim/campaign_v2/`),
    SC-PERT-03 excluded exactly as in `campaign_2d_ppo550k` (it needs a two-arm manifest;
    D-64 closed it), behind the same `flock` guard.

### Verification

`pytest` **762 passed, 1 skipped**. `python tools/check_traceability.py` — All checks
PASSED, 0 warnings. Training completion, the D-43 preflights, the nominal re-runs and
the full gate script were all **executed**, not asserted.

**Still blocked, and not resolvable from this host**: the 18.08 circuit frames are gone
(a filesystem-wide search found only M-6 checkerboard views and a Gazebo bag), so the
gate has not been run against real imagery and **no checkpoint is authorised for the
track**. Rectification has still never run on the car.

---

## [21.08.2026] — The v2 run was killed at 620k by operator error, not by a fault; the hazard is guarded, the run is resumed, and the reward decline is the circuit's known shape

**Document(s) affected:** `tools/run_campaign.py` (concurrency guard),
`tools/select_sim2real_checkpoint.py` (ranking metric corrected),
`src/cobraflex_rl/config/train_ppo_camera_2d_sim2real_v2_resume.yaml` (new),
`policy/tests/test_run_campaign.py`, `tools/tests/test_select_sim2real_checkpoint.py`,
`experiments/sim/training/ppo_gz2d_sim2real_v2_2024/raw_logs/INCIDENTS.md` (I-1…I-6)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored, no sim verdict touched
**Author:** Samuel Sanchez

### Change

1. **The run was killed by the operator at 620,544 steps (24.8 %).** A single-scenario
   `run_campaign.py` was started beside the running training to answer which checkpoint
   drives. The campaign reaps orphaned Gazebo servers at start-up with
   `pkill -9 -f "gz sim.*cobraflex/share/cobraflex/worlds"`, and a training's Gazebo runs
   the same world from the same install path, so the pattern matched it: `gazebo` exit
   **-9**, `train_ppo` exit **-2** with a traceback inside `env.step`. `GZ_PARTITION`
   isolates topics, not processes. `_reap_orphan_gazebo`'s own docstring states the
   assumption this violated. **Cost: ~20k steps**; all 24 checkpoints intact.
2. **Guarded.** `run_campaign.py` refuses to start while a trainer is alive, verified by
   `comm` and never by command line, with `--force-beside-training` as the explicit
   escape. A test pins that the reaper's pattern *does* match a training cmdline, so the
   hazard cannot be quietly forgotten.
3. **A second, chained error, also fixed.** The first cut of that guard used `pgrep -f`,
   which matches any shell whose command-line text contains the pattern — it found three
   (a health sampler, a monitor, and the checking command itself) and blocked three runs
   with nothing training. `reap_sim.sh` documents this trap and the 29.07 incident was
   misdiagnosed by it. The same defect was in this run's health sampler and monitor,
   which is why the monitor reported `ERROR SIGNATURE` instead of `TRAINER GONE`: it saw
   itself. `health.csv` rows after 08:03 are annotated in-file as invalid.
4. **Resumed** as `ppo_gz2d_sim2real_v2_2024_r2` from the 600k checkpoint and its paired
   VecNormalize. `total_timesteps: 1_900_000` lands on the original 2.5M
   (`reset_num_timesteps=False`). The learning rate **continues the parent schedule
   rather than restarting it** — resuming at the parent's `3e-4` would restart the anneal
   at full rate, in the direction I-3 identified as harmful. `2.424e-4` with a `0.2475`
   floor over 1.9M reproduces the remaining segment exactly, slope included
   (−9.6e-11 per step in both).
5. **The reward decline is the circuit's known shape, not this run's defect.**
   `ep_rew_mean` peaked **872 @ 330k** and fell to 124 by 620k. `ppo_newcam_complex_b_2024`
   on the same circuit peaked **822.9 @ ~297k** and decayed to 114 by 662k — it was
   stopped by hand and its **peak rescued**, which is how the 297k E-main exists. The
   mechanisms differ (that run's `value_loss` was 0.007–0.012, "tiny all run"; this one
   holds 0.055–0.088 with `explained_variance` rising to 0.68), so the shared shape is
   more likely a property of complex_b than of either run's settings.
6. **The probe metric moved the other way as the reward fell**, which is the point of the
   run. On the deployment arm, `r²` — the share of steering variance the lane explains —
   rose from 0.16 at the reward peak to **0.406** at its lowest, and the right-turn share
   to **80.7 %**, while the canonical arm collapsed (0.160 → 0.044): the policy is
   specialising into the hall photometry, 75 % of its episodes.
7. **Headline, and it is structural rather than magnitude-based.** On the deployment arm
   the run's checkpoints read `bias_over_swing` **0.07–1.10** and right-turn share
   **29–72 %**, against **1.44–1.94** / **6–14 %** for every checkpoint of the 19.08
   fine-tune and **12.9–19.2** / **0.8 %** for the trunk as deployed on 18.08. Those are
   exactly the two statistics D-71 identified as the failure. **The handedness term is
   fixed.**
8. **`select_sim2real_checkpoint.py`'s ranking was wrong, found by running it.** Three of
   its top five were ranked by "retention" of 304 %, 231 % and 184 % — impossible by the
   metric's own definition — because retention divides by a canonical arm that had
   collapsed. It now ranks by absolute swing on the deployment arm behind a
   `MIN_CANONICAL_SWING` floor. The floor does not fix everything and the tool says so:
   `r_squared` was tested as a discriminator and **does not separate** an untrained noisy
   policy from a lane-responsive one (0.282 at 25k against 0.306 at 100k). The tool ranks
   the *bias structure*, not the response *strength*.
9. **Three candidates drove SC-NOM-01 with 0 emergencies**: 325k (|ey| 11.8 mm), **450k
   (9.8 mm)**, 525k (13.3 mm). The I-5 hypothesis that late checkpoints "respond better
   and drive worse" is **not supported** at that 30 s horizon; a 4400-step repeat is
   outstanding and can only run once training finishes, which the new guard enforces.

10. **The selector gained the filter its prose warning could not replace.** Fixing the
    retention artefact (item 8) left the table still ranking the **25k** checkpoint
    first — an almost untrained policy whose steering is noise, not lane response.
    `r_squared` was tested as the discriminator and rejected on measurement: 0.282 at
    25k against 0.306 at 100k and 0.350 at 875k, no separation. The discriminator is
    not in the probe at all — it is whether the policy could finish an episode, which
    the run's own `learning_curve.csv` already records. `--learning-curve` (repeatable,
    since a resumed run writes one curve per segment) now excludes checkpoints from an
    era whose `ep_len_mean` was under 300 steps, the SC-NOM-01 horizon. This is **not**
    ranking by reward — the ordering still never reads it; it only excludes eras when
    the policy was not driving. An absent datum is explicitly not a rejection.

### Verification

`pytest` **760 passed, 1 skipped** (15 new since 20.08: 3 campaign concurrency guard,
5 selector ranking incl. the 304 % artefact and the resumed-series continuity, 7 for
the training-ep_len driving filter).
`python tools/check_traceability.py` — All checks PASSED, 0 warnings.
The resume was **verified running**, not assumed: `Resumed PPO from …_600000_steps.zip at
600000 steps`, one `gz` server, trainer RSS 2044 MB.

Not verified: the run has not finished; no checkpoint has been scored with
`sim2real_probe` against the physical frames, which are still **not on this host**; the
4400-step nominal repeat has not been run; and rectification has still never run on the car.

---

## [20.08.2026] — The 19.08 fine-tune analysed: it worked and was not enough, the term that failed on the track is the track's own handedness, and the geometric term is not negligible after all

**Document(s) affected:** `docs/DECISIONS.md` (D-72; D-71 index row, previously missing),
`docs/05_scenario_library.md` (SC-FRONT-07 note), `docs/08_odd_specification.md` (SC-FRONT-07 row),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/geometric_domain_randomization.py` (new),
`src/cobraflex_rl/cobraflex_rl/camera_geometry.py`,
`src/cobraflex_rl/cobraflex_rl/camera_pipeline.py`,
`src/cobraflex_rl/cobraflex_rl/visual_domain_randomization.py`,
`src/cobraflex_rl/cobraflex_rl/training_metrics.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/rl_policy_node.py`,
`src/cobraflex_rl/launch/deploy_cobraflex.launch.py`,
`src/cobraflex_rl/config/train_ppo_camera_2d_sim2real_v2.yaml` (new),
`policy/tests/` (5 new files, 79 new tests)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored, no sim verdict touched
**Author:** Samuel Sanchez

### Change

The 19.08 fine-tune ran **284,672 of its 400,000 steps** (stopped manually; `status` in its
metadata reads `failed`, meaning interrupted). Everything below is its analysis and what follows
from it. **Nothing here has been run on the car**, and the analysis arms are a *surrogate*: the
1521 physical frames are not on the simulation host — only `labels.csv` survives under
`experiments/physical/datasets/circuit_export/` — so the checkpoints were scored with
`sim2real_probe`'s own scorer against the 420-frame Gazebo pose set pushed into the hall's
photometry. `sim2real_probe` itself, the actual gate, has **not** been run on these checkpoints.

1. **The fine-tune worked, monotonically, and did not finish the job.** Swing retention at the
   measured hall point went **2 % (trunk) → 28 %** (best checkpoint, 800k), right-turn share
   **1 % → 14 %**. The gate wants 50 % / 10 % / bias-swing ≤ 1.0 — one of three. Its reward is a U
   (trough 421 at ~697k, 816 by 825k, still rising), so it was stopped mid-recovery.
2. **What failed on the track is the track.** The lane-independent bias is **+0.122 at the trunk
   and +0.124 after 285k steps**; only the swing around it grew. complex_b driven counter-clockwise
   is **6.5:1 left-dominant** (`generate_complex_track.py`'s own figure: ~13 m of driven left arc
   against ~2 m right per lap), and the fine-tune's action log held mean raw steering at
   **+0.112…+0.120, flat throughout**. Appearance randomisation cannot reach this.
3. **The geometric term is material, contradicting the 19.08 reading.** That reading (rectifying
   changes 0.097 → 0.090) was taken on a policy already at zero response. On policies that still
   respond, the measured M-6 lens costs the **trunk a third of its swing (0.363 → 0.232)**, and on
   the compound photometric+geometric arm the fine-tuned policy reads **0.030 raw vs 0.081
   rectified** — the latter exactly its photometric-only figure. Rectification is worth ~2.7×, and
   after it photometry is again the only binding term.
4. **The estimator is not the weak link.** Under the photometric range it pairs on **100 % of
   frames at every level** with rising confidence (0.637 → 0.786); under the full mount-pose range
   it also pairs on 100 %. So the C-02/C-03/C-05 activity during the fine-tune — absent from the
   trunk's own training — was **the policy driving worse, not perception misreading**. The cage
   stays in enforcement for the next run on that evidence.
5. **New: mirror augmentation** (`mirror_augmentation` in the training YAML, inert by default).
   Per-episode coin flip; the frame is flipped at the one point the policy observation and the
   cage's CV frame share, and the actuated steering is negated back at the actuator. Exact: the
   D-43 estimator is **antisymmetric to 0.075 mm in `ey` and 0.165° in `epsi` over 420 frames**
   (420/420 pairing either way), and end to end through the shipped CV controller an episode and
   its mirror issue the same physical command to within **0.0032**. The reward needs no change —
   it already reads `abs(ey)` and `abs(steer delta)`. No second world is loaded: the flipV world
   exists but the Gazebo trainer is single-circuit and a per-episode reload is not free.
6. **New: `geometric_domain_randomization`** (inert by default) — mount pitch ±1.5° and height
   ±10 %, plus an opt-in raw-lens minority. The split of labour was measured, not assumed:
   **height** carries the metric residual (ey ratio 1.105 / 0.917, lane width 297 / 243 mm, which
   brackets the +8…+30 mm session-dependent error surviving rectification) while **pitch** moves
   the horizon and look-ahead band and barely touches scale (0.983 / 1.006). `camera_geometry`
   gains `distortion_maps_to_calibration` (the stated inverse of the rectifier) and
   `ground_plane_homography` (exact on the road plane, and only there).
7. **The photometric base draw gains a second band.** 75 % of the mass now lands in [0.55, 1.00],
   the measured hall, and 25 % in [0.00, 0.15] so the Gazebo render — where every scored campaign
   still evaluates — stays in distribution. A config without the new field draws the identical
   numbers and leaves the generator in the identical state, pinned by a test against a
   transcription of the previous algorithm.
8. **Deployment gap closed: `rl_policy_node` now rectifies.** Only the estimator did, so a
   rectified deployment would have had the cage arbitrating a canonical world while the CNN saw
   the raw 160° lens. The launch file exposes **one** `rectify_calibration` argument wired to both
   nodes so they cannot be configured apart. Empty by default.
9. **New config `train_ppo_camera_2d_sim2real_v2.yaml`** — from scratch, 2.5M steps, seed 2024. It
   differs from the trunk config in exactly nine keys (the four changes above plus budget, `viz`
   and `model_path`), which a contract test asserts. `ent_coef` 0.01 → 0.02 and a new
   `linear_floor` LR schedule answer the fine-tune's PPO health: action std fell 0.054 → 0.024
   monotonically, `approx_kl` exceeded `target_kl` on 13.7 % of updates, `explained_variance` was
   negative on 23.5 % of log points.
10. **Run evidence.** `metadata.json` now records the `geometric_randomization` and
    `mirror_augmentation` blocks (it recorded only the photometric one), and `learning_curve.csv`
    gains a `mirror_rate` column — the run's own evidence that it got the handedness balance its
    config claims, rather than the config's assertion that it should.
11. **A correction tried, measured and rejected.** The flip maps `u → W-1-u`, leaving the mirrored
    optical centre at 319.5 against `cx = 320` — a *constant* 0.075 mm offset. The exact fix
    (shift one column) is exact on 95 % of frames but must fill the vacated column, and replicating
    the opposite edge tipped the estimator's line pairing on 10 of 420 frames, worst 223 mm, one
    with an inverted sign. The naive flip ships and `camera_pipeline.mirror_frame` records why.
12. **SC-FRONT-07 changes meaning.** Its premise is geometry OOD via reversed curve handedness; a
    mirror-invariant policy handles that by construction, so for any policy from this run it is an
    in-distribution regression test. GE4-V2's frozen result is unaffected.
13. **New `tools/select_sim2real_checkpoint.py`** — the run leaves 100 checkpoints and the reward
    does not order them (D-66's reward peak was its worst driving candidate; the fine-tune's reward
    recovered monotonically across its last 150k while the sampled steering swing kept shrinking).
    It scores each checkpoint's lane response through four conditions — `canonical`, `hall`,
    `hall+lens`, `hall+lens+rect` — using `sim2real_probe`'s own scorer so the numbers cannot drift
    from the gate, and ranks on the deployment arm. Validated against the 19.08 fine-tune's 11
    checkpoints, where it reproduces the manual analysis exactly (800k best at 24 % retention,
    **0 of 11 clearing the floors**) and exits 2. Without `--real` it prints, and this is the
    point, that these are surrogate arms which cannot authorise a deployment.
14. **`docs/17` §7 — the v2 deployment runbook**, written before the run finished and marked as
    procedure rather than result. It records the **blocker**: the 18.08 circuit recording's frames
    are gone from the simulation host (only `labels.csv` survives; `find experiments/physical -name
    '*.png'` returns nothing), so `sim2real_probe` — the gate — cannot be run at all until they are
    recovered from the Jetson, re-exported from the bag, or re-recorded as a deliberately weaving
    pass. §7.5 states in advance what would falsify the exercise, so the track session is a test
    and not a demonstration.

### Verification

`pytest` **745 passed, 1 skipped** (94 new: 21 geometric DR, 12 mirror augmentation incl. an
end-to-end loop-sign check through the real CV controller on 105 Gazebo frames, 15 checkpoint
selector, 10 v2 config contract, 9 LR schedule, 8 deploy-rectification contract, 9 photometric
focus band, 3 `mirror_frame`, 2 `mirror_rate`, plus schema updates).
`python tools/check_traceability.py` — **All checks PASSED, 0 warnings**; no ID added or removed.
**Run in Gazebo, not just typechecked:** `train_lane.launch.py` with the shipped v2 config
(budget cut to 2048 steps) completed a full PPO update end to end, wrote its run directory, and
recorded `mirror_rate` 0.56 / 0.35 across its two rollouts with both new blocks in `metadata.json`.

**The 2.5M run was launched at 11:46 on 20.08** (`experiments/sim/training/ppo_gz2d_sim2real_v2_2024/`),
detached, with a 60 s health sampler writing `raw_logs/health.csv` — RSS, swap, GPU, orphan-Gazebo
count and timestep. That sampler exists because the 19.08 fine-tune took the machine down after
~8 h and the cause was never established (no root for dmesg/journal, no OOM trace, evidence gone by
the time anyone looked); 2.5M steps is ~10× that exposure, so the data is collected up front rather
than reconstructed afterwards.

Not verified, and stated as such: the run has not finished; no checkpoint has been scored with
`sim2real_probe` against the physical frames, which are **not on this host**; rectification has
still never run on the car; and the four training changes are deliberately simultaneous, so this
run cannot attribute an outcome to any one of them.

---

## [19.08.2026 · later] — The sim camera had lost its pitch since 10.08; the measured extrinsics become the authority and all five URDF variants are unified

**Document(s) affected:** `src/cobraflex/urdf/my_robot_gazebo_mesh.urdf`,
`src/cobraflex/urdf/my_robot_mesh.urdf`, `src/cobraflex/urdf/my_robot_gazebo.urdf`,
`src/cobraflex/urdf/my_robot_basic.urdf`, `src/cobraflex/urdf/cobraflex_isaac.urdf`
(regenerated), `src/cobraflex_rl/cobraflex_rl/camera_geometry.py`,
`policy/tests/test_camera_geometry.py`
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored, no recorded result restated
**Author:** Samuel Sanchez

### Change

1. **A latent regression, found while transferring the new printed-model
   geometry.** Commit `a44ed5f0` (10.08, an `.stl` commit) dropped
   `rpy="0 0.30 0"` from `camera_joint_lane` in `my_robot_gazebo_mesh.urdf` —
   the variant `gazebo_mesh.launch.py` loads, i.e. the one every Gazebo training
   and evaluation uses. The other four variants and `camera_geometry` kept
   0.30 rad. Nine days passed unnoticed because no Gazebo run happened in
   between. A captured frame from the live sim measures it: **horizon at row 182
   against row 83** on a trunk-era frame, asphalt down from 50.2 % of the frame
   to 29.1 %. With zero pitch the estimator's near scan row (X = 0.15 m) maps to
   **row 364 of a 360-row image** — the near field C-01 acts on is not in frame.
2. **The direction of authority is reversed.** `camera_geometry`'s extrinsics
   were derived from a hand-picked URDF mount (0.30 rad, 0.07725 m) that nobody
   had measured — sim and code agreed with each other and with nothing else, the
   same circular agreement M-6 found for HFOV. They are now the **measured** pair
   (M-6: pitch 0.31132 rad, height 0.07794 m, fitted jointly over 17 tape marks,
   residual rms 0.485 px) and the URDF chain is solved to land on them:
   `camera_joint_lane` z = 0.07794 − (0.03725 + 0.075) = −0.03431.
3. **All five URDF variants unified**, with the 19.08 printed-model values
   carried across: the mesh visual origins (`body_link` 0.028 −0.059 0,
   `lidar_link` −0.003 −0.078 −0.03) to the mesh-bearing variants only, and the
   `body_joint` −0.005 offset plus the lane-camera joint to all of them. That
   also closes the drift `camera_geometry` used to carry as a NOTE (the non-mesh
   variants sat 1 cm higher). `cobraflex_isaac.urdf` was **regenerated** with
   `tools/build_isaac_urdf.py` rather than hand-edited; the 3.5 kg hand-patched
   mass budget survives untouched (it lives in the source xacro), and the file is
   now byte-identical to the generator's output — which is what the stale
   hand-patch note in it asked for. Its diff is large only because the generator
   emits LF where the hand-patched file was CRLF; five lines of content changed.
4. **The URDF↔code contract is now tested.** `test_camera_geometry.py` parses the
   kinematic chain out of all five variants and asserts each one lands on
   `DEFAULT_CAMERA_{HEIGHT_M,PITCH_RAD}`, plus that the five agree with each
   other. Pure text and arithmetic, no ROS. This is the test whose absence let
   the 10.08 regression live for nine days.

### Rationale

Transferring the printed-model values was the request; the pitch loss was found
on the way and outranks it. The user's ruling settles which numbers win: the
track measurements are the real geometry, the simulation used hand-picked ones.

### Impact

* **The fine-tune must not be launched against the broken geometry.** The 550k
  trunk trained at 0.30 / 0.07725, i.e. 0.65° and 0.7 mm from the measured pair —
  an 0.89 % lateral scale change and a 4 px horizon shift, far inside the
  0.15 rad spawn heading perturbation it already trains under, so a continuation
  is sound. A continuation against pitch 0 would not have been.
* Verified on the live sim after rebuilding: horizon back to **row 79** against a
  model prediction of 77, asphalt back to **50.2 %** — the trunk-era value.
* `tools/validate_cv_estimator.py` re-run against the ground-truth oracle on
  complex_b (reduced grid, 18 clean samples): **detection 1.0**, `ey` bias
  +6.5 mm, **MAE 8.0 mm**, p95 15.5 mm. The `epsi` bias of −0.14 rad is the
  documented curvature over-read on a tight circuit with the T3 gate disabled
  (D-62), not a new effect — the grid ran with estimator defaults, while the
  trunk's training config enables `heading_temporal_window: 4`. **No paired
  comparison against the trunk's old extrinsics was run**, so no accuracy
  improvement is claimed; only that the corrected geometry yields a healthy
  estimator.
* **Isaac needs a re-import.** `cobraflex_isaac/payloads/Physics/physics.usda`
  was hand-patched and the URDF geometry has now moved; re-import to regenerate
  it before any further Isaac work. Not done here — Isaac is posterior work.
* Not modelled, and stated: the mount sits 1.5 mm off the vehicle centreline
  (`y = -0.0015`), which a pitch-only IPM reads as a constant 1.5 mm `ey` bias —
  an order of magnitude under the estimator's own 13.2 mm re-placement
  repeatability (M-7 §4).

### Verification

`pytest` 657 passed (6 new URDF-contract tests). `python tools/check_traceability.py`
— unchanged, no ID added or removed. Live-sim frame capture and the reduced
oracle grid above; both run on the Ubuntu host, both reaped clean.

---

## [19.08.2026] — The sim-to-real gap is photometric, not geometric: reproduced offline, an offline gate to catch it, and the fine-tune that closes it

**Document(s) affected:** `docs/17_physical_deployment.md` (§1b, §2 item 1),
`src/cobraflex_rl/cobraflex_rl/visual_degradation.py`,
`src/cobraflex_rl/cobraflex_rl/visual_domain_randomization.py`,
`src/cobraflex_rl/cobraflex_rl/camera_geometry.py`,
`src/cobraflex_rl/cobraflex_rl/cv_lane_estimator_node.py`,
`tools/sim2real_probe.py` (new), `tools/README.md`,
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/config/train_ppo_camera_2d_sim2real_ft.yaml` (new),
`policy/tests/test_sim2real_finetune_config.py` (new),
`policy/tests/test_visual_degradation.py`,
`policy/tests/test_visual_degradation_eval_modes.py`,
`policy/tests/test_visual_domain_randomization.py`,
`policy/tests/test_camera_geometry.py`, `tools/tests/test_sim2real_probe.py` (new)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored, no sim verdict touched
**Author:** Samuel Sanchez

### Change

All of it derived on the simulation host from the 18.08 recordings — **nothing here
has been run on the car.**

1. **The M-7 §4 under-read is reproduced by a forward model** (render the real lane
   geometry through the M-6 camera, feed the shipped estimator): slope **0.674**
   against the tape's 0.68–0.83, C-01 firing at a true **239 mm** against the
   measured 207–241. The control arm (render through the assumed model) reads
   0.997, so the model is sound. M-6's "undistort, do not just re-parameterise" is
   now a measurement: correcting `fx`/`cx`/`cy` **without** undistorting gives
   **0.644** — worse — while undistorting into the canonical camera gives **0.998**
   with lane width 249.9 ± 1.5 mm against a 250 mm ruler.
2. **`camera_geometry.rectification_maps_from_calibration`** builds those maps,
   reading `M6_results.json` directly so the intrinsics keep one authority and are
   never copied into code. `cv_lane_estimator_node` gains `rectify_calibration`,
   `camera_pitch_rad` and `camera_height_m` — **all inert by default**, so every
   Gazebo path stays bit-identical and the physical path opts in explicitly.
3. **The trunk policy's failure is photometric.** Single-factor ablation on Gazebo
   frames, where the policy works (steering swing 0.363, right turns 48.6 %):
   pasting the entire workshop above the horizon changes **nothing** (0.352,
   47.9 %); matching the frames' grey statistics to the real ones collapses it to
   swing **0.004**, bias +0.134, right turns **0.0 %** — the deployed symptom,
   reproduced in simulation from one transform. Calibrated cause: Gazebo renders
   the road at grey **27** and the markings at 197; the physical circuit reads
   **106** and 209 across three independent sessions (contrast ratio 7.3× vs 2.0×).
4. **New DR mode `low_contrast`** (lifted black level + compressed range) covers
   it. `MODES` stays the frozen H-10 trio so every past run's DR draw is
   reproducible; the new `TRAINABLE_MODES` is what training may draw from, and the
   eval-only stressors stay excluded. At `level≈0.75` it lands on the measured
   hall, i.e. inside — not at the edge of — the standard `(0.2, 1.0)` draw. Opt in
   per run via `domain_randomization.modes` in the training YAML.
5. **`tools/sim2real_probe.py`** scores a checkpoint's lane response on recorded
   physical frames against the Gazebo control arm and fails closed. On the 550k
   trunk it returns BLOCKED for three independent reasons from recorded data alone.
6. **M-7 §4b's open `epsi` decision is answered with data.** On rectified frames
   `joint_pair_quadratic`/1.6 drops from sd 14.24° / 8.5 % past C-02 to
   10.61° / 1.6 %, and `near_secant`/1.0 is both unbiased (mean −0.03°) and
   cleanest (sd 4.94°, 0.7 %). The as-shipped column reproduces M-7's live table
   to 0.05°, which is what validates the offline replay.
7. **docs/17's HFOV claim is corrected** (§1b, §2 item 1): "real frames are ~24 %
   narrower" is wrong in sign. 77.89° is the pinhole-equivalent; actual coverage is
   94.6° × 52.2°, *wider* than the 90° trained on — consistent with the IMX219-160
   the JetRacer kit ships (the standard 79.3°-diagonal optic would give ~50° in
   this crop mode, off by 1.88×).
8. **The DR sampler gains an operating-point term.** `low_contrast` must not go in
   `modes`: the sampler draws one stressor per episode, so a four-mode list at
   `p_degrade 0.5` would show the policy the physical track's photometry in ~12 %
   of episodes — as if a mid-grey floor were a rare event rather than the constant
   condition M-7 measured. `DegradationSpec` now carries an optional base term
   drawn on its own schedule and applied *before* the stressor (the physical
   order: the camera sees a mid-grey floor, and then glare happens to that image).
   With no `base_mode` configured the sampler consumes the RNG exactly as before —
   short-circuit evaluation, pinned by a test against a transcription of the old
   algorithm — so every pre-19.08 run stays reproducible from its seed.
9. **`config/train_ppo_camera_2d_sim2real_ft.yaml`** — the fine-tune, continuing
   the 550k trunk. It differs from its parent in exactly four keys
   (`domain_randomization`, `learning_rate` 3e-4 → 1e-4, `total_timesteps`,
   `model_path`), which a contract test asserts, so the run has one experimental
   variable plus the standard fine-tune LR reduction. `base_level_range` spans the
   full `[0, 1]`: level 0 is the Gazebo render itself, kept in distribution because
   every scored campaign still evaluates there; 0.75 is the measured hall; 1.0 is
   headroom above it, and is capped by keeping the road under the D-43 white gate
   rather than by preference.

### Rationale

The 18.08 session ended with two separable defects fused into one narrative. Both
turn out to be diagnosable from the recordings, and they need opposite fixes: the
cage's is geometric and is closed by rectification; the policy's is photometric and
needs a retrain. Attacking either with the other's fix wastes a track session —
rectification moves the trunk's lane response from 0.097 to 0.090.

The gate exists because the evidence for the failure was already sitting in frames
recorded that morning. Turning "will it transfer?" into a number computable without
the car is worth more than any single fix here.

### Impact

* **No frozen evidence is touched.** `MODES` unchanged, every world and texture
  unchanged, every node default inert. The D-69 verdict of record stands.
* **The fine-tune is prepared but NOT launched** — it runs on the second machine.
  It needs two artefacts git does not carry (`policy/checkpoints/*.zip|*.pkl` are
  gitignored): `ppo_gz2d_cap022_1M_2024_550000_steps.zip` (sha256 `0d449246…`, the
  hash M-7 records for the trunk) and its paired
  `…_vecnormalize_550000_steps.pkl` (sha256 `5c1df0b2…`). `normalize_reward` is
  true, so resuming without the `.pkl` silently resets the running reward
  statistics. Launch:

  ```
  export CFG=$(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config
  ros2 launch cobraflex_rl train_lane.launch.py \
    train_config:=$CFG/train_ppo_camera_2d_sim2real_ft.yaml \
    resume_from:=<abs>/ppo_gz2d_cap022_1M_2024_550000_steps.zip \
    resume_vecnormalize:=<abs>/ppo_gz2d_cap022_1M_2024_vecnormalize_550000_steps.pkl \
    run_id:=ppo_gz2d_sim2real_ft_2024
  ```

  **Every path must be absolute.** `train_lane.launch.py` forwards
  `train_config` verbatim; only its *default* is a share path, so a bare
  filename reaches the trainer as a relative path and dies on `FileNotFoundError`
  after Gazebo has already come up. Same for the two resume arguments. This is
  the docs/11 §9 `$CFG/...` idiom.

  400k on top of 550k → ends at 950k, checkpoints every 25k. **Pick the
  checkpoint with `tools/sim2real_probe.py`, not by reward** — D-66's lesson
  holds, the reward peak was the worst driving candidate there.
* Rectification is implemented but **unproven on hardware**: enable it on the car
  behind a `preflight_deploy.py lanecheck`, not blind. Offline on 3357 real frames
  it removes the offset-dependent collapse (lane-width by |ey| band 244→229→207→183
  becomes 267→268→264→256) but leaves a **session-dependent** +8…+30 mm scale
  error — so once the optics are corrected, the dominant term is the mount pose,
  and the hands-off tape measurement M-7 §3b called for is still the open
  measurement. `camera_pitch_rad`/`camera_height_m` exist for that.
* The `epsi` mode is decided on evidence but not yet deployed: `near_secant`/1.0
  changes the readout the trunk's cage was trained against, so it is a Phase-5
  configuration choice, not a retro-fit to any scored run.

### Verification

`pytest` 651 passed (25 new: 4 rectification, 9 probe, 6 fine-tune config
contract, plus the DR assertions — including that no `low_contrast` level can
push the markings under, or the road over, the D-43 white gate the cage's
estimator shares with the policy, and that a config without a base term leaves
the RNG generator at the identical position).
`python tools/check_traceability.py` — unchanged, no ID added or removed.

Not verified, and stated as such: the fine-tune has not been run, the rectified
estimator has not seen hardware, and `sim2real_probe.py` has been exercised only
on checkpoints that fail it — no policy has yet passed the gate, so its PASS
branch is asserted by unit test, not by a driven car.

---

## [18.08.2026] — First run on the physical lane circuit: the D-43 estimator transfers at its shipped settings, the trunk camera policy does not, and three single-pose conclusions are retracted

**Document(s) affected:** `experiments/calibration/M7_track_perception.md` (new),
`docs/DECISIONS.md` (D-71), `docs/17_physical_deployment.md` (§2, §5, §6d),
`experiments/calibration/README.md`, `CLAUDE.md`,
`src/cobraflex_rl/cobraflex_rl/cv_lane_estimator_node.py`,
`src/cobraflex_rl/launch/deploy_cobraflex.launch.py`, `tools/lane_probe.py` (new),
`tools/measure_yaw_gain.py` (new), `tools/cv_controller_node.py` (new, unproven),
`tools/preflight_deploy.py` (`lanecheck` subcommand)
**Phase:** 5 (physical deployment)
**Gate context:** after G4; no gate re-scored
**Author:** Samuel Sanchez

### Change

The car was placed on the physical lane circuit and the Phase-5 chain was run end to end with
the 2-D PPO 550k trunk checkpoint for the first time. M-7 records the session; D-71 carries the
decisions.

1. `white_sat_max`, `white_val_min` and `policy` are exposed as launch arguments of
   `deploy_cobraflex.launch.py` (the first two also as `cv_lane_estimator_node` parameters),
   all inert by default — `-1` = not set for the thresholds, `policy:=true` for the node switch.
   `policy:=false` leaves `/raw_action` free for another controller behind the same cage.
2. Three measurement tools added: `tools/lane_probe.py`, `tools/measure_yaw_gain.py`, and a
   `lanecheck` subcommand on `tools/preflight_deploy.py`. `tools/cv_controller_node.py` is also
   added but **has never processed a frame** — the session ended before it could be tested.
3. M-6's propagated claim that `reported ey = 0.72 × true` is **retracted** in `docs/17` §2 and
   in M-7. M-6's camera measurement itself is unchanged.

### Rationale

Replaying a 2-minute recording of the whole circuit (1521 frames,
`experiments/physical/bags/circuit_20260818T140357Z`) through the estimator offline: at the
**default** `white_sat_max = 30` it pairs **95.4 %** of frames and reads a mean lane width of
**252.9 mm against a ruler-measured 250 — 2.9 mm of error, scale 1.012**. That refutes M-6's
propagation: in `camera_geometry.pixel_to_ground` an under-estimated `f` inflates `xo` and `yo`
by the same factor, `xo` multiplies while `yo` divides inside `denom`, so the two cancel in the
near field — and `c0`, hence `ey` and `lane_width`, is evaluated at `X = 0`, inside the
cancelling region. The error survives only in the far field, which is where the heading slope is
fitted: `joint_pair_quadratic`/1.6 is **unbiased (mean +0.04°) but has sd 14.29° and puts 7.8 %
of frames past C-02's 25° limit**, against `near_secant`/1.0's 5.31° and 0.8 %.

**The `ey` channel under-reads, confirmed hands-off against a tape.** With the car parked on the
ground at tape-measured offsets over ±100 mm (15 points, ~190 frames each,
`experiments/calibration/M7_offset_response.csv`), the transfer is
**reported = 0.68…0.83 × true − 10 mm**, robust to every filtering of the points (r up to 0.99).
M-6 predicted 0.72 and the measurement brackets it, so **C-01's 160 mm fires at a true 207–241 mm**
and C-05's 120 mm at a true 172–212 mm, against a 255 mm road half-width. An intra-session
retraction of M-6's prediction — made from the lane-width figure of 252.9 mm — is itself withdrawn:
`lane_width` is a *difference* straddling the optical axis, `ey` an *absolute* off-axis position,
and the unmodelled barrel distortion (`k1 = −0.339`) compresses the second while preserving the
first. At a true offset of 0 the width reads 0.975 of the ruler while `ey` reads −9.8 mm. A second,
independent defect: re-placing the car at the same tape offset elsewhere along the track moves the
reading by a mean of 13.2 mm and up to 29.4 mm, against ~2 mm of tape precision.

That 95.4 % pairing figure is also a **centre-of-lane** figure, and the qualification is the
session's other consequential result. The recording spent 90 % of its time within ±72 mm of centre. Sweeping the
car deliberately across the lane (2639 evaluated frames over two capture sessions) shows the
share of frames whose measured width lands within 40 mm of the ruler's 250 falling
**18 % → 30 % → 87 % → 95 % rejected** across the 0–30 / 30–55 / 55–80 / 80–120 mm bands. The
failure is systematic — 183.8 mm with sd 23.9 in the 80–120 band, `n_lines` predominantly 4, i.e.
both lanes in view and the wrong pair chosen — and is not explained by heading. **The estimator
feeding C-01 (`d_max` 160 mm) and C-05 (`d_warning` 120 mm) is therefore trustworthy only within
roughly ±55 mm of lane centre, entirely inside the band where those rules never act**, and pairing
rate does not detect it. Recorded as indicative rather than established: both sweeps moved the car
by hand, the IPM reads a constant pitch rather than the TF, and a hands-off measurement at
tape-measured offsets has not been run (M-7 §3b).

The same recording retracts three conclusions drawn earlier the same day from a **stationary car
at one spot**: that `white_sat_max` had to go 30 → 45 (over the circuit 45 pairs only 69.4 %, and
puts 37 % of frames within 15 mm of the `lane_width_tol_m` rejection floor); that the read was
0–12 % low and pose-dependent; and that `joint_pair_quadratic`/1.6 carried +17.28° of heading
bias. The underlying single-pose observations were real — at that location the lines genuinely
measured V 228…255 with S 36…50 and were genuinely rejected — but each derived fix makes the rest
of the circuit worse. Offline replay of a recorded circuit therefore replaces the stationary rig
as the primary characterisation method.

With the car moved by hand across a 332 mm span of `ey` and the chain running without actuation
(`experiments/physical/runs/policy_bias_probe/cage_status.csv`, 5665 logged cycles), the policy's
steering response has the correct sign but is an order of magnitude too weak:
`steer = −0.000166·ey_mm + 0.1155`, `r = −0.243`, `r² = 0.059`. The lane-dependent swing across
the whole span is **0.055** against a **constant left offset of +0.1155 — 2.1× the swing** — and
only 29 of 5665 samples (0.5 %) command a right turn at all. This conclusion rests on the
policy's own output barely moving, so it is robust to estimator error.

Separately, over 7721 cycles of drive attempts the speed reaching the cage carries outliers to
**6.960 m/s** on a 0.22 m/s car (ZED visual odometry through the ekf); 0.43 % of cycles exceed
the `state_validity_ranges.speed_mps` ceiling of 1.50 and **all of them are in emergency** —
SR-007 rejecting a hardware fault no simulation produced.

### Impact

No simulation result changes; the D-69 verdict of record is a Gazebo result and stands as
recorded. `cage.yaml` is untouched, no cage rule or SR is re-valued, and no gate is re-scored.
What changes is the Chapter-9 sim-to-real account: real imagery induces a large constant steering
bias that swamps the trunk's retained (correctly-signed) lane response, while the deterministic
estimator beside it transfers unchanged. Closing the gap is off-track work — fine-tuning or
domain randomisation calibrated against real imagery — carried as future work alongside T2/T4.

Withdrawn from the 17.08 M-6 entry's forward-looking text: "C-01/C-05 fire LATE" as a 0.72
scalar, and any margin table derived from it. Withdrawn from earlier drafts of this entry: the
`white_sat_max:=45` recommendation, the "0–12 % low" scale, and the `heading_bias_rad` correction.

New tool: `tools/record_lane_dataset.py` captures a labelled real-lane dataset at 5 Hz as PNG
with inline estimator labels (~1 MB/s against the 13.8 MB/s of a raw bag, which is what crashed
the board), gates each frame on lane-width sanity so a wrong pair is discarded rather than saved
with a confident wrong label, logs every rejection to `rejects.csv`, and prints live |ey| coverage
bars per side. First two sessions: `lane_00_firstpass` (1205 frames, ungated, 44 % width-sane) and
`lane_A` (631 saved / 803 rejected, width 237.4 mm sd 18.9).

Undecided and recorded as such: which heading configuration to deploy (`near_secant`/1.0 is
markedly cleaner but rescales the trained observation), the compressive yaw plant, and the
estimator's localised colour-gate failures.

### Verification

`python tools/check_traceability.py` — All checks PASSED, 0 warnings. Perception and heading
figures reproduce by replaying `experiments/physical/bags/circuit_20260818T140357Z` through
`CvLaneEstimator`; the policy sweep is the 5665-row `policy_bias_probe` log. The session ended in
a Jetson crash: the bag's `metadata.yaml` was regenerated with `ros2 bag reindex`
(`PRAGMA quick_check` on the `.db3` returns `ok`) and `circuit_survey/cage_status.csv` was
truncated at its last complete line (see that run's `REPAIR_NOTE.md`).

## [17.08.2026] — Bench session on the car: the perception-loss fail-safe and the actuation sign convention are verified on hardware for the first time

**Document(s) affected:** `docs/17_physical_deployment.md` (new §6c).
New artefact: `tools/preflight_deploy.py`.
Evidence: `experiments/physical/runs/ros_run_20260817T194009Z/cage_status.csv`.
**Code changed:** none.
**Phase:** Phase 5 (physical deployment)
**Gate context:** after G4; prerequisite work for the first hardware drive
**Author:** Samuel Sanchez

### Change

Ran docs/17 §4 stages 0 and 1 on the car (platform, **wheels off the ground**, no
track, no lane markings), Layers 1–3 up in `mode:=monitoring` on the
hash-verified 550k trunk checkpoint. Added `tools/preflight_deploy.py`, which
turns those stages into PASS/FAIL assertions instead of an rviz eyeball. Recorded
the results as §6c.

### Rationale

The 2026-08-05 review found five defects that were all *silent* — the chain
started, logged and would have driven wrongly rather than failing. That class of
fault is invisible to inspection, so the staged sequence needs machine-checked
invariants: frame contract, cage cadence at the trained 10 Hz rather than the
camera's 20, state-vector validity and liveness, and evidence actually reaching
disk.

### Impact

* **Stage 0 and stage 1 pass.** Camera at exactly 20.0 Hz median (retiring an
  earlier suspicion that the node published slowly — the gaps were transport loss
  at an extra subscriber); cage at 9.8 Hz; `cycles_since_last_state` max 0;
  evidence CSV written with `mode` stamped.
* **The perception-loss fail-safe is demonstrated outside simulation for the
  first time.** No lane markings → `perception_invalid` → C-05 latches →
  `/emergency` → `vehicle_control_node` commands a zero Twist → **97/97
  `/cmd_vel` samples exactly 0.0**, while the policy was asking for ≈ 0.70
  throttle throughout. H-11/H-12 → SR-005 → C-05 → actuation stop, end to end.
* **The actuation sign convention is verified in both directions**, previously
  untested on hardware: `angular.z = +0.5` turns right wheels forward and left
  wheels backward (counter-clockwise = left, REP-103), matching the firmware's
  `setpointA = rosX − rosZ·TRACK_WIDTH/2`; and the cage's half checked host-side
  (`ey` +0.20 → steering −0.12, `ey` −0.20 → +0.12, centred → 0).
* **Operational finding for track work:** C-05's exit is deliberately asymmetric
  — condition cleared **AND** a reset on `/cage_reset`, not either. Any momentary
  perception loss therefore stops the car until a reset is published. On a bare
  bench there is no way out at all, by design.
* `/odometry/filtered` alive at 14.6 Hz. `/cobraflex/battery` reads 10.89 V,
  confirming the §6b centivolt fix; that is ~3.63 V/cell on 3S and wants charging.
* **Not established:** §4 step 2's throttle envelope (C-05 latched, so `/cmd_vel`
  is identically zero and the envelope cannot be exercised), step 3's e-stop
  test, and the §5 yaw-gain bench number — all need a lane or the ground.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (no
hazard/SR/scenario/metric artefact touched). The preflight tool's own stage
assertions are the verification of the bench state; §6c records the measured
values behind each.

---

## [17.08.2026] — M-6: the lane camera's "90° effective HFOV" is measured on the car and refuted — it is 77.89°, the assumption was circular because the simulator mirrored it, and the mount pitch it was confused with turns out to be fine

**Document(s) affected:** `docs/17_physical_deployment.md` (§1b table + new falsification
note, §2 items 1 and 2, §5 launch note, §7 bring-up step),
`experiments/calibration/M6_camera_hfov.md` (new protocol + result),
`experiments/calibration/README.md` (M-6 rows).
New artefacts: `tools/calibrate_camera_hfov.py`,
`experiments/calibration/M6_results.json`, `experiments/calibration/M6_pitch_results.json`,
`experiments/calibration/M6_camera_hfov/` (checkerboard, 58 views; forward-tape capture
+ `partB_obs.json`; 3 rejected captures retained as evidence of rejection).
**Code changed:** none — see Impact.
**Phase:** Phase 5 (physical deployment)
**Gate context:** after G4; prerequisite work for the first hardware drive
**Author:** Samuel Sanchez

### Change

Executed M-6, a new calibration measurement closing the highest-priority
`[VERIFY]` of docs/17 §2. Checkerboard calibration of the lane camera on the
bench (26 views, 20.0 mm squares, `csi_camera_node` publishing 640×360,
`lane_keeper_node` down) measures:

| Quantity | Measured | Assumed |
| --- | --- | --- |
| `fx` = `fy` | **395.93 px** | 320.00 |
| Effective HFOV | **77.89°** | 90.00° |
| `cx` / `cy` | 305.39 / 193.20 px | 320 / 180 |
| Distortion k1 | **−0.339** (barrel) | 0 |
| rms reprojection | 0.238 px (58 views, 16/16 image regions) | — |
| **Mount pitch** | **0.3113 rad / 17.84°** | 0.3000 rad / 17.19° |
| Camera height | 77.9 mm *fitted*, vs 77 mm measured by hand | 77.25 mm (URDF) |

Part B (mount pitch) was executed in the same session and **closes `[VERIFY]` #2
as well**: the mount is right to +0.65°, inside the 1° confirmed band, so no
physical adjustment is needed. The fit recovered the camera height to within
0.9 mm of the operator's tape reading *without being given it* — an independent
cross-validation of `fx`, the pitch and the mark extraction simultaneously, only
possible because Part 0 ran first and broke the height/focal-length degeneracy.

docs/17 §1b's claim that the three code locations "all agree" is annotated as
**falsified for HFOV**: they still agree with each other, but no longer with the
camera.

### Rationale

The 90° figure was a *parameter default* in `lane_keeper_node` for an
IMX219-**160** lens which the Gazebo `Lane Cam` was then built to mirror. That
made the assumption circular and unfalsifiable in simulation — including by the
1890-run verdict-of-record campaign. Cause of the discrepancy is coherent with
the hardware: "160°" is a *diagonal* figure for the full 3280×2464 sensor, while
`csi_camera_node` captures the **1280×720 crop mode**, which discards field of
view rather than downscaling.

Two prior capture attempts using a tape measure were **rejected on target
geometry** and are retained as evidence of the rejection, not as results; a
Monte-Carlo identifiability study run before touching hardware established that
a single image cannot separate focal length from camera pose (zero-noise fits
returned fx = 334 px and fx = 351 px against a truth of 400 px, at zero
residual). An 8-view checkerboard attempt was likewise rejected by the tool's own
conditioning gate: its free-aspect probe read `fy/fx` = 1.85, impossible for this
pipeline's isotropic resize.

### Impact

**No source file was changed.** `camera_geometry.py`,
`lane_keeper_node.camera_hfov_deg`, `Lane Cam <horizontal_fov>` and `cage.yaml`
all still carry 90°, deliberately — the three possible responses (correct the IPM
only; correct the sim sensor and retrain; change the capture mode) differ by
whether they invalidate the trunk policy and the verdict-of-record campaign, and
that choice is the author's. Recorded as an open decision in the M-6 document.

* A raw single-point `ey` is over-read by 395.93/320 = **1.237**. **Propagated
  through the estimator's real construction, however, the sign reverses** — this
  corrects a first reading of this measurement. With the two lane markings
  0.245 m apart, per-row midpoints, a quadratic `Y(X)` fit and `ey = −c0`, the
  reported `ey` comes out **0.72 × true with a −1 mm bias**: the principal-point
  offset cancels (the markings are close and symmetric), the 28 % under-read does
  not. **C-01 and C-05 therefore fire at a larger true excursion than specified —
  on hardware the cage is *less* protective than the campaign verified, not more.**
  Linear extrapolation of the gain puts C-01 at a true ±0.22 m, but that is beyond
  the ±0.12 m range over which the gain was modelled (the two-marking geometry
  breaks down first, into single-side mode), so treat it as a direction, not a
  figure.
* **The simulation results are not invalidated.** Gazebo's sensor really was 90°
  and the IPM really assumed 90°, so in sim C-01 fired at exactly 0.16 m. Only
  the sim-to-real *transfer* is affected.
* `cx` being 14.61 px off centre adds a **lateral bias**, not just a gain.
  Propagating the full measured model (intrinsics + distortion + measured pitch)
  through the *running* IPM misplaces real lane points by **−57 mm to +167 mm**
  laterally; the worst case exceeds C-01's whole 160 mm `d_max_m`, and forward
  distance at 1.0 m decodes as 1.34 m.
* **Two counter-intuitive findings that constrain the fix.** (i) Correcting `fx`
  *alone* makes the mean lateral error **worse** (49.4 → 52.2 mm) — the scale
  error and the principal-point offset were partially cancelling, so the smallest
  plausible patch is the one change that must not be shipped on its own.
  (ii) With `fx`, `cx`, `cy`, pitch and height all corrected, a pinhole IPM still
  leaves ~44 mm: closing it requires the estimator to **undistort**, not merely to
  be re-parameterised.
* The 550k trunk policy trained on 90° frames but will see 77.89° ones — images
  ~24 % narrower in field of view than its entire training distribution. This is
  an observation-space domain shift that no IPM correction addresses.
* `cy` being 13.20 px low is worth **+1.91° of equivalent pitch** in the
  row→distance mapping, but Part B shows the *mount* is off by only +0.65°. The
  two are not the same quantity and must not be added: most of that error lives in
  the principal point, not in how the camera is bolted on.
* Correction of a docs/17 wording error: it called 0.12 m "C-01's threshold".
  C-01 uses `d_max_m` = 0.16; 0.12 is C-05's `d_warning_m`.

Both `[VERIFY]` items of docs/17 §2 are now **measured**. What remains open is
purely the decision of what to change in response, recorded in the M-6 document.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (no
hazard/SR/scenario/metric artefact was touched). The calibration tooling was
validated against synthetic ground truth before hardware: fx to 0.04 %, `cx`/`cy`
to ~1 px, k1 to 0.01 by exact inverse-ray rendering through a known `K` and
`plumb_bob` distortion. Result stability across independent solves: fx = 396.10
(58 views) / 396.10 (26) / 396.29 (34) / 395.70 (13-view half), spread 0.15 % while
the view count grew 4×; worst single-view reprojection 0.381 px, no outlier view.
The free-aspect probe returned `fy/fx` = 1.004 without that being imposed — the
isotropic-resize square-pixel physics recovered from the data. The result is also
**invariant to the square-size measurement**, verified by re-solving at 20.00,
18.03 and 50.00 mm for identical `fx` and k1. Part B: residual rms 0.48 px, max
1.07 px over 17 marks, and the height cross-check above.

---

## [17.08.2026] — First physical measurement of the platform reaches the specification: URDF mass corrected 6.59 → 3.5 kg, the real chassis measured at 0.4954× commanded yaw, and the "measured" 0.53 m/s² acceleration limit refuted as a unit error

**Document(s) affected:** `docs/08_odd_specification.md` (§8.1 + version rows v0.9.2 / v0.9.3),
`docs/09_environment_design.md` (C-06 acceleration bound),
`docs/13_isaacsim_environment.md` (drivetrain note + friction-table calibration target),
`docs/14_isaacsim_handover_spec.md` (§2.2 rewritten, §2.3 table + two notes, new §2.3a),
`docs/17_physical_deployment.md` (§2 item 4), `docs/DECISIONS.md` (D-70).
Code: `src/cobraflex/urdf/{my_robot_gazebo_mesh,my_robot_gazebo,my_robot_mesh,my_robot_basic}.urdf`,
`src/cobraflex/urdf/cobraflex_isaac.urdf`, `src/cobraflex/urdf/cobraflex_isaac/payloads/Physics/physics.usda`,
`src/cobraflex/urdf/robot.gazebo`, `src/cobraflex_rl/cobraflex_rl/{vehicle_control_node,cage_bridge}.py`,
`src/cobraflex_rl/launch/deploy_cobraflex.launch.py`, `tools/isaac_scene.py`.
**Sources:** the platform team's bench sheet *CobraFlex 1:14 Parameters_0813* (13.08.2026), its
itemised bill of materials (17.08.2026), and the platform repo
`Waveshare-Cobra-Flex-ROS2-Autonomous-Car` (`assets/Mathematical Model/`).
**Phase:** E5 / Phase 5 (physical deployment).
**Gate context:** none — G4 and the 550k verdict of record are untouched. No SR, cage rule,
`cage.yaml` value or `ODD-N.<PARAM>` is re-valued.
**Author:** Samuel Sanchez

### Change

The platform team supplied the first bench characterisation of the physical car
(*CobraFlex 1:14 Parameters_0813*, 13.08.2026). Five changes follow (full reasoning in **D-70**):

1. **URDF mass budget corrected to the measured 3.5 kg total, distributed from the bill of
   materials.** It summed to **6.59 kg** — chassis 5.0 + body 1.0 + 4×0.1 wheels + 0.19 lidar —
   i.e. the simulated vehicle was **1.88× too heavy**. The itemised BoM the platform team
   supplied the same day (three PLA shells weighed individually: 91.3 g bottom / 118.5 g centre
   / 68.0 g top cover, plus powerbank, lidar and ZED) locates the **entire 3.09 kg overshoot in
   the single `chassis_mass` placeholder**, so the split is itemised rather than uniform:
   `body_link` **0.8928** (PLA 0.2778 + powerbank 0.550 + ZED 0.060 + lane cam ≈0.005),
   `lidar_link` **0.190** (manufacturer — restored; the original URDF had it right), wheel ×4
   **0.1** (unchanged, still unmeasured), `base_link` **2.0172** (remainder: frame + motors +
   driver board + motor battery + Jetson DevKit 0.175 + wiring — the Jetson riding on the chassis
   rather than in the printed body was **confirmed by the platform team**, not assumed). Applied to all four xacro URDFs
   and the two generated Isaac artefacts (`cobraflex_isaac.urdf`, `physics.usda`), whose
   hard-coded inertias were recomputed from the same box/cylinder primitives the generator uses.
   Totals asserted at 3.5000 kg in both generated files. **Two datasheet corrections:** the
   powerbank is **550 g, not the 500 g quoted** (XTPower XT-27000DC, *"Weigth 550g"*), and the
   **Jetson Orin Nano DevKit is 175 g** (NVIDIA SP-11324-001 v1.3 p33) — previously unaccounted
   for anywhere in the budget. The ZED Mini's 60 g is folded into `body_link` because
   `zed_macro.urdf.xacro` declares **no `<inertial>` at all**. **2.25 kg (64 % of the car) — the
   rolling chassis — remains a derived remainder that has never been weighed;** one wheel and the
   bare chassis are the two measurements that would close it.
2. **`steering_to_yaw_rate_gain` raised 0.8 → 1.615 for hardware only**, in
   `deploy_cobraflex.launch.py`. The `vehicle_control_node` default stays 0.8 (the sim value,
   against which every frozen verdict was produced) with a comment saying why it must not be
   "fixed" there.
3. **`docs/14` §2.2** rewritten from the placeholder *"Total mass to be measured from real car.
   Inertias to be measured from real car."* to the measured mass, the rejected inertia tensor,
   and the rejected CoG. **New §2.3a** records the yaw-transfer measurement and its consequences.
4. **`docs/17` §2 item 4** goes from `[VERIFY]` to `[MEASURED]`, with the two conditions that
   still gate it. The same item's stale claim that the firmware's `Z` addresses "an Ackermann
   chassis" is corrected — the platform is skid-steer (docs/08 §11), which is *why* the deficit
   exists.
5. **`docs/08` §8.1** (`ODD-PHYS-1`) records the measured platform envelope in the table that
   section was written to receive; version row **v0.9.2** added.
6. **The `0.53 m/s²` acceleration limit is refuted — it was a unit error.** `robot.gazebo` is
   corrected from `max_linear_acceleration 0.53` / `min −10` to **±2.5 m/s²**, and the four live
   citations of "the platform's *measured* max linear accel 0.53 m/s²" (`docs/09`, `docs/13`,
   `docs/14`, `cage_bridge.py`) are corrected with a note. The platform repo's own parameter
   document states the diagnosis: **0.53 is this chassis's maximum velocity in m/s, copied into an
   acceleration field**; −10 was an arbitrary 20× braking limit. New platform figures recorded:
   **3.2 rad/s²** angular acceleration, **20 N·m** max wheel torque. **`cage.yaml` is deliberately
   untouched** — see Impact. D-50's prose is left as the historical record it is.
7. **New geometry error recorded, not corrected: the URDF wheelbase is 0.120 m against 0.154 m
   measured** (`wheel_off_x = ±0.060`, all four xacro URDFs). Inert in Gazebo (kinematic DiffDrive
   consumes only `wheel_separation`), material in Isaac, where it under-models the scrub behind
   the yaw deficit. Left for the Isaac regeneration pass; noted in `docs/13` and `docs/14` §2.3.
8. **Open conflict with the platform repo logged in `docs/14` §2.2.** It splits the same 3.5 kg as
   **2.20/0.71** chassis/body and places the **Jetson in the body**. Both are contradicted — the
   0.71 kg body is arithmetically impossible (weighed PLA 277.8 + powerbank 550 + ZED 62 = 890 g,
   180 g over the whole link), and the team confirmed the Jetson rides on the chassis. This repo
   keeps the itemised split; the platform repo should adopt it rather than the reverse.

### Rationale

Three of the supplied rows are measurements and three are not, and separating them is the point:

- **Measured, consistent with the model:** mass 3.5 kg; wheelbase 0.154 m / track 0.153 m /
  wheel radius 0.03725 m; straight-line tracking ≈0.99 of commanded to 0.53 m/s.
- **Measured, contradicting the model:** in-place rotation over 10 s at 0.20/0.40/0.53/0.80 rad/s
  yields 55.6°/114.5°/150.4°/226.9° — **0.4954 × commanded yaw**, least squares through the
  origin, per-point gains 0.485/0.500/0.495/0.495, linear and offset-free. Gazebo's DiffDrive
  delivers ~1:1. Forward transfers at 0.99 while rotation transfers at 0.50, so this is **scrub**:
  four fixed wheels dragging sideways, effective track `0.153/0.4954 = 0.309 m` ≈ 2.02× physical.
- **Not measurements:** the inertia tensor reproduces this repo's own URDF chassis box at the
  **old 5.0 kg** to nine decimals (our assumption read back out of Isaac — circular, and
  inconsistent with the 3.5 kg measured beside it); `0.53 m/s` and `6.0 rad/s` are the serial
  driver's clamp constants (docs/17 §2 item 3), and 6.0 rad/s is unreachable — ideal diff-drive
  gives 6.93 rad/s, ≈3.4 rad/s after the measured scrub; the CoG `(0.006, −0.004, 0.030) m` is
  frame-ambiguous and, read in `base_link`, geometrically unreachable (with the lidar at
  z = 0.16 m, all remaining mass at z = 0.030 m still floors the composite at 0.037 m).

Neither the CoG nor the inertia tensor was applied. The BoM makes the CoG case conclusive:
**740 g — 21 % of the car — sits in the upper two body shells** (powerbank 550 g in the centre,
lidar 190 g on the top cover), putting the itemised composite at **0.0566 m** above `base_link`,
nearly 2× the claimed 0.030 m. Read from the **chassis box centre** the supplied figure lands at
0.060 m, **3.4 mm from the model** — the working hypothesis for the reference frame, pending
confirmation.

### Impact

- **Transfer risk T2 is now quantified.** Every steering-expressed cage margin buys half the
  physical yaw it buys in sim. At `steer = 1.0`: 0.800 rad/s → 0.396 rad/s. Minimum turn radius
  at 0.22 m/s: 0.275 m → 0.555 m. C-06's `delta_max_steering_per_cycle = 0.15` bounds yaw
  acceleration at 2.40 rad/s² sim → 1.19 rad/s² real (20 Hz). The tightest `complex_b` curve
  (driven `R_min ≈ 0.998 m`) needs 27.6 % of full steer in sim, **55.6 %** on hardware — feasible,
  headroom 3.6× → 1.8×.
- **The two simulators bracket the truth.** Gazebo ≈1.00, real 0.4954, Isaac ≈0.18 at
  `friction 0.05` (D-54). Isaac's `--turn` calibration target becomes **≈1.44 rad/s**, after which
  `cage.yaw_gain` should return from 2.4 to 0.8. `docs/13` notes that one isotropic friction knob
  probably cannot match both axes and that anisotropic wheel friction is the likely requirement.
- **No safety argument weakens on the acceleration correction.** Every citation of 0.53 m/s² was an
  *upper*-bound argument, and the bound grew 5×: C-06's throttle rate limit bounds commanded
  acceleration to **0.22 m/s²** at the 0.22 m/s trunk cap and 0.5 m/s² on the Isaac contract, both
  far inside 2.5 m/s² rather than marginally inside 0.53. **`cage.yaml` is deliberately unchanged:**
  `a_min_mps2 = 0.3 [provisional, M-3]` and SR-008's `t_stop_max = 1.7 s` sit in a consistency
  relation, and 2.5 m/s² would make `a_min` ~8× conservative — but the replacement figure has **no
  stated measurement provenance either** (the 0813 bench sheet reports the same copied
  "≈0.5–0.53 m/s²" by a second route), and revising a braking parameter on an unsourced number is
  precisely the error being corrected here. **M-3 is informed, not closed.**
- **Frozen campaigns.** F4, GE4-V2 and `campaign_2d_ppo550k` ran with the 6.59 kg budget and the
  0.53 / −10 acceleration limits; they are pinned by git commit and remain reproducible from it,
  **not from HEAD**. Second-order in Gazebo (kinematic velocity plugin — traction/slip only;
  the acceleration limit never bound at 0.22 m/s), first-order for Isaac.
- **The camera is untouched by all of this.** Neither the bench sheet nor the platform parameter
  package specifies the lane camera, and the platform repo carries the same unverified
  `camera_hfov_deg = 90.0` default — so it is **not** independent corroboration.
- **Re-runs required:** none for any verdict. `tools/build_isaac_urdf.py` must be re-run on the
  Ubuntu host and the URDF re-imported in Isaac (see Verification).
- **Still open, unchanged:** **TBD-Q10 / `ODD-3.A_LAT_MAX`** — no lateral-accel envelope was
  supplied, so M-4 stays open and `docs/08` stays below v1.0. The document contains **nothing
  about the camera**, so `docs/17` §2 item 1 (the 90° effective HFOV) remains the highest-priority
  unverified number of the whole transfer, alongside `a_min` (M-3), actuator latency (M-2) and the
  real surface friction.
- **Not applied:** `manuscript/chapters/chapter_06_implementation.md` (~L129, wheel separation)
  and `chapter_09_sim_to_real_gap.md` (~L141, "0.154 m, aceleración máxima medida 0.53 m/s²")
  carry affected figures. Left for the author.

### Verification

`python tools/check_traceability.py` → All checks PASSED. Mass totals asserted programmatically
at 3.5000 kg in `cobraflex_isaac.urdf` and `physics.usda`; the recomputation formulas were first
verified to reproduce every previous inertia exactly at the previous masses. `pytest` unaffected
(no cage or policy logic touched).

**NOT verified — needs the Ubuntu host.** Neither URDF has been loaded in Gazebo or Isaac since
the rescale. `xacro` is unavailable on the Windows authoring host, so `tools/build_isaac_urdf.py`
could not be re-run; `cobraflex_isaac.urdf` and `physics.usda` are **generated artefacts that were
hand-patched**, and both must be regenerated to restore the re-derivable chain. The 1.615 yaw gain
has not been run on the car.

---

## [05.08.2026] — Phase-5 bench review on the car: five silent defects in the deploy chain fixed, sensors layer now owns the lane camera, deployed checkpoint verified on the car

**Document(s) affected:** `docs/17_physical_deployment.md` (status, §2 item 8, §2b, §3, §4, §5, §6, new §6b).
Code: `src/cobraflex_rl/cobraflex_rl/{rl_policy_node,vehicle_control_node,cv_lane_estimator_node,csi_camera_node,cage_viz}.py`,
`src/cobraflex/cobraflex/{lane_keeper_node,lane_keeper_gazebo_node}.py`,
`src/cobraflex/launch/cobraflex_sensors.launch.xml`, `src/cobraflex_rl/launch/deploy_cobraflex.launch.py`,
`policy/tests/{test_rl_policy_node,test_csi_camera_node}.py`, `.gitignore`.
**Phase:** E5 / Phase 5 (physical deployment).
**Gate context:** none — the G4 record and the 550k verdict of record are untouched; this is deployment-side only.
**Author:** Samuel Sanchez

### Change

First review of the Phase-5 chain **on the car** (`admit14-cobraflex`, Jetson / L4T R36.4.7,
ROS 2 Humble), read against the simulation it must reproduce and then run end to end on the
bench in `mode:=monitoring`, first with a synthetic checkpoint and then with the real 550k one.
Five defects, all silent — the chain started, logged and would have driven *wrongly* rather than
failed. Full detail in docs/17 §6b:

1. `rl_policy_node` published the policy's raw action a ∈ [-1, 1] on `/raw_action.linear.x`,
   where the cage expects its normalised throttle u ∈ [0, 1]. The sim applies
   `cage_bridge.policy_throttle_to_cage` before the cage; the node now imports the same mapping.
2. `vehicle_control_node` only had the frozen 1-D cruise-scaling speed map. Added
   `speed_map:=linear_2d`, delegating to `cage_bridge.target_speed_from_throttle_2d`.
3. Inference ran in the image callback, so policy **and cage** cycled at the camera's 20 Hz
   instead of the trained 10 Hz — doubling how often C-06's per-cycle steering budget is granted.
   Added `control_rate_hz` (default 10.0), timer-driven off the latest buffered frame.
4. `msg.data = frame.tobytes()` on a `sensor_msgs/Image` costs **127 ms** per 640×360 frame,
   because rclpy's generated `uint8[]` setter fast-paths only `array.array('B')` and otherwise
   validates every element in Python twice under `__debug__`. Fixed in all four publishers
   (including the classical `lane_keeper_node`, which publishes four debug topics per cycle).
5. `csi_camera_node` treated `cv2.VideoCapture.isOpened()` as proof of a working camera. When
   Argus refuses the capture session the pipeline still reaches PLAYING, so the node announced
   `ready` and then failed every `read()` — 1141 in the observed run — with no statement of why.
   It now probes for a real first frame (`open_timeout_s` 4 s) and retries the open
   (`open_retries` 3), because the refusal turned out to be a *startup race*: it reproduced only
   when the camera started inside the RL launch while `rl_policy_node` was loading the 20 MB
   checkpoint on the same six cores. The three-command bring-up avoids the race structurally.

Alongside: `cage_logger_node` now receives the real `cage_mode`, a `run_id` and
`experiments/physical/runs` (it defaulted to `experiments/sim/runs` relative to the shell cwd,
stamped `enforcement` whatever the mode); `cv_lane_estimator_node` now exposes the full D-43
estimator contract and the launch forwards the 550k trunk's values (`joint_pair_quadratic`,
gain 1.6, temporal window 4) instead of silently running the frozen GE4 `near_secant`/1.0; and
`odom_topic` defaults to `/odometry/filtered` (nothing publishes `/odom` on this platform, and
with speed stuck at 0 the cage's C-03/C-04 and C-05 high-energy trigger are inert).

**Pipeline change (author request).** `cobraflex_sensors.launch.xml` now starts the Jetson CSI
lane camera together with the lidar and the ZED, so a bring-up is three commands —
`cobraflex_bringup` → `cobraflex_sensors` → `deploy_cobraflex` — and no sensor is left to a side
script. `deploy_cobraflex.launch.py` therefore defaults `camera:=false`.

### Rationale

The 550k campaign is the verdict of record, and the point of Phase 5 is that the *same* policy
behind the *same* cage runs on the car. Three of the four defects broke exactly that equality —
the throttle domain, the actuation map and the control rate all changed what the cage arbitrates
— and none of them was observable from simulation, because the simulation path is the one that
was right. The fourth was a pure performance defect that starved the loop below its own control
rate. All are fixed by delegating to the sim's own functions rather than by re-implementing them,
so they cannot drift apart again.

### Impact

No sim result, gate record or verdict changes: `cage/cage.yaml` is untouched (still v0.6.1, hash
`4287fe71…`, bit-identical to the 550k campaign), and no rule, threshold, scenario, metric or SR
is affected. The changed nodes are deployment transport only — `gazebo_lane_env` and
`cage_bridge`, which carry every scored result, are unmodified.

The deployed checkpoint `ppo_gz2d_cap022_1M_2024_550000_steps.zip` **is now on the car** (repo
root), sha256 `0d449246…` verified exact against the campaign metadata, SB3-loadable, 550 000
timesteps, obs/action spaces matching the deployed contract, `predict()` deterministic at 9.2 ms
median on the Jetson CPU. `.gitignore` gained `/*_steps.zip`: the 25.07 root-level rule only
matched the `cobraflex_*` naming, so an SB3 `CheckpointCallback` artefact staged at the root was
still trackable. The physical run now remains blocked only on the mandatory `/external_stop`
e-stop, plus the standing `[VERIFY]` items (HFOV, camera height, yaw-rate gain).

### Verification

`pytest` 613 passed (was 612; +4 rewritten action-mapping tests, +1 chain-equality test,
+1 pipeline-throttle test). `python tools/check_traceability.py` PASS.

Bench runs on the car, both bring-up orders, with the **real 550k checkpoint**: six nodes up,
cage v0.6.1 loaded through the symlink walk-up, ~**10 Hz** cage cycles (44–50 per 5 s), camera
stamp gaps 50 ms median (was 117 ms), `csi_camera_node` CPU 140 % → 62 % of a core, **0**
`/safe_action` watchdog stops (was tripping). Evidence written to `experiments/physical/runs/`
stamped with the real mode. The policy commanded `raw_throttle` 0.652–0.755 — inside the cage's
[0, 1] domain, i.e. 0.143–0.166 m/s under the 2-D map — and a non-track (desk) scene was
correctly answered with `C-05` via `perception_invalid` rather than a drive command.

---

## [31.07.2026] — Submission build: `draft_V5.docx` rebuilt from Markdown to the university guidelines, body cut from 180 to 96 pages

**Document(s) affected:** `manuscript/draft_v5/` (new source tree: `front/`, `body/`, `back/`), `tools/build_thesis_docx.py` (new), `tools/thesis_page_budget.py` (new), `manuscript/README.md`, `manuscript/figures/` (3 campaign figures copied in as `fig_8_*`). Output: `B:/SE4AI/Documentos/draft_V5.docx` (`draft_V4.docx` untouched).
**Phase:** E5 / thesis production.
**Gate context:** none — editorial, no evidence changes.
**Author:** Samuel Sanchez

### Change

**The problem.** `draft_V4.docx` had a **180-page body** (pp. 13–192) against the guidelines'
**80–100**, and it used 1.08 line spacing where the guidelines require 1.5 — so merely applying
the mandated layout would have pushed it to roughly 240–250. It was also a week stale: no §8.9.9,
no 2-D campaign, none of the 31.07 closures.

**The approach, chosen deliberately** (author decision): move the evidence to **appendices**,
which the guidelines exclude from the page count, and condense the body prose around them —
rather than deleting content or merging chapters. Nothing is lost; the body keeps the argument
and cites the appendix.

**New source tree** `manuscript/draft_v5/`: front matter (cover with both examiners, the required
**certification of authenticity**, abstract, preface, TOC, list of figures/tables, abbreviations),
twelve condensed chapters, bibliography and **appendices A–I**. `manuscript/chapters/` stays the
research working source; `draft_v5/` is the submission source, derived editorially rather than
mechanically. Appendices A, B, D, E, F, G, H and I are **extracted or generated** from the living
documents and the campaign artefacts — the hazard register, the SRS with its rationale, the ODD
parameter table, `cage.yaml` verbatim, the traceability matrix and CSV, the full positioning
matrix, the hyperparameters and algorithm study, and a per-scenario campaign breakdown produced
directly from `campaign_report.json` and `failure_mode_breakdown.json` — so they stay
re-derivable instead of being hand-copied.

**New tooling.** `tools/build_thesis_docx.py` renders the tree to DOCX with the guideline layout
encoded as constants at the top of the file: A4, 12 pt, 1.5 spacing, justified, first-line indent,
margins 1.5"/1"/1.25", preliminary pages in lower-case roman centred at the bottom with no number
on the title page, body in arabic upper-right restarting at 1. It embeds figures, renders GFM
tables, drops HTML comments and editorial `[BORRADOR …]` tags, and builds a **working list of
figures and tables** via bookmarks and `PAGEREF` fields (a `TOC \c` field would have come out
empty, since the captions are not Word caption fields). `tools/thesis_page_budget.py` drives Word
over COM to repaginate, exports a PDF and reports per-chapter page spans plus the **body page
count** against the 80–100 bar — the build's acceptance check.

**Result.** Body **96 pages** (pp. 18–113), 159 pages in total including 17 of front matter,
3 of bibliography and 43 of appendices; 41 391 words; 16 figures embedded; 32 captions listed.
Content is current: the abstract, Ch. 7, Ch. 8, Ch. 10 and Ch. 12 carry the 2-D verdict of record,
the C-06 dependence finding, the SR-010 negative and the D-69 closures.

### Rationale

The page limit is a hard submission requirement and the draft was ~2× over it before the mandated
layout was even applied. Appendices are the guidelines' own mechanism for exactly this: the body
carries the argument, the appendix carries the evidence. Rebuilding from Markdown rather than
patching the DOCX also removes the staleness problem structurally — the document is now
regenerable in one command, so a result change no longer means hand-editing a binary.

### Impact

`draft_V4.docx` is left untouched as the previous submission draft. Two items stay open and are
recorded in `manuscript/README.md`: the **language** (the guidelines ask for standard English; the
manuscript is in Spanish — the author's decision was Spanish now, English afterwards over the
reduced text), and the **physical results**, which remain absent because Phase 5 has not run.

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings. Build reproduced from a
clean invocation; page budget verified by Word repagination, not estimated. Cover, abstract, TOC,
list of figures, a body page and an appendix page inspected as rendered PDF.

---

## [31.07.2026] — D-69: the simulation programme closes — verdict of record re-pointed to the 2-D campaign, and the last two SR-CL-B TBDs closed

**Document(s) affected:** `docs/07_traceability_matrix.md` (matrix rows, notes ²³⁷, new note ⁹, new E5 block, post-gate note, CSV schema row), `docs/02`–`docs/06` (framing notes + Last-update lines), `docs/08_odd_specification.md` (**v0.9 → v0.9.1**, status line, §1, §6.5, §7.3 realisation block, §11 Q10 row, §12.3), `docs/DECISIONS.md` (**D-69**, index rows D-62..D-69, status header), `tools/traceability_matrix.csv` (evidence re-pointed + 4 new rows for SR-009/SR-010), `CLAUDE.md`, `docs/16_defense_compendium.md`, `manuscript/` chapters 8 and 10 (only the claims the closure falsifies).
**Phase:** E5 (posterior) → end of the simulation programme, entry to F5.
**Gate context:** does **not** reopen G4; the gate record stands on its own frozen evidence.
**Author:** Samuel Sanchez

### Change

**The two follow-ups D-67 deferred are now taken — one of them.** D-67 recorded, rather than
silently skipped, two edits that could not honestly be made before a verdict existed: re-pointing
the `verdict of record` in `docs/02`–`docs/08`, and restructuring Chapter 8 so the camera track
leads. The verdict now exists, so **the first is done and the second is explicitly still open**
(it is an authoring decision, not an evidence one).

**Verdict of record → `campaign_2d_ppo550k`.** `docs/02`–`docs/08` now name the 2-D PPO 550k
pre-deployment campaign (1890 runs, 0 errors, 27 complex_b scenarios × {enf, mon}, seed 2024,
checkpoint 550k at cap 0.22). **GE4-V2 is retained, everywhere, as the frozen G4 gate record and
is not re-scored.** D-67's condition was **checked rather than assumed**: it required revisiting
the trunk decision if the campaign returned a worse in-ODD safety picture than GE4-V2's. It did
not — enforcement in-ODD road-edge contacts are **0 on both arms**, and out-of-ODD the 2-D arm
more than halves them (**56 vs 117**).

**SR-009 — TBD → `Satisfied`, scored out-of-band (D-64, ratified by D-69).** The verdict is
deliberately *not* taken from campaign aggregation: the 2-D campaign reports
`insufficient_evidence` because SC-PERT-03 was excluded from it by protocol, which is a fact
about that campaign's coverage, not about the requirement. It rests on D-64's three measured
parts — nominal liveness passes on every arm (M-P6 = 0); the policy **resists** being forced to
stall (the pure-stall-objective pilot did not produce a staller); and the detector **fires on a
ground-truth stall** (scripted stimulus through the real Gazebo + cage + metrics pipeline,
**M-P6 = 100.0**). Same out-of-band pattern as SR-006/D-39, for the same reason.

**SR-010 — TBD → `Not satisfied`, reported as the one negative in the matrix.** The scenario-side
gap that justified the abstention is gone (grid-IC injection wired; SC-EDGE-05 genuinely induces
co-activation), so the requirement was measured on two policies and **fails its own criterion**
(`M-S2 = 0` does not hold): **30/85** in-ODD grid points breach M-S1 on the 1-D arm and **16/85**
on the 2-D arm. The per-anchor split localises it — **C-01 ∧ C-02** 15/20 fail with 11 breaches,
C-01∧C-02∧C-04 14/20 with 11, C-01∧C-03 15/20 with 4, and **C-04 ∧ C-06 0/20**. Better training
halves the finding and does not change it in kind: **rule arbitration under simultaneous
activation is a design property of the cage, not a policy defect.** CL-B, non-vetoing (D-30),
carried as future work **T4**.

**Consequently the sim column has no `TBD` left**, and `docs/07` says so explicitly: eleven SRs
Satisfied, two Satisfied on their own criterion with the literal failure recorded and reconciled
(SR-002/003; D-47 + the D-68 metric audit), one **Not satisfied** (SR-010). What stays open is
stated in the same paragraph so it cannot be mistaken for completeness: the whole `verdict_phys`
column (Phase 5 scaffolded but **not run on hardware**, `docs/17`) and **TBD-Q10**
(`ODD-3.A_LAT_MAX`), hardware-gated by construction (D-33).

**`docs/08` → v0.9.1, and a stale claim corrected.** §6.5 still read that the 0.22 m/s contract
"has not been trained"; it has, and it is now the verdict of record. The paragraph now records
what was measured: mean speed **≈0.215–0.218 m/s** (the policy sits essentially *at* the cap),
throttle modulation correctly **localised** to the tightest apex (35.6 % of steps below 0.95 vs
8.3 % overall) but **marginal in magnitude** (floor 0.81). It also records the limitation this
exposes: 0.22 < `V_MAX_CURVE = 0.25`, which is the floor of `v_max(κ)`, so C-04 cannot bind — and
the campaign confirms it, **C-04 firing zero times across all 1890 runs in both modes**. The
ODD-3 speed ceiling therefore remains untested from above *even with speed authority in the
action space*; only the Isaac 0.5 m/s contract would exercise it. The doc stays **below 1.0 by
design**: Q10 is not an outstanding action item but a hardware dependency, since in Gazebo
`A_LAT_MAX` is a consequence of the friction coefficient the world assumes.

**Two findings promoted into the specs they belong to.** `docs/04` gains the C-06 result — on the
300 s endurance scenario the 2-D policy holds the two tightest apexes with a ledger of
`{C-06: 58124}` and **zero C-01/C-02/C-03/C-05**, while the same command stream leaves the lane in
17/25 runs with the cage off — so "the cage is latent in-ODD" is a statement about the **safety
rules**, not about the cage, and the coupling to a specific `delta_max_steering_per_cycle` is a
declared physical-transfer risk (T2). `docs/06` gains the D-64 metrology closure and the D-68
metric correction.

### Rationale

A TBD is a claim that the instrument is missing. Both instruments now exist — the stall metrology
(D-64) and the wired co-activation grid — so continuing to abstain would turn an honest gap into a
convenient one. Recording SR-010 as `Not satisfied` costs nothing the work is entitled to keep
(CL-B, vetoes no global verdict, no SR-CL-A safety predicate involved) and buys the register its
credibility: the document that reports 0 in-ODD road-edge contacts also reports the one
requirement that is not met.

### Impact

The simulation programme is closed; what remains is F5 (physical). **Deliberately not done:** G4 is
not reopened, no historical campaign is re-scored, no ODD parameter / SR threshold / cage rule /
`cage.yaml` value changes, no physical verdict is asserted, and **Chapter 8 is not restructured**
— that item stays open. `cage.yaml` remains at 0.6.1.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (before and after). The
SR-010 numbers are read from
`experiments/sim/campaign_2d_ppo550k/failure_mode_breakdown.json` → `sc_edge05_grid_split_enforcement`;
the C-04 claim is aggregated directly from the 1890 per-run `summary.json` ledgers rather than
inferred from the cap arithmetic.

---

## [31.07.2026] — The 2-D PPO 550k verdict campaign closes; manuscript brought up to the 2-D state and the steering-only figures retired

**Document(s) affected:** `experiments/sim/campaign_2d_ppo550k/` (`campaign_report.json`, `failure_mode_breakdown.json`, `figures/`, new `CAMPAIGN_2D_PPO550K_ANALYSIS.md`), `docs/DECISIONS.md` (D-66 outcome, D-67 condition resolved), `docs/11_camera_rl_training.md`, `tools/plot_campaign_contrast.py` (new), `tools/plot_f3_figures.py`, `manuscript/` chapters 7–12, `manuscript/figures/` (2 PNG + 2 new SVG sources + 3 `.mmd` + `DESIGN_PROMPTS.md`).
**Phase:** E5 (posterior).
**Gate context:** does **not** reopen G4; the GE4-V2 gate record stands.
**Author:** Samuel Sanchez

### Change

**The campaign closed.** `campaign_2d_ppo550k` finished on 31.07.2026: **1890 runs, 0 errors**, 27
`complex_b` scenarios × {enforcement, monitoring}, seed 2024, on the PPO 2-D camera policy at cap
0.22 m/s, checkpoint 550k (D-66). Global **`NOT SATISFIED` (literal)**, blocked by **SR-002/003 only**
and only through SC-EDGE-01's oval-legacy 2.0 s recovery clause — 0 emergencies there, max M-S1
0.043 m ≪ 0.16 m, max heading 14.2° ≤ 25° — so the D-47 reconciliation applies verbatim, and SR-011
with it (σ_θ 3.77° < 5°). 8/10 SR-CL-A Satisfied; SR-006 Satisfied out-of-band (840/840 enforcement
runs within the C-06 bound vs 263/945 monitoring); SR-009 `insufficient_evidence` **by protocol**
(SC-PERT-03 excluded, closed at D-64). **In-ODD road-edge contacts in enforcement: 0**; the bare
policy commits 60 and the cage removes all of them with 406 controlled stops. Out-of-ODD: 56 vs
GE4-V2's 117. Analysis written to `CAMPAIGN_2D_PPO550K_ANALYSIS.md`.

**Manuscript brought up to the 2-D state.** Ch.7 §7.2.2 now specifies the action map as configuration
(`steering` 1-D vs `steer_throttle` 2-D, cap 0.22, deadband 0.05) instead of declaring a 1-D action
"common to both tracks"; §7.5.5 embeds the 2-D training curve (Fig. 7.10) and a new Fig. 7.11.
Ch.8 gains **§8.9.9** with the verdict above, and the stale claims that the 2-D SC-PERT-03 test and
2-D campaigns were "not yet run" were corrected in §8.5, §8.6, §8.9.3 and the internal checklists.
Ch.9 §9.2.1 no longer calls the 2-D action an Isaac-only extension; Ch.10 SR-009 row and the bounded
declaration updated; Ch.11 (61 decisions, checkpoint-selection evidence) and Ch.12 (T1/T6 rewritten,
Hallazgo 5 extended, **Hallazgo 13** added) follow.

**Steering-only figures retired.** `etrack_camera_control_loop` and `camera_cnn_ppo_architecture`
showed the policy output as steering alone; both now show the 2-D action, in the `.mmd` structure
source, the inline copies in `docs/11`, the design prompts, **and the shipped PNGs** — which were
rebuilt from new versioned SVG sources rendered with headless Chrome, so those figures are
re-derivable for the first time (command in each `.mmd` header). `sim2real_roadmap` (Fig. 8.2) lost
its stale "SR-009 stall test … (not yet run)" and gained the Gazebo 2-D arm.

**Tools.** New `tools/plot_campaign_contrast.py` (per-scenario pass fraction + the safety-invariant
split, fully data-driven, works on any campaign dir). `tools/plot_f3_figures.py` renders one panel
per action dimension and takes `--action-run/--action-stem`. Note recorded in the analysis doc:
`plot_camera_comparison.py` is **not** reusable here — its annotations are hard-coded to the GE4-V1
narrative and are false for this campaign.

**New finding out of the SC-NOM-03 anomaly — Hallazgo 14 (Ch.12 §12.2.3, Ch.8 §8.9.9).** The
*competent* policy is the only one that cannot hold the 300 s endurance run **without** the cage
(17/25 `off_road`, against 25/25 completed by the weak margin022 and 24/25 by the 1-D E-main). The
failures are geometric, not accumulative: two arc-lengths (s ≈ 9.4 m and 17.2 m, the two tightest
apexes, the same pair that forced T3) and the jerk *falls* in the last 5 s (0.172 vs 0.411) — a
sustained over-steer. Enforcement and monitoring differ only in C-06: same raw command
(|steer| max 1.00), applied steer 0.84 vs 1.00, per-cycle Δ 0.15 vs 2.0, |ey| max **36 mm vs 145 mm**.
Across the 25 enforcement runs the intervention ledger is `{C-06: 58124}` with **zero**
C-01/02/03/05: in those apexes the lane is held by the **rate limiter**, formally a CL-B *smoothness*
rule. The policy's raw command is ~2× jerkier than its predecessors' (0.33–0.41 vs 0.16–0.19) and
saturates C-06 in 77.5 % of steps; speed does not explain it (+7.5 % over the E-main, which survives).
Consequences recorded: "the cage is latent in-ODD" is true of the **safety rules**, not of the cage
as a whole; the coupling to a specific `delta_max_steering_per_cycle` is a **physical-transfer risk**
now written into T2; and a 300-step nominal eval passes 50/50 in monitoring, so it cannot detect the
property. The dependence is measured, its origin (co-adaptation to the limiter in the training loop)
is inferred — the ablation that would prove it has not been run.

**Correction.** The Fig. 7.11 caption first said the 2-D policy "brakes in curves". Measurement
refines that: throttle modulation is correctly localised (35.6 % of steps below 0.95 at the tightest
apex vs 8.3 % overall) but marginal in magnitude — throttle floor 0.81, speed 0.218 → 0.216 m/s — so
the policy reaches the tightest curves essentially at the cap. Caption fixed.

**D-68 — the heading-recovery metric was audited and corrected.** SC-EDGE-01's
`time_to_recovery_heading` is the single cause of the literal `NOT SATISFIED` in both camera
campaigns, so it was checked rather than excused. It had a real defect: the recovery band was a
*fixed* 0.05 rad (2.86°) calibrated on the F-track PD controller on the oval, and since heading error
ripples about zero with a controller- and track-dependent amplitude (p90 3.0–4.8°), requiring five
consecutive in-band samples tests **ripple**, not recovery — applied to **unperturbed** runs it fails
outright (50/50 oval SC-NOM-02 "never recover", median 12.2 s). The band is now the run's own
steady-state envelope, `clamp(p95(|epsi|) over the last 50 %, floor 0.05 rad, cap σ_θ_max = 5°)`
(`scenario_metrics.heading_recovery_band_rad`); v1 stays selectable and reproduces the historical
records bit-exactly (**120/120 runs verified**). The rule was pre-registered and applied **once**,
with its acceptance test fixed in advance (false positives on unperturbed scenarios must collapse —
they do, 0/50 → 50/50).

**No verdict changes, and the correction favours the arm we do not present.** Re-scored
(`tools/rescore_recovery_clause.py` → `campaign_2d_ppo550k/rescore_recovery_clause_d68.json`):
SC-EDGE-01 goes 17/30 → **28/30 (pass)** on the frozen 1-D GE4-V2 arm but only 8/30 → **15/30 (still
fail)** on the 2-D PPO 550k. Historical campaigns are **not** re-scored (D-30/D-47 precedent; G4
untouched). The useful consequence: the 550k's SC-EDGE-01 failure is **not** a measurement artefact —
its recovery genuinely rings (13.6° → 1.4° → 5.9°, settling ≈2.5 s) on a **straight** (reference
curvature 0.00), the closed-loop signature of Hallazgo 14's bang-bang command stream under C-06 slew
limiting. Still a performance property, not a safety one. The 2.0 s **bound** is deliberately left
alone: this fixes a measurement, not a pass bar. Propagated to `docs/05` (SC-EDGE-01 + the recovery
note), Ch.8 §8.9.9, Ch.12 T7(a) and the campaign analysis. Test baseline 602 → **608**.

### Rationale

The campaign existed to separate "limit of the 2-D action" from "limit of that policy" (D-65 ran on a
weak, decayed SAC checkpoint). It answered in both directions: availability failures **cleared**
(SC-NOM-03 20/25 → 25/25 with zero emergencies; SC-PERT-05 30/40 → 40/40; all 12 SC-PERT enforcement
verdicts True) while the **structural** residuals persisted — the inherited SC-EDGE-01 clause and
SR-010 co-activation (attenuated 30/85 → 16/85 in-ODD M-S1 breaches, unchanged in kind). The
manuscript edits follow from the same evidence; the figure work is the part a reader sees first.

### Impact

D-67's trunk decision was recorded **conditional** on this verdict; the condition is now met and the
entry says so. Two deliberate follow-ups are unblocked but **not** taken here: re-pointing the
`verdict of record` in `docs/02`–`docs/08`, and restructuring Chapter 8 so the camera track leads.
The frozen 1-D verdict (GE4-V2) and the G4 record are untouched. The 29.07 concurrency incident
remains documented: 222 quarantined runs, re-executed under a `flock`-guarded serial driver.

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings**. Campaign roll-up: 1890 runs,
0 errors. `tools/campaign_e_failure_modes.py` and `tools/sr006_smoothness.py` re-run against this
campaign; both figures regenerated from the campaign's own artefacts.

---

## [30.07.2026] — Repo audit + D-67: the 2-D PPO policy becomes the research trunk; earlier arms reclassified as development history

**Document(s) affected:** `docs/DECISIONS.md` (**D-67**), `docs/16_defense_compendium.md` (new §8, old §8 → §9, v1.2), `CLAUDE.md` (trunk banner + phase-status rewrite + docs/17 in the index), `docs/15_implementation_inventory.md` (test baseline, §4.5, `calibrate_d43_c02`), `docs/11_camera_rl_training.md` (§8 path note), `.gitignore`. **`manuscript/` deliberately untouched.**
**Phase:** E5 (posterior) → thesis scoping.
**Gate context:** does NOT reopen G4; the gate record stands.
**Author:** Samuel Sanchez

### Change

Two things: a full repository consistency audit, and the scoping decision it fed into.

**D-67 — trunk of record.** The **2-D PPO camera policy** (cap 0.22, checkpoint 550k, D-66) is now the
research trunk: what the defense presents and what the framework is evaluated/verified against.
The three earlier arms are reclassified from parallel results to development history — F-track =
method validation (perfect-perception control arm), 1-D GE4-V2 = predecessor + verification data,
SAC/cap probes + margin022 = findings-with-fixes. Recorded in `docs/DECISIONS.md`, narrated for the
defense in `docs/16` §8 (one-sentence answer, per-arm role table, the "why isn't the earlier work in
the thesis" argument, and the "you cherry-picked the best arm" rebuttal), and surfaced as a banner at
the top of `CLAUDE.md`'s phase status. **By author instruction this is repo-only: none of it goes into
`manuscript/`**, since enumerating four arms as prose is the text bloat the decision exists to avoid.

**Audit fixes.** (a) `docs/15` test baseline refreshed **517 (15.07) → 602 (30.07)** with per-directory
counts (139 + 437 + 7) — the file's own instruction is to regenerate it before each Gate/defense
rehearsal, and it was 85 tests stale. (b) `docs/15` §4.5 added for the Phase-5 nodes (`csi_camera_node`,
`rl_policy_node`) and `tools/calibrate_d43_c02` added to the tools table — all three were absent.
(c) `docs/17` added to `CLAUDE.md`'s "Where to look first" table (it was missing entirely).
(d) `CLAUDE.md`'s E5 bullet rewritten: it still described the margin022 qualification as "ready but
unexecuted" with a "Next:" plan that had been executed two weeks earlier. (e) The dangling checkpoint
path documented (below). (f) `.gitignore` now covers the campaign driver's `.campaign.lock` and
per-session `*.log`, which were showing up as untracked.

### Rationale

Presenting four arms in parallel would give the defense four competing headline numbers across three
tracks, two observation modalities and two action spaces — where laps are not comparable across tracks
(oval 8.79 m vs complex_b 19.22 m) and `|ey|` is not comparable across observation modalities. The
earlier arms are more valuable as *controls* than as results: they are what makes the cage claim
non-trivial, since the in-ODD invariant is shown to hold across algorithm, seed, observation and
action space. And the failures they surfaced are the contribution of a runtime-assurance thesis, so
they belong in the development narrative as findings-with-fixes, not in a second results chapter.

### Impact

**The trunk claim is conditional and is recorded as such.** `campaign_2d_ppo550k` was still executing
when D-67 was written (1435/1890 cells at 09:50). The 2-D arm has a nominal evaluation (5.32 laps,
`|ey|` 8.6 mm, 0 emergencies, 0 safety interventions) and a D-43 preflight PASS, but **no verdict** —
D-67, `docs/16` §8.5 and the `CLAUDE.md` banner all say so explicitly. If the campaign returns a worse
in-ODD safety picture than GE4-V2's, the trunk decision must be revisited rather than defended.

**Two deliberate non-actions, both recorded in D-67 rather than done silently:**

1. **`docs/02–08` still name GE4-V2 the "verdict of record".** That is historically correct for the
   gate it closed. Re-pointing six spec documents at a campaign whose verdict does not yet exist would
   be premature; it is a deliberate post-verdict edit.
2. **Chapter 8's structure contradicts the decision** — §8.1–8.8 are F-track results and the whole
   camera track is demoted to §8.9, i.e. the inverse of the new priority, and the 2-D PPO campaign has
   no section at all. Restructuring it is the largest pending authoring task and only makes sense once
   the verdict is in hand.

**Audit finding worth its own note — provenance holds by hash, not by path.** The 1-D
verdict-of-record checkpoint is at `experiments/sim/training/ppo_newcam_complex_b_2024/checkpoints_peak/`,
but all 1970 GE4-V2 run metadata records `…ppo_newcam_complex_b_2024_1M/…`, a directory that no longer
exists (renamed after the campaign ran); `CLAUDE.md` and `docs/11` repeated the dangling path. The
SHA-256 in every `metadata.json` (`44c8e912bb4cb1de…`) was verified against the file at its current
location and **matches exactly**, so the artefact is still identified unambiguously. Docs corrected;
the run metadata is left alone on purpose — it is the immutable run record, and the resolution rule
(by hash) is now written down in `docs/11` §8.

**Known structural debt, not fixed:** `CLAUDE.md` is **316 lines** against its own "<250, split if
>200" rule. Compressed the superseded 425k, F-track and GE4-V2 bullets (whose detail lives in docs/11
and the CHANGELOG) to offset the new content, but a real split into `CLAUDE_*.md` remains open.

### Verification

`tools/check_traceability.py` **PASS, 0 warnings** (12 hazards, 14 SR, 6 cage rules, 19 metrics —
all re-counted from `docs/data/*.csv` and `docs/06` and confirmed against the totals CLAUDE.md
claims). `sync_hazard_register.py` + `sync_safety_requirements.py` re-run: **both CSVs already
byte-identical**, so no drift from the Markdown sources. **602 pytest passed.** Markdown link check
over `docs/*.md` + `README.md` + `CLAUDE.md` + `TRACEABILITY.md`: **0 broken links**.
`cage.yaml` 0.6.1 / `compatible_sr_spec_version` 1.0 consistent with
`_ACCEPTED_SR_SPEC_VERSIONS`. 27 `experiments/**` paths cited in docs do not exist on this host;
all but the checkpoint path above are gitignored artefacts, historical CHANGELOG references, or
illustrative examples (docs/01's `SC-NOM-01_enforcement/run_007`). No code changed, so the running
campaign is unaffected — verified still executing as a single process throughout.

## [30.07.2026] — Physical deployment completed end-to-end: CSI lane camera published (`csi_camera_node`), platform bring-up layering, ROS→JSON serial actuation

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/csi_camera_node.py` (new), `policy/tests/test_csi_camera_node.py` (new), `src/cobraflex_rl/setup.py` (entry point), `src/cobraflex_rl/launch/deploy_cobraflex.launch.py`, `src/cobraflex_rl/package.xml` (exec_depend), `src/cobraflex/launch/cobraflex_bringup.launch.xml` (arg forwarding), `docs/17_physical_deployment.md` (§1 table, new §1b, §2 prerequisites, new §2b, §3 bring-up, §4 step 0).
**Phase:** E5 → Phase 5 (deployment preparation).
**Author:** Samuel Sanchez

### Change

Closed the two ends of the physical chain that were still open — the image source and the
actuation sink — and aligned the RL deployment with the CobraFlex package's own bring-up layering.

**1. `csi_camera_node` (new).** The physical chain had no publisher for the lane camera:
`rl_policy_node` and `cv_lane_estimator_node` both *subscribe* to an Image topic, but the Jetson CSI
device is opened *inside* `cobraflex.lane_keeper_node`, which also publishes `/cmd_vel` and so could
not be reused as an image source. The new node publishes `camera/image_raw_lane` + `camera/camera_info`,
reusing `lane_keeper_node`'s GStreamer pipeline **byte-identically** (asserted in a unit test) and its
640×360 `INTER_AREA` downsample, and deriving the advertised `CameraInfo` intrinsics from the very
`CameraModel` the cage's IPM uses so the two cannot drift. Output size defaults come *from*
`camera_geometry`, and a non-default size logs an error: 640×360 is a hard contract because
`cv_lane_estimator` falls back to `CameraModel()` and indexes its scan bands by `camera.height_px`.

**2. Bring-up layering.** Audited every launch file in `cobraflex` and documented the layering in a
new docs/17 §2b: **Layer 1** `cobraflex_bringup.launch.xml` (= `cobraflex_description`
[robot_state_publisher + joint_state_publisher + rviz] + `cobraflex_driver` [`cobraflex_ros_driver`]),
**Layer 2** `cobraflex_sensors.launch.xml` (SLLIDAR A2M8 + ZED Mini), **Layer 3** a controller
(`cobraflex_lane_keeper.launch.py`, `cobraflex_automatic.launch.xml`, or the RL chain).
`deploy_cobraflex.launch.py` is now an explicit Layer-3 launch: it starts `csi_camera_node`
(`camera:=false` to use an external source) and can include Layer 1 via `bringup:=true` (default
**false** — attach to a running bring-up, as `cobraflex_lane_keeper` does), forwarding
`serial_port` / `baudrate` / `use_rviz`. `cobraflex_bringup.launch.xml` gained `serial_port` /
`baudrate` args (defaults identical to the driver's, no behaviour change) so a caller can retarget
the device. Added `<exec_depend>cobraflex</exec_depend>` to `cobraflex_rl`.

### Rationale

The RL policy must see the same camera and actuate through the same interface as every other
CobraFlex controller (PD, CV): it keeps both ends of the chain out of the comparison, and the A2
cage-independence argument then covers the full path from pixels to the serial link.
`cobraflex_ros_driver` was already a complete, entry-pointed node reached through Layer 1 — but
nothing in the RL chain referenced it, so the deploy chain stopped at `/cmd_vel` and listed "a motor
driver" as an external prerequisite. On the image side the situation was worse: docs/17's "a camera
driver publishing frames on `camera_topic`" papered over the fact that no such node existed at all.

Crucially, the sim mirrors the hardware here and not the reverse: the Gazebo `Lane Cam` sensor's own
comment states *"proc frames 640×360, effective hfov 90 deg, timer 20 Hz; capture is 1280×720@60 but
only the processed stream matters"*, and those are `lane_keeper_node`'s parameter defaults. So
reproducing the hardware path **is** reproducing the training distribution — no adaptation of the
camera settings was needed, only a node that publishes them without also driving the car.

### Impact

**Scaffolding only — still NOT run on hardware, but no longer blocked.** The observation contract is
now single-sourced and consistent across all three places it appears (`Lane Cam` sensor,
`camera_geometry` defaults, `lane_keeper_node` params): 640×360, HFOV 90° (1.5707963 rad), 20 Hz,
capture 1280×720@60 → `INTER_AREA`, optical frame `camera_link_optical_lane`, mount pitch 0.30 rad /
height 0.07725 m, observation 84×84 grey k=4. `csi_camera_node` publishes `bgr8` where the sim sensor
emitted `R8G8B8` — not a difference, since `decode_image` normalises both to the same BGR array.
Actuation is topic-compatible with no change to the driver: `vehicle_control_node` publishes
`/cmd_vel` (Twist), the driver emits `{"T":13,"X":vx,"Z":wz}` clamped ±0.53 m/s / ±6.0 rad/s, so the
deployed 0.22 m/s contract is never clamped. Documented the **fail-safe chain**: no frames →
no `/raw_action` → (it is `cage_ros_node`'s cycle trigger) no `/safe_action` →
`vehicle_control_node`'s `safe_action_timeout_s` (0.5 s) publishes a zero Twist → the driver's
keep-alive re-sends zeros; a dead camera stops the car without the e-stop.

The audit surfaced three findings, all recorded in docs/17:

1. **[VERIFY — highest priority] The 90° effective HFOV.** It originates as a *parameter default* in
   `lane_keeper_node` (`camera_hfov_deg` 90.0) for an IMX219-**160** wide-angle lens, and the Gazebo
   sensor mirrored it — so if it is wrong, sim and hardware are wrong the same way and **no sim result
   can expose it**. `CameraModel.fx = (w/2)/tan(hfov/2)` = 320 px at 640×360 and the IPM's metric
   output scales with it, so a wrong HFOV means C-01's 0.12 m threshold does not mean 0.12 m. The
   published `CameraInfo` is deliberately the ideal pinhole the cage assumes (no distortion terms),
   since measured intrinsics would contradict the IPM — both must be reconciled, not just extended.
2. **[VERIFY] `steering_to_yaw_rate_gain` = 0.8** was calibrated against the **Gazebo DiffDrive
   plugin's** reading of `angular.z` and has never been compared with the firmware's `Z` on the real
   Ackermann chassis. Re-calibrate before the cage's C-02/C-03 margins mean anything on hardware.
3. The driver has **no `/cmd_vel` watchdog** (`_resend_last_cmd` re-sends the last command every
   50 ms as a firmware keep-alive). `vehicle_control_node`'s `safe_action_timeout_s` covers the cage
   dying, but a death of `vehicle_control_node` itself leaves the car driving on its last command —
   the hardware e-stop is the only mitigation, reinforcing why it is mandatory. Driver left untouched
   (no atomic-stop change) because it is shared platform code and nothing is validated on the car.

Two mutual-exclusion hazards documented rather than papered over: `bringup:=true` on top of a running
Layer 1 starts a **second** `cobraflex_ros_driver` (Linux does not lock `/dev/ttyACM*`, so both
interleave JSON writes and keep-alives with no error — hence the `false` default), and
`cobraflex_lane_keeper.launch.py` must never run alongside the RL chain (same CSI device, competing
`/cmd_vel`). `lane_keeper_node` itself was left untouched: its camera settings already match training,
and it remains the classical HW baseline.

### Verification

**602 passed** (594 + 8 new host-side tests for `csi_camera_node`'s pure logic: 640×360 output
geometry, 16:9 aspect preservation so the HFOV survives the downsample, no-op at target size,
non-BGR rejection, `to_observation` shape round-trip, `CameraInfo` K/P derived from `CameraModel`,
`fx` = (w/2)/tan(hfov/2), and byte-identity of the GStreamer string with
`lane_keeper_node._gstreamer_pipeline` — that last one `importorskip`-guarded, since `cobraflex` is
an `ament_python` package importable only after a colcon build). `py_compile` on the node and the
launch; `generate_launch_description()` executed under a sourced ROS 2 Jazzy env — 14 args, **6
nodes**, 1 include forwarding `serial_port`/`baudrate`/`use_rviz`; the include resolves to
`install/cobraflex/share/cobraflex/launch/cobraflex_bringup.launch.xml` and
`AnyLaunchDescriptionSource` parses it (5 entities, args `use_rviz`/`serial_port`/`baudrate`),
confirming the forwarding patch. `package.xml` well-formed. `tools/check_traceability.py` PASS, 0
warnings (no ID change). **Nothing launched and no GStreamer capture exercised**: that needs the
Jetson, and a `colcon build` was deliberately deferred because the `campaign_2d_ppo550k` campaign is
running and spawns `ros2 launch` per run out of the same `install/` tree.

## [27.07.2026] — Competent 2-D policy: PPO cap 0.22 (reward 1755); best checkpoint by reward+cage%; campaign launched

**Document(s) affected:** `experiments/sim/training/ppo_gz2d_cap022_1M_2024/` + candidate evals + `experiments/sim/campaign_2d_ppo550k/` (new), `src/cobraflex_rl/config/train_ppo_camera_2d_cap022_1M.yaml` (new), `docs/DECISIONS.md` (D-66), Ch.7 §7.5.5, `manuscript/figures/auto/fig_ppo2d_training_curve.png`.  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4; frozen 1-D verdict untouched.  
**Author:** Samuel Sanchez  

### Change

Trained a proper 2-D camera policy (PPO, cap 0.22, 1M, checkpoints/25k), stopped at 700k, selected the best checkpoint by deterministic driving + cage intervention, ran its D-43 preflight, and launched its verdict campaign — to contrast a competent 2-D driver against the weak margin022 (D-65).

### Rationale

The margin022 verdict ran on a weak SAC policy AND a decayed checkpoint (75k, past its ~54k peak). PPO (not SAC) at cap 0.22 fixes both: SAC 2-D never exceeds ~200 (crashes at ~0.28 laps); PPO 2-D reaches 1755 and a stable plateau (5.3 clean laps). A single-variable diff shows only the cap changed vs the sloppy 0.5 run (654) — the slow cap lets the policy trace the tight curves cleanly.

### Impact

**PPO 2-D peak ep_rew 1755 @ 472k** (vs SAC ~200, 1-D E-main 823). Cage LATENT for safety across training (C-01/02/03/05=0). Candidate selection was decisive: **the reward-peak 475k is NOT best** (14 safety interventions, max|ey| 49mm); **550k wins** (5.32 laps, |ey| 8.6mm, max 27mm, 0 emerg, **0 safety interventions**, smoothest). Selecting on reward alone picks the worst — validates using cage%. 550k D-43 preflight (cage joint_pair+1.60+T3, = margin022) **PASS** (7/7). Campaign launched (`campaign_2d_ppo550k`, 27 scenarios × {enf,mon} = 1890 runs; SC-PERT-03 excluded, closed D-64; SR-009 D-29-feasible). Honesty: the ~2× reward vs 1-D is mostly the 2048-vs-1024 step cap + longer survival (per-step 1.165 vs 1.040), not 2× better driving. Figure + D-66 detail.

### Verification

Preflight PASS (7/7). Nominal evals of 3 candidates. `--resume` campaign (pausable/chunkable). 594/594 pytest, `tools/check_traceability.py` unaffected. Campaign verdict PENDING (~28-30h).

## [26.07.2026] — Phase-5 physical-deployment scaffolding (rl_policy_node + deploy launch + docs/17)

**Document(s) affected:** `src/cobraflex_rl/.../rl_policy_node.py` (new), `src/cobraflex_rl/launch/deploy_cobraflex.launch.py` (new), `docs/17_physical_deployment.md` (new), `policy/tests/test_rl_policy_node.py` (new), `src/cobraflex_rl/setup.py` (entry point).  
**Phase:** E5 → Phase 5 (deployment preparation).  
**Author:** Samuel Sanchez  

### Change

Prepared the physical bring-up path for the track-'E' RL camera policy behind the cage. Added the one missing piece — `rl_policy_node` (image → CNN → /raw_action Twist), reusing the exact sim preprocessing (decode_image + to_observation + k=4 stack) so the CNN sees identical observations — plus `deploy_cobraflex.launch.py` wiring the distributed chain (rl_policy → cv_lane_estimator → cage_ros → vehicle_control → cage_logger), and docs/17 with the bring-up checklist.

### Rationale

The last training + eval before deployment; the distributed cage_ros_node already carries the 2-D action (angular.z=steer, linear.x=throttle), so only the inference node + launch + checklist were missing. The cage as a separate process makes the A2 independence argument concrete on hardware.

### Impact

**Scaffolding only — NOT run on hardware.** The node's pure logic (action→Twist mapping, frame stack) is unit-tested host-side (5 tests). docs/17 flags the [VERIFY] items honestly: camera extrinsics (D-57), the 2-D throttle→speed mapping, the e-stop wiring, sim-to-real appearance gap.

### Verification

594/594 pytest (5 new), compile-check on node + launch, `tools/check_traceability.py` unaffected. No behaviour on the physical car is claimed.

## [26.07.2026] — Defense Q&A: the "just a bad policy / bad design" objection (Q14)

**Document(s) affected:** `docs/16_defense_compendium.md` (§7 Extended Q&A, new Q14).  
**Phase:** E5 (posterior) — defense preparation.  
**Author:** Samuel Sanchez  

### Change

Added Q14 to the cross-cutting defense-question bank: the objection that the cage's value is an artefact of a weak policy or a mis-designed reward/scenarios/metrics, with the honest rebuttal.

### Rationale

The strongest examiner objection to the central cage claim; captured with its concession (the intervention *magnitude* is policy-dependent, D-65) and its refutation (runtime assurance exists *because* a learned controller cannot be certified; safety is decoupled from reward by A2; scenarios trace to hazards; metrics are anti-gaming D-47; perception-degradation failures are irreducible by any policy; the longer-training re-run is the empirical control).

### Impact

Documentation only; no code, SR, scenario or metric change.

### Verification

`tools/check_traceability.py` unaffected (no ID changes).

## [26.07.2026] — First full 2-D verdict campaign (margin022): NOT SATISFIED literal, in-ODD safety holds

**Document(s) affected:** `experiments/sim/campaign_2d_margin022/` (new: 1970-run campaign + `CAMPAIGN_2D_ANALYSIS.md` + English figures), `docs/DECISIONS.md` (D-65), Ch.8 §8.9.8, `tools/plot_frontier.py` (bilingual, default now English).  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4; does NOT reopen the frozen 1-D E verdict (GE4-V2).  
**Author:** Samuel Sanchez  

### Change

Ran the first full verdict campaign on the 2-D (steer+throttle) action: margin022 across the 28 complex_b scenarios × {enforcement, monitoring}, seed 2024, 1970 runs, authorised by the T3 D-43 preflight. Reconciled the literal verdict per-SR. Made `plot_frontier.py` bilingual and flipped its default to English.

### Rationale

margin022's qualification (T3 nominal D-43 PASS, D-62; SC-PERT-03 closed, D-64; the 0.22 cap resolving the D-59 speed-envelope kill) unblocked the first 2-D verdict campaign — a posterior E5 contribution, not a re-run of the frozen 1-D verdict.

### Impact

**Global NOT SATISFIED (literal)** — 5 SR Satisfied, 8 not, 1 indeterminate — but **no in-ODD safety breach** (mirrors GE4-V2, D-47). Enforcement road-edge contacts: **in-ODD = 0**, out-of-ODD = 50 (frontier/edge stress). **Cage value larger than 1-D:** the bare 2-D policy commits **98 in-ODD road-edge contacts; the cage removes all** (0 in enforcement) via 433 controlled emergency stops. The 8 failing SRs trace to 4 scenarios, all non-breaches: SC-NOM-03 (5 SRs; cage emergencies on the 300 s endurance run, 0 road-edge — availability cost), SC-PERT-05 (SR-012/014; low-light, cage stops safely under degraded perception), SC-EDGE-05 (SR-010; genuine CL-B co-activation, same as 1-D), SC-PERT-03 (SR-009; documented stall construct, D-64). Net 2-D finding: **safety preserved, availability reduced** — the weaker throttle-commanding policy trips the cage more, always safely. Full analysis: `CAMPAIGN_2D_ANALYSIS.md` (D-65).

### Verification

1970 runs, 0 errors, D-43 preflight PASS embedded. `plot_frontier.py --lang es` still reproduces the Spanish F-track figures bit-identically. No manuscript SR/verdict changed; `tools/check_traceability.py` unaffected.

## [25.07.2026] — SC-PERT-03 metrology closed: stall detector confirmed via a scripted ground-truth stall

**Document(s) affected:** `experiments/sim/runs/sc_pert_03_scripted_stall_2024/` (new), `src/cobraflex_rl/cobraflex_rl/eval_policy.py` (`--scripted-stall`), `docs/DECISIONS.md` (D-64), Ch.8 §8.9.7. Removed the interim `experiments/sim/campaign_sac_pert03/V2_DESIGN_GOAL.md` proposal (root-cause folded into D-64).  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4; does NOT reopen the E verdict.  
**Author:** Samuel Sanchez  

### Change

Reframed SC-PERT-03 (per SR-009: liveness is a TRAINING mitigation, not a cage rule; the test is metrology — does M-P6 detect a stall?). Root-caused the D-63 inconclusive: the v1 adversary reward was internally contradictory (inherited `stall_penalty`=0.5, the SR-009 mitigation, opposing `lambda_stall`=4) and its a-priori λ ignored `clip_reward`+`normalize_reward` — a construction defect, not a cage result. A design-corrected pure-stall-objective pilot (forward_progress=0, stall_penalty=0, λ=4) was run as a one-way gate; when it did not induce a staller, λ was NOT iterated (anti-gaming). Added an opt-in `eval_policy --scripted-stall` mode (fixed full stop [steer 0, throttle -1]) to validate the detector with a ground-truth stall.

### Rationale

Fixing a mis-designed adversary is legitimate (cage untouched, pass bar unchanged); a scripted stall is a clean metrology stimulus, not a fished adversary. It sidesteps wrestling a robust driver into stalling and directly answers the SR-009 question.

### Impact

**Pilot:** the pure-stall fine-tune did NOT stall (ep_rew→−300, ep_len≈241 vs 2048 for a real stall) — the trained policy robustly resists stalling; recorded as evidence, not iterated. **Scripted stall** (`sc_pert_03_scripted_stall_2024`, complex_b, 400 steps, enforcement): mean/max speed 0.0000, **M-P6 = 100.0**, 0 emergencies → the detector fires on a genuine stall. **SR-009 now closes three ways:** (i) released arm drives, M-P6=0 (mitigation works); (ii) policy resists forced stalling (robustness); (iii) M-P6 detects a real stall (metrology sound). Details: D-64.

### Verification

`--scripted-stall` default-off (verdict runs bit-identical; eval_policy compiles + tests green). M-P6 computed by the same `campaign_metrics.compute_run_metrics` as the campaign. No manuscript SR/verdict changed; `tools/check_traceability.py` unaffected.

## [25.07.2026] — T3 D-43/C-02 calibration re-run: fault detection preserved end-to-end

**Document(s) affected:** `experiments/sim/eval_gz2d/d43_c02_calibration_t3/` (new), `experiments/sim/eval_gz2d/runtime_ppo_camera_t3.yaml` (new), `docs/12_cv_lane_keeper.md` (§4.10).  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4; confirmatory, changes no verdict.  
**Author:** Samuel Sanchez  

### Change

Re-ran the §4.9 bounded D-43/C-02 Gazebo calibration with the T3 temporal gate enabled (D-62) as an end-to-end regression check of the T3 change.

### Rationale

The T3 no-mask guarantee was proven offline (t3_parity.py) and in the closed-loop nominal preflight; this exercises it through the calibration harness's injected-fault matrix in Gazebo.

### Impact

**PASS, both splits: 6/6 injected heading faults detected within one 0.10 s cycle, 0 false C-02/C-05, 0 road-edge contacts.** T3 never delays/masks a fault — at injection `cv_ey` drifts > the 0.03 m gate in the same frame, so T3 disengages instantly and the uncapped `cv_epsi` trips C-02/C-05. One diagnostic shifts: the raw `|cv_epsi|` safe-vs-fault separation margin (§4.9 headline +0.074) goes negative (−0.178 held-out) because T3 caps the safe-side curve over-reads (its purpose) and the fault-min picks up post-stop low readings; detection now rests on the temporal gate + C-02 hysteresis on the post-drift signal, not a raw threshold. Safety property preserved. Details: docs/12 §4.10.

### Verification

`report.json` status PASS, blockers []; 28/28 cells, 0 errors. No manuscript SR/verdict changed.

## [24.07.2026] — SC-PERT-03 posterior 2-D campaign: released arm PASS, stall-variant adversary not induced

**Document(s) affected:** `experiments/sim/campaign_sac_pert03/` (new: 80-run campaign + `SC_PERT_03_ANALYSIS.md`), `docs/DECISIONS.md` (D-63), Ch.8 §8.9.6.  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4; does NOT reopen the E verdict.  
**Author:** Samuel Sanchez  

### Change

Ran the preregistered posterior 2-D SC-PERT-03 negative test on the margin022 parent + a 50k stall-penalty fine-tune (λ_stall=4.0, fixed a priori). Fine-tune: `sc_pert_03_protocol.py run` → `stall_variant.zip` (56d235da, distinct from parent 4f3b56e2), manifest finalized+validated. Campaign: 80 runs (20 reps × {released, stall_variant} × {enforcement, monitoring}) via `run_campaign.py --two-arm-manifest`, authorised by the T3 D-43 preflight (`d43_preflight_margin022_2024_75k_t3.json`, PASS). 0 errors.

### Rationale

SC-PERT-03 is the SR-009 stall/liveness negative test: a control arm (released = the deployed policy, must make progress and never stall) and an adversarial arm (stall_variant = fine-tuned to stall, must show M-P6 > 50 % so the cage's stall handling is actually exercised). For the frozen 1-D action stalling is N/A-by-construction (D-49); the 2-D margin022 action (D-50) makes it commandable in principle, so the test is well-posed.

### Impact

**Released arm PASS** — enforcement 18/20 (0.90, meets the bar), monitoring 20/20 (1.00): the deployed policy makes progress (M-P2=1) and never stalls (M-P6≈0). **Stall_variant arm did NOT induce a staller**: across all 40 stall_variant runs M-P6 max 0.79 %, mean 0.03 % (needs >50); the fine-tuned policy still drives ~0.34 laps at |ey|≈0.02 m. Mechanism: under `normalize_reward`+`clip_reward` the fixed λ=4.0 penalty is diluted by the running return scale, so training rollouts went short/negative (exploration off-road) but the deterministic policy kept driving. Per the anti-gaming protocol (λ fixed a priori, `adaptive_tuning: false`), λ is **not** retuned to force a staller — the stall-detection arm is recorded as a characterised inconclusive, not a cage failure; the released arm confirms deployed-policy liveness regardless. **Residual T3 note:** 2/20 released-enforcement runs hit a rare apex-exit CV-ey transient (cv_ey jumps ~3-4 cm while true ey stays ~2 cm) that breaks T3's drift gate BY DESIGN (it must not mask a possible real excursion), letting an uncapped cv_epsi trip a false C-02/C-05; 0/20 in monitoring. Conservative side of T3's no-mask guarantee, not a regression — not loosened. Full analysis: `experiments/sim/campaign_sac_pert03/SC_PERT_03_ANALYSIS.md`.

### Verification

Campaign report `campaign_report.json` (80 runs, 0 errors, D-43 preflight PASS embedded). Derived checkpoint hash verified in per-run metadata (56d235da, criterion_arm=stall_variant). No manuscript SR/verdict changed; `tools/check_traceability.py` unaffected.

## [24.07.2026] — T3 temporal heading gate: margin022 nominal D-43 preflight BLOCKED → PASS

**Document(s) affected:** `docs/DECISIONS.md` (D-62), `docs/12_cv_lane_keeper.md` (§4.10, v0.7), `src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py`, `cage_perception.py`, `gazebo_lane_env.py`, `src/cobraflex_rl/config/train_sac_camera_2d_tuned_entfix_margin022.yaml`, `policy/tests/test_cv_lane_estimator.py`, `policy/tests/test_campaign_contract.py`, Ch.7 §7.5.5.  
**Phase:** E5 (posterior).  
**Gate context:** posterior to G4 (closed 02.07.2026); does not reopen the E verdict.  
**Author:** Samuel Sanchez  

### Change

Added an opt-in **T3 temporal heading-consistency gate** to the D-43 CV lane estimator (`heading_temporal_window`, default 0 → every frozen GE4/G4 config bit-identical). When enabled it caps the reported `|epsi|` to `heading_temporal_cap_rad` (0.32 rad, below C-02's `theta_activate` 0.4014) **only** while the estimator's own `ey` confirms lane-following across the window (centred `|ey| ≤ 0.08 m`, drift-free span ≤ 0.03 m) and real curvature is present (median `|curvature| ≥ 0.30 1/m`). The estimator gains a per-episode `reset()`, called from `CagePerceptionSupervisor.reset()`; the `perception_heading_temporal_*` cage keys wire it through `GazeboLaneEnv`. The margin022 cage block opts in (window 4).

### Rationale

The checkpoint-bound **nominal** D-43 preflight (the gate the margin022 contract requires before a 2-D campaign) **BLOCKED** on the closed-loop `complex_b` trace: 13 centred false C-02 triggers at two tight apices (`s ≈ 8.9`, `16.1`), one escalating to a C-05 emergency. Root cause is the H-12 single-frame overlap — a centred, well-aligned vehicle reads a curve heading (≈ 0.44 rad) *larger* than a genuine fault — which no scalar gain separates and which single-frame curvature subtraction (§4.8) was already rejected for masking. The separable signal is temporal: a genuine heading error drifts `ey` within one cycle (held-out faults jump `cv_ey` > 40 mm at onset), while the geometric over-read leaves a non-drifting vehicle — so gating the cap on confirmed lane-following cannot mask a fault and adds no detection delay. This is an eval-time cage readout (the policy observes the CNN, never `cv_epsi`), so **no retrain**; the campaign-contract fingerprint (action + sac + contract, not `cage`) is unchanged and the existing checkpoint still validates.

### Impact

Offline over the labelled held-out (seed 42) D-43/C-02 cells + the margin022 nominal trace, then confirmed in a **fresh Gazebo closed-loop re-eval with T3 on** (`experiments/sim/runs/rl_sacmargin022_eval_2024_cb75k_4k4_t3/`, `experiments/sim/eval_gz2d/d43_preflight_margin022_2024_75k_t3.json`): **all 7 preflight checks PASS** (0/0), max centred `|epsi|` error 0.361 rad, **0 C-02 / 0 C-05 / 0 emergencies** across the 4400-step trace, 52 apex frames capped at ±0.320 rad at `|ey|` ≈ 5 mm; held-out faults still **6/6 detected, ≤ 1-cycle delay**. Re-eval is cleaner than the blocked original (3.99 vs 2.44 laps, mean `|ey|` 16.9 mm). Unblocks the margin022 fresh-parent → nominal-PASS → fine-tune → campaign path. Scope: hash-bound Gazebo Lane-Cam / `complex_b` envelope; no Isaac parameter reused.

### Verification

`pytest` 589/589 green (6 new T3 unit tests: gate behaviour, no-mask guarantee, reset, default-off bit-identity; updated margin022 controlled-delta contract test). Default-off parity confirmed against the 172-test cage+estimator subset. `tools/check_traceability.py`: unaffected (no H-/SR-/scenario/metric IDs added).

## [22.07.2026] — margin022 parent training launched; manuscript synced to 21–22.07 posterior evidence

**Document(s) affected:** `manuscript/chapters/chapter_02_related_work.md`,
`chapter_03_methodology.md`, `chapter_07_training_specification.md`,
`chapter_08_experimental_evaluation.md` (as-of header only),
`chapter_09_sim_to_real_gap.md`, `chapter_12_conclusions_and_future_work.md`.
No code/config/scenario, hazard/SR table, CSV or cage constant changed.
**Phase:** posterior E5 — Gazebo D-43 qualification / manuscript consolidation
**Gate context:** after G4; GE4/G4 frozen
**Author:** Samuel Sanchez

### Change

Two threads. (1) **Training:** the fresh 75k SAC 2-D `margin022` parent began
training on Gazebo `complex_b` (`run_id: sac_gz2d_entfix_margin022_2024_75k`,
seed 2024), the checkpoint the 21.07 D-43->C-02 calibration enabled; in progress
at write time, no qualified checkpoint or campaign result yet. (2) **Manuscript
sync to current date:** ch7 §7.5.5 records the D-43->C-02 measurement-interface
PASS and the in-progress parent (with a `[RESULTADO PENDIENTE — F5]` marker);
ch9 §9.2.2 adds the D-43 Gazebo calibration as a same-class perception-vs-renderer
discrepancy that reinforces adaptation A5 (with a `[FIGURA SUGERIDA]` pointer to
the existing calibration plots); ch12 T1 updates the margin022/preflight status.
**Literature attributions (verifiable only, no fabrication):** ch2 §2.3.2 adds
the canonical architectural lineage of the safety-cage/runtime-filter family
(Simplex — Sha 2001; shielding — Alshiekh et al. 2018); ch3 §3.3 adds the
systems-engineering root of the V-Model (Forsberg & Mooz 1991) alongside the
existing IEEE/ISO attribution.

### Rationale

Keep the manuscript current with the 21–22.07 posterior evidence and satisfy the
supervisor-facing requirement to attribute borrowed ideas (cage/Simplex/shield,
V-Model) with real, verifiable references — placeholders (`[CITA PENDIENTE]`)
reserved for anything not confidently attributable. None of this reopens G4.

### Impact

Manuscript only; the GE4-V2 verdict of record and all G4 statements are
unchanged. Pending items remain marked in-text: margin022 nominal + checkpoint-bound
D-43 preflight + SC-PERT-03 80-cell campaign (F5), and the physical column of the
sim-to-real gap table (F5).

Additionally, three `[FIGURA SUGERIDA]` placeholders were added where a visual
would strengthen the argument and the underlying data already exists (ch9 §9.2.2
D-43 calibration scatter/distribution; ch7 §7.5.5 SAC entropy/replay mechanisms;
ch2 §2.3.5 four-families taxonomy). Eleven of the less-canonical ch2 citations
were spot-checked against the literature and all are real and correctly
attributed (author + title + venue); the only nuance is Vasudevan et al., whose
proceedings year is 2022 (UKCI 2021) vs the cited 2021 — flagged, not corrected.

### Verification

`tools/check_traceability.py` → PASS (no IDs, CSVs or tables touched).

---

## [21.07.2026] — D-43 heading estimator improved; moving-fault validation PASS

**Document(s) affected:** `docs/12_cv_lane_keeper.md`; `docs/DECISIONS.md`
(D-59 follow-up); `tools/README.md`; D-43 estimator/env/eval sources; posterior
margin022 config; calibration tool/tests; bounded evidence under
`experiments/sim/eval_gz2d/d43_c02_calibration_20260721T082128Z/`.
**Phase:** posterior E5 — Gazebo D-43 qualification
**Gate context:** after G4; GE4/G4 frozen
**Author:** Samuel Sanchez

### Change

Added an opt-in joint two-boundary quadratic heading fit and a hash-bound Gazebo
measurement gain of 1.60. Added a calibration-only moving yaw injector, simulator
timestamps and post-emergency observation so detection delay, controlled stopping,
M-S1/M-S2 and road-edge contact are measured rather than inferred from a stationary
spawn. The untrained margin022 contract explicitly selects the candidate; frozen
defaults and historical configs remain unchanged.

### Rationale and result

The held-out dynamic split is **PASS**: 6/6 positive/negative real heading-fault
cells detected at a minimum pre-injection speed of 0.220 m/s, 0 false C-02/C-05
over 392 centred-safe cycles, 0 M-S2 cycles, 0 road-edge contacts, maximum M-S1
0.03177 m, maximum detection delay 0.10 s and controlled-stop upper bound 0.10 s.
Safe and faulty `|epsi_cv|` distributions are separated by 0.07438 rad. The
canonical 25-degree/20-degree thresholds and `d_max`/`t_min` are unchanged.

### Impact

The D-43 measurement interface is qualified only for the recorded Gazebo Lane
Cam/renderer/`complex_b` envelope and hashes. This does not qualify a policy:
the margin022 checkpoint still does not exist and its mandatory checkpoint-bound
nominal D-43 preflight remains. GE4/G4 and Isaac-specific settings are untouched.

### Verification

Targeted estimator, env, logging and calibration tests; bounded Gazebo matrix;
traceability and whitespace checks are recorded with the working-tree handoff.

---

## [21.07.2026] — D-43/C-02 controlled-heading calibration BLOCKED

**Document(s) affected:** `docs/12_cv_lane_keeper.md`; `tools/calibrate_d43_c02.py`; targeted tests; bounded evidence under `experiments/sim/eval_gz2d/d43_c02_calibration_20260721T073151Z/`.
**Phase:** posterior E5 — Gazebo D-43 qualification
**Gate context:** after G4; GE4/G4 frozen
**Author:** Samuel Sanchez

### Change

Added a reproducible 28-cell Gazebo calibration with disjoint calibration and
held-out seeds, controlled spawn-heading faults, curvature/speed/visual coverage,
per-cycle GT-oracle/CV/cage logging, hashes, raw CSV, JSON report and figures.
No estimator, cage threshold, verdict scenario or GE4 artefact was changed.

### Rationale and result

The retained split is **BLOCKED**: 0 false C-02/C-05 in the centred band and 0
contacts, but positive heading faults were missed at both tested non-zero
curvatures. Safe and faulty `|epsi_cv|` overlap by 0.02190 rad and the mean
CV-GT error varies from -0.0016 rad on the straight to -0.1741 rad at the
maximum tested curvature. This rules out a static Gazebo bias and a safe global
threshold; raising 25 degrees or subtracting curvature would further hide real faults.

### Impact

D-43 remains a fail-closed prerequisite for the untrained margin022 posterior
checkpoint. Required next evidence is either an improved estimator with a
separately observable tangent/vehicle heading or a conservative curvature/radius
validity envelope wired to `perception_invalid` and validated for SR-005/SR-008.
No GE4/G4 statement changes.

### Verification

Targeted D-43/plausibility/calibration tests pass; traceability and scoped
whitespace checks are recorded with the working-tree handoff.

---

## [20.07.2026] — Gazebo 2-D qualification made executable: fresh 0.22 contract, checkpoint-bound D-43 preflight and preregistered SC-PERT-03 two-arm protocol

**Document(s) affected:** `docs/05_scenario_library.md`; `docs/06_metrics_catalogue.md`; `docs/07_traceability_matrix.md` (post-G4 annotation only); `docs/08_odd_specification.md`; `docs/09_environment_design.md`; `docs/10_reward_function.md`; `docs/11_camera_rl_training.md`; `docs/14_isaacsim_handover_spec.md`; `docs/15_implementation_inventory.md`; `docs/16_defense_compendium.md`; `docs/DECISIONS.md` (D-49/D-59 follow-up); `README.md`; `AGENTS.md`; `CLAUDE.md`; `policy/README.md`; `tools/README.md`; `experiments/README.md`; Chapters 7, 8, 11 and 12. **Code/config/scenario:** campaign/training/eval/reward surfaces under `src/cobraflex_rl/`; `tools/run_campaign.py`; `tools/sc_pert_03_protocol.py`; `tools/d43_preflight.py`; both SC-PERT-03 YAMLs; `scenarios/_sc_pert_03_protocol.yaml`; `train_sac_camera_2d_tuned_entfix_margin022.yaml`; associated tests. **Derived evidence:** `experiments/sim/eval_gz2d/d43_*.json`.

**Phase:** posterior E5 — Gazebo 2-D qualification / SR-009 meta-test preparation

**Gate context:** after Gate G4; GE4-V2 and `docs/07` remain frozen.

**Author:** Samuel Sanchez

### Change

- Added a **fresh-training-only, bounded 75k** SAC-entfix 2-D contract at
  0.22 m/s: minimum 0.03 m/s below C-04's 0.25 m/s curve ceiling, 150k replay
  buffer covering the 75k parent + fixed 50k continuation, action/horizon
  fingerprint inside the SB3 checkpoint, historical-checkpoint rejection and
  mandatory D-43 preflight. The historical 0.25 evidence config remains
  byte-identical (`4cc04344…`); the new untrained config is `78b263b0…`.
- Implemented the ROS-free D-43 preflight over nominal `cage_status.csv`, with
  fail-closed metadata/checkpoint/config provenance. Existing Gazebo 2-D
  references classify entfix-2024/75k and entfix-42/50k as individual `PASS`,
  while auto-175k at 0.25 and its 0.22 probe are `BLOCKED`. The runner now
  requires a matching nominal-enforcement `PASS` before starting Gazebo and
  records the authorization hashes in the campaign report.
- Preregistered SC-PERT-03 at `lambda_stall = 4.0`, 50k one-shot continuation,
  no adaptive tuning, 20 runs per arm/mode, and arm criteria
  `stall_variant: M-P6 > 50.0` / `released: M-P6 == 0.0 AND M-P2 == 1`.
  Corrected the prior `>0.50` fraction/percentage mismatch; M-P6 is emitted on
  0–100. No historical verdict changes because the stall arm had never run.
- Added the default-zero reward hook, parent VecNormalize/replay restoration,
  one final deterministic VecNormalize/replay-buffer save, immutable manifest/hashes,
  arm-labelled run IDs/eval metadata and independent per-arm aggregation. A
  100% released arm can no longer mask an 80% stall arm.
- Reconciled the living docs and manuscript from “infrastructure pending” to
  “implemented, execution pending”, preserving the separation between posterior
  qualification evidence and the frozen 1-D GE4 verdict.

### Rationale

The previous evidence separated two 2-D blockers but did not enforce that
separation operationally: reducing the cap removed one exact speed-envelope
conflict, whereas auto-175k still stopped because a centred vehicle was assigned
a false CV heading beyond C-02. At the same time SC-PERT-03 was conceptually
well-posed in 2-D but could neither produce nor aggregate its two required arms.
The new contracts turn those findings into auditable preconditions instead of
allowing a historical checkpoint, unrelated preflight or pooled arm average to
be mistaken for evidence.

### Impact / remaining execution

- **No Gazebo training, fine-tune or campaign was run on this Windows host.**
  The margin022 YAML is a preregistration, not a result; the committed four-run
  D-43 matrix is diagnostic and aggregate `BLOCKED`, not an authorization token.
- The next evidence chain is fixed: fresh bounded-75k margin022 SAC training with final
  replay buffer → SC-NOM-01 enforcement eval → checkpoint/config-bound D-43
  `PASS` → one-shot 50k stall fine-tune → 80 SC-PERT-03 cells (2 arms × 2 modes
  × 20). Only that final chain can support a new posterior SR-009 statement.
- No H/SR/cage-rule count, cage threshold, generated traceability CSV, raw run,
  GE4 result or Gate verdict changed; Isaac remains an independent backend.

### Verification

- Targeted qualification suite → **106 passed, 1 skipped** on this host (the
  optional SB3 round-trip skips because `gymnasium` is unavailable here; it was
  exercised successfully in the dependency-complete environment).
- `python -m pytest -q --ignore=policy/tests/test_eval_policy_2d.py` →
  **541 passed, 7 skipped**. The omitted ROS/ament module cannot collect on
  this Windows host; the latest full Ubuntu/Jazzy baseline remains 517 passed.
- `python tools/check_traceability.py` → **PASS, 0 warnings**.
- `python tools/check_scenario_yaml.py` → **PASS, 0 errors** (historical warnings
  remain non-blocking).
- SC-PERT-03 complex_b dry-run → **80 cells** (2 arms × 2 modes × 20), no
  Gazebo; `py_compile` → PASS; `git diff --check` → clean (line-ending notices only).

---

## [20.07.2026] — Posterior Gazebo evidence consolidated across the engineering docs and manuscript: PPO/SAC 1-D/2-D scope, provenance limits and ordered next steps

**Document(s) affected:** `README.md`; `AGENTS.md`; `CLAUDE.md`; `docs/08_odd_specification.md`; `docs/09_environment_design.md`; `docs/10_reward_function.md`; `docs/11_camera_rl_training.md`; `docs/13_isaacsim_environment.md`; `docs/14_isaacsim_handover_spec.md`; `docs/15_implementation_inventory.md`; `docs/16_defense_compendium.md`; `docs/DECISIONS.md` (D-49/D-59/D-60 follow-ups + D-61 stack reconciliation); `experiments/README.md`; `policy/README.md`; `manuscript/README.md`; Chapters 7, 8, 11 and 12; `manuscript/figures/sim2real_roadmap.mmd`.

**Phase:** posterior E5 — Gazebo algorithm/action-space study

**Gate context:** after Gate G4; GE4-V2 and `docs/07` remain frozen.

**Author:** Samuel Sanchez

### Change

- Reconciled the completed PPO camera N=5 study, the PPO/SAC 1-D and 2-D
  training/evaluation chain, the 0.25/0.22 m/s speed-contract evidence, and the
  two SAC SC-PERT subset campaigns across the living docs and thesis chapters.
- Added a canonical run → checkpoint → SC-NOM-01 table and the combined SC-PERT
  result: **100/100 enforcement PASS vs 68/100 monitoring**, with 51 controlled-
  stop PASS cells. Both subset reports remain globally `INCOMPLETE` by
  construction and are not GE4 replacements.
- Corrected the SAC-entfix N=3 claim: **3/3 nominal enforcement-clean**, but
  paired nominal enforcement+monitoring exists only for seeds 2024/666 (**2/2**);
  the seed-42 nominal monitoring cell is pending.
- Recorded the evidence boundary and provenance gaps: seed-42 campaign run IDs /
  `campaign_runs.csv` retain a generated `seed2024` label while the per-run
  metadata and checkpoint hash identify seed 42; five pilot25k YAML snapshots
  are absent from the repository; interrupted training metadata can omit the
  rescued-checkpoint hash even though eval metadata pins it.
- Updated D-49/D-59/D-60 without changing their verdict boundary: Gazebo 2-D is
  implemented posteriorly, but no 2-D campaign or SC-PERT-03/SR-009 cell has run.
  The 0.22 m/s probe removes the zero-margin speed stop, not the independent D-43
  confident heading over-read.
- Added D-61 to reconcile the stale Phase-0 Humble choice with the implemented
  and evidence-bearing Ubuntu 24.04 + ROS2 Jazzy + Gazebo Sim Harmonic stack.

### Rationale

The repository contained the latest evidence artifacts and chronological
CHANGELOG entries, but several overview/specification documents still described
SAC and Gazebo 2-D as future work or over-stated the available paired nominal
evidence. This pass makes the current status auditable while keeping observation
track, action contract, simulator and verdict role separate.

### Impact / ordered next steps

1. **Close provenance before more compute:** run
   `rl_sacentfix42_eval_cb75k_4k4_mon`; fix the campaign runner's seed labelling
   for explicit `--model-path`; recover hash-matched pilot YAML snapshots if they
   still exist; and backfill training → rescued-checkpoint → eval links without
   rewriting raw evidence.
2. **Qualify Gazebo 2-D before a campaign:** preregister a non-zero speed margin
   (or recalibrate C-04 from new evidence), then characterise/mitigate D-43.
   Before the targeted SC-PERT-03/SR-009 cell, preregister `lambda_stall` and
   its criterion, implement runner orchestration for the released/fine-tuned
   arms, and hash the derived checkpoint/config.
3. **Only then decide on more training:** if justified, run a bounded 2-D hard-
   seed replica with fixed `ent_coef = 0.005` plus a replay buffer covering its
   planned horizon. The buffer result is demonstrated only for the bounded 1-D
   probe through 180k; transfer to 2-D is a hypothesis. Isaac/physical work stays
   an independent sim-to-real stream and does not reopen G4.

No hazard, SR, cage rule, scenario, metric, threshold, source code, generated
CSV, raw log or verdict artifact changed; no campaign/training re-run is required
by this documentation-only reconciliation.

### Verification

- `python tools/check_traceability.py` → **PASS, 0 warnings** (12 H, 14 SR,
  6 cage rules, 28 scenarios, 19 metrics).
- `python -m pytest -q --ignore=policy/tests/test_eval_policy_2d.py` →
  **491 passed, 6 skipped**. The omitted module cannot collect on this
  Windows/Python 3.14 host because ROS `ament_index_python` is unavailable; the
  latest fully green Ubuntu/Jazzy baseline remains **517 passed** (15.07.2026).
- `git diff --check` → clean (line-ending conversion notices only).

---

## [20.07.2026] — Replay-buffer mechanism probe (buffer 200k, bounded 180k): evidence supports replay eviction as the slow-decay mechanism — with a 2× buffer the peak band holds where the 100k twin fell 35%

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 mechanism-probe bullet, version log). **New evidence:** `experiments/sim/training/sac_newcam_entfix_buf200_2024_180k/` (curve to 180.2k, metadata `interrupted` + probe conclusion, `checkpoints_peak/` 150k/175k, config copy archived); eval `experiments/sim/runs/rl_sacbuf200_eval_cb150k_4k4`.
**Phase:** posterior (E5 — algorithm study; second-mechanism isolation, the follow-up the entfix runs called for)
**Gate context:** after Gate G4; nothing frozen touched.
**Author:** Samuel Sanchez

### Change

Single-knob probe on the 1-D entfix config: `sac.buffer_size` 100k → 200k (~11 GB), seed 2024,
planned stop at 180k.

### Rationale / Impact — second mechanism isolated over the observed horizon

Curve identical to the 100k twin up to ~86k (peak 720 @ 88k), then **no slow decay**: holds and
climbs in the **690–745 band through 180k** (new peaks 722 @ 145k, **744.7 @ 155.6k** — the
highest sustained level of the study) where the 100k twin had fallen to ~445–470. The timing
strongly supports the mechanism: the 100k twin's decay onset (~90–125k) coincides with its buffer filling and
**evicting the early era**; with 200k nothing is evicted before 200k and the decay never
starts. **Observed mechanism split:** abrupt collapse = auto-temperature → 0 (removed by
`ent_coef: 0.005`); the bounded slow decay is consistent with replay eviction (prevented by
the 200k buffer through the 180k observation window). The result is one seed and does not yet
establish transfer to 2-D or a longer horizon. Hypothesis for a future run: entfix + buffer
sized to the intended bounded budget. Eval of
the 150k plateau checkpoint: full horizon, 4.94 laps, 26.9 mm, 0 emergencies, 14.4% C-06 —
solid but not better than the 75k peaks (the eval-overrules-curve lesson, again).

### Verification

Planned SIGINT at 180k, clean exit; RAM watch never tripped (buffer ~11 GB); eval full 4400,
0 errors; `python tools/check_traceability.py` → PASS.

---

## [19.07.2026] — Entfix seed-robustness replica (seed 42, bounded 120k): the no-cliff + ~720-peak result replicates, and the 75k eval improves to near-PPO tracking with 2.3% cage engagement

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 seed-robustness note, version log). **New evidence:** `experiments/sim/training/sac_newcam_entfix_complex_b_42_120k/` (curve to 120.8k, metadata `interrupted` + planned-stop reason, `checkpoints_peak/` 75k/100k, seed-42 config copy archived in the run dir); eval `experiments/sim/runs/rl_sacentfix42_eval_cb75k_4k4`.
**Phase:** posterior (E5 — algorithm study; single-seed caveat check on the entfix headline)
**Gate context:** after Gate G4; nothing frozen touched.
**Author:** Samuel Sanchez

### Change

Bounded replica of the 1-D entfix run with seed 42 (only deltas vs `train_sac_camera_entfix.yaml`:
seed + model_path; planned stop at ~120k, past the peak zone).

### Rationale / Impact

The curve tracks the seed-2024 entfix run within ~3% at every 30-min checkpoint (102/111 @ 14k
… 682/687 @ 76k); peak **744.3 @ 87k** (2024: 722.5 @ 83k), **no cliff**. The headline entfix
findings — no abrupt collapse, ~720-745 peak at ~80-90k, clean 75k checkpoint — are **not
seed-2024 luck**. The seed-42 75k eval is in fact the best SAC checkpoint of the study:
**full horizon, 4.63 laps, |ey| 12.3 mm (max 35.0), 0 emergencies, intervention 2.3%
C-06-only** — near-PPO tracking precision (10.9 mm) at ~1/20th the PPO run's cage engagement
(43.5%), trained in 75k steps (~1/4 of the PPO peak budget).

**Addendum 2 — 2-D entfix seed-42 replica (same bounded protocol,
`sac_gz2d_tuned_entfix_42_120k`):** the 2-D no-violent-collapse regime replicates but the
curve magnitude is strongly seed-dependent (peak 270.9 @ 47k vs the 2024 run's 558.7 @ 78k;
band oscillation, recovering to 243 at the 120k cutoff). The deterministic eval again
overrules the curve (the §8.5 lesson): **50k checkpoint, enforcement — FULL horizon, 4.97
laps, |ey| 18.2 mm, 0 emergencies, 46.4% C-06** (the second full-horizon 2-D enforcement
eval of the programme; more laps than the 2024 2-D entfix's 4.32 at similar |ey|, at ~2.7×
its cage engagement). Monitoring: full horizon, 4.84 laps, 22.6 mm, but **39 would-be
emergency steps** (2024: 0) — this seed's bare policy grazes the emergency envelope; the
enforcement C-06 smoothing is doing real work. Evidence:
`experiments/sim/training/sac_gz2d_tuned_entfix_42_120k/`,
`experiments/sim/runs/rl_sacgz2dentfix42_eval_cb50k_4k4{,_mon}`.

**Addendum — seed 666 (same bounded protocol; the E5 hard seed, cage-dependent under PPO):**
same regime (no cliff, peak 606.9 @ 81k — ~16% below 2024/42, the hard seed stays hardest in
magnitude only; recovering to 596 at the 120k cutoff). **75k evals: enforcement 5.00 laps /
|ey| 14.0 mm / 0 emergencies / 5.3% C-06; monitoring matches the task metrics
(5.00 laps, 14.0 mm, 6.2% counterfactual C-06)** —
**not cage-dependent: the entfix recipe rescues the bad seed.** **Audit correction
(20.07.2026):** the supported N=3 statement is **3/3 clean in nominal enforcement**;
only seeds 2024/666 have the matched nominal monitoring cell and are 2/2 clean in both
modes. The seed-42 nominal monitoring run is still missing and its SC-PERT monitoring
campaign is not a substitute for SC-NOM-01. This is therefore not yet a 3/3 two-mode basin
classification. The PPO E5 N=5 split remains 3/5 (666 cage-dependent, 23 cage–CV conflict).
Evidence:
`experiments/sim/training/sac_newcam_entfix_complex_b_666_120k/`,
`experiments/sim/runs/rl_sacentfix666_eval_cb75k_4k4{,_mon}`.

### Verification

Planned SIGINT at 120k, clean exit; eval full 4400 / 0 errors;
`python tools/check_traceability.py` → PASS.

---

## [19.07.2026] — SC-PERT subset campaign on the SAC entfix peak: the protective direction replicates from PPO to SAC (enforcement 50/50 PASS); the SAC bare policy is more degradation-robust on this subset

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 closing bullet, version log). **New evidence:** `experiments/sim/campaign_sac_pert/` (100 runs, 0 errors: SC-PERT-04/09/11/12/13 × {enforcement, monitoring} × 10 reps, `scenarios_complex_b` overlay, SAC entfix 75k checkpoint; campaign_report.json + campaign_runs.csv + per-run dirs).
**Phase:** posterior (E5 — algorithm study close-out: does the GE4-V2 cage-value finding survive an algorithm change?)
**Gate context:** after Gate G4; GE4-V2 untouched (this is a subset probe on a different checkpoint, not a verdict campaign — the report's global INCOMPLETE is expected and meaningless here).
**Author:** Samuel Sanchez

### Change

Ran the five perception-degradation scenarios through the campaign runner on the SAC entfix
75k peak (10 reps/mode). NB the first attempt omitted `--scenario-dir scenarios_complex_b`
and was discarded — the base `scenarios/` YAMLs carry oval track blocks (PERT-09's
`lane_following_oval_worn.world` doesn't exist), the overlay is REQUIRED for complex_b
campaigns.

### Rationale / Impact

**Enforcement: 50/50 PASS — identical to PPO (175/175). The observed protection result
replicates under the PPO→SAC change.** Monitoring (bare policy): PERT-04 10/10, PERT-09 8/10,
PERT-11 **0/10**, PERT-12 10/10, PERT-13 5/10 — vs PPO's 24/40, 0/25, 0/30, 23/40, 0/40. Two
readings: (a) **the latent→active direction is observed under both PPO and SAC** — wherever the
bare policy fails under degradation, enforcement removes every failure; (b) **which scenarios
the bare policy fails is policy-dependent** — the SAC entfix policy is markedly more robust
(mon pass 33/50 = 66% vs PPO 27%; PERT-09/13 mostly survive where PPO always failed), and
**SC-PERT-11 is the strongest observed cross-policy discriminator** (0% both algorithms — the strongest
single cage-value scenario in the library). Net thesis claim strengthened: the cage's safety
contribution is the invariant across policies; the policy only moves *where* it is needed.

### Verification

100/100 cells with summaries, 0 errors; per-scenario roll-up cross-checked against the
GE4-V2 report numbers quoted above; `python tools/check_traceability.py` → PASS.

**Addendum (20.07.2026) — replicated on the seed-42 entfix 75k**
(`experiments/sim/campaign_sac_pert_s42/`, 100 runs, 0 errors): **enforcement again 50/50
PASS**; monitoring 35/50 (PERT-04 10/10, PERT-09 10/10, PERT-11 **0/10**, PERT-12 10/10,
PERT-13 **5/10** — identical to the seed-2024 rate). The degradation-robustness profile of
the entfix policy family is seed-stable, and **SC-PERT-11 is now 0% for a third independent
policy** (PPO 297k, SAC entfix 2024, SAC entfix 42) — the strongest cage-value
scenario in this observed battery.

---

## [19.07.2026] — 2-D entfix run (stopped 176k): first 2-D enforcement eval to complete the full horizon; cap-margin probes close the D-59 evidence

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 2-D entfix block, version log). **New evidence:** `experiments/sim/training/sac_gz2d_tuned_entfix_2024_1M/` (curve to 176k, metadata `interrupted` + stop_reason, `checkpoints_peak/` 75k/100k, 75k hash `b76724c7…`; the 2-D comparison figure is now three-curve); evals `experiments/sim/runs/rl_sacgz2dentfix_eval_2024_cb75k_4k4{,_mon}`; cap probes `rl_sacgz2d_capprobe022_2024_cb{150k,175k}_4k4` (eval-only 0.22-cap config, copy kept with the runs).
**Phase:** posterior (E5 — algorithm study follow-on + D-59 evidence)
**Gate context:** after Gate G4; nothing frozen touched.
**Author:** Samuel Sanchez

### Change

(a) Ran `sac_gz2d_tuned_entfix_2024_1M` (2-D tuned recipe, single delta `sac.ent_coef: 0.005`
fixed). The floor removes the 2-D collapse-recover cycles too: **monotonic climb to 558.7 @
78k — a new 2-D SAC record** (auto: 527 @ 154k) — then the familiar slow post-peak decay
(fourth consistent observation across the SAC runs); stopped at ~176k. (b) Ran the two
**cap-margin sensitivity probes** (eval-time `action.max_speed_mps` 0.25→0.22, policy
unchanged) on the auto run's 150k/175k checkpoints.

### Rationale / Impact

**2-D entfix 75k peak evals (SC-NOM-01, 4400 steps, DR off): enforcement completes the FULL
horizon — 4.32 laps, |ey| 17.1 mm, 0 emergencies, 17.1% C-06-only — the first full-horizon
2-D enforcement eval of the programme** (2-D PPO best: 1.52 laps; SAC auto: 2.85/3.45 before
stops). Monitoring also completes (4.31 laps, 16.3 mm, 0 emergencies, 18.0%
counterfactual C-06) → 2-D cage-latent-in-ODD.
Mechanism: the policy **self-limits to max 0.244 m/s**, never touching the 0.25 C-04 curve
ceiling — the entropy floor yields margin-keeping behaviour without any cage/config change.
**Cap probes (D-59 closed-out evidence):** the 150k ckpt — stopped at 0.25-cap by the
0.0002 m/s zero-margin overspeed — **completes the full 4400 under the 0.22 cap** (3.42 laps,
0 emergencies, vmax 0.221): margin-by-construction removes that stop entirely. The 175k ckpt
stops under both caps (804 steps @ 0.22, C-03→C-05) — its failure is the D-43 CV heading
over-read, cap-independent, as predicted. Net for D-59: **the speed-envelope conflict is
fully attributable to cap==ceiling; 0.03 m/s of margin (or an entfix-style policy) resolves
it; the residual 2-D enforcement risk is the CV over-read (D-43 thread), not speed.**

### Verification

SIGINT-clean stop; both peak evals + both probes ran full/terminated as described, 0 errors;
probe config copy stored alongside the probe runs; `python tools/check_traceability.py` → PASS.

---

## [18.07.2026] — SAC entfix variant (1-D): the fixed temperature floor removes the collapse cliff but not the slow post-peak decay; 75k peak eval is the cleanest SAC profile (5.04 laps, 9.1% C-06, 0 emergencies)

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 entfix block, version log). New configs: `train_sac_camera_entfix.yaml`, `train_sac_camera_2d_tuned_entfix.yaml` (single delta each: `sac.ent_coef: 0.005` fixed vs `auto`). **New evidence:** `experiments/sim/training/sac_newcam_entfix_complex_b_2024_1M/` (curve to 260k, metadata `interrupted` + stop_reason, `checkpoints_peak/` 75k/100k, 75k hash `b74505ac…`); evals `experiments/sim/runs/rl_sacentfix_eval_2024_cb{75k,100k}_4k4` + `…cb75k_4k4_mon`; the 1-D comparison figure is now three-curve (PPO / SAC auto / SAC entfix).
**Phase:** posterior (E5 — algorithm study follow-on; mechanism-isolation experiment, user-directed)
**Gate context:** after Gate G4; nothing frozen touched.
**Author:** Samuel Sanchez

### Change

Ran `sac_newcam_entfix_complex_b_2024_1M` (identical to the 1-D SAC mirror except
`sac.ent_coef: 0.005` fixed — a stochasticity floor ~7× above the value the auto temperature
collapsed to). Stopped at ~260k (177k steps past peak, oscillating 445–550 without
re-approaching it).

### Rationale / Impact — mechanism split confirmed

**The floor removes the cliff:** peak **722.5 @ 83k** (== the auto run's 720), and through the
140–155k window where the auto run collapsed 540→23, the entfix run held ~470 flat — **no
abrupt collapse anywhere in 260k steps**. **But the slow post-peak decay happened anyway**
(722 → 445–550 band): two distinct mechanisms — the cliff was the α→0 exploitation spiral;
the slow decay survives the floor (provisionally attributed here to critic overfit; superseded
by the 20.07 replay-buffer probe, which isolates replay eviction). **Eval (SC-NOM-01, 4400
steps, DR off): 75k peak-of-record — enforcement 5.04 laps,
|ey| 21.6 mm (max 55.8), 0 emergencies, intervention 9.1% C-06-only (402 steps); monitoring
identical (5.04 laps, 21.6 mm, 0 emerg, 10.6% would-be)** — the lowest cage engagement of any
camera policy measured (SAC auto 48.3%, PPO 297k 43.5%): the entropy floor yields a visibly
smoother steering policy. 100k flank (5.05 laps, 30.6 mm, 12.7%) confirms 75k.

### Verification

SIGINT-clean stop, metadata + stop_reason recorded; both evals full 4400 / 0 errors;
`python tools/check_traceability.py` → PASS.

---

## [18.07.2026] — Planned-1M 2-D tuned SAC run stopped at 251k: collapse-recover cycles (peaks 214→527 @ 154k), 175k peak evals — monitoring 4.31 laps / 0 emergencies, enforcement stopped by the two known 2-D mechanisms

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 2-D 1M block, version log). **New evidence:** `experiments/sim/training/sac_gz2d_tuned_complex_b_2024_1M/` (curve to 251k, metadata `interrupted` + stop_reason, `checkpoints_peak/` 150k/175k + VecNormalize stats, `ppo_vs_sac_2d_curve.png`); evals `experiments/sim/runs/rl_sacgz2d_eval_2024_cb150k_4k4`, `…cb175k_4k4{,_mon}`.
**Phase:** posterior (E5 — algorithm study; the 1M 2-D run docs/11 §4.2 called for, on the tuned recipe per the 15.07 pilot)
**Gate context:** after Gate G4; the 2-D PPO baseline and all frozen artefacts untouched.
**Author:** Samuel Sanchez

### Change

Ran the tuned 2-D SAC 1M config (`sac_gz2d_tuned_complex_b_2024_1M`, seed 2024, batch 256,
constant LR, warmup 5k, UTD 2, buffer 150k, 0.25 cap, D-58 random spawns). Stopped manually at
~251k: the run settles into **collapse-recover cycles** driven by the same auto-temperature
pinning as the 1-D run (α ≈ 7e-4 from ~62k; the tuned recipe fixes batch/LR but keeps
`ent_coef: auto`, and UTD 2 adapts α twice as fast) — cycle peaks **214 @ 54k → 527 @ 154k**
(the 2-D manifestation is throttle-greedy: mean raw throttle 0.86, ~25% saturated high,
emergencies rising into each collapse), but cycle 3 never recovered (527 → 66 over ~97k steps)
and the run was stopped with the peak zone already flanked by the 150k/175k checkpoints
(175k hash `e8934d51…`).

### Rationale / Impact (deterministic SC-NOM-01 evals, 4400 steps, DR off)

**175k is the peak-of-record** (eval-selected): **monitoring 4.31 laps, |ey| 32.3 mm,
0 emergencies, full horizon** (mean speed 0.182, max 0.252 — it slows for curves); enforcement
**3.45 laps / |ey| 34.8 mm** before a C-02→C-05 stop on the **known D-43 confident curve
heading over-read** (cv_epsi ≈ −0.45 rad on a centred car at true |epsi| 0.035 — the 13.07
CV-probe mechanism). The 150k flank: 2.85 laps / 49.4 mm, stopped by the **zero-margin speed
envelope** (odom 0.2502 vs the 0.25 C-04 curve ceiling — the action cap *equals* the cage
ceiling, so a 0.0002 m/s odom overshoot in a curve fires C-04+C-05; D-59 review item,
quantified). Verdict pattern replicates 2-D PPO (mon competent / enf stopped by cage–CV or
speed-margin, not by driving) but SAC gets **2.3× further in enforcement** (3.45 vs 1.52 best
PPO laps) and reaches its curve peak with **3.3× fewer steps** (527 @ 154k vs 654 @ 511k),
peaking lower. Both 2-D stop mechanisms are now cleanly quantified for the D-59 prerequisite
review. Combined with the 1-D run (17.07): **`ent_coef: auto` collapses in this env in both
action spaces** — a fixed-temperature floor (e.g. `sac.ent_coef: 0.005`) is the obvious next
variant if SAC is pursued further; not launched (deviates from the frozen recipes — user call).

### Verification

SIGINT-clean stop, metadata `interrupted` + stop_reason; `num_timesteps` verified
(150000/175000); mon eval full 4400 steps / 0 errors; per-step CSVs carry the 2-D
`raw_throttle`/`safe_throttle` evidence; zero-`cmd_vel` + settle guard between chained evals;
`python tools/check_traceability.py` → PASS.

---

## [17.07.2026] — Planned-1M 1-D SAC run stopped at 307k: peak 720 @ 89k, entropy-collapse dip + recovery; 75k peak checkpoint evals clean (5.12 laps, 0 emergencies, cage latent)

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 1M-run block, version log). Configs: `train_sac_camera.yaml` + `train_ppo_camera.yaml` (seed 23→2024 restore — the multiseed-E5 leftover contradicted the D-36 main-seed comment; `checkpoint_freq: 25000` added to both twins, the 03.07 ckpt-volume lesson, diff-parity preserved). **New evidence:** `experiments/sim/training/sac_newcam_complex_b_2024_1M/` (learning_curve.csv to 307k, metadata `interrupted` + stop_reason, `checkpoints_peak/` with the 75k/100k zips + VecNormalize stats, `ppo_vs_sac_1d_1M_curve.png`); evals `experiments/sim/runs/rl_sacnewcam_eval_2024_cb75k_4k4{,_mon}` + `rl_sacnewcam_eval_2024_cb100k_4k4`.
**Phase:** posterior (E5 — algorithm study, the 1M follow-up the 15.07 pilots called for)
**Gate context:** after Gate G4; GE4-V2 and every frozen PPO artefact untouched.
**Author:** Samuel Sanchez

### Change

Ran the 1M-budget 1-D camera SAC mirror (`sac_newcam_complex_b_2024_1M`, seed 2024, complex_b,
enforcement, DR on — config differs from the PPO E-main only in `algorithm:`/`sac:` block).
Stopped manually at ~307k under the pre-agreed deterioration rule (the PPO-1M precedent):
`ep_rew_mean` peaked **720.0 @ ~89k**, entered a slow decay, then an abrupt **entropy-collapse
dip at ~143k** (540 → 23 in ~3k steps; the auto-tuned temperature had contracted to ~4e-4,
near-deterministic — same exploration-collapse family as the PPO 297k run), **recovered** to
~635 by 262k (replay buffer retains the good era — a recovery PPO never showed from its 500k+
decay) but then oscillated 540–640 without re-approaching the peak; at a budget comparable to
the PPO peak (297k) the run was stopped and the peak zone rescued. Peak checkpoints 75k/100k
(25k periodic cadence) copied to `checkpoints_peak/`; 75k hash `58631022…`.

### Rationale / Impact (deterministic SC-NOM-01 evals, 4400 steps, DR off — the classifier, not the curve)

**75k enforcement: 5.12 laps, mean |ey| 19.8 mm (max 75.1 mm), 0 emergencies, interventions
48.3% C-06-only** — full horizon, no C-01/02/03/05. **75k monitoring: 5.13 laps, 23.3 mm,
0 emergencies** → the E-main **cage-latent-in-ODD signature in both modes** (constraint-
respecting policy). 100k enforcement (5.14 laps, 27.5 mm, 93.3% C-06) confirms 75k as the
peak checkpoint of record. Against the PPO E-main 297k (4.88 laps, 10.9 mm, 43.5% C-06):
SAC completes **more laps** (tighter line — the higher |ey| is line-cutting, not instability)
with **~2× the lateral error** and equal safety (0 emergencies both); it reaches ~87% of the
PPO peak reward in ~30% of the steps (sample efficiency), at the cost of a temperature-collapse
instability the linear-LR/batch-64 mirror values plausibly aggravate (the tuned-recipe lesson,
15.07). Laps ARE comparable here (same track, same fixed 0.2 m/s).

### Verification

Trainer SIGINT-clean (metadata written, no gz orphans; Gazebo kept alive for the eval chain
with the zero-`cmd_vel` + settle guard between runs); `num_timesteps` verified in both rescued
zips (75000/100000); all three evals `total_steps: 4400`, summaries recorded;
`python tools/check_traceability.py` → PASS.

---

## [15.07.2026] — Tuned 2-D SAC recipe (SAC-canonical values) + fifth pilot curve: the PPO-inherited values were handicapping SAC

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 tuned-variant block, version log), `docs/15_implementation_inventory.md` (§5.3 row). Configs: `train_sac_camera_2d_tuned.yaml` (1M) + `train_sac_camera_2d_pilot25k_tuned.yaml`. **New evidence:** `experiments/sim/training/sac_gz2d_pilot25k_tuned_2024/`; the battery figure under `pilot25k_ppo_vs_sac_2024/` is now `ppo_vs_sac_pilot25k_battery.png` (5 curves).
**Phase:** posterior (E5 — third same-day follow-on; see the two entries below)
**Gate context:** after Gate G4; nothing frozen touched.
**Author:** Samuel Sanchez

### Change

The paired SAC arms deliberately inherited the PPO-shared values for like-for-likeness; two of
them are non-canonical for SAC (`batch_size 64` vs canonical 256; `lr_schedule: linear` vs
canonical constant 3e-4 — the anneal switches learning off when the replay buffer is richest).
The tuned variant restores SAC-canonical values and adds the free-compute lever: **batch 256,
constant LR, `learning_starts` 5000, `gradient_steps` 2** (UTD 2 — the render caps collection
at ~7 steps/s while the GPU idles, so extra updates are wall-clock-free), buffer 150k (~8.4 GB).
The paired pilot configs stay untouched — the pair keeps answering the like-for-like question;
the tuned config answers "how far can 2-D SAC get".

### Rationale / Impact (25k tuned pilot, seed 2024)

**107.4 `ep_rew_mean`** with only ~20k learning steps (5k warmup): passes the untuned SAC arm
(90.0) around ~16k and nearly catches PPO (113.0) at cutoff with the steepest late slope of
the battery (31 → 76 → 107 at 15k/20k/25k). `ep_len` 131 vs the untuned arm's 198 — it drives
*faster* (PPO-like episode profile), easing the slow-but-alive concern flagged on the untuned
arm, at the cost of a small emergency-rate rise (0.011 vs 0.0002; intervention 0.935, lowest
of the 2-D battery). Conclusion: the PPO-inherited values were indeed handicapping SAC; the
1M 2-D SAC run on the training host should use `train_sac_camera_2d_tuned.yaml`. Wall-clock
~6-7 steps/s (UTD 2 nearly free, as predicted).

### Verification

Offline construction check (UTD 2 → 2 updates/step post-warmup confirmed; constant LR resolves
to a float, not a schedule); pilot `status: completed`, metadata records the tuned
hyperparameters; clean shutdown, no gz orphans; `python tools/check_traceability.py` → PASS.

---

## [15.07.2026] — 2-D (steer+throttle) wired for SAC + the four-curve pilot battery completed (1-D and 2-D PPO-vs-SAC pairs)

**Document(s) affected:** `docs/11_camera_rl_training.md` (§4.2 extended with the 2-D pair + four-curve result, v0.6.4), `docs/15_implementation_inventory.md` (§5.3 config rows), `experiments/README.md`, `policy/README.md`. Configs (no code change — D-60's switch and D-59's 2-D action block compose orthogonally): `train_sac_camera_2d.yaml` (SAC mirror of the 0.25-cap `train_ppo_camera_2d.yaml`), `train_{ppo,sac}_camera_2d_pilot25k.yaml` (2-D pilot pair). **New evidence:** `experiments/sim/training/{ppo,sac}_gz2d_pilot25k_2024/` + the four-curve figure and extended `summary.json` under `experiments/sim/training/pilot25k_ppo_vs_sac_2024/`.
**Phase:** posterior (E5 — algorithm study groundwork, same-day follow-on to the D-60 entry below)
**Gate context:** after Gate G4; the frozen 1-D verdict chain and the 2-D PPO 1M baseline are untouched.
**Author:** Samuel Sanchez

### Change

The D-60 `algorithm:` switch composes with the 2-D `action:` block with **zero code
change** (both live in shared config-driven paths); verified offline (SAC over a `Box(2,)`
action with `raw_throttle` action-sampling) and with a 600-step live-Gazebo smoke, then a
**25k 2-D pilot pair** (seed 2024, identical configs except the switch: 0.25 m/s cap,
`throttle_delta`/`stall_penalty` reward, `ent_coef 0.01` PPO-only, `max_episode_steps 2048`,
`random_start_s: true` D-58 — both arms identical, curves judged within the pair).

### Rationale

Complete the four-curve battery (1-D PPO/SAC + 2-D PPO/SAC): the 1-D pair is the clean
algorithm comparison; the 2-D pair asks whether SAC gets further than PPO did on the 2-D
action, where the PPO 1M baseline underdelivered (peak 654 ≪ 1-D 823, docs/11 §8.5).

### Impact

**1-D pair (unchanged from the entry below):** SAC 161.7 vs PPO 131.7 `ep_rew_mean` (+23%),
SAC overtakes from ~15k. **2-D pair (25k):** PPO 113.0 vs SAC 90.0 — but the *shapes*
differ: PPO flattens at its 114 peak (~24.5k) while SAC is still **accelerating** (7 → 19 →
67 → 90 at 5k/12k/20k/25k, the steepest end-slope of the four curves) and drives the longest
episodes of the battery (`ep_len` 198 vs 154 — slower, more survivable driving; emergencies
~0 in both, intervention ~0.96–0.98 C-06/C-04-dominated). At 25k neither 2-D arm approaches
a "good point"; the off-policy warmup (1k random steps + auto-temperature) delays SAC's
takeoff by design, so whether it overtakes needs a longer run — the 1M-budget config
(`train_sac_camera_2d.yaml`, buffer 100k ≈ 5.6 GB) is ready for the training host.

### Verification

Offline SAC 2-D smoke (Box(2,) action, learning-curve schema, `raw_throttle` column,
save/load) OK; 600-step live-Gazebo SAC 2-D smoke `status: completed` with the
`steer_throttle`/0.25 action contract recorded in metadata, clean shutdown, no gz orphans;
both 25k pilots `status: completed`; `python tools/check_traceability.py` → PASS, 0 warnings.

---

## [15.07.2026] — Trainer gains a config-selected algorithm switch (`algorithm: ppo|sac`) + 25k PPO-vs-SAC verification pilot pair

**Document(s) affected:** `docs/DECISIONS.md` (new **D-60** — algorithm switch as a config key, not a separate entry point), `docs/11_camera_rl_training.md` (new **§4.2** + §9 SAC command block, v0.6.3), `docs/15_implementation_inventory.md` (module rows + §5.3 config rows). Code: `src/cobraflex_rl/cobraflex_rl/train_ppo.py` (algorithm resolver, SAC branch, algorithm-aware metadata/registry/run-id), `training_metrics.py` (`SB3_SCALAR_COLUMNS_SAC` / `_BY_ALGO` — same CSV schema, SAC keys mapped), `callbacks.py` (`LearningCurveCallback` scalar-map + `min_row_interval` params, progress-bar `desc`), `eval_policy.py` (`--algorithm` / config-key resolution for loading SAC checkpoints), `launch/train_lane.launch.py` (new `train_config`, `run_id`, `model_path` launch args). Configs: `train_sac_camera.yaml` (SAC mirror of `train_ppo_camera.yaml`), `train_ppo_camera_pilot25k.yaml` + `train_sac_camera_pilot25k.yaml` (the pilot pair). **New evidence:** `experiments/sim/training/{ppo,sac}_cam_pilot25k_2024/` + `experiments/sim/training/pilot25k_ppo_vs_sac_2024/` (comparison figure + summary.json).
**Phase:** posterior (E5 — training-infrastructure extension; algorithm study groundwork)
**Gate context:** after Gate G4. The frozen PPO runs and GE4-V2 are untouched — `algorithm` defaults to `ppo` and the PPO code path is byte-identical.
**Author:** Samuel Sanchez

### Change

`train_ppo.py` now trains SB3 **PPO or SAC** from the same entry point, selected by a single
`algorithm:` key in the training config (default `ppo`; per-algorithm hyperparameters for SAC
live in an optional `sac:` block — `buffer_size`, `learning_starts`, `tau`, `train_freq`,
`gradient_steps`, `ent_coef: auto`). Env, wrappers (Monitor/VecFrameStack/VecNormalize),
reward, cage wiring, seed and LR schedule are shared verbatim, so two configs differing only
in `algorithm:` are a like-for-like comparison. One real incompatibility was found and fixed:
with SAC + image obs + `VecNormalize`, SB3 puts `VecTransposeImage` *outside* `VecNormalize`
while the off-policy replay buffer stores VecNormalize's original (untransposed) obs — the
trainer now applies the transpose inside the normalizer on the SAC path only.
`learning_curve.csv` keeps the exact PPO column schema for SAC runs (`value_loss` ←
`train/critic_loss`, `entropy` ← `train/ent_coef`, PPO-only columns NaN), throttled to one
row per 1024-step window (SAC ends a "rollout" every step). `eval_policy` resolves the SB3
class from `--algorithm` or the config; `train_lane.launch.py` exposes
`train_config:=`/`run_id:=`/`model_path:=`.

### Rationale

Algorithm-comparison groundwork (PPO vs an off-policy, sample-efficient baseline) on the
frozen 1-D camera architecture, requested 15.07.2026; config-key switch chosen over a
separate SAC entry point to guarantee the two arms share everything but the update rule.

### Impact

No hazard/SR/cage/scenario/metric artefacts touched. **25k verification pilots (complex_b,
seed 2024, enforcement, DR on, 1-D steering):** both algorithms learn healthily from pixels —
PPO `ep_rew_mean` 131.7 / `ep_len_mean` 162 at 25k; SAC **161.7 / 186** (+23% reward),
overtaking PPO from ~15k, with slightly lower cage-intervention rate (0.85 vs 0.91, C-06
dominated as usual early in training) and near-zero emergencies in both. 25k is far below the
1-D convergence regime (PPO peaks ~823 @ ~297k) — a sanity check of the implementation, not
an algorithm verdict. SAC wall-clock matched PPO (~7 steps/s, real-time-bound rendering; GPU
absorbs the per-step gradient update). RAM note: SAC's replay buffer on the 84×84×4 obs is
~56 KB/transition — `buffer_size` must stay explicit (100k ≈ 5.6 GB; SB3's 1M default would
be ~56 GB).

### Verification

`pytest` 517 passed; offline SAC-path smoke (synthetic camera env, full wrapper+callback
stack, checkpoint + save/load) OK; 600-step SAC smoke in live Gazebo OK (clean shutdown, no
orphans); both 25k pilots `status: completed` with full reproducibility metadata; SAC
checkpoint loads through the eval path (`SAC.load` via config resolution, deterministic
predict OK). `python tools/check_traceability.py` → PASS, 0 warnings.

---

## [13.07.2026] — CV weak-section probe: both estimator failure mechanisms measured in-situ (H-12 flip quantified + NEW confident heading over-read in tight curves)

**Document(s) affected:** `docs/12_cv_lane_keeper.md` (§4.4 — two quantified-limitation blocks, header v0.6), `docs/11_camera_rl_training.md` (posterior item (c) pointer), `tools/validate_cv_estimator.py` (section-probe mode: `--s-range/--s-step`, `--centerline/--world/--world-name/--camera-topic` retargeting, `--offsets/--headings`, `--skip-degraded`, `--run-prefix`, `--save-frames`; `ey_cmd`/`dpsi_cmd` now recorded per sample). **New evidence:** `experiments/sim/runs/cv_probe_weak_sections_20260713T084230Z/` (420-pose oracle grid on `complex_b`, Lane Cam, clean frames; samples.csv + summary.json + probed frames under gitignored `raw_logs/frames/`). No hazard/SR/cage/scenario/metric criterion changed.
**Phase:** posterior (E5 — perception characterisation feeding the D-49 temporal-estimator thread)
**Gate context:** after Gate G4. Explains (does not alter) the E5 multi-seed / 2-D enforcement stops; GE4-V2 untouched.
**Author:** Samuel Sanchez

### Change

`tools/validate_cv_estimator.py` (previously oval-only, full-circuit sweeps) gained a targeted
section-probe mode and was pointed at the three sections implicated by the E5 evals: the two
weak sections (A: s 8.0–9.8; B: s 12.0–14.6, containing the s≈13.4 stop point) plus a control
straight (s 2.0–4.0), grid = 35 arc-lengths × offsets {−0.06, 0, +0.06, +0.12} × headings
{−0.1, 0, +0.1}, CV estimate vs ground-truth oracle at each pose, all frames saved.

### Rationale (findings)

1. **The H-12 flip is now fully characterised.** It fires anywhere on the circuit at
   ey ≈ +0.12 (camera over the dashed centre line) and is **gated by heading, not by
   section**: nose-inward 0/35 poses, straight 17/35, nose-outward 30/35 — exactly the
   departing-vehicle geometry. Magnitude ≈ −1 lane width (est −0.135 ± 0.005) at confidence
   0.46–0.52, `cv_ok` True; clean (≤ ~25 mm) at ey ≤ +0.06. **Offline replay of the 105
   saved +0.12 frames validates the D-48 revert quantitatively**: `conservative_lane_selection`
   fixes only 4/47 flips — usually only one (wrong) plausible pair survives, no ambiguity to
   resolve.
2. **NEW second mechanism — confident heading over-read in tight curves.** Section A reads
   epsi −0.11…−0.36 rad (mean −0.22) on a centred, straight car at confidence ~0.77 (control
   straight: 0.000); with a real −0.1 rad offset it reaches −0.45 rad, **crossing the 25°
   C-02/C-05 envelope on a centred car**. This is the measured mechanism of the seed-23
   s≈8.8 false positives/stop and of the 2-D at-speed enforcement stops; section B shows it
   milder (mean +0.05, worst ±0.24).
3. Together the two mechanisms account for all the E5 nominal enforcement stops: 666/23's
   drift stops (flip family, ey→0.12 nose-out) and the centred-car C-05s (curve over-read).
   Both are confident-and-wrong (SR-014 cannot gate them); closure remains the D-49
   temporal estimator / posterior retrain.

### Impact

docs/12 §4.4 is now the quantified reference for both limitations (v0.6); docs/11 §8.5's
posterior item (c) points at it. The probe run is reusable (`--s-range` mode documented in
the tool docstring) for the temporal-estimator validation when it lands. No re-runs required.

### Verification

`python tools/check_traceability.py` → PASS (docs/tool/evidence only). Probe completed 420/420
poses, 0 settle failures / 0 dropped frames; the control section reproduces the known-good
nominal accuracy (centred ey bias +10 mm, epsi 0.000), confirming the probe protocol is sound.

---

## [13.07.2026] — 2-D action authority capped: `max_speed_mps` 0.5 → 0.25 (train config revision for the next 2-D run)

**Document(s) affected:** `src/cobraflex_rl/config/train_ppo_camera_2d.yaml` (action block + header rationale), `docs/11_camera_rl_training.md` (2-D posterior-variant paragraph). **No cage constant, hazard/SR table, scenario criterion or code changed.**
**Phase:** posterior (E5 — Gazebo 2-D baseline, D-50/D-59)
**Gate context:** after Gate G4; design revision for the next 2-D training run (training host).
**Author:** Samuel Sanchez

### Change

`action.max_speed_mps` in the Gazebo 2-D train config revised **0.5 → 0.25**. The header
and action-block comments now carry the revision rationale; the original intent ("0.5 =
C-04 `v_max_straight` so the cage speed rules arbitrate for real") is preserved in the
comment as the superseded design.

### Rationale

The full-authority run's evals (entry below) showed that with the cage's speed thresholds
still `[provisional]` and calibrated at the 1-D 0.2 m/s regime, the intended arbitration is
a wall: **no 2-D enforcement eval completed** (4 runs: 26 steps / 0.62 / 0.91 / 1.52 laps),
every stop C-04+C-05 on a *centered* car at >0.25 m/s, while monitoring showed competent
variable-speed driving. Capping the **action** (not the cage) keeps the policy inside the
validated envelope by construction, preserves the 2-D case for existing (slow-for-curves,
commandable stop → SR-009), avoids loosening safety-traced thresholds to fit the policy,
and should reduce the 2-D exploration burden (less throttle range to explore, fewer
emergency terminations during training). The 0.5 full-authority variant returns **after**
the D-59 speed-envelope calibration for the >0.2 regime.

### Impact

Next 2-D training run (training host) picks this up automatically; suggested run-id
`ppo_gz2d_complex_b_2024_v2`. Existing `ppo_gz2d_complex_b_2024` artifacts/evals unchanged
(they document the full-authority baseline). `metadata.json` will record the new contract
via the `action` block + `train_config_hash` (07.07 provenance hardening).

### Verification

Config parses (`yaml.safe_load`); `pytest policy/tests/test_eval_policy_2d.py` → 5 passed
(the eval action-space guard is shape-based, unaffected by the scale). No traceability
artefact touched.

---

## [13.07.2026] — E5 robustness closed: multi-seed N=5 complete (5/5 + evals), seed-2024 variants (v2 random-start, 2-D) documented + evaluated

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3 table/prose/footnotes/Fig 7.8 caption, **new §7.5.4**, internal appendix), `manuscript/chapters/chapter_08_experimental_evaluation.md` (GE4-closure list: (d) closed), `docs/11_camera_rl_training.md` (**new §8.5**, posterior list (b)/(c), Q6, version log v0.6.2), `tools/plot_f3_figures.py` (legend "pico"→"peak"; **new `fig_variants` + `--variant-runs`**), `manuscript/figures/fig_7_8_multiseed_newcam.png` (regenerated, 5 seeds, English), **new `manuscript/figures/fig_7_9_variants_2024.png`**, `experiments/README.md` (`sim/eval_gz2d/`, `ppo_gz2d_*`), `experiments/sim/training/{ppo_newcam_complex_b_23,ppo_newcam_complex_b_2024_v2,ppo_gz2d_complex_b_2024,ppo_gz2d_complex_b_2024_1M}/metadata.json` (rescued-peak / superseded blocks), 6 eval-run `metadata.json` seed corrections (noted). **New evidence:** `experiments/sim/runs/rl_newcam_eval_{123_cb139k,666_cb226k,23_cb350k,2024v2_cb234k}_4k4{,_mon}` (8 runs) + `experiments/sim/eval_gz2d/rl_gz2d_eval_2024_{525k,525k_mon,500k}_4k4` (3 runs) + 8 `*_r2` replication runs (666/23 and both 2-D ckpts, enf+mon incl. the first 500k mon), all SC-NOM-01 4400 steps, dev host, 13.07.2026. No hazard/SR/cage/scenario/metric criterion changed; no CSV regenerated.
**Phase:** posterior (E5 — camera robustness; the N=5 check deferred at G4, now closed)
**Gate context:** after Gate G4 (closed 02.07.2026). Robustness/reproducibility evidence; does **not** reopen G4 — the verdict of record stays GE4-V2 on the seed-2024 297k E-main.
**Author:** Samuel Sanchez

### Change

**Multi-seed N=5 closed.** Seed **23** trained (peak **782,6 @ 350 208**, stopped ~394k,
−24 %; checkpoint rescued, sha256 `c3c79aba…`) — same exploration-collapse signature as the
other four. Nominal **SC-NOM-01 evals (enforcement + monitoring) run for the three pending
peaks (123, 666, 23)** on the dev host (Gazebo headless, 4400 steps each; `eval_policy`).
§7.5.3 table filled; Fig 7.8 regenerated with all five seeds (peaks marked, English labels).

**Seed-2024 variants documented + evaluated (new §7.5.4 / docs/11 §8.5, Fig 7.9):**

- **v2 (`random_start_s`, D-58):** peak 773,2 @ 234 496 (ckpt rescued, sha256 `2813d13e…`);
  eval enf **5,12 laps / 16,7 mm / 0 emergencies / C-06 77,6 %**, mon clean. The D-58 spawn
  curriculum **does not improve** the Gazebo 1-D E-main (lower peak, worse tracking, heavier
  C-06) — it is a tool for under-visited blocking sections (the Isaac case), absent here.
- **2-D (`train_ppo_camera_2d.yaml`, D-50/D-59):** full run `ppo_gz2d_complex_b_2024` ~629k,
  peak **654,4 @ 509 952** (periodic ckpts 500k/525k bracket it; 525k designated, sha256
  `dadb94de…`; the ~100k dev-host pilot `…_1M` marked superseded). Reward clearly below 1-D
  (654 vs 823/773) — **the throttle dimension did not pay on complex_b**. Eval: monitoring
  **4,66 laps / 21,0 mm / speed 0–0,38 m/s (slows for curves)** — competent variable-speed
  driving; enforcement **stopped by the canonical speed envelope** (525k: C-04+C-05 @ step 26
  at 0,438 m/s > `v_warning` 0,4; 500k: 1,52 laps then C-05 on a centered car, ey 0,013 — CV
  false belief). First real activation of the longitudinal C-04/C-06 arbitration (526
  throttle-corrected steps @ 500k).

**Replication (same day, `*_r2` runs):** the surprising verdicts were re-run end-to-end
(666 enf+mon, 23 enf+mon, 2-D 525k/500k enf+mon — 8 runs, fresh Gazebo, brake-between-runs
mitigation). **666 reproduces deterministically** (stop s=13.5–13.7 at ey 0.116–0.122, C-03→
C-05, both runs; mon 178.3/178.8 mm). **23's monitoring reproduces** (4.93/4.99 clean laps;
CV false positive stable at s=8.86/8.77) but its **enforcement outcome is intermittent**
(replica: 2.44 clean laps, then C-05 on a *centered* car at s=8.75 — the second CV-weak
section actuating directly, vs the s≈13.4 drift of the first run). **2-D:** monitoring
replicates (525k r2: 4.52 laps / 20.0 mm, same speed profile; 500k mon new: 3.83 laps /
18.0 mm at 0.156 mean); **no 2-D enforcement run completes** (4 runs: 26 steps / 0.62 /
0.91 / 1.52 laps), every stop C-04+C-05 on a centered car at >0.25 m/s at varying positions.
3 of the 4 observed 1-D stops land at the s≈13.4 recovery-basin edge.

### Rationale

Closes GE4 pending item (d) (N=5 robustness) and scores the two posterior config variants
the user trained. **Central findings:** (1) the exploration collapse is seed-independent
(5/5; checkpoint-on-peak validated as protocol); (2) the **eval — not the training curve —
classifies the basin**: 666 and 23 look identical to the healthy seeds in training
(C-06-only) yet split in eval — **666 = cage-dependent** (bare: 312 mm off-lane excursion;
caged: controlled C-05 stop at ey 0,122 — the F-track basin reappears under camera on a
different seed, and the cage's protective value becomes visible in nominal), **23 = cage–CV
conflict** (bare: clean 4,99 laps, max 53,6 mm; caged: C-02/C-03 overrides on a confident
wrong CV read steer against the policy's corrective command until C-05 stops it — the first
observed **negative cage interference**, safe but counterproductive); (3) **both stops land
at s≈13,4 / ey≈0,12 m — the D-43/H-12 recovery-basin edge** — making the GE4-V2 under-read
residual an observed in-nominal mechanism; (4) monitoring C-05 counters latch (read
first-flag, not counts); (5) the 2-D enforcement stops confirm **D-59**: cage speed
thresholds (`[provisional]`, 0,2 m/s regime) + scenario speed assumptions must be reviewed
before any 2-D campaign.

### Impact

GE4-V2 verdict of record unchanged (seed 2024; SR verdicts in docs/07 untouched — these are
posterior robustness runs, not campaign evidence). The 23/666 findings sharpen the D-43
under-read thread carried in the posterior list (docs/11 §8.4→§8.5). The 2-D thread now has
a Gazebo baseline number to compare against Isaac kin2. Follow-ups (posterior, optional):
temporal CV estimator at the s≈13,4 section; cage speed-envelope calibration for the 2-D
regime (prerequisite for any 2-D campaign, D-59).

### Verification

`python tools/check_traceability.py` → PASS (no H/SR/C/SC/M artefact changed). 19 eval runs
completed with `status: completed`; the one infra failure (stale-spawn race: a run starting
while the previous run's vehicle still rolled) was detected (step-1 off-road termination),
the bogus dir deleted and the run re-executed cleanly (subsequent chained runs brake the car
via `cmd_vel` between runs). The four surprising verdicts (666, 23, 2-D×2) were **replicated
end-to-end** the same day (`*_r2`, see Change). Figures re-rendered and visually checked
(5 peaks marked; variant curves + peaks consistent with the tables).

---

## [11.07.2026] — Gazebo 1-D multi-seed: seeds 123 & 666 trained (peaks rescued), Fig 7.8 + §7.5.3 table updated

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3 table + prose + Fig 7.8 caption, internal appendix), `manuscript/chapters/chapter_08_experimental_evaluation.md` (GE4-closure pending-list (d) + appendix), `docs/11_camera_rl_training.md` (posterior-work list, Q6), `tools/plot_f3_figures.py` (`fig_multiseed` peak markers), `manuscript/figures/fig_7_8_multiseed_newcam.png` (regenerated, 4 seeds), `experiments/sim/training/ppo_newcam_complex_b_{123,666}/metadata.json` (rescued-peak block). No hazard/SR/cage/scenario/metric criterion changed; no CSV regenerated.
**Phase:** posterior (E5 — camera 1-D multi-seed robustness; the N=5 check deferred at G4)
**Gate context:** after Gate G4 (closed 02.07.2026). Robustness/reproducibility evidence for the E-main; does **not** reopen G4 — the verdict of record stays GE4-V2 on the seed-2024 297k E-main.
**Author:** Samuel Sanchez

### Change

Seeds **123** and **666** of the camera E-main battery ({2024, 42, 23, 666, 123}) were
trained on `complex_b` (steering-only "1-D" action, same config as the seed-2024 E-main)
and **stopped before the 1M plan without converging**. Both peaks were rescued and the
run-records completed:

- seed **123** — `ep_rew_mean` peak **787,1 @ 139 264** steps; stopped ~198k still on the
  healthy plateau (−8%); checkpoint `ppo_newcam_complex_b_123_139264_steps.zip`
  (sha256 `a7069ffe…`).
- seed **666** — `ep_rew_mean` peak **713,2 @ 226 304** steps; decayed −36% to ~458 @ 341k
  before manual stop; checkpoint `ppo_newcam_complex_b_666_226304_steps.zip`
  (sha256 `07166beb…`).

`metadata.json` for both gains the seed-42-style rescued-peak block (`peak_ep_rew_mean`,
`curve_peak`, `peak_checkpoint_timestep`, `last_logged_timestep`, `stop_reason`,
`checkpoint_selection: checkpoint-on-peak`, corrected `policy_checkpoint` path + hash).
`tools/plot_f3_figures.py:fig_multiseed` now marks each seed's reward peak (● + peak
value/timestep in the legend); **Fig 7.8** (`fig_7_8_multiseed_newcam.png`) regenerated
with all **4** trained seeds. §7.5.3 fills the training rows for 123/666 (eval rows stay
`pend.`); prose/caption/§7.2.7 notes move from "2/5" to "4/5 trained".

### Rationale

Advances the N=5 robustness check deferred at G4 to 4/5 on the training side. Central
finding: the **exploration-collapse is seed-independent** — all four seeds rise → peak →
decay (`std` over-anneals) and **none converges over the 1M plan**, with peak height
∈ [713, 823] and peak step ∈ [120k, 297k]. This validates **checkpoint-on-peak** as the
correct selection protocol for this configuration, not a patch for one bad run. All four
are **constraint-respecting** on the training cage signal (C-01/C-03/C-05 ≈ 0; only C-06
active); notably seed **123**, *cage-dependent* on the F baseline (58,8%), does **not**
reproduce that basin under camera (jerkiest — C-06 ~85% — but safe).

### Impact

E-main verdict of record unchanged (GE4-V2, seed 2024). Remaining for a full N=5: the
**nominal SC-NOM-01 evals of the 123/666 peaks** and **training seed 23** (host-deferred,
Gazebo real-time limit). No traceability artefact (H/SR/C/SC/M) affected.

### Verification

`python tools/check_traceability.py` → PASS (documentation/figure/metadata change only;
the H→SR→C→SC→M→verdict graph is untouched). Figure re-render confirmed visually (4 peaks
marked; every curve peaks then decays).

---

## [07.07.2026] — Training metadata now records the action contract, reward weights and train-config hash (Gazebo + Isaac trainers)

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/train_ppo.py` (`_write_training_metadata`), `tools/isaac_train.py` (`write_metadata`), `experiments/README.md` (metadata.json schema — training-run extras noted). No living-doc table, CSV, cage constant or scenario criterion changed.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..D-59)
**Gate context:** after Gate G4 — reproducibility-metadata hardening ahead of the first 2-D training runs; no verdict artefact touched.
**Author:** Samuel Sanchez

### Change

Both trainers' `metadata.json` gains three provenance fields:

- `action` — the D-50/D-59 action contract (`type` / `max_speed_mps` /
  `throttle_deadband`); `{}` for a config that predates the block (frozen 1-D
  steering-only contract, ED-2).
- `reward` — the docs/10 shaping weights the run actually trained under
  (including the 2-D `throttle_delta` / `stall_penalty` terms).
- `train_config` + `train_config_hash` — path + sha256 of the train-config YAML
  itself, threaded into `_write_training_metadata` / `write_metadata`
  (mirrors the existing `cage_yaml` / `policy_checkpoint` path+hash convention).

`tools/isaac_train.py` already recorded `action` (D-50) but neither `reward` nor
the config hash; the two writers are back in lockstep.

### Rationale

With the Gazebo 2-D config (`train_ppo_camera_2d.yaml`, D-59) live, a 2-D run's
`metadata.json` was indistinguishable from a 1-D run's except via
run_id/model_path: the recorded fields (observation, DR envelope,
hyperparameters) are near-identical across the two configs, while the action
mapping and reward weights — which define what optimum was trained — were not
recorded at all. The config hash pins the exact YAML the run trained under
(CLAUDE.md "Reproducibility metadata"), the same way the cage YAML and the
checkpoint are pinned.

### Impact

Purely additive, code-only. Existing runs' `metadata.json` keep their shape —
the new keys simply were not recorded at the time (absent ≠ changed); no
re-runs, no reader/aggregator depends on the new keys. Every future training
run (Gazebo 1-D/2-D, Isaac) records them automatically.

### Verification

Full host suite `pytest` → **507 passed, 5 skipped** (Windows `.venv-win`).
Functional smoke of both writers (ROS-stubbed import of `train_ppo`;
AST-extracted `isaac_train.write_metadata`) against
`train_ppo_camera_2d.yaml` / `train_ppo_camera.yaml` / `train_isaac_2d.yaml`:
the 2-D configs record `steer_throttle` + the full reward block, the frozen 1-D
config records `action: {}`, and `train_config_hash` matches an independently
computed sha256. `tools/check_traceability.py` → **All checks PASSED, 0
warnings** (no ID changes).

---

## [07.07.2026] — Manuscript + satellite-README sweep: track 'E' as evidence of record, F-track framed as superseded baseline

**Document(s) affected:** `manuscript/chapters/chapter_01_introduction.md` (stale future-tense verdict bullet → GE4-V2 as verdict of record, G4 closed), `chapter_02_related_work.md` (§2.2: new end-to-end-vision lineage block — ALVINN/PilotNet/Kendall, domain randomisation — and the thesis's positioning around it), `chapter_03_methodology.md` (same future-tense fix, names `complex_b`, notes the SR register growth to SR-014/H-12), `chapter_05_architecture_and_cage.md` (§5.7 vigencia note: node graph = F-track baseline; new §5.7.4 documents the track-'E' in-process wiring — CameraPipeline split, CV-estimator cage state, 10 Hz lockstep, verdict on true pose), `chapter_06_implementation.md` (new §6.7 "Implementación del track 'E'"; synthesis renumbered 6.7→6.8; §6.1 structure updated), `experiments/README.md` + `tools/README.md` + `scenarios/README.md` (all three pre-dated the E evaluation: campaign map now leads with `campaign_e_v2` as verdict of record, E-era tools documented, oval library marked frozen with pointer to `scenarios_complex_b/`), `docs/01_id_conventions.md` (E-track paragraph: merged single-trunk, prefixes E2/E4/E5, E = system of record), `docs/10_reward_function.md` (header row: reused unchanged by camera training), root `README.md` ("The idea" section now leads with the track-'E' in-process dataflow — camera → CV-estimator/CNN split → cage — and demotes the five-node ROS 2 graph to the physical/baseline pipeline; multi-seed N=5 corrected from "in progress" to deferred-posterior; phase table annotated with the register growth, the E-N/GE-N note and the E5 Isaac status; repo layout gains `scenarios_complex_b/`; ID table gains the `E-X`/`GE-X` row; figure credit covers the camera plotters; reading order gains docs/12), `CLAUDE.md` (hazard row H-01..H-09 → H-01..H-12). **No hazard/SR table row, CSV, code, cage constant or scenario criterion changed.**
**Phase:** track 'E' (posterior documentation, after Gate G4)
**Gate context:** after Gate G4 — documentation reconciliation only; no verdict or threshold touched
**Author:** Samuel Sanchez

### Change

Audit + fix of every doc/manuscript location that still presented the F-track
(ground-truth state vector) as the current system or the GE4 camera campaign as
future work. The documentation now consistently evidences the track-'E' end-to-end
camera system as the system of record (GE4-V2, 1970 runs, 28.06.2026; G4 closed
02.07.2026) and frames the F-track as the frozen, superseded baseline/control arm.

### Rationale

User review (07.07.2026): chapters 1–6 all pre-dated the GE4-V2 verdict (ch.1/3
said 'E' *will* supersede 'F' "cuando se ejecute la campaña GE4"; ch.5/ch.6 only
described the F2 node pipeline; ch.2 lacked the end-to-end-vision related work),
and the experiments/tools/scenarios READMEs still described the F4 campaign as
"in progress" with perturbations "pending validation". Chapters 7–8 and the
2026-07-07 living-doc sweep (docs/00–16) were already current.

### Impact

Manuscript cross-references to the old ch.6 §6.7 (synthesis) now point to §6.8;
checked: the only such reference was ch.6's own §6.1 intro (updated). No generated
artifact (CSV/figure) depends on the edited prose.

### Verification

`python tools/check_traceability.py` — PASS (see below); hazard/SR sync not
required (no machine-readable table touched).

---

## [07.07.2026] — Living-doc sweep: F-track archived, current-state framing added to docs/00/02/03/04/06/10

**Document(s) affected:** `docs/00_v_model_adapted.md`, `docs/02_hazard_register.md`, `docs/03_safety_requirements.md`, `docs/04_cage_specification.md`, `docs/06_metrics_catalogue.md`, `docs/10_reward_function.md`. No machine-readable table, CSV, code, cage constant or scenario criterion changed.
**Phase:** track 'E' (posterior documentation, after Gate G4)
**Gate context:** after Gate G4 (closed 02.07.2026) — several living docs still carried pre-G4 / F-track-primary framing.
**Author:** Samuel Sanchez

### Change

Reviewed the remaining living docs for F-track staleness and brought each to the current
state (track 'E' = verdict of record, F-track = archived baseline, G4 closed), **preserving**
the historical obstacles that led here rather than deleting them:

- **docs/00 (V-Model):** the Track-'E' section said "'F' superseded by 'E' *once the GE4
  campaign runs* (camera eval to date is nominal)" — factually stale. Updated: the **GE4-V2
  campaign has run** (297k E-main, 1970 runs, 28.06.2026) and **G4 closed 02.07.2026**;
  literal `NOT SATISFIED` held only by the SR-002/003 recovery-time clause (D-47), SR-001 +
  SR-012/013/014 Satisfied; Isaac is the posterior thread. A5 "provisional principal evidence"
  clarified (provisional only vs the posterior Isaac stage). Scenario list SC-PERT-04..10 →
  04..13, SC-FRONT-01..06 → 01..07.
- **docs/02 (Hazards):** stale header (`G1 pending`, `13.05.2026`) fixed; added a current-state
  note — all 12 hazard mitigations verified at G4 (F4 + GE4-V2), the in-ODD cage-latent-but-asset
  result and the **H-12 confident under-read** residual recorded so the knowledge is kept; noted
  the `Status: Open` column is hazard *registration*, verdicts live in docs/07. Machine-readable
  table untouched (CSV byte-identical).
- **docs/03 (SRs):** stale header fixed; added a current-state note — spec vs verdict split
  (verdicts in docs/07), the D-47 SR-002/003 reconciliation, **SR-009 N/A-by-construction on the
  1-D action (D-49) / well-posed on the 2-D Isaac action (D-50)**, SR-010 genuine CL-B. Table
  untouched.
- **docs/04 (Cage):** cage YAML version corrected **0.6.0 → 0.6.1** (header + Track-E note);
  added a current-state note with three preserved findings — the cage is latent in-ODD yet
  removes perception-degradation failures; the speed rules C-04/C-05 were structurally latent
  (0.20 m/s < ceilings) and the **2-D posterior (D-50, max_speed = V_MAX)** makes them arbitrate
  for real (latent→measured flip); the H-12 under-read residual.
- **docs/06 (Metrics):** header updated; added a note — metrics are track-neutral; **M-P6 (stall)
  is N/A on the 1-D action (D-49), well-posed only on the 2-D action (D-50)**; M-S5 is the
  frontier headline metric.
- **docs/10 (Reward):** added the track-framing note (this v1.2 reward is the verdict-of-record
  reward, F-track shares it, archived); split §10 into §10.1 (1-D camera verdict, reward
  unchanged — now *confirmed* by the GE4-V2 outcome) and **§10.2 — the 2-D posterior** (D-50):
  the added `throttle_delta` (0.10) and `stall_penalty` (0.5) terms, inert-by-default, with the
  crawl-and-die exploration-collapse obstacle (fixed by `ent_coef 0.01` D-52 + the stall penalty)
  recorded.

Docs already current were verified and left unchanged: **05** (scenario library, GE4-V2),
**07** (traceability, G4 closed), **11** (camera training v0.6), **12** (CV baseline v0.5),
**13/14** (Isaac — the Lane Cam is correctly the RL camera, the ZED Mini is the auxiliary
platform suite Isaac reproduces), **15** (inventory — F=oval / E=complex_b labelled), **16**
(defense compendium — GE4-V2 / 297k / literal verdicts), **01** (structural IDs).

### Rationale

With the track-'E' eval closed (GE4-V2) and G4 signed off, the F-track is archived; the living
docs must show the current state and keep the past obstacles (perception under-read, speed-rule
latency, exploration collapse) documented so the knowledge is not lost. User request.

### Impact

Documentation-only. No hazard/SR machine-readable table, generated CSV, cage constant, reward
weight or scenario criterion changed — only prose headers and current-state framing notes were
added above the tables. Consistent with the docs/08 and docs/09 rewrites earlier today.

### Verification

`tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** `sync_hazard_register.py`
and `sync_safety_requirements.py` re-run: 12 hazards / 14 SRs, CSVs unchanged (tables untouched).

---

## [07.07.2026] — Environment Design (docs/09) retargeted to track 'E' + Lane Cam + 2-D posterior (v0.5 → v0.6)

**Document(s) affected:** `docs/09_environment_design.md` (restructured, v0.6). No code or other doc edited.
**Phase:** track 'E' (posterior documentation, after Gate G4)
**Gate context:** after Gate G4 — the doc still led with the F-track state-vector environment (§1–§9) with the camera track as a §10 appendix, and named the legacy ZED as the source camera.
**Author:** Samuel Sanchez

### Change

Retargeted the RL training-environment design doc to **track 'E' as the sole subject**:

- **Track E is now the body** (§1–§9: camera observation, action, wrapper, reset/episode,
  actuation, visual degradation, cage-on-CV). The **F-track state-vector environment is
  compressed to a baseline / provenance note** (§10) — kept only as the frozen control arm
  for the E↔F "cost of camera" comparison, per the user's "keep only track E".
- **Source camera corrected: legacy ZED → dedicated Lane Cam (IMX219-160 mirror).** §2.1
  adds the full sensor table from `src/cobraflex/urdf/robot.gazebo`: 640×360 R8G8B8, HFOV
  1.5707963 (90°), 20 Hz, clip 0.1/15 m, topic `camera/image_raw_lane`, mount joint
  `camera_link_lane` at pitch **0.30 rad** down, h ≈ 0.077 m. The ZED Mini stereo pair
  stays on the platform for other purposes but is **not** what the track-'E' policy/cage
  read. (The earlier draft's "ZEDm 640×480, HFOV 1.3962634, `camera/image_raw`, pitch
  0.25 rad" was a stale carry-over.)
- **2-D action (steering + throttle) posterior design added (D-50).** §3.2 + §6: the policy
  emits `[steer, throttle]`; throttle → cage scale `u = (a+1)/2` → `speed = max_speed_mps·u`
  (full stop below `throttle_deadband = 0.05`); `max_speed_mps = 0.5 = ODD-1.V_MAX`, so the
  cage speed rules C-04/C-05/C-06 arbitrate for real and SR-009's stall test becomes
  well-posed. Config-gated and **inert by default** (default `action.type: steer`, the ED-2
  1-D contract, D-49 keeps the Gazebo verdict frozen). Records both config surfaces
  (`train_isaac_2d.yaml` Isaac in-process + `train_ppo_camera_2d.yaml` Gazebo counterpart),
  the training levers `ent_coef 0.01` (D-52) / `stall_penalty` (D-56), and multi-circuit
  per-episode sampling on the CV-safe trio `complex_b,complex_d,complex_e` (§5.3, D-50/D-51).
- ED decision table reworked to a track-'E' basis (new **ED-11** camera obs / **ED-12** cage
  on CV / **ED-13** 2-D posterior; ED-1/ED-7 marked superseded-on-E for provenance).

### Rationale

The doc had drifted: it led with the state-vector (baseline) environment and named the ZED
as the camera, neither of which is the verdict-of-record system. Track 'E' (camera, on the
Lane Cam) is the thesis's primary system; the 2-D action is the live posterior thread
(D-49→D-50) that makes the cage speed rules non-latent. User asked to focus the doc on
track E, add the 2-D decision, and fix the camera.

### Impact

Documentation-only; no reward weight, cage constant, action-space default or scenario
criterion changes (the 2-D action is inert-by-default and the Gazebo E verdict stays frozen
on 1-D, D-49). Consistent with `docs/08` §4.6 (camera interfaces), `docs/11` (camera
training), `docs/12` §5 (Lane-Cam geometry) and `docs/13`/`docs/14` (Isaac 2-D). No re-runs.

### Verification

`tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** Confirmed no residual
ZED-as-source-camera claim remains (only the deliberate "replaces the legacy ZED" notes);
Lane-Cam specs cross-checked against `robot.gazebo` and the URDF mount.

---

## [07.07.2026] — ODD Specification (docs/08) rewritten to the track-'E' / G4-closed reality (v0.6 → v0.7)

**Document(s) affected:** `docs/08_odd_specification.md` (full rewrite, v0.7). No other document edited; every `ODD-N.<PARAM>` identifier cited by `docs/03` (SRS), `cage/cage.yaml`, `docs/04`, `docs/16` and the manuscript is preserved.
**Phase:** track 'E' (posterior documentation, after Gate G4)
**Gate context:** after Gate G4 (closed 02.07.2026) — the doc was signed off at G4 but had drifted to the F-track (state-vector / oval) era; this brings it to the GE4-V2 verdict of record. Standing "do not rewrite doc 08" note overridden by explicit user request.
**Author:** Samuel Sanchez

### Change

Retargeted the ODD specification's concrete realisation from the **F-track state-vector
policy on the oval** to the **track-'E' front-camera policy on `complex_b`** (the GE4-V2
verdict of record). Specifically:

- **Sensor/actuation interfaces (§4.6)** rewritten for the front **Lane Cam** (IMX219-160
  mirror, 640×360, HFOV 90°, h≈0.077 m, pitch 0.30 rad) feeding the policy CNN (84×84×4),
  with the cage on its **own deterministic CV lane-estimator** (D-43); the F-track 6-D
  ground-truth state vector retained as the frozen **baseline** (control arm).
- **ODD-2 / ODD-4 adverse axis (§5, §7)** re-specified from state-vector sensor-noise +
  latency + obstacles to **camera-perception degradation**: visual degradation (glare /
  low-light / motion-blur = **H-10**), perception loss (occlusion = **H-11**) and cage
  lane-misdetection (false-lane = **H-12**), with the H-10 domain-randomisation trio + the
  SC-PERT-04..13 eval stressors + the worn/wet/gaps world variants as the named profiles.
  The F4 obstacle profile is **retired** (no observation channel; no verdict scenario).
- **Geometry (§6)** moved oval → `complex_b`: `ODD-1.ROAD_WIDTH` 0.50 → **0.52 m** (road
  edge 0.25 → **0.26 m**, recorded as the new `*.ROAD_EDGE`), perimeter 8.79 → **19.22 m**
  (centre) / **19.93 m** (driven), `ODD-3.KAPPA_MAX` 1.25 → **1.14 m⁻¹** (centre R_min
  0.876 m; driven 0.998 m). The monocular curvature boundary (docs/12 §4.7) promoted to an
  explicit ODD-3 constraint.
- **Action** kept **1-D steering-only** (D-49); the ODD-3/ODD-4 2-D speed envelope declared
  a coverage gap and forwarded to the **Isaac 2-D posterior retrain** (§8; D-50).
- **§8** expanded from a skeletal F5 forward-reference to include the **Isaac Sim
  sim-to-real** posterior bridge (docs/13–14, D-44/D-49/D-50); Isaac noted as a distinct
  simulator whose checkpoints do not transfer (a future retrain, not a re-do of the 297k
  E-main).
- **§12** rewritten from the F4 single-oval reconciliation (D-37) to the **GE4-V2 complex_b
  realisation** (1970 runs); coverage table + declared gaps updated (2-D speed envelope,
  the D-43/H-12 under-read residual, multi-seed, Q10).
- **§11 TBDs**: Q4/Q5/Q7/Q8/Q9/Q12 re-targeted to their track-'E' closures, Q6 retired;
  **Q10** remains the sole open TBD (physical `A_LAT_MAX`, deferred to M-4 / F5).

### Rationale

The document had become "totally outdated and obsolete" (user): it still described a 5-D
state-vector observation, the oval world, an `ACT_DIM=2` speed envelope and F4 obstacle
profiles — none of which is the verdict of record. The GE4-V2 campaign (297k E-main,
complex_b, 28.06.2026) and the G4 closure (02.07.2026) made the camera track the
authoritative realisation, so the ODD spec that the SRS / cage / scenarios trace to needed
to reflect it. Single-sourcing is preserved by keeping every cited `ODD-N.<PARAM>` ID.

### Impact

No SR threshold, cage constant or scenario criterion changes — this is a documentation
retarget, not a re-derivation (the doc states this in §12). Downstream docs that cite
`ODD-N.<PARAM>` IDs (`docs/03`, `cage/cage.yaml`, `docs/04`, `docs/16`, manuscript ch.3/4)
remain valid: all cited IDs verified present, including the wildcard-covered `*.FRICTION`
and the explicit `ODD-3.FRICTION` named for SR-004. `d_max = 0.16 m` is unchanged (the
margin Δ becomes 0.10 m on the 0.52 m road). No re-runs required.

### Verification

`tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** All 20 externally-cited
`ODD-N.<PARAM>` identifiers confirmed present in the rewritten doc.

---

## [07.07.2026] — Pass-mode split: campaign reports now say *how* a run passed (overcame vs emergency stop)

**Document(s) affected:** `tools/campaign_e_failure_modes.py` (per-group `pass_clean` / `pass_with_emergency` counters + a "Pass modes" console section; `campaign_dir` recorded as posix), `tools/run_campaign.py` (`n_pass_emergency` in the per-scenario report; `emergency` column in `campaign_runs.csv` for future campaigns), regenerated `experiments/sim/campaign_e_v2/failure_mode_breakdown.json` (additive — every pre-existing number byte-identical, verified by field-by-field diff), new `policy/tests/test_failure_modes_pass_modes.py` (3 tests) + 1 test in `test_run_campaign.py` + header assertion extended. **No scenario, criterion, threshold or verdict changed.**
**Phase:** posterior (evaluation tooling, after Gate G4)
**Gate context:** after Gate G4 — additive analysis; the GE4-V2 verdict of record is untouched (`campaign_report.json` / `campaign_runs.csv` of the v2 campaign not regenerated)
**Author:** Samuel Sanchez

### Change

Since D-45 dropped `emergency == False` from the adverse pass criteria, a per-run PASS
covers two distinct behaviours that no report distinguished: the policy **overcame** the
stressor and kept driving, or the cage flagged emergency with the safety limits held (in
enforcement, the SR-013 controlled stop). The per-run `summary.json` already records the
flag (`campaign.values.emergency`); the breakdown tool now splits every (scenario, mode)
group's pass count into `pass_clean` + `pass_with_emergency` (invariant: they sum to
`pass`), and the campaign runner reports `n_pass_emergency` per scenario and an
`emergency` per-run CSV column so future campaigns carry the split natively. In
monitoring the flag is the shadow cage's *un-enforced* request, kept per-mode.

### Rationale

User question on the GE4-V2 PERT results: a PASS by controlled stop (availability lost,
safety kept) and a PASS by driving through the perturbation are different findings; the
roll-up's bare pass fraction conflates them. Regenerating the v2 breakdown shows the split
is material: SC-PERT-07/-09/-11/-13 enforcement pass **entirely via emergency stop**
(25/25, 25/25, 30/30, 40/40), SC-PERT-04/-05/-12 are mixed (16/40, 20/40, 18/40 via
stop), SC-PERT-02/-08/-10 pass almost entirely clean (1/40, 1/25, 1/25 via stop).

### Impact

`failure_mode_breakdown.json` gains two fields per group (additive; all pre-existing
values verified identical). Future `campaign_report.json` / `campaign_runs.csv` gain
`n_pass_emergency` / `emergency`. Historical artifacts (F4 campaign, 139k `campaign_e`,
v2 report+CSV) intentionally not regenerated. No docs/05 criteria touched.

### Verification

`pytest` 507 passed + 5 skipped (was 503; +4 new). `tools/check_traceability.py`: all
checks PASSED, 0 warnings. Old-vs-new breakdown diff: no pre-existing field changed;
`pass_clean + pass_with_emergency == pass` holds in all 56 groups.

---

## [07.07.2026] — Defense-preparation documentation: docs/15 (implementation inventory) + docs/16 (defense compendium); stale docs/READMEs reconciled

**Document(s) affected:** new `docs/15_implementation_inventory.md` (full module/script/config/test inventory with test→SR mapping and the run→verdict evidence spine); new `docs/16_defense_compendium.md` (index of all per-doc defense-question banks; PPO/NatureCNN deep dive with hyperparameter provenance; Gazebo wiring narrative; cage lineage — Simplex/RTA/shielding — and the full threshold-provenance table; CV-estimator defense essentials; evaluation-methodology summary; 12 cross-cutting Q&As; reference shelf). Updated: `docs/04` §Unit tests (stale "90 tests / 10 files, YAML 0.4.0" table refreshed to the actual 17 files / 139 tests at YAML 0.6.1; deferred `test_evaluation_order.py` note resolved to the landed `test_joint_envelope.py`); `cage/README.md` + `policy/README.md` (both pre-F2-stale: wrong file lists, wrong phase status, `cage_node.py` mislabelled as a ROS2 node); `CLAUDE.md` "Where to look first" (two new rows). **No code, config, scenario or threshold changed.**
**Phase:** posterior (documentation; defense preparation)
**Gate context:** after Gate G4 (additive, non-normative — docs/15/16 explicitly defer to docs/00–14 and DECISIONS.md on any conflict)
**Author:** Samuel Sanchez

### Change

Added the two cross-cutting defense-preparation documents and reconciled the stale
documentation found while compiling them. docs/15 answers "what is it / where does it live /
which test proves it" for every module, tool script, config and test file in the repo
(inventory verified against a live run: 503 passed + 5 skipped; traceability PASS, 0
warnings, 2026-07-07). docs/16 answers "how does it work / why this design / says who":
the exact CNN (SB3 `CnnPolicy` = NatureCNN 32/64/64+512 over 4×84×84 grayscale), the PPO
hyperparameter provenance table (SB3 defaults vs the three incident-driven E-track
stability levers), the step-by-step Gazebo wiring, the cage's architecture lineage and a
per-parameter provenance table for every `cage.yaml` threshold, plus external anchors
(Simplex, ASTM F3269 RTA, shielding/safe-RL, TTLC/ISO 11270, ISO 26262/21448/UL 4600,
Mnih 2015, Schulman 2017, Raffin 2021, Tobin/Peng DR).

### Rationale

User request (defense preparation): consolidate everything built — much of it via
agentic coding — into documentation the author can study and defend question-by-question,
with values reasoned and referenced to standards/literature where such support exists.
The per-topic docs (00–14) already carry Q&A banks; what was missing was the single index,
the parameter-provenance consolidation, the complete script/test inventory, and the
external-literature grounding.

### Impact

None on any verdict, config or code path. docs/15 §6 test counts and the traceability
baseline should be re-verified (one `pytest` + one `check_traceability.py` run) before a
Gate review or defense rehearsal. The §8 reference details in docs/16 must be verified
against the originals before importing any of them into the manuscript bibliography.

### Verification

`pytest` (Windows host, `.venv-win`): **503 passed, 5 skipped**.
`python tools/check_traceability.py`: **All checks PASSED, 0 warnings** (12 hazards /
14 SRs / 6 cage rules / all scenarios+metrics linked).

---

## [06.07.2026] — D-59: Gazebo 2-D action config (`train_ppo_camera_2d.yaml`) + docs/11/13 command updates — Isaac 2-D findings ported where backend-agnostic

**Document(s) affected:** new `src/cobraflex_rl/config/train_ppo_camera_2d.yaml` (Gazebo 2-D camera PPO config); docs/11 §9 (2-D launch + eval note + "2-D posterior variant" paragraph); docs/13 (`isaac_eval.py` tool-table row + in-process eval / CV-parity command block + kin2 spawn-curriculum command + STOP-file stop + evaluator CLI-flag line); docs/DECISIONS.md (new **D-59**). **No code changed** — the 2-D path is shared `GazeboLaneEnv` / `cage_bridge` / `rewards` and `RosGazeboInterface.send_action` already publishes a variable `linear.x` (D-50).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..D-58)
**Gate context:** after Gate G4 (additive; the frozen 1-D E-main configs untouched → GE4-V2 bit-identical)
**Author:** Samuel Sanchez

### Change

Wired the 2-D action (steering + throttle) for the **Gazebo** camera trainer as a new config
`train_ppo_camera_2d.yaml`, launchable through the existing two-step camera path
(`--train-config` swap only). The config = `train_ppo_camera.yaml` (frozen Gazebo E-main) +
the **backend-agnostic** Isaac 2-D findings [2-D action D-50, `ent_coef 0.01` D-52,
`throttle_delta` / `stall_penalty` D-50/D-56], with the Isaac-renderer/kinematic calibrations
**dropped** [`yaw_gain 2.4` D-54, `cage_isaac.yaml` 40° D-55, heading de-bias D-57] — Gazebo
keeps the canonical cage + `yaw_gain 0.8` (DiffDrive is ~1:1). docs/11 gains the launch/eval
commands + a rationale paragraph; docs/13 gains the `isaac_eval` command block (nominal eval +
CV-parity probes), the kin2 spawn-curriculum command (D-58), and the STOP-file graceful stop.
Full kept/dropped decision table in **D-59**.

### Rationale

User request, while the Isaac host is busy. A clean Gazebo counterpart to the Isaac 2-D track:
Gazebo's ~1:1 yaw and Gazebo-calibrated estimator isolate the 2-D action + reward shaping +
spawn curriculum WITHOUT the Isaac yaw-authority / renderer-perception confounds (D-54/55/57)
that dominated the U-turn diagnostic. The docs were stale on the new Isaac evaluator, the
curriculum config and the STOP mechanism.

### Impact

Purely additive. The 1-D configs have no `action:` block → the env falls to the frozen 1-D
contract, bit-identical (`test_default_config_keeps_the_frozen_1d_contract`); GE4-V2 and every
F/E artefact untouched, no re-runs. A policy trained with the new config is a **new posterior
baseline** (D-49), evaluated with the same config via `eval_policy`. The deployed
`vehicle_control_node` ROS graph (F2 demo) stays 1-D — 2-D is in-process training/eval only.

### Verification

`pytest policy/tests/test_gazebo_lane_env_2d.py policy/tests/test_rewards.py policy/tests/test_cage_bridge.py` → **52 passed**; a YAML-load smoke builds a valid 2-D env with the real cage (action_space `Box(2,)`; full throttle → 0.5 m/s; zero throttle → full stop; `stall_penalty` active). `tools/check_traceability.py` → **All checks PASSED, 0 warnings** (no ID changes).

---

## [06.07.2026] — D-58: hard-section spawn curriculum (`random_start_s`) — reusable training technique from the Isaac U-turn diagnostic

**Document(s) affected:** docs/DECISIONS.md (new **D-58**); docs/13 (new "Hard-section spawn curriculum" subsection); code: `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (config-gated `spawn_perturbation.random_start_s`, default False → bit-identical); Isaac configs set it true; run `experiments/sim/training/ppo_isaac2d_kin2_2024_1M/`.
**Phase:** posterior (Isaac / sim-to-real, D-44..D-57)
**Gate context:** after Gate G4 (default-off → Gazebo/F-E verdicts bit-identical; pytest 508)
**Author:** Samuel Sanchez

### Change

The T1–T6 diagnostic ladder + the perfect-state test (T5) traced the Isaac ~0.4–0.6-lap wall
to a **chicken-and-egg exploration gap** at the tight complex_b U-turn: it is reached only
after the policy survives the preceding track, so early training rarely visits it → no
gradient at the hardest section → it never learns the slow-and-turn. New env feature
`random_start_s`: spawn at a uniform random arc-length along the driven centreline so every
part (incl. the hard corner) is practised from step 0. General reusable curriculum lever
(cheaper than reward shaping; composes with DR + multi-circuit). Default off; deterministic
eval / F4 scenarios (explicit start_s) unaffected.

### Rationale

Documenting a reusable technique the user flagged for future trainings (hard corners on other
circuits / the physical platform). The finding — under-visited hard sections need spawn
diversity — stands on the ladder evidence regardless of kin2's final lap number.

### Impact

Isaac training configs gain the flag; kin2 (2-D + yaw 0.8 champion recipe + `random_start_s`)
shows the strongest Isaac training signal yet (ep_len_mean 269, ~0 % emergencies @220k) —
**nominal-eval lap verdict PENDING** (do not treat as confirmed). **Caveat recorded:** the flag
shifts the training episode-length/return distribution → judge only by deterministic nominal
eval, never training curves.

### Verification

pytest — 508 passed (flag inert by default). `python tools/check_traceability.py` — PASS
(no ID change). kin2 confirmed stepping with the flag active.

---

## [06.07.2026] — Isaac U-turn root-cause diagnostic (T1–T6 ladder) + kin2 breakthrough; session checkpoint

**Document(s) affected:** memory `isaac-diagnostic-ladder.md` (consolidated results table + root cause + next-session plan); docs/DECISIONS.md (D-54..D-58 capture the pieces); diagnostic configs `src/cobraflex_rl/config/train_isaac_{T2_1d,T3_floor,T4_yaw,T5_state,kin_1M,kin2_curric}.yaml`; evals `experiments/sim/eval_isaac/*.json`.
**Phase:** posterior (Isaac / sim-to-real, D-44..D-58)
**Gate context:** after Gate G4 (no verdict artefacts touched; pytest 508)
**Author:** Samuel Sanchez

### Change

Systematic single-variable diagnostic of the Isaac ~0.4–0.6-lap wall (RL policy drove worse
than the hand-coded CV baseline, 0.63 vs 0.97). Ladder (all complex_b, nominal-eval laps):
T1 3→1 circuit 0.34 (dilution not it); T2 2-D→1-D 0.44; T3 −DR=Gazebo-recipe 0.43 (task
complexity not it); T4 +yaw 2.4 0.14 (yaw backfires); **T5 perfect-state 0.45 (perception
DEFINITIVELY not it)**; kin 2-D+yaw1.5 0.47. **Root cause = KINEMATIC + under-visited hard
section:** the U-turn (R 0.97 m) at cruise needs 0.206 rad/s but the Isaac skid-steer at
yaw 0.8 gives ~0.144 (Gazebo DiffDrive gives ~1:1) → must SLOW (2-D), and the policy only
learns it if it practises there. **D-58 `random_start_s` spawn curriculum** cracked it:
**kin2 (2-D + yaw 0.8 + random-s spawn) hit 0.76 laps @293k** (truncated, still driving,
slowed to 0.15 m/s at the U-turn), beating the champion, first clean U-turn crossing.

### Rationale

User goal: iterate/fix until a robust policy, understanding the root. The ladder isolated the
kinematic + exploration root the config levers (D-52..D-57) could never move; the curriculum
is the discovery-based fix.

### Impact

Best-so-far policy: kin2 (0.76, inconsistent — 2/3 eval episodes still die at the U-turn),
resumed with max_episode_steps 1024→2048 toward reliability/full laps. Champion of record
stays `cobraflex_ppo_isaac2d_stage1_2024_1M.zip` (0.63). Gazebo (E-main 4.88 laps on
complex_b) is the proven fallback if kin2 stalls. Session paused here; next-session plan in
the ladder memory.

### Verification

pytest — 508 passed; `check_traceability` — PASS (no ID changes). kin2 293k eval JSONs +
all diagnostic evals archived under `experiments/sim/eval_isaac/`.

---

## [05.07.2026] — v5 result (training record 227.8 but stall-inflated; nominal ≤0.62 + park exploit) → D-56: reward `stall_penalty`; v6 launched

**Document(s) affected:** docs/DECISIONS.md (new **D-56**); `src/cobraflex_rl/cobraflex_rl/rewards.py` (config-gated `stall_penalty`/`stall_progress_min`, default 0.0 bit-identical); `policy/tests/test_rewards.py` (+3, suite 506); Isaac configs (`stall_penalty: 0.5`, `stall_progress_min: 0.25` `[provisional]`). Runs: `ppo_isaac2d_v5_2024_1M/` (completed; loop record 227.8 @ 844k / ep_len 389) + `ppo_isaac2d_v6_2024_1M/` (launched 05.07 10:48). Evals: v5 final/775k/850k under `experiments/sim/eval_isaac/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..56)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

v5 (v4 + D-55 budgets) trained the healthiest curve of the loop (records to 844k, no
collapse, final without hard decay) — but nominal evals expose **stall inflation**: honest
0.62-lap drives mixed with 1747–2200-step idles at 0.005–0.03 m/s (the park mode avoids the
termination penalty and, with the widened blind budgets, the cage no longer executes a
stopped vehicle promptly — SR-009's M-P6 attractor, now measured twice). Champion by laps
remains **stage-1 final (0.63)**. Per D-53's pre-declared reward-rebalance lever → **D-56**:
per-step `stall_penalty` while normalised progress < `stall_progress_min` (0.25 ≈ 0.05 m/s;
slow-but-driving never charged; parking now strictly worse than driving-and-failing).
**v6 = v5 + stall_penalty** (single delta) launched.

### Verification

pytest — 506 passed (3 new pins: inert-by-default, fires-below-threshold,
never-while-driving). v6 confirmed stepping (t=2k: 27.3/46.9).

### D-57 — perception fix (the wall attacked directly); v7 launched (05.07.2026)

Acted on the D-56 conclusion instead of stopping: instrumented the CV controller's per-step
cage estimate and measured a **systematic heading bias** in `cv_epsi` on Isaac pixels (−4.8°
on straights, −13 to −17° at the complex_b U-turn) — a Gazebo-vs-Isaac camera-extrinsic
calibration mismatch, the exact quantity that caps every controller. Fix: config-gated
`heading_bias_rad` in `cv_lane_estimator.py` (default 0.0 → Gazebo bit-identical; Isaac +0.084)
threaded via `cage.perception_heading_bias_rad` into the env cage supervisor + CV baseline
(`gazebo_lane_env.py`, `tools/isaac_eval.py`; +2 unit tests, suite 508). CV validation: reaches
**0.977 laps** (vs 0.45 typ pre-fix) but 2/3 still die at the U-turn (static offset ≠ the
curve-compounded IPM shear; full fix = pitch re-cal, future). A *trained* policy can adapt its
line where the fixed CV cannot → **v7 `ppo_isaac2d_d57_2024_1M`** launched 19:59:
champion **stage-1 recipe + D-57 de-bias only** (single delta vs the 0.63 champion; new
`train_isaac_2d_d57.yaml`). Success = nominal laps > 0.63 → ≥ 1. Full rationale in D-57.

### v6 result + config-lever exhaustion (05.07.2026, addendum)

v6 completed (peak 226.9 @ 540k). Nominal eval: park exploit gone, but **overcorrected to
fast-and-reckless** (complex_b/d 0.04 laps / 36–45-step first-curve deaths at ~0.20 m/s;
peak-550k worse). This closes the D-52..D-56 config-lever campaign: **the champion across
all six iterations is stage-1 (0.63 laps, `c61d4a7e`)** — trained on the *un-fixed* env.
The env fixes D-54/55/56 helped the hand-tuned CV controller drive farther but made RL
outcomes worse/flat; the binding constraint is proven to be the **monocular estimator's
persistent over-read at the complex_b U-turn exit (s≈8.4 m)**, which caps both CV (0.45
typ / 0.97 once) and every RL policy. Config-space exhausted → next lever is the deep
perception/renderer re-calibration (D-43), required before any Isaac verdict. Full table +
interpretation in D-56.

---

## [05.07.2026] — v4 result (fast-and-reckless, ≤0.31 laps) + D-55 addendum: blind-stretch budgets widened (Trigger 5/8) and config-gated supervisor override; v5 launched (v4 + budgets, single delta)

**Document(s) affected:** docs/DECISIONS.md (D-55 addendum); `cage/cage_isaac.yaml` (`n_missing_max_cycles` 5→13, `staleness_max_s` 0.5→1.3, `[provisional, Isaac]`); `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (new config-gated `cage.perception_min_invalid_cycles` — unset = Gazebo-tuned default 4, bit-identical); Isaac configs (+`perception_min_invalid_cycles: 12`). Runs: `ppo_isaac2d_v4_2024_1M/` (completed; peak 170.2 @ 410k; nominal ≤0.31 laps — fast-and-reckless optimum, 0.30–0.35 m/s killed at first-curve entry) and `ppo_isaac2d_v5_2024_1M/` (launched 05.07 02:53). Evals: v4 final/400k, stage-1-on-D55(+wide), CV wide-budget parity — all under `experiments/sim/eval_isaac/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..55)
**Gate context:** after Gate G4 (Gazebo paths bit-identical: env override inert unset; pytest 503)
**Author:** Samuel Sanchez

### Change

v4 (first training on the D-54/55 env) converged to a **fast-and-reckless optimum** — clean
tracking at 0.30–0.35 m/s but killed by C-05 at every first-curve entry (≤0.31 laps; final
model worse than its 410k peak). The remaining blocker for every controller is the ONE
Isaac-renderer blind stretch: the supervisor latches Trigger 8 after 4 invalid cycles and
the cage's missing-state budget (5) stops the run 0.4–0.5 s in. Budgets widened for Isaac
(supervisor 12 cycles via the new config-gated env key; cage Trigger 5/3 to 13 cycles/1.3 s
≈ ≤26 cm blind at cruise). Validation shows the widening cannot rescue estimator-consuming
controllers (CV drives blind into a real off-road; pre-fix stage-1 champion unchanged at
~0.64) — its purpose is the TRAINING equilibrium: an end-to-end CNN policy keeps its own
(raw-frame) perception through the stretch, and the cage no longer executes mid-line
exploration there. **v5 = v4 + these budgets** (single attributable delta).

### Rationale

Iteration discipline (session goal): v4 isolated the training-vs-env coupling; the budgets
are the last calibration-level lever. If v5 still caps below a lap, next is the deep
estimator/renderer investigation at the archived failing viewpoint.

### Verification

pytest — 503 passed (override inert by default). CV wide-budget probe + stage-1-on-wide
eval archived (JSONs). v5 confirmed stepping (t=2k: rew 23.3, ep_len 49.8).

---

## [04.07.2026] — D-54 + D-55: the ~0.63-lap wall root-caused to the ENVIRONMENT (Isaac yaw-authority ceiling + renderer-shifted CV over-read), calibrated and validated by CV-parity probes; v4 training launched on the fixed env

**Document(s) affected:** docs/DECISIONS.md (new **D-54**, **D-55**; stage-1/1b closure note in D-53); new `cage/cage_isaac.yaml` (theta_max 25°→40°, theta_warning 20°→35°, `[provisional, Isaac]` — canonical `cage/cage.yaml` untouched); `src/cobraflex_rl/config/train_isaac_2d{,_stage1}.yaml` (`cage.yaw_gain` 0.8→2.4, `cage.yaml_path`→cage_isaac); `tools/isaac_eval.py` (`--controller cv`, `--cv-speed`, `--cv-yaw-boost`, `--dump-frames` + per-step cage-estimate trace). Evidence: probe JSONs + frame dumps under `experiments/sim/eval_isaac/`; stage-1b record `experiments/sim/training/ppo_isaac2d_stage1b_2024_1M/` (interrupted @1.52M by rule).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..53)
**Gate context:** after Gate G4 (Gazebo cage + verdicts untouched)
**Author:** Samuel Sanchez

### Change

Stage 1b (+1M resume) plateaued below stage-1's band → stopped by rule at 1.52M; its best
ckpts eval at the same **~0.63-lap wall**. The discriminating control experiment followed:
the **non-learned CV reference controller** (4.85 laps on Gazebo complex_b) through the same
Isaac env. It died at the FIRST curve everywhere (45/42/306-step episodes) → **wall #1:
yaw-authority ceiling** (plant delivers ~18 % of commanded yaw; `yaw_gain 0.8` capped the
command below every curve's requirement) → **D-54**: `yaw_gain 2.4` (validated: k≥3 boost
lifts CV from 0.04 to 0.42–0.44 laps, |ey| 13–14 mm). The survivor kill — same fixed spot
(s≈8.4 m), speed- and friction-invariant, TRUE state mm-clean (ey −27 mm, epsi −6.4°) —
exposed **wall #2: the monocular estimator over-reads ~+19° persistently on curves on Isaac
pixels** (cv_epsi −0.30 rad at true +0.03; dumped death frames show the lane fleeing the
image at the U-turn exit) → **D-55**: `cage_isaac.yaml` with theta_max 40°. Beyond 40° is
futile (at 45° the kill is the supervisor's missing-state budget — correct blind-driving
stop). **Parity achieved (with documented residual):** CV probe reaches **0.971 laps with
zero emergencies** on one repeat; the borderline viewpoint stays a coin flip for the
fixed-line CV (~0.45 on others) — an RL policy can learn estimator-friendly lines, which
is operationally what CV-safe driving means. **v4 launched 04.07.2026 18:22**
(`ppo_isaac2d_v4_2024_1M`: stage-1 curriculum config + D-54 + D-55).

### Rationale

Iterations 1–3 falsified the training-side hypotheses (exploration, task-difficulty
curriculum) while the CV-parity experiment — the reference that had proven the whole loop
in Gazebo — isolated the environment itself. Fixing the env under a known-good controller
BEFORE more RL is the SE4AI way round; the residual perception defect is documented and
scoped (supervisor re-calibration = future work, required before any Isaac verdict).

### Impact

Isaac training/eval now run on a calibrated plant (3× yaw command headroom) and an
Isaac-calibrated cage variant; Gazebo artefacts bit-identical. `isaac_eval.py` gained the
CV-baseline mode + perception post-mortem tooling (ring-buffer frame dump + per-step
cage-estimate trace) — the Isaac counterpart of the Gazebo eval's failure-frame dump.
Champion expectation shifts: pre-D-54/55 RL numbers (≤0.63 laps) are NOT comparable with
post-fix runs.

### Verification

pytest — 503 passed (canonical cage untouched); probe campaign archived (13 JSONs + 2 frame
dumps); parity best-case 0.971 laps / 0 emergencias; v4 confirmed stepping on the calibrated
env (scene D-51 trio, visual-DR-only, ent 0.01, yaw 2.4, cage_isaac).

---

## [04.07.2026] — Stage-1 curriculum CONFIRMED: full 1M healthy (peak 223.4, no collapse), nominal 0.63 laps — champion so far; stage-1b (+1M resume) launched per the extend-if-short instruction

**Document(s) affected:** docs/DECISIONS.md (D-53 stage-1 RESULT addendum). Evidence: `experiments/sim/training/ppo_isaac2d_stage1_2024_1M/` (status completed, 1M) + `experiments/sim/eval_isaac/{cobraflex_ppo_isaac2d_stage1_2024_1M,ppo_isaac2d_stage1_2024_1M_725000_steps}_enforcement.json`; new run `experiments/sim/training/ppo_isaac2d_stage1b_2024_1M/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..53)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

Stage 1 (visual-DR-only, D-53) completed its full 1M **healthy**: `ep_rew_mean` 10 → peak
**223.4 @ 747k** (final band 150–190; at 53k it already tripled runs 1–2's level), std
annealed 0.73 → 0.034 **without collapse**, emergencies 0.1–1 %. **Nominal eval:** the FINAL
model is the overall champion — complex_b **0.46–0.63 laps** (618–888 steps), complex_d
0.37–0.63, complex_e 0.02–0.31, conservative speeds 0.14–0.19 m/s; failure is localised
(exactly **one C-05 per episode** ends an otherwise-clean run; C-02 nearly absent), |ey|
15–58 mm. No late capability decay (final ≥ 725k near-peak ckpt) — first run where training
longer kept helping. Still short of the ≥ 1-lap criterion (user calibration: ~800 steps ≈
1 complex_b lap) → per the user's extend instruction, **stage 1b launched 04.07.2026 13:03**:
`--resume-from` the stage-1 final, same config (+1M → 2M; LR resumes ~1.5e-4; ent_coef 0.01
inside the ckpt), run id `ppo_isaac2d_stage1b_2024_1M`, verified "resumed PPO … at 1000448
steps". Stage 2 (full-DR fine-tune) queues behind the first lap-completing checkpoint.

### Rationale

Iteration loop (session goal): stage-1's result confirms dynamics/scene DR was the binding
constraint (D-53) and the remaining gap is refinement, not redesign — the curve still had
slope at 1M.

### Impact

Champion checkpoint: `cobraflex_ppo_isaac2d_stage1_2024_1M.zip` (hash `c61d4a7e…`). No config
or code changes in this cycle. The one-C-05-per-episode signature marks the next diagnostic
target (probable curve-apex failure) if stage 1b plateaus below a lap.

### Verification

Run metadata `completed` (visual DR True / dynamics+scene False, ent 0.01); eval JSONs
archived; resume confirmed in the run log. Monitors armed on the new run.

---

## [04.07.2026] — D-53: run 2 falsified the exploration hypothesis (peak 43.5, ≤0.25 laps, stall mode observed) → iteration 3 = DR curriculum, stage-1 run launched (visual-only DR)

**Document(s) affected:** docs/DECISIONS.md (new **D-53**); new `src/cobraflex_rl/config/train_isaac_2d_stage1.yaml` (deltas vs train_isaac_2d.yaml: `dynamics_randomization` + `scene_randomization` OFF, own `model_path`). Evidence: `experiments/sim/training/ppo_isaac2d_v2_2024_1M/` (status interrupted @ 518k via STOP file — first live use, model + metadata written correctly) + `experiments/sim/eval_isaac/{cobraflex_ppo_isaac2d_lane_2024_1M_v2,ppo_isaac2d_v2_2024_1M_250000_steps}_enforcement.json`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50/D-51/D-52)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

**Run 2** (`ppo_isaac2d_v2_2024_1M`, ent_coef 0.01): the lever worked as designed — std decayed
~5× slower — and the policy **still never found the lap mode** (peak 43.5 @ 258k, 18–32
plateau). Stopped at 52 % by the pre-declared rule (STOP file, graceful). Nominal evals: the
250k peak ckpt is worse than run 1's (6/6 C-05, ≤ 0.25 laps); the final model is degenerate —
8-step dashes or a **0.021 m/s stall-crawl** (the SR-009/M-P6 stall mode observed for real).
Conclusion across runs 1–2: with FULL sim-to-real DR from step 0 the nominal slice is never
mastered, under either exploration regime. **Iteration 3 (D-53): DR curriculum** — stage 1
trains with **visual (H-10) DR only** (the proven Gazebo E-main recipe) on the D-51 trio;
stage 2 will `--resume-from` the stage-1 champion under the full-DR config.
**Run 3 `ppo_isaac2d_stage1_2024_1M` launched 04.07.2026 05:09** (detached, monitored).

### Rationale

Session goal: iterate runs with fixes until a robust policy. Run 2 was the controlled
experiment for the exploration hypothesis; its negative result redirects the lever to task
difficulty (curriculum), exactly the pre-declared next step in D-52.

### Impact

`train_isaac_2d.yaml` stays the full-DR stage-2/final-target config (untouched);
the stage-1 YAML is a documented curriculum variant. Champion so far across iterations:
run-1's 225k ckpt (≤ 0.45 laps) — still far from robust. Stage-1 exit criteria + the
stall-mode watch item (reward rebalance as next lever) recorded in D-53.

### Verification

Stage-1 config parse-checked (visual ON / dynamics+scene OFF, ent 0.01, 2-D, seed 2024,
ckpt_freq 25k); run 3 confirmed stepping on the trio with NO `isaac_dr` randomizer built
(correct: only in-env visual DR). STOP-file mechanism validated live on run 2 (metadata
`interrupted`, final model hash `5159d48b…`). Eval JSONs archived under
`experiments/sim/eval_isaac/`.

---

## [03.07.2026] — D-52: Isaac 2-D run 1 stopped at 88 % (exploration collapse, ≤0.45 laps nominal) → iteration 2 launched with `ent_coef 0.01`; new in-process evaluator + STOP-file graceful stop

**Document(s) affected:** docs/DECISIONS.md (new **D-52**); `src/cobraflex_rl/config/train_isaac_2d.yaml` (`ent_coef` 0.0 → 0.01); `tools/isaac_train.py` (`StopFileCallback`, status `interrupted` on STOP); **new** `tools/isaac_eval.py`. Evidence: `experiments/sim/training/ppo_isaac2d_2024_1M/` (run 1, status interrupted, metadata reconstructed) + `experiments/sim/eval_isaac/ppo_isaac2d_2024_1M_{225000,875000}_steps_enforcement.json`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50/D-51)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

**Run 1** (`ppo_isaac2d_2024_1M`, commit `e51984f6`, launched 03.07 15:32 on this host — user
exception to the ≤1 h rule): `ep_rew_mean` peaked 61.5 @ ~208k, then a decaying 20–40 plateau;
stopped by SIGINT at ~88 % (880k) per the announced sustained-decay rule. The SIGINT
hard-killed the kit process before Python's `finally` (no metadata/final save) — metadata
**reconstructed post-hoc** (297k precedent), `status: interrupted`, last checkpoint 875k.
**Diagnosis:** exploration collapse — policy std 0.99 → 0.095 (36 %) → 0.023 (88 %) with
`ent_coef 0.0`. **Nominal eval** (new `tools/isaac_eval.py`; DR off, deterministic, 3 ep ×
3 circuits, enforcement): peak-225k ≤ 0.45 laps at crawl speeds, 7/9 cage emergencies;
final-875k worse (25–80-step deaths, 8/9) — real capability decay, no full lap ever. Cage
held: 2/18 nominal episodes off-road, everything else stopped by C-05. **Iteration 2**
(D-52): single lever `ent_coef 0.01`, all else identical; plus `StopFileCallback`
(`touch <run_dir>/STOP` → graceful end with model + metadata, status `interrupted`) and the
evaluator itself. **Run 2 `ppo_isaac2d_v2_2024_1M` launched 03.07.2026 23:46** (detached,
~10 h ETA), monitored on std + reward.

### Rationale

Session goal (user, 03.07.2026): evaluate on completion, conclude, iterate runs with fixes
until a robust policy emerges. The collapse mechanism repeats the Gazebo-1M failure family on
a harder task; entropy regularisation is the standard, minimal, attributable counter. Signals
can't stop Isaac cleanly (verified), hence the STOP file; iterating needs a nominal evaluator
(the D-50 follow-on tooling slice).

### Impact

`train_isaac_2d.yaml` now carries `ent_coef 0.01` as the live default (D-52 records the
history). Run-1 artefacts stay as evidence; its 225k peak is the run-1 champion but NOT a
robust policy. Exit criteria for run 2 in D-52 (std ≫ 0.1 stable; nominal laps ≥ 1 on b/d,
≥ 0.5 on e at peak); next levers pre-declared (reward rebalance → DR curriculum → longer
horizon). Gazebo verdicts untouched.

### Verification

`py_compile` on both tools; evaluator validated end-to-end (2 checkpoints × 9 episodes, JSON
records with ckpt hash + commit); checkpoint-load smoke under Isaac python (obs space
(4,84,84) — matches the manual VecFrameStack+transpose replication). Run 2 confirmed stepping
(scene = D-51 trio, DR active, seed 2024). pytest — 503 passed; `check_traceability` — PASS.

---

## [03.07.2026] — Pre-1M checkpoint hygiene: `checkpoint_freq: 25000` in train_isaac_2d.yaml + per-run checkpoint prefix in isaac_train.py

**Document(s) affected:** `src/cobraflex_rl/config/train_isaac_2d.yaml` (new `checkpoint_freq` key + corrected duration comment); `tools/isaac_train.py` (CheckpointCallback `name_prefix` = run id).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — tooling, before the 1M run
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

Two checkpoint-hygiene fixes ahead of the 1M full-authority run: (1) `checkpoint_freq: 25000`
in `train_isaac_2d.yaml` — unset it fell back to `n_steps` (1024), which at 1M steps means
~976 × 20 MB ≈ **20 GB** of rollout checkpoints; 25000 gives 40 (~800 MB) while keeping enough
granularity for a 297k-style peak rescue. (2) The CheckpointCallback prefix was the fixed
string `cobraflex_ppo_lane`, so **every run overwrote the previous run's same-step
checkpoints** (observed live: the D-51 pilot clobbered the morning pilot's rollout ckpts);
the prefix is now the run id. Also corrected the config's duration comment (~11 h at the
measured ~25 env-steps/s on the multi-track + DR 2-D scene, not 8.5 h at 33).

### Rationale

Both surfaced during the 03.07.2026 live validation; neither touches the training math
(same PPO, same env) — pure artefact hygiene for the long run.

### Impact

Checkpoints land as `<run_id>_<steps>_steps.zip` (+ matching `_vecnormalize_*.pkl`);
`--resume-from` is unaffected (explicit path). Existing checkpoints keep their old names.

### Verification

Live micro-run on the Isaac host (`total_timesteps` 2048, `checkpoint_freq` 1024):
completed, produced `<run_id>_1024/2048_steps.zip` + VecNormalize pkls with the run-id
prefix, honoring the YAML key (smoke artefacts removed afterwards). pytest — 503 passed;
`check_traceability` — PASS.

---

## [03.07.2026] — D-51: complex_e re-cut CLOCKWISE — steering-handedness balance for the Isaac multi-track training trio

**Document(s) affected:** docs/DECISIONS.md (new **D-51**; annotation in D-50 "New tracks"); docs/13 (preset list, full-authority offset note); `scripts/generate_complex_track.py` (new analytic builder `_complex_e_cw_waypoints()` + `TRACKS["complex_e"]` + CV-safe comment block); **regenerated assets**: `experiments/sim/tracks/complex_e/` (PNG + centerline + meta) and `src/cobraflex_rl/config/complex_e_centerline.yaml` + `complex_e_right_lane_centerline.yaml`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — before the 1M full-authority run
**Gate context:** after Gate G4 (does **not** reopen it; Gazebo artefacts untouched)
**Author:** Samuel Sanchez

### Change

`complex_e` is re-cut as the **clockwise** circuit of the CV-safe trio (it was CCW like
complex_b/d, and visually a near-twin of complex_d). Same design family — top straight,
wide end U-turns, "W" bottom with a central counter-steer crest — but driven the other
way: per-lap driven turning arc flips from 10.9 m left / 0.6 m right to **2.6 m left /
10.4 m right**. Geometry: R = 1.4 m semicircular ends (the driven right lane runs
**inside** the U-turns on a CW circuit), analytic cosine-W bottom (amplitude 0.145 m,
half-period 1.305 m), straight buffers at the arc→W joins; waypoints generated densely
(0.25 m) by `_complex_e_cw_waypoints()` because sparse Catmull-Rom kinks at curvature
sign flips (twelve sparse candidates measured R_min 0.44–0.89 m — under the boundary).
Full design + trade-offs in **D-51**.

### Rationale

User direction 03.07.2026: with all three circuits CCW the trio's driven lane
accumulated **36.5 m of left-turning arc vs 4.5 m right (8.1:1)** — the 2-D policy would
overfit left-steer commands; invert one circuit so the opposite steering trains. A plain
mirror is NOT CV-safe: CW puts the driven lane inside the U-turns (driven R = centre −
0.1225 m), and mirrored-old-complex_e measured 0.667 m driven — under the docs/12 §4.7
~0.9 m monocular boundary. Hence the widened re-design.

### Impact

Trio steering balance now **28.3 m left / 14.2 m right ≈ 2:1**, with ~⅓ of episodes on a
right-turn-dominant circuit. Shipped complex_e: perimeter 20.55 m, centre R_min 1.08 m,
**driven right-lane R_min 0.956 m** (design estimator; 0.904 m on the rounded YAML, vs
complex_d's 0.895 m on the same yardstick) — the most comfortable CV margin of the trio.
Scene offset of complex_e shifts +49.72 → **+49.92 m** (auto from the new bbox). The 20k
pilot `isaac2d_pilot_20k` ran on the OLD CCW complex_e (its metadata hashes are that
snapshot); the 1M run trains on the CW geometry. complex_a–d untouched.

### Verification

Generator: 411 points, perimeter 20.55 m, R_min 1.08 m, left+right turns TRUE. Shipped
YAMLs re-measured: CW signed area; driven R_min + arc balance as above. pytest — 503
passed. `python tools/check_traceability.py` — PASS (no ID changes). Live Isaac re-render:
three-circuit aerial (offsets +0 / +24.766 / +49.915, gaps + union grass hold) and
lane-cam from the new start (−2.9, 1.6, yaw 0.027 local) — only the own circuit in frame.
**Second 20k pilot on the CW trio** (`isaac2d_pilot_20k_d51`, seed 2024): status
`completed`; metadata records the NEW complex_e lane hash (`a271bc48ef…`) at offset
+49.9151 alongside the unchanged b/d hashes; episodes healthy (ep_len_mean 15–25, no
spawn deaths), cage live (C-04 0.8–1.6 %/step, emergencies ≈4–5 %), `raw_throttle`
logged; final model `policy/checkpoints/cobraflex_ppo_isaac2d_pilot_20k_d51.zip`
(hash `638e8029…`); scene renders archived under the run's `validation/`. End-of-run
reward 13.6 vs the pre-D-51 pilot's 28.5 — expected at a 20k budget with ~⅓ of episodes
on an unseen opposite-handed circuit; not a health signal.

---

## [03.07.2026] — Isaac USD re-import now replaces the canonical package (importer suffixed `cobraflex_isaac_1/` instead of overwriting)

**Document(s) affected:** `tools/isaac_scene.py` (`ensure_robot_usd`), `tools/isaac_import_check.py`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — tooling fix
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

The Isaac 6 URDF importer refuses to overwrite an existing output package and writes a
suffixed `cobraflex_isaac_1/`, `_2/`… beside it instead. `BRINGUP_REIMPORT=1` therefore
used the fresh suffixed copy for that run only, while the canonical
`src/cobraflex/urdf/isaac_usd/cobraflex_isaac/` — git-tracked, and what every cached run
loads — silently kept the stale USD. (The committed package's own `doc` header shows the
same had happened on PC CAST: it was composed from a `cobraflex_isaac_3/`.) Both import
paths now remove the canonical package directory before importing, so a re-import
genuinely replaces it and leaves no suffixed droppings.

### Rationale

Surfaced by the D-50 live validation (03.07.2026): the first `BRINGUP_REIMPORT=1` runs
left `cobraflex_isaac_1/`/`_2/` untracked droppings without refreshing the canonical
package. Harmless while the URDF is unchanged (identical content), but a silent trap for
the first real URDF edit (e.g. the pending zedm inertia fix).

### Impact

`BRINGUP_REIMPORT=1` (and every `isaac_import_check.py` run) now rewrites the tracked
package in place. **Note:** the importer embeds its random `/tmp/…` staging paths in the
USD `doc` metadata, so a re-import is never byte-identical — expect a git diff on the 9
package files after any re-import; commit it when the URDF actually changed, discard it
otherwise.

### Verification

`isaac_import_check.py` on the Isaac host after the fix: **PASS**, output at the
canonical path, `isaac_usd/` contains only `cobraflex_isaac/` (no suffixed dirs), stage
walk unchanged (articulation root, 17 frames, 9 meshes, 4 wheel revolute joints).

---

## [03.07.2026] — D-50 live validation on the Ubuntu + Isaac host — full-authority env verified end-to-end (URDF→USD, three-circuit scene, Lane-Cam isolation, 20k 2-D pilot); host-deferral closed

**Document(s) affected:** docs/DECISIONS.md (D-50 Status → VERIFIED + closure note); docs/13 (status header, full-authority section, RL-training host-deferred note → validated, measured multi-track throughput). **No code or config changes.** New evidence: `experiments/sim/training/isaac2d_pilot_20k/` (learning curve, action samples, metadata, final checkpoint `policy/checkpoints/cobraflex_ppo_isaac2d_pilot_20k.zip` hash `9a375c52…`) + `…/isaac2d_pilot_20k/validation/` (5 scene/camera renders, C-04/C-06 throttle-probe CSV, one-off probe scripts).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — after E4/G4 close
**Gate context:** after Gate G4 (does **not** reopen it; no Gazebo verdict artefact touched)
**Author:** Samuel Sanchez

### Change

The D-50 host-deferral is closed: the full-authority environment was validated live on the
Ubuntu + Isaac 6 host (the only step D-50 left open). Performed, in order: (1) sanity —
`check_traceability` PASS, pytest **503 passed** on this host, Isaac python has sb3 2.8.0 /
gymnasium 1.2.3 / torch cu130 + CUDA; (2) scene smokes — `isaac_import_check.py` PASS
(exit 0); three-circuit scene `complex_b,complex_d,complex_e` builds at the designed
offsets (+0.0 / **+24.766** / **+49.724** m, 15 m bbox gaps, one union grass backdrop,
complex_b in native coordinates); per-circuit Lane-Cam renders from each start line show
**only the own circuit** (far-clip isolation holds, incl. the tightest case complex_e →
complex_d, ~16.2 m); (3) **20k full-authority pilot** `isaac2d_pilot_20k` (seed 2024,
`train_isaac_2d.yaml` verbatim except `total_timesteps: 20000`, final model via
`--model-path` into `policy/checkpoints/`): status `completed`, episodes survive the
spawn CV/cage priming (`ep_len_mean` 13.5 → **35.6**, never the 1–2-step failure mode),
`ep_rew_mean` 7.8 → **28.5** (explained_variance 0.85), `metadata.json` records
`platform: sim-isaac`, the `action` block and the 3-entry `circuits` block with
per-circuit YAML hashes, `action_samples.csv` carries `raw_throttle`; (4) **C-04/C-06
interplay probe** (scripted full-throttle, DR off — `validation/throttle_probe.csv`).

### Rationale

D-44/D-50 precedent: authored + unit-tested offline on the Windows host, the live Isaac
flow (USD multi-track build, Replicator annotator, SB3-in-Isaac-python) had to be
confirmed on the Isaac host before the 1M training is launched. This entry records that
confirmation and the first live measurements of the D-50 design predictions.

### Impact

The cage speed rules are now **measured, not latent**: C-04 fires on 0.7–1.8 % of training
steps (emergencies ≤ 6.5 %, C-06 ~93–95 % on the noisy early policy). The probe shows
acceleration is slip-limited by the 0.05 sim friction to ~0.49 m/s² (numerically
coincident with C-06's 0.5 m/s² commanded bound); the straight ceiling (~0.49 of
0.5 m/s) is reached with zero speed-rule chatter, and a dropping contextual ceiling
escalates C-04 → C-05 emergency within one cycle — **no C-04/C-06 sawtooth; no cage.yaml
re-tune needed** (thresholds stay `[provisional]`). The **1M main run is ready but NOT
launched on this host** (≤1 h host rule): on PC CAST run
`BRINGUP_REIMPORT=1 $ISAAC tools/isaac_train.py --run-id ppo_isaac2d_2024_1M --model-path
policy/checkpoints/cobraflex_ppo_isaac2d_lane_2024_1M` (defaults carry the config + CV-safe
trio; geometry track mode needs no PNGs; PC CAST's Isaac python needs sb3 + gymnasium).
Two sizing notes for that run: measured throughput on this scene is **~25 env-steps/s**
(RTX 5060, headless) — below the ~33 single-track 1-D figure, so ~11 h, not 8.5 h, on this
GPU class; and `checkpoint_freq` defaults to `n_steps` (1024) → ~976 × 20 MB ≈ **20 GB** of
checkpoints for 1M (consider `checkpoint_freq: 25000` in the config — left untouched here).

### Verification

`python tools/check_traceability.py` — PASS (no ID changes). pytest — 503 passed (this
host). Smoke exit codes 0; scene offsets asserted against `track_offsets` output; pilot
artefacts verified (metadata status/hashes/blocks, CSV schemas, 20 rollout checkpoints +
final model). Renders + probe CSV archived under
`experiments/sim/training/isaac2d_pilot_20k/validation/`.

---

## [02.07.2026] — D-50: Isaac full-authority training environment — 2-D action (steering + throttle) + multi-circuit sampling + CV-safe tracks complex_d/e

**Document(s) affected:** docs/DECISIONS.md (new **D-50**); docs/13 (status, command reference, TRACK env, track presets + curvature-boundary caveat, new §"Full-authority training", complex_b preset description corrected to the committed two-lane asset); docs/14 (§1.1 future-work note → implemented D-50 contract). Code (posterior track, no verdict artefacts touched): `gazebo_lane_env.py` (config-gated `action:` block + `circuits=` per-episode sampling), `cage_bridge.py` (2-D maps `policy_throttle_to_cage` / `target_speed_from_throttle_2d` / `safe_action_to_cmd_2d`), `rewards.py` (`throttle_delta`, default 0.0), `callbacks.py` (`raw_throttle` column), `tools/isaac_scene.py` (multi-track scene, `TRACK_GAP_M` 15 m, shared DR materials, union backdrop, `load_circuits`), `tools/isaac_train.py` (defaults → `train_isaac_2d.yaml` + `complex_b,complex_d,complex_e`; circuits + action metadata), new `src/cobraflex_rl/config/train_isaac_2d.yaml`, `scripts/generate_complex_track.py` (presets `complex_d`/`complex_e`), generated track assets (`experiments/sim/tracks/complex_{a,c,d,e}/`) + config centerlines (`complex_{a,c,d,e}_{right_lane_,}centerline.yaml`). Tests: `policy/tests/test_gazebo_lane_env_2d.py` (new, 16), `test_cage_bridge.py` (+8), `test_rewards.py` (+4).
**Phase:** posterior (Isaac / sim-to-real, D-44) — after E4/G4 close
**Gate context:** after Gate G4 (does **not** reopen it)
**Author:** Samuel Sanchez

### Change

The D-49 deferral is taken up for the Isaac track: the training environment now supports a
**2-D action (steering + throttle)** and **multi-circuit per-episode track sampling**, both
config-gated and **inert by default** (no `action:` block ⇒ the frozen 1-D ED-2 contract).
The policy's throttle maps to the cage scale u ∈ [0, 1] and actuates as
`speed = 0.5 m/s · u` (full stop below the 0.05 deadband) — 0.5 m/s = C-04 `v_max_straight`
= ODD-1.V_MAX, so the cage speed rules **genuinely arbitrate** (the 1-D actuation capped
speed below every ceiling ⇒ structurally latent). Reward gains a raw-delta `throttle_delta`
term (default 0.0). `isaac_train.py` defaults to the full-authority run: camera CNN + 2-D
action + physics/scene/visual DR on the multi-track scene `complex_b,complex_d,complex_e`
(15 m apart = Lane-Cam far clip; one circuit sampled per episode; per-circuit YAML hashes in
the run metadata). `complex_d`/`complex_e` are new **CV-safe presets** (driven-lane
R_min 0.932/0.907 m ≥ the docs/12 §4.7 ~0.9 m curvature boundary); `complex_a`/`complex_c`
assets were generated but violate that boundary (0.28/0.42 m) — reserved for
ground-truth-cage/monitoring runs.

### Rationale

G4 closed with project time remaining; the scope deliberately re-expands to the most
ambitious Isaac target (user decision 02.07.2026): a fully autonomous CobraFlex —
steering **and** throttle, camera perception, able to follow the lane markings of any
circuit — trained under maximum sim-to-real realism. The 2-D action makes SR-009's
stall/liveness sub-mode well-posed (M-P6 meaningful, SC-PERT-03 exercisable) and turns the
cage's speed rules from latent into measured behaviour; multi-circuit sampling + DR is the
operational meaning of "any circuit" at this stage. Design details and trade-offs in D-50.

### Impact

Gazebo verdicts, the F/E baselines and every existing config are untouched (default action
type `steer`; regression suite green). An Isaac-trained 2-D policy is a **new baseline** —
its evaluation (campaign runner support for 2-D checkpoints, SC-PERT-03 negative test,
cage speed-rule re-tuning if the C-04/C-06 interplay oscillates) is follow-on work on the
Ubuntu + Isaac host, where the live flow (multi-track USD build, Replicator, SB3-in-Isaac)
must be validated first (D-44 host-deferred precedent).

### Verification

`python tools/check_traceability.py` — PASS (no ID changes). Full pytest suite on the
authoring host (`.venv-win`, py3.14): **498 passed, 5 skipped** (pre-existing cv2 skips),
including the 16 new end-to-end env tests (real cage through a fake interface: C-04 fires
on overspeed, C-06 clips throttle jumps, full brake = true stop, circuit sampling
seed-reproducible + pinnable) and the C-06/accel alignment pin (0.5 m/s² ≤ 0.53).
`py_compile` on `isaac_train.py`/`isaac_scene.py`. Track radii verified against the
curvature boundary at generation time.

---

## [02.07.2026] — Gate G4 CLOSED — Phase-4 evaluation complete on both arms; docs synchronized to the GE4-V2 verdict of record; next phase = Isaac / sim-to-real

**Document(s) affected:** docs/07 (G4 closure note + matrix rows SR-012/013/014 → GE4-V2 Satisfied + historical re-scoping of the 139k evidence block + notes ⁴/⁵/⁶) and `tools/traceability_matrix.csv` (E-track rows → satisfied on `campaign_e_v2`; SR-006 rows → satisfied per D-39); docs/05 (SC-PERT-11/12/13 + SC-FRONT-07 documented, library 24 → **28**, executed-campaign notes); docs/11 (v0.6: header/preamble to GE4-V2 + closure status); docs/12 (v0.5: H-12 under-read note in §4.4 + ruta-2b revert + head-to-head closed); docs/13–14 (E4-closed pointers); docs/DECISIONS.md (D-48 status → CLOSED); manuscript ch.7 (GE4 executed, §7.1/§7.5/§7.6/appendix) + ch.8 (intro/§8.7/§8.9.5/§8.10 to V2 + G4); README.md (results + phase table G4 complete); CLAUDE.md (phase snapshot); memory index.
**Phase:** E4 close → posterior (Isaac / sim-to-real)
**Gate context:** **Gate G4 closed 02.07.2026**
**Author:** Samuel Sanchez

### Change

G4 (Phase-4 sim evaluation) is formally closed on the two campaign arms:
**(i) F-track F4** (frozen 10.06.2026): 1260 runs, global **`SATISFIED`** (all 7 SR-CL-A).
**(ii) Track-'E' GE4-V2** (verdict of record, 28.06.2026): 1970 runs, global **`NOT SATISFIED`
(literal)** blocking SR-002/003 only — both Satisfied on their own criterion (D-47), so **no
SR-CL-A safety predicate is breached on either arm**; SR-001 Satisfied (ruta-1), SR-012/013/014
Satisfied. Open items are documented, CL-B and non-vetoing (D-30): the F-arm SR-009/010 TBD
abstentions (SR-009 stall arm N/A-by-construction for the shared 1-D action, D-49; SR-010's
co-activation question answered on the E arm by the V2 grid — 30/85 in-ODD, genuine CL-B),
the verdict-framing decision (recorded as literal + annotation), and multi-seed N=5
(host-deferred). All prose that still described GE4-on-297k as pending (ch.7/ch.8/README/
CLAUDE.md/docs/12/13/14/scenarios_complex_b) is synchronized; the four complex_b-native
scenarios run by V2 (SC-PERT-11/12/13, SC-FRONT-07) are now first-class docs/05 entries.

### Rationale

The GE4-V2 campaign (28.06.2026) supplied the last verdict-bearing evidence Phase 4 needed;
what remained was documentation debt: matrix rows and CSV still scored the superseded 139k
roll-up, docs/05 lacked the four scenarios the campaign ran, and several documents still
called the 297k campaign "pending". Closing G4 requires the master record (docs/07), the
scenario library and the manuscript to agree with the evidence of record.

### Impact

Thesis verdicts are **frozen in Gazebo**; the open thread is the posterior Isaac / sim-to-real
track (docs/13–14, D-44): 2-D action retrain (D-49, makes SR-009 well-posed), better perception
(temporal estimator — the honest H-12 closure), and the sim-to-real gap toward the physical
platform (Phase 5). Isaac work does not reopen G4. No hazard / SR / cage-rule / metric IDs
added or changed; scenario definitions added to docs/05 match the executable YAMLs already in
`scenarios_complex_b/` (no new IDs — they existed since 24.06.2026).

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (28 scenarios now
defined, incl. SC-PERT-11/12/13 + SC-FRONT-07; all reference SRs). Campaign evidence
unchanged: `experiments/sim/campaign_e_v2/` (1970/1970, 0 errors) + `experiments/sim/campaign/`
(1260 runs). No code changes — docs/CSV only.

---

## [28.06.2026] — GE4-V2 campaign COMPLETE — SR-001 closed by ruta-1; global NOT SATISFIED (literal) blocking SR-002/003 only

**Document(s) affected:** docs/07 (GE4 note + Last-update + note ⁷), docs/11 (§8.4 rewritten to V2), docs/DECISIONS.md (D-47/D-48 V2 outcome), manuscript ch.8 §8.9; new evidence + figures under experiments/sim/campaign_e_v2/  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation — verdict of record  
**Author:** Samuel Sanchez  

### Change

GE4-V2 ran on the 297k E-main with the validated V2 prep (honest legacy estimator): **1970 runs, seed
2024, 0 errors** (`experiments/sim/campaign_e_v2/`). **Global `NOT SATISFIED` (literal), blocking
SR-CL-A SR-002/003 only.** Headline result vs V1 (which blocked SR-001/002/003 + SR-012/014
incomplete): **SR-001 is now Satisfied** — ruta-1's in-ODD IC clip removed the 9/30 out-of-ODD
SC-EDGE-02 spawns SR-001 must not be charged for, so SC-EDGE-02 passes **28/30** (2 residual breaches
at the recovery-basin edge 0.118–0.121 m). **Ruta-1 alone closed SR-001; ruta-2b was unnecessary** (and
was reverted after its closed-loop regression). **SR-012/013/014 Satisfied** (coverage closed). SR-002/003
fail only the oval-legacy 2.0 s recovery-time clause (13/30, max M-P4 = 14.4° ≤ 25°) → reconciled
Satisfied (D-47). So no SR-CL-A safety predicate is breached. SR-010 genuine CL-B (30/85 in-ODD
co-activation breaches). Verdict of record (user decision): **literal NOT SATISFIED + reconciliation
annotated** (not re-stated as SATISFIED). Regenerated V2 figures (`tools/plot_camera_comparison.py`,
`plot_frontier.py`) + new `fig_sr001_edge02_offset.png`.

### Rationale

The early-output check on the first V2 launch caught the ruta-2b regression and aborted it; the relaunch
with the legacy estimator gave the clean verdict. The result is *better* than predicted (SR-001 closes),
showing ruta-1 (scoping the IC to the ODD) was the real fix.

### Impact

Verdict of record moves to V2 (`campaign_e_v2`); V1 (`campaign_e_297k`) + 139k become historical.
docs/07, docs/11 §8.4, D-47/D-48 updated; manuscript ch.8 §8.9 updated. No CSV regen (no hazard/SR edits).

### Verification

`pytest` 475 passed; `check_traceability` PASS; campaign 1970/1970, 0 errors. Comparison via
`scratchpad/compare_v1_v2.py`.

---

## [27.06.2026] — ruta-2b REVERTED (conservative lane-selection); no robust single-frame fix for the H-12 under-read (D-48)

**Document(s) affected:** src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py, policy/tests/test_cv_lane_estimator.py, docs/07, docs/11, docs/DECISIONS.md (D-48)  
**Phase:** E4 (track-'E' GE4 evaluation — V2 prep)  
**Gate context:** GE4 (camera) evaluation — V2 launch verification  
**Author:** Samuel Sanchez  

### Change

The committed ruta-2b conservative lane-selection (`conservative_lane_selection`) is set **default
False** (legacy nearest-centre restored). Reason: verifying the first V2 launch's early output caught
a regression — **SC-EDGE-01 emergency at step 1** (V1: clean 150 steps). The conservative rule cannot
distinguish a genuinely off-centre vehicle from a *centred* one under a small heading error (both
split into the same opposite-sign pairs), so it fires spurious C-01/C-05 emergencies. A heading gate
only relocated the false trigger to step 8 (a 9-run closed-loop smoke confirmed SC-EDGE-01 still
emergencies and **SC-NOM-02, a clean V1 nominal curve, regressed**). The ambiguity is irreducibly
single-frame; a real fix needs temporal lane tracking, which still would not fix the SC-EDGE-02 spawn
frame (no prior) → would not close SR-001 anyway. **SR-001 stays a genuine fail** (the H-12 under-read
is an un-cheaply-patchable D-43 limitation). Kept opt-in for the regression tests / future work.

### Rationale

A 16 h verdict campaign must use a trusted estimator; an estimator that fires spurious emergencies on
centred/recovering/curving views would invalidate the run (and is scientifically dishonest vs the
genuine SR-001 finding). The early-output check did its job.

### Impact

V2 re-runs with the legacy estimator; SR-001 expected to fail (global `NOT SATISFIED`). Ruta 1 (in-ODD
IC), the run-count bump (SR-012/014), and the D-47/SR-006/SR-009/SR-010 reconciliations are unaffected.
The prior-entry claims of "ruta-2b implemented + validated" are superseded by this revert.

### Verification

`pytest` → **475 passed** (conservative tests now opt-in explicit). `check_traceability` PASS.
Closed-loop smoke (SC-EDGE-01/02 + SC-NOM-02 curve) is what surfaced the regression.

---

## [27.06.2026] — GE4-V2 prep: SC-EDGE-02 in-ODD IC clip (ruta 1) + H-12 under-read mechanism finding (D-48)

**Document(s) affected:** docs/DECISIONS.md (D-48), docs/07 (GE4 note mechanism), docs/11 (§8.4 mechanism), scenarios_complex_b/edge/sc_edge_02.yaml; src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py + policy/tests/test_cv_lane_estimator.py  
**Phase:** E4 (track-'E' GE4 evaluation — V2 prep)  
**Gate context:** GE4 (camera) evaluation — V2 closure prep  
**Author:** Samuel Sanchez  

### Change

Investigated the sole remaining SR-001 blocker (SC-EDGE-02). **Ruta 1 (applied):** clipped the IC
randomisation so every spawn is in-ODD — `lateral_offset_uniform_m: [-0.02, 0.02] → [-0.02, 0.0025]`
(seed 0.12 m → [0.10, 0.1225]); the V1 symmetric band spilled 9/30 reps out-of-ODD. **Mechanism
correction (D-48):** V1 traces show the SC-EDGE-02 fails are an **H-12 estimator under-read**, not
perception loss — `cv_ok` stays True and `cv_ey ≈ 0.04 m` while true `ey` → 0.30 m (wrong-lane lock,
self-consistent, so SR-014 misses it). Corrected the "estimator loses the lane" wording in docs/07 +
docs/11 §8.4. **Ruta 2b (implemented + validated):** a Gazebo frame dump at the SC-EDGE-02 offsets
pinned the cause — when the vehicle is past its own left line a third (next-left) line forms a
competing pair whose opposite-signed centre is marginally nearer, so the legacy `min |centre|`
selection mis-locks onto the neighbour. Fix: `CvLaneEstimator` now picks the conservative
(largest-offset) pair when plausible pairs straddle the vehicle with opposite-sign centres
(`conservative_lane_selection`, default True; inert otherwise). Re-running the dump, cv_ey now reads
+0.140 / +0.181 m at ey 0.12 / 0.16 (was −0.130 / −0.088); full pytest green (471, +2 wrong-lock
regression tests). Ruta 2a (retrain) is out of scope per user. **SR-012/014 D-29 gate:** their V1
INCOMPLETE was a run-count gap (SC-PERT-08/09/10 ran 20 enf < the 25 CL-A min; the SC-PERT-07-style
bump had been missed) — bumped 20 → 25 (enf+mon); all pass 20/20, so V2 reaches coverage. **CL-B
items (non-gating) addressed** (docs/07 note ⁸): SR-011 reconciled on its own metric (max σ_θ over
1 s = 3.0° < 5° M-P7; same SC-EDGE-01 recovery-time artifact as SR-002/003); SR-006 re-pointed in
`run_campaign.aggregate_sr` → `scored_out_of_band` (`OUT_OF_BAND_SRS`, +unit test; D-39 follow-up)
so the V2 report stops reading `failed`. **SR-010 attribution gap CLOSED** (on existing V1 data —
`grid_point` is persisted under `summary.json["campaign"]`): added `sc_edge05_grid_split` to
`tools/campaign_e_failure_modes.py` (+3 unit tests). The split corrects the earlier "largely OOD"
guess — **30 of 85 in-ODD grid points breach M-S1** (a genuine SR-010 co-activation finding) vs 10/15
OOD; SR-010 is a real CL-B result, plausibly reduced in V2 by ruta-2b. **SR-009 resolved as N/A for the
steering-only action space (D-49):** SC-PERT-03's stall test is ill-posed for `ACT_DIM=1` (throttle
fixed → M-P6 ≡ 0 by construction, the `r−λ·|throttle|` injection is inert) — the stall fine-tune was
**not launched** (it would produce an identical policy). Stall arm satisfied-by-construction; the live
M-S2-monitoring arm is covered. **D-49** records: keep steering-only for the Gazebo E verdict (ED-2),
defer 2-D action (steering+throttle) to the Isaac posterior track (docs/14) after E4 closes for Gazebo.

### Rationale

SR-001 is the only thing standing between the GE4 verdict and (at best) INCOMPLETE; pinning down
whether it is a scenario-IC artifact or a genuine cage limitation required the trace analysis above.
It is both: 9/12 V1 fails are an out-of-ODD IC spill (ruta 1 fixes), and the residual is a genuine
H-12 safety-monitor blind spot (ruta 2b target).

### Impact

No verdict change yet (V2 not re-run). SC-EDGE-02 IC changed → its spawns differ in V2; the cage
perception is changed (conservative selection, default on) → the V2 campaign uses it automatically.
GE4-V2 is **ready on the perception side**; the open step is the ≈1940-run campaign itself (a host
job) + the closed-loop confirmation it gives. No CSV regeneration.

### Verification

`tools/check_traceability.py` → All checks PASSED, 0 warnings. `sc_edge_02.yaml` re-parses (valid).
`pytest` → **471 passed** (incl. 2 new wrong-lock regression tests). Gazebo frame dump
(`scratchpad/edge02_estimator_dump.json`): cv_ey +0.140 / +0.181 m at ey 0.12 / 0.16 (corrected).

---

## [27.06.2026] — complex_b GE4 scenario validation + SR-002/003 own-criterion reconciliation (D-47)

**Document(s) affected:** docs/07 (GE4-297k note + new footnote ⁷), docs/11 (§8.4 verdict + table), docs/DECISIONS.md (D-47), scenarios_complex_b/ (24 scenario banners + 22 inline comments, README.md)  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation — verdict validation  
**Author:** Samuel Sanchez  

### Change

Validated the `scenarios_complex_b/` library against the 297k GE4 evidence on four axes and
recorded the result. (1) **Timing/geometry audit:** `start_s_m = 2.0` re-mapping confirmed sound;
`*_completed` termination events confirmed decorative (`scenario_runner` is `timeout_s`-bounded);
only SC-EDGE-03's throttle pulse lands on the straight (optional curvature-coupling refinement,
SR-004 already satisfied). (2) **Spawn spot-check:** confirmed from the verdict-run
`cage_status.csv` spawn rows — SC-EDGE-02 lateral +0.128 m (IC 0.12), SC-FRONT-01 +0.169 m
(IC 0.16), SC-EDGE-01 yaw +14.3° (IC 15°), `start_s = 2.0` on the straight. (3) **Frontier
scoring:** confirmed already correct — the aggregator maps SR→scenario via the docs/03 "Verified
by" lists, so SC-FRONT-* are contrast-only and never veto an SR-CL-A. (4) **SR-002/003
reconciliation (D-47):** the 9 SC-EDGE-01 enforcement "fails" fail only the oval-legacy
`time_to_recovery_heading < 2.0 s` clause; on the SRs' own criteria (M-P4 = 14.3° ≤ 25°;
TTLC unbreached, max M-S1 = 0.035 m) both are **Satisfied**. Updated docs/07 + docs/11: blocking
SR-CL-A **{SR-001/002/003} → {SR-001}**, the F4→E flip list drops SC-EDGE-01, and SC-EDGE-02 is
re-characterised as an *in-ODD* boundary-band failure (not "out-of-ODD"). Replaced the stale
"DRAFT / NOT validated" banners on 24 scenarios with a VALIDATED banner.

### Rationale

The GE4-297k global `NOT SATISFIED` was reported as blocking on three SR-CL-A; validation against
the logged per-run evidence shows two of the three (SR-002/003) are scored by a scenario clause
that is neither SR's documented satisfaction predicate — the same honesty defect D-39/note ⁴ fixed.
SR-001 remains a genuine breach (in-ODD 0.12 m start → 12/30 enforcement edge contacts), so the
global verdict is unchanged but its cause is now single and clean (D-43 camera-perception cost on
lateral recovery; heading/TTLC hold under the camera).

### Impact

Global 297k GE4 verdict unchanged (`NOT SATISFIED`, SR-001). SR-002/003 verdicts move
Not-satisfied-as-scored → Satisfied-on-own-criterion. No re-run required — the reconciliation is
computed from existing logged evidence (`epsi`/`summary.json`). The F-track matrix rows
(SR-001..011) are unaffected (F4 frozen). No CSV regeneration (no hazard/SR register edits).

### Verification

`tools/check_traceability.py` — see entry below / re-run after edit.

---

## [27.06.2026] — GE4 evaluation campaign on the 297k E-main (complex_b) — global NOT SATISFIED

**Document(s) affected:** docs/07, docs/11 (§8.4 new, §9.2, version log v0.5), scenarios_complex_b/README.md; tools/run_campaign.py, tools/plot_camera_comparison.py; new evidence under experiments/sim/campaign_e_297k/  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation  
**Author:** Samuel Sanchez  

### Change

Ran the full GE4 verdict campaign on the **complex_b 297k peak** E-main: **1940 runs**,
seed 2024, 28 scenarios × {enforcement, monitoring}, 0 errors
(`experiments/sim/campaign_e_297k/campaign_report.json` + `failure_mode_breakdown.json` +
6 figures). Documented the verdict in docs/11 §8.4 and the docs/07 GE4-on-297k note (the
139k per-SR block is now historical). Pre-campaign hardening this cycle: `parameterised_grid`
IC injection + per-run co-activation counters + `kappa_seed` curve-spawn hook (SC-EDGE-05 now
determinate), the worn/particles/flip worlds + SC-FRONT-07 flip scenario, PERT timeouts → 40 s
(cover the first curve) + SC-PERT-07/08 onset moved into the curve, a `--train-config` fail-fast
guard and a GUI-reap fix in `run_campaign.py`, and a `--campaign-dir` arg on
`plot_camera_comparison.py`.

### Rationale

The per-SR verdicts were still scored on the superseded 139k oval policy; the thesis verdict
must come from the 297k E-main on its own circuit.

### Impact

**Global verdict (enforcement) `NOT SATISFIED`** — blocking SR-CL-A SR-001/002/003; SR-012/014
INCOMPLETE (documented D-29 exception, D-46). Two-sided finding: **in-ODD (NOM + PERT) the cage
is a safety asset** (0 road-edge, removes perception-degradation failures the bare policy
commits — PERT-04/09/11/12/13 enf PASS vs mon FAIL), but **out-of-ODD the camera cage cannot
recover** (125 enforcement road-edge contacts vs 0 in the 139k, all in SC-EDGE-02/05 +
SC-FRONT-01/03/04/06; D-43 common cause; F4→E PASS→FAIL flips). SC-EDGE-05 determinate (0.17),
SC-FRONT-07 flip PASS. Not a pure availability cost as the 139k was. Open: SC-PERT-03 (D-38),
multi-seed N=5 (host-deferred), figure caption strings ("v1/1660" → 297k/1940).

### Verification

`tools/check_traceability.py` PASS (0 warnings); `pytest policy/tests cage/tests` 462 passed.
Campaign roll-up reproducible via `tools/run_campaign.py … --out experiments/sim/campaign_e_297k`.

---

## [24.06.2026] — STPA SR-derivation table + control-structure diagram (folded into docs/02)

**Document(s) affected:** `docs/02_hazard_register.md` (SR-derivation table UCA→constraint→SR + Fig. STPA-CS reference, next to the per-block sweep); new `manuscript/figures/fig_stpa_control_structure.svg`.  
**Phase:** F1 safety analysis (STPA) — methodology documentation  
**Gate context:** none (derivation rationale; no H/SR/C/M changed, no verdict)  
**Author:** Samuel Sanchez  

### Change

Added, **in docs/02** (next to the per-block sweep), the bottom-up "SRs derived this way"
view requested as a thesis tool: a **UCA → safety-constraint → SR derivation table** tracing
every SR-001..014 to the block + UCA it answers, and the **control-structure block diagram**
(Fig. STPA-CS, `.svg`, in the style of the SE4ADS Ch.5 STPA slides). An interim standalone
`docs/15` was **consolidated into docs/02 and removed** to keep a single STPA home (the
analysis already lived in docs/02). Operationalises **D-27**.

### Rationale

Requested as a thesis tool ("the SRs were derived this way, per the four blocks, what could
fail"). Makes the bottom-up STPA reasoning auditable and the per-block coverage explicit
(controller/sensor fully derived; process/actuator execution-faults Phase-5).

### Verification

`python tools/check_traceability.py` → **All checks PASSED** (no registered IDs changed;
docs/02 references existing H/SR/C only).

---

## [24.06.2026] — STPA per-block completeness: actuator + process UCAs identified (Phase-5 deferred)

**Document(s) affected:** `docs/02_hazard_register.md` (STPA scope statement — new per-block control-structure sweep table; "Open hazards under consideration" — actuator execution-fault + process-disturbance entries).  
**Phase:** safety analysis (STPA) — coverage audit  
**Gate context:** none (hazard identification; no new *registered* H/SR/C, no verdict)  
**Author:** Samuel Sanchez  

### Change

Audited the hazard register against the four STPA control-structure blocks (controller /
sensor / process / actuator; SE4ADS ch.5 p.23–24, the four UCA types). Added an explicit
**per-block UCA sweep** table to the STPA scope statement, and registered two
previously-implicit UCAs under "Open hazards under consideration": **actuator command not
faithfully executed** (UCA *not given* / *unsafe given* at the actuator) and **process
disturbance / unmodelled dynamics** (low-friction skid).

### Rationale

The sweep showed controller and sensor blocks strongly covered (H-01/02/03/04/09;
H-06/10/11/12) but the **actuator** block only implicit (H-05 command-shaping + SC-PERT-02
latency) and the **process** block thin (H-08 stall only). Both new UCAs are deferred to
**Phase 5 (physical)**: the Gazebo DiffDrive actuator is faithful and the track is
flat/dry/controlled (ODD-1/2), so a control-level cage with no actuator feedback cannot
mitigate them in the sim verdict — mitigation is actuator-/platform-level. Mirrors the
existing Phase-5 "sensor calibration drift" entry.

### Verification

`python tools/check_traceability.py` → **All checks PASSED** (no registered IDs changed; the
`H-??` entries are under-consideration / Phase-5, outside the H/SR/C traceability chain).

---

## [24.06.2026] — GE4 indeterminate fix: SC-PERT-05 labelled criterion wired into the per-run verdict

**Document(s) affected:** code — `src/cobraflex_rl/cobraflex_rl/criterion_eval.py` (new `labelled_arms`), `scenario_perturbations.py` (`level_index`), `eval_policy.py` (labelled-arm selection); tests `policy/tests/test_criterion_eval.py` + `test_scenario_perturbations.py`. Docs: `docs/07` footnote ⁴.  
**Phase:** track 'E' (camera) — GE4 (eval) wiring  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Wired the two-arm `low:/high:` labelled per-run criterion so a single run is scored against
the arm matching its perturbation level: `eval_policy` now evaluates
`criterion_eval.labelled_arms(expr)[perturbation.level_index]` instead of hard-coding
`verdict = None`. `scenario_perturbations` records `level_index` (rep % n_levels) for the
multi-level types. Resolves GE4 open item (b) for **SC-PERT-05**.

### Rationale

SC-PERT-05 (low-light) was indeterminate (D-38 class) only because the labelled evaluator was
unwired — it has two arms with different specified outcomes (low: keep driving / SR-012;
high: controlled stop allowed / SR-013), one per level. Each rep runs one level, so the
matching arm is the correct per-run verdict.

### Impact

SC-PERT-05 will **score** (not indeterminate) on the 297k GE4 run — completing SR-012's
adverse evidence on the low arm and SR-013 on the high arm. **Still open** (separate, F-track
CL-B): SC-PERT-03 (finetune arms, not level-resolvable — grouped by the driver) and SC-EDGE-05
(parameterised_grid IC injection). No verdict change now (139k roll-up unchanged).

### Verification

`pytest` → **454 passed, 5 skipped** (incl. new `test_labelled_arms_order_and_level_arm_semantics`
+ `test_visual_degradation_level_index_round_robin`). Logic check: SC-PERT-05 rep0 → low arm
(a stop fails — `M-P2 == 1` required), rep1 → high arm (safe stop passes).

---

## [24.06.2026] — D-46: two-sided D-29 coverage for the camera SRs (SC-NOM-01 nominal anchor)

**Document(s) affected:** `docs/03_safety_requirements.md` (SR-012/013/014 Scenarios += SC-NOM-01) → `docs/data/safety_requirements.csv`; `docs/07_traceability_matrix.md` (matrix cells + footnote ⁶); `docs/DECISIONS.md` (D-46 + index + status note); `scenarios_complex_b/nominal/sc_nom_01.yaml` (`references_SR`).  
**Phase:** track 'E' (camera) — GE4 coverage  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Anchored the **D-29 nominal family** of the camera-stressor SRs (SR-012/013/014) on the
clean-input nominal run **SC-NOM-01** (the no-false-trigger / baseline-competence arm),
keeping the adverse family on the SC-PERT camera scenarios. Recorded as **D-46**;
SC-NOM-01's `references_SR` updated for bidirectional traceability.

### Rationale

The camera SRs were authored adverse-only → `nominal = 0` → INCOMPLETE under D-29. D-29's
nominal family is the **baseline arm of a two-sided test** (no-false-trigger + correct
response), not a "repeat the hazard under clean input" requirement; SC-NOM-01 is the genuine
no-false-positive control + competence baseline. Mirrors how SR-001 is covered
(SC-NOM-01/02 nominal + SC-EDGE-02 adverse). See D-46.

### Impact

`--dry-run` D-29 feasibility: SR-012/013/014 nominal **0 → 50**, adverse ≥ 25 → all three
**FEASIBLE** (GAP cleared). Combined with D-45 (SR-CL-A vetoes cleared) and SC-PERT-13
(SR-013 adverse), the camera SRs are now **coverage-ready**; the verdict is scored when the
297k GE4 campaign runs. No verdict change now (coverage/plan, not evidence).

### Verification

`python tools/sync_safety_requirements.py` → 14 SRs. `python tools/check_traceability.py`
→ **All checks PASSED, 0 warnings**. `run_campaign --dry-run` on `scenarios_complex_b`:
SR-012/013/014 `[OK]`, families nominal = 50 / adverse = 40.

---

## [24.06.2026] — Track-'E' degraded-markings scenarios SC-PERT-11/12/13 + scenario↔SR traceability

**Document(s) affected:** `docs/03_safety_requirements.md` (SR-012/013/014 Scenarios column) → `docs/data/safety_requirements.csv` (regenerated via `sync_safety_requirements.py`); `docs/07_traceability_matrix.md` (SR-012/013/014 Scenario cells + new footnote ⁶). New artefacts: `scenarios_complex_b/perturbed/sc_pert_{11,12,13}.yaml`; `scripts/generate_complex_track.py` (line toggles + arc-length erase); `experiments/sim/tracks/complex_b/complex_b_gaps.png` + `src/cobraflex/materials/road_assets/tracks/complex_b_gaps.png`; `src/cobraflex/worlds/lane_following_complex_b_gaps.world`.  
**Phase:** track 'E' (camera) — GE4 scenario library  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Added three complex_b camera scenarios for **degraded lane markings**, a face of H-10
admitted in-ODD by ODD-2 §5.4 ("lane markings may be partially degraded or faded along
arbitrary segments"): **SC-PERT-11** worn/segmented markings (world-variant — the
`generate_complex_track.py` line-erase renders `complex_b_gaps.png`, lane paint removed
over arc-length patches s≈2.5–6.5; new `lane_following_complex_b_gaps.world`),
**SC-PERT-12** camera image degradation (glare injector on normal markings — matched
control), **SC-PERT-13** both compounded. All complex_b-native (start_s_m = 2.0, the run
traverses the degraded zone), criterion per **D-45** (`M-S1 < 0.16 AND road_edge_contact
== False`). Wired the scenario↔SR traceability: SR-012 / SR-014 ← SC-PERT-11/12/13,
SR-013 ← SC-PERT-13, in both the docs/03 SR register (→ CSV) and the docs/07 matrix.

### Rationale

No new SR/hazard needed: worn/missing markings degrade the lane cue → it is the
infrastructure face of **H-10 / SR-012** (with SR-013 loss and SR-014 suspect-estimate as
the severity-dependent fall-backs), the twin of the SC-PERT-09/10 worn/wet world variants.
The combined SC-PERT-13 additionally gives **SR-013 a second adverse scenario**, closing
its adverse-side D-29 gap.

### Impact

`--dry-run` D-29 feasibility: SR-013 adverse family **0 → 40** (SC-PERT-13); SR-012/014
adverse families stay ≥ 25. The three camera SRs now have **adverse coverage met**; the
residual gap is **nominal = 0** (separate — the clean-input SC-NOM-01 anchor, Option 1).
Scenarios **not yet run** — no verdict change; scored when the 297k GE4 campaign runs.
Matrix grows 1660 → 1880 runs (seed 2024). check_traceability **PASS**.

### Verification

`python tools/sync_safety_requirements.py` → 14 SRs written. `python
tools/check_traceability.py` → **All checks PASSED, 0 warnings**. `run_campaign --dry-run`
on `scenarios_complex_b` loads 27 scenarios, builds the matrix, SR-013 adverse = 40.
Variant texture verified pixel-aligned to the base (only the erased patches differ).

---

## [24.06.2026] — D-45: controlled safe stop scored as pass on the SR limit predicate (camera GE4 criteria)

**Document(s) affected:** `scenarios_complex_b/` per-run criteria — `edge/sc_edge_02`, `edge/sc_edge_03`, `perturbed/sc_pert_01`, `perturbed/sc_pert_02`, `perturbed/sc_pert_04`, `perturbed/sc_pert_06`, `perturbed/sc_pert_09`, `perturbed/sc_pert_10`; `docs/DECISIONS.md` (new **D-45** + index + status note); `scenarios_complex_b/README.md` (new "Verdict scoring" section).  
**Phase:** track 'E' (camera) — GE4 (eval) scoring  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Dropped the `emergency == False` clause from the per-run pass criterion of the **eight
adverse safety scenarios** in the complex_b camera library, so a cage-commanded
**controlled safe stop scores as a pass** whenever the SR's safety limit held
(`M-S1 < 0.16`, plus `road_edge_contact == False` where present). A real breach
(`M-S1 >= d_max` / road-edge) still fails. Recorded the rule as decision **D-45**.
SC-PERT-07 (SR-013, stop *required*: `emergency == True`) and the nominal scenarios
(gated by `M-P2 == 1`) are unchanged; the frozen oval `scenarios/` + 139k evidence
are untouched.

### Rationale

Under the camera (D-41/D-43) the cage flips latent→active in-ODD: a controlled stop is
the safety mechanism working, not a breach. The original clause scored those safe stops
as fails (139k: 13/13 SC-EDGE-02 + 20/20 SC-PERT-04 enforcement fails were emergency-only,
with `M-S1 < d_max` and 0 road-edge contacts) — an **availability** cost mis-scored as a
**safety** failure. The thesis verdict is a safety verdict (D-28/D-30). Full argument and
alternatives in D-45.

### Impact

Clears the three SR-CL-A vetoes behind the 139k `NOT SATISFIED` (SR-001, SR-012, SR-014).
**Not sufficient for `SATISFIED`**: SR-013 stays INCOMPLETE (D-29 family coverage —
adverse-only SC-PERT-07) and the indeterminates persist (SC-PERT-05 labelled criterion
unwired; SC-EDGE-05 grid ICs not injected). Applies when the 297k GE4 campaign is run on
`scenarios_complex_b`; `docs/07` + Ch.8 §8.9 E-track verdicts to be re-pointed 139k→297k
at that time. No H/SR/C/M identifier changed (per-run criterion strings only;
`references_SR` untouched).

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (criteria edits
touch no IDs). `python -m pytest -q` → **452 passed, 5 skipped**. Direct evaluation of the
eight edited criteria via `run_campaign.evaluate_criterion`: a safe stop with limits held →
pass, a real breach → fail, drove-fine → pass; SC-PERT-07 confirmed unchanged (no-stop →
fail). The 24 complex_b YAMLs parse (`load_scenarios`).

---

## [24.06.2026] — Root README pivoted to track 'E' (camera) primary; F kept as baseline

**Document(s) affected:** `README.md` (intro framing, "Results at a glance" rewritten to the `complex_b` 297 k camera E-main + `_newcam` figures, track-'E' status note, "RL policy" pillar, GIF captions, how-to-read pointer to `docs/11`).  
**Phase:** track 'E' (camera) — public-facing consolidation  
**Gate context:** none (front-page narrative; no H/SR/C/M touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Brought the repository's front page in line with the manuscript pivot: the **end-to-end
camera** policy (E-main `complex_b` 297 k) is now the headline result (beats the CV baseline
on tracking, 10.9 vs 17.2 mm, 0 emergencies, cage latent), with the **state-vector track 'F'**
(oval, 11.2 laps / 9.9 mm vs PD 23 mm, G4-`SATISFIED`) kept explicitly as the frozen baseline /
control arm. Results figures swapped to the `_newcam` set; GIF captions labelled as the
state-vector baseline demo; added the honest scope note (nominal eval done; GE4-on-297k pending).

### Verification

Referenced `_newcam` figures exist; the only residual F-track numbers are the labelled baseline
mention. `tools/check_traceability.py` → PASS (no identifiers touched).

---

## [24.06.2026] — Seed 42 nominal eval done (enforcement) → multi-seed table row filled, basin confirmed

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.5.3 — seed-42 eval columns filled + reading). Evidence: `experiments/sim/runs/rl_newcam_eval_42_cb125k_4k4/` (synced from Ubuntu).  
**Phase:** track 'E' (camera) — multi-seed (GE3)  
**Gate context:** none  
**Author:** Samuel Sanchez  

### Change

Seed 42 evaluated on SC-NOM-01 (enforcement, complex_b, checkpoint hash `bc7e3d17…`):
**4,91 laps, mean |ey| 13,3 mm, max 41,6 mm, 0 emergencies, 64,9 % interventions (C-06
only)**. Filled the §7.5.3 multi-seed table row and added the 2024-vs-42 reading.

### Rationale / Impact

Confirms seed 42 is **constraint-respecting** (cage latent in safety — 0 emergencies, no
C-01/C-03/C-05) and **beats the CV baseline** on tracking (13,3 vs 17,2 mm), like 2024. The
only seed difference is **smoothness**: 42 runs 64,9 % C-06 vs 2024's 43,5 % (jerkier,
consistent with its lower/earlier peak). So the constraint-respecting basin is **stable
across the two seeds** in what matters for safety; only the benign C-06 rate-limiting cost
varies. Monitoring arm for 42 also done (4,90 laps, |ey| 16,5 mm, 0 emerg, 68 % C-06): the
enforcement↔monitoring contrast shows C-06 contributes ~3 mm of tracking to this jerkier
seed (mon 16,5 mm → enf 13,3 mm; near the CV's 17,2 without it), while staying safety-latent
(no C-01/C-03/C-05 either mode). Seeds 23/666/123 still TBD. No verdict changed.

### Verification

Checkpoint hash in the eval metadata (`bc7e3d17…`) matches the rescued seed-42 peak
(`num_timesteps == 124928`). `tools/check_traceability.py` → PASS.

---

## [23.06.2026] — Track-'E' multi-seed comparison started (seed 42 added; table + figure prepared for N=5)

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.5.3 — new E-track multi-seed table; §7.2.7 — "2 of 5 done"). New: `manuscript/figures/fig_7_8_multiseed_newcam.png`; `experiments/sim/training/ppo_newcam_complex_b_42/checkpoints_peak/cobraflex_ppo_newcam_complex_b_42_125k_peak.zip` + augmented `…/ppo_newcam_complex_b_42/metadata.json` (peak block).  
**Phase:** track 'E' (camera) — multi-seed (GE3)  
**Gate context:** none (training-side comparison; no H/SR/C/M touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Second camera seed (**42**) trained on complex_b; like seed 2024 it collapses late
(by ~410k) by exploration contraction → **checkpoint-on-peak** (`ep_rew_mean` 720,2
@ ~120k; rescued checkpoint `num_timesteps == 124928`, hash `bc7e3d17…`, placed in
its `checkpoints_peak/`; metadata augmented with the peak block). Built the **E-track
multi-seed table** in §7.5.3 on the F-track battery {2024, 42, 23, 666, 123}: seed 2024
fully filled (training + nominal eval), seed 42 training-side filled with **eval columns
TBD** (Gazebo), seeds 23/666/123 TBD. Generated the E-track multi-seed figure (Fig. 7.8,
`_newcam`) from the two seeds' learning curves cropped to their healthy regions
(2024 ≤450k, 42 ≤400k). The F-track multi-seed table/figure are kept as the baseline.

### Rationale

User ran seed 42 and asked for the F-track-style seed comparison with the table prepared
ahead of the remaining 3 seeds. Both camera seeds crashing late corroborates that the
camera-PPO instability is **seed-general** (a track finding, §7.4.3), not a 2024 fluke.

### Impact

Training-side only: peak height/timing vary by seed (2024: 822,9 @ ~297k; 42: 720,2 @
~120k); both are **constraint-respecting in safety during training** (C-01/C-03 ≈ 0, only
C-06). Seed 42's basin is **tentative pending its eval**. Remaining (Ubuntu): nominal evals
for seed 42 + seeds 23/666/123, then complete the table. No verdict changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** Figure via
`tools/plot_f3_figures.py --seed-runs` on truncated copies; seed-42 peak verified
(`num_timesteps == 124928`, seed 42).

---

## [22.06.2026] — GE4-on-297k campaign wiring (host-independent prep) + complex_b scenario scaffold

**Document(s) affected:** `tools/run_campaign.py` (new `--model-path`, `--scenario-dir`; `resolve_config_path`; `execute_run` now passes `centerline`/`road_centerline`/`world_name` from each scenario's `track`), `src/cobraflex_rl/launch/eval_scenario_batch.launch.py` (new `centerline`/`road_centerline`/`world_name` launch args → eval_policy). New: `scenarios_complex_b/` (24 scenario drafts + README). `tools/plot_f3_figures.py` was extended earlier the same day.  
**Phase:** track 'E' (camera) — pre-GE4 readiness  
**Gate context:** none (campaign tooling + draft scenarios; no H/SR/C/M identifiers touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Did the **host-independent** prep to run the GE4 campaign on the complex_b 297k E-main.
The campaign launch path now plumbs complex_b geometry end-to-end (it previously passed
only `world`, leaving eval_policy on the oval centerline with no road-centerline/world_name).
Added `--model-path` (point at the gitignored 297k peak) and `--scenario-dir` (select a
scenario set). Scaffolded `scenarios_complex_b/` — the 24 scenarios with their `track`
block re-pointed to complex_b (world, world_name, complex_b centerlines), **ICs copied
from the oval and loudly flagged as needing validation** (start_s_m semantics,
`straight_completed`/timeout, perturbation timing; SC-PERT-09/10 have no complex_b wet/worn
world). The **oval `scenarios/` set is untouched** (frozen F4 / 139k evidence).

### Rationale

User: "do everything you can here; I'll switch to Ubuntu later." The policy + 297k checkpoint
+ nominal eval were ready, but the campaign was built for the oval and the 297k is a complex_b
policy — so the launch plumbing, checkpoint flag, and a complex_b scenario set were the
blockers reachable from the Windows host.

### Impact

`--dry-run` against `scenarios_complex_b` builds the **1660-run** matrix and the D-29
feasibility cleanly; SR-012/013/014 show the **same** coverage GAPs as the 139k campaign
(SC-PERT-07/08/09/10 at 20<25 runs/family — pre-existing, not new). **Remaining for Ubuntu:**
validate/adapt the per-scenario ICs for complex_b geometry, provide complex_b wet/worn worlds
(SC-PERT-09/10), then run. No campaign verdict changed (still the 139k in docs/07 + §8.9).

### Verification

`python -m py_compile` on `run_campaign.py` + `eval_scenario_batch.launch.py` (OK);
`run_campaign.py --scenario-dir scenarios_complex_b --dry-run` builds the matrix (1660) +
feasibility; `python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [22.06.2026] — Manuscript pivot: track 'E' (camera) made primary, track 'F' kept as baseline; ch.7 rewritten + E figures

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (full rewrite → E-primary, F baseline, §7.7 folded into the body, complex_b 297k results in the §7.2–7.6 structure), `chapter_01_introduction.md` (§1.6.3 scope/abstractions → perception in scope, two geometries), `chapter_03_methodology.md` (§3.5.1 D-41 framed as primary; **D-42→D-43** fix), `chapter_04_safety_analysis_and_requirements.md` ("track paralelo" → primary), `docs/00_v_model_adapted.md` ("Track 'E' (primary)" reframe + staleness fix: D-42→D-43, H-12, SR-014, SC list, commit prefix), `docs/09_environment_design.md` (track-framing note). New: `manuscript/figures/fig_7_1..7_6_*_newcam.png` (E-track figures).  
**Phase:** track 'E' (camera) — manuscript consolidation  
**Gate context:** none (narrative framing; no H/SR/C/M identifiers touched; no campaign verdict changed)  
**Author:** Samuel Sanchez  

### Change

Pivoted the manuscript/docs so the **end-to-end camera track 'E'** (E-main complex_b
297k) is the **primary** narrative, with the **state-vector track 'F'** kept as the
explicit **baseline / control arm** (not deleted). Chapter 7 was fully rewritten into
an E-primary chapter (camera observation, the v3 stability stack, the complex_b 297k
convergence + nominal eval vs the CV baseline) keeping the same §7.2–7.6 figure/table
structure; §7.7 was folded into the body. Generated six E-track figures from the
complex_b run + eval (`_newcam` suffix); the F-track figures are retained for the
baseline subsections. **Training figures were cropped to ≤450k** (the run collapses by
exploration after ~450k; the post-450k tail is irrelevant to the peak-297k deployed
policy and is omitted from the figures, with an honest prose note + checkpoint-on-peak
rationale). Also fixed a stale **D-42→D-43** reference in ch.3 and docs/00, and
completed docs/00's E hazard/SR/scenario lists (H-12, SR-014, SC-PERT-04..10).

### Rationale

The user's directive: track 'E' is the system of record going forward; 'F' will be
**superseded by 'E' once the GE4 camera campaign runs** (the camera eval to date is
nominal, §8.9). Centring the camera track makes the thesis reflect the actual final
system while the state-vector baseline isolates the cost of perception (E↔F delta).

### Impact

**No campaign verdict changed.** The GE4 per-SR verdicts (ch.8 §8.9, docs/07) remain the
139k campaign's — flipping them awaits the GE4 re-run on 297k (group 'C', deferred per the
"F superseded in the future" premise). The **case-study framing** in ch.1 (§1.2 nivel
concreto, OE4, A3) was reframed E-primary (group 'B', applied). The **hypothesis (§1.3
H1–H3)** and the methodological contributions (A1/A2/A4/A5) are **track-agnostic and
unchanged** — this is a methodology thesis, so its core claims do not depend on the
observation track. Shared content (ODD, hazards H-01..09, methodology) unchanged.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** Figures
regenerated via `tools/plot_f3_figures.py` on the truncated (≤450k) complex_b run. The
generator was extended (backward-compatible): `--centerline` (Fig 7.5 draws the complex_b
centerline, not the oval), `--cv-run` + cumulative arc length (Fig 7.6 RL-vs-CV with no
per-lap-`s` seam artifact), and `--track-name`.

---

## [22.06.2026] — complex_b 297k SC-NOM-01 eval done → new E-main camera policy of record

**Document(s) affected:** `docs/11_camera_rl_training.md` (header → v0.4; §8 rewritten — complex_b 297k is the E-main, 425k/139k demoted to §8.3 predecessors; eval results + RL-vs-CV table in §8.2), `docs/07_traceability_matrix.md` ("Last update" + a "policy superseded" callout on the E-track evidence block), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.9 superseded-policy callout, §8.9.4 closure item (e), §8.9.5 RL-vs-CV head-to-head closed), `CLAUDE.md` (new E-main bullet + banner 425k→297k), `experiments/sim/runs/baseline_cv_vs_rl_nominal.json` (RL complex_b arm + finding_complex_b).  
**Phase:** track 'E' (camera) — GE3 / pre-GE4  
**Gate context:** none (nominal eval evidence + state-of-record update; no H/SR/C/M touched; no campaign verdict changed)  
**Author:** Samuel Sanchez  

### Change

Ran and analysed the first SC-NOM-01 eval of the complex_b 297k peak (enforcement +
monitoring), and promoted it to the **E-main camera policy of record**, superseding the
oval 425k peak and the 139k campaign policy. Eval (seed 2024, 4400 steps, DR off,
complex_b): enforcement `rl_newcam_eval_2024_cb297k_4k4` = **4.88 laps, mean |ey| 10.9 mm,
0 emergencies, 43.5 % C-06-only**; monitoring `…_mon` = 4.89 laps, 12.9 mm, 0 emergencies.
Cage **latent in-ODD** in both modes (no C-01/02/03/05). Head-to-head on the **same track**
vs the CV baseline (`cv_ctrl_eval_newcam_4k4`, 17.2 mm): the RL agent is ≈ 37 % tighter on
mean |ey| — closing the previously-pending RL-vs-CV contrast.

### Rationale

This is the final camera state ("este es el estado final de la cámara y la anterior no").
The 297k peak predates the run's late-run exploration collapse, so the "failed" training
did not contaminate it; the eval confirms a competent in-ODD policy that beats the classical
CV baseline on the hard circuit (reversing the oval finding, where CV was more accurate) and
restores the F-track latent-cage signature (the 139k curve-apex controlled stop is gone).

### Impact

`docs/11` §8, `CLAUDE.md` status and `baseline_cv_vs_rl_nominal.json` now read 297k as the
E-main. **The GE4 per-SR verdicts are unchanged**: the 1660-run campaign in `docs/07` + ch.8
§8.9 + `experiments/sim/campaign_e/` still scores the **superseded 139k** policy — a nominal
eval is not a campaign, so no SR verdict or global `NOT SATISFIED` was rewritten. Re-running
GE4 on 297k is the open closure step (ch.8 §8.9.4 item (e); docs/07 callout). Laps are not
comparable across tracks (complex_b 19.22 m vs oval 8.79 m); the same-track CV row is the only
fair lap comparison.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** `baseline_cv_vs_rl_nominal.json`
re-validated as well-formed JSON. (No hazard/SR/cage/scenario/metric identifiers were touched.)

---

## [22.06.2026] — complex_b 1M run: 297k peak rescued, run-record reconstructed, SC-NOM-01 eval prepared

**Document(s) affected:** `docs/11_camera_rl_training.md` (header → v0.3; new §8.1 "The complex_b 1M run, 297k peak"). New artifacts: `experiments/sim/training/ppo_newcam_complex_b_2024_1M/metadata.json` (reconstructed run-record) and `…/checkpoints_peak/cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` (canonical peak, gitignored).  
**Phase:** track 'E' (camera) — GE3 training / pre-GE4  
**Gate context:** none yet (training artifact + eval prep; no verdict, no H/SR/C/M touched)  
**Author:** Samuel Sanchez  

### Change

The `ppo_newcam_complex_b_2024_1M` camera run (seed 2024, `CnnPolicy`, complex_b
circuit, v3 stability stack) was stopped manually at ≈ 662k of the 1M plan after
late-run reward decay. Generated the **missing run-record** `metadata.json`
(reconstructed post-hoc from `learning_curve.csv` + the rescued checkpoint — the
interrupted run never fired the trainer's end-of-run writer): reproducibility pins
(git commit, cage/centerline hashes, checkpoint hash `44c8e912…`, seed,
hyperparameters), `status: interrupted`, and the checkpoint-on-peak metadata
(`ep_rew_mean ≈ 822.9 @ ≈ 297k`, `ep_len ≈ 791`). Placed the operator-rescued
peak as the canonical `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` inside
the gitignored `experiments/sim/training/ppo_newcam_complex_b_2024_1M/checkpoints_peak/`
(peak verified: `num_timesteps == 296960` in the zip). Documented the run in
docs/11 §8.1 with the concrete SC-NOM-01 eval command (enforcement + monitoring).

### Rationale

The run produced the highest camera reward yet (822.9, vs oval 425k's 335.6) but
died after the peak, so the peak must be evaluated before it can be trusted — the
user's "a ver si aunque haya fallado ese checkpoint vale". The run-record and a
traceably-named, gitignored peak are prerequisites for that eval and for the
CLAUDE.md reproducibility-metadata rule. Reward is **not** comparable across
tracks (different perimeter/geometry/reward integral), so §8.1 explicitly defers
the usability question to the eval.

### Impact

No verdict change. `docs/07`, Ch.8 §8.9 and `experiments/sim/campaign_e/` are
untouched and still report the 139k campaign — the complex_b peak is a **candidate**
pending a first nominal eval, which must run on Ubuntu 24.04 + ROS2 Jazzy + Gazebo
(it cannot be launched from the Windows authoring host). Hygiene note: the original
top-level `experiments/sim/cobraflex_ppo_lane_newcam_2024_peak.zip` (20 MB) is
**git-tracked** (committed in `24f7811f`) because `experiments/sim/*.zip` is not
ignored; the canonical copy now lives in the gitignored `checkpoints_peak/` dir, so
the top-level one can be `git rm --cached`-ed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** (No
hazard/SR/cage/scenario/metric identifiers were touched.)

---

## [20.06.2026] — Isaac positioned in the V-Model A5 as a higher-fidelity sim-to-real bridge (Gazebo stays the verdict environment)

**Document(s) affected:** `docs/00_v_model_adapted.md` (A5 + chapter-mapping table + date), `docs/DECISIONS.md` (D-44 "Validation positioning" note), `manuscript/chapters/chapter_01_introduction.md` (outline §1.7 Ch.9 + contribution A4), `manuscript/chapters/chapter_06_implementation.md` (§6.7 transition), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.8 sim-to-real limitation). Earlier same-day: `CLAUDE.md` (phase-status axes banner), `docs/11`/`docs/13` (positioning notes + DR section + command reference), broken doc-13 link fixes.
**Phase:** track 'E' / methodology (Isaac Sim platform)
**Gate context:** none (planning/methodology framing; no H/SR/C/M identifiers touched)
**Author:** Samuel Sanchez

### Change

Updated the planning/methodology documents so the *evolving* thesis plan reflects Isaac
Sim's real role. Adaptation **A5** (Bounded Operational Validation) is re-stated as a
**graded sequence of increasing-fidelity environments**: In-simulation Validation (**Gazebo**,
the primary verdict-bearing environment, reported as *provisional principal evidence*) → a
**high-fidelity simulation bridge (Isaac Sim**, PhysX + RTX, D-44) as an intermediate rung
aimed at narrowing the sim-to-real gap → Bounded Physical Validation. The chapter-mapping
table gains an Isaac row; Ch.1 (Ch.9 outline + contribution A4), Ch.6 §6.7 and Ch.8 §8.8 carry
the same framing; D-44 gains a "Validation positioning" note.

### Rationale

The work-plan drifted: Isaac entered (D-44) but the manuscript/methodology still described a
single Gazebo→physical jump, conflating the **observation track** (F/E) and **simulator**
(Gazebo/Isaac) axes. The author's decision (2026-06-20): Gazebo is the principal objective and
carries the *provisional* verdict; Isaac is a more powerful tool toward the sim-to-real gap,
kept as **internal evidence** for now (a Gazebo checkpoint does not transfer to Isaac → an
Isaac campaign is a retrain/re-eval from scratch). If the Isaac campaign matures into the
stronger result, the thesis is re-stated with those figures as final.

### Impact

No identifiers, scenarios, metrics or cage parameters change; no campaign re-runs implied. The
E-track verdict still closes in Gazebo (docs/07, Ch.8 §8.9, `experiments/sim/campaign_e/`).
Isaac evidence, when produced, is recorded for internal valuation, not as the thesis verdict.

### Verification

`tools/check_traceability.py` → **All checks PASSED, 0 warnings** (planning-prose edits only).

---

## [19.06.2026] — In-process Isaac-Sim RL training path (D-44), decoupled from the bring-up

**Document(s) affected:** `tools/isaac_scene.py` (new), `tools/isaac_train.py` (new), `tools/isaac_ros2_bringup.py` (refactored), `src/cobraflex_rl/cobraflex_rl/isaac_interface.py` (new), `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (import decouple), `docs/13_isaacsim_urdf_import.md` (retitled "Isaac Sim utilities" + in-process training section), `docs/14_isaacsim_handover_spec.md` (§3), `docs/DECISIONS.md` (D-44), `CLAUDE.md` (doc-13 label)
**Phase:** track 'E' / F-track tooling (Isaac Sim platform)
**Gate context:** none (RL training enablement; no H/SR/C/M identifiers touched)
**Author:** Samuel Sanchez

### Change

Added the **in-process** Isaac-Sim RL training path (option 2 of the Gazebo→Isaac
migration), and decoupled it from the ROS2 bring-up command:

1. **`tools/isaac_scene.py`** (new) — the shared physics scene builder (URDF→USD import,
   generated track geometry, robot spawn, wheel velocity drives + low-friction
   wheel/ground materials) extracted from the bring-up. Single source of the drivetrain
   constants (`WHEEL_RADIUS`/`WHEEL_SEPARATION`/`WHEEL_JOINTS` order, `WHEEL_SCRIPT`) and
   the Lane Cam spec. All `omni`/`pxr` imports are deferred into functions so importing
   the module is safe before `SimulationApp` exists.
2. **`tools/isaac_ros2_bringup.py`** — refactored to import the scene from `isaac_scene`;
   keeps only the ROS2-bridge graph, sensor publish graphs and the free-run loop. `build_scene`
   is now `build_world()` + `add_sensors()`. Observed behaviour unchanged.
3. **`isaac_interface.py`** (new) — `IsaacSimInterface` duck-types the surface
   `GazeboLaneEnv` calls but drives the live Isaac `World` directly: per-episode reset =
   `set_world_pose` + zeroed velocities; actuation = wheel `ArticulationAction`; advance =
   `world.step()`; pose/speed from the articulation root (ground truth); Lane Cam via a
   Replicator `rgb` render product (RGBA→BGR).
4. **`isaac_train.py`** (new) — entry point: `SimulationApp` → shared scene (no ROS bridge)
   → Lane Cam render product → `IsaacSimInterface` → `GazeboLaneEnv` → SB3 PPO. Reuses the
   existing `config/train_ppo*.yaml`, callbacks and reproducibility metadata
   (`platform: sim-isaac`).
5. **`gazebo_lane_env.py`** — the lone hard `rclpy` coupling (the `RosGazeboInterface` type
   import) moved under `TYPE_CHECKING`, so the env imports on the Isaac host without `rclpy`.

### Rationale

RL training's `reset()` teleports every episode via `gz service set_pose` (Gazebo-only);
the bring-up exposes no Isaac equivalent, so training could not respawn episodes against
it. Driving the gym env in-process against the `World` removes the blocker, is the standard
Isaac-Lab-style pattern (no ROS↔gz bridge, no `gz` CLI per reset), and lets training and the
bring-up evolve independently. Sharing the scene keeps the trained-policy kinematics
identical to the deployment/demo path. See D-44.

### Impact

No hazard/SR/scenario/metric tables touched; `experiments/` and `docs/07` unchanged. The
GE4 425k re-run (CLAUDE.md §8.9, host-deferred) can now train/eval on Isaac via this path
once host-validated. The bring-up's cached `isaac_usd/` is still stale (ZED stereo switch)
— re-import with `BRINGUP_REIMPORT=1` on first Isaac run.

### Verification

`python -m py_compile` passes on all four new/edited Python files; an rclpy-stubbed import
check confirms `cobraflex_rl.gazebo_lane_env` no longer pulls `rclpy` (it now fails only on
the absent `gymnasium`, not on `rclpy`). **Not yet run on Isaac** — this host is Windows
(no Isaac); the live `world.step`/`set_world_pose`/Replicator flow and SB3-in-Isaac-python
are deferred to the Ubuntu + Isaac host. `tools/check_traceability.py` unaffected (no
identifier changes).

---

## [19.06.2026] — Isaac bring-up synced to the ZED Mini stereo pair (+ obsolete-frame cleanup)

**Document(s) affected:** `tools/isaac_ros2_bringup.py`, `tools/isaac_import_check.py`, `src/cobraflex/urdf/cobraflex_isaac.urdf` (regenerated), `docs/13_isaacsim_urdf_import.md`, `docs/14_isaacsim_handover_spec.md`
**Phase:** track 'E' tooling (Isaac Sim platform)
**Gate context:** none (auxiliary platform tooling)
**Author:** Samuel Sanchez

### Change

The Gazebo robot's front camera became a **ZED Mini stereo pair** (commit
`412e2a1f`, `zedm_left_camera_frame` / `zedm_right_camera_frame`, topics
`camera/{left,right}/{image_raw,camera_info}`), and the Lane Cam's info topic
moved to `camera/camera_info`. The Isaac path still wired the **old mono ZED**
(`camera_link_optical` → `camera/image_raw`). Brought it in line:

1. **`isaac_ros2_bringup.py`** — `CAMERAS` now publishes the ZED stereo pair on
   the `zedm_*_camera_frame_optical` frames + the Lane Cam on `camera/camera_info`,
   matching `robot.gazebo` / `config/gz_bridge.yaml`. New `BRINGUP_ZED=0` drops the
   (non-RL) stereo pair to halve camera render cost; `BRINGUP_REIMPORT=1` forces a
   URDF→USD re-import so the stale cached `isaac_usd/` is not silently reused.
2. **`cobraflex_isaac.urdf`** — regenerated camera section: old `camera_link` /
   `camera_link_optical` replaced by the zed-macro expansion (`zedm_camera_link`
   → `zedm_camera_center` → `zedm_{left,right}_camera_frame` + opticals). 13→17
   links, 12→16 joints.
3. **`isaac_import_check.py`** — `EXPECTED_LINKS` updated to the 17-frame set;
   frame-count message de-hardcoded.
4. **docs/13, docs/14** — sensor/topic/frame tables updated; empirical "Verified"
   blocks caveated as the pre-stereo (mono) import.

### Rationale

The Isaac bring-up's contract is "same ROS2 nodes as Gazebo, unchanged." After the
stereo switch the Isaac camera frames/topics no longer matched Gazebo or the bridge,
so any node (or RViz) keyed to the new names saw nothing on the Isaac side. The
generated Isaac URDF and the import smoke-test still referenced the deleted mono
frames — orphaned artifacts that would fail the import check.

### Impact

`cobraflex_isaac.urdf` was regenerated **by hand** on the Windows host (the canonical
`tools/build_isaac_urdf.py` needs `xacro` + a sourced ROS2 workspace, i.e. Ubuntu);
re-run it on the Ubuntu host for the byte-canonical file. The committed
`src/cobraflex/urdf/isaac_usd/` USD package is from the mono URDF and is now **stale**
— re-import on the Isaac host (`BRINGUP_REIMPORT=1` or delete `isaac_usd/`) before the
bring-up shows the ZED frames. No H/SR/C/SC/M identifiers touched. Lane-cam info topic
rename is safe: no RL/CV consumer subscribes to it (they read `camera/image_raw_lane`;
`lane_keeper_node` publishes its own `/lane/camera_info`).

### Verification

URDF re-validated (Python ElementTree): well-formed, single root `base_footprint`,
17 links / 16 joints, 4 continuous wheel joints, 6 `zedm_*` frames, every joint
parent/child resolves. `tools/check_traceability.py` unaffected (no ID changes).
Isaac-side runtime (import check + live `ros2 topic list`) is **deferred to the Ubuntu
+ Isaac host** — not runnable on this Windows machine.

---

## [19.06.2026] — CV baseline re-run on complex_b + Lane Cam (authoritative); PolylineTracker lap-seam fix

**Document(s) affected:** `docs/12_cv_lane_keeper.md` (v0.4), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.9.5), `experiments/sim/runs/cv_ctrl_eval_newcam_4k4/summary.json`, `experiments/sim/runs/baseline_cv_vs_rl_nominal.json`, `src/cobraflex_rl/cobraflex_rl/polyline_tracker.py`, `policy/tests/test_polyline_tracker.py`
**Phase:** Track 'E' (camera) — GE4 baseline
**Gate context:** before GE4 (425k) re-run
**Author:** Samuel Sanchez

### Change

The CV control baseline was re-evaluated on the **complex_b** circuit with the **Lane
Cam** (IMX219-160, 640×360) — the track + camera the RL camera agent will be scored on
— and is now **the** authoritative control reference for the RL agent. All earlier oval
CV results (`cv_ctrl_eval_2024_4k4{,_mon}`) are **superseded**. Authoritative numbers
(SC-NOM-01, seed 2024, 0.2 m/s, enforcement, run `cv_ctrl_eval_newcam_4k4`):
**4.85 laps, mean |ey| 17.2 mm, max |ey| 57.3 mm (< d_max=160), mean |epsi| 0.025 rad,
0 emergencies, 0.09 % cage intervention (4× C-02).**

Fixed a `PolylineTracker` lap-seam bug: a closed circuit whose generator left the seam
point un-duplicated (complex_b right-lane: first–last gap 0.060 m vs 0.052 m mean
segment) was mis-detected as *open*, so the stateful nearest-segment search could not
wrap at the start/finish line and `ey` exploded from lap 2 on. The tracker now
auto-closes loops whose endpoints sit within ~one segment; regression tests added.

### Rationale

The new-cam run's original `summary.json` reported 1.68 m mean |ey| and 1.73 laps — a
scoring artifact, not a controller failure: the CV-perceived error (`cv_ey`) stayed at
~14 mm throughout and true nearest-distance-to-centreline (recomputed from logged pose)
was 2–42 mm. The cause was the lap-seam wrap bug above. Writing the artifact numbers
into the thesis as the baseline would have been wrong.

### Impact

The eval was **re-run live** on complex_b with the fixed tracker in place (headless,
seed 2024, 0.2 m/s); the native `summary.json` (laps 4.847, mean |ey| 17.25 mm, max
57.3 mm, 0 emergencies, 0 % cage) matches an offline re-derivation from the pre-fix
logged pose to 4 decimals — the canonical `cv_ctrl_eval_newcam_4k4/` now holds this
clean run. The F-track oval is exactly closed (gap 0) and **unaffected**: F4 results
stand. The RL-vs-CV head-to-head on complex_b is **pending** the RL camera eval on the
same track (prepared + dry-run-validated, not yet launched). Full pytest: 457 passed.

### Verification

`python3 -m pytest -q` → 457 passed (incl. 3 new tracker regression tests). Live re-run
(`ros2 launch cobraflex_rl eval_cv_controller.launch.py`, complex_b) reproduces the
metrics; cross-checked against stateless global point-to-segment projection.

---

## [18.06.2026] — CV baseline: pure-pursuit control + monocular curvature boundary; complex_b softened to an "M"

**Document(s) affected:** docs/12 (§3, §4.5, §4.7 new, version log); `scripts/generate_complex_track.py`; `src/cobraflex_rl/config/complex_b_centerline.yaml` + `complex_b_right_lane_centerline.yaml`; `experiments/sim/tracks/complex_b/*`; `cv_lane_controller.py`, `cv_lane_estimator.py`, `gazebo_lane_env.py`, `eval_*`; `policy/tests/test_cv_lane_estimator.py`.
**Phase:** E (track 'E', GE4 prep)
**Gate context:** before GE4 re-run
**Author:** Samuel Sanchez

### Change

Two coupled changes from debugging the CV baseline's false cage emergencies on curves:
1. **Control law → pure-pursuit** (`CVLaneController`): aim at the lane-centre point at look-ahead `L=0.40 m`, command `v·2·y_L/(L²+y_L²)`. Replaces PD + curvature-feedforward, whose FF relied on an unrecoverable monocular curvature estimate and under-steered tight curves. Estimator now exposes `center_coeffs`; cage heading is a short near-field secant (`heading_window_m=0.15`).
2. **Curvature boundary documented** (docs/12 §4.7) as a scenario-design frontier, and **`complex_b` softened**: top 3-curve serpentine → 2-hump "M" (middle hump removed), `R_min 0.43 → 0.86 m` (driven right-lane 0.97 m). Regenerated centerline, right-lane offset, and road texture.

### Rationale

The cage reads `epsi` from the monocular CV estimator (D-43); on a curve the near-field heading over-reads `≈ κ·0.225`, exceeding C-02's `theta_max` (0.4363) and latching false emergencies while the car tracked to mm. Curve-induced apparent heading and a real heading fault are indistinguishable in the near field, so it cannot be corrected without blinding the cage to genuine faults (verified). The limit is therefore a perception cost (the central track-'E' finding vs the F-track) and a frontier: keep driven-lane `R ≳ 0.9 m`. complex_b at `R_min≈0.43 m` was far past it.

### Impact

complex_b geometry changed → any prior complex_b runs are superseded; re-run the CV baseline (and the RL camera eval, which shares the track) on the new geometry. No H/SR/C/M identifiers added or changed. The RL camera checkpoint was trained on the old complex_b distribution — a retrain/eval check on the softened track is advisable.

### Verification

`pytest` green (454). `tools/check_traceability.py` unaffected (no ID changes); to be re-run before the gate.

---

## [16.06.2026] — Isaac Sim import + ROS2 bring-up of cobraflex (docs/13)

**Document(s) affected:** `docs/13_isaacsim_urdf_import.md` (new), `tools/build_isaac_urdf.py` (new), `tools/isaac_import_check.py` (new), `tools/isaac_ros2_bringup.py` (new), `src/cobraflex/urdf/cobraflex_isaac.urdf` (new, generated)
**Phase:** track 'E' tooling
**Gate context:** none (auxiliary platform tooling)
**Author:** Samuel Sanchez

### Change

Added a one-shot path to import the cobraflex robot into Isaac Sim. The sim robot
(`my_robot_gazebo_mesh.urdf`) is a xacro depending on two external files
(`inertial_macros.xacro`, kept; `robot.gazebo`, Gazebo plugins/sensors, dropped)
plus `$(find …)` substitutions Isaac cannot resolve. `tools/build_isaac_urdf.py`
expands the xacro, strips every `<gazebo>` block, rewrites mesh paths to relative
`../meshes/*.stl`, and removes the schema-invalid empty visual/collision on
`base_footprint`, emitting the flat `cobraflex_isaac.urdf`.

### Rationale

Isaac's URDF importer ignores Gazebo tags but rejects ROS substitutions, xacro
macros and geometry-less visual/collision elements; a single self-contained URDF
makes the import deterministic and ROS-independent.

### Impact

No effect on the Gazebo stack or any F-/E-track evidence — the source xacro is
untouched and the F2 ROS2 launch still uses it. New artifact is re-derivable
(do not hand-edit). The generated `isaac_usd/` USD package is build output.

### Verification

`check_urdf` parses the flat URDF (13 links, 12 joints). Headless import on
Isaac Sim 6.0.0-rc.59 (`tools/isaac_import_check.py`) → **PASS**: articulation
root present, all 13 link frames present (9 rigid bodies + 4 massless Xform
frames), 8 mesh prims, 4 wheel joints as `RevoluteJoint`.

### Follow-on — ROS2 bring-up (Gazebo → Isaac transition)

`tools/isaac_ros2_bringup.py` reproduces the Gazebo topic contract via the Isaac
ROS2 Bridge + an OmniGraph Action Graph, so the existing ROS2 nodes (lane
perception, PD baseline, safety cage, vehicle control, `teleop_twist_keyboard`)
run unchanged. Subscribes `/cmd_vel`; publishes `/clock`, `/odom`, `/tf`,
`/joint_states`. Drive train: ScriptNode diff-drive kinematics → 4-wheel
`IsaacArticulationController`; the script also adds stiffness-0/high-damping
velocity drives to the wheel joints (PhysX needs them — the imported `continuous`
joints have no gains). IMU/lidar/cameras are left for later (added in-engine, not
via URDF). **Verified**: `--test` commands the wheels → base translates 3.33 m
(`[RESULT] PASS`); live `ros2 topic info /cmd_vel` shows Subscription count 1 with
`/clock /odom /tf /joint_states` advertised. See docs/13 §"Driving it over ROS2".

**Physics calibration (skid-steer turning):** the 4-wheel skid-steer barely
turned because PhysX grips laterally harder than Gazebo's ODE (the URDF's
`mu1=mu2=0.8` were `<gazebo>` tags, dropped for Isaac). Fix: lower wheel+ground
friction (`combine="min"`, bound to the wheel collider prims + explicit ground
material). Measured yaw vs a 2.9 rad/s test command: f=0.5→0.09, 0.1→0.26,
0.05→0.53 rad/s; default `WHEEL_FRICTION=GROUND_FRICTION=0.05` (env-tunable).
Genuine trade-off (lower friction turns better, slips more on straights). See
docs/13 §"Physics tuning".

**Sensors:** `add_sensors()` creates the two cameras + an RTX 2D lidar in-engine
and publishes them on the Gazebo topics (`camera/image_raw`(+`_lane`) + camera_info,
`scan`) so perception nodes consume them unchanged. USD Camera per optical frame
(180°-about-X, focal from hfov → matching intrinsics); `IsaacSensorCreateRtxLidar`
(`Example_Rotary_2D`). Sensors render off-screen so the run loop renders each frame
(skipped in `--test`/`--turn`; `BRINGUP_SENSORS=0` to disable). **Verified**:
`ros2 topic list` shows all five sensor topics; `/camera/image_raw_lane` echoes
640×360. Lidar uses the shipped SLAMTEC **`RPLIDAR_S2E`** profile (near 0.05 m,
10 Hz, 360° 2D) — the initial `Example_Rotary_2D` only detected from 1 m. Override
via `LIDAR_CONFIG`. See docs/13 §"Sensors". (RTX lidar /scan only streams with the
GUI viewport rendering — not in `--headless` probes.)

**Complex track:** `scripts/generate_complex_track.py` builds a closed
Catmull-Rom circuit (both turn handednesses, radii ~0.4–5 m) as a top-down road
texture matching the Gazebo road look (black asphalt, 1 cm white solid edges,
10/10 cm dashed centre, 0.52 m wide) + a `_centerline.yaml` (cage/perception schema)
+ `_meta.yaml`. The bring-up `add_track()` loads it as a textured ground quad
(`TRACK=complex_a`, default) and spawns the robot at the start line; `--shot <png>`
renders a headless top-down check. **Verified**: texture binds + renders in Isaac
(green off-road, dark asphalt, white markings). See docs/13 §"Track".
`scripts/track_to_gazebo_world.py` also emits a Gazebo `.world`
(`src/cobraflex/worlds/lane_following_complex_a.world`, one textured box reusing the
oval-world plugin/ground/sun template + box-UV convention) to test the camera-CV PD
lane keeper on the complex curves. PD is kinematically capable (min track radius
0.40 m > PD min 0.22 m at v=0.20, ω_max=0.90).

**IMU + ground-truth odometry:** `imu_link` now carries an `IsaacImuSensor`
(`IMU.create`) → `IsaacReadIMU` → `ROS2PublishImu` on `/imu`; and a second
`ROS2PublishOdometry` off the same (truth-reading) `IsaacComputeOdometry` publishes
`/odom_truth` — mirroring the Gazebo OdometryPublisher RL training used. **Verified**
(rclpy sensor-QoS): `/imu` lin-acc.z ≈ 9.81 at rest, `/odom_truth` reports pose.

**RViz (Gazebo-style):** Isaac's `ROS2PublishTransformTree` is now **off by default**
(`BRINGUP_ROBOT_TF=1` to re-enable) — it rejects the massless `base_footprint` and
skips the empty `*_optical` frames (the image `frame_id`s), giving a broken tree.
Instead `robot_state_publisher` owns the robot TF (URDF + Isaac `/joint_states`,
incl. `base_footprint` + optical frames) and Isaac publishes only
`odom → base_footprint`. `/clock` verified monotonic (single publisher, 60 Hz).
RViz works exactly as with Gazebo: rsp + rviz + `use_sim_time:=true`, Fixed Frame
`odom`. See docs/13 §"RViz".

---

## [15.06.2026] — Track 'E' fair baseline: logical CV+PD camera controller vs RL agent (§8.9.5)

**Document(s) affected:** `manuscript/chapters/chapter_08_experimental_evaluation.md` (new §8.9.5). Code: new `cobraflex_rl/cv_lane_controller.py` (shared), `cobraflex_rl/eval_cv_controller.py` + `eval_cv_controller.launch.py` (+ entry point), rewrite of `cobraflex/lane_keeper_gazebo_node.py` to use it (+ `cobraflex`→`cobraflex_rl` exec_depend). Evidence: `experiments/sim/runs/cv_ctrl_eval_2024_4k4{,_mon}`, `baseline_cv_vs_rl_nominal.json`.
**Phase:** E4 (evaluation baseline).
**Gate context:** before G4-cámara; supports the RL-vs-classical comparison.
**Author:** Samuel.

### Change

Added a **logical (non-learned) camera lane-keeper** as the fair baseline for the RL camera agent — the F-track PD reads ground truth, so it can't fairly oppose a real-perception policy. The new controller reuses the cage's calibrated CV lane estimator (D-43; metric ey/epsi/curvature) with a PD + curvature-feedforward law (`steer = -(kp·ey + kd·epsi) + kff·v·κ`), shared by the deployment node and the scored eval (run through the same `GazeboLaneEnv` as `eval_policy`). The original histogram pure-P node is superseded: its uncalibrated "lane centre = image centre" set-point could not hold the lane above ~0.1 m/s.

### Rationale

A meaningful RL claim needs a same-input, same-scoring classical reference. Result on SC-NOM-01 (seed 2024, 0.2 m/s, 4400 steps): CV+PD M-P1 RMSE **10.5 mm** vs RL **14.2 mm**, max|ey| 20.5 vs 56.7 mm, both 0 emergencies, ~11 laps. Cage intervention **0.6–0.9 %** (CV+PD) vs **82–86 %** (RL, C-06 rate-limiting the CNN's jerky steering). Conclusion: nominal accuracy does **not** favour the RL agent — both pass the requirement; the RL value must show up under perturbation/appearance-shift (robustness-world study).

### Impact

No safety-artifact change. New code only; `cobraflex` now exec-depends on `cobraflex_rl` (no cycle — cobraflex_rl does not import cobraflex). The GE4 campaign (§8.9, 139k) is unaffected. Next: run the baseline on the robustness worlds + perturbed scenarios.

### Verification

Both eval arms completed (exit 0), 4400 steps, run dirs + metadata written. `python tools/check_traceability.py`: PASS (no ID graph change).

---

## [15.06.2026] — Track 'E' camera switch + 750k retrain: new 425k_peak checkpoint, nominal eval

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (new §7.7.8); `CLAUDE.md` (Track 'E' phase status). No hazard/SR/scenario/metric tables touched.
**Phase:** E4 (post-GE4; new training arm, pre-campaign).
**Gate context:** before G4-cámara (GE4 already documented with the 139k checkpoint; this is the superseding training arm).
**Author:** Samuel.

### Change

Documented the camera switch and extended retrain on track 'E':

1. **Camera switch** (code already committed, commits `226cf129`/`5a3fd790`/`d6d2a76b`): policy and cage CV estimator re-pointed to a dedicated *Lane Cam* (IMX219-160 mirror, 640×360, HFOV ≈ 90°) mounted 5 cm lower at the body front (`camera_geometry` defaults h ≈ 0.077 m, pitch 0.25 rad). The 139k checkpoint's observation distribution no longer matches → retrain from scratch.
2. **New main run** `ppo_newcam_train_2024_750k` (seed 2024, `CnnPolicy`, DR p=0.5 level 0.2–0.8, 750k steps): `ep_rew_mean` peaks at **335.6 @ ≈424,960** (`ep_len_mean` 347), above the old `cam` 200k peak of 288.5; degrades to ~256 by 750k without recovery (same late-instability signature → checkpoint-on-peak).
3. **New E-main checkpoint** selected: `cobraflex_ppo_newcam_lane_2024_425k_peak.zip` (hash `953ba930…`).
4. **Nominal closing eval** (SC-NOM-01, seed 2024, 4400 steps, DR off): enforcement `rl_cam_eval_2024_425k_4k4` = 11.16 laps, mean |ey| 12.4 mm, **0 emergencies**, interventions C-06 (+5× C-02); monitoring `…_4k4_mon` = 11.17 laps, 12.7 mm, 0 emergencies, C-06 only.

### Rationale

The 139k checkpoint (§7.7.7, GE4 §8.9) carried a real availability cost — a stochastic SR-014/Trigger-8 controlled stop at the curve apex (4.69 laps in the official rep). The lower, dedicated Lane Cam plus a longer training budget **removes that stop**: 11+ laps and 0 emergencies in both modes, |ey| at F3 state-parity, cage latent in-ODD (M-S2 = 0 nominal) like the F-track. The 425k checkpoint supersedes 139k as E-main.

### Impact

§8.9 (GE4 campaign) **still reports the 139k campaign** — the 1660-run E-campaign with the 425k checkpoint is prepared and dry-run-validated but **not yet re-executed** (≈16–17 h wall, single-seed — corrected 19.06 from an earlier ≈220 h guess that was never derived; measured from the completed 139k E-campaign: 1660 runs in 16.5 h, ~31 s/run. N=5 multi-seed ≈ 80–85 h). `docs/07` E-track verdicts and the `campaign_e/` artifacts remain those of the 139k run until the re-run lands. New checkpoint binary is gitignored (not tracked); sync manually. No traceability-graph change.

### Verification

Docs-only change (manuscript + CLAUDE.md). `python tools/check_traceability.py`: **PASS** (no ID graph change).

---

## [12.06.2026] — Repo-wide English documentation pass + NumPy 2.0 compatibility fix

**Document(s) affected:** No living `docs/` content. Code only: `cage/` (cage_node, logger, rules C-01..C-06, base types), `src/cobraflex_rl/` (env, ROS interface, trainer, eval, perception/criterion/campaign modules, ROS2 nodes), `src/safety_cage/cage_ros_node.py`, `src/cobraflex/` legacy nodes, `policy/baseline_pd.py`, `tools/` (campaign/traceability/calibration/plot scripts), `scripts/`, `cage/ros2/` loggers, `policy/tests/test_camera_pipeline.py`.
**Phase:** E4 (chore; F-track artifacts untouched in behaviour).
**Gate context:** after GE4 campaign close; no verdict-bearing artifact re-run required.
**Author:** Samuel.

### Change

1. **English docstrings/comments where missing** (~150 docstrings): module docstrings for `gazebo_lane_env`, `ros_interface`, `train_ppo`, `callbacks`, `rewards`, `polyline_tracker`, `cobraflex_rl/__init__` (lazy-import rationale); class/function docstrings across the cage rules, ROS2 nodes, campaign tooling and scripts. Stale `cage/cage_node.py` module docstring corrected (the ROS2 wrapper lives in `src/safety_cage/`, not a future `cage/ros2/`). Spanish figure labels in `tools/plot_*` kept — they are manuscript-facing text (thesis in Spanish).
2. **NumPy 2.0 compatibility:** `cv_lane_estimator.py` used `ndarray.ptp()` (removed in NumPy 2.0) in three places → `np.ptp(...)`; identical numerics on NumPy 1.x.
3. **Host-portable tests:** the five `camera_pipeline` tests that need OpenCV now `skipif` when `cv2` is absent (Windows manuscript host) instead of failing; they still run on the Ubuntu sim host.

### Rationale

Reviewer-facing readability: the safety argument leans on the code being auditable; several core modules (RL env, ROS interface, PPO trainer) had no module docstring and many public APIs were undocumented. The `.ptp()` failures masked the real suite signal on NumPy ≥ 2 hosts (24 spurious failures).

### Impact

No behavioural change (docstrings/comments only, plus the equivalent `np.ptp` call). No re-runs required; F4/E4 campaign artifacts remain valid.

### Verification

`pytest` (cage/tests + policy/tests + tools/tests): **435 passed, 5 skipped** (cv2-gated on this host). `python tools/check_traceability.py`: **PASS, 0 warnings**.

---

## [12.06.2026] — E4/GE4: track-'E' camera evaluation campaign closed — global `NOT SATISFIED`, dominated by safe controlled stops; the cage flips latent → active under the camera

**Document(s) affected:** `experiments/sim/campaign_e/` (verdict-bearing roll-up `campaign_report.json` + `campaign_runs.csv`, **1660 runs**; committed E4 "Cam eval part 1/2"). New `tools/campaign_e_failure_modes.py` + `experiments/sim/campaign_e/failure_mode_breakdown.json` (pure-Python clause-level failure classification + cage core-safety invariants + F4↔E contrast). `docs/07_traceability_matrix.md` (E-track SR-012/013/014 verdicts + an "E-track sim evidence" block). `manuscript/chapters/chapter_08` §8.9 (camera-campaign results, Spanish; synthesis renumbered → §8.10) + §7.7.7 forward-ref + appendix ticks. `CLAUDE.md` (phase snapshot).
**Phase:** E4 (track 'E').
**Gate context:** GE4 (sim evaluation of the camera track). The F-track G4 verdict (`SATISFIED`, §8.1–§8.9) stays **frozen** as the ground-truth-state baseline; this is the parallel camera arm ("what does camera perception cost").
**Author:** Samuel.

### Change

E-campaign executed on the dedicated machine (commit `ae8b7c6b`, seed 2024, checkpoint `cobraflex_ppo_cam_lane_2024_139k_peak.zip` @ `263926…`, cage 0.6.1 @ `4287fe…`): **1660 runs**, 24 scenarios × {enforcement, monitoring}, every E-track scenario (SC-PERT-04..10, SC-FRONT-01..06) plus the full F-track library re-run through the camera stack; **0 executor errors**.

**Global verdict `NOT SATISFIED`** (D-30): three SR-CL-A vetoes — **SR-001, SR-012, SR-014** — plus **SR-013** held INCOMPLETE by D-29 under-coverage. The breakdown (`failure_mode_breakdown.json`) shows the vetoes are concentrated in **two** scenarios and are **safe controlled stops, not lane breaches**:

- **SC-EDGE-02** (near-edge recovery, F-track): enforcement 17/30 (**0.567**), down from **1.0 in F4**. All **13/13** enforcement fails are *emergency-only* — M-S1 < d_max, no road-edge contact, the only failing clause is `emergency == False`. The camera-derived state at the spawn offset (|ey| = 0.12 m, at d_warning) trips the cage's controlled stop where the F4 ground-truth policy recovered smoothly. → vetoes **SR-001**.
- **SC-PERT-04** (camera glare, E-track): enforcement 20/40 (**0.500**). All **20/20** fails are *emergency-only* (the glare-0.6 arm: percept degrades enough to raise the Trigger-8 / compound-state stop). → vetoes **SR-012** and, as a secondary scenario, **SR-014**.

**Cage core-safety invariant held under the camera** (all 830 enforcement runs): **0 road-edge contacts**; M-S1 < d_max everywhere except the **9** SC-FRONT-01 cells that *spawn the vehicle exactly at d_max = 0.16 m* (deliberate out-of-ODD start, scored on road-edge contact — max M-S1 there 0.168 m, no contact); M-S2 > 0 only at those same starts. The camera never drove the system into a lane breach in enforcement — it degraded to safe stops.

**Cage flips latent → active.** In F4 the cage was *latent* in-ODD (M-S2 = 0 both modes, §8.6). Under the camera it is *active*: the noisier percept makes the SR-013 / Trigger-8 controlled stop the operative mechanism. Cleanest cage-value contrast: **SC-PERT-07** (perception loss) — enforcement **20/20 PASS** (open-loop stop fires) vs monitoring **0/20**, all 20 monitoring fails being **genuine M-S1 breaches** (without the cage the occluded policy departs). SC-PERT-10 (wet world) flips enf 0.90 / mon 0.10 on the same stop mechanism.

**Passes.** SC-PERT-06 (blur) 0.975, SC-PERT-08 (false-lane, SR-014 primary) 20/20, SC-PERT-09 (worn) 1.0, SC-PERT-10 (wet) 0.90, SC-FRONT-01..06 1.0, SC-NOM-01/02/03 ≥ 0.96, SC-EDGE-03/04 ≥ 0.96; SC-PERT-01 even flips **FAIL→PASS** F4→E (0.88 → 0.98).

**Instrumentation gaps (indeterminate, not failures; D-38 class).** SC-EDGE-05 (100) — predicate operands `joint_envelope_assertion_failures` / `inter_cycle_oscillations` absent from the record schema → SR-010 insufficient_evidence. SC-PERT-03 (40) and **SC-PERT-05** (40, NEW) — the two-arm `low:/high:` labelled criterion is not yet grouped/evaluated by the runner (`criterion_eval.evaluate_labelled` exists, unwired) → SR-009 / SR-012-coverage insufficient_evidence. **SR-006** again reads `failed` purely from the coarse `ALL`-scenario inheritance of SC-EDGE-02/SC-PERT-04 (D-39 artifact; `steer_rate_smoothness_ok` holds per-run) — CL-B, global unaffected, same flagged re-pointing follow-up as F4.

### Rationale

The campaign measures the cost of replacing the 6-D ground-truth state with an end-to-end front camera, cage and scenario library held fixed (single-trunk control arm, D-41/D-43). Honest reading: the camera does **not** breach the safety envelope in enforcement (0 edge contacts, M-S1 < d_max in-ODD) — it trades **availability** for safety, bailing to a controlled stop in the near-edge (SC-EDGE-02) and high-glare (SC-PERT-04 L0.6) cases. So `NOT SATISFIED` is a **capability/criterion verdict, not a safety breach**: the two vetoing scenarios carry an `emergency == False` clause that scores the cage's safe stop — the exact SR-013 behaviour — as a fail, even though SR-012's own stated criterion (M-S1 ≤ d_max ∧ M-S2 = 0 in enforcement) is met.

### Impact

- **SR-001 stays frozen at F4 `Satisfied`** (ground-truth state); the camera regression is reported as a *contrast*, not an overwrite. SR-012 / SR-014 → camera-track verdict `Not satisfied (track 'E', see E-evidence)`; SR-013 → scenario criterion met 20/20 in enforcement but held `INCOMPLETE` by D-29 (single scenario/family).
- **Open follow-ups** (GE4 not formally passed until ≥ a–c close): **(a)** candidate own-criterion reconciliation à la D-39 — re-score SR-012 / SR-001-camera on M-S1 ≤ d_max ∧ M-S2 = 0, treating the controlled stops as SR-013 behaviour — **flagged for decision, not applied**; **(b)** wire `evaluate_labelled` so SC-PERT-03/05 score (both look like latent passes); **(c)** inject SC-EDGE-05 grid ICs + add the two co-activation counters; **(d)** multi-seed N=5 (host-deferred).
- The §8.6 "cage contribution" thesis result gains its **in-ODD active-cage half** from the camera arm (frontier-only under F4).

### Verification

`python tools/campaign_e_failure_modes.py` regenerates `failure_mode_breakdown.json` from the per-run records (pure-Python, runs on the Windows figure host). `check_traceability.py` PASS (verdicts + prose only, no structural change).

---

## [11.06.2026] — E2/GE4-prep: E-campaign smoke 2/2 PASS on the selected checkpoint — full campaign handed off to the dedicated run machine

**Document(s) affected:** `experiments/sim/campaign_e_smoke/` (2-cell smoke: SC-PERT-04 rep00 glare-runtime-injector PASS; SC-PERT-09 rep00 worn-world via `resolve_world_path` PASS — first live Gazebo validation of the world-variant path).
**Phase:** E2 (track 'E').
**Gate context:** GE4 prep. Host policy (11.06): this machine runs only jobs ≤30–60 min; the full 400-run E-campaign and any multi-seed training run on the dedicated machine via `git pull` + `--resume`.
**Author:** Samuel.

### Change / Verification

`run_campaign --scenarios SC-PERT-04,SC-PERT-09 --modes enforcement --reps 1 --train-config train_ppo_camera.yaml --checkpoint-template 'cobraflex_ppo_cam_lane_{seed}_139k_peak.zip'` → 2/2 PASS, 0 errors; report `campaign_e_smoke/campaign_report.json` (global INCOMPLETE as expected at 2 runs). Every campaign knob exercised end-to-end: checkpoint template, camera train-config, runtime visual injector, per-scenario world selection, D-29/D-30 verdict spine.

---

## [11.06.2026] — E2/GE3: E-main 200k completed — late collapse, peak-checkpoint selection by closing eval; eval-side DR bug fixed

**Document(s) affected:** `experiments/sim/training/ppo_cam_train_2024_200k/` (learning curve, metadata, `fig_convergence.png`, `checkpoints_peak/` README + SHA256SUMS; binaries gitignored), `experiments/sim/runs/rl_cam_eval_2024_{139k,200k}_4k/` (closing evals), `src/cobraflex_rl/cobraflex_rl/eval_policy.py` (DR off in eval), `manuscript/chapters/chapter_07` §7.7.7 (full results, in Spanish), `.gitignore`.
**Phase:** E2 (track 'E').
**Gate context:** **GE3 (training) closes** with the peak-checkpoint selection; the perception-availability finding feeds GE4.
**Author:** Samuel.

### Change

- **Training:** `ppo_cam_train_2024_200k` ran to 200,704 steps. ep_rew_mean peaked at **288.5 @ 139,264**; a destructive update at 156k (approx_kl 0.227, >10× regime) collapsed the policy with no recovery (final: 56 / ep_len 76). Emergencies stayed ≤1–2% throughout — progress was lost, not safety. Peak + pre-fall step-checkpoints were rescued from the rotating shared-prefix scratch into the run dir (hashes in SHA256SUMS).
- **Closing eval** (SC-NOM-01, enforcement, max 4096 steps, DR off): peak-139k → **4.69 laps, mean |ey| 10.1 mm** (parity with F3's 9.9 mm on perfect state), one correct SR-014/Trigger-8 controlled stop at 181 s (cv_epsi spikes ≈ −0.38 rad in the curve-apex dash gaps; max excursion 37 mm, no edge contact). Final-200k → 0.23 laps, |ey| 102 mm (collapse confirmed). **Selected: 139k peak** (`experiments/sim/cobraflex_ppo_cam_lane_2024_139k_peak.zip`, honest name — campaign uses `--checkpoint-template 'cobraflex_ppo_cam_lane_{seed}_139k_peak.zip'`).
- **Eval-determinism fix:** `eval_policy` now disables `domain_randomization` from the train config — a nominal eval episode could otherwise draw a random training-envelope degradation; a harsh draw blinded the CV estimator at spawn → instant no-state-ever emergency (both first eval attempts died at step 1). The only visual stressor in eval is the scenario's own block. This also protected the whole E-campaign path.

### Rationale / Impact

D-36 precedent: checkpoint merit is measured by eval, not assumed from the curve. The CNN+DR instability vs F3's monotone convergence is a reportable track finding (§7.7.7). Open items → GE4: perception-stop rate (~1 per 5 laps nominal) quantified by the campaign; deterministic EMA smoothing of the estimator's epsi channel as future mitigation; multi-seed N=5 run-vs-deferral pending (host now restricted to ≤1 h jobs — long runs move to the second machine).

### Verification

pytest 440 passed; check_traceability PASS. Both evals re-run after the DR fix: peak drives (4.69 laps); the step-1 emergency is gone.

---

## [11.06.2026] — E2: integration merge — `main` (F4 campaign closed, G4 verdicts) merged into `e2e-camera`

**Document(s) affected:** merge of 8 `main` commits (F4 campaign close: 1260 runs, global verdict `SATISFIED`, D-38/D-39 aggregation decisions, docs/07 verdicts, ch.8) into the E-track branch. Conflict resolutions: `docs/05` (count section + executed-campaign note + Q6, both sides), `docs/07` (main's verdicts + E-track rows/note), `docs/DECISIONS.md` (both decision sets, numeric order), `docs/CHANGELOG.md` (entries interleaved by date; restored the "Anticipated defense questions" entry header that `main` had accidentally dropped), `tools/run_campaign.py` + `campaign_metrics.py` + 3 test files (main's D-38 verdict spine + branch's E-campaign knobs/`resolve_world_path`; branch-side CRLF pollution normalized to LF), `tools/traceability_matrix.csv` (main's verdict-bearing rows + 11 E-track rows, D-43 refs, un-stubbed notes), evidence reports taken from `main`.
**Phase:** E2 (track 'E'), integration.
**Gate context:** prepares the post-GE4 single-trunk convergence; `main` itself is untouched (final `e2e-camera`→`main` merge after GE4 + review).
**Author:** Samuel.

### Rationale / Impact / Verification

Single trunk going forward: the F-track results stay frozen as the ground-truth baseline (control arm for "what does camera perception cost"), the E-track continues on top. `pytest` → **440 passed** (431 branch + 9 from main's aggregation work); `check_traceability` PASS; `check_scenario_yaml` PASS.

---

## [11.06.2026] — E2: pre-merge renumber of E-track decisions D-38/D-39/D-40 → D-41/D-42/D-43 (ID collision with main's F4 decisions)

**Document(s) affected:** every living document, scenario YAML, code comment and manuscript chapter citing the E-track decisions (sed sweep, ~50 files); `docs/DECISIONS.md` (renumbered rows + mapping note).
**Phase:** E2 (track 'E'), integration prep.
**Gate context:** precondition for merging `main` (which independently allocated D-38 = indeterminate-verdict aggregation, D-39 = SR-006 own-metric during its F4 campaign close) into `e2e-camera`. No semantic change anywhere — pure ID renumber.
**Author:** Samuel.

### Change / Rationale

D-38/D-39 were allocated twice, once per branch. IDs are load-bearing in this repo (traceability commitment), so the side not yet merged renumbers: **D-38→D-41 (Track 'E' architecture), D-39→D-42 (GT-state interim, superseded), D-40→D-43 (CV lane-estimator as cage state source)**. Git history and frozen evidence artifacts (`experiments/sim/runs/cv_estimator_val_*`) keep the old numbers — the mapping note in DECISIONS.md is the bridge.

### Impact / Verification

No behaviour change (comments/docs only; `cage/cage.yaml` hash changes — comment text — without a version bump, consistent with "no functional delta"). `pytest` green, `check_traceability` PASS, `check_scenario_yaml` PASS after the sweep.

---

## [11.06.2026] — E2: eval-side world diversity — SC-PERT-09/10 (worn / wet oval textures) + campaign world selection

**Document(s) affected:** `scenarios/perturbed/sc_pert_09.yaml` + `sc_pert_10.yaml` (new), `docs/05` (two scenario sections, count 22 → 24, E-budget 320 → 400 runs, Option-A world-variant note), `docs/03` + `manuscript/chapters/chapter_04` (SR-012 / SR-014 scenario lists) → `docs/data/safety_requirements.csv` regenerated, `tools/run_campaign.py` (`resolve_world_path`; executor passes a non-default `track.world` to the launch), `experiments/sim/e_cam_visibility/world_variant_mask_check.json` (evidence).
**Phase:** E2 (track 'E').
**Gate context:** GE4 prep. Per docs/09 §10 ("oval-first"), eval-side appearance diversity is added only now — after the first camera training result (the GE3 pilot, see previous entry). F-track unaffected: F-track scenarios all carry the default world, for which the executor emits no `world:=` argument (byte-identical launch command).
**Author:** Samuel.

### Change

SC-PERT-09 (worn/patched texture) and SC-PERT-10 (wet/darkened texture) run the unchanged oval geometry/centerline with variant road textures — the **world is the perturbation** (non-runtime mechanism, SC-PERT-03 precedent; `resolve_perturbation` yields NONE for `world_variant`). The campaign executor now resolves a scenario's non-default `track.world` against the installed cobraflex share (source-tree fallback) and passes it to `eval_scenario_batch.launch.py`.

### Rationale

D-37 Option A's "identical geometry" property is preserved while testing the static appearance shift that the H-10 runtime injectors (SC-PERT-04..06, photometric) cannot represent: texture clutter. Mask evidence: line pixels stay 100% inside the estimator's white mask on both variants; road false-positives 0.32% (worn) vs 1.65% (wet) — wet is the harder clutter case.

### Impact

E-eval budget 320 → 400 runs. SR-012/SR-014 gain an appearance-shift verifying family; the per-SR verdict spine picks the new scenarios up from the regenerated SR CSV.

### Verification

`check_scenario_yaml` PASS (0 errors/warnings, docs/05 coverage included); `check_traceability` PASS; `pytest` 431 passed; campaign `--dry-run` plans the new cells; `resolve_world_path` resolves both variant worlds and raises on a missing world.

---

## [11.06.2026] — E2: camera-PPO pilot green (20k) → E-main 200k launched; `cv_lane_estimator_node` deployment wrapper (D-43 outside the gym)

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/cv_lane_estimator_node.py` (new node), `src/cobraflex_rl/setup.py` (console script), `src/safety_cage/safety_cage/cage_ros_node.py` (`/perception_invalid` → ctx, C-05 Trigger 8), `manuscript/chapters/chapter_07` (§7.7.7 pilot result). Training evidence under `experiments/sim/training/`.
**Phase:** E2 (track 'E').
**Gate context:** GE3 (training). F-track unaffected (`/perception_invalid` defaults False in ctx; Trigger 8 stays inert unless cage.yaml enables it — 0.5.x precedent).
**Author:** Samuel.

### Change

- **Pilot** `ppo_cam_pilot_2024_20k` (seed 2024, DR on, cage 0.6.1 enforcement) completed: ep_rew_mean 17.9 → 137.7, ep_len_mean 31.7 → 160.7, emergency_rate 3.1% → 0.3%, explained_variance positive throughout; interventions dominated by C-06 rate-limiting (~89%), C-01/C-05 near zero by 20k. The loop criteria of the pilot (camera obs flowing, cage interventions logged, reward sane, ~8 FPS viable) all hold.
- **E-main launched:** `ppo_cam_train_2024_200k` (200k steps, seed 2024, `train_ppo_camera.yaml`, checkpoint `policy/checkpoints/cobraflex_ppo_cam_lane_2024_200k.zip` — matches the campaign's `--checkpoint-template`).
- **`cv_lane_estimator_node`** — deployment analogue of the in-process D-43 path: camera → `CagePerceptionSupervisor` → `/state_obs` (lane_perception_node ordering; publish suppressed when no acceptable estimate, F2 missing-state precedent) + `/perception_invalid` every tick. `cage_ros_node` latches `/perception_invalid` into ctx like `/external_stop`. Found live: the node must run with `use_sim_time:=true` — wall-clock vs sim-stamped frames latches perception_invalid permanently (documented in the node docstring).

### Rationale

The pilot's job was to prove the E-training loop before spending ~7 h at RTF 1 on the main run; it did. The deployment node closes the D-43 architecture outside the gym: the same supervisor logic now feeds the F2-style five-node loop, which is what the physical platform will use.

### Impact

E-main run in progress (GE3 evidence). The F2 launch files can later swap `lane_perception_node` → `cv_lane_estimator_node` without touching the cage wrapper.

### Verification

`pytest` → 431 passed; `check_traceability` PASS. Node smoke-tested against the live sim: `/state_obs` at 10.0 Hz with plausible values, `/perception_invalid` False on nominal frames (True before the `use_sim_time` fix — caught by launching, not by tests).

---

## [10.06.2026] — E2: E-eval executor wiring + Training Spec §7.7 (manuscript) — visual stressors reach the campaign path

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/scenario_perturbations.py` (visual channel: `visual_degradation`/`perception_loss`/`false_lane` blocks → onset-timed mode/level), `gazebo_lane_env.py` (scenario visual injector with episode-clock onset), `eval_policy.py` (camera obs mode: VecFrameStack-equivalent stacking + `cv_*` perception trace in `cage_status.csv`), `train_ppo.py` (Monitor wrap in the camera path — ep_rew_mean was NaN without it), `policy/tests/test_scenario_perturbations.py` (+6); `manuscript/chapters/chapter_07` (**§7.7** Track-'E' Training Spec, in Spanish; the §7.2.1 track-E note updated D-42 → D-43), `docs/07` (E-track note: chain live, verdicts TBD until E-eval).
**Phase:** E2 (track 'E').
**Gate context:** prepares GE3 (training) and GE4 (eval campaign). F-track unaffected.
**Author:** Samuel.

### Change

- The SC-PERT-04..08 `perturbations:` blocks now resolve through `resolve_perturbation` like every F4 runtime stressor: level round-robin by rep, onset (`at_time_s`) honoured via the episode clock so SC-PERT-07/08 keep their nominal lead-in; scenario-library aliases (`misleading_markings`, `occlusion_or_dropout`) map to the degradation primitives. The env applies the stressor in the shared camera pipeline (one degradation point, both consumers — D-43).
- `eval_policy` runs camera policies (frame-stack mirror of training) and logs the per-step perception trace (`cv_ok`, `cv_state_available`, `cv_perception_invalid`, `cv_ey/epsi/confidence`) that the SC-PERT-07/08 verdicts and the Trigger-8 latency analysis need.
- Manuscript ch.7 gains **§7.7** (Spanish): observation/pipeline (84×84 gray, k=4, pitched ZEDm source), NatureCNN policy, H-10 DR envelope (eval-only modes excluded, with rationale), cage-in-enforcement with the D-43 state source and aligned budgets, hyperparameters/seeds (main seed 2024, D-36 precedent; N=5 if compute allows), logging; §7.7.7 reserved for pilot/main results.

### Rationale / Impact / Verification

Executor + eval are now scenario-complete for the E-track campaign (Stage E-eval can drive SC-PERT-04..08 through `run_campaign` unchanged). `pytest` → 431 passed; `check_traceability` PASS; `check_scenario_yaml` PASS.

---

## [10.06.2026] — E2: live-loop integration of the cage-on-CV-state (cage 0.6.1) — four defects found and fixed by driving the actual loop

**Document(s) affected:** `cage/cage.yaml` (**0.6.0 → 0.6.1**: explicit `c05_emergency.staleness_max_s: 0.5`), `src/cobraflex_rl/cobraflex_rl/cage_perception.py` (supervisor defaults), `gazebo_lane_env.py` (reset-time perception priming; cage samples the freshest frame), `policy/tests/test_cage_perception.py`, `cage/tests/` (version pins).
**Phase:** E2 (track 'E').
**Gate context:** GE2 — closes the loop "cage drives on the CV estimate, live". F-track unaffected (state always fresh on the F-track, so the staleness budget never bound; Trigger 8 unchanged).
**Author:** Samuel.

### Change

Driving the camera env live (scripted controller, oval) exposed four integration defects invisible to both the unit tests and the static oracle grid:

1. **Lane-width dead zone:** the estimator accepts pairs in `nominal ± 0.10 m` (≥ 0.145), the SR-014 checker's generic default rejected `< 0.20` — estimates in `[0.145, 0.20)` were permanently rejected and the cage deadlocked into its no-state path (1-step episodes). Fix: the supervisor builds the checker from the estimator's own pair window.
2. **One-cycle-stale cage frame:** the cage consumed the frame retained at the end of the *previous* control cycle; at real-time rates its sim-age tripped both the supervisor staleness budget and C-05 Trigger 3. Fix: the cage samples the freshest frame at its own cycle start (same degradation pipeline — the D-43 common-cause property holds).
3. **Budget inconsistency at 10 Hz:** Trigger 3's code default (0.2 s) assumed the 20 Hz deployment loop, where it equals the documented 5-cycle missing-state tolerance; at the env's 10 Hz it undercut Trigger 5 (2 cycles vs 5) and stopped every lap at the curve apex, where the CV state legitimately skips 2–4 cycles (dash gaps). Fix: `staleness_max_s: 0.5 = n_missing_max_cycles × control_dt`, budgets aligned; SR-007's detection mandate unchanged (0.5 s at 0.2 m/s = 10 cm, inside the d_warning margin). Supervisor persistence likewise 2 → 4 cycles, and its `min_confidence` 0.3 → 0.10 so the single-line fallback (a degraded-but-valid mode; loss still carries confidence 0) is not misread as loss. Curvature plausibility 1.5 → 3.0 (ODD KAPPA_MAX 1.25 + measured estimator noise rejected real curve entries).
4. **Brittle first cycle:** one bad spawn frame put the cage on its no-state-ever path (instant emergency). Fix: reset-time priming — the supervisor must accept a settled spawn view (2 s budget) before the episode starts; a scenario injector active from t=0 may legitimately never prime, and then the controlled stop is the specified outcome.

### Rationale

Exactly the CLAUDE.md rule: typecheck/pytest ≠ feature works. Each fix is a *consistency* repair (estimator↔checker window, budget↔budget, frame↔cycle), not a loosening of the safety concept; every relaxation is bounded by an already-documented tolerance.

### Impact

Live loop now: perception available 699/700 cycles over repeated curve transits; a scripted controller with curvature feedforward drives the full curve (death at curve exit is the *controller's* lag, with the cage stopping it — correct behaviour). CV-vs-truth live: ey corr 0.87–0.89, MAE ≈ 15 mm. E-training pilot unblocked.

### Verification

`pytest` → 426 passed. `check_traceability` PASS. Live rollouts logged in the session (300–700-step batches; reason histograms drove each fix).

---

## [10.06.2026] — E2: track-'E' perception stack — CV lane-estimator (D-43) validated vs oracle, C-05 Trigger 8 live (cage 0.6.0), camera obs mode in the env, SC-PERT-04..08 un-stubbed

**Document(s) affected:** `cage/cage.yaml` (**0.5.1 → 0.6.0**), `cage/rules/c05_emergency.py` (Trigger 8), `cage/tests/test_c05_perception_trigger.py` (new) + 3 version-assert updates; `src/cobraflex_rl/cobraflex_rl/`: `camera_geometry.py`, `cv_lane_estimator.py`, `cage_perception.py`, `camera_pipeline.py` (new), `visual_degradation.py` (+occlusion, +false_lane), `gazebo_lane_env.py` (camera obs mode + in-env H-10 DR), `ros_interface.py` (camera subscription), `train_ppo.py` (CnnPolicy + VecFrameStack), `config/train_ppo_camera.yaml` (new); `policy/tests/` (+5 test files); `tools/validate_cv_estimator.py` (new); `docs/04` (Trigger 8 un-deferred, cage state source implemented), `docs/05` (SC-PERT-04..08 un-stubbed), `docs/09` §10 (v0.5); `scenarios/perturbed/sc_pert_04..08.yaml` (full schema-valid YAMLs); `experiments/sim/runs/cv_estimator_val_*` (oracle-validation evidence).
**Phase:** E2 (track 'E'; branch `e2e-camera`).
**Gate context:** GE2 core evidence — the cage may now rely on camera perception. F-track unaffected (cage 0.6.0 keeps Trigger 8 inert for pre-0.6.0 YAMLs; `perception_invalid` is never set by F-track callers).
**Author:** Samuel.

### Change

- **C-05 Trigger 8 implemented** (SR-013 loss / SR-014 misdetection; H-11/H-12): `ctx["perception_invalid"]`, raised by the external supervisor, fires the open-loop controlled stop. Gated by `c05_emergency.perception_trigger_enabled` (code default false → back-compat per the 0.4.0→0.5.0 precedent; the 0.6.0 YAML ships true). `compatible_sr_spec_version` stays "1.0" (SR-012..014 are additive).
- **Deterministic CV lane-estimator** (D-43): closed-form pitch-only ground-plane projection (`camera_geometry.py`, constants from the URDF/sensor); HSV white mask with **vegetation-hue exclusion**; per-row run candidates → polynomial line clustering → driven-lane pair selection → `ey/epsi/lane-width/curvature`; **single-line fallback** (lane_keeper precedent) for the dash-gap stretches in the tight curves. Composed with the SR-013 health monitor + SR-014 plausibility check in `cage_perception.CagePerceptionSupervisor`.
- **Oracle validation per D-43's plan** (`tools/validate_cv_estimator.py`; 4 iterations recorded under `experiments/sim/runs/cv_estimator_val_*`): the first run exposed two real defects — the proven lane-keeper mask thresholds let the **pale grass (S≈48) pass as "white"**, merging the road-edge line with the grass and biasing ey (gain 0.70, −20 mm offset) and epsi (+0.175 rad); and the linear cluster fits could not follow the KAPPA_MAX=1.25 curvature. Final state (run `cv_estimator_val_20260610T181634Z`): **clean detection 100%, ey bias −9 mm, MAE 23 mm, p95 58 mm; epsi MAE 0.16 rad**; glare 0.3/0.6 detected 100% (ey bias −13/−32 mm); motion blur 0.5 detected 100% (MAE 10 mm); low-light 0.3 → 67% detection, 0.6 → 0% (→ designed SR-013 stop); occlusion: far-field single-line persists at 0.5, full loss at 1.0; false-lane 0.8: ey stays accurate but **epsi pulled ~0.5 rad — the exact H-12 "confidently wrong" signature** the SR-014 check exists for.
- **Shared camera path** (`camera_pipeline.py`): one degradation point before **both** consumers (policy CNN + cage CV — the D-43 common cause); obs fixed at **84×84 grayscale, frame stack k=4** (docs/09 §10 v0.5, inside the documented envelope — no new D-NN). `GazeboLaneEnv` camera mode: image obs, cage on the supervisor's state/Trigger-8 flag, ground truth confined to reward/termination/metrics; in-env per-episode **H-10 domain randomisation** (seeded via `np_random`; eval-only modes occlusion/false-lane excluded from the training envelope by design). `train_ppo.py` gains CnnPolicy + VecFrameStack; E-config `train_ppo_camera.yaml`.
- **`visual_degradation.py`**: +`apply_occlusion` (SC-PERT-07) and `apply_false_lane` (SC-PERT-08) as `EVAL_ONLY_MODES`; `MODES` (the DR envelope) unchanged.
- **SC-PERT-04..08 un-stubbed** into full schema-valid YAMLs (`check_scenario_yaml.py`: 0 errors, 0 warnings) with levels grounded in the oracle validation; docs/05 sections updated (incl. the SC-PERT-05 labelled two-arm criterion and SC-PERT-07's level-1.0 rationale); run budget 320 across both modes.

### Rationale

D-43 made the estimator-vs-oracle evidence the precondition for the cage relying on camera perception; building the estimator exposed two genuine perception defects that pure host tests could not have caught (grass-as-white, curvature-blind linear fits) — exactly the kind of finding the oracle-validation step exists for.

### Impact

- Cage consumers on the camera track must run cage YAML ≥ 0.6.0; F-track behaviour is bit-identical (back-compat default).
- The E-training pilot (Stage E3) is unblocked: env camera mode + config exist. Known limitation recorded: estimator epsi MAE ≈ 0.16 rad clean (p95 0.35) — C-02 enforcement on the CV state will be noisier than on ground truth; to be observed in the pilot and, if spurious C-02/C-05 fires dominate, a deterministic temporal smoothing (EMA) is the candidate fix.

### Verification

`pytest` → **426 passed** (60 new). `python tools/check_traceability.py` → All checks PASSED, 0 warnings. `python tools/check_scenario_yaml.py` → 0 errors, 0 warnings (stub warnings gone). Oracle validation: `experiments/sim/runs/cv_estimator_val_20260610T181634Z/summary.json` (numbers above) with full repro metadata (git commit, world/centerline/cage hashes, camera model, estimator config).

---

## [10.06.2026] — E2: camera evidence baseline — pitched front camera, matte road materials, lane-line visibility verified in-sim

**Document(s) affected:** `src/cobraflex/urdf/my_robot_gazebo.urdf` + `my_robot_gazebo_mesh.urdf` (camera pitch), `scripts/compose_lane_circuit.py` (matte PBR material), `src/cobraflex/worlds/lane_following_oval{,_wet,_worn}.world` (regenerated), `tools/capture_camera_frames.py` + `tools/cam_evidence_session.sh` + `tools/reap_sim.sh` (new evidence tools), `experiments/sim/e_cam_visibility/` (frame evidence).
**Phase:** E2 (track 'E'; branch `e2e-camera`).
**Gate context:** GE2 prerequisite — the camera+world visual baseline every later E-artefact (CNN obs, CV lane-estimator) consumes. F-track unaffected (the F-policy is state-vector-based; world visuals do not enter its evidence).
**Author:** Samuel.

### Change

- **Front camera verified live** on the Ubuntu host: the existing `ZEDm Cam` sensor (640×480 RGB, 20 Hz, `camera/image_raw`, bridged in `gz_bridge.yaml`) publishes headless (`gui:=false`); frames captured at four canonical poses (spawn, curve entry s=1.5, mid-curve, back straight) and stored under `experiments/sim/e_cam_visibility/`.
- **Camera pitched down 0.25 rad** (both gazebo URDFs): flat-mounted, the R=0.80 m curve swept out of the FOV at curve entry (frames kept as evidence); pitched, the near road fills the lower frame at all four poses.
- **Matte road materials**: the composer's tile material gained `roughness 0.9 / metalness 0.0` — ogre2's PBR defaults rendered the tiles glossy, with bright specular lobes a white-line detector (or the CNN) would read as lane features. All three oval worlds regenerated from the composer (content-identical otherwise; the wet/worn files also lost their accidental CRLF endings). With matte asphalt the dashed separator and the white edge lines are crisply visible at every pose — the visibility precondition of docs/09 §10 is met and evidenced.
- New host tools: `tools/capture_camera_frames.py` (frame grabber), `tools/cam_evidence_session.sh` (launch + teleport + capture), `tools/reap_sim.sh` (orphan reaper).

### Rationale

docs/09 §10 ("verify the lane lines are actually visible to the camera") is the entry condition for the camera observation bridge and the D-43 CV lane-estimator; both the pitch and the matte fix came out of looking at actual frames rather than assuming the texture work sufficed.

### Impact

- The world files' hashes change; E-track runs record the new hashes. Frozen F-track run metadata is untouched (their recorded hashes remain valid for the commits they cite).
- `oval_centerline.yaml` regeneration verified byte-identical — no geometry change, no ODD impact (ROAD_LENGTH / KAPPA_MAX unchanged).
- Camera intrinsics baseline for the E-obs design: 640×480 @ 20 Hz, HFOV 1.396 rad, pitch 0.25 rad.

### Verification

`pytest` → 366 passed. `python tools/check_traceability.py` → All checks PASSED, 0 warnings. Evidence frames reviewed at the four poses for the flat (`spawn/...`), pitched (`pitch025_*`) and pitched+matte (`matte_*`) configurations.

---

## [10.06.2026] — F4: SR-006 closed on its own metric (D-39); SR-009/SR-010 blockers diagnosed

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/campaign_metrics.py`, `policy/tests/test_campaign_metrics.py`, `tools/sr006_smoothness.py` (new), `docs/DECISIONS.md` (D-39), `docs/07_traceability_matrix.md`, `docs/05_scenario_library.md`, `docs/08_odd_specification.md` (§12.3), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.2.5, §8.4–§8.7, appendix), `CLAUDE.md`.  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Pushed the three open SR-CL-B TBDs as far as possible without a Gazebo re-run, and
diagnosed precisely what each still needs:

- **SR-006 (actuator smoothness) → Satisfied (D-39).** Added a committed-steer
  per-cycle rate metric to `campaign_metrics` (`M-I5.steer_rate_max`,
  `steer_rate_max_smoothness`, `steer_rate_smoothness_ok`) and a dedicated analysis
  tool `tools/sr006_smoothness.py` (reads `cage_status.csv`, no Gazebo, precedent
  D-35). SR-006 is now scored **on its own metric** instead of inheriting the
  unrelated SC-PERT-01 fraction fail. The cage runs C-06 first (bounds the raw rate),
  then downstream safety rules (C-01/C-02/C-03/C-05) may legitimately exceed it; on
  the steps C-06 governs (no override), the committed rate holds at δ_max = 0.15 in
  **559/559** evaluable enforcement runs vs **67.6 %** in monitoring (worst 0.43) — a
  direct measure of C-06's value. **No cage defect:** every apparent excursion
  coincides with a downstream safety intervention.
- **SR-010 (SC-EDGE-05) — diagnosed, needs re-run.** The scenario as-run induced
  **zero rule co-activation** (0 interventions across 100 runs); the
  `parameterised_grid` initial conditions are not injected by the runner. So SR-010
  cannot be verified from these logs even with the two missing counters added — the
  scenario must first actually stress co-activation, then re-run.
- **SR-009 (SC-PERT-03) — diagnosed, needs re-run.** The multi-arm evaluator already
  exists (`criterion_eval.evaluate_labelled`); the stall-variant arm was never
  executed and the driver does not group the two arms. Needs the fine-tune + run +
  grouping.

Documentation synced to the executed campaign: `docs/05` (1100→1260 runs, seed 2024,
SATISFIED, open items), §8.2.5 (the in-ODD enforcement-vs-monitoring delta is
*degenerate* — M-S2 = 0 in both modes, no variance — so inference applies to the
frontier and SR-006 contrasts, not the in-ODD M-S2 delta), `docs/08` §12.3 (the
ODD-Spec carries the lone TBD-Q10 to F5; it is not promoted to v1.0 at G4).

### Rationale

"Do everything possible without a re-run." SR-006 needed no re-run — its evidence is
in the committed-steer trace already logged — so it is closed here on a defensible,
architecture-grounded operationalisation (smoothness subordinate to safety, D-39).
SR-009/SR-010 genuinely need the Ubuntu host (a fine-tuned stall policy; a runner
that injects grid ICs), so the honest deliverable is a precise diagnosis + the
pure-Python pieces that make the re-run productive, not speculative untested code.
The investigation also cleared a scare: the large committed-steer jumps are correct
downstream safety corrections, **not** a C-06 rate-limiter defect.

### Impact

- `campaign_report.json` per-SR SR-006 still reads `failed` (coarse `ALL` inheritance);
  re-pointing it to the metric in `run_campaign.aggregate_sr` is a flagged D-39
  follow-up. SR-006 is CL-B → **global verdict unchanged (`SATISFIED`)**.
- **Ubuntu re-run punch-list (before G4):** SC-EDGE-05 grid-IC injection + counters;
  SC-PERT-03 stall arm + arm grouping; then re-score SR-009/SR-010. Plus the QED
  metric decision (D-17/D-21).
- No H/SR/C/SC/M artefacts changed; no new orphans.

### Verification

`pytest` → 316 passed (2 new SR-006 metric tests). `python tools/check_traceability.py`
→ 8/8 constraints PASS, 0 warnings.

---

## [10.06.2026] — F4: Reconcile campaign aggregators on indeterminate verdicts (D-38)

**Document(s) affected:** `tools/run_campaign.py`, `policy/tests/test_run_campaign.py`, `policy/tests/test_verdict_aggregation.py`, `experiments/sim/campaign/campaign_report.json` (regenerated), `docs/DECISIONS.md` (D-38), `docs/07_traceability_matrix.md` (aggregator caveat → reconciliation note).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Reconciled the two campaign verdict aggregators so an *indeterminate* (`None`)
per-run verdict is handled identically by both. `tools/run_campaign.py` previously
counted `None` runs inside the pass-fraction denominator (`n_pass / n_total`),
collapsing "no evidence" into a fail; it now **excludes** them (`n_pass / n_evaluable`,
`None` if no evaluable run) and propagates `insufficient_evidence`, matching the
unit-tested D-29/D-30 spine `src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py`.

- `aggregate_scenario` returns a three-valued verdict with `n_fail`/`n_indeterminate`.
- `aggregate_sr` returns a `status` ∈ {satisfied, failed, insufficient_evidence,
  not_run} (a genuine failure dominates an indeterminate sibling).
- `global_verdict` distinguishes `NOT SATISFIED` (an SR-CL-A failed) from `INCOMPLETE`
  (an SR-CL-A under-evidenced).
- `campaign_report.json` **regenerated from the raw `campaign_runs.csv`** (the per-run
  `None`s were already logged) — **no Gazebo re-run**. SC-EDGE-05 / SC-PERT-03 now read
  `verdict: null`; **SR-009 / SR-010 move from `false` to `insufficient_evidence`**.
- Tests added for "all runs `None` → insufficient_evidence, not failed" and the
  failed-dominates-indeterminate precedence in both test suites. Decision recorded as
  **D-38**; the `docs/07` "Aggregator caveat" replaced by a reconciliation note.

### Rationale

A `false` verdict must mean a demonstrated safety violation, not an instrumentation
gap. The old `run_campaign.py` denominator mis-reported two known gaps (SC-EDGE-05's
predicate references operands absent from the run-record schema; SC-PERT-03's labelled
multi-arm criterion is not scorable in the single-run evaluator) as failures, dragging
SR-009/SR-010 to `false`. The spine already used three-valued logic to avoid exactly
this; the fix brings the runner into line rather than adding a third rule.

### Impact

**The global verdict is unchanged: `SATISFIED`, all 7 SR-CL-A satisfied (D-30 veto
clear).** Only the classification of three non-blocking **SR-CL-B** verdicts is
touched: SR-009 and SR-010 are now correctly `insufficient_evidence`; **SR-006 remains
`failed`** because it inherits the *genuine* SC-PERT-01 fraction fail (0.883 < 0.90) —
a separate per-metric re-aggregation issue, not a `None`. The `docs/07` matrix verdict
cells for SR-006/009/010 stay **TBD** (held open until the schema/evaluator gaps close
and the scenarios are re-scored). No H/SR/C/SC/M artefacts changed; no
`traceability_matrix.csv` rows.

### Verification

`python -m pytest` → 314 passed (incl. the new D-38 cases).
`python tools/check_traceability.py` → all checks PASSED, 0 warnings.
`campaign_report.json` re-validated: valid JSON, ASCII-clean, `global.verdict =
SATISFIED`, `n_runs = 1260`, `n_error = 0`.

---

## [10.06.2026] — F4: Sim-eval campaign closed; docs/07 verdicts filled

**Document(s) affected:** `docs/07_traceability_matrix.md`, `tools/traceability_matrix.csv`, `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.2.1, §8.2.4, §8.2.6, §8.3–§8.7, §8.8.1), `CLAUDE.md` (phase status).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

The verdict-bearing simulation campaign ran to completion: **1260 runs**, main
seed **2024** (D-36), every verdict-bearing scenario × {enforcement, monitoring}.
Roll-up committed at `experiments/sim/campaign/campaign_report.json` +
`campaign_runs.csv`; out-of-ODD frontier contrast at
`experiments/sim/campaign_frontier/frontier_contrast.json` (+ two figures).

- **`docs/07`** — the `Verdict` column moves from all-`TBD` to the sim verdicts.
  **Global verdict `SATISFIED`**: all 7 **SR-CL-A** (SR-001..005, SR-007, SR-008)
  satisfied with margin → D-30 veto not triggered. SR-011 (CL-B) also Satisfied.
  Three **SR-CL-B** verdicts held **TBD** by deliberate abstention (notes ¹²³):
  SR-006 (coarse `ALL` aggregation inherits the SC-PERT-01 σ=0.05 emergency-trip
  failures, M-I5 itself not breached), SR-009 and SR-010 (instrumentation gaps —
  SC-PERT-03 multi-arm meta-test and SC-EDGE-05 predicate operands are not in the
  single-run evaluator / run-record schema, so those runs are *indeterminate*,
  not failing).
- **`tools/traceability_matrix.csv`** — `verdict_sim` set to `satisfied` and
  `evidence_path` populated for the SR-001/002/003/004/005/007/008 rows; SR-006
  rows kept `tbd` with a pointer to the docs/07 note.
- **`manuscript` §8** — §8.3–§8.7 and §8.8.1 (marked `[COMPLETAR FASE 4]`) written
  from the campaign data; the inline `[COMPLETAR]` placeholders in §8.2.4 (D-29/D-30
  summary) and §8.2.6 (runner reference) resolved; §8.2.1 corrected to the realised
  design (main seed 2024 per D-36, RL controller; the earlier "≈1100 runs / N=5
  across all scenarios / PD axis" draft did not match the executed campaign).

### Rationale

The campaign is the evidence layer the traceability matrix was built to receive.
Recording the honest picture matters more than a clean pass: the central in-ODD
finding is that **M-S2 (boundary violation) = 0 in both modes everywhere**, i.e.
the constraint-respecting main policy never approaches the boundary inside the ODD,
so the cage is **latent** there (enforcement ≈ monitoring). The cage's protective
value is shown **out-of-ODD** by the D-35 frontier contrast: for the cage-dependent
seed 123 the cage removes **96–100 % of road-edge contacts** (M-S5) the bare policy
would incur (SC-FRONT-01/03/04/06), while the constraint-respecting seed 2024
recovers on its own (benefit ≈ 0) — the §7.5.3 bimodality realised at runtime.
The three TBDs are abstentions, not failures: collapsing an indeterminate verdict
to a fail (as `run_campaign.py` does) would overstate the result, so they are held
open until the evaluator / run-record schema gaps are closed and the scenarios
re-scored.

### Impact

- No H/SR/C/SC/M artefacts added or changed; no new orphans.
- **Open before G4:** close the three TBDs (SR-006 per-metric re-aggregation on
  M-I5; SR-009/SR-010 schema-gap fix in the run record + multi-arm scoring in the
  evaluator, then re-score SC-PERT-03 / SC-EDGE-05). Tracked as the remaining F4
  work in `CLAUDE.md`.
- `run_campaign.py`'s indeterminate→fail collapse vs `verdict_aggregation.py`'s
  indeterminate→`insufficient_evidence` is recorded as a caveat in docs/07; a
  reconciliation of the two aggregators is a candidate decision (D-NN) for G4.

### Verification

`python tools/check_traceability.py` → all 8 constraints PASS, 0 warnings (the
verdict column is free-text and not constraint-checked; structure unchanged).

---

## [09.06.2026] — E2: D-43 — cage on a dedicated vision lane-estimator (supersedes D-42); H-12 / SR-014 / SC-PERT-08

**Document(s) affected:** `docs/DECISIONS.md` (D-43; D-42 → SUPERSEDED), `docs/02` (H-10/H-11 reframe + new H-12), `docs/03` (SR-012/SR-013 reframe + new SR-014), `docs/04`, `docs/05` (SC-PERT-08 + reframe), `docs/07`, `docs/09` §10 (v0.4), `docs/10` §10; `docs/data/*.csv` (regenerated); `tools/traceability_matrix.csv`; `manuscript/chapters/chapter_04`, `chapter_05`; `scenarios/perturbed/sc_pert_08.yaml` (new stub); `policy/tests/test_verdict_aggregation.py` (count); `src/cobraflex_rl/cobraflex_rl/visual_domain_randomization.py` + test (new).  
**Phase:** E1 (track 'E'; branch `e2e-camera`).  
**Gate context:** E-design, before GE2. F-track unaffected.  
**Author:** Samuel.  

### Change

Re-architected the track-'E' cage perception after the design clarification that the system must drive on **any road with visible lane lines** from the camera (policy *and* cage), without an authored centerline:

- **D-43 (supersedes D-42).** The cage's `state` now comes from a **dedicated, deterministic CV lane-estimator** (separate from the policy's CNN), not from privileged ground truth. Ground truth is kept **in sim only** as the training reward and an oracle to validate the estimator. C-01..C-06 unchanged — only the state *source* changes. D-42 → SUPERSEDED by D-43.
- **Reframed H-10 / H-11 and SR-012 / SR-013** (`docs/02`, `docs/03`, `docs/04`, `docs/05`, `docs/07`, chapters 04/05): the cage now reads the camera (its own CV detector), so a camera fault is **common-cause** (blinds policy and cage alike); the residual safety is the **open-loop controlled stop** (SR-013/C-05, "no lines ⇒ stop").
- **New hazard H-12** (cage lane-misdetection: a confidently-wrong CV estimate → false envelope) + **SR-014** (estimator plausibility / temporal-consistency check + conservative fall-back to C-05) + **SC-PERT-08** stub (misleading-markings / false-lane test). Registers the failure mode the CV estimator introduces (impossible under D-42).
- **Training-world diversity decided: oval-first** (`docs/09` §10): first camera-policy prototype on the current oval with visible lines; world diversity added afterwards.
- Added the host-testable **visual domain-randomization sampler** (`visual_domain_randomization.py` + test) — the training-side mitigation of H-10 referenced by `docs/09` §10.

### Rationale

The generalisation goal requires the *whole* system to key on visible lines, so the cage cannot rely on an authored centerline. A separate **deterministic CV** estimator keeps the cage independent of the *learned policy* and auditable (a classical algorithm is inspectable). The honest cost — common-cause blindness and a new misdetection hazard — is registered explicitly (D-43 consequences, H-12) rather than hidden; the open-loop stop is the residual safeguard.

### Impact

- Shared registers extended: H-12, SR-014, SC-PERT-08 (stub). SR-CL-A count 9 → 10.
- **Deferred to Ubuntu:** the cage's CV lane-estimator node + plausibility/temporal-consistency check, the camera obs bridge, the runtime injectors, and CNN training. Sim ground truth validates the estimator (oracle).

### Verification

- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (12 hazards H-01..H-12; 14 SRs SR-001..SR-014; 22 scenarios incl. SC-PERT-08).
- `python tools/check_scenario_yaml.py` → PASSED, 5 stub warnings.
- `pytest` (root) → **352 passed**.

---

## [09.06.2026] — E2: manuscript — track 'E' notes in ch.3 / ch.5 / ch.7

**Document(s) affected:** `manuscript/chapters/chapter_03_methodology.md`, `chapter_05_architecture_and_cage.md`, `chapter_07_training_specification.md`.  
**Phase:** E0/E1 (track 'E'; branch `e2e-camera`).  
**Author:** Samuel.  

### Change

- **§3.5.1** records that **D-01 ("no end-to-end") is superseded by D-41** for track 'E', with the retained-modular-cage argument (A1/A2/A4 stay viable; D-42). Closes the §3.5.1 follow-up flagged in the scaffolding entry.
- **§5.2.3** ("Lo que la cage no es") adds the property *the cage does not depend on the policy's perception* — it runs on an independent state estimate (D-42), which keeps H-06 (cage state) distinct from H-11 (camera perception).
- **§7.2.1** notes the camera-observation variant (CNN; action and reward unchanged; cage on independent state; PPO/camera training deferred to Ubuntu), pointing to `docs/09` §10.

### Rationale

Keep the manuscript consistent with the E-track architectural decisions (D-41/D-42) recorded under `docs/`.

### Verification

Prose only; `tools/check_traceability.py` parses `docs/`, not the manuscript, so it is unaffected (still PASS). `pytest` unaffected (340 passed).

---

## [09.06.2026] — E2: E-design — camera env (docs/09 §10), reward unchanged (docs/10 §10), pure-Python perception modules

**Document(s) affected:** `docs/09`, `docs/10`; `src/cobraflex_rl/cobraflex_rl/visual_degradation.py` + `perception_health.py` (new); `policy/tests/test_visual_degradation.py` + `test_perception_health.py` (new).  
**Phase:** E0/E1 (track 'E' design; branch `e2e-camera`).  
**Gate context:** E-design, before GE1. F-track unaffected.  
**Author:** Samuel.  

### Change

- **docs/09 §10** (v0.3): the E-track environment changes **only the observation** — the front-camera image (CNN policy) replaces the 6-dim state vector. Action, reward, cage (on the independent ground-truth state, D-42) and episode logic are unchanged; supersedes ED-1's image-obs rejection for track 'E'. Visual degradations act on the observation; perception loss raises C-05 Trigger 8.
- **docs/10 §10:** the reward is **unchanged** for track 'E' — it is observation-agnostic (computed on ground-truth state + progress + raw steering delta).
- **New host-testable pure modules** (numpy / stdlib only, no ROS): `visual_degradation.py` (glare / low-light / motion-blur primitives → SC-PERT-04..06 / SR-012 / H-10) and `perception_health.py` (`PerceptionHealthMonitor` raising the C-05 perception-health trigger → SC-PERT-07 / SR-013 / H-11), each with a unit-test file under `policy/tests/`.
- **`tools/traceability_matrix.csv` reconciled** (the hand-maintained granular matrix flagged as stale in the scaffolding entry): it now covers every `H→SR→C→SC→M` chain, adding the previously-missing H-08/H-09/SR-011 rows and the new track-'E' H-10/H-11 rows. Aligns the CSV with `docs/07`.

### Rationale

The E-track changes only the policy's input; the reward and cage are observation-agnostic / on the independent state, so they carry over (the minimal-delta point of D-42). The two pure modules are the host-doable, unit-testable kernels of the camera stressors; the Gazebo camera sensor, the observation bridge, the runtime injectors and the ROS perception-health node are the Ubuntu part.

### Impact

- No change to F-track artefacts or the H→SR→C→SC→M chain. SC-PERT-04..07 remain stubs.
- **Deferred to Ubuntu:** Gazebo front-camera sensor (URDF/SDF) + observation bridge in `gazebo_lane_env`, CNN/PPO training, runtime degradation/loss injectors, the ROS perception-health supervisor node.

### Verification

- `pytest` (root) → **340 passed** (33 new across `test_visual_degradation.py` + `test_perception_health.py`).
- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings**.

---

## [09.06.2026] — E2: Track 'E' scaffolding (end-to-end front-camera) — D-41/D-42, H-10/H-11, SR-012/013, SC-PERT-04..07

**Document(s) affected:** `docs/00`, `docs/01`, `docs/02`, `docs/03`, `docs/04`, `docs/05`, `docs/07`, `docs/DECISIONS.md`; `docs/data/hazard_register.csv` + `docs/data/safety_requirements.csv` (regenerated); `manuscript/chapters/chapter_04_*`; `scenarios/perturbed/sc_pert_04..07.yaml` (new stubs); `policy/tests/test_verdict_aggregation.py` (count).  
**Phase:** E0 (parallel track; branch `e2e-camera`).  
**Gate context:** track entry, before GE0. The main F-track (F4 → G4) is unaffected.  
**Author:** Samuel.  

### Change

Opened the parallel **track 'E'** for an end-to-end front-camera lane-following variant and scaffolded its left-arm artefacts (HARA → SRS → Cage → scenarios):

- **Decisions:** D-41 (open track 'E'; phases `E0..E6` / gates `GE0..GE6`; commit prefix `E2:`; **supersedes D-01**) and D-42 (the cage stays on an *independent* state estimate, not the camera). D-01 status → SUPERSEDED by D-41.
- **Numbering:** E-phase/gate scheme added to `docs/01`; "Parallel track E" section added to `docs/00`.
- **Hazards:** H-10 (lane misperception under degraded visual input) and H-11 (loss of valid lane perception) in `docs/02` + machine-readable table + STPA scope addendum.
- **SRs:** SR-012 (lane-keeping under degraded visual input → C-01/C-02/C-03 + training) and SR-013 (safe degradation on loss of valid perception → C-05 via a perception-health supervisor) in `docs/03` + table.
- **Cage:** `docs/04` cage-independence note (D-42) and C-05 Trigger 8 (perception-health, deferred). C-01..C-06 reused unchanged — **no new cage rule**.
- **Scenarios:** SC-PERT-04..07 (glare, low-light, motion-blur, occlusion/perception-loss) documented in `docs/05` + **stub** YAMLs under `scenarios/perturbed/` (reuse the PERT family — no schema/`RX_SC` change).
- **Matrix / manuscript:** H-10/H-11 rows added to `docs/07`; `chapter_04` hazard/SR tables mirrored.

### Rationale

The camera→action variant is a second instantiation of the SE4AI method on a harder perception problem and a full new left-arm cycle, so it is isolated on its own branch + phase numbering with the F-track evidence frozen. The supersession of D-01 is safe because the **modular cage is retained** (D-42): pixels enter the policy, never the safety envelope, so framework adaptations A1/A2/A4 stay viable. The new hazards are functional sensor/environment perception failures — narrower than D-31's still-excluded non-functional AI families — and the cage's independence keeps H-06 (cage state) distinct from H-11 (camera perception).

### Impact

- Shared global ID space extended: H-10/H-11, SR-012/SR-013, SC-PERT-04..07. CSVs regenerated via `tools/sync_hazard_register.py` + `tools/sync_safety_requirements.py`.
- `policy/tests/test_verdict_aggregation.py` SR-CL-A count updated 7 → 9 (the two new track-'E' SRs are SR-CL-A).
- SC-PERT-04..07 are stubs (skipped by `run_campaign.build_matrix`), so the F-track verdict-bearing campaign budget is unchanged.
- **Deferred to later E-phases:** camera observation / CNN env design (`docs/09`), reward (`docs/10`), Gazebo camera sensor + perception node + perception-health supervisor, PPO retraining, un-stubbing SC-PERT-04..07.
- **Follow-ups pending:** manuscript §3.5.1 (record the D-01 supersession + retained-cage argument); `tools/traceability_matrix.csv` (hand-maintained granular matrix) left unchanged — already partial (missing H-08/H-09) — track-E rows deferred to a matrix-reconciliation pass.

### Verification

- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (11 hazards H-01..H-11; 13 SRs SR-001..SR-013; 21 scenarios incl. SC-PERT-04..07; constraints 1–8 OK).
- `python tools/check_scenario_yaml.py` → PASSED, 4 warnings (SC-PERT-04..07 explicit stubs).
- `pytest` (root) → **307 passed**.

---

## [08.06.2026] — F4: Anticipated defense questions added to docs 00–08

**Document(s) affected:** `docs/00`–`docs/08` (new "Anticipated defense questions" section in each; `docs/08` as new §13).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added an **"Anticipated defense questions"** section (the format already used in
`docs/09` and `docs/10`) to each of the nine numbered engineering documents
`docs/00`–`docs/08`. Each section is six bold Q&A pairs anticipating the
committee's most probing questions on that document, with answers that cite the
relevant IDs, decisions (D-03, D-11, D-25, D-28/29/30, D-34, D-35, D-37),
sections and evidence, and that surface the known open points honestly (e.g. the
SR-010 Trigger 7 deferral, the 10 Hz vs 20 Hz cadence mismatch, the ODD-3/4
coverage gaps, the 5↔6 observation-dimension reconciliation). Placed before each
document's `## Change log`; in `docs/08` (which uses numbered sections) appended
as `## 13.` before the end marker.

### Rationale

`docs/09` and `docs/10` carry a defense-questions bank that consolidates the
*why* of each design decision in viva-ready form; extending it to the rest of the
engineering documents gives the whole `docs/` set a uniform, defensible closing
section for the thesis defense. Scope confirmed with the author: numbered
engineering specs only (`00`–`08`); the process registries `CHANGELOG.md` and
`DECISIONS.md` were deliberately left out as a poor genre fit.

### Impact

Prose-only addition. No H / SR / C / SC / M identifier, parameter, threshold, ODD
value, or cage constant changes; no `traceability_matrix.csv` rows. The new text
*cites* existing IDs but defines none, so coverage is unaffected.

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: D-37 — single-world ODD reconciliation (docs/08 §12)

**Document(s) affected:** `docs/08_odd_specification.md` (new §12, version 0.5→0.6, change-log row); `docs/DECISIONS.md` (new D-37; decision-index row; header `Status:` comment).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added **D-37** and `docs/08` §12 "F4 evaluation realisation on a single world". §12 records
that the F4 sim campaign runs every scenario on the single oval world (Option A, `docs/05`
Track-mapping) at one fixed-speed `ACT_DIM=1` operating point (0.2 m/s, 6-dim obs), and
declares the ODD coverage: ODD-1/2 covered (geometry/obs caveats), ODD-3 partial (curve
geometry exercised, 2-dim speed envelope `v_max(κ)` not), ODD-4 not exercised (no
adverse-curvy scenario). ODD-spec version bumped 0.5 → 0.6.

### Rationale

The ODD-spec stratifies four domains across two worlds (straight for ODD-1/2, oval for
ODD-3/4) with a 2-dim speed-adaptive action for ODD-3/4. The F4 campaign collapses this to
one world + one fixed-speed steering-only operating point, so the spec no longer literally
describes what is evaluated. Per `docs/08`'s own convention (numerical authority flows
spec → evidence), the parameters are **not** rewritten; §12 declares the evaluated subset
and its gaps — the Phase-4 analogue of D-11's bounded validation. Surfaced while assessing
how to handle `docs/08` given the single-map evaluation.

### Impact

No ODD parameter, SR threshold, or cage constant changes; no H/SR/C/SC/M artefacts; no
`traceability_matrix.csv` rows. **Follow-up:** align the manuscript Cap. 8 ODD-coverage
claim (ODD-1/2 covered, ODD-3 partial, ODD-4 deferred) and report the gap in Limitations.
A variable-speed `ACT_DIM=2` policy + an adverse-curvy scenario are future work (F5+).

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: D-36 — seed policy for the verdict / frontier campaigns

**Document(s) affected:** `docs/DECISIONS.md` (new D-36; decision-index row; header `Status:` comment).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added decision **D-36** fixing which policy seeds enter each F4 campaign: the D-29/D-30
verdict-bearing campaign certifies the G3-selected main policy **seed 2024** only, while
the cage-dependent **seed 123** (58.8 % cage, §7.5.3) appears solely in the D-35 frontier
cage-efficacy contrast (and, optionally, a separately-reported robustness sweep with its
own `--out`). Updated the decision index and the header status comment to list D-36.

### Rationale

`aggregate_campaign` (`tools/run_campaign.py`) groups per-run outcomes by
`(scenario, mode)` and pools all seeds into one `fraction_pass`; running seed 123 inside
the verdict campaign would average the deliberately cage-dependent policy into the
per-scenario verdict and could veto an SR-CL-A (D-30) on the basis of a policy not chosen
for delivery. Surfaced during the 08.06 campaign-readiness review.

### Impact

No H/SR/C/SC/M artefacts and no `traceability_matrix.csv` rows. Operational: the
verdict-bearing run uses `--seeds 2024 --out experiments/sim/campaign`; the frontier run
uses `--seeds 2024,123 --reps 25 --out experiments/sim/campaign_frontier` (realised budget
6 × 25 × 2 modes × 2 seeds = 600 runs). Both still pending on the Ubuntu+Jazzy host.

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: Runtime perturbation injection wired (SC-PERT-01/02, SC-EDGE-03)

**Document(s) affected:**
New: `src/cobraflex_rl/cobraflex_rl/scenario_perturbations.py`,
`policy/tests/test_scenario_perturbations.py`.
Modified: `…/scenario_runner.py`, `…/gazebo_lane_env.py`, `…/eval_policy.py`,
`policy/tests/test_scenario_runner.py`, `scenarios/_schema.yaml`, `experiments/README.md`.
**Phase:** F4.
**Gate context:** before G4.
**Author:** Samuel.

### Change

- **New pure module `scenario_perturbations.py`** — resolves a scenario `perturbations:` block +
  rep index into a concrete, level-resolved `ScenarioPerturbation`: `observation_noise` (Gaussian
  on the perceived lateral offset, SC-PERT-01), `actuation_latency` (command delay in control
  steps, SC-PERT-02), `throttle_override` (timed pulse fed to C-04, SC-EDGE-03). Multi-level types
  pick their level by `rep % n_levels` (the YAML's "20 runs per level"). ROS-free, unit-tested.
- **`scenario_runner.derive_run_config`** now carries the resolved `perturbation` and a per-rep
  `env_seed` on `RunConfig`.
- **`gazebo_lane_env`** applies the three perturbations: the *perceived* lateral offset
  (true + noise) feeds the policy observation **and** the cage state, while metrics / reward /
  termination stay on the *true* pose (Ch.8 §8.2.3); a `deque` buffers `/cmd_vel` for actuation
  latency; the throttle pulse substitutes the nominal throttle into the cage input.
- **`eval_policy`** passes the perturbation through `reset(options=…)`, seeds the env reset with
  the per-rep `env_seed` (independent yet reproducible obs-noise per rep), and records the level
  in `summary["perturbation"]`.

### Rationale

The F4 verdict campaign's adverse arm for SR-001/003/004/007 (and the SR-009 negative test)
depends on SC-PERT-01/02 and SC-EDGE-03, but the executor previously ignored the `perturbations:`
block entirely — those runs would have executed as plain nominal runs and reported a misleading
PASS (the 08.06 readiness review). This wires the three runtime stressors so the perturbed
scenarios test what they claim.

### Impact

- **Not yet Gazebo-validated.** The pure logic is unit-tested (28 cases) but the env application
  runs only on the Ubuntu+Jazzy host — smoke-test per `experiments/README.md` step 3b before
  trusting the perturbed verdicts.
- **SC-EDGE-03 caveat:** the fixed-speed actuation (`target_speed_from_throttle` caps speed at
  `fixed_speed` ≈ 0.2 m/s < `v_max` 0.5 m/s) limits the achievable over-speed, so the override
  reaches C-04 but exercises little real speed excess; a full SR-004 test needs variable-speed
  actuation (flagged in the runbook).
- **Still unwired (different mechanisms):** SC-EDGE-05 (initial-condition grid expansion) and
  SC-PERT-03 (pre-run stall-variant checkpoint). No H/SR/C/SC/M ids added or changed.

### Verification

`python -m pytest policy/tests/test_scenario_perturbations.py policy/tests/test_scenario_runner.py`
→ 28 passed. `py_compile` of `scenario_perturbations` / `scenario_runner` / `gazebo_lane_env` /
`eval_policy` → clean. `python tools/check_traceability.py` → unaffected (All checks PASSED, 0 warnings).

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
