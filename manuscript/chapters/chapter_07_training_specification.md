# Capítulo 7 — Training Specification y Entrenamiento PPO

<!--
Estado: ESQUELETO F3 (D36+).
Extensión objetivo: 10–14 páginas.
Convención: secciones marcadas [BORRADOR D3X] tienen prosa fijada.
Las marcadas [COMPLETAR FASE 3] dependen de resultados medidos durante
el entrenamiento (curvas de convergencia, métricas de evaluación,
número de timesteps, completion rate del RL).
Las marcadas [PULIDO FASE 6] requieren retoque estilístico al cierre.

Artefacto A1 del V-Model adaptado: Training Specification.
Debe existir antes del primer entrenamiento (D-07, D-34).
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

La Training Specification no es un resultado experimental: es un
*meta-diseño* que precede al primer entrenamiento y determina qué puede
y qué no puede aprender la policy. Las decisiones técnicas documentadas
aquí son responsabilidad del diseñador; la evidencia empírica de que esas
decisiones producen una policy competente es responsabilidad del
Capítulo 8.

El capítulo tiene la siguiente estructura. La sección 7.2 desarrolla la
Training Specification propiamente dicha, con sus ocho componentes. La
sección 7.3 describe el entorno de simulación adaptado para entrenamiento
RL. La sección 7.4 reporta los resultados del entrenamiento PPO
definitivo. La sección 7.5 evalúa la policy entrenada sobre el
escenario nominal (SC-NOM-01) para establecer una línea base de
rendimiento. La sección 7.6 sintetiza y articula la transición al
Capítulo 8.

---

## 7.2 Training Specification  [BORRADOR D36]

La Training Specification es el artefacto A1 del V-Model adaptado
(D-07). Se documenta aquí antes del primer entrenamiento; cualquier
modificación posterior constituye una revisión del documento y se
registra en `docs/CHANGELOG.md` con su rationale.

### 7.2.1 Espacio de observación

El vector de observación es un array de seis flotantes:

```text
obs = [ey, epsi, speed, prev_steer, kappa_near, kappa_far]
```

donde `ey` es el offset lateral respecto a la línea central del carril
(positivo a la izquierda), `epsi` es el error de heading respecto a la
tangente de la línea central (positivo en sentido antihorario), `speed`
es la velocidad escalar del vehículo en m/s, `prev_steer` es el
steering aplicado en el ciclo anterior (normalizado en [-1, 1]), y
`kappa_near`/`kappa_far` son la **curvatura con signo** de la línea
central (rad/m, positiva a la izquierda) a dos horizontes de preview
(3 y 8 segmentos por defecto).

Los límites del espacio son [-∞, +∞] para `ey`, `speed`, `kappa_near` y
`kappa_far`, [-π, π] para `epsi`, y [-1, 1] para `prev_steer`. En la
práctica, el rango operativo es estrecho: ey ∈ [-0.12, 0.12] m,
epsi ∈ [-0.4, 0.4] rad (ver §6.6.2), |kappa| ≤ 1.25 rad/m (R=0.8 m).

La inclusión de `prev_steer` es una forma ligera de memoria de primer
orden que ayuda al agente a regularizar su comportamiento de steering sin
requerir una arquitectura recurrente. El `speed` es información necesaria
para la calibración de la corrección de heading en curva.

**Preview de curvatura (revisión F3, primer run).** El vector original
de cuatro componentes era puramente reactivo: el agente solo veía
`ey/epsi` actuales y no la curva que se aproxima. En el primer run de
entrenamiento esto bloqueó el aprendizaje — en la curva de R=0.8 m, sin
anticipación, el agente derivaba hasta que la cage tomaba el control
(C-01/C-03) y disparaba C-05, con señal de crédito casi nula
(`explained_variance ≈ 0`). La cage **ya** consumía `curvature_ahead`
internamente; exponerla también a la política (`kappa_near`, `kappa_far`)
le permite anticipar la curva. Con el preview, el agente pasó a completar
vueltas y terminar por truncación. Decisión (ED-7) en
`docs/09_environment_design.md`.

