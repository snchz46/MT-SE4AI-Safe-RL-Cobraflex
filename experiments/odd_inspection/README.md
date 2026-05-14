# experiments/odd_inspection — Closing the ODD-Spec TBDs

This directory hosts the workflow for closing the twelve TBD-Q* tags
in `docs/08_odd_specification.md` against the actual configuration of
the simulator workspace. Closure of all TBD-Q1..Q12 (or explicit
deferral, with rationale) is a hard precondition for Gate G1.

## Files

| File | Purpose |
| ---- | ------- |
| `odd_tbds.yaml` | Template you fill in with the resolved values, their source, and notes. |

## Companion tool

`tools/close_odd_tbds.py` reads `odd_tbds.yaml`, substitutes every
resolved `TBD-QN` literal in the body of the ODD-Spec, and fills the
`Resolution` column of the open-issues table at section 11. By
default it prints a unified diff; pass `--apply` to write the patched
file in place (a `.bak` backup is left next to the original).

## Workflow per TBD

1. **Inspect** the source named in the description (a Gazebo
   `.world` / `.sdf` under `src/cobraflex/worlds/`, the env wrapper
   Python file under `src/cobraflex_rl/`, a scenario YAML, or a
   derivation formula). The descriptions in `odd_tbds.yaml` point to
   the expected source for each TBD.
2. **Fill in** the entry in `odd_tbds.yaml`:
   - `value`: the resolved numeric or string answer.
   - `source`: free-text reference (filename + line, derivation,
     or "design decision F1" if the value is a choice rather than a
     reading).
   - `notes`: optional caveats or follow-up cross-checks.
3. **Dry-run** the script and review the diff:

       python tools/close_odd_tbds.py

4. **Apply** when the diff looks right:

       python tools/close_odd_tbds.py --apply

   A `docs/08_odd_specification.md.bak` is left next to the patched
   document so you can revert by hand if needed.
5. **Commit** the patched ODD-Spec + the populated YAML + a
   CHANGELOG entry (the script prints a copy-paste snippet at the
   end of every dry-run with at least one resolved TBD).
6. **Verify** that the rest of the artefacts still validate:

       python tools/check_traceability.py
       pytest cage/tests/

The script is idempotent: TBDs whose `value` field is `null`/empty
are silently skipped. You can resolve and commit TBDs one by one,
re-running the script each time without disturbing the unresolved
ones.

## Sources by TBD group

| Group | TBDs | Where to look |
| ----- | ---- | ------------- |
| Surface spec | Q1 | `<surface><friction>` block in the Gazebo SDF of the road geom under `src/cobraflex/worlds/` (e.g., `empty.world`, `obstacles.world`, `test_world.sdf`) |
| Map geometry | Q8, Q9 | `<link>` / `<collision>` / `<visual>` primitives in `src/cobraflex/worlds/odd3_curvy_loop.world` (or the world that resolves to it); cross-checked with M-4 |
| Derived | Q2, Q10 | Pure arithmetic on Q1, V_MAX, V_MAX_CURVE, Q9 |
| Episode logic | Q3, Q11 | Termination thresholds in the gymnasium env wrapper under `src/cobraflex_rl/` |
| Scenario profiles | Q4, Q5, Q6, Q7, Q12 | Scenario YAMLs under `src/cobraflex_rl/config/` (if defined) **or** design decisions documented now for implementation in F4 |

## Closure criterion for Gate G1

A TBD is *closed* if either of the following holds:

- It has a numerical or descriptive `value` in `odd_tbds.yaml` backed
  by a verifiable `source` (file + line, derivation, or design
  decision).
- It is explicitly *deferred* to a later phase with the deferral
  documented as a decision in `docs/DECISIONS.md` (e.g., "TBD-Q12
  deferred to F4 entry; ODD-4 stressors will be specified at scenario
  library construction").

Gate G1 accepts a mixture of resolved and explicitly-deferred TBDs;
it does **not** accept silently-unresolved TBD-QN literals remaining
in the body of the document.
