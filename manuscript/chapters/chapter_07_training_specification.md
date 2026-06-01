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
RL. La sección 7.4 reporta los resultados del primer ciclo de
entrenamiento PPO. La sección 7.5 evalúa la policy entrenada sobre el
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
wrap del arco en el circuito cerrado), y `[terminated_off_road]` es 1 solo
si el episodio termina por salida de **vía** (no por emergencia C-05; ver
§7.2.4). Los pesos nominales (versión 1.0, sujetos a ajuste experimental)
son:

| Parámetro | Valor | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Premia progreso real (≈1.0/paso a crucero) |
| `w_ey` (lateral_error) | 2.5 | Penalización principal: offset lateral |
| `w_eps` (heading_error) | 0.75 | Penalización secundaria: heading |
| `w_ds` (steer_delta) | 0.10 | Suavidad de actuación |
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
El valor de 500 pasos es `[provisional, M-P6]`; se revisará si el agente
no converge en 50 000 timesteps (de hecho la policy aún mejoraba al
agotar el presupuesto — ver §7.4.2).

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
resultante, no sobre la acción raw.

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
| `total_timesteps` | 50 000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴ | SB3 default |
| `gamma` | 0.99 | SB3 default |
| `n_steps` | 1 024 | ≈ 2 episodios de 500 pasos |
| `batch_size` | 64 | SB3 default |
| `device` | cpu | Dev machine sin GPU |

Todos los parámetros marcados `[provisional, M-P7]` se revisarán tras
el análisis de curvas de convergencia del primer entrenamiento. El total
de 50 000 timesteps es conservador: la literatura de lane-following
simple con PPO muestra convergencia entre 20 000 y 100 000 timesteps
según la complejidad del entorno.

### 7.2.7 Semillas y reproducibilidad

El primer ciclo de entrenamiento usa `seed = 42`. Los resultados
reportados en §7.4 corresponden a esta semilla única. La evaluación
estadística multi-semilla (N ≥ 5) se difiere al Capítulo 8 cuando se
compare la policy RL contra el PD baseline.

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

## 7.4 Resultados del primer entrenamiento

Primer ciclo de entrenamiento PPO: run `ppo_train_20260601T150552Z`
(seed 42, 50 000 timesteps, ~95 min a tiempo real, fps≈8). Datos crudos:
`experiments/sim/training/ppo_train_20260601T150552Z/learning_curve.csv`
(49 iteraciones de 1 024 pasos).

### 7.4.1 Curva de convergencia

`ep_rew_mean` crece de forma **monótona** de 29.3 (1 024 pasos) a 427.9
(50 176 pasos); `ep_len_mean` de 45.9 a 427.3 pasos (de un horizonte de
500 ≈ 1.14 vueltas, es decir ~0.97 vueltas medias por episodio al final).
La Figura 7.1 muestra ambas curvas (raw + suavizado ventana 5). El
crecimiento es sostenido y **sin plateau**: la recompensa seguía subiendo
al agotar el presupuesto de 50 000 timesteps.

<img src="../figures/auto/fig_7_1_convergence.png" alt="Figura 7.1 — Curva de convergencia del entrenamiento PPO: ep_rew_mean y ep_len_mean vs timesteps." width="560"/>

*Figura 7.1 — Curva de convergencia del entrenamiento PPO (run
`ppo_train_20260601T150552Z`): `ep_rew_mean` (azul) y `ep_len_mean` (rojo)
vs timesteps, datos crudos + suavizado (ventana 5). Crecimiento monótono
sin plateau. Generada por `tools/plot_f3_figures.py`.*

### 7.4.2 Estabilidad y explained_variance

`explained_variance` fue baja y ruidosa durante la fase de mejora rápida
(≈0.01–0.34 entre 6k y 37k timesteps): el crítico persigue un retorno
creciente, con la función de valor por detrás de una policy que mejora
rápido. Subió a 0.55–0.73 en las últimas iteraciones, **superando el
umbral de 0.5** de esta sección al final del entrenamiento (final: 0.73);
en paralelo `value_loss` cayó de ~56 a ~0.2.

El criterio de convergencia de §7.4 (`ep_rew_mean` estable en ventana de
10 iteraciones) **no se cumple**: la recompensa fue monótonamente
creciente hasta el final, de modo que el número de timesteps hasta
convergencia **excede el presupuesto de 50 000**. La policy resultante es
competente (§7.5) pero **no saturada**; una corrida más larga seguiría
mejorando. Es una limitación documentada de este primer ciclo
[provisional, M-P6]: se ejecutó un único presupuesto fijo de 50k por
restricción de tiempo de cómputo (tiempo real, fps≈8), no porque la curva
hubiera estabilizado.

### 7.4.3 Observaciones sobre la convergencia

