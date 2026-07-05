# Change Log

This document records every change made to the living documents under `docs/` and to `cage/cage.yaml`.

Each entry has the following structure:

```text
## [DD.MM.2026] — Short summary

**Document(s) affected:** ...  
**Phase:** F0 / F1 / ...  
**Gate context:** before/after Gate G?  
**Author:** Samuel Sanchez  

### Change

What was changed, where.

### Rationale

Why the change was made; which evidence motivated it.

### Impact

Which other artefacts are affected; what re-runs are required.

### Verification

Result of `tools/check_traceability.py` after the change.
```

---

## [05.07.2026] — v5 result (training record 227.8 but stall-inflated; nominal ≤0.62 + park exploit) → D-56: reward `stall_penalty`; v6 launched

**Document(s) affected:** docs/DECISIONS.md (new **D-56**); `src/cobraflex_rl/cobraflex_rl/rewards.py` (config-gated `stall_penalty`/`stall_progress_min`, default 0.0 bit-identical); `policy/tests/test_rewards.py` (+3, suite 506); Isaac configs (`stall_penalty: 0.5`, `stall_progress_min: 0.25` `[provisional]`). Runs: `ppo_isaac2d_v5_2024_1M/` (completed; loop record 227.8 @ 844k / ep_len 389) + `ppo_isaac2d_v6_2024_1M/` (launched 05.07 10:48). Evals: v5 final/775k/850k under `experiments/sim/eval_isaac/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..56)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

v5 (v4 + D-55 budgets) trained the healthiest curve of the loop (records to 844k, no
collapse, final without hard decay) — but nominal evals expose **stall inflation**: honest
0.62-lap drives mixed with 1747–2200-step idles at 0.005–0.03 m/s (the park mode avoids the
termination penalty and, with the widened blind budgets, the cage no longer executes a
stopped vehicle promptly — SR-009's M-P6 attractor, now measured twice). Champion by laps
remains **stage-1 final (0.63)**. Per D-53's pre-declared reward-rebalance lever → **D-56**:
per-step `stall_penalty` while normalised progress < `stall_progress_min` (0.25 ≈ 0.05 m/s;
slow-but-driving never charged; parking now strictly worse than driving-and-failing).
**v6 = v5 + stall_penalty** (single delta) launched.

### Verification

pytest — 506 passed (3 new pins: inert-by-default, fires-below-threshold,
never-while-driving). v6 confirmed stepping (t=2k: 27.3/46.9).

---

## [05.07.2026] — v4 result (fast-and-reckless, ≤0.31 laps) + D-55 addendum: blind-stretch budgets widened (Trigger 5/8) and config-gated supervisor override; v5 launched (v4 + budgets, single delta)

**Document(s) affected:** docs/DECISIONS.md (D-55 addendum); `cage/cage_isaac.yaml` (`n_missing_max_cycles` 5→13, `staleness_max_s` 0.5→1.3, `[provisional, Isaac]`); `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (new config-gated `cage.perception_min_invalid_cycles` — unset = Gazebo-tuned default 4, bit-identical); Isaac configs (+`perception_min_invalid_cycles: 12`). Runs: `ppo_isaac2d_v4_2024_1M/` (completed; peak 170.2 @ 410k; nominal ≤0.31 laps — fast-and-reckless optimum, 0.30–0.35 m/s killed at first-curve entry) and `ppo_isaac2d_v5_2024_1M/` (launched 05.07 02:53). Evals: v4 final/400k, stage-1-on-D55(+wide), CV wide-budget parity — all under `experiments/sim/eval_isaac/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..55)
**Gate context:** after Gate G4 (Gazebo paths bit-identical: env override inert unset; pytest 503)
**Author:** Samuel Sanchez

### Change

v4 (first training on the D-54/55 env) converged to a **fast-and-reckless optimum** — clean
tracking at 0.30–0.35 m/s but killed by C-05 at every first-curve entry (≤0.31 laps; final
model worse than its 410k peak). The remaining blocker for every controller is the ONE
Isaac-renderer blind stretch: the supervisor latches Trigger 8 after 4 invalid cycles and
the cage's missing-state budget (5) stops the run 0.4–0.5 s in. Budgets widened for Isaac
(supervisor 12 cycles via the new config-gated env key; cage Trigger 5/3 to 13 cycles/1.3 s
≈ ≤26 cm blind at cruise). Validation shows the widening cannot rescue estimator-consuming
controllers (CV drives blind into a real off-road; pre-fix stage-1 champion unchanged at
~0.64) — its purpose is the TRAINING equilibrium: an end-to-end CNN policy keeps its own
(raw-frame) perception through the stretch, and the cage no longer executes mid-line
exploration there. **v5 = v4 + these budgets** (single attributable delta).

### Rationale

Iteration discipline (session goal): v4 isolated the training-vs-env coupling; the budgets
are the last calibration-level lever. If v5 still caps below a lap, next is the deep
estimator/renderer investigation at the archived failing viewpoint.

### Verification

pytest — 503 passed (override inert by default). CV wide-budget probe + stage-1-on-wide
eval archived (JSONs). v5 confirmed stepping (t=2k: rew 23.3, ep_len 49.8).

---

## [04.07.2026] — D-54 + D-55: the ~0.63-lap wall root-caused to the ENVIRONMENT (Isaac yaw-authority ceiling + renderer-shifted CV over-read), calibrated and validated by CV-parity probes; v4 training launched on the fixed env

**Document(s) affected:** docs/DECISIONS.md (new **D-54**, **D-55**; stage-1/1b closure note in D-53); new `cage/cage_isaac.yaml` (theta_max 25°→40°, theta_warning 20°→35°, `[provisional, Isaac]` — canonical `cage/cage.yaml` untouched); `src/cobraflex_rl/config/train_isaac_2d{,_stage1}.yaml` (`cage.yaw_gain` 0.8→2.4, `cage.yaml_path`→cage_isaac); `tools/isaac_eval.py` (`--controller cv`, `--cv-speed`, `--cv-yaw-boost`, `--dump-frames` + per-step cage-estimate trace). Evidence: probe JSONs + frame dumps under `experiments/sim/eval_isaac/`; stage-1b record `experiments/sim/training/ppo_isaac2d_stage1b_2024_1M/` (interrupted @1.52M by rule).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..53)
**Gate context:** after Gate G4 (Gazebo cage + verdicts untouched)
**Author:** Samuel Sanchez

### Change

Stage 1b (+1M resume) plateaued below stage-1's band → stopped by rule at 1.52M; its best
ckpts eval at the same **~0.63-lap wall**. The discriminating control experiment followed:
the **non-learned CV reference controller** (4.85 laps on Gazebo complex_b) through the same
Isaac env. It died at the FIRST curve everywhere (45/42/306-step episodes) → **wall #1:
yaw-authority ceiling** (plant delivers ~18 % of commanded yaw; `yaw_gain 0.8` capped the
command below every curve's requirement) → **D-54**: `yaw_gain 2.4` (validated: k≥3 boost
lifts CV from 0.04 to 0.42–0.44 laps, |ey| 13–14 mm). The survivor kill — same fixed spot
(s≈8.4 m), speed- and friction-invariant, TRUE state mm-clean (ey −27 mm, epsi −6.4°) —
exposed **wall #2: the monocular estimator over-reads ~+19° persistently on curves on Isaac
pixels** (cv_epsi −0.30 rad at true +0.03; dumped death frames show the lane fleeing the
image at the U-turn exit) → **D-55**: `cage_isaac.yaml` with theta_max 40°. Beyond 40° is
futile (at 45° the kill is the supervisor's missing-state budget — correct blind-driving
stop). **Parity achieved (with documented residual):** CV probe reaches **0.971 laps with
zero emergencies** on one repeat; the borderline viewpoint stays a coin flip for the
fixed-line CV (~0.45 on others) — an RL policy can learn estimator-friendly lines, which
is operationally what CV-safe driving means. **v4 launched 04.07.2026 18:22**
(`ppo_isaac2d_v4_2024_1M`: stage-1 curriculum config + D-54 + D-55).

### Rationale

Iterations 1–3 falsified the training-side hypotheses (exploration, task-difficulty
curriculum) while the CV-parity experiment — the reference that had proven the whole loop
in Gazebo — isolated the environment itself. Fixing the env under a known-good controller
BEFORE more RL is the SE4AI way round; the residual perception defect is documented and
scoped (supervisor re-calibration = future work, required before any Isaac verdict).

### Impact

Isaac training/eval now run on a calibrated plant (3× yaw command headroom) and an
Isaac-calibrated cage variant; Gazebo artefacts bit-identical. `isaac_eval.py` gained the
CV-baseline mode + perception post-mortem tooling (ring-buffer frame dump + per-step
cage-estimate trace) — the Isaac counterpart of the Gazebo eval's failure-frame dump.
Champion expectation shifts: pre-D-54/55 RL numbers (≤0.63 laps) are NOT comparable with
post-fix runs.

### Verification

pytest — 503 passed (canonical cage untouched); probe campaign archived (13 JSONs + 2 frame
dumps); parity best-case 0.971 laps / 0 emergencias; v4 confirmed stepping on the calibrated
env (scene D-51 trio, visual-DR-only, ent 0.01, yaw 2.4, cage_isaac).

---

## [04.07.2026] — Stage-1 curriculum CONFIRMED: full 1M healthy (peak 223.4, no collapse), nominal 0.63 laps — champion so far; stage-1b (+1M resume) launched per the extend-if-short instruction

**Document(s) affected:** docs/DECISIONS.md (D-53 stage-1 RESULT addendum). Evidence: `experiments/sim/training/ppo_isaac2d_stage1_2024_1M/` (status completed, 1M) + `experiments/sim/eval_isaac/{cobraflex_ppo_isaac2d_stage1_2024_1M,ppo_isaac2d_stage1_2024_1M_725000_steps}_enforcement.json`; new run `experiments/sim/training/ppo_isaac2d_stage1b_2024_1M/`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50..53)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

Stage 1 (visual-DR-only, D-53) completed its full 1M **healthy**: `ep_rew_mean` 10 → peak
**223.4 @ 747k** (final band 150–190; at 53k it already tripled runs 1–2's level), std
annealed 0.73 → 0.034 **without collapse**, emergencies 0.1–1 %. **Nominal eval:** the FINAL
model is the overall champion — complex_b **0.46–0.63 laps** (618–888 steps), complex_d
0.37–0.63, complex_e 0.02–0.31, conservative speeds 0.14–0.19 m/s; failure is localised
(exactly **one C-05 per episode** ends an otherwise-clean run; C-02 nearly absent), |ey|
15–58 mm. No late capability decay (final ≥ 725k near-peak ckpt) — first run where training
longer kept helping. Still short of the ≥ 1-lap criterion (user calibration: ~800 steps ≈
1 complex_b lap) → per the user's extend instruction, **stage 1b launched 04.07.2026 13:03**:
`--resume-from` the stage-1 final, same config (+1M → 2M; LR resumes ~1.5e-4; ent_coef 0.01
inside the ckpt), run id `ppo_isaac2d_stage1b_2024_1M`, verified "resumed PPO … at 1000448
steps". Stage 2 (full-DR fine-tune) queues behind the first lap-completing checkpoint.

### Rationale

Iteration loop (session goal): stage-1's result confirms dynamics/scene DR was the binding
constraint (D-53) and the remaining gap is refinement, not redesign — the curve still had
slope at 1M.

### Impact

Champion checkpoint: `cobraflex_ppo_isaac2d_stage1_2024_1M.zip` (hash `c61d4a7e…`). No config
or code changes in this cycle. The one-C-05-per-episode signature marks the next diagnostic
target (probable curve-apex failure) if stage 1b plateaus below a lap.

### Verification

Run metadata `completed` (visual DR True / dynamics+scene False, ent 0.01); eval JSONs
archived; resume confirmed in the run log. Monitors armed on the new run.

---

## [04.07.2026] — D-53: run 2 falsified the exploration hypothesis (peak 43.5, ≤0.25 laps, stall mode observed) → iteration 3 = DR curriculum, stage-1 run launched (visual-only DR)

**Document(s) affected:** docs/DECISIONS.md (new **D-53**); new `src/cobraflex_rl/config/train_isaac_2d_stage1.yaml` (deltas vs train_isaac_2d.yaml: `dynamics_randomization` + `scene_randomization` OFF, own `model_path`). Evidence: `experiments/sim/training/ppo_isaac2d_v2_2024_1M/` (status interrupted @ 518k via STOP file — first live use, model + metadata written correctly) + `experiments/sim/eval_isaac/{cobraflex_ppo_isaac2d_lane_2024_1M_v2,ppo_isaac2d_v2_2024_1M_250000_steps}_enforcement.json`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50/D-51/D-52)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

**Run 2** (`ppo_isaac2d_v2_2024_1M`, ent_coef 0.01): the lever worked as designed — std decayed
~5× slower — and the policy **still never found the lap mode** (peak 43.5 @ 258k, 18–32
plateau). Stopped at 52 % by the pre-declared rule (STOP file, graceful). Nominal evals: the
250k peak ckpt is worse than run 1's (6/6 C-05, ≤ 0.25 laps); the final model is degenerate —
8-step dashes or a **0.021 m/s stall-crawl** (the SR-009/M-P6 stall mode observed for real).
Conclusion across runs 1–2: with FULL sim-to-real DR from step 0 the nominal slice is never
mastered, under either exploration regime. **Iteration 3 (D-53): DR curriculum** — stage 1
trains with **visual (H-10) DR only** (the proven Gazebo E-main recipe) on the D-51 trio;
stage 2 will `--resume-from` the stage-1 champion under the full-DR config.
**Run 3 `ppo_isaac2d_stage1_2024_1M` launched 04.07.2026 05:09** (detached, monitored).

### Rationale

Session goal: iterate runs with fixes until a robust policy. Run 2 was the controlled
experiment for the exploration hypothesis; its negative result redirects the lever to task
difficulty (curriculum), exactly the pre-declared next step in D-52.

### Impact

`train_isaac_2d.yaml` stays the full-DR stage-2/final-target config (untouched);
the stage-1 YAML is a documented curriculum variant. Champion so far across iterations:
run-1's 225k ckpt (≤ 0.45 laps) — still far from robust. Stage-1 exit criteria + the
stall-mode watch item (reward rebalance as next lever) recorded in D-53.

### Verification

Stage-1 config parse-checked (visual ON / dynamics+scene OFF, ent 0.01, 2-D, seed 2024,
ckpt_freq 25k); run 3 confirmed stepping on the trio with NO `isaac_dr` randomizer built
(correct: only in-env visual DR). STOP-file mechanism validated live on run 2 (metadata
`interrupted`, final model hash `5159d48b…`). Eval JSONs archived under
`experiments/sim/eval_isaac/`.

---

## [03.07.2026] — D-52: Isaac 2-D run 1 stopped at 88 % (exploration collapse, ≤0.45 laps nominal) → iteration 2 launched with `ent_coef 0.01`; new in-process evaluator + STOP-file graceful stop

**Document(s) affected:** docs/DECISIONS.md (new **D-52**); `src/cobraflex_rl/config/train_isaac_2d.yaml` (`ent_coef` 0.0 → 0.01); `tools/isaac_train.py` (`StopFileCallback`, status `interrupted` on STOP); **new** `tools/isaac_eval.py`. Evidence: `experiments/sim/training/ppo_isaac2d_2024_1M/` (run 1, status interrupted, metadata reconstructed) + `experiments/sim/eval_isaac/ppo_isaac2d_2024_1M_{225000,875000}_steps_enforcement.json`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50/D-51)
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

**Run 1** (`ppo_isaac2d_2024_1M`, commit `e51984f6`, launched 03.07 15:32 on this host — user
exception to the ≤1 h rule): `ep_rew_mean` peaked 61.5 @ ~208k, then a decaying 20–40 plateau;
stopped by SIGINT at ~88 % (880k) per the announced sustained-decay rule. The SIGINT
hard-killed the kit process before Python's `finally` (no metadata/final save) — metadata
**reconstructed post-hoc** (297k precedent), `status: interrupted`, last checkpoint 875k.
**Diagnosis:** exploration collapse — policy std 0.99 → 0.095 (36 %) → 0.023 (88 %) with
`ent_coef 0.0`. **Nominal eval** (new `tools/isaac_eval.py`; DR off, deterministic, 3 ep ×
3 circuits, enforcement): peak-225k ≤ 0.45 laps at crawl speeds, 7/9 cage emergencies;
final-875k worse (25–80-step deaths, 8/9) — real capability decay, no full lap ever. Cage
held: 2/18 nominal episodes off-road, everything else stopped by C-05. **Iteration 2**
(D-52): single lever `ent_coef 0.01`, all else identical; plus `StopFileCallback`
(`touch <run_dir>/STOP` → graceful end with model + metadata, status `interrupted`) and the
evaluator itself. **Run 2 `ppo_isaac2d_v2_2024_1M` launched 03.07.2026 23:46** (detached,
~10 h ETA), monitored on std + reward.

### Rationale

Session goal (user, 03.07.2026): evaluate on completion, conclude, iterate runs with fixes
until a robust policy emerges. The collapse mechanism repeats the Gazebo-1M failure family on
a harder task; entropy regularisation is the standard, minimal, attributable counter. Signals
can't stop Isaac cleanly (verified), hence the STOP file; iterating needs a nominal evaluator
(the D-50 follow-on tooling slice).

### Impact

`train_isaac_2d.yaml` now carries `ent_coef 0.01` as the live default (D-52 records the
history). Run-1 artefacts stay as evidence; its 225k peak is the run-1 champion but NOT a
robust policy. Exit criteria for run 2 in D-52 (std ≫ 0.1 stable; nominal laps ≥ 1 on b/d,
≥ 0.5 on e at peak); next levers pre-declared (reward rebalance → DR curriculum → longer
horizon). Gazebo verdicts untouched.

### Verification

`py_compile` on both tools; evaluator validated end-to-end (2 checkpoints × 9 episodes, JSON
records with ckpt hash + commit); checkpoint-load smoke under Isaac python (obs space
(4,84,84) — matches the manual VecFrameStack+transpose replication). Run 2 confirmed stepping
(scene = D-51 trio, DR active, seed 2024). pytest — 503 passed; `check_traceability` — PASS.

---

## [03.07.2026] — Pre-1M checkpoint hygiene: `checkpoint_freq: 25000` in train_isaac_2d.yaml + per-run checkpoint prefix in isaac_train.py

**Document(s) affected:** `src/cobraflex_rl/config/train_isaac_2d.yaml` (new `checkpoint_freq` key + corrected duration comment); `tools/isaac_train.py` (CheckpointCallback `name_prefix` = run id).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — tooling, before the 1M run
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

Two checkpoint-hygiene fixes ahead of the 1M full-authority run: (1) `checkpoint_freq: 25000`
in `train_isaac_2d.yaml` — unset it fell back to `n_steps` (1024), which at 1M steps means
~976 × 20 MB ≈ **20 GB** of rollout checkpoints; 25000 gives 40 (~800 MB) while keeping enough
granularity for a 297k-style peak rescue. (2) The CheckpointCallback prefix was the fixed
string `cobraflex_ppo_lane`, so **every run overwrote the previous run's same-step
checkpoints** (observed live: the D-51 pilot clobbered the morning pilot's rollout ckpts);
the prefix is now the run id. Also corrected the config's duration comment (~11 h at the
measured ~25 env-steps/s on the multi-track + DR 2-D scene, not 8.5 h at 33).

### Rationale

Both surfaced during the 03.07.2026 live validation; neither touches the training math
(same PPO, same env) — pure artefact hygiene for the long run.

### Impact

Checkpoints land as `<run_id>_<steps>_steps.zip` (+ matching `_vecnormalize_*.pkl`);
`--resume-from` is unaffected (explicit path). Existing checkpoints keep their old names.

### Verification

Live micro-run on the Isaac host (`total_timesteps` 2048, `checkpoint_freq` 1024):
completed, produced `<run_id>_1024/2048_steps.zip` + VecNormalize pkls with the run-id
prefix, honoring the YAML key (smoke artefacts removed afterwards). pytest — 503 passed;
`check_traceability` — PASS.

---

## [03.07.2026] — D-51: complex_e re-cut CLOCKWISE — steering-handedness balance for the Isaac multi-track training trio

**Document(s) affected:** docs/DECISIONS.md (new **D-51**; annotation in D-50 "New tracks"); docs/13 (preset list, full-authority offset note); `scripts/generate_complex_track.py` (new analytic builder `_complex_e_cw_waypoints()` + `TRACKS["complex_e"]` + CV-safe comment block); **regenerated assets**: `experiments/sim/tracks/complex_e/` (PNG + centerline + meta) and `src/cobraflex_rl/config/complex_e_centerline.yaml` + `complex_e_right_lane_centerline.yaml`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — before the 1M full-authority run
**Gate context:** after Gate G4 (does **not** reopen it; Gazebo artefacts untouched)
**Author:** Samuel Sanchez

### Change

`complex_e` is re-cut as the **clockwise** circuit of the CV-safe trio (it was CCW like
complex_b/d, and visually a near-twin of complex_d). Same design family — top straight,
wide end U-turns, "W" bottom with a central counter-steer crest — but driven the other
way: per-lap driven turning arc flips from 10.9 m left / 0.6 m right to **2.6 m left /
10.4 m right**. Geometry: R = 1.4 m semicircular ends (the driven right lane runs
**inside** the U-turns on a CW circuit), analytic cosine-W bottom (amplitude 0.145 m,
half-period 1.305 m), straight buffers at the arc→W joins; waypoints generated densely
(0.25 m) by `_complex_e_cw_waypoints()` because sparse Catmull-Rom kinks at curvature
sign flips (twelve sparse candidates measured R_min 0.44–0.89 m — under the boundary).
Full design + trade-offs in **D-51**.

### Rationale

User direction 03.07.2026: with all three circuits CCW the trio's driven lane
accumulated **36.5 m of left-turning arc vs 4.5 m right (8.1:1)** — the 2-D policy would
overfit left-steer commands; invert one circuit so the opposite steering trains. A plain
mirror is NOT CV-safe: CW puts the driven lane inside the U-turns (driven R = centre −
0.1225 m), and mirrored-old-complex_e measured 0.667 m driven — under the docs/12 §4.7
~0.9 m monocular boundary. Hence the widened re-design.

### Impact

Trio steering balance now **28.3 m left / 14.2 m right ≈ 2:1**, with ~⅓ of episodes on a
right-turn-dominant circuit. Shipped complex_e: perimeter 20.55 m, centre R_min 1.08 m,
**driven right-lane R_min 0.956 m** (design estimator; 0.904 m on the rounded YAML, vs
complex_d's 0.895 m on the same yardstick) — the most comfortable CV margin of the trio.
Scene offset of complex_e shifts +49.72 → **+49.92 m** (auto from the new bbox). The 20k
pilot `isaac2d_pilot_20k` ran on the OLD CCW complex_e (its metadata hashes are that
snapshot); the 1M run trains on the CW geometry. complex_a–d untouched.

### Verification

Generator: 411 points, perimeter 20.55 m, R_min 1.08 m, left+right turns TRUE. Shipped
YAMLs re-measured: CW signed area; driven R_min + arc balance as above. pytest — 503
passed. `python tools/check_traceability.py` — PASS (no ID changes). Live Isaac re-render:
three-circuit aerial (offsets +0 / +24.766 / +49.915, gaps + union grass hold) and
lane-cam from the new start (−2.9, 1.6, yaw 0.027 local) — only the own circuit in frame.
**Second 20k pilot on the CW trio** (`isaac2d_pilot_20k_d51`, seed 2024): status
`completed`; metadata records the NEW complex_e lane hash (`a271bc48ef…`) at offset
+49.9151 alongside the unchanged b/d hashes; episodes healthy (ep_len_mean 15–25, no
spawn deaths), cage live (C-04 0.8–1.6 %/step, emergencies ≈4–5 %), `raw_throttle`
logged; final model `policy/checkpoints/cobraflex_ppo_isaac2d_pilot_20k_d51.zip`
(hash `638e8029…`); scene renders archived under the run's `validation/`. End-of-run
reward 13.6 vs the pre-D-51 pilot's 28.5 — expected at a 20k budget with ~⅓ of episodes
on an unseen opposite-handed circuit; not a health signal.

---

## [03.07.2026] — Isaac USD re-import now replaces the canonical package (importer suffixed `cobraflex_isaac_1/` instead of overwriting)

**Document(s) affected:** `tools/isaac_scene.py` (`ensure_robot_usd`), `tools/isaac_import_check.py`.
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — tooling fix
**Gate context:** after Gate G4
**Author:** Samuel Sanchez

### Change

The Isaac 6 URDF importer refuses to overwrite an existing output package and writes a
suffixed `cobraflex_isaac_1/`, `_2/`… beside it instead. `BRINGUP_REIMPORT=1` therefore
used the fresh suffixed copy for that run only, while the canonical
`src/cobraflex/urdf/isaac_usd/cobraflex_isaac/` — git-tracked, and what every cached run
loads — silently kept the stale USD. (The committed package's own `doc` header shows the
same had happened on PC CAST: it was composed from a `cobraflex_isaac_3/`.) Both import
paths now remove the canonical package directory before importing, so a re-import
genuinely replaces it and leaves no suffixed droppings.

### Rationale

Surfaced by the D-50 live validation (03.07.2026): the first `BRINGUP_REIMPORT=1` runs
left `cobraflex_isaac_1/`/`_2/` untracked droppings without refreshing the canonical
package. Harmless while the URDF is unchanged (identical content), but a silent trap for
the first real URDF edit (e.g. the pending zedm inertia fix).

### Impact

`BRINGUP_REIMPORT=1` (and every `isaac_import_check.py` run) now rewrites the tracked
package in place. **Note:** the importer embeds its random `/tmp/…` staging paths in the
USD `doc` metadata, so a re-import is never byte-identical — expect a git diff on the 9
package files after any re-import; commit it when the URDF actually changed, discard it
otherwise.

### Verification

`isaac_import_check.py` on the Isaac host after the fix: **PASS**, output at the
canonical path, `isaac_usd/` contains only `cobraflex_isaac/` (no suffixed dirs), stage
walk unchanged (articulation root, 17 frames, 9 meshes, 4 wheel revolute joints).

---

## [03.07.2026] — D-50 live validation on the Ubuntu + Isaac host — full-authority env verified end-to-end (URDF→USD, three-circuit scene, Lane-Cam isolation, 20k 2-D pilot); host-deferral closed

**Document(s) affected:** docs/DECISIONS.md (D-50 Status → VERIFIED + closure note); docs/13 (status header, full-authority section, RL-training host-deferred note → validated, measured multi-track throughput). **No code or config changes.** New evidence: `experiments/sim/training/isaac2d_pilot_20k/` (learning curve, action samples, metadata, final checkpoint `policy/checkpoints/cobraflex_ppo_isaac2d_pilot_20k.zip` hash `9a375c52…`) + `…/isaac2d_pilot_20k/validation/` (5 scene/camera renders, C-04/C-06 throttle-probe CSV, one-off probe scripts).
**Phase:** posterior (Isaac / sim-to-real, D-44/D-50) — after E4/G4 close
**Gate context:** after Gate G4 (does **not** reopen it; no Gazebo verdict artefact touched)
**Author:** Samuel Sanchez

### Change

The D-50 host-deferral is closed: the full-authority environment was validated live on the
Ubuntu + Isaac 6 host (the only step D-50 left open). Performed, in order: (1) sanity —
`check_traceability` PASS, pytest **503 passed** on this host, Isaac python has sb3 2.8.0 /
gymnasium 1.2.3 / torch cu130 + CUDA; (2) scene smokes — `isaac_import_check.py` PASS
(exit 0); three-circuit scene `complex_b,complex_d,complex_e` builds at the designed
offsets (+0.0 / **+24.766** / **+49.724** m, 15 m bbox gaps, one union grass backdrop,
complex_b in native coordinates); per-circuit Lane-Cam renders from each start line show
**only the own circuit** (far-clip isolation holds, incl. the tightest case complex_e →
complex_d, ~16.2 m); (3) **20k full-authority pilot** `isaac2d_pilot_20k` (seed 2024,
`train_isaac_2d.yaml` verbatim except `total_timesteps: 20000`, final model via
`--model-path` into `policy/checkpoints/`): status `completed`, episodes survive the
spawn CV/cage priming (`ep_len_mean` 13.5 → **35.6**, never the 1–2-step failure mode),
`ep_rew_mean` 7.8 → **28.5** (explained_variance 0.85), `metadata.json` records
`platform: sim-isaac`, the `action` block and the 3-entry `circuits` block with
per-circuit YAML hashes, `action_samples.csv` carries `raw_throttle`; (4) **C-04/C-06
interplay probe** (scripted full-throttle, DR off — `validation/throttle_probe.csv`).

### Rationale

D-44/D-50 precedent: authored + unit-tested offline on the Windows host, the live Isaac
flow (USD multi-track build, Replicator annotator, SB3-in-Isaac-python) had to be
confirmed on the Isaac host before the 1M training is launched. This entry records that
confirmation and the first live measurements of the D-50 design predictions.

### Impact

The cage speed rules are now **measured, not latent**: C-04 fires on 0.7–1.8 % of training
steps (emergencies ≤ 6.5 %, C-06 ~93–95 % on the noisy early policy). The probe shows
acceleration is slip-limited by the 0.05 sim friction to ~0.49 m/s² (numerically
coincident with C-06's 0.5 m/s² commanded bound); the straight ceiling (~0.49 of
0.5 m/s) is reached with zero speed-rule chatter, and a dropping contextual ceiling
escalates C-04 → C-05 emergency within one cycle — **no C-04/C-06 sawtooth; no cage.yaml
re-tune needed** (thresholds stay `[provisional]`). The **1M main run is ready but NOT
launched on this host** (≤1 h host rule): on PC CAST run
`BRINGUP_REIMPORT=1 $ISAAC tools/isaac_train.py --run-id ppo_isaac2d_2024_1M --model-path
policy/checkpoints/cobraflex_ppo_isaac2d_lane_2024_1M` (defaults carry the config + CV-safe
trio; geometry track mode needs no PNGs; PC CAST's Isaac python needs sb3 + gymnasium).
Two sizing notes for that run: measured throughput on this scene is **~25 env-steps/s**
(RTX 5060, headless) — below the ~33 single-track 1-D figure, so ~11 h, not 8.5 h, on this
GPU class; and `checkpoint_freq` defaults to `n_steps` (1024) → ~976 × 20 MB ≈ **20 GB** of
checkpoints for 1M (consider `checkpoint_freq: 25000` in the config — left untouched here).

### Verification

`python tools/check_traceability.py` — PASS (no ID changes). pytest — 503 passed (this
host). Smoke exit codes 0; scene offsets asserted against `track_offsets` output; pilot
artefacts verified (metadata status/hashes/blocks, CSV schemas, 20 rollout checkpoints +
final model). Renders + probe CSV archived under
`experiments/sim/training/isaac2d_pilot_20k/validation/`.

---

## [02.07.2026] — D-50: Isaac full-authority training environment — 2-D action (steering + throttle) + multi-circuit sampling + CV-safe tracks complex_d/e

**Document(s) affected:** docs/DECISIONS.md (new **D-50**); docs/13 (status, command reference, TRACK env, track presets + curvature-boundary caveat, new §"Full-authority training", complex_b preset description corrected to the committed two-lane asset); docs/14 (§1.1 future-work note → implemented D-50 contract). Code (posterior track, no verdict artefacts touched): `gazebo_lane_env.py` (config-gated `action:` block + `circuits=` per-episode sampling), `cage_bridge.py` (2-D maps `policy_throttle_to_cage` / `target_speed_from_throttle_2d` / `safe_action_to_cmd_2d`), `rewards.py` (`throttle_delta`, default 0.0), `callbacks.py` (`raw_throttle` column), `tools/isaac_scene.py` (multi-track scene, `TRACK_GAP_M` 15 m, shared DR materials, union backdrop, `load_circuits`), `tools/isaac_train.py` (defaults → `train_isaac_2d.yaml` + `complex_b,complex_d,complex_e`; circuits + action metadata), new `src/cobraflex_rl/config/train_isaac_2d.yaml`, `scripts/generate_complex_track.py` (presets `complex_d`/`complex_e`), generated track assets (`experiments/sim/tracks/complex_{a,c,d,e}/`) + config centerlines (`complex_{a,c,d,e}_{right_lane_,}centerline.yaml`). Tests: `policy/tests/test_gazebo_lane_env_2d.py` (new, 16), `test_cage_bridge.py` (+8), `test_rewards.py` (+4).
**Phase:** posterior (Isaac / sim-to-real, D-44) — after E4/G4 close
**Gate context:** after Gate G4 (does **not** reopen it)
**Author:** Samuel Sanchez

### Change

The D-49 deferral is taken up for the Isaac track: the training environment now supports a
**2-D action (steering + throttle)** and **multi-circuit per-episode track sampling**, both
config-gated and **inert by default** (no `action:` block ⇒ the frozen 1-D ED-2 contract).
The policy's throttle maps to the cage scale u ∈ [0, 1] and actuates as
`speed = 0.5 m/s · u` (full stop below the 0.05 deadband) — 0.5 m/s = C-04 `v_max_straight`
= ODD-1.V_MAX, so the cage speed rules **genuinely arbitrate** (the 1-D actuation capped
speed below every ceiling ⇒ structurally latent). Reward gains a raw-delta `throttle_delta`
term (default 0.0). `isaac_train.py` defaults to the full-authority run: camera CNN + 2-D
action + physics/scene/visual DR on the multi-track scene `complex_b,complex_d,complex_e`
(15 m apart = Lane-Cam far clip; one circuit sampled per episode; per-circuit YAML hashes in
the run metadata). `complex_d`/`complex_e` are new **CV-safe presets** (driven-lane
R_min 0.932/0.907 m ≥ the docs/12 §4.7 ~0.9 m curvature boundary); `complex_a`/`complex_c`
assets were generated but violate that boundary (0.28/0.42 m) — reserved for
ground-truth-cage/monitoring runs.

### Rationale

G4 closed with project time remaining; the scope deliberately re-expands to the most
ambitious Isaac target (user decision 02.07.2026): a fully autonomous CobraFlex —
steering **and** throttle, camera perception, able to follow the lane markings of any
circuit — trained under maximum sim-to-real realism. The 2-D action makes SR-009's
stall/liveness sub-mode well-posed (M-P6 meaningful, SC-PERT-03 exercisable) and turns the
cage's speed rules from latent into measured behaviour; multi-circuit sampling + DR is the
operational meaning of "any circuit" at this stage. Design details and trade-offs in D-50.

### Impact

Gazebo verdicts, the F/E baselines and every existing config are untouched (default action
type `steer`; regression suite green). An Isaac-trained 2-D policy is a **new baseline** —
its evaluation (campaign runner support for 2-D checkpoints, SC-PERT-03 negative test,
cage speed-rule re-tuning if the C-04/C-06 interplay oscillates) is follow-on work on the
Ubuntu + Isaac host, where the live flow (multi-track USD build, Replicator, SB3-in-Isaac)
must be validated first (D-44 host-deferred precedent).

### Verification

`python tools/check_traceability.py` — PASS (no ID changes). Full pytest suite on the
authoring host (`.venv-win`, py3.14): **498 passed, 5 skipped** (pre-existing cv2 skips),
including the 16 new end-to-end env tests (real cage through a fake interface: C-04 fires
on overspeed, C-06 clips throttle jumps, full brake = true stop, circuit sampling
seed-reproducible + pinnable) and the C-06/accel alignment pin (0.5 m/s² ≤ 0.53).
`py_compile` on `isaac_train.py`/`isaac_scene.py`. Track radii verified against the
curvature boundary at generation time.

---

## [02.07.2026] — Gate G4 CLOSED — Phase-4 evaluation complete on both arms; docs synchronized to the GE4-V2 verdict of record; next phase = Isaac / sim-to-real

**Document(s) affected:** docs/07 (G4 closure note + matrix rows SR-012/013/014 → GE4-V2 Satisfied + historical re-scoping of the 139k evidence block + notes ⁴/⁵/⁶) and `tools/traceability_matrix.csv` (E-track rows → satisfied on `campaign_e_v2`; SR-006 rows → satisfied per D-39); docs/05 (SC-PERT-11/12/13 + SC-FRONT-07 documented, library 24 → **28**, executed-campaign notes); docs/11 (v0.6: header/preamble to GE4-V2 + closure status); docs/12 (v0.5: H-12 under-read note in §4.4 + ruta-2b revert + head-to-head closed); docs/13–14 (E4-closed pointers); docs/DECISIONS.md (D-48 status → CLOSED); manuscript ch.7 (GE4 executed, §7.1/§7.5/§7.6/appendix) + ch.8 (intro/§8.7/§8.9.5/§8.10 to V2 + G4); README.md (results + phase table G4 complete); CLAUDE.md (phase snapshot); memory index.
**Phase:** E4 close → posterior (Isaac / sim-to-real)
**Gate context:** **Gate G4 closed 02.07.2026**
**Author:** Samuel Sanchez

### Change

G4 (Phase-4 sim evaluation) is formally closed on the two campaign arms:
**(i) F-track F4** (frozen 10.06.2026): 1260 runs, global **`SATISFIED`** (all 7 SR-CL-A).
**(ii) Track-'E' GE4-V2** (verdict of record, 28.06.2026): 1970 runs, global **`NOT SATISFIED`
(literal)** blocking SR-002/003 only — both Satisfied on their own criterion (D-47), so **no
SR-CL-A safety predicate is breached on either arm**; SR-001 Satisfied (ruta-1), SR-012/013/014
Satisfied. Open items are documented, CL-B and non-vetoing (D-30): the F-arm SR-009/010 TBD
abstentions (SR-009 stall arm N/A-by-construction for the shared 1-D action, D-49; SR-010's
co-activation question answered on the E arm by the V2 grid — 30/85 in-ODD, genuine CL-B),
the verdict-framing decision (recorded as literal + annotation), and multi-seed N=5
(host-deferred). All prose that still described GE4-on-297k as pending (ch.7/ch.8/README/
CLAUDE.md/docs/12/13/14/scenarios_complex_b) is synchronized; the four complex_b-native
scenarios run by V2 (SC-PERT-11/12/13, SC-FRONT-07) are now first-class docs/05 entries.

### Rationale

The GE4-V2 campaign (28.06.2026) supplied the last verdict-bearing evidence Phase 4 needed;
what remained was documentation debt: matrix rows and CSV still scored the superseded 139k
roll-up, docs/05 lacked the four scenarios the campaign ran, and several documents still
called the 297k campaign "pending". Closing G4 requires the master record (docs/07), the
scenario library and the manuscript to agree with the evidence of record.

### Impact

Thesis verdicts are **frozen in Gazebo**; the open thread is the posterior Isaac / sim-to-real
track (docs/13–14, D-44): 2-D action retrain (D-49, makes SR-009 well-posed), better perception
(temporal estimator — the honest H-12 closure), and the sim-to-real gap toward the physical
platform (Phase 5). Isaac work does not reopen G4. No hazard / SR / cage-rule / metric IDs
added or changed; scenario definitions added to docs/05 match the executable YAMLs already in
`scenarios_complex_b/` (no new IDs — they existed since 24.06.2026).

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (28 scenarios now
defined, incl. SC-PERT-11/12/13 + SC-FRONT-07; all reference SRs). Campaign evidence
unchanged: `experiments/sim/campaign_e_v2/` (1970/1970, 0 errors) + `experiments/sim/campaign/`
(1260 runs). No code changes — docs/CSV only.

---

## [28.06.2026] — GE4-V2 campaign COMPLETE — SR-001 closed by ruta-1; global NOT SATISFIED (literal) blocking SR-002/003 only

**Document(s) affected:** docs/07 (GE4 note + Last-update + note ⁷), docs/11 (§8.4 rewritten to V2), docs/DECISIONS.md (D-47/D-48 V2 outcome), manuscript ch.8 §8.9; new evidence + figures under experiments/sim/campaign_e_v2/  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation — verdict of record  
**Author:** Samuel Sanchez  

### Change

GE4-V2 ran on the 297k E-main with the validated V2 prep (honest legacy estimator): **1970 runs, seed
2024, 0 errors** (`experiments/sim/campaign_e_v2/`). **Global `NOT SATISFIED` (literal), blocking
SR-CL-A SR-002/003 only.** Headline result vs V1 (which blocked SR-001/002/003 + SR-012/014
incomplete): **SR-001 is now Satisfied** — ruta-1's in-ODD IC clip removed the 9/30 out-of-ODD
SC-EDGE-02 spawns SR-001 must not be charged for, so SC-EDGE-02 passes **28/30** (2 residual breaches
at the recovery-basin edge 0.118–0.121 m). **Ruta-1 alone closed SR-001; ruta-2b was unnecessary** (and
was reverted after its closed-loop regression). **SR-012/013/014 Satisfied** (coverage closed). SR-002/003
fail only the oval-legacy 2.0 s recovery-time clause (13/30, max M-P4 = 14.4° ≤ 25°) → reconciled
Satisfied (D-47). So no SR-CL-A safety predicate is breached. SR-010 genuine CL-B (30/85 in-ODD
co-activation breaches). Verdict of record (user decision): **literal NOT SATISFIED + reconciliation
annotated** (not re-stated as SATISFIED). Regenerated V2 figures (`tools/plot_camera_comparison.py`,
`plot_frontier.py`) + new `fig_sr001_edge02_offset.png`.

### Rationale

The early-output check on the first V2 launch caught the ruta-2b regression and aborted it; the relaunch
with the legacy estimator gave the clean verdict. The result is *better* than predicted (SR-001 closes),
showing ruta-1 (scoping the IC to the ODD) was the real fix.

### Impact

Verdict of record moves to V2 (`campaign_e_v2`); V1 (`campaign_e_297k`) + 139k become historical.
docs/07, docs/11 §8.4, D-47/D-48 updated; manuscript ch.8 §8.9 updated. No CSV regen (no hazard/SR edits).

### Verification

`pytest` 475 passed; `check_traceability` PASS; campaign 1970/1970, 0 errors. Comparison via
`scratchpad/compare_v1_v2.py`.

---

## [27.06.2026] — ruta-2b REVERTED (conservative lane-selection); no robust single-frame fix for the H-12 under-read (D-48)

**Document(s) affected:** src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py, policy/tests/test_cv_lane_estimator.py, docs/07, docs/11, docs/DECISIONS.md (D-48)  
**Phase:** E4 (track-'E' GE4 evaluation — V2 prep)  
**Gate context:** GE4 (camera) evaluation — V2 launch verification  
**Author:** Samuel Sanchez  

### Change

The committed ruta-2b conservative lane-selection (`conservative_lane_selection`) is set **default
False** (legacy nearest-centre restored). Reason: verifying the first V2 launch's early output caught
a regression — **SC-EDGE-01 emergency at step 1** (V1: clean 150 steps). The conservative rule cannot
distinguish a genuinely off-centre vehicle from a *centred* one under a small heading error (both
split into the same opposite-sign pairs), so it fires spurious C-01/C-05 emergencies. A heading gate
only relocated the false trigger to step 8 (a 9-run closed-loop smoke confirmed SC-EDGE-01 still
emergencies and **SC-NOM-02, a clean V1 nominal curve, regressed**). The ambiguity is irreducibly
single-frame; a real fix needs temporal lane tracking, which still would not fix the SC-EDGE-02 spawn
frame (no prior) → would not close SR-001 anyway. **SR-001 stays a genuine fail** (the H-12 under-read
is an un-cheaply-patchable D-43 limitation). Kept opt-in for the regression tests / future work.

### Rationale

A 16 h verdict campaign must use a trusted estimator; an estimator that fires spurious emergencies on
centred/recovering/curving views would invalidate the run (and is scientifically dishonest vs the
genuine SR-001 finding). The early-output check did its job.

### Impact

V2 re-runs with the legacy estimator; SR-001 expected to fail (global `NOT SATISFIED`). Ruta 1 (in-ODD
IC), the run-count bump (SR-012/014), and the D-47/SR-006/SR-009/SR-010 reconciliations are unaffected.
The prior-entry claims of "ruta-2b implemented + validated" are superseded by this revert.

### Verification

`pytest` → **475 passed** (conservative tests now opt-in explicit). `check_traceability` PASS.
Closed-loop smoke (SC-EDGE-01/02 + SC-NOM-02 curve) is what surfaced the regression.

---

## [27.06.2026] — GE4-V2 prep: SC-EDGE-02 in-ODD IC clip (ruta 1) + H-12 under-read mechanism finding (D-48)

**Document(s) affected:** docs/DECISIONS.md (D-48), docs/07 (GE4 note mechanism), docs/11 (§8.4 mechanism), scenarios_complex_b/edge/sc_edge_02.yaml; src/cobraflex_rl/cobraflex_rl/cv_lane_estimator.py + policy/tests/test_cv_lane_estimator.py  
**Phase:** E4 (track-'E' GE4 evaluation — V2 prep)  
**Gate context:** GE4 (camera) evaluation — V2 closure prep  
**Author:** Samuel Sanchez  

### Change

Investigated the sole remaining SR-001 blocker (SC-EDGE-02). **Ruta 1 (applied):** clipped the IC
randomisation so every spawn is in-ODD — `lateral_offset_uniform_m: [-0.02, 0.02] → [-0.02, 0.0025]`
(seed 0.12 m → [0.10, 0.1225]); the V1 symmetric band spilled 9/30 reps out-of-ODD. **Mechanism
correction (D-48):** V1 traces show the SC-EDGE-02 fails are an **H-12 estimator under-read**, not
perception loss — `cv_ok` stays True and `cv_ey ≈ 0.04 m` while true `ey` → 0.30 m (wrong-lane lock,
self-consistent, so SR-014 misses it). Corrected the "estimator loses the lane" wording in docs/07 +
docs/11 §8.4. **Ruta 2b (implemented + validated):** a Gazebo frame dump at the SC-EDGE-02 offsets
pinned the cause — when the vehicle is past its own left line a third (next-left) line forms a
competing pair whose opposite-signed centre is marginally nearer, so the legacy `min |centre|`
selection mis-locks onto the neighbour. Fix: `CvLaneEstimator` now picks the conservative
(largest-offset) pair when plausible pairs straddle the vehicle with opposite-sign centres
(`conservative_lane_selection`, default True; inert otherwise). Re-running the dump, cv_ey now reads
+0.140 / +0.181 m at ey 0.12 / 0.16 (was −0.130 / −0.088); full pytest green (471, +2 wrong-lock
regression tests). Ruta 2a (retrain) is out of scope per user. **SR-012/014 D-29 gate:** their V1
INCOMPLETE was a run-count gap (SC-PERT-08/09/10 ran 20 enf < the 25 CL-A min; the SC-PERT-07-style
bump had been missed) — bumped 20 → 25 (enf+mon); all pass 20/20, so V2 reaches coverage. **CL-B
items (non-gating) addressed** (docs/07 note ⁸): SR-011 reconciled on its own metric (max σ_θ over
1 s = 3.0° < 5° M-P7; same SC-EDGE-01 recovery-time artifact as SR-002/003); SR-006 re-pointed in
`run_campaign.aggregate_sr` → `scored_out_of_band` (`OUT_OF_BAND_SRS`, +unit test; D-39 follow-up)
so the V2 report stops reading `failed`. **SR-010 attribution gap CLOSED** (on existing V1 data —
`grid_point` is persisted under `summary.json["campaign"]`): added `sc_edge05_grid_split` to
`tools/campaign_e_failure_modes.py` (+3 unit tests). The split corrects the earlier "largely OOD"
guess — **30 of 85 in-ODD grid points breach M-S1** (a genuine SR-010 co-activation finding) vs 10/15
OOD; SR-010 is a real CL-B result, plausibly reduced in V2 by ruta-2b. **SR-009 resolved as N/A for the
steering-only action space (D-49):** SC-PERT-03's stall test is ill-posed for `ACT_DIM=1` (throttle
fixed → M-P6 ≡ 0 by construction, the `r−λ·|throttle|` injection is inert) — the stall fine-tune was
**not launched** (it would produce an identical policy). Stall arm satisfied-by-construction; the live
M-S2-monitoring arm is covered. **D-49** records: keep steering-only for the Gazebo E verdict (ED-2),
defer 2-D action (steering+throttle) to the Isaac posterior track (docs/14) after E4 closes for Gazebo.

### Rationale

SR-001 is the only thing standing between the GE4 verdict and (at best) INCOMPLETE; pinning down
whether it is a scenario-IC artifact or a genuine cage limitation required the trace analysis above.
It is both: 9/12 V1 fails are an out-of-ODD IC spill (ruta 1 fixes), and the residual is a genuine
H-12 safety-monitor blind spot (ruta 2b target).

### Impact

No verdict change yet (V2 not re-run). SC-EDGE-02 IC changed → its spawns differ in V2; the cage
perception is changed (conservative selection, default on) → the V2 campaign uses it automatically.
GE4-V2 is **ready on the perception side**; the open step is the ≈1940-run campaign itself (a host
job) + the closed-loop confirmation it gives. No CSV regeneration.

### Verification

`tools/check_traceability.py` → All checks PASSED, 0 warnings. `sc_edge_02.yaml` re-parses (valid).
`pytest` → **471 passed** (incl. 2 new wrong-lock regression tests). Gazebo frame dump
(`scratchpad/edge02_estimator_dump.json`): cv_ey +0.140 / +0.181 m at ey 0.12 / 0.16 (corrected).

---

## [27.06.2026] — complex_b GE4 scenario validation + SR-002/003 own-criterion reconciliation (D-47)

**Document(s) affected:** docs/07 (GE4-297k note + new footnote ⁷), docs/11 (§8.4 verdict + table), docs/DECISIONS.md (D-47), scenarios_complex_b/ (24 scenario banners + 22 inline comments, README.md)  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation — verdict validation  
**Author:** Samuel Sanchez  

### Change

Validated the `scenarios_complex_b/` library against the 297k GE4 evidence on four axes and
recorded the result. (1) **Timing/geometry audit:** `start_s_m = 2.0` re-mapping confirmed sound;
`*_completed` termination events confirmed decorative (`scenario_runner` is `timeout_s`-bounded);
only SC-EDGE-03's throttle pulse lands on the straight (optional curvature-coupling refinement,
SR-004 already satisfied). (2) **Spawn spot-check:** confirmed from the verdict-run
`cage_status.csv` spawn rows — SC-EDGE-02 lateral +0.128 m (IC 0.12), SC-FRONT-01 +0.169 m
(IC 0.16), SC-EDGE-01 yaw +14.3° (IC 15°), `start_s = 2.0` on the straight. (3) **Frontier
scoring:** confirmed already correct — the aggregator maps SR→scenario via the docs/03 "Verified
by" lists, so SC-FRONT-* are contrast-only and never veto an SR-CL-A. (4) **SR-002/003
reconciliation (D-47):** the 9 SC-EDGE-01 enforcement "fails" fail only the oval-legacy
`time_to_recovery_heading < 2.0 s` clause; on the SRs' own criteria (M-P4 = 14.3° ≤ 25°;
TTLC unbreached, max M-S1 = 0.035 m) both are **Satisfied**. Updated docs/07 + docs/11: blocking
SR-CL-A **{SR-001/002/003} → {SR-001}**, the F4→E flip list drops SC-EDGE-01, and SC-EDGE-02 is
re-characterised as an *in-ODD* boundary-band failure (not "out-of-ODD"). Replaced the stale
"DRAFT / NOT validated" banners on 24 scenarios with a VALIDATED banner.

### Rationale

The GE4-297k global `NOT SATISFIED` was reported as blocking on three SR-CL-A; validation against
the logged per-run evidence shows two of the three (SR-002/003) are scored by a scenario clause
that is neither SR's documented satisfaction predicate — the same honesty defect D-39/note ⁴ fixed.
SR-001 remains a genuine breach (in-ODD 0.12 m start → 12/30 enforcement edge contacts), so the
global verdict is unchanged but its cause is now single and clean (D-43 camera-perception cost on
lateral recovery; heading/TTLC hold under the camera).

### Impact

Global 297k GE4 verdict unchanged (`NOT SATISFIED`, SR-001). SR-002/003 verdicts move
Not-satisfied-as-scored → Satisfied-on-own-criterion. No re-run required — the reconciliation is
computed from existing logged evidence (`epsi`/`summary.json`). The F-track matrix rows
(SR-001..011) are unaffected (F4 frozen). No CSV regeneration (no hazard/SR register edits).

### Verification

`tools/check_traceability.py` — see entry below / re-run after edit.

---

## [27.06.2026] — GE4 evaluation campaign on the 297k E-main (complex_b) — global NOT SATISFIED

**Document(s) affected:** docs/07, docs/11 (§8.4 new, §9.2, version log v0.5), scenarios_complex_b/README.md; tools/run_campaign.py, tools/plot_camera_comparison.py; new evidence under experiments/sim/campaign_e_297k/  
**Phase:** E4 (track-'E' GE4 evaluation)  
**Gate context:** GE4 (camera) evaluation  
**Author:** Samuel Sanchez  

### Change

Ran the full GE4 verdict campaign on the **complex_b 297k peak** E-main: **1940 runs**,
seed 2024, 28 scenarios × {enforcement, monitoring}, 0 errors
(`experiments/sim/campaign_e_297k/campaign_report.json` + `failure_mode_breakdown.json` +
6 figures). Documented the verdict in docs/11 §8.4 and the docs/07 GE4-on-297k note (the
139k per-SR block is now historical). Pre-campaign hardening this cycle: `parameterised_grid`
IC injection + per-run co-activation counters + `kappa_seed` curve-spawn hook (SC-EDGE-05 now
determinate), the worn/particles/flip worlds + SC-FRONT-07 flip scenario, PERT timeouts → 40 s
(cover the first curve) + SC-PERT-07/08 onset moved into the curve, a `--train-config` fail-fast
guard and a GUI-reap fix in `run_campaign.py`, and a `--campaign-dir` arg on
`plot_camera_comparison.py`.

### Rationale

The per-SR verdicts were still scored on the superseded 139k oval policy; the thesis verdict
must come from the 297k E-main on its own circuit.

### Impact

**Global verdict (enforcement) `NOT SATISFIED`** — blocking SR-CL-A SR-001/002/003; SR-012/014
INCOMPLETE (documented D-29 exception, D-46). Two-sided finding: **in-ODD (NOM + PERT) the cage
is a safety asset** (0 road-edge, removes perception-degradation failures the bare policy
commits — PERT-04/09/11/12/13 enf PASS vs mon FAIL), but **out-of-ODD the camera cage cannot
recover** (125 enforcement road-edge contacts vs 0 in the 139k, all in SC-EDGE-02/05 +
SC-FRONT-01/03/04/06; D-43 common cause; F4→E PASS→FAIL flips). SC-EDGE-05 determinate (0.17),
SC-FRONT-07 flip PASS. Not a pure availability cost as the 139k was. Open: SC-PERT-03 (D-38),
multi-seed N=5 (host-deferred), figure caption strings ("v1/1660" → 297k/1940).

### Verification

`tools/check_traceability.py` PASS (0 warnings); `pytest policy/tests cage/tests` 462 passed.
Campaign roll-up reproducible via `tools/run_campaign.py … --out experiments/sim/campaign_e_297k`.

---

## [24.06.2026] — STPA SR-derivation table + control-structure diagram (folded into docs/02)

**Document(s) affected:** `docs/02_hazard_register.md` (SR-derivation table UCA→constraint→SR + Fig. STPA-CS reference, next to the per-block sweep); new `manuscript/figures/fig_stpa_control_structure.svg`.  
**Phase:** F1 safety analysis (STPA) — methodology documentation  
**Gate context:** none (derivation rationale; no H/SR/C/M changed, no verdict)  
**Author:** Samuel Sanchez  

### Change

Added, **in docs/02** (next to the per-block sweep), the bottom-up "SRs derived this way"
view requested as a thesis tool: a **UCA → safety-constraint → SR derivation table** tracing
every SR-001..014 to the block + UCA it answers, and the **control-structure block diagram**
(Fig. STPA-CS, `.svg`, in the style of the SE4ADS Ch.5 STPA slides). An interim standalone
`docs/15` was **consolidated into docs/02 and removed** to keep a single STPA home (the
analysis already lived in docs/02). Operationalises **D-27**.

### Rationale

Requested as a thesis tool ("the SRs were derived this way, per the four blocks, what could
fail"). Makes the bottom-up STPA reasoning auditable and the per-block coverage explicit
(controller/sensor fully derived; process/actuator execution-faults Phase-5).

### Verification

`python tools/check_traceability.py` → **All checks PASSED** (no registered IDs changed;
docs/02 references existing H/SR/C only).

---

## [24.06.2026] — STPA per-block completeness: actuator + process UCAs identified (Phase-5 deferred)

**Document(s) affected:** `docs/02_hazard_register.md` (STPA scope statement — new per-block control-structure sweep table; "Open hazards under consideration" — actuator execution-fault + process-disturbance entries).  
**Phase:** safety analysis (STPA) — coverage audit  
**Gate context:** none (hazard identification; no new *registered* H/SR/C, no verdict)  
**Author:** Samuel Sanchez  

### Change

Audited the hazard register against the four STPA control-structure blocks (controller /
sensor / process / actuator; SE4ADS ch.5 p.23–24, the four UCA types). Added an explicit
**per-block UCA sweep** table to the STPA scope statement, and registered two
previously-implicit UCAs under "Open hazards under consideration": **actuator command not
faithfully executed** (UCA *not given* / *unsafe given* at the actuator) and **process
disturbance / unmodelled dynamics** (low-friction skid).

### Rationale

The sweep showed controller and sensor blocks strongly covered (H-01/02/03/04/09;
H-06/10/11/12) but the **actuator** block only implicit (H-05 command-shaping + SC-PERT-02
latency) and the **process** block thin (H-08 stall only). Both new UCAs are deferred to
**Phase 5 (physical)**: the Gazebo DiffDrive actuator is faithful and the track is
flat/dry/controlled (ODD-1/2), so a control-level cage with no actuator feedback cannot
mitigate them in the sim verdict — mitigation is actuator-/platform-level. Mirrors the
existing Phase-5 "sensor calibration drift" entry.

### Verification

`python tools/check_traceability.py` → **All checks PASSED** (no registered IDs changed; the
`H-??` entries are under-consideration / Phase-5, outside the H/SR/C traceability chain).

---

## [24.06.2026] — GE4 indeterminate fix: SC-PERT-05 labelled criterion wired into the per-run verdict

**Document(s) affected:** code — `src/cobraflex_rl/cobraflex_rl/criterion_eval.py` (new `labelled_arms`), `scenario_perturbations.py` (`level_index`), `eval_policy.py` (labelled-arm selection); tests `policy/tests/test_criterion_eval.py` + `test_scenario_perturbations.py`. Docs: `docs/07` footnote ⁴.  
**Phase:** track 'E' (camera) — GE4 (eval) wiring  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Wired the two-arm `low:/high:` labelled per-run criterion so a single run is scored against
the arm matching its perturbation level: `eval_policy` now evaluates
`criterion_eval.labelled_arms(expr)[perturbation.level_index]` instead of hard-coding
`verdict = None`. `scenario_perturbations` records `level_index` (rep % n_levels) for the
multi-level types. Resolves GE4 open item (b) for **SC-PERT-05**.

### Rationale

SC-PERT-05 (low-light) was indeterminate (D-38 class) only because the labelled evaluator was
unwired — it has two arms with different specified outcomes (low: keep driving / SR-012;
high: controlled stop allowed / SR-013), one per level. Each rep runs one level, so the
matching arm is the correct per-run verdict.

### Impact

SC-PERT-05 will **score** (not indeterminate) on the 297k GE4 run — completing SR-012's
adverse evidence on the low arm and SR-013 on the high arm. **Still open** (separate, F-track
CL-B): SC-PERT-03 (finetune arms, not level-resolvable — grouped by the driver) and SC-EDGE-05
(parameterised_grid IC injection). No verdict change now (139k roll-up unchanged).

### Verification

`pytest` → **454 passed, 5 skipped** (incl. new `test_labelled_arms_order_and_level_arm_semantics`
+ `test_visual_degradation_level_index_round_robin`). Logic check: SC-PERT-05 rep0 → low arm
(a stop fails — `M-P2 == 1` required), rep1 → high arm (safe stop passes).

---

## [24.06.2026] — D-46: two-sided D-29 coverage for the camera SRs (SC-NOM-01 nominal anchor)

**Document(s) affected:** `docs/03_safety_requirements.md` (SR-012/013/014 Scenarios += SC-NOM-01) → `docs/data/safety_requirements.csv`; `docs/07_traceability_matrix.md` (matrix cells + footnote ⁶); `docs/DECISIONS.md` (D-46 + index + status note); `scenarios_complex_b/nominal/sc_nom_01.yaml` (`references_SR`).  
**Phase:** track 'E' (camera) — GE4 coverage  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Anchored the **D-29 nominal family** of the camera-stressor SRs (SR-012/013/014) on the
clean-input nominal run **SC-NOM-01** (the no-false-trigger / baseline-competence arm),
keeping the adverse family on the SC-PERT camera scenarios. Recorded as **D-46**;
SC-NOM-01's `references_SR` updated for bidirectional traceability.

### Rationale

The camera SRs were authored adverse-only → `nominal = 0` → INCOMPLETE under D-29. D-29's
nominal family is the **baseline arm of a two-sided test** (no-false-trigger + correct
response), not a "repeat the hazard under clean input" requirement; SC-NOM-01 is the genuine
no-false-positive control + competence baseline. Mirrors how SR-001 is covered
(SC-NOM-01/02 nominal + SC-EDGE-02 adverse). See D-46.

### Impact

`--dry-run` D-29 feasibility: SR-012/013/014 nominal **0 → 50**, adverse ≥ 25 → all three
**FEASIBLE** (GAP cleared). Combined with D-45 (SR-CL-A vetoes cleared) and SC-PERT-13
(SR-013 adverse), the camera SRs are now **coverage-ready**; the verdict is scored when the
297k GE4 campaign runs. No verdict change now (coverage/plan, not evidence).

### Verification

`python tools/sync_safety_requirements.py` → 14 SRs. `python tools/check_traceability.py`
→ **All checks PASSED, 0 warnings**. `run_campaign --dry-run` on `scenarios_complex_b`:
SR-012/013/014 `[OK]`, families nominal = 50 / adverse = 40.

---

## [24.06.2026] — Track-'E' degraded-markings scenarios SC-PERT-11/12/13 + scenario↔SR traceability

**Document(s) affected:** `docs/03_safety_requirements.md` (SR-012/013/014 Scenarios column) → `docs/data/safety_requirements.csv` (regenerated via `sync_safety_requirements.py`); `docs/07_traceability_matrix.md` (SR-012/013/014 Scenario cells + new footnote ⁶). New artefacts: `scenarios_complex_b/perturbed/sc_pert_{11,12,13}.yaml`; `scripts/generate_complex_track.py` (line toggles + arc-length erase); `experiments/sim/tracks/complex_b/complex_b_gaps.png` + `src/cobraflex/materials/road_assets/tracks/complex_b_gaps.png`; `src/cobraflex/worlds/lane_following_complex_b_gaps.world`.  
**Phase:** track 'E' (camera) — GE4 scenario library  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Added three complex_b camera scenarios for **degraded lane markings**, a face of H-10
admitted in-ODD by ODD-2 §5.4 ("lane markings may be partially degraded or faded along
arbitrary segments"): **SC-PERT-11** worn/segmented markings (world-variant — the
`generate_complex_track.py` line-erase renders `complex_b_gaps.png`, lane paint removed
over arc-length patches s≈2.5–6.5; new `lane_following_complex_b_gaps.world`),
**SC-PERT-12** camera image degradation (glare injector on normal markings — matched
control), **SC-PERT-13** both compounded. All complex_b-native (start_s_m = 2.0, the run
traverses the degraded zone), criterion per **D-45** (`M-S1 < 0.16 AND road_edge_contact
== False`). Wired the scenario↔SR traceability: SR-012 / SR-014 ← SC-PERT-11/12/13,
SR-013 ← SC-PERT-13, in both the docs/03 SR register (→ CSV) and the docs/07 matrix.

### Rationale

No new SR/hazard needed: worn/missing markings degrade the lane cue → it is the
infrastructure face of **H-10 / SR-012** (with SR-013 loss and SR-014 suspect-estimate as
the severity-dependent fall-backs), the twin of the SC-PERT-09/10 worn/wet world variants.
The combined SC-PERT-13 additionally gives **SR-013 a second adverse scenario**, closing
its adverse-side D-29 gap.

### Impact

`--dry-run` D-29 feasibility: SR-013 adverse family **0 → 40** (SC-PERT-13); SR-012/014
adverse families stay ≥ 25. The three camera SRs now have **adverse coverage met**; the
residual gap is **nominal = 0** (separate — the clean-input SC-NOM-01 anchor, Option 1).
Scenarios **not yet run** — no verdict change; scored when the 297k GE4 campaign runs.
Matrix grows 1660 → 1880 runs (seed 2024). check_traceability **PASS**.

### Verification

`python tools/sync_safety_requirements.py` → 14 SRs written. `python
tools/check_traceability.py` → **All checks PASSED, 0 warnings**. `run_campaign --dry-run`
on `scenarios_complex_b` loads 27 scenarios, builds the matrix, SR-013 adverse = 40.
Variant texture verified pixel-aligned to the base (only the erased patches differ).

---

## [24.06.2026] — D-45: controlled safe stop scored as pass on the SR limit predicate (camera GE4 criteria)

**Document(s) affected:** `scenarios_complex_b/` per-run criteria — `edge/sc_edge_02`, `edge/sc_edge_03`, `perturbed/sc_pert_01`, `perturbed/sc_pert_02`, `perturbed/sc_pert_04`, `perturbed/sc_pert_06`, `perturbed/sc_pert_09`, `perturbed/sc_pert_10`; `docs/DECISIONS.md` (new **D-45** + index + status note); `scenarios_complex_b/README.md` (new "Verdict scoring" section).  
**Phase:** track 'E' (camera) — GE4 (eval) scoring  
**Gate context:** before the complex_b 297k GE4 verdict run  
**Author:** Samuel Sanchez  

### Change

Dropped the `emergency == False` clause from the per-run pass criterion of the **eight
adverse safety scenarios** in the complex_b camera library, so a cage-commanded
**controlled safe stop scores as a pass** whenever the SR's safety limit held
(`M-S1 < 0.16`, plus `road_edge_contact == False` where present). A real breach
(`M-S1 >= d_max` / road-edge) still fails. Recorded the rule as decision **D-45**.
SC-PERT-07 (SR-013, stop *required*: `emergency == True`) and the nominal scenarios
(gated by `M-P2 == 1`) are unchanged; the frozen oval `scenarios/` + 139k evidence
are untouched.

### Rationale

Under the camera (D-41/D-43) the cage flips latent→active in-ODD: a controlled stop is
the safety mechanism working, not a breach. The original clause scored those safe stops
as fails (139k: 13/13 SC-EDGE-02 + 20/20 SC-PERT-04 enforcement fails were emergency-only,
with `M-S1 < d_max` and 0 road-edge contacts) — an **availability** cost mis-scored as a
**safety** failure. The thesis verdict is a safety verdict (D-28/D-30). Full argument and
alternatives in D-45.

### Impact

Clears the three SR-CL-A vetoes behind the 139k `NOT SATISFIED` (SR-001, SR-012, SR-014).
**Not sufficient for `SATISFIED`**: SR-013 stays INCOMPLETE (D-29 family coverage —
adverse-only SC-PERT-07) and the indeterminates persist (SC-PERT-05 labelled criterion
unwired; SC-EDGE-05 grid ICs not injected). Applies when the 297k GE4 campaign is run on
`scenarios_complex_b`; `docs/07` + Ch.8 §8.9 E-track verdicts to be re-pointed 139k→297k
at that time. No H/SR/C/M identifier changed (per-run criterion strings only;
`references_SR` untouched).

### Verification

`python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (criteria edits
touch no IDs). `python -m pytest -q` → **452 passed, 5 skipped**. Direct evaluation of the
eight edited criteria via `run_campaign.evaluate_criterion`: a safe stop with limits held →
pass, a real breach → fail, drove-fine → pass; SC-PERT-07 confirmed unchanged (no-stop →
fail). The 24 complex_b YAMLs parse (`load_scenarios`).

---

## [24.06.2026] — Root README pivoted to track 'E' (camera) primary; F kept as baseline

**Document(s) affected:** `README.md` (intro framing, "Results at a glance" rewritten to the `complex_b` 297 k camera E-main + `_newcam` figures, track-'E' status note, "RL policy" pillar, GIF captions, how-to-read pointer to `docs/11`).  
**Phase:** track 'E' (camera) — public-facing consolidation  
**Gate context:** none (front-page narrative; no H/SR/C/M touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Brought the repository's front page in line with the manuscript pivot: the **end-to-end
camera** policy (E-main `complex_b` 297 k) is now the headline result (beats the CV baseline
on tracking, 10.9 vs 17.2 mm, 0 emergencies, cage latent), with the **state-vector track 'F'**
(oval, 11.2 laps / 9.9 mm vs PD 23 mm, G4-`SATISFIED`) kept explicitly as the frozen baseline /
control arm. Results figures swapped to the `_newcam` set; GIF captions labelled as the
state-vector baseline demo; added the honest scope note (nominal eval done; GE4-on-297k pending).

### Verification

Referenced `_newcam` figures exist; the only residual F-track numbers are the labelled baseline
mention. `tools/check_traceability.py` → PASS (no identifiers touched).

---

## [24.06.2026] — Seed 42 nominal eval done (enforcement) → multi-seed table row filled, basin confirmed

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.5.3 — seed-42 eval columns filled + reading). Evidence: `experiments/sim/runs/rl_newcam_eval_42_cb125k_4k4/` (synced from Ubuntu).  
**Phase:** track 'E' (camera) — multi-seed (GE3)  
**Gate context:** none  
**Author:** Samuel Sanchez  

### Change

Seed 42 evaluated on SC-NOM-01 (enforcement, complex_b, checkpoint hash `bc7e3d17…`):
**4,91 laps, mean |ey| 13,3 mm, max 41,6 mm, 0 emergencies, 64,9 % interventions (C-06
only)**. Filled the §7.5.3 multi-seed table row and added the 2024-vs-42 reading.

### Rationale / Impact

Confirms seed 42 is **constraint-respecting** (cage latent in safety — 0 emergencies, no
C-01/C-03/C-05) and **beats the CV baseline** on tracking (13,3 vs 17,2 mm), like 2024. The
only seed difference is **smoothness**: 42 runs 64,9 % C-06 vs 2024's 43,5 % (jerkier,
consistent with its lower/earlier peak). So the constraint-respecting basin is **stable
across the two seeds** in what matters for safety; only the benign C-06 rate-limiting cost
varies. Monitoring arm for 42 also done (4,90 laps, |ey| 16,5 mm, 0 emerg, 68 % C-06): the
enforcement↔monitoring contrast shows C-06 contributes ~3 mm of tracking to this jerkier
seed (mon 16,5 mm → enf 13,3 mm; near the CV's 17,2 without it), while staying safety-latent
(no C-01/C-03/C-05 either mode). Seeds 23/666/123 still TBD. No verdict changed.

### Verification

Checkpoint hash in the eval metadata (`bc7e3d17…`) matches the rescued seed-42 peak
(`num_timesteps == 124928`). `tools/check_traceability.py` → PASS.

---

## [23.06.2026] — Track-'E' multi-seed comparison started (seed 42 added; table + figure prepared for N=5)

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (§7.5.3 — new E-track multi-seed table; §7.2.7 — "2 of 5 done"). New: `manuscript/figures/fig_7_8_multiseed_newcam.png`; `experiments/sim/training/ppo_newcam_complex_b_42/checkpoints_peak/cobraflex_ppo_newcam_complex_b_42_125k_peak.zip` + augmented `…/ppo_newcam_complex_b_42/metadata.json` (peak block).  
**Phase:** track 'E' (camera) — multi-seed (GE3)  
**Gate context:** none (training-side comparison; no H/SR/C/M touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Second camera seed (**42**) trained on complex_b; like seed 2024 it collapses late
(by ~410k) by exploration contraction → **checkpoint-on-peak** (`ep_rew_mean` 720,2
@ ~120k; rescued checkpoint `num_timesteps == 124928`, hash `bc7e3d17…`, placed in
its `checkpoints_peak/`; metadata augmented with the peak block). Built the **E-track
multi-seed table** in §7.5.3 on the F-track battery {2024, 42, 23, 666, 123}: seed 2024
fully filled (training + nominal eval), seed 42 training-side filled with **eval columns
TBD** (Gazebo), seeds 23/666/123 TBD. Generated the E-track multi-seed figure (Fig. 7.8,
`_newcam`) from the two seeds' learning curves cropped to their healthy regions
(2024 ≤450k, 42 ≤400k). The F-track multi-seed table/figure are kept as the baseline.

### Rationale

User ran seed 42 and asked for the F-track-style seed comparison with the table prepared
ahead of the remaining 3 seeds. Both camera seeds crashing late corroborates that the
camera-PPO instability is **seed-general** (a track finding, §7.4.3), not a 2024 fluke.

### Impact

Training-side only: peak height/timing vary by seed (2024: 822,9 @ ~297k; 42: 720,2 @
~120k); both are **constraint-respecting in safety during training** (C-01/C-03 ≈ 0, only
C-06). Seed 42's basin is **tentative pending its eval**. Remaining (Ubuntu): nominal evals
for seed 42 + seeds 23/666/123, then complete the table. No verdict changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** Figure via
`tools/plot_f3_figures.py --seed-runs` on truncated copies; seed-42 peak verified
(`num_timesteps == 124928`, seed 42).

---

## [22.06.2026] — GE4-on-297k campaign wiring (host-independent prep) + complex_b scenario scaffold

**Document(s) affected:** `tools/run_campaign.py` (new `--model-path`, `--scenario-dir`; `resolve_config_path`; `execute_run` now passes `centerline`/`road_centerline`/`world_name` from each scenario's `track`), `src/cobraflex_rl/launch/eval_scenario_batch.launch.py` (new `centerline`/`road_centerline`/`world_name` launch args → eval_policy). New: `scenarios_complex_b/` (24 scenario drafts + README). `tools/plot_f3_figures.py` was extended earlier the same day.  
**Phase:** track 'E' (camera) — pre-GE4 readiness  
**Gate context:** none (campaign tooling + draft scenarios; no H/SR/C/M identifiers touched; no verdict)  
**Author:** Samuel Sanchez  

### Change

Did the **host-independent** prep to run the GE4 campaign on the complex_b 297k E-main.
The campaign launch path now plumbs complex_b geometry end-to-end (it previously passed
only `world`, leaving eval_policy on the oval centerline with no road-centerline/world_name).
Added `--model-path` (point at the gitignored 297k peak) and `--scenario-dir` (select a
scenario set). Scaffolded `scenarios_complex_b/` — the 24 scenarios with their `track`
block re-pointed to complex_b (world, world_name, complex_b centerlines), **ICs copied
from the oval and loudly flagged as needing validation** (start_s_m semantics,
`straight_completed`/timeout, perturbation timing; SC-PERT-09/10 have no complex_b wet/worn
world). The **oval `scenarios/` set is untouched** (frozen F4 / 139k evidence).

### Rationale

User: "do everything you can here; I'll switch to Ubuntu later." The policy + 297k checkpoint
+ nominal eval were ready, but the campaign was built for the oval and the 297k is a complex_b
policy — so the launch plumbing, checkpoint flag, and a complex_b scenario set were the
blockers reachable from the Windows host.

### Impact

`--dry-run` against `scenarios_complex_b` builds the **1660-run** matrix and the D-29
feasibility cleanly; SR-012/013/014 show the **same** coverage GAPs as the 139k campaign
(SC-PERT-07/08/09/10 at 20<25 runs/family — pre-existing, not new). **Remaining for Ubuntu:**
validate/adapt the per-scenario ICs for complex_b geometry, provide complex_b wet/worn worlds
(SC-PERT-09/10), then run. No campaign verdict changed (still the 139k in docs/07 + §8.9).

### Verification

`python -m py_compile` on `run_campaign.py` + `eval_scenario_batch.launch.py` (OK);
`run_campaign.py --scenario-dir scenarios_complex_b --dry-run` builds the matrix (1660) +
feasibility; `python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [22.06.2026] — Manuscript pivot: track 'E' (camera) made primary, track 'F' kept as baseline; ch.7 rewritten + E figures

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (full rewrite → E-primary, F baseline, §7.7 folded into the body, complex_b 297k results in the §7.2–7.6 structure), `chapter_01_introduction.md` (§1.6.3 scope/abstractions → perception in scope, two geometries), `chapter_03_methodology.md` (§3.5.1 D-41 framed as primary; **D-42→D-43** fix), `chapter_04_safety_analysis_and_requirements.md` ("track paralelo" → primary), `docs/00_v_model_adapted.md` ("Track 'E' (primary)" reframe + staleness fix: D-42→D-43, H-12, SR-014, SC list, commit prefix), `docs/09_environment_design.md` (track-framing note). New: `manuscript/figures/fig_7_1..7_6_*_newcam.png` (E-track figures).  
**Phase:** track 'E' (camera) — manuscript consolidation  
**Gate context:** none (narrative framing; no H/SR/C/M identifiers touched; no campaign verdict changed)  
**Author:** Samuel Sanchez  

### Change

Pivoted the manuscript/docs so the **end-to-end camera track 'E'** (E-main complex_b
297k) is the **primary** narrative, with the **state-vector track 'F'** kept as the
explicit **baseline / control arm** (not deleted). Chapter 7 was fully rewritten into
an E-primary chapter (camera observation, the v3 stability stack, the complex_b 297k
convergence + nominal eval vs the CV baseline) keeping the same §7.2–7.6 figure/table
structure; §7.7 was folded into the body. Generated six E-track figures from the
complex_b run + eval (`_newcam` suffix); the F-track figures are retained for the
baseline subsections. **Training figures were cropped to ≤450k** (the run collapses by
exploration after ~450k; the post-450k tail is irrelevant to the peak-297k deployed
policy and is omitted from the figures, with an honest prose note + checkpoint-on-peak
rationale). Also fixed a stale **D-42→D-43** reference in ch.3 and docs/00, and
completed docs/00's E hazard/SR/scenario lists (H-12, SR-014, SC-PERT-04..10).

### Rationale

The user's directive: track 'E' is the system of record going forward; 'F' will be
**superseded by 'E' once the GE4 camera campaign runs** (the camera eval to date is
nominal, §8.9). Centring the camera track makes the thesis reflect the actual final
system while the state-vector baseline isolates the cost of perception (E↔F delta).

### Impact

**No campaign verdict changed.** The GE4 per-SR verdicts (ch.8 §8.9, docs/07) remain the
139k campaign's — flipping them awaits the GE4 re-run on 297k (group 'C', deferred per the
"F superseded in the future" premise). The **case-study framing** in ch.1 (§1.2 nivel
concreto, OE4, A3) was reframed E-primary (group 'B', applied). The **hypothesis (§1.3
H1–H3)** and the methodological contributions (A1/A2/A4/A5) are **track-agnostic and
unchanged** — this is a methodology thesis, so its core claims do not depend on the
observation track. Shared content (ODD, hazards H-01..09, methodology) unchanged.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** Figures
regenerated via `tools/plot_f3_figures.py` on the truncated (≤450k) complex_b run. The
generator was extended (backward-compatible): `--centerline` (Fig 7.5 draws the complex_b
centerline, not the oval), `--cv-run` + cumulative arc length (Fig 7.6 RL-vs-CV with no
per-lap-`s` seam artifact), and `--track-name`.

---

## [22.06.2026] — complex_b 297k SC-NOM-01 eval done → new E-main camera policy of record

**Document(s) affected:** `docs/11_camera_rl_training.md` (header → v0.4; §8 rewritten — complex_b 297k is the E-main, 425k/139k demoted to §8.3 predecessors; eval results + RL-vs-CV table in §8.2), `docs/07_traceability_matrix.md` ("Last update" + a "policy superseded" callout on the E-track evidence block), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.9 superseded-policy callout, §8.9.4 closure item (e), §8.9.5 RL-vs-CV head-to-head closed), `CLAUDE.md` (new E-main bullet + banner 425k→297k), `experiments/sim/runs/baseline_cv_vs_rl_nominal.json` (RL complex_b arm + finding_complex_b).  
**Phase:** track 'E' (camera) — GE3 / pre-GE4  
**Gate context:** none (nominal eval evidence + state-of-record update; no H/SR/C/M touched; no campaign verdict changed)  
**Author:** Samuel Sanchez  

### Change

Ran and analysed the first SC-NOM-01 eval of the complex_b 297k peak (enforcement +
monitoring), and promoted it to the **E-main camera policy of record**, superseding the
oval 425k peak and the 139k campaign policy. Eval (seed 2024, 4400 steps, DR off,
complex_b): enforcement `rl_newcam_eval_2024_cb297k_4k4` = **4.88 laps, mean |ey| 10.9 mm,
0 emergencies, 43.5 % C-06-only**; monitoring `…_mon` = 4.89 laps, 12.9 mm, 0 emergencies.
Cage **latent in-ODD** in both modes (no C-01/02/03/05). Head-to-head on the **same track**
vs the CV baseline (`cv_ctrl_eval_newcam_4k4`, 17.2 mm): the RL agent is ≈ 37 % tighter on
mean |ey| — closing the previously-pending RL-vs-CV contrast.

### Rationale

This is the final camera state ("este es el estado final de la cámara y la anterior no").
The 297k peak predates the run's late-run exploration collapse, so the "failed" training
did not contaminate it; the eval confirms a competent in-ODD policy that beats the classical
CV baseline on the hard circuit (reversing the oval finding, where CV was more accurate) and
restores the F-track latent-cage signature (the 139k curve-apex controlled stop is gone).

### Impact

`docs/11` §8, `CLAUDE.md` status and `baseline_cv_vs_rl_nominal.json` now read 297k as the
E-main. **The GE4 per-SR verdicts are unchanged**: the 1660-run campaign in `docs/07` + ch.8
§8.9 + `experiments/sim/campaign_e/` still scores the **superseded 139k** policy — a nominal
eval is not a campaign, so no SR verdict or global `NOT SATISFIED` was rewritten. Re-running
GE4 on 297k is the open closure step (ch.8 §8.9.4 item (e); docs/07 callout). Laps are not
comparable across tracks (complex_b 19.22 m vs oval 8.79 m); the same-track CV row is the only
fair lap comparison.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** `baseline_cv_vs_rl_nominal.json`
re-validated as well-formed JSON. (No hazard/SR/cage/scenario/metric identifiers were touched.)

---

## [22.06.2026] — complex_b 1M run: 297k peak rescued, run-record reconstructed, SC-NOM-01 eval prepared

**Document(s) affected:** `docs/11_camera_rl_training.md` (header → v0.3; new §8.1 "The complex_b 1M run, 297k peak"). New artifacts: `experiments/sim/training/ppo_newcam_complex_b_2024_1M/metadata.json` (reconstructed run-record) and `…/checkpoints_peak/cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` (canonical peak, gitignored).  
**Phase:** track 'E' (camera) — GE3 training / pre-GE4  
**Gate context:** none yet (training artifact + eval prep; no verdict, no H/SR/C/M touched)  
**Author:** Samuel Sanchez  

### Change

The `ppo_newcam_complex_b_2024_1M` camera run (seed 2024, `CnnPolicy`, complex_b
circuit, v3 stability stack) was stopped manually at ≈ 662k of the 1M plan after
late-run reward decay. Generated the **missing run-record** `metadata.json`
(reconstructed post-hoc from `learning_curve.csv` + the rescued checkpoint — the
interrupted run never fired the trainer's end-of-run writer): reproducibility pins
(git commit, cage/centerline hashes, checkpoint hash `44c8e912…`, seed,
hyperparameters), `status: interrupted`, and the checkpoint-on-peak metadata
(`ep_rew_mean ≈ 822.9 @ ≈ 297k`, `ep_len ≈ 791`). Placed the operator-rescued
peak as the canonical `cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` inside
the gitignored `experiments/sim/training/ppo_newcam_complex_b_2024_1M/checkpoints_peak/`
(peak verified: `num_timesteps == 296960` in the zip). Documented the run in
docs/11 §8.1 with the concrete SC-NOM-01 eval command (enforcement + monitoring).

### Rationale

The run produced the highest camera reward yet (822.9, vs oval 425k's 335.6) but
died after the peak, so the peak must be evaluated before it can be trusted — the
user's "a ver si aunque haya fallado ese checkpoint vale". The run-record and a
traceably-named, gitignored peak are prerequisites for that eval and for the
CLAUDE.md reproducibility-metadata rule. Reward is **not** comparable across
tracks (different perimeter/geometry/reward integral), so §8.1 explicitly defers
the usability question to the eval.

### Impact

No verdict change. `docs/07`, Ch.8 §8.9 and `experiments/sim/campaign_e/` are
untouched and still report the 139k campaign — the complex_b peak is a **candidate**
pending a first nominal eval, which must run on Ubuntu 24.04 + ROS2 Jazzy + Gazebo
(it cannot be launched from the Windows authoring host). Hygiene note: the original
top-level `experiments/sim/cobraflex_ppo_lane_newcam_2024_peak.zip` (20 MB) is
**git-tracked** (committed in `24f7811f`) because `experiments/sim/*.zip` is not
ignored; the canonical copy now lives in the gitignored `checkpoints_peak/` dir, so
the top-level one can be `git rm --cached`-ed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).** (No
hazard/SR/cage/scenario/metric identifiers were touched.)

---

## [20.06.2026] — Isaac positioned in the V-Model A5 as a higher-fidelity sim-to-real bridge (Gazebo stays the verdict environment)

**Document(s) affected:** `docs/00_v_model_adapted.md` (A5 + chapter-mapping table + date), `docs/DECISIONS.md` (D-44 "Validation positioning" note), `manuscript/chapters/chapter_01_introduction.md` (outline §1.7 Ch.9 + contribution A4), `manuscript/chapters/chapter_06_implementation.md` (§6.7 transition), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.8 sim-to-real limitation). Earlier same-day: `CLAUDE.md` (phase-status axes banner), `docs/11`/`docs/13` (positioning notes + DR section + command reference), broken doc-13 link fixes.
**Phase:** track 'E' / methodology (Isaac Sim platform)
**Gate context:** none (planning/methodology framing; no H/SR/C/M identifiers touched)
**Author:** Samuel Sanchez

### Change

Updated the planning/methodology documents so the *evolving* thesis plan reflects Isaac
Sim's real role. Adaptation **A5** (Bounded Operational Validation) is re-stated as a
**graded sequence of increasing-fidelity environments**: In-simulation Validation (**Gazebo**,
the primary verdict-bearing environment, reported as *provisional principal evidence*) → a
**high-fidelity simulation bridge (Isaac Sim**, PhysX + RTX, D-44) as an intermediate rung
aimed at narrowing the sim-to-real gap → Bounded Physical Validation. The chapter-mapping
table gains an Isaac row; Ch.1 (Ch.9 outline + contribution A4), Ch.6 §6.7 and Ch.8 §8.8 carry
the same framing; D-44 gains a "Validation positioning" note.

### Rationale

The work-plan drifted: Isaac entered (D-44) but the manuscript/methodology still described a
single Gazebo→physical jump, conflating the **observation track** (F/E) and **simulator**
(Gazebo/Isaac) axes. The author's decision (2026-06-20): Gazebo is the principal objective and
carries the *provisional* verdict; Isaac is a more powerful tool toward the sim-to-real gap,
kept as **internal evidence** for now (a Gazebo checkpoint does not transfer to Isaac → an
Isaac campaign is a retrain/re-eval from scratch). If the Isaac campaign matures into the
stronger result, the thesis is re-stated with those figures as final.

### Impact

No identifiers, scenarios, metrics or cage parameters change; no campaign re-runs implied. The
E-track verdict still closes in Gazebo (docs/07, Ch.8 §8.9, `experiments/sim/campaign_e/`).
Isaac evidence, when produced, is recorded for internal valuation, not as the thesis verdict.

### Verification

`tools/check_traceability.py` → **All checks PASSED, 0 warnings** (planning-prose edits only).

---

## [19.06.2026] — In-process Isaac-Sim RL training path (D-44), decoupled from the bring-up

**Document(s) affected:** `tools/isaac_scene.py` (new), `tools/isaac_train.py` (new), `tools/isaac_ros2_bringup.py` (refactored), `src/cobraflex_rl/cobraflex_rl/isaac_interface.py` (new), `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (import decouple), `docs/13_isaacsim_urdf_import.md` (retitled "Isaac Sim utilities" + in-process training section), `docs/14_isaacsim_handover_spec.md` (§3), `docs/DECISIONS.md` (D-44), `CLAUDE.md` (doc-13 label)
**Phase:** track 'E' / F-track tooling (Isaac Sim platform)
**Gate context:** none (RL training enablement; no H/SR/C/M identifiers touched)
**Author:** Samuel Sanchez

### Change

Added the **in-process** Isaac-Sim RL training path (option 2 of the Gazebo→Isaac
migration), and decoupled it from the ROS2 bring-up command:

1. **`tools/isaac_scene.py`** (new) — the shared physics scene builder (URDF→USD import,
   generated track geometry, robot spawn, wheel velocity drives + low-friction
   wheel/ground materials) extracted from the bring-up. Single source of the drivetrain
   constants (`WHEEL_RADIUS`/`WHEEL_SEPARATION`/`WHEEL_JOINTS` order, `WHEEL_SCRIPT`) and
   the Lane Cam spec. All `omni`/`pxr` imports are deferred into functions so importing
   the module is safe before `SimulationApp` exists.
2. **`tools/isaac_ros2_bringup.py`** — refactored to import the scene from `isaac_scene`;
   keeps only the ROS2-bridge graph, sensor publish graphs and the free-run loop. `build_scene`
   is now `build_world()` + `add_sensors()`. Observed behaviour unchanged.
3. **`isaac_interface.py`** (new) — `IsaacSimInterface` duck-types the surface
   `GazeboLaneEnv` calls but drives the live Isaac `World` directly: per-episode reset =
   `set_world_pose` + zeroed velocities; actuation = wheel `ArticulationAction`; advance =
   `world.step()`; pose/speed from the articulation root (ground truth); Lane Cam via a
   Replicator `rgb` render product (RGBA→BGR).
4. **`isaac_train.py`** (new) — entry point: `SimulationApp` → shared scene (no ROS bridge)
   → Lane Cam render product → `IsaacSimInterface` → `GazeboLaneEnv` → SB3 PPO. Reuses the
   existing `config/train_ppo*.yaml`, callbacks and reproducibility metadata
   (`platform: sim-isaac`).
5. **`gazebo_lane_env.py`** — the lone hard `rclpy` coupling (the `RosGazeboInterface` type
   import) moved under `TYPE_CHECKING`, so the env imports on the Isaac host without `rclpy`.

### Rationale

RL training's `reset()` teleports every episode via `gz service set_pose` (Gazebo-only);
the bring-up exposes no Isaac equivalent, so training could not respawn episodes against
it. Driving the gym env in-process against the `World` removes the blocker, is the standard
Isaac-Lab-style pattern (no ROS↔gz bridge, no `gz` CLI per reset), and lets training and the
bring-up evolve independently. Sharing the scene keeps the trained-policy kinematics
identical to the deployment/demo path. See D-44.

### Impact

No hazard/SR/scenario/metric tables touched; `experiments/` and `docs/07` unchanged. The
GE4 425k re-run (CLAUDE.md §8.9, host-deferred) can now train/eval on Isaac via this path
once host-validated. The bring-up's cached `isaac_usd/` is still stale (ZED stereo switch)
— re-import with `BRINGUP_REIMPORT=1` on first Isaac run.

### Verification

`python -m py_compile` passes on all four new/edited Python files; an rclpy-stubbed import
check confirms `cobraflex_rl.gazebo_lane_env` no longer pulls `rclpy` (it now fails only on
the absent `gymnasium`, not on `rclpy`). **Not yet run on Isaac** — this host is Windows
(no Isaac); the live `world.step`/`set_world_pose`/Replicator flow and SB3-in-Isaac-python
are deferred to the Ubuntu + Isaac host. `tools/check_traceability.py` unaffected (no
identifier changes).

---

## [19.06.2026] — Isaac bring-up synced to the ZED Mini stereo pair (+ obsolete-frame cleanup)

**Document(s) affected:** `tools/isaac_ros2_bringup.py`, `tools/isaac_import_check.py`, `src/cobraflex/urdf/cobraflex_isaac.urdf` (regenerated), `docs/13_isaacsim_urdf_import.md`, `docs/14_isaacsim_handover_spec.md`
**Phase:** track 'E' tooling (Isaac Sim platform)
**Gate context:** none (auxiliary platform tooling)
**Author:** Samuel Sanchez

### Change

The Gazebo robot's front camera became a **ZED Mini stereo pair** (commit
`412e2a1f`, `zedm_left_camera_frame` / `zedm_right_camera_frame`, topics
`camera/{left,right}/{image_raw,camera_info}`), and the Lane Cam's info topic
moved to `camera/camera_info`. The Isaac path still wired the **old mono ZED**
(`camera_link_optical` → `camera/image_raw`). Brought it in line:

1. **`isaac_ros2_bringup.py`** — `CAMERAS` now publishes the ZED stereo pair on
   the `zedm_*_camera_frame_optical` frames + the Lane Cam on `camera/camera_info`,
   matching `robot.gazebo` / `config/gz_bridge.yaml`. New `BRINGUP_ZED=0` drops the
   (non-RL) stereo pair to halve camera render cost; `BRINGUP_REIMPORT=1` forces a
   URDF→USD re-import so the stale cached `isaac_usd/` is not silently reused.
2. **`cobraflex_isaac.urdf`** — regenerated camera section: old `camera_link` /
   `camera_link_optical` replaced by the zed-macro expansion (`zedm_camera_link`
   → `zedm_camera_center` → `zedm_{left,right}_camera_frame` + opticals). 13→17
   links, 12→16 joints.
3. **`isaac_import_check.py`** — `EXPECTED_LINKS` updated to the 17-frame set;
   frame-count message de-hardcoded.
4. **docs/13, docs/14** — sensor/topic/frame tables updated; empirical "Verified"
   blocks caveated as the pre-stereo (mono) import.

### Rationale

The Isaac bring-up's contract is "same ROS2 nodes as Gazebo, unchanged." After the
stereo switch the Isaac camera frames/topics no longer matched Gazebo or the bridge,
so any node (or RViz) keyed to the new names saw nothing on the Isaac side. The
generated Isaac URDF and the import smoke-test still referenced the deleted mono
frames — orphaned artifacts that would fail the import check.

### Impact

`cobraflex_isaac.urdf` was regenerated **by hand** on the Windows host (the canonical
`tools/build_isaac_urdf.py` needs `xacro` + a sourced ROS2 workspace, i.e. Ubuntu);
re-run it on the Ubuntu host for the byte-canonical file. The committed
`src/cobraflex/urdf/isaac_usd/` USD package is from the mono URDF and is now **stale**
— re-import on the Isaac host (`BRINGUP_REIMPORT=1` or delete `isaac_usd/`) before the
bring-up shows the ZED frames. No H/SR/C/SC/M identifiers touched. Lane-cam info topic
rename is safe: no RL/CV consumer subscribes to it (they read `camera/image_raw_lane`;
`lane_keeper_node` publishes its own `/lane/camera_info`).

### Verification

URDF re-validated (Python ElementTree): well-formed, single root `base_footprint`,
17 links / 16 joints, 4 continuous wheel joints, 6 `zedm_*` frames, every joint
parent/child resolves. `tools/check_traceability.py` unaffected (no ID changes).
Isaac-side runtime (import check + live `ros2 topic list`) is **deferred to the Ubuntu
+ Isaac host** — not runnable on this Windows machine.

---

## [19.06.2026] — CV baseline re-run on complex_b + Lane Cam (authoritative); PolylineTracker lap-seam fix

**Document(s) affected:** `docs/12_cv_lane_keeper.md` (v0.4), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.9.5), `experiments/sim/runs/cv_ctrl_eval_newcam_4k4/summary.json`, `experiments/sim/runs/baseline_cv_vs_rl_nominal.json`, `src/cobraflex_rl/cobraflex_rl/polyline_tracker.py`, `policy/tests/test_polyline_tracker.py`
**Phase:** Track 'E' (camera) — GE4 baseline
**Gate context:** before GE4 (425k) re-run
**Author:** Samuel Sanchez

### Change

The CV control baseline was re-evaluated on the **complex_b** circuit with the **Lane
Cam** (IMX219-160, 640×360) — the track + camera the RL camera agent will be scored on
— and is now **the** authoritative control reference for the RL agent. All earlier oval
CV results (`cv_ctrl_eval_2024_4k4{,_mon}`) are **superseded**. Authoritative numbers
(SC-NOM-01, seed 2024, 0.2 m/s, enforcement, run `cv_ctrl_eval_newcam_4k4`):
**4.85 laps, mean |ey| 17.2 mm, max |ey| 57.3 mm (< d_max=160), mean |epsi| 0.025 rad,
0 emergencies, 0.09 % cage intervention (4× C-02).**

Fixed a `PolylineTracker` lap-seam bug: a closed circuit whose generator left the seam
point un-duplicated (complex_b right-lane: first–last gap 0.060 m vs 0.052 m mean
segment) was mis-detected as *open*, so the stateful nearest-segment search could not
wrap at the start/finish line and `ey` exploded from lap 2 on. The tracker now
auto-closes loops whose endpoints sit within ~one segment; regression tests added.

### Rationale

The new-cam run's original `summary.json` reported 1.68 m mean |ey| and 1.73 laps — a
scoring artifact, not a controller failure: the CV-perceived error (`cv_ey`) stayed at
~14 mm throughout and true nearest-distance-to-centreline (recomputed from logged pose)
was 2–42 mm. The cause was the lap-seam wrap bug above. Writing the artifact numbers
into the thesis as the baseline would have been wrong.

### Impact

The eval was **re-run live** on complex_b with the fixed tracker in place (headless,
seed 2024, 0.2 m/s); the native `summary.json` (laps 4.847, mean |ey| 17.25 mm, max
57.3 mm, 0 emergencies, 0 % cage) matches an offline re-derivation from the pre-fix
logged pose to 4 decimals — the canonical `cv_ctrl_eval_newcam_4k4/` now holds this
clean run. The F-track oval is exactly closed (gap 0) and **unaffected**: F4 results
stand. The RL-vs-CV head-to-head on complex_b is **pending** the RL camera eval on the
same track (prepared + dry-run-validated, not yet launched). Full pytest: 457 passed.

### Verification

`python3 -m pytest -q` → 457 passed (incl. 3 new tracker regression tests). Live re-run
(`ros2 launch cobraflex_rl eval_cv_controller.launch.py`, complex_b) reproduces the
metrics; cross-checked against stateless global point-to-segment projection.

---

## [18.06.2026] — CV baseline: pure-pursuit control + monocular curvature boundary; complex_b softened to an "M"

**Document(s) affected:** docs/12 (§3, §4.5, §4.7 new, version log); `scripts/generate_complex_track.py`; `src/cobraflex_rl/config/complex_b_centerline.yaml` + `complex_b_right_lane_centerline.yaml`; `experiments/sim/tracks/complex_b/*`; `cv_lane_controller.py`, `cv_lane_estimator.py`, `gazebo_lane_env.py`, `eval_*`; `policy/tests/test_cv_lane_estimator.py`.
**Phase:** E (track 'E', GE4 prep)
**Gate context:** before GE4 re-run
**Author:** Samuel Sanchez

### Change

Two coupled changes from debugging the CV baseline's false cage emergencies on curves:
1. **Control law → pure-pursuit** (`CVLaneController`): aim at the lane-centre point at look-ahead `L=0.40 m`, command `v·2·y_L/(L²+y_L²)`. Replaces PD + curvature-feedforward, whose FF relied on an unrecoverable monocular curvature estimate and under-steered tight curves. Estimator now exposes `center_coeffs`; cage heading is a short near-field secant (`heading_window_m=0.15`).
2. **Curvature boundary documented** (docs/12 §4.7) as a scenario-design frontier, and **`complex_b` softened**: top 3-curve serpentine → 2-hump "M" (middle hump removed), `R_min 0.43 → 0.86 m` (driven right-lane 0.97 m). Regenerated centerline, right-lane offset, and road texture.

### Rationale

The cage reads `epsi` from the monocular CV estimator (D-43); on a curve the near-field heading over-reads `≈ κ·0.225`, exceeding C-02's `theta_max` (0.4363) and latching false emergencies while the car tracked to mm. Curve-induced apparent heading and a real heading fault are indistinguishable in the near field, so it cannot be corrected without blinding the cage to genuine faults (verified). The limit is therefore a perception cost (the central track-'E' finding vs the F-track) and a frontier: keep driven-lane `R ≳ 0.9 m`. complex_b at `R_min≈0.43 m` was far past it.

### Impact

complex_b geometry changed → any prior complex_b runs are superseded; re-run the CV baseline (and the RL camera eval, which shares the track) on the new geometry. No H/SR/C/M identifiers added or changed. The RL camera checkpoint was trained on the old complex_b distribution — a retrain/eval check on the softened track is advisable.

### Verification

`pytest` green (454). `tools/check_traceability.py` unaffected (no ID changes); to be re-run before the gate.

---

## [16.06.2026] — Isaac Sim import + ROS2 bring-up of cobraflex (docs/13)

**Document(s) affected:** `docs/13_isaacsim_urdf_import.md` (new), `tools/build_isaac_urdf.py` (new), `tools/isaac_import_check.py` (new), `tools/isaac_ros2_bringup.py` (new), `src/cobraflex/urdf/cobraflex_isaac.urdf` (new, generated)
**Phase:** track 'E' tooling
**Gate context:** none (auxiliary platform tooling)
**Author:** Samuel Sanchez

### Change

Added a one-shot path to import the cobraflex robot into Isaac Sim. The sim robot
(`my_robot_gazebo_mesh.urdf`) is a xacro depending on two external files
(`inertial_macros.xacro`, kept; `robot.gazebo`, Gazebo plugins/sensors, dropped)
plus `$(find …)` substitutions Isaac cannot resolve. `tools/build_isaac_urdf.py`
expands the xacro, strips every `<gazebo>` block, rewrites mesh paths to relative
`../meshes/*.stl`, and removes the schema-invalid empty visual/collision on
`base_footprint`, emitting the flat `cobraflex_isaac.urdf`.

### Rationale

Isaac's URDF importer ignores Gazebo tags but rejects ROS substitutions, xacro
macros and geometry-less visual/collision elements; a single self-contained URDF
makes the import deterministic and ROS-independent.

### Impact

No effect on the Gazebo stack or any F-/E-track evidence — the source xacro is
untouched and the F2 ROS2 launch still uses it. New artifact is re-derivable
(do not hand-edit). The generated `isaac_usd/` USD package is build output.

### Verification

`check_urdf` parses the flat URDF (13 links, 12 joints). Headless import on
Isaac Sim 6.0.0-rc.59 (`tools/isaac_import_check.py`) → **PASS**: articulation
root present, all 13 link frames present (9 rigid bodies + 4 massless Xform
frames), 8 mesh prims, 4 wheel joints as `RevoluteJoint`.

### Follow-on — ROS2 bring-up (Gazebo → Isaac transition)

`tools/isaac_ros2_bringup.py` reproduces the Gazebo topic contract via the Isaac
ROS2 Bridge + an OmniGraph Action Graph, so the existing ROS2 nodes (lane
perception, PD baseline, safety cage, vehicle control, `teleop_twist_keyboard`)
run unchanged. Subscribes `/cmd_vel`; publishes `/clock`, `/odom`, `/tf`,
`/joint_states`. Drive train: ScriptNode diff-drive kinematics → 4-wheel
`IsaacArticulationController`; the script also adds stiffness-0/high-damping
velocity drives to the wheel joints (PhysX needs them — the imported `continuous`
joints have no gains). IMU/lidar/cameras are left for later (added in-engine, not
via URDF). **Verified**: `--test` commands the wheels → base translates 3.33 m
(`[RESULT] PASS`); live `ros2 topic info /cmd_vel` shows Subscription count 1 with
`/clock /odom /tf /joint_states` advertised. See docs/13 §"Driving it over ROS2".

**Physics calibration (skid-steer turning):** the 4-wheel skid-steer barely
turned because PhysX grips laterally harder than Gazebo's ODE (the URDF's
`mu1=mu2=0.8` were `<gazebo>` tags, dropped for Isaac). Fix: lower wheel+ground
friction (`combine="min"`, bound to the wheel collider prims + explicit ground
material). Measured yaw vs a 2.9 rad/s test command: f=0.5→0.09, 0.1→0.26,
0.05→0.53 rad/s; default `WHEEL_FRICTION=GROUND_FRICTION=0.05` (env-tunable).
Genuine trade-off (lower friction turns better, slips more on straights). See
docs/13 §"Physics tuning".

**Sensors:** `add_sensors()` creates the two cameras + an RTX 2D lidar in-engine
and publishes them on the Gazebo topics (`camera/image_raw`(+`_lane`) + camera_info,
`scan`) so perception nodes consume them unchanged. USD Camera per optical frame
(180°-about-X, focal from hfov → matching intrinsics); `IsaacSensorCreateRtxLidar`
(`Example_Rotary_2D`). Sensors render off-screen so the run loop renders each frame
(skipped in `--test`/`--turn`; `BRINGUP_SENSORS=0` to disable). **Verified**:
`ros2 topic list` shows all five sensor topics; `/camera/image_raw_lane` echoes
640×360. Lidar uses the shipped SLAMTEC **`RPLIDAR_S2E`** profile (near 0.05 m,
10 Hz, 360° 2D) — the initial `Example_Rotary_2D` only detected from 1 m. Override
via `LIDAR_CONFIG`. See docs/13 §"Sensors". (RTX lidar /scan only streams with the
GUI viewport rendering — not in `--headless` probes.)

**Complex track:** `scripts/generate_complex_track.py` builds a closed
Catmull-Rom circuit (both turn handednesses, radii ~0.4–5 m) as a top-down road
texture matching the Gazebo road look (black asphalt, 1 cm white solid edges,
10/10 cm dashed centre, 0.52 m wide) + a `_centerline.yaml` (cage/perception schema)
+ `_meta.yaml`. The bring-up `add_track()` loads it as a textured ground quad
(`TRACK=complex_a`, default) and spawns the robot at the start line; `--shot <png>`
renders a headless top-down check. **Verified**: texture binds + renders in Isaac
(green off-road, dark asphalt, white markings). See docs/13 §"Track".
`scripts/track_to_gazebo_world.py` also emits a Gazebo `.world`
(`src/cobraflex/worlds/lane_following_complex_a.world`, one textured box reusing the
oval-world plugin/ground/sun template + box-UV convention) to test the camera-CV PD
lane keeper on the complex curves. PD is kinematically capable (min track radius
0.40 m > PD min 0.22 m at v=0.20, ω_max=0.90).

**IMU + ground-truth odometry:** `imu_link` now carries an `IsaacImuSensor`
(`IMU.create`) → `IsaacReadIMU` → `ROS2PublishImu` on `/imu`; and a second
`ROS2PublishOdometry` off the same (truth-reading) `IsaacComputeOdometry` publishes
`/odom_truth` — mirroring the Gazebo OdometryPublisher RL training used. **Verified**
(rclpy sensor-QoS): `/imu` lin-acc.z ≈ 9.81 at rest, `/odom_truth` reports pose.

**RViz (Gazebo-style):** Isaac's `ROS2PublishTransformTree` is now **off by default**
(`BRINGUP_ROBOT_TF=1` to re-enable) — it rejects the massless `base_footprint` and
skips the empty `*_optical` frames (the image `frame_id`s), giving a broken tree.
Instead `robot_state_publisher` owns the robot TF (URDF + Isaac `/joint_states`,
incl. `base_footprint` + optical frames) and Isaac publishes only
`odom → base_footprint`. `/clock` verified monotonic (single publisher, 60 Hz).
RViz works exactly as with Gazebo: rsp + rviz + `use_sim_time:=true`, Fixed Frame
`odom`. See docs/13 §"RViz".

---

## [15.06.2026] — Track 'E' fair baseline: logical CV+PD camera controller vs RL agent (§8.9.5)

**Document(s) affected:** `manuscript/chapters/chapter_08_experimental_evaluation.md` (new §8.9.5). Code: new `cobraflex_rl/cv_lane_controller.py` (shared), `cobraflex_rl/eval_cv_controller.py` + `eval_cv_controller.launch.py` (+ entry point), rewrite of `cobraflex/lane_keeper_gazebo_node.py` to use it (+ `cobraflex`→`cobraflex_rl` exec_depend). Evidence: `experiments/sim/runs/cv_ctrl_eval_2024_4k4{,_mon}`, `baseline_cv_vs_rl_nominal.json`.
**Phase:** E4 (evaluation baseline).
**Gate context:** before G4-cámara; supports the RL-vs-classical comparison.
**Author:** Samuel.

### Change

Added a **logical (non-learned) camera lane-keeper** as the fair baseline for the RL camera agent — the F-track PD reads ground truth, so it can't fairly oppose a real-perception policy. The new controller reuses the cage's calibrated CV lane estimator (D-43; metric ey/epsi/curvature) with a PD + curvature-feedforward law (`steer = -(kp·ey + kd·epsi) + kff·v·κ`), shared by the deployment node and the scored eval (run through the same `GazeboLaneEnv` as `eval_policy`). The original histogram pure-P node is superseded: its uncalibrated "lane centre = image centre" set-point could not hold the lane above ~0.1 m/s.

### Rationale

A meaningful RL claim needs a same-input, same-scoring classical reference. Result on SC-NOM-01 (seed 2024, 0.2 m/s, 4400 steps): CV+PD M-P1 RMSE **10.5 mm** vs RL **14.2 mm**, max|ey| 20.5 vs 56.7 mm, both 0 emergencies, ~11 laps. Cage intervention **0.6–0.9 %** (CV+PD) vs **82–86 %** (RL, C-06 rate-limiting the CNN's jerky steering). Conclusion: nominal accuracy does **not** favour the RL agent — both pass the requirement; the RL value must show up under perturbation/appearance-shift (robustness-world study).

### Impact

No safety-artifact change. New code only; `cobraflex` now exec-depends on `cobraflex_rl` (no cycle — cobraflex_rl does not import cobraflex). The GE4 campaign (§8.9, 139k) is unaffected. Next: run the baseline on the robustness worlds + perturbed scenarios.

### Verification

Both eval arms completed (exit 0), 4400 steps, run dirs + metadata written. `python tools/check_traceability.py`: PASS (no ID graph change).

---

## [15.06.2026] — Track 'E' camera switch + 750k retrain: new 425k_peak checkpoint, nominal eval

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md` (new §7.7.8); `CLAUDE.md` (Track 'E' phase status). No hazard/SR/scenario/metric tables touched.
**Phase:** E4 (post-GE4; new training arm, pre-campaign).
**Gate context:** before G4-cámara (GE4 already documented with the 139k checkpoint; this is the superseding training arm).
**Author:** Samuel.

### Change

Documented the camera switch and extended retrain on track 'E':

1. **Camera switch** (code already committed, commits `226cf129`/`5a3fd790`/`d6d2a76b`): policy and cage CV estimator re-pointed to a dedicated *Lane Cam* (IMX219-160 mirror, 640×360, HFOV ≈ 90°) mounted 5 cm lower at the body front (`camera_geometry` defaults h ≈ 0.077 m, pitch 0.25 rad). The 139k checkpoint's observation distribution no longer matches → retrain from scratch.
2. **New main run** `ppo_newcam_train_2024_750k` (seed 2024, `CnnPolicy`, DR p=0.5 level 0.2–0.8, 750k steps): `ep_rew_mean` peaks at **335.6 @ ≈424,960** (`ep_len_mean` 347), above the old `cam` 200k peak of 288.5; degrades to ~256 by 750k without recovery (same late-instability signature → checkpoint-on-peak).
3. **New E-main checkpoint** selected: `cobraflex_ppo_newcam_lane_2024_425k_peak.zip` (hash `953ba930…`).
4. **Nominal closing eval** (SC-NOM-01, seed 2024, 4400 steps, DR off): enforcement `rl_cam_eval_2024_425k_4k4` = 11.16 laps, mean |ey| 12.4 mm, **0 emergencies**, interventions C-06 (+5× C-02); monitoring `…_4k4_mon` = 11.17 laps, 12.7 mm, 0 emergencies, C-06 only.

### Rationale

The 139k checkpoint (§7.7.7, GE4 §8.9) carried a real availability cost — a stochastic SR-014/Trigger-8 controlled stop at the curve apex (4.69 laps in the official rep). The lower, dedicated Lane Cam plus a longer training budget **removes that stop**: 11+ laps and 0 emergencies in both modes, |ey| at F3 state-parity, cage latent in-ODD (M-S2 = 0 nominal) like the F-track. The 425k checkpoint supersedes 139k as E-main.

### Impact

§8.9 (GE4 campaign) **still reports the 139k campaign** — the 1660-run E-campaign with the 425k checkpoint is prepared and dry-run-validated but **not yet re-executed** (≈16–17 h wall, single-seed — corrected 19.06 from an earlier ≈220 h guess that was never derived; measured from the completed 139k E-campaign: 1660 runs in 16.5 h, ~31 s/run. N=5 multi-seed ≈ 80–85 h). `docs/07` E-track verdicts and the `campaign_e/` artifacts remain those of the 139k run until the re-run lands. New checkpoint binary is gitignored (not tracked); sync manually. No traceability-graph change.

### Verification

Docs-only change (manuscript + CLAUDE.md). `python tools/check_traceability.py`: **PASS** (no ID graph change).

---

## [12.06.2026] — Repo-wide English documentation pass + NumPy 2.0 compatibility fix

**Document(s) affected:** No living `docs/` content. Code only: `cage/` (cage_node, logger, rules C-01..C-06, base types), `src/cobraflex_rl/` (env, ROS interface, trainer, eval, perception/criterion/campaign modules, ROS2 nodes), `src/safety_cage/cage_ros_node.py`, `src/cobraflex/` legacy nodes, `policy/baseline_pd.py`, `tools/` (campaign/traceability/calibration/plot scripts), `scripts/`, `cage/ros2/` loggers, `policy/tests/test_camera_pipeline.py`.
**Phase:** E4 (chore; F-track artifacts untouched in behaviour).
**Gate context:** after GE4 campaign close; no verdict-bearing artifact re-run required.
**Author:** Samuel.

### Change

1. **English docstrings/comments where missing** (~150 docstrings): module docstrings for `gazebo_lane_env`, `ros_interface`, `train_ppo`, `callbacks`, `rewards`, `polyline_tracker`, `cobraflex_rl/__init__` (lazy-import rationale); class/function docstrings across the cage rules, ROS2 nodes, campaign tooling and scripts. Stale `cage/cage_node.py` module docstring corrected (the ROS2 wrapper lives in `src/safety_cage/`, not a future `cage/ros2/`). Spanish figure labels in `tools/plot_*` kept — they are manuscript-facing text (thesis in Spanish).
2. **NumPy 2.0 compatibility:** `cv_lane_estimator.py` used `ndarray.ptp()` (removed in NumPy 2.0) in three places → `np.ptp(...)`; identical numerics on NumPy 1.x.
3. **Host-portable tests:** the five `camera_pipeline` tests that need OpenCV now `skipif` when `cv2` is absent (Windows manuscript host) instead of failing; they still run on the Ubuntu sim host.

### Rationale

Reviewer-facing readability: the safety argument leans on the code being auditable; several core modules (RL env, ROS interface, PPO trainer) had no module docstring and many public APIs were undocumented. The `.ptp()` failures masked the real suite signal on NumPy ≥ 2 hosts (24 spurious failures).

### Impact

No behavioural change (docstrings/comments only, plus the equivalent `np.ptp` call). No re-runs required; F4/E4 campaign artifacts remain valid.

### Verification

`pytest` (cage/tests + policy/tests + tools/tests): **435 passed, 5 skipped** (cv2-gated on this host). `python tools/check_traceability.py`: **PASS, 0 warnings**.

---

## [12.06.2026] — E4/GE4: track-'E' camera evaluation campaign closed — global `NOT SATISFIED`, dominated by safe controlled stops; the cage flips latent → active under the camera

**Document(s) affected:** `experiments/sim/campaign_e/` (verdict-bearing roll-up `campaign_report.json` + `campaign_runs.csv`, **1660 runs**; committed E4 "Cam eval part 1/2"). New `tools/campaign_e_failure_modes.py` + `experiments/sim/campaign_e/failure_mode_breakdown.json` (pure-Python clause-level failure classification + cage core-safety invariants + F4↔E contrast). `docs/07_traceability_matrix.md` (E-track SR-012/013/014 verdicts + an "E-track sim evidence" block). `manuscript/chapters/chapter_08` §8.9 (camera-campaign results, Spanish; synthesis renumbered → §8.10) + §7.7.7 forward-ref + appendix ticks. `CLAUDE.md` (phase snapshot).
**Phase:** E4 (track 'E').
**Gate context:** GE4 (sim evaluation of the camera track). The F-track G4 verdict (`SATISFIED`, §8.1–§8.9) stays **frozen** as the ground-truth-state baseline; this is the parallel camera arm ("what does camera perception cost").
**Author:** Samuel.

### Change

E-campaign executed on the dedicated machine (commit `ae8b7c6b`, seed 2024, checkpoint `cobraflex_ppo_cam_lane_2024_139k_peak.zip` @ `263926…`, cage 0.6.1 @ `4287fe…`): **1660 runs**, 24 scenarios × {enforcement, monitoring}, every E-track scenario (SC-PERT-04..10, SC-FRONT-01..06) plus the full F-track library re-run through the camera stack; **0 executor errors**.

**Global verdict `NOT SATISFIED`** (D-30): three SR-CL-A vetoes — **SR-001, SR-012, SR-014** — plus **SR-013** held INCOMPLETE by D-29 under-coverage. The breakdown (`failure_mode_breakdown.json`) shows the vetoes are concentrated in **two** scenarios and are **safe controlled stops, not lane breaches**:

- **SC-EDGE-02** (near-edge recovery, F-track): enforcement 17/30 (**0.567**), down from **1.0 in F4**. All **13/13** enforcement fails are *emergency-only* — M-S1 < d_max, no road-edge contact, the only failing clause is `emergency == False`. The camera-derived state at the spawn offset (|ey| = 0.12 m, at d_warning) trips the cage's controlled stop where the F4 ground-truth policy recovered smoothly. → vetoes **SR-001**.
- **SC-PERT-04** (camera glare, E-track): enforcement 20/40 (**0.500**). All **20/20** fails are *emergency-only* (the glare-0.6 arm: percept degrades enough to raise the Trigger-8 / compound-state stop). → vetoes **SR-012** and, as a secondary scenario, **SR-014**.

**Cage core-safety invariant held under the camera** (all 830 enforcement runs): **0 road-edge contacts**; M-S1 < d_max everywhere except the **9** SC-FRONT-01 cells that *spawn the vehicle exactly at d_max = 0.16 m* (deliberate out-of-ODD start, scored on road-edge contact — max M-S1 there 0.168 m, no contact); M-S2 > 0 only at those same starts. The camera never drove the system into a lane breach in enforcement — it degraded to safe stops.

**Cage flips latent → active.** In F4 the cage was *latent* in-ODD (M-S2 = 0 both modes, §8.6). Under the camera it is *active*: the noisier percept makes the SR-013 / Trigger-8 controlled stop the operative mechanism. Cleanest cage-value contrast: **SC-PERT-07** (perception loss) — enforcement **20/20 PASS** (open-loop stop fires) vs monitoring **0/20**, all 20 monitoring fails being **genuine M-S1 breaches** (without the cage the occluded policy departs). SC-PERT-10 (wet world) flips enf 0.90 / mon 0.10 on the same stop mechanism.

**Passes.** SC-PERT-06 (blur) 0.975, SC-PERT-08 (false-lane, SR-014 primary) 20/20, SC-PERT-09 (worn) 1.0, SC-PERT-10 (wet) 0.90, SC-FRONT-01..06 1.0, SC-NOM-01/02/03 ≥ 0.96, SC-EDGE-03/04 ≥ 0.96; SC-PERT-01 even flips **FAIL→PASS** F4→E (0.88 → 0.98).

**Instrumentation gaps (indeterminate, not failures; D-38 class).** SC-EDGE-05 (100) — predicate operands `joint_envelope_assertion_failures` / `inter_cycle_oscillations` absent from the record schema → SR-010 insufficient_evidence. SC-PERT-03 (40) and **SC-PERT-05** (40, NEW) — the two-arm `low:/high:` labelled criterion is not yet grouped/evaluated by the runner (`criterion_eval.evaluate_labelled` exists, unwired) → SR-009 / SR-012-coverage insufficient_evidence. **SR-006** again reads `failed` purely from the coarse `ALL`-scenario inheritance of SC-EDGE-02/SC-PERT-04 (D-39 artifact; `steer_rate_smoothness_ok` holds per-run) — CL-B, global unaffected, same flagged re-pointing follow-up as F4.

### Rationale

The campaign measures the cost of replacing the 6-D ground-truth state with an end-to-end front camera, cage and scenario library held fixed (single-trunk control arm, D-41/D-43). Honest reading: the camera does **not** breach the safety envelope in enforcement (0 edge contacts, M-S1 < d_max in-ODD) — it trades **availability** for safety, bailing to a controlled stop in the near-edge (SC-EDGE-02) and high-glare (SC-PERT-04 L0.6) cases. So `NOT SATISFIED` is a **capability/criterion verdict, not a safety breach**: the two vetoing scenarios carry an `emergency == False` clause that scores the cage's safe stop — the exact SR-013 behaviour — as a fail, even though SR-012's own stated criterion (M-S1 ≤ d_max ∧ M-S2 = 0 in enforcement) is met.

### Impact

- **SR-001 stays frozen at F4 `Satisfied`** (ground-truth state); the camera regression is reported as a *contrast*, not an overwrite. SR-012 / SR-014 → camera-track verdict `Not satisfied (track 'E', see E-evidence)`; SR-013 → scenario criterion met 20/20 in enforcement but held `INCOMPLETE` by D-29 (single scenario/family).
- **Open follow-ups** (GE4 not formally passed until ≥ a–c close): **(a)** candidate own-criterion reconciliation à la D-39 — re-score SR-012 / SR-001-camera on M-S1 ≤ d_max ∧ M-S2 = 0, treating the controlled stops as SR-013 behaviour — **flagged for decision, not applied**; **(b)** wire `evaluate_labelled` so SC-PERT-03/05 score (both look like latent passes); **(c)** inject SC-EDGE-05 grid ICs + add the two co-activation counters; **(d)** multi-seed N=5 (host-deferred).
- The §8.6 "cage contribution" thesis result gains its **in-ODD active-cage half** from the camera arm (frontier-only under F4).

### Verification

`python tools/campaign_e_failure_modes.py` regenerates `failure_mode_breakdown.json` from the per-run records (pure-Python, runs on the Windows figure host). `check_traceability.py` PASS (verdicts + prose only, no structural change).

---

## [11.06.2026] — E2/GE4-prep: E-campaign smoke 2/2 PASS on the selected checkpoint — full campaign handed off to the dedicated run machine

**Document(s) affected:** `experiments/sim/campaign_e_smoke/` (2-cell smoke: SC-PERT-04 rep00 glare-runtime-injector PASS; SC-PERT-09 rep00 worn-world via `resolve_world_path` PASS — first live Gazebo validation of the world-variant path).
**Phase:** E2 (track 'E').
**Gate context:** GE4 prep. Host policy (11.06): this machine runs only jobs ≤30–60 min; the full 400-run E-campaign and any multi-seed training run on the dedicated machine via `git pull` + `--resume`.
**Author:** Samuel.

### Change / Verification

`run_campaign --scenarios SC-PERT-04,SC-PERT-09 --modes enforcement --reps 1 --train-config train_ppo_camera.yaml --checkpoint-template 'cobraflex_ppo_cam_lane_{seed}_139k_peak.zip'` → 2/2 PASS, 0 errors; report `campaign_e_smoke/campaign_report.json` (global INCOMPLETE as expected at 2 runs). Every campaign knob exercised end-to-end: checkpoint template, camera train-config, runtime visual injector, per-scenario world selection, D-29/D-30 verdict spine.

---

## [11.06.2026] — E2/GE3: E-main 200k completed — late collapse, peak-checkpoint selection by closing eval; eval-side DR bug fixed

**Document(s) affected:** `experiments/sim/training/ppo_cam_train_2024_200k/` (learning curve, metadata, `fig_convergence.png`, `checkpoints_peak/` README + SHA256SUMS; binaries gitignored), `experiments/sim/runs/rl_cam_eval_2024_{139k,200k}_4k/` (closing evals), `src/cobraflex_rl/cobraflex_rl/eval_policy.py` (DR off in eval), `manuscript/chapters/chapter_07` §7.7.7 (full results, in Spanish), `.gitignore`.
**Phase:** E2 (track 'E').
**Gate context:** **GE3 (training) closes** with the peak-checkpoint selection; the perception-availability finding feeds GE4.
**Author:** Samuel.

### Change

- **Training:** `ppo_cam_train_2024_200k` ran to 200,704 steps. ep_rew_mean peaked at **288.5 @ 139,264**; a destructive update at 156k (approx_kl 0.227, >10× regime) collapsed the policy with no recovery (final: 56 / ep_len 76). Emergencies stayed ≤1–2% throughout — progress was lost, not safety. Peak + pre-fall step-checkpoints were rescued from the rotating shared-prefix scratch into the run dir (hashes in SHA256SUMS).
- **Closing eval** (SC-NOM-01, enforcement, max 4096 steps, DR off): peak-139k → **4.69 laps, mean |ey| 10.1 mm** (parity with F3's 9.9 mm on perfect state), one correct SR-014/Trigger-8 controlled stop at 181 s (cv_epsi spikes ≈ −0.38 rad in the curve-apex dash gaps; max excursion 37 mm, no edge contact). Final-200k → 0.23 laps, |ey| 102 mm (collapse confirmed). **Selected: 139k peak** (`experiments/sim/cobraflex_ppo_cam_lane_2024_139k_peak.zip`, honest name — campaign uses `--checkpoint-template 'cobraflex_ppo_cam_lane_{seed}_139k_peak.zip'`).
- **Eval-determinism fix:** `eval_policy` now disables `domain_randomization` from the train config — a nominal eval episode could otherwise draw a random training-envelope degradation; a harsh draw blinded the CV estimator at spawn → instant no-state-ever emergency (both first eval attempts died at step 1). The only visual stressor in eval is the scenario's own block. This also protected the whole E-campaign path.

### Rationale / Impact

D-36 precedent: checkpoint merit is measured by eval, not assumed from the curve. The CNN+DR instability vs F3's monotone convergence is a reportable track finding (§7.7.7). Open items → GE4: perception-stop rate (~1 per 5 laps nominal) quantified by the campaign; deterministic EMA smoothing of the estimator's epsi channel as future mitigation; multi-seed N=5 run-vs-deferral pending (host now restricted to ≤1 h jobs — long runs move to the second machine).

### Verification

pytest 440 passed; check_traceability PASS. Both evals re-run after the DR fix: peak drives (4.69 laps); the step-1 emergency is gone.

---

## [11.06.2026] — E2: integration merge — `main` (F4 campaign closed, G4 verdicts) merged into `e2e-camera`

**Document(s) affected:** merge of 8 `main` commits (F4 campaign close: 1260 runs, global verdict `SATISFIED`, D-38/D-39 aggregation decisions, docs/07 verdicts, ch.8) into the E-track branch. Conflict resolutions: `docs/05` (count section + executed-campaign note + Q6, both sides), `docs/07` (main's verdicts + E-track rows/note), `docs/DECISIONS.md` (both decision sets, numeric order), `docs/CHANGELOG.md` (entries interleaved by date; restored the "Anticipated defense questions" entry header that `main` had accidentally dropped), `tools/run_campaign.py` + `campaign_metrics.py` + 3 test files (main's D-38 verdict spine + branch's E-campaign knobs/`resolve_world_path`; branch-side CRLF pollution normalized to LF), `tools/traceability_matrix.csv` (main's verdict-bearing rows + 11 E-track rows, D-43 refs, un-stubbed notes), evidence reports taken from `main`.
**Phase:** E2 (track 'E'), integration.
**Gate context:** prepares the post-GE4 single-trunk convergence; `main` itself is untouched (final `e2e-camera`→`main` merge after GE4 + review).
**Author:** Samuel.

### Rationale / Impact / Verification

Single trunk going forward: the F-track results stay frozen as the ground-truth baseline (control arm for "what does camera perception cost"), the E-track continues on top. `pytest` → **440 passed** (431 branch + 9 from main's aggregation work); `check_traceability` PASS; `check_scenario_yaml` PASS.

---

## [11.06.2026] — E2: pre-merge renumber of E-track decisions D-38/D-39/D-40 → D-41/D-42/D-43 (ID collision with main's F4 decisions)

**Document(s) affected:** every living document, scenario YAML, code comment and manuscript chapter citing the E-track decisions (sed sweep, ~50 files); `docs/DECISIONS.md` (renumbered rows + mapping note).
**Phase:** E2 (track 'E'), integration prep.
**Gate context:** precondition for merging `main` (which independently allocated D-38 = indeterminate-verdict aggregation, D-39 = SR-006 own-metric during its F4 campaign close) into `e2e-camera`. No semantic change anywhere — pure ID renumber.
**Author:** Samuel.

### Change / Rationale

D-38/D-39 were allocated twice, once per branch. IDs are load-bearing in this repo (traceability commitment), so the side not yet merged renumbers: **D-38→D-41 (Track 'E' architecture), D-39→D-42 (GT-state interim, superseded), D-40→D-43 (CV lane-estimator as cage state source)**. Git history and frozen evidence artifacts (`experiments/sim/runs/cv_estimator_val_*`) keep the old numbers — the mapping note in DECISIONS.md is the bridge.

### Impact / Verification

No behaviour change (comments/docs only; `cage/cage.yaml` hash changes — comment text — without a version bump, consistent with "no functional delta"). `pytest` green, `check_traceability` PASS, `check_scenario_yaml` PASS after the sweep.

---

## [11.06.2026] — E2: eval-side world diversity — SC-PERT-09/10 (worn / wet oval textures) + campaign world selection

**Document(s) affected:** `scenarios/perturbed/sc_pert_09.yaml` + `sc_pert_10.yaml` (new), `docs/05` (two scenario sections, count 22 → 24, E-budget 320 → 400 runs, Option-A world-variant note), `docs/03` + `manuscript/chapters/chapter_04` (SR-012 / SR-014 scenario lists) → `docs/data/safety_requirements.csv` regenerated, `tools/run_campaign.py` (`resolve_world_path`; executor passes a non-default `track.world` to the launch), `experiments/sim/e_cam_visibility/world_variant_mask_check.json` (evidence).
**Phase:** E2 (track 'E').
**Gate context:** GE4 prep. Per docs/09 §10 ("oval-first"), eval-side appearance diversity is added only now — after the first camera training result (the GE3 pilot, see previous entry). F-track unaffected: F-track scenarios all carry the default world, for which the executor emits no `world:=` argument (byte-identical launch command).
**Author:** Samuel.

### Change

SC-PERT-09 (worn/patched texture) and SC-PERT-10 (wet/darkened texture) run the unchanged oval geometry/centerline with variant road textures — the **world is the perturbation** (non-runtime mechanism, SC-PERT-03 precedent; `resolve_perturbation` yields NONE for `world_variant`). The campaign executor now resolves a scenario's non-default `track.world` against the installed cobraflex share (source-tree fallback) and passes it to `eval_scenario_batch.launch.py`.

### Rationale

D-37 Option A's "identical geometry" property is preserved while testing the static appearance shift that the H-10 runtime injectors (SC-PERT-04..06, photometric) cannot represent: texture clutter. Mask evidence: line pixels stay 100% inside the estimator's white mask on both variants; road false-positives 0.32% (worn) vs 1.65% (wet) — wet is the harder clutter case.

### Impact

E-eval budget 320 → 400 runs. SR-012/SR-014 gain an appearance-shift verifying family; the per-SR verdict spine picks the new scenarios up from the regenerated SR CSV.

### Verification

`check_scenario_yaml` PASS (0 errors/warnings, docs/05 coverage included); `check_traceability` PASS; `pytest` 431 passed; campaign `--dry-run` plans the new cells; `resolve_world_path` resolves both variant worlds and raises on a missing world.

---

## [11.06.2026] — E2: camera-PPO pilot green (20k) → E-main 200k launched; `cv_lane_estimator_node` deployment wrapper (D-43 outside the gym)

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/cv_lane_estimator_node.py` (new node), `src/cobraflex_rl/setup.py` (console script), `src/safety_cage/safety_cage/cage_ros_node.py` (`/perception_invalid` → ctx, C-05 Trigger 8), `manuscript/chapters/chapter_07` (§7.7.7 pilot result). Training evidence under `experiments/sim/training/`.
**Phase:** E2 (track 'E').
**Gate context:** GE3 (training). F-track unaffected (`/perception_invalid` defaults False in ctx; Trigger 8 stays inert unless cage.yaml enables it — 0.5.x precedent).
**Author:** Samuel.

### Change

- **Pilot** `ppo_cam_pilot_2024_20k` (seed 2024, DR on, cage 0.6.1 enforcement) completed: ep_rew_mean 17.9 → 137.7, ep_len_mean 31.7 → 160.7, emergency_rate 3.1% → 0.3%, explained_variance positive throughout; interventions dominated by C-06 rate-limiting (~89%), C-01/C-05 near zero by 20k. The loop criteria of the pilot (camera obs flowing, cage interventions logged, reward sane, ~8 FPS viable) all hold.
- **E-main launched:** `ppo_cam_train_2024_200k` (200k steps, seed 2024, `train_ppo_camera.yaml`, checkpoint `policy/checkpoints/cobraflex_ppo_cam_lane_2024_200k.zip` — matches the campaign's `--checkpoint-template`).
- **`cv_lane_estimator_node`** — deployment analogue of the in-process D-43 path: camera → `CagePerceptionSupervisor` → `/state_obs` (lane_perception_node ordering; publish suppressed when no acceptable estimate, F2 missing-state precedent) + `/perception_invalid` every tick. `cage_ros_node` latches `/perception_invalid` into ctx like `/external_stop`. Found live: the node must run with `use_sim_time:=true` — wall-clock vs sim-stamped frames latches perception_invalid permanently (documented in the node docstring).

### Rationale

The pilot's job was to prove the E-training loop before spending ~7 h at RTF 1 on the main run; it did. The deployment node closes the D-43 architecture outside the gym: the same supervisor logic now feeds the F2-style five-node loop, which is what the physical platform will use.

### Impact

E-main run in progress (GE3 evidence). The F2 launch files can later swap `lane_perception_node` → `cv_lane_estimator_node` without touching the cage wrapper.

### Verification

`pytest` → 431 passed; `check_traceability` PASS. Node smoke-tested against the live sim: `/state_obs` at 10.0 Hz with plausible values, `/perception_invalid` False on nominal frames (True before the `use_sim_time` fix — caught by launching, not by tests).

---

## [10.06.2026] — E2: E-eval executor wiring + Training Spec §7.7 (manuscript) — visual stressors reach the campaign path

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/scenario_perturbations.py` (visual channel: `visual_degradation`/`perception_loss`/`false_lane` blocks → onset-timed mode/level), `gazebo_lane_env.py` (scenario visual injector with episode-clock onset), `eval_policy.py` (camera obs mode: VecFrameStack-equivalent stacking + `cv_*` perception trace in `cage_status.csv`), `train_ppo.py` (Monitor wrap in the camera path — ep_rew_mean was NaN without it), `policy/tests/test_scenario_perturbations.py` (+6); `manuscript/chapters/chapter_07` (**§7.7** Track-'E' Training Spec, in Spanish; the §7.2.1 track-E note updated D-42 → D-43), `docs/07` (E-track note: chain live, verdicts TBD until E-eval).
**Phase:** E2 (track 'E').
**Gate context:** prepares GE3 (training) and GE4 (eval campaign). F-track unaffected.
**Author:** Samuel.

### Change

- The SC-PERT-04..08 `perturbations:` blocks now resolve through `resolve_perturbation` like every F4 runtime stressor: level round-robin by rep, onset (`at_time_s`) honoured via the episode clock so SC-PERT-07/08 keep their nominal lead-in; scenario-library aliases (`misleading_markings`, `occlusion_or_dropout`) map to the degradation primitives. The env applies the stressor in the shared camera pipeline (one degradation point, both consumers — D-43).
- `eval_policy` runs camera policies (frame-stack mirror of training) and logs the per-step perception trace (`cv_ok`, `cv_state_available`, `cv_perception_invalid`, `cv_ey/epsi/confidence`) that the SC-PERT-07/08 verdicts and the Trigger-8 latency analysis need.
- Manuscript ch.7 gains **§7.7** (Spanish): observation/pipeline (84×84 gray, k=4, pitched ZEDm source), NatureCNN policy, H-10 DR envelope (eval-only modes excluded, with rationale), cage-in-enforcement with the D-43 state source and aligned budgets, hyperparameters/seeds (main seed 2024, D-36 precedent; N=5 if compute allows), logging; §7.7.7 reserved for pilot/main results.

### Rationale / Impact / Verification

Executor + eval are now scenario-complete for the E-track campaign (Stage E-eval can drive SC-PERT-04..08 through `run_campaign` unchanged). `pytest` → 431 passed; `check_traceability` PASS; `check_scenario_yaml` PASS.

---

## [10.06.2026] — E2: live-loop integration of the cage-on-CV-state (cage 0.6.1) — four defects found and fixed by driving the actual loop

**Document(s) affected:** `cage/cage.yaml` (**0.6.0 → 0.6.1**: explicit `c05_emergency.staleness_max_s: 0.5`), `src/cobraflex_rl/cobraflex_rl/cage_perception.py` (supervisor defaults), `gazebo_lane_env.py` (reset-time perception priming; cage samples the freshest frame), `policy/tests/test_cage_perception.py`, `cage/tests/` (version pins).
**Phase:** E2 (track 'E').
**Gate context:** GE2 — closes the loop "cage drives on the CV estimate, live". F-track unaffected (state always fresh on the F-track, so the staleness budget never bound; Trigger 8 unchanged).
**Author:** Samuel.

### Change

Driving the camera env live (scripted controller, oval) exposed four integration defects invisible to both the unit tests and the static oracle grid:

1. **Lane-width dead zone:** the estimator accepts pairs in `nominal ± 0.10 m` (≥ 0.145), the SR-014 checker's generic default rejected `< 0.20` — estimates in `[0.145, 0.20)` were permanently rejected and the cage deadlocked into its no-state path (1-step episodes). Fix: the supervisor builds the checker from the estimator's own pair window.
2. **One-cycle-stale cage frame:** the cage consumed the frame retained at the end of the *previous* control cycle; at real-time rates its sim-age tripped both the supervisor staleness budget and C-05 Trigger 3. Fix: the cage samples the freshest frame at its own cycle start (same degradation pipeline — the D-43 common-cause property holds).
3. **Budget inconsistency at 10 Hz:** Trigger 3's code default (0.2 s) assumed the 20 Hz deployment loop, where it equals the documented 5-cycle missing-state tolerance; at the env's 10 Hz it undercut Trigger 5 (2 cycles vs 5) and stopped every lap at the curve apex, where the CV state legitimately skips 2–4 cycles (dash gaps). Fix: `staleness_max_s: 0.5 = n_missing_max_cycles × control_dt`, budgets aligned; SR-007's detection mandate unchanged (0.5 s at 0.2 m/s = 10 cm, inside the d_warning margin). Supervisor persistence likewise 2 → 4 cycles, and its `min_confidence` 0.3 → 0.10 so the single-line fallback (a degraded-but-valid mode; loss still carries confidence 0) is not misread as loss. Curvature plausibility 1.5 → 3.0 (ODD KAPPA_MAX 1.25 + measured estimator noise rejected real curve entries).
4. **Brittle first cycle:** one bad spawn frame put the cage on its no-state-ever path (instant emergency). Fix: reset-time priming — the supervisor must accept a settled spawn view (2 s budget) before the episode starts; a scenario injector active from t=0 may legitimately never prime, and then the controlled stop is the specified outcome.

### Rationale

Exactly the CLAUDE.md rule: typecheck/pytest ≠ feature works. Each fix is a *consistency* repair (estimator↔checker window, budget↔budget, frame↔cycle), not a loosening of the safety concept; every relaxation is bounded by an already-documented tolerance.

### Impact

Live loop now: perception available 699/700 cycles over repeated curve transits; a scripted controller with curvature feedforward drives the full curve (death at curve exit is the *controller's* lag, with the cage stopping it — correct behaviour). CV-vs-truth live: ey corr 0.87–0.89, MAE ≈ 15 mm. E-training pilot unblocked.

### Verification

`pytest` → 426 passed. `check_traceability` PASS. Live rollouts logged in the session (300–700-step batches; reason histograms drove each fix).

---

## [10.06.2026] — E2: track-'E' perception stack — CV lane-estimator (D-43) validated vs oracle, C-05 Trigger 8 live (cage 0.6.0), camera obs mode in the env, SC-PERT-04..08 un-stubbed

**Document(s) affected:** `cage/cage.yaml` (**0.5.1 → 0.6.0**), `cage/rules/c05_emergency.py` (Trigger 8), `cage/tests/test_c05_perception_trigger.py` (new) + 3 version-assert updates; `src/cobraflex_rl/cobraflex_rl/`: `camera_geometry.py`, `cv_lane_estimator.py`, `cage_perception.py`, `camera_pipeline.py` (new), `visual_degradation.py` (+occlusion, +false_lane), `gazebo_lane_env.py` (camera obs mode + in-env H-10 DR), `ros_interface.py` (camera subscription), `train_ppo.py` (CnnPolicy + VecFrameStack), `config/train_ppo_camera.yaml` (new); `policy/tests/` (+5 test files); `tools/validate_cv_estimator.py` (new); `docs/04` (Trigger 8 un-deferred, cage state source implemented), `docs/05` (SC-PERT-04..08 un-stubbed), `docs/09` §10 (v0.5); `scenarios/perturbed/sc_pert_04..08.yaml` (full schema-valid YAMLs); `experiments/sim/runs/cv_estimator_val_*` (oracle-validation evidence).
**Phase:** E2 (track 'E'; branch `e2e-camera`).
**Gate context:** GE2 core evidence — the cage may now rely on camera perception. F-track unaffected (cage 0.6.0 keeps Trigger 8 inert for pre-0.6.0 YAMLs; `perception_invalid` is never set by F-track callers).
**Author:** Samuel.

### Change

- **C-05 Trigger 8 implemented** (SR-013 loss / SR-014 misdetection; H-11/H-12): `ctx["perception_invalid"]`, raised by the external supervisor, fires the open-loop controlled stop. Gated by `c05_emergency.perception_trigger_enabled` (code default false → back-compat per the 0.4.0→0.5.0 precedent; the 0.6.0 YAML ships true). `compatible_sr_spec_version` stays "1.0" (SR-012..014 are additive).
- **Deterministic CV lane-estimator** (D-43): closed-form pitch-only ground-plane projection (`camera_geometry.py`, constants from the URDF/sensor); HSV white mask with **vegetation-hue exclusion**; per-row run candidates → polynomial line clustering → driven-lane pair selection → `ey/epsi/lane-width/curvature`; **single-line fallback** (lane_keeper precedent) for the dash-gap stretches in the tight curves. Composed with the SR-013 health monitor + SR-014 plausibility check in `cage_perception.CagePerceptionSupervisor`.
- **Oracle validation per D-43's plan** (`tools/validate_cv_estimator.py`; 4 iterations recorded under `experiments/sim/runs/cv_estimator_val_*`): the first run exposed two real defects — the proven lane-keeper mask thresholds let the **pale grass (S≈48) pass as "white"**, merging the road-edge line with the grass and biasing ey (gain 0.70, −20 mm offset) and epsi (+0.175 rad); and the linear cluster fits could not follow the KAPPA_MAX=1.25 curvature. Final state (run `cv_estimator_val_20260610T181634Z`): **clean detection 100%, ey bias −9 mm, MAE 23 mm, p95 58 mm; epsi MAE 0.16 rad**; glare 0.3/0.6 detected 100% (ey bias −13/−32 mm); motion blur 0.5 detected 100% (MAE 10 mm); low-light 0.3 → 67% detection, 0.6 → 0% (→ designed SR-013 stop); occlusion: far-field single-line persists at 0.5, full loss at 1.0; false-lane 0.8: ey stays accurate but **epsi pulled ~0.5 rad — the exact H-12 "confidently wrong" signature** the SR-014 check exists for.
- **Shared camera path** (`camera_pipeline.py`): one degradation point before **both** consumers (policy CNN + cage CV — the D-43 common cause); obs fixed at **84×84 grayscale, frame stack k=4** (docs/09 §10 v0.5, inside the documented envelope — no new D-NN). `GazeboLaneEnv` camera mode: image obs, cage on the supervisor's state/Trigger-8 flag, ground truth confined to reward/termination/metrics; in-env per-episode **H-10 domain randomisation** (seeded via `np_random`; eval-only modes occlusion/false-lane excluded from the training envelope by design). `train_ppo.py` gains CnnPolicy + VecFrameStack; E-config `train_ppo_camera.yaml`.
- **`visual_degradation.py`**: +`apply_occlusion` (SC-PERT-07) and `apply_false_lane` (SC-PERT-08) as `EVAL_ONLY_MODES`; `MODES` (the DR envelope) unchanged.
- **SC-PERT-04..08 un-stubbed** into full schema-valid YAMLs (`check_scenario_yaml.py`: 0 errors, 0 warnings) with levels grounded in the oracle validation; docs/05 sections updated (incl. the SC-PERT-05 labelled two-arm criterion and SC-PERT-07's level-1.0 rationale); run budget 320 across both modes.

### Rationale

D-43 made the estimator-vs-oracle evidence the precondition for the cage relying on camera perception; building the estimator exposed two genuine perception defects that pure host tests could not have caught (grass-as-white, curvature-blind linear fits) — exactly the kind of finding the oracle-validation step exists for.

### Impact

- Cage consumers on the camera track must run cage YAML ≥ 0.6.0; F-track behaviour is bit-identical (back-compat default).
- The E-training pilot (Stage E3) is unblocked: env camera mode + config exist. Known limitation recorded: estimator epsi MAE ≈ 0.16 rad clean (p95 0.35) — C-02 enforcement on the CV state will be noisier than on ground truth; to be observed in the pilot and, if spurious C-02/C-05 fires dominate, a deterministic temporal smoothing (EMA) is the candidate fix.

### Verification

`pytest` → **426 passed** (60 new). `python tools/check_traceability.py` → All checks PASSED, 0 warnings. `python tools/check_scenario_yaml.py` → 0 errors, 0 warnings (stub warnings gone). Oracle validation: `experiments/sim/runs/cv_estimator_val_20260610T181634Z/summary.json` (numbers above) with full repro metadata (git commit, world/centerline/cage hashes, camera model, estimator config).

---

## [10.06.2026] — E2: camera evidence baseline — pitched front camera, matte road materials, lane-line visibility verified in-sim

**Document(s) affected:** `src/cobraflex/urdf/my_robot_gazebo.urdf` + `my_robot_gazebo_mesh.urdf` (camera pitch), `scripts/compose_lane_circuit.py` (matte PBR material), `src/cobraflex/worlds/lane_following_oval{,_wet,_worn}.world` (regenerated), `tools/capture_camera_frames.py` + `tools/cam_evidence_session.sh` + `tools/reap_sim.sh` (new evidence tools), `experiments/sim/e_cam_visibility/` (frame evidence).
**Phase:** E2 (track 'E'; branch `e2e-camera`).
**Gate context:** GE2 prerequisite — the camera+world visual baseline every later E-artefact (CNN obs, CV lane-estimator) consumes. F-track unaffected (the F-policy is state-vector-based; world visuals do not enter its evidence).
**Author:** Samuel.

### Change

- **Front camera verified live** on the Ubuntu host: the existing `ZEDm Cam` sensor (640×480 RGB, 20 Hz, `camera/image_raw`, bridged in `gz_bridge.yaml`) publishes headless (`gui:=false`); frames captured at four canonical poses (spawn, curve entry s=1.5, mid-curve, back straight) and stored under `experiments/sim/e_cam_visibility/`.
- **Camera pitched down 0.25 rad** (both gazebo URDFs): flat-mounted, the R=0.80 m curve swept out of the FOV at curve entry (frames kept as evidence); pitched, the near road fills the lower frame at all four poses.
- **Matte road materials**: the composer's tile material gained `roughness 0.9 / metalness 0.0` — ogre2's PBR defaults rendered the tiles glossy, with bright specular lobes a white-line detector (or the CNN) would read as lane features. All three oval worlds regenerated from the composer (content-identical otherwise; the wet/worn files also lost their accidental CRLF endings). With matte asphalt the dashed separator and the white edge lines are crisply visible at every pose — the visibility precondition of docs/09 §10 is met and evidenced.
- New host tools: `tools/capture_camera_frames.py` (frame grabber), `tools/cam_evidence_session.sh` (launch + teleport + capture), `tools/reap_sim.sh` (orphan reaper).

### Rationale

docs/09 §10 ("verify the lane lines are actually visible to the camera") is the entry condition for the camera observation bridge and the D-43 CV lane-estimator; both the pitch and the matte fix came out of looking at actual frames rather than assuming the texture work sufficed.

### Impact

- The world files' hashes change; E-track runs record the new hashes. Frozen F-track run metadata is untouched (their recorded hashes remain valid for the commits they cite).
- `oval_centerline.yaml` regeneration verified byte-identical — no geometry change, no ODD impact (ROAD_LENGTH / KAPPA_MAX unchanged).
- Camera intrinsics baseline for the E-obs design: 640×480 @ 20 Hz, HFOV 1.396 rad, pitch 0.25 rad.

### Verification

`pytest` → 366 passed. `python tools/check_traceability.py` → All checks PASSED, 0 warnings. Evidence frames reviewed at the four poses for the flat (`spawn/...`), pitched (`pitch025_*`) and pitched+matte (`matte_*`) configurations.

---

## [10.06.2026] — F4: SR-006 closed on its own metric (D-39); SR-009/SR-010 blockers diagnosed

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/campaign_metrics.py`, `policy/tests/test_campaign_metrics.py`, `tools/sr006_smoothness.py` (new), `docs/DECISIONS.md` (D-39), `docs/07_traceability_matrix.md`, `docs/05_scenario_library.md`, `docs/08_odd_specification.md` (§12.3), `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.2.5, §8.4–§8.7, appendix), `CLAUDE.md`.  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Pushed the three open SR-CL-B TBDs as far as possible without a Gazebo re-run, and
diagnosed precisely what each still needs:

- **SR-006 (actuator smoothness) → Satisfied (D-39).** Added a committed-steer
  per-cycle rate metric to `campaign_metrics` (`M-I5.steer_rate_max`,
  `steer_rate_max_smoothness`, `steer_rate_smoothness_ok`) and a dedicated analysis
  tool `tools/sr006_smoothness.py` (reads `cage_status.csv`, no Gazebo, precedent
  D-35). SR-006 is now scored **on its own metric** instead of inheriting the
  unrelated SC-PERT-01 fraction fail. The cage runs C-06 first (bounds the raw rate),
  then downstream safety rules (C-01/C-02/C-03/C-05) may legitimately exceed it; on
  the steps C-06 governs (no override), the committed rate holds at δ_max = 0.15 in
  **559/559** evaluable enforcement runs vs **67.6 %** in monitoring (worst 0.43) — a
  direct measure of C-06's value. **No cage defect:** every apparent excursion
  coincides with a downstream safety intervention.
- **SR-010 (SC-EDGE-05) — diagnosed, needs re-run.** The scenario as-run induced
  **zero rule co-activation** (0 interventions across 100 runs); the
  `parameterised_grid` initial conditions are not injected by the runner. So SR-010
  cannot be verified from these logs even with the two missing counters added — the
  scenario must first actually stress co-activation, then re-run.
- **SR-009 (SC-PERT-03) — diagnosed, needs re-run.** The multi-arm evaluator already
  exists (`criterion_eval.evaluate_labelled`); the stall-variant arm was never
  executed and the driver does not group the two arms. Needs the fine-tune + run +
  grouping.

Documentation synced to the executed campaign: `docs/05` (1100→1260 runs, seed 2024,
SATISFIED, open items), §8.2.5 (the in-ODD enforcement-vs-monitoring delta is
*degenerate* — M-S2 = 0 in both modes, no variance — so inference applies to the
frontier and SR-006 contrasts, not the in-ODD M-S2 delta), `docs/08` §12.3 (the
ODD-Spec carries the lone TBD-Q10 to F5; it is not promoted to v1.0 at G4).

### Rationale

"Do everything possible without a re-run." SR-006 needed no re-run — its evidence is
in the committed-steer trace already logged — so it is closed here on a defensible,
architecture-grounded operationalisation (smoothness subordinate to safety, D-39).
SR-009/SR-010 genuinely need the Ubuntu host (a fine-tuned stall policy; a runner
that injects grid ICs), so the honest deliverable is a precise diagnosis + the
pure-Python pieces that make the re-run productive, not speculative untested code.
The investigation also cleared a scare: the large committed-steer jumps are correct
downstream safety corrections, **not** a C-06 rate-limiter defect.

### Impact

- `campaign_report.json` per-SR SR-006 still reads `failed` (coarse `ALL` inheritance);
  re-pointing it to the metric in `run_campaign.aggregate_sr` is a flagged D-39
  follow-up. SR-006 is CL-B → **global verdict unchanged (`SATISFIED`)**.
- **Ubuntu re-run punch-list (before G4):** SC-EDGE-05 grid-IC injection + counters;
  SC-PERT-03 stall arm + arm grouping; then re-score SR-009/SR-010. Plus the QED
  metric decision (D-17/D-21).
- No H/SR/C/SC/M artefacts changed; no new orphans.

### Verification

`pytest` → 316 passed (2 new SR-006 metric tests). `python tools/check_traceability.py`
→ 8/8 constraints PASS, 0 warnings.

---

## [10.06.2026] — F4: Reconcile campaign aggregators on indeterminate verdicts (D-38)

**Document(s) affected:** `tools/run_campaign.py`, `policy/tests/test_run_campaign.py`, `policy/tests/test_verdict_aggregation.py`, `experiments/sim/campaign/campaign_report.json` (regenerated), `docs/DECISIONS.md` (D-38), `docs/07_traceability_matrix.md` (aggregator caveat → reconciliation note).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Reconciled the two campaign verdict aggregators so an *indeterminate* (`None`)
per-run verdict is handled identically by both. `tools/run_campaign.py` previously
counted `None` runs inside the pass-fraction denominator (`n_pass / n_total`),
collapsing "no evidence" into a fail; it now **excludes** them (`n_pass / n_evaluable`,
`None` if no evaluable run) and propagates `insufficient_evidence`, matching the
unit-tested D-29/D-30 spine `src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py`.

- `aggregate_scenario` returns a three-valued verdict with `n_fail`/`n_indeterminate`.
- `aggregate_sr` returns a `status` ∈ {satisfied, failed, insufficient_evidence,
  not_run} (a genuine failure dominates an indeterminate sibling).
- `global_verdict` distinguishes `NOT SATISFIED` (an SR-CL-A failed) from `INCOMPLETE`
  (an SR-CL-A under-evidenced).
- `campaign_report.json` **regenerated from the raw `campaign_runs.csv`** (the per-run
  `None`s were already logged) — **no Gazebo re-run**. SC-EDGE-05 / SC-PERT-03 now read
  `verdict: null`; **SR-009 / SR-010 move from `false` to `insufficient_evidence`**.
- Tests added for "all runs `None` → insufficient_evidence, not failed" and the
  failed-dominates-indeterminate precedence in both test suites. Decision recorded as
  **D-38**; the `docs/07` "Aggregator caveat" replaced by a reconciliation note.

### Rationale

A `false` verdict must mean a demonstrated safety violation, not an instrumentation
gap. The old `run_campaign.py` denominator mis-reported two known gaps (SC-EDGE-05's
predicate references operands absent from the run-record schema; SC-PERT-03's labelled
multi-arm criterion is not scorable in the single-run evaluator) as failures, dragging
SR-009/SR-010 to `false`. The spine already used three-valued logic to avoid exactly
this; the fix brings the runner into line rather than adding a third rule.

### Impact

**The global verdict is unchanged: `SATISFIED`, all 7 SR-CL-A satisfied (D-30 veto
clear).** Only the classification of three non-blocking **SR-CL-B** verdicts is
touched: SR-009 and SR-010 are now correctly `insufficient_evidence`; **SR-006 remains
`failed`** because it inherits the *genuine* SC-PERT-01 fraction fail (0.883 < 0.90) —
a separate per-metric re-aggregation issue, not a `None`. The `docs/07` matrix verdict
cells for SR-006/009/010 stay **TBD** (held open until the schema/evaluator gaps close
and the scenarios are re-scored). No H/SR/C/SC/M artefacts changed; no
`traceability_matrix.csv` rows.

### Verification

`python -m pytest` → 314 passed (incl. the new D-38 cases).
`python tools/check_traceability.py` → all checks PASSED, 0 warnings.
`campaign_report.json` re-validated: valid JSON, ASCII-clean, `global.verdict =
SATISFIED`, `n_runs = 1260`, `n_error = 0`.

---

## [10.06.2026] — F4: Sim-eval campaign closed; docs/07 verdicts filled

**Document(s) affected:** `docs/07_traceability_matrix.md`, `tools/traceability_matrix.csv`, `manuscript/chapters/chapter_08_experimental_evaluation.md` (§8.2.1, §8.2.4, §8.2.6, §8.3–§8.7, §8.8.1), `CLAUDE.md` (phase status).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

The verdict-bearing simulation campaign ran to completion: **1260 runs**, main
seed **2024** (D-36), every verdict-bearing scenario × {enforcement, monitoring}.
Roll-up committed at `experiments/sim/campaign/campaign_report.json` +
`campaign_runs.csv`; out-of-ODD frontier contrast at
`experiments/sim/campaign_frontier/frontier_contrast.json` (+ two figures).

- **`docs/07`** — the `Verdict` column moves from all-`TBD` to the sim verdicts.
  **Global verdict `SATISFIED`**: all 7 **SR-CL-A** (SR-001..005, SR-007, SR-008)
  satisfied with margin → D-30 veto not triggered. SR-011 (CL-B) also Satisfied.
  Three **SR-CL-B** verdicts held **TBD** by deliberate abstention (notes ¹²³):
  SR-006 (coarse `ALL` aggregation inherits the SC-PERT-01 σ=0.05 emergency-trip
  failures, M-I5 itself not breached), SR-009 and SR-010 (instrumentation gaps —
  SC-PERT-03 multi-arm meta-test and SC-EDGE-05 predicate operands are not in the
  single-run evaluator / run-record schema, so those runs are *indeterminate*,
  not failing).
- **`tools/traceability_matrix.csv`** — `verdict_sim` set to `satisfied` and
  `evidence_path` populated for the SR-001/002/003/004/005/007/008 rows; SR-006
  rows kept `tbd` with a pointer to the docs/07 note.
- **`manuscript` §8** — §8.3–§8.7 and §8.8.1 (marked `[COMPLETAR FASE 4]`) written
  from the campaign data; the inline `[COMPLETAR]` placeholders in §8.2.4 (D-29/D-30
  summary) and §8.2.6 (runner reference) resolved; §8.2.1 corrected to the realised
  design (main seed 2024 per D-36, RL controller; the earlier "≈1100 runs / N=5
  across all scenarios / PD axis" draft did not match the executed campaign).

### Rationale

The campaign is the evidence layer the traceability matrix was built to receive.
Recording the honest picture matters more than a clean pass: the central in-ODD
finding is that **M-S2 (boundary violation) = 0 in both modes everywhere**, i.e.
the constraint-respecting main policy never approaches the boundary inside the ODD,
so the cage is **latent** there (enforcement ≈ monitoring). The cage's protective
value is shown **out-of-ODD** by the D-35 frontier contrast: for the cage-dependent
seed 123 the cage removes **96–100 % of road-edge contacts** (M-S5) the bare policy
would incur (SC-FRONT-01/03/04/06), while the constraint-respecting seed 2024
recovers on its own (benefit ≈ 0) — the §7.5.3 bimodality realised at runtime.
The three TBDs are abstentions, not failures: collapsing an indeterminate verdict
to a fail (as `run_campaign.py` does) would overstate the result, so they are held
open until the evaluator / run-record schema gaps are closed and the scenarios
re-scored.

### Impact

- No H/SR/C/SC/M artefacts added or changed; no new orphans.
- **Open before G4:** close the three TBDs (SR-006 per-metric re-aggregation on
  M-I5; SR-009/SR-010 schema-gap fix in the run record + multi-arm scoring in the
  evaluator, then re-score SC-PERT-03 / SC-EDGE-05). Tracked as the remaining F4
  work in `CLAUDE.md`.
- `run_campaign.py`'s indeterminate→fail collapse vs `verdict_aggregation.py`'s
  indeterminate→`insufficient_evidence` is recorded as a caveat in docs/07; a
  reconciliation of the two aggregators is a candidate decision (D-NN) for G4.

### Verification

`python tools/check_traceability.py` → all 8 constraints PASS, 0 warnings (the
verdict column is free-text and not constraint-checked; structure unchanged).

---

## [09.06.2026] — E2: D-43 — cage on a dedicated vision lane-estimator (supersedes D-42); H-12 / SR-014 / SC-PERT-08

**Document(s) affected:** `docs/DECISIONS.md` (D-43; D-42 → SUPERSEDED), `docs/02` (H-10/H-11 reframe + new H-12), `docs/03` (SR-012/SR-013 reframe + new SR-014), `docs/04`, `docs/05` (SC-PERT-08 + reframe), `docs/07`, `docs/09` §10 (v0.4), `docs/10` §10; `docs/data/*.csv` (regenerated); `tools/traceability_matrix.csv`; `manuscript/chapters/chapter_04`, `chapter_05`; `scenarios/perturbed/sc_pert_08.yaml` (new stub); `policy/tests/test_verdict_aggregation.py` (count); `src/cobraflex_rl/cobraflex_rl/visual_domain_randomization.py` + test (new).  
**Phase:** E1 (track 'E'; branch `e2e-camera`).  
**Gate context:** E-design, before GE2. F-track unaffected.  
**Author:** Samuel.  

### Change

Re-architected the track-'E' cage perception after the design clarification that the system must drive on **any road with visible lane lines** from the camera (policy *and* cage), without an authored centerline:

- **D-43 (supersedes D-42).** The cage's `state` now comes from a **dedicated, deterministic CV lane-estimator** (separate from the policy's CNN), not from privileged ground truth. Ground truth is kept **in sim only** as the training reward and an oracle to validate the estimator. C-01..C-06 unchanged — only the state *source* changes. D-42 → SUPERSEDED by D-43.
- **Reframed H-10 / H-11 and SR-012 / SR-013** (`docs/02`, `docs/03`, `docs/04`, `docs/05`, `docs/07`, chapters 04/05): the cage now reads the camera (its own CV detector), so a camera fault is **common-cause** (blinds policy and cage alike); the residual safety is the **open-loop controlled stop** (SR-013/C-05, "no lines ⇒ stop").
- **New hazard H-12** (cage lane-misdetection: a confidently-wrong CV estimate → false envelope) + **SR-014** (estimator plausibility / temporal-consistency check + conservative fall-back to C-05) + **SC-PERT-08** stub (misleading-markings / false-lane test). Registers the failure mode the CV estimator introduces (impossible under D-42).
- **Training-world diversity decided: oval-first** (`docs/09` §10): first camera-policy prototype on the current oval with visible lines; world diversity added afterwards.
- Added the host-testable **visual domain-randomization sampler** (`visual_domain_randomization.py` + test) — the training-side mitigation of H-10 referenced by `docs/09` §10.

### Rationale

The generalisation goal requires the *whole* system to key on visible lines, so the cage cannot rely on an authored centerline. A separate **deterministic CV** estimator keeps the cage independent of the *learned policy* and auditable (a classical algorithm is inspectable). The honest cost — common-cause blindness and a new misdetection hazard — is registered explicitly (D-43 consequences, H-12) rather than hidden; the open-loop stop is the residual safeguard.

### Impact

- Shared registers extended: H-12, SR-014, SC-PERT-08 (stub). SR-CL-A count 9 → 10.
- **Deferred to Ubuntu:** the cage's CV lane-estimator node + plausibility/temporal-consistency check, the camera obs bridge, the runtime injectors, and CNN training. Sim ground truth validates the estimator (oracle).

### Verification

- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (12 hazards H-01..H-12; 14 SRs SR-001..SR-014; 22 scenarios incl. SC-PERT-08).
- `python tools/check_scenario_yaml.py` → PASSED, 5 stub warnings.
- `pytest` (root) → **352 passed**.

---

## [09.06.2026] — E2: manuscript — track 'E' notes in ch.3 / ch.5 / ch.7

**Document(s) affected:** `manuscript/chapters/chapter_03_methodology.md`, `chapter_05_architecture_and_cage.md`, `chapter_07_training_specification.md`.  
**Phase:** E0/E1 (track 'E'; branch `e2e-camera`).  
**Author:** Samuel.  

### Change

- **§3.5.1** records that **D-01 ("no end-to-end") is superseded by D-41** for track 'E', with the retained-modular-cage argument (A1/A2/A4 stay viable; D-42). Closes the §3.5.1 follow-up flagged in the scaffolding entry.
- **§5.2.3** ("Lo que la cage no es") adds the property *the cage does not depend on the policy's perception* — it runs on an independent state estimate (D-42), which keeps H-06 (cage state) distinct from H-11 (camera perception).
- **§7.2.1** notes the camera-observation variant (CNN; action and reward unchanged; cage on independent state; PPO/camera training deferred to Ubuntu), pointing to `docs/09` §10.

### Rationale

Keep the manuscript consistent with the E-track architectural decisions (D-41/D-42) recorded under `docs/`.

### Verification

Prose only; `tools/check_traceability.py` parses `docs/`, not the manuscript, so it is unaffected (still PASS). `pytest` unaffected (340 passed).

---

## [09.06.2026] — E2: E-design — camera env (docs/09 §10), reward unchanged (docs/10 §10), pure-Python perception modules

**Document(s) affected:** `docs/09`, `docs/10`; `src/cobraflex_rl/cobraflex_rl/visual_degradation.py` + `perception_health.py` (new); `policy/tests/test_visual_degradation.py` + `test_perception_health.py` (new).  
**Phase:** E0/E1 (track 'E' design; branch `e2e-camera`).  
**Gate context:** E-design, before GE1. F-track unaffected.  
**Author:** Samuel.  

### Change

- **docs/09 §10** (v0.3): the E-track environment changes **only the observation** — the front-camera image (CNN policy) replaces the 6-dim state vector. Action, reward, cage (on the independent ground-truth state, D-42) and episode logic are unchanged; supersedes ED-1's image-obs rejection for track 'E'. Visual degradations act on the observation; perception loss raises C-05 Trigger 8.
- **docs/10 §10:** the reward is **unchanged** for track 'E' — it is observation-agnostic (computed on ground-truth state + progress + raw steering delta).
- **New host-testable pure modules** (numpy / stdlib only, no ROS): `visual_degradation.py` (glare / low-light / motion-blur primitives → SC-PERT-04..06 / SR-012 / H-10) and `perception_health.py` (`PerceptionHealthMonitor` raising the C-05 perception-health trigger → SC-PERT-07 / SR-013 / H-11), each with a unit-test file under `policy/tests/`.
- **`tools/traceability_matrix.csv` reconciled** (the hand-maintained granular matrix flagged as stale in the scaffolding entry): it now covers every `H→SR→C→SC→M` chain, adding the previously-missing H-08/H-09/SR-011 rows and the new track-'E' H-10/H-11 rows. Aligns the CSV with `docs/07`.

### Rationale

The E-track changes only the policy's input; the reward and cage are observation-agnostic / on the independent state, so they carry over (the minimal-delta point of D-42). The two pure modules are the host-doable, unit-testable kernels of the camera stressors; the Gazebo camera sensor, the observation bridge, the runtime injectors and the ROS perception-health node are the Ubuntu part.

### Impact

- No change to F-track artefacts or the H→SR→C→SC→M chain. SC-PERT-04..07 remain stubs.
- **Deferred to Ubuntu:** Gazebo front-camera sensor (URDF/SDF) + observation bridge in `gazebo_lane_env`, CNN/PPO training, runtime degradation/loss injectors, the ROS perception-health supervisor node.

### Verification

- `pytest` (root) → **340 passed** (33 new across `test_visual_degradation.py` + `test_perception_health.py`).
- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings**.

---

## [09.06.2026] — E2: Track 'E' scaffolding (end-to-end front-camera) — D-41/D-42, H-10/H-11, SR-012/013, SC-PERT-04..07

**Document(s) affected:** `docs/00`, `docs/01`, `docs/02`, `docs/03`, `docs/04`, `docs/05`, `docs/07`, `docs/DECISIONS.md`; `docs/data/hazard_register.csv` + `docs/data/safety_requirements.csv` (regenerated); `manuscript/chapters/chapter_04_*`; `scenarios/perturbed/sc_pert_04..07.yaml` (new stubs); `policy/tests/test_verdict_aggregation.py` (count).  
**Phase:** E0 (parallel track; branch `e2e-camera`).  
**Gate context:** track entry, before GE0. The main F-track (F4 → G4) is unaffected.  
**Author:** Samuel.  

### Change

Opened the parallel **track 'E'** for an end-to-end front-camera lane-following variant and scaffolded its left-arm artefacts (HARA → SRS → Cage → scenarios):

- **Decisions:** D-41 (open track 'E'; phases `E0..E6` / gates `GE0..GE6`; commit prefix `E2:`; **supersedes D-01**) and D-42 (the cage stays on an *independent* state estimate, not the camera). D-01 status → SUPERSEDED by D-41.
- **Numbering:** E-phase/gate scheme added to `docs/01`; "Parallel track E" section added to `docs/00`.
- **Hazards:** H-10 (lane misperception under degraded visual input) and H-11 (loss of valid lane perception) in `docs/02` + machine-readable table + STPA scope addendum.
- **SRs:** SR-012 (lane-keeping under degraded visual input → C-01/C-02/C-03 + training) and SR-013 (safe degradation on loss of valid perception → C-05 via a perception-health supervisor) in `docs/03` + table.
- **Cage:** `docs/04` cage-independence note (D-42) and C-05 Trigger 8 (perception-health, deferred). C-01..C-06 reused unchanged — **no new cage rule**.
- **Scenarios:** SC-PERT-04..07 (glare, low-light, motion-blur, occlusion/perception-loss) documented in `docs/05` + **stub** YAMLs under `scenarios/perturbed/` (reuse the PERT family — no schema/`RX_SC` change).
- **Matrix / manuscript:** H-10/H-11 rows added to `docs/07`; `chapter_04` hazard/SR tables mirrored.

### Rationale

The camera→action variant is a second instantiation of the SE4AI method on a harder perception problem and a full new left-arm cycle, so it is isolated on its own branch + phase numbering with the F-track evidence frozen. The supersession of D-01 is safe because the **modular cage is retained** (D-42): pixels enter the policy, never the safety envelope, so framework adaptations A1/A2/A4 stay viable. The new hazards are functional sensor/environment perception failures — narrower than D-31's still-excluded non-functional AI families — and the cage's independence keeps H-06 (cage state) distinct from H-11 (camera perception).

### Impact

- Shared global ID space extended: H-10/H-11, SR-012/SR-013, SC-PERT-04..07. CSVs regenerated via `tools/sync_hazard_register.py` + `tools/sync_safety_requirements.py`.
- `policy/tests/test_verdict_aggregation.py` SR-CL-A count updated 7 → 9 (the two new track-'E' SRs are SR-CL-A).
- SC-PERT-04..07 are stubs (skipped by `run_campaign.build_matrix`), so the F-track verdict-bearing campaign budget is unchanged.
- **Deferred to later E-phases:** camera observation / CNN env design (`docs/09`), reward (`docs/10`), Gazebo camera sensor + perception node + perception-health supervisor, PPO retraining, un-stubbing SC-PERT-04..07.
- **Follow-ups pending:** manuscript §3.5.1 (record the D-01 supersession + retained-cage argument); `tools/traceability_matrix.csv` (hand-maintained granular matrix) left unchanged — already partial (missing H-08/H-09) — track-E rows deferred to a matrix-reconciliation pass.

### Verification

- `python tools/check_traceability.py` → **All checks PASSED, 0 warnings** (11 hazards H-01..H-11; 13 SRs SR-001..SR-013; 21 scenarios incl. SC-PERT-04..07; constraints 1–8 OK).
- `python tools/check_scenario_yaml.py` → PASSED, 4 warnings (SC-PERT-04..07 explicit stubs).
- `pytest` (root) → **307 passed**.

---

## [08.06.2026] — F4: Anticipated defense questions added to docs 00–08

**Document(s) affected:** `docs/00`–`docs/08` (new "Anticipated defense questions" section in each; `docs/08` as new §13).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added an **"Anticipated defense questions"** section (the format already used in
`docs/09` and `docs/10`) to each of the nine numbered engineering documents
`docs/00`–`docs/08`. Each section is six bold Q&A pairs anticipating the
committee's most probing questions on that document, with answers that cite the
relevant IDs, decisions (D-03, D-11, D-25, D-28/29/30, D-34, D-35, D-37),
sections and evidence, and that surface the known open points honestly (e.g. the
SR-010 Trigger 7 deferral, the 10 Hz vs 20 Hz cadence mismatch, the ODD-3/4
coverage gaps, the 5↔6 observation-dimension reconciliation). Placed before each
document's `## Change log`; in `docs/08` (which uses numbered sections) appended
as `## 13.` before the end marker.

### Rationale

`docs/09` and `docs/10` carry a defense-questions bank that consolidates the
*why* of each design decision in viva-ready form; extending it to the rest of the
engineering documents gives the whole `docs/` set a uniform, defensible closing
section for the thesis defense. Scope confirmed with the author: numbered
engineering specs only (`00`–`08`); the process registries `CHANGELOG.md` and
`DECISIONS.md` were deliberately left out as a poor genre fit.

### Impact

Prose-only addition. No H / SR / C / SC / M identifier, parameter, threshold, ODD
value, or cage constant changes; no `traceability_matrix.csv` rows. The new text
*cites* existing IDs but defines none, so coverage is unaffected.

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: D-37 — single-world ODD reconciliation (docs/08 §12)

**Document(s) affected:** `docs/08_odd_specification.md` (new §12, version 0.5→0.6, change-log row); `docs/DECISIONS.md` (new D-37; decision-index row; header `Status:` comment).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added **D-37** and `docs/08` §12 "F4 evaluation realisation on a single world". §12 records
that the F4 sim campaign runs every scenario on the single oval world (Option A, `docs/05`
Track-mapping) at one fixed-speed `ACT_DIM=1` operating point (0.2 m/s, 6-dim obs), and
declares the ODD coverage: ODD-1/2 covered (geometry/obs caveats), ODD-3 partial (curve
geometry exercised, 2-dim speed envelope `v_max(κ)` not), ODD-4 not exercised (no
adverse-curvy scenario). ODD-spec version bumped 0.5 → 0.6.

### Rationale

The ODD-spec stratifies four domains across two worlds (straight for ODD-1/2, oval for
ODD-3/4) with a 2-dim speed-adaptive action for ODD-3/4. The F4 campaign collapses this to
one world + one fixed-speed steering-only operating point, so the spec no longer literally
describes what is evaluated. Per `docs/08`'s own convention (numerical authority flows
spec → evidence), the parameters are **not** rewritten; §12 declares the evaluated subset
and its gaps — the Phase-4 analogue of D-11's bounded validation. Surfaced while assessing
how to handle `docs/08` given the single-map evaluation.

### Impact

No ODD parameter, SR threshold, or cage constant changes; no H/SR/C/SC/M artefacts; no
`traceability_matrix.csv` rows. **Follow-up:** align the manuscript Cap. 8 ODD-coverage
claim (ODD-1/2 covered, ODD-3 partial, ODD-4 deferred) and report the gap in Limitations.
A variable-speed `ACT_DIM=2` policy + an adverse-curvy scenario are future work (F5+).

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: D-36 — seed policy for the verdict / frontier campaigns

**Document(s) affected:** `docs/DECISIONS.md` (new D-36; decision-index row; header `Status:` comment).  
**Phase:** F4.  
**Gate context:** before G4.  
**Author:** Samuel.  

### Change

Added decision **D-36** fixing which policy seeds enter each F4 campaign: the D-29/D-30
verdict-bearing campaign certifies the G3-selected main policy **seed 2024** only, while
the cage-dependent **seed 123** (58.8 % cage, §7.5.3) appears solely in the D-35 frontier
cage-efficacy contrast (and, optionally, a separately-reported robustness sweep with its
own `--out`). Updated the decision index and the header status comment to list D-36.

### Rationale

`aggregate_campaign` (`tools/run_campaign.py`) groups per-run outcomes by
`(scenario, mode)` and pools all seeds into one `fraction_pass`; running seed 123 inside
the verdict campaign would average the deliberately cage-dependent policy into the
per-scenario verdict and could veto an SR-CL-A (D-30) on the basis of a policy not chosen
for delivery. Surfaced during the 08.06 campaign-readiness review.

### Impact

No H/SR/C/SC/M artefacts and no `traceability_matrix.csv` rows. Operational: the
verdict-bearing run uses `--seeds 2024 --out experiments/sim/campaign`; the frontier run
uses `--seeds 2024,123 --reps 25 --out experiments/sim/campaign_frontier` (realised budget
6 × 25 × 2 modes × 2 seeds = 600 runs). Both still pending on the Ubuntu+Jazzy host.

### Verification

`python tools/check_traceability.py` → All checks PASSED, 0 warnings.

---

## [08.06.2026] — F4: Runtime perturbation injection wired (SC-PERT-01/02, SC-EDGE-03)

**Document(s) affected:**
New: `src/cobraflex_rl/cobraflex_rl/scenario_perturbations.py`,
`policy/tests/test_scenario_perturbations.py`.
Modified: `…/scenario_runner.py`, `…/gazebo_lane_env.py`, `…/eval_policy.py`,
`policy/tests/test_scenario_runner.py`, `scenarios/_schema.yaml`, `experiments/README.md`.
**Phase:** F4.
**Gate context:** before G4.
**Author:** Samuel.

### Change

- **New pure module `scenario_perturbations.py`** — resolves a scenario `perturbations:` block +
  rep index into a concrete, level-resolved `ScenarioPerturbation`: `observation_noise` (Gaussian
  on the perceived lateral offset, SC-PERT-01), `actuation_latency` (command delay in control
  steps, SC-PERT-02), `throttle_override` (timed pulse fed to C-04, SC-EDGE-03). Multi-level types
  pick their level by `rep % n_levels` (the YAML's "20 runs per level"). ROS-free, unit-tested.
- **`scenario_runner.derive_run_config`** now carries the resolved `perturbation` and a per-rep
  `env_seed` on `RunConfig`.
- **`gazebo_lane_env`** applies the three perturbations: the *perceived* lateral offset
  (true + noise) feeds the policy observation **and** the cage state, while metrics / reward /
  termination stay on the *true* pose (Ch.8 §8.2.3); a `deque` buffers `/cmd_vel` for actuation
  latency; the throttle pulse substitutes the nominal throttle into the cage input.
- **`eval_policy`** passes the perturbation through `reset(options=…)`, seeds the env reset with
  the per-rep `env_seed` (independent yet reproducible obs-noise per rep), and records the level
  in `summary["perturbation"]`.

### Rationale

The F4 verdict campaign's adverse arm for SR-001/003/004/007 (and the SR-009 negative test)
depends on SC-PERT-01/02 and SC-EDGE-03, but the executor previously ignored the `perturbations:`
block entirely — those runs would have executed as plain nominal runs and reported a misleading
PASS (the 08.06 readiness review). This wires the three runtime stressors so the perturbed
scenarios test what they claim.

### Impact

- **Not yet Gazebo-validated.** The pure logic is unit-tested (28 cases) but the env application
  runs only on the Ubuntu+Jazzy host — smoke-test per `experiments/README.md` step 3b before
  trusting the perturbed verdicts.
- **SC-EDGE-03 caveat:** the fixed-speed actuation (`target_speed_from_throttle` caps speed at
  `fixed_speed` ≈ 0.2 m/s < `v_max` 0.5 m/s) limits the achievable over-speed, so the override
  reaches C-04 but exercises little real speed excess; a full SR-004 test needs variable-speed
  actuation (flagged in the runbook).
- **Still unwired (different mechanisms):** SC-EDGE-05 (initial-condition grid expansion) and
  SC-PERT-03 (pre-run stall-variant checkpoint). No H/SR/C/SC/M ids added or changed.

### Verification

`python -m pytest policy/tests/test_scenario_perturbations.py policy/tests/test_scenario_runner.py`
→ 28 passed. `py_compile` of `scenario_perturbations` / `scenario_runner` / `gazebo_lane_env` /
`eval_policy` → clean. `python tools/check_traceability.py` → unaffected (All checks PASSED, 0 warnings).

---

## [08.06.2026] — F4: Frontier cage-efficacy scenario family (SC-FRONT-01…06 + M-S5) registered; Gazebo executor live

**Document(s) affected:**
`docs/05_scenario_library.md` (Frontier category + study section + 6 SC-FRONT entries; count 11→17),
`docs/06_metrics_catalogue.md` (new M-S5), `scenarios/_schema.yaml`,
`tools/check_scenario_yaml.py`, `tools/check_traceability.py`, `docs/DECISIONS.md` (D-35 + index),
`docs/07_traceability_matrix.md` (D-35 carve-out note),
`manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_08_experimental_evaluation.md`,
`CLAUDE.md`.
New code/scenarios this entry documents: `scenarios/frontier/sc_front_01…06.yaml`,
`tools/run_campaign.py` (`execute_run` + frontier-plot hook), `tools/frontier_contrast.py`,
`tools/plot_frontier.py`, `tools/README.md`,
`src/cobraflex_rl/cobraflex_rl/scenario_metrics.py`, `…/eval_policy.py`.
**Phase:** F4.
**Gate context:** before G4.
**Author:** Samuel.

### Change

- **New Frontier (FRONT) scenario family — SC-FRONT-01…06.** Out-of-ODD /
  cage-efficacy scenarios: an out-of-ODD pair (01–03: lateral 0.16 m / heading 32° /
  compound) where the start is already past the boundary, and an in-ODD-drift pair
  (04–06: 0.10 m + 8°/22°/14° outward) where the cage responds **graded** rather than
  with an immediate stop. All on the oval (`start_s=0.0`, 0.2 m/s, 15 s), 25 runs/mode.
  Registered in `docs/05` (new category, study section, per-scenario entries; total
  scenario count **11 → 17**). They reference existing SR-001/002/005/007/008 — no new SR.
- **New safety metric M-S5 — Road-edge departure** (`road_edge_contact = max|ey| ≥
  road_half_m`, road half-width ≈ 0.26 m, beyond the 0.1225 m lane edge) — the
  cage-efficacy harm proxy, mirroring the M-S3/`emergency` per-run-event ↔ aggregate-rate
  pattern. `max_excursion_m` documented as the realised value of M-S1. Added to `docs/06`.
- **Gazebo executor live.** `run_campaign.execute_run` now drives
  `ros2 launch cobraflex_rl eval_scenario_batch.launch.py` per matrix cell (per-run
  `GZ_PARTITION` isolation, orphan-`gz` reaping, retries, resume) — **no longer a stub.**
- **Scenario-evaluation framework.** `scenario_metrics.py` (`max_excursion_m`,
  `road_edge_contact`, `time_to_recovery_heading`) wired into
  `eval_policy._evaluate_scenario`; `tools/frontier_contrast.py` aggregates the paired
  enforcement-vs-monitoring benefit (`M-S5(monitoring) − M-S5(enforcement)`).
- **Validators/schema taught the FRONT family.** `FRONT` added to the id/category
  allowlists in `check_scenario_yaml.py` and to `RX_SC`/`RX_SC_DEF` in
  `check_traceability.py`; `road_edge_contact`/`max_excursion_m` whitelisted as per-run
  bare-name fields; `_schema.yaml` documents the category and tokens.
- **Decision D-35 recorded** in `docs/DECISIONS.md` (+ index row, + D-34 index row backfilled):
  the frontier scenario family and its **non-verdict-bearing** cage-efficacy semantics —
  the explicit D-30 carve-out that a frontier result never vetoes the global verdict. A
  matching note added to `docs/07` explains the deliberate SC-FRONT absence from the verdict matrix.
- **Cage-efficacy figures wired into the campaign.** `tools/plot_frontier.py` renders the paired
  enforcement-vs-monitoring figures (`fig_frontier_excursion`, `fig_frontier_cage_benefit`)
  **aggregating over the N reps per cell** (mean ± std + road-edge-contact rate) — the same script
  serves the rep00 pilot and the full 25-rep campaign. `run_campaign.py` auto-invokes it after a
  frontier campaign (best-effort; `--no-frontier-plots` to skip; falls back to printing the manual
  command when matplotlib is absent, e.g. the headless ROS host).

### Rationale

The frontier family answers *what the cage is worth*: on an out-of-ODD start the policy is
not designed to recover, so the monitoring arm (no-cage counterfactual) is expected to
reach the road edge while enforcement is not — the contrast is the H-04 cage-value
evidence. The scenarios, the M-S5 harm proxy and a pilot campaign already existed as
**committed run artifacts** (`experiments/sim/campaign_frontier`, today's `F4:` commits) but
were **unregistered** — invisible to the traceability spine and rejected by the scenario
validator (`id must match SC-{NOM|EDGE|PERT}-NN`). This entry closes that orphan gap.

### Impact

- Frontier evidence is **not** folded into the global G4 verdict (D-30; recorded as decision
  **D-35**); it is reported as a per-arm enforcement-vs-monitoring contrast. The 6 × 25 × 2 =
  **300** frontier runs are separate from the ~1100-run verdict-bearing (NOM/EDGE/PERT) campaign.
- No hazard / SR / cage-rule IDs added or changed; one metric added (M-S5).
- Still pending (Ubuntu+Jazzy host): the full verdict-bearing campaign → per-SR sim
  verdicts in `docs/07` (all still `TBD`); scaling the frontier pilot (rep00, seeds 123 &
  2024) to the recommended 25 reps incl. SC-FRONT-01/02/03; the QED-metric decision
  (D-17/D-21/D-22).

### Verification

`python tools/check_scenario_yaml.py --strict` → PASSED, 0 error(s), 0 warning(s).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s)
(Defined scenarios now 17 incl. SC-FRONT-01…06; Defined metrics incl. M-S5).

---

## [07.06.2026] — F3: Ch.7 main seed switched 42 → 2024 (best of the 5); figs + text repointed

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.5, §7.2.7, §7.2.8,
§7.4, §7.5.1–§7.5.3), `manuscript/figures/fig_7_1..fig_7_6` (regenerated),
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md`, `CLAUDE.md`.
**Phase:** F3 (recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Chapter 7 main run changed from seed 42 to `ppo_train_2024_200k` (seed 2024).**
  Of the five trained seeds, 2024 has the **highest reward (536.8)** and the **best
  PPO health (`explained_variance` 0.67)** while tying the best safety (0% cage, 0
  emergencies) with near-best tracking (9.9 mm). Seed 23 tracks marginally tighter
  (6.7 mm) but its value-function fit is weak (`explained_variance` 0.22), so 2024 is
  the more defensible all-around main.
- **Figs 7.1–7.6 regenerated** from the seed-2024 train + eval runs (`--train-run
  ppo_train_2024_200k --rl-run rl_eval_2024_200k_4k4 --pd-run ros_run_20260523T153003Z`).
  Fig 7.8 (multi-seed) unchanged.
- **§7.4/§7.5.1–§7.5.2 text repointed** to seed 2024: convergence (`ep_rew` 20.9→536.8,
  saturation ~75k), `explained_variance` (0.67, max 0.81), intervention co-adaptation
  (~90%→3.4%), entropy (1.42→−1.52), eval (11.2 laps, mean |ey| 9.9 mm, max 23 mm,
  **0% cage / 0 interventions**, raw |Δ| 0.030, sign-flips 1.1%).
- **Stale "Nota de cobertura" (§7.2.8) corrected** — it claimed the definitive cycle
  used the legacy 4-column schema; all five seeds carry the extended instrumentation.
- **`docs/09` (ED-10), `docs/10`, `CLAUDE.md` synced** to the seed-2024 smoothness /
  cage numbers (0.030 / 1.1% / 0% vs the old 0.031 / 3.3% / 0.023%).

### Impact

- The §7.5.3 multi-seed table / Fig 7.8 still report all five seeds (incl. seed 42);
  only the *main* detailed run changed. The F4 campaign should use the seed-2024
  checkpoint as the RL controller.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --train-run … --rl-run … --pd-run …` → figs 7.1–7.6.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [07.06.2026] — F3: seed-666 cycle added; multi-seed complete (N=5, 4/5 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 5 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Fifth and final training cycle `ppo_train_666_200k`** (seed 666, 200k, reward
  v1.2) + eval `rl_eval_666_200k_4k4`. Constraint-respecting: ep_rew 529.3, training
  intervention → 11 %, eval cage 1.55 % (**C-06 only**, smoothing), mean |ey| 8.0 mm,
  max 26 mm, 0 emergencies, 11.1 laps.
- **Multi-seed campaign complete at N = 5: 4/5 constraint-respecting (42, 2024, 23,
  666), 1/5 cage-dependent (123).** §7.5.3 table (5 columns), analysis, caption and
  Fig. 7.8 updated to five seeds; §7.2.7 records N = 5 reached. The 4-vs-1 bimodality
  (seed 123 the lone outlier) fixes the observed `w_ds` / M-P4 distribution at 80 % CR.

### Impact

- Multi-seed reporting closed: five seeds reported individually in Ch.7 (§7.5.3,
  Fig. 7.8). Seed 42 remains the §7.5.1–§7.5.2 main; median±band deliberately omitted
  (bimodal — would mask the two basins). `w_ds` sensitivity analysis stays for Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>,<23>,<666>` → fig_7_8 (5 lines).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-23 cycle added; multi-seed now 4 seeds (3/4 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 4 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Fourth training cycle `ppo_train_23_200k`** (seed 23, 200k, reward v1.2) + eval
  `rl_eval_23_200k_4k4`. Constraint-respecting, with the **tightest tracking** of the
  four: ep_rew 535, training intervention → 5 %, eval cage 0 %, mean |ey| **6.7 mm**,
  max 22 mm, 0 emergencies, 11.1 laps.
- **Multi-seed result is now 3/4 constraint-respecting (42, 2024, 23), 1/4
  cage-dependent (123).** §7.5.3 table (4 columns + basin row), analysis and Fig. 7.8
  updated; §7.2.7 notes four seeds trained. The 3-vs-1 split (seed 123 the lone
  outlier) sharpens the `w_ds` / M-P4 sensitivity point.

### Impact

- Four seeds reported individually in Ch.7 (§7.5.3, Fig. 7.8). Seed 23 is the best
  tracker (6.7 mm), but seed 42 remains the §7.5.1–§7.5.2 main. N≥5 (a fifth seed) +
  median±band stay for Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>,<23>` → fig_7_8 (4 lines).
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-2024 cycle added; multi-seed comparison now 3 seeds (2/3 constraint-respecting)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (regenerated, 3 seeds).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3.
**Author:** Samuel.

### Change

- **Third training cycle `ppo_train_2024_200k`** (seed 2024, 200k, reward v1.2) +
  eval `rl_eval_2024_200k_4k4`. It converges **constraint-respecting**, like seed 42
  (marginally cleaner): ep_rew 537, training intervention → 3 %, eval cage **0 %**,
  mean |ey| **9.9 mm**, max 23 mm, 0 emergencies, 11.2 laps.
- **Multi-seed result is now 2/3 constraint-respecting (42, 2024), 1/3
  cage-dependent (123).** §7.5.3 table + analysis + Fig. 7.8 updated to three seeds;
  §7.2.7 notes seed 23 (4th) in progress. The 2-vs-1 split sharpens the `w_ds`
  (M-P4) sensitivity point: the smoothness weight yields constraint-respecting in the
  majority of seeds but not reliably.

### Impact

- Three seeds reported individually in Ch.7 (§7.5.3, Fig. 7.8). Seed 2024 is
  marginally the best policy (537, 0 % cage, 9.9 mm); seed 42 remains the
  §7.5.1–§7.5.2 main. N≥5 consolidation (seed 23 + one more) stays in Ch.8.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs <42>,<123>,<2024>` → fig_7_8_multiseed.png
(3 lines). `python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [06.06.2026] — F3: seed-123 cycle + multi-seed comparison (constraint-respecting vs cage-dependent); Fig. 7.8 + §7.5.3

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.7, new §7.5.3),
`manuscript/figures/fig_7_8_multiseed.png` (new),
`tools/plot_f3_figures.py` (`--seed-runs` / `fig_multiseed`).
**Phase:** F3 (multi-seed; recorded during F4).
**Gate context:** after G3 — adds the multi-seed evidence deferred at §7.2.7.
**Author:** Samuel.

### Change

- **Second training cycle `ppo_train_123_200k`** (seed 123, 200k, reward v1.2, same
  config) + eval `rl_eval_123_200k_4k4`. It converges to a **cage-dependent** basin,
  in contrast to seed 42's **constraint-respecting** one:
  - seed 42: ep_rew 530, training intervention → 5 %, eval cage 0.02 %, mean |ey| 11.6 mm.
  - seed 123: ep_rew 443, training intervention → 74 %, eval cage **58.8 %** (C-06 58 %,
    C-01 6 %, C-03 3 %), mean |ey| **90.7 mm**, max |ey| **145 mm**. Both: 0 emergencies, ~11 laps.
- **New §7.5.3** reports the comparison: both policies are safe (the cage guarantees
  it), but seed 123's worse policy needs the cage *actively* — C-01/C-03 prevent lane
  departure in real time — the strongest cage-utility evidence so far, which the
  nominal-only seed-42 result could not provide. Framed as the `w_ds` (smoothness
  weight) sensitivity flagged by M-P4.
- **Fig. 7.8** (multi-seed reward + intervention overlay) + `tools/plot_f3_figures.py
  --seed-runs` to generate it. §7.2.7 updated (seed 123 done, 2024 pending;
  bimodality → report seeds individually, not only a median).

### Rationale

The nominal seed-42 evaluation showed the cage latent (0.02 %), so its protective
value had to be argued indirectly. Seed 123 — same code, different basin — drives
poorly enough (90 mm mean offset, peaks crossing the lane half-width) that the cage
intervenes 58.8 % of steps, with C-01/C-03 actively preventing lane departure. The
two seeds together show the cage's value *depends on the policy* and that it performs
at both ends (latent vs active protector).

### Impact

- Multi-seed evidence now in Ch.7 (§7.5.3, Fig. 7.8). N≥5 consolidation (seed 2024 and
  beyond) stays in Ch.8; bimodality → seeds reported individually.
- No hazard / SR / cage-rule / metric / scenario IDs added or changed.

### Verification

`python tools/plot_f3_figures.py --seed-runs experiments/sim/training/ppo_train_42_200k,experiments/sim/training/ppo_train_123_200k`
→ fig_7_8_multiseed.png. Chapter figure refs monotonic 7.1→7.8.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [04.06.2026] — F4: SR-002/005/007 nominal-family coverage added; scenario library now 11/11 D-29-feasible

**Document(s) affected:**
`docs/03_safety_requirements.md` (SR-002/005/007 Scenarios += SC-NOM-03),
`docs/data/safety_requirements.csv` (regenerated),
`docs/05_scenario_library.md` (SC-NOM-03 References SR + nominal-coverage note),
`scenarios/nominal/sc_nom_03.yaml` (references_SR += SR-005/007; M-P4 gate).
**Phase:** F4 (entry).
**Gate context:** after G3 — closes the 3 D-29 nominal-coverage gaps the campaign
dry-run surfaced; the scenario library is now fully D-29-feasible.
**Author:** Samuel.

### Change

- **SR-002 / SR-005 / SR-007 gain nominal-family coverage via SC-NOM-03** (the
  full-circuit run, 25 nominal runs), so each of these SR-CL-A is now verified in a
  nominal *and* an adverse family (D-29). SR-002 (heading) is verified positively —
  M-P4 promoted to primary with a `M-P4 < 0.436` (θ_max = 25°) gate. SR-005
  (compound-state emergency) and SR-007 (state staleness) are verified as
  **no-false-activation** checks: their hazards do not arise in nominal, so the
  nominal evidence is `emergency == False` / M-S3 = 0 over the run (documented in
  docs/05). A pre-existing docs/03↔docs/05 inconsistency (SC-NOM-03 already
  referenced SR-002 on the scenario side but not in the SR register) is resolved.
- `safety_requirements.csv` regenerated from docs/03 via
  `tools/sync_safety_requirements.py`.

### Rationale

The dry-run showed SR-002/005/007 (all SR-CL-A) verified only in adverse families,
failing D-29's nominal+adverse requirement. SC-NOM-03 already exercises the relevant
metrics (M-P4 heading, M-S3 emergency) over an extended nominal run, so it is the
natural nominal carrier. The no-false-activation framing keeps the emergency-SR
nominal evidence honest rather than fabricating a positive demonstration of a hazard
that cannot occur in nominal.

### Impact

- `run_campaign --dry-run`: **0 GAP — 11/11 SRs D-29-feasible** (was 3 GAP). The
  scenario library is ready for the campaign (pending the Gazebo executor).
- No hazard / SR / cage-rule / metric / scenario IDs added or changed; only the
  SR↔scenario links and SC-NOM-03's metrics/gate.

### Verification

`python tools/sync_safety_requirements.py` → 11 SRs written.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).
`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 0 warnings.
`python tools/run_campaign.py --dry-run` → 0 SR not feasible (11/11).

---

## [04.06.2026] — F4: 7 scenario stubs promoted to full YAMLs; dry-run resolves D-29 run-count gaps

**Document(s) affected:**
`scenarios/{nominal,edge,perturbed}/*.yaml` (7 stubs → full: SC-NOM-02/03,
SC-EDGE-02/03/04, SC-PERT-01/02), `docs/05_scenario_library.md` (SC-EDGE-03 /
SC-NOM-03 run counts → 25), `tools/run_campaign.py` ("ALL" convention + message),
`policy/tests/test_run_campaign.py`.
**Phase:** F4 (entry).
**Gate context:** after G3 — the `run_campaign --dry-run` had flagged the 7 stubs
as blocking SR coverage; this promotes them and closes the run-count gaps.
**Author:** Samuel.

### Change

- **7 stub scenarios promoted to full, schema-valid YAMLs** (SC-NOM-02 curved
  nominal, SC-NOM-03 full circuit, SC-EDGE-02 lateral, SC-EDGE-03 speed pulse,
  SC-EDGE-04 compound, SC-PERT-01 sensor noise, SC-PERT-02 latency), translated
  from docs/05 onto the oval track mapping, with a small per-run randomisation so
  the runs are **independent** (D-29) and pass criteria on catalogued M-* metrics.
  `check_scenario_yaml.py` now reports 0 warnings (was 7 stubs).
- **Run-count reconciliation for D-29.** SC-EDGE-03 (verifies SR-004) and SC-NOM-03
  (verifies SR-008) bumped 20 → 25 runs/mode, the SR-CL-A minimum (D-29); docs/05
  updated to match.
- **`run_campaign.py`:** handle the docs/05 "ALL" scenario convention (SR-006, the
  always-active rate limiter, is verified by every scenario), and fix the stale
  "blocked by stubs" message.

### Rationale

The `--dry-run` planner showed 8/11 SRs not D-29-feasible because the verifying
scenarios were stubs. Promoting them + the two run-count bumps + the SR-006 fix
brings it to **8/11 feasible**. The remaining 3 gaps (SR-002, SR-005, SR-007) are
**structural**: each is verified only in adverse (EDGE/PERT) scenarios, while D-29
requires an SR-CL-A to be covered in a nominal family too. Closing those needs a
scenario↔SR mapping decision (add a nominal reference, or argue the SR is
inherently adverse) — deferred to the supervisor.

### Impact

- D-29 feasibility: 3/11 → **8/11** SRs feasible (dry-run). Remaining GAPs: SR-002,
  SR-005, SR-007 (no nominal-family coverage — design decision).
- No hazard / SR / cage-rule / `cage.yaml` / metric / scenario IDs added or changed;
  only the 7 YAML bodies and two run counts changed. The 11 scenario IDs stay
  consistent with docs/05 and the traceability matrix.

### Verification

`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 0 warnings.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).
`python -m pytest policy/tests/test_run_campaign.py` → 11 passed.
`python tools/run_campaign.py --dry-run` → 11/11 executable, 8/11 SRs D-29-feasible.

---

## [04.06.2026] — F4: scenario track-mapping reconciliation + campaign-runner core (plan + D-29/D-30 aggregation)

**Document(s) affected:**
`docs/05_scenario_library.md` (new "Track mapping" section),
`scenarios/{nominal,edge,perturbed}/*.yaml` (11 files: explicit `track` block +
`commanded_speed_mps`), `tools/run_campaign.py` (new),
`policy/tests/test_run_campaign.py` (new).
**Phase:** F4 (entry).
**Gate context:** after G3 — prepares the L2′ campaign for launch: pins the
scenarios to the trained world and provides the orchestration/verdict spine.
**Author:** Samuel.

### Change

- **Scenario↔world reconciliation (Option A — run on the oval).** The scenarios
  were specified (Phase 2) in abstract geometry without a world, while the policy
  and PD baseline were trained/validated only on the oval. Every scenario YAML now
  carries an explicit `track` block (`world: lane_following_oval.world`,
  `centerline: oval_right_lane_centerline.yaml`, `start_s_m` = 0.0 straight start /
  1.5 curve entry for SC-NOM-02) and `commanded_speed_mps: 0.2` (the env fixed
  speed, superseding the per-scenario 0.3–0.4 prose). Documented authoritatively in
  a new "Track mapping" section of `docs/05`. `straight_road.world` is reserved for
  the Phase-5 physical subset. No retraining needed — the policy already drives the
  oval's κ=0 straights.
- **Campaign-runner core `tools/run_campaign.py`.** Pure, ROS-free orchestration +
  aggregation: scenario/SR loading, run-matrix generation
  (scenario × mode × controller × seed × rep), per-run verdict from the
  pass-criterion strings (sandboxed eval), and aggregation per **D-29** (≥25
  runs/family for SR-CL-A, 10 for SR-CL-B, nominal+adverse coverage) and **D-30**
  (any SR-CL-A failure vetoes the global verdict). A `--dry-run` planner validates
  the run matrix and the D-29 feasibility against the current library before any
  run is launched. The Gazebo executor (`execute_run`: mode/start_s/perturbation
  via `eval_policy`) is a documented stub for the Ubuntu+Jazzy host.

### Rationale

Launching F4 needs two things this change provides: (a) the scenarios must point at
the world the policy actually runs on (they did not), and (b) an orchestration spine
that turns the campaign into per-SR and global verdicts under the agreed counting
(D-29) and veto (D-30) rules. The `--dry-run` surfaces, before spending the run
budget, that 8 of 11 SRs are not yet feasible because the scenarios that verify them
are still stubs — making "promote the 7 stub scenarios" the concrete next F4 task.

### Impact

- `--dry-run` on the current library: 11 scenarios (4 executable, 7 stub),
  1760 matrix runs, 3/11 SRs D-29-feasible (SR-009/010/011), 8 GAP (stub-blocked).
- Known refinement: the SR-006 "ALL"-scenario convention (docs/05) is not yet
  special-cased in the runner (shows as a gap).
- No hazard / SR / cage-rule / `cage.yaml` / metric IDs added or changed; the 11
  scenario IDs are unchanged (only their YAML bodies gained the `track` block).

### Verification

`python tools/check_scenario_yaml.py` → PASSED, 0 errors, 7 warnings (the
pre-existing stubs). `python -m pytest policy/tests/test_run_campaign.py` →
11 passed. `python -m py_compile tools/run_campaign.py` → OK.
`python tools/check_traceability.py` → All checks PASSED, 0 warning(s).

---

## [04.06.2026] — F3: extended training instrumentation + re-instrumented seed-42 cycle; Ch.7 figures 7.1–7.7

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.6 hyperparameter table,
§7.2.7 multi-seed note, §7.2.8 CSV schema, §7.4 + Figures 7.2–7.4, §7.5 + §7.5.2),
`manuscript/figures/fig_7_1..fig_7_7*.png` (regenerated + renumbered to reading order),
`src/cobraflex_rl/cobraflex_rl/training_metrics.py` (new), `.../callbacks.py`,
`.../train_ppo.py`, `tools/plot_f3_figures.py`,
`policy/tests/test_training_metrics.py` (new),
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md` (§5), `CLAUDE.md`.
**Phase:** F3 (Training Spec / Ch.7 refinement; recorded during F4).
**Gate context:** after G3 — closes the co-adaptation-evidence gap left open at G3 (the
training-time cage-intervention curve was never logged, so the cage's contribution had to
be argued indirectly).
**Author:** Samuel.

### Change

- **Extended PPO learning-curve logger.** `LearningCurveCallback` now records, per rollout,
  the PPO-health scalars (`value_loss`, `entropy = −entropy_loss`, `approx_kl`,
  `clip_fraction`, `std`) and the safety-cage activity (`intervention_rate`,
  `emergency_rate`, per-rule `int_rate_C-01..C-06`) — a superset of the legacy 4-column
  schema (§7.2.8). New `ActionSampleCallback` → `action_samples.csv` (subsampled raw
  steering). Aggregation lives in the pure, dependency-free `training_metrics.py`
  (unit-tested in `policy/tests/test_training_metrics.py`, 10 tests).
- **Re-instrumented definitive cycle.** `ppo_train_42_200k` (run_id
  `ppo_train_20260603T203630Z`, seed 42, 200k, reward v1.2) + eval `rl_eval_42_200k_4k4`
  (run_id `rl_eval_20260604T083959Z`) replace the prior seed-42/200k run (retained as
  `*_old`): same config, now with the full logging. §7.4/§7.5 rewritten around it.
- **Figures 7.1–7.7, renumbered to reading order.** New training-dynamics figures —
  7.2 (cage intervention + per-rule co-adaptation), 7.3 (value-loss/entropy), 7.4 (action
  distribution) — and the eval figures renumbered (7.5 trajectory, 7.6 tracking error,
  7.7 Gazebo capture). `tools/plot_f3_figures.py` emits all six auto-generated figures.
- **§7.2.6 hyperparameter table** completed to the full effective SB3 2.8.0 config
  (`n_epochs`, `gae_lambda`, `clip_range`, `ent_coef`, `vf_coef`, `max_grad_norm`,
  `normalize_advantage`) + `MlpPolicy` architecture note.
- **Number sync** to the new run in `docs/09` (ED-10), `docs/10` (§5) and `CLAUDE.md`.

### Rationale

At G3 the nominal evaluation showed ~0% cage interventions, so co-adaptation could only be
argued indirectly. The direct signal — the cage intervention rate *during training* — was
not logged. The extended logger captures it: the new cycle shows the intervention rate
falling monotonically from ~89% to ~4.7% (Figure 7.2), entropy decaying 1.42 → −1.56
(Figure 7.3) and the raw action distribution moving from bang-bang to smooth (Figure 7.4) —
the constraint-respecting co-adaptation the methodology predicts.

### Impact

- **Result (re-instrumented run):** `ep_rew_mean` → 530.2, `ep_len_mean` → 500,
  `explained_variance` → 0.55; eval 11.03 laps, 0 emergencies, mean |ey| 11.6 mm (×2.0 vs
  PD), cage 0.023% (one C-06 step). Slightly less precise than the prior seed-42 run
  (6.5 mm) — run-to-run variance, not budget: 200k is saturated (plateau from ~83k).
- Additional seeds (123, 2024, …) under the **same** config are in progress; the
  median±band overlay and the §7.2.7 cross-seed consolidation are deferred to that set
  (Ch.8).
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python -m pytest policy/tests/test_training_metrics.py` → **10 passed**.
`python -m py_compile` on `training_metrics.py`, `callbacks.py`, `train_ppo.py`,
`plot_f3_figures.py` → OK. `tools/plot_f3_figures.py` regenerates `fig_7_1..fig_7_6` with
the new names. `python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F4: SR criticality single-sourced into the SR register CSV

**Document(s) affected:**
`docs/03_safety_requirements.md` (machine-readable SR table → new Criticality column),
`tools/sync_safety_requirements.py` (`column_mapping` + `fieldnames`),
`docs/data/safety_requirements.csv` (regenerated; new `criticality` column),
`src/cobraflex_rl/cobraflex_rl/verdict_aggregation.py`,
`policy/tests/test_verdict_aggregation.py`.
**Phase:** F4.
**Gate context:** after G3 — closes the follow-up flagged in the 03.06 "verdict spine" entry
(drop the injected criticality map once the SR sync pipeline carries the column).
**Author:** Samuel.

### Change

Restored single-source-of-truth for the SR criticality class (SR-CL-A/B/C), which until now
lived only in the manuscript SRS table (ch.4 §4.7 "Criticidad") and was duplicated in code:

- Added a **Criticality** column to the machine-readable SR table in
  `docs/03_safety_requirements.md`, with values mirrored from ch.4: SR-001..SR-005, SR-007,
  SR-008 = SR-CL-A; SR-006, SR-009, SR-010, SR-011 = SR-CL-B (7× A, 4× B).
- Extended `tools/sync_safety_requirements.py` (`column_mapping` + `fieldnames`) to extract and
  emit a `criticality` column, and regenerated `docs/data/safety_requirements.csv`.
- `verdict_aggregation.load_sr_registry` now reads criticality from the CSV; the hard-coded
  `SR_CRITICALITY` map (previously cited to ch.4 / D-28) and its guard test
  `test_sr_criticality_matches_csv` are deleted. The criticality-count assertion
  (7× SR-CL-A, 4× SR-CL-B) is retained, now sourced from the CSV-built registry.

### Rationale

The injected map duplicated a fact that belongs in the generated register; the duplication was
only kept honest by a guard test. Carrying `criticality` through the Markdown→CSV sync removes
both the duplication and the guard, so the D-29 run-count gate and D-30 SR-CL-A veto read the
same source the manuscript does.

### Impact

- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed; SR semantics
  unchanged — only the criticality attribute is relocated to its single source.
- One CSV column added (`criticality`). `load_sr_registry` is its only consumer and is updated;
  an empty/absent column falls back to SR-CL-C, preserving the previous default for unknown SRs.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
`python -m pytest -q` → **233 passed** (guard test removed, count assertion retained and now
CSV-sourced; net test count unchanged).

---

## [03.06.2026] — F4: verdict spine (campaign metrics, criterion eval, scenario loader, SR verdict aggregation)

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/campaign_metrics.py`, `…/criterion_eval.py`,
`…/scenario_loader.py`, `…/verdict_aggregation.py` (all new),
`policy/tests/test_campaign_metrics.py`, `…/test_criterion_eval.py`,
`…/test_scenario_loader.py`, `…/test_verdict_aggregation.py` (all new).
**Phase:** F4.
**Gate context:** after G3 — the pure-Python core of the scenario-campaign verdict pipeline
(deliverable 2; the Gazebo-coupled driver + env stressor hooks are Phase C, deferred).
**Author:** Samuel.

### Change

The ROS-free, unit-tested core that turns per-run results into per-SR and global verdicts.
Mirrors the pure style of `eval_metrics.py` so it runs under `pytest` on any host (the Gazebo
campaign driver, Phase C, will feed it):

- **`campaign_metrics.py`** — full per-run metric catalogue (docs/06): M-P1/P3/P4/P5/P6/P7,
  M-S1/S2/S3/S4, M-I1/I2/I3/I4/I5, M-C1/C2, computed from the `cage_status.csv` per-step record
  schema. Reports an `availability` map for metrics needing data absent from that schema (M-S4
  needs a ttlc series; M-P3 and M-I4's C-04 arm need per-step curvature; M-C* unmeasured in sim;
  M-I5 is steering-only). Plus `aggregate_metric` (median/mean/std/p5/p95).
- **`criterion_eval.py`** — safe, `eval()`-free, **three-valued** evaluator for the
  `pass_criterion_*` strings (conjunction of comparisons; labelled multi-arm for SC-PERT-03). An
  unavailable metric yields *indeterminate* (None), never a false fail.
- **`scenario_loader.py`** — scenario YAML → typed `RunSpec`; skips stubs; exposes the
  nominal/adverse `family` the D-29 gate needs.
- **`verdict_aggregation.py`** — per-scenario (`fraction_pass`) → per-SR → global verdict,
  implementing **D-29** (SR-CL-A needs ≥25 runs in a nominal AND an adverse family; SR-CL-B ≥10
  in ≥1 family; SR-CL-C informal) and **D-30** (any SR-CL-A failure vetoes the global verdict).
  SR criticality is injected from `SR_CRITICALITY` (cited to the ch.4 SRS table / D-28) with a
  guard test asserting it matches `docs/data/safety_requirements.csv`.

### Rationale

The verdict logic is the reusable, correctness-critical heart of the F4 campaign and is pure
data-in/data-out, so it is built and **unit-tested on the Windows host** (the Gazebo campaign
cannot run here). Per-run verdicts are produced by `criterion_eval` on each run's metrics and
fed into `verdict_aggregation` as data, keeping the D-29/D-30 logic testable with synthetic
inputs.

### Impact

- **Finding (surfaced by a test):** SR-002, SR-005, SR-007 (all SR-CL-A) are mapped only to
  *adverse* scenario families in the SRS, so the D-29 "nominal AND adverse" gate **cannot be met
  as currently mapped** — each needs a nominal verifying scenario, or a documented D-29 exception
  for inherently-adverse requirements. Flagged for review; not changed here.
- Phase C (deferred, to run on the Ubuntu host): extend `GazeboLaneEnv` with stressor hooks
  (deterministic ICs, perception noise, action latency, throttle pulse) + a `run_campaign.py`
  driver writing `experiments/sim/<SC>_<mode>/run_NNN/` and calling this spine.
- Follow-ups flagged: harden `close_odd_tbds.py` (prose-mention substitution footgun); add a
  `criticality` column to the SR sync pipeline so `verdict_aggregation` can drop the injected map.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python -m pytest -q` → **233 passed** (58 new across the four modules; no regression).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F4: ODD-2 adverse stressor profiles closed (TBD-Q4–Q7, Q12)

**Document(s) affected:**
`src/cobraflex_rl/config/adverse_profiles.yaml` (new),
`docs/08_odd_specification.md` (§5.5, §7.2, §11, cover block → v0.5),
`docs/DECISIONS.md` (D-33 status table + status-update note),
`experiments/odd_inspection/odd_tbds.yaml` (Q4–Q7, Q12 values).
**Phase:** F4.
**Gate context:** after G3 — F4-entry prerequisite (the adverse scenario families need
parameterised stressor profiles before the campaign can run).
**Author:** Samuel.

### Change

- **New machine-readable source of truth** `src/cobraflex_rl/config/adverse_profiles.yaml`:
  per-profile stressor parameters for the ODD-2 named profiles (+ the ODD-4 cross-product),
  to be consumed by the F4 campaign runner for stressor injection.
- **ODD-Spec TBD closures (D-33):**
  - **Q4** `odd2_nominal_adverse` — σ_lateral=0.03 m (SC-PERT-01 mid level) + faded markings
    / non-uniform light via `lane_following_oval_worn.world`.
  - **Q5** `odd2_adverse_with_latency` — +100 ms latency (SC-PERT-02 high, over the 50 ms
    nominal) + 20 ms jitter + 0.02 steering actuation noise.
  - **Q6** `odd2_adverse_with_obstacle` — 1 static 0.10 m box, ~0.05 m lane intrusion at
    mid-straight. **Specified only; execution deferred** — the F3 policy observes a 6-dim
    vector with no obstacle channel (§5.1 specifies an 8-dim ODD-2 obs); the campaign skips
    `execution: deferred` profiles until obstacle perception is wired.
  - **Q7** `odd2_adverse_full` — union of Q4+Q5+Q6 (inherits Q6's execution deferral).
  - **Q12** ODD-4 — no additional stressors; the ODD-4 profiles are the pure cross-product
    of ODD-3 geometry × ODD-2 stressors.
  - ODD-Spec §5.5 table now mirrors `adverse_profiles.yaml` with per-column values; §7.2
    ODD-4 table and §11 resolution rows filled; cover block → **v0.5**, **11 of 12** TBDs
    resolved (only Q10 remains, deferred to M-4 physical calibration).

### Rationale

The ODD-2 adverse profiles parameterise the perturbed/adverse scenario families the F4
campaign verifies. Magnitudes are grounded in the existing scenarios (σ from SC-PERT-01,
latency from SC-PERT-02) and the 50 ms `*.LATENCY_NOMINAL`, not invented.

Closed **by hand** rather than via `tools/close_odd_tbds.py --apply`: the dry-run showed the
tool's blanket `TBD-QN` substitution would (a) repeat one value across the three σ/latency/
jitter columns of the §5.5 table, and (b) **corrupt prose mentions of already-closed TBDs** —
the §0.1 change-log rows and the §9 source column — because it cannot tell a placeholder cell
from a documentation mention. `odd_tbds.yaml` is kept in sync as provenance; D-33 records the
decision and flags hardening the tool as a separate follow-up.

### Impact

- Closes the F4-entry ODD prerequisite. Remaining F4 work unchanged (campaign runner +
  per-SR verdicts **D-29/D-30**, QED decision, sim verdicts in `docs/07`).
- Obstacle scenarios are spec'd but not executed by the campaign (no obstacle perception);
  flagged in `adverse_profiles.yaml`, §5.5, and the D-33 table.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
`python tools/check_scenario_yaml.py` → **PASSED, 0 errors, 7 warning(s)** (deferred stubs).
`adverse_profiles.yaml` and `odd_tbds.yaml` parse as valid YAML.

---

## [03.06.2026] — F4 entry: Gate G3 passed, F3 closed; scenario library completed (SC-EDGE-05, SC-PERT-03)

**Document(s) affected:**
`scenarios/edge/sc_edge_05.yaml` (new), `scenarios/perturbed/sc_pert_03.yaml` (new),
`CLAUDE.md` (phase snapshot → F4).
**Phase:** F4 (entry).
**Gate context:** **Gate G3 passed 2026-06-03**, closing F3 (PPO training). This is the
F3→F4 transition the prior 03.06 entry left pending ("the closing commit / F4 entry").
**Author:** Samuel.

### Change

- **Gate G3 / F3 close-out.** F3 (PPO training) is closed. Closing evidence: the
  definitive reward-v1.2 cycle `ppo_train_42_200k` (seed 42/200k, saturated) and its
  re-evaluation `rl_eval_42_200k_4k4` (SC-NOM-01, 11.2 laps, 0 emergencies, 0% cage
  intervention); the Training Spec (Ch.7 §7.2–§7.5) is complete; the mechanical gate
  `tools/check_traceability.py` passes with 0 warnings. Phase enters **F4 — Sim eval**
  (scenario-based validation campaign; closes at G4).
- **Scenario library completed to 11/11 documented.** The two documented scenarios
  that had no YAML file are now full, schema-valid executable YAMLs translated from
  `docs/05_scenario_library.md`:
  - `SC-EDGE-05` (cage-rule co-activation matrix, SR-010): parameterised
    `(d, θ, v, dκ/dt)` grid with the five documented pair/triple co-activation anchors;
    primary metrics M-S2/M-I2/M-I3; ≥100 runs per mode (5 reps × ≥20 grid points);
    per-run verdict = no joint-envelope assertion failure, M-S2 = 0, no inter-cycle
    oscillation; ≥95% of grid points pass.
  - `SC-PERT-03` (reward-injection stall test, **negative** test for SR-009): two-arm
    (released vs ~50k-step stall-fine-tuned) design; primary metrics M-P6/M-P2; 40 runs
    per mode (20+20), 80 total; verdict = stall variant M-P6 > 0.50 while released
    M-P6 = 0 and M-P2 = 1; ≥90% of runs pass.

### Rationale

"Initiating F4" requires (a) formally closing F3 at G3 and (b) bringing the scenario
library — the L2′ artefact F4 executes — to full documented coverage. SC-EDGE-05 and
SC-PERT-03 were the only two documented scenarios with no YAML at all (the other seven
non-F2 scenarios remain explicit stubs, full YAMLs deferred); they are written first
because they carry the most design content and verify the two SRs (SR-010 joint-envelope,
SR-009 stall) least served by off-the-shelf tooling.

### Impact

- **F4 scope now open.** Remaining F4 entry work (not in this change): the ODD-2 adverse
  scenario profiles (TBD-Q4–Q7, Q12 — `docs/DECISIONS.md`), the multi-run campaign runner
  + per-SR verdict aggregation (run-count convention D-29, veto rule D-30), the QED-metric
  decision (D-17/D-21/D-22), and filling the sim verdicts in `docs/07_traceability_matrix.md`.
  The seven sibling scenario stubs (NOM-02/03, EDGE-02/03/04, PERT-01/02) are promoted to
  full YAMLs as the campaign reaches them.
- No hazard / SR / cage-rule / `cage.yaml` / metric IDs added or changed. No scenario IDs
  added — SC-EDGE-05 and SC-PERT-03 were already in the traceability matrix; only their
  YAML *implementations* are new.

### Verification

`python tools/check_scenario_yaml.py` → **PASSED, 0 errors, 7 warning(s)** (the two
"documented but has no YAML file yet" warnings for SC-EDGE-05/SC-PERT-03 are cleared; the
7 remaining are the deferred sibling stubs).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [03.06.2026] — F3 definitive cycle: seed-42/200k under reward v1.2 (native smoothness, 0 cage interventions)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md`
(§7.2.4–§7.2.7, §7.4, §7.5, §7.5.2),
`manuscript/figures/auto/fig_7_1_convergence.png`,
`manuscript/figures/auto/fig_7_2_trajectory.png`,
`manuscript/figures/auto/fig_7_2b_tracking_error.png`,
`docs/09_environment_design.md` (ED-10), `docs/10_reward_function.md`,
`CLAUDE.md` (status snapshot).
**Phase:** F3.
**Gate context:** after G2 — closes the reward-v1.2 backlog item from the two prior
02.06 entries; supersedes the 250k/seed-123 (reward v1.0) cycle.
**Author:** Samuel.

### Change

- **New definitive training cycle `ppo_train_42_200k`** (run_id
  `ppo_train_20260602T145922Z`, seed 42, 200 000 timesteps, **reward v1.2**,
  commit 666249c, ~6.2 h real, fps≈9, 196 iterations of 1 024). It **supersedes**
  both prior cycles — the preliminary 50k (not saturated) and the 250k/seed-123
  reward-v1.0 cycle (saturated but C-06-dependent). §7.4/§7.5 rewritten around it.
- **Convergence (§7.4.1):** `ep_rew_mean` 24.8 → plateau **535.2** (max 535.2);
  `ep_len_mean` 48.0 → **500.0**. `ep_len_mean` reaches 500 by ~71k timesteps,
  `ep_rew_mean` hits 90% of final (~482) by ~84k, then climbs gently to 535.2 over
  the plateau (episode length pinned at 500 throughout). `explained_variance`
  averages 0.56 on the plateau, final **0.63** (max 0.82) — above the 0.5 threshold.
- **Re-evaluation `rl_eval_42_200k_4k4`** (run_id `rl_eval_20260603T075419Z`,
  SC-NOM-01, 1 deterministic episode of 4 400 steps ≈ **11.17** continuous laps,
  checkpoint hash 150e496d…). §7.5.1/§7.5.2 refreshed.
- **Hyperparameters §7.2.6:** `total_timesteps` 250 000 → **200 000**; §7.2.7 seed
  note now seed 42 under reward v1.2.
- **Figures regenerated** from the new cycle + eval:
  `python tools/plot_f3_figures.py --train-run experiments/sim/training/ppo_train_42_200k --rl-run experiments/sim/runs/rl_eval_42_200k_4k4 --pd-run experiments/sim/runs/ros_run_20260523T153003Z`
  (explicit pins **required**: the re-checked-in seed runs share one mtime, so
  `plot_f3_figures.py`'s mtime auto-pick is ambiguous).
- **ED-10 / `docs/10`:** the reward-v1.2 effect, previously "pending re-train", is
  marked **confirmed**.

### Rationale

The two 02.06 entries left an open loop: reward v1.2 (raw-Δsteer smoothness term,
`w_ds` 0.10→0.20) was wired and unit-tested, but its effect on native RL smoothness
"required a new training cycle". This cycle is that re-train, and it confirms the
hypothesis: the policy now steers smoothly on its own (sign-flips **1.1%** vs ~46%,
**0%** ±1 saturation, mean |Δraw| **0.027** — below C-06's 0.15 limit), so the cage
never has to rate-limit it in nominal.

### Impact

- **Result:** PPO matches the PD on safety (**0 C-05 emergencies over 11.2 laps**)
  and beats it on tracking (mean |ey| 23 mm → **6.5 mm**, ×3.6, max 18 mm; mean
  |epsi| 4.3° → **1.9°**, ×2.3). Cage intervention 0.047% (PD) → **0%** (PPO):
  `raw ≡ safe` at every one of the 4 400 steps. The 89.0%/all-C-06 of the prior
  reward-v1.0 cycle is **superseded** — the cage is now a latent safeguard in
  nominal, its protective value reserved for the Ch.8 edge/perturbed scenarios.
- The other seed runs checked in alongside (`*_old` training dirs: 2024/200k,
  123/250k, 42/50k — reward-v1.0 or under-trained) are retained for the record;
  **only seed-42/200k is the definitive reward-v1.2 run.** Multi-seed (N≥5) stays
  deferred to Ch.8 (§7.2.7).
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
Chapter §7.4/§7.5 quantitative claims reproduce from
`experiments/sim/training/ppo_train_42_200k/learning_curve.csv` and
`experiments/sim/runs/rl_eval_42_200k_4k4/cage_status.csv`.

---

## [02.06.2026] — F3 reward v1.2: smoothness term on the raw policy Δsteer (penalise bang-bang)

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/rewards.py`,
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_rewards.py`,
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.3, §7.2.5, §7.5.2),
`docs/10_reward_function.md`, `docs/09_environment_design.md` (ED-10).
**Phase:** F3.
**Gate context:** after G2 — non-blocking refinement from the §7.5.2 backlog (not required for G3).
**Author:** Samuel.

### Change

- The smoothness reward term `w_ds·|Δsteer|` now measures the **raw** policy
  steering delta (pre-cage) instead of the post-cage applied delta. `GazeboLaneEnv`
  tracks `prev_policy_steer` separately from `prev_steer` (the latter still feeds
  the `prev_steer` observation as the applied steering).
- `w_ds` raised **0.10 → 0.20** in `train_ppo.yaml` (`[provisional, M-P4]`).
- Tests: `test_steer_delta_*` updated to the 0.20 weight; new
  `test_raw_bang_bang_costs_more_than_smooth_ramp` pins that a raw sign-flip
  (|Δ|=2.0) costs far more than a within-C-06 ramp (|Δ|=0.15). 11/11 pass.

### Rationale

The F3 definitive evaluation (§7.5.2) showed the policy emitting bang-bang raw
steering (sign-flip 46% of steps, ±1 saturation 27%, mean |Δraw|≈0.54) that the
rate-limiter **C-06** absorbed into a smooth post-cage signal. Because the old
term was computed post-cage (per the reward-on-safe-action convention, D-34), the
smoothed result was near-identical whether or not the policy oscillated, so the
penalty never bit — the policy drove C-06 to its limit ~89% of steps for free.
Measuring the raw delta (a deliberate, scoped exception to D-34, this term only)
makes the policy pay for its own jerk; it does **not** penalise the cage's action.

### Impact

- The change is wired and unit-tested, but its effect on native RL smoothness
  **requires a new training cycle** on the Ubuntu+Jazzy host — not verifiable on
  the current dev host. The evaluated policy in §7.5 corresponds to the previous
  reward (post-cage, `w_ds=0.10`) and is unchanged.
- Weights remain `[provisional, M-P4]`; the Ch.8 sensitivity analysis confirms
  them before freeze.

### Verification

`policy/tests/test_rewards.py`: 11/11 pass. `tools/check_traceability.py`: PASS
(no ID changes; reward weights are not traceability nodes).

---

## [02.06.2026] — F3 §7.4/§7.5 update: definitive 250k PPO cycle (saturated) + re-evaluation

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md`
(§7.1, §7.2.4, §7.2.6, §7.2.7, §7.4, §7.5, internal appendix),
`manuscript/figures/fig_7_1_convergence.png` (+ `figures/auto/` copy),
`manuscript/figures/fig_7_2_trajectory.png` (+ `figures/auto/` copy),
`manuscript/figures/fig_7_2b_tracking_error.png` (+ `figures/auto/` copy),
`policy/checkpoints/checkpoint_registry.csv` (250k row), `CLAUDE.md` (status snapshot).
**Phase:** F3.
**Gate context:** after G2 — supersedes the preliminary 50k cycle that did not saturate.
**Author:** Samuel.

### Change

- **Definitive training cycle `ppo_train_20260601T184341Z`** (seed 123,
  250 000 timesteps, ~7.8 h real, fps≈9, 245 iterations of 1 024). §7.4 rewritten
  around it; it **supersedes** the preliminary 50k cycle (`ppo_train_20260601T150552Z`,
  seed 42), which was competent but **not saturated**.
- **Convergence (§7.4.1):** `ep_rew_mean` 32.4 → plateau **534.7** (max 535.6);
  `ep_len_mean` 48.4 → **500.0** (the full truncation horizon, ≈1.14 laps/episode).
  `ep_len_mean` reaches 500 by ~62k timesteps and `ep_rew_mean` hits 99% of final
  by ~72k — a stable plateau thereafter (with a minor reward dip ~120k–150k to ~490
  that does not affect episode length). The 50k-cycle "no plateau" limitation is
  **resolved**.
- **Stability (§7.4.2):** `explained_variance` sustained >0.4 from ~150k, mean **0.78**
  over the last 20 iterations (range 0.63–0.88) — the convergence criterion now holds.
- **Re-evaluation `rl_eval_20260602T070417Z`** (policy `cobraflex_ppo_lane` from the
  250k cycle, SC-NOM-01, 1 deterministic episode of 4 400 steps ≈ 11.0 continuous
  laps). §7.5.1/§7.5.2 refreshed.
- **Hyperparameters §7.2.6:** `total_timesteps` 50 000 → **250 000**; §7.2.7 seed
  note (definitive seed 123, preliminary seed 42); §7.2.4 horizon note (500-step
  horizon now saturates).
- **Figures regenerated** from the 250k cycle + new eval via
  `python tools/plot_f3_figures.py --train-run … --rl-run … --pd-run …`
  (explicit `--train-run` is **required**: `plot_f3_figures.py` auto-picks the
  latest run by mtime, which is a stray 5-row aborted run `ppo_train_20260602T070504Z`;
  the previously committed `fig_7_1_convergence.png` had been generated from it and
  showed a 4k-timestep stub — now fixed). The tracked `manuscript/figures/` copies
  (the ones the chapter `<img>` references) were overwritten with the corrected
  renders.
- **`checkpoint_registry.csv`** carries the 250k row (seed 123, commit a15412c).
- **Fig 7.3 / videos:** the Gazebo capture and `manuscript/media/*.mp4` remain from
  the preliminary eval (`rl_eval_20260601T172201Z`); caption clarified as a
  representative, visually-equivalent capture (no new screenshot on this host).

### Rationale

The 50k cycle (§7.4.2, prior entry) ended without saturation — `ep_rew_mean` was
still rising at budget exhaustion — flagged as a documented limitation [M-P6/M-P7].
A 250k cycle was run to confirm convergence; it saturates with wide margin, so the
Training Spec now reports a converged policy.

### Impact

- **Result:** PPO still matches the PD on safety (**0 C-05 emergencies over 11.0
  laps**) and beats it on tracking (mean |ey| 23 mm → **8.7 mm**, max 25 mm; mean
  |epsi| 4.4° → **2.1°**). Cage intervention 0.047% (PD) → **89.0%** (PPO) —
  **entirely C-06**: raw steering is bang-bang (sign-flips 46.4% of steps, ±1
  saturation 27.2%, mean |raw| 0.53, mean |Δraw| 0.54), smoothed by the rate
  limiter (mean |safe| 0.28, max 0.80; ~89% of steps exactly at the 0.15/cycle
  limit). No C-01..C-05 fire.
- Lap count 11.04 (440 s) vs PD 9.91 (845 s): durations differ, so the raw count
  is not 1:1; the comparable claim is both ran fault-free.
- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**
Chapter §7.4/§7.5 quantitative claims reproduce from
`experiments/sim/training/ppo_train_20260601T184341Z/learning_curve.csv` and
`experiments/sim/runs/rl_eval_20260602T070417Z/cage_status.csv`.

---

## [01.06.2026] — F3 doc reconciliation: `max_episode_steps` 400→500 propagation + status sync

**Document(s) affected:**
`docs/08_odd_specification.md` (→ v0.4), `docs/09_environment_design.md` (→ v0.2),
`docs/10_reward_function.md` (version log), `docs/DECISIONS.md` (D-33 Q11 row),
`experiments/odd_inspection/odd_tbds.yaml` (TBD-Q11 source),
`manuscript/chapters/chapter_07_training_specification.md` (§7.4.3),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (default), `CLAUDE.md`.
**Phase:** F3.
**Gate context:** before the F3 closing commit / F4 entry — a consistency pass over
the §7.2.4 `max_episode_steps` 400→500 change and the F3 status snapshot.
**Author:** Samuel.

### Change

- **`max_episode_steps` 400→500 propagation.** Training Spec §7.2.4 set the episode
  horizon to 500 steps (50 s ≈ 1.14 laps; the value the first run actually used).
  Realigned every downstream reference still reading 400 / 40 s / 0.47 laps:
  `docs/09` truncation line (→ v0.2), `docs/08` §6.8 prose + master-parameter table
  + TBD-Q11 row (→ v0.4, F2-closure history preserved), `docs/DECISIONS.md` D-33
  Q11 row, and `experiments/odd_inspection/odd_tbds.yaml` (the source
  `close_odd_tbds.py` reads). The ODD `STUCK_TIMEOUT` closure is **unchanged**
  (n/a, subsumed by env truncation) — only the illustrative seconds figure moved
  40→50 s. Code default `gazebo_lane_env.py` 400→500 (behaviour-neutral:
  `train_ppo.yaml` already sets 500).
- **`docs/09` spawn perturbation** marked **implemented** (was "Pending"): it is
  enabled in `train_ppo.yaml` and described in §7.3.
- **`docs/10`** version log gains the forward-driver **v1.1** entry (progress reward;
  weights still v1.0).
- **Chapter 7 §7.4.3** "0 emergencias en 500 pasos" → "0 emergencias en las 11.5
  vueltas / 4 400 pasos", matching the §7.5 evaluation it cites.
- **`CLAUDE.md`** phase-status snapshot refreshed (TS-01 done; F3 training+eval
  evidence IDs; first 50k cycle not saturated, longer run planned); hazard range
  H-01..H-07 → H-01..H-09; docs range 00–08 → 00–10; docs/09 + docs/10 added to the
  reference table.

### Rationale

The §7.2.4 horizon change (committed in `train_ppo.yaml`, reflected in the
working-tree chapter edit) had not propagated to the ODD spec, the environment-
design doc, or the decision log, leaving "400 / 40 s / 0.47 laps" in four files.
This is a pre-commit consistency pass so the F3 closing commit is internally
coherent. No semantic decision was changed — only stale figures realigned to the
normative §7.2/§7.3.

### Impact

- No hazard / SR / cage-rule / `cage.yaml` / scenario / metric IDs added or changed.
- No behavioural change: the first run already used 500; the code-default edit is
  inert because the config sets the key.
- Confirmed the chapter §7.5.2 quantitative claims (raw sign-flip 46.9 %, ±1
  saturation 24.0 %, mean |raw| 0.47, mean |safe| 0.28 / max 0.82, 85.9 % of steps
  at the C-06 rate limit, 0 emergencies) reproduce exactly from
  `experiments/sim/runs/rl_eval_20260601T172201Z/cage_status.csv`.

### Verification

`/usr/bin/pytest -q` → **174 passed**. `python tools/check_traceability.py` →
**All checks PASSED. 0 warning(s).**

---

## [01.06.2026] — F3 §7.5 evidence: first PPO evaluation on SC-NOM-01 (RL vs PD)

**Document(s) affected:**
`manuscript/chapters/chapter_07_training_specification.md` (§7.5.1, §7.5.2),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` (pose in `info`),
`src/cobraflex_rl/cobraflex_rl/eval_policy.py` (x/y/yaw columns),
`src/cobraflex_rl/launch/eval_lane.launch.py` (new).
**Phase:** F3.
**Gate context:** after G2; first §7.5 evaluation of the trained PPO policy.
**Author:** Samuel.

### Change

- **Evaluation run `rl_eval_20260601T172201Z`** (policy
  `ppo_train_20260601T150552Z`, seed 42, SC-NOM-01, 1 deterministic episode of
  4 400 steps ≈ 11.5 continuous laps). §7.5.1/§7.5.2 of the Training Spec filled
  with the measured results. (Short check run `rl_eval_20260601T170402Z`, 500
  steps, preceded it.)
- **Eval logging:** `GazeboLaneEnv` now exposes world pose `x, y, yaw` in `info`;
  `eval_policy` writes them as columns in `cage_status.csv` (enables the §7.5
  trajectory overlay, Figure 7.2). New `eval_lane.launch.py` (gazebo gui + eval)
  and `eval_policy --max-steps` to extend the horizon for the lap-count run.

### Rationale

§7.5 requires an empirical comparison of the trained policy against the PD
baseline (`ros_run_20260523T153003Z`) on the nominal scenario.

### Impact

- **Result:** PPO matches the PD on safety (**0 C-05 emergencies over 11.5 laps**)
  and **beats it on tracking** (mean |ey| 23 mm → 9.2 mm; mean |epsi| 4.4° →
  2.0°). Cage intervention rate 0.047% (PD) → 85.9% (PPO) — **entirely C-06**
  (rate limiter): the PPO's raw steering is bang-bang (sign-flips 46.9% of steps,
  saturates ±1 on 24.0%), which the cage smooths. No C-01..C-05 fire — the policy
  stays well inside the lane. This validates the cage as an active safeguard over
  a learned policy and motivates a future raw-Δsteer penalty.
- Lap count 11.53 (440 s) vs PD 9.91 (845 s): durations differ, so the raw count
  is not 1:1; the comparable claim is both ran fault-free and the PPO sustained
  >11 continuous laps without an emergency.
- No hazard / SR / cage-rule / cage.yaml changes.

### Verification

`pytest` → **174 passed**. `python tools/check_traceability.py` → **PASSED, 0 warnings**.

---

## [01.06.2026] — F3 learning fix: curvature preview in observation + progress reward

**Document(s) affected:**
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/rewards.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_rewards.py`,
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.1, §7.2.3, §7.2.4),
`docs/09_environment_design.md` (obs, Q2, ED-7/8/9),
`docs/10_reward_function.md` (formula v1.1).
**Phase:** F3.
**Gate context:** after G2; first training run did not learn (`ep_rew_mean` flat,
`explained_variance ≈ 0`, `std` pinned at 1.0) — root-caused to MDP design, not
the cage.
**Author:** Samuel.

### Change

- **Observation: curvature preview (4 → 6 dims).** `obs` becomes
  `[ey, epsi, speed, prev_steer, kappa_near, kappa_far]`, where the two new
  components are the signed centerline curvature (rad/m, + = left) at a near and
  a far look-ahead (`observation.curvature_lookahead_{near,far}`, default 3/8
  segments). The cage already consumed `curvature_ahead` internally; the policy
  did not, so it could not anticipate the R=0.8 m bend.
- **Reward: progress instead of speed (v1.1).** The forward term changes from
  `w_fwd·speed` (cage-fixed, near-constant ≈0.2) to `w_fwd·max(progress, 0)`,
  where `progress` is the normalised centerline advance per cycle (≈1.0 at
  cruise; the env unwraps the closed-loop `s` reset). Weights unchanged (v1.0).
  `compute_reward`'s `speed` parameter renamed to `progress`.

### Rationale

With speed fixed by the cage, the old forward term did not depend on the policy,
and the reactive 4-dim observation gave the policy no way to anticipate the
curve — together these flattened the return's dependence on the actions
(`explained_variance ≈ 0`). Curvature preview gives the policy the information to
act; progress reward makes the return discriminate behaviour (survive + advance)
and keeps every on-track step net-positive, which also closes the perverse
incentive that the penalty-free C-05 termination ([01.06] bring-up entry) would
otherwise create. Empirically the policy then learned: `ep_rew_mean` 29→57,
`ep_len_mean` 46→78, `explained_variance` 0→0.29, `std` starting to fall, with
episodes completing laps and ending by truncation (18% of training).

### Impact

- Old policy checkpoints (4-dim obs) are **incompatible**; retrain fresh.
- No hazard / SR / cage-rule IDs touched; the cage and `cage/cage.yaml` are
  unchanged. Observation/reward are env-side (Training Spec §7.2), not cage.
- Spec drift closed across Training Spec §7.2.1/§7.2.3/§7.2.4, `docs/09` (ED-7/8/9),
  `docs/10` (v1.1).

### Verification

`pytest` → **174 passed** (incl. updated `test_rewards.py`).
`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [01.06.2026] — F3 training-loop bring-up: C-05 episode termination + spawn-settle + sim-time pacing

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/ros_interface.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`docs/DECISIONS.md` (D-34 addendum).
**Phase:** F3.
**Gate context:** after G2; first end-to-end run of the in-process cage training
loop (TS-01) on the Gazebo/Jazzy host.
**Author:** Samuel.

### Change

- **Episode termination on C-05 emergency.** `GazeboLaneEnv.step` now sets
  `terminated=True` the instant the cage latches a C-05 emergency, in addition
  to the pre-existing off-road condition `|ey| > road_width/2`. A latched
  emergency freezes the car, so the remaining steps carried no learning signal
  and burned the full `max_episode_steps` per failed rollout. `info` now carries
  `termination_reason ∈ {cage_emergency, off_road, truncated}`. Both conditions
  set `terminated` (value bootstraps from 0); they differ only in the reward. Per
  D-34, the C-05 emergency carries **no** termination penalty (the cage's action
  is not punished — the episode simply ends, so the policy only forgoes future
  reward); only a genuine off-road failure, which predates the cage in the loop,
  incurs the penalty (`done=off_road` to `compute_reward`). The corrective
  interventions C-01..C-04/C-06 likewise remain transparent dynamics.
- **Spawn-pose settle fix.** A `set_pose` teleport propagates to `/odom_truth` a
  few sim steps *after* the gz service returns, so calibrating the odom→world
  offset immediately latched the previous-crash pose — producing impossible
  multi-metre `ey` and degenerate 1-step `off_road` terminations that polluted
  the PPO rollouts. `reset()` now uses `_calibrate_spawn_settled`, which
  recalibrates against a wall-clock-settled stationary pose and self-corrects if
  a stale offset was latched.
- **Sim-time control pacing.** `RosGazeboInterface.step_ros` advances by
  *simulation* time (odom header stamps) with an odom-backlog drain and a
  wall-clock fallback, instead of blocking on wall-clock; the reset settle uses a
  dedicated wall-clock `spin_wall`. A session-only `sim_real_time_factor` knob
  (default 1 = real-time) is applied via `/world/.../set_physics`. A runtime
  unthrottle is currently avoided (gz froze on `real_time_update_rate=0`), so
  headless training still runs at real-time pending the world-RTF lever.
- Transient `debug_reset_timing` / `debug_cage` console instrumentation was used
  during bring-up and removed after validation (cage confirmed intervening:
  C-01/C-02/C-03/C-06 per step, C-05 closing failed episodes).

### Rationale

The first end-to-end run of the in-process cage training loop (D-34 / TS-01)
exposed three bring-up issues: failed rollouts wasting the full horizon, a spawn
calibration race injecting garbage transitions, and real-time-locked episode
pacing. The C-05 termination and spawn-settle changes are correctness/quality;
the pacing change is groundwork for faster-than-real-time training.

### Impact

- Training throughput: failed rollouts end on emergency (seconds, not the full
  horizon); the degenerate 1-step `off_road` episodes are gone.
- Reward semantics: a C-05 emergency ends the episode with **no** termination
  penalty (only off-road failures are penalised), keeping cage interventions
  penalty-free per D-34. Cage behaviour and `cage/cage.yaml` are unchanged.
- No hazard / SR / cage-rule IDs added or changed; no scenario or metric changes.
- Re-runs: none required for traceability; the F3 first training run subsumes
  this as its starting code state.

### Verification

`python tools/check_traceability.py` → **All checks PASSED. 0 warning(s).**

---

## [29.05.2026] — F3 off-host prep: training run registration (§7.2.8) + .bak hygiene

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/run_io.py` (new),
`src/cobraflex_rl/cobraflex_rl/callbacks.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`policy/tests/test_run_io.py` (new),
`experiments/sim/training/.gitkeep` (new), `.gitignore`.
**Phase:** F3.
**Gate context:** after G2; off-host preparation so the first training run is turnkey.
**Author:** Samuel.

### Change

- **§7.2.8 training run registration**: `train_ppo` now writes
  `experiments/sim/training/<run_id>/` with `learning_curve.csv`
  (`[timestep, ep_rew_mean, ep_len_mean, explained_variance]`, via the new
  `LearningCurveCallback`) and `metadata.json` (git commit; cage/scenario/policy
  hashes; seed; hyperparameters). Periodic checkpoints go to `policy/checkpoints/`
  (SB3 `CheckpointCallback`, every `n_steps`) and a row is appended to
  `checkpoint_registry.csv` on completion — so the Gazebo/Jazzy run produces its
  §7.4 evidence automatically.
- New pure `run_io` (sha256 + git commit), shared by `train_ppo` and
  `eval_policy` (de-duplicated); `test_run_io.py` (3 tests).
- **`.gitignore`**: ignore `*.bak` so `check_traceability`'s transient
  `docs/08_..md.bak` backup never shows in `git status`.

### Verification

- `pytest cage/tests policy/tests` → 174 passed (+3 in `test_run_io.py`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- The training loop still requires the Gazebo/Jazzy host; the pure pieces
  (`run_io`, metrics) are verified here, the callback/registration syntax-checked.

---

## [29.05.2026] — F3 Week-8 wrap: seed, spawn perturbation, §7.5 eval harness, §7.2.4 reconciled

**Document(s) affected:** `src/cobraflex_rl/config/train_ppo.yaml`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/cobraflex_rl/eval_metrics.py` (new),
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`policy/tests/test_eval_metrics.py` (new),
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.4).
**Phase:** F3.
**Gate context:** after G2; closing the off-host Week-8 (D36–D40) items before the first training run.
**Author:** Samuel.

### Change

- **seed = 42** (§7.2.7): added `seed` to `train_ppo.yaml` and passed it to
  `PPO(...)`. SB3 seeds python/numpy/torch + the action space and propagates to
  `env.reset(seed=...)`, so the spawn perturbation is reproducible too.
- **Spawn perturbation** (§7.3): `GazeboLaneEnv.reset` applies a random
  per-episode start perturbation (lateral ±0.05 m perpendicular to the tangent,
  heading ±0.15 rad) via `self.np_random`; configurable under
  `spawn_perturbation` in `train_ppo.yaml`, disabled for deterministic eval.
- **§7.5 evaluation harness**: new pure `eval_metrics.summarize_eval` (laps,
  cage intervention rate, emergencies, mean/abs ey & epsi) + `test_eval_metrics.py`
  (7 tests); `eval_policy.py` rewritten to disable spawn perturbation, collect
  per-step records, and write `cage_status.csv` + `summary.json` + `metadata.json`
  under `experiments/sim/runs/<run_id>/`. Evaluation runs through `GazeboLaneEnv`,
  i.e. under the same in-process cage as deployment (D-34, SR-009).
- **§7.2.4 reconciled**: termination text updated from `|ey| > lane_width/2` to
  the implemented `|ey| > road_width/2`, with rationale and a cross-ref to
  `docs/09_environment_design.md` (ED-4).

### Verification

- `pytest cage/tests policy/tests` → 171 passed (+7 in `test_eval_metrics.py`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- The training/eval loops still require the Gazebo/Jazzy host; the pure pieces
  (metrics, reward, cage bridge) are verified here.

---

## [29.05.2026] — F3 D39 closed: reward unit tests + environment/reward design docs

**Document(s) affected:** `policy/tests/test_rewards.py` (new),
`docs/09_environment_design.md` (new),
`docs/10_reward_function.md` (new).
**Phase:** F3.
**Gate context:** after G2; Week-8 (D36–D40) infrastructure deliverables.
**Author:** Samuel.

### Change

- Closed F3 day **D39**: added `policy/tests/test_rewards.py` — 10
  synthetic-state unit tests for `compute_reward` (forward-progress, ey/epsi/
  Δsteer penalties, termination penalty, negative-speed clamp, linear
  composition, `w_ey`>`w_eps` dominance, YAML reward-block completeness). The
  reward function previously had no tests.
- Added the **D36** deliverable `docs/09_environment_design.md`:
  observation/action spaces, wrapper structure, reset/episode, actuation
  mapping, cage-in-loop, design decisions + rejected alternatives, traceability,
  anticipated defense Q&A.
- Added `docs/10_reward_function.md`: formula, components, weights v1.0 +
  rationale, simplicity argument, cage interaction, degeneration / reward-hacking
  analysis, verification, anticipated defense Q&A.
- Numbered `docs/0X` are kept in **English** (repo convention); the Spanish
  working copies live, gitignored, in `docs/.phases/Fase 3/`
  (`environment_design_v0.1.md`, `reward_function_design.md`).

### Rationale

D39's reward test suite was the one Week-8 deliverable that is pure and closable
off-host; it guards spec (§7.2.3) ↔ implementation consistency. The two design
docs are defense-preparation back-up for the viva, expanding §7.2–§7.3 with the
"why" and the rejected alternatives at a depth the thesis chapter does not
carry. They are rationale documents; §7.2 remains the normative source.

### Verification

- `pytest cage/tests policy/tests` → 164 passed (154 + 10 in `test_rewards.py`).
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.

---

## [29.05.2026] — F3 TS-01: cage wired into PPO training (in-process, D-34)

**Document(s) affected:** `docs/DECISIONS.md` (D-34),
`manuscript/chapters/chapter_07_training_specification.md` (§7.2.5 + checklist),
`src/cobraflex_rl/cobraflex_rl/cage_bridge.py` (new),
`src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py`,
`src/cobraflex_rl/config/train_ppo.yaml`,
`policy/tests/test_cage_bridge.py` (new).
**Phase:** F3.
**Gate context:** after G2, before the first PPO training run.
**Author:** Samuel.

### Change

Implemented TS-01: `GazeboLaneEnv` now routes the policy action through the
safety cage in `enforcement` mode (D-34). The cage is invoked **in-process** —
the env builds a cage `State` from the tracker, forms
`raw_action = (policy_steering, throttle_nominal)`, calls the same
`cage.cage_node.SafetyCageNode.step()` (with the same `cage/cage.yaml`) that
`cage_ros_node` wraps in deployment, and maps the safe `(steering, throttle)`
to `/cmd_vel` by replicating `vehicle_control_node` (throttle→speed,
`angular.z = steering·yaw_gain`, emergency→stop). Reward is computed on the
safe action. A fresh `SafetyCageNode` is built per episode (no latched C-05 /
rate-limiter state across rollouts). New ROS-free glue `cage_bridge.py`; new
`cage:` block in `train_ppo.yaml` (with an `enabled:false` debug fallback).
D-34's implementation note + Status and §7.2.5 were updated to record the
in-process mechanism instead of the topic round-trip originally sketched.

### Rationale

The env is a synchronous `gym.Env` loop; a per-step `/raw_action`→`/safe_action`
ROS handshake with a separate node would add asynchrony (harming determinism
under seed=42, §7.2.7), latency, and launch complexity. The in-process call is
byte-identical in cage behaviour (same class + YAML), stays deterministic, and
needs no launch changes (the env publishes `/cmd_vel` itself, so there is no
`vehicle_control_node` to co-launch and no double-actuation). Satisfies SR-009
(train under the deployed envelope) at the behavioural level. User-approved
this session.

### Impact

- Training now runs under the cage; the first PPO run can proceed (still
  pending, together with §7.4/§7.5 and `experiments/sim/training/` registration).
- Actuation constants `throttle_nominal` / `yaw_gain` / `min_speed_scale` are
  duplicated from `vehicle_control_node` defaults in `train_ppo.yaml`; keep in
  sync if those change.
- No cage code changed → cage v0.5.1 and all SR thresholds unchanged.

### Verification

- `pytest cage/tests policy/tests` → 154 passed (was 144; +10 in
  `test_cage_bridge.py`, incl. a C-01 correction routed through
  `SafetyCageNode`).
- `python -m py_compile` on the new/edited `.py` files → OK.
- `python tools/check_traceability.py --strict` → all checks PASSED, 0 warnings.
- End-to-end training-loop validation on the Gazebo/Jazzy host is deferred to
  the F3 first-run task (ROS2/Gazebo cannot launch on the dev Windows host).

---

## [23.05.2026] — F3 kickoff: Training Specification, training pipeline fixes, D-34

**Document(s) affected:** `manuscript/chapters/chapter_07_training_specification.md`,
`docs/DECISIONS.md` (D-34), `src/cobraflex_rl/cobraflex_rl/ros_interface.py`,
`src/cobraflex_rl/cobraflex_rl/train_ppo.py`,
`src/cobraflex_rl/cobraflex_rl/eval_policy.py`,
`src/cobraflex_rl/launch/train_lane.launch.py`,
`CLAUDE.md`.
**Phase:** F3.
**Gate context:** G2 passed; F3 entry.
**Author:** Samuel.

### Change

Gate G2 passed on the strength of `ros_run_20260523T153003Z` (9.91 laps,
0 emergencies, 144 tests, traceability PASS). F3 starts.

**Training Specification (Chapter 7 §7.2, artefact A1):** complete
8-component spec written before first training run, covering observation
space, action space, reward function (weights v1.0), termination/truncation
criteria, cage-in-training mode (D-34), PPO hyperparameters (v1.0),
seed/reproducibility policy, and checkpoint registry.

**D-34 (cage active during training):** documented in DECISIONS.md.
Strategy B chosen: training env routes through `/raw_action → cage →
/safe_action`. Implementation is F3 task TS-01.

**Training pipeline bug fixes:**
- `ros_interface.py`: world_name default `"road_carpet_world"` →
  `"lane_following_oval"` (wrong world would have caused service failures).
- `train_ppo.py`, `eval_policy.py`: centerline default `"centerline.yaml"`
  (3-point straight) → `"oval_right_lane_centerline.yaml"`.
- `train_lane.launch.py`: replaced stub (wrong `gazebo.launch.py` +
  `obstacles.world`) with correct `gazebo_mesh.launch.py` + oval world
  + `headless` arg for faster training.

### Rationale

The training pipeline had accumulated stub code from F1 that pointed to
wrong worlds and wrong centerlines. These would have caused silent failures
(training on a 3-point straight, or failing to find the Gazebo service)
on the first F3 training attempt. Fixing before training is cheaper than
debugging after.

### Verification

- AST OK on all modified Python files.
- `pytest cage/tests policy/tests` → 144 passed (no new tests; fixes are
  config/default changes that only activate at ROS2 runtime).
- `python3 tools/check_traceability.py --strict` → all checks PASS.

---

## [23.05.2026] — lane_perception_node: speed spike rejection filter

**Document(s) affected:** `src/cobraflex_rl/cobraflex_rl/lane_perception_node.py`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Added Gazebo odometry spike rejection to `LanePerceptionNode`.
Speed is now filtered in two steps:

1. **Spike rejection:** if `speed_raw > speed_spike_factor × max(speed_smooth, 0.01)`,
   the sample is discarded (held at `speed_smooth`) and a `WARNING` is logged.
   Default `speed_spike_factor = 5.0`; calibratable as a ROS2 parameter.

2. **EMA smoothing:** the (possibly clamped) raw value is fed into an EMA with
   the same `ema_alpha` parameter already used for `ey`/`epsi`.

`_speed_smooth` is reset to `None` on warp detection alongside `_ey_smooth`
and `_epsi_smooth`.

### Rationale

Run `ros_run_20260523T150400Z` (14.3 min, 10+ laps) ended at t = 724.45 s
with a single-sample odom spike of 32.5 m/s (actual cruise speed 0.07 m/s).
The cage correctly fired C-04 + C-03 + C-05, latching the vehicle stopped for
the remaining 2.3 min. Lane position at the moment was ey = −17 mm,
epsi = −4° — a false positive caused by a Gazebo physics artifact, not a real
safety event. With `speed_spike_factor = 5.0`, the spike (32.5 >> 0.35 m/s
threshold) is rejected and C-04/C-03 do not fire.

### Impact

Nominal runs are unaffected (no spike → rejection branch never taken).
EMA adds at most ~5 ms of smoothing lag at 20 Hz, negligible for the PD controller.
No cage YAML or SR changes required; this is a sensor pre-processing fix.

### Verification

- `pytest cage/tests policy/tests` → 144 passed.
- AST check on modified node: OK.
- Simulated spike scenario: speed_raw = 32.5, speed_smooth = 0.07, factor = 5.0
  → threshold = 0.35 → spike rejected, WARNING emitted, speed_smooth unchanged.
- **ROS2/Gazebo validation run `ros_run_20260523T153003Z`:** 14.1 min (845.5 s),
  16 910 cycles, **0 emergencies**, speed max 0.200 m/s. Same 8-intervention
  pattern (C-02 × 1, C-06;C-02 × 5, C-06 × 2) as the G2 evidence run. The
  run covered the same elapsed-time window (~845 s) where the prior spike had
  occurred, with no C-03/C-04/C-05 activation.

---

## [23.05.2026] — F2 pipeline hardening: logger flush, watchdogs, wraparound guards, packaging fixes

**Document(s) affected:** `cage/logger.py`, `cage/tests/test_pipeline.py`,
`policy/baseline_pd.py`,
`src/cobraflex_rl/cobraflex_rl/cage_logger_node.py`,
`src/cobraflex_rl/cobraflex_rl/lane_perception_node.py`,
`src/cobraflex_rl/cobraflex_rl/vehicle_control_node.py`,
`src/cobraflex_rl/package.xml`,
`src/safety_cage/safety_cage/cage_ros_node.py`,
`src/safety_cage/launch/lane_following.launch.py`,
`manuscript/chapters/chapter_06_implementation.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Pipeline-wide audit and hardening pass before F3. No nominal-behaviour
changes; every fix is either a fail-safe that only activates on failure
(watchdogs, wraparound guards, polling unpause) or a packaging/observability
improvement.

CageLogger (`cage/logger.py`): line-buffered file open so each
`writerow` is flushed to disk immediately, eliminating tail-truncation
on abrupt termination; warns when overwriting an existing CSV.

cage_logger_node: 5 s wall-clock watchdog that surfaces silent
upstream failures (no /cage_status received vs. count stuck);
`output_dir` resolved to absolute path; new `cage_mode` parameter
stamped into every CSV row and into `metadata.json`.

vehicle_control_node: 10 Hz wall-clock watchdog that publishes
`cmd_vel=(0, 0)` if no `/safe_action` arrives within 0.5 s, preventing
the Gazebo DiffDrive plugin from holding a stale command after an
upstream crash.

lane_perception_node: warp detection (>0.5 m odom jump) resets the
`PolylineTracker` neighbourhood cache and the EMA, with WARN log;
EMA on `epsi` rewritten to operate on the wrapped delta so the
smoothed estimate tracks the shortest-arc trajectory across the ±pi
seam.

cage_ros_node: dropped the redundant `ctx["reset"]` pass-through and
the dead `require_state_for_first_cycle` parameter.

policy/baseline_pd.py: `psi_dot` finite-difference now uses
`wrap_angle(psi - prev_psi)` so a heading that crosses ±pi does not
produce a spurious 120 rad/s derivative.

lane_following.launch.py: replaced the hardcoded 4 s TimerAction +
fixed world name with a polling loop that retries the gz unpause
service every 0.5 s for up to 30 s; world name is now an explicit
`world_name` launch argument.

cobraflex_rl/package.xml: declared previously-missing `std_msgs` and
`cobraflex_safety_msgs` dependencies.

Chapter 6 manuscript: §6.5.3 pruned to match real coverage (no
`hypothesis`); §6.5.4 rewritten around the existing
`test_pipeline.py` instead of the aspirational `pytest-launch_testing`
suite; §6.5.5 acknowledges that the pre-commit hook and GitHub
Actions workflow are F3 work; Listing 6.1 added with the actual
`LaneBoundaryRule.evaluate` skeleton.

### Rationale

The earlier "no se genera CSV" report and the latent C-05 risk from
the unwrapped heading derivative motivated the audit. The fixes
target three failure modes: silent data loss (logger flush), silent
pipeline failures (three watchdogs, polling unpause), and latent
correctness bugs that F2 happens not to hit but F3 with arbitrary
spawn orientations will (wraparound in PD and perception). Pruning
the manuscript brings §6.5 in line with what the repo actually
implements, so Gate 2 evidence does not over-promise.

### Impact

Nominal pipeline produces bit-identical CSV content (only the `mode`
column now reads `"enforcement"` instead of empty). Watchdogs are
dormant in nominal operation. The new package.xml deps unblock
`rosdep install` on a clean machine. No re-run of historical
scenarios needed; the run candidate `ros_run_20260523T073134Z`
remains the Gate-2 evidence.

### Verification

- `pytest cage/tests policy/tests` -> 144 passed (143 existing + 1 new
  `test_pipeline_handles_missing_state_until_first_obs`).
- `python3 tools/check_traceability.py --strict` -> all checks PASS,
  0 warnings.
- `python3 tools/check_scenario_yaml.py` -> PASS, 0 errors.
- AST OK on all 5 modified pipeline nodes.

## [23.05.2026] — Chapter 6: promoted definitivo pre-F3 run to all §6.3.5/§6.5.4/§6.6 placeholders

**Document(s) affected:** `manuscript/chapters/chapter_06_implementation.md`,
`experiments/sim/runs/ros_run_20260523T153003Z/summary.json`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Replaced all numerical references previously sourced from `ros_run_20260523T073134Z`
(4.50 laps, 379.8 s, 7 597 cycles) with values from the definitive pre-F3 run
`ros_run_20260523T153003Z` (9.91 laps, 845.4 s, 16 910 cycles, 0 emergencies).

Sections updated: §6.3.5 (logger throughput), §6.5.4 (throughput test body and
latency figure), §6.6.1 (demostración integrada), §6.6.2 (all three preliminary
metrics). Test count updated from 143 → 144 in §6.5.2 and the internal appendix.

Created `experiments/sim/runs/ros_run_20260523T153003Z/summary.json` with the
full metrics (laps, distance, dt stats, intervention breakdown, signal ranges).

### Rationale

The new run includes the speed-spike rejection filter and ran for ~14 min without
any emergency, providing 2.2× more evidence than the prior 6.3 min run. The
same pipeline, same cage YAML and same PD gains — only the odom spike filter
is new. All three §6.6.2 metrics improve: intervention rate drops from 0.105%
to 0.047%, completion extends from 4.50 to 9.91 laps.

### Verification

- `python3 tools/check_traceability.py --strict` → all checks PASS, 0 warnings.
- `grep -n "T073134Z\|379\.8\|7 597\|4\.50 vueltas\|0\.105%\|53\.0 ms\|143 casos"` → 0 matches.

---

## [23.05.2026] — Chapter 6 §6.3.5/§6.4.2/§6.5.2/§6.5.4/§6.6: resolved [COMPLETAR FASE 2] placeholders with run candidate data

**Document(s) affected:** `manuscript/chapters/chapter_06_implementation.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Replaced the numerical `[COMPLETAR FASE 2]` placeholders in §6.3.5
(logger throughput), §6.4.2 (PD gains v0.8.0), §6.5.2 (test counts:
61 per-rule, 132 cage suite, 143 with PD), §6.5.4 (cycle latency
50.0/50.0/53.0 ms, 0 dropped log lines), §6.6.1 (4.50 laps over
target 3, 0 emergency cycles, 8 cage interventions distributed
across C-02 and C-06), and §6.6.2 (intervention rate 0.105%,
completion rate provisional 100% with N=1). Updated the chapter's
internal appendix to mark these placeholders as done and to add a
new pending item for the N≥30 multi-run completion-rate campaign.

### Rationale

The run `ros_run_20260523T073134Z` (PD 0.8.0, cage 0.5.1, SC-NOM-01,
enforcement) is the Gate-2 candidate evidence; backfilling the
chapter with its measured values is required before tagging G2.
Honest scoping: the multi-run completion-rate campaign (N=30) is
explicitly flagged as outstanding rather than fabricated, and the
spawn perturbation described in §6.6.1 is noted as not applied in
this run.

### Impact

Chapter 6 numerical placeholders are now closed; outstanding items
for G2 are Figura 6.1, Listing 6.1, multi-run completion campaign,
cross-chapter consistency check with Chapter 5, and pre-existing
`colcon test` lint failures in `cobraflex`.

### Verification

- `python3 tools/check_traceability.py --strict` -> all checks PASS, 0 warnings.
- Manual grep confirms no remaining numerical `[COMPLETAR FASE 2]`
  markers; only the convention preamble (line 8), the Figura 6.1
  placeholder (line 107), and the Fase-6 polish line (line 757) remain.

## [23.05.2026] — Gate 2 candidate evidence: ROS oval run completes >3 laps without emergency

**Document(s) affected:** `experiments/sim/runs/ros_run_20260523T073134Z/metadata.json`, `experiments/sim/runs/ros_run_20260523T073134Z/summary.json`, `docs/04_cage_specification.md`, `experiments/sim/oval_pd_cage_smoke.py`, `tools/check_scenario_yaml.py`, `tools/README.md`, `scenarios/README.md`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Added reproducibility metadata and a summary file for the ROS2/Gazebo run
`ros_run_20260523T073134Z`. The run is the first Gate-2 candidate evidence
for the full F2 pipeline: baseline PD 0.8.0, cage YAML 0.5.1, right-lane
oval centerline, cage in enforcement mode.

The committed `summary.json` declares the evidence segment explicitly: the
full monotonic timestamp segment, lines 2–7598 of `cage_status.csv`.

### Rationale

The closure segment runs for 379.799 s, covers an estimated 4.504501 laps
against the ODD-3 perimeter of 8.0232 m, and records zero emergency-mode
cycles. Cage activity is limited to 8 intervention cycles, all C-02/C-06
bounded corrections, with no C-01, C-03 or C-05 activation in nominal
lane-following.

### Impact

This provides the empirical evidence needed for the F2 end-to-end demo
criterion. The pure-Python `oval_pd_cage_smoke.py` docstring is updated to
classify it as a kinematic chain sanity check rather than the Gate-2 closure
demo, because it does not model the current ROS2/Gazebo stack. The evidence
is not yet a full Gate-2 closure by itself: Chapter 5/6 placeholders and the
inherited `colcon test` lint failures in `src/cobraflex` remain to be addressed
or explicitly scoped before tagging G2. The scenario YAML validator promised
by `scenarios/README.md` is added in Phase-2 scope: default mode accepts
explicit stubs with warnings, while `--strict` turns those warnings into
failures for later gates.

### Verification

- `pytest cage/tests policy/tests` -> 143 passed.
- `python3 tools/check_traceability.py --strict` -> all checks PASS, 0 warnings.
- `python3 tools/check_scenario_yaml.py` -> PASS, 0 errors, warnings for deferred stubs/missing later-phase YAMLs.
- `colcon build --packages-select cobraflex_safety_msgs safety_cage cobraflex_rl cobraflex --symlink-install` -> 4 packages finished.
- `colcon test --packages-select cobraflex_safety_msgs safety_cage cobraflex_rl cobraflex` -> package tests execute, but `cobraflex` fails pre-existing lint/pep257 checks.

## [22.05.2026] — PD Baseline 0.6.0: zero kd_y and kp_h — polyline signals unreliable at curves (Phase 2)

**Document(s) affected:** `policy/baseline_pd.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

`kd_y` 0.5 → 0.0; `kp_h` 1.0 → 0.0; `version` bumped from `0.5.0` to `0.6.0`.

### Rationale

Two consecutive sim runs (`ros_run_20260522T175259Z`, `ros_run_20260522T180231Z`)
showed emergency stop at the first oval curve (t ≈ 13.75 s, κ ≈ 1.08 rad/m),
car never completing a lap — F2 FAIL.

Root cause: the polyline tracker (±6 segment local search) jumps segments at
curve entries, producing step discontinuities in both `ey` and `epsi` within
a single 50 ms cycle.

- `kd_y`: `ey` jumps ±0.15 m → `y_dot ≈ ±3 m/s` → `kd_y × y_dot ≈ 1.5`,
  saturating steering alone. Fix: `kd_y → 0.0`.
- `kp_h`: even with `kd_y = 0`, `epsi` steps ±0.25–0.36 rad at curve entries.
  Combined with feedforward (0.49) and kp_y term (0.28), total reaches 1.13 →
  saturation → C-06 + C-03 + C-05 chain. Fix: `kp_h → 0.0`.

Both fixes follow the same reasoning as `kd_h → 0.0` in v0.5.0: piecewise-
constant polyline signals are not reliable inputs for PD terms. The effective
controller is now `steering = kappa_ff·κ − kp_y·ey`, which stays below 1.0
for all physically reachable (ey, κ) on the F2 oval.

Also: `_LOCAL_SEARCH_RADIUS` in `polyline_tracker.py` reduced 6 → 2. The
local search radius controls how many adjacent segments are considered per
cycle. With radius=6, the tracker could jump up to 6 segments (0.66 m) in
one cycle — the F2 oval's 0.11 m/segment spacing combined with near-equidistant
geometry at curve entry allows this. Those multi-segment jumps produce the
ey/epsi discontinuities described above. Radius=2 (0.22 m, 22× headroom over
the 0.01 m/cycle at 0.2 m/s) enforces continuity while tolerating a 20× speed
increase before the constraint binds.

### Impact

`policy/baseline_pd.yaml` and `src/cobraflex_rl/cobraflex_rl/polyline_tracker.py`.
No cage rules, SRs, or hazards affected. Re-run oval scenario to verify lap
completion.

### Verification

`python3 tools/check_traceability.py` — no ID references changed.

---

## [22.05.2026] — PD Baseline 0.7.0: restore kp_h=0.3 — heading correction safe with bounded search radius (Phase 2)

**Document(s) affected:** `policy/baseline_pd.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

`kp_h` 0.0 → 0.3; `version` bumped from `0.6.0` to `0.7.0`.

### Rationale

Third sim run (`ros_run_20260522T180853Z`) showed that with `kp_h=0.0` the car's
heading drifts at curves (epsi reaches 0.25–0.35 rad), which alone triggers C-05
`theta_warning` (threshold 0.349 rad = 20°). Without proportional heading
correction the curvature feedforward + kp_y lateral correction cannot damp the
heading drift fast enough on the R=0.9225 m curve.

After reducing `_LOCAL_SEARCH_RADIUS` from 6 to 2 (v0.6.0 / polyline_tracker.py),
the maximum epsi jump from a 2-segment advance is ~0.094 rad. At `kp_h=0.3`:

```
kp_h × Δepsi_max = 0.3 × 0.094 = 0.028   (negligible for saturation)
worst-case total  = kappa_ff(0.487) + kp_y×ey_max(0.366) + kp_h×epsi_max(0.028)
                  = 0.881 < 1.0  ✓
```

The heading term is now safe to restore at a smaller gain, and necessary to
prevent the C-05 theta_warning chain.

### Impact

`policy/baseline_pd.yaml` only. No cage rules, SRs, or hazards affected.
`policy/tests/test_baseline_pd.py` updated: `test_heading_has_no_effect_with_kp_h_zero`
renamed to `test_heading_error_produces_corrective_steering` to reflect kp_h=0.3.

### Verification

`python3 tools/check_traceability.py` — no ID references changed.

---

## [18.05.2026] — Cage 0.5.0: SR-010 Part 2 — inter-cycle oscillation detection (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Bumped `cage.version` from `0.4.0` to `0.5.0`. Added a new top-level
`cage.oscillation` subsection with three parameters:

- `f_osc_max_hz: 5.0` — alternation-rate threshold (per-rule, on the sign
  of the steering correction) above which the cage logs the cycle.
- `t_osc_window_s: 1.0` — sliding window over which the alternation
  rate is computed.
- `t_osc_persist_s: 3.0` — sustained-violation duration above which the
  oscillation triggers C-05 emergency mode via a new
  `oscillation_detected` trigger.

### Rationale

Implements SR-010 Part 2 (Inter-cycle oscillation check) as documented
in §"Joint-envelope assertion and conflict resolution" of the cage
specification. Detects pathological policy-cage feedback where the cage
fires alternately left/right on the same rule across consecutive
cycles, which the safety analysis treats as evidence of a degenerate
loop requiring human intervention. SR-010 Part 1 (end-of-cycle
joint-envelope assertion / C-05 Trigger 7) remains deferred because the
per-rule `safe_envelope_predicate_holds(state, action)` API it requires
does not yet exist on the rule contract.

### Impact

- `SafetyCageNode` now maintains a per-rule signed-correction history
  (`_osc_history`) and a per-rule violation start timestamp
  (`_osc_violation_start`). The new `step()` result also exposes
  `oscillation_rates_hz` (per-rule current rates) and
  `oscillation_persistent` (the boolean fed to C-05) for the logger.
- `EmergencyRule._evaluate_triggers` reads `ctx["oscillation_detected"]`
  and contributes it to the `any` aggregate; new explicit branch in
  `evaluate()` emits the `triggered-oscillation` reason when fired.
- Defaults on `SafetyCageNode.__init__` make the feature inert
  (`f_osc_max=inf`) when the YAML lacks the `oscillation` subsection,
  preserving backward compatibility with 0.4.0 YAMLs.

### Verification

- `pytest cage/tests/` — full suite passes including the new
  `test_oscillation.py` cases (no fire below threshold, log without
  emergency at fast rates, emergency once persistence exceeds
  `t_osc_persist_s`).
- `tools/check_traceability.py` — unchanged (SR-010 is in the registry;
  no new SR added).

---

## [18.05.2026] — Cage 0.4.0: complete C-05 trigger set (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

### Change

Bumped `cage.version` from `0.3.0` to `0.4.0`. Added two parameters under
`c05_emergency`:

- `v_warning_mps: 0.4` — speed threshold above which the compound trigger
  uses the high-energy persistence (SR-005 Trigger B). 80 % of
  `v_max_straight_mps`.
- `delta_t_max_fast_s: 0.1` — shorter persistence applied when the
  high-energy variant fires.

### Rationale

Both parameters complete the C-05 trigger set per the cage specification
(`docs/04_cage_specification.md` §C-05): Trigger 2 (high-energy compound)
joins the already-implemented Triggers 1 (low-energy compound), 3
(stale), 4 (invalid), 5 (missing-state via the cage_node counter) and 6
(external stop). Trigger 7 (joint-envelope assertion of SR-010) remains
deferred because the per-rule predicate API it requires does not yet
exist.

### Impact

- `EmergencyRule.__init__` now reads `v_warning_mps` and
  `delta_t_max_fast_s`. Both have constructor defaults (`inf` and the
  low-energy persistence respectively) so older YAMLs continue to load,
  but the high-energy trigger is effectively disabled in that case.
- `SafetyCageNode.step()` now accepts `state=None` to flag a missing
  observation; consecutive `None` calls feed the missing-state trigger
  (5) once they exceed `cage.n_missing_max_cycles`.
- No re-run of validation campaigns required (no existing parameter
  value changed).

### Verification

- `pytest cage/tests/` — all rule and integration tests pass, including
  new tests for the high-energy trigger and the missing-state counter.
- `tools/check_traceability.py` — unchanged (no SR or cage rule added or
  modified at the registry level).

---

## [18.05.2026] — Cage 0.3.0: parameters required by executable rules (Phase 2)

**Document(s) affected:** `cage/cage.yaml`.
**Phase:** F2.
**Gate context:** before G2.
**Author:** Samuel.

Bumped `cage.version` from `0.2.0` to `0.3.0`. Added three parameters needed
by the first executable cut of the rule logic (no existing parameter values
were modified):

- `c03_ttlc.d_max_m: 0.16` — TTLC projection needs the lane half-width;
  duplicated here with the explicit comment that it must mirror
  `c01_lane_boundary.d_max_m` (coupling documented in-place).
- `c03_ttlc.v_min_estimate_mps: 0.05` — kinematic floor below which
  `compute_ttlc` returns infinity (avoids division by near-zero lateral
  velocity at standstill).
- `c04_speed_ceiling.k_throttle_per_mps: 5.0` — proportional gain that
  maps speed excess over `v_max(κ)` to throttle reduction in the
  correction formula `throttle_safe = max(0, throttle_raw − k·excess)`.

The three parameters are required by the rule implementations under
`cage/rules/c03_ttlc.py` and `cage/rules/c04_speed_ceiling.py` checked
in alongside this bump. Their default values follow the Phase 2 plan
(`docs/.phases/Fase 2/fase_2_detallada.md` §5.3 and §5.4); both
`d_max_m` and `k_throttle_per_mps` are inherited as-is, and
`v_min_estimate_mps` reuses the value documented under the same plan
section. All three remain candidates for revision once the calibration
campaign (M-1..M-5) closes and the policy-side margins of SR-003 are
exercised.

- Rule constructors `TTLCRule.__init__` and `SpeedCeilingRule.__init__`
  now read these keys; older YAMLs without them will fail to instantiate.
- No change to traceability matrix — no SR or hazard added.
- No re-run of validation campaigns required (no value of any existing
  parameter changed).

- `pytest cage/tests/` — all rule unit tests pass.
- `tools/check_traceability.py` — unchanged (no SR or cage rule added or
  modified at the registry level).

---

## [30.04.2026] — Initial baseline (Phase 0)

**Document(s) affected:** all `docs/*.md` files.  
**Phase:** F0.  
**Gate context:** before G0.  
**Author:** Samuel.  

Initial creation of living documents from Phase 0 templates. Hazard Register seeded with H-01 to H-07. SRS seeded with SR-001 to SR-008. Cage Specification seeded with C-01 to C-06. Scenario Library seeded with 9 scenarios across 3 categories. Metrics catalogue seeded with M-P, M-S, M-I, M-C families. Traceability Matrix seeded with the chains derived from the above.

Establish the baseline that subsequent phases will refine. The numerical thresholds in the SRS are first-cut estimates derived from the platform geometry and the kinematic envelope; they will be refined in Phase 1 as the analysis matures.

None upstream (this is the baseline). Downstream: Phase 1 will refine numerical parameters and may add or merge hazards based on closer analysis.

`tools/check_traceability.py` reports: 0 orphans on hazards, 0 orphans on SRs, 0 orphans on cage rules, 0 orphans on scenarios, 0 orphans on metrics. Coverage requirements (1)–(8) all satisfied.

---

## [30.04.2026] — Update of chapter 3

**Document(s) affected:** chapter_03_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 3 Metodology with comparison between classical V model and adapted for this thesis

---
---

## [02.05.2026] — Update of chapter 1

**Document(s) affected:** chapter_01_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 1 and double check all references

---
---

## [02.05.2026] — Update of chapter 2

**Document(s) affected:** chapter_02_metodology.md  
**Phase:** F0  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapter 2 with related work, double check of references pending

---
---

## [02.05.2026] — Rename of templates + added 00_odd_specification.md

**Document(s) affected:** chapter_02_metodology.md  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Added 00_odd_specification.md, changed of names of templates for better understanding

---
---

## [04.05.2026] — Update of Chapters 1, 2 & 3 with new papers

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapters 1,2 and 3 with related work, double check of references pending

---
---

## [11.05.2026] — Update of Chapters 1, 2 & 3

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

Update of Chapters 1,2 and 3

---
---

## [11.05.2026] — Added HARA script check

**Document(s) affected:** chapters 1, 2 and 3  
**Phase:** F1  
**Gate context:** before G0  
**Author:** Samuel Sanchez

---
---

## [13.05.2026] — Gate 0 closed

**Document(s) affected:** -  
**Phase:** F1  
**Gate context:** after G0  
**Author:** Samuel Sanchez

---

## [13.05.2026] — Pre-G1 consolidation: rating fixes, SR consistency, STPA expansion, chapter cleanup

**Document(s) affected:** `docs/02_hazard_register.md`, `docs/03_safety_requirements.md`, `docs/05_scenario_library.md`, `manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Pre-G1 consolidation pass over the safety analysis and requirements artefacts, applying the recommendations of `docs/.phases/Fase 1/phase1_refinement_notes.md` and the defaults of `docs/.phases/Fase 1/phase1_supervisor_briefing.md` to bring the F1 deliverables to G1-ready state. Specific edits:

*Hazard Register (`docs/02_hazard_register.md`).* Removed stray `**PLACEHOLDERS**` scaffold line; updated `Last update` to 13.05.2026; added explicit "Severity convention" note documenting the analogue-real-vehicle interpretation (decision D-03, Decision 1 default of the supervisor briefing). Added per-hazard "Rating rationale" paragraphs to H-01..H-07 with written justification for each S/E/C level. Applied three rating consolidations recommended by the refinement notes: H-03 split rating `S=2 (S=3 in tight curves)` → conservative single `S=3` (worst case in curve) with tightened description; H-05 `S=2` → `S=1` aligned with analogue-real-vehicle convention (abrupt actuation is primarily a comfort-and-wear hazard); H-06 `E=1 to E=2` → single `E=2` dominated by physical-deployment scenario. Added to H-01 a note that C=2 is conditional on TTLC predictor reliability. Added to H-02 the explicit rationale for not upgrading severity despite escalation into H-01 (Decision 2 default). Expanded STPA-light findings for H-01, H-02 and H-04 from shallow notes to a systematic pass across the four UCA categories applied to each principal control action (Decision 5 default: into the living document). H-04 STPA section additionally registers two design findings outside the standard UCA grid (trigger persistence requirement and asymmetric exit via explicit reset). Updated STPA scope statement accordingly.

*Safety Requirements Specification (`docs/03_safety_requirements.md`).* Updated `Last update` to 13.05.2026. **Critical consistency fix**: SR-008 `t_stop_max` raised from `1.5 s` to `1.7 s` to resolve a numerical inconsistency with SR-005 (`a_min = 0.3 m/s²` at `v_max_straight = 0.5 m/s` implies a stopping time of approximately 1.67 s, which the previous `t_stop_max = 1.5 s` violated). The fix follows option (a) of Decision 6 in the supervisor briefing. Expanded parameter rationales: SR-002 now includes a bicycle-model recoverability derivation for `θ_max = 25°`; SR-003 marks the policy-side component of `t_min` (`0.7 s`) as provisional pending the first F3 training prototype; SR-004 documents the rationale for the curvature-decay coefficient `k_κ = 0.3` and the pending-measurement status of `v_max_curve` and `v_max_straight` (measurement M-4); SR-005 documents the provisional status of `a_min` pending measurement M-3 and the STPA-informed rationale for `Δt_max = 0.2 s`; SR-006 declares `δ_max` values as conservative defaults pending M-5 and post-prototype cross-check; SR-007 expands the rationale of `staleness_max` and `N_missing_max` and clarifies the deliberate width of plausible state ranges.

*Scenario Library (`docs/05_scenario_library.md`).* SC-NOM-01 now declares explicit "Cage rules exercised" (C-01, C-06) to clear the `check_traceability.py` warning on Constraint (5) for C-06.

*Chapter 4 (`manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`).* Closed nine `[COMPLETAR FASE 1 / Dxx]` markers across §4.4.3, §4.4.4, §4.5.2, §4.5.3, §4.6.3, §4.6.4, §4.7.2, §4.8.2 and §4.8.3. Updated the Hazard Register compact table in §4.4.3 to reflect the consolidated H-03 / H-05 / H-06 ratings. Wrote §4.4.4 (HARA coverage argument in three axes), §4.5.2 (STPA-light results synthesis), §4.7.2 (relative completeness argument). Wrote a synthesis paragraph in §4.6.4 with summary rationale for SR-002..SR-008 to complement the SR-001 worked example. Updated §4.6.3 table to reflect the SR-008 `t_stop_max = 1.7 s` value and the provisional flag on SR-005 `a_min`. Removed obsolete `[COMPLETAR FASE 1 / Dxx]` markers from §4.4, §4.5, §4.6 and §4.8 headings.

*Chapter 3 (`manuscript/chapters/chapter_03_methodology.md`).* Closed the `[COMPLETAR FASE 1 — IDs definitivos]` marker in §3.5.2 by substituting the placeholder identifiers `SR-001..SR-00k` and `C-01..C-0n` with the definitive ranges `SR-001..SR-008` and `C-01..C-06`.

The refinement notes and the supervisor briefing for F1 identified a list of edits required before G1 can close. Most are textual or methodological (rating justifications, per-SR rationale) but one is a critical numerical fix (SR-005 ↔ SR-008 inconsistency) that the briefing's Decision 6 had pre-committed to resolve under option (a). The consolidation pass applies all the edits that do not depend on pending platform measurements (M-1 through M-5), leaving the platform-dependent parameters (`a_min`, `v_max_curve`, `δ_max`) explicitly flagged as provisional in both the SRS and Chapter 4.

Downstream: the cage parameters in `cage/cage.yaml` (`a_min_mps2 = 0.3`, `c04_speed_ceiling.*`, `c06_rate_limiter.*`) remain numerically unchanged in this pass; they are flagged as provisional in the SRS and will be revised after M-3, M-4 and M-5 are executed (with corresponding bump to `cage.yaml` version 0.2.0 at that point). The Hazard Register STPA expansion is purely documentary and does not introduce new SRs or new cage rules. The scenario library change adds explicit C-06 mention to SC-NOM-01 without altering its run semantics.

After the pass:

- `python tools/check_traceability.py` is expected to PASS without warnings (Constraint 5 warning on C-06 resolved by the SC-NOM-01 edit).
- `pytest cage/tests/` is expected to PASS unchanged (no cage logic affected).

Both verifications are to be re-run as the final step of this consolidation.

---

## [13.05.2026] — cage.yaml v0.2.0: parameter-rationale consolidation

**Document(s) affected:** `cage/cage.yaml`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Bumped `cage.version` from `"0.1.0"` to `"0.2.0"`. No parameter values
were modified; the bump is a documentation-precision revision that
adds per-rule rationale comments linking each parameter to the
corresponding SR rationale in `docs/03_safety_requirements.md` and
flagging the parameters that remain provisional pending the pre-G1
measurement campaign (`experiments/calibration/`). Specifically:

- C-01 `d_max_m`: flagged `[provisional, M-1, M-2]` (lateral noise σ
  and end-to-end control latency).
- C-03 `t_min_s`: flagged as having a provisional policy-side
  component (0.7 s of the 1.0 s total) pending the F3 prototype.
- C-04 `v_max_straight_mps`, `v_max_curve_mps`, `k_kappa_*`: flagged
  `[provisional, M-4]` and dependent on ODD TBD-Q1 / TBD-Q9.
- C-05 `a_min_mps2`: flagged `[provisional, M-3]` with explicit
  consistency note referencing SR-008 `t_stop_max = 1.7 s` (the
  kinematic stopping time at `v_max_straight = 0.5 m/s` is 1.67 s).
- C-06 `delta_max_steering_per_cycle`, `delta_max_throttle_per_cycle`:
  flagged `[provisional, M-5 + F3 prototype]`.

The header description is expanded to declare that the SR-005 ↔ SR-008
consistency reconciliation is documented in the immediately preceding
CHANGELOG entry, and that the next planned bump (0.3.0) will follow
the closure of M-1 through M-5 with the corresponding parameter
revisions.

The supervisor briefing for F1 (`docs/.phases/Fase 1/phase1_supervisor_briefing.md`
"What I will produce after this session" item 3) commits to a 0.2.0
bump with the "revised parameters". Because the parameter revisions
that depend on platform measurements have not yet been executed, the
0.2.0 bump is restricted to rationale consolidation and traceability
to the SRS; the numerical revisions will produce the 0.3.0 bump after
the M-1 to M-5 campaign closes. This convention preserves semantic
versioning meaning: 0.2.0 marks the F1 rationale closure, 0.3.0 marks
the F1 numerical closure, and any minor bumps in between (0.2.1 etc.)
record purely cosmetic edits to comments or formatting.

Downstream: the cage logic and the unit tests are unaffected (no
parameter values changed); `pytest cage/tests/` continues to pass.
The hash of `cage/cage.yaml` referenced in the metadata of every
experimental run changes, which is correct semantic behaviour (the
file content has changed, the metadata correctly records that).

`pytest cage/tests/` → 13 passed (re-run after the bump).

---

## [13.05.2026] — Calibration campaign infrastructure (M-1..M-5)

**Document(s) affected:** `experiments/calibration/` (new directory).  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Created `experiments/calibration/` with one protocol document per
measurement and a top-level `README.md` that orchestrates the
campaign:

- `README.md`: campaign overview, effort table, execution-status
  table, output-format conventions, closure criterion.
- `M1_lidar_static_noise.md`: procedure, expected JSON schema,
  decision rule for confirming or revising SR-001 `d_max` margin.
- `M2_control_latency.md`: protocol for measuring end-to-end
  control latency, decision rule confirming or revising the
  `LATENCY_NOMINAL = 50 ms` assumption.
- `M3_max_deceleration.md`: protocol for measuring achievable
  deceleration, decision rule coordinating SR-005 `a_min` and
  SR-008 `t_stop_max` revisions.
- `M4_speed_vs_curvature.md`: protocol for the empirical
  v_max(κ) curve, decision rule for SR-004.
- `M5_actuator_rate.md`: protocol for measuring actuator rate
  envelope, decision rule for SR-006.

Each protocol document follows the same structure: Goal, Closes,
Effort, Procedure, Expected output JSON schema, Decision rule,
Results table (to be filled in upon execution), and Propagation
actions on completion. The propagation actions are explicit about
which artefacts (SRS section, cage.yaml block, manuscript section,
ODD-Spec parameter, CHANGELOG entry) must be updated when a
measurement closes.

The supervisor briefing for F1 (item 4 of "What I will produce after
this session") commits to "a documented set of measurement reports
under `experiments/calibration/` covering M-1 through M-5". The
measurements themselves require platform/simulator access and are
deferred to execution by the student; the *protocols* — which fix the
procedure, the output format, and the decision rule before
execution — are produced now so that the campaign can run with
explicit pre-registered criteria, removing degrees of freedom that
would otherwise enable post-hoc rationalisation of marginal results.

The "no measurement results yet" status is recorded transparently in
the README's execution-status table; the campaign closes (and the
G1 sign-off can proceed) when all five rows report `done` and the
corresponding propagation actions have been taken.

No downstream artefact is affected by the scaffold itself. When the
campaign executes, the propagation actions per protocol will affect
`docs/03_safety_requirements.md`, `cage/cage.yaml` (bump to 0.3.0),
`docs/08_odd_specification.md`, the relevant manuscript chapters, and
this CHANGELOG.

`tools/check_traceability.py` → all checks PASS, 0 warnings (no
artefacts cited by the validator are modified).
`pytest cage/tests/` → 13 passed (no cage logic affected).

---

## [13.05.2026] — SRS audit pass: hazard chain consolidated to 9H / 11SR / 11SC / 18M

**Document(s) affected:** `docs/02_hazard_register.md`, `docs/03_safety_requirements.md`, `docs/04_cage_specification.md`, `docs/05_scenario_library.md`, `docs/06_metrics_catalogue.md`, `docs/DECISIONS.md`, `tools/check_traceability.py`, `tools/sync_hazard_register.py`, `tools/sync_safety_requirements.py` (new).
**Phase:** F1.
**Gate context:** before G1.
**Author:** Samuel Sanchez.

Exhaustive audit of the hazard ↔ SR ↔ cage ↔ scenario ↔ metric chain identified seven bidirectional-traceability inconsistencies and six coverage gaps. Resolved by:

- **New hazards.** H-08 (Progress stall via reward exploitation, covering both stall and adversarial-direction sub-modes), H-09 (Cage rule composition hazard). Both promoted from the "Open hazards under consideration" section.
- **New SRs.** SR-009 (Minimum forward progress, liveness pattern, with `Δt_settle = 1.0 s` carve-out to resolve conflict with SR-005 / SR-008), SR-010 (Cage rule composition consistency, reformulated to match the cage spec's deterministic single-pass pipeline rather than strict priority + iteration), SR-011 (Heading stability without sustained oscillation, closes the in-band branch of H-02 that SR-002's magnitude bound did not constrain).
- **New metrics.** M-P6 (Stall rate, verifies SR-009), M-P7 (Heading variability, verifies SR-011). M-S2 "Contributes evidence to" extended to SR-010.
- **New scenarios.** SC-EDGE-05 (cage rule co-activation matrix, dedicated SR-010 verifier), SC-PERT-03 (reward-injection negative test that validates M-P6 by inducing stall on a fine-tuned policy variant).
- **Cage specification.** New §Joint-envelope assertion and conflict resolution section; new Trigger 7 in C-05 (joint-envelope failure → emergency); C-05 trigger list expanded with the high-energy Trigger B (`v > v_warning`, `Δt_max_fast = 0.1 s`) matching the new SR-005 dual-trigger.
- **Schema rename.** `related_cage_rules` → `implementation_type` in both machine-readable tables; admits `C-XX` lists, `training`, and `arbiter` markers. `owner` column removed (always the same author). Both sync scripts and downstream docs updated; `check_traceability.py` recognises the new categorical markers.
- **Tooling.** `tools/sync_safety_requirements.py` implemented analogously to `sync_hazard_register.py`. `tools/check_traceability.py` splitter bug fixed via new `extract_section_blocks()` helper — the last section of each kind no longer absorbs trailing machine-readable tables.
- **Methodological decision.** D-25 registered in `docs/DECISIONS.md`: non-cage mitigations (training constraint, cage architecture property) are first-class implementation types alongside numbered cage rules.

The audit was prompted by the user-reported empirical observation that an RL policy in past testing converged to inaction when the reward function over-penalised forward motion — registered as H-08. H-09 was already on the "Open hazards" list and registered as a side-effect of explicitly modelling cage composition. The bidirectional inconsistencies (e.g., SR-009 declaring `Verified by SC-NOM-01..03` while those scenarios did not reciprocally list SR-009) were latent because `check_traceability.py` only verified one direction of each chain.

- Final counts: 9 hazards, 11 SRs, 6 cage rules (unchanged), 11 scenarios, 18 metrics, 8 SR patterns (added Liveness, Bounded variance).
- `cage/cage.yaml` requires a parameter addition on the next bump (`v_warning`, `delta_t_max_fast`, `f_osc_max`, `t_osc_window`, `t_osc_persist`); deferred to a separate change.
- `cage/cage_node.py` acquires deferred F2 work: the end-of-cycle joint-envelope assertion logic and the inter-cycle oscillation monitor.
- The Training Specification (Phase 3, not yet written) acquires two reward-design constraints traceable from SR-009 (progress / anti-stall term) and SR-011 (heading-variance penalty).

`python tools/check_traceability.py --strict` → all checks PASS, 0 errors, 0 warnings, across 9 hazards / 11 SRs / 6 cage rules / 11 scenarios / 18 metrics.

---

## [14.05.2026] — Chapter 4 sync + traceability matrix update + decision renumbering

**Document(s) affected:** `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`, `docs/07_traceability_matrix.md`, `docs/DECISIONS.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Closing edit pass for the F1 audit findings of 14.05.2026 covering three coordinated changes:

*Chapter 4 sync to 9 hazards / 11 SRs.* Before this pass, Chapter 4 still described the F0 baseline of 7 hazards (H-01..H-07) and 8 SRs (SR-001..SR-008) while the canonical artefacts had already moved to 9 hazards and 11 SRs after the 13.05.2026 audit. The sync updates the compact tables in §4.4.3 (Hazard Register: add H-08 stall and H-09 cage rule conflict) and §4.6.3 (SRS: add SR-009 liveness, SR-010 composition consistency, SR-011 bounded-variance heading) including parameter columns; rewrites the coverage argument in §4.4.4 across the four-function eje plus the new meta-architectural eje for H-09; adds explicit out-of-STPA-scope rationale for H-08 (training-time pathology) and H-09 (composition hazard) in §4.5.1; expands §4.6.4's per-SR rationale synthesis to cover SR-009, SR-010 and SR-011; revises §4.7.2's relative-completeness argument from 7×8 to 9×11; expands the H↔SR matrix in §4.8.2 from 7×8 to 9×11 with the three new full-coverage cells (H-02↔SR-011, H-08↔SR-009, H-09↔SR-010); updates §4.10 synthesis to nine hazards and eleven SRs with explicit mention of the non-cage implementation types (training, arbiter). The pending-work appendix is updated to mark D12-D17 items as completed where the 13.05.2026 audit closed them.

*Traceability matrix human-readable update.* `docs/07_traceability_matrix.md` §"Matrix summary" extended from 8 to 11 rows: added H-02↔SR-011↔(C-06 + training)↔SC-EDGE-01/04↔M-P7, H-08↔SR-009↔training↔SC-NOM-01/02/03 + SC-PERT-03↔M-P6 + M-S2(monitoring), and H-09↔SR-010↔arbiter↔SC-EDGE-04/05↔M-S2 + M-I3. Row 1 (H-01↔SR-001) corrected to list only C-01 in the Cage Rule column (was incorrectly "C-01, C-03" — C-03 belongs to SR-003's row). Added explanatory paragraph below the table noting the three valid implementation kinds (numbered rule, `training`, `arbiter`) per D-25.

*Decision renumbering D-03..D-08 → D-26..D-31.* Chapter 4 was citing decisions D-03..D-08 with one set of meanings (HARA convention, STPA scope, SR-CL-A consequences, AI-hazard exclusion) while the DECISIONS.md index had since reassigned D-03..D-08 to a different set of decisions (OE1–OE7 mapping, SAE Level 2 scope, design science positioning, A1, A2). The chapter's internal decisions are now registered at D-26 (severity homothety convention), D-27 (selective STPA-light), D-28 (SR-CL-A requires deterministic cage rule), D-29 (SR-CL-A requires ≥25 runs), D-30 (SR-CL-A veto on global verdict) and D-31 (deliberate exclusion of non-functional AI-hazard families). Each new decision gets a full entry in DECISIONS.md following the project's ADR template (decision / alternatives / rationale / consequences). The chapter's in-text references at lines 339, 549, 763-764 and 1024 are updated to the new IDs; the decisions appendix at the end of Chapter 4 (lines 1197-1213) is rewritten to reflect the new numbering and to note that D-20..D-24 remain provisional placeholders for future cierres. Two stale "decision D-02 simulador Gazebo" references (lines 89 and 1174) are corrected to D-12 (the current Gazebo decision in DECISIONS.md).

The F1 audit of 14.05.2026 identified Chapter 4 as desynchronised with the canonical artefacts (described 7 hazards while the registers had 9), the traceability matrix summary as showing only 8 of 11 rows, and the Chapter 4 in-text decision references as colliding with the DECISIONS.md numbering. All three issues are now closed. The pre-existing measurement campaign M-1..M-5 (still pending execution) remains the principal blocker for Gate G1 sign-off; the present edit pass clears the documentation-side blockers identified in the audit.

Downstream: no cage logic, no scenario library, no SRS / Hazard Register canonical artefacts touched — the canonical sources of truth were already at 9H/11SR. The manuscript and the human-readable traceability matrix are now consistent with those sources. Chapter 5 (Cage Specification) referenced from §4.10 already documents the non-cage implementation types via D-25; no Chapter 5 edit follows from this sync.

`python tools/check_traceability.py` → all checks PASS, 0 warnings, 9 hazards / 11 SRs / 6 cage rules / 11 scenarios / 18 metrics.  
`pytest cage/tests/` → 13 passed (no cage logic affected).

---

## [14.05.2026] — F1 soft-blockers closure: typo Cap. 3, cross-checks Cap. 4, §4.10 transition

**Document(s) affected:** `manuscript/chapters/chapter_03_methodology.md`, `manuscript/chapters/chapter_04_safety_analysis_and_requirements.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Closing the soft-blocker items identified in the audit of 14.05.2026 — the work that does not depend on simulator/physical access nor on supervisor sign-off, and therefore can be done before the M-1..M-5 campaign runs.

*Chapter 3 typo fix.* §3.5.3 stated *"diez fases secuenciales (Fase 0 a Fase 9)"* — the project has seven phases (F0..F6), each with a gate G0..G6. Corrected to *"siete fases secuenciales (Fase 0 a Fase 6), … con un gate de revisión (G0 a G6) al cierre"*. This aligns with the appendix figure 7 (project_phases) which already shows F0..F6 with gates G0..G6, with Cap. 3 §3.5.4 (which already names F1 as the upper-left branch of the V), and with the `docs/.phases/Fase 0..6/` directory structure.

*Chapter 4 D18 cross-checks.* Two checklist items closed:

- **§3.7 meta-criteria vs §4.4–§4.8.** The five meta-criteria of §3.7.1 evaluated retrospectively at Cap. 11 are: (1) integrity of traceability — instantiated by the bidirectional matrix of §4.8 and validated continuously by `check_traceability.py`; (2) SR coverage by experimental evidence — set up by §4.7.1's SR-CL-A verification rules and D-30's veto on global verdict; (3) hazard-anticipation degree — set up by §4.4.4's three-axis coverage argument; (4) adoption cost and (5) matrix productivity — meta-evaluative, recorded in `DECISIONS.md`, do not need direct reflection in Cap. 4. An explicit cross-reference paragraph was added at the end of §4.7.1 anchoring meta-criteria 1, 2, 3 to their Cap. 4 antecedents.

- **A1–A5 coherence vs §3.4.** Before the pass, only A3 and A4 were cited by name in Cap. 4 (lines 104, 875, 888). A1, A2, A5 were instantiated implicitly via D-25's three-way implementation taxonomy, the "Verificación" column linking to scenarios, and the bounded ODD respectively. Explicit citations now added: A1 in §4.6.3 (paragraph after the SRS table, connecting D-25 with the Cage Spec / Training Spec split of §3.4.1); A2 in §4.6.3 (connecting the ≥25-runs convention of D-29 with the L4b' policy-behavioral-evaluation split of §3.4.2); A5 in §4.3.1 (connecting the bounded ODD + ODD-PHYS-1 sim-to-real gap deferral with §3.4.5). No contradictions detected between §4.5/§4.6 and §3.4.

*Chapter 4 D19-D20 transition refinement.* §4.10 closed with an explicit paragraph anchoring the chapter's completion to the formal F1 closure ritual: Gate G1 with supervisor sign-off, the two cuantitativos pre-requisites (M-1..M-5 campaign and ODD-Spec TBD-Q1..Q12 closure), the bump of `cage/cage.yaml` to 0.3.0, and the *post-G1* state that Cap. 5 assumes when picking up at the L3/L4a levels.

*Chapter 4 internal checklist.* The appendix at the end of Cap. 4 (lines 1116-1175) is updated: D18 items marked `[x]` with the cross-check summary; D19-D20 `[x]` on the §4.10 closure; the figure-insertion and prose-polish items relabelled `[PULIDO FASE 6]` to make their deferral explicit.

The audit of 14.05.2026 identified these four items as actionable now (no external dependencies). The remaining F1 blockers are the M-1..M-5 measurement campaign, the ODD-Spec TBDs against the simulator's `.world` / `.material` files, the Gate G1 presentation material, and the supervisor session itself.

Downstream: no canonical artefacts (Hazard Register, SRS, cage.yaml, traceability matrix, DECISIONS.md) are touched by this pass — only the manuscript chapters and the CHANGELOG. `check_traceability.py` and `pytest cage/tests/` continue to pass unchanged.

`python tools/check_traceability.py` → all checks PASS, 0 warnings.  
`pytest cage/tests/` → 13 passed.

---

## [14.05.2026] — ROS2 workspace integration under `src/` (cobraflex + cobraflex_rl)

**Document(s) affected:** root structure (new `src/` directory), `.gitignore`, `pytest.ini` (new), `docs/DECISIONS.md`.  
**Phase:** F1.  
**Gate context:** before G1 (infrastructure prerequisite for closing ODD-Spec TBDs).  
**Author:** Samuel Sanchez.

Integrated the ROS2 packages of the author's prior simulator + physical-platform stack into this repository under the canonical colcon workspace layout. Tracked packages:

- **`src/cobraflex`** — URDF/SDF of the CobraFlex 1:14 platform, Gazebo worlds (`empty.world`, `obstacles.world`, `test_world.sdf`), launch files, perception/control nodes, configs, rviz layouts, mesh visualisations.
- **`src/cobraflex_rl`** — RL training infrastructure, gymnasium-Gazebo-ROS2 interface, launch files for training campaigns.

Source: `E:\CAST\Cobra Flex Drivers & SW\src` at the working-tree snapshot of 14.05.2026. The fresh-copy integration mode is registered as decision D-32. Files filtered out during the copy: `.vscode/`, `.pytest_cache/`, `__pycache__/`, `build/`, `install/`, `log/`, `*.egg-info/`, `*.pyc`. Total: 65 files (51 in cobraflex, 14 in cobraflex_rl), 110 MB total of which 87 MB is the lidar visualisation mesh `rplidar-a2m4-r1.stl`.

Third-party drivers **deferred** (not brought into this repo): `sllidar_ros2` (Slamtec, https://github.com/Slamtec/sllidar_ros2.git, HEAD 3430009) and `zed-ros2-wrapper` (Stereolabs, https://github.com/stereolabs/zed-ros2-wrapper.git, HEAD 0719912). The decision on whether to add these as git submodules or to install them via `rosdep` is left for a later session once the actual physical-platform experiments are scoped.

*Tooling adjustments.*

- `.gitignore` extended with per-package ROS2 build patterns (`src/*/build/`, `src/*/install/`, `src/*/log/`) and with the generated rosidl bindings glob (`src/*/msg/_*.py`, `src/*/srv/_*.py`, `src/*/action/_*.py`).
- `pytest.ini` added at the repo root to constrain `pytest` auto-discovery to `cage/tests`. Without this, running `pytest` from the root would attempt to collect the ament_python tests under `src/cobraflex/test/` (`test_copyright.py`, `test_flake8.py`, `test_pep257.py`) and fail with `ModuleNotFoundError: No module named 'ament_pep257'` because the ament test infrastructure is not part of the safety-side dev environment. The ROS2 tests inside `src/` continue to run via `colcon test` from a ROS2 environment, as intended.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings (no traceability artefacts touched).
- `python -m pytest` (from root, after `pytest.ini`) → 13 passed; only `cage/tests/` discovered.
- `python -m pytest cage/tests/` → 13 passed (explicit invocation also works).
- `python tools/apply_calibration.py` → exit 0, "not_executed" × 5 (unchanged).
- No internal `.git`/`build`/`install`/`log`/`__pycache__`/`.pytest_cache` directories under `src/` after the copy (verified by `find`).

*Open follow-ups.*

- Decide whether `src/cobraflex/meshes/rplidar-a2m4-r1.stl` (87 MB) stays in git or moves to Git LFS / external download. Acceptable for now but worth revisiting before any externally-published version of the repo.
- Decide submodule vs. rosdep for `sllidar_ros2` and `zed-ros2-wrapper` once physical-platform scope is fixed.
- Update README with the `colcon build` workflow when the supervisor needs the buildable-from-clone path documented (deferred to F2 entry — Phase 2 starts working against the cage_node inside the ROS2 graph).
- Reconcile Cap. 3 §3.6.1's reference to "Gazebo" with the actual simulator declared in `src/cobraflex/worlds/` (Gazebo .world / .sdf) and in the ODD-Spec (which currently says "MuJoCo material spec" — this label may need correction during the ODD-Spec TBD closure).

---

## [14.05.2026] — Post-integration follow-ups: heavy mesh, MuJoCo→Gazebo, README build instructions

**Document(s) affected:** `.gitignore`, `docs/08_odd_specification.md`, `experiments/odd_inspection/odd_tbds.yaml`, `experiments/odd_inspection/README.md`, `README.md`, new `scripts/download_meshes.sh`, new `src/cobraflex/meshes/README.md`.  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Three coordinated follow-ups closing the gaps identified at the end of the `src/` integration entry above.

*Follow-up 1 — Heavy mesh `rplidar-a2m4-r1.stl` (87 MB) untracked.* The Slamtec RPLidar A2 visualisation mesh is the single biggest file in the repository at 87 MB out of the 110 MB total of `src/cobraflex/`. The file is upstream-distributed by Slamtec, does not change with the thesis work, and exceeds the 50 MB soft-limit that GitHub flags. Action taken:

- `git rm --cached src/cobraflex/meshes/rplidar-a2m4-r1.stl` to stop tracking; the file remains on the working tree for the local build and continues to be referenced by the URDF.
- `.gitignore` extended with `src/cobraflex/meshes/rplidar-a2m4-r1.stl`.
- `scripts/download_meshes.sh` created as the canonical mechanism for fetching the mesh on a fresh clone. The current implementation is a stub that prints clear manual-acquisition instructions because the Slamtec CAD URLs are not publicly stable; when a stable mirror is decided (a thesis-controlled release artefact, an S3 bucket, etc.), the URL slot in the script is filled in and `curl` does the rest. The script is idempotent and skips files already present at expected size.
- `src/cobraflex/meshes/README.md` documents which meshes are tracked (the three CobraFlex CAD parts at ~23 MB total + the 78 KB ZED Mini reference) and which are externally-obtained (the RPLidar mesh), with explicit instructions and rationale.

The mesh is still in the repository's git history at commit 029ad28 ("F1: added ROS src folders for cobraflex and cobraflex_rl"). Removing it from history requires `git filter-repo` or equivalent and is a destructive operation deferred until publication, when the repository will be reviewed for size and external-distribution cleanliness in one pass.

*Follow-up 2 — Simulator label "MuJoCo" → "Gazebo".* The Phase 0 ODD-Spec was drafted before the simulator choice was finalised and referred to "MuJoCo material specification" / "MuJoCo map files" / "MuJoCo map geometry" / "MuJoCo `<geom>`". The actual simulator now packaged in `src/cobraflex/worlds/` is Gazebo (`.world` / `.sdf` files with the SDFormat `<surface><friction>` block), consistent with decision D-12 (§3.6.1 of Chapter 3). The label "MuJoCo" is replaced throughout the ODD-Spec body (§4.1, §4.2, §9 master parameter table, §11 TBD-Q1 row), in the YAML template `experiments/odd_inspection/odd_tbds.yaml` (inline examples), and in the README of `experiments/odd_inspection/` (workflow + Sources-by-TBD-group table). The TBD parameter values themselves are unchanged — only the *source* annotations are corrected. `grep -rn "MuJoCo" docs/ experiments/odd_inspection/` returns zero matches post-edit.

*Follow-up 3 — Repository README updated with ROS2 build instructions.* The top-level `README.md` previously had no mention of the `src/` workspace. Added: a row for `src/` and `scripts/` in the Repository Structure table; a new "ROS2 Workspace (`src/`)" section between "Identifier Conventions" and "Reproducibility" with:

- Package roster (cobraflex, cobraflex_rl) with a brief role description per package.
- Prerequisites (Ubuntu 22.04, ROS2 Humble, gazebo-ros-pkgs, colcon, rosdep).
- One-time setup commands (`rosdep install --from-paths src --ignore-src -r -y` and `./scripts/download_meshes.sh`).
- Build commands (`source /opt/ros/humble/setup.bash && colcon build --symlink-install && source install/setup.bash`).
- Launch examples for bringup, training, and the M-2 calibration logger.
- A note on the deferred third-party drivers (`sllidar_ros2`, `zed-ros2-wrapper`) referencing decision D-32.

The intention is that an evaluator following the README from "Repository Structure" to "ROS2 Workspace" can clone, build, and run a launch file in one sequence, without re-reading the full Chapter 6 of the manuscript.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings.
- `python -m pytest` (from root) → 13 passed; only `cage/tests/` discovered.
- `python tools/apply_calibration.py` → exit 0, 5 × not_executed (unchanged).
- `python tools/close_odd_tbds.py` → exit 2, "nothing to do" (unchanged, YAML still null).
- `./scripts/download_meshes.sh` on a host that already has the file → `✓ rplidar-a2m4-r1.stl already present (91076984 bytes)`. The idempotent branch works.
- `grep -rn "MuJoCo" docs/ experiments/odd_inspection/ src/cobraflex/meshes/README.md` → no matches.

---

## [14.05.2026] — ODD-Spec TBD closure (3 of 12 at F1; remaining 9 deferred per phase)

**Document(s) affected:** `docs/08_odd_specification.md` (bumped 0.1 → 0.2), `experiments/odd_inspection/odd_tbds.yaml`, `docs/DECISIONS.md` (new D-33).  
**Phase:** F1.  
**Gate context:** before G1.  
**Author:** Samuel Sanchez.

Phase 1 partial closure of the ODD-Spec TBDs against the actual `src/cobraflex` and `src/cobraflex_rl` workspace integrated in the preceding commit. Three TBDs resolved by inspection of the simulator files; the remaining nine are explicitly deferred to later phases per decision D-33.

*Resolved at F1.*

- **TBD-Q1 FRICTION = 1.0**. All three world files under `src/cobraflex/worlds/` (`empty.world`, `obstacles.world`, `test_world.sdf`) use the empty Gazebo SDF block `<surface><friction><ode/></friction></surface>`. Gazebo ODE defaults `mu1 = mu2 = 1.0` when no explicit `<mu>`/`<mu2>` is specified, so the effective surface friction on the simulated road is 1.0. Documented as such in the YAML `source` field with a note flagging that the value comes from a Gazebo default rather than an explicit declaration.
- **TBD-Q2 A_LAT_MAX (ODD-1) = 9.81 m/s²**. Derived: `μ · g = 1.0 × 9.81`. This is the Coulomb no-skid ceiling on the lateral acceleration the policy can command without losing traction; the actually-commanded a_lat in ODD-1 is much smaller because curvature is zero and the bicycle-model steering geometry dominates.
- **TBD-Q3 CORRIDOR_EDGE = 0.1225 m**. From `src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py` line 93: `terminated = abs(track_state.ey) > (self.lane_width * 0.5)` with `lane_width = 0.245 m` from `src/cobraflex_rl/config/centerline.yaml`. Therefore `CORRIDOR_EDGE = LANE_WIDTH / 2 = 0.1225 m`, which equals `LANE_EDGE`; the ODD-Spec note "if the two differ, document the rationale" resolves to "they do not differ".

*Deferred per phase.* Q4–Q7 and Q12 (ODD-2 / ODD-4 stressor profiles) deferred to F4 because the scenario YAMLs do not yet exist under `src/cobraflex_rl/config/` — they will be specified jointly with the Scenario Library construction. Q8–Q11 deferred to F2 / F3 because the `odd3_curvy_loop` Gazebo world is not yet implemented (only `empty.world`, `obstacles.world`, `test_world.sdf` exist, and the current `centerline.yaml` is a 3 m straight). The deferral is registered as decision D-33 in `docs/DECISIONS.md` with a per-TBD rationale and target phase.

*Tooling executed.* `python tools/close_odd_tbds.py --apply` substituted `TBD-Q1 → 1.0`, `TBD-Q2 → 9.81`, `TBD-Q3 → 0.1225` in the body of the ODD-Spec (§4.2, §4.5, §4.8, §4.9 prose; §9 master parameter table; §11 resolution rows) and left a `.bak` of the pre-edit document next to the original. The remaining `TBD-Q4..Q12` literals stay in the document as designed; re-running the script after later closures is idempotent.

*Versioning.* The ODD-Spec moves from v0.1 (Phase 0 draft) to v0.2 (F1 partial closure). The cover-block status changes from *"DRAFT — contains TBD values that must be filled before Gate 1"* to *"DRAFT — 3 of 12 TBDs resolved at F1 (Q1, Q2, Q3); remaining 9 explicitly deferred per phase (Q4–Q7, Q12 to F4; Q8–Q11 to F2/F3) — see decision D-33"*. The §0.1 change-log row for v0.2 records the substantive change.

*Verification.*

- `python tools/check_traceability.py` → all checks PASS, 0 warnings (no traceability artefacts touched; the ODD-Spec is not part of the traceability graph as a node, only as an upstream parameter source cited from the SRS).
- `python -m pytest` → 13 passed.
- `grep -n "TBD-Q[123]\b" docs/08_odd_specification.md` → only matches inside the §0.1 change log row and the §11 resolution rows; zero remaining TBD-Q1/Q2/Q3 literals in the body. Q4–Q12 still present with their original counts.
- ODD-Spec v0.2 file size: 28.4 KB (up from 27.2 KB v0.1, due to the resolution-column text in §11).

*Open items propagated.*

- M-4 (speed-vs-curvature, `apply_calibration.py` decision rule for SR-004) inherits the Q8/Q9 deferral: it cannot run at F1 because `odd3_curvy_loop` is not yet built. M-4 re-scheduled together with ODD-3 closure at F2/F3 entry.
- The Phase 1 closure criterion of `experiments/odd_inspection/README.md` is now satisfied: every TBD is either *resolved* (Q1, Q2, Q3) or *explicitly deferred via a registered decision* (Q4–Q12 via D-33).

---
<!-- Subsequent entries appended below -->
