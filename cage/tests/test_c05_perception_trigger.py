"""
Unit tests for C-05 Trigger 8 — perception invalid (track 'E').

SR-013 (loss of valid perception) / SR-014 (suspect estimate) — D-40.
The external supervisor sets ctx["perception_invalid"]; C-05 answers with
the open-loop controlled stop. Gated by `perception_trigger_enabled`
(default False in code → inert for pre-0.6.0 YAMLs).

Coverage:
    - trigger fires immediately when enabled and ctx flag set
    - reason / metadata identify Trigger 8
    - default-off: flag is ignored when YAML key absent
    - explicitly disabled: flag is ignored
    - emergency persists while the flag persists (require_explicit_reset)
    - reset + flag cleared → exit
    - throttle is the brake value; steering frozen at activation
"""

from pathlib import Path

import pytest
import yaml

from cage.rules import EmergencyRule, State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture(scope="module")
def c05_params():
    with CAGE_YAML.open() as f:
        return yaml.safe_load(f)["cage"]["c05_emergency"]


@pytest.fixture
def rule(c05_params):
    return EmergencyRule(c05_params)


def test_yaml_enables_perception_trigger(c05_params):
    # cage.yaml 0.6.0 ships with the trigger enabled for track 'E'.
    assert c05_params["perception_trigger_enabled"] is True


def test_perception_invalid_fires_immediately(rule):
    r = rule.evaluate(
        state=State(),
        raw_action=(0.2, 0.5),
        ctx={"current_time": 1.0, "perception_invalid": True},
    )
    assert r.fire is True
    assert r.reason == "triggered-perception-invalid"
    assert r.metadata["trigger"] == 8
    assert r.metadata["triggers"]["perception"] is True


def test_perception_trigger_default_off(c05_params):
    params = {k: v for k, v in c05_params.items() if k != "perception_trigger_enabled"}
    rule = EmergencyRule(params)
    r = rule.evaluate(
        state=State(),
        raw_action=(0.0, 0.5),
        ctx={"current_time": 1.0, "perception_invalid": True},
    )
    assert r.fire is False


def test_perception_trigger_explicitly_disabled(c05_params):
    params = dict(c05_params)
    params["perception_trigger_enabled"] = False
    rule = EmergencyRule(params)
    r = rule.evaluate(
        state=State(),
        raw_action=(0.0, 0.5),
        ctx={"current_time": 1.0, "perception_invalid": True},
    )
    assert r.fire is False


def test_emergency_persists_until_reset_and_cleared(rule):
    ctx_bad = {"current_time": 1.0, "perception_invalid": True}
    rule.evaluate(state=State(), raw_action=(0.1, 0.5), ctx=ctx_bad)
    # Flag cleared but no explicit reset: emergency persists.
    r1 = rule.evaluate(
        state=State(),
        raw_action=(0.0, 0.5),
        ctx={"current_time": 1.1, "perception_invalid": False},
    )
    assert r1.fire is True
    # Reset while flag still raised: emergency persists.
    r2 = rule.evaluate(
        state=State(),
        raw_action=(0.0, 0.5),
        ctx={"current_time": 1.2, "perception_invalid": True, "reset": True},
    )
    assert r2.fire is True
    # Reset + flag cleared → exit.
    r3 = rule.evaluate(
        state=State(),
        raw_action=(0.0, 0.5),
        ctx={"current_time": 1.3, "perception_invalid": False, "reset": True},
    )
    assert r3.fire is False
    assert r3.reason == "emergency-cleared"


def test_controlled_stop_action(rule, c05_params):
    r = rule.evaluate(
        state=State(),
        raw_action=(0.3, 0.5),
        ctx={"current_time": 1.0, "perception_invalid": True},
    )
    steering, throttle = r.safe_action
    assert throttle < 0.0  # brake
    if c05_params["freeze_steering"]:
        assert steering == pytest.approx(0.3)  # frozen at activation
