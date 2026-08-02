#!/usr/bin/env python3
"""Measure the built thesis against the 80-100 page body budget.

Drives Microsoft Word (COM) to repaginate and export a PDF, then reports where
each chapter starts and how many pages the *body of the text* occupies -- the only
figure the HS Esslingen guidelines put a number on.

Usage:
    python tools/thesis_page_budget.py "B:/SE4AI/Documentos/draft_V5.docx"
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PS = [
    "powershell",
    "-NoProfile",
    "-NonInteractive",
    "-Command",
]

EXPORT = r"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
    $doc = $word.Documents.Open('{docx}', $false, $true)
    $doc.Fields.Update() | Out-Null
    $doc.Repaginate()
    $doc.SaveAs2('{pdf}', 17)
    Write-Output ("PAGES=" + $doc.ComputeStatistics(2))
    Write-Output ("WORDS=" + $doc.ComputeStatistics(0))
    $doc.Close($false)
}} finally {{
    $word.Quit()
}}
"""


def word_export(docx: Path, pdf: Path) -> dict[str, int]:
    script = EXPORT.format(docx=str(docx).replace("/", "\\"), pdf=str(pdf).replace("/", "\\"))
    res = subprocess.run(PS + [script], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise SystemExit("Word export failed")
    stats = {}
    for line in res.stdout.splitlines():
        m = re.match(r"(\w+)=(\d+)", line.strip())
        if m:
            stats[m.group(1)] = int(m.group(2))
    return stats


def analyse(pdf: Path) -> None:
    import fitz

    doc = fitz.open(pdf)
    total = doc.page_count
    chapter = re.compile(r"^\s*CAP[ÍI]TULO\s+(\d+)", re.M | re.I)
    anexo = re.compile(r"^\s*(ANEXO|AP[ÉE]NDICE)\s+([A-Z])", re.M | re.I)
    biblio = re.compile(r"^\s*BIBLIOGRAF[ÍI]A", re.M | re.I)

    starts: list[tuple[int, str]] = []
    for i, page in enumerate(doc, start=1):
        txt = page.get_text()
        # only a real section opener: first non-blank line of the page, and not a
        # table-of-contents row (those carry dot leaders and a trailing page number)
        head_lines = [ln for ln in txt.split("\n")[:3] if ln.strip()]
        head = "\n".join(head_lines)
        if "...." in head:
            continue
        for rx in (chapter, anexo, biblio):
            m = rx.search(head)
            if m:
                end = head.find("\n", m.start())
                line = head[m.start() : end if end > 0 else len(head)].strip()
                starts.append((i, line[:64]))
                break

    seen: set[str] = set()
    uniq = []
    for pg, line in starts:
        key = re.sub(r"\s+", " ", line)[:24]
        if key in seen:
            continue
        seen.add(key)
        uniq.append((pg, line))

    print(f"\nTOTAL PDF PAGES: {total}")
    print("-" * 68)
    body_start = body_end = None
    for idx, (pg, line) in enumerate(uniq):
        nxt = uniq[idx + 1][0] if idx + 1 < len(uniq) else total + 1
        print(f"  p.{pg:>4}  ({nxt - pg:>3} pp)  {line}")
        if body_start is None and line.upper().startswith("CAP"):
            body_start = pg
        if line.upper().startswith(("BIBLIOGRAF", "ANEXO", "APÉNDICE", "APENDICE")):
            if body_end is None:
                body_end = pg - 1
    if body_start and body_end:
        body = body_end - body_start + 1
        print("-" * 68)
        verdict = "OK" if 80 <= body <= 100 else ("OVER" if body > 100 else "UNDER")
        print(f"  BODY OF THE TEXT: pp. {body_start}-{body_end} = {body} pages  [{verdict}]")
        print("  guideline: 80-100 pages (body only; appendices excluded)")
        if body > 100:
            print(f"  -> must cut {body - 100} pages (~{(body - 100) * 400} words)")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    docx = Path(sys.argv[1]).resolve()
    if not docx.exists():
        print(f"not found: {docx}", file=sys.stderr)
        return 1
    pdf = docx.with_name(docx.stem + "_preview.pdf")
    stats = word_export(docx, pdf)
    print(f"Word reports: {stats.get('PAGES', '?')} pages, {stats.get('WORDS', '?')} words")
    analyse(pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
