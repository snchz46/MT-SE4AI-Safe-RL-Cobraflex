import csv
import importlib.util
from pathlib import Path
import sys

import pytest


PATH = Path(__file__).parents[1] / "calibrate_d43_c02.py"
SPEC = importlib.util.spec_from_file_location("calibrate_d43_c02", PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def row(split, cell, *, epsi_gt=0.0, epsi_cv=0.0, c02=0, c05=0,
        timestamp=0.0, speed_mps=0.0, ey_gt=0.0):
    return {"split": split, "cell_id": cell, "ey_gt": ey_gt, "epsi_gt": epsi_gt,
            "epsi_cv": epsi_cv, "c02": c02, "c05": c05, "timestamp": timestamp,
            "road_edge_contact": int(abs(ey_gt) >= MOD.ROAD_HALF_M),
            "m_s1": abs(ey_gt), "m_s2": int(abs(ey_gt) > MOD.D_MAX),
            "speed_mps": speed_mps,
            "curvature_gt": 0.0, "curvature_anchor_gt": 0.0,
            "epsi_error": epsi_cv - epsi_gt}


def test_held_out_false_negative_blocks():
    rows = [row("calibration", "safe"), row("calibration", "fault", epsi_gt=.48, epsi_cv=.5, c02=1),
            row("validation", "safe"), row("validation", "fault", epsi_gt=.48, epsi_cv=.1)]
    report = MOD.analyse(rows)
    assert report["status"] == "BLOCKED"
    assert "heading false negative" in report["blockers"]


def test_clean_separated_validation_passes():
    rows = [row(split, "safe") for split in ("calibration", "validation")]
    for split in ("calibration", "validation"):
        rows += [
            row(split, "fault", timestamp=0.0, speed_mps=.22),
            row(split, "fault", epsi_gt=.48, epsi_cv=.50, c02=1,
                timestamp=.1, speed_mps=0.0),
        ]
    assert MOD.analyse(rows)["status"] == "PASS"


def test_m_s2_counts_real_lateral_crossing_not_rule_activity():
    safe = row("validation", "safe", c02=1, ey_gt=.02)
    breach = row("validation", "breach", ey_gt=.17)
    assert safe["m_s2"] == 0
    assert breach["m_s2"] == 1


def test_matrix_has_disjoint_splits_and_faults():
    anchors = {"straight": (0.0, 0.0), "odd_curve": (1.0, .5), "demanding": (2.0, 1.0)}
    matrix = MOD.build_matrix(anchors)
    assert {c.seed for c in matrix if c.split == "calibration"} == {2024}
    assert {c.seed for c in matrix if c.split == "validation"} == {42}
    assert any(abs(c.heading_rad) > MOD.THETA_MAX for c in matrix)


def test_curvature_oracle_is_per_cycle_and_signed():
    import math

    points = [(5.0 * math.cos(a), 5.0 * math.sin(a))
              for a in [2.0 * math.pi * i / 120 for i in range(120)]]
    assert MOD.curvature_at_s(points, 0.0) == pytest.approx(0.2, abs=0.01)


def test_heading_candidate_is_opt_in():
    defaults = MOD.parse_args(["--input", "trace.csv"])
    assert defaults.heading_fit_mode == "near_secant"
    assert defaults.heading_gain == 1.0
    args = MOD.parse_args([
        "--input", "trace.csv", "--heading-fit-mode", "joint_pair_quadratic",
        "--heading-gain", "1.75",
    ])
    assert args.heading_fit_mode == "joint_pair_quadratic"
    assert args.heading_gain == 1.75
