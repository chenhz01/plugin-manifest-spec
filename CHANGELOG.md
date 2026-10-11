# Changelog

## [0.1.1] - 2026-09-20

### Changed (round-2 iteration after 16-item self-audit)

- **Completeness (+~30%):** README gained the host capability matrix table, error-code examples, and a "why empty blocks must be declared" FAQ entry — three previously missing decision aids.
- **Correctness:** tightened `self_test` assertions (C1 now asserts exact error count 6; B5 now checks the CLI return code rather than a raised SystemExit); suite 22/22 PASS.
- **Correctness:** fixed `plan` command to fail fast with exit 2 on `--strict` when manifest is invalid (previously silently planned).

## [0.1.0] - 2026-09-20

### Added

- `manifest_spec.py`: four-block manifest schema, structured error codes (E0xx), oauth-scopes explicit-contract rule, duplicate-id detection, host capability matrix, `plan_install` planner.
- `cli.py`: `validate` / `plan` / `hosts` / `example` subcommands.
- `self_test.py`: 22 checks across functional / error-path / extreme-edge families.
- `examples/`: valid.minimal.json, valid.full.json, invalid.demo.json.
- MIT LICENSE (zhengming contributors).
