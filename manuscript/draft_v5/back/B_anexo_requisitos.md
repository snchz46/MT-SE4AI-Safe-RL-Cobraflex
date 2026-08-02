# Anexo B — Especificación de requisitos de seguridad y *rationale*

Versión completa de la tabla 4.2, con umbrales y trazabilidad, seguida del *rationale*
requisito por requisito: de dónde sale cada umbral, qué lo hace falsable y cuál es su estado
de calibración.

| ID | Enunciado abreviado | Parámetros principales | H cubiertos | Cage rule | Criticidad | Verificación |
| -- | ------------------- | ---------------------- | ----------- | --------- | ---------- | ------------ |
| SR-001 | El offset lateral absoluto respecto al centro de la calzada se mantendrá por debajo de `d_max` durante operación dentro del ODD aplicable. | `d_max = 0.16 m` | H-01 | C-01 | SR-CL-A | SC-NOM-01, SC-NOM-02, SC-EDGE-02 |
| SR-002 | El error de orientación absoluto respecto a la dirección del carril se mantendrá por debajo de `θ_max`. | `θ_max = 0.44 rad (25°)` | H-02 | C-02 | SR-CL-A | SC-EDGE-01, SC-EDGE-04 |
| SR-003 | El tiempo a salida de carril proyectado (TTLC) se mantendrá por encima de `t_min`; el percentil 5 de TTLC sobre runs nominales será ≥ 0.5 s. | `t_min = 1.0 s`; floor p5 = 0.5 s | H-01, H-02 (parcial) | C-03 | SR-CL-A | SC-NOM-02, SC-EDGE-01 |
| SR-004 | La velocidad longitudinal no excederá `v_max(κ)`, techo dependiente de la curvatura local κ. | `v_max_straight = 0.5 m/s`; `v_max_curve = 0.25 m/s` | H-03 | C-04 | SR-CL-A | SC-NOM-02, SC-EDGE-03 |
| SR-005 | Bajo trigger compuesto sobre heading y offset durante `Δt_max`, el sistema transitará a modo emergencia con desaceleración mínima y steering frozen. | `θ_warn = 20°`; `d_warn = 0.12 m`; `Δt_max = 0.2 s`; `a_min = 0.3 m/s²` (provisional, sujeto a M-3) | H-04, H-07 (parcial) | C-05 | SR-CL-A | SC-EDGE-04 |
| SR-006 | La variación de comando entre dos ciclos consecutivos se mantendrá por debajo de `δ_max` para steering y throttle. | `δ_max_steer = 0.15`; `δ_max_thr = 0.10` (por ciclo) | H-05 | C-06 | SR-CL-B | Todos los escenarios (rate limiter activo) |
| SR-007 | La cage activará modo emergencia si la observación tiene antigüedad mayor a `staleness_max` o cualquier campo fuera de rango plausible. | `staleness_max = 200 ms`; `N_missing_max = 5 ciclos` | H-06 | parte de C-05 | SR-CL-A | SC-PERT-02 |
| SR-008 | Bajo señal externa de stop o cierre controlado de episodio, el sistema desacelerará a 0 m/s en `t_stop_max` sin exceder `d_max` lateral. | `t_stop_max = 1.7 s`; `d_max = 0.16 m` | H-07 | parte de C-05 + nodo vehicle-control | SR-CL-A | SC-NOM-03, SC-EDGE-04 |
| SR-009 | En toda ventana elegible de `t_window`, el vehículo acumulará al menos `Δs_min` de progreso longitudinal nominal; la métrica M-S2 bajo monitoring-mode no exhibirá elevación sostenida frente al baseline. | `Δs_min = 0.10 m`; `t_window = 2.0 s`; `Δt_settle = 1.0 s` | H-08 | training (D-25) | SR-CL-B | SC-NOM-01..03, SC-PERT-03 |
| SR-010 | Cuando dos o más cage rules activen en el mismo ciclo, el comando final satisfará la envolvente segura de toda regla activada y el patrón inter-ciclo no exhibirá oscilación sostenida a más de `f_osc_max`. | `f_osc_max = 5 Hz`; joint-envelope assertion | H-09 | arbiter (D-25) | SR-CL-B | SC-EDGE-04, SC-EDGE-05 |
| SR-011 | La desviación estándar del error de heading sobre ventanas elegibles de `t_psd` se mantendrá por debajo de `σ_θ_max`, cubriendo la rama in-band de H-02 que SR-002 no acota. | `σ_θ_max = 5°`; `t_psd = 1.0 s` | H-02 (rama oscilatoria) | C-06 + training | SR-CL-B | SC-EDGE-01, SC-EDGE-04 |
| SR-012 | (Track 'E') El lane-keeping se mantendrá dentro de la envolvente SR-001/SR-002 bajo entrada visual degradada (glare, exposición, motion blur, contraste, sombra). | `d_max = 0.16 m`; `θ_max = 25°` (reutilizados); envolvente visual provisional (docs/09) | H-10 | C-01, C-02, C-03 + training | SR-CL-A | SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10 |
| SR-013 | (Track 'E') Ante pérdida de percepción válida (oclusión/ausencia de features/frames obsoletos o caídos), el sistema entrará en parada controlada open-loop vía C-05 sin exceder `d_max`. | `perc_staleness_max = 200 ms` (provisional); `d_max = 0.16 m` | H-11 | parte de C-05 (salud del estimador CV del cage) | SR-CL-A | SC-PERT-07 |
| SR-014 | (Track 'E') El cage no impondrá sus reglas sobre una estimación de carril que falle la verificación de plausibilidad/consistencia temporal; en su lugar entrará en parada controlada (C-05). | `plaus_tol`, `Δt_plaus` (provisionales, vs oráculo ground-truth) | H-12 | parte de C-05 (check de plausibilidad → parada) | SR-CL-A | SC-PERT-08, SC-PERT-04..06, SC-PERT-09, SC-PERT-10 |

