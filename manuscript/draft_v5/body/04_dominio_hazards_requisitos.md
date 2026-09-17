# Capítulo 4 — Dominio operacional, análisis de peligros y requisitos de seguridad

## 4.1 Propósito del capítulo

Este capítulo cubre la parte superior de la rama izquierda del V-Model adaptado. Contiene los requisitos de las partes interesadas (nivel L1), expresados como dominio operacional, y los requisitos de seguridad del sistema (nivel L2), obtenidos paso a paso a partir de un análisis de peligros. Es el primer capítulo en el que el marco del Capítulo 3 deja de ser solo una propuesta: produce artefactos que la adaptación A4 comprueba como restricción dura.

El contenido oficial de cada artefacto se guarda en un documento vivo versionado. Este capítulo muestra su forma final y el razonamiento que hay detrás. El registro de peligros completo, con la hipótesis de causa raíz y las referencias cruzadas de cada entrada, está en el Anexo A. El *rationale* completo de cada requisito, con la forma en que se obtuvo cada umbral, está en el Anexo B. La especificación completa del dominio operacional, con sus doce cuestiones abiertas y cómo se cerraron, está en el Anexo D.

## 4.2 Función prevista y requisitos de sistema

La función prevista es mantener el vehículo dentro de su carril a lo largo de una pista cerrada, en condiciones controladas y sin ayuda humana durante el episodio. La función es sencilla a propósito. Lo que interesa en esta tesis no es lo avanzada que sea la función, sino lo riguroso que sea el ciclo que la construye y la valida.

De esta función salen cuatro requisitos de sistema, antes de cualquier consideración de seguridad. El vehículo debe seguir el carril con un error lateral limitado. Debe completar el recorrido sin detenerse sin motivo. Debe funcionar en tiempo real dentro del ciclo de control declarado. Y debe registrar su comportamiento para que la evidencia se pueda reconstruir después. Los tres primeros son funcionales. El cuarto viene directamente de la adaptación A3 y no aparecería en un ciclo clásico.

## 4.3 Dominio operacional

### 4.3.1 Cuatro dominios

El dominio operacional se divide en los cuatro dominios anidados de la Figura 4.1. Cada uno aísla una fuente de complejidad. Así se puede relacionar un cambio observado en la seguridad o el rendimiento con una sola causa, y no con una mezcla de causas:

- **ODD-1 — nominal.** Trazado de referencia, condiciones limpias, sin estresores. Es la línea base.
- **ODD-2 — adverso.** El mismo trazado con estresores sobre el canal de percepción. En el track de cámara son problemas visuales: deslumbramiento, poca luz, desenfoque de movimiento y marcas desgastadas o tapadas.
- **ODD-3 — trazado exigente.** Un trazado sinuoso y cerrado en condiciones limpias, con un límite de velocidad que depende de la curvatura.
- **ODD-4 — combinado.** El trazado de ODD-3 combinado con los estresores de ODD-2.

<img src="../figures/fig_4_1_odd_taxonomy_es.png" alt="Figura 4.1 — Taxonomía ODD retenida y los cuatro dominios estratificados." width="580"/>

*Figura 4.1 — La taxonomía ODD usada y los cuatro dominios. A la izquierda, las dimensiones de PAS 1883 / ISO 34503 con las que se describe cada dominio. A la derecha, la división 2 × 2 cuyas comparaciones por pares permiten al Capítulo 8 relacionar un efecto con una sola fuente de complejidad: ODD-1 frente a ODD-2 aísla los estresores en tramo recto, ODD-1 frente a ODD-3 aísla el trazado más difícil en condiciones limpias, y ODD-3 frente a ODD-4 añade estresores en curva.*

Cada dominio fija parámetros con nombre: ancho de carril y de calzada, coeficiente de fricción, curvatura máxima, rango de velocidad, latencia de control y tamaño de la observación y de la acción. Así, cualquier afirmación posterior puede referirse a un valor concreto y no a una descripción vaga.

### 4.3.2 Atributos del dominio y estresores de escenario

Hay una distinción que el trabajo respeta de forma estricta, porque mezclar las dos cosas lleva a menudo a conclusiones equivocadas. Un atributo del dominio define dónde el sistema está *autorizado* a funcionar. Un estresor de escenario es una perturbación que se añade dentro de ese dominio para provocar un modo de fallo concreto. Si un estresor dentro del dominio hace que el vehículo se salga del carril, es un fallo del sistema. Si la misma salida la provoca una condición inicial fuera del dominio, no lo es, y contarla como fallo invalidaría el veredicto. Esta distinción es la base de la división «dentro/fuera del ODD» que usa el Capítulo 8 para leer todos sus resultados.

