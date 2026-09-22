# Anexo H — Especificación de entrenamiento: detalle

## H.1 Función de recompensa

La recompensa es la misma en los dos tracks. Se calcula sobre el estado **ground-truth** más el avance, así que no depende de la observación:

```text
r = w_fwd · max(progress, 0)
  - w_ey  · |ey|
  - w_eps · |epsi|
  - w_ds  · |Δsteering|
  - w_term · [terminated_off_road]
```

donde `progress` es el avance normalizado a lo largo de la línea central, `Δsteering` es el cambio en el steering crudo de la política (no el que sale de la cage; §7.2.2), y `[terminated_off_road]` vale 1 solo si el episodio termina por salida de vía (no por emergencia C-05; §7.2.4). Los pesos nominales (que pueden ajustarse experimentalmente) son:

| Parámetro | Valor | Rationale |
| --- | --- | --- |
| `w_fwd` (forward_progress) | 1.0 | Premia progreso real (≈1.0/paso a crucero) |
| `w_ey` (lateral_error) | 2.5 | Penalización principal: offset lateral |
| `w_eps` (heading_error) | 0.75 | Penalización secundaria: heading |
| `w_ds` (steer_delta) | 0.20 | Suavidad de actuación (sobre Δsteering crudo, v1.2; §7.2.2) |
| `w_term` (termination) | 25.0 | Desincentiva salida de vía |

El término de avance usa el progreso normalizado y no la velocidad. Como la velocidad es fija, un término `w_fwd·speed` sería una constante que no distingue ninguna conducta, y dejaba `explained_variance ≈ 0`. La penalización alta por terminación (25.0) da prioridad a seguir en la vía. Solo se aplica al salir de la vía: la emergencia C-05 termina el episodio sin penalización, porque la intervención de la cage es parte de la dinámica y no un castigo (§7.2.4). Los pesos son `[provisional, M-P1..M-P4]`. El detalle está en `docs/10_reward_function.md`.

## H.2 Hiperparámetros

La tabla recoge la configuración efectiva completa. La columna E-main corresponde al run de cámara `ppo_newcam_complex_b_2024_1M`, y la baseline F, al run de estado `ppo_train_2024_200k`.

| Parámetro | E-main (cámara) | Baseline (F, estado) | Fuente / nota |
| --- | --- | --- | --- |
| `policy` | CnnPolicy | MlpPolicy | red de la política |
| `total_timesteps` | 1 000 000 (plan; parado ≈662k) | 200 000 | `[provisional, M-P7]` |
| `learning_rate` | 3×10⁻⁴, anneal lineal | 3×10⁻⁴ constante | E: `lr_schedule: linear` |
| `target_kl` | 0.5 | — (sin freno) | E: freno de región de confianza (§7.3) |
| `normalize_reward` | True (`VecNormalize`) | False | E: estabiliza el crítico (§7.3) |
| `clip_range_vf` | 0.2 | null | E: clip del valor sobre recompensa normalizada |
| `gamma` | 0.99 | 0.99 | = SB3 default |
| `n_steps` | 1 024 | 1 024 | ≈ 1 episodio |
| `batch_size` | 64 | 64 | = SB3 default |
| `n_epochs` | 10 | 10 | SB3 default |
| `gae_lambda` | 0.95 | 0.95 | SB3 default |
| `clip_range` | 0.2 | 0.2 | SB3 default |
| `ent_coef` | 0.0 | 0.0 | sin bonus de entropía |
| `vf_coef` | 0.5 | 0.5 | SB3 default |
| `max_grad_norm` | 0.5 | 0.5 | SB3 default |
| `device` | auto (CUDA si existe) | cpu | E: la CNN aprovecha GPU |

Los cuatro ajustes de estabilidad del E-main (`target_kl`, reducción lineal del LR, `VecNormalize(norm_reward)` y `clip_range_vf`) no están en el baseline F. Se añadieron al ver que PPO con una CNN y aleatorización visual es bastante menos estable que con el vector de estado (§7.3). `norm_obs` se deja en False, así que la evaluación y la inferencia no se ven afectadas y `ep_rew_mean` en la curva queda sin normalizar (comparable con el baseline). El presupuesto para la cámara es de al menos 1M pasos, y un piloto de unos 20k pasos comprueba que el bucle funciona antes de gastar ese presupuesto.

