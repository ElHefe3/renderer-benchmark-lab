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
    for case_id in selected:
        case = config.cases[case_id]
        case_root = root / "cases" / case_id
        responses, rasters = {}, {}
        for renderer_id in (config.reference, *config.candidates):
            render_root = case_root / renderer_id
            render_root.mkdir(parents=True)
            pdf = render_root / "output.pdf"
            responses[renderer_id] = invoke(config.renderers[renderer_id], request(case.html, pdf, profile.warmups, profile.iterations))
            rasters[renderer_id] = rasterize(pdf, profile.dpi, render_root)
        comparisons = {}
        for candidate_id in config.candidates:
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
    aggregate = {
        "case_count": len(results),
        "quality_score": statistics.fmean(item["comparisons"][primary]["quality_score"] for item in results),
        "overall_error_percent": statistics.fmean(item["comparisons"][primary]["overall_error_percent"] for item in results),
        "critical_failure_count": sum(len(item["comparisons"][primary]["critical_failures"]) for item in results),
        "reference_median_ms": statistics.fmean(statistics.median(item["renderers"][config.reference]["samples_ms"]) for item in results),
        "candidate_median_ms": statistics.fmean(statistics.median(item["renderers"][primary]["samples_ms"]) for item in results),
    }
    baseline = _baseline(config)
    checks = evaluate(aggregate, config.budgets, baseline.get("aggregates") if baseline else None)
    manifest = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "created_at": created.isoformat(), "profile": profile_name,
        "status": "failed" if any(not check["passed"] for check in checks) else "passed",
        "environment": {"os": platform.platform(), "python": platform.python_version(), "commit": _git_commit(config.path.parent)},
        "reference": config.reference, "candidates": list(config.candidates), "aggregates": aggregate,
        "budget_checks": checks, "cases": results,
    }
    (root / "run.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _history(config)
    return root, manifest


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
