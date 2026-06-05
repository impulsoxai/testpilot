"""
TestPilot — Code Quality (lint) check
Runs ruff (Python) and eslint (Node) when available, cross-platform, and reports
findings as WARNINGS only — lint never fails the gate. Skips gracefully when no
linter is installed.
Built by ImpulsoX AI — github.com/impulsoxai/testpilot
"""

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from _shared import print_banner


# ── Detection ─────────────────────────────────────────────────────────────────

def _detect_python_linter(
    find_spec_fn=importlib.util.find_spec,
    which_fn=shutil.which,
) -> str | None:
    """Prefer ruff (importable module), fall back to pyflakes, else None."""
    if find_spec_fn("ruff") is not None:
        return "ruff"
    if find_spec_fn("pyflakes") is not None or which_fn("pyflakes"):
        return "pyflakes"
    return None


def _detect_node_linter(
    which_fn=shutil.which,
    path_exists_fn=os.path.exists,
) -> str | None:
    """Prefer a project-local eslint, then global eslint, then npx, else None."""
    local = os.path.join("node_modules", ".bin", "eslint")
    if path_exists_fn(local):
        return local
    if which_fn("eslint"):
        return "eslint"
    if which_fn("npx"):
        return "npx"
    return None


# ── Command building ──────────────────────────────────────────────────────────

def _build_lint_command(tool: str, files: list[str], python_exe: str = sys.executable) -> list[str]:
    """Build the argv for a linter. Uses `python -m` for ruff/pyflakes (no PATH dependency)."""
    if tool == "ruff":
        return [python_exe, "-m", "ruff", "check", *files]
    if tool == "pyflakes":
        return [python_exe, "-m", "pyflakes", *files]
    if tool == "npx":
        return ["npx", "--no-install", "eslint", *files]
    # tool is an eslint executable ("eslint" or a path)
    return [tool, *files]


# ── Output parsing ────────────────────────────────────────────────────────────

def _parse_ruff_output(text: str) -> int:
    """Number of ruff findings. Prefers the 'Found N error(s).' summary."""
    m = re.search(r"Found (\d+) error", text)
    if m:
        return int(m.group(1))
    if "All checks passed" in text:
        return 0
    return len(re.findall(r"^.+?:\d+:\d+:", text, flags=re.MULTILINE))


def _parse_eslint_output(text: str) -> tuple[int, int]:
    """Return (errors, warnings) from eslint's '✖ N problems (E errors, W warnings)'."""
    m = re.search(r"\((\d+) errors?, (\d+) warnings?\)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


# ── Verdict (WARN only, never FAIL) ───────────────────────────────────────────

def _lint_verdict(total_issues: int, ran: bool) -> str:
    if not ran:
        return "⚪ SKIP — nenhum linter disponível (instale ruff e/ou eslint)"
    if total_issues == 0:
        return "✅ PASS — sem problemas de lint"
    return f"⚠️  {total_issues} problema(s) de lint (não bloqueia o gate)"


# ── File discovery ────────────────────────────────────────────────────────────

def _find_files(root: str, patterns: list[str], skip_dirs: set[str]) -> list[str]:
    out = []
    for p in patterns:
        for f in Path(root).rglob(p):
            if not any(part in skip_dirs for part in f.parts):
                out.append(str(f))
    return out


# ── Runner ────────────────────────────────────────────────────────────────────

def run_lint(root: str = ".") -> dict:
    """Run available linters over the project. Returns a summary dict."""
    skip = {"node_modules", ".venv", "venv", ".git", "__pycache__", "dist", "build"}
    py_files = _find_files(root, ["*.py"], skip)
    js_files = _find_files(root, ["*.js", "*.jsx", "*.ts", "*.tsx"], skip)

    total = 0
    ran = False
    details = []

    if py_files:
        tool = _detect_python_linter()
        if tool:
            ran = True
            cmd = _build_lint_command(tool, py_files)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            issues = _parse_ruff_output(proc.stdout + proc.stderr)
            total += issues
            details.append(f"{tool}: {issues} issue(s) em {len(py_files)} arquivo(s) Python")
        else:
            details.append("AVISO: arquivos Python encontrados mas ruff/pyflakes não instalados — pulando")

    if js_files:
        tool = _detect_node_linter()
        if tool:
            ran = True
            cmd = _build_lint_command(tool, js_files)
            proc = subprocess.run(cmd, capture_output=True, text=True)
            errors, warnings = _parse_eslint_output(proc.stdout + proc.stderr)
            total += errors + warnings
            details.append(
                f"eslint: {errors} erro(s), {warnings} aviso(s) em {len(js_files)} arquivo(s) Node"
            )
        else:
            details.append("AVISO: arquivos Node encontrados mas eslint/npx não instalados — pulando")

    return {"total_issues": total, "ran": ran, "details": details,
            "verdict": _lint_verdict(total, ran)}


def main():
    parser = argparse.ArgumentParser(
        description="TestPilot Code Quality — runs ruff/eslint, reports lint as warnings (never fails the gate)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root to lint (default: .)")
    args = parser.parse_args()

    print_banner("Lint", args.root)
    result = run_lint(args.root)
    for line in result["details"]:
        print(f"   {line}")
    print()
    print(result["verdict"])
    # Lint never fails the gate.
    sys.exit(0)


if __name__ == "__main__":
    main()
