from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def export(result_path: Path, output_path: Path | None = None) -> dict[str, str]:
    data = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    aggregates = data.get("aggregates") or {}
    values = {
        "status": str(data.get("status", "unknown")),
        "run_id": str(data.get("run_id", "")),
        "quality_score": str(aggregates.get("quality_score", 0)),
        "visual_error_percent": str(aggregates.get("visual_error_percent", 0)),
        "critical_failure_count": str(aggregates.get("critical_failure_count", 0)),
        "failed_case_count": str(data.get("failed_case_count", 0)),
    }
    if output_path:
        with output_path.open("a", encoding="utf-8") as output:
            for key, value in values.items():
                output.write(f"{key}={_command_escape(value)}\n")
    return values


def emit_annotations(path: Path) -> None:
    items = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    for item in items:
        level = "error" if item.get("level") == "error" else "warning"
        title = _command_escape(item.get("title", "Renderer benchmark"))
        message = _command_escape(item.get("message", ""))
        print(f"::{level} title={title}::{message}")


def _command_escape(value) -> str:
    return str(value).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args(argv)
    output = Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None
    export(args.result, output)
    if args.annotations:
        emit_annotations(args.annotations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
