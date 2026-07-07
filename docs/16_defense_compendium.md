# Defense Compendium — How It Works, Why It Is Built This Way, and the Literature Behind It

| Field | Value |
| --- | --- |
| Artifact | Cross-cutting defense-preparation compendium |
| Version | v1.0 |
| Date | 2026-07-07 |
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
circuits in Gazebo: a **learned policy** (PPO; state-vector baseline on the
F-track, end-to-end front-camera CNN on the E-track) and, wrapped around it, a
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

### 3.1 Why PPO (D-14) and why Stable-Baselines3 (D-15)

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

Rejected/contingency alternatives (policy/README, D-14): SAC (off-policy,
sample-efficient, but replay-buffer + entropy-temperature machinery adds
failure modes with no need given cheap sim steps); PPO-Lagrangian (constrained
RL) — unnecessary **by architecture**: hard constraints are the cage's job,
not the objective's (separation of concerns, docs/10 §4).

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

### 3.4 How the agent is wired to Gazebo, step by step

There is **no ROS RL "framework"** in the loop — the wiring is deliberately
minimal and inspectable (docs/15 §1.2 diagram):

1. **SB3 → env.** `model.learn()` calls `GazeboLaneEnv.step(action)` — a
   normal Gymnasium env; SB3 knows nothing about ROS.
2. **Cage in-process.** The env routes the raw action through
   `SafetyCageNode.step(state, raw_action)` — the same class + `cage.yaml` the
   deployment ROS node wraps (D-34). Enforcement: the safe action is actuated.
3. **Actuation.** The safe action becomes a `geometry_msgs/Twist` on
   `/cmd_vel`: `angular.z = steering × yaw_gain(0.8)`,
   `linear.x = fixed_speed(0.2) × scale(throttle)` — constants that *mirror*
   `vehicle_control_node`, so training actuation ≡ deployment actuation.
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

**Q3. Two seeds behaved differently — why is seed 2024 the verdict seed?**
(D-36) The N=5 study ranked seeds by reward *and* PPO health; 2024 was best
and constraint-respecting. Seed 123 (58.8% cage activity) is retained in the
frontier contrast — it is the *evidence* that the cage matters for weaker
policies — but pre-registered rules keep it out of the global verdict pool.
Multi-seed verdict replication is a declared posterior item.

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

**Q6. Why is SR-009's stall requirement "N/A by construction"?** (D-49) The
shared 1-D action is steering-only at fixed cruise speed — the policy cannot
stall the vehicle, so a stall test has no degree of freedom to exercise
(M-P6 ≡ 0). It becomes well-posed with the 2-D (steer+throttle) action of the
Isaac posterior track, which is exactly why D-49 schedules the retrain there.

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
*assumed*?** Verified (deterministic, by test): the cage rules' logic —
139 tests; the campaign/verdict arithmetic — 357 tests. Validated (by
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
pure kernel — 503 tests pass, including regression tests for every found
defect; (iii) the traceability gate machine-checks that no artifact floats
free of a requirement; (iv) every experimental claim is pinned to hashed
configs + seeds + commits and is regenerable by scripts, not asserted; (v) a
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

## 8. Reference shelf

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
