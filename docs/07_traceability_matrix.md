# Traceability Matrix

**Status:** Living document — Phase 0 baseline, refined through every phase, closed at G6
**Last update:** [date]
**Approved at Gate:** every Gate (incrementally)

## Purpose

This document is the master record of bidirectional traceability across the thesis. It connects every Hazard to one or more Safety Requirements, every Safety Requirement to one or more Cage Rules, every Cage Rule to one or more Scenarios, every Scenario to one or more Metrics, and every Metric to logged evidence and a final per-SR validation verdict.

The matrix exists in two complementary forms:

1. **Human-readable form** — this Markdown document, organised as a tabular summary.
2. **Machine-readable form** — `tools/traceability_matrix.csv`, generated and verified by `tools/check_traceability.py`.

The two forms are kept in sync by `tools/sync_traceability.py` (to be implemented in Phase 0).

## Coverage requirements

The following coverage requirements are *hard constraints* enforced by `tools/check_traceability.py`:

- (1) Every H-XX referenced by ≥ 1 SR-XXX.
- (2) Every SR-XXX references ≥ 1 H-XX.
- (3) Every SR-XXX implemented by ≥ 1 C-XX (or training constraint, or scenario test).
- (4) Every C-XX implements ≥ 1 SR-XXX.
- (5) Every C-XX exercised by ≥ 1 SC-*.
- (6) Every SC-* references ≥ 1 SR-XXX.
- (7) Every SR-XXX has ≥ 1 verifying metric M-*.
- (8) Every metric used in a verdict references ≥ 1 SR-XXX.

Any violation is a blocker for the next Gate review.

## Matrix summary (current state)

The full matrix is in `tools/traceability_matrix.csv`. The summary below shows the chain Hazard → SR → Cage Rule → Scenario.

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict |
|--------|--------------------|--------------|-----------|---------------------|---------|
| H-01 | SR-001 | C-01, C-03 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1, M-S2 | TBD |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | TBD |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | TBD |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | TBD |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | TBD |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | TBD |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | TBD |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | TBD |

"TBD" verdicts are filled in during Phase 4 (simulation results) and Phase 5 (physical results, where applicable).

## Verdict possibilities

- **Satisfied** — the criterion holds with margin across all relevant runs in enforcement mode.
- **Partially satisfied** — the criterion holds in most conditions but with documented exceptions in specific scenarios; rationale and impact analysis required.
- **Not satisfied** — the criterion does not hold; documented analysis of why and consequences for the work's claims.

The thesis can defend "Satisfied" or "Partially satisfied" verdicts with full rigour. "Not satisfied" verdicts are reported honestly and discussed in the Limitations chapter.

## Verdict by source of evidence

Verdicts can be split between simulation evidence and physical evidence:

- **Sim**: as evaluated in Phase 4 across the simulation campaign.
- **Phys**: as evaluated in Phase 5 across the physical experiments, when scope permits.

Some SRs will have only Sim verdicts; SRs verified only in scenarios not exported to physical have no Phys verdict by design, and this is documented.

## Update procedure

When any of the following changes, the matrix is updated and `tools/check_traceability.py` is re-run:

- A hazard is added, modified, or deprecated in the Hazard Register.
- An SR is added, modified, or deprecated in the SRS.
- A cage rule is added, modified, or removed.
- A scenario is added, modified, or removed.
- A metric is added or modified.
- A verdict is filled in based on experimental evidence.

Every update is recorded in `docs/08_change_log.md`.

## Schema of the CSV

`tools/traceability_matrix.csv` has the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `hazard_id` | string | H-XX |
| `sr_id` | string | SR-XXX |
| `cage_rule_id` | string | C-XX or empty if implementation is not a cage rule |
| `implementation_kind` | string | "cage_rule", "training_constraint", or "scenario_test" |
| `scenario_id` | string | SC-* |
| `metric_id` | string | M-* |
| `verdict_sim` | enum | "satisfied", "partial", "not_satisfied", "tbd" |
| `verdict_phys` | enum | same plus "out_of_scope" |
| `evidence_path` | string | relative path to the experiment directory |
| `notes` | string | free text |

Each row of the CSV represents one chain from a hazard to a metric (with possibly intermediate links). A single hazard typically appears in multiple rows because it spans multiple chains.

## Known orphans (must be empty before any Gate)

- (none expected; if any appear, list them here with rationale)

## Change log

See `docs/08_change_log.md`.
