# Margin notes for the PSIThesis rendering

These notes exist only in the LaTeX rendering: the DOCX build has no margin
column. `md2tex.py` inserts each one into the chapter it names, right after the
first occurrence of its anchor text, as a numbered `\sidenote`. An entry marked
`@prelim` puts the evidence-status flag (`\prelimflag`) in the margin instead.

Rules for adding a note:

* The anchor must be copied exactly from the Markdown of that chapter, and must
  sit in running text: not in a heading, a caption or a table (a float has no
  margin to put a note in). The converter warns when an anchor is not found.
* A note explains a term or points to where something is explained. It adds no
  result, number or claim that the chapter does not already contain.
* Appendices have no margin column (`main.tex` switches to full width), so
  notes can only be attached to `body/` chapters.

Format: `## <file>` opens a chapter; `@ <anchor>` starts a note, whose text is
the following lines up to a blank line. The note text is Markdown and goes
through the same conversion as the chapter (identifiers, `§` references, code).

## body/01_introduction.md

@ SAE level 2
SAE J3016 defines six levels, from 0 (no automation) to 5 (full automation). At level 2 the system steers and controls speed, but a human driver must supervise all the time (Figure 1.1).

@ monitor-actuator architectures or *safety cages*
A safety cage is a set of fixed, hand-written rules between the learned policy and the vehicle. It checks every command and replaces the ones that break a rule. The cage of this work has six rules (Chapter 5).

@ is end-to-end from the front camera
End-to-end: one network goes from the raw image to the command, with no separate, hand-built perception step in between.

@ serves as a control arm
As in a clinical trial, the control arm is the comparison group: same cage, same scenarios, but perfect state information, so the difference between the arms can be attributed to perception.

@ by projecting the true pose onto the centre line
`ey` is the lateral offset from the lane centre, `epsi` the heading error relative to the lane direction and `v` the speed. All symbols are listed at the start of the document.

## body/02_related_work.md

@ thanks to its clipped loss
PPO limits how far the policy can move in one update by clipping its objective. This keeps training stable, at the cost of needing more samples.

@ because it is *off-policy*
An off-policy method can learn from experience collected by older versions of the policy, kept in a replay buffer. An on-policy method such as PPO only uses fresh experience.

@ At the same time, domain randomization
Domain randomization trains on many randomly varied copies of the simulated world (lighting, textures, dynamics), so that the real world looks like one more variation.

@ The architecture goes back to the Simplex pattern
In the Simplex pattern a simple, verified controller watches a complex one and takes over when the system gets close to an unsafe state.

@ The theoretical problem behind this is coverage.
Coverage: how much of the operational domain the scenario library actually exercises. Without a measure of it, no library size can be called enough.

@ formalises the *safety case*
A safety case is a structured argument, backed by evidence, that a system is acceptably safe for a given use in a given environment.

@ a six-stage method with GSN patterns
GSN, Goal Structuring Notation: a graphical way to draw a safety argument as goals, the strategies that break them down, and the evidence that supports them.

## body/03_methodology.md

@ *design science research* tradition
In design science the contribution is a useful artefact, here the adapted V-Model. It is judged by how well it solves the problem when it is used, not by a statistical test.

@ L4 is split into two different sublevels
L1 to L5 are the levels of the left branch of the V, from stakeholder requirements (L1) to implementation (L5). A primed level, such as L4a', is its partner on the right branch (Table 3.3).

@ fails if it finds orphans in either direction
An orphan is an identifier with a missing link: for example a cage rule that no requirement asks for, or a requirement that no scenario tests.

@ like Class I technology
TR 5469 classes: Class I can be handled with existing functional safety methods, Class II also needs extra methods, and for Class III no known method is enough (§2.5).

@ ends with a review gate
A review gate is the check at the end of a phase. The project moves on only when the deliverables of the phase exist and the traceability checker reports no orphans.

## body/04_domain_hazards_requirements.md

@ split into the four nested domains shown in Figure 4.1
ODD, operational design domain: the conditions (layout, lighting, speed, latency) under which the system is designed to work. Outside it, no safety claim is made.

@ follows the structure of a HARA as in ISO 26262
HARA, hazard analysis and risk assessment: the ISO 26262 step that lists hazards, rates them and derives the safety goals that the requirements must meet.

