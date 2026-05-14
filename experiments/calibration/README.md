# Pre-G1 Calibration Campaign

**Status:** Protocols ready for execution — Phase 1 deliverable  
**Last update:** 13.05.2026  
**Purpose:** Close the parameter-defensibility gap identified in  
`docs/.phases/Fase 1/phase1_refinement_notes.md` §2 and §3 before
Gate G1 review.

## Overview

The Safety Requirements Specification (`docs/03_safety_requirements.md`)
contains numerical thresholds whose justification is currently *partially*
defensible. Some thresholds are derived from physics (`d_max` from
geometry, `θ_max` from a bicycle model); others are conservative defaults
that need empirical confirmation before they can be defended at G1 with
the level of rigour required by the V-Model adaptation A4 (traceability).

This directory contains the protocols for the five measurements (M-1 to
M-5) that close those gaps. Each measurement is a self-contained
experiment with a procedure, an expected output format, and a decision
rule that determines whether the corresponding SR parameter is confirmed
or must be revised.

| Measurement | Closes | Effort | Requires |
| ----------- | ----------------------------------- | ------ | ------------------------------------- |
| [M-1](M1_lidar_static_noise.md) | SR-001 d_max margin (lateral noise σ) | <1 h | sim perception pipeline |
| [M-2](M2_control_latency.md) | SR-001 latency assumption | <1 h | full sim stack running |
| [M-3](M3_max_deceleration.md) | SR-005 a_min, SR-008 t_stop_max | 1 h | physical platform |
| [M-4](M4_speed_vs_curvature.md) | SR-004 v_max_curve | 2 h | physical platform + hand-tuned PD |
| [M-5](M5_actuator_rate.md) | SR-006 δ_max for steering and throttle | 1 h | physical platform |

Total effort estimate: approximately 6 hours of empirical work,
distributed across simulator and platform.

## Execution status

| Measurement | Status     | Executed on | Result file                               |
| ----------- | ---------- | ----------- | ----------------------------------------- |
| M-1         | not yet    | —           | `M1_results.json` (to be produced)        |
| M-2         | not yet    | —           | `M2_results.json` (to be produced)        |
| M-3         | not yet    | —           | `M3_results.json` (to be produced)        |
| M-4         | not yet    | —           | `M4_results.json` (to be produced)        |
| M-5         | not yet    | —           | `M5_results.json` (to be produced)        |

Each result file follows the schema declared at the bottom of its
protocol document. When a measurement is executed, the corresponding
status above is updated to `done`, the result file is committed, and a
`docs/CHANGELOG.md` entry records the SR parameter changes (if any)
together with the cage.yaml version bump to 0.3.0 once all five close.

## Output format conventions

Each measurement produces:

1. A JSON file `MN_results.json` with the numerical outputs, conformant
   to the schema in the protocol document.
2. A short narrative section in the protocol document under "Results",
   filled in by the experimenter, including any observations that the
   bare numbers cannot convey.
3. A decision statement of the form "SR-XXX parameter Y: confirmed at
   value Z" or "SR-XXX parameter Y: revised from Z_old to Z_new
   (rationale)".

If a measurement's decision requires revising a SRS parameter, the
revision is propagated to `docs/03_safety_requirements.md`, to
`cage/cage.yaml`, and to the corresponding figure or table in
Chapter 4 or Chapter 5 of the manuscript, *in the same commit* that
records the measurement result.

## Closure criterion for the campaign

The campaign closes when all five measurements have status `done`,
their result files are committed, the corresponding SRS revisions are
propagated, `cage/cage.yaml` has been bumped to 0.3.0, and
`tools/check_traceability.py` and `pytest cage/tests/` both pass on
the post-measurement state. Closure of the campaign is a hard
precondition for Gate G1 sign-off.
