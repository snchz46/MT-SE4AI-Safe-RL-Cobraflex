# Anexo C — Elecciones de instrumento y mapeo normativo

Desarrollo completo de §3.6 y §3.8. Cada elección se presenta con su justificación y con las alternativas descartadas y el motivo del descarte, de modo que la decisión sea auditable y no meramente declarada.

# C.1 Instrumentos


Esta sección documenta las elecciones de instrumento que articulan el marco
metodológico sobre el caso de estudio. La intención no es enumerar
herramientas, sino justificar cada elección frente a las alternativas
descartadas, dejando registro auditable de decisiones que de otro modo
quedarían implícitas. Cada subsección sigue un patrón uniforme:
herramienta elegida, justificación, alternativas descartadas con motivo
del descarte.

## C.1.1 Simulador

**Elección: Gazebo** (Koenig y Howard, 2004), en su variante moderna con
integración ROS2 nativa, operada a través de una interfaz
gymnasium-Gazebo-ROS2 que reutiliza un entorno previamente construido por
el autor en un trabajo de investigación anterior. La elección se
justifica por cuatro razones que conviene articular con honestidad, dado
que difiere de la práctica dominante en investigación de conducción
autónoma —donde CARLA es el simulador de referencia—.

Primero, *integración ROS2 nativa*. Gazebo es co-desarrollado con ROS por
Open Robotics y comparte primitivas (tópicos, transformadas, herramientas
de visualización) sin necesidad de capas de bridge intermedias. Toda la
arquitectura del proyecto descrita en el Capítulo 5 —percepción, policy,
cage, actuación, logger— es ROS2 desde su concepción; alojar el simulador
en el mismo grafo elimina superficie de falla y reduce la ambigüedad
sobre dónde ocurren latencias o desincronizaciones, lo que tiene
consecuencias directas para la fidelidad de las métricas de integración
(M-I).

Segundo, *reutilización del trabajo previo del autor*. El autor dispone
de un entorno Gazebo previamente construido para una tarea afín, con el
vehículo a escala modelado y la pista controlada configurada.
Reutilizar este entorno, en lugar de reconstruirlo desde cero en otra
plataforma, libera tiempo de proyecto para concentrarse en el aporte
metodológico —las adaptaciones A1–A5 y su materialización—, que es el
verdadero objeto de la tesis. Esta decisión es coherente con el enfoque
*design science* explicitado en §3.2.1: la contribución no está en el
simulador sino en el marco, y la elección de instrumento debe minimizar
el coste accidental.

Tercero, *interfaz gymnasium-Gazebo-ROS2 para entrenamiento*. La
interfaz que une el bucle de entrenamiento (Stable-Baselines3 sobre
gymnasium) con el simulador (Gazebo, vía ROS2) está disponible como
tooling abierto y permite una separación limpia entre algoritmo, entorno
y sistema. Esto facilita el cumplimiento de la adaptación A1 (Training
Specification como meta-design): los hiperparámetros, la función de
recompensa y el ODD de entrenamiento se especifican en un módulo Python
separado, sin acoplamiento al simulador subyacente.

Cuarto, *requisitos de cómputo más modestos*. Gazebo opera sobre
hardware menos exigente que CARLA, lo que es relevante para una tesis
individual sin acceso a infraestructura de cómputo dedicada y permite
acelerar el ciclo de iteración durante el desarrollo del Training Spec.

Esta elección lleva consigo dos compromisos que conviene reconocer
abiertamente. Por un lado, la fidelidad visual de Gazebo es inferior a
la que ofrece el motor Unreal Engine subyacente a CARLA; para una policy
basada en cámara monocular, esto puede traducirse en un gap sim-to-real
más pronunciado de lo que se observaría con un simulador fotorrealista.
La adaptación A5 del marco —caracterización empírica del gap— está
precisamente diseñada para hacer este efecto visible y medirlo, no para
ocultarlo (cf. §3.9 y Capítulo 9). Por otro lado, la comunidad de
investigación específica de conducción autónoma usa mayoritariamente
CARLA, lo que limita la disponibilidad inmediata de scenario libraries
reutilizables en formato Gazebo; esto supone que la scenario library del
proyecto debe construirse explícitamente, lo cual queda dentro del
alcance del Capítulo 6.

