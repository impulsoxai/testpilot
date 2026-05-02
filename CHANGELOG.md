# Changelog

All notable changes to TestPilot are documented here.

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