# True-position capture session — 2026-08-31, rectified, camera only, D-78

The session D-78 prepared, executed the same afternoon. Camera only: `csi_camera_node`
(`capture_fps:=30`, measured **19.38 Hz**, gap median 50 ms, 45.5 % of a core), no policy, no cage,
no ZED, no launch file. Rectified with `experiments/calibration/M6_results.json`, `near_secant` /
gain 1.0 — the deployed configuration since 26.08. Labels computed inline by `CvLaneEstimator` at its
shipped thresholds (`white_sat_max` 30).

Ground truth: 4 numbered floor stations at tape-measured centreline arc-lengths (0 / 4.82 / 9.64 /
14.46 m of the 19.28 m circuit) plus a fifth press back at station 1 to close the lap, and a **fixed
pointer on the chassis at the camera's longitudinal station**, read against the centre of a painted
lane line. No chalk was available, so the offset was held against the pointer rather than a floor
guide — which removes one transfer error, since a chalk line would itself have been measured off the
same painted lines. Lane lines are 250 mm apart centre-to-centre (M-7 §2), so centred = 125 mm.

Sign: **+ = car LEFT of the lane centreline**, as everywhere else.

`--no-frames` throughout: 2400 rows cost ~300 kB, against ~600 MB with PNGs. The eMMC pressure that
crashed the Jetson on 18.08 did not recur, and the whole score comes from the CSV.

## Result 1 — the acceptance criterion of D-78 FAILS on every lap: κ over-reads ~2×

| lap | true ey | frames | paired | `single_line` | usable¹ | arc | ∫\|κ\|ds / (laps·2π) | same, right-pair only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `truepos_000` | 0 | 2704 | 55.4 % | 44.1 % | 15.2 % | 18.04 m | **2.37** | 2.22 |
| `truepos_000_ctrl` | 0 | 2069 | 70.0 % | 28.9 % | 21.8 % | 18.51 m | **1.97** | 1.90 |
| `truepos_000_ctrl_3` | 0 | 2459 | 68.2 % | 31.3 % | 35.8 % | 16.19 m | **2.01** | 1.85 |
| `truepos_m065` | −65 mm | 2415 | 46.6 % | 44.9 % | 25.7 % | 15.56 m | **2.25** | 1.78 |

¹ usable = plausible lane width (|w − 250| ≤ 40 mm) **and** |ey − true| ≤ 40 mm.

D-78 fixed the acceptance band at **0.75–1.35** in advance. Four laps land at **1.97–2.37**, and
restricting to right-pair frames only moves it to **1.78–2.22** — so `κ` still over-reads and, per
D-75, **C-04 stays un-armable**. This is the first measurement of the over-read that owes nothing to
odometry, to the policy or to the cage: the arc length came off the floor with a tape.

D-75 estimated ~3× from driving logs (2.92–3.04× on lap02/lap04). The independent figure here is
**~2×**, i.e. the same defect, somewhat smaller once the odometry is out of the chain.

Offset dependence, which D-76 suspected: from 0 to −65 mm, paired frames fall 68.2 → 46.6 % and the
ratio rises 2.01 → 2.25. **The over-read's tail grows with offset. Confirmed.**

## Result 2 — the operator's shadow was a real confound, and it explains a third of it

`truepos_000` was pushed with the operator walking alongside at 0.13 m/s. The two `ctrl` laps were
pushed from outside the lane so no shadow fell on the lines. Same offset, same circuit, 40 min apart:

| | with operator alongside | shadow-free (mean of 2) |
| --- | --- | --- |
| paired | 55.4 % | **69.1 %** |
| `single_line` | 44.1 % | **30.1 %** |
| usable | 15.2 % | **28.8 %** |
| \|ey\| error on right-pair frames | 54.6 mm | **31.9 mm** (ctrl_3) |
| \|ey\| error p95 | 213 mm | **91 mm** (ctrl_3) |
| ratio κ | 2.37 | **1.97 / 2.01** |

Half the offset error and a third of the pairing failures in the first lap were **the operator**.
Every hand-pushed capture protocol in this project inherits this, and it leaves a caveat on the
18.08 `circuit_export` dataset (1521 frames, 95.3 % paired, also hand-swept — unrectified, different
hour, so not directly comparable, but no longer above suspicion).

**Nothing else in this note is affected by it**: the shadow-free laps are the ones the conclusions
rest on.

## Result 3 — it is the PLACE, not the motion. Four parked probes settle it

Every previous single-pose measurement in this repo — the 31.08 sweep, every `lanecheck` — was taken
at the start of the straight, which is also where each lap's fifth segment sits. That segment is
excellent; the moving segments are not. Motion and location were confounded, so the car was parked
**inside the bad stretches** at true ey = 0 and held still for 20 s:

