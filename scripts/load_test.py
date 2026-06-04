"""
TestPilot — Load Testing Script
Runs concurrent requests to measure API performance.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import asyncio
import httpx
import json
import time
import statistics

from _shared import (
    Severity,
    SEVERITY_ICONS,
    print_banner,
)


async def run_load_test(
    base_url: str,
    endpoint: str = "/health",
    concurrency_levels: list[int] | None = None,
    timeout: int = 30,
) -> dict:
    """
    Run load tests at different concurrency levels.

    Returns dict with results per concurrency level:
    {
        10: {"avg": 45.2, "p50": 42.0, "p95": 120.5, "total": 1.2, "errors": 0},
        50: {...},
        100: {...}
    }
    """
    if concurrency_levels is None:
        concurrency_levels = [10, 50, 100]

    results = {}

    async with httpx.AsyncClient(timeout=timeout) as client:
        for n in concurrency_levels:
            async def req():
                start = time.time()
                try:
                    r = await client.get(f"{base_url}{endpoint}")
                    if r.status_code == 200:
                        return time.time() - start
                except Exception:
                    pass
                return None

            t_start = time.time()
            raw = await asyncio.gather(*[req() for _ in range(n)])
            t_total = time.time() - t_start

            valid = [r for r in raw if r is not None]
            errors = n - len(valid)

            if valid:
                p95_idx = int(len(valid) * 0.95)
                p95_idx = min(p95_idx, len(valid) - 1)
                results[n] = {
                    "avg": round(statistics.mean(valid) * 1000, 2),
                    "p50": round(statistics.median(valid) * 1000, 2),
                    "p95": round(sorted(valid)[p95_idx] * 1000, 2),
                    "total": round(t_total, 2),
                    "errors": errors,
                }
            else:
                results[n] = {
                    "avg": 0,
                    "p50": 0,
                    "p95": 0,
                    "total": round(t_total, 2),
                    "errors": n,
                }

    return results


def check_thresholds(results: dict) -> list[dict]:
    """Check results against performance thresholds."""
    issues = []

    thresholds = {
        10: {"avg": 1000, "p95": 3000, "errors": 0},
        50: {"avg": 2000, "p95": 5000, "errors_pct": 5},
        100: {"avg": 3000, "p95": 8000, "errors_pct": 10},
    }

    for n, data in results.items():
        t = thresholds.get(n, thresholds[100])

        if data["avg"] > t["avg"]:
            issues.append({
                "level": n,
                "metric": "avg",
                "actual": data["avg"],
                "threshold": t["avg"],
                "severity": Severity.WARNING,
            })

        if data["p95"] > t["p95"]:
            issues.append({
                "level": n,
                "metric": "p95",
                "actual": data["p95"],
                "threshold": t["p95"],
                "severity": Severity.CRITICAL,
            })

        if "errors" in t and data["errors"] > t["errors"]:
            issues.append({
                "level": n,
                "metric": "errors",
                "actual": data["errors"],
                "threshold": t["errors"],
                "severity": Severity.CRITICAL,
            })

        if "errors_pct" in t:
            error_pct = (data["errors"] / n) * 100
            if error_pct > t["errors_pct"]:
                issues.append({
                    "level": n,
                    "metric": "errors_pct",
                    "actual": round(error_pct, 1),
                    "threshold": t["errors_pct"],
                    "severity": Severity.WARNING,
                })

    return issues


def format_results(results: dict) -> str:
    """Format detailed results for display."""
    lines = ["Performance Results:"]
    lines.append("-" * 50)

    for n, data in sorted(results.items()):
        lines.append(f"\n{n} concurrent requests:")
        lines.append(f"  Avg:  {data['avg']:.0f}ms")
        lines.append(f"  P50:  {data['p50']:.0f}ms")
        lines.append(f"  P95:  {data['p95']:.0f}ms")
        lines.append(f"  Total: {data['total']:.2f}s")
        lines.append(f"  Errors: {data['errors']}")

    return "\n".join(lines)


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TestPilot Load Testing — measures API performance under concurrency",
        epilog="Examples:\n"
               "  python load_test.py https://api.example.com\n"
               "  python load_test.py https://api.example.com /api/users\n"
               "  python load_test.py https://api.example.com --json\n"
               "  python load_test.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("base_url", help="Base URL of the API to test")
    parser.add_argument("endpoint", nargs="?", default="/health", help="Endpoint to test (default: /health)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON")

    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    print_banner("Load", f"{base_url}{args.endpoint}")

    results = await run_load_test(base_url, args.endpoint)
    issues = check_thresholds(results)

    if args.json_output:
        print(json.dumps({"results": results, "issues": issues}, indent=2))
    else:
        print(format_results(results))
        if issues:
            print("\n⚠️  Threshold violations:")
            for issue in issues:
                icon = SEVERITY_ICONS.get(issue["severity"], "⚪")
                print(
                    f"  {icon} {issue['level']} concurrent — {issue['metric']}: "
                    f"{issue['actual']} (threshold: {issue['threshold']})"
                )
        else:
            print("\n✅ All performance thresholds passed")


if __name__ == "__main__":
    asyncio.run(main())
