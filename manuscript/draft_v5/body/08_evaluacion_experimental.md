# Capítulo 8 — Evaluación experimental

## 8.1 Propósito del capítulo

Este capítulo ocupa los niveles de evaluación conductual de la policy (L4b') y de validación basada en escenarios (L2'). Es donde la adaptación A2 se materializa: la caracterización estadística sustituye a la verificación clásica para el componente aprendido, mientras la cage conserva su verificación determinista del Capítulo 6.

Se presenta primero el diseño experimental —la biblioteca de escenarios, los dos modos de operación y la regla de agregación de veredictos—, después los resultados de la campaña de referencia, y por último los tres hallazgos que la campaña produjo y que no estaban en el guion. El desglose completo escenario por escenario se recoge en el Anexo I.

## 8.2 Diseño experimental

### 8.2.1 La biblioteca de escenarios

La biblioteca contiene veintiocho escenarios repartidos en cuatro familias con función distinta. Los nominales verifican competencia básica y ausencia de falsos disparos con entrada limpia; incluyen una prueba de resistencia de 300 s cuya función es detectar degradación acumulativa. Los límite inyectan condiciones iniciales adversas dentro o en la frontera del dominio: rumbo inicial elevado, desplazamiento lateral inicial, estado compuesto y una rejilla de co-activación cuyo propósito explícito es forzar la activación simultánea de dos o más reglas. Los perturbados aplican estresores sobre el canal de percepción —deslumbramiento, baja iluminación, desenfoque, marcas desgastadas, oclusión, carril falso inyectado y sus combinaciones—. Y los de frontera sitúan el vehículo *fuera* del dominio para medir la eficacia de la cage donde la policy no tiene por qué funcionar.

Cada escenario declara condiciones iniciales, perturbación, criterio de terminación, métricas primarias y criterio de aprobación explícito. Ninguna ejecución se interpreta sin ese criterio escrito de antemano.

### 8.2.2 Los dos modos como contrafactual

Cada escenario se ejecuta en enforcement —la cage corrige— y en monitoring —la cage evalúa las mismas reglas y registra las mismas activaciones, pero no modifica el comando—. La comparación entre ambos, sobre el mismo escenario y la misma semilla, es el instrumento central del capítulo: no compara dos sistemas distintos sino el mismo sistema con y sin envolvente, lo que elimina el confundido más obvio. Todo lo que este capítulo afirma sobre «la contribución de la cage» descansa sobre ese contraste.

### 8.2.3 Regla de agregación y tratamiento de la indeterminación

Un veredicto por requisito se compone a partir de los veredictos de sus escenarios bajo dos reglas declaradas de antemano. La primera es de suficiencia de evidencia: un requisito solo recibe veredicto si su cobertura alcanza un número mínimo de ejecuciones repartidas entre una familia nominal y una adversa; de lo contrario se marca como evidencia insuficiente, que no es lo mismo que fallo. La segunda es de veto: solo los requisitos de clase A pueden invalidar el veredicto global.

Una sutileza de implementación resultó importante. Un veredicto por ejecución indeterminado —cuando el criterio del escenario referencia una magnitud que el registro no captura— no es un fallo: se excluye del denominador y se propaga como evidencia insuficiente. Colapsarlo a fallo, como hacía una versión temprana del agregador, produce requisitos «incumplidos» que en realidad son huecos de instrumentación. La distinción parece pedante hasta que se comprueba que es justo lo que separa un hueco de un resultado: los dos requisitos que este trabajo cierra de forma no trivial —uno satisfecho y otro no— lo hacen porque el hueco de instrumentación se cerró y la medida se pudo tomar de verdad.

## 8.3 La campaña de referencia

La campaña de referencia ejecuta 1.890 corridas sin errores: veintisiete escenarios por dos modos, con las repeticiones que cada escenario declara, sobre la política bidimensional seleccionada en el Capítulo 7. Un escenario queda excluido por protocolo —la meta-prueba de *stall*, cerrada por separado con su propia metrología, según se explica en §8.6—. La configuración de la cage es idéntica a la de la campaña anterior, de modo que el contraste entre ambas es un contraste de política, no de instrumento.

### 8.3.1 Veredicto global