### 7.2.2 Espacio de acción

El espacio de acción es un array de un flotante: `action = [steering]`
en [-1, 1]. La velocidad es fija (`fixed_speed = 0.2 m/s`) durante el
entrenamiento; el agente no controla el throttle. Esta elección reduce
la dimensionalidad del problema de aprendizaje: en la Fase 2 el PD con
velocidad fija ya produce comportamiento estable, por lo que no hay
evidencia de que el agente RL necesite control de velocidad para el
escenario nominal. Si el control de velocidad resulta necesario para los
escenarios perturbados de Fase 4, la Training Specification se revisa.

### 7.2.3 Función de recompensa

La función de recompensa en un ciclo de control es:

```text
r = w_fwd · max(progress, 0)
  - w_ey  · |ey|
  - w_eps · |epsi|
  - w_ds  · |Δsteering|
  - w_term · [terminated_off_road]
```

donde `progress` es el avance **normalizado** a lo largo de la línea
central en ese ciclo (≈1.0 a velocidad de crucero; el entorno gestiona el
wrap del arco en el circuito cerrado), `Δsteering` es el cambio en el
steering **crudo de la política** (no el post-cage; ver §7.2.5), y
`[terminated_off_road]` es 1 solo si el episodio termina por salida de
**vía** (no por emergencia C-05; ver §7.2.4). Los pesos nominales (sujetos
a ajuste experimental) son:

| Parámetro | Valor | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Premia progreso real (≈1.0/paso a crucero) |
| `w_ey` (lateral_error) | 2.5 | Penalización principal: offset lateral |
| `w_eps` (heading_error) | 0.75 | Penalización secundaria: heading |
| `w_ds` (steer_delta) | 0.20 | Suavidad de actuación (sobre Δsteering **crudo**, v1.2; ver §7.2.5) |
| `w_term` (termination) | 25.0 | Desincentiva salida de vía |

**Progreso, no velocidad (revisión F3, primer run).** El término forward
originalmente era `w_fwd · speed`. Como la velocidad es fija (crucero
cage-controlado), ese término era una constante ≈0.2 que no discriminaba
la conducta de la política: el retorno apenas dependía de las acciones, lo
que dejaba `explained_variance ≈ 0` y el aprendizaje plano. Sustituirlo
por el **progreso normalizado a lo largo del centerline** hace que el
retorno premie sobrevivir y avanzar más (completar curvas/vueltas) — la
señal que el agente sí puede optimizar. Además mantiene cada paso en pista
**netamente positivo**, de modo que terminar pronto (vía la emergencia
C-05 sin penalización, §7.2.4) nunca renta más que continuar.

El diseño de recompensa es deliberadamente simple. La penalización de
terminación alta (25.0) prioriza la permanencia en **vía** sobre la
optimización de velocidad; nótese que **solo** la salida de vía la aplica
— la emergencia C-05 termina sin penalización (la intervención de la cage
es dinámica, no castigo; D-34, §7.2.4/§7.2.5).

Los pesos son `[provisional, M-P1..M-P4]` — se marcan provisionalmente
hasta que el análisis de sensibilidad del Capítulo 8 confirme que no hay
degeneración. Detalle y banco de preguntas en `docs/10_reward_function.md`.

### 7.2.4 Criterios de terminación y truncación

**Terminación** (episodio falla): el episodio termina (`terminated=True`)
en cualquiera de dos condiciones:

1. **Salida de vía**: `|ey| > road_width / 2`. Se termina en el borde de
   vía y no en el de carril (`lane_width/2`) por una razón deliberada de
   entrenamiento: una policy inicial aleatoria saldría del carril en 1–2
   pasos y nunca acumularía experiencia útil. La cage corrige las
   violaciones de **carril** dentro de la vía (C-01/C-03); terminar en el
   borde de **vía** marca el caso "la cage no pudo evitarlo". **Esta** es
   la única condición que aplica la penalización `w_term` (§7.2.3).
