# Capítulo 3 — Metodología

## 3.1 Propósito del capítulo

Este capítulo presenta la aportación metodológica central de la tesis: el **V-Model adaptado**, un marco de ciclo de vida concebido para sistemas que incorporan componentes entrenados por refuerzo dentro de funciones con implicaciones de seguridad. Establece el marco que rige el resto del trabajo, justifica las decisiones que lo configuran y sitúa cada una respecto de los estándares y de la literatura del Capítulo 2; no presenta resultados experimentales ni detalles de implementación.

Conviene separar dos niveles que a menudo se confunden. La *metodología de investigación* —cómo se produce conocimiento generalizable a partir del trabajo— se discute en §3.2. La *metodología de ingeniería del sistema* —cómo se produce el artefacto técnico desde los requisitos hasta el despliegue— ocupa §3.3 a §3.8. La primera responde a «¿qué aporta esta tesis al conocimiento?»; la segunda, a «¿cómo se construye el sistema?». Los capítulos 4 a 10 son la materialización experimental de lo aquí definido y el Capítulo 11 evalúa el marco a la luz de esa materialización.

## 3.2 Posicionamiento epistemológico

### 3.2.1 Tipo de investigación

El trabajo se inscribe en la tradición del *design science research* (Hevner et al., 2004) o, en formulación próxima, *constructive research* (March y Smith, 1995). En ella la contribución académica no es una proposición empírica contrastada contra la realidad ni una proposición lógica demostrada deductivamente, sino un **artefacto** que aborda un problema previamente identificado y cuya utilidad se evalúa mediante uno o varios casos de aplicación.

El artefacto es el V-Model adaptado —cinco adaptaciones A1–A5 sobre el V-Model de ISO 26262— junto con las plantillas, validadores y artefactos derivados que lo materializan. Esta caracterización tiene tres consecuencias. Primera: la tesis no busca la contribución típica de una tesis empírica —descubrir un fenómeno, refutar una hipótesis estadística— sino producir un artefacto útil y demostrar su funcionamiento. Segunda: la evaluación se hace sobre el artefacto y no solo sobre el sistema construido con él, lo que exige un capítulo dedicado a evaluar el marco en sí (Capítulo 11). Tercera: la generalización se argumenta por **plausibilidad estructural** —las adaptaciones atacan supuestos del V-Model que fallan para cualquier sistema con componente aprendido— y no por inducción estadística sobre múltiples casos.

### 3.2.2 Estrategia de evaluación: caso de estudio único

El marco se evalúa mediante un único caso: seguimiento de carril sobre un vehículo a escala 1:14, entrenado por PPO en Gazebo y supervisado por una safety cage determinista. El motivo es de **viabilidad**: un caso que cubra el ciclo completo —de HARA a despliegue— es ya un compromiso ambicioso para una tesis de máster, y multiplicarlo introduciría una superficialidad incompatible con el rigor que el propio marco exige. Es preferible un caso profundo a varios superficiales. El coste es de **validez externa**, y se mitiga por dos vías: el argumento de plausibilidad estructural y el reconocimiento explícito, en el Capítulo 12, de qué partes del marco son trasladables y cuáles requieren replanteamiento.

### 3.2.3 Rol del autor

El autor es a la vez diseñador del marco, implementador del sistema y evaluador del resultado. Esa triple condición introduce un sesgo de confirmación estructural que conviene reconocer antes de intentar neutralizarlo. La mitigación se articula en tres niveles: la **trazabilidad bidireccional como restricción dura** (A4), aplicada por un validador automático que expone cualquier huérfano sin intervención del autor y actúa como auditor externo de bajo coste; el **registro fechado de decisiones**, que documenta no solo qué se decidió sino qué alternativas se descartaron y por qué, auditable a posteriori por terceros; y la **declaración explícita de limitaciones** (§3.9 y Capítulo 11) con la misma honestidad que se reservaría a una solución ajena. Los tres mecanismos no eliminan el sesgo —ninguno puede— pero lo acotan a lo que un tercero independiente podría auditar sobre los artefactos versionados.

