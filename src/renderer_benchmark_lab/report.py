from __future__ import annotations

import json
import shutil
from pathlib import Path
from string import Template

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
    for summary in index["runs"]:
        run_id = summary["run_id"]
        source = config.output_root / "runs" / run_id
        target = data / "runs" / run_id
        shutil.copytree(source, target)
        manifest = json.loads((target / "run.json").read_text(encoding="utf-8"))
        (target / "run.js").write_text("window.BENCHMARK_RUNS=window.BENCHMARK_RUNS||{};window.BENCHMARK_RUNS[" +
                                      json.dumps(run_id) + "]=" + json.dumps(manifest) + ";", encoding="utf-8")
    (destination / "summary.md").write_text(markdown(index, config), encoding="utf-8")
    return destination


def markdown(index: dict, config: Config) -> str:
    if not index.get("runs"):
        return "# Renderer benchmark\n\nNo completed runs.\n"
    run = index["runs"][0]
    a = run["aggregates"]
    checks = "Passed" if run["status"] == "passed" else "Failed"
    return Template("""# Renderer benchmark

**$status** · $cases cases · $quality quality · $error% error

| Reference mean | Candidate mean | Critical failures |
|---:|---:|---:|
| $reference ms | $candidate ms | $critical |

Run: `$run_id` · Profile: `$profile`
""").substitute(status=checks, cases=a["case_count"], quality=f'{a["quality_score"]:.1f}',
                  error=f'{a["overall_error_percent"]:.1f}', reference=f'{a["reference_median_ms"]:.2f}',
                  candidate=f'{a["candidate_median_ms"]:.2f}', critical=a["critical_failure_count"],
                  run_id=run["run_id"], profile=run["profile"])

