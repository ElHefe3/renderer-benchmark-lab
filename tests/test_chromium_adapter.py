import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

from renderer_benchmark_lab.chromium_adapter import main, render


def test_render_uses_print_media_blocks_network_and_returns_samples(tmp_path):
    html = tmp_path / "document.html"
    html.write_text("<p>hello</p>", encoding="utf-8")
    output = tmp_path / "out" / "result.pdf"
    page = MagicMock()
    page.pdf.side_effect = lambda **values: Path(values["path"]).write_bytes(b"%PDF")
    context = MagicMock()
    context.new_page.return_value = page
    browser = MagicMock(version="123")
    browser.new_context.return_value = context
    chromium = MagicMock()
    chromium.launch.return_value = browser
    manager = MagicMock()
    manager.__enter__.return_value.chromium = chromium
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = MagicMock(return_value=manager)
    package = types.ModuleType("playwright")
    package.sync_api = sync_api
    with patch.dict(sys.modules, {"playwright": package, "playwright.sync_api": sync_api}):
        result = render({"schema_version": 1, "html": str(html), "output_pdf": str(output),
                         "page": {"size": "A4", "margin_mm": 10}, "warmups": 1, "iterations": 2})
    assert output.is_file()
    assert result["renderer"] == "chromium"
    assert len(result["samples_ms"]) == 2
    page.emulate_media.assert_called_once_with(media="print")
    assert page.route.call_count == 2
    assert page.pdf.call_count == 3


def test_main_rejects_unsupported_schema(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps({"schema_version": 99}))
    assert main() == 1
    assert "unsupported schema" in capsys.readouterr().err
