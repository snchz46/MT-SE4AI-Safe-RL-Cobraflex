# Capítulo 3 — Metodología

## 3.1 Propósito del capítulo

Este capítulo presenta la aportación metodológica principal de la tesis: el V-Model adaptado. Es un marco de ciclo de vida para sistemas con componentes entrenados por refuerzo dentro de funciones que afectan a la seguridad. El capítulo define el marco que se usa en el resto del trabajo, explica las decisiones que hay detrás y relaciona cada decisión con los estándares y con la literatura del Capítulo 2. No presenta resultados experimentales ni detalles de implementación.

Conviene separar dos cosas que se suelen mezclar. La *metodología de investigación* se trata en §3.2, y responde a la pregunta «¿qué aporta esta tesis al conocimiento?». La *metodología de ingeniería del sistema* ocupa de §3.3 a §3.8, y responde a otra distinta: «¿cómo se construye el sistema?». Los capítulos 4 a 10 llevan a la práctica lo que se define aquí, y el Capítulo 11 evalúa el marco a partir de esa práctica.

## 3.2 Enfoque de la investigación

### 3.2.1 Tipo de investigación

El trabajo sigue la tradición del *design science research* (March y Smith, 1995; Hevner et al., 2004). En esta tradición, la aportación académica no es una afirmación empírica contrastada con la realidad ni una proposición lógica demostrada por deducción. Es un artefacto que resuelve un problema conocido, y su utilidad se evalúa con uno o varios casos de aplicación.

Aquí el artefacto es el V-Model adaptado: cinco adaptaciones A1–A5 sobre el V-Model de ISO 26262, con las plantillas y los validadores que las implementan. De ahí tres consecuencias. La tesis no busca descubrir un fenómeno ni refutar una hipótesis estadística, sino construir un artefacto útil y demostrar que funciona. La evaluación mira el artefacto y no solo el sistema construido con él, de donde sale el Capítulo 11. Y la generalización se argumenta por la estructura —las adaptaciones atacan supuestos que fallan en cualquier sistema con un componente aprendido— y no por estadística sobre muchos casos.

### 3.2.2 Estrategia de evaluación: un solo caso de estudio

El marco se evalúa con un único caso: seguimiento de carril en un vehículo a escala 1:14, entrenado con PPO en Gazebo y supervisado por una safety cage determinista. La razón es de viabilidad. Un caso que cubra todo el ciclo, desde el HARA hasta el despliegue, ya es mucho trabajo para una tesis de máster. Hacer varios obligaría a tratarlos por encima, y eso no encaja con el rigor que pide el propio marco. Es mejor un caso profundo que varios superficiales. El precio es una menor validez externa, que se reduce de dos formas: con el argumento estructural y diciendo claramente en el Capítulo 12 qué partes del marco se pueden reutilizar y cuáles habría que replantear.

### 3.2.3 Papel del autor

El autor diseña el marco, construye el sistema y evalúa el resultado. Eso crea un riesgo de sesgo de confirmación que conviene reconocer antes de intentar reducirlo, y se aborda en tres niveles. La trazabilidad en ambos sentidos como restricción dura (A4), que un validador hace cumplir señalando huérfanos sin que intervenga el autor, funciona como un auditor externo barato. El registro fechado de decisiones anota qué se decidió, qué se descartó y por qué, y otros pueden auditarlo después. Y la lista de limitaciones (§3.9 y Capítulo 11) está escrita con el mismo espíritu crítico que si la solución fuera ajena. Ninguno elimina el sesgo, y nada podría: lo que consiguen es dejarlo abierto a lo que una persona independiente puede comprobar en los artefactos versionados.

## 3.3 El V-Model clásico y sus supuestos subyacentes

El V-Model viene de la ingeniería de sistemas (Forsberg y Mooz, 1991) y es el modelo de proceso de referencia en ISO 26262. Organiza el desarrollo en cinco niveles, con una relación en ambos sentidos entre la especificación (rama izquierda, que baja) y la verificación y validación (rama derecha, que sube).

