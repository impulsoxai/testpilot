"""
TestPilot — Security Testing Script
Tests API endpoints against common attack vectors.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import httpx
import json
import time

from _shared import (
    Severity,
    SEVERITY_ICONS,
    print_banner,
)

STACK_TRACE_MARKERS = [
    "traceback", "stack trace", "exception",
    "at line", "file \"", "syntaxerror",
]

DB_ERROR_MARKERS = [
    "sql syntax", "syntax error near", "you have an error in your sql",
    "warning: mysql", "pg::syntaxerror", "postgresql error",
    "sqlite3.operationalerror", "sqlite_error",
    "odbc sql", "sqlstate", "ora-",
    "unclosed quotation mark", "jdbc exception",
    "sql server", "database error",
]

SLOW_REQUEST_THRESHOLD_S = 3.0

# Statuses that mean "this route does not exist / wrong method" — not a finding.
UNREACHABLE_STATUSES = frozenset({404, 405})

# Reserved issue category for target-misconfiguration. Its presence forces a
# non-PASS verdict so the gate never reports GREEN against a route that 404s.
CONFIG_ERROR_CATEGORY = "_config"


def _is_unreachable(status_codes: list[int]) -> bool:
    """
    True when every probe hit a missing route (all 404/405).

    Empty list → False (no responses captured; a connection-level problem,
    handled elsewhere). A single non-404/405 status → the route exists, so a
    500 or a clean 200 is a real result, not a config error.
    """
    return bool(status_codes) and all(s in UNREACHABLE_STATUSES for s in status_codes)


def _check_sql_injection_signals(
    response_text: str,
    elapsed_s: float,
    payload_repr: str,
) -> list[dict]:
    """
    Return real SQL injection signals from a probe response.

    Checks: DB error strings in body, response time > threshold.
    Status 200 alone is NOT a signal — it's correct sanitized behavior.
    """
    issues = []
    body_lower = response_text.lower()

    if any(marker in body_lower for marker in DB_ERROR_MARKERS):
        issues.append({
            "payload": payload_repr,
            "issue": "Database error in response (possible error-based SQL injection)",
            "severity": Severity.WARNING,
        })

    if elapsed_s > SLOW_REQUEST_THRESHOLD_S:
        issues.append({
            "payload": payload_repr,
            "issue": (
                f"Slow response ({elapsed_s:.1f}s) to SQL payload — "
                "possible time-based injection"
            ),
            "severity": Severity.WARNING,
        })

    return issues


MALICIOUS_INPUTS = {
    "sql_injection": [
        "'; DROP TABLE users; --",
        "\" OR 1=1 --",
        "1' UNION SELECT * FROM users --",
        "admin'--",
        "1; EXEC xp_cmdshell('dir')",
    ],
    "xss": [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "' onmouseover='alert(1)'",
    ],
    "path_traversal": [
        "../../etc/passwd",
        "/etc/shadow",
        "..\\..\\windows\\system32\\config\\sam",
        "....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    ],
    "ssrf": [
        "http://localhost:8000/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/",
        "http://127.0.0.1:6379/",
        "file:///etc/passwd",
    ],
    "command_injection": [
        "$(whoami)",
        "`whoami`",
        "| ls -la",
        "; cat /etc/passwd",
        "&& rm -rf /",
    ],
    "template_injection": [
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        "#{7*7}",
        "{{config}}",
    ],
    "prototype_pollution": [
        '{"__proto__": {"admin": true}}',
        '{"constructor": {"prototype": {"admin": true}}}',
        '{"__proto__": null}',
    ],
    "encoding_attacks": [
        "\x00\x01\x02\x03",
        "\r\n\r\nHTTP/1.1 200 OK",
        "𝕳𝖊𝖑𝖑𝖔",
        "אבגד",
        "‮A‬",
    ],
    "size_attacks": [
        "A" * 10000,
        "A" * 100000,
    ],
    "type_confusion": [
        None,
        999999999999999999,
        -999999999999999999,
        0,
        [],
        {},
        True,
        3.14159,
    ],
}


def _send_payload(
    client: httpx.Client,
    base_url: str,
    payload,
    test_mcp: bool,
    tool_name: str | None,
    request_id: int,
) -> httpx.Response:
    """Send a single payload to the target."""
    if test_mcp and tool_name:
        r = client.post(
            f"{base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {"input": payload}},
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    else:
        r = client.post(
            f"{base_url}/test",
            json={"input": payload},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    return r


def test_security(
    base_url: str,
    tool_name: str | None = None,
    test_mcp: bool = False,
) -> dict[str, list[dict]]:
    """Test API security against common attack vectors. Returns issues by category."""
    issues = {}
    all_statuses: list[int] = []

    with httpx.Client() as client:
        for category, payloads in MALICIOUS_INPUTS.items():
            category_issues = []

            for i, payload in enumerate(payloads):
                payload_repr = str(payload)[:100]

                try:
                    t0 = time.time()
                    r = _send_payload(client, base_url, payload, test_mcp, tool_name, i)
                    elapsed = time.time() - t0
                    all_statuses.append(r.status_code)
                    response_lower = r.text.lower()

                    if r.status_code == 500:
                        category_issues.append({
                            "payload": payload_repr,
                            "issue": "Server returned 500",
                            "severity": Severity.CRITICAL,
                        })

                    if any(marker in response_lower for marker in STACK_TRACE_MARKERS):
                        category_issues.append({
                            "payload": payload_repr,
                            "issue": "Stack trace exposed",
                            "severity": Severity.CRITICAL,
                        })

                    if category == "sql_injection":
                        category_issues.extend(
                            _check_sql_injection_signals(r.text, elapsed, payload_repr)
                        )

                except httpx.ConnectError:
                    category_issues.append({
                        "payload": payload_repr,
                        "issue": "Connection lost after attack",
                        "severity": Severity.CRITICAL,
                    })
                except Exception as e:
                    category_issues.append({
                        "payload": payload_repr,
                        "issue": f"Error: {str(e)[:100]}",
                        "severity": Severity.WARNING,
                    })

            if category_issues:
                issues[category] = category_issues

        if _is_unreachable(all_statuses):
            issues[CONFIG_ERROR_CATEGORY] = [{
                "payload": "N/A",
                "issue": (
                    f"All {len(all_statuses)} probes returned 404/405 — the target "
                    "route does not exist. No payload reached real logic, so this is "
                    "NOT a pass. Configure the correct endpoint/shape "
                    "(SECURITY_TARGETS) and re-run."
                ),
                "severity": Severity.CRITICAL,
            }]

        health = client.get(f"{base_url}/health", timeout=5)
        if health.status_code != 200:
            issues.setdefault("_server", []).append({
                "payload": "N/A",
                "issue": f"Server unhealthy after tests: {health.status_code}",
                "severity": Severity.CRITICAL,
            })

    return issues


def format_security_report(issues: dict[str, list[dict]]) -> str:
    """Format security test results for display."""
    if not issues:
        return "✅ Security tests passed — no vulnerabilities found"

    lines = ["⚠️  Security issues found:", ""]

    total_critical = 0
    total_warning = 0

    for category, category_issues in issues.items():
        critical = sum(1 for i in category_issues if i["severity"] == Severity.CRITICAL)
        warning = sum(1 for i in category_issues if i["severity"] == Severity.WARNING)
        total_critical += critical
        total_warning += warning

        lines.append(f"  {category}:")
        for issue in category_issues[:3]:
            icon = SEVERITY_ICONS.get(issue["severity"], "⚪")
            lines.append(f"    {icon} {issue['issue']}: {issue['payload'][:50]}...")

        if len(category_issues) > 3:
            lines.append(f"    ... and {len(category_issues) - 3} more")

        lines.append("")

    lines.append(f"Summary: {total_critical} critical, {total_warning} warnings")
    return "\n".join(lines)


def get_security_verdict(issues: dict[str, list[dict]]) -> str:
    """Return overall security verdict."""
    if CONFIG_ERROR_CATEGORY in issues:
        return "🚫 ERRO — alvo não testável (configure SECURITY_TARGETS)"

    if not issues:
        return "✅ PASS"

    has_critical = any(
        i["severity"] == Severity.CRITICAL
        for category_issues in issues.values()
        for i in category_issues
    )

    return "❌ FAIL" if has_critical else "⚠️  WARNING"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestPilot Security Testing — tests API endpoints against common attack vectors",
        epilog="Examples:\n"
               "  python security_test.py https://api.example.com\n"
               "  python security_test.py https://api.example.com --mcp tool_name\n"
               "  python security_test.py https://api.example.com --json\n"
               "  python security_test.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("base_url", help="Base URL of the API to test")
    parser.add_argument("--mcp", action="store_true", help="Test MCP server mode")
    parser.add_argument("tool_name", nargs="?", default=None, help="MCP tool name to test")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON")

    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    print_banner("Security", base_url)
    print(f"   Mode: {'MCP' if args.mcp else 'REST'}")
    if args.tool_name:
        print(f"   Tool: {args.tool_name}")
    print()

    issues = test_security(base_url, args.tool_name, args.mcp)

    if args.json_output:
        json_issues = {}
        for cat, cat_issues in issues.items():
            json_issues[cat] = [
                {"payload": i["payload"], "issue": i["issue"], "severity": i["severity"].value}
                for i in cat_issues
            ]
        print(json.dumps({"verdict": get_security_verdict(issues), "issues": json_issues}, indent=2))
    else:
        print(format_security_report(issues))
        print(f"\nVerdict: {get_security_verdict(issues)}")


if __name__ == "__main__":
    main()
