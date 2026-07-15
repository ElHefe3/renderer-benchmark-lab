from pathlib import Path

from renderer_benchmark_lab.budgets import evaluate
from renderer_benchmark_lab.config import load, validate
from renderer_benchmark_lab.protocol import AdapterError, invoke


ROOT = Path(__file__).parents[1]


def test_smoke_configuration_is_valid():
    config = load(ROOT / "benchmark.smoke.toml")
    assert validate(config) == []
    assert config.reference == "reference"
    assert config.profiles["smoke"].iterations == 1


def test_budget_absolute_and_regression_checks():
    aggregate = {"overall_error_percent": 12, "visual_error_percent": 8, "critical_failure_count": 0,
                 "quality_score": 88, "candidate_median_ms": 110}
    baseline = {"quality_score": 90, "candidate_median_ms": 100}
    checks = evaluate(aggregate, {"max_error_percent": 15, "max_quality_regression": 1,
                                  "max_speed_regression_percent": 5}, baseline)
    assert [item["passed"] for item in checks] == [True, False, False]


def test_visual_budget_is_independent_from_timing():
    aggregate = {"overall_error_percent": 12, "visual_error_percent": 40,
                 "critical_failure_count": 0, "quality_score": 88, "candidate_median_ms": 999}
    checks = evaluate(aggregate, {"max_visual_error_percent": 35})
    assert checks == [{"name": "visual error", "actual": 40, "limit": 35, "passed": False}]


def test_adapter_rejects_invalid_json(tmp_path):
    from renderer_benchmark_lab.config import Renderer
    renderer = Renderer("bad", ["python", "-c", "print('not-json')"], "process", {})
    request = {"base_path": str(tmp_path), "output_pdf": str(tmp_path / "x.pdf")}
    try:
        invoke(renderer, request)
    except AdapterError as error:
        assert "invalid JSON" in str(error)
    else:
        raise AssertionError("invalid adapter response accepted")
