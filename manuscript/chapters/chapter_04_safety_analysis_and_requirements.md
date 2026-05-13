# Capítulo 4 — Dominio Operacional, Análisis de Hazards y Requisitos de Seguridad

<!--
Estado: PRIMERA REDACCIÓN D11 (Fase 1).
Extensión objetivo: 14-18 páginas.
Convención: las secciones marcadas [BORRADOR D11] tienen prosa en estado de
borrador maduro de Fase 1 fijada el día indicado y dependen únicamente del
marco metodológico del Capítulo 3 y de la literatura. Las marcadas
[COMPLETAR FASE 1 / Dxx] dependen de los artefactos cuyo cierre se produce
en el día indicado dentro de Fase 1: la operacionalización del Hazard
Register en D12-D13, la STPA ligera en D13, la SRS en D14-D16, y la
construcción de la matriz de trazabilidad en D17. Las marcadas [PULIDO FASE 6]
requieren retoques estilísticos al cierre del trabajo, una vez que las
referencias cruzadas a los Capítulos 6, 7, 8, 9 y 10 puedan apuntar a
contenido cerrado.

Notación de identificadores en este capítulo:
- Hazards: H-01, H-02, ..., H-07.
- Safety Requirements: SR-001, SR-002, ..., SR-008.
- Cage Rules: C-01, ..., C-06 (definidos en el Capítulo 5; aquí solo
  referenciados desde la columna de implementación de los SRs).
- Dominios operacionales: ODD-1, ODD-2, ODD-3, ODD-4 (definidos en docs/08_odd_specification.md;
  aquí resumidos en §4.3).
- Parámetros del ODD: ODD-N.<PARAM>, por ejemplo ODD-1.LANE_WIDTH = 0.245 m.
- Niveles de criticidad: SR-CL-A (alto), SR-CL-B (medio), SR-CL-C (bajo);
  derivados según §4.7.
-->

## 4.1 Introducción del capítulo  [BORRADOR D11]

El Capítulo 3 estableció el V-Model adaptado como marco metodológico de la
tesis y describió, en su §3.5.2, los seis niveles que articulan la rama
izquierda del modelo. El presente capítulo desarrolla los dos primeros de
esos niveles para el caso de estudio lane-following: el nivel L1, que
formaliza el dominio operacional y la función pretendida del sistema, y
el nivel L2, que produce el análisis sistemático de hazards y la
derivación de Safety Requirements asignados a niveles de criticidad. Junto
con la primera versión consolidada de la matriz de trazabilidad, estos
artefactos constituyen la *especificación de seguridad* del sistema, en el
sentido en que la entiende ISO 26262 (ISO 26262:2018), refinada para
componentes basados en aprendizaje según los principios articulados en
ISO/PAS 8800:2024 e ISO/IEC TR 5469:2024.

Conviene declarar de entrada qué hace y qué no hace este capítulo.
Establece el dominio operacional dentro del cual se garantizan las
propiedades de seguridad, identifica de manera sistemática los hazards
relevantes, deriva un conjunto cerrado y falsable de Safety Requirements
con su correspondiente rationale y niveles de criticidad, y materializa
por primera vez en el trabajo la trazabilidad bidireccional entre hazards
y SRs como restricción verificable por herramienta. No describe la
arquitectura del sistema —que es objeto del Capítulo 5—, no especifica las
reglas de la cage runtime —que se derivan de los SRs en §5.4 y se
documentan en §5.5—, y no presenta evidencia experimental sobre el
cumplimiento de los requisitos —que se acumula a lo largo de los
Capítulos 8, 9 y 10—. El capítulo es, en este sentido, puramente de
especificación: produce las restricciones que los capítulos siguientes
deben respetar y validar.

La estructura del capítulo es la siguiente. La §4.2 caracteriza la
función pretendida del sistema y enumera los requisitos a nivel de
sistema en su forma más abstracta. La §4.3 resume el dominio operacional
formalizado, cuyo desarrollo completo vive como artefacto autónomo en
`docs/08_odd_specification.md` y se cita desde aquí. La §4.4 desarrolla
el procedimiento HARA aplicado al caso de estudio y presenta el Hazard
Register resultante. La §4.5 documenta la STPA ligera utilizada como
complemento sistémico para los hazards más críticos. La §4.6 describe el
procedimiento de derivación de Safety Requirements desde hazards y
presenta la SRS consolidada. La §4.7 articula los niveles de criticidad
asignados a cada SR y discute las consecuencias prácticas de la
asignación. La §4.8 presenta la primera versión de la matriz de
trazabilidad bidireccional y caracteriza el procedimiento mediante el
cual `tools/check_traceability.py` la verifica. La §4.9 declara las
limitaciones del análisis presentado. La §4.10 cierra con una transición
al Capítulo 5.

---

## 4.2 Función pretendida y requisitos a nivel de sistema  [BORRADOR D11]

### 4.2.1 Función pretendida

La función pretendida del sistema es el seguimiento de carril en una
plataforma vehicular a escala 1:14 (CobraFlex), entrenado por refuerzo
mediante PPO (Schulman et al., 2017) en simulación Gazebo (Koenig y
Howard, 2004) sobre una interfaz gymnasium-Gazebo-ROS2 reutilizada de
un trabajo previo del autor, y desplegado físicamente bajo la
supervisión de una safety cage de reglas determinista (Kuutti et al.,
2019b). La elección de simulador queda justificada en §3.6.1 del
Capítulo 3 (decisión D-02 registrada en `DECISIONS.md`). El sistema percibe el
estado relativo del vehículo respecto al carril y emite acciones de
control que mantienen al vehículo dentro del carril durante la operación
nominal y dentro del corredor transitable durante la operación adversa.
La función pretendida es deliberadamente acotada: no incluye planificación
de ruta, gestión de intersecciones, interacción con otros agentes
dinámicos, ni decisiones tácticas más allá del control lateral —y, en los
dominios curvos, longitudinal— necesario para mantener la trayectoria
dentro de los límites del carril.

El acotamiento de la función pretendida no es una elección arbitraria
sino la condición de validez del análisis de seguridad que sigue. Una
función pretendida ambigua produce un HARA ambiguo, un HARA ambiguo
produce SRs incompletos, y SRs incompletos producen una cage que no
cubre el espacio de hazards relevante. La trazabilidad bidireccional
exigida por la adaptación A4 (§3.4.4) hace que cualquier ambigüedad en
este punto se propague mecánicamente al resto del análisis. Por esta
razón, la función pretendida queda fijada formalmente en esta sección y
cualquier modificación posterior se registra como decisión D-XX con su
correspondiente justificación y se propaga a través de la matriz de
trazabilidad.

### 4.2.2 Requisitos de sistema (SyR)

Los requisitos de sistema, denotados SyR-XXX para distinguirlos de los
Safety Requirements derivados en §4.6, expresan las propiedades de alto
nivel que el sistema debe satisfacer en su conjunto. Los SyR se obtienen
de la función pretendida mediante refinamiento progresivo y constituyen
el ancla de nivel L1 del V-Model adaptado. Esta tesis utiliza un conjunto
mínimo de cinco SyR, suficiente para articular el caso de estudio sin
introducir compromisos no relacionados con la aportación metodológica.

**SyR-001** El sistema mantendrá al vehículo dentro del carril definido
por el dominio operacional vigente durante operación nominal y dentro
del corredor transitable durante operación adversa.

