# Capítulo 6 — Implementación y verificación

## 6.1 Propósito del capítulo

Este capítulo ocupa el nivel de implementación (L5) y su nivel simétrico de verificación clásica (L4a'). Documenta cómo se materializan el entorno de simulación, los nodos del sistema y la cage especificada en el Capítulo 5, y cómo se verifica esa cage con la técnica que sigue siendo aplicable a un componente determinista: el test unitario.

La intención no es exhaustividad de ingeniería —el inventario completo de módulos, scripts y pruebas vive como documento vivo versionado— sino documentar las decisiones no triviales y la evidencia de que la cadena funciona antes de introducir el componente aprendido.

## 6.2 Entorno de simulación y modelado del vehículo

El entorno se construye sobre una distribución de ROS2 y una versión de Gazebo con soporte a largo plazo, elegidas por coherencia con el resto de la cadena y por disponibilidad del puente nativo entre ambos. El mundo simulado reproduce una pista delimitada con marcas laterales blancas y separador central discontinuo, sobre superficie plana y con iluminación controlada; sus parámetros geométricos son exactamente los que el dominio operacional declara, de modo que cualquier afirmación sobre el dominio es comprobable contra el fichero del mundo.

<img src="../figures/fig_6_1_oval_gazebo_env.png" alt="Figura 6.1 — Entorno de simulación del track de estado." width="560"/>

*Figura 6.1 — El entorno de simulación del track de estado: el óvalo de referencia con marcas laterales blancas y separador central discontinuo, el vehículo sobre la línea de salida y el árbol de entidades del mundo, cuyos parámetros geométricos son los que declara el dominio operacional.*

El vehículo se modela aproximando la dinámica del vehículo físico a escala. Una precisión importante y frecuentemente pasada por alto: la plataforma real es de tracción diferencial, con cuatro ruedas fijas y sin ángulo de dirección, no de tipo Ackermann; el modelo de simulación usa un controlador de tracción diferencial y es, en ese sentido, fiel. La consecuencia práctica es que «dirección» en todo este trabajo significa una consigna de velocidad angular normalizada, no un ángulo de rueda, y que la envolvente de maniobrabilidad del simulador y la de la plataforma comparten estructura.

## 6.3 Implementación de los nodos

Todos los nodos siguen un patrón común: parámetros externalizados y declarados, suscripción y publicación explícitas, bucle a frecuencia fija gobernado por temporizador y registro estructurado. La uniformidad no es cosmética: hace que la latencia y el comportamiento temporal sean atribuibles a un nodo concreto cuando algo se desvía.

**Nodo de percepción.** En el track de estado proyecta la pose sobre la línea central para producir el vector de estado. En el track de cámara este papel lo desempeña el estimador de visión de la propia cage, descrito más abajo.

**Nodo de policy.** Carga el modelo entrenado, consume la observación y publica el comando crudo. Es deliberadamente delgado: toda la lógica de aprendizaje vive en el entorno de entrenamiento, y en operación el nodo es un evaluador de la política.

**Nodo de cage.** Es el componente central. Se implementa como una biblioteca de Python puro sin dependencia de ROS2, envuelta por un nodo delgado que la conecta a los tópicos. Esta separación tiene una consecuencia metodológica que conviene destacar: la cage puede probarse íntegramente sin levantar el simulador ni el middleware, con una suite determinista que se ejecuta en menos de un segundo. La verificabilidad que el Capítulo 5 reivindicaba en abstracto se hace así operativa.

**Nodo de control de vehículo.** Traduce el comando seguro a consignas de actuación, aplicando la saturación física final.

**Nodo de registro.** Persiste el estado completo de la cage por ciclo —comando crudo, comando seguro, reglas activas, modo, estado observado— a un fichero estructurado. Es el instrumento del nivel de monitorización en operación: sin él, la adaptación A3 no tendría evidencia.

## 6.4 Un controlador clásico como validador de la cadena

Antes de introducir el componente aprendido se implementa un controlador proporcional-derivativo sobre el error lateral y de rumbo. Su función en la tesis no es competir con la policy sino tres cosas distintas: validar que la cadena completa funciona de extremo a extremo con un controlador cuyo comportamiento es enteramente predecible; ofrecer una referencia de rendimiento contra la que interpretar los resultados del aprendizaje; y permitir calibrar los umbrales de la cage con un conductor cuyo comportamiento no cambia entre ejecuciones.

Sus limitaciones se declaran: no anticipa la curvatura, degrada en curvas cerradas y sus ganancias se ajustaron empíricamente sobre una geometría concreta. No es un baseline competitivo, es un instrumento.

## 6.5 Estrategia y resultados de verificación

La verificación se organiza en tres niveles. Los tests unitarios por regla cubren, para cada una de las seis reglas, al menos la activación por encima del umbral, la no activación por debajo, el comportamiento dentro de la banda de histéresis en ambos sentidos y la saturación. Los tests de propiedades transversales verifican invariantes que ninguna regla posee por separado: que el orden de evaluación es el declarado; que el modo de emergencia domina a cualquier corrección previa; que el comando de salida está siempre dentro del rango físico con independencia de cuántas reglas hayan intervenido; y que una configuración de parámetros de versión anterior sigue produciendo el comportamiento anterior. Los tests de integración ejercitan la cadena completa con estados sintéticos, comprobando que el comando llega filtrado y que el registro contiene lo que debe contener.

La suite crece con el sistema y se ejecuta como condición de cada revisión. Su valor no está en el número de casos sino en una propiedad: cada regla de la cage tiene tests que fallan si su comportamiento cambia, lo que convierte cualquier modificación de umbral en un cambio visible y no en una deriva silenciosa.

## 6.6 Validación de la cadena y métricas preliminares

La demostración integrada ejecuta la cadena completa en simulación con el controlador clásico al mando. Se reportan tres métricas preliminares, no como resultado experimental sino como evidencia de que la cadena funciona; la caracterización pertenece al Capítulo 8.

La latencia del ciclo de la cage, medida sobre 845 s de operación continua, arroja mediana y percentil 95 de 50,0 ms, con un máximo de 62,0 ms atribuible a un único ciclo y al planificador no determinista del sistema operativo. Mediana y percentil 95 caben dentro del presupuesto del ciclo de control.

La tasa de intervención durante operación nominal es del 0,047 % de los ciclos —8 de 16 910—, todas atribuidas a la regla de rumbo o al limitador de tasa, sin ninguna activación del límite lateral, del predictivo ni de la emergencia. La lectura tiene dos direcciones y ambas importan: el controlador clásico está bien calibrado para el escenario nominal, y los umbrales de la cage no son artificialmente restrictivos. Una cage que interviniera constantemente en condiciones nominales no estaría midiendo seguridad, estaría midiendo su propio desajuste.

La tasa de completitud en condiciones nominales es de 9,91 vueltas en 845 s sin ningún ciclo de emergencia. Con una única ejecución no cabe hablar de caracterización; lo que la cifra establece es que la cadena sostiene operación prolongada sin degradación.

## 6.7 Especialización para el track de cámara

El sistema de referencia no añade nodos: especializa el entorno, según la Figura 6.2. El mismo entorno de entrenamiento sirve a ambos tracks y la rama de cámara se activa con un conmutador de configuración. Cuatro decisiones técnicas merecen registro.

**Cadena de cámara compartida y garantía de causa común.** La imagen nativa llega por el puente entre simulador y middleware y atraviesa una cadena única por ciclo. El inyector de degradación visual del escenario se aplica antes de la bifurcación, de modo que la misma imagen degradada alimenta tanto al estimador de la cage, a resolución nativa, como a la reducción a 84×84 en escala de grises que consume la policy. Aplicar la degradación una sola vez antes de la bifurcación es lo que garantiza que policy y cage ven el mismo mundo, también cuando ese mundo está degradado. Un hallazgo de implementación con consecuencia directa sobre el presupuesto experimental: el renderizado de cámara está ligado a tiempo real, de modo que el reloj de simulación corre a factor uno en este track, frente a la ejecución acelerada del track de estado.

<img src="../figures/etrack_camera_control_loop.png" alt="Figura 6.2 — Lazo de control del track de cámara." width="540"/>

*Figura 6.2 — El lazo de control del track de cámara. El inyector de degradación se aplica antes de la bifurcación, de modo que el estimador determinista de la cage y la reducción a 84×84 que consume la red reciben exactamente la misma imagen. De ahí la causa común que el Capítulo 5 declara como riesgo residual, y de ahí también que un estresor de escenario sea atribuible: entra una sola vez en el sistema.*

<img src="../figures/cv_lane_estimator_pipeline.png" alt="Figura 6.3 — Cadena del estimador de carril de la cage." width="520"/>

*Figura 6.3 — La cadena del estimador de carril sobre la que razona la cage: cinco etapas deterministas desde la imagen nativa hasta el estado relativo al carril, sin ningún componente aprendido. Es lo que permite que la envolvente de seguridad no herede los modos de fallo de la red.*

**Estimador de carril de la cage.** La Figura 6.3 la detalla: es una cadena de visión clásica y determinista —umbralizado, extracción de líneas y geometría de carril— que reconstruye el offset lateral y el error de rumbo para las seis reglas. Su validación es propia y previa al veredicto: contra el oráculo de verdad de referencia del simulador alcanza detección completa con un sesgo de offset por debajo de 32 mm bajo los niveles de deslumbramiento que después emplea la campaña de escenarios. Cuando su supervisor de salud declara la percepción inválida, el modo de emergencia ejecuta la parada controlada en lazo abierto: el mecanismo que el Capítulo 8 mide como el valor de la cage bajo degradación.

**Circuito de validación.** El track de referencia se valida sobre un circuito sinuoso y auto-aproximante de 19,22 m de perímetro —2,2 veces el óvalo del track de estado— y sus variantes de estrés visual. La auto-aproximación forzó un cambio en la contención: el criterio perpendicular de salida de vía colapsa cuando dos tramos del trazado quedan a menos de un ancho de calzada, de modo que la salida se juzga por distancia global al eje de la calzada, manteniendo intacto el comportamiento anterior para el track de estado. Es un ejemplo instructivo de cómo un cambio de geometría invalida silenciosamente una métrica que parecía neutral.

**Aleatorización visual durante el entrenamiento.** El entrenamiento aplica degradaciones visuales aleatorias dentro de la envolvente del peligro correspondiente, como mitigación de robustez. En evaluación la aleatorización se desactiva, y el único estresor visual es el declarado por el escenario, de modo que cada ejecución sea atribuible a su perturbación. Mezclar ambas cosas produciría resultados no atribuibles.

## 6.8 Síntesis

Al cierre de este capítulo el sistema existe: la cadena funciona de extremo a extremo, la cage está implementada y verificada con la técnica clásica que su naturaleza determinista admite, y el registro produce la evidencia que los niveles superiores de la rama derecha consumirán. Lo que falta es el componente que el marco existe para acomodar. El Capítulo 7 aborda su especificación de proceso —la segunda mitad de la adaptación A1— y su entrenamiento.
