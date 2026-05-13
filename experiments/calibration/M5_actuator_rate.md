# M-5 — Actuator rate envelope

**Goal.** Determine the maximum per-cycle command change that the
steering servo and the throttle motor can physically achieve, so that
SR-006 `δ_max` for steering and throttle is set below this envelope
with margin rather than as an ad-hoc guess.

**Closes.** SR-006 `δ_max_steering` and `δ_max_throttle` (currently
0.15 and 0.10 normalised units per 50 ms cycle, both flagged as
provisional in `docs/03_safety_requirements.md`).

**Effort.** One hour, requires physical platform.

## Procedure

1. With the platform stationary on a flat surface, command a step
   input on the steering servo: from `-1` (full left) to `+1` (full
   right) in normalised units, applied as a single instantaneous
   command transition. Log the actual commanded value (after any
   firmware-level clamping) and the observed servo position from the
   encoder readback at the highest available sample rate (≥ 200 Hz).
2. Measure the **time to settle** as the elapsed time from command
   transition to the moment the observed servo position is within
   2 % of the new commanded value and stays there for at least 50 ms.
3. Convert the time-to-settle into a maximum per-cycle rate by
   computing `δ_actuator_max_steering = 2 / (time_to_settle / 50 ms)`.
   The factor 2 represents the command-range span; the divisor
   represents the number of 50 ms cycles required to traverse it.
4. Repeat the procedure for the throttle motor with a step input
   from `-1` (full reverse) to `+1` (full forward), measuring time
   to reach 95 % of the commanded value (since throttle dynamics
   include both motor electromechanical response and gearbox
   inertia, "settle" here uses 95 % rather than 98 %).
5. Repeat each step at least **3 times** to characterise variance.
   Repeat at low and high battery states (M-3 includes battery
   voltage logging) to detect dependence on state-of-charge.

## Expected output

`M5_results.json`:

```json
{
  "measurement_id": "M-5",
  "executed_on": "YYYY-MM-DD",
  "executed_by": "name",
  "platform": "physical",
  "battery_voltage_V": <float>,
  "steering": {
    "trials": [
      {"time_to_settle_ms": <float>, "delta_actuator_max_per_cycle": <float>}
    ],
    "delta_actuator_max_steering_per_cycle": <float>,
    "comment": "<text>"
  },
  "throttle": {
    "trials": [
      {"time_to_reach_95pct_ms": <float>, "delta_actuator_max_per_cycle": <float>}
    ],
    "delta_actuator_max_throttle_per_cycle": <float>,
    "comment": "<text>"
  },
  "decision": "<see below>"
}
```

## Decision rule

Let `δ_act_steer` and `δ_act_thr` be the averaged
`delta_actuator_max_*_per_cycle` values.

A safe rule of thumb is to set the cage's rate limiter at **half the
actuator envelope**, so that the limiter intervenes only on commands
that would saturate the actuator rather than on commands within its
physical capability.

- **If `δ_act_steer ≥ 0.30`** → SR-006 `δ_max_steering = 0.15`
  confirmed (it equals half the actuator envelope at this floor).
  Decision: "SR-006 δ_max_steering confirmed at 0.15."
- **If `δ_act_steer < 0.30`** → SR-006 must be revised down to
  `0.5 · δ_act_steer`. Decision: "SR-006 δ_max_steering revised
  from 0.15 to `0.5 · δ_act_steer`."

The same rule applies for throttle with the threshold scaled to the
current SR-006 throttle default (`δ_max_throttle = 0.10`, hence
trigger threshold `δ_act_thr ≥ 0.20`).

A complementary cross-check, deferred to F3 once the first training
prototype is available, compares `δ_max` against the 95th-percentile
delta of the policy's natural action distribution. The current SR-006
rationale calls out this dual gate (M-5 + F3 prototype) explicitly.

## Results

*To be filled in upon execution.*

### Steering trials

| Trial | Time to settle (ms) | δ_actuator_max per cycle |
| ----- | ------------------- | ------------------------ |
| 1     |                     |                          |
| 2     |                     |                          |
| 3     |                     |                          |

### Throttle trials

| Trial | Time to 95 % (ms) | δ_actuator_max per cycle |
| ----- | ----------------- | ------------------------ |
| 1     |                   |                          |
| 2     |                   |                          |
| 3     |                   |                          |

**Decision statement:** *To be filled in upon execution.*

**Propagation actions on completion:**

- Update `docs/03_safety_requirements.md` §SR-006 §Parameters per
  decision.
- Update `cage/cage.yaml` (`c06_rate_limiter.delta_max_*`) and
  remove the `[provisional, M-5]` annotation.
- Add a `docs/CHANGELOG.md` entry.
- Re-run `tools/check_traceability.py` and `pytest cage/tests/`.
- Schedule the F3 cross-check against the policy's natural action
  distribution (the second gate of SR-006 rationale).
