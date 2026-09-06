# Capítulo 5 — Diseño arquitectónico y especificación de la cage

## 5.1 Propósito del capítulo

Este capítulo ocupa los niveles de diseño arquitectónico (L3) y de especificación de módulo en su vertiente clásica (L4a). Produce el artefacto donde la adaptación A1 se materializa por primera vez: la Cage Specification, una especificación determinista y modular escrita en sentido tradicional, frente a la especificación de proceso que el Capítulo 7 dedicará a la policy.

Se desarrollan aquí la filosofía de diseño de la envolvente de seguridad, los retos conceptuales que su construcción plantea, la derivación de las reglas desde los requisitos, el diseño de cada regla, la parametrización versionada y la arquitectura ROS2 que la aloja. La especificación completa de parámetros, con la derivación numérica de cada umbral y su estado de calibración, se recoge en el Anexo E.

## 5.2 Filosofía de diseño: la cage como escudo en tiempo de ejecución

### 5.2.1 Elección del mecanismo

El espacio de mecanismos para hacer segura una policy aprendida admite, según el Capítulo 2, cuatro familias. La tesis adopta el escudo en tiempo de ejecución como mecanismo dominante, por tres razones.

Primera, verificabilidad. Una cage de reglas escritas a mano es un componente clásico: admite test unitario determinista, análisis estático e inspección. En los términos del TR 5469 es un elemento de Clase I, mientras la policy es de Clase II. Esa asimetría es precisamente lo que permite que el sistema conjunto conserve un núcleo verificable.

Segunda, independencia del entrenamiento. Una garantía obtenida por modificación del objetivo de aprendizaje es estadística y está condicionada a la distribución de entrenamiento; una garantía obtenida por filtrado en tiempo de ejecución se sostiene sobre el estado observado en cada ciclo, con independencia de cómo se haya entrenado la policy —y, por tanto, sigue en pie si la policy se reentrena, se sustituye o se degrada.

Tercera, compatibilidad con el marco. El escudo produce, como subproducto natural de su operación, un registro de intervenciones que es exactamente la evidencia que el nivel de monitorización en operación (A3) necesita. La cage no es solo un mecanismo de seguridad: es el instrumento de medida del comportamiento de la policy.

### 5.2.2 Lo que la cage no es

Tres delimitaciones evitan lecturas excesivas. La cage no es un controlador: no autoría comportamiento, corrige comandos inseguros; si la policy conduce bien, la cage debe permanecer inactiva, y el Capítulo 8 mostrará que en condiciones nominales limpias así ocurre. La cage no es una garantía formal: sus reglas son heurísticas con umbrales derivados de requisitos, no invariantes demostradas sobre un modelo dinámico; lo que ofrece es contención medible, no prueba. Y la cage no elimina la necesidad de entrenar bien: es la última línea, no la primera, y un sistema cuya seguridad dependa por completo de ella sería un sistema mal entrenado —afirmación que el Capítulo 8 obliga a matizar de forma incómoda.

## 5.3 Retos conceptuales del diseño

La construcción de una envolvente de reglas plantea seis problemas que no son de implementación sino de diseño, y cuya resolución explícita es parte de la aportación del capítulo.

**Prioridad y orden entre reglas.** Varias reglas pueden activarse en el mismo ciclo sobre el mismo canal de actuación. Se adopta una cadena de evaluación de orden fijo y declarado, con el limitador de tasa primero —acota el comando crudo antes de que ninguna regla de seguridad razone sobre él— y el modo de emergencia último —porque debe poder sobrescribir cualquier corrección previa. Entre medias, la regla de límite lateral se evalúa después de la de rumbo, de modo que la cota más dura sobre la variable más crítica tenga la última palabra entre las reglas operacionales.

**Diseño de la acción correctiva.** Una corrección puede sumarse al comando de la policy o sobrescribirlo. Se elige sobrescritura, para evitar que policy y cage compitan en el mismo espacio y produzcan una suma que ninguna de las dos pretendía. La magnitud de la corrección es proporcional al exceso sobre el umbral, no un valor fijo: una corrección constante generaría discontinuidades en la frontera de activación.

