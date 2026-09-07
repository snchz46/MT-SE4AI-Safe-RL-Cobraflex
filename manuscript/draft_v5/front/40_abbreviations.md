# Lista de abreviaturas y símbolos

| Abreviatura | Significado |
| --- | --- |
| ADAS | Advanced Driver-Assistance System (sistema avanzado de asistencia a la conducción) |
| AI / IA | Artificial Intelligence / Inteligencia Artificial |
| AMLAS | Assurance of Machine Learning for Autonomous Systems (garantía de aprendizaje automático para sistemas autónomos) |
| ASIL | Automotive Safety Integrity Level (nivel de integridad de seguridad automotriz) |
| CMDP | Constrained Markov Decision Process (proceso de decisión de Markov con restricciones) |
| CNN | Convolutional Neural Network (red neuronal convolucional) |
| CV | Computer Vision (visión por computador) |
| DR | Domain Randomization (aleatorización de dominio) |
| DRL | Deep Reinforcement Learning (aprendizaje por refuerzo profundo) |
| ESC | Electronic Speed Controller (variador electrónico de velocidad) |
| GSN | Goal Structuring Notation (notación de estructuración de objetivos) |
| HARA | Hazard Analysis and Risk Assessment (análisis de peligros y evaluación de riesgo) |
| IMU | Inertial Measurement Unit (unidad de medida inercial) |
| KL | Kullback–Leibler (divergencia entre distribuciones) |
| MBSE | Model-Based Systems Engineering (ingeniería de sistemas basada en modelos) |
| MDP | Markov Decision Process (proceso de decisión de Markov) |
| ML | Machine Learning (aprendizaje automático) |
| MPC | Model Predictive Control (control predictivo por modelo) |
| ODD | Operational Design Domain (dominio operacional de diseño) |
| PD | Proportional-Derivative (controlador proporcional-derivativo) |
| PPO | Proximal Policy Optimization |
| RC | Radio-Controlled (radiocontrolado) |
| RL | Reinforcement Learning (aprendizaje por refuerzo) |
| ROS2 | Robot Operating System 2 |
| RTX / PhysX | Motores de renderizado y física de NVIDIA (Isaac Sim) |
| SAC | Soft Actor-Critic |
| SAE | SAE International (organismo de normalización; niveles J3016) |
| SB3 | Stable-Baselines3 (biblioteca de algoritmos de RL) |
| SBC | Single-Board Computer (computador de placa única) |
| SE4AI | Systems Engineering for Artificial Intelligence |
| SOTIF | Safety of the Intended Functionality (ISO 21448) |
| SR | Safety Requirement (requisito de seguridad) |
| SRS | Safety Requirements Specification (especificación de requisitos de seguridad) |
| STPA | System-Theoretic Process Analysis |
| TTLC | Time-To-Lane-Crossing (tiempo hasta el cruce de carril) |
| V&V | Verificación y Validación |

**Identificadores del marco.** El trabajo usa un espacio de identificadores único y no reutilizable, resumido aquí; los registros correspondientes son los Anexos A (peligros), B (requisitos), E (cage) y F (trazabilidad): `H-XX` (peligro), `SR-XXX` (requisito de seguridad), `SR-CL-A` / `SR-CL-B` (clase de criticidad del requisito), `C-XX` (regla de la cage), `SC-*` (escenario), `M-*` (métrica), `D-NN` (decisión de diseño registrada), `F-X` / `G-X` (fase y puerta del proyecto), `ODD-n.PARÁMETRO` (parámetro declarado del dominio operacional), `TBD-Qn` (cuestión abierta pendiente de cierre).

**Identificadores de la argumentación.** Distintos de los anteriores, ordenan el hilo del texto en lugar de la cadena de evidencia: `OE1`…`OE7` (objetivos específicos, §1.4), `H1`…`H3` (hipótesis, §1.5 — no confundir con `H-01`…`H-12`, que son peligros), `A1`…`A5` (adaptaciones al V-Model, §3.4), `R1`…`R14` (resultados, Capítulo 12), `T1`…`T7` (líneas de trabajo futuro, Capítulo 12).

**Símbolos principales.**

| Símbolo | Significado | Unidad |
| --- | --- | --- |
| `ey` | Desviación lateral respecto al centro del carril | m |
| `epsi`, θ | Error de rumbo respecto a la tangente del carril | rad / ° |
| κ | Curvatura de la trayectoria de referencia | m⁻¹ |
| `d_max` | Límite duro de desviación lateral (regla C-01) | m |
| θ_max | Límite de error de rumbo (regla C-02) | ° |
| `t_min` | Umbral de tiempo hasta el cruce de carril (regla C-03) | s |
| σ_θ | Desviación típica del rumbo en ventana deslizante | ° |
| `s` | Longitud de arco recorrida sobre el centro del circuito | m |
| Δs | Incremento de longitud de arco entre dos ciclos consecutivos | m |
