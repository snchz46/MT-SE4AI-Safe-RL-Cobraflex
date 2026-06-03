"""
Unit tests for cobraflex_rl.scenario_loader — parsing the real scenario YAMLs
under scenarios/. Runs without ROS/Gazebo.
"""

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


def test_stub_raises():
    # sc_nom_02 is an explicit stub in the repo
    with pytest.raises(ScenarioStub):
        load_scenario(_SCEN / "nominal" / "sc_nom_02.yaml")


def test_load_scenarios_skips_stubs():
    specs = load_scenarios(_SCEN)
    # the four full scenarios are present...
    for sid in ("SC-NOM-01", "SC-EDGE-01", "SC-EDGE-05", "SC-PERT-03"):
        assert sid in specs
    # ...and the known stubs are not
    assert "SC-NOM-02" not in specs
    assert "SC-PERT-02" not in specs
