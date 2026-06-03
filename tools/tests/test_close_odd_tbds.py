"""Unit tests for ``tools/close_odd_tbds.py``.

These pin the *hardened* substitution contract (added 2026-06-03): the tool
must only rewrite **designated placeholders** — a ``TBD-QN`` token that is the
sole content of a Markdown table cell, or a still-blank §11 ``Resolution``
cell — and must leave *prose mentions* of already-closed TBDs intact. This is
what keeps a re-run idempotent instead of corrupting the §0.1 change log
("F1 partial closure of TBD-Q1 …") and the §9 source column ("closes TBD-Q8").
See D-33 and the 03.06 "ODD-2 adverse stressor profiles" CHANGELOG entry.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# The script imports PyYAML at module load; skip the whole module if it is
# unavailable rather than erroring (the repo depends on it, but tests stay
# graceful in a yaml-less environment).
pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = REPO_ROOT / "tools" / "close_odd_tbds.py"

# Load the script by path: `tools/` is not an importable package.
_spec = importlib.util.spec_from_file_location("close_odd_tbds", _MODULE_PATH)
assert _spec and _spec.loader
codt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codt)


# =============================================================
# substitute_in_body — only sole-content table cells
# =============================================================

def test_sole_cell_placeholders_are_substituted():
    """A `TBD-QN` that is the only content of a table cell IS filled."""
    resolved = {"TBD-Q10": {"value": 0.078}}
    # §9 `*.A_LAT_MAX` row shape: two adjacent placeholder cells (ODD-3, ODD-4).
    body = "| `*.A_LAT_MAX` | accel (m/s²) | 9.81 | 9.81 | TBD-Q10 | TBD-Q10 | derived; deferred |"
    out = codt.substitute_in_body(body, resolved)
    assert "| 9.81 | 9.81 | 0.078 | 0.078 | derived; deferred |" in out
    assert "TBD-Q10" not in out


def test_prose_mentions_are_left_intact():
    """Prose mentions of resolved TBDs must NOT be rewritten."""
    resolved = {"TBD-Q8": {"value": 8.0232}, "TBD-Q1": {"value": 1.0}}
    body = "\n".join([
        # §9 source column: the TBD tag trails real prose inside the cell.
        "| `*.ROAD_LENGTH` | len (m) | 10 | 10 | 8.0232 | 8.0232 | composer preset; closes TBD-Q8 |",
        # §0.1 change-log cell: TBD tags embedded mid-sentence.
        "| 0.2 | 2026-05-14 | SS | F1 partial closure of TBD-Q1 (FRICTION = 1.0). |",
        # §5.5 prose paragraph (no table at all).
        "the table below mirrors it. Closes TBD-Q4–Q7 (D-33, F4 entry).",
    ])
    out = codt.substitute_in_body(body, resolved)
    assert out == body  # nothing changed
    # And specifically: no resolved value leaked into the prose.
    assert "closes 8.0232" not in out
    assert "F1 partial closure of 1.0" not in out


def test_unresolved_placeholder_is_kept():
    """A sole-content cell for a still-null TBD keeps its placeholder."""
    body = "| x | TBD-Q10 | y |"
    assert codt.substitute_in_body(body, resolved={}) == body


def test_substitution_is_idempotent():
    """Re-substituting an already-filled body is a no-op."""
    resolved = {"TBD-Q10": {"value": 0.078}}
    body = "| a | b | TBD-Q10 | TBD-Q10 | c |"
    once = codt.substitute_in_body(body, resolved)
    twice = codt.substitute_in_body(once, resolved)
    assert "TBD-Q10" not in once
    assert once == twice


# =============================================================
# update_resolution_table — fill blanks only
# =============================================================

_SECTION_HEAD = [
    "## 11. Open issues and TBDs",
    "",
    "| Tag | Question | Owner | Target close | Resolution |",
    "| --- | -------- | ----- | ------------ | ---------- |",
]


def test_resolution_table_fills_blank_cell():
    resolved = {"TBD-Q4": {
        "value": "stress profile",
        "source": "adverse_profiles.yaml",
        "notes": "F4 closure",
    }}
    section = "\n".join(_SECTION_HEAD + [
        "| TBD-Q4 | what stressors? | SS | D11 PM | |",
    ])
    out = codt.update_resolution_table(section, resolved, "2026-06-03")
    assert "stress profile (adverse_profiles.yaml) -- 2026-06-03 [F4 closure]" in out


def test_resolution_table_preserves_handwritten_closure():
    """An already-written resolution is never re-dated or reformatted."""
    resolved = {"TBD-Q4": {
        "value": "stress profile",
        "source": "adverse_profiles.yaml",
        "notes": "F4 closure",
    }}
    handwritten = (
        "| TBD-Q4 | what stressors? | SS | D11 PM | "
        "faded markings; σ_lateral = 0.03 m -- 2026-06-03 [by hand] |"
    )
    section = "\n".join(_SECTION_HEAD + [handwritten])
    out = codt.update_resolution_table(section, resolved, "2099-01-01")
    assert out == section            # unchanged, even with a different `today`
    assert "stress profile" not in out


# =============================================================
# patch_odd_spec — end-to-end idempotency on the live ODD-Spec
# =============================================================

def test_real_odd_spec_reapply_is_noop():
    """Re-running against the live, fully-closed ODD-Spec changes nothing.

    Regression guard for the corruption confirmed on 2026-06-03: a blanket
    re-run rewrote prose mentions of closed TBDs (§0.1 change log, §9 source
    column) and re-dated the hand-written §11 resolutions.
    """
    data = codt.load_yaml(codt.DEFAULT_YAML)
    resolved = codt.collect_resolved(data["tbds"])
    original = codt.load_text(codt.DEFAULT_ODD_SPEC)
    patched = codt.patch_odd_spec(original, resolved, "2026-06-03")
    assert patched == original