El veredicto global literal es `NO SATISFECHO`, compuesto como muestra la Tabla 8.1, y está bloqueado por dos requisitos de clase A —el de estabilidad de rumbo y el de tiempo predictivo a salida de carril— exclusivamente a través de un solo escenario y una sola cláusula. Conviene desglosarlo, porque la diferencia entre «el sistema no es seguro» y lo que realmente ocurre es toda la diferencia del capítulo:

| | Recuento | Requisitos |
| --- | :-: | --- |
| Clase A satisfechos | 8 / 10 | SR-001, 004, 005, 007, 008, 012, 013, 014 |
| Clase A con fallo **literal** | 2 / 10 | SR-002, SR-003 — solo vía un escenario y una cláusula; satisfechos sobre su propio criterio |
| Clase B con fallo **literal** | 1 / 4 | SR-011 — la misma cláusula heredada; satisfecho sobre su propia métrica (3,77° < 5°) |
| Clase B **no satisfecho** | 1 / 4 | SR-010 — rejilla de co-activación; el único veredicto negativo del trabajo (§8.6) |
| Clase B cerrados fuera de banda | 2 / 4 | SR-006 y SR-009 — satisfechos sobre su propia metrología (§8.6.1) |

*Tabla 8.1 — Composición del veredicto global de la campaña de referencia.*

En el escenario que bloquea, la única cláusula violada a lo largo de sus treinta corridas de enforcement es la de tiempo de recuperación de rumbo (Tabla 8.2). Las cláusulas de seguridad no se tocan en ninguna:

| Magnitud | Observado | Límite |
| --- | ---: | ---: |
| Paradas de emergencia | 0 | — |
| Excursión lateral máxima | 0,043 m | 0,16 m |
| Error de rumbo máximo | 14,2° | 25° |
| Desviación típica de rumbo máxima | 3,77° | 5° |

*Tabla 8.2 — El escenario que bloquea el veredicto: qué se mide y qué se incumple.*

Los dos requisitos están, por tanto, satisfechos sobre su propio criterio documentado: el de rumbo exige que el error no exceda 25°, y el máximo medido es 14,2°; el predictivo exige un margen de tiempo que nunca se compromete, con el vehículo a un cuarto del límite lateral. La cláusula de 2,0 s de recuperación es una exigencia de rendimiento heredada de una biblioteca anterior, no el predicado de seguridad de ninguno de los dos.

El veredicto se registra como literal, con la reconciliación anotada, no reformulado como satisfecho. Es una decisión deliberada: un marco cuyo valor consiste en no dejar afirmaciones sin evidencia perdería su sentido si reescribiera el veredicto cada vez que resulta incómodo. Lo que sí se hace es explicar exactamente qué se incumple y qué no.

### 8.3.2 La cláusula, auditada en lugar de excusada

Que la misma cláusula bloqueara el veredicto en dos campañas sucesivas es motivo para sospechar de la cláusula, no solo del sistema. Se auditó, y tenía un defecto real: su banda de recuperación era un valor *fijo* calibrado sobre un controlador y una geometría anteriores, de modo que —dado que el error de rumbo oscila en torno a cero con una amplitud que depende del controlador y del trazado— exigir varias muestras consecutivas dentro de esa banda medía el rizado, no la recuperación. Aplicada a corridas sin perturbación alguna, la métrica reportaba que el 100 % de ellas «nunca se recupera».

La corrección referencia la banda a la envolvente de régimen permanente de cada corrida, y se aplicó una sola vez, con su criterio de aceptación fijado de antemano: los falsos positivos sobre escenarios no perturbados deben desaparecer. Desaparecen. Dos conclusiones, ambas relevantes. La primera: re-puntuada con la métrica corregida, esta campaña sigue fallando el escenario, mientras que la política anterior lo aprobaría —es decir, la corrección favorece al brazo que la tesis no presenta, y por tanto no puede leerse como un ajuste hecho a conveniencia—. La segunda: el fallo no es un artefacto de medida. La recuperación de esta política efectivamente *repica* —13,6° → 1,4° → 5,9°, asentándose hacia los 2,5 s— y lo hace sobre una recta, lo que es la firma en lazo cerrado del mando a tirones que §8.5 documenta. Es una propiedad de rendimiento, no de seguridad, y la reconciliación descansa sobre terreno más firme que «la cláusula es heredada».

