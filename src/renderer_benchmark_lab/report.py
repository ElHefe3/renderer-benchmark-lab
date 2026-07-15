from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import Config


def generate(config: Config, destination: Path | None = None) -> Path:
    destination = (destination or config.path.parent / "dist" / "dashboard").resolve()
    destination.mkdir(parents=True, exist_ok=True)
    assets = Path(__file__).parent / "dashboard"
    for name in ("index.html", "style.css", "app.js"):
        shutil.copy2(assets / name, destination / name)
    data = destination / "data"
    if data.exists():
        shutil.rmtree(data)
    data.mkdir()
    index_path = config.output_root / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {"schema_version": 1, "runs": []}
    (data / "index.js").write_text("window.BENCHMARK_INDEX=" + json.dumps(index) + ";", encoding="utf-8")
    manifests = []
    for summary in index["runs"]:
        run_id = summary["run_id"]
        source = config.output_root / "runs" / run_id
        target = data / "runs" / run_id
        shutil.copytree(source, target)
        manifest = json.loads((target / "run.json").read_text(encoding="utf-8"))
        manifests.append(manifest)
        (target / "run.js").write_text(
            "window.BENCHMARK_RUNS=window.BENCHMARK_RUNS||{};window.BENCHMARK_RUNS["
            + json.dumps(run_id) + "]=" + json.dumps(manifest) + ";", encoding="utf-8",
        )
    latest = manifests[0] if manifests else None
    (destination / "summary.md").write_text(markdown(latest), encoding="utf-8")
    result = ci_result(latest, config)
    (destination / "ci-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (destination / "annotations.json").write_text(json.dumps(annotations(result), indent=2), encoding="utf-8")
    return destination


def _case_rows(manifest: dict | None, config: Config) -> list[dict]:
    if not manifest:
        return []
    rows = []
    default_candidate = (manifest.get("candidates") or list(config.candidates) or [""])[0]
    for case in manifest.get("cases") or []:
        candidate = (case.get("comparisons") or {}).get(default_candidate) or {}
        critical = list(candidate.get("critical_failures") or [])
        error = case.get("error")
        if error:
            critical.append(str(error))
        visual = (candidate.get("categories") or {}).get("visual")
        failed = bool(critical) or float(candidate.get("overall_error_percent", 0) or 0) >= 100
        rows.append({
            "id": str(case.get("id", "unknown")), "failed": failed,
            "reference_pages": candidate.get("reference_pages"),
            "candidate_pages": candidate.get("candidate_pages"),
            "visual_error_percent": visual, "critical_failures": critical,
            "overall_error_percent": candidate.get("overall_error_percent"),
        })
    return rows


def ci_result(manifest: dict | None, config: Config) -> dict:
    if not manifest:
        return {"status": "no-runs", "run_id": "", "aggregates": {}, "budget_checks": [],
                "failed_case_count": 0, "failed_cases": []}
    rows = _case_rows(manifest, config)
    failed = [row for row in rows if row["failed"]]
    aggregate = dict(manifest.get("aggregates") or {})
    aggregate.setdefault("visual_error_percent", _mean(row["visual_error_percent"] for row in rows))
    return {
        "status": manifest.get("status", "unknown"), "run_id": manifest.get("run_id", ""),
        "profile": manifest.get("profile", ""), "aggregates": aggregate,
        "budget_checks": manifest.get("budget_checks") or [],
        "failed_case_count": len(failed), "failed_cases": failed,
        "errors": manifest.get("errors") or [],
    }


def annotations(result: dict) -> list[dict]:
    output = []
    for case in result.get("failed_cases") or []:
        reasons = case.get("critical_failures") or [f'visual error {case.get("visual_error_percent", "n/a")}%']
        message = _one_line(f'{case.get("id", "unknown")}: {"; ".join(map(str, reasons))}')
        output.append({"level": "error", "title": "Renderer benchmark case failed", "message": message})
    return output


def markdown(manifest: dict | None) -> str:
    if not manifest:
        return "# Renderer benchmark\n\nNo completed runs.\n"
    aggregates = manifest.get("aggregates") or {}
    status = str(manifest.get("status", "unknown")).upper()
    lines = [
        "# Renderer benchmark", "",
        f'**{_md(status)}** · {_fmt(aggregates.get("case_count"), 0)} cases · '
        f'{_fmt(aggregates.get("quality_score"))} quality · '
        f'{_fmt(aggregates.get("overall_error_percent"))}% error', "",
        "| Reference mean | Candidate mean | Critical failures |", "|---:|---:|---:|",
        f'| {_fmt(aggregates.get("reference_median_ms"), 2)} ms | '
        f'{_fmt(aggregates.get("candidate_median_ms"), 2)} ms | '
        f'{_fmt(aggregates.get("critical_failure_count"), 0)} |', "",
        f'Run: `{_md(manifest.get("run_id", ""))}` · Profile: `{_md(manifest.get("profile", ""))}`', "",
        "## Budget checks", "", "| Check | Actual | Limit | Result |", "|---|---:|---:|---|",
    ]
    checks = manifest.get("budget_checks") or []
    lines.extend(
        f'| {_md(item.get("name", "unknown"))} | {_fmt(item.get("actual"))} | '
        f'{_fmt(item.get("limit"))} | {"PASS" if item.get("passed") else "FAIL"} |' for item in checks
    )
    if not checks:
        lines.append("| No checks | n/a | n/a | n/a |")
    rows = []
    candidates = manifest.get("candidates") or [""]
    candidate_id = candidates[0]
    for case in manifest.get("cases") or []:
        comparison = (case.get("comparisons") or {}).get(candidate_id) or {}
        rows.append((case, comparison))
    rows.sort(key=lambda pair: (not bool(pair[1].get("critical_failures")), -float(pair[1].get("overall_error_percent", 0) or 0)))
    lines += ["", "## Failed or worst cases", "", "| Case | Pages ref/candidate | Visual error | Critical failures |", "|---|---:|---:|---|"]
    for case, comparison in rows[:10]:
        failures = "; ".join(map(str, comparison.get("critical_failures") or [])) or "—"
        visual = (comparison.get("categories") or {}).get("visual")
        lines.append(f'| {_md(case.get("id", "unknown"))} | {_fmt(comparison.get("reference_pages"), 0)}/{_fmt(comparison.get("candidate_pages"), 0)} | {_fmt(visual)}% | {_md(failures)} |')
    return "\n".join(lines) + "\n"


def _mean(values) -> float:
    numbers = [float(value) for value in values if value is not None]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _fmt(value, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def _md(value) -> str:
    return _one_line(value).replace("|", "\\|").replace("`", "\\`")


def _one_line(value) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())
