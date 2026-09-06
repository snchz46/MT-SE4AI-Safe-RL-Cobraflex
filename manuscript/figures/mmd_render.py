"""
Render the project's mermaid flowcharts to PNG, offline, with matplotlib.

WHY THIS EXISTS. The .mmd files in this directory are the canonical sources
for ten figures (they say so in their own headers, and the research chapters
in manuscript/chapters/ carry them as inline ```mermaid blocks). Rendering
them needs mermaid-cli, which needs Node; neither the Windows authoring host
nor the compute host has it installed, so the figures were never rendered and
never reached manuscript/draft_v5. This module reads the .mmd files and draws
them, so the .mmd stays the single source of truth and nothing has to be
transcribed by hand.

It is NOT a mermaid implementation. It covers exactly the subset these files
use: `flowchart TD|LR`, rectangular / stadium / cylinder nodes, solid `-->`
chains, dotted `-. "label" .->` edges, and `classDef` / `class` styling. A
construct outside that subset raises rather than being silently dropped.

LAYOUT. Mermaid's own layout is not reproduced. The graphs here are all one
main chain with a few side nodes hanging off it by dotted edges, so the
layout is: find the longest solid-edge path, lay it along the main axis, and
place every remaining node beside the neighbour it attaches to. `direction`
can be overridden per figure, because a nine-box `LR` chain that mermaid
renders 1800 px wide is illegible at the 155 mm the thesis actually prints.

Everything is drawn at final printed size (6.1 in wide == \\widefigurewidth
of the PSIThesis layout), so the font sizes are the point sizes that reach
the page.

Run:
    python mmd_render.py                 # render every figure in FIGURES
    python mmd_render.py cage_rule_chain # render one

Produces:
    <name>.png in this directory.
"""

import html
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Which figures to render, and how to lay each one out.
#
#   direction : "TD" (top-down) or "LR" (left-right); overrides the .mmd
#   width     : figure width in inches (6.10 == the full text+margin measure)
#   box_h     : height of one node box, inches
#   side      : which side of the main chain the off-chain nodes go on
# --------------------------------------------------------------------------
FIGURES = {
    "odd_taxonomy_reduced": dict(direction="TD", width=6.10, box_h=0.62, side="right"),
    "hara_procedure": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
    "sr_derivation": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
    "cage_rule_chain": dict(direction="TD", width=6.10, box_h=0.58, side="right"),
    "c05_emergency_states": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
    "control_cycle_sequence": dict(direction="TD", width=6.10, box_h=0.58, side="right"),
    "traceability_case_sr001": dict(direction="TD", width=6.10, box_h=0.62, side="right"),
    "sim2real_roadmap": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
}

# Entities the .mmd files actually use, plus the inline tags.
ENTITIES = {
    "&middot;": "·", "&ndash;": "–", "&mdash;": "—", "&rarr;": "→",
    "&larr;": "←", "&harr;": "↔", "&rArr;": "⇒", "&hArr;": "⇔",
    "&ge;": "≥", "&le;": "≤", "&ne;": "≠", "&asymp;": "≈",
    "&Delta;": "Δ", "&delta;": "δ", "&theta;": "θ", "&kappa;": "κ",
    "&sigma;": "σ", "&psi;": "ψ", "&mu;": "µ", "&deg;": "°",
    "&sup2;": "²", "&plusmn;": "±", "&times;": "×", "&hellip;": "…",
    "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
}

STYLE_FALLBACK = dict(fill="#F3F3F5", stroke="#5F5E5A", color="#2C2C2A", lw=1.0)


def clean(text: str) -> str:
    """Turn a mermaid node label into plain text with real newlines."""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</?(i|b|em|strong)>", "", text)
    for k, v in ENTITIES.items():
        text = text.replace(k, v)
    text = html.unescape(text)
    return text.strip().strip('"')


class Graph:
    """The parsed subset of one .mmd file."""

    def __init__(self):
        self.direction = "TD"
        self.labels = {}          # id -> display text
        self.shapes = {}          # id -> "box" | "round" | "cyl" | "diamond"
        self.solid = []           # (src, dst)
        self.dotted = []          # (src, dst, label)
        self.styles = {}          # class name -> style dict
        self.node_class = {}      # id -> class name


NODE_RE = re.compile(
    r"""(?P<id>[A-Za-z_][A-Za-z0-9_]*)\s*
        (?:
          \[\(\s*(?P<cyl>.*?)\s*\)\]      |
          \(\(\s*(?P<circ>.*?)\s*\)\)     |
          \{\s*(?P<diamond>.*?)\s*\}      |
          \(\s*(?P<round>.*?)\s*\)        |
          \[\s*(?P<box>.*?)\s*\]
        )""",
    re.X,
)