El límite de 2,0 s se dejó deliberadamente intacto: la auditoría corrige una medición, no rebaja un listón.

## 8.4 El invariante de seguridad

Este es el resultado central del trabajo. La Tabla 8.3 cuenta los contactos con el borde de la calzada y separa las corridas por si su condición inicial está dentro o fuera del dominio operacional:

| | Dentro del ODD | Fuera del ODD |
| --- | ---: | ---: |
| **Enforcement** (cage activa) | **0** | 56 |
| Monitoring (cage inactiva) | 60 | 217 |

*Tabla 8.3 — Contactos con el borde de la calzada por modo y por pertenencia al dominio.*

La Figura 8.1 la representa: dentro del dominio operacional, con la cage activa, no se registra un solo contacto con el borde de la calzada; la policy por sí sola comete sesenta, y la cage los elimina en su totalidad al coste de 406 paradas controladas. Fuera del dominio —donde el sistema no está obligado a funcionar— la mejora respecto de la política anterior es grande: 56 contactos frente a 117, concentrada precisamente donde el estrés de frontera aprieta.

<img src="../figures/fig_8_2_safety_invariant.png" alt="Figura 8.1 — Contactos con el borde por modo y por pertenencia al dominio." width="560"/>

*Figura 8.1 — Contactos con el borde de la calzada por modo y por pertenencia al dominio operacional, con las campañas anteriores superpuestas. El bloque «dentro del ODD, enforcement» es cero en todas ellas; la diferencia entre políticas está fuera del dominio.*

### 8.4.1 Latente dentro, activa donde se degrada la percepción

En el escenario nominal limpio la cage es latente: la política conduce 5,32 vueltas con 8,6 mm de error lateral medio, cero emergencias y cero intervenciones de seguridad; solo el limitador de tasa actúa. Pero el contraste entre modos, escenario a escenario (Tabla 8.4), muestra dónde deja de ser latente:

| Escenario | Enforcement | Monitoring |
| --- | ---: | ---: |
| Estado compuesto | 30/30 | 0/30 |
| Frontera (aproximación lateral) | 25/25 | 0/25 |
| Marcas desgastadas | 25/25 | 0/25 |
| **Marcas degradadas + deslumbramiento** | **40/40** | **20/40** |
| Resistencia 300 s | 25/25 | 8/25 |

*Tabla 8.4 — Escenarios que la cage rescata: corridas aprobadas por modo.*

Este es el contenido empírico de la afirmación central: la cage elimina fallos que la política comete por sí sola, y lo hace mediante el mecanismo previsto —la parada controlada ante percepción no fiable— exactamente en los escenarios donde el canal visual se degrada. La cage no mejora la conducción; acota la consecuencia de que la conducción falle.

<img src="../figures/fig_8_1_campaign_pass_fraction.png" alt="Figura 8.2 — Fracción de aprobados por escenario y modo." width="600"/>

*Figura 8.2 — Fracción de corridas aprobadas por escenario, enforcement frente a monitoring, ordenada por la contribución de la cage. Los escenarios de la parte superior son aquellos donde la envolvente marca la diferencia entre completar y no completar.*

## 8.5 El hallazgo incómodo: el limitador de tasa sostiene el carril

La prueba de resistencia de 300 s produce una inversión que las tablas de veredicto no muestran, y que resultó ser el hallazgo más informativo de la campaña. Con la cage activa, las veinticinco corridas se completan sin excursiones apreciables. Con la cage inactiva, diecisiete de veinticinco terminan fuera de la calzada —una tasa que ninguna de las políticas anteriores, incluidas las peores, exhibía.

Cuatro mediciones acotan la causa.

**No es deriva acumulada: es geométricamente determinista.** Las diecisiete salidas ocurren en exactamente dos arcos del circuito —los dos ápices más cerrados— y en los últimos segundos previos el tirón del mando es *menor* que la media de la corrida. No es oscilación: es un sobreviraje sostenido y confiado.

**Lo único que difiere entre modos es el limitador de tasa** (Tabla 8.5). Misma política, mismo trazado, misma velocidad en el ápice:

| En el ápice más cerrado | Enforcement | Monitoring |
| --- | ---: | ---: |
| Mando crudo de dirección (máx.) | 1,00 | 1,00 |
| Mando **aplicado** (máx.) | 0,84 | 1,00 |
| Variación por ciclo aplicada | ≤ 0,15 | hasta 2,0 |
| Error lateral máximo | 36 mm | 145 mm → fuera de calzada |

*Tabla 8.5 — Enforcement y monitoring en el ápice: la única diferencia es el limitador.*

**Ninguna regla de seguridad interviene.** A lo largo de las veinticinco corridas de enforcement el registro de intervenciones es exclusivamente del limitador de tasa, con cero activaciones de las reglas de límite lateral, rumbo, predictiva y emergencia. La regla que mantiene el vehículo en el carril en esos ápices es, formalmente, una regla de clase B de suavidad.

**El mando crudo de esta política es aproximadamente el doble de brusco** que el de sus predecesoras y satura el limitador en el 77,5 % de los pasos. La velocidad no lo explica: la política anterior circula un 7 % más lenta y sobrevive; y la comparación entre modos mantiene la velocidad constante dentro de la misma política.

**Interpretación, con sus límites declarados.** La lectura natural es de co-adaptación: la política se entrenó con la cage en la cadena de actuación, donde el limitador integra lo que ella comande; bajo ese lazo cerrado un mando casi de todo-o-nada no resulta penalizado, y la política lo emite. Con la cage activa, la pareja conduce mejor que ninguna otra configuración de este trabajo; sin ella, el mismo mando abandona el carril aproximadamente una vez cada tres vueltas. La cage no solo está filtrando a esta política: ha moldeado lo que la política aprendió a emitir.

Dos límites honestos sobre esa lectura. La dependencia está medida; su origen es inferido, y probar la causalidad exigiría una ablación —reentrenar con el limitador fuera del lazo— que no se ha ejecutado. Y la exposición importa: el escenario nominal corto aprueba 50/50 en monitoring, de modo que una evaluación nominal breve no puede detectar esta propiedad; solo la prueba de resistencia la revela.

Las consecuencias para leer el resto del trabajo son tres. «La cage es latente dentro del dominio» sigue siendo cierto de las reglas de seguridad, pero no debe leerse como «la cage está ociosa»: en esta política la latencia de las reglas de seguridad la *produce* el limitador actuando aguas arriba. La clasificación del requisito de suavidad como clase B subestima lo que esa regla está haciendo. Y sobre la plataforma física, donde la dinámica del actuador no es el limitador simulado, una política tan acoplada a un parámetro concreto de la envolvente constituye un riesgo de transferencia que se declara explícitamente en el Capítulo 12.

## 8.6 El veredicto negativo: composición de reglas

De los catorce requisitos, uno se cierra como no satisfecho, y se reporta como tal en lugar de reconciliarse.

Su criterio exige que, cuando dos o más reglas se activan en el mismo ciclo, el comando resultante satisfaga la envolvente segura de todas ellas. La rejilla de co-activación —cuyas condiciones iniciales se inyectan explícitamente para forzar ese caso— muestra que no se cumple: de los 85 puntos de rejilla situados dentro del dominio, 16 producen violaciones del margen lateral. Sobre la política anterior eran 30 de 85.

El desglose por combinación de reglas localiza el problema con precisión útil: las violaciones se concentran en la co-activación de las reglas de límite lateral y de rumbo —15 de 20 corridas fallan, con 11 violaciones— y en la terna que las incluye, son más suaves cuando la combinación es lateral con predictiva (4 violaciones) y desaparecen por completo allí donde no hay conflicto entre corrección lateral y de rumbo: la combinación de velocidad con limitador de tasa no produce ni una violación ni un fallo.

Entrenar una política mejor reduce el hallazgo a la mitad pero no lo cambia de naturaleza. Esa es la conclusión sustantiva: la arbitración bajo activación simultánea es una propiedad de diseño de la cage, no un defecto de la política, y la evidencia para afirmarlo es que dos políticas muy distintas producen el mismo patrón atenuado. Es exactamente el peligro que el registro anticipaba al incluir un peligro para el propio mecanismo de mitigación, y se carga como trabajo futuro declarado.

