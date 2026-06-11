"""
Unit tests for cobraflex_rl.run_io — the pure hashing / git-commit helpers used
to write reproducible training (§7.2.8) and evaluation (§7.5) run metadata.
"""

import sys
from pathlib import Path

_PKG_PARENT = Path(__file__).resolve().parents[2] / "src" / "cobraflex_rl"
if str(_PKG_PARENT) not in sys.path:
    sys.path.insert(0, str(_PKG_PARENT))

from cobraflex_rl.run_io import git_commit, sha256_file  # noqa: E402


def test_sha256_known_value(tmp_path):
    target = tmp_path / "x.txt"
    target.write_bytes(b"abc")
    # Well-known: sha256("abc")
    assert sha256_file(target) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_sha256_missing_returns_none(tmp_path):
    assert sha256_file(tmp_path / "does_not_exist.bin") is None


def test_git_commit_returns_nonempty_string():
    # Inside this repo it returns a hash; anywhere else, the literal "unknown".
    out = git_commit(Path(__file__).resolve().parent)
    assert isinstance(out, str) and out != ""
