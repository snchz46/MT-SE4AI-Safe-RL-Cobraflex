# Capítulo 11 — Discusión

Convención: las secciones marcadas [BORRADOR POST-G4] contienen prosa
provisional redactada tras el cierre de G4 (02.07.2026), a falta de la evidencia
física de Fase 5; el veredicto sobre cada criterio del marco y sobre las
hipótesis se emite aquí en versión **provisional** y se re-cierra en Fase 6.
Este capítulo evalúa el **marco**, no el sistema: la pregunta es si el V-Model
adaptado resultó útil para producir el sistema, no si el sistema resultó útil
(§3.7).

---

## 11.1 Propósito y método de esta discusión  [BORRADOR POST-G4]

El Capítulo 3 fijó por adelantado (§3.7.1) cinco criterios meta con indicadores
medibles, precisamente para que esta evaluación no degenerara en
autocomplacencia retrospectiva. Este capítulo los recorre uno a uno con la
evidencia registrada (§11.2), evalúa las tres hipótesis de §1.3 (§11.3), destila
las lecciones aprendidas que no estaban en el diseño original (§11.4), compara
con las prácticas alternativas que el marco desplaza (§11.5), y cierra con
limitaciones y riesgos residuales (§11.6–11.7). El registro primario para todo
ello es `DECISIONS.md` (55 entradas hasta D-61) y el CHANGELOG: la disciplina de anotar
decisiones y costes *cuando ocurrían* es lo que permite que esta sección cite en
lugar de recordar.

## 11.2 El marco contra sus cinco criterios (§3.7.1)  [BORRADOR POST-G4 — PROVISIONAL]

**(1) Integridad de la trazabilidad — criterio: cero huérfanos.** Cumplido de
forma continua: `check_traceability.py` pasó sin huérfanos en cada gate (G1–G4)
y en la matriz consolidada al cierre de G4 (12 hazards, 14 SRs, 6 reglas, 28
escenarios, 19 métricas). El dato relevante no es el cero final sino que la
restricción operó como **gate duro durante** el desarrollo: los IDs huérfanos se
detectaban al introducirse, no en una auditoría final.

**(2) Cobertura de SRs por evidencia — criterio: 100 % con veredicto, aunque sea
fail o parcial.** Cumplido: 14/14 SRs tienen veredicto respaldado por evidencia
cuantitativa (tabla §10.4), incluyendo dos abstenciones documentadas (que son
veredictos sobre la *evidencia*, no omisiones — distinción D-30/D-38) y dos
fallos literales mantenidos en el registro con su reconciliación (D-47). La
cláusula "preferible un veredicto honesto a una omisión" se ejercitó de verdad:
el global del brazo de cámara quedó `NOT SATISFIED` literal en el documento de
registro.

**(3) Anticipación de hazards — criterio: la mayoría de lo observado estaba
anticipado; lo no anticipado es auditable.** Sustancialmente cumplido, con dos
casos instructivos. De los hazards que se manifestaron en operación, casi todos
estaban en el registro desde F1 (H-01..H-08) o se añadieron al abrir el track de
cámara (H-10/H-11/H-12) **antes** de que la campaña los midiera. Los dos
emergentes: (a) el **conflicto cage–CV** de la semilla 23 —el enforcement
degradando a una policy competente por una lectura CV confiada pero errónea— es
una manifestación no anticipada *como modo propio* aunque su raíz (H-12) sí
estaba registrada; quedó auditado en §7.5.3 y motiva T3/T5 (cap. 12). (b) El
**óptimo degenerado de "aparcar"** de la acción 2-D en Isaac (D-56) es un hazard
de proceso de entrenamiento (H-08, familia reward-hacking) que el registro
anticipaba en abstracto y la instancia concreta requirió descubrir. En ambos
casos el marco absorbió el emergente por la vía prevista: ID, decisión, artefacto.

**(4) Coste de adopción — criterio: proporcional al beneficio.** Evaluación
provisional: proporcional. El registro contiene 61 decisiones hasta D-67, el validador, las
plantillas y los documentos vivos 00–16 mantenidos al día de los resultados por
una sola persona *mientras* se ejecutaban dos campañas de evaluación, dos pistas
de entrenamiento y un puente de simulador. La cifra de reparto exacto
marco-vs-técnica no se midió en horas (límite declarado en §3.7.2); el proxy
registrado es que ningún gate se retrasó por artefactos del marco, y sí hubo
retrasos por causas técnicas (colapsos de entrenamiento, calibraciones Isaac).
*(Re-evaluar al cierre con el registro completo de Fase 5–6.)*

