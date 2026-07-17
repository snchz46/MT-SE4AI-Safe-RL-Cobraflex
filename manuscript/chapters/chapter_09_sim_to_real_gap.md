# Capítulo 9 — Caracterización del Gap Sim-to-Real

Convención: las secciones marcadas [BORRADOR POST-G4] contienen prosa provisional
redactada tras el cierre de G4 (02.07.2026) con la evidencia disponible a
16.07.2026; las marcadas [ESQUELETO — F5] son encabezados a poblar cuando exista
la evidencia correspondiente (campaña Isaac cerrada / corridas físicas de Fase 5).
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
que Gazebo no tiene: la **acción 2-D** (dirección + throttle, D-50), que da a la
policy autoridad longitudinal real hasta `max_speed = 0.5 m/s = ODD-1.V_MAX` y
hace **bien-puesto el test de stall de SR-009** (M-P6 deja de ser ≡ 0), y el
**muestreo multi-circuito por episodio** sobre el trío CV-safe
`complex_b`/`complex_d`/`complex_e` (D-50/D-51, con `complex_e` re-cortado en
sentido horario para equilibrar la lateralidad del steering). Todo el stack fue
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

### 9.2.3 Resultados de la campaña Isaac  [ESQUELETO — pendiente]

*(A poblar cuando exista un run 2-D de Isaac con eval nominal aceptable y, en su
caso, una campaña de escenarios. Contenido previsto: curva de entrenamiento del
run final, eval nominal multi-modo, primera verificación bien-puesta de SR-009
—stall arm— y activación real del arbitraje C-04/C-06 a 0.5 m/s; contraste de
métricas contra el peldaño Gazebo.)*

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
simulación de referencia (brazo de cámara, E-main 297k, SC-NOM-01, enforcement)
ya están fijados; la columna física se puebla en F5.

| Métrica | Sim (Gazebo, E-main) | Isaac | Físico | Gap | Interpretación |
| --- | --- | --- | --- | --- | --- |
| M-P1 — \|ey\| medio | 10.9 mm | [TBD] | [TBD F5] | — | — |
| M-P2 — vueltas / completion | 4.88 vueltas (4k4) | [TBD] | [TBD F5] | — | — |
| M-S1 — máx. desviación lateral | < `d_max` en todos los runs in-ODD | [TBD] | [TBD F5] | — | — |
| M-S3 — paros de emergencia | 0 (nominal) | [TBD] | [TBD F5] | — | — |
| M-I1 — tasa de intervención | 43.5 % (C-06 únicamente) | [TBD] | [TBD F5] | — | — |
| Latencia de control extremo-a-extremo | 50 ms nominal (ODD-1.T_CTRL) | [TBD] | [TBD F5] | — | — |

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
