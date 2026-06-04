"""
TDD — fix #2: Phase 1 must parse .env file directly, not rely on os.getenv.
Bug: vars defined only in .env (not exported) were flagged as missing.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from env_check import check_env_vars


def test_all_vars_in_dotenv(tmp_path):
    """All required vars present in .env file → no missing."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("DB_URL=\nSECRET=\n")
    env.write_text("DB_URL=postgres://localhost/db\nSECRET=abc123\n")

    required, missing = check_env_vars(example, env)

    assert missing == []
    assert set(required) == {"DB_URL", "SECRET"}


def test_var_missing_from_dotenv(tmp_path):
    """Var in .env.example but absent from .env → flagged."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("DB_URL=\nSECRET=\n")
    env.write_text("DB_URL=postgres://localhost/db\n")

    required, missing = check_env_vars(example, env)

    assert missing == ["SECRET"]


def test_var_in_os_environ_not_in_dotenv(tmp_path):
    """Var exported in shell but not in .env → not flagged."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("TOKEN=\n")
    env.write_text("")

    required, missing = check_env_vars(example, env, extra_environ={"TOKEN": "abc"})

    assert missing == []


def test_no_env_example_returns_empty(tmp_path):
    """No .env.example → skip check (return empty lists, no error)."""
    env = tmp_path / ".env"
    env.write_text("SOMETHING=value\n")

    required, missing = check_env_vars(tmp_path / ".env.example", env)

    assert required == []
    assert missing == []


def test_empty_value_in_dotenv_flagged(tmp_path):
    """Key present in .env but with empty value → flagged as missing."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("SECRET=\n")
    env.write_text("SECRET=\n")

    required, missing = check_env_vars(example, env)

    assert "SECRET" in missing


def test_no_dotenv_file_var_in_environ(tmp_path):
    """No .env file, var is in os.environ → not flagged."""
    example = tmp_path / ".env.example"
    example.write_text("TOKEN=\n")

    required, missing = check_env_vars(
        example, tmp_path / ".env", extra_environ={"TOKEN": "val"}
    )

    assert missing == []


def test_comment_lines_ignored(tmp_path):
    """Comment lines in .env.example must not appear in required."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("# This is a comment\nDB_URL=\n")
    env.write_text("DB_URL=postgres://localhost/db\n")

    required, missing = check_env_vars(example, env)

    assert "# This is a comment" not in required
    assert missing == []


def test_value_with_equals_sign(tmp_path):
    """Value containing '=' (e.g. connection strings) parses correctly."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("DB_URL=\n")
    env.write_text("DB_URL=postgres://user:pass@host/db?ssl=true\n")

    required, missing = check_env_vars(example, env)

    assert missing == []


def test_os_environ_overrides_dotenv(tmp_path):
    """os.environ value wins over .env value (both present)."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("SECRET=\n")
    env.write_text("SECRET=from-file\n")

    required, missing = check_env_vars(
        example, env, extra_environ={"SECRET": "from-env"}
    )

    assert missing == []


def test_multiple_missing(tmp_path):
    """Multiple missing vars all reported."""
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("A=\nB=\nC=\n")
    env.write_text("A=present\n")

    required, missing = check_env_vars(example, env)

    assert set(missing) == {"B", "C"}
