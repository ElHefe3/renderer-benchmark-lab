from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def render(request: dict) -> dict:
    from playwright.sync_api import sync_playwright

    html = Path(request["html"]).resolve()
    output = Path(request["output_pdf"]).resolve()
    if not html.is_file():
        raise FileNotFoundError(f"HTML input not found: {html}")
    iterations = int(request["iterations"])
    warmups = int(request.get("warmups", 0))
    if iterations < 1 or warmups < 0:
        raise ValueError("iterations must be positive and warmups non-negative")
    output.parent.mkdir(parents=True, exist_ok=True)
    page_config = request.get("page", {})
    size = str(page_config.get("size", "A4"))
    margin = f'{float(page_config.get("margin_mm", 10))}mm'
    pdf_options = {
        "path": str(output), "format": size, "print_background": True,
        "margin": {name: margin for name in ("top", "right", "bottom", "left")},
    }
    samples: list[float] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US", timezone_id="UTC")
        page = context.new_page()
        page.route("http://**/*", lambda route: route.abort())
        page.route("https://**/*", lambda route: route.abort())
        page.emulate_media(media="print")
        for index in range(warmups + iterations):
            started = time.perf_counter()
            page.goto(html.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.pdf(**pdf_options)
            elapsed = (time.perf_counter() - started) * 1000
            if index >= warmups:
                samples.append(elapsed)
        version = browser.version
        context.close()
        browser.close()
    return {
        "schema_version": int(request["schema_version"]), "renderer": "chromium",
        "version": version, "timing_scope": "adapter-defined", "samples_ms": samples,
        "timing_detail": "navigation, font readiness, and PDF generation in a warm browser",
        "output_pdf": str(output),
    }


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        if request.get("schema_version") != 1:
            raise ValueError("unsupported schema")
        print(json.dumps(render(request)))
        return 0
    except Exception as error:
        print(f"chromium adapter failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
