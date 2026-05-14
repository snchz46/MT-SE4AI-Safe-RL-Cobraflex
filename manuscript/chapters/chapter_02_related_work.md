# Capítulo 2 — Estado del arte

<!--
Estado: SEGUNDA REDACCIÓN (D9 de Fase 0).
Extensión objetivo: 12–16 páginas.
Convención: las secciones marcadas [LISTO] están redactadas a nivel borrador maduro.
Las marcadas [VERIFICAR] requieren confirmar afirmaciones específicas contra el
contenido exacto de los papers cuando se haga la revisión final.
-->

## 2.1 Introducción del capítulo  [LISTO]

El propósito de este capítulo es organizar la literatura relevante para la
tesis en un mapa coherente, identificar qué cubre cada línea de trabajo y, lo
más importante, dónde están las costuras entre líneas que esta tesis pretende
abordar de forma unificada. La revisión no es exhaustiva sino selectiva:
prioriza trabajos publicados en los últimos siete años y aquellos que han
tenido influencia visible sobre el discurso académico o normativo en seguridad
de sistemas con IA.

El capítulo se estructura del general al particular, terminando con una
síntesis crítica que motiva el aporte metodológico desarrollado a partir del
Capítulo 3. La sección 2.2 sitúa el aprendizaje por refuerzo en el panorama
de la conducción autónoma. La sección 2.3 revisa las cuatro familias de
aproximaciones a la seguridad en sistemas con componentes aprendidos: safe RL,
safety cages y filtros runtime, robustez frente a perturbaciones, y
monitorización en tiempo de operación. La sección
2.4 cubre la validación basada en escenarios. La sección 2.5 hace inventario
de los estándares aplicables. La sección 2.6 examina los pocos trabajos que
abordan el ciclo de vida completo. La sección 2.7 discute el gap sim-to-real.
La sección 2.8 sintetiza el panorama y posiciona explícitamente la tesis
respecto a él.

---

## 2.2 Aprendizaje por refuerzo en conducción autónoma  [LISTO]

El uso de aprendizaje automático en control de vehículos autónomos ha
evolucionado en tres oleadas sucesivas. La primera, basada en clonación de
comportamiento (*behavioural cloning*) e *imitation learning*, demostró que
una red neuronal podía mapear directamente píxeles de cámara a comandos de
volante, pero adolecía de fragilidad bajo desviaciones del estado experto y
limitada capacidad de generalización a situaciones no vistas durante el
entrenamiento. La segunda oleada, basada en aprendizaje por refuerzo profundo
(*deep reinforcement learning*, DRL), prometía superar estas limitaciones al
permitir que el agente explorase activamente las consecuencias de sus
decisiones (Kuutti et al., 2019a). La tercera oleada, en curso, combina ambas
estrategias mediante esquemas híbridos —preentrenamiento por imitación seguido
de afinado por refuerzo— y, más recientemente, integra modelos de mundo y
representaciones de seguridad explícitas.

<img src="../figures/Classical RL framework.png" alt="Figura 2 — The classical RL framework." width="400"/>

*Figura 2 — The classical RL framework (Source: Sutton and Barto 1998 [13]). The agent selects an action At at state St, in response to which it receives a corresponding reward R T +1 . The objective of the agent is to choose actions that maximize its reward over a long sequence of transitions.*

Dentro del paradigma DRL, dos algoritmos dominan los trabajos recientes en
control de vehículos autónomos: PPO (*Proximal Policy Optimization*) y SAC
(*Soft Actor-Critic*). PPO (Schulman et al., 2017) ofrece estabilidad de
entrenamiento gracias a su función de pérdida con *clipping*, lo que lo
convierte en una elección popular cuando se busca reproducibilidad y la
sensibilidad a hiperparámetros es un problema operativo. SAC (Haarnoja et al.,
2018), por su parte, optimiza un objetivo de máxima entropía que favorece la
exploración y la robustez, y al ser off-policy resulta más eficiente en
muestras. La elección entre uno y otro suele depender de la naturaleza del
espacio de acciones, la disponibilidad de cómputo, y la importancia que se
atribuya a la interpretabilidad del bucle de entrenamiento.

En el dominio concreto de seguimiento de carril y navegación, trabajos
recientes han mostrado la viabilidad de DRL puro para tareas acotadas. Cheng
et al. (2025) presentan un sistema de *lane keeping* y navegación basado en
DRL entrenado en simulación con *domain randomization* y desplegado sobre
una plataforma física, demostrando que la transferencia simulación-realidad
es factible con ajustes mínimos cuando el dominio operacional está
suficientemente acotado. Zhao et al. (2024) abordan el problema más complejo
de toma de decisiones en autopista mediante **RECPO** (*Replay buffer
Constrained Policy Optimization*), una variante de Constrained Policy
Optimization que combina restricciones tipo CMDP con *importance sampling*
sobre un replay buffer para mitigar el olvido catastrófico. La tendencia
general es clara: para tareas con horizonte de decisión corto y un dominio
operacional acotado —como el seguimiento de carril— DRL ofrece resultados
sólidos. Para tareas con horizontes largos y dominios abiertos, la
comunidad reconoce que DRL puro es insuficiente sin mecanismos adicionales
de garantía.

El problema estructural compartido por todos estos trabajos es el mismo: el
comportamiento de la *policy* aprendida no es derivable de una especificación
escrita a priori, lo que rompe el supuesto fundacional sobre el que descansan
los marcos clásicos de seguridad funcional. Esta limitación motiva las
familias de aproximaciones revisadas en la sección siguiente.

---

## 2.3 Aproximaciones a la seguridad en sistemas con componentes aprendidos  [LISTO]

La literatura sobre seguridad en sistemas con componentes RL/IA puede
organizarse en cuatro familias, cada una atacando el problema desde un ángulo
distinto del ciclo de vida.

### 2.3.1 Safe RL: incorporar seguridad en el entrenamiento

