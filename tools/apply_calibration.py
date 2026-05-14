#!/usr/bin/env python3
"""
apply_calibration.py
--------------------
Ingest the pre-G1 calibration campaign results (M-1..M-5), validate
them, apply the decision rules declared in each protocol document,
and produce a propagation report comparing the target SRS / cage.yaml
parameter values to the current ones.

This script is the closing companion to the protocols under
`experiments/calibration/M{1..5}_*.md`. It does NOT edit prose in the
SRS or in the manuscript: those edits remain manual because they
involve rationale text. The script does:

  - Validate each MN_results.json against its expected schema.
  - Skip stub files where `executed_on` is the sentinel "YYYY-MM-DD".
  - Apply the decision rule of each measurement and compute the
    target parameter value(s).
  - Read the current values from `cage/cage.yaml` and compare.
  - Emit a per-measurement report on stdout with the suggested
    SRS / cage.yaml / CHANGELOG updates.
  - With `--apply-yaml`, write the new cage.yaml values in place
    (a `.bak` backup is left next to the file).

Exit codes:
  0  every available measurement produced a valid decision
  1  one or more measurements failed schema validation
  2  one or more measurements demand a tightening that the platform
     could not satisfy (e.g., M-3 a_max_brake < 0.3)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CALIB_DIR = REPO_ROOT / "experiments" / "calibration"
CAGE_YAML = REPO_ROOT / "cage" / "cage.yaml"
SRS_MD = REPO_ROOT / "docs" / "03_safety_requirements.md"

UNFILLED_DATE = "YYYY-MM-DD"


# =============================================================
# Result container
# =============================================================

@dataclass
class Outcome:
    measurement_id: str
    status: str  # "ready" | "not_executed" | "invalid" | "platform_underperforms"
    decision: str = ""
    target_values: Dict[str, float] = field(default_factory=dict)
    current_values: Dict[str, Any] = field(default_factory=dict)
    srs_sections_to_update: List[str] = field(default_factory=list)
    yaml_keys_to_update: Dict[str, float] = field(default_factory=dict)
    changelog_snippet: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# =============================================================
# Loaders
# =============================================================

def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON in {path.name}: {e}") from e


def load_cage_yaml() -> dict:
    return yaml.safe_load(CAGE_YAML.read_text(encoding="utf-8"))


# =============================================================
# Helpers
# =============================================================

def is_stub(data: dict) -> bool:
    """True if the result file is still the unfilled template."""
    return data.get("executed_on") == UNFILLED_DATE


def get_nested(d: dict, dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if cur is None:
            return None
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def require(data: dict, key_path: str, kind: type, errors: List[str]) -> Any:
    """Validate that data has key_path of the right kind. Append to errors if not."""
    val = get_nested(data, key_path)
    if val is None:
        errors.append(f"missing required key '{key_path}'")
        return None
    if not isinstance(val, kind):
        errors.append(f"key '{key_path}' has type {type(val).__name__}, expected {kind.__name__}")
        return None
    return val


def round_to_step(x: float, step: float = 0.01) -> float:
    return round(x / step) * step


# =============================================================
# Decision rules — one per measurement
# =============================================================

def apply_m1(data: dict, cage: dict) -> Outcome:
    """SR-001 d_max margin from LiDAR static noise."""
    out = Outcome(measurement_id="M-1", status="invalid")
    positions = require(data, "positions", list, out.errors)
    if positions is None or len(positions) == 0:
        return out

    sigmas = [p.get("std_dev_m") for p in positions]
    biases = [
        abs((p.get("mean_observed_y_m") or 0.0) - (p.get("ground_truth_y_m") or 0.0))
        for p in positions
    ]
    if any(s is None for s in sigmas):
        out.errors.append("one or more positions have null std_dev_m")
        return out

    sigma_max = max(sigmas)
    bias_max = max(biases)

    out.current_values = {
        "d_max_m (cage.yaml c01)": get_nested(cage, "cage.c01_lane_boundary.d_max_m"),
    }

    if sigma_max <= 0.01 and bias_max <= 0.005:
        out.status = "ready"
        out.decision = "SR-001 confirmed at d_max = 0.16 m (LiDAR noise within budget)."
        out.target_values["d_max_m"] = 0.16
        out.yaml_keys_to_update["cage.c01_lane_boundary.d_max_m"] = 0.16
    elif sigma_max <= 0.02:
        out.status = "ready"
        out.decision = (
            f"SR-001 confirmed at d_max = 0.16 m with reduced margin "
            f"(sigma_max={sigma_max:.4f} m exceeds the 0.01 m budget but stays below 0.02 m); "
            "document the reduced margin in the rationale and consider widening delta in a future revision."
        )
        out.target_values["d_max_m"] = 0.16
        out.yaml_keys_to_update["cage.c01_lane_boundary.d_max_m"] = 0.16
        out.warnings.append(f"sigma_max={sigma_max:.4f} m > 0.01 m budget; margin is tight")
    else:
        # Recompute d_max preserving 3-sigma on the noise component
        # d_max = ROAD_WIDTH/2 - (3*sigma + LATENCY*v_max + half_footprint)
        ROAD_WIDTH_HALF = 0.25
        LATENCY = 0.050  # s, nominal
        V_MAX = 0.5
        HALF_FOOTPRINT = 0.05
        new_delta = 3 * sigma_max + LATENCY * V_MAX + HALF_FOOTPRINT
        new_d_max = round_to_step(ROAD_WIDTH_HALF - new_delta, 0.005)
        out.status = "ready"
        out.decision = (
            f"SR-001 d_max revised downward to {new_d_max:.3f} m "
            f"(sigma_max={sigma_max:.4f} m exceeds 0.02 m; preserving 3-sigma on noise)."
        )
        out.target_values["d_max_m"] = new_d_max
        out.yaml_keys_to_update["cage.c01_lane_boundary.d_max_m"] = new_d_max

    out.srs_sections_to_update = ["SR-001 §Parameters"]
    out.changelog_snippet = (
        f"M-1 closed (sigma_max={sigma_max:.4f} m, bias_max={bias_max:.4f} m). {out.decision}"
    )
    return out


def apply_m2(data: dict, cage: dict) -> Outcome:
    """SR-001 latency assumption from end-to-end control latency."""
    out = Outcome(measurement_id="M-2", status="invalid")
    p95 = get_nested(data, "latency_obs_to_safe_action_ms.p95")
    if p95 is None or not isinstance(p95, (int, float)):
        out.errors.append("missing or non-numeric latency_obs_to_safe_action_ms.p95")
        return out

    out.current_values = {
        "LATENCY_NOMINAL_ms (ODD assumption)": 50,
        "cycle_period_ms (cage.yaml control)": get_nested(cage, "cage.control.cycle_period_ms"),
    }

    if p95 <= 50:
        out.status = "ready"
        out.decision = "SR-001 latency assumption confirmed at 50 ms (one control cycle)."
        out.target_values["LATENCY_NOMINAL_ms"] = 50
    elif p95 <= 75:
        out.status = "ready"
        out.decision = (
            f"p95={p95:.1f} ms exceeds 50 ms. Two options: "
            "(a) tighten cycle_period_ms to 33 (30 Hz); "
            "(b) widen the latency component of d_max margin to v_max * 75 ms = 0.0375 m "
            "and recompute d_max. The chosen path must be recorded in the decision field of M2_results.json."
        )
        out.warnings.append("decision is non-trivial; review the decision field of M2_results.json")
        out.target_values["LATENCY_NOMINAL_ms"] = round(p95)
    else:
        out.status = "platform_underperforms"
        out.decision = (
            f"p95={p95:.1f} ms exceeds 75 ms. The cage is not meeting timing assumptions; "
            "diagnose the ROS2 executor, threading model and per-callback cost before closing G1."
        )
        out.errors.append("p95 latency > 75 ms — block on G1 closure until diagnosed")

    out.srs_sections_to_update = ["SR-001 §Parameters (latency)"]
    out.changelog_snippet = f"M-2 closed (p95={p95:.1f} ms). {out.decision}"
    return out


def apply_m3(data: dict, cage: dict) -> Outcome:
    """SR-005 a_min and SR-008 t_stop_max from max-deceleration trials."""
    out = Outcome(measurement_id="M-3", status="invalid")
    trials = require(data, "trials", list, out.errors)
    if trials is None:
        return out

    fast_trials = [t for t in trials if t.get("initial_speed_mps") == 0.5]
    decels = [t.get("average_deceleration_mps2") for t in fast_trials]
    if any(d is None for d in decels) or len(decels) < 3:
        out.errors.append(
            f"need >=3 trials at v=0.5 m/s with non-null average_deceleration_mps2 "
            f"(got {len(decels)} trials with {sum(d is not None for d in decels)} populated)"
        )
        return out

    a_max_brake = sum(decels) / len(decels)
    V_MAX = 0.5

    out.current_values = {
        "a_min_mps2 (cage.yaml c05)": get_nested(cage, "cage.c05_emergency.a_min_mps2"),
        "t_stop_max_s (SR-008)": 1.7,
        "v_max_straight_mps (cage.yaml c04)": get_nested(cage, "cage.c04_speed_ceiling.v_max_straight_mps"),
    }

    if a_max_brake >= 0.4:
        a_min_new = 0.4
        t_stop_max_new = 1.3
        out.status = "ready"
        out.decision = (
            f"a_max_brake={a_max_brake:.3f} m/s^2 (>=0.4). Coordinated revision: "
            f"SR-005 a_min: 0.3 -> {a_min_new}; SR-008 t_stop_max: 1.7 -> {t_stop_max_new} s."
        )
        out.target_values["a_min_mps2"] = a_min_new
        out.target_values["t_stop_max_s"] = t_stop_max_new
        out.yaml_keys_to_update["cage.c05_emergency.a_min_mps2"] = a_min_new
    elif a_max_brake >= 0.3:
        out.status = "ready"
        out.decision = (
            f"a_max_brake={a_max_brake:.3f} m/s^2 (in [0.3, 0.4)). "
            "SR-005 a_min confirmed at 0.3 m/s^2; SR-008 t_stop_max confirmed at 1.7 s."
        )
        out.target_values["a_min_mps2"] = 0.3
        out.target_values["t_stop_max_s"] = 1.7
        out.yaml_keys_to_update["cage.c05_emergency.a_min_mps2"] = 0.3
    else:
        a_min_new = round_to_step(a_max_brake, 0.01)
        v_max_new = round_to_step(a_min_new * 1.7, 0.05)
        out.status = "platform_underperforms"
        out.decision = (
            f"a_max_brake={a_max_brake:.3f} m/s^2 (<0.3). Coordinated revision: "
            f"SR-005 a_min revised to {a_min_new}; SR-004 v_max_straight reduced from 0.5 to "
            f"{v_max_new} m/s to preserve SR-005 <-> SR-008 consistency."
        )
        out.target_values["a_min_mps2"] = a_min_new
        out.target_values["v_max_straight_mps"] = v_max_new
        out.yaml_keys_to_update["cage.c05_emergency.a_min_mps2"] = a_min_new
        out.yaml_keys_to_update["cage.c04_speed_ceiling.v_max_straight_mps"] = v_max_new
        out.warnings.append("platform cannot satisfy a_min = 0.3 m/s^2 at v_max_straight = 0.5 m/s; v_max reduced")

    out.srs_sections_to_update = ["SR-005 §Parameters (a_min)", "SR-008 §Parameters (t_stop_max)"]
    if "v_max_straight_mps" in out.target_values:
        out.srs_sections_to_update.append("SR-004 §Parameters (v_max_straight)")
    out.changelog_snippet = f"M-3 closed (a_max_brake={a_max_brake:.3f} m/s^2). {out.decision}"
    return out


def apply_m4(data: dict, cage: dict) -> Outcome:
    """SR-004 v_max_curve and k_kappa from speed-vs-curvature trials."""
    out = Outcome(measurement_id="M-4", status="invalid")
    v_max_emp = require(data, "v_max_curve_empirical_mps", (int, float), out.errors)
    if v_max_emp is None:
        return out

    v_max_curve_new = round_to_step(0.8 * v_max_emp, 0.05)

    out.current_values = {
        "v_max_curve_mps (cage.yaml c04)": get_nested(cage, "cage.c04_speed_ceiling.v_max_curve_mps"),
        "k_kappa_mps_per_curvature (cage.yaml c04)": get_nested(cage, "cage.c04_speed_ceiling.k_kappa_mps_per_curvature"),
    }

    fitted_k = data.get("fitted_k_kappa_mps_per_curvature")

    if v_max_emp >= 0.30:
        out.status = "ready"
        out.decision = (
            f"v_max_curve_empirical={v_max_emp:.3f} m/s (>=0.30). "
            f"SR-004 v_max_curve revised from 0.25 to {v_max_curve_new:.3f} m/s "
            "with the standard 20 % safety margin."
        )
        out.target_values["v_max_curve_mps"] = v_max_curve_new
        out.yaml_keys_to_update["cage.c04_speed_ceiling.v_max_curve_mps"] = v_max_curve_new
    elif v_max_emp >= 0.20:
        out.status = "ready"
        out.decision = (
            f"v_max_curve_empirical={v_max_emp:.3f} m/s (in [0.20, 0.30)). "
            "SR-004 v_max_curve confirmed at 0.25 m/s (within safety margin of empirical)."
        )
        out.target_values["v_max_curve_mps"] = 0.25
        out.yaml_keys_to_update["cage.c04_speed_ceiling.v_max_curve_mps"] = 0.25
    else:
        out.status = "platform_underperforms"
        out.decision = (
            f"v_max_curve_empirical={v_max_emp:.3f} m/s (<0.20). "
            f"SR-004 v_max_curve revised down to {v_max_curve_new:.3f} m/s; "
            "coordinated revision of k_kappa to preserve the linear-interpolation crossing."
        )
        out.target_values["v_max_curve_mps"] = v_max_curve_new
        out.yaml_keys_to_update["cage.c04_speed_ceiling.v_max_curve_mps"] = v_max_curve_new
        out.warnings.append("v_max_curve below the SR-004 working assumption; review SR rationale")

    if fitted_k is not None and isinstance(fitted_k, (int, float)):
        out.target_values["k_kappa_mps_per_curvature"] = round_to_step(fitted_k, 0.01)
        out.yaml_keys_to_update["cage.c04_speed_ceiling.k_kappa_mps_per_curvature"] = round_to_step(fitted_k, 0.01)
        out.decision += f" Fitted k_kappa={fitted_k:.3f} replaces the working assumption 0.3."

    out.srs_sections_to_update = ["SR-004 §Parameters (v_max_curve, k_kappa)"]
    out.changelog_snippet = f"M-4 closed (v_max_emp={v_max_emp:.3f} m/s). {out.decision}"
    return out


def apply_m5(data: dict, cage: dict) -> Outcome:
    """SR-006 delta_max for steering and throttle from actuator-step trials."""
    out = Outcome(measurement_id="M-5", status="invalid")
    delta_steer = get_nested(data, "steering.delta_actuator_max_steering_per_cycle")
    delta_thr = get_nested(data, "throttle.delta_actuator_max_throttle_per_cycle")
    if delta_steer is None or delta_thr is None:
        out.errors.append(
            "missing steering.delta_actuator_max_steering_per_cycle or "
            "throttle.delta_actuator_max_throttle_per_cycle"
        )
        return out

    out.current_values = {
        "delta_max_steering_per_cycle (cage.yaml c06)": get_nested(
            cage, "cage.c06_rate_limiter.delta_max_steering_per_cycle"
        ),
        "delta_max_throttle_per_cycle (cage.yaml c06)": get_nested(
            cage, "cage.c06_rate_limiter.delta_max_throttle_per_cycle"
        ),
    }

    # Decision rule: cage limit at half the actuator envelope.
    new_delta_steer = (
        0.15 if delta_steer >= 0.30 else round_to_step(0.5 * delta_steer, 0.01)
    )
    new_delta_thr = (
        0.10 if delta_thr >= 0.20 else round_to_step(0.5 * delta_thr, 0.01)
    )

    parts = []
    if new_delta_steer == 0.15:
        parts.append("SR-006 delta_max_steering confirmed at 0.15.")
    else:
        parts.append(
            f"SR-006 delta_max_steering revised 0.15 -> {new_delta_steer:.3f} "
            f"(actuator envelope delta_act_steer={delta_steer:.3f})."
        )
    if new_delta_thr == 0.10:
        parts.append("SR-006 delta_max_throttle confirmed at 0.10.")
    else:
        parts.append(
            f"SR-006 delta_max_throttle revised 0.10 -> {new_delta_thr:.3f} "
            f"(actuator envelope delta_act_thr={delta_thr:.3f})."
        )

    out.status = "ready"
    out.decision = " ".join(parts)
    out.target_values["delta_max_steering_per_cycle"] = new_delta_steer
    out.target_values["delta_max_throttle_per_cycle"] = new_delta_thr
    out.yaml_keys_to_update["cage.c06_rate_limiter.delta_max_steering_per_cycle"] = new_delta_steer
    out.yaml_keys_to_update["cage.c06_rate_limiter.delta_max_throttle_per_cycle"] = new_delta_thr
    out.srs_sections_to_update = ["SR-006 §Parameters (delta_max_steering, delta_max_throttle)"]
    out.changelog_snippet = (
        f"M-5 closed (delta_act_steer={delta_steer:.3f}, delta_act_thr={delta_thr:.3f}). {out.decision}"
    )
    return out


# =============================================================
# Driver
# =============================================================

DISPATCH = {
    "M-1": (apply_m1, "M1_results.json"),
    "M-2": (apply_m2, "M2_results.json"),
    "M-3": (apply_m3, "M3_results.json"),
    "M-4": (apply_m4, "M4_results.json"),
    "M-5": (apply_m5, "M5_results.json"),
}


def process_one(mid: str, cage_data: dict) -> Outcome:
    fn, filename = DISPATCH[mid]
    path = CALIB_DIR / filename
    data = load_json(path)
    if data is None:
        return Outcome(measurement_id=mid, status="not_executed",
                       decision=f"{filename} not found; create from the protocol or wait for execution.")
    if is_stub(data):
        return Outcome(measurement_id=mid, status="not_executed",
                       decision=f"{filename} still has executed_on='{UNFILLED_DATE}'; not yet executed.")
    return fn(data, cage_data)


def set_nested(d: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = d
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def apply_yaml_updates(updates: Dict[str, float]) -> None:
    """Write the new values to cage/cage.yaml, leaving a .bak alongside."""
    if not updates:
        return
    bak = CAGE_YAML.with_suffix(".yaml.bak")
    shutil.copy(CAGE_YAML, bak)
    cage = load_cage_yaml()
    for key, value in updates.items():
        set_nested(cage, key, value)
    CAGE_YAML.write_text(yaml.safe_dump(cage, sort_keys=False), encoding="utf-8")
    print(f"\n>>> Wrote {len(updates)} parameter update(s) to {CAGE_YAML.relative_to(REPO_ROOT)}")
    print(f">>> Backup left at {bak.relative_to(REPO_ROOT)}")


def print_outcome(o: Outcome) -> None:
    bar = "-" * 70
    print(f"\n{bar}\n{o.measurement_id}  [{o.status}]\n{bar}")
    if o.status == "not_executed":
        print(f"  {o.decision}")
        return
    if o.errors:
        print("  ERRORS:")
        for e in o.errors:
            print(f"    - {e}")
    if o.warnings:
        print("  WARNINGS:")
        for w in o.warnings:
            print(f"    - {w}")
    if o.decision:
        print(f"  Decision: {o.decision}")
    if o.current_values:
        print("  Current values:")
        for k, v in o.current_values.items():
            print(f"    {k:<55} = {v}")
    if o.target_values:
        print("  Target values:")
        for k, v in o.target_values.items():
            print(f"    {k:<55} = {v}")
    if o.yaml_keys_to_update:
        print("  cage.yaml updates that would be applied with --apply-yaml:")
        for k, v in o.yaml_keys_to_update.items():
            print(f"    {k} = {v}")
    if o.srs_sections_to_update:
        print("  SRS sections to update manually:")
        for s in o.srs_sections_to_update:
            print(f"    - {s}")
    if o.changelog_snippet:
        print("  CHANGELOG snippet:")
        print(f"    {o.changelog_snippet}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-yaml",
        action="store_true",
        help="write the new values back to cage/cage.yaml (a .bak backup is left)",
    )
    parser.add_argument(
        "--measurement",
        choices=list(DISPATCH.keys()),
        help="only process this measurement (default: all)",
    )
    args = parser.parse_args()

    if not CAGE_YAML.exists():
        print(f"ERROR: cage configuration not found at {CAGE_YAML}", file=sys.stderr)
        return 1

    cage = load_cage_yaml()

    targets = [args.measurement] if args.measurement else list(DISPATCH.keys())
    outcomes = [process_one(m, cage) for m in targets]

    print("=" * 70)
    print("apply_calibration.py — calibration campaign report")
    print("=" * 70)

    yaml_updates: Dict[str, float] = {}
    any_invalid = False
    any_underperforms = False

    for o in outcomes:
        print_outcome(o)
        if o.status == "invalid":
            any_invalid = True
        if o.status == "platform_underperforms":
            any_underperforms = True
        if args.apply_yaml and o.status == "ready":
            yaml_updates.update(o.yaml_keys_to_update)

    # Aggregate summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    counts: Dict[str, int] = {}
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
    for status, n in counts.items():
        print(f"  {status:<25} {n}")

    if args.apply_yaml:
        apply_yaml_updates(yaml_updates)
        print("\nNext steps:")
        print("  1. Review the cage.yaml diff (compare to .bak).")
        print("  2. Apply the SRS section edits listed above.")
        print("  3. Bump cage.yaml version to 0.3.0 in the same commit.")
        print("  4. Add the corresponding CHANGELOG entry.")
        print("  5. Re-run `python tools/check_traceability.py` and `pytest cage/tests/`.")
    else:
        print("\n(dry-run; re-run with --apply-yaml to write cage.yaml changes)")

    if any_invalid:
        return 1
    if any_underperforms:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
