from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from . import SCHEMA_VERSION
from .config import Renderer


class AdapterError(RuntimeError):
    pass


def invoke(renderer: Renderer, request: dict, timeout: float = 300) -> dict:
    environment = os.environ.copy()
    environment.update(renderer.environment)
    completed = subprocess.run(
        renderer.command, input=json.dumps(request), text=True, capture_output=True,
        timeout=timeout, env=environment, cwd=Path(request["base_path"]),
    )
    if completed.returncode:
        raise AdapterError(f"{renderer.id} failed ({completed.returncode}): {completed.stderr.strip()}")
    try:
        response = json.loads(completed.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as error:
        raise AdapterError(f"{renderer.id} returned invalid JSON") from error
    required = {"schema_version", "renderer", "version", "timing_scope", "samples_ms", "output_pdf"}
    missing = required - response.keys()
    if missing:
        raise AdapterError(f"{renderer.id} response missing: {', '.join(sorted(missing))}")
    if response["schema_version"] != SCHEMA_VERSION:
        raise AdapterError(f"{renderer.id} uses unsupported protocol schema")
    if not response["samples_ms"] or any(float(value) < 0 for value in response["samples_ms"]):
        raise AdapterError(f"{renderer.id} returned invalid timing samples")
    if not Path(response["output_pdf"]).is_file():
        raise AdapterError(f"{renderer.id} did not create output PDF")
    return response


def request(html: Path, output: Path, warmups: int, iterations: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "html": str(html), "base_path": str(html.parent), "output_pdf": str(output),
        "page": {"size": "A4", "margin_mm": 10},
        "warmups": warmups, "iterations": iterations,
    }