La primera familia, conocida genéricamente como *safe reinforcement
learning*, intenta restringir el comportamiento del agente desde el bucle de
entrenamiento, antes del despliegue. La taxonomía clásica del campo se
encuentra en el survey comprehensivo de García y Fernández (2015), que
distingue dos grandes ejes: modificación del criterio de optimización
(p. ej., introducción de restricciones en la función objetivo, aprendizaje
restringido por riesgo) y modificación del proceso de exploración (p. ej.,
exploración guiada por un experto o por un controlador seguro). Más de una
década después, esta taxonomía sigue siendo una referencia útil aunque haya
sido enriquecida por aportaciones posteriores.

Trabajos recientes han avanzado dentro de esta familia incorporando
representaciones explícitas de seguridad en el espacio de estados o en la
función de valor. Keswani y Bhattacharyya (2025) proponen **SRPL** (*Safety
Representations for Safer Policy Learning*), que codifican la proximidad a
estados inseguros como una representación predictiva aprendida durante el
entrenamiento, permitiendo que la *policy* internalice consideraciones de
seguridad sin recurrir a un mecanismo externo de contención. Su evaluación
sistemática sobre datasets reales —Waymo Open Motion Dataset y NuPlan—
reporta mejoras estadísticamente significativas en *success rate* y
reducción de coste con respecto a baselines no informados por safety. Esta
aproximación es elegante pero comparte una limitación estructural con todo
el paradigma safe RL: la garantía de seguridad sigue siendo estadística y
dependiente de la distribución del entrenamiento. La seguridad demostrada
en el dominio de entrenamiento no se transfiere automáticamente a un dominio
operacional con distribución desplazada.

### 2.3.2 Safety cages y filtros runtime: contención post-entrenamiento

La segunda familia, complementaria a la anterior, opera en tiempo de
inferencia y trata la *policy* aprendida como una caja negra cuyas salidas
deben filtrarse antes de actuar sobre el sistema físico. Kuutti et al. (2019b)
introducen el concepto de *safety cage* aplicado a vehículos autónomos: un
módulo determinista que monitoriza las salidas de la red neuronal y las
sustituye por acciones seguras cuando detecta que el comportamiento propuesto
violaría una invariante. La cage opera con reglas escritas a mano y, por
tanto, es enteramente verificable mediante técnicas clásicas de unit testing
y análisis estático.

Una extensión natural de esta idea aparece en Kuutti et al. (2021), donde la
cage cumple un doble papel: contención durante el despliegue y supervisión
débil (*weak supervision*) durante el entrenamiento. La cage se utiliza para
generar etiquetas implícitas de "acción correcta" sobre las salidas de la
*policy*, lo que reduce la necesidad de demostraciones humanas y acelera la
convergencia. Este uso dual de la cage —barrera de seguridad y profesor del
agente— es una de las ideas más fértiles del campo, porque establece una vía
sistemática para que la cage no solo contenga sino también *forme* el
comportamiento de la *policy*.

<img src="../figures/Idea of Safety Cage.png" alt="Figura 3 — Safety Cage applied to the classical RL framework." width="400"/>

*Figura 3 — Safety Cage applied to the classical RL framework.*

Una línea relacionada propone *predictive safety filters* basados en control
predictivo por modelo (MPC). En lugar de evaluar acciones puntualmente, el
filtro proyecta hacia el futuro las consecuencias de la acción propuesta por
la *policy* y solo la admite si la trayectoria predicha permanece dentro del
conjunto seguro. Tearle et al. (2021) aplican esta idea a control de
carreras basado en aprendizaje, demostrando que el filtro puede coexistir con
una *policy* DRL agresiva y desplazarla solo cuando la evidencia predictiva
indica violación inminente. La ventaja teórica de los filtros predictivos
sobre las cages basadas en reglas es la elegancia matemática y la facilidad
para razonar formalmente sobre garantías; la desventaja práctica es la
dependencia de un modelo dinámico suficientemente preciso, lo que en sistemas
con percepción ruidosa o dinámica desconocida resulta difícil de obtener.

### 2.3.3 Robustez frente a perturbaciones

La tercera familia se ocupa de la robustez de la *policy* frente a entradas
perturbadas, ya sea por ruido, por distribuciones no vistas, o por
adversarios deliberados. He et al. (2024) estudian empíricamente la robustez
de un controlador basado en Q-learning sobre TORCS frente a dos modelos de
amenaza distintos: manipulación de lecturas sensoriales y alteración directa
de la acción de salida. El hallazgo es contraintuitivo y metodológicamente
importante: las perturbaciones sobre sensores apenas afectan al sistema
(tasa de éxito de ataque ≈ 0% por la discretización del espacio de acciones
en cinco valores), mientras que la alteración directa de la acción tiene
éxito entre el 60% y el 78% de las veces. La discretización emerge como
mecanismo de "robustez accidental" frente a un canal de ataque pero deja
expuesto el otro.

Wei et al. (2026), en una contribución más reciente, proponen **CARRL**
(*Criticality-Aware Robust RL*) para atacar precisamente la asimetría que
He et al. ponen de manifiesto. CARRL tiene dos componentes: un adversario
de exposición al riesgo (REA) que concentra los ataques en estados
*safety-critical* bajo presupuesto limitado, y un agente robusto orientado
al riesgo (RTRA) que entrena sobre un dual replay buffer combinando datos
benignos y adversariales. Los autores reportan reducciones de tasa de
colisión de al menos 22.66% sobre los baselines del estado del arte.

Estos trabajos atacan una faceta complementaria del problema: incluso una
*policy* segura en el sentido de safe RL puede comportarse de forma
catastrófica si las entradas o las salidas pueden ser manipuladas. La
implicación metodológica es clara: la caracterización del comportamiento de
la *policy* debe incluir su respuesta frente a entradas y salidas fuera de
distribución nominal, y la cage debe diseñarse asumiendo que tanto la
*policy* como sus interfaces pueden fallar.

### 2.3.4 Monitorización en tiempo de operación y detección de error

