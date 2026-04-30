# Cage Specification

**Status:** Living document — Phase 2 deliverable
**Last update:** [date]
**Approved at Gate:** G2 (pending)

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
```
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
```
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
```
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
```
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
1. Compound state: `abs(theta) > theta_warning AND abs(d) > d_warning` for more than `Δt_max` consecutive seconds.
2. Stale state: timestamp of last `/state_obs` older than `staleness_max`.
3. Invalid state field: any field outside its plausible range.
4. Missing state: no `/state_obs` received for `N_missing_max` consecutive cycles.
5. External stop: `/external_stop` signal received.

**On activation:**
- Replace throttle command with a deceleration target producing at least `a_min`.
- Freeze steering at its value at the instant of transition.
- Publish emergency signal on `/cage_status`.

**On deactivation:** only via explicit reset signal AND underlying condition cleared. This prevents oscillatory entry/exit.

**Parameters.**
- `theta_warning = 0.35 rad (20 deg)`.
- `d_warning = 0.12 m`.
- `delta_t_max = 0.2 s`.
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
```
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

The rules are evaluated in a fixed deterministic order at every control cycle:

1. **C-05 first.** If emergency mode activates, all subsequent rules are short-circuited for this cycle.
2. **C-01 and C-02 in parallel.** They operate on the same command component (steering) but with different criteria; their corrections combine additively.
3. **C-03.** May further bias the steering correction. If both C-01 and C-03 fire, the larger-magnitude correction wins (worst-case envelope).
4. **C-04.** Operates on throttle only. Independent.
5. **C-06 last.** Applied to the result of all upstream rules to ensure the final command satisfies the smoothness bound regardless.

This order is encoded in `cage/cage_node.py` and exercised by dedicated unit tests in `cage/tests/test_evaluation_order.py`.

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

Each rule has a dedicated test file under `cage/tests/`:
- `test_c01_lane_boundary.py`
- `test_c02_heading_limit.py`
- `test_c03_ttlc.py`
- `test_c04_speed_ceiling.py`
- `test_c05_emergency.py`
- `test_c06_rate_limiter.py`

Each test file covers: the trigger condition, the correction logic, the hysteresis behaviour where applicable, the boundary cases. The full suite is run before any commit to `main` and before any Gate review.

In addition, `test_evaluation_order.py` covers the interaction between rules.

## Change log

See `docs/08_change_log.md`.
