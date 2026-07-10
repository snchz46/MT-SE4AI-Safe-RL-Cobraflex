# Prompts para Claude Design — figuras visuales de la tesis

> **Material de trabajo** (no es artefacto de la tesis; bórralo o déjalo fuera del
> commit si no lo quieres versionado). Cada prompt es autocontenido: lleva los
> datos reales verificados contra `docs/` y la paleta de la casa, así que se puede
> copiar y pegar tal cual. Etiquetas de figura en inglés (convención del repo);
> los pies de figura en el manuscrito van en español.
>
> Paleta común (ya embebida en cada prompt): morado = policy aprendida,
> verde-azulado (teal) = percepción determinista, coral = safety cage,
> gris cálido = simulador/infraestructura.

---

## P1 — "From pixels to action" (CNN NatureCNN + PPO, track E)

**Destino:** diapositiva central de la defensa; versión sobria para Cap. 7 §7.1 o Cap. 5 §5.7.4.
**Nota:** adjunta al prompt un frame real de la cámara si puedes (p. ej. un recorte de
`manuscript/figures/fig_7_7_gazebo_capture.png` o cualquier frame de eval); si no,
el placeholder que deje la herramienta se sustituye luego.

```text
Create a clean, academic engineering figure (SVG, 16:9 landscape, flat design, no
gradients, white background, sans-serif like Inter/Helvetica, legible at 1600 px
wide) titled "From camera pixels to steering action — end-to-end policy (track E)".

It shows a left-to-right pipeline in the style of classic CNN architecture
diagrams (AlexNet-style 3D slabs for conv feature maps). Stages, with exact
numbers (do not invent any):

1. "Gazebo front lane camera" — a photo-like placeholder rectangle labeled
   "native frame 640x360 · HFOV 90° · 20 Hz · pitched down 0.30 rad". Neutral
   gray styling (fill #F1EFE8, stroke #5F5E5A).
2. Small intermediate block "degradation injector (DR draw or scenario
   stressor) — applied ONCE, before the split (D-43)". Neutral gray.
3. "Observation: 4 stacked 84x84 grayscale frames" — draw 4 overlapping small
   squares (frame stack, VecFrameStack k=4; channel-first 4x84x84). Purple
   styling (fill #EEEDFE, stroke #534AB7, text #26215C).
4. "NatureCNN feature extractor (~1.7 M params)" as three 3D slabs + one bar,
   purple, each labeled:
   - "Conv 8x8, stride 4 → 32 @ 20x20, ReLU"
   - "Conv 4x4, stride 2 → 64 @ 9x9, ReLU"
   - "Conv 3x3, stride 1 → 64 @ 7x7, ReLU"
   - "Flatten 3136 → FC 512, ReLU"
5. Two small heads branching from the 512 features:
   - "Policy head: Gaussian steering — mean μ + learned log σ" (purple) →
     arrow to stage 6.
   - "Value head V(s) — training only" (gray, dashed border) → arrow into a
     dashed "training-only" region at the bottom containing "reward (sim
     oracle: ey, epsi, progress)" and "PPO clipped-surrogate update"; a dashed
     gradient arrow ∇θ returns from PPO to the CNN trunk. Label the region
     "exists only during training — no reward, no V(s) at deployment".
6. "Safety cage — 6 deterministic rules, order C-06→C-04→C-02→C-03→C-01→C-05"
   as a coral box (fill #FAECE7, stroke #993C1D): input "raw steering ∈ [−1,1]",
   output "safe action".
7. "Actuation: geometry_msgs/Twist on /cmd_vel — angular.z = steer × 0.8,
   linear.x = 0.2 m/s" (neutral gray), with a loop-back arrow labeled "Gazebo
   step 0.10 s (10 Hz control)" returning to stage 1.

Under-annotate, don't over-decorate: thin arrows, small caption-size labels,
generous white space. The visual emphasis order is: input image → conv slabs →
steering distribution → cage.
```

---

## P2 — "One sensor, two eyes" (bifurcación D-43: CNN vs estimador CV)

**Destino:** defensa (pregunta de independencia) + Cap. 5 §5.2.3/§5.7.4 o docs/12.
**Nota:** ideal con un frame real degradado repetido en ambas ramas; los overlays
(máscara, puntos, polinomios) pueden ser estilizados.

