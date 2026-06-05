"""
TestPilot — Dependency Vulnerability Gate
Runs npm audit (Node) and pip-audit (Python). FAILS the phase when a vulnerability
at/above the configured level is found. Cross-platform; SKIPs gracefully when the
tool is not installed.

npm thresholds by severity via AUDIT_FAIL_LEVEL (default "high"). pip-audit has no
reliable native severity, so Python fails on ANY vulnerability; AUDIT_IGNORE
(comma-separated advisory IDs) accepts known/unfixable ones.

Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from _shared import print_banner

NPM_LEVELS = ["info", "low", "moderate", "high", "critical"]
DEFAULT_FAIL_LEVEL = "high"
FAIL_LEVEL_ENV = "AUDIT_FAIL_LEVEL"
IGNORE_ENV = "AUDIT_IGNORE"


# ── Config ────────────────────────────────────────────────────────────────────

def _get_fail_level(environ) -> str:
    """npm audit severity threshold from AUDIT_FAIL_LEVEL; invalid -> default."""
    raw = environ.get(FAIL_LEVEL_ENV, "").strip().lower()
    return raw if raw in NPM_LEVELS else DEFAULT_FAIL_LEVEL


def _parse_ignore(environ) -> set[str]:
    """Accepted advisory IDs from AUDIT_IGNORE (comma-separated)."""
    raw = environ.get(IGNORE_ENV, "")
    return {part.strip() for part in raw.split(",") if part.strip()}


# ── Command building ──────────────────────────────────────────────────────────

def _build_npm_audit_command(level: str) -> list[str]:
    return ["npm", "audit", "--json", f"--audit-level={level}"]


def _build_pip_audit_command(python_exe: str = sys.executable) -> list[str]:
    return [python_exe, "-m", "pip_audit", "--format", "json"]


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_npm_audit(text: str) -> dict:
    """Severity counts from `npm audit --json` (npm v7+ metadata format)."""
    data = json.loads(text)
    vulns = data.get("metadata", {}).get("vulnerabilities", {})
    return {level: int(vulns.get(level, 0)) for level in NPM_LEVELS}


def _npm_exceeds(counts: dict, level: str) -> bool:
    """True if any vulnerability exists at `level` or a higher severity."""
    idx = NPM_LEVELS.index(level)
    return any(counts.get(l, 0) > 0 for l in NPM_LEVELS[idx:])


def _parse_pip_audit(text: str, ignore: set[str]) -> int:
    """Count pip-audit vulnerabilities (any severity), minus ignored IDs."""
    data = json.loads(text)
    deps = data.get("dependencies", []) if isinstance(data, dict) else data
    count = 0
    for dep in deps:
        for v in dep.get("vulns", []):
            if v.get("id") not in ignore:
                count += 1
    return count


# ── Verdict (FAILS the gate) ──────────────────────────────────────────────────

def _audit_verdict(failed: bool, ran: bool) -> str:
    if not ran:
        return "⚪ SKIP — audit indisponível (instale pip-audit e/ou npm)"
    if failed:
        return "❌ FAIL — vulnerabilidade(s) de dependência encontrada(s)"
    return "✅ PASS — sem vulnerabilidades acima do limiar"


# ── Runner ────────────────────────────────────────────────────────────────────

def run_audit(root: str = ".", environ=None) -> dict:
    """Run available dependency audits. Returns summary; FAILS on vulns >= level."""
    environ = environ if environ is not None else os.environ
    level = _get_fail_level(environ)
    ignore = _parse_ignore(environ)

    ran = False
    failed = False
    details = []

    # Node
    if (Path(root) / "package.json").exists():
        if shutil.which("npm"):
            ran = True
            proc = subprocess.run(_build_npm_audit_command(level), capture_output=True, text=True, cwd=root)
            try:
                counts = _parse_npm_audit(proc.stdout)
                if _npm_exceeds(counts, level):
                    failed = True
                    details.append(f"npm audit: {counts} (limiar={level}) → FAIL")
                else:
                    details.append(f"npm audit: sem vuln ≥ {level}")
            except (json.JSONDecodeError, KeyError):
                details.append("AVISO: npm audit não retornou JSON válido — pulando")
        else:
            details.append("AVISO: package.json presente mas npm não instalado — pulando")

    # Python
    has_py_manifest = (Path(root) / "requirements.txt").exists() or (Path(root) / "pyproject.toml").exists()
    if has_py_manifest:
        if importlib.util.find_spec("pip_audit") is not None:
            ran = True
            proc = subprocess.run(_build_pip_audit_command(), capture_output=True, text=True, cwd=root)
            try:
                n = _parse_pip_audit(proc.stdout, ignore)
                if n > 0:
                    failed = True
                    details.append(f"pip-audit: {n} vuln(s) (qualquer severidade) → FAIL")
                else:
                    details.append("pip-audit: sem vulnerabilidades")
            except (json.JSONDecodeError, KeyError):
                details.append("AVISO: pip-audit não retornou JSON válido — pulando")
        else:
            details.append("AVISO: manifesto Python presente mas pip-audit não instalado — pulando")

    return {"failed": failed, "ran": ran, "details": details,
            "verdict": _audit_verdict(failed, ran)}


def main():
    parser = argparse.ArgumentParser(
        description="TestPilot Dependency Audit — fails the gate on known vulnerabilities",
        epilog=(
            "Env:\n"
            f"  {FAIL_LEVEL_ENV}  npm severity threshold (info|low|moderate|high|critical; default high)\n"
            f"  {IGNORE_ENV}      comma-separated advisory IDs to accept (pip-audit)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root (default: .)")
    args = parser.parse_args()

    print_banner("Dependency Audit", args.root)
    result = run_audit(args.root)
    for line in result["details"]:
        print(f"   {line}")
    print()
    print(result["verdict"])
    sys.exit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
