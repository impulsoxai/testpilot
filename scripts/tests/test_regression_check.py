"""
TDD — fix #13b: Phase 4 regression detection as a real script (was POSIX-only
bash: /tmp, [ -f ], diff, grep, cp).
A regression = a test that PASSED in the previous run and now FAILS/ERRORS.
New failures (never passed) are not regressions (Phase 2 catches those). Missing
tests are not regressions (rename/refactor). Baseline stored as JSON (not /tmp),
cross-platform. A regression FAILS the phase.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from regression_check import (
    _parse_test_statuses,
    _find_regressions,
    _find_newly_passing,
    _regression_verdict,
    _load_baseline,
    _save_baseline,
)


# ── Parsing pytest -v output ──────────────────────────────────────────────────

def test_parse_statuses_basic():
    out = (
        "tests/test_a.py::test_one PASSED\n"
        "tests/test_a.py::test_two FAILED\n"
        "tests/test_b.py::test_three PASSED\n"
    )
    assert _parse_test_statuses(out) == {
        "tests/test_a.py::test_one": "PASSED",
        "tests/test_a.py::test_two": "FAILED",
        "tests/test_b.py::test_three": "PASSED",
    }


def test_parse_statuses_with_error_and_percentages():
    out = (
        "tests/test_a.py::test_one PASSED                 [ 50%]\n"
        "tests/test_a.py::test_boom ERROR                 [100%]\n"
    )
    parsed = _parse_test_statuses(out)
    assert parsed["tests/test_a.py::test_one"] == "PASSED"
    assert parsed["tests/test_a.py::test_boom"] == "ERROR"


def test_parse_statuses_ignores_non_test_lines():
    out = "============ test session starts ============\nrootdir: /x\n5 passed in 1s\n"
    assert _parse_test_statuses(out) == {}


# ── Regression detection (PASSED -> FAILED/ERROR only) ────────────────────────

def test_regression_passed_then_failed():
    prev = {"t::a": "PASSED", "t::b": "PASSED"}
    curr = {"t::a": "PASSED", "t::b": "FAILED"}
    assert _find_regressions(prev, curr) == ["t::b"]


def test_regression_passed_then_error():
    prev = {"t::a": "PASSED"}
    curr = {"t::a": "ERROR"}
    assert _find_regressions(prev, curr) == ["t::a"]


def test_new_failure_not_a_regression():
    """A test that never passed before is a new failure, not a regression."""
    prev = {"t::a": "PASSED"}
    curr = {"t::a": "PASSED", "t::new": "FAILED"}
    assert _find_regressions(prev, curr) == []


def test_still_failing_not_a_regression():
    prev = {"t::a": "FAILED"}
    curr = {"t::a": "FAILED"}
    assert _find_regressions(prev, curr) == []


def test_fixed_test_not_a_regression():
    prev = {"t::a": "FAILED"}
    curr = {"t::a": "PASSED"}
    assert _find_regressions(prev, curr) == []


def test_missing_test_not_a_regression():
    """A test removed/renamed is not flagged (avoids refactor noise)."""
    prev = {"t::a": "PASSED", "t::gone": "PASSED"}
    curr = {"t::a": "PASSED"}
    assert _find_regressions(prev, curr) == []


def test_multiple_regressions_sorted():
    prev = {"t::z": "PASSED", "t::a": "PASSED", "t::m": "PASSED"}
    curr = {"t::z": "FAILED", "t::a": "FAILED", "t::m": "PASSED"}
    assert _find_regressions(prev, curr) == ["t::a", "t::z"]


# ── Newly passing (informational) ─────────────────────────────────────────────

def test_newly_passing():
    prev = {"t::a": "FAILED", "t::b": "PASSED"}
    curr = {"t::a": "PASSED", "t::b": "PASSED"}
    assert _find_newly_passing(prev, curr) == ["t::a"]


# ── Verdict ───────────────────────────────────────────────────────────────────

def test_verdict_no_baseline():
    v = _regression_verdict([], had_baseline=False)
    assert "❌" not in v
    assert "baseline" in v.lower() or "primeira" in v.lower()


def test_verdict_clean():
    v = _regression_verdict([], had_baseline=True)
    assert "✅" in v or "PASS" in v
    assert "❌" not in v


def test_verdict_regressions_fail():
    v = _regression_verdict(["t::a", "t::b"], had_baseline=True)
    assert "❌" in v
    assert "2" in v


# ── Baseline persistence (JSON, not /tmp) ─────────────────────────────────────

def test_baseline_roundtrip(tmp_path):
    f = tmp_path / "reports" / "last_run.json"
    statuses = {"t::a": "PASSED", "t::b": "FAILED"}
    _save_baseline(f, statuses)
    assert _load_baseline(f) == statuses


def test_load_baseline_missing_returns_none(tmp_path):
    assert _load_baseline(tmp_path / "nope.json") is None
