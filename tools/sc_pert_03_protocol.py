#!/usr/bin/env python3
"""Preregister and execute the one-shot SC-PERT-03 two-arm preparation.

The tool deliberately separates *preregistration* from *execution*:

1. ``prepare`` binds the fixed protocol to one concrete 2-D parent policy,
   writes the derived training config, hashes every input and freezes the exact
   command in ``protocol_manifest.json``.
2. ``run`` executes that frozen command at most once. It marks the attempt
   before spawning ROS/Gazebo, so a failed attempt cannot be silently retuned.
3. ``finalize`` is a recovery-only step: it verifies an already-created derived
   checkpoint and completes the manifest without launching training again.

The module is pure except for ``run``'s explicit subprocess call, making the
validation, config derivation and hash contract unit-testable without ROS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import yaml


REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = REPO / "scenarios" / "_sc_pert_03_protocol.yaml"
DEFAULT_SCENARIO = REPO / "scenarios_complex_b" / "perturbed" / "sc_pert_03.yaml"
MANIFEST_NAME = "protocol_manifest.json"
DERIVED_CONFIG_NAME = "stall_variant_train.yaml"
DERIVED_CHECKPOINT_NAME = "stall_variant.zip"


class ProtocolError(ValueError):
    """The preregistration contract is incomplete, inconsistent or mutated."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """SHA-256 of a required file; missing files are protocol errors."""
    path = Path(path)
    if not path.is_file():
        raise ProtocolError(f"required file not found: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProtocolError(f"YAML root must be a mapping: {path}")
    return data


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProtocolError(f"JSON root must be a mapping: {path}")
    return data


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _resolve_checkpoint(path: Path) -> Path:
    path = Path(path).expanduser().resolve()
    if path.is_file():
        return path
    zipped = path if path.suffix == ".zip" else path.with_suffix(".zip")
    if zipped.is_file():
        return zipped
    raise ProtocolError(f"parent checkpoint not found: {path}")


def _resolve_track_file(name: str, kind: str) -> Path:
    candidate = Path(name)
    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()
    roots = (
        [REPO / "src" / "cobraflex" / "worlds"]
        if kind == "world"
        else [REPO / "src" / "cobraflex_rl" / "config"]
    )
    for root in roots:
        candidate = root / name
        if candidate.is_file():
            return candidate.resolve()
    raise ProtocolError(f"scenario track {kind} not found: {name!r}")


def validate_contract(
    protocol: Dict[str, Any], scenario: Dict[str, Any], parent_cfg: Dict[str, Any]
) -> None:
    """Cross-check protocol, scenario and parent config before hashing anything."""
    if int(protocol.get("protocol_version", 0)) != 1:
        raise ProtocolError("unsupported protocol_version (expected 1)")
    if protocol.get("scenario_id") != "SC-PERT-03" or scenario.get("id") != "SC-PERT-03":
        raise ProtocolError("protocol and scenario must both identify SC-PERT-03")
    if protocol.get("action_contract") != "steer_throttle":
        raise ProtocolError("SC-PERT-03 executable protocol requires steer_throttle")
    if (parent_cfg.get("action") or {}).get("type") != "steer_throttle":
        raise ProtocolError("parent training config is not a 2-D steer_throttle policy")

    finetune = protocol.get("finetune") or {}
    if bool(finetune.get("adaptive_tuning", True)):
        raise ProtocolError("adaptive lambda tuning is forbidden after preregistration")
    if float(finetune.get("lambda_stall", 0.0)) <= 0.0:
        raise ProtocolError("finetune.lambda_stall must be a positive numeric value")
    if int(finetune.get("steps", 0)) <= 0:
        raise ProtocolError("finetune.steps must be positive")

    # Opted-in posterior parents additionally bind the bounded parent/fine-tune
    # replay chain. Generic historical/test configs omit this block and retain
    # the older validation surface.
    campaign_contract = parent_cfg.get("campaign_contract")
    if campaign_contract is not None:
        if not isinstance(campaign_contract, dict):
            raise ProtocolError("parent campaign_contract is not a mapping")
        if int(campaign_contract.get("planned_finetune_steps", 0)) != int(
            finetune["steps"]
        ):
            raise ProtocolError(
                "parent campaign contract fine-tune horizon differs from protocol"
            )
        if campaign_contract.get("replay_buffer_covers_parent_and_finetune") is not True:
            raise ProtocolError(
                "parent campaign contract does not cover parent + fine-tune replay"
            )

    criterion = str(protocol.get("pass_criterion_per_run", ""))
    if criterion != str(scenario.get("pass_criterion_per_run", "")):
        raise ProtocolError("scenario criterion differs from the preregistered criterion")
    if "M-P6 > 50.0" not in criterion:
        raise ProtocolError("M-P6 is 0..100; protocol must preregister the >50.0 threshold")

    perturb = scenario.get("perturbations") or {}
    if perturb.get("type") != "pre_run_policy_finetune":
        raise ProtocolError("scenario does not declare pre_run_policy_finetune")
    scenario_arms = {str(a.get("id")): a for a in perturb.get("arms", [])}
    if list(protocol.get("arms") or []) != ["released", "stall_variant"]:
        raise ProtocolError("protocol arms must be [released, stall_variant]")
    if set(scenario_arms) != {"released", "stall_variant"}:
        raise ProtocolError("scenario arms must be released and stall_variant")
    stall = scenario_arms["stall_variant"]
    if int(stall.get("finetune_steps", 0)) != int(finetune["steps"]):
        raise ProtocolError("scenario finetune_steps differs from protocol")
    if float(stall.get("lambda_stall", 0.0)) != float(finetune["lambda_stall"]):
        raise ProtocolError("scenario lambda_stall differs from protocol")
    runs = int(protocol.get("runs_per_arm_per_mode", 0))
    if runs <= 0 or any(int(a.get("runs_per_mode", 0)) != runs for a in scenario_arms.values()):
        raise ProtocolError("scenario arm run counts differ from protocol")


def derive_training_config(
    parent_cfg: Dict[str, Any], protocol: Dict[str, Any], derived_checkpoint: Path
) -> Dict[str, Any]:
    """Return the frozen continuation config; never mutate ``parent_cfg``."""
    # YAML round-trip is a compact deep copy containing only serializable config data.
    derived = yaml.safe_load(yaml.safe_dump(parent_cfg, sort_keys=False))
    finetune = protocol["finetune"]
    derived["total_timesteps"] = int(finetune["steps"])
    reward = dict(derived.get("reward") or {})
    reward["lambda_stall"] = float(finetune["lambda_stall"])
    derived["reward"] = reward
    if str(derived.get("algorithm", "ppo")).lower() == "sac":
        derived["save_replay_buffer"] = True
    derived["model_path"] = str(Path(derived_checkpoint).resolve())
    derived["protocol"] = {
        "id": "SC-PERT-03",
        "version": int(protocol["protocol_version"]),
        "arm": "stall_variant",
        "adaptive_tuning": False,
    }
    return derived


def _training_command(
    scenario: Dict[str, Any], derived_cfg: Path, parent_checkpoint: Path,
    parent_vecnormalize: Optional[Path], parent_replay_buffer: Optional[Path],
    derived_checkpoint: Path, run_id: str,
) -> list[str]:
    track = dict(scenario.get("track") or {})
    world = _resolve_track_file(str(track.get("world", "")), "world")
    centerline = _resolve_track_file(str(track.get("centerline", "")), "centerline")
    road_name = str(track.get("road_centerline", "")).strip()
    if not road_name:
        # Oval scenario library predates the explicit road-centerline field.
        road_name = "oval_centerline.yaml"
    road_centerline = _resolve_track_file(road_name, "centerline")
    world_name = str(track.get("world_name", "")).strip() or "lane_following_oval"
    command = [
        "ros2", "launch", "cobraflex_rl", "train_lane.launch.py",
        f"world:={world}",
        f"world_name:={world_name}",
        f"centerline:={centerline}",
        f"road_centerline:={road_centerline}",
        f"train_config:={derived_cfg.resolve()}",
        f"resume_from:={parent_checkpoint.resolve()}",
        f"model_path:={derived_checkpoint.resolve()}",
        f"run_id:={run_id}",
        "gui:=false",
        "shutdown_on_train_exit:=true",
    ]
    if parent_vecnormalize is not None:
        command.append(f"resume_vecnormalize:={parent_vecnormalize.resolve()}")
    if parent_replay_buffer is not None:
        command.append(f"resume_replay_buffer:={parent_replay_buffer.resolve()}")
    return command


def prepare(
    *, protocol_path: Path, scenario_path: Path, parent_checkpoint: Path,
    parent_config: Path, output_dir: Path,
    parent_vecnormalize: Optional[Path] = None,
    parent_replay_buffer: Optional[Path] = None,
) -> Path:
    """Write the immutable preregistration manifest and return its path."""
    protocol_path = Path(protocol_path).resolve()
    scenario_path = Path(scenario_path).resolve()
    parent_config = Path(parent_config).resolve()
    parent_checkpoint = _resolve_checkpoint(parent_checkpoint)
    parent_vecnormalize = (
        Path(parent_vecnormalize).resolve() if parent_vecnormalize else None
    )
    parent_replay_buffer = (
        Path(parent_replay_buffer).resolve() if parent_replay_buffer else None
    )
    protocol = _load_yaml(protocol_path)
    scenario = _load_yaml(scenario_path)
    parent_cfg = _load_yaml(parent_config)
    validate_contract(protocol, scenario, parent_cfg)
    if parent_vecnormalize is not None:
        sha256_file(parent_vecnormalize)
    if parent_replay_buffer is not None:
        sha256_file(parent_replay_buffer)
    if bool(parent_cfg.get("normalize_reward", False)) and parent_vecnormalize is None:
        raise ProtocolError(
            "parent config uses normalize_reward; --parent-vecnormalize is required "
            "so fine-tuning does not reset the reward statistics"
        )
    algorithm = str(parent_cfg.get("algorithm", "ppo")).lower()
    if algorithm == "sac" and parent_replay_buffer is None:
        raise ProtocolError(
            "SAC parent requires --parent-replay-buffer; SB3 policy .zip files "
            "do not contain replay state"
        )
    if algorithm != "sac" and parent_replay_buffer is not None:
        raise ProtocolError("--parent-replay-buffer is valid only for a SAC parent")

    protocol_hash = sha256_file(protocol_path)
    scenario_hash = sha256_file(scenario_path)
    parent_checkpoint_hash = sha256_file(parent_checkpoint)
    parent_config_hash = sha256_file(parent_config)
    parent_vecnormalize_hash = (
        sha256_file(parent_vecnormalize) if parent_vecnormalize else None
    )
    parent_replay_buffer_hash = (
        sha256_file(parent_replay_buffer) if parent_replay_buffer else None
    )

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    if manifest_path.exists():
        existing = validate_manifest(manifest_path, require_completed=False)
        requested = {
            "protocol": protocol_hash,
            "scenario": scenario_hash,
            "parent_checkpoint": parent_checkpoint_hash,
            "parent_config": parent_config_hash,
            "parent_vecnormalize": parent_vecnormalize_hash,
            "parent_replay_buffer": parent_replay_buffer_hash,
        }
        frozen = {
            "protocol": existing["protocol"]["sha256"],
            "scenario": existing["scenario"]["sha256"],
            "parent_checkpoint": existing["parent"]["checkpoint_sha256"],
            "parent_config": existing["parent"]["train_config_sha256"],
            "parent_vecnormalize": existing["parent"].get("vecnormalize_sha256"),
            "parent_replay_buffer": existing["parent"].get("replay_buffer_sha256"),
        }
        if requested != frozen:
            raise ProtocolError(
                "output directory already contains a manifest for different frozen inputs"
            )
        return manifest_path

    derived_cfg_path = output_dir / DERIVED_CONFIG_NAME
    derived_checkpoint = output_dir / DERIVED_CHECKPOINT_NAME
    if derived_cfg_path.exists() or derived_checkpoint.exists():
        raise ProtocolError(
            f"refusing to overwrite unregistered protocol output under {output_dir}"
        )
    derived_cfg = derive_training_config(parent_cfg, protocol, derived_checkpoint)
    derived_cfg_path.write_text(
        yaml.safe_dump(derived_cfg, sort_keys=False), encoding="utf-8"
    )
    seed = int(parent_cfg.get("seed", 0))
    run_id = (
        f"sc_pert_03_stall_seed{seed}_"
        f"{parent_checkpoint_hash[:12]}_{protocol_hash[:8]}"
    )
    command = _training_command(
        scenario, derived_cfg_path, parent_checkpoint, parent_vecnormalize,
        parent_replay_buffer, derived_checkpoint, run_id,
    )
    manifest: Dict[str, Any] = {
        "protocol_version": 1,
        "scenario_id": "SC-PERT-03",
        "status": "preregistered",
        "preregistered_at": _utc_now(),
        "training_attempted_at": None,
        "criterion": protocol["pass_criterion_per_run"],
        "per_arm_criterion": protocol["pass_criterion_per_arm"],
        "runs_per_arm_per_mode": int(protocol["runs_per_arm_per_mode"]),
        "modes": list(protocol["modes"]),
        "lambda_stall": float(protocol["finetune"]["lambda_stall"]),
        "finetune_steps": int(protocol["finetune"]["steps"]),
        "adaptive_tuning": False,
        "seed": seed,
        "algorithm": algorithm,
        "action_contract": "steer_throttle",
        "protocol": {"path": str(protocol_path), "sha256": protocol_hash},
        "scenario": {"path": str(scenario_path), "sha256": scenario_hash},
        "parent": {
            "checkpoint": str(parent_checkpoint),
            "checkpoint_sha256": parent_checkpoint_hash,
            "train_config": str(parent_config),
            "train_config_sha256": parent_config_hash,
            "vecnormalize": str(parent_vecnormalize) if parent_vecnormalize else None,
            "vecnormalize_sha256": parent_vecnormalize_hash,
            "replay_buffer": str(parent_replay_buffer) if parent_replay_buffer else None,
            "replay_buffer_sha256": parent_replay_buffer_hash,
        },
        "derived": {
            "checkpoint": str(derived_checkpoint),
            "checkpoint_sha256": None,
            "vecnormalize": (
                str(derived_checkpoint.with_suffix(".vecnormalize.pkl"))
                if bool(derived_cfg.get("normalize_reward", False)) else None
            ),
            "vecnormalize_sha256": None,
            "replay_buffer": (
                str(derived_checkpoint.with_suffix(".replay_buffer.pkl"))
                if algorithm == "sac" else None
            ),
            "replay_buffer_sha256": None,
            "train_config": str(derived_cfg_path),
            "train_config_sha256": sha256_file(derived_cfg_path),
            "training_run_id": run_id,
            "training_metadata": str(
                REPO / "experiments" / "sim" / "training" / run_id / "metadata.json"
            ),
            "training_metadata_sha256": None,
        },
        "command": command,
    }
    _write_json(manifest_path, manifest)
    return manifest_path


def _verify_entry(entry: Dict[str, Any], path_key: str, hash_key: str) -> None:
    path = Path(str(entry.get(path_key, "")))
    expected = str(entry.get(hash_key, ""))
    actual = sha256_file(path)
    if not expected or actual != expected:
        raise ProtocolError(f"hash mismatch for {path}: expected {expected}, got {actual}")


def validate_manifest(path: Path, *, require_completed: bool = True) -> Dict[str, Any]:
    """Validate all frozen inputs and, when requested, both policy checkpoints."""
    path = Path(path).resolve()
    data = _load_json(path)
    if data.get("scenario_id") != "SC-PERT-03" or data.get("action_contract") != "steer_throttle":
        raise ProtocolError("manifest is not an SC-PERT-03 2-D protocol")
    _verify_entry(data["protocol"], "path", "sha256")
    _verify_entry(data["scenario"], "path", "sha256")
    _verify_entry(data["parent"], "checkpoint", "checkpoint_sha256")
    _verify_entry(data["parent"], "train_config", "train_config_sha256")
    if data["parent"].get("vecnormalize"):
        _verify_entry(data["parent"], "vecnormalize", "vecnormalize_sha256")
    if data["parent"].get("replay_buffer"):
        _verify_entry(data["parent"], "replay_buffer", "replay_buffer_sha256")
    _verify_entry(data["derived"], "train_config", "train_config_sha256")
    if require_completed:
        if data.get("status") != "completed":
            raise ProtocolError(f"protocol manifest is not completed (status={data.get('status')!r})")
        _verify_entry(data["derived"], "checkpoint", "checkpoint_sha256")
        if data["derived"].get("vecnormalize"):
            _verify_entry(
                data["derived"], "vecnormalize", "vecnormalize_sha256"
            )
        if data.get("algorithm") == "sac":
            _verify_entry(data["derived"], "replay_buffer", "replay_buffer_sha256")
        _verify_entry(data["derived"], "training_metadata", "training_metadata_sha256")
    return data


def finalize(manifest_path: Path) -> Dict[str, Any]:
    """Hash the already-created derived artifacts; never launches training."""
    manifest_path = Path(manifest_path).resolve()
    data = validate_manifest(manifest_path, require_completed=False)
    checkpoint = Path(data["derived"]["checkpoint"])
    metadata = Path(data["derived"]["training_metadata"])
    data["derived"]["checkpoint_sha256"] = sha256_file(checkpoint)
    if data["derived"].get("vecnormalize"):
        data["derived"]["vecnormalize_sha256"] = sha256_file(
            Path(data["derived"]["vecnormalize"])
        )
    if data.get("algorithm") == "sac":
        data["derived"]["replay_buffer_sha256"] = sha256_file(
            Path(data["derived"]["replay_buffer"])
        )
    data["derived"]["training_metadata_sha256"] = sha256_file(metadata)
    training_meta = _load_json(metadata)
    if training_meta.get("status") != "completed":
        raise ProtocolError("derived training metadata does not report status=completed")
    if sha256_file(checkpoint) != training_meta.get("policy_checkpoint_hash"):
        raise ProtocolError("derived checkpoint hash disagrees with training metadata")
    if data["derived"].get("vecnormalize") and (
        data["derived"]["vecnormalize_sha256"]
        != training_meta.get("policy_vecnormalize_hash")
    ):
        raise ProtocolError("derived VecNormalize hash disagrees with training metadata")
    if data.get("algorithm") == "sac" and (
        data["derived"]["replay_buffer_sha256"]
        != training_meta.get("policy_replay_buffer_hash")
    ):
        raise ProtocolError("derived replay-buffer hash disagrees with training metadata")
    data["status"] = "completed"
    data["completed_at"] = _utc_now()
    _write_json(manifest_path, data)
    return validate_manifest(manifest_path, require_completed=True)


def run_once(manifest_path: Path) -> Dict[str, Any]:
    """Execute the frozen fine-tune exactly once, then finalize its hashes."""
    manifest_path = Path(manifest_path).resolve()
    data = validate_manifest(manifest_path, require_completed=False)
    if data.get("status") == "completed":
        return validate_manifest(manifest_path, require_completed=True)
    if data.get("training_attempted_at") is not None:
        raise ProtocolError(
            "the preregistered fine-tune was already attempted; do not rerun or retune. "
            "Use finalize only if that attempt produced complete artifacts."
        )
    data["status"] = "training"
    data["training_attempted_at"] = _utc_now()
    _write_json(manifest_path, data)
    completed = subprocess.run(list(data["command"]), check=False)
    if completed.returncode != 0:
        data = _load_json(manifest_path)
        data["status"] = "training_failed"
        data["training_returncode"] = completed.returncode
        _write_json(manifest_path, data)
        raise ProtocolError(
            f"one-shot fine-tune failed with return code {completed.returncode}; "
            "the tool will not retry it automatically"
        )
    return finalize(manifest_path)


def model_paths_by_arm(manifest: Dict[str, Any]) -> Dict[str, Path]:
    """Policy mapping consumed by the campaign runner after validation."""
    return {
        "released": Path(manifest["parent"]["checkpoint"]),
        "stall_variant": Path(manifest["derived"]["checkpoint"]),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command_name", required=True)
    prep = sub.add_parser("prepare", help="freeze inputs/config/command; do not run Gazebo")
    prep.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    prep.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    prep.add_argument("--parent-checkpoint", type=Path, required=True)
    prep.add_argument("--parent-config", type=Path, required=True)
    prep.add_argument("--parent-vecnormalize", type=Path)
    prep.add_argument("--parent-replay-buffer", type=Path)
    prep.add_argument("--out", type=Path, required=True)
    for name in ("run", "finalize", "validate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command_name == "prepare":
            path = prepare(
                protocol_path=args.protocol, scenario_path=args.scenario,
                parent_checkpoint=args.parent_checkpoint,
                parent_config=args.parent_config, output_dir=args.out,
                parent_vecnormalize=args.parent_vecnormalize,
                parent_replay_buffer=args.parent_replay_buffer,
            )
            data = validate_manifest(path, require_completed=False)
            print(f"Preregistered: {path}")
            print("Frozen command:")
            print("  " + " ".join(str(x) for x in data["command"]))
        elif args.command_name == "run":
            run_once(args.manifest)
            print(f"Completed one-shot fine-tune: {args.manifest}")
        elif args.command_name == "finalize":
            finalize(args.manifest)
            print(f"Finalized existing artifacts: {args.manifest}")
        else:
            validate_manifest(args.manifest, require_completed=True)
            print(f"Valid completed manifest: {args.manifest}")
    except ProtocolError as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
