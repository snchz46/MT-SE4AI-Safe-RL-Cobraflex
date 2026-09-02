# Capítulo 10 — Validación Operacional

Convención: las secciones marcadas [BORRADOR POST-G4] se redactaron tras el
cierre de G4 (02.07.2026); la mitad de simulación de este capítulo está completa
y **congelada** con los veredictos de G4. La columna física se declara **NO
EJECUTADA** —no «pendiente»— tras el cierre de la Fase 5 el 01.09.2026: existe
evidencia física, es de bring-up, y ningún escenario se ejecutó bajo protocolo.
Decir «pendiente» sugeriría una medición en curso que no existe. Este capítulo es argumentativo, no descriptivo: consolida la evidencia de
los capítulos 6–9 en una **declaración de validación acotada** y articula por qué
esa evidencia soporta la tesis metodológica. Los resultados detallados viven en
el Capítulo 8; aquí solo se citan.

---

## 10.1 Propósito: de resultados a declaración  [BORRADOR POST-G4]

Un conjunto de campañas no es, por sí mismo, una validación. Lo que convierte
~3200 corridas en un argumento es la cadena que va de cada Safety Requirement a
su veredicto por un camino verificable: qué escenarios lo ejercitan, qué métricas
lo miden, qué criterio decide, qué evidencia concreta (runs con metadatos de
reproducibilidad completos) respalda el número, y qué límites de validez acotan
la afirmación. Este capítulo recorre esa cadena en dirección descendente —de la
declaración global a la evidencia— y hace explícito lo que la declaración **no**
dice.

La forma de la declaración importa tanto como su contenido. Esta tesis adopta el
patrón de **veredicto literal + reconciliación anotada** (D-39/D-45/D-47): el
resultado de aplicar mecánicamente los criterios tal como estaban escritos se
registra sin edición, y toda discrepancia entre ese literal y el criterio de
satisfacción documentado del SR se analiza al lado, con identificador de
decisión. El caso paradigmático es el global del brazo de cámara (§10.3).

## 10.2 Inventario de evidencia consolidada  [BORRADOR POST-G4]

La evidencia sobre la que descansa la declaración, con su fuente canónica:

- **Campaña F4 (brazo F, estado ground-truth; congelada 10.06.2026).** 1260 runs,
  semilla principal 2024, 24 escenarios × {enforcement, monitoring} + estudio
  frontier (300 runs, D-35). Roll-up: `experiments/sim/campaign/campaign_report.json`;
  contraste frontier: `experiments/sim/campaign_frontier/frontier_contrast.json`.
- **Campaña GE4-V2 (brazo E, cámara; veredicto de registro 28.06.2026).** 1970
  runs, semilla 2024, los 28 escenarios complex_b × ambos modos, 0 errores.
  Roll-up: `experiments/sim/campaign_e_v2/campaign_report.json` + desglose por
  modos de fallo (`failure_mode_breakdown.json`). Predecesoras históricas: V1
  297k y la campaña 139k (contraste de evolución de policy).
- **Robustez multi-semilla.** N=5 en ambos brazos (brazo F: §7.5.3; brazo E:
  cerrado 13.07.2026, §7.5.3–7.5.4) con eval nominal por semilla en ambos modos.
- **Análisis fuera-de-banda.** SR-006 sobre su métrica propia
  (`tools/sr006_smoothness.py`, D-39: 559/559 enforcement vs 67.6 % monitoring);
  split in-ODD/OOD del grid de co-activación (SR-010, 30/85).
- **Verificación de la cage.** Suite de tests unitarios de reglas y pipeline
  (cap. 6), validación del estimador CV contra el oráculo de sim (GE2), y la
  matriz de trazabilidad sin huérfanos (`check_traceability.py`, PASS en G1–G4).

## 10.3 Veredicto global por brazo y su lectura  [BORRADOR POST-G4]

**Brazo F (baseline de estado): global `SATISFIED`.** Las 7 SR-CL-A pasan con
margen; M-S2 = 0 en ambos modos in-ODD (cage latente; su valor protector se mide
fuera del ODD en el contraste frontier). Sin reservas de seguridad; dos CL-B en
abstención documentada (§10.4).

