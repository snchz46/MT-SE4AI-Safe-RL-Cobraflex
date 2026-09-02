# Capítulo 9 — Caracterización del Gap Sim-to-Real

Convención: las secciones marcadas [BORRADOR POST-G4] se redactaron tras el
cierre de G4 (02.07.2026). La evidencia posterior incorporada llega hasta el
**01.09.2026**: el estudio de algoritmos SAC en Gazebo (§7.5.5), la calibración
D-43→C-02 del readout de rumbo, el brazo de acción 2-D hasta la campaña de la
policy PPO 550k (cap. 8 §8.9.7–§8.9.9, cerrada el 31.07.2026) y **la Fase 5
completa** —reentrenamiento orientado a transferencia, despliegue físico y las
tres sesiones del 31.08— cerrada el 01.09.2026 (D-70…D-80, docs/17).
**Toda la evidencia de Fase 5 es posterior: no re-puntúa ninguna puerta ni toca
el veredicto de récord D-69.** La única sección que permanece en esqueleto es
§9.2.3 (campaña Isaac), y permanece así **por decisión**: esa campaña no se
ejecutó y no se ejecutará dentro del alcance de este trabajo.
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

El veredicto de la tesis reposa sobre Gazebo, y **así queda**. La opción
registrada en ch.1 §1.7 y ch.8 §8.8.2 —re-enunciar el veredicto con cifras de
Isaac si esa campaña maduraba como resultado más fuerte— **no se ejerció**: la
campaña Isaac no llegó a producir un eval nominal citable dentro del alcance del
trabajo (§9.2.3), de modo que el peldaño Isaac se reporta por lo que sí produjo,
que es un resultado metodológico negativo y útil (§9.6). El veredicto de récord es
y sigue siendo el de la campaña 2-D PPO 550k en Gazebo (D-69).

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

### 9.2.3 Resultados de la campaña Isaac — NO EJECUTADA

**Esta sección se declara no ejecutada, no pendiente.** El puente Isaac no llegó a
producir un run 2-D con eval nominal citable dentro del alcance temporal del
trabajo, y el esfuerzo se reasignó al peldaño físico —que era el objetivo de la
escalera— cuando quedó claro que Isaac no era el cuello de botella. Lo previsto
era: curva de entrenamiento del run final, eval nominal multi-modo con activación
real del arbitraje C-04/C-06 a 0.5 m/s, y contraste de métricas contra el peldaño
Gazebo.

Nada depende de ello. La verificación bien-puesta de **SR-009** ya **no** requiere
este peldaño —se cerró sobre la acción 2-D de Gazebo (cap. 8 §8.9.7, D-63/D-64)—,
de modo que Isaac habría aportado aquí una réplica de backend y no una primera
medición. Lo que el peldaño sí produjo, y es lo que este capítulo reporta, es el
resultado de §9.2.2: **las discrepancias entre entornos son medibles,
raíz-causables y calibrables, pero no son silenciosas**, y los checkpoints no
transfieren entre simuladores (D-49/D-54/D-55/D-57). Ese resultado negativo es el
que calibró la expectativa sobre el salto a hardware, y el hardware lo confirmó
(§9.3.3a). La continuación figura como trabajo futuro T6 (cap. 12), no como un
hueco de este capítulo.

---

## 9.3 Peldaño 2 — despliegue físico (Fase 5)  [BRING-UP EJECUTADO 08.2026 · FASE CERRADA 01.09.2026 — **campaña de resultados NO EJECUTADA**]

> **Estatus de esta sección, y hay que leerlo antes que sus cifras.** Lo que
> sigue es el **bring-up** del peldaño físico, no su campaña de resultados. Se
> distingue deliberadamente entre dos clases de evidencia, porque tienen
> valor probatorio distinto:
>
> * **Medidas de calibración y hallazgos estructurales** (§9.3.1, §9.3.2,
>   §9.3.3a, §9.3.3d). No dependen de una campaña: una metrología contra
>   patrón, una regresión sobre 5665 ciclos, dos pares A/B controlados y una
>   comparación aritmética de umbrales. **Son resultados**, y se citan como
>   tales.
> * **Cifras de conducción** (§9.3.3c y la columna física de §9.4). Provienen
>   de **una única corrida**, en `monitoring`, fuera del protocolo de
>   escenarios y sobre un contrato de percepción distinto del puntuado. Son
>   **preliminares**, tienen N=1, y la campaña física las sustituirá.
>
> Ninguna de las dos clases produce `verdict_phys`, y la sección no lo
> pretende. El capítulo se re-enuncia sobre §9.4 cuando la campaña exista.

