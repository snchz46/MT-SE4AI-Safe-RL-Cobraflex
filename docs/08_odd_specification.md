# ODD Specification — SE4AI Lane Following Thesis

**Document ID:** `ODD-SPEC`  
**Version:** 0.6 (F4 single-world eval reconciliation §12 + D-37, 08.06.2026; 0.5 = F4-entry TBD closure 03.06.2026; 0.4 = F3 housekeeping)  
**Owner:** Samuel Sánchez  
**Phase of birth:** F0 — Phase of maturity: F1 — Phase of revision: F5 (physical ODD)  
**Status:** DRAFT — 11 of 12 TBDs resolved (Q1–Q3 at F1; Q8, Q9, Q11 at F2 against the oval_R080 preset; Q4–Q7 and Q12 at F4 entry against `src/cobraflex_rl/config/adverse_profiles.yaml`); only Q10 remains, deferred to M-4 (physical lateral-accel calibration) — see decision D-33 in `docs/DECISIONS.md`.  
**Last updated:** 2026-06-08  
**Approving reviewer (Gate 1):** [supervisor name]  

<!--
TEACHER NOTE: This is the cover block. Treat the version as a strict integer-decimal:
0.1 = first complete draft, 0.2…0.9 = revisions during F1, 1.0 = approved at Gate 1.
After Gate 1 the document becomes a versioned living artefact: every subsequent edit
that changes a parameter or a boundary must increment the minor version and be logged
in §0.1 below. The Hazard Register, the SRS and the Cage Spec all cite specific
sections and parameters of this document by ID, so once 1.0 is signed off, do NOT
renumber sections — only append.
-->

## 0.1 Change log

| Version | Date | Author | Summary |
| ------- | ---- | ------ | ------- |
| 0.1 | 2026-05-02 | SS | Initial structural extraction from `draft_V3.docx` §6.1, with TBDs for unresolved quantitative items. |
| 0.2 | 2026-05-14 | SS | F1 partial closure of TBD-Q1 (FRICTION = 1.0), TBD-Q2 (A_LAT_MAX = 9.81 m/s²) and TBD-Q3 (CORRIDOR_EDGE = 0.1225 m), against the `src/cobraflex` + `src/cobraflex_rl` workspace. Remaining 9 TBDs deferred per decision D-33: Q4–Q7 and Q12 to F4 (scenario library), Q8–Q11 to F2/F3 (ODD-3 curvy world implementation). Simulator label "MuJoCo" replaced by "Gazebo" throughout. |
| 0.3 | 2026-05-21 | SS | F2 closure of TBD-Q8 (ROAD_LENGTH = 8.0232 m, perimeter of the oval_R080 preset), TBD-Q9 (KAPPA_MAX = 1.25 m⁻¹ = 1 / R_min with R_min = 0.80 m on the two U-turns) and TBD-Q11 (STUCK_TIMEOUT = n/a — subsumed by `max_episode_steps × control_dt = 40 s` truncation in `gazebo_lane_env.py`; no separate stuck check is configured). Geometry source of truth: `scripts/compose_lane_circuit.py` preset `oval_R080`, which emits both `src/cobraflex/worlds/lane_following_oval.world` and `src/cobraflex_rl/config/oval_centerline.yaml`. TBD-Q10 (A_LAT_MAX ODD-3) remains deferred to the M-4 calibration measurement, which depends on the physical platform. |
| 0.4 | 2026-06-01 | SS | F3 housekeeping: `max_episode_steps` raised 400→500 in the training env (`train_ppo.yaml`, Training Spec §7.2.4), so the truncation window that subsumes `*.STUCK_TIMEOUT` (TBD-Q11) is now `500 × 0.10 s = 50 s` (was 40 s). The TBD-Q11 closure itself is unchanged (n/a, subsumed by env truncation); only the illustrative figure was realigned. No ODD parameter value changed. |
| 0.5 | 2026-06-03 | SS | F4-entry closure of TBD-Q4–Q7 (ODD-2 adverse stressor profiles) and TBD-Q12 (ODD-4 adds no stressor beyond ODD-2). `odd2_nominal_adverse` σ_lateral=0.03 m + faded/non-uniform world; `odd2_adverse_with_latency` +100 ms latency / 20 ms jitter / 0.02 steer-noise; `odd2_adverse_with_obstacle` 0.10 m box, ~0.05 m intrusion (**spec only — execution deferred**, no obstacle channel in the 6-dim obs); `odd2_adverse_full` = union. Source of truth: `src/cobraflex_rl/config/adverse_profiles.yaml` (§5.5 mirrors it). Closed **by hand**, not via `close_odd_tbds.py`, whose blanket `TBD-QN` substitution would clobber the prose mentions of already-closed TBDs in §0.1 and the §9 source column. Only Q10 (A_LAT_MAX ODD-3) remains, deferred to M-4. |
| 0.6 | 2026-06-08 | SS | F4 single-world evaluation reconciliation. New §12 records that the F4 simulation campaign realises ODD-1..ODD-4 on the **single oval world** `lane_following_oval.world` at one fixed-speed `ACT_DIM=1` operating point (0.2 m/s, 6-dim obs), per *Option A* of the `docs/05` Track-mapping note. ODD-1/ODD-2 claimed covered; ODD-3 partial (curve geometry exercised, 2-dim speed envelope not); ODD-4 not exercised (no adverse-curvy scenario). Coverage gaps declared §12.2. **No ODD parameter changed.** Decision D-37. |

---

## 1. Purpose and scope

This document specifies the four Operational Design Domains (ODD-1 to ODD-4) within which the lane-following controller of this thesis is intended to function. Each ODD is defined as a specific combination of scenery, environmental conditions, dynamic elements, subject-vehicle dynamics envelope, and sensor and actuation interfaces. The ODDs are organised so that each one isolates a methodologically meaningful axis of variation. ODD-1 is the nominal straight-road baseline; ODD-2 adds adverse stressors on the same straight geometry; ODD-3 introduces curvy closed-loop geometry under nominal conditions; ODD-4 combines curvy geometry with adverse conditions. This stratification makes it possible to attribute observed safety or performance changes to a specific axis of complexity rather than to a confounded combination.

