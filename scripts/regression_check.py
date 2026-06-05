"""
TestPilot — Regression Gate
Detects regressions: tests that PASSED in the previous run and now FAIL/ERROR.
Replaces the old POSIX-only bash (/tmp, [ -f ], diff, grep, cp) with a
cross-platform script and a JSON baseline. A regression FAILS the phase.

New failures (never passed) are not regressions — Phase 2 already catches those.
Missing tests are not flagged, to avoid rename/refactor noise.

Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from _shared import print_banner

BASELINE_PATH = "tests/reports/last_run.json"

_STATUS_LINE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR)\b")


def _parse_test_statuses(output: str) -> dict[str, str]:
    """Map each test id to PASSED/FAILED/ERROR from pytest -v output."""
    statuses = {}
    for line in output.splitlines():
        m = _STATUS_LINE.match(line.strip())
        if m:
            statuses[m.group(1)] = m.group(2)
    return statuses


def _find_regressions(previous: dict, current: dict) -> list[str]:
    """Tests that were PASSED before and now FAIL/ERROR."""
    return sorted(
        t for t, s in current.items()
        if s in ("FAILED", "ERROR") and previous.get(t) == "PASSED"
    )


def _find_newly_passing(previous: dict, current: dict) -> list[str]:
    """Tests that were FAILED/ERROR before and now PASS (informational)."""
    return sorted(
        t for t, s in current.items()
        if s == "PASSED" and previous.get(t) in ("FAILED", "ERROR")
    )


def _regression_verdict(regressions: list[str], had_baseline: bool) -> str:
    if not had_baseline:
        return "✅ baseline salvo — primeira execução, sem comparação"
    if regressions:
        return f"❌ FAIL — {len(regressions)} regressão(ões) (PASSED → FAILED)"
    return "✅ PASS — sem regressões"


def _load_baseline(path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_baseline(path, statuses: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(statuses, indent=2), encoding="utf-8")


def run_regression(root: str = ".", baseline_path: str = BASELINE_PATH) -> dict:
    """Run the suite, compare with the baseline, then update it."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no"],
        capture_output=True, text=True, cwd=root,
    )
    current = _parse_test_statuses(proc.stdout + proc.stderr)

    full_baseline = str(Path(root) / baseline_path)
    previous = _load_baseline(full_baseline)
    had_baseline = previous is not None

    regressions = _find_regressions(previous or {}, current)
    newly_passing = _find_newly_passing(previous or {}, current)

    _save_baseline(full_baseline, current)

    return {
        "failed": bool(regressions),
        "regressions": regressions,
        "newly_passing": newly_passing,
        "had_baseline": had_baseline,
        "verdict": _regression_verdict(regressions, had_baseline),
    }


def main():
    parser = argparse.ArgumentParser(
        description="TestPilot Regression Gate — fails on PASSED->FAILED tests vs the last run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root (default: .)")
    args = parser.parse_args()

    print_banner("Regression", args.root)
    result = run_regression(args.root)

    for t in result["regressions"]:
        print(f"   ❌ {t}")
    for t in result["newly_passing"]:
        print(f"   ✅ (novo) {t}")
    print()
    print(result["verdict"])
    sys.exit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
