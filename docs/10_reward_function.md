# Reward Function Design — PPO Reward Function (CobraFlex / F3)

| Field | Value |
| --- | --- |
| Artifact | Output of days **D38–D39** (Phase 3, Week 8) — see `docs/.phases/Fase 3/fase_3_detallada.md` §4 (local plan) |
| Weights version | **v1.2** (forward-driver v1.1 + raw-smoothness v1.2; provisional, subject to experimental tuning) |
| Phase / Gate | F3 (PPO training), after G2 — **reused unchanged by the track-'E' camera training** (GE3 train / GE4 eval, the system of record): the reward scores the **ground-truth** state regardless of what the policy observes (docs/11 §3.4) |
| Author | Samuel Sanchez |
| Date | 2026-05-29 |
| Status | CONFIRMED — implemented in `cobraflex_rl/rewards.py`; tests in `policy/tests/test_rewards.py` |
| Normative spec | Training Specification §7.2.3. **This document is supporting rationale**: on any numeric discrepancy, §7.2.3 prevails. |
| Sibling document | `docs/09_environment_design.md` (obs/action/wrapper) |
| Spanish working copy | `docs/.phases/Fase 3/reward_function_design.md` (local, gitignored) |

> Purpose: explain the reward function — its form, components, weights and the
> rationale for each decision — at the level the committee may ask about.
> Includes a bank of defense questions.

> **Track framing (current state).** This reward was authored for F3 but is
> **observation-agnostic** (it scores the ground-truth state + the raw policy delta,
> §10), so the **same v1.2 reward is the verdict-of-record reward of track 'E'** — the
> primary system, whose GE4-V2 camera campaign (297k E-main, G4 closed 02.07.2026) ran on
> it unchanged. The F-track (state-vector baseline) is **archived / frozen**; it shares this
> reward. The one place the reward is *extended* is the **2-D action posterior work** (D-50),
> which adds a longitudinal-smoothness + anti-stall pair — documented in §10.2, inert by
> default so the frozen 1-D returns stay bit-identical.

---

## 1. Formula

In one control cycle, the reward is a linear sum of four terms minus a
termination penalty:

```text
r = w_fwd · max(progress, 0)
  − w_ey  · |ey|
  − w_eps · |epsi|
  − w_ds  · |Δsteer|
  − w_term · [terminated_off_road]
```

where `progress` is the **normalised centerline advance** this cycle (≈1.0 at
cruise; the env unwraps the closed-loop arc-length reset and divides by the
nominal per-step advance), `Δsteer = raw_steer − previous_raw_steer` (the **raw
policy** command, pre-cage — v1.2, see §5), and `[terminated_off_road]` is 1 only
if the episode ends by leaving the **road** (not by a C-05 emergency — see §7.2.4
/ ED-8). The exact implementation is in `cobraflex_rl/rewards.py::compute_reward`.

`progress` enters as `max(progress, 0)` (see §6). `ey` and `epsi` are taken from
the resulting state, and the smoothness term from the **raw** policy action; all
other terms reflect the **safe** (post-cage) outcome (D-34, §5).

> **Revision (F3 first run, v1.1).** The forward term was originally
> `w_fwd · speed`. Because speed is fixed (cage-controlled cruise), that term was
> a near-constant ≈0.2 that did not discriminate the policy's behaviour, so the
> return barely depended on the actions (`explained_variance ≈ 0`, flat
> learning). Rewarding **progress along the centerline** instead makes the return
> reward surviving and advancing (completing curves/laps) and keeps each on-track
> step net-positive, so ending early via the penalty-free C-05 emergency is never
> preferable to continuing. Weights are unchanged (v1.0); only the forward
> driver changed. See `docs/09_environment_design.md` ED-9.

---

## 2. Components

| Term | Sign | What it incentivises / penalises | Magnitude unit |
| --- | --- | --- | --- |
| `w_fwd · progress` | + | Advancing along the centerline (surviving + completing laps); avoids the degenerate policy that stalls to dodge penalties | normalised (≈1.0/step at cruise) |
| `w_ey · [ey]` | − | Lateral deviation from the lane centre (primary objective) | m |
| `w_eps · [epsi]` | − | Heading error w.r.t. the lane tangent | rad |
| `w_ds · [Δsteer]` | − | Abrupt **raw** steering changes (actuation smoothness; pre-cage, v1.2 — §5) | [-1,1] |
| `w_term · [done]` | − | Leaving the **road** (off-road failure only; C-05 emergency is penalty-free) | — |

Each term is **interpretable and isolable**, which eases the Chapter 8 ablation
analysis and the unit tests (§7).

---

## 3. v1.0 weights and rationale

