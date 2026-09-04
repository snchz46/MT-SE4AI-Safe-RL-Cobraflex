# Appendix B — Safety requirements specification and *rationale*

Complete version of Table 4.2, with thresholds and traceability, followed by the *rationale*
requirement by requirement: where each threshold comes from, what makes it falsifiable and what its
calibration status is.

| ID | Short statement | Main parameters | H covered | Cage rule | Criticality | Verification |
| -- | ------------------- | ---------------------- | ----------- | --------- | ---------- | ------------ |
| SR-001 | The absolute lateral offset with respect to the centre of the road shall stay below `d_max` during operation inside the applicable ODD. | `d_max = 0.16 m` | H-01 | C-01 | SR-CL-A | SC-NOM-01, SC-NOM-02, SC-EDGE-02 |
| SR-002 | The absolute orientation error with respect to the lane direction shall stay below `θ_max`. | `θ_max = 0.44 rad (25°)` | H-02 | C-02 | SR-CL-A | SC-EDGE-01, SC-EDGE-04 |
| SR-003 | The projected time to lane crossing (TTLC) shall stay above `t_min`; the 5th percentile of TTLC over nominal runs shall be ≥ 0.5 s. | `t_min = 1.0 s`; p5 floor = 0.5 s | H-01, H-02 (partial) | C-03 | SR-CL-A | SC-NOM-02, SC-EDGE-01 |
| SR-004 | The longitudinal speed shall not exceed `v_max(κ)`, a ceiling dependent on the local curvature κ. | `v_max_straight = 0.5 m/s`; `v_max_curve = 0.25 m/s` | H-03 | C-04 | SR-CL-A | SC-NOM-02, SC-EDGE-03 |
| SR-005 | Under a compound trigger on heading and offset lasting `Δt_max`, the system shall transition to emergency mode with minimum deceleration and frozen steering. | `θ_warn = 20°`; `d_warn = 0.12 m`; `Δt_max = 0.2 s`; `a_min = 0.3 m/s²` (provisional, subject to M-3) | H-04, H-07 (partial) | C-05 | SR-CL-A | SC-EDGE-04 |
| SR-006 | The command variation between two consecutive cycles shall stay below `δ_max` for steering and throttle. | `δ_max_steer = 0.15`; `δ_max_thr = 0.10` (per cycle) | H-05 | C-06 | SR-CL-B | All scenarios (rate limiter active) |
| SR-007 | The cage shall activate emergency mode if the observation is older than `staleness_max` or if any field is outside the plausible range. | `staleness_max = 200 ms`; `N_missing_max = 5 cycles` | H-06 | part of C-05 | SR-CL-A | SC-PERT-02 |
| SR-008 | Under an external stop signal or a controlled end of episode, the system shall decelerate to 0 m/s within `t_stop_max` without exceeding the lateral `d_max`. | `t_stop_max = 1.7 s`; `d_max = 0.16 m` | H-07 | part of C-05 + vehicle-control node | SR-CL-A | SC-NOM-03, SC-EDGE-04 |
| SR-009 | In every eligible window of `t_window`, the vehicle shall accumulate at least `Δs_min` of nominal longitudinal progress; the metric M-S2 under monitoring mode shall not exhibit a sustained rise with respect to the baseline. | `Δs_min = 0.10 m`; `t_window = 2.0 s`; `Δt_settle = 1.0 s` | H-08 | training (D-25) | SR-CL-B | SC-NOM-01..03, SC-PERT-03 |
| SR-010 | When two or more cage rules activate in the same cycle, the final command shall satisfy the safe envelope of every activated rule and the inter-cycle pattern shall not exhibit sustained oscillation above `f_osc_max`. | `f_osc_max = 5 Hz`; joint-envelope assertion | H-09 | arbiter (D-25) | SR-CL-B | SC-EDGE-04, SC-EDGE-05 |
| SR-011 | The standard deviation of the heading error over eligible windows of `t_psd` shall stay below `σ_θ_max`, covering the in-band branch of H-02 that SR-002 does not bound. | `σ_θ_max = 5°`; `t_psd = 1.0 s` | H-02 (oscillatory branch) | C-06 + training | SR-CL-B | SC-EDGE-01, SC-EDGE-04 |
| SR-012 | (Track 'E') Lane keeping shall stay inside the SR-001/SR-002 envelope under degraded visual input (glare, exposure, motion blur, contrast, shadow). | `d_max = 0.16 m`; `θ_max = 25°` (reused); provisional visual envelope (docs/09) | H-10 | C-01, C-02, C-03 + training | SR-CL-A | SC-PERT-04, SC-PERT-05, SC-PERT-06, SC-PERT-09, SC-PERT-10 |
| SR-013 | (Track 'E') On loss of valid perception (occlusion / absence of features / stale or dropped frames), the system shall enter an open-loop controlled stop through C-05 without exceeding `d_max`. | `perc_staleness_max = 200 ms` (provisional); `d_max = 0.16 m` | H-11 | part of C-05 (health of the CV estimator of the cage) | SR-CL-A | SC-PERT-07 |
| SR-014 | (Track 'E') The cage shall not impose its rules on a lane estimate that fails the plausibility / temporal consistency check; instead it shall enter a controlled stop (C-05). | `plaus_tol`, `Δt_plaus` (provisional, against the ground-truth oracle) | H-12 | part of C-05 (plausibility check → stop) | SR-CL-A | SC-PERT-08, SC-PERT-04..06, SC-PERT-09, SC-PERT-10 |

## Rationale per requirement

