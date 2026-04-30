# Identifier Conventions

**Status:** Living document — Phase 0 deliverable
**Last update:** [date]
**Approved at Gate:** G0 (pending)

## Purpose

Every artefact in this thesis carries an identifier. Identifiers are the basis of the Traceability Matrix, of cross-references in the manuscript, of file naming conventions in the repository, and of the metadata of every experimental run. Inconsistent identifiers break traceability mechanically, so the conventions in this document are a hard constraint.

Identifiers are assigned exactly once. Once an identifier is used, it is never reused even if its referent is deprecated; deprecated entries are marked as such in their respective living document but their identifier is preserved.

## Hazards: H-XX

Format: `H-` followed by two digits, zero-padded.

Range: H-01 through H-99.

Examples: H-01, H-02, H-15.

Hazards are defined in `docs/02_hazard_register.md`. Their identifier is assigned at the time of registration in the HARA. The H-XX identifier is the only acceptable way to reference a hazard in any other document.

## Safety Requirements: SR-XXX

Format: `SR-` followed by three digits, zero-padded.

Range: SR-001 through SR-999.

Examples: SR-001, SR-024, SR-105.

Safety Requirements are defined in `docs/03_safety_requirements.md`. The numbering does not need to be contiguous; gaps are acceptable when SRs are deprecated, but no number is reused.

## Cage rules: C-XX

Format: `C-` followed by two digits, zero-padded.

Range: C-01 through C-99.

Examples: C-01, C-03, C-12.

Cage rules are defined in `docs/04_cage_specification.md` and implemented under `cage/rules/`. Each rule's implementation file is named `cXX_descriptive_name.py` (e.g. `c01_lane_boundary.py`).

## Scenarios: SC-CATEGORY-XX

Format: `SC-` followed by category code (`NOM`, `EDGE`, `PERT`) followed by `-` and two digits.

Examples: SC-NOM-01, SC-EDGE-04, SC-PERT-02.

Categories:
- `NOM` — nominal operational conditions within the ODD.
- `EDGE` — edge cases at the boundary of the ODD.
- `PERT` — perturbed conditions (sensor noise, latency, etc.).

Scenarios are defined in `docs/05_scenario_library.md` and as YAML files under `scenarios/<category_lowercase>/sc_<category>_<NN>.yaml`.

## Metrics: M-PREFIX-N

Format: `M-` followed by a one-letter category prefix followed by a digit.

Categories and examples:
- `M-PN` — Performance metrics (M-P1: lateral RMSE, M-P2: completion rate, M-P3: heading error mean, M-P4: heading error max, M-P5: speed compliance).
- `M-SN` — Safety metrics (M-S1: max lateral offset, M-S2: boundary violations, M-S3: emergency stop rate, M-S4: TTLC 5th percentile).
- `M-IN` — Intervention metrics (M-I1: total intervention rate, M-I2: per-rule intervention rate, M-I3: intervention duration distribution, M-I4: intervention-hazard correlation, M-I5: action correction magnitude).
- `M-CN` — Computational metrics (M-C1: control loop latency, M-C2: cage overhead).

Metrics are defined in `docs/06_metrics_catalogue.md`.

## Phases: F-N

Format: `F` followed by a single digit.

Range: F0 through F6.

Examples: F0, F2, F5.

Phases are defined in the project plan (outside the repository, see `docs/00_v_model_adapted.md` for the cross-reference).

## Gates: G-N

Format: `G` followed by a single digit.

Range: G0 through G6.

Examples: G0, G2, G5.

## Milestones: M-N

Format: `M` followed by a single digit.

Range: M1 through M4.

Note: this conflicts visually with the metrics prefix `M-` followed by category. Context disambiguates: a milestone is `M1`, `M2`, etc., without a category letter, while a metric is `M-P1`, `M-S2`, etc., with a category letter.

## Experimental runs

Format: `run_NNN` for the run number within an experiment, where NNN is a three-digit zero-padded number unique within its experiment directory.

Example file path: `experiments/sim/SC-NOM-01_enforcement/run_007/`.

Each run directory contains: `state_obs.csv`, `raw_action.csv`, `safe_action.csv`, `cage_status.csv`, `metadata.json`.

## File naming under `cage/rules/`

Format: `cXX_short_name.py` where XX is the two-digit cage rule number and `short_name` is a snake-case name.

Examples: `c01_lane_boundary.py`, `c05_emergency.py`.

## File naming under `scenarios/`

Format: `sc_category_NN.yaml`.

Examples: `sc_nom_01.yaml`, `sc_edge_04.yaml`, `sc_pert_02.yaml`.

## Cross-reference rules

When referencing an identifier in the manuscript or in any document, use the identifier *exactly* as defined here, in monospace if the document format supports it. Do not invent shortened forms ("the cage rule 1" instead of "C-01") because such shortened forms break the mechanical traceability check.

## Change log

See `docs/08_change_log.md`.
