# Capítulo 1 — Introducción

## 1.1 Contexto y motivación

La conducción autónoma ha pasado en una década de demostración de laboratorio a producto comercial parcial. Los sistemas avanzados de asistencia al conductor (ADAS) están desplegados a millones de unidades y los proyectos de nivel 4 operan ya en flotas restringidas (Kootbally et al., 2024). En ese movimiento se han consolidado en paralelo dos tendencias: la incorporación creciente de componentes basados en aprendizaje automático —redes profundas (Kuutti et al., 2019a) y, más recientemente, políticas entrenadas por refuerzo (García y Fernández, 2015)— en módulos críticos de percepción, predicción y decisión; y el endurecimiento de los marcos normativos de seguridad funcional.

<img src="../figures/fig_1_1_sae_automation_levels.png" alt="Figura 1.1 — Niveles SAE de automatización de la conducción." width="400"/>

*Figura 1.1 — Niveles SAE de automatización de la conducción.*

Ambas tendencias son individualmente sólidas y presentan una tensión estructural cuando confluyen. Los marcos clásicos —ISO 26262:2018 a la cabeza— fueron diseñados para sistemas cuyo comportamiento es derivable de una especificación escrita a priori, verificable mediante tests con salidas esperadas y validable estáticamente antes del despliegue. Los componentes aprendidos rompen los tres supuestos: su comportamiento emerge de una optimización estocástica, su salida no admite la noción clásica de «respuesta correcta» y su robustez fuera de la distribución de entrenamiento solo puede caracterizarse empíricamente (Wäschle et al., 2022; Paterson et al., 2025). El análisis sistemático más temprano de esta tensión es el de Salay, Queiroz y Czarnecki (2017), que identificó cinco áreas concretas de impacto sobre ISO 26262 —desde la aparición de nuevos tipos de hazard hasta la inaplicabilidad de aproximadamente el 40 % de las técnicas de software prescritas en su Parte 6— y constituye el antecedente conceptual directo de este trabajo. La industria ha respondido con dos estrategias parciales: contención mediante arquitecturas monitor-actuador o *safety cages* (Kuutti et al., 2019b, 2021) y caracterización mediante validación basada en escenarios (De Gelder et al., 2024). Su integración coherente dentro de un ciclo de desarrollo trazable sigue siendo un problema abierto.

En el plano normativo la respuesta institucional está en plena maduración. ISO 21448 (SOTIF) reconoce desde 2022 que la validación estática es insuficiente cuando el dominio operacional no puede especificarse exhaustivamente (Wang et al., 2024); ISO/IEC TR 5469:2024 ofrece la primera guía sistemática sobre IA en funciones de seguridad y clasifica los elementos de tecnología IA según su verificabilidad; UL 4600 formaliza el *safety case* como mecanismo central de evidencia (Koopman, 2023). Los tres son guías de alto nivel: enuncian principios, pero no prescriben un ciclo de vida concreto, ejecutable y aplicable a un proyecto real. Esta tesis se sitúa exactamente en esa brecha.

## 1.2 Planteamiento del problema

**Nivel general.** Las metodologías canónicas de seguridad funcional del automóvil —singularmente el V-Model adoptado por ISO 26262— no pueden aplicarse sin modificaciones a sistemas que incorporan componentes aprendidos por refuerzo. Aplicarlas tal cual conduce a uno de dos fracasos predecibles: forzar al componente RL a una especificación que no puede satisfacer, rompiendo la honestidad del proceso; o eximirlo del proceso, rompiendo la trazabilidad. Ninguno de los dos es aceptable en un sistema con consecuencias de seguridad.

