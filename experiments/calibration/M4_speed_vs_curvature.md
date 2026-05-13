# M-4 — Speed-vs-curvature tracking envelope

**Goal.** Characterise the maximum stable forward speed at the tightest
curvature available on the test track, so that SR-004 `v_max_curve`
and the interpolation coefficient `k_κ` are anchored in empirical
data rather than in conservative guesses.

**Closes.** SR-004 `v_max_curve` and `k_κ` (currently 0.25 m/s and
0.3 m/s per unit curvature respectively, both flagged as provisional
in `docs/03_safety_requirements.md`) and confirms the working
assumption `KAPPA_MAX ≈ 0.83 rad/m` referenced in SR-004's rationale.

**Effort.** Two hours, requires physical platform and a hand-tuned
PD controller (or equivalent open-loop steering input).

## Procedure

1. Identify the section of `odd3_curvy_loop` with the highest local
   curvature; record the curvature value `κ_test` from the map
   geometry (or from a tape-measure estimation of the local turning
   radius and conversion `κ = 1 / R`).
2. Install a hand-tuned PD controller (or an open-loop oscillatory
   steering input that produces a stable turn) — the controller
   need not be the trained RL policy. The goal is to test the
   *platform's* tracking envelope, not the policy's behaviour.
3. Approach the curve at low speed `v = 0.1 m/s` and confirm clean
   tracking (the lateral RMSE stays below 0.05 m).
4. Repeat the approach, incrementing the commanded speed by 0.05 m/s
   at each iteration: 0.10, 0.15, 0.20, 0.25, 0.30, 0.35 m/s.
5. The empirical `v_max_curve_empirical` is the largest commanded
   speed at which lateral RMSE stays below 0.05 m and no wheel
   slip is observed. Repeat each speed level at least 3 times to
   confirm stability.
6. (Optional) Repeat the procedure at a curvature `κ_intermediate =
   0.5 · κ_test` to enable a two-point fit of the linear
   interpolation `v_max(κ) = v_max_straight - k_κ · |κ|`.

## Expected output

`M4_results.json`:

```json
{
  "measurement_id": "M-4",
  "executed_on": "YYYY-MM-DD",
  "executed_by": "name",
  "platform": "physical",
  "track_section": "odd3_curvy_loop, tightest curve",
  "kappa_test_inv_m": <float>,
  "trials": [
    {
      "commanded_speed_mps": 0.10,
      "lateral_rmse_m": <float>,
      "wheel_slip_observed": false,
      "completion": true
    },
    {"commanded_speed_mps": 0.15, "...": "..."}
  ],
  "v_max_curve_empirical_mps": <float>,
  "intermediate_curvature_trials": [
    {"kappa_inv_m": <float>, "v_max_empirical_mps": <float>}
  ],
  "fitted_k_kappa_mps_per_curvature": <float | null>,
  "decision": "<see below>"
}
```

## Decision rule

Let `v_max_emp = v_max_curve_empirical` measured at `κ_test`. Apply
a safety margin of 20 %: the new `v_max_curve` is `0.8 · v_max_emp`.

- **If `v_max_emp ≥ 0.30 m/s`** → the current SR-004 `v_max_curve =
  0.25 m/s` is conservative; decision: "SR-004 v_max_curve revised
  to `0.8 · v_max_emp` with margin justification in CHANGELOG."
- **If `0.20 m/s ≤ v_max_emp < 0.30 m/s`** → SR-004 confirmed at the
  current value. Decision: "SR-004 v_max_curve confirmed at 0.25 m/s
  (within margin of empirical `v_max_emp`)."
- **If `v_max_emp < 0.20 m/s`** → SR-004 is too permissive. Decision:
  "SR-004 v_max_curve revised down to `0.8 · v_max_emp`; coordinated
  revision of k_κ to preserve the linear interpolation crossing."

If the intermediate-curvature trial is executed, the fitted `k_κ`
from the two-point fit is used in place of the working assumption
0.3. The fitted value is reported and propagated.

## Results

*To be filled in upon execution.*

| v_commanded (m/s) | Lateral RMSE (m) | Wheel slip | Completion |
| ----------------- | ---------------- | ---------- | ---------- |
| 0.10              |                  |            |            |
| 0.15              |                  |            |            |
| 0.20              |                  |            |            |
| 0.25              |                  |            |            |
| 0.30              |                  |            |            |
| 0.35              |                  |            |            |

`v_max_curve_empirical` = ____ m/s

**Decision statement:** *To be filled in upon execution.*

**Propagation actions on completion:**

- Update `docs/03_safety_requirements.md` §SR-004 §Parameters
  (`v_max_curve_mps` and possibly `k_kappa`).
- Update `cage/cage.yaml` (`c04_speed_ceiling.v_max_curve_mps`
  and `k_kappa_mps_per_curvature`) and remove the
  `[provisional, M-4]` annotation.
- Update `docs/08_odd_specification.md` §6.5 (ODD-3 envelope) and
  §9 master parameter table with the measured `κ_test`.
- Close TBD-Q9 (KAPPA_MAX) in the ODD-Spec if `κ_test` is the new
  KAPPA_MAX.
- Add a `docs/CHANGELOG.md` entry.
- Re-run `tools/check_traceability.py` and `pytest cage/tests/`.