```text
Create a clean academic engineering figure (SVG, 16:9 landscape, flat design,
white background, sans-serif, legible at 1600 px wide) titled "One sensor, two
independent readers — the D-43 split (track E)".

Layout: ONE camera frame on the left ("native frame 640x360, degraded once —
common-cause point"), neutral gray (fill #F1EFE8, stroke #5F5E5A). From it, two
horizontal branches:

TOP branch (purple, fill #EEEDFE, stroke #534AB7) — "What the learned policy
sees": the frame downsampled to "84x84 grayscale, stack of 4" (draw 4 small
overlapping squares) → "CNN policy (PPO, NatureCNN)" → output "steering ∈ [−1,1]".

BOTTOM branch (teal, fill #E1F5EE, stroke #0F6E56) — "What the cage's
deterministic CV estimator sees" as five mini-stages, each a small thumbnail of
the SAME frame with a stylized overlay (exact labels, do not invent numbers):
  1. "HSV white mask — S ≤ 30, V ≥ 150, vegetation hues 35–85° excluded"
     (thumbnail: white lane pixels isolated on black).
  2. "Row scan → ground points — 24 rows, 0.15–1.0 m ahead, pixel→ground via
     closed-form pitch-only camera model" (thumbnail: dots along the lane lines).
  3. "Greedy line clustering — Y = c0 + c1·X + c2·X²" (thumbnail: two fitted
     curves through the dots).
  4. "Lane-pair selection — expected width 0.245 ± 0.10 m, single-line fallback"
     (thumbnail: the driven pair highlighted).
  5. "State readout — ey = −c0 · epsi = −atan(c1) · κ = 2·c2 + confidence".
Then → "Perception supervisor: SR-013 health check (stale/dropped frame, low
confidence, missing features) + SR-014 plausibility & temporal consistency" →
either "cage State (ey, epsi, …)" or a red-ish exit "perception_invalid →
C-05 Trigger 8: open-loop controlled stop — needs NO perception
('no valid lines ⇒ stop')".

Both branches converge on the right into a coral box (fill #FAECE7, stroke
#993C1D): "Safety cage C-01..C-06 — judges the learned branch using the
deterministic branch". Output arrow "safe action → /cmd_vel".

Bottom caption strip (small, gray): "Same sensor ⇒ common cause is treated
explicitly: H-10 degraded visual input → SR-012 · H-11 perception loss →
SR-013 · H-12 confident misdetection → SR-014. Independence is algorithmic
(learned CNN vs classical CV), not sensorial."
```

---

## P3 — Geometría del estado + umbrales del cage (ey, epsi, κ, TTLC)

**Destino:** Cap. 4/5 (definición formal) y backup slide de defensa. No existe
ninguna figura que defina ey/epsi y se usan en toda la tesis.

```text
Create a clean academic engineering figure (SVG, 16:9 landscape, flat design,
white background, sans-serif) titled "Vehicle state and cage thresholds —
schematic, not to scale". Three panels left to right:

PANEL A — "State definition (bird's-eye view)": a curved lane segment (two
lane lines + dashed centerline of the driven lane), a small top-view car
slightly off-center and slightly rotated. Annotate with thin dimension arrows:
  - "ey — lateral offset from the driven-lane centerline [m]"
  - "epsi (θ) — heading error vs lane tangent [rad]"
  - "v — forward speed [m/s]" (arrow along the car's heading)
  - "κ — local curvature ahead [1/m]" (small arc annotation on the centerline)
Neutral gray road, purple car (stroke #534AB7).

PANEL B — "Threshold ladder" : two horizontal band charts (coral bands, fill
#FAECE7, stroke #993C1D). Use EXACTLY these values:
  Lateral |ey|:  0.12 m = "d_warning (C-05 compound trigger)" ·
                 0.14 m = "C-01 fires (d_max − hysteresis 0.02)" ·
                 0.16 m = "d_max (SR-001 hard limit)".
  Heading |θ|:   20° = "θ_warning (C-05)" · 23° = "C-02 fires (θ_max − hyst. 2°)" ·
                 25° (0.44 rad) = "θ_max (SR-002 hard limit)".
  Add one line below: "Speed ceiling C-04: v ≤ 0.5 m/s straight · ≤ 0.25 m/s
  curve · v_warning 0.4 m/s".

PANEL C — "Predictive rule C-03 (TTLC)": same bird's-eye lane, car near the
centerline with a dashed projected trajectory (zero corrective action) crossing
the |ey| = 0.16 m boundary; annotate the crossing point "projected crossing at
t = TTLC" and the rule "C-03 fires if TTLC < 1.0 s — correction magnitude
scales with urgency".

Keep everything schematic; add the footnote "distances exaggerated for
legibility — thresholds are the real cage.yaml values".
```

---

## P4 — Matriz de veredictos por SR (cierre G4)

