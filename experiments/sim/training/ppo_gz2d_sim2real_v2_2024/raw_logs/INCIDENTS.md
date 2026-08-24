# Incident log — ppo_gz2d_sim2real_v2_2024

Kept alongside the run so its anomalies are part of its own evidence rather than
reconstructed from a chat log afterwards.

## I-1 (launch, 20.08 11:44) — launch script died instantly under `set -u`

**Symptom.** First launch produced no processes and a 77-byte log.
**Cause.** `set -u` in `raw_logs/launch.sh`; `/opt/ros/jazzy/setup.bash` dereferences
`AMENT_TRACE_SETUP_FILES` while unset and exits.
**Impact.** None — caught before the run started. Second launch at 11:46 succeeded.
**Fix.** `set -u` removed, with the reason recorded in the script so it is not re-added.

## I-2 (20.08, ~11:00) — four orphaned `gz sim` processes from smoke tests

**Symptom.** Load average 5.18 with no training running; four `gz sim` at ~65 % of a
core each, 13–38 minutes old.
**Cause.** Smoke-test launches without `shutdown_on_train_exit`; Gazebo does not die
on SIGINT within the launch system's 5 s escalation window.
**Impact.** None on this run (reaped before launch), but it is a plausible contributor
to the machine crash that ended the 19.08 fine-tune after ~8 h, which was never
diagnosed. The v2 launch sets `shutdown_on_train_exit:=true`; the monitor alarms if a
second `gz sim` ever appears.

## I-3 (21.08, ~01:30, timestep ~425k) — sustained reward decline with KL over target

**Symptom.** `ep_rew_mean` peaked at **827** in the 325k block and fell for three
consecutive blocks: 827 -> 766 -> 599 -> **462**. `ep_len_mean` tracks it, 739 -> 429.
`approx_kl` in the last rollouts reads 0.775 / 1.680 / 1.170 / 0.759 against
`target_kl` 0.5, where the rest of the run held 0.3-0.4.

