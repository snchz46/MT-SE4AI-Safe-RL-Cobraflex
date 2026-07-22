# D-43 to C-02 Gazebo calibration — PASS

Date: 2026-07-21. This is bounded posterior evidence; it does not alter or
re-score GE4/G4.

## Candidate

- heading readout: joint quadratic fit of both selected lane markings, with
  separate lateral intercepts and shared tangent/curvature;
- global Gazebo measurement gain: `1.60`;
- validity envelope: hashed Gazebo Lane Cam renderer and `complex_b` driven-lane
  geometry through the `|kappa_anchor| = 1.031 1/m` demanding section (exact
  per-cycle local GT maximum 0.978 1/m), at 0.10/0.22 m/s and the tested
  clean/glare/motion-blur conditions;
- unchanged cage limits: `theta_max = 0.4363 rad`,
  `theta_warning = 0.3491 rad`, `d_max = 0.16 m`.

The six heading failures per split were injected while the vehicle was moving,
after a nominal prefix. Ground truth labelled the evidence offline only; neither
the policy/controller nor cage consumed it.

## Results

| Metric | Calibration (seed 2024) | Held-out validation (seed 42) |
| --- | ---: | ---: |
| Cycles | 560 | 560 |
| Centred safe cycles | 392 | 392 |
| Heading-fault cells detected | 6/6 | **6/6** |
| False C-02 / false C-05 in centred band | 0 / 0 | **0 / 0** |
| Max detection delay | 0.10 s | **0.10 s** |
| Controlled-stop upper bound | 0.10 s | **0.10 s** |
| Minimum pre-injection speed | 0.220 m/s | **0.220 m/s** |
| M-S1 maximum | 0.0318 m | **0.0318 m** |
| M-S2 boundary-crossing cycles | 0 | **0** |
| Road-edge contacts | 0 | **0** |
| Safe max `|epsi_cv|` | 0.2962 rad | **0.3086 rad** |
| Fault min `|epsi_cv|` | 0.5702 rad | **0.3830 rad** |
| Safe/fault distribution separation | +0.2740 rad | **+0.0744 rad** |

The lowest held-out fault read (`0.3830 rad`) occurred for the positive injection
at maximum curvature. It was followed by a `0.7250 rad` read and C-02/C-05 in the
next cycle, hence the measured 0.10 s worst-case delay. The retained safe maximum
stayed 0.0405 rad below the canonical C-05 warning threshold.

## Decision

**PASS for the exact hash-bound Gazebo/complex_b envelope above.** The candidate
detects every real heading failure without creating a false C-02/C-05, M-S2
crossing or edge contact. It improves observability instead of subtracting a
curvature term, and the controlled positive/negative faults remain visible.

This is not permission to raise `theta_max` or to reuse Isaac's 40-degree/bias
settings. It also does not qualify an unseen checkpoint: the posterior margin022
checkpoint does not yet exist and must still pass its checkpoint-bound nominal
D-43 preflight before any campaign.

## Evidence and provenance

- Raw cycles: [`raw_cycles.csv`](raw_cycles.csv)
- Machine report: [`report.json`](report.json)
- Scenario matrix: [`matrix.json`](matrix.json)
- Scatter: [`epsi_gt_vs_cv_validation.png`](epsi_gt_vs_cv_validation.png)
- Distributions: [`epsi_abs_distribution_validation.png`](epsi_abs_distribution_validation.png)

Key SHA-256 values from `report.json`: target posterior config
`3ae8f74bca9dee07...`, runtime CV config `4a49c0e7db830f9f...`, canonical cage
`4287fe711b662eb9...`, estimator source `e192e1ec0f206e7a...`, Gazebo world
`3b218c07104b70ae...`, camera URDF `56773a628ed2c16e...`, and generated scenario
bundle `7a3af6aa3f64564...`. The report preserves the collector provenance separately
from the later analysis/binding provenance; the final raw-cycle CSV is
`6d09479cb2aaa40e...`.
