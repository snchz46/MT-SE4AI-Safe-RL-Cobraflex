#!/usr/bin/env bash
# ---------------------------------------------------------------
# download_meshes.sh
# ---------------------------------------------------------------
# Fetch the large STL meshes referenced by the URDF/SDF of the
# CobraFlex 1:14 platform that are NOT tracked in git (because they
# are upstream-distributed and exceed the GitHub size soft-limit).
#
# Run from the repository root:
#
#     ./scripts/download_meshes.sh
#
# The script is idempotent: it skips files that already exist with
# the expected size.
# ---------------------------------------------------------------

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MESHES_DIR="${REPO_ROOT}/src/cobraflex/meshes"

mkdir -p "${MESHES_DIR}"

# ---------------------------------------------------------------
# Files to fetch.
#
# Each entry is: <filename> <expected_size_bytes> <url>
#
# The URL must point at the raw STL. When the canonical upstream URL
# is unstable (as is the case for the Slamtec CAD library), the
# pragmatic substitute is to mirror the file in a release artefact of
# this repository (or in any other persistent location the author
# controls) and to update the URL below to that mirror.
#
# Until a stable URL is decided, the entry for `rplidar-a2m4-r1.stl`
# is left as `MANUAL` so that the script prints a clear instruction
# instead of attempting a broken download.
# ---------------------------------------------------------------

FILES=(
    "rplidar-a2m4-r1.stl MANUAL"
)

MIN_BYTES_SANITY=1000000   # 1 MB: anything smaller is almost certainly truncated

for entry in "${FILES[@]}"; do
    read -r filename url <<<"${entry}"
    target="${MESHES_DIR}/${filename}"

    if [[ -f "${target}" ]]; then
        actual_size=$(wc -c <"${target}" | tr -d ' ')
        if (( actual_size < MIN_BYTES_SANITY )); then
            echo "  ! ${filename} exists but is suspiciously small (${actual_size} bytes)"
            echo "    Remove it and re-run if it should be the full mesh."
        else
            echo "  ✓ ${filename} already present (${actual_size} bytes)"
        fi
        continue
    fi

    if [[ "${url}" == "MANUAL" ]]; then
        echo "  ! ${filename} must be obtained manually."
        echo "    Source: Slamtec RPLidar A2 CAD library"
        echo "    Target: ${target}"
        echo "    Once obtained, place the file at the target path and re-run this script to verify."
        continue
    fi

    echo "  → Downloading ${filename} from ${url}"
    curl -fsSL "${url}" -o "${target}"
done

echo ""
echo "Done."