2. **Emergencia C-05** (revisión F3): si la cage enclava un paro de
   emergencia, el rollout ya falló (el coche queda congelado) y los pasos
   restantes no aportan señal — terminar de inmediato evita malgastar el
   horizonte. Se trata como fallo terminal (el value bootstrapea desde 0)
   pero **sin penalización** (`done=off_road` en la recompensa): castigar
   la acción de la cage contradiría su tratamiento como dinámica del
   entorno (D-34). `info["termination_reason"] ∈ {off_road, cage_emergency,
   truncated}`.

Implementación en `GazeboLaneEnv.step`; rationale en
`docs/09_environment_design.md` (ED-4 / ED-8) y D-34 (addendum F3).

**Truncación** (episodio completo): `step_count ≥ max_episode_steps`.
Con `max_episode_steps = 500` y `control_dt = 0.10 s`, el episodio dura
50 s (≈ 1.14 vueltas al óvalo). Episodios más largos aceleran la
convergencia porque el agente ve más variedad de estados por episodio.
El valor de 500 pasos es `[provisional, M-P6]`; el horizonte resultó
adecuado: en el ciclo definitivo de 200 000 timesteps la policy aprende a
recorrer el episodio completo sin terminar (`ep_len_mean` satura en los 500
pasos, §7.4.1), de modo que toda la experiencia tardía es por truncación.

### 7.2.5 Cage durante el entrenamiento

La cage opera en modo `enforcement` durante todo el entrenamiento
(D-34). En cada ciclo de control, `GazeboLaneEnv` construye el estado de
la cage a partir del tracker, forma la acción raw `(steering_policy,
throttle_nominal)`, e invoca **en proceso** la misma clase
`SafetyCageNode` —con el mismo `cage/cage.yaml`— que el nodo de
despliegue `cage_ros_node` envuelve por tópicos. La acción segura
resultante se mapea a `/cmd_vel` replicando `vehicle_control_node`
(throttle→velocidad, `angular.z = steering·yaw_gain`, emergencia→parada
controlada). La recompensa se calcula sobre la acción segura y el estado
resultante, no sobre la acción raw, **con una excepción deliberada: el
término de suavidad `w_ds·|Δsteering|`** (reward v1.2). Ese término existe
para moldear la actuación de la *propia política*. Bajo el reward anterior
(v1.0, con el Δ medido **post-cage**) C-06 absorbía el bang-bang crudo en
una señal post-cage casi idéntica se saturara o no la política, de modo que
medir el Δ post-cage dejaba el término sin efecto: un ciclo previo mostró a
la policy llevando C-06 a su tope el ~89% de los pasos sin pagar por ello.
Por eso el término se computa sobre el `Δsteering` **crudo** (pre-cage) y se
sube de peso (`w_ds = 0.10 → 0.20`): así la política paga su propio jerk en
lugar de delegarlo gratis en C-06. **La evaluación del ciclo definitivo
(§7.5.2) confirma el efecto:** bajo reward v1.2 la policy aprende a girar de
forma nativa suave (|Δraw| medio 0.027, muy por debajo del límite 0.15 de
C-06) y la cage deja de intervenir (0 % de los pasos). El resto de términos
(ey, epsi, progreso, terminación) sigue sobre el estado resultante / la
acción segura, y las intervenciones de la cage no se penalizan (D-34).

La invocación en proceso —en lugar del intercambio asíncrono
`/raw_action`→`/safe_action` por tópicos— se elige por determinismo (bajo
la semilla fija de §7.2.7) y porque produce un comportamiento de cage
idéntico al de despliegue: misma clase y misma configuración (ver D-34).
El cableado puro y libre de ROS reside en `cobraflex_rl/cage_bridge.py`.