**Nivel específico.** Las adaptaciones puntuales propuestas en la literatura —safety cages para contener policies (Kuutti et al., 2019b, 2021), filtros predictivos de seguridad (Tearle et al., 2021), evaluación basada en escenarios (De Gelder et al., 2024)— atacan facetas individuales del problema pero no se integran de oficio en un ciclo de vida unificado con trazabilidad bidireccional explícita. Existen propuestas que sí abordan el ciclo completo —notablemente Ullrich et al. (2025) sobre la expansión del V-Model clásico para sistemas con IA, y los trabajos previos de adaptación de ISO 26262 a ML (Salay et al., 2017; Vasudevan et al., 2021)—, pero permanecen en un plano abstracto, sin operacionalización ejecutable ni caso de aplicación documentado de extremo a extremo. El espacio que esta tesis ocupa es la materialización ejecutable de un marco de ese tipo, validada por aplicación a un caso concreto.

**Nivel concreto.** Para que un marco así sea evaluable debe ejecutarse sobre un caso suficientemente complejo como para exhibir los problemas característicos —especificación de comportamiento aprendido, gap sim-to-real, monitorización en operación— y suficientemente acotado como para ser abordable por un único investigador. El caso elegido es un sistema de seguimiento de carril sobre un vehículo a escala 1:14, entrenado en Gazebo mediante PPO sobre una interfaz gymnasium–Gazebo–ROS2. En su instanciación principal la *policy* es **end-to-end sobre cámara frontal** —una CNN que aprende la percepción y mapea imagen a acción— con la cage determinista operando sobre su **propio estimador de carril por visión**, separado de la red; esto introduce deliberadamente la percepción en el lazo, el caso más exigente. Una segunda instanciación sobre **vector de estado** privilegiado se conserva como brazo de control que aísla el efecto de la cage y cuantifica el coste de la percepción.

La pregunta de investigación principal se formula así:

> **¿Es posible adaptar el V-Model canónico de ISO 26262 mediante un conjunto finito y trazable de modificaciones, de modo que acomode componentes entrenados por refuerzo dentro de un ciclo de desarrollo con safety case, sin abandonar los principios de correspondencia bidireccional especificación↔V&V que dan al estándar su valor?**

Y, subordinada a ella, una pregunta de validación:

> **Cuando el marco resultante se aplica a un caso concreto de seguimiento de carril con policy PPO y cage de reglas, ¿produce evidencia coherente y trazable sobre el comportamiento del sistema, incluida una caracterización honesta del gap sim-to-real?**

## 1.3 Hipótesis

- **H1 (de constructo).** Es posible identificar un conjunto pequeño y enumerable de adaptaciones al V-Model clásico —aquí, cinco— que cubran los modos de fallo característicos de los componentes RL/IA sin romper la estructura general del estándar.
- **H2 (de operatividad).** Cada adaptación es operacionalizable como un conjunto concreto de artefactos —documentos, tests, validadores automáticos— producibles y mantenibles con esfuerzo proporcional al resto del proyecto, no como sobrecarga prohibitiva.
- **H3 (de utilidad).** El marco resultante, aplicado al caso de estudio, produce evidencia trazable que permite emitir un veredicto fundamentado sobre el comportamiento del sistema, incluidos los límites de validez de dicho veredicto.

Las tres se evalúan al cierre (Capítulo 11): H1 por inspección estructural del marco, H2 por el coste de adopción registrado en el log de decisiones a lo largo del proyecto, y H3 por la cobertura de veredictos alcanzada sobre los Safety Requirements.

## 1.4 Objetivos

### 1.4.1 Objetivo general

Diseñar, implementar y evaluar un marco metodológico —el *V-Model adaptado*— para el desarrollo de sistemas de conducción autónoma que incorporan componentes entrenados por refuerzo, articulando dentro de un ciclo único las prácticas de safety cage, validación basada en escenarios, monitorización en tiempo de ejecución y trazabilidad bidireccional, en coherencia con ISO 26262, ISO 21448, ISO/IEC TR 5469 y UL 4600.

### 1.4.2 Objetivos específicos

