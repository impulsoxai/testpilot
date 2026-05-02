# TestPilot — Example Report Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 TestPilot v1.1.0 — QA Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Phase 1  — Environment: 5/5 vars present
✅ Phase 2  — Unit Tests: 212/212 passed (coverage: 82%)
✅ Phase 3  — Integration: 14/14 passed
✅ Phase 4  — Regression: No regressions
✅ Phase 5  — Contract: 12/12 tools valid
✅ Phase 6  — Idempotency: 8/8 deterministic
⚠️  Phase 7  — Cache: 2/3 tools cached (missing on /api/metrics)
✅ Phase 8  — Rate Limiting: Enforced (429 after 200 req)
✅ Phase 9  — Encoding: 11/11 passed
✅ Phase 10 — Security: 10/10 passed
✅ Phase 11 — Performance: avg 45ms, p95 120ms
✅ Phase 12 — Recovery: Server recovered after bad input
✅ Phase 13 — Code Quality: No dead code, all functions documented

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESUMO: 212 testes | 0 falhas | 1 warning
STATUS: ✅ PRONTO PARA DEPLOY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## JSON Output Example

```json
{
  "version": "1.1.0",
  "timestamp": "2026-05-01T14:30:00Z",
  "project": "ImpulsoX-CRM",
  "total_tests": 212,
  "passed": 212,
  "failed": 0,
  "warnings": 1,
  "phases": {
    "environment": {"status": "pass", "details": "5/5 vars"},
    "unit": {"status": "pass", "details": "212/212", "coverage": 82},
    "integration": {"status": "pass", "details": "14/14"},
    "security": {"status": "pass", "details": "10/10"},
    "performance": {"status": "pass", "avg_ms": 45, "p95_ms": 120}
  },
  "deploy_ready": true
}
```