### 9.3.1 Plataforma y ODD físico

La plataforma es la CobraFlex 1:14 real: tracción **diferencial/skid-steer**
(cuatro ruedas fijas, sin ángulo de dirección — el plugin DiffDrive de la
simulación es fiel a esta cinemática), `wheel_radius` 0.03725 m, separación
0.154 m. La primera caracterización sobre el vehículo (**D-70**, 17.08.2026)
corrigió tres cosas que este capítulo había dado por medidas: la masa total es
**3.5 kg** y no los 6.59 kg del presupuesto URDF (1.88× de exceso, reescalado);
el seguimiento en línea recta transfiere ≈0.99 de lo comandado, pero el de
**guiñada solo 0.4954×**, lo que **divide por dos todo margen de la cage
expresado en dirección** sobre hardware (riesgo de transferencia **T2**;
compensado en despliegue vía `steering_to_yaw_rate_gain 0.8 → 1.615`); y la
«aceleración máxima medida de 0.53 m/s²» que esta sección, docs/09, docs/13,
docs/14 y `cage_bridge.py` citaban **era la velocidad máxima del chasis en m/s
copiada a un campo de aceleración** — las cifras de plataforma son ±2.5 m/s² y
3.2 rad/s². Toda conclusión sobrevive con un margen 5× mayor; `cage.yaml` sin
tocar. La velocidad de operación desplegada es **0.22 m/s** (el cap del trunk
2-D), no los 0.20 m/s del brazo 1-D.

Percepción: Lane Cam IMX219-160 sobre Jetson (captura CSI 1280×720 —a **30 fps**
desde 26.08.2026, ver §9.3.6—, procesada a 640×360), ZED Mini y RPLiDAR fuera del
camino RL. **El HFOV es el hallazgo de §9.3.2 y no un parámetro de esta lista.**
El dominio operacional físico, `ODD-PHYS-1` (docs/08 §8.1), se especifica como el
análogo hardware-realizable de ODD-1/ODD-3. El único parámetro genuinamente
no-medible en simulación, `ODD-3.A_LAT_MAX` (TBD-Q10), **sigue abierto**: M-4 no
ha producido medida de aceleración lateral, y docs/08 permanece por debajo de
v1.0 por esa razón.

### 9.3.2 La verificación bloqueante se ejecutó y falló (M-6 / M-7)

El elemento marcado `[VERIFY]` era el HFOV efectivo de la Lane Cam: un valor por
defecto de configuración que la simulación **replicó**, de modo que ningún
resultado de simulación podía exponer un error en él, y que escala toda magnitud
lateral sobre la que la cage actúa. **M-6** (17.08.2026) lo midió y lo refutó:
el HFOV horizontal efectivo es **77.89°**, `fx` **395.93 px** y no 320.

**M-7** (18.08.2026) midió la consecuencia contra cinta métrica, con el coche
desplazado a mano sobre ±100 mm y 15 puntos: el estimador D-43 lee
`ey ≈ 0.68–0.83 × verdadero − 10 mm`, robusto a todo filtrado. Traducido a la
cage: **C-01 dispara con el coche a 207–241 mm reales** en lugar de a sus 160 mm
nominales, dejando 14–48 mm hasta el borde en vez de 95. El **ancho de carril**,
en cambio, se lee bien (252.9 mm contra regla de 250, 95.4 % de fotogramas del
circuito emparejados) porque un ancho es una *diferencia* que abraza el eje
óptico mientras `ey` es una *posición absoluta* fuera de él, y el término barril
no modelado `k1 = −0.339` comprime solo la segunda. Dos defectos más en la misma
banda donde actúan C-01/C-05: repetibilidad (media 13.2 mm, peor 29.4, contra una
cinta de ~2 mm) y **colapso del emparejamiento más allá de ~±55 mm**.

