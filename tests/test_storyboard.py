from pydantic import ValidationError
import pytest

from app.storyboard import split_sentences, template_storyboard
from app.schemas import RenderRequest
from app.ai_video import STYLE_PROMPTS, gpu_status
from app.tts import voice_catalog


def test_split_sentences():
    assert split_sentences("First sentence. Second sentence!") == ["First sentence.", "Second sentence!"]


def test_template_storyboard_keeps_script():
    data = template_storyboard("A topic", "This is the supplied script. Do not change it.", "", "cinematic", "hinglish", "short")
    assert data["generation_mode"] == "template"
    assert data["scenes"][0]["narration"] == "This is the supplied script."
    assert data["format"] == "short"


def test_visual_styles_are_available():
    assert {"cinematic", "islamic_geometry", "cyberpunk", "clay", "3d", "minimal"} <= set(STYLE_PROMPTS)


def test_render_schema_rejects_unknown_engine():
    storyboard = {"title": "test", "scenes": [{"narration": "text"}]}
    with pytest.raises(ValidationError):
        RenderRequest(storyboard=storyboard, visual_engine="not-a-real-engine")


def test_voice_catalog_has_chatterbox_not_kokoro():
    catalog = voice_catalog()
    assert catalog[0]["engine"] == "chatterbox"
    assert all(row["engine"] != "kokoro" for row in catalog)


def test_gpu_status_is_explicit():
    status = gpu_status()
    assert "available" in status and isinstance(status["available"], bool)
