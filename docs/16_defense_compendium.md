# Defense Compendium — How It Works, Why It Is Built This Way, and the Literature Behind It

| Field | Value |
| --- | --- |
| Artifact | Cross-cutting defense-preparation compendium |
| Version | v1.3 |
| Date | 2026-07-31 |
| Author | Samuel Sanchez |
| Status | LIVING |
| Sibling document | [docs/15_implementation_inventory.md](15_implementation_inventory.md) (module/script/test map) |

> **Purpose.** The single entry point for defense preparation. It (a) indexes
> every existing "Anticipated defense questions" bank, (b) provides the deep
> technical dives a committee member may drill into — the RL agent's network
> and algorithm, the Gazebo wiring, the provenance of every cage threshold —
> and (c) anchors the design choices in external standards and literature.
> Nothing here changes any decision; where a decision is cited (D-NN), the
> authoritative rationale is [docs/DECISIONS.md](DECISIONS.md).

---

## 1. Index of existing defense-question banks

Every core document already carries a Q&A bank. **Note:** in docs/04, 09, 10
and 11 the bank is inside an HTML comment (`<!-- … -->`) — visible when opening
the raw Markdown, invisible in rendered previews. Don't miss them.

| Topic | Where the Q&A bank lives |
| --- | --- |
| Methodology / adapted V-model | [docs/00](00_v_model_adapted.md) §Anticipated defense questions |
| ID conventions / traceability discipline | [docs/01](01_id_conventions.md) |
| Hazard analysis (why these 12, severity scale) | [docs/02](02_hazard_register.md) |
| Safety requirements (threshold derivations) | [docs/03](03_safety_requirements.md) |
| Cage architecture, order, approximations | [docs/04](04_cage_specification.md) (commented block) |
| Scenario library (coverage, families, reps) | [docs/05](05_scenario_library.md) |
| Metrics catalogue | [docs/06](06_metrics_catalogue.md) |
| Traceability matrix / verdicts | [docs/07](07_traceability_matrix.md) |
| ODD (boundaries, TBD closure) | [docs/08](08_odd_specification.md) §13 |
| RL environment design (obs/action/termination) | [docs/09](09_environment_design.md) §9 (commented) |
| Reward function (weights, hacking, cage interplay) | [docs/10](10_reward_function.md) §9 (commented) |
| Camera RL training (CNN, DR, common cause) | [docs/11](11_camera_rl_training.md) §10 (commented) |
| Classical CV lane-keeper & estimator | [docs/12](12_cv_lane_keeper.md) §9 |
| This document | Cross-cutting deep dives + §7 extended Q&A + §8 references |

## 2. The system in sixty seconds

Two controllers drive a 1:14 differential-drive vehicle around closed lane
circuits in Gazebo: a **learned policy** (PPO for every thesis verdict;
posterior PPO/SAC studies; state-vector baseline on the F-track and end-to-end
front-camera CNN on the E-track) and, wrapped around it, a
**runtime safety cage** of six deterministic rules (C-01..C-06) whose every
threshold traces to a Safety Requirement, which traces to a Hazard. The cage
runs identically during training, evaluation and deployment (D-34). Claims are
settled by scenario campaigns run in **enforcement vs monitoring** mode — the
paired causal contrast that isolates what the cage actually contributes — and
rolled into verdicts under pre-registered statistical gates (D-29/D-30). A
traceability script fails any Gate review if a single artifact is orphaned.
The thesis question is not "is this policy safe" but "does this SE4AI process
produce auditable safety evidence for an ML component" — the policy and cage
are the vehicle for evaluating the *framework*.

---

## 3. The RL agent — algorithm, networks, and the Gazebo wiring

### 3.1 Why PPO carries the verdict — and why SAC was tested posteriorly (D-14/D-15/D-60)

**PPO** (Proximal Policy Optimization; Schulman et al., 2017) is an on-policy
actor-critic method whose clipped surrogate objective bounds how far each
update can move the policy — first-order trust-region behaviour without TRPO's
second-order machinery. Reasons it fits this project:

1. **Stability over sample efficiency.** Sim steps are cheap (headless Gazebo,
   unthrottled clock); what is expensive is diagnosing a diverged run. PPO's
   conservative updates suit a thesis timeline better than the
   higher-variance off-policy alternatives (SAC/TD3).
2. **Continuous-control default.** Steering ∈ [−1, 1] with a diagonal-Gaussian
   policy is PPO's native setting.
3. **Auditability of the training loop.** On-policy = the data always comes
   from the current policy under the current cage — no stale replay buffer
   collected under a different safety configuration (relevant to SR-009's
   "trained under deployment constraints").
4. **Ecosystem maturity.** Stable-Baselines3 (Raffin et al., 2021) provides a
   tested, widely-cited reference implementation, with `check_env` API
   validation, vectorised wrappers and callbacks; the thesis inherits its
   correctness rather than re-implementing an RL algorithm inside a safety
   project. PyTorch backend; Gymnasium (the maintained fork of OpenAI Gym,
   Brockman et al., 2016) as the env API.

At the verdict-design freeze (D-14), SAC was a contingency: it is
sample-efficient, but its replay buffer and entropy-temperature machinery add
state and failure modes that PPO avoids. That was a defensible **selection for
the verdict**, not a claim that SAC was unsuitable. D-60 later made the trainer
algorithm-selectable and ran the matched 1-D SAC comparison while holding the
environment, action, cage, reward and metrics fixed. The separate 2-D evidence
uses different historical/current speed contracts and is not a controlled
algorithm pair. The result is unusually useful:
SAC learned faster and rescued a PPO-hard seed, while the predicted machinery
failures appeared empirically as an auto-entropy cliff and a bounded replay
probe consistent with eviction-driven decay. PPO-Lagrangian remains unnecessary **by architecture**: hard constraints
are the cage's job, not the objective's (separation of concerns, docs/10 §4).

### 3.2 The networks — exactly what is learned

**F-track (state obs) — `MlpPolicy`.** Input: the 6-dim vector
`[ey, epsi, speed, prev_steer, kappa_near, kappa_far]`. SB3 default
architecture: two hidden layers of 64 tanh units each, **separate** actor and
critic towers (`net_arch pi=[64,64], vf=[64,64]`); actor head outputs the
Gaussian mean for the 1-D steering action plus a state-independent learned
log-std; critic head outputs V(s). Order of 10⁴ parameters — deliberately
small, matching a 6-dim regulation problem.

**E-track (camera obs) — `CnnPolicy` = the "NatureCNN".** Input: 4 stacked
84×84 grayscale frames (`VecFrameStack(k=4)`; SB3 auto-inserts
`VecTransposeImage`, so the tensor is 4×84×84 channel-first). The feature
extractor is the DQN Atari network (Mnih et al., 2015):

