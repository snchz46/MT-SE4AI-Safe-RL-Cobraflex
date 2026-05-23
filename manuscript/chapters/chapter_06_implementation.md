# Capítulo 6 — Implementación, Entorno de Simulación y Verificación

<!--
Estado: REDACCIÓN BORRADOR FASE 2 (D26–D35).
Extensión objetivo: 12–16 páginas.
Convención: las secciones marcadas [BORRADOR D2X] tienen prosa madura de
borrador de Fase 2 fijada el día indicado. Las marcadas
[COMPLETAR FASE 2] dependen de números medidos al final de la fase
(latencias, throughput del logger, completion rate del PD, resultados
exactos de pytest). Las marcadas [PULIDO FASE 6] requieren retoque
estilístico al cierre.
-->

## 6.1 Introducción del capítulo  [BORRADOR D26]

Este capítulo desarrolla la materialización ejecutable de la Cage
Specification y de la Architectural Design fijadas en el Capítulo 5, y
documenta los artefactos de verificación asociados. En términos del
V-Model adaptado (§3.5.2), el capítulo cubre tres niveles
simultáneamente: el nivel L5 (*Implementation*) con el código de los
cinco nodos ROS2 y el entorno Gazebo; el nivel L4a' (*Cage Unit Tests*),
primer artefacto resultante de la adaptación A2 (desdoblamiento del nivel
de unit testing), con la suite que verifica que cada regla implementada
cumple su especificación; y el nivel L3' (*Integration Testing*) en su
versión preliminar con tests que validan el flujo end-to-end del
pipeline. La validación operacional sobre escenarios y la evaluación
estadística de la policy se difieren a los Capítulos 8 y 9.

La estructura del capítulo es la siguiente. La sección 6.2 documenta el
entorno Gazebo y el modelado del vehículo 1:14, que es la plataforma de
desarrollo de las Fases 2 a 4. La sección 6.3 desarrolla la
implementación de cada uno de los cinco nodos ROS2, presentando para
cada uno su estructura, sus dependencias y las decisiones técnicas no
triviales. La sección 6.4 describe el controlador baseline PD, su
papel como validador de pipeline y como referencia clásica para la
comparación con el RL del Capítulo 7. La sección 6.5 desarrolla la
estrategia de testing en sus tres niveles (unitarios por regla, de
propiedades, de integración) y reporta los resultados. La sección 6.6
documenta la validación end-to-end con métricas preliminares
medidas con el PD circulando en Gazebo. La sección 6.7 cierra el
capítulo y articula la transición al Capítulo 7.

Una decisión transversal merece comentario antes de entrar en detalle.
Una de las tentaciones de un capítulo de implementación es convertirse
en un manual de uso del código. Esta no es la función académica del
capítulo. La función es documentar las decisiones técnicas no triviales
y los hallazgos empíricos de la implementación, no enumerar la API
completa de cada nodo. El código fuente es el artefacto de referencia
para la API; este capítulo articula el rationale de las decisiones que
ese código materializa. Los listados de código en el capítulo son
selectivos y se eligen para ilustrar la decisión que se está
documentando, no para sustituir el código fuente.

---

## 6.2 Entorno Gazebo y modelado del vehículo  [BORRADOR D25]

### 6.2.1 Selección de versión y rationale

La elección concreta del entorno de simulación es **ROS2 Humble + Gazebo
Classic 11**. Esta elección se fijó tras una evaluación corta en D24 y
no se ha revisado posteriormente, porque cambiar de simulador a mitad
de tesis tiene un coste muy alto en tiempo y en validez de los logs
históricos.

El rationale de la elección tiene tres componentes. Primero, la base
documental de Gazebo Classic en aplicaciones de robot cars es la más
amplia: existen templates maduros de F1TENTH y MuSHR adaptables al
vehículo 1:14. Segundo, las idiosincrasias de integración ROS2 son
menores en Gazebo Classic que en Gazebo Sim/Ignition, especialmente
para plugins de Ackermann steering. Tercero, el proyecto tiene un
horizonte de 5 meses y no se beneficia significativamente del soporte
a largo plazo que Gazebo Sim ofrecerá, a costa de la madurez actual.

La desventaja reconocida es que Gazebo Classic está en *maintenance
mode* y migrará progresivamente a Gazebo Sim. La tesis acepta este
debt: si el proyecto se continuara más allá de su horizonte
experimental, el porting al nuevo simulador sería trabajo a planificar.
Esta limitación queda documentada en el Capítulo 11 como nota
metodológica.

### 6.2.2 Mundo Gazebo: pista, iluminación, suelo

El mundo (archivo `worlds/lane_following.world` en formato SDF) contiene
cuatro elementos. Primero, una pista en forma de óvalo cerrado con
dimensiones aproximadas de 4 m × 2.5 m (radio interior 0.4 m, exterior
0.8 m) y carriles delimitados por marcas blancas pintadas de 5 cm de
ancho sobre suelo gris uniforme. Segundo, un sistema de iluminación
ambiental uniforme sin sombras direccionales, que evita complicar la
percepción visual con artefactos de iluminación. Tercero, un suelo
plano sin gradientes y con coeficientes de fricción típicos de hormigón
liso. Cuarto, un sistema de referencia con origen marcado en el centro
geométrico del óvalo y eje X alineado con la dirección preferente de
circulación.

