#!/usr/bin/env python3
"""Offline D-43 preflight for camera-policy ``cage_status.csv`` traces.

The track-E cage acts on a deterministic CV estimate while Gazebo ground truth
is retained as an evaluation oracle.  This tool compares both streams without
ROS, Gazebo, NumPy, or the estimator implementation.  It is intended to run on
nominal evaluation traces before authorising a posterior 2-D campaign.

The default gate is deliberately fail-closed.  It blocks when a ground-truth
centred vehicle has a material CV-state disagreement, a CV-dependent safety
rule fires, perception is declared invalid, or an emergency is reported.  It
also characterises the separate D-43 lateral under-read residual when ground
truth is outside the C-05 warning band but CV remains inside it.  That residual
is reported, not used as a default gate condition, because it is not a
``centred vehicle`` false-trigger condition.

Exit codes:
    0  PASS
    1  INVALID input/schema/coverage
    2  BLOCKED by one or more preflight criteria
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "d43-preflight/v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
TRAINING_ROOT = REPO_ROOT / "experiments" / "sim" / "training"
CV_SAFETY_RULES = frozenset({"C-01", "C-02", "C-03"})
REQUIRED_COLUMNS = frozenset(
    {
        "ey",
        "epsi",
        "interventions",
        "emergency",
        "cv_ok",
        "cv_state_available",
        "cv_perception_invalid",
        "cv_ey",
        "cv_epsi",
    }
)


@dataclass(frozen=True)
class Criteria:
    """Explicit preflight limits (engineering gates, not new SR thresholds)."""

    # Ground-truth window in which the vehicle is treated as centred.
    # 0.08 m is half of C-01's 0.16 m lateral envelope: a near-centre band
    # that still includes the observed cap-0.22 false stop at |ey|=0.0755 m.
    center_ey_max_m: float = 0.08
    center_epsi_max_rad: float = 0.10

    # Maximum CV-vs-oracle disagreement allowed inside the centred window.
    centered_ey_error_max_m: float = 0.05
    # Final clean GE2 oracle sweep max |epsi error| was 0.38734 rad
    # (cv_estimator_val_20260610T181634Z). 0.40 admits that established clean
    # baseline but retains 0.0363 rad before C-02's 0.4363 rad hard limit.
    centered_epsi_error_max_rad: float = 0.40

    # Canonical cage envelope values, used for direct-conflict diagnostics.
    lane_limit_m: float = 0.16
    heading_limit_rad: float = 0.4363
    lane_warning_m: float = 0.12

    # D-43 under-read characterisation: truth outside warning, CV inside it,
    # with at least this much absolute-magnitude disagreement.
    underread_min_gap_m: float = 0.05

    # Coverage and allowed blocker counts.  Defaults require a clean trace.
    min_centered_samples: int = 100
    max_centered_ey_error_steps: int = 0
    max_centered_epsi_error_steps: int = 0
    max_centered_lane_envelope_conflict_steps: int = 0
    max_centered_heading_envelope_conflict_steps: int = 0
    max_centered_false_rule_steps: int = 0
    max_centered_perception_invalid_steps: int = 0
    max_centered_emergency_steps: int = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    """Prefer a cwd-relative POSIX path in portable JSON evidence."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