Una cuarta familia, transversal a las tres anteriores, se ocupa de detectar
errores de la *policy* durante la operación misma del sistema, sin
pretender prevenirlos en entrenamiento ni contenerlos mediante reglas
externas. Mohseni, Pitale, Singh y Wang (2019), en una sistematización
particularmente útil para esta tesis, organizan el espacio de soluciones
técnicas para *machine learning safety* en automoción en torno a las cinco
gaps que el ML introduce sobre los estándares clásicos —especificación,
transparencia, verificación, performance y, crucialmente, *runtime
monitoring function*— y mapean cada gap a las cuatro estrategias de
seguridad de Varshney (*inherently safe design*, *safe fail*, *safety
margin*, *procedural safeguards*). Su contribución central, para el
propósito de esta tesis, es identificar la *monitoring function* como una
categoría arquitectónica propia y revisar tres familias de técnicas para
materializarla: estimación de incertidumbre (deep ensembles, MC-dropout),
detectores de error en distribución (selective classification, *reject
options*) y detectores *out-of-distribution* (OOD detectors, novelty
detection).

Esta categorización es relevante para la presente tesis por dos razones.
Primera, sitúa el *runtime monitoring* como respuesta sistemática a un
gap normativo identificado, no como práctica recomendada genérica. La
adaptación A3 propuesta en el Capítulo 3 hereda directamente esta
filosofía. Segunda, sus reseñas de uncertainty estimation, in-distribution
error detection y OOD error detection ofrecen un menú de técnicas
concretas que podrían enriquecer la cage del proyecto en iteraciones
futuras —aunque la versión inicial del marco se acota a una cage basada
en reglas, como se discute en el Capítulo 5—. Trabajos posteriores como
Vasudevan et al. (2021) extienden esta línea proponiendo *evidential deep
learning* para cuantificar incertidumbre en cumplimiento explícito con
ISO 26262.

### 2.3.5 Síntesis de la sección

Las cuatro familias revisadas son complementarias, no alternativas. Un
sistema maduro razonablemente debería incorporar elementos de las cuatro:
safe RL para formar el comportamiento desde el entrenamiento, una cage o
filtro para contener residuos en runtime, mecanismos de robustez frente a
perturbaciones de entrada, y monitorización continua en operación que
detecte errores y alimente evidencia para la validación. Sin embargo, la
literatura tiende a presentarlas como contribuciones aisladas, sin un
marco unificador que articule cómo se integran dentro de un ciclo de
vida completo con trazabilidad y safety case. Este es uno de los huecos
que esta tesis identifica explícitamente.

---

## 2.4 Validación basada en escenarios para sistemas autónomos  [LISTO]

Mientras las secciones anteriores se ocupan de cómo *construir* sistemas
seguros, la presente se ocupa de cómo *evaluarlos*. La pregunta central es
qué significa validar un sistema cuyo dominio operacional es continuo y, en
sentido estricto, infinito. La respuesta dominante en la última década es la
validación basada en escenarios (*scenario-based validation*), donde el
sistema se evalúa contra una biblioteca curada de situaciones representativas,
en lugar de pretender cobertura exhaustiva.

El problema teórico de fondo es la noción de cobertura. De Gelder et al.
(2024) abordan precisamente esta cuestión proponiendo métricas de cobertura
para bases de datos de escenarios destinadas a la evaluación de sistemas de
conducción automatizada. Su contribución central consiste en formalizar qué
quiere decir que una biblioteca *cubra* el dominio operacional, distinguiendo
entre cobertura sobre parámetros del escenario, sobre interacciones entre
agentes, y sobre clases de eventos críticos. Esta formalización es importante
porque sin métricas de cobertura, cualquier biblioteca puede defenderse como
"suficiente" mediante argumentos circulares.

En el plano operativo, dos plataformas han ganado tracción para evaluación
sistemática. CARLA (Dosovitskiy et al., 2017) se ha consolidado como el
simulador de referencia para tareas urbanas y permite construir escenarios
parametrizables con relativa facilidad. Gao et al. (2021) sistematizan la
evaluación cuantitativa de sistemas de conducción autónoma sobre CARLA
proponiendo **QED** (*Quantitative Evaluation for Driving*), una métrica
compuesta en escala 0–100 que pondera estancia en el centro de carril,
ausencia de *weaving*, cumplimiento del límite de velocidad y ausencia de
colisiones, calibrada contra evaluadores humanos con correlaciones de
Pearson de 0.96 y Spearman de 0.97 en escenarios estándar. Paniego et al.
(2024) presentan *Behavior Metrics*, una herramienta de código abierto para
evaluación de tareas de conducción autónoma que sistematiza la captura y
agregación de métricas tanto en simulación como en plataformas físicas
escalables. Esta herramienta es directamente aplicable al caso de estudio de
la presente tesis y se discute como instrumento candidato en la sección §3.6
del capítulo de metodología.

Una línea emergente, a medio camino entre validación y mejora del sistema, es
la generación automática de escenarios mediante el propio aprendizaje por
refuerzo. Giamattei et al. (2025) replican y extienden trabajos previos sobre
uso de RL para *online testing* de sistemas de conducción autónoma. Su
hallazgo metodológico es importante por contraintuitivo: en la replicación
estricta del estudio original, una vez controlados los sesgos de medición
de colisiones, **el RL no supera al random testing**; solo cuando se
extiende el agente con una función de recompensa saneada y un algoritmo
adecuado al espacio de estados continuo, el RL convierte su ventaja teórica
en mejora empírica. La lección práctica es que la elección del algoritmo y
la calidad de la métrica de fallo afectan al resultado más que la
sofisticación nominal del método.

Un eje todavía poco explotado en la literatura aplicada a vehículos a escala
es el uso de datasets de razonamiento sobre interacciones complejas. Trabajos
como WOMD-Reasoning ofrecen recursos a gran escala para entrenar y evaluar
sistemas que requieren comprender intenciones de otros agentes, una capacidad
que excede el alcance de la presente tesis pero que conviene mencionar para
contextualizar el espectro de evaluación.

La limitación común de toda esta línea de trabajo es que se ocupa de la
evaluación pero no del ciclo de vida. La validación basada en escenarios es
una pieza necesaria de un marco metodológico, pero por sí sola no constituye
un marco. Falta la articulación con la especificación, con la verificación, y
con el safety case.

