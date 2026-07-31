# Capítulo 9 — Caracterización del Gap Sim-to-Real

Convención: las secciones marcadas [BORRADOR POST-G4] contienen prosa provisional
redactada tras el cierre de G4 (02.07.2026); la evidencia posterior incorporada
se extiende hasta el 31.07.2026 (estudio de algoritmos SAC en Gazebo §7.5.5, la
calibración D-43→C-02 del readout de rumbo en Gazebo, y el brazo de acción 2-D
de Gazebo hasta la campaña de la policy PPO 550k, cerrada el 31.07.2026 — cap. 8
§8.9.7–§8.9.9). Las secciones marcadas [ESQUELETO — F5] son encabezados a
poblar cuando exista la evidencia correspondiente (campaña Isaac cerrada /
corridas físicas de Fase 5).
Este capítulo materializa la adaptación **A5** del V-Model (L1' reformulada como
Operational Validation con caracterización del gap): el testing en simulación no
equivale a validación operacional, y la diferencia se **mide**, no se asume.

---

## 9.1 Introducción: el gap como objeto de estudio  [BORRADOR POST-G4]

Los capítulos 7 y 8 cierran la evaluación del sistema **en Gazebo**, que es el
entorno portador de todos los veredictos de esta tesis (G4, 02.07.2026). Este
capítulo aborda la pregunta que esos veredictos dejan deliberadamente abierta:
¿qué parte de esa evidencia se sostiene fuera del simulador en que se produjo?

La estrategia no es un salto único simulación→hardware sino una **escalera de
fidelidad en tres peldaños**: (i) Gazebo, donde viven los veredictos congelados;
(ii) un puente de mayor fidelidad en **Isaac Sim** (PhysX + RTX, D-44),
introducido para estrechar el gap y destapar discrepancias *antes* de tocar la
plataforma; y (iii) el despliegue en la **CobraFlex 1:14 física** (Fase 5). Cada
peldaño conserva las especificaciones (hazards, SRs, reglas, escenarios, métricas
— escritas en abstracto precisamente para esto, docs/08 §8) y cambia la
realización. El contrato de transferencia es explícito:

- **Transfiere:** el código del entorno (interfaz duck-typed de `GazeboLaneEnv`),
  la cage pura-Python + `cage.yaml`, las especificaciones de escenario y SR, y el
  handover spec de interfaces ROS2 (docs/14: `/cmd_vel`, `/odom_truth`,
  `/camera/image_raw_lane` 640×360 @ ≥20 Hz, `/clock`, `/tf`).
- **No transfiere:** los checkpoints de policy. Una policy en Isaac o en físico
  es un **re-entrenamiento y una nueva línea base**, nunca una repetición del
  E-main de 297k; nada en este capítulo reabre G4 (D-49).

El veredicto de la tesis reposa hoy sobre Gazebo y se reporta como **evidencia
principal provisional**; si la campaña de Isaac madura como resultado más
fuerte, el veredicto se re-enuncia con esas cifras como finales (decisión
registrada en ch.1 §1.7 y ch.8 §8.8.2).

---

## 9.2 Peldaño 1 — el puente Isaac Sim (D-44): estado y primeros resultados  [BORRADOR POST-G4]

### 9.2.1 Qué se construyó

El puente comprende: la importación URDF→USD del vehículo
(`cobraflex_isaac.urdf`), el bring-up ROS2 contra Isaac con el contrato de
docs/14, y un **entrenador RL in-process** (D-44: el bucle de RL corre dentro del
proceso de Isaac, sin el overhead del puente ROS2 durante el entrenamiento), con
randomización de dominio y evaluador nominal integrado. Sobre él, dos extensiones
que Gazebo no tenía entonces: la **acción 2-D** (dirección + throttle, D-50), que
da a la policy autoridad longitudinal real hasta
`max_speed = 0.5 m/s = ODD-1.V_MAX` y hace **bien-puesto el test de stall de
SR-009** (M-P6 deja de ser ≡ 0), y el **muestreo multi-circuito por episodio**
sobre el trío CV-safe `complex_b`/`complex_d`/`complex_e` (D-50/D-51, con
`complex_e` re-cortado en sentido horario para equilibrar la lateralidad del
steering). De las dos, **la acción 2-D volvió a Gazebo** —el mismo mapa
`steer_throttle`, pero con cap 0,22 m/s tras la revisión D-59 de la envolvente de
velocidad (cap. 7 §7.2.2)—, y es allí donde el test de stall de SR-009 se ejecutó
y se cerró (cap. 8 §8.9.7, D-63/D-64) y donde corre la campaña de veredicto 2-D
(§8.9.8–§8.9.9). El muestreo multi-circuito sigue siendo exclusivo de Isaac.
Todo el stack fue
validado en vivo extremo-a-extremo en el host Ubuntu + Isaac (importación, escena
de tres circuitos, aislamiento de la Lane Cam, piloto 2-D de 20k — CHANGELOG
03.07.2026).

