"""
Unit tests for tools/select_sim2real_checkpoint.py — checkpoint ranking by
transfer rather than reward (D-66/D-72).

The pure logic: checkpoint discovery/ordering, the ranking key, and the exit
contract. Scoring itself delegates to sim2real_probe, which has its own tests,
so it is not re-tested here.
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO / "tools"))

import select_sim2real_checkpoint as sel  # noqa: E402


def _touch(directory: Path, name: str) -> Path:
    p = directory / name
    p.write_bytes(b"")
    return p


# --- checkpoint discovery ---------------------------------------------------


def test_checkpoints_are_found_and_ordered_numerically(tmp_path):
    """Lexicographic ordering would put 100000 before 25000."""
    for steps in (25000, 100000, 50000, 1000000, 225000):
        _touch(tmp_path, f"run_a_{steps}_steps.zip")
    found = sel.find_checkpoints(tmp_path, "run_a", 1)
    assert [sel._checkpoint_steps(p) for p in found] == [
        25000, 50000, 100000, 225000, 1000000
    ]


def test_other_runs_and_stray_files_are_ignored(tmp_path):
    _touch(tmp_path, "run_a_25000_steps.zip")
    _touch(tmp_path, "run_b_25000_steps.zip")
    _touch(tmp_path, "run_a_vecnormalize_25000_steps.pkl")
    _touch(tmp_path, "run_a_final.zip")
    found = sel.find_checkpoints(tmp_path, "run_a", 1)
    assert [p.name for p in found] == ["run_a_25000_steps.zip"]


def test_every_thins_the_candidate_list(tmp_path):
    for steps in range(25000, 250001, 25000):
        _touch(tmp_path, f"run_a_{steps}_steps.zip")
    every_four = sel.find_checkpoints(tmp_path, "run_a", 4)
    assert [sel._checkpoint_steps(p) for p in every_four] == [100000, 200000]
    assert len(sel.find_checkpoints(tmp_path, "run_a", 1)) == 10


# --- the ranking key --------------------------------------------------------


def _rec(steps, *, swing=0.2, retention=0.6, bias_ratio=0.5, right=0.4, sign=True,
         canonical_swing=0.4):
    return {
        "steps": steps,
        "arms": {
            "canonical": {"swing": canonical_swing},
            "hall+lens+rect": {
                "swing": swing,
                "retention_vs_canonical": retention,
                "bias_over_swing": bias_ratio,
                "right_fraction": right,
                "sign_correct": sign,
            },
        },
    }


ARM = "hall+lens+rect"


def test_a_wrong_sign_never_outranks_a_correct_one():
    """Steering away from the lane is not a weak response, it is the wrong one:
    no magnitude of it may outrank a correct response."""
    wrong = _rec(1, swing=0.9, retention=0.99, bias_ratio=0.01, right=0.5, sign=False)
    right_but_weak = _rec(2, swing=0.02, retention=0.05, bias_ratio=0.9, right=0.11,
                          sign=True)
    assert sel.rank_key(right_but_weak, ARM) > sel.rank_key(wrong, ARM)


def test_clearing_the_floors_outranks_higher_retention_that_does_not():
    cleared = _rec(1, retention=0.55, bias_ratio=0.9, right=0.2)
    blocked_by_bias = _rec(2, retention=0.95, bias_ratio=1.5, right=0.2)
    assert sel.rank_key(cleared, ARM) > sel.rank_key(blocked_by_bias, ARM)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"retention": sel.MIN_RETENTION - 0.01},
        {"bias_ratio": sel.MAX_BIAS_RATIO + 0.01},
        {"right": sel.MIN_RIGHT_FRACTION - 0.01},
        {"sign": False},
        {"canonical_swing": sel.MIN_CANONICAL_SWING - 0.01},
    ],
)
def test_each_floor_alone_blocks(kwargs):
    assert sel.rank_key(_rec(1, **kwargs), ARM)[1] == 0


def test_absolute_swing_orders_within_the_cleared_group():
    """Not retention: both arms come from the same checkpoint, so a collapsed
    canonical arm flatters a weak one."""
    a = _rec(1, swing=0.20)
    b = _rec(2, swing=0.30)
    assert sel.rank_key(b, ARM) > sel.rank_key(a, ARM)


def test_a_collapsed_control_arm_cannot_be_promoted_by_its_own_weakness():
    """The defect this floor exists for, from a real run: a checkpoint scored
    304 % 'retention' because its canonical swing had collapsed to 0.067, and it
    outranked genuinely responsive checkpoints. Retention above 100 % is not
    possible by the metric's own definition; it is a division artefact."""
    collapsed = _rec(1, swing=0.20, retention=3.04, canonical_swing=0.067)
    responsive = _rec(2, swing=0.19, retention=0.55, canonical_swing=0.40)
    assert sel.rank_key(responsive, ARM) > sel.rank_key(collapsed, ARM)
    assert sel.rank_key(collapsed, ARM)[0] == 0


def test_an_untrained_noisy_policy_is_not_ranked():
    """A near-random policy scores a large swing because its steering is noisy.
    Swing does not distinguish that from a lane response, so the control-arm
    floor must keep it out of the table entirely."""
    noisy = _rec(25000, swing=0.89, retention=1.19, canonical_swing=0.10)
    assert sel.rank_key(noisy, ARM)[0] == 0


