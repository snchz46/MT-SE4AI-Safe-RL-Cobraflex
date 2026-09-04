# Appendix I — Breakdown of the reference campaign

Data generated directly from the campaign artefacts
(`campaign_report.json` and `failure_mode_breakdown.json`): **1,890 runs, 0 errors**,
27 scenarios × 2 modes, over the two-dimensional reference policy.

## I.1 Runs passed by scenario and mode

The verdict in the right-hand column corresponds to *enforcement* mode and is computed against the
pass criterion declared by each scenario, with the fraction threshold that the
scenario fixes.

| Scenario | Enforcement | Monitoring | Enf. verdict |
| --- | ---: | ---: | :-: |
| SC-EDGE-01 | 8/30 | 4/30 | ✗ |
| SC-EDGE-02 | 29/30 | 22/30 | ✓ |
| SC-EDGE-03 | 25/25 | 25/25 | ✓ |
| SC-EDGE-04 | 30/30 | 0/30 | ✓ |
| SC-EDGE-05 | 44/100 | 25/100 | ✗ |
| SC-FRONT-01 | 0/25 | 0/25 | ✗ |
| SC-FRONT-02 | 25/25 | 25/25 | ✓ |
| SC-FRONT-03 | 25/25 | 0/25 | ✓ |
| SC-FRONT-04 | 19/25 | 0/25 | ✗ |
| SC-FRONT-05 | 25/25 | 6/25 | ✓ |
| SC-FRONT-06 | 17/25 | 0/25 | ✗ |
| SC-FRONT-07 | 25/25 | 25/25 | ✓ |
| SC-NOM-01 | 50/50 | 50/50 | ✓ |
| SC-NOM-02 | 49/50 | 44/50 | ✓ |
| SC-NOM-03 | 25/25 | 8/25 | ✓ |
| SC-PERT-01 | 60/60 | 60/60 | ✓ |
| SC-PERT-02 | 40/40 | 40/40 | ✓ |
| SC-PERT-04 | 40/40 | 33/40 | ✓ |
| SC-PERT-05 | 40/40 | 37/40 | ✓ |
| SC-PERT-06 | 40/40 | 40/40 | ✓ |
| SC-PERT-07 | 25/25 | 25/25 | ✓ |
| SC-PERT-08 | 25/25 | 25/25 | ✓ |
| SC-PERT-09 | 25/25 | 0/25 | ✓ |
| SC-PERT-10 | 25/25 | 25/25 | ✓ |
| SC-PERT-11 | 30/30 | 30/30 | ✓ |
| SC-PERT-12 | 40/40 | 32/40 | ✓ |
| SC-PERT-13 | 40/40 | 20/40 | ✓ |

## I.2 Status per requirement

| Requirement | Class | Status in the campaign | Failing scenarios |
| --- | :-: | --- | --- |
| SR-001 | A | satisfied | — |
| SR-002 | A | literal failure | SC-EDGE-01 |
| SR-003 | A | literal failure | SC-EDGE-01 |
| SR-004 | A | satisfied | — |
| SR-005 | A | satisfied | — |
| SR-006 | B | out of band | — |
| SR-007 | A | satisfied | — |
| SR-008 | A | satisfied | — |
| SR-009 | B | insufficient evidence | — |
| SR-010 | B | literal failure | SC-EDGE-05 |
| SR-011 | B | literal failure | SC-EDGE-01 |
| SR-012 | A | satisfied | — |
| SR-013 | A | satisfied | — |
| SR-014 | A | satisfied | — |

## I.3 Safety invariant (enforcement mode)

| Quantity | Value |
| --- | ---: |
| Enforcement runs | 945 |
| Contacts with the road edge | 56 |
| Runs with a lateral excursion ≥ the limit | 69 |
| Maximum lateral excursion (m) | 0.2824 |

The contacts counted correspond entirely to runs whose **initial
condition falls outside the operational domain** (edge and frontier families). Inside the
domain, the count is **zero**.

## I.4 Co-activation grid: breakdown of the negative verdict

Partition of the grid according to whether the injected point falls inside the operational domain:

| Block | Runs | Passed | Failed | Lateral margin violations |
| --- | ---: | ---: | ---: | ---: |
| Inside the ODD | 85 | 42 | 43 | **16** |
| Outside the ODD | 15 | 2 | 13 | 10 |

Breakdown by the combination of rules actually co-activated, which is what localises the
arbitration problem:

| Rule combination | Runs | Failures | Lateral margin violations | Inside the ODD |
| --- | ---: | ---: | ---: | ---: |
| C-01 ∧ C-02 | 20 | 15 | 11 | 15 |
| C-01 ∧ C-02 ∧ C-04 | 20 | 14 | 11 | 15 |
| C-01 ∧ C-03 | 20 | 15 | 4 | 20 |
| C-01 ∧ C-04 ∧ C-06 | 20 | 12 | 0 | 15 |
| C-04 ∧ C-06 | 20 | 0 | 0 | 20 |

The reading is in §8.6: the violations concentrate where the lateral correction and the
heading correction come into conflict, and they disappear where they do not.
