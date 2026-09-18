# Capítulo 8 — Evaluación experimental

## 8.1 Propósito del capítulo

Este capítulo cubre dos niveles: la evaluación del comportamiento de la policy (L4b') y la validación basada en escenarios (L2'). Es donde la adaptación A2 se hace concreta. Para el componente aprendido, la caracterización estadística ocupa el lugar de la verificación clásica, mientras que la cage mantiene la verificación determinista del Capítulo 6.

Primero se presenta el diseño experimental: la biblioteca de escenarios, los dos modos de funcionamiento y la regla para combinar veredictos. Después vienen los resultados de la campaña de referencia y, por último, los tres hallazgos que salieron de la campaña sin estar previstos. Los resultados completos escenario por escenario están en el Anexo I.

## 8.2 Diseño experimental

### 8.2.1 La biblioteca de escenarios

La biblioteca tiene veintiocho escenarios en cuatro familias, cada una con un propósito distinto. Los escenarios nominales comprueban la competencia básica y que nada se dispare sin motivo con una entrada limpia. Incluyen una prueba de resistencia de 300 s pensada para detectar degradación que se va acumulando con el tiempo. Los escenarios límite añaden condiciones iniciales difíciles dentro del dominio o en su borde: un error de rumbo inicial grande, un desplazamiento lateral inicial, un estado compuesto y una rejilla de co-activación cuyo objetivo explícito es hacer que dos o más reglas se activen a la vez. Los escenarios perturbados añaden estresores al canal de percepción: deslumbramiento, poca luz, desenfoque, marcas desgastadas, oclusión, un carril falso inyectado y combinaciones de todo esto. Los escenarios de frontera ponen el vehículo *fuera* del dominio para medir cómo funciona la cage donde la policy no tiene obligación de funcionar.

Cada escenario indica sus condiciones iniciales, la perturbación, la condición de fin, las métricas principales y un criterio de aprobación explícito. Ninguna ejecución se interpreta si ese criterio no estaba escrito antes.

### 8.2.2 Los dos modos como contrafactual

Cada escenario se ejecuta en modo enforcement, en el que la cage corrige el comando, y en modo monitoring, en el que la cage evalúa las mismas reglas y registra las mismas activaciones pero no cambia el comando. Comparar los dos, con el mismo escenario y la misma semilla, es la herramienta principal de este capítulo. No compara dos sistemas distintos, sino el mismo sistema con y sin la envolvente, lo que elimina el factor de confusión más evidente. Todo lo que este capítulo dice sobre «lo que aporta la cage» se basa en esta comparación.

### 8.2.3 Cómo se combinan los veredictos y qué hacer con los resultados indeterminados

El veredicto de un requisito se construye a partir de los veredictos de sus escenarios, con dos reglas definidas de antemano. La primera trata de tener suficiente evidencia. Un requisito solo recibe veredicto si tiene al menos un número mínimo de ejecuciones, repartidas entre una familia nominal y otra adversa. Si no, se marca como evidencia insuficiente, que no es lo mismo que un fallo. La segunda es una regla de veto: solo los requisitos de clase A pueden hacer que el veredicto global falle.

Un detalle de implementación resultó importante. El veredicto de una ejecución puede ser indeterminado cuando el criterio del escenario usa una magnitud que el registro no guarda; eso no es un fallo, se quita del denominador y se transmite como evidencia insuficiente. Una versión temprana del agregador lo contaba como fallo, y producía requisitos «incumplidos» que en realidad eran huecos de instrumentación. Parece menor, pero es justo lo que separa un hueco de un resultado: los dos requisitos que este trabajo cierra de forma no trivial, uno satisfecho y otro no, solo se pudieron cerrar tras arreglar el hueco y tomar la medida de verdad.

## 8.3 La campaña de referencia

La campaña de referencia ejecuta 1.890 corridas sin errores: veintisiete escenarios en dos modos, con el número de repeticiones que define cada escenario, usando la política bidimensional elegida en el Capítulo 7. Un escenario queda fuera por protocolo: la meta-prueba de *stall*, que se cerró por separado con sus propias mediciones, como se explica en §8.6. La configuración de la cage es la misma que en la campaña anterior, así que cualquier diferencia entre las dos viene de la política y no del instrumento de medida.

### 8.3.1 Veredicto global

