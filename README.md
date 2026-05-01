# TestPilot 🚀

**Universal QA skill for Claude Code**
APIs · MCP Servers · AI Agents · Node.js · Python

> Found and fixed critical production bugs in 2 projects
> before a single user was affected.

---

## What is TestPilot?

TestPilot is a Claude Code skill that runs a complete QA
suite on your project automatically — 13 test phases,
auto-fix with your approval, and a full report in minutes.

It works alongside Claude Code's built-in `/simplify` skill:
- `/testpilot` — validates that your code **works correctly**
- `/simplify` — validates that your code **is well written**

**Run both. Ship with confidence.**

---

## The recommended workflow

```
Build or modify your code
        ↓
    /testpilot          ← finds bugs, security issues, crashes
        ↓
  "Auto-fix? (s/n)"    ← approve fixes with one keystroke
        ↓
    /simplify           ← cleans dead code, redundancies
        ↓
    /testpilot          ← confirms everything still works
        ↓
  commit + deploy       ← suggested message included
```

No manual testing. No configuration. One command.

---

## Install

```bash
# Copy to your project
cp -r testpilot your-project/.claude/skills/

# Run
/testpilot
```

That's it. TestPilot auto-detects your stack.

---

## 13 Test Phases

| # | Phase | What it checks |
|---|-------|----------------|
| 1 | Environment | All env vars present, external APIs reachable |
| 2 | Unit Tests | pytest / jest with coverage report |
| 3 | Integration | Live endpoints — valid and invalid inputs |
| 4 | Regression | Nothing that worked before is now broken |
| 5 | Contract | API schema hasn't changed in breaking ways |
| 6 | Idempotency | Same input always returns same output |
| 7 | Cache | Cache hit/miss working correctly |
| 8 | Rate Limiting | Limits enforced after threshold |
| 9 | Encoding | UTF-8, accents, emojis, RTL text |
| 10 | Security | 20+ malicious input patterns (SQLi, XSS, SSRF...) |
| 11 | Performance | P50/P95/P99 under 10/50/100 concurrent requests |
| 12 | Recovery | Server survives bad requests and keeps responding |
| 13 | Code Quality | Dead code, missing docstrings, pattern consistency |

---

## Auto-fix

When TestPilot finds a problem, it asks before changing anything:

```
⚠️  PHASE 12 — 1 issue found:
Server crashes on malformed JSON
Fix: add global Express error handler
Auto-fix? (s/n)
```

Say **s** and TestPilot fixes, re-tests, and confirms.
Say **n** and it documents what needs manual attention.

---

## Real bugs found

TestPilot found these critical bugs before production:

| Project | Bug | Phase |
|---------|-----|-------|
| ImpulsoX CRM | Server crash on malformed JSON | Phase 12 |
| ImpulsoX CRM | SQLite transactions without ROLLBACK | Phase 13 |
| Brazil MCP Server | Missing docstrings on MCP tools | Phase 13 |

---

## Works with

| Stack | Supported |
|-------|-----------|
| Python + FastAPI | ✅ |
| Python + FastMCP (MCP Server) | ✅ |
| Node.js + Express | ✅ |
| Any HTTP REST API | ✅ |
| Any MCP Server | ✅ |

---

## Built by

**[ImpulsoX AI](https://impulsoxai.com.br)**
Brazilian AI agents company.
Also check out our [Brazil MCP Server](https://github.com/impulsoxai/brazil-mcp-server) —
the first MCP Server with native Brazilian APIs (CNPJ, CPF, CEP, PIX).

MIT License · Made in Brazil 🇧🇷

---
---

# TestPilot 🚀

**Skill universal de QA para Claude Code**
APIs · MCP Servers · Agentes de IA · Node.js · Python

> Encontrou e corrigiu bugs críticos em 2 projetos
> antes de qualquer usuário ser afetado.

---

## O que é o TestPilot?

TestPilot é uma skill do Claude Code que roda uma suite
completa de QA no seu projeto automaticamente — 13 fases
de teste, auto-correção com sua aprovação, e relatório
completo em minutos.

Funciona junto com a skill `/simplify` nativa do Claude Code:
- `/testpilot` — valida que seu código **funciona corretamente**
- `/simplify` — valida que seu código **está bem escrito**

**Rode os dois. Faça deploy com confiança.**

---

## O fluxo recomendado

```
Constrói ou modifica o código
        ↓
    /testpilot          ← encontra bugs, problemas de segurança, crashes
        ↓
  "Auto-corrigir? (s/n)" ← aprova correções com uma tecla
        ↓
    /simplify           ← limpa código morto e redundâncias
        ↓
    /testpilot          ← confirma que tudo ainda funciona
        ↓
  commit + deploy       ← mensagem de commit sugerida
```

Sem testes manuais. Sem configuração. Um comando.

---

## Instalar

```bash
# Copia para o seu projeto
cp -r testpilot seu-projeto/.claude/skills/

# Roda
/testpilot
```

Pronto. O TestPilot detecta automaticamente o seu stack.

---

## 13 Fases de Teste

| # | Fase | O que verifica |
|---|------|----------------|
| 1 | Ambiente | Variáveis de ambiente, APIs externas acessíveis |
| 2 | Unitários | pytest / jest com relatório de cobertura |
| 3 | Integração | Endpoints reais — inputs válidos e inválidos |
| 4 | Regressão | Nada que funcionava antes está quebrado |
| 5 | Contrato | Schema da API não mudou de forma incompatível |
| 6 | Idempotência | Mesmo input sempre retorna mesmo output |
| 7 | Cache | Cache hit/miss funcionando corretamente |
| 8 | Rate Limiting | Limites respeitados após threshold |
| 9 | Encoding | UTF-8, acentos, emojis, texto RTL |
| 10 | Segurança | 20+ padrões maliciosos (SQLi, XSS, SSRF...) |
| 11 | Performance | P50/P95/P99 com 10/50/100 requests simultâneos |
| 12 | Recovery | Servidor sobrevive a requisições ruins |
| 13 | Qualidade | Código morto, docstrings, consistência de padrões |

---

## Auto-correção

Quando o TestPilot encontra um problema, pergunta antes de mudar:

```
⚠️  FASE 12 — 1 problema encontrado:
Servidor crasha com JSON malformado
Correção: adicionar error handler global no Express
Auto-corrigir? (s/n)
```

Diga **s** e o TestPilot corrige, testa de novo e confirma.
Diga **n** e ele documenta o que precisa de atenção manual.

---

## Bugs reais encontrados

O TestPilot encontrou estes bugs críticos antes da produção:

| Projeto | Bug | Fase |
|---------|-----|------|
| ImpulsoX CRM | Servidor crashava com JSON malformado | Fase 12 |
| ImpulsoX CRM | Transações SQLite sem ROLLBACK | Fase 13 |
| Brazil MCP Server | Docstrings faltando nas tools MCP | Fase 13 |

---

## Compatível com

| Stack | Suporte |
|-------|---------|
| Python + FastAPI | ✅ |
| Python + FastMCP (MCP Server) | ✅ |
| Node.js + Express | ✅ |
| Qualquer API HTTP REST | ✅ |
| Qualquer MCP Server | ✅ |

---

## Construído por

**[ImpulsoX AI](https://impulsoxai.com.br)**
Agência brasileira de agentes de IA.
Confira também nosso [Brazil MCP Server](https://github.com/impulsoxai/brazil-mcp-server) —
o primeiro MCP Server com APIs brasileiras nativas (CNPJ, CPF, CEP, PIX).

Licença MIT · Feito no Brasil 🇧🇷