This document is the source of truth for every parameter that is later cited as a threshold in the Safety Requirements Specification (SRS), as a scenario boundary in the Scenario Library, or as a configuration constant in the Cage Specification. It is not a description of the simulator implementation (see Chapter 7, Pragmatic Aspects) nor of the safety analyses themselves (see Hazard Register and SRS). It is the boundary condition from which those artefacts derive their numerical content.

<!--
TEACHER NOTE: When a reviewer asks "why does SR-001 use d_max = 0.16 m and not 0.18 m?",
the answer must trace back to a parameter that lives in this document. If the answer
"lives in the SR rationale" but not here, you have created a documentation cycle
that will eventually break. Always push numerical authority upstream to this file.
-->

---

## 2. ODD formulation method

The four ODDs are formulated using a hierarchical taxonomy adapted from PAS 1883 (BSI 2020) and ISO 34503 (ISO 2023), expressed with the semantic discipline encouraged by ASAM OpenODD 1.0.0 (ASAM 2021). Each ODD is described in five steps. First, the intended function and subject-vehicle assumptions are stated. Second, the scenery is described, comprising drivable-area type, geometry, lane specification, edge and surface characteristics, and the presence or absence of structures. Third, the environmental conditions are specified, comprising illumination, weather, particulates, and connectivity. Fourth, the dynamic elements are specified, comprising other actors and their permitted states. Fifth, the subject-vehicle dynamic envelope and the sensor and actuation interfaces are specified, comprising the dynamic ranges of the subject vehicle and the assumed properties of the sensors and actuators. Each ODD then closes with explicit excluded conditions and ODD-exit assumptions.

A methodological distinction between ODD attributes and implementation-side stressors is preserved throughout. Internal noise, latency, and actuation imperfections are treated as scenario-side experimental perturbations, layered on top of the ODD as named scenario profiles, rather than as ODD attributes themselves. This distinction is what makes ODD-2 and ODD-4 meaningful as stressor-bearing extensions of ODD-1 and ODD-3 instead of independent operational domains. The named scenario profiles for ODD-2 and ODD-4 are documented within this specification because their parameters are cited from SRs and cage rules, but their broader test purposes belong to the Scenario Library.

---

## 3. Identifier conventions

This document distinguishes three classes of identifier. Domain identifiers of the form `ODD-N`, where N runs from 1 to 4, refer to the abstract operational design domain and are the identifiers used in cross-references from the SRS, the Hazard Register, and the Cage Specification. Map identifiers of the form `oddN_<descriptor>`, such as `odd1_straight_road` or `odd3_curvy_loop`, refer to the concrete simulator map files, expressed in lowercase snake_case for software-side use. Scenario profile identifiers of the form `oddN_<scenario_name>`, such as `odd2_adverse_with_latency`, refer to specific stressor configurations layered on top of a map; these names match the ones used in the Scenario Library.

Numerical parameters declared in this document use a stable identifier of the form `ODD-N.<PARAM>` (for example, `ODD-1.LANE_WIDTH`, `ODD-3.KAPPA_MAX`). These identifiers are how the SRS, the Hazard Register, and the Cage Specification cite the values without copying them, ensuring single sourcing.

---

## 4. ODD-1 — Nominal straight-road baseline

### 4.1 Intended function and subject-vehicle assumptions

The intended function is lane following on a structured straight-road segment. The subject vehicle is the simulated CobraFlex-like platform of the Gazebo environment (URDF + SDF, ROS2 Humble, packaged as `src/cobraflex`), operating at low forward speed with a single steering degree of freedom controlled by the policy. ODD-1 is the reference point against which all other domains are differentially defined; it is intentionally the narrowest of the four to support interpretable PPO training, reproducible debugging, and unambiguous scenario derivation.

### 4.2 Scenery

The drivable area is a two-lane straight segment of uniform asphalt-like surface, with clearly visible lateral lane boundaries, a dashed central lane separator, flat geometry, and no junctions, special structures, or temporary road structures. Total road width is `0.50 m`, lane width per direction is `0.245 m`, and total road length is `10 m`. The road gradient is zero. The friction coefficient of the simulated surface is `1.0` (must be read from the Gazebo SDF `<surface><friction>` block of the road geom in `src/cobraflex/worlds/odd1_straight_road.world` — or in the world that `odd1_straight_road` resolves to in your launch configuration; for example, `empty.world` / `obstacles.world` / `test_world.sdf` currently shipped under `src/cobraflex/worlds/`).

### 4.3 Environmental conditions

ODD-1 assumes dry conditions, absence of fog, snow, rain, flooding, and atmospheric particulates, and nominal uniform illumination across the entire drivable area. Connectivity is not required for the simulator implementation. There are no spatially varying lighting effects, shadows, or reflectivity discontinuities.

### 4.4 Dynamic elements

No surrounding traffic, pedestrians, cyclists, animals, or moving obstacles are present in ODD-1. The only dynamic element is the subject vehicle itself.

### 4.5 Subject-vehicle dynamic envelope

<!--
TEACHER NOTE: This is one of the sections the audit flagged as weak in the draft.
Every quantity here will eventually appear in an SR rationale (especially in
SR-003 for TTLC, SR-004 for v_max, SR-006 for actuator smoothness). Be precise.
-->

The forward speed range under nominal operation is `[0, ODD-1.V_MAX]` with `ODD-1.V_MAX = 0.5 m/s` (consistent with SR-004 on straight sections). The local path curvature is `κ ≡ 0` everywhere within ODD-1 (straight road). The lateral acceleration that the policy is expected to command is bounded by `ODD-1.A_LAT_MAX = 9.81` (must be derived from the friction coefficient and the velocity envelope). The control cycle nominal period is `ODD-1.T_CTRL = 50 ms` (20 Hz). The end-to-end nominal control latency between observation and applied command is assumed to be no greater than `ODD-1.LATENCY_NOMINAL = 50 ms` (this number is also referenced by SR-001 in the rationale of `d_max`).

