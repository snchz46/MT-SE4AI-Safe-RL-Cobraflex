# `latex_psithesis` — the thesis set in the PSIThesis template

An alternative typesetting of the thesis, built on the **PSIThesis** class from
`manuscript/fisba48428.pdf` (Dominik Herrmann, University of Bamberg — a
`kaobook`-derived layout). It exists so the manuscript can be *seen* in that
layout; it is **not** the submission build.

> **This is a parallel rendering, not a new source of truth.** The authoritative
> submission source stays `manuscript/draft_v5/` (Spanish) built by
> `tools/build_thesis_docx.py`. The `.tex` files here were converted from
> `manuscript/draft_v5_en/` and **do not feed back into it**. When a result
> changes, change `manuscript/chapters/` first, then `draft_v5/`, exactly as
> `manuscript/README.md` says — and re-convert here only if this rendering is
> still wanted.

## Build

**LuaLaTeX only.** The class loads TTF/OTF faces through `fontspec` and calls
`microtype`'s `\textls` on the title page. `pdflatex` cannot build it.

```bash
cd manuscript/latex_psithesis
make
```

which is

```bash
lualatex -shell-escape main.tex && biber main && \
lualatex -shell-escape main.tex && lualatex -shell-escape main.tex
```

Neither LuaLaTeX nor a TeX distribution is installed on the Windows authoring
host. Build on the Ubuntu compute host (`texlive-full`, or the package list in
`deps.txt`), or on Overleaf.

**On Overleaf.** The upstream guide (2020) records that Overleaf could *not*
compile this template, because Overleaf then shipped `lualatex` 1.07 from TeX
Live 2018, which hits a `microtype` bug. Overleaf has moved to much newer TeX
Live since, so it is expected to work now — **this has not been verified.** If
it fails on `(vf): invalid DVI command (1)`, that is the same bug: drop the
`microtype` line from `misc/setup.tex` and remove the `\textls` call in
`misc/titlepage.tex`.

## What came from upstream, and what was changed