---

## 2.5 Estándares y marcos normativos para IA en seguridad funcional  [LISTO]

El ecosistema normativo aplicable a vehículos autónomos con componentes IA se
ha movido sustancialmente en los últimos cinco años, pero permanece
fragmentado. Cinco documentos vertebran el espacio.

**ISO 26262:2018** establece el marco de seguridad funcional para vehículos
de carretera y formaliza el V-Model como ciclo de vida de referencia. Su
limitación, ampliamente reconocida, es que asume sistemas determinísticos
especificables a priori. Aplicarla literalmente a un módulo entrenado por
refuerzo conduce a contradicciones o a evasiones poco honestas, según se
discutió en la sección §1.2.

**ISO 21448:2022 (SOTIF)** —*Safety of the Intended Functionality*— extiende
el alcance de ISO 26262 a la consideración de comportamientos peligrosos que
no provienen de fallos del sistema sino de limitaciones de la función misma
en condiciones operacionales no anticipadas. Es la primera respuesta
institucional al problema de que sistemas con percepción y decisión basada en
ML pueden comportarse incorrectamente sin que ningún componente haya
"fallado" en sentido clásico. Wang et al. (2024) ofrecen un survey
sistemático sobre SOTIF y sus implicaciones, identificando los retos abiertos
en aplicación práctica del estándar y proponiendo, de forma notable para la
discusión metodológica de esta tesis, una reformulación del V-Model
tradicional con una "fase de operación" continua que integra monitorización
post-despliegue como brazo derecho extendido del ciclo de vida.

**ISO/IEC TR 5469:2024** es el documento normativo más específico publicado
hasta la fecha sobre uso de IA en funciones de seguridad. Su aportación
principal es la clasificación de elementos de tecnología IA en clases I y II
en función de la posibilidad de aplicar técnicas de seguridad funcional
clásicas. Los elementos de Clase I admiten verificación tradicional; los de
Clase II —entre los que cae típicamente una *policy* RL— requieren técnicas
específicas que el TR enumera pero no prescribe en detalle. Para los casos
en que no es posible cumplir directamente con IEC 61508 o ISO 26262, el TR
propone un *three-stage realization principle* (cláusula 7) que distingue
las fases de adquisición desde entradas/datos, inducción de conocimiento
desde datos de entrenamiento y conocimiento humano, y procesamiento y
generación de salidas; cada fase admite mecanismos distintos de seguridad
(robustez, especificabilidad, verificabilidad, interpretabilidad). La
estructura del TR es de guía, no de norma vinculante, lo que la hace útil
como brújula pero insuficiente como receta operativa.

**ISO/PAS 8800:2024** —*Road vehicles — Safety and AI*— es la
especialización automotriz del marco genérico de TR 5469. Publicada en 2024,
articula explícitamente cómo introducir componentes ML en el ciclo de vida
de seguridad funcional del vehículo, indicando qué cláusulas de ISO 26262 se
mantienen, cuáles se adaptan (*tailor*) y cuáles se sustituyen cuando hay un
componente de IA. Una aplicación temprana del estándar sobre un caso de uso
real —un detector de señales de stop— ha sido publicada por BSI y el UK
Centre for Connected and Autonomous Vehicles (BSI/CAM, 2024), constituyendo
la primera plantilla pública para articular ISO 26262 + SOTIF + ISO/PAS 8800
sobre una pipeline ML. Para la presente tesis, este documento es la
referencia más directa sobre cómo encajar las adaptaciones propuestas dentro
del marco normativo emergente.

**UL 4600:2023**, por su parte, formaliza la noción de *safety case* como
instrumento central de evidencia para productos autónomos. Koopman (2023)
ofrece una guía pragmática sobre qué incluir en un safety case bajo UL 4600,
particularmente útil porque articula el estándar con la práctica de
ingeniería real. La filosofía de UL 4600 es claim-argument-evidence: cada
afirmación de seguridad debe respaldarse con argumentos explícitos y
evidencia trazable.

Más allá de los estándares formales, varios trabajos sintetizan el panorama
desde perspectivas distintas. Wäschle et al. (2022) revisan AI safety en
conducción altamente automatizada mediante revisión sistemática (protocolo
Brereton/Kitchenham) sobre 145 referencias, organizando el campo en seis
áreas (alineamiento de valores, robustez adversarial, verificación formal,
runtime monitoring, cuantificación de incertidumbre, procesos de assurance)
e identificando como vacíos centrales la ausencia de métricas universalmente
aceptadas para *AI safety* y la inmadurez de los procesos de certificación.
Paterson et al. (2025) consolidan **AMLAS** (*Assurance of Machine Learning
for Autonomous Systems*), una metodología de seis etapas con patrones GSN
(*Goal Structuring Notation*) específicamente diseñada para construir
argumentos de safety sobre componentes ML, alineada con su ciclo de vida
data-céntrico (definición de requisitos, gestión de datos, aprendizaje,
verificación, despliegue, monitorización). AMLAS es la pieza argumentativa
que faltaba en el ecosistema y se está incorporando como insumo de los
estándares emergentes —notablemente ISO/PAS 8800—. Schlenoff, Kootbally
et al. (2024) en el informe **NIST IR 8527**, desde una perspectiva más
institucional, consolidan los hallazgos del segundo *Standards and
Performance Metrics for On-Road Automated Vehicles Workshop* y revisan
estándares y métricas en seis áreas (interacción de sistemas, percepción,
ciberseguridad, comunicaciones, IA e infraestructura digital), ofreciendo
una taxonomía útil de qué se mide y cómo en el ecosistema actual.

La síntesis de esta sección puede formularse así: cada estándar cubre un
ángulo necesario del problema —ISO 26262 el ciclo de vida clásico, SOTIF las
condiciones no anticipadas, TR 5469 la naturaleza específica de la IA,
ISO/PAS 8800 su especialización automotriz, UL 4600 la estructuración de la
evidencia, AMLAS los patrones argumentativos para ML—, pero ninguno por sí
solo prescribe una metodología ejecutable que los integre en un proyecto
concreto. La integración queda a cargo del equipo de ingeniería, y
precisamente esa integración es lo que esta tesis propone.

