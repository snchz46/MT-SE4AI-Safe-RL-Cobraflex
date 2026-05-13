# Traceability Matrix and Artifact Generation

This document explains how to maintain and regenerate the traceability artifacts (hazard register, requirements matrix, etc.) from Markdown sources in the manuscript.

## Overview

The thesis uses a **manuscript-first approach** where:

1. All key information (hazards, requirements, adaptations, etc.) lives in Markdown files in `manuscript/chapters/`
2. Structured data (CSV, JSON) is **generated automatically** from these Markdown sources
3. Tools and CI/CD pipelines consume the generated CSVs

This approach ensures:

- **Single source of truth**: Update Markdown, regenerate CSVs
- **Version control friendly**: Markdown diffs are readable
- **Testable**: Scripts validate structure and consistency
- **Sustainable**: No manual sync required

## Current Artifacts

### 1. Hazard Register (`docs/data/hazard_register.csv`)

**Source**: Markdown tables in `manuscript/chapters/chapter_*.md` with hazard-like IDs (H-01, H-02, etc.)

**Generator**: `tools/sync_hazard_register.py`

**Expected Format in Markdown**:

```markdown
## HARA Results — Hazards

| Hazard ID | Description | Severity | Mitigation | implementation_type | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| H-01 | Unintended lane exit | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 | Open | TTLC predictive constraint |
| H-02 | Divergent heading error | S2/E3/C2 - Medium-High | SR-002, SR-003 | C-02, C-03 | Open | Heading stability |
```

**Generated CSV Structure**:

```csv
id, description, severity, mitigation, implementation_type, status, notes
H-01, Unintended lane exit, S3/E3/C2 - High, "SR-001, SR-003", "C-01, C-03", Open, TTLC predictive constraint
```

**Update Command**:

```bash
python tools/sync_hazard_register.py --verbose
```

## Planned Artifacts (Future Phases)

The following artifacts are currently placeholders but follow the same pattern:

| Artifact | Source | Status |
| --- | --- | --- |
| `docs/data/requirements_matrix.csv` | Requirements tables (SR-001, SR-002, ...) | Planned for Phase 2 |
| `docs/data/adaptation_matrix.csv` | Adaptation details (A1–A5 tables) | Planned for Phase 2 |
| `docs/data/test_traceability.csv` | Test case mapping | Planned for Phase 3 |
| `docs/data/verification_log.csv` | Verification results | Planned for Phase 3 |

## Workflow

### For Authors

When writing a chapter with hazards or requirements:

1. **Create a structured table in Markdown**:

   ```markdown
   ## 5.2 Hazard Analysis
   
   | Hazard ID | Description | Severity | Mitigation | implementation_type |
   | --- | --- | --- | --- | --- |
   | H-01 | ... | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 |
   ```

2. **Use consistent ID patterns**:
   - Hazards: `H-01`, `H-02`, ... (or `H-1`, `H_1`)
   - Requirements: `SR-001`, `SR-002`, ... (Safety Requirement)
   - Cage rules: `C-01`, `C-02`, ..., `C-06`
   - Adaptations: `A1`, `A2`, ..., `A5` (methodology-level, not used in the hazard table)

3. **Link to thesis sections**: Use references like "See §5.2" for cross-referencing

4. **Commit Markdown** to version control

### For Build/CI

1. **Regenerate artifacts**:

   ```bash
   python tools/sync_hazard_register.py
   ```

2. **Validate consistency**:

   ```bash
   python tools/validate_traceability.py  # (to be implemented)
   ```

3. **Commit generated CSVs** or skip if using CI-generated artifacts

4. **Import to external tools** (Jira, Doors, Excel, etc.) as needed

### Example: Complete Workflow

```bash
# 1. Author writes Markdown chapter
# (Edit manuscript/chapters/chapter_05.md)

# 2. Generate artifacts
python tools/sync_hazard_register.py --verbose

# 3. Review generated CSV
cat docs/data/hazard_register.csv

# 4. Commit everything
git add manuscript/chapters/chapter_05.md docs/data/hazard_register.csv
git commit -m "F3: Add HARA results and hazard register"

# 5. External tools import the CSV
# (Jira, requirements tool, etc.)
```