**Destino:** cierre del Cap. 8 + slide de conclusiones de la defensa.

```text
Create a clean academic results-matrix figure (SVG, 16:9 landscape, flat
design, white background, sans-serif, generous row height) titled "Safety
Requirements — verdicts at G4 closure (02.07.2026)".

A table-like grid: 14 rows (SR-001..SR-014) + a bottom "Global" band. Columns:
  [SR id] [implements] [F-track verdict — F4 campaign, frozen baseline]
  [E-track verdict — GE4-V2, verdict of record] [note].

Color legend (use these four chip styles):
  - Satisfied: teal chip (fill #E1F5EE, stroke #0F6E56)
  - Satisfied on own criterion, literal clause fail (D-47): amber chip
    (fill #FBF0DC, stroke #8A6116)
  - Genuine CL-B finding: purple chip (fill #EEEDFE, stroke #534AB7)
  - N/A / abstention: gray chip (fill #F1EFE8, stroke #5F5E5A)

EXACT row data (do not invent):
  SR-001 · C-01 lane boundary        · F: Satisfied · E: Satisfied — "ruta-1: SC-EDGE-02 IC clipped to ODD, 28/30; 2 residuals = H-12 confident under-read"
  SR-002 · C-02 heading limit        · F: Satisfied · E: Satisfied on own criterion (D-47) — "literal fail only on SC-EDGE-01's oval-legacy 2.0 s recovery clause; max heading 14.4° ≤ 25°, 0 emergencies"
  SR-003 · C-03 predictive TTLC      · F: Satisfied · E: Satisfied on own criterion (D-47) — same clause as SR-002
  SR-004 · C-04 speed ceiling        · F: Satisfied · E: Satisfied
  SR-005 · C-05 emergency mode       · F: Satisfied · E: Satisfied
  SR-006 · C-06 rate limiter         · F: Satisfied (D-39: 559/559 enforcement vs 67.6% monitoring) · E: Satisfied
  SR-007 · C-05 state validity       · F: Satisfied · E: Satisfied
  SR-008 · C-05 controlled stop      · F: Satisfied · E: Satisfied
  SR-009 · training constraint       · F: documented abstention (D-30) · E: N/A-by-construction — "1-D steering-only action ⇒ stall test ill-posed (M-P6 ≡ 0, D-49); deferred to Isaac 2-D action"
  SR-010 · arbiter property          · F: documented abstention (D-30) · E: genuine CL-B finding — "wired SC-EDGE-05 grid: 30/85 in-ODD co-activation breaches"
  SR-011 · C-06 + training           · F: Satisfied · E: Satisfied
  SR-012 · camera lane-keeping       · F: — (not in F verdict) · E: Satisfied (GE4-V2, D-29 coverage closed)
  SR-013 · safe perception-loss stop · F: — · E: Satisfied (SC-PERT-07 25/25 · SC-PERT-13 40/40)
  SR-014 · estimator plausibility    · F: — · E: Satisfied (SC-PERT-08 false-lane 25/25)

Global band, two cells:
  "F4 global: SATISFIED — all 7 SR-CL-A, no veto (D-30)" (teal)
  "GE4-V2 global: NOT SATISFIED (literal) — blocked by SR-002/003's legacy
  recovery-time clause only; NO SR-CL-A safety predicate breached; verdict
  recorded literal + reconciliation annotated (D-47)" (amber).

Mark SR-CL-A rows with a small "A" tag and CL-B rows (SR-006, SR-009, SR-010,
SR-011) with "B". Keep the notes column in small caption text.
```

---

## P5 — Heatmap de cobertura H ↔ SR (Figura 4.4 pendiente)

**Destino:** Cap. 4 §4.8.2 (placeholder «Figura 4.4»).

