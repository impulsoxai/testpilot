"""
TDD — fix #4b: configurable REST security targets.
Bug: REST mode only knew /test with {"input": payload}. Real APIs have their own
routes and body shapes, so payloads never reached real logic.
Fix: load targets from SECURITY_TARGETS (JSON file) or testpilot.targets.json,
inject the §PAYLOAD§ marker into the configured route/shape, build one request
per target. No targets configured → /test fallback (the #4a guard still catches
the resulting 404s so the gate never reports a false PASS).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from security_test import (
    PAYLOAD_MARKER,
    _inject_payload,
    _build_requests,
    _load_targets,
)


# ── _inject_payload: marker substitution ──────────────────────────────────────

def test_inject_into_flat_body_field():
    """Marker in a body value is replaced with the payload."""
    target = {"method": "POST", "path": "/api/reservation",
              "body": {"name": PAYLOAD_MARKER, "party_size": 2}}
    method, path, body = _inject_payload(target, "'; DROP TABLE users; --")
    assert method == "POST"
    assert path == "/api/reservation"
    assert body == {"name": "'; DROP TABLE users; --", "party_size": 2}


def test_inject_into_nested_body():
    """Marker nested inside dicts/lists is reached."""
    target = {"path": "/x", "body": {"outer": {"inner": [PAYLOAD_MARKER]}}}
    _, _, body = _inject_payload(target, "xss")
    assert body == {"outer": {"inner": ["xss"]}}


def test_inject_whole_value_preserves_type():
    """When a value IS exactly the marker, the raw payload type is preserved."""
    target = {"path": "/x", "body": {"input": PAYLOAD_MARKER}}
    _, _, body = _inject_payload(target, None)
    assert body == {"input": None}
    _, _, body = _inject_payload(target, 999)
    assert body == {"input": 999}
    _, _, body = _inject_payload(target, [])
    assert body == {"input": []}


def test_inject_marker_embedded_in_string_stringifies():
    """Marker inside a larger string → str() substitution."""
    target = {"path": "/x", "body": {"q": f"search={PAYLOAD_MARKER}!"}}
    _, _, body = _inject_payload(target, 42)
    assert body == {"q": "search=42!"}


def test_inject_into_path():
    """Marker in the path is replaced (path-param injection)."""
    target = {"method": "GET", "path": f"/users/{PAYLOAD_MARKER}"}
    method, path, body = _inject_payload(target, "../../etc/passwd")
    assert method == "GET"
    assert path == "/users/../../etc/passwd"
    assert body is None


def test_inject_method_defaults_to_post_and_uppercases():
    target = {"path": "/x", "body": {"a": PAYLOAD_MARKER}}
    method, _, _ = _inject_payload(target, "p")
    assert method == "POST"
    target2 = {"method": "put", "path": "/x"}
    method2, _, _ = _inject_payload(target2, "p")
    assert method2 == "PUT"


# ── _build_requests: request specs without HTTP ───────────────────────────────

def test_build_requests_mcp_mode():
    """MCP mode yields a single /mcp tools/call request."""
    reqs = list(_build_requests("http://h", "payload", True, "my_tool", None, 1))
    assert len(reqs) == 1
    method, url, body = reqs[0]
    assert method == "POST"
    assert url == "http://h/mcp"
    assert body["method"] == "tools/call"
    assert body["params"]["name"] == "my_tool"


def test_build_requests_with_targets_one_per_target():
    """REST + targets yields one request per configured target."""
    targets = [
        {"method": "POST", "path": "/a", "body": {"x": PAYLOAD_MARKER}},
        {"method": "GET", "path": f"/b/{PAYLOAD_MARKER}"},
    ]
    reqs = list(_build_requests("http://h", "PWN", False, None, targets, 1))
    assert len(reqs) == 2
    assert reqs[0] == ("POST", "http://h/a", {"x": "PWN"})
    assert reqs[1] == ("GET", "http://h/b/PWN", None)


def test_build_requests_no_targets_falls_back_to_test():
    """REST with no targets → single /test fallback (guarded by #4a)."""
    reqs = list(_build_requests("http://h", "payload", False, None, None, 1))
    assert len(reqs) == 1
    method, url, body = reqs[0]
    assert method == "POST"
    assert url == "http://h/test"
    assert body == {"input": "payload"}


# ── _load_targets: env var + file ─────────────────────────────────────────────

def test_load_targets_from_env_path(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"targets": [{"path": "/a"}]}), encoding="utf-8")
    targets = _load_targets(env_value=str(f), default_file="nonexistent.json")
    assert targets == [{"path": "/a"}]


def test_load_targets_from_default_file(tmp_path):
    f = tmp_path / "testpilot.targets.json"
    f.write_text(json.dumps({"targets": [{"path": "/x"}]}), encoding="utf-8")
    targets = _load_targets(env_value="", default_file=str(f))
    assert targets == [{"path": "/x"}]


def test_load_targets_bare_list(tmp_path):
    """Accept a bare JSON list too, not only {'targets': [...]}."""
    f = tmp_path / "t.json"
    f.write_text(json.dumps([{"path": "/a"}]), encoding="utf-8")
    assert _load_targets(env_value=str(f), default_file="x") == [{"path": "/a"}]


def test_load_targets_none_when_nothing_configured(tmp_path):
    missing = tmp_path / "absent.json"
    assert _load_targets(env_value="", default_file=str(missing)) is None


def test_load_targets_none_when_empty_targets(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"targets": []}), encoding="utf-8")
    assert _load_targets(env_value=str(f), default_file="x") is None


def test_payload_marker_constant():
    assert PAYLOAD_MARKER == "§PAYLOAD§"
