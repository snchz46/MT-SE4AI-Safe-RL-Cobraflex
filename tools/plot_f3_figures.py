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
  * fig_7_4_intervention.png — cage intervention + C-05 emergency rate vs
    timesteps and the per-rule breakdown: the co-adaptation evidence (plan
    §11.1 Fig. 2/3).
  * fig_7_5_ppo_health.png — PPO value loss + policy entropy vs timesteps
    (plan §11.1 Fig. 5).
  * fig_7_6_action_distribution.png — policy raw-steering histogram, early vs
    late training (plan §11.1 Fig. 6).

The 7.4/7.5/7.6 figures need a training run produced with the extended logger
(cobraflex_rl/callbacks.py + training_metrics.py: the cage-rate columns and
action_samples.csv). On a legacy 4-column run they are skipped with a note,
while 7.1/7.2/7.2b still render.

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


# Canonical cage rule IDs (mirrors cobraflex_rl.training_metrics.CAGE_RULES;
# duplicated so this pure post-processing tool needs no src/ import).
CAGE_RULES = ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06")


def _has_columns(rows: List[dict], cols) -> bool:
    return bool(rows) and all(c in rows[0] for c in cols)


def _col(rows: List[dict], name: str) -> np.ndarray:
    return np.array([float(r[name]) for r in rows], dtype=float)


def fig_intervention(train_run: Path, out: Path) -> None:
    """Fig. 7.4 — cage intervention + C-05 emergency rate vs timesteps (top) and
    the per-rule breakdown (bottom): the co-adaptation evidence (plan §11.1
    Fig. 2/3). Requires a run logged with the extended schema; skipped (with a
    note) on a legacy 4-column learning_curve.csv."""
    rows = _read_csv(train_run / "learning_curve.csv")
    if not _has_columns(rows, ["intervention_rate"]):
        print("  skip fig_7_4_intervention (no cage columns; re-train with the extended logger)")
        return
    ts = _col(rows, "timestep")
    rate = _col(rows, "intervention_rate") * 100.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax1.plot(ts, rate, color="#9467bd", alpha=0.35, lw=1)
    ax1.plot(ts, _smooth(rate), color="#9467bd", lw=2, label="cage intervention rate")
    if "emergency_rate" in rows[0]:
        emerg = _col(rows, "emergency_rate") * 100.0
        ax1.plot(ts, _smooth(emerg), color="#d62728", lw=1.5, ls="--",
                 label="C-05 emergency rate")
    ax1.set_ylabel("% of steps")
    ax1.set_title("Fig. 7.4 — Cage activity during training (run %s)" % train_run.name)
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    plotted = 0
    for rule in CAGE_RULES:
        col = f"int_rate_{rule}"
        if col in rows[0]:
            series = _col(rows, col) * 100.0
            if np.nanmax(series) > 1e-9:
                ax2.plot(ts, _smooth(series), lw=1.5, label=rule)
                plotted += 1
    if plotted == 0:
        ax2.text(0.5, 0.5, "no per-rule interventions logged\n(cage stayed latent in nominal)",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=9, color="0.4")
    else:
        ax2.legend(fontsize=8, ncol=3)
    ax2.set_xlabel("timesteps")
    ax2.set_ylabel("% of steps (per rule)")
    ax2.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "fig_7_4_intervention.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_7_4_intervention.png'}")


def fig_ppo_health(train_run: Path, out: Path) -> None:
    """Fig. 7.5 — PPO value loss + policy entropy vs timesteps (plan §11.1
    Fig. 5). Requires the extended schema; skipped otherwise."""
    rows = _read_csv(train_run / "learning_curve.csv")
    if not _has_columns(rows, ["value_loss", "entropy"]):
        print("  skip fig_7_5_ppo_health (no value_loss/entropy columns; re-train with the extended logger)")
        return
    ts = _col(rows, "timestep")
    vloss = _col(rows, "value_loss")
    entropy = _col(rows, "entropy")

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(ts, vloss, color="#1f77b4", alpha=0.3, lw=1)
    ax1.plot(ts, _smooth(vloss), color="#1f77b4", lw=2, label="value loss")
    ax1.set_xlabel("timesteps")
    ax1.set_ylabel("value loss", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")

    ax2 = ax1.twinx()
    ax2.plot(ts, entropy, color="#ff7f0e", alpha=0.3, lw=1)
    ax2.plot(ts, _smooth(entropy), color="#ff7f0e", lw=2, label="policy entropy")
    ax2.set_ylabel("policy entropy", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")

    ax1.set_title("Fig. 7.5 — PPO health: value loss & entropy (run %s)" % train_run.name)
    fig.tight_layout()
    fig.savefig(out / "fig_7_5_ppo_health.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_7_5_ppo_health.png'}")


def fig_action_distribution(train_run: Path, out: Path, frac: float = 0.1) -> None:
    """Fig. 7.6 — policy raw-steering distribution at the start vs the end of
    training (plan §11.1 Fig. 6), from the subsampled action_samples.csv.
    Skipped if that file is absent."""
    path = train_run / "action_samples.csv"
    if not path.is_file():
        print("  skip fig_7_6_action_distribution (no action_samples.csv; re-train with the extended logger)")
        return
    rows = _read_csv(path)
    if not _has_columns(rows, ["timestep", "raw_steer"]):
        print("  skip fig_7_6_action_distribution (action_samples.csv missing columns)")
        return
    ts = _col(rows, "timestep")
    steer = _col(rows, "raw_steer")
    tmax = ts.max() if len(ts) else 0.0
    early = steer[ts <= frac * tmax]
    late = steer[ts >= (1.0 - frac) * tmax]

    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(-1.0, 1.0, 41)
    if len(early):
        ax.hist(early, bins=bins, density=True, alpha=0.5, color="#1f77b4",
                label=f"early (first {frac:.0%} of steps)")
    if len(late):
        ax.hist(late, bins=bins, density=True, alpha=0.5, color="#d62728",
                label=f"late (last {frac:.0%} of steps)")
    ax.set_xlabel("raw policy steering")
    ax.set_ylabel("density")
    ax.set_title("Fig. 7.6 — Policy action distribution: early vs late training")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "fig_7_6_action_distribution.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_7_6_action_distribution.png'}")


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
        fig_intervention(train_run, args.out)
        fig_ppo_health(train_run, args.out)
        fig_action_distribution(train_run, args.out)
    if rl_run:
        fig_trajectory(rl_run, pd_run, args.out, laps=args.laps)


if __name__ == "__main__":
    main()
