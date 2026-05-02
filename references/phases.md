# TestPilot — 13 Test Phases Reference

## Phase 1 — Environment Check
**What:** Validates required env vars and external API reachability
**When:** Before any tests run
**Auto-fix:** Adds missing env vars with placeholder values (never secrets)

## Phase 2 — Unit Tests
**What:** Runs pytest/jest with coverage report
**When:** Always
**Auto-fix:** Fixes import errors, typos, wrong assertions in CODE (never in tests)
**Target:** 70%+ coverage

## Phase 3 — Integration Tests
**What:** Tests live API/MCP endpoints with real requests
**When:** Only if PRODUCTION_URL found
**Auto-fix:** None (reports only)

## Phase 4 — Regression Tests
**What:** Compares current test run with previous run
**When:** Always
**Auto-fix:** None (reports differences)

## Phase 5 — Contract Tests
**What:** Verifies API schema hasn't changed (tools, endpoints, parameters)
**When:** Always (MCP servers and REST APIs)
**Auto-fix:** Fixes docstrings, descriptions, incomplete schemas

## Phase 6 — Idempotency Tests
**What:** Same input must return same output (3 consecutive calls)
**When:** Always
**Auto-fix:** None (reports non-deterministic tools)

## Phase 7 — Cache Tests
**What:** Verifies cache hits are faster than cache misses
**When:** If caching is implemented
**Auto-fix:** Adds @cache decorator with recommended TTL

## Phase 8 — Rate Limiting Tests
**What:** Verifies rate limits are enforced (expects 429 after limit)
**When:** Always
**Auto-fix:** Adjusts rate limit config

## Phase 9 — Encoding Tests
**What:** Tests UTF-8, accents, emojis, RTL, special characters
**When:** Always
**Auto-fix:** None (reports encoding failures)

## Phase 10 — Security Tests
**What:** Tests 20+ malicious inputs (SQL injection, XSS, path traversal, SSRF)
**When:** Always
**Auto-fix:** Adds input sanitization, fixes stack trace exposure

## Phase 11 — Performance Tests
**What:** Load tests with 10/50/100 concurrent requests
**When:** If PRODUCTION_URL found
**Auto-fix:** None (reports metrics)

## Phase 12 — Recovery Tests
**What:** Server must recover after receiving bad input
**When:** Always
**Auto-fix:** None (reports recovery failures)

## Phase 13 — Code Quality
**What:** Dead code detection, missing docstrings, /simplify
**When:** Always
**Auto-fix:** Adds docstrings, removes unused imports/dead code