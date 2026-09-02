# Capítulo 11 — Discusión

Convención: las secciones marcadas [BORRADOR POST-G4] se redactaron tras el
cierre de G4 (02.07.2026) y **se han actualizado con la evidencia de Fase 5**,
cerrada el 01.09.2026. La marca se conserva porque señala la procedencia del
texto, no una carencia: la evidencia física existe, está incorporada, y es
**posterior** —no re-puntúa ninguna puerta— de modo que la evaluación del marco
que sigue ya no es provisional a la espera de datos, sino acotada por lo que esos
datos pueden sostener. Este capítulo evalúa el **marco**, no el sistema: la
pregunta es si el V-Model adaptado resultó útil para producir el sistema, no si
el sistema resultó útil (§3.7).

---

## 11.1 Propósito y método de esta discusión  [BORRADOR POST-G4]

El Capítulo 3 fijó por adelantado (§3.7.1) cinco criterios meta con indicadores
medibles, precisamente para que esta evaluación no degenerara en
autocomplacencia retrospectiva. Este capítulo los recorre uno a uno con la
evidencia registrada (§11.2), evalúa las tres hipótesis de §1.3 (§11.3), destila
las lecciones aprendidas que no estaban en el diseño original (§11.4), compara
con las prácticas alternativas que el marco desplaza (§11.5), y cierra con
limitaciones y riesgos residuales (§11.6–11.7). El registro primario para todo
ello es `DECISIONS.md` (**74 entradas, numeradas hasta D-80**) y el CHANGELOG: la disciplina de anotar
decisiones y costes *cuando ocurrían* es lo que permite que esta sección cite en
lugar de recordar.

## 11.2 El marco contra sus cinco criterios (§3.7.1)  [BORRADOR POST-G4 · actualizado con Fase 5]

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

Un tercer emergente merece mención aparte porque el registro **no** lo contempla
en ninguna forma: la **dependencia de una regla CL-B** —C-06, el limitador de
tasa— para el propio mantenimiento del carril (docs/04, hallazgo 4). El registro
contempla que la cage falle, arbitre mal o lea mal; no contempla que la policy se
adapte a la cage hasta necesitarla para conducir. Es un modo de fallo del
*acoplamiento* entre componente aprendido y envolvente, y sugiere una categoría de
hazard que el análisis inicial no tenía.

**El peldaño físico somete este criterio a una prueba más dura que la simulación,
y el resultado se matiza en consecuencia (Fase 5, D-70…D-80).** Sobre hardware los
fallos observados caen en dos grupos con valor distinto para juzgar el criterio.
El primero son manifestaciones **dentro** de familias ya registradas pero no
descritas por ellas: H-12 contempla que el estimador de la cage lea mal con
confianza, pero no que su exactitud sea una **propiedad del lugar del circuito**
—96.7 % de emparejamiento y 7.2 mm de error en el inicio de la recta, frente a
sesgos de ±40 mm *confiadamente* reportados y colapsos al 0 % en puntos concretos
(D-79)— que es como se manifestó. Que la familia estuviera anticipada es lo que
permitió absorberla; que su forma no lo estuviera es lo que obligó a medirla con
una captura de posición verdadera antes de poder actuar sobre ella. El segundo
grupo **no es de hazards en absoluto**, y ahí el criterio no aplica más que por
omisión: reglas correctas frente a su especificación cuyo *comportamiento
operacional* no está definido (C-05 enclava correctamente y deja el vehículo
detenido para siempre, D-74) y umbrales que no pueden activarse en la
configuración desplegada (C-04, `v_max_curve_mps` 0.25 > los 0.22 m/s
desplegados, D-75). Un registro de hazards pregunta qué puede salir mal; no
pregunta qué ocurre después, ni si el punto de operación alcanza la envolvente
que se especificó.

La lectura honesta del criterio es por tanto **cumplida en simulación y
parcialmente interrogada sobre hardware**: ninguna manifestación física exigió una
familia de hazard nueva, pero varias exigieron una descripción nueva, y la clase
más incómoda —el hueco entre especificación y operación— cae fuera del
instrumento. El cap. 9 §9.5 lo cuantifica desde el otro lado, con una asimetría
que conviene no suavizar: la lista de *gaps* escrita antes de tocar hardware
(docs/17 §5) acertó los términos que un simulador sabe representar y **no contiene
ninguno de los que efectivamente detuvieron al vehículo** (docs/17 §14.1).

