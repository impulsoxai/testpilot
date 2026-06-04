---
name: testpilot
description: >
  Universal QA gate for APIs, MCP Servers, and AI agents.
  Runs 13 test phases: unit, integration, security, performance,
  contract, regression, idempotency, cache, rate limiting,
  encoding, recovery, and code quality. Use explicitly with
  /testpilot before deploy or merge, or when a QA gate is
  requested. Works with Python (pytest), Node.js (jest/vitest),
  REST APIs, and MCP Servers. Auto-fixes issues with permission
  and generates a full report. Built by ImpulsoX AI.
version: "1.1.0"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# TestPilot — Universal QA Skill
# Built by ImpulsoX AI — github.com/impulsoxai/testpilot
# MIT License

---

## COMPORTAMENTO DE AUTO-CORRECAO (TODAS AS FASES)

Apos cada fase que encontrar problemas, a skill DEVE seguir este fluxo:

### PASSO 1 — Reportar claramente:

```
⚠️  FASE X — [N] problema(s) encontrado(s):

1. [descricao clara do problema]
   Causa: [por que aconteceu]
   Correcao: [o que vai fazer para resolver]

2. [proximo problema]
   ...
```

### PASSO 2 — Perguntar permissao:

```
Posso corrigir automaticamente? (s/n)
```

### PASSO 3a — Se aprovado (s):

- Aplica a correcao
- Roda o teste de novo para confirmar
- Mostra:

```
✅ Corrigido: [descricao do que foi feito]
Teste re-executado: PASSOU
```

### PASSO 3b — Se negado (n):

- Documenta no relatorio como "⚠️ Manual action needed"
- Mostra instrucao exata:

```
📋 Para corrigir manualmente:
[passo 1]
[passo 2]
```

---

## CORRECOES AUTOMATICAS POR FASE

### Phase 1 — Environment Check
Problemas corrigiveis automaticamente:
- Variavel faltando no .env → adiciona com valor placeholder
- .env.example desatualizado → adiciona variavel nova

NAO corrigir automaticamente:
- JWT_SECRET — deixa para o usuario definir
- Tokens de API reais (Telegram, Sentry)

### Phase 2 — Unit Tests
Problemas corrigiveis:
- Import faltando → adiciona o import correto
- Typo em nome de funcao → corrige
- Assertion com valor hardcoded errado → atualiza

NAO corrigir:
- Logica de negocio incorreta → documenta e para

### Phase 5 — Contract Tests
Problemas corrigiveis:
- Docstring muito curta → expande com mais detalhes
- Descricao em ingles → traduz para portugues
- Schema incompleto → adiciona parametros faltando

### Phase 7 — Cache Tests
Problemas corrigiveis:
- TTL incorreto → ajusta para o valor recomendado
- Cache nao aplicado em ferramenta → adiciona decorator

### Phase 8 — Rate Limiting
Problemas corrigiveis:
- Limite incorreto → corrige no config

### Phase 10 — Security Tests
Problemas corrigiveis:
- Input nao sanitizado → adiciona sanitizacao
- Stack trace exposto → adiciona try/catch adequado
- Erro 500 em input malicioso → adiciona validacao

### Phase 13 — Code Quality
Problemas corrigiveis:
- Funcao sem docstring → gera docstring baseada no codigo
- Import nao utilizado → remove
- Dead code obvio → remove apos confirmar
- Padrao de erro inconsistente (nao comeca com ❌) → corrige

---

## REGRA DE AUTOCORRECAO — MOSTRAR DIFF

ANTES de aplicar qualquer correcao, mostra o diff:

```
Vou alterar src/tools/identidade.py:

linha 45: [antes]
linha 45: [depois]

Confirma? (s/n)
```

---

## REGRAS DE AUTO-CORRECAO

1. SEMPRE pede permissao antes de modificar qualquer arquivo
2. NUNCA modifica testes para fazer passar — corrige o codigo
3. NUNCA commita sem aprovacao explicita
4. NUNCA faz deploy — so prepara para deploy
5. Se uma correcao automatica falhar 2x → move para manual
6. Sempre mostra o diff antes de aplicar correcao

---

## PHASE 0 — PROJECT DISCOVERY

Scan the project before running any tests:

```bash
# Read CLAUDE.md
cat CLAUDE.md 2>/dev/null | head -50

# Detect language
ls pyproject.toml setup.py requirements.txt package.json 2>/dev/null

# Find test files
find . -name "test_*.py" -o -name "*_test.py" \
       -o -name "*.test.js" -o -name "*.spec.js" \
  | grep -v node_modules | grep -v .venv | head -20

# Find production URL
grep -r "railway.app\|\.com\|production\|PROD_URL\|BASE_URL" \
  CLAUDE.md .env.example 2>/dev/null | head -10

# Check environment variables
cat .env.example 2>/dev/null
```

Extract and store:
- PROJECT_NAME from pyproject.toml or package.json
- PROJECT_TYPE (MCP Server / REST API / Agent / Web App)
- TECH_STACK (Python / Node.js)
- TEST_FRAMEWORK (pytest / jest / vitest)
- PRODUCTION_URL (if found)
- REQUIRED_ENV_VARS (from .env.example)

Print discovery summary:
🔍 TestPilot v1.1.0 — Discovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: {name}
Type: {type}
Stack: {stack}
Tests: {N} files found
Production URL: {url or "not configured"}
Starting QA suite...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

## PHASE 1 — ENVIRONMENT CHECK

Before any tests, verify the environment is correct.

```bash
# Check all required env vars from .env.example exist in .env file OR os.environ
python -c "
import os
from pathlib import Path

def parse_env_file(path):
    result = {}
    p = Path(path)
    if not p.exists():
        return result
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            result[key.strip()] = value.strip()
    return result

example = Path('.env.example')
if not example.exists():
    print('⚠️  No .env.example found — skipping env check')
    exit(0)

required = list(parse_env_file(example).keys())
configured = {**parse_env_file('.env'), **os.environ}
missing = [k for k in required if not configured.get(k)]

if missing:
    print(f'❌ Missing env vars: {missing}')
else:
    print(f'✅ All {len(required)} env vars present')
" 2>&1

# Check external API dependencies are reachable
python -c "
import httpx

apis = {
    'BrasilAPI': 'https://brasilapi.com.br/api/cep/v1/01310100',
    'ExchangeRate': 'https://open.er-api.com/v6/latest/BRL',
}

for name, url in apis.items():
    try:
        r = httpx.get(url, timeout=5)
        status = '✅' if r.status_code == 200 else '⚠️'
        print(f'{status} {name}: {r.status_code}')
    except Exception as e:
        print(f'❌ {name}: unreachable ({e})')
" 2>&1
```

### AUTO-CORRECAO — Phase 1

Se encontrar variaveis faltando:

```
⚠️  FASE 1 — [N] variável(is) faltando no .env:

1. VAR_NAME
   Causa: Existe no .env.example mas não no .env
   Correção: Adicionar com valor placeholder

Posso corrigir automaticamente? (s/n)
```

Se aprovado:
- Adiciona variaveis com valores placeholder (NUNCA JWT_SECRET ou tokens reais)
- Mostra o diff do .env
- Re-verifica

---

## PHASE 2 — UNIT TESTS

```bash
# Python
python -m pytest tests/ -v --tb=short \
  --cov=src --cov-report=term-missing 2>&1

# Node.js
npm test -- --coverage 2>&1
```

Auto-fix loop (max 3 attempts):
- Read error carefully
- Fix the CODE (not the test)
- Re-run
- Log if cannot fix

Coverage target: 70%+
If below, identify untested functions and create tests for:
- Happy path
- Invalid input
- Empty/null input
- Boundary values (0, -1, very large numbers)
- Special characters

### AUTO-CORRECAO — Phase 2

Se encontrar falhas:

```
⚠️  FASE 2 — [N] teste(s) falhando:

1. test_nome_funcao
   Causa: [erro especifico]
   Correção: [o que vai alterar no codigo]

Vou alterar src/arquivo.py:

linha X: [antes]
linha X: [depois]

Posso corrigir automaticamente? (s/n)
```

Se aprovado:
- Aplica a correcao no CODIGO (nunca no teste)
- Roda pytest novamente
- Se passar: mostra ✅
- Se falhar de novo: tenta ate 3x, depois move para manual

---

## PHASE 3 — INTEGRATION TESTS

Only if PRODUCTION_URL found. First check health:

```bash
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  {PRODUCTION_URL}/health 2>/dev/null)
echo "Health check: $STATUS"
```

If not 200, skip integration and warn.