Esta elección alinea entrenamiento con despliegue: la policy aprende
bajo la misma restricción que encontrará en evaluación y en físico. Las
intervenciones de la cage son parte de la dinámica del entorno desde la
perspectiva del agente; no se penalizan explícitamente en la recompensa
(la penalización está implícita en el peor estado que la cage corregida
no puede evitar completamente).

Este cableado es la tarea TS-01 de F3, ya implementada. La cage puede
desactivarse (`cage.enabled: false` en `train_ppo.yaml`) para reproducir
el bucle sin cage usado en la depuración preliminar del pipeline.

### 7.2.6 Hiperparámetros PPO

Los hiperparámetros de partida (versión 1.0) siguen los valores
recomendados de Stable-Baselines3 para entornos de control continuo,
con ajuste del horizonte `n_steps` al periodo del episodio:

| Parámetro | Valor | Fuente |
| --- | --- | --- |
| `total_timesteps` | 200 000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴ | SB3 default |
| `gamma` | 0.99 | SB3 default |
| `n_steps` | 1 024 | ≈ 2 episodios de 500 pasos |
| `batch_size` | 64 | SB3 default |
| `device` | cpu | Dev machine sin GPU |

El presupuesto de timesteps `[provisional, M-P7]` se fijó iterativamente.
Un primer ciclo de 50 000 timesteps produjo una policy competente pero
**no saturada** —la recompensa seguía creciendo al agotar el presupuesto—,
lo que motivó extenderlo. El ciclo definitivo de **200 000 timesteps**
(seed 42, reward v1.2, §7.4) satura con margen holgado: la literatura de
lane-following simple con PPO sitúa la convergencia entre 20 000 y 100 000
timesteps según la complejidad del entorno, y aquí `ep_len_mean` alcanza el
horizonte completo de 500 pasos hacia ~71 000 timesteps, con la recompensa
estabilizada en el último tercio del presupuesto (§7.4.1).

### 7.2.7 Semillas y reproducibilidad

El ciclo de entrenamiento definitivo usa `seed = 42` y 200 000 timesteps
bajo el reward v1.2 (§7.2.3, §7.2.5). Los resultados reportados en §7.4 y
§7.5 corresponden a esta semilla única. La evaluación estadística
multi-semilla (N ≥ 5) se difiere al Capítulo 8 cuando se compare la policy
RL contra el PD baseline.

### 7.2.8 Checkpoints y registro

Los checkpoints se guardan en `policy/checkpoints/` cada `n_steps`
pasos (denominación SB3 `cobraflex_ppo_lane_<N>_steps.zip`, p.ej.
`cobraflex_ppo_lane_50176_steps.zip`).
El modelo final se guarda como `cobraflex_ppo_lane.zip`. Cada run de
entrenamiento registra en `experiments/sim/training/` un CSV de curva
de aprendizaje con columnas `[timestep, ep_rew_mean, ep_len_mean,
explained_variance]` y un `metadata.json` con los mismos campos de
reproducibilidad que los runs de validación (git commit, YAML hashes,
seed, timestamp).

---

## 7.3 Entorno de simulación para entrenamiento RL  [BORRADOR D36]

El entorno de simulación para entrenamiento es el mismo mundo Gazebo
(`lane_following_oval.world`) utilizado en la validación F2, con tres
adaptaciones para el ciclo RL.

Primera, **control del reloj de simulación.** En la validación F2 el
reloj de Gazebo avanza en tiempo real (RTF ≈ 1). En el entrenamiento RL
el simulador se ejecuta *headless* (sin GUI) y con el reloj sin pausa,
lo que permite un RTF superior a 1 y acelera el muestreo de timesteps.
El RTF efectivo depende del hardware; en la máquina de desarrollo se
estima en 2–4×.

Segunda, **reset de episodio.** Al inicio de cada episodio, el vehículo
se teletransporta a la posición de spawn mediante el servicio
`/world/lane_following_oval/set_pose`. Este reset usa el mismo mecanismo
que la detección de warp en `lane_perception_node` (§6.3.2): el nodo
detecta el salto brusco de posición y reinicia su tracker y EMA.

