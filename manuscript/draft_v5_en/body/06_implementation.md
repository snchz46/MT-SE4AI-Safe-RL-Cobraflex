# Chapter 6 — Implementation and verification

## 6.1 Purpose of the chapter

This chapter covers the implementation level (L5) and the matching classical verification level (L4a'). It describes how the simulation environment, the system nodes and the cage from Chapter 5 were built, and how the cage is verified with the one technique that still works for a deterministic component: the unit test.

The goal is not to describe every engineering detail. The full list of modules, scripts and tests is kept in a version-controlled living document. The goal is to record the decisions that were not obvious, and the evidence that the chain works before the learned component is added.

## 6.2 Simulation environment and vehicle model

The environment uses a long-term support version of ROS2 and of Gazebo. They were chosen because they fit the rest of the chain and because they come with a native bridge between the two. The simulated world is a closed track with white side markings and a dashed centre line, on a flat surface with controlled lighting. Its geometric parameters are exactly those stated in the operational domain, so any claim about the domain can be checked against the world file.

<img src="../figures/fig_6_1_oval_gazebo_env.png" alt="Figure 6.1 — Simulation environment of the state track." width="560"/>

*Figure 6.1 — The simulation environment of the state track: the reference oval with white side markings and a dashed centre line, the vehicle on the start line, and the entity tree of the world, whose geometric parameters are those stated in the operational domain.*

The vehicle model approximates the dynamics of the physical scale vehicle. One important point is often missed. The real platform uses differential drive, with four fixed wheels and no steering angle. It is not an Ackermann vehicle. The simulation model uses a differential drive controller, so it matches the real platform in this respect. In practice, "steering" in this work always means a normalised angular velocity setpoint, not a wheel angle, and the manoeuvring limits of the simulator and of the platform have the same structure.

## 6.3 Node implementation

All nodes follow the same pattern: parameters declared outside the code, explicit subscriptions and publications, a fixed-rate loop driven by a timer, and structured logging. This is not just for looks. When something goes wrong, it makes it possible to link latency and timing behaviour to a specific node.

**Perception node.** On the state track it projects the pose onto the centre line to produce the state vector. On the camera track this job is done by the cage's own vision estimator, described below.

**Policy node.** It loads the trained model, reads the observation and publishes the raw command. It is kept as simple as possible: all the learning logic is in the training environment, and during operation the node only runs the policy.

**Cage node.** This is the central component. It is written as a pure Python library with no ROS2 dependency, and a thin node connects it to the topics. This split has an important consequence for the method. The cage can be fully tested without starting the simulator or the middleware, with a deterministic test suite that runs in less than one second. This is how the verifiability that Chapter 5 claimed in theory becomes real.

**Vehicle control node.** It turns the safe command into actuation setpoints and applies the final physical saturation.

**Logging node.** For every cycle it writes the full cage status (raw command, safe command, active rules, mode, observed state) to a structured file. It is the tool of the runtime monitoring level. Without it, adaptation A3 would have no evidence.

## 6.4 A classical controller to validate the chain

Before adding the learned component, a proportional-derivative controller on the lateral and heading error is implemented. Its role in the thesis is not to compete with the policy. It does three other things. It checks that the full chain works end to end with a controller whose behaviour is completely predictable. It gives a performance reference for reading the learning results. And it allows the cage thresholds to be calibrated with a driver that behaves the same way in every run.

Its limitations are stated. It does not anticipate curvature, it gets worse on tight curves, and its gains were tuned by hand on one specific layout. It is not a strong baseline. It is a tool.

## 6.5 Verification strategy and results

Verification has three levels. The unit tests for each rule cover, for all six rules, at least: activation above the threshold, no activation below it, behaviour inside the hysteresis band in both directions, and saturation. The property tests check invariants that no single rule owns: that the evaluation order is the declared one; that emergency mode overrides any earlier correction; that the output command is always within the physical range, however many rules acted; and that a parameter configuration from an older version still gives the older behaviour. The integration tests run the whole chain with synthetic states, checking that the command arrives filtered and that the log contains what it should.

The test suite grows with the system and has to pass before every review. Its value is not the number of tests but one property: every cage rule has tests that fail if its behaviour changes. So any change to a threshold becomes visible and cannot slip in unnoticed.

## 6.6 Chain validation and first metrics

The integrated demo runs the full chain in simulation with the classical controller driving. Three first metrics are reported here. They are not an experimental result, only evidence that the chain works. The real characterisation is in Chapter 8.

The cage cycle latency, measured over 845 s of continuous operation, has a median and a 95th percentile of 50.0 ms, with a maximum of 62.0 ms caused by a single cycle and by the operating system's non-deterministic scheduler. The median and 95th percentile fit within the control cycle budget.

During nominal operation the cage intervenes in 0.047 % of the cycles (8 out of 16,910). All of them come from the heading rule or the rate limiter. The lateral limit, the predictive rule and emergency mode never fire. This result says two things, and both matter: the classical controller is well tuned for the nominal scenario, and the cage thresholds are not too strict. A cage that intervened all the time under nominal conditions would not be measuring safety. It would be measuring its own bad tuning.

Under nominal conditions the vehicle completes 9.91 laps in 845 s without a single emergency cycle. One run is not enough to characterise anything. What the number shows is that the chain can run for a long time without getting worse.

## 6.7 Changes for the camera track

The reference system does not add new nodes. It adapts the environment, as shown in Figure 6.2. The same training environment is used for both tracks, and the camera branch is turned on with a configuration switch. Four technical decisions are worth recording.

**Shared camera pipeline and common cause.** The native image comes through the bridge between simulator and middleware and passes through a single pipeline in each cycle. The scenario's visual degradation injector is applied before the pipeline splits. This way, the same degraded image goes both to the cage estimator, at native resolution, and to the 84×84 greyscale version that the policy uses. Applying the degradation only once, before the split, is what makes sure that policy and cage see the same world, including when that world is degraded. One implementation finding has a direct effect on the experiment budget: camera rendering is tied to real time, so on this track the simulation clock runs at factor one, while the state track runs faster than real time.

<img src="../figures/fig_6_2_etrack_camera_control_loop.png" alt="Figure 6.2 — Control loop of the camera track." width="540"/>

*Figure 6.2 — The control loop of the camera track. The degradation injector is applied before the split, so the deterministic cage estimator and the 84×84 image the network uses receive exactly the same input. This is the common cause that Chapter 5 records as a residual risk, and it is also why a scenario stressor can be clearly attributed: it enters the system exactly once.*

<img src="../figures/fig_6_3_cv_lane_estimator_pipeline.png" alt="Figure 6.3 — Chain of the cage lane estimator." width="520"/>

*Figure 6.3 — The lane estimator pipeline that the cage uses: five deterministic stages from the native image to the lane-relative state, with no learned component. This is what keeps the safety envelope from inheriting the failure modes of the network.*

**Cage lane estimator.** Figure 6.3 shows it in detail. It is a classical, deterministic vision pipeline (thresholding, line extraction and lane geometry) that rebuilds the lateral offset and the heading error for the six rules. It is validated on its own, before the verdict. Against the simulator's ground truth it detects the lane in every case, with an offset bias below 32 mm at the glare levels that the scenario campaign uses later. When its health monitor says that perception is invalid, emergency mode carries out the controlled stop in open loop. This is the mechanism that Chapter 8 measures as the value of the cage under degradation.

**Validation circuit.** The reference track is validated on a winding circuit that comes close to itself, with a perimeter of 19.22 m (2.2 times the oval of the state track), and on its visual stress variants. Because the layout comes close to itself, the containment logic had to change. The off-road check based on perpendicular distance stops working when two parts of the layout are closer than one road width. So departure is judged by the global distance to the road axis, and the old behaviour is kept for the state track. It is a good example of how a change of layout can quietly break a metric that looked neutral.

**Visual randomization during training.** Training applies random visual degradations within the range of the matching hazard, to make the policy more robust. During evaluation the randomization is turned off, and the only visual stressor is the one the scenario declares, so every run can be linked to its own perturbation. Mixing the two would give results that could not be attributed.

## 6.8 Summary

At the end of this chapter the system exists. The chain works end to end, the cage is implemented and verified with the classical technique that suits a deterministic component, and the logging produces the evidence that the upper levels of the right branch will use. What is still missing is the component the framework was built for. Chapter 7 covers its process specification, which is the second half of adaptation A1, and its training.
