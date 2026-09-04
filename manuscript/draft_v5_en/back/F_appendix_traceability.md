# Appendix F — Traceability matrix

The matrix exists in two complementary forms that are kept synchronised: a readable one,
organised by mitigation chain, and a machine-processable one over which the validator
checks the eight coverage constraints. A violation of any of them blocks the
corresponding review gate.

## F.1 Summary by mitigation chain

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict (Sim) |
| ------ | ------------------ | ------------ | --------- | ------------------- | ------- |
| H-01 | SR-001 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | **Satisfied** |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | **Satisfied** ⁷ |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | **Satisfied** ⁷ |
| H-02 | SR-011 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | **Satisfied** |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | **Satisfied** |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | **Satisfied** |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | **Satisfied** ¹ |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | **Satisfied** |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | **Satisfied** |
| H-08 | SR-009 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | **Satisfied** (out-of-band, D-64/D-69) ² |
| H-09 | SR-010 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | **Not satisfied** — CL-B finding, non-vetoing (D-69) ³ |
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁹ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁹ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁹ |

## F.2 Machine-processable form

Each row represents a chain from a hazard to a metric. A hazard appears in
several rows because it spans several chains. The physical verdict column is declared **not
executed** in its entirety: the deployment chain is built and has driven on hardware, but no
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
| H-09 | SR-010 | — | arbiter | SC-EDGE-05 | M-S2 | **not satisfied** | not executed |

## F.3 Verified constraints

The validator checks mechanically that: every hazard is referenced by at least one
requirement; every requirement references at least one hazard; every requirement is implemented by
at least one rule, training constraint or arbitration property; every rule
implements at least one requirement; every rule is exercised by at least one scenario; every
scenario references at least one requirement; every requirement has at least one verifying
metric; and every referenced metric is defined.

**Status at the close: all checks pass, with no orphans and no warnings.**
