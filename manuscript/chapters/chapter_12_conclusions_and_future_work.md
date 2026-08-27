# Capítulo 12 — Conclusiones y Trabajo Futuro

Convención: las secciones marcadas [BORRADOR POST-G4] se redactaron tras el cierre
de Gate 4 (02.07.2026) y se actualizaron con la evidencia posterior disponible a
20.07.2026. Los capítulos 9 (sim-to-real / físico), 10 (validación operacional) y
11 (discusión) ya existen como borradores tempranos, pero sus resultados Isaac y
físicos siguen incompletos; las conclusiones que dependen de ellos se marcan
explícitamente como **provisionales** y este capítulo se re-cierra en Fase 6. Los
solapes deliberados con los capítulos 10 y 11 (veredictos, limitaciones) se
redistribuyen en esa consolidación — ver el apéndice interno al final.

---

## 12.1 Propósito y alcance del capítulo  [BORRADOR POST-G4]

Este capítulo cierra la tesis en tres movimientos. Primero sintetiza los
**hallazgos** acumulados hasta el cierre de la evaluación en simulación (Gate 4,
02.07.2026) y el trabajo posterior inmediato (robustez multi-semilla E5, estudio
de algoritmo y acción 2-D), formulados como afirmaciones concretas ancladas en
evidencia identificable (§12.2). Segundo, responde de forma provisional a las
preguntas de investigación e hipótesis del Capítulo 1 con esa evidencia (§12.3),
declarando qué partes de la respuesta quedan pendientes de la Fase 5. Tercero,
deriva el **trabajo futuro** exclusivamente de los hallazgos concretos —cada
línea propuesta traza a un hallazgo, una decisión (D-NN) o un hueco documentado,
no a una lista genérica de extensiones deseables (§12.5).

El estado de la evidencia al escribir este borrador es: **todos los veredictos de
la tesis están cerrados en Gazebo** sobre dos brazos del mismo tronco —el
*baseline* F-track de vector de estado (campaña F4: 1260 runs, veredicto global
`SATISFIED`) y el track 'E' end-to-end con cámara (campaña GE4-V2: 1970 runs
sobre el E-main de 297k, veredicto global `NOT SATISFIED` *literal*, reconciliado
en criterio propio, D-47)—, con la cadena de trazabilidad completa (12 hazards →
14 Safety Requirements → 6 reglas de cage → 28 escenarios → 19 métricas →
evidencia loggeada → veredicto) verificada sin huérfanos por `check_traceability.py`
en cada gate. Ambos veredictos son de **acción 1-D** (dirección; velocidad fija):
el brazo posterior de **acción 2-D** —dirección + acelerador, cap 0,22 m/s— ya
cerró la verificación de SR-009 (cap. 8 §8.9.7) y **dos campañas completas**: la
de margin022 (§8.9.8) y la de la policy competente de 550k (§8.9.9, 1890 runs,
cerrada el 31.07.2026), cuyo resultado concuerda con los veredictos congelados
—invariante in-ODD intacta, literal reconciliable por la misma cláusula
heredada— sin entrar en la cadena de gate. El despliegue físico y la
caracterización del gap sim-to-real (Capítulo 9) no han comenzado; el puente de
fidelidad Isaac Sim (D-44) está en curso como trabajo posterior que no reabre G4.

---

## 12.2 Síntesis de hallazgos  [BORRADOR POST-G4]

### 12.2.1 Hallazgos metodológicos

**Hallazgo 1 — La cadena de trazabilidad completa es operacionalizable de
extremo a extremo por un equipo de una persona.** La cadena Hazard → SR → Regla
→ Escenario → Métrica → Evidencia → Veredicto no quedó en propuesta: se
materializó en artefactos versionados (docs/02–07), un validador automático
ejecutado como restricción dura en cada gate (cero huérfanos en G1–G4), y
veredictos por SR respaldados por runs reproducibles con metadatos completos
(commit, hashes de cage/checkpoint/escenario, semilla). Las cinco adaptaciones
del V-Model (A1–A5, Capítulo 3) produjeron cada una los artefactos que
prometían. El coste de adopción quedó registrado en **55 decisiones** hasta
D-61 (con los huecos históricos D-20..D-24 y D-40) — evidencia directa para la
hipótesis H2.

**Hallazgo 2 — El veredicto literal y el criterio propio divergen, y la
disciplina de reportar ambos es en sí misma un resultado.** El global
`NOT SATISFIED` del brazo de cámara descansa **enteramente** en una cláusula de
recuperación (`time_to_recovery_heading < 2.0 s`, SC-EDGE-01) heredada
literalmente del set del óvalo, que no es el criterio de satisfacción documentado
de ningún SR: sobre sus criterios propios, SR-002 (máx. M-P4 = 14.4° ≤ 25°) y
SR-003 (TTLC nunca violado) están satisfechos, y ningún predicado de seguridad
SR-CL-A se incumple en ninguno de los dos brazos. La decisión de registrar el
veredicto literal *más* la reconciliación anotada (D-39, D-45, D-47) en lugar de
re-escribir el criterio a posteriori es el patrón metodológico que esta tesis
defiende: la **higiene de criterios** —mantener separados los predicados de
seguridad del SR y las sobrecapas de performance del escenario, y versionar las
cláusulas cuando la biblioteca migra de geometría— resultó ser tan determinante
para el veredicto como el comportamiento del sistema.