## 3.3 El V-Model clásico y sus supuestos implícitos

El V-Model, con raíz en la ingeniería de sistemas (Forsberg y Mooz, 1991), formalizado en ISO/IEC/IEEE 15288 y adoptado por ISO 26262, estructura el proceso en cinco niveles jerárquicos con correspondencia bidireccional entre especificación (rama descendente) y verificación/validación (rama ascendente).

<img src="../figures/fig_3_1_adopted_classical_v_model.png" alt="Figura 3.1 — V-Model adoptado por ISO 26262, instanciado sobre el caso de seguimiento de carril." width="480"/>

*Figura 3.1 — V-Model adoptado por ISO 26262 (simplificado), instanciado sobre el caso de seguimiento de carril.*

Opera sobre cinco supuestos que rara vez se explicitan pero que sostienen toda su estructura. Su identificación sistemática tiene antecedente fundacional en Salay, Queiroz y Czarnecki (2017); los supuestos S1–S5 que siguen son una reformulación operativa de aquel análisis, articulada de modo que cada uno admita una adaptación correspondiente en §3.4.

| Supuesto | Enunciado | Por qué falla ante un componente RL |
| --- | --- | --- |
| S1 | Cada módulo tiene una especificación completa y determinista escrita a priori | La policy no tiene especificación prediseñada: emerge del entrenamiento. No existe un documento «cuando la entrada es Y, produce Z» |
| S2 | El comportamiento es fielmente derivable de la especificación | El comportamiento es observable *post hoc* pero no predecible analíticamente |
| S3 | Los tests unitarios verifican el cumplimiento con cobertura finita | No hay salida «correcta» definida por entrada: solo salidas estadísticamente plausibles |
| S4 | La verificación estática basta para garantizar las propiedades | La policy puede acertar en test y fallar en operación por distribuciones de estado no cubiertas |
| S5 | El entorno operacional es suficientemente similar al de testing | El gap entre simulación y realidad puede ser grande y **silente** |

*Tabla 3.1 — Los cinco supuestos del V-Model clásico y su modo de fallo ante componentes aprendidos.*

El alcance cuantitativo del problema lo ilustra el hallazgo de Salay et al. sobre las 75 técnicas de software prescritas en la Parte 6 de ISO 26262: **cerca del 40 % no aplica a componentes ML sin modificación**, repartido entre técnicas directamente reutilizables, adaptables con modificación e inaplicables por estar orientadas a lenguajes imperativos. Ese vacío es operativo, no solo conceptual, y es lo que motiva un marco complementario.

Los cinco fallos no son un argumento para abandonar el V-Model sino para adaptarlo. El núcleo metodológico del trabajo consiste en **mantener la estructura del V —y con ella la coherencia con ISO 26262— introduciendo las modificaciones mínimas necesarias** para que la policy quepa dentro del ciclo sin romper la trazabilidad ni la honestidad del proceso.

## 3.4 Las cinco adaptaciones

### 3.4.1 A1 — Desdoblamiento del diseño de módulo

**Problema.** El nivel de diseño de módulo (L4) asume que cada módulo admite una especificación completa, determinista y escribible a priori. Para la policy el supuesto se rompe: no cabe escribir «la policy debe producir `a = f(s)` tal que…» porque `f` es el resultado de la optimización, no su entrada.

**Adaptación.** L4 se desdobla en dos subniveles conceptualmente distintos. **L4a — Cage Specification** es especificación clásica, determinista y modular: cada regla de la cage es una función pura, testeable, con entradas y salidas definidas, diseñada en sentido tradicional. **L4b — Training Specification** es una *meta-especificación*: no especifica el comportamiento de la policy sino **el proceso que la produce** —función de recompensa, espacios de estado y acción, ODD de entrenamiento, criterios de convergencia, algoritmo, restricciones activas durante el entrenamiento.

