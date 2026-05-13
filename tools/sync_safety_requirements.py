#!/usr/bin/env python3
"""
Sync safety requirements register from Markdown to CSV.

Extracts safety requirement information from the machine-readable table at the
bottom of `docs/03_safety_requirements.md` and generates a CSV file compatible
with the Traceability Matrix.

Usage:
    python tools/sync_safety_requirements.py [--input INPUT_MD] [--output OUTPUT_CSV]

Default paths:
    INPUT:  docs/03_safety_requirements.md
    OUTPUT: docs/data/safety_requirements.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional


def find_sr_tables(md_content: str) -> List[Dict[str, str]]:
    """
    Extract safety requirement table rows from Markdown content.

    Expects markdown table format with SR-like IDs (SR-001, SR-002, etc.):
    | SR ID | Statement | Pattern | Hazards | Cage Rule | Scenarios | Metric | ... |
    | --- | --- | --- | --- | --- | --- | --- | --- |
    | SR-001 | ... | ... | H-01 | C-01 | ... | ... | ... |

    Args:
        md_content: Full markdown content

    Returns:
        List of dicts with extracted SR data
    """
    srs = []
    lines = md_content.split('\n')

    in_table = False
    header_col_names: List[str] = []

    for line in lines:
        line = line.strip()

        # Empty line breaks any table context
        if not line:
            in_table = False
            continue

        # Not a markdown table row
        if not line.startswith('|') or not line.endswith('|'):
            in_table = False
            continue

        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if not cells:
            continue

        # Separator row (---) — marks transition from header to body
        if all(re.match(r'^-+$|^:-*-*:$', cell) for cell in cells):
            if header_col_names:
                in_table = True
            continue

        # Header row (first row with content, before separator)
        if not in_table:
            if any('id' in cell.lower() or 'sr' in cell.lower() for cell in cells):
                header_col_names = [cell.lower() for cell in cells]
            continue

        # Data row
        if in_table and header_col_names:
            sr_dict: Dict[str, str] = {}
            for col_idx, cell in enumerate(cells):
                if col_idx < len(header_col_names):
                    header = header_col_names[col_idx]
                    sr_dict[header] = cell

            id_field = (
                sr_dict.get('id', '')
                or sr_dict.get('sr id', '')
                or sr_dict.get('sr_id', '')
            )
            if id_field and re.match(r'^SR[\-_]?\d+', id_field, re.IGNORECASE):
                srs.append(sr_dict)

    return srs


def normalize_sr(sr: Dict[str, str]) -> Dict[str, str]:
    """
    Normalize SR dict to standard column names.

    Args:
        sr: Raw SR dict from markdown table

    Returns:
        Normalized SR dict with standard columns
    """
    normalized: Dict[str, str] = {}

    column_mapping = {
        'id': ['id', 'sr id', 'sr_id', 'requirement id', 'requirement_id'],
        'statement': ['statement', 'description', 'requirement', 'desc'],
        'pattern': ['pattern', 'type', 'category'],
        'hazards': ['hazards', 'hazard', 'related_hazards', 'related hazards', 'h_refs'],
        'cage_rule': ['cage rule', 'cage_rule', 'cage rules', 'cage_rules', 'related_cage_rules'],
        'scenarios': ['scenarios', 'scenario', 'verifying_scenarios', 'verified by scenarios'],
        'metric': ['metric', 'metrics', 'verifying_metric', 'verifying metric'],
        'status': ['status', 'state'],
        'notes': ['notes', 'remarks', 'comments', 'additional_info'],
    }

    flat_sr = {k.lower().replace(' ', '_'): v for k, v in sr.items()}

    for std_col, possible_names in column_mapping.items():
        for possible_name in possible_names:
            key = possible_name.replace(' ', '_')
            if key in flat_sr and flat_sr[key]:
                normalized[std_col] = flat_sr[key]
                break

    return normalized


def extract_srs_from_files(input_pattern: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Find and extract SRs from markdown files.

    Args:
        input_pattern: Glob pattern for input files. Default: docs/03_safety_requirements.md

    Returns:
        List of normalized SR dicts
    """
    if input_pattern is None:
        input_pattern = 'docs/03_safety_requirements.md'

    all_srs: List[Dict[str, str]] = []

    for file_path in Path('.').glob(input_pattern):
        if not file_path.is_file():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            continue

        raw_srs = find_sr_tables(content)
        for sr in raw_srs:
            normalized = normalize_sr(sr)
            if normalized:
                all_srs.append(normalized)

    return all_srs


def write_sr_register_csv(srs: List[Dict[str, str]], output_path: str) -> None:
    """
    Write SRs to CSV file.

    Args:
        srs: List of normalized SR dicts
        output_path: Path to output CSV file
    """
    fieldnames = [
        'id',
        'statement',
        'pattern',
        'hazards',
        'cage_rule',
        'scenarios',
        'metric',
        'status',
        'notes',
    ]

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for sr in srs:
            row = {field: sr.get(field, '') for field in fieldnames}
            writer.writerow(row)

    print(f"[OK] Wrote {len(srs)} safety requirements to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Sync safety requirements register from Markdown to CSV'
    )
    parser.add_argument(
        '--input',
        default='docs/03_safety_requirements.md',
        help='Input markdown file pattern (default: docs/03_safety_requirements.md)'
    )
    parser.add_argument(
        '--output',
        default='docs/data/safety_requirements.csv',
        help='Output CSV file path (default: docs/data/safety_requirements.csv)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        print(f"Input pattern: {args.input}")
        print(f"Output path: {args.output}")

    srs = extract_srs_from_files(args.input)

    if not srs:
        print("Warning: No SR tables found in markdown files", file=sys.stderr)
        if args.verbose:
            print(f"Searched for pattern: {args.input}", file=sys.stderr)

    if args.verbose and srs:
        print(f"Found {len(srs)} safety requirements:")
        for sr in srs:
            print(f"  - {sr.get('id', '?')}: {sr.get('statement', '?')[:60]}")

    write_sr_register_csv(srs, args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main())