El veredicto global literal es `NO SATISFECHO`, construido como muestra la Tabla 8.1. Lo bloquean dos requisitos de clase A, el de estabilidad de rumbo y el de tiempo predictivo hasta la salida de carril, y solo a través de un escenario y una cláusula. Vale la pena mirarlo en detalle, porque la diferencia entre «el sistema no es seguro» y lo que pasa en realidad es el punto clave del capítulo:

| | Recuento | Requisitos |
| --- | :-: | --- |
| Clase A satisfechos | 8 / 10 | SR-001, 004, 005, 007, 008, 012, 013, 014 |
| Clase A con fallo **literal** | 2 / 10 | SR-002, SR-003 — solo a través de un escenario y una cláusula; satisfechos sobre su propio criterio |
| Clase B con fallo **literal** | 1 / 4 | SR-011 — la misma cláusula heredada; satisfecho sobre su propia métrica (3,77° < 5°) |
| Clase B **no satisfecho** | 1 / 4 | SR-010 — rejilla de co-activación; el único veredicto negativo del trabajo (§8.6) |
| Clase B cerrados fuera de banda | 2 / 4 | SR-006 y SR-009 — satisfechos sobre sus propias mediciones (§8.6.1) |

*Tabla 8.1 — Cómo se construye el veredicto global de la campaña de referencia.*

En el escenario que bloquea, la única cláusula incumplida en sus treinta corridas de enforcement es la del tiempo de recuperación del rumbo (Tabla 8.2). Ninguna de las cláusulas de seguridad se incumple en ninguna corrida:

| Magnitud | Observado | Límite |
| --- | ---: | ---: |
| Paradas de emergencia | 0 | — |
| Excursión lateral máxima | 0,043 m | 0,16 m |
| Error de rumbo máximo | 14,2° | 25° |
| Desviación típica de rumbo máxima | 3,77° | 5° |

*Tabla 8.2 — El escenario que bloquea el veredicto: qué se mide y qué se incumple.*

Por tanto, los dos requisitos se cumplen según su propio criterio documentado. El de rumbo pide que el error no pase de 25°, y el máximo medido es 14,2°. El predictivo pide un margen de tiempo que nunca se pierde, y el vehículo se queda a un cuarto del límite lateral. La cláusula de 2,0 s de recuperación es un requisito de rendimiento heredado de una biblioteca anterior. No es la condición de seguridad de ninguno de los dos requisitos.

El veredicto se registra tal cual, con la explicación anotada al lado, y no se reescribe como satisfecho. Fue una decisión consciente. Un marco cuyo valor es no dejar ninguna afirmación sin evidencia perdería su sentido si reescribiera el veredicto cada vez que resulta incómodo. En su lugar, el texto explica exactamente qué se incumple y qué no.

### 8.3.2 La cláusula, auditada en lugar de excusada

La misma cláusula bloqueó el veredicto en dos campañas seguidas. Eso es un motivo para sospechar de la cláusula, no solo del sistema. Se auditó, y tenía un defecto real. Su banda de recuperación era un valor *fijo*, calibrado sobre un controlador y un trazado anteriores. Como el error de rumbo oscila alrededor de cero con una amplitud que depende del controlador y del trazado, pedir varias muestras seguidas dentro de esa banda medía el rizado y no la recuperación. Al aplicarla a corridas sin ninguna perturbación, la métrica decía que el 100 % de ellas «nunca se recupera».

La corrección fija la banda en relación con la envolvente de régimen permanente de cada corrida. Se aplicó una sola vez, con su criterio de aceptación fijado antes: los falsos positivos en escenarios sin perturbar tenían que desaparecer, y desaparecieron. De ahí salen dos conclusiones. Primera: al volver a puntuar esta campaña con la métrica corregida el escenario sigue fallando, mientras que la política anterior lo aprobaría, así que la corrección favorece a la opción que la tesis *no* presenta y no se puede ver como un ajuste a conveniencia. Segunda: el fallo no es un error de medida. La recuperación de esta política de verdad *repica* (13,6° → 1,4° → 5,9°, asentándose hacia los 2,5 s) y lo hace en una recta: así se ve en lazo cerrado el mando a tirones que documenta §8.5. Es una propiedad de rendimiento, no de seguridad, y la explicación se apoya ahora en algo más sólido que «la cláusula es heredada».

El límite de 2,0 s se dejó igual a propósito: la auditoría corrige una medición, no baja el listón.

