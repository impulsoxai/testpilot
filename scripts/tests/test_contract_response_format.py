"""
TDD — fix #5: check_mcp_response_format raises NameError because mcp_call_tool
is called but not imported in contract_test.py.
"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import contract_test
from contract_test import check_mcp_response_format


def test_mcp_call_tool_in_contract_test_namespace():
    """mcp_call_tool must exist in contract_test namespace — else NameError at runtime."""
    assert hasattr(contract_test, "mcp_call_tool"), (
        "mcp_call_tool not imported in contract_test.py — "
        "check_mcp_response_format will crash with NameError on every call"
    )


def test_valid_response_no_issues():
    """Valid MCP content response → valid=True, issues=[]."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {
            "result": {
                "content": [{"type": "text", "text": "✅ ok"}]
            }
        }
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is True
    assert result["issues"] == []


def test_missing_content_field_reported():
    """result present but 'content' absent → issue reported."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {"result": {}}
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is False
    assert any("content" in issue for issue in result["issues"])


def test_content_not_list_reported():
    """'content' is not a list → issue reported."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {"result": {"content": "not a list"}}
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is False
    assert any("not an array" in issue or "array" in issue.lower() for issue in result["issues"])


def test_content_item_missing_type_reported():
    """Content item missing 'type' key → issue reported."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {
            "result": {
                "content": [{"text": "hello"}]  # 'type' absent
            }
        }
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is False
    assert any("type" in issue for issue in result["issues"])


def test_content_item_missing_text_reported():
    """Content item missing 'text' key → issue reported."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {
            "result": {
                "content": [{"type": "text"}]  # 'text' absent
            }
        }
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is False
    assert any("text" in issue for issue in result["issues"])


def test_error_response_with_code_and_message_valid():
    """JSON-RPC error response with code+message → valid (well-formed error)."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {
            "error": {"code": -32600, "message": "Invalid request"}
        }
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is True


def test_error_response_missing_code_reported():
    """Error response missing 'code' → issue reported."""
    with patch.object(contract_test, "mcp_call_tool") as mock_tool:
        mock_tool.return_value = {
            "error": {"message": "Something failed"}  # 'code' absent
        }
        result = check_mcp_response_format("http://localhost", "my_tool")

    assert result["valid"] is False
    assert any("code" in issue for issue in result["issues"])
