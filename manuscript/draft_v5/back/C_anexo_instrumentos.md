# Anexo C — Elecciones de instrumento y mapeo normativo

Este anexo desarrolla por completo §3.6 y §3.8. Cada elección se presenta con su justificación, las alternativas descartadas y el motivo por el que se descartaron, para que la decisión se pueda auditar y no quede solo enunciada.

# C.1 Instrumentos

Esta sección recoge las herramientas con las que el marco metodológico se aplica al caso de estudio. No se trata de hacer una lista de herramientas, sino de justificar cada elección frente a las alternativas descartadas y dejar un registro auditable de decisiones que de otro modo quedarían sin explicar. Todas las subsecciones siguen el mismo esquema: herramienta elegida, justificación y alternativas descartadas con su motivo.

## C.1.1 Simulador

**Elección: Gazebo** (Koenig y Howard, 2004), en su versión moderna con integración ROS2 nativa, usado a través de una interfaz gymnasium-Gazebo-ROS2 que reutiliza un entorno que el autor construyó en un trabajo de investigación anterior. Hay cuatro motivos, y conviene explicarlos con claridad, porque la elección se aparta de lo habitual en investigación de conducción autónoma, donde el simulador de referencia es CARLA.

Primero, *integración ROS2 nativa*. Open Robotics desarrolla Gazebo junto con ROS, y los dos comparten piezas básicas (tópicos, transformadas, herramientas de visualización) sin necesidad de capas de puente intermedias. Toda la arquitectura del proyecto descrita en el Capítulo 5 (percepción, policy, cage, actuación, logger) es ROS2 desde el principio. Tener el simulador en el mismo grafo elimina posibles puntos de fallo y deja más claro dónde se producen retardos o desincronizaciones, lo que influye directamente en la fiabilidad de las métricas de integración (M-I).

Segundo, *reutilizar el trabajo previo del autor*. El autor ya tenía un entorno Gazebo construido para una tarea parecida, con el vehículo a escala modelado y la pista controlada preparada. Reutilizarlo, en lugar de construirlo de nuevo en otra plataforma, deja más tiempo para la aportación metodológica (las adaptaciones A1–A5 y su puesta en práctica), que es el verdadero tema de la tesis. Esto encaja con el enfoque *design science* de §3.2.1: la aportación no está en el simulador sino en el marco, y la elección de herramienta debe reducir al mínimo el coste que no aporta nada.

Tercero, *interfaz gymnasium-Gazebo-ROS2 para el entrenamiento*. La interfaz que une el bucle de entrenamiento (Stable-Baselines3 sobre gymnasium) con el simulador (Gazebo, vía ROS2) existe como herramienta abierta y separa con claridad algoritmo, entorno y sistema. Esto facilita cumplir la adaptación A1 (Training Specification como meta-diseño): los hiperparámetros, la función de recompensa y el ODD de entrenamiento se definen en un módulo Python aparte, sin depender del simulador que hay debajo.

Cuarto, *menos necesidades de cómputo*. Gazebo funciona en hardware menos potente que CARLA. Esto importa en una tesis individual sin infraestructura de cómputo dedicada, y permite iterar más rápido mientras se desarrolla el Training Spec.

La elección tiene dos inconvenientes que hay que reconocer abiertamente. Por un lado, la calidad visual de Gazebo es menor que la del motor Unreal Engine que usa CARLA. Para una policy basada en una cámara monocular, esto puede dar un gap sim-to-real mayor que con un simulador fotorrealista. La adaptación A5 del marco (medición empírica del gap) está pensada precisamente para hacer visible este efecto y medirlo, no para ocultarlo (ver §3.9 y Capítulo 9). Por otro lado, la comunidad de conducción autónoma usa sobre todo CARLA, así que no hay bibliotecas de escenarios listas para usar en formato Gazebo. Por eso la biblioteca de escenarios del proyecto hay que construirla, algo que entra en el alcance del Capítulo 6.