<img src="../figures/fig_3_1_adopted_classical_v_model.png" alt="Figura 3.1 — El V-Model adoptado por ISO 26262, simplificado a cinco niveles." width="480"/>

*Figura 3.1 — El V-Model adoptado por ISO 26262, simplificado a los cinco niveles que se usan en todo el trabajo. La relación horizontal entre cada nivel de especificación y su nivel de verificación es lo que las adaptaciones de §3.4 intentan conservar.*

El modelo se apoya en cinco supuestos. Casi nunca se escriben, pero toda la estructura depende de ellos. Salay, Queiroz y Czarnecki (2017) fueron los primeros en identificarlos de forma sistemática. Los supuestos S1–S5 de la Tabla 3.1 son una reescritura práctica de su análisis, planteada para que cada uno tenga una adaptación correspondiente en §3.4.

| Supuesto | Enunciado | Por qué falla con un componente RL |
| --- | --- | --- |
| S1 | Cada módulo tiene una especificación completa y determinista escrita de antemano | La policy no tiene una especificación diseñada: sale del entrenamiento. No existe un documento que diga «cuando la entrada es Y, produce Z» |
| S2 | El comportamiento se puede deducir fielmente de la especificación | El comportamiento se puede observar *post hoc*, pero no se puede predecir analíticamente |
| S3 | Los tests unitarios comprueban el cumplimiento con una cobertura finita | No hay una salida «correcta» para cada entrada, solo salidas estadísticamente plausibles |
| S4 | La verificación estática basta para garantizar las propiedades | La policy puede pasar los tests y fallar en operación por distribuciones de estado que no se probaron |
| S5 | El entorno de operación se parece lo bastante al de pruebas | El gap entre simulación y realidad puede ser grande y pasar desapercibido |

*Tabla 3.1 — Los cinco supuestos del V-Model clásico y por qué fallan con componentes aprendidos.*

El hueco es práctico y no solo conceptual: de las técnicas de software de la Parte 6 aplicables a nivel de unidad, cerca del 40 % no sirve para componentes ML (§2.6). Esa es la razón de un marco complementario.

Estos cinco fallos no son un motivo para abandonar el V-Model. Son un motivo para adaptarlo. El núcleo de este trabajo es mantener la estructura en V, y con ella la coherencia con ISO 26262, añadiendo solo los cambios necesarios para que la policy encaje en el ciclo sin romper la trazabilidad ni la honestidad del proceso.

## 3.4 Las cinco adaptaciones

### 3.4.1 A1 — Dividir el diseño de módulo

**Problema.** El nivel de diseño de módulo (L4) supone que cada módulo puede tener una especificación completa y determinista escrita de antemano. Esto no se cumple para la policy. No se puede escribir «la policy debe producir `a = f(s)` tal que…» porque `f` es el resultado de la optimización, no algo que se le da como entrada.

**Adaptación.** L4 se divide en dos subniveles distintos. L4a — Cage Specification es una especificación clásica. Es determinista y modular, y cada regla de la cage es una función pura y testeable, con entradas y salidas definidas, diseñada de la forma tradicional. L4b — Training Specification es una *meta-especificación*. No describe cómo se comporta la policy. Describe el proceso que la produce: función de recompensa, espacios de estado y acción, ODD de entrenamiento, criterios de convergencia, algoritmo y restricciones activas durante el entrenamiento.

Esta división encaja con el principio de realización en tres etapas de ISO/IEC TR 5469:2024, que separa la adquisición de datos, la inducción de conocimiento a partir de datos y conocimiento humano, y el procesamiento y generación de salidas. El TR aclara que ese principio no es un ciclo de vida, así que A1 lleva la idea al proceso de diseño. Artefactos: la especificación de la cage con sus reglas definidas formalmente (Capítulo 5) y la especificación de entrenamiento (Capítulo 7).