**Hallazgo 3 — La semántica de agregación importa: indeterminado no es fallo, y
la abstención documentada es un veredicto legítimo.** Dos defectos históricos de
instrumentación (el evaluador multi-brazo sin agrupar en SC-PERT-03; la
inyección de condiciones iniciales del grid sin cablear en SC-EDGE-05) habrían
colapsado a `FAIL` bajo una agregación ingenua. La reconciliación D-38 (los
veredictos `None` se excluyen del denominador y se propagan como
`insufficient_evidence`) y el registro de SR-009/SR-010 como **abstenciones
documentadas no-vetantes** (D-30) preservaron la distinción entre "el sistema
falla" y "el experimento no puede pronunciarse" — distinción que el cierre de G4
convirtió en resoluciones materiales (§12.2.3, Hallazgo 8). El runner posterior
ya separa y conjuga los dos brazos de SC-PERT-03; esto habilita evidencia nueva,
pero no reinterpreta los runs históricos ni modifica aquel cierre.

**Hallazgo 4 — La curva de entrenamiento no clasifica el comportamiento de
seguridad de la policy; el eval sí.** Las cinco semillas del E-main comparten la
misma firma de curva (subida → pico → colapso de exploración, señal de cage
C-06-only durante el entrenamiento), y sin embargo el eval nominal las separa en
**tres cuencas**: *constraint-respecting* (3/5), *cage-dependent* (la 666, que
desnuda deriva fuera del carril con |ey| medio 178.8 mm) y un caso nuevo,
**conflicto cage–CV** (la 23, donde el enforcement *degrada* a una policy
competente porque C-02/C-03 corrigen contra una lectura CV confiada pero
errónea). La implicación metodológica extiende D-36: la selección de checkpoint
por pico de reward es necesaria pero no suficiente; la clasificación de cuenca
exige la evaluación conductual por semilla en ambos modos.

### 12.2.2 Hallazgos sobre la arquitectura policy + cage

**Hallazgo 5 — La cage es latente cuando la policy respeta las restricciones y
se vuelve el mecanismo de seguridad activo cuando la percepción se degrada o el
sistema sale del ODD; el flip latente→activa se midió, no se postuló.** Es el
hallazgo empírico central de la tesis, medido en tres planos:

- *In-ODD con policy sana:* M-S2 = 0 en **ambos** modos en toda la campaña F4 —
  la policy principal nunca se acerca a la frontera y el delta
  enforcement-vs-monitoring es nulo. La cage no compra nada… todavía.
- *Fuera del ODD / policy degradada:* en el contraste frontier sobre la policy
  *cage-dependent* (seed 123), la cage elimina el **96–100 %** de los contactos
  con el borde de calzada que la policy desnuda comete.
- *Bajo degradación de percepción (brazo de cámara):* la cage **remueve** fallos
  que la policy desnuda comete — SC-PERT-13 (marcas degradadas + glare) pasa
  **40/40 en enforcement contra 0/40 en monitoring**; el patrón se repite en
  SC-PERT-04/09/11/12. El mecanismo operativo cambia además de naturaleza: de
  corrección de acción (F-track) a **parada controlada por salud del estimador**
  (SR-013 / Trigger 8).
- *Con autoridad longitudinal (acción 2-D):* el mismo flip se replica sobre otro
  espacio de acción y sobre dos policies de calidad muy distinta. La policy
  desnuda comete **98** contactos de borde in-ODD en la campaña margin022 y
  **60** en la de la 550k; en enforcement, **ambas cifras caen a cero**
  (§8.9.8–§8.9.9). Que el número de contactos evitados baje al mejorar el
  conductor —y que la cuenta con la cage siga siendo 0 en los dos casos— es
  justamente la forma que debe tener una garantía: su valor escala con la
  necesidad, su resultado no.

La formulación que condensa el resultado: la cage es una **garantía cuyo valor
es nulo cuando no hace falta y decisivo cuando hace falta**, y la comparación
enforcement-vs-monitoring es el instrumento que permite afirmarlo causalmente.
Con una matización que el Hallazgo 14 mide y que conviene no perder: "latente"
se predica de las reglas de **seguridad** (C-01/02/03/05), no de la cage entera
—C-06 puede estar trabajando aguas arriba y ser lo que hace posible esa
latencia—.

**Hallazgo 6 — El coste de la percepción por cámara es medible, localizado y
tiene un modo de fallo residual caracterizado (H-12).** El estimador CV
determinista de la cage (D-43) puede producir un **under-read confiado**: con el
vehículo desplazado, lee `cv_ey ≈ 0.04 m` mientras el ey verdadero tiende a
0.30 m, con auto-consistencia interna (`cv_ok = True`) que SR-014 no puede
atrapar por construcción. Acotado al ODD costó exactamente 2 breaches marginales
(0.118/0.121 m, borde de la cuenca de recuperación ~0.120 m) en SC-EDGE-02; el
multi-seed lo elevó de residuo estadístico a **mecanismo activo observado y
replicado** (3 de las 4 paradas 1-D observadas aterrizan en s≈13.4, ey≈0.12 m —
la sección discriminadora de complex_b). El intento de arreglo por selección
conservadora de carril (ruta-2b) **regresionó en lazo cerrado y fue revertido**
(D-48): no hay corrección single-frame robusta — el arreglo pertenece al dominio
temporal/multi-frame (§12.5).

