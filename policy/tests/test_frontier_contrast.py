"""Unit tests for tools/frontier_contrast — the paired enforcement-vs-monitoring
analysis of the frontier cage-efficacy study. Pure stdlib, no ROS."""

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import frontier_contrast as fc  # noqa: E402


def _summary(scenario, mode, max_exc, contact, emergency=True, verdict=True, reason="off_road"):
    return {
        "scenario_id": scenario, "mode": mode, "verdict": verdict,
        "campaign": {
            "termination_reason": reason,
            "values": {"max_excursion_m": max_exc, "road_edge_contact": contact,
                       "emergency": emergency},
        },
    }


def test_parse_run_extracts_seed_and_mode():
    rec = fc.parse_run("camp_front03_rl_seed123_monitoring_rep00",
                       _summary("SC-FRONT-03", "monitoring", 0.272, True))
    assert rec is not None
    assert rec.seed == "123"
    assert rec.mode == "monitoring"
    assert rec.rep == 0
    assert rec.road_edge_contact is True
    assert rec.max_excursion_m == 0.272


def test_parse_run_rejects_non_campaign_dir():
    assert fc.parse_run("rl_eval_20260608T082007Z", _summary("SC-NOM-01", "enforcement", 0.02, False)) is None


def test_contrast_quantifies_cage_benefit_for_weak_policy():
    records = [
        # weak policy 123: enforcement safe, monitoring crashes
        fc.parse_run("camp_front03_rl_seed123_enforcement_rep00",
                     _summary("SC-FRONT-03", "enforcement", 0.136, False, reason="cage_emergency")),
        fc.parse_run("camp_front03_rl_seed123_monitoring_rep00",
                     _summary("SC-FRONT-03", "monitoring", 0.272, True, reason="off_road")),
    ]
    rep = fc.contrast([r for r in records if r])
    assert len(rep) == 1
    row = rep[0]
    assert row["seed"] == "123"
    assert row["enforcement"]["contact_rate"] == 0.0
    assert row["monitoring"]["contact_rate"] == 1.0
    # cage prevents 100% of the contacts and ~0.136 m of excursion
    assert row["cage_benefit"]["contact_rate_reduction"] == 1.0
    assert abs(row["cage_benefit"]["max_excursion_reduction_median"] - 0.136) < 1e-9


def test_contrast_good_policy_no_benefit():
    records = [
        fc.parse_run("camp_front03_rl_seed2024_enforcement_rep00",
                     _summary("SC-FRONT-03", "enforcement", 0.136, False, reason="cage_emergency")),
        fc.parse_run("camp_front03_rl_seed2024_monitoring_rep00",
                     _summary("SC-FRONT-03", "monitoring", 0.136, False, reason="truncated")),
    ]
    rep = fc.contrast([r for r in records if r])
    row = rep[0]
    assert row["monitoring"]["contact_rate"] == 0.0
    assert row["cage_benefit"]["contact_rate_reduction"] == 0.0


def test_cell_stats_median_and_rates():
    runs = [
        fc.parse_run(f"camp_x_rl_seed1_monitoring_rep0{i}",
                     _summary("SC-X", "monitoring", exc, contact))
        for i, (exc, contact) in enumerate([(0.20, False), (0.27, True), (0.30, True)])
    ]
    stats = fc._cell_stats([r for r in runs if r])
    assert stats["n"] == 3
    assert abs(stats["contact_rate"] - 2 / 3) < 1e-9
    assert stats["max_excursion_median"] == 0.27