- **Inicio (≈2%):** la policy emergencia/sale en ~46 pasos de media;
  episodios cortos dominados por C-05 (ver `docs/CHANGELOG.md`, entrada de
  bring-up F3).
- **Mitad (≈30–60%):** `ep_len_mean` sube a 140–320 pasos — la policy
  completa fracciones crecientes de vuelta; `std` empieza a bajar de 1.0.
- **Final (≈90–100%):** `ep_len_mean` ≈ 427 ≈ una vuelta completa; deja de
  salirse con regularidad (las emergencias caen a ~0, confirmado en la
  evaluación §7.5: 0 emergencias en las 11.5 vueltas / 4 400 pasos). `std` baja a 0.74 — la
  policy se compromete con acciones concretas.
- **Oscilación residual:** sí, pero solo en la *actuación cruda* — el
  steering raw conserva un patrón bang-bang (§7.5.2) que el rate-limiter
  C-06 absorbe. A nivel de **trayectoria** no hay oscilación apreciable
  (ey máx 30 mm sobre 11.5 vueltas en evaluación, §7.5).

---

## 7.5 Evaluación de la policy sobre SC-NOM-01

Policy evaluada: checkpoint `cobraflex_ppo_lane` (run de entrenamiento
`ppo_train_20260601T150552Z`, seed 42, 50 000 timesteps). Run de
evaluación `rl_eval_20260601T172201Z`: un episodio determinista (spawn
sin perturbación, §7.3), horizonte extendido a 4 400 pasos = 440 s
(≈ 11.5 vueltas continuas) para que el recuento de vueltas sea comparable
con el PD. Comparación directa con la run del PD baseline
`ros_run_20260523T153003Z` (§6.6.1).

### 7.5.1 Completion rate y métricas de tracking

| Métrica | PD (pre-F3) | PPO (F3) |
| --- | --- | --- |
| Vueltas completadas | 9.91 (845 s) | 11.53 (440 s) † |
| Emergencias cage (C-05) | 0 | **0** |
| Intervenciones cage (% de pasos) | 0.047% | 85.9% (todo C-06) |
| ey medio \|ey\| (m) | 0.023 | **0.0092** |
| epsi medio \|epsi\| (rad) | 0.076 | **0.034** |

† Las duraciones difieren (PPO 440 s, PD 845 s), así que el recuento bruto
de vueltas **no es 1:1**. Lo robusto y comparable: **ambos completaron su
corrida sin un solo fallo** (0 emergencias), y la PPO **sostuvo > 11
vueltas continuas** sin que el cage tuviera que activar la parada de
emergencia. Las métricas por-paso (tasa de intervención, error de
tracking) son independientes de la duración y son el resultado
discriminante. Referencia:
`experiments/sim/runs/rl_eval_20260601T172201Z/cage_status.csv`.

**Lectura.** La PPO **iguala** al PD en seguridad (0 emergencias en 11.5
vueltas) y lo **supera en precisión de tracking**: el error lateral medio
cae de 23 mm a 9.2 mm (máximo 30 mm, dentro del medio-carril de 122 mm y
muy por debajo del `d_max = 160 mm` del cage) y el error de heading medio
de 4.4° a 2.0°.

<img src="../figures/auto/fig_7_2_trajectory.png" alt="Figura 7.2 — Trayectoria de la policy PPO sobre el óvalo." width="460"/>

*Figura 7.2 — Trayectoria de la policy PPO sobre el óvalo (~2 vueltas, run
`rl_eval_20260601T172201Z`), ciñéndose a la línea central del carril. A
escala espacial la diferencia de tracking con el PD (mm) no es resoluble;
ver Figura 7.2b. Generada por `tools/plot_f3_figures.py`.*

<img src="../figures/auto/fig_7_2b_tracking_error.png" alt="Figura 7.2b — Error lateral RL vs PD a lo largo de la corrida." width="600"/>

*Figura 7.2b — Error lateral \|ey\| a lo largo de la corrida: PPO (azul) vs
PD baseline (rojo), warm-up de 0.3 vueltas recortado. La PPO se mantiene en
una banda estrecha (~10–25 mm) frente a la oscilación del PD en curva (hasta
~65 mm), ambos muy por debajo del medio-carril (122 mm). Generada por
`tools/plot_f3_figures.py`.*

### 7.5.2 Comportamiento cualitativo

Tres observaciones del log por-paso (`cage_status.csv`):

1. **Tracking más fino que el PD.** La PPO centra el vehículo con ~2.5× menos
   error lateral (9.2 mm vs 23 mm) y ~2× menos error de heading, sostenido a lo
   largo de las 11.5 vueltas. Visualmente (Figura 7.2) la trayectoria RL se ciñe
   a la línea central con menos desviación en curva que el PD.
