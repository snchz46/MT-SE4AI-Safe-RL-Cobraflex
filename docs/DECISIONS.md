# DECISIONS.md — Registro de decisiones del proyecto

<!--
Estado: D9 (cierre Fase 0).
Última actualización: ver fecha de commit en Git.
-->

## Propósito de este archivo

Este fichero es el **registro central de decisiones** del proyecto. Cada
decisión técnica, metodológica o de alcance que tiene impacto en la
trayectoria del trabajo se documenta aquí con un identificador único
(`D-NN`), independientemente de si la decisión queda confirmada,
diferida a una fase posterior, o eventualmente revisada.

El archivo cumple tres funciones que la metodología del Capítulo 3 hace
explícitas. Primero, sirve como *instrumento auditable* de mitigación
del sesgo del autor (cf. §3.2.3): un tercero que repitiera el ejercicio
sobre los artefactos del proyecto puede inspeccionar aquí qué se
decidió y por qué, sin tener que reconstruirlo de los capítulos.
Segundo, sirve como *instrumento de medida del coste de adopción* del
marco (cf. §3.7, criterio 4): el peso de las decisiones registradas es
uno de los indicadores que el Capítulo 11 retoma para evaluar el marco.
Tercero, sirve como *memoria operativa* durante el desarrollo: cuando
una decisión posterior depende de una anterior, se cita por su ID en
lugar de reabrir la discusión.

El formato de cada entrada es consistente y se inspira en los
*Architecture Decision Records* (ADR) propuestos por Michael Nygard,
adaptado al léxico de la tesis. Cada decisión incluye una pequeña tabla
de metadatos (sección donde se documenta en los capítulos, estado
actual, fecha de toma de decisión, fecha prevista de revisión si
procede) y un cuerpo en prosa con cuatro bloques: *decisión*
(declarativa, una o dos frases), *alternativas consideradas y
descartadas* (con motivos), *justificación* (la respuesta a "¿por qué
esto y no aquello?" si el tribunal pregunta), y *consecuencias* (qué
implica para el resto del proyecto).

Cuando una decisión cita literatura, se referencia con el formato
`Apellido (año)` consistente con los capítulos.

---

## Índice de decisiones

| ID | Título | Capítulo / Sección | Estado |
| --- | --- | --- | --- |
| D-01 | No adoptar arquitectura *end-to-end* para la integración de la *policy* RL | §3.5.1 (motivación adicional en §3.4) | CONFIRMADA |
| D-02 | Estructura de tres hipótesis encadenadas (H1, H2, H3) | §1.3 | CONFIRMADA |
| D-03 | Siete objetivos específicos (OE1–OE7) con mapeo 1:1 a capítulos | §1.4 | CONFIRMADA |
| D-04 | Alcance acotado: SAE Nivel 2, caso único *lane-following*, pista controlada | §1.6 | CONFIRMADA |
| D-05 | Posicionamiento epistemológico: *design science research* | §3.2.1 | CONFIRMADA |
| D-06 | Estrategia de evaluación: caso único + plausibilidad estructural | §3.2.2 | CONFIRMADA |
| D-07 | A1 — Desdoblamiento del nivel L4 en Cage Spec + Training Spec | §3.4.1 | CONFIRMADA |
| D-08 | A2 — Desdoblamiento del nivel L4' en Cage Unit Tests + Policy Behavioral Evaluation | §3.4.2 | CONFIRMADA |
| D-09 | A3 — Nuevo nivel transversal Runtime Monitoring | §3.4.3 | CONFIRMADA |
| D-10 | A4 — Trazabilidad bidireccional como restricción dura aplicada por herramienta | §3.4.4 | CONFIRMADA |
| D-11 | A5 — Validación operacional acotada con caracterización del gap sim-to-real | §3.4.5 | CONFIRMADA |
| D-12 | Simulador adoptado: Gazebo (sustituye CARLA en versión preliminar) | §3.6.1 | CONFIRMADA |
| D-13 | Middleware: ROS2 distribución Humble | §3.6.2 | CONFIRMADA |
| D-14 | Algoritmo de aprendizaje: PPO | §3.6.3 | CONFIRMADA |
| D-15 | Stack tecnológico: Stable-Baselines3 + PyTorch + pytest + Python 3.10+ | §3.6.4 | CONFIRMADA |
| D-16 | Plataforma física: vehículo radio-controlado escala 1:14 | §3.6.5 | CONFIRMADA |
| D-17 | QED diferida a Fase 4: inspiración conceptual con calibración pendiente | §3.6.6 | DIFERIDA |
| D-18 | Documentación en plain-text Markdown (no MBSE industrial) | §3.6.7 | CONFIRMADA |
| D-19 | Cinco criterios de meta-evaluación del marco | §3.7 | CONFIRMADA |

---

## Decisiones

### D-01 — No adoptar arquitectura *end-to-end* para la integración de la *policy* RL

| Campo | Valor |
| --- | --- |
| Sección | §3.5.1 (con motivación adicional en §3.4) |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | No procede (decisión arquitectónica fundacional) |

**Decisión.** El sistema NO adopta una aproximación *end-to-end* en la
que una única red neuronal mapee directamente píxeles de cámara a
comandos de actuación. La arquitectura mantiene una descomposición
modular explícita —percepción, *policy* PPO, cage de reglas, actuación,
logger— donde el componente aprendido por refuerzo ocupa una posición
acotada dentro del grafo ROS2.

