# Capítulo 4 — Dominio operacional, análisis de peligros y requisitos de seguridad

## 4.1 Propósito del capítulo

Este capítulo materializa la rama izquierda superior del V-Model adaptado: los requisitos de las partes interesadas (nivel L1), concretados en el dominio operacional, y los requisitos de seguridad del sistema (nivel L2), derivados sistemáticamente de un análisis de peligros. Es el primer capítulo donde el marco del Capítulo 3 deja de ser propuesta y produce artefactos sobre los que la adaptación A4 opera como restricción dura.

El contenido canónico de cada artefacto vive como documento vivo versionado; aquí se presenta la forma consolidada y el razonamiento que la produce. El registro de peligros completo, con la hipótesis de causa raíz y las referencias cruzadas de cada entrada, se recoge en el **Anexo A**; el *rationale* íntegro requisito por requisito, con la derivación de cada umbral, en el **Anexo B**; y la especificación completa del dominio operacional, con sus doce cuestiones abiertas y su cierre, en el **Anexo D**.

## 4.2 Función pretendida y requisitos de sistema

La **función pretendida** es mantener el vehículo dentro de su carril a lo largo de una pista delimitada, bajo condiciones controladas, sin intervención humana durante el episodio. Es deliberadamente modesta: el interés de la tesis no está en la sofisticación de la función sino en el rigor del ciclo que la produce y la valida.

De esa función se derivan cuatro requisitos de sistema que preceden a cualquier consideración de seguridad: el vehículo debe **seguir el carril** con un error lateral acotado; debe **completar el recorrido** sin detenerse indebidamente; debe **operar en tiempo real** dentro del ciclo de control declarado; y debe **registrar su comportamiento** de forma que la evidencia sea reconstruible a posteriori. Los tres primeros son de función; el cuarto es una consecuencia directa de la adaptación A3 y no aparecería en un ciclo clásico.

## 4.3 Dominio operacional

### 4.3.1 Estructura de cuatro dominios

La especificación del dominio operacional se estratifica en cuatro dominios anidados que aíslan un eje de complejidad cada uno, lo que permite atribuir un cambio observado en seguridad o rendimiento a una **única** causa y no a una combinación confundida:

- **ODD-1 — nominal.** Geometría de referencia, condiciones limpias, sin estresores. Es la línea base.
- **ODD-2 — adverso.** La misma geometría con estresores sobre el canal de percepción. En el track de cámara ese eje **es** la degradación visual: deslumbramiento, baja iluminación, desenfoque de movimiento, marcas desgastadas u ocluidas.
- **ODD-3 — geometría exigente.** Trazado sinuoso y cerrado en condiciones limpias, con envolvente de velocidad dependiente de la curvatura.
- **ODD-4 — combinado.** Producto cartesiano de la geometría de ODD-3 con los estresores de ODD-2.

Cada dominio fija parámetros con nombre —ancho de carril y de calzada, coeficiente de fricción, curvatura máxima, envolvente de velocidad, latencia de control, dimensionalidad de la observación y de la acción— de modo que cualquier afirmación posterior pueda referirse a un valor concreto y no a una descripción cualitativa.

### 4.3.2 Atributos del dominio frente a estresores de escenario

Una distinción que el trabajo mantiene con disciplina, porque su confusión es una fuente habitual de conclusiones inválidas: un **atributo del dominio** define dónde el sistema está *autorizado* a operar; un **estresor de escenario** es una perturbación inyectada dentro de ese dominio para provocar un modo de fallo concreto. Una excursión inducida por un estresor dentro del dominio es un fallo del sistema; la misma excursión provocada por una condición inicial fuera del dominio no lo es, y contarla como tal invalidaría el veredicto. Esta distinción sostiene la partición «dentro/fuera del ODD» con la que el Capítulo 8 lee todos sus resultados.

### 4.3.3 Dominio físico

Para el despliegue sobre la plataforma real se prevé un dominio análogo, el más próximo realizable en hardware, que comparte tipo de escenario, exclusiones e hipótesis de salida pero difiere en la envolvente dinámica del vehículo, en las interfaces de sensado y actuación y en la latencia nominal del lazo. Un único parámetro del dominio —la aceleración lateral máxima comandada— es **inmedible en simulación por construcción**, porque en el simulador sería una consecuencia del coeficiente de fricción que el propio mundo asume; queda abierto y explícitamente pendiente de una calibración física. Es la única cuestión del dominio que el trabajo cierra como pendiente, y se declara como tal en lugar de estimarse.