---

## 2.6 Adaptaciones del V-Model para sistemas con IA  [LISTO]

El nivel de granularidad más cercano a la aportación de esta tesis es el de
los trabajos que abordan explícitamente la adaptación del ciclo de vida —y
en particular del V-Model— para acomodar componentes basados en IA.

**Ullrich et al. (2025)** son la referencia más relevante en esta línea. Su
trabajo sobre la expansión del V-Model clásico para el desarrollo de
sistemas complejos que incorporan IA propone modificaciones estructurales
concretas: introducción de ciclos iterativos entre niveles, fases
data-céntricas explícitas (curación, anotación, entrenamiento, evaluación),
runtime monitoring como brazo derecho extendido, y artefactos específicos
del paradigma data-driven (*datasheets*, *model cards*, especificaciones
ODD). El alcance del trabajo es mayor del que cabría esperar de una mera
propuesta conceptual y constituye, junto con la reformulación de Wang et al.
(2024), el precedente directo más relevante para la tesis.

La diferencia entre el trabajo de Ullrich et al. y la presente tesis es de
naturaleza, no de objetivo último. Ullrich et al. articulan el *qué* —qué
modificaciones estructurales son necesarias y por qué— a un nivel de marco
conceptual transferible a múltiples dominios. Esta tesis articula el *cómo*
en tres dimensiones complementarias que el trabajo de referencia deja
abiertas: la operacionalización ejecutable de cada modificación en términos
de plantillas de artefactos y validadores automáticos (señaladamente, la
trazabilidad bidireccional como restricción dura aplicada por
herramienta); la concreción del marco sobre un caso de aplicación
documentado de extremo a extremo, desde HARA hasta despliegue físico; y la
caracterización empírica del gap sim-to-real como nivel obligatorio de
validación, no como práctica recomendada.

**Salay, Queiroz y Czarnecki (2017)** son, anteriormente, el antecedente
fundacional del campo. Su análisis sistemático sobre las diez partes de
ISO 26262 identifica cinco áreas concretas donde el uso de aprendizaje
automático impacta al estándar: identificación de hazards (incluyendo
modos de fallo específicos de RL como el *reward hacking* o las
interacciones humano-vehículo derivadas de la complacencia operativa),
faltas y modos de fallo, uso de training sets en sustitución de
especificaciones (vinculado al supuesto de especificabilidad del V-Model),
nivel arquitectónico vs. unidad de implementación, y aplicabilidad de las
técnicas software prescritas en la Parte 6. La aportación cuantitativa
más relevante es el análisis de las 75 técnicas software del estándar:
aproximadamente el 40% no aplica a componentes ML sin modificación,
distribuidas entre las categorías "OK" (directamente aplicable), "Adapt"
(aplicable con modificación) y "N/A" (no aplicable por sesgo hacia
lenguajes imperativos). Las recomendaciones del paper —desaconsejar el
ML *end-to-end* a nivel arquitectónico, expandir la definición de hazard
para incluir interacciones humano-vehículo, exigir especificaciones
parciales y métricas de cobertura sobre training sets, y reformular las
técnicas de la Parte 6 en términos de *intent* en lugar de detalle
imperativo— anticipan, en su mayoría, las direcciones que esta tesis
materializa.

El trabajo es directamente relevante para la presente tesis en dos
sentidos. Primero, los cinco supuestos S1–S5 desarrollados en el
Capítulo 3 son una reformulación operativa del análisis de Salay et al.,
articulada de modo que cada supuesto admite una adaptación A1–A5
correspondiente. Segundo, la recomendación de limitar el ML al nivel
de componente (no arquitectural) coincide con la decisión arquitectónica
de la tesis de mantener la *policy* PPO como un módulo dentro de una
arquitectura ROS2 explícita, no como un sistema *end-to-end*.

**Vasudevan, Abdullatif, Kabir y Campean (2021)**, posteriormente,
proponen un *framework* específico para manejar incertidumbres de
modelos ML en cumplimiento explícito con ISO 26262. Su contribución
articula el uso de *evidential deep learning* (Sensoy et al., 2018) como
mecanismo para cuantificar incertidumbre epistémica y aleatoria de los
modelos, integrando los resultados como insumo a las actividades de
V&V del estándar. La construcción es coherente con Salay et al. (2017)
y con Mohseni et al. (2019), a los que cita explícitamente, y representa
un paso intermedio entre la identificación del problema (Salay et al.)
y la operacionalización completa que esta tesis propone. Para los
propósitos de la presente tesis, Vasudevan et al. son una **referencia de
contexto** que demuestra que el trabajo de adaptación de ISO 26262 a ML
es una línea de investigación activa con publicaciones recientes, pero
acotada a aspectos puntuales (gestión de incertidumbre) y sin caso de
aplicación de extremo a extremo.nnn

**Sprockhoff et al. (2023)**, desde el dominio aeroespacial, ofrecen una
perspectiva complementaria mediante Model-Based Systems Engineering aplicado
a sistemas con componentes IA. Sobre un caso de uso de localización de
amenazas basada en IA, ilustran tres aplicaciones de MBSE: modelado del
sistema y su contexto operacional, trazabilidad de requisitos a componentes
de IA, e integración de actividades de V&V específicas para AI usando SysML.
Su filosofía —el modelo es el artefacto central del proyecto, no la
documentación textual— casa naturalmente con la trazabilidad estricta
requerida por sistemas con IA. La limitación práctica es la curva de
adopción: las herramientas MBSE industriales tienen un coste cognitivo y
económico significativo que las hace poco accesibles para proyectos
académicos o de menor escala, donde una aproximación basada en archivos de
texto versionados —como la que esta tesis adopta— resulta más operativa
manteniendo equivalencia funcional en cuanto a trazabilidad y consistencia.