**Brazo E (cámara, veredicto de registro): global `NOT SATISFIED` (literal),
bloqueado únicamente por SR-002/003.** Ambos fallan *solo* la cláusula de tiempo
de recuperación de SC-EDGE-01 (2.0 s), una sobrecapa de performance heredada del
set del óvalo que no es criterio de ningún SR; sobre sus criterios propios
(M-P4 máx = 14.4° ≤ 25°; TTLC nunca violado) ambos están **Satisfechos** (D-47).
**Ningún predicado de seguridad SR-CL-A se incumple en ninguno de los dos
brazos**: 0 contactos de borde in-ODD, M-S1 < `d_max` en enforcement, y la cage
remueve los fallos de percepción-degradada que la policy desnuda comete
(SC-PERT-13: 40/40 vs 0/40). La decisión de mantener el literal en el registro
—en lugar de re-escribir el criterio tras ver el resultado— es deliberada: el
literal documenta un defecto real (de higiene de criterios, no de seguridad) que
una edición retroactiva habría ocultado.

## 10.4 Tabla consolidada de veredictos por SR  [BORRADOR POST-G4 — columna física NO EJECUTADA]

Versión reducida de la matriz (la completa, con escenarios y métricas, en
docs/07 y el Anexo de trazabilidad). Los veredictos que cerraron **G4** están congelados;
las dos abstenciones CL-B que el gate dejó explícitamente abiertas se cerraron después,
sobre evidencia posterior y sin re-puntuar ninguna campaña histórica (D-69).

| SR | Clase | Brazo F (estado) | Brazo E (cámara; GE4-V2 y, desde 31.07.2026, la campaña 2-D 550k) | Físico |
| --- | --- | --- | --- | --- |
| SR-001 (desviación lateral) | CL-A | Satisfecho | Satisfecho (ruta-1; 28/30, 2 residuos H-12 en el borde de cuenca) | **No ejecutado** |
| SR-002 (estabilidad de heading) | CL-A | Satisfecho | Literal: fallo (cláusula 2.0 s); criterio propio: **Satisfecho** (D-47) | **No ejecutado** |
| SR-003 (TTLC predictivo) | CL-A | Satisfecho | Literal: fallo (misma cláusula); criterio propio: **Satisfecho** (D-47) | **No ejecutado** |
| SR-004 (techo de velocidad) | CL-A | Satisfecho | Satisfecho | **No ejecutado** |
| SR-005 (parada de emergencia) | CL-A | Satisfecho | Satisfecho | **No ejecutado** |
| SR-006 (suavidad de actuación) | CL-B | Satisfecho (D-39, métrica propia) | Satisfecho (out-of-band) | **No ejecutado** |
| SR-007 (validez de estado) | CL-A | Satisfecho | Satisfecho | **No ejecutado** |
| SR-008 (parada externa) | CL-A | Satisfecho | Satisfecho | **No ejecutado** |
| SR-009 (liveness) | CL-B | Abstención documentada → N/A-por-construcción en 1-D (D-49) | **Satisfecho** (fuera de banda, D-64/D-69): liveness nominal M-P6 = 0 en todos los brazos; la policy resiste ser forzada a parar; el detector marca M-P6 = 100.0 ante una parada real guionizada | **No ejecutado** (la plataforma física comanda throttle, luego el test *sería* bien-puesto allí) |
| SR-010 (composición de reglas) | CL-B | Abstención documentada (grid no inyectado) | **No satisfecho** — hallazgo CL-B no vetante (D-30/D-69): 30/85 breaches in-ODD bajo co-activación en 1-D, **16/85** en el 2-D; concentrado en C-01 ∧ C-02. Trabajo futuro T4 | **No ejecutado** |
| SR-011 (varianza de heading) | CL-B | Satisfecho | Satisfecho (métrica propia: σ_θ máx 3.0° < 5°) | **No ejecutado** |
| SR-012 (lane-keeping bajo cámara) | — | n/a (SR de track 'E') | Satisfecho (D-29 cerrado) | **No ejecutado** |
| SR-013 (degradación segura de percepción) | — | n/a | Satisfecho (SC-PERT-07 25/25 + SC-PERT-13 40/40) | **No ejecutado** |
| SR-014 (plausibilidad del estimador) | — | n/a | Satisfecho (falso-carril 25/25); residuo H-12 documentado | **No ejecutado** |

Lectura por subconjuntos: **13 de 14 SRs con veredicto Satisfecho** en al menos
un brazo sobre su criterio documentado; **1 SR `No satisfecha`** (SR-010, CL-B, no
vetante), reportada como tal y no reconciliada; **0 SRs sin veredicto, omitidos o en
TBD** en la columna de simulación — la cobertura del criterio §3.7.1(2) es del 100 %,
incluyendo los veredictos incómodos.