### 4.3.3 Dominio físico

Para el despliegue en la plataforma real se prevé un dominio equivalente, lo más parecido que permite el hardware. Comparte el tipo de escenario, las exclusiones y las hipótesis de salida, pero cambia en los límites dinámicos del vehículo, en las interfaces de sensado y actuación y en la latencia normal del lazo. Hay un parámetro del dominio, la aceleración lateral máxima comandada, que no se puede medir en simulación de ninguna manera, porque allí sería una simple consecuencia del coeficiente de fricción que supone el mundo simulado. Sigue abierto, a la espera explícita de una calibración física. Es la única cuestión del dominio que este trabajo deja abierta, y se marca como abierta en lugar de estimarla.

## 4.4 Análisis de peligros

### 4.4.1 Procedimiento

El análisis sigue la estructura de un HARA según ISO 26262 (la Figura 4.2 muestra el procedimiento tal como se aplicó), con tres simplificaciones que hay que declarar. Se aplica a una sola función y un solo elemento, y no a un vehículo completo. Las situaciones operacionales salen de los cuatro dominios, y no de un catálogo de uso. Y en lugar de asignar un nivel de integridad, se usa una escala propia de criticidad con dos clases, que encaja con un vehículo a escala que no puede causar daños a personas. Estas simplificaciones cambian el alcance del razonamiento, no su estructura: situación, peligro, severidad, exposición, controlabilidad, criticidad y mitigación.

<img src="../figures/fig_4_2_hara_procedure.png" alt="Figura 4.2 — Procedimiento HARA aplicado." width="560"/>

*Figura 4.2 — El procedimiento HARA tal como se aplicó: cinco pasos desde la lista de funciones hasta documentar la consecuencia y la hipótesis de causa raíz. Una pasada sistémica ligera ajusta las restricciones de algunos peligros seleccionados, y la salida es el registro de peligros.*

Cada peligro se valora en tres ejes con escalas explícitas: severidad (de S0, sin lesión, a S3, consecuencia grave en el equivalente a tamaño real), exposición (de E0 a E4, según la frecuencia con que se da la situación dentro del dominio) y controlabilidad (de C0 a C3, según lo bien que el sistema o un supervisor pueden evitar el daño). Juntas dan la criticidad, que decide si el peligro necesita una regla determinista, una restricción de entrenamiento o ambas.

### 4.4.2 Registro de peligros

El registro, resumido en la Tabla 4.1, contiene doce peligros: nueve de nivel sistema, comunes a los dos tracks, y tres propios del track de cámara. La numeración es estable. Un identificador asignado nunca se reutiliza ni se cambia de nombre, aunque el peligro se descarte en una revisión posterior. La tabla es la versión corta. El registro ampliado, con la hipótesis de causa raíz y la consecuencia operacional de cada entrada, está en el Anexo A.

| ID | Peligro | S | E | C | Criticidad |
| --- | --- | :-: | :-: | :-: | --- |
| H-01 | Salida lateral involuntaria del carril | S3 | E3 | C2 | Alta |
| H-02 | Error de orientación divergente u oscilatorio | S2 | E3 | C2 | Media-alta |
| H-03 | Velocidad excesiva para la curvatura local | S3 | E2 | C1 | Media-alta |
| H-04 | Estado compuesto irrecuperable (rumbo + offset + velocidad) | S3 | E1 | C3 | Alta |
| H-05 | Comando de actuación abrupto entre ciclos consecutivos | S1 | E3 | C1 | Media |
| H-06 | Operación sobre estado no observable o corrupto | S3 | E2 | C2 | Alta |
| H-07 | Imposibilidad de realizar una parada controlada | S3 | E1 | C1 | Alta |
| H-08 | *Stall* por explotación de la recompensa | S2 | E3 | C2 | Media-alta |
| H-09 | Conflicto entre reglas de la cage bajo co-activación | S3 | E1 | C2 | Media |
| H-10 | Mala percepción de carril por entrada visual degradada | S3 | E3 | C2 | Alta |
| H-11 | Pérdida de percepción de carril válida | S3 | E2 | C2 | Alta |
| H-12 | Detección errónea del estimador de la cage (carril falso plausible) | S3 | E2 | C2 | Alta |

*Tabla 4.1 — Registro de peligros, versión corta (registro ampliado en el Anexo A).*