@lru_cache(maxsize=1)
def _training_metadata_index() -> tuple[dict[str, Any], ...]:
    """Read archived training records once for legacy eval provenance lookup."""

    records = []
    if not TRAINING_ROOT.is_dir():
        return ()
    for path in sorted(TRAINING_ROOT.glob("*/metadata.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        run_id = str(data.get("run_id") or path.parent.name)
        records.append(
            {
                "path": path,
                "sha256": _sha256(path),
                "run_id": run_id,
                "directory_name": path.parent.name,
                "data": data,
            }
        )
    return tuple(records)


def _resolve_training_record(policy_checkpoint: str) -> tuple[dict[str, Any] | None, str]:
    """Resolve legacy eval metadata to its archived training run by path/name."""

    normalised = policy_checkpoint.replace("\\", "/")
    stem = Path(normalised).stem
    path_parts = {part for part in normalised.split("/") if part}
    candidates: list[tuple[int, int, dict[str, Any]]] = []
    for record in _training_metadata_index():
        aliases = {record["run_id"], record["directory_name"]}
        score = 0
        matched_len = 0
        for alias in aliases:
            if not alias:
                continue
            alias_score = 3 if alias in path_parts else 2 if stem.startswith(alias) else 0
            if alias_score > score or (alias_score == score and len(alias) > matched_len):
                score = alias_score
                matched_len = len(alias)
        if score:
            candidates.append((score, matched_len, record))
    if not candidates:
        return None, "no archived training metadata matches policy_checkpoint"
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score = candidates[0][:2]
    best = [record for score, length, record in candidates if (score, length) == best_score]
    if len(best) != 1:
        names = ", ".join(record["run_id"] for record in best)
        return None, f"ambiguous archived training metadata match: {names}"
    return best[0], "matched archived training metadata by checkpoint path/name"


def _load_provenance(csv_path: Path) -> dict[str, Any]:
    """Bind one CSV to sibling eval metadata and its training-config hash."""

    metadata_path = csv_path.parent / "metadata.json"
    result: dict[str, Any] = {
        "valid": False,
        "errors": [],
        "metadata_path": _display_path(metadata_path),
        "metadata_sha256": None,
    }
    if not metadata_path.is_file():
        result["errors"].append("sibling metadata.json is missing")
        return result
    result["metadata_sha256"] = _sha256(metadata_path)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"metadata.json cannot be parsed: {exc}")
        return result
    if not isinstance(metadata, dict):
        result["errors"].append("metadata.json root is not an object")
        return result

    copied_fields = (
        "run_id",
        "scenario_id",
        "mode",
        "status",
        "policy_checkpoint",
        "policy_checkpoint_hash",
        "scenario_yaml",
        "scenario_yaml_hash",
        "cage_yaml_hash",
        "git_commit",
        "seed",
    )
    for key in copied_fields:
        result[key] = metadata.get(key)

    required = ("run_id", "scenario_id", "mode", "status", "policy_checkpoint_hash")
    for key in required:
        if metadata.get(key) in (None, ""):
            result["errors"].append(f"metadata field {key!r} is missing")
    if metadata.get("run_id") and metadata["run_id"] != csv_path.parent.name:
        result["errors"].append(
            f"metadata run_id {metadata['run_id']!r} does not match directory "
            f"{csv_path.parent.name!r}"
        )
    if metadata.get("mode") not in {"enforcement", "monitoring"}:
        result["errors"].append("metadata mode is not enforcement or monitoring")
    if metadata.get("status") != "completed":
        result["errors"].append(
            f"metadata status is {metadata.get('status')!r}, expected 'completed'"
        )
    if not _valid_sha256(metadata.get("policy_checkpoint_hash")):
        result["errors"].append("policy_checkpoint_hash is not a SHA-256 digest")
    scenario_hash = metadata.get("scenario_yaml_hash")
    if scenario_hash not in (None, "") and not _valid_sha256(scenario_hash):
        result["errors"].append("scenario_yaml_hash is not a SHA-256 digest")

    direct_config_hash = metadata.get("train_config_hash")
    result["train_config"] = metadata.get("train_config")
    result["train_config_hash"] = direct_config_hash
    result["train_config_source"] = None
    result["training_metadata_path"] = None
    result["training_metadata_sha256"] = None
    result["training_run_id"] = None
    if direct_config_hash not in (None, ""):
        result["train_config_source"] = "eval_metadata"
    else:
        policy_checkpoint = str(metadata.get("policy_checkpoint") or "")
        training_record, resolution = _resolve_training_record(policy_checkpoint)
        result["training_resolution"] = resolution
        if training_record is None:
            result["errors"].append(resolution)
        else:
            training = training_record["data"]
            result["training_metadata_path"] = _display_path(training_record["path"])
            result["training_metadata_sha256"] = training_record["sha256"]
            result["training_run_id"] = training_record["run_id"]
            result["train_config"] = training.get("train_config")
            result["train_config_hash"] = training.get("train_config_hash")
            result["train_config_source"] = "archived_training_metadata"
            training_checkpoint_hash = training.get("policy_checkpoint_hash")
            if (
                training_checkpoint_hash not in (None, "")
                and training_checkpoint_hash != metadata.get("policy_checkpoint_hash")
            ):
                result["errors"].append(
                    "policy_checkpoint_hash disagrees with archived training metadata"
                )
            training_cage_hash = training.get("cage_yaml_hash")
            if (
                training_cage_hash not in (None, "")
                and metadata.get("cage_yaml_hash") not in (None, "")
                and training_cage_hash != metadata.get("cage_yaml_hash")
            ):
                result["errors"].append(
                    "cage_yaml_hash disagrees with archived training metadata"
                )
    if not _valid_sha256(result.get("train_config_hash")):
        result["errors"].append(
            "train_config_hash is unavailable or is not a SHA-256 digest"
        )

    result["valid"] = not result["errors"]
    return result


def _as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{key} is not finite: {value!r}")
    return number


def _as_bool(row: dict[str, str], key: str) -> bool:
    value = row.get(key, "").strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no", ""}:
        return False
    raise ValueError(f"{key} is not boolean: {row.get(key)!r}")


def _rules(value: str) -> set[str]:
    return {item.strip() for item in value.split(";") if item.strip()}


def _angle_error(a: float, b: float) -> float:
    """Smallest signed angular difference ``a - b`` in [-pi, pi]."""

    return (a - b + math.pi) % (2.0 * math.pi) - math.pi


def _context(
    source: Path,
    row_number: int,
    row: dict[str, str],
    ey: float,
    epsi: float,
    cv_ey: float,
    cv_epsi: float,
    rules: set[str],
) -> dict[str, Any]:
    """Compact evidence row retained in report hotspot lists."""

    result: dict[str, Any] = {
        "source": _display_path(source),
        "csv_row": row_number,
        "ey_m": round(ey, 6),
        "epsi_rad": round(epsi, 6),
        "cv_ey_m": round(cv_ey, 6),
        "cv_epsi_rad": round(cv_epsi, 6),
        "ey_error_m": round(cv_ey - ey, 6),
        "epsi_error_rad": round(_angle_error(cv_epsi, epsi), 6),
        "interventions": sorted(rules),
        "emergency": _as_bool(row, "emergency"),
    }
    for key in (
        "episode",
        "step",
        "s",
        "speed",
        "joint_envelope_violated",
        "cv_confidence",
        "cv_reason",
    ):
        value = row.get(key, "").strip()
        if value:
            result[key] = value
    return result


def analyse_csv(path: Path, criteria: Criteria, hotspot_limit: int = 20) -> dict[str, Any]:
    """Analyse one eval CSV and return counts plus bounded evidence hotspots."""

    provenance = _load_provenance(path)
    counts = {
        "rows": 0,
        "row_parse_errors": 0,
        "centered_rows": 0,
        "centered_cv_usable_rows": 0,
        "centered_ey_error_steps": 0,
        "centered_epsi_error_steps": 0,
        "centered_lane_envelope_conflict_steps": 0,
        "centered_heading_envelope_conflict_steps": 0,
        "centered_false_rule_steps": 0,
        "centered_perception_invalid_steps": 0,
        "centered_emergency_steps": 0,
        "centered_unattributed_emergency_steps": 0,
        "lateral_underread_steps": 0,
    }
    maxima = {
        "centered_abs_ey_error_m": 0.0,
        "centered_abs_epsi_error_rad": 0.0,
        "underread_abs_gap_m": 0.0,
    }
    hotspots: dict[str, list[dict[str, Any]]] = {
        "centered_cv_conflicts": [],
        "centered_false_rules": [],
        "centered_emergencies": [],
        "lateral_underread": [],
        "row_parse_errors": [],
    }

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            return {
                "path": _display_path(path),
                "sha256": _sha256(path),
                "schema_valid": False,
                "missing_columns": missing,
                "provenance": provenance,
                "counts": counts,
                "maxima": maxima,
                "hotspots": hotspots,
            }

        for row_number, row in enumerate(reader, start=2):
            counts["rows"] += 1
            try:
                ey = _as_float(row, "ey")
                epsi = _as_float(row, "epsi")
                cv_ey = _as_float(row, "cv_ey")
                cv_epsi = _as_float(row, "cv_epsi")
                cv_ok = _as_bool(row, "cv_ok")
                cv_available = _as_bool(row, "cv_state_available")
                cv_invalid = _as_bool(row, "cv_perception_invalid")
                emergency = _as_bool(row, "emergency")
                rules = _rules(row.get("interventions", ""))
            except (TypeError, ValueError) as exc:
                counts["row_parse_errors"] += 1
                if len(hotspots["row_parse_errors"]) < hotspot_limit:
                    hotspots["row_parse_errors"].append(
                        {"source": _display_path(path), "csv_row": row_number, "error": str(exc)}
                    )
                continue

            centred = (
                abs(ey) <= criteria.center_ey_max_m
                and abs(epsi) <= criteria.center_epsi_max_rad
            )
            cv_usable = cv_ok and cv_available and not cv_invalid
            if centred:
                counts["centered_rows"] += 1
            if centred and cv_usable:
                counts["centered_cv_usable_rows"] += 1
                ey_error = abs(cv_ey - ey)
                epsi_error = abs(_angle_error(cv_epsi, epsi))
                maxima["centered_abs_ey_error_m"] = max(
                    maxima["centered_abs_ey_error_m"], ey_error
                )
                maxima["centered_abs_epsi_error_rad"] = max(
                    maxima["centered_abs_epsi_error_rad"], epsi_error
                )
                ey_error_bad = ey_error > criteria.centered_ey_error_max_m
                epsi_error_bad = epsi_error > criteria.centered_epsi_error_max_rad
                lane_conflict = abs(cv_ey) > criteria.lane_limit_m
                heading_conflict = abs(cv_epsi) > criteria.heading_limit_rad
                counts["centered_ey_error_steps"] += int(ey_error_bad)
                counts["centered_epsi_error_steps"] += int(epsi_error_bad)
                counts["centered_lane_envelope_conflict_steps"] += int(lane_conflict)
                counts["centered_heading_envelope_conflict_steps"] += int(heading_conflict)
                if (
                    ey_error_bad
                    or epsi_error_bad
                    or lane_conflict
                    or heading_conflict
                ):
                    hotspots["centered_cv_conflicts"].append(
                        _context(path, row_number, row, ey, epsi, cv_ey, cv_epsi, rules)
                    )

            false_rules = bool(rules & CV_SAFETY_RULES)
            if centred and false_rules:
                counts["centered_false_rule_steps"] += 1
                hotspots["centered_false_rules"].append(
                    _context(path, row_number, row, ey, epsi, cv_ey, cv_epsi, rules)
                )
            if centred and cv_invalid:
                counts["centered_perception_invalid_steps"] += 1
            if centred and emergency:
                counts["centered_emergency_steps"] += 1
                # C-05 cause/failing-rule detail is absent from the current eval CSV.
                # Mark rows that cannot be attributed to an observable CV condition.
                direct_cv_evidence = (
                    cv_invalid
                    or bool(rules & CV_SAFETY_RULES)
                    or (cv_usable and abs(cv_ey) > criteria.lane_limit_m)
                    or (cv_usable and abs(cv_epsi) > criteria.heading_limit_rad)
                )
                if not direct_cv_evidence:
                    counts["centered_unattributed_emergency_steps"] += 1
                hotspots["centered_emergencies"].append(
                    _context(path, row_number, row, ey, epsi, cv_ey, cv_epsi, rules)
                )

            if cv_usable and abs(ey) >= criteria.lane_warning_m:
                magnitude_gap = abs(ey) - abs(cv_ey)
                underread = (
                    abs(cv_ey) < criteria.lane_warning_m
                    and magnitude_gap >= criteria.underread_min_gap_m
                )
                if underread:
                    counts["lateral_underread_steps"] += 1
                    maxima["underread_abs_gap_m"] = max(
                        maxima["underread_abs_gap_m"], magnitude_gap
                    )
                    hotspots["lateral_underread"].append(
                        _context(path, row_number, row, ey, epsi, cv_ey, cv_epsi, rules)
                    )

    # Keep the most severe examples, not merely the earliest rows.  This makes
    # the report retain the actual stop row even when a systematic bias starts
    # hundreds of cycles earlier.
    hotspots["centered_cv_conflicts"] = sorted(
        hotspots["centered_cv_conflicts"],
        key=lambda item: max(
            abs(item["ey_error_m"]) / max(criteria.centered_ey_error_max_m, 1e-12),
            abs(item["epsi_error_rad"])
            / max(criteria.centered_epsi_error_max_rad, 1e-12),
        ),
        reverse=True,
    )[:hotspot_limit]
    hotspots["centered_false_rules"] = sorted(
        hotspots["centered_false_rules"],
        key=lambda item: (
            item["emergency"],
            abs(item["epsi_error_rad"]),
            abs(item["ey_error_m"]),
        ),
        reverse=True,
    )[:hotspot_limit]
    hotspots["centered_emergencies"] = sorted(
        hotspots["centered_emergencies"],
        key=lambda item: max(abs(item["epsi_error_rad"]), abs(item["ey_error_m"])),
        reverse=True,
    )[:hotspot_limit]
    hotspots["lateral_underread"] = sorted(
        hotspots["lateral_underread"],
        key=lambda item: abs(item["ey_m"]) - abs(item["cv_ey_m"]),
        reverse=True,
    )[:hotspot_limit]
    hotspots["row_parse_errors"] = hotspots["row_parse_errors"][:hotspot_limit]

    return {
        "path": _display_path(path),
        "sha256": _sha256(path),
        "schema_valid": True,
        "missing_columns": [],
        "provenance": provenance,
        "counts": counts,
        "maxima": {key: round(value, 6) for key, value in maxima.items()},
        "hotspots": hotspots,
    }


def _sum_counts(inputs: Iterable[dict[str, Any]]) -> dict[str, int]:
    inputs = list(inputs)
    keys = inputs[0].get("counts", {}).keys() if inputs else ()
    return {key: sum(item["counts"][key] for item in inputs) for key in keys}


def _max_values(inputs: Iterable[dict[str, Any]]) -> dict[str, float]:
    inputs = list(inputs)
    keys = next(iter(inputs), {}).get("maxima", {}).keys()
    return {key: max((item["maxima"][key] for item in inputs), default=0.0) for key in keys}


def _check(check_id: str, observed: int, limit: int, rationale: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASS" if observed <= limit else "BLOCK",
        "observed": observed,
        "limit": limit,
        "rationale": rationale,
    }


def _checks_from_counts(counts: dict[str, int], criteria: Criteria) -> list[dict[str, Any]]:
    return [
        _check(
            "D43-CV-EY-CENTERED",
            counts.get("centered_ey_error_steps", 0),
            criteria.max_centered_ey_error_steps,
            "CV lateral disagreement exceeds the centred-vehicle preflight tolerance.",
        ),
        _check(
            "D43-CV-EPSI-CENTERED",
            counts.get("centered_epsi_error_steps", 0),
            criteria.max_centered_epsi_error_steps,
            "CV heading disagreement exceeds the GE2-anchored clean tolerance.",
        ),
        _check(
            "D43-CV-LANE-ENVELOPE-CENTERED",
            counts.get("centered_lane_envelope_conflict_steps", 0),
            criteria.max_centered_lane_envelope_conflict_steps,
            "CV alone places a ground-truth centred vehicle outside C-01's envelope.",
        ),
        _check(
            "D43-CV-HEADING-ENVELOPE-CENTERED",
            counts.get("centered_heading_envelope_conflict_steps", 0),
            criteria.max_centered_heading_envelope_conflict_steps,
            "CV alone places a ground-truth centred vehicle outside C-02's envelope.",
        ),
        _check(
            "D43-CV-RULE-FALSE-TRIGGER",
            counts.get("centered_false_rule_steps", 0),
            criteria.max_centered_false_rule_steps,
            "C-01/C-02/C-03 fired while the ground-truth vehicle was centred.",
        ),
        _check(
            "D43-CV-INVALID-CENTERED",
            counts.get("centered_perception_invalid_steps", 0),
            criteria.max_centered_perception_invalid_steps,
            "The CV supervisor declared perception invalid while ground truth was centred.",
        ),
        _check(
            "D43-EMERGENCY-CENTERED",
            counts.get("centered_emergency_steps", 0),
            criteria.max_centered_emergency_steps,
            "A nominal centred trace contains a C-05 emergency/shadow emergency.",
        ),
    ]


def _annotate_input_verdict(item: dict[str, Any], criteria: Criteria) -> None:
    """Attach the same fail-closed checks to an individual input record."""

    counts = item["counts"]
    checks = _checks_from_counts(counts, criteria)
    invalid_reasons = []
    if not item["schema_valid"]:
        invalid_reasons.append("missing required columns")
    if not item["provenance"]["valid"]:
        invalid_reasons.extend(item["provenance"]["errors"])
    if counts.get("row_parse_errors", 0):
        invalid_reasons.append("one or more rows could not be parsed")
    if counts.get("centered_rows", 0) < criteria.min_centered_samples:
        invalid_reasons.append(
            f"centred rows {counts.get('centered_rows', 0)} < "
            f"minimum {criteria.min_centered_samples}"
        )
    item["checks"] = checks
    item["diagnostics"] = {
        "lateral_underread_steps": counts.get("lateral_underread_steps", 0),
        "gating": False,
        "status": (
            "OBSERVED" if counts.get("lateral_underread_steps", 0) else "NOT_OBSERVED"
        ),
    }
    item["invalid_reasons"] = invalid_reasons
    if invalid_reasons:
        item["verdict"] = "INVALID"
    elif any(check["status"] == "BLOCK" for check in checks):
        item["verdict"] = "BLOCKED"
    else:
        item["verdict"] = "PASS"


def build_report(
    paths: Sequence[Path], criteria: Criteria | None = None, hotspot_limit: int = 20
) -> dict[str, Any]:
    """Build a JSON-serialisable aggregate preflight report."""

    criteria = criteria or Criteria()
    analysed = [analyse_csv(path, criteria, hotspot_limit) for path in paths]
    for item in analysed:
        _annotate_input_verdict(item, criteria)
    totals = _sum_counts(analysed)
    maxima = _max_values(analysed)
    schema_errors = sum(not item["schema_valid"] for item in analysed)
    provenance_errors = sum(not item["provenance"]["valid"] for item in analysed)
    parse_errors = totals.get("row_parse_errors", 0)
    coverage_shortfall = max(0, criteria.min_centered_samples - totals.get("centered_rows", 0))

    checks = _checks_from_counts(totals, criteria)

    invalid_reasons = []
    if not paths:
        invalid_reasons.append("no input CSV files")
    if schema_errors:
        invalid_reasons.append(f"{schema_errors} input(s) missing required columns")
    if provenance_errors:
        invalid_reasons.append(
            f"{provenance_errors} input(s) have incomplete or inconsistent provenance"
        )
    if parse_errors:
        invalid_reasons.append(f"{parse_errors} row(s) could not be parsed")
    if coverage_shortfall:
        invalid_reasons.append(
            f"centred coverage short by {coverage_shortfall} rows "
            f"(minimum {criteria.min_centered_samples})"
        )

    if invalid_reasons:
        verdict = "INVALID"
    elif any(item["status"] == "BLOCK" for item in checks):
        verdict = "BLOCKED"
    else:
        verdict = "PASS"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "D-43 offline preflight before a posterior Gazebo 2-D campaign",
        "verdict": verdict,
        "invalid_reasons": invalid_reasons,
        "criteria": asdict(criteria),
        "checks": checks,
        "diagnostics": {
            "D43-CV-EY-UNDERREAD": {
                "status": (
                    "OBSERVED" if totals.get("lateral_underread_steps", 0) else "NOT_OBSERVED"
                ),
                "observed_steps": totals.get("lateral_underread_steps", 0),
                "gating": False,
                "rationale": (
                    "Off-centre lateral under-read is reported separately from the "
                    "centred-vehicle false-trigger gate."
                ),
            }
        },
        "totals": totals,
        "maxima": maxima,
        "notes": {
            "lateral_underread": (
                "Characterisation only: truth |ey| >= lane_warning_m while CV remains "
                "inside that band by at least underread_min_gap_m."
            ),
            "unattributed_emergency": (
                "The current eval CSV does not log the C-05 trigger reason or "
                "joint_envelope_failing_rules; centred emergencies without direct CV "
                "evidence therefore remain unattributed and block conservatively."
            ),
            "threshold_scope": (
                "Centred/error limits are preflight engineering criteria, not changes "
                "to the ODD, safety requirements, or cage configuration."
            ),
            "heading_tolerance_provenance": (
                "0.40 rad is just above the final clean GE2 oracle maximum 0.38734 rad "
                "(experiments/sim/runs/cv_estimator_val_20260610T181634Z/summary.json) "
                "and 0.0363 rad below C-02 theta_max=0.4363 rad. Direct envelope "
                "crossings are reported separately."
            ),
        },
        "inputs": analysed,
    }