**Hallazgo 7 — El RL end-to-end con cámara supera a la línea base CV clásica en
la geometría compleja, invirtiendo el resultado del óvalo.** Sobre complex_b, la
policy de cámara logra |ey| medio de 10.9 mm contra 17.2 mm del controlador
CV + pure-pursuit sobre la misma pista y el mismo harness; en el óvalo la
relación era la inversa. La ventaja del aprendizaje aparece donde la geometría
castiga al controlador geométrico — el resultado es específico de geometría y
así debe citarse.

**Hallazgo 8 — La composición de reglas es un problema real, no teórico
(SR-010), y el espacio de acción acota qué requisitos son verificables
(SR-009).** El grid de co-activación de SC-EDGE-05, una vez cableado (V2),
produjo **30/85 breaches de M-S1 en puntos in-ODD** bajo co-activación de reglas
— un hallazgo CL-B genuino sobre el arbitraje, no un artefacto. Y el brazo de
stall de SR-009 resultó **N/A-por-construcción** para el espacio de acción
solo-dirección que ambos tracks comparten (M-P6 ≡ 0; la inyección de reward es
inerte sobre throttle fijo, D-49): un requisito de liveness longitudinal no es
verificable en una plataforma sin autoridad longitudinal. Ambos son resultados
sobre los *límites del método*, tan citables como los veredictos — y el segundo
tiene su confirmación por la vía positiva: al dotar de acelerador a la policy
(acción 2-D), el mismo requisito **pasa a ser verificable y se verifica**
(cap. 8 §8.9.7, D-63/D-64). El límite estaba en el espacio de acción, no en el
método.

**Hallazgo 9 — El conservadurismo fail-safe cuesta disponibilidad, y ese coste
delimita el borde del ODD.** Bajo ruido de observación severo (SC-PERT-01,
σ = 0.05 m) la cage dispara paros de emergencia espurios (7/20 runs) con el
vehículo realmente seguro (|d| verdadero ≤ 0.034 m); bajo cámara, la semilla 23
muestra el caso extremo (C-05 sobre un coche centrado por un falso positivo CV
estable en una sección concreta). La seguridad se preserva en todos los casos;
lo que se paga es disponibilidad. La frontera seguridad/disponibilidad quedó
medida, y motiva la línea de robustez del disparador C-05 (§12.5).

### 12.2.3 Hallazgos del trabajo posterior inmediato (post-G4)

**Hallazgo 10 — Los umbrales `[provisional]` de la cage están acoplados al
régimen operativo, pero el fallo 2-D inicial no era un único mecanismo.** El
PPO 2-D de autoridad completa (`max_speed_mps = 0.5`) mostró competencia real
en monitoring (4.66 vueltas, 21.0 mm y desaceleración aprendida en curva), pero
ninguno de sus cuatro runs de enforcement completó el horizonte: la policy
cruzaba una envolvente calibrada para el régimen 1-D de 0.2 m/s. La revisión a
0.25 m/s hizo visible que aún había dos causas distintas. Primero, un **margen
cero**: el cap de la policy coincidía con el techo C-04 de curva (0.25 m/s), de
modo que un overshoot de odometría de 0.0002 m/s bastaba para C-04→C-05; el
probe de evaluación a 0.22 m/s eliminó ese paro y completó los 4 400 pasos.
Segundo, un residuo independiente del cap: el over-read confiado de heading del
estimador CV D-43; el checkpoint auto-175k paró tanto a 0.25 como a 0.22 m/s.
La contraprueba la aportó SAC-entfix: dos checkpoints 2-D sí completaron
enforcement nominal — seed 2024, 75k: **4.32 vueltas, 17.1 mm, 0 emergencias,
17.1 % C-06**; seed 42, 50k: **4.97 vueltas, 18.2 mm, 0 emergencias, 46.4 %
C-06**. Por tanto, D-59 no implica que todo control 2-D sea inviable: exige
margen o recalibración antes de una campaña, y deja D-43 como riesgo residual.
Todo ello es evidencia posterior SC-NOM-01, no una campaña ni un veredicto GE4.