## 4.4 Análisis de peligros

### 4.4.1 Procedimiento

El análisis sigue la estructura de un HARA conforme a ISO 26262, **simplificado** en tres puntos que conviene declarar: se aplica sobre una única función y un único elemento, en lugar de sobre un vehículo completo; las situaciones operacionales se enumeran a partir de los cuatro dominios en lugar de derivarse de un catálogo de uso; y la asignación de nivel de integridad se sustituye por una clasificación de criticidad propia de dos clases, adecuada a un vehículo a escala sin consecuencias sobre personas. Las simplificaciones no afectan a la estructura del razonamiento —situación, peligro, severidad, exposición, controlabilidad, criticidad, mitigación— sino a su alcance.

Cada peligro se clasifica según tres ejes con rúbricas explícitas: **severidad** (de S0, sin lesión, a S3, consecuencia grave sobre el análogo a escala real), **exposición** (de E0 a E4, según la frecuencia de la situación dentro del dominio) y **controlabilidad** (de C0 a C3, según la capacidad del sistema o de un supervisor de evitar el daño). La combinación produce la criticidad, y esta determina si el peligro exige mitigación por regla determinista, por restricción de entrenamiento o por ambas.

### 4.4.2 Registro de peligros

El registro consolida **doce peligros**: nueve de nivel sistema, comunes a ambos tracks, y tres específicos del track de cámara. La numeración es estable: un identificador asignado no se reutiliza ni se renombra, aunque el peligro se descarte en revisiones posteriores. La tabla presenta la forma compacta; el registro extendido, con hipótesis de causa raíz y consecuente operacional de cada entrada, está en el Anexo A.

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

*Tabla 4.1 — Registro de peligros en forma compacta (registro extendido en el Anexo A).*

Tres entradas merecen comentario porque no aparecerían en un análisis clásico. **H-08** es un peligro propio del componente aprendido: la explotación de la función de recompensa, por la cual la policy converge a la inacción o a una conducta adversa que acumula más recompensa que el seguimiento nominal. **H-09** es un peligro propio de la *mitigación*: si dos o más reglas de la cage se activan en el mismo ciclo y su composición produce un comando fuera de la envolvente segura, la cage deja de ser garantía y se convierte en fuente de mandos inseguros. Registrar el peligro que introduce el propio mecanismo de seguridad es una exigencia elemental de honestidad, y el Capítulo 8 mostrará que no era una precaución retórica. **H-12** es su equivalente en el track de cámara: el estimador de la cage produce un carril falso pero plausible, e impone una envolvente errónea sobre el carril verdadero.

### 4.4.3 Complemento sistémico

Sobre los peligros de mayor criticidad se ejecuta además una pasada ligera de análisis sistémico basado en teoría de control, que examina las acciones de control inseguras del lazo completo en lugar de los modos de fallo de sus componentes. Su aportación fue identificar dos clases de peligro que el análisis por componentes no había producido: los derivados de **actuar sobre información inválida** —modelo de proceso desactualizado— y los derivados de la **ausencia de acción cuando era necesaria**. Ambas clases se materializaron en requisitos que hoy son parte del núcleo de la cage. La pasada es *ligera* y se declara como tal: no construye el modelo de control jerárquico completo ni enumera exhaustivamente los escenarios causales.

## 4.5 Derivación de requisitos de seguridad

### 4.5.1 Procedimiento y criterios de calidad

Cada peligro se traduce en uno o más requisitos bajo cuatro criterios obligatorios, que la plantilla del documento hace exigibles: **falsabilidad** —expresado como condición medible con procedimiento de veredicto definido—; **operatividad** —implementable por un mecanismo concreto, sea regla, restricción de entrenamiento o test de escenario—; **trazabilidad** —referencia al menos un peligro y es referenciado al menos por una regla y un escenario—; y **atomicidad** —captura una sola propiedad.