Más allá de estos cuatro trabajos, la literatura sobre adaptaciones del
ciclo de vida es notablemente escasa. La mayor parte del esfuerzo
investigador se ha concentrado en aspectos puntuales —entrenamiento seguro,
verificación de redes, validación basada en escenarios— y no en la
integración global. Esta asimetría es comprensible: las contribuciones
puntuales son más publicables y admiten evaluación cuantitativa más limpia.
Pero también explica por qué la adopción industrial de IA en funciones de
seguridad sigue siendo un proceso ad-hoc, dependiente del juicio del equipo
más que de un marco compartido.

---

## 2.7 El gap sim-to-real y su caracterización  [LISTO]

Toda *policy* entrenada en simulación enfrenta, al desplegarse en un sistema
físico, una pregunta inevitable: ¿en qué medida el comportamiento aprendido
se transfiere? El gap entre el entorno de simulación y el entorno real
—conocido como *sim-to-real gap*— ha sido objeto de estudio sostenido en
robótica de manipulación y, en menor grado, en conducción autónoma.

Las técnicas para reducir el gap se agrupan en tres familias principales:
*domain randomization*, que entrena la *policy* sobre una distribución
amplia de variantes simuladas para ganar robustez frente a la incertidumbre
del entorno físico; *domain adaptation*, que ajusta la *policy* o sus
representaciones internas para adaptarse al dominio real con datos limitados;
y *system identification*, que mejora la simulación mediante calibración
contra datos físicos. Estas familias son complementarias y los sistemas más
robustos tienden a combinarlas.

El problema, sin embargo, no es solo cómo reducir el gap, sino cómo
*caracterizarlo* honestamente. Un sistema desplegado puede comportarse
razonablemente bien en el promedio y catastróficamente mal en condiciones
específicas no caracterizadas. La literatura está rica en propuestas para
reducir el gap pero pobre en marcos sistemáticos para *medirlo* en términos
útiles para el safety case. Esta carencia es uno de los motivos por los que
la adaptación A5 del marco propuesto en el Capítulo 3 incorpora la
caracterización del gap como nivel obligatorio del ciclo de vida.

El simulador adoptado en esta tesis es Gazebo (Koenig y Howard, 2004),
operado a través de una interfaz gymnasium-Gazebo-ROS2 que reutiliza un
entorno previamente construido por el autor en un trabajo de investigación
anterior. Esta elección difiere de la práctica dominante en investigación
de conducción autónoma, donde CARLA (Dosovitskiy et al., 2017) es el
ecosistema de referencia, y se justifica con detalle en la sección 3.6.1
del Capítulo 3 a partir de cuatro razones: integración ROS2 nativa,
reutilización del trabajo previo del autor, disponibilidad de la interfaz
gymnasium-Gazebo-ROS2, y requisitos de cómputo más modestos. Para los
propósitos del presente capítulo basta señalar dos cosas. Primero, que la
fidelidad sensorial de Gazebo es razonable para el caso de seguimiento
de carril en pista controlada con cámara monocular pero su fidelidad
visual es inferior a la que ofrece el motor Unreal Engine subyacente a
CARLA, lo que tiene implicaciones para la magnitud esperable del gap
sim-to-real que la adaptación A5 del marco propuesto exige caracterizar
empíricamente. Segundo, que para vehículos a escala 1:14, como el
utilizado en esta tesis, la correspondencia entre la dinámica simulada y
la real introduce discrepancias específicas —fricción de neumáticos,
latencias del lazo de control, ruido de sensores embebidos— que requieren
caracterización empírica con independencia del simulador concreto. Cheng
et al. (2025) ofrecen un precedente reciente y directamente relevante:
aplican *domain randomization* sobre observaciones cámara y estado
vehicular durante el entrenamiento, y reportan transferencia
satisfactoria a un vehículo físico bajo distintas condiciones de
iluminación y trazado. Su trabajo establece la viabilidad técnica del
sim-to-real para tareas de lane-keeping pero, como el resto de la
literatura, se concentra en la *reducción* del gap más que en su
*caracterización sistemática* para safety case. Este será el contenido
principal del Capítulo 9.

---

## 2.8 Síntesis crítica y posicionamiento de la tesis  [LISTO]

Tras revisar las seis líneas de trabajo precedentes, es posible elaborar una
visión consolidada del estado del arte y articular con precisión el espacio
que esta tesis ocupa.

La tabla siguiente resume las contribuciones principales de las líneas
revisadas a lo largo de seis ejes de interés: tratamiento del entrenamiento
seguro, contención runtime, validación basada en escenarios, marco de ciclo
de vida, trazabilidad explícita, y caracterización del gap sim-to-real. Una
columna adicional indica la presencia de un caso de aplicación documentado
de extremo a extremo.

| Work / line | Safe training | Cage / runtime filter | Scenario validation | Lifecycle | Explicit traceability | Sim-to-real gap | E2e case study |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| García y Fernández (2015) — safe RL survey (taxonomy) | ✓ | – | – | – | – | – | – |
| Salay et al. (2017) — foundational analysis ISO 26262 ↔ ML (S1–S5) | – | – | – | partial | – | – | – |
| Kuutti et al. (2019b, 2021) — safety cage AV (runtime + weak supervision) | partial | ✓ | – | – | – | – | – |
| Mohseni et al. (2019) — practical ML safety | – | partial | – | partial | – | – | – |
| Tearle et al. (2021) — predictive safety filter (MPC) | – | ✓ | – | – | – | – | – |
| Vasudevan et al. (2021) — uncertainty + ISO 26262 | – | partial | – | partial | – | – | – |
| Keswani & Bhattacharyya (2025) — SRPL (safety representations) | ✓ | – | – | – | – | – | – |
| Wei et al. (2026) — CARRL (critical robust RL + adversarial) | ✓ | – | – | – | – | – | – |
| He et al. (2024) — Q-learning + adversarial (TORCS) | – | – | partial | – | – | – | – |
| De Gelder et al. (2024) — scenario coverage metrics | – | – | ✓ | – | – | – | – |
| Gao et al. (2021) — QED | – | – | ✓ | – | – | – | – |
| Paniego et al. (2024) — Behavior Metrics (eval. toolkit) | – | – | ✓ | – | – | – | – |
| Giamattei et al. (2025) — RL for online testing | – | – | ✓ | – | – | – | – |
| Cheng et al. (2025) — DRL lane-keeping + sim2real | partial | – | – | – | – | partial | partial |
| Wang et al. (2024) — SOTIF | – | – | partial | partial | – | – | – |
| Paterson et al. (2025) — AMLAS | – | – | – | partial | ✓ | – | – |
| Koopman (2023) — UL 4600 | – | – | – | partial | partial | – | – |
| BSI/CAM (2024) — PAS 8800 | – | – | partial | ✓ | partial | – | partial |
| Sprockhoff et al. (2023) — MBSE | – | – | – | ✓ | ✓ | – | – |
| Ullrich et al. (2025) — expanded V-Model for AI | partial | partial | partial | ✓ | partial | – | – |
| **This thesis** | **partial** | **✓** | **✓** | **✓** | **✓** | **✓** | **partial** |

