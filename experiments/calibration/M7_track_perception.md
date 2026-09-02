# M-7 — First perception + policy measurement on the physical lane circuit

**Date:** 18.08.2026 · **Phase:** 5 (physical deployment) · **Platform:** `admit14-cobraflex`
(Jetson, L4T R36.4.7, ROS 2 Humble) · **Track:** physical lane circuit, HS Esslingen hall
**Related:** [M-6](M6_camera_hfov.md) · [docs/17](../../docs/17_physical_deployment.md) ·
[docs/12](../../docs/12_cv_lane_keeper.md) · D-71

---

## 0. What this measurement is for

M-6 measured the *camera* on a bench: `fx = 395.93 px`, effective HFOV **77.89°** (not the
assumed 90°), mount pitch 17.84°. It then **propagated** that model through the D-43
estimator's construction and predicted that the reported `ey` would be `0.72 ×` the true one,
i.e. that C-01/C-05 would fire late. That propagation was never checked against a real lane.

M-7 is that check, plus the first end-to-end run of the deployed chain on the track. It ran
with the wheels on the ground, on the real circuit, with the 2-D PPO 550k trunk checkpoint
(`ppo_gz2d_cap022_1M_2024_550000_steps.zip`, hash `0d4492461b24efce…`).

**Headline, as measured on 18.08 (read the banner below before using any of it): the D-43
estimator reads lane *width* correctly (within 3 mm of a ruler) but under-reads lateral
*offset* by a factor of 0.68–0.83 with a ~10 mm bias — measured hands-off against a tape,
robust to every filtering (§4). C-01 therefore fires at a true 207–241 mm rather than 160, and
its pairing additionally collapses beyond roughly ±55 mm of offset (§3b). Both defects sit
inside the band where C-01 and C-05 act. The trunk camera policy does not transfer. The cage
contained it anyway, and separately rejected a real odometry fault.**

> **Both offset defects in that headline are measured on the UNRECTIFIED path and do NOT
> reproduce once rectified (31.08.2026) — see the banner at §4 before using any number
> from this document to tune the cage.** Rectified, the same nine-point sweep gives scale
> **1.058 / 0.991 with no intercept**, so C-01 fires at a true **151/158 mm** with ~100 mm
> of margin. The prescription this document made — *undistort, do not re-parameterise* — is
> exactly what that vindicates, so the finding stands even though its numbers do not.
>
> **What stands unchanged:** the lane-*width* result, the heading-noise comparison between fit
> modes, the **§5 yaw calibration** and the **§3 method lesson**. Two further caveats added
> later: the repeatability spread of §4 did **not** go away — it is the first sighting of what
> D-79 isolated as **place-dependence** (docs/17 §12) — and every measurement in this document
> was taken at the **start of the straight**, which D-79 established is the estimator's *best*
> point on the circuit. Their content stands; their generalisation to the whole track does not.

**Second headline, methodological:** three conclusions drawn from a stationary rig at one spot
were all overturned by two minutes of recorded circuit — see §2 before reading anything else.

## 1. Track geometry (operator measurement, ruler)

| Quantity | Value |
| --- | --- |
| Total width, outer edge to outer edge | 0.51 m |
| Lane, inner edge of outer line to the centre line | 0.25 m |
| Line thickness | 0.01 m |
| Centre line | dashed, one lane each side |
| Line **centre-to-centre** separation (what the estimator fits) | **0.250 m** |

This is essentially the design track: `generate_complex_track.py` uses
`ROAD_WIDTH_M = 0.52` and `LANE_USEFUL_M = 0.245`, with a dashed centreline of 10 cm mark +
10 cm gap. `n_lines = 3` in the camera view is therefore expected, not an anomaly.

## 2. Method warning: three of this session's conclusions were single-pose artefacts

Read this before §3–§4. The session first characterised perception with the car **stationary at
one spot**, and drew three conclusions from it. A 2-minute recording of the **whole circuit**
(`experiments/physical/bags/circuit_20260818T140357Z`, 1521 frames, replayed through the
estimator offline) overturned all three:

