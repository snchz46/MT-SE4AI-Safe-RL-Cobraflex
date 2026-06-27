#!/usr/bin/env python3
"""plot_camera_comparison — meeting / manuscript figures contrasting the F4
ground-truth-state campaign with the track-'E' camera v1 (GE4) campaign.

Pure read-over-evidence (no Gazebo): consumes the two committed roll-ups
``experiments/sim/campaign{,_e}/campaign_report.json`` and the E failure-mode
breakdown ``experiments/sim/campaign_e/failure_mode_breakdown.json`` and renders
four PNGs into ``manuscript/figures/auto/`` (override with ``--out``):

  1. fig_cam_cost_of_camera[_en].png   — per-scenario enforcement pass-fraction,
     F4 (ground-truth state) vs camera v1, on the shared F-track scenarios.
  2. fig_cam_cage_value[_en].png       — enforcement vs monitoring on the camera
     scenarios where the cage acts (the latent→active evidence; SC-PERT-07 hero).
  3. fig_cam_failure_modes[_en].png    — decomposition of the camera vetoes: every
     enforcement fail is a SAFE controlled stop, not a lane breach.
  4. fig_cam_cage_regimes[_en].png     — synthesis matrix: when the cage is latent
     vs active across both campaigns.

``--lang es`` (default; manuscript is Spanish) or ``--lang en`` (Prof. Schüler /
international). English files get the ``_en`` suffix so both stay regenerable.

Usage:
  python tools/plot_camera_comparison.py                 # Spanish (manuscript)
  python tools/plot_camera_comparison.py --lang en       # English (meeting)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
F4_REPORT = REPO / "experiments" / "sim" / "campaign" / "campaign_report.json"
E_REPORT = REPO / "experiments" / "sim" / "campaign_e" / "campaign_report.json"
E_BREAKDOWN = REPO / "experiments" / "sim" / "campaign_e" / "failure_mode_breakdown.json"
DEFAULT_OUT = REPO / "manuscript" / "figures" / "auto"

# Palette — kept distinct across the figure set to avoid cross-figure confusion.
C_F4 = "#55a868"        # F4 ground-truth-state campaign (baseline)
C_CAM = "#8172b3"       # camera v1 campaign
C_ENF = "#2c7fb8"       # enforcement (cage active) — matches plot_frontier.py
C_MON = "#d95f0e"       # monitoring (no cage)      — matches plot_frontier.py
C_PASS = "#55a868"
C_STOP = "#dd8452"      # fail = safe controlled stop (emergency-only)
C_BREACH = "#c44e52"    # fail = real lane breach
C_INDET = "#b0b0b0"     # indeterminate (instrumentation gap)
GRAY = "#555555"

PASS_BAR = 0.90         # pass_criterion_per_scenario threshold (fraction_pass >= 0.90)

# --------------------------------------------------------------------------- #
# Localised strings
# --------------------------------------------------------------------------- #
STRINGS: Dict[str, Dict[str, object]] = {
    "es": {
        "f1_title": "Coste de la percepción por cámara — escenarios F-track compartidos\n"
                    "mismo tronco (cage + library), solo cambia la fuente de percepción",
        "f1_ylabel": "Fracción de aprobados (enforcement)",
        "f1_leg_f4": "F4 — estado ground truth",
        "f1_leg_cam": "Cámara v1 (GE4)",
        "f1_thresh": "umbral PASS 0.90",
        "f1_indet": "indet",
        "f1_flip_down": "PASA→FALLA\n(paradas seguras)",
        "f1_flip_up": "FALLA→PASA",
        "f1_note": "F4 1260 runs · Cámara v1 1660 runs · seed 2024 · el set F-track se "
                   "mantiene salvo SC-EDGE-02 (recuperación cerca del borde)",
        "f2_title": "La cage pasa de latente a ACTIVA bajo la cámara (dentro del ODD)\n"
                    "el delta enforcement−monitoring mide qué previene la cage",
        "f2_labels": ["SC-PERT-07\noclusión /\npérdida percepción",
                      "SC-PERT-10\nmundo mojado",
                      "SC-EDGE-02\nrecuperación\ncerca del borde"],
        "f2_leg_enf": "Enforcement (cage activa)",
        "f2_leg_mon": "Monitoring (sin cage)",
        "f2_ylabel": "Fracción de aprobados",
        "f2_annot": "20/20  vs  0/20\nsin cage → 20 brechas\nREALES de carril",
        "f2_note": "Cámara v1 · seed 2024 · en F4 la cage era latente in-ODD (M-S2=0 ambos modos).\n"
                   "SC-PERT-04 (glare) enf 0.50<mon 0.70: la parada segura penalizada por "
                   "`emergency==False` — ver Fig. modos de fallo.",
        "f3_title": "El veredicto `NOT SATISFIED` es coste de DISPONIBILIDAD, no brecha de seguridad\n"
                    "todos los fallos de los escenarios que vetan son paradas controladas seguras",
        "f3_leg_pass": "PASA",
        "f3_leg_stop": "FALLA = parada controlada segura (emergency-only)",
        "f3_leg_breach": "FALLA = brecha real de carril / contacto de borde",
        "f3_box": "830 runs enforcement → {n} contactos de borde · M-S1 < d_max in-ODD\n"
                  "(rojo = 0 en todas: ningún fallo es brecha de seguridad)",
        "f3_ylabel": "Nº de runs",
        "f3_note": "Cámara v1 · enforcement · SC-EDGE-02 y SC-PERT-04 vetan SR-001/012/014 "
                   "(`emergency==False` puntúa la parada como fallo)",
        "f4_rows": ["Nominal\n(dentro del ODD)", "Estrés in-ODD\n(perturbado)",
                    "Fuera del ODD\n(frontier)"],
        "f4_cols": ["F4 — estado ground truth", "Cámara v1"],
        "f4_cells": [
            [("LATENTE\nM-S2 = 0 en ambos modos\nla policy no se acerca al borde", False),
             ("ACTIVA\nla percepción ruidosa dispara\nla parada controlada", True)],
            [("LATENTE\nla policy se basta sola", False),
             ("ACTIVA · SC-PERT-07\n20/20 vs 0/20\nla cage previene la salida", True)],
            [("ACTIVA · seed 123\nelimina 96–100 % de\ncontactos de borde", True),
             ("Se mantiene\nSC-FRONT 1.0", False)],
        ],
        "f4_title": "¿Cuándo importa la cage? — valor medido, no postulado",
        "f4_key": "verde = cage activa / decisiva      ·      gris = cage latente",
        "f4_note": "Síntesis de los dos brazos: la cage es una garantía cuyo valor es nulo con "
                   "policy buena + estado limpio in-ODD, y decisivo cuando la percepción se "
                   "degrada o el sistema sale del ODD.",
    },
    "en": {
        "f1_title": "Cost of camera perception — shared F-track scenarios\n"
                    "same trunk (cage + library), only the perception source changes",
        "f1_ylabel": "Pass fraction (enforcement)",
        "f1_leg_f4": "F4 — ground-truth state",
        "f1_leg_cam": "Camera v1 (GE4)",
        "f1_thresh": "PASS threshold 0.90",
        "f1_indet": "indet",
        "f1_flip_down": "PASS→FAIL\n(safe stops)",
        "f1_flip_up": "FAIL→PASS",
        "f1_note": "F4 1260 runs · Camera v1 1660 runs · seed 2024 · the F-track set holds "
                   "except SC-EDGE-02 (near-edge recovery)",
        "f2_title": "The cage flips from latent to ACTIVE under the camera (in-ODD)\n"
                    "the enforcement−monitoring delta measures what the cage prevents",
        "f2_labels": ["SC-PERT-07\nocclusion /\nperception loss",
                      "SC-PERT-10\nwet world",
                      "SC-EDGE-02\nnear-edge\nrecovery"],
        "f2_leg_enf": "Enforcement (cage active)",
        "f2_leg_mon": "Monitoring (no cage)",
        "f2_ylabel": "Pass fraction",
        "f2_annot": "20/20  vs  0/20\nno cage → 20 REAL\nlane breaches",
        "f2_note": "Camera v1 · seed 2024 · in F4 the cage was latent in-ODD (M-S2=0 both modes).\n"
                   "SC-PERT-04 (glare) enf 0.50<mon 0.70: the safe stop penalised by "
                   "`emergency==False` — see failure-modes fig.",
        "f3_title": "The `NOT SATISFIED` verdict is an AVAILABILITY cost, not a safety breach\n"
                    "every fail in the vetoing scenarios is a safe controlled stop",
        "f3_leg_pass": "PASS",
        "f3_leg_stop": "FAIL = safe controlled stop (emergency-only)",
        "f3_leg_breach": "FAIL = real lane breach / road-edge contact",
        "f3_box": "830 enforcement runs → {n} road-edge contacts · M-S1 < d_max in-ODD\n"
                  "(red = 0 everywhere: no fail is a safety breach)",
        "f3_ylabel": "Number of runs",
        "f3_note": "Camera v1 · enforcement · SC-EDGE-02 and SC-PERT-04 veto SR-001/012/014 "
                   "(`emergency==False` scores the stop as a fail)",
        "f4_rows": ["Nominal\n(in-ODD)", "In-ODD stress\n(perturbed)",
                    "Out-of-ODD\n(frontier)"],
        "f4_cols": ["F4 — ground-truth state", "Camera v1"],
        "f4_cells": [
            [("LATENT\nM-S2 = 0 in both modes\npolicy never nears the edge", False),
             ("ACTIVE\nnoisy percept triggers\nthe controlled stop", True)],
            [("LATENT\npolicy suffices alone", False),
             ("ACTIVE · SC-PERT-07\n20/20 vs 0/20\ncage prevents departure", True)],
            [("ACTIVE · seed 123\nremoves 96–100% of\nroad-edge contacts", True),
             ("Holds\nSC-FRONT 1.0", False)],
        ],
        "f4_title": "When does the cage matter? — value measured, not postulated",
        "f4_key": "green = cage active / decisive      ·      gray = cage latent",
        "f4_note": "Synthesis of both arms: the cage is a guarantee whose value is null with a "
                   "good policy + clean state in-ODD, and decisive when perception degrades or "
                   "the system leaves the ODD.",
    },
}


def _enf_map(report: dict, mode: str = "enforcement") -> Dict[str, dict]:
    return {r["scenario"]: r for r in report["per_scenario"] if r["mode"] == mode}


def _short(s: str) -> str:
    return s.replace("SC-", "")


def _frac_or_nan(rec: Optional[dict]) -> float:
    if rec is None or rec.get("fraction_pass") is None:
        return np.nan
    return float(rec["fraction_pass"])


# --------------------------------------------------------------------------- #
# Fig 1 — cost of camera (F4 vs camera v1, enforcement)
# --------------------------------------------------------------------------- #
def fig_cost_of_camera(f4: dict, e: dict, out: Path, S: dict) -> Path:
    f4e, ee = _enf_map(f4), _enf_map(e)
    order = ["SC-NOM-01", "SC-NOM-02", "SC-NOM-03",
             "SC-EDGE-01", "SC-EDGE-02", "SC-EDGE-03", "SC-EDGE-04", "SC-EDGE-05",
             "SC-PERT-01", "SC-PERT-02", "SC-PERT-03"]
    scenarios = [s for s in order if s in f4e and s in ee]
    x = np.arange(len(scenarios))
    w = 0.38
    f4v = [_frac_or_nan(f4e.get(s)) for s in scenarios]
    ev = [_frac_or_nan(ee.get(s)) for s in scenarios]

    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    ax.bar(x - w / 2, np.nan_to_num(f4v), w, color=C_F4, label=S["f1_leg_f4"])
    ax.bar(x + w / 2, np.nan_to_num(ev), w, color=C_CAM, label=S["f1_leg_cam"])
    ax.axhline(PASS_BAR, ls="--", color="#c44e52", lw=1.3)
    ax.text(len(scenarios) - 0.5, PASS_BAR + 0.012, S["f1_thresh"],
            ha="right", color="#c44e52", fontsize=8.5)

    for i, s in enumerate(scenarios):
        for off, val in ((-w / 2, f4v[i]), (w / 2, ev[i])):
            if np.isnan(val):
                ax.bar(x[i] + off, 1.0, w, color=C_INDET, hatch="///",
                       edgecolor="white", alpha=0.45)
                ax.text(x[i] + off, 0.5, S["f1_indet"], rotation=90, ha="center",
                        va="center", fontsize=7.5, color="#333")
        if s == "SC-EDGE-02":
            ax.annotate(S["f1_flip_down"], xy=(x[i] + w / 2, ev[i]),
                        xytext=(x[i] + w / 2, ev[i] - 0.30), ha="center", fontsize=8.5,
                        color="#c44e52", fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color="#c44e52", lw=1.2))
        if s == "SC-PERT-01":
            ax.annotate(S["f1_flip_up"], xy=(x[i] + w / 2, ev[i]),
                        xytext=(x[i], ev[i] + 0.07), ha="center", fontsize=8.5,
                        color="#2e7d32", fontweight="bold",
                        arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.2))

    ax.set_xticks(x)
    ax.set_xticklabels([_short(s) for s in scenarios], rotation=20, ha="right")
    ax.set_ylabel(S["f1_ylabel"])
    ax.set_ylim(0, 1.12)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower left", fontsize=10, framealpha=0.9)
    ax.set_title(S["f1_title"], fontsize=13)
    fig.text(0.5, 0.005, S["f1_note"], ha="center", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Fig 2 — cage value under the camera (enforcement vs monitoring)
# --------------------------------------------------------------------------- #
def fig_cage_value(e: dict, out: Path, S: dict) -> Path:
    enf, mon = _enf_map(e, "enforcement"), _enf_map(e, "monitoring")
    scenarios = ["SC-PERT-07", "SC-PERT-10", "SC-EDGE-02"]
    x = np.arange(len(scenarios))
    w = 0.38
    ev = [_frac_or_nan(enf.get(s)) for s in scenarios]
    mv = [_frac_or_nan(mon.get(s)) for s in scenarios]

    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    bars_e = ax.bar(x - w / 2, ev, w, color=C_ENF, label=S["f2_leg_enf"])
    bars_m = ax.bar(x + w / 2, mv, w, color=C_MON, label=S["f2_leg_mon"])
    for b, v in list(zip(bars_e, ev)) + list(zip(bars_m, mv)):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                ha="center", fontsize=9, fontweight="bold")
    ax.annotate(S["f2_annot"], xy=(x[0] + w / 2, mv[0] + 0.01), xytext=(0.30, 0.40),
                ha="center", fontsize=8.5, color="#c44e52", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#c44e52", lw=1.4))

    ax.set_xticks(x)
    ax.set_xticklabels(S["f2_labels"], fontsize=9.5)
    ax.set_ylabel(S["f2_ylabel"])
    ax.set_ylim(0, 1.12)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper right", fontsize=10)
    ax.set_title(S["f2_title"], fontsize=12.5)
    fig.text(0.5, 0.02, S["f2_note"], ha="center", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Fig 3 — failure modes: availability cost, not a safety breach
# --------------------------------------------------------------------------- #
def fig_failure_modes(bd: dict, out: Path, S: dict) -> Path:
    groups = {(g["scenario"], g["mode"]): g for g in bd["per_group"]}
    rows = [("SC-EDGE-02", "enforcement"), ("SC-PERT-04", "enforcement"),
            ("SC-PERT-02", "enforcement"), ("SC-NOM-02", "enforcement")]
    labels = [f"{_short(s)}\n({m[:3]})" for s, m in rows]
    x = np.arange(len(rows))
    npass = [groups[r]["pass"] for r in rows]
    nstop = [groups[r]["fail_emergency_only"] for r in rows]
    nbreach = [groups[r]["fail_ms1_breach"] + groups[r]["fail_edge_contact"]
               + groups[r]["fail_other"] for r in rows]

    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    ax.bar(x, npass, color=C_PASS, label=S["f3_leg_pass"])
    ax.bar(x, nstop, bottom=npass, color=C_STOP, label=S["f3_leg_stop"])
    ax.bar(x, nbreach, bottom=np.array(npass) + np.array(nstop), color=C_BREACH,
           label=S["f3_leg_breach"])
    for i, r in enumerate(rows):
        n = groups[r]["n"]
        if nstop[i] >= 3:
            ax.text(i, npass[i] + nstop[i] / 2, f"{nstop[i]}", ha="center",
                    va="center", fontsize=10, fontweight="bold", color="white")
        ax.text(i, n + 0.7, f"n={n}", ha="center", fontsize=8.5, color="#333")

    inv = bd["cage_core_safety_enforcement"]
    ax.text(0.98, 0.97, S["f3_box"].format(n=inv["road_edge_contacts"]),
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#222",
            bbox=dict(boxstyle="round,pad=0.4", fc="#fff6e6", ec="#dd8452"))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel(S["f3_ylabel"])
    ax.set_ylim(0, max(groups[r]["n"] for r in rows) * 1.36)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="upper left", fontsize=8.8)
    ax.set_title(S["f3_title"], fontsize=12)
    fig.text(0.5, 0.01, S["f3_note"], ha="center", fontsize=8, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------- #
# Fig 4 — synthesis matrix: when is the cage latent vs active
# --------------------------------------------------------------------------- #
def fig_cage_regimes(out: Path, S: dict) -> Path:
    rows, cols, cells = S["f4_rows"], S["f4_cols"], S["f4_cells"]
    fig, ax = plt.subplots(figsize=(11, 5.8))
    nrows = len(rows)
    ax.set_xlim(0, 2)
    ax.set_ylim(0, nrows + 0.18)
    ax.axis("off")
    for j, c in enumerate(cols):
        ax.text(j + 0.5, nrows + 0.03, c, ha="center", va="bottom",
                fontsize=11.5, fontweight="bold")
    for i, r in enumerate(rows):
        yr = nrows - 1 - i
        ax.text(-0.04, yr + 0.5, r, ha="right", va="center", fontsize=10.5,
                fontweight="bold", color="#333")
        for j in range(len(cols)):
            txt, active = cells[i][j]
            fc = "#eaf3ea" if active else "#f2f2f2"
            ec = "#2e7d32" if active else "#bdbdbd"
            ax.add_patch(plt.Rectangle((j + 0.03, yr + 0.05), 0.94, 0.9,
                                       facecolor=fc, edgecolor=ec, lw=2))
            ax.text(j + 0.5, yr + 0.5, txt, ha="center", va="center",
                    fontsize=9.2, color="#222")
    fig.suptitle(S["f4_title"], fontsize=13.5, y=0.985)
    fig.text(0.5, 0.925, S["f4_key"], ha="center", fontsize=10, color=GRAY)
    fig.text(0.5, 0.02, S["f4_note"], ha="center", fontsize=8.2, color=GRAY)
    fig.tight_layout(rect=(0, 0.05, 1, 0.89))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """Render the four F4-vs-camera comparison figures."""
    ap = argparse.ArgumentParser(description="Camera-vs-ground-truth comparison figures.")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--campaign-dir", type=Path, default=None,
                    help="E-campaign dir (default: experiments/sim/campaign_e, the 139k). "
                         "Point at experiments/sim/campaign_e_297k for the 297k E-main.")
    ap.add_argument("--lang", choices=["es", "en"], default="es",
                    help="figure language (default es; the manuscript is Spanish).")
    args = ap.parse_args(argv)
    e_report = (args.campaign_dir / "campaign_report.json") if args.campaign_dir else E_REPORT
    e_breakdown = (args.campaign_dir / "failure_mode_breakdown.json") if args.campaign_dir else E_BREAKDOWN
    out = (args.out or (args.campaign_dir / "figures" if args.campaign_dir else DEFAULT_OUT)).resolve()
    out.mkdir(parents=True, exist_ok=True)
    args.out = out
    S = STRINGS[args.lang]
    sfx = "" if args.lang == "es" else "_en"
    f4 = json.loads(F4_REPORT.read_text(encoding="utf-8"))
    e = json.loads(e_report.read_text(encoding="utf-8"))
    bd = json.loads(e_breakdown.read_text(encoding="utf-8"))
    outs = [
        fig_cost_of_camera(f4, e, args.out / f"fig_cam_cost_of_camera{sfx}.png", S),
        fig_cage_value(e, args.out / f"fig_cam_cage_value{sfx}.png", S),
        fig_failure_modes(bd, args.out / f"fig_cam_failure_modes{sfx}.png", S),
        fig_cage_regimes(args.out / f"fig_cam_cage_regimes{sfx}.png", S),
    ]
    for p in outs:
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