### 4.6 Sensor and actuation interfaces

The agent does not receive raw camera or LiDAR data. Instead, it receives a 5-dimensional state vector composed of lateral error, heading error, current speed, current steering value, and previously issued steering action. The action space in ODD-1 is one-dimensional and continuous, corresponding to the steering command only. The throttle is set to a constant nominal value within `[0, ODD-1.V_MAX]` and is not a controlled variable in this domain.

A sensor reading is considered nominal when its timestamp is no older than `ODD-1.STALENESS_MAX = 200 ms` and all of its fields lie within their physically plausible ranges (see §9 master parameter table). Violations of this nominal sensor condition are not part of ODD-1 itself but trigger Hazard H-06 and Safety Requirement SR-007.

### 4.7 Excluded conditions

ODD-1 explicitly excludes any non-zero curvature, any deviation from uniform illumination, any presence of dynamic or static obstacles, any precipitation or particulates, any sensor degradation, and any forward speed exceeding `ODD-1.V_MAX`. Operation under any of these conditions is, by definition, outside ODD-1; it does not necessarily violate the SRs, but it does mean that the corresponding evidence belongs to a different domain.

### 4.8 ODD-exit assumptions

The system is considered to be exiting ODD-1 when the absolute lateral offset of the vehicle exceeds `0.1225 m` (the geometric edge of the lane, equal to lane width over two), when the forward speed exceeds `ODD-1.V_MAX`, when the simulator reports a contact event with the road edge, or when an episode termination condition fires. The policy is not designed to recover the system once it has exited ODD-1; recovery, if attempted at all, is the responsibility of the cage in emergency mode, governed by Cage Rule C-05 and Safety Requirements SR-005, SR-007, SR-008.

The "drivable corridor" boundary used by the simulator's episode-termination logic is `0.1225`. This must be reconciled with the geometric lane edge above; if the two differ, the rationale for the difference must be documented here.

### 4.9 Parameter summary for ODD-1

See §9 master parameter table for the consolidated tabular form. The parameters declared in this section are: `ODD-1.LANE_WIDTH`, `ODD-1.ROAD_WIDTH`, `ODD-1.ROAD_LENGTH`, `ODD-1.GRADIENT`, `ODD-1.FRICTION` (1.0), `ODD-1.V_MAX`, `ODD-1.KAPPA_MAX`, `ODD-1.A_LAT_MAX` (9.81), `ODD-1.T_CTRL`, `ODD-1.LATENCY_NOMINAL`, `ODD-1.STALENESS_MAX`, `ODD-1.LANE_EDGE`, `ODD-1.CORRIDOR_EDGE` (0.1225).

---

## 5. ODD-2 — Adverse straight-road validation

### 5.1 Relation to ODD-1

ODD-2 preserves the scenery, dimensions, gradient, and friction of ODD-1 unchanged. It differs from ODD-1 only in two respects: the environmental conditions are no longer guaranteed to be nominal, and named scenario profiles introduce explicit stressors on the sensor and actuation paths. The subject-vehicle dynamic envelope, the control cycle, and the action space are inherited from ODD-1 unchanged. The observation space is extended from 5 dimensions to 8 dimensions to include obstacle-forward distance, obstacle-lateral offset, and an obstacle-detected flag, since ODD-2 admits the optional presence of static obstacles.

### 5.2 Environmental conditions

Lane markings may be partially degraded or faded along arbitrary segments. Illumination is permitted to be non-uniform, including the presence of shadow regions over portions of the drivable area. Weather, particulates, and gradient conditions remain as in ODD-1. The full quantitative parameterisation of degradation severity is given by the named scenario profiles in §5.5.

### 5.3 Dynamic elements

ODD-2 admits the optional presence of static obstacles on the road, either fully outside the lane (clutter), partially intruding into the lane, or fully blocking the lane. No moving traffic, pedestrians, cyclists, or animals are admitted. The number, position, and dimensions of admitted obstacles are specified by the named scenario profiles in §5.5.

### 5.4 Sensor and actuation interfaces

Beyond the obstacle-related extension of the observation space declared in §5.1, ODD-2 admits explicit perturbations of the sensor and actuation paths through scenario stressors: observation noise added to the state vector, observation latency exceeding `ODD-1.LATENCY_NOMINAL`, observation jitter, and small actuation imperfections. The numerical parameters of these perturbations are not free; they are fixed within each named scenario profile. The relationship between these stressors and Hazard H-06 (operation under unobservable or corrupt state) is direct: the stressors are the controlled means by which H-06 conditions are exercised in evaluation.

### 5.5 Named scenario profiles

Stressor parameters are maintained as the single source of truth in
[`src/cobraflex_rl/config/adverse_profiles.yaml`](../src/cobraflex_rl/config/adverse_profiles.yaml);
the table below mirrors it. "Latency (ms)" is the *total* observation latency
(nominal `*.LATENCY_NOMINAL = 50 ms` plus any injected excess). Closes TBD-Q4–Q7
(D-33, F4 entry).

| Profile ID                  | Lighting / markings                | Obstacle config                                                                | Sensor noise (σ_lateral) | Latency (ms)   | Jitter (ms) | Actuation imperfection |
|-----------------------------|------------------------------------|--------------------------------------------------------------------------------|--------------------------|----------------|-------------|------------------------|
| `odd2_nominal_adverse`      | Faded markings + non-uniform light | None                                                                           | 0.03 m                   | 50 (nominal)   | 0           | None                   |
| `odd2_adverse_with_latency` | Nominal markings + nominal light   | None                                                                           | 0 (nominal)              | 150 (50 + 100) | 20          | Steering noise 0.02    |
| `odd2_adverse_with_obstacle`| Nominal                            | 1 static box 0.10×0.10×0.10 m, qty 1, ~0.05 m lane intrusion at mid-straight † | 0 (nominal)              | 50 (nominal)   | 0           | None                   |
| `odd2_adverse_full`         | Faded markings + non-uniform light | as `odd2_adverse_with_obstacle` †                                              | 0.03 m                   | 150 (50 + 100) | 20          | Steering noise 0.02    |

