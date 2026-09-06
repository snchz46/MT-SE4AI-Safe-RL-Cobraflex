"""
Strip the in-image title band from plot PNGs that carry one.

WHY. Several plots in this directory were rendered with a matplotlib
`suptitle` that hard-codes a figure number ("Fig. 7.2 — ...") and, in two
cases, a leftover temporary run path ("run .figcut_tmp"). Both are wrong in
the manuscript: the figure number belongs to the document, not to the image,
and it no longer matches after the chapters were condensed; the temp path is
simply an artefact of how the plot was produced.

Regenerating them properly needs the run data, which lives on the compute
host. Cropping the title band is the lossless alternative -- no plotted data
is touched -- and the caption in the manuscript carries the title anyway.

The crop row is found, not guessed: the script scans down from the top for
the first row that looks like an axes frame (a long run of dark pixels), and
cuts a few pixels above it.

Run:
    python crop_titles.py                 # every entry in SOURCES
    python crop_titles.py fig_7_2_intervention_newcam

Produces:
    <name>_notitle.png next to the original. The original is never modified.
"""

import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent

# Plots whose baked-in title contradicts the manuscript's own numbering.
SOURCES = [
    "fig_7_2_intervention_newcam",
    "fig_7_8_multiseed_newcam",
]

DARK = 128          # a pixel this dark counts as frame ink
MIN_RUN_FRACTION = 0.55   # a frame row is dark across at least this much width
PAD_ABOVE = 1       # keep the frame line itself; any more catches title descenders


def find_frame_row(im: Image.Image) -> int:
    """Row index of the first axes frame line, scanning from the top."""
    grey = im.convert("L")
    w, h = grey.size
    px = grey.load()
    for y in range(h):
        dark = sum(1 for x in range(0, w, 2) if px[x, y] < DARK)
        if dark >= (w / 2) * MIN_RUN_FRACTION:
            return y
    raise ValueError("no axes frame row found; is this a plot?")


def crop(name: str) -> Path:
    """Write <name>_notitle.png with the title band removed."""
    src = HERE / f"{name}.png"
    im = Image.open(src)
    top = max(0, find_frame_row(im) - PAD_ABOVE)
    out = HERE / f"{name}_notitle.png"
    im.crop((0, top, im.size[0], im.size[1])).save(out)
    print(f"{src.name}: cropped {top} px of title band -> {out.name}")
    return out


if __name__ == "__main__":
    for figure in (sys.argv[1:] or SOURCES):
        crop(figure)