Tres entradas necesitan un comentario, porque no aparecerían en un análisis clásico. H-08 es propio del componente aprendido. Es la explotación de la recompensa: la policy acaba sin hacer nada, o haciendo algo perjudicial, porque así gana más recompensa que siguiendo el carril con normalidad. H-09 es propio de la *mitigación*. Si dos o más reglas de la cage se activan en el mismo ciclo y la combinación da un comando fuera de la envolvente segura, la cage deja de ser una garantía y pasa a generar comandos inseguros. Registrar los peligros que crea el propio mecanismo de seguridad es una cuestión básica de honestidad, y el Capítulo 8 muestra que no era una precaución puramente formal. H-12 es la versión del mismo problema en el track de cámara: el estimador de la cage produce un carril falso pero creíble, y aplica una envolvente equivocada sobre el carril real.

### 4.4.3 Análisis sistémico

Para los peligros más críticos se hace además un análisis sistémico ligero basado en teoría de control. Este análisis mira las acciones de control inseguras en todo el lazo, en lugar de los modos de fallo de cada componente. Encontró dos tipos de peligro que el análisis por componentes no había detectado: los que vienen de actuar sobre información no válida (un modelo de proceso desactualizado) y los que vienen de no actuar cuando hacía falta. Los dos tipos se convirtieron en requisitos que hoy forman parte del núcleo de la cage. La pasada es *ligera*, y se presenta así: no construye el modelo de control jerárquico completo ni enumera todos los escenarios causales.

## 4.5 Obtención de los requisitos de seguridad

### 4.5.1 Procedimiento y criterios de calidad

Cada peligro se convierte en uno o más requisitos siguiendo el procedimiento de la Figura 4.3. Hay cuatro criterios obligatorios, que la plantilla del documento hace cumplir. Falsabilidad: el requisito es una condición medible con una forma definida de llegar a un veredicto. Operatividad: se puede implementar con un mecanismo concreto, como una regla, una restricción de entrenamiento o un test de escenario. Trazabilidad: apunta al menos a un peligro y al menos una regla y un escenario apuntan a él. Atomicidad: describe una sola propiedad.

<img src="../figures/fig_4_3_sr_derivation.png" alt="Figura 4.3 — Procedimiento de derivación de requisitos de seguridad." width="560"/>

*Figura 4.3 — Cómo se obtiene un requisito de seguridad a partir de un peligro, en cuatro pasos. Dos salvaguardas hacen defendible el resultado. Los umbrales se fijan a partir de la física del ODD y nunca a partir del rendimiento de la policy entrenada, lo que sería circular. Y la clase de criticidad decide cómo se implementa el requisito: todo requisito de clase A acaba en una regla determinista.*

La falsabilidad merece destacarse, porque todo lo demás depende de ella. Un requisito como «el vehículo conducirá de forma segura» no se puede falsar, así que tampoco se puede verificar ni trazar: ninguna medición podría contradecirlo nunca. Exigir un umbral con nombre, una métrica y un procedimiento de veredicto es lo que hace de la matriz de trazabilidad una herramienta útil y no un ejercicio de papeleo.

### 4.5.2 Especificación de requisitos

El registro tiene catorce requisitos. La Tabla 4.2 muestra la versión corta. El *rationale* completo de cada uno, incluida la forma en que se obtuvo cada umbral y la discusión de los valores marcados como provisionales hasta la calibración física, está en el Anexo B.

| ID | Requisito (forma abreviada) | Umbral principal | Peligro | Implementación | Clase |
| --- | --- | --- | --- | --- | :-: |
| SR-001 | Offset lateral acotado dentro del ODD | `d_max = 0,16 m` | H-01 | C-01 | A |
| SR-002 | Error de orientación acotado | `θ_max = 25°` | H-02 | C-02 | A |
| SR-003 | Tiempo proyectado a salida de carril por encima de un mínimo | `t_min = 1,0 s` | H-01, H-02 | C-03 | A |
| SR-004 | Velocidad bajo techo dependiente de la curvatura | `0,25–0,5 m/s` | H-03 | C-04 | A |
| SR-005 | Transición a modo emergencia bajo *trigger* compuesto | `θ_warn 20°`, `d_warn 0,12 m` | H-04, H-07 | C-05 | A |
| SR-006 | Variación de comando acotada entre ciclos | `δ_max = 0,15` | H-05 | C-06 | B |
| SR-007 | Emergencia ante observación obsoleta o fuera de rango | `staleness ≤ 200 ms` | H-06 | C-05 | A |
| SR-008 | Parada controlada bajo señal externa | `t_stop ≤ 1,7 s` | H-07 | C-05 | A |
| SR-009 | Progreso longitudinal mínimo (*liveness*) | `Δs ≥ 0,10 m / 2 s` | H-08 | entrenamiento | B |
| SR-010 | Composición consistente de reglas co-activas | envolvente conjunta | H-09 | arbitraje | B |
| SR-011 | Varianza de rumbo acotada | `σ_θ ≤ 5°` | H-02 | C-06 + entren. | B |
| SR-012 | Seguimiento bajo entrada visual degradada | reutiliza `d_max`, `θ_max` | H-10 | C-01/02/03 + entren. | A |
| SR-013 | Parada controlada ante pérdida de percepción | `≤ 200 ms` | H-11 | C-05 | A |
| SR-014 | No imponer reglas sobre una estimación implausible | tolerancia de plausibilidad | H-12 | C-05 | A |

