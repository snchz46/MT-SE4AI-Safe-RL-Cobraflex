# ODD Specification — SE4AI Lane Following Thesis

**Document ID:** `ODD-SPEC`
**Version:** 0.1 (draft, D11 of Phase 1)
**Owner:** Samuel Sánchez
**Phase of birth:** F0 — Phase of maturity: F1 — Phase of revision: F5 (physical ODD)
**Status:** DRAFT — contains TBD values that must be filled before Gate 1
**Last updated:** 2026-05-02
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

| Version | Date       | Author | Summary                                                                                               |
|---------|------------|--------|-------------------------------------------------------------------------------------------------------|
| 0.1     | 2026-05-02 | SS     | Initial structural extraction from `draft_V3.docx` §6.1, with TBDs for unresolved quantitative items. |

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

The intended function is lane following on a structured straight-road segment. The subject vehicle is the simulated CobraFlex-like platform of the MuJoCo environment, operating at low forward speed with a single steering degree of freedom controlled by the policy. ODD-1 is the reference point against which all other domains are differentially defined; it is intentionally the narrowest of the four to support interpretable PPO training, reproducible debugging, and unambiguous scenario derivation.

### 4.2 Scenery

The drivable area is a two-lane straight segment of uniform asphalt-like surface, with clearly visible lateral lane boundaries, a dashed central lane separator, flat geometry, and no junctions, special structures, or temporary road structures. Total road width is `0.50 m`, lane width per direction is `0.245 m`, and total road length is `10 m`. The road gradient is zero. The friction coefficient of the simulated surface is `TBD-Q1` (must be read from the MuJoCo material specification of `odd1_straight_road`).

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

The forward speed range under nominal operation is `[0, ODD-1.V_MAX]` with `ODD-1.V_MAX = 0.5 m/s` (consistent with SR-004 on straight sections). The local path curvature is `κ ≡ 0` everywhere within ODD-1 (straight road). The lateral acceleration that the policy is expected to command is bounded by `ODD-1.A_LAT_MAX = TBD-Q2` (must be derived from the friction coefficient and the velocity envelope). The control cycle nominal period is `ODD-1.T_CTRL = 50 ms` (20 Hz). The end-to-end nominal control latency between observation and applied command is assumed to be no greater than `ODD-1.LATENCY_NOMINAL = 50 ms` (this number is also referenced by SR-001 in the rationale of `d_max`).

### 4.6 Sensor and actuation interfaces

The agent does not receive raw camera or LiDAR data. Instead, it receives a 5-dimensional state vector composed of lateral error, heading error, current speed, current steering value, and previously issued steering action. The action space in ODD-1 is one-dimensional and continuous, corresponding to the steering command only. The throttle is set to a constant nominal value within `[0, ODD-1.V_MAX]` and is not a controlled variable in this domain.

A sensor reading is considered nominal when its timestamp is no older than `ODD-1.STALENESS_MAX = 200 ms` and all of its fields lie within their physically plausible ranges (see §9 master parameter table). Violations of this nominal sensor condition are not part of ODD-1 itself but trigger Hazard H-06 and Safety Requirement SR-007.

### 4.7 Excluded conditions

ODD-1 explicitly excludes any non-zero curvature, any deviation from uniform illumination, any presence of dynamic or static obstacles, any precipitation or particulates, any sensor degradation, and any forward speed exceeding `ODD-1.V_MAX`. Operation under any of these conditions is, by definition, outside ODD-1; it does not necessarily violate the SRs, but it does mean that the corresponding evidence belongs to a different domain.

### 4.8 ODD-exit assumptions

The system is considered to be exiting ODD-1 when the absolute lateral offset of the vehicle exceeds `0.1225 m` (the geometric edge of the lane, equal to lane width over two), when the forward speed exceeds `ODD-1.V_MAX`, when the simulator reports a contact event with the road edge, or when an episode termination condition fires. The policy is not designed to recover the system once it has exited ODD-1; recovery, if attempted at all, is the responsibility of the cage in emergency mode, governed by Cage Rule C-05 and Safety Requirements SR-005, SR-007, SR-008.

The "drivable corridor" boundary used by the simulator's episode-termination logic is `TBD-Q3`. This must be reconciled with the geometric lane edge above; if the two differ, the rationale for the difference must be documented here.

### 4.9 Parameter summary for ODD-1

