# `latex_psithesis` — the thesis set in the PSIThesis template

An alternative typesetting of the thesis, built on the **PSIThesis** class from
`manuscript/fisba48428.pdf` (Dominik Herrmann, University of Bamberg — a
`kaobook`-derived layout). It exists so the manuscript can be *seen* in that
layout; it is **not** the submission build.

> **This is a parallel rendering, not a new source of truth.** The authoritative
> submission source stays `manuscript/draft_v5/` (Spanish) built by
> `tools/build_thesis_docx.py`. The `.tex` files here are **generated** from
> `manuscript/draft_v5_en/` by `md2tex.py` and never feed back into it. When a
> result changes, change `manuscript/chapters/` first, then `draft_v5/` and
> `draft_v5_en/`, exactly as `manuscript/README.md` says — then re-run
> `python md2tex.py` if this rendering is still wanted.

## Regenerate, build, upload

```bash
cd manuscript/latex_psithesis
python md2tex.py            # chapters/, appendices/, front/, literature.bib
python md2tex.py --zip      # the same, plus ../thesis-psithesis-overleaf.zip
```

No third-party Python packages; it runs on the Windows authoring host.
**Never edit the generated `.tex` files or `literature.bib` by hand** — the next
run overwrites them. Edit the Markdown, `margin_notes.md`, or the converter.

**Overleaf.** *New Project → Upload Project* with
`manuscript/thesis-psithesis-overleaf.zip`; the zip already contains the
figures, the fonts and a `latexmkrc` that selects LuaLaTeX. If Overleaf still
compiles with pdfLaTeX, set *Menu → Compiler → LuaLaTeX* by hand. pdfLaTeX
cannot build this template (fontspec + TTF/OTF fonts).

**Locally** (TeX Live 2020 or newer):

```bash
make            # lualatex -shell-escape, biber, lualatex, lualatex
```

**Verified build (17.09.2026).** Compiled on the Windows authoring host with
TinyTeX (LuaHBTeX 1.24.0, TeX Live 2026, biber 2.22), from the unpacked Overleaf
zip: 0 errors, 0 undefined references or citations, 0 missing glyphs, no
overfull box above 1.3 pt outside the template's own chapter-title line.
**155 pages:** 18 front matter, 98 body (Chapters 1–12), 36 appendices,
3 references. Two packages the template needs are no longer where `deps.txt`
used to say: `scrhack` was split out of `koma-script`, and `centernot` lives in
`oberdiek`; `deps.txt` lists both now.

## What `md2tex.py` does