**Hallazgo 11 — El estudio SAC largo separó dos mecanismos de degradación que
la curva agregada confundía.** El conmutador `algorithm: ppo|sac` (D-60)
compuso con las acciones 1-D y 2-D sin bifurcar el entorno ni el pipeline de
evidencia. Los runs largos previstos como 1M se detuvieron una vez
caracterizados sus regímenes, no porque completaran el millón: con
`ent_coef: auto`, SAC 1-D alcanzó 720 @ 89k y SAC 2-D tuned 527 @ 154k, pero la
temperatura cayó hacia cero y produjo un cliff o ciclos collapse–recover. Fijar
`ent_coef = 0.005` conservó los picos (1-D 722.5 @ 83k; 2-D **558.7 @ 78k**) y
eliminó el colapso abrupto, además de producir los dos evals 2-D full-horizon
del Hallazgo 10. Quedaba una deriva lenta post-pico. El probe 1-D de una sola
variable, `buffer_size` 100k→200k, mantuvo la banda 690–745 hasta 180k allí
donde el twin de 100k había caído ~35 %: la deriva coincide con el llenado del
buffer y es consistente con la **evicción de datos tempranos**. La evidencia acotada apoya esta
cadena: cliff = temperatura automática→0; deriva lenta observada = replay
eviction. Es evidencia posterior de algoritmo, no un cambio del E-main PPO ni
un veredicto SAC/GE4; y
refuerza que el checkpoint se selecciona por eval conductual, no por la curva.

**Hallazgo 12 (Isaac, diagnóstico) — El gap entre simuladores es en sí mismo un
resultado de sim-to-real en miniatura.** El intento de retrain 2-D en Isaac
destapó una cadena de discrepancias medibles y calibrables (techo de autoridad
de yaw del backend PhysX, D-54; sesgo de heading del estimador CV bajo el
renderer RTX, D-55/D-57; óptimo degenerado de "aparcar" en la acción 2-D que
exigió `stall_penalty`, D-56) que hubo que raíz-causar con sondas de paridad CV
antes de que ningún entrenamiento progresara. Un checkpoint de Gazebo no
transfiere a Isaac; tampoco, se comprobó, transfieren silenciosamente las
calibraciones. Esto anticipa la forma que tendrá el gap Gazebo→físico y valida
la adaptación A5 (caracterizar el gap, no asumirlo).

**Hallazgo 13 — El checkpoint del pico de recompensa puede ser el peor de los
candidatos; la selección tiene que ser conductual.** Es la forma más nítida del
Hallazgo 4, y aparece justo donde importa, al elegir el artefacto que se lleva a
campaña. Sobre el PPO 2-D de cámara con cap 0,22 (D-66) se evaluaron tres
checkpoints con el mismo protocolo nominal determinista: el del **pico de
recompensa (475k)** acumuló **14 intervenciones de seguridad** y `max |ey|`
49 mm, mientras el de **550k** condujo mejor con **0 emergencias, 0
intervenciones de seguridad**, `|ey|` medio 8,6 mm y el menor uso de C-06.
Seleccionar por la curva habría entregado a la campaña el peor de los tres. El
criterio que sí discrimina combina conducción (vueltas, `|ey|`) con **porcentaje
y tipo de intervención de la cage**: durante todo ese entrenamiento la cage está
**latente en seguridad** (C-01/02/03/05 = 0), de modo que la señal útil no es
"cuánta recompensa" sino "qué reglas dispara y cuándo". La acción 2-D añade su
propio matiz de honestidad: su recompensa total, ~2× la del 1-D, procede sobre
todo del techo de episodio (2048 vs 1024 pasos) y de la mayor supervivencia, no
de conducir "2× mejor" —una razón más para no comparar curvas entre
configuraciones (cap. 7 §7.5.5).

**Hallazgo 14 — La cage no sólo filtra a la policy: la *moldea*. Y lo que la
mantiene en el carril puede ser la regla que la taxonomía llama "de confort".**
Es la matización del Hallazgo 5, y salió de una inversión que las tablas de
veredicto no muestran: en el run de resistencia de 300 s (SC-NOM-03), la policy
2-D **competente** es la única que **no** aguanta sin cage —17/25 terminan en
`off_road`— mientras la débil (margin022) lo completa 25/25 y el E-main 1-D
24/25. Cuatro medidas acotan la causa. **(i)** El fallo es *geométrico*, no
acumulativo: los 17 abandonos caen en dos arcos, s ≈ 9,4 m y s ≈ 17,2 m —los dos
ápices más cerrados del circuito— y en los últimos 5 s el jerk **baja** (0,172
frente a 0,411): sobre-viraje sostenido, no oscilación. **(ii)** Entre
enforcement y monitoring sólo cambia C-06: mismo comando crudo (|steer| máx
1,00), steering aplicado 0,84 frente a 1,00, Δ por ciclo 0,15 frente a 2,0, y
|ey| máximo **36 mm frente a 145 mm**. **(iii)** En los 25 runs de enforcement
sólo dispara C-06 (58 124 intervenciones; cero C-01/02/03/05): en esos ápices, el
carril lo sostiene el **rate limiter**, formalmente una regla **CL-B de
suavidad** (SR-006). **(iv)** El comando crudo de esta policy es ~2× más brusco
que el de sus predecesoras (0,33–0,41 frente a 0,16–0,19) y satura C-06 en el
77,5 % de los pasos, frente al 43 % del E-main; la velocidad no lo explica (+7,5 %
sobre el E-main, que sí sobrevive).

