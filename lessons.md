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

---

## L-011 — security_test.py: rota/shape REST configuráveis via SECURITY_TARGETS (#4b)

**Symptom:** Mesmo com o guard anti-404 (#4a), o modo REST só sabia bater em
`/test` com `{"input": payload}`. API real → 404 → ERRO honesto, mas ainda sem
testar as rotas certas. Faltava o caminho para o operador apontar rota+shape reais.

**Root cause:** Acoplamento rígido de rota e shape no código. Skill é genérica —
não existe rota/body universal.

**Fix (#4b — fatia 2 de 3):** Targets configuráveis.
- `_load_targets(env_value, default_file)`: lê `SECURITY_TARGETS` (caminho de JSON)
  ou `testpilot.targets.json` na raiz; aceita `{"targets":[...]}` ou lista nua;
  retorna None quando vazio/ausente.
- Marcador `PAYLOAD_MARKER = "§PAYLOAD§"` + `_deep_substitute`: injeta o payload em
  qualquer campo do body (recursivo em dict/list) ou na rota. Valor que **é** o
  marcador preserva o tipo cru (None/int/list — para type-confusion); marcador
  embutido em string maior → `str()`.
- `_inject_payload(target, payload) -> (method, path, body)`.
- `_build_requests(...)`: gerador puro de specs `(method, url, body)` — MCP → `/mcp`;
  REST+targets → 1 request por target; REST sem targets → fallback `/test`.
- `test_security` agora itera `_build_requests` e usa `client.request(method, ...)`;
  AVISO explícito quando REST roda sem targets.

**Decisão:** mantida abordagem C (config explícita), NÃO auto-discovery. Funções
puras (`_inject_payload`, `_build_requests`, `_load_targets`) → testáveis sem mock
HTTP. `_send_payload` antigo removido (substituído por `_build_requests` + send inline).

**Trade-off:** REST exige config manual de targets — preço de ser honesto e
genérico. Sem config, o guard #4a garante que o silêncio nunca vira PASS.

**Commit:** `5ad9e6f` — `feat(security): configurable REST targets via SECURITY_TARGETS (#4b)`

**Testes adicionados:** `scripts/tests/test_security_targets.py` — 15 casos:
injeção em campo flat/nested/path, preservação de tipo no valor-marcador,
str() em marcador embutido, default/uppercase de method, `_build_requests`
MCP/targets/fallback, `_load_targets` env/arquivo/lista-nua/None/vazio, constante
do marcador.

---

## L-012 — security_test.py: confirmação por sinal positivo + enum MCP (#4c)

**Symptom:** Fora SQL (já corrigido no #8), as outras categorias só viam 500/stack
trace. XSS, path traversal, SSTI e command injection passavam despercebidos quando
o servidor respondia 200 — mesmo tendo refletido o payload, vazado `/etc/passwd`
ou avaliado um template. Detecção por ausência de erro = cego para injeção real.

**Root cause:** Faltavam detectores específicos. "Não deu 500" não prova que o
input foi tratado — pode ter sido executado com sucesso.

**Fix (#4c — fatia 3 de 3):** Detector puro por categoria, busca evidência de que
o payload AGIU:
- `_check_xss_reflection`: payload com `<`/`javascript:` refletido literal (não
  escapado) no body → WARNING. Reflexão escapada (`&lt;`) não dispara.
- `_check_path_traversal`: conteúdo de arquivo de sistema (`TRAVERSAL_MARKERS`:
  `root:x:0:0`, `[boot loader]`...) → CRITICAL.
- `_check_ssti`: payload com `7*7` que vira `49` no body E o literal `7*7` some →
  template avaliado → CRITICAL. Reflexão literal não dispara; `{{config}}` ignorado
  pela heurística aritmética.
- `_check_command_injection`: saída de comando no body (`CMDI_MARKERS`: `uid=`,
  `gid=`, `root:x:0:0`, dir do Windows) → CRITICAL.

**MCP enum:** `_parse_tool_names(data)` (puro) + `_discover_mcp_tools(client, url)`
(HTTP). Em `--mcp` sem tool_name, descobre via `tools/list` e testa CADA tool.
Sem tools → AVISO, não PASS. Loop de `tool_names` envolve `_build_requests`.

**Decisão:** funções puras → testáveis sem mock HTTP (só `_discover_mcp_tools` toca
rede, e a parte de parsing foi extraída pra `_parse_tool_names`). Sinais positivos
têm seus próprios falsos positivos (app que ecoa `{{7*7}}` como texto, ou
legitimamente retorna `49`) — mitigado: SSTI exige que o literal suma; payload+
contexto sempre no report pro humano julgar.

**Commit:** `9dee69c` — `feat(security): positive injection signals per category + MCP tool enumeration (#4c)`

**Testes adicionados:** `scripts/tests/test_security_signals.py` — 16 casos:
XSS refletido/escapado/ausente, traversal passwd/win.ini/limpo, SSTI avaliado/
refletido-literal/variante-${}/não-aritmético, cmdi id/passwd/limpo, `_parse_tool_names`
extrai/pula-sem-nome/vazio-em-erro.

**Fecha #4** (3 fatias: #4a guard, #4b targets, #4c sinais). Gate de segurança
agora: bate na rota certa (config), confirma injeção por evidência, e nunca
reporta PASS no vazio.

---

## L-013 — Phase 13: linter caseiro (grep+ast) → ruff + eslint (#9)

**Symptom:** Phase 13 reimplementava linter à mão em dois `python -c` no markdown:
(1) "dead code" via `subprocess.run(['grep','-r',node.name,'src/'])` + heurística
"nome aparece <2x → morto"; (2) docstring obrigatória em toda função via AST.

**Root cause:** `grep` é POSIX-only → quebra no dev Windows. A heurística de dead
code é O(funções×arquivos) e falso-positiva em massa (API pública, métodos,
chamadas dinâmicas, nomes curtos). Reinventava — mal — o que ruff/eslint fazem
certo. Docstring obrigatória é estilo, ruidoso para um gate.

**Fix (#9):** Novo script `scripts/lint_check.py`.
- Detecção: Python → `ruff` (via `importlib.util.find_spec`) → fallback `pyflakes`;
  Node → eslint local (`node_modules/.bin`) → global → `npx --no-install eslint`.
- Comando cross-platform: `python -m ruff check` / `python -m pyflakes` (sem
  dependência de PATH no Windows).
- Parsers puros: `_parse_ruff_output` ("Found N error" → int), `_parse_eslint_output`
  ("(E errors, W warnings)" → tupla).
- Veredito **WARN-only**: `_lint_verdict` retorna SKIP/PASS/⚠️, **nunca `❌`**;
  `main` faz `sys.exit(0)` sempre. Lint não bloqueia o gate.
- Removidos: heurística dead-code por grep e exigência de docstring. Dead-code real
  exige call-graph (`vulture`) — deixado como nota de futuro, não reintroduzir
  heurística ruim. Decisões 1/2/3 confirmadas pelo usuário (WARN, remover docstring,
  script).

**Regra #16:** 2 linters reais = abstração mínima justificada, não plugin-system
especulativo.

**Dogfood:** rodando contra `scripts/`, ruff ausente → fallback pyflakes → achou 6
imports/f-strings mortos pré-existentes em OUTROS arquivos (rate_limit_check.py,
test_cleanup.py, test_env_check.py, test_rate_limit_check.py). Fora do escopo #9 —
anotado para aprovação futura. lint_check.py e seus testes: pyflakes limpo.

**Nota de ambiente:** `print_banner` usa emoji 🔍 → crash `UnicodeEncodeError`
(cp1252) no console PowerShell do Windows. Pré-existente, afeta todos os scripts;
contornado com `PYTHONIOENCODING=utf-8`. Não é do #9; candidato a fix próprio.

**Sobreposição com #13:** este script já é uma das "fases que viram script" que o
#13 vai consolidar. Quando #13 for feito, Phase 13 já estará no formato-alvo.

**Commit:** `3bf0dd8` — `feat(lint): replace homegrown grep+ast linter with ruff/eslint (#9)`

**Testes adicionados:** `scripts/tests/test_lint_check.py` — 21 casos:
detecção Python (ruff/pyflakes/path/none) e Node (local/global/npx/none),
construção de comando (ruff/pyflakes/npx/path-direto), parse ruff (summary/clean/
sem-summary) e eslint (summary/vazio), veredito (skip/pass/warn) + guard
`never_returns_fail_marker` (nunca `❌` em nenhuma combinação).

---

## L-014 — Lacuna: sem gate de dependências → vuln conhecida passava (#10a)

**Symptom:** As 13 fases não auditavam dependências. CVE conhecida em
`requirements.txt`/`package.json` passava sem reprovar nada.

**Root cause:** Faltava a fase. Supply-chain não estava no escopo original.

**Fix (#10a — fatia 1 de 2):** `scripts/dep_audit.py`, chamado no início da
Phase 10 (Security — vuln de dep É segurança). **Reprova** a fase (`sys.exit(1)`).
- Node: `npm audit --json --audit-level=<LEVEL>`; `_npm_exceeds(counts, level)`
  reprova se houver vuln no nível-ou-acima. `AUDIT_FAIL_LEVEL` padrão `high`.
- Python: `python -m pip_audit --format json`. pip-audit **não tem threshold de
  severidade nativo confiável** → reprova em QUALQUER vuln. `AUDIT_IGNORE`
  (IDs separados por vírgula) aceita advisories conhecidos/sem fix.
- Tool ausente → SKIP + AVISO (não reprova por falta de ferramenta).
- Funções puras: `_get_fail_level`, `_parse_ignore`, `_build_npm_audit_command`,
  `_build_pip_audit_command` (`python -m pip_audit`, cross-platform),
  `_parse_npm_audit`, `_npm_exceeds`, `_parse_pip_audit` (formatos
  `{"dependencies":[...]}` e lista nua + filtro ignore), `_audit_verdict`.

**Decisão (confirmada pelo usuário):** encaixe em fase existente (sem renumerar);
npm threshold `high`; pip-audit reprova em qualquer vuln (assimetria documentada,
não parsear CVSS à mão — frágil).

**Regra #16:** 2 ecossistemas reais, funções puras, sem abstração especulativa.

**Commit:** `65b0bee` — `feat(deps): dependency-vulnerability gate via pip-audit/npm audit (#10a)`

**Testes adicionados:** `scripts/tests/test_dep_audit.py` — 21 casos:
fail-level default/override/inválido, parse ignore, build commands, parse npm
(counts/vazio), `_npm_exceeds` (high/critical/só-moderate/limpo/moderate),
parse pip (dependencies/lista-nua/ignore/sem-vuln), veredito skip/pass/fail.

---

## L-015 — Lacuna: sem gate de build → fases rodavam sobre build morto (#10b)

**Symptom:** `tsc`/`npm run build` quebrado não reprovava nada. Integração, perf e
recovery rodavam sobre um build que nem compila — resultado sem sentido.

**Root cause:** Faltava a verificação. Nenhuma fase checava "isto compila?".

**Fix (#10b — fatia 2 de 2):** `scripts/build_check.py`, chamado no **início da
Phase 2** (antes dos unit tests — compila primeiro, testa depois). **Reprova** a
fase (`sys.exit(1)`) em build não-zero.
- Node: `npm run build` se `package.json` tem script `build`; senão `npx
  --no-install tsc --noEmit` se existir `tsconfig.json`.
- Python puro: SKIP (sem build universal; unit tests pegam import/sintaxe).
- `npm`/`npx` ausente → SKIP + AVISO.
- Funções puras: `_load_package_json` (None se ausente/inválido), `_has_build_script`,
  `_detect_build_command` (build script tem prioridade sobre tsconfig; None = skip),
  `_build_verdict` (skip/pass/`❌` fail).

**Decisão (confirmada pelo usuário):** Python puro = SKIP (não forçar passo vazio);
build gate é Node/TS-focused.

**Regra #16:** detecção simples por intenção, sem abstrair para "build systems"
genéricos.

**Fecha #10** (2 fatias: #10a dep audit, #10b build gate). Supply chain e build
agora travam o gate de verdade.

**Commit:** `f446ca1` — `feat(build): build gate before unit tests (#10b)`

**Testes adicionados:** `scripts/tests/test_build_check.py` — 16 casos:
load package.json (valid/missing/inválido), `_has_build_script` (true/sem-build/
sem-scripts/None), `_detect_build_command` (npm/tsc/prioridade/None×2), veredito
skip/pass/fail + guard fail em qualquer exit não-zero.
