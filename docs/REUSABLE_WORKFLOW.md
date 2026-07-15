# Reusable GitHub Actions workflow

Call the workflow from a candidate repository and provide a build command that creates a protocol-compatible executable inside that candidate checkout.

```yaml
jobs:
  visual-benchmark:
    uses: ElHefe3/renderer-benchmark-lab/.github/workflows/benchmark.yml@<pinned-sha>
    with:
      candidate-repository: ${{ github.repository }}
      candidate-ref: ${{ github.sha }}
      candidate-id: my-renderer
      candidate-build-command: ./scripts/build-benchmark-adapter.sh
      candidate-adapter-path: target/release/my-renderer-benchmark-adapter
```

The workflow uses read-only permissions and does not inherit secrets. It compares Chromium print-to-PDF output with the candidate PDF, writes a concise job summary and annotations, and uploads the complete self-contained visual report for seven days. Timing is reported but does not gate the job. The final gate runs only after report upload.

Inputs `profile`, `artifact-retention-days`, and `fail-on-visual-regression` default to `ci`, `7`, and `true`. Outputs are `status`, `run-id`, `quality-score`, `visual-error-percent`, `critical-failure-count`, `failed-case-count`, and `artifact-url`.
