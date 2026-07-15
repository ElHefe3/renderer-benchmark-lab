# Architecture

## System Goal

Renderer Benchmark Lab measures whether a candidate PDF renderer is moving toward an explicit development goal without coupling the framework to one renderer or one application. A run answers two independent questions:

1. How long did each renderer take under its declared timing scope?
2. How different is each candidate PDF from the selected reference PDF for the same materialized HTML and local assets?

Chromium print-to-PDF is the bundled default reference and Fulgur is the initial candidate. Neither identity is embedded in the runner, scoring, run schema, or dashboard; wkhtmltopdf remains an optional adapter.

## Data Flow

```text
benchmark.toml
  ├─ renderer declarations ──> executable adapters
  ├─ cases/profiles ─────────> materialized HTML + local assets
  ├─ scoring weights ────────> metric aggregation
  └─ budgets ────────────────> CI pass/fail checks

runner
  ├─ sends protocol request to reference and candidates
  ├─ receives PDF path, timing samples, version, and timing scope
  ├─ rasterizes PDFs and extracts text/resources
  ├─ compares each candidate to the reference
  └─ writes a versioned run bundle

reporter
  ├─ copies retained run bundles into a relative static-site layout
  ├─ writes data/index.js and one run.js per run
  ├─ writes summary.md
  └─ produces dist/dashboard/ for local serving, CI artifacts, or Pages
```

The dashboard never invokes renderers. It is a read-only presentation of completed bundles and works without an application backend.

## Component Boundaries

### Configuration

`config.py` resolves environment variables and paths relative to the selected TOML file, creates typed configuration objects, and performs structural validation. `validate --require-commands` additionally verifies that adapter executables exist.

### Adapter execution

`protocol.py` owns subprocess invocation and schema validation. An adapter may be written in any language. It owns renderer-specific flags and internal timing, and it must produce the requested PDF before returning success.

Timing scopes:

- `process` includes process startup for each sample.
- `warm-engine` measures repeated renders inside a long-lived renderer process.
- `adapter-defined` is allowed only when the adapter clearly documents its boundary.

### Metrics and scoring

`metrics.py` rasterizes pages with PyMuPDF and calculates five categories:

- Text: missing words, unexpected words, and extracted reading-order divergence.
- Layout: ink bounding-box overlap and painted-area drift.
- Pagination: page-count and blank-page differences.
- Assets: PDF image and drawing-resource count differences.
- Visual: structural similarity and normalized pixel error.

Category values are 0–100 error percentages; lower is better. The configured weighted mean becomes overall error and quality is `100 - error`. Missing required text, empty output, or violated page bounds is a critical failure and caps case quality below 50.

This is reference-relative fidelity, not absolute CSS conformance. Visual artifacts remain the final diagnostic evidence.

### Budgets and baselines

`budgets.py` evaluates absolute error/critical limits and, when `.bench/baseline.json` exists, quality and speed regression limits. Baselines are local or supplied by CI; they are not source fixtures and should not be committed accidentally.

### Run bundles

Schema 1 layout:

```text
.bench/<suite>/
  index.json
  baseline.json                 # optional
  runs/<UTC-run-id>/
    run.json
    cases/<case-id>/
      <renderer-id>/output.pdf
      <renderer-id>/page-N.png
      diff-<candidate-id>/page-N.png
```

`run.json` contains environment provenance, renderer responses, case complexity, comparisons, aggregates, budget checks, and status. The newest configured number of runs is retained.

## Extension Points

- New renderer: implement protocol schema 1 and add a renderer declaration.
- New workload: add a self-contained fixture and case metadata.
- New metric: add it within a category or introduce a versioned schema change; update tests and dashboard together.
- New CI system: reproduce install, adapter build, validation, run, and artifact-upload commands.

Avoid adding renderer-specific switches to the CLI or top-level run schema. If a renderer needs special settings, place them in adapter configuration or a future explicit protocol extension.
