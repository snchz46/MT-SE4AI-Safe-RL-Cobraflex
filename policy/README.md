# Policy

Reinforcement learning policy implementation and training pipeline.

## Files

- `train.py` — PPO training script (Phase 3).
- `policy_node.py` — ROS2 node that wraps the trained policy for online inference.
- `reward.py` — reward function specification (per Training Specification).
- `env_wrapper.py` — Gymnasium-compatible environment wrapper around the simulator.
- `checkpoints/` — trained policy checkpoints (large binary; tracked via registry CSV).

## Algorithm

PPO via Stable-Baselines3 is the primary algorithm. PPO-Lagrangian is a Phase 3 contingency if needed; SAC may be added for contextual comparison if budget allows.

## Training Specification

The Training Specification is part of the V-Model adaptation A1. It is documented in the manuscript (Chapter 6, Pragmatic Aspects). The reward function, hyperparameters, and termination criteria are specified there before training begins.

## Cage during training

The cage is active during training (in enforcement mode by default). The rationale and the implications for the reward design are discussed in the Training Specification.

## Phase status

Phase 0: directory created.
Phase 2: env_wrapper.py implemented.
Phase 3: train.py implemented; first policy trained. **Currently this is the next phase.**
Phase 4 onwards: trained policy used in experiments.
