from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import fitz

from . import SCHEMA_VERSION


def main() -> int:
    request = json.load(sys.stdin)
    output = Path(request["output_pdf"])
    output.parent.mkdir(parents=True, exist_ok=True)
    variant = os.environ.get("MOCK_VARIANT", "reference")
    samples = []
    for _ in range(request["iterations"]):
        start = time.perf_counter()
        document = fitz.open()
        page = document.new_page(width=595, height=842)
        text = Path(request["html"]).read_text(encoding="utf-8")
        page.insert_textbox(fitz.Rect(45,45,550,790), f"{variant}\n{text[:3500]}", fontsize=8)
        document.save(output)
        document.close()
        samples.append((time.perf_counter()-start)*1000)
    print(json.dumps({"schema_version":SCHEMA_VERSION,"renderer":f"mock-{variant}","version":"1",
                      "timing_scope":"process","samples_ms":samples,"output_pdf":str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