**SyR-002** El sistema operará exclusivamente dentro de los dominios
operacionales formalizados ODD-1 a ODD-4. Las condiciones fuera de los
ODDs serán detectadas y producirán una transición a estado seguro.

**SyR-003** El sistema acompañará cada decisión de control con un
mecanismo runtime independiente capaz de inhibir o reemplazar acciones
que violen los Safety Requirements derivados en §4.6.

**SyR-004** El sistema producirá un registro auditable de su operación
suficiente para verificar el cumplimiento de cada Safety Requirement
mediante evidencia cuantitativa.

**SyR-005** El sistema admitirá despliegue físico parcial sobre la
plataforma CobraFlex 1:14 con caracterización empírica del gap
sim-to-real para las métricas principales de rendimiento e intervención.

Los cinco SyR están articulados de modo que cada uno se refina más
adelante en uno o más SRs o se satisface por un mecanismo
arquitectónico específico. SyR-001 y SyR-002 se refinan en SR-001 a
SR-004 sobre permanencia en carril, orientación, TTLC y velocidad.
SyR-003 se refina en SR-005 a SR-008 sobre transición a estado
seguro, suavidad de actuación, validez de estado y parada
controlada. SyR-004 no produce un SR numerado: se satisface
arquitectónicamente por el output `/cage_status` y los intervention
logs especificados en la Cage Specification del Capítulo 5, que cada
SR de la SRS cita en su columna de Verificación como medio de
evidencia. SyR-005 no se refina en SRs sino en la actividad
experimental del Capítulo 9, donde se caracteriza empíricamente el
gap sim-to-real. La cadena de trazabilidad
SR → C → escenario → métrica → veredicto verificada por
`tools/check_traceability.py` es la columna vertebral de la matriz
que se presenta en §4.8; los SyR son una capa documental adicional
que se revisa manualmente en el gate G1 (cf. §4.8.1).

---

## 4.3 Dominio Operacional (ODD)  [BORRADOR D11]

### 4.3.1 Especificación autónoma y resumen en este capítulo

El dominio operacional se formaliza como artefacto autónomo en
`docs/08_odd_specification.md`, versionado, parametrizado por
identificadores estables del tipo `ODD-N.<PARAM>`, y citado desde la
SRS y la Cage Specification mediante esos identificadores. Esta
separación entre artefacto autónomo y resumen capitular tiene una
finalidad doble. Por un lado, evita la duplicación de números entre
documentos, que es la fuente más común de inconsistencias en
especificaciones de seguridad: cada parámetro vive en un único sitio y
los demás documentos lo citan. Por otro lado, permite que la
especificación del ODD evolucione sin necesidad de reabrir el capítulo
de la tesis cada vez que se ajusta un valor durante la maduración del
artefacto (por ejemplo, el coeficiente de fricción de la superficie
simulada o el radio mínimo de curvatura del mapa curvy_loop).

El presente capítulo resume las decisiones estructurales del ODD y
remite al artefacto autónomo para los valores numéricos exhaustivos. La
auditoría del estado de redacción del ODD en D11 quedó documentada en
el cuaderno de trabajo de Fase 1 y motivó las TBD-Q1 a TBD-Q12 que
restan por cerrar.

### 4.3.2 Estructura de cuatro dominios operacionales

La tesis adopta una formulación estratificada en cuatro dominios
operacionales que aíslan ejes metodológicamente significativos de
variación. ODD-1 es el dominio nominal de carril recto; ODD-2 añade
estresores adversos sobre la misma geometría recta; ODD-3 introduce
geometría curva en lazo cerrado bajo condiciones nominales; ODD-4
combina geometría curva con condiciones adversas. La diferenciación
diádica resultante es la siguiente: ODD-1 frente a ODD-2 aísla el efecto
de los estresores adversos sobre carril recto; ODD-1 frente a ODD-3
aísla el efecto de la complejidad geométrica bajo condiciones nominales;
ODD-3 frente a ODD-4 aísla el efecto de los estresores adversos sobre
geometría curva. Esta estratificación es la condición que permite, en
el Capítulo 8, atribuir cambios observados en el rendimiento o en la
seguridad a un eje específico de complejidad en lugar de a una
combinación confundida.

La formulación se construye sobre la taxonomía jerárquica de PAS 1883
(BSI 2020) e ISO 34503 (ISO 2023), expresada con la disciplina semántica
de ASAM OpenODD (ASAM 2021). Cada ODD se describe en cinco pasos: función
pretendida y supuestos sobre el vehículo subjetivo; scenery, comprendiendo
tipo y geometría del área transitable, especificación del carril,
características de bordes y superficie, y presencia de estructuras;
condiciones ambientales, comprendiendo iluminación, climatología,
particulado y conectividad; elementos dinámicos, comprendiendo otros
actores y sus estados permitidos; envelope dinámico del vehículo subjetivo
e interfaces de sensores y actuadores. Cada dominio cierra con
exclusiones explícitas y suposiciones de salida del ODD.

### 4.3.3 Distinción entre atributos del ODD y estresores de escenario

La tesis preserva una distinción metodológica entre *atributos del ODD*
y *estresores de escenario* que merece comentario explícito porque
condiciona la lectura de los Capítulos 7 y 8. Los atributos del ODD son
las propiedades del entorno operativo que están definidas a priori por
la especificación del dominio: ancho de carril, geometría de la calzada,
condiciones lumínicas nominales, ausencia o presencia de actores
dinámicos. Los estresores de escenario son perturbaciones controladas
introducidas durante la evaluación: ruido en la observación, latencia en
el control, jitter, presencia de obstáculos estáticos, degradación de
las marcas viales. ODD-2 y ODD-4 se describen formalmente como ODD-1 y
ODD-3 respectivamente más una colección de perfiles de escenario con
nombre, no como dominios operacionales independientes con perturbaciones
internas.

Esta distinción tiene tres consecuencias prácticas. Primera: los
parámetros de los estresores se documentan en el ODD-Spec dentro de las
secciones de perfiles de escenario con nombre, no dispersos en el
capítulo de implementación. Segunda: los Safety Requirements pueden
referirse a los perfiles por nombre cuando un requisito acota el
comportamiento bajo un estresor concreto (por ejemplo, SR-007 sobre
validez del estado bajo `odd2_adverse_with_latency`). Tercera: la
generación de escenarios para la Fase 4 se construye combinatoriamente
sobre estos perfiles, con cardinalidad acotada y trazable al ODD.

### 4.3.4 ODD físico para despliegue en F5

La especificación del dominio físico, denotada provisionalmente
ODD-PHYS-1, se difiere a la Fase 5 para integrar las propiedades
medidas del CobraFlex 1:14 que solo se conocerán cuando el vehículo
esté instrumentado. ODD-PHYS-1 se concibe como el análogo realizable
en hardware de ODD-1, compartiendo tipo de scenery, exclusiones y
suposiciones de salida, y diferenciándose en envelope dinámico,
interfaces de sensores y actuadores, y latencia nominal de control.
Los hazards y Safety Requirements del presente capítulo se redactan
de forma suficientemente abstracta para aplicar tanto al ODD simulado
como al ODD físico, con valores numéricos de parámetros que pueden
reajustarse para ODD-PHYS-1 cuando se midan; cualquier reajuste
quedará registrado en el change log del documento afectado.

---

## 4.4 Análisis HARA: identificación sistemática de hazards  [BORRADOR D11 + COMPLETAR FASE 1 / D13]

