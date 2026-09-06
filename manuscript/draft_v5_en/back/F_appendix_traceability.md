# Appendix F — Traceability matrix

The matrix exists in two complementary forms that are kept synchronised: a readable one,
organised by mitigation chain, and a machine-processable one over which the validator
checks the eight coverage constraints. A violation of any of them blocks the
corresponding review gate.

## F.1 Summary by mitigation chain

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict (Sim) |
| ------ | ------------------ | ------------ | --------- | ------------------- | ------- |
| H-01 | SR-001 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | Satisfied |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | Satisfied ⁷ |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | Satisfied ⁷ |
| H-02 | SR-011 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | Satisfied |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | Satisfied |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | Satisfied |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | Satisfied ¹ |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | Satisfied |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | Satisfied |
| H-08 | SR-009 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | Satisfied (out-of-band, D-64/D-69) ² |
| H-09 | SR-010 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | Not satisfied — CL-B finding, non-vetoing (D-69) ³ |
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁹ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁹ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁹ |

**Notes to Table F.1.** The eight markers point at the full treatment of each case in the living
traceability document; the condensed version is given here.

- **¹ SR-006 — Satisfied on its own metric (D-39).** The coarse all-scenarios aggregation made it
  inherit a fraction failure unrelated to smoothness, so it is scored directly on its own metric: over
  the steps the rate limiter actually governs — no safety rule overriding, no emergency — the
  per-cycle delta of the committed command respects `δ_max = 0.15` in 559 of 559 evaluable
  enforcement runs; in monitoring only 67.6 % hold and the worst rate reaches 0.43. It is,
  incidentally, the most direct measure of C-06's value.
- **² SR-009 — Satisfied out of band (D-64, ratified by D-69).** SC-PERT-03 was excluded from the
  campaign by protocol, so the verdict does not come from aggregation but from three separately
  measured parts: the nominal policy never stalls; a deliberate attempt to force it to stall does not
  succeed; and the detector does fire on a scripted, genuinely injected stall.
- **³ SR-010 — `Not satisfied`, a determinate class-B finding (D-69).** It is the one requirement the
  work closes as unmet, measured twice on two different policies: 30 of 85 in-ODD grid points on
  the earlier policy, 16 of 85 on the reference one. It concentrates on the co-activation of C-01 and
  C-02 and vanishes where there is no conflict between lateral and heading correction. Being class B
  it does not veto the global verdict.
- **⁴ SR-012 / SR-014 — Satisfied.** The perturbed scenarios pass in enforcement, the injected false
  lane included. Where the scenario criterion marks a failure it does so *only* on the no-emergency
  clause: the cage executed its controlled stop on a degraded percept and the criterion scores that
  safe stop as a failure. SR-012's own criterion is met in every case.
- **⁵ SR-013 — Satisfied.** The open-loop stop executes within budget with no road-edge contact, and
  the two-sided coverage closes the gap the earlier version carried by having no second adverse
  scenario.
- **⁶ SC-PERT-11 / 12 / 13** — worn markings, image degradation and both compounded — broaden the
  adverse family of SR-012 / SR-014 and give SR-013 its second adverse scenario. They score 30/30,
  40/40 and 40/40 in enforcement, against 0/30, 23/40 and 0/40 in monitoring.
- **⁷ SR-002 / SR-003 — Satisfied on their own criterion (D-47).** The SC-EDGE-01 "failure" is a
  performance clause inherited from the oval — heading recovery time — which is the documented
  satisfaction criterion of neither: SR-002 requires `M-P4 ≤ 25°` and the measured maximum is 14.2°;
  SR-003 requires a time margin that is never compromised, with a maximum lateral excursion of 0.043 m
  and zero emergencies. See §8.3.
- **⁹ The verdict of record is the 2-D PPO 550k campaign** (31.07.2026, D-69). SR-012 / SR-013 / SR-014
  are satisfied on both camera arms; the rows above cite that campaign as current evidence and
  retain GE4-V2 as the frozen G4 gate record.