The complete rationale for each SR — including the physical justification of the
threshold citing the ODD parameters, the description of the falsifiable
form, the identification of the verification experiment, and the cross
reference to the hazard from which it derives — lives in `docs/03_safety_requirements.md`.
As an illustration of the level of detail required, this subsection
presents the complete rationale of SR-001 as a representative example;
the rest is summarised briefly at the end of the subsection and cited
by reference.

The rationale of SR-001 is the following. The parameter
`d_max = 0.16 m` is not chosen from the performance of the policy
but from the geometric envelope of the ODD: the road has a total width
`ODD-1.ROAD_WIDTH = 0.50 m`, which places the physical edge of the drivable
corridor at `0.25 m` from the longitudinal axis of the track. An aggregate
safety margin of `Δ = 0.09 m` absorbs three independent
contributions: the lateral noise of the state estimator
(`≈ 0.01 m`), the maximum drift expected from the nominal control latency
(`v_max · LATENCY_NOMINAL = 0.5 m/s · 50 ms = 0.025 m`), and
half the lateral physical footprint of the 1:14 CobraFlex (`≈ 0.05 m`). The
falsifiable threshold is then `d_max = ROAD_WIDTH/2 − Δ = 0.25 − 0.09 = 0.16 m`,
interpreted as the modulus of the lateral offset of the geometric centre
of the vehicle with respect to the axis of the drivable corridor. This
convention of sign and unit is fixed in the statement of SR-001 in
`docs/03_safety_requirements.md` and is cited by the derived SRs
(SR-005 on `d_warning = 0.12 m < d_max` as an early warning
threshold, SR-008 on staying below `d_max` during the controlled
stop).

The summarised rationale of the rest of the SRs is described below,
with a reference to the standalone artefact for the details. **SR-002**
(`θ_max = 25°`) is justified through a bicycle-model calculation of
recoverability with a wheelbase of 0.15 m, a saturated steering of 0.5 rad,
a nominal speed of 0.3 m/s and a cage response time of 0.05 s;
the value falls inside the recoverable envelope with a margin of approximately
a factor of two. **SR-003** (`t_min = 1.0 s`) is decomposed into 0.3 s of
margin for the cage (defensible by kinematic physics) and 0.7 s of
margin for the policy (marked as provisional, subject to review
after the training prototype in F3). **SR-004** defines a speed
ceiling dependent on the curvature, anchored on `ODD-1.V_MAX = 0.5 m/s`
for straight sections and reduced to 0.25 m/s in a curve; the interpolation
coefficient `k_κ = 0.3` is chosen so that the curve falls
exactly at the maximum curvature expected from the `odd3_curvy_loop`
map (pending closure with TBD-Q9). **SR-005** introduces a compound
trigger with a persistence of `Δt_max = 0.2 s` (four control cycles,
necessary to distinguish a genuine compound state from a transient
glitch); `a_min = 0.3 m/s²` is provisional pending the
M-3 measurement on the platform. **SR-006** fixes a rate
limiter as a conservative defence against abrupt actuation;
the values `δ_max_steer = 0.15` and `δ_max_thr = 0.10` are
defaults that require an empirical cross-check against the mechanical
envelope of the actuator (measurement M-5) and against the 95th percentile of the
natural delta of the trained policy (after the F3 prototype). **SR-007**
preserves a staleness horizon of `staleness_max = 200 ms` (four
control cycles) complemented by a counter of missing
messages `N_missing_max = 5`, both values conservative with respect to
the nominal properties of the ROS2 bus; the plausible ranges per
state field are kept deliberately wider than the operating
envelope of each variable, so that range violations are unambiguous
indicators of a sensor failure. **SR-008**
fixes `t_stop_max = 1.7 s`, consistent with `v_max_straight / a_min ≈ 1.67 s`
from SR-005 plus a margin for granularity and latency; the consolidation
of the earlier inconsistency with SR-005 (1.5 s in the F0 baseline) is
recorded in `docs/CHANGELOG.md`. **SR-009** bounds the longitudinal
progress from below: `Δs_min = 0.10 m` derives from the product of the
minimum useful operating speed (`v_min ≈ 0.05 m/s`) and a sliding
window of `t_window = 2.0 s`; the carve-out of `Δt_settle = 1.0 s`
after transitions from emergency mode or controlled stop prevents
SR-009 from conflicting with SR-005 or SR-008 during the restart
ramp (cf. §SR-009 of the SRS for the explicit priority
order). Its implementation is training (D-25): the cage does not inject
progress, it only observes the stall through M-P6 and emits a signal to
the test harness. **SR-010** ensures the compositional consistency of the
cage: the *joint-envelope assertion* at the end of each cycle
verifies that the emitted command satisfies the preconditions of every
rule active in that cycle, and an inter-cycle monitor bounds the
oscillation between contradictory corrections below
`f_osc_max = 5 Hz`. The implementation is a structural property
of the cage pipeline (`arbiter`, D-25), not an additional numbered
rule; the failure of the assertion drops the system into C-05
(emergency mode) as a last-line mitigation. **SR-011** closes
the oscillatory branch of H-02 that the pure-magnitude threshold of SR-002 does not
bound: `σ_θ_max = 5°` admits oscillations up to an amplitude of ≈ 7° with
sufficient margin against `θ_max = 25°`, but is tight enough
to detect the within-bounds-but-oscillatory mode; the window
`t_psd = 1.0 s` captures at least one period of the significant
oscillation (≈ 1 Hz) without being diluted by drifts on a longer time scale.
The implementation is hybrid (`C-06 + training`): C-06 attenuates
high-frequency content in the commands of the policy, and a
heading variance term in the reward encourages the policy not to
oscillate in steady state.

---