### 4.4.1 Procedimiento HARA adoptado

El análisis HARA aplicado en este trabajo es una versión simplificada
del procedimiento canónico de ISO 26262 Parte 3, ajustada al alcance de
una tesis de máster. La simplificación afecta a la cuantificación de
exposición y controlabilidad —que se mantiene cualitativa en lugar de
basada en kilómetros recorridos por flota como en automoción de serie—
y a la asignación de ASIL —que se sustituye por niveles de criticidad
SR-CL-A/B/C derivados en §4.7—, pero preserva la estructura sistemática
del método: identificación de funciones, derivación de fallos potenciales
de cada función, asignación de severidad, exposición y controlabilidad,
y consolidación en hazards de nivel sistema.

El procedimiento se descompone en cinco pasos. El primer paso enumera
las funciones del sistema en relación con la función pretendida; en este
caso, las funciones son percepción del estado relativo al carril, decisión
de la acción de control, actuación de la acción sobre el vehículo, y
monitorización runtime de la acción decidida. El segundo paso deriva,
para cada función, los modos de fallo plausibles mediante una técnica
combinada de FMEA cualitativa y revisión de literatura sobre fallos
recurrentes en sistemas RL para conducción autónoma (Wäschle et al.,
2022; Wang et al., 2024; Wei et al., 2026). El tercer paso consolida los
modos de fallo en hazards de nivel sistema, donde un hazard se entiende
como una *condición potencialmente peligrosa observable a nivel del
sistema* en lugar de un fallo de un componente específico. El cuarto paso
asigna a cada hazard severidad (S), exposición (E) y controlabilidad (C)
según rúbricas cualitativas declaradas en §4.4.2. El quinto paso documenta
para cada hazard un consequence operacional concreto y una hipótesis de
causa raíz que sirve de puente hacia la derivación de Safety Requirements
en §4.6.

La distinción entre fallo de componente y hazard de sistema es
metodológicamente importante y conviene anclarla. Un agente RL puede
producir una acción incorrecta (fallo de componente: la policy emite un
steering inadecuado), pero el hazard relevante a nivel sistema no es la
acción incorrecta en sí sino la condición que esa acción puede generar
(salida del carril). El HARA opera sobre hazards de sistema porque los
Safety Requirements se redactan sobre propiedades observables de sistema,
no sobre estados internos de componentes; esto es lo que permite que la
cage runtime, que opera sobre interfaces de sistema, los pueda hacer
cumplir sin necesidad de inspeccionar el interior de la policy. Esta
elección está alineada con el espíritu de ISO/IEC TR 5469:2024, que
trata el componente AI como una caja cuyo comportamiento debe acotarse
desde la envoltura del sistema.

### 4.4.2 Rúbricas para severidad, exposición y controlabilidad

Las rúbricas adoptadas en este trabajo se documentan a continuación
para hacer reproducible el rating de cada hazard y son las mismas que
versiona el Hazard Register en `docs/02_hazard_register.md`. La
severidad sigue la escala de tres niveles de ISO 26262 reinterpretada
para el contexto escalado del CobraFlex 1:14: S1 para desviación
controlada con daño potencial menor (analogía: rasguños), S2 para
salida del carril con daño potencial moderado y recuperable (analogía:
daño mecánico apreciable), S3 para colisión o salida del corredor
transitable con daño potencial mayor o pérdida total de integridad de
la plataforma. La exposición sigue la escala de cuatro niveles de la
norma referida a la fracción del tiempo operativo dentro del ODD
aplicable: E1 para condición muy rara (<1 %), E2 para condición
ocasional (1–10 %), E3 para condición frecuente (10–50 %), E4 para
condición habitual (>50 %). La controlabilidad sigue la escala de
tres niveles de la norma referida a la capacidad de un mecanismo
runtime arquitecturalmente independiente de la policy para evitar el
consecuente: C1 para alta controlabilidad —el hazard es prevenible
mediante regla determinista en >99 % de los casos—, C2 para
controlabilidad moderada —el hazard se previene en >90 % mediante
lógica de runtime más elaborada—, C3 para baja controlabilidad —el
hazard solo se mitiga parcialmente desde runtime y exige también
intervención en diseño o entrenamiento—. La derivación del nivel de
criticidad cualitativo (Low, Medium, Medium-High, High) a partir del
trío S/E/C se realiza por agregación cualitativa documentada en el
Hazard Register, sin emisión de ASIL formal (cf. §3.8.7 del
Capítulo 3).

La interpretación física de cada nivel S/E/C en el contexto del CobraFlex
1:14 se hace por homotecia con la interpretación automotriz canónica:
una colisión a la velocidad máxima del 1:14 (0.5 m/s) no produce daño
físico relevante en hardware, pero el rating S se asigna *como si* el
vehículo fuera de tamaño real, porque el HARA está al servicio de la
metodología y no del producto. Esta convención queda registrada como
decisión D-03 y se discute en §4.9 como una de las limitaciones del
análisis.

### 4.4.3 Hazard Register

<!--
TEACHER NOTE: La tabla siguiente es la materialización del Hazard Register
de F1. En D11 el contenido viene del primer pase del draft V3. En D12-D13
se hace la auditoría de calidad (cada hazard ¿es de verdad un peligro o
un fallo?, ¿el rating S/E/C tiene justificación escrita?, ¿las causas
raíz están bien hipotetizadas?) y se actualiza la tabla. El cierre formal
es D13 PM con la SRS que se deriva en D14.
-->

El Hazard Register consolida siete hazards de nivel sistema identificados
mediante el procedimiento de §4.4.1. La numeración es estable: una vez
asignado un identificador H-XX, no se reutiliza ni se renombra incluso si
el hazard se descarta en revisiones posteriores. La tabla siguiente
presenta el registro en su forma compacta; la versión extendida con
rationale completo, hipótesis de causa raíz y referencias cruzadas vive
como artefacto autónomo en `docs/02_hazard_register.md`.

| ID    | Hazard (descripción)                                                                                              | S  | E  | C  | Criticidad   | ODDs aplicables | Consecuente operacional principal                                  | Hipótesis de causa raíz dominante                                |
|-------|--------------------------------------------------------------------------------------------------------------------|----|----|----|---------------|------------------|---------------------------------------------------------------------|------------------------------------------------------------------|
| H-01  | Salida lateral involuntaria del carril durante operación nominal o adversa.                                         | S3 | E3 | C2 | High          | 1, 2, 3, 4       | Contacto con borde de pista o salida del corredor transitable.       | Acción de control incorrecta en presencia de error lateral elevado. |
| H-02  | Error de orientación divergente u oscilatorio respecto a la trayectoria del carril.                                  | S2 | E3 | C2 | Medium-High   | 1, 2, 3, 4       | Trayectoria oscilante o pérdida progresiva de centrado.              | Acción correctiva insuficiente u oscilante en heading error.       |
| H-03  | Velocidad longitudinal excesiva para la curvatura o visibilidad locales.                                            | S2 (S3 en curva)| E2 | C1 | Medium        | 3, 4             | Insuficiente distancia de frenado; salida tangencial en curva.        | Reward que prioriza progreso sin penalización por curvatura.       |
| H-04  | Estado compuesto irrecuperable (heading + offset + velocidad simultáneamente elevados).                              | S3 | E1 | C3 | High          | 1, 2, 3, 4       | Salida del carril de alta energía; pérdida de pose funcional.         | Perturbaciones acumuladas no vistas en entrenamiento.              |
| H-05  | Comando de actuación excesivamente abrupto entre dos ciclos de control consecutivos.                                | S2 | E3 | C1 | Medium        | 1, 2, 3, 4       | Inestabilidad mecánica; ruido propagado a la estimación del estado.   | Ausencia de regularización del action delta durante entrenamiento. |
| H-06  | Operación sobre estado no observable o corrupto (latencia excesiva, datos obsoletos, ruido fuera de rango).         | S3 | E1–E2 | C2 | High        | 2, 4             | Decisión basada en información inválida; pérdida de coherencia.       | Mensaje ROS2 perdido, sensor en fallo, desincronización temporal.  |
| H-07  | Imposibilidad de realizar una parada controlada cuando las condiciones la requieren.                                | S3 | E1 | C1 | High          | 1, 2, 3, 4       | Continuación de movimiento sin base de control; impacto al final.     | Ausencia de mecanismo de stop; policy no entrenada para frenar.    |

