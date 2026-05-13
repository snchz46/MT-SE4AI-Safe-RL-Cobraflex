#!/usr/bin/env python3
"""
Sync hazard register from Markdown to CSV.

Extracts hazard information from structured Markdown files in the manuscript
and generates a CSV file compatible with the Traceability Matrix.

Usage:
    python tools/sync_hazard_register.py [--input INPUT_MD] [--output OUTPUT_CSV]

Default paths:
    INPUT:  manuscript/chapters/chapter_*.md (searches for hazard tables)
    OUTPUT: docs/data/hazard_register.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional


def find_hazard_tables(md_content: str) -> List[Dict[str, str]]:
    """
    Extract hazard table rows from Markdown content.

    Expects markdown table format with hazard-like IDs (H-01, H-02, etc.):
    | Hazard ID | Description | Severity | Mitigation | Related A1-A5 | Notes |
    | --- | --- | --- | --- | --- | --- |
    | H-01 | ... | High | ... | A1, A3 | ... |

    Args:
        md_content: Full markdown content

    Returns:
        List of dicts with extracted hazard data
    """
    hazards = []
    lines = md_content.split('\n')

    in_table = False
    header_row = None
    header_col_names = []

    for i, line in enumerate(lines):
        line = line.strip()

        # Skip empty lines
        if not line:
            in_table = False
            continue

        # Check if line is a markdown table row
        if not line.startswith('|') or not line.endswith('|'):
            in_table = False
            continue

        # Parse row
        cells = [cell.strip() for cell in line.split('|')[1:-1]]

        # Skip rows with wrong column count
        if not cells:
            continue

        # Separator row (---)
        if all(re.match(r'^-+$|^:-*-*:$', cell) for cell in cells):
            if header_col_names:  # Only mark as in_table if we had a header
                in_table = True
            continue

        # Header row (first row with content, before separator)
        if not in_table:
            # Check if this looks like a header (contains ID-like keywords)
            if any('id' in cell.lower() or 'hazard' in cell.lower() for cell in cells):
                header_col_names = [cell.lower() for cell in cells]
                header_row = {i: cell.lower() for i, cell in enumerate(cells)}
            continue

        # Data row
        if in_table and header_col_names:
            hazard_dict = {}
            for col_idx, cell in enumerate(cells):
                if col_idx < len(header_col_names):
                    header = header_col_names[col_idx]
                    hazard_dict[header] = cell

            # Only add rows with hazard-like IDs (H-XX, H_XX, HXX format)
            id_field = hazard_dict.get('id', '') or hazard_dict.get('hazard id', '')
            if id_field and re.match(r'^H[\-_]?\d+', id_field, re.IGNORECASE):
                hazards.append(hazard_dict)

    return hazards


def normalize_hazard(hazard: Dict[str, str]) -> Dict[str, str]:
    """
    Normalize hazard dict to standard column names.

    Handles variations in header names and formats.

    Args:
        hazard: Raw hazard dict from markdown table

    Returns:
        Normalized hazard dict with standard columns
    """
    normalized = {}

    # Map possible column name variations to standard names
    column_mapping = {
        'id': ['id', 'hazard id', 'hazard_id', 'h_id'],
        'description': ['description', 'hazard', 'hazard_description', 'desc'],
        'severity': ['severity', 'risk level', 'risk_level', 'level'],
        'mitigation': ['mitigation', 'mitigation_measure', 'control', 'treatment'],
        'related_adaptations': ['related_adaptations', 'related a1-a5', 'related a', 'adaptations', 'a1-a5'],
        'notes': ['notes', 'remarks', 'comments', 'additional_info'],
        'status': ['status', 'state'],
        'owner': ['owner', 'responsible', 'assignee'],
    }

    # Flatten input keys to lowercase for matching
    flat_hazard = {k.lower().replace(' ', '_'): v for k, v in hazard.items()}

    # Map to standard columns
    for std_col, possible_names in column_mapping.items():
        for possible_name in possible_names:
            if possible_name in flat_hazard and flat_hazard[possible_name]:
                normalized[std_col] = flat_hazard[possible_name]
                break

    return normalized


def extract_hazards_from_files(input_pattern: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Find and extract hazards from markdown files.

    Args:
        input_pattern: Glob pattern for input files. Default: manuscript/chapters/chapter_*.md

    Returns:
        List of normalized hazard dicts
    """
    if input_pattern is None:
        input_pattern = 'docs/02_hazard_register.md'

    all_hazards = []

    for file_path in Path('.').glob(input_pattern):
        if not file_path.is_file():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            continue

        # Extract tables from this file
        raw_hazards = find_hazard_tables(content)

        for hazard in raw_hazards:
            normalized = normalize_hazard(hazard)
            if normalized:  # Only add if something was extracted
                all_hazards.append(normalized)

    return all_hazards


def write_hazard_register_csv(hazards: List[Dict[str, str]], output_path: str) -> None:
    """
    Write hazards to CSV file.

    Args:
        hazards: List of normalized hazard dicts
        output_path: Path to output CSV file
    """
    # Standard columns in order
    fieldnames = [
        'id',
        'description',
        'severity',
        'mitigation',
        'related_adaptations',
        'status',
        'owner',
        'notes',
    ]

    # Create parent directories if needed
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for hazard in hazards:
            # Ensure all columns present (use empty string as default)
            row = {field: hazard.get(field, '') for field in fieldnames}
            writer.writerow(row)

    print(f"[OK] Wrote {len(hazards)} hazards to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Sync hazard register from Markdown to CSV'
    )
    parser.add_argument(
        '--input',
        default='docs/02_hazard_register.md',
        help='Input markdown file pattern (default: docs/02_hazard_register.md)'
    )
    parser.add_argument(
        '--output',
        default='docs/data/hazard_register.csv',
        help='Output CSV file path (default: docs/data/hazard_register.csv)'
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

    # Extract hazards from markdown files
    hazards = extract_hazards_from_files(args.input)

    if not hazards:
        print("Warning: No hazard tables found in markdown files", file=sys.stderr)
        if args.verbose:
            print(f"Searched for pattern: {args.input}", file=sys.stderr)

    if args.verbose and hazards:
        print(f"Found {len(hazards)} hazards:")
        for hazard in hazards:
            print(f"  - {hazard.get('id', '?')}: {hazard.get('description', '?')[:50]}")

    # Write CSV
    write_hazard_register_csv(hazards, args.output)

    return 0


if __name__ == '__main__':
    sys.exit(main())