Tercera, **perturbación de spawn.** Para generar diversidad de estados
de inicio, cada episodio introduce una perturbación aleatoria en el
heading de spawn dentro de `[-0.15, +0.15] rad` y en la posición lateral
dentro de `[-0.05, +0.05] m`. Esto evita que la policy memori\-ze una
única trayectoria de arranque y mejora la generalización a los escenarios
perturbados de Fase 4. Los rangos son `[provisional, M-P5]`.

---

## 7.4 Resultados del entrenamiento

Ciclo de entrenamiento PPO definitivo: run `ppo_train_42_200k` (run_id
`ppo_train_20260602T145922Z`, seed 42, 200 000 timesteps, reward v1.2,
~6.2 h a tiempo real, fps≈9). Datos crudos:
`experiments/sim/training/ppo_train_42_200k/learning_curve.csv`
(196 iteraciones de 1 024 pasos). Este ciclo, entrenado bajo el reward
v1.2 (§7.2.5), **supersede** a los ciclos previos —el preliminar de
50 000 timesteps (no saturado) y un ciclo de 250 000 timesteps con reward
v1.0 que saturaba pero dejaba a la policy apoyándose en C-06 el ~89 % de
los pasos (§7.5.2)— y es el que se evalúa en §7.5.

### 7.4.1 Curva de convergencia

`ep_rew_mean` crece de 24.8 (1 024 pasos) a un plateau de **535.2**
(200 704 pasos; máximo 535.2); `ep_len_mean` de 48.0 a **500.0**, es decir
el horizonte completo de truncación (≈ 1.14 vueltas por episodio). La
Figura 7.1 muestra ambas curvas (raw + suavizado ventana 5). A diferencia
del ciclo de 50 000 timesteps, esta corrida **satura**: `ep_len_mean`
alcanza los 500 pasos hacia los ~71 000 timesteps —la policy deja de
salirse y agota el episodio por truncación— y `ep_rew_mean` llega al 90 %
de su valor final (~482) hacia los ~84 000. El tramo restante (84k–200k)
es un plateau estable en el que `ep_rew_mean` asciende suavemente de ~480 a
535.2 mientras `ep_len_mean` permanece clavado en 500 —el episodio se
completa entero durante toda la meseta—, de modo que esa ganancia tardía de
recompensa es refinamiento residual de la calidad de tracking, no mayor
supervivencia.

<img src="../figures/fig_7_1_convergence.png" alt="Figura 7.1 — Curva de convergencia del entrenamiento PPO: ep_rew_mean y ep_len_mean vs timesteps." width="560"/>

*Figura 7.1 — Curva de convergencia del entrenamiento PPO (run
`ppo_train_42_200k`, seed 42, 200 000 timesteps): `ep_rew_mean`
(azul) y `ep_len_mean` (rojo) vs timesteps, datos crudos + suavizado
(ventana 5). `ep_len_mean` satura en el horizonte de 500 pasos hacia ~71k y
la recompensa asciende hasta su plateau de ~535 en el último tercio.
Generada por `tools/plot_f3_figures.py`.*

### 7.4.2 Estabilidad y explained_variance

`explained_variance` fue baja y ruidosa durante la fase de mejora rápida
(oscila entre ~−0.39 y ~0.56, ≈0.30 a los 50k timesteps): el crítico
persigue un retorno creciente, con la función de valor por detrás de una
policy que mejora rápido. Una vez la recompensa hace plateau se estabiliza:
promedia **0.56** en la meseta (≥71k) —el 71 % de las iteraciones de
plateau queda ≥0.5 y el 86 % ≥0.4— y cierra en **0.63** (máximo 0.82),
**por encima del umbral de 0.5** de esta sección: el crítico predice con
fiabilidad el retorno de una policy estacionaria.

