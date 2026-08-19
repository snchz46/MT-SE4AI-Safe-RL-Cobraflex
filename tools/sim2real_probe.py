#!/usr/bin/env python3
"""Offline sim-to-real transfer probe for a track-'E' camera checkpoint.

Scores a policy's **lane response** on recorded *physical* camera frames and
contrasts it with the same policy's response on Gazebo frames, without the car
and without a simulator. It exists because the 18.08.2026 deployment (M-7/D-71)
spent a track session discovering something that was already latent in 1521
frames recorded that morning: the 550k trunk barely responds to lane position
on real imagery, and drives off to the left regardless of where it sits.

What it measures
----------------
For every frame it takes the policy's committed steering and the lane offset
``ey`` the D-43 estimator read on that same frame, then reports four numbers:

``swing``        steering change across the covered ``ey`` range — how much the
                 policy actually steers *because of* the lane.
``bias``         steering at ``ey = 0`` — the lane-independent offset.
``bias/swing``   the operative statistic. Below ~0.3 the lane dominates; above
                 1.0 the constant offset does and the car leaves the lane
                 whatever it sees.
``right``        share of frames commanding a right turn at all. A lane
                 follower that never turns one way is not following a lane.

Measured with this tool on the 18.08 circuit recording:

=========================  ======  =======  ==========  ======
arm                        swing   bias     bias/swing  right
=========================  ======  =======  ==========  ======
Gazebo frames (control)    0.363   +0.104   0.29        48.6 %
physical, as deployed      0.097   +0.143   1.47        0.8 %
=========================  ======  =======  ==========  ======

The physical column is the failure, quantified, from recorded data alone.

What it can and cannot conclude
-------------------------------
This is an **open-loop** probe on recorded frames: the policy never influences
what it sees next. It can therefore *falsify* transfer — a policy that does not
respond to the lane cannot drive one — but a PASS does not establish that the
car will drive. It is a necessary condition and a cheap one, not a sufficient
one, and it is a gate to run **before** a track session, not instead of it.

Two further limits, both inherited from the labels:

* ``ey`` comes from the D-43 estimator, which M-7 measured at 0.68-0.83 x true
  with a ~10 mm offset and unreliable pairing past ~55 mm. So the *slope* in
  physical units is biased; ``swing``, ``bias/swing`` and ``right`` are the
  statistics to read, and the comparison against the sim arm is what carries
  the meaning. ``--rectify`` improves the labels (see below) but does not make
  them ground truth.
* the recording must actually cover a range of ``ey``. A perfectly centred
  recording cannot show a response, and the tool refuses to score one.

``--rectify`` undistorts the physical frames into the canonical pinhole camera
the simulator renders (``camera_geometry.CameraModel`` defaults), using the M-6
intrinsics read from ``experiments/calibration/M6_results.json`` — one
authority, never a second copy of those numbers. Note that on the 550k trunk
this changes almost nothing (swing 0.097 -> 0.090): the trunk's gap is
photometric, not geometric. Rectification is for the *cage's* thresholds.

Exit codes:
    0  PASS      — the policy responds to the lane on real imagery
    1  INVALID   — missing/unusable inputs, or a recording with no ey coverage
    2  BLOCKED   — the response is too weak or too biased to drive
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

SCHEMA_VERSION = "sim2real-probe/v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
M6_RESULTS = REPO_ROOT / "experiments" / "calibration" / "M6_results.json"

# Gate thresholds. [provisional] — calibrated against exactly two arms: the
# Gazebo control arm (passes, and drives) and the 550k trunk on the 18.08
# physical recording (fails, and did not drive). They separate those two by a
# wide margin but have not been exercised on a borderline policy; revisit once
# a retrained checkpoint has been driven.
MIN_SWING_RETENTION = 0.50   # fraction of the sim arm's swing that must survive
MAX_BIAS_RATIO = 1.00        # |bias| / swing
MIN_RIGHT_FRACTION = 0.10    # share of frames commanding a right turn
MIN_EY_SPAN_MM = 60.0        # a recording flatter than this cannot score a response
MIN_FRAMES = 100

# Absolute fallbacks when no sim control arm is supplied (the sim arm is
# strongly preferred: it calibrates "what this policy does when it works").
FALLBACK_MIN_SWING = 0.15


# --------------------------------------------------------------------- inputs
def _load_camera_maps(width: int, height: int):
    """Rectification maps: measured physical camera -> canonical sim pinhole.

    Delegates to ``camera_geometry`` so the M-6 intrinsics have exactly one
    reader in the repository and this tool cannot drift from the node.
    """
    sys.path.insert(0, str(REPO_ROOT / "src" / "cobraflex_rl"))
    from cobraflex_rl.camera_geometry import (
        CameraModel,
        rectification_maps_from_calibration,
    )

    if not M6_RESULTS.exists():
        raise FileNotFoundError(f"--rectify needs {M6_RESULTS}")
    return rectification_maps_from_calibration(
        M6_RESULTS, CameraModel(width_px=width, height_px=height)
    )


def _read_labels(path: Path) -> Dict[str, float]:
    """``record_lane_dataset`` labels.csv -> {frame: ey_mm}, paired frames only.

    Unpaired frames and single-line fallbacks are dropped: their ``ey`` is
    inferred from the running width estimate, not measured, so pairing them
    with a steering command would regress against a partly-invented label.
    """
    out: Dict[str, float] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            if row.get("reason") != "ok" or row.get("paired") not in ("1", "True"):
                continue
            try:
                out[row["frame"]] = float(row["ey_m"]) * 1000.0
            except (KeyError, ValueError):
                continue
    return out


_SIM_NAME = re.compile(r"ey([+-][\d.]+)_dpsi([+-][\d.]+)\.png$")


def _sim_labels(paths: Sequence[Path], heading_zero_only: bool) -> Dict[str, float]:
    """Gazebo probe frames carry their pose in the filename."""
    out: Dict[str, float] = {}
    for p in paths:
        m = _SIM_NAME.search(p.name)
        if not m:
            continue
        if heading_zero_only and abs(float(m.group(2))) > 1e-6:
            continue
        out[p.name] = float(m.group(1)) * 1000.0
    return out


# ------------------------------------------------------------------- scoring
def _score(ey_mm: Sequence[float], steer: Sequence[float]) -> Dict[str, float]:
    ey = np.asarray(ey_mm, dtype=float)
    st = np.asarray(steer, dtype=float)
    lo, hi = float(np.percentile(ey, 2)), float(np.percentile(ey, 98))
    slope, bias = (float(v) for v in np.polyfit(ey, st, 1))
    corr = float(np.corrcoef(ey, st)[0, 1])
    swing = abs(slope) * (hi - lo)
    return {
        "n": int(ey.size),
        "ey_span_mm": hi - lo,
        "slope_per_mm": slope,
        "bias": bias,
        "swing": swing,
        "bias_over_swing": abs(bias) / swing if swing > 1e-9 else float("inf"),
        "right_fraction": float(np.mean(st < 0.0)),
        "r_squared": corr * corr,
        "steer_sd": float(np.std(st)),
        # The response must also have the right SIGN: steering left when the car
        # is left of centre is a response, but the wrong one.
        "sign_correct": bool(slope < 0.0),
    }


def _run_arm(
    model,
    frames: Sequence[Tuple[str, "np.ndarray"]],
    labels: Dict[str, float],
    stack_mode: str,
) -> Optional[Dict[str, float]]:
    """Roll the policy over one arm's frames.

    ``stack_mode='history'`` builds the k=4 stack from *consecutive* frames, the
    way the deployed ``rl_policy_node`` does. ``stack_mode='repeat'`` repeats
    each frame four times, which is all an unordered pose set allows. The
    distinction is not cosmetic: M-7's first offline probe repeated frames and
    read +0.53 where the live node read +0.12, and concluded the two could not
    be reconciled. They reconcile under 'history'.
    """
    sys.path.insert(0, str(REPO_ROOT / "src" / "cobraflex_rl"))
    from cobraflex_rl.camera_pipeline import to_observation

    buf: List[np.ndarray] = []
    ey: List[float] = []
    steer: List[float] = []
    for name, frame in frames:
        obs = to_observation(frame)
        if stack_mode == "history":
            buf = (buf + [obs])[-4:]
            if len(buf) < 4:
                continue
            stacked = np.concatenate(buf, axis=-1)
        else:
            stacked = np.concatenate([obs] * 4, axis=-1)
        if name not in labels:
            continue
        action, _ = model.predict(stacked, deterministic=True)
        ey.append(labels[name])
        steer.append(float(np.asarray(action).ravel()[0]))
    if len(ey) < MIN_FRAMES:
        return None
    return _score(ey, steer)


def _obs_stats(frames: Sequence[Tuple[str, "np.ndarray"]]) -> Dict[str, float]:
    """Photometry of the observation itself — the cheap early warning.

    The 550k trunk's failure is visible here before any policy is loaded: the
    Gazebo observation is near-bimodal (sd ~95, a third of pixels above 200)
    while the physical one is a flat mid-grey (sd ~36, 2.5 % above 200).
    """
    sys.path.insert(0, str(REPO_ROOT / "src" / "cobraflex_rl"))
    from cobraflex_rl.camera_pipeline import to_observation

    vals = np.concatenate(
        [to_observation(f).astype(np.float32).ravel() for _, f in frames[:200]]
    )
    return {
        "mean": float(vals.mean()),
        "sd": float(vals.std()),
        "frac_above_200": float(np.mean(vals > 200)),
        "frac_below_60": float(np.mean(vals < 60)),
    }


# ---------------------------------------------------------------------- load
def _load_frames(
    directory: Path, stride: int, rectify: bool
) -> List[Tuple[str, "np.ndarray"]]:
    import cv2

    paths = sorted(directory.glob("*.png"))
    if not paths:
        raise FileNotFoundError(f"no .png frames in {directory}")
    maps = None
    out: List[Tuple[str, np.ndarray]] = []
    for p in paths[::stride]:
        img = cv2.imread(str(p))
        if img is None:
            continue
        if rectify:
            if maps is None:
                maps = _load_camera_maps(img.shape[1], img.shape[0])
            img = cv2.remap(
                img, maps[0], maps[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
            )
        out.append((p.name, img))
    return out


def _dataset(root: Path) -> Tuple[Path, Optional[Path]]:
    """Accept either a dataset root (frames/ + labels.csv) or a frames dir."""
    if (root / "frames").is_dir():
        labels = root / "labels.csv"
        return root / "frames", labels if labels.exists() else None
    labels = root.parent / "labels.csv"
    return root, labels if labels.exists() else None


# -------------------------------------------------------------------- verdict
def verdict_for(
    real: Dict[str, float], sim: Optional[Dict[str, float]]
) -> Tuple[str, List[str], Optional[float]]:
    """Fail-closed gate over one real arm, calibrated by the sim arm when given.

    Separated from ``main`` so the thresholds can be regression-tested against
    the two arms that are actually known: the Gazebo control arm, which drives,
    and the 550k trunk on the 18.08 physical recording, which did not.
    """
    reasons: List[str] = []
    retention: Optional[float] = None
    if sim is not None and sim.get("swing", 0.0) > 1e-6:
        retention = real["swing"] / sim["swing"]
        if retention < MIN_SWING_RETENTION:
            reasons.append(
                f"lane response retains only {retention:.0%} of the sim arm's swing "
                f"(need {MIN_SWING_RETENTION:.0%})"
            )
    elif real["swing"] < FALLBACK_MIN_SWING:
        reasons.append(
            f"lane response swing {real['swing']:.3f} below the absolute floor "
            f"{FALLBACK_MIN_SWING:.3f} (no sim arm supplied to calibrate it)"
        )
    if real["bias_over_swing"] > MAX_BIAS_RATIO:
        reasons.append(
            f"lane-independent bias is {real['bias_over_swing']:.2f}x the whole "
            f"lane-dependent swing (max {MAX_BIAS_RATIO:.2f})"
        )
    if real["right_fraction"] < MIN_RIGHT_FRACTION:
        reasons.append(
            f"commands a right turn on only {real['right_fraction']:.1%} of frames "
            f"(need {MIN_RIGHT_FRACTION:.0%})"
        )
    if not real["sign_correct"]:
        reasons.append("steering response has the WRONG SIGN against lane offset")
    return ("PASS" if not reasons else "BLOCKED"), reasons, retention


# ---------------------------------------------------------------------- main
def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--checkpoint", type=Path, required=True, help="SB3 .zip policy")
    p.add_argument(
        "--real",
        type=Path,
        required=True,
        help="physical dataset root (frames/ + labels.csv) or a frames directory",
    )
    p.add_argument(
        "--sim",
        type=Path,
        default=None,
        help="Gazebo control-arm frames, pose encoded in the filename "
        "(…ey+0.000_dpsi+0.00.png). Strongly recommended: it calibrates the gate.",
    )
    p.add_argument("--rectify", action="store_true",
                   help="undistort the physical frames to the canonical sim camera")
    p.add_argument("--stride", type=int, default=1, help="frame subsampling")
    p.add_argument("--device", default="cpu")
    p.add_argument("--output", type=Path, default=None, help="write the JSON report here")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    if not args.checkpoint.exists():
        print(f"INVALID: checkpoint not found: {args.checkpoint}", file=sys.stderr)
        return 1

    from stable_baselines3 import PPO, SAC

    try:
        model = PPO.load(str(args.checkpoint), device=args.device)
    except Exception:  # noqa: BLE001 - a SAC checkpoint is a legitimate input
        model = SAC.load(str(args.checkpoint), device=args.device)

    frames_dir, labels_path = _dataset(args.real)
    if labels_path is None:
        print(
            f"INVALID: no labels.csv beside {frames_dir} — the probe needs the "
            "estimator's ey per frame (tools/record_lane_dataset.py writes it)",
            file=sys.stderr,
        )
        return 1
    real_frames = _load_frames(frames_dir, args.stride, args.rectify)
    real_labels = _read_labels(labels_path)
    real = _run_arm(model, real_frames, real_labels, "history")
    real_repeat = _run_arm(model, real_frames, real_labels, "repeat")
    if real is None:
        print(
            f"INVALID: fewer than {MIN_FRAMES} labelled+paired frames in {frames_dir}",
            file=sys.stderr,
        )
        return 1
    if real["ey_span_mm"] < MIN_EY_SPAN_MM:
        print(
            f"INVALID: the recording spans only {real['ey_span_mm']:.0f} mm of ey "
            f"(need {MIN_EY_SPAN_MM:.0f}). A centred recording cannot show a lane "
            "response — record a deliberately weaving pass.",
            file=sys.stderr,
        )
        return 1

    sim = None
    if args.sim is not None:
        sim_frames = _load_frames(args.sim, args.stride, False)
        sim = _run_arm(
            model, sim_frames, _sim_labels([Path(n) for n, _ in sim_frames], True),
            "repeat",
        )

    verdict, reasons, retention = verdict_for(real, sim)
    report = {
        "schema": SCHEMA_VERSION,
        "checkpoint": str(args.checkpoint),
        "real_dataset": str(frames_dir),
        "rectified": bool(args.rectify),
        "verdict": verdict,
        "reasons": reasons,
        "swing_retention_vs_sim": retention,
        "arms": {
            "real": real,
            "real_repeat_stacked": real_repeat,
            "sim_control": sim,
        },
        "observation_photometry": {
            "real": _obs_stats(real_frames),
            "sim": _obs_stats(sim_frames) if sim is not None else None,
        },
        "thresholds": {
            "min_swing_retention": MIN_SWING_RETENTION,
            "max_bias_over_swing": MAX_BIAS_RATIO,
            "min_right_fraction": MIN_RIGHT_FRACTION,
            "provisional": True,
        },
    }
    if args.output is not None:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def _line(tag: str, s: Optional[Dict[str, float]]) -> str:
        if s is None:
            return f"  {tag:26s} (not supplied)"
        return (
            f"  {tag:26s} n={s['n']:5d}  swing {s['swing']:.3f}  bias {s['bias']:+.4f}"
            f"  bias/swing {s['bias_over_swing']:5.2f}x  right {s['right_fraction']:5.1%}"
            f"  r2 {s['r_squared']:.3f}"
        )

    print(f"sim2real probe — {args.checkpoint.name}"
          f"{' (rectified)' if args.rectify else ''}")
    print(_line("sim control arm", sim))
    print(_line("physical (k=4 history)", real))
    print(_line("physical (repeat-stacked)", real_repeat))
    ph = report["observation_photometry"]
    for tag in ("sim", "real"):
        st = ph[tag]
        if st:
            print(f"  {tag + ' observation':26s} mean {st['mean']:5.1f}  sd {st['sd']:5.1f}"
                  f"  >200 {st['frac_above_200']:5.1%}  <60 {st['frac_below_60']:5.1%}")
    print(f"\n  VERDICT: {verdict}")
    for r in reasons:
        print(f"    - {r}")
    if verdict == "PASS":
        print("  (necessary, not sufficient: open-loop on recorded frames)")
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
