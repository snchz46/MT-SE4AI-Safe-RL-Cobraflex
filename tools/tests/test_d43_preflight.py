"""Pure-Python tests for the D-43 offline preflight gate."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "tools" / "d43_preflight.py"
SPEC = importlib.util.spec_from_file_location("d43_preflight", MODULE_PATH)
assert SPEC and SPEC.loader
d43 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = d43
SPEC.loader.exec_module(d43)


FIELDS = [
    "episode",
    "step",
    "s",
    "ey",
    "epsi",
    "interventions",
    "emergency",
    "cv_ok",
    "cv_state_available",
    "cv_perception_invalid",
    "cv_ey",
    "cv_epsi",
]


def _row(**overrides):
    row = {
        "episode": 0,
        "step": 1,
        "s": 1.0,
        "ey": 0.01,
        "epsi": 0.02,
        "interventions": "",
        "emergency": 0,
        "cv_ok": 1,
        "cv_state_available": 1,
        "cv_perception_invalid": 0,
        "cv_ey": 0.012,
        "cv_epsi": 0.025,
    }
    row.update(overrides)
    return row


def _write(path: Path, rows, fields=FIELDS, metadata_overrides=None):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "run_id": path.parent.name,
        "scenario_id": "SC-NOM-01",
        "mode": "enforcement",
        "status": "completed",
        "policy_checkpoint": "policy/checkpoints/test_2d.zip",
        "policy_checkpoint_hash": "a" * 64,
        "train_config": "test_config.yaml",
        "train_config_hash": "b" * 64,
        "scenario_yaml": "scenarios/nominal/sc_nom_01.yaml",
        "scenario_yaml_hash": "c" * 64,
        "cage_yaml_hash": "d" * 64,
        "git_commit": "e" * 40,
        "seed": 2024,
    }
    metadata.update(metadata_overrides or {})
    (path.parent / "metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )


def _criteria(**overrides):
    values = {"min_centered_samples": 1}
    values.update(overrides)
    return d43.Criteria(**values)


def test_clean_centred_trace_passes(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row()])

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "PASS"
    assert report["totals"]["centered_rows"] == 1
    assert all(check["status"] == "PASS" for check in report["checks"])


def test_heading_overread_in_centred_vehicle_blocks(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row(cv_epsi=-0.45, interventions="C-02")])

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "BLOCKED"
    totals = report["totals"]
    assert totals["centered_epsi_error_steps"] == 1
    assert totals["centered_heading_envelope_conflict_steps"] == 1
    assert totals["centered_false_rule_steps"] == 1


def test_ge2_clean_heading_error_below_point40_passes(tmp_path):
    path = tmp_path / "cage_status.csv"
    # 0.38 rad disagreement is below the 0.40 rad GE2-anchored gate and the
    # estimate itself remains below C-02's 0.4363 rad envelope.
    _write(path, [_row(epsi=0.0, cv_epsi=0.38)])

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "PASS"
    assert report["totals"]["centered_epsi_error_steps"] == 0


def test_direct_heading_envelope_crossing_blocks_even_below_error_tolerance(tmp_path):
    path = tmp_path / "cage_status.csv"
    # Difference is only 0.34 rad, but the CV estimate itself exceeds C-02.
    _write(path, [_row(epsi=0.10, cv_epsi=0.44)])

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "BLOCKED"
    assert report["totals"]["centered_epsi_error_steps"] == 0
    assert report["totals"]["centered_heading_envelope_conflict_steps"] == 1


def test_lateral_underread_is_characterised_but_not_a_centred_blocker(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row(ey=0.14, epsi=0.02, cv_ey=0.04, cv_epsi=0.03)])

    report = d43.build_report([path], _criteria(min_centered_samples=0))

    assert report["verdict"] == "PASS"
    assert report["totals"]["lateral_underread_steps"] == 1
    assert report["maxima"]["underread_abs_gap_m"] == 0.1


def test_unattributed_centred_emergency_blocks_conservatively(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row(interventions="C-04;C-05", emergency=1)])

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "BLOCKED"
    assert report["totals"]["centered_emergency_steps"] == 1
    assert report["totals"]["centered_unattributed_emergency_steps"] == 1


def test_missing_cv_schema_is_invalid(tmp_path):
    path = tmp_path / "cage_status.csv"
    fields = [field for field in FIELDS if field != "cv_epsi"]
    _write(path, [{key: value for key, value in _row().items() if key in fields}], fields)

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "INVALID"
    assert report["inputs"][0]["missing_columns"] == ["cv_epsi"]


def test_missing_sibling_metadata_is_invalid(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row()])
    (tmp_path / "metadata.json").unlink()

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "INVALID"
    assert report["inputs"][0]["provenance"]["valid"] is False
    assert "sibling metadata.json is missing" in report["inputs"][0]["invalid_reasons"]


def test_incomplete_eval_status_is_invalid(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row()], metadata_overrides={"status": "interrupted"})

    report = d43.build_report([path], _criteria())

    assert report["verdict"] == "INVALID"
    errors = report["inputs"][0]["provenance"]["errors"]
    assert any("expected 'completed'" in error for error in errors)


def test_report_binds_csv_eval_metadata_checkpoint_and_train_config(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row()])

    report = d43.build_report([path], _criteria())
    item = report["inputs"][0]

    assert item["verdict"] == "PASS"
    assert len(item["sha256"]) == 64
    assert len(item["provenance"]["metadata_sha256"]) == 64
    assert item["provenance"]["policy_checkpoint_hash"] == "a" * 64
    assert item["provenance"]["train_config_hash"] == "b" * 64
    assert item["provenance"]["scenario_id"] == "SC-NOM-01"
    assert item["provenance"]["mode"] == "enforcement"


def test_insufficient_centred_coverage_is_invalid(tmp_path):
    path = tmp_path / "cage_status.csv"
    _write(path, [_row(ey=0.081)])

    report = d43.build_report([path], _criteria(min_centered_samples=1))

    assert report["verdict"] == "INVALID"
    assert "centred coverage short" in report["invalid_reasons"][0]


def test_angle_error_wraps_at_pi_boundary():
    assert abs(d43._angle_error(-3.13, 3.13)) < 0.03


def test_cli_returns_blocking_exit_code_and_writes_report(tmp_path, capsys):
    trace = tmp_path / "cage_status.csv"
    output = tmp_path / "preflight.json"
    _write(trace, [_row(cv_epsi=-0.45, interventions="C-02")])

    exit_code = d43.main(
        [str(trace), "--output", str(output), "--min-centered-samples", "1"]
    )

    assert exit_code == 2
    assert '"verdict": "BLOCKED"' in output.read_text(encoding="utf-8")
    assert '"verdict": "BLOCKED"' in capsys.readouterr().out