## Script Reference

### `sync_hazard_register.py`

```text
Usage:
    python tools/sync_hazard_register.py [--input INPUT] [--output OUTPUT] [--verbose]

Options:
    --input INPUT       Glob pattern for Markdown files (default: manuscript/chapters/chapter_*.md)
    --output OUTPUT     Output CSV path (default: docs/data/hazard_register.csv)
    --verbose           Print extraction details
```

## Header Name Recognition

The scripts use flexible header name matching. These are recognized:

| Standard | Variations |
| --- | --- |
| `id` | ID, Hazard ID, Hazard_ID |
| `description` | Description, Hazard, Desc |
| `severity` | Severity, Risk Level, Risk_Level |
| `mitigation` | Mitigation, Mitigation_Measure, Control |
| `implementation_type` | Implementation Type, Implementation, Implemented_By, Related Cage Rules, Cage_Rules |
| `status` | Status, State |

**Example Markdown headers that will be recognized**:

✓ `| Hazard ID | Description | Severity | ...`
✓ `| ID | Hazard | Risk Level | ...`
✓ `| H-ID | Desc | Severity | ...`

## Integration with External Tools

### Jira

1. Export CSV from `docs/data/hazard_register.csv`
2. Use Jira's CSV import to create issues/stories
3. Link back to Markdown sections

### Excel / Google Sheets

1. Import CSV: `File → Open → docs/data/hazard_register.csv`
2. Create pivot tables for dashboards
3. Add manual columns (owner, assignee, due date) as needed

### Requirements Management Tools (Doors, Polarion, etc.)

1. Use CSV as data source
2. Map columns to tool-specific fields
3. Set up automated sync (if tool supports webhooks)

## Validation and Quality Checks

Currently basic validation is built into the scripts:

- Hazard IDs must match pattern `H-\d+` or similar
- Table structure is validated (correct number of columns)
- Headers are matched flexibly

Future planned checks:

- Uniqueness of IDs within a document
- Cross-references to adaptations (A1–A5) are valid
- Severity levels match defined taxonomy
- All hazards have mitigations

To add validation, implement `tools/validate_traceability.py`.

## Troubleshooting

### No artifacts generated?

1. Check Markdown file locations:

   ```bash
   ls manuscript/chapters/chapter_*.md
   ```

2. Verify tables have correct structure:
   - Rows start and end with `|`
   - Separator row with `---`
   - Header row with ID/Description columns

3. Run with verbose mode:

   ```bash
   python tools/sync_hazard_register.py --verbose
   ```

### IDs not recognized?

- Ensure ID format matches: `H-01`, `H-1`, `H_1`, etc.
- Check that first column is named `ID` or `Hazard ID`
- Try running with a sample file to test

### Wrong data extracted?

- Verify column headers match recognized names (case-insensitive)
- Check for extra spaces in headers
- Review the verbose output to see parsed headers

## Contributing

To add a new artifact generator:

1. Create a new script: `tools/sync_*.py`
2. Follow the pattern of `sync_hazard_register.py`:
   - Flexible header matching
   - Robust error handling
   - CSV output to `docs/data/`
3. Add documentation to this file
4. Update `update_traceability.sh` to include the new script
5. Submit as part of thesis development

## References

- **Markdown format**: CommonMark (standard Markdown tables)
- **CSV format**: RFC 4180 (standard CSV, UTF-8 encoding)
- **Filename convention**: `<domain>_register.csv` or `<domain>_matrix.csv`
- **ID patterns**: Based on ISO 26262 HARA, functional safety conventions

## Future Enhancements

Phase 2–3 roadmap:

- [ ] Interactive web dashboard showing traceability across all artifacts
- [ ] Automated validation rules (severity, ID uniqueness, etc.)
- [ ] Bidirectional sync (CSV → Markdown)
- [ ] Integration with Jira/GitHub Issues via API
- [ ] Test coverage analysis (link hazards to test cases)
- [ ] Safety case generation from CSV data
- [ ] PDF/HTML report generation from traceability matrix