```text
Conv2d( 4→32, kernel 8×8, stride 4) → ReLU     (84×84 → 20×20)
Conv2d(32→64, kernel 4×4, stride 2) → ReLU     (20×20 → 9×9)
Conv2d(64→64, kernel 3×3, stride 1) → ReLU     (9×9  → 7×7)
Flatten (64·7·7 = 3136) → Linear(3136→512) → ReLU
```

≈1.7 M parameters in the extractor; on top of the shared 512-dim features sit
a linear actor head (steering mean + log-std) and a linear critic head. So the
precise answer to *"which CNN does the agent use?"* is: **SB3's `CnnPolicy`
with the NatureCNN feature extractor — three conv layers (32/64/64) + one
512-unit dense layer — over a 4×84×84 stacked-grayscale input.**

For posterior SAC, the observation preprocessing and `CnnPolicy`/NatureCNN
interface are unchanged, but the learned heads follow SAC: a stochastic actor
and **twin Q critics** with target updates instead of PPO's actor + V critic.
The cage still filters the action outside the learned network. No SAC-specific
perception, reward or safety rule was introduced.

Why these observation choices (fixed at E2, docs/09 §10): 84×84 is the input
size the architecture was designed for and at which the ~1 cm rendered lane
lines remain ≥1 px in the near field; grayscale because the lane cue is
white-on-asphalt **luminance** — colour would triple the input and invite
reliance on the appearance axis the H-10 domain randomisation deliberately
varies; k=4 because the camera obs has no `prev_steer` channel, so all
rate/motion cues must come from the stack (the image analogue of the F-track's
first-order memory). A recurrent policy was rejected as costlier and less
stable for the same short temporal window (docs/11 §10 Q1).

### 3.3 Hyperparameters and their provenance

| Parameter | Value | Provenance |
| --- | --- | --- |
| `learning_rate` | 3e-4 (F: constant; E: **linear anneal to 0**) | SB3/Adam default; anneal added post-collapse (see below) |
| `n_steps` | 1024 | Halved from SB3's 2048: with 500–1024-step episodes, a 1024-step rollout still spans ≥1 episode while doubling update frequency |
| `batch_size` / `n_epochs` | 64 / 10 | SB3 defaults |
| `gamma` / `gae_lambda` | 0.99 / 0.95 | SB3 defaults (standard GAE setting, Schulman et al., 2016) |
| `clip_range` | 0.2 | PPO paper default |
| `ent_coef` | 0.0 | No entropy bonus: the Gaussian log-std provides exploration; the task is regulation, not sparse exploration |
| `vf_coef` / `max_grad_norm` | 0.5 / 0.5 | SB3 defaults |
| `target_kl` | **0.5** (E-track) | **Project-tuned.** The first 1M camera run collapsed at ~105k steps: `approx_kl` ran away to ~2.7 (100× the healthy 0.02–0.4 band) and destroyed policy + value function. SB3 aborts the update when a minibatch's approx_kl exceeds 1.5·target_kl → brake at 0.75, above healthy, far below runaway |
| `normalize_reward` | true (E) | **Root-cause fix for the v2 sawtooth**: returns ~700 made the critic's `value_loss` spike to ~470; `VecNormalize(norm_reward=True, norm_obs=False)` keeps critic targets ~O(1). `norm_obs` stays **False** so eval/inference need no normalisation statistics — the obs→action map is untouched |
| `clip_range_vf` | 0.2 (E) | Bounds per-update critic movement; only meaningful together with reward normalisation |
| `seed` | 2024 (main runs) | D-36: best reward + PPO health among the 5-seed study {42,123,2024,23,666}; seeds Python/NumPy/Torch, the action space, the spawn perturbation and the DR draw |
| `sim_real_time_factor` | 0 (F) / 1 (E) | F: pure physics, run as fast as possible. E: the Gazebo camera renders in real time; unthrottling starves the image stream (docs/11 §10 Q4) |

The three E-track stability levers (`target_kl`, LR anneal, reward
normalisation + value clip) are a documented *incident-response* narrative
(CHANGELOG 21.06.2026; docs/11 §4.1): each addresses a specific observed
failure of the 1M run, not speculative tuning — a defensible engineering
story, and `metadata.json` records all of them per run.

**Posterior SAC controls (D-60).** These are algorithm/data-pipeline settings,
not reward weights:

| SAC setting | 1-D | Tuned 2-D | Why it matters |
| --- | --- | --- | --- |
| Replay buffer | 100k; diagnostic 200k probe | 150k | Camera transitions are ≈56 KB, so SB3's 1M default would be impractical; the bounded 1-D seed-2024 probe supports replay eviction rather than reward drift, without establishing transfer to 2-D or beyond 180k |
| `learning_starts` | 1k | 5k | Random-action warm-up before critic updates |
| Batch / UTD | shared batch 64 / 1 | batch 256 / 2 | The tuned 2-D recipe removes PPO-inherited handicaps |
| Entropy coefficient | `auto` or fixed **0.005** | `auto` or fixed **0.005** | Fixed entropy prevented the observed temperature collapse |
| Learning rate | 3e-4 | 3e-4, constant in tuned recipe | Explicit in the archived config/metadata |

The historical 25k pilot metadata records config paths and hashes, but five
named `*_pilot25k.yaml` files are absent from the current config tree. Treat
those pilot curves as archived evidence with a provenance gap until matching
config snapshots are restored; do not present the missing filenames as live
reproducible configs.

### 3.4 How the agent is wired to Gazebo, step by step

There is **no ROS RL "framework"** in the loop — the wiring is deliberately
minimal and inspectable (docs/15 §1.2 diagram):

1. **SB3 → env.** `model.learn()` calls `GazeboLaneEnv.step(action)` — a
   normal Gymnasium env; SB3 knows nothing about ROS.
2. **Cage in-process.** The env routes the raw action through
   `SafetyCageNode.step(state, raw_action)` — the same class + `cage.yaml` the
   deployment ROS node wraps (D-34). Enforcement: the safe action is actuated.
3. **Actuation.** The safe action becomes a `geometry_msgs/Twist` on
   `/cmd_vel`: `angular.z = steering × yaw_gain(0.8)`. For frozen GE4 1-D,
   `linear.x = fixed_speed(0.20) × scale(throttle)`; posterior 2-D maps policy
   throttle to `[0,max_speed_mps]` with a true-stop deadband. Current Gazebo
   configs cap at 0.25 m/s (diagnostic probe: 0.22); Isaac's separate contract
   uses 0.5 m/s. Constants are archived per run and mirror the actuation path.
   Gazebo's DiffDrive plugin turns the Twist into wheel speeds (the physical
   CobraFlex is differential/skid-steer — the plugin is faithful to it).
4. **Time.** `step_ros(0.1 s)` advances **simulation time**, measured from
   `/odom_truth` header stamps — so the 10 Hz control cadence is correct even
   when the sim runs many× real time (or the camera pins it to 1×).