### 9.2.2 El diagnóstico como resultado: la escalera T1–T6

El intento de re-entrenamiento 2-D en Isaac no convergió a la primera, y el
proceso de raíz-causado es en sí mismo la primera medición del gap
inter-simulador (Hallazgo 12, cap. 12). La cadena, en orden de descubrimiento:

1. **Colapso de exploración** (iteración 1, D-52) → `ent_coef 0.01`; la
   iteración 2 lo **falsificó** como causa única (D-53).
2. **Curriculum de DR por etapas** (D-53): la etapa 1 (DR solo-visual) completó
   1M sana (pico 223.4) pero se estancó en ~0.63 vueltas nominales.
3. El muro de 0.63 vueltas se raíz-causó **al entorno, no a la policy** (D-54):
   un techo de autoridad de yaw del backend PhysX (calibrado con sondas de
   paridad CV: `yaw_gain` 0.8 → 2.4) más una **lectura desplazada del estimador
   CV bajo el renderer RTX** (recalibración de C-02 en una variante dedicada
   `cage_isaac.yaml`, D-55, y de-bias de heading del estimador, D-57).
4. La acción 2-D reveló además un **óptimo degenerado de "aparcar"** (quedarse
   quieto maximiza supervivencia): neutralizado con el término de reward
   `stall_penalty` (D-56).

Dos lecciones de este peldaño ya **portaron de vuelta a Gazebo** tras el filtro
de qué es backend-agnóstico y qué es específico del renderer/cinemática (D-59):
el curriculum de spawn en secciones difíciles (`random_start_s`, D-58) y la
configuración 2-D de Gazebo (que deliberadamente **no** hereda `yaw_gain 2.4` ni
`cage_isaac.yaml` — la cinemática DiffDrive de Gazebo es ~1:1 y su estimador está
calibrado a 25°).

Que la clase de discrepancia sea real —y no un artefacto de Isaac— quedó
confirmado de forma independiente dentro de **Gazebo mismo**: al preparar el
parent 2-D margin022, el readout de rumbo del estimador CV bajo el renderer Lane
Cam exhibió su propio sesgo dependiente de curvatura, que hubo de medirse y
calibrarse con una prueba controlada (D-43→C-02, 21.07.2026): estimador
`joint_pair_quadratic` con ganancia de medición 1.60, validado con 6/6 fallos de
rumbo detectados y 0 falsos C-02/C-05 sobre 392 ciclos centrados, ligado por hash
al renderer y a la geometría `complex_b` (docs/12 §4.9). Es el análogo
Gazebo-interno del sesgo de heading que en Isaac exigió D-55/D-57: la lección A5
—*el estimador de percepción debe re-calibrarse a cada renderer, y esa
discrepancia se mide, no se hereda*— aparece por tanto en dos entornos
distintos, lo que la eleva de anécdota a patrón. **[FIGURA SUGERIDA:** dispersión
GT-vs-CV y separación de distribuciones seguro/fallo de la calibración D-43
—las gráficas ya existen en
`experiments/sim/eval_gz2d/d43_c02_calibration_20260721T082128Z/`
(`epsi_gt_vs_cv_validation.png`, `epsi_abs_distribution_validation.png`)— como
ilustración compacta de "la discrepancia es medible y calibrable".]**

### 9.2.3 Resultados de la campaña Isaac  [ESQUELETO — pendiente]

*(A poblar cuando exista un run 2-D de Isaac con eval nominal aceptable y, en su
caso, una campaña de escenarios. Contenido previsto: curva de entrenamiento del
run final, eval nominal multi-modo y activación real del arbitraje C-04/C-06 a
0.5 m/s; contraste de métricas contra el peldaño Gazebo. Nota: la verificación
bien-puesta de SR-009 ya **no** depende de este peldaño —se cerró sobre la acción
2-D de Gazebo (cap. 8 §8.9.7, D-63/D-64)—, de modo que Isaac aportaría aquí una
réplica de backend, no la primera medición.)*

