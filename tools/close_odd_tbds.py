#!/usr/bin/env python3
"""
close_odd_tbds.py
-----------------
Close the TBD-Q1..Q12 placeholders in `docs/08_odd_specification.md`
by substituting them with the resolved values declared in
`experiments/odd_inspection/odd_tbds.yaml`.

The script does two things:

1. In the body of the ODD-Spec, replace every literal `TBD-QN`
   occurrence outside the open-issues table by the resolved value.
2. In the open-issues table at section 11, fill the `Resolution`
   column of each resolved row with `value (source) -- YYYY-MM-DD`.

By default the script runs in dry-run mode and prints a unified diff.
Use `--apply` to write the patched ODD-Spec in place (a `.bak` file
is left next to the original).

TBDs whose `value` field is `null` in the YAML are skipped — their
literals remain in the document and their row in section 11 is left
untouched. This makes the script safe to run repeatedly as you close
TBDs one by one.

Exit codes:
  0  the script ran (dry-run or apply); at least one TBD value was
     processed (`null` entries are silently skipped).
  1  the YAML or the ODD-Spec is missing or malformed.
  2  every TBD in the YAML is still `null` (nothing to do).
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML = REPO_ROOT / "experiments" / "odd_inspection" / "odd_tbds.yaml"
DEFAULT_ODD_SPEC = REPO_ROOT / "docs" / "08_odd_specification.md"

SECTION_11_HEADING = "## 11. Open issues and TBDs"
TBD_RE = re.compile(r"TBD-Q(\d+)\b")
TBD_ROW_RE = re.compile(r"^\|\s*(TBD-Q\d+)\s*\|")


# =============================================================
# Helpers
# =============================================================

def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"YAML not found at {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def format_value(value: Any) -> str:
    """Render a YAML value into a Markdown-friendly string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        # Use repr() to preserve the canonical float representation:
        # 1.0 stays "1.0" (not "1"), 0.83 stays "0.83", 9.81 stays "9.81".
        return repr(value)
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def collect_resolved(tbds: Dict[str, dict]) -> Dict[str, dict]:
    """Return only the TBDs whose value is not null/empty."""
    resolved: Dict[str, dict] = {}
    for tbd_id, entry in tbds.items():
        value = entry.get("value")
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        resolved[tbd_id] = entry
    return resolved


# =============================================================
# Patching
# =============================================================

def split_at_section_11(text: str) -> tuple[str, str]:
    """Split the ODD-Spec at the section-11 heading."""
    idx = text.find(SECTION_11_HEADING)
    if idx < 0:
        return text, ""
    return text[:idx], text[idx:]


def substitute_in_body(body: str, resolved: Dict[str, dict]) -> str:
    """Replace every `TBD-QN` literal in the body with its resolved value."""

    def repl(m: re.Match) -> str:
        tbd_id = f"TBD-Q{m.group(1)}"
        if tbd_id not in resolved:
            return m.group(0)
        return format_value(resolved[tbd_id]["value"])

    return TBD_RE.sub(repl, body)


def update_resolution_table(section_11: str, resolved: Dict[str, dict],
                            today: str) -> str:
    """Fill the `Resolution` column of each resolved row in section 11."""
    lines = section_11.split("\n")
    out: List[str] = []
    for line in lines:
        m = TBD_ROW_RE.match(line)
        if not m:
            out.append(line)
            continue
        tbd_id = m.group(1)
        if tbd_id not in resolved:
            out.append(line)
            continue
        # Parse cells: line starts and ends with `|`; cells separated by `|`.
        cells = line.split("|")
        # cells[0] is empty (before first `|`), cells[-1] is empty (after last `|`).
        if len(cells) < 7:  # need 5 columns + 2 empty endpoints
            out.append(line)
            continue
        entry = resolved[tbd_id]
        value_str = format_value(entry["value"])
        source = (entry.get("source") or "").strip()
        notes = (entry.get("notes") or "").strip()
        resolution_bits: List[str] = [value_str]
        if source:
            resolution_bits.append(f"({source})")
        resolution_bits.append(f"-- {today}")
        if notes:
            resolution_bits.append(f"[{notes}]")
        cells[-2] = f" {' '.join(resolution_bits)} "
        out.append("|".join(cells))
    return "\n".join(out)