**Alternativas consideradas y descartadas.** Aproximación *end-to-end*
tipo PilotNet (Bojarski et al., 2016), donde una CNN procesa
imagen→comando de volante directamente, descartada por las dos razones
que articula Salay et al. (2017): las arquitecturas *end-to-end*
desafían el supuesto de descomposición jerárquica estable que sostiene
buena parte de las técnicas de seguridad funcional clásicas, y suelen
requerir conjuntos de entrenamiento exponencialmente mayores que las
arquitecturas modulares para alcanzar prestaciones equivalentes
(Shalev-Shwartz y Shashua, 2016).

**Justificación.** Esta tesis es un trabajo metodológico cuya
contribución es el marco V-Model adaptado, no un sistema *end-to-end*
novedoso. La arquitectura modular es además condición necesaria para
varias adaptaciones del marco: A1 separa Cage Spec de Training Spec, lo
que solo es posible si cage y *policy* son módulos distintos; A2 separa
Cage Unit Tests de Policy Behavioral Evaluation, lo que requiere que la
cage sea verificable independientemente; A4 (trazabilidad obligatoria)
es trivial sobre componentes modulares y ardua sobre una caja negra
unificada. Adoptar *end-to-end* haría inviables varias adaptaciones del
marco propuesto.

**Consecuencias.** El sistema produce evidencia para safety case más
fácilmente; pero asume el coste adicional de mantener varios componentes
y sus interfaces. La policy PPO opera sobre observaciones procesadas por
un módulo de percepción simplificado, no sobre píxeles directamente.

**Referencias.** Salay, Queiroz y Czarnecki (2017); Bojarski et al.
(2016); Shalev-Shwartz y Shashua (2016).

---

### D-02 — Estructura de tres hipótesis encadenadas (H1, H2, H3)

| Campo | Valor |
| --- | --- |
| Sección | §1.3 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | Tras Gate 0 (cierre Fase 1), si la formulación de SRs lo motiva |

**Decisión.** La tesis adopta una estructura de tres hipótesis
encadenadas: H1 (de constructo: existe un conjunto pequeño y enumerable
de adaptaciones que cubren los modos de fallo de los componentes RL/IA
sin romper la estructura del estándar), H2 (de operatividad: cada
adaptación es operacionalizable como artefactos concretos con coste
proporcional al resto del proyecto), y H3 (de utilidad: el marco
resultante produce evidencia trazable que permite emitir un veredicto
fundamentado sobre el comportamiento del sistema). Las tres se evalúan
al cierre del trabajo en el Capítulo 11.

