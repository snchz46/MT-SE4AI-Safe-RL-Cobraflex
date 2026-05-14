"""
Figure 6 — Normative pyramid for AI safety in automotive systems.

Source script for the figure referenced at the close of section 3.8
of chapter 3 (`Capítulo 3 — Metodología`). Renders a stacked pyramid
with the four standards that organise the AI/automotive safety
landscape, plus the UL 4600 safety-case envelope around the pyramid,
the AMLAS transversal-patterns sidebar, and the five framework
adaptations A1..A5 marked on the layer where each applies.

Run:
    python normative_pyramid.py

Produces:
    normative_pyramid.png in the same directory.
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Polygon


HERE = Path(__file__).resolve().parent
OUT_PNG = HERE / "normative_pyramid.png"


def main() -> None:
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.axis("off")

    # ---------------------------------------------------------------
    # UL 4600 envelope — wraps the entire pyramid as a safety-case halo
    # ---------------------------------------------------------------
    ul4600 = FancyBboxPatch(
        (0.5, 0.5), 12.0, 7.0,
        boxstyle="round,pad=0.0,rounding_size=0.3",
        linewidth=2.0, edgecolor="#5c4b8c", facecolor="#f5f0fa",
        linestyle="--", zorder=1,
    )
    ax.add_patch(ul4600)
    ax.text(
        6.5, 7.10, "UL 4600 — safety case envelope",
        ha="center", va="center",
        fontsize=12, fontweight="bold", color="#5c4b8c", zorder=2,
    )

    # ---------------------------------------------------------------
    # Pyramid — four trapezoid layers stacked from base to apex
    # ---------------------------------------------------------------
    center_x = 6.5
    base_y = 1.2
    layer_height = 1.05
    # Half-widths from base to apex: 5 values produce 4 trapezoids.
    half_widths = [4.0, 3.3, 2.6, 1.9, 1.2]

    layers = [
        {
            "name": "ISO 26262",
            "desc": "Functional safety lifecycle (road vehicles)",
            "fill": "#fff4d4", "edge": "#b18b21",
        },
        {
            "name": "ISO 21448 (SOTIF)",
            "desc": "Complement for unexpected conditions",
            "fill": "#ffe7cc", "edge": "#b97326",
        },
        {
            "name": "ISO/IEC TR 5469",
            "desc": "AI in functional safety — umbrella",
            "fill": "#dde9f5", "edge": "#3366aa",
        },
        {
            "name": "PAS 8800",
            "desc": "Automotive AI / ML specialization",
            "fill": "#d8eed8", "edge": "#2e7d32",
        },
    ]

    for i, layer in enumerate(layers):
        y_bot = base_y + i * layer_height
        y_top = y_bot + layer_height
        pts = [
            (center_x - half_widths[i],     y_bot),
            (center_x + half_widths[i],     y_bot),
            (center_x + half_widths[i + 1], y_top),
            (center_x - half_widths[i + 1], y_top),
        ]
        poly = Polygon(
            pts, closed=True,
            facecolor=layer["fill"], edgecolor=layer["edge"],
            linewidth=1.6, zorder=3,
        )
        ax.add_patch(poly)
        ax.text(
            center_x, (y_bot + y_top) / 2 + 0.18, layer["name"],
            ha="center", va="center", fontsize=11, fontweight="bold", zorder=4,
        )
        ax.text(
            center_x, (y_bot + y_top) / 2 - 0.18, layer["desc"],
            ha="center", va="center", fontsize=8.5, style="italic", zorder=4,
        )

    # ---------------------------------------------------------------
    # AMLAS sidebar — argumentative patterns (transversal, to the left)
    # ---------------------------------------------------------------
    amlas_h = 4 * layer_height
    amlas = FancyBboxPatch(
        (0.85, base_y), 1.55, amlas_h,
        boxstyle="round,pad=0.0,rounding_size=0.2",
        linewidth=1.5, edgecolor="#7a5197", facecolor="#fbf6ff", zorder=2,
    )
    ax.add_patch(amlas)
    ax.text(
        1.625, base_y + amlas_h / 2,
        "AMLAS\n\nargumentative\npatterns\n(transversal)",
        ha="center", va="center", fontsize=9, fontweight="bold",
        color="#5c4b8c", zorder=3,
    )

    # ---------------------------------------------------------------
    # Adaptation markers A1..A5 — placed on the layer where each applies.
    # Markers sit in the lower-left portion of each trapezoid, below
    # the layer name+description (which are centred vertically), so they
    # do not collide with the text.
    # ---------------------------------------------------------------
    #   A4 — ISO 26262 base  (mandatory traceability across lifecycle)
    #   A5 — SOTIF           (operational validation + sim-to-real gap)
    #   A1 — TR 5469         (L4 split: Cage Spec + Training Spec, for ML modules)
    #   A2 — PAS 8800        (L4' split: Cage Unit Tests + Policy Behavioral Eval)
    #   A3 — transversal     (Runtime Monitoring, vertical span on the right)
    adaptations = [
        {"label": "A4", "x": center_x - 3.5, "y": base_y + 0.5 * layer_height},
        {"label": "A5", "x": center_x - 2.9, "y": base_y + 1.5 * layer_height},
        {"label": "A1", "x": center_x - 2.3, "y": base_y + 2.5 * layer_height},
        {"label": "A2", "x": center_x - 1.7, "y": base_y + 3.5 * layer_height},
    ]
    for a in adaptations:
        circ = Circle(
            (a["x"], a["y"]), 0.25,
            facecolor="#b71c1c", edgecolor="black", linewidth=1.0, zorder=5,
        )
        ax.add_patch(circ)
        ax.text(
            a["x"], a["y"], a["label"],
            ha="center", va="center",
            fontsize=9, fontweight="bold", color="white", zorder=6,
        )

    # A3 transversal: vertical double-headed arrow spanning SOTIF..PAS 8800
    arrow_x = center_x + 3.6
    arrow_top = base_y + 4 * layer_height - 0.15
    arrow_bot = base_y + layer_height + 0.15
    ax.annotate(
        "", xy=(arrow_x, arrow_top), xytext=(arrow_x, arrow_bot),
        arrowprops=dict(arrowstyle="<->", linewidth=2.0, color="#b71c1c"),
        zorder=4,
    )
    a3_y = base_y + 2.5 * layer_height
    a3_circ = Circle(
        (arrow_x, a3_y), 0.30,
        facecolor="#b71c1c", edgecolor="black", linewidth=1.0, zorder=5,
    )
    ax.add_patch(a3_circ)
    ax.text(
        arrow_x, a3_y, "A3",
        ha="center", va="center",
        fontsize=10, fontweight="bold", color="white", zorder=6,
    )
    ax.text(
        arrow_x + 0.45, a3_y,
        "transversal\nruntime\nmonitoring",
        ha="left", va="center", fontsize=8, color="#444", zorder=4,
    )

    # ---------------------------------------------------------------
    # Title
    # ---------------------------------------------------------------
    ax.text(
        6.5, 7.65, "Normative pyramid — AI safety in automotive",
        ha="center", va="center", fontsize=13, fontweight="bold",
    )

    fig.savefig(
        OUT_PNG, dpi=150, bbox_inches="tight", facecolor="white",
    )
    print(f"Wrote {OUT_PNG.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
