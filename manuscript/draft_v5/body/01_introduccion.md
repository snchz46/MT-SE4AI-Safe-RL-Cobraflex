# Capítulo 1 — Introducción

## 1.1 Contexto y motivación

En unos diez años, la conducción autónoma ha pasado de ser una demostración de laboratorio a estar, en parte, en el mercado. La mayoría de los fabricantes ya vende sistemas avanzados de asistencia al conductor (ADAS) de nivel 2 SAE y trabaja para llegar a los niveles 3 y 4 (Cheng et al., 2025), y ya existen los primeros sistemas de nivel 4 (Paniego et al., 2024). La Figura 1.1 muestra la escala de referencia que se usa en este trabajo para nombrar esos grados de automatización. Al mismo tiempo han crecido dos tendencias. La primera es el uso de aprendizaje automático en módulos de percepción, decisión y control que son críticos para la seguridad: redes profundas, que Kuutti et al. (2021a) revisan para el control del vehículo, y más recientemente políticas entrenadas por refuerzo (Kendall et al., 2019). La segunda es que las normas de seguridad funcional se han vuelto más exigentes.

<img src="../figures/fig_1_1_sae_automation_levels.png" alt="Figura 1.1 — Niveles SAE de automatización de la conducción." width="400"/>

*Figura 1.1 — Los seis niveles SAE de automatización de la conducción. El caso de estudio de esta tesis corresponde a una función de nivel 2 (§1.6.1). Reproducida de la tabla resumen de SAE J3016™, © 2021 SAE International, que puede copiarse y distribuirse tal cual siempre que se acredite a SAE International como fuente.*

Cada tendencia tiene sentido por separado, pero juntas generan un problema. Los marcos clásicos, con ISO 26262:2018 a la cabeza, se diseñaron para sistemas cuyo comportamiento se puede deducir de una especificación escrita de antemano, comprobar con tests que tienen una salida esperada y validar antes del despliegue. Los componentes aprendidos rompen los tres supuestos. Su comportamiento sale de una optimización estocástica, no existe una «respuesta correcta» con la que comparar su salida, y su robustez fuera de los datos de entrenamiento solo se puede medir de forma empírica (Wäschle et al., 2022; Paterson et al., 2025). Uno de los primeros estudios sistemáticos de este problema es el de Salay, Queiroz y Czarnecki (2017). Encontraron cinco áreas concretas en las que el ML afecta a ISO 26262, desde nuevos tipos de hazard hasta el hecho de que cerca del 40 % de las técnicas de software de la Parte 6 aplicables a nivel de unidad no sirven en absoluto para componentes ML. Ese artículo es el punto de partida directo de este trabajo. La investigación y la industria han respondido con dos estrategias parciales. Una es la contención, con arquitecturas monitor-actuador o *safety cages* (Kuutti et al., 2019, 2021b). La otra es la validación basada en escenarios (De Gelder et al., 2024). Cómo combinar ambas dentro de un ciclo de desarrollo con trazabilidad sigue siendo una pregunta abierta.

Las normas también están todavía poniéndose al día. Desde 2022, ISO 21448 (SOTIF) acepta que la validación estática no basta cuando el dominio operacional no se puede especificar por completo (Wang et al., 2024). ISO/IEC TR 5469:2024 ofrece la primera guía sistemática sobre IA en funciones de seguridad y clasifica los elementos de tecnología IA según lo bien que se pueden verificar. UL 4600 convierte el *safety case* en la forma principal de presentar la evidencia (Koopman, 2023). Las tres son guías de alto nivel. Dan principios, pero no describen un ciclo de vida concreto que se pueda aplicar a un proyecto real. Esta tesis trabaja justo en ese hueco.

## 1.2 Planteamiento del problema

**Nivel general.** Los métodos habituales de seguridad funcional del automóvil, sobre todo el V-Model de ISO 26262, no se pueden usar tal cual en sistemas con componentes entrenados por refuerzo. Si se aplican sin cambios, pasa una de dos cosas. O se obliga al componente RL a cumplir una especificación que no puede cumplir, y el proceso deja de ser honesto sobre lo que hace el sistema. O se deja el componente fuera del proceso, y se pierde la trazabilidad. Ninguna de las dos opciones es aceptable en un sistema con consecuencias de seguridad.

