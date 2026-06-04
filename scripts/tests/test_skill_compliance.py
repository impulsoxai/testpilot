"""
TDD — fix #3: SKILL.md must never auto-execute git push, git add ., or claim deploy.
Bug: RESUMO section executed `git add . && git commit && git push` automatically,
contradicting its own RULES #2 and #3.
"""

import re
from pathlib import Path

SKILL_MD = Path(__file__).parent.parent.parent / "SKILL.md"


def _content():
    return SKILL_MD.read_text(encoding="utf-8")


def test_no_deploy_ready_claim():
    """'Deploy pronto' must not appear — TestPilot never deploys."""
    assert "Deploy pronto" not in _content()


def test_no_railway_reference_in_auto_flow():
    """'Aguardando Railway' must not appear — TestPilot never deploys."""
    assert "Aguardando Railway" not in _content()


def test_git_push_not_automatic_action():
    """
    'git push' must not appear as a bullet-point action Claude executes.
    Pattern: '- git push' or '* git push' as a list item.
    Allowed: inside a code block labeled as 'run manually' / user suggestion.
    """
    content = _content()
    bad = re.search(r"^[-*]\s+git push", content, re.MULTILINE)
    assert bad is None, (
        f"'git push' appears as an automatic action at: "
        f"...{content[bad.start()-50:bad.end()+50]}..."
    )


def test_git_add_dot_not_automatic_action():
    """
    'git add .' must not appear as a bullet-point action Claude executes.
    Staging all files risks including secrets or unrelated changes.
    """
    content = _content()
    bad = re.search(r"^[-*]\s+git add \.", content, re.MULTILINE)
    assert bad is None, (
        f"'git add .' appears as an automatic action at: "
        f"...{content[bad.start()-50:bad.end()+50]}..."
    )


def test_commit_push_question_removed():
    """'→ Fazer commit e push?' must not appear — push is never Claude's call."""
    assert "Fazer commit e push" not in _content()


def test_resumo_shows_manual_commands():
    """After fixes, RESUMO must guide user to run commands manually."""
    content = _content()
    # After the fix, RESUMO should contain language about manual execution
    resumo_start = content.find("## RESUMO DE CORRECOES")
    assert resumo_start != -1, "RESUMO section not found"
    resumo_section = content[resumo_start:resumo_start + 1500]
    # Must contain some indication that commands are for the user to run
    manual_indicators = ["manualmente", "rode manualmente", "Para commitar", "run manually"]
    assert any(ind in resumo_section for ind in manual_indicators), (
        "RESUMO section must instruct user to run git commands manually"
    )


def test_rules_no_commit_no_deploy_still_present():
    """Sanity check: RULES #2 and #3 must still exist."""
    content = _content()
    assert "NEVER commit automatically" in content
    assert "NEVER deploy" in content
