# scenarios_complex_b — complex_b variant of the scenario library (DRAFT)

Parallel scenario set for the **track-'E' camera campaign** on the **complex_b**
circuit. The E-main policy `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` was
trained on complex_b and must be evaluated there. The oval set in `../scenarios/`
is **frozen F4 / 139k-campaign evidence and is left untouched**.

## What is done (mechanical, correct)
Every scenario's `track:` block is re-pointed to complex_b:
- `world: lane_following_oval_complex.world`
- `world_name: lane_following_complex_b`  (SDF name for the gz teleport services)
- `centerline: complex_b_right_lane_centerline.yaml`  (reward target / Frenet frame)
- `road_centerline: complex_b_centerline.yaml`  (off-road geometry, docs/11 §3.5)

The campaign plumbing is wired end-to-end (and dry-run-validated):
`tools/run_campaign.py` (`--scenario-dir`, `--model-path`, resolves + passes
centerline/road_centerline/world_name) → `eval_scenario_batch.launch.py`
(new `centerline`/`road_centerline`/`world_name` args) → `eval_policy`.

## What MUST be validated before a verdict run (ICs copied from the oval)
`initial_conditions` and `perturbations` were copied verbatim from the oval and
are **NOT** valid for complex_b geometry. Per scenario, check:
- **`start_s_m`** — oval semantics ("1.5 = curve entry") don't map to complex_b
  arc-length; re-pick start points against complex_b features.
- **`straight_completed` event + `timeout_s`** — oval assumed a 1.5 m straight;
  complex_b (perimeter 19.22 m) has different straight/curve layout.
- **`perturbations.at_time_s`** — timed to oval features; re-time to where the
  complex_b vehicle reaches the intended feature (curve apex, occlusion zone).
- **`pose` lateral offset / heading** — relative, mostly transfer (same lane
  width), but re-confirm the recovery margins fit complex_b.
- **SC-PERT-09 / SC-PERT-10** — there is **no complex_b wet/worn world**; those
  two are flagged inline. Recreate the textured worlds or apply the degradation
  in-pipeline before running them.

## How to run (Ubuntu + ROS2 Jazzy + Gazebo)
```bash
PEAK=experiments/sim/training/ppo_newcam_complex_b_2024_1M/checkpoints_peak/cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip
python tools/run_campaign.py   --scenario-dir scenarios_complex_b   --model-path $PEAK   --train-config $(ros2 pkg prefix cobraflex_rl)/share/cobraflex_rl/config/train_ppo_camera.yaml   --seeds 2024 --modes enforcement,monitoring   --out experiments/sim/campaign_e_297k
# add --dry-run first to print the matrix + D-29 feasibility with no Gazebo.
```