| Single-pose conclusion | Circuit measurement | Verdict |
| --- | --- | --- |
| `white_sat_max` must go 30 → 45; at 30 the estimator pairs **0/60** | at 30 it pairs **95.4 %**, at 45 only **69.4 %** | **retracted** — 30 is correct |
| lane-width read is 0–12 % low, pose-dependent | mean **252.9 mm** against a true 250 → **+1.2 %** | **retracted** — the read is accurate |
| `joint_pair_quadratic`/1.6 carries **+17.28° of heading bias** | mean **+0.04°** over the circuit | **retracted** — no general bias |

The single-pose observations were not measurement errors — at that spot the lane lines really did
sit at S 36…50 and really were rejected at `S ≤ 30`. They simply do not generalise, and each one
pointed at a fix that makes the rest of the circuit worse. **A stationary rig characterises a
location, not a track.** Everything below is the circuit-wide measurement; the single-pose
numbers are kept only where they explain a mechanism.

## 3. Illuminant / colour gate — the D-43 default is correct

`CvLaneEstimatorConfig` gates a white-marking pixel on `white_sat_max` and `white_val_min` in
HSV. Swept over the circuit recording (761 frames, every 2nd, `joint_pair_quadratic`/1.6):

| `white_sat_max` | paired | mean width | sd | \|err\| vs 250 mm | frames near the 145 mm floor | worst segment |
| --- | --- | --- | --- | --- | --- | --- |
| 25 | 96.5 % | 269.4 mm | 37.8 | 19.4 mm | 2.0 % | 86.7 % |
| **30** (D-43 default) | **95.4 %** | **252.9 mm** | 41.7 | **2.9 mm** | **2.3 %** | 86.7 % |
| 35 | 96.5 % | 222.0 mm | 41.4 | 28.0 mm | 5.0 % | 90.8 % |
| 40 | 90.9 % | 223.5 mm | 58.2 | 26.5 mm | 17.5 % | 78.6 % |
| 50 | 89.5 % | 186.4 mm | 46.6 | 63.6 mm | 37.2 % | 74.2 % |

**`white_sat_max = 30` wins on every column that matters**, and reads the lane width to within
**2.9 mm of a ruler**. Loosening the gate admits road surface and clutter, which corrupts the
line fits and manufactures spuriously narrow pairs: at 50, 37 % of frames sit within 15 mm of the
`lane_width_tol_m` rejection floor, against 2.3 % at 30.

**Why one location failed anyway.** At the pose used for the stationary work, the lane lines
measured **V 228…255 with S 36…50** — bright by a wide margin, rejected on saturation — and the
estimator fell through to `_single_line_estimate` on background clutter. That is a real, local
failure of a global threshold, and it is the mechanism to carry forward: the estimator has
locations where a single HSV gate does not separate line from surface, and **the fix is not a
looser gate**. Candidate directions, none tested: a per-row adaptive threshold (the road runs
V p50 112 at far rows and 80 at near ones, so no single `white_val_min` fits both), or exposure
control on the camera.

The two parameters are exposed regardless (node parameters and launch arguments, `-1` = not set,
defaults bit-identical) — an illuminant knob is the right thing for a physical platform to have.
**Its value stays at the default.**

## 3b. Pairing succeeds where the cage does not need it, and fails where it does

`white_sat_max = 30` pairs 95.4 % of circuit frames (§3) — but that recording spent 90 % of its
time within ±72 mm of lane centre. Sweeping the car deliberately across the lane exposes a
dependence the circuit average hides.

Two hand-swept sessions, 2639 evaluated frames, scored on whether the measured lane width lands
within 40 mm of the ruler's 250 mm — i.e. whether the estimator paired *the right two lines*, not
merely *two lines*:

