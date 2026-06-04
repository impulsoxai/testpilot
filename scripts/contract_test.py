"""
TestPilot — Contract Testing Script
Validates API contracts haven't changed in breaking ways.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import json
import sys
from typing import Any

import httpx

from _shared import (
    Severity,
    SEVERITY_ICONS,
    mcp_call,
    mcp_call_tool,
    print_banner,
    require_args,
)


def _failure(issue: str) -> dict[str, Any]:
    return {"tools": {}, "issues": [issue], "valid": False}


def check_mcp_contracts(base_url: str) -> dict[str, Any]:
    """Verify MCP Server tool contracts are valid."""
    issues = []
    tools = {}

    try:
        data = mcp_call(base_url, "tools/list")

        if "result" not in data:
            return _failure("Missing 'result' in response")

        if "tools" not in data["result"]:
            return _failure("Missing 'tools' in result")

        raw_tools = data["result"]["tools"]

        for tool in raw_tools:
            name = tool.get("name", "UNKNOWN")
            tools[name] = tool

            if "description" not in tool:
                issues.append(f"{name}: missing 'description'")
            elif len(tool["description"]) < 10:
                issues.append(f"{name}: description too short ({len(tool['description'])} chars)")

            if "inputSchema" not in tool:
                issues.append(f"{name}: missing 'inputSchema'")
            else:
                schema = tool["inputSchema"]
                if "type" not in schema:
                    issues.append(f"{name}: inputSchema missing 'type'")

                for prop_name, prop_def in schema.get("properties", {}).items():
                    if "type" not in prop_def:
                        issues.append(f"{name}.{prop_name}: missing 'type'")
                    if "description" not in prop_def:
                        issues.append(f"{name}.{prop_name}: missing 'description'")

    except httpx.ConnectError:
        return _failure("Connection failed")
    except Exception as e:
        return _failure(f"Error: {str(e)}")

    return {"tools": tools, "issues": issues, "valid": len(issues) == 0}


def check_mcp_response_format(base_url: str, tool_name: str) -> dict[str, Any]:
    """Verify a tool returns consistent response format."""
    issues = []

    try:
        data = mcp_call_tool(base_url, tool_name, {})

        if "result" in data:
            result = data["result"]
            if "content" not in result:
                issues.append(f"{tool_name}: missing 'content' in result")

            content = result.get("content", [])
            if not isinstance(content, list):
                issues.append(f"{tool_name}: 'content' is not an array")

            for i, item in enumerate(content):
                if "type" not in item:
                    issues.append(f"{tool_name}.content[{i}]: missing 'type'")
                if "text" not in item:
                    issues.append(f"{tool_name}.content[{i}]: missing 'text'")

        elif "error" in data:
            error = data["error"]
            if "code" not in error:
                issues.append(f"{tool_name}: error missing 'code'")
            if "message" not in error:
                issues.append(f"{tool_name}: error missing 'message'")

    except Exception as e:
        issues.append(f"{tool_name}: test error: {str(e)}")

    return {"issues": issues, "valid": len(issues) == 0}


def compare_contracts(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> list[dict]:
    """Compare current contract with previous version. Returns breaking changes."""
    breaking = []
    current_tools = set(current.get("tools", {}).keys())
    previous_tools = set(previous.get("tools", {}).keys())

    for tool in previous_tools - current_tools:
        breaking.append({
            "type": "removed",
            "tool": tool,
            "severity": Severity.CRITICAL,
            "message": f"Tool '{tool}' was removed",
        })

    for tool in current_tools - previous_tools:
        breaking.append({
            "type": "added",
            "tool": tool,
            "severity": Severity.INFO,
            "message": f"Tool '{tool}' was added",
        })

    for tool in current_tools & previous_tools:
        curr = current["tools"][tool]
        prev = previous["tools"][tool]

        curr_schema = curr.get("inputSchema", {})
        prev_schema = prev.get("inputSchema", {})

        curr_required = set(curr_schema.get("required", []))
        prev_required = set(prev_schema.get("required", []))

        for param in curr_required - prev_required:
            breaking.append({
                "type": "required_param_added",
                "tool": tool,
                "param": param,
                "severity": Severity.CRITICAL,
                "message": f"New required param '{param}' in '{tool}'",
            })

        curr_props = set(curr_schema.get("properties", {}).keys())
        prev_props = set(prev_schema.get("properties", {}).keys())

        for param in prev_props - curr_props:
            breaking.append({
                "type": "param_removed",
                "tool": tool,
                "param": param,
                "severity": Severity.WARNING,
                "message": f"Param '{param}' removed from '{tool}'",
            })

    return breaking


def format_contract_report(
    contract_result: dict[str, Any],
    breaking_changes: list[dict] | None = None,
) -> str:
    """Format contract test results for display."""
    lines = []

    if contract_result["valid"]:
        lines.append(f"✅ {len(contract_result['tools'])} tools have valid contracts")
    else:
        lines.append("❌ Contract validation failed:")
        for issue in contract_result["issues"]:
            lines.append(f"   • {issue}")

    if breaking_changes:
        lines.append("\n⚠️  Contract changes detected:")

        for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
            for change in breaking_changes:
                if change["severity"] == severity:
                    icon = SEVERITY_ICONS.get(severity, "⚪")
                    lines.append(f"   {icon} {change['message']}")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestPilot Contract Testing — validates API contracts haven't changed",
        epilog="Examples:\n"
               "  python contract_test.py https://api.example.com\n"
               "  python contract_test.py https://api.example.com --compare previous.json\n"
               "  python contract_test.py https://api.example.com --json\n"
               "  python contract_test.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("base_url", help="Base URL of the MCP server to test")
    parser.add_argument("--compare", metavar="FILE", help="Compare with previous contract snapshot")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON")

    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    print_banner("Contract", base_url)

    result = check_mcp_contracts(base_url)

    breaking = None
    if args.compare:
        with open(args.compare) as f:
            previous = json.load(f)
        breaking = compare_contracts(result, previous)

    if args.json_output:
        print(json.dumps({"valid": result["valid"], "tools": result["tools"], "breaking": breaking}, indent=2))
    else:
        print(format_contract_report(result, breaking))

    if result["valid"]:
        import os
        os.makedirs("tests/reports", exist_ok=True)
        with open("tests/reports/contract_snapshot.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\n💾 Contract snapshot saved to tests/reports/contract_snapshot.json")


if __name__ == "__main__":
    main()