La lectura: entrenada con el limitador **dentro del lazo de actuación**, la
política aprendió que emitir un comando casi *bang-bang* no se penaliza —C-06 lo
integra—. Con cage, la pareja policy+C-06 conduce mejor que cualquier otro
artefacto de esta tesis (8,6 mm de |ey| medio, 90,7 vueltas de resistencia sin
pasar de 55 mm); sin cage, ese mismo flujo de comandos se sale del carril **una
vez cada ~3,2 vueltas**. Tres consecuencias, en orden de importancia: primero,
**"la cage está latente in-ODD" describe las reglas de seguridad, no la cage
entera** — esa latencia la *produce* C-06 aguas arriba, y presentarla como
"la cage no hace nada" sería falso; segundo, es un **riesgo de transferencia**
identificado para la Fase 5, porque el actuador físico no implementa ese
`delta_max_steering_per_cycle`; tercero, es un aviso metodológico: SC-NOM-01
(300 pasos) pasa **50/50 en monitoring** y no detecta nada — el fallo necesita el
horizonte de 3000 pasos, así que **un eval nominal corto no clasifica esta
propiedad**, exactamente como el Hallazgo 4 dice de la curva de entrenamiento.
La dependencia está **medida**; su origen queda **inferido**: probar la
co-adaptación causalmente exige una ablación (reentrenar con C-06 fuera del lazo)
que no se ha ejecutado, y que §12.5 recoge junto a la línea de transferencia
física.

> **Post-scriptum de Fase 5 (26.08.2026), PRELIMINAR — una corrida: la pareja
> transfiere, y con la tasa prevista.** El riesgo T2 —que el actuador físico no implementa
> `delta_max_steering_per_cycle` y que por tanto la pareja *(policy, C-06)*
> podía no sobrevivir al hardware— se declaró antes de conducir y **se resolvió
> midiendo**. Eligiendo el checkpoint por independencia de la cage en lugar de
> por recompensa (D-72: 3,0 % de intervención nominal frente al 35,0 % del pico
> de recompensa), C-06 interviene sobre el vehículo real en el **3,4 % de los
> ciclos en movimiento contra el 3,0 % de simulación**. Con **N=1 y sin escenario
> puntuado** esto no cierra T2 —la campaña física puede desmentirlo—, pero la
> distancia no es marginal y la dirección es la contraria a la temida. Y el
> **origen sigue inferido**, así que la ablación de §12.5 tampoco queda cerrada.

---

## 12.3 Respuesta a las preguntas de investigación  [BORRADOR POST-G4 — PROVISIONAL]

**Pregunta principal** (¿es adaptable el V-Model canónico mediante un conjunto
finito y trazable de modificaciones que acomode componentes RL sin abandonar la
correspondencia especificación↔V&V?): la evidencia acumulada soporta un **sí
acotado a simulación**. Las cinco adaptaciones se operacionalizaron (Hallazgo 1),
la correspondencia bidireccional se mantuvo verificable mecánicamente en todo el
ciclo, y el marco produjo veredictos por SR con sus límites de validez
declarados — incluyendo veredictos incómodos (el `NOT SATISFIED` literal) que el
propio marco obligó a registrar en lugar de maquillar (Hallazgo 2). La cláusula
"sin abandonar los principios del estándar" se sostiene en que cada relajación
(abstenciones D-30, reconciliaciones D-47) quedó documentada dentro del sistema
de decisión, no fuera de él.

**Pregunta subordinada** (¿produce el marco evidencia coherente y trazable sobre
el caso concreto, incluida una caracterización honesta del gap sim-to-real?):
respondida a medias. La mitad de evidencia trazable está cerrada con dos brazos
y ~3200 runs de campaña verdict-bearing; la caracterización del gap sim-to-real
es exactamente la mitad pendiente (Fase 5 / Capítulo 9), con el puente Isaac
como primer peldaño ya en curso y aportando la anticipación del Hallazgo 12.

Sobre las hipótesis: **H1** (conjunto pequeño y enumerable de adaptaciones)
queda soportada por construcción — cinco adaptaciones bastaron sin romper la
estructura del estándar. **H2** (esfuerzo proporcional) queda soportada por el
registro: 55 decisiones registradas hasta D-61, documentos vivos mantenidos al día de los
resultados, y gates superados con validación automática, todo dentro del
presupuesto de una tesis de máster de una persona. **H3** (veredicto fundamentado
con límites de validez) queda soportada en su mitad de simulación por los dos
veredictos globales y sus reconciliaciones anotadas; su evaluación completa
(Capítulo 11) espera a la evidencia física. Ninguna de las tres se declara
*confirmada* aquí: eso corresponde al cierre de Fase 6.

---

## 12.4 Limitaciones que enmarcan estas conclusiones  [BORRADOR POST-G4]

