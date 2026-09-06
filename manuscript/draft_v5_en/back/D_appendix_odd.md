# Appendix D — Operational domain specification

Consolidated table of parameters for the four operational domains. Each parameter has a
name, a value per domain and a provenance; no claim in the body about the domain rests
on a qualitative description when a named parameter exists.

| `*.V_MAX` / `*.V_MAX_STRAIGHT` | Speed ceiling, straight (m/s) | 0.5 | 0.5 | 0.5 | 0.5 | SR-004; C-04. Operating point = 0.20 |
| `*.V_MAX_CURVE` | Speed ceiling, curve (m/s) | n/a | n/a | 0.25 | 0.25 | SR-004; C-04 |
| `*.K_KAPPA` | Curvature speed-decay coeff. | n/a | n/a | 0.3 | 0.3 | SR-004; C-04 |
| `*.KAPPA_MAX` | Max local curvature (1/m) | 0 | 0 | 1.14 | 1.14 | 1 / 0.876 m (complex_b centre R_min); driven ≈ 1.00; oval legacy 1.25 |
| `*.A_LAT_MAX` | Max commanded lateral accel. (m/s²) | 9.81 | 9.81 | TBD-Q10 | TBD-Q10 | Coulomb ceiling FRICTION×g (ODD-1); ODD-3 deferred to M-4 |
| `*.T_CTRL` | Control cycle period (ms) | 50 | 50 | 50 | 50 | cage.yaml (20 Hz deployment); sim train/eval 10 Hz (control_dt 0.10 s) |
| `*.LATENCY_NOMINAL` | Nominal control latency (ms) | 50 | 50 | 50 | 50 | Implementation; SR-001 rationale |
| `*.STALENESS_MAX` | Max admissible state staleness (ms) | 200 | 200 | 200 | 200 | SR-007 (cage budget 0.5 s at 10 Hz, cage 0.6.1) |
| `*.LANE_EDGE` | Geometric lane edge (m, from centre) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | LANE_WIDTH / 2 |
| `*.CORRIDOR_EDGE` | Episode-termination edge (m) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | Episode-termination logic (= LANE_EDGE) |
| `*.ROAD_EDGE` | Painted road boundary (m, from centre) | 0.26 | 0.26 | 0.26 | 0.26 | ROAD_WIDTH / 2; off-road / M-S5 criterion (oval legacy 0.25) |
| `*.STUCK_TIMEOUT` | Stuck criterion timeout (s) | n/a | n/a | n/a | n/a | Subsumed by env truncation (500 × 0.10 s = 50 s); TBD-Q11 |
| `*.OBS_DIM` | Observation | camera 84×84×4 (policy); CV lane-estimate (cage) | same | same | same | Track 'E' (D-43). F-track baseline: 6-D state vector |
| `*.ACT_DIM` | GE4-realised action vector dimension | 1 | 1 | 1 | 1 | Steering-only verdict parameter (D-49). Posterior Gazebo and Isaac configs set 2 locally (D-50/D-59/D-60) without changing this ODD value |

## D.1 Open questions of the domain and their closure

Of the twelve quantitative questions that the specification opened when it was written, eleven are
closed with an explicit value and its date; the twelfth remains open because of a hardware
dependency and not because of an omission.