- Entrenamiento final y selección de checkpoint — [TBD]
- Eval nominal (enforcement + monitoring) — [TBD]
- SR-009 bien-puesto: resultado del brazo de stall — [TBD]
- Contraste Gazebo↔Isaac por métrica — [TBD]

---

## 9.3 Peldaño 2 — despliegue físico (Fase 5)  [BORRADOR POST-G4 — plan; resultados ESQUELETO]

### 9.3.1 Plataforma y ODD físico

La plataforma es la CobraFlex 1:14 real: tracción **diferencial/skid-steer**
(cuatro ruedas fijas, sin ángulo de dirección — el plugin DiffDrive de la
simulación es fiel a esta cinemática), `wheel_radius` 0.03725 m, separación
0.154 m, aceleración máxima medida 0.53 m/s², crucero 0.20 m/s. Percepción: Lane
Cam IMX219-160 sobre Jetson (captura CSI 1280×720 @ 60 fps, procesada a 640×360,
HFOV 90° — la simulación modela exactamente el stream procesado), ZED Mini y
RPLiDAR A2M4 fuera del camino RL. El dominio operacional físico, `ODD-PHYS-1`
(docs/08 §8.1), se especifica en F5 como el análogo hardware-realizable de
ODD-1/ODD-3: misma escenografía, exclusiones y asunciones de salida, con el
envelope dinámico y las latencias medidos en la plataforma. El único parámetro
genuinamente no-medible en simulación, `ODD-3.A_LAT_MAX` (TBD-Q10), se cierra
aquí vía la calibración M-4. La caracterización del hardware (masas, inercias,
latencias de actuación, condiciones de pista documentadas con fotografía y
medida) se produce como apéndice propio antes de cualquier corrida con veredicto.

### 9.3.2 Diseño experimental físico

El presupuesto de corridas físicas es deliberadamente pequeño (orden de 30), y
la pregunta que gobierna cada afirmación del capítulo es: *¿qué pueden afirmar
honestamente treinta corridas físicas?* El subconjunto exportado de la biblioteca
(docs/05 §"Subset for physical deployment"): **SC-NOM-01** (obligatorio, el
escenario de comparación de referencia), **SC-NOM-02** (si la geometría de la
pista física admite curvas) y **SC-EDGE-01** (activación de cage bajo
perturbación controlada; solo enforcement — observar la cage es el propósito).
Disciplina anti-parcheo: el sistema se ejecuta **tal como salió de Fase 4** —sin
ajustar ganancias, umbrales ni filtros entre corridas—; los ajustes que el
comportamiento físico sugiera se documentan como trabajo futuro, no se aplican
durante los experimentos.

### 9.3.3 Resultados físicos  [ESQUELETO — F5]

- Caracterización del hardware y de la pista (apéndice) — [TBD F5]
- SC-NOM-01 físico: métricas por corrida y agregados — [TBD F5]
- SC-NOM-02 / SC-EDGE-01 físicos — [TBD F5]
- Corrección funcional de la cage en hardware (¿dispara cuando debe, con la
  latencia presupuestada?) — [TBD F5]

---

## 9.4 La tabla de gap  [ESQUELETO — F5; columnas sim pobladas]

Núcleo cuantitativo del capítulo: una fila por métrica clave, con valor en
simulación, valor físico, gap absoluto/relativo e interpretación. Los valores de
simulación de referencia (brazo de cámara, SC-NOM-01, enforcement) ya están
fijados, ahora en dos columnas: la 1-D del E-main 297k, que es la referencia
histórica, y la **2-D del checkpoint 550k**, que es la policy que efectivamente se
despliega en F5 y por tanto la fila de contraste relevante. La columna física se
puebla en F5.