El desarrollo completo corresponde al Capítulo 11; aquí se enumeran las que
acotan directamente lo afirmado arriba. (i) **N = 1 en plataforma y familia de
geometrías**: un vehículo 1:14, circuitos planos interiores; la generalización
es argumental, no empírica. (ii) **Veredictos solo-simulación**: todos los
veredictos cierran en Gazebo. La Fase 5 ha conducido sobre hardware pero **no ha
puntuado ningún escenario**, de modo que la limitación se mantiene y ahora puede
enunciarse con precisión: *la evidencia física existe y no está puntuada*. Lo que
la Fase 5 sí ha decidido es que **el objeto validado no es el objeto que
conduce** —el trunk 550k no transfiere (D-71)— y que la diferencia cinemática
real está medida y compensada, no supuesta (D-70: guiñada 0,4954× de lo
comandado). (iii) **Percepción proxy en el brazo F**: el baseline de estado modela el
error de percepción como ruido paramétrico; solo el brazo de cámara ejercita
percepción real. (iv) **Una campaña verdict-bearing por brazo, semilla principal
2024**: el multi-seed N=5 caracteriza robustez sobre el eval nominal, no repite
las campañas completas. (v) **Umbrales `[provisional]` heredados**: parte de la
parametrización de la cage sigue pendiente de calibración física (y el Hallazgo
10 muestra el coste de moverla de régimen sin recalibrar). (vi) **El análisis
forense de intervenciones del plan de Fase 4** (correlación intervención–hazard
M-I4, duración M-I3, magnitud de corrección) quedó parcialmente ejecutado: la
latencia de la cage in-ODD en el brazo F dejó el dataset de intervenciones casi
vacío donde el plan lo esperaba rico, y el análisis se desplazó al desglose por
modos de fallo del brazo E; M-I4 se computa por run pero no se reporta como
análisis agregado.

---

## 12.5 Trabajo futuro  [BORRADOR POST-G4]

Cada línea traza a un hallazgo o decisión concreta.

**T1 — Cerrar el brazo de acción 2-D y trasladarlo a Isaac** *(Hallazgos 8, 10,
12, 13; D-44/D-49/D-50/D-59/D-66).* La parte que era trabajo futuro al cierre de
G4 **ya se ejecutó**: la cadena de cualificación completa —calibración
D-43→C-02 del readout de rumbo (21.07), gate temporal T3 (D-62), parent 2-D
fresco, preflight D-43 ligado a hashes— habilitó la **verificación bien-puesta
de SR-009** (80 celdas de dos brazos + validación del detector con una parada
*scripted*, cap. 8 §8.9.7, D-63/D-64) y **dos campañas 2-D completas**:
margin022 sobre una policy débil (§8.9.8, D-65) y la campaña sobre la policy PPO
competente de 550k (§8.9.9, D-66, cerrada el 31.07.2026). El contraste entre
ambas ya respondió su pregunta: los fallos de disponibilidad eran de **calidad
de policy** (SC-NOM-03 y SC-PERT-05 se limpian; los doce SC-PERT aprueban en
enforcement) y los que **persisten** son estructurales —la cláusula heredada de
SC-EDGE-01 y la co-activación SR-010—, con la invariante de seguridad in-ODD
intacta en los dos casos.

De ese "lo que queda", el punto **(i)** ya se ejecutó el 31.07.2026 (D-69): la
reconciliación de criterio propio al estilo D-47 está documentada para la campaña de
550k —el clausulado de SC-EDGE-01 es lo único que falla, con 0 emergencias, M-S1 máx.
0.043 m y M-P4 máx. 14.2°— y, con el veredicto ya existente, los documentos de
especificación **re-apuntaron su *veredicto de récord*** a esta campaña como edición
deliberada, dejando GE4-V2 como registro congelado del gate. En la misma decisión se
cerraron las dos últimas abstenciones CL-B (SR-009 Satisfecha fuera de banda,
SR-010 `No satisfecha`), de modo que la columna de simulación de `docs/07` ya no tiene
ningún TBD. Queda, por tanto: **(ii)** atacar el
residuo estructural que ninguna mejora de policy resolvió, es decir el arbitraje
de reglas de SR-010 (T4) y el over-read/under-read del estimador CV (T3); y
**(iii)** trasladar el brazo a Isaac como réplica de backend, recordando que sus
checkpoints no son compatibles con Gazebo y que nada de esto reabre G4.

**T2 — La campaña física: puntuar escenarios sobre hardware (Fase 5 /
Capítulo 9)** *(pregunta subordinada; adaptación A5).* **Bring-up ejecutado;
campaña pendiente — es el trabajo futuro más inmediato del proyecto.** El despliegue físico
está hecho, el vehículo conduce (cap. 9 §9.3.3) y la tabla de gap tiene columna
física; lo que falta es la mitad que produce veredicto: correr SC-NOM-01/02 y
SC-EDGE-01 bajo protocolo, en enforcement, y emitir la corrección funcional de la
cage en hardware. **Tres condiciones lo separan de ser ejecutable, las tres
identificadas:** (a) una vía de rearme para C-05, de modo que una corrida
puntuada no termine en el primer pulso de percepción —resuelta **fuera** de la
cage (D-74), precisamente para no modificar el artefacto bajo verificación con un
cambio cuyo efecto entero está en hardware y que la simulación no podría validar,
porque allí el enclavamiento es casi inerte—; (b) el registro de procedencia por
corrida, ya implementado; (c) la decisión de `heading_fit_mode` (§9.3.5), porque
el ajuste con el que el coche **puede** conducir no es el contrato D-43 bajo el
que se puntuaron las campañas.