**(5) Productividad de la matriz — criterio: casos documentados donde aceleró el
análisis de impacto.** Cumplido con ejemplos concretos: (a) el defecto de
higiene de criterios que produjo el `NOT SATISFIED` literal se **localizó en
minutos** siguiendo la fila SR-002/003 → SC-EDGE-01 → cláusula, porque la
cadena criterio-escenario-SR estaba materializada (D-47); (b) el re-scoring de
SR-006 sobre su métrica propia (D-39) fue posible porque la matriz distinguía
qué escenarios ejercitan qué SR con qué métrica; (c) la migración óvalo→complex_b
de la biblioteca reutilizó las cadenas existentes con cambios auditables
(CHANGELOG 24.06.2026). El contraejemplo también se registra: la matriz **no**
detectó por sí sola que SC-EDGE-05 corría sin inyectar su grid (0 co-activación
as-run) — la trazabilidad garantiza que el escenario existe y referencia al SR,
no que el runner lo ejecute como se especificó. Ese hueco (validación de
*ejecución*, no solo de *referencia*) es una mejora identificada del marco.

## 11.3 Las hipótesis H1–H3, evaluación provisional  [BORRADOR POST-G4 — PROVISIONAL]

**H1 (de constructo) — soportada.** Las cinco adaptaciones bastaron para cubrir
los modos de fallo RL encontrados durante todo el ciclo; ningún evento del
proyecto exigió una sexta adaptación estructural (los emergentes de §11.2(3) se
absorbieron dentro de las existentes). La inspección estructural del marco
(§3.4–3.6) más esta ausencia de excepciones es la evidencia disponible.

**H2 (de operatividad) — soportada provisionalmente.** Cada adaptación produjo
sus artefactos y estos se mantuvieron vivos (no se escribieron para el gate y
murieron después: docs/02–08 tienen historial de revisión continuo hasta julio).
El coste quedó registrado por decisión, no por horas — suficiente para
"proporcional", insuficiente para una cuantificación fina (límite §3.7.2).

**H3 (de utilidad) — soportada en su mitad de simulación.** El marco produjo
veredictos fundamentados con límites de validez declarados (§10.5), incluyendo
la capacidad —que era el test real— de emitir veredictos **incómodos** sin
romperse: el literal negativo, las abstenciones, los residuos H-12/SR-010. La
mitad física de H3 (¿sobrevive la cadena de evidencia al hardware?) queda
abierta hasta Fase 5.

## 11.4 Lecciones aprendidas  [BORRADOR POST-G4]

Las que no estaban en el diseño original y un lector que aplique el marco debería
conocer (desarrollo en cap. 12 §12.2; aquí la forma general):

1. **La higiene de criterios es un artefacto de primera clase.** Las cláusulas
   de escenario y los criterios de SR divergen silenciosamente cuando la
   biblioteca migra de geometría; deben versionarse y distinguirse en el esquema
   (predicado-de-SR vs sobrecapa de performance). El coste de no hacerlo fue el
   veredicto global literal del brazo E.
2. **La semántica de agregación debe fijarse antes de la campaña.**
   Indeterminado ≠ fallo (D-38); abstención documentada ≠ omisión (D-30). Sin
   esas distinciones, los defectos de instrumentación se disfrazan de fallos de
   seguridad y viceversa.
3. **La curva de entrenamiento no clasifica la seguridad; el eval multi-modo
   sí** (D-36 extendido, §7.5.3). Cinco curvas indistinguibles produjeron tres
   comportamientos de seguridad distintos, y en la policy 2-D el checkpoint del
   **pico de recompensa fue el peor** de los tres candidatos evaluados —14
   intervenciones de seguridad frente a 0 del elegido (D-66, §7.5.5).
4. **Los umbrales están acoplados al régimen para el que se calibraron.** El
   traslado 1-D→2-D invalidó el envelope de velocidad sin tocar una línea de la
   cage (D-59); "parámetro `[provisional]`" resultó significar "válido en el
   régimen donde se midió". La respuesta posterior convierte esa lección en un
   gate reproducible: cap 0.22 con margen explícito, checkpoint fresh-only y
   preflight D-43 ligado a checkpoint/config. La matriz histórica discrimina
   mecanismos —entfix-2024/42 pasan, auto-175k falla también a 0.22—, por lo que
   velocidad y percepción no deben colapsarse en una sola causa.
5. **Entre simuladores no hay transferencia silenciosa** — ni de checkpoints ni
   de calibraciones (D-54/D-55/D-57); cada discrepancia exigió una sonda
   dedicada. Anticipa la forma del gap físico.
6. **El monitoring como contrafactual barato.** Mantener el modo monitoring en
   toda campaña dio, además del test causal, el diagnóstico diferencial de los
   casos difíciles (la 666 vs la 23 se distinguen por sus trazas de monitoring).

## 11.5 Comparación con prácticas alternativas  [BORRADOR POST-G4 — ampliar]

