import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from renderer_benchmark_lab.ci_export import export
from renderer_benchmark_lab.config import load
from renderer_benchmark_lab.metrics import compare
from renderer_benchmark_lab.runner import run


ROOT = Path(__file__).parents[1]


def test_runner_preserves_partial_report_after_adapter_failure(tmp_path):
    config = replace(load(ROOT / "benchmark.smoke.toml"), output_root=tmp_path / "runs")
    with patch("renderer_benchmark_lab.runner.invoke", side_effect=RuntimeError("renderer exploded")):
        root, manifest = run(config, "smoke")
    assert (root / "run.json").is_file()
    assert manifest["status"] == "failed"
    assert manifest["errors"]
    assert manifest["aggregates"]["critical_failure_count"] > 0


def test_visual_comparison_writes_heatmap_and_overlay(tmp_path):
    white = np.full((8, 8, 3), 255, dtype=np.uint8)
    black = np.zeros((8, 8, 3), dtype=np.uint8)
    reference = {"pages": [white], "texts": ["hello"], "blank_pages": [],
                 "resources": {"images": 0, "drawings": 0}}
    candidate = {"pages": [black], "texts": ["hello"], "blank_pages": [],
                 "resources": {"images": 0, "drawings": 0}}
    diff = tmp_path / "diff-candidate"
    diff.mkdir()
    result = compare(reference, candidate, diff)
    assert result["categories"]["visual"] > 0
    assert (diff / "page-1.png").is_file()
    assert (tmp_path / "overlay-candidate" / "page-1.png").is_file()


def test_ci_export_writes_workflow_outputs(tmp_path):
    result = tmp_path / "ci-result.json"
    result.write_text(json.dumps({"status": "failed", "run_id": "run-1", "failed_case_count": 2,
                                  "aggregates": {"quality_score": 80, "visual_error_percent": 20,
                                                 "critical_failure_count": 1}}), encoding="utf-8")
    output = tmp_path / "github-output"
    values = export(result, output)
    assert values["failed_case_count"] == "2"
    assert "visual_error_percent=20" in output.read_text(encoding="utf-8")


def test_reusable_workflow_contract():
    workflow = (ROOT / ".github" / "workflows" / "benchmark.yml").read_text(encoding="utf-8")
    for name in ("candidate-repository", "candidate-ref", "candidate-id", "candidate-build-command",
                 "candidate-adapter-path", "artifact-retention-days", "fail-on-visual-regression"):
        assert name in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "compression-level: 0" in workflow
    assert "retention-days: ${{ inputs.artifact-retention-days }}" in workflow
    assert workflow.index("Upload complete visual report") < workflow.index("Apply visual gate")