La elección de un óvalo simple, no de un circuito complejo, es
deliberada. La función del mundo en esta fase es validar el pipeline
end-to-end y permitir el desarrollo del baseline PD; un mundo más
complejo introduciría modos de fallo (curvas cerradas, cambios de
gradiente, intersecciones) cuya gestión se difiere a la scenario library
de Fase 4. El óvalo permite vueltas repetidas con geometría conocida y
métricas reproducibles.

> *Figura 6.1 — Vista superior del mundo Gazebo. Pista oval con marcas
> de carril, vehículo 1:14 en posición de inicio, sistema de
> referencia. Posición sugerida: aquí. Pendiente para Fase 2 D32.*
> [COMPLETAR FASE 2]

### 6.2.3 Modelado del vehículo 1:14

El vehículo se modela en URDF con dimensiones aproximadas del CobraFlex
1:14 que se usará en la Fase 5: wheelbase de 0.20 m, ancho de vía de
0.18 m, altura del centro de masas de 0.06 m, masa total de 1.5 kg.
El sistema de steering es Ackermann, con ángulo máximo de las ruedas
delanteras de 25° y conversión nominal a la entrada normalizada
*steering* ∈ [-1, 1] vía un mapeo lineal.

El plugin Gazebo elegido para la dinámica del vehículo es
`gazebo_ros_ackermann_drive`. Este plugin acepta comandos en el topic
`/ackermann_cmd` con tipo `ackermann_msgs/AckermannDriveStamped` y
publica el estado del vehículo (pose y twist) en topics estándar. El
ajuste de los parámetros del plugin (ganancias del controlador interno
de velocidad, constantes de tiempo del actuador simulado) es una de
las tareas no triviales de D25; los valores actuales producen una
respuesta del vehículo que es aproximadamente realista para el
horizonte de bandwidths de interés (0–10 Hz).

Los sensores simulados incluyen: una IMU con ruido gaussiano calibrado
a partir de las hojas de datos del componente físico análogo;
encoders de rueda con resolución finita; un LiDAR 2D frontal de 270°
con resolución angular de 0.5°; y, opcionalmente para experimentos
posteriores, una cámara RGB frontal de baja resolución. En esta fase,
el nodo Perception consume preferentemente ground truth del Gazebo
para los campos derivables (lateral_offset, heading_error,
curvature_ahead) y deja los sensores reales para experimentos de
robustez en Fase 4 y para el porting a físico en Fase 5.

### 6.2.4 Launch files y orquestación

El sistema completo se lanza desde un único launch file principal
(`launch/full_pipeline.launch.py`) que orquesta el levantamiento de
Gazebo con el mundo y el vehículo, los cinco nodos ROS2 en el orden
correcto (Logger primero, Perception, Vehicle Control, Cage,
Policy/PD), y la publicación inicial del `/experiment_tag` con un
identificador derivado de la fecha y de la versión de
`cage_params.yaml` cargado.

El launch file admite argumentos desde la línea de comandos: el modo
de la cage (`enforcement` por defecto, `monitoring` o `disabled`); el
controlador a usar (`pd` o `rl`); y el tag de experimento. Esta
parametrización es la que articula los experimentos comparativos del
Capítulo 8.

---

## 6.3 Implementación de los nodos ROS2  [BORRADOR D30]

### 6.3.1 Patrón común

Los cinco nodos siguen un patrón de implementación común basado en
`rclpy` (cliente ROS2 para Python). Cada nodo es una clase que hereda
de `rclpy.node.Node`, declara sus suscriptores y publicadores en el
constructor, define callbacks de mensaje como métodos de la clase, y
expone una función `main()` para ser ejecutada como entry point.

La elección de Python sobre C++ requiere justificación. Python tiene
overhead de inferencia y de mensajes en ROS2, lo cual a 20 Hz
introduce latencia adicional de pocos milisegundos por nodo. Esa
latencia es aceptable para el caso (presupuesto de 50 ms), y a cambio
Python proporciona velocidad de desarrollo, integración directa con
las librerías de RL (Stable-Baselines3 / CleanRL en Fase 7) y
ecosistema de testing maduro (pytest, hypothesis). La decisión se
documenta como reversible: si la latencia se vuelve crítica en Fase 5
con el coche físico, el nodo cage puede portarse a C++ manteniendo la
misma especificación.

Cada nodo implementa además dos prácticas comunes. La primera es la
*health check* periódica: cada segundo, el nodo publica un mensaje en
`/diagnostics` con su estado interno (último mensaje recibido, tasa
efectiva, contadores de errores). Esto permite detectar nodos que se
han colgado sin que el sistema lance una excepción visible. La
segunda es la *parameter discovery* mediante el sistema de parámetros
de ROS2: cada nodo declara sus parámetros con valores por defecto y
los lee en runtime, lo cual permite cambiar configuración sin
modificar código.

### 6.3.2 Perception node (D26)

El nodo Perception consume datos de los sensores simulados de Gazebo y
publica un estado estructurado en `/state_obs`. En la implementación
actual la fuente principal es ground truth del simulador (topic
`/gazebo/model_states` y derivados), porque el foco de Fase 2 es el
pipeline de control, no la percepción robusta. La estructura del nodo
está preparada para portar a sensores reales en Fase 5 con un cambio
mínimo: el algoritmo de extracción de offset y heading se aísla en una
función `extract_state_from_sensors()` cuya entrada cambiará pero cuya
salida (un objeto `StateObservation`) será la misma.

