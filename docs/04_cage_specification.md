# Cage Specification

**Status:** Living document — Phase 2 deliverable (G2 approved; **verified at G4, 02.07.2026**)  
**Last update:** 31.07.2026 (verdict of record re-pointed to the 2-D PPO 550k pre-deployment campaign, D-69; two C-06 findings added to the framing note. Cage YAML unchanged at **0.6.1** — no rule, threshold or parameter changed on this evidence)  
**Approved at Gate:** G2 (approved)  
**Cage YAML version:** **0.6.1** (`cage/cage.yaml`).

## Purpose

This document specifies the runtime safety cage as an explicitly designed engineering artefact. It defines the architecture, the rules, the parameters, the evaluation order, the operating modes, and the interface to the rest of the system.

> **Current-state framing (G4 closed, 02.07.2026).** The cage rules C-01..C-06 and
> `cage.yaml` are **shared, unchanged, across both tracks** — only the *source* of the
> `state` differs (F-track: ground truth via `PolylineTracker`; track 'E': the cage's own
> deterministic CV lane-estimator, **D-43**, the Track-E note below). The verdict of record is
> the **2-D PPO 550k pre-deployment campaign** (31.07.2026, D-66/D-69); **GE4-V2** is the frozen
> G4 gate record (`docs/07`, `docs/11` §8.4). Crucially the **cage YAML is byte-identical across
> the 2-D campaigns** (`4287fe71…`, shared with margin022), so the D-65 → D-66 contrast isolates
> the *policy*, not the instrument. Three findings from GE4-V2 belong here, so the knowledge is
> preserved — followed by two the 2-D arm added:
>
> 1. **The cage is *latent* in-ODD but a safety asset.** At the fixed 0.20 m/s operating point
>    it never fires C-01/C-02/C-03/C-05 on clean nominal driving, yet it **removes the
>    perception-degradation failures the bare policy commits** (glare/worn/gaps: enforcement
>    PASS vs monitoring FAIL) via the SR-013/Trigger-8 controlled stop — the in-ODD cage-value
>    result under the camera.
> 2. **The speed rules C-04/C-05 were *structurally latent*** because the 1-D verdict caps
>    speed at 0.20 m/s, below every C-04 ceiling (M-S2 ≡ 0 in-ODD, the F4/GE4 central finding).
>    The **2-D action posterior** (D-50, `max_speed = V_MAX = 0.5 m/s`) makes them **arbitrate
>    for real** — the D-50 Isaac pilot measures C-04 active on 0.7–1.8 % of steps, the
>    latent→measured flip. `cage.yaml` is consumed **as-is** for the 2-D action (the throttle
>    maps onto the `u ∈ [0,1]` scale the rules already use — no cage change).
> 3. **The H-12 confident under-read** (§Track-E note; docs/12 §4.4) is the one real residual:
>    an off-centre CV estimate that locks onto a neighbour-lane pair is *self-consistent*, so
>    SR-014's plausibility check cannot reject it and C-01 never fires. Boundary-marginal
>    in-ODD (2/30 SC-EDGE-02); the honest closure is better perception, not a single-frame
>    rule (the ruta-2b patch was reverted, D-48).
>
> Two more from the **2-D verdict of record** (31.07.2026), both about C-06:
>
> 4. **C-06 is doing load-bearing lane-keeping, not just smoothing.** On the 300 s endurance
>    scenario the 2-D policy holds the two tightest `complex_b` apexes with an intervention
>    ledger of `{C-06: 58124}` and **zero C-01/C-02/C-03/C-05**; with the cage off, the *same*
>    command stream leaves the lane in 17 of 25 runs (|ey| max 145 mm vs 36 mm, applied
>    per-cycle Δsteer 2.0 vs the 0.15 bound). The policy's raw command is ~2× jerkier than its
>    predecessors' and saturates the limiter in 77.5 % of steps. So **"the cage is latent
>    in-ODD" is a statement about the *safety rules*, not about the cage**: here their latency is
>    *produced* by C-06 acting upstream. The dependence is measured; its origin (co-adaptation to
>    the limiter inside the training loop) is inferred — the ablation that would prove it has not
>    been run.
> 5. **Consequence for the physical platform.** A policy this coupled to a specific
>    `delta_max_steering_per_cycle` is a **transfer risk** where actuator dynamics differ from the
>    simulated rate limit (declared as T2), and SR-006's CL-B *smoothness* classification
>    undersells what C-06 is doing. Nothing in `cage.yaml` changes on this evidence; the reading
>    of it does.
>
> The parameters below stay `[provisional]` pending the physical calibrations (M-1..M-5); the
> 2-D verdict of record is the first context that actually exercises the speed thresholds.