- **OE1.** Caracterizar formalmente los supuestos implícitos del V-Model clásico que fallan al introducir un componente entrenado por refuerzo en un módulo de seguridad. *(§3.3.)*
- **OE2.** Proponer y justificar un conjunto finito de adaptaciones que ataquen esos supuestos manteniendo la coherencia con los estándares. *(§3.4.)*
- **OE3.** Operacionalizar cada adaptación en artefactos concretos —especificaciones, tests, validadores, métricas— y definir su flujo de producción. *(§3.5; capítulos 4–8 como ejecución.)*
- **OE4.** Aplicar el marco al caso de estudio, en su instanciación principal con cámara y en la de vector de estado como línea base, hasta obtener un sistema funcional, evaluable y con trazabilidad completa. *(Capítulos 4–8.)*
- **OE5.** Caracterizar cuantitativamente el gap entre el entorno de entrenamiento y el operacional, cumpliendo la adaptación A5. *(Capítulo 9.)*
- **OE6.** Emitir un veredicto fundamentado sobre el cumplimiento de los Safety Requirements, con declaración explícita de sus límites de validez. *(Capítulo 10.)*
- **OE7.** Evaluar el propio marco: coste de adopción, cobertura y criterios bajo los cuales se considera suficiente o insuficiente. *(Capítulo 11.)*

## 1.5 Aportaciones

La aportación principal es **metodológica**, no técnica. El sistema de seguimiento de carril resultante no constituye por sí mismo una contribución relevante —existen variantes mejor entrenadas sobre vehículos más capaces—. Lo que esta tesis aporta es el marco que ese sistema materializa y la evidencia documentada de su aplicación.

- **A1 — Marco metodológico unificado.** Un V-Model adaptado con cinco modificaciones explícitas: desdoblamiento del diseño de módulo en *Cage Specification* y *Training Specification*; desdoblamiento del test unitario en *Cage Unit Tests* y *Policy Behavioral Evaluation*; introducción de un nivel de monitorización en operación como validación continua; trazabilidad bidireccional como restricción dura; y reformulación de la validación operacional con caracterización explícita del gap sim-to-real.
- **A2 — Operacionalización ejecutable.** Cada modificación se acompaña de los artefactos que la materializan, con plantillas reutilizables y validadores automáticos —en particular el verificador de trazabilidad que la convierte en una restricción mecánica de puerta.
- **A3 — Caso de estudio completo y reproducible.** Aplicación del marco a un sistema implementado desde cero, en dos instanciaciones cuyo contraste aísla el coste de la percepción por cámara, con artefactos versionados, scripts de entrenamiento y evaluación y datos de ejecución publicados.
- **A4 — Caracterización empírica del gap sim-to-real** en peldaños de fidelidad creciente: Gazebo (campaña de referencia) → plataforma física.
- **A5 — Auto-evaluación del marco:** coste de adopción, puntos donde funcionó como se esperaba y puntos donde reveló limitaciones, como evidencia para refinamientos posteriores por terceros.

## 1.6 Alcance y limitaciones

### 1.6.1 Alcance

El marco se aplica a un **único sistema** —seguimiento de carril con PPO y cage— sobre una **única plataforma** —vehículo RC 1:14 en pista controlada—, sin comparación contra un sistema baseline desarrollado con V clásico. La función objetivo es seguimiento de carril en pista delimitada con iluminación y meteorología controladas: no se aborda planificación, interacción con otros vehículos ni operación en vía pública. Conceptualmente el sistema se enmarca en el espacio de funciones de **nivel SAE 2**; la extensión a niveles 4–5 queda fuera del alcance.

### 1.6.2 Limitaciones reconocidas

- **Sesgo del autor.** Una misma persona diseña, implementa y evalúa el marco, lo que introduce sesgo de confirmación. Mitigación parcial: trazabilidad estricta auditable y registro de decisiones fechado.
- **N = 1.** No cabe derivar conclusiones generales sobre la utilidad del marco a partir de un único caso. La generalización se argumenta por *plausibilidad estructural* —las adaptaciones atacan supuestos que fallan en cualquier sistema con componente aprendido—, no por evidencia estadística.
- **Coste de adopción no comparado.** Se documenta el esfuerzo dedicado a los artefactos del marco, pero sin grupo de control.
- **Adaptaciones no exhaustivas.** Las cinco propuestas son las que el autor considera más relevantes para el caso; otras serían defendibles.
- **Plataforma a escala.** Los hallazgos sobre el gap sim-to-real son específicos de un vehículo 1:14 en pista controlada.