`[COMPLETAR FASE 1 / D13]` La tabla anterior es la versión compacta del
Hazard Register consolidado en `docs/02_hazard_register.md`. Las
entradas siguen literalmente el contenido y los ratings del registro
canónico tras la auditoría D12–D13. El rationale extendido por
hazard —incluyendo ejemplos concretos de modos de fallo de la
literatura (Wang et al., 2024; Wäschle et al., 2022; Wei et al.,
2026), referencias cruzadas a los SRs que lo cubren y los hallazgos
STPA-light cuando aplica— vive en el artefacto autónomo. Cualquier
modificación al registro debe propagarse a esta tabla en el mismo
commit para que `tools/check_traceability.py` mantenga consistencia.

### 4.4.4 Cobertura de los hazards respecto al espacio del problema

`[COMPLETAR FASE 1 / D13]` Esta subsección argumenta de manera
estructurada que los siete hazards identificados constituyen una
*cobertura razonable* del espacio de hazards relevante para la función
pretendida acotada en §4.2.1. La argumentación se construye en tres
ejes: cobertura por función del sistema (cada función de §4.4.1 tiene
al menos un hazard asociado), cobertura por interfaz observable (cada
variable observable a nivel sistema participa en al menos un hazard
como consecuente o como condición), y cobertura por axioma de
literatura (los hazards recurrentes en revisiones recientes —Wang et
al., 2024; Wäschle et al., 2022; Paterson et al., 2025— están
representados o explícitamente excluidos por scope). La completitud no
se argumenta en sentido absoluto, lo cual sería incompatible con el
estado del arte, sino en sentido *relativo al alcance de la tesis y a
la literatura disponible*. Las exclusiones explícitas —por ejemplo,
hazards relacionados con interacción dinámica, hazards de
ciberseguridad, hazards relacionados con el comportamiento de la red
neuronal por ataque adversarial— se documentan en §4.9.

---

## 4.5 STPA ligera como complemento sistémico  [BORRADOR D11 + COMPLETAR FASE 1 / D13]

### 4.5.1 Motivación del complemento

El HARA descrito en §4.4 es un análisis bottom-up: parte de los modos
de fallo de cada función del sistema y los consolida en hazards de
nivel sistema. Esta orientación es eficaz para identificar hazards
asociados a fallos de componente —una policy que emite una acción
incorrecta, un sensor que entrega un valor obsoleto, un actuador que
sobre-responde— pero tiende a infravalorar los hazards que emergen de
la interacción entre componentes correctamente funcionando. La
literatura de safety systems thinking, articulada principalmente por
Leveson y desarrollada en el procedimiento STPA (Systems-Theoretic
Process Analysis, Leveson y Thomas 2018), argumenta que en sistemas
complejos los accidentes derivan con frecuencia no de fallos de
componente sino de control inadecuado a nivel sistema.

Aplicar la STPA en su forma plena al alcance de esta tesis sería
desproporcionado. Sin embargo, omitirla del todo dejaría sin cobertura
estructurada los hazards de tipo *unsafe control action* (UCA) en los
que un componente operando dentro de su especificación produce un
efecto sistémico inseguro. La tesis adopta por ello una *STPA ligera*:
una pasada selectiva que aplica las cuatro categorías canónicas de UCA
—acción de control no provista cuando se requiere; acción provista
cuando se prohíbe; acción provista demasiado pronto, demasiado tarde,
en orden incorrecto, o durante demasiado tiempo; acción detenida o
modificada inadecuadamente— sobre los hazards en los que la
perspectiva de control inseguro añade información operacional que el
HARA puro, centrado en consecuencias, no captura. La pasada se aplica
selectivamente a H-01 (salida lateral involuntaria), H-02
(desalineación angular divergente) y H-04 (estado compuesto
irrecuperable), criterio que coincide con el "STPA scope statement"
declarado en `docs/02_hazard_register.md`. Los hazards H-03, H-05,
H-06 y H-07 no se analizan con STPA por tener una estructura causal
suficientemente localizada (techo de velocidad, rate limiter,
validación de estado y mecanismo de stop respectivamente) como para
que la perspectiva sistémica no produzca insight adicional accionable.

### 4.5.2 Resultados de la STPA ligera sobre H-01, H-02, H-04

`[COMPLETAR FASE 1 / D13]` Esta subsección presenta, para cada uno de los
tres hazards seleccionados, las cuatro UCAs identificadas y discute para
cada UCA si genera nuevos requisitos de seguridad —que se incorporarían
a la SRS de §4.6 con identificadores SR-XXX— o si queda subsumida por
los SRs ya derivados del HARA. Se anticipa que la STPA ligera no
generará hazards completamente nuevos sino que producirá refinamientos
de los SRs derivados del HARA (típicamente: condiciones temporales sobre
la actuación, condiciones de orden entre comandos, condiciones de
persistencia mínima de la acción). El detalle vive como subsección de
`docs/02_hazard_register.md` bajo la cabecera "STPA-light pass" y se
cierra en D13 PM.

### 4.5.3 Limitaciones de la pasada ligera

`[COMPLETAR FASE 1 / D13]` Una pasada STPA ligera no es una STPA
completa. La diferencia principal es que la STPA completa construye un
modelo de control jerárquico explícito y deriva los UCAs por inspección
sistemática del modelo, mientras que la pasada ligera aplica la
plantilla de cuatro UCAs por inspección dirigida. La consecuencia es
que la pasada ligera puede pasar por alto UCAs derivados de
interacciones no anticipadas en la inspección dirigida. La tesis asume
este coste y lo registra como decisión D-04; una STPA completa quedaría
como trabajo futuro en el Capítulo 12.

---

## 4.6 Derivación de Safety Requirements  [BORRADOR D11 + COMPLETAR FASE 1 / D14-D16]

### 4.6.1 Procedimiento de derivación

