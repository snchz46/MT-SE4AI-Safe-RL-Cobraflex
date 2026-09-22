# Capítulo 5 — Diseño arquitectónico y especificación de la cage

## 5.1 Propósito del capítulo

Este capítulo cubre dos niveles: el diseño arquitectónico (L3) y la especificación de módulo en su forma clásica (L4a). Produce el primer artefacto en el que la adaptación A1 se hace concreta: la Cage Specification. Es una especificación determinista y modular escrita de la forma tradicional, a diferencia de la especificación de proceso que el Capítulo 7 escribe para la policy.

El capítulo trata la idea de diseño de la envolvente de seguridad, los problemas conceptuales que surgen al construirla, cómo se obtienen las reglas a partir de los requisitos, el diseño de cada regla, los parámetros versionados y la arquitectura ROS2 que la ejecuta. La especificación completa de parámetros, con el cálculo de cada umbral y su estado de calibración, está en el Anexo E.

## 5.2 Idea de diseño: la cage como escudo en tiempo de ejecución

### 5.2.1 Elección del mecanismo

Como se vio en el Capítulo 2, hay cuatro familias de mecanismos para hacer segura una policy aprendida. Esta tesis usa el escudo en tiempo de ejecución como mecanismo principal, por tres motivos.

El primer motivo es la verificabilidad. Una cage hecha de reglas escritas a mano es un componente clásico. Se puede probar con tests unitarios deterministas, analizar de forma estática e inspeccionar. En términos del TR 5469 (usados por analogía, ya que el TR clasifica tecnología de IA) corresponde a la Clase I, mientras que la policy es como mucho de Clase II. Esa diferencia es lo que permite al sistema completo mantener un núcleo verificable.

El segundo motivo es la independencia del entrenamiento. Una garantía obtenida cambiando el objetivo de aprendizaje es estadística y depende de la distribución de entrenamiento. Una garantía obtenida filtrando en tiempo de ejecución depende del estado observado en cada ciclo, sin importar cómo se entrenó la policy. Por eso se sigue cumpliendo si la policy se reentrena, se sustituye o empeora.

El tercer motivo es que encaja con el marco. Como efecto secundario de su funcionamiento, el escudo genera un registro de intervenciones, y ese registro es justo la evidencia que necesita el nivel de monitorización en operación (A3). La cage no es solo un mecanismo de seguridad. Es también la herramienta que mide cómo se comporta la policy.

### 5.2.2 Alcance y limitaciones de la cage

Tres aclaraciones ayudan a no sacar conclusiones exageradas. La cage no es un controlador. No crea comportamiento, sino que corrige comandos inseguros. Si la policy conduce bien, la cage debería quedarse inactiva, y el Capítulo 8 muestra que eso es lo que pasa en condiciones nominales limpias. La cage no es una garantía formal. Sus reglas son heurísticas con umbrales sacados de los requisitos, no invariantes demostradas sobre un modelo dinámico. Ofrece una contención que se puede medir, no una prueba. Y la cage no quita la necesidad de entrenar bien. Es la última línea de defensa, no la primera, y un sistema cuya seguridad dependiera por completo de la cage sería un sistema mal entrenado. El Capítulo 8 obliga a matizar esta última afirmación de una forma incómoda.

## 5.3 Problemas de diseño

Construir una envolvente de reglas plantea seis problemas. Son problemas de diseño, no de implementación, y resolverlos de forma explícita es parte de lo que aporta este capítulo.

**Prioridad y orden entre reglas.** Varias reglas pueden activarse en el mismo ciclo sobre el mismo canal de actuación. La solución elegida es un orden de evaluación fijo y declarado. El limitador de tasa va primero, así que limita el comando crudo antes de que ninguna regla de seguridad lo mire. El modo de emergencia va el último, porque tiene que poder anular cualquier corrección anterior. Entre medias, la regla de límite lateral va después de la de rumbo, para que el límite más duro sobre la variable más crítica tenga la última palabra entre las reglas operacionales.

