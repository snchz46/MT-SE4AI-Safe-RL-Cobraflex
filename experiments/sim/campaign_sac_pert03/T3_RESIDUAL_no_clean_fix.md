# T3 apex-exit residual — offline proof that no clean single-frame fix exists (25.07.2026)

The 2/20 released-enforcement false emergencies (SC_PERT_03_ANALYSIS.md) both occur at the
SAME apex (s≈8.9): true ey small+stable (0.9–1.8 cm), CV ey transiently noisy up to ~4.5 cm,
breaking T3's 0.03 m drift gate so the uncapped cv_epsi (−0.49) trips C-02/C-05.

Tested candidate fix: disengage T3 (uncap) only when the window has drifted AND is genuinely
off-centre (max|cv_ey| > MAG), so a bounded CV-ey noise spike keeps the cap engaged. Evaluated
offline against (i) all 20 released-enf campaign runs and (ii) the held-out (seed 42) D-43/C-02
calibration faults:

| MAG (m) | apex false emergencies | calibration fault detection max delay | faults missed |
| ---: | ---: | ---: | --- |
| 0.045 | 0/20 | **2 frames (0.20 s)** | none |
| 0.05  | 0/20 | **2 frames (0.20 s)** | none |
| 0.06  | 0/20 | 2 frames | val_07 |
| 0.08  | 0/20 | 2 frames | val_07, val_11 |

Current T3 (no MAG gate) detects every fault in **1 frame (0.10 s)** and has 0 missed. Every
variant that removes the apex false emergencies pushes real-fault detection to the 0.20 s budget
EDGE (zero margin) and, past MAG=0.05, starts missing faults. Root cause: the false apex CV-ey
transient (~0.045 m) and a real fault's first-frame CV-ey jump (~0.054 m) are only ~9 mm apart —
the H-12 single-frame thinness, now in the ey channel.

**Conclusion: no clean fix. Keep T3 at its current operating point.** It guarantees 1-frame
fault detection at the cost of a rare (2/20, one apex) *fail-safe* false emergency — an
availability cost (an unnecessary controlled stop), not a missed hazard. Any "fix" trades
guaranteed detection speed for fewer false stops, the wrong direction for a safety cage. Recorded
as an accepted CL-B residual, not a code change.