See §9 master parameter table for the consolidated tabular form. The parameters declared in this section are: `ODD-1.LANE_WIDTH`, `ODD-1.ROAD_WIDTH`, `ODD-1.ROAD_LENGTH`, `ODD-1.GRADIENT`, `ODD-1.FRICTION` (TBD-Q1), `ODD-1.V_MAX`, `ODD-1.KAPPA_MAX`, `ODD-1.A_LAT_MAX` (TBD-Q2), `ODD-1.T_CTRL`, `ODD-1.LATENCY_NOMINAL`, `ODD-1.STALENESS_MAX`, `ODD-1.LANE_EDGE`, `ODD-1.CORRIDOR_EDGE` (TBD-Q3).

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

<!--
TEACHER NOTE: This is the section that the audit flagged as missing quantitative
content. Each named profile must give explicit parameters; an empty cell below
breaks the citation chain from any SR that references "the adverse_with_latency
scenario". Fill the TBD-Q4 to TBD-Q7 blocks before Gate 1. If the values live
already in a YAML or JSON file in the project, copy them here AND link to the file.
-->

| Profile ID                  | Lighting / markings                  | Obstacle config            | Sensor noise (σ)             | Latency (ms)        | Jitter (ms)      | Actuation imperfection |
|-----------------------------|--------------------------------------|----------------------------|------------------------------|---------------------|------------------|------------------------|
| `odd2_nominal_adverse`      | Faded markings + non-uniform light   | None                       | TBD-Q4                       | TBD-Q4              | TBD-Q4           | None                   |
| `odd2_adverse_with_latency` | Nominal markings + nominal light     | None                       | TBD-Q5                       | TBD-Q5              | TBD-Q5           | TBD-Q5                 |
| `odd2_adverse_with_obstacle`| Nominal                              | TBD-Q6 (geometry, position)| TBD-Q6                       | TBD-Q6              | TBD-Q6           | None                   |
| `odd2_adverse_full`         | Faded markings + non-uniform light   | TBD-Q7                     | TBD-Q7                       | TBD-Q7              | TBD-Q7           | TBD-Q7                 |

### 5.6 Excluded conditions

ODD-2 retains all exclusions from ODD-1 that are not explicitly relaxed above. In particular, dynamic agents, intersections, route-planning demands, gradient changes, weather effects beyond illumination, and curvature remain excluded.

### 5.7 ODD-exit assumptions

The same exit conditions as ODD-1 apply. Additionally, ODD-2 considers the system to be exiting the domain if any obstacle is contacted by the subject vehicle, whether the obstacle was inside or partially intruding the lane.

---

## 6. ODD-3 — Nominal curvy-loop domain

### 6.1 Relation to ODD-1

ODD-3 preserves the environmental conditions and the dynamic-element exclusions of ODD-1 unchanged, and differs from it in three respects: the scenery is a closed loop with curvature, the action space is two-dimensional (steering and speed) rather than one-dimensional, and the subject-vehicle dynamic envelope must accommodate non-zero lateral acceleration.

### 6.2 Scenery

The drivable area is a structured two-lane closed loop containing multiple 90-degree turns and one S-shaped section, with clearly visible lateral lane boundaries and a dashed centre line. The total loop length is `TBD-Q8` and the minimum curvature radius is `TBD-Q9` (this last parameter, equivalently expressed as `ODD-3.KAPPA_MAX = 1 / R_min`, is the most consequential physical constant of this domain and is referenced by SR-004 and Cage Rule C-04). Lane width, road width, and surface friction are inherited from ODD-1 unless otherwise stated.

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

Inherits the lateral-offset and contact criteria from ODD-1 with the lane edge now being the local lane edge (the lane following the curve). Adds, additionally, an exit condition based on the "stuck" criterion characteristic of closed loops: the vehicle is considered to have exited the domain if it remains within a small spatial neighbourhood for longer than `TBD-Q11` consecutive seconds without progressing along the route.

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
| `odd4_nominal_adverse`      | `odd2_nominal_adverse`       | TBD-Q12                     |
| `odd4_adverse_with_latency` | `odd2_adverse_with_latency`  | TBD-Q12                     |
| `odd4_adverse_with_obstacle`| `odd2_adverse_with_obstacle` | TBD-Q12                     |
| `odd4_adverse_full`         | `odd2_adverse_full`          | TBD-Q12                     |

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

