# TestPilot

**Universal QA skill for Claude Code — APIs, MCP Servers, and AI agents**

13 test phases | Auto-fix | Full reports | Zero config

---

## Quick Start

```bash
# 1. Copy to your project
cp -r .claude/skills/testpilot your-project/.claude/skills/

# 2. Install Python dependency
pip install httpx

# 3. Run
/testpilot
```

Claude will scan your project, detect the stack, and run all 13 phases automatically.

## What you'll see

```
🔍 TestPilot v1.2.0 — Discovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: ImpulsoX-CRM
Type: REST API
Stack: Node.js
Tests: 8 files found
Production URL: https://crm.impulsoxai.com.br
Starting QA suite...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Phase 1  — Environment: 5/5 vars present
✅ Phase 2  — Unit Tests: 212/212 passed (coverage: 82%)
✅ Phase 3  — Integration: 14/14 passed
✅ Phase 4  — Regression: No regressions
✅ Phase 5  — Contract: 12/12 tools valid
✅ Phase 6  — Idempotency: 8/8 deterministic
⚠️  Phase 7  — Cache: 2/3 tools cached
✅ Phase 8  — Rate Limiting: Enforced
✅ Phase 9  — Encoding: 11/11 passed
✅ Phase 10 — Security: 10/10 passed
✅ Phase 11 — Performance: avg 45ms, p95 120ms
✅ Phase 12 — Recovery: Server recovered
✅ Phase 13 — Code Quality: No dead code

╔═══════════════════════════════════════════════════╗
║  OVERALL: ✅ READY TO DEPLOY                      ║
║  Auto-fixed: 0 issues                             ║
║  Manual action needed: 0 issues                   ║
╚═══════════════════════════════════════════════════╝

Suggested commit message:
feat: updates to ImpulsoX-CRM
TestPilot QA ✅
Unit: pass | Integration: pass
Security: clean | P95: 120ms
13/13 phases passed
```

## What it tests

| Phase | Type | Description |
|-------|------|-------------|
| 1 | Environment | Env vars + external API availability |
| 2 | Unit | pytest/jest with coverage |
| 3 | Integration | Live API/MCP testing |
| 4 | Regression | Nothing that worked before broke |
| 5 | Contract | API schema hasn't changed |
| 6 | Idempotency | Same input = same output |
| 7 | Cache | Cache is working correctly |
| 8 | Rate limiting | Limits are enforced |
| 9 | Encoding | UTF-8, accents, emojis, RTL |
| 10 | Security | Dependency audit (CVEs) + 20+ malicious input patterns |
| 11 | Performance | 10/50/100 concurrent requests |
| 12 | Recovery | Server recovers after errors |
| 13 | Code Quality | ruff (Python) / eslint (Node) — warning only |

## Complete Invocation Example

When you type `/testpilot`, Claude will:

**Step 1 — Discovery:** Scans your project for language, test framework, and production URL.

**Step 2 — Run phases 1-13:** Each phase runs sequentially. If a phase finds problems, Claude asks permission before auto-correcting:

```
⚠️  FASE 10 — 1 vulnerabilidade(s) encontrada(s):

1. /api/users: retorna 500 com SQL injection
   Causa: Input não sanitizado
   Correção: Adicionar validação com regex

Vou alterar src/routes/users.py:

linha 45: def get_user(id: str):
linha 45: def get_user(id: str):
              if not re.match(r'^[a-zA-Z0-9-]+$', id):
                  return {"error": "ID inválido"}, 400

Posso corrigir automaticamente? (s/n)
```

**Step 3 — Summary:** Shows all fixes applied and a final report saved to `tests/reports/`.

## CLI Scripts

Each script runs standalone. All support `--help` and (where applicable) `--json` for CI/CD.

```bash
# Security — configurable targets, positive injection signals, MCP enum
python scripts/security_test.py https://api.example.com
python scripts/security_test.py https://api.example.com --mcp          # enumerate tools/list

# Contract — schema validation + breaking-change detection
python scripts/contract_test.py https://api.example.com
python scripts/contract_test.py https://api.example.com --compare tests/reports/contract_snapshot.json

# Dependency audit — fails on known CVEs (AUDIT_FAIL_LEVEL=high)
python scripts/dep_audit.py .
AUDIT_IGNORE=GHSA-xxxx python scripts/dep_audit.py .   # accept a known advisory

# Build gate — npm run build or tsc --noEmit before tests
python scripts/build_check.py .

# Regression — PASSED→FAILED detection vs JSON baseline
python scripts/regression_check.py .

# Rate limiting
python scripts/rate_limit_check.py https://api.example.com
RATE_LIMIT_ENDPOINT=/token python scripts/rate_limit_check.py https://api.example.com

# Load testing
python scripts/load_test.py https://api.example.com
python scripts/load_test.py https://api.example.com /api/users --json

# Code quality (lint — warning only, never blocks)
python scripts/lint_check.py .

# Report generation
python scripts/report_generator.py results.json
python scripts/report_generator.py results.json --output report.md
```

