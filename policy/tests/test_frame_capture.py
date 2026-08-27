"""Host-side tests for the frame ring buffer behind ``frame_capture_node``.

The node itself needs a Jetson and a camera; this is the part that decides what
reaches disk, and getting it wrong is expensive in both directions — too eager
and it reproduces the eMMC saturation that crashed the car on 18.08.2026, too
lazy and the next track session again cannot say what the estimator saw.
"""
import pytest

from cobraflex_rl.frame_capture import (
    TRIGGER_EMERGENCY,
    TRIGGER_PERCEPTION_INVALID,
    FrameCapture,
    frame_filename,
)


def _fill(cap, start, count, dt=0.05):
    """Feed ``count`` frames at ``dt`` spacing; return what got written."""
    written = []
    for i in range(count):
        written.extend(cap.add_frame(start + i * dt, f"f{i}"))
    return written


def test_idle_frames_are_buffered_and_never_written():
    cap = FrameCapture(pre_seconds=3.0, post_seconds=2.0)
    assert _fill(cap, 100.0, 40) == []
    assert cap.frames_written == 0
    assert cap.buffered == 40


def test_buffer_is_trimmed_by_time_not_by_count():
    """A starved camera must still yield a full pre_seconds of history."""
    fast = FrameCapture(pre_seconds=1.0)
    _fill(fast, 0.0, 100, dt=0.05)          # 20 Hz
    slow = FrameCapture(pre_seconds=1.0)
    _fill(slow, 0.0, 100, dt=0.137)         # the 7.3 Hz measured on 26.08

    assert fast.buffered == pytest.approx(20, abs=1)
    assert slow.buffered == pytest.approx(8, abs=1)
    # Both hold ~1 s, which is the invariant that matters.
    for cap in (fast, slow):
        span = cap._buffer[-1][0] - cap._buffer[0][0]
        assert span <= 1.0


def test_trigger_emits_the_pre_buffer_then_the_post_window():
    cap = FrameCapture(pre_seconds=1.0, post_seconds=0.5)
    _fill(cap, 0.0, 40, dt=0.05)            # 2 s of history, 1 s retained
    pre = cap.trigger(2.0, TRIGGER_PERCEPTION_INVALID)
    assert len(pre) == pytest.approx(20, abs=1)
    assert cap.buffered == 0

    post = _fill(cap, 2.05, 20, dt=0.05)    # 1 s of frames, 0.5 s inside window
    assert len(post) == pytest.approx(10, abs=1)

    (event,) = cap.events
    assert event.reason == TRIGGER_PERCEPTION_INVALID
    assert event.total_frames == len(pre) + len(post)
    assert not cap.recording(3.5)


def test_overlapping_triggers_extend_one_event_rather_than_opening_several():
    """A flickering estimator is one failure. Opening an event per flicker would
    spend the whole budget on the first second of a run."""
    cap = FrameCapture(pre_seconds=1.0, post_seconds=1.0, max_events=3)
    _fill(cap, 0.0, 20, dt=0.05)
    cap.trigger(1.0, TRIGGER_PERCEPTION_INVALID)
    for t in (1.2, 1.4, 1.6):
        assert cap.trigger(t, TRIGGER_PERCEPTION_INVALID) == []
    assert len(cap.events) == 1
    assert cap.recording(2.5)               # extended from 2.0 to 2.6
    assert not cap.recording(2.7)


def test_a_later_distinct_trigger_opens_a_second_event():
    cap = FrameCapture(pre_seconds=1.0, post_seconds=0.5)
    _fill(cap, 0.0, 20, dt=0.05)
    cap.trigger(1.0, TRIGGER_PERCEPTION_INVALID)
    _fill(cap, 1.05, 30, dt=0.05)           # runs past the window, refills buffer
    cap.trigger(2.6, TRIGGER_EMERGENCY)
    assert [e.reason for e in cap.events] == [
        TRIGGER_PERCEPTION_INVALID, TRIGGER_EMERGENCY
    ]


def test_event_budget_is_enforced():
    cap = FrameCapture(pre_seconds=0.1, post_seconds=0.1, max_events=2)
    for k in range(5):
        base = k * 10.0
        _fill(cap, base, 4, dt=0.05)
        cap.trigger(base + 1.0, TRIGGER_PERCEPTION_INVALID)
    assert len(cap.events) == 2
    assert cap.budget_exhausted


def test_frame_budget_caps_a_pathological_run():
    cap = FrameCapture(pre_seconds=1.0, post_seconds=60.0, max_frames=25)
    _fill(cap, 0.0, 20, dt=0.05)
    cap.trigger(1.0, TRIGGER_EMERGENCY)
    _fill(cap, 1.05, 200, dt=0.05)
    assert cap.frames_written == 25


def test_pre_buffer_is_clipped_to_the_remaining_frame_budget():
    cap = FrameCapture(pre_seconds=5.0, post_seconds=0.0, max_frames=6)
    _fill(cap, 0.0, 40, dt=0.05)
    pre = cap.trigger(2.0, TRIGGER_PERCEPTION_INVALID)
    assert len(pre) == 6
    assert pre[-1][0] == pytest.approx(1.95)   # the NEWEST frames are kept


def test_filename_groups_by_event_and_keeps_the_join_key():
    name = frame_filename(3, 1787738804.712935)
    assert name.startswith("e03_")
    assert "1787738804.712935" in name
    assert name.endswith(".png")
