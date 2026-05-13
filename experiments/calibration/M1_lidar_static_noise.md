# M-1 — Static LiDAR noise on lateral offset

**Goal.** Determine the standard deviation σ of the noise on the
LiDAR-observed lateral offset under stationary vehicle conditions, and
detect any position-dependent bias.

**Closes.** SR-001 `d_max` margin (the 0.04 m component "absorbing the
joint uncertainty of LiDAR-observed lateral noise" in
`docs/03_safety_requirements.md` §SR-001).

**Effort.** Under one hour once the perception pipeline is running.
Does not require the physical platform — sim perception is sufficient
for the F1 closure; a re-run on the physical perception stack is
folded into F5 calibration when ODD-PHYS-1 is characterised.

## Procedure

1. With the cage and policy nodes disabled (or with the policy
   replaced by a constant zero-command stub), place the vehicle at a
   known lateral position with the perception pipeline running at
   nominal rate (20 Hz, `cage.control.cycle_period_ms = 50`).
2. Log the topic `/state_obs` (specifically the `lateral_offset_m`
   field) for at least **5 minutes of wall-clock time** to obtain
   ≥ 6000 samples.
3. Repeat the procedure at three lateral positions: centred
   (`y = 0`), `y = +0.10 m`, and `y = -0.10 m`, using the simulator's
   pose-spawn mechanism. The three positions detect bias that depends
   on lateral location.
4. For each position, compute:
   - sample mean μ of the observed lateral offset.
   - sample standard deviation σ.
   - empirical 95th-percentile absolute deviation from μ.
   - autocorrelation at lag 1 (to confirm samples are not
     pathologically correlated, which would bias σ downward).

## Expected output

`M1_results.json` with the schema:

```json
{
  "measurement_id": "M-1",
  "executed_on": "YYYY-MM-DD",
  "executed_by": "name",
  "platform": "sim" | "physical",
  "perception_pipeline_version": "git SHA or descriptor",
  "samples_per_position": <int>,
  "positions": [
    {
      "ground_truth_y_m": 0.0,
      "mean_observed_y_m": <float>,
      "std_dev_m": <float>,
      "p95_abs_deviation_m": <float>,
      "lag1_autocorr": <float>
    },
    {"ground_truth_y_m": 0.10, "...": "..."},
    {"ground_truth_y_m": -0.10, "...": "..."}
  ],
  "decision": "<see below>"
}
```

## Decision rule

Let `σ_max` be the maximum standard deviation across the three
positions, and `|bias|_max` be the maximum absolute deviation of
sample mean from ground truth across positions.

- **If `σ_max ≤ 0.01 m` and `|bias|_max ≤ 0.005 m`** → SR-001 d_max
  margin is defensible as currently written. Decision: "SR-001
  confirmed at d_max = 0.16 m".
- **If `σ_max ≤ 0.02 m`** → margin is tight but acceptable. Decision:
  "SR-001 confirmed at d_max = 0.16 m with reduced margin; document
  the reduced margin in the rationale and consider widening Δ in a
  future revision."
- **If `σ_max > 0.02 m`** → the 0.04 m margin in d_max is
  insufficient. Decision: "SR-001 d_max revised downward to
  ROAD_WIDTH/2 - (σ_max·3 + LATENCY_NOMINAL·v_max + half_footprint)
  to preserve at least 3σ on the noise component."

## Results

*To be filled in upon execution.*

| Position (ground truth `y_m`) | Mean obs. (m) | σ (m) | p95 |abs. dev| (m) | Lag-1 autocorr |
| ----------------------------- | ------------- | ----- | --------------------- | -------------- |
| 0.00                          |               |       |                       |                |
| +0.10                         |               |       |                       |                |
| -0.10                         |               |       |                       |                |

**Decision statement:** *To be filled in upon execution.*

**Propagation actions on completion:**

- Update `docs/03_safety_requirements.md` §SR-001 §Parameters with the
  measured σ_lateral_static value (replacing the "≈ 0.01 m" hypothesis).
- If d_max is revised, propagate to `cage/cage.yaml` (`c01_lane_boundary.d_max_m`)
  and to the rationale text in `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`
  §4.6.4 (SR-001 worked example).
- Add a `docs/CHANGELOG.md` entry describing the change.
- Re-run `tools/check_traceability.py` and `pytest cage/tests/`.
