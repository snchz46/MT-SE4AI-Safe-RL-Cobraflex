"""
Figure 5.2 — ROS2 node graph of the system, for both observation tracks.

Source script for the figure referenced in section 5.7.1 of chapter 5
(draft_v5/body/05_arquitectura_y_cage.md, draft_v5_en/body/05_architecture_and_cage.md).
It replaces an RViz screenshot that had been shipped under this file name by
mistake (kept as rviz_lane_camera_and_policy_observation.png).

The graph is the one wired in src/: node and topic names are taken from the
declare_parameter defaults of lane_perception_node, cv_lane_estimator_node,
rl_policy_node, cage_ros_node, vehicle_control_node and cage_logger_node.
The research chapter carries the state-track subset as a mermaid block
(manuscript/chapters/chapter_05_architecture_and_cage.md, §5.7.1). It is drawn
here with its own layout because the graph branches — two consumers of the
camera image, two producers into the cage — which mmd_render.py's
single-chain layout does not cover.

Everything is drawn at final printed size (6.1 in wide), so the font sizes are
the point sizes that reach the page.

Run:
    python fig_5_2_node_chain.py

Produces:
    fig_5_2_node_chain.png in the same directory.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
OUT_PNG = HERE / "fig_5_2_node_chain.png"

# House palette, shared with the .mmd figures (fill, stroke, text).
PERCEPTION = ("#E1F5EE", "#0F6E56", "#04342C")
POLICY = ("#EEEDFE", "#534AB7", "#26215C")
CAGE = ("#FAECE7", "#993C1D", "#4A1B0C")
SIM = ("#F1EFE8", "#5F5E5A", "#2C2C2A")
EDGE = "#6B6B6B"
AUX = "#9A9A9A"

WIDTH = 6.10
TITLE_PT = 8.5
BODY_PT = 6.6
LABEL_PT = 6.2

# Styles of the three kinds of data edge; the legend repeats them.
BOTH = "-"
CAMERA_ONLY = (0, (4, 2))
STATE_ONLY = (0, (1, 1.6))


def box(ax, cx, cy, w, h, colors, title, lines, lw=1.2):
    """Rounded node box with a bold title and smaller body lines."""
    fill, stroke, text = colors
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.06",
        facecolor=fill, edgecolor=stroke, linewidth=lw, zorder=2,
    ))
    n = len(lines)
    step = 0.13
    top = cy + (n * step) / 2
    ax.text(cx, top, title, ha="center", va="center", fontsize=TITLE_PT,
            fontweight="bold", color=text, zorder=3)
    for i, line in enumerate(lines):
        ax.text(cx, top - (i + 1) * step - 0.02, line, ha="center", va="center",
                fontsize=BODY_PT, color=text, zorder=3)


def arrow(ax, p0, p1, style=BOTH, color=EDGE, lw=1.0):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>", mutation_scale=8, color=color,
        linewidth=lw, linestyle=style, shrinkA=0, shrinkB=0, zorder=1,
    ))


def label(ax, x, y, text, ha="left", color=EDGE):
    ax.text(x, y, text, ha=ha, va="center", fontsize=LABEL_PT, color=color,
            family="DejaVu Sans Mono", zorder=3)


def main() -> None:
    height = 4.60
    fig = plt.figure(figsize=(WIDTH, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(-0.10, height - 0.10)
    ax.set_aspect("equal")
    ax.axis("off")

    xl, xr = 1.625, 4.475          # column centres
    cw = 2.25                      # column box width
    xc, wide = 3.05, 3.60          # centred boxes (platform, cage)
    y_plat, h_plat = 4.13, 0.58
    y_row1, h_row1 = 2.98, 0.72
    y_cage, h_cage = 1.83, 0.66
    y_row3, h_row3 = 0.62, 0.66
    xa, xb = 1.80, 4.30            # x of the two vertical edge lanes

    box(ax, xc, y_plat, wide, h_plat, SIM, "Vehicle platform",
        ["Gazebo DiffDrive plugin  |  CobraFlex 1:14 driver",
         "front camera  ·  odometry"])
    box(ax, xl, y_row1, cw, h_row1, PERCEPTION, "Perception",
        ["lane_perception_node · state track",
         "cv_lane_estimator_node · camera track"])
    box(ax, xr, y_row1, cw, h_row1, POLICY, "Policy",
        ["PD / RL on /state_obs · state track",
         "rl_policy_node (CNN) · camera track"])
    box(ax, xc, y_cage, wide, h_cage, CAGE, "Safety cage — cage_ros_node",
        ["C-06 → C-04 → C-02 → C-03 → C-01 → C-05",
         "enforcement or monitoring mode"], lw=2.0)
    box(ax, xl, y_row3, cw, h_row3, SIM, "Vehicle control",
        ["vehicle_control_node",
         "zero command while /emergency is latched"])
    box(ax, xr, y_row3, cw, h_row3, SIM, "Logging",
        ["cage_logger_node",
         "CSV + metadata.json per run"])

    plat_bot = y_plat - h_plat / 2
    row1_top, row1_bot = y_row1 + h_row1 / 2, y_row1 - h_row1 / 2
    cage_top, cage_bot = y_cage + h_cage / 2, y_cage - h_cage / 2
    row3_top = y_row3 + h_row3 / 2

    # platform -> perception (both tracks) and -> policy (camera track only)
    arrow(ax, (xa, plat_bot), (xa, row1_top))
    label(ax, xa - 0.06, (plat_bot + row1_top) / 2, "image · /odom", ha="right")
    arrow(ax, (xb, plat_bot), (xb, row1_top), style=CAMERA_ONLY)
    label(ax, xb + 0.06, (plat_bot + row1_top) / 2, "image")

    # perception -> policy (state track only)
    arrow(ax, (xl + cw / 2, y_row1), (xr - cw / 2, y_row1), style=STATE_ONLY)
    ax.text((xl + xr) / 2, y_row1 + 0.09, "/state_obs", ha="center",
            va="center", fontsize=LABEL_PT - 0.6, color=EDGE,
            family="DejaVu Sans Mono", zorder=3)

    # perception -> cage, policy -> cage
    arrow(ax, (xa, row1_bot), (xa, cage_top))
    label(ax, xa - 0.06, (row1_bot + cage_top) / 2 + 0.07, "/state_obs", ha="right")
    label(ax, xa - 0.06, (row1_bot + cage_top) / 2 - 0.07, "/perception_invalid", ha="right")
    arrow(ax, (xb, row1_bot), (xb, cage_top))
    label(ax, xb + 0.06, (row1_bot + cage_top) / 2, "/raw_action")

    # cage -> vehicle control, cage -> logger
    arrow(ax, (xa, cage_bot), (xa, row3_top))
    label(ax, xa - 0.06, (cage_bot + row3_top) / 2 + 0.07, "/safe_action", ha="right")
    label(ax, xa - 0.06, (cage_bot + row3_top) / 2 - 0.07, "/emergency", ha="right")
    arrow(ax, (xb, cage_bot), (xb, row3_top))
    label(ax, xb + 0.06, (cage_bot + row3_top) / 2, "/cage_status")

    # vehicle control -> platform: the only edge that reaches the actuator
    x_loop = 0.18
    ax.plot([xl - cw / 2, x_loop, x_loop], [y_row3, y_row3, y_plat],
            color=EDGE, linewidth=1.0, zorder=1, solid_capstyle="butt")
    arrow(ax, (x_loop, y_plat), (xc - wide / 2, y_plat))
    ax.text(x_loop - 0.07, (y_row3 + y_plat) / 2, "/cmd_vel", rotation=90,
            ha="center", va="center", fontsize=LABEL_PT, color=EDGE,
            family="DejaVu Sans Mono", zorder=3)

    # operator / auxiliary inputs into the cage
    arrow(ax, (5.20, y_cage), (xc + wide / 2, y_cage), style=(0, (3, 1.5, 1, 1.5)),
          color=AUX, lw=0.9)
    label(ax, 5.25, y_cage + 0.07, "/cage_reset", color=AUX)
    label(ax, 5.25, y_cage - 0.07, "/external_stop", color=AUX)

    # legend
    y_leg = 0.05
    entries = [
        (BOTH, EDGE, "both tracks", 0.40),
        (CAMERA_ONLY, EDGE, "camera track only", 1.78),
        (STATE_ONLY, EDGE, "state track only", 3.36),
        ((0, (3, 1.5, 1, 1.5)), AUX, "operator inputs", 4.86),
    ]
    for style, color, text, x in entries:
        ax.add_line(Line2D([x, x + 0.30], [y_leg, y_leg], color=color,
                           linewidth=1.0, linestyle=style))
        ax.text(x + 0.36, y_leg, text, ha="left", va="center",
                fontsize=LABEL_PT, color=SIM[2])

    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", pad_inches=0.03,
                facecolor="white")
    print(f"written: {OUT_PNG}")


if __name__ == "__main__":
    main()