*Table 1 — Positioning space for this thesis.*

La lectura de la tabla permite formular tres observaciones que sintetizan el
panorama y motivan la contribución de la tesis.

**Primera observación.** Las contribuciones puntuales son sólidas y, en
muchos casos, profundas. Cada trabajo ataca su problema con rigor y aporta
evidencia robusta sobre la solución propuesta. No es razonable, ni necesario,
intentar mejorar a la literatura en ninguno de los ejes individuales: la
tesis adopta soluciones existentes para entrenamiento (PPO de Schulman et
al., 2017), para cage (la tradición Kuutti et al., 2019b, 2021), y para
validación basada en escenarios (la metodología cristalizada por De Gelder
et al., 2024 y Paniego et al., 2024).

**Segunda observación.** Existen propuestas que abordan explícitamente la
adaptación del ciclo de vida ISO 26262 a sistemas con ML, en una línea
que arranca con el análisis fundacional de Salay, Queiroz y Czarnecki
(2017) —antecedente conceptual directo de los supuestos S1–S5
desarrollados en el Capítulo 3—, continúa con propuestas de
operacionalización parcial (Mohseni et al., 2019; Vasudevan et al.,
2021) y culmina, hasta la fecha, en marcos más comprensivos como Ullrich
et al. (2025), la reformulación de V-Model con fase de operación de Wang
et al. (2024), AMLAS de Paterson et al. (2025), y el use case BSI/CAM
(2024) sobre PAS 8800. Algunas de las modificaciones que esta tesis
propone encuentran precedente en estos trabajos: la idea de runtime
monitoring como brazo derecho extendido (presente en Ullrich et al.,
Wang et al., y conceptualizada por Mohseni et al. como *monitoring
function*) anticipa la adaptación A3; los patrones GSN de AMLAS
comparten filosofía con la trazabilidad bidireccional propuesta como A4;
la recomendación de Salay et al. de evitar el ML *end-to-end* y limitar
su uso al nivel de componente coincide con la decisión arquitectónica de
mantener la *policy* PPO como módulo dentro de una arquitectura ROS2
explícita; el use case BSI/CAM articula ISO 26262 + SOTIF + PAS 8800
sobre un componente ML, mostrando que la integración multi-estándar es
factible. La novedad de esta tesis no radica, por tanto, en haber
inventado las adaptaciones, sino en tres dimensiones complementarias que
ningún trabajo previo cubre simultáneamente:

- **Operacionalización ejecutable.** Cada adaptación se materializa en
  artefactos concretos (plantillas, scripts, validadores) en lugar de
  permanecer como recomendación de marco.
- **Trazabilidad como restricción dura.** A4 convierte la trazabilidad de
  buena práctica documental en propiedad verificable por herramienta
  automatizada (`check_traceability.py`), lo que excede el plano descriptivo
  de AMLAS y MBSE.
- **Caso de aplicación de extremo a extremo.** Los precedentes metodológicos
  permanecen en plano conceptual o usan casos de uso ilustrativos breves.
  Esta tesis aplica el marco completo desde HARA hasta despliegue físico,
  documentando los puntos de fricción y los costes reales.

**Tercera observación.** La caracterización del gap sim-to-real es el eje
más débilmente cubierto en la literatura aplicable a este dominio. Cheng et
al. (2025) demuestran que la transferencia es factible mediante *domain
randomization*, pero su trabajo se centra en la *reducción* del gap, no en
su *caracterización* sistemática para safety case. Existen técnicas para
reducir el gap, pero los marcos sistemáticos para *medirlo* en términos
compatibles con un safety case son escasos. La adaptación A5 del marco
propuesto en esta tesis, junto con el desarrollo del Capítulo 9, es una
contribución específica en este eje, aunque su validez externa quedará
limitada al caso particular de un vehículo a escala 1:14 sobre pista
controlada.

Con este panorama establecido, el Capítulo 3 desarrolla en detalle el marco
metodológico —el V-Model adaptado con sus cinco modificaciones A1–A5— que
constituye el aporte académico central de la tesis.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

