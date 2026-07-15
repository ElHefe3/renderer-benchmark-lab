# Agent Instructions

## Purpose

This repository is a renderer-neutral PDF benchmark framework. It exists to turn PDF-renderer development goals into repeatable speed, fidelity, pagination, text, layout, and asset measurements. The initial real comparison is wkhtmltopdf (reference) versus Fulgur (candidate), but core code and result schemas must not assume those names.

Read these before changing behavior:

1. `docs/ARCHITECTURE.md` — components, data flow, result ownership, and scoring boundaries.
2. `docs/DEVELOPMENT.md` — setup, commands, fixture workflow, testing, CI, and troubleshooting.
3. `docs/ADAPTER_PROTOCOL.md` — the stable renderer integration contract.

## Working Rules

- Keep renderer-specific behavior in adapters. The runner, metrics, budgets, and dashboard remain renderer-neutral.
- Treat the reference renderer as a comparison baseline, not a correctness oracle.
- Keep absolute timing separate from fidelity scores. Always record the adapter's timing scope.
- Do not silently compare incompatible timing scopes as if they were identical.
- Never commit `.bench/`, `dist/`, build output, PDFs, page rasters, or local baselines.
- Fixtures must be deterministic, self-contained, legally reusable, and free of remote network dependencies.
- Each new fixture needs meaningful tags, required-text assertions, and realistic page bounds in `benchmark.toml`.
- Preserve schema compatibility. Bump `SCHEMA_VERSION` and document a migration when a protocol or run-bundle change is incompatible.
- Do not push, publish Pages, approve a baseline, or change regression budgets unless the user explicitly asks.

## Required Checks

For Python, configuration, or fixture changes:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m pytest -q --basetemp .pytest-agent
python -m ruff check src tests
python -m renderer_benchmark_lab.cli --config benchmark.toml validate
python -m renderer_benchmark_lab.cli --config benchmark.smoke.toml run --profile smoke
node --check src\renderer_benchmark_lab\dashboard\app.js
```

For Fulgur adapter changes, also run:

```powershell
cargo fmt --manifest-path adapters\fulgur\Cargo.toml -- --check
cargo check --manifest-path adapters\fulgur\Cargo.toml
```

On Windows, `cargo check` requires the MSVC C++ Build Tools and a shell where `link.exe` is available. If that toolchain is unavailable, report the limitation and rely on the Linux CI build; do not claim the adapter compiled locally.

## Repository Map

- `benchmark.toml` — real wkhtmltopdf/Fulgur suite, cases, profiles, weights, budgets, and retention.
- `benchmark.smoke.toml` — dependency-light mock-adapter suite used for local checks and pre-commit.
- `src/renderer_benchmark_lab/` — CLI, config, protocol, orchestration, metrics, budgets, reporting, and bundled Python adapters.
- `src/renderer_benchmark_lab/dashboard/` — static dashboard source copied into `dist/dashboard/`.
- `adapters/fulgur/` — warm-engine Rust adapter implementing protocol schema 1.
- `fixtures/` — committed, self-contained HTML workloads and local assets.
- `tests/` — unit and contract-oriented tests.
- `.github/workflows/benchmark.yml` — full Linux comparison, budget gate, artifacts, and opt-in Pages deployment.