**Nivel específico.** La literatura propone varios arreglos por separado: safety cages para contener policies (Kuutti et al., 2019, 2021b), filtros predictivos de seguridad (Tearle et al., 2021) y evaluación basada en escenarios (De Gelder et al., 2024). Cada uno resuelve una parte del problema, pero no se combinan en un único ciclo de vida con trazabilidad explícita en ambos sentidos. Algunos trabajos sí miran el ciclo completo, sobre todo Ullrich et al. (2025), que amplían el V-Model clásico para sistemas con IA, y trabajos anteriores que adaptan ISO 26262 al ML (Salay et al., 2017; Vasudevan et al., 2021). Pero estas propuestas se quedan en lo abstracto. No ofrecen una versión ejecutable ni un caso de aplicación completo y documentado. Esta tesis construye una versión ejecutable de ese tipo de marco y la pone a prueba aplicándola a un caso real.

**Nivel concreto.** Para evaluar un marco así hay que aplicarlo a un caso lo bastante complejo como para que aparezcan los problemas típicos (especificar un comportamiento aprendido, el gap sim-to-real, la monitorización en operación), pero lo bastante pequeño como para que lo pueda llevar una sola persona. El caso elegido es el seguimiento de carril en un vehículo a escala 1:14, entrenado en Gazebo con PPO a través de una interfaz gymnasium–Gazebo–ROS2. En la versión principal, la *policy* es end-to-end desde la cámara frontal: una CNN aprende la percepción y convierte la imagen en una acción. La cage determinista no usa la red. Trabaja con su propio estimador de carril por visión. Así la percepción entra en el lazo a propósito, porque es el caso más difícil. Una segunda versión usa un vector de estado privilegiado y sirve como brazo de control. Permite aislar el efecto de la cage y ver cuánto cuesta la percepción.

La pregunta de investigación principal es:

> **¿Se puede adaptar el V-Model de ISO 26262 con un conjunto pequeño y trazable de cambios, de forma que admita componentes entrenados por refuerzo dentro de un ciclo de desarrollo con safety case, sin perder la relación en ambos sentidos entre especificación y V&V que da valor al estándar?**

Una segunda pregunta comprueba si el marco funciona en la práctica:

> **Cuando el marco se aplica a un caso de seguimiento de carril con una policy PPO y una cage de reglas, ¿produce evidencia coherente y trazable sobre el comportamiento del sistema, incluida una descripción honesta del gap sim-to-real?**

## 1.3 Hipótesis

- **H1 (de constructo).** Un conjunto pequeño y contable de cambios al V-Model clásico (cinco en este trabajo) basta para cubrir los modos de fallo típicos de los componentes RL/IA sin romper la estructura general del estándar.
- **H2 (de operatividad).** Cada cambio se puede convertir en artefactos concretos (documentos, tests, validadores automáticos) que se pueden producir y mantener con un esfuerzo acorde al resto del proyecto, y no como una carga desproporcionada.
- **H3 (de utilidad).** Aplicado al caso de estudio, el marco produce evidencia trazable que permite dar un veredicto fundamentado sobre el comportamiento del sistema, incluidos los límites de ese veredicto.

Las tres hipótesis se evalúan al final del trabajo (Capítulo 11). H1 se comprueba mirando la estructura del marco, H2 con el coste de adopción anotado en el registro de decisiones durante el proyecto, y H3 con cuántos Safety Requirements han recibido un veredicto.

## 1.4 Objetivos

### 1.4.1 Objetivo general

Diseñar, implementar y evaluar un marco metodológico, el *V-Model adaptado*, para desarrollar sistemas de conducción autónoma con componentes entrenados por refuerzo. El marco reúne en un solo ciclo las safety cages, la validación basada en escenarios, la monitorización en tiempo de ejecución y la trazabilidad en ambos sentidos, y es coherente con ISO 26262, ISO 21448, ISO/IEC TR 5469 y UL 4600.

### 1.4.2 Objetivos específicos

- **OE1.** Describir con precisión qué supuestos implícitos del V-Model clásico dejan de funcionar cuando se añade un componente entrenado por refuerzo a un módulo de seguridad. *(§3.3.)*
- **OE2.** Proponer y justificar un conjunto limitado de cambios que resuelvan esos supuestos y sigan siendo coherentes con los estándares. *(§3.4.)*
- **OE3.** Convertir cada cambio en artefactos concretos (especificaciones, tests, validadores, métricas) y definir cómo se producen. *(§3.5; los capítulos 4–8 lo llevan a la práctica.)*
- **OE4.** Aplicar el marco al caso de estudio, tanto en la versión principal con cámara como en la de vector de estado que sirve de línea base, hasta tener un sistema que funcione, se pueda evaluar y tenga trazabilidad completa. *(Capítulos 4–8.)*
- **OE5.** Medir el gap entre el entorno de entrenamiento y el entorno real de operación, como pide la adaptación A5. *(Capítulo 9.)*
- **OE6.** Dar un veredicto fundamentado sobre si se cumplen los Safety Requirements, y decir con claridad hasta dónde es válido. *(Capítulo 10.)*
- **OE7.** Evaluar el propio marco: cuánto cuesta adoptarlo, qué cubre y con qué criterios se considera suficiente o insuficiente. *(Capítulo 11.)*

