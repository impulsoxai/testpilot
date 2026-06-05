# Changelog

All notable changes to TestPilot are documented here.

## [1.2.0] — 2026-06-05

### Fixed (critical bugs — gate was lying)

- **parse_test_output AND condition** (L-001): all-green pytest output reported as
  `{total:0, passed:0, failed:0}` — the Phase 9 gate declared PASS even when tests
  failed, and PASS even when there were zero tests. Fixed with independent regex
  searches per metric.
- **Phase 1 os.getenv vs .env file** (L-002): `os.getenv` reads the process
  environment, not the `.env` file. Claude Code does not export `.env` before
  running Python. Phase 1 reported every var as missing even with a complete `.env`.
  Fixed by parsing `.env` directly.
- **RESUMO auto git push** (L-003): SKILL.md RESUMO ran `git add .` + `git commit`
  + `git push` automatically, ending with "Deploy pronto! Aguardando Railway..." —
  contradicting its own RULES #2 and #3 ("NEVER commit automatically", "NEVER
  deploy"). Replaced with manual-command block.
- **contract_test NameError** (L-004): `mcp_call_tool` called on line 78 but never
  imported — Phase 5 silently raised `NameError` on every run.
- **format_severity TypeError** (L-005): `SEVERITY_ICONS(key)` called a dict as a
  function — `TypeError` not caught by `except (ValueError, KeyError)`. Every
  severity label displayed as nothing.
- **security_test false-GREEN via /test** (L-010 to L-012): REST mode hit the
  hardcoded route `/test` with `{"input": payload}`. Any real API returns 404 →
  no 500, no stack trace → `issues={}` → verdict PASS. The gate approved without
  testing anything. Fixed in three slices: 404-guard (never PASS on all-404),
  configurable targets via `SECURITY_TARGETS` + `§PAYLOAD§` marker, and positive
  injection signals (XSS reflection, path traversal content, SSTI eval, command
  output).
- **SQL injection false positives** (L-009): `status_code == 200` flagged as
  injection — 200 is the correct response when input is sanitised. Replaced with
  real signals: DB error strings in body + response time > 3s (time-based).
- **print_banner UnicodeEncodeError** (L-013-b): emoji in `print_banner` crashed
  on Windows cp1252/ASCII consoles. Fixed with `errors="replace"` encoding. Note:
  v1.1.0 CHANGELOG claimed this was fixed — it was not.

### Added (new gates that actually fail the phase)

- **`dep_audit.py`** (Phase 10): dependency vulnerability gate. npm audit
  (threshold `AUDIT_FAIL_LEVEL`, default `high`) + pip-audit (any CVE fails;
  `AUDIT_IGNORE` accepts specific advisory IDs). Tool missing → SKIP, not FAIL.
- **`build_check.py`** (Phase 2, runs before unit tests): build gate. `npm run
  build` if a build script exists, else `tsc --noEmit` if tsconfig.json present.
  Pure Python → SKIP. Non-zero exit → phase FAIL.
- **`regression_check.py`** (Phase 4): cross-platform replacement for the POSIX-
  only bash (`/tmp`, `[ -f ]`, `diff | grep`). Stores a JSON baseline; a
  regression is PASSED→FAILED/ERROR only (new failures and renamed tests are not
  flagged). Baseline missing → save and skip comparison.

### Added (new scripts — all testable standalone)

- **`env_check.py`** — `.env` parser with `check_env_vars()` pure function.
- **`rate_limit_check.py`** — rate-limit probe; endpoint configurable via
  `RATE_LIMIT_ENDPOINT` (explicit AVISO on fallback to `/health`).
- **`lint_check.py`** — ruff → pyflakes (Python) + eslint (Node); warning only,
  never blocks the gate; cross-platform via `python -m ruff`.

### Changed

- Phase 13 (Code Quality): removed POSIX-only dead-code heuristic (`grep`, O(n²),
  mass false positives) and mandatory-docstring check. Now calls `lint_check.py`.
- Phases 5/8/11: removed stale inline code duplicates that shadowed the standalone
  scripts. SKILL.md now calls `contract_test.py`, `rate_limit_check.py`,
  `load_test.py` directly.
- Phase 8 rate-limit endpoint: no longer hardcoded to `/health`; configurable via
  `RATE_LIMIT_ENDPOINT` with explicit AVISO when using the fallback.
- RESUMO rewritten to one-fix-at-a-time loop (was batch-apply).
- SKILL.md `disable-model-invocation: true` (was `false`); description no longer
  says "after any code change" (caused over-triggering).

### Fixed (cleanup)

- Dead imports removed from 5 files (L-013-a): `rate_limit_check.py`, and test
  files `test_cleanup.py`, `test_env_check.py`, `test_rate_limit_check.py`,
  `test_regression_check.py`. Guard test added: `test_no_unused_imports_full_repo`
  runs pyflakes over the entire `scripts/` tree.
- `VERSION` constant centralised in `_shared.py` (was hardcoded in
  `report_generator.py`).
- `require_args` removed (dead code after argparse migration).

### Tests

- 76 → 209 pytest tests (L-001 through L-017 + lateral fixes).
- All scripts covered by pure-function unit tests (no HTTP mocking required).

## [1.1.0] — 2026-05-02

### Added
- `references/phases.md` — documentation of all 13 test phases
- `expected_outputs/report_example.md` — example human-readable and JSON reports
- `CHANGELOG.md` — this file
- Argparse CLI with `--help`, `--json` flags on all scripts
- `--compare FILE` flag on contract_test.py for snapshot diffing
- `--output FILE` flag on report_generator.py for custom output path
- Troubleshooting section in README
- Quick-start guide with real output examples
- Complete invocation walkthrough

### Changed
- README now documents httpx dependency and Python 3.10+ requirement
- All scripts now have proper `--help` with usage examples

### Fixed
- Unicode encoding errors on Windows (cp1252) in validation scripts

## [1.0.0] — 2026-05-01

### Added
- Initial release with 13 test phases
- Auto-correction with diff preview and permission flow
- Scripts: security_test.py, contract_test.py, load_test.py, report_generator.py, _shared.py
- SKILL.md with full Claude Code integration
- Support for Python (pytest) and Node.js (jest/vitest)
- MCP Server and REST API testing
- JSON output mode for CI/CD integration