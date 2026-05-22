# CLAUDE.md — Working context for this repo

> Base context for any Claude session on this thesis repo. Keep lean
> (<200 lines). Move detail into linked docs rather than inflating this file.
> Last reviewed: 2026-05-22.

## What this repo is

Master's thesis (Samuel Sanchez, HS Esslingen, Automotive Systems M.Sc.,
supervisor Prof. Dr.-Ing. Ralf Schüler) on **runtime safety cages + RL
for lane-following**, applied to the CobraFlex 1:14 platform under a
**SE4AI** (Systems Engineering for AI) methodology. Validated in
Gazebo and, eventually, on the physical platform.

The defining commitment is **traceability**:

```
Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict
```

Every artifact has an ID, every Gate review fails if the traceability
script reports orphans on either side.

## Phase status (snapshot)

- **Current phase:** F2 (Cage v0.5.0 + lane_following oval simulation
  with PD baseline). Pre-Gate G2.
- **Recent emphasis:** ROS2 lane-keeping integration (`pd_baseline_node`,
  `vehicle_control_node`, `cage_logger_node`), texture/world tuning
  for the oval scenario, PD gain tuning, heading-smoothing fixes.
- **Authoritative status sources:** [docs/CHANGELOG.md](docs/CHANGELOG.md)
  and `git log --oneline` (commits prefixed `F2:` are current-phase work).

## Repo map

| Path | Role |
| --- | --- |
| `docs/` | Living engineering documents (00–08 + CHANGELOG, DECISIONS) |
| `cage/` | Pure-Python safety cage (rules C-01..C-06, cage_node, logger, YAML config). Importable without ROS2. |
| `cage/ros2/` | ROS2 helper scripts (M-1/M-2 calibration loggers). Not in colcon workspace yet. |
| `policy/` | RL policy: PD baseline, PPO training, checkpoints (gitignored binaries) |
| `src/` | colcon ROS2 workspace — packages below |
| `src/cobraflex` | URDF/SDF, Gazebo worlds, perception/control nodes, rviz, meshes |
| `src/cobraflex_rl` | RL gym wrapper, training launches, PD baseline node, vehicle control, lane perception, cage logger node |
| `src/safety_cage` | ROS2 wrapper exposing the pure-Python cage as a node |
| `src/cobraflex_safety_msgs` | Custom safety msg definitions |
| `scenarios/` | YAML scenario library: `nominal/`, `edge/`, `perturbed/` (schema `_schema.yaml`) |
| `experiments/` | Calibration data, ODD inspection, sim+physical run outputs |
| `tools/` | Traceability + sync scripts (manuscript Markdown → CSV) |
| `tests/` | Top-level integration/unit harness (Python-side, no ROS2 needed) |
| `manuscript/` | Thesis chapters + figures — authoritative source for hazard/SR tables |
| `scripts/` | Workspace bootstrap (`download_meshes.sh`, oval centerline generator, lane-circuit composer) |

`build/`, `install/`, `log/`, `.venv/`, mesh blobs, bag files, checkpoint
binaries, and `experiments/**/raw_logs/` are gitignored.

## Identifier conventions (memorize)

| Prefix | Meaning |
| --- | --- |
| `H-XX` | Hazard (e.g. `H-01`) |
| `SR-XXX` | Safety Requirement (e.g. `SR-001`) |
| `C-XX` | Cage rule (`C-01` lane bdry, `C-02` heading, `C-03` TTLC, `C-04` speed, `C-05` emergency, `C-06` rate limiter) |
| `SC-*` | Scenario (e.g. `SC-NOM-01`) |
| `M-*` | Metric (e.g. `M-S1`) |
| `F-X` / `G-X` / `D-NN` | Phase / Gate / Decision |

Full spec: [docs/01_id_conventions.md](docs/01_id_conventions.md).
Commits are prefixed with the current phase tag (`F2: feat:`, `F2: fix:`, etc.).

## How changes flow

1. Edit Markdown source (often `manuscript/chapters/*.md` for hazards/SRs,
   or `docs/0X_*.md` for engineering specs).
2. If hazards/SRs touched, regenerate CSVs:
   `python tools/sync_hazard_register.py` (and `sync_safety_requirements.py`).
3. Record the change in [docs/CHANGELOG.md](docs/CHANGELOG.md) with
   Phase / Gate / Rationale / Impact / Verification blocks.
4. Run `python tools/check_traceability.py` — must pass before any Gate.
5. Commit with `FN:` prefix matching the current phase.

