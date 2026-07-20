"""Offline gates for the preregistered Gazebo 2-D speed-margin contract."""

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import yaml


REPO = Path(__file__).resolve().parents[2]
PKG_PARENT = REPO / "src" / "cobraflex_rl"
if str(PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(PKG_PARENT))

from cobraflex_rl.campaign_contract import (  # noqa: E402
    MODEL_CONTRACT_ATTRIBUTE,
    bind_campaign_contract,
    campaign_contract_fingerprint,
    validate_checkpoint_campaign_contract,
)


CONFIG_DIR = PKG_PARENT / "config"
HISTORICAL_ENTFIX = CONFIG_DIR / "train_sac_camera_2d_tuned_entfix.yaml"
MARGIN022 = CONFIG_DIR / "train_sac_camera_2d_tuned_entfix_margin022.yaml"
CAGE_YAML = REPO / "cage" / "cage.yaml"


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_margin022_is_a_controlled_bounded_fresh_training_delta():
    """The 0.25 evidence recipe stays intact; only preregistered knobs drift."""

    historical = _load(HISTORICAL_ENTFIX)
    candidate = _load(MARGIN022)

    assert historical["action"]["max_speed_mps"] == pytest.approx(0.25)
    assert candidate["action"]["max_speed_mps"] == pytest.approx(0.22)
    assert candidate["model_path"] != historical["model_path"]
    assert candidate["save_replay_buffer"] is True
    assert candidate["total_timesteps"] == 75_000

    normalized_candidate = deepcopy(candidate)
    normalized_candidate.pop("campaign_contract")
    normalized_candidate.pop("save_replay_buffer")
    normalized_candidate["total_timesteps"] = historical["total_timesteps"]
    normalized_candidate["action"]["max_speed_mps"] = historical["action"][
        "max_speed_mps"
    ]
    normalized_candidate["model_path"] = historical["model_path"]
    assert normalized_candidate == historical


def test_margin022_gap_is_positive_and_uses_canonical_c04_curve_floor():
    cfg = _load(MARGIN022)
    cage = _load(CAGE_YAML)
    contract = cfg["campaign_contract"]
    c04_curve_floor = cage["cage"]["c04_speed_ceiling"]["v_max_curve_mps"]

    assert contract["c04_curve_ceiling_mps"] == pytest.approx(c04_curve_floor)
    assert contract["d43_preflight_required"] is True
    assert contract["replay_buffer_required"] is True
    assert contract["bounded_training_required"] is True
    assert contract["planned_training_steps"] == 75_000
    assert contract["planned_finetune_steps"] == 50_000
    assert cfg["sac"]["buffer_size"] >= (
        contract["planned_training_steps"] + contract["planned_finetune_steps"]
    )
    assert c04_curve_floor == pytest.approx(0.25)
    actual_margin = c04_curve_floor - cfg["action"]["max_speed_mps"]
    assert actual_margin == pytest.approx(0.03)
    assert actual_margin > 0.0


def test_contract_fingerprint_binds_and_accepts_only_matching_checkpoint():
    cfg = _load(MARGIN022)
    expected = campaign_contract_fingerprint(cfg)
    fresh_model = SimpleNamespace()

    bind_campaign_contract(fresh_model, cfg, require_existing=False)
    assert getattr(fresh_model, MODEL_CONTRACT_ATTRIBUTE) == expected
    validate_checkpoint_campaign_contract(fresh_model, cfg)


def test_stall_variant_keeps_parent_fingerprint_at_finetune_horizon():
    parent = _load(MARGIN022)
    derived = deepcopy(parent)
    derived["total_timesteps"] = parent["campaign_contract"][
        "planned_finetune_steps"
    ]
    derived["protocol"] = {"arm": "stall_variant"}

    assert campaign_contract_fingerprint(derived) == campaign_contract_fingerprint(
        parent
    )


def test_sb3_checkpoint_round_trips_bound_contract(tmp_path):
    """SB3 save/load must preserve the custom fingerprint used by eval."""

    gym = pytest.importorskip("gymnasium")
    PPO = pytest.importorskip("stable_baselines3").PPO

    cfg = _load(MARGIN022)
    model = PPO(
        "MlpPolicy",
        gym.make("CartPole-v1"),
        n_steps=8,
        batch_size=8,
        verbose=0,
    )
    bind_campaign_contract(model, cfg, require_existing=False)
    checkpoint = tmp_path / "contract_roundtrip"
    model.save(checkpoint)
    model.get_env().close()

    loaded = PPO.load(checkpoint)
    validate_checkpoint_campaign_contract(loaded, cfg)


def test_contract_rejects_historical_checkpoint_without_fingerprint():
    cfg = _load(MARGIN022)
    with pytest.raises(RuntimeError, match="requires a fresh training run"):
        validate_checkpoint_campaign_contract(SimpleNamespace(), cfg)


def test_contract_rejects_zero_margin_or_declared_cap_drift():
    cfg = _load(MARGIN022)
    cfg["action"]["max_speed_mps"] = 0.25
    cfg["campaign_contract"]["max_speed_mps"] = 0.25

    with pytest.raises(ValueError, match="less than the required"):
        campaign_contract_fingerprint(cfg)


def test_contract_rejects_disabling_d43_preflight():
    cfg = _load(MARGIN022)
    cfg["campaign_contract"]["d43_preflight_required"] = False

    with pytest.raises(ValueError, match="D-43 preflight"):
        campaign_contract_fingerprint(cfg)


def test_contract_rejects_disabling_replay_buffer_evidence():
    cfg = _load(MARGIN022)
    cfg["save_replay_buffer"] = False

    with pytest.raises(ValueError, match="save_replay_buffer=true"):
        campaign_contract_fingerprint(cfg)


def test_contract_rejects_unbounded_horizon_or_short_replay():
    cfg = _load(MARGIN022)
    cfg["total_timesteps"] = 1_000_000
    with pytest.raises(ValueError, match="bounded parent horizon"):
        campaign_contract_fingerprint(cfg)

    cfg = _load(MARGIN022)
    cfg["sac"]["buffer_size"] = 100_000
    with pytest.raises(ValueError, match="does not cover"):
        campaign_contract_fingerprint(cfg)


def test_historical_config_remains_outside_the_new_guard():
    cfg = _load(HISTORICAL_ENTFIX)
    model = SimpleNamespace()
    assert campaign_contract_fingerprint(cfg) is None
    validate_checkpoint_campaign_contract(model, cfg)
    assert not hasattr(model, MODEL_CONTRACT_ATTRIBUTE)
