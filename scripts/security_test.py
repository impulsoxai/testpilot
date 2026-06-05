"""
TestPilot — Security Testing Script
Tests API endpoints against common attack vectors.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import httpx
import json
import os
import time
from pathlib import Path

from _shared import (
    Severity,
    SEVERITY_ICONS,
    print_banner,
)

# Marker the operator places in a target's path/body where the malicious payload
# should be injected. See SECURITY_TARGETS / testpilot.targets.json.
PAYLOAD_MARKER = "§PAYLOAD§"
TARGETS_ENV_VAR = "SECURITY_TARGETS"
DEFAULT_TARGETS_FILE = "testpilot.targets.json"

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


# System-file content that proves a path-traversal payload actually read a file.
TRAVERSAL_MARKERS = [
    "root:x:0:0", "root:*:0:0", "daemon:x:",   # /etc/passwd, /etc/shadow
    "[boot loader]", "[fonts]",                 # Windows boot.ini / win.ini
    "; for 16-bit app support",
]

# Command output that proves a command-injection payload executed.
CMDI_MARKERS = [
    "uid=", "gid=",                # id / whoami output
    "root:x:0:0",                  # cat /etc/passwd via injection
    "volume serial number",        # Windows dir
    "directory of c:\\",
]


def _check_xss_reflection(response_text: str, payload: str, payload_repr: str) -> list[dict]:
    """Flag when an XSS payload is reflected UNescaped (raw markup survives)."""
    if not payload or ("<" not in payload and "javascript:" not in payload.lower()):
        return []
    if payload in response_text:
        return [{
            "payload": payload_repr,
            "issue": "XSS payload reflected unescaped in response",
            "severity": Severity.WARNING,
        }]
    return []


def _check_path_traversal(response_text: str, payload_repr: str) -> list[dict]:
    """Flag when system-file content leaks into the response."""
    body_lower = response_text.lower()
    if any(marker in body_lower for marker in TRAVERSAL_MARKERS):
        return [{
            "payload": payload_repr,
            "issue": "System file content leaked (path traversal succeeded)",
            "severity": Severity.CRITICAL,
        }]
    return []


def _check_ssti(response_text: str, payload: str, payload_repr: str) -> list[dict]:
    """Flag when an arithmetic SSTI probe (7*7) evaluates to 49 in the body."""
    if "7*7" not in payload:
        return []
    if "49" in response_text and "7*7" not in response_text:
        return [{
            "payload": payload_repr,
            "issue": "Template expression evaluated (7*7 -> 49) — server-side template injection",
            "severity": Severity.CRITICAL,
        }]
    return []


def _check_command_injection(response_text: str, payload_repr: str) -> list[dict]:
    """Flag when command output appears in the response."""
    body_lower = response_text.lower()
    if any(marker in body_lower for marker in CMDI_MARKERS):
        return [{
            "payload": payload_repr,
            "issue": "Command output in response (command injection succeeded)",
            "severity": Severity.CRITICAL,
        }]
    return []


def _parse_tool_names(data: dict) -> list[str]:
    """Extract tool names from an MCP tools/list response. Empty on error/none."""
    tools = data.get("result", {}).get("tools", []) if isinstance(data, dict) else []
    return [t["name"] for t in tools if isinstance(t, dict) and "name" in t]


def _discover_mcp_tools(client: httpx.Client, base_url: str) -> list[str]:
    """Query the MCP server's tools/list and return tool names. Empty on failure."""
    try:
        r = client.post(
            f"{base_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        return _parse_tool_names(r.json())
    except Exception:
        return []


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


def _deep_substitute(obj, payload):
    """Replace PAYLOAD_MARKER anywhere inside obj with `payload`.

    A value that IS exactly the marker becomes the raw payload (type preserved —
    None/int/list survive for type-confusion probes). A marker embedded in a
    larger string is str()-substituted.
    """
    if obj == PAYLOAD_MARKER:
        return payload
    if isinstance(obj, dict):
        return {k: _deep_substitute(v, payload) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_substitute(v, payload) for v in obj]
    if isinstance(obj, str) and PAYLOAD_MARKER in obj:
        return obj.replace(PAYLOAD_MARKER, str(payload))
    return obj


def _inject_payload(target: dict, payload) -> tuple[str, str, dict | None]:
    """Substitute the marker in a target's path and body. Returns (method, path, body)."""
    method = str(target.get("method", "POST")).upper()
    path = str(target.get("path", "/")).replace(PAYLOAD_MARKER, str(payload))
    body = _deep_substitute(target.get("body"), payload)
    return method, path, body


def _load_targets(
    env_value: str | None = None,
    default_file: str = DEFAULT_TARGETS_FILE,
) -> list[dict] | None:
    """
    Load REST security targets. Reads SECURITY_TARGETS (a JSON file path) or, if
    unset, the default testpilot.targets.json. Accepts {"targets": [...]} or a
    bare list. Returns None when nothing is configured or the list is empty.
    """
    raw = (env_value if env_value is not None else os.environ.get(TARGETS_ENV_VAR, "")).strip()
    path = raw or default_file
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    targets = data.get("targets") if isinstance(data, dict) else data
    return targets or None


def _build_requests(
    base_url: str,
    payload,
    test_mcp: bool,
    tool_name: str | None,
    targets: list[dict] | None,
    request_id: int,
):
    """Yield (method, url, json_body) request specs for one payload."""
    if test_mcp and tool_name:
        yield "POST", f"{base_url}/mcp", {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": {"input": payload}},
        }
        return

    if targets:
        for target in targets:
            method, path, body = _inject_payload(target, payload)
            yield method, f"{base_url}{path}", body
        return

    yield "POST", f"{base_url}/test", {"input": payload}


def test_security(
    base_url: str,
    tool_name: str | None = None,
    test_mcp: bool = False,
) -> dict[str, list[dict]]:
    """Test API security against common attack vectors. Returns issues by category."""
    issues = {}
    all_statuses: list[int] = []
    targets = _load_targets() if not test_mcp else None
    if not test_mcp and not targets:
        print(
            f"AVISO: nenhum target configurado — usando fallback '/test'. "
            f"Defina {TARGETS_ENV_VAR} (ou crie {DEFAULT_TARGETS_FILE}) com as "
            f"rotas e shapes reais; use o marcador {PAYLOAD_MARKER} onde o payload entra."
        )

    with httpx.Client() as client:
        if test_mcp:
            tool_names = [tool_name] if tool_name else _discover_mcp_tools(client, base_url)
            if not tool_names:
                print("AVISO: nenhuma tool MCP encontrada via tools/list — nada a testar.")
        else:
            tool_names = [None]

        for category, payloads in MALICIOUS_INPUTS.items():
            category_issues = []

            for i, payload in enumerate(payloads):
                payload_repr = str(payload)[:100]

                try:
                    requests_iter = (
                        spec
                        for tn in tool_names
                        for spec in _build_requests(base_url, payload, test_mcp, tn, targets, i)
                    )
                    for method, url, body in requests_iter:
                        t0 = time.time()
                        r = client.request(
                            method, url, json=body,
                            headers={"Content-Type": "application/json"},
                            timeout=10,
                        )
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
                        elif category == "xss":
                            category_issues.extend(
                                _check_xss_reflection(r.text, str(payload), payload_repr)
                            )
                        elif category == "path_traversal":
                            category_issues.extend(
                                _check_path_traversal(r.text, payload_repr)
                            )
                        elif category == "template_injection":
                            category_issues.extend(
                                _check_ssti(r.text, str(payload), payload_repr)
                            )
                        elif category == "command_injection":
                            category_issues.extend(
                                _check_command_injection(r.text, payload_repr)
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