### For MCP Servers:
```python
import httpx, json

BASE = "{PRODUCTION_URL}"
HEADERS = {"Content-Type": "application/json"}

def mcp_call(method, params={}):
    r = httpx.post(f"{BASE}/mcp",
        json={"jsonrpc":"2.0","id":1,
              "method":method,"params":params},
        headers=HEADERS, timeout=15)
    return r.json()

# List all tools
result = mcp_call("tools/list")
tools = result["result"]["tools"]
print(f"Found {len(tools)} tools")

# Test each tool with valid input
# Test each tool with invalid input
# Verify all return descriptive errors (not 500)
```

### For REST APIs:
Test each route with valid and invalid inputs.
All invalid inputs must return 400/422, never 500.

---

## PHASE 4 — REGRESSION TESTS

Check that things that worked before still work.

```bash
# Run the full test suite and compare with last run
python -m pytest tests/ -v 2>&1 | tee /tmp/current_run.txt

# Compare with previous run if exists
if [ -f tests/reports/last_run.txt ]; then
    diff tests/reports/last_run.txt /tmp/current_run.txt \
      | grep "^[<>]" | grep -E "PASSED|FAILED" || echo "No regressions"
fi

# Save current run for next comparison
mkdir -p tests/reports
cp /tmp/current_run.txt tests/reports/last_run.txt
```

---

## PHASE 5 — CONTRACT TESTS

Verify the API contract hasn't changed in breaking ways.

```python
# For MCP Servers — verify all tools still exist with same schema
import httpx, json

BASE = "{PRODUCTION_URL}"

def check_contracts():
    r = httpx.post(f"{BASE}/mcp",
        json={"jsonrpc":"2.0","id":1,
              "method":"tools/list","params":{}},
        timeout=10)

    tools = {t["name"]: t for t in r.json()["result"]["tools"]}

    # Each tool must have: name, description, inputSchema
    for name, tool in tools.items():
        assert "description" in tool, f"{name} missing description"
        assert "inputSchema" in tool, f"{name} missing inputSchema"
        assert len(tool["description"]) > 10, \
            f"{name} description too short"

    print(f"✅ {len(tools)} tools have valid contracts")

    # Verify response format consistency
    # All success responses must start with ✅
    # All error responses must start with ❌

check_contracts()
```

### AUTO-CORRECAO — Phase 5

Se encontrar contratos invalidos:

```
⚠️  FASE 5 — [N] contrato(s) inválido(s):

1. ferramenta_nome: descrição muito curta (5 chars)
   Causa: Docstring incompleta
   Correção: Expandir descrição com mais detalhes

Vou alterar src/tools/arquivo.py:

linha X: """Função curta"""
linha X: """
    Função que faz X com Y.
    Retorna Z quando W.
    """

Posso corrigir automaticamente? (s/n)
```

---

## PHASE 6 — IDEMPOTENCY TESTS

Same input must always return same output.

```python
import httpx

def test_idempotency(tool_name, args, n=3):
    results = []
    for i in range(n):
        r = httpx.post(f"{BASE}/mcp",
            json={"jsonrpc":"2.0","id":i,
                  "method":"tools/call",
                  "params":{"name":tool_name,
                           "arguments":args}},
            timeout=15)
        results.append(r.json()["result"]["content"][0]["text"])

    # All results must be identical
    assert len(set(results)) == 1, \
        f"{tool_name} is not idempotent: {set(results)}"
    print(f"✅ {tool_name}: idempotent ({n} calls)")

# Test deterministic tools (validation, formatting)
# Skip non-deterministic (currency rates, real-time data)
```

---

## PHASE 7 — CACHE TESTS

Verify cache is working correctly.

```python
import httpx, time

def test_cache(tool_name, args):
    # First call (cache miss)
    start = time.time()
    r1 = call_tool(tool_name, args)
    time1 = time.time() - start

    # Second call (cache hit — should be faster)
    start = time.time()
    r2 = call_tool(tool_name, args)
    time2 = time.time() - start

    # Results must be same
    assert r1 == r2, f"Cache returned different results"

    # Cache hit should be at least 2x faster
    if time2 < time1 * 0.5:
        print(f"✅ {tool_name}: cache working ({time1*1000:.0f}ms → {time2*1000:.0f}ms)")
    else:
        print(f"⚠️  {tool_name}: cache may not be working ({time1*1000:.0f}ms → {time2*1000:.0f}ms)")
```

### AUTO-CORRECAO — Phase 7

Se cache nao funcionar:

```
⚠️  FASE 7 — Cache não aplicado em ferramenta_nome:

Causa: Decorator @cache ausente ou TTL incorreto
Correção: Adicionar decorator com TTL recomendado

Vou alterar src/tools/arquivo.py:

linha X: async def ferramenta_nome(args):
linha X: @cache(ttl=300)
         async def ferramenta_nome(args):

Posso corrigir automaticamente? (s/n)
```

---

## PHASE 8 — RATE LIMITING TESTS

Verify rate limiting is enforced on the correct endpoint.

```bash
# Run via standalone script — reads RATE_LIMIT_ENDPOINT from environment.
# If the var is not set, falls back to /health and prints AVISO.
python scripts/rate_limit_check.py {PRODUCTION_URL}
```

Or inline:

```python
import httpx, os

RATE_LIMIT_ENDPOINT = os.environ.get("RATE_LIMIT_ENDPOINT", "").strip() or "/health"
_used_fallback = not os.environ.get("RATE_LIMIT_ENDPOINT", "").strip()

if _used_fallback:
    print(
        "AVISO: usando endpoint padrão '/health' — "
        "defina RATE_LIMIT_ENDPOINT para o endpoint real do seu projeto."
    )

url = f"{BASE_URL}{RATE_LIMIT_ENDPOINT}"
responses = []
for i in range(110):
    try:
        r = httpx.get(url, timeout=5)
        responses.append(r.status_code)
    except httpx.ConnectError:
        break

last_10 = responses[-10:] if len(responses) >= 10 else responses
has_429 = 429 in last_10

if has_429:
    print(f"✅ Rate limiting aplicado em {RATE_LIMIT_ENDPOINT} (429 detectado)")
else:
    print(
        f"⚠️  Rate limiting NÃO detectado em {RATE_LIMIT_ENDPOINT} "
        f"(sem 429 após {len(responses)} requests)"
    )
```

### AUTO-CORRECAO — Phase 8

Se rate limiting nao funcionar:

```
⚠️  FASE 8 — Rate limiting não configurado:

Causa: Limite ausente ou muito alto
Correção: Configurar limite no middleware

Posso corrigir automaticamente? (s/n)
```

---

## PHASE 9 — ENCODING TESTS

Verify proper handling of special characters.

```python
ENCODING_TESTS = [
    # Brazilian Portuguese
    "São Paulo", "João", "Ângela", "Açaí",
    # Special chars
    "Rua das Flores, nº 123",
    "R$ 1.234,56",
    # Emojis
    "Olá! 😊", "✅ Aprovado",
    # Mixed
    "ImpulsoX — Agência de IA 🇧🇷",
]

for text in ENCODING_TESTS:
    # Each should not cause encoding errors
    # Response should contain the text or handle gracefully
    pass
```

---

## PHASE 10 — SECURITY TESTS

```python
MALICIOUS_INPUTS = [
    "A" * 10000,                      # Long string
    "A" * 100000,                     # Very long string
    "'; DROP TABLE users; --",         # SQL injection
    "\" OR 1=1 --",                   # SQL injection 2
    "<script>alert('xss')</script>",   # XSS
    "<img src=x onerror=alert(1)>",   # XSS 2
    "../../etc/passwd",                # Path traversal
    "/etc/shadow",                     # Path traversal 2
    "http://localhost:8000/admin",     # SSRF
    "http://169.254.169.254/latest",   # AWS metadata SSRF
    "\x00\x01\x02\x03",              # Null bytes
    "\r\n\r\nHTTP/1.1 200 OK",        # HTTP injection
    "𝕳𝖊𝖑𝖑𝖔",                        # Unicode extreme
    "אבגד",                           # RTL text
    "{\"__proto__\": {\"admin\": true}}", # Prototype pollution
    "$(whoami)",                       # Command injection
    "`whoami`",                        # Command injection 2
    "{{7*7}}",                         # Template injection
    None,                              # Null
    999999999999999999,                # Huge number
    -999999999999999999,               # Huge negative
    0,                                 # Zero
    [],                                # Empty list
    {},                                # Empty dict
]

for payload in MALICIOUS_INPUTS:
    # Server must:
    # 1. Not crash (still respond to /health after)
    # 2. Return 400/422, not 500
    # 3. Not expose stack traces
    # 4. Not execute the payload
```

### AUTO-CORRECAO — Phase 10

Se encontrar vulnerabilidades:

```
⚠️  FASE 10 — [N] vulnerabilidade(s) encontrada(s):

1. ferramenta_nome: retorna 500 com SQL injection
   Causa: Input não sanitizado
   Correção: Adicionar validação com pydantic/regex

Vou alterar src/tools/arquivo.py:

linha X: def ferramenta_nome(input: str):
linha X: def ferramenta_nome(input: str):
             if not re.match(r'^[a-zA-Z0-9]+$', input):
                 return {"error": "Input inválido"}

Posso corrigir automaticamente? (s/n)
```

Se aprovado:
- Aplica sanitizacao
- Roda teste de seguranca novamente
- Mostra resultado

---

## PHASE 11 — PERFORMANCE TESTS

```python
# scripts/load_test.py
import asyncio, httpx, time, statistics

async def run_load_test(base_url: str):
    results = {}

    for n in [10, 50, 100]:
        times = []
        errors = 0

        async with httpx.AsyncClient(timeout=30) as client:
            async def req():
                start = time.time()
                try:
                    r = await client.get(f"{base_url}/health")
                    if r.status_code == 200:
                        return time.time() - start
                except:
                    pass
                return None

            t_start = time.time()
            raw = await asyncio.gather(*[req() for _ in range(n)])
            t_total = time.time() - t_start

        valid = [r for r in raw if r]
        errors = n - len(valid)

        if valid:
            results[n] = {
                "avg": statistics.mean(valid) * 1000,
                "p50": statistics.median(valid) * 1000,
                "p95": sorted(valid)[int(len(valid)*0.95)] * 1000,
                "total": t_total,
                "errors": errors
            }

    return results

# Thresholds:
# 10 concurrent: avg < 1000ms, p95 < 3000ms, errors = 0
# 50 concurrent: avg < 2000ms, p95 < 5000ms, errors < 5%
# 100 concurrent: avg < 3000ms, p95 < 8000ms, errors < 10%
```

---

## PHASE 12 — RECOVERY TESTS

After errors, the server must recover normally.

```python
import httpx

def test_recovery(base_url):
    # 1. Send bad request
    try:
        httpx.post(f"{base_url}/mcp",
            content="INVALID JSON {{{{",
            headers={"Content-Type": "application/json"},
            timeout=5)
    except:
        pass

    # 2. Wait briefly
    import time; time.sleep(1)

    # 3. Server must still respond normally
    r = httpx.get(f"{base_url}/health", timeout=5)
    assert r.status_code == 200, \
        f"Server did not recover: {r.status_code}"

    print("✅ Server recovered after bad request")
```

---

## PHASE 13 — CODE QUALITY

```bash
# Recently changed files
CHANGED=$(git diff --name-only HEAD~1 2>/dev/null \
          || git diff --name-only)
echo "Changed files: $CHANGED"

# Run /simplify on each changed file

# Dead code detection
python -c "
import ast, glob, sys

dead = []
for f in glob.glob('src/**/*.py', recursive=True):
    try:
        tree = ast.parse(open(f).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef,
                                  ast.AsyncFunctionDef)):
                # Check if function is called anywhere
                import subprocess
                result = subprocess.run(
                    ['grep', '-r', node.name, 'src/'],
                    capture_output=True, text=True)
                if result.stdout.count(node.name) < 2:
                    dead.append(f'{f}:{node.name}')
    except:
        pass

if dead:
    print(f'⚠️  Possibly unused functions:')
    for d in dead[:5]:
        print(f'   {d}')
else:
    print('✅ No dead code found')
" 2>&1

# Missing docstrings
python -c "
import ast, glob

missing = []
for f in glob.glob('src/**/*.py', recursive=True):
    try:
        tree = ast.parse(open(f).read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef,
                                  ast.AsyncFunctionDef)):
                if not (node.body and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value,
                                   ast.Constant)):
                    missing.append(f'{f}:{node.name}')
    except:
        pass

if missing:
    print(f'⚠️  Missing docstrings ({len(missing)}):')
    for m in missing[:5]:
        print(f'   {m}')
else:
    print('✅ All functions have docstrings')
" 2>&1
```

### AUTO-CORRECAO — Phase 13

Se encontrar problemas de qualidade:

```
⚠️  FASE 13 — [N] problema(s) de qualidade:

1. Função sem docstring: src/tools/arquivo.py:funcao_nome
   Causa: Docstring não definida
   Correção: Gerar docstring baseada no código

Vou alterar src/tools/arquivo.py:

linha X: def funcao_nome(args):
linha X: def funcao_nome(args):
             """Descrição gerada automaticamente."""

Posso corrigir automaticamente? (s/n)
```