## F.2 Machine-processable form

Each row represents a chain from a hazard to a metric. A hazard appears in
several rows because it spans several chains. The physical verdict column is declared not
executed in its entirety: the deployment chain is built and has driven on hardware, but no
run has been executed under the scenario protocol (§10.4d–e).

| Hazard | Requirement | Rule | Type | Scenario | Metric | Sim. verdict | Phys. verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-01 | M-S1 | satisfied | not executed |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-02 | M-S1 | satisfied | not executed |
| H-01 | SR-001 | C-01 | cage rule | SC-EDGE-02 | M-S1 | satisfied | not executed |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-01 | M-S2 | satisfied | not executed |
| H-01 | SR-003 | C-03 | cage rule | SC-NOM-02 | M-S4 | satisfied | not executed |
| H-01 | SR-003 | C-03 | cage rule | SC-EDGE-01 | M-S4 | satisfied | not executed |
| H-02 | SR-002 | C-02 | cage rule | SC-EDGE-01 | M-P4 | satisfied | not executed |
| H-02 | SR-002 | C-02 | cage rule | SC-EDGE-04 | M-P4 | satisfied | not executed |
| H-02 | SR-003 | C-03 | cage rule | SC-EDGE-01 | M-S4 | satisfied | not executed |
| H-03 | SR-004 | C-04 | cage rule | SC-NOM-02 | M-P3 | satisfied | not executed |
| H-03 | SR-004 | C-04 | cage rule | SC-EDGE-03 | M-P3 | satisfied | not executed |
| H-04 | SR-005 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfied | not executed |
| H-05 | SR-006 | C-06 | cage rule | SC-NOM-01 | M-I5 | satisfied | not executed |
| H-05 | SR-006 | C-06 | cage rule | SC-NOM-02 | M-I5 | satisfied | not executed |
| H-06 | SR-007 | C-05 | cage rule | SC-PERT-02 | M-S3 | satisfied | not executed |
| H-07 | SR-005 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfied | not executed |
| H-07 | SR-008 | C-05 | cage rule | SC-NOM-03 | M-S3 | satisfied | not executed |
| H-07 | SR-008 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfied | not executed |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-04 | M-S1 | satisfied | not executed |
| H-10 | SR-012 | C-02 | cage rule | SC-PERT-05 | M-S1 | satisfied | not executed |
| H-10 | SR-012 | C-03 | cage rule | SC-PERT-06 | M-S2 | satisfied | not executed |
| H-10 | SR-012 | — | training | SC-PERT-04 | M-S2 | satisfied | not executed |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-09 | M-S1 | satisfied | not executed |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-10 | M-S1 | satisfied | not executed |
| H-11 | SR-013 | C-05 | cage rule | SC-PERT-07 | M-S3 | satisfied | not executed |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-08 | M-S1 | satisfied | not executed |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-08 | M-S3 | satisfied | not executed |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-09 | M-S3 | satisfied | not executed |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-10 | M-S3 | satisfied | not executed |
| H-08 | SR-009 | — | training constraint | SC-NOM-01 | M-P6 | satisfied | not executed |
| H-08 | SR-009 | — | training constraint | SC-PERT-03 | M-P6 | satisfied | not executed |
| H-09 | SR-010 | — | arbiter | SC-EDGE-04 | M-I3 | satisfied | not executed |
| H-09 | SR-010 | — | arbiter | SC-EDGE-05 | M-S2 | not satisfied | not executed |

## F.3 Verified constraints

The validator checks mechanically that: every hazard is referenced by at least one
requirement; every requirement references at least one hazard; every requirement is implemented by
at least one rule, training constraint or arbitration property; every rule
implements at least one requirement; every rule is exercised by at least one scenario; every
scenario references at least one requirement; every requirement has at least one verifying
metric; and every referenced metric is defined.

**Status at the close: all checks pass, with no orphans and no warnings.**
