#!/usr/bin/env python3
"""
Validate executable scenario YAML files against the Phase-2 schema.

Phase-2 scope is intentionally partial: SC-NOM-01 and SC-EDGE-01 are fully
specified executable scenarios; the remaining scenario YAMLs may still be
explicit stubs while the scenario library matures in later phases. Default
mode therefore fails on malformed full YAMLs and missing F2-required YAMLs,
but reports other missing/stub scenarios as warnings. Use --strict to turn
warnings into failures before a final scenario-library gate.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO_ROOT / "scenarios"
SCENARIO_DOC = REPO_ROOT / "docs" / "05_scenario_library.md"

ID_RE = re.compile(r"^SC-(NOM|EDGE|PERT|FRONT)-\d{2}$")
SR_RE = re.compile(r"^SR-\d{3}$")
METRIC_RE = re.compile(r"^M-[A-Z]\d+$")
DOC_SCENARIO_RE = re.compile(r"^## (SC-(?:NOM|EDGE|PERT|FRONT)-\d{2})\b", re.MULTILINE)

# Bare-name (non-M-id) tokens accepted in metrics_primary/secondary. These are
# per-run event/quantity fields the executor records directly rather than
# catalogued M-* metrics: time_to_recovery_heading (SC-EDGE-01) and the frontier
# cage-efficacy fields road_edge_contact (per-run event behind M-S5) and
# max_excursion_m (the realised value of M-S1). Documented in docs/06.
NON_METRIC_TOKENS = {"time_to_recovery_heading", "road_edge_contact", "max_excursion_m"}

REQUIRED_FULL_KEYS = {
    "id",
    "category",
    "description",
    "initial_conditions",
    "perturbations",
    "termination",
    "metrics_primary",
    "metrics_secondary",
    "pass_criterion_per_run",
    "pass_criterion_per_scenario",
    "references_SR",
    "n_runs_recommended",
}

EXPECTED_CATEGORY = {
    "NOM": "nominal",
    "EDGE": "edge",
    "PERT": "perturbed",
    "FRONT": "frontier",
}

F2_REQUIRED_FULL = {"SC-NOM-01", "SC-EDGE-01"}


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat stubs and doc/YAML coverage gaps as errors",
    )
    args = parser.parse_args(argv)

    result = Result()
    yaml_by_id: dict[str, Path] = {}

    for path in sorted(SCENARIO_DIR.glob("*/*.yaml")):
        validate_yaml_file(path, result, yaml_by_id)

    doc_ids = set(extract_doc_scenario_ids())
    yaml_ids = set(yaml_by_id)

    for scenario_id in sorted(F2_REQUIRED_FULL):
        if scenario_id not in yaml_ids:
            result.error(f"Missing F2-required scenario YAML for {scenario_id}.")

    for scenario_id in sorted(doc_ids - yaml_ids):
        result.warn(f"{scenario_id} is documented but has no YAML file yet.")

    for scenario_id in sorted(yaml_ids - doc_ids):
        result.warn(f"{scenario_id} has a YAML file but is not documented in docs/05.")

    print_report(result, strict=args.strict)
    return 1 if result.errors or (args.strict and result.warnings) else 0


def validate_yaml_file(path: Path, result: Result, yaml_by_id: dict[str, Path]) -> None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        result.error(f"{rel(path)}: YAML parse error: {exc}")
        return

    if not isinstance(data, dict):
        result.error(f"{rel(path)}: top-level YAML value must be a mapping.")
        return

    scenario_id = data.get("id")
    if not isinstance(scenario_id, str) or not ID_RE.match(scenario_id):
        result.error(f"{rel(path)}: id must match SC-{{NOM|EDGE|PERT|FRONT}}-NN.")
        return

    if scenario_id in yaml_by_id:
        result.error(f"{rel(path)}: duplicate id also defined in {rel(yaml_by_id[scenario_id])}.")
    yaml_by_id[scenario_id] = path

    expected_dir = {
        "nominal": "nominal",
        "edge": "edge",
        "perturbed": "perturbed",
        "frontier": "frontier",
    }.get(data.get("category"))
    if expected_dir is None:
        result.error(f"{rel(path)}: category must be nominal, edge, perturbed, or frontier.")
    elif path.parent.name != expected_dir:
        result.error(f"{rel(path)}: category does not match parent directory.")

    prefix = scenario_id.split("-")[1]
    expected_category = EXPECTED_CATEGORY[prefix]
    if data.get("category") != expected_category:
        result.error(f"{rel(path)}: id prefix {prefix} requires category {expected_category}.")

    if data.get("status") == "stub":
        if scenario_id in F2_REQUIRED_FULL:
            result.error(f"{rel(path)}: {scenario_id} is F2-required and cannot be a stub.")
        else:
            result.warn(f"{rel(path)}: explicit stub, full YAML deferred.")
        return

    missing = sorted(REQUIRED_FULL_KEYS - set(data))
    if missing:
        result.error(f"{rel(path)}: missing required keys: {', '.join(missing)}.")
        return

    validate_full_scenario(path, data, result)


def validate_full_scenario(path: Path, data: dict, result: Result) -> None:
    scenario_id = data["id"]

    if not isinstance(data["metrics_primary"], list) or not data["metrics_primary"]:
        result.error(f"{rel(path)}: metrics_primary must be a non-empty list.")
    if not isinstance(data["metrics_secondary"], list):
        result.error(f"{rel(path)}: metrics_secondary must be a list.")

    for metric in data.get("metrics_primary", []) + data.get("metrics_secondary", []):
        if metric in NON_METRIC_TOKENS:
            continue
        if not isinstance(metric, str) or not METRIC_RE.match(metric):
            result.error(f"{rel(path)}: invalid metric id {metric!r}.")

    if not isinstance(data["references_SR"], list) or not data["references_SR"]:
        result.error(f"{rel(path)}: references_SR must be a non-empty list.")
    for sr_id in data.get("references_SR", []):
        if not isinstance(sr_id, str) or not SR_RE.match(sr_id):
            result.error(f"{rel(path)}: invalid SR id {sr_id!r}.")

    termination = data["termination"]
    if not isinstance(termination, dict):
        result.error(f"{rel(path)}: termination must be a mapping.")
    else:
        if "timeout_s" not in termination:
            result.error(f"{rel(path)}: termination.timeout_s is required.")
        if "events" not in termination or not isinstance(termination["events"], list):
            result.error(f"{rel(path)}: termination.events must be a list.")

    n_runs = data["n_runs_recommended"]
    if not isinstance(n_runs, dict):
        result.error(f"{rel(path)}: n_runs_recommended must map mode names to counts.")
    else:
        for mode in ("enforcement", "monitoring"):
            if mode not in n_runs or not isinstance(n_runs[mode], int) or n_runs[mode] <= 0:
                result.error(f"{rel(path)}: n_runs_recommended.{mode} must be a positive int.")

    if scenario_id in F2_REQUIRED_FULL:
        print(f"INFO: {scenario_id} full YAML OK ({rel(path)}).")


def extract_doc_scenario_ids() -> list[str]:
    if not SCENARIO_DOC.exists():
        return []
    return DOC_SCENARIO_RE.findall(SCENARIO_DOC.read_text(encoding="utf-8"))


def print_report(result: Result, strict: bool) -> None:
    print("\nScenario YAML check")
    print("=" * 40)
    for message in result.errors:
        print(f"ERROR: {message}")
    for message in result.warnings:
        print(f"WARNING: {message}")

    if result.errors:
        print(f"\nFAILED: {len(result.errors)} error(s), {len(result.warnings)} warning(s).")
    elif strict and result.warnings:
        print(f"\nFAILED under --strict: {len(result.warnings)} warning(s).")
    else:
        print(f"\nPASSED: 0 error(s), {len(result.warnings)} warning(s).")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