El criterio de convergencia (`ep_rew_mean` estable en ventana de 10
iteraciones) **se cumple**: la recompensa lleva en plateau desde los ~84k
timesteps, de modo que el presupuesto de 200 000 deja un amplio margen
sobre el punto de convergencia. Esto resuelve la limitación documentada
del ciclo preliminar de 50 000 (no saturado): la policy resultante es
competente (§7.5) **y** saturada.

### 7.4.3 Observaciones sobre la convergencia

- **Inicio (≈0–5%):** la policy emergencia/sale en ~48 pasos de media;
  episodios cortos dominados por C-05 (ver `docs/CHANGELOG.md`, entrada de
  bring-up F3).
- **Subida (≈5–35%):** `ep_len_mean` trepa desde ~50 hasta los 500 pasos
  —la policy completa fracciones crecientes de vuelta hasta recorrer el
  episodio entero, hacia ~71k timesteps—; en paralelo `ep_rew_mean` sube de
  ~50 a ~480.
- **Plateau (≈35–100%):** `ep_len_mean` ≈ 500 (horizonte completo, ~1.14
  vueltas); deja de salirse por completo (las emergencias caen a ~0,
  confirmado en la evaluación §7.5: 0 emergencias en las 11.2 vueltas /
  4 400 pasos). La policy se compromete con acciones concretas y la
  recompensa asciende suavemente de ~480 a ~535.
- **Actuación cruda suave (reward v1.2):** a diferencia del ciclo previo de
  reward v1.0 —cuyo steering raw era bang-bang y delegaba el suavizado en
  C-06—, bajo reward v1.2 la actuación cruda es **nativamente suave**
  (|Δraw| medio 0.027, cambios de signo en el 1.1 % de los pasos, 0 % de
  saturación a ±1): el rate-limiter C-06 ya no necesita intervenir (§7.5.2).
  A nivel de **trayectoria** tampoco hay oscilación apreciable (ey máx 18 mm
  sobre 11.2 vueltas en evaluación, §7.5).

---

## 7.5 Evaluación de la policy sobre SC-NOM-01

Policy evaluada: checkpoint `cobraflex_ppo_lane` (run de entrenamiento
`ppo_train_42_200k`, seed 42, 200 000 timesteps, reward v1.2). Run de
evaluación `rl_eval_42_200k_4k4` (run_id `rl_eval_20260603T075419Z`): un
episodio determinista (spawn sin perturbación, §7.3), horizonte extendido a
4 400 pasos = 440 s (≈ 11.2 vueltas continuas) para que el recuento de
vueltas sea comparable con el PD. Comparación directa con la run del PD
baseline `ros_run_20260523T153003Z` (§6.6.1).

### 7.5.1 Completion rate y métricas de tracking

| Métrica | PD (pre-F3) | PPO (F3) |
| --- | --- | --- |
| Vueltas completadas | 9.91 (845 s) | 11.17 (440 s) † |
| Emergencias cage (C-05) | 0 | **0** |
| Intervenciones cage (% de pasos) | 0.047% | **0%** |
| ey medio \|ey\| (m) | 0.023 | **0.0065** |
| epsi medio \|epsi\| (rad) | 0.076 | **0.032** |

† Las duraciones difieren (PPO 440 s, PD 845 s), así que el recuento bruto
de vueltas **no es 1:1**. Lo robusto y comparable: **ambos completaron su
corrida sin un solo fallo** (0 emergencias), y la PPO **sostuvo > 11
vueltas continuas** sin que el cage tuviera que activar la parada de
emergencia. Las métricas por-paso (tasa de intervención, error de
tracking) son independientes de la duración y son el resultado
discriminante. Referencia:
`experiments/sim/runs/rl_eval_42_200k_4k4/cage_status.csv`.

