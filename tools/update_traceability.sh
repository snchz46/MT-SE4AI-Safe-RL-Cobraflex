#!/bin/bash
# Update all traceability artifacts from manuscript sources
#
# This script regenerates CSV files and traceability matrix inputs
# from the Markdown manuscript files.

set -e  # Exit on error

echo "=== Updating Traceability Artifacts ==="

# Update hazard register
echo "[1/1] Syncing hazard register from Markdown..."
python tools/sync_hazard_register.py --verbose

echo ""
echo "=== Complete ==="
echo "Generated artifacts:"
echo "  - docs/data/hazard_register.csv"
echo ""
echo "Next steps:"
echo "  1. Review the generated CSV files"
echo "  2. Commit to version control"
echo "  3. Import into your traceability matrix tool"
