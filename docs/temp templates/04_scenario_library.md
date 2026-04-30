# Scenario Library v1.0

**Última actualización:** YYYY-MM-DD

## Principios

- Los escenarios son reproducibles: mismo seed + config → mismo comportamiento inicial.
- Cada escenario tiene criterio pass/fail explícito.
- Cada escenario se ejecuta N_runs para soportar análisis estadístico.

---

### SC-NOM-01 — Straight Track Nominal

| Campo | Valor |
|-------|-------|
| **ID** | SC-NOM-01 |
| **Categoría** | Nominal |
| **Descripción** | Recta de 3 m, condiciones ideales, sin perturbaciones. |
| **Condiciones iniciales** | pose = (0, 0), heading = 0°, lateral_offset = 0 m, speed_cmd = v_nominal |
| **Perturbaciones** | Ninguna |
| **N_runs** | 50 |
| **SRs verificados** | SR-001, SR-002, SR-004 |
| **Cage rules esperadas activar** | Ninguna (nominal) |
| **Métricas principales** | M-P1 (lateral RMSE), M-P2 (completion rate), M-I1 (intervention rate) |
| **Criterio pass** | M-P1 < 0.05 m AND M-P2 = 100% AND M-I1 < 5% |
| **Criterio fail** | M-P2 < 100% OR M-P1 > 0.10 m |
| **Notas** | Baseline scenario. Cualquier fallo aquí indica problema grave. |

---

### SC-EDGE-01 — Heading Error Perturbation at Start

| Campo | Valor |
|-------|-------|
| **ID** | SC-EDGE-01 |
| **Categoría** | Edge case |
| **Descripción** | Start con heading error de +15° (derecha). Policy debe recuperar. |
| **Condiciones iniciales** | pose = (0, 0), heading = +15°, lateral_offset = 0 m |
| **Perturbaciones** | Solo en init |
| **N_runs** | 30 |
| **SRs verificados** | SR-002, SR-003 |
| **Cage rules esperadas activar** | C-02 (heading), posiblemente C-03 (TTLC) |
| **Métricas principales** | M-I2, M-S3 (emergency stop rate), M-P4 (heading recovery time) |
| **Criterio pass** | M-S3 = 0 AND vehicle recovers to heading error < 3° within 2 s |
| **Criterio fail** | Emergency stop OR lane exit |
| **Notas** | Tests cage intervention responsiveness. |