† **Obstacle profiles are specified but execution-deferred for F4:** the F3 policy
observation is 6-dimensional with no obstacle channel, whereas §5.1 specifies an
8-dimensional ODD-2 observation (obstacle-forward distance, obstacle-lateral
offset, obstacle-detected flag). The F4 campaign runner skips profiles marked
`execution: deferred` in `adverse_profiles.yaml` until obstacle perception is
wired and the policy retrained (TBD-Q6 / TBD-Q7 closure rationale; D-33).

### 5.6 Excluded conditions

ODD-2 retains all exclusions from ODD-1 that are not explicitly relaxed above. In particular, dynamic agents, intersections, route-planning demands, gradient changes, weather effects beyond illumination, and curvature remain excluded.

### 5.7 ODD-exit assumptions

The same exit conditions as ODD-1 apply. Additionally, ODD-2 considers the system to be exiting the domain if any obstacle is contacted by the subject vehicle, whether the obstacle was inside or partially intruding the lane.

---

## 6. ODD-3 — Nominal curvy-loop domain

### 6.1 Relation to ODD-1

ODD-3 preserves the environmental conditions and the dynamic-element exclusions of ODD-1 unchanged, and differs from it in three respects: the scenery is a closed loop with curvature, the action space is two-dimensional (steering and speed) rather than one-dimensional, and the subject-vehicle dynamic envelope must accommodate non-zero lateral acceleration.

### 6.2 Scenery

The drivable area is a structured two-lane closed loop. The F2-closing implementation (`scripts/compose_lane_circuit.py` preset `oval_R080`) is an oval composed of two 1.5 m straight tiles connected by two 180° U-turn tiles of centreline radius 0.80 m, drawn from the modular `road_assets/road_curves/` library and a procedurally-generated straight tile at exactly the requested length. The total loop length is `ODD-3.ROAD_LENGTH = 8.0232 m` (sum of `2 × 1.5 m` straights + `2 × π × 0.80 m` arcs) and the minimum curvature radius is `R_min = 0.80 m`, giving `ODD-3.KAPPA_MAX = 1 / R_min = 1.25 m⁻¹` (this last parameter, the most consequential physical constant of this domain, is referenced by SR-004 and Cage Rule C-04). Lane width, road width, and surface friction are inherited from ODD-1 unless otherwise stated. Future ODD-3 worlds may add intermediate curvatures by extending the composer preset list (`oval_R050`, `oval_R120` for tighter / gentler curves are already supported); each additional preset increments `ROAD_LENGTH` and re-derives `KAPPA_MAX` from its own `R_min`.

### 6.3 Environmental conditions

Identical to ODD-1: dry, no fog or snow, nominal uniform illumination, no spatial variation in lighting.

### 6.4 Dynamic elements

Identical to ODD-1: no other actors, only the subject vehicle.

### 6.5 Subject-vehicle dynamic envelope

The forward-speed envelope becomes curvature-dependent. The straight-section speed cap is `ODD-3.V_MAX_STRAIGHT = 0.5 m/s` (inherited from ODD-1.V_MAX). The curve-section speed cap is `ODD-3.V_MAX_CURVE = 0.25 m/s`. The interpolation between the two is governed by `v_max(κ) = max(ODD-3.V_MAX_CURVE, ODD-3.V_MAX_STRAIGHT − k_κ |κ|)` with `k_κ = 0.3 m/s per unit curvature` (these values are mirrored in SR-004 and originally derive from the kinematic envelope of the simulated platform). The maximum lateral acceleration commanded is bounded by `ODD-3.A_LAT_MAX = TBD-Q10`, derivable once the friction coefficient and `R_min` are confirmed.

### 6.6 Sensor and actuation interfaces

The observation vector is the same 5-dimensional vector as ODD-1. The action space is two-dimensional and continuous, comprising a steering command and a speed command. Control cycle period and nominal latency are inherited from ODD-1.

### 6.7 Excluded conditions

ODD-3 retains all environmental and actor exclusions from ODD-1. Curvatures larger than `ODD-3.KAPPA_MAX` are out of scope, as are speeds above `v_max(κ)` evaluated at the current local curvature.

### 6.8 ODD-exit assumptions

Inherits the lateral-offset and contact criteria from ODD-1 with the lane edge now being the local lane edge (the lane following the curve). The F2-closing implementation does not configure a separate stuck check; the `max_episode_steps × control_dt` truncation of `gazebo_lane_env.py` (currently 500 steps × 0.10 s = 50 s; was 400/40 s at F2 closure, raised in F3) acts as the implicit stuck timeout — if the vehicle cannot complete the loop within that window it is reset. Formal closure: `ODD-3.STUCK_TIMEOUT = n/a (subsumed by env truncation)`. A dedicated stuck monitor can be added later (Phase 4 onwards) without disturbing this entry, since the env-level truncation provides a safe upper bound.

---

## 7. ODD-4 — Adverse curvy-loop validation

### 7.1 Relation to ODD-3 and ODD-2

ODD-4 inherits the geometry of ODD-3 and the environmental and stressor mechanisms of ODD-2. Its formal definition is `ODD-4 = scenery(ODD-3) + environmental_conditions(ODD-2) + dynamic_elements(ODD-2) + scenario_profiles(ODD-4-specific)`.

<!--
TEACHER NOTE: The audit raised a question here: does ODD-4 introduce any
stressor that is not present in ODD-2? If yes, declare it explicitly below.
If no, the formal definition above is sufficient and the named profiles
inherit their structure from §5.5.
-->

