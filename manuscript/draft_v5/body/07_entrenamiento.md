# Capítulo 7 — Especificación de entrenamiento y ejecución

## 7.1 Propósito del capítulo

Este capítulo desarrolla la segunda mitad de la adaptación A1: la **Training Specification**. Es una meta-especificación, no una especificación de comportamiento. No dice qué hará la policy ante un estado dado —no puede decirlo— sino que fija con precisión el **proceso que la produce**: espacios de observación y acción, función de recompensa, criterios de terminación, papel de la cage durante el entrenamiento, hiperparámetros, semillas y política de puntos de control. Un lector que disponga de este documento y del código puede reproducir el proceso; no puede predecir el resultado. Esa asimetría es exactamente el punto de la adaptación.

La tabla completa de hiperparámetros y el estudio comparativo entre algoritmos, con sus ocho configuraciones y sus puntos de control evaluados, se recogen en el **Anexo H**.

## 7.2 Especificación del proceso

### 7.2.1 Observación y acción

La observación del sistema de referencia es la **imagen de la cámara frontal**, reducida a 84×84 en escala de grises y apilada en cuatro fotogramas consecutivos para dotar a la política de información de movimiento. El apilado no es un detalle de implementación: sin él la política no puede distinguir una situación estática de una dinámica, y el error de rumbo se vuelve parcialmente inobservable. La red es una convolucional estándar del tipo usado en control desde píxeles.

El espacio de acción es **configuración, no constante del trabajo**, y el recorrido entre sus dos valores es una de las líneas argumentales del capítulo. Durante la mayor parte del proyecto la acción fue **unidimensional** —solo dirección, con velocidad longitudinal fija—, lo que reduce el problema a control lateral y mantiene limpia la separación entre lo que la recompensa guía y lo que la cage garantiza. La configuración de referencia final es **bidimensional** —dirección y tracción—, con un techo de velocidad de 0,22 m/s y una banda muerta en el mando de tracción. La consecuencia es sustantiva: en 1-D las reglas de velocidad de la cage son **estructuralmente inertes**, porque la velocidad no es una variable de decisión; solo con autoridad longitudinal pueden arbitrar de verdad.

### 7.2.2 Función de recompensa

La recompensa combina cuatro términos: **progreso** a lo largo del arco del circuito, que es la señal de tarea; **penalización del error lateral**, que la centra en el carril; **penalización del error de rumbo**, que la alinea con la tangente; y **penalización de la variación de mando**, que desincentiva el pilotaje a tirones. En la configuración bidimensional se añade un quinto término contra el óptimo degenerado de **detenerse**: sin él, una política con autoridad sobre la tracción descubre que aparcar evita todas las penalizaciones, un caso de manual del peligro de explotación de la recompensa que el registro de peligros anticipaba.

Conviene explicitar la relación entre recompensa y seguridad, porque es una de las decisiones de diseño más importantes del trabajo: **la recompensa no contiene términos de seguridad**. No penaliza la activación de la cage ni premia mantenerse lejos del límite. La razón es de separación de responsabilidades —la recompensa guía, la cage garantiza— y tiene una consecuencia experimental valiosa: como la policy no fue entrenada para complacer a la cage, la frecuencia con que la cage interviene es una **medida no contaminada** de la calidad de la conducción aprendida.

### 7.2.3 La cage durante el entrenamiento

La cage está **activa en el lazo de entrenamiento**, filtrando el comando antes de que llegue al vehículo simulado. La decisión tiene ventajas evidentes: los episodios no se malgastan en excursiones catastróficas y el agente experimenta la dinámica del sistema tal como será desplegado. Tiene también un coste que el trabajo no anticipó por completo y que el Capítulo 8 documenta como hallazgo: si la cage integra el comando durante el entrenamiento, **la policy aprende contra un sistema que ya incluye a la cage**, y lo que se optimiza es la pareja y no la política sola.

### 7.2.4 Reproducibilidad

Cada ejecución de entrenamiento registra semilla, versión de configuración, *hash* del fichero de parámetros de la cage, revisión del código y marca temporal. Los puntos de control se guardan con cadencia fija y cada uno lleva un identificador criptográfico que lo liga a su configuración; una evaluación que intente cargar un punto de control con una configuración incompatible **falla de forma explícita** en lugar de producir un resultado silenciosamente inválido. Es un mecanismo modesto que evitó al menos una confusión seria durante el proyecto.

## 7.3 Resultados: la política de cámara unidimensional

