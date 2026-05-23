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

El vector de observación es un array de cuatro flotantes:

```
obs = [ey, epsi, speed, prev_steer]
```

donde `ey` es el offset lateral respecto a la línea central del carril
(positivo a la izquierda), `epsi` es el error de heading respecto a la
tangente de la línea central (positivo en sentido antihorario), `speed`
es la velocidad escalar del vehículo en m/s, y `prev_steer` es el
steering aplicado en el ciclo anterior (normalizado en [-1, 1]).

Los límites del espacio son [-∞, +∞] para `ey` y `speed`, [-π, π] para
`epsi`, y [-1, 1] para `prev_steer`. En la práctica, el rango operativo
es estrecho: ey ∈ [-0.12, 0.12] m, epsi ∈ [-0.4, 0.4] rad (ver §6.6.2).

La inclusión de `prev_steer` es una forma ligera de memoria de primer
orden que ayuda al agente a regularizar su comportamiento de steering sin
requerir una arquitectura recurrente. El `speed` es información necesaria
para la calibración de la corrección de heading en curva.

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

```
r = w_fwd · speed
  - w_ey  · |ey|
  - w_eps · |epsi|
  - w_ds  · |Δsteering|
  - w_term · [terminated]
```

donde `[terminated]` es 1 si el episodio termina por violación de carril.
Los pesos nominales (versión 1.0, sujetos a ajuste experimental) son:

| Parámetro | Valor | Rationale |
|---|---|---|
| `w_fwd` (forward_progress) | 1.0 | Incentiva avance |
| `w_ey` (lateral_error) | 2.5 | Penalización principal: offset lateral |
| `w_eps` (heading_error) | 0.75 | Penalización secundaria: heading |
| `w_ds` (steer_delta) | 0.10 | Suavidad de actuación |
| `w_term` (termination) | 25.0 | Desincentiva salida de carril |

El diseño de recompensa es deliberadamente simple. La práctica en
lane-following con RL muestra que recompensas más complejas (múltiples
términos de curvatura, penalización por oscilación de heading) raramente
mejoran el comportamiento base y complican el análisis de ablación. La
penalización de terminación alta (25.0) prioriza la permanencia en carril
sobre la optimización de velocidad.

Los pesos son `[provisional, M-P1..M-P4]` — se marcan provisionalmente
hasta que el análisis de sensibilidad del Capítulo 8 confirme que no hay
degeneración (policy que maximiza `forward_progress` sin atender `ey`).

### 7.2.4 Criterios de terminación y truncación

**Terminación** (episodio falla): `|ey| > lane_width / 2`. El agente
sale del carril. La cage debería haber evitado esto; si ocurre, indica
que la cage no puede corregir el nivel de error acumulado.

**Truncación** (episodio completo): `step_count ≥ max_episode_steps`.
Con `max_episode_steps = 400` y `control_dt = 0.10 s`, el episodio dura
40 s (≈ 0.47 vueltas al óvalo). Episodios más largos aceleran la
convergencia porque el agente ve más variedad de estados por episodio.
El valor de 400 pasos es `[provisional, M-P6]`; se revisará si el agente
no converge en 50 000 timesteps.

### 7.2.5 Cage durante el entrenamiento

La cage opera en modo `enforcement` durante todo el entrenamiento
(D-34). El bucle de entrenamiento publica acciones raw en `/raw_action`,
recibe acciones seguras de `/safe_action`, y pasa éstas últimas al
vehículo. La recompensa se calcula sobre la acción segura y el estado
resultante, no sobre la acción raw.

Esta elección alinea entrenamiento con despliegue: la policy aprende
bajo la misma restricción que encontrará en evaluación y en físico. Las
intervenciones de la cage son parte de la dinámica del entorno desde la
perspectiva del agente; no se penalizan explícitamente en la recompensa
(la penalización está implícita en el peor estado que la cage corregida
no puede evitar completamente).

La implementación concreta de este cableado es la tarea TS-01 de F3;
hasta que esté completada, las runs de entrenamiento preliminares usan
el bucle sin cage para depuración del pipeline de entrenamiento.

### 7.2.6 Hiperparámetros PPO

Los hiperparámetros de partida (versión 1.0) siguen los valores
recomendados de Stable-Baselines3 para entornos de control continuo,
con ajuste del horizonte `n_steps` al periodo del episodio:

