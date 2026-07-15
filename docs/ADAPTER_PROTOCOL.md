# Renderer Adapter Protocol

## Transport

An adapter is an executable invoked once per renderer and case. It receives exactly one JSON request on standard input. It writes diagnostics to standard error and a single JSON response as the last non-empty standard-output line.

Exit code `0` means the adapter produced a valid PDF and response. Any other exit code is a renderer/adapter failure and the runner surfaces standard error.

## Schema 1 Request

```json
{
  "schema_version": 1,
  "html": "C:/absolute/case/document.html",
  "base_path": "C:/absolute/case",
  "output_pdf": "C:/absolute/run/cases/example/renderer/output.pdf",
  "page": {
    "size": "A4",
    "margin_mm": 10
  },
  "warmups": 2,
  "iterations": 10
}
```

Requirements:

- `html`, `base_path`, and `output_pdf` are absolute paths.
- The adapter must resolve relative document assets from `base_path`.
- Warmups do not appear in `samples_ms`.
- The adapter must return exactly `iterations` non-negative measured samples.
- The output parent may not exist; the adapter creates it.
- The PDF at `output_pdf` must exist before the adapter exits successfully.

## Schema 1 Response

```json
{
  "schema_version": 1,
  "renderer": "example-renderer",
  "version": "2.4.1",
  "timing_scope": "process",
  "samples_ms": [51.8, 49.6, 50.2],
  "output_pdf": "C:/absolute/run/cases/example/renderer/output.pdf"
}
```

Required fields are validated by `protocol.py`. Adapters may add forward-compatible metadata such as peak memory, helper wall time, renderer build commit, or warnings; unknown fields are retained in the run bundle.

## Timing Semantics

Choose the narrowest accurate scope:

- `process`: each sample includes launching the renderer command. The bundled wkhtmltopdf adapter uses this scope.
- `warm-engine`: one adapter process constructs/reuses the engine and measures only repeated render operations. The bundled Fulgur adapter uses this scope.
- `adapter-defined`: only for a boundary that does not fit the above; document it in adapter metadata and project documentation.

Do not relabel process time as warm-engine time to make results appear faster. Dashboard comparisons must show absolute timings and scope provenance.

## Adding an Adapter

1. Implement stdin request parsing, validation, rendering, measurement, and response output.
2. Add success, malformed-input, renderer-failure, and missing-output contract tests.
3. Declare the command and timing scope in TOML.
4. Add its id to `comparison.candidates` or use it as `comparison.reference`.
5. Run `validate --require-commands`, smoke cases, and at least one multi-page fixture.

Renderer-specific command flags belong inside the adapter. Do not interpolate user data into a shell command; invoke the renderer with an argument array.

