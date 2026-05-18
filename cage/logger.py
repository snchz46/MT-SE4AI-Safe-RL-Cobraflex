"""
CageLogger — synchronous CSV writer for cage_node.step() results.

Phase status: F2 first cut. Synchronous, one writer per run, single file
`cage_status.csv` plus a `metadata.json` for run identification. The
asynchronous design with a thread-safe queue per topic envisaged in the
Phase 2 plan §3.4 will land in a later increment when integrated with
the ROS2 wrapper and the multi-topic publishing pipeline. For now this
class is sufficient to capture the per-cycle decision stream produced
by `SafetyCageNode.step()` in pure Python tests and offline replay.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CAGE_STATUS_COLUMNS = [
    "timestamp",
    "mode",
    "cage_version",
    "raw_steering",
    "raw_throttle",
    "safe_steering",
    "safe_throttle",
    "emergency",
    "rules_fired",
    "cycles_since_last_state",
    "oscillation_persistent",
    "osc_rate_c01",
    "osc_rate_c02",
    "osc_rate_c03",
]


class CageLogger:
    """
    Append cage_node step() result dicts to a CSV file. Optional context
    dict (`metadata`) is dumped to `metadata.json` on close.

    Usage:
        with CageLogger(output_dir, run_id="demo_gate2") as log:
            for _ in range(N):
                result = node.step(state, raw_action, ctx)
                log.add_cycle(result)
    """

    def __init__(
        self,
        output_dir,
        run_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._metadata = dict(metadata or {})
        self._metadata.setdefault("run_id", self.run_id)
        self._metadata.setdefault("created_utc", datetime.now(timezone.utc).isoformat())

        self.cage_status_path = self.output_dir / "cage_status.csv"
        self.metadata_path = self.output_dir / "metadata.json"

        self._file = self.cage_status_path.open("w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=CAGE_STATUS_COLUMNS)
        self._writer.writeheader()
        self._cycle_count = 0
        self._closed = False

    def add_cycle(self, result: dict) -> None:
        rules_fired = ";".join(iv["rule"] for iv in result.get("interventions", []))
        rates = result.get("oscillation_rates_hz") or {}
        raw_s, raw_t = result["raw_action"]
        safe_s, safe_t = result["safe_action"]
        row = {
            "timestamp": _format_timestamp(result.get("current_time")),
            "mode": result.get("mode", ""),
            "cage_version": result.get("cage_version", ""),
            "raw_steering": raw_s,
            "raw_throttle": raw_t,
            "safe_steering": safe_s,
            "safe_throttle": safe_t,
            "emergency": int(bool(result.get("emergency", False))),
            "rules_fired": rules_fired,
            "cycles_since_last_state": result.get("cycles_since_last_state", 0),
            "oscillation_persistent": int(bool(result.get("oscillation_persistent", False))),
            "osc_rate_c01": rates.get("C-01", 0.0),
            "osc_rate_c02": rates.get("C-02", 0.0),
            "osc_rate_c03": rates.get("C-03", 0.0),
        }
        self._writer.writerow(row)
        self._cycle_count += 1

    def close(self) -> None:
        if self._closed:
            return
        self._file.close()
        self._metadata["cycles_logged"] = self._cycle_count
        with self.metadata_path.open("w") as f:
            json.dump(self._metadata, f, indent=2)
        self._closed = True

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def __enter__(self) -> "CageLogger":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def _format_timestamp(value) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"
