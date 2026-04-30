# Safety Cage

Runtime safety cage as a ROS2 node, separated from the policy and traceable to specific Safety Requirements.

## Files

- `cage_node.py` — main ROS2 node entry point.
- `cage.yaml` — versioned parameter file. Single source of truth.
- `rules/` — one Python module per cage rule (C-01 through C-06).
- `tests/` — unit tests for each rule and for the evaluation order.

## Design specification

The authoritative specification is `docs/04_cage_specification.md`. The code in this directory must match that specification at all times.

## Updating parameters

1. Edit `cage.yaml`.
2. Add an entry to `docs/08_change_log.md`.
3. Run `pytest cage/tests/` and verify all tests pass.
4. Re-run any affected scenarios from `docs/05_scenario_library.md`.

## Operating modes

- `enforcement`: corrections applied. Default.
- `monitoring`: corrections logged but not applied. Used for the enforcement-vs-monitoring comparison.

## Phase status

Phase 0: spec drafted.
Phase 1: spec refined with parameter values from analysis.
Phase 2: implementation. **Currently in this phase.**
Phase 3 onwards: cage active during training and evaluation.
