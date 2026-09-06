# Anexo F — Matriz de trazabilidad

La matriz existe en dos formas complementarias que se mantienen sincronizadas: una legible,
organizada por cadena de mitigación, y otra procesable por máquina sobre la que el validador
comprueba las ocho restricciones de cobertura. Una violación de cualquiera de ellas bloquea la
puerta de revisión correspondiente.

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

**Notas de la tabla F.1.** Los ocho marcadores remiten al desarrollo completo de cada caso en el
documento vivo de trazabilidad; aquí se recoge la versión condensada.

- **¹ SR-006 — Satisfecho sobre su propia métrica (D-39).** La agregación gruesa sobre «todos los
  escenarios» le hacía heredar un fallo de fracción ajeno a la suavidad, de modo que se puntúa
  directamente sobre su métrica: en los pasos que el limitador realmente gobierna —sin regla de
  seguridad prevaleciendo ni emergencia— la variación por ciclo del mando comprometido respeta
  `δ_max = 0,15` en 559 de 559 corridas evaluables de enforcement; en monitorización solo el
  67,6 % aguanta y la peor tasa llega a 0,43. Es, de paso, la medida más directa del valor de C-06.
- **² SR-009 — Satisfecho fuera de banda (D-64, ratificado por D-69).** SC-PERT-03 quedó excluido de
  la campaña por protocolo, de modo que el veredicto no procede de la agregación sino de tres partes
  medidas por separado: la política nominal nunca se detiene; un intento deliberado de forzarla a
  detenerse no lo consigue; y el detector dispara ante una parada real inyectada por guion.
- **³ SR-010 — `No satisfecho`, hallazgo determinado de clase B (D-69).** Es el único requisito que el
  trabajo cierra como incumplido, medido dos veces sobre dos políticas distintas: 30 de 85 puntos
  de rejilla dentro del ODD en la política anterior, 16 de 85 en la de referencia. Se concentra en la
  co-activación de C-01 y C-02, y desaparece donde no hay conflicto entre corrección lateral y de
  rumbo. Al ser de clase B no veta el veredicto global.
- **⁴ SR-012 / SR-014 — Satisfechos.** Los escenarios perturbados aprueban en enforcement, incluido el
  carril falso inyectado. Donde el criterio del escenario marca fallo, lo hace *solo* por la cláusula
  de ausencia de emergencia: la cage ejecutó su parada controlada sobre una percepción degradada y el
  criterio puntúa esa parada segura como fallo. El criterio propio de SR-012 se cumple en todos los casos.
- **⁵ SR-013 — Satisfecho.** La parada en lazo abierto se ejecuta dentro de presupuesto, sin contacto
  con el borde, y la cobertura por ambos lados cierra la carencia que la versión anterior arrastraba
  al no disponer de un segundo escenario adverso.
- **⁶ SC-PERT-11 / 12 / 13** —marcas desgastadas, degradación de imagen y ambas combinadas— amplían la
  familia adversa de SR-012 / SR-014 y dan a SR-013 su segundo escenario adverso. Puntúan 30/30,
  40/40 y 40/40 en enforcement, contra 0/30, 23/40 y 0/40 en monitorización.
- **⁷ SR-002 / SR-003 — Satisfechos sobre su propio criterio (D-47).** El «fallo» de SC-EDGE-01 es una
  cláusula de rendimiento heredada del óvalo —tiempo de recuperación de rumbo— que no es el criterio
  de satisfacción documentado de ninguno de los dos: SR-002 exige `M-P4 ≤ 25°` y el máximo medido es
  14,2°; SR-003 exige un margen de tiempo que nunca se compromete, con excursión lateral máxima de
  0,043 m y cero emergencias. Véase §8.3.
- **⁹ El veredicto de récord es la campaña 2-D PPO 550k** (31.07.2026, D-69). SR-012 / SR-013 / SR-014
  están satisfechos en ambos brazos de cámara; las filas anteriores citan esa campaña como
  evidencia vigente y conservan GE4-V2 como registro congelado de la puerta G4.

## F.2 Forma procesable por máquina

Cada fila representa una cadena desde un peligro hasta una métrica. Un peligro aparece en
varias filas porque abarca varias cadenas. La columna de veredicto físico permanece pendiente
en su totalidad: la fase de despliegue está construida pero no ejecutada sobre hardware.

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

El validador comprueba mecánicamente que: todo peligro está referenciado por al menos un
requisito; todo requisito referencia al menos un peligro; todo requisito está implementado por
al menos una regla, restricción de entrenamiento o propiedad de arbitraje; toda regla
implementa al menos un requisito; toda regla es ejercitada por al menos un escenario; todo
escenario referencia al menos un requisito; todo requisito tiene al menos una métrica
verificadora; y toda métrica referenciada está definida.

**Estado al cierre: todas las comprobaciones pasan, sin huérfanos y sin avisos.**
