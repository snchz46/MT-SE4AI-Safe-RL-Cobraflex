# Capítulo 7 — Especificación de entrenamiento y ejecución

## 7.1 Propósito del capítulo

Este capítulo trata la segunda mitad de la adaptación A1: la Training Specification. Es una meta-especificación, no una especificación de comportamiento. No dice qué hará la policy en un estado dado, porque no puede. Lo que hace es fijar el proceso que produce la policy: espacios de observación y acción, función de recompensa, criterios de terminación, papel de la cage durante el entrenamiento, hiperparámetros, semillas y cómo se guardan los puntos de control. Quien tenga este documento y el código puede repetir el proceso, pero no puede predecir el resultado. Esa diferencia es justo la idea de la adaptación.

La tabla completa de hiperparámetros y la comparación entre algoritmos, con sus ocho configuraciones y los puntos de control evaluados, están en el Anexo H.

## 7.2 Especificación del proceso

### 7.2.1 Observación y acción

La observación del sistema de referencia es la imagen de la cámara frontal, reducida a 84×84 en escala de grises y apilada en cuatro fotogramas seguidos para que la política tenga información sobre el movimiento. El apilado no es un detalle menor. Sin él, la política no puede distinguir una situación quieta de una en movimiento, y el error de rumbo pasa a ser parcialmente inobservable. La red es una red convolucional estándar, del tipo que se usa para controlar desde píxeles.

El espacio de acción es una opción de configuración, no algo fijo en todo el trabajo, y cómo cambió entre sus dos valores es uno de los hilos principales de este capítulo. Durante la mayor parte del proyecto la acción fue unidimensional: solo dirección, con velocidad de avance fija. Esto reduce el problema al control lateral y separa con claridad lo que guía la recompensa de lo que garantiza la cage. La configuración de referencia final es bidimensional, con dirección y tracción, un techo de velocidad de 0,22 m/s y una banda muerta en el mando de tracción. Esto importa mucho. En 1-D, las reglas de velocidad de la cage no pueden hacer nada nunca, porque la velocidad no la decide la política. Solo cuando la política controla la velocidad pueden esas reglas intervenir de verdad.

### 7.2.2 Función de recompensa

La recompensa tiene cuatro términos: el avance a lo largo del circuito, que es la señal de la tarea; una penalización por error lateral, que mantiene el vehículo centrado en el carril; una penalización por error de rumbo, que lo mantiene alineado con la pista; y una penalización por los cambios de mando, que desanima la conducción a tirones. En la configuración bidimensional se añade un quinto término para evitar que la política simplemente se pare. Sin él, una política que controla la tracción descubre que aparcar evita todas las penalizaciones. Es un caso de manual del peligro de explotación de la recompensa que el registro de peligros ya había previsto.

Hay que dejar clara la relación entre recompensa y seguridad, porque es una de las decisiones de diseño más importantes del trabajo: la recompensa no tiene términos de seguridad. No penaliza que la cage se active ni premia mantenerse lejos de los límites. El motivo es un reparto de responsabilidades: la recompensa guía, la cage garantiza. Esto tiene una ventaja para los experimentos. Como la policy no se entrenó para contentar a la cage, la frecuencia con la que la cage interviene es una medida limpia de lo buena que es la conducción aprendida.

### 7.2.3 La cage durante el entrenamiento

La cage está activa en el lazo de entrenamiento y filtra el comando antes de que llegue al vehículo simulado. Esto tiene ventajas claras: no se pierden episodios en choques, y el agente aprende la dinámica del sistema tal como se va a desplegar. También tiene un coste que este trabajo no esperaba del todo y que el Capítulo 8 recoge como hallazgo. Si la cage modifica el comando durante el entrenamiento, la policy aprende frente a un sistema que ya incluye la cage, así que lo que se optimiza es la pareja y no la política sola.

### 7.2.4 Reproducibilidad

Cada entrenamiento guarda la semilla, la versión de la configuración, el *hash* del fichero de parámetros de la cage, la revisión del código y una marca de tiempo. Los puntos de control se guardan a intervalos fijos, y cada uno tiene un identificador criptográfico que lo liga a su configuración. Si una evaluación intenta cargar un punto de control con una configuración que no coincide, falla con un error en lugar de dar en silencio un resultado inválido. Es un mecanismo sencillo, y evitó al menos una confusión seria durante el proyecto.

El texto usa nombres descriptivos para los entrenamientos, puntos de control y campañas, mientras que las figuras y los anexos usan las etiquetas cortas del repositorio. La Tabla 7.1 relaciona unos con otras.

