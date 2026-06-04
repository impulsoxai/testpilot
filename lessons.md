# TestPilot — Lessons Learned

## L-001 — parse_test_output: AND condition hides all-green results

**Symptom:** Suite 100% verde reportada como `{total:0, passed:0, failed:0}`.

**Root cause:** `if "passed" in line and "failed" in line` — exige AMBAS as
palavras na mesma linha. Pytest all-pass imprime `"5 passed in 0.12s"` sem a
palavra "failed"; jest all-pass imprime `"Tests: 5 passed, 5 total"`. Condição
nunca satisfeita → zero em tudo.

**Fix:** Buscar cada métrica de forma independente no output completo:
`re.search(r"(\d+) passed", output)` separado de `re.search(r"(\d+) failed", output)`.
Jest: override via linha `Tests:` quando presente.

**Impacto real:** Gate da Fase 9 do B.L.A.S.T. declarava VERDE (0 falhas)
mesmo quando havia falhas, E declarava 0 testes mesmo em suite 100% verde —
report inútil em ambos os sentidos.

**Commit:** `272c096` — `fix(report_generator): parse_test_output returns zeros when all tests pass`

**Testes adicionados:** `scripts/tests/test_parse_output.py` — 12 casos cobrindo
pytest all-pass/all-fail/mixed/errors, jest all-pass/all-fail/mixed,
cobertura, FAILED lines, output vazio.
