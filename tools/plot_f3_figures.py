#!/usr/bin/env python3
"""
plot_f3_figures — generate the Chapter 7 (F3) figures from the run artifacts.

Outputs (PNG, into --out, default manuscript/figures/auto/):
  * fig_7_1_convergence.png  — ep_rew_mean + ep_len_mean vs timesteps (raw +
    window-5 smoothing), from a training run's learning_curve.csv (§7.4.1).
  * fig_7_2_trajectory.png   — RL trajectory on the oval (exact, from x/y) with
    the PD baseline overlaid (reconstructed from its ey + speed-integrated arc
    length, since the F2 PD log has no world pose) and the lane centerline (§7.5).
  * fig_7_2b_tracking_error.png — |ey| vs lap fraction, RL vs PD: the spatial
    overlay cannot resolve the mm-scale tracking difference on an R=0.8 m oval,
    so this companion plot is where the RL-vs-PD precision gap is visible.

Pure post-processing of logged CSVs — no ROS / Gazebo. Run on any host with
numpy + matplotlib + pyyaml.

Usage:
  python tools/plot_f3_figures.py                 # auto-pick latest runs
  python tools/plot_f3_figures.py --rl-run <dir> --pd-run <dir> --train-run <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CENTERLINE = REPO / "src" / "cobraflex_rl" / "config" / "oval_right_lane_centerline.yaml"

# A saturating training run logs hundreds of learning-curve rows; an aborted
# stub has a handful. Require more than this many *data* rows before a training
# run is eligible for auto-selection (guards against picking a crashed run).
MIN_TRAIN_ROWS = 20


def _metadata_ok(run: Path) -> bool:
    """True if ``run/metadata.json`` exists and, if it carries a ``status``
    field, reports ``"completed"``. Runs with no metadata.json (e.g. a crashed
    training run) are rejected; runs whose metadata predates the status field
    (older ros_run logs) are accepted on metadata presence alone."""
    meta = run / "metadata.json"
    if not meta.is_file():
        return False
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    status = data.get("status")
    return status is None or status == "completed"


def _csv_row_count(path: Path) -> int:
    """Number of data rows (excluding the header) in a CSV, or 0 if absent."""
    if not path.is_file():
        return 0
    with path.open(newline="", encoding="utf-8") as h:
        return max(0, sum(1 for _ in h) - 1)


def _train_run_ok(run: Path) -> bool:
    """A training run is usable only if it completed (metadata) *and* logged a
    non-trivial learning curve — rejects the 5-row aborted-run footgun."""
    return _metadata_ok(run) and _csv_row_count(run / "learning_curve.csv") >= MIN_TRAIN_ROWS


def _latest(
    glob_dir: Path, pattern: str, ok: Optional[Callable[[Path], bool]] = None
) -> Optional[Path]:
    """Newest directory (by mtime) matching ``pattern`` that satisfies ``ok``.

    ``ok(path) -> bool`` filters out incomplete/aborted runs; the newest
    *eligible* run is returned, not merely the newest on disk. Without ``ok``
    the raw newest match is returned (legacy behaviour)."""
    hits = sorted(glob_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if ok is not None:
        hits = [h for h in hits if ok(h)]
    return hits[0] if hits else None


def _read_csv(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def _smooth(y: np.ndarray, w: int = 5) -> np.ndarray:
    """Centered moving average without edge pull-to-zero: divide the windowed sum
    by the actual number of samples in the window at each position (so the first
    and last points are not dragged toward 0 by zero-padding)."""
    if len(y) < w:
        return y
    k = np.ones(w)
    num = np.convolve(y, k, mode="same")
    den = np.convolve(np.ones_like(y, dtype=float), k, mode="same")
    return num / den


def _load_centerline() -> Tuple[np.ndarray, float]:
    cfg = yaml.safe_load(CENTERLINE.read_text(encoding="utf-8"))
    pts = np.asarray(cfg["centerline"]["points"], dtype=float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return pts, float(seg.sum())


def fig_convergence(train_run: Path, out: Path) -> None:
    rows = _read_csv(train_run / "learning_curve.csv")
    ts = np.array([float(r["timestep"]) for r in rows])
    rew = np.array([float(r["ep_rew_mean"]) for r in rows])
    elen = np.array([float(r["ep_len_mean"]) for r in rows])

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(ts, rew, color="#1f77b4", alpha=0.35, lw=1, label="ep_rew_mean (raw)")
    ax1.plot(ts, _smooth(rew), color="#1f77b4", lw=2, label="ep_rew_mean (smoothed, w=5)")
    ax1.set_xlabel("timesteps")
    ax1.set_ylabel("ep_rew_mean", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")

    ax2 = ax1.twinx()
    ax2.plot(ts, elen, color="#d62728", alpha=0.3, lw=1)
    ax2.plot(ts, _smooth(elen), color="#d62728", lw=2, label="ep_len_mean (smoothed)")
    ax2.set_ylabel("ep_len_mean (steps)", color="#d62728")
    ax2.tick_params(axis="y", labelcolor="#d62728")

    ax1.set_title("Fig. 7.1 — PPO convergence (run %s)" % train_run.name)
    fig.tight_layout()
    fig.savefig(out / "fig_7_1_convergence.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_7_1_convergence.png'}")


def _rl_series(rl_run: Path, dt: float = 0.1):
    """RL: exact world pose (x, y) + |ey| + cumulative arc length (cumsum v·dt)."""
    rows = _read_csv(rl_run / "cage_status.csv")
    x = np.array([float(r["x"]) for r in rows])
    y = np.array([float(r["y"]) for r in rows])
    ey = np.array([float(r["ey"]) for r in rows])
    spd = np.array([float(r["speed"]) for r in rows])
    cum_s = np.cumsum(spd * dt)
    return x, y, ey, cum_s


def _pd_series(pd_run: Path):
    """PD (F2 log): |ey| + cumulative arc length integrated from speed·dt.
    The F2 cage logger has no world pose, so only the tracking-error series is
    reconstructed (the spatial overlay would require x/y the log does not store)."""
    rows = _read_csv(pd_run / "cage_status.csv")
    if not rows or "ey" not in rows[0] or "speed" not in rows[0]:
        return None
    ey = np.array([float(r["ey"]) for r in rows])
    spd = np.array([float(r["speed"]) for r in rows])
    t = np.array([float(r["timestamp"]) for r in rows])
    dt = np.clip(np.diff(t, prepend=t[0]), 0.0, 0.5)
    cum_s = np.cumsum(spd * dt)
    return ey, cum_s


def fig_trajectory(rl_run: Path, pd_run: Optional[Path], out: Path, laps: float = 2.0) -> None:
    pts, perimeter = _load_centerline()
    rl_x, rl_y, rl_ey, rl_s = _rl_series(rl_run)

    # --- Fig 7.2: spatial trajectory (RL only — exact x/y; the PD log has no
    #     world pose and integrating its speed drifts over ~10 laps). ---
    n_rl = int(np.searchsorted(rl_s, laps * perimeter)) or len(rl_s)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    ax.plot(pts[:, 0], pts[:, 1], "--", color="0.6", lw=1, label="centerline (lane)")
    ax.plot(rl_x[:n_rl], rl_y[:n_rl], color="#1f77b4", lw=1.6, label="PPO (RL)")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"Fig. 7.2 — PPO trajectory on the oval (~{laps:g} laps)")
    ax.legend(loc="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_7_2_trajectory.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_7_2_trajectory.png'}")

    # --- Fig 7.2b: |ey| vs cumulative laps, RL vs PD (same v·dt integration for
    #     both, so the x-axis is consistent); warm-up (first 0.3 laps) trimmed. ---
    fig2, ax2 = plt.subplots(figsize=(7.5, 3.6))
    show_laps = max(3.0, laps)
    warm = 0.3

    def _plot(ax, ey, cum_s, color, label):
        lap = cum_s / perimeter
        m = (lap >= warm) & (lap <= warm + show_laps)
        ax.plot(lap[m] - warm, np.abs(ey[m]) * 1000, color=color, lw=1.0, label=label)

    _plot(ax2, rl_ey, rl_s, "#1f77b4", "PPO (RL)")
    pd = _pd_series(pd_run) if pd_run else None
    if pd is not None:
        pd_ey, pd_s = pd
        _plot(ax2, pd_ey, pd_s, "#d62728", "PD baseline")
    ax2.axhline(122, color="0.7", ls=":", lw=0.8)  # half-lane 122 mm
    ax2.text(0.02, 124, "half-lane 122 mm", fontsize=7, color="0.4")
    ax2.set_xlabel(f"laps (first {warm:g} lap warm-up trimmed)")
    ax2.set_ylabel("|ey| (mm)")
    ax2.set_title("Fig. 7.2b — Lateral tracking error: RL vs PD")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(out / "fig_7_2b_tracking_error.png", dpi=150)
    plt.close(fig2)
    print(f"  wrote {out/'fig_7_2b_tracking_error.png'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate F3 (Chapter 7) figures.")
    ap.add_argument("--train-run", type=Path, default=None)
    ap.add_argument("--rl-run", type=Path, default=None)
    ap.add_argument("--pd-run", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=REPO / "manuscript" / "figures" / "auto")
    ap.add_argument("--laps", type=float, default=2.0, help="laps to draw in Fig 7.2")
    args = ap.parse_args()

    train_dir = REPO / "experiments" / "sim" / "training"
    runs_dir = REPO / "experiments" / "sim" / "runs"
    train_run = args.train_run or _latest(train_dir, "ppo_train_*", _train_run_ok)
    rl_run = args.rl_run or _latest(runs_dir, "rl_eval_*", _metadata_ok)
    pd_run = args.pd_run or _latest(runs_dir, "ros_run_*", _metadata_ok)
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"train run: {train_run}\nRL eval  : {rl_run}\nPD run   : {pd_run}\nout      : {args.out}")
    if train_run:
        fig_convergence(train_run, args.out)
    if rl_run:
        fig_trajectory(rl_run, pd_run, args.out, laps=args.laps)


if __name__ == "__main__":
    main()
