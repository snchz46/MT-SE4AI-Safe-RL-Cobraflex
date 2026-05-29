# Reward Function Design — PPO Reward Function (CobraFlex / F3)

| Field | Value |
| --- | --- |
| Artifact | Output of days **D38–D39** (Phase 3, Week 8) — see `docs/.phases/Fase 3/fase_3_detallada.md` §4 (local plan) |
| Weights version | **v1.0** (provisional, subject to experimental tuning) |
| Phase / Gate | F3 (PPO training), after G2 |
| Author | Samuel Sanchez |
| Date | 2026-05-29 |
| Status | CONFIRMED — implemented in `cobraflex_rl/rewards.py`; tests in `policy/tests/test_rewards.py` |
| Normative spec | Training Specification §7.2.3. **This document is supporting rationale**: on any numeric discrepancy, §7.2.3 prevails. |
| Sibling document | `docs/09_environment_design.md` (obs/action/wrapper) |
| Spanish working copy | `docs/.phases/Fase 3/reward_function_design.md` (local, gitignored) |

> Purpose: explain the reward function — its form, components, weights and the
> rationale for each decision — at the level the committee may ask about.
> Includes a bank of defense questions.

---

## 1. Formula

In one control cycle, the reward is a linear sum of four terms minus a
termination penalty:

```text
r = w_fwd · speed
  − w_ey  · |ey|
  − w_eps · |epsi|
  − w_ds  · |Δsteer|
  − w_term · [terminated]
```

where `Δsteer = applied_steer − previous_applied_steer` and `[terminated]` is 1
if the episode ends by leaving the road. The exact implementation is in
`cobraflex_rl/rewards.py::compute_reward`.

`speed` enters as `max(speed, 0)` (see §6). `ey`, `epsi` and `steer` are taken
from the **safe** (post-cage) action and the resulting state (D-34, §5).

---

## 2. Components

| Term | Sign | What it incentivises / penalises | Magnitude unit |
| --- | --- | --- | --- |
| `w_fwd · speed` | + | Moving forward; avoids the degenerate policy that stays still to dodge penalties | m/s |
| `w_ey · |ey|` | − | Lateral deviation from the lane centre (primary objective) | m |
| `w_eps · |epsi|` | − | Heading error w.r.t. the lane tangent | rad |
| `w_ds · |Δsteer|` | − | Abrupt steering changes (actuation smoothness) | [-1,1] |
| `w_term · [done]` | − | Leaving the road (failure event) | — |

Each term is **interpretable and isolable**, which eases the Chapter 8 ablation
analysis and the unit tests (§7).

---

## 3. v1.0 weights and rationale

| Parameter | Value | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Scale reference; at cruise (0.2 m/s) it contributes +0.2/cycle |
| `w_ey` (lateral_error) | 2.5 | **Primary penalty.** Dominates heading: a 0.1 m offset costs 0.25, more than the per-cycle progress → the agent prioritises centring |
| `w_eps` (heading_error) | 0.75 | Secondary penalty; heading is a means to control `ey`, not an end |
| `w_ds` (steer_delta) | 0.10 | Small; smooths without choking the ability to correct |
| `w_term` (termination) | 25.0 | **Deliberately high**: equals ~125 cycles of cruise progress. Makes staying on the road dominate over optimising speed |

**Priority hierarchy encoded in the weights:**
`staying on road (25) ≫ lateral centring (2.5) > heading (0.75) > smoothness (0.10) > progress (1.0 · speed)`.

The weights are marked `[provisional, M-P1..M-P4]`: the Chapter 8 sensitivity
analysis will confirm they do not produce degeneration before they are frozen.

---

## 4. Why a deliberately simple design

A linear sum of few terms was chosen over an elaborate reward (curvature terms,
explicit heading-oscillation penalty, cage-distance shaping…). Reasons:

1. RL lane-following practice shows that complex rewards rarely improve base
   behaviour and **complicate ablation analysis** (which term caused what?).
2. A simple reward is **auditable and testable** term by term (see §7), which
   fits the project's traceability philosophy.
3. Hard safety **is not delegated to the reward**: the cage (C-01..C-06)
   guarantees it. The reward only models *driving quality*, not *safety*. This
   separation of concerns is central to the thesis.

---

## 5. Interaction with the cage (D-34)

The reward is computed on the **safe** action (the one actually actuated), not on
the raw action the policy requested:

- Cage interventions are **not penalised explicitly**. They are part of the
  environment dynamics from the agent's viewpoint.
- The penalty is **implicit**: if the policy drives the system into a state from
  which the cage can only recover with a strong correction (or with C-05), that
  state has high `|ey|`/`|epsi|` — penalised — and, in the worst case, terminates
  (−25) or yields no progress (emergency stop → `speed≈0` → no `w_fwd` term).

This avoids double punishment (penalising the intervention *and* the bad state)
and lets the policy learn to **not need** the cage, rather than to fear it.

---

## 6. `forward_progress` with `max(speed, 0)`

The forward term uses `max(speed, 0)`: a negative speed (reverse, or odometry
noise) yields **no** forward reward, but neither does it reward reversing.
Without this clamp a policy could exploit spurious negative speeds. (In training
the speed is fixed ≥ 0, but the clamp guards against artifacts and a future
throttle action.)

---

## 7. Verification

**D38 (qualitative calibration vs PD).** Run the F2 PD controller inside the
wrapper and verify its cumulative reward is high and coherent. If the PD — which
we know is competent — scores poorly, the reward is mis-calibrated. *(This check
requires Gazebo; it is evidenced on the Ubuntu+Jazzy host.)*

**D39 (unit tests on synthetic states).** `policy/tests/test_rewards.py`
(10 tests, runnable without ROS) pins the arithmetic of each term:

- centred + cruise → `r = w_fwd · speed`;
- `|ey|`, `|epsi|`, `|Δsteer|` penalised with the correct weight and sign;
- termination penalty = exactly `w_term`;
- `speed < 0` → no forward reward (clamp);
- linear composition of terms;
- `w_ey` dominates `w_eps` at equal error;
- the `reward` block in `train_ppo.yaml` is complete with positive weights.

---

## 8. Degeneration risk and mitigation

The classic risk: a policy that **maximises `forward_progress` ignoring `ey`**
(runs fast off-centre). Mitigations encoded:

- `w_ey` (2.5) > the per-cycle progress gain at cruise (0.2), so deviating never
  pays off for the extra progress.
- `w_term` (25.0) makes leaving the road catastrophic.
- Speed is **fixed**, so the policy cannot "buy" reward by accelerating at the
  cost of lateral control.

Empirical confirmation that there is no degeneration (nor reward hacking) is the
subject of the **Chapter 8** sensitivity/ablation analysis; until then the
weights remain `[provisional]`.

---

## 9. Anticipated defense questions

**Q1. How were the weights chosen? Aren't they arbitrary?**
They were chosen by their *relative hierarchy*, not by a fine absolute value:
staying on the road ≫ centring > heading > smoothness. The concrete values are
provisional (`M-P1..M-P4`) and validated by the Ch. 8 sensitivity analysis. The
key relation (`w_ey` > progress/cycle) is justified numerically above.

**Q2. Why is the termination penalty so high (25)?**
To impose the "do not leave the road" priority over "go fast". 25 equals ~125
cycles of cruise progress: no episode can offset a road departure by
accumulating speed. It encodes that the task's safety weighs more than its
efficiency.

**Q3. Why is the reward computed on the safe action and not the raw one?**
Because what affects the world state — and therefore what the agent must learn to
anticipate — is the action *actually actuated* after the cage (D-34). Rewarding
the raw action would teach the policy to optimise something that does not happen.

**Q4. Why not penalise cage interventions explicitly?**
To avoid double punishment. The bad state that triggers the intervention is
already penalised via `|ey|`/`|epsi|`/termination. Penalising the intervention as
well would bias the policy to "fear" the cage instead of driving well. The cage
is environment dynamics, not a reward signal.

**Q5. How do you avoid reward hacking?**
Three barriers: (i) fixed speed removes the "run to score" route; (ii) `w_ey`
dominates the per-cycle progress; (iii) safety is guaranteed by the cage, not the
reward, so a reward exploit cannot produce unsafe behaviour. The absence of
degeneration is verified empirically in Ch. 8.

**Q6. Why a linear reward and not more sophisticated shaping?**
For auditability and clean ablation analysis. Complexity rarely improves base
lane-following and makes attributing effects harder. The "reward = quality, cage
= safety" separation stays sharp.

---

## Version log

- **weights v1.0 (2026-05-29):** first freeze, consistent with §7.2.3 and the
  reward-on-safe-action of the TS-01 wiring (D-34). Verified by
  `policy/tests/test_rewards.py`.