## 8.4 El invariante de seguridad

Este es el resultado principal del trabajo. La Tabla 8.3 cuenta los contactos con el borde de la calzada y separa las corridas según si su condición inicial está dentro o fuera del dominio operacional:

| | Dentro del ODD (555 corridas/modo) | Fuera del ODD (390 corridas/modo) |
| --- | ---: | ---: |
| **Enforcement** (cage activa) | **0** | 56 |
| Monitoring (cage inactiva) | 60 | 217 |

*Tabla 8.3 — Contactos con el borde de la calzada por modo y según si la corrida empieza dentro del dominio. Las 945 corridas de cada modo se reparten en 555 dentro del dominio (familias nominal y perturbada) y 390 fuera (familias límite y frontera).*

La Figura 8.1 lo muestra: dentro del dominio operacional, con la cage activa, no hay ni un solo contacto con el borde de la calzada. La policy sola comete sesenta, y la cage los elimina todos a cambio de 406 paradas controladas. Fuera del dominio, donde el sistema no tiene obligación de funcionar, la mejora respecto a la política anterior es grande: 56 contactos frente a 117, concentrados justo donde las condiciones de frontera son más duras.

<img src="../figures/fig_8_1_safety_invariant.png" alt="Figura 8.1 — Contactos con el borde por modo y por pertenencia al dominio." width="560"/>

*Figura 8.1 — Contactos con el borde de la calzada por modo y según si la corrida empieza dentro del dominio operacional, para la campaña de referencia y las dos anteriores, `margin022` y `GE4-V2` (Tabla 7.1). El bloque «dentro del ODD, enforcement» es cero en las tres. Las diferencias entre políticas están fuera del dominio.*

### 8.4.1 Latente dentro, activa donde empeora la percepción

En el escenario nominal limpio la cage está latente, con las cifras que ya dio §7.5.2 al elegir el punto de control: solo actúa el limitador de tasa. Pero al comparar los modos escenario a escenario (Tabla 8.4) se ve dónde deja de estar latente:

| Escenario | Enforcement | Monitoring |
| --- | ---: | ---: |
| Estado compuesto | 30/30 | 0/30 |
| Frontera (aproximación lateral) | 25/25 | 0/25 |
| Marcas desgastadas | 25/25 | 0/25 |
| **Marcas degradadas + deslumbramiento** | **40/40** | **20/40** |
| Resistencia 300 s | 25/25 | 8/25 |

*Tabla 8.4 — Escenarios que la cage rescata: corridas aprobadas en cada modo.*

Esta es la evidencia que sostiene la afirmación principal. La cage elimina fallos que la política comete por sí sola, y lo hace con el mecanismo previsto, la parada controlada cuando la percepción no es fiable, justo en los escenarios donde el canal visual empeora. La cage no hace que la conducción sea mejor. Limita lo que pasa cuando la conducción falla.

<img src="../figures/fig_8_2_campaign_pass_fraction.png" alt="Figura 8.2 — Fracción de aprobados por escenario y modo." width="600"/>

*Figura 8.2 — Proporción de corridas aprobadas por escenario en la campaña de referencia (`2-D PPO 550k`, Tabla 7.1; identificadores de escenario sin el prefijo `SC-`), enforcement frente a monitoring, ordenada según lo que aporta la cage. En los escenarios de arriba, la envolvente marca la diferencia entre terminar y no terminar.*

## 8.5 El hallazgo incómodo: el limitador de tasa mantiene el coche en el carril

La prueba de resistencia de 300 s muestra una inversión que las tablas de veredicto esconden, y resultó ser el hallazgo más informativo de la campaña. Con la cage activa, las veinticinco corridas terminan sin ninguna excursión apreciable. Con la cage inactiva, diecisiete de veinticinco acaban fuera de la calzada. Ninguna de las políticas anteriores, ni siquiera las peores, hacía esto.

Cuatro mediciones acotan la causa.

**No es una deriva que se acumula con el tiempo. Ocurre en sitios fijos.** Las diecisiete salidas se producen en exactamente dos puntos del circuito, los dos ápices más cerrados. En los últimos segundos antes de llegar a ellos, el tirón del mando es *menor* que la media de la corrida. No es una oscilación. Es un sobreviraje constante y seguro de sí mismo.