**Diseño de la corrección.** Una corrección puede sumarse al comando de la policy o sustituirlo. Se elige sustituirlo, para que policy y cage no compitan en el mismo espacio y den una suma que ninguna de las dos buscaba. El tamaño de la corrección depende de cuánto se ha pasado el valor del umbral, no es una cantidad fija. Una corrección constante crearía saltos en el límite de activación.

**Reglas reactivas y predictivas.** Las reglas que miran el estado actual siempre llegan tarde: cuando el offset llega al umbral, la dinámica ya está comprometida. Por eso se añade una regla predictiva. Proyecta el estado a corto plazo y actúa sobre el tiempo estimado hasta salirse del carril. Los dos tipos se complementan: la regla reactiva limita el presente y la predictiva gana margen.

**Histéresis y evitar el parpadeo.** Con un solo umbral, una regla se enciende y se apaga una y otra vez alrededor de ese valor, y el comando oscilante que resulta es un peligro en sí mismo. Por eso toda regla con umbral tiene una banda de histéresis. Se activa por encima de un valor y se desactiva por debajo de otro más bajo, y recuerda su estado entre ciclos.

**Saturación y conflictos.** La suma de correcciones puede salirse del rango físico del actuador. La saturación se aplica al final de la cadena, sobre el comando combinado, y no regla a regla. Así el resultado es predecible, independientemente de cuántas reglas hayan actuado.

**Modo de emergencia y validez del estado.** El modo de emergencia tiene una condición de entrada basada en un *trigger* compuesto, un comportamiento determinista (frenar a una tasa mínima con la dirección congelada) y una salida explícita. Sus disparadores incluyen el estado compuesto irrecuperable, pero también los casos en que el propio estado no es válido: una observación antigua, campos fuera de un rango plausible o pérdida de la percepción. Este último grupo es la cadena de confianza del sistema. Si la cage no se puede fiar del estado que ve, la respuesta segura no es corregir el comando sino detener el vehículo de forma controlada.

## 5.4 De los requisitos a las reglas

Los requisitos se asignan a reglas con un procedimiento explícito. Para cada requisito se identifican tres cosas: la variable observable que expresa su condición, el mecanismo que puede mantener esa variable dentro de sus límites y el canal de actuación sobre el que actuar. A veces no existe un mecanismo así sin ir contra la idea de la cage. Es el caso de la *liveness*: una regla que forzara tracción positiva estaría creando comportamiento en lugar de corregirlo. En ese caso el requisito se implementa en otro nivel, y se dice así.

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

Tres comentarios. Primero, seis reglas cubren catorce requisitos, porque una regla puede implementar varios requisitos y un requisito puede necesitar varias reglas. Segundo, dos requisitos no se implementan con ninguna regla. El marco obliga a que esto se vea en la matriz, indicando el tipo de implementación (restricción de entrenamiento y propiedad de arbitraje), en lugar de inventar una regla que los cubra solo sobre el papel. Nombrar el tipo es más honesto que forzar una regla. Tercero, los requisitos del track de cámara no añaden reglas nuevas. Reutilizan las existentes sobre un estado que viene de otra fuente. Esto ya es un resultado de diseño: a la cage no le importa de dónde viene el estado.

## 5.5 Las seis reglas

Las seis reglas se evalúan en el orden fijo que muestra la Figura 5.1, en una sola pasada por ciclo. Cada regla se describe con el mismo formato: requisito que implementa, variable observada, lógica de activación, estrategia de corrección y parámetros. Usar el mismo formato hace más fácil compararlas y revisarlas entre sí. Los valores numéricos completos están en el Anexo E.

<img src="../figures/fig_5_1_cage_rule_chain.png" alt="Figura 5.1 — Cadena de reglas en orden de evaluación." width="500"/>

