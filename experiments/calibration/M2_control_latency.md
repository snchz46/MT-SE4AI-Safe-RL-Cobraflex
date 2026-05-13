# M-2 — End-to-end control latency

**Goal.** Determine the time elapsed from the arrival of a state
observation on `/state_obs` to the publication of the corresponding
safe action on `/safe_action`, and (separately) to the actuator
response. Both medians and tail percentiles are required.

**Closes.** SR-001 latency assumption (the "drift over one nominal
control latency `v_max · ODD-1.LATENCY_NOMINAL = 0.5 m/s · 50 ms =
0.025 m`" component of d_max margin in
`docs/03_safety_requirements.md` §SR-001) and confirms the nominal
`LATENCY_NOMINAL = 50 ms` claim of the ODD specification.

**Effort.** Under one hour in simulation.

## Procedure

1. With the cage and policy nodes running in nominal configuration
   (enforcement mode, `cage.control.cycle_period_ms = 50`), drive the
   vehicle for several minutes on the straight-road map
   `odd1_straight_road` with a hand-tuned PD controller or a stub
   policy that produces consistent (non-zero) commands.
2. Log timestamps for both `/state_obs` (the input) and
   `/safe_action` (the output of the cage) using the ROS2 timestamp
   on each message. For each `/safe_action` message, compute the
   latency as the difference between its timestamp and the timestamp
   of the most recent `/state_obs` it consumed.
3. (Optional, if platform is available) Add a third timestamp at
   the actuator-response level by logging encoder readback or a
   commanded-vs-observed delta with known dynamics; the difference
   between `/safe_action` publication and observed actuator response
   is the actuator latency component.
4. Compute median, 5th percentile, 95th percentile and 99th
   percentile of the latency distribution from a sample of at least
   2000 cycles.

## Expected output

`M2_results.json`:

```json
{
  "measurement_id": "M-2",
  "executed_on": "YYYY-MM-DD",
  "executed_by": "name",
  "platform": "sim" | "physical",
  "n_cycles": <int>,
  "latency_obs_to_safe_action_ms": {
    "median": <float>,
    "p05": <float>,
    "p95": <float>,
    "p99": <float>,
    "max": <float>
  },
  "latency_safe_action_to_actuator_ms": {
    "median": <float | null>,
    "p95": <float | null>,
    "comment": "null if not measured (sim-only run)"
  },
  "decision": "<see below>"
}
```

## Decision rule

The reference value is `LATENCY_NOMINAL = 50 ms` (one control cycle).

- **If `p95(latency_obs_to_safe_action) ≤ 50 ms`** → SRS is consistent
  with the nominal model. Decision: "SR-001 latency assumption
  confirmed at 50 ms (one control cycle)."
- **If `50 ms < p95 ≤ 75 ms`** → tighten the cycle period to
  `cycle_period_ms = 33` (30 Hz) **or** widen the latency component of
  the d_max margin to `v_max · 75 ms = 0.0375 m`, requiring
  recomputation of d_max. Decision states the chosen path.
- **If `p95 > 75 ms`** → the cage is not meeting timing assumptions
  and must be diagnosed before G1 can close; check the executor
  configuration of the ROS2 node, threading model, and per-callback
  cost.

## Results

*To be filled in upon execution.*

| Quantity                          | Value (ms) |
| --------------------------------- | ---------- |
| Median latency obs→safe_action    |            |
| 95th percentile                   |            |
| 99th percentile                   |            |
| Max observed                      |            |
| Median actuator response (if any) |            |

**Decision statement:** *To be filled in upon execution.*

**Propagation actions on completion:**

- Update `docs/03_safety_requirements.md` §SR-001 §Parameters with
  the measured 95th-percentile latency, replacing the implicit
  assumption of "50 ms latency = nominal cycle period".
- Update `docs/08_odd_specification.md` §9 master parameter table
  with the measured value of `LATENCY_NOMINAL` if it differs from
  50 ms.
- If d_max is revised as a consequence, propagate to
  `cage/cage.yaml` (`c01_lane_boundary.d_max_m`) and to Chapter 4
  §4.6.4.
- Add a `docs/CHANGELOG.md` entry describing the change.
- Re-run `tools/check_traceability.py` and `pytest cage/tests/`.