| \|ey\| band | share rejected on width (`lane_A`) | width-sane share (`lane_00_firstpass`) |
| --- | --- | --- |
| 0–30 mm | 18 % | 92 % (0–40 band) |
| 30–55 mm | 30 % | — |
| 55–80 mm | **87 %** | 29 % (40–80 band) |
| 80–120 mm | **95 %** | **6 %** |

The failure is systematic, not noisy: in the 80–120 band the measured width sits at
**183.8 mm with sd 23.9** while `n_lines` is predominantly **4** — both lanes in view, and a
wrong pair chosen. It is **not** explained by heading: `lane_width` is
`(left.c0 − right.c0)·cos(heading)`, measured headings there are 2–9°, and dividing the width
back out by `cos` moves the sane share from 6 % to 7 %.

**The consequence is a safety one, not a dataset one.** The estimator that feeds C-01 (`d_max`
160 mm) and C-05 (`d_warning` 120 mm) is reliable only within roughly **±55 mm** of lane centre
on this track — less than half the lane half-width, and entirely inside the region where those
rules never act. Where the cage needs a trustworthy lateral measurement, it does not have one.

**Pairing rate is not a sufficient health metric.** The estimator pairs; the pair is wrong. Only
comparing the measured width against a ruler catches it, which is why
`tools/record_lane_dataset.py` gates on width and logs every rejection to `rejects.csv`.

### Confounder, stated because it is not resolved

Both sessions swept the car **by hand**. Sliding it may also tilt it, and the IPM is
pitch-sensitive — `camera_geometry` reads a constant 0.30 rad, not the TF. Measured `epsi`
sd is only 4.4°, so heading was controlled, but pitch and camera height are not observable from
these logs. The `|ey|` dependence is strong and monotonic across 1434 frames of a single
session, but it is confounded with however the chassis was handled.

**The clean test, not yet run:** place the car on the ground, hands off, at tape-measured
offsets (0, ±40, ±60, ±80, ±100 mm), and sample each for 10 s with
`tools/preflight_deploy.py lanecheck` or `tools/lane_probe.py`. That separates offset from
handling. Until it is run, treat the ±55 mm figure as indicative rather than established — the
§2 lesson applies to this measurement too.

## 4. The `ey` transfer function, measured hands-off — M-6's under-read is REINSTATED

> **SUPERSEDED FOR THE DEPLOYED CONFIGURATION (31.08.2026). Do not re-tune C-01 or C-05
> from the numbers in this section.** Everything below was measured on the **unrectified**
> path — rectification was only demonstrated on hardware eight days later (docs/17 §8.3)
> and has been the deployed configuration since. The clean test this section asks for in
> §3b was run on 31.08: car on the ground, hands off, tape-measured, rectified,
> `near_secant`/1.0, `policy:=false`. **Rectified, the under-read is not there**: scale
> **1.058** (car left, r² 0.999) / **0.991** (car right, r² 0.977), and the ≈ −10 mm
> intercept disappears too (−11.7 mm with the wheels in the air, +0.7 mm on the ground).
> C-01 fires at a true **151 / 158 mm** with ~100 mm of margin to the road edge — not at
> the 207–241 mm with 14–48 mm computed below. The ±55 mm pairing collapse does not
> reproduce either (0/440 invalid cycles out to ±100 mm), which confirms this section's
> own suspicion that the hand sweep produced it.
>
> **This section is not withdrawn, and its operative conclusion was right.** It said
> "correcting `fx` alone is not enough, the estimator has to undistort"; the 31.08 sweep
> is the measurement showing that undistorting did exactly what was asked of it. Read §4
> as the characterisation of the **raw** path and as the reason the deployment is
> rectified — not as a live description of what the cage sees today.
>
> What the sweep found instead is a **different** defect in the same band: right of
> centre the estimate is unstable — 43.3 mm of swing on a stationary car at −60 mm,
> sd 6.2–8.4 mm against 0.5–0.9 mm mirrored, reproducible — with `/perception_invalid`
> False for all 705 cycles, i.e. confidently wrong (H-12 / D-43). Sweep:
> `experiments/physical/runs/lanesweep_20260831T094110Z/SWEEP_NOTE.md`; session:
> `experiments/physical/runs/SESSION_20260831.md`; CHANGELOG `[31.08.2026]`.

