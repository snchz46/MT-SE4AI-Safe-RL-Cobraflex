"""
Contract test for the sim-to-real fine-tune config (M-7/D-71).

The run's whole claim is that it changes ONE experimental variable against the
2-D trunk it continues from. That is a checkable property, so it is checked here
rather than asserted in a comment: a stray edit to the cage block, the reward
weights or the stressor schedule would silently turn the fine-tune into an
uninterpretable two-variable run.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

_REPO = Path(__file__).resolve().parents[2]
_PKG_PARENT = _REPO / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.visual_degradation import LOW_CONTRAST  # noqa: E402
from cobraflex_rl.visual_domain_randomization import (  # noqa: E402
    DomainRandomizationConfig,
    VisualDomainRandomizer,
)

_CONFIG_DIR = _PKG_PARENT / "config"
PARENT = _CONFIG_DIR / "train_ppo_camera_2d_cap022_1M.yaml"
FINETUNE = _CONFIG_DIR / "train_ppo_camera_2d_sim2real_ft.yaml"

# The level at which apply_low_contrast reproduces the photometry M-7 measured
# on the physical circuit (road grey 106, markings 209).
MEASURED_HALL_LEVEL = 0.75


@pytest.fixture(scope="module")
def configs():
    return yaml.safe_load(PARENT.read_text()), yaml.safe_load(FINETUNE.read_text())


def test_finetune_changes_only_the_intended_keys(configs):
    parent, finetune = configs
    differing = {
        k for k in set(parent) | set(finetune) if parent.get(k) != finetune.get(k)
    }
    assert differing == {
        "domain_randomization",   # the experimental variable
        "learning_rate",          # standard fine-tune reduction
        "total_timesteps",        # the fine-tune budget
        "model_path",             # a different run must not overwrite the parent
    }


def test_finetune_lowers_the_learning_rate(configs):
    parent, finetune = configs
    assert finetune["learning_rate"] < parent["learning_rate"]


def test_stressor_schedule_is_untouched(configs):
    """The H-10 stressors must keep the parent's rate, or the run confounds
    photometric invariance with more (or less) glare and blur."""
    parent, finetune = configs
    p, f = parent["domain_randomization"], finetune["domain_randomization"]
    assert f["p_degrade"] == p["p_degrade"]
    assert f["level_range"] == p["level_range"]
    assert f.get("modes", None) == p.get("modes", None)
    # and low_contrast must NOT be smuggled into `modes` — as a one-of-N draw it
    # would reach only ~12 % of episodes.
    assert LOW_CONTRAST not in (f.get("modes") or ())


def test_photometric_operating_point_is_drawn_every_episode(configs):
    _, finetune = configs
    dr = finetune["domain_randomization"]
    assert dr["base_mode"] == LOW_CONTRAST
    assert dr["p_base"] == 1.0
    lo, hi = dr["base_level_range"]
    # both endpoints are load-bearing: 0 keeps the Gazebo render (where every
    # scored campaign still evaluates) in distribution, and the top must reach
    # past the measured hall so the deployment condition is interior.
    assert lo == 0.0
    assert hi > MEASURED_HALL_LEVEL


def test_the_shipped_config_samples_as_intended(configs):
    """End-to-end: the YAML as written, through the sampler the env builds."""
    _, finetune = configs
    dr = finetune["domain_randomization"]
    randomizer = VisualDomainRandomizer(
        DomainRandomizationConfig(
            p_degrade=float(dr["p_degrade"]),
            level_range=tuple(dr["level_range"]),
            base_mode=dr["base_mode"],
            p_base=float(dr["p_base"]),
            base_level_range=tuple(dr["base_level_range"]),
        )
    )
    rng = np.random.default_rng(2024)
    specs = [randomizer.sample(rng) for _ in range(2000)]

    assert all(s.base_mode == LOW_CONTRAST for s in specs)
    stressed = np.mean([s.mode is not None for s in specs])
    assert 0.45 < stressed < 0.55
    levels = np.array([s.base_level for s in specs])
    # the deployment condition must be sampled often enough to be learned, and
    # must not be the only thing sampled
    assert 0.15 < np.mean(levels >= MEASURED_HALL_LEVEL) < 0.40
    assert np.mean(levels <= 0.1) > 0.05


def test_cage_configuration_is_identical_to_the_parent(configs):
    """The 19.08 heading finding (near_secant/1.0 is cleaner) applies to the
    RECTIFIED PHYSICAL image, not to the Gazebo render. Adopting it here would
    put a second variable in the run."""
    parent, finetune = configs
    assert finetune["cage"] == parent["cage"]
    assert finetune["cage"]["perception_heading_fit_mode"] == "joint_pair_quadratic"
