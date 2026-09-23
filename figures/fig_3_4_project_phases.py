"""
Figure 3.4 -- Project phases against the levels of the adapted V-Model.

Renderer for the same matrix as ``fig_3_4_project_phases.dot``. The .dot
file stays the reference description of the figure; this script exists
because the authoring host has no Graphviz, and because drawing the
matrix at its final printed width lets the font sizes be chosen in
points that actually reach the page instead of being scaled down by
\\includegraphics.

If you change one, change the other: the CELLS table below is a
transcription of the .dot table body, row for row.

Run:
    python fig_3_4_project_phases.py

Produces:
    fig_3_4_project_phases.png in the same directory.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
OUT_PNG = HERE / "fig_3_4_project_phases.png"

PHASES = [
    ("F0", "Foundation"),
    ("F1", "HARA + SR"),
    ("F2", "Cage"),
    ("F3", "Training"),
    ("F4", "Sim eval"),
    ("F5", "Physical"),
    ("F6", "Closure"),
]

# Row header background / cell background, by branch.
LEFT_HDR, LEFT_CELL = "#eaf3ff", "#f7faff"
RIGHT_HDR, RIGHT_CELL = "#f4e9ff", "#fbf6ff"
RM_HDR, RM_CELL = "#ffeef0", "#fff5f6"
TR_HDR, TR_CELL = "#f0f0f0", "#fafafa"

# (row label, header colour, cell colour, [7 cell texts, "" for empty])
ROWS = [
    ("L1  Stakeholder Req.", LEFT_HDR, LEFT_CELL,
     ["", "ODD-Spec v1.0", "", "", "", "ODD-PHYS-1", "review"]),
    ("L2  System Safety Req.", LEFT_HDR, LEFT_CELL,
     ["", "HazReg + SRS\n(12H / 14SR)", "SRS calibration\n(M-1..M-5)", "", "", "", "review"]),
    ("L3  Architecture Design", LEFT_HDR, LEFT_CELL,
     ["", "skeleton", "ROS2 graph\n(perc/policy/\ncage/log)", "", "", "", "review"]),
    ("L4a  Cage Specification", LEFT_HDR, LEFT_CELL,
     ["", "", "C-01..C-06\ncage.yaml v0.6.1", "", "", "", ""]),
    ("L4b  Training Specification", LEFT_HDR, LEFT_CELL,
     ["", "", "", "reward +\nhyperparams\n+ criteria", "", "", ""]),
    ("L5  Implementation", LEFT_HDR, LEFT_CELL,
     ["", "", "cage_node", "PPO policy\n(training)", "trained policy", "", ""]),
    ("L4a'  Cage Unit Tests", RIGHT_HDR, RIGHT_CELL,
     ["", "", "test_cage_rules.py", "", "", "", ""]),
    ("L4b'  Policy Behavioral Eval.", RIGHT_HDR, RIGHT_CELL,
     ["", "", "", "", "scenario eval."
      "\n+ M-P*/M-S*/\nM-I*", "", ""]),
    ("L3'  Integration Testing", RIGHT_HDR, RIGHT_CELL,
     ["", "", "pipeline tests", "end-to-end sim", "", "", ""]),
    ("L2'  Scenario-Based Testing", RIGHT_HDR, RIGHT_CELL,
     ["", "", "", "SC-NOM/EDGE/\nPERT/FRONT", "runs in Gazebo", "", ""]),
    ("L1'  Operational Validation", RIGHT_HDR, RIGHT_CELL,
     ["", "", "", "", "sim verdicts", "sim-to-real gap\n+ physical\nbring-up",
      "global verdict\n+ defence"]),
]

# Transversal runtime-monitoring band: one cell spanning F2..F6.
RM_ROW = ("RM (A3)  Runtime Monitoring", 2, 7,
          "Logger Node + intervention logs — transversal across F2–F6")

TRACE_ROW = ("Traceability matrix (A4)",
             ["skeleton", "H↔SR", "+ C", "+ SC, M", "sim verdicts",
              "gap evidence", "close at G6"])

GATES = ["G0", "G1", "G2", "G3", "G4", "G5", "G6"]

W = 6.10           # final printed width in inches (== \widefigurewidth)
LABEL_W = 1.46     # width of the row-label column
ROW_H = 0.262
HDR_H = 0.255
GATE_H = 0.185


def main() -> None:
    """Render the phase/level matrix (manuscript Fig. 3.4)."""
    n_rows = len(ROWS) + 3  # + runtime-monitoring, traceability, gates
    height = HDR_H + n_rows * ROW_H + GATE_H
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

    col_w = (W - LABEL_W) / len(PHASES)

    def cell(x, y, w, h, face, edge="#c9ccd1", lw=0.5):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=face,
                               edgecolor=edge, linewidth=lw, zorder=2))

    y = height - HDR_H

    # Header row
    cell(0, y, LABEL_W, HDR_H, "#222222", edge="#222222")
    ax.text(0.05, y + HDR_H / 2, "Level \\ Phase", ha="left", va="center",
            color="white", fontsize=6.4, fontweight="bold", zorder=3)
    for i, (code, name) in enumerate(PHASES):
        x = LABEL_W + i * col_w
        cell(x, y, col_w, HDR_H, "#222222", edge="#222222")
        ax.text(x + col_w / 2, y + HDR_H * 0.66, code, ha="center", va="center",
                color="white", fontsize=6.4, fontweight="bold", zorder=3)
        ax.text(x + col_w / 2, y + HDR_H * 0.27, name, ha="center", va="center",
                color="white", fontsize=5.2, zorder=3)

    # Body rows
    for label, hdr_c, cell_c, texts in ROWS:
        y -= ROW_H
        cell(0, y, LABEL_W, ROW_H, hdr_c)
        code, _, rest = label.partition("  ")
        ax.text(0.05, y + ROW_H / 2, code, ha="left", va="center",
                color="#1a1a1a", fontsize=5.6, fontweight="bold", zorder=3)
        ax.text(0.05 + 0.36, y + ROW_H / 2, rest, ha="left", va="center",
                color="#1a1a1a", fontsize=5.4, zorder=3)
        for i, txt in enumerate(texts):
            x = LABEL_W + i * col_w
            cell(x, y, col_w, ROW_H, cell_c if txt else "white")
            if txt:
                ax.text(x + col_w / 2, y + ROW_H / 2, txt, ha="center",
                        va="center", color="#26292c", fontsize=4.4,
                        linespacing=1.25, zorder=3)

    # Runtime-monitoring band
    label, c0, c1, txt = RM_ROW
    y -= ROW_H
    cell(0, y, LABEL_W, ROW_H, RM_HDR)
    ax.text(0.05, y + ROW_H / 2, "RM (A3)", ha="left", va="center",
            color="#1a1a1a", fontsize=5.6, fontweight="bold", zorder=3)
    ax.text(0.05 + 0.54, y + ROW_H / 2, "Runtime Monitoring", ha="left",
            va="center", color="#1a1a1a", fontsize=5.4, zorder=3)
    for i in range(c0):
        cell(LABEL_W + i * col_w, y, col_w, ROW_H, "white")
    x0 = LABEL_W + c0 * col_w
    cell(x0, y, (c1 - c0) * col_w, ROW_H, RM_CELL)
    ax.text(x0 + (c1 - c0) * col_w / 2, y + ROW_H / 2, txt, ha="center",
            va="center", color="#26292c", fontsize=5.0, style="italic", zorder=3)

    # Traceability-matrix fill
    label, texts = TRACE_ROW
    y -= ROW_H
    cell(0, y, LABEL_W, ROW_H, TR_HDR)
    ax.text(0.05, y + ROW_H / 2, label, ha="left", va="center",
            color="#1a1a1a", fontsize=5.4, fontweight="bold", zorder=3)
    for i, txt in enumerate(texts):
        x = LABEL_W + i * col_w
        cell(x, y, col_w, ROW_H, TR_CELL)
        ax.text(x + col_w / 2, y + ROW_H / 2, txt, ha="center", va="center",
                color="#26292c", fontsize=4.6,
                fontweight="bold" if i == len(texts) - 1 else "normal", zorder=3)

    # Gate strip
    y -= GATE_H
    cell(0, y, LABEL_W, GATE_H, "#222222", edge="#222222")
    ax.text(0.05, y + GATE_H / 2, "Gate", ha="left", va="center",
            color="white", fontsize=5.6, fontweight="bold", zorder=3)
    for i, g in enumerate(GATES):
        x = LABEL_W + i * col_w
        cell(x, y, col_w, GATE_H, "#bbbbbb")
        ax.text(x + col_w / 2, y + GATE_H / 2, g, ha="center", va="center",
                color="#1a1a1a", fontsize=5.6, fontweight="bold", zorder=3)

    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
