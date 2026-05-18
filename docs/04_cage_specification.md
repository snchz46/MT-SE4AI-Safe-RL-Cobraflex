# Cage Specification

**Status:** Living document — Phase 2 deliverable  
**Last update:** 18.05.2026  
**Approved at Gate:** G2 (pending)  
**Cage YAML version:** 0.3.0 (`cage/cage.yaml`).  

## Purpose

This document specifies the runtime safety cage as an explicitly designed engineering artefact. It defines the architecture, the rules, the parameters, the evaluation order, the operating modes, and the interface to the rest of the system.

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

**Implements.** SR-005, SR-007, SR-008.
**Mitigates.** H-04, H-06, H-07.
**Type.** Trigger-based (procedural safety).

**Triggers (any of these activates emergency mode):**

1. Compound state, low-energy: `abs(theta) > theta_warning AND abs(d) > d_warning` for more than `delta_t_max` consecutive seconds.
2. Compound state, high-energy: `abs(theta) > theta_warning AND abs(d) > d_warning AND v > v_warning` for more than `delta_t_max_fast` consecutive seconds. The high-energy variant shortens the persistence requirement because the kinematic margin at elevated speed is smaller.
3. Stale state: timestamp of last `/state_obs` older than `staleness_max`.
4. Invalid state field: any field outside its plausible range.
5. Missing state: no `/state_obs` received for `N_missing_max` consecutive cycles.
6. External stop: `/external_stop` signal received.
7. Joint-envelope assertion failure (see §Joint-envelope assertion below).

**Implementation status (cage YAML 0.4.0).** Triggers 1–6 are implemented in [cage/rules/c05_emergency.py](../cage/rules/c05_emergency.py); Triggers 1–4 and 6 are exercised by [test_c05_emergency.py](../cage/tests/test_c05_emergency.py) and Triggers 2 and 5 by [test_c05_triggers_extended.py](../cage/tests/test_c05_triggers_extended.py). Trigger 5 (missing state) is fed by the cage_node-level counter in [cage/cage_node.py](../cage/cage_node.py) (`_cycles_since_last_state`), verified by [test_cage_node_missing_state.py](../cage/tests/test_cage_node_missing_state.py). Trigger 7 (joint-envelope assertion) is **deferred**: it requires a per-rule `safe_envelope_predicate_holds(state, action) -> bool` method that does not yet exist on the rule contract. The sibling inter-cycle oscillation check described in the SR-010 section below is also deferred for the same reason (no per-rule signed-correction predicate yet).

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

Each rule has a dedicated test file under `cage/tests/`. Current status (cage YAML 0.4.0, 90 tests passing):

| File | Coverage |
|---|---|
| [test_c01_lane_boundary.py](../cage/tests/test_c01_lane_boundary.py) | Hysteresis, bounds, sign of correction, saturation, disable |
| [test_c02_heading_limit.py](../cage/tests/test_c02_heading_limit.py) | Same pattern on heading_error |
| [test_c03_ttlc.py](../cage/tests/test_c03_ttlc.py) | `compute_ttlc`, urgency ramp, predictive activation |
| [test_c04_speed_ceiling.py](../cage/tests/test_c04_speed_ceiling.py) | `v_max(κ)`, throttle reduction, curvature behaviour |
| [test_c05_emergency.py](../cage/tests/test_c05_emergency.py) | Triggers 1, 3, 4, 6; persistence; reset semantics; freeze steering |
| [test_c05_triggers_extended.py](../cage/tests/test_c05_triggers_extended.py) | Trigger 2 (high-energy); Trigger 5 (missing-state via ctx) |
| [test_c06_rate_limiter.py](../cage/tests/test_c06_rate_limiter.py) | Per-component clipping, boundary, disable |
| [test_cage_node.py](../cage/tests/test_cage_node.py) | Chain composition, modes, prev_action tracking, emergency override |
| [test_cage_node_missing_state.py](../cage/tests/test_cage_node_missing_state.py) | Missing-state counter, no-state-ever safe-stop |
| [test_cage_rules.py](../cage/tests/test_cage_rules.py) | YAML load + per-rule smoke tests |

The integration tests in `test_cage_node.py` exercise rule interaction (composition and override semantics); a dedicated `test_evaluation_order.py` covering rule-pair conflicts at the level of detail required for SR-010 will land alongside the joint-envelope assertion (Trigger 7 of C-05) when that work is taken up.

The full suite is run before any commit to `main` and before any Gate review.

## Change log

See `docs/CHANGELOG.md`.