@ severity (from S0, no injury
The three ratings follow ISO 26262 Part 3, adapted to a 1:14 vehicle on a closed track. §C.2.7 explains what each level means here.

@ a light systemic analysis based on control theory is also carried out
This is a light version of STPA, System-Theoretic Process Analysis, which looks for unsafe control actions in the whole loop instead of broken components.

@ The requirements are split into two classes
In the tables, A and B stand for the classes `SR-CL-A` and `SR-CL-B`. Only a failed class A requirement can make the global verdict fail.

## body/05_architecture_and_cage.md

@ uses the runtime shield as the main mechanism
Runtime means that the check happens while the system runs, in every control cycle, not once before deployment.

@ Every rule with a threshold therefore has a hysteresis band.
With hysteresis a rule switches on above one threshold and off only below a lower one. The gap stops it from flickering when the value sits near the limit.

@ acts on the estimated time to lane departure
Also called TTLC, time to lane crossing: how long the vehicle would take to reach the lane boundary if it kept its current lateral motion.

@ records the *hash* of the file
A cryptographic hash is a short fingerprint of a file. If one character of the file changes, the hash changes, so every run can be matched to its exact configuration.

@ The cage also has two operating modes
Both modes run the same rules and log the same activations. The only difference is whether the corrected command reaches the vehicle, which is what makes monitoring a clean counterfactual.

@ The cost is a common cause
A common cause is one fault that defeats two protections that are meant to be independent. Here it is a degraded image that blinds the policy and the cage estimator at the same time.

## body/06_implementation.md

@ a proportional-derivative controller on the lateral and heading error is implemented
A PD controller steers in proportion to the lateral and heading errors and to how fast they change. It does not learn and behaves the same way in every run.

@ The real platform uses differential drive
Differential drive: the vehicle turns by driving its left and right wheels at different speeds, like a tank, instead of turning its front wheels.

## body/07_training.md

@ stacked over four consecutive frames
With one frame the network sees a position. With four it also sees motion, so it can tell whether the car is moving towards the edge or away from it.

@ a dead band in the throttle command
A dead band ignores very small throttle commands, so that noise around zero does not make the vehicle creep or jerk.

@ Checkpoints are saved at fixed intervals
A checkpoint is a saved copy of the network weights at a given training step. Any checkpoint can later be loaded and evaluated on its own.

@ once the policy's standard deviation is annealed too far
PPO samples its actions from a distribution whose width, the standard deviation, is reduced during training. When the width becomes too small the policy stops trying new actions.

@ It has to be chosen by closed-loop evaluation on scenarios
Closed loop: the policy drives, its actions change what the camera sees next, and the outcome is measured. The training reward is collected with exploration and visual randomisation switched on.

@ A policy trained with the on-policy method
The on-policy method is PPO and the off-policy method is SAC (§2.2).

## body/08_experimental_evaluation.md

@ The library has twenty-eight scenarios in four families
Scenario IDs show the family: `SC-NOM` nominal, `SC-EDGE` edge, `SC-PERT` perturbed and `SC-FRONT` frontier. Appendix I gives the result of every scenario.

@ The literal global verdict is `NOT SATISFIED`
Literal: the verdict exactly as the aggregator computes it from the scenario criteria, before any reading of why a criterion failed.

@ splits the runs by whether their starting condition is inside or outside the operational domain
A run counts as outside the ODD when its starting condition is beyond the declared domain. The system is not required to cope with it, but the cage is measured there anyway.

@ at the cost of 406 controlled stops
A controlled stop is the response of C-05: steering frozen and braking at a minimum rate until the vehicle stands still. It is safe, but it ends the run early.

@ The only difference between the modes is the rate limiter
C-06 caps how much the command may change from one cycle to the next: 0.15 for steering and 0.10 for throttle, on the normalised command.

@ The most likely explanation is co-adaptation.
During training the policy only ever acted through the limiter, so jerky commands were smoothed before they could cost any reward. Nothing pushed the policy to learn smooth commands itself.

@ Proving the cause would need an ablation
An ablation removes one part, here the limiter during training, and repeats the experiment to see whether the effect goes away with it.

@ The co-activation grid, whose starting conditions are set on purpose to force this case
The grid is scenario SC-EDGE-05: 100 runs whose starting points are chosen so that two or more rules must fire in the same cycle (§I.4).

@ The *liveness* requirement is closed on its own measurements.
Liveness: the vehicle keeps making progress. A policy that learns to park avoids every penalty but is useless, which is hazard H-08.

## body/09_sim_to_real_gap.md

@ **What follows is the *bring-up* of the physical step, not its results campaign**
Bring-up: getting the hardware chain to run end to end and calibrating it. It comes before, and is not the same as, a campaign run under the scenario protocol.

@ The item marked as blocking was the effective field of view of the onboard camera.
The effective field of view is the horizontal angle the camera really sees. Converting pixels to millimetres depends on it, so a wrong value scales every lateral quantity.

@ is not to change the estimator's parameters but to rectify the real image to the standard camera model
Rectifying removes the lens distortion, so that the image follows the same ideal pinhole camera model that the simulator uses.

@ The policy memorised the handedness of the track as a steering bias.
Handedness is the balance between left and right curves. Driven clockwise, `complex_b` has about 13 m of left curves and 2 m of right curves per lap.

@ observation and action are mirrored per episode
Mirroring flips the image left to right and the sign of the steering together, so in about half of the episodes the policy effectively drives a right-handed circuit.

@prelim **And it transfers: first measurement, one run.**

@ latched the emergency stop
Latched: once C-05 fires it stays active until an explicit reset, even after the trigger has gone. This avoids switching on and off at the edge of the trigger.

@ When the stereo camera's visual odometry closes a loop
Loop closure: when the camera recognises a place it has already seen, it corrects its accumulated drift in a single step. That step is what reaches the cage as a pose jump.

@ on a closed circuit, the curvature integrated over one lap equals 2π
Over one closed lap the heading turns through one full circle, whatever the shape of the circuit. The check needs no reference position, and the measured values are ratios to that expected total.

@prelim The table now has a physical column

## body/10_operational_validation.md

@ For that reason the physical column of the table below is marked not executed.
Not executed rather than pending: no measurement is in progress, and no data taken outside the protocol is used to fill the column.

@ The requirement is satisfied trivially
Trivially satisfied: the requirement was never challenged, because the speed never reached the rule's threshold, so its rule was never exercised.

## body/11_discussion.md

@ That difference, checking the *execution* versus checking the *reference*
Checking the reference: every scenario ID points to a requirement that exists. Checking the execution: the scenario really injects its starting conditions and logs what its criterion needs.
