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

---

## L-002 — Phase 1: os.getenv não lê .env não-exportado

**Symptom:** Fase 1 reportava "❌ Missing env vars" mesmo com `.env` completo.
Auto-correção escrevia placeholder, re-checava via `os.getenv` (ainda vazio),
falhava de novo → loop até "manual action needed".

**Root cause:** `os.getenv(k)` lê `os.environ` (variáveis exportadas no processo).
Arquivo `.env` nunca é sourced automaticamente — Claude Code não exporta `.env`
pro ambiente antes de rodar o python -c. Resultado: toda variável definida só
no arquivo `.env` era invisível.

**Fix:** Parsear `.env` como arquivo diretamente (igual ao `.env.example`),
mesclar com `os.environ` (`{**parse_env_file('.env'), **os.environ}`). Usar
`str.partition('=')` em vez de `split('=')[0]` para lidar com valores que
contêm `=` (connection strings, URLs com parâmetros).

**Artefatos:** `scripts/env_check.py` (módulo standalone + testável); SKILL.md
Phase 1 inline code atualizado com mesma lógica.

**Commit:** `8e4d401` — `fix(phase-1): parse .env file directly instead of os.getenv`

**Testes adicionados:** `scripts/tests/test_env_check.py` — 10 casos cobrindo
all-present, missing, os.environ override, no .env.example, empty value,
value-with-equals, comments, no .env file + var in environ.

---

## L-003 — RESUMO: git push automático contradiz as próprias RULES

**Symptom:** Após aprovar correções, SKILL.md executava `git add .`,
`git commit` e `git push` automaticamente, terminando com
"✅ Deploy pronto! Aguardando Railway...".

**Root cause:** Contradição interna: as próprias RULES #2 e #3 do SKILL.md
dizem "NEVER commit automatically" e "NEVER deploy", mas a seção RESUMO
as violava. `git add .` ainda arriscava incluir segredos e arquivos não
relacionados.

**Fix:** Substituir o bloco de execução automática por um bloco de
"comandos para rodar manualmente" — o usuário vê os comandos exatos,
revisa o diff, e decide quando e o que commitar/pushar.

**Commit:** `2f42573` — `fix(resumo): remove automatic git push, add ., and deploy claims`

**Testes adicionados:** `scripts/tests/test_skill_compliance.py` — 7 casos
de compliance: ausência de "Deploy pronto", "Aguardando Railway", "- git push",
"- git add .", "Fazer commit e push"; presença de linguagem de "rode manualmente".

---

## L-004 — contract_test.py: mcp_call_tool chamado sem estar importado

**Symptom:** `check_mcp_response_format` lançava `NameError: name 'mcp_call_tool'
is not defined` toda vez que era chamada — Phase 5 (Contract Tests) quebrava silenciosamente.

**Root cause:** Função na linha 78 chama `mcp_call_tool(...)` mas o bloco de import
só trazia `mcp_call`. Symbol nunca importado → NameError em runtime. pyflakes
confirma: `contract_test.py:78:16: undefined name 'mcp_call_tool'`.

**Fix:** Adicionar `mcp_call_tool` ao import de `_shared` em `contract_test.py` — uma linha.

**Commit:** `f9c1400` — `fix(contract_test): import mcp_call_tool to fix NameError at runtime`

**Testes adicionados:** `scripts/tests/test_contract_response_format.py` — 8 casos:
verificação do símbolo no namespace do módulo + respostas MCP válidas/inválidas
(content ausente, content não-lista, type/text ausentes, error com/sem code).