| TBD-Q1 | Friction coefficient of the road surface? | SS | closed | 1.0 — world SDFs ship an empty `<surface><friction>` block; Gazebo ODE defaults `mu1=mu2=1.0`. Inferred, not explicit `<mu>`; re-read if a future world sets one. (2026-05-14) |
| TBD-Q2 | Max commanded lateral accel., ODD-1? | SS | closed | 9.81 — Coulomb ceiling FRICTION×g. Physical envelope, not a typical value (operational `a_lat ≈ 0` at κ=0). (2026-05-14) |
| TBD-Q3 | Numerical drivable-corridor edge; why differ from LANE_EDGE? | SS | closed | 0.1225 — the env terminates at `\|ey\| > lane_width/2`; CORRIDOR_EDGE = LANE_EDGE, no separate margin. (Track 'E' adds off-road-by-road-centre-distance vs ROAD_EDGE = 0.26 for self-approaching loops, docs/11 §3.5.) (2026-05-14) |
| TBD-Q4 | Lighting-degradation + noise in the nominal-adverse profile? | SS | closed | Superseded on track 'E' by the camera visual-degradation stressors (§5.5): glare/low-light/motion-blur (H-10), levels grounded in the GE2 oracle. F-track legacy value in `adverse_profiles.yaml`. (2026-06-03; retargeted 2026-07-07) |
| TBD-Q5 | Latency / jitter / actuation-imperfection profile? | SS | closed | Superseded on track 'E' — the perception channel, not state-vector latency, is the ODD-2 axis; F-track legacy `odd2_adverse_with_latency` retained historically. (2026-06-03; retargeted 2026-07-07) |
| TBD-Q6 | Obstacle geometry / position / quantity? | SS | closed (retired) | Retired — no obstacle observation channel; no obstacle scenario in the verdict library. The F4 spec-only box profile is withdrawn. (2026-07-07) |
| TBD-Q7 | Full parameterisation of the adverse-full profile? | SS | closed | On track 'E' = the union/compound of the §5.5 camera stressors (e.g. SC-PERT-13 = worn markings + glare). (2026-06-03; retargeted 2026-07-07) |
| TBD-Q8 | Total loop length of the curvy world? | SS | closed | complex_b: 19.22 m (centre) / 19.93 m (driven), from `complex_b_centerline.yaml` (`perimeter_m`). Oval legacy ≈ 8.0232 m (centre) / 8.79 m (driven). (2026-05-21; retargeted 2026-07-07) |
| TBD-Q9 | Minimum curvature radius / KAPPA_MAX? | SS | closed | complex_b: R_min ≈ 0.876 m (centre) / 0.998 m (driven) → KAPPA_MAX ≈ 1.14 m⁻¹ (centre) / 1.00 (driven); shaped to the §6.2 monocular boundary. Oval legacy R_min 0.80 → 1.25 m⁻¹. (2026-05-21; retargeted 2026-07-07) |
| TBD-Q10 | Max commanded lateral accel., ODD-3, from FRICTION + V_MAX_CURVE? | SS | M-4 (F5) | OPEN, and now closed *as* open (Phase 5 ended 01.09.2026 without M-4, and no further physical measurement is planned). Coulomb upper bound `A_LAT_MAX ≤ FRICTION×g = 9.81 m/s²`; operational value at V_MAX_CURVE=0.25 on driven R_min≈1.0 m is `V²/R ≈ 0.063 m/s²` — well below. The 2-D verdict-of-record campaign ran at ≈0.216 m/s (`a_lat ≈ 0.047 m/s²`), so it neither approaches nor could bound the envelope: in Gazebo `A_LAT_MAX` is a *property of the friction model that was assumed*, so measuring it there would return the assumption. Unmeasurable in simulation by construction (D-33) — a hardware dependency, not an outstanding action item — and the hardware phase closed without taking it. The figure would close with **M-4**; it is carried as future work, and this spec stays below v1.0 by design. |
| TBD-Q11 | Stuck-criterion timeout? | SS | closed | n/a — no separate stuck monitor; env truncation `max_episode_steps × control_dt = 500 × 0.10 s = 50 s` is the implicit timeout. (2026-05-21, F3 update 2026-06-01) |
| TBD-Q12 | Do ODD-4 profiles add any stressor beyond ODD-2? | SS | closed | No — ODD-4 = ODD-3 geometry × ODD-2 perception stressors (§7.1), realised as curve-traversing complex_b scenarios (SC-PERT-11/12/13, SC-FRONT-07). (2026-06-03; retargeted 2026-07-07) |