La derivación de Safety Requirements desde el Hazard Register sigue un
procedimiento estructurado en cuatro pasos que está alineado con la
guía de derivación de safety requirements de ISO 26262 Parte 4 e
ISO/IEC TR 5469:2024. El primer paso, dado un hazard H-XX, formula
una propiedad observable de sistema cuya violación implicaría la
materialización del hazard; esta propiedad se redacta en lenguaje
operacional con un parámetro acotado y una condición de validez
(típicamente: durante operación dentro del ODD aplicable). El segundo
paso fija el parámetro en un valor numérico justificado por las
propiedades físicas del ODD (citadas mediante identificadores
`ODD-N.<PARAM>`) y no por las propiedades observadas de la policy
entrenada. Este principio es crítico para la independencia de la
verificación: si los SRs se ajustaran al rendimiento de la policy, la
verificación se volvería tautológica. El tercer paso redacta el SR en
forma falsable, esto es, en una forma tal que sea verificable mediante
un experimento finito que pueda devolver resultado positivo o negativo
sin ambigüedad. El cuarto paso asigna el SR a uno o más hazards
mediante la matriz de trazabilidad, y a una o más cage rules y
escenarios de verificación que se desarrollan en los Capítulos 5 y 6.

La distinción entre *requirement de seguridad* y *requirement de
rendimiento* se mantiene de forma estricta. Un requirement de seguridad
acota propiedades cuya violación produce un hazard con S ≥ S2; un
requirement de rendimiento acota propiedades cuya violación degrada el
servicio sin entrar en condición peligrosa. La SRS contiene
exclusivamente Safety Requirements; los requirements de rendimiento se
articulan en el Capítulo 7 como objetivos de entrenamiento y en el
Capítulo 8 como criterios de evaluación, pero no participan en la matriz
de trazabilidad de seguridad ni se vinculan a cage rules.

### 4.6.2 Falsabilidad como criterio de calidad

El criterio de falsabilidad merece desarrollo porque es donde se
concentran la mayoría de los errores de redacción que comprometen un
HARA en revisiones por terceros. Un SR que dice "el sistema operará de
manera segura" no es falsable: no hay experimento finito que pueda
producir un resultado negativo sin ambigüedad. Un SR que dice "el
módulo de error lateral mantendrá `|d_lateral| ≤ ODD-1.LANE_EDGE − Δ`
durante toda operación dentro de ODD-1, donde Δ = 0.04 m" sí es
falsable: bastan condiciones de simulación con logging del error
lateral para que el experimento devuelva un resultado conclusivo.

Cada SR de este capítulo se redacta para satisfacer cuatro condiciones
mínimas de falsabilidad: (i) la propiedad acotada es observable, en el
sentido de que existe al menos una variable medida del sistema que
permite evaluar la propiedad; (ii) el umbral está fijado a un valor
numérico concreto, no a un calificador cualitativo; (iii) la condición
de validez está acotada espacial o temporalmente —típicamente al ODD
aplicable— de modo que el SR no haga afirmaciones sobre regiones del
espacio operacional que no le corresponden; (iv) el SR identifica al
menos un escenario de verificación y al menos una métrica que
materializan la prueba. La cuarta condición vincula la falsabilidad a
la matriz de trazabilidad: un SR que no apunta a un escenario y a una
métrica no es verificable y, por tanto, no es falsable en el sentido
operativo de la tesis.

### 4.6.3 Safety Requirements Specification

<!--
TEACHER NOTE: La tabla siguiente es la materialización de la SRS de F1.
Las propiedades acotadas en cada SR vienen del primer pase del draft V3
y son razonables. Lo que falta cerrar es el rationale numérico para los
SRs cuyo umbral aún no está justificado por ODD-physics, y la asignación
final de criticidad. El cierre formal es D16 PM antes de que arranque la
construcción de la matriz en D17.
-->

La SRS consolida ocho Safety Requirements derivados del Hazard Register
y refinados por la pasada STPA ligera. La numeración es estable: una vez
asignado SR-XXX, no se reutiliza ni se renombra. La tabla siguiente
presenta la SRS en su forma compacta; la versión extendida con
rationale completo, parámetros, hazards cubiertos, cage rule
implementadora, escenarios de verificación, métricas y criterios de
satisfacción vive como artefacto autónomo en
`docs/03_safety_requirements.md`. El requisito a nivel de sistema
SyR-004 sobre logging auditable no genera un SR numerado por sí mismo:
se satisface por el output `/cage_status` y por los intervention logs
especificados en la Cage Specification (Cap. 5) y referenciados desde
todos los SRs de esta tabla mediante la columna de Verificación.

| ID     | Enunciado abreviado                                                                                                                                 | Parámetros principales                                  | H cubiertos          | Cage rule           | Criticidad | Verificación                            |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|------------------------|----------------------|--------------|------------------------------------------|
| SR-001 | El offset lateral absoluto respecto al centro de la calzada se mantendrá por debajo de `d_max` durante operación dentro del ODD aplicable.            | `d_max = 0.16 m`                                         | H-01                   | C-01                 | SR-CL-A      | SC-NOM-01, SC-NOM-02, SC-EDGE-02         |
| SR-002 | El error de orientación absoluto respecto a la dirección del carril se mantendrá por debajo de `θ_max`.                                              | `θ_max = 0.44 rad (25°)`                                 | H-02                   | C-02                 | SR-CL-A      | SC-EDGE-01, SC-EDGE-04                   |
| SR-003 | El tiempo a salida de carril proyectado (TTLC) se mantendrá por encima de `t_min`; el percentil 5 de TTLC sobre runs nominales será ≥ 0.5 s.         | `t_min = 1.0 s`; floor p5 = 0.5 s                        | H-01, H-02 (parcial)   | C-03                 | SR-CL-A      | SC-NOM-02, SC-EDGE-01                    |
| SR-004 | La velocidad longitudinal no excederá `v_max(κ)`, techo dependiente de la curvatura local κ.                                                         | `v_max_straight = 0.5 m/s`; `v_max_curve = 0.25 m/s`     | H-03                   | C-04                 | SR-CL-A      | SC-NOM-02, SC-EDGE-03                    |
| SR-005 | Bajo trigger compuesto sobre heading y offset durante `Δt_max`, el sistema transitará a modo emergencia con desaceleración mínima y steering frozen. | `θ_warn = 20°`; `d_warn = 0.12 m`; `Δt_max = 0.2 s`      | H-04, H-07 (parcial)   | C-05                 | SR-CL-A      | SC-EDGE-04                                |
| SR-006 | La variación de comando entre dos ciclos consecutivos se mantendrá por debajo de `δ_max` para steering y throttle.                                   | `δ_max_steer = 0.15`; `δ_max_thr = 0.10` (por ciclo)    | H-05                   | C-06                 | SR-CL-B      | Todos los escenarios (rate limiter activo) |
| SR-007 | La cage activará modo emergencia si la observación tiene antigüedad mayor a `staleness_max` o cualquier campo fuera de rango plausible.              | `staleness_max = 200 ms`; `N_missing_max = 5 ciclos`     | H-06                   | parte de C-05        | SR-CL-A      | SC-PERT-02                                |
| SR-008 | Bajo señal externa de stop o cierre controlado de episodio, el sistema desacelerará a 0 m/s en `t_stop_max` sin exceder `d_max` lateral.             | `t_stop_max = 1.5 s`; `d_max = 0.16 m`                   | H-07                   | parte de C-05 + nodo vehicle-control | SR-CL-A      | SC-NOM-03, SC-EDGE-04                    |

`[COMPLETAR FASE 1 / D14-D16]` Los valores presentes en la tabla son los
fijados en `docs/03_safety_requirements.md` tras el cierre de D14–D15;
los umbrales que todavía dependen de los TBD-Q1 a TBD-Q12 del ODD-Spec
quedan marcados explícitamente en el artefacto autónomo. La columna
"Cage rule" referencia los identificadores de la Cage Specification del
Capítulo 5 (`docs/04_cage_specification.md`). La columna "Verificación"
lista los identificadores de escenarios definidos en la Scenario Library
de F4 (`docs/05_scenario_library.md`), siguiendo el formato
`SC-<CAT>-<NN>` declarado en `docs/01_id_conventions.md`.

