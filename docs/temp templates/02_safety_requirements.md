# Safety Requirements Specification v1.0

**Última actualización:** YYYY-MM-DD
**Documento fuente:** docs/01_hazard_register.md (v1.0)

## Principios

- Cada SR DEBE ser falsable: expresable como una condición que puede afirmarse o negarse mediante observación/medición.
- Cada SR DEBE referenciar al menos un hazard.
- Cada SR DEBE ser implementable por al menos un mecanismo trazable (cage rule, constraint de entrenamiento, test de escenario).

---

### SR-001 — [Nombre corto]

| Campo | Valor |
|-------|-------|
| **ID** | SR-001 |
| **Nombre** | Lane Departure Prevention |
| **Enunciado formal** | Under nominal ODD conditions, the absolute lateral offset of the vehicle from the lane centreline SHALL NOT exceed d_max = (lane_width/2) - safety_margin at any time. |
| **Parámetros** | d_max = 0.16 m (for lane_width = 0.4 m, safety_margin = 0.04 m) |
| **Hazards referenciados** | H-01 |
| **Cage rules que lo implementan** | C-01, C-03 |
| **Escenarios que lo verifican** | SC-NOM-01, SC-NOM-02, SC-EDGE-02 |
| **Métricas asociadas** | M-S1 (Max lateral offset), M-S2 (Boundary violations) |
| **Criterio de satisfacción** | M-S1 ≤ d_max en 100% de runs; M-S2 = 0 en modo enforcement |
| **Rationale del umbral** | safety_margin de 4 cm tolera incertidumbre de sensor LiDAR (σ≈1 cm observada) y latencia de control de hasta 50 ms |
| **Notas** | — |

---

### SR-002 — [...]

(mismo formato)