#!/usr/bin/env python3
"""Rank a training run's checkpoints by *transfer*, not by reward (D-66/D-72).

A 2.5M-step run at ``checkpoint_freq: 25000`` leaves 100 candidates and the
reward curve does not order them. That is not a hunch: D-66's reward peak (475k)
was the *worst* driving candidate of its run, with 14 safety interventions and
max |ey| 49 mm against the chosen 550k's zero and 27 mm; and over the 19.08
sim-to-real fine-tune the reward recovered monotonically across its last 150k
steps while the sampled steering swing kept *shrinking*. Two independent runs,
same lesson. So this tool never reads the reward.

WHAT IT SCORES
Each checkpoint's **lane response** — how much its steering actually depends on
where the lane is — on the same Gazebo pose set seen through four photometric
and geometric conditions, using ``sim2real_probe``'s own scorer so the numbers
cannot drift from the gate:

    canonical        the render as trained. The control arm: it calibrates what
                     "working" means for this particular policy.
    hall             + the measured hall photometry (road grey 106 +/- 3 over a
                     1521-frame survey), which alone collapsed the 550k trunk
                     from swing 0.363 to 0.006.
    hall+lens        + the measured M-6 optics. What a deployment that forgets
                     to rectify actually sees.
    hall+lens+rect   + rectification. What the planned deployment sees, and
                     therefore the arm this tool ranks on.

THIS IS A PRE-FILTER, NOT THE GATE
Every arm above is a *surrogate*: real frames pushed through a transform, not a
recording of the real track. It shares the training run's own operator, so a
good score here is invariance to that operator and not evidence of transfer.
The gate is ``tools/sim2real_probe.py`` against the frames recorded on the
circuit, and this tool runs it too — but only when ``--real`` is given, and it
says so loudly when it is not. Ranking without ``--real`` narrows 100 candidates
to a handful worth carrying to the track; it does not authorise driving one.

Two further limits worth stating because they bound the numbers, not just the
prose. The distorted arms ask for scene content outside the canonical 90-degree
frustum, which the simulator never rendered, so they are pessimistic at the
frame edges by an amount nothing here can recover. And an open-loop probe on
recorded frames can *falsify* transfer but never establish it: the policy never
influences what it sees next.

Exit codes:
    0  at least one checkpoint cleared the ranking criteria
    1  INVALID inputs
    2  no checkpoint cleared them
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "src" / "cobraflex_rl"))

SCHEMA_VERSION = "sim2real-select/v1"

# apply_low_contrast level at which the render reproduces the measured hall.
HALL_LEVEL = 0.75
# Ranking floors, deliberately the probe's own gate thresholds so a checkpoint
# that tops this table is one that could plausibly clear the real gate.
MIN_RETENTION = 0.50
MAX_BIAS_RATIO = 1.00
MIN_RIGHT_FRACTION = 0.10

# Minimum swing on the CONTROL arm before a checkpoint is ranked at all.
#
# Found by running this tool on a partial 2.5M run: three of the top five were
# ranked there by a retention of 304 %, 231 % and 184 % — a ratio that cannot
# exceed 100 % by its own definition. It did because ``retention`` divides the
# degraded arm by the canonical one, and the canonical arm had collapsed (0.061,
# and 0.006 elsewhere). A near-zero denominator promotes exactly the checkpoints
# that respond least to the lane on the render they trained on.
#
# The failure is worse than a bad ordering. The single highest "retention" in
# that run belonged to the **25k** checkpoint, i.e. an almost untrained policy:
# a random policy's steering varies a great deal with its input, and swing does
# not distinguish that from a lane response. So the floor is not a tie-breaker,
# it is the filter that keeps noise out of the table.
MIN_CANONICAL_SWING = 0.15

# Minimum training ``ep_len_mean`` at a checkpoint's step for it to be ranked.
#
# The control-arm floor above keeps out checkpoints that respond too *weakly*.
# It does not keep out ones that respond too *noisily*: an almost untrained
# policy's steering varies a great deal with any input, and neither ``swing``
# nor ``r_squared`` distinguishes that from a lane response (measured: the 25k
# checkpoint reads r^2 0.282 on the deployment arm against 0.306 at 100k and
# 0.350 at 875k — no separation at all).
#
# What does distinguish them is not in the probe: it is whether the policy could
# complete an episode at the time. That is already recorded, per rollout, in the
# run's own ``learning_curve.csv``, and using it is not "ranking by reward" —
# D-66's lesson stands and the ordering below still never reads the reward. This
# only *excludes* checkpoints from an era when the policy was not driving. The
# default is the SC-NOM-01 campaign horizon, so a checkpoint that survives this
# filter could at least have finished the scenario it will be scored on.
MIN_TRAINING_EP_LEN = 300.0

_STEPS = re.compile(r"_(\d+)_steps\.zip$")


def _checkpoint_steps(path: Path) -> int:
    m = _STEPS.search(path.name)
    return int(m.group(1)) if m else -1


def episode_lengths(curves: Sequence[Path]) -> List[tuple]:
    """``[(timestep, ep_len_mean), ...]`` from one or more learning curves.

    Several curves because a run interrupted and resumed writes one per segment
    (the v2 run: a parent to 620,544 and an ``_r2`` continuation). They are one
    lineage and concatenate on the step axis.
    """
    out: List[tuple] = []
    for path in curves:
        if not path.is_file():
            continue
        with path.open() as fh:
            for row in csv.DictReader(fh):
                try:
                    out.append((float(row["timestep"]), float(row["ep_len_mean"])))
                except (KeyError, ValueError):
                    continue
    return sorted(out)


def ep_len_at(steps: int, lengths: Sequence[tuple]) -> Optional[float]:
    """Training ``ep_len_mean`` in force at a checkpoint's step (last value at or
    before it). ``None`` when the curves do not cover that step, which must not
    be read as a failure — an unknown is not a rejection."""
    best = None
    for timestep, value in lengths:
        if timestep <= steps:
            best = value
        else:
            break
    return best


def find_checkpoints(directory: Path, prefix: str, every: int) -> List[Path]:
    """Checkpoints for one run, ordered by step, optionally thinned."""
    found = sorted(
        (p for p in directory.glob(f"{prefix}_*_steps.zip") if _checkpoint_steps(p) > 0),
        key=_checkpoint_steps,
    )
    if every > 1:
        found = [p for p in found if (_checkpoint_steps(p) // 25000) % every == 0]
    return found


def build_arms(frames, calibration: Path, camera=None):
    """The four scoring conditions, as ``{name: [(frame_name, image), ...]}``."""
    import cv2

    from cobraflex_rl.camera_geometry import (
        CameraModel,
        distortion_maps_to_calibration,
        rectification_maps_from_calibration,
    )
    from cobraflex_rl.visual_degradation import apply_low_contrast

    cam = camera or CameraModel()
    fwd = distortion_maps_to_calibration(calibration, cam)
    rev = rectification_maps_from_calibration(calibration, cam)

    def lens(img):
        return cv2.remap(img, fwd[0], fwd[1], cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)

    def rect(img):
        return cv2.remap(img, rev[0], rev[1], cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REPLICATE)

    transforms = {
        "canonical": lambda im: im,
        "hall": lambda im: apply_low_contrast(im, HALL_LEVEL),
        "hall+lens": lambda im: lens(apply_low_contrast(im, HALL_LEVEL)),
        "hall+lens+rect": lambda im: rect(lens(apply_low_contrast(im, HALL_LEVEL))),
    }
    return {k: [(n, f(im)) for n, im in frames] for k, f in transforms.items()}


def score_checkpoint(path: Path, arm_frames, labels, device: str) -> Dict:
    from stable_baselines3 import PPO, SAC

    import sim2real_probe as probe

    try:
        model = PPO.load(str(path), device=device)
    except Exception:  # noqa: BLE001 - a SAC checkpoint is a legitimate input
        model = SAC.load(str(path), device=device)

    arms: Dict[str, Optional[Dict]] = {}
    for name, frames in arm_frames.items():
        arms[name] = probe._run_arm(model, frames, labels, "repeat")
    base = arms.get("canonical")
    for name, s in arms.items():
        if s is not None and base is not None and base["swing"] > 1e-9:
            s["retention_vs_canonical"] = s["swing"] / base["swing"]
    return {"checkpoint": path.name, "steps": _checkpoint_steps(path), "arms": arms}


def rank_key(record: Dict, arm: str):
    """Order: responsive-on-the-control-arm, then gate-clearing, then by the
    ABSOLUTE swing on the deployment arm.

    Three terms, each answering a way the ranking was observed to go wrong:

    ``responsive``  the control arm must clear ``MIN_CANONICAL_SWING``. Without
                    it, ``retention`` divides by a collapsed denominator and
                    promotes the least responsive checkpoints — and the most
                    extreme case was a 25k checkpoint whose "response" was an
                    untrained policy's noise.
    ``cleared``     the probe's own gate criteria.
    ``swing``       absolute, not retention. Retention answers "how much of its
                    own response survived", which is the right question for the
                    *real* probe where the sim arm calibrates a working policy;
                    it is the wrong question here, where both arms come from the
                    same checkpoint and a small denominator flatters a weak one.
                    Retention is still reported, because the *drop* from
                    canonical to deployment is informative — it just must not
                    order the table.

    A checkpoint that steers the WRONG WAY is never ranked above one that steers
    the right way weakly, whatever its magnitude — hence sign inside ``cleared``
    and as its own guard below.
    """
    s = record["arms"].get(arm)
    if s is None or not s.get("sign_correct", False):
        return (0, 0, 0.0)
    canonical = record["arms"].get("canonical") or {}
    ep_len = record.get("training_ep_len")
    drove = ep_len is None or float(ep_len) >= MIN_TRAINING_EP_LEN
    responsive = drove and float(canonical.get("swing", 0.0)) >= MIN_CANONICAL_SWING
    cleared = (
        responsive
        and s.get("retention_vs_canonical", 0.0) >= MIN_RETENTION
        and s.get("bias_over_swing", float("inf")) <= MAX_BIAS_RATIO
        and s.get("right_fraction", 0.0) >= MIN_RIGHT_FRACTION
    )
    return (int(responsive), int(cleared), float(s.get("swing", 0.0)))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--checkpoint-dir", type=Path,
                   default=REPO_ROOT / "policy" / "checkpoints")
    p.add_argument("--prefix", required=True,
                   help="run_id prefix, e.g. ppo_gz2d_sim2real_v2_2024")
    p.add_argument("--sim-frames", type=Path, required=True,
                   help="Gazebo frames with the pose in the filename "
                        "(…ey+0.000_dpsi+0.00.png)")
    p.add_argument("--real", type=Path, default=None,
                   help="physical dataset root (frames/ + labels.csv). Without "
                        "it this ranks on the surrogate arms only and CANNOT "
                        "authorise a deployment.")
    p.add_argument("--calibration", type=Path,
                   default=REPO_ROOT / "experiments" / "calibration" / "M6_results.json")
    p.add_argument("--arm", default="hall+lens+rect",
                   help="arm to rank on (default: the planned deployment's)")
    p.add_argument("--learning-curve", type=Path, action="append", default=None,
                   help="run learning_curve.csv, repeatable (a resumed run has "
                        "one per segment). Checkpoints from an era whose "
                        "ep_len_mean was below MIN_TRAINING_EP_LEN are excluded "
                        "as non-drivers. Omit and no such filter is applied.")
    p.add_argument("--every", type=int, default=1,
                   help="score every Nth 25k checkpoint (1 = all)")
    p.add_argument("--stride", type=int, default=1, help="frame subsampling")
    p.add_argument("--top", type=int, default=5, help="how many to carry forward")
    p.add_argument("--device", default="cpu")
    p.add_argument("--output", type=Path, default=None)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    import sim2real_probe as probe

    checkpoints = find_checkpoints(args.checkpoint_dir, args.prefix, args.every)
    if not checkpoints:
        print(f"INVALID: no checkpoints matching {args.prefix}_*_steps.zip in "
              f"{args.checkpoint_dir}", file=sys.stderr)
        return 1
    if not args.sim_frames.is_dir():
        print(f"INVALID: --sim-frames not a directory: {args.sim_frames}",
              file=sys.stderr)
        return 1

    frames = probe._load_frames(args.sim_frames, args.stride, False)
    labels = probe._sim_labels([Path(n) for n, _ in frames], True)
    if len(labels) < probe.MIN_FRAMES:
        print(f"INVALID: only {len(labels)} zero-heading labelled frames in "
              f"{args.sim_frames} (need {probe.MIN_FRAMES})", file=sys.stderr)
        return 1
    arm_frames = build_arms(frames, args.calibration)
    lengths = episode_lengths(args.learning_curve or [])
    if args.learning_curve and not lengths:
        print("INVALID: --learning-curve given but no usable rows were read",
              file=sys.stderr)
        return 1

    print(f"scoring {len(checkpoints)} checkpoints on {len(labels)} labelled frames "
          f"x {len(arm_frames)} arms  (ranking arm: {args.arm})\n")
    records = []
    for i, path in enumerate(checkpoints, 1):
        rec = score_checkpoint(path, arm_frames, labels, args.device)
        if lengths:
            rec["training_ep_len"] = ep_len_at(rec["steps"], lengths)
        records.append(rec)
        cells = []
        for name in arm_frames:
            s = rec["arms"][name]
            cells.append("   n/a" if s is None else f"{s['swing']:6.3f}")
        print(f"  [{i:3d}/{len(checkpoints)}] {rec['steps']:>8d} steps  "
              + "  ".join(f"{n} {c}" for n, c in zip(arm_frames, cells)))

    records.sort(key=lambda r: rank_key(r, args.arm), reverse=True)
    top = records[: args.top]

    print(f"\n{'rank':>4} {'steps':>9} {'swing':>7} {'retention':>10} "
          f"{'bias/swing':>11} {'right':>7} {'sign':>6} {'ep_len':>7}   "
          f"(arm: {args.arm})")
    for i, rec in enumerate(top, 1):
        s = rec["arms"].get(args.arm)
        if s is None:
            print(f"{i:>4} {rec['steps']:>9} {'no lane response scored':>44}")
            continue
        ep = rec.get("training_ep_len")
        ep_txt = "  n/a" if ep is None else f"{ep:7.0f}"
        print(f"{i:>4} {rec['steps']:>9} {s['swing']:>7.3f} "
              f"{s.get('retention_vs_canonical', float('nan')):>9.0%} "
              f"{s['bias_over_swing']:>11.2f} {s['right_fraction']:>6.1%} "
              f"{'ok' if s['sign_correct'] else 'WRONG':>6} {ep_txt}")

    cleared = [r for r in records if rank_key(r, args.arm)[1] == 1]
    unresponsive = [r for r in records if rank_key(r, args.arm)[0] == 0]
    print(f"\n{len(cleared)} of {len(records)} checkpoints clear the ranking floors "
          f"(canonical swing >= {MIN_CANONICAL_SWING:.2f}, retention >= "
          f"{MIN_RETENTION:.0%}, bias/swing <= {MAX_BIAS_RATIO:.2f}, right >= "
          f"{MIN_RIGHT_FRACTION:.0%}).")
    if unresponsive:
        print(f"{len(unresponsive)} were dropped for responding too weakly on the "
              f"control arm, with the wrong sign, or from a training era whose "
              f"ep_len_mean was under {MIN_TRAINING_EP_LEN:.0f} steps.")
    if not lengths:
        print("NOTE: no --learning-curve given, so nothing filters out "
              "checkpoints from an era when the policy could not finish an "
              "episode. Their steering is noisy, not lane-driven, and both "
              "swing and r_squared rate them highly.")
    print("\nSWING IS NOT DRIVING. An untrained policy scores a large swing because "
          "its steering is noisy, and this probe is open-loop on recorded frames. "
          "Cross-check the shortlist with an SC-NOM-01 nominal drive before the "
          "track — a checkpoint that transfers but cannot drive is not a candidate.")

    gate: Dict[str, Dict] = {}
    if args.real is not None:
        print(f"\nrunning the REAL gate (sim2real_probe) on the top {len(top)}:")
        for rec in top:
            path = args.checkpoint_dir / rec["checkpoint"]
            rc = probe.main([
                "--checkpoint", str(path), "--real", str(args.real),
                "--sim", str(args.sim_frames), "--device", args.device,
                "--stride", str(args.stride),
            ])
            gate[rec["checkpoint"]] = {"exit_code": rc,
                                       "verdict": {0: "PASS", 1: "INVALID",
                                                   2: "BLOCKED"}.get(rc, "?")}
    else:
        print("\n*** NO --real GIVEN: these are SURROGATE arms. The gate is "
              "sim2real_probe against the frames recorded on the circuit, and it "
              "has NOT been run. This ranking narrows the field; it does not "
              "authorise driving any of them. ***")

    report = {
        "schema": SCHEMA_VERSION,
        "prefix": args.prefix,
        "ranking_arm": args.arm,
        "hall_level": HALL_LEVEL,
        "floors": {"min_retention": MIN_RETENTION,
                   "max_bias_over_swing": MAX_BIAS_RATIO,
                   "min_right_fraction": MIN_RIGHT_FRACTION,
                   "provisional": True},
        "real_gate_run": args.real is not None,
        "real_gate": gate,
        "ranked": records,
    }
    if args.output is not None:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nreport: {args.output}")
    return 0 if cleared else 2


if __name__ == "__main__":
    raise SystemExit(main())