This section was written twice. The first version concluded from the lane-width measurement that
"the IPM reads lateral distance correctly" and retracted M-6's propagated `ey` scale. **That
inference was invalid**, and the hands-off measurement below overturns it.

### Why lane width does not answer the question

`lane_width` is `(left.c0 − right.c0)·cos(heading)` — a **difference** between two positions that
straddle the optical axis. `ey` is `−c0` — an **absolute** off-axis position. M-6 measured barrel
distortion `k1 = −0.339`, which `camera_geometry` does not model at all, and barrel distortion
compresses positions away from the image centre while largely preserving a symmetric difference
across it. So the width can read true while `ey` does not, and it does: at a true offset of 0 the
width reads **243.8 mm against a ruler 250 (0.975)** while `ey` reads **−9.8 mm**.

### The measurement

`tools/measure_offset_response.py`. The car is parked on the ground at a tape-measured offset,
**hands off**, and sampled for 10 s; ~190 frames per point; 15 points over ±100 mm with repeats.
Tape references the lane centre (midpoint of the two inner line edges); `ey` positive = car left
of centre. Raw data: `experiments/calibration/M7_offset_response.csv`.

| filtering | n | slope | intercept | r | C-01's real trigger |
| --- | --- | --- | --- | --- | --- |
| all points | 15 | 0.715 | −10.1 mm | +0.943 | 238 mm |
| width-sane ≥ 50 % | 6 | 0.768 | −11.7 mm | +0.990 | 224 mm |
| stable (`ey` sd ≤ 12 mm) | 7 | 0.677 | −2.7 mm | +0.808 | 241 mm |
| sane **and** stable | 4 | 0.827 | −10.8 mm | +0.984 | 207 mm |

**The under-read survives every filtering**: slope 0.68–0.83, intercept ≈ −10 mm, r up to 0.99.
That robustness is what distinguishes this from the three §2 artefacts, which reversed depending
on which subset was inspected.

**M-6 predicted 0.72. The direct measurement brackets it.** The afternoon retraction of that
prediction is itself withdrawn. What does not survive from M-6 is its *mechanism* — a pure `fx`
scale — since the intercept and the side-asymmetry point at the principal-point offset
(`cx` 305.39 vs an assumed 320, i.e. 14.6 px off-axis) plus the unmodelled distortion. M-6's
operative conclusion stands verbatim: **correcting `fx` alone is not enough, the estimator has to
undistort.**

### What this costs the cage

Across the four fittings, C-01's nominal `d_max` of 160 mm fires at a **true 207–241 mm**, and
C-05's 120 mm warning at a true 172–212 mm. The road half-width is 255 mm. So the lane-boundary
limit sits **47–81 mm later than designed**, leaving **14–48 mm to the road edge instead of
95 mm**. Both figures are extrapolations past where the fit was measured (±100 mm), so treat the
magnitude as indicative; the direction and the order are not in doubt.

### Repeatability is a second, separate defect

Re-placing the car at the same tape offset, in a different spot along the track:

| true `ey` | reading 1 | reading 2 | spread |
| --- | --- | --- | --- |
| −60 mm | −78.8 | −49.4 | **29.4 mm** |
| +60 mm | +26.0 | +42.8 | 16.8 mm |
| +80 mm | +31.6 | +50.4 | 18.8 mm |
| +100 mm | +56.8 | +59.9 | 3.1 mm |
| −40 mm | +0.1 | −7.1 | 7.2 mm |
| 0 mm | −11.7 | −7.9 | 3.8 mm |

