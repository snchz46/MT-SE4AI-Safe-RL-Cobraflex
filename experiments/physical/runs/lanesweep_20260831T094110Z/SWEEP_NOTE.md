# Lane-estimator offset sweep — 2026-08-31, rectified, hands-off, on the ground

The "clean test, not yet run" prescribed by M-7 §3b: car on the ground, hands off,
tape-measured offsets, 10 s per point, rectified (`M6_results.json`), `near_secant`/1.0,
`policy:=false` so nothing could drive. Single location: start of the straight.

Sign: + = car LEFT of the lane centreline. Road half-width 255 mm.

## Result 1 — the M-6/M-7 ey under-read is NOT present when rectified

| side | n | scale | intercept | r2 |
| --- | --- | --- | --- | --- |
| + (car left)  | 5 | **1.058** | +0.21 mm | 0.99872 |
| - (car right) | 4 | **0.991** | -3.55 mm | 0.97746 |

M-6 propagated 0.72; M-7 §4 measured 0.68-0.83 x true - 10 mm hands-off. Neither
reproduces rectified. C-01 (160 mm) fires at a true 151 mm (left) / 158 mm (right),
leaving ~100 mm to the road edge — not the 14-48 mm of M-7 §4.

The -10 mm offset term also disappears: measured -11.7 mm with the wheels held in
the air, +0.7 mm with the car on the ground. Two things changed at once (support and
repositioning), so this is consistent with, not proof of, IPM pitch sensitivity.

## Result 2 — the estimator is UNSTABLE on the right, and confident while wrong

| true | reported | sd | range | invalid |
| --- | --- | --- | --- | --- |
| +60 | +63.5 | **0.5** | 62.1..64.5 (span 2.4) | 0/86 |
| -60 | -68.1 | **8.4** | -99.8..-56.5 (span 43.3) | 0/81 |
| -60 (repeat) | -68.6 | 6.9 | -99.6..-61.9 | 0/81 |
| -100 | -96.3 | 6.2 | -122.2..-90.6 | 0/100 |

Dispersion is ~10x worse on the right (sd 6.2-8.4 mm vs 0.5-0.9), the point ratio
swings 0.963-1.143 there against 1.034-1.079 on the left, and the excursions sit
~31 mm off the mode — the signature of a pairing that flips between candidate line
pairs, which is the mechanism M-7 §3b identified (`n_lines` 4, wrong pair chosen).
It reproduces across two consecutive runs with the car untouched.

`/perception_invalid` stayed False for every one of the 705 cycles in this sweep.
The estimator does not fail here; it is confidently wrong (H-12 / D-43).

## Result 3 — the +-55 mm pairing collapse does not reproduce

0/440 invalid cycles out to +100 mm, sd 0.5-0.9 mm throughout. M-7 flagged its
+-55 mm figure as "indicative rather than established" and suspected the hand
sweep; that suspicion is confirmed on the LEFT side. On the right the estimate
degrades from 60 mm on, but as dispersion, not as rejection.

## Limits of this measurement

* **One location.** The whole sweep was taken at the start of the straight, where
  the scene is asymmetric (an adjacent red carriageway to the left of the lane,
  plain green plus skirting to the right). Whether the right-side instability
  generalises around the circuit is NOT established here — M-7's finding came from
  a full circuit recording, this did not.
* Between-point scatter is +-2 mm, larger than the within-point sd, so tape
  placement — not the estimator — dominates the residuals of the fit.
* `preflight_deploy.py lanecheck` reports PASS on `sd_ey <= 10 mm`, so it passed
  every right-side point while the estimate swung 43 mm on a stationary car. That
  threshold does not catch this failure.

Raw data: `lane_sweep.csv`.
