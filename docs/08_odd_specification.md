# ODD Specification — SE4AI Lane Following Thesis

**Document ID:** `ODD-SPEC`  
**Version:** 0.9.1 (pre-deployment 2-D verdict of record, 31.07.2026 — the qualification
contract of 0.9 was executed: the 2-D PPO policy at cap 0.22 was trained to 1M, checkpoint
550k selected (D-66) and run as the **verdict of record** campaign (1890 runs, D-69). **No
`ODD-N.<PARAM>` changed**; the entry records that the 0.22 contract is no longer a
preregistered intention but measured evidence, and that the last simulation campaign before
physical deployment could not — and by construction never could — close **TBD-Q10**.
0.9 = posterior Gazebo 2-D qualification contract, 20.07.2026 — keeps the
ODD and GE4 parameters frozen while recording the bounded 75k/0.22 parent,
150k replay coverage and checkpoint-bound D-43 gate; 0.8 = post-G4 evidence reconciliation — keeps the
GE4-V2 1-D PPO verdict frozen while recording the posterior Gazebo PPO/SAC 1-D/2-D
evidence and its distinct speed contracts; 0.7 = E-track / G4-closed rewrite, 07.07.2026 — retargets the concrete
realisation from the F-track oval to the **track-'E' front-camera policy on the
`complex_b` circuit** (the GE4-V2 verdict of record), re-specifies the ODD-2/ODD-4
adverse axis as **camera-perception degradation** (H-10/H-11/H-12), rewrites the
sensor/actuation interfaces for the front camera + the cage's own CV lane-estimator
(D-43), and expands §8 to the Isaac sim-to-real posterior track. 0.6 = F4 single-oval
reconciliation §12; 0.5 = F4-entry TBD closure; 0.4 = F3 housekeeping.)  
**Owner:** Samuel Sánchez  
**Phase of birth:** F0 — Phase of maturity: F1 — Phase of revision: track 'E' / G4  
**Status:** LIVING (signed off at G4, 02.07.2026) — **11 of 12 TBDs resolved; every
simulation-resolvable TBD is closed**. Only **TBD-Q10** (`ODD-3.A_LAT_MAX`, physical
lateral-accel envelope) remains, deferred to the M-4 physical calibration (F5). It is
**unmeasurable in simulation by construction** (decision D-33, §12.3), so the completion of the
final pre-deployment campaign on 31.07.2026 does not and cannot close it — it is a disclosed
hardware dependency, not an outstanding action item.  
**Last updated:** 2026-07-31

**Approving reviewer (Gate 1 / Gate 4):** [supervisor name]  

<!--
TEACHER NOTE: This is the cover block. Treat the version as a strict integer-decimal:
0.1 = first complete draft, 0.2…0.9 = revisions, 1.0 = "all TBDs resolved, all values
measured" (reached only when M-4 closes Q10 on the physical platform — §12.3).
The Hazard Register, the SRS, the Cage Spec and the Scenario Library all cite specific
sections and `ODD-N.<PARAM>` identifiers of this document, so do NOT renumber sections
or rename a parameter ID once it is cited — only append and re-value. This rewrite
retargets the *realisation* (oval → complex_b, state-vector → camera) but preserves
every parameter ID that downstream artefacts cite.
-->

## 0.1 Change log