Mean spread **13.2 mm**, worst **29.4 mm**, against a tape precision of ~2 mm. The reading is not
a function of lateral offset alone — it also depends on position along the track. This is *on top
of* the 0.75 gain, and it is not removable by re-parameterising a scale.

### Retracted, again

Withdrawn from the earlier version of this section: "the IPM reads lateral distance correctly",
"scale 1.012", and the conclusion that M-6's propagation was refuted. The 1.012 figure is
correct **for lane width** and is retained in §3 as such; it simply does not answer the question
it was used to answer.

## 4b. Heading — noise, not bias

Same 761 circuit frames at `white_sat_max = 30`. The car was being pushed, so some genuine
heading error is present; the valid comparison is between modes on identical frames.

| mode | gain | `epsi` mean | sd | p95 \|epsi\| | > 20° (C-05 warning) | > 25° (C-02 limit) |
| --- | --- | --- | --- | --- | --- | --- |
| `joint_pair_quadratic` | 1.6 | +0.04° | **14.29°** | 32.88° | 10.1 % | **7.8 %** |
| `joint_pair_quadratic` | 1.0 | −0.05° | 9.05° | 20.55° | 5.5 % | 3.4 % |
| `near_secant` | 1.6 | −2.79° | 8.24° | 18.33° | 3.8 % | 2.2 % |
| `near_secant` | 1.0 | −1.81° | **5.31°** | 12.61° | 0.8 % | **0.8 %** |

`joint_pair_quadratic`/1.6 — the estimator the 550k trunk was trained and scored with — is
**unbiased but 2.7× noisier** than `near_secant`/1.0, and puts **7.8 % of frames past C-02's
25° limit** against 0.8 %. `numpy` reports `RankWarning: Polyfit may be poorly conditioned` on
these fits, which is the quadratic complaining about the same thing.

That noise is the operative problem, and it is consistent with §4's mechanism: the quadratic is
fitted across the whole band out to 1 m, where the `f` error survives; `near_secant` reads only
the near field, where it cancels.

**Undecided, deliberately.** `near_secant`/1.0 is markedly cleaner but rescales the observation
the trunk was trained with. A `heading_bias_rad` correction — proposed during the session — is
**withdrawn**: there is no general bias to subtract.

## 5. Chassis and yaw authority

Commanded through `/cmd_vel` with the cage out of the path, yaw integrated from
`/odometry/filtered` (`tools/measure_yaw_gain.py`):

| `vx` (m/s) | `wz` cmd (rad/s) | `wz` achieved | ratio |
| --- | --- | --- | --- |
| 0.20 | 0.00 | −0.004 | — (**−1.0° of drift over 4 s**) |
| 0.00 | 1.00 | 0.150 | 0.150 |
| 0.20 | 0.20 | 0.096 | 0.482 |
| 0.20 | 0.40 | 0.174 | 0.436 |
| 0.20 | 0.80 | 0.273 | 0.341 |

Three things follow.

1. **The chassis tracks straight.** −1.0° over 4 s at 0.20 m/s. No mechanical or driver bias.
2. **The platform team's 0.4954 is confirmed — while moving.** 0.482 / 0.436 / 0.341 bracket it,
   and `deploy_cobraflex.launch.py` already compensates with
   `steering_to_yaw_rate_gain = 0.8/0.4954 = 1.615`. The in-place 0.150 measured **on this
   floor** is far below their bench 0.4954: docs/17 §5 warns that skid-steer scrub is
   surface-dependent, and this is that warning coming true. In-place is not the policy's regime.
3. **The plant is compressive, and that part is new.** Marginal gain falls from 0.39 (0.2→0.4)
   to 0.25 (0.4→0.8). A single linear `steering_to_yaw_rate_gain` is calibrated at moderate
   demand and **under-delivers at high demand** — which is precisely when C-01/C-02 correct.

The docs/17 §5 question as posed (firmware `TRACK_WIDTH 0.159` vs Gazebo 0.154, a 3.2 % effect)
is **not answerable and not the dominant term**: no 3 % constant fits a channel whose gain runs
from 0.48 to 0.34 across the operating range. Answer: neither; carry the compression instead.

