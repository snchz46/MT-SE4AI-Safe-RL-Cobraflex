"""
Deployment contract: a physical run must be able to say what produced it, and
must keep the frames that explain how it ended.

Both halves are lessons, not preferences:

* `docs/17` §8.9 — ``cage_logger_node`` wrote ``{mode, run_id, created_utc,
  cycles_logged}`` and nothing else, contrary to CLAUDE.md's rule for
  ``experiments/physical/runs/``, so the provenance of the 18.08 and 26.08 track
  sessions is a hand-written paragraph at the head of §8 rather than evidence.
* §8.9 again — the measurement that would localise a perception failure is the
  frames the estimator saw, and two sessions have now ended on unexplained
  ``/perception_invalid`` events with no frames kept.

The drift these tests exist to catch is the quiet one: adding a field to
``CONTRACT_KEYS`` and forgetting the launch that feeds it, which yields a
metadata.json that looks complete and records nothing.
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.run_io import CONTRACT_KEYS  # noqa: E402

LAUNCH_SOURCE = (_PKG_PARENT / "launch" / "deploy_cobraflex.launch.py").read_text(
    encoding="utf-8"
)
CAGE_YAML = (_REPO / "cage" / "cage.yaml").read_text(encoding="utf-8")


def _node_parameter_block(executable: str) -> str:
    start = LAUNCH_SOURCE.index(f'executable="{executable}"')
    params = LAUNCH_SOURCE.index("parameters=[{", start)
    end = LAUNCH_SOURCE.index("}]", params)
    return LAUNCH_SOURCE[params:end]


# --------------------------------------------------------------- provenance
def test_the_logger_is_told_the_run_is_physical():
    """The switch that turns the four-field legacy metadata into the full block."""
    assert '"platform": "physical"' in _node_parameter_block("cage_logger_node")


@pytest.mark.parametrize("field", ["cage_yaml", "policy_checkpoint",
                                   "rectify_calibration"])
def test_the_hashed_artefacts_are_forwarded(field):
    assert f'"{field}"' in _node_parameter_block("cage_logger_node")


@pytest.mark.parametrize("key", CONTRACT_KEYS)
def test_every_contract_key_is_actually_fed_by_the_launch(key):
    """A key the node declares but the launch never passes records "" — that is
    worse than not recording it, because the metadata looks complete."""
    assert f'"contract.{key}"' in _node_parameter_block("cage_logger_node"), (
        f"CONTRACT_KEYS declares {key!r} but deploy_cobraflex.launch.py does not "
        "pass it; the run's metadata.json would record it as absent"
    )


def test_the_checkpoint_hashed_is_the_one_deployed():
    """Hashing some other path would be provenance theatre."""
    block = _node_parameter_block("cage_logger_node")
    assert re.search(r'"policy_checkpoint":\s*checkpoint\b', block)


def test_the_layer2_settings_are_not_faked_here():
    """`lane_camera_capture_fps` and the ZED overrides decided the 26.08 session,
    but this is a Layer-3 launch and cannot know what Layer 2 was started with.
    Recording a plausible default would be a lie in the evidence."""
    assert "lane_camera_capture_fps" not in CONTRACT_KEYS
    assert "zed_overrides" not in CONTRACT_KEYS


# ------------------------------------------------------------ frame capture
def test_frame_capture_is_in_the_launch_and_on_by_default():
    assert 'executable="frame_capture_node"' in LAUNCH_SOURCE
    assert re.search(
        r'DeclareLaunchArgument\(\s*"capture_frames",\s*default_value="true"',
        LAUNCH_SOURCE,
    ), "frames must be captured unless explicitly disabled — §8.9 twice"


def test_frame_capture_reads_the_same_topic_the_estimator_does():
    """Capturing a different stream would answer a question nobody asked."""
    block = _node_parameter_block("frame_capture_node")
    assert re.search(r'"image_topic":\s*camera_topic\b', block)
    estimator = _node_parameter_block("cv_lane_estimator_node")
    assert re.search(r'"image_topic":\s*camera_topic\b', estimator)


# --------------------------------------------------------------- reset path
def test_the_reset_proxy_never_publishes_unless_asked():
    """`observe` is the default: it logs what a reset path would have done and
    publishes nothing. Only `auto` actuates, and that makes the run diagnostic."""
    assert re.search(
        r'DeclareLaunchArgument\(\s*"reset_proxy",\s*default_value="observe"',
        LAUNCH_SOURCE,
    )
    block = _node_parameter_block("cage_reset_proxy_node")
    assert '"auto"' in block, "enabled must be gated on reset_proxy == auto"


def test_c05_itself_is_untouched():
    """D-74 keeps C-05 exactly as every campaign scored it: the reset path lives
    outside the cage. If this ever fails, D-74 was reversed without an ADR."""
    assert re.search(r"require_explicit_reset:\s*true", CAGE_YAML), (
        "c05_emergency.require_explicit_reset changed: the operator-proxy work "
        "was allowed to leak into the artefact under test"
    )


# ------------------------------------------------- launch parameter typing
# The three tests above are source-text checks, and they all passed on
# 27.08.2026 while the node they describe could not start at all. The first
# time the deploy chain was launched with the provenance block (31.08.2026,
# wheels up, Layers 1+2 running) `cage_logger_node` died in its constructor:
#
#   InvalidParameterTypeException: Trying to set parameter
#   'contract.max_speed_mps' to '0.22' of type 'DOUBLE', expecting type 'STRING'
#
# `ros2 launch` serialises node parameters through a YAML file, so a value that
# merely LOOKS numeric arrives typed. The crash was the visible half; the quiet
# half is that `.string_value` on a DOUBLE returns "", which would have dropped
# max_speed_mps, control_rate_hz and both gains from metadata.json while leaving
# it looking complete — exactly the drift this module's docstring names.
#
# So this test drives the real node through the real type inference: `-p k:=v`
# on the command line is typed by the same rcl YAML rules the launch file uses.


def test_a_numeric_contract_value_reaches_metadata_as_a_string(tmp_path):
    rclpy = pytest.importorskip("rclpy")
    pytest.importorskip("cobraflex_safety_msgs.msg")
    import json

    from cobraflex_rl.cage_logger_node import CageLoggerNode

    rclpy.init(args=[
        "--ros-args",
        "-p", f"output_dir:={tmp_path}",
        "-p", "run_id:=typing_probe",
        "-p", "platform:=physical",
        "-p", "cage_mode:=monitoring",
        # strings, doubles and integers, as deploy_cobraflex.launch.py emits them
        "-p", "contract.algorithm:=ppo",
        "-p", "contract.heading_fit_mode:=near_secant",
        "-p", "contract.max_speed_mps:=0.22",
        "-p", "contract.control_rate_hz:=10.0",
        "-p", "contract.steering_to_yaw_rate_gain:=1.615",
        "-p", "contract.heading_temporal_window:=4",
        "-p", "contract.white_sat_max:=-1",
    ])
    try:
        node = CageLoggerNode()          # must not raise
        node.destroy_node()
    finally:
        rclpy.shutdown()

    contract = json.loads(
        (tmp_path / "typing_probe" / "metadata.json").read_text()
    )["contract"]

    # The numeric ones are the point: they are what silently vanished.
    assert contract["max_speed_mps"] == "0.22"
    assert contract["control_rate_hz"] == "10.0"
    assert contract["steering_to_yaw_rate_gain"] == "1.615"
    assert contract["heading_temporal_window"] == "4"
    assert contract["white_sat_max"] == "-1"
    # and the string ones still behave
    assert contract["algorithm"] == "ppo"
    assert contract["heading_fit_mode"] == "near_secant"
