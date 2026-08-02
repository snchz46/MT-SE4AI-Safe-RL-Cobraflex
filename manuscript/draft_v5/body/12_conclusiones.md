# Capítulo 12 — Conclusiones y trabajo futuro

## 12.1 Propósito

Este capítulo cierra el trabajo en tres movimientos: sintetiza los hallazgos que la tesis sostiene con evidencia, responde a las preguntas de investigación planteadas en el Capítulo 1, y traduce los residuos abiertos en líneas de trabajo concretas con criterio de éxito. Se ordena por **valor demostrado**, no por orden cronológico, y los hallazgos negativos ocupan tanto espacio como los positivos porque tienen igual estatus como resultado.

## 12.2 Síntesis de hallazgos

**H1 — La cadena de trazabilidad completa es operacionalizable por una sola persona.** La cadena `Peligro → Requisito → Regla → Escenario → Métrica → Evidencia → Veredicto` se mantuvo verificada por herramienta a lo largo de todo el proyecto, sin huérfanos en ninguna puerta de revisión, con un validador de coste marginal. Es la afirmación central de la tesis y la que mejor evidencia tiene.

**H2 — El veredicto literal y el criterio propio pueden divergir, y la divergencia es informativa.** El veredicto global de la campaña de referencia es literalmente negativo, imputable en su totalidad a una cláusula de rendimiento sobre un único escenario, mientras los predicados de seguridad se cumplen íntegramente. Mantener ambas lecturas en el registro —el fallo literal y la reconciliación argumentada— es más honesto que reescribir el veredicto, y expone un defecto real de higiene de criterios que una edición retroactiva habría ocultado.

**H3 — La semántica de agregación importa: indeterminado no es fallo.** Un veredicto por ejecución que referencia una magnitud no registrada es un hueco de instrumentación, no un incumplimiento. Distinguirlos es lo que permitió, al cerrarse los huecos, que las mediciones resultantes fueran interpretables como resultados —uno positivo, otro negativo— y no como artefactos del agregador.

**H4 — La curva de entrenamiento no clasifica el comportamiento.** Semillas con curvas de recompensa indistinguibles producen políticas que caen a lados opuestos de la frontera entre respetar las restricciones y depender de la envolvente. La consecuencia operativa es que la selección debe hacerse por evaluación en lazo cerrado con la tasa de intervención como criterio de primer orden.

**H5 — El punto de control del pico de recompensa puede ser el peor candidato.** En la política de referencia lo fue: catorce intervenciones de seguridad frente a cero en el candidato elegido. Es el corolario práctico del hallazgo anterior y funciona además como control frente a la objeción de selección a posteriori, porque el criterio se fijó antes de la campaña.

**H6 — La cage es latente cuando la política respeta las restricciones, y su valor se mide donde la percepción se degrada.** Con percepción perfecta la envolvente no interviene dentro del dominio; bajo cámara degradada **elimina fallos que la política comete por sí sola**. El contraste entre ambos brazos es lo que convierte la afirmación «la cage aporta seguridad» en una afirmación medida y no en un supuesto arquitectónico.

**H7 — El invariante de seguridad se sostiene: cero contactos de borde dentro del dominio con la cage activa**, frente a sesenta que la política comete sin ella, a lo largo de 945 corridas de enforcement.

**H8 — El aprendizaje end-to-end desde cámara supera al baseline clásico en precisión de seguimiento** sobre geometría sinuosa, invirtiendo el resultado obtenido sobre geometría simple. Es el hallazgo que justifica el coste del componente aprendido en este dominio.

**H9 — La composición de reglas es un problema real, no teórico.** Bajo co-activación simultánea de las reglas lateral y de rumbo persisten violaciones del margen lateral. Entrenar mejor **reduce el hallazgo a la mitad sin cambiarlo de naturaleza**, lo que lo sitúa como problema de diseño de la envolvente. Es el único requisito que el trabajo cierra como no satisfecho, y se reporta como tal.

**H10 — El conservadurismo a prueba de fallos cuesta disponibilidad, y ese coste es medible.** Las paradas controladas que evitan excursiones también interrumpen corridas que habrían terminado bien. El diseño del disparador es un compromiso explícito entre seguridad y disponibilidad, no una elección libre.

**H11 — El gap entre simuladores es en sí mismo un resultado.** Portar el sistema a un entorno de mayor fidelidad requirió recalibrar la autoridad dinámica, los umbrales de rumbo y la propia estructura de la recompensa. **Los puntos de control no transfieren.** Ese resultado negativo calibra la expectativa razonable sobre el salto a hardware mejor que cualquier estimación optimista.

**H12 — La cage no solo filtra a la política: la moldea.** Entrenada con la envolvente en la cadena de actuación, la política de referencia emite un mando casi de todo-o-nada que satura el limitador de tasa en el 77,5 % de los pasos; con la cage activa conduce mejor que ninguna otra configuración del trabajo, y sin ella abandona el carril aproximadamente cada tres vueltas. Lo que se ha construido —y lo que se transferirá a hardware— es **la pareja**, no la política. La dependencia está medida; su origen está inferido.

## 12.3 Respuesta a las preguntas de investigación

