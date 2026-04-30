# Traceability Matrix v1.0 (Explicativo)

**Fuente canónica:** `docs/05_traceability_matrix.csv`
**Validador:** `scripts/check_traceability.py`

## Cómo se lee cada fila

Cada fila es una aserción:
"Para mitigar el hazard [hazard_id], se ha definido el requerimiento [sr_id], implementado por la cage rule [cage_rule_id], verificado mediante el escenario [scenario_id] midiendo la métrica [metric_id], con evidencia en [evidence_ref], concluyendo [conclusion]."

## Invariantes verificados automáticamente

- Todo hazard_id aparece en ≥1 fila (no hay hazards huérfanos).
- Todo sr_id aparece en ≥1 fila.
- Todo cage_rule_id aparece en ≥1 fila o está documentado como "monitoring-only".
- conclusion ∈ {TBD, SATISFIED, PARTIAL, NOT_SATISFIED}.
- evidence_ref apunta a un archivo que existe (en fases avanzadas).