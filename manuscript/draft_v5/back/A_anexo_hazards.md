# Anexo A — Registro de peligros (versión extendida)

Versión completa del registro resumido en la Tabla 4.1. Cada entrada conserva su
clasificación de severidad (S), exposición (E) y controlabilidad (C), los dominios
operacionales en que aplica, el consecuente operacional principal y la hipótesis de causa
raíz dominante. La numeración es estable y no reutilizable: un identificador retirado no
vuelve a asignarse.

| ID | Hazard (descripción) | S | E | C | Criticidad | ODDs aplicables | Consecuente operacional principal | Hipótesis de causa raíz dominante |
| -- | -------------------- | - | - | - | ---------- | --------------- | --------------------------------- | --------------------------------- |
| H-01 | Salida lateral involuntaria del carril durante operación nominal o adversa. | S3 | E3 | C2 | High | 1, 2, 3, 4 | Contacto con borde de pista o salida del corredor transitable. | Acción de control incorrecta en presencia de error lateral elevado. |
| H-02 | Error de orientación divergente u oscilatorio respecto a la trayectoria del carril. | S2 | E3 | C2 | Medium-High | 1, 2, 3, 4 | Trayectoria oscilante o pérdida progresiva de centrado. | Acción correctiva insuficiente u oscilante en heading error. |
| H-03 | Velocidad longitudinal excesiva para la curvatura o visibilidad locales (worst case: curva cerrada). | S3 (conservador, worst case en curva) | E2 | C1 | Medium-High | 3, 4 | Insuficiente distancia de frenado; salida tangencial en curva. | Reward que prioriza progreso sin penalización por curvatura. |
| H-04 | Estado compuesto irrecuperable (heading + offset + velocidad simultáneamente elevados). | S3 | E1 | C3 | High | 1, 2, 3, 4 | Salida del carril de alta energía; pérdida de pose funcional. | Perturbaciones acumuladas no vistas en entrenamiento. |
| H-05 | Comando de actuación excesivamente abrupto entre dos ciclos de control consecutivos. | S1 | E3 | C1 | Medium | 1, 2, 3, 4 | Inestabilidad mecánica menor; desgaste; ruido propagado a la estimación del estado. | Ausencia de regularización del action delta durante entrenamiento. |
| H-06 | Operación sobre estado no observable o corrupto (latencia excesiva, datos obsoletos, ruido fuera de rango). | S3 | E2 (dominada por despliegue físico) | C2 | High | 2, 4 | Decisión basada en información inválida; pérdida de coherencia. | Mensaje ROS2 perdido, sensor en fallo, desincronización temporal. |
| H-07 | Imposibilidad de realizar una parada controlada cuando las condiciones la requieren. | S3 | E1 | C1 | High | 1, 2, 3, 4 | Continuación de movimiento sin base de control; impacto al final. | Ausencia de mecanismo de stop; policy no entrenada para frenar. |
| H-08 | Stall por explotación del reward: la policy converge a inacción o a una dirección adversa que acumula más reward que el lane-following nominal. | S2 | E3 | C2 | Medium-High | 1, 2, 3, 4 | Vehículo detenido o derivando sistemáticamente fuera de la trayectoria segura; episodio no progresa. | Especificación de reward desalineada durante entrenamiento; horizonte o factor de descuento que premia inacción. |
| H-09 | Conflicto entre cage rules: dos o más reglas activas en el mismo ciclo producen un comando combinado fuera de la envolvente segura, o una oscilación entre correcciones contradictorias. | S3 (hereda del hazard más severo cuya envolvente se rompa) | E1 | C2 | Medium | 1, 2, 3, 4 | La cage deja de ser garantía y se vuelve fuente de mandos inseguros. | Reglas diseñadas en aislamiento sin arbitraje explícito; acoplamiento de estado entre C-04/C-06/C-03; emergencia activándose durante cascada. |
| H-10 | (Track 'E') Mala percepción de carril por entrada visual degradada (glare, exposición, motion blur, bajo contraste, sombras). | S3 | E3 | C2 | High | 1, 2, 3, 4 | Acción sobre un carril mal leído; deriva lateral / error de heading que escala a H-01/H-02. | Iluminación fuera de la distribución de entrenamiento; blur de movimiento; reflejos/sombras. |
| H-11 | (Track 'E') Pérdida de percepción de carril válida (oclusión, ausencia de features, caída/latencia de cámara); ciega a policy y cage (causa común, D-43). | S3 | E2 | C2 | High | 1, 2, 3, 4 | Comandos arbitrarios sobre percepción ciega; sin fallback, trayectoria indefinida. | Oclusión; features ausentes; dropout/freeze de cámara; wash-out extremo. |
| H-12 | (Track 'E') Mala detección del cage: el detector CV del cage produce un carril falso plausible y la cage impone una envolvente errónea. | S3 | E2 | C2 | High | 1, 2, 3, 4 | La cage deja de ser garantía y puede sacar al vehículo del carril verdadero. | Marcas engañosas (bifurcaciones, pintura antigua); sombras/reflejos como bordes; visión degradada que corrompe la detección. |

**Nota sobre tres reclasificaciones.** Durante la auditoría del registro se normalizaron
tres valoraciones inicialmente ambiguas. H-03 pasó de una severidad partida —no admitida por
la norma— a un único valor conservador sobre el peor caso en curva. H-05 bajó de S2 a S1
para alinearse con la convención de vehículo real: la actuación abrupta es primariamente un
peligro de confort y desgaste, no de lesión. Y H-06 consolidó su exposición en un único
valor dominado por el despliegue físico. Las tres quedan registradas porque una
reclasificación silenciosa de severidad es indistinguible de un ajuste a conveniencia.