**Alternativas consideradas y descartadas.** Hipótesis única ("el
V-Model adaptado permite incorporar componentes RL en sistemas de
conducción autónoma sin sacrificar la trazabilidad"), descartada porque
colapsa los tres niveles en un único veredicto binario y pierde
granularidad en la evaluación: H1 puede salir verdadera y H3 falsa, lo
cual sería un resultado interesante pero invisible bajo hipótesis única.

**Justificación.** La estructura encadenada permite veredictos parciales
en el Capítulo 11. Si H1 se confirma pero H2 falla, el aporte sigue
siendo válido a nivel de marco conceptual aunque la operacionalización
requiera revisión. Si H1 y H2 se confirman pero H3 falla, queda
evidencia útil para futuras refinaciones por terceros.

**Consecuencias.** El Capítulo 11 debe emitir tres veredictos separados
y argumentados. Los criterios meta de §3.7 (cf. D-19) deben mapear a
las tres hipótesis con explicitud.

---

### D-03 — Siete objetivos específicos (OE1–OE7) con mapeo 1:1 a capítulos

| Campo | Valor |
| --- | --- |
| Sección | §1.4 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | No procede |

**Decisión.** El objetivo general se descompone en siete objetivos
específicos OE1–OE7, cada uno asignado de forma unívoca a un capítulo
del bloque metodológico/experimental (Capítulos 3–11).

**Alternativas consideradas y descartadas.** Tres a cinco objetivos
específicos con mapeo n:m a capítulos (formato más común en TFM en
algunas escuelas españolas). Descartado porque el mapeo n:m diluye la
verificabilidad: ¿qué capítulo "cumple" cada objetivo? El mapeo 1:1
facilita la defensa porque cada objetivo tiene un capítulo entero como
evidencia explícita de cumplimiento.

**Justificación.** Estructura estándar de tesis de investigación con
contribución metodológica. Al final cada OE tiene un veredicto claro de
cumplimiento basado en el contenido del capítulo correspondiente.

**Consecuencias.** El Capítulo 11 debe revisar OE1–OE7 sistemáticamente
y emitir veredicto por cada uno. Si una escuela específica exige menos
objetivos, la fusión natural sería OE1+OE2 (caracterización + propuesta
del marco) y OE5+OE6 (caracterización del gap + verdicto de validación).

---

### D-04 — Alcance acotado: SAE Nivel 2, caso único *lane-following*, pista controlada

| Campo | Valor |
| --- | --- |
| Sección | §1.6 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | No procede (decisión de alcance fundacional) |

**Decisión.** El proyecto se acota explícitamente a tres ejes: caso
único de aplicación (no estudio multi-caso, no comparación contra grupo
de control con V clásico); tarea de seguimiento de carril en pista
delimitada (no planificación, no interacción con otros agentes); nivel
SAE 2 (asistencia continua bajo supervisión humana, no SAE 4–5).

**Alternativas consideradas y descartadas.** Estudio multi-caso
(descartado por superficialidad incompatible con el rigor que el propio
marco exige). Comparación contra grupo de control con V clásico
(descartada: requeriría doble proyecto, inviable para una tesis
individual). Nivel SAE 4 (descartado: requeriría reformular A1 para
safety cases más exhaustivos y A4 para extender la trazabilidad a
runtime reasoning, no solo a artefactos de diseño).

**Justificación.** Un caso de aplicación que cubra el ciclo completo
desde HARA hasta despliegue físico con caracterización del gap
sim-to-real es ya un compromiso ambicioso para una tesis de máster. Es
preferible un caso profundo que varios casos superficiales. La
generalización se argumenta por plausibilidad estructural (D-06), no
por evidencia empírica multi-caso.

**Consecuencias.** El Capítulo 12 distingue explícitamente qué partes
del marco son razonablemente trasladables a otros dominios (otras
escalas, otras tareas, otros niveles SAE) y cuáles requieren
replanteamiento. El Capítulo 11 evalúa el marco con las limitaciones de
N=1 declaradas explícitamente.

---

### D-05 — Posicionamiento epistemológico: *design science research*

| Campo | Valor |
| --- | --- |
| Sección | §3.2.1 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** La tesis se inscribe en la tradición del *design science
research* (Hevner et al., 2004) o, en formulación próxima, *constructive
research* (March y Smith, 1995). La contribución académica es un
*artefacto* —el marco V-Model adaptado, articulado en cinco adaptaciones
A1–A5 más sus plantillas y validadores— que aborda un problema
previamente identificado en la literatura, evaluado mediante un caso de
aplicación.

**Alternativas consideradas y descartadas.** Tesis empírica clásica
(descubrir un fenómeno, refutar hipótesis estadística), descartada
porque no hay un fenómeno por descubrir, hay un artefacto por
construir. Tesis teórica deductiva, descartada porque el problema no es
demostrable analíticamente —involucra decisiones de ingeniería y
métodos que solo se evalúan por construcción y aplicación—.

**Justificación.** El problema que aborda esta tesis es de ingeniería y
de método: cómo se adapta un ciclo de vida ISO 26262 para acomodar
componentes RL. La respuesta natural es construir un marco y demostrar
su funcionamiento, lo cual define con precisión el design science
research. Esto tiene tres consecuencias prácticas que el Capítulo 3
desarrolla: la tesis no busca la contribución típica de una tesis
empírica; la evaluación se hace sobre el artefacto, lo que exige el
Capítulo 11; la generalización se argumenta por plausibilidad
estructural, no por inducción estadística.

**Consecuencias.** El Capítulo 11 está dedicado a evaluar el marco como
artefacto (cf. D-19). El argumento de generalización del Capítulo 12
sigue la lógica de plausibilidad estructural (D-06).

**Referencias.** Hevner et al. (2004); March y Smith (1995).

---

### D-06 — Estrategia de evaluación: caso único + argumento de plausibilidad estructural

| Campo | Valor |
| --- | --- |
| Sección | §3.2.2 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** El marco se evalúa sobre un único caso de aplicación
(consistente con D-04). La generalización a otros dominios se argumenta
por *plausibilidad estructural*: las adaptaciones A1–A5 atacan supuestos
del V-Model que fallan para cualquier sistema con componente aprendido,
no solo para *lane-following*. La inferencia es por plausibilidad, no
por experimentación controlada multi-caso.

**Alternativas consideradas y descartadas.** Estudio multi-caso
(descartado: superficialidad incompatible con el rigor del marco).
Comparación contra grupo de control donde se aplicara V clásico al mismo
sistema (descartado: requeriría doble proyecto, inviable para una tesis
individual).

**Justificación.** Inherente al *design science research* (D-05). Un
caso profundo y completo es preferible a varios casos superficiales
para validar un marco metodológico. La validez externa se acota
explícitamente y se discute en §3.9 y Capítulo 12.

**Consecuencias.** El Capítulo 11 evalúa el marco con N=1, declarando
explícitamente los límites de la inferencia. El Capítulo 12 distingue
qué partes del marco son razonablemente trasladables y cuáles requieren
replanteamiento. La defensa del trabajo debe articular el argumento de
plausibilidad estructural cuando el tribunal pregunte por la
generalización.

**Referencias.** Hevner et al. (2004); March y Smith (1995).

---

### D-07 — A1: Desdoblamiento del nivel L4 (*Module Design*) en Cage Spec + Training Spec

| Campo | Valor |
| --- | --- |
| Sección | §3.4.1 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** El nivel L4 del V-Model clásico se desdobla en L4a (Cage
Specification, especificación clásica determinista de módulo) y L4b
(Training Specification, *meta-design* del proceso de entrenamiento).
La Cage Spec sigue el formato tradicional de spec de módulo: cada regla
Cᵢ es una función pura, testeable, con entradas y salidas definidas. El
Training Spec especifica el proceso (función de recompensa, espacios de
estado y acción, ODD de entrenamiento, hiperparámetros, criterios de
convergencia, restricciones activas), no el comportamiento aprendido.

**Alternativas consideradas y descartadas.** Mantener L4 sin desdoblar
(descartado: forzar la *policy* a una especificación clásica rompe la
honestidad del proceso, eximirla rompe la trazabilidad). Tres niveles
L4a/L4b/L4c añadiendo una "data spec" separada (descartado: redundante
con Training Spec).

**Justificación.** Coherente con el *three-stage realization principle*
de ISO/IEC TR 5469:2024 (cláusula 7), que distingue las fases de
adquisición desde entradas, inducción de conocimiento desde datos, y
procesamiento y generación de salidas. Coherente también con la
distinción entre elementos Clase I (cage, verificación tradicional
aplicable) y Clase II (policy, técnicas específicas requeridas) del
mismo TR. Permite aplicar técnicas clásicas allí donde son aplicables y
técnicas estadísticas allí donde son necesarias, sin forzar metáforas.

**Consecuencias.** Se producen dos artefactos versionados separados:
`cage_specification.md` (con C-01..C-0n formalmente definidas) y
`training_specification.md` (con función de recompensa, hiperparámetros,
ODD y criterios de convergencia). La trazabilidad H↔SR↔C debe distinguir
entre componentes Clase I y Clase II.

**Referencias.** Kuutti et al. (2019b, 2021); ISO/IEC TR 5469:2024.

---

### D-08 — A2: Desdoblamiento del nivel L4' (*Unit Testing*) en Cage Unit Tests + Policy Behavioral Evaluation

| Campo | Valor |
| --- | --- |
| Sección | §3.4.2 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** El nivel L4' del V-Model clásico se desdobla en L4a'
(Cage Unit Tests, suite determinista pass/fail con pytest sobre cada
regla de cage) y L4b' (Policy Behavioral Evaluation, caracterización
estadística del comportamiento de la *policy* sobre la *scenario
library* con medias, varianzas, percentiles e intervalos de confianza).