## Dependencies

| Package | Required | Purpose |
|---------|----------|---------|
| httpx | Yes | HTTP requests for integration/security/performance tests |
| Python 3.10+ | Yes | Script execution |
| pip-audit | Optional | Dependency vulnerability gate (Phase 10) |
| ruff | Optional | Python linter (Phase 13 — falls back to pyflakes) |
| pyflakes | Optional | Python linter fallback (Phase 13) |
| eslint | Optional | Node/JS linter (Phase 13) |

All other imports use Python standard library.

## Works with

- Python APIs (FastAPI, FastMCP, Flask)
- Node.js APIs (Express, Fastify)
- MCP Servers (any transport)
- AI Agents (OpenClaw, LangChain)

## Troubleshooting

### `ModuleNotFoundError: No module named 'httpx'`
Install the dependency: `pip install httpx`

### `UnicodeEncodeError` on Windows
Fixed in v1.2.0 — `print_banner` now degrades gracefully on cp1252/ASCII consoles
(emoji becomes `?` instead of crashing). If you see this in an older version,
set `$env:PYTHONIOENCODING = "utf-8"` and upgrade to v1.2.0.

### Integration/Performance phases skipped
These phases require a running server. If `PRODUCTION_URL` is not found in CLAUDE.md or .env.example, they are marked `⏭️ SKIPPED`. Add your URL to `.env.example`:
```
BASE_URL=https://your-api.com
```

### `Connection refused` during security tests
The test server must be running locally. Start it before running `/testpilot`:
```bash
# Python
uvicorn src.main:app --port 8000

# Node.js
npm run dev
```

### Auto-correction not working
TestPilot only auto-corrects specific issues (see SKILL.md for the full list). Business logic errors, test failures caused by wrong behavior, and security tokens are never auto-corrected — they are flagged as `⚠️ Manual action needed`.

### JSON output for CI/CD
Use `--json` flag on any script to get machine-readable output:
```bash
python .claude/skills/testpilot/scripts/security_test.py https://api.example.com --json
```

## Project Structure

```
testpilot/
├── SKILL.md                    # Claude instructions (~1000 lines)
├── README.md                   # This file
├── CHANGELOG.md                # Version history
├── lessons.md                  # Bugs found and fixed (L-001 to L-017)
├── references/
│   └── phases.md               # 13 phases documentation
├── expected_outputs/
│   └── report_example.md       # Example report output
└── scripts/
    ├── _shared.py              # Shared utilities (Severity, mcp_call, VERSION)
    ├── security_test.py        # Configurable targets, positive injection signals
    ├── contract_test.py        # MCP schema validation + breaking-change detection
    ├── load_test.py            # Concurrent performance tests (10/50/100)
    ├── report_generator.py     # Formatted QA reports
    ├── env_check.py            # .env file parser (Phase 1)
    ├── rate_limit_check.py     # Rate-limit probe (configurable endpoint)
    ├── dep_audit.py            # Dependency CVE gate — pip-audit + npm audit
    ├── build_check.py          # Build gate — npm run build / tsc --noEmit
    ├── regression_check.py     # Regression gate — PASSED→FAILED vs JSON baseline
    ├── lint_check.py           # ruff / eslint (warning only)
    └── tests/                  # 209 pytest tests covering all scripts
```

## Built by

[ImpulsoX AI](https://impulsoxai.com.br) —
Brazilian AI agents company

---

# TestPilot

**Skill universal de QA para Claude Code**

13 fases de teste | Auto-correcao | Relatorios completos

## Como usar

```bash
# Copia para seu projeto
cp -r .claude/skills/testpilot seu-projeto/.claude/skills/

# Instala dependencia
pip install httpx

# Roda
/testpilot
```

## Construido por

[ImpulsoX AI](https://impulsoxai.com.br)