| Parameter ID                 | Quantity                                  | ODD-1   | ODD-2   | ODD-3       | ODD-4       | Source                          |
|------------------------------|-------------------------------------------|---------|---------|-------------|-------------|---------------------------------|
| `*.LANE_WIDTH`               | Lane width (m)                            | 0.245   | 0.245   | 0.245       | 0.245       | MuJoCo map files                |
| `*.ROAD_WIDTH`               | Total road width (m)                      | 0.50    | 0.50    | 0.50        | 0.50        | MuJoCo map files                |
| `*.ROAD_LENGTH`              | Total road length (m)                     | 10      | 10      | TBD-Q8      | TBD-Q8      | MuJoCo map files                |
| `*.GRADIENT`                 | Road gradient                             | 0       | 0       | 0           | 0           | Map convention                  |
| `*.FRICTION`                 | Surface friction coeff.                   | TBD-Q1  | TBD-Q1  | TBD-Q1      | TBD-Q1      | MuJoCo material spec            |
| `*.V_MAX_STRAIGHT`           | Max forward speed, straight (m/s)         | 0.5     | 0.5     | 0.5         | 0.5         | SR-004; platform envelope       |
| `*.V_MAX_CURVE`              | Max forward speed, curve (m/s)            | n/a     | n/a     | 0.25        | 0.25        | SR-004; platform envelope       |
| `*.K_KAPPA`                  | Curvature speed-decay coeff.              | n/a     | n/a     | 0.3         | 0.3         | SR-004                          |
| `*.KAPPA_MAX`                | Max local curvature (1/m)                 | 0       | 0       | TBD-Q9      | TBD-Q9      | MuJoCo map geometry             |
| `*.A_LAT_MAX`                | Max commanded lateral accel. (m/s²)       | TBD-Q2  | TBD-Q2  | TBD-Q10     | TBD-Q10     | Derived from FRICTION + V_MAX   |
| `*.T_CTRL`                   | Control cycle period (ms)                 | 50      | 50      | 50          | 50          | Implementation                  |
| `*.LATENCY_NOMINAL`          | Nominal control latency (ms)              | 50      | 50      | 50          | 50          | Implementation; SR-001 rationale|
| `*.STALENESS_MAX`            | Max admissible state staleness (ms)       | 200     | 200     | 200         | 200         | SR-007                          |
| `*.LANE_EDGE`                | Geometric lane edge (m, from centre)      | 0.1225  | 0.1225  | 0.1225      | 0.1225      | LANE_WIDTH / 2                  |
| `*.CORRIDOR_EDGE`            | Drivable-corridor edge (m, from centre)   | TBD-Q3  | TBD-Q3  | TBD-Q3      | TBD-Q3      | Episode-termination logic       |
| `*.STUCK_TIMEOUT`            | Stuck criterion timeout (s)               | n/a     | n/a     | TBD-Q11     | TBD-Q11     | Episode-termination logic       |
| `*.OBS_DIM`                  | Observation vector dimension              | 5       | 8       | 5           | 8           | Implementation                  |
| `*.ACT_DIM`                  | Action vector dimension                   | 1       | 1       | 2           | 2           | Implementation                  |

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

| Tag      | Question                                                                                                                              | Owner | Target close | Resolution |
|----------|---------------------------------------------------------------------------------------------------------------------------------------|-------|--------------|------------|
| TBD-Q1   | What friction coefficient is configured in the MuJoCo material of `odd1_straight_road`? Is it identical for ODD-3 and ODD-4 maps?        | SS    | D11 PM       |            |
| TBD-Q2   | What is the maximum commanded lateral acceleration in ODD-1, derived from FRICTION and V_MAX?                                         | SS    | D11 PM       |            |
| TBD-Q3   | What is the numerical "drivable-corridor edge" used by the simulator's episode-termination logic? Why does it differ from LANE_EDGE?              | SS    | D11 PM       |            |
| TBD-Q4   | What are the lighting-degradation parameters and observation-noise σ in `odd2_nominal_adverse`?                                              | SS    | D11 PM       |            |
| TBD-Q5   | What are the latency, jitter, and actuation-imperfection parameters in `odd2_adverse_with_latency`?                                        | SS    | D11 PM       |            |
| TBD-Q6   | What are the obstacle geometry, position distribution, and quantity in `odd2_adverse_with_obstacle`?                                      | SS    | D11 PM       |            |
| TBD-Q7   | What is the full parameterisation of `odd2_adverse_full` (combining all preceding profiles)?                                              | SS    | D11 PM       |            |
| TBD-Q8   | What is the total loop length of the `odd3_curvy_loop` map?                                                                               | SS    | D11 PM       |            |
| TBD-Q9   | What is the minimum curvature radius of the `odd3_curvy_loop` map (equivalently, KAPPA_MAX)?                                              | SS    | D11 PM       |            |
| TBD-Q10  | What is the maximum commanded lateral acceleration in ODD-3, derived from FRICTION and V_MAX_CURVE?                                   | SS    | D11 PM       |            |
| TBD-Q11  | What is the stuck-criterion timeout in seconds?                                                                                            | SS    | D11 PM       |            |
| TBD-Q12  | Do the ODD-4 named profiles introduce any stressor not present in their ODD-2 counterparts? If yes, document them.                          | SS    | D11 PM       |            |

---

*End of ODD-SPEC v0.1.*