**Lectura.** La PPO **iguala** al PD en seguridad (0 emergencias en 11.2
vueltas), lo **supera en precisión de tracking** —el error lateral medio
cae de 23 mm a 6.5 mm (×3.6; máximo 18 mm, dentro del medio-carril de
122 mm y muy por debajo del `d_max = 160 mm` del cage) y el error de
heading medio de 4.3° a 1.9° (×2.3)— y, a diferencia del ciclo previo de
reward v1.0, lo hace **sin una sola intervención del cage** (0 % de los
pasos, §7.5.2): la policy se mantiene por sí misma dentro de la envolvente
de seguridad en el escenario nominal.

<img src="../figures/fig_7_2_trajectory.png" alt="Figura 7.2 — Trayectoria de la policy PPO sobre el óvalo." width="460"/>

*Figura 7.2 — Trayectoria de la policy PPO sobre el óvalo (~2 vueltas, run
`rl_eval_42_200k_4k4`), ciñéndose a la línea central del carril. A
escala espacial la diferencia de tracking con el PD (mm) no es resoluble;
ver Figura 7.2b. Generada por `tools/plot_f3_figures.py`.*

<img src="../figures/fig_7_2b_tracking_error.png" alt="Figura 7.2b — Error lateral RL vs PD a lo largo de la corrida." width="600"/>

*Figura 7.2b — Error lateral \|ey\| a lo largo de la corrida: PPO (azul) vs
PD baseline (rojo), warm-up de 0.3 vueltas recortado. La PPO se mantiene en
una banda estrecha (~0–18 mm) frente a la oscilación del PD en curva (hasta
~65 mm), ambos muy por debajo del medio-carril (122 mm). Generada por
`tools/plot_f3_figures.py`.*

### 7.5.2 Comportamiento cualitativo

Tres observaciones del log por-paso (`cage_status.csv`):

1. **Tracking más fino que el PD.** La PPO centra el vehículo con ~3.6× menos
   error lateral (6.5 mm vs 23 mm) y ~2.3× menos error de heading (1.9° vs 4.3°),
   sostenido a lo largo de las 11.2 vueltas. Visualmente (Figura 7.2) la
   trayectoria RL se ciñe a la línea central con menos desviación en curva que el
   PD; la diferencia de banda es nítida en la Figura 7.2b.
2. **Actuación cruda nativamente suave (reward v1.2).** A diferencia del ciclo
   previo de reward v1.0 —cuyo steering *crudo* era bang-bang (cambio de signo en
   ~46% de los pasos, saturación frecuente a ±1, \|Δraw\| medio ≈ 0.54, > 3× el
   límite `delta_max = 0.15` de C-06) y delegaba el suavizado en el rate-limiter—,
   la policy entrenada bajo reward v1.2 emite un comando crudo **suave y
   moderado**: magnitud media \|raw\| = **0.26** (máx 0.55, **sin saturar**),
   cambios de signo en solo el **1.1%** de los pasos y \|Δraw\| medio = **0.027**,
   holgadamente **por debajo** del límite de tasa de C-06. La policy aprendió a
   girar de forma continua en lugar de explotar el rate-limiter como actuador de
   tasa. Este es el efecto buscado del término de suavidad sobre el `Δsteering`
   **crudo** (`w_ds = 0.20`, §7.2.5): al pagar su propio jerk, la política
   internaliza la suavidad en vez de delegarla en C-06.
