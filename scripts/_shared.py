"""
TestPilot — Shared utilities across all test scripts.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import sys
from enum import Enum

import httpx

VERSION = "1.2.0"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


SEVERITY_ICONS = {
    Severity.CRITICAL: "🔴",
    Severity.WARNING: "🟡",
    Severity.INFO: "🟢",
}

DEFAULT_TIMEOUT = 15


def mcp_call(
    base_url: str,
    method: str,
    params: dict | None = None,
    request_id: int = 1,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Send a JSON-RPC request to an MCP server and return the parsed response."""
    r = httpx.post(
        f"{base_url}/mcp",
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        },
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    return r.json()


def mcp_call_tool(
    base_url: str,
    tool_name: str,
    arguments: dict | None = None,
    request_id: int = 1,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Call an MCP tool and return the parsed response."""
    return mcp_call(
        base_url,
        "tools/call",
        params={"name": tool_name, "arguments": arguments or {}},
        request_id=request_id,
        timeout=timeout,
    )


def format_severity(severity: str) -> str:
    """Return the icon for a severity level."""
    try:
        return SEVERITY_ICONS.get(Severity(severity), "⚪")
    except ValueError:
        return "⚪"


def _safe_print(text: str) -> None:
    """Print text, replacing characters unencodable in sys.stdout.encoding."""
    enc = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    sys.stdout.write(text.encode(enc, errors="replace").decode(enc) + "\n")


def print_banner(test_type: str, target: str) -> None:
    """Print a standardized test banner, safe on narrow-encoding consoles (cp1252, ascii)."""
    icons = {
        "Load": "🚀",
        "Security": "🔒",
        "Contract": "📋",
        "Report": "📊",
    }
    icon = icons.get(test_type, "🔍")
    _safe_print(f"{icon} TestPilot {test_type} Test")
    _safe_print(f"   Target: {target}")
    _safe_print("")



def format_performance_line(n: int, data: dict) -> str:
    """Format a single performance result line."""
    return (
        f"{n} concurrent:  avg {data['avg']:.0f}ms | "
        f"p95 {data['p95']:.0f}ms | errors: {data['errors']}"
    )


def format_performance_summary(results: dict) -> str:
    """Format all performance results for display."""
    lines = ["Performance Summary:"]
    for n, data in sorted(results.items()):
        lines.append(format_performance_line(n, data))
    return "\n".join(lines)
