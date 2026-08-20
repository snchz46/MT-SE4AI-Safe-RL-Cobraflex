"""
Contract test for the from-scratch sim-to-real run (D-71 follow-up).

The run changes four things at once, deliberately — there is one multi-day slot
and each of the four is separately evidenced. That makes it *more* important,
not less, that the four are exactly the four: a stray edit to the cage block,
the reward weights or the stressor schedule would add a fifth variable to a run
whose attribution already rests entirely on the offline probe arms rather than
on its own reward curve.

What this pins is the CONFIG. It says nothing about the outcome, and nothing
here re-scores a gate: the simulation verdict of record remains the 550k trunk
and its 1890-run campaign (D-67/D-69).
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
from cobraflex_rl.geometric_domain_randomization import (  # noqa: E402
    GeometricDomainRandomizer,
    GeometricRandomizationConfig,
)

_CONFIG_DIR = _PKG_PARENT / "config"
TRUNK = _CONFIG_DIR / "train_ppo_camera_2d_cap022_1M.yaml"
V2 = _CONFIG_DIR / "train_ppo_camera_2d_sim2real_v2.yaml"

# apply_low_contrast level at which the render reproduces the photometry M-7
# measured on the physical circuit (road grey 106 +/- 3, markings 209).
MEASURED_HALL_LEVEL = 0.75


@pytest.fixture(scope="module")
def configs():
    return yaml.safe_load(TRUNK.read_text()), yaml.safe_load(V2.read_text())


def test_v2_changes_only_the_intended_keys(configs):
    trunk, v2 = configs
    differing = {k for k in set(trunk) | set(v2) if trunk.get(k) != v2.get(k)}
    assert differing == {
        "mirror_augmentation",       # 1. handedness prior
        "domain_randomization",      # 2. photometry, re-weighted
        "geometric_randomization",   # 3. lens + mount pose
        "ent_coef",                  # 4. PPO health: exploration
        "lr_schedule",               # 4. PPO health: a live LR in the tail
        "lr_floor_fraction",         # 4.  "
        "total_timesteps",           # the budget
        "viz",                       # headless multi-day run
        "model_path",                # must not overwrite the trunk
    }


def test_it_is_a_from_scratch_run_at_the_agreed_budget(configs):
    _, v2 = configs
    assert v2["total_timesteps"] == 2_500_000
    assert v2["seed"] == 2024
    # A resume would be expressed on the launch line, but the config must not
    # silently carry a parent: the whole point is that no left-steer prior is
    # inherited.
    assert "resume_from" not in v2 and "parent_policy_checkpoint" not in v2


def test_ppo_health_changes_go_the_right_way(configs):
    trunk, v2 = configs
    # More exploration: the fine-tune's action std fell 0.054 -> 0.024
    # monotonically under the trunk's value, with no plateau.
    assert v2["ent_coef"] > trunk["ent_coef"]
    # And an LR that is still alive in the last third, where the far corners of
    # the randomisation distribution finally get visited.
    assert v2["lr_schedule"] == "linear_floor"
    assert 0.0 < v2["lr_floor_fraction"] < 1.0
    assert v2["learning_rate"] == trunk["learning_rate"]  # only the SHAPE changed
    assert v2["target_kl"] == trunk["target_kl"]


def test_mirror_is_a_balanced_per_episode_draw(configs):
    _, v2 = configs
    mirror = v2["mirror_augmentation"]
    assert mirror["enabled"] is True
    # Exactly 0.5, or complex_b's 6.5:1 left dominance is only partly cancelled.
    assert mirror["p"] == 0.5


def test_stressor_schedule_is_untouched(configs):
    """The H-10 stressors keep the trunk's rate, or the run confounds sim-to-real
    invariance with more (or less) glare and blur."""
    trunk, v2 = configs
    t, v = trunk["domain_randomization"], v2["domain_randomization"]
    assert v["p_degrade"] == t["p_degrade"]
    assert v["level_range"] == t["level_range"]
    assert v.get("modes", None) == t.get("modes", None)
    assert LOW_CONTRAST not in (v.get("modes") or ())


def test_photometry_is_reweighted_onto_the_hall_without_dropping_gazebo(configs):
    _, v2 = configs
    dr = v2["domain_randomization"]
    assert dr["base_mode"] == LOW_CONTRAST and dr["p_base"] == 1.0
    lo_band, hi_band = dr["base_level_range"]
    lo_focus, hi_focus = dr["base_level_focus_range"]
    # the minority band is the Gazebo render itself — every scored campaign
    # still evaluates there, so level 0 must stay in distribution
    assert lo_band == 0.0
    # the majority band must contain the measured hall, with headroom above it
    assert lo_focus < MEASURED_HALL_LEVEL < hi_focus
    assert dr["p_base_focus"] > 0.5


def test_the_shipped_photometric_block_samples_as_intended(configs):
    """End-to-end through the sampler the env actually builds from this YAML."""
    _, v2 = configs
    dr = v2["domain_randomization"]
    randomizer = VisualDomainRandomizer(
        DomainRandomizationConfig(
            p_degrade=float(dr["p_degrade"]),
            level_range=tuple(dr["level_range"]),
            base_mode=dr["base_mode"],
            p_base=float(dr["p_base"]),
            base_level_range=tuple(dr["base_level_range"]),
            base_level_focus_range=tuple(dr["base_level_focus_range"]),
            p_base_focus=float(dr["p_base_focus"]),
        )
    )
    rng = np.random.default_rng(2024)
    specs = [randomizer.sample(rng) for _ in range(4000)]
    levels = np.array([s.base_level for s in specs])

    assert all(s.base_mode == LOW_CONTRAST for s in specs)
    stressed = np.mean([s.mode is not None for s in specs])
    assert 0.45 < stressed < 0.55
    # The deployment condition is now the common case, not a corner: the 19.08
    # uniform draw reached it ~25 % of the time and 285k steps of it recovered
    # only 28 % of the sim arm's lane response.
    assert np.mean(levels >= MEASURED_HALL_LEVEL) > 0.35
    # ...and the Gazebo render is still sampled often enough to stay learned.
    assert np.mean(levels <= 0.15) > 0.15


def test_the_shipped_geometric_block_samples_as_intended(configs):
    _, v2 = configs
    geom = v2["geometric_randomization"]
    randomizer = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=bool(geom["enabled"]),
            p_pose=float(geom["p_pose"]),
            pitch_delta_rad=tuple(geom["pitch_delta_rad"]),
            height_scale=tuple(geom["height_scale"]),
            p_lens=float(geom["p_lens"]),
            calibration_path=geom["calibration_path"],
        )
    )
    rng = np.random.default_rng(2024)
    specs = [randomizer.sample(rng) for _ in range(4000)]
    # The raw lens is insurance against a misconfigured rectifier, not the
    # operating point: the deployed chain is meant to rectify, and a policy
    # trained mostly on distorted frames would be the one out of distribution.
    lens_share = np.mean([s.lens for s in specs])
    assert 0.05 <= lens_share <= 0.15
    # The mount-pose term is what carries the measured +8...+30 mm residual;
    # height is the load-bearing half (ey ratio 1.105 / 0.917 at +/- 10 %).
    lo, hi = geom["height_scale"]
    assert lo <= 0.92 and hi >= 1.08


def test_geometric_calibration_path_resolves(configs):
    """p_lens > 0 with an unresolvable path would fail hours into the run."""
    _, v2 = configs
    geom = v2["geometric_randomization"]
    randomizer = GeometricDomainRandomizer(
        GeometricRandomizationConfig(
            enabled=True,
            p_lens=float(geom["p_lens"]),
            calibration_path=geom["calibration_path"],
        )
    )
    assert randomizer._calibration.exists()


def test_cage_and_reward_are_identical_to_the_trunk(configs):
    """The cage keeps joint_pair_quadratic/1.6: the 19.08 finding that
    near_secant/1.0 is cleaner applies to the RECTIFIED PHYSICAL image, not to
    the Gazebo render. Changing it here would add a fifth variable."""
    trunk, v2 = configs
    for block in ("cage", "reward", "action", "observation", "spawn_perturbation"):
        assert v2[block] == trunk[block], block