| parked probe | n | paired | right pair | ey mean | sd | span | error | mean \|κ\| |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `parked_seg23_a` | 370 | **17.3 %** | 21.9 % | +7.9 mm | 84.3 | **711 mm** | 50.5 mm | 0.08 |
| `parked_seg23_b` | 273 | **0.0 %** | — | — | — | — | **blind** | — |
| `parked_seg34_a` | 314 | 99.4 % | 54.5 % | **+43.7 mm** | 14.0 | 46 mm | 43.7 mm | **0.88** |
| `parked_seg34_b` | 231 | 100 % | 91.3 % | **−39.7 mm** | **3.1** | 13 mm | 39.7 mm | 0.14 |
| start straight, ey = 0 | 524 | 92.7 % | 85.4 % | −4.8 mm | 38.0 | — | **15.9 mm** | 0.08 |
| start straight, ey = −65 | 448 | 96.7 % | 98.2 % | −59.1 mm | 5.9 | — | **7.2 mm** | 0.03 |

Parked in the bad places is as bad as moving through them, or worse. **The variable is where the car
is, not what it is doing** — and the one location every earlier conclusion came from is the
estimator's best point by a wide margin. This is precisely the limitation `SWEEP_NOTE.md` declared
about itself ("One location… whether the right-side instability generalises around the circuit is NOT
established here"), now measured.

Note `parked_seg34_b`: **−39.7 mm wrong with sd 3.1 mm**, on a stationary car, with a plausible
279 mm width and `/perception_invalid` never firing. And `parked_seg34_a`: mean \|κ\| **0.88 m⁻¹**
while **standing still**.

## Result 4 — the mechanism is candidate GENERATION, not pair selection

`line_c0_m` records the ground-frame intercept of *every* detected line, so each probe's failure can
be read directly. For a car at true 0, the correct pair is ≈ ±125 mm.

* **`parked_seg23_b`** sees **exactly one line** in 273/273 frames (`n_lines = 1`, intercepts
  −150/−100 mm). There is nothing to pair. A **detection** failure, not a selection one.
* **`parked_seg23_a`** sees three lines at ≈ **−200, −150, +250 mm**. The first two are 50 mm apart —
  **the two edges of one painted stripe**. No available pair has a plausible separation (50, 400,
  450 mm), so the estimator correctly refuses: `single_line` in 306/370 frames. Correct behaviour on
  bad candidates.
* **`parked_seg34_a`** pairs ≈ (−200, +100) → width **300.6 mm**, midpoint displaced ≈ +50 → reports
  **+43.7 mm**. It has taken the **outer edge** of a stripe instead of its centre.
* **`parked_seg34_b`** pairs ≈ (−100, +200) → width **279.2 mm**, midpoint displaced ≈ −50 → reports
  **−39.7 mm**, rock-steady.

So at these locations the candidate set is not "the two stripe centres": it is stripe *edges*,
adjacent markings, or a single stripe. The pair that survives has a plausible-looking width
(279–301 mm) and a midpoint displaced 40–50 mm.

**This inverts the obvious fix.** A temporal continuity prior on pair selection — the first thing one
would add for D-76 — would track the wrong pair happily: `parked_seg34_b` proves the wrong pair is
stable to **3.1 mm**. The widening has to act on line extraction (stripe edge vs stripe centre,
threshold behaviour at these spots), not on the tie-break.

## Result 5 — no stability gate can catch this, by construction

`parked_seg34_b` is 39.7 mm wrong with sd 3.1 mm and span 13.3 mm. The old `lanecheck` gate
(`sd_ey ≤ 10 mm`) **passes** it comfortably; the span gate added on 31.08 (`≤ 12 mm`) **fails** it by
1.3 mm — a coin flip. Neither detects a *bias*, because no dispersion statistic can. The only gate
that catches it is `preflight_deploy.py lanecheck --true-ey`, and it must be run **at more than one
location**. The next-steps item "lanecheck at −60 and −100 mm" is necessary but not sufficient as
written: at the start of the straight it will keep passing.

## What this session did NOT do

* **No `verdict_phys`.** The policy never ran. Nothing here re-scores G4, the D-69 verdict of record,
  or any hazard, SR, cage rule, scenario or metric. Posterior evidence, as all of Phase 5 is.
* **`+60`, `−100` and `+100` laps are still owed** (D-78's full offset matrix). The offset dependence
  is established in one direction only.
* **No cause named for the bad places.** What is physically different at those four spots — stripe
  width, a mat join, the adjacent red carriageway entering frame, local lighting — was not inspected;
  the session ran out of time. That inspection is cheap and is the next thing worth doing.
* **The per-segment map does not reproduce.** Across the three offset-0 laps only two things repeat:
  the 2→3 stretch is always poor (paired 50.2 / 51.4 / 46.7 %, error 58.5 / 57.0 / 79.3 mm) and the
  start straight is always good. Segments 1, 3 and 4 swing (e.g. 3→4: 75.4 / 98.6 / 70.7 % paired).
  An early reading of lap 1 called 3→4 a located defect; three laps do not support that.

## Raw data

`truepos_000/`, `truepos_000_ctrl/`, `truepos_000_ctrl_3/`, `truepos_m065/`,
`parked_seg23_{a,b}/`, `parked_seg34_{a,b}/` — each `labels.csv` (every frame, including unpaired and
bad-width, per D-78) plus `rejects.csv`. `truepos_000_ctrl_2/` is an aborted attempt with no station
pressed and carries no usable data.

`truepos_m065` was recorded with `--true-ey -0.060` while the pointer was held at ≈ −65 mm; the
`true_ey_m` column was rewritten to `-0.06500` and the directory renamed from `truepos_m060` before
scoring, so the reported errors are against the offset actually held.