La separación es coherente con el principio de realización en tres etapas de ISO/IEC TR 5469:2024, que distingue adquisición desde entradas, inducción de conocimiento desde datos y generación de salidas; A1 lleva esa distinción al nivel del proceso de diseño. **Artefactos:** la especificación de la cage con sus reglas formalmente definidas (Capítulo 5) y la especificación de entrenamiento (Capítulo 7).

### 3.4.2 A2 — Del test unitario a la evaluación conductual

**Problema.** El test unitario verifica un módulo contra su especificación mediante casos con salidas esperadas. Para la policy no existe «salida esperada» para un estado dado: solo distribuciones plausibles condicionadas al estado.

**Adaptación.** El nivel se desdobla en correspondencia con A1. **L4a' — Cage Unit Tests**: tests unitarios clásicos sobre cada regla, con vectores de estado sintéticos, comportamiento determinista esperado y veredicto binario; idénticos en filosofía a los del V clásico. **L4b' — Policy Behavioral Evaluation**: evaluación estadística sobre distribuciones de estado —«en N estados muestreados del ODD, la policy produce acciones que satisfacen la propiedad X con frecuencia Y»—. No es verificación en sentido lógico, es **caracterización estadística del comportamiento**.

La adaptación reconoce que la verificación clásica no es aplicable a componentes aprendidos. La tesis no fuerza la metáfora: la sustituye por una herramienta apropiada, manteniendo la verificación clásica allí donde sigue siendo aplicable —la cage—. La asimetría es coherente con la distinción de elementos Clase I / Clase II del TR 5469: la cage opera como elemento de Clase I, la policy como elemento de Clase II.

### 3.4.3 A3 — Monitorización en operación como validación continua

**Problema.** El V-Model asume que la validación se completa antes del despliegue: una vez validado, el sistema se despliega y se mantiene. No hay nivel dedicado a validación continua posdespliegue.

**Adaptación.** Se añade un nivel horizontal —**Runtime Monitoring**— alimentado por los registros de intervención de la cage durante la operación, que realimenta la validación de forma continua. El nivel reconoce tres hechos propios de los sistemas con IA: la distribución operacional puede diferir de la de testing; pueden emerger modos de fallo no anticipados en el análisis de peligros; y la evidencia de seguridad debe acumularse con el tiempo.

En este trabajo el nodo de registro no es un componente auxiliar sino **el instrumento primario del nivel**: los registros que produce durante las campañas experimentales son evidencia de validación continua dentro de la ventana del proyecto, y en un despliegue real el mismo mecanismo generaría evidencia indefinidamente. La adaptación es coherente con la filosofía de SOTIF y con la reformulación del V-Model de Wang et al. (2024), y hereda de Mohseni et al. (2019) la categorización de la *función de monitorización* como categoría arquitectónica propia, llevándola un paso más allá: la eleva de mecanismo técnico a **nivel explícito del ciclo de vida**, con artefactos versionados y un papel definido en la matriz de trazabilidad.

### 3.4.4 A4 — Trazabilidad obligatoria como restricción dura

**Problema.** La trazabilidad entre niveles es recomendada pero, en la práctica, no exigida: puede existir lógica de pegamento sin requisito padre explícito. En sistemas clásicos resulta tolerable porque el comportamiento es inspeccionable en su totalidad.

**Problema específico en RL.** Cuando un componente es aprendido, la tentación de atribuir comportamientos a «propiedades emergentes» es alta. Sin trazabilidad estricta, **cualquier comportamiento puede justificarse retrospectivamente** como algo que la policy aprendió, lo que vacía de contenido la responsabilidad ingenieril.

**Adaptación.** La trazabilidad bidireccional pasa de buena práctica a restricción dura, con cinco obligaciones simultáneas: toda regla de la cage referencia al menos un requisito de seguridad; todo requisito tiene al menos una regla que lo implementa —o un argumento explícito de por qué no la requiere—; todo hazard tiene al menos un requisito que lo mitiga o un riesgo aceptado documentado; todo escenario referencia al menos un requisito que verifica; y toda métrica referencia al menos un requisito al que aporta evidencia. Un validador automatizado se ejecuta en cada cambio y **falla si detecta huérfanos en cualquier dirección**.

