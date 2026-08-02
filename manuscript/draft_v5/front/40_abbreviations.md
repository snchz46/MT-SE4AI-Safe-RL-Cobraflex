# Lista de abreviaturas y símbolos

| Abreviatura | Significado |
| --- | --- |
| ADAS | Advanced Driver-Assistance System (sistema avanzado de asistencia a la conducción) |
| AI / IA | Artificial Intelligence / Inteligencia Artificial |
| CNN | Convolutional Neural Network (red neuronal convolucional) |
| CV | Computer Vision (visión por computador) |
| DR | Domain Randomization (aleatorización de dominio) |
| HARA | Hazard Analysis and Risk Assessment (análisis de peligros y evaluación de riesgo) |
| MDP | Markov Decision Process (proceso de decisión de Markov) |
| ODD | Operational Design Domain (dominio operacional de diseño) |
| PD | Proportional-Derivative (controlador proporcional-derivativo) |
| PPO | Proximal Policy Optimization |
| RL | Reinforcement Learning (aprendizaje por refuerzo) |
| ROS2 | Robot Operating System 2 |
| RTX / PhysX | Motores de renderizado y física de NVIDIA (Isaac Sim) |
| SAC | Soft Actor-Critic |
| SE4AI | Systems Engineering for Artificial Intelligence |
| SOTIF | Safety of the Intended Functionality (ISO 21448) |
| SR | Safety Requirement (requisito de seguridad) |
| STPA | System-Theoretic Process Analysis |
| TTLC | Time-To-Lane-Crossing (tiempo hasta el cruce de carril) |
| V&V | Verificación y Validación |

**Identificadores del marco.** El trabajo usa un espacio de identificadores único y no reutilizable, definido en el Anexo A: `H-XX` (hazard), `SR-XXX` (requisito de seguridad), `C-XX` (regla de la cage), `SC-*` (escenario), `M-*` (métrica), `D-NN` (decisión de diseño registrada), `F-X` / `G-X` (fase y puerta del proyecto).

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