**Lo único que cambia entre los modos es el limitador de tasa** (Tabla 8.5). Misma política, mismo trazado, misma velocidad en el ápice:

| En el ápice más cerrado | Enforcement | Monitoring |
| --- | ---: | ---: |
| Mando crudo de dirección (máx.) | 1,00 | 1,00 |
| Mando **aplicado** (máx.) | 0,84 | 1,00 |
| Variación por ciclo aplicada | ≤ 0,15 | hasta 2,0 |
| Error lateral máximo | 36 mm | 145 mm → fuera de calzada |

*Tabla 8.5 — Enforcement y monitoring en el ápice: la única diferencia es el limitador.*

**No interviene ninguna regla de seguridad.** En las veinticinco corridas de enforcement, el registro de intervenciones solo contiene el limitador de tasa, con cero activaciones de las reglas de límite lateral, rumbo, predictiva y emergencia. La regla que mantiene el vehículo en el carril en esos ápices es, sobre el papel, una regla de suavidad de clase B.

**El mando crudo de esta política es más o menos el doble de brusco** que el de las políticas anteriores, y satura el limitador en el 77,5 % de los pasos. La velocidad no lo explica. La política anterior va un 7 % más despacio y se mantiene en la calzada, y en la comparación entre modos la velocidad es la misma porque es la misma política.

**Interpretación y sus límites.** La explicación más probable es la co-adaptación. La política se entrenó con la cage en la cadena de actuación, donde el limitador suaviza todo lo que la política manda. En ese lazo cerrado, un mando casi de todo o nada no se penaliza, así que la política lo produce. Con la cage activa, la pareja conduce mejor que cualquier otra configuración de este trabajo. Sin ella, el mismo mando se sale del carril más o menos una vez cada tres vueltas. La cage no solo está filtrando esta política. Ha moldeado lo que la política aprendió a producir.

Esta explicación tiene dos límites. La dependencia está medida, pero su origen es una inferencia. Para demostrar la causa haría falta una ablación (reentrenar con el limitador fuera del lazo), y no se ha hecho. La exposición también importa. El escenario nominal corto aprueba 50/50 en monitoring, así que una evaluación nominal breve no puede detectar esta propiedad. Solo la prueba de resistencia la saca a la luz.

Esto tiene tres consecuencias para leer el resto del trabajo. «La cage está latente dentro del dominio» sigue siendo verdad para las reglas de seguridad, pero no hay que leerlo como «la cage no hace nada»: en esta política, las reglas de seguridad están latentes *porque* el limitador actúa antes. La etiqueta de clase B del requisito de suavidad subestima lo que hace esa regla. Y en la plataforma física, donde la dinámica del actuador no es el limitador simulado, una política tan ligada a un parámetro concreto de la envolvente es un riesgo de transferencia. El Capítulo 12 lo dice de forma explícita.

## 8.6 El veredicto negativo: composición de reglas

De los catorce requisitos, uno se cierra como no satisfecho, y se informa así en lugar de justificarlo.

Su criterio dice que, cuando dos o más reglas se activan en el mismo ciclo, el comando resultante tiene que quedar dentro de la envolvente segura de todas ellas. La rejilla de co-activación, cuyas condiciones iniciales se eligen a propósito para forzar este caso, muestra que no se cumple. De los 85 puntos de la rejilla que están dentro del dominio, 16 incumplen el margen lateral. Con la política anterior eran 30 de 85.

Mirar qué reglas se activan juntas deja el problema bastante claro. Las violaciones se concentran cuando se activan a la vez las reglas de límite lateral y de rumbo (fallan 15 de 20 corridas, con 11 violaciones) y en la terna que las incluye. Son más leves cuando la regla lateral se activa con la predictiva (4 violaciones). Y desaparecen por completo donde las correcciones lateral y de rumbo no entran en conflicto: la velocidad junto con el limitador de tasa no produce ninguna violación ni ningún fallo.

Entrenar una política mejor reduce el problema a la mitad, pero no cambia su naturaleza. Esa es la conclusión principal. Cómo arbitra la cage cuando varias reglas se activan a la vez es una propiedad de diseño de la cage, no un defecto de la política, y la prueba es que dos políticas muy distintas muestran el mismo patrón, solo que más débil. Es exactamente el peligro que el registro preveía al incluir un peligro para el propio mecanismo de mitigación, y queda como trabajo futuro declarado.

