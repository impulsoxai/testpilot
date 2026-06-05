"""
TDD — fix #4a: guard against false-GREEN when the security target route is wrong.
Bug: REST mode hits hardcoded /test. Real API → 404 on every payload → no 500,
no stack trace → issues={} → verdict PASS. Gate approves without testing anything.
Fix: if every probe returns 404/405, the target is unreachable → CONFIG ERROR,
never PASS.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from security_test import (
    _is_unreachable,
    UNREACHABLE_STATUSES,
    CONFIG_ERROR_CATEGORY,
    get_security_verdict,
    Severity,
)


# ── _is_unreachable: all probes hit a missing route ───────────────────────────

def test_all_404_is_unreachable():
    """Every probe returned 404 → target route does not exist."""
    assert _is_unreachable([404, 404, 404, 404, 404]) is True


def test_all_405_is_unreachable():
    """Every probe returned 405 (method not allowed) → wrong method/route."""
    assert _is_unreachable([405, 405, 405]) is True


def test_mixed_404_405_is_unreachable():
    """Mix of 404/405 only → still unreachable."""
    assert _is_unreachable([404, 405, 404, 405]) is True


def test_some_200_not_unreachable():
    """At least one real response → route exists, not a config error."""
    assert _is_unreachable([404, 200, 404]) is False


def test_all_200_not_unreachable():
    assert _is_unreachable([200, 200, 200]) is False


def test_500_not_unreachable():
    """500 means the route exists and broke — that's a real finding, not config."""
    assert _is_unreachable([500, 500]) is False


def test_empty_list_not_unreachable():
    """No responses captured (e.g. all connection errors) → not a 404 guard case."""
    assert _is_unreachable([]) is False


def test_unreachable_statuses_constant():
    """404 and 405 are the missing-route markers."""
    assert 404 in UNREACHABLE_STATUSES
    assert 405 in UNREACHABLE_STATUSES
    assert 200 not in UNREACHABLE_STATUSES


# ── verdict: config error must NOT be PASS ────────────────────────────────────

def test_verdict_config_error_is_not_pass():
    """When a CONFIG_ERROR is present, verdict must not be PASS."""
    issues = {
        CONFIG_ERROR_CATEGORY: [{
            "payload": "N/A",
            "issue": "All probes returned 404 — target route not found",
            "severity": Severity.CRITICAL,
        }]
    }
    verdict = get_security_verdict(issues)
    assert "PASS" not in verdict
    assert "ERRO" in verdict or "ERROR" in verdict


def test_verdict_empty_issues_is_pass():
    """No issues and no config error → genuine PASS (regression guard)."""
    assert get_security_verdict({}) == "✅ PASS"


def test_verdict_config_error_takes_priority_over_findings():
    """Config error reported even if other categories also have issues."""
    issues = {
        CONFIG_ERROR_CATEGORY: [{
            "payload": "N/A",
            "issue": "unreachable",
            "severity": Severity.CRITICAL,
        }],
        "sql_injection": [{
            "payload": "x",
            "issue": "db error",
            "severity": Severity.WARNING,
        }],
    }
    verdict = get_security_verdict(issues)
    assert "PASS" not in verdict
    assert "ERRO" in verdict or "ERROR" in verdict