**Alternativas consideradas y descartadas.** Mantener L4' sin desdoblar
(descartado: no existe "salida correcta" para tests unitarios sobre la
*policy*; todo test unitario clásico sobre ella sería inválido por
construcción). Sustituir L4' enteramente por evaluación estadística
(descartado: la cage admite tests clásicos y conviene mantenerlos como
verificación de Clase I).

**Justificación.** Espejo simétrico de D-07. Reconoce que la
verificación clásica no es aplicable a componentes aprendidos pero
sigue siendo aplicable a la cage. La asimetría es coherente con la
distinción Clase I/II de ISO/IEC TR 5469:2024. La caracterización
estadística se inspira en QED (Gao et al., 2021) y en *Behavior
Metrics* (Paniego et al., 2024), instrumentos abiertos para evaluación
cuantitativa.

**Consecuencias.** Se producen dos suites de evaluación:
`tests/cage/test_rules.py` (determinista, ejecutable en CI) y el
Capítulo 8 como Policy Behavioral Evaluation estructurada. La adopción
definitiva de QED como métrica oficial queda diferida a Fase 4 (D-17).

**Referencias.** Gao et al. (2021); Paniego et al. (2024); ISO/IEC
TR 5469:2024.

---

### D-09 — A3: Nuevo nivel transversal Runtime Monitoring

| Campo | Valor |
| --- | --- |
| Sección | §3.4.3 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** Se añade al V-Model adaptado un nivel horizontal,
*Runtime Monitoring*, representado como banda transversal debajo del V
(no como sub-nivel colgando del vértice de Implementación). El nivel se
alimenta de los logs de intervención de la cage durante operación y
realimenta los niveles superiores de validación (L1' y, eventualmente,
L2 cuando emergen hazards no anticipados).

**Alternativas consideradas y descartadas.** Brazo derecho extendido
del V al estilo Wang et al. (2024) (descartado: rompe la simetría
visual del V, dificulta la lectura). Bucle de retroalimentación cerrado
externo al V (descartado: gráficamente más denso, requiere leyenda
explícita). No añadir A3 y dejar el monitoring como práctica recomendada
genérica (descartado: convierte el runtime monitoring en una intención,
no en un nivel auditable del ciclo).

**Justificación.** La validación estática es insuficiente para sistemas
que operan en entornos no completamente especificados (filosofía SOTIF,
ISO 21448:2022). El runtime monitoring eleva esta filosofía de práctica
recomendada a nivel arquitectónico explícito del lifecycle. Antecedente
técnico directo en Mohseni et al. (2019), que conceptualiza la
*monitoring function* como categoría arquitectónica propia y revisa
tres familias de técnicas para implementarla (uncertainty estimation,
in-distribution error detectors, OOD detectors). La reformulación del
V-Model con fase de operación continua de Wang et al. (2024) y Ullrich
et al. (2025) refuerza la dirección.

**Consecuencias.** El Logger Node de la arquitectura ROS2 (Capítulo 5)
es el instrumento primario de A3, no un componente auxiliar. El
Capítulo 10 incorpora el concepto de "validación continua como
sustituto parcial de validación estática completa". La versión inicial
del marco se acota a una cage basada en reglas más logging agregado;
incorporar detectores de incertidumbre o de distribución queda como
línea de extensión natural (Capítulo 12).

**Referencias.** Mohseni et al. (2019); Wang et al. (2024); Ullrich et
al. (2025); ISO 21448:2022.

---

### D-10 — A4: Trazabilidad bidireccional como restricción dura aplicada por herramienta

| Campo | Valor |
| --- | --- |
| Sección | §3.4.4 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** La trazabilidad bidireccional H↔SR↔C↔SC↔M es una
restricción dura, no una buena práctica. Toda regla de cage debe
trazarse a SRs; todo SR a hazards o argumento explícito de riesgo
aceptado; todo escenario a SRs; toda métrica a SRs. Un script
automatizado (`check_traceability.py`) se ejecuta en cada commit y
diariamente, fallando si detecta huérfanos en cualquier dirección.

**Alternativas consideradas y descartadas.** Trazabilidad como buena
práctica documental al estilo AMLAS (Paterson et al., 2025), descartada
porque depende de revisiones manuales auditables a posteriori, lo que
en una tesis individual es inviable de garantizar. Trazabilidad parcial
solo de SRs a cage, descartada por dejar la rama derecha del V sin
auditoría automatizada.

