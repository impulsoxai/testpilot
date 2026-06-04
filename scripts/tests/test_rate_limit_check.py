"""
TDD — fix #7: rate-limit test endpoint must be configurable via RATE_LIMIT_ENDPOINT.
Bug: endpoint hardcoded to /health — any project where rate-limiting lives elsewhere
(e.g. /token, /api, /login) silently reports 'no rate limiting' (false NEGATIVO).
Fix: read RATE_LIMIT_ENDPOINT from env; fallback to /health with explicit AVISO.
"""

import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from rate_limit_check import get_rate_limit_endpoint, ENDPOINT_ENV_VAR, FALLBACK_ENDPOINT


# ── Endpoint resolution ───────────────────────────────────────────────────────

def test_uses_env_var_when_set():
    """RATE_LIMIT_ENDPOINT set → use it, no fallback."""
    with patch.dict(os.environ, {ENDPOINT_ENV_VAR: "/token"}):
        endpoint, used_fallback = get_rate_limit_endpoint()
    assert endpoint == "/token"
    assert used_fallback is False


def test_falls_back_to_health_when_not_set():
    """RATE_LIMIT_ENDPOINT absent → fallback to /health."""
    env = {k: v for k, v in os.environ.items() if k != ENDPOINT_ENV_VAR}
    with patch.dict(os.environ, env, clear=True):
        endpoint, used_fallback = get_rate_limit_endpoint()
    assert endpoint == FALLBACK_ENDPOINT
    assert used_fallback is True


def test_strips_whitespace_from_endpoint():
    """Leading/trailing whitespace in env var is stripped."""
    with patch.dict(os.environ, {ENDPOINT_ENV_VAR: "  /api/v1/auth  "}):
        endpoint, used_fallback = get_rate_limit_endpoint()
    assert endpoint == "/api/v1/auth"
    assert used_fallback is False


def test_empty_env_var_treated_as_absent():
    """RATE_LIMIT_ENDPOINT='' (empty) falls back to /health."""
    with patch.dict(os.environ, {ENDPOINT_ENV_VAR: ""}):
        endpoint, used_fallback = get_rate_limit_endpoint()
    assert endpoint == FALLBACK_ENDPOINT
    assert used_fallback is True


def test_fallback_constant_is_health():
    """Fallback endpoint must be /health (documented default)."""
    assert FALLBACK_ENDPOINT == "/health"


def test_env_var_name_is_rate_limit_endpoint():
    """Env var name must be RATE_LIMIT_ENDPOINT (documented in AVISO)."""
    assert ENDPOINT_ENV_VAR == "RATE_LIMIT_ENDPOINT"


# ── Warning output ────────────────────────────────────────────────────────────

def test_warning_printed_when_using_fallback(capsys):
    """When falling back to /health, must print AVISO with env var name."""
    from rate_limit_check import warn_if_fallback
    env = {k: v for k, v in os.environ.items() if k != ENDPOINT_ENV_VAR}
    with patch.dict(os.environ, env, clear=True):
        warn_if_fallback(used_fallback=True)
    captured = capsys.readouterr()
    assert "AVISO" in captured.out
    assert ENDPOINT_ENV_VAR in captured.out
    assert FALLBACK_ENDPOINT in captured.out


def test_no_warning_when_endpoint_explicitly_set(capsys):
    """When RATE_LIMIT_ENDPOINT is set, no AVISO must appear."""
    from rate_limit_check import warn_if_fallback
    warn_if_fallback(used_fallback=False)
    captured = capsys.readouterr()
    assert "AVISO" not in captured.out


def test_warning_mentions_how_to_fix(capsys):
    """AVISO must tell user what env var to set (actionable)."""
    from rate_limit_check import warn_if_fallback
    warn_if_fallback(used_fallback=True)
    captured = capsys.readouterr()
    assert "RATE_LIMIT_ENDPOINT" in captured.out
