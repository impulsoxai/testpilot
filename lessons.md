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

---

## L-005 — _shared.py: dict chamado como função em format_severity

**Symptom:** `format_severity("critical")` lançava `TypeError: 'dict' object is
not callable`. Função inútil para todas as entradas válidas.

**Root cause:** `SEVERITY_ICONS(Severity(severity))` — parênteses em cima de um
dict (não colchetes). O `except (ValueError, KeyError)` não pega `TypeError`, então
a exceção escapava para o chamador.

**Fix:** Trocar `SEVERITY_ICONS(key)` por `SEVERITY_ICONS.get(key, "⚪")`. Dict
`.get()` lida com chaves ausentes nativamente; `except` reduzido para só `ValueError`
(levantado por `Severity(invalid_string)`).

**Commit:** `9091e0a` — `fix(_shared): format_severity uses .get() instead of calling dict as function`

**Testes adicionados:** `scripts/tests/test_format_severity.py` — 7 casos:
ícone correto por severidade, default para string inválida/vazia/uppercase,
guard `test_never_raises` verifica que nenhuma entrada propaga exceção.

---

## L-006 — Limpeza: imports mortos causam ruído e risco de NameError

**Symptom:** pyflakes reportava 10 warnings de imports não usados em 4 scripts.
`require_args` importado em 3 scripts sem nenhum uso após migração para argparse.
`sys` importado mas nunca chamado em 4 scripts.

**Root cause:** Migração de `sys.argv` manual para `argparse` (v1.0.0) não removeu
os imports antigos. `require_args` ficou como dead code em `_shared.py` com
referência a `sys` que foi removido — criaria `NameError` em runtime se chamada.

**Fix:** Remover todos imports mortos; apagar `require_args` de `_shared.py`;
centralizar versão com `VERSION = "1.1.0"` em `_shared.py`; `report_generator.py`
importa e usa em vez de literal hardcoded. SKILL.md description removeu "after any
code change" + `disable-model-invocation: true`.

**Commit:** `06329b3` — `chore(cleanup): dead imports, VERSION constant, skill description`

**Testes adicionados:** `scripts/tests/test_cleanup.py` — 5 casos de compliance:
pyflakes limpo, VERSION presente e usado no banner, description e
disable-model-invocation corretos.

---

## L-007 — RESUMO: lote de correções contradiz "uma correção por vez"

**Symptom:** "Aplicar todas as correções automáticas? (s/n)" aplicava tudo em
sequência com um único commit sugerido — violava Golden Rule #4 e CLAUDE.md.

**Root cause:** Design original priorizava conveniência (uma aprovação para tudo)
em vez de segurança/rastreabilidade. Cada fix em lote não tem fase de re-verificação
própria nem commit atômico. Bug + acoplamento invisível.

**Fix:** Loop individual por correção: diff → permissão → aplica → re-verifica fase
afetada → sugere commit específico → próxima. Nunca em lote.

**Commit:** `b89da64` — `fix(resumo): one-fix-at-a-time loop replaces batch apply`

**Testes adicionados:** `scripts/tests/test_one_fix_at_a_time.py` — 5 casos:
ausência de linguagem de lote, presença de "uma de cada vez",
re-verificação por fase, commit-por-fix.

---

## L-008 — Phase 8: endpoint /health hardcoded → falso NEGATIVO silencioso

**Symptom:** Phase 8 disparava 110 requests em `/health`. Projetos com rate-limit
em `/token`, `/api` ou `/login` recebiam "⚠️ Rate limiting not enforced" mesmo
com rate-limit corretamente configurado.

**Root cause:** `f"{url}/health"` hardcoded no pseudocódigo da fase. Nenhum
mecanismo para o operador indicar o endpoint real. Falso NEGATIVO silencioso —
não havia nenhum aviso de que o endpoint testado pode não ser o correto.

**Fix:** Ler `RATE_LIMIT_ENDPOINT` de `os.environ`; fallback para `/health` só
quando ausente/vazio; imprimir `AVISO` explícito no fallback com nome da var
e instrução de como configurar.