## Rationale por requisito

El rationale completo para cada SR —incluyendo justificación física del
umbral citando los parámetros del ODD, descripción de la forma
falsable, identificación del experimento de verificación, y referencia
cruzada al hazard del que deriva— vive en `docs/03_safety_requirements.md`.
A modo de ilustración del nivel de detalle exigido, esta subsección
presenta el rationale completo de SR-001 como ejemplo representativo;
el resto se sintetiza brevemente al final de la subsección y se cita
por referencia.

El rationale de SR-001 es el siguiente. El parámetro
`d_max = 0.16 m` no se elige en función del rendimiento de la policy
sino del envelope geométrico del ODD: la calzada tiene anchura total
`ODD-1.ROAD_WIDTH = 0.50 m`, lo que sitúa el borde físico del corredor
transitable a `0.25 m` del eje longitudinal de la pista. Un margen de
seguridad agregado de `Δ = 0.09 m` absorbe tres contribuciones
independientes: el ruido lateral del estimador de estado
(`≈ 0.01 m`), la deriva máxima esperable por latencia de control
nominal (`v_max · LATENCY_NOMINAL = 0.5 m/s · 50 ms = 0.025 m`), y la
mitad de la huella física lateral del CobraFlex 1:14 (`≈ 0.05 m`). El
umbral falsable queda entonces en `d_max = ROAD_WIDTH/2 − Δ = 0.25 − 0.09 = 0.16 m`,
interpretado como el módulo del offset lateral del centro geométrico
del vehículo respecto al eje del corredor transitable. Esta convención
de signo y unidad queda fijada en el enunciado de SR-001 en
`docs/03_safety_requirements.md` y se cita por los SRs derivados
(SR-005 sobre `d_warning = 0.12 m < d_max` como umbral de aviso
temprano, SR-008 sobre permanencia bajo `d_max` durante la parada
controlada).

