# Quarantine — 29.07.2026, concurrent-writer contamination

These 222 run directories were produced on 29.07.2026 while **three**
`tools/run_campaign.py` processes were executing the same `--out` directory
concurrently (PIDs 5533 / 5826 / 6388). They are **not valid campaign evidence**
and are kept only for forensics.

Two independent defects:

1. Two `--resume` passes over the *full* 27-scenario matrix (5533, 6388) reached
   the execution frontier at ~11:42-11:50 while the intended executor (5826) was
   already there. Multiple `eval_policy` processes then wrote the same run
   directory: `_write_run` opens `summary.json` with `open("w")`, so a shorter
   second write left a valid JSON document followed by the tail of the longer
   first one — 35 files fail `json.load` with `Extra data`.
2. `GZ_PARTITION` is keyed on `run_id`, so two processes executing the *same*
   cell shared a partition and their Gazebo servers could cross-talk. Runs in
   this window are therefore suspect even when their JSON parses.

The 1327 runs produced on 27-28.07.2026 are unaffected (verified: 0 JSON
parse failures) and remain in `runs/`. The 222 cells here were re-executed from
scratch by a single serial process.

Root cause was operator error in the resume procedure, not a defect in
`run_campaign.py` or in the policy/cage under test.
