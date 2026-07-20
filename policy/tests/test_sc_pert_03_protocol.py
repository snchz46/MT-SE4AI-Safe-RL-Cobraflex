"""Pure tests for the preregistered SC-PERT-03 two-arm preparation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml


TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import sc_pert_03_protocol as sp  # noqa: E402


REPO = Path(__file__).resolve().parents[2]
PROTOCOL = REPO / "scenarios" / "_sc_pert_03_protocol.yaml"
SCENARIO = REPO / "scenarios_complex_b" / "perturbed" / "sc_pert_03.yaml"
MARGIN022 = (
    REPO
    / "src"
    / "cobraflex_rl"
    / "config"
    / "train_sac_camera_2d_tuned_entfix_margin022.yaml"
)


def _parent_cfg(
    *, normalize_reward=False, action_type="steer_throttle", algorithm="ppo"
):
    return {
        "algorithm": algorithm,
        "seed": 2024,
        "total_timesteps": 1_000_000,
        "normalize_reward": normalize_reward,
        "action": {"type": action_type},
        "reward": {
            "forward_progress": 1.0,
            "lateral_error": 1.0,
            "heading_error": 0.5,
            "steer_delta": 0.2,
            "throttle_delta": 0.1,
            "stall_penalty": 0.5,
            "stall_progress_min": 0.25,
            "termination": 10.0,
        },
    }


def _inputs(tmp_path, **cfg_kw):
    checkpoint = tmp_path / "parent.zip"
    checkpoint.write_bytes(b"parent-policy")
    config = tmp_path / "parent.yaml"
    config.write_text(yaml.safe_dump(_parent_cfg(**cfg_kw)), encoding="utf-8")
    return checkpoint, config


def test_real_protocol_and_both_scenario_copies_are_consistent():
    protocol = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["finetune"]["lambda_stall"] == 4.0
    assert "M-P6 > 50.0" in protocol["pass_criterion_per_run"]
    for scenario_path in (
        REPO / "scenarios" / "perturbed" / "sc_pert_03.yaml",
        SCENARIO,
    ):
        scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        sp.validate_contract(protocol, scenario, _parent_cfg())

    margin_parent = yaml.safe_load(MARGIN022.read_text(encoding="utf-8"))
    sp.validate_contract(
        protocol,
        yaml.safe_load(SCENARIO.read_text(encoding="utf-8")),
        margin_parent,
    )


def test_margin022_prepare_produces_contract_compatible_finetune(tmp_path):
    pkg_parent = REPO / "src" / "cobraflex_rl"
    if str(pkg_parent) not in sys.path:
        sys.path.insert(0, str(pkg_parent))
    from cobraflex_rl.campaign_contract import campaign_contract_fingerprint

    checkpoint = tmp_path / "fresh_margin022.zip"
    vecnormalize = tmp_path / "fresh_margin022.vecnormalize.pkl"
    replay = tmp_path / "fresh_margin022.replay_buffer.pkl"
    checkpoint.write_bytes(b"fresh-policy")
    vecnormalize.write_bytes(b"fresh-vec")
    replay.write_bytes(b"fresh-replay")
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL,
        scenario_path=SCENARIO,
        parent_checkpoint=checkpoint,
        parent_config=MARGIN022,
        parent_vecnormalize=vecnormalize,
        parent_replay_buffer=replay,
        output_dir=tmp_path / "protocol",
    )
    manifest = sp.validate_manifest(manifest_path, require_completed=False)
    parent_cfg = yaml.safe_load(MARGIN022.read_text(encoding="utf-8"))
    derived_cfg = yaml.safe_load(
        Path(manifest["derived"]["train_config"]).read_text(encoding="utf-8")
    )
    assert derived_cfg["total_timesteps"] == 50_000
    assert campaign_contract_fingerprint(derived_cfg) == (
        campaign_contract_fingerprint(parent_cfg)
    )


def test_prepare_freezes_hashes_and_derives_reward_config(tmp_path):
    checkpoint, config = _inputs(tmp_path)
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL,
        scenario_path=SCENARIO,
        parent_checkpoint=checkpoint,
        parent_config=config,
        output_dir=tmp_path / "protocol_run",
    )
    manifest = sp.validate_manifest(manifest_path, require_completed=False)
    derived = yaml.safe_load(
        Path(manifest["derived"]["train_config"]).read_text(encoding="utf-8")
    )
    assert manifest["status"] == "preregistered"
    assert manifest["lambda_stall"] == 4.0
    assert manifest["finetune_steps"] == 50_000
    assert derived["total_timesteps"] == 50_000
    assert derived["reward"]["lambda_stall"] == 4.0
    assert derived["protocol"]["adaptive_tuning"] is False
    assert sp.sha256_file(checkpoint)[:12] in manifest["derived"]["training_run_id"]
    assert "--resume-from" not in manifest["command"]  # launch syntax is key:=value
    assert any(str(checkpoint.resolve()) in arg for arg in manifest["command"])


def test_prepare_requires_2d_parent(tmp_path):
    checkpoint, config = _inputs(tmp_path, action_type="steer")
    with pytest.raises(sp.ProtocolError, match="2-D"):
        sp.prepare(
            protocol_path=PROTOCOL, scenario_path=SCENARIO,
            parent_checkpoint=checkpoint, parent_config=config,
            output_dir=tmp_path / "out",
        )


def test_prepare_requires_vecnormalize_state_for_normalized_parent(tmp_path):
    checkpoint, config = _inputs(tmp_path, normalize_reward=True)
    with pytest.raises(sp.ProtocolError, match="parent-vecnormalize"):
        sp.prepare(
            protocol_path=PROTOCOL, scenario_path=SCENARIO,
            parent_checkpoint=checkpoint, parent_config=config,
            output_dir=tmp_path / "out",
        )
    vecnormalize = tmp_path / "parent_vecnormalize.pkl"
    vecnormalize.write_bytes(b"vecnormalize-state")
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        parent_vecnormalize=vecnormalize, output_dir=tmp_path / "ready",
    )
    manifest = sp.validate_manifest(manifest_path, require_completed=False)
    assert manifest["parent"]["vecnormalize_sha256"] == sp.sha256_file(
        vecnormalize
    )
    assert manifest["derived"]["vecnormalize"].endswith(".vecnormalize.pkl")
    assert any("resume_vecnormalize:=" in arg for arg in manifest["command"])


def test_prepare_requires_and_hashes_sac_replay_buffer(tmp_path):
    checkpoint, config = _inputs(tmp_path, algorithm="sac")
    with pytest.raises(sp.ProtocolError, match="parent-replay-buffer"):
        sp.prepare(
            protocol_path=PROTOCOL, scenario_path=SCENARIO,
            parent_checkpoint=checkpoint, parent_config=config,
            output_dir=tmp_path / "missing",
        )
    replay = tmp_path / "parent_replay.pkl"
    replay.write_bytes(b"replay-state")
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        parent_replay_buffer=replay, output_dir=tmp_path / "ready",
    )
    manifest = sp.validate_manifest(manifest_path, require_completed=False)
    assert manifest["parent"]["replay_buffer_sha256"] == sp.sha256_file(replay)
    derived_cfg = yaml.safe_load(
        Path(manifest["derived"]["train_config"]).read_text(encoding="utf-8")
    )
    assert derived_cfg["save_replay_buffer"] is True
    assert any("resume_replay_buffer:=" in arg for arg in manifest["command"])


def test_manifest_detects_mutated_parent_checkpoint(tmp_path):
    checkpoint, config = _inputs(tmp_path)
    manifest = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        output_dir=tmp_path / "out",
    )
    checkpoint.write_bytes(b"mutated")
    with pytest.raises(sp.ProtocolError, match="hash mismatch"):
        sp.validate_manifest(manifest, require_completed=False)


def test_prepare_refuses_reusing_output_dir_for_a_different_parent(tmp_path):
    checkpoint, config = _inputs(tmp_path)
    out = tmp_path / "out"
    sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config, output_dir=out,
    )
    other_checkpoint = tmp_path / "other_parent.zip"
    other_checkpoint.write_bytes(b"different-parent")
    with pytest.raises(sp.ProtocolError, match="different frozen inputs"):
        sp.prepare(
            protocol_path=PROTOCOL, scenario_path=SCENARIO,
            parent_checkpoint=other_checkpoint, parent_config=config, output_dir=out,
        )


def test_finalize_records_derived_checkpoint_and_training_metadata(tmp_path):
    checkpoint, config = _inputs(tmp_path)
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        output_dir=tmp_path / "out",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    derived_checkpoint = Path(manifest["derived"]["checkpoint"])
    derived_checkpoint.write_bytes(b"derived-policy")
    metadata = tmp_path / "training_metadata.json"
    metadata.write_text(json.dumps({
        "status": "completed",
        "policy_checkpoint_hash": sp.sha256_file(derived_checkpoint),
    }), encoding="utf-8")
    manifest["derived"]["training_metadata"] = str(metadata)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    completed = sp.finalize(manifest_path)
    assert completed["status"] == "completed"
    assert completed["derived"]["checkpoint_sha256"] == sp.sha256_file(
        derived_checkpoint
    )
    assert sp.model_paths_by_arm(completed) == {
        "released": checkpoint,
        "stall_variant": derived_checkpoint,
    }


def test_finalize_hashes_normalized_sac_state(tmp_path):
    checkpoint, config = _inputs(
        tmp_path, normalize_reward=True, algorithm="sac"
    )
    parent_vec = tmp_path / "parent.vecnormalize.pkl"
    parent_replay = tmp_path / "parent.replay_buffer.pkl"
    parent_vec.write_bytes(b"parent-vec")
    parent_replay.write_bytes(b"parent-replay")
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        parent_vecnormalize=parent_vec, parent_replay_buffer=parent_replay,
        output_dir=tmp_path / "out",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    derived_checkpoint = Path(manifest["derived"]["checkpoint"])
    derived_vec = Path(manifest["derived"]["vecnormalize"])
    derived_replay = Path(manifest["derived"]["replay_buffer"])
    derived_checkpoint.write_bytes(b"derived-policy")
    derived_vec.write_bytes(b"derived-vec")
    derived_replay.write_bytes(b"derived-replay")
    metadata = tmp_path / "training_metadata.json"
    metadata.write_text(json.dumps({
        "status": "completed",
        "policy_checkpoint_hash": sp.sha256_file(derived_checkpoint),
        "policy_vecnormalize_hash": sp.sha256_file(derived_vec),
        "policy_replay_buffer_hash": sp.sha256_file(derived_replay),
    }), encoding="utf-8")
    manifest["derived"]["training_metadata"] = str(metadata)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    completed = sp.finalize(manifest_path)
    assert completed["derived"]["vecnormalize_sha256"] == sp.sha256_file(
        derived_vec
    )
    assert completed["derived"]["replay_buffer_sha256"] == sp.sha256_file(
        derived_replay
    )


def test_failed_one_shot_is_not_retried(tmp_path, monkeypatch):
    checkpoint, config = _inputs(tmp_path)
    manifest_path = sp.prepare(
        protocol_path=PROTOCOL, scenario_path=SCENARIO,
        parent_checkpoint=checkpoint, parent_config=config,
        output_dir=tmp_path / "out",
    )

    class Result:
        returncode = 7

    calls = []
    monkeypatch.setattr(sp.subprocess, "run", lambda command, check: calls.append(command) or Result())
    with pytest.raises(sp.ProtocolError, match="return code 7"):
        sp.run_once(manifest_path)
    with pytest.raises(sp.ProtocolError, match="already attempted"):
        sp.run_once(manifest_path)
    assert len(calls) == 1