**Reglas reactivas y reglas predictivas.** Las reglas que observan el estado actual actúan tarde por construcción: cuando el offset alcanza el umbral, la dinámica ya está comprometida. Se añade por ello una regla predictiva, que propaga el estado a corto horizonte y actúa sobre el tiempo estimado hasta la salida de carril. Reactivo y predictivo son complementarios: el primero acota el presente, el segundo compra margen.

**Histéresis y prevención de conmutación espuria.** Un umbral único produce activación y desactivación repetidas en su entorno, con un comando resultante oscilante que es en sí mismo un peligro. Cada regla con umbral incorpora una banda de histéresis: activa por encima de un valor y desactiva por debajo de otro menor, con memoria de estado entre ciclos.

**Saturación y resolución de conflictos.** La composición de correcciones puede exceder el rango físico del actuador. La saturación se aplica al final de la cadena, sobre el comando compuesto, no regla a regla, para que el resultado sea predecible con independencia de cuántas reglas hayan intervenido.

**Modo de emergencia y validez del estado.** El modo de emergencia se define con entrada por *trigger* compuesto, comportamiento determinista —desaceleración a tasa mínima con dirección congelada— y salida explícita. Sus disparadores incluyen no solo el estado compuesto irrecuperable, sino también la invalidez del estado mismo: observación obsoleta, campos fuera de rango plausible o pérdida de la percepción. Esto último es la cadena de confianza del sistema: si la cage no puede confiar en el estado que observa, la respuesta segura no es corregir el comando sino detener el vehículo de forma controlada.

## 5.4 De los requisitos a las reglas

El mapeo de requisitos a reglas sigue un procedimiento explícito: para cada requisito se identifica la variable observable que expresa su predicado, el mecanismo capaz de mantenerla dentro de límites y el canal de actuación sobre el que actuar. Cuando no existe tal mecanismo sin violar la filosofía de la cage —el caso de la *liveness*, donde una regla que forzase tracción positiva estaría autorizando comportamiento en lugar de corregirlo— el requisito se implementa en otro nivel y así se declara.

| Requisito | Regla | Variable observada | Canal |
| --- | --- | --- | --- |
| SR-001 | C-01 — límite lateral duro | offset lateral | dirección |
| SR-002 | C-02 — límite de error de rumbo | error de rumbo | dirección |
| SR-003 | C-03 — límite predictivo de tiempo a salida | tiempo proyectado a cruce | dirección |
| SR-004 | C-04 — techo de velocidad | velocidad y curvatura local | tracción |
| SR-005, SR-007, SR-008, SR-013, SR-014 | C-05 — modo de emergencia | estado compuesto, validez, salud del estimador | ambos |
| SR-006, SR-011 | C-06 — limitador de tasa | variación de comando entre ciclos | ambos |
| SR-009 | — | — | restricción de entrenamiento |
| SR-010 | — | — | propiedad de arbitraje de la cadena |
| SR-012 | C-01, C-02, C-03 sobre estado estimado | offset y rumbo estimados | dirección |

*Tabla 5.1 — Trazabilidad de requisitos a reglas de la cage.*

Tres observaciones. La primera: seis reglas cubren catorce requisitos, porque una misma regla puede implementar varios y un requisito puede requerir varias. La segunda: dos requisitos no se implementan por regla, y el marco obliga a declararlo en la matriz con el tipo de implementación explícito —restricción de entrenamiento y propiedad de arbitraje— en lugar de inventar una regla que los cubra nominalmente. Es más honesto etiquetar el tipo que forzar la metáfora. La tercera: los requisitos del track de cámara no añaden reglas: reutilizan las existentes sobre un estado de origen distinto, lo que es en sí mismo un resultado de diseño —la cage es agnóstica al origen del estado.

## 5.5 Las seis reglas

