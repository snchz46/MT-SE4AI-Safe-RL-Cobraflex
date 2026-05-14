# Safety Cages and Safe RL within an SE4AI Framework for Autonomous Driving

> **Master's Thesis** — Systems Engineering for AI (SE4AI) applied to lane-following with Reinforcement Learning, validated in simulation and on the CobraFlex 1:14 scale physical platform.

---

## At a Glance

This repository contains the full research artefacts for a master's thesis investigating how **runtime safety cages** can constrain a Reinforcement Learning (RL) agent operating in an autonomous driving context. The work is structured under a Systems Engineering for AI (SE4AI) methodology, meaning every design decision is traceable from a formal hazard down to experimental evidence.

**Key pillars of the research:**

| Pillar | Description |
| ------ | ----------- |
| **Hazard analysis** | Systematic identification and classification of failure modes |
| **Safety requirements** | Formal requirements derived from each hazard |
| **Runtime safety cage** | ROS2 node that enforces safety rules over the RL policy at runtime |
| **RL policy** | Lane-following policy trained and deployed under cage supervision |
| **Validation scenarios** | Nominal, edge-case, and perturbed scenarios for systematic testing |
| **Full traceability** | Every hazard is linked to evidence through an auditable chain |

The central methodological commitment of this work is **traceability**: every hazard identified in the analysis must reach a final validation verdict through a chain of explicitly linked artefacts:

```text
Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict
```

Absence of orphans on either side of this chain is verified mechanically before each Gate review.

---

## Repository Structure

```text
.
├── docs/           Living engineering documents (HARA, SRS, Cage Spec, ...)
├── cage/           Safety cage implementation (pure-Python logic + ROS2 helpers)
├── policy/         RL training pipeline and policy ROS2 node
├── scenarios/      Scenario library (nominal, edge, perturbed)
├── experiments/    Experimental data, calibration campaign, ODD inspection
├── tests/          Unit and integration tests
├── tools/          Verification tooling (traceability check, calibration ingest, ...)
├── manuscript/     Thesis manuscript, figures and figure sources
├── scripts/        Workspace setup / mesh download helpers
└── src/            ROS2 colcon workspace (cobraflex + cobraflex_rl)
```

Every top-level subdirectory contains its own `README.md` explaining its internal organisation and the conventions specific to it.

---

## How to Read This Repository

If you are new to the project, the suggested reading order is:

1. [`docs/00_v_model_adapted.md`](docs/00_v_model_adapted.md) — the methodological framework that organises all the rest.
2. [`docs/01_id_conventions.md`](docs/01_id_conventions.md) — the naming conventions for every identifier you will encounter (`H-XX`, `SR-XXX`, `C-XX`, `SC-*`, `M-*`).
3. [`docs/02_hazard_register.md`](docs/02_hazard_register.md) — the seven identified hazards with their analysis.
4. [`docs/03_safety_requirements.md`](docs/03_safety_requirements.md) — the eight Safety Requirements derived from the hazards.
5. [`docs/04_cage_specification.md`](docs/04_cage_specification.md) — the design of the runtime safety cage.
6. [`docs/05_scenario_library.md`](docs/05_scenario_library.md) — the validation scenarios.
7. [`docs/06_metrics_catalogue.md`](docs/06_metrics_catalogue.md) — the metrics computed on every experimental run.
8. [`docs/07_traceability_matrix.md`](docs/07_traceability_matrix.md) — the master matrix that connects everything.
9. [`docs/08_odd_specification.md`](docs/08_odd_specification.md) — the specification of the Operational Design Domains.

After reading the documents above, the implementation directories (`cage/`, `policy/`, `scenarios/`) will provide full context.

---

## Living Documents

The files under `docs/` are *living* in the strict sense: they are updated as the work progresses, every change is recorded in [`docs/08_change_log.md`](docs/08_change_log.md) with rationale, and every change triggers a re-run of `tools/check_traceability.py` to verify that no orphan references have been introduced.

