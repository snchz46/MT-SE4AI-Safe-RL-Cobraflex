# lap01_20260831T095940Z — 3.11 m, stopped by a one-cycle heading spike

`monitoring`, rectified, `near_secant`/1.0, `reset_proxy:=observe`, checkpoint
`ppo_gz2d_sim2real_v2_2024_r2_1650000_steps.zip`. Diagnostic run, NOT scored
(`near_secant` is not the D-43 contract — docs/17 §8.4).

| | |
| --- | --- |
| distance (integrated) | **3.11 m**, 177 moving cycles of 1056 |
| loop | 9.10 Hz, `cycles_since_last_state` max **0** |
| \|ey\| while moving | median **9.9 mm**, max 58.8 mm |
| speed | median 0.180, max 0.210 m/s |
| rules | C-06 x3, **C-02 x2**, C-05 x914 (the latch) |

## What stopped it

Not the policy, not CPU, not perception loss. `/perception_invalid` never fired.

| cycle | t-t0 | ey (mm) | epsi (deg) | kappa | rules |
| --- | --- | --- | --- | --- | --- |
| 128..140 | -1.5..-0.1 s | -26..+7 | -7.5..+1.8 | small | - |
| **141** | -0.11 | **-58.8** | +2.50 | **-1.44** | - |
| **142** | 0.00 | -50.5 | **-36.97** | -1.50 | **C-02 ; C-05** |
| 143 | +0.09 | -40.5 | **-1.01** | 0.28 | C-05 |

One cycle. `ey`, `epsi` and `kappa` all jump together and all recover together —
the signature of a wrong line pair, not of a real heading error. C-02 (25 deg)
fired on a measurement artefact and latched C-05 for the remaining 914 cycles.

**The morning's sweep predicted this.** -58.8 mm was the run's maximum |ey|, i.e.
the car ~60 mm RIGHT of centre — the exact band where the stationary sweep
(`../lanesweep_20260831T094110Z/SWEEP_NOTE.md`) measured 43 mm of swing, sd 8.4 mm
and excursions to -99.8 mm, against sd 0.5 mm at the mirrored +60 mm. The captured
frames show why: the car was entering a LEFT curve off-centre to the right, with
the near solid right line steeply angled, the far dashed left line, and the curve's
own arc crossing the mid-field — four line candidates, which is M-7 section 3b's
wrong-pair mechanism.

Note this is `near_secant`/1.0, the QUIETER heading mode (M-7 section 6d: 5.3 deg
sd / 0.8 % past C-02, against `joint_pair_quadratic`/1.6's 14.3 deg / 7.8 %).

## D-74's open question, answered by the observe pass

    1788170432.21  would_reset  "healthy for 1.11 s, reset 1/6"

`reset_proxy:=auto` would have recovered the run **6.4 s after the stop**. The five
later entries at ~3.09 s intervals are an artefact of observe mode — nothing clears
the latch, so the condition keeps re-arming. There was ONE event, not six; the
"budget spent (6/6)" console line must not be read as six failures.

## Evidence apparatus — first real outing, all four gaps closed

* `frame_capture_node`: **82 PNG** around the event, the measurement docs/17
  section 8.9 asked for after 18.08 and again after 26.08. Cost 6.9 % of a core idle.
* `cage_logger_node platform:=physical`: full provenance block (commit 719edfda,
  cage.yaml 4287fe71, checkpoint c67c3daf) — after the crash fixed this morning.
* `cage_reset_proxy_node` in `observe`: answered D-74 with data instead of opinion.
* `run_physical_lap.sh`: one run id for CSV/bag/frames/resets, `layer2.json`
  probed off the running nodes.

## What this does NOT settle

* Why 26.08 drove 18.05 m with no C-02 at all and this run hit it at 3.11 m is
  **not established**. Different line through the curve, different light, chance.
* The sweep was taken at one location (start of the straight). That the right-side
  instability appears in the curve too is consistent with this run, not proven by it.
* No floor-mark measurement is meaningful here — the car never approached the start.
