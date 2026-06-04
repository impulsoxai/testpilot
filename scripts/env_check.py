"""
TestPilot — Environment Variable Checker
Verifies required vars from .env.example exist in .env file OR os.environ.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import os
import sys
from pathlib import Path


def _parse_env_file(path) -> dict:
    """Parse KEY=VALUE lines from an env file. Returns {key: value}."""
    p = Path(path)
    if not p.exists():
        return {}
    result = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


def check_env_vars(
    example_path=".env.example",
    env_path=".env",
    extra_environ=None,
) -> tuple[list, list]:
    """
    Check that every var in example_path is configured somewhere.

    Sources checked (in order, later overrides earlier):
      1. .env file (parsed directly — no shell export required)
      2. extra_environ (typically os.environ)

    Returns:
        (required, missing) — both as lists of var names.
        Returns ([], []) when .env.example does not exist (skip check).
    """
    if not Path(example_path).exists():
        return [], []

    required = list(_parse_env_file(example_path).keys())

    configured = _parse_env_file(env_path)
    if extra_environ:
        configured.update(extra_environ)

    missing = [k for k in required if not configured.get(k)]
    return required, missing


def main():
    required, missing = check_env_vars(
        example_path=".env.example",
        env_path=".env",
        extra_environ=os.environ,
    )

    if not required:
        print("⚠️  No .env.example found — skipping env check")
        return

    if missing:
        print(f"❌ Missing env vars: {missing}")
        sys.exit(1)
    else:
        print(f"✅ All {len(required)} env vars present")


if __name__ == "__main__":
    main()