---

## RESUMO DE CORRECOES DISPONIVEIS

Ao final de todas as fases, ANTES do relatorio final:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 RESUMO DE CORREÇÕES DISPONÍVEIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Automáticas (uma de cada vez, com confirmação):
✅ [Phase 1] Adicionar 3 env vars faltando
✅ [Phase 13] Adicionar docstring em função X
✅ [Phase 10] Sanitizar input em ferramenta Y

Manuais (requerem sua decisão):
⚠️  [Phase 2] Lógica incorreta em test_X
⚠️  [Phase 1] JWT_SECRET precisa de valor real
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Para cada correção automática, individualmente e em ordem:

1. Mostra o diff da correção
2. Pergunta: `Posso aplicar esta correção? (s/n)`
3. Se aprovado (s):
   - Aplica a correção
   - Roda novamente só a fase afetada para confirmar
   - Mostra resultado (`✅ Corrigido` ou `⚠️ Falhou — movendo para manual`)
   - Sugere commit para ESTA correção:
     ```
     📋 Para commitar esta correção, rode manualmente:

     git add [arquivo alterado]
     git commit -m "fix: [descrição desta correção]

     TestPilot auto-fix — Phase N"

     # Revise o diff antes de commitar.
     ```
4. Se negado (n): documenta como `⚠️ Manual action needed` e passa para próxima
5. Avança para a próxima correção — nunca em lote

Após processar todas individualmente, mostra o relatório final.

---

## PHASE 14 — FINAL REPORT

Save to tests/reports/testpilot-{timestamp}.md and print:
╔═══════════════════════════════════════════════════╗
║  🚀 TESTPILOT v1.1.0 — COMPLETE QA REPORT        ║
║  {project_name} — {timestamp}                     ║
╠═══════════════════════════════════════════════════╣
║  PHASE 1  Environment Check    ✅/❌              ║
║  PHASE 2  Unit Tests           ✅/❌  X/Y (Z%)   ║
║  PHASE 3  Integration Tests    ✅/❌/⏭️  X/Y     ║
║  PHASE 4  Regression Tests     ✅/❌              ║
║  PHASE 5  Contract Tests       ✅/❌              ║
║  PHASE 6  Idempotency Tests    ✅/❌              ║
║  PHASE 7  Cache Tests          ✅/❌/⏭️          ║
║  PHASE 8  Rate Limiting        ✅/❌/⏭️          ║
║  PHASE 9  Encoding Tests       ✅/❌              ║
║  PHASE 10 Security Tests       ✅/❌              ║
║  PHASE 11 Performance Tests    ✅/❌/⏭️          ║
║  PHASE 12 Recovery Tests       ✅/❌              ║
║  PHASE 13 Code Quality         ✅/⚠️             ║
╠═══════════════════════════════════════════════════╣
║  OVERALL: ✅ READY TO DEPLOY / ❌ NEEDS FIXES    ║
╠═══════════════════════════════════════════════════╣
║  Auto-fixed: N issues                             ║
║  Manual action needed: N issues                   ║
╚═══════════════════════════════════════════════════╝
Performance Summary:
10 concurrent:  avg Xms | p95 Xms | errors: 0
50 concurrent:  avg Xms | p95 Xms | errors: N
100 concurrent: avg Xms | p95 Xms | errors: N
[If READY TO DEPLOY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Suggested commit message:
feat/fix: [describe what changed]
TestPilot QA ✅

Unit: X/Y | Integration: X/Y
Security: clean | P95: Xms
13/13 phases passed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[If NEEDS FIXES]
Priority fixes before deploy:

🔴 CRITICAL: [issue]
🟡 WARNING:  [issue]
🟢 MINOR:    [issue]

Built with TestPilot — github.com/impulsoxai/testpilot

---

## RULES

1. NEVER skip a failing test — fix it
2. NEVER commit automatically — only suggest message
3. NEVER deploy — only validate and report
4. Show real-time progress for each phase
5. If production server down, skip phases 3,4,5,6,7,8,11,12
6. Auto-fix max 3 attempts per issue
7. Save every report to tests/reports/
8. Mark phases as ⏭️ SKIPPED with reason when not applicable
9. ALWAYS ask permission before auto-correcting
10. ALWAYS show diff before applying corrections
11. NEVER modify tests to make them pass — fix the code
