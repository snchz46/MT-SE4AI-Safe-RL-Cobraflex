# Capítulo 7 — Training Specification y Entrenamiento PPO

<!--
Estado: E-track PRIMARIO (2026-06-22). El capítulo reporta el track 'E'
(cámara end-to-end, D-41/D-43) como sistema principal; el track 'F'
(vector de estado) queda como LÍNEA BASE / brazo de control ("coste de la
percepción por cámara"), no se elimina. F quedará formalmente superado por
E cuando se ejecute la campaña GE4 sobre el E-main 297k (hoy E tiene eval
nominal; la campaña de 24 escenarios sobre 297k está pendiente, §8.9).

Convención de figuras: las figuras primarias E llevan sufijo `_newcam`
(generadas del run complex_b 297k por `tools/plot_f3_figures.py`); las
figuras F originales (fig_7_1..fig_7_6, fig_7_8) se conservan como línea
base. Artefacto A1 del V-Model adaptado (D-07, D-34): Training Specification.
-->

## 7.1 Introducción del capítulo  [BORRADOR D36]

Este capítulo produce el segundo artefacto resultante de la adaptación A1
del V-Model (D-07): la **Training Specification**. Mientras el Capítulo 5
especificó el comportamiento de la cage mediante la *Cage Specification*
(primer artefacto de A1), la Training Specification especifica las
condiciones bajo las cuales la policy RL se entrena: espacio de
observación, espacio de acción, función de recompensa, criterios de
terminación y truncación, hiperparámetros PPO, y el modo de operación de
la cage durante el entrenamiento.

El **sistema principal de la tesis es el agente end-to-end de cámara
frontal** (track 'E', D-41/D-43): una política CNN que conduce desde la
imagen cruda, con la cage leyendo su **propio estimador de carril CV
determinista** (D-43). El agente de **vector de estado** (track 'F') se
conserva como **línea base / brazo de control**: comparte toda la Training
Specification salvo la observación, de modo que el delta de resultados
**aísla el coste de la percepción por cámara**. El track 'F' está
plenamente caracterizado (campaña G4, global `SATISFIED`); el track 'E'
**superará** a 'F' como evidencia de cierre **una vez se ejecute la campaña
GE4 sobre el E-main de cámara** (hoy con evaluación nominal; §7.5, §8.9). El
capítulo reporta 'E' como primario y 'F' como baseline.

La Training Specification no es un resultado experimental: es un
*meta-diseño* que precede al primer entrenamiento y determina qué puede
y qué no puede aprender la policy. Las decisiones técnicas documentadas
aquí son responsabilidad del diseñador; la evidencia empírica de que esas
decisiones producen una policy competente es responsabilidad del
Capítulo 8.

El capítulo tiene la siguiente estructura. La sección 7.2 desarrolla la
Training Specification con sus ocho componentes (observación de cámara
como primaria; vector de estado como baseline). La sección 7.3 describe el
entorno de simulación adaptado para entrenamiento RL (circuito `complex_b`
de cámara como primario; óvalo del track 'F' como baseline). La sección
7.4 reporta los resultados del entrenamiento PPO de cámara (E-main
`complex_b` 297k) con el contraste de la convergencia del track 'F'. La
sección 7.5 evalúa la policy de cámara sobre el escenario nominal
(SC-NOM-01) contra la línea base de control clásico (CV). La sección 7.6
sintetiza y articula la transición al Capítulo 8.

---

## 7.2 Training Specification  [BORRADOR D36]

La Training Specification es el artefacto A1 del V-Model adaptado
(D-07). Se documenta aquí antes del primer entrenamiento; cualquier
modificación posterior constituye una revisión del documento y se
registra en `docs/CHANGELOG.md` con su rationale. Salvo la observación
(§7.2.1) y los detalles de red/estabilidad de §7.2.6, **los ocho
componentes son comunes a ambos tracks**: ese es el delta mínimo que
D-41/D-43 persiguen — solo cambia la fuente de percepción.

### 7.2.1 Espacio de observación

**Primario (track 'E', cámara — D-41).** La observación es la **imagen de
la cámara frontal** reescalada a **84×84 píxeles en escala de grises**
(uint8), con **frame stack k=4** aplicado por el entrenador
(`VecFrameStack`). La política es una CNN (§7.2.2) que aprende la
percepción en lugar de consumir un estado construido a mano (supersede a
D-01/ED-1 para este track). Las decisiones de codificación quedan fijadas
en E2 dentro de la envolvente que `docs/09` §10 dejó abierta:

- **Escala de grises:** la señal de carril es luminancia (líneas blancas
  sobre asfalto); el color triplica la entrada sin información de carril e
  invita a depender del eje de apariencia que la *domain randomisation* de
  H-10 varía.
- **84×84:** entrada nativa del extractor NatureCNN de SB3; a esa
  resolución las líneas (~10 mm) conservan ≥1 píxel en el campo cercano.
- **k=4:** la observación de cámara no incluye el canal `prev_steer` del
  baseline, así que las pistas de velocidad angular salen íntegramente del
  stack; se toma el extremo superior de la envolvente.

La cámara fuente es la **Lane Cam dedicada** (espejo IMX219-160, 640×360,
HFOV ≈ 90°) montada **5 cm más abajo en el frente del chasis**
(`camera_geometry` h ≈ 0,077 m, pitch 0,25 rad), compartida por la CNN de
la política y el estimador CV de la cage. Cada fotograma atraviesa el
**pipeline compartido** (`camera_pipeline.CameraPipeline`): un único punto
de degradación (estresor de escenario o *domain randomisation*) **antes de
ambos consumidores** — la causa común que D-43 acepta y documenta. La
especificación completa del pipeline, *domain randomisation*, supervisor
de percepción y Trigger 8 de C-05 está en §7.2.5 y en `docs/09` §10.

**Baseline (track 'F', vector de estado).** El brazo de control sustituye
la imagen por un vector de seis flotantes:

```text
obs = [ey, epsi, speed, prev_steer, kappa_near, kappa_far]
```

donde `ey` es el offset lateral respecto a la línea central del carril,
`epsi` el error de heading, `speed` la velocidad escalar, `prev_steer` el
steering del ciclo anterior, y `kappa_near`/`kappa_far` la **curvatura con
signo** de la línea central a dos horizontes de preview (3 y 8 segmentos).
El preview de curvatura (revisión F3, ED-7 en `docs/09`) fue necesario para
desbloquear el aprendizaje en el baseline; en el track 'E' la geometría de
la curva debe inferirse **desde la imagen** — el problema de percepción más
difícil que D-41 asume, con su coste presupuestado en datos
(Shalev-Shwartz & Shashua 2016).

### 7.2.2 Arquitectura de la política y espacio de acción

El espacio de acción es común a ambos tracks: un flotante `action =
[steering]` en [-1, 1], con velocidad fija (`fixed_speed = 0.2 m/s`)
durante el entrenamiento; el agente no controla el throttle. Esta elección
reduce la dimensionalidad del aprendizaje; si el control de velocidad
resulta necesario para los escenarios perturbados de Fase 4, la
especificación se revisa.

**Primario (E):** `CnnPolicy` de SB3 (extractor NatureCNN: conv 32@8×8/4 →
64@4×4/2 → 64@3×3/1 → FC 512, con normalización de imagen interna), sobre la
observación apilada (84×84×4 tras `VecFrameStack` + `VecTransposeImage`).
**Baseline (F):** `MlpPolicy` por defecto (dos capas de 64 `tanh`, redes
separadas pi/vf), sobre el vector de 6 dimensiones. Ambas producen salida
Gaussiana diagonal (media + `log_std` independiente del estado).

### 7.2.3 Función de recompensa

La recompensa es **idéntica en ambos tracks** y se computa sobre el estado
**ground-truth** + progreso, agnóstica a la observación:

```text
r = w_fwd · max(progress, 0)
  - w_ey  · |ey|
  - w_eps · |epsi|
  - w_ds  · |Δsteering|
  - w_term · [terminated_off_road]
```

donde `progress` es el avance **normalizado** a lo largo de la línea
central, `Δsteering` es el cambio en el steering **crudo de la política**
(no el post-cage; §7.2.5), y `[terminated_off_road]` es 1 solo si el
episodio termina por salida de **vía** (no por emergencia C-05; §7.2.4).
Los pesos nominales (sujetos a ajuste experimental) son:

| Parámetro | Valor | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Premia progreso real (≈1.0/paso a crucero) |
| `w_ey` (lateral_error) | 2.5 | Penalización principal: offset lateral |
| `w_eps` (heading_error) | 0.75 | Penalización secundaria: heading |
| `w_ds` (steer_delta) | 0.20 | Suavidad de actuación (sobre Δsteering **crudo**, v1.2; §7.2.5) |
| `w_term` (termination) | 25.0 | Desincentiva salida de vía |

El término forward usa **progreso normalizado** (no velocidad): como la
velocidad es fija, un término `w_fwd·speed` sería una constante que no
discrimina la conducta y dejaba `explained_variance ≈ 0` (revisión F3,
primer run). La penalización de terminación alta (25.0) prioriza la
permanencia en **vía**; **solo** la salida de vía la aplica — la emergencia
C-05 termina sin penalización (la intervención de la cage es dinámica, no
castigo; D-34, §7.2.4). Los pesos son `[provisional, M-P1..M-P4]`; detalle
en `docs/10_reward_function.md`.

### 7.2.4 Criterios de terminación y truncación

Comunes a ambos tracks. **Terminación** (`terminated=True`) en dos
condiciones: (1) **salida de vía** `|ey| > road_width/2` — única condición
que aplica `w_term`; se termina en el borde de **vía**, no de carril, para
que una policy inicial aleatoria acumule experiencia útil (la cage corrige
las violaciones de **carril** C-01/C-03 dentro de la vía); (2)
**emergencia C-05** — el rollout ya falló (coche congelado), se trata como
fallo terminal **sin penalización** (castigar la cage contradiría D-34).
`info["termination_reason"] ∈ {off_road, cage_emergency, truncated}`.

**Truncación** (`step_count ≥ max_episode_steps`). Con `max_episode_steps`
= 1024 y `control_dt = 0.10 s` el episodio dura ≈ 102 s. En el track 'E'
sobre `complex_b` el horizonte resultó adecuado: la policy de cámara
aprende a recorrer episodios casi completos (`ep_len_mean` ≈ 791 en el pico,
§7.4.1). Implementación en `GazeboLaneEnv.step`; rationale en `docs/09`
(ED-4/ED-8) y D-34.

### 7.2.5 Cage durante el entrenamiento

La cage opera en modo `enforcement` durante todo el entrenamiento, **en
ambos tracks** (D-34). `GazeboLaneEnv` invoca **en proceso** la misma clase
`SafetyCageNode` —con el mismo `cage/cage.yaml` (v0.6.1)— que el nodo de
despliegue envuelve por tópicos, por determinismo y para que el
comportamiento de la cage sea idéntico al de despliegue. La acción segura
se mapea a `/cmd_vel` replicando `vehicle_control_node`. La recompensa se
calcula sobre la acción segura y el estado resultante, **con una excepción
deliberada: el término de suavidad `w_ds·|Δsteering|`** (reward v1.2) se
computa sobre el `Δsteering` **crudo** (pre-cage) y con peso subido
(`w_ds = 0.10 → 0.20`), para que la política pague su propio jerk en lugar
de delegarlo gratis en C-06 (el rate-limiter). El cableado puro y libre de
ROS reside en `cobraflex_rl/cage_bridge.py`.

**Fuente del estado de la cage (track 'E', D-43).** Lo que cambia en el
track de cámara es la **fuente del estado de la cage**: el supervisor de
percepción (`cage_perception.CagePerceptionSupervisor`) compone el
**estimador CV determinista** con el monitor de salud (SR-013) y el chequeo
de plausibilidad/consistencia temporal (SR-014); cuando el estimado es
aceptable produce el `State` de la cage, y cuando la percepción se pierde o
es sospechosa levanta el **Trigger 8 de C-05** (parada controlada en lazo
abierto). Ni ground truth ni la CNN de la política: así cage y política
generalizan a cualquier vía con líneas visibles. El ground truth queda
confinado a recompensa, terminación y métricas. Presupuestos al ciclo de
10 Hz: `staleness_max_s = 0.5 s`, persistencia del supervisor 4 ciclos;
en cada reset el supervisor se ceba (*priming*) sobre la vista de spawn.
En el **baseline (F)** la cage lee el estado del tracker ground-truth
directamente. Tarea TS-01 de F3, implementada.

### 7.2.6 Hiperparámetros PPO

La tabla lista la configuración **efectiva completa**. La columna E-main es
la del run de cámara `ppo_newcam_complex_b_2024_1M`; la baseline F es la del
run de estado `ppo_train_2024_200k`.

| Parámetro | E-main (cámara) | Baseline (F, estado) | Fuente / nota |
| --- | --- | --- | --- |
| `policy` | **CnnPolicy** | MlpPolicy | red de la política |
| `total_timesteps` | 1 000 000 (plan; parado ≈662k) | 200 000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴, **anneal lineal** | 3×10⁻⁴ constante | E: `lr_schedule: linear` |
| `target_kl` | **0.5** | — (sin freno) | E: freno de región de confianza (§7.4.1) |
| `normalize_reward` | **True** (`VecNormalize`) | False | E: estabiliza el crítico (§7.4.1) |
| `clip_range_vf` | **0.2** | null | E: clip del valor sobre recompensa normalizada |
| `gamma` | 0.99 | 0.99 | = SB3 default |
| `n_steps` | 1 024 | 1 024 | ≈ 1 episodio |
| `batch_size` | 64 | 64 | = SB3 default |
| `n_epochs` | 10 | 10 | SB3 default |
| `gae_lambda` | 0.95 | 0.95 | SB3 default |
| `clip_range` | 0.2 | 0.2 | SB3 default |
| `ent_coef` | 0.0 | 0.0 | sin bonus de entropía |
| `vf_coef` | 0.5 | 0.5 | SB3 default |
| `max_grad_norm` | 0.5 | 0.5 | SB3 default |
| `device` | auto (CUDA si existe) | cpu | E: la CNN aprovecha GPU |

Los **cuatro levers de estabilidad** del E-main (`target_kl`, anneal lineal
de LR, `VecNormalize(norm_reward)` y `clip_range_vf`) **no** existen en el
baseline F: se añadieron tras observar que PPO sobre CNN con randomización
visual es marcadamente menos estable que sobre el vector de estado (§7.4.1).
`norm_obs` se mantiene **False**, de modo que la evaluación/inferencia no se
ve afectada y `ep_rew_mean` en la curva queda **cruda** (comparable con el
baseline). El presupuesto de cámara es **≥ 1M pasos** (D-41 acepta la mayor
demanda de datos del extremo a extremo); un piloto de ~20k valida el bucle
antes de comprometer el presupuesto.

### 7.2.7 Semillas y reproducibilidad

Semilla principal **2024** en ambos tracks (precedente D-36). El **baseline
F** está caracterizado con **N = 5** (seeds 42, 123, 2024, 23, 666), que
revela dos cuencas de convergencia (*constraint-respecting* vs
*cage-dependent*, §7.5.3). El **E-main de cámara** se reporta sobre la
semilla 2024; su **multi-seed N=5** (misma batería) está **en curso — 2 de 5
hechas (2024, 42), 3 pendientes** (coste de cómputo por el límite de tiempo-real
de la cámara, §7.2.8). El contraste por-semilla se desarrolla en §7.5.3.

### 7.2.8 Checkpoints y registro

Los checkpoints se guardan cada `n_steps` pasos (denominación SB3
`cobraflex_ppo_lane_<N>_steps.zip`); un *peak* puede seleccionarse post-hoc
(§7.4.1). Cada run registra en `experiments/sim/training/<run_id>/`:
`learning_curve.csv` (una fila por rollout: `ep_rew_mean`, `ep_len_mean`,
salud de PPO `explained_variance/value_loss/entropy/approx_kl/clip_fraction/std`
y actividad del cage `intervention_rate/emergency_rate/int_rate_C-0x`),
`action_samples.csv` (steering crudo submuestreado) y `metadata.json`
(commit, hashes de cage/escenario/checkpoint, semilla, hiperparámetros, y —
track 'E'— clase de política, bloque de observación y envolvente de DR). La
instrumentación reside en `cobraflex_rl/callbacks.py` y el módulo puro
`cobraflex_rl/training_metrics.py`. Restricción operativa del track 'E': con
cámara el simulador queda ligado a tiempo real (la renderización a RTF > 1
deja sin atender los servicios de gz), de modo que el coste de pared es
≈ control_dt por paso (~8 FPS).

---

## 7.3 Entorno de simulación para entrenamiento RL  [BORRADOR D36]

**Primario (track 'E'): el circuito `complex_b`.** El entrenamiento de
cámara se ejecuta sobre el circuito **`complex_b`** — un trazado sinuoso
que **se aproxima a sí mismo** (perímetro **19,22 m**, 2,2× el óvalo del
baseline), elegido para forzar generalización geométrica de la percepción.
La terminación fuera de vía se juzga por la distancia global a la línea
**centro-de-vía** vs `road_width/2` (robusta donde el circuito se aproxima
a sí mismo y el `ey` estático colapsa; `--road-centerline-config`, §3.5 de
`docs/11`).

**Baseline (track 'F'): el óvalo.** El brazo de control se entrena sobre
`lane_following_oval.world` (perímetro 8,79 m), el mismo mundo de la
validación F2.

Tres adaptaciones comunes para el ciclo RL: (1) **reloj de simulación** —
*headless* y sin pausa; en el track de estado RTF 2–4×, en el de cámara
RTF ≈ 1 (ligado al render, §7.2.8); (2) **reset de episodio** por
teletransporte (`/world/<world>/set_pose`), detectado como warp por el
tracker; (3) **perturbación de spawn** — heading `[-0.15, +0.15] rad` y
lateral `[-0.05, +0.05] m` por episodio, para diversidad de estados de
arranque (rangos `[provisional, M-P5]`).

---

## 7.4 Resultados del entrenamiento

**E-main (cámara):** run `ppo_newcam_complex_b_2024_1M` (seed 2024,
`CnnPolicy`, DR p=0,5 nivel 0,2–0,8, los cuatro levers de estabilidad de
§7.2.6), sobre `complex_b`. Plan de 1M pasos, **parado manualmente a ≈ 662k**
por degradación tardía (abajo). Datos crudos:
`experiments/sim/training/ppo_newcam_complex_b_2024_1M/learning_curve.csv`
(647 iteraciones); checkpoint-en-pico verificado
(`cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip`, hash `44c8e912…`,
`num_timesteps == 296960`). El **baseline F** (`ppo_train_2024_200k`, seed
2024, estado, reward v1.2) se reporta al final de la sección como contraste.

### 7.4.1 Curva de convergencia y estabilidad (E-main)

`ep_rew_mean` asciende de ~14 (1k) hasta un **pico de ≈ 822,9 en el paso
≈ 297k** (`ep_len_mean` ≈ 791, cerca del tope de 1024 → episodios casi
completos) y **mantiene la banda 700–800 hasta ~450k** (Figura 7.1, **recortada
en 450k**: ~770 en la última iteración mostrada). El run se detuvo manualmente
más tarde, tras un **colapso de exploración posterior a ~450k** (`ep_rew_mean`
cae a ~113 hacia 662k al sobre-recocerse el `std`, 0,034 → 0,018); ese tramo es
**irrelevante para la policy desplegada** —el checkpoint-en-pico (§7.4.3) es del
paso 297k, muy anterior— y se **omite de las figuras de entrenamiento** por no
informar sobre el agente evaluado.

<img src="../figures/fig_7_1_convergence_newcam.png" alt="Figura 7.1 — Curva de convergencia del entrenamiento de cámara (complex_b 297k): ep_rew_mean y ep_len_mean vs timesteps." width="560"/>

*Figura 7.1 — Convergencia del E-main de cámara (run `ppo_newcam_complex_b_2024_1M`,
seed 2024): `ep_rew_mean` y `ep_len_mean` vs timesteps (crudo + suavizado).
Pico ≈ 822,9 @ ≈ 297k y meseta 700–800 hasta el corte en **~450k**; el colapso
de exploración posterior a ~450k (que motivó el paro manual) se omite por
irrelevante para la policy desplegada — de ahí la selección de
**checkpoint-en-pico** (297k). Generada por `tools/plot_f3_figures.py`.*

**Decaimiento tardío = colapso de exploración, no del crítico.**
Crucialmente, `value_loss` permanece **minúsculo** (~0,003–0,07) durante
todo el run —incluido el tramo posterior a 450k omitido de las figuras—: no es
la inestabilidad de la función de valor de iteraciones previas, sino contracción
de exploración una vez el `std` anela. Por eso **el pico es la política a conservar** (checkpoint-en-pico) y
el decaimiento posterior no contamina el checkpoint del paso 297k. Los
cuatro levers de §7.2.6 nacen precisamente de domar la inestabilidad del
PPO de cámara: `target_kl = 0,5` frena la actualización cuando un minibatch
excede 1,5× ese valor (un piloto previo de `complex_b` colapsó a ~105k con
`approx_kl` desbocado a ~2,7 sin freno de región de confianza);
`VecNormalize(norm_reward)` + `clip_range_vf` mantienen los objetivos del
crítico ~O(1) (sin ellos el crítico perseguía retornos ~700–800 y la curva
hacía dientes de sierra hasta dígitos sueltos).

### 7.4.2 Co-adaptación policy–cage (E-main)

La tasa de intervención del cage **decrece de ~87 % (inicio) a ~40 %** (en el
corte de ~450k), **dominada por C-06** (el rate-limiter), con las reglas de seguridad
(C-01/C-03) cayendo a ~0 (Figura 7.2). Es decir: la policy aprende a
**respetar las constraints de seguridad** (no se acerca al borde), pero su
steering crudo sigue siendo a tirones y C-06 lo suaviza de forma continua —
un comportamiento benigno coherente con la evaluación (§7.5: 43 % C-06, 0
emergencias). La entropía decae de forma gradual (Figura 7.3), sin colapso
prematuro de la exploración hasta el sobre-recocido tardío.

<img src="../figures/fig_7_2_intervention_newcam.png" alt="Figura 7.2 — Actividad del cage durante el entrenamiento de cámara y desglose por regla vs timesteps." width="560"/>

*Figura 7.2 — Actividad del cage durante el entrenamiento de cámara (run
`ppo_newcam_complex_b_2024_1M`): tasa de intervención global + emergencia C-05
(arriba) y desglose por regla C-01..C-06 (abajo). La intervención cae de ~87 %
a ~40 % **dominada por C-06**; C-01/C-03 caen a ~0 (la policy se vuelve
constraint-respecting en seguridad, pero su jerk lo absorbe el rate-limiter).
Curva recortada en ~450k. Generada por `tools/plot_f3_figures.py`.*

<img src="../figures/fig_7_3_ppo_health_newcam.png" alt="Figura 7.3 — Value loss y entropía de la política de cámara vs timesteps." width="560"/>

*Figura 7.3 — Salud interna de PPO (cámara): value loss (azul) y entropía
(naranja) vs timesteps (recortada en ~450k). El `value_loss` se mantiene
minúsculo en todo el tramo mostrado (y también en el posterior omitido) —
la estabilización por `VecNormalize`/`clip_range_vf` funciona; el decaimiento
tardío de recompensa es exploración, no el crítico. Generada por
`tools/plot_f3_figures.py`.*

<img src="../figures/fig_7_4_action_distribution_newcam.png" alt="Figura 7.4 — Distribución del steering crudo de la política de cámara, inicio vs fin." width="560"/>

*Figura 7.4 — Distribución de la acción (steering crudo) al inicio vs al
final del entrenamiento de cámara. Generada por `tools/plot_f3_figures.py`.*

### 7.4.3 La inestabilidad del PPO de cámara como hallazgo de track

El contraste con la convergencia **monótona** del baseline de estado
(§7.4.4) es un **hallazgo del track**: **PPO sobre CNN con randomización
visual es marcadamente menos estable** que sobre el vector de 6 dimensiones.
La evolución de la cámara lo confirma a lo largo de tres runs principales:
la cámara frontal original (ZED) colapsó tras un pico de 288,5 @ 139k; la
*Lane Cam* sobre óvalo (`ppo_newcam_train_2024_750k`) alcanzó 335,6 @ 425k y
degradó; y este run de `complex_b` alcanza 822,9 @ 297k con los levers de
estabilidad antes de degradar. En los tres, la **política de checkpoints
periódicos (cada 1024 pasos) pasa de conveniencia a necesidad** y la
selección por **checkpoint-en-pico** es la norma. La recompensa **no es
comparable entre circuitos** (el integral de recompensa de `complex_b`
—perímetro mayor, geometría más cerrada— difiere del óvalo): 822,9 no dice
nada por sí solo sobre la calidad de conducción; eso lo establece la
evaluación de §7.5.

### 7.4.4 Línea base (track 'F', vector de estado) — contraste

El run de estado `ppo_train_2024_200k` (seed 2024, 200k, reward v1.2)
**converge de forma monótona**: `ep_rew_mean` 20,9 → **536,8**,
`ep_len_mean` → **500** (horizonte completo hacia ~75k), `explained_variance`
cierra en **0,67**. La intervención del cage cae de ~90 % a ~3,4 % (caída
mucho más profunda que la del track de cámara: el estado perfecto permite a
la policy emitir steering **nativamente suave**, |Δraw| medio 0,030, y C-06
queda casi inactivo). Esta convergencia limpia es exactamente el baseline
contra el que se mide la inestabilidad del track de cámara (§7.4.3). Las
figuras del baseline de estado se conservan como `fig_7_1_convergence.png`,
`fig_7_2_intervention.png`, `fig_7_3_ppo_health.png` y
`fig_7_4_action_distribution.png` (sufijo sin `_newcam`).

---

## 7.5 Evaluación sobre SC-NOM-01

**Primario (E-main de cámara).** Policy evaluada: checkpoint del pico
`cobraflex_ppo_newcam_complex_b_2024_297k_peak.zip` (seed 2024). Runs de
evaluación `rl_newcam_eval_2024_cb297k_4k4` (enforcement) y `…_mon`
(monitoring): un episodio determinista (spawn sin perturbación, §7.3),
horizonte 4 400 pasos = 440 s, DR desactivada (el único estresor visual
legítimo en evaluación es el del escenario), sobre `complex_b`. La línea
base de comparación es el **controlador clásico CV** (pure-pursuit sobre el
mismo estimador CV determinista, misma vía y cámara): run
`cv_ctrl_eval_newcam_4k4`.

### 7.5.1 Completion rate, tracking y comparación con la base CV

| Métrica (SC-NOM-01, `complex_b`) | CV pure-pursuit (enf) | **RL 297k (enf)** | RL 297k (mon) |
| --- | --- | --- | --- |
| Vueltas completadas | 4,85 | 4,88 | 4,89 |
| media \|ey\| | 17,2 mm | **10,9 mm** | 12,9 mm |
| máx \|ey\| | 57,3 mm | 48,2 mm | 46,2 mm |
| media \|epsi\| | 0,025 rad | 0,028 rad | 0,030 rad |
| Emergencias C-05 | 0 | **0** | 0 |
| Intervención cage | 0 % | 43,5 % (solo C-06) | 45,7 % (solo C-06) |

Evidencia: `experiments/sim/runs/rl_newcam_eval_2024_cb297k_4k4{,_mon}/` y la
comparación consolidada `experiments/sim/runs/baseline_cv_vs_rl_nominal.json`.

**Lectura.** **El agente RL de cámara bate al baseline CV en precisión de
tracking** — 10,9 vs 17,2 mm de media \|ey\| (~37 % más ajustado), a la misma
distancia (~94 m) y con **0 emergencias** en ambos. Esto **invierte el
hallazgo del óvalo** (donde el CV clásico era el más preciso): sobre la
geometría sinuosa y auto-aproximante de `complex_b` el punto de mira del
pure-pursuit se degrada mientras la CNN sostiene la línea — la primera
evidencia nominal de que el agente aprendido justifica su coste frente al
baseline clásico. **Las vueltas no son comparables entre circuitos**
(`complex_b` 19,22 m vs óvalo 8,79 m): la fila CV de la misma pista es la
única comparación de vueltas justa, y la distancia recorrida (~94 m) iguala
a las 11,16 vueltas del eval sobre óvalo (~98 m).

<img src="../figures/fig_7_5_trajectory_newcam.png" alt="Figura 7.5 — Trayectoria de la policy de cámara sobre complex_b." width="460"/>

*Figura 7.5 — Trayectoria del E-main de cámara sobre `complex_b` (run
`rl_newcam_eval_2024_cb297k_4k4`), ciñéndose a la línea central del carril en
el trazado sinuoso. Generada por `tools/plot_f3_figures.py`.*

<img src="../figures/fig_7_6_tracking_error_newcam.png" alt="Figura 7.6 — Error lateral RL de cámara vs CV baseline sobre complex_b." width="600"/>

*Figura 7.6 — Error lateral \|ey\| sobre `complex_b`: RL de cámara (azul) vs
CV pure-pursuit baseline (rojo), warm-up de 0.3 vueltas recortado. El eje x es la
distancia **acumulada** (vueltas), no la `s` por-vuelta. El RL se mantiene en
banda más estrecha que el CV, ambos muy por debajo del medio-carril (122 mm).
Generada por `tools/plot_f3_figures.py --cv-run`.*

### 7.5.2 Comportamiento cualitativo: la cage queda latente

Tres observaciones del log por-paso (`cage_status.csv`):

1. **Tracking más fino que la base clásica.** El RL centra el vehículo con
   ~37 % menos error lateral que el CV (10,9 vs 17,2 mm), sostenido a lo
   largo de la corrida.
2. **La cage queda latente in-ODD en ambos modos.** **0 emergencias** y
   **ninguna** activación de C-01/C-02/C-03/C-05 — **solo C-06** (el
   rate-limiter) dispara (43–46 %). Enforcement y monitoring dan vueltas y
   \|ey\| casi idénticos (4,88 vs 4,89; 10,9 vs 12,9 mm): la policy se mantiene
   por sí misma dentro de la envolvente de seguridad y la cage no actúa sobre
   seguridad. Es la **firma del track 'F'** recuperada — y, a diferencia de
   checkpoints de cámara previos (la parada de curva SR-014/Trigger-8 del
   139k), aquí ocurre sobre un circuito **más difícil**.
3. **El coste es la suavidad, no la seguridad.** El RL dispara C-06 en
   43–46 % de los pasos (la CNN comanda steering a tirones que el limitador
   suaviza, intervención **benigna**) frente al 0 % del CV. La actuación es
   **más ajustada pero más a tirones** que la del CV; C-06 absorbe el jerk
   sin dañar la precisión (el \|ey\| de enforcement es incluso ligeramente
   mejor que el de monitoring).

> **Alcance: eval nominal, no campaña GE4.** Esta evaluación establece la
> **competencia in-ODD** del E-main de cámara. El head-to-head bajo
> perturbación/degradación (la campaña GE4 de 24 escenarios) **no** se ha
> re-ejecutado sobre el 297k: el §8.9 del Cap. 8 y `docs/07` reportan todavía
> la campaña GE4 sobre el checkpoint **139k** (política superada). La
> propiedad de **seguridad** de la cage (0 salidas de carril → parada segura)
> es independiente de la policy; la **magnitud del coste de disponibilidad**
> bajo perturbación queda por medir sobre 297k — el paso de cierre que
> formalmente hará que el track 'E' supere al 'F'.

<img src="../figures/fig_7_7_gazebo_capture.png" alt="Figura 7.7 — Captura de la evaluación en Gazebo bajo el cage." width="640"/>

*Figura 7.7 — Captura representativa del lane-following bajo el cage: vista de
Gazebo (vehículo 1:14) y RViz (modelo del robot y frames TF). La vista no
depende del checkpoint.*

### 7.5.3 Variabilidad entre semillas (track 'E' cámara — en curso; baseline F)

**Multi-seed de cámara (en curso, N = 5 previsto).** Replicando el protocolo del
baseline F, el E-main se entrena sobre la batería **{2024, 42, 23, 666, 123}**
(la misma que F, para que el contraste E↔F sea comparable, §7.2.7). Hechas **2 de
5** (2024, 42); faltan 3. Ambas semillas **colapsan tarde por contracción de
exploración** (2024 tras ~490k, 42 tras ~410k) → selección por
**checkpoint-en-pico**, con notable **variabilidad de semilla en la altura y el
momento del pico** (2024: 822,9 @ ~297k; 42: 720,2 @ ~120k). El **eval nominal
SC-NOM-01** de cada peak fija las columnas de evaluación; **2024 y 42 están
evaluadas** (enforcement; faltan las 3 restantes, pendientes de Gazebo).

| Métrica (track 'E', `complex_b`) | Seed 2024 | Seed 42 | Seed 23 | Seed 666 | Seed 123 |
| --- | --- | --- | --- | --- | --- |
| **Cuenca** | c-respecting | c-respecting | TBD | TBD | TBD |
| `ep_rew_mean` (pico) | **822,9** | **720,2** | TBD | TBD | TBD |
| Paso del checkpoint | 296 960 | 124 928 | TBD | TBD | TBD |
| Intervención (fin sano, C-06) | ~40 % (@450k) | ~41 % (@400k) | TBD | TBD | TBD |
| Intervención cage (**eval**) | 43,5 % (solo C-06) | 64,9 % (solo C-06) | TBD | TBD | TBD |
| `mean \|ey\|` (**eval**) | 10,9 mm | 13,3 mm | TBD | TBD | TBD |
| `max \|ey\|` (**eval**) | 48,2 mm | 41,6 mm | TBD | TBD | TBD |
| Emergencias C-05 (**eval**) | 0 | 0 | TBD | TBD | TBD |
| Vueltas (**eval**) | 4,88 | 4,91 | TBD | TBD | TBD |

**Lectura (2024 vs 42).** Las dos semillas evaluadas **confirman
*constraint-respecting***: 0 emergencias, **sin C-01/C-03/C-05** (cage latente en
seguridad), solo C-06; y **ambas baten al CV** en tracking (10,9 y 13,3 mm vs
17,2 mm). La diferencia es de **suavidad**: la 42 dispara C-06 el **64,9 %** de los
pasos (vs 43,5 % de la 2024) — más a tirones, coherente con su pico más bajo y
temprano (720 @ ~120k vs 822 @ ~297k) y menos refinado. La cuenca se mantiene
estable entre semillas en lo que importa para seguridad; lo que varía es el coste
(benigno) de rate-limiting de C-06.

<img src="../figures/fig_7_8_multiseed_newcam.png" alt="Figura 7.8 — Comparación multi-semilla del track de cámara (seeds 2024 y 42)." width="560"/>

*Figura 7.8 — Multi-semilla del **track de cámara** (seeds 2024 y 42; recortadas
en su tramo sano ~450k / ~400k): `ep_rew_mean` (arriba) e intervención del cage
(abajo) vs timesteps. Ambas son *constraint-respecting* en seguridad (C-01/C-03
≈ 0; la intervención es C-06). Pendientes las 3 semillas restantes; la tabla se
completará con sus evals. Generada por `tools/plot_f3_figures.py --seed-runs`.*

**Línea base (track 'F', estado) — la referencia que estableció las cuencas.**
Las cinco semillas del baseline F revelan **dos cuencas**: cuatro
*constraint-respecting* y una (123) *cage-dependent* (curvas en
`fig_7_8_multiseed.png`, Fig. 7.8b).

| Métrica (baseline F, estado) | Seed 42 | Seed 2024 | Seed 23 | Seed 666 | Seed 123 |
| --- | --- | --- | --- | --- | --- |
| **Cuenca** | c-respecting | c-respecting | c-respecting | c-respecting | **cage-dependent** |
| Tasa de intervención (eval) | 0,02 % | 0 % | 0 % | 1,55 % | **58,8 %** |
| `mean \|ey\|` (eval) | 11,6 mm | 9,9 mm | 6,7 mm | 8,0 mm | **90,7 mm** |
| `max \|ey\|` (eval) | 27 mm | 23 mm | 22 mm | 26 mm | **145 mm** |
| Emergencias C-05 | 0 | 0 | 0 | 0 | 0 |

**Por qué importa.** En el baseline F la seed 123 es la evidencia de utilidad del
cage que el escenario nominal de las *constraint-respecting* no puede dar: una
policy *peor* que el cage mantiene **segura y dentro de la vía** (C-01/C-03
disparan activamente; sin cage abandonaría el carril). El valor del cage
**depende de la policy** — latente cuando la policy basta (el E-main de cámara en
nominal, §7.5.2), protector activo cuando no. La fuerza que empuja hacia
*constraint-respecting* es el término de suavidad `w_ds` (§7.2.5), suficiente para
4/5 semillas del baseline F; el multi-seed de cámara dirá si se sostiene también
bajo percepción. El análisis de sensibilidad de `w_ds` es del Capítulo 8 (tag
`[provisional, M-P4]`).

---

## 7.6 Síntesis y transición al Capítulo 8  [BORRADOR D36]

Este capítulo ha producido la Training Specification (artefacto A1 del
V-Model) y la primera evidencia empírica de que una policy PPO **de cámara
end-to-end** puede aprender lane-following: el E-main `complex_b` 297k
conduce con ~11 mm de error lateral, **bate al baseline de control clásico
(CV)** y mantiene la cage **latente** en nominal, sobre un circuito sinuoso.
El brazo de control de estado (track 'F') queda como baseline plenamente
caracterizado que aísla el coste de la percepción.

La Training Specification es un documento de diseño, no de evaluación. Que
la policy converja en entrenamiento no valida que cumpla los Safety
Requirements: esa validación es el objeto del Capítulo 8, que introduce la
*scenario library* como instrumento — la policy se evalúa sobre todos los
escenarios (SC-NOM/EDGE/PERT/FRONT) con las métricas M-S/M-P/M-I/M-C de
`docs/06`. La campaña **GE4 sobre el E-main de cámara 297k** es el paso de
cierre pendiente: cuando se ejecute, el track 'E' superará formalmente al
'F' como evidencia de veredicto (hoy el §8.9 reporta la campaña GE4 sobre el
checkpoint 139k). La comparación sistemática RL+cage vs CV+cage —y el
contraste E↔F como coste de la percepción— es el resultado experimental
central de la tesis.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

E-track (primario):
  [x] E-main de cámara complex_b 297k: training + eval nominal SC-NOM-01
      (enf+mon) — cage latente, bate al baseline CV (§7.4–7.5)
  [x] Figuras E (convergencia, co-adaptación, salud PPO, acción, trayectoria,
      tracking) generadas del run complex_b (sufijo _newcam)
  [ ] Campaña GE4 sobre el E-main 297k (24 escenarios) — pendiente; al
      ejecutarse, track 'E' supera a 'F' como evidencia de veredicto (§8.9)
  [ ] Multi-seed N=5 de cámara — diferido (restricción de tiempo-real, §7.2.8)

Baseline F (conservado):
  [x] Caracterizado: 200k estado, N=5 semillas, campaña G4 SATISFIED

Fase 6 (consolidación):
  [ ] Pulido de prosa; coherencia §7.2.3 (pesos) con sensibilidad del Cap. 8
-->
