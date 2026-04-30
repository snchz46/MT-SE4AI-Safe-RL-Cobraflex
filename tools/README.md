# Tools

Verification and synchronisation utilities for the repository.

## Available

- `check_traceability.py` — verifies bidirectional traceability between hazards, SRs, cage rules, scenarios and metrics. Hard gate before every Gate review. Run: `python tools/check_traceability.py`. Use `--strict` to fail on warnings.

- `traceability_matrix.csv` — machine-readable form of the traceability matrix, kept in sync with `docs/07_traceability_matrix.md`.

## To be implemented

- `check_scenario_yaml.py` — validates scenario YAML files against `scenarios/_schema.yaml` (Phase 2).
- `sync_traceability.py` — syncs `docs/07_traceability_matrix.md` ↔ `tools/traceability_matrix.csv` (Phase 0/1).
- `sync_hazard_register.py` — extracts hazard identifiers and metadata from `docs/02_hazard_register.md` to a CSV.
- `sync_safety_requirements.py` — same for SRs.
- `compute_run_hash.py` — computes the metadata hashes (cage YAML, scenario YAML, policy checkpoint) used for reproducibility (Phase 4).

## CI integration

These scripts are designed to be runnable in a CI pipeline. The recommended integration:

- Pre-commit hook: `check_traceability.py` runs on changes to `docs/`.
- Pre-push hook: full test suite runs.
- Nightly build: full traceability + scenario YAML validation + cage unit tests.
