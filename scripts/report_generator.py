"""
TestPilot — Report Generator Script
Generates formatted QA reports from test results.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from _shared import format_performance_line


def generate_report(
    project_name: str,
    phases: dict[str, dict[str, Any]],
    performance_data: dict[str, dict] | None = None,
    security_issues: dict[str, list] | None = None,
    auto_fixed: int = 0,
    manual_needed: int = 0,
    commit_message: str | None = None,
) -> str:
    """
    Generate the complete TestPilot QA report.

    Args:
        project_name: Name of the project tested
        phases: Dict of phase results
        performance_data: Optional performance test results
        security_issues: Optional security test issues
        auto_fixed: Number of issues auto-fixed
        manual_needed: Number of issues needing manual fix
        commit_message: Suggested commit message if all passed
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_passed = all(p["status"] == "pass" for p in phases.values())

    lines = []
    lines.append("╔═══════════════════════════════════════════════════╗")
    lines.append("║  🚀 TESTPILOT v1.1.0 — COMPLETE QA REPORT        ║")
    lines.append(f"║  {project_name} — {timestamp:<30} ║")
    lines.append("╠═══════════════════════════════════════════════════╣")

    STATUS_ICONS = {"pass": "✅", "fail": "❌", "skip": "⏭️", "warn": "⚠️"}

    for i, (phase, result) in enumerate(phases.items(), 1):
        status_icon = STATUS_ICONS.get(result["status"], "?")
        phase_label = f"PHASE {i:<2} {phase}"
        details = result.get("details", "")

        if details:
            lines.append(f"║  {phase_label:<30} {status_icon}  {details:<15} ║")
        else:
            lines.append(f"║  {phase_label:<30} {status_icon:<20} ║")

    lines.append("╠═══════════════════════════════════════════════════╣")

    if all_passed:
        lines.append("║  OVERALL: ✅ READY TO DEPLOY                      ║")
    else:
        lines.append("║  OVERALL: ❌ NEEDS FIXES                          ║")

    lines.append("╠═══════════════════════════════════════════════════╣")
    lines.append(f"║  Auto-fixed: {auto_fixed} issues{' ' * (32 - len(str(auto_fixed)))} ║")
    lines.append(f"║  Manual action needed: {manual_needed} issues{' ' * (23 - len(str(manual_needed)))} ║")
    lines.append("╚═══════════════════════════════════════════════════╝")

    if performance_data:
        lines.append("")
        lines.append("Performance Summary:")
        for n, data in sorted(performance_data.items()):
            lines.append(format_performance_line(n, data))

    lines.append("")
    if all_passed:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if commit_message:
            lines.append("Suggested commit message:")
            lines.append(commit_message)
        else:
            lines.append("Suggested commit message:")
            lines.append(f"feat: updates to {project_name}")
            lines.append("TestPilot QA ✅")
            lines.append("")
            lines.append("Unit: pass | Integration: pass")
            lines.append("Security: clean | P95: N/A")
            lines.append(f"{len(phases)}/{len(phases)} phases passed")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    else:
        lines.append("Priority fixes before deploy:")
        lines.append("")

        for phase, result in phases.items():
            if result["status"] == "fail":
                severity = result.get("severity", "critical")
                icon = {"critical": "🔴", "warning": "🟡"}.get(severity, "🟢")
                lines.append(f"{icon} {severity.upper()}: {phase}")
                if "issue" in result:
                    lines.append(f"   {result['issue']}")

    lines.append("")
    lines.append("Built with TestPilot — github.com/impulsoxai/testpilot")

    return "\n".join(lines)


def save_report(
    report: str,
    project_name: str,
    output_dir: str = "tests/reports",
) -> str:
    """Save report to file. Returns path to saved report."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filepath = Path(output_dir) / f"testpilot-{timestamp}.md"

    content = "\n".join([
        f"# TestPilot QA Report — {project_name}",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "```",
        report,
        "```",
        "",
    ])

    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def generate_phase_summary(phases: dict[str, dict[str, Any]]) -> str:
    """Generate a one-line summary of all phases."""
    counts = {"pass": 0, "fail": 0, "skip": 0}
    for p in phases.values():
        status = p["status"]
        if status in counts:
            counts[status] += 1
    total = len(phases)

    parts = [f"{counts['pass']}/{total} passed"]
    if counts["fail"]:
        parts.append(f"{counts['fail']} failed")
    if counts["skip"]:
        parts.append(f"{counts['skip']} skipped")

    return " | ".join(parts)


def parse_test_output(output: str) -> dict[str, Any]:
    """
    Parse pytest/jest output to extract test results.
    Returns dict with total, passed, failed, coverage, failures.
    """
    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "coverage": None,
        "failures": [],
    }

    # Search each metric independently — no AND condition.
    # pytest errors (collection failures) count toward failed.
    m_passed = re.search(r"(\d+) passed", output)
    m_failed = re.search(r"(\d+) failed", output)
    m_error  = re.search(r"(\d+) error", output)

    if m_passed:
        result["passed"] = int(m_passed.group(1))
    if m_failed:
        result["failed"] += int(m_failed.group(1))
    if m_error:
        result["failed"] += int(m_error.group(1))

    # jest "Tests:" line is authoritative when present — overrides above.
    jest_match = re.search(r"Tests:\s+(.+)", output)
    if jest_match:
        jest_line = jest_match.group(1)
        jm_passed = re.search(r"(\d+) passed", jest_line)
        jm_failed = re.search(r"(\d+) failed", jest_line)
        result["passed"] = int(jm_passed.group(1)) if jm_passed else 0
        result["failed"] = int(jm_failed.group(1)) if jm_failed else 0

    result["total"] = result["passed"] + result["failed"]

    for line in output.splitlines():
        if "TOTAL" in line and "%" in line:
            m = re.search(r"(\d+)%", line)
            if m:
                result["coverage"] = int(m.group(1))
        if line.startswith("FAILED "):
            # keep only the test node ID; strip " - Reason" suffix
            test_id = line.removeprefix("FAILED ").split(" - ")[0].strip()
            result["failures"].append(test_id)

    return result


def main():
    """CLI entry point — generate a report from JSON input."""
    parser = argparse.ArgumentParser(
        description="TestPilot Report Generator — generates formatted QA reports from test results",
        epilog="Examples:\n"
               "  python report_generator.py results.json\n"
               "  python report_generator.py results.json --output report.md\n"
               "  python report_generator.py results.json --json\n"
               "  python report_generator.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_file", help="JSON file with test results")
    parser.add_argument("--output", metavar="FILE", help="Save report to specific file")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output raw data as JSON")

    args = parser.parse_args()

    with open(args.input_file) as f:
        data = json.load(f)

    if args.json_output:
        print(json.dumps(data, indent=2))
        return

    report = generate_report(
        project_name=data["project_name"],
        phases=data["phases"],
        performance_data=data.get("performance_data"),
        security_issues=data.get("security_issues"),
        auto_fixed=data.get("auto_fixed", 0),
        manual_needed=data.get("manual_needed", 0),
        commit_message=data.get("commit_message"),
    )

    print(report)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\n💾 Report saved to: {args.output}")
    else:
        filepath = save_report(report, data["project_name"])
        print(f"\n💾 Report saved to: {filepath}")


if __name__ == "__main__":
    main()