Alternativas consideradas y descartadas. CARLA (Dosovitskiy et al.,
2017) es el candidato más fuerte y la elección por defecto en
investigación de conducción autónoma reciente; ofrece fidelidad
sensorial superior y un ecosistema maduro de benchmarks, pero requiere
*bridge* ROS2 con sus propias complicaciones, y su mayor coste de cómputo es un freno
operativo para una tesis individual. Highway-Env y otros entornos
derivados de Gym, sin sensores realistas, con espacio de observación
abstracto, no adecuados para políticas basadas en cámara. LGSVL,
proyecto discontinuado en 2022 con ecosistema en descomposición.
**AirSim**, foco aeroespacial con soporte automotriz secundario y
desarrollo en pausa.

## C.1.2 Algoritmo de aprendizaje por refuerzo

**Elección: PPO** —*Proximal Policy Optimization*— (Schulman et al.,
2017). PPO se impone por cuatro motivos coherentes con el marco
metodológico. Primero, *estabilidad de entrenamiento*: el *clipped
surrogate objective* limita la divergencia de actualización sin requerir
restricción explícita de KL, lo que reduce la sensibilidad a
hiperparámetros y mejora la reproducibilidad —propiedad importante para un
trabajo individual con limitada compute para *sweeps* exhaustivos—.
Segundo, *interpretabilidad del Training Spec*: al ser *on-policy*, los
hiperparámetros tienen un significado semántico relativamente directo
(tamaño de rollout, épocas por update, ratio de clipping, coeficiente de
entropía), lo que facilita escribir el Training Spec del nivel L4b como
documento legible. Tercero, *soporte en herramientas abiertas*: la
implementación de Stable-Baselines3 está madura, ampliamente usada, y
admite integración directa con Gazebo a través de la interfaz
gymnasium-Gazebo-ROS2 mencionada en §3.6. Cuarto,
*compatibilidad con extensiones*: si en futuras iteraciones la tesis
explorase *constrained RL* (al estilo de RECPO de Zhao et al., 2024),
PPO admite extensión natural a CMDP.

Alternativas consideradas y descartadas: SAC (Haarnoja et al., 2018)
es competitivo en eficiencia de muestras y en robustez a hiperparámetros,
pero su carácter *off-policy* hace el Training Spec menos interpretable
—la noción de "qué política produjo qué experiencia" se difumina en el
*replay buffer*—, y su naturaleza estocástica con *temperature tuning*
añade complejidad al diseño del experimento; DDPG / TD3 (deterministas
*off-policy*) son más inestables que SAC y han sido superados por este en
casi todos los benchmarks; A3C / A2C son menos eficientes en muestras
y han sido virtualmente abandonados a favor de PPO desde 2018.

## C.1.3 Bucle de aprendizaje y herramientas de implementación

- **Stable-Baselines3** como implementación de PPO. Justificación:
  estabilidad, comunidad, integración con *gym* / *gymnasium*, código
  auditable.
- **PyTorch** como backend de redes neuronales. Justificación: estándar
  en investigación contemporánea, integración nativa con
  Stable-Baselines3, herramientas de profiling maduras.
- **pytest** como framework de testing para Cage Unit Tests (L4a' del
  V-Model adaptado) y para la suite de regresión general.
- **Python 3.10+** con herramientas de calidad: `ruff` (linting),
  `mypy` (type checking), `pre-commit` para automatización en commits.

## C.1.4 Plataforma física