| File | Provenance |
| --- | --- |
| `PSIThesis.cls` | **verbatim** from upstream (LPPL v1.3c) |
| `misc/setup.tex`, `misc/commands.tex` | **verbatim** from upstream |
| `fonts/` | **verbatim** — Roboto (Apache 2.0) and Iosevka SS04 (OFL), vendored so the project builds offline. Cochineal comes from TeX Live. |
| `deps.txt` | **verbatim** — the TeX package list |
| `misc/titlepage.tex` | **rewritten** for Hochschule Esslingen |
| `main.tex` | **rewritten** — thesis information, front matter, 12 chapters, 9 appendices |
| `Makefile` | rewritten (upstream's Docker and `pdf/` move targets dropped) |
| `misc/thesis-commands.tex` | **new** — project macros, see below |
| `literature.bib` | **generated** from `../draft_v5_en/back/0_bibliography.md` |
| `chapters/`, `appendices/`, `front/` | **converted** from `../draft_v5_en/` |

Changes to the title page against the stock one: the Bamberg logo and the
guide's DOI/version block are removed; thesis type, degree programme, subtitle,
both examiners, matriculation number and submission date are added, because the
HS Esslingen guidelines require them. The geometry option `showframe` — which
upstream deliberately leaves *on* to illustrate the type block — is off.

## Project macros (`misc/thesis-commands.tex`)

The thesis runs on a single non-reusable identifier space
(`docs/01_id_conventions.md`). Marking those identifiers semantically rather
than typing them as literal text means one place to change how they look, and a
grep-able source a traceability checker could be pointed at.

```latex
\hz{01}         % H-01     hazard
\sr{003}        % SR-003   safety requirement
\cagerule{06}   % C-06     cage rule
\scn{NOM-01}    % SC-NOM-01 scenario
\met{S1}        % M-S1     metric
\dec{69}        % D-69     recorded decision
\gate{4}        % G4       gate
```

All of them typeset a non-breaking hyphen, so an identifier never splits across
a line break.

```latex
\verdictsat \verdictnot \verdictind \verdictna \verdictopen
```

set the aggregator's **literal** verdicts in the monospace face and in colour, so
that a verdict in running prose reads as a machine output rather than as the
author's adjective — a distinction the thesis leans on repeatedly. Use them only
for the literal; the ordinary English words stay ordinary text.

`\enf` / `\mon` set the two campaign modes. `\prelimflag` and `\retracted{...}`
put evidence-status qualifiers in the margin. `\fig`, `\figwide`, `\figmargin`
and `\figmissing` are the figure wrappers; `\qmm`, `\qm`, `\qmps`, `\qdeg`,
`\qhz`, `\qs`, `\qpc` are `siunitx` shorthands (prefixed `q` so nothing in the
kernel is clobbered — `\deg`, `\m` and `\sec` already exist).

## What this layout does to the page budget

The HS Esslingen guidelines cap the body at **80–100 pages**. This layout is
**not** the layout that budget was set against, and neither is the current DOCX:

| | current DOCX build | PSIThesis |
| --- | --- | --- |
| Text column | 159.2 mm | **107 mm** |
| Margin column | — | **49.4 mm**, permanent |
| Line spacing | 1.15 | single |
| Body face | Arial 11 pt | Cochineal 11 pt |

A 33 % narrower measure at roughly 72 characters per line instead of 95, against
about 52 lines per page instead of 46. That points at **something like 15–20 %
more body pages** — but that is an **estimate from geometry, not a measurement**,
and it ignores the two offsets that work the other way: material moved into the
margin column, and tables and figures widened to `\widefigurewidth`.

`manuscript/README.md` already records the page budget as unverified, because
`tools/thesis_page_budget.py` needs Word COM and has not run since the
typography changed. **Nothing here settles it.** Measure a real build
(`make pages`, or `pdfinfo main.pdf`) before concluding anything, and do not
quote the 96-page figure from the 31.07.2026 build against this layout.

## Static checks — the stand-in for a trial compile

```bash
make check
```

or, where `make` is not installed (the Windows authoring host has no `make`):

```bash
perl check_tex.pl chapters/*.tex appendices/*.tex front/*.tex
perl check_complete.pl
perl check_refs.pl chapters/*.tex appendices/*.tex front/*.tex
```

`check_tex.pl` answers *would it compile*: unescaped `%` `&` `_` `#` `$` in
text, brace balance, environment nesting, macros that are not defined anywhere
in this project, argument counts on `\fig` / `\figwide` / `\figmissing`, table
rows whose `&` count disagrees with the declared column spec (expanding
`*{n}{...}` repetitions), bare Greek and maths glyphs outside math mode — which
matter because Cochineal has no Greek — plus warnings for leftover Markdown,
`\sidenote` inside a float, and `longtable` without `\endhead`.

`check_complete.pl` answers the other half, *is it still the same document*: it
compares each `.tex` against the Markdown it came from on section and
subsection counts, which must match exactly, and on running-word count after
markup is stripped from both sides, which must land in a 0.90–1.12 band. Below
the band means text went missing; above usually means Markdown leaked through.
Three files trip a threshold for a reason that was checked by hand and is not
content loss; they are listed in the script as **verified exceptions**, each
with the evidence that settled it, so that anything else tripping is genuinely
unexplained.

`check_refs.pl` catches the one defect that only exists *between* files: a
`\Cref` whose `\label` is never defined. LaTeX renders those as `??` and emits
only a warning, so they survive a successful build and reach the examiner.

**Status: all three pass.** 0 errors and 0 warnings on all 25 files; 0
unexplained completeness flags; 217 labels, 56 references, none dangling and
none duplicated.

**None of this is proof.** They cannot catch a table too wide for its column, a
float that lands three pages from its reference, or a sentence whose meaning
changed. They exist because the authoring host has no TeX.

## Known gaps

1. **Nothing here has been compiled.** No TeX distribution exists on the
   authoring host. Both static checks pass on every converted file, but
   **checking is not building**. Expect to fix some errors on the first real
   run — most likely float placement, a table overflowing the 107 mm column,
   and undefined `\Cref` targets.
2. ~~**Two figures are missing.**~~ **Resolved (05.09.2026).**
   `manuscript/figures/auto/` is *not* empty on the Windows authoring host:
   `fig_ppo2d_training_curve.png` and `fig_ppo2d_action_distribution.png` are
   both there. The two `\figmissing` placeholders became real `\figwide` calls
   and no placeholder remains anywhere in the document. This was the
   three-machine trap in reverse: the note assumed the compute host's state.
3. **No institutional logo.** `misc/titlepage.tex` has a commented
   `\includegraphics` waiting for `misc/hse-logo.pdf`. A vector PDF, not a PNG.
4. **The language is English.** `manuscript/README.md` records that the
   guidelines ask for standard English while the submission manuscript is in
   Spanish, and that this is unconfirmed with the supervisor. This rendering
   uses `draft_v5_en/`; converting `draft_v5/` instead is a swap of the source
   directory, nothing more.
5. **Cross-references are conservative.** `\Cref` was used only where the target
   label certainly exists. Some "see Chapter 8" mentions are still plain text.
6. **Two source defects were repaired, not transcribed.** Both are noted in a
   comment at the top of the file that carries them. **Appendix D**'s two tables
   have no header row in the Markdown — the rows begin directly with data — so
   headers were supplied from the column contents; this is the only place where
   content was added rather than converted. **Appendix F**'s first table carries
   superscript markers 1–7 and 9 whose footnote texts do not exist anywhere in
   the source; they are transcribed verbatim and remain dangling until the notes
   are written.
7. **Appendix C is renumbered.** Its source hand-numbers 13 `##` headings under
   two `#` divisions, skipping C.3 and restarting at C.1, and one subsection
   headed "Middleware" is actually about the RL algorithm. The manual numbers
   were dropped so LaTeX numbers the appendix consistently; no heading text was
   changed and nothing cross-references those numbers. **The mis-titled heading
   was left alone** — that is an editorial call, not a typesetting one.

## Licence

The template — `PSIThesis.cls`, `misc/setup.tex`, `misc/commands.tex` and the
title-page structure — is by **Dominik Herrmann**, University of Bamberg:
<https://github.com/UBA-PSI/psi-thesis-guide>. The guide is CC BY-SA 4.0; the
class file is LPPL v1.3c. It derives in turn from *MastersDoctoralThesis.cls*
(LaTeXTemplates.com). The thesis content is the author's own.
