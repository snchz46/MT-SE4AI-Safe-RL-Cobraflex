# List of abbreviations and symbols

| Abbreviation | Meaning |
| --- | --- |
| ADAS | Advanced Driver-Assistance System |
| AI | Artificial Intelligence |
| AMLAS | Assurance of Machine Learning for Autonomous Systems |
| ASIL | Automotive Safety Integrity Level |
| CMDP | Constrained Markov Decision Process |
| CNN | Convolutional Neural Network |
| CV | Computer Vision |
| DR | Domain Randomization |
| DRL | Deep Reinforcement Learning |
| ESC | Electronic Speed Controller |
| GSN | Goal Structuring Notation |
| HARA | Hazard Analysis and Risk Assessment |
| IMU | Inertial Measurement Unit |
| KL | Kullback–Leibler (divergence between distributions) |
| MBSE | Model-Based Systems Engineering |
| MDP | Markov Decision Process |
| ML | Machine Learning |
| MPC | Model Predictive Control |
| ODD | Operational Design Domain |
| PD | Proportional-Derivative (controller) |
| PPO | Proximal Policy Optimization |
| RC | Radio-Controlled |
| RL | Reinforcement Learning |
| ROS2 | Robot Operating System 2 |
| RTX / PhysX | NVIDIA rendering and physics engines (Isaac Sim) |
| SAC | Soft Actor-Critic |
| SAE | SAE International (standards body; J3016 levels) |
| SB3 | Stable-Baselines3 (RL algorithm library) |
| SBC | Single-Board Computer |
| SE4AI | Systems Engineering for Artificial Intelligence |
| SOTIF | Safety of the Intended Functionality (ISO 21448) |
| SR | Safety Requirement |
| SRS | Safety Requirements Specification |
| STPA | System-Theoretic Process Analysis |
| TTLC | Time-To-Lane-Crossing |
| V&V | Verification and Validation |

**Framework identifiers.** The work uses a single, non-reusable identifier space, summarised here; the corresponding registers are Appendices A (hazards), B (requirements), E (cage) and F (traceability): `H-XX` (hazard), `SR-XXX` (safety requirement), `SR-CL-A` / `SR-CL-B` (criticality class of a requirement), `C-XX` (cage rule), `SC-*` (scenario), `M-*` (metric), `D-NN` (recorded design decision), `F-X` / `G-X` (project phase and gate), `ODD-n.PARAMETER` (declared parameter of the operational domain), `TBD-Qn` (open question pending closure).

**Argument identifiers.** Distinct from the previous ones, these organise the thread of the text rather than the chain of evidence: `OE1`…`OE7` (specific objectives, §1.4), `H1`…`H3` (hypotheses, §1.5 — not to be confused with `H-01`…`H-12`, which are hazards), `A1`…`A5` (adaptations to the V-Model, §3.4), `R1`…`R14` (results, Chapter 12), `T1`…`T7` (lines of future work, Chapter 12).

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
| Δs | Arc-length increment between two consecutive cycles | m |
