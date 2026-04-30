# Safety Cage Specification v1.0

**Última actualización:** YYYY-MM-DD
**Documento fuente:** docs/02_safety_requirements.md (v1.0)

## Convenciones

- Cada regla es una función pura: f(state, action_raw) → (action_safe, intervention_flag, rule_id).
- Las reglas se evalúan en orden C-01, C-02, ... Cn en cada ciclo de control.
- Parámetros numéricos se cargan desde `config/cage_params.yaml`.

---

### C-01 — Lane Boundary Hard Limit

| Campo | Valor |
|-------|-------|
| **ID** | C-01 |
| **Nombre** | Lane Boundary Hard Limit |
| **SRs implementados** | SR-001 |
| **Hazards mitigados (vía SR)** | H-01 |
| **Entrada** | state.lateral_offset (m), action_raw.steering ([-1,1]) |
| **Constraint formal** | abs(state.lateral_offset) <= d_max |
| **Parámetros** | d_max = 0.16 m |
| **Lógica de corrección** | Si constraint violado o predicho violado en siguiente step: forzar steering hacia centreline con magnitud proporcional a excess offset, clipped a steering_max. |
| **Output** | action_safe, intervention_flag=True si se corrige |
| **Test vectors** | ver `tests/cage/test_C01.py` |
| **Rationale** | Constraint fundamental: traduce SR-001 directamente. Corrección proporcional evita oscilación. |

---

### C-02 — [...]

(mismo formato)