| Etiqueta en figuras y anexos | Nombre en el texto | Qué es |
| --- | --- | --- |
| `F-track` | Track de estado (brazo de control) | La política observa un vector de estado proyectado desde la pose verdadera, en el circuito oval; aísla el efecto de la cage (§1.6.3). Campaña: `campaign`. |
| `track E`, `E-track` | Track de cámara | La política observa la imagen de la cámara frontal; es el sistema de referencia de la tesis. |
| `E-main`, `1-D PPO`, `297k` | Política de cámara unidimensional | PPO, solo dirección a velocidad fija de 0,20 m/s en `complex_b`; punto de control guardado en el pico de recompensa, 297.000 pasos (§7.3). Ejecución: `ppo_newcam_complex_b_2024_1M`. |
| `seed 2024`, `42`, `23`, `666`, `123` | Las cinco semillas | Copias de ese entrenamiento que solo cambian en la semilla (§7.4). Ejecuciones: `ppo_newcam_complex_b_<semilla>`. |
| `GE4-V2`, `campaign_e_v2` | Campaña de la política unidimensional | Segunda versión de la campaña de escenarios de la puerta G4, ejecutada sobre `E-main`: 1.970 corridas, guardada congelada como registro de la puerta. |
| `margin022`, `2-D SAC` | Primera campaña bidimensional | SAC, dirección y acelerador, techo de velocidad 0,22 m/s, que es 0,03 m/s menos que el techo en curva de 0,25 m/s de C-04 (de ahí el nombre); punto de control a 75.000 pasos; 1.970 corridas (§7.5.1). Ejecución: `sac_gz2d_entfix_margin022_2024_75k`; campaña: `campaign_2d_margin022`. |
| `2-D PPO 550k`, `cap 0.22` | Política y campaña de referencia | PPO, dirección y acelerador, techo de velocidad 0,22 m/s; punto de control a 550.000 pasos elegido por conducción en lazo cerrado (§7.5.2); su campaña de 1.890 corridas da el veredicto (Capítulo 8). Ejecución: `ppo_gz2d_cap022_1M_2024`; campaña: `campaign_2d_ppo550k`. |
| `sim-to-real v2`, `1650k` | Política reentrenada para transferir | PPO bidimensional reentrenada con espejado por episodio y aleatorización de fotometría y de geometría de cámara, 2,5 millones de pasos; punto de control a 1.650.000 pasos desplegado en el vehículo (§9.3.4). Su `v2` no tiene nada que ver con `GE4-V2`. Ejecución: `ppo_gz2d_sim2real_v2_2024`. |

*Tabla 7.1 — Nombres de entrenamientos, puntos de control y campañas. Convenciones: `k` detrás de un número cuenta miles de pasos de entrenamiento (`550k` = 550.000; `@297k` = a los 297.000 pasos); `1-D` y `2-D` indican el tamaño de la acción (dirección; dirección y acelerador); `cap` es el techo de velocidad de la acción; `complex_b` es el circuito sinuoso (perímetro 19,22 m) y `oval` el oval (R = 0,8 m); `newcam` en el nombre de una ejecución marca las hechas después del cambio a la cámara dedicada de carril.*

## 7.3 Resultados: la política de cámara unidimensional

La primera política de cámara que conduce bien se entrena en el circuito sinuoso con acción unidimensional. Su recompensa media por episodio sube hasta un pico de ≈ 823 hacia los 297 000 pasos, se mantiene alta unos 150 000 pasos más y después baja. La causa importa. La pérdida del crítico se mantiene muy pequeña durante todo el entrenamiento, así que el problema no es una función de valor inestable. Lo que pasa es que la exploración se reduce cuando la desviación típica de la política se recuece demasiado. Por eso se guarda la política del pico y no la del final.

<img src="../figures/fig_7_1_convergence_newcam_notitle.png" alt="Figura 7.1 — Convergencia del entrenamiento de cámara unidimensional." width="540"/>

*Figura 7.1 — Convergencia de la política de cámara unidimensional (`E-main`, Tabla 7.1): recompensa y longitud media de episodio frente a pasos. Pico ≈ 823 y meseta alta. El colapso posterior de la exploración llevó a parar el entrenamiento a mano y a quedarse con el punto de control del pico.*

Un segundo resultado de este entrenamiento, que la Figura 7.2 desglosa, es que policy y cage se adaptan la una a la otra. La tasa de intervención baja de ~87 % al principio a ~40 %, sobre todo por el limitador de tasa, mientras que las reglas de seguridad caen a cero. Esto quiere decir que la policy aprende a respetar las restricciones de seguridad (no se acerca al borde), pero su dirección sigue siendo a tirones y el limitador la va suavizando todo el tiempo.

<img src="../figures/fig_7_2_intervention_newcam_notitle.png" alt="Figura 7.2 — Actividad de la cage durante el entrenamiento." width="540"/>