*El riesgo que este ítem declaraba de antemano tiene ya una primera medida, y
es favorable.* La policy 2-D
está acoplada al `delta_max_steering_per_cycle` de C-06 y el actuador físico no
implementa ese límite; seleccionando el checkpoint por independencia de la cage
(D-72), C-06 interviene en el **3,4 % de los ciclos sobre hardware contra el
3,0 % en simulación**. También apunta en la dirección del pronóstico sobre qué componente
transferiría mejor: **ninguna regla de seguridad se activó durante el
recorrido**. Ambas observaciones son de **una sola corrida en `monitoring`**, y es
la campaña la que las convierte en resultado. Lo que no se anticipó, y es el aporte propio del peldaño, es que la
policy validada **no transferiría en absoluto** por haber memorizado la
lateralidad 6,5:1 del circuito de entrenamiento como sesgo de mando (D-71), ni
que la primera medida de cámara sobre hardware **refutaría una suposición que la
simulación había heredado** y que estaba en el camino de C-01 (M-6/M-7, §9.3.2).

**T3 — Robustez temporal del estimador CV frente a H-12** *(Hallazgo 6; D-43,
D-48).* La lección de ruta-2b es que no hay corrección single-frame robusta para
el under-read confiado. Las direcciones con fundamento: consistencia multi-frame
(el falso positivo de la semilla 23 es *estable* en la misma sección — un
tracker temporal lo detectaría como inconsistencia con la odometría), calibración
de confianza del estimador contra el oráculo de sim, y redundancia barata de
sensor para el estado de la cage. El criterio de éxito es concreto: eliminar los
2 breaches residuales de SC-EDGE-02 y las paradas espurias de s≈13.4/s≈8.8 sin
regresión en lazo cerrado (el test que ruta-2b falló).

**T4 — Diseño y verificación del arbitraje de reglas (SR-010)** *(Hallazgo 8).*
Es la única SR que el trabajo cierra como **`No satisfecha`** (D-69), y se reporta
así en `docs/07` en vez de reconciliarse. Los breaches in-ODD bajo co-activación
—**30/85** en el brazo 1-D y **16/85** en el 2-D— piden pasar de la composición por
orden fijo (C-06→C-04→C-02→C-03→C-01→C-05) a un análisis del envelope conjunto:
caracterizar en qué subregión del espacio de estado la composición secuencial
produce acciones fuera del envelope seguro que cada regla garantiza por
separado, y o bien re-ordenar/parametrizar, o bien documentar la subregión como
exclusión del ODD. Medirlo sobre dos policies acota el problema con precisión
útil: **entrenar mejor lo reduce a la mitad pero no lo cambia de naturaleza**, luego
el residuo es de diseño de la cage y no de la policy —y el desglose por anclaje
señala dónde—: la co-activación **C-01 ∧ C-02** (lateral + rumbo) concentra los
fallos (15/20, 11 breaches), mientras que allí donde no hay conflicto
lateral/rumbo el arbitraje es limpio (C-04 ∧ C-06: 0/20 fallos). El grid de
SC-EDGE-05 ya cableado es el instrumento de medida; el re-run del brazo F (óvalo)
queda como réplica opcional.

**T5 — Disponibilidad: robustez del disparador C-05 a ruido de percepción**
*(Hallazgo 9).* Histéresis/persistencia en el trigger de validez de estado y en
el Trigger 8, dimensionadas para que el paro espurio de SC-PERT-01 σ=0.05 y el
falso positivo estable de la semilla 23 no disparen, sin alargar el tiempo de
reacción ante degradación genuina (SC-PERT-07/13 deben seguir 25/25 y 40/40).
Es un problema de diseño de filtro con criterio de aceptación ya medible en la
biblioteca existente.

**T6 — Consolidación del estudio SAC a escala** *(Hallazgo 11; D-60).* El paso
de pilotos a runs largos **ya se ejecutó** en 1-D y 2-D y aisló la temperatura
automática; el probe 1-D acotado apoya la evicción del replay como segundo
mecanismo observado. Terminar por inercia los presupuestos 1M
interrumpidos no añade un veredicto. El cierre reproducible exige ahora
archivar los configs exactos de cada variante y enlazar explícitamente cada
eval con su `train_config`, checkpoint y hashes. El retrain 2-D predeclarado por
T1 —**entfix (`0.005`) + cap 0.22 + parent 75k + buffer 150k para los 125k
parent/fine-tune**, con selección conductual de checkpoint, preflight D-43 y
SC-PERT-03— **se entrenó y se ejecutó** (margin022: §8.9.7–§8.9.8), y su
comparación con el PPO 2-D de D-66 dejó además una lección de algoritmo: sobre
cámara, el SAC 2-D no supera ~200 de recompensa mientras el PPO 2-D alcanza una
meseta estable de ~1755, de modo que la consolidación SAC pendiente es de
**réplicas de semilla y archivado**, no de capacidad de conducción. El
resultado seguirá siendo posterior y comparativo: no sustituye el E-main PPO
ni entra en la cadena GE4 salvo una decisión futura explícita.

