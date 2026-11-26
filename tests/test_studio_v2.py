from __future__ import annotations

from pathlib import Path
import pytest

from studio_v2.planner import STYLES, create_storyboard
from studio_v2.providers import LLM_PROVIDERS
from studio_v2.composer import build_project
from studio_v2.stock import download_stock, search_stock


def test_script_mode_does_not_require_an_api_key():
    supplied = "Assalamu alaikum. Aaj hum sabr ke ek aham sabaq par baat karenge. Allah par bharosa rakhein."
    data = create_storyboard(
        topic="Sabr", script=supplied, scene_notes="", style="islamic_geometry",
        language="hinglish", aspect_ratio="9:16", duration_seconds=45,
    )
    assert data["script"] == supplied
    assert data["scenes"]
    assert data["generation_mode"] == "script-preserving"


def test_topic_only_requires_model_credentials():
    with pytest.raises(ValueError, match="LLM provider"):
        create_storyboard(
            topic="Jumuah reminder", script="", scene_notes="", style="cinematic",
            language="hinglish", aspect_ratio="9:16", duration_seconds=45,
        )


def test_style_gallery_and_provider_catalog_are_not_empty():
    assert len(STYLES) >= 10
    assert {"openrouter", "groq", "gemini", "cloudflare", "xai"} <= set(LLM_PROVIDERS)
    assert LLM_PROVIDERS["openrouter"]["default_model"] == "openrouter/free"
    assert "free tier" in LLM_PROVIDERS["cloudflare"]["free_note"].lower() or "free" in LLM_PROVIDERS["cloudflare"]["free_note"].lower()


def test_cloudflare_model_list_is_explicit_and_needs_account_base_url():
    from studio_v2.providers import list_models
    assert "@cf/meta/llama-3.2-1b-instruct" in LLM_PROVIDERS["cloudflare"]["models"]
    with pytest.raises(ValueError, match="base URL"):
        list_models("cloudflare", "test-token", "")


def test_hyperframes_composition_contains_real_timeline_and_caption(tmp_path):
    storyboard = {
        "title": "Sabr",
        "hook": "Sabr se himmat milti hai",
        "scenes": [{
            "id": "scene-01",
            "narration": "Assalamu alaikum. Sabr rakhein.",
            "on_screen_text": "Sabr rakhein",
            "visual_prompt": "Sunrise over a quiet mosque courtyard",
            "stock_file": None,
            "stock_credit": None,
        }],
    }
    project = build_project(
        tmp_path, storyboard, "islamic_geometry", "9:16", 30,
        None, None, [{"start": 0.0, "end": 2.0, "text": "Sabr rakhein"}],
    )
    html = (Path(project["project_dir"]) / "index.html").read_text(encoding="utf-8")
    assert 'data-composition-id="root"' in html
    assert 'window.__timelines["root"]' in html
    assert 'data-track-index="5"' in html
    assert "Sabr rakhein" in html
    assert Path(project["srt"]).exists()
    assert Path(project["timestamps"]).exists()


def test_stock_downloader_rejects_non_stock_domains(tmp_path):
    with pytest.raises(ValueError, match="approved"):
        download_stock({"download_url": "https://example.org/clip.mp4", "id": "bad"}, tmp_path)


def test_model_catalog_marks_paid_api_separately():
    assert "paid API" in LLM_PROVIDERS["openai"]["label"]
    assert "paid API" in LLM_PROVIDERS["xai"]["label"]
    assert "free tier" in LLM_PROVIDERS["groq"]["label"].lower()