El vehículo radio-controlado a escala 1:14 se selecciona sobre alternativas
de otras escalas por tres motivos: *coste* —un 1:14 es manipulable, las
piezas son asequibles y el riesgo de daño en operación es acotado—;
*seguridad de operación* —velocidades bajas, energía cinética baja, riesgo
para terceros despreciable en pista cerrada—; y *transferibilidad de la
simulación* —la dinámica de un 1:14 admite aproximación razonable en
Gazebo mediante un modelo vehicular plugin-based con parámetros
ajustables (masa, distribución de carga, fricción de neumáticos,
parámetros de actuación), mientras que escalas mayores (1:5, 1:1)
introducirían discrepancias dinámicas que dominarían el gap
sim-to-real—. Las especificaciones detalladas del coche (motor, ESC,
controlador de bajo nivel, cámara, plataforma de cómputo embebido) se
documentan en el Capítulo 5 y en el Anexo correspondiente.

<img src="../figures/fig_3_5_vehicle_cad.png" alt="Figura 3.5 — Fotografía del vehículo RC 1:14 instrumentado con la cámara, IMU." width="300"/>

*Figura 3.5 — fotografía/diagrama del vehículo RC 1:14 instrumentado con la cámara, IMU, encoder y SBC, con etiquetas sobre cada componente.*

## C.1.5 Instrumentación de medida

El instrumento primario de captura de evidencia es el Logger Node de la
arquitectura ROS2, ya descrito en la adaptación A3 (§3.4.3). El Logger
Node graba todas las interacciones relevantes en el bus —observaciones,
acciones de *policy*, decisiones de cage, intervenciones, estados del
vehículo— con marcas de tiempo que permiten reconstrucción posterior.

Las métricas concretas que se computan a partir de los logs se definen
formalmente en el Capítulo 4 y se agrupan en cinco familias por su
naturaleza: M-P (performance: error de seguimiento, completitud de
trayectoria), M-S (safety: tasa de intervención de cage, número de
violaciones por SR), M-I (integración: latencias, jitter, throughput),
M-C (comportamiento: estabilidad lateral, suavidad de control), y M-T
(transfer: divergencia sim-vs-real para cada métrica anterior, métricas
específicas del gap A5). El detalle se difiere al Capítulo 4.

Para evaluación cuantitativa adicional sobre la *scenario library* se
considera la métrica compuesta QED (Gao et al., 2021) como inspiración
conceptual: una métrica compuesta calibrada contra evaluadores humanos
para tareas de conducción autónoma. La adopción directa requiere
matización porque QED fue desarrollada y calibrada sobre CARLA, mientras
que el simulador adoptado en esta tesis es Gazebo; la fórmula conceptual
puede transferirse, pero los pesos calibrados deberían recomputarse para
el escenario lane-following en Gazebo si se quiere una métrica con
significado equivalente. *Behavior Metrics* (Paniego et al., 2024) se
considera como herramienta auxiliar de evaluación cuantitativa, dado
que su diseño es relativamente agnóstico al simulador subyacente. La
decisión sobre adopción definitiva como métrica oficial del proyecto se
difiere a Fase 4, cuando se cuente con la *policy* entrenada y se pueda
calibrar contra el evaluador humano del autor.

## C.1.6 Documentación, control de versiones y reproducibilidad

Todos los artefactos del proyecto —documentos, código, plantillas,
matriz de trazabilidad, scripts de validación— viven en un único
repositorio Git con la siguiente filosofía: el repositorio *es* el
proyecto. La elección consciente es de *plain text first*: los
artefactos se redactan en Markdown con extensiones mínimas (citas en
formato `[Apellido (año)]`, ecuaciones LaTeX, figuras como SVG/PNG en
carpeta dedicada), no en herramientas MBSE industriales del estilo de
Cameo o Capella.

Esta elección difiere de la propuesta MBSE de Sprockhoff et al. (2023)
para sistemas con componentes IA, que defiende SysML y herramientas
estructuradas como columna vertebral del ciclo de vida. La diferencia es
de *coste de adopción*: una tesis individual sin acceso a licencias
industriales obtiene mejor relación coste/beneficio con archivos de
texto versionados, manteniendo equivalencia funcional en cuanto a
trazabilidad (vía `traceability_matrix.csv` + `check_traceability.py`)
y consistencia (vía revisión por pares automatizada en cada commit).
La decisión se documenta en `DECISIONS.md` con su justificación
explícita y la conjetura de que escalar el marco a un equipo
industrial mediano sí motivaría el cambio a MBSE.