Estas limitaciones se desarrollan en §3.9 y en el Capítulo 11.

### 1.6.3 Abstracciones deliberadas del caso de estudio

Más allá de lo anterior, el caso incorpora abstracciones técnicas que no son simplificaciones de conveniencia sino **controles experimentales**: cada una fija una capa del sistema para poder aislar la que esta tesis estudia. El sistema se entiende como una pila:

> `percepción → estado (ey, epsi, v, κ) → [ policy + cage ] → actuación → dinámica`

La aportación reside en el bloque `[policy + cage]`, y las reglas de la cage se definen sobre el estado abstracto en ambos tracks. Las abstracciones son tres.

**Dos tracks de observación.** El sistema principal es el track de **cámara**: la policy conduce desde la imagen y la cage lee su propio estimador CV determinista, de modo que la percepción entra en el alcance como contribución central. En paralelo, el track de **estado** obtiene `(ey, epsi, v)` proyectando la pose verdadera sobre la línea central, fijando la capa de percepción para aislar el efecto de la cage y medir su coste (el delta entre ambos). La cage es agnóstica al origen del estado y los veredictos de seguridad se miden siempre sobre la pose verdadera: salir del carril es un hecho físico, no un artefacto del estimador.

**Autoridad de la policy sobre la velocidad.** El trabajo recorre dos contratos. Durante la mayor parte del proyecto el componente aprendido controla **solo la dirección** y la velocidad se mantiene constante, lo que reduce el problema a control lateral y preserva la separación «la recompensa guía, la cage garantiza». La campaña de referencia final amplía la acción a **dirección más tracción**, de modo que la policy adquiere autoridad longitudinal; el Capítulo 8 muestra que esa autoridad cambia el papel de la cage de forma medible.

**Dos geometrías de pista y una plataforma.** El track de estado se valida sobre un óvalo (R = 0,8 m) y el de cámara sobre el circuito `complex_b`, sinuoso y auto-aproximante (perímetro 19,22 m), ambos sobre el vehículo 1:14. La generalización a otras geometrías se argumenta por plausibilidad estructural, reforzada por esa segunda geometría, no por evidencia exhaustiva.

Estas fronteras no debilitan la afirmación central —que la cage añade seguridad medible y trazable a un componente aprendido— sino que la hacen *limpia*: al fijar las capas vecinas, el efecto de la cage puede atribuirse sin confusión en lugar de quedar enmascarado por el ruido de la percepción o por la transferencia a hardware. Cada frontera vuelve a tratarse, en su contexto experimental, en §8.2 y §8.8.

## 1.7 Estructura del documento

La tesis se organiza en doce capítulos agrupados en cuatro bloques. El **Bloque I — Marco** comprende esta introducción, el estado del arte (Capítulo 2) y la metodología (Capítulo 3), que constituye la aportación académica central. El **Bloque II — Especificación** cubre el dominio operacional, el análisis de peligros y la derivación de requisitos (Capítulo 4) y el diseño arquitectónico con la especificación de la cage (Capítulo 5). El **Bloque III — Implementación y evaluación** recorre la implementación y verificación (Capítulo 6), la especificación de entrenamiento y su ejecución (Capítulo 7), la campaña de evaluación experimental (Capítulo 8) y la caracterización del gap sim-to-real en peldaños de fidelidad creciente (Capítulo 9). El **Bloque IV — Cierre** presenta la validación operacional y la tabla consolidada de veredictos (Capítulo 10), la discusión del propio marco frente a sus criterios (Capítulo 11) y las conclusiones y trabajo futuro (Capítulo 12).

Los anexos recogen el material de evidencia que sustenta el cuerpo sin interrumpirlo: convenciones de identificadores, registro de peligros completo, especificación de requisitos con su rationale, catálogo de escenarios, catálogo de métricas, matriz de trazabilidad, tablas completas de las campañas y registro de decisiones de diseño.