Contra el **reporte típico de RL aplicado** (curvas de reward + métricas de test
en la semilla campeona): el marco añade el contrafactual causal
(enforcement/monitoring), los veredictos por requisito con criterio pre-fijado y
la trazabilidad auditable; el coste añadido es aproximadamente el doble de
cómputo de campaña y la disciplina documental. Contra el **V-Model clásico
aplicado tal cual**: los supuestos S1–S5 (§3.3) fallan sobre el componente
aprendido — sin las adaptaciones, la columna izquierda no tiene dónde anclar la
especificación del comportamiento entrenado ni la derecha un objeto estable que
verificar. Contra el **safe-RL de entrenamiento restringido** (recompensa
penalizada, RL con restricciones): son complementarios, no rivales — esta tesis
lo exhibe empíricamente: la policy constraint-respecting *aprendió* a no
necesitar la cage (co-adaptación §7.4) y la cage siguió siendo necesaria
exactamente donde el aprendizaje no llega (fuera de distribución, percepción
degradada). *(Sección a ampliar en Fase 6 con las referencias del cap. 2.)*

## 11.6 Limitaciones  [BORRADOR POST-G4]

Las tres estructurales de §3.7.2, con su estado al cierre de G4: **N=1** (un
proyecto, un autor, sin grupo de control metodológico — la inferencia sobre el
marco es por plausibilidad); **sesgo del autor** (mitigado por trazabilidad
auditable y registro de decisiones, no eliminado); **ventana experimental
finita** (el Runtime Monitoring —A3— se evaluó en ventanas de campaña, no en
operación prolongada). A ellas se añaden las empíricas ya declaradas en ch.8
§8.8.2 y cap. 12 §12.4: veredictos solo-Gazebo, una familia de geometrías, una
plataforma, percepción proxy en el brazo F, campaña de veredicto sobre la
semilla principal, umbrales `[provisional]` pendientes de física.

## 11.7 Riesgos residuales  [BORRADOR POST-G4]

Los que quedan **dentro** del sistema tal como se validó, con su evidencia:

- **H-12, under-read confiado del estimador CV** — el residuo activo: 2 breaches
  marginales in-ODD, mecanismo replicado en s≈13.4; SR-014 no puede atraparlo
  por construcción (auto-consistencia). Mitigación propuesta: T3 (cap. 12).
- **Región de co-activación SR-010** — 30/85 puntos in-ODD del grid con breach
  de M-S1 bajo co-activación de reglas; acotada al grid de SC-EDGE-05, no
  observada en operación nominal. Mitigación: T4.
- **Disponibilidad bajo ruido/falsos positivos de percepción** — paros espurios
  (SC-PERT-01 σ=0.05: 7/20; semilla 23: C-05 sobre coche centrado). Fail-safe,
  pero un riesgo operacional real en despliegues con requisitos de
  disponibilidad. Mitigación: T5.
- **Cuencas por semilla** — una policy re-entrenada puede caer en la cuenca
  cage-dependent o de conflicto sin señal en su curva; el gate conductual
  multi-modo (lección 3) es la barrera de proceso.
- **Parámetros no medibles en sim** — `ODD-3.A_LAT_MAX` (TBD-Q10) y las
  latencias reales quedan abiertos hasta la calibración física (M-4, F5).

## 11.8 Síntesis y transición al Capítulo 12  [BORRADOR POST-G4]

La evaluación provisional del marco es favorable en sus cinco criterios, con dos
matices honestos: el coste de adopción está registrado pero no cuantificado en
horas, y la trazabilidad garantiza referencia pero no ejecución (el hueco
SC-EDGE-05). Las hipótesis H1–H2 quedan soportadas, H3 en su mitad de
simulación. Los riesgos residuales están identificados, acotados y con línea de
mitigación asignada. El Capítulo 12 condensa los hallazgos y convierte estas
mitigaciones en el programa de trabajo futuro.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: BORRADOR POST-G4 (16.07.2026). Evaluación de criterios e hipótesis en
versión provisional; re-cerrar tras Fase 5 (y con el registro de coste completo).

  [ ] Re-emitir §11.2(4) coste de adopción con el registro Fase 5-6; considerar
       una tabla resumen decisiones-por-fase como proxy cuantitativo.
  [ ] §11.5: desarrollar la comparación con referencias concretas del cap. 2
       (Kuutti safety cages, safe-RL surveys, UL 4600/Koopman) en Fase 6.
  [ ] Contrastar §11.2(3) con lo que emerja en físico (¿hazards no anticipados
       nuevos?) — la sección está escrita para absorberlo.
  [ ] Decidir reparto final §10.6 vs §11.2 (argumento SE4AI) en Fase 6.
  [ ] La mejora del marco identificada en §11.2(5) (validar *ejecución* además
       de *referencia*) podría formalizarse como propuesta en cap. 12 T7 — hoy
       está implícita en T7(a); decidir si se nombra como sexta adaptación
       candidata o como refinamiento de A4.
-->
