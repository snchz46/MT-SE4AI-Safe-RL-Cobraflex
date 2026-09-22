# Capítulo 6 — Implementación y verificación

## 6.1 Propósito del capítulo

Este capítulo cubre el nivel de implementación (L5) y su nivel correspondiente de verificación clásica (L4a'). Explica cómo se construyeron el entorno de simulación, los nodos del sistema y la cage del Capítulo 5, y cómo se verifica la cage con la única técnica que sigue sirviendo para un componente determinista: el test unitario.

El objetivo no es contar todos los detalles de ingeniería. La lista completa de módulos, scripts y tests se guarda en un documento vivo versionado. El objetivo es dejar constancia de las decisiones que no eran obvias y de la evidencia de que la cadena funciona antes de añadir el componente aprendido.

## 6.2 Entorno de simulación y modelo del vehículo

El entorno usa una versión de ROS2 y otra de Gazebo con soporte a largo plazo. Se eligieron porque encajan con el resto de la cadena y porque incluyen un puente nativo entre ambos. El mundo simulado es una pista cerrada con marcas laterales blancas y una línea central discontinua, sobre una superficie plana y con iluminación controlada. Sus parámetros geométricos son exactamente los que declara el dominio operacional, así que cualquier afirmación sobre el dominio se puede comprobar con el fichero del mundo.

<img src="../figures/fig_6_1_oval_gazebo_env.png" alt="Figura 6.1 — Entorno de simulación del track de estado." width="560"/>

*Figura 6.1 — El entorno de simulación del track de estado: el óvalo de referencia con marcas laterales blancas y línea central discontinua, el vehículo en la línea de salida y el árbol de entidades del mundo, cuyos parámetros geométricos son los que declara el dominio operacional.*

El modelo del vehículo aproxima la dinámica del vehículo físico a escala. Hay un detalle importante que a menudo se pasa por alto. La plataforma real tiene tracción diferencial, con cuatro ruedas fijas y sin ángulo de dirección. No es un vehículo Ackermann. El modelo de simulación usa un controlador de tracción diferencial, así que en este aspecto coincide con la plataforma real. En la práctica, «dirección» en este trabajo significa siempre una consigna de velocidad angular normalizada, no un ángulo de rueda, y los límites de maniobra del simulador y de la plataforma tienen la misma estructura.

## 6.3 Implementación de los nodos

Todos los nodos siguen el mismo patrón: parámetros declarados fuera del código, suscripciones y publicaciones explícitas, un bucle a frecuencia fija controlado por un temporizador y un registro estructurado. No es solo por estética. Cuando algo falla, permite relacionar la latencia y el comportamiento temporal con un nodo concreto.

**Nodo de percepción.** En el track de estado proyecta la pose sobre la línea central para obtener el vector de estado. En el track de cámara esta tarea la hace el propio estimador de visión de la cage, que se describe más abajo.

**Nodo de policy.** Carga el modelo entrenado, lee la observación y publica el comando crudo. Se mantiene lo más simple posible: toda la lógica de aprendizaje está en el entorno de entrenamiento, y durante la operación el nodo solo ejecuta la policy.

**Nodo de cage.** Es el componente central. Está escrito como una biblioteca de Python puro sin dependencia de ROS2, y un nodo fino la conecta a los tópicos. Esta separación tiene una consecuencia importante para el método. La cage se puede probar entera sin arrancar el simulador ni el middleware, con una suite de tests determinista que tarda menos de un segundo. Así la verificabilidad que el Capítulo 5 defendía en teoría se vuelve real.

**Nodo de control de vehículo.** Convierte el comando seguro en consignas de actuación y aplica la saturación física final.

**Nodo de registro.** En cada ciclo guarda en un fichero estructurado el estado completo de la cage: comando crudo, comando seguro, reglas activas, modo y estado observado. Es la herramienta del nivel de monitorización en operación. Sin él, la adaptación A3 no tendría evidencia.

## 6.4 Controlador clásico para la validación de la cadena

Antes de añadir el componente aprendido, se implementa un controlador proporcional-derivativo sobre el error lateral y el de rumbo. Su papel en la tesis no es competir con la policy. Sirve para otras tres cosas. Comprueba que la cadena completa funciona de principio a fin con un controlador cuyo comportamiento es totalmente predecible. Da una referencia de rendimiento para interpretar los resultados del aprendizaje. Y permite calibrar los umbrales de la cage con un conductor que se comporta igual en todas las ejecuciones.

Sus limitaciones se declaran. No anticipa la curvatura, empeora en curvas cerradas y sus ganancias se ajustaron a mano sobre un trazado concreto. No es un baseline fuerte. Es una herramienta.

## 6.5 Estrategia y resultados de verificación

La verificación tiene tres niveles. Los tests unitarios de cada regla cubren, para las seis reglas, al menos: la activación por encima del umbral, la no activación por debajo, el comportamiento dentro de la banda de histéresis en ambos sentidos y la saturación. Los tests de propiedades comprueban invariantes que no pertenecen a ninguna regla concreta: que el orden de evaluación es el declarado; que el modo de emergencia anula cualquier corrección anterior; que el comando de salida siempre está dentro del rango físico, actúen las reglas que actúen; y que una configuración de parámetros de una versión anterior sigue dando el comportamiento anterior. Los tests de integración ejecutan la cadena completa con estados sintéticos y comprueban que el comando llega filtrado y que el registro contiene lo que debe.

La suite de tests crece con el sistema y tiene que pasar antes de cada revisión. Su valor no está en el número de tests sino en una propiedad: cada regla de la cage tiene tests que fallan si su comportamiento cambia. Así, cualquier cambio de un umbral se hace visible y no puede colarse sin que nadie lo note.

## 6.6 Validación de la cadena y primeras métricas

La demostración integrada ejecuta la cadena completa en simulación con el controlador clásico conduciendo. Aquí se dan tres primeras métricas. No son un resultado experimental, solo evidencia de que la cadena funciona. La caracterización de verdad está en el Capítulo 8.

La latencia del ciclo de la cage se midió durante 845 s de funcionamiento continuo. Su mediana y su percentil 95 son los dos de 50,0 ms. El máximo es de 62,0 ms, causado por un único ciclo y por el planificador no determinista del sistema operativo. La mediana y el percentil 95 caben dentro del presupuesto del ciclo de control.

Durante la operación nominal, la cage interviene en el 0,047 % de los ciclos (8 de 16 910). Todas las intervenciones vienen de la regla de rumbo o del limitador de tasa. El límite lateral, la regla predictiva y el modo de emergencia no se activan nunca. Este resultado dice dos cosas, y las dos importan: el controlador clásico está bien ajustado para el escenario nominal, y los umbrales de la cage no son demasiado estrictos. Una cage que interviniera todo el rato en condiciones nominales no estaría midiendo seguridad. Estaría midiendo su propio mal ajuste.

En condiciones nominales el vehículo completa 9,91 vueltas en 845 s sin un solo ciclo de emergencia. Con una sola ejecución no se puede caracterizar nada. Lo que muestra la cifra es que la cadena puede funcionar durante mucho tiempo sin empeorar.

## 6.7 Cambios para el track de cámara

El sistema de referencia no añade nodos nuevos. Adapta el entorno, como muestra la Figura 6.2. El mismo entorno de entrenamiento se usa para los dos tracks, y la rama de cámara se activa con un interruptor de configuración. Hay cuatro decisiones técnicas que merece la pena anotar.

**Cadena de cámara compartida y causa común.** La imagen nativa llega por el puente entre simulador y middleware y pasa por una única cadena en cada ciclo. El inyector de degradación visual del escenario se aplica antes de que la cadena se divida. Así, la misma imagen degradada va tanto al estimador de la cage, a resolución nativa, como a la versión de 84×84 en escala de grises que usa la policy. Aplicar la degradación una sola vez, antes de la división, es lo que asegura que policy y cage ven el mismo mundo, también cuando ese mundo está degradado. Un hallazgo de implementación afecta directamente al presupuesto de los experimentos: el renderizado de la cámara va ligado al tiempo real, así que en este track el reloj de simulación va a factor uno, mientras que el track de estado va más rápido que el tiempo real.

<img src="../figures/fig_6_2_etrack_camera_control_loop.png" alt="Figura 6.2 — Lazo de control del track de cámara." width="540"/>

*Figura 6.2 — El lazo de control del track de cámara. El inyector de degradación se aplica antes de la división, así que el estimador determinista de la cage y la imagen de 84×84 que usa la red reciben exactamente la misma entrada. Esa es la causa común que el Capítulo 5 registra como riesgo residual, y también es la razón por la que un estresor de escenario se puede atribuir con claridad: entra en el sistema una sola vez.*

<img src="../figures/fig_6_3_cv_lane_estimator_pipeline.png" alt="Figura 6.3 — Cadena del estimador de carril de la cage." width="520"/>

*Figura 6.3 — La cadena del estimador de carril que usa la cage: cinco etapas deterministas desde la imagen nativa hasta el estado relativo al carril, sin ningún componente aprendido. Esto es lo que evita que la envolvente de seguridad herede los modos de fallo de la red.*

**Estimador de carril de la cage.** La Figura 6.3 lo muestra en detalle. Es una cadena de visión clásica y determinista (umbralizado, extracción de líneas y geometría de carril) que reconstruye el offset lateral y el error de rumbo para las seis reglas. Se valida por separado, antes del veredicto. Frente a la verdad de referencia del simulador detecta el carril en todos los casos, con un sesgo de offset por debajo de 32 mm con los niveles de deslumbramiento que luego usa la campaña de escenarios. Cuando su supervisor de salud indica que la percepción no es válida, el modo de emergencia hace la parada controlada en lazo abierto. Este es el mecanismo que el Capítulo 8 mide como el valor de la cage cuando hay degradación.

**Circuito de validación.** El track de referencia se valida sobre un circuito sinuoso que pasa cerca de sí mismo, con 19,22 m de perímetro (2,2 veces el óvalo del track de estado), y sobre sus variantes con estrés visual. Como el trazado pasa cerca de sí mismo, hubo que cambiar la lógica de contención. El criterio de salida de vía basado en la distancia perpendicular deja de funcionar cuando dos tramos del trazado están a menos de un ancho de calzada. Por eso la salida se juzga por la distancia global al eje de la calzada, y se mantiene el comportamiento anterior para el track de estado. Es un buen ejemplo de cómo un cambio de trazado puede romper sin avisar una métrica que parecía neutral.

**Aleatorización visual durante el entrenamiento.** El entrenamiento aplica degradaciones visuales aleatorias dentro del rango del peligro correspondiente, para que la policy sea más robusta. Durante la evaluación la aleatorización se desactiva, y el único estresor visual es el que declara el escenario, de modo que cada ejecución se pueda relacionar con su propia perturbación. Mezclar las dos cosas daría resultados que no se podrían atribuir.

## 6.8 Resumen

Al final de este capítulo el sistema existe. La cadena funciona de principio a fin. La cage está implementada y verificada con la técnica clásica que corresponde a un componente determinista. Y el registro produce la evidencia que usarán los niveles superiores de la rama derecha. Lo que falta todavía es el componente para el que se construyó el marco. El Capítulo 7 trata su especificación de proceso, que es la segunda mitad de la adaptación A1, y su entrenamiento.
