"""Unit tests for the SC-EDGE-05 in-ODD/OOD grid attribution split (SR-010, D-48)
in tools/campaign_e_failure_modes.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import campaign_e_failure_modes as fm  # noqa: E402


def _run(d_m, theta_deg, ms1, verdict, anchor="C01_C02", mode="enforcement"):
    return {
        "scenario_id": "SC-EDGE-05",
        "mode": mode,
        "verdict": verdict,
        "campaign": {
            "grid_point": {"anchor_id": anchor, "seed": {"d_m": d_m, "theta_deg": theta_deg}},
            "values": {"M-S1": ms1},
        },
    }


def test_grid_split_classifies_in_odd_vs_ood():
    runs = [
        _run(0.10, 10.0, 0.30, False),   # in-ODD (d,θ in range), M-S1 breach
        _run(0.115, 12.0, 0.10, True),   # in-ODD, pass
        _run(0.13, 5.0, 0.30, False),    # OOD: d = 0.13 > 0.1225, breach
        _run(0.05, 30.0, 0.05, True),    # OOD: θ = 30 > 25, pass
    ]
    split = fm.sc_edge05_grid_split(runs)
    assert split["buckets"]["in_odd"] == {"n": 2, "pass": 1, "fail": 1, "ms1_breach": 1}
    assert split["buckets"]["ood"] == {"n": 2, "pass": 1, "fail": 1, "ms1_breach": 1}
    assert split["criteria"]["d_odd_m"] == fm.D_ODD_M


def test_grid_split_only_enforcement_edge05():
    runs = [
        _run(0.10, 10.0, 0.30, False, mode="monitoring"),         # wrong mode -> skipped
        {"scenario_id": "SC-NOM-01", "mode": "enforcement"},      # wrong scenario -> skipped
    ]
    assert fm.sc_edge05_grid_split(runs) is None


def test_grid_split_boundary_is_in_odd():
    # exactly at the painted edge / theta_max counts as in-ODD (<=, not <)
    split = fm.sc_edge05_grid_split([_run(0.1225, 25.0, 0.10, True)])
    assert split["buckets"]["in_odd"]["n"] == 1
    assert split["buckets"]["ood"]["n"] == 0
