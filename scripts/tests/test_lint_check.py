"""
TDD — fix #9: Phase 13 linter must use ruff (Python) + eslint (Node), not a
homegrown grep+ast heuristic.
Old bug: POSIX-only `grep`, O(funcs*files), and a "name appears <2x => dead"
heuristic that false-positives on public API, methods, dynamic calls.
New: detect real linters, build cross-platform commands (python -m ruff), parse
their output, and report lint issues as WARNINGS only (never fail the gate).
Graceful skip when no linter is installed.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lint_check import (
    _detect_python_linter,
    _detect_node_linter,
    _build_lint_command,
    _parse_ruff_output,
    _parse_eslint_output,
    _lint_verdict,
)


# ── Python linter detection ───────────────────────────────────────────────────

def test_detect_python_prefers_ruff():
    find = lambda name: object() if name == "ruff" else None
    which = lambda name: None
    assert _detect_python_linter(find, which) == "ruff"


def test_detect_python_falls_back_to_pyflakes():
    find = lambda name: object() if name == "pyflakes" else None
    which = lambda name: None
    assert _detect_python_linter(find, which) == "pyflakes"


def test_detect_python_pyflakes_via_path_only():
    find = lambda name: None
    which = lambda name: "/usr/bin/pyflakes" if name == "pyflakes" else None
    assert _detect_python_linter(find, which) == "pyflakes"


def test_detect_python_none_when_nothing_installed():
    find = lambda name: None
    which = lambda name: None
    assert _detect_python_linter(find, which) is None


# ── Node linter detection ─────────────────────────────────────────────────────

def test_detect_node_prefers_local_eslint():
    local = os.path.join("node_modules", ".bin", "eslint")
    which = lambda name: None
    exists = lambda p: p == local
    assert _detect_node_linter(which, exists) == local


def test_detect_node_global_eslint():
    which = lambda name: "/usr/bin/eslint" if name == "eslint" else None
    exists = lambda p: False
    assert _detect_node_linter(which, exists) == "eslint"


def test_detect_node_npx_fallback():
    which = lambda name: "/usr/bin/npx" if name == "npx" else None
    exists = lambda p: False
    assert _detect_node_linter(which, exists) == "npx"


def test_detect_node_none():
    which = lambda name: None
    exists = lambda p: False
    assert _detect_node_linter(which, exists) is None


# ── Command building (cross-platform) ─────────────────────────────────────────

def test_build_ruff_command_uses_python_module():
    cmd = _build_lint_command("ruff", ["a.py", "b.py"], python_exe="PY")
    assert cmd == ["PY", "-m", "ruff", "check", "a.py", "b.py"]


def test_build_pyflakes_command_uses_python_module():
    cmd = _build_lint_command("pyflakes", ["a.py"], python_exe="PY")
    assert cmd == ["PY", "-m", "pyflakes", "a.py"]


def test_build_npx_command():
    cmd = _build_lint_command("npx", ["x.js"])
    assert cmd == ["npx", "--no-install", "eslint", "x.js"]


def test_build_eslint_command_direct_path():
    local = os.path.join("node_modules", ".bin", "eslint")
    cmd = _build_lint_command(local, ["x.js", "y.js"])
    assert cmd == [local, "x.js", "y.js"]


# ── Output parsing ────────────────────────────────────────────────────────────

def test_parse_ruff_summary():
    assert _parse_ruff_output("a.py:1:1: F401 unused\nFound 3 errors.") == 3


def test_parse_ruff_clean():
    assert _parse_ruff_output("All checks passed!") == 0


def test_parse_ruff_no_summary_counts_lines():
    out = "a.py:1:1: F401 x\na.py:2:5: F841 y"
    assert _parse_ruff_output(out) == 2


def test_parse_eslint_summary():
    out = "/x.js\n  1:1  error  no-undef\n\n✖ 5 problems (2 errors, 3 warnings)"
    assert _parse_eslint_output(out) == (2, 3)


def test_parse_eslint_clean():
    assert _parse_eslint_output("") == (0, 0)


# ── Verdict: WARN only, never FAIL ────────────────────────────────────────────

def test_verdict_skip_when_no_linter_ran():
    v = _lint_verdict(total_issues=0, ran=False)
    assert "SKIP" in v
    assert "❌" not in v


def test_verdict_pass_when_clean():
    v = _lint_verdict(total_issues=0, ran=True)
    assert "PASS" in v or "✅" in v
    assert "❌" not in v


def test_verdict_warn_with_issues_never_fails():
    v = _lint_verdict(total_issues=7, ran=True)
    assert "7" in v
    assert "❌" not in v  # lint never blocks the gate


def test_verdict_never_returns_fail_marker():
    for issues in (0, 1, 100):
        for ran in (True, False):
            assert "❌" not in _lint_verdict(issues, ran)