**Pregunta principal.** *¿Es posible adaptar el V-Model canónico mediante un conjunto finito y trazable de modificaciones que acomode componentes entrenados por refuerzo sin abandonar la correspondencia bidireccional especificación↔V&V?* **Sí, con la evidencia de un caso.** Cinco adaptaciones bastaron para cubrir todos los modos de fallo encontrados; ninguna exigió abandonar la estructura del V; la correspondencia bidireccional no solo se preservó sino que se **endureció**, pasando de recomendación a restricción verificada por herramienta. El límite de la respuesta es el de un caso único: se ha demostrado suficiencia práctica, no completitud.

**Pregunta subordinada.** *¿Produce el marco evidencia coherente y trazable, incluida una caracterización honesta del gap sim-to-real?* **Sí en cuanto a evidencia trazable; parcialmente en cuanto al gap.** Los catorce requisitos tienen veredicto respaldado, incluidos los desfavorables. La caracterización del gap está estructurada y su primer peldaño medido, pero **el peldaño físico no se ha ejecutado**, de modo que la parte de A5 que exige medición sobre hardware queda pendiente y así se declara.

## 12.4 Trabajo futuro

**T1 — Diseño y verificación de la arbitración entre reglas.** Es el residuo que ninguna mejora de política resolvió y el único requisito no satisfecho. La dirección es pasar de la composición por orden fijo a un análisis de la envolvente conjunta: caracterizar en qué subregión del espacio de estado la composición secuencial produce acciones fuera de la envolvente que cada regla garantiza por separado, y o bien reordenar y parametrizar, o bien documentar esa subregión como exclusión del dominio. El desglose por combinación de reglas ya indica dónde mirar —la co-activación de límite lateral y de rumbo— y la rejilla de escenarios existente es el instrumento de medida.

**T2 — Despliegue físico y caracterización del gap.** Portar el subconjunto físico de la biblioteca con el sistema **tal como salió de la fase de simulación**, sin parcheos entre corridas, y producir la tabla de gap por métrica. Con un riesgo identificado de antemano: la política está acoplada al parámetro de variación máxima del limitador, y el actuador físico no implementa ese límite. Dos comprobaciones baratas antes de conducir: medir la respuesta real del actuador frente a la cota de la cage, y ejecutar **un horizonte largo y no el nominal corto**, porque el escenario breve no detecta la dependencia. El componente con mejor pronóstico de transferencia es la propia cage, por estar especificada sobre un estado abstracto e independiente de la calidad de la política y de la percepción.

**T3 — Ablación del limitador de tasa.** La medición del hallazgo H12 está hecha; su mecanismo está inferido. Reentrenar con el limitador fuera del lazo de actuación y comparar la distribución del mando crudo cerraría la cuestión, es barato en simulación y **debería preceder al hardware**.

**T4 — Robustez temporal del estimador de la cage.** No existe corrección robusta de un solo fotograma para una lectura errónea pero autoconsistente. Las direcciones con fundamento son la consistencia multifotograma —una lectura falsa estable en la misma sección del circuito sería detectable como inconsistencia con la odometría—, la calibración de confianza del estimador contra el oráculo de simulación y la redundancia barata de sensor para el estado de la cage.

**T5 — Disponibilidad: robustez del disparador de emergencia.** Dimensionar histéresis y persistencia en los disparadores de validez y de salud de percepción para que las paradas espurias no se produzcan, sin alargar el tiempo de reacción ante degradación genuina. El criterio de aceptación ya es medible sobre la biblioteca existente.

**T6 — Validación de ejecución, no solo de referencia.** Es la mejora que el marco se identificó a sí mismo. Extender el validador para comprobar que un escenario **se ejecuta como está especificado** —que sus condiciones iniciales se inyectan, que las magnitudes que su criterio referencia se registran— cerraría el hueco que permitió que un escenario corriera durante meses sin hacer lo que decía hacer.

**T7 — Replicación y escala.** Replicar el marco sobre un segundo caso con componente aprendido y sobre un simulador fotorrealista, para separar lo que es propiedad del marco de lo que es propiedad de este caso y de este instrumento.

## 12.5 Conclusión

La tesis sostiene que un ciclo de vida clásico de seguridad funcional puede acomodar un componente entrenado por refuerzo sin renunciar a lo que le da valor —la correspondencia verificable entre lo que se especifica y lo que se verifica—, y lo sostiene con un caso ejecutado de extremo a extremo cuya cadena de evidencia es auditable en su totalidad.

El resultado más sólido es también el más simple: dentro del dominio operacional declarado, con la envolvente activa, el sistema no abandonó la calzada ni una sola vez en novecientas cuarenta y cinco corridas, mientras que sin ella lo hizo sesenta veces. El resultado más instructivo, en cambio, es incómodo: la envolvente que hace posible esa cifra **también moldeó la política que contiene**, hasta el punto de que la política ya no es viable sin ella. Y el resultado que el trabajo entrega como problema abierto es el único requisito que no satisface: la arbitración entre reglas simultáneas, medida sobre dos políticas distintas y persistente en ambas.

Que los tres convivan en el mismo documento, con la misma trazabilidad y sin que ninguno haya sido reescrito para resultar más presentable, es la mejor evidencia disponible de que el marco hace lo que dice hacer.
