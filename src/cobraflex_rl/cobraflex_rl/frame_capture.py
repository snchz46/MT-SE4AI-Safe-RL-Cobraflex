"""
frame_capture — the ROS-free half of ``frame_capture_node``: a time-bounded
ring buffer over camera frames plus the trigger state machine that decides
which of them reach disk.

WHY THIS EXISTS. `docs/17` §8.9 closed the 26.08.2026 track session with an
open item: the failures could not be localised because nothing recorded what
the lane estimator SAW when it declared perception invalid, and the frame that
would have located them was the one that jumped. The obvious fix — adding the
image topic to `ros2 bag record` — is the one that must not be used: raw
640x360 bgr8 at 20 Hz is 13.8 MB/s to eMMC, and doing exactly that alongside
the deploy chain crashed the Jetson on 18.08 (`tools/record_lane_dataset.py`
header, `experiments/physical/runs/circuit_survey/REPAIR_NOTE.md`).

So frames are held in RAM and written only around an event. On the 26.08
`noloopclosure` lap there was exactly ONE in-motion perception event in 101 s,
so a 3 s pre / 2 s post window costs about 100 frames — roughly 20 MB of PNG
for the whole run instead of 1.4 GB of bag.

The buffer stores opaque payloads, never ROS message types, so the whole
policy is testable on a host with no ROS installed.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, List, Optional, Tuple

#: Triggers, in the order they are reported when several coincide.
TRIGGER_PERCEPTION_INVALID = "perception_invalid"
TRIGGER_EMERGENCY = "emergency"
TRIGGER_MANUAL = "manual"


@dataclass
class CaptureEvent:
    """One dump: why it fired, when, and how many frames it took."""

    index: int
    reason: str
    trigger_time: float
    pre_frames: int = 0
    post_frames: int = 0

    @property
    def total_frames(self) -> int:
        return self.pre_frames + self.post_frames


@dataclass
class FrameCapture:
    """Ring buffer + trigger window.

    ``pre_seconds`` of history are kept at all times; a trigger emits that
    history and then keeps emitting for ``post_seconds``. Overlapping triggers
    EXTEND the current window rather than opening a second event — a lane
    estimator that flickers invalid four times in a second is one failure, not
    four, and the alternative burns the ``max_events`` budget on the first
    second of a run.
    """

    pre_seconds: float = 3.0
    post_seconds: float = 2.0
    max_events: int = 8
    max_frames: int = 4000

    _buffer: Deque[Tuple[float, Any]] = field(default_factory=deque, repr=False)
    _events: List[CaptureEvent] = field(default_factory=list)
    _window_until: Optional[float] = None
    _frames_written: int = 0

    # ---------------------------------------------------------------- queries
    @property
    def events(self) -> List[CaptureEvent]:
        return list(self._events)

    @property
    def frames_written(self) -> int:
        return self._frames_written

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    @property
    def budget_exhausted(self) -> bool:
        return (
            len(self._events) >= self.max_events
            or self._frames_written >= self.max_frames
        )

    def recording(self, now: float) -> bool:
        return self._window_until is not None and now <= self._window_until

    # ----------------------------------------------------------------- inputs
    def add_frame(self, stamp: float, payload: Any) -> List[Tuple[float, Any]]:
        """Offer one frame. Returns the frames to write to disk (0 or 1).

        While no window is open the frame only enters the ring buffer. The
        buffer is trimmed by TIME, not by count, so a starved camera (7.3 Hz on
        26.08 against a nominal 20) still yields a full ``pre_seconds`` of
        history instead of a third of it.
        """
        self._buffer.append((stamp, payload))
        horizon = stamp - self.pre_seconds
        while self._buffer and self._buffer[0][0] < horizon:
            self._buffer.popleft()

        if not self.recording(stamp):
            return []
        if self._frames_written >= self.max_frames:
            return []
        self._buffer.pop()          # it is being written, not buffered
        self._frames_written += 1
        self._events[-1].post_frames += 1
        return [(stamp, payload)]

    def trigger(self, now: float, reason: str) -> List[Tuple[float, Any]]:
        """Open (or extend) a capture window. Returns the pre-buffer to write.

        Extending returns nothing: those frames were already emitted by the
        event in progress.
        """
        if self.recording(now):
            self._window_until = now + self.post_seconds
            return []
        if self.budget_exhausted:
            return []

        event = CaptureEvent(
            index=len(self._events) + 1, reason=reason, trigger_time=now
        )
        self._events.append(event)
        self._window_until = now + self.post_seconds

        pre = list(self._buffer)
        room = max(0, self.max_frames - self._frames_written)
        pre = pre[-room:] if room < len(pre) else pre
        self._buffer.clear()
        event.pre_frames = len(pre)
        self._frames_written += len(pre)
        return pre


def frame_filename(event_index: int, stamp: float, extension: str = "png") -> str:
    """``e03_1787738804.712935.png`` — event first so a listing groups by event,
    then the raw stamp, which is the join key to `/state_obs` in the rosbag."""
    return f"e{event_index:02d}_{stamp:.6f}.{extension}"
