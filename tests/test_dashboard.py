"""Lightweight checks for the self-contained static dashboard.

These tests never run a browser. They assert the dashboard HTML/JS/CSS stay
backend-free and relative-linked, declare the controls the spec requires, and
handle missing/optional images without producing broken-image noise.
"""
from pathlib import Path

ROOT = Path(__file__).parents[1]
DASH = ROOT / "src" / "renderer_benchmark_lab" / "dashboard"

HTML = (DASH / "index.html").read_text(encoding="utf-8")
JS = (DASH / "app.js").read_text(encoding="utf-8")
CSS = (DASH / "style.css").read_text(encoding="utf-8")


def test_dashboard_assets_are_self_contained():
    # No remote network assets may appear in the dashboard sources.
    for name, content in (("index.html", HTML), ("app.js", JS), ("style.css", CSS)):
        assert "http://" not in content, f"{name} references http://"
        assert "https://" not in content, f"{name} references https://"


def test_dashboard_uses_relative_data_paths():
    # index.html loads the run index; app.js loads each run bundle relatively.
    assert "data/index.js" in HTML
    assert "data/runs/" in JS


def test_dashboard_declares_required_controls():
    for control in ("run", "candidate", "page", "cases", "pages"):
        assert f'id="{control}"' in HTML, f"missing control #{control}"


def test_dashboard_handles_missing_images_without_broken_noise():
    # Product images mark the wrapper missing instead of showing a broken image.
    assert "classList.add('missing')" in JS
    # Every product image injects an onerror handler.
    assert "onerror=" in JS


def test_dashboard_overlay_is_optional():
    # The overlay figure removes itself entirely when its image is missing.
    assert "closest('figure').remove()" in JS
    assert "overlay-" in JS


def test_dashboard_retains_timing_scope_and_critical_failures():
    assert "timing_scope" in JS
    assert "critical_failures" in JS