def test_wrong_sign_is_never_ranked_at_all():
    assert sel.rank_key(_rec(1, sign=False, swing=0.9), ARM) == (0, 0, 0.0)


def test_a_missing_arm_ranks_last_and_does_not_raise():
    assert sel.rank_key({"steps": 1, "arms": {}}, ARM) == (0, 0, 0.0)


def test_floors_match_the_probe_gate():
    """The ranking floors are the probe's thresholds on purpose: a checkpoint
    that tops this table is one that could plausibly clear the real gate. If the
    probe's gate moves, this must move with it."""
    import sim2real_probe as probe

    assert sel.MIN_RETENTION == probe.MIN_SWING_RETENTION
    assert sel.MAX_BIAS_RATIO == probe.MAX_BIAS_RATIO
    assert sel.MIN_RIGHT_FRACTION == probe.MIN_RIGHT_FRACTION


def test_hall_level_matches_the_calibrated_operating_point():
    """0.75 is where apply_low_contrast reproduces the measured hall; if that
    calibration is revised the surrogate arm must follow it."""
    from cobraflex_rl.visual_degradation import apply_low_contrast  # noqa: F401

    assert sel.HALL_LEVEL == 0.75


# --- exit contract ----------------------------------------------------------


def test_missing_checkpoints_is_invalid(tmp_path, capsys):
    assert sel.main([
        "--prefix", "nothing_here",
        "--checkpoint-dir", str(tmp_path),
        "--sim-frames", str(tmp_path),
    ]) == 1


def test_missing_sim_frames_is_invalid(tmp_path):
    _touch(tmp_path, "run_a_25000_steps.zip")
    assert sel.main([
        "--prefix", "run_a",
        "--checkpoint-dir", str(tmp_path),
        "--sim-frames", str(tmp_path / "no_such_dir"),
    ]) == 1


def test_a_resumed_run_is_ranked_as_one_continuous_series(tmp_path):
    """The v2 run was killed at 620,544 and resumed from its 600k checkpoint under
    the run id `..._r2` (INCIDENTS.md I-6). Both segments are one lineage and must
    be scored together: the parent's checkpoints end at 600k and the resumed ones
    begin at 625k, so they concatenate without overlap. An unrelated run sharing
    a prefix stem must still be excluded."""
    for steps in (575000, 600000):
        _touch(tmp_path, f"ppo_gz2d_sim2real_v2_2024_{steps}_steps.zip")
    for steps in (625000, 650000):
        _touch(tmp_path, f"ppo_gz2d_sim2real_v2_2024_r2_{steps}_steps.zip")
    _touch(tmp_path, "ppo_gz2d_sim2real_ft_2024_600000_steps.zip")

    found = sel.find_checkpoints(tmp_path, "ppo_gz2d_sim2real_v2_2024", 1)
    assert [sel._checkpoint_steps(p) for p in found] == [
        575000, 600000, 625000, 650000
    ]
    assert not any("ft_2024" in p.name for p in found)


# --- the driving filter (training ep_len) -----------------------------------


def test_episode_lengths_concatenates_the_segments_of_a_resumed_run(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    a.write_text("timestep,ep_len_mean\n1024,40\n2048,90\n")
    b.write_text("timestep,ep_len_mean\n3072,500\n4096,700\n")
    assert sel.episode_lengths([a, b]) == [
        (1024.0, 40.0), (2048.0, 90.0), (3072.0, 500.0), (4096.0, 700.0)
    ]


def test_episode_lengths_tolerates_a_missing_or_malformed_curve(tmp_path):
    good = tmp_path / "g.csv"
    good.write_text("timestep,ep_len_mean\n1024,40\nbad,rows\n")
    assert sel.episode_lengths([good, tmp_path / "absent.csv"]) == [(1024.0, 40.0)]


def test_ep_len_at_takes_the_last_value_at_or_before_the_step():
    lengths = [(1024.0, 40.0), (2048.0, 90.0), (3072.0, 500.0)]
    assert sel.ep_len_at(2048, lengths) == 90.0
    assert sel.ep_len_at(2500, lengths) == 90.0
    assert sel.ep_len_at(3072, lengths) == 500.0


def test_ep_len_at_returns_none_before_any_coverage():
    """An unknown must not read as a rejection."""
    assert sel.ep_len_at(100, [(1024.0, 40.0)]) is None


def test_a_checkpoint_from_a_non_driving_era_is_not_ranked():
    """The defect this filter exists for: the 25k checkpoint of the v2 run
    scored the highest swing of all 40 (0.892) while its training episodes
    averaged 34 steps. Its steering was noise, and neither swing nor r_squared
    separates noise from a lane response."""
    noisy = _rec(25000, swing=0.892, canonical_swing=0.747)
    noisy["training_ep_len"] = 34.0
    assert sel.rank_key(noisy, ARM)[0] == 0


def test_a_driving_era_checkpoint_is_ranked():
    driving = _rec(150000, swing=0.644, canonical_swing=0.598)
    driving["training_ep_len"] = 765.0
    assert sel.rank_key(driving, ARM)[0] == 1


def test_without_a_learning_curve_the_filter_is_inert():
    """No `--learning-curve` means no `training_ep_len`, and an absent datum must
    not silently reject every candidate."""
    rec = _rec(25000, swing=0.892, canonical_swing=0.747)
    assert "training_ep_len" not in rec
    assert sel.rank_key(rec, ARM)[0] == 1
