# Capítulo 10 — Validación operacional

## 10.1 De resultados a declaración

Los capítulos anteriores producen mediciones; este las convierte en una **declaración de validación** con sus límites incorporados al enunciado. Es la materialización de la primera mitad de la adaptación A5: la conclusión de validación deja de ser «el sistema es seguro» y pasa a ser una afirmación acotada sobre qué requisitos se satisfacen, bajo qué dominio, con qué evidencia y con qué riesgos residuales declarados.

## 10.2 Inventario de evidencia

La declaración descansa sobre tres bloques de evidencia, todos con sus artefactos versionados y su metadato de reproducibilidad —revisión de código, identificador de la configuración de la cage, identificador del punto de control, semilla y marca temporal— registrado ejecución por ejecución.

El **brazo de percepción perfecta** aporta 1.260 corridas con veredicto global satisfecho, y su función es de control: fija lo que ocurre cuando la percepción no es un problema. El **brazo de cámara** aporta las campañas de escenarios sobre política aprendida desde píxeles, culminando en la **campaña de referencia de 1.890 corridas sin errores** que sostiene el veredicto de este capítulo. El **estudio de variabilidad entre semillas** aporta la caracterización de que el comportamiento no es homogéneo entre repeticiones del procedimiento de entrenamiento.

No hay evidencia física. La columna correspondiente de la tabla siguiente está vacía por esa razón, y permanecerá vacía hasta que exista.

## 10.3 Tabla consolidada de veredictos

| Requisito | Clase | Brazo de control | **Brazo de cámara (campaña de referencia)** | Físico |
| --- | :-: | --- | --- | --- |
| SR-001 desviación lateral | A | Satisfecho | **Satisfecho** | pendiente |
| SR-002 estabilidad de rumbo | A | Satisfecho | Literal: fallo (cláusula de recuperación); **criterio propio: satisfecho** | pendiente |
| SR-003 tiempo predictivo a salida | A | Satisfecho | Literal: fallo (misma cláusula); **criterio propio: satisfecho** | pendiente |
| SR-004 techo de velocidad | A | Satisfecho | **Satisfecho** (regla nunca activada; ver §10.4) | pendiente |
| SR-005 parada de emergencia | A | Satisfecho | **Satisfecho** | pendiente |
| SR-006 suavidad de actuación | B | Satisfecho (métrica propia) | **Satisfecho** (840/840 en enforcement) | pendiente |
| SR-007 validez de estado | A | Satisfecho | **Satisfecho** | pendiente |
| SR-008 parada externa | A | Satisfecho | **Satisfecho** | pendiente |
| SR-009 *liveness* | B | Abstención documentada | **Satisfecho** (metrología propia) | pendiente |
| SR-010 composición de reglas | B | Abstención documentada | **No satisfecho** — hallazgo, no vetante | pendiente |
| SR-011 varianza de rumbo | B | Satisfecho | Satisfecho sobre métrica propia (3,77° < 5°) | pendiente |
| SR-012 seguimiento bajo cámara degradada | A | n/a | **Satisfecho** | pendiente |
| SR-013 degradación segura de percepción | A | n/a | **Satisfecho** | pendiente |
| SR-014 plausibilidad del estimador | A | n/a | **Satisfecho** | pendiente |

*Tabla 10.1 — Veredictos consolidados por requisito.*

La lectura por subconjuntos: **trece de catorce requisitos con veredicto satisfecho** sobre su criterio documentado; **uno no satisfecho**, de clase B y no vetante, reportado como tal y no reconciliado; **ninguno sin veredicto, omitido ni pendiente** en la columna de simulación. La cobertura del criterio de evaluación del marco que exigía veredicto para el 100 % de los requisitos —aunque el veredicto fuera incómodo— se cumple, y se cumple incluyendo el veredicto incómodo.

Dos casillas merecen nota. Los dos requisitos con **fallo literal** conservan el fallo en el registro junto a su reconciliación; no se reescriben. Y el techo de velocidad se marca satisfecho con una precisión importante, que se desarrolla en la declaración siguiente: se satisface **sin haber sido ejercitado**.

## 10.4 Declaración de validación acotada

> **Declaración.** Bajo el dominio operacional especificado, realizado sobre un único circuito en simulación, con la política de cámara de acción bidimensional seleccionada por evaluación en lazo cerrado y con la configuración de cage identificada por su *hash*, el sistema **satisface trece de sus catorce requisitos de seguridad sobre su criterio documentado**. El veredicto global literal de la campaña es `NO SATISFECHO`, imputable en su totalidad a una cláusula de rendimiento —tiempo de recuperación de rumbo— sobre un único escenario, sin que ningún predicado de seguridad de clase A resulte incumplido.
>
> **Dentro del dominio operacional y con la cage activa no se registra ningún contacto con el borde de la calzada** a lo largo de 945 corridas de enforcement; la misma política sin la cage comete sesenta. El requisito no satisfecho es el de **consistencia de composición de reglas bajo co-activación simultánea**, de clase B, medido sobre dos políticas distintas, atenuado a la mitad por un mejor entrenamiento y persistente en naturaleza; se declara como limitación de diseño de la envolvente y como trabajo futuro.

**Límites explícitos de esta declaración.** *Sobre el alcance:* es válida en simulación, sobre un circuito y con una semilla en la campaña de veredicto; la variabilidad entre semillas está caracterizada por separado y **no es homogénea**. *Sobre lo no ejercitado:* el techo de velocidad de la cage **no se activó ni una sola vez** en las 1.890 corridas, porque el punto de operación de la política queda por debajo del suelo de esa envolvente; el requisito se satisface trivialmente y su regla permanece **sin probar desde arriba**. Es una limitación del punto de operación, no de la especificación, y se declara para que no se lea como evidencia de robustez. *Sobre la dependencia medida:* el mantenimiento del carril en las curvas más cerradas descansa, en esta política, sobre el limitador de tasa; la dependencia está medida y su origen es inferido. *Sobre la transferencia:* no existe evidencia física, y ninguna afirmación de esta declaración se extiende a la plataforma real.

## 10.5 De la declaración a la tesis metodológica

La declaración anterior es el producto que el marco prometía: no un juicio binario sino un **enunciado acotado, trazable hasta la evidencia que lo sostiene y explícito sobre lo que no cubre**. Su forma es tan relevante como su contenido, porque es exactamente lo que distingue una validación honesta de un sello de aprobación: cada afirmación puede seguirse hacia atrás hasta un conjunto de corridas registradas, y cada límite está enunciado dentro de la declaración en lugar de en una sección aparte que el lector apresurado podría saltarse.

Merece subrayarse un punto que el Capítulo 11 retoma. El marco produjo un veredicto global negativo, un requisito no satisfecho y una regla nunca ejercitada, y los tres están en la declaración. Un marco de trazabilidad que solo produjera resultados favorables sería sospechoso por construcción; el valor de este descansa precisamente en que los desfavorables sobrevivieron hasta la página final.
