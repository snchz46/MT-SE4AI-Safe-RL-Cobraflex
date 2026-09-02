# lap02_20260831T100709Z — 14.56 m with reset_proxy:=auto, left the lane in the final curve

`monitoring`, rectified, `near_secant`/1.0, **`reset_proxy:=auto`**, same 1650k
checkpoint. **DIAGNOSTIC, NEVER SCORABLE** — part of the stopping behaviour is the
proxy's, not the cage's (docs/17 section 9.5). Started from where `lap01` stopped:
mid-curve, off-centre, NOT from the marked start.

| | lap02 | lap01 | 26.08 best |
| --- | --- | --- | --- |
| distance | **14.56 m** | 3.11 m | 18.05 m |
| loop | 9.00 Hz, `cycles_since_last_state` max 0 | 9.10 Hz | 9.59 Hz |
| \|ey\| moving | median **41.2**, max **150.3** mm | 9.9 / 58.8 | 18.7 / 98.7 |
| rules | C-05 1100, **C-02 52**, C-06 19, **C-01 3**, **C-03 1** | C-05 914, C-02 2, C-06 3 | C-06 only |
| resets | **4 published by the proxy** | 0 (observe) | 0 |

## D-74's `auto` posture works on hardware

Four `/cage_reset` publications, each after the required 1 s healthy hold with the
car stopped and no C-01..C-04 active, and the car resumed every time. That is the
`observe` -> `auto` sequence docs/17 section 9.5 designed, executed as designed:
`lap01` measured that a reset would have recovered it, `lap02` turned it on and it
did. **4.7x the distance of lap01.**

## But the driving degraded, and the lane departure is real

`|ey|` median per 10 s window: 20, 27, 37, 63, 39, 30, 45, 63, 45, 72, 73 mm.
Against lap01's 9.9 mm median over the whole run.

The C-01 event at cycle 520 is **not a one-cycle glitch** — unlike lap01's. `ey`
grows monotonically 74 -> 116 -> **150.3 mm** over 12 cycles / 1.2 s at a steady
0.19 m/s, in a curve of `kappa` -1.2 -> -2.03. C-03 and C-01 both fire at the peak,
10 mm short of C-01's 160 mm threshold. This is the car genuinely running wide.

**C-04 never fired, and cannot on commanded motion.** [AMENDED 01.09: it *did* fire in the
evening session, 58 and 40 cycles, all on ZED velocity artefacts at a reported 0.25-1.30 m/s
- docs/17 SS13.5. The dead-zone argument stands; the word "cannot" does not.] Speed held 0.19-0.199 m/s through a `kappa` 2.0
curve because `v_max_curve_mps` 0.25 > the deployed 0.22 (D-69 finding (ii),
docs/17 section 8.8). Third observation of that dead zone; first one with a
measured `ey` excursion attached to it.

**In `monitoring` C-01 and C-03 fired and did nothing.** The cage DETECTED the
departure and was not permitted to act. Under `enforcement` it would have.

## New finding: the policy's frame stack is never re-initialised

`rl_policy_node` subscribes to the image topic ONLY — not to `/emergency`, not to
`/cage_reset` — and `_first` is set False after the first frame of the process and
never set again (`rl_policy_node.py:189,273-275`). So the k=4 stack is reset once,
at start-up. During a C-05 latch it fills with frames of a stationary scene, and on
release the policy acts for ~0.4 s on a temporally degenerate observation that no
training episode contained.

Real, and newly exposed: before today a stop ended the run, so it never mattered.
**But keep its weight honest** — it is a 0.4 s effect per reset (about 76 mm of
travel), four times in this run. It does not by itself explain a run-wide
degradation from 9.9 to 41.2 mm.

## What is NOT established

* **Why lap02 drove so much worse than lap01.** The leading candidate is that it
  started mid-curve and off-centre and never got a clean straight to settle on,
  compounded by each reset restarting it from a bad pose. That is a hypothesis, not
  a measurement — a run started from the marked start with `auto` would test it.
* Whether the final departure and the cycle-520 excursion share a cause.
* No floor-mark measurement applies: the car never started from the mark.

## Third departure in the same curve

26.08 lost the lane there twice, today once more. Common to all three: it is the
tightest curve on the circuit and C-04 is structurally unable to slow the car for
it. Per section 9.6, do NOT lower `max_speed_mps` to chase this in the same run --
all three candidate causes improve with less speed, so it cannot discriminate.