Las dos abstenciones que el brazo F arrastraba se cerraron el **31.07.2026** (D-69),
tras la última campaña de simulación previa al despliegue físico, y conviene subrayar
que se cerraron **en direcciones opuestas**: SR-009 hacia *Satisfecho* y SR-010 hacia
*No satisfecho*. Un TBD afirma que falta el instrumento; una vez que existe —la
metrología del stall guionizado en un caso, el grid de co-activación cableado en el
otro— mantenerlo habría sido cómodo, no honesto. La columna **Físico** queda entera en
**No ejecutado**, y desde el cierre de la Fase 5 (01.09.2026) por una razón
estrecha y precisa: la cadena de despliegue **sí se puso en marcha sobre
hardware** —el vehículo condujo 18,05 m del circuito real en un único tramo sin
activar ninguna regla de seguridad, cap. 9 §9.3.3c— pero eso es **bring-up, no
campaña**: **ninguna corrida física se ejecutó bajo el protocolo de la biblioteca
de escenarios**, en enforcement y con el contrato de percepción D-43 bajo el que
se puntuó toda campaña; todas fueron en `monitoring`, y **la cage nunca ha
modificado una acción sobre hardware**. Haber conducido no es haber puntuado:
rellenar `verdict_phys` con medidas tomadas fuera de protocolo sería inventar el
veredicto, igual que antes lo sería haberlo estimado. Las tres condiciones que
separan la columna de ser poblable no son conjeturas sino **términos medidos** del
ledger de gap (docs/17 §14): el contrato de percepción que ninguna corrida ha
usado (término 12, §9.3.5), la vía de rearme cuya espera resultó no satisfacible
conduciendo (término 9, D-74/D-80) y la exactitud del estimador dependiente del
lugar (término 2, D-79). Se declaran así, y no como trabajo pendiente, porque la
Fase 5 se cerró deliberadamente sin campaña (§9.3.4).

Dos casillas de esta tabla quedan además **matizadas** por la Fase 5, sin
re-puntuarse. **SR-004** se satisface mediante C-04, y en la configuración
física desplegada C-04 **no puede activarse sobre movimiento comandado**
(`v_max_curve_mps` 0.25 > 0.22 m/s desplegados, D-75): lo que en simulación era un
hueco de cobertura es, en la curva más cerrada del circuito real, una regla que no
protege un caso existente. Peor: la regla **sí se activó** —58 y 40 ciclos en las
dos corridas enjauladas del 31.08 que sobreviven a la auditoría—, el 100 % de las
veces sobre **artefactos de velocidad** del sensor de pose (0,25–1,30 m/s
reportados, imposibles bajo su propia potencia), y en un caso esos disparos
espurios bloquearon la vía de rearme de la regla que ellos mismos habían
levantado (docs/17 §13.5). La casilla `Satisfecho` en simulación no cambia; lo que
cambia es lo que esa casilla puede reclamar sobre el vehículo real. Y **el objeto que sostiene esta declaración no es el objeto que
conduce**: el trunk 2-D 550k no transfiere (D-71) y lo que se despliega es el
reentrenamiento v2 (D-72). Ninguna de las dos observaciones toca un veredicto de
simulación; ambas acotan su alcance, que es exactamente lo que §10.5 debe hacer.

## 10.5 Declaración de validación acotada  [BORRADOR POST-G4 — PROVISIONAL]

Con la evidencia inventariada en §10.2, esta tesis declara:

> El sistema lane-following [policy PPO + safety cage C-01..C-06], en sus dos
> instanciaciones (vector de estado y end-to-end con cámara), **satisface sus
> Safety Requirements de clase A dentro del ODD especificado, en simulación
> Gazebo**, con la evidencia trazable de ~3200 corridas de campaña y veredictos
> por SR reproducibles. La contribución de seguridad de la cage está medida
> causalmente (enforcement vs monitoring): latente donde la policy respeta las
> restricciones, decisiva bajo degradación de percepción y fuera del ODD.

Y declara con el mismo peso lo que **no** afirma:

1. **Nada fuera de Gazebo.** La validez operacional en Isaac y en la plataforma
   física no se reclama; se **caracteriza** en el Capítulo 9, y esa
   caracterización está ahora completa y cerrada (Fase 5, 01.09.2026): existe
   evidencia física de bring-up, con trece términos de gap medidos (docs/17 §14),
   y **ninguna** de ella puntuada. Los parámetros `[provisional]` de la cage
   siguen esperando calibración física; `cage.yaml` no cambió en toda la Fase 5.