> **RETRACTADO PARA LA RUTA DESPLEGADA (31.08.2026, docs/17 §10.2).** Los tres
> defectos de offset de M-7 §4 se midieron **sin rectificar** y **no sobreviven a
> la rectificación**. La mitad `--true-ey` de M-7 §3b —la medida pendiente que el
> propio §9.5 señalaba como la de mayor valor por coste— se ejecutó: barrido de
> nueve puntos, coche en el suelo, sin tocar, rectificado, y da escala **1.058
> izquierda / 0.991 derecha con el término independiente desaparecido**. Es decir
> **C-01 dispara a un `ey` verdadero de 151/158 mm, con ~100 mm de margen al
> borde**, no a 207–241 mm con 14–48. Las cifras de arriba caracterizan la ruta
> **cruda** y se conservan porque son la evidencia que motivó la decisión de
> rectificar; **ninguna regla de la cage debe ajustarse a partir de ellas**. Lo
> que sí sobrevive intacto es la prescripción de M-7 —*rectificar, no
> reparametrizar*—, que es exactamente lo que esta medida vindica.

La corrección adoptada **no es reparametrizar el estimador a 77.89° sino
rectificar** el fotograma real hacia el modelo canónico, de modo que una sola
proyección sirva a las campañas y al coche. Su efecto está medido sobre hardware
por un A/B controlado con el coche parado y sin tocar (docs/17 §8.3): ciclos con
percepción inválida **45 % → 5.5 %**, `ey` medio **−97.7 → +7.7 mm**, sd
104.5 → 27.8 mm, activaciones de **C-01 102 → 0**. La mitad `--true-ey` de M-7
§3b sigue abierta.

Metodológicamente es el hallazgo que mejor justifica que A5 exija el peldaño
físico: **una suposición que la simulación heredó, y que por tanto la simulación
no podía falsar, estaba equivocada y estaba en el camino de una regla de
seguridad.**

### 9.3.3 Resultados del bring-up físico

**(a) El trunk 550k no transfiere (D-71, 18.08.2026).** Con el coche desplazado a
mano sobre 332 mm de `ey` y la cadena corriendo sin actuación
(`experiments/physical/runs/policy_bias_probe/`, 5665 ciclos):
`steer = −0.000166·ey_mm + 0.1155`, `r = −0.243`, `r² = 0.059`. Signo correcto,
amplitud un orden de magnitud corta: la excursión dependiente del carril sobre
los 332 mm completos es **0.055** contra un **sesgo constante de +0.1155**, es
decir **2.1× la excursión entera**, y solo **29 de 5665 muestras (0.5 %)** ordenan
giro a derechas. En lazo cerrado el sesgo domina. La causa es la pista:
`complex_b` recorrido en el sentido de entrenamiento presenta **~13 m de arco a
izquierdas contra ~2 m a derechas por vuelta (6.5:1)**, y el log de acciones
mantiene la dirección media en +0.112…+0.120 **plana durante 284 672 pasos**. Es
lateralidad de pista memorizada como sesgo de mando: propiedad de la distribución
de entrenamiento, no del hardware.

**(b) El reentrenamiento sim-to-real v2 (D-72).** El gap se descompone en tres
términos, solo el primero propiedad de la pista: **lateralidad** (observación y
acción espejadas por episodio, `mirror_rate` medido 0.527), **fotometría** (75 %
de episodios en la banda medida de la nave, 25 % al render de Gazebo) y
**geometría de cámara** (pitch del soporte ±1.5°, altura ±10 %, 10 % de episodios
con la lente medida completa). Run `ppo_gz2d_sim2real_v2_2024_r2`, **2 500 544
pasos, completado**. Punto de control de récord **1 650 000**, elegido por
transferencia y **por independencia de la cage, nunca por recompensa**: r² 0.440,
bias/swing 0.10, cuota de giro a derechas 62.1 %, y **3.0 %** de intervención
nominal frente al **35.0 %** del pico de recompensa. El segundo criterio es
deliberado — D-69 declaró **T2**, el acoplamiento a
`delta_max_steering_per_cycle`, como el riesgo de transferencia concreto. El
término de lateralidad queda cerrado: bias/swing **0.07–1.10** contra
**12.9–19.2** del trunk tal como se desplegó. Preflight D-43 **PASS** en 325k /
1650k / 2000k. Detalle en docs/11 §8.6.