| Version | Date | Author | Summary |
| ------- | ---- | ------ | ------- |
| 0.1 | 2026-05-02 | SS | Initial structural extraction from `draft_V3.docx` §6.1, with TBDs for unresolved quantitative items. |
| 0.2 | 2026-05-14 | SS | F1 partial closure of TBD-Q1 (FRICTION = 1.0), TBD-Q2 (A_LAT_MAX = 9.81 m/s²) and TBD-Q3 (CORRIDOR_EDGE = 0.1225 m). Simulator label "MuJoCo" → "Gazebo" throughout. |
| 0.3 | 2026-05-21 | SS | F2 closure of TBD-Q8 (oval ROAD_LENGTH), TBD-Q9 (oval KAPPA_MAX = 1.25 m⁻¹) and TBD-Q11 (STUCK_TIMEOUT = n/a, subsumed by env truncation). Geometry source: `scripts/compose_lane_circuit.py` preset `oval_R080`. |
| 0.4 | 2026-06-01 | SS | F3 housekeeping: `max_episode_steps` 400→500, so the truncation window that subsumes STUCK_TIMEOUT is `500 × 0.10 s = 50 s`. No ODD parameter changed. |
| 0.5 | 2026-06-03 | SS | F4-entry closure of TBD-Q4–Q7 (ODD-2 stressor profiles) and TBD-Q12. Source: `src/cobraflex_rl/config/adverse_profiles.yaml`. Obstacle profiles specced but execution-deferred. Only Q10 left. |
| 0.6 | 2026-06-08 | SS | F4 single-world reconciliation (§12, D-37): the F4 **F-track** campaign realises ODD-1..4 on the single oval `lane_following_oval.world` at one fixed-speed `ACT_DIM=1` operating point. No ODD parameter changed. |
| **0.7** | **2026-07-07** | **SS** | **Track-'E' / G4-closed rewrite.** The concrete realisation moves from the **F-track state-vector policy on the oval** to the **track-'E' front-camera policy on the `complex_b` circuit** — the **GE4-V2 verdict of record** (297k E-main, 1970 runs, 28.06.2026; G4 closed 02.07.2026). Changes: **(a)** ODD-2 / ODD-4's differentiator is re-specified from "state-vector sensor noise + latency + obstacles" to **camera-perception degradation** — visual degradation (glare / low-light / motion-blur = **H-10**), perception loss (occlusion = **H-11**) and cage lane-misdetection (false-lane = **H-12**), with the H-10 domain-randomisation trio + the SC-PERT-04..13 eval stressors + the worn/wet/gaps world variants as the named profiles (§5.5); **(b)** the sensor/actuation interfaces (§4.6) are rewritten for the **front camera** (Lane Cam IMX219-160 mirror, 640×360) feeding the policy CNN, and the cage's **own deterministic CV lane-estimator** (D-43), replacing the privileged state vector; the F-track 6-vector is retained as the frozen ground-truth **baseline**; **(c)** the geometry (§6) moves oval→`complex_b`: `ROAD_WIDTH` 0.50 → **0.52 m** (road edge 0.25 → **0.26 m**), perimeter 8.79 → **19.22 m** (centre) / **19.93 m** (driven right lane), `KAPPA_MAX` 1.25 → **1.14 m⁻¹** (centre R_min 0.876 m; driven R_min 0.998 m); a new **`*.ROAD_EDGE`** parameter (0.26 m) records the off-road boundary the E-track uses; **(d)** the action stays **1-D steering-only** (D-49) — the 2-D speed envelope of ODD-3/ODD-4 is deferred to the **Isaac posterior track** (D-50); **(e)** §8 expanded to the **Isaac Sim sim-to-real** forward reference (docs/13–14); **(f)** §12 rewritten from D-37 (F4 oval) to the **GE4-V2 complex_b realisation**. Only Q10 remains open. Ignores the standing "do not rewrite doc 08" note by user request. |
| **0.8** | **2026-07-20** | **SS** | **Post-G4 evidence reconciliation.** GE4-V2 remains the frozen 1-D PPO verdict at 0.20 m/s. Records the separate posterior Gazebo evidence: PPO/SAC camera policies in 1-D and 2-D, the current Gazebo 2-D authority cap `max_speed_mps = 0.25`, the diagnostic 0.22 m/s margin probe, the first full-horizon 2-D enforcement runs, and the two-seed SC-PERT subset. Keeps Isaac as a different posterior simulator with its own 2-D 0.5 m/s contract. No `ODD-N.<PARAM>`, SR threshold, cage constant, or G4 verdict changed. |
| **0.9** | **2026-07-20** | **SS** | **Posterior qualification contract.** Adds no ODD parameter: preregisters a fresh bounded-75k Gazebo parent at 0.22 m/s, 150k replay covering its 50k SC-PERT continuation, and a checkpoint/config-bound D-43 preflight before execution. Historical 0.25 evidence and the diagnostic 0.22 probe remain distinct. |
| **0.9.1** | **2026-07-31** | **SS** | **Pre-deployment verdict of record.** Adds no ODD parameter. The 0.9 contract was executed end-to-end: PPO 2-D at cap 0.22 trained to 1M on `complex_b`, checkpoint **550k** selected on driving quality rather than reward (D-66), D-43 preflight PASS 7/7, and the **1890-run verdict campaign** run as the last simulation campaign before physical deployment (D-69). The §7.3 operating-point prose is updated from "specified but not trained" to measured: the policy runs at ≈0.215–0.218 m/s under the 0.22 cap with throttle modulation localised to the tightest apexes but marginal in magnitude (floor 0.81). `ODD-3.A_LAT_MAX` (**TBD-Q10**) is explicitly recorded as *unclosable by this or any simulation campaign* (D-33). Isaac keeps its separate 0.5 m/s full-authority contract. |
| **0.9.2** | **2026-08-17** | **SS** | **First physical measurement reaches the spec.** Adds no `ODD-N.<PARAM>` and re-values nothing. §8.1 records the platform team's bench characterisation of the real car (*CobraFlex 1:14 Parameters_0813*, 13.08.2026): total mass **3.5 kg** (the URDF budget was 6.59 kg, 1.88× too heavy — rescaled in `src/cobraflex/urdf/`), geometry confirmed, straight-line tracking ≈0.99, and the one contradiction — **yaw tracking 0.4954× commanded** where Gazebo's DiffDrive delivers ~1:1, halving every steering-expressed cage margin on hardware (transfer risk **T2**; compensated at deployment via `steering_to_yaw_rate_gain 0.8 → 1.615`, docs/17 §2 item 4). Also flags three supplied quantities that are *not* evidence: the inertia tensor (this repo's own URDF box at the old 5.0 kg, read back out of Isaac), the 0.53 m/s / 6.0 rad/s maxima (serial-driver clamps; 6.0 is unreachable), and a frame-ambiguous CoG that was not applied. **TBD-Q10 (`ODD-3.A_LAT_MAX`) is untouched** — no lateral-accel measurement was supplied, so M-4 remains open and the spec stays below v1.0. |
| **0.9.3** | **2026-08-17** | **SS** | **Platform-repo cross-check.** Adds no `ODD-N.<PARAM>`. Reconciles §8.1 against the platform repo's own parameter document (`Waveshare-Cobra-Flex-ROS2-Autonomous-Car`, `assets/Mathematical Model/`). One **refutation**: the `0.53 m/s²` that this spec, docs/09, docs/13, docs/14, `cage_bridge.py` and D-50 all cited as *the platform's measured max linear acceleration* is the chassis's max **velocity** in m/s copied into an acceleration field; the platform figures are **±2.5 m/s²** linear, **3.2 rad/s²** angular, **20 N·m** per wheel. Every conclusion survives with a 5× larger margin; `cage.yaml` untouched and **M-3 remains open** (the 2.5 has no stated measurement provenance either). One **new geometry error**: the URDF wheelbase is **0.120 m against 0.154 m measured** — inert in Gazebo (kinematic DiffDrive), material in Isaac, where it under-models the scrub behind the yaw deficit. One **open conflict** logged, not resolved: the platform repo splits the 3.5 kg as 2.20/0.71 chassis/body and places the Jetson in the body, both contradicted by the itemised weighing and by the team's own 17.08 confirmation (docs/14 §2.2). |

---

## 1. Purpose and scope

This document specifies the four Operational Design Domains (ODD-1 to ODD-4) within which the lane-following controller of this thesis is intended to function. Each ODD is a specific combination of scenery, environmental conditions, dynamic elements, subject-vehicle dynamics envelope, and sensor and actuation interfaces. The stratification isolates a methodologically meaningful axis of variation: ODD-1 is the nominal baseline; ODD-2 adds adverse stressors on the same geometry; ODD-3 introduces curvy closed-loop geometry under nominal conditions; ODD-4 combines curvy geometry with adverse conditions. This makes it possible to attribute an observed safety or performance change to a *single* axis of complexity rather than to a confounded combination.

The thesis carries **two orthogonal tracks that share this one ODD** (docs/00; decisions D-41/D-43):

- The **F-track** (state-vector policy, ground-truth-derived cage state) is the **frozen ground-truth baseline** — the control arm for "what does camera perception cost". Realised on the **oval** (`lane_following_oval.world`).
- The **track 'E'** (end-to-end front camera, cage on its own CV lane-estimator) carries the **verdict of record** — since 31.07.2026 the **2-D PPO 550k pre-deployment campaign** (1890 runs, D-66/D-69); **GE4-V2** on the `complex_b` 297k E-main (1970 runs, 28.06.2026) is the frozen **G4 gate record** (**G4 closed 02.07.2026**). Realised on **`complex_b`** in both cases, on the same cage YAML.

Both tracks run the **same** cage rules C-01..C-06, the **same** metrics, and the **same** identifier space. What differs is *what the policy observes* (a 6-D state vector vs an 84×84 camera frame) and *where the cage's state comes from* (privileged ground truth vs a deterministic CV lane-estimator on the same camera, D-43). Sections 4–7 state the domain abstractly and give the concrete `complex_b` (track-'E') realisation as the primary reading, with the oval (F-track) values noted as the frozen legacy.

This document is the source of truth for every parameter later cited as a threshold in the Safety Requirements Specification (SRS), as a scenario boundary in the Scenario Library, or as a configuration constant in the Cage Specification. It is not a description of the simulator implementation (see docs/09, docs/11) nor of the safety analyses (see Hazard Register and SRS). It is the boundary condition from which those artefacts derive their numerical content.

<!--
TEACHER NOTE: When a reviewer asks "why does SR-001 use d_max = 0.16 m?", the answer
must trace back to a parameter that lives in this document (ODD-1.ROAD_WIDTH/2 − Δ).
Always push numerical authority upstream to this file; never let it live only in an
SR rationale.
-->

---

## 2. ODD formulation method

The four ODDs are formulated using a hierarchical taxonomy adapted from PAS 1883 (BSI 2020) and ISO 34503 (ISO 2023), expressed with the semantic discipline of ASAM OpenODD 1.0.0 (ASAM 2021). Each ODD is described in five steps: (1) intended function and subject-vehicle assumptions; (2) scenery — drivable-area type, geometry, lane specification, edge/surface characteristics, structures; (3) environmental conditions — illumination, weather, particulates, connectivity; (4) dynamic elements — other actors and their permitted states; (5) subject-vehicle dynamic envelope and the sensor/actuation interfaces. Each ODD then closes with explicit excluded conditions and ODD-exit assumptions.

A methodological distinction between ODD attributes and implementation-side stressors is preserved throughout. On the F-track, internal noise, latency and actuation imperfections were treated as scenario-side perturbations layered on top of the ODD. On **track 'E'** the same discipline applies to the **perception channel**: the visual-degradation stressors (glare, low light, motion blur, occlusion, false markings) and the road-appearance variants (worn, wet, marking-gaps) are named scenario profiles layered on the base geometry, not new ODD geometries. This is what makes ODD-2 and ODD-4 meaningful as stressor-bearing extensions of ODD-1 and ODD-3. The named profiles are documented here because their parameters are cited from SRs and cage rules; their broader test purposes belong to the Scenario Library (docs/05).

---

## 3. Identifier conventions

Three classes of identifier are distinguished. **Domain identifiers** `ODD-N` (N = 1..4) refer to the abstract operational design domain and are the identifiers cross-referenced from the SRS, Hazard Register, and Cage Specification. **Map identifiers** `oddN_<descriptor>` (e.g. `odd1_straight_road`, `odd3_curvy_loop`) refer to concrete simulator maps, lowercase snake_case. **Scenario profile identifiers** `oddN_<scenario_name>` refer to specific stressor configurations layered on a map; these match the Scenario Library names.

Numerical parameters use a stable identifier `ODD-N.<PARAM>` (e.g. `ODD-1.LANE_WIDTH`, `ODD-3.KAPPA_MAX`). This is how the SRS, Hazard Register, Cage Specification and `cage.yaml` cite values without copying them, ensuring single sourcing. **These IDs are load-bearing and are preserved across this rewrite even where their concrete world changed.**

Concrete worlds referenced below:

- `lane_following_complex_b.world` (SDF name `lane_following_complex_b`) — the **track-'E' verdict world**; a self-approaching, scalloped "M/W" circuit. Reward/lane-target centerline `complex_b_right_lane_centerline.yaml`; off-road (road-centre) centerline `complex_b_centerline.yaml`.
- `lane_following_oval.world` (preset `oval_R080`) — the **frozen F-track world** (baseline). Centerline `oval_right_lane_centerline.yaml`.
- `lane_following_complex_b_{gaps,worn,wet,flipV}.world` — appearance/geometry variants of `complex_b` used as ODD-2/ODD-4 world-variant stressors (§5.5).

---

## 4. ODD-1 — Nominal baseline

### 4.1 Intended function and subject-vehicle assumptions

The intended function is lane following on a structured, well-marked road segment under nominal conditions. The subject vehicle is the simulated CobraFlex-like platform (URDF + SDF, ROS2 Jazzy, packaged as `src/cobraflex`), a **differential/skid-steer** 1:14 platform (four fixed wheels, no steering angle — the sim DiffDrive plugin is faithful), operating at low forward speed with a single steering (yaw-rate) degree of freedom controlled by the policy. ODD-1 is the reference point against which the other domains are differentially defined; it is intentionally the narrowest of the four to support interpretable PPO training, reproducible debugging, and unambiguous scenario derivation.

### 4.2 Scenery

The drivable area is a two-lane road of uniform asphalt-like surface, with clearly visible white lateral lane boundaries and a dashed central lane separator, flat geometry, no junctions, and no special or temporary road structures. Lane width per direction is `ODD-1.LANE_WIDTH = 0.245 m`; total road width is `ODD-1.ROAD_WIDTH = 0.52 m` (track-'E' `complex_b`; the frozen F-track oval used **0.50 m**), giving a geometric road edge at **0.26 m** from the road centre (`ODD-1.ROAD_EDGE`; oval legacy 0.25 m). The road gradient is zero. The friction coefficient of the simulated surface is `ODD-1.FRICTION = 1.0` (Gazebo ODE default; the world SDFs ship an empty `<surface><friction>` block, so `mu1 = mu2 = 1.0` — see TBD-Q1).

ODD-1 is the **nominal-straight** face of the domain. On `complex_b` it is realised on the circuit's straight tiles (the run initialises mid-straight, `start_s ≈ 2.0 m`); on the oval it is realised on the 1.5 m straight tile (`start_s = 0.0`). Total road length is a property of the concrete loop, not of ODD-1 per se: `complex_b` perimeter is `19.22 m` (centre) / `19.93 m` (driven right lane); the oval is `≈ 8.79 m` (driven). The dedicated pure-straight `straight_road.world` is reserved for the physical subset (F5), where a straight is simpler to set up than a loop.

### 4.3 Environmental conditions

ODD-1 assumes dry conditions; absence of fog, snow, rain, flooding, and atmospheric particulates; and nominal uniform illumination across the entire drivable area, with clean (un-worn) lane markings. Connectivity is not required. There are no spatially varying lighting effects, shadows, reflectivity discontinuities, or marking degradation — those are the ODD-2 adverse axis.

### 4.4 Dynamic elements

No surrounding traffic, pedestrians, cyclists, animals, or moving obstacles. The only dynamic element is the subject vehicle. (Static obstacles are **not** part of any ODD in the current system — the obstacle profiles specced provisionally at F4 entry were execution-deferred and are retired in this rewrite; the camera observation has no obstacle channel and no obstacle scenario is in the verdict library. See §5.5.)

### 4.5 Subject-vehicle dynamic envelope

<!--
TEACHER NOTE: Every quantity here appears in an SR rationale (SR-004 for v_max,
SR-003 for TTLC, SR-006 for actuator smoothness). Distinguish the *envelope ceiling*
(what the platform cannot exceed) from the *operating point* (what is actually
commanded). The verdict runs at the operating point; the cage rules bound the ceiling.
-->

The forward-speed **envelope ceiling** is `[0, ODD-1.V_MAX]` with `ODD-1.V_MAX = 0.5 m/s` (SR-004; C-04 `v_max_straight`). The verdict campaigns run at a single conservative **operating point**: fixed forward speed **0.20 m/s** (`fixed_speed`, docs/09 §3 ED-2), well below the ceiling — the policy commands only steering, throttle is held. Local path curvature is `κ ≡ 0` within ODD-1 (nominal-straight). The lateral acceleration the policy could command is bounded by the no-skid Coulomb ceiling `ODD-1.A_LAT_MAX = FRICTION × g = 9.81 m/s²` (the physical envelope, not a typical value — at `κ = 0` the operationally commanded `a_lat` is ~0).

The control-loop nominal period is `ODD-1.T_CTRL = 50 ms` (20 Hz — the cage's deployment-loop rate, `cage.yaml control.cycle_period_ms`). The Gazebo **training/eval** loop runs at **10 Hz** (`control_dt = 0.10 s`); the cage's staleness/missing-state budgets are parameterised to whichever rate is active (cage 0.6.1: `staleness_max_s = n_missing_max_cycles × control_dt = 5 × 0.10 = 0.5 s` at 10 Hz). End-to-end nominal control latency between observation and applied command is assumed `≤ ODD-1.LATENCY_NOMINAL = 50 ms` (referenced by SR-001's `d_max` rationale).

### 4.6 Sensor and actuation interfaces

This is the interface that **track 'E' redefined** relative to the F-track baseline. Two consumers read the world, from disjoint pipelines but a **common camera** (D-43 common-cause):

- **Policy observation (track 'E', verdict of record).** The policy is a CNN over the **front camera** — the dedicated **Lane Cam** (IMX219-160 mirror, 640×360, HFOV ≈ 90° / 1.5708 rad, mounted at height `h ≈ 0.077 m`, pitch `0.30 rad` down). Each native frame is grayscaled and resized to **84×84×1**, frame-stacked **×4** → an `84×84×4` tensor consumed by SB3 `CnnPolicy` (NatureCNN). The policy receives **no** ground truth, no LiDAR, and no authored centerline. `ODD-1.OBS_DIM` for track 'E' is therefore an **image**, not a scalar vector.
- **Cage observation (track 'E').** The cage does **not** read the camera image or the policy's CNN. It reads its **own deterministic CV lane-estimator** (`CvLaneEstimator`, D-43; docs/12 §4) on the same native frame, producing a state `(ey, epsi, lane_width, curvature, confidence)` for the rules C-01..C-06. A **perception supervisor** wraps it: on a trustworthy estimate it stamps a cage `State` with the frame's age; otherwise it passes `perception_invalid = True` so the cage takes its missing-state path and, once persistence elapses, fires C-05 **Trigger 8** (the controlled stop, SR-013/SR-014).
- **F-track baseline (frozen).** For the ground-truth control arm the policy reads a **6-D state vector** `[ey, epsi, speed, prev_steer, kappa_near, kappa_far]` (`MlpPolicy`), and the cage reads ground-truth-derived state (`PolylineTracker` on `/odom_truth`). This is the frozen reference for "what camera perception costs"; it is not the deployable artefact (it needs a prior map and privileged pose).

For the **GE4 verdict**, the action space in ODD-1 is **one-dimensional and continuous** — steering (yaw-rate) only, `Box([-1, 1])`, `ODD-1.ACT_DIM = 1` (D-49). Throttle is held at the fixed cruise operating point and is not a controlled variable; the exogenous throttle-override stressor (SC-EDGE-03) exercises C-04. Posterior work implements a config-gated 2-D action (steering + throttle) in **both Gazebo and Isaac** (§8; D-50/D-59/D-60): Gazebo evidence uses a 0.25 m/s cap (plus a diagnostic 0.22 probe), and an **untrained** fresh contract now preregisters a bounded 0.22 parent; Isaac uses its separate full-authority 0.5 m/s contract. These posterior contracts do not alter `ODD-1.ACT_DIM = 1` for GE4.

A sensor reading is **nominal** when its timestamp is no older than `ODD-1.STALENESS_MAX = 200 ms` (SR-007) and all fields lie within their plausible ranges (§9). Violations are not part of ODD-1; they trigger H-06 (cage-state staleness) / SR-007, or — for the camera channel — H-11/H-12 / SR-013/SR-014.

### 4.7 Excluded conditions

ODD-1 excludes any non-zero curvature, any deviation from uniform illumination or clean markings, any visual degradation of the camera image, any dynamic or static obstacle, any precipitation or particulate, any sensor/perception degradation, and any forward speed exceeding `ODD-1.V_MAX`. Operation under any of these is by definition outside ODD-1; it does not necessarily violate an SR, but the corresponding evidence belongs to a different domain (ODD-2/3/4 or the out-of-ODD Frontier study).

### 4.8 ODD-exit assumptions

The system is exiting ODD-1 when the absolute lateral offset exceeds the geometric **lane edge** `ODD-1.LANE_EDGE = 0.1225 m` (= `LANE_WIDTH / 2`), when forward speed exceeds `ODD-1.V_MAX`, when the simulator reports a road-edge contact, or when an episode-termination condition fires. The policy is not designed to recover once ODD-1 is exited; recovery, if attempted, is the cage's responsibility in emergency mode (C-05; SR-005/007/008).

Two edges are distinguished, both used at runtime:

- `ODD-1.CORRIDOR_EDGE = 0.1225 m` — the **episode-termination** edge (= `LANE_EDGE`; F-track terminates on perpendicular `|ey| > lane_width/2`). On the self-approaching `complex_b` this perpendicular test folds back where the road passes near itself, so the track-'E' env judges off-road by the **global** distance to the *road-centre* centerline vs `ROAD_EDGE` instead (docs/11 §3.5) — a gated, opt-in fix that leaves the convex oval byte-for-byte unchanged.
- `ODD-1.ROAD_EDGE = 0.26 m` — the **painted road boundary** (= `ROAD_WIDTH / 2`). Crossing it is the "left the road" event; it is the headline criterion (M-S5, `road_edge_contact`) of the Frontier cage-efficacy study.

### 4.9 Parameter summary for ODD-1

See §9. Parameters declared here: `ODD-1.LANE_WIDTH`, `ODD-1.ROAD_WIDTH`, `ODD-1.ROAD_LENGTH`, `ODD-1.GRADIENT`, `ODD-1.FRICTION`, `ODD-1.V_MAX`, `ODD-1.KAPPA_MAX` (0), `ODD-1.A_LAT_MAX` (9.81), `ODD-1.T_CTRL`, `ODD-1.LATENCY_NOMINAL`, `ODD-1.STALENESS_MAX`, `ODD-1.LANE_EDGE`, `ODD-1.CORRIDOR_EDGE`, `ODD-1.ROAD_EDGE`, `ODD-1.OBS_DIM`, `ODD-1.ACT_DIM`.

---

## 5. ODD-2 — Adverse-conditions validation

### 5.1 Relation to ODD-1

ODD-2 preserves the scenery, dimensions, gradient, and friction of ODD-1 unchanged. It differs in one respect: the **environmental / perception conditions are no longer guaranteed nominal**. On track 'E' this axis is **camera-perception degradation** — the visual channel that feeds both the policy CNN and the cage's CV estimator (D-43). The subject-vehicle dynamic envelope, the control cycle, and the 1-D steering action are inherited from ODD-1 unchanged. There is **no observation-space extension** (the F4-era 8-D obstacle extension is retired — no obstacle channel exists and no obstacle scenario is in the verdict library).

### 5.2 Environmental / perception conditions

ODD-2 admits, singly or in combination:

- **Degraded illumination and exposure** — sun glare / over-exposure and low-light / under-exposure (both **H-10**), and strong shadow transitions.
- **Motion blur** — directional (horizontal) smear at speed (**H-10**).
- **Degraded / worn markings** — partially erased or faded painted lines over arbitrary arc-length stretches (worn/gaps world variants; **H-10** infrastructure face).
- **Adverse surface appearance** — worn/patched or wet/darkened asphalt (world variants).
- **Loss of valid perception** — full occlusion of the ground-view lane band (**H-11**), the specified-safe response to which is the cage's controlled stop (SR-013).
- **Misleading markings** — a plausible-but-false lane feature (fork, old paint, tar seam) that can make the cage's CV estimator lock onto a *wrong* lane (**H-12**), backstopped by SR-014's plausibility / temporal-consistency check.

Weather, particulates, gradient, and curvature remain as in ODD-1 (curvature is the ODD-3 axis). The quantitative parameterisation is in the named profiles (§5.5).

### 5.3 Dynamic elements

Identical to ODD-1: no other actors, no obstacles. ODD-2's stressors act on the **perception channel**, not on the dynamic scene.

### 5.4 Sensor and actuation interfaces

The interfaces are ODD-1's (§4.6). ODD-2 adds explicit **perturbation of the camera image before both consumers** — the D-43 common-cause design: the single degradation injector is applied once to the native frame, then the frame splits to (a) the cage's CV estimator and (b) the policy's downsample/stack. A camera fault can therefore blind both at once; the designed answer is the cage's open-loop controlled stop (SR-013/SR-014 → C-05 Trigger 8), which needs no perception. The relationship to the hazards is direct: the stressors are the controlled means by which H-10 (degradation), H-11 (loss) and H-12 (misdetection) conditions are exercised.

### 5.5 Named scenario profiles

The camera stressors are the single source of truth in the visual-degradation kernels (`src/cobraflex_rl/cobraflex_rl/visual_degradation.py`) and the per-scenario YAMLs under `scenarios_complex_b/` (the executed library) / `scenarios/perturbed/`. Two mechanisms exist: **runtime frame injectors** (applied per control cycle) and **world variants** (a different-texture `.world`, the geometry unchanged, so behaviour changes are attributable to appearance alone). Levels are grounded in the GE2 CV-estimator oracle validation.

| Profile / scenario | Mechanism | Models | Level(s) | Hazard / SR |
|---|---|---|---|---|
| `glare_overexposure` (SC-PERT-04, SC-PERT-12) | runtime injector | sun glare / specular saturation | 0.3, 0.6 | H-10 / SR-012 |
| `low_light_underexposure` (SC-PERT-05) | runtime injector | dusk / deep shadow | 0.2 (low), 0.5 (high) | H-10, H-11 / SR-012, SR-013 |
| `motion_blur` (SC-PERT-06) | runtime injector | rolling-shutter smear | 0.4, 0.8 | H-10 / SR-012 |
| `occlusion` (SC-PERT-07) | runtime injector, onset t = 5 s | lane band fully occluded | 1.0 | H-11 / SR-013 (controlled stop **required**) |
| `false_lane` (SC-PERT-08) | runtime injector, onset t = 5 s | misleading slanted bright line | 0.8 | H-12 / SR-014 (plausibility reject → stop) |
| worn markings (SC-PERT-11) | world variant `…_gaps.world` | painted lines erased over stretches | — | H-10 / SR-012, SR-014 |
| worn surface (SC-PERT-09) | world variant `…_worn.world` | patched asphalt, aged markings | — | H-10 / SR-012, SR-014 |
| wet surface (SC-PERT-10) | world variant `…_wet.world` | darker asphalt + sheen | — | H-10 / SR-012, SR-014 |

**Training-time domain randomisation (H-10 mitigation, SR-012).** During PPO training a per-episode `VisualDomainRandomizer` draws a `(mode, level)` from the **H-10 trio** (`glare_overexposure`, `low_light_underexposure`, `motion_blur`) with `p_degrade = 0.5`, `level_range = [0.2, 0.8]`. `occlusion` and `false_lane` are **eval-only** — training the policy to "see through" them would teach it to ignore exactly the cues whose loss must trigger the SR-013/SR-014 controlled stop (the cage's job, not the policy's). Domain randomisation is disabled for deterministic evaluation.

> **Retired: the F4 state-vector adverse profiles.** The v0.5 profiles (`odd2_nominal_adverse` σ_lateral=0.03 m, `odd2_adverse_with_latency` +100 ms/20 ms jitter/0.02 steer-noise, `odd2_adverse_with_obstacle` 0.10 m box) belonged to the F-track state-vector observation and are **superseded** on the verdict track by the camera stressors above. They remain valid as the historical F-track adverse spec (`adverse_profiles.yaml`); the obstacle profile was never executed (no obstacle observation channel) and is retired.

### 5.6 Excluded conditions

ODD-2 retains all ODD-1 exclusions not explicitly relaxed above. In particular, dynamic agents, obstacles, intersections, route-planning demands, gradient changes, weather beyond illumination/appearance, and curvature remain excluded.

### 5.7 ODD-exit assumptions

The ODD-1 exit conditions apply (§4.8). ODD-2 additionally treats persistent loss of a trustworthy lane percept as the trigger for the cage's controlled stop — not an ODD exit but the *designed safe response* within the domain (SR-013). A confidently-wrong estimate that is *not* rejected (the H-12 under-read, §12.2) can allow the true state to leave ODD-1 undetected; this is the documented residual perception cost, not a specified-safe behaviour.

---

## 6. ODD-3 — Nominal curvy-loop domain

### 6.1 Relation to ODD-1

ODD-3 preserves the environmental conditions and dynamic-element exclusions of ODD-1 and differs in the **scenery**: a closed loop with non-zero curvature. Its full speed-envelope face presupposes two controlled dimensions (steering + speed), but the canonical **GE4 realisation parameter** stays **`ODD-3.ACT_DIM = 1`**, steering-only (D-49), so GE4 does not exercise that face end-to-end (§12.2). Posterior 2-D configs exercise it separately in Gazebo and Isaac (§8; D-50/D-59/D-60), without changing the GE4 parameter or reopening G4.

### 6.2 Scenery

The drivable area is a structured two-lane closed loop. The **track-'E' verdict world** is **`complex_b`** — a self-approaching, scalloped circuit (a 2-hump "M" top serpentine with a pronounced central counter-steer valley, joined by wide U-turn ends), generated by `scripts/generate_complex_track.py` and offset to the driven right lane by `scripts/offset_lane_centerline.py`. Its geometry:

- Perimeter `ODD-3.ROAD_LENGTH = 19.22 m` (centre-line) / `19.93 m` (driven right lane) — ≈ 2.2× the oval.
- Minimum curvature radius `R_min ≈ 0.876 m` (centre-line) / `≈ 0.998 m` (driven right lane), giving `ODD-3.KAPPA_MAX = 1 / R_min ≈ 1.14 m⁻¹` (centre; ≈ 1.00 m⁻¹ on the driven lane). This is **the most consequential physical constant of this domain** — referenced by SR-004 and C-04.

**The monocular curvature boundary (docs/12 §4.7) is an ODD-3 constraint, not just an implementation note.** The cage's heading reading `epsi` (feeding C-02 / C-05 Trigger-7) carries an irreducible near-field bias `epsi_bias ≈ κ · X_c` (`X_c ≈ 0.225 m`, the near-window centroid). A curve tighter than `R_min ≈ 0.9 m` (κ ≳ 1.1) drives the *perceived* heading past C-02's `theta_max = 0.4363 rad (25°)` while the vehicle tracks the true lane to millimetres — a false emergency that cannot be corrected without blinding the cage to real heading faults. **`complex_b` was deliberately shaped to honour this** (driven-lane `R_min ≈ 0.998 m`, `epsi_bias ≲ 0.23 rad`), so a curve tighter than this is *outside the camera ODD for the heading rule*. The Isaac multi-circuit set (`complex_d/e`, D-50/D-51) is designed against the same boundary.

Lane width, road width and surface friction are inherited from ODD-1: `ODD-3.FRICTION = ODD-1.FRICTION = 1.0` (referenced with `ODD-3.KAPPA_MAX` by SR-004's `v_max_curve` skid-threshold rationale). The **frozen F-track legacy world** is the oval (`oval_R080`): two 1.5 m straights + two 180° U-turns of centreline radius 0.80 m, perimeter `≈ 8.0232 m` (centre) / `8.79 m` (driven), `KAPPA_MAX = 1 / 0.80 = 1.25 m⁻¹`, and the oval's `ROAD_WIDTH = 0.50 m` legacy.

### 6.3 Environmental conditions

Identical to ODD-1: dry, no fog or snow, nominal uniform illumination, clean markings, no spatial lighting variation.

### 6.4 Dynamic elements

Identical to ODD-1: no other actors, only the subject vehicle.

### 6.5 Subject-vehicle dynamic envelope

The forward-speed envelope is curvature-dependent: straight cap `ODD-3.V_MAX_STRAIGHT = 0.5 m/s` (= ODD-1.V_MAX), curve cap `ODD-3.V_MAX_CURVE = 0.25 m/s`, interpolated by `v_max(κ) = max(V_MAX_CURVE, V_MAX_STRAIGHT − k_κ|κ|)` with `ODD-3.K_KAPPA = 0.3 m/s per unit curvature` (mirrored in SR-004 and C-04). The maximum commanded lateral acceleration is `ODD-3.A_LAT_MAX = TBD-Q10`, closing when M-4 measures the physical envelope. In the **canonical GE4 realisation** the operating point is fixed at 0.20 m/s with `ODD-3.ACT_DIM = 1` (below both caps), so its policy does not exercise this envelope end-to-end. Earlier posterior Gazebo 2-D configs used `max_speed_mps = 0.25`, and a diagnostic 0.22 m/s eval cap removed one zero-margin speed-conflict stop while a D-43 heading over-read persisted under both caps. **The 0.22 contract is no longer a preregistered intention: it was trained and is now the verdict of record (31.07.2026, D-66/D-69).** A fresh PPO 2-D policy was trained to 1M on `complex_b` under that cap and evaluated over 1890 runs with `ODD-3.ACT_DIM = 2`. Measured behaviour under the cap: mean speed **≈0.215–0.218 m/s**, i.e. the policy sits essentially *at* the ceiling; throttle modulation is correctly **localised** (35.6 % of steps below 0.95 at the tightest apex vs 8.3 % overall) but **marginal in magnitude** (throttle floor 0.81), so the vehicle reaches the tightest curves near the cap rather than braking into them. Consequently the curvature-dependent interpolation `v_max(κ)` is still not stressed end-to-end: 0.22 m/s stays below `V_MAX_CURVE = 0.25`, which is the floor of `v_max(κ)`, so C-04 cannot bind — and the campaign confirms it empirically, with **C-04 firing exactly zero times across all 1890 runs in both modes** (the enforcement ledger is `C-06 181620, C-03 764, C-02 721, C-05 361, C-01 159`). The ODD-3 speed *ceiling* therefore remains untested from above even now that the action space carries speed authority; this is a **disclosed limitation of the operating point, not of the specification**. Isaac retains its separate `max_speed_mps = 0.5` full-authority contract, which is the only configuration that would exercise it. The result is evidence about implementations and margin, **not** a re-value of the ODD ceilings or action parameter — no `ODD-N.<PARAM>` changes on this campaign.

### 6.6 Sensor and actuation interfaces

Inherited from ODD-1 (§4.6): track-'E' policy reads the camera (84×84×4), the cage reads its CV estimator; the F-track baseline reads the 6-D state vector. The **canonical GE4 action parameter** is 1-D steering (`ODD-3.ACT_DIM = 1`, D-49); local posterior Gazebo/Isaac configs implement 2-D without changing that verdict realisation. Control cycle and nominal latency are inherited from ODD-1.

### 6.7 Excluded conditions

ODD-3 retains all environmental and actor exclusions from ODD-1. Curvatures above `ODD-3.KAPPA_MAX` are out of scope (and, per §6.2, tighter-than-`R_min ≈ 0.9 m` curves are outside the camera ODD for the heading rule). Speeds above `v_max(κ)` at the local curvature are out of scope.

### 6.8 ODD-exit assumptions

Inherits the lateral-offset and contact criteria from ODD-1, with the lane edge now the *local* lane edge following the curve, and off-road judged by the global road-centre distance (§4.8, docs/11 §3.5). No dedicated stuck monitor is configured; the `max_episode_steps × control_dt` env truncation (500 × 0.10 s = 50 s) is the implicit `ODD-3.STUCK_TIMEOUT = n/a`. A dedicated stuck monitor can be added later without disturbing this entry.

---

## 7. ODD-4 — Adverse curvy-loop validation

### 7.1 Relation to ODD-3 and ODD-2

ODD-4 inherits the geometry of ODD-3 and the environmental / perception stressors of ODD-2: `ODD-4 = scenery(ODD-3) + perception_conditions(ODD-2) + dynamic_elements(ODD-2)`. Unlike the F4 realisation (where ODD-4 was *not exercised* — no adverse-curvy scenario existed), the **track-'E' verdict does exercise ODD-4**: the complex_b-native camera scenarios spawn mid-straight and traverse the worn/degraded zone **through the first scallop curve**, so an adverse stressor is present on curved geometry.

### 7.2 Named scenario profiles

ODD-4 introduces **no stressor beyond ODD-2** (TBD-Q12); its profiles are the cross-product of ODD-3 geometry × ODD-2 perception stressors, realised as curve-traversing complex_b scenarios:

| Profile / scenario | Inherits (ODD-2) | Curve-specific realisation |
|---|---|---|
| SC-PERT-11 (worn markings) | worn/gaps world variant | spawns `start_s = 2.0 m`, run traverses the worn zone + first scallop curve |
| SC-PERT-12 (image degradation) | `glare_overexposure` runtime | same start, curve-extended 40 s horizon |
| SC-PERT-13 (worn markings **+** glare, compounded) | worn variant + glare | the hardest camera case; **2nd adverse scenario for SR-013** (D-29) |
| SC-FRONT-07 (mirrored geometry OOD) | clean markings | geometry OOD: the Y-mirror of complex_b (`…_flipV.world`) reverses curve handedness |

These are analysed with the D-45 "a safe controlled stop = pass" criterion (adverse) or the paired enforcement-vs-monitoring contrast (frontier). GE4-V2 result: SC-PERT-11 enforcement 30/30 vs monitoring 0/30; SC-PERT-13 enforcement 40/40 vs monitoring 0/40 (the cleanest in-ODD measure of the cage's value under compound camera degradation); SC-FRONT-07 passes (generalises to the flipped straights, cage controlled-stops the flipped curve).

### 7.3 Excluded conditions and ODD-exit assumptions

Inherit from §6.7 / §6.8 the curvature-dependent conditions and from §5.6 / §5.7 the adverse-perception conditions. Conflicts are resolved conservatively; any explicit relaxation is documented here as a numbered exception (none at present).

---

## 8. Physical + Isaac sim-to-real ODD (forward reference)

<!--
TEACHER NOTE: This section declares the domains that exist beyond the Gazebo verdict.
It is intentionally forward-looking. Its job is to show that (a) a physical ODD will
exist as a refinement of ODD-1/ODD-3 for the hardware, (b) the Isaac sim-to-real
bridge is a separate simulator whose checkpoints do not transfer, and (c) the F1
hazards/SRs are written abstractly enough to apply across all of them.
-->

### 8.1 Physical-deployment ODD (F5)

A physical operational design domain, provisionally `ODD-PHYS-1`, will be specified in F5 to characterise the physical CobraFlex 1:14 platform and its operating environment. `ODD-PHYS-1` is the closest hardware-realisable analogue of ODD-1 (and, geometry permitting, ODD-3), sharing scenery type, exclusions and exit assumptions, while differing in the subject-vehicle dynamic envelope, the sensor/actuation interfaces, and the nominal control latency. The physical platform is **differential/skid-steer** (four fixed wheels, no Ackermann steering angle), which the sim DiffDrive plugin already mirrors. The single genuinely-unmeasurable-in-simulation parameter, `ODD-3.A_LAT_MAX` (TBD-Q10), closes here via the M-4 lateral-accel calibration. The F1 Hazard Register and SRS are written to hold under both the simulated and physical ODDs, with values that may be re-tuned for `ODD-PHYS-1` when measured (each re-tuning logged here).

**First measured platform data — logged 2026-08-17, no `ODD-N.<PARAM>` changed.** The platform team supplied a bench characterisation of the physical car (*CobraFlex 1:14 Parameters_0813*, 13.08.2026). It is the first hardware evidence to reach this document and it seeds — but does not yet constitute — `ODD-PHYS-1`:

| Quantity | Measured | Bearing on the simulated ODD |
| --- | --- | --- |
| Total mass | **3.5 kg** | The URDF budget summed to 6.59 kg (**1.88× too heavy**) through every frozen campaign; corrected 17.08.2026. An itemised bill of materials supplied the same day (three weighed PLA shells 91.3/118.5/68.0 g + powerbank 550 g + lidar 190 g + ZED 60 g + Jetson 175 g) locates the **entire 3.09 kg overshoot in the single `chassis_mass` placeholder** — `body_link`, `lidar_link` and the wheels were already right. Gazebo's DiffDrive is a kinematic velocity controller, so the effect on the frozen verdicts is second-order (traction/slip only); for Isaac, which is dynamics-based, it is first-order. **2.25 kg (64 %) — the rolling chassis — is still a derived remainder, never weighed.** |
| Track / wheelbase / wheel radius | **0.153 / 0.154 / 0.03725 m** | Track and radius confirm the sim geometry. Two provenance errors surfaced: the plugin's `wheel_separation` 0.154 is the *wheelbase*, not the track (0.65 %, deliberately not corrected); and the URDF's **wheelbase is 0.120 m against 0.154 m measured — 22 % short**. Gazebo's DiffDrive is kinematic and ignores wheelbase, so no simulated result is affected; **Isaac is**, because a short wheelbase under-models the very scrub that causes the yaw deficit. Both in docs/14 §2.3. |
| Linear / angular acceleration | **±2.5 m/s² / 3.2 rad/s²**, max wheel torque **20 N·m** | **Refutes a value the specification had been citing as measured.** `robot.gazebo`, docs/09, docs/13, docs/14, `cage_bridge.py` and D-50 all quoted **0.53 m/s²** as the platform's measured max linear acceleration; the platform repo's own parameter document diagnoses it as the chassis's max *velocity* in m/s copied into an acceleration field. All citations corrected 17.08.2026. **Every conclusion survives with a larger margin** — C-06 bounds commanded acceleration to 0.22 m/s² at the 0.22 m/s trunk cap and 0.5 m/s² on the Isaac contract, both far inside 2.5. The replacement has no stated measurement provenance either, so **M-3 (deceleration, `a_min` = 0.3 `[provisional]`) is informed, not closed**; `cage.yaml` is unchanged. |
| Straight-line tracking | **≈0.99** of commanded, to 0.53 m/s | The forward axis transfers essentially 1:1. `ODD-1.V_MAX = 0.5 m/s` is 94 % of the platform's 0.53 m/s ceiling, so the actuator is a de-facto second limiter at the straight cap; `ODD-3.V_MAX_CURVE = 0.25` is comfortably reachable, i.e. **C-04 is physically exercisable on hardware** even though the 0.22 m/s trunk never fires it in sim. |
| **Yaw-rate tracking** | **0.4954 × commanded** | **The one genuine contradiction.** Gazebo's DiffDrive delivers ~1:1, so the simulated plant is **2× optimistic in rotation**. Every cage margin expressed through steering — C-01/C-02/C-03 corrections and C-06's slew bound — buys **half** the physical yaw it buys in sim. Quantified in docs/14 §2.3a and docs/17 §2 item 4; carried as transfer risk **T2**. Compensated at deployment by `steering_to_yaw_rate_gain 0.8 → 1.615`, *not* by re-valuing any ODD parameter. |
| Lateral acceleration | **not measured** | **TBD-Q10 / `ODD-3.A_LAT_MAX` stays OPEN.** This characterisation does not include the M-4 lateral-accel envelope, so the sole remaining TBD is untouched and this document stays below v1.0. |

Two supplied quantities are **not** evidence and are recorded here so they are not mistaken for it. The inertia tensor `Ixx/Iyy/Izz = 0.008542 / 0.023160 / 0.028702` reproduces this repo's own URDF chassis box at the *old* 5.0 kg to nine decimals — it is our assumption read back out of Isaac, and it contradicted the 3.5 kg measured beside it. The `0.53 m/s` / `6.0 rad/s` maxima are the serial driver's clamp constants (docs/17 §2 item 3); the 6.0 rad/s figure is in fact **unreachable** (ideal `2·v_max/T = 6.93 rad/s`, ≈3.4 rad/s after the measured scrub). The supplied centre of gravity `(0.006, −0.004, 0.030) m` is frame-ambiguous and, read in `base_link`, geometrically unreachable by the current link layout — it was **not** applied. The bill of materials makes this conclusive: 740 g (21 % of the car) sits in the upper two body shells (powerbank 550 g in the centre, lidar 190 g on the top cover), putting the itemised composite at **0.0566 m** above `base_link` versus the claimed 0.030 m. Reading the figure from the **chassis box centre** instead lands at 0.060 m — 3.4 mm from the model — which is the working hypothesis pending confirmation from the platform team (docs/14 §2.2).

### 8.2 Isaac Sim sim-to-real bridge (posterior track, docs/13–14)

With G4 closed, the **Isaac Sim** sim-to-real bridge (D-44) is a *posterior* track, **not** a re-opening of the Gazebo E verdict. It comprises URDF→USD import, ROS2 bring-up, in-process PPO training/evaluation (docs/13), the handover contract (docs/14), and the **2-D action (steering + throttle)** (D-49/D-50). The implemented Isaac training environment adds **multi-circuit per-episode sampling** across a CV-safe trio (`complex_b`, `complex_d`, `complex_e`; D-50/D-51), each designed against the §6.2 monocular curvature boundary.

Three ODD-relevant facts follow. First, **Isaac is a different simulator**: Gazebo checkpoints do not transfer, and its completed/repeated retrains are new baselines, never re-runs of the 297k E-main; they do not reopen G4. Second, Isaac's 2-D action uses `max_speed_mps = 0.5`, whereas the **posterior Gazebo 2-D** PPO/SAC configs currently cap policy authority at **0.25 m/s** (with a 0.22 m/s diagnostic probe). Third, both posterior paths make longitudinal arbitration measurable, but only within their own simulator/config contracts. Cross-simulator comparison therefore requires a fresh, explicitly matched evaluation; none of this changes an `ODD-N.<PARAM>` value or the frozen GE4 verdict.

---

## 9. Master parameter table

<!--
TEACHER NOTE: This is the table cited by the SRS, the Cage Spec, the Scenario Library,
and cage.yaml. Every numerical value mentioned elsewhere in this document appears here,
one row per parameter ID. When a value changes, update it once here and propagate via
the ID. The "track-'E' realisation" reading is complex_b; oval values are the frozen
F-track legacy noted in Source.
-->

The table is the canonical **track-'E' GE4 realisation**. In particular,
`*.ACT_DIM = 1` is a realised verdict parameter, not a claim that the posterior
2-D configs changed an ODD parameter. The curvature-dependent speed limits are
envelope bounds; their end-to-end 2-D face is reported as a coverage gap and
posterior experiment, not back-propagated into this table.

| Parameter ID | Quantity | ODD-1 | ODD-2 | ODD-3 | ODD-4 | Source |
| ------------ | -------- | ----- | ----- | ----- | ----- | ------ |
| `*.LANE_WIDTH` | Lane width (m) | 0.245 | 0.245 | 0.245 | 0.245 | Centerline configs (`complex_b_centerline.yaml`) |
| `*.ROAD_WIDTH` | Total road width (m) | 0.52 | 0.52 | 0.52 | 0.52 | complex_b configs (oval legacy 0.50) |
| `*.ROAD_LENGTH` | Loop / segment length (m) | straight portion | straight portion | 19.22 (centre) / 19.93 (driven) | 19.22 / 19.93 | complex_b perimeter (oval legacy ≈ 8.79) |
| `*.GRADIENT` | Road gradient | 0 | 0 | 0 | 0 | Map convention |
| `*.FRICTION` | Surface friction coeff. | 1.0 | 1.0 | 1.0 | 1.0 | Gazebo ODE default (empty `<friction>`); TBD-Q1 |
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
| `*.ACT_DIM` | **GE4-realised** action vector dimension | 1 | 1 | 1 | 1 | Steering-only verdict parameter (D-49). Posterior Gazebo and Isaac configs set 2 locally (D-50/D-59/D-60) without changing this ODD value |

---

## 10. Traceability hooks

This document is the upstream source for the downstream artefacts. The **Hazard Register** cites it in the *consequence* and *root cause* of every hazard depending on a domain attribute — the geometry/dynamics hazards H-01/H-02/H-03/H-06/H-07 and the **camera-perception hazards H-10/H-11/H-12** (track 'E'). The **SRS** cites parameter IDs in the *parameters* / *rationale* of every SR fixing a numerical threshold — SR-001/002/003/004/006/007 and the camera SRs **SR-012/SR-013/SR-014**. The **Cage Specification** and `cage.yaml` cite this document in the *observed variables* and *trigger thresholds* of each rule (e.g. C-01 `d_max = ODD-1.ROAD_WIDTH/2 − Δ = 0.16 m`, C-04 `v_max` from `ODD-1.V_MAX` / `ODD-3.KAPPA_MAX`, C-05 Trigger 3 `staleness` from `ODD-1.STALENESS_MAX`). The **Scenario Library** cites the named profile IDs (§5.5) as scenario classes. The **Traceability Matrix** cross-references an `ODD-N.<PARAM>` identifier when a parameter participates in a hazard-requirement-cage-scenario chain. `tools/check_traceability.py` must pass before any Gate.

---

## 11. Open issues and TBDs

<!--
TEACHER NOTE: Each TBD-Qx appears here exactly once with a question, owner and target
close. Resolved items keep their closed value with the resolving evidence. Do NOT
delete a TBD silently; close it with an explicit value. Do NOT run tools/close_odd_tbds.py
— its blanket TBD-QN substitution would clobber the closed-TBD prose in §0.1 and the
§9 source column (0.5 change-log note); close by hand.
-->

| Tag | Question | Owner | Target close | Resolution |
| --- | -------- | ----- | ------------ | ---------- |
| TBD-Q1 | Friction coefficient of the road surface? | SS | closed | **1.0** — world SDFs ship an empty `<surface><friction>` block; Gazebo ODE defaults `mu1=mu2=1.0`. Inferred, not explicit `<mu>`; re-read if a future world sets one. (2026-05-14) |
| TBD-Q2 | Max commanded lateral accel., ODD-1? | SS | closed | **9.81** — Coulomb ceiling FRICTION×g. Physical envelope, not a typical value (operational `a_lat ≈ 0` at κ=0). (2026-05-14) |
| TBD-Q3 | Numerical drivable-corridor edge; why differ from LANE_EDGE? | SS | closed | **0.1225** — the env terminates at `\|ey\| > lane_width/2`; CORRIDOR_EDGE = LANE_EDGE, no separate margin. (Track 'E' adds off-road-by-road-centre-distance vs ROAD_EDGE = 0.26 for self-approaching loops, docs/11 §3.5.) (2026-05-14) |
| TBD-Q4 | Lighting-degradation + noise in the nominal-adverse profile? | SS | closed | Superseded on track 'E' by the **camera visual-degradation stressors** (§5.5): glare/low-light/motion-blur (H-10), levels grounded in the GE2 oracle. F-track legacy value in `adverse_profiles.yaml`. (2026-06-03; retargeted 2026-07-07) |
| TBD-Q5 | Latency / jitter / actuation-imperfection profile? | SS | closed | Superseded on track 'E' — the perception channel, not state-vector latency, is the ODD-2 axis; F-track legacy `odd2_adverse_with_latency` retained historically. (2026-06-03; retargeted 2026-07-07) |
| TBD-Q6 | Obstacle geometry / position / quantity? | SS | closed (retired) | **Retired** — no obstacle observation channel; no obstacle scenario in the verdict library. The F4 spec-only box profile is withdrawn. (2026-07-07) |
| TBD-Q7 | Full parameterisation of the adverse-full profile? | SS | closed | On track 'E' = the union/compound of the §5.5 camera stressors (e.g. SC-PERT-13 = worn markings **+** glare). (2026-06-03; retargeted 2026-07-07) |
| TBD-Q8 | Total loop length of the curvy world? | SS | closed | **complex_b: 19.22 m (centre) / 19.93 m (driven)**, from `complex_b_centerline.yaml` (`perimeter_m`). Oval legacy ≈ 8.0232 m (centre) / 8.79 m (driven). (2026-05-21; retargeted 2026-07-07) |
| TBD-Q9 | Minimum curvature radius / KAPPA_MAX? | SS | closed | **complex_b: R_min ≈ 0.876 m (centre) / 0.998 m (driven) → KAPPA_MAX ≈ 1.14 m⁻¹ (centre) / 1.00 (driven)**; shaped to the §6.2 monocular boundary. Oval legacy R_min 0.80 → 1.25 m⁻¹. (2026-05-21; retargeted 2026-07-07) |
| TBD-Q10 | Max commanded lateral accel., ODD-3, from FRICTION + V_MAX_CURVE? | SS | **M-4 (F5)** | **OPEN — and deliberately still open after the last pre-deployment campaign (31.07.2026).** Coulomb upper bound `A_LAT_MAX ≤ FRICTION×g = 9.81 m/s²`; operational value at V_MAX_CURVE=0.25 on driven R_min≈1.0 m is `V²/R ≈ 0.063 m/s²` — well below. The 2-D verdict-of-record campaign ran at ≈0.216 m/s (`a_lat ≈ 0.047 m/s²`), so it neither approaches nor could bound the envelope: in Gazebo `A_LAT_MAX` is a *property of the friction model that was assumed*, so measuring it there would return the assumption. Final figure closes when **M-4** measures the physical achievable envelope. **Unmeasurable in simulation by construction** (D-33) — this is a hardware dependency, not an outstanding action item. |
| TBD-Q11 | Stuck-criterion timeout? | SS | closed | **n/a** — no separate stuck monitor; env truncation `max_episode_steps × control_dt = 500 × 0.10 s = 50 s` is the implicit timeout. (2026-05-21, F3 update 2026-06-01) |
| TBD-Q12 | Do ODD-4 profiles add any stressor beyond ODD-2? | SS | closed | **No** — ODD-4 = ODD-3 geometry × ODD-2 perception stressors (§7.1), realised as curve-traversing complex_b scenarios (SC-PERT-11/12/13, SC-FRONT-07). (2026-06-03; retargeted 2026-07-07) |

---

## 12. Verdict realisation on `complex_b` (track-'E' reconciliation)

<!--
Append-only reconciliation (numerical authority flows spec → evidence, never the
reverse). This section changes NO ODD parameter; it records which sub-region of the
ODD-1..ODD-4 stratification the track-'E' GE4-V2 campaign actually exercises, and
declares the coverage gaps. Supersedes the v0.6 §12 (F4 single-oval, D-37).
-->

The four ODDs are specified abstractly. Two campaigns realise them on the **single `complex_b` world**, over the `scenarios_complex_b/` library, and they differ in exactly one axis — the action space:

- **GE4-V2** (the frozen G4 gate record): **28 scenarios × {enforcement, monitoring}, 1970 runs, seed 2024, 0 errors** (`experiments/sim/campaign_e_v2/campaign_report.json`), at **one operating point** — fixed forward speed **0.20 m/s**, **steering-only** action (`ACT_DIM = 1`, D-49).
- **2-D PPO 550k** (the verdict of record since 31.07.2026, D-69): **27 scenarios × {enforcement, monitoring}, 1890 runs, seed 2024, 0 errors** (`experiments/sim/campaign_2d_ppo550k/campaign_report.json`) — **`ACT_DIM = 2`** (steering + throttle) under the **0.22 m/s** cap, i.e. the first verdict-bearing campaign in which the policy holds speed authority and the ODD-3 speed envelope is exercised rather than structurally bypassed. SC-PERT-03 is absent by protocol (D-64).

Both share an **84×84×4 camera** policy observation, the cage on its **own CV lane-estimator** (D-43), and a byte-identical cage YAML. `complex_b` contains both straight tiles and scallop curves, so the nominal/adverse-straight vs curvy axis is realised by the **start arc-length** `start_s` rather than by separate worlds. The frozen F-track oval is the ground-truth **baseline** (the control arm), and the pure `straight_road.world` is reserved for the F5 physical subset.

### 12.1 ODD → complex_b realisation

| ODD | Realised on complex_b as | Speed / ACT_DIM | Scenarios | Coverage |
| --- | --- | --- | --- | --- |
| ODD-1 — nominal | straight tile (`start_s ≈ 2.0`) | 0.20 m/s, 1 | SC-NOM-01, SC-EDGE-01..05 | **Covered** — 0 in-ODD road-edge, cage latent |
| ODD-2 — adverse (perception) | straight + camera stressors (§5.5) | 0.20 m/s, 1 | SC-PERT-04..10, 12 | **Covered** — cage removes perception-degradation failures the bare policy commits |
| ODD-3 — nominal curvy | full loop incl. scallop curves | 0.20 m/s, **1** | SC-NOM-02/03 | **Partial** — curve geometry + cage-on-curves yes; 2-D speed envelope no (12.2-b) |
| ODD-4 — adverse curvy | curve-traversing stressor scenarios | 0.20 m/s, 1 | SC-PERT-11/12/13, SC-FRONT-07 | **Covered** (perception × curve); speed-envelope face still 1-D (12.2-b) |
| Beyond ODD | out-of-ODD lateral/heading/geometry starts | 0.20 m/s, 1 | SC-FRONT-01..07 | Cage-efficacy contrast (D-35) — paired, not folded into the verdict |

### 12.2 Declared coverage gaps

- **(a) Nominal-straight length & curvature.** ODD-1's abstract "straight, κ ≡ 0" is realised on complex_b's straight tiles; curvature is zero only within the recovery window before curve entry. The single-rule isolation each straight scenario intends is preserved because the recovery budgets complete within the straight at 0.20 m/s.
- **(b) ODD-3/4 speed-envelope face NOT exercised end-to-end by GE4.** The curvature-dependent `v_max(κ)` design needs throttle authority for a learned-policy test, while the canonical verdict parameter is fixed-speed `ACT_DIM = 1` (D-49). ODD-3 therefore remains **partial in the GE4 claim**. Posterior Gazebo and Isaac 2-D runs exercise longitudinal control under local configs (§12.4), but are not verdict campaigns and do not change `ODD-3.ACT_DIM` or retroactively expand GE4 coverage.
- **(c) Two distinct D-43 confident-estimate residuals.** In SC-EDGE-02 the cage's CV estimator can lock onto a neighbouring lane pair and **under-read lateral offset** (`cv_ey ≈ 0.04 m` while true `ey → 0.30 m`, `cv_ok` True). Scoped to the ODD by ruta 1, this costs **2/30 boundary-edge breaches** in GE4-V2 and SR-001 still closes; the single-frame "read the larger offset" patch (ruta 2b) was reverted after spurious emergencies on centred/curving views (D-48). Separately, the posterior 2-D cap probe exposed a confident **heading over-read** (`cv_epsi`) in a tight curve: lowering 0.25→0.22 m/s did not remove that stop. The probe therefore shows that speed margin cannot repair a confidently wrong estimator, but it does not re-characterise the SC-EDGE-02 `cv_ey` under-read. The honest closure for both is better/temporal perception, not a new action dimension or a single-frame rule.
- **(d) Single operating speed in GE4.** 0.20 m/s is a single conservative operating point, below both `V_MAX = 0.5` and `V_MAX_CURVE = 0.25` — not a speed sweep. This is why the speed rules are structurally latent in the verdict runs; posterior 2-D evidence is reported separately.
- **(e) Multi-seed.** GE4-V2 remains the seed-2024 verdict. The posterior PPO camera N = 5 study is now complete (3/5 constraint-respecting; seed 666 cage-dependent; seed 23 cage–CV conflict), but was not pooled into the pre-registered GE4 verdict.
- **(f) `ODD-3.A_LAT_MAX` (TBD-Q10).** Unmeasurable in simulation; deferred to the physical M-4 calibration (§12.3).

These gaps are the analogue of the bounded-validation principle (D-11), reported in the manuscript Limitations. They change no ODD parameter, SR threshold, or cage constant; the spec above remains the authoritative definition of the *intended* domain, and the reconciliation records coverage — it does not back-propagate a measured value into a threshold.

### 12.3 Version status at G4 (v1.0 carries Q10 to F5)

The maturation plan targeted **v1.0 "all TBDs resolved, signed off"**. With the F4 and GE4-V2 campaigns closed and **G4 signed off (02.07.2026)**, **11 of 12 TBDs are resolved**; the sole remainder, **TBD-Q10 (`ODD-3.A_LAT_MAX`)**, depends on the physical lateral-accel calibration **M-4** and is by construction unmeasurable in simulation, so it is deferred to F5 (D-33). The ODD-Spec is therefore signed off at G4 and maintained at a minor version with **Q10 explicitly carried to F5**, not promoted to 1.0; 1.0 is reached when M-4 closes Q10 on the physical platform. This is a disclosed limitation, not an open orphan: every *simulation-resolvable* TBD is closed, and Q10's dependency on hardware is recorded here and in D-33.

**Confirmed at the end of simulation work (31.07.2026, v0.9.1, D-69).** The simulation programme is now complete: the last pre-deployment campaign (2-D PPO 550k, 1890 runs) has run and is the verdict of record. The count is unchanged at **11 of 12**, and this is the intended outcome rather than a shortfall — running more simulation could never have moved it, because `A_LAT_MAX` in Gazebo is a consequence of the friction coefficient the world *assumes* (`FRICTION = 1.0`, itself the inferred ODE default of TBD-Q1), so a simulated measurement would return the assumption rather than test it. The document therefore stays below 1.0 **by design** for as long as the platform has not been driven. Everything the simulation side could resolve is resolved, including the two long-standing SR-level TBDs (SR-009/SR-010, closed in `docs/07` on 31.07.2026); what remains is exactly one hardware-gated number and the physical `verdict_phys` column, both explicitly owed to F5 and neither of them silently dropped.

### 12.4 Post-G4 posterior evidence (17–20.07.2026)

This evidence is **diagnostic/posterior**, not a new Gate campaign:

| Evidence family | Action / speed contract | Result relevant to the ODD |
| --- | --- | --- |
| Frozen GE4-V2, PPO 297k | 1-D, fixed 0.20 m/s | Verdict of record; unchanged |
| Gazebo PPO/SAC posterior | 1-D and 2-D; current 2-D cap 0.25 m/s | PPO 2-D reached a competent monitoring baseline; SAC produced full-horizon 2-D enforcement runs after entropy fixing |
| Gazebo 0.22 m/s probe | 2-D eval-time diagnostic cap | Removed the zero-margin speed-conflict stop on the SAC-auto 150k checkpoint; did **not** remove the D-43 heading over-read on the 175k checkpoint |
| Gazebo margin022 qualification | 2-D, fresh bounded 75k parent + 50k continuation inside 150k replay | Preregistered/untrained; runner requires a D-43 PASS for the exact checkpoint/config before Gazebo |
| Gazebo SAC SC-PERT subset | 1-D, seeds 2024 and 42; 200 cells total | Enforcement 100/100 PASS versus monitoring 68/100; subset reports are intentionally `INCOMPLETE` globally and carry no GE4 verdict |
| Isaac posterior | 2-D, 0.5 m/s full authority | Separate simulator and retrained baselines; checkpoints do not transfer |

Thus the ODD-3 speed face is no longer wholly unexercised in the repository, but it remains **outside the GE4 verdict claim**. The 0.22 probe also separates two mechanisms: longitudinal margin can remove a speed-boundary conflict, whereas lowering speed alone does not repair a confidently wrong CV heading estimate.

---
<!--
## 13. Anticipated defense questions

**Q1. The verdict track uses an 84×84 camera image and a 1-D action, but ODD-3/ODD-4 include a curvature-dependent speed envelope — isn't the validated realisation narrower than that envelope?**
Yes, and it is declared (§6.5, §12.2-b). ODD-3 is claimed **partial in GE4**: curve geometry and the cage's lateral behaviour on curves are exercised end-to-end (SC-NOM-02/03, and adversely SC-PERT-11/12/13), but the canonical verdict parameter is fixed-speed `ACT_DIM=1` (D-49). Posterior Gazebo 2-D runs at a 0.25 m/s cap and Isaac 2-D runs at 0.5 m/s exercise speed authority as new baselines under local configs; they do not retroactively expand the GE4 coverage claim or change the ODD parameter table. This is a bounded, declared gap, not a silent one.

**Q2. Why re-specify ODD-2/ODD-4 as camera-perception degradation instead of the earlier sensor-noise-plus-obstacles?**
Because track 'E' is the verdict of record and its stressor axis *is* the perception channel: the same camera feeds the policy CNN and the cage's CV estimator (D-43 common-cause), so glare/low-light/blur (H-10), occlusion (H-11) and false markings (H-12) are the meaningful adverse conditions. The old state-vector noise/latency profiles belonged to the F-track baseline and are retained historically; the obstacle profile never had an observation channel and is retired.

**Q3. `ODD-1.ROAD_WIDTH` changed 0.50 → 0.52 m and `KAPPA_MAX` 1.25 → 1.14 — do those break the cage thresholds that cite them?**
No. `d_max = 0.16 m` (C-01) is unchanged: the margin Δ = ROAD_WIDTH/2 − d_max is simply 0.10 m on complex_b (was 0.09 on the oval), still absorbing the LiDAR noise / one-cycle drift / half-footprint budget. `KAPPA_MAX` loosening from 1.25 to 1.14 relaxes the C-04 curve ceiling conservatively; the cage's C-04 interpolation was calibrated at the tighter oval value and remains `[provisional, M-4]`. The road edge moved 0.25 → 0.26 m consistently with the frontier scenarios' `road_edge_contact` criterion.

**Q4. Several "closed" TBDs are inferred, not measured (FRICTION = 1.0 from an empty ODE block). Is that a real closure?**
TBD-Q1 is closed to the Gazebo ODE default because the world SDFs ship an empty `<friction>` block; the note flags it as inferred and instructs re-reading if a future world sets an explicit `<mu>`. A defensible, surfaced-assumption closure — not a fabricated number. The one genuinely unmeasurable item (Q10) is left open and deferred to M-4.

**Q5. The camera policy observation is an image while the F-track baseline is a 6-vector — which is the "real" ODD-1.OBS_DIM?**
Both, on their own tracks. `ODD-1.OBS_DIM` is a *modality*, not a fixed scalar: track 'E' (verdict of record) observes an 84×84×4 camera tensor and its cage reads a CV lane-estimate (D-43); the F-track baseline observes a 6-D ground-truth vector. The parameter row (§9) records both; the two are the perception-cost comparison the thesis is built to make. The cage rules C-01..C-06, the metrics, and the action are identical across the two, so the comparison is controlled.

**Q6. Why four ODDs and a full PAS 1883 / ISO 34503 taxonomy for a 1:14 lane-follower?**
The stratification (nominal → +perception stressor → +curvature → combined) is exactly what lets an observed safety/performance change be attributed to a *single* axis rather than a confounded mixture — the methodological core of an SE4AI thesis. The taxonomy supplies the standards vocabulary the automotive committee expects, and the `ODD-N.<PARAM>` single-sourcing is what prevents the documentation cycles the document's own notes warn about.

--->

*End of ODD-SPEC v0.8.*
