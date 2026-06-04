"""
TDD — fix #15: RESUMO must process corrections one at a time, not in batch.
Bug: 'Aplicar todas as correções automáticas? (s/n)' batched all fixes into
one operation, contradicting Golden Rule #4 ('uma correção por vez') and
CLAUDE.md ('não empilhe correções num commit').
"""

from pathlib import Path

SKILL_MD = Path(__file__).parent.parent.parent / "SKILL.md"


def _resumo_section() -> str:
    content = SKILL_MD.read_text(encoding="utf-8")
    start = content.find("## RESUMO DE CORRECOES")
    end = content.find("\n## PHASE 14", start)
    assert start != -1, "RESUMO section not found"
    return content[start:end]


def test_no_apply_all_at_once_prompt():
    """'Aplicar todas as correções automáticas?' must not appear — that's batch."""
    assert "Aplicar todas as correções automáticas" not in _resumo_section()


def test_no_aplica_todas_em_sequencia():
    """'Aplica todas as correcoes automaticas em sequencia' must not appear."""
    section = _resumo_section()
    assert "em sequencia" not in section
    assert "em sequência" not in section


def test_one_at_a_time_language_present():
    """RESUMO must contain language indicating one-fix-at-a-time flow."""
    section = _resumo_section()
    indicators = [
        "uma de cada vez",
        "uma correção por vez",
        "uma por vez",
        "1 de cada vez",
        "cada correção individualmente",
        "individualmente",
    ]
    assert any(ind in section for ind in indicators), (
        "RESUMO must describe one-fix-at-a-time flow, not batch"
    )


def test_re_verify_after_each_fix():
    """After each fix, RESUMO must re-run the affected phase before the next."""
    section = _resumo_section()
    reverify_indicators = [
        "re-executa",
        "re-roda",
        "roda novamente",
        "re-run",
        "reexecuta",
        "fase afetada novamente",
        "fase afetada",
    ]
    assert any(ind in section for ind in reverify_indicators), (
        "RESUMO must verify each fix before moving to the next"
    )


def test_commit_suggestion_per_fix():
    """Each fix must suggest its own commit, not one commit for all."""
    section = _resumo_section()
    # Must NOT suggest a single commit for all fixes
    bad_indicators = [
        "fix: [lista do que foi corrigido]\n\nTestPilot auto-fix:\n[correção 1]\n[correção 2]\n[correção 3]",
    ]
    for bad in bad_indicators:
        assert bad not in section, f"Found batch-commit suggestion: {bad!r}"