**(c) Transfiere — primera medida, N=1 (26.08.2026).** [PRELIMINAR]
El checkpoint 1650k recorrió **18.05 m del
circuito real en un único tramo ininterrumpido de 101.1 s**, sin reset de
operador, `|ey|` mediano **18.7 mm** (p90 44.7, máx 98.7 contra el `d_max` 160 de
C-01), `|epsi|` máx **18.91°** contra los 25° de C-02, `cycles_since_last_state`
nunca > 0. **Ninguna regla de seguridad se activó**; la única que actuó fue C-06,
en el **3.4 % de los ciclos en movimiento contra el 3.0 % de simulación**. Esa
pareja de cifras es la **primera medida de T2**: el riesgo se declaró antes de
tocar hardware y **la primera corrida no lo materializa**. Con N=1 eso no es una
refutación —la campaña puede desmentirlo—, pero la distancia entre 3.4 y 3.0 no
es marginal y la dirección es la contraria a la temida.

**(d) Lo que detiene al coche, y ninguno es la política.** El recorrido terminó
**2.11 m antes de cerrar el circuito** (314° de 360°) por **un único pulso de
400 ms** de `/perception_invalid`, con el coche a **27 mm del centro** en la curva
más cerrada (`kappa` 0.75 1/m): **C-05** enclavó y `require_explicit_reset` lo
mantuvo enclavado los 396 s restantes. La regla hizo lo especificado; el hueco
está entre un artefacto validado contra episodios simulados —que terminan— y un
vehículo que debe seguir operando (**D-74**: C-05 intacta, vía de rearme fuera de
la cage). Dos más de la misma clase: la odometría de la ZED **salta** al cerrar
bucle y, como el ekf fusiona su pose y no su twist, el salto entra en la cage como
pico de velocidad —3621.8 mm en un fotograma, 5.479 m/s contra un contrato de
0.22, disparando C-04→C-03→C-05—; desactivar el cierre de bucle lo elimina, con
saltos por fotograma **116 → 0** en 509 s (**D-73**). Y **C-04 no puede disparar
nunca** en la configuración desplegada (`v_max_curve_mps` 0.25 > 0.22): lo que
D-69 registró como hueco de cobertura es, en la curva más cerrada del circuito
real, **una regla que no protege un caso físico existente**.

### 9.3.4 Diseño experimental físico  [NO EJECUTADO — la Fase 5 cerró antes]

El presupuesto de corridas físicas era deliberadamente pequeño (orden de
30) y la pregunta que gobernaba cada afirmación no cambia: *¿qué pueden afirmar
honestamente treinta corridas físicas?* El subconjunto exportado (docs/05
§"Subset for physical deployment"): **SC-NOM-01** (obligatorio), **SC-NOM-02** y
**SC-EDGE-01**. **Ninguno se ha ejecutado bajo protocolo, y ninguno se ejecutará
dentro del alcance de este trabajo**: la Fase 5 se cerró el 01.09.2026 con la
base de evidencia física completa y sin campaña. La columna `verdict_phys` no
está *pendiente de medición*; está **declarada no ejecutada**, que es una
afirmación más fuerte y más honesta. Las condiciones que la separan de ser
poblable están medidas, no supuestas, y se enumeran en docs/17 §14 (términos 2,
9 y 12) y en §9.3.5 y §9.3.6b de este capítulo.

La disciplina anti-parcheo original —«el sistema se ejecuta tal como salió de
Fase 4, sin ajustar ganancias, umbrales ni filtros entre corridas»— **se
mantiene entre corridas y ha dejado de describir la configuración desplegada**,
que difiere de la de Fase 4 en cuatro puntos, cada uno una decisión registrada y
ninguno un ajuste sobre la marcha: la policy (v2 1650k, no el trunk 550k, D-71),
la rectificación activada (§9.3.2), `steering_to_yaw_rate_gain 1.615` (D-70) y el
`heading_fit_mode` (§9.3.5). Enunciar la disciplina como «igual que en Fase 4»
sería hoy inexacto; enunciarla como «sin parcheos entre corridas, y con las
diferencias respecto de Fase 4 registradas como decisiones» es lo que se hizo.

