"""
Unit tests for train_ppo's learning-rate schedules.

``linear_floor`` was added for the 2.5M-step sim-to-real run. Plain ``linear``
reaches exactly zero at the last step, which is right for a run sized to its own
convergence and wrong for a long, heavily randomised one: the 19.08 fine-tune
spent its final steps at an inert LR while its reward was still climbing (trough
421 at ~697k, 816 by 825k and rising), and on a wide randomisation distribution
the tail is where the far corners finally get visited.
"""
import sys
from pathlib import Path

import pytest

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.train_ppo import (  # noqa: E402
    _linear_floor_schedule,
    _linear_schedule,
    _resolve_learning_rate,
)


def test_default_is_a_constant_float():
    lr = _resolve_learning_rate({"learning_rate": 3e-4})
    assert isinstance(lr, float) and lr == pytest.approx(3e-4)


def test_linear_still_anneals_to_zero():
    """The frozen runs used this shape; it must not move."""
    s = _resolve_learning_rate({"learning_rate": 3e-4, "lr_schedule": "linear"})
    assert s(1.0) == pytest.approx(3e-4)
    assert s(0.5) == pytest.approx(1.5e-4)
    assert s(0.0) == pytest.approx(0.0)


def test_linear_floor_stops_at_the_configured_fraction():
    s = _resolve_learning_rate(
        {
            "learning_rate": 3e-4,
            "lr_schedule": "linear_floor",
            "lr_floor_fraction": 0.2,
        }
    )
    assert s(1.0) == pytest.approx(3e-4)          # full rate at the start
    assert s(0.0) == pytest.approx(0.2 * 3e-4)    # and still alive at the end
    assert s(0.5) == pytest.approx(3e-4 * (0.2 + 0.8 * 0.5))


def test_linear_floor_is_monotonically_decreasing():
    s = _linear_floor_schedule(3e-4, 0.2)
    values = [s(p / 100.0) for p in range(100, -1, -1)]
    assert all(b <= a for a, b in zip(values, values[1:]))


def test_zero_floor_reproduces_the_plain_linear_schedule():
    floored = _linear_floor_schedule(3e-4, 0.0)
    plain = _linear_schedule(3e-4)
    for p in (1.0, 0.75, 0.5, 0.25, 0.0):
        assert floored(p) == pytest.approx(plain(p))


def test_default_floor_is_applied_when_unspecified():
    s = _resolve_learning_rate({"learning_rate": 1e-3, "lr_schedule": "linear_floor"})
    assert s(0.0) == pytest.approx(0.2 * 1e-3)


@pytest.mark.parametrize("fraction", [-0.1, 1.5])
def test_out_of_range_floor_is_rejected(fraction):
    with pytest.raises(ValueError, match="lr_floor_fraction"):
        _linear_floor_schedule(3e-4, fraction)


def test_unknown_schedule_name_falls_back_to_the_constant():
    lr = _resolve_learning_rate({"learning_rate": 3e-4, "lr_schedule": "cosine"})
    assert isinstance(lr, float) and lr == pytest.approx(3e-4)