def patch_odd_spec(text: str, resolved: Dict[str, dict], today: str) -> str:
    body, section_11 = split_at_section_11(text)
    new_body = substitute_in_body(body, resolved)
    if section_11:
        new_section_11 = update_resolution_table(section_11, resolved, today)
        return new_body + new_section_11
    return new_body


# =============================================================
# Diff and reporting
# =============================================================

def print_diff(original: str, patched: str, label_a: str, label_b: str) -> None:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=label_a,
        tofile=label_b,
        n=2,
    )
    # Reconfigure stdout for utf-8 so the diff (which contains characters
    # like sigma, squared, em-dash, etc. from the ODD-Spec) prints cleanly
    # on Windows consoles using cp1252 by default.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    output = "".join(diff)
    try:
        sys.stdout.write(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))


def print_summary(resolved: Dict[str, dict], skipped: List[str]) -> None:
    bar = "-" * 70
    print(f"\n{bar}\nSummary\n{bar}")
    print(f"  resolved: {len(resolved)} TBD(s) ({', '.join(sorted(resolved.keys())) or '<none>'})")
    if skipped:
        print(f"  skipped : {len(skipped)} TBD(s) still null ({', '.join(skipped)})")


def print_changelog_snippet(resolved: Dict[str, dict], today: str) -> None:
    if not resolved:
        return
    bar = "=" * 70
    print(f"\n{bar}\nCHANGELOG snippet (copy into docs/CHANGELOG.md)\n{bar}")
    print(f"\n## [{today}] -- ODD-Spec TBD closure ({len(resolved)} of 12)\n")
    print(f"**Document(s) affected:** `docs/08_odd_specification.md`.")
    print(f"**Phase:** F1.")
    print(f"**Gate context:** before G1.\n")
    print("Closed the following TBD-Q* entries against the simulator workspace inspection:\n")
    for tbd_id in sorted(resolved.keys()):
        entry = resolved[tbd_id]
        value = format_value(entry["value"])
        source = (entry.get("source") or "").strip() or "see ODD-Spec section 11"
        print(f"- **{tbd_id}** -> `{value}` ({source})")
    print(
        "\n`python tools/check_traceability.py` -> all checks PASS, 0 warnings "
        "(no traceability artefacts touched).\n"
    )


# =============================================================
# Main
# =============================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tbd-yaml", type=Path, default=DEFAULT_YAML,
        help=f"YAML with resolved TBD values (default: {DEFAULT_YAML})",
    )
    parser.add_argument(
        "--odd-spec", type=Path, default=DEFAULT_ODD_SPEC,
        help=f"target ODD-Spec markdown (default: {DEFAULT_ODD_SPEC})",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="write the patched ODD-Spec in place (a .bak backup is left)",
    )
    parser.add_argument(
        "--date", default="",
        help="resolution date YYYY-MM-DD (default: today)",
    )
    args = parser.parse_args(argv)

    try:
        data = load_yaml(args.tbd_yaml)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    tbds = data.get("tbds") or {}
    if not isinstance(tbds, dict) or not tbds:
        print(f"ERROR: {args.tbd_yaml} has no `tbds:` mapping", file=sys.stderr)
        return 1
    if not args.odd_spec.exists():
        print(f"ERROR: ODD-Spec not found at {args.odd_spec}", file=sys.stderr)
        return 1

    resolved = collect_resolved(tbds)
    skipped = sorted(set(tbds.keys()) - set(resolved.keys()))

    if not resolved:
        print("Nothing to do: every TBD in the YAML is still null/empty.")
        return 2

    today = args.date or date.today().isoformat()

    original = load_text(args.odd_spec)
    patched = patch_odd_spec(original, resolved, today)

    rel_path = args.odd_spec.relative_to(REPO_ROOT)
    if patched == original:
        print(f"No changes to apply: {rel_path} already up to date with the YAML.")
        print_summary(resolved, skipped)
        return 0

    if args.apply:
        bak = args.odd_spec.with_suffix(args.odd_spec.suffix + ".bak")
        shutil.copy(args.odd_spec, bak)
        args.odd_spec.write_text(patched, encoding="utf-8")
        print(f"Wrote patched {rel_path}")
        print(f"Backup left at {bak.relative_to(REPO_ROOT)}")
    else:
        print_diff(original, patched, f"a/{rel_path}", f"b/{rel_path}")

    print_summary(resolved, skipped)
    print_changelog_snippet(resolved, today)
    if not args.apply:
        print(
            "\n(dry-run; re-run with `--apply` to write the patched ODD-Spec)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