Las decisiones técnicas no triviales en este nodo son tres. Primera,
la estimación de `curvature_ahead`. El método actual hace una proyección
geométrica desde la posición ground-truth del vehículo a la geometría
conocida de la pista, calcula la curvatura en un horizonte de 0.5 m
adelante, y aplica un filtro pasabajo de primer orden con constante
de tiempo 200 ms para suavizar el resultado. Esta estimación es
trivial en simulación con ground truth y será no-trivial en físico;
el filtro pasabajo se mantendrá igual para preservar el contrato con
C-04 (que asume curvatura ya filtrada).

Segunda, la asignación del flag `state_valid`. El flag es `false` si
alguno de los siguientes ocurre: el último mensaje de Gazebo es más
viejo que 100 ms; algún campo del estado está fuera de rango plausible
(por ejemplo, lateral_offset mayor que 1 m sobre una pista de 0.4 m
de carril); o el vehículo está en una posición topológicamente
inconsistente (por ejemplo, fuera del óvalo). La validez es publicada
junto con el estado y consumida principalmente por C-05.

Tercera, la frecuencia de publicación. El nodo publica a 20 Hz por
timer interno, pero la fuente Gazebo publica a 50 Hz. Esto implica que
Perception submuestrea: en cada tick del timer, lee el último estado
recibido y publica. La alternativa (publicar a 50 Hz, dejando que
suscriptores submuestreen) se descartó porque concentra el coste de
submuestreo en cada suscriptor en vez de hacerlo una vez.

### 6.3.3 Vehicle Control node (D27)

El nodo Vehicle Control traduce `/safe_action` (acciones normalizadas
en [-1, 1]) a comandos compatibles con el plugin Gazebo (en este caso
`/ackermann_cmd` con velocidad lineal y ángulo de steering en
unidades físicas). La traducción es lineal: el throttle normalizado se
mapea a velocidad lineal en m/s mediante una constante
`max_speed_throttle = 0.5 m/s`, y el steering normalizado se mapea a
ángulo en radianes mediante `max_steering_angle = 0.436 rad` (25°).

Una decisión técnica no trivial es el manejo de la transición a modo
emergencia. Cuando el campo `is_emergency_stop` de la acción recibida
es `true`, el nodo deja de seguir el throttle comandado y aplica
deceleración mediante el campo `brake` directamente al plugin, hasta
que la velocidad cae por debajo del umbral de exit. Esta lógica
duplica parcialmente la lógica de C-05 en el nodo cage; la duplicación
es deliberada por defensa en profundidad: si el nodo cage falla y deja
de publicar, el último mensaje retenido con `is_emergency_stop=true`
sigue siendo procesado por Vehicle Control, lo cual proporciona una
detención básica sin requerir la cage activa.

### 6.3.4 Safety Cage node (D28-D29)

El nodo Safety Cage es el que más superficie de código tiene y el que
más cuidado requiere en su implementación, porque cualquier defecto
aquí compromete la red de seguridad del sistema completo. Su
estructura interna refleja la arquitectura conceptual del Capítulo 5.

La clase principal `CageNode` mantiene tres atributos de estado
persistente: `last_action` (la acción aplicada en el ciclo anterior,
necesaria para C-06); `rule_active_flags` (un diccionario indexado por
ID de regla con el estado de activación, necesario para la histéresis
de C-01 y C-02); y `emergency_state` (la máquina de estados de C-05,
con valores `none`, `entering`, `active`, `recovering`).

La lógica de cada regla está aislada en un módulo independiente
(`cage_rules/c01_lane_boundary.py`, etc.) que expone una función pura
`apply_rule(state, action_in, params, internal_state)` que devuelve
`(action_out, intervention_info)`. La función es pura en el sentido de
que no tiene side effects y es determinista dado los inputs. Esta
pureza es crítica para los tests unitarios: cada función puede
probarse aisladamente sin necesidad de ROS2 corriendo.

El callback principal del nodo, ejecutado cada vez que llega un
mensaje en `/raw_action` o `/state_obs` (con sincronización por
timestamp), aplica las seis funciones en el orden de evaluación
(C-06, C-04, C-02, C-03, C-01, C-05), encadenando la salida de cada
una con la entrada de la siguiente, y compone el mensaje
`CageStatus` con los flags de cada regla. Si el modo es `monitoring`,
la acción de salida se reasigna a la acción raw original al final de
la cadena, manteniendo `CageStatus` con su contenido lógico
inalterado. Si el modo es `disabled`, las reglas ni siquiera se
evalúan y la salida es la entrada.

Una decisión técnica no trivial es la gestión de la sincronización de
mensajes. El callback se dispara con `ApproximateTimeSynchronizer` de
`message_filters`, que requiere que `/raw_action` y `/state_obs`
lleguen con timestamps próximos. La tolerancia se fija en 25 ms
(media del período de control), suficiente para tolerar
desincronización pequeña y estricta para no procesar combinaciones
incoherentes. Si la sincronización falla durante más de 5 ciclos
consecutivos, el nodo entra en modo emergencia por la rama de "estado
inválido" de C-05.

**Listing 6.1.** Esqueleto de `LaneBoundaryRule.evaluate` (C-01)
ilustrando la estructura común de las reglas: histéresis con estado
interno, corrección proporcional al exceso sobre el umbral de
desactivación, y reporte de la intervención vía `CageDecision`. Código
extraído de `cage/rules/c01_lane_boundary.py`.