| Parameter | Value | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Scale reference; with the v1.1 progress driver it contributes ≈+1.0/cycle at cruise (was +0.2 under the old `speed` driver) |
| `w_ey` (lateral_error) | 2.5 | **Primary penalty.** A 0.1 m offset costs 0.25 → the agent prioritises centring; still small vs the +1.0 progress, so an on-track step stays net-positive |
| `w_eps` (heading_error) | 0.75 | Secondary penalty; heading is a means to control `ey`, not an end |
| `w_ds` (steer_delta) | 0.20 | Smooths without choking correction. v1.2: applied to the **raw** policy delta (pre-cage) and raised 0.10→0.20, because the old post-cage term was toothless — C-06 absorbed the raw bang-bang for free (§5, §8) |
| `w_term` (termination) | 25.0 | **Deliberately high**: applied only on off-road failure (not C-05). Makes staying on the road dominate over optimising speed |

**Priority hierarchy encoded in the weights:**
`staying on road (25) ≫ progress (1.0 · progress) ≳ lateral centring (2.5·|ey|) > heading (0.75) > smoothness (0.20, on raw Δ)`.
Under v1.1 the forward term (≈1.0/step) is comparable to the per-step penalties,
so every on-track step is net-positive — the agent is pulled toward *continuing*,
not toward triggering the penalty-free emergency to cut losses.

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
the raw action the policy requested — **with one deliberate exception, the
smoothness term `w_ds·|Δsteer|` (v1.2)**:

- Cage interventions are **not penalised explicitly**. They are part of the
  environment dynamics from the agent's viewpoint.
- The penalty is **implicit**: if the policy drives the system into a state from
  which the cage can only recover with a strong correction (or with C-05), that
  state has high `|ey|`/`|epsi|` — penalised — and, in the worst case, terminates
  (−25) or yields no progress (emergency stop → `speed≈0` → no `w_fwd` term).

This avoids double punishment (penalising the intervention *and* the bad state)
and lets the policy learn to **not need** the cage, rather than to fear it.

**The smoothness exception (v1.2).** The F3 first-cycle evaluation showed the
policy exploiting exactly this "reward on safe action" rule against the smoothness
term: because the rate-limiter **C-06** clamps the steering *change* per cycle
(`delta_max = 0.15`), a raw bang-bang command (sign-flip 46% of steps, ±1
saturation 27%, mean |Δraw| ≈ 0.54) produces a post-cage signal that is smooth
*regardless* of how jerky the raw command was. Measuring `Δsteer` on the post-cage
action therefore made the term **toothless** — the policy paid nothing for driving
C-06 to its limit ~89% of steps (§7.5.2 / §8). The smoothness term exists to shape
the *policy's own* actuation, so it is the one term computed on the **raw** policy
delta (and weighted up 0.10→0.20). This is *not* punishing the cage: the cage's
corrective action is still never penalised — what is penalised is the policy's own
raw jerk, which the cage merely happens to mask. The rationale for the term then
holds: the policy learns native smoothness instead of outsourcing it to C-06.

