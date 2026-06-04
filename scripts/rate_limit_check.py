"""
TestPilot — Rate Limit Checker
Tests that rate limiting is enforced on the configured endpoint.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import json
import os
import sys

import httpx

from _shared import VERSION

FALLBACK_ENDPOINT = "/health"
ENDPOINT_ENV_VAR = "RATE_LIMIT_ENDPOINT"


def get_rate_limit_endpoint() -> tuple[str, bool]:
    """
    Return (endpoint, used_fallback).

    Reads RATE_LIMIT_ENDPOINT from environment. Falls back to /health when
    the var is absent or empty. Callers should pass used_fallback to
    warn_if_fallback() so the operator knows to configure the right endpoint.
    """
    raw = os.environ.get(ENDPOINT_ENV_VAR, "").strip()
    if raw:
        return raw, False
    return FALLBACK_ENDPOINT, True


def warn_if_fallback(used_fallback: bool) -> None:
    """Print AVISO when falling back to the default /health endpoint."""
    if used_fallback:
        print(
            f"AVISO: usando endpoint padrão {FALLBACK_ENDPOINT!r} — "
            f"defina {ENDPOINT_ENV_VAR} para o endpoint real do seu projeto."
        )


def test_rate_limiting(base_url: str, limit: int = 100) -> dict:
    """
    Fire limit+10 requests at the configured endpoint; check for HTTP 429.

    Returns dict with: endpoint, used_fallback, has_429, total_requests,
    last_statuses (last 20 status codes for the report).
    """
    endpoint, used_fallback = get_rate_limit_endpoint()
    warn_if_fallback(used_fallback)

    url = f"{base_url.rstrip('/')}{endpoint}"
    statuses = []

    with httpx.Client(timeout=5) as client:
        for _ in range(limit + 10):
            try:
                r = client.get(url)
                statuses.append(r.status_code)
            except httpx.ConnectError:
                break

    last = statuses[-10:] if len(statuses) >= 10 else statuses
    has_429 = 429 in last

    return {
        "endpoint": endpoint,
        "used_fallback": used_fallback,
        "has_429": has_429,
        "total_requests": len(statuses),
        "last_statuses": statuses[-20:],
    }


def format_result(result: dict) -> str:
    if result["used_fallback"]:
        warn = (
            f"⚠️  AVISO: endpoint padrão {FALLBACK_ENDPOINT!r} usado. "
            f"Defina {ENDPOINT_ENV_VAR} para o endpoint real.\n"
        )
    else:
        warn = ""

    if result["has_429"]:
        verdict = f"✅ Rate limiting aplicado em {result['endpoint']} (429 detectado)"
    else:
        verdict = f"⚠️  Rate limiting NÃO detectado em {result['endpoint']} (sem 429 após {result['total_requests']} requests)"

    return f"{warn}{verdict}"


def main():
    parser = argparse.ArgumentParser(
        description="TestPilot Rate Limit Check — verifies rate limiting is enforced",
        epilog=(
            "Examples:\n"
            f"  python rate_limit_check.py https://api.example.com\n"
            f"  {ENDPOINT_ENV_VAR}=/token python rate_limit_check.py https://api.example.com\n"
            f"  python rate_limit_check.py https://api.example.com --limit 50 --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("base_url", help="Base URL of the API to test")
    parser.add_argument(
        "--limit", type=int, default=100,
        help=f"Request limit to test (default: 100). Env: {ENDPOINT_ENV_VAR}"
    )
    parser.add_argument("--json", action="store_true", dest="json_output")

    args = parser.parse_args()
    result = test_rate_limiting(args.base_url.rstrip("/"), args.limit)

    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        print(format_result(result))

    sys.exit(0 if result["has_429"] else 1)


if __name__ == "__main__":
    main()