---

# C.2 Relación con los estándares


El V-Model adaptado se relaciona con el estado del arte normativo en
seguridad de sistemas IA. Esta sección sitúa cada adaptación en el
ecosistema regulatorio, distinguiendo qué es coherente con cada
estándar y qué va más allá. La revisión sigue el orden cronológico de
publicación, que coincide aproximadamente con el orden de adopción
industrial.

## C.2.1 ISO 26262:2018 — Functional Safety for Road Vehicles

ISO 26262:2018 establece el V-Model clásico aplicado a automoción. La
tesis lo toma como punto de partida y como marco al que pretende
mantenerse fiel en su estructura general.

- **Coherente:** la columna vertebral de cinco niveles L1–L5, la noción
  de safety requirement, el principio de correspondencia bidireccional
  especificación↔V&V, la derivación de requisitos a partir del HARA con
  asignación de niveles ASIL.
- **Más allá:** ISO 26262 no contempla módulos aprendidos. Las
  adaptaciones A1, A2 y A3 son extensiones explícitas para acomodar
  componentes RL sin romper la estructura general del estándar. La
  filosofía es de *tailoring* aditivo: nada se elimina; se añade lo
  estrictamente necesario.

## C.2.2 ISO 21448:2022 — SOTIF (Safety Of The Intended Functionality)

ISO 21448:2022 introduce la noción de seguridad más allá de fallos,
incluyendo uso de funciones en condiciones no anticipadas, y es la
respuesta institucional al hecho de que sistemas con percepción y
decisión basada en ML pueden comportarse incorrectamente sin que
ningún componente haya "fallado" en sentido clásico (Wang et al.,
2024).

- **Coherente:** la adaptación A5 (validación operacional acotada y
  caracterización del gap sim-to-real) es directamente consistente con
  la filosofía SOTIF de que la validación estática es insuficiente
  cuando el ODD no está completamente especificado. La adaptación A3
  (runtime monitoring continuo) es coherente con el principio SOTIF
  de gestión de *triggering conditions* descubiertas en operación.
- **Más allá:** A3 propone runtime monitoring como nivel
  arquitectónico explícito del lifecycle, no solo como práctica
  recomendada en operación.

## C.2.3 ISO/IEC TR 5469:2024 — AI Functional Safety

ISO/IEC TR 5469:2024 es el documento normativo más específico
publicado hasta la fecha sobre uso de IA en funciones de seguridad.
Su aportación principal para el marco propuesto es triple:
clasificación de elementos en Clase I y II, *three-stage realization
principle* (cláusula 7) y propiedades deseables de los componentes IA
(robustez, especificabilidad, verificabilidad, interpretabilidad).

- **Coherente:** la *policy* PPO de la tesis clasifica como elemento
  Clase II del TR 5469 —no admite verificación clásica completa—, y
  la adaptación A2 (Policy Behavioral Evaluation estadística) es
  congruente con esta clasificación. La trazabilidad bidireccional
  obligatoria (A4) operacionaliza el principio de *specifiability* del
  TR. El desdoblamiento Cage Spec / Training Spec (A1) articula a
  nivel de proceso de diseño la distinción del *three-stage realization
  principle* entre fases de adquisición, inducción y procesamiento.
- **Más allá:** la separación explícita entre Cage Spec (elemento
  Clase I) y Training Spec (meta-design para elemento Clase II) en
  documentos versionados separados es un refinamiento operativo del
  TR, no presente en el documento normativo en esa granularidad.

## C.2.4 ISO/PAS 8800:2024 — Road Vehicles, Safety and AI

ISO/PAS 8800:2024 es la especialización automotriz del marco
genérico de TR 5469. Indica qué cláusulas de ISO 26262 se mantienen,
cuáles se *tailor* y cuáles se sustituyen cuando hay un componente
de IA. Su aplicación temprana a un caso real (BSI/CAM, 2024 sobre un
detector de señales de stop) constituye la primera plantilla pública
para articular ISO 26262 + SOTIF + ISO/PAS 8800.

