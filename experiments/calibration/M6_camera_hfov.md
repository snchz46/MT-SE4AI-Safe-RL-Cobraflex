# M-6 — Lane camera effective HFOV and mount pitch

**Goal.** Measure, on the physical car, the two geometric constants the safety
cage's inverse-perspective mapping depends on: the **effective horizontal field
of view** of the 640×360 lane stream, and the **camera mount pitch**. Both were
*assumed*, never measured.

**Closes.** [docs/17 §2](../../docs/17_physical_deployment.md) `[VERIFY]` #1
(the 90° effective HFOV, flagged there as *"the load-bearing unverified number of
the whole sim-to-real transfer"*) and `[VERIFY]` #2 (camera extrinsics —
`camera_geometry.DEFAULT_CAMERA_PITCH_RAD` = 0.30 rad).

**Status: both executed 17.08.2026.** HFOV is **77.89°**, not 90° — verdict
**`Blocking`**. Mount pitch is **17.84°** against 17.19° assumed — **confirmed**,
no adjustment needed. Jump to [RESULT](#result--fully-measured-17082026-bench-intrinsics-and-extrinsics).

**Effort.** Under one hour. Requires the physical platform with
`csi_camera_node` publishing, a flat surface, a tape measure, and — for the
preferred route — a checkerboard displayed on any flat screen. No printer.

## Why this cannot be answered in simulation

`camera_hfov_deg` 90.0 originates as a *parameter default* in `lane_keeper_node`
for an IMX219-**160** wide-angle lens. The Gazebo `Lane Cam` sensor was then
built to mirror it (`<horizontal_fov>1.5707963</horizontal_fov>`). Sim and
hardware therefore share the assumption, and **no simulation result can expose an
error in it** — including the 1890-run verdict-of-record campaign.

It is load-bearing because `CameraModel.fx = (w/2)/tan(hfov/2)` = 320 px at
640×360, and the IPM's metric output scales with `1/fx`. If the true effective
HFOV differs, every `ey` the cage acts on is mis-scaled by `fx_assumed /
fx_measured`, and **C-01's 0.16 m `d_max_m` stops meaning 0.16 m** (docs/17 §2
calls this threshold 0.12 m; that value is actually C-05's `d_warning_m`). The
same applies to the pitch, which sets the row→distance mapping.

Note the `CameraInfo` published on `camera/camera_info` is deliberately the
*ideal pinhole the cage assumes* (zero distortion), not a measured calibration.
This protocol does not change that; it measures the disagreement so the two can
be reconciled deliberately (see the decision rule).

## Principle — why a tape measure is a sufficient target

A pinhole images a fronto-parallel line at distance `D` with a constant scale:

```
u_i = cx + fx · (y_i − y0) / (D + δ)
```

`y_i` is a tape reading, `y0` the (unknown) reading on the optical axis, and `δ`
the (unknown) offset between whatever face you measured `D` against and the lens
entrance pupil. Fitting one straight line per distance gives a slope
`s_j = fx/(D_j + δ)` in px/m, and collapses `cx` and `y0` into its intercept —
**neither is ever needed**. One further regression separates the last two
unknowns:

```
1/s_j = D_j/fx + δ/fx
```

slope `1/fx`, intercept `δ/fx`. So **two or more distances give `fx` without
knowing where the optical axis is and without trusting the zero of your tape**.

The residuals of each per-distance line are exactly the lens distortion the
pinhole IPM ignores. The tool reports them in px *and* in the lateral metres of
error they inject, because that is the quantity C-01 compares against its
0.16 m `d_max_m`.

For the pitch, a tape laid **forward** on the ground plane gives (tape reading,
image row) pairs, and the same trick fits the unknown tape-zero offset, so the
only physical quantity that must be measured by hand is the camera height above
that plane.

### Ground-plane correction (do not skip)

With the target lying **flat on the surface the car stands on** and `D` measured
as a horizontal forward distance, the lateral scale is set by the *optical
depth*, not by `D`:

```
z_o = D·cos(pitch) + H·sin(pitch)      →      fx = cos(pitch) / slope
```

Ignoring the cosine inflates `fx` by `1/cos(pitch)` = **+4.7 %** at the assumed
0.30 rad — on its own more than the 2 % "confirmed" band of the decision rule
below. The pitch enters only through its cosine, so it barely has to be right: a
3° pitch error moves `fx` by 0.3 %. Take it from Part B and iterate once if you
care. Use `--perpendicular` only if the target was genuinely held normal to the
optical axis, which for a pitched camera is hard to do by hand.

## Identifiability — why several distances are mandatory

Established by Monte-Carlo simulation of the fits before any hardware was
touched, because the failure mode here is silent: a degenerate fit converges to
a **confidently wrong** answer at zero residual, not to an obvious error.

| Configuration | Free parameters | Result |
| --- | --- | --- |
| Forward tape alone | fx, H, pitch, offset | **Degenerate.** At zero noise the fit returns fx = 351 px / pitch 19.41° for a truth of 400 px / 17.19°, residual ≈ 0. |
| Forward tape + measured height | fx, pitch, offset | Identifiable, but fx only to ±7 % at 1 px reading noise. Enough for pitch, not for fx. |
| Forward tape + measured height + known fx | pitch, offset | Pitch to **±0.04°**, tape offset to ±1 mm. This is Part B. |
| Transversal tape, single image | fx, H, pitch, tape pose | **Degenerate.** Zero-noise fit returns fx = 334 px for a truth of 400 px. |
| Transversal tape, single image + measured height | fx, pitch, tape pose | Unbiased but useless: fx ±96 px (±24 %) at 0.3 px noise. |
| **Transversal target at ≥ 2 distances** | fx, pupil offset | **Well conditioned.** This is Part A. |

The conclusion is structural, not a matter of care: **one image cannot separate
focal length from camera pose.** Varying the distance is what breaks the
degeneracy, because only `fx` is shared across the sets while the pose is not.

## Target requirements (learned the hard way)

The first attempt used a steel tape laid across the view at 0.145 m and had to be
discarded. Windowed-FFT analysis of its graduation period showed the image scale
running from 27.7 px/cm at the centre to 16 px/cm at the edges — a 44 % variation
that a pinhole cannot produce for a straight fronto-parallel line. The blade was
both **bowed** (a loose steel tape does not stay straight on a table) and
**yawed** (its image row drifted 19 px across the frame, ≈ 15 mm of depth
difference between the ends, ≈ 10 % of scale variation at that distance).

Hence:

1. **Rigid, not flexible.** Use a stiff ruler or a straight edge. A free steel
   tape bows, and the bow is indistinguishable from lens distortion in one shot.
2. **Perpendicular to the car's forward axis.** The check is in the image and
   needs no protractor: for a pitch-only camera, every point at the same forward
   distance lands on the same row, so **a correctly aligned target is a
   horizontal line in the image**. Any row drift end-to-end is yaw.
3. **Far enough.** Yaw sensitivity scales as 1/D: the same 15 mm of end-to-end
   depth error costs ~10 % of scale at 0.145 m but ~3 % at 0.5 m.

## Procedure

Tool: [`tools/calibrate_camera_hfov.py`](../../tools/calibrate_camera_hfov.py).
Run everything with `csi_camera_node` up and `lane_keeper_node` **down** — the
two contend for the CSI device *and* for `/cmd_vel` (docs/17 §1b).

### Part 0 — checkerboard (PREFERRED; use this unless no screen is available)

The tape route below was written for "no printed target available". It works,
but it fights three error sources the standard method simply does not have:
target rigidity, target yaw, and the measured distance. A checkerboard shown
**on a monitor** is flat, rigid and high-contrast, needs no printer, and many
views over-determine `fx`, `fy`, `cx`, `cy` *and* the distortion coefficients —
with **no distance measurement at all**, and no degeneracy to reason about.

1. `... board --out .../checkerboard_9x6.png` and display it **full screen with
   no scaling** on a flat monitor (a laptop screen is fine).
2. Measure the square size: lay the tape across **all ten squares** and divide
   by ten. **This does not affect the answer** — verified by re-solving the real
   data at 20.00, 18.03 and 50.00 mm, which returned `fx` = 396.10 px and
   k1 = −0.338 *identically* in all three. Scaling the object points scales only
   the recovered board translations; `K` and the distortion coefficients are
   invariant. Measure it anyway so the board poses come out in metres, but do not
   treat it as a precision step, and do not let a doubt about it cast doubt on
   the HFOV.
3. `... board-capture --views 20` and move the board around the field of view:
   near/far, all four quadrants, and — this is the part people skip —
   **tilted**, ±30° or so about both axes. Tilt is what separates focal length
   from distance; a set of fronto-parallel views is the same degeneracy the tape
   route hits.
4. `... board-solve <dir> --square-m <measured> --out M6_results.json`
5. Sanity gate: rms reprojection should be well under 0.5 px. Above that,
   suspect the square size, a non-flat screen, or blurred views.

Validated end-to-end against exact synthetic ground truth (inverse-ray rendering
through a known `K` and `plumb_bob` distortion): `fx` recovered to 0.04 %,
`cx`/`cy` to ~1 px, `k1` to 0.01, rms 0.32 px.

### Part A — effective HFOV (tape route; fallback)

1. Frame check:
   `python3 tools/calibrate_camera_hfov.py preview --out experiments/calibration/M6_camera_hfov`
   Confirm the frame is **640×360** (a different size silently mis-projects every
   `ey`, because `cv_lane_estimator` indexes its scan bands by `camera.height_px`).
2. Lay a **rigid** graduated straight edge across the field of view, flat on the
   surface, perpendicular to the car's forward axis, spanning as much of the
   image width as it can, with the cm marks legible. See the target requirements
   above — a free steel tape is not rigid enough.
3. Measure `D₁` from a repeatable reference face — the front of the lens barrel
   is fine. **The reference only has to be the same for every distance**; a
   constant error is absorbed by `δ`.
4. Capture:
   `... capture --distance-m 0.30 --distance-reference "lens front face"`
   Then check the alignment on the captured frame: the target's image row must be
   constant across the width. Rotate and re-capture until the end-to-end row
   drift is under ~2 px.
5. Repeat steps 2–4 at **two more distances**, e.g. 0.50 m and 0.80 m. Spread
   them: the `1/s` vs `D` regression is what separates `fx` from `δ`, and per the
   identifiability table it is the *only* thing that does.
6. For each capture, locate the tick marks and read off their cm labels:
   `... detect <png> --band <v0> <v1> --overlay <png> --json <json>`
   Pair each detected column with its tape reading in an observations file
   (schema below). Use marks spread across the width, but note the outermost
   ones carry the most distortion.
7. Solve: `... solve observations.json --out M6_results.json`

### Part B — mount pitch

1. Lay the tape **forward** along the optical axis, flat on the same plane the
   car stands on, cm marks legible.
2. Measure the **camera height above that plane** with the tape. This is the one
   hand measurement the fit cannot absorb. On a bench this is *not* 0.07725 m —
   that is the height above the floor with the car on its wheels. Pitch is a
   mount property and transfers from bench to track; height is not.
3. Capture a frame, then `detect --vertical --band <u0> <u1>` to get the rows of
   the tick marks, and label them with their cm readings.
4. Solve: `... solve-pitch pitch_obs.json --fx <fx from Part A> --height-m <h>`
   Add `--free-height` once as a consistency check: if the fitted height
   disagrees with the tape by more than a few mm, the plane was not flat, the
   marks were mis-labelled, or `fx` is wrong.

## Decision rule

Let `k = fx_assumed / fx_measured` be the metric scale error the tool reports.

| Condition | Verdict | Action |
| --- | --- | --- |
| \|k − 1\| ≤ 2 % and \|pitch error\| ≤ 1° | **Confirmed** | Record and close both `[VERIFY]` items. The assumed geometry stands. |
| 2 % < \|k − 1\| ≤ 10 %, or pitch error ≤ 3° | **Revise** | Update `camera_geometry` defaults + `lane_keeper_node.camera_hfov_deg` + the `Lane Cam` `<horizontal_fov>`, **all three together** (they are one contract). Re-run `tools/validate_cv_estimator.py`. The 550k policy need not be retrained — the CNN never sees metres — but every cage threshold in metres must be re-read. |
| \|k − 1\| > 10 % | **Blocking** | Do not drive on cage thresholds. **The sim campaigns are not affected** — Gazebo's sensor and the IPM shared the same HFOV, so in sim C-01 fired at exactly its 0.16 m. It is the *hardware* cage that fires at `0.16·k` m, so the in-ODD road-edge-contact result cannot be claimed to transfer until the geometry is reconciled. |

Whatever the outcome, the disagreement between the published `CameraInfo` (ideal
pinhole, no distortion) and the measured intrinsics must be **reconciled
deliberately, not patched** by adding distortion coefficients to the message —
that would contradict the IPM that consumes it (docs/17 §2 item 1).

## Output schema

Observations for Part A (`--out` of `solve` writes the results beside it):

```json
{
  "width_px": 640,
  "observation_sets": [
    {"distance_m": 0.30, "label": "d030",
     "marks": [{"u_px": 91.4, "y_m": -0.10}, {"u_px": 320.2, "y_m": 0.00}]}
  ]
}
```

Part B:

```json
{
  "camera_height_m": 0.0625,
  "height_px": 360,
  "marks": [{"s_m": 0.10, "v_px": 325.2}, {"s_m": 0.15, "v_px": 299.8}]
}
```

`s_m` is the raw tape reading; the tape-zero offset is fitted. Supply `x_m`
instead if the true distance from the camera is known, and the offset is pinned
to zero.

Results land in `M6_results.json` / `M6_pitch_results.json`, each carrying the
git commit and a UTC timestamp for the reproducibility metadata every run under
`experiments/` records.

## RESULT — fully MEASURED 17.08.2026 (bench). Intrinsics *and* extrinsics.

> **Short answer to "is the camera calibrated?"** — yes, the measurement is complete and
> cross-validated. What is *not* done is applying it: no source file has been changed, so
> the running system still uses the wrong geometry. See "Open decision".

`experiments/calibration/M6_results.json`, from
`M6_camera_hfov/board_views2/` — 26 checkerboard views, 20.0 mm squares,
`csi_camera_node` publishing 640×360, `lane_keeper_node` down.

| Quantity | Measured | Assumed | Error |
| --- | --- | --- | --- |
| `fx` = `fy` | **395.93 px** | 320.00 | **+23.7 %** |
| **Effective HFOV** | **77.89°** | 90.00° | **−12.11°** |
| `cx` | 305.39 px | 320.0 | −14.61 px |
| `cy` | 193.20 px | 180.0 | +13.20 px |
| Distortion (`plumb_bob`) | k1 −0.339, k2 +0.137, k3 −0.028, p1 +0.0004, p2 −0.0003 | all zero | barrel |
| rms reprojection | 0.238 px | — | — |
| **Mount pitch** | **0.3113 rad / 17.84°** | 0.3000 rad / 17.19° | **+0.65°** |
| Camera height | 77.9 mm *(fitted)* | 77.25 mm (URDF) | +0.7 mm |

**The verdict is `Blocking`** by the decision rule below: the metric scale error
is `k = 320/395.93 = 0.808`, i.e. **−19.2 %**, far outside the ±10 % band.

Conditioning (all checks passed — see the tool's `conditioning_problems`):
free-aspect `fy/fx` = **1.006**, which matters because nothing imposed it — the
square-pixel physics of the isotropic 1280×720→640×360 resize is *recovered from
the data*. Corner coverage 12/16 image regions, board tilt 25–67°. Stability
across independent solves: fx = 395.93 (**58 views, 16/16 image regions**) /
396.10 (26) / 396.29 (34) / 395.70 (13-view half) — spread 0.15 % while the view
count grew 4×. Worst single-view reprojection 0.381 px, median 0.168; no outlier
view.

An earlier 8-view attempt (`board_views/`) is retained but **must not be
quoted**: its free-aspect probe read `fy/fx` = 1.85, physically impossible here,
because the views were clustered and under-tilted. It is the worked example of
why the conditioning gate exists — with the aspect ratio *fixed* it happily
returned a plausible-looking 397.73 px at rms 0.211 px.

### Why the lens is far narrower than 90°

Coherent with the hardware: the IMX219's nominal "160°" is a **diagonal** figure
for the *full* 3280×2464 sensor, but `csi_camera_node` captures the **1280×720**
mode, which on this sensor is a *cropped* readout, not a downscale of the full
frame. A crop keeps the pixel pitch and throws away field of view. 77.89° is what
that crop leaves.

### What this does to the cage

The IPM's metric output scales with `1/fx`, so every `ey` in metres the cage acts
on is inflated by 395.93/320 = **1.237**:

| Threshold (`cage/cage.yaml`) | Nominal | What it really means on this camera |
| --- | --- | --- |
| C-01 `d_max_m` | 0.160 m | **0.1293 m** |
| C-03 `d_max_m` | 0.160 m | 0.1293 m |
| C-05 `d_warning_m` | 0.120 m | 0.0970 m |
| `state_validity lateral_offset_m` | 0.300 m | 0.2425 m |

**That table is the raw single-point scaling, and it is NOT what reaches C-01.**
Propagating the full measured model through the estimator's actual construction —
two lane markings `lane_width_nominal_m` = 0.245 m apart, per-row midpoints, a
quadratic `Y(X)` fit, `ey = −c0` extrapolated to X = 0 — gives:

> **reported `ey` = 0.72 × true, bias −1 mm** (modelled over |true ey| ≤ 0.12 m)

The principal-point offset **cancels** here, because the two markings sit close
together and symmetrically about the lane centre. The 28 % under-read does not.
So the operative consequence is the opposite of the naive one: **C-01 and C-05
fire at a *larger* true excursion than their nominal 0.16 m / 0.12 m — the
hardware cage is *less* protective than the campaign verified, not more.**
Extrapolating the gain linearly puts C-01 at a true ±0.22 m, but that is outside
the ±0.12 m band the gain was fitted over, and the two-marking geometry breaks
down before then (the estimator drops into single-side mode), so read it as a
direction and a rough magnitude, not a threshold.

**The simulation results are not invalidated.** Gazebo's `Lane Cam` really was
90° and the IPM really did assume 90°, so in sim C-01 fired at exactly 0.16 m.
What the mirror broke is the *transfer*, and only on hardware.

**Two consequences beyond the scale factor:**

1. **A lateral bias, not just a gain.** `cx` sits 14.61 px off centre, so a
   perfectly centred lane does not decode as centred. A bias is worse than a gain
   for a centring controller: the cage believes the car is centred when it is
   consistently off to one side. Quantified against the measured pitch in "The
   error the cage commits today" below.
2. **The policy's observation distribution shifts too, independently of the
   IPM.** The 550k trunk CNN trained on 90°-HFOV Gazebo frames; the real camera
   delivers 77.89°. Real images are ~24 % "zoomed in" relative to everything the
   policy ever saw. This is a sim-to-real domain shift in the *observation*, and
   no IPM correction touches it — only re-configuring the Gazebo sensor and
   retraining does.

`cy` being 13.20 px low is worth **+1.91°** of equivalent pitch error at
`fy` = 395.9. Part B measured the *mount* pitch independently at +0.65° from
nominal, so the two are **not** the same thing and must not be added: the mount is
nearly right, and most of the row→distance error comes from the principal point,
not from how the camera is bolted on.

### Part B — mount pitch (executed same session)

`experiments/calibration/M6_pitch_results.json`, from `partB_tape_raw.png` +
`partB_obs.json` — the tape laid forward along the optical axis, 17 cm marks
read from the image (10–26 cm), `fx` taken from Part 0.

| | Fitted | Cross-check |
| --- | --- | --- |
| Mount pitch | **0.3113 rad (17.84°)** | 0.3084 rad (17.67°) with the height pinned at the hand-measured 77 mm |
| Camera height | **77.9 mm** (fitted) | **77 mm** measured by hand — **agree to 0.9 mm** |
| Tape zero offset | −3.5 mm | absorbs the constant number-to-tick print offset |
| Residual | rms **0.48 px**, max 1.07 px over 17 marks | — |

The height agreement is the strongest single validation in this document: it was
never given to the fit, and the fit recovered the operator's tape reading to
0.9 mm. That is only possible if `fx`, the pitch and the mark extraction are all
right simultaneously. The degeneracy that made a height-free fit impossible
earlier is broken precisely because `fx` came from Part 0 first — which is why
the two parts must run in that order.

**The mount pitch is essentially correct**: +0.65° against the URDF's 0.30 rad,
inside this protocol's 1° "confirmed" band. `camera_geometry`'s extrinsics do not
need physical adjustment. The problem is entirely in the intrinsics.

### The error the cage commits today, on real lane points

Ground points projected through the *measured* camera (intrinsics **and** pitch),
then decoded by the *running* IPM (`fx` 320, `cx` 320, `cy` 180, pitch 0.30, no
distortion):

| X | Y = +0.25 m | Y = 0 | Y = −0.25 m |
| --- | --- | --- | --- |
| 0.30 m | −8.0 mm | +13.2 mm | +33.7 mm |
| 0.50 m | +39.0 mm | +23.6 mm | +4.5 mm |
| 0.80 m | +111.0 mm | +43.1 mm | −32.1 mm |
| 1.00 m | **+166.8 mm** | +59.7 mm | −57.5 mm |

Lateral error spans **−57 mm to +167 mm**. The worst case **exceeds C-01's entire
160 mm `d_max_m`**. Forward distance is worse still — a point at 1.00 m decodes as
1.34 m — because at the far end of the estimator's 0.15–1.00 m scan band the rays
are within ~20 px of the horizon, where the row→distance mapping is intrinsically
steep. The near field is far healthier: ~8–34 mm at 0.30 m.

### Which correction actually buys anything

Errors over the same lane points, applying corrections cumulatively:

| Correction applied | \|dY\| max | \|dY\| mean |
| --- | --- | --- |
| as it runs today | 166.9 mm | 49.4 mm |
| `fx` corrected only | 102.1 mm | **52.2 mm** |
| `fx` + `cx` + `cy` | 43.7 mm | 13.8 mm |
| + pitch & height | 50.7 mm | 26.1 mm |
| + distortion undone | ~0 mm | ~0 mm |

Two things fall out of this, and both are counter-intuitive:

1. **Correcting `fx` alone makes the average error worse** (49.4 → 52.2 mm). The
   scale error and the principal-point offset were partially cancelling. "Just fix
   the HFOV" is the one change that must *not* be made in isolation.
2. **Undistortion is not optional.** With `fx`, `cx`, `cy`, pitch and height all
   corrected, a pinhole IPM still leaves ~44–51 mm of lateral error, because the
   lens is not a pinhole. Only undoing the distortion closes it.

   *Caveat on that last row:* the ground truth here is generated with the same
   `plumb_bob` model the correction inverts, so ~0 is a round-trip check of the
   arithmetic, not independent proof that the real lens is exactly `plumb_bob`.
   The meaningful content is the **first four rows** — the residual that scalar
   corrections cannot reach.

### Open decision — nothing has been actioned in code

No source file was changed by this measurement. `camera_geometry.py`,
`lane_keeper_node.camera_hfov_deg`, the `Lane Cam <horizontal_fov>` and
`cage.yaml` all still carry the 90° assumption, deliberately: the three plausible
responses have very different costs and the choice is the author's.

Whatever is chosen, the decomposition above forbids the smallest version of it:
**correcting `fx` on its own raises the mean error** and must not be shipped
alone.

* **Correct the IPM properly** — `CameraModel` gains the measured `fx`, `cx`,
  `cy` and pitch, *and* the estimator undistorts before projecting. Restores the
  metric meaning of every cage threshold on hardware, and it does **not** touch
  the policy — the CNN never sees metres. Leaves the observation-space shift
  untouched. Note undistortion is the part that carries the last ~44 mm, so a
  scalars-only patch is a half measure.
* **Correct the sim sensor too and retrain.** Sets `Lane Cam <horizontal_fov>` to
  the measured value so training frames match the car. Removes the ~24 % zoom
  shift, at the cost of retraining the trunk policy and re-running the campaign
  that produced the verdict of record — i.e. a new trunk.
* **Change the capture mode instead.** Move the hardware to the assumption
  rather than the reverse, keeping both the sim results and the policy valid.
  The sensor offers (`v4l2-ctl --list-formats-ext -d /dev/video0`, 17.08.2026):

  | Mode | fps | Note |
  | --- | --- | --- |
  | 3280×2464 | 21 | full sensor, full FOV, 4:3 |
  | 3280×1848 | 28 | full width → same HFOV as full |
  | 1920×1080 | 30 | cropped |
  | 1640×1232 | 30 | full sensor binned 2×2 → **full FOV**, 4:3 |
  | **1280×720** | **60** | **cropped — what is used today, 77.89°** |

  `1640×1232` is the mode that keeps the whole sensor area. **Whether it lands
  near 90° is measurable, not derivable** from this calibration: it depends on
  the crop/binning factor of the 1280×720 mode, which the mode list does not
  state, and the lens's strong barrel distortion makes extrapolating from
  `fx` unreliable. It is also **not a drop-in** — 1640×1232 is 4:3 against the
  pipeline's 16:9, so reaching 640×360 needs a crop, which changes the FOV
  again, and it caps at 30 fps against the 20 Hz contract's 60. Re-run this
  protocol at any candidate mode before adopting it.

Whichever is chosen, the three code locations in the docs/17 §1b table must move
**together** — they are one contract — and `tools/validate_cv_estimator.py`
re-run afterwards.

### Tooling provenance

Self-tested against synthetic ground truth before any hardware: the tape route's
fx to 0.02 px and pitch to 0.02° under ±0.5 px reading noise, the ground-plane
correction reproducing its predicted +4.68 % bias exactly when disabled, and the
checkerboard route validated by exact inverse-ray rendering through a known `K`
and `plumb_bob` distortion — fx to 0.04 %, `cx`/`cy` to ~1 px, k1 to 0.01.

Executed so far, both **discarded on target geometry, not on tooling**, and
**no `fx` or HFOV number should be quoted from either**:

| Capture | Date | Why rejected |
| --- | --- | --- |
| `d014_*` (steel tape, D = 0.145 m) | 17.08.2026 bench | Blade bowed *and* yawed. Windowed-FFT of the graduation period ran 27.7 px/cm at the centre to 16 px/cm at the edges — a 44 % scale variation a pinhole cannot produce for a straight fronto-parallel line. |
| `d115_rigid_*` (rigid ruler, D = 0.115 m) | 17.08.2026 bench | The forward tape lay *across* the ruler, occluding its centre, and the ruler sat cut off at the bottom frame edge. Sub-pixel fit of its straight top edge left a 5.1 px rms residual — too noisy for a number. Its ~13 px of apparent sagitta is *suggestive* of barrel distortion (a rigid edge cannot bow) but is **not** a measurement. |

Next step is Part 0 (checkerboard). Part B additionally needs the camera height
above the bench measured by hand — the identifiability table shows it is the one
quantity no fit can absorb.