D9 (primera redacción + verificación bibliográfica):
  [x] Estructura de secciones 2.1–2.8
  [x] Redacción borrador maduro de las ocho secciones
  [x] Tabla de síntesis en §2.8 con siete ejes y veintiún trabajos comparados
  [x] Verificación bibliográfica de todas las referencias (compass research report)
  [x] Corrección factual en §2.3.3 (He et al.: la robustez "accidental" está
       en la discretización, no en la red; ataques sobre la acción son los
       devastadores, no los ataques sobre sensores)
  [x] Incorporación de ISO/PAS 8800:2024 y BSI/CAM use case en §2.5
  [x] Incorporación de AMLAS por nombre en §2.5
  [x] Cita explícita a Sprockhoff et al. (2023) en §2.6
  [x] Reposicionamiento honesto de Ullrich et al. en §2.6 y §2.8
  [x] Acknowledgment de Wang et al. (2024) como precedente de A3 (V con fase
       de operación continua)
  [x] Especificación de algoritmos: RECPO (Zhao), SRPL (Keswani),
       CARRL (Wei), QED (Gao)
  [x] Hallazgo metodológico de Giamattei et al. correctamente expresado
       (en replicación pura el RL NO supera al random; sí lo hace solo
       con el agente extendido)
  [x] Incorporación del three-stage realization principle de TR 5469 en §2.5
       (relevante metodológicamente para Capítulo 3)
  [x] Atribución correcta del NIST IR 8527 a Schlenoff, Kootbally et al.
  [x] Nueva subsección §2.3.4 sobre Runtime Monitoring como categoría propia
       (Mohseni et al. 2019, Vasudevan et al. 2021); reorganización de
       §2.3 de tres a cuatro familias
  [x] Subsección dedicada a Salay et al. (2017) y Vasudevan et al. (2021)
       en §2.6 como antecedentes específicos de adaptación ISO 26262 + ML;
       reposicionamiento honesto de la novedad de la tesis frente a estos
       precedentes
  [x] Tres filas nuevas en tabla de §2.8 (Salay 2017, Mohseni 2019,
       Vasudevan 2021)
  [x] Reformulación de "Segunda observación" en §2.8 reconociendo Salay
       et al. como antecedente fundacional, alineamiento explícito con la
       recomendación de evitar ML end-to-end

Fase 1 (D15–D19):
  [ ] Confirmar inclusión de WOMD-Reasoning (Li et al. 2025) — actualmente no
       lo cito porque su uso central es percepción/LLM, distante del foco
       de esta tesis. Decidir si añadir en §2.4 como nota al pie.
  [ ] Identificar el documento `vehicles0700100v2.pdf` (no identificable
       desde el reporte; abrir el PDF y verificar portada). Posiblemente
       UNECE GRVA / WP.29 sobre ADS validation.

Fase 6 (consolidación):
  [ ] Pulido final de prosa, conectores, ritmo
  [ ] Verificar entradas BibTeX y formato definitivo según el estilo
       de citación elegido (IEEE numérico vs APA autor-año)
  [ ] Decisión: ¿añadir referencia a IEC 61508 como ascendiente común
       de ISO 26262 y TR 5469?

REFERENCIAS USADAS EN ESTE CAPÍTULO (D9 — todas verificadas):

  Surveys / reviews:
  - García y Fernández, 2015 (JMLR — Safe RL survey)
  - Kuutti et al., 2019a (IEEE T-ITS — DL applications to AV control)
  - Wäschle et al., 2022 (Frontiers in AI — AI Safety in HAD)
  - Wang et al., 2024 (Engineering — Survey on SOTIF)
  - Schlenoff/Kootbally et al., 2024 (NIST IR 8527)
  - Paterson et al., 2025 (RESS — Safety assurance of ML / AMLAS)

  RL para conducción autónoma:
  - Cheng et al., 2025 (Electronics 14(13):2738 — DRL lane-keeping sim2real)
  - Zhao et al., 2024 (Sensors 24(13):4140 — RECPO)
  - Schulman et al., 2017 (arXiv:1707.06347 — PPO)
  - Haarnoja et al., 2018 (ICML PMLR 80:1861 — SAC)

  Safety RL / cages / filtros:
  - Kuutti et al., 2019b (Safety cages para AVs)
  - Kuutti et al., 2021 (RL débil + cages virtuales)
  - Tearle, Wabersich, Carron, Zeilinger, 2021 (IEEE L-CSS / arXiv:2102.11907 — PSF)
  - Keswani y Bhattacharyya, 2025 (arXiv:2512.17586 — SRPL)

  Robustez:
  - He, Zhao, Mori, 2024 (NDSS Symposium 2024 Posters — Q-learning vs adversarial)
  - Wei et al., 2026 (arXiv:2601.01800 — CARRL)

  Validación basada en escenarios:
  - De Gelder, Buermann, Op den Camp, 2024 (IEEE IAVVC — Coverage metrics)
  - Gao, Paulissen, Coletti, Patton, 2021 (IEEE IV — QED)
  - Paniego, Calvo-Palomino, Cañas, 2024 (SoftwareX — Behavior Metrics)
  - Giamattei et al., 2025 (Empirical SE 30(1):19 — RL online testing)

  V-Model y MBSE / Adaptación de ISO 26262 a ML:
  - Salay, Queiroz, Czarnecki, 2017 (arXiv:1709.02435 — análisis fundacional
       del impacto de ML sobre ISO 26262; antecedente directo de S1–S5)
  - Mohseni, Pitale, Singh, Wang, 2019 (arXiv:1912.09630 — soluciones
       prácticas para ML safety en AVs; introduce monitoring function como
       categoría propia mapeada a las cuatro estrategias de Varshney)
  - Vasudevan, Abdullatif, Kabir, Campean, 2021 (UKCI 2021,
       DOI 10.1007/978-3-030-87094-2_45 — framework para incertidumbres ML
       conforme ISO 26262; usa evidential deep learning)
  - Sprockhoff, Lukic, Janson, Ahlbrecht, Durak, Gupta, Krueger, 2023
       (AIAA SCITECH 2023-2587 — MBSE for AI-Based Systems)
  - Ullrich, Buchholz, Dietmayer, Graichen, 2025 (IEEE T-IV 10(3) — V-Model expandido)

  Estándares y safety case:
  - ISO 26262:2018
  - ISO 21448:2022 (SOTIF)
  - ISO/IEC TR 5469:2024
  - ISO/PAS 8800:2024 (Road vehicles — Safety and AI)
  - BSI / UK CAM, 2024 (Use case application of PD ISO/PAS 8800 for ML)
  - UL 4600:2023 (vía Koopman, 2023)
  - Koopman, 2023 (IEEE Computer — UL 4600 safety case)

  Simulador y datasets:
  - Dosovitskiy, Ros, Codevilla, López, Koltun, 2017 (CoRL — CARLA)
  - Li et al., 2025 (ICML PMLR 267 — WOMD-Reasoning) — referencia disponible
       pero no citada en el cuerpo por estar fuera del foco metodológico
-->