Las seis reglas se evalúan en el orden fijo que muestra la Figura 5.1, en una sola pasada por ciclo. Cada regla se especifica con el mismo formato: requisito implementado, variable observada, lógica de activación, estrategia correctiva y parámetros. La uniformidad facilita la comparación y la verificación cruzada. Los valores numéricos completos están en el Anexo E.

<img src="../figures/cage_rule_chain.png" alt="Figura 5.1 — Cadena de reglas en orden de evaluación." width="500"/>

*Figura 5.1 — Las seis reglas en su orden fijo de evaluación, una sola pasada por ciclo. Cada regla consume como acción cruda la acción segura de la anterior. C-06 sanea primero el comando hasta una línea base factible; C-05 se evalúa la última para que su acción sustituida —dirección congelada y frenado— prevalezca sobre toda corrección anterior. La aserción de envolvente conjunta al cierre del ciclo puede aún escalar a emergencia.*

**C-01 — Límite lateral duro.** Observa el offset lateral con signo. Activación histerética por encima de un umbral situado por debajo del límite del requisito, con banda de desactivación menor y memoria entre ciclos. Corrección proporcional al exceso, en la dirección que devuelve el vehículo al centro, aplicada por sobrescritura sobre la dirección; la tracción queda intacta. Si el modo de emergencia está activo, C-01 no actúa.

**C-02 — Límite de error de rumbo.** Lógica análoga sobre el error de orientación, con su propia banda de histéresis y ganancia. C-01 y C-02 pueden activarse simultáneamente; en el orden elegido C-02 se evalúa antes, de modo que la corrección final es composición de ambas y C-01 conserva la última palabra. Esta co-activación es exactamente el escenario que el peligro H-09 anticipa, y el Capítulo 8 lo mide.

**C-03 — Límite predictivo de tiempo a cruce.** Propaga el estado lateral a corto horizonte con un modelo cinemático simple y estima el tiempo hasta cruzar la frontera del carril. Si cae por debajo del mínimo, aplica corrección proporcional a la urgencia. Su valor es comprar margen antes de que C-01 tenga que actuar; su coste, la dependencia de un modelo de propagación cuya validez se degrada con la curvatura.

**C-04 — Techo de velocidad.** Acota la velocidad comandada por un techo dependiente de la curvatura local, interpolado entre un valor de recta y uno de curva. Actúa sobre la tracción. Es la única regla que en la campaña de referencia nunca llega a activarse, por una razón que se documenta en el Capítulo 8 y que constituye una limitación declarada del punto de operación, no de la regla.

**C-05 — Modo de emergencia.** Es la regla más compleja y la única que puede sobrescribir a todas las demás. Se dispara por ocho condiciones agrupadas en tres familias: estado compuesto irrecuperable —rumbo y offset elevados de forma sostenida—; invalidez del estado —observación obsoleta, campos fuera de rango, pérdida de mensajes—; y salud de la percepción —el estimador de carril reporta que no puede producir una estimación fiable, o la estimación falla la verificación de plausibilidad. El comportamiento es determinista: desaceleración a tasa mínima con dirección congelada hasta detención. Las tres últimas familias son las que hacen que el sistema degrade a parada segura en lugar de actuar sobre una percepción corrupta, y son la materialización de los requisitos del track de cámara.

**C-06 — Limitador de tasa.** Acota la variación del comando entre ciclos consecutivos, en dirección y en tracción. Se evalúa primero, sobre el comando crudo. Es formalmente la regla de menor criticidad —implementa requisitos de clase B, de suavidad y de varianza— y el Capítulo 8 mostrará que esa clasificación subestima gravemente su papel real en el sistema final.

## 5.6 Parametrización, versionado y modos

Todos los umbrales viven en un fichero de parámetros versionado, no en el código. La separación tiene tres consecuencias operativas. Primera: cualquier ejecución experimental registra el *hash* del fichero junto con el resto de metadatos de reproducibilidad, de modo que un resultado queda ligado sin ambigüedad a la configuración exacta que lo produjo. Segunda: los umbrales pendientes de calibración física se marcan explícitamente en el propio fichero, de modo que su carácter provisional es visible para quien lo lea y no queda sepultado en la documentación. Tercera: el versionado sigue una política de compatibilidad hacia atrás —al introducir una funcionalidad nueva, sus valores por defecto deben dejarla inerte para configuraciones anteriores— de modo que una campaña histórica pueda re-ejecutarse sin que una funcionalidad posterior altere su resultado.