**Confirmed (seed-2024/200k, reward v1.2).** The definitive run verifies it: the policy now
emits a smooth raw command (sign-flips **1.1%** of steps, **0%** ±1 saturation, mean
|Δraw| ≈ **0.030** — well below C-06's `delta_max = 0.15`), so `raw ≡ safe` at all
4 400 steps and **the cage fires on 0%** (zero interventions) in the nominal evaluation (vs
~89% under v1.0). The smoothness term achieved its purpose; the cage becomes a latent safeguard
in nominal cruising (§7.5.2), its protective value reserved for the edge/perturbed
scenarios of Ch.8.

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

- centred + cruise → `r = w_fwd · progress`;
- `|ey|`, `|epsi|`, `|Δsteer|` penalised with the correct weight and sign;
- termination penalty = exactly `w_term`;
- `progress < 0` → no forward reward (clamp);
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
<!--
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
**The one exception is the smoothness term `w_ds·|Δsteer|` (v1.2)**: it is
computed on the *raw* policy delta, because its purpose is to shape the policy's
own actuation, and C-06 masks raw bang-bang into a near-identical post-cage signal
— so a post-cage smoothness penalty never bites (see §5, §8 and §7.5.2). The
state-affecting terms (ey, epsi, progress, termination) stay on the safe outcome.

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
--->
## 10. Track E and the 2-D posterior — what carries over, what extends

### 10.1 Track E (camera, verdict of record) — reward unchanged (D-41 / D-43)

The end-to-end front-camera variant (track 'E', `docs/09`) leaves this reward
**unchanged**. The reward is a function of the resulting **ground-truth state**
(`ey`, `epsi`, `progress`) and the **raw policy steering delta** — none of which
depend on the observation modality. The camera changes what the *policy sees*, not
what the *environment measures* to score it. The reward's `ey/epsi/progress` come from the
simulator's **ground truth** — a training-time signal available in sim exactly as in F3,
and independent of whether the *cage* uses ground truth (F-track, archived) or its own CV
estimate (track 'E', D-43). There is **no reward at evaluation**: the trained policy drives
from the camera alone. Consequently the §1 formula, the §3 weights and the §7 unit tests all
carry over, and **no new reward term is introduced for the 1-D camera verdict**. This is
confirmed by the outcome: the GE4-V2 297k E-main trained on this exact v1.2 reward and drives
the lane cleanly (nominal |ey| 10.9 mm, beating the CV baseline; `docs/11` §8.2). *(No
camera-specific reward pathology surfaced — the v2.x contingency anticipated at E-design was
not needed.)*

### 10.2 The 2-D action posterior — two added terms (D-50 / D-56)

The **only** extension of this reward is for the **2-D action (steering + throttle)**
posterior work (D-50, `docs/09` §3.2) — deferred out of the frozen Gazebo verdict by D-49
and taken up on the Isaac track. Because the policy now commands throttle, the reward gains
a **longitudinal** mirror of the existing terms, both **weight-defaulted to leave the 1-D
returns bit-identical**:

| Term | Weight (2-D) | Rationale |
| --- | --- | --- |
| `throttle_delta` (raw policy throttle delta) | 0.10 | Longitudinal twin of the v1.2 raw `steer_delta` (§10 above): C-06 rate-limits throttle too, so a post-cage penalty would be toothless — measuring the raw delta makes the policy pay for its own jerk |
| `stall_penalty` (below `stall_progress_min = 0.25`) | 0.5 | **The 2-D-only failure mode:** with speed authority the policy can converge to a degenerate "park" optimum (throttle → 0, collect the survival/centring reward without moving). The penalty makes standing still unprofitable, so SR-009's liveness sub-mode is well-posed (D-56) |

The `stall_penalty` is the knowledge worth preserving from the 2-D pilots: the **first**
Isaac 2-D run's `ep_rew_mean` peaked then decayed into a *crawl-and-die* regime as the
policy over-annealed — an exploration collapse fixed by `ent_coef 0.01` (D-52), while
`stall_penalty` removes the standing-still attractor the added speed dimension created.
Neither exists on the 1-D verdict reward. A policy trained with these terms is a **new
posterior baseline**, never a re-run of the 297k E-main.

---

## Version log

- **weights v1.0 (2026-05-29):** first freeze, consistent with §7.2.3 and the
  reward-on-safe-action of the TS-01 wiring (D-34). Verified by
  `policy/tests/test_rewards.py`.
- **forward-driver v1.1 (2026-06-01):** after the F3 first run, the forward term
  changed from `w_fwd·speed` to `w_fwd·max(progress, 0)` (normalised centerline
  advance) — see the §1 revision note and `docs/CHANGELOG.md` (F3 learning fix).
  **Weights are unchanged (v1.0)**; only the forward driver changed. Re-verified
  by the updated `policy/tests/test_rewards.py`.
- **smoothness-term v1.2 (2026-06-02):** after the F3 definitive evaluation
  (§7.5.2) revealed the policy exploiting the post-cage smoothness term (raw
  bang-bang absorbed for free by C-06), the `w_ds·|Δsteer|` term was changed to
  measure the **raw** policy steering delta (pre-cage) and the weight raised
  `0.10 → 0.20`. Deliberate, documented exception to the reward-on-safe-action
  convention, for this term only (§5, §7.2.5). Implemented in
  `gazebo_lane_env.step` + `rewards.py`; re-verified by
  `policy/tests/test_rewards.py`. Effect on native RL smoothness **pending a new
  training cycle** (Ubuntu+Jazzy host) and the Ch.8 sensitivity analysis; weights
  remain `[provisional, M-P4]`.
- **track E note (2026-06-09):** added §10 — the reward is **unchanged** for the
  end-to-end camera variant (D-41/D-43); it is observation-agnostic (computed on
  ground-truth state + progress + raw steering delta, a sim training signal). No
  formula/weight change.
- **current-state framing (2026-07-07):** added the track-framing note (this v1.2
  reward is the **verdict-of-record** reward of track 'E' — the GE4-V2 297k E-main ran on
  it unchanged; the F-track that shares it is **archived/frozen**). Split §10 into §10.1
  (1-D camera verdict — reward unchanged, now *confirmed* by the GE4-V2 outcome) and
  **§10.2 — the 2-D action posterior** (D-50): the two added longitudinal terms
  `throttle_delta` (0.10, raw) and `stall_penalty` (0.5 below `stall_progress_min = 0.25`,
  D-56), both inert-by-default so the 1-D returns stay bit-identical, with the exploration-
  collapse / crawl-and-die obstacle (fixed by `ent_coef 0.01`, D-52 + the stall penalty)
  recorded so the knowledge is not lost. No 1-D formula/weight change.