## 6. The trunk policy does not transfer

`rl_policy_node` feeds the CNN the raw image (`to_observation`, 84×84 grayscale, k=4 stack on
`axis=-1`, `predict(deterministic=True)`) — verified to match the training pipeline. `/state_obs`
goes only to the cage.

**Static, car centred, 144 consecutive cycles:** policy steering `+0.1199`, **sd 0.0020**,
LEFT in 144/144.

**Live sweep**, car moved by hand across the lane while the deployed chain ran with
`cmd_vel_topic:=/cmd_vel_dryrun` (no actuation). Evidence of record:
`experiments/physical/runs/policy_bias_probe/cage_status.csv`, **5665 logged cycles**, `ey`
spanning **332 mm** (−250.4 … +81.5):

| `ey` bin (mm) | n | mean steer | sd |
| --- | --- | --- | --- |
| −250 … −217 | 32 | +0.1663 | 0.0461 |
| −118 … −84 | 71 | +0.1289 | 0.0572 |
| −84 … −51 | 136 | +0.1382 | 0.0505 |
| −51 … −18 | 2597 | +0.1193 | 0.0148 |
| −18 … +15 | 2174 | +0.1159 | 0.0197 |
| +15 … +48 | 213 | +0.1072 | 0.0483 |
| +48 … +81 | 428 | +0.1105 | 0.0289 |

```
steer = -0.000166 · ey_mm + 0.1155      r = -0.243      r² = 0.059
```

**The response has the right sign and is an order of magnitude too weak to matter.** Read the
three numbers that follow it, not the correlation:

| | |
| --- | --- |
| Lane-dependent swing over the **whole** 332 mm | **0.055** |
| Constant left offset (steer at `ey = 0`) | **+0.1155** — **2.1×** the entire swing |
| Samples commanding RIGHT at all (`steer < 0`) | **29 / 5665 = 0.5 %** |

So the policy did not forget lane-following outright: `r² = 0.059` of its steering variance
tracks lateral position, in the correct direction. It is **swamped by a constant left bias that
the real imagery induces**, and across a full lane width it essentially never commands a right
turn. In closed loop the bias dominates and the car leaves to the left regardless of where it
is — which is exactly what was observed on the ground before the cage stopped it.

The output is also not frozen: it varies with the scene (sd 0.0237 over the file). It varies
*mostly* with something other than the lane.

*Corroborating offline probe* (`PPO.load`, same stacking as the node): mirroring the
observation — which must mirror a lane-follower's steering — moves the output by 0.04
(+0.5325 → +0.4959); all-black gives +0.7208, uniform grey +0.5429, random noise +0.5609. Every
input lands in the same band, always left. **Caveat:** the offline absolute values do not
reconcile with the live node (+0.53 vs +0.12), because the probe repeats one frame four times
instead of using real history and may omit a `VecNormalize` step. Only the direction and the
insensitivity are claimed from it; the logged sweep above is the evidence of record.

*Correction made during analysis:* a first pass over a 146-sample live window reported
`r = −0.028` and characterised the response as *uncorrelated*. The full 5665-row log does not
support that: the correlation is weak but real. The finding is the **bias-to-swing ratio**, not
the absence of a response.

## 6b. A sensor fault the cage caught, and the crash

`experiments/physical/runs/track_first_drive/cage_status.csv` — 7721 cycles over 17 minutes of
drive attempts — shows the speed the cage consumes carrying **physically impossible outliers**:

| threshold | cycles | share |
| --- | --- | --- |
| > 0.22 m/s (the 2-D contract ceiling) | 176 | 2.28 % |
| > 1.50 m/s (`state_validity_ranges.speed_mps`) | 33 | 0.43 % |
| maximum observed | **6.960 m/s** | — |