```python
class LaneBoundaryRule:
    def __init__(self, params):
        self.d_max = params["d_max_m"]
        self.h_d = params["h_d_m"]
        self.gain = params["correction_gain"]
        self.d_activate = self.d_max - self.h_d
        self.d_deactivate = self.d_max - 2.0 * self.h_d
        self._active = False
        self._below_threshold_cycles = 0

    def evaluate(self, state, raw_action, prev_action=None, ctx=None):
        d = state.lateral_offset
        abs_d = abs(d)

        # Hysteresis: activate on rising edge, deactivate after N stable cycles.
        if abs_d > self.d_activate:
            self._active = True
            self._below_threshold_cycles = 0
        elif abs_d < self.d_deactivate:
            self._below_threshold_cycles += 1
            if self._below_threshold_cycles >= _CYCLES_TO_DEACTIVATE:
                self._active = False
        else:
            self._below_threshold_cycles = 0

        if not self._active:
            return CageDecision(fire=False, reason="within-bounds", ...)

        # Proportional correction toward centreline, sign opposite to d.
        steering_raw, throttle_raw = raw_action
        excess = max(0.0, abs_d - self.d_deactivate)
        correction = -math.copysign(self.gain * excess, d)
        steering_safe = max(-1.0, min(1.0, correction))

        return CageDecision(
            fire=True,
            safe_action=(steering_safe, throttle_raw),  # throttle untouched
            reason="lane-boundary-correction",
            metadata={"rule": "C-01", "lateral_offset": d,
                      "correction_raw": correction},
        )
```

### 6.3.5 Logger node (D30)

El nodo Logger se suscribe a todos los topics relevantes y escribe los
mensajes a disco. El diseño es asíncrono para no bloquear los otros
nodos: cada callback solo añade el mensaje a una cola thread-safe en
memoria; un thread separado consume la cola y escribe a disco.

El formato de salida es CSV, una línea por mensaje, con un archivo
distinto por topic. El directorio de salida es
`experiments/sim/YYYY-MM-DD_HH-MM-SS_<experiment_tag>/` con cinco
archivos: `state_obs.csv`, `raw_action.csv`, `safe_action.csv`,
`cage_status.csv`, y `metadata.json`. Este último es crítico para
reproducibilidad: contiene la versión de `cage_params.yaml` cargada,
el hash del commit de Git en el momento de la corrida, la duración
total, los argumentos del launch file, y un timestamp ISO 8601 de
inicio y fin.

La elección de CSV sobre Parquet o SQLite responde a tres
consideraciones: legibilidad humana (un investigador puede abrir un
CSV con cualquier herramienta), simplicidad de escritura (no requiere
buffering por bloques), y compatibilidad con pandas (la herramienta
de análisis de los Capítulos 8 y 9). El precio es el tamaño en disco;
para una corrida de 3 minutos a 20 Hz son aproximadamente 0.5 MB
por archivo, lo cual es manejable.

Una decisión técnica no trivial es el dimensionamiento de la cola
interna. Si la cola crece sin límite, un evento de I/O lento (por
ejemplo, el sistema operativo flusheando) podría agotar la memoria.
La cola tiene un tope de 10000 entradas por topic (≈ 8 minutos de
buffer a 20 Hz); si se llena, las entradas más viejas se descartan y
se publica una warning en `/diagnostics`. En operación normal, el
buffer típico es de pocas decenas de entradas.

El test de throughput ejecutado en D30 tarde, descrito en §6.5.4,
verificó que el logger sostiene 20 Hz durante 6.33 min (379.8 s)
sin pérdida de mensajes y con uso de memoria estable: 7 597 líneas
capturadas frente a 7 597 esperadas a 20 Hz (0% de pérdida; ver
`experiments/sim/runs/ros_run_20260523T073134Z/cage_status.csv`).

---

## 6.4 Controlador baseline PD como validador de pipeline  [BORRADOR D32]

### 6.4.1 Función del PD en la tesis

El controlador PD tiene tres funciones distintas en la tesis y vale
la pena ser explícito sobre cada una para evitar que el lector
sobredimensione su importancia.

Primera, **validar el pipeline end-to-end**. Si el PD circula por la
pista con el pipeline activo (Perception → PD → Cage → Vehicle Control
→ Gazebo), el pipeline está estructuralmente correcto. Cualquier
problema observado al sustituir el PD por un RL entrenado en la
Fase 7 será atribuible al RL, no al pipeline. Esta es la función
central en la Fase 2 y es la que justifica que el PD se desarrolle
antes que el RL.

Segunda, **proveer un baseline de referencia clásica** para los
experimentos comparativos del Capítulo 8. Cuando se evalúa la performance
del RL+cage frente a alternativas, el PD+cage es la opción natural
para representar "control clásico sin aprendizaje". Esta comparación
sitúa los resultados del RL en su contexto adecuado.

Tercera, **generar los primeros datos de log reales**. Antes de
disponer de un RL entrenado, el PD ejecutando vueltas en el óvalo
produce un dataset de logs que permite desarrollar y depurar los
scripts de análisis y visualización que se usarán intensivamente en
las Fases 4 y 5. Llegar a esas fases con scripts de análisis sin
probar es un riesgo evitable.

El PD no es parte de la aportación académica de la tesis. Es
infraestructura. Su tuning no tiene que ser óptimo; tiene que ser
"suficientemente bueno" para validar el pipeline. La aceptación de
esta característica como infraestructura más que como contribución es
fundamental para no dedicarle tiempo desproporcionado al ajuste.