### 7.2 Named scenario profiles

| Profile ID                  | Inherits from                | Curve-specific additions    |
|-----------------------------|------------------------------|-----------------------------|
| `odd4_nominal_adverse`      | `odd2_nominal_adverse`       | No additional stressors     |
| `odd4_adverse_with_latency` | `odd2_adverse_with_latency`  | No additional stressors     |
| `odd4_adverse_with_obstacle`| `odd2_adverse_with_obstacle` | No additional stressors     |
| `odd4_adverse_full`         | `odd2_adverse_full`          | No additional stressors     |

### 7.3 Excluded conditions and ODD-exit assumptions

Inherit from §6.7 and §6.8 the conditions that depend on curvature, and from §5.6 and §5.7 the conditions that depend on adverse stressors. Conflicts between the two sets are resolved in favour of the more conservative side; the rationale for any explicit relaxation is documented here as a numbered exception.

---

## 8. Physical-deployment ODD (forward reference for F5)

<!--
TEACHER NOTE: This section is intentionally short and skeletal. The full physical
ODD will be written in F5 (week 15) when the CobraFlex platform is being
characterised. What we need here is just enough to declare that (a) a physical
ODD will exist, (b) it will be a refinement of ODD-1 (and possibly ODD-3) for
the actual hardware, and (c) the SRs and hazards in F1 are written abstractly
enough to apply to both. This shields F1 from claims of incompleteness during
Gate 1.
-->

A physical operational design domain, provisionally `ODD-PHYS-1`, will be specified in Phase F5 to characterise the CobraFlex 1:14 platform and its operating environment. ODD-PHYS-1 is intended as the closest hardware-realisable analogue of ODD-1, sharing its scenery type, exclusions, and exit assumptions, while differing in the subject-vehicle dynamic envelope, the sensor and actuation interfaces, and the nominal control latency. The Hazard Register and the Safety Requirements Specification produced in Phase F1 are written so that they hold under both the simulated and the physical ODDs, with parameter values that may be re-tuned for ODD-PHYS-1 when its measured properties become available; any such re-tuning is recorded in the change log of the affected document.

---

## 9. Master parameter table

<!--
TEACHER NOTE: This is the table that will be cited by the SRS, the Cage Spec,
the Scenario Library, and the metrics. Every numerical value mentioned anywhere
else in this document must appear here, with one row per parameter. When a value
changes, update it once here and propagate via the IDs.
-->

| Parameter ID | Quantity | ODD-1 | ODD-2 | ODD-3 | ODD-4 | Source |
| ------------ | -------- | ----- | ----- | ----- | ----- | ------ |
| `*.LANE_WIDTH` | Lane width (m) | 0.245 | 0.245 | 0.245 | 0.245 | Gazebo world files (`src/cobraflex/worlds/*.world` / `*.sdf`) |
| `*.ROAD_WIDTH` | Total road width (m) | 0.50 | 0.50 | 0.50 | 0.50 | Gazebo world files |
| `*.ROAD_LENGTH` | Total road length (m) | 10 | 10 | 8.0232 | 8.0232 | `scripts/compose_lane_circuit.py` preset `oval_R080`; closes TBD-Q8 |
| `*.GRADIENT` | Road gradient | 0 | 0 | 0 | 0 | Map convention |
| `*.FRICTION` | Surface friction coeff. | 1.0 | 1.0 | 1.0 | 1.0 | Gazebo SDF `<surface><friction>` of road geom |
| `*.V_MAX_STRAIGHT` | Max forward speed, straight (m/s) | 0.5 | 0.5 | 0.5 | 0.5 | SR-004; platform envelope |
| `*.V_MAX_CURVE` | Max forward speed, curve (m/s) | n/a | n/a | 0.25 | 0.25 | SR-004; platform envelope |
| `*.K_KAPPA` | Curvature speed-decay coeff. | n/a | n/a | 0.3 | 0.3 | SR-004 |
| `*.KAPPA_MAX` | Max local curvature (1/m) | 0 | 0 | 1.25 | 1.25 | 1 / 0.80 m (R_min of oval_R080); closes TBD-Q9 |
| `*.A_LAT_MAX` | Max commanded lateral accel. (m/s²) | 9.81 | 9.81 | TBD-Q10 | TBD-Q10 | Derived from FRICTION + V_MAX_CURVE — deferred to M-4 |
| `*.T_CTRL` | Control cycle period (ms) | 50 | 50 | 50 | 50 | Implementation |
| `*.LATENCY_NOMINAL` | Nominal control latency (ms) | 50 | 50 | 50 | 50 | Implementation; SR-001 rationale |
| `*.STALENESS_MAX` | Max admissible state staleness (ms) | 200 | 200 | 200 | 200 | SR-007 |
| `*.LANE_EDGE` | Geometric lane edge (m, from centre) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | LANE_WIDTH / 2 |
| `*.CORRIDOR_EDGE` | Drivable-corridor edge (m, from centre) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | Episode-termination logic |
| `*.STUCK_TIMEOUT` | Stuck criterion timeout (s) | n/a | n/a | n/a | n/a | Subsumed by env truncation (`max_episode_steps × control_dt = 50 s`); closes TBD-Q11 |
| `*.OBS_DIM` | Observation vector dimension | 5 | 8 | 5 | 8 | Implementation |
| `*.ACT_DIM` | Action vector dimension | 1 | 1 | 2 | 2 | Implementation |

---

## 10. Traceability hooks

This document is the upstream source for the following downstream artefacts. The Hazard Register cites this document in the *consequence* and *root cause* fields of every hazard whose materialisation depends on a domain attribute (notably H-01, H-02, H-03, H-06, H-07). The Safety Requirements Specification cites parameter IDs in the *parameters* and *rationale* fields of every SR that fixes a numerical threshold (notably SR-001, SR-002, SR-003, SR-004, SR-006, SR-007). The Cage Specification cites this document in the description of the *observed variables* and the *trigger thresholds* of each cage rule. The Scenario Library cites named scenario profile IDs as scenario classes. The Traceability Matrix cross-references a `ODD-N.<PARAM>` identifier when a parameter participates in a hazard-requirement-cage-scenario chain.