*Tabla 4.2 — Especificación de requisitos de seguridad, versión corta (rationale completo en el Anexo B).*

Un umbral de la tabla necesita una nota, porque es el único que la implementación cambia. SR-007 fija la antigüedad máxima de la observación en `200 ms`, que son cuatro ciclos del lazo de control a 20 Hz. El disparador correspondiente de C-05 funciona a 10 Hz en el track de cámara y usa `0,5 s`. Es la misma tolerancia expresada en ciclos (cinco), no un requisito más flojo. La equivalencia está anotada en el fichero de parámetros y en el Anexo D. Se señala aquí para que el lector no vea una contradicción donde solo hay un cambio de parámetros declarado.

### 4.5.3 Clases de criticidad

Los requisitos se dividen en dos clases, que afectan de forma distinta al veredicto global. La clase A reúne los requisitos que expresan condiciones de seguridad propiamente dichas. Si se incumple uno de ellos, el veredicto global de la campaña queda invalidado. La clase B reúne requisitos sobre propiedades de calidad deseables, como suavidad, ausencia de oscilación, *liveness* y composición coherente de reglas. Su incumplimiento se informa, pero no bloquea el veredicto.

Esta división no es una forma de escurrir el bulto. Permite informar con honestidad de un requisito no cumplido sin tener que declarar inseguro un sistema que cumple todas sus condiciones de seguridad. El Capítulo 8 usa esta distinción una sola vez, y lo hace abiertamente y con argumentos.

## 4.6 Matriz de trazabilidad en ambos sentidos

La matriz es donde A4 se hace concreta. Registra la cadena completa `Peligro → Requisito → Regla → Escenario → Métrica → Evidencia → Veredicto` y se mantiene en dos formas: una tabla legible y una versión que puede leer una máquina, que es la que usa el validador.

En este capítulo la matriz cubre solo su primera parte: la relación entre peligros y requisitos. Todos los peligros del registro tienen al menos un requisito que los mitiga, y todos los requisitos vienen de al menos un peligro, sin huérfanos en ningún sentido. Dos peligros, H-01 y H-02, están cubiertos por más de un requisito, porque cada uno puede ocurrir de más de una forma. H-01 se cubre con un límite duro de offset y también con el criterio predictivo de tiempo hasta la salida. H-02 se cubre con un límite de magnitud y otro de varianza, que cubren respectivamente la versión divergente y la versión oscilatoria del mismo peligro.

El validador aplica ocho restricciones de cobertura y bloquea la puerta de revisión si se incumple alguna. La matriz completa, con las partes que van rellenando los capítulos siguientes y con los veredictos finales, está en el Anexo F.

## 4.7 Limitaciones del análisis

- **Alcance limitado del análisis de peligros.** El HARA cubre el seguimiento de carril en una plataforma a escala. Ni las situaciones operacionales ni las escalas de severidad se pueden usar en un vehículo de calle sin revisarlas.
- **Severidades por analogía.** Las severidades se fijan comparando con un vehículo real, no midiendo consecuencias físicas sobre la plataforma a escala. Es una convención declarada, no una medición.
- **Pasada sistémica ligera.** El análisis basado en teoría de control no es completo. Se hizo sobre los peligros más críticos y encontró dos tipos nuevos, pero no se puede decir que el catálogo esté cerrado.
- **Umbrales provisionales.** Varios umbrales están marcados como provisionales hasta que se calibren en la plataforma física. El marco exige que esta situación sea visible en el propio artefacto y no quede sin decir, y el proceso para resolverla está definido: medir, actualizar el fichero de parámetros, versionarlo, volver a ejecutar los escenarios afectados y registrar el cambio.
- **La completitud no se puede demostrar.** Ningún procedimiento puede demostrar que el catálogo de peligros está completo. Lo que sí se afirma, y se comprueba de forma automática, es que ningún peligro identificado se queda sin mitigación y sin evidencia.

Con el dominio definido, los peligros registrados y los requisitos obtenidos, el Capítulo 5 pasa al nivel de diseño: la arquitectura del sistema y la especificación de la cage que debe hacer cumplir estos requisitos en tiempo de ejecución.
