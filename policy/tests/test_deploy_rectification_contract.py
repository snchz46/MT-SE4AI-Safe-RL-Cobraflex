"""
Deployment contract: the policy and the cage's estimator must see the SAME frame.

``cv_lane_estimator_node`` gained ``rectify_calibration`` on 19.08; the policy
node did not, so a rectified deployment would have had the cage arbitrating a
canonical world while the CNN saw the raw 160-degree lens. That is not a small
inconsistency for the policy: rendering the Gazebo pose set through the measured
M-6 lens costs the 550k trunk a third of its lane response (steering swing 0.363
-> 0.232), and on the compound photometric+geometric arm the fine-tuned policy
reads swing 0.030 raw against 0.081 rectified.

The launch file therefore exposes ONE argument feeding BOTH nodes, and these
tests pin that it cannot drift back apart.
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

LAUNCH = _PKG_PARENT / "launch" / "deploy_cobraflex.launch.py"
POLICY_NODE = _PKG_PARENT / "cobraflex_rl" / "rl_policy_node.py"
ESTIMATOR_NODE = _PKG_PARENT / "cobraflex_rl" / "cv_lane_estimator_node.py"


def _node_parameter_block(source: str, executable: str) -> str:
    """The ``parameters=[{...}]`` literal belonging to one Node(...) call."""
    start = source.index(f'executable="{executable}"')
    params = source.index("parameters=[{", start)
    end = source.index("}]", params)
    return source[params:end]


@pytest.mark.parametrize("executable", ["rl_policy_node", "cv_lane_estimator_node"])
def test_both_consumers_receive_the_rectification_parameter(executable):
    block = _node_parameter_block(LAUNCH.read_text(), executable)
    assert "rectify_calibration" in block, (
        f"{executable} does not receive rectify_calibration — the policy and the "
        "cage would disagree about the camera model"
    )


def test_they_receive_the_SAME_launch_argument():
    """Two independent arguments would let an operator rectify one and not the
    other, which is the failure this contract exists to prevent."""
    source = LAUNCH.read_text()
    refs = set()
    for executable in ("rl_policy_node", "cv_lane_estimator_node"):
        block = _node_parameter_block(source, executable)
        match = re.search(
            r'"rectify_calibration":\s*LaunchConfiguration\(\s*"([^"]+)"', block
        )
        assert match, f"{executable} must take it from a LaunchConfiguration"
        refs.add(match.group(1))
    assert refs == {"rectify_calibration"}


def test_rectification_is_off_by_default():
    """Every Gazebo path already renders the canonical camera, and the rectified
    estimator has never run on hardware; it is opted into behind a lanecheck."""
    source = LAUNCH.read_text()
    match = re.search(
        r'DeclareLaunchArgument\(\s*\n?\s*"rectify_calibration",\s*default_value="(.*?)"',
        source,
    )
    assert match and match.group(1) == ""


@pytest.mark.parametrize("node", [POLICY_NODE, ESTIMATOR_NODE])
def test_both_nodes_build_maps_from_the_one_shared_authority(node):
    """The M-6 intrinsics are read from the calibration JSON through
    camera_geometry, never copied into either node."""
    source = node.read_text()
    assert "rectification_maps_from_calibration" in source
    assert "395.93" not in source and "0.33896" not in source


@pytest.mark.parametrize("node", [POLICY_NODE, ESTIMATOR_NODE])
def test_both_nodes_replicate_the_border_rather_than_filling_it_black(node):
    """The unmapped strip is the extreme near-field corner; a black wedge there
    would read as a dark object rather than as more road."""
    source = node.read_text()
    assert "BORDER_REPLICATE" in source
