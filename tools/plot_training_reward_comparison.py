#!/usr/bin/env python3
"""plot_training_reward_comparison — Figure 7.4: training reward of the three camera policies.

Reads the `learning_curve.csv` of each training run and draws the mean episode
reward against training steps for:

  * the reference policy, 2-D PPO with a 0.22 m/s cap (run ppo_gz2d_cap022_1M_2024),
    with the three checkpoints evaluated in closed loop marked and the selected
    one (550k) flagged;
  * the one-dimensional camera policy, E-main (run ppo_newcam_complex_b_2024_1M,
    steering only at a fixed 0.20 m/s), whose kept checkpoint is the 297k peak;
  * the off-policy 2-D variant, margin022 (run sac_gz2d_entfix_margin022_2024_75k).

The legend uses the labels defined in Table 7.1 of the manuscript. The earlier
version of this figure was rendered outside the repository and labelled the 1-D run
"verdict, cap ~0.5": it ran at a fixed 0.20 m/s, and since D-69 it is the G4 gate
record, not the verdict of record.

No in-image title: the manuscript caption carries it.

Usage:
    python tools/plot_training_reward_comparison.py
    python tools/plot_training_reward_comparison.py --out manuscript/figures/auto/fig_7_4_ppo2d_training_curve.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
TRAINING = REPO / "experiments" / "sim" / "training"
DEFAULT_OUT = REPO / "manuscript" / "figures" / "auto" / "fig_7_4_ppo2d_training_curve.png"

# (run directory, legend label, colour, line width)
SERIES = [
    ("ppo_gz2d_cap022_1M_2024", "2-D PPO, cap 0.22 m/s — reference policy", "#1f77b4", 2.0),
    ("ppo_newcam_complex_b_2024", "1-D PPO, fixed 0.20 m/s — E-main", "#e07b2a", 1.5),
    ("sac_gz2d_entfix_margin022_2024_75k", "2-D SAC, cap 0.22 m/s — margin022", "#8c8c8c", 1.5),
]
REFERENCE_CHECKPOINTS = (400_000, 475_000, 550_000)
SELECTED = 550_000
E_MAIN_KEPT = 297_000


def load(run: str) -> tuple[np.ndarray, np.ndarray]:
    with (TRAINING / run / "learning_curve.csv").open(newline="", encoding="utf-8") as h:
        rows = [r for r in csv.DictReader(h) if r["ep_rew_mean"] not in ("", "nan")]
    ts = np.array([float(r["timestep"]) for r in rows])
    rew = np.array([float(r["ep_rew_mean"]) for r in rows])
    return ts, rew


def smooth(y: np.ndarray, w: int = 5) -> np.ndarray:
    """Centred moving average, same window as tools/plot_f3_figures.py."""
    if len(y) < w:
        return y
    pad = w // 2
    padded = np.pad(y, (pad, pad), mode="edge")
    return np.convolve(padded, np.ones(w) / w, mode="valid")


def at(ts: np.ndarray, y: np.ndarray, step: float) -> tuple[float, float]:
    i = int(np.argmin(np.abs(ts - step)))
    return ts[i], y[i]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fig, ax = plt.subplots(figsize=(9.0, 5.0))
    curves = {}
    for run, label, colour, lw in SERIES:
        ts, rew = load(run)
        ys = smooth(rew)
        curves[run] = (ts, ys)
        ax.plot(ts / 1000, ys, color=colour, lw=lw, label=label)
        print(f"{run}: {len(ts)} points, last {ts[-1]:.0f}, raw peak {rew.max():.1f} "
              f"@ {ts[int(np.argmax(rew))]:.0f}")

    ts, ys = curves["ppo_gz2d_cap022_1M_2024"]
    for step in REFERENCE_CHECKPOINTS:
        x, y = at(ts, ys, step)
        chosen = step == SELECTED
        ax.plot(x / 1000, y, "o", ms=7 if chosen else 6, mfc="#1f77b4" if chosen else "white",
                mec="#0b3c61", mew=1.2, zorder=5)
        ax.annotate(f"{step // 1000}k" + (" (selected)" if chosen else ""), (x / 1000, y),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5)

    ts, ys = curves["ppo_newcam_complex_b_2024"]
    x, y = at(ts, ys, E_MAIN_KEPT)
    ax.plot(x / 1000, y, "o", ms=6, mfc="#e07b2a", mec="#7a3c0c", mew=1.2, zorder=5)
    ax.annotate("297k (kept)", (x / 1000, y), xytext=(0, 9), textcoords="offset points",
                ha="center", fontsize=8.5)

    ts, ys = curves["sac_gz2d_entfix_margin022_2024_75k"]
    ax.plot(ts[-1] / 1000, ys[-1], "o", ms=6, mfc="#8c8c8c", mec="#3d3d3d", mew=1.2, zorder=5)
    ax.annotate("75k", (ts[-1] / 1000, ys[-1]), xytext=(10, -2), textcoords="offset points",
                ha="left", va="center", fontsize=8.5)

    ax.set_xlabel("Training steps (×1000)")
    ax.set_ylabel("Mean episode reward (ep_rew_mean)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", fontsize=9, frameon=True)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150, facecolor="white")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