El requisito es de clase B, así que no bloquea el veredicto global, y no afecta a ninguna condición de seguridad de clase A. Tener un veredicto negativo en la matriz, junto a la afirmación de cero contactos dentro del dominio, es lo que hace creíble esa afirmación.

### 8.6.1 Los dos requisitos cerrados fuera de banda

Dos requisitos se cierran con su propia métrica en lugar de con los resultados de los escenarios. En los dos casos el motivo está documentado.

El requisito de suavidad de actuación se comprueba directamente sobre la traza del mando que de verdad se aplicó, contando solo los ciclos que no anula la parada de emergencia. En enforcement, las 840 corridas que tienen ciclos de ese tipo respetan todas el límite; las 105 restantes terminan en emergencia y no aportan muestra. En monitoring, donde la cage no anula nada y las 945 corridas puntúan, solo 263 lo respetan. De paso, es la medida más directa de lo que vale el limitador.

El requisito de *liveness* se cierra con sus propias mediciones. Su escenario, una meta-prueba de dos brazos que añade un incentivo para detenerse, quedó fuera de la campaña porque no depende de la política y ya se había cerrado por separado, con tres partes medidas. La política nominal nunca se detiene. Un intento deliberado de hacer que se detenga no funciona, lo que es evidencia positiva de que la mitigación del entrenamiento funciona. Y el detector sí salta ante una parada real inyectada por un script. Es decir: una mitigación que funciona, un modo de fallo que no aparece y una métrica que funciona.

## 8.7 Comparación con el brazo de percepción perfecta

El brazo de control usa la misma cage y los mismos escenarios, pero toma el estado de la verdad de referencia y no de la cámara. Cierra con un veredicto global satisfecho y da un hallazgo que pone todo lo anterior en contexto: con percepción perfecta la cage está completamente latente dentro del dominio, con la métrica de violación de frontera a cero en los dos modos y ninguna diferencia entre enforcement y monitoring.

Leídos juntos, los dos brazos dan la aportación empírica del trabajo: lo que vale la cage depende de lo buena que sea la percepción. Con percepción perfecta no tiene nada que corregir y su valor solo se ve fuera del dominio; con una red que aprende de píxeles degradados pasa de latente a activa y elimina fallos medibles. Sin el brazo de control no se podría saber si la cage ayuda porque el problema es difícil o porque la política es mala.

## 8.8 Amenazas a la validez

- **Una sola semilla en la campaña de veredicto.** La campaña de referencia usa una semilla. La variación entre semillas se estudia por separado (§7.4) y muestra que el comportamiento no es igual en todas. No está demostrado que el veredicto valga para otras semillas.
- **Un solo circuito.** Todos los resultados de referencia vienen de un solo trazado. El segundo trazado del brazo de control hace el argumento más plausible, pero no lo cierra.
- **Las vueltas no se pueden comparar entre trazados**, y el error lateral no se puede comparar entre tipos de observación. El trabajo evita estas comparaciones y las señala donde el lector podría caer en ellas.
- **Simulación, no realidad.** Ningún resultado de este capítulo es evidencia sobre la plataforma física. El Capítulo 9 describe qué se sabe y qué no sobre ese paso.
- **El origen de la dependencia del limitador es una inferencia**, no está demostrado, y la ablación que lo demostraría no se ha hecho.
- **Un incidente de operación** durante la campaña afectó a 222 corridas: dos procesos escribieron a la vez en el mismo directorio. Esas corridas se apartaron y se volvieron a ejecutar con un controlador en serie con cerrojo, y los resultados finales cubren las 1.890 celdas sin errores. Se anota aquí porque la integridad de la evidencia también es una afirmación que necesita evidencia.

## 8.9 Resumen

La campaña de referencia da cuatro resultados. Dentro del dominio, con la cage activa, hay cero contactos con el borde, frente a sesenta que la política comete sin ella. Las reglas de seguridad de la cage están latentes dentro del dominio y se activan justo donde la percepción empeora. El limitador de tasa hace un trabajo de mantener el carril que su clasificación no refleja, y esta dependencia es un riesgo de transferencia declarado. Y un requisito, la composición de reglas cuando se activan a la vez, no se cumple. Se informa tal cual y queda como trabajo futuro.

El Capítulo 9 estudia cuánto de todo esto se puede esperar que sobreviva al paso a la plataforma física.
