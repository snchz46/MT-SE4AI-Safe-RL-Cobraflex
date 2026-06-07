# Capítulo 8 — Evaluación Experimental (Campaña de Validación)

<!--
Estado: ESQUELETO F4 (D56+).
Extensión objetivo: 14–18 páginas.
Convención (igual que el Capítulo 7):
  [BORRADOR D5X]    → prosa de metodología/diseño, fijable ya (no depende de
                      resultados); escrita en F4 al abrir la campaña.
  [COMPLETAR FASE 4]→ depende de los resultados medidos de la campaña
                      (tablas por escenario, veredictos por SR, deltas
                      enforcement-vs-monitoring, figuras).
  [PULIDO FASE 6]   → retoque estilístico al cierre.

Artefacto L2′ del V-Model adaptado: la scenario library como instrumento de
validación. La campaña ejecuta los escenarios de `docs/05_scenario_library.md`
con las métricas de `docs/06_metrics_catalogue.md` y puebla la matriz de
trazabilidad de `docs/07_traceability_matrix.md`.

Insumos normativos (no duplicar; citar):
  - Escenarios:  docs/05_scenario_library.md  (+ scenarios/*/*.yaml)
  - Métricas:    docs/06_metrics_catalogue.md  (+ docs/data/metrics.csv)
  - Trazabilidad:docs/07_traceability_matrix.md
  - SRs/Hazards: Capítulo 4 (HARA, SRS)
  - Cage:        Capítulo 5 (Cage Specification)
  - Policy:      Capítulo 7 (Training Specification)
-->

## 8.1 Introducción del capítulo  [BORRADOR D56]

Este capítulo presenta la **campaña de validación experimental** del sistema:
la ejecución sistemática de la *scenario library* (Capítulo 4 / `docs/05`) sobre
el pipeline policy + cage construido en las fases anteriores, midiendo las
métricas de `docs/06` y poblando con ellas la matriz de trazabilidad de
`docs/07`. Es el artefacto **L2′** del V-Model adaptado: el lazo de verificación
que cierra cada Safety Requirement contra evidencia logueada.

Mientras los Capítulos 5 y 7 *especificaron* la cage y la policy, este capítulo
*verifica* su comportamiento conjunto. La pregunta rectora no es "¿conduce bien
la policy?" —eso se estableció como línea base en §7.5— sino **"¿qué seguridad
añade la cage, de forma medible y trazable, frente a la policy sola?"**. La
respuesta es el resultado experimental central de la tesis y se obtiene mediante
la comparación **enforcement vs monitoring** (§8.2.2, §8.6).

El capítulo se estructura así. La sección 8.2 fija la metodología experimental:
los ejes de comparación, el contraste enforcement-vs-monitoring, la capa del
sistema que cada familia de escenarios estresa, las métricas y reglas de
veredicto, y el análisis estadístico. Las secciones 8.3–8.5 reportan los
resultados por familia de escenarios (nominal, límite, perturbado). La sección
8.6 cuantifica la contribución causal de la cage. La sección 8.7 presenta la
matriz de trazabilidad poblada. La sección 8.8 discute hallazgos, limitaciones y
amenazas a la validez. La sección 8.9 articula la transición al Capítulo 9
(despliegue físico, Fase 5).

---

## 8.2 Metodología experimental  [BORRADOR D56]

### 8.2.1 Diseño de la campaña

La campaña evalúa **11 escenarios** (3 nominales SC-NOM, 5 límite SC-EDGE, 3
perturbados SC-PERT; `docs/05`) a lo largo de **dos ejes de comparación**:

- **Controlador:** la policy RL de Fase 3 (checkpoint `cobraflex_ppo_lane`, §7.5)
  frente al baseline **PD** de Fase 2 (§6.6). Ambos consumen el mismo estado
  abstracto y el mismo pipeline, de modo que la comparación aísla el efecto del
  controlador.
- **Modo de la cage:** **enforcement** (la cage corrige la acción) frente a
  **monitoring** (la cage observa y registra qué *habría* corregido, pero deja
  pasar la acción cruda). Este eje aísla el efecto de la cage (§8.2.2).

Cada escenario fija condiciones iniciales, perturbaciones, criterio de
terminación, métricas primarias y criterios de paso por-run y por-escenario
(plantilla en `docs/05`). El número de runs por modo está dimensionado para
validez estadística (de 20 a ≥100 según el escenario); el total en simulación
es de **≈1100 runs** sumando escenarios y modos.

> **Multi-semilla (RL).** La variabilidad entre semillas de la policy
> (`seed ∈ {42, 123, 2024, 23, 666}`, **N = 5** entrenadas, §7.2.7) se trata como
> una fuente de varianza de primer orden: los escenarios discriminantes se ejecutan
> sobre las cinco semillas, no sobre una única policy. Dada la **bimodalidad**
> observada en §7.5.3 (**4/5 *constraint-respecting*, 1/5 *cage-dependent***), se
> reportan las semillas individualmente además de su agregado. Esto cumple el
> diferido explícito de §7.2.7.

### 8.2.2 Modos enforcement vs monitoring — el test causal de la cage

El núcleo metodológico de la tesis es que la contribución de la cage debe
**medirse**, no postularse. Para ello, cada escenario se ejecuta en dos modos
sobre el **mismo** controlador y las **mismas** semillas/condiciones:

- **Enforcement:** `cmd = cage.step(state, raw_action)` — la acción aplicada es
  la corregida. Es el modo de despliegue.
- **Monitoring-only:** se aplica la acción **cruda** de la policy; la cage corre
  en paralelo y registra qué reglas *habrían* disparado y qué corrección
  *habría* aplicado, sin actuar.

La diferencia en las métricas de seguridad entre ambos modos **es** la
contribución causal de la cage. La métrica decisiva es **M-S2** (violaciones de
frontera, `|d| > d_max`): por diseño debe ser **0 en enforcement** (la cage lo
garantiza), mientras que en monitoring refleja lo que la policy sola habría
producido. Un delta `M-S2(monitoring) − M-S2(enforcement) > 0`, estadísticamente
significativo, es la evidencia directa de que la cage previene violaciones que
de otro modo ocurrirían (`docs/06` M-S2 note).

Este diseño responde de raíz a la pregunta de defensa "si la policy es buena, ¿de
qué sirve la cage?" (cf. §7.5.2): en nominal el delta puede ser nulo (la policy
se basta), pero en los escenarios límite y perturbados —donde la policy se acerca
a la frontera— el delta materializa el valor protector de la cage.

### 8.2.3 Capa del sistema evaluada — dinámica vs proxy de percepción

El sistema se descompone en capas
`percepción → estado → [policy + cage] → actuación → dinámica`. Esta campaña
valida el bloque **[policy + cage] + actuación + dinámica** *dado* el estado; la
capa de percepción (cámara/lidar → estado) es objeto de la Fase 5 (Capítulo 9).
En consecuencia, cada familia de escenarios estresa una capa distinta, y la
distinción se hace explícita para acotar qué afirma cada resultado:

| Familia | Capa estresada | Naturaleza |
| --- | --- | --- |
| **SC-NOM** | dinámica nominal | estado **verdadero**, operación dentro del ODD |
| **SC-EDGE-01..05** | dinámica/geometría al borde del ODD | estado **verdadero** empujado a la frontera (heading, lateral, velocidad, estado compuesto, co-activación de reglas) |
| **SC-PERT-01/02** | estimación de estado | **proxy de percepción**: ruido (`d_obs = d_true + N(0,σ)`) / latencia inyectados sobre el estado |
| **SC-PERT-03** | máquina de verificación | meta-test (inyección de fallo) de la detectabilidad de SR-009 |

Lectura: los veredictos de seguridad se miden sobre la **pose verdadera** (salir
del carril es un hecho físico), por lo que la validación del *mecanismo* de
seguridad es sólida con estado ground-truth. Los SC-PERT-01/02 modelan el error
de percepción como ruido paramétrico del estado —un *proxy*, no un pipeline real—
y prueban la robustez de la cage a estimación imperfecta. La validación del
pipeline de percepción real y el gap sim-to-real se difieren al Capítulo 9.

### 8.2.4 Métricas y reglas de veredicto

Las métricas se definen en `docs/06` y se agrupan en performance (M-P1..M-P7),
seguridad (M-S1..M-S4), intervención (M-I1..M-I5) y cómputo (M-C1..M-C2). Cada
escenario declara sus `metrics_primary` (deciden el veredicto) y `secondary`
(se reportan). El formato estándar por métrica es mediana, media, desviación
típica y percentiles 5/95.

**Agregación y veredicto.** El veredicto por-run aplica el `pass_criterion_per_run`
del escenario; el veredicto por-escenario aplica el `pass_criterion_per_scenario`
(p.ej. "≥95 % de runs pasan"). La agregación a veredicto por-SR sigue la
convención de recuento de runs (D-29) y la regla de veto (D-30): [COMPLETAR —
resumir D-29/D-30 al fijar el runner de campaña].

### 8.2.5 Análisis estadístico

Las comparaciones enforcement-vs-monitoring (y RL-vs-PD) usan, según el tipo de
métrica (`docs/06`):

- **Continuas** (M-P1, M-S1, …): test t de Welch para diferencia de medias +
  **d de Cohen** para tamaño de efecto; **Mann-Whitney U** si la distribución es
  marcadamente no gaussiana.
- **Binarias** (lane_exit, emergency_activated): χ² o Fisher exacto para
  muestras pequeñas.
- **Distribuciones** (duración de intervención M-I3): Kolmogorov-Smirnov de dos
  muestras.

Umbral de significación: **p < 0.05** para las comparaciones primarias, **p <
0.01** para cualquier afirmación de efecto fuerte. Los tamaños de efecto se
reportan junto a los p-valores para evitar leer significación estadística como
relevancia práctica.

### 8.2.6 Reproducibilidad

Cada run registra sus metadatos de reproducibilidad (commit git, hash de
`cage.yaml`, hash del checkpoint, hash del YAML de escenario, seed, timestamp,
modo) bajo `experiments/sim/runs/<run_id>/`, igual que las corridas de §7.5. La
campaña la orquesta el *campaign runner* [COMPLETAR — referenciar la herramienta
y la convención de `run_id` al fijarla], que ejecuta el grid (escenario × modo ×
controlador × semilla), agrega por-(escenario, modo) y emite los veredictos.

---

## 8.3 Resultados — Escenarios nominales (SC-NOM)  [COMPLETAR FASE 4]

Verifica que el sistema opera dentro del ODD y establece la línea base RL-vs-PD.
SC-NOM-01 ya tiene su evaluación de referencia en §7.5 (run `rl_eval_2024_200k_4k4`
vs PD `ros_run_20260523T153003Z`); aquí se completa con SC-NOM-02 (curva) y
SC-NOM-03 (circuito completo), en ambos modos.

<!-- Tabla esqueleto (rellenar con la campaña):
| Escenario | Controlador | Modo | M-P1 (RMSE, m) | M-S1 (max|d|, m) | M-S2 (/s) | M-I1 (%) | M-S3 (%) | Veredicto |
| SC-NOM-01 | PD  | enforcement | … | … | 0 | 0.047 | 0 | PASS |
| SC-NOM-01 | RL  | enforcement | 0.012 | 0.027 | 0 | 0.023 | 0 | PASS |
| SC-NOM-01 | RL  | monitoring  | … | … | … | … | … | … |
| SC-NOM-02 | …   | …           | … | … | … | … | … | … |
SR cubiertos: SR-001, SR-002, SR-003, SR-004, SR-006, SR-008, SR-009.
Expectativa: delta enforcement-vs-monitoring ≈ 0 (nominal es "fácil"; la cage es latente). -->

---

## 8.4 Resultados — Escenarios límite (SC-EDGE)  [COMPLETAR FASE 4]

Estresan la dinámica/geometría al borde del ODD; **aquí se espera que la cage
empiece a aportar**. SC-EDGE-01 (heading inicial), SC-EDGE-02 (lateral inicial),
SC-EDGE-03 (pulso de velocidad), SC-EDGE-04 (estado compuesto → posible C-05),
SC-EDGE-05 (matriz de co-activación de reglas, SR-010).

<!-- Por escenario: tabla (controlador × modo) con métricas primarias del escenario
(M-I1/M-I2 por regla, M-S2, M-S3, time-to-recovery, M-P7…), + el delta
enforcement-vs-monitoring en M-S2 con su p-valor y d de Cohen.
SC-EDGE-05: foco en la aserción de joint-envelope (M-S2=0) y la ausencia de
oscilación inter-ciclo (M-I3) bajo co-activación (SR-010). -->

---

## 8.5 Resultados — Escenarios perturbados (SC-PERT)  [COMPLETAR FASE 4]

Prueban la robustez a error de estimación de estado (proxy de percepción) y la
detectabilidad de la verificación. SC-PERT-01 (ruido gaussiano sobre el offset
lateral, σ ∈ {0.01, 0.03, 0.05} m), SC-PERT-02 (latencia 50/100 ms), SC-PERT-03
(test negativo de stall, SR-009).

<!-- SC-PERT-01/02: M-I1 y M-S1/M-S2 por nivel de perturbación, en ambos modos
(se espera que M-I1 crezca con σ/latencia; la cage debería contener M-S2 en
enforcement aun cuando la policy degrada). SC-PERT-03: confirmar M-P6>50% en la
variante stall y M-P6=0/M-P2=1 en la released. -->

---

## 8.6 La contribución de la cage: enforcement vs monitoring  [COMPLETAR FASE 4]

Análisis transversal y **resultado central de la tesis**. Para cada escenario
discriminante, el delta de seguridad entre monitoring y enforcement cuantifica
qué previene la cage:

- **M-S2 (violaciones de frontera):** 0 en enforcement por diseño; >0 en
  monitoring donde la policy sola se sale → el delta es el número de violaciones
  evitadas, con su significación (χ²/Fisher) y tamaño de efecto.
- **M-S3 (paro de emergencia), lane-exit:** fracción de runs rescatados por la
  cage.
- **M-I4 (correlación intervención-hazard):** confirma que cada regla dispara
  *por la razón correcta* (estado hazard-compatible), validando el diseño de la
  cage, no solo su efecto.

<!-- Figura resumen: barras del delta M-S2 (monitoring − enforcement) por
escenario, con IC; y tabla de p-valores + d de Cohen. Texto: dónde la cage
aporta (edge/pert), dónde es latente (nominal), y la lectura conjunta con la
co-adaptación de §7.4 (la policy aprendió a no necesitarla en nominal, pero la
cage sigue siendo la garantía en la frontera). -->

---

## 8.7 Matriz de trazabilidad poblada  [COMPLETAR FASE 4]

Cierre de la cadena `Hazard → SR → Cage Rule → Scenario → Metric → Evidence →
Verdict` (`docs/07`). Tabla por-SR con el/los escenario(s) que lo verifican, las
métricas, los runs de evidencia y el veredicto (PASS/FAIL/condicional). El
script `tools/check_traceability.py` garantiza que no quedan SRs huérfanos a
ninguno de los dos lados.

<!-- Tabla: SR | Hazard(s) | Cage rule(s) | Scenario(s) | Metric(s) | Evidence run_id(s) | Verdict.
Es la versión "poblada con verdictos" de docs/07; aquí se reporta, en docs/07 se mantiene. -->

---

## 8.8 Discusión y amenazas a la validez

### 8.8.1 Lectura de los resultados  [COMPLETAR FASE 4]

Síntesis, con los números de §8.3–§8.6, de (i) **qué añade la cage y dónde**
—latente en nominal, protectora en la frontera— y (ii) la **relación
policy–cage**: lectura conjunta con §7.5.2–§7.5.3 (4/5 semillas aprendieron
comportamiento *constraint-respecting* y degradarían con gracia sin cage en
nominal, mientras la seed 123 quedó *cage-dependent* —una dependencia ya
**observada**, no hipotética). La curva de co-adaptación de §7.4 (la
intervención del cage decreciendo durante el entrenamiento) y el delta de §8.6
(la protección que el cage ejerce en runtime) son las dos caras de la misma
evidencia: el cage participó causalmente en *producir* la policy y la protege
*donde la policy no se basta*.

### 8.8.2 Amenazas a la validez  [BORRADOR D56]

Las fronteras del estudio se declaran de forma explícita (cf. §1.6.3),
organizadas por tipo de validez:

- **De constructo — qué se valida realmente.** La campaña valida el bloque
  `[policy + cage]` en el **espacio de estado** donde la cage está especificada,
  con estado *ground-truth*. **No valida la capa de percepción**: los escenarios
  SC-PERT-01/02 modelan el error de percepción como **ruido paramétrico inyectado
  sobre el estado** (un *proxy*, no un pipeline de visión real; §8.2.3). En
  consecuencia, las afirmaciones de seguridad se refieren al mecanismo de la cage
  *dado un estimado de estado*, no al sistema percepción-a-actuación completo. No
  obstante, los veredictos de SR se miden sobre la pose **verdadera**, por lo que
  la propiedad evaluada (no salir del carril) es físicamente significativa.
  Análogamente, el control es **lateral a velocidad fija**: la regla de velocidad
  C-04 se ejercita por perturbación inyectada (SC-EDGE-03), no por conducta
  longitudinal de la policy.

- **Interna — atribución de los efectos.** El contraste
  enforcement-vs-monitoring sobre el **mismo** controlador, semillas y condiciones
  (§8.2.2) aísla el efecto de la cage; el análisis estadístico (§8.2.5) acota su
  significación y tamaño. Las fuentes de varianza controladas son la
  estocasticidad entre semillas de la policy (mitigada con N ≥ 5) y la de la
  propia simulación.

- **Externa — generalización.** Los resultados son específicos de **una
  geometría** (óvalo R = 0.8 m) y **una plataforma** (CobraFlex 1:14). La
  generalización a otras geometrías o vehículos no se establece empíricamente; se
  argumenta por plausibilidad estructural —las reglas de la cage atacan
  invariantes geométricos del lane-following, no propiedades de una pista
  concreta—.

- **Sim-to-real.** Todo este capítulo es simulación. El gap entre Gazebo y la
  plataforma física —incluida la capa de percepción omitida aquí— se caracteriza
  en el Capítulo 9 (adaptación A5). La cage, por estar especificada sobre el
  estado abstracto e **independiente de la calidad de la policy y de la
  percepción**, es el componente del que se espera la transferencia más fiel.

---

## 8.9 Síntesis y transición al Capítulo 9  [BORRADOR D56]

Esta campaña convierte la *scenario library* en evidencia estructurada: cada SR
queda verificado (o no) contra runs logueados y reproducibles, y la contribución
de la cage queda **medida**, no postulada. Con ello se cierra la rama derecha del
V-Model en simulación.

El Capítulo 9 lleva el subconjunto físico de la library (`docs/05`, §"Subset for
physical deployment": SC-NOM-01, SC-NOM-02, SC-EDGE-01) a la plataforma
CobraFlex real, introduce la capa de **percepción** omitida deliberadamente hasta
aquí (§8.2.3), y caracteriza el gap sim-to-real (adaptación A5 del V-Model). La
cage, validada aquí como mecanismo de seguridad en espacio de estado, es el
componente que se espera que transfiera con mayor fidelidad, por ser
independiente de la calidad de la policy y de la percepción.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

F4 (campaña):
  [ ] Fijar el campaign runner + convención run_id; resumir D-29 (recuento) y
       D-30 (veto) en §8.2.4
  [ ] Resolver la decisión de métrica QED (D-17/D-21/D-22) si aplica a §8.6
  [ ] Promover los 7 stubs de escenario a YAML completos a medida que la campaña
       los alcanza (NOM-02/03, EDGE-02/03/04, PERT-01/02)
  [ ] Ejecutar grid (escenario × modo × controlador × semilla N≥5); poblar
       §8.3–§8.5
  [ ] §8.6: figura de deltas M-S2 + tabla p-valores / d de Cohen
  [ ] §8.7: poblar veredictos por-SR; sincronizar con docs/07
  [ ] §8.8.1: redactar la lectura de resultados con los números reales
       (§8.8.2 amenazas a la validez ya escrito)

Fase 6:
  [ ] Pulido de prosa; verificar coherencia cruzada con Cap.7 (§7.5/§7.6) y
       Cap.5 (Cage Specification)
-->