### 3.4.2 A2 — Del test unitario a la evaluación del comportamiento

**Problema.** Un test unitario comprueba un módulo contra su especificación con casos que tienen una salida esperada. Para la policy no existe una «salida esperada» para un estado dado, solo distribuciones plausibles que dependen del estado.

**Adaptación.** Este nivel se divide igual que en A1. L4a' — Cage Unit Tests son tests unitarios clásicos para cada regla, con vectores de estado sintéticos, un comportamiento determinista esperado y un resultado de pasa/no pasa, igual que en el V clásico. L4b' — Policy Behavioral Evaluation es una evaluación estadística sobre distribuciones de estado, por ejemplo «en N estados muestreados del ODD, la policy produce acciones que cumplen la propiedad X con frecuencia Y». No es verificación en sentido lógico. Es una descripción estadística del comportamiento.

La adaptación acepta que la verificación clásica no funciona con componentes aprendidos. La tesis no intenta forzarla. Usa una herramienta adecuada y mantiene la verificación clásica donde sigue funcionando, que es en la cage. Esta diferencia encaja, por analogía, con las clases tecnológicas del TR 5469. La cage es un componente convencional de reglas y se puede desarrollar y revisar por completo con la práctica de seguridad funcional existente, como la tecnología de Clase I. La policy es como mucho un elemento de Clase II, cuyas propiedades requeridas solo se pueden abordar con métodos complementarios como la evaluación estadística de A2.

### 3.4.3 A3 — Monitorización en operación como validación continua

**Problema.** El V-Model supone que la validación termina antes del despliegue. Una vez validado, el sistema se despliega y se mantiene. No hay ningún nivel para seguir validando después del despliegue.

**Adaptación.** Se añade un nivel horizontal llamado Runtime Monitoring. Se alimenta de los registros de intervención de la cage durante la operación y devuelve esa información a la validación de forma continua. Este nivel acepta tres hechos propios de los sistemas con IA: la distribución en operación puede ser distinta de la de pruebas, pueden aparecer modos de fallo que el análisis de peligros no previó, y la evidencia de seguridad hay que acumularla con el tiempo.

En este trabajo el nodo de registro no es un componente auxiliar. Es la herramienta principal de este nivel. Los registros que genera durante las campañas experimentales son evidencia de validación continua dentro del periodo del proyecto, y en un despliegue real el mismo mecanismo seguiría generando evidencia sin fecha de fin. La adaptación encaja con el enfoque de SOTIF y con la fase de operación que usan Wang et al. (2024) para organizar la investigación sobre SOTIF. De Mohseni et al. (2019) toma la idea de la *función de monitorización* como categoría arquitectónica propia, y da un paso más: la monitorización deja de ser solo un mecanismo técnico y pasa a ser un nivel explícito del ciclo de vida, con artefactos versionados y un lugar definido en la matriz de trazabilidad.

### 3.4.4 A4 — Trazabilidad obligatoria como restricción dura

**Problema.** La trazabilidad entre niveles se recomienda, pero en la práctica no se exige. Puede haber código de pegamento sin un requisito padre. En sistemas clásicos esto se tolera, porque todo el comportamiento se puede inspeccionar.

**Problema específico en RL.** Cuando un componente es aprendido, es tentador explicar los comportamientos como «propiedades emergentes». Sin una trazabilidad estricta, cualquier comportamiento se puede justificar a posteriori como algo que la policy aprendió, y la responsabilidad de ingeniería pierde su sentido.

**Adaptación.** La trazabilidad en ambos sentidos pasa de buena práctica a restricción dura, con cinco obligaciones que se aplican a la vez. Toda regla de la cage apunta al menos a un requisito de seguridad. Todo requisito tiene al menos una regla que lo implementa, o una razón explícita de por qué no la necesita. Todo hazard tiene al menos un requisito que lo mitiga, o un riesgo aceptado documentado. Todo escenario apunta al menos a un requisito que verifica. Toda métrica apunta al menos a un requisito al que aporta evidencia. Un validador automático, cuyo flujo muestra la Figura 3.2, se ejecuta en cada cambio y falla si encuentra huérfanos en cualquier sentido.