| Markdown | LaTeX |
| --- | --- |
| `# Chapter N — Title`, `## N.M …` | `\chapter` + `\label{ch:NN}`, `\section` + `\label{sec:N.M}` |
| `(Author et al., 2025)` | `\cite{key}`, e.g. `[CLL25]` (the template's alphabetic style) |
| `Author et al. (2025)` | names kept as written + `\cite{key}` |
| `Chapter 8`, `Figure 7.1`, `Table F.1`, `Appendix G`, `§9.3.6` | same words, number linked with `\ref` |
| `H-01`, `SR-001`, `C-06`, `SC-PERT-13`, `M-S1`, `D-69` | `\hz`, `\sr`, `\cagerule`, `\scn`, `\met`, `\dec` |
| other hyphenated labels (`TBD-Q10`, `ODD-3`, `GE4-V2`) | `\mbox{…}` — never split at the hyphen |
| `` `NOT SATISFIED` `` | `\verdictnot` |
| `<img …>` + `*Figure N.M — caption*` | `figure` (text column) or `figure*` (text + margin), width from the DOCX width |
| pipe table + `*Table N.M — caption*` | see *Tables* below |
| Greek, arrows, `×`, `≤`, superscripts in prose | maths mode (Cochineal has no Greek); left as is inside code, set in Iosevka, which has them |
| `back/0_bibliography.md` | `literature.bib`, with `\nocite{*}` so the list printed matches the Markdown list |

Keys are `<first surname><year><suffix>` (`kuutti2021b`); standards use their
number (`iso26262`, `isotr5469`, `isopas8800`, `ul4600`). The converter reports
every citation, cross reference, figure file or margin-note anchor it cannot
resolve — a clean run prints no `WARNING` line.

### Tables

The column layout is computed from the content, not typed: every column starts
at the width of its longest unbreakable run (identifiers, short code tokens,
header words), and the remaining width goes, step by step, to whichever column
shortens the table most. Short columns (IDs, S/E/C ratings, check marks) stay
tight and prose columns get the room. A block of check-mark columns under long
headers (Table 2.1, Table G.1) gets rotated headers.

* **Body chapters.** A table that fits the 107 mm text column stays there;
  anything wider becomes a `table*` float over text + margin column (164.6 mm).
  `table*` (from `sidenotes`) moves into the margin on the correct side of odd
  and even pages.
* **Appendices.** `main.tex` switches the appendices to a full-width geometry
  with no margin column. **This is the fix for the tables that broke on
  Overleaf:** the hand conversion widened page-breaking `longtable`s into the
  margin column, which works on odd pages and runs off the paper on even ones,
  where the margin column sits on the *left*. A page-breaking table cannot
  follow the margin from page to page, so the appendices do without it. Long
  registers (A.1, B.1, D.1, D.2, F.1, F.2, G.1, I.1) are `longtable`s with a
  repeated header and a *continued* line; tables that fit in half a page (H.1–H.3,
  I.2–I.5) are ordinary floats.
* The header row of Appendix D's two tables is missing in the Markdown and is
  supplied by the converter (`SUPPLIED_TABLE_HEADERS`); appendix tables without
  a caption line get one from `SUPPLIED_TABLE_CAPTIONS`, because a table without
  a caption cannot be referenced and the text does reference *Table F.1*.

Each generated table carries a comment with its layout, e.g.
`% layout: longtable, fixed, \footnotesize, 164 of 165 mm`.

### Margin notes

`margin_notes.md` holds short notes that explain a term where it first matters
(safety cage, ODD, hysteresis, co-adaptation, rectification, handedness …), and
the *PRELIMINARY* flag next to the physical driving figures of Chapter 9. They
exist only in this rendering. Each note names its chapter and an anchor phrase
copied from the Markdown; the converter places it as a numbered `\sidenote`
right after the first occurrence of the anchor. Rules, kept in the file itself:
a note explains or points, it adds no result; anchors must be in running text
(not headings, captions or tables); appendices have no margin, so no notes.

## What came from upstream, and what was changed

| File | Provenance |
| --- | --- |
| `PSIThesis.cls` | **verbatim** from upstream (LPPL v1.3c) |
| `misc/setup.tex`, `misc/commands.tex` | **verbatim** from upstream |
| `fonts/` | **verbatim** — Roboto (Apache 2.0) and Iosevka SS04 (OFL), vendored so the project builds offline. Cochineal comes from TeX Live. |
| `deps.txt` | upstream list + `scrhack`, `setspaceenhanced`, `oberdiek` |
| `misc/titlepage.tex` | **rewritten** for Hochschule Esslingen |
| `main.tex` | **rewritten** — thesis information, front matter, 12 chapters, 9 appendices, full-width appendix geometry |
| `misc/thesis-commands.tex` | **new** — project macros, float placement, see below |
| `md2tex.py`, `margin_notes.md`, `latexmkrc` | **new** |
| `chapters/`, `appendices/`, `front/`, `literature.bib` | **generated** by `md2tex.py` |

Changes to the title page against the stock one: the Bamberg logo and the
guide's DOI/version block are removed; thesis type, degree programme, subtitle,
both examiners, matriculation number and submission date are added, because the
HS Esslingen guidelines require them. The cover data live in `main.tex`, not in
the converter — if `draft_v5_en/front/00_cover.md` changes, change `main.tex`.

## Project macros (`misc/thesis-commands.tex`)

```latex
\hz{01} \sr{003} \cagerule{06} \scn{NOM-01} \met{S1} \dec{69} \gate{4}
\verdictsat \verdictnot \verdictind \verdictna \verdictopen
\enf \mon \prelimflag \retracted{...} \caveat{...}
```

The identifier macros typeset a non-breaking hyphen, so an identifier never
splits across a line. The verdict macros set the aggregator's **literal**
verdicts in the monospace face and in colour, so a verdict in prose reads as a
machine output rather than as the author's adjective. `\prelimflag` puts the
evidence-status qualifier in the margin. The file also raises the float
fractions (`\topfraction` 0.9, `\textfraction` 0.07, `\floatpagefraction` 0.6),
because most floats here span text + margin and the defaults leave half-empty
pages, and sets `\emergencystretch` for the narrow text column.

## What this layout does to the page budget

The HS Esslingen guidelines cap the body at **80–100 pages**. This layout is not
the one that budget was set against:

| | current DOCX build | PSIThesis |
| --- | --- | --- |
| Text column | 159.2 mm | **107 mm** (+ 49.4 mm margin column) |
| Line spacing | 1.15 | single |
| Body face | Arial 11 pt | Cochineal 11 pt |

Measured here: **98 body pages** (17.09.2026 build). That number describes this
rendering only; the submission budget is measured on the DOCX with
`tools/thesis_page_budget.py`.

## Static checks

```bash
make check
```

or, without `make`:

```bash
perl check_tex.pl chapters/*.tex appendices/*.tex front/*.tex
perl check_complete.pl
perl check_refs.pl chapters/*.tex appendices/*.tex front/*.tex
```

`check_tex.pl` looks for what would stop a build (escaping, brace balance,
environment nesting, unknown macros, bare Greek outside maths and code).
`check_complete.pl` compares every `.tex` with its Markdown — section counts
must match, running-word ratio must stay in 0.90–1.12, margin notes excluded —
and lists the files that trip a threshold for a reason checked by hand.
`check_refs.pl` finds `\ref` targets that are never labelled.

**Status (17.09.2026): all three pass** — 0 errors; 0 unexplained completeness
flags (4 verified exceptions); 245 labels, none dangling or duplicated. Now that
a real build exists these checks are a fast pre-flight, not a substitute.

## Known gaps

1. **No institutional logo.** `misc/titlepage.tex` has a commented
   `\includegraphics` waiting for `misc/hse-logo.pdf` (a vector PDF, not a PNG).
2. **The language is English.** `manuscript/README.md` records that the
   guidelines ask for standard English while the submission manuscript is in
   Spanish, unconfirmed with the supervisor. Converting `draft_v5/` instead would
   need the Spanish chapter/figure/table words in the converter's patterns.
3. **Figure placement is LaTeX's.** Floats go `[htbp]`; a figure can land a page
   after its first mention, and the last table of an appendix can end up alone on
   the appendix's final page. The PDF has been checked page by page for tables,
   not tuned by hand.
4. **Overleaf's TeX Live is older than the one used here.** The build was
   verified on TeX Live 2026, not on Overleaf itself.

## Licence

The template — `PSIThesis.cls`, `misc/setup.tex`, `misc/commands.tex` and the
title-page structure — is by **Dominik Herrmann**, University of Bamberg:
<https://github.com/UBA-PSI/psi-thesis-guide>. The guide is CC BY-SA 4.0; the
class file is LPPL v1.3c. It derives in turn from *MastersDoctoralThesis.cls*
(LaTeXTemplates.com). The thesis content is the author's own.
