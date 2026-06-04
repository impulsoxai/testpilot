"""
TDD — fix #14: dead imports, VERSION constant, SKILL.md description.
"""

import subprocess
import sys
import re
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent
SKILL_MD = SCRIPTS_DIR.parent / "SKILL.md"

CHECKED_FILES = [
    "_shared.py",
    "security_test.py",
    "contract_test.py",
    "load_test.py",
    "report_generator.py",
    "env_check.py",
]


# ── Dead imports ──────────────────────────────────────────────────────────────

def test_no_unused_imports():
    """pyflakes must report zero 'imported but unused' warnings across all scripts."""
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes"] + CHECKED_FILES,
        capture_output=True,
        text=True,
        cwd=SCRIPTS_DIR,
    )
    unused = [
        line for line in result.stdout.splitlines()
        if "imported but unused" in line
    ]
    assert unused == [], (
        f"Unused imports found:\n" + "\n".join(unused)
    )


# ── VERSION constant ──────────────────────────────────────────────────────────

def test_version_defined_in_shared():
    """_shared.py must export a VERSION string constant."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    import importlib
    import _shared
    importlib.reload(_shared)
    assert hasattr(_shared, "VERSION"), "_shared.py must define VERSION"
    assert isinstance(_shared.VERSION, str) and _shared.VERSION, "VERSION must be non-empty string"


def test_report_generator_uses_version():
    """generate_report output must contain the VERSION string (not hardcoded literal)."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    import importlib
    import _shared, report_generator
    importlib.reload(_shared)
    importlib.reload(report_generator)

    output = report_generator.generate_report(
        project_name="TestProject",
        phases={"env": {"status": "pass"}},
    )
    assert _shared.VERSION in output, (
        f"VERSION ({_shared.VERSION}) not found in report output"
    )


# ── SKILL.md description ──────────────────────────────────────────────────────

def test_description_no_after_any_code_change():
    """Description must not say 'after any code change' — causes over-triggering."""
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "after any code change" not in content, (
        "SKILL.md description still contains 'after any code change'"
    )


def test_disable_model_invocation_is_true():
    """disable-model-invocation must be true — testpilot requires explicit /testpilot."""
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "disable-model-invocation: true" in content, (
        "SKILL.md must have disable-model-invocation: true to prevent auto-triggering"
    )
