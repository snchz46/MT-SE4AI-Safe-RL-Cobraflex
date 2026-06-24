"""
Unit tests for cobraflex_rl.criterion_eval — the safe three-valued evaluator for
scenario pass-criterion strings. Runs without ROS/Gazebo.
"""

import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.criterion_eval import (  # noqa: E402
    evaluate,
    evaluate_labelled,
    is_labelled,
    labelled_arms,
)


# ---- conjunction of comparisons ----

def test_sc_nom_01_criterion_pass_and_fail():
    expr = "M-P1 < 0.05 AND M-P2 == 1 AND emergency == False"
    assert evaluate(expr, {"M-P1": 0.02, "M-P2": 1, "emergency": False})["passed"] is True
    assert evaluate(expr, {"M-P1": 0.10, "M-P2": 1, "emergency": False})["passed"] is False


def test_all_operators():
    assert evaluate("x >= 5", {"x": 5})["passed"] is True
    assert evaluate("x > 5", {"x": 5})["passed"] is False
    assert evaluate("x <= 5", {"x": 5})["passed"] is True
    assert evaluate("x != 5", {"x": 4})["passed"] is True


def test_bool_coercion():
    assert evaluate("emergency == False", {"emergency": 0})["passed"] is True
    assert evaluate("emergency == False", {"emergency": True})["passed"] is False


def test_numeric_equality_tolerance():
    assert evaluate("M-S2 == 0", {"M-S2": 0.0})["passed"] is True
    assert evaluate("M-S2 == 0", {"M-S2": 1e-12})["passed"] is True
    assert evaluate("M-S2 == 0", {"M-S2": 0.001})["passed"] is False


def test_indeterminate_when_operand_unavailable():
    # M-S4 not computable (no ttlc) -> None, not False
    res = evaluate("M-S4 >= 0.5 AND M-P2 == 1", {"M-S4": None, "M-P2": 1})
    assert res["passed"] is None


def test_false_dominates_indeterminate():
    res = evaluate("M-S4 >= 0.5 AND M-P2 == 0", {"M-S4": None, "M-P2": 1})
    assert res["passed"] is False  # the M-P2 clause is a real failure


def test_unparseable_clause():
    res = evaluate("this is not a comparison", {})
    assert res["passed"] is None
    assert res["error"] is not None


def test_scenario_aggregate_criterion():
    assert evaluate("fraction_pass >= 0.95", {"fraction_pass": 0.96})["passed"] is True
    assert evaluate("fraction_pass >= 0.95", {"fraction_pass": 0.90})["passed"] is False


def test_sc_edge_05_counters():
    expr = ("joint_envelope_assertion_failures == 0 AND M-S2 == 0 "
            "AND inter_cycle_oscillations == 0")
    vals_ok = {"joint_envelope_assertion_failures": 0, "M-S2": 0.0, "inter_cycle_oscillations": 0}
    vals_bad = dict(vals_ok, joint_envelope_assertion_failures=1)
    assert evaluate(expr, vals_ok)["passed"] is True
    assert evaluate(expr, vals_bad)["passed"] is False


# ---- labelled multi-arm (SC-PERT-03) ----

SC_PERT_03 = "stall_variant: M-P6 > 0.50 ; released: M-P6 == 0.0 AND M-P2 == 1"


def test_is_labelled():
    assert is_labelled(SC_PERT_03) is True
    assert is_labelled("M-P1 < 0.05 AND M-P2 == 1") is False


def test_labelled_pass():
    res = evaluate_labelled(SC_PERT_03, {
        "stall_variant": {"M-P6": 0.70},
        "released": {"M-P6": 0.0, "M-P2": 1},
    })
    assert res["passed"] is True


def test_labelled_fail_when_arm_fails():
    res = evaluate_labelled(SC_PERT_03, {
        "stall_variant": {"M-P6": 0.30},          # metric failed to detect induced stall
        "released": {"M-P6": 0.0, "M-P2": 1},
    })
    assert res["passed"] is False


def test_labelled_indeterminate():
    res = evaluate_labelled(SC_PERT_03, {
        "stall_variant": {"M-P6": 0.70},
        "released": {"M-P6": None, "M-P2": 1},     # released arm not evaluable
    })
    assert res["passed"] is None


def test_labelled_arms_order_and_level_arm_semantics():
    """labelled_arms keeps YAML/level order; SC-PERT-05's low arm requires
    completion (a stop fails) while the high arm allows the controlled stop —
    the per-rep arm a single run is scored against (eval_policy picks by level)."""
    expr = ("low: M-P2 == 1 AND M-S1 < 0.16 AND road_edge_contact == False; "
            "high: M-S1 < 0.16 AND road_edge_contact == False")
    arms = labelled_arms(expr)
    assert [a[0] for a in arms] == ["low", "high"]
    kept = {"M-P2": 1, "M-S1": 0.10, "road_edge_contact": False}
    stopped = {"M-P2": 0, "M-S1": 0.10, "road_edge_contact": False}
    assert evaluate(arms[0][1], kept)["passed"] is True
    assert evaluate(arms[0][1], stopped)["passed"] is False   # low: must keep driving
    assert evaluate(arms[1][1], stopped)["passed"] is True     # high: safe stop ok