### 9.3.5 La decisión de percepción que bloquea el veredicto físico

Un par controlado sobre hardware (docs/17 §8.4, mismo modo, misma rectificación,
secuencial, solo cambia el ajuste de rumbo): `joint_pair_quadratic`/1.6 —**el
contrato D-43 bajo el que se puntuó toda campaña**— recorre **1.08 m** antes de
que el estimador parpadee inválido y C-05 detenga el coche; `near_secant`/1.0
recorre **14.45 m** con 0 ciclos inválidos. **Y parado ambos están quietos**
(sd_epsi 0.25° vs 0.80°, si acaso a favor del default), de modo que ningún test
de banco puede ver la diferencia.

Esto deja el veredicto físico bloqueado por una decisión, no por instrumentación:
el ajuste con el que el coche **puede** conducir no es el ajuste bajo el que se
puntuaron las campañas, y usar el primero pondría la cage desplegada sobre un
estimador distinto del de toda la evidencia de simulación. La decisión está
abierta (docs/17 §8.4).

---

### 9.3.6 Las dos medidas del 31.08: el lugar, y los tres bloqueos de la cage

Tres sesiones del 31.08 cierran el bring-up y reordenan su lectura. Ninguna
re-puntúa nada; todas son evidencia posterior (docs/17 §10, §12, §13; D-75…D-80).

**(a) La exactitud del estimador es una propiedad del lugar, no del movimiento
(D-79).** Captura de posición verdadera con estaciones de cinta en el suelo,
cámara sola, cuatro vueltas y cuatro sondas paradas (~11 500 fotogramas). El
criterio se fijó *antes*: en circuito cerrado `∮|κ|ds` vale 2π por vuelta. Falla
por ~2× (**1.97 / 2.01 / 2.25 / 2.37** contra banda 0.75–1.35) — la primera
medida del canal de curvatura que no debe nada a odometría, policy ni cage. Y el
resultado que reordena: el inicio de la recta empareja **96.7 %** con **7.2 mm**
de error, los tramos en movimiento **37.9–60.2 %**, y **paradas** sobre dos
puntos malos a `ey` verdadero 0 dan **0.0 % emparejado** (273 fotogramas) y
**−39.7 mm con sd 3.1 mm** — *confiadamente equivocado*, invisible a cualquier
puerta de dispersión. El inicio de la recta, donde se tomaron M-6, M-7 y todos los
`lanecheck`, **es el mejor punto del circuito**: el contenido de esas medidas se
mantiene, su generalización al trazado se retira. El mecanismo es **generación de
candidatas**, no selección del par (bordes de una misma franja, marcas
adyacentes), lo que invierte el arreglo obvio: un prior de continuidad temporal no
sirve, porque el par equivocado es estable a 3.1 mm.

**(b) Los tres bloqueos de la cage (D-80).** Tres corridas consecutivas en
`monitoring`, variando solo los parámetros de la vía de rearme, ninguna capaz de
mantener el coche en marcha, y las tres fallan por la **medida**: el hold de 1 s
de D-74 **no es satisfacible conduciendo** (48 % de 623 withholds son la espera
sin completarse); el escape documentado —quitar C-01 de `blocking_rules`— quema
**30 de 30 resets en un minuto**, cada uno reenclavando, con el coche parado a
`ey` = −296 mm; y al acortar el hold aparece C-02 disparando con el coche a
**20 mm del centro** y sd(`epsi`) **19.1°** contra los 5.3° que M-6 midió en el
buen punto. Esa última comparación es la **cuarta confirmación independiente de
D-79 y la primera en el canal de rumbo conduciendo**. D-76 ordenó ensanchar el
estimador antes de restringir la policy; esto es la medida que lo sostiene.

---

## 9.4 La tabla de gap  [COLUMNA FÍSICA PRELIMINAR — N=1, sin puntuar]

