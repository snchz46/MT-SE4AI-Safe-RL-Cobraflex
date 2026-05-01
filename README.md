# 🛡️ Safety Cages and Safe RL within an SE4AI Framework for Autonomous Driving

> **Master's Thesis** — Systems Engineering for AI (SE4AI) applied to lane-following with Reinforcement Learning, validated in simulation and on the CobraFlex 1:14 scale physical platform.

---

## 📌 At a Glance

This repository contains the full research artefacts for a master's thesis investigating how **runtime safety cages** can constrain a Reinforcement Learning (RL) agent operating in an autonomous driving context. The work is structured under a Systems Engineering for AI (SE4AI) methodology, meaning every design decision is traceable from a formal hazard down to experimental evidence.

**Key pillars of the research:**

| Pillar | Description |
|--------|-------------|
| 🔍 **Hazard analysis** | Systematic identification and classification of failure modes |
| 📋 **Safety requirements** | Formal requirements derived from each hazard |
| 🔒 **Runtime safety cage** | ROS2 node that enforces safety rules over the RL policy at runtime |
| 🤖 **RL policy** | Lane-following policy trained and deployed under cage supervision |
| 🧪 **Validation scenarios** | Nominal, edge-case, and perturbed scenarios for systematic testing |
| 🔗 **Full traceability** | Every hazard is linked to evidence through an auditable chain |

The central methodological commitment of this work is **traceability**: every hazard identified in the analysis must reach a final validation verdict through a chain of explicitly linked artefacts:

```
Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict
```

Absence of orphans on either side of this chain is verified mechanically before each Gate review.

---

## 🗂️ Repository Structure

```text
.
├── 📄 docs/           Living engineering documents (HARA, SRS, Cage Spec, ...)
├── 🔒 cage/           Safety cage implementation as ROS2 node + rules
├── 🤖 policy/         RL training pipeline and policy ROS2 node
├── 🧪 scenarios/      Scenario library (nominal, edge, perturbed)
├── 📊 experiments/    Experimental data and analysis scripts
├── ✅ tests/           Unit and integration tests
├── 🔧 tools/          Verification tooling (traceability check, etc.)
└── 📝 manuscript/     Thesis manuscript and figures
```

Every top-level subdirectory contains its own `README.md` explaining its internal organisation and the conventions specific to it.

---

## 📖 How to Read This Repository

If you are new to the project, the suggested reading order is:

1. [`docs/00_v_model_adapted.md`](docs/00_v_model_adapted.md) — the methodological framework that organises all the rest.
2. [`docs/01_id_conventions.md`](docs/01_id_conventions.md) — the naming conventions for every identifier you will encounter (`H-XX`, `SR-XXX`, `C-XX`, `SC-*`, `M-*`).
3. [`docs/02_hazard_register.md`](docs/02_hazard_register.md) — the seven identified hazards with their analysis.
4. [`docs/03_safety_requirements.md`](docs/03_safety_requirements.md) — the eight Safety Requirements derived from the hazards.
5. [`docs/04_cage_specification.md`](docs/04_cage_specification.md) — the design of the runtime safety cage.
6. [`docs/05_scenario_library.md`](docs/05_scenario_library.md) — the validation scenarios.
7. [`docs/06_metrics_catalogue.md`](docs/06_metrics_catalogue.md) — the metrics computed on every experimental run.
8. [`docs/07_traceability_matrix.md`](docs/07_traceability_matrix.md) — the master matrix that connects everything.

After reading the documents above, the implementation directories (`cage/`, `policy/`, `scenarios/`) will provide full context.

---

## 📋 Living Documents

The files under `docs/` are *living* in the strict sense: they are updated as the work progresses, every change is recorded in [`docs/08_change_log.md`](docs/08_change_log.md) with rationale, and every change triggers a re-run of `tools/check_traceability.py` to verify that no orphan references have been introduced.

A living document is *closed* (frozen) only when the corresponding Gate review approves it. Closure does not mean the document cannot change; it means that any subsequent change requires a justified entry in the change log and the approval of the supervisor.

---

## 🏷️ Identifier Conventions

All artefacts in this repository follow a strict naming scheme to enable automated traceability verification.

| Prefix | Meaning | Example |
|--------|---------|---------|
| `H-XX` | Hazard | `H-01` |
| `SR-XXX` | Safety Requirement | `SR-001` |
| `C-XX` | Cage rule | `C-03` |
| `SC-*` | Scenario | `SC-NOM-01` |
| `M-*` | Metric | `M-S1` |
| `F-X` | Phase | `F2` |
| `G-X` | Gate review | `G3` |
| `M-X` | Milestone | `M2` |

Full specification in [`docs/01_id_conventions.md`](docs/01_id_conventions.md).

---

## ✅ Traceability Verification

Before each Gate review (G0 through G6), the following command must pass without errors:

```bash
python tools/check_traceability.py
```

This script verifies that:
- Every hazard is referenced by at least one Safety Requirement.
- Every Safety Requirement is implemented by at least one cage rule.
- Every cage rule is exercised by at least one scenario.
- Every scenario references at least one Safety Requirement.
- There are no orphan artefacts on either side.

> ⚠️ This is a **hard gate**: if the script fails, the Gate review cannot proceed.

---

## 🔁 Reproducibility

Every experimental run produces logs under `experiments/sim/` or `experiments/physical/` with a unique run identifier. The metadata for each run records:

- Git commit hash of the code
- Hash of the cage YAML configuration
- Policy checkpoint hash
- Scenario YAML hash
- Random seed
- Timestamp and platform identifier

Reproducing a run requires checking out the recorded git commit, recovering the same configuration files, and re-running with the recorded seed. The reproducibility check is part of every Gate review.

---

## 🗓️ Research Plan

The thesis follows a **20-week plan** organised in seven phases (F0 through F6), four milestones (M1 through M4), and seven Gate reviews (G0 through G6). The detailed phase-by-phase plan is documented in [`docs/00_v_model_adapted.md`](docs/00_v_model_adapted.md).

---

## 👤 Author and Supervision

| Role | Name |
|------|------|
| **Author** | [name placeholder] |
| **Supervisor** | [name placeholder] |
| **Institution** | [institution placeholder] |
| **Programme** | [programme placeholder] |

---

## ⚖️ License

License to be decided with the supervisor before public release.