```text
Create a clean academic coverage-matrix figure (SVG, near-square, flat design,
white background, sans-serif) titled "Hazard ↔ Safety Requirement coverage
(machine-checked)". 

Grid: 12 rows = hazards H-01..H-12, 14 columns = SR-001..SR-014. A filled
teal cell (fill #0F6E56 at ~85% opacity) marks "SR mitigates hazard"; empty
cells very light gray. EXACT marks (row: columns):
  H-01: SR-001, SR-003
  H-02: SR-002, SR-003, SR-011
  H-03: SR-004
  H-04: SR-005
  H-05: SR-006
  H-06: SR-007
  H-07: SR-005, SR-008
  H-08: SR-009
  H-09: SR-010
  H-10: SR-012
  H-11: SR-013
  H-12: SR-014

Row labels (small, two lines): id + short name + criticality:
  H-01 "Unintended lane exit · High" · H-02 "Divergent/oscillatory heading ·
  Med-High" · H-03 "Excessive speed · Medium" · H-04 "Compound unrecoverable
  state · High" · H-05 "Abrupt actuator command · Medium" · H-06 "Invalid/
  unobservable state · High" · H-07 "No controlled stop · High" · H-08
  "Progress stall (reward exploitation) · Med-High" · H-09 "Cage rule conflict
  · Medium" · H-10 "Lane misperception, degraded input · High" · H-11 "Loss of
  lane perception · High" · H-12 "Cage lane-misdetection · High".
Column headers rotated 45°, tagging criticality class: SR-001..005, SR-007,
SR-008, SR-012..014 = "CL-A"; SR-006, SR-009..011 = "CL-B". Visually separate
the track-E extension (H-10..H-12 rows and SR-012..014 columns) with a thin
dashed divider labeled "track E extension (D-41/D-43)".

Footer caption: "Every row and every column has at least one mark — no orphan
hazards, no orphan requirements; enforced by tools/check_traceability.py at
every Gate."
```

---

## P6 — Regímenes del cage: latente → activa → limitador de daño

**Destino:** narrativa central del Cap. 8 §8.9 + defensa (hallazgo principal).
Versión conceptual; la versión con datos ya existe (`fig_cam_cage_regimes`).

```text
Create a clean academic concept figure (SVG, 16:9 landscape, flat design, white
background, sans-serif) titled "When does the safety cage matter? Three
evidence-anchored regimes".

A single horizontal axis labeled "operating condition → distance from nominal
ODD" divided into three zones (soft background tints, left to right):

ZONE 1 (teal tint #E1F5EE) — "In-ODD, nominal perception · cage LATENT":
  bullet-style annotations: "0 safety interventions in BOTH modes (M-S2 = 0)" ·
  "policy never approaches the boundary" · "only C-06 rate-smoothing active
  (43.5% of cycles)". Small icon: car centered in lane.

ZONE 2 (amber tint #FBF0DC) — "In-ODD, degraded perception · cage ACTIVE and
DECISIVE": annotations: "enforcement PASSES where monitoring FAILS:
SC-PERT-04/09/11/12/13" · "cleanest contrast SC-PERT-13 (worn markings +
image degradation): 40/40 with cage vs 0/40 without" · "the cage REMOVES
failures the bare policy commits". Small icon: car drifting, cage arrow
correcting.

ZONE 3 (coral tint #FAECE7) — "Out-of-ODD · cage = DAMAGE LIMITER":
annotations: "frontier contrast: cage removes 96–100% of road-edge contacts
(cage-dependent seed)" · "on the E-main, ALL 117 enforcement road-edge
contacts lie out-of-ODD" · "controlled stop is the designed exit, not a
failure". Small icon: car stopping before road edge.

A thin vertical dashed line labeled "ODD boundary" separates zone 2 from
zone 3. Footer: "Numbers from the F4 (1260 runs) and GE4-V2 (1970 runs)
Gazebo campaigns, seed 2024, enforcement vs monitoring."
```

---

## P7 — Familia de circuitos (aviso)

Esta la haría **con matplotlib desde los YAML de centerline**, no con una
herramienta de diseño: las formas reales (óvalo vs complex_b vs flipV) deben
salir de los datos para ser fieles a escala — una herramienta de diseño se las
inventaría. Pídemela y la genero (`scripts/` ya tiene el composer de circuitos
como referencia de geometría). Si aun así quieres una **versión esquemática**
para una slide:

```text
Create a simple schematic figure (SVG, 16:9, flat, white background) titled
"Evaluation circuits (schematic — not the real shapes)". Three top-view track
outlines side by side, neutral gray strokes:
  1. "Oval — F-track + E 425k predecessor · straights 1.5 m, curve radius
     0.8 m, perimeter ≈ 8.0 m".
  2. "complex_b — E-main training + GE4-V2 verdict · perimeter 19.22 m
     (≈2.3× oval), mixed-curvature closed loop" (draw a wavy irregular loop,
     clearly labeled as schematic).
  3. "complex_b flipV — Y-mirror, geometry-OOD generalization test
     (SC-FRONT-07)".
Add under each a small tag: world file name (lane_following_oval.world ·
lane_following_complex_b*.world · lane_following_complex_b_flipV.world).
Footer: "Laps are NOT comparable across circuits; texture variants (worn 25/50/
75%, gaps, particles) reuse the complex_b geometry."
```