## 1.5 Aportaciones

La aportación principal es un método, no un resultado técnico. El sistema de seguimiento de carril no es una aportación importante por sí mismo, porque existen versiones mejor entrenadas sobre vehículos más capaces. Lo que aporta esta tesis es el marco que hay detrás del sistema y la evidencia documentada de cómo se aplicó.

La tesis presenta cinco aportaciones, C1–C5. No son lo mismo que las cinco *adaptaciones* A1–A5 que forman el marco y que se definen en §3.4. Las adaptaciones son el contenido del marco. Las aportaciones son lo que este trabajo añade al estado del arte. En este capítulo y en todos los siguientes, A1–A5 se refiere siempre a las adaptaciones.

- **C1 — Un marco metodológico único.** Un V-Model adaptado con cinco cambios explícitos (A1–A5): el diseño de módulo se divide en *Cage Specification* y *Training Specification*; el test unitario se divide en *Cage Unit Tests* y *Policy Behavioral Evaluation*; se añade un nivel de monitorización en operación como validación continua; la trazabilidad en ambos sentidos pasa a ser una restricción dura; y la validación operacional se redefine para incluir una descripción explícita del gap sim-to-real.
- **C2 — Una versión ejecutable.** Cada cambio viene con los artefactos que lo implementan, incluidas plantillas reutilizables y validadores automáticos. El más importante es el verificador de trazabilidad, que convierte la trazabilidad en una puerta que un script puede aprobar o rechazar.
- **C3 — Un caso de estudio completo y reproducible.** El marco se aplica a un sistema construido desde cero, en dos versiones cuya comparación muestra cuánto cuesta la percepción por cámara. Los artefactos y los scripts de entrenamiento y evaluación están versionados, y los datos de ejecución están publicados.
- **C4 — Medición del gap sim-to-real** en dos peldaños cada vez más realistas a partir de Gazebo, que es donde se produce la campaña de referencia: primero un simulador de mayor fidelidad (Isaac Sim, PhysX + RTX) y después la plataforma física. El segundo peldaño termina como puesta en marcha y no como campaña de resultados. Los Capítulos 9 y 10 lo dicen abiertamente en lugar de ocultarlo.
- **C5 — Autoevaluación del marco:** cuánto costó adoptarlo, dónde funcionó como se esperaba y dónde mostró sus límites, para que otros puedan mejorarlo más adelante.

## 1.6 Alcance y limitaciones

### 1.6.1 Alcance

El marco se aplica a un solo sistema (seguimiento de carril con PPO y cage) sobre una sola plataforma (un vehículo RC 1:14 en una pista controlada). No hay comparación con un sistema parecido desarrollado con el V-Model clásico. La función es seguir el carril en una pista cerrada con iluminación y meteorología controladas. No se tratan la planificación, la interacción con otros vehículos ni la conducción en vía pública. En términos de niveles SAE, el sistema es una función de nivel 2. Los niveles 4–5 quedan fuera del alcance.

### 1.6.2 Limitaciones conocidas

- **Sesgo del autor.** La misma persona diseña, construye y evalúa el marco, así que hay riesgo de sesgo de confirmación. Se reduce en parte con una trazabilidad estricta que otros pueden auditar y con un registro de decisiones fechado.
- **N = 1.** Un solo caso no basta para sacar conclusiones generales sobre el marco. El argumento para generalizar es *estructural*: las adaptaciones atacan supuestos que fallan en cualquier sistema con un componente aprendido. No es un argumento estadístico.
- **Coste de adopción sin comparación.** Se anota el esfuerzo dedicado a los artefactos del marco, pero no hay grupo de control.
- **Las adaptaciones no son una lista cerrada.** Las cinco elegidas son las que el autor considera más relevantes para este caso. Se podrían justificar otras.
- **Plataforma a escala.** Lo que se encuentra sobre el gap sim-to-real vale para un vehículo 1:14 en una pista controlada.
- **El peldaño físico termina como puesta en marcha.** La cadena de despliegue funciona en el vehículo real y da resultados de calibración y hallazgos estructurales, pero no se ha puntuado ningún escenario sobre hardware y la cage nunca ha cambiado una acción allí. De ahí que la columna física de la tabla de veredictos se marque como *no ejecutada* (§10.4d–e) y que todas las cifras de conducción del Capítulo 9 sean preliminares. Es un límite de la evidencia, no del marco.