**Justificación.** En sistemas con componentes aprendidos, la tentación
de atribuir comportamientos a "propiedades emergentes" del aprendizaje
es alta. Sin trazabilidad estricta automatizada, cualquier
comportamiento puede justificarse retrospectivamente como "algo que la
*policy* aprendió", lo que vacía de contenido el concepto de
responsabilidad ingenieril. La filosofía es próxima a los patrones GSN
(*Goal Structuring Notation*) de AMLAS pero va un paso más allá al
convertir la trazabilidad en propiedad verificable por herramienta
automatizada en lugar de práctica documental revisable.

**Consecuencias.** La Fase 1 (HARA + SR) se simplifica porque obliga al
autor a pensar "¿qué cage rule voy a tener para esto?" desde el primer
SR. El resultado son SRs más operativos y menos abstractos. Se producen
dos artefactos: `traceability_matrix.csv` (matriz viva) y
`check_traceability.py` (validador automatizado), más Anexo F como
versión consolidada al cierre.

**Referencias.** Paterson et al. (2025) AMLAS; Koopman (2023) UL 4600.

---

### D-11 — A5: Validación operacional acotada con caracterización explícita del gap sim-to-real

| Campo | Valor |
| --- | --- |
| Sección | §3.4.5 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** El nivel L1' (Acceptance Testing) del V-Model clásico se
reformula como **Operational Validation** con dos componentes
obligatorios: L1'-a (Scenario-Based System Validation, equivalente al
acceptance testing clásico estructurado por escenarios ligados a SRs,
con métricas de cobertura sobre el ODD en la línea de De Gelder et al.,
2024) y L1'-b (Sim-to-Real Gap Characterization, cuantificación
explícita y empírica del gap entre el entorno de entrenamiento y el
entorno operacional para cada métrica y modo de fallo relevante). La
conclusión de validación NO es "el sistema es seguro" sino "el sistema
satisface los SRs bajo las condiciones del ODD X con un gap medido de Y
respecto a las condiciones de entrenamiento, y con los siguientes
riesgos residuales documentados".

**Alternativas consideradas y descartadas.** Mantener L1' como
acceptance testing binario (descartado: implícitamente asume que las
condiciones de testing son representativas de las operacionales, lo
cual es falso para sistemas entrenados en simulación). Validación
cualitativa sin métricas del gap (descartada: incompatible con el
principio claim-argument-evidence de UL 4600).

**Justificación.** Para un sistema entrenado en simulación, las
condiciones de testing en sim no son representativas de las condiciones
operacionales físicas. El gap es un riesgo de primer orden; un
"acceptance test passed" en simulación no implica operación segura en
el mundo real. La adaptación A5 hace este sesgo visible y mensurable.
Coherente con la filosofía SOTIF y con el principio
claim-argument-evidence de UL 4600.

**Consecuencias.** El Capítulo 9 está dedicado al gap sim-to-real con
métricas M-T1 a M-T4 que lo cuantifican. El Capítulo 10 emite veredicto
acotado con tabla de riesgos residuales documentados (Anexo H). La
elección de Gazebo como simulador (D-12) hace especialmente relevante
esta caracterización.

**Referencias.** De Gelder et al. (2024); ISO 21448:2022; Koopman
(2023).

---

### D-12 — Simulador adoptado: Gazebo (sustituye CARLA en versión preliminar)

| Campo | Valor |
| --- | --- |
| Sección | §3.6.1 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) — revisión interna D9+ |
| Revisión prevista | No procede (validada tras análisis comparativo) |

**Decisión.** El simulador adoptado es Gazebo (Koenig y Howard, 2004)
en su variante moderna con integración ROS2 nativa, operado a través
de una interfaz gymnasium-Gazebo-ROS2 que reutiliza un entorno
previamente construido por el autor en un trabajo de investigación
anterior. Esta decisión sustituye a una elección preliminar de CARLA
registrada en una versión inicial del Capítulo 3 y obliga a actualizar
todas las menciones del simulador en los Capítulos 1, 2 y 3.

**Alternativas consideradas y descartadas.** **CARLA** (Dosovitskiy et
al., 2017): candidato más fuerte y dominante en investigación de
conducción autónoma reciente; ofrece fidelidad sensorial superior y un
ecosistema maduro de benchmarks; descartado por requerir bridge ROS2
con sus complicaciones, no admitir reutilización del trabajo previo del
autor, y mayor coste de cómputo. **Highway-Env** y derivados de Gym
(sin sensores realistas, espacio de observación abstracto, no aptos
para policies basadas en cámara). **LGSVL** (proyecto discontinuado en
2022, ecosistema en descomposición). **AirSim** (foco aeroespacial,
soporte automotriz secundario y desarrollo en pausa).

**Justificación.** Cuatro razones articuladas en §3.6.1: integración
ROS2 nativa sin capas de bridge intermedias, lo que reduce superficie
de falla y mejora la fiabilidad de las métricas de integración M-I;
reutilización del trabajo previo del autor, coherente con el enfoque
*design science* (la contribución no está en el simulador sino en el
marco); disponibilidad de la interfaz gymnasium-Gazebo-ROS2 que separa
limpiamente algoritmo, entorno y sistema, facilitando A1; requisitos de
cómputo más modestos, relevantes para una tesis individual sin acceso a
infraestructura dedicada.