### 6.4.2 Estructura del controlador

La estructura del controlador es un PD doble: un lazo sobre el
lateral_offset y un lazo sobre el heading_error, ambos contribuyendo
al steering, más un throttle aproximadamente constante con reducción
suave en curva. Las ecuaciones son

```python
steering_raw = -Kp_y · lateral_offset - Kd_y · lateral_rate
             + -Kp_h · heading_error - Kd_h · heading_rate
throttle_raw = throttle_nominal · (1 - α · |curvature_ahead|)
```

donde `lateral_rate` y `heading_rate` se estiman numéricamente como
diferencias finitas entre observaciones sucesivas (en producción
podría usarse un filtro de Kalman ligero, pero para los propósitos
del baseline la diferencia finita es suficiente).

Las ganancias se ajustaron manualmente en D32 mañana siguiendo un
procedimiento clásico: empezar con ganancias bajas, aumentar Kp_y
hasta que el vehículo siga el centro del carril en recta sin offset
constante, ajustar Kd_y para evitar oscilación, y luego repetir el
proceso para el lazo de heading. Los valores resultantes en la
versión 0.8.0 de `policy/baseline_pd.yaml` son
`Kp_y = 3.0`, `Kd_y = 0.0`, `Kp_h = 0.3`, `Kd_h = 0.0`, con
feedforward de curvatura `kappa_to_steering_gain = 0.45` y throttle
nominal 0.5 atenuado por `alpha_curve_slowdown = 0.6`. Los dos
términos derivativos se anularon tras detectar que la proyección
sobre la polilínea introduce saltos discretos de `ey` y de
`track_heading` al cambiar de segmento en la entrada de curva;
diferenciar numéricamente una señal discontinua genera picos
espurios que saturan el actuador, y el feedforward de curvatura
cubre el papel anticipativo que se esperaba del derivativo. El
valor exacto de las ganancias no es relevante académicamente; lo
relevante es que existe un PD que circula por la pista de manera
estable (ver §6.6.1).

### 6.4.3 Limitaciones reconocidas

El PD tiene limitaciones reconocidas que vale la pena documentar.
Primera, no anticipa curvas: el feed-forward por curvatura es
aproximado y el PD reacciona principalmente a errores ya
manifestados, no a errores predichos. Segunda, no es adaptativo: las
ganancias son constantes, optimizadas para el régimen de velocidades
del experimento, y empeoran fuera de él. Tercera, no maneja
robustamente perturbaciones grandes: si el estado inicial está fuera
del régimen de operación nominal, el PD puede tardar varios segundos
en recuperarse o entrar en oscilación.

Estas limitaciones son parte del rationale de querer un controlador
basado en RL: el RL puede aprender a compensar curvas anticipándose,
puede ser adaptativo a través de su estado interno (si la red tiene
componente recurrente o si el estado de entrada incluye historia), y
puede haber sido entrenado sobre escenarios perturbados. El Capítulo
8 cuantificará estas diferencias empíricamente.

---

## 6.5 Estrategia y resultados de testing  [BORRADOR D33]

### 6.5.1 Filosofía y nivel de cobertura

La filosofía de testing en este capítulo es que los tests no son un
extra opcional sino parte integral del entregable de Fase 2. Sin
ellos, la confianza en la cage no es justificable, y por tanto el
argumento de seguridad del Capítulo 10 carece de base.

La estrategia opera en tres niveles. El primero son tests unitarios
por regla, que verifican que cada función `apply_cXX` cumple su
especificación en casos representativos. El segundo son tests de
propiedades, que verifican propiedades generales del comportamiento
de la cage sobre vectores de entrada aleatoriamente generados. El
tercero son tests de integración, que verifican el flujo end-to-end
del pipeline con todos los nodos activos pero sin Gazebo (con mocks
de los topics).

El criterio de aceptación de Gate 2 es: 100% de los tests unitarios y
de propiedades en verde, y al menos un test de integración en verde.

### 6.5.2 Tests unitarios por regla

Para cada regla C-01 a C-06 se ha escrito una batería de entre 3 y 5
tests cubriendo tres tipos de caso: *compliance* (la regla no debe
activarse), *violación marginal* (la regla debe activarse con
corrección suave) y *violación severa* (la regla debe activar con
corrección fuerte o emergencia). Adicionalmente, para reglas con
estado interno (C-01, C-02 con histéresis; C-05 con máquina de
estados; C-06 con acción previa), tests específicos verifican que el
estado se gestiona correctamente entre invocaciones.

Un ejemplo concreto del patrón de test, para C-01:

```python
def test_c01_compliance():
    """C-01 should not activate when offset is well within limits."""
    state = make_state(lateral_offset=0.05, heading_error=0.0, speed=0.3)
    action_raw = VehicleAction(steering=0.1, throttle=0.5, brake=0.0)
    action_safe, info = apply_c01(state, action_raw, params, ist={})
    assert not info.intervention
    assert action_safe.steering == action_raw.steering

def test_c01_marginal_violation():
    """C-01 activates with soft correction when crossing d_activate."""
    state = make_state(lateral_offset=0.15, heading_error=0.0, speed=0.3)
    action_raw = VehicleAction(steering=0.2, throttle=0.5, brake=0.0)
    action_safe, info = apply_c01(state, action_raw, params, ist={})
    assert info.intervention
    assert action_safe.steering < action_raw.steering
    assert action_safe.steering > -params.steering_max

def test_c01_hysteresis_persistence():
    """Once active, C-01 stays active until offset drops below d_deactivate."""
    state_in = make_state(lateral_offset=0.13, heading_error=0.0, speed=0.3)
    ist = {"c01_active": True}  # came from previous active cycle
    _, info = apply_c01(state_in, default_action(), params, ist)
    assert info.intervention  # still active, between thresholds
    state_out = make_state(lateral_offset=0.08, heading_error=0.0, speed=0.3)
    _, info = apply_c01(state_out, default_action(), params, ist)
    assert not info.intervention  # below d_deactivate, deactivated
```