<img src="../figures/fig_3_2_check_traceability_flow.png" alt="Figura 3.2 — Flujo del validador de trazabilidad." width="470"/>

*Figura 3.2 — Flujo del validador de trazabilidad, en cuatro capas: carga de los documentos vivos; extracción de identificadores con expresiones regulares sobre las cabeceras; comprobación de la cadena de restricciones sobre el grafo `H ↔ SR ↔ C ↔ SC`, con el subgrafo `SR ↔ M` colgando del nodo de requisitos; y combinación final con tres salidas posibles: todas las comprobaciones pasan, huérfano o referencia inválida, o aviso en modo estricto.*

Esto tiene un efecto indirecto pero importante en el diseño. La restricción facilita el análisis de peligros, porque desde el primer requisito obliga a preguntarse «¿qué regla se va a encargar de esto?». El resultado son requisitos más prácticos y menos abstractos. La idea se parece a los patrones GSN de AMLAS, pero A4 va un paso más allá al convertir la trazabilidad en algo que una herramienta puede comprobar, en lugar de una práctica de documentación que alguien tiene que revisar.

### 3.4.5 A5 — Validación operacional acotada y medición del gap

**Problema.** El test de aceptación supone un veredicto de pasa/no pasa frente a los requisitos de las partes interesadas y, sin decirlo, supone que las condiciones de prueba representan las de operación. Para un sistema entrenado en simulación esto es falso. El gap es un riesgo de primer orden, y pasar una prueba en simulación no significa que el sistema sea seguro en el mundo real.

**Adaptación.** Este nivel pasa a ser la Validación Operacional, con dos partes obligatorias. La primera es la validación por escenarios ligados a requisitos, con métricas de cobertura sobre el ODD. La segunda es una medición explícita y cuantitativa del gap entre el entorno de entrenamiento y el de operación, para cada métrica y cada modo de fallo relevante. La conclusión ya no es «el sistema es seguro». Pasa a ser: *el sistema cumple los requisitos en las condiciones del ODD X, con un gap medido de Y respecto a las condiciones de entrenamiento, y con los siguientes riesgos residuales documentados*.

### 3.4.6 Resumen

| ID | Adaptación | Problema del V clásico | Solución | Artefacto |
| --- | --- | --- | --- | --- |
| A1 | Dividir el diseño de módulo | La policy no tiene especificación a priori | Cage Spec (clásica) + Training Spec (meta-diseño) | Caps. 5 y 7 |
| A2 | Dividir el test unitario | La policy no admite un test unitario clásico | Tests de la cage + evaluación estadística del comportamiento | Suite de tests + Cap. 8 |
| A3 | Nivel de monitorización en operación | La validación estática no basta | Registro de intervenciones como evidencia continua | Nodo de registro + datos |
| A4 | Trazabilidad obligatoria | Los huérfanos esconden «propiedades emergentes» | Restricción dura en ambos sentidos `H↔SR↔C↔SC↔M` | Matriz + validador |
| A5 | Validación acotada con gap | La prueba en simulación no representa la operación | Veredicto con límites + gap medido | Caps. 9 y 10 |

*Tabla 3.2 — Las cinco adaptaciones al V-Model clásico.*

<img src="../figures/fig_3_3_adapted_v_model.png" alt="Figura 3.3 — V-Model adaptado." width="480"/>

*Figura 3.3 — El V-Model adaptado a IA. En gris, los elementos que se mantienen sin cambios de la Figura 3.1. En color, los que A1–A5 añaden o cambian: naranja para la división del diseño de módulo (A1), azul para la división del test unitario (A2), verde para la banda transversal de monitorización en operación (A3), las flechas horizontales de *compulsory traceability* para A4, y morado para la validación operacional con el gap (A5).*

