# Capítulo 10 — Validación operacional

## 10.1 De los resultados a una declaración de validación

Los capítulos anteriores producen mediciones. Este capítulo las convierte en una declaración de validación que incluye sus propios límites. Es la primera mitad de la adaptación A5 llevada a la práctica: la conclusión ya no es «el sistema es seguro», sino una afirmación acotada sobre qué requisitos se cumplen, en qué dominio, con qué evidencia y con qué riesgos residuales declarados.

## 10.2 La evidencia

La declaración se basa en tres bloques de evidencia. Todos tienen artefactos versionados, y cada ejecución guarda sus metadatos de reproducibilidad: revisión del código, identificador de la configuración de la cage, identificador del punto de control, semilla y marca de tiempo.

El brazo de percepción perfecta aporta 1.260 corridas con un veredicto global satisfecho. Sirve de control: muestra lo que pasa cuando la percepción no es un problema. El brazo de cámara aporta las campañas de escenarios sobre una política que aprendió desde píxeles, y termina con la campaña de referencia de 1.890 corridas sin errores que sostiene el veredicto de este capítulo. El estudio de variación entre semillas muestra que el comportamiento no es el mismo cuando se repite el procedimiento de entrenamiento.

**Hay evidencia física, pero es de puesta en marcha y no sirve como evidencia de veredicto.** La cadena ha funcionado sobre el vehículo real y ha conducido 18,05 m del circuito en un solo tramo sin activar ninguna regla de seguridad (Capítulo 9), pero ninguna corrida se hizo bajo el protocolo de la biblioteca, en enforcement y con el contrato de percepción con el que se puntuaron las campañas. Por eso la columna física de la tabla siguiente se marca como no ejecutada. Es distinto de decir que no hay datos, y más preciso: haber conducido no es lo mismo que haber puntuado, y llenar la columna con medidas tomadas fuera del protocolo sería justo el tipo de afirmación que el marco quiere evitar. Los límites que esto impone se enuncian en §10.4d–e.

## 10.3 Tabla final de veredictos

| Requisito | Clase | Brazo de control | **Brazo de cámara (campaña de referencia)** | Físico *(fuera de alcance — §12.4 T2)* |
| --- | :-: | --- | --- | --- |
| SR-001 desviación lateral | A | Satisfecho | Satisfecho | no ejecutado |
| SR-002 estabilidad de rumbo | A | Satisfecho | Literal: fallo (cláusula de recuperación); criterio propio: satisfecho | no ejecutado |
| SR-003 tiempo predictivo a salida | A | Satisfecho | Literal: fallo (misma cláusula); criterio propio: satisfecho | no ejecutado |
| SR-004 techo de velocidad | A | Satisfecho | Satisfecho (regla no activada en campaña; ver §10.4b y §10.4f) | no ejecutado |
| SR-005 parada de emergencia | A | Satisfecho | Satisfecho | no ejecutado |
| SR-006 suavidad de actuación | B | Satisfecho (métrica propia) | Satisfecho (840/840 en enforcement) | no ejecutado |
| SR-007 validez de estado | A | Satisfecho | Satisfecho | no ejecutado |
| SR-008 parada externa | A | Satisfecho | Satisfecho | no ejecutado |
| SR-009 *liveness* | B | Abstención documentada | Satisfecho (mediciones propias) | no ejecutado |
| SR-010 composición de reglas | B | Abstención documentada | No satisfecho — hallazgo, no bloquea | no ejecutado |
| SR-011 varianza de rumbo | B | Satisfecho | Literal: fallo (misma cláusula heredada); criterio propio: satisfecho (3,77° < 5°) | no ejecutado |
| SR-012 seguimiento bajo cámara degradada | A | n/a | Satisfecho | no ejecutado |
| SR-013 degradación segura de percepción | A | n/a | Satisfecho | no ejecutado |
| SR-014 plausibilidad del estimador | A | n/a | Satisfecho | no ejecutado |

*Tabla 10.1 — Veredictos finales por requisito. La columna física no se puntúa en este trabajo: ninguna corrida sobre hardware se hizo bajo el protocolo de escenarios, y todas se hicieron en monitorización (§10.4e). Se marca como «no ejecutado» y no como «pendiente», para no dar a entender que hay una medición en curso.*

<img src="../figures/fig_10_1_traceability_case_sr001.png" alt="Figura 10.1 — La cadena de trazabilidad instanciada de punta a punta." width="520"/>

*Figura 10.1 — Una fila de la Tabla 10.1 seguida hacia atrás hasta la evidencia que la sostiene. El compromiso central del trabajo, `Peligro → Requisito → Regla → Escenario → Métrica → Evidencia → Veredicto`, aplicado al requisito más importante. Cada eslabón es un identificador en un artefacto versionado, y `check_traceability.py` bloquea la puerta de revisión si aparece un huérfano en cualquiera de los dos sentidos. Así es como una casilla de esta tabla se puede auditar. La evidencia es la campaña de referencia (`campaign_2d_ppo550k`, `2-D PPO 550k`; Tabla 7.1).*

Mirándola por grupos: trece de los catorce requisitos se cumplen según su criterio documentado. Uno no se cumple. Es de clase B, no bloquea el veredicto y se informa tal cual, sin justificarlo. Ninguno se queda sin veredicto, fuera de la tabla o pendiente en la columna de simulación. El criterio de cobertura de la evaluación del marco, que pedía un veredicto para el 100 % de los requisitos aunque fuera incómodo, se cumple, y se cumple incluyendo el veredicto incómodo.

