"""
TDD — fix #10b: build gate. A broken build makes every downstream phase
meaningless, so verify the project compiles before unit tests (Phase 2).
Node/TS focused: `npm run build` if a build script exists, else `tsc --noEmit`
when tsconfig.json is present. Pure Python has no universal build -> SKIP (unit
tests already catch import/syntax errors). Build failure FAILS the phase.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from build_check import (
    _load_package_json,
    _has_build_script,
    _detect_build_command,
    _build_verdict,
)


# ── package.json loading ──────────────────────────────────────────────────────

def test_load_package_json_valid(tmp_path):
    f = tmp_path / "package.json"
    f.write_text(json.dumps({"scripts": {"build": "tsc"}}), encoding="utf-8")
    assert _load_package_json(f) == {"scripts": {"build": "tsc"}}


def test_load_package_json_missing(tmp_path):
    assert _load_package_json(tmp_path / "nope.json") is None


def test_load_package_json_invalid_returns_none(tmp_path):
    f = tmp_path / "package.json"
    f.write_text("{ not json", encoding="utf-8")
    assert _load_package_json(f) is None


# ── build-script detection ────────────────────────────────────────────────────

def test_has_build_script_true():
    assert _has_build_script({"scripts": {"build": "vite build"}}) is True


def test_has_build_script_false_no_build():
    assert _has_build_script({"scripts": {"test": "jest"}}) is False


def test_has_build_script_false_no_scripts():
    assert _has_build_script({"name": "x"}) is False


def test_has_build_script_none():
    assert _has_build_script(None) is False


# ── command detection ─────────────────────────────────────────────────────────

def test_detect_npm_run_build_when_script_present():
    cmd = _detect_build_command({"scripts": {"build": "tsc"}}, has_tsconfig=False)
    assert cmd == ["npm", "run", "build"]


def test_detect_tsc_when_only_tsconfig():
    cmd = _detect_build_command(None, has_tsconfig=True)
    assert cmd == ["npx", "--no-install", "tsc", "--noEmit"]


def test_detect_build_script_takes_priority_over_tsconfig():
    cmd = _detect_build_command({"scripts": {"build": "vite build"}}, has_tsconfig=True)
    assert cmd == ["npm", "run", "build"]


def test_detect_none_for_pure_python():
    assert _detect_build_command(None, has_tsconfig=False) is None


def test_detect_none_when_package_has_no_build_and_no_tsconfig():
    assert _detect_build_command({"scripts": {"test": "jest"}}, has_tsconfig=False) is None


# ── verdict: build failure FAILS the gate ─────────────────────────────────────

def test_verdict_skip_when_not_ran():
    v = _build_verdict(returncode=0, ran=False)
    assert "SKIP" in v
    assert "❌" not in v


def test_verdict_pass_on_zero_exit():
    v = _build_verdict(returncode=0, ran=True)
    assert "✅" in v or "PASS" in v
    assert "❌" not in v


def test_verdict_fail_on_nonzero_exit():
    v = _build_verdict(returncode=2, ran=True)
    assert "❌" in v


def test_verdict_fail_on_any_nonzero():
    for rc in (1, 2, 127):
        assert "❌" in _build_verdict(rc, ran=True)