*Figura 7.2 — Actividad de la cage durante el entrenamiento unidimensional. Arriba: la tasa total de intervención baja de ~87 % a ~40 %, mientras que la tasa de emergencia es cero desde el principio. Abajo: el desglose por regla muestra de qué está hecha esa tasa. Es el limitador de tasa. Las reglas de seguridad C-01, C-02, C-03 y C-05 caen a cero en los primeros pasos y se quedan ahí.*

La evaluación nominal determinista frente a un controlador clásico en el mismo circuito, que muestra la Tabla 7.2, da el resultado que justifica el coste del componente aprendido:

| Métrica (escenario nominal) | Baseline clásico | **RL cámara 1-D** |
| --- | --- | --- |
| Vueltas completadas | 4,85 | 4,88 |
| Error lateral medio | 17,2 mm | 10,9 mm |
| Error lateral máximo | 57,3 mm | 48,2 mm |
| Paradas de emergencia | 0 | 0 |
| Intervención de la cage | 0 % | 43,5 % (solo limitador) |

*Tabla 7.2 — Evaluación nominal: política de cámara frente al baseline clásico en el mismo circuito.*

El agente es más preciso que el baseline clásico: un 37 % menos de error lateral medio, en la misma distancia y con cero emergencias. Es lo contrario de lo que pasó en el óvalo, donde el controlador clásico era el más preciso. En un trazado sinuoso, el punto de mira del método clásico pierde fiabilidad, mientras que la red mantiene su línea. Hay dos observaciones más. La cage queda latente dentro del dominio en los dos modos: cero emergencias y ninguna activación de reglas de seguridad, solo del limitador de tasa, y enforcement y monitoring dan casi las mismas vueltas y los mismos errores. Y el coste del agente aprendido es la suavidad, no la seguridad. Activa el limitador en el 43 % de los pasos, frente al 0 % del controlador clásico. Esta intervención no hace daño: absorbe los tirones de la dirección sin perjudicar la precisión.

## 7.4 Variación entre semillas

Un resultado con una sola semilla no dice nada sobre un procedimiento estocástico. Repetir el entrenamiento con cinco semillas, como muestra la Figura 7.3, da el hallazgo más incómodo y seguramente el más útil del capítulo: la curva de entrenamiento no dice cómo se comporta la política. Tres de las cinco semillas respetan las restricciones (la cage se queda latente), mientras que las otras dos dependen mucho de la cage, con cientos de intervenciones de seguridad. Esta diferencia no se puede predecir a partir de la recompensa de entrenamiento. Semillas con curvas casi idénticas acaban en lados distintos.

<img src="../figures/fig_7_8_multiseed_newcam_notitle.png" alt="Figura 7.3 — Comparación entre cinco semillas." width="540"/>

*Figura 7.3 — Cinco semillas del mismo procedimiento (Tabla 7.1; `@297k` marca el paso de cada pico). Arriba: la recompensa. Las curvas son parecidas y sus picos van de 713 a 823, sin que ninguna destaque sobre las demás. Abajo: la tasa de intervención de la cage para las mismas ejecuciones, que sí las separa. La información que distingue los comportamientos está en el panel de abajo, no en el de arriba, y es justo el panel que una selección por recompensa no mira.*

La consecuencia para el método es directa y vale para el resto del trabajo: la política no se puede elegir por recompensa. Hay que elegirla con evaluación en lazo cerrado sobre escenarios, usando la tasa de intervención de la cage como criterio principal. Es un ejemplo concreto de lo que el marco busca producir: un criterio de aceptación que ninguna métrica de entrenamiento habría dado.

## 7.5 La política de referencia: acción bidimensional

### 7.5.1 Motivación y elección del algoritmo

El primer intento de campaña completa con acción bidimensional usó una política floja por dos motivos: un algoritmo usado fuera del rango en el que funciona bien y un entrenamiento corto. Y, peor aún, el punto de control era posterior al pico en lugar de ser el del pico. Su resultado dejó una pregunta clara: ¿los fallos venían de la acción bidimensional o de esa política en concreto? Para responderla se entrenó una política bidimensional como es debido, con dos cambios, los dos medidos.

**Algoritmo.** Una política entrenada con el método en política llega a una recompensa media de 1755 hacia los 472 000 pasos (Figura 7.4), con una meseta alta y estable. El método fuera de política nunca pasa de ~200 y no llega a aprender a conducir el circuito. **Techo de velocidad.** Una comparación que solo cambia esta variable muestra que a 0,5 m/s la política llega a un pico de 654 y conduce mal (se pasa en las curvas cerradas), frente a 1421 a 0,22 m/s, donde las toma limpiamente.

