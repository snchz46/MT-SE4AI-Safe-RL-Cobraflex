# M-3 — Maximum platform deceleration

**Goal.** Determine the maximum deceleration achievable on the
CobraFlex 1:14 platform (or its simulated analogue) under saturated
brake or reverse-throttle command, from the operating-speed envelope
of SR-004.

**Closes.** SR-005 `a_min` parameter (currently set to 0.3 m/s²,
flagged as provisional in `docs/03_safety_requirements.md`) and
SR-008 `t_stop_max` (currently 1.7 s, consistent with `a_min = 0.3`
at `v = v_max_straight = 0.5 m/s`).

**Effort.** One hour, requires physical platform (or representative
simulation with verified actuator dynamics).

## Procedure

1. With the platform at rest on the straight section of the test
   track, command full forward throttle and accelerate to a target
   speed.
2. When the speed reaches `v = 0.5 m/s` (the maximum nominal
   operating speed under SR-004 on a straight section), command
   either full reverse throttle or full brake (whichever the
   platform's actuation supports), and continue to log forward speed
   `v(t)` at 100 Hz or higher until the platform reaches `v = 0`.
3. Compute the achieved deceleration as the slope of `v(t)` between
   the moment of brake command and the moment of full stop.
   Report the average deceleration and the maximum instantaneous
   deceleration.
4. Repeat at `v = 0.3 m/s` to confirm the deceleration is
   approximately speed-independent (or characterise its dependence
   on initial speed if it is not).
5. Repeat each measurement at least **5 times** to characterise
   variance.

## Expected output

`M3_results.json`:

```json
{
  "measurement_id": "M-3",
  "executed_on": "YYYY-MM-DD",
  "executed_by": "name",
  "platform": "physical",
  "platform_battery_voltage_at_start_V": <float>,
  "platform_battery_voltage_at_end_V": <float>,
  "trials": [
    {
      "initial_speed_mps": 0.5,
      "average_deceleration_mps2": <float>,
      "max_deceleration_mps2": <float>,
      "stopping_time_s": <float>,
      "stopping_distance_m": <float>
    },
    {"initial_speed_mps": 0.3, "...": "..."}
  ],
  "a_max_brake_mps2": <float>,
  "comment_on_speed_dependence": "<text>",
  "decision": "<see below>"
}
```

## Decision rule

Let `a_max_brake` be the average deceleration averaged across the
five trials at `v = 0.5 m/s`.

- **If `a_max_brake ≥ 0.4 m/s²`** → SR-005 `a_min` may be raised to
  `0.4 m/s²` and SR-008 `t_stop_max` tightened correspondingly to
  `0.5 / 0.4 = 1.25 s` (rounded conservatively to 1.3 s). Decision:
  "SR-005 a_min revised from 0.3 to 0.4 m/s²; SR-008 t_stop_max
  revised from 1.7 to 1.3 s; coordinated revision recorded in
  CHANGELOG."
- **If `0.3 m/s² ≤ a_max_brake < 0.4 m/s²`** → SR-005 `a_min = 0.3
  m/s²` is achievable with margin. Decision: "SR-005 a_min confirmed
  at 0.3 m/s²; SR-008 t_stop_max confirmed at 1.7 s."
- **If `a_max_brake < 0.3 m/s²`** → the platform cannot satisfy the
  current SR-005. Decision: "SR-005 a_min revised down to
  a_max_brake; SR-004 v_max_straight reduced to `a_min · 1.7 s`
  to preserve the SR-005 ↔ SR-008 consistency; coordinated revision
  recorded in CHANGELOG."

## Results

*To be filled in upon execution.*

| Trial | v₀ (m/s) | a_avg (m/s²) | a_max (m/s²) | t_stop (s) | d_stop (m) |
| ----- | -------- | ------------ | ------------ | ---------- | ---------- |
| 1     | 0.5      |              |              |            |            |
| 2     | 0.5      |              |              |            |            |
| 3     | 0.5      |              |              |            |            |
| 4     | 0.5      |              |              |            |            |
| 5     | 0.5      |              |              |            |            |
| 6     | 0.3      |              |              |            |            |
| 7     | 0.3      |              |              |            |            |
| 8     | 0.3      |              |              |            |            |

**Decision statement:** *To be filled in upon execution.*

**Propagation actions on completion:**

- Update `docs/03_safety_requirements.md` §SR-005 §Parameters
  (`a_min`) and §SR-008 §Parameters (`t_stop_max`) per decision.
- Update `cage/cage.yaml` (`c05_emergency.a_min_mps2`) and remove
  the `[provisional, M-3]` annotation.
- If `v_max_straight` is reduced as a consequence, update SR-004,
  `cage.yaml` (`c04_speed_ceiling.v_max_straight_mps`) and the
  ODD specification §9 master parameter table.
- Add a `docs/CHANGELOG.md` entry describing the coordinated
  SR-005 / SR-008 (/ SR-004) revision and the cage.yaml version
  bump.
- Re-run `tools/check_traceability.py` and `pytest cage/tests/`.
