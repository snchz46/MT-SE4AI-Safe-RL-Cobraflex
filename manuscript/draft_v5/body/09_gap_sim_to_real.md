# Capítulo 9 — Caracterización del gap sim-to-real

## 9.1 El gap como objeto de estudio

La adaptación A5 exige que la validación operacional incorpore, como componente obligatorio y no opcional, la caracterización explícita del gap entre el entorno donde el sistema se entrenó y aquel donde va a operar. La exigencia responde a una asimetría de la literatura señalada en §2.7: abundan las técnicas para *reducir* el gap y escasean los marcos para *medirlo* en términos utilizables por un argumento de seguridad.

Este capítulo trata el gap como objeto de estudio en **peldaños de fidelidad creciente**: el simulador donde vive toda la evidencia de veredicto; un puente de mayor fidelidad física y visual; y la plataforma real. Cada peldaño responde una pregunta distinta, y el capítulo declara con precisión cuál de ellas tiene hoy respuesta medida y cuál no.

## 9.2 Primer peldaño: el puente de alta fidelidad

Se construyó un entorno equivalente sobre un simulador con motor físico y renderizado de mayor fidelidad, con la cadena completa portada: importación del modelo del vehículo, publicación de sensores, entrenamiento en proceso, aleatorización de dominio y la misma cage con su fichero de parámetros.

El resultado más útil de este peldaño **no es una campaña sino un diagnóstico**, y merece reportarse como tal porque es exactamente el tipo de información que A5 pretende obtener. Portar el sistema reveló una escalera de obstáculos que no eran de implementación sino de **acoplamiento entre capas**: la autoridad de guiñada del modelo requirió recalibración porque la respuesta dinámica difiere; los umbrales de rumbo de la cage tuvieron que recalibrarse para el nuevo renderizador porque el estimador de visión lee el mismo carril con un sesgo distinto; y la política con autoridad longitudinal descubrió un óptimo degenerado —detenerse— que el entorno anterior no permitía expresar.

De esos obstáculos se extrae la lección central del peldaño: **los puntos de control no se transfieren entre simuladores**. Una política entrenada en uno no es una política válida en el otro, ni siquiera con la misma arquitectura y la misma recompensa; cada entorno exige reentrenamiento. Si eso ocurre entre dos simuladores, la expectativa razonable sobre el salto a la plataforma física debe calibrarse en consecuencia. Es un resultado negativo, y es informativo.

## 9.3 Segundo peldaño: la plataforma física

### 9.3.1 Estado

La cadena de despliegue físico está **construida y documentada de extremo a extremo** —captura de la cámara embebida con los mismos parámetros de la simulación, nodo de política, estimador de carril, nodo de cage, control de vehículo y el controlador de la plataforma— pero **no se ha ejecutado sobre hardware**. En consecuencia, este capítulo no reporta ningún resultado físico, y la tabla de gap conserva su columna física vacía. Rellenarla con estimaciones sería exactamente el tipo de afirmación sin evidencia que el marco existe para impedir.

Un elemento de la cadena está señalado como **verificación bloqueante**: el campo de visión efectivo de la cámara embebida es un valor por defecto de configuración que la simulación **replicó**, de modo que ningún resultado de simulación puede exponer un error en él —y ese valor escala todas las magnitudes laterales sobre las que la cage actúa. Es el primer punto a medir sobre hardware, antes que ninguna métrica de conducción.

### 9.3.2 Diseño experimental previsto

El subconjunto físico de la biblioteca se limita a tres escenarios exportables —nominal, nominal con curvatura y límite de rumbo— sobre pista cerrada con iluminación controlada, en los dos modos de operación. La comparación se hace por métrica y por modo de fallo, no en agregado. Un único parámetro del dominio operacional se cierra en este peldaño y solo en él: la envolvente de aceleración lateral, inmedible en simulación por construcción.

## 9.4 La tabla de gap

Los valores de simulación de referencia están fijados en dos columnas: la de la política unidimensional, referencia histórica, y la de la política **bidimensional que efectivamente se despliega**, que es la fila de contraste relevante. La columna física se puebla en la fase de despliegue.

| Métrica (escenario nominal, enforcement) | Sim 1-D | **Sim 2-D (la que se despliega)** | Físico |
| --- | --- | --- | --- |
| Error lateral medio | 10,9 mm | **8,6 mm** (máx. 27,3 mm) | pendiente |
| Vueltas completadas | 4,88 | **5,32** | pendiente |
| Excursión lateral máxima | < límite en todo el dominio | **0 contactos de borde dentro del ODD** | pendiente |
| Paradas de emergencia | 0 | **0** | pendiente |
| Tasa de intervención | 43,5 % (solo limitador) | **76,1 %** (solo limitador) | pendiente |
| Velocidad de operación | 0,200 m/s fija | **≈ 0,216 m/s** bajo techo 0,22 | pendiente |
| Latencia extremo a extremo | 50 ms nominal | 50 ms nominal | pendiente |

*Tabla 9.1 — Tabla de gap: columnas de simulación fijadas, columna física pendiente de la fase de despliegue.*

La fila que concentra el riesgo no es el error lateral sino la **tasa de intervención**. Sube de 43,5 % a 76,1 % porque el mando crudo de la política de referencia es aproximadamente el doble de brusco, hasta el punto —documentado en §8.5— de que **sin la cage esa política no sostiene la corrida de resistencia**. Lo que se transfiere a la plataforma no es la política sola: es **la pareja formada por la política y el limitador de tasa**. Como en el vehículo real la dinámica del actuador no es el limitador simulado sino una respuesta electromecánica con su propia constante de tiempo, el primer gap a vigilar es el del comportamiento del limitador y su parámetro de variación máxima por ciclo, no el del error de seguimiento.

## 9.5 Síntesis

El capítulo deja el estado del gap declarado con precisión: **el primer peldaño está medido y su resultado es un diagnóstico negativo útil** —los puntos de control no transfieren, el acoplamiento entre percepción, calibración y dinámica es más fuerte de lo que sugeriría la arquitectura modular—; **el segundo está construido pero no ejecutado**, y por tanto no produce evidencia. La adaptación A5 se cumple en su exigencia de *hacer explícito* el gap y de estructurar su medición; no se cumple todavía en la parte que exige medirlo sobre hardware. El Capítulo 10 emite el veredicto consolidado con esa limitación incorporada a su enunciado, y no al margen de él.
