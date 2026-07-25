# SC-PERT-03 fine-tune attempt — ABORTED (24.07.2026)

This preregistered manifest's single fine-tune attempt was terminated by an
operator SIGKILL **during Gazebo bring-up / the first training rollout**, before
any training step was committed and before any checkpoint or training metadata
was written. `status: training`, `training_attempted_at` set, but
`derived/checkpoint` never produced.

Cause: the operator misread the trainer's cosmetic progress display
("75001/50000 (150%)") as a no-op and killed the run. It was in fact training
correctly — SB3 2.8.0 `_setup_learn` adds `num_timesteps` to `total_timesteps`
when `reset_num_timesteps=False`, so the run targets 125000 (= 75000 parent +
50000 fine-tune); the custom ProgressBarCallback only prints and never stops
training.

**No training result exists in this attempt** (0 committed steps, 0 artifacts),
so it hides nothing. A fresh manifest was preregistered in
`experiments/sim/training/sc_pert_03_margin022_run/` with an IDENTICAL protocol
(same parent checkpoint hash, λ_stall=4.0, 50k steps, same scenario/criterion —
nothing tuned). The anti-gaming guard (one attempt per manifest) is respected:
the block prevents silent *retuning*, not a clean re-preregistration after a
zero-artifact infrastructure abort.