**Compromisos reconocidos.** Fidelidad visual inferior a la del motor
Unreal Engine subyacente a CARLA (consecuencia: el gap sim-to-real
puede ser más pronunciado en características visuales de la cámara; A5
hace este efecto visible y medible). La comunidad específica de
investigación AD usa mayoritariamente CARLA, lo que limita la
disponibilidad inmediata de scenario libraries reutilizables en formato
Gazebo (consecuencia: la *scenario library* del proyecto debe
construirse explícitamente en el Capítulo 6).

**Consecuencias.** Capítulos 1, 2 y 3 actualizados consistentemente.
QED (Gao et al., 2021) pasa a inspiración conceptual con pesos a
recalibrar (D-17), porque su calibración original es sobre CARLA. El
Capítulo 12 incluye como línea de extensión natural la replicación del
experimento sobre CARLA para comparar magnitudes del gap entre
simuladores con distinta fidelidad visual.

**Referencias.** Koenig y Howard (2004); Dosovitskiy et al. (2017) como
alternativa descartada y como referencia del estado del arte en §2.4.

---

### D-13 — Middleware: ROS2 distribución Humble

| Campo | Valor |
| --- | --- |
| Sección | §3.6.2 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** ROS2 distribución Humble (LTS) como middleware de
comunicación entre nodos del proyecto.

**Alternativas consideradas y descartadas.** ROS1 Noetic (EOL en 2025,
sin sucesor de soporte; descartado). Middleware propio basado en ZMQ o
gRPC (descartado: descarta tooling existente, coste de desarrollo
prohibitivo).

**Justificación.** ROS2 es el estándar de facto en investigación
robótica desde la transición ROS1→ROS2 hacia 2020. El modelo
publish/subscribe casa naturalmente con la arquitectura
monitor-actuador de la cage: la *policy* publica acciones candidatas, la
cage las suscribe, las evalúa, y publica las acciones efectivas. El
soporte para *bag recording* permite implementar el Logger Node de A3
sin código adicional. La distribución Humble se adopta por
compatibilidad con la versión de Gazebo del entorno reutilizado (D-12)
y con el SBC embarcado en el coche físico.

**Consecuencias.** Toda la arquitectura del Capítulo 5 es ROS2 desde su
concepción. Las herramientas de inspección (rqt, ros2 topic, ros2 bag)
son utilizables tal cual, sin desarrollo adicional.

---

### D-14 — Algoritmo de aprendizaje: PPO (*Proximal Policy Optimization*)

| Campo | Valor |
| --- | --- |
| Sección | §3.6.3 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** PPO (Schulman et al., 2017) como algoritmo de aprendizaje
por refuerzo, implementado mediante Stable-Baselines3.

**Alternativas consideradas y descartadas.** **SAC** (Haarnoja et al.,
2018): competitivo en eficiencia de muestras y en robustez a
hiperparámetros, pero su carácter *off-policy* hace el Training Spec
menos interpretable —la noción de "qué política produjo qué experiencia"
se difumina en el *replay buffer*— y su naturaleza estocástica con
*temperature tuning* añade complejidad al diseño del experimento;
descartado. **DDPG / TD3**: deterministas *off-policy*, más inestables
que SAC y superados por este en casi todos los benchmarks; descartados.
**A3C / A2C**: menos eficientes en muestras y virtualmente abandonados
a favor de PPO desde 2018; descartados.

**Justificación.** Cuatro motivos coherentes con el marco metodológico.
*Estabilidad de entrenamiento*: el *clipped surrogate objective* limita
la divergencia de actualización sin requerir restricción explícita de
KL, lo que reduce la sensibilidad a hiperparámetros y mejora la
reproducibilidad —propiedad importante para un trabajo individual con
limitada compute para *sweeps* exhaustivos—.
*Interpretabilidad del Training Spec*: al ser *on-policy*, los
hiperparámetros tienen un significado semántico relativamente directo
(tamaño de rollout, épocas por update, ratio de clipping, coeficiente
de entropía), lo que facilita escribir el Training Spec del nivel L4b
como documento legible. *Soporte en herramientas abiertas*: la
implementación de Stable-Baselines3 está madura y admite integración
directa con Gazebo a través de la interfaz gymnasium-Gazebo-ROS2.
*Compatibilidad con extensiones*: si en futuras iteraciones la tesis
explorase *constrained RL* (al estilo de RECPO de Zhao et al., 2024),
PPO admite extensión natural a CMDP.

**Consecuencias.** El Training Spec del Capítulo 7 es legible para un
revisor sin entrenamiento profundo en RL. Los hiperparámetros
documentados en `training_specification.md` tienen significado
trazable a propiedades del bucle de entrenamiento.

**Referencias.** Schulman et al. (2017); Haarnoja et al. (2018) como
alternativa descartada; Zhao et al. (2024) RECPO como extensión futura.

---

### D-15 — Stack tecnológico: Stable-Baselines3 + PyTorch + pytest + Python 3.10+

| Campo | Valor |
| --- | --- |
| Sección | §3.6.4 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** Stack tecnológico del proyecto: Stable-Baselines3 como
implementación de PPO; PyTorch como backend de redes neuronales;
pytest como framework de testing para Cage Unit Tests (L4a' del V
adaptado) y suite de regresión general; Python 3.10+ con herramientas
de calidad ruff (linting), mypy (type checking) y pre-commit
(automatización en commits).

**Alternativas consideradas y descartadas.** Stable-Baselines (v2)
sobre TensorFlow (descartado: comunidad migrada a SB3/PyTorch). RLlib
sobre Ray (descartado: complejidad innecesaria para un proyecto
individual). unittest estándar (descartado: pytest tiene mejor
ergonomía y fixtures).

