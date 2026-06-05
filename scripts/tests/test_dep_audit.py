"""
TDD — fix #10a: dependency-vulnerability gate (pip-audit / npm audit).
Lacuna: a known CVE in requirements.txt/package.json passed the suite untouched.
This gate FAILS the phase (not just warns) when a vulnerability at/above the
configured level is found. npm thresholds by severity (AUDIT_FAIL_LEVEL, default
high); pip-audit has no reliable native severity, so Python fails on ANY vuln,
with AUDIT_IGNORE to accept specific advisory IDs. Tool missing -> SKIP.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dep_audit import (
    NPM_LEVELS,
    DEFAULT_FAIL_LEVEL,
    _get_fail_level,
    _parse_ignore,
    _build_npm_audit_command,
    _build_pip_audit_command,
    _parse_npm_audit,
    _npm_exceeds,
    _parse_pip_audit,
    _audit_verdict,
)


# ── Config from environment ───────────────────────────────────────────────────

def test_fail_level_default_is_high():
    assert _get_fail_level({}) == "high"
    assert DEFAULT_FAIL_LEVEL == "high"


def test_fail_level_override():
    assert _get_fail_level({"AUDIT_FAIL_LEVEL": "critical"}) == "critical"
    assert _get_fail_level({"AUDIT_FAIL_LEVEL": "Moderate"}) == "moderate"


def test_fail_level_invalid_falls_back_to_default():
    assert _get_fail_level({"AUDIT_FAIL_LEVEL": "bogus"}) == "high"


def test_parse_ignore_empty():
    assert _parse_ignore({}) == set()
    assert _parse_ignore({"AUDIT_IGNORE": ""}) == set()


def test_parse_ignore_comma_separated_with_whitespace():
    assert _parse_ignore({"AUDIT_IGNORE": "GHSA-1, GHSA-2 ,PYSEC-3"}) == {"GHSA-1", "GHSA-2", "PYSEC-3"}


# ── Command building ──────────────────────────────────────────────────────────

def test_build_npm_audit_command():
    assert _build_npm_audit_command("high") == ["npm", "audit", "--json", "--audit-level=high"]


def test_build_pip_audit_command_uses_module():
    cmd = _build_pip_audit_command(python_exe="PY")
    assert cmd == ["PY", "-m", "pip_audit", "--format", "json"]


# ── npm audit parsing + threshold ─────────────────────────────────────────────

def test_parse_npm_audit_counts():
    text = '{"metadata":{"vulnerabilities":{"info":0,"low":2,"moderate":1,"high":3,"critical":0,"total":6}}}'
    counts = _parse_npm_audit(text)
    assert counts["high"] == 3
    assert counts["low"] == 2
    assert counts["critical"] == 0


def test_parse_npm_audit_empty():
    counts = _parse_npm_audit('{"metadata":{"vulnerabilities":{}}}')
    assert all(counts[level] == 0 for level in NPM_LEVELS)


def test_npm_exceeds_high_when_high_present():
    counts = {"info": 0, "low": 5, "moderate": 2, "high": 1, "critical": 0}
    assert _npm_exceeds(counts, "high") is True


def test_npm_exceeds_high_when_only_critical():
    counts = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 1}
    assert _npm_exceeds(counts, "high") is True


def test_npm_exceeds_high_false_when_only_moderate():
    counts = {"info": 0, "low": 9, "moderate": 4, "high": 0, "critical": 0}
    assert _npm_exceeds(counts, "high") is False


def test_npm_exceeds_moderate_true_when_moderate():
    counts = {"info": 0, "low": 0, "moderate": 1, "high": 0, "critical": 0}
    assert _npm_exceeds(counts, "moderate") is True


def test_npm_exceeds_clean():
    counts = {"info": 3, "low": 0, "moderate": 0, "high": 0, "critical": 0}
    assert _npm_exceeds(counts, "high") is False


# ── pip-audit parsing (fail on ANY, with ignore) ──────────────────────────────

def test_parse_pip_audit_dependencies_format():
    text = '{"dependencies":[{"name":"flask","version":"1.0","vulns":[{"id":"PYSEC-1"}]},{"name":"requests","version":"2.0","vulns":[]}]}'
    assert _parse_pip_audit(text, ignore=set()) == 1


def test_parse_pip_audit_bare_list_format():
    text = '[{"name":"flask","version":"1.0","vulns":[{"id":"PYSEC-1"},{"id":"PYSEC-2"}]}]'
    assert _parse_pip_audit(text, ignore=set()) == 2


def test_parse_pip_audit_ignore_filters():
    text = '{"dependencies":[{"name":"flask","version":"1.0","vulns":[{"id":"PYSEC-1"},{"id":"PYSEC-2"}]}]}'
    assert _parse_pip_audit(text, ignore={"PYSEC-1"}) == 1
    assert _parse_pip_audit(text, ignore={"PYSEC-1", "PYSEC-2"}) == 0


def test_parse_pip_audit_no_vulns():
    text = '{"dependencies":[{"name":"flask","version":"1.0","vulns":[]}]}'
    assert _parse_pip_audit(text, ignore=set()) == 0


# ── Verdict ───────────────────────────────────────────────────────────────────

def test_verdict_skip_when_not_ran():
    v = _audit_verdict(failed=False, ran=False)
    assert "SKIP" in v
    assert "❌" not in v


def test_verdict_pass_when_clean():
    v = _audit_verdict(failed=False, ran=True)
    assert "✅" in v or "PASS" in v
    assert "❌" not in v


def test_verdict_fail_when_vulns():
    v = _audit_verdict(failed=True, ran=True)
    assert "❌" in v
