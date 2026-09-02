# AGENTS.md

**This file is a pointer, not a copy. The repository's agent guidance lives in
[`CLAUDE.md`](CLAUDE.md) — read that.**

Until 2026-07-20 this file was maintained as a parallel copy of `CLAUDE.md` for
agent tooling that looks for `AGENTS.md` by name. It then fell behind by six
weeks: its phase snapshot predated **D-67** (the 2-D PPO policy becoming the
research trunk), **D-69** (the verdict of record re-pointed to
`campaign_2d_ppo550k`, and the simulation programme closed) and the whole of
**Phase 5** (sim-to-real retrain + physical deployment, D-70…D-80, closed
2026-09-01). Two divergent status files is one more than this repo can keep
honest, so the copy was collapsed into this pointer on 2026-09-02 rather than
re-synchronised.

## The thirty-second version

Master's thesis (Samuel Sanchez, HS Esslingen, Automotive Systems M.Sc.,
supervisor Prof. Dr.-Ing. Ralf Schüler) on **runtime safety cages + RL for
lane-following** on the CobraFlex 1:14 platform, under a **SE4AI** methodology.
The defining commitment is traceability:

```text
Hazard → Safety Requirement → Cage Rule → Scenario → Metric → Logged Evidence → Verdict
```

`python tools/check_traceability.py` is a hard gate and must pass before any
Gate review or commit that touches `docs/`.

## The two rules that matter most if you read nothing else

1. **Never run `git commit` or `git push`** (user rule, 2026-06-25). Leave
   changes in the working tree; the author reviews and commits by hand. Offer to
   draft the message, then stop. When the author does commit, write the message
   as the human author — **no** agent attribution, `Co-Authored-By`, or
   "Generated with" trailers.
2. **Don't claim a feature works without running it.** ROS2 nodes especially:
   typecheck and pytest are not "it works". If you cannot launch the world on
   this host, say so explicitly.

## Where the current state actually lives

| You need… | Read |
| --- | --- |
| Phase status, repo map, conventions, commands, working rules | [`CLAUDE.md`](CLAUDE.md) |
| What changed when | [`docs/CHANGELOG.md`](docs/CHANGELOG.md) |
| Why a decision was taken (cite by ID, don't re-argue) | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| The traceability matrix and every SR verdict | [`docs/07_traceability_matrix.md`](docs/07_traceability_matrix.md) |
| Phase-5 physical deployment, and the measured sim-to-real gap ledger | [`docs/17_physical_deployment.md`](docs/17_physical_deployment.md) (§14) |
| The thesis itself | [`manuscript/README.md`](manuscript/README.md) |
