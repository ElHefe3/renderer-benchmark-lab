from __future__ import annotations

import json
import platform
import shutil
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import SCHEMA_VERSION
from .budgets import evaluate
from .config import Config
from .metrics import compare, complexity, rasterize
from .protocol import invoke, request


def run(config: Config, profile_name: str) -> tuple[Path, dict]:
    profile = config.profiles[profile_name]
    created = datetime.now(timezone.utc)
    run_id = created.strftime("%Y%m%dT%H%M%SZ")
    root = config.output_root / "runs" / run_id
    root.mkdir(parents=True)
    selected = profile.cases or tuple(config.cases)
    results = []
    run_errors = []
    for case_id in selected:
        case = config.cases[case_id]
        case_root = root / "cases" / case_id
        responses, rasters, renderer_errors = {}, {}, {}
        for renderer_id in (config.reference, *config.candidates):
            render_root = case_root / renderer_id
            render_root.mkdir(parents=True)
            pdf = render_root / "output.pdf"
            try:
                responses[renderer_id] = invoke(
                    config.renderers[renderer_id], request(case.html, pdf, profile.warmups, profile.iterations)
                )
                rasters[renderer_id] = rasterize(pdf, profile.dpi, render_root)
            except Exception as error:
                message = f"{renderer_id}: {error}"
                renderer_errors[renderer_id] = message
                run_errors.append(f"{case_id}: {message}")
                responses[renderer_id] = {
                    "renderer": renderer_id, "version": "unknown",
                    "timing_scope": config.renderers[renderer_id].timing_scope,
                    "samples_ms": [], "output_pdf": str(pdf), "error": str(error),
                }
        comparisons = {}
        for candidate_id in config.candidates:
            if config.reference not in rasters or candidate_id not in rasters:
                failures = [renderer_errors[key] for key in (config.reference, candidate_id) if key in renderer_errors]
                comparisons[candidate_id] = _failed_comparison(failures)
                continue
            diff = case_root / f"diff-{candidate_id}"
            diff.mkdir()
            metric = compare(rasters[config.reference], rasters[candidate_id], diff, case.required_text)
            weighted = sum(metric["categories"].get(name, 0) * weight for name, weight in config.weights.items()) / sum(config.weights.values())
            critical = list(metric["required_text_missing"])
            if not rasters[candidate_id]["pages"]:
                critical.append("candidate produced no pages")
            page_count = len(rasters[candidate_id]["pages"])
            if case.min_pages is not None and page_count < case.min_pages:
                critical.append(f"candidate has fewer than {case.min_pages} pages")
            if case.max_pages is not None and page_count > case.max_pages:
                critical.append(f"candidate has more than {case.max_pages} pages")
            quality = min(49, 100-weighted) if critical else 100-weighted
            comparisons[candidate_id] = {
                **metric, "overall_error_percent": weighted, "quality_score": quality, "critical_failures": critical,
                "reference_pages": len(rasters[config.reference]["pages"]), "candidate_pages": len(rasters[candidate_id]["pages"]),
            }
        results.append({"id": case_id, "tags": case.tags, "complexity": complexity(case.html),
                        "renderers": responses, "comparisons": comparisons})
    primary = config.candidates[0]
    completed = [item for item in results if item["comparisons"].get(primary)]
    aggregate = {
        "case_count": len(results),
        "quality_score": _mean(item["comparisons"][primary]["quality_score"] for item in completed),
        "overall_error_percent": _mean(item["comparisons"][primary]["overall_error_percent"] for item in completed),
        "visual_error_percent": _mean(item["comparisons"][primary]["categories"]["visual"] for item in completed),
        "critical_failure_count": sum(len(item["comparisons"][primary]["critical_failures"]) for item in results),
        "reference_median_ms": _timing_mean(results, config.reference),
        "candidate_median_ms": _timing_mean(results, primary),
    }
    baseline = _baseline(config)
    checks = evaluate(aggregate, config.budgets, baseline.get("aggregates") if baseline else None)
    manifest = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": created.isoformat(), "profile": profile_name,
        "status": "failed" if any(not check["passed"] for check in checks) else "passed",
        "environment": {"os": platform.platform(), "python": platform.python_version(), "commit": _git_commit(config.path.parent)},
        "reference": config.reference, "candidates": list(config.candidates), "aggregates": aggregate,
        "budget_checks": checks, "cases": results, "errors": run_errors,
    }
    (root / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _history(config)
    return root, manifest


def _failed_comparison(failures: list[str]) -> dict:
    failures = failures or ["comparison could not be completed"]
    return {
        "categories": {name: 100.0 for name in ("text", "layout", "pagination", "assets", "visual")},
        "required_text_missing": [], "ssim": 0.0, "pixel_error": 1.0,
        "overall_error_percent": 100.0, "quality_score": 0.0,
        "critical_failures": failures, "reference_pages": 0, "candidate_pages": 0,
    }


def _mean(values) -> float:
    items = list(values)
    return statistics.fmean(items) if items else 0.0


def _timing_mean(results: list[dict], renderer_id: str) -> float:
    medians = []
    for item in results:
        samples = item["renderers"].get(renderer_id, {}).get("samples_ms", [])
        if samples:
            medians.append(statistics.median(samples))
    return _mean(medians)


def approve(config: Config, run_id: str) -> Path:
    source = config.output_root / "runs" / run_id / "run.json"
    if not source.is_file():
        raise FileNotFoundError(f"run not found: {run_id}")
    target = config.output_root / "baseline.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _baseline(config):
    path = config.output_root / "baseline.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _history(config):
    runs = sorted((config.output_root / "runs").glob("*/run.json"), reverse=True)
    for manifest in runs[config.history_limit:]:
        shutil.rmtree(manifest.parent)
    index = [{key: value[key] for key in ("run_id","created_at","status","profile","aggregates")}
             for value in (json.loads(item.read_text(encoding="utf-8")) for item in runs[:config.history_limit])]
    (config.output_root / "index.json").write_text(json.dumps({"schema_version":1,"runs":index},indent=2),encoding="utf-8")


def _git_commit(root):
    try:
        return subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,timeout=5,check=True).stdout.strip()
    except Exception:
        return "unknown"