2. **Actuación cruda bang-bang = control de tasa.** El steering *crudo* es muy
   oscilatorio: cambia de signo en el **46.9%** de los pasos, satura a ±1 en el
   **24.0%**, con magnitud media \|raw\| = 0.47 y \|Δraw\| medio = 0.48 (> 3× el
   límite `delta_max = 0.15` de C-06). Lejos de ser un artefacto, es la
   estrategia **racional** bajo un rate-limiter: como C-06 acota el *cambio* de
   steering por ciclo, el actuador efectivo es la *tasa* de giro, no la posición;
   saturar el comando hacia un lado hace que el steering real rampe a su máxima
   tasa (0.15/ciclo) en esa dirección. La policy aprendió a usar el comando de
   posición como **comando de tasa** (satura, flipa para invertir — control tipo
   PWM). Lo *permite* que la recompensa penalice el `Δsteer` débilmente
   (`w_ds = 0.10`) y se compute sobre la acción **post-cage** (D-34): el
   resultado suavizado es idéntico se sature o no, así que la policy no "paga"
   por la oscilación cruda.
3. **El cage hace trabajo real para la RL (a diferencia del PD).** El
   rate-limiter **C-06** interviene en el **85.9%** de los pasos; en el **86%**
   el steering real se mueve **exactamente al límite de 0.15/ciclo** (la policy
   conduce el rate-limiter a su tope de forma continua). El steering real resulta
   suave y moderado (\|safe\| medio 0.28, máx 0.82) pese al comando nervioso
   (\|raw\| 0.47) — frente al **0.047%** de intervención del PD, que produce
   steering suave de forma nativa. Ninguna otra regla (C-01..C-05) se activa: la
   policy se mantiene holgadamente dentro del carril, y lo único que el cage
   necesita aportar es **suavizado de actuación**. Esto valida cuantitativamente
   el cage como salvaguarda activa sobre una policy aprendida, y sugiere un
   refinamiento futuro (penalizar más el `Δsteer` crudo, o un término sobre la
   acción raw) para acercar la suavidad nativa de la RL a la del PD.

<img src="../figures/eval_figure_11_lap.png" alt="Figura 7.3 — Captura de la evaluación en Gazebo: la policy PPO conduciendo el óvalo bajo el cage." width="640"/>

*Figura 7.3 — Captura de la corrida de evaluación (`rl_eval_20260601T172201Z`):
vista de Gazebo (óvalo + vehículo 1:14, izquierda) y RViz (modelo del robot y
frames TF, derecha) durante el lane-following de la policy PPO bajo el cage.*

> **Material suplementario (vídeo).** Las grabaciones completas de las corridas
> están en `manuscript/media/` (no versionadas por tamaño; ver `.gitignore`):
> `training_1_lap.mp4` (una vuelta, política entrenada) y `eval_11_lap.mp4` (la
> corrida de evaluación de ~11.5 vueltas de §7.5).

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

Fase 3 (D36+):
  [x] Esqueleto de secciones 7.1–7.6 fijado en D36
  [x] Training Specification §7.2 completa (8 componentes)
  [x] Completar §7.4 con datos del primer entrenamiento (run
       ppo_train_20260601T150552Z: convergencia, ev→0.73, no satura en 50k)
  [x] Completar §7.5 con evaluación del RL sobre SC-NOM-01
       (rl_eval_20260601T172201Z, 11.5 vueltas, RL vs PD)
  [x] Añadir Figura 7.1: curva de convergencia ep_rew_mean vs timesteps
       (tools/plot_f3_figures.py → figures/auto/)
  [x] Añadir Figura 7.2: trayectoria RL sobre el óvalo + 7.2b error lateral
       RL vs PD + 7.3 captura Gazebo
  [x] Tarea TS-01: cablear GazeboLaneEnv → cage in-process (misma
       SafetyCageNode/cage.yaml que cage_ros_node; D-34 enforcement)
  [x] Añadir perturbación aleatoria de spawn en GazeboLaneEnv.reset() (§7.3)
  [x] Registrar training runs en experiments/sim/training/ (§7.2.8)
  [x] Decidir si aumentar total_timesteps si no converge en 50k → se reporta
       50k con la limitación documentada (§7.4.2); extensión diferida
  -- Mejoras F3 abiertas (no bloqueantes para G3), de §7.5.2 / sesión:
  [ ] Penalizar más el Δsteer crudo (la policy ofrece bang-bang que C-06 suaviza)
  [ ] Robustez del set_pose timeout recurrente en reset()
  [ ] (opc.) VecNormalize de observaciones; RTF para acelerar entrenamiento

Fase 4–5:
  [ ] Evaluar sobre todos los escenarios SC-NOM, SC-EDGE, SC-PERT
  [ ] Añadir análisis multi-semilla (N≥5)

Fase 6 (consolidación):
  [ ] Pulido de prosa
  [ ] Verificar coherencia cruzada §7.2.3 (pesos recompensa) con
       resultados del Capítulo 8 si se revisan los pesos
-->
