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
    python mmd_render.py fig_5_1_cage_rule_chain # render one

Produces:
    <name>.png in this directory.
"""

import html
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as MplPath

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Which figures to render, and how to lay each one out.
#
#   direction : "TD" (top-down) or "LR" (left-right); overrides the .mmd
#   width     : figure width in inches (6.10 == the full text+margin measure)
#   box_h     : height of one node box, inches
#   side      : which side of the main chain the off-chain nodes go on
# --------------------------------------------------------------------------
# Three .mmd files in this directory are deliberately absent from this table,
# because this module renders flowcharts and none of them is one. Listing them
# here did not make them renderable: it only made `python mmd_render.py` with
# no arguments die on the first of them.
#
#   fig_4_1_odd_taxonomy_reduced  `subgraph` blocks and undirected `---` links.
#                                 Figure 4.1 is drawn by its own renderer,
#                                 fig_4_1_odd_taxonomy.py, which transcribes it.
#   c05_emergency_states          a `stateDiagram-v2`.
#   control_cycle_sequence        a `sequenceDiagram`.
#
# The last two render no figure in the manuscript; they are structure sources,
# which is also why they keep a descriptive name instead of a chapter number.
FIGURES = {
    "fig_4_2_hara_procedure": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
    "fig_4_3_sr_derivation": dict(direction="TD", width=6.10, box_h=0.60, side="right"),
    "fig_5_1_cage_rule_chain": dict(direction="TD", width=6.10, box_h=0.58, side="right"),
    "fig_10_1_traceability_case_sr001": dict(direction="TD", width=6.10, box_h=0.62, side="right"),
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
    # The space between the two columns is a routing lane, not spare margin:
    # every dotted edge travels along it and every edge label sits inside it.
    # At 0.24 in there was room for neither, so the edges were drawn as
    # diagonals over the top of the figure and the labels were dropped on the
    # boxes. It is widened only where labels actually have to fit, because the
    # room comes out of the two columns and an unlabelled edge does not need it.
    labelled = any(lab for _, _, lab in g.dotted)
    gutter = 0.50 if labelled else 0.24
    main_w = width * ((0.54 if labelled else 0.56) if off else 0.86)
    main_x = 0.04 if off and cfg["side"] == "right" else (width - main_w) / 2
    side_w = width - main_w - 0.08 - gutter if off else 0.0
    side_x = main_x + main_w + gutter
    gutter_x = main_x + main_w + gutter / 2

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

    # Side nodes go BESIDE the node they attach to -- what the header of this
    # module has always said the layout does, and what it did not do. They were
    # spread evenly down the column in declaration order, so an annotation on
    # the first step and one on the last step could land in each other's place
    # and their edges then crossed the whole figure diagonally to reach back.
    # Anchored at their neighbour's height, the same edges are short and
    # horizontal. A side node with no edge into the chain keeps its even slot.
    if off:
        centre = {n: pos[n][1] + pos[n][3] / 2 for n in chain}
        edges = [(a, b) for a, b, _ in g.dotted] + list(g.solid)
        step = (height - 0.16) / len(off)
        want = {}
        for i, nid in enumerate(off):
            near = [centre[o] for e in edges if nid in e
                    for o in e if o in centre]
            want[nid] = (sum(near) / len(near) if near
                         else height - 0.08 - step * (i + 0.5))

        rows = [[nid, want[nid] - box_height(nid) / 2, box_height(nid)]
                for nid in sorted(off, key=lambda n: -want[n])]
        # Preferred positions can overlap; two clamping passes separate them.
        # The figure height was sized to hold the entire column, so whatever
        # the downward pass has to force, the upward pass can undo.
        top = height - 0.08
        for row in rows:
            row[1] = min(row[1], top - row[2])
            top = row[1] - gap
        bottom = 0.08
        for row in reversed(rows):
            row[1] = max(row[1], bottom)
            bottom = row[1] + row[2] + gap

        for nid, sy, h in rows:
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

    def dotted_arrow(verts):
        """An orthogonal dotted run through the gutter, arrowhead at the end."""
        codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(verts) - 1)
        ax.add_patch(FancyArrowPatch(
            path=MplPath(verts, codes), arrowstyle="-|>", mutation_scale=8,
            linewidth=0.8, color="#8a8a8a", linestyle=(0, (2.5, 2)),
            shrinkA=0, shrinkB=0, zorder=2))

    def dotted_line(x0, y0, x1, y1):
        ax.plot([x0, x1], [y0, y1], color="#8a8a8a", linewidth=0.8,
                linestyle=(0, (2.5, 2)), zorder=2)

    def edge_label(text, x, y):
        """
        An edge label, wrapped to fit the gutter it now lives in.

        These used to be dropped at a fixed fraction along a diagonal, with an
        opaque background: in Figure 4.2 that background erased a piece of the
        border of the very box the edge came from, which is why the edge looked
        like it started out of nowhere. There is nothing to erase in the gutter.
        """
        words = text.split()
        if len(words) > 1:
            cut = min(range(1, len(words)),
                      key=lambda i: abs(len(" ".join(words[:i]))
                                        - len(" ".join(words[i:]))))
            text = " ".join(words[:cut]) + "\n" + " ".join(words[cut:])
        t = ax.text(x, y, text, ha="center", va="center", fontsize=4.6,
                    color="#6b6b6b", style="italic", linespacing=1.2, zorder=5,
                    bbox=dict(boxstyle="round,pad=0.10", facecolor="white",
                              edgecolor="none", alpha=0.9))
        fig.canvas.draw()
        drawn = t.get_window_extent(renderer=fig.canvas.get_renderer()).width / fig.dpi
        if drawn > gutter - 0.04:
            t.set_fontsize(max(3.4, 4.6 * (gutter - 0.04) / drawn))

    # A dotted edge is an annotation -- an off-chain box commenting on the
    # chain -- so it is routed orthogonally along the gutter instead of being
    # drawn as a diagonal across everything else. Grouped by source, because
    # one source with several targets is a different drawing problem.
    by_source = {}
    for a, b, lab in g.dotted:
        by_source.setdefault(a, []).append((b, lab))

    for src, targets in by_source.items():
        sx, sy, sw, sh = pos[src]
        src_c = sy + sh / 2
        ends = [(pos[t][1] + pos[t][3] / 2, pos[t][0] + pos[t][2]) for t, _ in targets]

        if not all(pos[t][0] < sx for t, _ in targets):
            # Not the side-column-to-chain case this routing is for; a straight
            # line is the right drawing between neighbours.
            for t, lab in targets:
                p0, p1 = anchor(src, t), anchor(t, src)
                dotted_arrow([p0, p1])
                if lab:
                    edge_label(clean(lab), (p0[0] + p1[0]) / 2,
                               (p0[1] + p1[1]) / 2 + 0.09)
            continue

        if len(ends) >= 3:
            # One box annotating three or more links -- "this is checked on
            # every one of them". As separate edges that is a fan of diagonals
            # that overlap each other and have to be traced one by one; as a
            # spine with a tick into each target it is a single shape, and it
            # says "all of these" the way the sentence does.
            span = [c for c, _ in ends] + [src_c]
            dotted_line(gutter_x, min(span), gutter_x, max(span))
            dotted_line(sx, src_c, gutter_x, src_c)
            for c, right in ends:
                dotted_arrow([(gutter_x, c), (right, c)])
            continue

        for (t, lab), (c, right) in zip(targets, ends):
            if abs(src_c - c) < 0.012:
                dotted_arrow([(sx, src_c), (right, c)])
            else:
                dotted_arrow([(sx, src_c), (gutter_x, src_c),
                              (gutter_x, c), (right, c)])
            if lab:
                edge_label(clean(lab), gutter_x, c + 0.10)

    out = HERE / f"{name}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {out.name}  ({len(chain)} in chain, {len(off)} side)")
    return out


if __name__ == "__main__":
    wanted = sys.argv[1:] or list(FIGURES)
    for fig_name in wanted:
        render(fig_name)