El número total de tests específicos por regla al cierre de D33 es
61 entre las seis reglas (`cage/tests/test_c01_lane_boundary.py`
a `test_c06_rate_limiter.py`, incluyendo
`test_c05_triggers_extended.py`). La suite completa de la cage
suma 132 casos (per-rule + integración de la cadena de reglas +
serialización del logger + comprobación de versión SR-spec); con
los 3 tests del baseline PD el repositorio reúne 143 casos.
Todos pasan con código de retorno cero de pytest
(`pytest cage/tests policy/tests` → 143 passed, fechado 2026-05-23).

### 6.5.3 Tests de propiedades transversales

Tres propiedades generales del cage se verifican por construcción
mediante tests cerrados sobre vectores representativos (no aleatorios:
el uso de `hypothesis` se difiere a F3 cuando la cobertura per-rule
esté estable). Los tres son tests pytest ordinarios dentro de
`cage/tests/`.

**Idempotencia**: si la cage ve un estado plenamente compliante con
todas las constraints, la acción de salida es idéntica a la de
entrada. Cubierto por `test_cage_node.py::test_no_intervention_on_clean_state`.

**Determinismo**: dada la misma combinación de estado, acción raw,
parámetros y estado interno, la cage produce exactamente la misma
salida. Implícitamente verificado por la ausencia de fuentes de
aleatoriedad en `cage/rules/` (sin RNG, sin tiempo wall) y por la
re-ejecución determinista del pipeline en `test_pipeline.py`.

**Saturación**: las acciones de salida nunca exceden los límites
físicos del vehículo. Cubierto end-to-end por C-06 (rate limiter)
y C-04 (speed ceiling), con tests en
`test_c06_rate_limiter.py` y `test_c04_speed_ceiling.py`.

Estas tres propiedades dan confianza estructural en la implementación;
la generación aleatoria con `hypothesis` está prevista para F3 como
refuerzo de los casos borde, no como cobertura primaria.

### 6.5.4 Tests de integración

El test de integración primario en F2 vive en
`cage/tests/test_pipeline.py::test_pd_cage_logger_pipeline` y
encadena `BaselinePD → SafetyCageNode → CageLogger` en pura Python
durante 200 ciclos (10 s a 20 Hz) sobre un stub cinemático del
vehículo. Verifica que: (i) el PD produce acciones plausibles, (ii)
el cage interviene cuando la deriva lateral supera `d_max`, (iii) el
logger persiste todos los ciclos sin pérdida, y (iv) el CSV
resultante es bien formado. Una variante (`test_pipeline_handles_missing_state_until_first_obs`)
cubre el camino en que `/raw_action` precede al primer `/state_obs`:
el cage emite el safe-stop neutro `(0.0, -0.5)` durante los ciclos
sin estado y se recupera al primer obs real.

La integración a nivel ROS2 (cinco nodos contra mocks de tópicos
sin Gazebo, vía `pytest-launch_testing`) se difiere a F3 cuando la
suite del pipeline ROS sea estable bajo cambios de la policy RL;
la cobertura actual sobre la lógica pura de cage y PD agota las
fuentes de error que no dependen del transporte ROS2.

El test de throughput se mide directamente sobre el run candidato
G2 `ros_run_20260523T073134Z` en vez de un test sintético: durante
379.8 s el logger captura 7 597 mensajes a 20 Hz sin pérdida.

Resultados del test de throughput, medidos sobre los 7 597 ciclos
del run `ros_run_20260523T073134Z` (379.8 s de operación continua,
modo `enforcement`):

- Frecuencia efectiva del callback de cage: 20.00 Hz (target 20 Hz).
- Periodo de ciclo: mediana 50.0 ms, P95 50.0 ms, máximo 53.0 ms.
  La latencia state→safe_action no se mide por separado en F2
  (se difiere a F3 cuando se instrumenten timestamps por etapa);
  el periodo de ciclo da una cota superior holgada bajo el
  presupuesto de 50 ms del SR-006.
- Líneas perdidas en logger: 0 sobre 7 597 esperadas a 20 Hz
  (`wc -l cage_status.csv` = 7 598 incluyendo cabecera).

### 6.5.5 Ejecución y automatización

La suite se ejecuta con `pytest cage/tests policy/tests` desde la
raíz del repositorio; `pytest.ini` restringe la auto-detección a
estos dos directorios para que los paquetes ROS2 bajo `src/` se
testeen vía `colcon test` (su toolchain `ament_python` con
`ament_pep257`/`ament_flake8`). La traceability matrix
(`tools/check_traceability.py --strict`) se ejecuta como gate
manual antes de cada commit que toque hazards, SRs o reglas; su
integración en un hook `pre-commit` se difiere a F3, junto con un
workflow de GitHub Actions que ejecute el ciclo completo de
pytest + traceability + `check_scenario_yaml.py` en cada push.

