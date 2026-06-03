"""Unit tests for cobraflex_rl.training_metrics — the pure (ROS/SB3-free)
aggregation behind the extended PPO learning-curve logger (callbacks.py).

These verify the per-rollout cage-intervention tally and the CSV schema without
needing Stable-Baselines3 or ROS, so they run under the repo-root pytest on any
host (the colcon package itself is excluded from pytest via norecursedirs)."""

import sys
from pathlib import Path

# training_metrics lives in the colcon `cobraflex_rl` package, which pytest does
# not import from the repo root (src/ is in norecursedirs). The module is
# deliberately dependency-free, so import it by file path.
_PKG_DIR = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl" / "cobraflex_rl"
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

import training_metrics as tm  # noqa: E402


def test_cage_rules_and_schema():
    assert tm.CAGE_RULES == ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06")
    cols = tm.LEARNING_CURVE_COLUMNS
    # 3 timestep/episode + 6 PPO scalars + 2 aggregate cage + 6 per-rule = 17.
    assert len(cols) == 17
    assert cols[:4] == ("timestep", "ep_rew_mean", "ep_len_mean", "explained_variance")
    for scalar in ("value_loss", "entropy", "approx_kl", "clip_fraction", "std"):
        assert scalar in cols
    assert "intervention_rate" in cols and "emergency_rate" in cols
    for rule in tm.CAGE_RULES:
        assert f"int_rate_{rule}" in cols
    assert len(set(cols)) == len(cols)  # no duplicate column names


def test_entropy_sign_in_scalar_spec():
    # entropy must be stored as -train/entropy_loss (SB3 logs -mean(entropy)).
    spec = {col: (key, sign) for col, key, sign in tm.SB3_SCALAR_COLUMNS}
    assert spec["entropy"] == ("train/entropy_loss", -1.0)
    assert spec["value_loss"] == ("train/value_loss", 1.0)


def test_empty_rollout_is_all_zeros():
    rates = tm.RolloutCageStats().rates()
    assert rates["intervention_rate"] == 0.0
    assert rates["emergency_rate"] == 0.0
    for rule in tm.CAGE_RULES:
        assert rates[f"int_rate_{rule}"] == 0.0


def test_single_rule_rate():
    stats = tm.RolloutCageStats()
    stats.update({"cage_interventions": ["C-06"], "cage_emergency": False})
    for _ in range(3):
        stats.update({"cage_interventions": [], "cage_emergency": False})
    rates = stats.rates()
    assert rates["intervention_rate"] == 0.25
    assert rates["int_rate_C-06"] == 0.25
    assert rates["int_rate_C-01"] == 0.0
    assert rates["emergency_rate"] == 0.0


def test_multiple_rules_one_step():
    stats = tm.RolloutCageStats()
    stats.update({"cage_interventions": ["C-01", "C-03"]})
    stats.update({"cage_interventions": []})
    rates = stats.rates()
    # Two rules on one step → one intervened step, each per-rule = 0.5.
    assert rates["intervention_rate"] == 0.5
    assert rates["int_rate_C-01"] == 0.5
    assert rates["int_rate_C-03"] == 0.5


def test_emergency_counted():
    stats = tm.RolloutCageStats()
    stats.update({"cage_interventions": ["C-05"], "cage_emergency": True})
    stats.update({"cage_interventions": [], "cage_emergency": False})
    rates = stats.rates()
    assert rates["emergency_rate"] == 0.5
    assert rates["int_rate_C-05"] == 0.5


def test_unknown_rule_hits_aggregate_not_a_column():
    stats = tm.RolloutCageStats()
    stats.update({"cage_interventions": ["C-99"]})
    rates = stats.rates()
    assert rates["intervention_rate"] == 1.0  # aggregate still counts it
    assert stats.other_rule_steps == 1
    assert "int_rate_C-99" not in rates  # but no spurious per-rule column


def test_missing_keys_treated_as_no_activity():
    stats = tm.RolloutCageStats()
    stats.update({})  # neither cage_interventions nor cage_emergency
    rates = stats.rates()
    assert rates["intervention_rate"] == 0.0
    assert rates["emergency_rate"] == 0.0
    assert stats.total_steps == 1


def test_update_many_skips_non_mappings():
    stats = tm.RolloutCageStats()
    stats.update_many([{"cage_interventions": ["C-06"]}, None, "bad", 42])
    assert stats.total_steps == 1
    assert stats.rates()["int_rate_C-06"] == 1.0


def test_reset_clears():
    stats = tm.RolloutCageStats()
    stats.update({"cage_interventions": ["C-06"], "cage_emergency": True})
    stats.reset()
    assert stats.total_steps == 0
    assert stats.rates()["intervention_rate"] == 0.0
    assert stats.rates()["int_rate_C-06"] == 0.0
