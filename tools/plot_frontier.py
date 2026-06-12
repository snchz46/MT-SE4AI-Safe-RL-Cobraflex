#!/usr/bin/env python3
"""
plot_frontier — cage-efficacy comparison figures for a frontier campaign.

Reads ``<campaign-dir>/runs/*/summary.json`` for the ``SC-FRONT-*`` scenarios and
renders two PNGs into ``<campaign-dir>/figures/`` (override with ``--out``):

  * ``fig_frontier_excursion.png``  — max lateral excursion |ey|, enforcement
    (cage active) vs monitoring (no cage), one panel per policy seed, **mean ±
    std across reps**, with the lane-edge and road-edge reference lines and the
    per-cell road-edge-contact rate marked.
  * ``fig_frontier_cage_benefit.png`` — the measured cage benefit, i.e. the mean
    excursion reduction monitoring − enforcement, per scenario and seed.

The figures **aggregate over the N repetitions** of each (scenario, seed, mode)
cell, so the *same* script serves the rep00 pilot (n=1, bars = the single run) and
the full 25-rep campaign (D-29, bars = mean ± std with the contact rate). Visual
companion to ``tools/frontier_contrast.py`` (text table).

Usage:
  python tools/plot_frontier.py                         # default: the frontier pilot dir
  python tools/plot_frontier.py --campaign-dir experiments/sim/campaign_frontier
  python tools/plot_frontier.py --campaign-dir <out> --out <out>/figures

``run_campaign.py`` calls ``render(campaign_dir)`` automatically after a campaign
that included frontier scenarios (best-effort; if matplotlib is absent it prints
this command instead).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN_DIR = REPO / "experiments" / "sim" / "campaign_frontier"

LANE_EDGE_M = 0.1225   # ODD-1 lane edge
ROAD_EDGE_M = 0.26     # road half-width (0.5 * road_width); road_edge_contact threshold

C_ENF = "#2c7fb8"      # enforcement (cage active)
C_MON = "#d95f0e"      # monitoring (no cage)
SEED_COLOR = {"2024": "#7fb3d5", "123": "#c0392b"}

SEED_LABEL_FULL = {
    "2024": "Seed 2024 — policy que respeta restricciones",
    "123": "Seed 123 — policy dependiente de la cage",
}
_SEED_ORDER = {"2024": 0, "123": 1}

Cell = Tuple[str, str, str]  # (scenario_id, seed, mode)


# --------------------------------------------------------------------------- #
# Load + aggregate over reps
# --------------------------------------------------------------------------- #
def _seed_of(run_id: str) -> str:
    m = re.search(r"seed(\d+)", run_id)
    return m.group(1) if m else "pd"


def load_cells(campaign_dir: Path) -> Dict[Cell, dict]:
    """Collect per-rep values for every (scenario, seed, mode) frontier cell."""
    cells: Dict[Cell, dict] = defaultdict(lambda: {"max_ey": [], "edge": [], "intv": []})
    pattern = str(Path(campaign_dir) / "runs" / "*" / "summary.json")
    for path in sorted(glob.glob(pattern)):
        d = json.load(open(path, encoding="utf-8"))
        sc = str(d.get("scenario_id", ""))
        if not sc.startswith("SC-FRONT"):
            continue  # robust to a mixed campaign — only the frontier arm
        rid = os.path.basename(os.path.dirname(path))
        vals = d.get("campaign", {}).get("values", {})
        key: Cell = (sc, _seed_of(rid), str(d.get("mode")))
        if d.get("max_abs_ey_m") is not None:
            cells[key]["max_ey"].append(float(d["max_abs_ey_m"]))
        cells[key]["edge"].append(1.0 if vals.get("road_edge_contact") else 0.0)
        if d.get("intervention_rate_pct") is not None:
            cells[key]["intv"].append(float(d["intervention_rate_pct"]))
    return cells


def aggregate(cells: Dict[Cell, dict]) -> Dict[Cell, dict]:
    agg: Dict[Cell, dict] = {}
    for key, v in cells.items():
        eys = v["max_ey"]
        agg[key] = {
            "n": len(v["edge"]),
            "ey_mean": mean(eys) if eys else math.nan,
            "ey_std": pstdev(eys) if len(eys) > 1 else 0.0,
            "edge_rate": (mean(v["edge"]) if v["edge"] else 0.0),
            "intv_mean": (mean(v["intv"]) if v["intv"] else math.nan),
        }
    return agg


def _seed_label(seed: str) -> str:
    return SEED_LABEL_FULL.get(seed, f"Seed {seed}")


def _short(sc: str) -> str:
    return sc.replace("SC-FRONT-", "FRONT-")


def _note(agg: Dict[Cell, dict]) -> str:
    n_max = max((a["n"] for a in agg.values()), default=0)
    if n_max <= 1:
        return "Piloto F4 · 1 run/celda (rep00) · campaña 25-rep (D-29) pendiente en host Ubuntu"
    return f"Campaña frontier F4 · n={n_max} runs/celda · media ± std (D-29)"


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_excursion(agg, scenarios, seeds, out_dir: Path, note: str) -> Path:
    x = np.arange(len(scenarios))
    w = 0.38
    fig, axes = plt.subplots(1, len(seeds), figsize=(min(6.4 * len(seeds), 18), 5.2),
                             sharey=True, squeeze=False)
    axes = axes[0]
    tops = [0.30]
    for ax, seed in zip(axes, seeds):
        def col(mode, field):
            return [agg.get((s, seed, mode), {}).get(field, math.nan) for s in scenarios]

        enf, mon = col("enforcement", "ey_mean"), col("monitoring", "ey_mean")
        enf_e, mon_e = col("enforcement", "ey_std"), col("monitoring", "ey_std")
        ax.bar(x - w / 2, enf, w, yerr=enf_e, capsize=3, label="Enforcement (cage activa)",
               color=C_ENF, error_kw=dict(lw=1, alpha=0.6))
        ax.bar(x + w / 2, mon, w, yerr=mon_e, capsize=3, label="Monitoring (sin cage)",
               color=C_MON, error_kw=dict(lw=1, alpha=0.6))
        for i, s in enumerate(scenarios):
            a = agg.get((s, seed, "monitoring"), {})
            rate, n = a.get("edge_rate", 0.0), a.get("n", 0)
            if rate > 0:
                ytop = (mon[i] if not math.isnan(mon[i]) else 0) + (mon_e[i] or 0)
                ax.plot(x[i] + w / 2, ytop, marker="X", color="red", ms=11, zorder=5)
                if n > 1:  # show the contact RATE for the real campaign; X alone for n=1
                    ax.text(x[i] + w / 2, ROAD_EDGE_M + 0.008, f"{int(round(rate * n))}/{n}",
                            ha="center", color="red", fontsize=8, fontweight="bold")
            tops += [(v or 0) + (e or 0) for v, e in ((enf[i], enf_e[i]), (mon[i], mon_e[i]))
                     if v is not None and not math.isnan(v)]
        ax.axhline(ROAD_EDGE_M, ls="--", color="red", lw=1.2)
        ax.axhline(LANE_EDGE_M, ls=":", color="gray", lw=1.2)
        ax.set_title(_seed_label(seed), fontsize=10.5)
        ax.set_xticks(x)
        ax.set_xticklabels([_short(s) for s in scenarios])
        ax.grid(axis="y", alpha=0.25)
    for ax in axes:
        ax.set_ylim(0, max(tops) * 1.12)
    axes[0].set_ylabel("Excursión lateral máxima  |ey|  (m)")
    handles, labels = axes[0].get_legend_handles_labels()
    handles += [
        plt.Line2D([0], [0], marker="X", color="red", ls="", ms=10),
        plt.Line2D([0], [0], ls="--", color="red", lw=1.2),
        plt.Line2D([0], [0], ls=":", color="gray", lw=1.2),
    ]
    labels += ["Salida de calzada", "Borde calzada (0.26 m)", "Borde carril (0.1225 m)"]
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.945), frameon=False)
    fig.suptitle("Eficacia de la cage — escenarios frontier (arranque fuera del ODD)",
                 fontsize=13, y=1.0)
    fig.text(0.5, 0.005, note, ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    out = out_dir / "fig_frontier_excursion.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_benefit(agg, scenarios, seeds, out_dir: Path, note: str) -> Path:
    x = np.arange(len(scenarios))
    w = 0.8 / max(len(seeds), 1)
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    top = 0.05
    for j, seed in enumerate(seeds):
        benefit = []
        for s in scenarios:
            enf = agg.get((s, seed, "enforcement"), {}).get("ey_mean")
            mon = agg.get((s, seed, "monitoring"), {}).get("ey_mean")
            d = (mon - enf) if (enf is not None and mon is not None
                                and not math.isnan(enf) and not math.isnan(mon)) else math.nan
            benefit.append(d)
            if not math.isnan(d):
                top = max(top, d)
        off = (j - (len(seeds) - 1) / 2) * w
        ax.bar(x + off, benefit, w, label=_seed_label(seed).split(" — ")[0],
               color=SEED_COLOR.get(seed, None))
        for i, s in enumerate(scenarios):
            mon_a = agg.get((s, seed, "monitoring"), {})
            enf_a = agg.get((s, seed, "enforcement"), {})
            if mon_a.get("edge_rate", 0) > 0 and enf_a.get("edge_rate", 0) == 0 and not math.isnan(benefit[i]):
                ax.text(x[i] + off, benefit[i] + 0.004, "salida\nevitada", ha="center",
                        va="bottom", color="red", fontsize=7.5, fontweight="bold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([_short(s) for s in scenarios])
    ax.set_ylabel("Beneficio de la cage:  Δ excursión = monitoring − enforcement  (m)")
    ax.set_title("Valor protector medido de la cage por escenario y policy", fontsize=12.5)
    ax.set_ylim(top=top * 1.20)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title=None, fontsize=9.5, loc="upper left")
    ax.text(0.5, 0.90, "Δ alto = la cage reduce mucho la excursión   ·   Δ≈0 = la policy se basta sola",
            transform=ax.transAxes, ha="center", fontsize=9, color="#444", style="italic")
    fig.text(0.5, 0.01, note, ha="center", fontsize=8, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = out_dir / "fig_frontier_cage_benefit.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Entry points
# --------------------------------------------------------------------------- #
def render(campaign_dir: Path = DEFAULT_CAMPAIGN_DIR, out_dir: Optional[Path] = None) -> List[Path]:
    """Render the frontier figures for ``campaign_dir``; returns the written paths
    (empty if the campaign has no frontier runs). Importable from run_campaign."""
    cells = load_cells(campaign_dir)
    if not cells:
        return []
    agg = aggregate(cells)
    out_dir = Path(out_dir) if out_dir else Path(campaign_dir) / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios = sorted({k[0] for k in agg})
    seeds = sorted({k[1] for k in agg}, key=lambda s: (_SEED_ORDER.get(s, 9), s))
    note = _note(agg)
    return [
        fig_excursion(agg, scenarios, seeds, out_dir, note),
        fig_benefit(agg, scenarios, seeds, out_dir, note),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    """Render the frontier cage-efficacy figures."""
    ap = argparse.ArgumentParser(description="Cage-efficacy figures for a frontier campaign.")
    ap.add_argument("--campaign-dir", type=Path, default=DEFAULT_CAMPAIGN_DIR,
                    help="campaign root containing runs/<run_id>/summary.json (default: the pilot).")
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir for the PNGs (default: <campaign-dir>/figures).")
    args = ap.parse_args(argv)
    outs = render(args.campaign_dir, args.out)
    if not outs:
        print(f"No frontier (SC-FRONT-*) summaries under {args.campaign_dir}/runs")
        return 1
    n_cells = len(aggregate(load_cells(args.campaign_dir)))
    print(f"frontier cells={n_cells}")
    for p in outs:
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
