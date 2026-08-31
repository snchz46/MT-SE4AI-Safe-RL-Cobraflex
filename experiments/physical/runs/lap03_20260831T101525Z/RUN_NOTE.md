# lap03_20260831T101525Z — 5.47 m from the marked start; the starting-position hypothesis is REFUTED

Identical to `lap02` except one variable: started from the marked start on the
straight, centred, instead of from where `lap01` stopped. `monitoring`, rectified,
`near_secant`/1.0, `reset_proxy:=auto`. DIAGNOSTIC, NOT SCORABLE.

| | lap01 | lap02 | lap03 |
| --- | --- | --- | --- |
| start | straight, centred | mid-curve, off-centre | **straight, centred** |
| distance | 3.11 m | 14.56 m | **5.47 m** |
| \|ey\| median / max (moving) | 8.8 / 58.8 | 42.0 / 150.3 | 29.4 / **181.9** mm |
| C-02 while moving | 2 / 146 = 1.4 % | 51 / 751 = 6.8 % | 36 / 311 = 11.6 % |
| resets published | 0 (observe) | 4 | **6, budget exhausted** |
| \|kappa\| p90 while moving | **0.21** | 1.81 | 1.18 |

Starting from the mark did not help. `lap02`'s note proposed the bad start as the
leading candidate for its degradation; **this run refutes it.**

## lap01 was not a fair baseline

`|kappa|` p90 of **0.21** against 1.81 and 1.18: with 3.11 m `lap01` barely left the
straight. Its excellent 8.8 mm median is the straight's number, not the circuit's.
The honest summary of all three runs, and of 26.08, is that the policy drives the
straight well and the curves badly.

## Three hypotheses tested against the data, three unsupported

1. **Starting position** — refuted by this run.
2. **Heading error scales with curvature** (a secant fit's systematic error).
   Refuted: correlation `|kappa|` vs `|epsi|` is **r = 0.045** over 1208 moving
   cycles, and C-02 fires MOST in the lowest curvature band (12.7 % at
   `|kappa|` 0-0.25) and least at 1.25-1.75 (0.6 %).
3. **Degenerate frame stack after each reset** (`rl_policy_node` never
   re-initialises its k=4 stack — real, see lap02's note). Not supported as the
   driver here: within 3 s of a reset, C-02 runs at **0.0 %** in lap02 and
   **21.8 %** in lap03, against 7.5 % / 7.6 % afterwards. The two runs contradict
   each other on small n (72 and 87 cycles).

## What the data does support

`|ey|` median by `|kappa|` band, pooled over the three runs (moving cycles only):

| `\|kappa\|` | n | `\|ey\|` median |
| --- | --- | --- |
| 0.00-0.25 | 442 | 26.2 mm |
| 0.25-0.75 | 210 | 32.1 mm |
| 0.75-1.25 | 284 | 33.2 mm |
| 1.25-1.75 | 181 | 42.8 mm |
| 1.75+ | 91 | **63.0 mm** |

The car runs progressively wider as the curve tightens, while C-04 — the rule whose
job that is — cannot fire at all (`v_max_curve_mps` 0.25 > the deployed 0.22).

C-02 fires on isolated spikes rather than on a sustained heading error, which is
the wrong-pair signature `lap01` showed in a single cycle and which the morning's
stationary sweep measured directly on the right-hand side.

**The mechanism behind the curve failures is NOT settled by these three runs.**

## Note on counting

`lap03` logged 228 C-02 firings in total but only **36 with the car moving**; the
rest are cycles with the car already stopped. Rule counts in this campaign must be
normalised by moving cycles or they mislead.