<img src="../figures/fig_3_2_check_traceability_flow.png" alt="Figura 3.2 — Flujo del validador de trazabilidad." width="470"/>

*Figura 3.2 — Flujo del validador de trazabilidad, en cuatro capas: carga de los documentos vivos; extracción de identificadores definidos por expresiones regulares sobre las cabeceras; cadena de restricciones sobre el grafo `H ↔ SR ↔ C ↔ SC` con el subgrafo `SR ↔ M` colgando del nodo de requisitos; y agregación final con tres salidas posibles —todas las comprobaciones pasan, huérfano o referencia inválida, o aviso en modo estricto.*

La consecuencia de diseño es indirecta pero importante: la restricción **simplifica la fase de análisis de peligros**, porque obliga a preguntarse «¿qué regla voy a tener para esto?» desde el primer requisito. El resultado son requisitos más operativos y menos abstractos. La filosofía es próxima a los patrones GSN de AMLAS, pero A4 da un paso más al convertir la trazabilidad en **propiedad verificable por herramienta** en lugar de en práctica documental revisable.

### 3.4.5 A5 — Validación operacional acotada y caracterización del gap

**Problema.** El test de aceptación asume un veredicto binario contra los requisitos de las partes interesadas y, de forma implícita, que las condiciones de prueba representan las operacionales. Para un sistema entrenado en simulación esto es falso: el gap es un riesgo de primer orden y un test superado en simulación **no implica** operación segura en el mundo real.

**Adaptación.** El nivel se reformula como **Validación Operacional** con dos componentes obligatorios: validación por escenarios ligados a requisitos, con métricas de cobertura sobre el ODD; y **caracterización explícita y cuantitativa del gap** entre entorno de entrenamiento y entorno operacional, por métrica y por modo de fallo relevante. La conclusión de validación deja de ser «el sistema es seguro» y pasa a ser: *el sistema satisface los requisitos bajo las condiciones del ODD X, con un gap medido de Y respecto de las condiciones de entrenamiento, y con los siguientes riesgos residuales documentados*.

### 3.4.6 Síntesis

| ID | Adaptación | Problema del V clásico | Solución | Artefacto |
| --- | --- | --- | --- | --- |
| A1 | Desdoblamiento del diseño de módulo | La policy no admite especificación a priori | Cage Spec (clásica) + Training Spec (meta-diseño) | Caps. 5 y 7 |
| A2 | Desdoblamiento del test unitario | La policy no admite test unitario clásico | Tests de la cage + evaluación conductual estadística | Suite de tests + Cap. 8 |
| A3 | Nivel de monitorización en operación | La validación estática es insuficiente | Registro de intervenciones como evidencia continua | Nodo de registro + datos |
| A4 | Trazabilidad obligatoria | Los huérfanos ocultan «propiedades emergentes» | Restricción dura bidireccional `H↔SR↔C↔SC↔M` | Matriz + validador |
| A5 | Validación acotada con gap | La prueba en simulación no representa la operación | Veredicto con límites + gap cuantificado | Caps. 9 y 10 |

*Tabla 3.2 — Las cinco adaptaciones al V-Model clásico.*

<img src="../figures/fig_3_3_adapted_v_model.png" alt="Figura 3.3 — V-Model adaptado." width="480"/>

*Figura 3.3 — V-Model adaptado a IA. En gris, los elementos heredados del V clásico; en color, los nuevos o modificados por las adaptaciones A1–A5.*

## 3.5 Operacionalización sobre el caso de estudio

### 3.5.1 Sistema bajo estudio y decisión arquitectónica