Estas limitaciones se tratan con más detalle en §3.9 y en el Capítulo 11.

### 1.6.3 Simplificaciones buscadas en el caso de estudio

El caso de estudio también incluye simplificaciones técnicas. No se eligieron por comodidad. Son controles experimentales: cada una fija una capa del sistema para poder estudiar por separado la capa que interesa a esta tesis. El sistema se puede ver como una pila:

> `percepción → estado (ey, epsi, v, κ) → [ policy + cage ] → actuación → dinámica`

La aportación está en el bloque `[policy + cage]`, y en ambos tracks las reglas de la cage se escriben sobre el estado abstracto. Hay tres simplificaciones.

**Dos tracks de observación.** El sistema principal es el track de cámara. La policy conduce desde la imagen y la cage lee su propio estimador CV determinista, así que la percepción es una parte central del trabajo. A su lado, el track de estado obtiene `(ey, epsi, v)` proyectando la pose verdadera sobre la línea central. Así se fija la capa de percepción, lo que permite aislar el efecto de la cage y medir el coste de la percepción como la diferencia entre los dos tracks. A la cage no le importa de dónde viene el estado. Los veredictos de seguridad se miden siempre sobre la pose verdadera, porque salirse del carril es un hecho físico y no un error del estimador.

**Control de la velocidad por parte de la policy.** El trabajo usa dos contratos. Durante la mayor parte del proyecto, el componente aprendido solo controla la dirección y la velocidad se mantiene constante. Esto reduce el problema al control lateral y mantiene la regla «la recompensa guía, la cage garantiza». En la campaña de referencia final la acción incluye dirección y tracción, así que la policy también controla la velocidad. El Capítulo 8 muestra que esto cambia el papel de la cage de una forma que se puede medir.

**Dos trazados, una plataforma.** El track de estado se valida sobre un óvalo (R = 0,8 m) y el de cámara sobre el circuito `complex_b`, que es sinuoso y pasa cerca de sí mismo (perímetro 19,22 m). Los dos usan el vehículo 1:14. El argumento para otros trazados es estructural, apoyado por ese segundo trazado, y no se basa en evidencia exhaustiva.

Estos límites no debilitan la afirmación principal, que es que la cage añade seguridad medible y trazable a un componente aprendido. La hacen *limpia*. Como las capas vecinas están fijadas, el efecto de la cage se puede atribuir con claridad, sin que lo tape el ruido de la percepción o el paso a hardware. Cada límite se vuelve a tratar en su contexto experimental en §8.2 y §8.8.

## 1.7 Estructura del documento

La tesis tiene doce capítulos en cuatro bloques, que se resumen en la Figura 1.2. El Bloque I — Marco contiene esta introducción, el estado del arte (Capítulo 2) y la metodología (Capítulo 3), que es la aportación académica principal. El Bloque II — Especificación trata el dominio operacional, el análisis de peligros y la derivación de requisitos (Capítulo 4), y la arquitectura con la especificación de la cage (Capítulo 5). El Bloque III — Implementación y evaluación trata la implementación y verificación (Capítulo 6), la especificación de entrenamiento y cómo se llevó a cabo (Capítulo 7), la campaña de evaluación experimental (Capítulo 8) y la medición del gap sim-to-real en peldaños cada vez más realistas (Capítulo 9). El Bloque IV — Cierre presenta la validación operacional y la tabla final de veredictos (Capítulo 10), una discusión del marco frente a sus propios criterios (Capítulo 11), y las conclusiones y el trabajo futuro (Capítulo 12).

<img src="../figures/fig_1_2_document_roadmap_es.png" alt="Figura 1.2 — Mapa de lectura del documento." width="620"/>

*Figura 1.2 — Mapa de lectura del documento: los cuatro bloques, los doce capítulos, lo que produce cada capítulo y a qué nivel del V-Model adaptado pertenece. La relación formal entre niveles y artefactos no se repite aquí. Está en la Tabla 3.3, una vez definido el marco.*

Los anexos recogen el material de apoyo, para que el texto principal se pueda leer de corrido: el registro de peligros ampliado (A), la especificación de requisitos con su *rationale* (B), la elección de instrumentos y la relación con las normas (C), la especificación del dominio operacional (D), los parámetros de la cage (E), la matriz de trazabilidad (F), el espacio de posicionamiento completo (G), el detalle de la especificación de entrenamiento (H) y los resultados escenario por escenario de la campaña de referencia (I).