**Commit:** `5aa6413` — `fix(phase-8): rate-limit endpoint configurable via RATE_LIMIT_ENDPOINT`

**Testes adicionados:** `scripts/tests/test_rate_limit_check.py` — 9 casos:
env var usada quando presente, fallback quando ausente/vazio, strip de whitespace,
AVISO com nome da var, sem warning quando explicitamente configurado.

---

## L-009 — security_test.py: status 200 = falso positivo em massa

**Symptom:** Todo input SQL que retornava 200 era flagado como "Possible SQL
injection". Servidor que sanitizou corretamente o input → 200 → acusado.

**Root cause:** `if category == "sql_injection" and r.status_code == 200:` —
heurística incorreta. Status 200 é o comportamento CORRETO quando o input é
sanitizado; não é sinal de injeção.

**Fix:** Remover verificação de status 200. Substituir por sinais reais:
- Erros de banco no body (MySQL, PG, SQLite, Oracle, MSSQL) → WARNING
- Tempo de resposta > 3.0s (injeção baseada em tempo) → WARNING

Extraído em `_check_sql_injection_signals(response_text, elapsed_s, payload_repr)`
— função pura, sem necessidade de mock HTTP nos testes.

**Commit:** `5b08aa6` — `fix(security): replace status-200 SQL heuristic with real injection signals`

**Testes adicionados:** `scripts/tests/test_sql_injection_signals.py` — 13 casos:
200 limpo (sem issue), 200 com erro de banco (issue), resposta lenta (issue),
exatamente no limiar (sem issue), ambos sinais (2 issues), case-insensitive,
marcadores MySQL/PG/SQLite/Oracle/MSSQL, constante SLOW_REQUEST_THRESHOLD_S.

---

## L-010 — security_test.py: rota /test hardcoded → falso VERDE no gate (#4a)

**Symptom:** Modo REST batia em `/test` hardcoded com `{"input": payload}`. API
real responde 404 em todos os payloads → loop não acha 500 nem stack trace →
`issues={}` → `get_security_verdict()` retorna `✅ PASS`. Gate de segurança
aprovava sem ter testado nada — pior que falso negativo: o report afirmava
"no vulnerabilities found" quando nenhum payload chegou na lógica real.

**Root cause:** Acoplamento rígido de rota (`/test`) + shape (`{"input": ...}`).
Sem rota válida, a ausência de erro vira "aprovado" em vez de "não testável".

**Fix (#4a — fatia 1 de 3):** Guard anti-404. Coletar `status_code` de cada
probe; se `_is_unreachable(all_statuses)` (todos 404/405) → registrar issue na
categoria reservada `CONFIG_ERROR_CATEGORY = "_config"` com CRITICAL, e
`get_security_verdict` retorna `🚫 ERRO — alvo não testável` ANTES de checar PASS.
Sem rota válida → nunca PASS. `_is_unreachable([])` é False (sem resposta =
problema de conexão, tratado em outro ramo). Um único status ≠ 404/405 (ex: 500,
200) significa que a rota existe → resultado real, não config error.

**Trade-off:** REST ainda exige config de rota/shape reais (vem em #4b via
`SECURITY_TARGETS`). #4a sozinho não testa as rotas certas — mas para de MENTIR:
gate falha honestamente em vez de aprovar no vazio. Abordagem escolhida: config
explícita + guard, NÃO auto-discovery (crawler OpenAPI = over-engineering, frágil,
Regra #16).

**Commit:** `c827af0` — `fix(security): guard against false-GREEN when target route returns 404 (#4a)`

**Testes adicionados:** `scripts/tests/test_security_guard.py` — 11 casos:
all-404/all-405/misto unreachable, algum 200 / 500 / lista vazia não-unreachable,
constante `UNREACHABLE_STATUSES`, veredito não-PASS com config error, PASS genuíno
em issues vazio, config error tem prioridade sobre outras findings.

**Nota:** `lessons.md` tinha L-005 duplicado no fim (resíduo de append anterior) —
removido nesta edição.