The cage is implemented as a ROS2 node under `cage/`. Its parameters are externalised in `cage/cage.yaml`, version-controlled, and referenced by hash in the metadata of every experimental run.

## Design philosophy

Three forms of safety are reconciled in the cage's design:

- **Direct safety** addresses bounds that must hold on observable state variables (lateral offset, heading error). Implemented by reactive rules.
- **Predictive safety** addresses bounds whose violation can be anticipated through short-horizon kinematic propagation (TTLC). Implemented by predictive rules.
- **Procedural safety** addresses behaviours that must occur under specific conditions (transition into emergency mode when state becomes invalid). Implemented by trigger-based rules.

Each form motivates a distinct family of cage rules.

## Architecture

The cage is a dedicated ROS2 node, distinct from the policy node. Its interface:

**Inputs (subscribed topics):**

- `/raw_action` (from policy node) — proposed steering and throttle commands.
- `/state_obs` (from perception node) — current state vector.
- `/external_stop` — external emergency stop signal.

**Outputs (published topics):**

- `/safe_action` — the corrected (or substituted) command sent to the actuators.
- `/cage_status` — per-cycle log entry: which rules fired, with what magnitude, on what state.

**Internal state:**

- Previous command (for rate limiting).
- Emergency mode flag.
- Last valid state timestamp.

**Operating modes:**

- `enforcement` — corrections are applied to `/safe_action`.
- `monitoring` — corrections are computed and logged but not applied; `/safe_action` equals `/raw_action`. Used for the causal comparison in the experimental campaign.

The mode is set by a launch parameter and recorded in the metadata of every run.

### Track-E note — cage perception (D-42 superseded by D-43)

