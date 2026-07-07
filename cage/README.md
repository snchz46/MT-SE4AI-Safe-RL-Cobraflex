# Safety Cage

Pure-Python runtime safety cage (rules C-01..C-06), separated from the policy
and traceable to specific Safety Requirements. **No ROS2 dependency in this
package** — that is what makes it independently unit-testable (property A2)
and lets the ROS2 wrapper, the RL training loop and the test suite all run the
*same* class against the *same* `cage.yaml`.

## Files

- `cage_node.py` — `SafetyCageNode`: composes the six rules in the fixed order
  C-06 → C-04 → C-02 → C-03 → C-01 → C-05; called per control cycle via
  `step(state, raw_action, ctx)`. Not a ROS node — the ROS2 wrapper is
  `src/safety_cage/safety_cage/cage_ros_node.py`; the in-process training-time
  consumer is `cobraflex_rl/cage_bridge.py` (D-34).
- `cage.yaml` — versioned parameter file (single source of truth; referenced
  by hash in every run's metadata). `cage_isaac.yaml` is the Isaac-track
  calibration variant (posterior work).
- `rules/` — one module per cage rule (C-01 through C-06) plus the shared
  `base.py` contract (`State`/`Action`/`Decision`,
  `safe_envelope_predicate_holds`).
- `logger.py` — per-cycle CSV + metadata writer (one schema shared by tests,
  the ROS2 logger node and the campaign analysis).
- `tests/` — 139 unit/integration tests (rules, chain order, SR-010
  joint-envelope + oscillation, missing-state, config governance). Full
  test-to-SR map: `docs/15_implementation_inventory.md` §6.1.
- `ros2/` — M-1/M-2 calibration logger helpers (not in the colcon workspace).

## Design specification

The authoritative specification is `docs/04_cage_specification.md`. The code in
this directory must match that specification at all times. Threshold
provenance (where every number comes from): `docs/16_defense_compendium.md`
§4.3 and the inline comments in `cage.yaml`.

## Updating parameters

1. Edit `cage.yaml` and bump `cage.version`.
2. Add an entry to `docs/CHANGELOG.md` with rationale and evidence.
3. Run `pytest cage/tests/` and verify all tests pass.
4. Re-run any affected scenarios from `docs/05_scenario_library.md`.
5. If an SR threshold changed, bump `compatible_sr_spec_version` **and**
   `_ACCEPTED_SR_SPEC_VERSIONS` in `cage_node.py` (the loader refuses
   mismatched configs).

## Operating modes

- `enforcement`: corrections applied. Default.
- `monitoring`: corrections logged but not applied. Used for the
  enforcement-vs-monitoring causal comparison in the campaigns.

## Status

Implemented and frozen through the F4 + GE4-V2 campaigns (cage YAML 0.6.1,
G4 closed 02.07.2026). C-05 has 8 triggers (Trigger 8 = perception-invalid,
track 'E', D-43). See `docs/CHANGELOG.md` for the version history.
