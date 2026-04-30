# Thesis: Safety Cages and Safe RL within an SE4AI Framework for Autonomous Driving

This repository contains the implementation, living documents, scenario library, experimental data and supporting tooling for the master's thesis on Systems Engineering for AI (SE4AI) applied to lane-following with reinforcement learning, demonstrated in simulation and on the CobraFlex 1:14 scale platform.

The central methodological commitment of this work is **traceability**: every hazard identified in the analysis must reach a final validation verdict through a chain of explicitly linked artefacts (Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict), and the absence of orphans on either side is verified mechanically before each Gate review.

## Repository organisation

```text
.
├── docs/                  Living engineering documents (HARA, SRS, Cage Spec, ...)
├── cage/                  Safety cage implementation as ROS2 node + rules
├── policy/                RL training pipeline and policy ROS2 node
├── scenarios/             Scenario library (nominal, edge, perturbed)
├── experiments/           Experimental data and analysis scripts
├── tests/                 Unit and integration tests
├── tools/                 Verification tooling (traceability check, etc.)
└── manuscript/            Thesis manuscript and figures
```

Every top-level subdirectory has its own README explaining its internal organisation and the conventions specific to it.

## How to read this repository

If you are new to the project, the suggested reading order is:

1. `docs/00_v_model_adapted.md` — the methodological framework that organises all the rest.
2. `docs/01_id_conventions.md` — the naming conventions for every identifier you will encounter (H-XX, SR-XXX, C-XX, SC-*, M-*).
3. `docs/02_hazard_register.md` — the seven identified hazards with their analysis.
4. `docs/03_safety_requirements.md` — the eight Safety Requirements derived from the hazards.
5. `docs/04_cage_specification.md` — the design of the runtime safety cage.
6. `docs/05_scenario_library.md` — the validation scenarios.
7. `docs/06_metrics_catalogue.md` — the metrics computed on every run.
8. `docs/07_traceability_matrix.md` — the master matrix that connects everything.

After that, the implementation directories (`cage/`, `policy/`, `scenarios/`) make sense.

## Living documents

The files under `docs/` are *living* in the strict sense: they are updated as the work progresses, every change is recorded in `docs/08_change_log.md` with rationale, and every change triggers a re-run of `tools/check_traceability.py` to verify that no orphan references have been introduced.

A living document is *closed* (frozen) only when the corresponding Gate review approves it. Closure does not mean the document cannot change; it means that any subsequent change requires a justified entry in the change log and the approval of the supervisor.

## Identifier conventions (summary)

| Prefix | Meaning | Example |
| -------- | --------- | --------- |
| H-XX | Hazard | H-01 |
| SR-XXX | Safety Requirement | SR-001 |
| C-XX | Cage rule | C-03 |
| SC-* | Scenario | SC-NOM-01 |
| M-* | Metric | M-S1 |
| F-X | Phase | F2 |
| G-X | Gate review | G3 |
| M-X | Milestone | M2 |

Full conventions in `docs/01_id_conventions.md`.

## Verification before any Gate

Before each Gate review (G0 through G6), run:

```bash
python tools/check_traceability.py
```

This script verifies that every hazard is referenced by at least one SR, every SR is implemented by at least one cage rule, every cage rule is exercised by at least one scenario, every scenario references at least one SR, and there are no orphans on either side. It is a hard gate: if it fails, the Gate review cannot proceed.

## Reproducibility

Every experimental run produces logs under `experiments/sim/` or `experiments/physical/` with a unique run identifier. The metadata for each run records: the git commit hash of the code, the hash of the cage YAML, the policy checkpoint hash, the scenario YAML hash, the random seed, the timestamp and the platform identifier.

Reproducing a run requires checking out the recorded git commit, recovering the same configuration files, and re-running with the recorded seed. The reproducibility check is part of every Gate review.

## Plan

The thesis follows a 20-week plan organised in seven phases (F0 through F6), four milestones (M1 through M4), and seven Gate reviews (G0 through G6). The detailed phase-by-phase plan is documented separately (outside this repository) and referenced from `docs/00_v_model_adapted.md`.

## Author and supervision

Author: [name placeholder]
Supervisor: [name placeholder]
Institution: [institution placeholder]
Programme: [programme placeholder]

## License

[License placeholder. To be decided with supervisor before public release.]