def _resolve_inputs(values: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = Path(value)
        if path.is_dir():
            path = path / "cage_status.csv"
        if not path.is_file():
            raise FileNotFoundError(f"input does not exist or is not a file: {path}")
        paths.append(path.resolve())
    return paths


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline D-43 preflight over one or more eval cage_status.csv files."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="cage_status.csv paths or eval run directories",
    )
    parser.add_argument("--output", type=Path, help="write the full JSON report here")
    parser.add_argument("--hotspot-limit", type=int, default=20)
    parser.add_argument("--center-ey-max-m", type=float, default=0.08)
    parser.add_argument("--center-epsi-max-rad", type=float, default=0.10)
    parser.add_argument("--centered-ey-error-max-m", type=float, default=0.05)
    parser.add_argument("--centered-epsi-error-max-rad", type=float, default=0.40)
    parser.add_argument("--min-centered-samples", type=int, default=100)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        paths = _resolve_inputs(args.inputs)
        criteria = Criteria(
            center_ey_max_m=args.center_ey_max_m,
            center_epsi_max_rad=args.center_epsi_max_rad,
            centered_ey_error_max_m=args.centered_ey_error_max_m,
            centered_epsi_error_max_rad=args.centered_epsi_error_max_rad,
            min_centered_samples=args.min_centered_samples,
        )
        report = build_report(paths, criteria, args.hotspot_limit)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "checks": report["checks"],
        "totals": report["totals"],
        "maxima": report["maxima"],
        "output": str(args.output) if args.output else None,
    }, indent=2))
    return {"PASS": 0, "INVALID": 1, "BLOCKED": 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
