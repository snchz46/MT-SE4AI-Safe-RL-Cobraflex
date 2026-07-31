#!/usr/bin/env python3
"""
plot_campaign_contrast — enforcement-vs-monitoring figures for any verdict campaign.

Fully data-driven: every label, count and scenario comes from the campaign's own
artefacts, so the same script serves the F4, GE4-V2 and the posterior 2-D campaigns
without carrying a narrative baked into the code (the reason
``plot_camera_comparison.py`` cannot be reused outside the GE4-V1 story it was
written for).

Reads ``<campaign-dir>/campaign_report.json`` (per-scenario roll-up) and
``<campaign-dir>/runs/*/summary.json`` (per-run metrics), and renders into
``<campaign-dir>/figures/`` (override with ``--out``):

  * ``fig_campaign_pass_fraction.png`` — pass fraction per scenario, enforcement
    vs monitoring, ordered by the enforcement−monitoring delta: where the cage
    rescues runs the bar pair opens up, where it costs availability it inverts.
  * ``fig_campaign_safety_invariant.png`` — road-edge contacts by mode, split
    in-ODD (nominal + perturbed families) vs out-of-ODD (edge + frontier), the
    partition used by the campaign analyses. Optional ``--compare`` overlays the
    same split from other campaign dirs (e.g. the weaker 2-D predecessor).

Usage:
  python tools/plot_campaign_contrast.py --campaign-dir experiments/sim/campaign_2d_ppo550k
  python tools/plot_campaign_contrast.py --campaign-dir <dir> \
      --compare experiments/sim/campaign_2d_margin022,experiments/sim/campaign_e_v2
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

ENF = "#1f77b4"
MON = "#d62728"
GRID = 0.3

# The in-ODD / out-of-ODD split used by every campaign analysis in this repo:
# nominal + perturbed scenarios run inside the ODD, edge + frontier are the
# deliberate out-of-domain stress. SC-EDGE-05's individually in-ODD grid points
# are attributed separately to the SR-010 co-activation finding, not diluted here.
IN_ODD_PREFIXES = ("SC-NOM", "SC-PERT")


def _load_runs(campaign_dir: Path) -> List[dict]:
    runs = []
    for summary in sorted((campaign_dir / "runs").glob("*/summary.json")):
        try:
            runs.append(json.loads(summary.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return runs


def _contacts(runs: List[dict]) -> Dict[str, int]:
    """Road-edge contacts per (mode, ODD bucket)."""
    counts: Counter = Counter()
    for run in runs:
        values = (run.get("campaign", {}) or {}).get("values", {}) or {}
        if not values.get("road_edge_contact"):
            continue
        scenario = run.get("scenario_id", "")
        bucket = "in-ODD" if scenario.startswith(IN_ODD_PREFIXES) else "out-of-ODD"
        counts[f"{run.get('mode')}|{bucket}"] += 1
    return counts


def fig_pass_fraction(report: dict, out: Path, title: str) -> None:
    by_scenario: Dict[str, Dict[str, float]] = {}
    for row in report.get("per_scenario", []):
        by_scenario.setdefault(row["scenario"], {})[row["mode"]] = row["fraction_pass"]
    pairs = [(s, m.get("enforcement"), m.get("monitoring")) for s, m in by_scenario.items()]
    pairs = [(s, e, m) for s, e, m in pairs if e is not None and m is not None]
    pairs.sort(key=lambda p: (p[1] - p[2]), reverse=True)

    labels = [p[0].replace("SC-", "") for p in pairs]
    enf = [p[1] for p in pairs]
    mon = [p[2] for p in pairs]
    x = np.arange(len(pairs))
    width = 0.4

    fig, ax = plt.subplots(figsize=(max(9.0, 0.52 * len(pairs) + 3), 5.4))
    ax.bar(x - width / 2, enf, width, color=ENF, label="Enforcement (cage active)")
    ax.bar(x + width / 2, mon, width, color=MON, label="Monitoring (cage off)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=9)
    ax.set_ylabel("pass fraction")
    ax.set_ylim(0, 1.08)
    ax.grid(True, axis="y", alpha=GRID)
    ax.legend(fontsize=9, loc="lower left")
    ax.set_title(title + "\nper-scenario pass fraction, sorted by the cage's contribution",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(out / "fig_campaign_pass_fraction.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_campaign_pass_fraction.png'}")


def fig_safety_invariant(series: List[Tuple[str, Dict[str, int]]], out: Path) -> None:
    buckets = ["enforcement|in-ODD", "monitoring|in-ODD",
               "enforcement|out-of-ODD", "monitoring|out-of-ODD"]
    tick_labels = ["enforcement\nin-ODD", "monitoring\nin-ODD",
                   "enforcement\nout-of-ODD", "monitoring\nout-of-ODD"]
    x = np.arange(len(buckets))
    width = 0.8 / max(1, len(series))

    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    for i, (label, counts) in enumerate(series):
        offset = (i - (len(series) - 1) / 2) * width
        heights = [counts.get(b, 0) for b in buckets]
        bars = ax.bar(x + offset, heights, width, label=label)
        for bar, height in zip(bars, heights):
            ax.annotate(str(height), (bar.get_x() + bar.get_width() / 2, height),
                        ha="center", va="bottom", fontsize=9,
                        fontweight="bold" if height == 0 else "normal")
    ax.set_xticks(x)
    ax.set_xticklabels(tick_labels, fontsize=10)
    ax.set_ylabel("runs with a road-edge contact")
    ax.grid(True, axis="y", alpha=GRID)
    ax.legend(fontsize=9)
    ax.set_title("Cage core-safety invariant: road-edge contacts by mode\n"
                 "in-ODD = nominal + perturbed families; out-of-ODD = edge + frontier stress",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(out / "fig_campaign_safety_invariant.png", dpi=150)
    plt.close(fig)
    print(f"  wrote {out/'fig_campaign_safety_invariant.png'}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Enforcement-vs-monitoring campaign figures.")
    ap.add_argument("--campaign-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default: <campaign-dir>/figures)")
    ap.add_argument("--compare", type=str, default=None,
                    help="comma-separated campaign dirs overlaid on the safety-invariant figure")
    ap.add_argument("--title", type=str, default=None,
                    help="title for the pass-fraction figure (default: the campaign dir name)")
    args = ap.parse_args()

    campaign_dir = args.campaign_dir.resolve()
    out = (args.out or campaign_dir / "figures").resolve()
    out.mkdir(parents=True, exist_ok=True)

    report = json.loads((campaign_dir / "campaign_report.json").read_text(encoding="utf-8"))
    title = args.title or campaign_dir.name
    print(f"campaign : {campaign_dir}\nout      : {out}")
    fig_pass_fraction(report, out, title)

    series = [(campaign_dir.name, _contacts(_load_runs(campaign_dir)))]
    for extra in (args.compare or "").split(","):
        extra = extra.strip()
        if not extra:
            continue
        other = Path(extra).resolve()
        series.append((other.name, _contacts(_load_runs(other))))
    fig_safety_invariant(series, out)


if __name__ == "__main__":
    main()
