# Anexo F — Matriz de trazabilidad

La matriz existe en dos formas complementarias que se mantienen sincronizadas: una legible,
organizada por cadena de mitigación, y otra procesable por máquina sobre la que el validador
comprueba las ocho restricciones de cobertura. Una violación de cualquiera de ellas bloquea la
puerta de revisión correspondiente.

## F.1 Resumen por cadena de mitigación

| Hazard | Safety Requirement | Cage Rule(s) | Scenarios | Verifying Metric(s) | Verdict (Sim) |
| ------ | ------------------ | ------------ | --------- | ------------------- | ------- |
| H-01 | SR-001 | C-01 | SC-NOM-01, SC-NOM-02, SC-EDGE-02 | M-S1 | **Satisfied** |
| H-01, H-02 | SR-003 | C-03 | SC-NOM-02, SC-EDGE-01 | M-S4 | **Satisfied** ⁷ |
| H-02 | SR-002 | C-02 | SC-EDGE-01, SC-EDGE-04 | M-P4 | **Satisfied** ⁷ |
| H-02 | SR-011 | C-06 + training | SC-EDGE-01, SC-EDGE-04 | M-P7 | **Satisfied** |
| H-03 | SR-004 | C-04 | SC-NOM-02, SC-EDGE-03 | M-P3 | **Satisfied** |
| H-04, H-07 | SR-005 | C-05 | SC-EDGE-04 | M-S3 | **Satisfied** |
| H-05 | SR-006 | C-06 | All scenarios | M-I5 | **Satisfied** ¹ |
| H-06 | SR-007 | C-05 (state-validity triggers) | SC-PERT-02 | M-S3 | **Satisfied** |
| H-07 | SR-008 | C-05 (external-stop trigger) | SC-NOM-03, SC-EDGE-04 | M-S3 | **Satisfied** |
| H-08 | SR-009 | training | SC-NOM-01, SC-NOM-02, SC-NOM-03, SC-PERT-03 | M-P6, M-S2 (monitoring) | **Satisfied** (out-of-band, D-64/D-69) ² |
| H-09 | SR-010 | arbiter | SC-EDGE-04, SC-EDGE-05 | M-S2, M-I3 | **Not satisfied** — CL-B finding, non-vetoing (D-69) ³ |
| H-10 | SR-012 | C-01, C-02, C-03 (over CV state) + training | SC-NOM-01, SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10, SC-PERT-11, SC-PERT-12, SC-PERT-13 | M-S1, M-S2 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record; D-29 coverage closed) ⁴ ⁶ ⁹ |
| H-11 | SR-013 | C-05 (CV-estimator health → controlled stop) | SC-NOM-01, SC-PERT-07, SC-PERT-13 | M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-07 25/25 + SC-PERT-13 40/40; D-29 closed by D-46) ⁵ ⁶ ⁹ |
| H-12 | SR-014 | C-05 (plausibility check → controlled stop) | SC-NOM-01, SC-PERT-08, SC-PERT-04..06, SC-PERT-09..10, SC-PERT-11..13 | M-S1, M-S3 | **Satisfied** (2-D PPO 550k, verdict of record; GE4-V2 gate record: SC-PERT-08 false-lane 25/25) ⁴ ⁶ ⁹ |

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
| H-09 | SR-010 | — | arbiter | SC-EDGE-05 | M-S2 | **no satisfecho** | pendiente |

## F.3 Restricciones verificadas

El validador comprueba mecánicamente que: todo peligro está referenciado por al menos un
requisito; todo requisito referencia al menos un peligro; todo requisito está implementado por
al menos una regla, restricción de entrenamiento o propiedad de arbitraje; toda regla
implementa al menos un requisito; toda regla es ejercitada por al menos un escenario; todo
escenario referencia al menos un requisito; todo requisito tiene al menos una métrica
verificadora; y toda métrica referenciada está definida.

**Estado al cierre: todas las comprobaciones pasan, sin huérfanos y sin avisos.**