La primera lectura de la tabla no es una fila sino un encabezado: **la policy que
se despliega no es la que produjo el veredicto**. Esa sustitución es el resultado
(a) de §9.3.3, y significa que la columna física y las de simulación **no son un
contraste de igual a igual** — describen policies distintas, en modos distintos y
bajo contratos de percepción distintos. Se presentan juntas porque la comparación
sigue siendo informativa, y separadas en el encabezado porque tratarlas como una
diferencia limpia sería la afirmación sin evidencia que el marco existe para
impedir.

| Métrica | Sim 1-D (Gazebo, E-main 297k) | Sim 2-D (Gazebo, 550k — **la del veredicto**) | Isaac *(no ejecutada, §9.2.3)* | **Físico** *(PRELIMINAR: v2 1650k, `monitoring`, **una corrida**, sin puntuar)* |
| --- | --- | --- | --- | --- |
| M-P1 — \|ey\| mediano | 10.9 mm | **8.6 mm** (máx. 27.3 mm) | — | **18.7 mm** (p90 44.7; máx. 98.7) |
| M-P2 — recorrido continuo | 4.88 vueltas (4k4) | **5.32 vueltas** | — | **18.05 m en un tramo** (≈0.94 del perímetro) |
| M-S1 — desviación lateral máx. | < `d_max` in-ODD | < `d_max` in-ODD; **0 contactos de borde in-ODD** | — | 0 contactos; máx. 98.7 mm contra `d_max` 160 |
| M-S3 — paros de emergencia | 0 (nominal) | **0** (nominal) | — | **1**, por C-05 sobre percepción, con el coche en carril |
| M-I1 — tasa de intervención | 43.5 % (C-06) | **3.0 %** en el checkpoint desplegado (76.1 % en el 550k) | — | **3.4 %** (C-06 únicamente) |
| Velocidad de operación | 0.200 m/s fija | ≈0.216 m/s bajo cap 0.22 | — | ≤ **0.213 m/s** bajo el mismo cap |
| Cadencia del lazo de control | 10 Hz nominal | 10 Hz nominal | — | **8.68 Hz** medidos (`/state_obs` 9.84); 9.6 Hz sin lidar en capa 2 |

Tres lecturas.

**La fila que concentraba el riesgo ya no lo concentra.** El capítulo 8 §8.9.9
identificó M-I1 como el primer gap a vigilar, con el argumento de que lo que se
transfiere es la pareja *(policy, C-06)* y que el actuador físico no implementa
`delta_max_steering_per_cycle`. Elegido el checkpoint por independencia de la
cage, las dos cifras difieren en **cuatro décimas de punto porcentual**. El riesgo
estaba bien identificado y su mitigación funcionó. Nótese que la columna 2-D
cambia de valor por esta razón: **76.1 %** es la tasa del trunk 550k, y **3.0 %**
la del checkpoint que efectivamente se despliega.

**El error lateral se duplica, y era esperable.** 18.7 mm contra 8.6 mm, con un
estimador cuya exactitud depende del punto del circuito (§9.3.6a) y un lazo a
8.68 Hz en vez de los 10 Hz de entrenamiento. Sigue holgadamente dentro de
`d_max`; la cifra a vigilar es el máximo de 98.7 mm, no la mediana. **Lo que no
puede decirse ya** es que ese máximo corresponda a un valor real notablemente
mayor por la sub-lectura de M-7: sobre la ruta rectificada la escala es ~1.0
(§9.3.2, banner). El sesgo que sí queda es el **dependiente del lugar**, que puede
ir en cualquiera de los dos sentidos (+43.7 mm en un punto, −39.7 en otro) y que
sin captura de posición verdadera no puede aplicarse fila a fila.

**Y las tres lecturas son provisionales.** Salen de una corrida. La campaña
física —SC-NOM-01/02 y SC-EDGE-01, en los dos modos, con repeticiones— es la que
convierte esta columna en una tabla de gap y no en una anécdota bien instrumentada.

**La última fila es el gap abierto.** La cadencia es el único parámetro del
contrato de despliegue que el hardware aún no alcanza, y su causa está localizada:
no es la cámara —`/state_obs` sostiene 9.84 Hz tras el arreglo de captura— sino el
tiempo de inferencia de la CNN en `rl_policy_node`.