En F2 la garantía de que la suite no regresiona descansa en la
disciplina del autor de ejecutar `pytest` antes de cada commit
relevante; F3 sustituirá esta disciplina por automatización del
repositorio.

---

## 6.6 Validación end-to-end y métricas preliminares  [BORRADOR D34]

### 6.6.1 Demostración integrada

La validación end-to-end de Fase 2 es una corrida de 3 minutos del
sistema completo en Gazebo con el baseline PD como controlador, la
cage en modo `enforcement`, el logger activo, y una perturbación
inducida intencionalmente al inicio (heading_error = 0.3 rad en el
spawn) para forzar al menos una activación de cage observable.

La demostración pasa si: el vehículo completa al menos 3 vueltas
completas al óvalo sin entrar en modo emergencia; la cage interviene
durante la perturbación inicial y libera tras estabilización; el
logger captura todos los mensajes sin pérdida; los archivos de
salida tienen la estructura esperada y son legibles por los scripts
de análisis preliminares.

El run candidato para el cierre de D34 es
`ros_run_20260523T073134Z` (PD baseline 0.8.0, cage YAML 0.5.1,
escenario SC-NOM-01, modo `enforcement`, perímetro ODD-3 = 8.0232 m).
La demostración cumple los cuatro criterios:

- El vehículo recorre 36.14 m, equivalentes a 4.50 vueltas
  completas frente al objetivo de 3, en 379.8 s
  (≈ 84.4 s por vuelta a velocidad media 0.095 m/s).
- La cage interviene en 8 ciclos de los 7 597 totales, distribuidos
  entre C-02 (6 activaciones) y C-06 (7 activaciones, en combinación
  con C-02 en 5 de los 8 ciclos); las reglas C-01, C-03 y C-05 no
  se activan durante toda la corrida, consistente con un PD que se
  mantiene dentro del régimen nominal del óvalo.
- No se registra ningún ciclo en modo emergencia.
- El logger captura 7 597 filas sin pérdida y los scripts de
  análisis preliminares procesan el CSV sin errores; los hashes
  SHA-256 de `cage.yaml`, `baseline_pd.yaml`, world y centerline
  quedan registrados en `metadata.json` para reproducibilidad.

Nota metodológica: la perturbación intencional de spawn
(`heading_error = 0.3 rad`) anticipada al diseñar la sección no
se aplicó en este run, que parte del estado nominal del launch.
Las activaciones de C-01/C-03 bajo perturbación quedan diferidas
al run de robustez previsto antes de tagear G2 (ver §6.6.2 y
apéndice).

### 6.6.2 Métricas preliminares

Tres métricas se reportan preliminarmente en este capítulo, no como
resultado experimental sino como evidencia de que el pipeline funciona.
La caracterización completa pertenece al Capítulo 8.

La primera es la **latencia del ciclo de la cage**. Se mide como
diferencia entre timestamps consecutivos publicados por
`cage_logger_node` sobre 379.8 s de operación. Resultado preliminar:
mediana 50.0 ms, P95 50.0 ms, máximo 53.0 ms, todos dentro del
presupuesto de 50 ms del SR-006 (el máximo de 53 ms corresponde a
un único ciclo y se atribuye a jitter del scheduler de Linux no
realtime). La latencia *sensor → safe_action* desglosada por etapa
requiere instrumentación adicional de timestamps y se difiere a F3.

La segunda es la **tasa de intervención de la cage** durante
operación nominal con el PD como controlador. Sobre los 7 597
ciclos del run `ros_run_20260523T073134Z`, la cage interviene en
8 ciclos (0.105% del total), todos atribuidos a C-02 (límite de
heading) y/o C-06 (rate limiter de la acción), sin activaciones de
C-01, C-03 ni C-05. La interpretación es: si el PD circula sin
salirse del régimen donde la cage actúa, esa tasa debe ser muy baja
(< 5%). El valor observado, dos órdenes de magnitud por debajo del
umbral, confirma que el PD 0.8.0 está bien calibrado para el
escenario nominal y que los umbrales de la cage no son
artificialmente restrictivos.

La tercera es el **completion rate** del PD en condiciones
nominales: porcentaje de vueltas completas del óvalo sin que la
cage entre en modo emergencia. Sobre la única corrida candidata
disponible al cierre de D34, el PD completa 4.50 vueltas (objetivo
≥ 3) sin emergencia, equivalente a un completion rate provisional
de 100% con N = 1 ejecución. La caracterización completa con N = 30
vueltas seguidas exige una campaña de runs múltiples actualmente
en cola; un completion rate consolidado por encima del 80% es el
criterio de Decisión 6 del briefing del supervisor. Valores menores
indicarían que el PD necesita más tuning o que hay un problema
estructural en el pipeline.

Estas tres métricas no son los resultados experimentales de la tesis;
son evidencia de funcionamiento del pipeline antes de introducir el
RL en la Fase 3. La interpretación de cada una se desarrolla en el
Capítulo 8 cuando se compare contra el RL.

---

## 6.7 Síntesis y transición al Capítulo 7  [BORRADOR D35]

