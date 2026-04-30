# Scenarios

Scenario library for system validation. Each scenario is a reproducible experiment.

## Organisation

- `nominal/` — operational conditions within the ODD.
- `edge/` — at the boundary of the ODD.
- `perturbed/` — sensor noise, latency, etc. applied during operation.
- `_schema.yaml` — schema documentation for scenario YAML files.

## Authoritative source

The narrative description and the rationale for each scenario are in `docs/05_scenario_library.md`. The YAML files in this directory are the executable counterpart.

## Validation

Before any Gate review, run:

```bash
python tools/check_scenario_yaml.py    # to be implemented in Phase 2
```

This validates that every scenario YAML conforms to the schema and that every scenario referenced in `docs/05_scenario_library.md` has a matching YAML file (and vice versa).

## Phase status

Phase 0: 9 scenarios identified and described.
Phase 2: full YAML specifications. **Currently in this phase for SC-NOM-01 and SC-EDGE-01; remaining scenarios are stubs.**
Phase 4: scenarios executed; results in `experiments/sim/`.
