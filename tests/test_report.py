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
