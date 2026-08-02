# Prefacio

Esta tesis se presenta como Trabajo Fin de Máster del programa Automotive Systems (M.Sc.) de la Hochschule Esslingen, bajo la supervisión del Prof. Dr.-Ing. Ralf Schüler. El trabajo surge de una convicción: la adopción responsable de la inteligencia artificial en funciones de seguridad del automóvil no exige únicamente algoritmos capaces, sino un método de ingeniería que haga su comportamiento trazable, verificable y auditable. Sobre esa premisa se construyó el marco metodológico que estas páginas desarrollan y aplican a un caso concreto.

**Motivación y origen.** El proyecto nació de una pregunta que la práctica industrial plantea antes que la académica: si un componente aprendido no puede especificarse por adelantado ni verificarse contra una respuesta esperada, ¿qué queda del V-Model? La respuesta que aquí se defiende no es abandonarlo, sino modificarlo en cinco puntos concretos y comprobar si el ciclo resultante sigue siendo ejecutable de extremo a extremo.

**Alcance.** El estudio abarca desde el análisis de peligros y la derivación de requisitos hasta la campaña de validación en simulación y la caracterización del gap hacia la plataforma física, sobre un único caso de estudio deliberadamente acotado. El andamiaje de despliegue físico está construido y documentado, pero **no se ha ejecutado sobre hardware**; allí donde no hay medición, el documento lo dice en lugar de estimarlo.

**Sobre la honestidad del reporte.** Una decisión atraviesa todo el trabajo: los resultados incómodos se reportan como resultados. El veredicto global de la campaña de referencia es literalmente `NOT SATISFIED`, un requisito se cierra como no satisfecho, y el capítulo de conclusiones dedica más espacio a lo que el marco no demostró que a lo que sí. Esa elección es metodológica: un marco de trazabilidad cuyo valor consiste en no dejar afirmaciones sin evidencia perdería su sentido si se aplicara selectivamente a las favorables.

Agradezco a mi supervisor su orientación a lo largo del proyecto, así como a la Hochschule Esslingen por los medios puestos a disposición. [Espacio reservado para agradecimientos personales del autor.]
