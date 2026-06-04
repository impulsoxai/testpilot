"""
TDD — fix #8: SQL injection detection must use real signals, not status 200.
Bug: any 200 response to SQL payload flagged as 'Possible SQL injection'
(mass false positives — 200 is the CORRECT response when input is sanitized).
Fix: check for DB error strings in body AND response time > 3s.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from security_test import _check_sql_injection_signals, SLOW_REQUEST_THRESHOLD_S


# ── 200 alone must NOT be flagged ─────────────────────────────────────────────

def test_200_with_clean_body_no_issues():
    """Status 200 + clean response body → no SQL injection signal."""
    issues = _check_sql_injection_signals(
        response_text='{"result": "ok"}',
        elapsed_s=0.05,
        payload_repr="'; DROP TABLE users; --",
    )
    assert issues == []


def test_200_with_html_body_no_issues():
    """HTML 200 page with no DB error markers → no issues."""
    issues = _check_sql_injection_signals(
        response_text="<html><body>Input inválido</body></html>",
        elapsed_s=0.10,
        payload_repr="' OR 1=1 --",
    )
    assert issues == []


# ── DB error markers → WARNING ────────────────────────────────────────────────

def test_mysql_error_in_body_flagged():
    """MySQL error string in body → WARNING."""
    issues = _check_sql_injection_signals(
        response_text="You have an error in your SQL syntax near 'DROP'",
        elapsed_s=0.05,
        payload_repr="'; DROP TABLE users; --",
    )
    assert len(issues) == 1
    assert issues[0]["severity"].value == "warning"
    assert "sql" in issues[0]["issue"].lower() or "database" in issues[0]["issue"].lower()


def test_postgresql_error_in_body_flagged():
    issues = _check_sql_injection_signals(
        response_text="pg::SyntaxError: syntax error at or near 'DROP'",
        elapsed_s=0.05,
        payload_repr="test",
    )
    assert len(issues) >= 1


def test_sqlite_error_in_body_flagged():
    issues = _check_sql_injection_signals(
        response_text="sqlite3.OperationalError: near 'DROP': syntax error",
        elapsed_s=0.05,
        payload_repr="test",
    )
    assert len(issues) >= 1


def test_oracle_error_in_body_flagged():
    issues = _check_sql_injection_signals(
        response_text="ORA-00942: table or view does not exist",
        elapsed_s=0.05,
        payload_repr="test",
    )
    assert len(issues) >= 1


def test_mssql_error_in_body_flagged():
    issues = _check_sql_injection_signals(
        response_text="Unclosed quotation mark after the character string",
        elapsed_s=0.05,
        payload_repr="test",
    )
    assert len(issues) >= 1


def test_db_error_check_is_case_insensitive():
    """Detection must be case-insensitive (servers vary in error casing)."""
    issues = _check_sql_injection_signals(
        response_text="SQL SYNTAX ERROR NEAR 'UNION'",
        elapsed_s=0.05,
        payload_repr="test",
    )
    assert len(issues) >= 1


# ── Slow response → WARNING ───────────────────────────────────────────────────

def test_slow_response_flagged():
    """Response time > SLOW_REQUEST_THRESHOLD_S → WARNING (time-based injection)."""
    issues = _check_sql_injection_signals(
        response_text='{"result": "ok"}',
        elapsed_s=SLOW_REQUEST_THRESHOLD_S + 0.1,
        payload_repr="'; WAITFOR DELAY '0:0:5'--",
    )
    assert len(issues) == 1
    assert "slow" in issues[0]["issue"].lower() or str(int(SLOW_REQUEST_THRESHOLD_S)) in issues[0]["issue"]


def test_response_exactly_at_threshold_not_flagged():
    """Response time == threshold (not strictly >) → not flagged."""
    issues = _check_sql_injection_signals(
        response_text='{"result": "ok"}',
        elapsed_s=SLOW_REQUEST_THRESHOLD_S,
        payload_repr="test",
    )
    # Only flag if STRICTLY greater than threshold
    timing_issues = [i for i in issues if "slow" in i["issue"].lower()]
    assert timing_issues == []


def test_fast_response_not_flagged():
    """Fast response → no timing issue."""
    issues = _check_sql_injection_signals(
        response_text='{"result": "ok"}',
        elapsed_s=0.3,
        payload_repr="test",
    )
    assert issues == []


# ── Both signals together ─────────────────────────────────────────────────────

def test_both_signals_produce_two_issues():
    """DB error + slow response → 2 separate issues."""
    issues = _check_sql_injection_signals(
        response_text="sql syntax error near 'union'",
        elapsed_s=SLOW_REQUEST_THRESHOLD_S + 1,
        payload_repr="UNION SELECT",
    )
    assert len(issues) == 2


# ── Threshold constant ────────────────────────────────────────────────────────

def test_slow_threshold_is_3_seconds():
    """Threshold must be 3.0s as documented."""
    assert SLOW_REQUEST_THRESHOLD_S == 3.0