---

## 9.5 Primera lectura de divergencias  [PRELIMINAR — el análisis pleno requiere la campaña]

Lo que sigue clasifica lo observado durante el bring-up. Es una **hipótesis de trabajo sobre dónde estará el gap**, no su medida: sin campaña no hay distribución por escenario, ni separación por modo, ni repetición, y por tanto ninguna de estas categorías tiene todavía magnitud asociada más allá de la corrida única de §9.3.3c. Su valor es dirigir la campaña.

**Percepción — la divergencia dominante, y la única que invalidaba una
suposición.** El HFOV heredado (§9.3.2) es la única discrepancia medida que
**afectaba a un umbral de seguridad**. Se mitiga por rectificación y no por
reparametrización, y el residuo que §9.5 señalaba —la mitad `--true-ey` de M-7
§3b— **se midió el 31.08 y cerró en la dirección favorable**: sobre la ruta
rectificada la escala es 1.058/0.991 sin offset. Lo que quedó en su lugar es una
divergencia distinta y peor caracterizada: la exactitud del estimador **depende
del punto del circuito** (§9.3.6a), con sesgos de ±40 mm *confiadamente*
reportados y colapsos de emparejamiento al 0 % en puntos concretos, y ese es el
residuo de percepción que la campaña debe acotar.

**Actuación — anticipada por el peldaño Isaac, confirmada, y de forma no lineal.**
§9.2.2 predijo «autoridad de actuación» como primera categoría donde buscar; D-70
la encontró en la forma más limpia posible —**0.4954× de guiñada comandada**— y el
despliegue la compensa con `steering_to_yaw_rate_gain` 1.615. **M-7 §5 midió
además que la planta es compresiva**: la razón cae de 0.482 (cmd 0.2) a 0.436
(0.4) y 0.341 (0.8), de modo que ninguna ganancia constante la corrige — una
ganancia calibrada a demanda moderada sub-entrega exactamente donde C-01/C-02
corrigen. **Lo que NO está medido** es dónde termina esa compresión: si es una
compresión suave o una saturación dura, y con ella cuál es el `R_min` realmente
alcanzable. Esa medida está pendiente y su discriminador es de banco.

**Distribución de entrenamiento — la divergencia no anticipada.** Ninguna de las
categorías que §9.2.2 sugería (dinámica, percepción, latencia, superficie) cubre
lo que realmente impidió conducir: **la lateralidad 6.5:1 del circuito de
entrenamiento memorizada como sesgo de mando**. No es un gap entre entornos sino
un gap entre *distribuciones*, invisible en la pista donde se entrenó y en la
métrica que se optimizó. Es el aporte propio de este peldaño a la taxonomía.

**Latencia — degradada y localizada.** 8.68 Hz contra 10. La cadena de percepción
está sana; el déficit es de inferencia.

**¿Se sostienen los veredictos de G4?** Sí, y **ninguno se re-puntúa** — ni
podría hacerlo esta evidencia, que no es de campaña. Nada de la
Fase 5 toca la campaña de veredicto: D-69 sigue siendo el veredicto de récord y
GE4-V2 el registro congelado de G4. Lo que la Fase 5 **matiza** son dos
declaraciones del Capítulo 10: SR-004 se satisface con una regla, C-04, que en la
configuración física **no puede activarse sobre movimiento comandado** —el techo
de curva son 0.25 m/s y el cap desplegado 0.22 (D-75)— y que, sin embargo, **sí
se activó sobre artefactos de velocidad del ZED**: 58 y 40 ciclos en las dos
corridas enjauladas que sobreviven al 31.08, el 100 % de ellos a una velocidad
reportada de 0.25–1.30 m/s, imposible bajo su propia potencia, y en un caso
bloqueando la vía de rearme de la regla que él mismo había levantado. Una regla
que no protege el caso real que existe y que arbitra sobre uno que no existe es
un hallazgo más incómodo que un simple hueco de cobertura. Y el objeto validado
por esa declaración (la policy 550k) **no es el objeto que conduce**.

---

## 9.6 Síntesis y transición al Capítulo 10