## 3.5 Aplicación del marco al caso de estudio

### 3.5.1 Sistema estudiado y decisión de arquitectura

El sistema es un vehículo radiocontrolado a escala 1:14. Su sensor principal es una cámara frontal monocular, y también lleva una unidad inercial y un encoder de motor, con cómputo embarcado en una placa que soporta ROS2. Se desarrolla en dos plataformas en paralelo. Una es simulada: Gazebo con integración ROS2 nativa, usado a través de una interfaz gymnasium–Gazebo–ROS2 que reutiliza un entorno construido por el autor en un trabajo anterior. La otra es física: una pista cerrada con iluminación controlada.

Hay una decisión de arquitectura que importa para la metodología y no solo para el sistema. Al principio el proyecto usó una división modular explícita (percepción, policy, cage, actuación y registro), con el componente aprendido en una posición limitada, siguiendo el consejo de Salay et al. (2017) de evitar el ML a nivel de arquitectura y dejarlo a nivel de unidad. Después, el sistema principal pasó a ser una versión end-to-end con cámara, con la policy como una CNN que aprende la percepción y convierte la imagen en una acción.

El cambio es seguro porque la arquitectura de seguridad se mantiene: la cage sigue trabajando sobre su propio estimador de carril, una cadena clásica de visión separada de la CNN que no es ni la verdad de referencia ni una red aprendida. Los píxeles entran en la policy, pero la envolvente trabaja sobre un estado independiente y auditable. Por eso A1 sigue valiendo (cage y policy siguen siendo módulos distintos), A2 también (la cage se verifica sin la policy) y A4 igual (la cadena de trazabilidad no cambia). El coste aceptado es el que ya señalaba el motivo original: el enfoque end-to-end necesita más entrenamiento, y el Capítulo 7 lo tiene en cuenta. El track de estado queda congelado como brazo de control para aislar el coste de la percepción.

### 3.5.2 Correspondencia entre el marco y el caso

| Nivel del V-Model adaptado | Artefacto en el caso de estudio | Capítulo |
| --- | --- | --- |
| L1 — Requisitos de las partes interesadas | ODD + caso de uso | 4 |
| L2 — Requisitos de seguridad del sistema | `SR-001..SR-014` derivados del HARA | 4 |
| L3 — Diseño arquitectónico | Grafo ROS2 (percepción, policy, cage, actuación, registro) | 5 |
| L4a — Cage Specification | Reglas `C-01..C-06` | 5 |
| L4b — Training Specification | Recompensa, ODD de entrenamiento, hiperparámetros, criterios | 7 |
| L5 — Implementación | Nodo de cage ROS2 + policy entrenada | 6, 7 |
| L4a' — Tests unitarios de la cage | Suite determinista de la cage | 6 |
| L4b' — Evaluación del comportamiento de la policy | Análisis estadístico sobre la biblioteca de escenarios | 8 |
| L3' — Test de integración | Tests de la cadena completa | 6 |
| L2' — Test basado en escenarios | Familias `SC-NOM` / `SC-EDGE` / `SC-PERT` / `SC-FRONT` | 6, 8 |
| L1' — Validación operacional | Campaña + gap sim-to-real + veredicto por requisito | 9, 10 |
| Monitorización en operación (A3) | Nodo de registro + registros de intervención (transversal) | 5–10 |

*Tabla 3.3 — Correspondencia entre el marco y el caso de estudio.*

Esta tabla es la primera prueba de que el marco se puede llevar a la práctica. Cada nivel del V tiene un artefacto, un capítulo donde se desarrolla y un lugar en la matriz de trazabilidad.

### 3.5.3 Fases

