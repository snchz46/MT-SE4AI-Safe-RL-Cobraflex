from __future__ import annotations

import sys
import time
from typing import Optional

from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.utils import safe_mean


class ProgressBarCallback(BaseCallback):
    """Training progress feedback showing steps, reward and episode length.

    Under a real terminal (stdout is a TTY) it renders a live tqdm bar.
    Under ``ros2 launch`` stdout is captured line-by-line, where tqdm's
    carriage-return redraw does not render; there it falls back to emitting a
    periodic one-line progress update that shows up cleanly in the launch log.

    Reward/length come from ``model.ep_info_buffer`` (populated by the Monitor
    wrapper SB3 adds automatically), matching SB3's ``rollout/ep_rew_mean`` and
    ``rollout/ep_len_mean``.
    """

    def __init__(self, total_timesteps: int, log_interval_steps: int = 1000) -> None:
        super().__init__()
        self.total_timesteps = int(total_timesteps)
        self.log_interval_steps = int(log_interval_steps)
        self._use_tqdm = sys.stdout.isatty()
        self._pbar = None
        self._start_time = 0.0
        self._last_log_step = 0

    def _stats(self) -> tuple[float, float, int]:
        buffer = self.model.ep_info_buffer
        n_episodes = len(buffer) if buffer is not None else 0
        if n_episodes == 0:
            return 0.0, 0.0, 0
        mean_reward = safe_mean([ep["r"] for ep in buffer])
        mean_length = safe_mean([ep["l"] for ep in buffer])
        return float(mean_reward), float(mean_length), n_episodes

    def _fps(self) -> int:
        elapsed = time.time() - self._start_time
        return int(self.num_timesteps / elapsed) if elapsed > 0 else 0

    def _on_training_start(self) -> None:
        self._start_time = time.time()
        if self._use_tqdm:
            from tqdm import tqdm

            self._pbar = tqdm(
                total=self.total_timesteps,
                desc="PPO",
                unit="step",
                dynamic_ncols=True,
            )

    def _on_step(self) -> bool:
        mean_reward, mean_length, n_episodes = self._stats()
        if self._use_tqdm:
            self._pbar.n = self.num_timesteps
            self._pbar.set_postfix(
                ep_rew=f"{mean_reward:.2f}",
                ep_len=f"{mean_length:.0f}",
                eps=n_episodes,
                refresh=False,
            )
            self._pbar.refresh()
        elif self.num_timesteps - self._last_log_step >= self.log_interval_steps:
            self._last_log_step = self.num_timesteps
            pct = 100.0 * self.num_timesteps / max(self.total_timesteps, 1)
            print(
                f"PPO progress: {self.num_timesteps}/{self.total_timesteps} "
                f"({pct:.0f}%) | ep_rew_mean={mean_reward:.2f} | "
                f"ep_len_mean={mean_length:.0f} | episodes={n_episodes} | "
                f"fps={self._fps()}",
                flush=True,
            )
        return True

    def _on_training_end(self) -> None:
        if self._use_tqdm and self._pbar is not None:
            self._pbar.n = self.num_timesteps
            self._pbar.refresh()
            self._pbar.close()
            self._pbar = None