El sistema es un vehículo radiocontrolado a escala 1:14 con cámara frontal monocular como sensor primario, unidad inercial y encoder de motor, con cómputo embebido sobre una placa con soporte ROS2. Se desarrolla en dos plataformas paralelas: la **simulada** —Gazebo con integración ROS2 nativa, operada mediante una interfaz gymnasium–Gazebo–ROS2 que reutiliza un entorno construido por el autor en trabajo previo— y la **física**, sobre pista cerrada con iluminación controlada.

Una decisión arquitectónica es relevante para la metodología y no solo para el sistema. Inicialmente el proyecto adoptó una **descomposición modular explícita** —percepción, policy, cage, actuación y registro— con el componente aprendido en posición acotada, alineándose con la recomendación de Salay et al. (2017) de evitar el ML a nivel arquitectónico y limitarlo al de unidad. Posteriormente el sistema principal pasó a ser una variante **end-to-end con cámara**: la policy es una CNN que aprende la percepción y mapea imagen a acción.

La supersesión es segura porque **no se reemplaza la arquitectura de seguridad**: la cage se conserva y opera sobre su propio estimador de carril determinista —una cadena clásica de visión, separada de la CNN y por tanto ni verdad de referencia ni red aprendida—, de modo que los píxeles entran a la policy pero la envolvente razona sobre un estado **auditable e independiente**. Las adaptaciones que motivaban la decisión original siguen vigentes: A1, porque cage y policy siguen siendo módulos distintos; A2, porque la cage es verificable con independencia de la policy; y A4, porque la cadena de trazabilidad no cambia. El coste asumido es el otro motivo original —el mayor volumen de entrenamiento que exige el end-to-end—, presupuestado en el Capítulo 7. El track de estado se conserva **congelado como brazo de control** para aislar el coste de la percepción.

### 3.5.2 Mapeo del marco sobre el caso

| Nivel del V-Model adaptado | Artefacto en el caso de estudio | Capítulo |
| --- | --- | --- |
| L1 — Requisitos de las partes interesadas | ODD + caso de uso | 4 |
| L2 — Requisitos de seguridad del sistema | `SR-001..SR-014` derivados del HARA | 4 |
| L3 — Diseño arquitectónico | Grafo ROS2 (percepción, policy, cage, actuación, registro) | 5 |
| L4a — Cage Specification | Reglas `C-01..C-06` | 5 |
| L4b — Training Specification | Recompensa, ODD de entrenamiento, hiperparámetros, criterios | 7 |
| L5 — Implementación | Nodo de cage ROS2 + policy entrenada | 6, 7 |
| L4a' — Tests unitarios de la cage | Suite determinista de la cage | 6 |
| L4b' — Evaluación conductual de la policy | Análisis estadístico sobre la biblioteca de escenarios | 8 |
| L3' — Test de integración | Tests de la cadena completa | 6 |
| L2' — Test basado en escenarios | Familias `SC-NOM` / `SC-EDGE` / `SC-PERT` / `SC-FRONT` | 6, 8 |
| L1' — Validación operacional | Campaña + gap sim-to-real + veredicto por requisito | 9, 10 |
| Monitorización en operación (A3) | Nodo de registro + registros de intervención (transversal) | 5–10 |

*Tabla 3.3 — Mapeo del marco sobre el caso de estudio.*

El mapeo es la primera comprobación de que el marco es operacionalizable: **cada nivel del V tiene un artefacto identificable, un capítulo donde se desarrolla y una posición en la matriz de trazabilidad**.

### 3.5.3 Estructura por fases

El proyecto se organiza en siete fases secuenciales, cada una con entregables definidos y una **puerta de revisión** al cierre que decide si se procede a la siguiente. La estructura por fases es ortogonal al V-Model: una fase produce artefactos de varios niveles a la vez, y un nivel puede construirse a lo largo de varias fases. En resumen: la fase inicial establece marco y plantillas; la siguiente produce ODD, análisis de peligros y requisitos; la tercera desarrolla la cage y sus tests; la cuarta define la especificación de entrenamiento y la biblioteca de escenarios; la quinta ejecuta el entrenamiento y la evaluación conductual; la sexta despliega físicamente y caracteriza el gap; y la última consolida evidencia y cierra la matriz.