Alternativas consideradas y descartadas. CARLA (Dosovitskiy et al., 2017) es la opción más fuerte y la elección por defecto en la investigación reciente de conducción autónoma. Ofrece mejor calidad de sensores y un ecosistema maduro de benchmarks, pero necesita un *bridge* ROS2 con sus propios problemas, y su mayor coste de cómputo es un freno práctico para una tesis individual. Highway-Env y otros entornos derivados de Gym no tienen sensores realistas y usan un espacio de observación abstracto, así que no sirven para políticas basadas en cámara. LGSVL es un proyecto abandonado en 2022, con un ecosistema que se está deshaciendo. **AirSim** está centrado en vehículos aéreos, con el soporte para coches en segundo plano, y su desarrollo está parado.

## C.1.2 Algoritmo de aprendizaje por refuerzo

**Elección: PPO**, *Proximal Policy Optimization* (Schulman et al., 2017). PPO se elige por cuatro motivos que encajan con el marco metodológico. Primero, *entrenamiento estable*: el *clipped surrogate objective* limita el tamaño de cada actualización de la política sin necesitar una restricción explícita de KL. Esto favorece un entrenamiento estable y la reproducibilidad, algo importante en un trabajo individual con poco cómputo para hacer *sweeps* completos. Segundo, *un Training Spec fácil de interpretar*: como es *on-policy*, sus hiperparámetros tienen un significado bastante directo (tamaño del rollout, épocas por actualización, ratio de clipping, coeficiente de entropía), lo que facilita escribir el Training Spec del nivel L4b como un documento legible. Tercero, *buen soporte en herramientas abiertas*: la implementación de Stable-Baselines3 es madura, muy usada y se integra directamente con Gazebo a través de la interfaz gymnasium-Gazebo-ROS2 de §3.6. Cuarto, *compatibilidad con extensiones*: si más adelante la tesis explorase *constrained RL* (como RECPO de Zhao et al., 2024), PPO se puede extender de forma natural a CMDP.

Alternativas consideradas y descartadas: SAC (Haarnoja et al., 2018) es competitivo en eficiencia de muestras y estable entre semillas, pero al ser *off-policy* hace que el Training Spec sea menos fácil de interpretar (la idea de "qué política produjo qué experiencia" se pierde en el *replay buffer*), y su naturaleza estocástica con *temperature tuning* complica el diseño del experimento. DDPG / TD3 (deterministas y *off-policy*) quedaron por detrás de SAC en las tareas más difíciles de los benchmarks de Haarnoja et al. (2018), donde además se describe DDPG como frágil frente a los hiperparámetros. A3C / A2C fueron menos eficientes en muestras que PPO en los benchmarks de Schulman et al. (2017).

## C.1.3 Bucle de aprendizaje y herramientas de implementación