### 4.6.4 Rationale por Safety Requirement

`[COMPLETAR FASE 1 / D14-D16]` El rationale completo para cada SR
—incluyendo justificación física del umbral citando los parámetros del
ODD, descripción de la forma falsable, identificación del experimento
de verificación, y referencia cruzada al hazard del que deriva— vive
en `docs/03_safety_requirements.md` y se cierra en D16 PM.
A modo de ilustración del nivel de detalle exigido, esta subsección
presenta el rationale completo de SR-001 como ejemplo representativo,
mientras que el resto se referencia.

`[BORRADOR D11]` El rationale de SR-001 es el siguiente. El parámetro
`d_max = 0.16 m` no se elige en función del rendimiento de la policy
sino del envelope geométrico del ODD: la calzada tiene anchura total
`ODD-1.ROAD_WIDTH = 0.50 m`, lo que sitúa el borde físico del corredor
transitable a `0.25 m` del eje longitudinal de la pista. Un margen de
seguridad agregado de `Δ = 0.09 m` absorbe tres contribuciones
independientes: el ruido lateral del estimador de estado
(`≈ 0.01 m`), la deriva máxima esperable por latencia de control
nominal (`v_max · LATENCY_NOMINAL = 0.5 m/s · 50 ms = 0.025 m`), y la
mitad de la huella física lateral del CobraFlex 1:14 (`≈ 0.05 m`). El
umbral falsable queda entonces en `d_max = ROAD_WIDTH/2 − Δ = 0.25 − 0.09 = 0.16 m`,
interpretado como el módulo del offset lateral del centro geométrico
del vehículo respecto al eje del corredor transitable. Esta convención
de signo y unidad queda fijada en el enunciado de SR-001 en
`docs/03_safety_requirements.md` y se cita por los SRs derivados
(SR-005 sobre `d_warning = 0.12 m < d_max` como umbral de aviso
temprano, SR-008 sobre permanencia bajo `d_max` durante la parada
controlada).

---

## 4.7 Niveles de criticidad y completitud  [BORRADOR D11 + COMPLETAR FASE 1 / D16]

### 4.7.1 Asignación de criticidad

La asignación de criticidad sustituye al ASIL canónico de ISO 26262 por
una rúbrica de tres niveles SR-CL-A, SR-CL-B, SR-CL-C, derivada de la
combinación S/E/C del hazard del que deriva el SR según la matriz de la
Tabla 4.1. El nivel SR-CL-A reúne los SRs cuya violación produce un
hazard con S ≥ S3 o que cubren un hazard con E ≥ E3 y C ≤ C2; el
SR-CL-B reúne los SRs cuya violación produce un hazard con S = S2 o
con E moderada y C alta; el SR-CL-C reúne los SRs cuya violación
produce hazards con S = S1.

Las consecuencias prácticas de la asignación son tres y se documentan
aquí explícitamente para evitar ambigüedad. Primera: los SRs SR-CL-A
deben tener al menos una cage rule implementadora con regla
determinista —no condicional al estado interno de la policy— en el
rango C-01..C-06 de la Cage Specification; los SRs SR-CL-B pueden
tener implementación menos estricta (por ejemplo, monitorización con
flag en lugar de override de acción). Segunda: los SRs SR-CL-A deben
verificarse en al menos una familia de escenarios nominal y al menos
una de adverso, con un mínimo de veinticinco runs por familia para ser
estadísticamente discriminantes; los SRs SR-CL-B aceptan un mínimo de
diez runs. Tercera: los SRs SR-CL-A son obligatorios para emitir
veredicto positivo en la tabla del Capítulo 10; un SR-CL-A con
veredicto negativo invalida el veredicto global de la tesis sobre el
sistema. Estas convenciones quedan registradas como decisiones D-05,
D-06 y D-07.

### 4.7.2 Completitud y cierre del análisis

`[COMPLETAR FASE 1 / D16]` Esta subsección argumenta que la SRS
constituye una *cobertura completa* del Hazard Register en el sentido
operativo de F1: cada hazard tiene al menos un SR que cubre su
condición principal, y cada SR cubre al menos un hazard. La completitud
en sentido absoluto —garantizar que ningún hazard latente queda fuera
de la SRS— no se argumenta porque sería incompatible con el estado del
arte de la literatura para componentes RL; lo que se argumenta es
completitud relativa al Hazard Register cerrado en D13. El argumento se
materializa en la matriz de cobertura H↔SR de §4.8.2.

---

## 4.8 Matriz de trazabilidad bidireccional  [BORRADOR D11 + COMPLETAR FASE 1 / D17]

### 4.8.1 Función y forma de la matriz

La matriz de trazabilidad bidireccional es el artefacto que materializa
la adaptación A4 del V-Model adaptado (§3.4.4). Su función es doble.
Hacia adelante, traza cada SR a una o más cage rules, cada cage rule a
uno o más escenarios de verificación, cada escenario a una o más
métricas, y cada métrica a un veredicto —cadena `H↔SR↔C↔SC↔M`
declarada en §3.4.4 del Capítulo 3 y verificada por
`tools/check_traceability.py`—. Hacia atrás, permite, dada cualquier
evidencia experimental, recuperar el encadenamiento de artefactos que
justifica que esa evidencia es relevante para el cumplimiento de la
especificación de seguridad. La trazabilidad bidireccional es la
condición que hace que el cierre del V sea verificable: si cualquiera
de los dos sentidos contiene un huérfano —un artefacto sin
antecedente o sin consecuente— el cierre del V es incompleto y el
script lo señala como tal. Los requisitos de sistema SyR-001..SyR-005
se mantienen como capa documental por encima de los SRs y se documentan
con referencia a los SRs que los refinan en §4.2.2, pero no entran en
el conjunto de aristas verificadas automáticamente por el validador en
F1; su incorporación al script queda como extensión natural posterior.

La forma de la matriz en este capítulo se centra en la zona izquierda
de la rama izquierda: H ↔ SR. Las extensiones SR ↔ C ↔ SC ↔ M ↔ V se
describen estructuralmente aquí pero su materialización completa exige
las cage rules del Capítulo 5, los escenarios y métricas del Capítulo 7
y los veredictos del Capítulo 10.

### 4.8.2 Matriz de cobertura H ↔ SR

`[COMPLETAR FASE 1 / D17]` La tabla siguiente presenta la matriz de
cobertura entre Hazards y Safety Requirements en su forma binaria. Una
celda con marca indica que el SR de la columna cubre, en todo o en
parte, el hazard de la fila. Las marcas son consistentes con la columna
"H cubiertos" de la SRS en §4.6.3.

|        | SR-001 | SR-002 | SR-003 | SR-004 | SR-005 | SR-006 | SR-007 | SR-008 |
|--------|--------|--------|--------|--------|--------|--------|--------|--------|
| H-01   | ●      |        | ●      |        |        |        |        |        |
| H-02   |        | ●      | (●)    |        |        |        |        |        |
| H-03   |        |        |        | ●      |        |        |        |        |
| H-04   |        |        |        |        | ●      |        |        |        |
| H-05   |        |        |        |        |        | ●      |        |        |
| H-06   |        |        |        |        |        |        | ●      |        |
| H-07   |        |        |        |        | (●)    |        |        | ●      |