6.96 m/s on a car whose commanded maximum is 0.22 — the ZED visual odometry through the ekf
producing ~30× excursions. **All 33 out-of-range cycles are in emergency**: SR-007's state
validity range, a `[provisional]` parameter, is catching a real hardware sensor fault that no
simulation produced. This is evidence *for* the design, and the first out-of-ODD input the
deployed cage has rejected on hardware.

**Session ended by a Jetson crash and power cycle.** The bag lost its `metadata.yaml`
(regenerated with `ros2 bag reindex`; `PRAGMA quick_check` on the `.db3` returns `ok`) and
`circuit_survey/cage_status.csv` lost its final unflushed block to 1114 NUL bytes at 99.8 %
through (truncated at the last complete line; see that run's `REPAIR_NOTE.md`). Recording raw
640×360 at 20 Hz is **13.8 MB/s** to eMMC while the whole chain runs, and the recorded rates are
visibly I/O-starved — camera 13.1 Hz against a nominal 20, `/state_obs` 5.0 Hz against 10. Read
no rate figure from these runs as chain capability: the 17.08 bench session measured 20.0 Hz
camera and 9.8 Hz cage with no recorder running.

## 7. What this means

The runtime safety cage and the deterministic estimator are the parts that worked, both at
their shipped settings. On a track where the trained policy is ineffective, the chain stayed
safe: C-05 stopped the car on every excursion, `/cmd_vel` went to
an exact zero Twist, and no road-edge contact occurred. That is the thesis argument
demonstrated on hardware rather than in simulation — a stronger result than a clean lap would
have been.

**Open, and each is off-track work:**

- Closing the appearance gap: fine-tune or retrain with domain randomisation calibrated against
  real imagery. Raw material: `experiments/physical/bags/circuit_20260818T140357Z` — 1521 frames
  with time-aligned `/state_obs`, i.e. **the working estimator labelling real images for free**.
  It is short (116 s) and was recorded mostly centred, so it lacks recovery examples; a longer
  deliberately-weaving pass is the next capture.
- The estimator's localised colour failures (§3): a per-row adaptive threshold or camera exposure
  control, neither tested.
- The `epsi` channel: `near_secant`/1.0 is clean but changes the observation scaling the trunk
  was trained with; `joint_pair_quadratic` + `heading_bias_rad` keeps the scaling but retains
  13.6° of noise. Neither is decided here.
- The compressive yaw plant (§5.3).

## 8. Reproducing

```bash
# perception, non-invasive: a second estimator on the live camera, changes nothing
python3 tools/lane_probe.py --seconds 12 --true-width 0.25

# the deployed chain WITHOUT actuation — full chain, driver receives nothing
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
  checkpoint:=<trunk>.zip mode:=enforcement cmd_vel_topic:=/cmd_vel_dryrun

# chassis / yaw, cage bypassed by design (kinematics under test, not the controller)
python3 tools/measure_yaw_gain.py --vx 0.20 --wz 0.40 --seconds 4
```

Offline replay of a recorded circuit is what the live tools could not give, and it is now the
primary method — `tools/lane_probe.py` characterises the pose you are standing at, which §2
shows is not the track. `lane_probe.py` refuses to report a scale from the single-line fallback (whose `lane_width` is
the nominal constant, sd exactly 0.0), from fewer than 20 paired frames, or when the width has
zero dispersion. Each of those guards was added after the tool produced a confidently wrong
answer during this session.

## 9. Tooling provenance

| Tool | Added | Purpose |
| --- | --- | --- |
| `tools/lane_probe.py` | 18.08.2026 | shadow estimator on the live camera; exposes `lane_width`, pairing rate, failure reasons |
| `tools/measure_yaw_gain.py` | 18.08.2026 | commanded vs achieved yaw from `/odometry/filtered`; refuses to run against a live publisher |
| `tools/preflight_deploy.py lanecheck` | 18.08.2026 | static `ey`/`epsi` against a tape measure, with an `epsi`-stability gate |