- **Coherente:** la filosofía de *tailoring* aditivo del V-Model
  adaptado coincide con la de ISO/PAS 8800. Las cinco adaptaciones
  A1–A5 son razonablemente alineables con las áreas que el estándar
  identifica como críticas (definición de operating environment,
  análisis sistemático de insuficiencias, monitoring post-despliegue).
- **Más allá:** la operacionalización del marco en un caso completo
  desde HARA hasta despliegue físico, con caracterización empírica
  del gap, excede en concreción a los ejemplos publicados hasta la
  fecha.

## C.2.5 UL 4600 — Standard for Safety for the Evaluation of Autonomous Products

UL 4600 (Koopman, 2023) enfatiza la noción de *safety case* y
evidencia estructurada como mecanismo central de assurance para
productos autónomos.

- **Coherente:** la Matriz de Trazabilidad H↔SR↔C↔SC↔M es un
  micro-safety-case en la línea de UL 4600: cada *claim* de seguridad
  se respalda con un argumento explícito (la regla de cage, el
  escenario, la métrica) y con evidencia trazable (los logs, los
  resultados experimentales).
- **Más allá:** A4 convierte la trazabilidad en restricción dura
  aplicada por herramienta automatizada (`check_traceability.py`), no
  en buena práctica documental revisable.

## C.2.6 AMLAS — Assurance of Machine Learning for Autonomous Systems

AMLAS, consolidado por Paterson et al. (2025), no es un estándar
formal sino una metodología con patrones GSN (*Goal Structuring
Notation*) específicos para construir argumentos de safety sobre
componentes ML. Se está incorporando como insumo a estándares
emergentes, en particular ISO/PAS 8800.

- **Coherente:** la filosofía claim-argument-evidence de AMLAS
  coincide con la trazabilidad bidireccional propuesta como A4. El
  ciclo de vida data-céntrico que AMLAS articula (definición de
  requisitos, gestión de datos, aprendizaje, verificación,
  despliegue, monitorización) coincide a grandes rasgos con la
  estructura por fases del proyecto descrita en §3.5.3.
- **Más allá:** AMLAS está principalmente probado sobre modelos
  supervisados; el marco propuesto en esta tesis es una articulación
  explícita para *policies* RL, dominio aún poco cubierto por
  AMLAS.

## C.2.7 HARA simplificado y su relación con la versión formal de la norma

La cláusula 6 de la Parte 3 de ISO 26262:2018 prescribe el método HARA
formal aplicado a *items* de automoción: análisis de situación,
identificación sistemática de hazards asociados a las funciones del
item, clasificación de cada hazard por tres ejes —severidad (S, escala
S0–S3), exposición (E, escala E0–E4) y controlabilidad (C, escala
C0–C3)— y derivación del *ASIL* (Automotive Safety Integrity Level,
QM/A/B/C/D) mediante una tabla de combinación de S×E×C. El ASIL
determina el rigor exigible al resto del ciclo de vida, incluyendo
medidas de diseño, técnicas de verificación y cobertura de tests.

La versión adoptada en esta tesis se denomina explícitamente *HARA
simplificado* y se documenta como tal en el encabezado del Hazard
Register. Las diferencias respecto a la norma formal son tres y se
enuncian aquí con honestidad:

- **Escalas S/E/C preservadas pero reinterpretadas para el contexto
  escalado.** Las tres escalas se mantienen con la granularidad de la
  norma (S1–S3, E1–E4, C1–C3), pero las definiciones cualitativas de
  cada nivel se reinterpretan para un vehículo a escala 1:14 sobre
  pista cerrada: S3 deja de significar "lesión mortal" y pasa a
  significar "pérdida total de la integridad de la plataforma", E3
  conserva el significado de "10–50% del tiempo operativo" pero
  referido al ODD declarado, y C2 mantiene el significado de
  "controlable en >90% de los casos" referido a la cage de reglas en
  lugar de al conductor humano. La rúbrica reinterpretada se versiona
  junto con el registro y queda auditable.