def parse(path: Path) -> Graph:
    """Parse one .mmd file into a Graph. Raises on anything unsupported."""
    g = Graph()
    body = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        body.append(line)

    if not body:
        raise ValueError(f"{path.name}: nothing but comments")

    m = re.match(r"(?:flowchart|graph)\s+(TD|TB|LR|RL|BT)\b", body[0])
    if not m:
        raise ValueError(f"{path.name}: first statement is not a flowchart header")
    g.direction = "TD" if m.group(1) in ("TD", "TB") else "LR"

    for line in body[1:]:
        # classDef name fill:#XXX,stroke:#YYY,color:#ZZZ,stroke-width:1.2px
        m = re.match(r"classDef\s+(\w+)\s+(.*)$", line)
        if m:
            name, decl = m.group(1), m.group(2)
            st = dict(STYLE_FALLBACK)
            for key, val in re.findall(r"([a-z-]+)\s*:\s*([^,;]+)", decl):
                val = val.strip()
                if key == "fill":
                    st["fill"] = val
                elif key == "stroke":
                    st["stroke"] = val
                elif key == "color":
                    st["color"] = val
                elif key == "stroke-width":
                    st["lw"] = float(val.rstrip("px")) * 0.8
            g.styles[name] = st
            continue

        m = re.match(r"class\s+([\w,\s]+?)\s+(\w+);?$", line)
        if m:
            for nid in m.group(1).split(","):
                g.node_class[nid.strip()] = m.group(2)
            continue

        # Dotted edge, with (`-. "label" .->`) or without (`-.->`) a label.
        m = re.match(
            r"([A-Za-z_]\w*)\s*-\.(?:\s*\"([^\"]*)\"\s*\.)?->\s*([A-Za-z_]\w*)", line)
        if m:
            g.dotted.append((m.group(1), m.group(3), m.group(2) or ""))
            _register_bare(g, m.group(1))
            _register_bare(g, m.group(3))
            continue

        # Node declarations anywhere on the line.
        for nm in NODE_RE.finditer(line):
            nid = nm.group("id")
            for shape, key in (("cyl", "cyl"), ("circ", "round"), ("diamond", "diamond"),
                               ("round", "round"), ("box", "box")):
                if nm.group(shape) is not None:
                    g.labels[nid] = clean(nm.group(shape))
                    g.shapes[nid] = key
                    break

        # Solid chains: A --> B --> C, with node declarations allowed inline.
        if "-->" in line:
            parts = re.split(r"-->", line)
            ids = []
            for part in parts:
                part = part.strip()
                m2 = re.match(r"([A-Za-z_]\w*)", part)
                if not m2:
                    raise ValueError(f"{path.name}: cannot read edge endpoint in {line!r}")
                ids.append(m2.group(1))
                _register_bare(g, m2.group(1))
            for a, b in zip(ids, ids[1:]):
                g.solid.append((a, b))
            continue

        if "---" in line or "==>" in line or "-.->" in line:
            raise ValueError(f"{path.name}: unsupported edge syntax in {line!r}")

    missing = [n for n in set(sum(([a, b] for a, b in g.solid), []) +
                              sum(([a, b] for a, b, _ in g.dotted), []))
               if n not in g.labels]
    if missing:
        raise ValueError(f"{path.name}: edges reference undeclared nodes {missing}")
    return g


def _register_bare(g: Graph, nid: str) -> None:
    g.shapes.setdefault(nid, "box")


def longest_chain(g: Graph):
    """Longest simple path over the solid edges. These graphs are small DAGs."""
    succ = {}
    for a, b in g.solid:
        succ.setdefault(a, []).append(b)
    nodes = set(succ) | {b for _, b in g.solid}
    best = []

    def walk(node, seen):
        nonlocal best
        path = seen + [node]
        if len(path) > len(best):
            best = path
        for nxt in succ.get(node, []):
            if nxt not in seen:
                walk(nxt, path)

    for n in nodes:
        walk(n, [])
    return best


