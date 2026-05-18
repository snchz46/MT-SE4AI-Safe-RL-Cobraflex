"""
Tests for CageLogger — CSV + metadata writer for cage_node.step() results.

Coverage:
    - writes header on construction
    - add_cycle records one row per call with expected columns
    - close() writes metadata.json with run_id and cycle count
    - empty interventions → empty rules_fired field
    - multiple cycles produce multiple rows
    - timestamp formatting handles None and floats
    - context manager closes file on exit
    - end-to-end: drives SafetyCageNode and captures the stream
"""

import csv
import json
from pathlib import Path

import pytest

from cage import SafetyCageNode
from cage.logger import CAGE_STATUS_COLUMNS, CageLogger
from cage.rules import State

CAGE_YAML = Path(__file__).resolve().parent.parent / "cage.yaml"


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path / "run"


def _read_rows(out_dir):
    path = out_dir / "cage_status.csv"
    return list(csv.DictReader(path.open()))


def _minimal_result(**overrides) -> dict:
    base = {
        "safe_action": (0.0, 0.5),
        "raw_action": (0.0, 0.5),
        "interventions": [],
        "emergency": False,
        "mode": "enforcement",
        "cage_version": "0.5.0",
        "current_time": 0.0,
        "cycles_since_last_state": 0,
        "oscillation_rates_hz": {},
        "oscillation_persistent": False,
    }
    base.update(overrides)
    return base


def test_writes_header(out_dir):
    logger = CageLogger(out_dir, run_id="t1")
    logger.close()
    rows = _read_rows(out_dir)
    assert rows == []  # only header, no data
    # Header is correct
    first_line = (out_dir / "cage_status.csv").read_text().splitlines()[0]
    assert first_line == ",".join(CAGE_STATUS_COLUMNS)


def test_add_cycle_records_one_row(out_dir):
    with CageLogger(out_dir, run_id="t1") as log:
        log.add_cycle(_minimal_result(current_time=1.5))
    rows = _read_rows(out_dir)
    assert len(rows) == 1
    assert rows[0]["timestamp"] == "1.500000"
    assert rows[0]["mode"] == "enforcement"
    assert rows[0]["rules_fired"] == ""
    assert rows[0]["emergency"] == "0"


def test_records_fired_rules_as_semicolon_joined(out_dir):
    interventions = [
        {"rule": "C-06", "reason": "rate-clipped", "metadata": {}},
        {"rule": "C-04", "reason": "speed-exceeds", "metadata": {}},
    ]
    with CageLogger(out_dir) as log:
        log.add_cycle(_minimal_result(interventions=interventions))
    rows = _read_rows(out_dir)
    assert rows[0]["rules_fired"] == "C-06;C-04"


def test_emergency_flag_written_as_int(out_dir):
    with CageLogger(out_dir) as log:
        log.add_cycle(_minimal_result(emergency=True))
    rows = _read_rows(out_dir)
    assert rows[0]["emergency"] == "1"


def test_oscillation_rates_written(out_dir):
    rates = {"C-01": 12.0, "C-02": 0.0, "C-03": 3.5}
    with CageLogger(out_dir) as log:
        log.add_cycle(_minimal_result(
            oscillation_rates_hz=rates,
            oscillation_persistent=True,
        ))
    rows = _read_rows(out_dir)
    assert rows[0]["osc_rate_c01"] == "12.0"
    assert rows[0]["osc_rate_c02"] == "0.0"
    assert rows[0]["osc_rate_c03"] == "3.5"
    assert rows[0]["oscillation_persistent"] == "1"


def test_close_writes_metadata_json(out_dir):
    with CageLogger(out_dir, run_id="demo", metadata={"scenario": "oval_lap"}) as log:
        log.add_cycle(_minimal_result())
        log.add_cycle(_minimal_result(current_time=0.05))
    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["run_id"] == "demo"
    assert meta["scenario"] == "oval_lap"
    assert meta["cycles_logged"] == 2
    assert "created_utc" in meta


def test_timestamp_none_renders_as_empty_string(out_dir):
    with CageLogger(out_dir) as log:
        log.add_cycle(_minimal_result(current_time=None))
    rows = _read_rows(out_dir)
    assert rows[0]["timestamp"] == ""


def test_context_manager_close_is_idempotent(out_dir):
    log = CageLogger(out_dir)
    log.close()
    log.close()  # should not raise
    assert (out_dir / "metadata.json").exists()


def test_end_to_end_with_cage_node(out_dir):
    node = SafetyCageNode(CAGE_YAML, mode="enforcement")
    with CageLogger(out_dir, run_id="e2e") as log:
        for i in range(5):
            t = i * 0.05
            result = node.step(
                state=State(speed=0.2),
                raw_action=(0.0, 0.4),
                ctx={"current_time": t},
            )
            log.add_cycle(result)
    rows = _read_rows(out_dir)
    assert len(rows) == 5
    assert rows[0]["cage_version"] == "0.5.0"
    assert all(r["mode"] == "enforcement" for r in rows)
    meta = json.loads((out_dir / "metadata.json").read_text())
    assert meta["cycles_logged"] == 5