El requisito es de clase B y por tanto no veta el veredicto global; ningún predicado de seguridad de clase A está implicado. Que la matriz contenga un veredicto negativo, junto a la afirmación de cero contactos dentro del dominio, es lo que da crédito a la segunda.

### 8.6.1 Los dos requisitos cerrados fuera de banda

Dos requisitos se cierran sobre su propia métrica en lugar de por agregación de escenarios, y en ambos casos la razón está documentada.

El de suavidad de actuación se verifica directamente sobre la traza del mando comprometido: en enforcement, 840 de 840 corridas respetan el límite por ciclo; en monitoring solo 263 de 945. Es, incidentalmente, la medida más directa del valor del limitador.

El de *liveness* se cierra sobre su propia metrología. Su escenario —una meta-prueba de dos brazos que inyecta un incentivo adverso a detenerse— quedó excluido de la campaña porque es independiente de la política y se había cerrado ya por separado, con tres partes medidas: la política nominal nunca se detiene; un intento deliberado de forzarla a detenerse no lo consigue, lo que es evidencia positiva de la mitigación de entrenamiento; y el detector sí dispara ante una parada real inyectada por guion. Mitigación que funciona, patología resistida, métrica sana.

## 8.7 Contraste con el brazo de percepción perfecta

El brazo de control —misma cage, mismos escenarios, pero con estado obtenido de la verdad de referencia en lugar de la cámara— cierra con veredicto global satisfecho y aporta un hallazgo que da sentido a todo lo anterior: con percepción perfecta, la cage es completamente latente dentro del dominio; su métrica de violación de frontera es cero en ambos modos y el contraste entre enforcement y monitoring es nulo.

La lectura conjunta es la aportación empírica del trabajo: el valor de la cage es una función de la calidad de la percepción. Donde la percepción es perfecta, la envolvente no tiene nada que corregir y su valor solo se manifiesta fuera del dominio. Donde la percepción es una red que aprende de píxeles degradados, la envolvente pasa de latente a operativa y elimina fallos medibles. Sin el brazo de control, el resultado del brazo de cámara sería ambiguo: no se sabría si la cage aporta porque el problema es difícil o porque la política es mala.

## 8.8 Amenazas a la validez

- **Una sola semilla en la campaña de veredicto.** La campaña de referencia usa una semilla; la variabilidad entre semillas se caracteriza por separado (§7.4) y muestra que el comportamiento no es homogéneo. La generalización del veredicto a otras semillas no está establecida.
- **Un solo circuito.** Todos los resultados de referencia provienen de una geometría. La segunda geometría del brazo de control refuerza el argumento por plausibilidad, no lo cierra.
- **Las vueltas no son comparables entre trazados**, y el error lateral no es comparable entre modalidades de observación. El trabajo evita esas comparaciones y las señala donde podrían inducirse.
- **Simulación, no realidad.** Ningún resultado de este capítulo es evidencia sobre la plataforma física. El Capítulo 9 caracteriza qué se sabe y qué no del salto.
- **El origen de la dependencia del limitador es inferido**, no probado, y la ablación que lo probaría no se ha ejecutado.
- **Un incidente de operación** durante la campaña —dos procesos escribiendo concurrentemente sobre el mismo directorio— afectó a 222 corridas. Se pusieron en cuarentena y se re-ejecutaron bajo un controlador serie con cerrojo; el agregado final cubre las 1.890 celdas sin errores. Se registra aquí porque la integridad de la evidencia es una afirmación que también debe sostenerse con evidencia.

## 8.9 Síntesis

La campaña de referencia deja cuatro resultados. Dentro del dominio, con la cage activa, cero contactos con el borde, frente a sesenta que la política comete sin ella. La cage es latente en sus reglas de seguridad dentro del dominio y se vuelve operativa exactamente donde la percepción se degrada. El limitador de tasa hace un trabajo de mantenimiento de carril que su clasificación no refleja, y esa dependencia es un riesgo de transferencia declarado. Y un requisito no se satisface —la composición de reglas bajo co-activación—, se reporta como tal y se carga como trabajo futuro.

El Capítulo 9 aborda qué de todo esto se puede esperar que sobreviva al salto a la plataforma física.