- **Stable-Baselines3** como implementación de PPO. Motivo: estabilidad, comunidad, integración con *gym* / *gymnasium* y código auditable.
- **PyTorch** como backend de redes neuronales. Motivo: es el estándar en la investigación actual, se integra de forma nativa con Stable-Baselines3 y tiene herramientas de profiling maduras.
- **pytest** como framework de testing para los Cage Unit Tests (L4a' del V-Model adaptado) y para la suite de regresión general.
- **Python 3.10+** con herramientas de calidad: `ruff` (linting), `mypy` (type checking) y `pre-commit` para automatizar comprobaciones en cada commit.

## C.1.4 Plataforma física

Se elige el vehículo radiocontrolado a escala 1:14 frente a otras escalas por tres motivos. *Coste*: un 1:14 es fácil de manejar, las piezas son baratas y el riesgo de daños durante el uso es limitado. *Seguridad de operación*: velocidades bajas, poca energía cinética y un riesgo para terceros despreciable en una pista cerrada. *Transferibilidad desde la simulación*: la dinámica de un 1:14 se puede aproximar razonablemente en Gazebo con un modelo de vehículo basado en plugins y parámetros ajustables (masa, reparto de carga, fricción de los neumáticos, parámetros de actuación), mientras que escalas mayores (1:5, 1:1) añadirían diferencias dinámicas que dominarían el gap sim-to-real. Las especificaciones detalladas del coche (motor, ESC, controlador de bajo nivel, cámara, plataforma de cómputo embarcado) están en el Capítulo 5 y en el anexo correspondiente.

<img src="../figures/fig_3_5_vehicle_cad.png" alt="Figura 3.5 — Fotografía del vehículo RC 1:14 instrumentado con la cámara, IMU." width="300"/>

*Figura 3.5 — El vehículo RC 1:14 instrumentado con cámara, IMU, encoder y SBC, con cada componente etiquetado.*

## C.1.5 Instrumentación de medida

La herramienta principal para recoger evidencia es el Logger Node de la arquitectura ROS2, ya descrito en la adaptación A3 (§3.4.3). El Logger Node guarda todo lo relevante que pasa por el bus (observaciones, acciones de la *policy*, decisiones de la cage, intervenciones, estados del vehículo) con marcas de tiempo que permiten reconstruirlo después.

Las métricas concretas que se calculan a partir de los logs se definen formalmente en el Capítulo 4 y se agrupan en cinco familias: M-P (rendimiento: error de seguimiento, completitud de la trayectoria), M-S (seguridad: tasa de intervención de la cage, número de violaciones por SR), M-I (integración: latencias, jitter, throughput), M-C (comportamiento: estabilidad lateral, suavidad del control) y M-T (transferencia: diferencia entre simulación y realidad para cada métrica anterior, y métricas propias del gap de A5). El detalle está en el Capítulo 4.

Para una evaluación cuantitativa adicional sobre la *scenario library* se toma como inspiración la métrica compuesta QED (Gao et al., 2021), calibrada con evaluadores humanos para tareas de conducción autónoma. No se puede adoptar tal cual, porque QED se desarrolló y calibró sobre CARLA y esta tesis usa Gazebo. La fórmula se puede trasladar, pero los pesos calibrados habría que volver a calcularlos para el escenario de seguimiento de carril en Gazebo si se quiere una métrica con el mismo significado. *Behavior Metrics* (Paniego et al., 2024) se considera como herramienta auxiliar de evaluación cuantitativa, porque ya funciona con dos simuladores, CARLA y Gazebo. La decisión de adoptarla como métrica oficial del proyecto se aplaza a la Fase 4, cuando se tenga la *policy* entrenada y se pueda calibrar con el criterio humano del autor.

## C.1.6 Documentación, control de versiones y reproducibilidad

Todos los artefactos del proyecto (documentos, código, plantillas, matriz de trazabilidad, scripts de validación) están en un único repositorio Git, con una idea de base: el repositorio *es* el proyecto. Se elige a propósito trabajar *primero en texto plano*: los artefactos se escriben en Markdown con extensiones mínimas (citas con formato `[Apellido (año)]`, ecuaciones LaTeX, figuras SVG/PNG en una carpeta propia), y no en herramientas MBSE industriales como Cameo o Capella.

Esta elección se aparta de la propuesta MBSE de Sprockhoff et al. (2023) para sistemas con componentes de IA, que defiende SysML y herramientas estructuradas como eje del ciclo de vida. La diferencia está en el *coste de adopción*: para una tesis individual sin licencias industriales, los archivos de texto versionados salen más a cuenta, y cumplen la misma función en trazabilidad (con `traceability_matrix.csv` + `check_traceability.py`) y en coherencia (con revisión automática en cada commit). La decisión está en `DECISIONS.md` con su justificación y con la hipótesis de que, si el marco se aplicara en un equipo industrial mediano, sí tendría sentido pasar a MBSE.

---

# C.2 Relación con los estándares

El V-Model adaptado se apoya en el estado actual de las normas de seguridad para sistemas con IA. Esta sección sitúa cada adaptación dentro de ese panorama normativo y separa lo que es coherente con cada estándar de lo que va más allá. El repaso sigue el orden de publicación, que coincide más o menos con el orden en que la industria los fue adoptando.

## C.2.1 ISO 26262:2018 — Functional Safety for Road Vehicles

ISO 26262:2018 aplica el V-Model clásico a la automoción. La tesis lo toma como punto de partida y como marco cuya estructura general quiere respetar.

- **Coherente:** la estructura de cinco niveles L1–L5, la idea de safety requirement, el principio de relación en ambos sentidos entre especificación y V&V, y la obtención de requisitos a partir del HARA con asignación de niveles ASIL.
- **Va más allá:** ISO 26262 no contempla módulos aprendidos. Las adaptaciones A1, A2 y A3 son extensiones explícitas para incluir componentes RL sin romper la estructura general del estándar. La idea es un *tailoring* que solo suma: no se quita nada y se añade solo lo imprescindible.

## C.2.2 ISO 21448:2022 — SOTIF (Safety Of The Intended Functionality)

ISO 21448:2022 amplía la seguridad más allá de los fallos, incluido el uso de funciones en condiciones no previstas. Es la respuesta oficial al hecho de que un sistema con percepción y decisión basadas en ML puede comportarse mal sin que ningún componente haya "fallado" en el sentido clásico (Wang et al., 2024).

- **Coherente:** la adaptación A5 (validación operacional acotada y medición del gap sim-to-real) encaja directamente con la idea de SOTIF de que la validación estática no basta cuando el ODD no está especificado por completo. La adaptación A3 (runtime monitoring continuo) encaja con el principio de SOTIF de gestionar las *triggering conditions* que se descubren en operación.
- **Va más allá:** A3 propone el runtime monitoring como un nivel arquitectónico explícito del ciclo de vida, no solo como una práctica recomendada durante la operación.

## C.2.3 ISO/IEC TR 5469:2024 — AI Functional Safety

ISO/IEC TR 5469:2024 es hasta hoy el documento normativo más específico sobre el uso de IA en funciones de seguridad. Aporta tres cosas al marco propuesto: la clasificación de la tecnología IA por nivel de uso y por clase tecnológica (Clase I, II y III; cláusula 6), el *three-stage realization principle* (cláusula 7), y las propiedades y factores de riesgo de los sistemas con IA (cláusula 8: nivel de automatización y control, transparencia y explicabilidad, complejidad del entorno y especificaciones vagas, resiliencia ante entradas adversarias, hardware de IA y madurez de la tecnología).

- **Coherente:** la *policy* PPO de la tesis es como mucho un elemento de Clase II del TR 5469 (las normas de seguridad funcional existentes solo cubren parte de sus propiedades requeridas y hacen falta métodos complementarios), y la adaptación A2 (Policy Behavioral Evaluation estadística) es uno de esos métodos complementarios. La trazabilidad obligatoria en ambos sentidos (A4) no tiene un equivalente concreto entre las propiedades del TR; su anclaje normativo se explica en C.2.5 y C.2.6. La división Cage Spec / Training Spec (A1) lleva al proceso de diseño la distinción del *three-stage realization principle* entre adquisición de datos, inducción de conocimiento y procesamiento, que el propio TR no presenta como un ciclo de vida.
- **Va más allá:** separar explícitamente el Cage Spec (elemento convencional que, por analogía, corresponde a la Clase I) y el Training Spec (meta-diseño para un elemento de Clase II) en documentos versionados distintos es un refinamiento práctico del TR, que el documento normativo no llega a detallar con ese nivel de granularidad.

## C.2.4 ISO/PAS 8800:2024 — Road Vehicles, Safety and AI

ISO/PAS 8800:2024 es el documento automotriz sobre seguridad e IA, muy ligado a los conceptos generales del TR 5469. Extiende ISO 26262 e ISO 21448 a los elementos de IA: los riesgos de seguridad funcional se tratan adaptando (*tailoring*) las cláusulas aplicables de ISO 26262 (Partes 4, 6 y 8), y las insuficiencias funcionales, ampliando los conceptos de SOTIF. Un caso de uso de ejemplo publicado por BSI para el UK CCAV (Hawkins, 2025), sobre un detector ML de señales de tráfico con requisitos para las señales de stop, muestra cómo se combinan ISO 26262, SOTIF e ISO/PAS 8800 sobre un componente ML.

- **Coherente:** el *tailoring* que solo suma del V-Model adaptado coincide con el de ISO/PAS 8800. Las cinco adaptaciones A1–A5 se pueden alinear razonablemente con las áreas que el estándar señala como críticas (definición del operating environment, análisis sistemático de insuficiencias, monitoring después del despliegue).
- **Va más allá:** aplicar el marco a un caso completo, desde el HARA hasta el despliegue físico y con medición empírica del gap, es más concreto que los ejemplos publicados hasta ahora.

## C.2.5 UL 4600 — Standard for Safety for the Evaluation of Autonomous Products

UL 4600 (UL Standards, 2023; Koopman, 2023) pone el foco en el *safety case* y en la evidencia estructurada como forma principal de dar garantías sobre productos autónomos.

- **Coherente:** la Matriz de Trazabilidad H↔SR↔C↔SC↔M es un pequeño safety case en la línea de UL 4600: cada *claim* de seguridad se apoya en un argumento explícito (la regla de la cage, el escenario, la métrica) y en evidencia trazable (los logs, los resultados experimentales).
- **Va más allá:** A4 convierte la trazabilidad en una restricción dura que aplica una herramienta automática (`check_traceability.py`), en lugar de una buena práctica documental que alguien tiene que revisar.

## C.2.6 AMLAS — Assurance of Machine Learning for Autonomous Systems

AMLAS, consolidado por Paterson et al. (2025), no es un estándar formal sino una metodología con patrones GSN (*Goal Structuring Notation*) específicos para construir argumentos de seguridad sobre componentes ML. Se está incorporando como base a estándares nuevos, en particular a ISO/PAS 8800.

- **Coherente:** el enfoque claim-argument-evidence de AMLAS coincide con la trazabilidad en ambos sentidos de A4. El ciclo de vida centrado en los datos que plantea AMLAS (definición de requisitos, gestión de datos, aprendizaje, verificación, despliegue, monitorización) se parece a grandes rasgos a las fases del proyecto descritas en §3.5.3.
- **Va más allá:** AMLAS se ha probado sobre todo con modelos supervisados. El marco de esta tesis está pensado explícitamente para *policies* RL, un ámbito que AMLAS todavía cubre poco.

## C.2.7 HARA simplificado y su relación con la versión formal de la norma

La cláusula 6 de la Parte 3 de ISO 26262:2018 define el método HARA formal para *items* de automoción: análisis de situaciones, identificación sistemática de los hazards ligados a las funciones del item, clasificación de cada hazard en tres ejes (severidad S, escala S0–S3; exposición E, escala E0–E4; controlabilidad C, escala C0–C3) y obtención del *ASIL* (Automotive Safety Integrity Level, QM/A/B/C/D) con una tabla que combina S×E×C. El ASIL marca el nivel de rigor exigido en el resto del ciclo de vida, incluidas las medidas de diseño, las técnicas de verificación y la cobertura de tests.

La versión usada en esta tesis se llama explícitamente *HARA simplificado*, y así figura en la cabecera del Hazard Register. Hay tres diferencias con la norma formal, que se explican aquí con franqueza:

- **Se mantienen las escalas S/E/C, pero se reinterpretan para un vehículo a escala.** Las tres escalas conservan la granularidad de la norma (S1–S3, E1–E4, C1–C3), pero las definiciones de cada nivel se adaptan a un vehículo 1:14 en pista cerrada. S3 ya no significa "lesión mortal", sino "pérdida total de la integridad de la plataforma". E3 se define como "10–50% del tiempo operativo" dentro del ODD declarado (una banda propia de este proyecto: en las clases de exposición por duración de la norma, E3 corresponde al 1–10 % y E4 a más del 10 % del tiempo medio de operación). C2 mantiene el significado de "controlable en >90% de los casos", pero referido a la cage de reglas y no al conductor humano. Esta rúbrica adaptada se versiona junto con el registro y se puede auditar.

- **No se asigna un ASIL formal; en su lugar se usa una "Criticality" cualitativa.** El resultado del HARA simplificado es, para cada hazard, una etiqueta cualitativa de criticidad con cuatro niveles (Low, Medium, Medium-High, High), obtenida combinando cualitativamente S, E y C, y usada solo para priorizar el trabajo de mitigación. No se asigna una letra de ASIL porque el ASIL es una construcción legal y normativa pensada para la certificación industrial, no para la demostración metodológica que busca la tesis. Poner un "ASIL B" a un coche a escala daría una falsa sensación de precisión que el marco prefiere evitar. La criticidad cualitativa es honesta sobre lo que se mide y sobre para qué se usa. Por separado, los Safety Requirements tienen su propia rúbrica de criticidad con dos clases, SR-CL-A y SR-CL-B, definida en §4.5.3 del Capítulo 4 y con consecuencias prácticas distintas (nivel mínimo de rigor en la implementación y en la verificación).

- **Se añade un STPA-light sobre algunos hazards.** El HARA simplificado se completa con un análisis *STPA-light* aplicado a los hazards de criticidad alta y limitado a las cuatro categorías de *unsafe control actions*: acción no dada cuando hace falta, dada cuando no debe, dada con una magnitud inadecuada y dada en el momento equivocado. Este añadido recoge modos de fallo sistémicos que un HARA puro, centrado en las consecuencias, suele dejar poco representados. Usar STPA es un préstamo metodológico habitual en la práctica reciente de seguridad de sistemas con IA, y se documenta como tal, no como parte del HARA formal de ISO 26262.

Lo que el HARA simplificado *mantiene* es lo esencial del método: la enumeración sistemática de hazards a partir del análisis del item, su clasificación antes de obtener los requisitos, la trazabilidad en ambos sentidos entre cada hazard y los SRs que lo mitigan (adaptación A4), y el registro auditable de cada decisión de clasificación. La estructura del proceso (situación → hazards → clasificación → SRs) es la misma que la de la norma. Lo que cambia es el tipo de resultado final (criticidad cualitativa en lugar de ASIL) y el añadido de STPA-light sobre los hazards de mayor severidad relativa.

El reparto del trabajo con ISO 21448 (SOTIF) sigue la división habitual en la industria. El HARA simplificado identifica fallos sistemáticos del sistema, que es el foco tradicional de ISO 26262. Las *insuficiencias de la función prevista*, es decir, comportamientos correctos según la especificación pero peligrosos en operación, que son el foco de SOTIF, se recogen con la adaptación A5 (medición empírica del gap sim-to-real) y la adaptación A3 (runtime monitoring sobre los logs de intervención), no con el HARA. Este reparto se ve en la matriz de trazabilidad: los enlaces H↔SR cubren la parte ISO 26262 del problema, y la columna de "modo de evidencia esperado" (test / análisis estadístico / runtime) cubre la parte SOTIF cuando corresponde.

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figura 3.6 — Diagrama de la pirámide normativa." width="500"/>

*Figura 3.6 — Pirámide normativa: ISO 26262 en la base como ciclo de vida, SOTIF como complemento para condiciones no previstas, TR 5469 como capa general de IA, PAS 8800 como extensión automotriz para IA, UL 4600 como safety case que lo envuelve todo y AMLAS como patrones de argumentación transversales. Sobre la pirámide se marcan las cinco adaptaciones A1–A5 con su ámbito de aplicación.*

---