La primera política de cámara competente se entrena sobre el circuito sinuoso con acción unidimensional. Su recompensa media por episodio asciende hasta un **pico de ≈ 823 hacia los 297 000 pasos** y mantiene una banda alta durante unos 150 000 pasos más, tras lo cual **decae**. El diagnóstico importa: la pérdida del crítico permanece minúscula durante todo el recorrido, de modo que **no es inestabilidad de la función de valor sino contracción de la exploración** una vez que la desviación típica de la política se recoce en exceso. Por eso la política que se conserva es la del pico y no la del final.

<img src="../figures/fig_7_1_convergence_newcam.png" alt="Figura 7.1 — Convergencia del entrenamiento de cámara unidimensional." width="540"/>

*Figura 7.1 — Convergencia de la política de cámara unidimensional: recompensa y longitud media de episodio frente a pasos. Pico ≈ 823 y meseta alta; el colapso posterior de exploración motivó la parada manual y la selección del punto de control en el pico.*

Un segundo resultado de este entrenamiento es la **co-adaptación entre policy y cage**: la tasa de intervención desciende de ~87 % al inicio a ~40 %, **dominada por el limitador de tasa**, mientras las reglas de seguridad caen a cero. La lectura es que la policy aprende a respetar las restricciones de seguridad —no se acerca al borde— pero su mando de dirección sigue siendo a tirones y el limitador lo suaviza de forma continua.

La evaluación nominal determinista contra un controlador clásico sobre el mismo circuito arroja el resultado que justifica el coste del componente aprendido:

| Métrica (escenario nominal) | Baseline clásico | **RL cámara 1-D** |
| --- | --- | --- |
| Vueltas completadas | 4,85 | 4,88 |
| Error lateral medio | 17,2 mm | **10,9 mm** |
| Error lateral máximo | 57,3 mm | 48,2 mm |
| Paradas de emergencia | 0 | **0** |
| Intervención de la cage | 0 % | 43,5 % (solo limitador) |

*Tabla 7.1 — Evaluación nominal: política de cámara frente al baseline clásico sobre el mismo circuito.*

El agente **bate al baseline clásico en precisión de seguimiento** —un 37 % menos de error lateral medio, a la misma distancia recorrida y con cero emergencias—, lo que **invierte el hallazgo obtenido sobre el óvalo**, donde el controlador clásico era el más preciso: sobre una geometría sinuosa el punto de mira del método clásico se degrada mientras la red sostiene la línea. Dos observaciones cualitativas acompañan al resultado. La cage queda **latente dentro del dominio en ambos modos**: cero emergencias y ninguna activación de las reglas de seguridad, solo del limitador de tasa; enforcement y monitoring dan vueltas y errores casi idénticos. Y el coste del agente aprendido **no es seguridad sino suavidad**: dispara el limitador en el 43 % de los pasos frente al 0 % del controlador clásico, una intervención benigna que absorbe el tirón sin dañar la precisión.

## 7.4 Variabilidad entre semillas

Un resultado con una sola semilla no dice nada sobre un procedimiento estocástico. La replicación sobre cinco semillas produce el hallazgo más incómodo y probablemente más útil del capítulo: **la curva de entrenamiento no clasifica el comportamiento**. Tres de las cinco semillas resultan respetuosas con las restricciones —la cage permanece latente— mientras que las otras dos dependen de la cage de forma sustantiva, con centenares de intervenciones de seguridad, y **esa diferencia no es predecible desde la recompensa de entrenamiento**: semillas con curvas prácticamente indistinguibles caen a lados distintos.

La consecuencia metodológica es directa y se aplica al resto del trabajo: **la selección de la política no puede hacerse por recompensa**. Debe hacerse por evaluación en lazo cerrado sobre escenarios, con la tasa de intervención de la cage como criterio de primer orden. Es un ejemplo concreto de aquello que el marco pretende: un criterio de aceptación que ninguna métrica de entrenamiento habría producido.

## 7.5 La política de referencia: acción bidimensional

### 7.5.1 Motivación y elección de algoritmo

El primer intento de campaña completa sobre acción bidimensional se ejecutó con una política **doblemente subóptima**: algoritmo fuera de su régimen, entrenamiento corto y, peor aún, un punto de control **posterior al pico** en lugar del pico. Su resultado dejó una pregunta bien planteada: ¿los fallos observados eran **de la acción bidimensional** o **de aquella política**? Para responderla se entrenó una política bidimensional en condiciones, con dos cambios, ambos medidos.

**Algoritmo.** Una política entrenada con el método en política alcanza una recompensa media de **1755 hacia los 472 000 pasos** con meseta alta y estable, mientras el método fuera de política nunca supera ~200 y no llega a dominar el circuito. **Techo de velocidad.** Una comparación de una sola variable muestra que a 0,5 m/s la política pica en 654 y traza sucio —se pasa de las curvas cerradas— frente a 1421 a 0,22 m/s, donde las traza limpio.