def render(name: str) -> Path:
    """Render one figure by base name and return the PNG path."""
    cfg = FIGURES[name]
    g = parse(HERE / f"{name}.mmd")

    chain = longest_chain(g)
    off = [n for n in g.labels if n not in chain]

    width = cfg["width"]
    box_h = cfg["box_h"]
    gap = 0.20
    main_w = width * (0.56 if off else 0.86)
    main_x = 0.04 if off and cfg["side"] == "right" else (width - main_w) / 2
    side_w = width - main_w - 0.32 if off else 0.0
    side_x = main_x + main_w + 0.24

    def box_height(nid):
        n = len(g.labels[nid].split("\n"))
        return max(box_h, 0.17 + 0.128 * n)

    height = sum(box_height(n) for n in chain) + (len(chain) - 1) * gap + 0.16
    if off:
        height = max(height, sum(box_height(n) for n in off) + len(off) * gap + 0.16)

    # Full-bleed axes. plt.subplots() would leave the default ~22 % of
    # margin, which shrinks everything drawn in data units (the boxes) while
    # leaving everything sized in points (the text) untouched -- so labels
    # overflow their boxes by exactly that factor, and the "drawn at final
    # printed size" premise stops being true. With the axes spanning the whole
    # figure, one data unit is one inch and the measurement in place() is exact.
    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")

    def style_of(nid):
        return g.styles.get(g.node_class.get(nid, ""), STYLE_FALLBACK)

    def place(x, y, text, box_w, nominal, weight, colour, spacing=1.25):
        """
        Draw text centred at (x, y), shrunk until it actually fits box_w.

        Character-count heuristics are not good enough here: the labels mix
        digits, Greek and box-drawing arrows, whose advance widths differ by
        more than the margin available in a 2.3 in side column. So the text is
        drawn, measured through the renderer, and rescaled if it overflows --
        which is exact for whatever face matplotlib ends up using.
        """
        t = ax.text(x, y, text, ha="center", va="center", color=colour,
                    fontsize=nominal, fontweight=weight, linespacing=spacing,
                    zorder=4)
        fig.canvas.draw()
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        drawn_in = bb.width / fig.dpi
        limit_in = box_w - 0.10
        if drawn_in > limit_in:
            t.set_fontsize(max(3.6, nominal * limit_in / drawn_in))
        return t

    def draw_box(nid, x, y, w, h):
        st = style_of(nid)
        shape = g.shapes.get(nid, "box")
        rounding = 0.16 if shape in ("round", "cyl") else 0.05
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h,
                boxstyle=f"round,pad=0.0,rounding_size={rounding}",
                linewidth=st["lw"], edgecolor=st["stroke"],
                facecolor=st["fill"], zorder=3,
            )
        )
        lines = g.labels[nid].split("\n")
        head, detail = lines[0], lines[1:]
        if detail:
            place(x + w / 2, y + h * 0.73, head, w, 6.4, "bold", st["color"])
            place(x + w / 2, y + h * 0.30, "\n".join(detail), w, 5.3,
                  "normal", st["color"])
        else:
            place(x + w / 2, y + h / 2, head, w, 6.4, "bold", st["color"])

    pos = {}
    y = height - 0.08
    for nid in chain:
        h = box_height(nid)
        y -= h
        pos[nid] = (main_x, y, main_w, h)
        draw_box(nid, main_x, y, main_w, h)
        y -= gap

    # Side nodes, spread down the right-hand column.
    if off:
        step = (height - 0.16) / len(off)
        for i, nid in enumerate(off):
            h = box_height(nid)
            sy = height - 0.08 - step * (i + 0.5) - h / 2
            pos[nid] = (side_x, sy, side_w, h)
            draw_box(nid, side_x, sy, side_w, h)

    def anchor(nid, other):
        x, yy, w, h = pos[nid]
        ox, oy, ow, oh = pos[other]
        if abs((ox + ow / 2) - (x + w / 2)) > max(w, ow) / 2:
            # horizontal neighbour
            return (x + w, yy + h / 2) if ox > x else (x, yy + h / 2)
        return (x + w / 2, yy) if oy < yy else (x + w / 2, yy + h)

    for a, b in g.solid:
        p0, p1 = anchor(a, b), anchor(b, a)
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=9,
                                     linewidth=0.9, color="#6b6b6b", zorder=2))

    for a, b, lab in g.dotted:
        p0, p1 = anchor(a, b), anchor(b, a)
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=8,
                                     linewidth=0.8, color="#8a8a8a",
                                     linestyle=(0, (2.5, 2)), zorder=2))
        if lab:
            t = 0.22 + 0.16 * (g.dotted.index((a, b, lab)) % 3)
            ax.text(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + 0.04,
                    clean(lab), ha="center", va="bottom", fontsize=4.6,
                    color="#6b6b6b", style="italic", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.12", facecolor="white",
                              edgecolor="none", alpha=0.85))

    out = HERE / f"{name}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out.name}  ({len(chain)} in chain, {len(off)} side)")
    return out


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(FIGURES)
    for fig_name in wanted:
        render(fig_name)