On the parallel **track 'E'** (end-to-end front-camera policy, D-41) the cage's `state` (`/state_obs`) is produced by a **dedicated, deterministic computer-vision lane-detection pipeline** — separate from the policy's learned CNN, and **not** from privileged ground truth (decision **D-43**, which supersedes D-42's "cage on ground truth, never the camera"). The cage still evaluates C-01..C-06 **unchanged** over this `state`; only the *source* of the state changes (the CV-estimator node instead of `PolylineTracker(/odom_truth)`). Ground truth survives **in simulation only**, as the training reward and an **oracle** to measure the CV estimator's error — never as a runtime input.

This keeps the cage independent of the **learned policy** and **auditable** (a classical CV algorithm is inspectable, unlike the CNN), so the A2 "independently-verifiable cage" property still holds; and it lets the cage generalise to **any road with visible lane lines**, like the policy. The honest trade-off (D-43): policy and cage now both rely on the camera, so a camera fault (H-10/H-11) can blind **both** at once (common-cause) — the residual safety is the open-loop **controlled stop** (SR-013 / C-05, which needs no perception: "no lines ⇒ stop"). A confidently *wrong* CV estimate is a new hazard, **H-12** (cage lane-misdetection), mitigated by **SR-014** (estimator plausibility / temporal-consistency check + conservative fall-back to C-05). Still **no new numbered cage rule**: SR-012 by C-01/C-02/C-03 over the CV state + a training constraint, and SR-013 / SR-014 by C-05 (Trigger 8 below).

**Implemented (E2, cage YAML 0.6.0; staleness budget refined in 0.6.1).** The CV estimator and its supervision are built and host-tested: `cobraflex_rl/cv_lane_estimator.py` (HSV white mask with vegetation-hue exclusion → per-row white-run candidates → metric ground-frame projection via the closed-form pitch-only camera model `camera_geometry.py` → polynomial line clustering → driven-lane pair selection → `ey/epsi/lane-width/curvature` at the vehicle), wrapped by `cage_perception.CagePerceptionSupervisor` (health per SR-013 + plausibility per SR-014 → cage `state` or `perception_invalid`). In the training/eval loop (`gazebo_lane_env`, camera mode) the cage consumes **only** this estimate; ground truth keeps driving reward, termination and metrics (the oracle role). Estimator-vs-oracle accuracy: `experiments/sim/runs/cv_estimator_val_*` (GE2 evidence).

## Rules

The cage implements six rules, C-01 through C-06. Each rule is an independent module under `cage/rules/`. The full rule code is in `cage/rules/cXX_<name>.py`; the specification below is the source of truth for what that code must implement.

### C-01 Lane boundary hard limit

**Implements.** SR-001.
**Mitigates.** H-01.
**Type.** Reactive (direct safety).

**Observed variable.** Lateral offset `d`.

**Logic.**

```python
if abs(d) > (d_max - h_d) and policy_action_increases_abs_d():
    correction = bounded_steering_toward_centre(d, d_max, h_d)
    fire = True
elif abs(d) < (d_max - 2*h_d) for last 2 cycles:
    fire = False
```

**Parameters (from `cage.yaml`).**

- `d_max = 0.16 m` (from SR-001).
- `h_d = 0.02 m` (hysteresis margin).

**Correction strategy.** Bounded modification of the steering command in the direction of the lane centre. Magnitude proportional to how far inside the warning band the vehicle is. Hysteresis avoids chattering at the boundary.

---

### C-02 Heading error limit

**Implements.** SR-002.
**Mitigates.** H-02.
**Type.** Reactive (direct safety).

**Observed variable.** Heading error `θ`.

**Logic.**

```python
if abs(theta) > (theta_max - h_theta) and policy_action_increases_abs_theta():
    correction = bounded_steering_toward_alignment(theta, theta_max, h_theta)
    fire = True
elif abs(theta) < (theta_max - 2*h_theta) for last 2 cycles:
    fire = False
```

**Parameters.**

- `theta_max = 0.44 rad (25 deg)` (from SR-002).
- `h_theta = 0.035 rad (2 deg)` (hysteresis).

**Correction strategy.** Bounded modification with directional bias toward the lane axis. Conservative: produces a safe, monotonic correction that the policy can subsequently refine.

---

### C-03 Predictive lane departure (TTLC)

**Implements.** SR-003.  
**Mitigates.** H-01 (primarily), H-02 (partially).  
**Type.** Predictive.  

**Observed variables.** Lateral offset `d`, heading error `θ`, forward speed `v`.

**Logic.**

```python
ttlc = compute_ttlc(d, theta, v, d_max)
if ttlc < t_min:
    correction = precautionary_steering_toward_centre(d, magnitude=urgency(ttlc))
    fire = True
```

The function `compute_ttlc` projects the trajectory under the assumption of zero corrective action and returns the time at which `|d|` would equal `d_max`. If the projection does not lead to a crossing within a long horizon, returns infinity.

**Parameters.**

- `t_min = 1.0 s` (from SR-003).

**Correction strategy.** Gradient-like bounded correction. Magnitude scales with urgency: lower TTLC means larger correction, capped at the rate-limit envelope. Operates simultaneously with C-01; if both fire on steering, the larger-magnitude correction wins.

---

### C-04 Speed ceiling

> **UN-ARMABLE AT THE DEPLOYED SPEED CAP — a stated limitation of the validation, not an
> oversight (D-75, 31.08.2026).** The ceiling is `max(v_max_curve, v_max_straight − k_kappa·|κ|)`,
> so **0.25 m/s is a floor no curvature can push it below**, while the deployed policy is capped at
> 0.22 m/s. Over the 2484 moving cycles of the 31.08 track session the achieved speed was median
> 0.166, p99 0.209, **max 0.228 m/s**, and the count of cycles reaching 0.25 was **zero**. C-04
> fired **0/1890** in the D-69 verdict campaign (finding (ii)) and has **never arbitrated on
> hardware**. It is deliberately left that way: its curvature input over-reads by ~3× on the closed
> circuit (D-75's `∮κ·ds` test), so lowering the threshold would arm the rule on phantom curvature,
> concentrated exactly where the car is already off-centre (D-76). Re-arming is blocked on the
> capture session of docs/17 §10.6, not on more driving.

**Implements.** SR-004.
**Mitigates.** H-03.
**Type.** Reactive (direct safety, parameterised).

**Observed variables.** Forward speed `v`, local curvature `κ` (estimated from the recent trajectory).

**Logic.**

```python
v_ceiling = compute_v_max(kappa)  # from cage.yaml table
if v > v_ceiling:
    correction = throttle_command_to_reach(v_target=v_ceiling)
    fire = True
```

**Parameters.**

- `v_max_straight = 0.5 m/s`.
- `v_max_curve = 0.25 m/s`.
- `k_kappa = 0.3 m/s per unit curvature`.

**Correction strategy.** Bounded modification of the throttle command only; steering is not affected.

---

### C-05 Emergency mode

**Implements.** SR-005, SR-007, SR-008, SR-013, SR-014 (SR-013/SR-014 on track 'E' only — see Trigger 8).
**Mitigates.** H-04, H-06, H-07, H-11, H-12 (H-11/H-12 on track 'E').
**Type.** Trigger-based (procedural safety).

**Triggers (any of these activates emergency mode):**

1. Compound state, low-energy: `abs(theta) > theta_warning AND abs(d) > d_warning` for more than `delta_t_max` consecutive seconds.
2. Compound state, high-energy: `abs(theta) > theta_warning AND abs(d) > d_warning AND v > v_warning` for more than `delta_t_max_fast` consecutive seconds. The high-energy variant shortens the persistence requirement because the kinematic margin at elevated speed is smaller.
3. Stale state: timestamp of last `/state_obs` older than `staleness_max`.
4. Invalid state field: any field outside its plausible range.
5. Missing state: no `/state_obs` received for `N_missing_max` consecutive cycles.
6. External stop: `/external_stop` signal received.
7. Joint-envelope assertion failure (see §Joint-envelope assertion below).
8. (Track 'E', D-43) Perception-health invalid: the cage's CV lane-estimator reports either **loss** of a valid lane (occlusion, absent features, frame stale / dropped beyond `perc_staleness_max`) **or** a failed **plausibility / temporal-consistency** check (a suspect, possibly false detection). Implements SR-013 (loss) and SR-014 (misdetection); mitigates H-11 and H-12. On this trigger the cage executes the open-loop controlled stop — which needs no perception ("no valid lines ⇒ stop").

**Implementation status (cage YAML 0.6.0).** Triggers 1–7 are implemented in [cage/rules/c05_emergency.py](../cage/rules/c05_emergency.py) and [cage/cage_node.py](../cage/cage_node.py); Triggers 1–4 and 6 are exercised by [test_c05_emergency.py](../cage/tests/test_c05_emergency.py), Triggers 2 and 5 by [test_c05_triggers_extended.py](../cage/tests/test_c05_triggers_extended.py), Trigger 5's cage_node-level counter (`_cycles_since_last_state`) by [test_cage_node_missing_state.py](../cage/tests/test_cage_node_missing_state.py), Trigger 7 (joint-envelope assertion, SR-010 Part 1) by [test_joint_envelope.py](../cage/tests/test_joint_envelope.py), and the inter-cycle oscillation check (SR-010 Part 2, the `oscillation_detected` trigger) by [test_oscillation.py](../cage/tests/test_oscillation.py).

**Trigger 8 is implemented (cage YAML 0.6.0, track 'E').** C-05 consumes a single boolean, `ctx["perception_invalid"]`, raised by the **external perception supervisor** ([cobraflex_rl/cage_perception.py](../src/cobraflex_rl/cobraflex_rl/cage_perception.py)) that composes the deterministic CV lane-estimator ([cv_lane_estimator.py](../src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py), classical CV over the closed-form pitch-only ground-plane mapping of [camera_geometry.py](../src/cobraflex_rl/cobraflex_rl/camera_geometry.py)) with the SR-013 health monitor (`perception_health.py`: stale/dropped frame, low confidence, missing features) and the SR-014 plausibility / temporal-consistency check (`lane_plausibility.py`). The trigger is gated by the YAML key `c05_emergency.perception_trigger_enabled` (code default **false**, so pre-0.6.0 YAMLs keep their exact behaviour; the 0.6.0 YAML ships it **true**). Coverage: [test_c05_perception_trigger.py](../cage/tests/test_c05_perception_trigger.py) for the rule, `policy/tests/test_cage_perception.py` for the supervisor composition. The supervisor's thresholds live with the supervisor, not in `cage.yaml` — the cage stays camera-agnostic. Per D-43's verification plan, the estimator's error is validated in sim against the ground-truth oracle (`tools/validate_cv_estimator.py` → `experiments/sim/runs/cv_estimator_val_*`).

**On activation:**

- Replace throttle command with a deceleration target producing at least `a_min`.
- Freeze steering at its value at the instant of transition.
- Publish emergency signal on `/cage_status`.

**On deactivation:** only via explicit reset signal AND underlying condition cleared. This prevents oscillatory entry/exit.

**Parameters.**

- `theta_warning = 0.35 rad (20 deg)`.
- `d_warning = 0.12 m`.
- `v_warning = 0.4 m/s` (80 % of `v_max_straight`; from SR-005 Trigger B).
- `delta_t_max = 0.2 s` (Trigger 1).
- `delta_t_max_fast = 0.1 s` (Trigger 2).
- `a_min = 0.3 m/s²`.
- `staleness_max = 0.2 s`.
- `N_missing_max = 5 cycles`.

**Correction strategy.** Substitution rather than modification: the policy is no longer trustworthy in the trigger conditions, so its commands are replaced rather than tweaked.

---

### C-06 Actuator rate limiter

**Implements.** SR-006.
**Mitigates.** H-05.
**Type.** Bounded derivative (always active).

**Observed variables.** Previous and current commanded steering and throttle.

**Logic.**

```python
delta_steering = current_steering_cmd - prev_steering_cmd
if abs(delta_steering) > delta_max_steering:
    current_steering_cmd = prev_steering_cmd + sign(delta_steering) * delta_max_steering

# same for throttle
```

**Parameters.**

- `delta_max_steering = 0.15` (normalised units per 50 ms cycle).
- `delta_max_throttle = 0.10` (normalised units per 50 ms cycle).

**Correction strategy.** Always active, no conditional. Operates on the command space rather than the state space.

## Evaluation order

The rules are evaluated in a fixed deterministic order at every control cycle, in **ascending criticality** as defined in the Phase 2 plan (`docs/.phases/Fase 2/fase_2_detallada.md` §2.1):

**C-06 → C-04 → C-02 → C-03 → C-01 → C-05**  

Rationale for each position:

1. **C-06 first.** Sanitises the raw policy command into a physically realisable action (bounded delta against the previous emitted action). Subsequent rules then operate on a feasible baseline, so their corrections do not need to reason about implausible large jumps. The plan documents this position explicitly in §5.6 of the detailed plan.
2. **C-04.** Throttle ceiling depending on curvature. Independent channel from the steering rules; placed early to make the speed-bounded action visible to the downstream steering rules in their internal reasoning.
3. **C-02.** Reactive bound on heading error. Modifies steering.
4. **C-03.** Predictive bound (TTLC). May further override steering if the kinematic projection indicates an imminent boundary crossing.
5. **C-01.** Reactive hard bound on lateral offset. The last reactive guard before emergency mode takes over; together with C-03 it implements defence in depth on H-01.
6. **C-05 last.** Emergency mode. When triggered, its substituted action (frozen steering + brake) overrides every upstream correction. Placing it last guarantees the override semantics regardless of what upstream rules have done.

Each rule consumes the previous rule's `safe_action` as its `raw_action` input; the rule returns either `safe_action=None` (pass-through) or a new tuple. The order, the chain composition, and the override semantics of C-05 are exercised by the integration tests in `cage/tests/test_cage_node.py`.

### Known approximation (F2)

The plan's "C-06 first" position guarantees that the action *entering* the chain is rate-bounded. Downstream rules (C-01..C-04) can in principle introduce a step that violates the rate bound on the *emitted* action. This is accepted as an F2 approximation; a second, terminal C-06 pass (or per-rule rate-budgeting) is a candidate refinement once Phase 4 logs quantify whether the violation occurs in practice and at what magnitude. The joint-envelope assertion described under SR-010 (Trigger 7 of C-05) is the long-term mitigation.

## Joint-envelope assertion and conflict resolution

The evaluation order above is a single-pass deterministic pipeline; corrections compose by additive merging (C-01 + C-02 on steering), max-merging (C-01 + C-03 on steering, worst-case envelope), independent channels (C-04 on throttle), and final smoothing (C-06). The pipeline is therefore non-iterative by construction — there is no inner fixed-point loop and no risk of an "infinite correction" within a single cycle.

What can still fail, however, is the *joint* envelope: it is in principle possible for the composed correction (e.g., C-01 + C-02 additive, then capped by C-06's rate limit) to lie outside the safe-envelope predicate of one of the individually firing rules — for instance, if C-06's rate cap prevents the C-01 correction from reaching the boundary band within a single cycle. SR-010 makes this case explicit and the cage shall handle it via an end-of-cycle check:

**End-of-cycle assertion (implements SR-010).** After the C-06 step and before publishing `/safe_action`:

```python
for rule in active_rules_this_cycle:
    if not rule.safe_envelope_predicate_holds(command_out):
        log_joint_envelope_failure(rule.id, command_out)
        trigger_emergency_mode()  # Trigger 7 of C-05
        break
```

**Inter-cycle oscillation check (implements SR-010).** A monitoring counter tracks consecutive cycles in which contradictory rules fire (e.g., C-01 firing left in cycle `n` and C-01 firing right in cycle `n+1`). If the alternation frequency exceeds `f_osc_max = 5 Hz` over a `t_osc_window = 1 s` window, the cage logs the event for offline review; sustained oscillation beyond `t_osc_persist = 3 s` triggers emergency mode (the alternation is taken as evidence of a degenerate policy-cage feedback that requires human intervention).

**Parameters.**

- `f_osc_max = 5 Hz` (from SR-010).
- `t_osc_window = 1 s`.
- `t_osc_persist = 3 s`.

The joint-envelope assertion and the oscillation check are exercised by `cage/tests/test_joint_envelope.py` (covering rule pairs and triples) and by scenario SC-EDGE-05 (cage rule co-activation matrix).

## Parameters and configuration management

All parameters listed above are centralised in `cage/cage.yaml`. Updating a parameter requires:

1. Editing `cage/cage.yaml`.
2. Recording the rationale and evidence in `docs/08_change_log.md`.
3. Re-running the full cage unit-test suite (`pytest cage/tests/`).
4. Re-running the affected scenarios in the validation campaign.

The `cage.yaml` is referenced by hash in the metadata of every experimental run, so any reported result can be uniquely associated with the parameter set under which it was obtained.

## Operating modes

### Enforcement mode

The default. Corrections produced by the rules are applied to `/safe_action`. This is the operational configuration.

### Monitoring mode

The diagnostic. Corrections are computed and logged in `/cage_status` but are not applied; `/safe_action` equals `/raw_action`. Used for two purposes:

1. **Causal comparison in the experimental campaign.** Running the same scenarios in both modes isolates the causal contribution of the cage to the safety properties of the system.
2. **Offline development diagnostic.** Replaying recorded sessions in monitoring mode allows the analyst to inspect which rules would have intervened, where, and why, without committing to a runtime correction.

The mode is set at launch and recorded in `metadata.json` of every run.

## Unit tests

Each rule has a dedicated test file under `cage/tests/`. Current status (cage YAML 0.6.1, **139 tests passing**, verified 2026-07-07):

| File | Coverage |
| ---- | -------- |
| [test_c01_lane_boundary.py](../cage/tests/test_c01_lane_boundary.py) | Hysteresis, bounds, sign of correction, saturation, disable |
| [test_c02_heading_limit.py](../cage/tests/test_c02_heading_limit.py) | Same pattern on heading_error |
| [test_c03_ttlc.py](../cage/tests/test_c03_ttlc.py) | `compute_ttlc`, urgency ramp, predictive activation |
| [test_c04_speed_ceiling.py](../cage/tests/test_c04_speed_ceiling.py) | `v_max(κ)`, throttle reduction, curvature behaviour |
| [test_c05_emergency.py](../cage/tests/test_c05_emergency.py) | Triggers 1, 3, 4, 6; persistence; reset semantics; freeze steering |
| [test_c05_triggers_extended.py](../cage/tests/test_c05_triggers_extended.py) | Trigger 2 (high-energy); Trigger 5 (missing-state via ctx) |
| [test_c05_perception_trigger.py](../cage/tests/test_c05_perception_trigger.py) | Trigger 8 (perception invalid, track 'E'); `perception_trigger_enabled` back-compat gate |
| [test_c06_rate_limiter.py](../cage/tests/test_c06_rate_limiter.py) | Per-component clipping, boundary, disable |
| [test_cage_node.py](../cage/tests/test_cage_node.py) | Chain composition, modes, prev_action tracking, emergency override |
| [test_cage_node_missing_state.py](../cage/tests/test_cage_node_missing_state.py) | Missing-state counter, no-state-ever safe-stop |
| [test_joint_envelope.py](../cage/tests/test_joint_envelope.py) | SR-010 Part 1: per-rule envelope predicates, post-chain assertion → C-05 Trigger 7, rule pairs/triples |
| [test_oscillation.py](../cage/tests/test_oscillation.py) | SR-010 Part 2: alternation-rate window, persistence → emergency, stale-timestamp filter (0.5.1 regression) |
| [test_integration_chain.py](../cage/tests/test_integration_chain.py) | End-to-end synthetic trajectory across all six rules (Phase-2 plan §13(5)) |
| [test_pipeline.py](../cage/tests/test_pipeline.py) | PD → cage → logger 200-cycle pipeline (pure-Python M1-demo analogue) |
| [test_logger.py](../cage/tests/test_logger.py) | CSV schema stability of the cage log |
| [test_cage_rules.py](../cage/tests/test_cage_rules.py) | YAML load + per-rule smoke tests |
| [test_sr_spec_version_check.py](../cage/tests/test_sr_spec_version_check.py) | `IncompatibleCageConfigError` on missing/unknown `compatible_sr_spec_version` |

The rule-pair conflict coverage originally deferred to a future `test_evaluation_order.py` landed as `test_joint_envelope.py` (together with Trigger 7 of C-05) plus the cross-rule `test_integration_chain.py`. The complete repo-wide test inventory, with each file mapped to the SR/artifact it evidences, is in [docs/15_implementation_inventory.md](15_implementation_inventory.md) §6.

The full suite is run before any commit to `main` and before any Gate review.

<!--
## Anticipated defense questions

**Q1. Why this specific evaluation order, and why is C-06 (rate limiter) first while C-05 (emergency) is last?**
The order is ascending criticality (Phase 2 plan §2.1). C-06 first sanitises the raw command into a physically realisable baseline so downstream rules never reason about implausible jumps; C-05 last guarantees override semantics — its substitution (brake + frozen steering) must win regardless of what upstream rules did. The order is fixed, deterministic, and exercised by `test_cage_node.py`.

**Q2. The spec admits a "known approximation": C-06 bounds the action *entering* the chain, but C-01..C-04 can introduce a step that violates the rate bound on the *emitted* action. Isn't that a hole in SR-006?**
It is a real, declared F2 approximation. Its consequence is bounded (only the last firing rule's correction can exceed the per-cycle delta, and only by that correction's magnitude), and the candidate fixes are named — a terminal second C-06 pass or per-rule rate-budgeting — gated on Phase 4 logs that quantify whether it occurs in practice. Declaring it is more defensible than silently assuming the emitted action is smooth.

**Q3. The cage is specified at 20 Hz (50 ms) but the RL environment runs at 10 Hz — which is the real cadence, and does the mismatch invalidate the per-cycle deltas?**
This is a known open point (also flagged in `docs/09`). C-06's per-cycle deltas are interpreted per environment step and are provisional `[M-5 + F3 prototype]`; they will be recalibrated against the policy's real action distribution, and if cadence matters `control_dt` is aligned to the cage cycle or the deltas rescaled. Because the cage class and `cage.yaml` are identical in training and deployment (D-34), whatever cadence is chosen there is no train/deploy divergence.

**Q4. Monitoring mode passes the unsafe raw action straight to `/safe_action` — isn't running an unsafe controller on the platform reckless?**
Monitoring mode is a *diagnostic* for the causal enforcement-vs-monitoring contrast and for offline replay; in simulation it is free, and on hardware it is used only inside the bounded, supervised frontier study where the no-cage counterfactual *is* the measurement (D-35). The active mode is recorded in every run's `metadata.json`, so no result is ever ambiguous about which was in force.

**Q5. The cage is "pure-Python, importable without ROS2" yet deployed as a ROS2 node — how do you know the node behaves like the tested class?**
The ROS2 wrapper (`src/safety_cage`) imports the very `cage` package the unit-test suite exercises; the rules and `cage.yaml` are shared, not reimplemented. The residual risk lives in the thin wrapper (topic plumbing), which is integration-tested — not in the rule logic. The project rule is explicit that typecheck / pytest ≠ feature works for ROS2, which is why the deployment claim rests on the live Gazebo executor, not on unit tests alone.

**Q6. `cage.yaml` is at 0.5.1 — how do you guarantee an older config doesn't silently change behaviour as the schema evolves?**
By the backward-compatibility discipline: new features must default inert for older YAMLs (precedent 0.4.0→0.5.0), and bumping `compatible_sr_spec_version` requires updating `_ACCEPTED_SR_SPEC_VERSIONS` or load raises `IncompatibleCageConfigError`. Every run records the `cage.yaml` hash, binding each result to its exact parameter set. Version 0.5.1 specifically fixed the oscillation-window reset bug across ROS launches — a concrete instance of this discipline.

--->

## Change log

See `docs/CHANGELOG.md`.