**T7 — Consolidación metodológica del marco** *(Hallazgos 2, 3, 4; limitación
vi).* Tres artefactos generalizables que esta tesis deja especificados pero no
cerrados: (a) **higiene de criterios versionada** — separar formalmente en el
esquema de escenario las cláusulas-predicado-de-SR de las sobrecapas de
performance, con migración explícita al cambiar de geometría (el defecto que
produjo el `NOT SATISFIED` literal). Un primer paso ya está dado y muestra cómo
debe hacerse: la métrica de recuperación de rumbo se auditó, se le encontró un
defecto real —banda fija calibrada en otra pista, que convertía el test en una
medida de rizado y fallaba en runs *sin perturbar*— y se corrigió refiriéndola a
la envolvente del propio run, con la regla **pre-registrada y aplicada una sola
vez**, sin re-puntuar ningún veredicto histórico (D-68). Que la corrección
beneficie al brazo congelado y **no** al que la tesis presenta —que sigue
fallando la cláusula— es la prueba de que el procedimiento, no el resultado,
mandó; (b) **el eval conductual multi-modo como
gate de selección de checkpoint** — institucionalizar que ninguna policy se
declara apta por curva de entrenamiento (D-36 extendido); (c) **el análisis
forense de intervenciones como artefacto estándar** — cerrar el reporte agregado
de M-I4/M-I3/magnitud sobre el dataset del brazo E (donde sí hay intervenciones
ricas), como plantilla para cualquier aplicación futura del marco.

**T8 — Escala y estandarización** *(horizonte largo).* Replicar el marco sobre
una plataforma de mayor escala con ratings ASIL reales, mapear los artefactos
del marco a las actividades de ISO 21448 y a los prompts de UL 4600 de forma
auditable, y publicar el dataset de runs + matriz de trazabilidad como caso de
estudio reutilizable para la comunidad SE4AI.

---

## 12.6 Conclusión  [BORRADOR POST-G4 — PROVISIONAL]

La tesis se propuso demostrar que un componente entrenado por refuerzo puede
habitar un ciclo de desarrollo con safety case sin que el estándar pierda lo que
lo hace valioso: la correspondencia verificable entre lo que se especifica y lo
que se comprueba. Al cierre de la evaluación en simulación, esa correspondencia
existe y es mecánicamente verificable de hazard a veredicto; la contribución de
la cage está medida causalmente y no postulada — nula donde la policy basta,
decisiva donde no; y los resultados incómodos (el veredicto literal negativo, la
dependencia de cuenca por semilla, el modo de fallo residual del estimador, el
coste en disponibilidad del conservadurismo) están dentro del safety case, con
identificador, análisis y decisión — que es exactamente el lugar donde un marco
de ingeniería de seguridad honesto debe ponerlos. Lo que queda —el hardware— no
es un apéndice: es la mitad de la pregunta subordinada, y el marco ya contiene
el sitio exacto (A5, Capítulo 9) donde su respuesta debe encajar.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: BORRADOR POST-G4 (actualizado 31.07.2026), pre-Fase 5. Redactado con la
evidencia de G4 + posterior E5 (multi-seed, brazo de acción 2-D en Gazebo y
estudio SAC largo).

  [ ] Ítems específicos del autor pendientes de incorporar (solicitados tras
       este borrador).
  [ ] Re-cerrar §12.3/§12.6 tras Fase 5 (gap sim-to-real) y tras los caps. 10-11
       (evaluación formal de H1-H3 vive en el 11; aquí solo la síntesis).
  [ ] Redistribuir solapes en Fase 6: los veredictos detallados → cap. 10; el
       desarrollo de limitaciones → cap. 11; aquí queda síntesis + futuro.
  [x] Hallazgo 11 elevado de piloto a estudio posterior: runs SAC largos 1-D/2-D,
      entfix y probe de replay ejecutados; sigue fuera del veredicto GE4.
  [x] T1 reescrito (31.07): SC-PERT-03 2-D y las campañas 2-D ya no son futuro —
      ejecutados (D-63/D-64, D-65); T1 queda acotado al cierre de §8.9.9 y a Isaac.
  [x] Hallazgo 13 añadido (D-66): el checkpoint del pico de recompensa no es el
      mejor; selección conductual + % de cage.
  [x] Hallazgo 14 añadido (31.07): C-06 sostiene el carril en dos ápices; "latente"
      se predica de las reglas de seguridad, no de la cage entera. Matiza el
      Hallazgo 5, alimenta T2 (riesgo de transferencia) y deja pendiente la
      ablación sin-C-06 que probaría la co-adaptación.
  [x] §8.9.9 cerrada (31.07): T1, §12.1 y el Hallazgo 5 citan ya el veredicto 2-D.
  [ ] Decisión pendiente (post-verdicto, D-67): si §12.3/§12.4 y los documentos de
      especificación amplían su alcance del 1-D al brazo 2-D. Hoy declaran 1-D.
  [ ] Números a re-verificar contra los reportes al pulir: 96-100% frontier
       (frontier_contrast.json), 30/85 (failure_mode_breakdown.json), 10.9/17.2 mm
       (docs/12 §8), SAC largo/entfix/cap probes (CHANGELOG 17–20.07).
  [ ] Referencias cruzadas definitivas (§ de caps. 9-11) cuando existan.
-->
