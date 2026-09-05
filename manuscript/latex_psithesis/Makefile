# Build the thesis with the PSIThesis template.
#
# REQUIRES LuaLaTeX. pdfLaTeX cannot build this document: the template loads
# TTF/OTF fonts through fontspec and uses microtype's \textls on the title page.
#
#   make          -- full build (lualatex, biber, lualatex, lualatex)
#   make quick    -- single pass, for checking a change fast (refs will be stale)
#   make clean    -- remove every generated file
#
# TeX Live 2020 or newer is recommended; see ../latex_psithesis/README.md for
# the known issues with older lualatex + microtype.

SOURCES = main.tex \
          misc/setup.tex misc/commands.tex misc/thesis-commands.tex misc/titlepage.tex \
          $(wildcard front/*.tex) \
          $(wildcard chapters/*.tex) \
          $(wildcard appendices/*.tex) \
          literature.bib

OPTS = -shell-escape -interaction=nonstopmode -halt-on-error

main.pdf: $(SOURCES)
	lualatex $(OPTS) main.tex
	biber main
	lualatex $(OPTS) main.tex
	lualatex $(OPTS) main.tex

.PHONY: quick
quick:
	lualatex $(OPTS) main.tex

# Static checks. These stand in for a trial compile on hosts with no TeX
# distribution -- they do not prove the document builds, but they catch the
# defects a Markdown-to-LaTeX conversion actually produces.
#   check-tex       escaping, brace balance, environment nesting, unknown
#                   macros, figure arity, table column counts, bare Greek
#   check-complete  section counts and word ratios against the Markdown source,
#                   i.e. "did the conversion silently drop or summarise text"
#   check-refs      cross-file: a \Cref whose \label is never defined renders as
#                   "??" and is only a WARNING in the log, so it survives a
#                   successful build. Per-file checks cannot see it.
.PHONY: check check-tex check-complete check-refs
check: check-tex check-complete check-refs

check-tex:
	perl check_tex.pl chapters/*.tex appendices/*.tex front/*.tex

check-complete:
	perl check_complete.pl

check-refs:
	perl check_refs.pl chapters/*.tex appendices/*.tex front/*.tex

.PHONY: clean
clean:
	rm -f main.aux main.bbl main.bcf main.blg main.log main.lof main.lot \
	      main.out main.toc main.run.xml main.synctex.gz main.pdf
	rm -f chapters/*.aux appendices/*.aux front/*.aux misc/*.aux

# Page budget check: the HS Esslingen guidelines cap the body at 80-100 pages.
# This layout is NOT the layout that budget was set against -- see README.
.PHONY: pages
pages: main.pdf
	@pdfinfo main.pdf | grep Pages || echo "install poppler-utils for pdfinfo"