`[COMPLETAR FASE 1 / D17]` La marca `(●)` indica cobertura parcial:
SR-003 (TTLC predictivo) cubre H-02 de modo parcial en tanto el
indicador de tiempo a salida de carril es sensible a derivas
angulares pero no las cuantifica directamente; SR-005 (modo
emergencia compuesto) cubre H-07 de modo parcial porque su trigger
sobre estado compuesto puede iniciarse antes de que el operador
emita el comando externo de parada que invoca SR-008 propiamente.
Ambas coberturas parciales son consistentes con el campo "References
hazard" del SRS canónico y con la sección "Mitigated by" del Hazard
Register; el `tools/check_traceability.py` las admite siempre que
sigan declaradas en `docs/07_traceability_matrix.md`.

### 4.8.3 Verificación automatizada por `check_traceability.py`

`[COMPLETAR FASE 1 / D17]` La verificación de la matriz se realiza
mediante el script `tools/check_traceability.py`, cuya especificación
funcional se presenta a continuación. El script consume los artefactos
en formato Markdown (`docs/02_hazard_register.md`,
`docs/03_safety_requirements.md`) junto con los CSV compañeros
generados automáticamente por `tools/sync_hazard_register.py`
(`docs/data/hazard_register.csv` y `docs/data/safety_requirements.csv`),
y la matriz consolidada como `docs/07_traceability_matrix.md`. El
script parsea las relaciones declaradas y verifica cuatro condiciones: (a) cada hazard del Hazard Register
aparece en al menos una entrada de la matriz como antecedente; (b)
cada SR de la SRS aparece en al menos una entrada como consecuente; (c)
no existe SR cuya cobertura no esté justificada por algún hazard del
registro; (d) los identificadores referenciados son sintácticamente
válidos y existen. El script devuelve código de salida 0 si las cuatro
condiciones se satisfacen y código no nulo en caso contrario,
imprimiendo en stderr la lista de huérfanos y referencias inválidas.

El script se ejecuta como step de pre-commit en el repositorio del
proyecto a partir del cierre de F1, de modo que cualquier modificación
al Hazard Register o a la SRS que rompa la matriz se detecta antes de
ser persistida. La especificación funcional completa, los pseudocódigos
y los tests del script viven en el Capítulo 6 (§6.5.4).

### 4.8.4 Extensión hacia la derecha de la matriz

`[COMPLETAR FASE 4 / D45]` La extensión SR → C → SC → M → V se
materializa progresivamente conforme cierra cada artefacto: las cage
rules cierran en F2 (Capítulo 5), los escenarios y métricas en F4
(Capítulo 7), y los veredictos en F4-F5 (Capítulos 8 y 9). La matriz
extendida se presenta consolidada en el Capítulo 10 (§10.x). En el
presente capítulo se referencia su existencia y su forma esperada, pero
no se materializa.

---

## 4.9 Limitaciones del análisis  [BORRADOR D11]

El análisis presentado en este capítulo tiene cinco limitaciones
explícitas que conviene declarar honestamente antes del cierre.

La primera es la naturaleza cualitativa del rating S/E/C. La asignación
de severidad, exposición y controlabilidad se hace mediante rúbricas
discutidas en §4.4.2 y no mediante datos cuantitativos de exposición
real (kilómetros recorridos, frecuencias observadas). Esta limitación
es estructural en una tesis de máster con un caso de estudio único y
una plataforma a escala 1:14: no existe flota desplegada de la cual
extraer estadísticas de exposición. El análisis cuantitativo riguroso
queda como trabajo futuro, ligado a la posibilidad de instrumentación
de flotas reales o de datasets de validación a escala (Kootbally et
al., 2024).

La segunda es la convención de homotecia de severidad mencionada en
§4.4.2. El rating de severidad se asigna como si el vehículo fuera de
tamaño real, lo cual es una convención al servicio de la metodología
pero no se corresponde con la consecuencia física real de un
comportamiento inseguro del CobraFlex 1:14. El alineamiento entre
severidad metodológica y severidad física se restablecería en un
trabajo futuro sobre vehículo de tamaño real, donde los ratings
producirían las decisiones de criticidad que la convención actual
simula.

La tercera es la cobertura del HARA con respecto a hazards específicos
de componentes AI no contemplados. La revisión de Wang et al. (2024)
identifica al menos cinco familias de hazards específicos de
componentes AI no funcionales —ataques adversariales, distribución de
deriva (distribution shift), explicabilidad insuficiente, sesgos en el
dataset de entrenamiento, brittleness frente a perturbaciones de baja
magnitud— que no aparecen en el Hazard Register de §4.4.3 porque caen
fuera del alcance acotado de la tesis. La omisión es deliberada y se
registra como decisión D-08, pero limita la generalización del análisis
a sistemas RL de producción.

La cuarta es la naturaleza ligera de la pasada STPA. La pasada
selectiva descrita en §4.5 puede pasar por alto UCAs derivados de
interacciones no anticipadas en la inspección dirigida, según se
discute en §4.5.3.

La quinta es la dependencia de la verificación experimental respecto a
los escenarios de la Scenario Library del Capítulo 7. Un SR es
falsable solo en la medida en que existe un escenario que materialice
la falsación; un SR para el cual no se ha podido construir un escenario
ejecutable queda como falsable en principio pero no verificado en la
práctica. La cobertura de los SRs por escenarios se cierra en F4 y se
discute en el Capítulo 7 con los criterios de cobertura de De Gelder
et al. (2024).

---

## 4.10 Síntesis y transición al Capítulo 5  [BORRADOR D11]

El presente capítulo ha desarrollado los niveles L1 y L2 del V-Model
adaptado para el caso de estudio lane-following. La función pretendida
y los requisitos de sistema SyR-001 a SyR-005 quedaron fijados en §4.2.
El dominio operacional, formalizado en cuatro estratos ODD-1 a ODD-4
con un ODD físico ODD-PHYS-1 diferido a F5, quedó resumido en §4.3 con
remisión al artefacto autónomo. El Hazard Register, con siete hazards
H-01 a H-07 (salida lateral, desalineación angular, velocidad
excesiva, estado compuesto irrecuperable, actuación abrupta, estado
no observable, imposibilidad de parada controlada) derivados mediante
un procedimiento HARA simplificado y una pasada STPA ligera
complementaria sobre H-01, H-02 y H-04, quedó consolidado en §4.4 y
§4.5. La SRS, con ocho Safety Requirements SR-001 a SR-008
falsablemente redactados y asignados a niveles de criticidad SR-CL-A o
SR-CL-B, quedó consolidada en §4.6 y §4.7. La matriz de trazabilidad
bidireccional, en su versión H ↔ SR, quedó presentada en §4.8 con
remisión al script `tools/check_traceability.py` para su verificación
automatizada. Las limitaciones del análisis quedaron declaradas en §4.9.

Establecida la especificación de seguridad, el Capítulo 5 desciende al
nivel L3 con el diseño arquitectónico del sistema —descomposición en
nodos ROS2, interfaces explícitas, modos de operación— y al nivel L4a
con la primera versión cerrada de la Cage Specification, donde cada
una de las cage rules C-01 a C-06 referenciadas en la columna
correspondiente de la SRS se desarrolla con su lógica completa, sus
parámetros versionados y su trazabilidad explícita a los SRs que
implementa. El Capítulo 5 no añade nuevos hazards ni nuevos SRs: opera
estrictamente dentro del marco fijado en este capítulo y produce los
mecanismos runtime que harán cumplir esa especificación.

