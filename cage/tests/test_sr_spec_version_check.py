"""Defensive check: cage.yaml must declare a compatible_sr_spec_version."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from cage.cage_node import (
    IncompatibleCageConfigError,
    SafetyCageNode,
    _ACCEPTED_SR_SPEC_VERSIONS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GOOD_YAML = REPO_ROOT / "cage" / "cage.yaml"


def _write_minimal_yaml(tmp_path: Path, mutator) -> Path:
    """Load the real cage.yaml, mutate it, and write it to tmp_path."""
    with GOOD_YAML.open("r", encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    mutator(cfg["cage"])
    out = tmp_path / "cage.yaml"
    with out.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, sort_keys=False)
    return out


def test_real_cage_yaml_loads_ok():
    """The shipped cage.yaml must be loadable as-is."""
    node = SafetyCageNode(GOOD_YAML)
    assert node.compatible_sr_spec_version in _ACCEPTED_SR_SPEC_VERSIONS


def test_missing_field_raises(tmp_path):
    def drop_field(cage_cfg):
        cage_cfg.pop("compatible_sr_spec_version", None)

    bad = _write_minimal_yaml(tmp_path, drop_field)
    with pytest.raises(IncompatibleCageConfigError) as exc:
        SafetyCageNode(bad)
    assert "missing the 'compatible_sr_spec_version'" in str(exc.value)


def test_unknown_version_raises(tmp_path):
    def set_unknown_version(cage_cfg):
        cage_cfg["compatible_sr_spec_version"] = "99.99"

    bad = _write_minimal_yaml(tmp_path, set_unknown_version)
    with pytest.raises(IncompatibleCageConfigError) as exc:
        SafetyCageNode(bad)
    assert "'99.99'" in str(exc.value)
    assert "accepted set" in str(exc.value)


def test_accepted_set_is_non_empty():
    """Guard against an accidental empty allowlist that would make every
    YAML unloadable."""
    assert len(_ACCEPTED_SR_SPEC_VERSIONS) >= 1
