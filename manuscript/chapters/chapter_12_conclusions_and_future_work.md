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
en cada gate. El despliegue físico y la caracterización del gap sim-to-real
(Capítulo 9) no han comenzado; el puente de fidelidad Isaac Sim (D-44) está en
curso como trabajo posterior que no reabre G4.

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

La formulación que condensa el resultado: la cage es una **garantía cuyo valor
es nulo cuando no hace falta y decisivo cuando hace falta**, y la comparación
enforcement-vs-monitoring es el instrumento que permite afirmarlo causalmente.

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
sobre los *límites del método*, tan citables como los veredictos.

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
veredictos cierran en Gazebo; la Fase 5 decide cuánto sobrevive al hardware —
incluida la diferencia cinemática real (skid-steer físico vs DiffDrive fiel en
sim). (iii) **Percepción proxy en el brazo F**: el baseline de estado modela el
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

**T1 — Verificación 2-D bien-puesta de SR-009 y traslado a Isaac** *(Hallazgos
8, 10, 12; D-44/D-49/D-50/D-59).* Gazebo ya demostró la autoridad longitudinal
y dos evals nominales full-horizon, pero aún no ejecutó **SC-PERT-03** sobre una
policy 2-D ni produjo una campaña 2-D. La infraestructura de cualificación ya
está fijada: el contrato **fresh-training-only** `margin022` deja 0.03 m/s bajo
C-04, acota el parent a 75k y retiene parent + fine-tune en un buffer de 150k;
el fingerprint queda embebido en el checkpoint y el preflight D-43 compara CV con el
oráculo y el runner exige un `PASS` ligado a los hashes exactos del checkpoint
y del config antes de arrancar Gazebo. El meta-test también quedó preregistrado:
`lambda_stall = 4.0`, continuación única de 50k, criterio porcentual
`M-P6 > 50.0`, 20 runs por brazo y modo, manifest con hashes y agregación
independiente de *released*/*stall_variant*. Lo pendiente ya no es diseñar el
test: es entrenar desde cero el parent 0.22, ejecutar su SC-NOM-01 nominal,
obtener un preflight D-43 `PASS`, correr el fine-tune único y sólo entonces las
80 celdas de SC-PERT-03. Los informes históricos muestran por qué el gate es
necesario: entfix-2024/42 pasan individualmente, mientras auto-175k queda
bloqueado a 0.25 y en el probe 0.22 por el over-read CV. Isaac sigue siendo una
réplica de transferencia —sus checkpoints no son compatibles con Gazebo— y no
reabre G4.

**T2 — Despliegue físico y caracterización del gap sim-to-real (Fase 5 /
Capítulo 9)** *(pregunta subordinada; adaptación A5).* Portar el subconjunto
físico de la biblioteca (SC-NOM-01/02, SC-EDGE-01) a la plataforma CobraFlex con
el sistema **tal como salió de Fase 4** (sin parcheo entre corridas), producir
la tabla de gap por métrica (sim vs físico, absoluto/relativo) y emitir el
veredicto de corrección funcional de la cage en hardware. El componente con
mejor pronóstico de transferencia es la cage misma, por estar especificada sobre
el estado abstracto e independiente de la calidad de policy y percepción.

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
Los 30/85 breaches in-ODD bajo co-activación piden pasar de la composición por
orden fijo (C-06→C-04→C-02→C-03→C-01→C-05) a un análisis del envelope conjunto:
caracterizar en qué subregión del espacio de estado la composición secuencial
produce acciones fuera del envelope seguro que cada regla garantiza por
separado, y o bien re-ordenar/parametrizar, o bien documentar la subregión como
exclusión del ODD. El grid de SC-EDGE-05 ya cableado es el instrumento de
medida; el re-run del brazo F (óvalo) queda como réplica opcional.

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
eval con su `train_config`, checkpoint y hashes. El único retrain 2-D justificado
por T1 ya tiene hipótesis predeclarada: **entfix (`0.005`) + cap 0.22 + parent
75k + buffer 150k para los 125k parent/fine-tune**, seguida de selección conductual de checkpoint,
preflight D-43, réplicas de semilla y SC-PERT-03; esa combinación aún no se ha
entrenado. El
resultado seguirá siendo posterior y comparativo: no sustituye el E-main PPO
ni entra en la cadena GE4 salvo una decisión futura explícita.

**T7 — Consolidación metodológica del marco** *(Hallazgos 2, 3, 4; limitación
vi).* Tres artefactos generalizables que esta tesis deja especificados pero no
cerrados: (a) **higiene de criterios versionada** — separar formalmente en el
esquema de escenario las cláusulas-predicado-de-SR de las sobrecapas de
performance, con migración explícita al cambiar de geometría (el defecto que
produjo el `NOT SATISFIED` literal); (b) **el eval conductual multi-modo como
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

Estado: BORRADOR POST-G4 (actualizado 20.07.2026), pre-Fase 5. Redactado con la
evidencia de G4 + posterior E5 (multi-seed, Gazebo 2-D y estudio SAC largo).

  [ ] Ítems específicos del autor pendientes de incorporar (solicitados tras
       este borrador).
  [ ] Re-cerrar §12.3/§12.6 tras Fase 5 (gap sim-to-real) y tras los caps. 10-11
       (evaluación formal de H1-H3 vive en el 11; aquí solo la síntesis).
  [ ] Redistribuir solapes en Fase 6: los veredictos detallados → cap. 10; el
       desarrollo de limitaciones → cap. 11; aquí queda síntesis + futuro.
  [x] Hallazgo 11 elevado de piloto a estudio posterior: runs SAC largos 1-D/2-D,
      entfix y probe de replay ejecutados; sigue fuera del veredicto GE4.
  [ ] Números a re-verificar contra los reportes al pulir: 96-100% frontier
       (frontier_contrast.json), 30/85 (failure_mode_breakdown.json), 10.9/17.2 mm
       (docs/12 §8), SAC largo/entfix/cap probes (CHANGELOG 17–20.07).
  [ ] Referencias cruzadas definitivas (§ de caps. 9-11) cuando existan.
-->
