# Anexo F — Matriz de trazabilidad

La matriz existe en dos formas que se mantienen sincronizadas. Una es legible y está organizada por cadena de mitigación. La otra la puede procesar una máquina, y sobre ella el validador comprueba las ocho restricciones de cobertura. Si se incumple cualquiera de ellas, la puerta de revisión correspondiente queda bloqueada.

## F.1 Resumen por cadena de mitigación

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict (Sim) |
| ------ | ------------------ | ------------ | --------- | ------------------- | ------- |
| H-01 | SR-001 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | Satisfied |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | Satisfied ⁷ |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | Satisfied ⁷ |
| H-02 | SR-011 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | Satisfied |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | Satisfied |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | Satisfied |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | Satisfied ¹ |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | Satisfied |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | Satisfied |
| H-08 | SR-009 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | Satisfied (out-of-band, D-64/D-69) ² |
| H-09 | SR-010 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | Not satisfied — CL-B finding, non-vetoing (D-69) ³ |
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁹ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁹ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | Satisfied (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁹ |

**Notas de la tabla F.1.** Los ocho marcadores remiten al desarrollo completo de cada caso en el documento vivo de trazabilidad. Aquí se recoge la versión resumida.

- **¹ SR-006 — Satisfecho sobre su propia métrica (D-39).** Al agregarlo de forma gruesa sobre «todos los escenarios», heredaba un fallo de proporción que no tenía nada que ver con la suavidad. Por eso se puntúa directamente sobre su métrica. En los pasos que de verdad controla el limitador (sin una regla de seguridad por encima ni emergencia), la variación por ciclo del mando aplicado respeta `δ_max = 0,15` en 559 de 559 corridas evaluables de enforcement. En monitorización solo lo cumple el 67,6 %, y la peor tasa llega a 0,43. De paso, es la medida más directa de lo que vale C-06.
- **² SR-009 — Satisfecho fuera de banda (D-64, ratificado por D-69).** SC-PERT-03 quedó fuera de la campaña por protocolo, así que el veredicto no sale de la agregación sino de tres partes medidas por separado: la política nominal nunca se para, un intento deliberado de hacer que se pare no funciona, y el detector salta ante una parada real inyectada por un script.
- **³ SR-010 — `No satisfecho`, hallazgo confirmado de clase B (D-69).** Es el único requisito que el trabajo cierra como incumplido, y se midió dos veces con dos políticas distintas: 30 de 85 puntos de rejilla dentro del ODD con la política anterior, y 16 de 85 con la de referencia. Se concentra en la co-activación de C-01 y C-02, y desaparece donde no hay conflicto entre la corrección lateral y la de rumbo. Como es de clase B, no bloquea el veredicto global.
- **⁴ SR-012 / SR-014 — Satisfechos.** Los escenarios perturbados aprueban en enforcement, incluido el del carril falso inyectado. Cuando el criterio de un escenario marca fallo, lo hace *solo* por la cláusula de ausencia de emergencia: la cage hizo su parada controlada ante una percepción degradada, y el criterio cuenta esa parada segura como fallo. El criterio propio de SR-012 se cumple en todos los casos.
- **⁵ SR-013 — Satisfecho.** La parada en lazo abierto se hace dentro del presupuesto de tiempo y sin tocar el borde. Tener cobertura por los dos lados cierra la carencia de la versión anterior, que no tenía un segundo escenario adverso.
- **⁶ SC-PERT-11 / 12 / 13** (marcas desgastadas, degradación de imagen y las dos combinadas) amplían la familia adversa de SR-012 / SR-014 y dan a SR-013 su segundo escenario adverso. Puntúan 30/30, 40/40 y 40/40 en enforcement, frente a 0/30, 23/40 y 0/40 en monitorización.
- **⁷ SR-002 / SR-003 — Satisfechos sobre su propio criterio (D-47).** El «fallo» de SC-EDGE-01 viene de una cláusula de rendimiento heredada del óvalo (tiempo de recuperación del rumbo) que no es el criterio de satisfacción documentado de ninguno de los dos. SR-002 pide `M-P4 ≤ 25°`, y el máximo medido es 14,2°. SR-003 pide un margen de tiempo que nunca se pierde, con una excursión lateral máxima de 0,043 m y cero emergencias. Ver §8.3.
- **⁹ El veredicto de referencia es la campaña 2-D PPO 550k** (31.07.2026, D-69). SR-012 / SR-013 / SR-014 se cumplen en los dos brazos de cámara. Las filas de arriba citan esa campaña como evidencia vigente y mantienen GE4-V2 como registro congelado de la puerta G4.

## F.2 Forma procesable por máquina

Cada fila es una cadena desde un peligro hasta una métrica. Un mismo peligro aparece en varias filas porque cubre varias cadenas. La columna de veredicto físico está vacía en todas las filas: la cadena de despliegue está construida y se ha puesto en marcha sobre hardware, pero ningún escenario se ha puntuado allí (§9.3.1, §10.4).

| Peligro | Requisito | Regla | Tipo | Escenario | Métrica | Veredicto sim. | Veredicto fís. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-01 | M-S1 | satisfecho | pendiente |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-02 | M-S1 | satisfecho | pendiente |
| H-01 | SR-001 | C-01 | cage rule | SC-EDGE-02 | M-S1 | satisfecho | pendiente |
| H-01 | SR-001 | C-01 | cage rule | SC-NOM-01 | M-S2 | satisfecho | pendiente |
| H-01 | SR-003 | C-03 | cage rule | SC-NOM-02 | M-S4 | satisfecho | pendiente |
| H-01 | SR-003 | C-03 | cage rule | SC-EDGE-01 | M-S4 | satisfecho | pendiente |
| H-02 | SR-002 | C-02 | cage rule | SC-EDGE-01 | M-P4 | satisfecho | pendiente |
| H-02 | SR-002 | C-02 | cage rule | SC-EDGE-04 | M-P4 | satisfecho | pendiente |
| H-02 | SR-003 | C-03 | cage rule | SC-EDGE-01 | M-S4 | satisfecho | pendiente |
| H-03 | SR-004 | C-04 | cage rule | SC-NOM-02 | M-P3 | satisfecho | pendiente |
| H-03 | SR-004 | C-04 | cage rule | SC-EDGE-03 | M-P3 | satisfecho | pendiente |
| H-04 | SR-005 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfecho | pendiente |
| H-05 | SR-006 | C-06 | cage rule | SC-NOM-01 | M-I5 | satisfecho | pendiente |
| H-05 | SR-006 | C-06 | cage rule | SC-NOM-02 | M-I5 | satisfecho | pendiente |
| H-06 | SR-007 | C-05 | cage rule | SC-PERT-02 | M-S3 | satisfecho | pendiente |
| H-07 | SR-005 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfecho | pendiente |
| H-07 | SR-008 | C-05 | cage rule | SC-NOM-03 | M-S3 | satisfecho | pendiente |
| H-07 | SR-008 | C-05 | cage rule | SC-EDGE-04 | M-S3 | satisfecho | pendiente |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-04 | M-S1 | satisfecho | pendiente |
| H-10 | SR-012 | C-02 | cage rule | SC-PERT-05 | M-S1 | satisfecho | pendiente |
| H-10 | SR-012 | C-03 | cage rule | SC-PERT-06 | M-S2 | satisfecho | pendiente |
| H-10 | SR-012 | — | training | SC-PERT-04 | M-S2 | satisfecho | pendiente |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-09 | M-S1 | satisfecho | pendiente |
| H-10 | SR-012 | C-01 | cage rule | SC-PERT-10 | M-S1 | satisfecho | pendiente |
| H-11 | SR-013 | C-05 | cage rule | SC-PERT-07 | M-S3 | satisfecho | pendiente |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-08 | M-S1 | satisfecho | pendiente |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-08 | M-S3 | satisfecho | pendiente |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-09 | M-S3 | satisfecho | pendiente |
| H-12 | SR-014 | C-05 | cage rule | SC-PERT-10 | M-S3 | satisfecho | pendiente |
| H-08 | SR-009 | — | training constraint | SC-NOM-01 | M-P6 | satisfecho | pendiente |
| H-08 | SR-009 | — | training constraint | SC-PERT-03 | M-P6 | satisfecho | pendiente |
| H-09 | SR-010 | — | arbiter | SC-EDGE-04 | M-I3 | satisfecho | pendiente |
| H-09 | SR-010 | — | arbiter | SC-EDGE-05 | M-S2 | no satisfecho | pendiente |

## F.3 Restricciones verificadas

El validador comprueba de forma automática que: todo peligro está referenciado por al menos un requisito; todo requisito referencia al menos un peligro; todo requisito está implementado por al menos una regla, una restricción de entrenamiento o una propiedad de arbitraje; toda regla implementa al menos un requisito; toda regla se prueba en al menos un escenario; todo escenario referencia al menos un requisito; todo requisito tiene al menos una métrica que lo verifica; y toda métrica referenciada está definida.

**Estado al cierre: todas las comprobaciones pasan, sin huérfanos y sin avisos.**
