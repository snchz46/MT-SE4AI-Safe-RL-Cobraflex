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
| M-1         | stub ready | —           | `M1_results.json` (scaffold, fill in)     |
| M-2         | stub ready | —           | `M2_results.json` (scaffold, fill in)     |
| M-3         | stub ready | —           | `M3_results.json` (scaffold, fill in)     |
| M-4         | stub ready | —           | `M4_results.json` (scaffold, fill in)     |
| M-5         | stub ready | —           | `M5_results.json` (scaffold, fill in)     |

Each result file follows the schema declared at the bottom of its
protocol document. The stub files already exist in this directory;
when a measurement is executed, replace the `"YYYY-MM-DD"` sentinel
and the `null` placeholders with the measured values, commit the file,
and run `python tools/apply_calibration.py` to generate the
propagation report. The script will validate the schema, apply the
decision rule, and emit suggested updates for the SRS and
`cage/cage.yaml`; with `--apply-yaml` it writes the `cage.yaml`
edits in place (a `.bak` backup is left).

## Workflow per measurement

The standard cycle to close one measurement is:

1. **Execute** the protocol declared in `M{1..5}_*.md`.
2. **Fill in** the corresponding `M{N}_results.json` (already scaffolded
   in this directory with the schema and sentinel placeholders).
   Replace `"YYYY-MM-DD"` with the execution date and the `null`
   placeholders with the measured values; fill the `decision` field
   with one of the verbatim strings declared in the protocol's
   "Decision rule" section.
3. **Run** the ingestion tool to validate and compute target values:

       python tools/apply_calibration.py --measurement M-N

   This prints the decision, the target parameter values, the current
   `cage.yaml` values, the SRS sections to update manually, and a
   CHANGELOG snippet. The tool exits 0 when the measurement is ready,
   1 if the schema is invalid, and 2 if the platform underperformed
   (e.g. M-3 brake authority below 0.3 m/s² — a G1 blocker).

4. **Apply** the suggested updates. The `cage.yaml` edits can be
   automated with `--apply-yaml` (a `.bak` backup is left next to the
   file); the SRS rationale edits remain manual because they involve
   prose. After the edits, commit the result JSON + the propagated
   artefact changes + a CHANGELOG entry in a single commit.

5. **Verify** by re-running `python tools/check_traceability.py` and
   `pytest cage/tests/` after every measurement closure.

To process all five measurements in one pass once they are all filled
in:

    python tools/apply_calibration.py --apply-yaml

After that pass succeeds, manually bump `cage/cage.yaml`
`cage.version` from `"0.2.0"` to `"0.3.0"` and write the closing entry
in `docs/CHANGELOG.md`. That commit closes the calibration campaign
and is the hard precondition for G1 sign-off (see "Closure criterion"
below).

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
