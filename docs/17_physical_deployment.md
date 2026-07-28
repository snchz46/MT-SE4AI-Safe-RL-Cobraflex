# 17 · Physical deployment (Phase 5) — bring-up plan for the real CobraFlex

**Status: scaffolding prepared, NOT yet run on hardware.** This document is the
bring-up checklist for taking the verdict-bearing RL camera policy + safety cage
from Gazebo to the physical 1:14 CobraFlex. Every sim-side component it reuses is
validated; the hardware I/O and the items flagged **[VERIFY]** are not, by
construction — they need the car.

## 1. What changes from simulation, and what does not

The distributed node chain is the same as the F2 physical demo pattern, now
camera-driven and 2-D. Only the **image source**, the **actuation sink**, and the
**RL inference node** differ from sim; the safety-relevant logic is bit-identical.

| Stage | Sim (Gazebo) | Physical | Reused? |
| --- | --- | --- | --- |
| Image | `camera_bridge` (rendered) | camera driver (ZED/other, D-32) | topic only |
| **Policy inference** | in-process `GazeboLaneEnv.step` | **`rl_policy_node`** (NEW) | preprocessing + model |
| Cage perception (D-43) | `CagePerceptionSupervisor` in-process | `cv_lane_estimator_node` | **identical** |
| Cage rules (C-01..C-06) | `SafetyCageNode` in-process | `cage_ros_node` | **identical** |
| Actuation | `RosGazeboInterface` → sim `/cmd_vel` | `vehicle_control_node` → motor driver | node reused |
| Evidence | `cage_status.csv` | `cage_logger_node` → CSV | **identical** |

The only new code is `rl_policy_node` (`src/cobraflex_rl/.../rl_policy_node.py`);
it reuses `camera_pipeline.decode_image` + `to_observation` + a k=4 frame stack —
the exact preprocessing the CNN trained on — so the policy sees the same
observation on hardware. Its pure logic is unit-tested
(`policy/tests/test_rl_policy_node.py`).

## 2. Hardware prerequisites (do these first)

1. **Camera driver** publishing frames on `camera/image_raw_lane` with the SAME
   field of view / mounting geometry the policy trained on. Installed externally
   (not tracked, D-32).
2. **[VERIFY] Camera extrinsics.** The IPM in `camera_geometry.py` is calibrated
   for pitch 0.30 rad, height 0.077 m (the URDF mount). Match the real mount to
   these, OR re-run the D-57 workflow to set `cage.perception_heading_bias_rad`
   for the real camera's near-field-slope offset. A wrong pitch corrupts the CV
   `ey`/`epsi` the cage acts on.
3. **Motor driver** consuming `/cmd_vel` (`geometry_msgs/Twist`: `linear.x` m/s,
   `angular.z` yaw rate). Map the CobraFlex ESC + steering servo to it.
4. **Hardware e-stop** wired to `/external_stop` (`std_msgs/Bool`). **Mandatory
   before any powered run** — it drives C-05 Trigger 6 (external stop).

## 3. Bring-up command

```bash
source /opt/ros/jazzy/setup.bash && source install/setup.bash
# start the camera + motor drivers first (external), then:
ros2 launch cobraflex_rl deploy_cobraflex.launch.py \
    checkpoint:=/abs/path/to/<deployed>.zip \
    algorithm:=sac \
    max_speed_mps:=0.22 \
    mode:=monitoring          # FIRST runs in monitoring (cage shadows, does not act)
```

## 4. Staged, safe bring-up sequence

1. **Bench, wheels up.** `mode:=monitoring`. Confirm topics flow
   (`/raw_action`, `/state_obs`, `/perception_invalid`, `/cage_status`) and the
   CV estimator tracks a hand-moved lane. No actuation trusted yet.
2. **[VERIFY] 2-D throttle→speed mapping.** The sim maps the cage's safe throttle
   via `cage_bridge.target_speed_from_throttle_2d` (max_speed·u, full stop below
   the deadband); `vehicle_control_node` scales `fixed_speed_mps` by the safe
   throttle. Confirm they agree (set `fixed_speed_mps` = `action.max_speed_mps`,
   check the deadband/stop) so commanded speeds match the campaign.
3. **Low-speed enforcement, tethered.** `mode:=enforcement`, e-stop in hand,
   `max_speed_mps` reduced. Verify C-05 stops the car and the e-stop overrides.
4. **Full deploy** only after 1–3 pass.

## 5. Known gaps / sim-to-real (Ch.9, honest list)

- **Appearance gap** (CNN + CV estimator): the real camera image differs from the
  Gazebo render → both the policy and the D-43 estimator may degrade. Mitigations:
  H-10 domain randomisation (training-side), the D-57 calibration precedent.
- **`[provisional]` thresholds** (M-1..M-5) were calibrated on sim noise; the
  calibration campaign exists to re-derive them on hardware.
- **Compute cadence**: the loop is 10 Hz in sim; confirm the real camera→inference
  →actuation path sustains it (CPU inference is ample; the camera driver is the
  likely bottleneck).
- **Which checkpoint**: deploy the rescued *peak* checkpoint of the final training
  (monitor the 25k-cadence learning curve), not necessarily the last step.

## 6. What is and isn't claimed

Prepared and host-verified: the inference node's preprocessing + action mapping,
the launch wiring, the reuse of the identical cage logic. **Not** verified: any
behaviour on the physical car. First bring-up is the Phase-5 experiment this plan
scaffolds; the `[VERIFY]` items are its explicit agenda.