La trazabilidad bidireccional —que en este capítulo se materializa en
H ↔ SR— se extenderá en el Capítulo 5 hacia SR ↔ C, en el Capítulo 6
hacia C ↔ implementación, en el Capítulo 7 hacia SR ↔ escenario ↔
métrica, y en el Capítulo 10 hacia métrica ↔ veredicto. El cierre
completo del V se materializa así de forma incremental, con
verificación automatizada en cada cierre de fase mediante
`tools/check_traceability.py`.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

D11 (cierre):
  [x] Estructura de secciones 4.1–4.10
  [x] Redacción [BORRADOR D11] de 4.1, 4.2, 4.3, 4.4.1, 4.4.2, 4.6.1, 4.6.2, 4.7.1, 4.8.1, 4.9, 4.10
  [x] Esqueletos tabulares de 4.4.3 (Hazard Register) y 4.6.3 (SRS) con
       contenido provisional del primer pase del draft V3
  [x] Marcadores [COMPLETAR FASE 1 / Dxx] en todas las subsecciones
       que dependen de cierres posteriores

D12-D13 (operacionalización del Hazard Register y STPA ligera):
  [x] Auditoría de calidad de los siete hazards: rating S/E/C
       reconciliado contra docs/02_hazard_register.md tras la
       auditoría D11 que detectó el desfase de identificadores;
       tabla §4.4.3 alineada al registro canónico.
  [x] Producir docs/02_hazard_register.md (versión D11 ampliada
       en D12-D13)
  [ ] STPA ligera sobre H-01, H-02, H-04: tabla de UCAs y
       refinamientos generados
  [ ] Argumentación de cobertura del HARA en §4.4.4

D14-D16 (derivación y cierre de SRS):
  [ ] Cierre de TBDs residuales en parámetros del SRS
       (dependientes de TBD-Q1 a TBD-Q12 del ODD-Spec)
  [ ] Rationale completo por SR en docs/03_safety_requirements.md
  [ ] Asignación final de criticidad SR-CL-A/B/C por SR
  [ ] Argumentación de completitud relativa en §4.7.2

D17 (matriz de trazabilidad):
  [ ] Consolidación de docs/07_traceability_matrix.md y de los CSV
       compañeros generados por tools/sync_hazard_register.py
       (docs/data/hazard_register.csv, docs/data/safety_requirements.csv)
  [ ] Especificación funcional de tools/check_traceability.py
       (a desarrollar en §6.5.4)
  [ ] Verificación de no-huérfanos en H ↔ SR; resolución de
       cualquier huérfano detectado mediante ajuste del Hazard
       Register o de la SRS, registrado como decisión D-XX

D18 (revisión de calidad):
  [ ] Revisión cruzada de §4.4 a §4.8 contra los criterios de
       calidad declarados en §3.7 (criterios meta del marco)
  [ ] Verificación de coherencia con el Capítulo 3 (los
       enunciados sobre A1-A5 deben corresponderse con su
       formulación en §3.4)

D19-D20 (consolidación de cap. 4):
  [ ] Pulido de prosa y tránsito a tono académico definitivo
  [ ] Cierre de §4.10 con la transición exacta al Capítulo 5
  [ ] Inserción de figuras: Figura 4.1 (taxonomía PAS 1883
       reducida), Figura 4.2 (procedimiento HARA), Figura 4.3
       (procedimiento de derivación SR), Figura 4.4 (matriz de
       trazabilidad H ↔ SR como heatmap)

Fase 6 (consolidación final):
  [ ] [PULIDO FASE 6] Sustitución de placeholders SVG por figuras
       finales
  [ ] [PULIDO FASE 6] Verificación de coherencia con Capítulos
       5 a 10 (referencias cruzadas a IDs, métricas, números de
       capítulo)
  [ ] [PULIDO FASE 6] Revisión de §4.9 con los hallazgos reales
       del Capítulo 11 sobre la propia metodología
  [ ] [PULIDO FASE 6] Aplicación de formato bibliográfico
       definitivo a citas inline

REFERENCIAS USADAS EN ESTE CAPÍTULO (D11):

  Estándares y normativa:
  - ISO 26262:2018 (HARA, ASIL, lifecycle)
  - ISO 21448:2022 (SOTIF)
  - ISO/PAS 8800:2024 (ML safety)
  - ISO/IEC TR 5469:2024 (AI functional safety)
  - PAS 1883:2020 / BS ISO 34503:2023 (ODD specification)
  - ASAM OpenODD 1.0.0 (2021)

  Metodología de safety analysis:
  - Leveson y Thomas, 2018 (STPA Handbook)
  - Koopman, 2023 (UL 4600 / safety case)
  - Paterson et al., 2025 (AMLAS)

  Algoritmos y simulador (referencias arrastradas del Cap. 3):
  - Schulman et al., 2017 (PPO)
  - Koenig y Howard, 2004 (Gazebo — simulador adoptado, decisión D-02)
  - Kuutti et al., 2019b (Safety cages)

  Hazards específicos AI / lane-following:
  - Wang et al., 2024 (SOTIF para AVs)
  - Wäschle et al., 2022 (AI safety in HAD)
  - Wei et al., 2026 (criticality-aware robust RL)
  - Zhao et al., 2024 (RECPO)

  Cobertura y métricas:
  - De Gelder et al., 2024 (coverage metrics for scenario DBs)
  - Kootbally et al., 2024 (NIST IR 8527 — performance metrics)

REFERENCIAS A FIGURAS (placeholders explícitos):
  - Figura 4.1 (pendiente): figures/odd_taxonomy_reduced.svg —
       taxonomía PAS 1883 reducida a las dimensiones usadas
  - Figura 4.2 (pendiente): figures/hara_procedure.svg —
       diagrama de flujo del procedimiento HARA aplicado
  - Figura 4.3 (pendiente): figures/sr_derivation.svg —
       procedimiento de derivación SR desde hazards
  - Figura 4.4 (pendiente): figures/traceability_matrix_heatmap.svg —
       matriz H ↔ SR como heatmap con marcas de cobertura

DECISIONES REGISTRADAS EN ESTE CAPÍTULO:
  (Las decisiones D-01 anti-end-to-end y D-02 simulador Gazebo
  son propiedad del Capítulo 3 y se documentan en DECISIONS.md;
  el Capítulo 4 inicia su numeración en D-03.)
  - D-03: Convención de homotecia para severidad en plataforma 1:14
       (rating como si el vehículo fuera de tamaño real). §4.4.2
  - D-04: Adopción de STPA ligera selectiva en lugar de STPA
       completa, aplicada a H-01, H-02, H-04 conforme al STPA
       scope statement del Hazard Register. §4.5
  - D-05: SR-CL-A exige cage rule determinista en el rango
       C-01..C-06 de la Cage Specification. §4.7.1
  - D-06: SR-CL-A exige verificación con ≥25 runs por familia
       de escenarios. §4.7.1
  - D-07: SR-CL-A negativo invalida veredicto global. §4.7.1
  - D-08: Exclusión deliberada de hazards específicos AI no
       funcionales (adversariales, distribution shift,
       explicabilidad, sesgo, brittleness). §4.9
-->
