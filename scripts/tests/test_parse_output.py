"""
TDD — fix #1: parse_test_output must correctly count tests in all formats.
Bug: returned {total:0, passed:0, failed:0} when all tests pass (no "failed" word).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from report_generator import parse_test_output


# ── pytest formats ────────────────────────────────────────────────────────────

def test_pytest_all_pass():
    out = "==================== 5 passed in 0.12s ===================="
    r = parse_test_output(out)
    assert r["passed"] == 5
    assert r["failed"] == 0
    assert r["total"] == 5


def test_pytest_mixed():
    out = "==================== 3 passed, 2 failed in 0.34s ===================="
    r = parse_test_output(out)
    assert r["passed"] == 3
    assert r["failed"] == 2
    assert r["total"] == 5


def test_pytest_all_fail():
    out = "==================== 4 failed in 0.20s ===================="
    r = parse_test_output(out)
    assert r["passed"] == 0
    assert r["failed"] == 4
    assert r["total"] == 4


def test_pytest_with_errors():
    """pytest errors (collection failures) count as failures."""
    out = "==================== 2 passed, 1 error in 0.10s ===================="
    r = parse_test_output(out)
    assert r["passed"] == 2
    assert r["failed"] == 1
    assert r["total"] == 3


def test_pytest_realistic_output():
    """Multi-line pytest output including FAILED lines and coverage."""
    out = (
        "tests/test_foo.py::test_a PASSED\n"
        "tests/test_foo.py::test_b FAILED\n"
        "FAILED tests/test_foo.py::test_b - AssertionError\n"
        "TOTAL                 100     20    80%\n"
        "==================== 1 passed, 1 failed in 0.55s ====================\n"
    )
    r = parse_test_output(out)
    assert r["passed"] == 1
    assert r["failed"] == 1
    assert r["total"] == 2
    assert r["coverage"] == 80
    assert "tests/test_foo.py::test_b" in r["failures"]


# ── jest formats ──────────────────────────────────────────────────────────────

def test_jest_all_pass():
    out = "Tests:       5 passed, 5 total"
    r = parse_test_output(out)
    assert r["passed"] == 5
    assert r["failed"] == 0
    assert r["total"] == 5


def test_jest_mixed():
    out = "Tests:       3 failed, 2 passed, 5 total"
    r = parse_test_output(out)
    assert r["passed"] == 2
    assert r["failed"] == 3
    assert r["total"] == 5


def test_jest_all_fail():
    out = "Tests:       4 failed, 4 total"
    r = parse_test_output(out)
    assert r["passed"] == 0
    assert r["failed"] == 4
    assert r["total"] == 4


def test_jest_realistic_output():
    """Multi-line jest output."""
    out = (
        " PASS  src/tools/faq.test.js\n"
        " FAIL  src/tools/order.test.js\n"
        "Tests:       1 failed, 3 passed, 4 total\n"
        "Snapshots:   0 total\n"
        "Time:        1.234s\n"
    )
    r = parse_test_output(out)
    assert r["passed"] == 3
    assert r["failed"] == 1
    assert r["total"] == 4


# ── edge cases ────────────────────────────────────────────────────────────────

def test_empty_output():
    r = parse_test_output("")
    assert r["total"] == 0
    assert r["passed"] == 0
    assert r["failed"] == 0
    assert r["coverage"] is None
    assert r["failures"] == []


def test_no_tests_found():
    out = "no tests ran"
    r = parse_test_output(out)
    assert r["total"] == 0


def test_coverage_parsed():
    out = "TOTAL                 100     20    80%\n1 passed in 0.01s"
    r = parse_test_output(out)
    assert r["coverage"] == 80
    assert r["passed"] == 1
