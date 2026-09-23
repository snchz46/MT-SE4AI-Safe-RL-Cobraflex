"""
Figure 1.2 -- Reading map of the document / Mapa de lectura del documento.

Source script for the figure referenced at the close of section 1.7 of
chapter 1. It answers the navigation question -- which chapter answers
what, and what does it leave behind -- and is deliberately NOT a second
copy of the V-Model mapping: the formal correspondence
level -> artefact -> chapter lives in Table 3.3, and the caption of this
figure points there.

The manuscript of record is Spanish (manuscript/draft_v5); the English
rendering (manuscript/draft_v5_en, manuscript/latex_psithesis) uses the
same layout with the English table. Both are rendered by default.

The four block colours are the ones Figure 3.3 uses for the same roles,
so that a reader who has seen the adapted V recognises them: grey for
the framework itself, orange for the specification branch, blue for
implementation and evaluation, purple for the closure.

The figure is drawn at its final printed size (6.1 in wide, i.e. the
\\widefigurewidth of the PSIThesis layout), so the font sizes below are
the point sizes that reach the page.

Run:
    python fig_1_2_document_roadmap.py          # both languages
    python fig_1_2_document_roadmap.py es       # Spanish only

Produces:
    fig_1_2_document_roadmap.png      (English)
    fig_1_2_document_roadmap_es.png   (Spanish)
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT = {
    "en": HERE / "fig_1_2_document_roadmap.png",
    "es": HERE / "fig_1_2_document_roadmap_es.png",
}

EN = "–"   # en dash
EM = "—"   # em dash

# (block colour, block label, [(chapter, title, what it leaves behind, V level)])
BLOCKS = {
    "en": [
        (
            "#5F6368",
            "I " + EM + " Framework",
            [
                ("1", "Introduction", "problem, hypotheses, scope, limits", ""),
                ("2", "State of the art", "the seams between the lines of work", ""),
                ("3", "Methodology", "the adapted V-Model, adaptations A1" + EN + "A5", ""),
            ],
        ),
        (
            "#C9591B",
            "II " + EM + " Specification",
            [
                ("4", "Domain, hazards, requirements", "ODD, H-01..H-12, SR-001..SR-014", "L1, L2"),
                ("5", "Architecture and cage", "ROS2 graph, cage rules C-01..C-06", "L3, L4a"),
            ],
        ),
        (
            "#1565C0",
            "III " + EM + " Implementation and evaluation",
            [
                ("6", "Implementation, verification", "cage node, unit + integration tests", "L5, L4a', L3'"),
                ("7", "Training", "training specification, policy of record", "L4b, L5"),
                ("8", "Experimental evaluation", "1,890-run campaign, metrics", "L4b', L2'"),
                ("9", "Sim-to-real gap", "measured gap, physical bring-up", "L1'"),
            ],
        ),
        (
            "#7B1FA2",
            "IV " + EM + " Closure",
            [
                ("10", "Operational validation", "consolidated verdict with its limits", "L1'"),
                ("11", "Discussion", "the framework against its own criteria", ""),
                ("12", "Conclusions, future work", "answers, transferability, T1" + EN + "T7", ""),
            ],
        ),
    ],
    "es": [
        (
            "#5F6368",
            "I " + EM + " Marco",
            [
                ("1", "Introducción", "problema, hipótesis, alcance, límites", ""),
                ("2", "Estado del arte", "las costuras entre líneas de trabajo", ""),
                ("3", "Metodología", "el V-Model adaptado, adaptaciones A1" + EN + "A5", ""),
            ],
        ),
        (
            "#C9591B",
            "II " + EM + " Especificación",
            [
                ("4", "Dominio, peligros, requisitos", "ODD, H-01..H-12, SR-001..SR-014", "L1, L2"),
                ("5", "Arquitectura y cage", "grafo ROS2, reglas C-01..C-06", "L3, L4a"),
            ],
        ),
        (
            "#1565C0",
            "III " + EM + " Implementación y evaluación",
            [
                ("6", "Implementación, verificación", "nodo cage, tests unit. + integración", "L5, L4a', L3'"),
                ("7", "Entrenamiento", "spec de entrenamiento, policy de registro", "L4b, L5"),
                ("8", "Evaluación experimental", "campaña de 1.890 corridas, métricas", "L4b', L2'"),
                ("9", "Gap sim-to-real", "gap medido, puesta en marcha física", "L1'"),
            ],
        ),
        (
            "#7B1FA2",
            "IV " + EM + " Cierre",
            [
                ("10", "Validación operacional", "veredicto consolidado con sus límites", "L1'"),
                ("11", "Discusión", "el marco frente a sus propios criterios", ""),
                ("12", "Conclusiones, trabajo futuro", "respuestas, transferibilidad, T1" + EN + "T7", ""),
            ],
        ),
    ],
}

LABELS = {
    "en": {
        "chapter": "chapter",
        "leaves": "what it leaves behind",
        "level": "V-Model level",
        "appendix": (
            "Appendices A" + EN + "I " + EM + " evidence material: hazard register (A), requirements (B),\n"
            "instrument choices (C), ODD (D), cage parameters (E), traceability (F),\n"
            "positioning (G), training detail (H), campaign breakdown (I)"
        ),
    },
    "es": {
        "chapter": "capítulo",
        "leaves": "qué deja",
        "level": "nivel del V-Model",
        "appendix": (
            "Anexos A" + EN + "I " + EM + " material de evidencia: registro de peligros (A), requisitos (B),\n"
            "elecciones de instrumento (C), ODD (D), parámetros de la cage (E), trazabilidad (F),\n"
            "posicionamiento (G), detalle de entrenamiento (H), desglose de campaña (I)"
        ),
    },
}

W = 6.10            # figure width in inches == \widefigurewidth
ROW_H = 0.235       # height of one chapter row
HDR_H = 0.185       # height of a block header
BLOCK_PAD = 0.055   # vertical gap between blocks
LEFT = 0.06
RIGHT = W - 0.06
CHIP_W = 0.30
TITLE_X = LEFT + 0.40
LEAVES_X = LEFT + 2.80
LEVEL_X = RIGHT - 0.06


def render(lang: str) -> None:
    """Render the document reading map (manuscript Fig. 1.2) in one language."""
    blocks = BLOCKS[lang]
    labels = LABELS[lang]

    n_rows = sum(len(b[2]) for b in blocks)
    band_h = 0.40
    height = n_rows * ROW_H + len(blocks) * (HDR_H + BLOCK_PAD) + 0.44 + band_h
    # Full-bleed axes: plt.subplots() leaves ~22 % of default margin, which
    # shrinks everything drawn in data units while leaving everything sized in
    # points untouched -- so the point sizes chosen below would not be the ones
    # that reach the page. With the axes spanning the figure, one data unit is
    # one inch and the sizes are literal.
    fig = plt.figure(figsize=(W, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, height)
    ax.axis("off")

    y = height - 0.16

    # Column legend
    ax.text(TITLE_X, y, labels["chapter"], ha="left", va="center",
            fontsize=6.0, color="#5f6368", style="italic")
    ax.text(LEAVES_X, y, labels["leaves"], ha="left", va="center",
            fontsize=6.0, color="#5f6368", style="italic")
    ax.text(LEVEL_X, y, labels["level"], ha="right", va="center",
            fontsize=6.0, color="#5f6368", style="italic")
    y -= 0.14

    for colour, label, chapters in blocks:
        # Block header bar
        y -= HDR_H
        ax.add_patch(
            FancyBboxPatch(
                (LEFT, y), RIGHT - LEFT, HDR_H,
                boxstyle="round,pad=0.0,rounding_size=0.035",
                linewidth=0, facecolor=colour, zorder=2,
            )
        )
        ax.text(LEFT + 0.10, y + HDR_H / 2, label, ha="left", va="center",
                color="white", fontsize=7.6, fontweight="bold", zorder=3)

        # Chapter rows
        for number, title, leaves, level in chapters:
            y -= ROW_H
            ax.add_patch(
                FancyBboxPatch(
                    (LEFT, y + 0.012), RIGHT - LEFT, ROW_H - 0.024,
                    boxstyle="round,pad=0.0,rounding_size=0.03",
                    linewidth=0.6, edgecolor="#d5d7da", facecolor="white", zorder=2,
                )
            )
            ax.add_patch(
                FancyBboxPatch(
                    (LEFT + 0.05, y + 0.045), CHIP_W, ROW_H - 0.09,
                    boxstyle="round,pad=0.0,rounding_size=0.03",
                    linewidth=0, facecolor=colour, zorder=3,
                )
            )
            ax.text(LEFT + 0.05 + CHIP_W / 2, y + ROW_H / 2, number,
                    ha="center", va="center", color="white",
                    fontsize=7.0, fontweight="bold", zorder=4)
            ax.text(TITLE_X, y + ROW_H / 2, title, ha="left", va="center",
                    color="#1a1a1a", fontsize=7.0, fontweight="bold", zorder=4)
            ax.text(LEAVES_X, y + ROW_H / 2, leaves, ha="left", va="center",
                    color="#40464c", fontsize=6.8, style="italic", zorder=4)
            if level:
                ax.text(LEVEL_X, y + ROW_H / 2, level, ha="right", va="center",
                        color=colour, fontsize=6.4, family="monospace", zorder=4)
        y -= BLOCK_PAD

    # Appendix band
    y -= band_h
    ax.add_patch(
        FancyBboxPatch(
            (LEFT, y), RIGHT - LEFT, band_h,
            boxstyle="round,pad=0.0,rounding_size=0.035",
            linewidth=0.7, edgecolor="#9aa0a6", facecolor="#f1f3f4", zorder=2,
        )
    )
    ax.text((LEFT + RIGHT) / 2, y + band_h / 2, labels["appendix"],
            ha="center", va="center", color="#40464c", fontsize=6.2,
            linespacing=1.3, zorder=3)

    fig.savefig(OUT[lang], dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT[lang]}")


if __name__ == "__main__":
    for language in (sys.argv[1:] or ["en", "es"]):
        render(language)