Architectural decisions go in [docs/DECISIONS.md](docs/DECISIONS.md) as
`D-NN` ADR-style entries — cite by ID rather than re-arguing.

## Commands

Python-side (cage + policy, no ROS2 needed):

```bash
pip install -e .                                  # editable install (pyproject.toml)
pip install -r requirements.txt
pytest                                            # only cage/tests + policy/tests (see pytest.ini)
python tools/check_traceability.py                # hard gate before any review
```

ROS2-side (Ubuntu 22.04 + Humble; **not the Windows dev box**):

```bash
rosdep install --from-paths src --ignore-src -r -y
./scripts/download_meshes.sh                      # 87 MB lidar visual, gitignored
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch cobraflex bringup.launch.py
ros2 launch cobraflex_rl train.launch.py
```

`pytest` from the root is configured to **skip** `src/` (those packages
use `ament_python` + `colcon test`, not bare pytest).

## Environment & host constraints

- Primary dev machine is **Windows 11 + PowerShell**. The ROS2 side
  cannot run here — only Python-side tests, document edits, and Gazebo
  via WSL/Linux box are valid.
- Use PowerShell syntax in Bash tool calls on this host (`$null`, not
  `/dev/null`; backtick continuation; `$env:VAR`).
- `.venv/` is the local Python env. `pyproject.toml` exposes `cage`,
  `cage.rules`, `policy` for `pip install -e .`.
- Third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) are
  **intentionally not tracked** (decision D-32) — install externally.

## Where to look first

| You need… | Read |
| --- | --- |
| Methodology overview | [docs/00_v_model_adapted.md](docs/00_v_model_adapted.md) |
| ID rules | [docs/01_id_conventions.md](docs/01_id_conventions.md) |
| Hazards (H-01..H-07) | [docs/02_hazard_register.md](docs/02_hazard_register.md) |
| Safety Requirements | [docs/03_safety_requirements.md](docs/03_safety_requirements.md) |
| Cage rule specs | [docs/04_cage_specification.md](docs/04_cage_specification.md) |
| Scenarios | [docs/05_scenario_library.md](docs/05_scenario_library.md) |
| Metrics | [docs/06_metrics_catalogue.md](docs/06_metrics_catalogue.md) |
| Traceability matrix | [docs/07_traceability_matrix.md](docs/07_traceability_matrix.md) |
| ODD spec | [docs/08_odd_specification.md](docs/08_odd_specification.md) |
| Decisions (D-NN) | [docs/DECISIONS.md](docs/DECISIONS.md) |
| What changed when | [docs/CHANGELOG.md](docs/CHANGELOG.md) |
| Manuscript-to-CSV generation | [TRACEABILITY.md](TRACEABILITY.md) |
| Cage runtime details | [cage/README.md](cage/README.md) |
| Policy training details | [policy/README.md](policy/README.md) |
| Experimental runs | [experiments/README.md](experiments/README.md) |
| Tools usage | [tools/README.md](tools/README.md) |

## Working rules of thumb

- **Single source of truth = the Markdown.** Generated CSVs and tables
  must be re-derivable; never hand-edit `docs/data/*.csv` or generated
  figures under `manuscript/figures/auto/`.
- **No orphan IDs.** If you add an `H-`, it needs an `SR-` and a row
  in the hazard register. If you add an `SR-`, it needs a `C-` or an
  explicit "implementation deferred" note (with rationale).
- **Cage backwards compatibility:** when bumping `cage.yaml`'s
  `cage.version`, defaults in `SafetyCageNode.__init__` must keep new
  features inert for older YAMLs (precedent set at 0.4.0→0.5.0).
- **Commit prefix matches phase.** `F2:` for current work, never bare
  messages. Conventional-Commit body style (`feat:`, `fix:`, `chore:`,
  `refactor:`).
- **Don't claim a feature works without running it.** ROS2 nodes
  especially: typecheck/pytest ≠ feature works. If you can't launch
  the world on this host, say so explicitly.
- **Reproducibility metadata.** Each run under `experiments/sim/runs/`
  or `experiments/physical/runs/` records git commit, cage YAML hash,
  policy checkpoint hash, scenario YAML hash, seed, timestamp.

## Out-of-scope reminders

- Don't write CLAUDE.md content that's already in `README.md` or
  `docs/0X_*.md` — link instead.
- Don't add planning/decision/analysis docs unless the user asks.
- Don't introduce abstractions or backward-compat shims preemptively.
- This file is maintained by the `daily-update` scheduled task; if it
  starts drifting >200 lines, split into `CLAUDE_*.md` linked from here.