**(4) Coste de adopción — criterio: proporcional al beneficio.** Cumplido, con la
cuantificación fina declarada fuera de alcance. El registro contiene **74
decisiones numeradas hasta D-80**, el validador, las plantillas y los documentos
vivos 00–17 mantenidos al día de los resultados por una sola persona *mientras*
se ejecutaban dos pistas de entrenamiento, varias campañas de evaluación, un
puente entre simuladores y un despliegue físico. La cifra de reparto exacto
marco-vs-técnica no se midió en horas (límite declarado en §3.7.2); el proxy
registrado es que ningún gate se retrasó por artefactos del marco, y sí hubo
retrasos por causas técnicas (colapsos de entrenamiento, calibraciones Isaac, y
en Fase 5 tres sesiones de pista que no alcanzaron su objetivo). La Fase 5 añade
un dato favorable al criterio y otro desfavorable: el marco **absorbió** una fase
entera de evidencia posterior sin que ninguna de sus estructuras —hazards, SRs,
reglas, escenarios, métricas— tuviera que modificarse ni re-puntuarse; y a cambio
`CLAUDE.md`, el fichero de estado, creció muy por encima de su propio presupuesto
declarado, que es el coste documental haciéndose visible.

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

## 11.3 Las hipótesis H1–H3  [BORRADOR POST-G4 · actualizado con Fase 5]

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

**H3 (de utilidad) — soportada, con una precisión importante.** El marco produjo
veredictos fundamentados con límites de validez declarados (§10.5), incluyendo
la capacidad —que era el test real— de emitir veredictos **incómodos** sin
romperse: el literal negativo, las abstenciones, los residuos H-12/SR-010. La
precisión es que el veredicto es incómodo; un lector podría leerlo como fracaso
del sistema y sería un error de nivel, porque la hipótesis versa sobre la
capacidad del marco de producir un juicio trazable y no sobre el signo de ese
juicio.

La mitad física de H3 —*¿sobrevive la cadena de evidencia al hardware?*— **se
ejecutó y tiene respuesta, aunque no la que se buscaba**. La cadena sobrevivió: cada
medida física entró al registro con su decisión (D-70…D-80), su procedencia por
corrida y su etiqueta de clase (calibración/estructural = resultado; conducción =
preliminar, N=1, sin puntuar), y **tres afirmaciones fueron retiradas por el
propio mecanismo** cuando la evidencia las falsó —la sub-lectura de M-7 §4 al
rectificar, el brazo bare-policy completo por contaminación del operador, y el
literal «C-04 no puede dispararse nunca»—. Lo que **no** se produjo es un
`verdict_phys`: ningún escenario se ejecutó bajo protocolo, todas las corridas
fueron en monitorización y la cage nunca ha modificado una acción sobre hardware.
De modo que H3 queda soportada en la producción de evidencia trazable, y
explícitamente **no** en la extensión del veredicto a la plataforma real.

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
7. **Una medida tomada en un punto no caracteriza una envolvente de operación.**
   Es la lección que el peldaño físico impuso con más insistencia y la más fácil
   de repetir para quien venga después. La calibración de cámara (M-6), la
   comprobación de `ey` contra cinta (M-7 §4) y todos los `lanecheck` previos al
   despliegue se tomaron con el vehículo detenido **en el mismo lugar** del
   circuito, por la razón práctica de que era el lugar cómodo; la captura sobre
   el trazado completo reveló que ese punto es **el mejor del circuito para el
   estimador** (D-79), y con ello que tres conclusiones de pose única no
   generalizaban. El contenido de aquellas medidas se mantuvo; lo que se retiró
   fue su alcance. Corolario operativo: **una puerta de aceptación basada en
   dispersión no puede detectar un sesgo estable** —`sd_ey ≤ 10 mm` aprobó una
   lectura con 43.3 mm de recorrido y otra con −39.7 mm de sesgo a sd 3.1 mm—,
   de modo que el protocolo de una medida debe cubrir el dominio sobre el que se
   va a afirmar algo.
8. **La envolvente puede moldear al componente que contiene.** Al entrenar con la
   cage en la cadena de actuación, lo que se optimiza es **la pareja**, no la
   policy: la policy 2-D del veredicto satura C-06 en el 77.5 % de los pasos y,
   sin cage, abandona el carril en 17 de 25 corridas de resistencia (docs/04,
   hallazgo 4). La contención en tiempo de ejecución no es un filtro neutro sobre
   un componente dado; es parte del sistema que el componente aprende a habitar.
   La dependencia está **medida**; su origen —co-adaptación al limitador dentro
   del bucle— está **inferido**, y la ablación que lo probaría no se ejecutó.

## 11.5 Comparación con prácticas alternativas  [BORRADOR POST-G4 — ampliar en pulido final]

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

