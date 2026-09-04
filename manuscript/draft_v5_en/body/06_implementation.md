# Chapter 6 — Implementation and verification

## 6.1 Purpose of the chapter

This chapter occupies the implementation level (L5) and its symmetric level of classical verification (L4a'). It documents how the simulation environment, the system nodes and the cage specified in Chapter 5 are materialised, and how that cage is verified with the technique that is still applicable to a deterministic component: the unit test.

The intention is not engineering exhaustiveness — the complete inventory of modules, scripts and tests lives as a version-controlled living document — but to document **the non-trivial decisions** and the evidence that the chain works before the learned component is introduced.

## 6.2 Simulation environment and vehicle modelling

The environment is built on a ROS2 distribution and a Gazebo version with long-term support, chosen for coherence with the rest of the chain and for the availability of the native bridge between them. The simulated world reproduces a delimited track with white side markings and a dashed central separator, on a flat surface and with controlled lighting; its geometric parameters are exactly those declared by the operational domain, so that any claim about the domain can be checked against the world file.

The vehicle is modelled by approximating the dynamics of the physical scale vehicle. One important and frequently overlooked clarification: the real platform is **differential drive**, with four fixed wheels and no steering angle, and not of the Ackermann type; the simulation model uses a differential drive controller and is faithful in that sense. The practical consequence is that "steering" in this whole work means a normalised angular velocity setpoint, not a wheel angle, and that the manoeuvrability envelope of the simulator and that of the platform share the same structure.

## 6.3 Implementation of the nodes

All nodes follow a common pattern: externalised and declared parameters, explicit subscription and publication, a fixed-frequency loop governed by a timer, and structured logging. The uniformity is not cosmetic: it makes latency and temporal behaviour attributable to a specific node when something deviates.

**Perception node.** On the state track it projects the pose onto the centre line in order to produce the state vector. On the camera track this role is played by the vision estimator of the cage itself, described below.

**Policy node.** It loads the trained model, consumes the observation and publishes the raw command. It is deliberately thin: all the learning logic lives in the training environment, and in operation the node is an evaluator of the policy.

**Cage node.** This is the central component. It is implemented as a **pure Python library with no ROS2 dependency**, wrapped by a thin node that connects it to the topics. This separation has a methodological consequence that deserves to be highlighted: the cage can be **tested completely without starting the simulator or the middleware**, with a deterministic suite that runs in less than one second. The verifiability that Chapter 5 claimed in the abstract becomes operational in this way.

**Vehicle control node.** It translates the safe command into actuation setpoints, applying the final physical saturation.

**Logging node.** It persists the complete cage status per cycle — raw command, safe command, active rules, mode, observed state — to a structured file. It is the instrument of the runtime monitoring level: without it, adaptation A3 would have no evidence.

## 6.4 A classical controller as a chain validator

Before introducing the learned component, a **proportional-derivative controller** over the lateral and heading error is implemented. Its function in the thesis is not to compete with the policy but to do three different things: to validate that the complete chain works end to end with a controller whose behaviour is entirely predictable; to offer a **performance reference** against which the learning results can be interpreted; and to allow the cage thresholds to be calibrated with a driver whose behaviour does not change between runs.

Its limitations are declared: it does not anticipate curvature, it degrades on tight curves and its gains were tuned empirically on one concrete geometry. It is not a competitive baseline, it is an instrument.

## 6.5 Verification strategy and results

Verification is organised on three levels. The **unit tests per rule** cover, for each of the six rules, at least the activation above the threshold, the non-activation below it, the behaviour inside the hysteresis band in both directions, and the saturation. The **transversal property tests** verify invariants that no rule owns on its own: that the evaluation order is the declared one; that the emergency mode dominates any previous correction; that the output command is always inside the physical range independently of how many rules intervened; and that a parameter configuration of an earlier version still produces the earlier behaviour. The **integration tests** exercise the complete chain with synthetic states, checking that the command arrives filtered and that the log contains what it should contain.

The suite grows with the system and is run as a condition of each review. Its value is not in the number of cases but in one property: **every cage rule has tests that fail if its behaviour changes**, which turns any threshold modification into a visible change and not into a silent drift.

## 6.6 Chain validation and preliminary metrics

The integrated demonstration runs the complete chain in simulation with the classical controller in command. Three preliminary metrics are reported, **not as an experimental result but as evidence that the chain works**; the characterisation belongs to Chapter 8.

The **cage cycle latency**, measured over 845 s of continuous operation, gives a median and a 95th percentile of 50.0 ms, with a maximum of 62.0 ms attributable to a single cycle and to the non-deterministic scheduler of the operating system. Median and 95th percentile fit inside the budget of the control cycle.

The **intervention rate** during nominal operation is 0.047 % of the cycles — 8 out of 16,910 — all of them attributed to the heading rule or to the rate limiter, with no activation of the lateral limit, of the predictive rule or of the emergency. The reading goes in two directions and both matter: the classical controller is well calibrated for the nominal scenario, **and** the cage thresholds are not artificially restrictive. A cage that intervened constantly under nominal conditions would not be measuring safety, it would be measuring its own misadjustment.

The **completion rate** under nominal conditions is 9.91 laps in 845 s with no emergency cycle at all. With a single run it is not possible to speak of characterisation; what the figure establishes is that the chain sustains prolonged operation without degradation.

## 6.7 Specialisation for the camera track

The reference system **does not add nodes: it specialises the environment**. The same training environment serves both tracks, and the camera branch is activated with a configuration switch. Four technical decisions deserve to be recorded.

**Shared camera chain and common-cause guarantee.** The native image arrives through the bridge between simulator and middleware and goes through a single chain per cycle. The visual degradation injector of the scenario is applied **before** the branching, so that the same degraded image feeds both the cage estimator, at native resolution, and the reduction to 84×84 in grey scale that the policy consumes. Applying the degradation only once, before the branching, is what guarantees that **policy and cage see the same world, also when that world is degraded**. One implementation finding has a direct consequence for the experimental budget: camera rendering is tied to real time, so the simulation clock runs at factor one on this track, as opposed to the accelerated execution of the state track.

**Lane estimator of the cage.** It is a classical and deterministic vision chain — thresholding, line extraction and lane geometry — that reconstructs the lateral offset and the heading error for the six rules. Its validation is **its own and prior to the verdict**: against the ground truth oracle of the simulator it reaches complete detection with an offset bias below 32 mm under the glare levels that the scenario campaign later uses. When its health supervisor declares perception invalid, the emergency mode executes the controlled stop in open loop: the mechanism that Chapter 8 measures as the value of the cage under degradation.

**Validation circuit.** The reference track is validated on a winding and self-approaching circuit of 19.22 m perimeter — 2.2 times the oval of the state track — and on its visual stress variants. The self-approaching layout forced a change in the containment logic: the perpendicular off-road criterion collapses when two sections of the layout are closer than one road width, so departure is judged by **global distance to the road axis**, keeping the earlier behaviour intact for the state track. It is an instructive example of how a change of geometry silently invalidates a metric that looked neutral.

**Visual randomization during training.** The training applies random visual degradations inside the envelope of the corresponding hazard, as a robustness mitigation. In evaluation the randomization is **switched off**, and the only visual stressor is the one declared by the scenario, so that every run is attributable to its perturbation. Mixing the two would produce results that could not be attributed.

## 6.8 Synthesis

At the close of this chapter the system exists: the chain works end to end, the cage is implemented and verified with the classical technique that its deterministic nature admits, and the logging produces the evidence that the upper levels of the right branch will consume. What is missing is the component that the framework exists to accommodate. Chapter 7 addresses its process specification — the second half of adaptation A1 — and its training.