**Not the critic.** `explained_variance` *rises* across the same blocks (0.44 -> 0.62
-> 0.68) and `value_loss` stays in its usual band. This is not the
`ppo_newcam_complex_b_2024_1M` failure ("value_loss tiny all run — exploration
collapse"); that signature points the other way.

**Cause — a config decision, not a defect.** The log reads `learning_rate 0.000259`.
At 425k steps the trunk was at **1.725e-4** (plain `linear` over 1M); this run is at
**2.592e-4**, **1.5x higher**, because `lr_schedule: linear_floor` was stretched over
2.5M *and* given a 0.2 floor. At 425k the trunk had spent 42 % of its decay; v2 has
spent 14 %. A learning rate that high against an action `std` already down to 0.061
produces exactly this: large policy steps in a narrow distribution, KL past its
trust region, and a policy that degrades between updates.

The floor was added for a real reason — the 19.08 fine-tune spent its last 100k steps
at an inert LR while its reward was still climbing — but it was sized against that
failure without checking what it implies at the *middle* of a 2.5M run.

**Decision: no intervention at 425k.** Three reasons.
1. This run already recovered from one dip (765 @ 175k -> 635 @ 225k -> **805 @ 364k**,
   a new high), so a decline alone does not establish a trend.
2. The checkpoint that matters is chosen by transfer, not reward (D-66/D-72), and the
   high-reward region is already on disk (325k-350k, every 25k with its VecNormalize).
   A degrading tail does not destroy what has been earned.
3. Editing a running experiment's config would break both its reproducibility and the
   contract test that pins it to four variables.

**Criterion for acting, fixed in advance so the decision is not made by hindsight:**
if by **500k** `ep_rew_mean` has not recovered above **700** *and* `approx_kl` is still
routinely over 0.5, the decline is sustained rather than a fluctuation. The remedy is
then to resume from the best checkpoint with a corrected schedule (plain `linear` over
the remaining budget, or a floor sized to the *remaining* steps rather than the total),
which is a decision for the run's owner, not one to take silently mid-flight.

## I-4 (21.08, ~03:40) — the checkpoint selector's ranking metric was wrong, found by running it

**Symptom.** Scoring the run's first 19 checkpoints put three entries in the top five
with "retention" of **304 %, 231 % and 184 %** — a figure that cannot exceed 100 % by
its own definition — and ranked the **25k** checkpoint first.

**Cause.** `retention_vs_canonical` divides the degraded arm's swing by the canonical
arm's. Both come from the *same* checkpoint here, so when the canonical arm collapses
(0.061 at 475k, 0.006 at 225k) the ratio explodes and promotes the checkpoints that
respond *least* on the render they trained on. That logic is sound in
`sim2real_probe`, where the sim arm calibrates a *working* policy against a *real*
recording; it is not sound for a degraded-vs-clean comparison within one checkpoint.

**Fix.** `rank_key` now orders by **absolute swing on the deployment arm**, behind a
`MIN_CANONICAL_SWING = 0.15` floor and the sign guard. Retention is still reported —
the drop from canonical to deployment is informative — but no longer orders the table.
Four new tests pin the artefact, including the 304 % case verbatim.

**What the fix does NOT solve, stated because it bounds every number this tool
produces.** The floor removes collapsed control arms; it does not remove *noisy* ones.
The 25k checkpoint still ranks first, with a canonical swing of 0.747 — an almost
untrained policy whose steering varies a great deal with any input. `r_squared` was
checked as a discriminator and **does not separate them**: 25k reads 0.282 on the
deployment arm against 0.306 at 100k and 0.368 at 150k, and every checkpoint sits
between 0.03 and 0.37. The 420-frame probe set carries only four distinct `ey` values
and was recorded for a different purpose, so it is a weak regression design for
measuring the *strength* of a response.

The honest consequence: **this tool ranks the bias structure, not the response
strength.** `bias_over_swing` and `right_fraction` are ratios and shares, robust to
that noise; absolute swing is not. Choosing a checkpoint needs the SC-NOM-01 drive and
the real probe, which is what the tool now prints in its own output rather than
leaving to the reader.

**Substantive result, independent of the ranking defect.** On the deployment arm the
run's checkpoints read `bias_over_swing` **0.07-1.10** and right-turn share
**29-72 %**, against **1.44-1.94** and **6-14 %** for every checkpoint of the 19.08
fine-tune, and **12.9-19.2** and **0.8 %** for the trunk as deployed on 18.08. Those
two statistics are exactly the ones D-71 identified as the failure, and they are
structural rather than magnitude-based, so the noise above does not reach them. The
handedness term is fixed.

## I-5 (21.08, ~06:00, timestep ~560k) — the reward decline is the track's known shape, and the probe metric diverges from it

**Symptom.** The decline reported in I-3 did not stop where it appeared to. From the
**872 @ 330k** peak: 462 (400k), 437 (525k), **195 @ 560k** — a 78 % fall over 230k
steps, with `ep_len_mean` 739 -> 198 and cage activity rising (C-03 x8, emergencies
x2.5 in two hours). The plateau reported at 500k was a step in a continuing decline,
not a floor; that earlier reading was wrong.

**It is not the documented exploration collapse, and it is not novel.**
`ppo_newcam_complex_b_2024` on this same circuit peaked **822.9 @ ~297k** and decayed
to ~113 by 662k — it was stopped by hand and its **peak was rescued**, which is how
the 297k E-main checkpoint came to exist. Two independent runs, different algorithms
and hyperparameters, both peak near 300k on complex_b and lose 60-70 % over the next
250k. The mechanism differs though: that run's `value_loss` was 0.007-0.012 ("tiny all
run"), while this one holds 0.055-0.088 with `explained_variance` *rising* to 0.68.
Its critic was idle; this one is working. So the shared shape is more likely a property
of the circuit and the task than of either run's settings.

**The probe metric moves the other way, and that is the point of this run.**
Scored on the deployment arm as the reward fell:

    checkpoint   reward   bias/swing   right     r^2
    325k          ~870      0.35       45.7 %   0.164
    450k          ~537      0.07       62.9 %   0.260
    500k          ~418      0.21       70.7 %   0.324
    525k          ~437      0.25       80.7 %   0.353
    550k          ~239      0.20       72.1 %   0.406

`r^2` — the share of steering variance the lane explains — rises to the highest of the
run exactly as the reward reaches its lowest, and the canonical arm collapses in
parallel (0.160 -> 0.044). The policy is specialising into the hall photometry, which
is 75 % of its episodes, and away from the clean render, which is 25 %.

**The tension, stated rather than smoothed over.** It responds to the lane *better* and
*drives worse*: episodes fell 739 -> 244 steps and the cage intervenes more. An
open-loop probe on static frames measures response to lane position; driving also
requires that response to be stable, and a high gain can oscillate. This is the
concrete case the tool's own "SWING IS NOT DRIVING" warning exists for.

**Consequence for checkpoint selection.** The reward peak (300-350k) and the probe peak
(500-550k) are **different regions of the run**, and neither metric alone chooses
between them. The SC-NOM-01 nominal drive is no longer a formality in the selection
procedure — it is the discriminator. Not run yet: it needs a second Gazebo instance
competing with the training on a machine that has already crashed once undiagnosed
(I-2), so it waits for the run to finish.

**No intervention.** The run is still producing distinct, plausible candidates; every
peak is already on disk with its VecNormalize; and stopping early would forfeit the
remaining candidates without recovering anything.

## I-6 (21.08, 08:03, timestep 620,544) — THE RUN WAS KILLED BY THE OPERATOR, not by a fault

**Symptom.** `gazebo` exit **-9** (SIGKILL), `train_ppo` exit **-2**, with a traceback
inside `collect_rollouts` -> `env.step` — the trainer died because its simulator
vanished mid-rollout, not the other way round.

**Cause.** A single-scenario `run_campaign.py` invocation was started *beside* the
running training, to answer I-5's open question about which checkpoint drives. The
campaign reaps orphaned Gazebo servers at start-up with

    pkill -9 -f "gz sim.*cobraflex/share/cobraflex/worlds"

and a training's Gazebo runs the same world from the same install path, so the
pattern matched it. `GZ_PARTITION` isolates *topics*, not *processes*, and gave no
protection.

**This was avoidable and documented.** `_reap_orphan_gazebo`'s own docstring states
the assumption — "Campaign runs are strictly serial […] so after a run returns there
must be no gz server we still need" — and scopes the pattern "so an unrelated gz the
user started is untouched". The scoping protects a *foreign* Gazebo; a training on a
cobraflex world is precisely the case it does not cover. The surrounding code was
read; this function was not.

**Cost.** ~20,000 steps, from the 600k checkpoint to 620,544. The 24 checkpoints
already written are intact, with their VecNormalize files, so the run is resumable.

**A second error, chained.** The guard written to prevent recurrence used `pgrep -f`,
which matches any shell whose command-line *text* contains the pattern. It found
three — a health sampler, a monitor, and the checking command itself — and blocked
three campaign runs with nothing training. `reap_sim.sh` documents this exact trap,
and the 29.07 concurrency incident was misdiagnosed by it ("the matching process was
the checker itself"). The same defect was in the health sampler and the monitor
written for this run, which is why the monitor reported `ERROR SIGNATURE` instead of
`TRAINER GONE`: it saw itself and concluded the trainer was alive.

**Fixes.**
* `run_campaign.py` refuses to start while a trainer is alive (`_live_training_pids`,
  verified by `comm`, never by cmdline), with `--force-beside-training` as the
  explicit escape. Two tests, one of which pins that the reaper's pattern *does*
  match a training cmdline so the hazard cannot be quietly forgotten.
* Health sampler and monitor stopped. `health.csv` rows after 08:03 are annotated
  in-file as invalid — they recorded a bash wrapper's 1 MB RSS as the trainer's.

**What this does not excuse.** Two messages before starting the campaign, the risk of
running it concurrently was assessed as *resource contention* and dismissed on the
grounds that the machine sat at 8 % of 12 cores. That was the wrong resource to look
at: the hazard was a process-name pattern, not CPU.

## I-7 (23.08, 22:34) — a third orphaned Gazebo, alive for 2 d 14 h

The training's own `gz sim` survived `shutdown_on_train_exit`: the launch escalated
SIGINT to SIGTERM, logged `exit code -15`, and the ruby server was still running
2 days 14 hours later, from the 21.08 08:14 resume. Reaped by hand before the
post-run. Same pattern as I-2, and the third occurrence — `shutdown_on_train_exit`
reduces but does not eliminate it. Anything starting Gazebo on this host should
check `ps -eo comm= | grep -c ruby` first; `tools/reap_sim.sh` exists for it.

## I-8 (23.08, 22:40) — every nominal eval of this run measured the randomisation, not the policy

**Symptom.** The fail-closed D-43 preflight BLOCKED the 1.65M checkpoint: 35 of 300
centred rows with a material CV-vs-ground-truth disagreement, max **58 mm** against
a 50 mm threshold.

**Cause, and it is mine.** `eval_policy` forces `domain_randomization.enabled =
False` for evaluation — its comment explains exactly why ("a nominal eval episode
can draw a random degradation from the training envelope"). The two blocks added on
20.08, `geometric_randomization` and `mirror_augmentation`, were **not added to that
rule**. So every nominal drive of this run — the three on 21.08 and the four in the
post-run — ran with the mirror flipped on ~half its episodes and the camera mount
perturbed on all of them (pitch +/-1.5 deg, height +/-10 %, plus a 10 % chance of the
full M-6 lens). A +/-10 % height perturbation scales the estimator's `ey` by ~10 %
directly, which is where the 58 mm came from: the preflight was measuring the
perturbation I injected.

**Retracted.** The |ey| figures reported from those runs (9.9 / 11.1 / 13.4 /
14.2 mm) and the intervention-rate comparison drawn from them.

**Fix.** `eval_policy` now disables both blocks alongside `domain_randomization`,
with the semantic reason recorded rather than just the mechanism: a mirrored episode
on a perturbed camera is not the world the SC-* YAML describes. Two tests.

**Re-measured, randomisation off** (single 300-step episodes, so read the spread as
indicative rather than settled — the trunk's reference nominal is 4400 steps):

    checkpoint   |ey|      max      emergencies   interventions
    325k          9.6 mm   27.4 mm       0           35.0 %
    1500k        34.3 mm   48.5 mm       0            2.0 %
    1650k        19.1 mm   43.3 mm       0            3.0 %
    2000k        19.6 mm   55.6 mm       0            0.3 %

D-43 preflight now **PASSES** on 325k, 1650k and 2000k, max centred ey error
18-21 mm against the 50 mm threshold.

**The trade this exposes is real and is the checkpoint decision.** The reward-peak
checkpoint drives tightest on clean sim (9.6 mm, against the trunk's 8.6) but leans
on the cage for **35 %** of steps, almost all C-06. The late checkpoints are looser
(19-34 mm) and nearly cage-free (0.3-3 %). D-69 named the C-06 coupling to
`delta_max_steering_per_cycle` a physical-transfer risk (T2) precisely because it is
a per-cycle parameter with no guarantee of transferring, so for a deployment the
low-intervention checkpoints are the safer bet even though they look worse in sim.
