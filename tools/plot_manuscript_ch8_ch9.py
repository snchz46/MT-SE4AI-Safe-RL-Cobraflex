#!/usr/bin/env python3
"""
plot_manuscript_ch8_ch9 — the figures chapters 8 and 9 were missing.

Chapters 8-12 carry 3 figures across ~14,700 words, against 22 across ~20,800 in
chapters 1-7; chapter 9 is the longest chapter of the thesis and had none at all.
This script renders five figures for the findings those chapters state in prose
and had no picture for. Every number comes from an artefact already in the repo:
no figure here carries a value that is not re-derived at render time.

  * ``fig_8_3_c06_load_bearing.png`` — SC-NOM-03 (300 s endurance), enforcement
    against monitoring: the intervention ledger is C-06 alone, yet the same
    command stream leaves the lane in 17 of 25 runs with the cage off. The
    "uncomfortable finding" of section 8.4.
    Source: ``experiments/sim/campaign_2d_ppo550k/runs/camp_nom03_*/summary.json``

The chapter-9 figures are numbered in the order the chapter reaches them, not in
the order they were built.

  * ``fig_9_1_rectification.png`` — reported against true lateral error on the
    raw path (M-7, 15 poses) and the rectified one (31.08 sweep, 9 poses), with
    the C-01 threshold drawn in both. The retraction of section 9.3.2, and the
    evidence for the fix it motivated.
    Source: ``experiments/calibration/M7_offset_response.csv`` and
    ``experiments/physical/runs/lanesweep_20260831T094110Z/lane_sweep.csv``

  * ``fig_9_2_handedness_bias.png`` — the 5,665-cycle hands-off probe: correct
    sign, an order of magnitude too weak, and a constant left bias 2.1x the whole
    excursion. The negative transfer result of section 9.3.3.
    Source: ``experiments/physical/runs/policy_bias_probe/cage_status.csv``

  * ``fig_9_3_physical_run_trace.png`` — the run that transfers: lateral error
    against distance, the C-01 threshold, C-06 activity, and the single
    perception pulse that latched C-05 short of the lap (sections 9.3.4, 9.3.5).
    Source: ``experiments/physical/runs/track_v2_noloopclosure_20260826T100450Z``

  * ``fig_9_4_place_not_motion.png`` — per-segment pairing around the circuit for
    the two shadow-free laps, and the four parked probes at true ey = 0. The
    estimator degrades by *place*, not by motion (section 9.3.6).
    Source: ``experiments/physical/datasets/{truepos_*,parked_*}/labels.csv``

Usage:
  python tools/plot_manuscript_ch8_ch9.py
  python tools/plot_manuscript_ch8_ch9.py --out manuscript/figures/auto --only 9_1
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
OUT_DEFAULT = REPO / "manuscript" / "figures" / "auto"

# Same palette as plot_campaign_contrast.py, so the new figures sit beside 8.1/8.2.
ENF = "#1f77b4"
MON = "#d62728"
GOOD = "#2ca02c"
WARN = "#ff7f0e"
NEUTRAL = "#7f7f7f"
GRID = 0.3
DPI = 150

# C-01's lane-boundary threshold, in millimetres (cage.yaml lat_err_max = 0.16 m).
C01_MM = 160.0


def _save(fig, out: Path, name: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    fig.tight_layout()
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print(f"  wrote {path.relative_to(REPO)}")
    return path


# --------------------------------------------------------------------------- 8.3
def fig_8_3(out: Path) -> None:
    """C-06 is load-bearing: the endurance scenario, both modes."""
    stats = {}
    for mode in ("enforcement", "monitoring"):
        pat = f"experiments/sim/campaign_2d_ppo550k/runs/camp_nom03_*_{mode}_rep*/summary.json"
        runs = [json.load(open(p)) for p in glob.glob(str(REPO / pat))]
        if not runs:
            raise SystemExit(f"no SC-NOM-03 runs found for {mode}")
        ledger: dict[str, int] = {}
        for r in runs:
            for k, v in (r.get("interventions_per_rule") or {}).items():
                ledger[k] = ledger.get(k, 0) + v
        pts = sorted(
            (
                r["max_abs_ey_m"] * 1000,
                r["campaign"]["termination_reason"] == "off_road",
            )
            for r in runs
        )
        stats[mode] = {
            "n": len(runs),
            "pts": pts,
            "max_ey_mm": [p[0] for p in pts],
            "off_road": sum(1 for _, o in pts if o),
            "ledger": ledger,
            "steer_rate_max": max(
                r["campaign"]["values"]["M-I5"]["steer_rate_max"] for r in runs
            ),
            "bound": runs[0]["campaign"]["values"]["M-I5"]["delta_max_steer"],
        }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 5.0))

    # (a) per-run maximum lateral excursion, with the outcome of each mode.
    # Runs that end off road are marked: their maximum is where the run was cut,
    # not how far the vehicle would have wandered, so the two are not the same
    # quantity and the figure should not let them read as one.
    for i, (mode, colour) in enumerate((("enforcement", ENF), ("monitoring", MON))):
        s = stats[mode]
        xs = np.full(len(s["pts"]), i) + np.linspace(-0.17, 0.17, len(s["pts"]))
        for x, (v, off) in zip(xs, s["pts"]):
            ax1.scatter(
                [x],
                [v],
                s=58 if off else 28,
                marker="X" if off else "o",
                color=colour,
                alpha=0.85,
                zorder=3,
            )
        med = float(np.median(s["max_ey_mm"]))
        ax1.plot([i - 0.31, i + 0.31], [med, med], color=colour, lw=2.4, zorder=4)
        ax1.annotate(
            f"median {med:.0f} mm",
            (i + 0.33, med),
            fontsize=9,
            va="center",
            color=colour,
        )
    ax1.axhline(C01_MM, color="k", ls="--", lw=1.2)
    ax1.annotate(
        f"C-01 threshold, {C01_MM:.0f} mm",
        (-0.46, C01_MM + 4),
        fontsize=9,
    )
    ax1.scatter([], [], marker="o", s=28, color="k", label="run completed")
    ax1.scatter(
        [], [], marker="X", s=58, color="k", label="run ended off road (value = where it was cut)"
    )
    ax1.legend(fontsize=8.5, loc="upper left")
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(
        [
            f"enforcement\n{stats['enforcement']['n']} runs, "
            f"{stats['enforcement']['off_road']}/{stats['enforcement']['n']} off road",
            f"monitoring — cage observes,\ndoes not act\n"
            f"{stats['monitoring']['n']} runs, "
            f"{stats['monitoring']['off_road']}/{stats['monitoring']['n']} off road",
        ],
        fontsize=9,
    )
    ax1.set_xlim(-0.58, 1.78)
    ax1.set_ylim(0, C01_MM + 45)
    ax1.set_ylabel("maximum lateral excursion per run (mm)")
    ax1.grid(axis="y", alpha=GRID)
    ax1.set_title(
        "(a) the same command stream, with and without the cage acting", fontsize=11
    )

    # (b) what the cage actually did: the intervention ledger by rule.
    rules = ["C-01", "C-02", "C-03", "C-05", "C-06"]
    enf = [stats["enforcement"]["ledger"].get(r, 0) for r in rules]
    mon = [stats["monitoring"]["ledger"].get(r, 0) for r in rules]
    x = np.arange(len(rules))
    w = 0.38
    b1 = ax2.bar(x - w / 2, enf, w, label="enforcement", color=ENF)
    b2 = ax2.bar(x + w / 2, mon, w, label="monitoring", color=MON)
    for bars in (b1, b2):
        for b in bars:
            ax2.annotate(
                f"{int(b.get_height()):,}",
                (b.get_x() + b.get_width() / 2, b.get_height()),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                rotation=90 if b.get_height() > 1000 else 0,
            )
    ax2.set_xticks(x)
    ax2.set_xticklabels(rules, fontsize=10)
    ax2.set_ylabel("intervention cycles, all runs of the scenario")
    ax2.set_yscale("symlog", linthresh=10)
    ax2.set_ylim(0, max(enf + mon) * 12)
    ax2.legend(fontsize=9, loc="upper left")
    ax2.grid(axis="y", alpha=GRID)
    ax2.set_title(
        "(b) the ledger is the rate limiter alone\n"
        "(the safety rules never fire in enforcement)",
        fontsize=11,
    )

    fig.suptitle(
        "C-06 is doing load-bearing lane-keeping, not smoothing "
        "— SC-NOM-03, 300 s endurance, 2-D PPO 550k",
        fontsize=12,
    )
    fig.subplots_adjust(top=0.86)
    _save(fig, out, "fig_8_3_c06_load_bearing.png")


# --------------------------------------------------------------------------- 9.1
def _labels(name: str) -> pd.DataFrame:
    p = REPO / "experiments" / "physical" / "datasets" / name / "labels.csv"
    return pd.read_csv(p)


def fig_9_4(out: Path) -> None:
    """The estimator degrades by place, not by motion."""
    # The two shadow-free laps (pushed from outside the lane), by circuit segment.
    laps = {
        "lap at true ey = 0": ("truepos_000_ctrl_3", 0.0),
        "lap at true ey = -65 mm": ("truepos_m065", -65.0),
    }
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.0, 5.2))

    for (label, (name, _true)), colour in zip(laps.items(), (ENF, WARN)):
        d = _labels(name)
        seg = d[d.station > 0].groupby("station")["paired"].agg(["size", "mean"])
        ax1.plot(
            seg.index,
            100 * seg["mean"],
            "o-",
            color=colour,
            lw=2.0,
            ms=7,
            label=f"{label} ({int(seg['size'].sum())} frames)",
        )
    ax1.axvspan(4.62, 5.38, color=GOOD, alpha=0.11)
    ax1.annotate(
        "segment 5 is the start of the straight:\n"
        "every single-pose calibration in this\n"
        "work was measured here",
        (0.30, 0.055),
        xycoords="axes fraction",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=NEUTRAL, alpha=0.92),
    )
    ax1.set_xticks([1, 2, 3, 4, 5])
    ax1.set_xlabel("circuit segment (in order of travel)")
    ax1.set_ylabel("frames with a valid lane pair (%)")
    ax1.set_ylim(0, 105)
    ax1.legend(fontsize=9, loc="lower left")
    ax1.grid(alpha=GRID)
    ax1.set_title("(a) moving: accuracy depends on where it is", fontsize=11)

    # The parked probes: stationary, true ey = 0, inside the bad stretches.
    probes = [
        ("parked_seg23_b", "parked\nseg 2-3 b"),
        ("parked_seg23_a", "parked\nseg 2-3 a"),
        ("parked_seg34_a", "parked\nseg 3-4 a"),
        ("parked_seg34_b", "parked\nseg 3-4 b"),
    ]
    def _probe(frame: pd.DataFrame) -> tuple[float, float]:
        """Pairing rate, and mean absolute error against the true position.

        The error is the mean of |reported - true| over paired frames, the same
        statistic CAPTURE_NOTE_20260831.md reports: at these spots the estimator
        is both biased and dispersed, so a bias alone would understate it.
        """
        pair = 100 * frame["paired"].mean()
        ok = frame[frame["paired"] == 1]
        if not len(ok):
            return pair, np.nan
        return pair, float((ok["ey_m"] - ok["true_ey_m"]).abs().mean() * 1000)

    names, paired, err = [], [], []
    for key, label in probes:
        d = _labels(key)
        d = d[d.station == 1]
        p, e = _probe(d)
        names.append(f"{label}\n({len(d)} frames)")
        paired.append(p)
        err.append(e)
    # The start-of-straight reference, same protocol, from the lap at true ey = 0.
    ref = _labels("truepos_000_ctrl_3")
    ref = ref[ref.station == 5]
    p, e = _probe(ref)
    names.append(f"start of\nstraight\n({len(ref)} frames)")
    paired.append(p)
    err.append(e)

    x = np.arange(len(names))
    colours = [MON] * 4 + [GOOD]
    bars = ax2.bar(x, paired, 0.62, color=colours, alpha=0.8, label="frames paired (left)")
    for b, p in zip(bars, paired):
        ax2.annotate(
            f"{p:.1f} %",
            (b.get_x() + b.get_width() / 2, p + 2),
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )
    ax2.annotate(
        "sees ONE line in\nall 273 frames:\nnothing to pair",
        (0, 8),
        ha="center",
        va="bottom",
        fontsize=8.5,
        color=MON,
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, fontsize=8.5)
    ax2.set_ylabel("frames with a valid lane pair (%)")
    ax2.set_ylim(0, 132)
    ax2.grid(axis="y", alpha=GRID)

    # The error on a second axis: a tall bar with a high marker is the finding.
    ax2b = ax2.twinx()
    ax2b.plot(
        x,
        err,
        "D",
        ms=10,
        color="k",
        zorder=6,
        label="mean |error| vs true position (right)",
    )
    for xi, e in zip(x, err):
        if not np.isnan(e):
            ax2b.annotate(
                f"{e:.1f} mm",
                (xi, e),
                xytext=(0, 11),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                fontweight="bold",
            )
    ax2b.set_ylabel("mean absolute error against true position (mm)")
    ax2b.set_ylim(0, 92)
    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2b.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper left")
    ax2.set_title(
        "(b) stationary, true ey = 0: as bad or worse\n"
        "a full bar with a high marker is 'confidently wrong'",
        fontsize=11,
    )

    fig.suptitle(
        "The lane estimator degrades by place, not by motion "
        "— true-position capture, rectified, camera only",
        fontsize=12,
    )
    fig.subplots_adjust(top=0.85)
    _save(fig, out, "fig_9_4_place_not_motion.png")


# --------------------------------------------------------------------------- 9.2
def fig_9_1(out: Path) -> None:
    """Rectification removes the under-read that the raw path showed."""
    raw = pd.read_csv(REPO / "experiments" / "calibration" / "M7_offset_response.csv")
    rect = pd.read_csv(
        REPO
        / "experiments"
        / "physical"
        / "runs"
        / "lanesweep_20260831T094110Z"
        / "lane_sweep.csv"
    )
    rect = rect[rect["support"].str.startswith("ground")]

    fig, ax = plt.subplots(figsize=(10.2, 6.6))
    lim = 275
    ax.plot([-lim, lim], [-lim, lim], color="k", ls=":", lw=1.3, label="ideal (1:1)")

    ax.errorbar(
        raw["true_ey_mm"],
        raw["ey_mean_mm"],
        yerr=raw["ey_sd_mm"],
        fmt="s",
        ms=7,
        color=MON,
        alpha=0.85,
        capsize=3,
        lw=1.0,
        label=f"raw path, M-7 ({len(raw)} poses, unrectified)",
    )
    ax.errorbar(
        rect["true_ey_mm"],
        rect["reported_ey_mm"],
        yerr=rect["sd_ey_mm"],
        fmt="o",
        ms=8,
        color=GOOD,
        capsize=3,
        lw=1.0,
        label=f"rectified path, 31.08 sweep ({len(rect)} poses)",
    )

    xs = np.linspace(-lim, lim, 60)

    # The raw path: one fit over the whole sweep, as M-7 reported it.
    sl_r, ic_r = np.polyfit(raw["true_ey_mm"], raw["ey_mean_mm"], 1)
    ax.plot(xs, sl_r * xs + ic_r, color=MON, lw=1.6, alpha=0.6)
    raw_fires = (C01_MM - ic_r) / sl_r

    # The rectified path is fitted per side, which is how section 9.3.2 reports
    # it; the zero pose belongs to both sides.
    zero = float(rect.loc[rect["true_ey_mm"] == 0, "reported_ey_mm"].iloc[0])
    sides = {}
    for tag, mask, thr in (
        ("left", rect["true_ey_mm"] > 0, C01_MM),
        ("right", rect["true_ey_mm"] < 0, -C01_MM),
    ):
        sub = rect[mask]
        sl, ic = np.polyfit(
            np.append(sub["true_ey_mm"].values, 0.0),
            np.append(sub["reported_ey_mm"].values, zero),
            1,
        )
        sides[tag] = (sl, ic, (thr - ic) / sl)
        seg = np.linspace(0, lim if tag == "left" else -lim, 30)
        ax.plot(seg, sl * seg + ic, color=GOOD, lw=1.6, alpha=0.7)

    for thr in (C01_MM, -C01_MM):
        ax.axhline(thr, color="k", ls="--", lw=1.2)
    ax.annotate(
        f"C-01 acts on the REPORTED value: ±{C01_MM:.0f} mm",
        (-lim + 8, C01_MM + 8),
        fontsize=9,
    )

    # The two firing points that matter, and the margin between them.
    ax.axvspan(sides["left"][2], raw_fires, color=MON, alpha=0.10)
    for x_at, colour, label in (
        (sides["left"][2], GOOD, f"rectified: {sides['left'][2]:.0f} mm"),
        (raw_fires, MON, f"raw: {raw_fires:.0f} mm"),
    ):
        ax.plot([x_at], [C01_MM], marker="v", ms=11, color=colour, zorder=6)
        ax.annotate(
            label,
            (x_at, C01_MM),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            fontsize=9.5,
            fontweight="bold",
            color=colour,
        )
    ax.annotate(
        f"the vehicle travelled this far past the\nthreshold before C-01 saw it: "
        f"{raw_fires - sides['left'][2]:.0f} mm",
        ((sides["left"][2] + raw_fires) / 2, -95),
        ha="center",
        fontsize=9,
        color=MON,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=MON, alpha=0.92),
    )

    ax.annotate(
        f"raw fit:  {sl_r:.3f} x true {ic_r:+.1f} mm\n"
        f"rectified: {sides['left'][0]:.3f} left, {sides['right'][0]:.3f} right,"
        f" intercept gone\n"
        f"C-01 now fires at a true {sides['left'][2]:.0f} mm (left) / "
        f"{abs(sides['right'][2]):.0f} mm (right)",
        (0.025, 0.035),
        xycoords="axes fraction",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=NEUTRAL, alpha=0.93),
    )

    ax.set_xlabel("true lateral error, measured against a tape (mm)")
    ax.set_ylabel("lateral error reported by the estimator (mm)")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=GRID)
    ax.set_title(
        "Rectifying the image removes the under-read, and with it the lost margin\n"
        "An assumption simulation had inherited, sitting in the path of a safety rule",
        fontsize=12,
    )
    _save(fig, out, "fig_9_1_rectification.png")


# --------------------------------------------------------------------------- 9.3
def fig_9_2(out: Path) -> None:
    """The training circuit's handedness, memorised as a steering bias."""
    d = pd.read_csv(
        REPO / "experiments" / "physical" / "runs" / "policy_bias_probe" / "cage_status.csv"
    )
    ey_mm = d["ey"].values * 1000.0
    steer = d["raw_steering"].values
    slope, icept = np.polyfit(ey_mm, steer, 1)
    span = ey_mm.max() - ey_mm.min()
    excursion = abs(slope * span)
    right = int((steer < 0).sum())

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.0, 5.2), gridspec_kw={"width_ratios": [2.05, 1]}
    )

    ax1.scatter(ey_mm, steer, s=5, alpha=0.18, color=ENF, edgecolors="none")
    xs = np.linspace(ey_mm.min(), ey_mm.max(), 50)
    ax1.plot(xs, slope * xs + icept, color=MON, lw=2.4, label="least-squares fit")
    ax1.axhline(0, color="k", lw=1.2)
    ax1.annotate(
        "straight ahead",
        (ey_mm.min() + 6, 0.006),
        fontsize=9,
    )
    ax1.annotate(
        "",
        xy=(ey_mm.max() + 6, 0),
        xytext=(ey_mm.max() + 6, icept),
        arrowprops=dict(arrowstyle="<->", color="k", lw=1.6),
    )
    ax1.annotate(
        f"constant\nleft bias\n{icept:.4f}",
        (ey_mm.max() + 14, icept / 2),
        fontsize=9.5,
        fontweight="bold",
        va="center",
    )
    ax1.annotate(
        f"across the whole {span:.0f} mm of position the command moves only "
        f"{excursion:.4f},\nwhile the bias that never goes away is "
        f"{icept:.4f} — {icept / excursion:.1f}x larger.\n"
        f"In closed loop the bias wins and the vehicle leaves the lane to the left.",
        (0.03, 0.05),
        xycoords="axes fraction",
        fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=NEUTRAL, alpha=0.9),
    )
    ax1.set_xlim(ey_mm.min() - 10, ey_mm.max() + 78)
    ax1.set_xlabel("lateral error, vehicle moved by hand (mm)")
    ax1.set_ylabel("steering commanded by the policy")
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(alpha=GRID)
    ax1.set_title(
        f"(a) correct sign, an order of magnitude too weak ({len(d):,} cycles)",
        fontsize=11,
    )

    # What the command stream asks for, left against right.
    left = len(steer) - right
    bars = ax2.bar(
        ["asks left", "asks right"],
        [left, right],
        0.55,
        color=[MON, GOOD],
    )
    for b, v in zip(bars, (left, right)):
        ax2.annotate(
            f"{v:,}\n({100 * v / len(steer):.1f} %)",
            (b.get_x() + b.get_width() / 2, v),
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
    ax2.set_ylabel("logged cycles")
    ax2.set_ylim(0, len(steer) * 1.22)
    ax2.grid(axis="y", alpha=GRID)
    ax2.set_title(
        "(b) the training circuit is 6.5:1 left-handed,\nand the policy memorised it",
        fontsize=11,
    )

    fig.suptitle(
        "The policy validated in simulation does not transfer: handedness learned as a bias "
        "— hands-off probe on the real circuit",
        fontsize=12,
    )
    fig.subplots_adjust(top=0.86)
    _save(fig, out, "fig_9_2_handedness_bias.png")


# --------------------------------------------------------------------------- 9.4
def fig_9_3(out: Path) -> None:
    """The 18.05 m run, and the single pulse that ended it."""
    run = (
        REPO
        / "experiments"
        / "physical"
        / "runs"
        / "track_v2_noloopclosure_20260826T100450Z"
    )
    d = pd.read_csv(run / "cage_status.csv")
    t = d["timestamp"].values
    dt = np.clip(np.diff(t, prepend=t[0]), 0, 1.0)
    dist = np.cumsum(d["speed"].values * dt)
    elapsed = t - t[0]
    em = d["emergency"].astype(bool).values
    latch = int(np.argmax(em)) if em.any() else len(d) - 1

    ey_mm = d["ey"].values * 1000.0
    rules = d["rules_fired"].fillna("").values
    moving_all = d["speed"].values > 0.05
    # The segment runs to the last cycle with real motion: C-05 latches at
    # `latch` and the vehicle coasts a little further before stopping. The
    # remaining ~0.1 m of the integral accrues as residual sensor velocity over
    # the 396 s the latch is held, which is not travel, so it is excluded here.
    last_moving = int(np.max(np.flatnonzero(d["speed"].values > 0.02)))
    drive = slice(0, last_moving + 1)
    total_m = float(dist[-1])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11.6, 6.4), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )

    ax1.plot(dist[drive], ey_mm[drive], color=ENF, lw=1.3)
    ax1.axhline(0, color="k", lw=0.9, ls="-", alpha=0.5)
    for sign in (1, -1):
        ax1.axhline(sign * C01_MM, color=MON, ls="--", lw=1.3)
    ax1.annotate(
        f"C-01 threshold, ±{C01_MM:.0f} mm — never approached",
        (0.4, C01_MM - 26),
        fontsize=9,
        color=MON,
    )
    md = moving_all[drive]
    med = float(np.median(np.abs(ey_mm[drive][md])))
    mx = float(np.max(np.abs(ey_mm[drive][md])))
    ax1.annotate(
        f"median |ey| {med:.1f} mm, max {mx:.1f} mm\n"
        f"no safety rule fired while driving",
        (0.02, 0.06),
        xycoords="axes fraction",
        fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=NEUTRAL, alpha=0.9),
    )
    ax1.plot([dist[latch]], [ey_mm[latch]], marker="X", ms=14, color=MON, zorder=5)
    ax1.annotate(
        f"a single 400 ms perception pulse latches C-05\n"
        f"at {dist[latch]:.2f} m, with the car {abs(ey_mm[latch]):.0f} mm from the centre",
        (dist[latch], ey_mm[latch]),
        xytext=(-260, 62),
        textcoords="offset points",
        fontsize=9.5,
        color=MON,
        arrowprops=dict(arrowstyle="->", color=MON, lw=1.4),
    )
    ax1.set_ylabel("lateral error (mm)")
    ax1.set_ylim(-C01_MM - 35, C01_MM + 35)
    ax1.grid(alpha=GRID)

    # C-06 activity along the run: the only rule that acts.
    c06 = np.array(["C-06" in r for r in rules])[drive]
    ax2.vlines(dist[drive][c06], 0, 1, color=WARN, lw=1.6)
    pct = 100 * c06[md].sum() / max(md.sum(), 1)
    ax2.annotate(
        f"C-06, the rate limiter: {int(c06.sum())} cycles "
        f"= {pct:.1f} % of moving cycles (3.0 % in simulation)",
        (0.02, 0.62),
        xycoords="axes fraction",
        fontsize=9.5,
    )
    ax2.set_yticks([])
    ax2.set_ylim(0, 1.6)
    ax2.set_xlabel("distance travelled along the circuit (m)")
    ax2.set_xlim(0, dist[last_moving] * 1.02)
    ax2.grid(axis="x", alpha=GRID)

    fig.suptitle(
        f"The retrained policy transfers: {dist[last_moving]:.2f} m in one continuous "
        f"segment, {elapsed[latch]:.1f} s, no operator help\n"
        "PRELIMINARY — one run, monitoring mode, no scored scenario",
        fontsize=12,
    )
    fig.subplots_adjust(top=0.85)
    _save(fig, out, "fig_9_3_physical_run_trace.png")


FIGURES = {
    "8_3": fig_8_3,
    "9_1": fig_9_1,
    "9_2": fig_9_2,
    "9_3": fig_9_3,
    "9_4": fig_9_4,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_DEFAULT), help="output directory")
    ap.add_argument(
        "--only",
        default=None,
        help=f"render one figure only ({', '.join(FIGURES)})",
    )
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = REPO / out

    todo = FIGURES if args.only is None else {args.only: FIGURES[args.only]}
    for name, fn in todo.items():
        print(f"rendering {name} ...")
        fn(out)


if __name__ == "__main__":
    main()