*Figura 5.1 — Las seis reglas en su orden fijo de evaluación, una pasada por ciclo. Cada regla toma como acción cruda la acción segura de la regla anterior. C-06 limpia primero el comando hasta una línea base factible. C-05 va la última, para que su acción de sustitución (dirección congelada y frenado) anule toda corrección anterior. La comprobación de envolvente conjunta al final del ciclo todavía puede escalar a emergencia.*

**C-01 — Límite lateral duro.** Mira el offset lateral con signo. Se activa con histéresis por encima de un umbral situado por debajo del límite del requisito, con una banda de desactivación más baja y memoria entre ciclos. La corrección crece con el exceso, apunta hacia el centro y sustituye el comando de dirección. La tracción no se toca. Si el modo de emergencia está activo, C-01 no hace nada.

**C-02 — Límite de error de rumbo.** La misma lógica aplicada al error de orientación, con su propia banda de histéresis y su ganancia. C-01 y C-02 pueden estar activas a la vez. En el orden elegido C-02 va antes, así que la corrección final combina las dos y C-01 tiene la última palabra. Esta co-activación es justo el caso que prevé el peligro H-09, y el Capítulo 8 lo mide.

**C-03 — Límite predictivo de tiempo a cruce.** Proyecta el estado lateral a corto plazo con un modelo cinemático sencillo y estima cuánto falta para cruzar el borde del carril. Si ese tiempo baja del mínimo, aplica una corrección que crece con la urgencia. Su ventaja es que gana margen antes de que tenga que actuar C-01. Su coste es que depende de un modelo de proyección que pierde precisión cuanto mayor es la curvatura.

**C-04 — Techo de velocidad.** Limita la velocidad comandada con un techo que depende de la curvatura local, interpolado entre un valor para recta y otro para curva. Actúa sobre la tracción. Es la única regla que nunca se activa en la campaña de referencia. El Capítulo 8 explica por qué, y el motivo es una limitación declarada del punto de operación, no de la regla.

**C-05 — Modo de emergencia.** Es la regla más compleja y la única que puede anular a todas las demás. La pueden disparar ocho condiciones, en tres grupos. El primero es un estado compuesto irrecuperable: error de rumbo y offset altos que se mantienen en el tiempo. El segundo es un estado no válido: una observación antigua, campos fuera de rango o mensajes perdidos. El tercero es la salud de la percepción: el estimador de carril indica que no puede dar una estimación fiable, o la estimación no pasa la comprobación de plausibilidad. El comportamiento es determinista: frenar a una tasa mínima con la dirección congelada hasta que el vehículo se detiene. Los dos últimos grupos son los que hacen que el sistema pase a una parada segura en lugar de actuar sobre una percepción mala, y son los que implementan los requisitos del track de cámara.

**C-06 — Limitador de tasa.** Limita cuánto puede cambiar el comando entre dos ciclos seguidos, tanto en dirección como en tracción. Se evalúa la primera, sobre el comando crudo. Formalmente es la regla menos crítica, porque implementa requisitos de clase B de suavidad y varianza. El Capítulo 8 muestra que esta etiqueta subestima mucho su papel real en el sistema final.

## 5.6 Parámetros, versionado y modos

Todos los umbrales están en un fichero de parámetros versionado, no en el código, con tres efectos prácticos. Cada ejecución guarda el *hash* del fichero junto al resto de metadatos, así que cada resultado queda ligado sin duda a la configuración que lo produjo. Los umbrales pendientes de calibración física se marcan en el propio fichero, y no en algún punto perdido de la documentación. Y el versionado sigue una regla de compatibilidad hacia atrás —una funcionalidad nueva debe quedar inactiva con los valores por defecto de configuraciones anteriores— para poder volver a ejecutar una campaña antigua sin que un añadido posterior cambie su resultado.