El rationale resumido del resto de los SRs se describe a continuación
con remisión al artefacto autónomo para los detalles. **SR-002**
(`θ_max = 25°`) se justifica mediante un cálculo bicycle-model de
recuperabilidad con wheelbase 0.15 m, steering saturado de 0.5 rad,
velocidad nominal 0.3 m/s y tiempo de respuesta de la cage de 0.05 s;
el valor cae dentro del envelope recuperable con margen aproximado de
factor dos. **SR-003** (`t_min = 1.0 s`) se descompone en 0.3 s de
margen para la cage (defensible por física cinemática) y 0.7 s de
margen para la policy (marcado como provisional, sujeto a revisión
tras prototipo de entrenamiento en F3). **SR-004** define un techo
de velocidad dependiente de la curvatura, anclado en `ODD-1.V_MAX = 0.5 m/s`
para tramos rectos y reducido a 0.25 m/s en curva; el coeficiente de
interpolación `k_κ = 0.3` se elige para que la curva caiga
exactamente a la curvatura máxima esperada del mapa `odd3_curvy_loop`
(pendiente de cierre con TBD-Q9). **SR-005** introduce un trigger
compuesto con persistencia `Δt_max = 0.2 s` (cuatro ciclos de control,
necesarios para distinguir un estado compuesto genuino de un glitch
transitorio); la `a_min = 0.3 m/s²` es provisional pendiente de la
medición M-3 sobre la plataforma. **SR-006** fija un limitador de
rate como defensa conservadora frente a actuación abrupta;
los valores `δ_max_steer = 0.15` y `δ_max_thr = 0.10` son
defaults que requieren cross-check empírico contra el envelope
mecánico del actuador (medición M-5) y contra el percentil 95 del
delta natural de la policy entrenada (tras prototipo F3). **SR-007**
preserva un horizonte de antigüedad `staleness_max = 200 ms` (cuatro
ciclos de control) complementado con un contador de mensajes
faltantes `N_missing_max = 5`, ambos valores conservadores frente a
las propiedades nominales del bus ROS2; los rangos plausibles por
campo del estado se mantienen deliberadamente más amplios que el
envelope operativo de cada variable para que las violaciones de
rango sean indicadores no ambiguos de fallo de sensor. **SR-008**
fija `t_stop_max = 1.7 s`, consistente con `v_max_straight / a_min ≈ 1.67 s`
de SR-005 más un margen de granularidad y latencia; la consolidación
de la inconsistencia previa con SR-005 (1.5 s en el baseline F0) se
registra en `docs/CHANGELOG.md`. **SR-009** acota inferiormente el
progreso longitudinal: `Δs_min = 0.10 m` deriva del producto entre la
velocidad operativa mínima útil (`v_min ≈ 0.05 m/s`) y una ventana
deslizante de `t_window = 2.0 s`; el carve-out de `Δt_settle = 1.0 s`
tras transiciones desde modo emergencia o stop controlado evita que
SR-009 entre en conflicto con SR-005 o SR-008 durante la rampa de
re-arranque (cf. §SR-009 del SRS para el orden de prioridad
explícito). Su implementación es training (D-25): la cage no inyecta
progreso, solo observa el stall mediante M-P6 y emite señal hacia el
test harness. **SR-010** asegura la consistencia composicional de la
cage: la *joint-envelope assertion* al final de cada ciclo
verifica que el comando emitido satisface las precondiciones de toda
regla activa en ese ciclo, y un monitor inter-ciclo acota la
oscilación entre correcciones contradictorias por debajo de
`f_osc_max = 5 Hz`. La implementación es una propiedad estructural
del pipeline de la cage (`arbiter`, D-25), no una regla numerada
adicional; el fallo de la asertión hace caer el sistema en C-05
(modo emergencia) como mitigación de última línea. **SR-011** cierra
la rama oscilatoria de H-02 que el umbral magnitud-puro de SR-002 no
acota: `σ_θ_max = 5°` admite oscilaciones hasta amplitud ≈ 7° con
suficiente margen frente a `θ_max = 25°` pero tensa lo suficiente
como para detectar el modo within-bounds-but-oscillatory; la ventana
`t_psd = 1.0 s` captura al menos un período de la oscilación
significativa (≈ 1 Hz) sin diluirse en derivas de timescale mayor.
La implementación es híbrida (`C-06 + training`): C-06 atenúa
contenido de alta frecuencia en los comandos del policy, y un
término de varianza de heading en el reward incentiva al policy a no
oscilar en estado estacionario.

---