Dos grupos de casillas necesitan un comentario. Los tres requisitos con fallo literal (SR-002 y SR-003, de clase A, y SR-011, de clase B, los tres por la misma cláusula heredada de §8.3.2) mantienen ese fallo en el registro junto a la explicación. No se reescriben. Y el techo de velocidad se marca como satisfecho con una condición importante, que se explica en la declaración siguiente: se cumple sin haberse probado nunca.

## 10.4 Declaración de validación acotada

> **Declaración.** Dentro del dominio operacional especificado, sobre un único circuito en simulación, con la política de cámara bidimensional elegida por evaluación en lazo cerrado y con la configuración de la cage identificada por su *hash*, el sistema cumple trece de sus catorce requisitos de seguridad según su criterio documentado. El veredicto global literal de la campaña es `NO SATISFECHO`, y se debe por completo a una cláusula de rendimiento (tiempo de recuperación del rumbo) en un solo escenario, sin que se incumpla ninguna condición de seguridad de clase A.
>
> **Dentro del dominio operacional y con la cage activa, no hay ningún contacto con el borde de la calzada** en las 555 corridas de enforcement que empiezan dentro de él. La misma política sin la cage comete sesenta sobre esas mismas 555. La afirmación se acota al dominio a propósito: en las 390 corridas de enforcement que empiezan fuera quedan 56 contactos (Tabla 8.3). El requisito que no se cumple es el de composición coherente de reglas cuando se activan a la vez. Es de clase B, se midió con dos políticas distintas, se redujo a la mitad con un mejor entrenamiento y sigue siendo del mismo tipo. Se declara como limitación de diseño de la envolvente y como trabajo futuro.

**Límites explícitos de esta declaración.** Se listan aquí, como parte de la declaración y no en una sección aparte, porque cada uno limita una afirmación concreta de las de arriba.

**(a) Alcance.** La declaración vale en simulación, sobre un circuito y con una semilla en la campaña de veredicto. La variación entre semillas se estudia por separado y no es uniforme.

**(b) Lo que no se probó.** El techo de velocidad de la cage no se activó ni una vez en las 1.890 corridas, porque la velocidad de operación de la política queda por debajo del límite inferior de esa envolvente. El requisito se cumple de forma trivial, y su regla nunca se ha probado desde arriba. Es una limitación del punto de operación, no de la especificación, y se declara para que no se lea como evidencia de robustez.

**(c) La dependencia medida.** En esta política, mantenerse en el carril en las curvas más cerradas depende del limitador de tasa. La dependencia está medida y su origen es una inferencia.

**(d) Transferencia.** La evidencia física existe pero no está puntuada, y ninguna afirmación de esta declaración se aplica a la plataforma real. Lo que sí se puede afirmar, y se afirma en el Capítulo 9 y no aquí, es que la política que sostiene este veredicto no transfiere al vehículo real, y que la que sí transfiere es un reentrenamiento posterior. Lo que se valida en esta declaración y lo que conduce en hardware no son lo mismo.

**(e) Lo que el hardware no ha probado en absoluto, que es el mayor límite de este trabajo.** Todas las corridas físicas se hicieron en modo monitorización. En ese modo la cage evalúa, publica y registra sus reglas, pero no cambia la acción, así que la acción segura coincide con la acción cruda de la política en todos los ciclos registrados. Por tanto, la envolvente nunca ha actuado sobre el vehículo real. Lo que mide el peldaño físico es lo que la cage *habría dicho*, más el coste en disponibilidad de su enclavamiento de emergencia. Lo que no mide es cómo cambia la cage la trayectoria de un vehículo físico, que es exactamente la propiedad que esta declaración certifica en simulación. Es un límite de alcance y no un resultado negativo: no hay evidencia física en contra de la envolvente, tampoco a favor, y no la habrá hasta que se haga una corrida puntuada en enforcement.

**(f) Una regla que el hardware sí puso a prueba.** El techo de velocidad se declara satisfecho aquí sin haberse activado ni una vez, y §9.3.5 añade dos medidas físicas que limitan esta casilla sin volver a puntuarla: en la configuración desplegada la regla no puede activarse sobre movimiento comandado, y las únicas veces que sí se activó fue por errores de velocidad del sensor de pose. Para esta declaración eso significa una cosa concreta y limitada: el veredicto de este requisito depende por completo de que su condición de disparo nunca se alcanzó en simulación, y no de evidencia de que la regla actúe bien cuando se alcanza. Es el requisito con el respaldo más débil de la tabla, y se señala así.

## 10.5 De la declaración a la tesis metodológica

La declaración de arriba es lo que el marco prometía producir: no un juicio de sí o no, sino un enunciado acotado que se puede seguir hasta su evidencia y que dice claramente lo que no cubre. Su forma importa tanto como su contenido, porque es lo que separa una validación honesta de un sello de aprobación. Cada afirmación se puede seguir hacia atrás hasta un conjunto de corridas registradas, y cada límite está escrito dentro de la declaración, no en una sección aparte que un lector con prisa podría saltarse. Los tres resultados desfavorables —un veredicto global negativo, un requisito no cumplido y una regla que nunca se probó— están dentro de ella, y el Capítulo 11 evalúa qué dice eso sobre el marco.
