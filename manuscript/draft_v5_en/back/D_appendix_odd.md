# Appendix D — Operational domain specification

Full table of parameters for the four operational domains. Each parameter has a name, a value for each domain and a source. Whenever a named parameter exists, no claim about the domain in the main text relies on a qualitative description.

| Parameter ID | Quantity | ODD-1 | ODD-2 | ODD-3 | ODD-4 | Source |
| ------------ | -------- | ----- | ----- | ----- | ----- | ------ |
| `*.LANE_WIDTH` | Lane width (m) | 0.245 | 0.245 | 0.245 | 0.245 | Centerline configs (`complex_b_centerline.yaml`) |
| `*.ROAD_WIDTH` | Total road width (m) | 0.52 | 0.52 | 0.52 | 0.52 | complex_b configs (oval legacy 0.50) |
| `*.ROAD_LENGTH` | Loop / segment length (m) | straight portion | straight portion | 19.22 (centre) / 19.93 (driven) | 19.22 / 19.93 | complex_b perimeter (oval legacy ≈ 8.79) |
| `*.GRADIENT` | Road gradient | 0 | 0 | 0 | 0 | Map convention |
| `*.FRICTION` | Surface friction coeff. | 1.0 | 1.0 | 1.0 | 1.0 | Gazebo ODE default |
| `*.V_MAX` / `*.V_MAX_STRAIGHT` | Speed ceiling, straight (m/s) | 0.5 | 0.5 | 0.5 | 0.5 | SR-004; C-04. Operating point = 0.20 |
| `*.V_MAX_CURVE` | Speed ceiling, curve (m/s) | n/a | n/a | 0.25 | 0.25 | SR-004; C-04 |
| `*.K_KAPPA` | Curvature speed-decay coeff. | n/a | n/a | 0.3 | 0.3 | SR-004; C-04 |
| `*.KAPPA_MAX` | Max local curvature (1/m) | 0 | 0 | 1.14 | 1.14 | 1 / 0.876 m (complex_b centre R_min); driven ≈ 1.00; oval legacy 1.25 |
| `*.A_LAT_MAX` | Max commanded lateral accel. (m/s²) | 9.81 | 9.81 | 9.81 | 9.81 | Coulomb ceiling FRICTION×g |
| `*.T_CTRL` | Control cycle period (ms) | 50 | 50 | 50 | 50 | cage.yaml (20 Hz deployment); sim train/eval 10 Hz (control_dt 0.10 s) |
| `*.LATENCY_NOMINAL` | Nominal control latency (ms) | 50 | 50 | 50 | 50 | Implementation; SR-001 rationale |
| `*.STALENESS_MAX` | Max admissible state staleness (ms) | 200 | 200 | 200 | 200 | SR-007 (cage budget 0.5 s at 10 Hz, cage 0.6.1) |
| `*.LANE_EDGE` | Geometric lane edge (m, from centre) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | LANE_WIDTH / 2 |
| `*.CORRIDOR_EDGE` | Episode-termination edge (m) | 0.1225 | 0.1225 | 0.1225 | 0.1225 | Episode-termination logic (= LANE_EDGE) |
| `*.ROAD_EDGE` | Painted road boundary (m, from centre) | 0.26 | 0.26 | 0.26 | 0.26 | ROAD_WIDTH / 2; off-road / M-S5 criterion (oval legacy 0.25) |
| `*.STUCK_TIMEOUT` | Stuck criterion timeout (s) | n/a | n/a | n/a | n/a | Subsumed by env truncation (500 × 0.10 s = 50 s); TBD-Q11 |
| `*.OBS_DIM` | Observation | camera 84×84×4 (policy); CV lane-estimate (cage) | same | same | same | Track 'E'. F-track baseline: 6-D state vector |
| `*.ACT_DIM` | GE4-realised action vector dimension | 1 | 1 | 1 | 1 | Steering-only verdict parameter. Posterior Gazebo and Isaac configs set 2 locally without changing this ODD value |