El proyecto tiene siete fases seguidas, cada una con entregables definidos y una puerta de revisión que decide si se pasa a la siguiente. Son independientes de los niveles del V-Model: una fase puede producir artefactos de varios niveles, y un nivel se puede construir a lo largo de varias fases. La Figura 3.4 cruza fases y niveles: preparación del marco y las plantillas; ODD, análisis de peligros y requisitos; cage y sus tests; especificación de entrenamiento y biblioteca de escenarios; entrenamiento y evaluación del comportamiento; despliegue físico y medición del gap; y cierre de la evidencia y la matriz.

<img src="../figures/fig_3_4_project_phases.png" alt="Figura 3.4 — Fases del proyecto frente a niveles del V-Model adaptado." width="480"/>

*Figura 3.4 — Fases del proyecto frente a niveles del V-Model adaptado. La banda de monitorización es horizontal porque empieza a funcionar en cuanto existe el nodo de cage y sigue hasta el final. La banda de trazabilidad muestra cómo la cadena `H ↔ SR ↔ C ↔ SC ↔ M` se va completando fase a fase.*

Conviene insistir en un punto, porque es donde el marco deja de ser una propuesta y se convierte en práctica. A4 funciona por completo desde la fase de análisis de peligros. El validador se ejecuta con cada cambio del registro de hazards y de la especificación de requisitos. Exige que cada hazard enlace con al menos un requisito que lo mitigue, o con un riesgo aceptado documentado, y lo mismo al revés. Desde ahí, el ciclo «documentar → enlazar → validar» corre en cada commit.

## 3.6 Elección de herramientas

Cada elección de herramienta se justifica frente a las alternativas descartadas, para que decisiones que de otro modo quedarían implícitas dejen un registro auditable. Aquí solo se discute el simulador, porque la metodología depende de él: es la referencia contra la que A5 mide el gap. Las demás (algoritmo y biblioteca de aprendizaje, plataforma física, instrumentos de medida y herramientas de reproducibilidad) se tratan igual en el Anexo C, junto con la relación cláusula a cláusula con las normas. El middleware no se discute aparte porque va unido al simulador: la integración ROS2 nativa es el primero de los motivos de abajo.

**Simulador: Gazebo.** Esta elección se aparta de lo habitual, donde CARLA es la referencia, y se apoya en cuatro motivos que el Anexo C.1.1 desarrolla uno a uno: integración ROS2 nativa, que mantiene todo el sistema en un solo grafo y hace fiables las métricas de latencia; reutilización de un entorno que el autor ya tenía construido, coherente con un enfoque de *design science* en el que la herramienta no es la aportación; una interfaz de entrenamiento disponible que separa algoritmo, entorno y sistema, y así facilita A1; y unos requisitos de cómputo modestos, decisivos en una tesis individual.

Sus dos inconvenientes hay que decirlos. La calidad visual es menor que la de los motores fotorrealistas, lo que para una policy basada en cámara puede suponer un gap mayor; la adaptación A5 existe precisamente para hacer visible ese efecto y medirlo, no para ocultarlo. Y como la comunidad de conducción autónoma usa sobre todo CARLA, no hay bibliotecas de escenarios para Gazebo y este proyecto tiene que construir la suya.

Las alternativas descartadas (CARLA, Highway-Env, LGSVL y AirSim) se razonan también en el Anexo C.1.1.

## 3.7 Evaluación del marco

Esta sección se pregunta si la metodología ayudó a construir el sistema, no si el sistema resultó útil. Son dos preguntas distintas: se puede aplicar un buen marco a un sistema modesto, y al revés. La evaluación usa cinco criterios, cada uno con un indicador que se puede medir al final:

1. **Integridad de la trazabilidad.** Indicador: huérfanos encontrados por el validador en la última ejecución. Éxito: cero.
2. **Cobertura de requisitos con evidencia.** Indicador: porcentaje de requisitos con un veredicto respaldado por evidencia cuantitativa. Éxito: el 100 % tiene veredicto, aunque sea negativo o parcial. Un veredicto incómodo es mejor que uno que falta.
3. **Anticipación de hazards.** Indicador: cuántos de los hazards que aparecieron realmente estaban previstos, frente a los que no. Éxito: la mayoría de los hazards observados estaban previstos, y los inesperados se pueden auditar y clasificar.
4. **Coste de adopción.** Indicador: tiempo dedicado a artefactos del marco frente a artefactos puramente técnicos. Éxito: el coste es proporcional al beneficio observado.
5. **Utilidad de la matriz.** Indicador: cambios técnicos en los que la matriz hizo más rápido el análisis de impacto. Éxito: casos documentados en los que aportó un valor claro.

La evaluación tiene tres límites declarados. Se hace dentro de un solo proyecto y sin grupo de control, así que las conclusiones se basan en la plausibilidad y no en experimentos controlados. El sesgo del autor se limita pero no desaparece. Y el periodo experimental es corto, mientras que los beneficios de A3 se verían en plazos mucho más largos.

## 3.8 Relación con los estándares

El marco no sustituye a los estándares. Los conecta. Cada adaptación tiene un anclaje claro en las normas, que resume la Tabla 3.4. La relación completa, cláusula a cláusula, está en el Anexo C.

| Adaptación | Anclaje normativo principal |
| --- | --- |
| A1 — Cage Spec + Training Spec | TR 5469 §7 (principio de realización en tres etapas); PAS 8800 (adaptación del diseño de módulo) |
| A2 — Tests de cage + evaluación del comportamiento | TR 5469 (elementos Clase I / Clase II); ISO 26262 Parte 6 para la parte clásica |
| A3 — Monitorización en operación | SOTIF (la validación estática no basta); fase de operación tal como la describen Wang et al. (2024) |
| A4 — Trazabilidad dura | ISO 26262 Parte 8 (gestión de requisitos); AMLAS (patrones GSN); UL 4600 (afirmación–argumento–evidencia) |
| A5 — Validación acotada + gap | SOTIF (condiciones no previstas); UL 4600 (límites declarados del safety case) |

*Tabla 3.4 — Anclaje normativo de las cinco adaptaciones.*

Una aclaración sobre el análisis de peligros: el HARA usado aquí es más simple que el que exige ISO 26262. No se hace en paralelo al V sino dentro de él, justo en el lugar donde el estándar coloca la salida del HARA formal. El Capítulo 4 explica las simplificaciones y por qué se hicieron.

## 3.9 Limitaciones de la metodología

Las limitaciones del *trabajo* están en §1.6.2. Las tres que afectan a la *metodología* en sí, y no al caso que la pone a prueba, son estas:

- **La validez de constructo está limitada por tener un solo caso.** La generalización se apoya en la estructura, no en evidencia de varios casos. Mitigación: el Capítulo 12 separa las partes que se pueden reutilizar de las que habría que replantear.
- **La simulación tiene una calidad visual solo moderada.** Todo el entrenamiento ocurre en Gazebo, lo que puede agrandar el gap en las características visuales que capta la cámara. Mitigación: A5 hace visible el gap y el Capítulo 9 lo mide. Repetir el experimento en un simulador fotorrealista es el siguiente paso natural.
- **Las cinco adaptaciones no son una lista cerrada.** Se podrían justificar otras, por ejemplo un nivel dedicado a la ingeniería de datos, siguiendo el enfoque centrado en datos del TR 5469 y de AMLAS. Cada una está justificada, pero no se afirma que sean las únicas posibles.

## 3.10 Siguientes pasos

Con el marco definido, los capítulos siguientes lo aplican. El Capítulo 4 cubre la parte superior de la rama izquierda del V (dominio operacional, análisis de peligros y derivación de requisitos) y produce los primeros artefactos que A4 comprueba como restricción dura. A partir de ahí, cada capítulo cubre un nivel del V y cierra su relación con el nivel correspondiente de la rama derecha.