<img src="../figures/fig_3_4_project_phases.png" alt="Figura 3.4 — Fases del proyecto frente a niveles del V-Model adaptado." width="480"/>

*Figura 3.4 — Fases del proyecto frente a niveles del V-Model adaptado. La banda de monitorización se extiende horizontalmente porque su operatividad arranca en cuanto el nodo de cage existe y persiste hasta el cierre; la banda de trazabilidad muestra cómo la cadena `H ↔ SR ↔ C ↔ SC ↔ M` se completa fase por fase.*

Un punto merece énfasis porque es donde el marco deja de ser propuesta y pasa a ser práctica: **A4 entra plenamente en vigor desde la fase de análisis de peligros**. El validador se ejecuta sobre cada cambio del registro de hazards y de la especificación de requisitos, exigiendo que cada hazard enlace con al menos un requisito que lo mitigue —o con un riesgo aceptado documentado— y viceversa. Desde ese momento el ciclo «documentar → enlazar → validar» se ejecuta en cada commit.

## 3.6 Elecciones de instrumento

Esta sección justifica cada elección frente a las alternativas descartadas, dejando registro auditable de decisiones que de otro modo quedarían implícitas. El detalle completo —incluidas las alternativas evaluadas para middleware, biblioteca de RL, plataforma física e instrumentación— se recoge en el **Anexo C**.

**Simulador: Gazebo.** La elección difiere de la práctica dominante, donde CARLA es la referencia, y se sostiene en cuatro razones. *Integración ROS2 nativa*: Gazebo se co-desarrolla con ROS y comparte primitivas sin capas intermedias; como toda la arquitectura es ROS2 desde su concepción, alojar el simulador en el mismo grafo elimina superficie de fallo y reduce la ambigüedad sobre dónde ocurren latencias, lo que afecta directamente a la fidelidad de las métricas de integración. *Reutilización de trabajo previo*: el autor dispone de un entorno con el vehículo modelado y la pista configurada; reutilizarlo libera tiempo para el aporte metodológico, que es el verdadero objeto de la tesis —coherente con el enfoque de *design science*, donde la contribución no está en el instrumento. *Interfaz de entrenamiento disponible*, que permite separar limpiamente algoritmo, entorno y sistema, facilitando A1. *Requisitos de cómputo modestos*, relevante para una tesis individual sin infraestructura dedicada.

La elección conlleva dos compromisos que conviene reconocer. La **fidelidad visual de Gazebo es inferior** a la de los motores fotorrealistas; para una policy basada en cámara esto puede traducirse en un gap sim-to-real más pronunciado. La adaptación A5 está precisamente diseñada para hacer ese efecto visible y medirlo, no para ocultarlo. Y la comunidad de conducción autónoma usa mayoritariamente CARLA, por lo que no hay bibliotecas de escenarios reutilizables en formato Gazebo: la del proyecto debe construirse explícitamente.

Alternativas descartadas: **CARLA**, el candidato más fuerte, por su coste de cómputo y por requerir un puente ROS2 con complicaciones propias; **Highway-Env** y derivados, por carecer de sensores realistas y trabajar sobre observación abstracta, inadecuados para políticas basadas en cámara; **LGSVL**, discontinuado; y **AirSim**, de foco aeroespacial y desarrollo en pausa.

## 3.7 Cómo se evaluará el propio marco

La pregunta de este apartado es si la metodología resultó útil para producir el sistema, no si el sistema resultó útil: son separables, porque cabe un marco exitoso aplicado a un sistema modesto y también lo contrario. La evaluación se articula en cinco criterios, cada uno con un indicador medible al cierre:

1. **Integridad de la trazabilidad.** Indicador: huérfanos detectados por el validador en la última ejecución. Éxito: cero.
2. **Cobertura de requisitos por evidencia.** Indicador: porcentaje de requisitos con veredicto respaldado por evidencia cuantitativa. Éxito: el 100 % tiene veredicto, **aunque el veredicto sea negativo o parcial**. Es preferible un veredicto incómodo a una omisión.
3. **Anticipación de hazards.** Indicador: proporción de hazards que efectivamente se manifestaron frente a los no anticipados que emergieron. Éxito: la mayoría de los observados estaban anticipados y los no anticipados son auditables y categorizables.
4. **Coste de adopción.** Indicador: tiempo dedicado a artefactos del marco frente a artefactos técnicos puros. Éxito: coste proporcional al beneficio observado.
5. **Productividad de la matriz.** Indicador: cambios técnicos cuyo análisis de impacto aceleró la matriz. Éxito: casos documentados donde aportó valor observable.

La evaluación tiene tres límites declarados: es interna a un único proyecto y sin grupo de control, de modo que la inferencia es por plausibilidad y no por experimentación controlada; el sesgo del autor se acota pero no se elimina; y la ventana experimental es finita, cuando los beneficios de A3 se manifestarían en horizontes mucho mayores.

## 3.8 Relación con los estándares

El marco no sustituye a los estándares: los articula. Cada adaptación tiene un anclaje normativo identificable, resumido a continuación; el mapeo completo, cláusula por cláusula, se recoge en el **Anexo C**.

| Adaptación | Anclaje normativo principal |
| --- | --- |
| A1 — Cage Spec + Training Spec | TR 5469 §7 (principio de realización en tres etapas); PAS 8800 (adaptación del diseño de módulo) |
| A2 — Tests de cage + evaluación conductual | TR 5469 (elementos Clase I / Clase II); ISO 26262 Parte 6 para la parte clásica |
| A3 — Monitorización en operación | SOTIF (insuficiencia de la validación estática); Wang et al. (2024), fase de operación continua |
| A4 — Trazabilidad dura | ISO 26262 Parte 8 (gestión de requisitos); AMLAS (patrones GSN); UL 4600 (afirmación–argumento–evidencia) |
| A5 — Validación acotada + gap | SOTIF (condiciones no anticipadas); UL 4600 (límites declarados del safety case) |

*Tabla 3.4 — Anclaje normativo de las cinco adaptaciones.*

Una precisión sobre el análisis de peligros: el HARA adoptado es **simplificado** respecto del que prescribe ISO 26262, y no se desarrolla en paralelo al V sino **dentro** de él, ocupando exactamente la posición que el estándar reserva a la salida del HARA formal. Las simplificaciones y su justificación se detallan en el Capítulo 4.

## 3.9 Limitaciones de la metodología

Conviene declararlas en frío, antes de que el lector las identifique en caliente al final del trabajo.

- **Validez de constructo limitada por caso único.** La generalización se sostiene por plausibilidad estructural, no por evidencia multicaso. Mitigación: el Capítulo 12 distingue qué partes son trasladables y cuáles requieren replanteamiento.
- **Dependencia de una simulación de fidelidad visual moderada.** El entrenamiento se ejecuta enteramente en Gazebo, lo que puede acentuar el gap en las características visuales captadas por la cámara. Mitigación: A5 lo hace visible y el Capítulo 9 lo cuantifica; replicar el experimento sobre un simulador fotorrealista queda como extensión natural.
- **Las cinco adaptaciones no son exhaustivas.** Otras serían defendibles —por ejemplo un nivel dedicado a ingeniería de datos, siguiendo la filosofía data-céntrica del TR 5469 y de AMLAS—. Las cinco adoptadas se justifican individualmente, pero no se argumenta que sean las únicas posibles.
- **El marco no elimina el sesgo del autor**, solo lo expone a auditoría.

## 3.10 Transición

Definido el marco, los capítulos siguientes lo ejecutan. El Capítulo 4 materializa la rama izquierda superior del V —dominio operacional, análisis de peligros y derivación de requisitos— y produce los primeros artefactos sobre los que A4 opera como restricción dura. A partir de ahí, cada capítulo ocupa un nivel del V y cierra su correspondencia con el nivel simétrico de la rama derecha.