| Parámetro | Valor | Fuente |
|---|---|---|
| `total_timesteps` | 50 000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴ | SB3 default |
| `gamma` | 0.99 | SB3 default |
| `n_steps` | 1 024 | ≈ 2.5 episodios de 400 pasos |
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
iteraciones (denominación `cobraflex_ppo_lane_stepXXXXX.zip`).
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

## 7.4 Resultados del primer entrenamiento  [COMPLETAR FASE 3]

> *Esta sección se completa tras el primer ciclo de entrenamiento PPO
> completo (50 000 timesteps, seed 42). Los campos pendientes son:
> curva de recompensa media por episodio, curva de longitud media de
> episodio, explained_variance al final del entrenamiento, número real
> de timesteps hasta convergencia (criterio: ep_rew_mean estable en
> ventana de 10 iteraciones), y run-id del experimento de entrenamiento.*

### 7.4.1 Curva de convergencia

> [COMPLETAR FASE 3] — Figura con ep_rew_mean vs timesteps.
> Incluir la curva suavizada (ventana 5) y los datos raw.
> Referencia: `experiments/sim/training/<run_id>/learning_curve.csv`.

### 7.4.2 Estabilidad y explained_variance

> [COMPLETAR FASE 3] — Reportar explained_variance al final del
> entrenamiento. Valores < 0.5 indican función de valor mal ajustada
> y motivarían incrementar n_steps o total_timesteps.

### 7.4.3 Observaciones sobre la convergencia

> [COMPLETAR FASE 3] — Descripción cualitativa del comportamiento
> de la policy al inicio, a la mitad, y al final del entrenamiento.
> ¿Cuándo deja de salirse del carril con regularidad? ¿Muestra
> comportamiento oscilatorio residual?

---

## 7.5 Evaluación de la policy sobre SC-NOM-01  [COMPLETAR FASE 3]

> *Esta sección se completa tras la primera run de evaluación de la
> policy entrenada en el escenario nominal. Comparación directa con
> la run del PD baseline (§6.6.1).*

### 7.5.1 Completion rate y métricas de tracking

> [COMPLETAR FASE 3] — Tabla comparativa RL vs PD:
>
> | Métrica | PD (pre-F3) | PPO (F3) |
> |---|---|---|
> | Vueltas completadas | 9.91 | [COMPLETAR] |
> | Emergencias cage | 0 | [COMPLETAR] |
> | Intervenciones cage (%) | 0.047% | [COMPLETAR] |
> | ey medio (m) | 0.023 | [COMPLETAR] |
> | epsi medio (rad) | 0.076 | [COMPLETAR] |
>
> Referencia: `experiments/sim/runs/<run_id_rl>/cage_status.csv`.

### 7.5.2 Comportamiento cualitativo

> [COMPLETAR FASE 3] — ¿El RL mejora el tracking lateral respecto al
> PD? ¿Activa la cage con menos frecuencia? ¿Muestra oscilación de
> steering? Describir brevemente 2–3 observaciones cualitativas del
> comportamiento.

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
  [ ] Completar §7.4 con datos del primer entrenamiento (curva de convergencia,
       explained_variance, timesteps hasta convergencia)
  [ ] Completar §7.5 con evaluación del RL sobre SC-NOM-01
  [ ] Añadir Figura 7.1: curva de convergencia ep_rew_mean vs timesteps
  [ ] Añadir Figura 7.2: comparación trayectorias RL vs PD en el óvalo
  [ ] Tarea TS-01: cablear GazeboLaneEnv con /raw_action → /safe_action
       (D-34 enforcement mode durante training)
  [ ] Añadir perturbación aleatoria de spawn en GazeboLaneEnv.reset()
  [ ] Registrar training runs en experiments/sim/training/
  [ ] Decidir si aumentar total_timesteps si no converge en 50k

Fase 4–5:
  [ ] Evaluar sobre todos los escenarios SC-NOM, SC-EDGE, SC-PERT
  [ ] Añadir análisis multi-semilla (N≥5)

Fase 6 (consolidación):
  [ ] Pulido de prosa
  [ ] Verificar coherencia cruzada §7.2.3 (pesos recompensa) con
       resultados del Capítulo 8 si se revisan los pesos
-->
