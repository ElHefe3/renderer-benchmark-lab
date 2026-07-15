# Renderer Benchmark Lab

A renderer-neutral framework for tracking PDF rendering speed, fidelity, pagination, text, layout, and assets against an explicit development goal.

## Documentation

- [Architecture and data flow](docs/ARCHITECTURE.md)
- [Development, fixtures, CI, and troubleshooting](docs/DEVELOPMENT.md)
- [Renderer adapter protocol](docs/ADAPTER_PROTOCOL.md)
- [Instructions for coding agents](AGENTS.md)

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
renderer-bench --config benchmark.smoke.toml run --profile smoke
renderer-bench --config benchmark.smoke.toml serve
```

Open `http://127.0.0.1:8000/`. The generated `dist/dashboard/` directory is self-contained and can be uploaded to any static host. `dist/dashboard/summary.md` is suitable for GitHub or CI job summaries.

## Chromium and Fulgur comparison

Install the pinned Chromium browser and build the bundled warm-engine Fulgur adapter:

```powershell
cargo build --release --manifest-path adapters/fulgur/Cargo.toml
$env:FULGUR_ADAPTER_BIN = "$PWD\adapters\fulgur\target\release\renderer-bench-fulgur.exe"
python -m playwright install chromium
$env:CANDIDATE_ID = "fulgur"
renderer-bench validate --require-commands
renderer-bench run --profile full
```

`benchmark.toml` is the public suite definition. Add another renderer by declaring an executable adapter and adding its id to `comparison.candidates`.

## Adapter protocol

An adapter reads one JSON request from stdin and writes one JSON response to stdout. Schema 1 requests include `html`, `base_path`, `output_pdf`, A4 page configuration, `warmups`, and `iterations`. Responses include `renderer`, `version`, `timing_scope`, `samples_ms`, and `output_pdf`. Any language may implement the protocol.

Timing scopes are explicit: wkhtmltopdf reports process time while the bundled Fulgur adapter reports warm-engine time. The dashboard never hides this distinction.

## Goals and baselines

Budgets in `benchmark.toml` cover maximum overall error, critical failures, quality regression, and speed regression. Approve a known run locally with:

```powershell
renderer-bench baseline approve <run-id>
```

The baseline and runs live under ignored `.bench/`. CI uploads the dashboard and complete artifacts; it does not commit generated results. GitHub Pages publication is opt-in through the workflow input.

## Automation

- `pre-commit run renderer-benchmark-smoke` runs deterministic tiny, small, and invoice mock-renderer cases.
- The reusable GitHub workflow installs pinned Chromium, builds a supplied candidate adapter, runs the CI profile, and always uploads the complete visual report.
- Other CI systems need the same four commands: install, build adapters, `renderer-bench validate`, and `renderer-bench run`.