La falsabilidad merece énfasis porque es el criterio que hace posible todo lo demás. Un requisito como «el vehículo conducirá de forma segura» no es falsable y, por tanto, no es verificable ni trazable: no existe medición que pueda contradecirlo. La disciplina de exigir un umbral con nombre, una métrica y un procedimiento de veredicto es lo que convierte la matriz de trazabilidad en un instrumento con contenido, y no en un ejercicio documental.

### 4.5.2 Especificación de requisitos

El registro contiene **catorce requisitos**. La tabla los presenta en forma compacta; el *rationale* completo de cada uno —incluida la derivación de cada umbral y la discusión de los valores marcados como provisionales a la espera de calibración física— está en el Anexo B.

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

*Tabla 4.2 — Especificación de requisitos de seguridad en forma compacta (rationale completo en el Anexo B).*

### 4.5.3 Clases de criticidad

Los requisitos se reparten en dos clases con consecuencias distintas sobre el veredicto global. La **clase A** agrupa los que expresan un predicado de seguridad propiamente dicho: su incumplimiento invalida el veredicto global de la campaña. La **clase B** agrupa los que expresan propiedades deseables de calidad —suavidad, ausencia de oscilación, *liveness*, consistencia de composición— cuyo incumplimiento se reporta pero **no veta** el veredicto.

La distinción no es una vía de escape: es la que permite reportar honestamente un requisito no satisfecho sin que ello obligue a declarar inseguro un sistema cuyos predicados de seguridad se cumplen íntegramente. El Capítulo 8 hace uso de esa distinción exactamente una vez, y lo hace de forma explícita y argumentada.

## 4.6 Matriz de trazabilidad bidireccional

La matriz es el artefacto donde A4 se materializa. Registra la cadena completa `Peligro → Requisito → Regla → Escenario → Métrica → Evidencia → Veredicto` y se mantiene en dos formas complementarias: una legible, tabular, y otra procesable por máquina que el validador comprueba.

En este capítulo la matriz cubre su primer tramo: la cobertura entre peligros y requisitos. Todos los peligros del registro tienen al menos un requisito que los mitiga y todos los requisitos derivan de al menos un peligro, sin huérfanos en ninguna dirección. Dos peligros —H-01 y H-02— reciben mitigación de más de un requisito, lo que refleja que admiten ramas distintas: H-01 se mitiga por límite duro de offset y también por el criterio predictivo de tiempo a salida; H-02 por límite de magnitud y por límite de varianza, que cubren respectivamente la rama divergente y la rama oscilatoria del mismo peligro.

El validador aplica ocho restricciones de cobertura y **falla la puerta de revisión** si alguna se viola. La matriz completa, con los tramos que los capítulos siguientes van rellenando y con los veredictos finales, se recoge en el **Anexo F**.

## 4.7 Limitaciones del análisis

- **Análisis de peligros de alcance acotado.** El HARA cubre la función de seguimiento de carril sobre una plataforma a escala; ni las situaciones operacionales ni las rúbricas de severidad son trasladables sin revisión a un vehículo de calle.
- **Severidades por analogía.** Las severidades se asignan por analogía con un vehículo real, no por consecuencia física medida sobre la plataforma a escala. Es una convención declarada, no una medición.
- **Pasada sistémica ligera.** El complemento basado en teoría de control no es exhaustivo; se ejecutó sobre los peligros de mayor criticidad y produjo dos clases nuevas, pero no cabe afirmar que el catálogo esté cerrado.
- **Umbrales provisionales.** Varios umbrales quedan marcados como provisionales a la espera de calibración sobre la plataforma física. El marco exige que esa condición sea visible en el propio artefacto en lugar de quedar implícita, y el ciclo de resolución está definido: medir, actualizar el fichero de parámetros, versionar, re-ejecutar los escenarios afectados y registrar el cambio.
- **Completitud no demostrable.** No existe procedimiento que demuestre que el catálogo de peligros es completo. Lo que sí se afirma —y se comprueba mecánicamente— es que **ninguno de los identificados queda sin mitigación y sin evidencia**.

Con el dominio fijado, los peligros catalogados y los requisitos derivados, el Capítulo 5 aborda el nivel de diseño: la arquitectura del sistema y la especificación de la cage que ha de hacer cumplir estos requisitos en tiempo de ejecución.
