from dataclasses import replace
from pathlib import Path

from renderer_benchmark_lab.config import load
from renderer_benchmark_lab.report import generate


def test_empty_static_report(tmp_path):
    root = Path(__file__).parents[1]
    config = replace(load(root / "benchmark.smoke.toml"), output_root=tmp_path / "empty-runs")
    output = generate(config, tmp_path / "site")
    assert (output / "index.html").is_file()
    assert "No completed runs" in (output / "summary.md").read_text()
    assert not (config.output_root / "index.json").exists()
    result = (output / "ci-result.json").read_text(encoding="utf-8")
    assert '"status": "no-runs"' in result


def test_ci_report_contains_failures_and_escaped_markdown(tmp_path):
    import json

    root = Path(__file__).parents[1]
    output_root = tmp_path / "runs"
    run_id = "20260715T000000Z"
    run_root = output_root / "runs" / run_id
    run_root.mkdir(parents=True)
    manifest = {
        "schema_version": 1, "run_id": run_id, "profile": "ci", "status": "failed",
        "candidates": ["candidate"],
        "aggregates": {"case_count": 1, "quality_score": 0, "overall_error_percent": 100,
                       "visual_error_percent": 100, "critical_failure_count": 1,
                       "reference_median_ms": 10, "candidate_median_ms": 12},
        "budget_checks": [{"name": "visual error", "actual": 100, "limit": 35, "passed": False}],
        "cases": [{"id": "bad|case", "comparisons": {"candidate": {
            "categories": {"visual": 100}, "overall_error_percent": 100,
            "critical_failures": ["remote\nasset blocked"], "reference_pages": 1, "candidate_pages": 0,
        }}}],
    }
    (run_root / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
    (output_root / "index.json").write_text(json.dumps({"schema_version": 1, "runs": [{
        key: manifest[key] for key in ("run_id", "status", "profile", "aggregates")
    }]}), encoding="utf-8")
    config = replace(load(root / "benchmark.smoke.toml"), output_root=output_root)
    output = generate(config, tmp_path / "site")
    summary = (output / "summary.md").read_text(encoding="utf-8")
    result = json.loads((output / "ci-result.json").read_text(encoding="utf-8"))
    annotations = json.loads((output / "annotations.json").read_text(encoding="utf-8"))
    assert "bad\\|case" in summary
    assert result["failed_case_count"] == 1
    assert "\n" not in annotations[0]["message"]