La cage admite además dos modos de operación que son la base de todo el diseño experimental del trabajo. En modo enforcement las correcciones se aplican al comando que llega al vehículo. En modo monitoring la cage evalúa exactamente las mismas reglas, registra exactamente las mismas activaciones, pero no modifica el comando: la policy conduce sola. El contraste entre ambos modos sobre el mismo escenario y la misma semilla es el instrumento con el que el Capítulo 8 mide la contribución de la cage, y su valor metodológico es que constituye un contrafactual limpio —no una comparación entre sistemas distintos, sino entre el mismo sistema con y sin la envolvente activa.

## 5.7 Arquitectura ROS2

### 5.7.1 Descomposición en nodos

El sistema se descompone en los nodos de la Figura 5.2, con responsabilidad única y comunicados por tópicos explícitos. La cadena de datos es lineal y auditable: la percepción produce el estado; la policy consume el estado y produce un comando crudo; la cage consume comando crudo y estado y produce comando seguro más un registro de estado de la cage; el control de vehículo traduce el comando seguro a consignas de actuación; y el nodo de registro persiste el estado de la cage a disco.

<img src="../figures/Lane_camera_agent-cage.png" alt="Figura 5.2 — Cadena de nodos del sistema." width="480"/>

*Figura 5.2 — Cadena de nodos: percepción, policy, cage, control de vehículo y registro. El comando de la policy nunca alcanza al actuador sin pasar por la cage.*

La propiedad arquitectónica que importa es que el comando de la policy no alcanza el actuador sin atravesar la cage. No es una convención de código: es una propiedad topológica del grafo, verificable por inspección de las conexiones, y significa que no existe camino por el cual un comando no filtrado llegue al vehículo.

### 5.7.2 Arquitectura del track de cámara

El track de cámara conserva la misma topología con dos diferencias sustantivas. La policy recibe la imagen en lugar del vector de estado, y la cage obtiene su estado de un estimador de carril propio, una cadena clásica de visión por computador que procesa la misma imagen con un algoritmo determinista e independiente de la red.

Esta decisión es el punto de diseño más delicado del trabajo y conviene exponer su compromiso con precisión. La ventaja es que la envolvente de seguridad no hereda los modos de fallo de la red: razona sobre un estado producido por un algoritmo auditable, inspeccionable línea a línea y verificable contra una referencia. El coste es una causa común: ambos consumen la misma imagen, de modo que una degradación suficientemente severa del canal visual ciega a los dos a la vez. El diseño no oculta ese coste; lo mitiga con la familia de disparadores de salud y plausibilidad de C-05 —que degradan a parada controlada cuando el estimador no puede producir una estimación fiable— y lo declara como riesgo residual, con un peligro propio registrado (H-12) para el caso en que la estimación sea errónea *pero plausible*, que es el caso que ninguna verificación de consistencia interna puede atrapar.

## 5.8 Trazabilidad y verificación automática

Con las reglas especificadas, la matriz cubre su segundo tramo: la correspondencia entre requisitos y reglas. El validador comprueba mecánicamente que toda regla implementa al menos un requisito, que todo requisito está implementado por una regla o declara explícitamente su tipo alternativo de implementación, y que toda regla es ejercitada por al menos un escenario. Cualquier violación bloquea la puerta de revisión.

Conviene subrayar el efecto de diseño que esto produce, porque es una de las afirmaciones que el Capítulo 11 evalúa: la restricción obliga a decidir la vía de implementación en el momento de escribir el requisito, no después. El resultado observable es un conjunto de requisitos más operativos, y un conjunto de reglas sin funcionalidad huérfana —no hay ninguna regla en la cage que no responda a un requisito trazable hasta un peligro registrado.

Definida la especificación, el Capítulo 6 aborda su implementación y verificación.
