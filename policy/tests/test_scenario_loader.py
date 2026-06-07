"""
Unit tests for cobraflex_rl.scenario_loader — parsing the real scenario YAMLs
under scenarios/. Runs without ROS/Gazebo.
"""

import shutil
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.scenario_loader import (  # noqa: E402
    RunSpec,
    ScenarioStub,
    family,
    load_scenario,
    load_scenarios,
)

_SCEN = _REPO / "scenarios"


def test_family_classification():
    assert family("SC-NOM-01") == "nominal"
    assert family("SC-EDGE-05") == "adverse"
    assert family("SC-PERT-03") == "adverse"


def test_load_full_scenario_sc_nom_01():
    spec = load_scenario(_SCEN / "nominal" / "sc_nom_01.yaml")
    assert isinstance(spec, RunSpec)
    assert spec.id == "SC-NOM-01"
    assert spec.category == "nominal"
    assert "SR-001" in spec.references_SR
    assert spec.runs_for_mode("enforcement") == 50
    assert spec.family == "nominal"


def test_load_full_scenario_sc_edge_05():
    spec = load_scenario(_SCEN / "edge" / "sc_edge_05.yaml")
    assert spec.id == "SC-EDGE-05"
    assert "SR-010" in spec.references_SR
    assert spec.runs_for_mode("enforcement") == 100
    assert spec.family == "adverse"


# The scenario library is fully promoted (no stubs remain in the repo since the
# 04.06 F4 stub-promotion), so the stub mechanism is exercised on synthetic YAMLs.
_ALL_SCENARIO_IDS = (
    "SC-NOM-01", "SC-NOM-02", "SC-NOM-03",
    "SC-EDGE-01", "SC-EDGE-02", "SC-EDGE-03", "SC-EDGE-04", "SC-EDGE-05",
    "SC-PERT-01", "SC-PERT-02", "SC-PERT-03",
)


def test_stub_raises(tmp_path):
    stub = tmp_path / "sc_stub.yaml"
    stub.write_text("id: SC-STUB-01\nstatus: stub\n", encoding="utf-8")
    with pytest.raises(ScenarioStub):
        load_scenario(stub)


def test_load_scenarios_loads_all_full():
    # all 11 documented scenarios are promoted to full YAMLs (none skipped)
    specs = load_scenarios(_SCEN)
    for sid in _ALL_SCENARIO_IDS:
        assert sid in specs, f"{sid} missing from loaded scenarios"


def test_load_scenarios_skips_stub_in_dir(tmp_path):
    # a stub dropped alongside full scenarios is skipped by the bulk loader
    cat = tmp_path / "nominal"
    cat.mkdir()
    shutil.copy(_SCEN / "nominal" / "sc_nom_01.yaml", cat / "sc_nom_01.yaml")
    (cat / "sc_stub.yaml").write_text("id: SC-STUB-01\nstatus: stub\n", encoding="utf-8")
    specs = load_scenarios(tmp_path)
    assert "SC-NOM-01" in specs
    assert "SC-STUB-01" not in specs
