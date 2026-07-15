from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import SCHEMA_VERSION


def main() -> int:
    request = json.load(sys.stdin)
    binary = os.environ.get("WKHTMLTOPDF_BIN") or shutil.which("wkhtmltopdf")
    if not binary:
        print("WKHTMLTOPDF_BIN is not set and wkhtmltopdf is not on PATH", file=sys.stderr)
        return 2
    output, samples = Path(request["output_pdf"]), []
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [binary,"--enable-local-file-access","--print-media-type","--page-size",request["page"]["size"],
               "--margin-top","10mm","--margin-right","10mm","--margin-bottom","10mm","--margin-left","10mm",
               request["html"],str(output)]
    version = subprocess.run([binary,"--version"],capture_output=True,text=True).stdout.strip()
    for index in range(request["warmups"] + request["iterations"]):
        start = time.perf_counter()
        completed = subprocess.run(command,cwd=request["base_path"],capture_output=True,text=True)
        elapsed = (time.perf_counter()-start)*1000
        if completed.returncode:
            print(completed.stderr,file=sys.stderr)
            return completed.returncode
        if index >= request["warmups"]:
            samples.append(elapsed)
    print(json.dumps({"schema_version":SCHEMA_VERSION,"renderer":"wkhtmltopdf","version":version,
                      "timing_scope":"process","samples_ms":samples,"output_pdf":str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