5. **State.** Ground truth `/odom_truth` (an OdometryPublisher, *not* the
   DiffDrive dead-reckoning `/odom`, which never reflects teleports) →
   `PolylineTracker` Frenet projection → `ey/epsi/s/curvature`.
6. **Reset.** Each episode: `gz service /world/<w>/set_pose` teleport (4
   retries; the CLI does service discovery per call and can time out under
   load), settle-and-verify odom→world offset calibration, fresh cage
   instance (no latched emergency across rollouts), seeded spawn perturbation
   (±0.05 m lateral, ±0.15 rad heading).
7. **Camera (E-track).** The Gazebo camera sensor is bridged by `ros_gz` to
   `/camera/image_raw_lane` (dedicated front lane camera, 640×360, HFOV 90°,
   20 Hz, pitched down 0.30 rad); the env samples the freshest frame per
   control cycle through the shared `CameraPipeline` (one degradation point →
   both consumers).

The environment is transport-agnostic (duck-typed interface): the same
`GazeboLaneEnv` runs against `RosGazeboInterface` (Gazebo/ROS2) or
`IsaacSimInterface` (in-process Isaac, D-44) — which is *why* the posterior
Isaac track could reuse the entire training loop unchanged.

### 3.5 What the training runs actually were

Authoritative detail: docs/11 §8 (E-track) and Training Spec Ch.7 (F-track).
One-line map: F3 main = `ppo_train_2024_200k` (state obs, oval, 200k steps,
`ep_rew_mean`→536.8, eval 11.2 laps / |ey| 9.9 mm / 0% cage); E-main =
`ppo_newcam_complex_b_2024_1M` stopped ~662k, **peak rescued at 296,960 steps**
(`ep_rew_mean` 822.9) → `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip`,
eval 4.88 laps / |ey| 10.9 mm / 0 emergencies — beating the classical CV
baseline (17.2 mm) on the same circuit. Multi-seed N=5 on F3: 4/5
constraint-respecting, 1/5 cage-dependent (seed 123 — itself a finding: the
cage's value is policy-dependent).

**Post-G4 Gazebo evidence (not a verdict campaign):**

| Family | Training / nominal evidence | Safety-cage reading |
| --- | --- | --- |
| PPO camera 1-D N=5 | Study complete: 3/5 constraint-respecting; seed 666 cage-dependent; seed 23 cage–CV conflict | Confirms basin variability; GE4 seed-2024 verdict remains frozen |
| PPO camera 2-D | Historical 0.5 m/s full-authority run: peak 654.4 at 510k; competent monitoring | No full-horizon PPO 2-D enforcement run is claimed; current Gazebo configs use 0.25 m/s |
| SAC camera 1-D auto | Peak 720 at 89k; 75k eval 5.12 laps, 19.8 mm, 0 emergency, 48.3% C-06 | Fast learning followed by auto-entropy collapse |
| SAC camera 1-D entfix | Seed 2024 peak 722.5 at 83k; seeds 42/666 peaks 744.3/606.9; 3/3 enforcement-clean | Fixed `ent_coef=0.005` rescued PPO-hard seed 666; paired nominal enforcement+monitoring is complete for 2/2 evaluated pairs, while seed 42 monitoring remains pending |
| SAC 1-D buffer probe | 200k buffer held ≈690–745 through 180k; 744.7 at 155.6k | Slow decay was consistent with replay eviction; 150k eval: 4.94 laps, 26.9 mm, 0 emergency |
| SAC camera 2-D auto | Peak 527 at 154k; monitoring 4.31 laps, 32.3 mm | Enforcement stopped on zero-margin speed or D-43 CV over-read |
| SAC camera 2-D entfix | Peak 558.7 at 78k; full-horizon enforcement seeds 2024 (4.32 laps, 17.1 mm) and 42 (4.97 laps, 18.2 mm), 0 emergencies | First full-horizon Gazebo 2-D enforcement evidence; current cap 0.25 m/s |
| Gazebo 2-D qualification | Fresh-only entfix parent 75k at 0.22 m/s; buffer 150k covers parent + SC-PERT-03 λ=4.0/50k; checkpoint/config-bound D-43 gate + two-arm manifest | Implemented and tested offline; no fresh checkpoint, fine-tune or campaign cell yet |

The 0.22 m/s eval probe removed the speed-boundary stop for the auto 150k
checkpoint but not the D-43 heading over-read for auto 175k. A two-seed SAC
SC-PERT subset then produced **100/100 enforcement PASS** versus **68/100
monitoring PASS**; SC-PERT-11 monitoring was 0/10 on each seed. These subset
roll-ups are globally `INCOMPLETE` by design and do not alter GE4.

The offline D-43 matrix makes the mechanism split explicit: entfix-2024/75k
and entfix-42/50k are individual `PASS`; auto-175k at 0.25 and its 0.22 probe
are `BLOCKED`. At the latter stops the true pose remains centred while the CV
heading crosses C-02. The campaign runner now refuses an opted-in config unless
the supplied report contains a nominal enforcement PASS for the exact
checkpoint and train-config hashes.

---

## 4. The safety cage — why six rules, and where every number comes from

### 4.1 The architecture pattern and its lineage

The cage is a **runtime safety monitor with override authority** placed
between the untrusted (learned) controller and the actuators. This is an
established pattern with several names in the literature:

- **Simplex architecture** (Seto et al., 1998; Sha, 2001): a high-performance
  complex controller + a simple verified safety controller + a decision module
  that switches when the complex controller endangers the plant. The cage's
  enforcement mode *is* a Simplex decision module: C-01..C-04/C-06 are bounded
  corrections; C-05 is the switch to the simple controller (the open-loop
  controlled stop).
- **Run-Time Assurance (RTA)** — standardised for aviation in ASTM F3269
  ("bounding" untrusted flight-control functions with a monitored recovery
  function); surveyed for safety-critical autonomy by Hobbs et al. (2023).
- **Safety cages for NN-driven vehicles** — Kuutti et al. (2019; 2021, cited
  in manuscript Ch.2) introduced exactly this term for AVs: a runtime
  supervisor over a deep-learning controller. The thesis borrows the term and
  extends the *process* around it (traceability, verdicts).
- **Shielding in safe RL** (Alshiekh et al., 2018; taxonomy in García &
  Fernández, 2015): correcting the agent's unsafe actions during learning.
  D-34 (cage active in training) is a shielding instance, with one deliberate
  difference — the shield here is not synthesised from a temporal-logic spec
  but hand-derived from the hazard analysis, because auditable traceability
  to hazards *is the research object*.
- **Control Barrier Functions** (Ames et al., 2019) are the continuous
  optimisation-based cousin of C-01/C-03. Rejected as primary mechanism: a
  QP-based safety filter is harder to audit item-by-item at a Gate review
  than six explicit rules, and needs a reliable dynamics model; the thesis
  prioritises inspectability (A2) over control-theoretic optimality.

### 4.2 Why exactly six rules — the honest derivation

The number six is **not** claimed to be universally sufficient. The defensible
chain is:

1. The F1 hazard analysis produced a bounded register (now 12 hazards; scope
   exclusions explicit in D-31 — adversarial attacks, distribution shift,
   explainability et al. are *documented out*, not forgotten).
2. Each hazard demanded ≥1 Safety Requirement (14 SRs); each SR of criticality
   class A demanded a deterministic cage rule (D-28) or an explicit non-cage
   mitigation (D-25: training constraints, architecture properties).
3. Grouping those demands by observed variable and mechanism yields six
   rules, one per mechanism family — lateral bound (C-01), heading bound
   (C-02), predictive lane-departure (C-03), speed governor (C-04),
   trigger-based emergency/watchdog (C-05, 8 triggers), actuator rate limit
   (C-06). Track 'E's new hazards (H-10..H-12) were absorbed **without a new
   rule**: a training constraint (SR-012) plus a new C-05 trigger (SR-013/014)
   — evidence the rule taxonomy (direct / predictive / procedural, docs/04)
   generalises.
4. **Completeness is enforced relative to the register**: `check_traceability.py`
   fails any Gate if a hazard lacks an SR, an SR lacks an implementation, or a
   rule implements nothing. So "why 6?" → "because that is what 12 hazards ×
   14 SRs reduce to under the D-25/D-28 taxonomy, and the reduction is
   machine-checked to have no gaps *within the declared scope*."

Each rule also has a recognisable industrial analogue, which is the external
plausibility argument: C-01/C-03 ↔ lane-departure warning/keeping functions
(TLC-based, ISO 11270; van Winsum et al., 2000; Mammar et al., 2006); C-04 ↔
curve-speed governors; C-05 ↔ the watchdog + safe-state transition mandated by
functional-safety practice (ISO 26262 "safe state"); C-06 ↔ standard actuator
slew-rate protection.

### 4.3 Parameter provenance — every number, its derivation, its status

All values live in [cage/cage.yaml](../cage/cage.yaml) (v0.6.1) with inline
rationale; the SRS-level derivations are in docs/03. Summary table for the
defense (Q: *"where does 0.16 come from?"*):

| Parameter | Value | Derivation | Status |
| --- | --- | --- | --- |
| `d_max` (C-01) | 0.16 m | ODD-1 half road width 0.25 m − Δ≈0.09 m, where Δ = lateral sensing noise ~0.01 (M-1) + one-cycle drift v_max·latency = 0.5·0.05 = 0.025 (M-2) + vehicle half-footprint ~0.05 | `[provisional, M-1/M-2]` |
| `h_d` (C-01) | 0.02 m | Hysteresis ≈12% of the bound — anti-chatter, standard relay-control practice; exit needs 2 clean cycles | design |
| `theta_max` (C-02) | 0.4363 rad (25°) | Bicycle-model recoverability calculation (docs/03 SR-002): inside the recoverable envelope with ~2× margin | derived |
| `h_theta` | 0.0349 rad (2°) | Hysteresis band, same rationale as `h_d` | design |
| `t_min` (C-03 TTLC) | 1.0 s | 0.3 s cage-side kinematic margin (defensible by stopping/steering kinematics) + 0.7 s policy-side margin; consistent with the ~1 s TLC warning thresholds of the lane-departure literature (van Winsum et al., 2000; Mammar et al., 2006) | policy part `[provisional]` |
| `horizon_s` (C-03) | 3.0 s | Projection horizon; beyond it TTLC:=∞ (no false urgency on straights) | design |
| `v_max_straight` (C-04) | 0.5 m/s | = ODD-1.V_MAX (the ODD speed envelope) | `[provisional, M-4]` |
| `v_max_curve` (C-04) | 0.25 m/s | Kinematic envelope at the ODD's KAPPA_MAX under assumed friction (TBD-Q1/Q9 linkage) | `[provisional]` |
| `k_kappa` | 0.3 (m/s)/κ | Set so the linear interpolation crosses `v_max_curve` at the working KAPPA_MAX of the curvy loop | `[provisional]` |
| `theta_warning`/`d_warning` (C-05) | 20° / 0.12 m | Early-warning bands 5° / 0.04 m *inside* the C-02/C-01 hard bounds: emergency triggers before the reactive rules are already saturated | design |
| `delta_t_max` (C-05 T1) | 0.2 s (4 cycles) | STPA-informed persistence: single-cycle glitches must not trip an emergency (Leveson, 2011 — unsafe control actions include *premature* ones) | design |
| `delta_t_max_fast` (C-05 T2) | 0.1 s (2 cycles) | Same condition at v > `v_warning` = 0.4 m/s (80% of v_max): less kinematic margin ⇒ shorter persistence | design |
| `a_min` (C-05) | 0.3 m/s² | Consistency relation: stop from 0.5 m/s in 0.5/0.3 = 1.67 s ≤ SR-008's `t_stop_max` = 1.7 s (the SRS-level reconciliation recorded in the CHANGELOG) | `[provisional, M-3]` |
| `staleness_max_s` (C-05 T3) | 0.5 s | = `n_missing_max_cycles`(5) × `control_dt`(0.1 s). The 0.6.1 story: the code default 0.2 s assumed the 20 Hz loop; at 10 Hz with the CV estimator legitimately skipping 2–3 cycles at dash gaps it stopped every lap mid-curve — the budget was re-expressed in cycles, the SR-007 mandate unchanged. At 0.2 m/s, 0.5 s = 10 cm of travel, inside `d_warning` | derived |
| `state_validity_ranges` | ±0.30 m / ±π/2 / [−0.1, 1.5] m/s | Wider than the operating envelope so genuine outliers (sensor faults, H-06) are caught without clipping honest extremes | design |
| `delta_max_steering/throttle` (C-06) | 0.15 / 0.10 per cycle | Conservative defaults pending M-5 actuator envelope + the 95th-percentile natural action delta of the trained policy. Empirical cross-check: the final F3 policy's mean \|Δraw\| ≈ 0.030 ≪ 0.15, i.e. the bound shapes only outliers | `[provisional, M-5]` |
| `f_osc_max`/`t_osc_window`/`t_osc_persist` | 5 Hz / 1 s / 3 s | SR-010 Part 2: alternation above 5 Hz sustained 3 s = degenerate policy-cage feedback ⇒ emergency; below that, log-only | design |

The `[provisional, M-X]` tag is itself a defense asset: it is the explicit
admission of which numbers await measurement (calibration campaign M-1..M-5,
`tools/apply_calibration.py`) and which are derived — nothing is silently
asserted as final.

### 4.4 Evaluation order and known approximations (short form)

Order **C-06 → C-04 → C-02 → C-03 → C-01 → C-05** = ascending criticality:
sanitize the command first (feasible baseline for all downstream reasoning),
emergency last (override must win unconditionally). Known, *declared*
approximations: (i) downstream rules can re-introduce a step exceeding C-06's
bound on the emitted action — bounded consequence, candidate fixes named,
gated on Phase-4 log evidence; (ii) cage spec'd at 20 Hz vs 10 Hz training
loop — C-06 deltas interpreted per env step, provisional pending
recalibration. Both have full Q&A entries in docs/04's bank. The SR-010
joint-envelope assertion (C-05 Trigger 7) is the systemic backstop for
composition effects.

### 4.5 Who watches the cage?

Standard committee follow-up. Layered answer:

1. **Its own input validity checks** — state ranges, staleness, missing-state
   counter (SR-007/H-06); on track 'E' additionally the SR-013 health monitor
   and the SR-014 plausibility check on the CV estimate (H-12).
2. **Its own output check** — the end-of-cycle joint-envelope assertion
   (SR-010): if the *composed* correction violates any firing rule's
   invariant, C-05 fires.
3. **139 unit/integration tests** on the pure-Python class (docs/15 §6.1),
   including regression tests for real found bugs (the 0.5.1
   oscillation-window relaunch bug).
4. **The monitoring mode** — the same code path scored with corrections not
   applied; the enforcement-vs-monitoring contrast measures what the cage
   *causes*, which would surface a harmful cage.
5. **Version governance** — YAML/SRS compatibility check refuses stale
   configs; every run pins the cage-YAML hash.

---

## 5. The cage's eyes on track 'E' — why classical CV, and its tuned values

Full treatment: docs/12 §4–§5. Defense essentials:

- **Why a classical estimator and not a second CNN (D-43):** the safety
  monitor must be *auditable* — every stage of
  HSV-mask → row-scan → ground-projection → clustering → pair-selection is
  inspectable and unit-tested against synthetic frames with known geometry;
  a learned estimator would re-import the very verification problem the cage
  exists to contain. It also must be independent of the *learned* policy
  (A2), though not of the camera — the common cause is accepted and
  compensated by the perception-triggered controlled stop (C-05 Trigger 8),
  which needs no perception ("no valid lines ⇒ stop").
- **The camera model is closed-form** (pitch-only mount ⇒ analytic pixel↔
  ground mapping, `camera_geometry.py`) — no homography calibration to drift.
- **Tuned thresholds carry incident stories, not magic:** `white_sat_max`
  30 (was 70: pale grass at S≈48 leaked into the mask at far rows — found in
  the GE2 oracle validation); vegetation-hue exclusion for glare wash-out;
  `heading_window_m` 0.15 with curvature correction (full-band slope is
  unusable on r≈0.26 m bends; the value was swept on recorded apex frames to
  keep \|cv_epsi\| 0.13 rad under C-02's bound); single-line fallback mirrors
  the proven deployment node's behaviour at dash gaps.
- **Validated against an oracle before being trusted:** D-43's plan —
  `tools/validate_cv_estimator.py` grids poses and compares (ey, epsi) to the
  ground-truth tracker, clean and degraded
  (`experiments/sim/runs/cv_estimator_val_*`). The residual weakness found
  there (the H-12 "confident under-read" at the recovery-basin edge,
  ~0.120 m) is documented and bounded in the GE4-V2 verdict, not hidden.

## 6. Evaluation methodology — why the verdicts are trustworthy

- **Enforcement vs monitoring** (docs/04 §Operating modes): the same
  scenarios, seeds and policy run twice; monitoring is the no-cage
  counterfactual (raw action applied, cage shadow-logged). Differences are
  attributable to the cage alone — a paired causal design, not a
  before/after anecdote.
- **D-29 run counts** (≥25 runs per family for SR-CL-A, ≥10 for CL-B):
  pre-registered discrimination thresholds — a 25-run family bounds the
  one-sided 95% upper limit on an unobserved failure mode to ≈11% per family,
  and, more importantly for the thesis, the gate is *declared before* the
  campaign, so evidence sufficiency is not negotiated after seeing results.
- **D-30 veto:** any SR-CL-A failure invalidates the global verdict — the
  aggregation cannot average away a safety failure.
- **Three-valued verdicts (D-38):** an unevaluable run is
  `insufficient_evidence`, never silently a pass *or* a fail.
- **Literal verdicts (D-45/D-47, GE4-V2):** the recorded global verdict on the
  E-track is `NOT SATISFIED` *literal* even though the blocking clause is an
  oval-legacy recovery-time criterion the SRs pass on their own terms — the
  reconciliation is annotated *next to* the literal result rather than
  rewriting it. Committee-facing point: the framework preserves unfavourable
  literals + argued context, which is exactly what a safety case requires
  (UL 4600's claim–argument–evidence discipline).
- **Frontier scenarios (D-35)** are explicitly non-verdict-bearing: cage
  efficacy out-of-ODD is *measured* (96–100% road-edge-contact removal on the
  cage-dependent seed) but never pooled into the in-ODD verdict.

## 7. Extended Q&A — cross-cutting questions with no existing bank

**Q1. Why Gazebo and not CARLA?** (D-12) The platform is a 1:14 indoor
vehicle, not an urban car: what must be faithful are lane geometry, the
camera view and differential-drive dynamics — not traffic, pedestrians or
city assets. Gazebo is ROS2-native (the deployment middleware), runs headless
and multi-instance for 1000+-run campaigns (`GZ_PARTITION` isolation), and
its worlds are hand-authorable to the ODD spec. CARLA's fidelity would add
GPU cost and asset complexity orthogonal to every research question. The
simulator carries **all** thesis verdicts; Isaac Sim (D-44) enters only as
posterior sim-to-real bridging.

**Q2. Why a 1:14 platform?** (D-16) It makes the sim-to-real leg of SE4AI
*feasible* within a master's thesis (lab-scale, safe to fail) while keeping
real perception/actuation. Hazard severities are deliberately rated under the
analogue-real-vehicle interpretation (D-26 homothety), so the safety analysis
does not trivialise itself to toy scale.

**Q3. Seeds behaved differently — why is seed 2024 the verdict seed?**
(D-36) The N=5 study ranked seeds by reward *and* PPO health; 2024 was best
and constraint-respecting. Seed 123 (58.8% cage activity) is retained in the
frontier contrast — it is the *evidence* that the cage matters for weaker
policies — but pre-registered rules keep it out of the global verdict pool.
Posterior multi-seed replication is now complete for the 1-D camera PPO
(3/5 constraint-respecting; seed 666 cage-dependent; seed 23 cage–CV conflict)
and for SAC-entfix N=3 (3/3 enforcement-clean; paired nominal
enforcement+monitoring complete for 2/2 evaluated pairs, seed 42 monitoring
pending). These studies characterise training variance; they were not
retroactively pooled into GE4.

**Q4. Isn't ending the episode on a C-05 emergency, penalty-free, an exploit
waiting to happen?** It was — until the forward term rewarded *progress*
(ED-8/ED-9): every on-track step is net-positive, so ending early always
forfeits reward; the exploit is closed by construction and the definitive
runs confirm 0 emergencies in nominal driving.

**Q5. How does the cage-in-training relate to "shielding"?** See §4.1: same
family (Alshiekh et al., 2018), two deliberate differences — the shield is
hazard-derived rather than synthesised, and the reward never punishes cage
interventions (the cage is environment dynamics; docs/10 §5), so the policy
learns to not *need* the cage instead of learning to fear it.

**Q6. Why is SR-009's stall requirement "N/A by construction" in GE4?** (D-49) The
shared verdict action is steering-only at fixed cruise speed — the policy cannot
stall the vehicle, so a stall test has no degree of freedom to exercise
(M-P6 ≡ 0). It is now well-posed in the 2-D (steer+throttle) Gazebo and Isaac
posterior environments. The Gazebo test surface is preregistered — λ=4.0,
50k one-shot, M-P6>50 %, 20 runs/arm/mode and independent arm aggregation —
but this implementation does not itself close a new SR-009 claim: the fresh
0.22 parent, D-43 PASS, fine-tune and 80 Gazebo cells are still pending.

**Q7. Doesn't the D-43 common cause defeat the point of an independent cage?**
The independence that matters for A2 is from the *learned controller*, and
that is preserved (separate deterministic pipeline). Sensor-level redundancy
was traded against real-road generalisation (a ground-truth-fed cage cannot
leave the lab) — and the compensation is architectural: the failure response
(controlled stop) requires no perception at all. The residual risk was made a
first-class hazard (H-12) with its own SR, check and scenario evidence — the
framework *metabolised* the trade-off instead of hiding it.

**Q8. Why are hazards like adversarial attacks and distribution shift out of
scope?** (D-31) Scope control with documentation: the register targets the
hazard families a runtime cage can plausibly mitigate on this platform;
AI-specific non-functional families are excluded *explicitly, with rationale*,
so the boundary is auditable rather than accidental. (Distribution shift is
partially touched anyway: ODD boundaries + OOD frontier scenarios + H-10 DR.)

**Q9. The policy trains on ground truth (F-track) / a privileged reward
(E-track) — is that legitimate?** Yes, and it is the standard sim protocol:
privileged signals exist only at training time in sim (reward/termination/
metrics oracle); the deployed loop consumes camera + CV estimate only. See
docs/11 §10 Q5. The F/E pair is precisely the controlled experiment for "what
does real perception cost" (the E↔F delta is the perception axis).

**Q10. What in this system is actually *verified*, vs *validated*, vs
*assumed*?** Verified (deterministic, by test): the cage, RL and campaign
pure-Python kernels — latest fully green host suite **517 passed** (15.07). On
this Windows/Python 3.14 host, a 20.07 collection reached 496 before the
ROS/ament-dependent `test_eval_policy_2d.py` import failed because
`ament_index_python` is unavailable; that is not a newer green count. Validated (by
scenario campaign): closed-loop safety properties per SR, 1260 F-runs +
1970 E-runs, enforcement-vs-monitoring. Assumed (declared): ODD boundaries,
`[provisional]` thresholds pending M-1..M-5, Gazebo fidelity (bridged in
posterior work), single-fault-at-a-time scenario model. Having this
three-way split ready is the strongest possible answer shape for a
safety-engineering committee.

**Q11. The code was written with agentic AI assistance — why should the
committee trust it?** Because the *assurance* never rests on authorship, it
rests on the process — which is the thesis's own SE4AI argument applied
reflexively: (i) specs are normative and precede code (docs/03/04/09/10; code
must match the doc, not vice versa); (ii) every module has a host-testable
pure kernel — the latest fully green host suite has 517 passing tests, including
regression tests for every found
defect; (iii) the traceability gate machine-checks that no artifact floats
free of a requirement; (iv) every **verdict-bearing** experimental claim is
pinned to hashed configs + seeds + commits and is regenerable by scripts, while
the posterior pilot-config provenance gap is disclosed in §3.3; (v) a
human (the author) reviews and commits every change and signs every Gate; and
(vi) incidents are documented as incidents (KL collapse, staleness misfire,
mask leak — each with root cause and a pinned fix). An AI assistant under
this regime is a power tool inside a certified process — the same argument
the industry uses for any generated code (compilers, code generators) under
ISO 26262 tool-qualification thinking.

**Q12. What would break first if this went to the physical car?** Honest
list, and it is the declared Phase-5/posterior agenda: (1) the sim-to-real
appearance gap for both CNN and CV estimator (mitigations: H-10 DR, Isaac
scene/dynamics DR, the D-57 calibration precedent shows the workflow); (2)
actuation latency and friction differences (dynamics DR ranges already
parameterised); (3) the `[provisional]` thresholds calibrated on sim noise
(M-1..M-5 campaign exists for exactly this); (4) compute cadence (the 10 vs
20 Hz question). None of these invalidate the framework claim — they are the
framework's *next iterations*, pre-traced in docs/13–14.

**Q13. Did SAC make the cage unnecessary?** No. SAC changed which policy basin
was reached and improved sample efficiency; it did not change a single cage
rule, hazard, SR or metric. The two-seed SC-PERT subset shows the opposite:
enforcement passed 100/100 cells while the same SAC policies in monitoring
passed 68/100. The algorithm and the runtime-assurance layer answer different
questions. The honest qualification is that this is a posterior subset, not a
replacement GE4 campaign.

**Q14. "The cage only looks valuable because the policy/reward/scenarios/metrics
weren't designed well enough — fix the design and the cage is redundant."** The
strongest objection, and it *concedes the premise*. Concede first: the
**magnitude** of the cage's demonstrated intervention does depend on policy
quality — the weaker 2-D policy makes it larger (bare policy commits 98 in-ODD
road-edge contacts, enforcement removes all → 0, via 433 controlled stops; D-65),
and a stronger policy would trigger it less. That is stated, not hidden. But the
objection misses three things. **(1) It assumes you can design the failures away;
the entire premise of runtime assurance (Simplex/shielding lineage, §4.1) is that
for a *learned black-box* controller you provably cannot** — if you could certify
the policy, you would need neither RL nor a cage. "The design isn't perfect" is
the *justification* for the cage, not an objection to it. **(2) The safety
argument is architecturally decoupled from the design levers the objector names.**
Safety comes from the cage — a simple, inspectable rule set — not from the reward
(A2, docs/10 §4): RL optimises *expected return*, never worst-case safety, and a
reward-optimal policy can still commit a rare unsafe act; "better reward" is also
no free lunch (we *observed* reward-hacking, the park optimum, D-56). The
scenarios are **traceable to hazards** (Hazard→SR→Scenario), not cherry-picked,
and the *in-ODD nominal* set — the fair test — still exhibited the failures the
cage caught; out-of-ODD frontier/edge cells are explicitly labelled and separated
in the reconciliation (D-65). The metrics are pre-registered and traced to SRs;
loosening one to pass a failing case is exactly the malpractice the thesis
refuses (anti-gaming, D-47) — their strictness is a *feature* (it distinguishes a
safe controlled stop from a road-edge breach, which is what makes the
reconciliation honest). **(3) Some failures are irreducible by policy design at
all:** under severe perception degradation (SC-PERT-05 low-light) *any* driving
policy fails, because the failure is in the camera/CV estimate, not the driving
skill — a better policy does not see better. There the cage is not redundant, it
is the *only* mitigation. Finally, the **empirical control**: the posterior
longer-training run + re-run campaign is designed to test this objection directly
— if a materially better policy clears the *availability* failures (SC-NOM-03
endurance emergencies) while the *structural* ones persist (perception blindness
SC-PERT-05, cage co-activation SR-010/SC-EDGE-05, the SR-009 stall construct),
that empirically proves those residual failures are not policy-quality artefacts.
The invariant the thesis claims — 0 in-ODD road-edge contacts under enforcement —
held across every algorithm, seed, observation modality and action space tested;
its *guarantee* does not depend on policy quality, only its *visibility* does.

## 8. What is a result, and what is a finding (the defense narrative) — D-67

> **Scope of this section.** It exists so the defense tells *one* story instead of
> four. It is repo-only by author instruction (30.07.2026): none of this reasoning
> goes into `manuscript/`, because enumerating four research arms as prose is
> exactly the bloat the decision avoids. Full rationale, including what the
> decision explicitly does *not* do, is **D-67**.

### 8.1 The one-sentence answer

> *"The framework is evaluated on an end-to-end 2-D camera policy — PPO, steering
> and throttle, on the `complex_b` circuit. The earlier arms are how we got there:
> each one isolated a problem, and each fix is traceable."*

### 8.2 The four arms and what each is *for*

| Arm | It answers | Status in the defense |
| --- | --- | --- |
| **F-track** — state-vector policy, oval, ground-truth observations | *Does the framework work at all when perception is perfect?* | **Method validation.** The control arm that isolates what camera perception costs. Verdict `SATISFIED`, G3/F4. Not a headline number |
| **1-D camera E-main** — GE4-V2, complex_b 297k, 1970 runs | *Does it survive real perception?* | **Predecessor + verification data.** Closed G4. Its D-47 verdict reconciliation and its latent→active cage flip are load-bearing *method* evidence, cited as cross-checks |
| **Algorithm / action probes** — SAC studies (D-59/D-60), 2-D margin022 (D-65) | *Is the result an artefact of one algorithm, one action space, one seed?* | **Findings: problems met and overcome.** Entropy collapse, replay eviction, the speed-envelope kill, the weak-and-decayed-checkpoint trap |
| **2-D PPO 550k** (D-66) | *What does the framework certify?* | **THE result.** Evaluation + verification of cage, D-43 supervisor, scenario library, metrics and verdict spine |

### 8.3 Answering "why is the earlier work not in the thesis?"

Because it is not a *result*, it is *method*. Three defensible reasons, in the
order an examiner will accept them:

1. **A result needs one operating point.** Four arms produce four headline numbers
   on three different tracks with two observation modalities and two action spaces
   — laps are not comparable across tracks (oval 8.79 m vs complex_b 19.22 m),
   and `|ey|` is not comparable across observation modalities. Presenting them in
   parallel invites exactly the false comparison the thesis should refuse to make.
2. **The earlier arms are load-bearing where it matters — as *controls*.** They are
   what makes the cage claim non-trivial: the invariant "0 in-ODD road-edge
   contacts under enforcement" is shown to hold across algorithm (PPO/SAC), seed
   (N=5), observation (state-vector/camera) and action space (1-D/2-D). That is a
   robustness argument about the *framework*, and it belongs in the discussion of
   validity, not in a second results chapter.
3. **The failures are the contribution.** The problems found — entropy collapse,
   the decayed-checkpoint trap, H-12's confident under-read, the SR-010
   co-activation breach — are what a runtime-assurance thesis is *supposed* to
   surface. They are presented as findings with fixes, each traceable to a `D-NN`.

### 8.4 If an examiner pushes: "you cherry-picked the best arm"

Concede the shape of the objection, then separate two claims:

* **Availability** *is* policy-dependent, and the thesis says so. A weak policy
  trips the cage more (D-65: 433 controlled emergency stops); a competent one
  barely trips it (D-66 nominal: 0 safety interventions). That is expected — and
  it is why the availability numbers are reported for the trunk policy only.
* **Safety is not.** The in-ODD invariant held on *every* arm tested, including the
  weak ones. The cage's guarantee does not depend on policy quality; only its
  *visibility* does (§7, Q14). Selecting the best policy therefore makes the cage
  look *less* necessary, not more — the opposite of cherry-picking.

Then point at the selection procedure itself: the trunk checkpoint was **not**
chosen by reward. The reward-peak checkpoint (475k) was rejected for 14 safety
interventions and max `|ey|` 49 mm; 550k won on driving quality and cage
intervention rate (D-66). Selecting on reward alone would have picked the worst of
the three candidates — that is an anti-cherry-picking control, documented before
the verdict campaign ran.

### 8.5 Status: the condition was checked, and met (31.07.2026)

When D-67 was recorded (30.07.2026) the trunk claim was **conditional**:
`campaign_2d_ppo550k` was still executing, so the 2-D arm had a *nominal*
evaluation and a D-43 preflight PASS but **no verdict**, and D-67 committed to
revisiting the trunk decision — not defending it — if the campaign returned a
materially worse in-ODD safety picture than GE4-V2's.

**The campaign finished: 1890 runs, 0 errors, and the condition is met.** In-ODD
enforcement road-edge contacts are **0 on both arms**; out-of-ODD the 2-D arm more
than halves GE4-V2's (**56 vs 117**); the literal global verdict is `NOT SATISFIED`
on both, blocked by the same two SRs through the same single clause on the same
single scenario, so D-47 transfers verbatim. The verdict of record was therefore
re-pointed to this campaign across `docs/02`–`docs/08` (**D-69**), with GE4-V2 kept
as the frozen G4 gate record.

**Three things to say plainly if asked.** (a) The condition was **tested, not
waived** — if the numbers had gone the other way this section would read
differently, and that is why D-67 was written before the result. (b) The matrix now
carries **one `Not satisfied` verdict**, SR-010 (co-activation arbitration): CL-B,
non-vetoing, twice-measured, halved-but-not-eliminated by better training, carried
as future work T4. It is reported rather than reconciled, and it is the honest
counterweight to the 0-in-ODD-contacts claim. (c) The one property the campaign
surfaced that the verdict tables do not show is the **C-06 dependence** (§ the
endurance anomaly): cage-off, the *competent* policy is the only one that cannot
hold the 300 s run. The dependence is measured; its origin — co-adaptation to the
rate limiter inside the training loop — is **inferred**, and the ablation that
would prove it has not been run. Say so before being asked.

**Still open, deliberately:** `verdict_phys` (Phase 5 scaffolded, not run on
hardware), **TBD-Q10** (`ODD-3.A_LAT_MAX`, unmeasurable in simulation by
construction, D-33), and the Chapter 8 restructure that would let the camera track
lead rather than sit in §8.9 — the other item D-67 deferred, and an authoring
decision rather than an evidence one.

## 9. Reference shelf

Already grounded in the manuscript (Ch. 2 carries the full citations and the
comparison matrix): safety cages for AVs (Kuutti et al., 2019; 2021),
ISO 26262:2018, ISO 21448:2022 (SOTIF), ISO/IEC TR 5469, ISO/PAS 8800,
UL 4600 (via Koopman, 2023), AMLAS (Paterson et al.), Salay et al. (2017) on
ISO 26262 ↔ ML, PPO (Schulman et al., 2017), domain randomization lineage,
CARLA (Dosovitskiy et al., 2017), uncertainty (Sensoy et al., 2018).

Additional anchors used by this compendium (verify page/venue details before
importing into the manuscript bibliography):

- Seto, D., Krogh, B., Sha, L., Chutinan, A. (1998). *The Simplex architecture
  for safe online control system upgrades.* Proc. American Control Conference.
- Sha, L. (2001). *Using Simplicity to Control Complexity.* IEEE Software 18(4).
- ASTM F3269. *Standard Practice for Methods to Safely Bound Behavior of
  Aircraft Systems Containing Complex Functions Using Run-Time Assurance.*
- Hobbs, K. L., et al. (2023). *Runtime Assurance for Safety-Critical Systems.*
  IEEE Control Systems Magazine 43(2).
- Alshiekh, M., Bloem, R., Ehlers, R., Könighofer, B., Niekum, S., Topcu, U.
  (2018). *Safe Reinforcement Learning via Shielding.* AAAI 2018.
- García, J., Fernández, F. (2015). *A Comprehensive Survey on Safe
  Reinforcement Learning.* JMLR 16.
- Ames, A. D., Coogan, S., Egerstedt, M., Notomista, G., Sreenath, K.,
  Tabuada, P. (2019). *Control Barrier Functions: Theory and Applications.*
  Proc. European Control Conference.
- Leveson, N. (2011). *Engineering a Safer World: Systems Thinking Applied to
  Safety.* MIT Press. (STPA — used for the C-05 persistence rationale and the
  selective STPA-light pass, D-27.)
- van Winsum, W., Brookhuis, K. A., de Waard, D. (2000). *A comparison of
  different ways to approximate time-to-line crossing (TLC) during car
  driving.* Accident Analysis & Prevention 32(1). (TTLC ↔ C-03.)
- Mammar, S., Glaser, S., Netto, M. (2006). *Time to line crossing for lane
  departure avoidance.* IEEE Trans. Intelligent Transportation Systems 7(2).
- ISO 11270:2014. *Lane keeping assistance systems (LKAS) — performance
  requirements and test procedures.* (Industrial analogue of C-01/C-03.)
- Mnih, V., et al. (2015). *Human-level control through deep reinforcement
  learning.* Nature 518. (The NatureCNN architecture + the 84×84 grayscale
  4-frame-stack preprocessing convention.)
- Raffin, A., Hill, A., Gleave, A., Kanervisto, A., Ernestus, M., Dormann, N.
  (2021). *Stable-Baselines3: Reliable Reinforcement Learning
  Implementations.* JMLR 22(268).
- Haarnoja, T., Zhou, A., Abbeel, P., Levine, S. (2018). *Soft Actor-Critic:
  Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic
  Actor.* ICML 2018. (Posterior SAC algorithm comparison, D-60.)
- Brockman, G., et al. (2016). *OpenAI Gym.* arXiv:1606.01540. (Gymnasium is
  its maintained successor — the env API used here.)
- Tobin, J., et al. (2017). *Domain randomization for transferring deep neural
  networks from simulation to the real world.* IROS 2017. (H-10 visual DR.)
- Peng, X. B., Andrychowicz, M., Zaremba, W., Abbeel, P. (2018). *Sim-to-Real
  Transfer of Robotic Control with Dynamics Randomization.* ICRA 2018.
  (Isaac dynamics DR lever.)
- Bojarski, M., et al. (2016). *End to End Learning for Self-Driving Cars.*
  arXiv:1604.07316. (E2E camera-to-steering lineage of track 'E'; the modern
  descendant of Pomerleau's ALVINN, 1989.)
- Shalev-Shwartz, S., Shammah, S., Shashua, A. (2016). *Safe, Multi-Agent,
  Reinforcement Learning for Autonomous Driving.* arXiv:1610.03295. (Cited in
  docs/09 §10 for the E2E training-budget argument.)

## Version log

- **v1.0 (2026-07-07):** first release: Q&A-bank index, PPO/NatureCNN deep
  dive with hyperparameter provenance, Gazebo wiring narrative, cage lineage +
  full threshold-provenance table, CV-estimator defense essentials,
  evaluation-methodology summary, 12 cross-cutting Q&As, reference shelf.
- **v1.1 (2026-07-20):** keeps PPO as the frozen verdict algorithm while adding
  the D-60 posterior SAC rationale, architecture distinction, entropy/replay
  failure diagnoses, Gazebo 1-D/2-D evidence, 0.25/0.22 speed-margin result,
  two-seed SC-PERT subset and updated multi-seed/test-suite answers. Separates
  all posterior evidence from GE4 and records the missing-pilot-config
  provenance gap explicitly.
- **v1.2 (2026-07-30):** adds §8, the defense narrative under **D-67** — the 2-D
  PPO policy as the single result of record, the other three arms reclassified as
  method validation / verification data / findings-with-fixes, the "you
  cherry-picked the best arm" rebuttal, and the honest note that the trunk claim
  is conditional on a campaign verdict that did not yet exist. Old §8 (reference
  shelf) renumbered to §9.
- **v1.3 (2026-07-31):** rewrites §8.5 — the D-67 condition was **checked and met**
  (1890 runs, 0 in-ODD road-edge contacts on both arms, out-of-ODD 56 vs 117), the
  verdict of record is re-pointed to the 2-D campaign under **D-69**, and the section
  now states the three things to volunteer under questioning: the condition was
  tested rather than waived, SR-010 is a reported `Not satisfied`, and the C-06
  dependence is measured but its co-adaptation origin is inferred. Also fixes the
  stale `Version` field, which still read v1.1 after the v1.2 entry landed.
