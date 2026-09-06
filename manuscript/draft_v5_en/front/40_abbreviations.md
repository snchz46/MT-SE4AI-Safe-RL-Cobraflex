# List of abbreviations and symbols

| Abbreviation | Meaning |
| --- | --- |
| ADAS | Advanced Driver-Assistance System |
| AI | Artificial Intelligence |
| CNN | Convolutional Neural Network |
| CV | Computer Vision |
| DR | Domain Randomization |
| HARA | Hazard Analysis and Risk Assessment |
| MDP | Markov Decision Process |
| ODD | Operational Design Domain |
| PD | Proportional-Derivative (controller) |
| PPO | Proximal Policy Optimization |
| RL | Reinforcement Learning |
| ROS2 | Robot Operating System 2 |
| RTX / PhysX | NVIDIA rendering and physics engines (Isaac Sim) |
| SAC | Soft Actor-Critic |
| SE4AI | Systems Engineering for Artificial Intelligence |
| SOTIF | Safety of the Intended Functionality (ISO 21448) |
| SR | Safety Requirement |
| STPA | System-Theoretic Process Analysis |
| TTLC | Time-To-Lane-Crossing |
| V&V | Verification and Validation |

**Framework identifiers.** The work uses a single, non-reusable identifier space, summarised here; the corresponding registers are Appendices A (hazards), B (requirements), E (cage) and F (traceability): `H-XX` (hazard), `SR-XXX` (safety requirement), `C-XX` (cage rule), `SC-*` (scenario), `M-*` (metric), `D-NN` (recorded design decision), `F-X` / `G-X` (project phase and gate).

**Main symbols.**

| Symbol | Meaning | Unit |
| --- | --- | --- |
| `ey` | Lateral deviation from the lane centre | m |
| `epsi`, θ | Heading error with respect to the lane tangent | rad / ° |
| κ | Curvature of the reference trajectory | m⁻¹ |
| `d_max` | Hard limit on lateral deviation (rule C-01) | m |
| θ_max | Limit on heading error (rule C-02) | ° |
| `t_min` | Time-to-lane-crossing threshold (rule C-03) | s |
| σ_θ | Standard deviation of the heading over a sliding window | ° |
| `s` | Arc length travelled along the centre line of the circuit | m |
