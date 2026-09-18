# Appendix F — Traceability matrix

The matrix exists in two forms that are kept in sync. One is readable and organised by mitigation chain. The other can be processed by a machine, and the checker uses it to verify the eight coverage constraints. If any of them is broken, the corresponding review gate is blocked.

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
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁸ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁸ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁸ |

**Notes to Table F.1.** The eight markers point to the full discussion of each case in the living traceability document. A short version is given here.

- **¹ SR-006 — Satisfied on its own metric (D-39).** When it was aggregated coarsely over "all scenarios", it inherited a failure in the pass fraction that had nothing to do with smoothness. So it is scored directly on its own metric. In the steps that the rate limiter really controls (no safety rule taking over and no emergency), the per-cycle change of the applied command stays within `δ_max = 0.15` in all 840 enforcement runs that have such steps; the remaining 105 end in emergency and contribute no sample. In monitoring only 263 of 945 stay within it (27.8 %), with a worst per-cycle change of 2.0. It is the most direct measure of what C-06 is worth. The method was first applied to the earlier campaign (559/559 enforcement against 67.6 % in monitoring, worst 0.43); the figures above are the verdict of record.
- **² SR-009 — Satisfied out of band (D-64, confirmed by D-69).** SC-PERT-03 was left out of the campaign by protocol, so the verdict does not come from aggregation but from three parts measured separately: the nominal policy never stalls, a deliberate attempt to make it stall does not work, and the detector does fire on a real stall injected by a script.
- **³ SR-010 — `Not satisfied`, a confirmed class B finding (D-69).** It is the only requirement the work closes as not met, and it was measured twice on two different policies: 30 of 85 in-ODD grid points with the earlier policy, and 16 of 85 with the reference one. It is concentrated where C-01 and C-02 fire together, and it disappears where the lateral and heading corrections do not conflict. Since it is class B, it does not block the global verdict.
- **⁴ SR-012 / SR-014 — Satisfied.** The perturbed scenarios pass in enforcement, including the one with an injected false lane. When a scenario criterion marks a failure, it does so *only* because of the no-emergency clause: the cage made its controlled stop on degraded perception, and the criterion counts that safe stop as a failure. SR-012's own criterion is met in every case.
- **⁵ SR-013 — Satisfied.** The open-loop stop happens within the time budget and without touching the road edge. Having coverage on both sides closes the gap of the earlier version, which had no second adverse scenario.
- **⁶ SC-PERT-11 / 12 / 13** (worn markings, image degradation and both combined) widen the adverse family of SR-012 / SR-014 and give SR-013 its second adverse scenario. In the verdict-of-record campaign they score 30/30, 40/40 and 40/40 in enforcement, against 30/30, 32/40 and 20/40 in monitoring; on the frozen GE4-V2 gate record the monitoring figures were 0/30, 23/40 and 0/40.
- **⁷ SR-002 / SR-003 — Satisfied on their own criterion (D-47).** The SC-EDGE-01 "failure" comes from a performance clause inherited from the oval (heading recovery time), which is not the documented satisfaction criterion of either requirement. SR-002 requires `M-P4 ≤ 25°`, and the measured maximum is 14.2°. SR-003 requires a time margin that is never lost, with a maximum lateral excursion of 0.043 m and zero emergencies. See §8.3.
- **⁸ The verdict of record is the 2-D PPO 550k campaign** (31.07.2026, D-69). SR-012 / SR-013 / SR-014 are satisfied on both camera arms. The rows above cite that campaign as current evidence and keep GE4-V2 as the frozen G4 gate record.

## F.2 Machine-processable form

Each row is a chain from a hazard to a metric. A hazard appears in several rows because it covers several chains. The physical verdict column is marked not executed in every row: the deployment chain is built and has driven on hardware, but no run has been done under the scenario protocol (§10.4d–e).

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

The checker verifies automatically that: every hazard is referenced by at least one requirement; every requirement references at least one hazard; every requirement is implemented by at least one rule, training constraint or arbitration property; every rule implements at least one requirement; every rule is tested by at least one scenario; every scenario references at least one requirement; every requirement has at least one metric that verifies it; and every referenced metric is defined.

**Status at the close: all checks pass, with no orphans and no warnings.**