Una advertencia sobre estas cifras: la recompensa no se puede comparar directamente entre espacios de acción, porque la recompensa máxima por episodio se duplica al pasar a dos dimensiones. El factor ~2 respecto a la política unidimensional viene sobre todo de sobrevivir más tiempo y de un horizonte más largo, no de «conducir el doble de bien».

<img src="../figures/auto/fig_7_4_ppo2d_training_curve.png" alt="Figura 7.4 — Curva de entrenamiento de la política bidimensional de referencia." width="600"/>

*Figura 7.4 — Recompensa de entrenamiento de la política bidimensional de referencia (`2-D PPO`) comparada con la unidimensional (`E-main`) y con la versión fuera de política (`margin022`); etiquetas en la Tabla 7.1. Pico 1755 y meseta alta y estable, frente al colapso después del pico de la primera y el techo de ~200 de la segunda. Están marcados los tres puntos de control candidatos evaluados en lazo cerrado, incluido el elegido, y el punto de control guardado de cada una de las otras dos ejecuciones.*

### 7.5.2 Elegir el punto de control: por conducción, no por recompensa

Durante todo el entrenamiento, la cage se mantiene latente en cuanto a seguridad: las reglas de límite lateral, rumbo, predictiva y emergencia no se activan nunca, solo el limitador de tasa. La elección se hizo probando tres candidatos en lazo cerrado, y el resultado confirma muy claramente la lección de §7.4. El punto de control del pico de recompensa es el peor de los tres, con catorce intervenciones de seguridad y 49 mm de error lateral máximo. El de 550 000 pasos gana con claridad: 5,32 vueltas, 8,6 mm de error medio, 27 mm de máximo, cero emergencias y cero intervenciones de seguridad.

Elegir por recompensa habría llevado al peor candidato. Es un control contra el sesgo documentado antes de ejecutar la campaña de veredicto, y responde directamente a la objeción de que se eligió la mejor opción después de ver los resultados.

### 7.5.3 Qué hace la política con el control de la velocidad

<img src="../figures/auto/fig_7_5_ppo2d_action_distribution.png" alt="Figura 7.5 — Distribución de la acción cruda bidimensional." width="640"/>

*Figura 7.5 — Distribución de la acción cruda al principio y al final del entrenamiento, un panel por dimensión. En dirección, el mando de todo o nada del principio desaparece (36,9 % → 7,1 % de muestras saturadas). En tracción, el cambio va en sentido contrario, hacia la saturación (48,2 % → 89,6 %): la política aprende a pedir el techo casi siempre.*

La Figura 7.5 apoya una lectura realista de cómo usa la política el control de la velocidad: lo usa para fijar la velocidad general, no para seguir un perfil de velocidad. Hay algo de modulación, y aparece en los sitios adecuados. El 8,3 % de pasos con tracción reducida se concentra en las zonas de mucha curvatura y sube al 35,6 % en el ápice más cerrado. Pero el efecto es muy pequeño: la tracción baja a 0,81 y la velocidad solo cae de 0,218 a 0,216 m/s. La política entra en las curvas más cerradas casi al techo de velocidad. Este detalle, que parece menor, explica un resultado del Capítulo 8: la regla de velocidad de la cage no se activa nunca en toda la campaña.

### 7.5.4 Aprobación antes de la campaña

Antes de ejecutar la campaña de veredicto, la política tuvo que pasar una comprobación previa ligada por identificador criptográfico a su punto de control y a su configuración. Esa comprobación asegura que la interfaz de medida de la cage (el estimador de carril y su lectura de rumbo) funciona como debe: detecta los fallos reales de rumbo, no da falsos positivos en ciclos seguros y centrados, y el retardo se mantiene dentro de los límites. Pasó las siete pruebas, y eso es lo que permitió empezar la campaña.

El orden importa para el método. La política se elige con evaluación nominal, la instrumentación se comprueba por separado y queda ligada por *hash*, y solo después se ejecuta la campaña. Ninguno de estos tres pasos se puede hacer en otro orden sin debilitar la evidencia.

## 7.6 Resumen

Este capítulo deja tres resultados que usa el siguiente. Primero, existe una política de cámara que conduce bien, y está comparada con un método clásico. Segundo, la curva de entrenamiento no dice cómo se comporta la política. La elección hay que hacerla conduciendo en lazo cerrado, y cuando se aplicó ese criterio a la política de referencia descartó justo el punto de control que habría elegido la recompensa. Tercero, la política de referencia controla la velocidad, pero la usa para fijar la velocidad general y no para ajustarla a lo largo de la pista, lo que influye en qué reglas de la cage llegan a probarse de verdad.

El Capítulo 8 pasa esa política por la campaña de escenarios y produce el veredicto.