Una advertencia de honestidad sobre las cifras: la recompensa **no es comparable uno a uno entre espacios de acción**, porque el techo de episodio se duplica al pasar a dos dimensiones. El factor ~2 frente a la política unidimensional es sobre todo mayor supervivencia y horizonte, no «el doble de buena conducción».

<img src="../figures/auto/fig_ppo2d_training_curve.png" alt="Figura 7.2 — Curva de entrenamiento de la política bidimensional de referencia." width="600"/>

*Figura 7.2 — Recompensa de entrenamiento de la política **bidimensional** de referencia frente a la unidimensional y a la variante fuera de política. Pico 1755 y meseta alta estable, frente al colapso posterior al pico de la primera y al techo de ~200 de la segunda. Los puntos de control candidatos evaluados aparecen marcados.*

### 7.5.2 Selección del punto de control: por conducción, no por recompensa

Durante todo el entrenamiento la cage permanece **latente en seguridad**: ninguna activación de las reglas de límite lateral, rumbo, predictiva ni emergencia; solo del limitador de tasa. La selección se resolvió evaluando tres candidatos en lazo cerrado, y el resultado confirma la lección de §7.4 de la forma más nítida posible: **el punto de control del pico de recompensa es el peor de los tres** —catorce intervenciones de seguridad y 49 mm de error lateral máximo— mientras que el de 550 000 pasos gana con claridad: **5,32 vueltas, 8,6 mm de error medio, 27 mm de máximo, cero emergencias y cero intervenciones de seguridad**.

Elegir por recompensa habría seleccionado el peor candidato. Es un control anticiparon-el-sesgo documentado **antes** de ejecutar la campaña de veredicto, y es la respuesta directa a la objeción de que se haya seleccionado el mejor brazo a posteriori.

### 7.5.3 Qué hace la política con la autoridad longitudinal

<img src="../figures/auto/fig_ppo2d_action_distribution.png" alt="Figura 7.3 — Distribución de la acción cruda bidimensional." width="640"/>

*Figura 7.3 — Distribución de la **acción cruda** al inicio frente al final del entrenamiento, un panel por dimensión. En **dirección**, el mando de todo-o-nada inicial se disuelve (36,9 % → 7,1 % de muestras saturadas). En **tracción**, la evolución es la contraria, hacia la saturación (48,2 % → 89,6 %): la política aprende a pedir el techo casi siempre.*

La lectura honesta de la autoridad longitudinal es que la política la usa para **fijar el régimen de velocidad, no para trazar un perfil**. Hay modulación y está bien localizada —el 8,3 % de pasos con tracción reducida se concentra en curvatura alta y sube al 35,6 % en el ápice más cerrado—, pero su **magnitud es marginal**: la tracción baja a 0,81 y la velocidad apenas cae de 0,218 a 0,216 m/s. La política llega a las curvas más cerradas prácticamente al techo. Esta observación, aparentemente menor, explica un resultado del Capítulo 8: la regla de velocidad de la cage **nunca llega a activarse en toda la campaña**.

### 7.5.4 Autorización previa a la campaña

Antes de ejecutar la campaña de veredicto, la política superó una **verificación previa ligada por identificador criptográfico** a su punto de control y a su configuración, que comprueba que la interfaz de medida de la cage —el estimador de carril y su lectura de rumbo— se comporta como debe: fallos reales de rumbo detectados, cero falsos positivos sobre ciclos centrados seguros y retardo acotado. La verificación **pasó en sus siete comprobaciones**, y es la que autoriza la campaña.

El orden importa metodológicamente: la política se selecciona por evaluación nominal, la instrumentación se verifica por separado y ligada por *hash*, y solo entonces se ejecuta la campaña. Ninguno de los tres pasos puede reordenarse sin debilitar la evidencia.

## 7.6 Síntesis

El capítulo deja tres resultados que el siguiente utiliza. Primero, existe una política de cámara competente y la referencia contra un método clásico está establecida. Segundo, **la curva de entrenamiento no clasifica el comportamiento**: la selección debe hacerse por conducción en lazo cerrado, y ese criterio, aplicado a la política de referencia, descartó precisamente el punto de control que la recompensa habría elegido. Tercero, la política de referencia tiene autoridad longitudinal pero la usa para fijar el régimen, no para modular, lo que condiciona qué reglas de la cage llegan a ejercitarse.

El Capítulo 8 somete esa política a la campaña de escenarios y produce el veredicto.
