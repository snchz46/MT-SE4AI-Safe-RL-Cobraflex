# Hazard Register v1.0

**Última actualización:** YYYY-MM-DD
**Sistema:** Lane-following autonomous driving function
**ODD referenciado:** docs/00_odd_specification.md (v1.0)

## Convenciones de rating

- **Severidad (S):** S1=leve, S2=moderado, S3=severo, S4=catastrófico
- **Exposición (E):** E1=muy baja, E2=baja, E3=media, E4=alta
- **Controlabilidad (C):** C1=totalmente controlable, C2=simplemente controlable, C3=difícilmente controlable
- **ASIL-like rating** (combinación S×E×C, referencia indicativa, no uso formal de ASIL):
  - QM, A, B, C, D (de menor a mayor criticidad)

## Registro de Hazards

---

### H-01 — [Nombre corto del hazard]

| Campo | Valor |
|-------|-------|
| **ID** | H-01 |
| **Nombre** | Unintended Lane Exit |
| **Descripción** | The vehicle crosses the lane boundary laterally without intent. |
| **Condiciones operacionales** | Any speed within ODD; curves or straight sections. |
| **Causa raíz hipotetizada** | Policy produces steering action that accumulates lateral offset; sensor noise induces incorrect state estimation; sudden curvature not anticipated. |
| **Consecuencia** | Loss of lane discipline, potential collision with out-of-lane objects in real-world analog. |
| **Severidad (S)** | S3 (severe in scale: high energy collision possible in operational analog) |
| **Exposición (E)** | E3 (medium: expected in several scenarios per operational hour) |
| **Controlabilidad (C)** | C2 (simply controllable if detected in time) |
| **Rating** | B-like |
| **SRs que lo mitigan** | SR-001, SR-003 |
| **Notas** | — |

---

### H-02 — [...]

(mismo formato)

---

## Cobertura (auto-generable desde matriz)

| Hazard | SRs cubiertos | Nota |
|--------|---------------|------|
| H-01 | SR-001, SR-003 | Cobertura directa y predictiva (TTLC) |
| ...  | ...           | |