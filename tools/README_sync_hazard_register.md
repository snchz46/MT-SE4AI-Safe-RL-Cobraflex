# Hazard Register Sync Tool

## Overview

The `sync_hazard_register.py` script automatically extracts hazard information from Markdown files in the manuscript and generates a CSV file (`docs/data/hazard_register.csv`) that serves as input to the Traceability Matrix.

## Usage

### Command Line

```bash
# Use defaults (searches manuscript/chapters/chapter_*.md, outputs to docs/data/hazard_register.csv)
python tools/sync_hazard_register.py

# Custom input/output paths
python tools/sync_hazard_register.py --input manuscript/chapters/chapter_HARA.md --output my_hazards.csv

# Verbose output
python tools/sync_hazard_register.py --verbose
```

### Integration

Add to your build/CI pipeline to automatically update the hazard register whenever Markdown files change:

```makefile
# In Makefile or similar
traceability: hazard-register

hazard-register:
python tools/sync_hazard_register.py --verbose
```

## Markdown Format

Hazard tables in Markdown should follow this structure:

```markdown
## HARA Results — Hazards and Risk Assessment

| Hazard ID | Description | Severity | Mitigation | implementation_type | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| H-01 | Unintended lane exit | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 | Open | TTLC predictive constraint |
| H-02 | Divergent heading error | S2/E3/C2 - Medium-High | SR-002, SR-003 | C-02, C-03 | Open | Heading stability |
| H-03 | Excessive speed for conditions | S3/E2/C1 - Medium | SR-004 | C-04 | Open | Curvature-dependent ceiling |
```

### Supported Column Headers

The script is flexible and recognizes variations of these header names:

| Standard Name | Recognized Variations |
| --- | --- |
| `id` | ID, Hazard ID, Hazard_ID, H_ID |
| `description` | Description, Hazard, Hazard_Description, Desc |
| `severity` | Severity, Risk Level, Risk_Level, Level |
| `mitigation` | Mitigation, Mitigation_Measure, Control, Treatment |
| `implementation_type` | Implementation Type, Implementation, Implemented_By, Related_Cage_Rules, Cage_Rules |
| `status` | Status, State |
| `notes` | Notes, Remarks, Comments, Additional_Info |

### Best Practices

1. **Use consistent IDs**: H1, H2, H3... or similar naming scheme
2. **Implementation type**: in the `implementation_type` column, list the cage rules (e.g. `C-01, C-03`) that implement the mitigation, or a categorical marker (`training`, `arbiter`) when the mitigation lives outside the cage rule set
3. **Keep descriptions concise**: Under 100 characters when possible
4. **Update severity based on analysis**: High/Medium/Low or ASIL ratings
5. **Track status**: Mark as Active, Mitigated, Closed, or similar

## Output Format

The generated CSV has columns:

```csv
id, description, severity, mitigation, implementation_type, status, notes
```

Example output:

```csv
id,description,severity,mitigation,implementation_type,status,notes
H-01,Unintended lane exit,S3/E3/C2 - High,"SR-001, SR-003","C-01, C-03",Open,TTLC predictive constraint
H-02,Divergent or oscillatory heading error,S2/E3/C2 - Medium-High,"SR-002, SR-003","C-02, C-03",Open,Heading stability
H-03,Excessive speed for current conditions,S3/E2/C1 - Medium,SR-004,C-04,Open,Curvature-dependent ceiling
```

## Integration with Traceability Matrix

The CSV output (`docs/data/hazard_register.csv`) is designed to be imported into the Traceability Matrix tool. Each hazard ID (H-01, H-02, ...) can be traced to:

- **Safety Requirements** (SR-001..SR-008, mitigation column)
- **Cage Rules** (C-01..C-06, `implementation_type` column)
- **Verification** (test cases, validation scenarios)
- **Validation** (physical deployment results)

## Error Handling

The script will:

- Skip files that cannot be read
- Print warnings for missing table formats
- Use `--verbose` flag to see extraction details
- Exit with code 0 even if no hazards found (safe default)

## Requirements

- Python 3.6+
- No external dependencies (uses standard library only)

## Troubleshooting

### No hazards found?

- Ensure markdown files are in `manuscript/chapters/chapter_*.md`
- Check that hazard tables use `|` delimiters correctly
- Use `--verbose` flag to see what files are being scanned
- Ensure table has a separator row (`| --- | --- | ... |`)

### Some columns missing in output?

- The script only includes columns it recognizes
- Check that your header names match the variations listed above
- Case-insensitive matching, spaces/underscores flexible

### Incorrect mapping?

- Verify header names use recognized variations
- Check for typos (e.g., "Hazard ID" not "HazardID")
- Review output CSV with `--verbose` mode

## Example Workflow

1. **Create chapter with HARA results**:

   ```markdown
   # Chapter 5 — HARA and Risk Assessment
   
   ## 5.1 Hazard Identification
   
   | Hazard ID | Description | Severity | Mitigation | implementation_type |
   | --- | --- | --- | --- | --- |
   | H-01 | ... | S3/E3/C2 - High | SR-001, SR-003 | C-01, C-03 |
   ```

2. **Run sync script**:

   ```bash
   python tools/sync_hazard_register.py --verbose
   ```

3. **Check generated CSV**:

   ```bash
   cat docs/data/hazard_register.csv
   ```

4. **Import into Traceability Matrix**:
   - Use the CSV as a data source for your traceability tool
   - Link hazards to requirements and adaptations

## Author Notes

This script was generated as part of the thesis infrastructure to support bidirectional traceability between Markdown documentation and structured data formats (CSV/database).

The design prioritizes:

- **Minimal dependencies**: No external packages required
- **Flexibility**: Recognizes common column name variations
- **Safety**: Non-destructive (reads Markdown, writes CSV)
- **Debuggability**: Verbose mode for troubleshooting
