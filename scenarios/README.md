# Scenarios (oval library — frozen F-track baseline)

Scenario library for system validation. Each scenario is a reproducible experiment.

> **This is the F-track (oval, state-vector) library — frozen since the F4
> campaign closed (2026-06-10).** The library that carries the **verdict of
> record** is [`scenarios_complex_b/`](../scenarios_complex_b/README.md): the
> track-'E' camera variants on the complex_b circuit (28 scenarios, GE4-V2,
> G4 closed 02.07.2026). Edit there for anything track-'E'; this directory is
> kept intact so the F4 baseline evidence remains reproducible.

## Organisation

- `nominal/` — operational conditions within the ODD.
- `edge/` — at the boundary of the ODD.
- `perturbed/` — degraded conditions (sensor noise, latency, visual stressors) applied during operation.
- `_schema.yaml` — schema documentation for scenario YAML files.

The frontier (`SC-FRONT-*`) out-of-ODD cage-efficacy scenarios live in the
category directories alongside the verdict scenarios but are analysed as a
paired contrast, not aggregated into the global verdict (D-35).

## Authoritative source

The narrative description and the rationale for each scenario are in `docs/05_scenario_library.md`. The YAML files in this directory are the executable counterpart.

## Validation

Before any Gate review, run:

```bash
python tools/check_scenario_yaml.py
```

Use `--strict` to fail on warnings once every documented scenario must have a full YAML counterpart.

## Phase status

- **F4 (closed):** 24 oval scenarios executed in the verdict-bearing campaign
  (`experiments/sim/campaign/`, global `SATISFIED`); library frozen.
- **Track 'E' (closed, elsewhere):** the complex_b camera library
  (`scenarios_complex_b/`, 28 scenarios incl. SC-PERT-04..13 visual/perception
  stressors and SC-FRONT-07) carried the GE4-V2 verdict of record.
