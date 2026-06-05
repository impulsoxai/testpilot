"""
TDD — fix #L013-b: print_banner raises UnicodeEncodeError on Windows consoles
with cp1252 encoding (emoji like 🔍 not representable).
Fix: write via sys.stdout with errors='replace' so the banner always prints,
with '?' substituted for unencodable chars, instead of crashing.
"""

import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _shared import print_banner


def _strict_stdout(encoding):
    """TextIOWrapper with errors='strict' — mirrors a real Windows console."""
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict")


def _lenient_stdout(encoding):
    """TextIOWrapper with errors='replace' — mirrors a fixed console."""
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="replace")


def _run_banner(test_type, target, fake_stdout):
    old = sys.stdout
    sys.stdout = fake_stdout
    try:
        print_banner(test_type, target)
    finally:
        sys.stdout = old
    fake_stdout.seek(0)
    return fake_stdout.read()


# ── Demonstrates the bug (strict cp1252) ─────────────────────────────────────

def test_bug_banner_crashes_on_strict_cp1252():
    """Reproduces the real crash: strict cp1252 stdout + emoji → UnicodeEncodeError."""
    try:
        _run_banner("Security", "http://h", _strict_stdout("cp1252"))
        # If no exception, the fix is already in — that's fine (test passes)
    except UnicodeEncodeError:
        # Bug confirmed present: this test documents it.
        # Once the fix is in, this branch won't be reached.
        pass  # Will flip after fix — see tests below


# ── Post-fix requirements ─────────────────────────────────────────────────────

def test_banner_does_not_raise_on_strict_cp1252():
    """After fix: print_banner must not raise on a strict cp1252 stdout."""
    try:
        _run_banner("Security", "http://example.com", _strict_stdout("cp1252"))
    except UnicodeEncodeError as e:
        raise AssertionError(f"print_banner raised UnicodeEncodeError on cp1252: {e}") from e


def test_banner_does_not_raise_on_strict_ascii():
    try:
        _run_banner("Lint", ".", _strict_stdout("ascii"))
    except UnicodeEncodeError as e:
        raise AssertionError(f"print_banner raised UnicodeEncodeError on ASCII: {e}") from e


def test_banner_contains_test_type_on_ascii():
    text = _run_banner("Regression", "http://h", _lenient_stdout("ascii"))
    assert "Regression" in text


def test_banner_contains_target_on_ascii():
    text = _run_banner("Build", "http://h:8080", _lenient_stdout("ascii"))
    assert "http://h:8080" in text


def test_banner_utf8_still_shows_emoji():
    """On a UTF-8 stdout the full emoji must survive unmodified."""
    text = _run_banner("Security", "http://h", _lenient_stdout("utf-8"))
    assert "🔒" in text


def test_unknown_type_fallback_does_not_crash_strict_cp1252():
    """Fallback icon (🔍) must not crash on strict cp1252."""
    try:
        _run_banner("Unknown", ".", _strict_stdout("cp1252"))
    except UnicodeEncodeError as e:
        raise AssertionError(f"fallback icon crashed on cp1252: {e}") from e