El peldaño Gazebo está completo y congelado. El peldaño Isaac dejó un resultado
metodológico: **las discrepancias entre entornos son medibles, raíz-causables y
calibrables, pero no son silenciosas** — cada una hubo que descubrirla con sondas
dedicadas (D-54/D-55/D-57). El peldaño físico **está cerrado sin campaña** (01.09.2026): su bring-up se
ejecutó, su campaña de resultados no, y no se planifica más medición. Aun así el
bring-up produjo cuatro cosas que la simulación no podía producir, y tres de ellas
no dependen de que la campaña se corra: una **suposición falsada** que
estaba en el camino de una regla de seguridad (§9.3.2); un **resultado negativo**
sobre la policy validada, con causa identificada en la distribución de
entrenamiento (§9.3.3a); un **resultado positivo** sobre su reemplazo, que
además responde al riesgo T2 declarado de antemano (§9.3.3b–c); y una clase de
defecto que solo aparece con un vehículo delante — reglas correctas por
especificación sin comportamiento operacional definido, umbrales inactivables y
modos de fallo de sensor que entran directos en la única entrada de velocidad de
la cage (§9.3.3d).

Lo que **no** produce es ni un veredicto por escenario ni la tabla de gap por
escenario que este capítulo idealmente debería. La columna `verdict_phys` del
Capítulo 10 queda vacía, y por una razón enunciable con precisión: **la evidencia
física existe, es de bring-up y no está puntuada**, con tres condiciones
*medidas* que la separan de estarlo (§9.3.4, §9.3.5, y la vía de rearme de D-74;
docs/17 §14 términos 12, 2 y 9). El Capítulo 10 consolida los veredictos por SR
con esa acotación explícita.

Hay, en su lugar, un producto que la escalera sí entregó completo y que ningún
veredicto por escenario habría dado: **el balance del gap medido contra el gap
anticipado** (§9.5, docs/17 §14.1). Escribir la lista de gaps *antes* de tocar
hardware y conservarla sin editar convierte su fallo en un resultado — y el fallo
es sistemático, no aleatorio: la lista acertó los términos que un simulador sabe
representar y no contiene ninguno de los que efectivamente detuvieron al vehículo.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: 02.09.2026. FASE 5 CERRADA (01.09.2026) — la base de evidencia física es
final y no se planifica más medición. §9.3 (todo), §9.4 (columna física), §9.5 y
§9.6 poblados y reconciliados con docs/17 §14. §9.2.3 se declara NO EJECUTADA en
lugar de quedar en esqueleto.

  [x] §9.2.3: resuelto declarándola no ejecutada (02.09.2026). La campaña Isaac no
       se corrió y no se eleva a evidencia de veredicto; el peldaño se reporta por
       su resultado metodológico. Continuación en cap. 12 T6.
  [x] F5: §9.3.3, §9.4 (columna física) y §9.5 poblados (27.08.2026); §9.3.6
       (sesiones del 31.08) añadido y auditado (01.09.2026).
  [x] §9.3.5: la decisión de `heading_fit_mode` NO se cerró, y eso es el resultado
       — término 12 del ledger (docs/17 §14): todo lo que ha conducido usó
       `near_secant`, luego ninguna corrida física está bajo el contrato puntuado.
       Ya no bloquea nada porque `verdict_phys` se declara no ejecutado.
  [ ] OPCIONAL, autoría: caracterización hardware + pista como apéndice propio
       (fotografía, medidas de pista, tabla de calibraciones M-1..M-7).
  [ ] OPCIONAL, autoría: verificar los valores sim de la tabla §9.4 contra
       experiments/sim/runs/rl_newcam_eval_2024_cb297k_4k4/ al pulir.
  [ ] OPCIONAL, autoría: decidir dónde vive el detalle Isaac que hoy está en
       docs/13 (¿anexo?).
  [ ] OPCIONAL, autoría: figura candidata, la escalera de fidelidad
       (reutilizar/adaptar Fig. 8.2, sim2real_roadmap.mmd).
  — RETIRADO: «cuando se puntúe un escenario físico, re-enunciar §10.5 sobre
       §9.4». No se puntuará ningún escenario físico en este trabajo.
-->