| Métrica | Sim 1-D (Gazebo, E-main 297k) | **Sim 2-D (Gazebo, 550k — la que se despliega)** | Isaac | Físico | Gap | Interpretación |
| --- | --- | --- | --- | --- | --- | --- |
| M-P1 — \|ey\| medio | 10.9 mm | **8.6 mm** (máx. 27.3 mm) | [TBD] | [TBD F5] | — | — |
| M-P2 — vueltas / completion | 4.88 vueltas (4k4) | **5.32 vueltas** | [TBD] | [TBD F5] | — | — |
| M-S1 — máx. desviación lateral | < `d_max` en todos los runs in-ODD | < `d_max` en todos los runs in-ODD; **0 contactos con el borde in-ODD** en enforcement | [TBD] | [TBD F5] | — | — |
| M-S3 — paros de emergencia | 0 (nominal) | **0** (nominal; 0 intervenciones de seguridad) | [TBD] | [TBD F5] | — | — |
| M-I1 — tasa de intervención | 43.5 % (C-06 únicamente) | **76.1 %** (C-06 únicamente) | [TBD] | [TBD F5] | — | — |
| Velocidad de operación | 0.200 m/s fija (`ACT_DIM = 1`) | **≈0.216 m/s** bajo cap 0.22 (`ACT_DIM = 2`) | [TBD] | [TBD F5] | — | — |
| Latencia de control extremo-a-extremo | 50 ms nominal (ODD-1.T_CTRL) | 50 ms nominal (ODD-1.T_CTRL) | [TBD] | [TBD F5] | — | — |

La columna que importa para F5 es la **2-D**: es la policy que se despliega, y es también
la que introduce el riesgo de transferencia más concreto de todo el trabajo. Su tasa de
intervención de C-06 sube de 43.5 % a **76.1 %** porque su flujo de comandos crudo es
~2× más brusco que el de su predecesora, hasta el punto de que **sin cage no sostiene** la
corrida de resistencia de 300 s (17/25 runs terminan `off_road`), mientras que con cage
conduce mejor que ninguna otra policy del repositorio. Es decir: la pareja
*(policy + C-06)* es el objeto que se transfiere, no la policy sola. Como en la plataforma
física la dinámica del actuador **no** es el limitador de slew simulado, el gap a vigilar
primero no es `|ey|` sino el comportamiento de C-06 y su
`delta_max_steering_per_cycle` (riesgo declarado **T2**; cap. 8 §8.9.9).

*(Se añadirán las filas del baseline F que apliquen y las métricas de la cage
—latencia de disparo, duración de intervención— cuando el subset físico las
produzca.)*

---

## 9.5 Análisis de divergencias  [ESQUELETO — F5]

*(A poblar: qué métricas degradan más y por qué; clasificación de divergencias
—dinámica, percepción, latencia, superficie—; qué hazards anticipados se
manifestaron en físico y si emergió alguno no anticipado; lectura de si los
veredictos de G4 se sostienen, se matizan o se invalidan por métrica. La
experiencia del peldaño Isaac (§9.2.2) sugiere las dos primeras categorías donde
buscar: autoridad de actuación y sesgo del estimador de percepción bajo otro
"renderer" — en físico, la óptica y la iluminación reales.)*

---

## 9.6 Síntesis y transición al Capítulo 10  [BORRADOR POST-G4 — PROVISIONAL]

Al cierre de este borrador, el peldaño Gazebo está completo y congelado; el
peldaño Isaac tiene la infraestructura validada extremo-a-extremo y un proceso
de calibración inter-simulador documentado cuyo primer resultado es
metodológico: **las discrepancias entre entornos son medibles, raíz-causables y
calibrables, pero no son silenciosas** — cada una hubo que descubrirla con
sondas dedicadas (D-54/D-55/D-57). Esa es exactamente la forma que la adaptación
A5 predice para el gap Gazebo→físico, y la razón por la que la validación
operacional del Capítulo 10 se declara **acotada** al dominio donde la evidencia
existe. El Capítulo 10 consolida los veredictos por SR con esa acotación
explícita; cuando la Fase 5 aporte la columna física, la declaración se
re-enuncia sobre la tabla de gap de §9.4.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: BORRADOR POST-G4 (16.07.2026). Secciones 9.1-9.3.2 y 9.6 con prosa
provisional; 9.2.3, 9.3.3, 9.4 (columnas Isaac/físico) y 9.5 son esqueleto.

  [ ] Poblar §9.2.3 cuando el run 2-D Isaac (v6+ / SAC tuned, T6 del cap. 12)
       produzca un eval nominal citable; decidir si la campaña Isaac se eleva a
       evidencia de veredicto (re-enunciado) o queda como puente interno.
  [ ] F5: caracterización hardware + pista → apéndice; poblar §9.3.3, §9.4, §9.5.
  [ ] Verificar los valores sim de la tabla §9.4 contra
       experiments/sim/runs/rl_newcam_eval_2024_cb297k_4k4/ al pulir.
  [ ] Decidir dónde vive el detalle Isaac que hoy está en docs/13 (¿anexo?).
  [ ] Figura candidata: la escalera de fidelidad (reutilizar/adaptar Fig. 8.2,
       sim2real_roadmap.mmd).
-->