Este capítulo ha completado la materialización ejecutable de la rama
izquierda inferior del V-Model adaptado para el caso lane-following.
Cinco nodos ROS2 están operativos; el entorno Gazebo modela un
vehículo 1:14 en una pista oval de 4 m × 2.5 m; la cage implementa
las seis reglas de la especificación con su lógica determinista, sus
parámetros versionados y sus modos de operación; la suite de tests
(unitarios, de propiedades, de integración) verifica el cumplimiento
de la especificación; el baseline PD valida el pipeline end-to-end y
proporciona los primeros datos de log para los scripts de análisis.

La pasada del Gate 2 marca el primer hito sustancial de la tesis y
señala una transición importante en el modo de trabajo. Hasta este
punto el trabajo era principalmente de diseño y construcción
estática: especificar, implementar, verificar contra la especificación.
A partir del Capítulo 7 el trabajo se vuelve experimental: entrenar
una policy RL es un proceso estocástico cuyos resultados emergen
empíricamente y deben caracterizarse estadísticamente. La
infraestructura construida en este capítulo es la base sobre la que
ese trabajo experimental se hará tratable.

Una observación metodológica relevante para el Capítulo 7 es que los
logs producidos por el PD durante esta fase ya contienen información
sobre la dinámica del sistema que informará el diseño del entorno de
entrenamiento del RL. La distribución de lateral_offset y de
heading_error durante una vuelta nominal del PD da pistas sobre la
distribución que la policy RL deberá manejar. Las activaciones
ocasionales de la cage durante la perturbación inicial dan pistas
sobre los regímenes que el reward debe penalizar específicamente.
Esta lectura cuidadosa de los logs es la primera tarea del
Capítulo 7.

El Capítulo 7 desarrolla la *Training Specification* (segundo
artefacto resultante de la adaptación A1) y la ejecución del
entrenamiento PPO en el entorno de simulación; el Capítulo 8 evalúa
estadísticamente la policy resultante sobre la *scenario library*
(L4b'); los Capítulos 9 y 10 cierran la rama derecha del V-Model con
la caracterización del gap sim-to-real y el verdicto de validación
acotada.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Fase 2 (D26–D35):
  [x] Estructura de secciones 6.1–6.7 fijada en D26
  [x] Borrador de §6.2 (Gazebo) en D25 al cerrar la implementación
  [x] Borrador de §6.3.1 (patrón común) en D26
  [x] Borrador de §6.3.2 (Perception) en D26
  [x] Borrador de §6.3.3 (Vehicle Control) en D27
  [x] Borrador de §6.3.4 (Cage) en D28-D29
  [x] Borrador de §6.3.5 (Logger) en D30
  [x] Borrador de §6.4 (PD) en D32
  [x] Borrador de §6.5 (testing) en D33
  [x] Borrador de §6.6 (validación end-to-end) en D34 con placeholders
  [x] Síntesis §6.7 escrita en D35

Pendientes obligatorios para cierre de Gate 2 (D35):
  [x] Rellenar todos los [COMPLETAR FASE 2] con cifras reales
       (run candidato ros_run_20260523T073134Z, 2026-05-23):
       - [x] throughput del logger en §6.3.5 y §6.5.4
       - [x] número exacto de tests unitarios en §6.5.2 (61 per-rule,
              132 cage total, 143 con PD)
       - [x] resultados del test de demostración en §6.6.1
              (4.50 vueltas, 0 emergencias, 8 intervenciones)
       - [x] latencia, tasa de intervención, completion rate en §6.6.2
              (50.0/50.0/53.0 ms; 0.105%; 100% con N=1)
       - [x] ganancias finales del PD en §6.4.2 (v0.8.0)
  [ ] Generar Figura 6.1 (vista superior del mundo Gazebo)
  [x] Generar Listing 6.1 (esqueleto de apply_c01) — extraído de
       cage/rules/c01_lane_boundary.py
  [ ] Campaña de runs múltiples (N≥30 vueltas) para consolidar
       completion rate frente al umbral del 80% de la Decisión 6;
       sustituye al N=1 provisional anotado en §6.6.2
  [ ] Verificar coherencia con Capítulo 5 (todos los IDs, parámetros
       y nombres de topics deben coincidir bit-a-bit)
  [ ] Ejecutar `check_traceability.py` y verificar que todas las
       reglas tienen tests asociados (columna que se añadió en D33)

Fase 3 (D36+):
  [ ] Añadir nota cruzada al Capítulo 7 cuando esté escrito sobre
       la integración del RL en el pipeline
  [ ] Verificar si el patrón de testing por reglas se mantiene
       cuando la policy RL sustituya al PD

Fase 4–5 (operacionalización):
  [ ] Añadir resultados de tests con escenarios realistas en §6.5
  [ ] Documentar diferencias de implementación al portar al físico
       en una sección 6.X (a decidir si va aquí o en el Capítulo 9)

Fase 6 (consolidación):
  [ ] Pulido de prosa: pasar §6.3 de tono "documentación técnica" a
       tono "tesis académica" (suavizar imperativos, conectores
       académicos, eliminar referencias a días concretos como D27)
  [ ] Sustituir [COMPLETAR FASE 2] por valores definitivos
  [ ] Verificar formato bibliográfico
  [ ] Decisión: ¿incluir un diagrama de secuencia (sequence diagram)
       de un ciclo de control completo en §6.3.4 para ilustrar el
       flujo Cage?
  [ ] Decisión: ¿añadir tabla resumen de la suite de tests con
       columnas (regla, propósito, casos cubiertos) al final de §6.5?
-->
