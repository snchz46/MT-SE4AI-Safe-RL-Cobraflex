# Anexo I — Desglose de la campaña de referencia

Datos generados directamente a partir de los artefactos de la campaña
(`campaign_report.json` y `failure_mode_breakdown.json`): 1.890 corridas, 0 errores,
27 escenarios × 2 modos, sobre la política bidimensional de referencia.

## I.1 Corridas aprobadas por escenario y modo

El veredicto de la columna derecha corresponde al modo *enforcement* y se calcula contra el
criterio de aprobación declarado por cada escenario, con el umbral de fracción que ese
escenario fija.

| Escenario | Enforcement | Monitoring | Veredicto enf. |
| --- | ---: | ---: | :-: |
| SC-EDGE-01 | 8/30 | 4/30 | ✗ |
| SC-EDGE-02 | 29/30 | 22/30 | ✓ |
| SC-EDGE-03 | 25/25 | 25/25 | ✓ |
| SC-EDGE-04 | 30/30 | 0/30 | ✓ |
| SC-EDGE-05 | 44/100 | 25/100 | ✗ |
| SC-FRONT-01 | 0/25 | 0/25 | ✗ |
| SC-FRONT-02 | 25/25 | 25/25 | ✓ |
| SC-FRONT-03 | 25/25 | 0/25 | ✓ |
| SC-FRONT-04 | 19/25 | 0/25 | ✗ |
| SC-FRONT-05 | 25/25 | 6/25 | ✓ |
| SC-FRONT-06 | 17/25 | 0/25 | ✗ |
| SC-FRONT-07 | 25/25 | 25/25 | ✓ |
| SC-NOM-01 | 50/50 | 50/50 | ✓ |
| SC-NOM-02 | 49/50 | 44/50 | ✓ |
| SC-NOM-03 | 25/25 | 8/25 | ✓ |
| SC-PERT-01 | 60/60 | 60/60 | ✓ |
| SC-PERT-02 | 40/40 | 40/40 | ✓ |
| SC-PERT-04 | 40/40 | 33/40 | ✓ |
| SC-PERT-05 | 40/40 | 37/40 | ✓ |
| SC-PERT-06 | 40/40 | 40/40 | ✓ |
| SC-PERT-07 | 25/25 | 25/25 | ✓ |
| SC-PERT-08 | 25/25 | 25/25 | ✓ |
| SC-PERT-09 | 25/25 | 0/25 | ✓ |
| SC-PERT-10 | 25/25 | 25/25 | ✓ |
| SC-PERT-11 | 30/30 | 30/30 | ✓ |
| SC-PERT-12 | 40/40 | 32/40 | ✓ |
| SC-PERT-13 | 40/40 | 20/40 | ✓ |

## I.2 Estado por requisito

| Requisito | Clase | Estado en la campaña | Escenarios que fallan |
| --- | :-: | --- | --- |
| SR-001 | A | satisfecho | — |
| SR-002 | A | fallo literal | SC-EDGE-01 |
| SR-003 | A | fallo literal | SC-EDGE-01 |
| SR-004 | A | satisfecho | — |
| SR-005 | A | satisfecho | — |
| SR-006 | B | fuera de banda | — |
| SR-007 | A | satisfecho | — |
| SR-008 | A | satisfecho | — |
| SR-009 | B | evidencia insuficiente | — |
| SR-010 | B | fallo literal | SC-EDGE-05 |
| SR-011 | B | fallo literal | SC-EDGE-01 |
| SR-012 | A | satisfecho | — |
| SR-013 | A | satisfecho | — |
| SR-014 | A | satisfecho | — |

## I.3 Invariante de seguridad (modo enforcement)

| Magnitud | Valor |
| --- | ---: |
| Corridas de enforcement | 945 |
| Contactos con el borde de la calzada | 56 |
| Corridas con excursión lateral ≥ límite | 69 |
| Excursión lateral máxima (m) | 0.2824 |

Los contactos contabilizados corresponden en su totalidad a corridas cuya condición
inicial cae fuera del dominio operacional (familias límite y de frontera). Dentro del
dominio, el recuento es cero.

## I.4 Rejilla de co-activación: desglose del veredicto negativo

Partición de la rejilla según si el punto inyectado cae dentro del dominio operacional:

| Bloque | Corridas | Aprobadas | Fallidas | Violaciones de margen lateral |
| --- | ---: | ---: | ---: | ---: |
| Dentro del ODD | 85 | 42 | 43 | 16 |
| Fuera del ODD | 15 | 2 | 13 | 10 |

Desglose por combinación de reglas efectivamente co-activadas, que es lo que localiza el
problema de arbitraje:

| Combinación de reglas | Corridas | Fallos | Violaciones de margen lateral | Dentro del ODD |
| --- | ---: | ---: | ---: | ---: |
| C-01 ∧ C-02 | 20 | 15 | 11 | 15 |
| C-01 ∧ C-02 ∧ C-04 | 20 | 14 | 11 | 15 |
| C-01 ∧ C-03 | 20 | 15 | 4 | 20 |
| C-01 ∧ C-04 ∧ C-06 | 20 | 12 | 0 | 15 |
| C-04 ∧ C-06 | 20 | 0 | 0 | 20 |

La lectura está en §8.6: las violaciones se concentran donde la corrección lateral y la de
rumbo entran en conflicto, y desaparecen donde no lo hacen.
