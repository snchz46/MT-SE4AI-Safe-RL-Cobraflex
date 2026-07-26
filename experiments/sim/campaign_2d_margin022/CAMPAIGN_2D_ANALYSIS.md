# Posterior 2-D verdict campaign (margin022) — analysis (26.07.2026, D-65)

Campaign: `experiments/sim/campaign_2d_margin022/` — **1970 runs, 0 errors**, 28 complex_b
scenarios × {enforcement, monitoring}, seed 2024, policy = margin022 (2-D steer+throttle,
`4f3b56e2…`), authorised by the T3 D-43 preflight (D-62). D-29 feasible for all 14 SRs.
This is the **first full verdict campaign on the 2-D action** — posterior E5; it does NOT
reopen the frozen 1-D E verdict (GE4-V2, ED-2/D-49).

## Global verdict: NOT SATISFIED (literal) — but no safety predicate is breached

5 SR Satisfied (SR-001/003/004/011/013), 8 not (SR-002/005/007/008/009/010/012/014),
1 indeterminate (SR-006). As with GE4-V2, the literal NOT SATISFIED must be reconciled: the
8 failures trace to **only four scenarios**, none of them an in-ODD safety breach.

## The core safety predicate HOLDS in 2-D

**Road-edge contacts (the M-S5 safety metric):**

| | in-ODD (nominal + perturbed) | out-of-ODD (edge + frontier) |
| --- | ---: | ---: |
| **Enforcement (cage on)** | **0** | 50 |
| Monitoring (cage off) | 98 | 147 |

**Enforcement produces ZERO in-ODD road-edge contacts.** The 50 enforcement contacts are all
out-of-ODD frontier/edge stress (beyond the operational domain, expected). The cage holds the
safety line in 2-D exactly as in 1-D.

## The cage's value is *larger* in 2-D — and measured

The bare 2-D policy commits **98 in-ODD road-edge contacts**; the cage **removes all of them**
(0 in enforcement). The 2-D policy is weaker than the frozen 1-D policy (it errs far more
in-ODD), so the cage works harder — **433 controlled emergency stops** in enforcement — and
converts every in-ODD bare-policy failure into a safe outcome. This is the central thesis claim,
now demonstrated where the policy genuinely needs the cage.

## Per-SR reconciliation — the 8 "failures" trace to 4 scenarios, all non-breaches

| SR(s) | scenario | what actually happens | class |
| --- | --- | --- | --- |
| SR-002/005/007/008/009 | **SC-NOM-03** | 5/25 cage **emergencies** on the 300 s endurance run; **0 road-edge contacts**, max \|ey\| 88 mm (≪ 160 mm envelope). Safe controlled stops that fail the *completed* / *no-emergency* clauses. | **availability cost**, not a breach |
| SR-012/014 | **SC-PERT-05** | severe low-light/under-exposure (level 0.5): 30/40 cage **emergencies**, **0 road-edge contacts**. The cage detects degraded perception (SR-013/014 Trigger-8) and stops safely — the cage *working*. | **cage value** (safe stop under blindness) |
| SR-010 | **SC-EDGE-05** | the co-activation grid — a **genuine CL-B** in-ODD finding, identical in character to GE4-V2's SR-010 (1-D). | genuine CL-B |
| SR-009 | **SC-PERT-03** | the stall two-arm meta-test; the stall_variant arm "fails" M-P6 > 50 **by construction** (a mis-designed adversary; closed via the scripted-stall metrology, **D-64**). | documented construct |

**Summary:** 7 of the 8 failing SRs are driven by cage **emergencies (safe controlled stops)** —
an *availability* cost of the weaker 2-D policy tripping the cage on the long endurance run
(SC-NOM-03) and under severe perception degradation (SC-PERT-05, where the stop is the cage
correctly handling blindness). SR-010 is the same genuine CL-B co-activation finding as 1-D;
SR-009's SC-PERT-03 arm is the documented stall construct (D-64). **No in-ODD road-edge safety
predicate is breached in enforcement.**

## The honest 2-D finding

The 2-D policy is **materially weaker** than the frozen 1-D policy: 98 in-ODD bare-policy
road-edge contacts (vs ~0 for 1-D in-ODD), and it trips the cage into 433 emergency stops. The
cage keeps it **safe** in every in-ODD case, but at a **higher availability cost** (more
unnecessary-looking safe stops, especially on the 300 s endurance run and under low light). So
the 2-D result is: *safety preserved, availability reduced* — the expected cost of the more
expressive (throttle-commanding) but less-trained action, contained by the cage.

## Figures (English)

`figures/fig_frontier_excursion.png`, `figures/fig_frontier_cage_benefit.png` — enforcement vs
monitoring max excursion + measured cage benefit on the frontier scenarios.

## Verdict framing (does not reopen G4)

Recorded as literal NOT SATISFIED + this reconciliation (mirroring the GE4-V2 precedent, D-47):
the core in-ODD safety holds; the NOT SATISFIED is availability + one CL-B + the documented stall
construct. Posterior E5; the frozen 1-D E verdict is untouched. See D-65.
