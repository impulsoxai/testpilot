"""
TDD — fix #4c: confirm injection by POSITIVE signals, not absence of 500.
Each category gets a pure detector that looks for evidence the payload actually
did something:
  - XSS: payload reflected UNescaped in the body.
  - path traversal: system-file content (root:x:0:0) leaked.
  - SSTI: {{7*7}} evaluated to 49 in the body.
  - command injection: command output (uid=, root:x:0:0) in the body.
Plus MCP tool enumeration via tools/list (pure parse of the response).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from security_test import (
    _check_xss_reflection,
    _check_path_traversal,
    _check_ssti,
    _check_command_injection,
    _parse_tool_names,
    Severity,
)


# ── XSS reflection ────────────────────────────────────────────────────────────

def test_xss_reflected_unescaped_flagged():
    """Raw <script> echoed back → reflected XSS WARNING."""
    payload = "<script>alert('xss')</script>"
    issues = _check_xss_reflection(
        response_text=f"<html><body>Hello {payload}</body></html>",
        payload=payload, payload_repr=payload,
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == Severity.WARNING


def test_xss_escaped_not_flagged():
    """Payload echoed but HTML-escaped → safe, no flag."""
    issues = _check_xss_reflection(
        response_text="<html>Hello &lt;script&gt;alert('xss')&lt;/script&gt;</html>",
        payload="<script>alert('xss')</script>",
        payload_repr="<script>alert('xss')</script>",
    )
    assert issues == []


def test_xss_not_reflected_not_flagged():
    """Payload absent from response → no reflection."""
    issues = _check_xss_reflection(
        response_text='{"error": "invalid input"}',
        payload="<img src=x onerror=alert(1)>",
        payload_repr="<img src=x onerror=alert(1)>",
    )
    assert issues == []


# ── Path traversal ────────────────────────────────────────────────────────────

def test_traversal_passwd_content_flagged():
    """/etc/passwd content in body → CRITICAL."""
    issues = _check_path_traversal(
        response_text="root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:",
        payload_repr="../../etc/passwd",
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == Severity.CRITICAL


def test_traversal_windows_ini_flagged():
    issues = _check_path_traversal(
        response_text="[boot loader]\ntimeout=30",
        payload_repr="..\\..\\boot.ini",
    )
    assert len(issues) >= 1


def test_traversal_clean_body_not_flagged():
    issues = _check_path_traversal(
        response_text='{"error": "not found"}',
        payload_repr="../../etc/passwd",
    )
    assert issues == []


# ── SSTI ──────────────────────────────────────────────────────────────────────

def test_ssti_evaluated_flagged():
    """{{7*7}} → 49 in body and literal 7*7 gone → evaluated → CRITICAL."""
    issues = _check_ssti(
        response_text="<html>Result: 49</html>",
        payload="{{7*7}}", payload_repr="{{7*7}}",
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == Severity.CRITICAL


def test_ssti_reflected_literally_not_flagged():
    """{{7*7}} echoed verbatim (not evaluated) → no SSTI."""
    issues = _check_ssti(
        response_text="You searched for {{7*7}}",
        payload="{{7*7}}", payload_repr="{{7*7}}",
    )
    assert issues == []


def test_ssti_dollar_brace_variant_flagged():
    issues = _check_ssti(
        response_text="value=49",
        payload="${7*7}", payload_repr="${7*7}",
    )
    assert len(issues) == 1


def test_ssti_non_arithmetic_payload_ignored():
    """A payload without 7*7 (e.g. {{config}}) isn't judged by the 49 heuristic."""
    issues = _check_ssti(
        response_text="49 results found",
        payload="{{config}}", payload_repr="{{config}}",
    )
    assert issues == []


# ── Command injection ─────────────────────────────────────────────────────────

def test_cmdi_id_output_flagged():
    """uid=/gid= output → command executed → CRITICAL."""
    issues = _check_command_injection(
        response_text="uid=0(root) gid=0(root) groups=0(root)",
        payload_repr="$(id)",
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == Severity.CRITICAL


def test_cmdi_passwd_via_cat_flagged():
    issues = _check_command_injection(
        response_text="root:x:0:0:root:/root:/bin/bash",
        payload_repr="; cat /etc/passwd",
    )
    assert len(issues) >= 1


def test_cmdi_clean_body_not_flagged():
    issues = _check_command_injection(
        response_text='{"result": "ok"}',
        payload_repr="`whoami`",
    )
    assert issues == []


# ── MCP tool enumeration (pure parse) ─────────────────────────────────────────

def test_parse_tool_names_extracts_names():
    data = {"result": {"tools": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}}
    assert _parse_tool_names(data) == ["a", "b", "c"]


def test_parse_tool_names_skips_unnamed():
    data = {"result": {"tools": [{"name": "a"}, {"description": "no name"}]}}
    assert _parse_tool_names(data) == ["a"]


def test_parse_tool_names_empty_when_no_tools():
    assert _parse_tool_names({"result": {"tools": []}}) == []
    assert _parse_tool_names({}) == []
    assert _parse_tool_names({"error": {"code": -1}}) == []