La Fase 5 **no levanta** ninguna de esas limitaciones y precisa la principal. Los
veredictos siguen siendo solo-Gazebo: existe evidencia física, pero es de
**bring-up y no está puntuada** —ningún escenario se ejecutó bajo protocolo,
todas las corridas fueron en `monitoring`, y **la cage nunca ha modificado una
acción sobre hardware**—, de modo que el enunciado correcto de la limitación pasó
de «no hay evidencia física» a «la evidencia física existe y no está puntuada».
Se añaden tres límites propios del peldaño: la evidencia física es **N=1 por
configuración** y sin repetición; el objeto que condujo **no es** el objeto
validado (el trunk 550k no transfiere, D-71; conduce el reentrenamiento v2,
D-72); y ninguna corrida física usó el contrato de percepción D-43 bajo el que se
puntuaron las campañas (todo lo que condujo usó `near_secant`, docs/17 §14
término 12).

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
- **Parámetros no medibles en sim** — `ODD-3.A_LAT_MAX` (TBD-Q10) queda abierto
  por construcción (D-33): es una dependencia de hardware, no una acción
  pendiente, y M-4 no se ejecutó antes del cierre de la Fase 5.

Los que la Fase 5 **añadió**, todos posteriores y ninguno re-puntuando nada
(docs/17 §14):

- **La exactitud del estimador depende del lugar** (D-79) — sesgos de ±40 mm
  *confiadamente* reportados y colapsos de emparejamiento al 0 % en puntos
  concretos del circuito, con el mecanismo localizado en la **generación de
  candidatas** y no en la selección del par. Es el riesgo que ordena el resto:
  D-76 fija ensanchar el estimador antes de restringir la policy. Mitigación: T3.
- **Reglas correctas sin comportamiento operacional definido** — C-05 enclava por
  especificación y deja detenido indefinidamente a un vehículo que debe seguir
  operando; la vía de rearme vive **fuera** de la cage por decisión (D-74) y su
  espera de 1 s resultó **no satisfacible conduciendo** (48 % de 623 retenciones).
  `cage.yaml` no se tocó. Mitigación: T2/T3.
- **Umbral inactivable, y activándose por artefacto** — C-04 no puede dispararse
  sobre movimiento comandado al cap desplegado (0.25 > 0.22 m/s, D-75) y sin
  embargo se disparó 58 y 40 ciclos sobre **artefactos de velocidad** del ZED, en
  un caso bloqueando el rearme de la regla que él mismo había levantado. Un modo
  de fallo de sensor que entra directo en la única entrada de velocidad de la
  cage.
- **La cage nunca ha actuado sobre el vehículo real** — el riesgo residual que más
  acota lo que este trabajo puede reclamar. El artefacto central se ha verificado
  en simulación y únicamente **observado** sobre hardware.

## 11.8 Síntesis y transición al Capítulo 12  [BORRADOR POST-G4]

La evaluación del marco es favorable en sus cinco criterios, con tres matices
honestos: el coste de adopción está registrado pero no cuantificado en horas; la
trazabilidad garantiza referencia pero no ejecución (el hueco SC-EDGE-05); y el
criterio (3) —anticipación de hazards— queda **cumplido en simulación y solo
parcialmente interrogado sobre hardware**, porque la clase de fallo que más costó
en Fase 5, el hueco entre especificación y operación, cae fuera de lo que un
registro de hazards pregunta. Las hipótesis H1–H2 quedan soportadas y H3 también,
en la producción de evidencia trazable y explícitamente **no** en la extensión del
veredicto a la plataforma real. Los riesgos residuales están identificados,
acotados y con línea de mitigación asignada. El Capítulo 12 condensa los hallazgos
y convierte estas mitigaciones en el programa de trabajo futuro.

---

<!--
APÉNDICE INTERNO — TRABAJO PENDIENTE EN ESTE CAPÍTULO

Estado: ACTUALIZADO 02.09.2026 con la evidencia de Fase 5 (cerrada 01.09.2026).
§11.2(3), §11.2(4), §11.3 (H3), §11.4 (lecciones 7-8), §11.6 y §11.7 incorporan el
peldaño físico. El registro de coste sigue sin cuantificarse en horas — límite
declarado de antemano en §3.7.2, no una tarea pendiente.

  [x] Re-emitir §11.2(4) coste de adopción con el registro Fase 5 (02.09.2026);
       la tabla decisiones-por-fase como proxy cuantitativo sigue sin hacerse y es
       opcional.
  [ ] §11.5: desarrollar la comparación con referencias concretas del cap. 2
       (Kuutti safety cages, safe-RL surveys, UL 4600/Koopman) en Fase 6.
  [x] Contrastar §11.2(3) con lo que emergió en físico (02.09.2026): **ninguna
       familia de hazard nueva**, pero varias manifestaciones exigieron descripción
       nueva, y la clase más incómoda (especificación vs operación) cae fuera del
       instrumento. La sección efectivamente lo absorbió sin cambiar de forma.
  [ ] Decidir reparto final §10.6 vs §11.2 (argumento SE4AI) en Fase 6.
  [ ] La mejora del marco identificada en §11.2(5) (validar *ejecución* además
       de *referencia*) podría formalizarse como propuesta en cap. 12 T7 — hoy
       está implícita en T7(a); decidir si se nombra como sexta adaptación
       candidata o como refinamiento de A4.
-->
