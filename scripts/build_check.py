"""
TestPilot — Build Gate
Verifies the project compiles before the test phases. A broken build makes every
downstream phase meaningless. Node/TS focused: `npm run build` when a build script
exists, else `tsc --noEmit` when tsconfig.json is present. Pure Python has no
universal build → SKIP (unit tests already catch import/syntax errors). A build
failure FAILS the phase.

Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from _shared import print_banner


def _load_package_json(path) -> dict | None:
    """Parse package.json; None if missing or invalid."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _has_build_script(package_json) -> bool:
    return bool(package_json) and "build" in package_json.get("scripts", {})


def _detect_build_command(package_json, has_tsconfig: bool) -> list[str] | None:
    """Decide the build command. None → nothing to build (skip)."""
    if _has_build_script(package_json):
        return ["npm", "run", "build"]
    if has_tsconfig:
        return ["npx", "--no-install", "tsc", "--noEmit"]
    return None


def _build_verdict(returncode: int, ran: bool) -> str:
    if not ran:
        return "⚪ SKIP — nada para buildar (Python puro ou sem build configurado)"
    if returncode == 0:
        return "✅ PASS — build OK"
    return f"❌ FAIL — build quebrou (exit {returncode})"


def run_build_check(root: str = ".") -> dict:
    """Run the build gate. FAILS on non-zero build exit."""
    pkg = _load_package_json(Path(root) / "package.json")
    has_ts = (Path(root) / "tsconfig.json").exists()
    cmd = _detect_build_command(pkg, has_ts)

    if cmd is None:
        return {"failed": False, "ran": False,
                "details": ["Sem build configurado — pulando (testes cobrem compilação)"],
                "verdict": _build_verdict(0, ran=False)}

    tool = cmd[0]
    if not shutil.which(tool):
        return {"failed": False, "ran": False,
                "details": [f"AVISO: build requer '{tool}' mas não está instalado — pulando"],
                "verdict": _build_verdict(0, ran=False)}

    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=root)
    failed = proc.returncode != 0
    details = [f"comando: {' '.join(cmd)}"]
    if failed:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-10:]
        details.extend(tail)

    return {"failed": failed, "ran": True, "details": details,
            "verdict": _build_verdict(proc.returncode, ran=True)}


def main():
    parser = argparse.ArgumentParser(
        description="TestPilot Build Gate — fails the phase when the build breaks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root (default: .)")
    args = parser.parse_args()

    print_banner("Build", args.root)
    result = run_build_check(args.root)
    for line in result["details"]:
        print(f"   {line}")
    print()
    print(result["verdict"])
    sys.exit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
