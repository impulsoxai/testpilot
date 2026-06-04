"""
TDD — fix #6: format_severity calls SEVERITY_ICONS as a function (TypeError).
Bug: SEVERITY_ICONS is a dict; SEVERITY_ICONS(key) raises TypeError.
      except only catches ValueError and KeyError — TypeError escapes to caller.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _shared import format_severity


def test_critical_returns_red():
    assert format_severity("critical") == "🔴"


def test_warning_returns_yellow():
    assert format_severity("warning") == "🟡"


def test_info_returns_green():
    assert format_severity("info") == "🟢"


def test_unknown_string_returns_default():
    """Unrecognised severity → safe default, no exception."""
    assert format_severity("unknown") == "⚪"


def test_empty_string_returns_default():
    """Empty string is not a valid severity → safe default, no exception."""
    assert format_severity("") == "⚪"


def test_wrong_case_returns_default():
    """Enum values are lowercase; CRITICAL (uppercase) is invalid → default."""
    assert format_severity("CRITICAL") == "⚪"


def test_never_raises():
    """format_severity must never propagate any exception to the caller."""
    for bad in ["", "none", "fatal", "  ", "🔴", None.__class__.__name__]:
        try:
            result = format_severity(bad)
            assert isinstance(result, str)
        except Exception as exc:
            raise AssertionError(
                f"format_severity({bad!r}) raised {type(exc).__name__}: {exc}"
            )