**Justificación.** Decisiones de tooling bien establecidas en
investigación contemporánea, todas con código auditable.
Stable-Baselines3 admite integración directa con gymnasium-Gazebo-ROS2
(cf. D-12). PyTorch es estándar de facto en investigación reciente y
tiene herramientas de profiling maduras. pytest con fixtures simplifica
los Cage Unit Tests de A2 (D-08).

**Consecuencias.** Las plantillas y CI/CD del proyecto se construyen
sobre este stack. La reproducibilidad del proyecto exige documentar
estas dependencias en `pyproject.toml` y fijarlas en `requirements.lock`.

---

### D-16 — Plataforma física: vehículo radio-controlado escala 1:14

| Campo | Valor |
| --- | --- |
| Sección | §3.6.5 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** Vehículo RC escala 1:14 instrumentado con cámara frontal
monocular, IMU para estimación de actitud, encoder de motor para
velocidad longitudinal, y SBC con soporte ROS2 para cómputo embebido.

**Alternativas consideradas y descartadas.** Escala 1:5 (descartada:
discrepancias dinámicas dominantes con simulación, mayor coste, mayor
riesgo en operación). Escala 1:1 (descartada: coste prohibitivo, riesgo
de operación, requerimientos legales fuera del alcance). Escala 1:24 o
menor (descartada: dinámica demasiado distante de la de un coche real
para ser informativa sobre el gap sim-to-real).

**Justificación.** Tres motivos articulados en §3.6.5. *Coste*: un 1:14
es manipulable, las piezas son asequibles y el riesgo de daño en
operación es acotado. *Seguridad de operación*: velocidades bajas,
energía cinética baja, riesgo para terceros despreciable en pista
cerrada. *Transferibilidad de la simulación*: la dinámica de un 1:14
admite aproximación razonable en Gazebo mediante un modelo plugin-based
con parámetros ajustables (masa, distribución de carga, fricción de
neumáticos, parámetros de actuación), mientras escalas mayores
introducirían discrepancias dinámicas que dominarían el gap sim-to-real.

**Consecuencias.** Las especificaciones detalladas (motor, ESC,
controlador de bajo nivel, cámara, plataforma de cómputo) se documentan
en el Capítulo 5 y en el Anexo correspondiente. El gap sim-to-real
caracterizado en el Capítulo 9 es específico de esta escala y no
extrapolable directamente a escalas mayores; esta limitación se declara
explícitamente en §3.9 y se discute en el Capítulo 12.

---

### D-17 — QED diferida a Fase 4: inspiración conceptual con calibración pendiente

| Campo | Valor |
| --- | --- |
| Sección | §3.6.6 |
| Estado | DIFERIDA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | Fase 4 (cuando se cuente con la *policy* entrenada y un conjunto de evaluaciones humanas de referencia) |

**Decisión.** La métrica compuesta QED (Gao et al., 2021) se considera
como *inspiración conceptual* del proyecto: una métrica calibrada
contra evaluadores humanos para tareas de conducción autónoma. La
adopción directa requiere matización porque QED fue desarrollada y
calibrada sobre CARLA, mientras el simulador adoptado es Gazebo
(D-12); la fórmula conceptual puede transferirse, pero los pesos
calibrados deberían recomputarse para el escenario *lane-following* en
Gazebo si se quiere una métrica con significado equivalente. Behavior
Metrics (Paniego et al., 2024) se considera como herramienta auxiliar
de evaluación cuantitativa, dado que su diseño es relativamente
agnóstico al simulador subyacente. La decisión sobre adopción
definitiva como métrica oficial del proyecto se difiere a Fase 4.

**Justificación.** No procede comprometerse a una métrica calibrada
sobre otra plataforma sin verificación. Diferir permite tomar la
decisión cuando se disponga de la *policy* entrenada y un conjunto de
evaluaciones humanas de referencia sobre el simulador efectivamente
adoptado.

**Consecuencias.** El Capítulo 4 define las métricas oficiales del
proyecto (M-P, M-S, M-I, M-C, M-T) sin comprometerse a QED como
obligatoria. La Fase 4 retoma la decisión y la confirma o la sustituye
por una métrica compuesta propia con calibración explícita.

**Referencias.** Gao et al. (2021); Paniego et al. (2024).

---

### D-18 — Documentación en plain-text Markdown (no MBSE industrial)

| Campo | Valor |
| --- | --- |
| Sección | §3.6.7 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |

**Decisión.** Todos los artefactos del proyecto —documentos, código,
plantillas, matriz de trazabilidad, scripts de validación— viven en un
único repositorio Git en formato plain-text. Markdown con extensiones
mínimas: citas en formato `Apellido (año)`, ecuaciones LaTeX, figuras
como SVG/PNG en carpeta dedicada. NO se adoptan herramientas MBSE
industriales (Cameo, Capella o similar).

**Alternativas consideradas y descartadas.** SysML + MBSE industrial al
estilo de Sprockhoff et al. (2023), descartado por coste cognitivo y
económico significativo, licencias inaccesibles para una tesis
individual, ROI negativo en proyecto de un autor. Documentación en
Word/Google Docs, descartada por no ser versionable de forma granular,
no auditable por línea, no integrable con CI/CD.

