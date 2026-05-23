# Repository Guidelines

## Project Structure & Module Organization

This repository combines thesis documentation, Python safety logic, policy code, scenarios, and a ROS 2 workspace. Core safety cage code lives in `cage/`, with rules in `cage/rules/`, ROS helpers in `cage/ros2/`, and tests in `cage/tests/`. RL policy code and tests live in `policy/` and `policy/tests/`. ROS 2 packages are under `src/` (`cobraflex`, `cobraflex_rl`, `cobraflex_safety_msgs`). Scenario YAML files are grouped in `scenarios/nominal/`, `scenarios/edge/`, and `scenarios/perturbed/`. Living engineering documents and traceability data are in `docs/`, `TRACEABILITY.md`, and `tools/`.

## Build, Test, and Development Commands

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install -e .
```

Run the Python test suite:

```bash
pytest
pytest cage/tests policy/tests
```

Verify traceability before gate reviews or documentation changes:

```bash
python tools/check_traceability.py
python tools/check_traceability.py --strict
```

Build ROS 2 packages from a ROS Humble environment:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
colcon test
```

## Coding Style & Naming Conventions

Use Python 3.10+ and keep Python code PEP 8 compatible. `src/cobraflex` configures flake8 with a 99-character line limit; use that as the repository default. Prefer snake_case for modules, functions, variables, YAML keys, and test files. Keep safety artefact IDs stable: hazards use `H-XX`, requirements `SR-XXX`, cage rules `C-XX`, scenarios `SC-*`, and metrics `M-*`. Do not rename IDs without updating docs, scenarios, tests, and traceability files together.

## Testing Guidelines

Root-level `pytest` is limited by `pytest.ini` to `cage/tests` and `policy/tests`; ROS package tests under `src/` require the ROS 2 toolchain and should be run with `colcon test`. Name Python tests `test_*.py`; use rule-specific names such as `cage/tests/test_c03_ttlc.py`. Add tests when changing cage rules, policy behavior, scenario parsing, or traceability tooling.

## Commit & Pull Request Guidelines

Recent commits use a phase prefix such as `F2:` followed by a short imperative summary, sometimes with `feat:`. Follow that pattern, for example `F2: feat: update baseline controller gains`. Pull requests should summarize changed artefacts, list validation commands, and call out traceability impact. Link related issues or thesis decisions, and include screenshots or logs for ROS/Gazebo or experiment changes.

## Security & Configuration Tips

Do not commit generated ROS outputs (`build/`, `install/`, `log/`), local virtual environments, external driver checkouts, or private experiment data. ROS dependencies are managed with `rosdep` and colcon, not `requirements.txt`. When changing living documents in `docs/`, update `docs/CHANGELOG.md` and rerun traceability.
