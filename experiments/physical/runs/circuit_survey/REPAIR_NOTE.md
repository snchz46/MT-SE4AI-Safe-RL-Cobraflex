# Repair note — circuit_survey/cage_status.csv

The Jetson crashed and was power-cycled during this run (18.08.2026). The logger
never flushed its final block, leaving 1114 NUL bytes at 99.8% through the file.

Repaired by truncating at the last complete line. No data before that point is
affected: `PRAGMA quick_check` on the companion bag
(`experiments/physical/bags/circuit_20260818T140357Z`) returned `ok`, and that
bag's metadata.yaml — also lost to the crash — was regenerated with
`ros2 bag reindex`.

The run is therefore usable but **short of its intended length**, and its
publication rates are degraded by the recorder competing for eMMC bandwidth
(camera 13.1 Hz against a nominal 20, `/state_obs` 5.0 Hz against 10). Read any
rate figure from this run as I/O-limited, not as chain capability — the
2026-08-17 bench session measured the chain at 20.0 Hz camera / 9.8 Hz cage with
no recorder running.