**Justificación.** El repositorio *es* el proyecto. Una tesis
individual obtiene mejor relación coste/beneficio con archivos de texto
versionados, manteniendo equivalencia funcional en cuanto a
trazabilidad (vía `traceability_matrix.csv` + `check_traceability.py`,
cf. D-10) y consistencia (vía revisión por pares automatizada en cada
commit). Conjetura, declarada en §3.6.7: escalar el marco a un equipo
industrial mediano sí motivaría el cambio a MBSE.

**Consecuencias.** Toda la trazabilidad de D-10 se materializa en
archivos de texto más script Python. Los diagramas se mantienen como
SVG editables. La tesis es íntegramente reproducible desde el
repositorio: cualquier persona con Git y un editor de texto puede
inspeccionar todo el trabajo.

**Referencias.** Sprockhoff et al. (2023) como contraste explícito.

---

### D-19 — Cinco criterios de meta-evaluación del marco

| Campo | Valor |
| --- | --- |
| Sección | §3.7 |
| Estado | CONFIRMADA |
| Fecha | D9 (Fase 0) |
| Revisión prevista | Capítulo 11 (aplicación de los criterios al cierre del trabajo) |

**Decisión.** El propio marco metodológico se evalúa al cierre del
trabajo (Capítulo 11) mediante cinco criterios meta con indicadores
concretos. *Integridad de la trazabilidad*: número de huérfanos en la
última ejecución de `check_traceability.py`; criterio de éxito: cero.
*Cobertura de SRs por evidencia experimental*: porcentaje de SRs con
veredicto pass/fail respaldado por evidencia cuantitativa; criterio de
éxito: 100% con veredicto, aunque sea fail. *Grado de anticipación de
hazards*: proporción de hazards anticipados en HARA frente a no
anticipados que emergen en operación. *Coste de adopción*: tiempo
dedicado a artefactos del marco vs artefactos técnicos puros, registrado
en este DECISIONS.md. *Productividad de la matriz*: número de cambios
técnicos cuyo análisis de impacto fue acelerado por la trazabilidad.

**Alternativas consideradas y descartadas.** Evaluación binaria del
marco "funcionó / no funcionó" (descartada: poca granularidad, pierde
información sobre qué partes funcionaron). Evaluación cuantitativa
única tipo NPS o equivalente (descartada: el marco no es un producto
comercial). Evaluación únicamente cualitativa (descartada: no admite
refutación clara, vulnerable a sesgo del autor).

**Justificación.** Un marco metodológico exitoso aplicado a un sistema
modesto, y un sistema brillante producido a pesar del marco, son dos
resultados distintos que conviene poder distinguir. Los cinco criterios
separan eficacia del marco de eficacia técnica del sistema. Coherente
con el design science research (D-05): la evaluación del artefacto es
distinta de la evaluación de su aplicación.

**Consecuencias.** El Capítulo 11 retoma los cinco criterios y emite
veredicto fundamentado sobre cada uno. Este DECISIONS.md sirve como
instrumento de medida del coste de adopción (criterio 4): cada decisión
añadida documenta tiempo invertido en marco vs tiempo invertido en
técnica.

---

## Decisiones futuras y pendientes

Las siguientes decisiones están explícitamente diferidas a fases
posteriores y se documentarán aquí cuando se tomen.

| ID provisional | Asunto | Fase de decisión |
| --- | --- | --- |
| D-20 (provisional) | Cierre de IDs definitivos en matriz de trazabilidad (SR-001..SR-00*k*, C-01..C-0*n*) | Fase 1 (D15–D19) |
| D-21 (provisional) | Confirmación o sustitución de QED como métrica oficial (cf. D-17) | Fase 4 |
| D-22 (provisional) | Adopción de Behavior Metrics como herramienta auxiliar oficial | Fase 4 |
| D-23 (provisional) | Decisión sobre fusión de `V-Model_Adaptado.md` con Capítulo 3 o conservación como anexo | Fase 6 |
| D-24 (provisional) | Estilo bibliográfico definitivo (IEEE numérico vs APA autor-año) | Fase 6 |

---

## Convenciones de uso del archivo

**Cómo añadir una decisión.** Toda decisión nueva se añade al final de
la sección "Decisiones" con el siguiente identificador disponible
(D-NN). Se añade también una fila al "Índice de decisiones" al inicio
del archivo. Se actualiza la "Última actualización" en el comentario
HTML del encabezado.

**Cómo modificar una decisión.** Las decisiones registradas no se
sobrescriben. Si una decisión cambia, se añade una nueva entrada que
**supersede** a la anterior, indicando explícitamente "Sustituye a
D-NN". La decisión anterior cambia su estado a "SUPERSEDIDA por D-MM"
pero su contenido se conserva. Esta convención preserva el historial
auditable y permite reconstruir la trayectoria de decisiones a
posteriori.

**Estados posibles.** *CONFIRMADA*: decisión tomada y vigente.
*DIFERIDA*: decisión diferida a una fase posterior, con fecha estimada
de revisión. *TENTATIVA*: decisión preliminar en fase de validación.
*SUPERSEDIDA*: reemplazada por una decisión posterior.

**Relación con la matriz de trazabilidad.** Las decisiones de este
archivo NO entran en la matriz `traceability_matrix.csv` salvo que
generen artefactos H, SR, C, SC o M. Sin embargo, los artefactos de la
matriz pueden citar decisiones de este archivo en su campo de
*justificación* mediante la referencia `cf. D-NN`.

**Coste de adopción (criterio D-19).** Cada nueva entrada añade entre
diez y veinte minutos de coste de adopción (redacción + revisión). Este
coste se considera explícitamente al evaluar el marco en el Capítulo 11.