---

## 11. Open issues and TBDs

<!--
TEACHER NOTE: This is the action list. Each TBD-Qx tag in the document above
appears here exactly once, with a question, an owner, and a target close date.
Items resolved in subsequent versions are moved to the change log with the
resolved value attached. Do NOT delete TBDs from this list silently; close them
with an explicit value.
-->

| Tag | Question | Owner | Target close | Resolution |
| --- | -------- | ----- | ------------ | ---------- |
| TBD-Q1 | What friction coefficient is configured in the Gazebo SDF `<surface><friction>` block of the road geom in `src/cobraflex/worlds/odd1_straight_road.world` (or its current alias under `src/cobraflex/worlds/`)? Is the value identical across the ODD-1, ODD-3 and ODD-4 world files? | SS | D11 PM | 1.0 (src/cobraflex/worlds/{empty.world,obstacles.world,test_world.sdf} all use `<surface><friction><ode/></friction></surface>` (empty ODE block); Gazebo ODE defaults mu1=mu2=1.0 when no explicit value is set.) -- 2026-05-14 [Value inferred from Gazebo default rather than from an explicit <mu> tag. If a future world introduces an explicit <mu>, re-read and re-run close_odd_tbds.py.] |
| TBD-Q2 | What is the maximum commanded lateral acceleration in ODD-1, derived from FRICTION and V_MAX? | SS | D11 PM | 9.81 (Derived: TBD-Q1 * g = 1.0 * 9.81 m/s^2. Upper bound from the no-skid Coulomb limit; the policy's actually-commanded a_lat in ODD-1 is far smaller because curvature is zero.) -- 2026-05-14 [Operational a_lat in ODD-1 is bounded by the steering geometry of the bicycle model, not by this Coulomb ceiling. The figure is the physical envelope, not a typical value.] |
| TBD-Q3 | What is the numerical "drivable-corridor edge" used by the simulator's episode-termination logic? Why does it differ from LANE_EDGE? | SS | D11 PM | 0.1225 (src/cobraflex_rl/cobraflex_rl/gazebo_lane_env.py L93: `terminated = abs(track_state.ey) > (self.lane_width * 0.5)` with lane_width = 0.245 m from src/cobraflex_rl/config/centerline.yaml.) -- 2026-05-14 [CORRIDOR_EDGE == LANE_EDGE = LANE_WIDTH/2 = 0.1225 m. The env terminates the episode exactly at the geometric lane edge; no separate corridor margin is configured. The ODD-Spec note 'if the two differ, document the rationale' resolves to 'they do not differ'.] |
| TBD-Q4 | What are the lighting-degradation parameters and observation-noise σ in `odd2_nominal_adverse`? | SS | D11 PM | faded markings + non-uniform light; observation noise σ_lateral = 0.03 m; latency/jitter nominal (`src/cobraflex_rl/config/adverse_profiles.yaml` → `odd2_nominal_adverse`; σ = SC-PERT-01 mid level; worn world `lane_following_oval_worn.world`) -- 2026-06-03 [F4-entry closure, D-33] |
| TBD-Q5 | What are the latency, jitter, and actuation-imperfection parameters in `odd2_adverse_with_latency`? | SS | D11 PM | extra latency +100 ms (over 50 ms nominal); jitter 20 ms; steering actuation noise 0.02 (`adverse_profiles.yaml` → `odd2_adverse_with_latency`; latency = SC-PERT-02 high level) -- 2026-06-03 [F4-entry closure, D-33] |
| TBD-Q6 | What are the obstacle geometry, position distribution, and quantity in `odd2_adverse_with_obstacle`? | SS | D11 PM | 1 static box 0.10×0.10×0.10 m, qty 1, ~0.05 m lane intrusion at mid-straight (`adverse_profiles.yaml` → `odd2_adverse_with_obstacle`; modelled on `obstacles.world`; partial-intrusion per §5.3, ODD-exit on contact §5.7) -- 2026-06-03 [F4-entry closure, D-33; SPEC ONLY — execution deferred: no obstacle channel in the 6-dim obs, §5.1 specifies 8-dim] |
| TBD-Q7 | What is the full parameterisation of `odd2_adverse_full` (combining all preceding profiles)? | SS | D11 PM | union of odd2_nominal_adverse + odd2_adverse_with_latency + odd2_adverse_with_obstacle (`adverse_profiles.yaml` → `odd2_adverse_full`) -- 2026-06-03 [F4-entry closure, D-33; inherits the Q6 obstacle execution-deferral] |
| TBD-Q8 | What is the total loop length of the `odd3_curvy_loop` map? | SS | D11 PM | 8.0232 (Sum of `2 × 1.5 m` straights + `2 × π × 0.80 m` arcs = `3 + 1.6π m`, computed by `scripts/compose_lane_circuit.py` preset `oval_R080` and emitted into `src/cobraflex_rl/config/oval_centerline.yaml` under `centerline.perimeter_m`.) -- 2026-05-21 [The composer is the single source of truth; changing `--straight-length` or `--preset` re-derives this value and the polyline simultaneously, so the SRS / cage citation by `ODD-3.ROAD_LENGTH` cannot drift from the world file.] |
| TBD-Q9 | What is the minimum curvature radius of the `odd3_curvy_loop` map (equivalently, KAPPA_MAX)? | SS | D11 PM | 1.25 (R_min = 0.80 m on the two U-turn tiles `curve_R080cm_A180deg.png` of the `oval_R080` preset. KAPPA_MAX = 1 / 0.80 = 1.25 m⁻¹.) -- 2026-05-21 [Switching to the `oval_R050` or `oval_R120` preset would change KAPPA_MAX to 2.00 m⁻¹ or 0.833 m⁻¹ respectively. For Phase 2 the `oval_R080` value is canonical; revisit when ODD-3 graduates to a multi-radius composite circuit.] |
| TBD-Q10 | What is the maximum commanded lateral acceleration in ODD-3, derived from FRICTION and V_MAX_CURVE? | SS | M-4 | Deferred to M-4 calibration. Upper bound from no-skid Coulomb limit on the curve tile: `A_LAT_MAX ≤ FRICTION × g = 9.81 m/s²`. Operational value at `V_MAX_CURVE = 0.25 m/s` on `R_min = 0.80 m` is `V² / R = 0.078 m/s²`, well below the Coulomb ceiling. Final figure closes when M-4 measures the achievable acceleration envelope on the physical platform. |
| TBD-Q11 | What is the stuck-criterion timeout in seconds? | SS | D11 PM | n/a (No separate stuck monitor is configured in the F2 implementation. The `gazebo_lane_env.py` env truncates at `max_episode_steps × control_dt = 400 × 0.10 s = 40 s`, which acts as the implicit stuck timeout.) -- 2026-05-21 [If a dedicated stuck monitor is added later (Phase 4 onwards), this entry should be re-opened to declare its specific value; for now the env truncation is the operational answer.] [F3 update 2026-06-01: `max_episode_steps` was raised 400→500, so the truncation window is now `500 × 0.10 s = 50 s`; the closure is unchanged (n/a, subsumed by env truncation).] |
| TBD-Q12 | Do the ODD-4 named profiles introduce any stressor not present in their ODD-2 counterparts? If yes, document them. | SS | D11 PM | No additional stressors — ODD-4 named profiles are the pure cross-product of ODD-3 geometry × ODD-2 stressors (§7.1; `adverse_profiles.yaml` → `odd4_profiles`) -- 2026-06-03 [F4-entry closure, D-33] |

---

## 12. F4 evaluation realisation on a single world (Phase-4 reconciliation)

<!--
Append-only reconciliation (cf. §1 TEACHER NOTE: numerical authority flows
spec → evidence, never the reverse). This section changes NO ODD parameter; it
records which sub-region of the ODD-1..ODD-4 stratification the F4 simulation
campaign actually exercises, and declares the coverage gaps. Recorded as D-37.
-->

The four ODDs above are specified across **two** geometries — a dedicated
straight world for ODD-1/ODD-2 and the curvy oval for ODD-3/ODD-4. The F4
**simulation** campaign, however, runs **every** scenario on the single oval
world `lane_following_oval.world` (preset `oval_R080`), per *Option A* of the
Track-mapping note in `docs/05` and decision **D-37**. The oval already contains
both straight tiles (1.5 m) and U-turn curve tiles, so the straight/curvy axis
is realised by the **start arc-length** `start_s` rather than by separate
worlds. The dedicated `odd1_straight_road.world` is **reserved for the F5
physical subset** (a straight is simpler to set up on hardware than an oval).

All F4 runs share **one operating point**: fixed forward speed **0.2 m/s**,
**steering-only** action (`ACT_DIM = 1`, throttle held constant; Training Spec
§7.2.2), a **6-dimensional** observation (the F3 policy; cf. §5.5 footnote), and
no obstacle channel.

### 12.1 ODD → oval realisation

| ODD | Realised on the oval as | Speed / ACT_DIM | Scenarios | Coverage |
| --- | --- | --- | --- | --- |
| ODD-1 — nominal straight | `start_s = 0.0`, straight tile (1.5 m) | 0.2 m/s, 1 | SC-NOM-01, SC-EDGE-01..05, SC-PERT-03 | **Covered** (caveat 12.2-a) |
| ODD-2 — adverse straight | `start_s = 0.0` + inline stressors (levels match §5.5) | 0.2 m/s, 1 | SC-PERT-01 (noise σ), SC-PERT-02 (latency), SC-EDGE-03 (throttle) | **Covered** except obstacles (deferred, D-33) |
| ODD-3 — nominal curvy | `start_s = 1.5` (curve entry) + full loop | 0.2 m/s, **1** | SC-NOM-02, SC-NOM-03 | **Partial** — curve geometry yes, speed envelope no (12.2-b) |
| ODD-4 — adverse curvy | *(no scenario combines curve + stressor)* | — | none | **Not exercised** — no adverse-curvy scenario; `odd4_*` profiles (§7.2) spec-only (12.2-b, 12.2-e) |
| Beyond ODD-1 | `start_s = 0.0`, out-of-ODD initial state | 0.2 m/s, 1 | SC-FRONT-01..06 | Cage-efficacy contrast (D-35) — paired, not a verdict |

### 12.2 Declared coverage gaps

- **(a) ODD-1/2 length & curvature.** `ODD-1.ROAD_LENGTH = 10 m, κ ≡ 0` is
  approximated by the oval's **1.5 m** straight tile; curvature is zero only
  within the recovery window before curve entry. The single-rule isolation each
  straight scenario intends is preserved because the recovery budgets complete
  within 1.5 m at 0.2 m/s (cf. `docs/05`, "Recovery fits the straight").
- **(b) ODD-3/4 speed envelope NOT exercised.** ODD-3/ODD-4 are *defined* by a
  **2-dimensional** action space (steering + speed) and a curvature-dependent
  speed cap `v_max(κ)` with `ODD-3.V_MAX_CURVE = 0.25 m/s`. The evaluated policy
  is **fixed-speed, `ACT_DIM = 1`**, so this envelope is **not** validated by
  closed-loop policy control. ODD-3 is therefore claimed **partial**: the curve
  *geometry* and the cage's lateral behaviour on curves are exercised
  (SC-NOM-02/03), but the speed-adaptation envelope is validated only at the
  cage-rule level (C-04 unit tests), not end-to-end. Closing this gap needs a
  variable-speed (`ACT_DIM = 2`) policy — future work (F5+).
- **(c) Observation / obstacles.** The evaluated policy is 6-dim; the spec's
  `ODD-1.OBS_DIM = 5` / `ODD-2,4.OBS_DIM = 8` are not the evaluated config. The
  8-dim obstacle profiles remain execution-deferred (D-33); the 5↔6 difference
  for the nominal vector is a separate documentation reconciliation, noted here,
  with no effect on any SR or cage threshold.
- **(d) Single operating speed.** 0.2 m/s is below both `V_MAX = 0.5` and
  `V_MAX_CURVE = 0.25`; F4 is a single conservative operating point, not a speed
  sweep.
- **(e) ODD-4 has no dedicated scenario.** No scenario in the F4 verdict library
  layers an adverse stressor on a curve start, and the `odd4_*` named profiles
  (§7.2) are specified but unused. ODD-4 (adverse × curvy) is therefore deferred
  in full, compounding gap (b).

These gaps are the Phase-4 analogue of the bounded-validation principle (D-11)
and are reported in the manuscript Limitations (§1.6.3 / Cap. 11). They change no
ODD parameter, SR threshold, or cage constant; the spec above remains the
authoritative definition of the *intended* domain.

### 12.3 Version status at G4 (v1.0 carries one open TBD to F5)

The maturation plan (D-33 rationale) targeted **v1.0 "all TBDs resolved, signed off
at G4."** With the F4 campaign closed, **11 of 12 TBDs are resolved**; the sole
remainder, **TBD-Q10 (`ODD-3.A_LAT_MAX`, maximum lateral acceleration)**, depends on
the **physical** lateral-accel calibration **M-4** and is by construction
**unmeasurable in simulation** — it is deferred to F5 (D-33). The ODD-Spec is
therefore signed off at G4 at its current minor version with **Q10 explicitly
carried forward to F5**, not promoted to 1.0; 1.0 is reached when M-4 closes Q10 on
the physical platform. This is a disclosed limitation, not an open orphan: every
*simulation-resolvable* TBD is closed, and Q10's dependency on hardware is recorded
here and in D-33.

---
<!--
## 13. Anticipated defense questions

**Q1. `ODD-1.A_LAT_MAX = 9.81 m/s²` is just *g* — is that a real envelope or a placeholder?**
It is the no-skid Coulomb ceiling (`FRICTION × g = 1.0 × 9.81`), i.e. the *physical* envelope, not a typical value — and the document says so (TBD-Q2 note). On a straight (`κ ≡ 0`) the operationally commanded lateral acceleration is far smaller, bounded by the bicycle-model steering geometry. The Coulomb figure is the bound the platform cannot exceed without sliding; the consequential curve value (`ODD-3.A_LAT_MAX`, TBD-Q10) is the one deferred to the M-4 physical calibration.

**Q2. §12 admits the F4 campaign runs everything on one oval at one fixed speed, leaving ODD-3's speed envelope and all of ODD-4 unexercised — isn't that a large hole in the validation?**
It is a *declared, bounded* gap (D-37, §12.2), not a silent one. ODD-3 is claimed **partial** — curve geometry yes, the 2-D `v_max(κ)` speed envelope no, because the evaluated policy is `ACT_DIM = 1` fixed-speed — and ODD-4 is **not exercised** (no adverse-curvy scenario). Closing it needs a variable-speed policy (future work, F5+). The speed envelope is still checked at the cage-rule level (C-04 unit tests), just not end-to-end. This is the Phase-4 analogue of the bounded-validation principle (D-11), reported in the manuscript Limitations.

**Q3. Several "closed" TBDs are *inferred*, not measured — friction = 1.0 comes from an empty Gazebo ODE block, not an explicit `<mu>`. Is that a real closure?**
TBD-Q1 is closed to the Gazebo ODE default (`mu1 = mu2 = 1.0`) because the world files ship an empty `<friction>` block, and the closure note explicitly flags the value as *inferred* and instructs re-reading if a future world sets an explicit `<mu>`. That is a defensible, documented closure with its assumption surfaced — not a fabricated number. The one genuinely unmeasurable item (Q10) is left open and deferred to M-4.

**Q4. The document insists numerical authority flows spec → evidence "never the reverse", yet §12 was added to reconcile the spec with what F4 actually ran — didn't the evidence drive the spec here?**
No: §12 changes *no* ODD parameter (it states this three times). It records which sub-region of the specified domain the campaign exercises and declares the gaps; the `ODD-N.<PARAM>` values remain the authoritative definition of the *intended* domain. The append-only reconciliation documents coverage — it does not back-propagate a measured value into a threshold.

**Q5. There is a 5-vs-6 observation-dimension discrepancy: the spec says `ODD-1.OBS_DIM = 5` but the evaluated F3 policy is 6-dimensional. Which is correct?**
The evaluated policy is 6-dim (a signed curvature preview, `kappa_near` / `kappa_far`, added in F3 — see `docs/09`). The spec's `OBS_DIM = 5` predates that and is flagged in §12.2(c) as a documentation reconciliation with *no effect on any SR or cage threshold*: the extra signal is an abstract centerline preview, not a new ODD attribute. It is a known, scoped, harmless bookkeeping mismatch, not a contradiction in the safety-relevant parameters.

**Q6. Why specify four ODDs and a full PAS 1883 / ISO 34503 taxonomy for a 1:14 lane-follower — isn't that ceremony disproportionate to the system?**
The stratification (ODD-1 nominal → ODD-2 + stressors → ODD-3 + curvature → ODD-4 combined) is precisely what lets an observed safety or performance change be attributed to a *single* axis of complexity rather than a confounded mixture — that is the methodological core of an SE4AI thesis, not ceremony. The taxonomy supplies the standards vocabulary the automotive committee expects, and the parameter-ID single-sourcing is what prevents the documentation cycles the document's own notes warn about. The cost is upfront; the payoff is clean attribution and non-drifting thresholds.

--->

*End of ODD-SPEC v0.6.*