- **No se emite ASIL formal; se sustituye por una "Criticality"
  cualitativa.** El producto del HARA simplificado es, para cada
  hazard, una etiqueta cualitativa de criticidad en cuatro niveles
  (Low, Medium, Medium-High, High), derivada por agregación
  cualitativa del trío S/E/C y utilizada exclusivamente para
  priorización del trabajo de mitigación. La elección de no emitir
  un ASIL letra reconoce que el ASIL es una construcción
  legal-normativa orientada a la certificación industrial, no a la
  demostración metodológica que persigue la tesis. Emitir un
  "ASIL B" sobre un coche a escala introduciría una falsa precisión
  que el marco prefiere evitar; la criticidad cualitativa es honesta
  sobre lo que se está midiendo y sobre el uso que se le dará.
  Los Safety Requirements derivados, por separado, llevan su propia
  rúbrica de criticidad de tres niveles SR-CL-A/B/C definida en
  §4.7 del Capítulo 4 con consecuencias operativas distintas
  (rigor mínimo de implementación y de verificación).

- **Complemento con STPA-light sobre hazards seleccionados.** El HARA
  simplificado se complementa con un análisis *STPA-light* aplicado a
  los hazards de criticidad alta, acotado a las cuatro categorías de
  *unsafe control actions* —acción no provista cuando se necesita,
  provista cuando no debe, provista con magnitud inadecuada, provista
  en el momento equivocado—. Este complemento captura modos de fallo
  de tipo sistémico que un HARA puro, centrado en consecuencias,
  tiende a infrarrepresentar. La incorporación de STPA es un préstamo
  metodológico habitual en la práctica reciente de seguridad de
  sistemas con componentes IA y se documenta como tal, no como parte
  del HARA formal de ISO 26262.

Lo que el HARA simplificado *preserva* es lo metodológicamente
esencial: la enumeración sistemática de hazards a partir del análisis
del item, la clasificación previa a la derivación de requisitos, la
trazabilidad bidireccional desde cada hazard a sus SRs mitigantes
(adaptación A4), y la documentación auditable de cada decisión de
clasificación. La estructura del proceso —situación → hazards →
clasificación → SRs— es idéntica a la de la norma; lo que se modula
es la naturaleza del producto final (criticidad cualitativa en lugar
de ASIL) y la complementación con STPA-light sobre los hazards de
mayor severidad relativa.

La división del trabajo respecto a ISO 21448 (SOTIF) se mantiene
coherente con la repartición usual en la práctica industrial: el
HARA simplificado identifica fallos sistemáticos del sistema —foco
tradicional de ISO 26262—, mientras que las *insuficiencias de la
función intencionada* —comportamientos correctos respecto a la
especificación pero peligrosos en operación, foco de SOTIF— quedan
recogidas mediante la adaptación A5 (caracterización empírica del
gap sim-to-real) y la adaptación A3 (runtime monitoring sobre logs
de intervención), no por el HARA en sí. Esta repartición se hace
explícita en la matriz de trazabilidad: los hazards H↔SR cubren la
componente ISO 26262 del problema, y la columna de "modo de evidencia
esperado" (test / análisis estadístico / runtime) cubre la componente
SOTIF cuando aplica.

<img src="../figures/fig_3_6_normative_pyramid.png" alt="Figura 3.6 — Diagrama de la pirámide normativa." width="500"/>

*Figura 3.6 — diagrama de la pirámide normativa: ISO26262 en la base como ciclo de vida, SOTIF como complemento para condiciones no anticipadas, TR 5469 como paraguas IA, PAS 8800 como especialización automotriz, UL 4600 como safety case envolvente, AMLAS como patrones argumentativos transversales. Sobre esa pirámide, las cinco adaptaciones A1–A5 marcadas con su ámbito de aplicación. Posición sugerida: cierre de §3.8 Pendiente para Fase 6.*

---