3. **El cage no interviene en nominal (salvaguarda latente).** Como consecuencia
   directa de (2), el steering crudo nunca viola ninguna regla: la acción segura
   coincide **exactamente** con la acción cruda en los 4 400 pasos
   (\|raw − safe\| = 0 en todo el episodio), de modo que la tasa de intervención
   del cage es **0%** —ni C-06 ni ninguna otra regla C-01..C-05 se activa— frente
   al **89.0%** (todo C-06) del ciclo previo de reward v1.0 y al 0.047% del PD. En
   el escenario nominal la policy se mantiene por sí misma dentro de la envolvente
   de seguridad y el cage opera como **salvaguarda latente**: presente y armado,
   pero sin coste de actuación. El valor protector del cage no se ejerce en
   crucero nominal, sino frente a las perturbaciones y casos límite del Capítulo 8
   (SC-EDGE, SC-PERT), donde la policy sí puede acercarse a los bordes del carril.
   Esto **completa** el diagnóstico del ciclo de reward v1.0: aquél mostró que un
   término de suavidad post-cage era inocuo (la policy llevaba C-06 a su tope
   gratis); reformularlo sobre el `Δsteering` crudo produjo una policy que ya no
   necesita el rate-limiter en nominal.

   > **Refinamiento confirmado (reward v1.2).** El término de suavidad reformulado
   > para penalizar el `Δsteering` **crudo** (pre-cage), con peso subido
   > `w_ds = 0.10 → 0.20` (§7.2.5, `docs/10_reward_function.md`), se diseñó para
   > que la política pagara su propio bang-bang en lugar de delegarlo gratis en
   > C-06. Su efecto, que en el ciclo de reward v1.0 quedaba **pendiente de
   > confirmar en un nuevo ciclo de entrenamiento**, queda **verificado** por esta
   > evaluación: bajo reward v1.2 la actuación cruda es nativamente suave (punto 2)
   > y el cage deja de intervenir en el escenario nominal (punto 3). Los pesos
   > siguen `[provisional, M-P4]` a la espera del análisis de sensibilidad del
   > Capítulo 8.

<img src="../figures/fig_7_3_gazebo_capture.png" alt="Figura 7.3 — Captura de la evaluación en Gazebo: la policy PPO conduciendo el óvalo bajo el cage." width="640"/>

*Figura 7.3 — Captura representativa del lane-following de la policy PPO bajo el
cage (corrida de evaluación de un ciclo previo; visualmente equivalente al run
definitivo de §7.5, ya que la vista de Gazebo/RViz no depende del checkpoint):
vista de Gazebo (óvalo + vehículo 1:14, izquierda) y RViz (modelo del robot y
frames TF, derecha).*

> **Material suplementario (vídeo).** Las grabaciones completas de las corridas
> están en `manuscript/media/` (no versionadas por tamaño; ver `.gitignore`):
> `training_1_lap.mp4` (una vuelta, política entrenada) y `eval_11_lap.mp4` (una
> corrida de evaluación de ~11.5 vueltas de un ciclo previo, representativa de la
> conducta de §7.5).

---

## 7.6 Síntesis y transición al Capítulo 8  [BORRADOR D36]

Este capítulo ha producido la Training Specification (artefacto A1 del
V-Model) y, una vez completado con los datos de §7.4 y §7.5, la
primera evidencia empírica de que una policy PPO puede aprender
lane-following en el mismo entorno donde el PD baseline fue validado.

La Training Specification es un documento de diseño, no de evaluación.
El hecho de que la policy converja en entrenamiento no valida que cumpla
los Safety Requirements: esa validación es el objeto del Capítulo 8.
Lo que este capítulo establece es que existe una policy candidata —
entrenada bajo condiciones documentadas y reproducibles — que el
Capítulo 8 puede evaluar sistemáticamente.

El Capítulo 8 introduce la *scenario library* como instrumento de
evaluación: en vez de una única corrida nominal, la policy se evalúa
sobre todos los escenarios de la library (SC-NOM-01..03, SC-EDGE-01..05,
SC-PERT-01..03), con las métricas M-S1..M-S4, M-P1..M-P7, M-I1..M-I5,
M-C1..M-C2 definidas en `docs/06_metrics_catalogue.md`. La comparación
sistemática entre RL+cage y PD+cage es el resultado experimental central
de la tesis.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Fase 4–5:
  [ ] Evaluar sobre todos los escenarios SC-NOM, SC-EDGE, SC-PERT
  [ ] Añadir análisis multi-semilla (N≥5)

Fase 6 (consolidación):
  [ ] Pulido de prosa
  [ ] Verificar coherencia cruzada §7.2.3 (pesos recompensa) con
       resultados del Capítulo 8 si se revisan los pesos
-->