La cage tiene además dos modos de funcionamiento, y todo el diseño experimental del trabajo se apoya en ellos. En modo enforcement, las correcciones se aplican al comando que llega al vehículo. En modo monitoring, la cage evalúa exactamente las mismas reglas y registra exactamente las mismas activaciones, pero no cambia el comando, así que la policy conduce sola. Comparar los dos modos con el mismo escenario y la misma semilla es la forma en que el Capítulo 8 mide lo que aporta la cage. Lo valioso de este método es que da un contrafactual limpio: no compara sistemas distintos, sino el mismo sistema con y sin la envolvente activa.

## 5.7 Arquitectura ROS2

### 5.7.1 Nodos

El sistema se divide en los nodos de la Figura 5.2. Cada nodo tiene una sola tarea, y se comunican mediante tópicos explícitos. El flujo de datos es lineal y fácil de auditar. La percepción produce el estado. La policy lee el estado y produce un comando crudo. La cage lee el comando crudo y el estado y produce un comando seguro y un registro del estado de la cage. El control de vehículo convierte el comando seguro en consignas de actuación. El nodo de registro guarda el estado de la cage en disco.

<img src="../figures/fig_5_2_node_chain.png" alt="Figura 5.2 — Grafo de nodos del sistema." width="518"/>

*Figura 5.2 — Grafo de nodos del sistema: percepción, policy, cage, control de vehículo y registro, con los tópicos que los conectan. En el track de estado la policy lee el estado que publica la percepción. En el track de cámara lee directamente la imagen, y la cage obtiene su estado del estimador de carril CV (§5.7.2). La única conexión con la plataforma, `/cmd_vel`, sale del control de vehículo, que solo recibe datos de la cage: el comando de la policy nunca llega al actuador sin pasar por ella.*

La propiedad de arquitectura que importa es que el comando de la policy no puede llegar al actuador sin pasar por la cage. No es una convención de programación. Es una propiedad de la topología del grafo que se puede comprobar mirando las conexiones, y significa que no hay ningún camino por el que un comando sin filtrar llegue al vehículo.

### 5.7.2 Arquitectura del track de cámara

El track de cámara mantiene la misma topología, con dos diferencias importantes. La policy recibe la imagen en lugar del vector de estado. Y la cage obtiene su estado de su propio estimador de carril, una cadena clásica de visión por computador que procesa la misma imagen con un algoritmo determinista que no depende de la red.

Este es el punto de diseño más delicado del trabajo, y hay que explicar bien lo que se gana y lo que se pierde. La ventaja es que la envolvente de seguridad no hereda los modos de fallo de la red. Trabaja sobre un estado producido por un algoritmo que se puede auditar, leer línea a línea y comprobar contra una referencia. El coste es una causa común: los dos usan la misma imagen, así que una degradación lo bastante fuerte del canal visual ciega a ambos a la vez. El diseño no lo oculta. Reduce el riesgo con los disparadores de salud y plausibilidad de C-05, que pasan a una parada controlada cuando el estimador no puede dar una estimación fiable. Y lo registra como riesgo residual, con su propio peligro (H-12) para el caso en que la estimación es errónea *pero plausible*. Ninguna comprobación de consistencia interna puede detectar ese caso.

## 5.8 Trazabilidad y comprobación automática

Ahora que las reglas están especificadas, la matriz cubre su segunda parte: la relación entre requisitos y reglas. El validador comprueba de forma automática tres condiciones. Toda regla implementa al menos un requisito. Todo requisito está implementado por una regla, o indica explícitamente otro tipo de implementación. Y toda regla se prueba en al menos un escenario. Cualquier incumplimiento bloquea la puerta de revisión.

Vale la pena señalar el efecto que esto tiene en el diseño, porque el Capítulo 11 lo evalúa. La restricción obliga a decidir cómo se implementa un requisito en el momento de escribirlo, no después. El resultado visible es un conjunto de requisitos más prácticos y un conjunto de reglas sin funcionalidad huérfana: cada regla de la cage responde a un requisito que se puede seguir hasta un peligro registrado.

Con la especificación definida, el Capítulo 6 trata su implementación y verificación.
