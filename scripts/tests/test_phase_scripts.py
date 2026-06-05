"""
TDD — fix #13a: SKILL.md must call the existing standalone scripts, not carry a
stale inline duplicate of their logic.
Phases 5 (contract), 8 (rate limit) and 11 (performance) already have scripts
(contract_test.py, rate_limit_check.py, load_test.py) but the markdown still
embedded the old inline code, guaranteeing drift. Phase 5/11 must point to the
script; Phase 8's "Or inline" duplicate must be gone.
"""

import os

SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "SKILL.md")


def _skill_text() -> str:
    with open(SKILL, encoding="utf-8") as f:
        return f.read()


# ── Phase 5 — Contract ────────────────────────────────────────────────────────

def test_phase5_calls_contract_script():
    assert "scripts/contract_test.py" in _skill_text()


def test_phase5_no_inline_check_contracts():
    """The inline def check_contracts() duplicate must be removed."""
    assert "def check_contracts" not in _skill_text()


# ── Phase 8 — Rate Limiting ───────────────────────────────────────────────────

def test_phase8_calls_rate_limit_script():
    assert "scripts/rate_limit_check.py" in _skill_text()


def test_phase8_no_inline_110_loop():
    """The inline 'for i in range(110)' rate-limit duplicate must be removed."""
    assert "range(110)" not in _skill_text()


def test_phase8_no_or_inline_marker():
    assert "Or inline:" not in _skill_text()


# ── Phase 4 — Regression ──────────────────────────────────────────────────────

def test_phase4_calls_regression_script():
    assert "scripts/regression_check.py" in _skill_text()


def test_phase4_no_posix_bash_diff():
    """The POSIX-only diff|grep / /tmp / [ -f ] regression bash must be removed."""
    text = _skill_text()
    assert "/tmp/current_run.txt" not in text
    assert "tests/reports/last_run.txt" not in text


# ── Phase 11 — Performance ────────────────────────────────────────────────────

def test_phase11_calls_load_test_script():
    assert "scripts/load_test.py" in _skill_text()


def test_phase11_no_inline_run_load_test():
    """The inline async def run_load_test duplicate must be removed."""
    assert "async def run_load_test" not in _skill_text()
