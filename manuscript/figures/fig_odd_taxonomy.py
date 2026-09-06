"""
ODD taxonomy retained + the four stratified operational domains.

Bespoke renderer for `odd_taxonomy_reduced.mmd`, which the generic
`mmd_render.py` cannot handle: that source is the only one in the set that
uses mermaid `subgraph` blocks and labelled solid edges, i.e. a two-column
layout with a 2x2 grid rather than a chain. The content below is a
transcription of that file -- if one changes, change the other.

Left: the PAS 1883 / ISO 34503 dimensions retained for this thesis. Right: the
2x2 stratification whose pairwise contrasts let chapter 8 attribute an effect
to a single complexity axis. Bottom: the physical analogue, deferred.

Drawn at final printed size (6.1 in == \\widefigurewidth), with a full-bleed
axes so one data unit is one inch and the point sizes are literal.

Run:
    python fig_odd_taxonomy.py          # both languages
    python fig_odd_taxonomy.py es

Produces:
    fig_odd_taxonomy.png / fig_odd_taxonomy_es.png
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = {"en": HERE / "fig_odd_taxonomy.png", "es": HERE / "fig_odd_taxonomy_es.png"}

# Palette taken from the classDefs of odd_taxonomy_reduced.mmd.
TAX = dict(fill="#E1F5EE", stroke="#0F6E56", color="#04342C")
NOM = dict(fill="#EEEDFE", stroke="#534AB7", color="#26215C")
ADV = dict(fill="#FAECE7", stroke="#993C1D", color="#4A1B0C")
DEF = dict(fill="#F1EFE8", stroke="#5F5E5A", color="#2C2C2A")

TEXT = {
    "en": {
        "tax_title": "Taxonomy retained\n(PAS 1883 / ISO 34503)",
        "tax": [
            "Intended function +\nsubject-vehicle assumptions",
            "Scenery\ndrivable area, lane spec,\nedges, surface, structures",
            "Environmental conditions\nillumination, weather,\nparticulates, connectivity",
            "Dynamic elements\nother actors and\npermitted states",
            "Subject-vehicle envelope +\nsensor / actuation interfaces",
            "Explicit exclusions +\nODD-exit assumptions",
        ],
        "dom_title": "Four stratified operational domains (2 × 2)",
        "o1": "ODD-1\nstraight lane · nominal",
        "o2": "ODD-2\n= ODD-1 + named\nadverse profiles",
        "o3": "ODD-3\ncurvy closed loop · nominal",
        "o4": "ODD-4\n= ODD-3 + named\nadverse profiles",
        "e12": "adverse stressors\n(straight)",
        "e13": "geometric complexity\n(nominal)",
        "e34": "adverse stressors\n(curved)",
        "phys": ("ODD-PHYS-1 (deferred) — hardware analogue of ODD-1: same scenery, exclusions and\n"
                 "exit assumptions; dynamic envelope and interfaces re-measured on the platform"),
        "describes": "describes each domain",
    },
    "es": {
        "tax_title": "Taxonomía retenida\n(PAS 1883 / ISO 34503)",
        "tax": [
            "Función pretendida +\nsupuestos del vehículo",
            "Escenario\nárea transitable, carril,\nbordes, superficie, estructuras",
            "Condiciones ambientales\niluminación, meteorología,\npartículas, conectividad",
            "Elementos dinámicos\notros actores y\nestados permitidos",
            "Envolvente del vehículo +\ninterfaces de sensado y actuación",
            "Exclusiones explícitas +\nsupuestos de salida del ODD",
        ],
        "dom_title": "Cuatro dominios operacionales estratificados (2 × 2)",
        "o1": "ODD-1\ncarril recto · nominal",
        "o2": "ODD-2\n= ODD-1 + perfiles\nadversos con nombre",
        "o3": "ODD-3\ncircuito sinuoso · nominal",
        "o4": "ODD-4\n= ODD-3 + perfiles\nadversos con nombre",
        "e12": "estresores adversos\n(recta)",
        "e13": "complejidad geométrica\n(nominal)",
        "e34": "estresores adversos\n(curva)",
        "phys": ("ODD-PHYS-1 (diferido) — análogo hardware de ODD-1: mismo escenario, exclusiones y\n"
                 "supuestos de salida; envolvente dinámica e interfaces medidas de nuevo en la plataforma"),
        "describes": "describe cada dominio",
    },
}

W = 6.10
H = 3.82
LEFT_W = 2.05        # taxonomy column
GRID_X = 2.55        # left edge of the 2x2
CELL_W = 1.62
CELL_H = 0.60
CELL_GX = 0.30       # horizontal gap inside the grid
CELL_GY = 0.52       # vertical gap inside the grid


def box(ax, x, y, w, h, style, text, size=5.4, head_size=6.2, rounding=0.05):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle=f"round,pad=0.0,rounding_size={rounding}",
        linewidth=1.0, edgecolor=style["stroke"], facecolor=style["fill"], zorder=3))
    lines = text.split("\n")
    if len(lines) > 1:
        ax.text(x + w / 2, y + h * 0.74, lines[0], ha="center", va="center",
                color=style["color"], fontsize=head_size, fontweight="bold", zorder=4)
        ax.text(x + w / 2, y + h * 0.30, "\n".join(lines[1:]), ha="center",
                va="center", color=style["color"], fontsize=size,
                linespacing=1.25, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, lines[0], ha="center", va="center",
                color=style["color"], fontsize=head_size, fontweight="bold", zorder=4)


def arrow(ax, p0, p1, label, colour="#6b6b6b", dy=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=9,
                                 linewidth=0.9, color=colour, zorder=2))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + dy
    ax.text(mx, my, label, ha="center", va="center", fontsize=4.7,
            color="#4a4a4a", style="italic", linespacing=1.2, zorder=5,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor="none", alpha=0.9))


def render(lang: str) -> None:
    """Render the ODD taxonomy / domain-stratification figure."""
    t = TEXT[lang]
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    # ---- left column: retained taxonomy -----------------------------------
    ax.text(0.06 + LEFT_W / 2, H - 0.14, t["tax_title"], ha="center", va="center",
            fontsize=6.0, fontweight="bold", color=TAX["color"], linespacing=1.25)
    y = H - 0.40
    for item in t["tax"]:
        n = len(item.split("\n"))
        h = 0.13 + 0.108 * n
        y -= h
        box(ax, 0.06, y, LEFT_W, h, TAX, item, size=4.7, head_size=5.4)
        y -= 0.055

    # ---- right: the 2x2 ---------------------------------------------------
    ax.text(GRID_X + (2 * CELL_W + CELL_GX) / 2, H - 0.14, t["dom_title"],
            ha="center", va="center", fontsize=6.0, fontweight="bold",
            color="#3c3c3c")

    top_y = H - 0.40 - CELL_H
    bot_y = top_y - CELL_GY - CELL_H
    x1, x2 = GRID_X, GRID_X + CELL_W + CELL_GX

    box(ax, x1, top_y, CELL_W, CELL_H, NOM, t["o1"])
    box(ax, x2, top_y, CELL_W, CELL_H, ADV, t["o2"])
    box(ax, x1, bot_y, CELL_W, CELL_H, NOM, t["o3"])
    box(ax, x2, bot_y, CELL_W, CELL_H, ADV, t["o4"])

    arrow(ax, (x1 + CELL_W, top_y + CELL_H / 2), (x2, top_y + CELL_H / 2), t["e12"], dy=0.20)
    arrow(ax, (x1 + CELL_W / 2, top_y), (x1 + CELL_W / 2, bot_y + CELL_H), t["e13"])
    arrow(ax, (x1 + CELL_W, bot_y + CELL_H / 2), (x2, bot_y + CELL_H / 2), t["e34"], dy=0.20)

    # taxonomy -> domains
    arrow(ax, (0.06 + LEFT_W + 0.02, H - 1.30), (GRID_X - 0.04, H - 1.30), t["describes"], dy=0.17)

    # ---- bottom band: the deferred physical analogue -----------------------
    band_h = 0.42
    ax.add_patch(FancyBboxPatch(
        (0.06, 0.08), W - 0.12, band_h,
        boxstyle="round,pad=0.0,rounding_size=0.05", linewidth=1.0,
        edgecolor=DEF["stroke"], facecolor=DEF["fill"], zorder=3))
    ax.text(W / 2, 0.08 + band_h / 2, t["phys"], ha="center", va="center",
            color=DEF["color"], fontsize=5.2, linespacing=1.35, zorder=4)

    fig.savefig(OUT[lang], dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT[lang].name}")


if __name__ == "__main__":
    for language in (sys.argv[1:] or ["en", "es"]):
        render(language)