2. **Nada fuera del ODD.** Los 117 contactos de borde del brazo E en enforcement
   son todos out-of-ODD (SC-FRONT-* y puntos OOD del grid); informan el estudio
   de eficacia, no el veredicto.
3. **Residuos identificados, no resueltos:** el under-read confiado del
   estimador CV (H-12, 2 breaches marginales en el borde de cuenca, mecanismo
   replicado en multi-seed), la región de co-activación SR-010 (30/85 in-ODD en
   el brazo 1-D que sostiene esta declaración; **16/85** en el brazo 2-D
   posterior — mitad de magnitud, misma naturaleza), y el
   coste en disponibilidad del conservadurismo bajo ruido severo (SC-PERT-01
   σ = 0.05; conflicto cage–CV de la semilla 23).
4. **Robustez por semilla no uniforme:** 3/5 semillas del brazo E son
   constraint-respecting; una es cage-dependent y una exhibe conflicto cage–CV.
   El veredicto de campaña se emitió sobre la semilla principal (D-36); la
   variabilidad está caracterizada, no eliminada.
5. **Esta declaración es sobre la acción 1-D.** Los veredictos declarados
   provienen de campañas con **acción 1-D** (dirección; velocidad fija). El brazo
   posterior de acción 2-D —dirección + acelerador, cap 0,22 m/s— sí produjo el
   cierre de SR-009 (cap. 8 §8.9.7) y dos campañas completas (§8.9.8–§8.9.9), y
   su resultado es **concordante**: la invariante in-ODD se sostiene (0 contactos
   de borde en enforcement) y el literal `NOT SATISFIED` se reconcilia por la
   misma cláusula heredada. Pero esa evidencia es **posterior** y no se ha
   sometido al proceso de gate, de modo que respalda la declaración sin
   ampliarla; elevarla exigiría una decisión explícita.

6. **Y la envolvente nunca ha actuado sobre el vehículo real.** Es la acotación
   que más restringe lo que esta declaración alcanza. Todas las corridas físicas
   fueron en `monitoring`, con la acción segura idéntica a la acción cruda en la
   totalidad de los ciclos registrados, de modo que el artefacto central de este
   trabajo —una cage que corrige en tiempo de ejecución— está **verificado en
   simulación y únicamente observado sobre hardware**. El marco produjo la
   evidencia que permite decir esto con precisión, que es su función; no produce,
   ni pretende, la que faltaría para decir lo contrario.

*(Sobre el re-enunciado: la columna física se declara **no ejecutada** y la
declaración **no** se re-enuncia sobre ella — la Fase 5 cerró sin campaña. La
incorporación formal del brazo 2-D al proceso de gate sigue siendo una decisión
post-veredicto no tomada, y es una decisión de autoría, no de evidencia.)*

## 10.6 De la declaración a la tesis metodológica  [BORRADOR POST-G4]

El valor demostrativo de este capítulo no es que el sistema "funcione", sino que
cada celda de §10.4 es **auditable**: un evaluador puede tomar cualquier
veredicto, seguir su fila en la matriz hasta los runs concretos, verificar los
hashes y recomputar el criterio. Esa auditabilidad —imposible sin las
adaptaciones A2 (cage spec separada), A4 (trazabilidad como restricción dura) y
la disciplina de agregación D-29/D-30/D-38— es el producto que el V-Model
clásico no genera para componentes aprendidos, y constituye la evidencia
central de la hipótesis H3. La evaluación crítica del marco (¿a qué coste?, ¿con
qué límites?) corresponde al Capítulo 11.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: ACTUALIZADO 02.09.2026. Mitad sim completa y congelada. La columna física
se declara NO EJECUTADA tras el cierre de la Fase 5 (01.09.2026) y §10.5 gana la
acotación 6 (la cage nunca actuó sobre hardware) en lugar de re-enunciarse.

  [x] Columna "Físico" de §10.4: resuelta como **No ejecutado** (02.09.2026), no
       como poblada. §10.5 acotado, no re-enunciado.
  [ ] Decidir presentación: ¿la tabla §10.4 absorbe la de ch.8 §8.7 o la resume?
       (evitar duplicación en Fase 6).
  [ ] Verificar al pulir: enunciados cortos de los SR contra docs/03 (aquí van
       parafraseados); 30/85 y 559/559 contra los reportes.
  [ ] El plan de Fase 6 sitúa aquí también la argumentación "contribución SE4AI"
       — hoy está repartida entre §10.6 y el cap. 11; decidir reparto final.
  [ ] Anexo: matriz completa (tools/traceability_matrix.csv) + procedencia.
-->
