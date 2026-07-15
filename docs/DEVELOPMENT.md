# Development and Operations

## Local Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
$env:PYTHONPATH = "$PWD\src"
```

Setting `PYTHONPATH` explicitly is important when another editable installation exists. Adapter subprocesses run with each fixture directory as their working directory, so a stale editable install can otherwise load code from an old worktree.

## Fast Local Loop

The smoke configuration uses mock adapters and requires no wkhtmltopdf or Rust binary:

```powershell
python -m renderer_benchmark_lab.cli --config benchmark.smoke.toml validate
python -m renderer_benchmark_lab.cli --config benchmark.smoke.toml run --profile smoke
python -m renderer_benchmark_lab.cli --config benchmark.smoke.toml serve
```

Open `http://127.0.0.1:8000/`. Stop the server with `Ctrl+C` before moving or deleting the repository on Windows, because the server holds its working directory open.

## Real wkhtmltopdf/Fulgur Run on This Machine

The current wkhtmltopdf installation used by the prototype is:

```powershell
$env:WKHTMLTOPDF_BIN = "C:\Users\kobus\Documents\projects\document-templating-system\tools\wkhtmltox\bin\wkhtmltopdf.exe"
```

Build and configure Fulgur:

```powershell
cargo build --release --manifest-path adapters\fulgur\Cargo.toml
$env:FULGUR_ADAPTER_BIN = "$PWD\adapters\fulgur\target\release\renderer-bench-fulgur.exe"
```

Never use literal documentation placeholders such as `C:\path\to\wkhtmltopdf.exe`. Verify both paths first:

```powershell
Test-Path $env:WKHTMLTOPDF_BIN
Test-Path $env:FULGUR_ADAPTER_BIN
```

Then run:

```powershell
python -m renderer_benchmark_lab.cli --config benchmark.toml validate --require-commands
python -m renderer_benchmark_lab.cli --config benchmark.toml run --profile full
python -m renderer_benchmark_lab.cli --config benchmark.toml serve
```

The full profile currently covers tiny text/assets, a small report, a one-page invoice, a multi-column newsletter, a long contract, and an image-heavy catalogue.

## Adding a Fixture

1. Create `fixtures/<case-id>/document.html` and local assets under the same directory.
2. Do not use remote fonts, scripts, images, APIs, timestamps, or random content.
3. Materialize enough content to exercise the intended failure mode without JavaScript.
4. Add the case to `benchmark.toml` with tags, at least one required-text marker, and realistic `min_pages`/`max_pages` where pagination is meaningful.
5. Add it to the appropriate profile. Keep pre-commit/smoke reasonably fast.
6. Render once with both target renderers and inspect every page before accepting the page bounds.

Current reference page counts with wkhtmltopdf are invoice 1, newsletter 2, contract 3, and catalogue 3. Bounds intentionally allow modest renderer differences while catching severe pagination failures.

## Reports and Baselines

Every successful `run` regenerates `dist/dashboard/`. It uses only relative paths and may be served locally, uploaded as a CI artifact, or published to static hosting.

Approve a selected run as the local regression baseline only with explicit authorization:

```powershell
python -m renderer_benchmark_lab.cli --config benchmark.toml baseline approve <run-id>
```

Both `.bench/` and `dist/` are ignored. A report can be regenerated from retained bundles without rerendering:

```powershell
python -m renderer_benchmark_lab.cli --config benchmark.toml report
```

## CI and Pre-commit

`.pre-commit-config.yaml` runs the mock smoke suite. The GitHub workflow installs wkhtmltopdf, builds the Rust Fulgur adapter, executes the full profile, enforces budgets, writes the Markdown job summary, and uploads the static site. Pages deployment occurs only when manually requested with `publish_pages=true`.

Do not weaken budgets to make CI green without evidence. Determine whether the failure is performance variance, a reference change, fixture instability, or a real renderer regression.

## Troubleshooting

### FileNotFoundError for wkhtmltopdf or Fulgur

The environment variable points at a placeholder or missing binary. Run `Test-Path` and `validate --require-commands` before a full run.

### Adapter traceback references another worktree

The child Python process found a stale editable installation. Set `$env:PYTHONPATH = "$PWD\src"` and reinstall the current checkout if necessary:

```powershell
.venv\Scripts\python -m pip install -e ".[dev]"
```

### Rust reports `link.exe` not found

Install/load Visual Studio C++ Build Tools for the MSVC toolchain, or run the Linux GitHub workflow. Formatting and Python smoke success do not prove the Rust adapter compiled.

### Repository cannot be moved on Windows

Stop `renderer-bench serve` or any `python -m http.server` process using the directory. A running server holds the project path open.

### Full run is slow

The full profile uses 10 measured samples at 144 DPI across six cases. Use the mock smoke profile during iteration; do not publish smoke timings as renderer performance evidence.

