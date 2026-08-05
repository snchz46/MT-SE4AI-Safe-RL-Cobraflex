#!/usr/bin/env python3
"""
Sync policy/checkpoints/checkpoint_registry.csv from run metadata.

The registry is written incrementally by
``cobraflex_rl.train_ppo._append_checkpoint_registry`` at the end of each
training run. That appender writes a placeholder ``checkpoint_id``
(``cobraflex_<algo>_lane``) and leaves ``scenario_evaluated`` empty with a
"filled in by eval_policy later" comment that was never implemented. This
script performs that fill retroactively, from evidence that exists now:

  * ``experiments/sim/training/*/metadata.json``  -> one row per training run
  * ``experiments/sim/runs/*/metadata.json``      -> scenarios evaluated
  * ``experiments/sim/campaign*/runs/*/metadata.json``  (same)

Rows are matched by ``run_id`` (carried in the ``notes`` column). Existing
rows are **never dropped**: several early runs survive only in this CSV
because their training directories were renamed or removed, and the CSV is
the last record of them.

Schema is fixed at the 8 columns the appender writes positionally --
do not add columns here without updating
``train_ppo.py:_append_checkpoint_registry``.

Usage:
    python tools/sync_checkpoint_registry.py [--check] [--repo REPO]

    --check  exit 1 if the file on disk differs from what would be written
             (for use as a pre-Gate guard); writes nothing.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

COLUMNS = [
    "checkpoint_id", "seed", "training_steps", "scenario_evaluated",
    "timestamp", "git_commit", "cage_yaml_hash", "notes",
]

# Long scenario lists are replaced by a count plus a pointer to the campaign
# that produced them, so the cell stays readable.
INLINE_SCENARIO_LIMIT = 4

# stop_reason in metadata.json runs to whole paragraphs; the registry keeps a
# lead-in and defers to the run's metadata.json for the rest.
STOP_REASON_CHARS = 160


def sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def index_on_disk(repo: Path) -> Dict[str, Path]:
    """sha256 -> path, for every checkpoint binary still present."""
    found: Dict[str, Path] = {}
    patterns = ["policy/checkpoints/*.zip", "experiments/**/*.zip"]
    for pattern in patterns:
        for raw in glob.glob(str(repo / pattern), recursive=True):
            path = Path(raw)
            digest = sha256_file(path)
            if digest and digest not in found:
                found[digest] = path.relative_to(repo)
    return found


def index_evaluations(repo: Path) -> Dict[str, Set[str]]:
    """checkpoint sha256 -> set of scenario IDs it was evaluated on."""
    index: Dict[str, Set[str]] = defaultdict(set)
    sources = (
        glob.glob(str(repo / "experiments/sim/runs/*/metadata.json"))
        + glob.glob(str(repo / "experiments/sim/campaign*/runs/*/metadata.json"))
    )
    for meta in sources:
        try:
            with open(meta, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        digest, scenario = data.get("policy_checkpoint_hash"), data.get("scenario_id")
        if digest and scenario:
            index[digest].add(scenario)
    return index


def index_campaigns(repo: Path) -> Dict[str, Set[str]]:
    """checkpoint sha256 -> set of campaign directory names."""
    index: Dict[str, Set[str]] = defaultdict(set)
    for meta in glob.glob(str(repo / "experiments/sim/campaign*/runs/*/metadata.json")):
        try:
            with open(meta, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        digest = data.get("policy_checkpoint_hash")
        if digest:
            index[digest].add(Path(meta).parents[2].name)
    return index


def run_digests(run_dir: Path, nominal: Optional[str]) -> List[str]:
    """Every checkpoint sha256 attributable to a training run.

    The nominal ``policy_checkpoint_hash`` is often a bare end-of-run save that
    was never evaluated; what campaigns actually load is the rescued peak under
    ``checkpoints_peak/``. Both count as "this run's" checkpoints.
    """
    digests = [nominal] if nominal else []
    peak = run_dir / "checkpoints_peak"
    if peak.is_dir():
        for path in sorted(peak.glob("*.zip")):
            digest = sha256_file(path)
            if digest and digest not in digests:
                digests.append(digest)
    return digests


def scenario_cell(scenarios: Set[str], campaigns: Set[str]) -> str:
    if not scenarios:
        return ""
    if len(scenarios) <= INLINE_SCENARIO_LIMIT:
        return ";".join(sorted(scenarios))
    where = ",".join(sorted(campaigns)) if campaigns else "experiments/sim/runs"
    return f"{len(scenarios)} scenarios ({where})"


def build_notes(run_id: str, data: Optional[dict], digest: Optional[str],
                on_disk: Dict[str, Path], extra: str = "") -> str:
    parts = [f"run_id={run_id}"]
    if data:
        algorithm = data.get("algorithm")
        if algorithm:
            parts.append(f"algo={algorithm}")
        status = data.get("status")
        if status and status != "completed":
            parts.append(f"status={status}")
        stop = data.get("stop_reason")
        if stop:
            stop = " ".join(stop.split())
            if len(stop) > STOP_REASON_CHARS:
                stop = stop[:STOP_REASON_CHARS].rsplit(" ", 1)[0] + " [...see metadata.json]"
            parts.append(f"stop={stop}")
    if digest:
        parts.append(f"sha256={digest[:12]}")
        parts.append("binary=present" if digest in on_disk else "binary=MISSING")
    if extra:
        parts.append(extra)
    return "; ".join(parts)


def reconstruct_row(repo: Path, run_dir: Path, evaluations: Dict[str, Set[str]],
                    campaigns: Dict[str, Set[str]],
                    on_disk: Dict[str, Path]) -> Optional[List[str]]:
    """Build a row for a training run that has no metadata.json.

    The 2-D PPO cap-0.22 trunk is in this state: its directory carries only
    learning_curve.csv and action_samples.csv. Everything else is recovered
    from the campaign that consumed its checkpoint, which records seed,
    git commit, cage hash and the checkpoint sha256 on every one of its runs.
    Rows built this way are flagged in notes -- they are derived, not logged.
    """
    prefix = run_dir.name + "_"
    candidates = [(d, p) for d, p in on_disk.items()
                  if p.parent.name == "checkpoints" and p.name.startswith(prefix)
                  and d in evaluations]
    if not candidates:
        return None
    digest, path = max(candidates, key=lambda dp: len(evaluations[dp[0]]))

    source = None
    for meta in glob.glob(str(repo / "experiments/sim/campaign*/runs/*/metadata.json")):
        try:
            with open(meta, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("policy_checkpoint_hash") == digest:
            source = (data, Path(meta).parents[2].name)
            break
    if source is None:
        return None
    data, campaign = source

    # training_steps is the length of the run, not the step of the selected
    # checkpoint -- take the furthest checkpoint the run left on disk.
    steps_seen = [int(m.group(1)) for m in
                  (re.search(r"_(\d+)_steps\.zip$", p.name) for p in on_disk.values()
                   if p.parent.name == "checkpoints" and p.name.startswith(prefix))
                  if m]
    steps = max(steps_seen) if steps_seen else ""
    selected = re.search(r"_(\d+)_steps\.zip$", path.name)

    notes = (f"run_id={run_dir.name}; algo={data.get('algorithm', '')}; "
             f"sha256={digest[:12]}; "
             f"binary={'present' if digest in on_disk else 'MISSING'}; "
             + (f"selected_at={selected.group(1)}; " if selected else "")
             + f"no metadata.json in training dir - row derived from {campaign}")
    return [
        path.name,
        data.get("seed", ""),
        steps,
        scenario_cell(evaluations.get(digest, set()), campaigns.get(digest, set())),
        data.get("timestamp_iso", ""),
        data.get("git_commit", ""),
        data.get("cage_yaml_hash", ""),
        notes,
    ]


def read_existing(path: Path) -> List[List[str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.reader(handle) if r]
    return [r for r in rows if not r[0].startswith("#") and r[0] != COLUMNS[0]]


def run_id_of(row: List[str]) -> str:
    notes = row[7] if len(row) > 7 else ""
    match = re.search(r"run_id=([^;,\s]+)", notes)
    return match.group(1) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if on-disk file differs; write nothing")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    registry = repo / "policy" / "checkpoints" / "checkpoint_registry.csv"

    on_disk = index_on_disk(repo)
    evaluations = index_evaluations(repo)
    campaigns = index_campaigns(repo)

    existing = read_existing(registry)
    by_run_id = {run_id_of(r): r for r in existing if run_id_of(r)}

    out: List[List[str]] = []
    seen: Set[str] = set()

    training_dirs = sorted((repo / "experiments/sim/training").glob("*/"))

    for run_dir in training_dirs:
        meta_path = run_dir / "metadata.json"
        if not meta_path.exists():
            row = reconstruct_row(repo, run_dir, evaluations, campaigns, on_disk)
            if row:
                seen.add(run_dir.name)
                out.append(row)
            continue

        with meta_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        run_id = data.get("run_id") or run_dir.name
        seen.add(run_id)
        nominal = data.get("policy_checkpoint_hash")
        digests = run_digests(run_dir, nominal)
        checkpoint = data.get("policy_checkpoint") or ""
        prior = by_run_id.get(run_id)

        scenarios: Set[str] = set()
        camps: Set[str] = set()
        for digest in digests:
            scenarios |= evaluations.get(digest, set())
            camps |= campaigns.get(digest, set())

        # Name the artifact that was actually evaluated, when the nominal save
        # was not the one campaigns loaded.
        evaluated = next((d for d in digests if d in evaluations), None)
        if evaluated and evaluated != nominal and evaluated in on_disk:
            checkpoint = on_disk[evaluated].name

        out.append([
            os.path.basename(checkpoint) or (prior[0] if prior else ""),
            data.get("seed", prior[1] if prior else ""),
            data.get("total_timesteps", prior[2] if prior else ""),
            scenario_cell(scenarios, camps),
            # keep the original timestamp when the row already existed
            (prior[4] if prior else data.get("timestamp_iso", "")),
            data.get("git_commit", prior[5] if prior else ""),
            data.get("cage_yaml_hash", prior[6] if prior else ""),
            build_notes(run_id, data, evaluated or nominal, on_disk),
        ])

    # Preserve rows with no surviving training directory.
    for run_id, row in by_run_id.items():
        if run_id in seen:
            continue
        row = (row + [""] * len(COLUMNS))[:len(COLUMNS)]
        row[7] = build_notes(run_id, None, None, on_disk, extra="registry-only")
        out.append(row)

    out.sort(key=lambda r: (str(r[4]), str(r[0])))

    sio = io.StringIO()
    writer = csv.writer(sio, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(out)
    rendered = sio.getvalue()

    if args.check:
        current = registry.read_text(encoding="utf-8") if registry.exists() else ""
        if current != rendered:
            print("checkpoint_registry.csv is stale — run tools/sync_checkpoint_registry.py")
            return 1
        print("checkpoint_registry.csv up to date.")
        return 0

    registry.write_text(rendered, encoding="utf-8")
    missing = sum(1 for r in out if "binary=MISSING" in r[7])
    filled = sum(1 for r in out if r[3])
    print(f"wrote {registry.relative_to(repo)}: {len(out)} rows "
          f"({filled} with scenario_evaluated, {missing} with a missing binary)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