## H.3 Estudio comparativo de algoritmos y puntos de control

La tabla sigue la cadena corrida → punto de control → evaluación del estudio posterior. Todos los valores de evaluación vienen del escenario nominal con la aleatorización desactivada. El pico indicado es el de la curva de entrenamiento y no siempre coincide con los puntos de control guardados, así que la elección final se hace con evaluación en lazo cerrado.

| Acción · configuración | Evidencia de entrenamiento | Checkpoint evaluado | SC-NOM-01, enforcement | SC-NOM-01, monitoring |
| --- | --- | --- | --- | --- |
| **1-D**, SAC `auto`, seed 2024 · `sac_newcam_complex_b_2024_1M` | pico 720,0 @ 89 089; parada manual en 307 201 de 1M previstos | 75k (`58631022…`) | 5,12 vueltas; 19,8 mm; 0 emerg.; 48,3 % C-06 | 5,13 vueltas; 23,3 mm; 0 emerg. |
| **1-D**, `ent_coef=0.005`, seed 2024 · `sac_newcam_entfix_complex_b_2024_1M` | pico 722,5 @ 82 945; sin el colapso abrupto; parada en 260 097 | 75k (`b74505ac…`) | 5,04 vueltas; 21,6 mm; 0 emerg.; 9,1 % C-06 | 5,04 vueltas; 21,6 mm; 0 emerg. |
| **1-D**, `ent_coef=0.005`, seed 42 · `sac_newcam_entfix_complex_b_42_120k` | pico 744,3 @ 87 041; réplica acotada a 120 833 | 75k (`4d09e43c…`) | 4,63 vueltas; **12,3 mm**; 0 emerg.; **2,3 % C-06** | **pendiente: no existe run nominal `_mon`** |
| **1-D**, `ent_coef=0.005`, seed 666 · `sac_newcam_entfix_complex_b_666_120k` | pico 606,9 @ 80 897; réplica acotada a 120 833 | 75k (`18c80fce…`) | 5,00 vueltas; 14,0 mm; 0 emerg.; 5,3 % C-06 | 5,00 vueltas; 14,0 mm; 0 emerg.; 6,2 % C-06 contrafactual |
| **1-D**, `ent_coef=0.005`, buffer 200k, seed 2024 · `sac_newcam_entfix_buf200_2024_180k` | banda 690–745 sostenida; pico 744,7 @ 155 649; parada en 180 225 | 150k (`a5c5f3c4…`) | 4,94 vueltas; 26,9 mm; 0 emerg.; 14,4 % C-06 | no ejecutado |
| **2-D**, SAC `auto`, seed 2024 · `sac_gz2d_tuned_complex_b_2024_1M` | ciclos colapso–recuperación; pico 527,0 @ 153 601; parada en 250 881 | flanco 175k (`e8934d51…`) | 3,45 vueltas; 34,8 mm; 1 parada C-05 | 4,31 vueltas; 32,3 mm; 0 emerg. |
| **2-D**, `ent_coef=0.005`, seed 2024 · `sac_gz2d_tuned_entfix_2024_1M` | pico 558,7 @ 77 825; subida sin ciclos abruptos; parada en 176 129 | 75k (`b76724c7…`) | **4,32 vueltas; 17,1 mm; 0 emerg.**; 17,1 % C-06 | 4,31 vueltas; 16,3 mm; 0 emerg. |
| **2-D**, `ent_coef=0.005`, seed 42 · `sac_gz2d_tuned_entfix_42_120k` | pico 270,9 @ 47 105; réplica acotada a 120 833 | 50k (`cbde3836…`) | **4,97 vueltas; 18,2 mm; 0 emerg.**; 46,4 % C-06 | 4,84 vueltas; 22,6 mm; 39 pasos con trigger C-05 contrafactual |

*Cadena corrida → checkpoint → evaluación del estudio SAC posterior. Los porcentajes de intervención en monitoring son activaciones contrafactuales: se registran, pero la acción de la cage no se aplica.*