A living document is *closed* (frozen) only when the corresponding Gate review approves it. Closure does not mean the document cannot change; it means that any subsequent change requires a justified entry in the change log and the approval of the supervisor.

---

## Identifier Conventions

All artefacts in this repository follow a strict naming scheme to enable automated traceability verification.

| Prefix | Meaning | Example |
| ------ | ------- | ------- |
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

## Traceability Verification

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

## ROS2 Workspace (`src/`)

The `src/` directory is a canonical [colcon](https://colcon.readthedocs.io/) workspace containing the ROS2 packages that drive the simulator and the physical platform:

| Package | Role |
| ------- | ---- |
| `src/cobraflex` | URDF/SDF of the 1:14 platform, Gazebo worlds (`empty.world`, `obstacles.world`, `test_world.sdf`), launch files, perception/control nodes, rviz layouts |
| `src/cobraflex_rl` | RL training infrastructure, gymnasium-Gazebo-ROS2 environment wrapper, training launch files |

The cage's pure-Python safety logic lives **outside** this workspace at top-level `cage/` so that the safety-side test suite (`pytest cage/tests/`) can run without a ROS2 toolchain. The two sides connect at runtime via the ROS2 helpers under `cage/ros2/` (M-1 / M-2 calibration loggers) which can be invoked from a ROS2 environment without modifying the workspace.

### Prerequisites

- Ubuntu 22.04 (recommended) or compatible Linux with ROS2 Humble
- `ros-humble-desktop`, `ros-humble-gazebo-ros-pkgs`, `python3-colcon-common-extensions`
- `rosdep` initialised: `sudo rosdep init && rosdep update`
- Python 3.10+ (for the policy training side; install via `pip install -r requirements.txt`)

### One-time setup

```bash
# Resolve ROS2 dependencies declared in package.xml
cd <repo-root>
rosdep install --from-paths src --ignore-src -r -y

# Fetch large meshes excluded from git (87 MB lidar visual)
./scripts/download_meshes.sh
```

### Build

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

`--symlink-install` makes Python edits visible without rebuilding. Build artefacts (`build/`, `install/`, `log/`) are git-ignored.

### Launch examples

```bash
# Bring up the cobraflex platform in a Gazebo world
ros2 launch cobraflex bringup.launch.py

# Run an RL training episode
ros2 launch cobraflex_rl train.launch.py

# Calibration logger for M-2 (control latency)
ros2 run cage_calibration m2_latency_logger \
    --ros-args -p output_csv:=/tmp/m2_latency.csv -p duration_s:=120
```

The `cage_calibration` package above is **not yet** part of `src/` — the M-1 / M-2 logger templates currently live as standalone scripts under `cage/ros2/`. They can be invoked via `python -m cage.ros2.m2_latency_logger` from a ROS2-sourced environment, or promoted to a proper colcon package when needed (see `cage/ros2/README.md`).

### Third-party drivers

`sllidar_ros2` (Slamtec) and `zed-ros2-wrapper` (Stereolabs) are intentionally **not** tracked in this repository (decision D-32). Install them externally if your physical setup needs them, either via `apt`/`rosdep` or by cloning into `src/` alongside the tracked packages (in which case they should be added to `.gitignore` or as git submodules).

---

## Reproducibility

Every experimental run produces logs under `experiments/sim/` or `experiments/physical/` with a unique run identifier. The metadata for each run records:

- Git commit hash of the code
- Hash of the cage YAML configuration
- Policy checkpoint hash
- Scenario YAML hash
- Random seed
- Timestamp and platform identifier

Reproducing a run requires checking out the recorded git commit, recovering the same configuration files, and re-running with the recorded seed. The reproducibility check is part of every Gate review.

---

## Author and Supervision

| Role | Name |
| ---- | ---- |
| **Author** | Ing. Samuel Sanchez |
| **Supervisor** | Prof. Dr.-Ing. Ralf Schüler |
| **Institution** | Hochschule Esslingen |
| **Programme** | Automotive Systems Master |

---

## License

MIT License
