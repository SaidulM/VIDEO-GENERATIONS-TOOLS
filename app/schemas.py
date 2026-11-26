from pydantic import BaseModel, Field, field_validator

class DraftRequest(BaseModel):
    topic: str = Field(default="", max_length=1000)
    script: str = Field(default="", max_length=18000)
    scene_notes: str = Field(default="", max_length=6000)
    style: str = "cinematic"
    language: str = "hinglish"
    format: str = "short"
    provider: str | None = None
    model: str | None = None

    @field_validator("style")
    @classmethod
    def valid_style(cls, value):
        if value not in {"cinematic","islamic_geometry","cyberpunk","clay","3d","minimal"}:
            raise ValueError("Unknown visual style.")
        return value

    @field_validator("format")
    @classmethod
    def valid_format(cls, value):
        if value not in {"short","long"}:
            raise ValueError("Format must be short or long.")
        return value

class RenderRequest(BaseModel):
    storyboard: dict
    style: str = "cinematic"
    format: str = "short"
    voice_engine: str = "kokoro"
    voice_id: str = "hm_omega"
    voice_reference: str | None = None
    captions: bool = True
    caption_style: str = "bold"
    target_seconds: int = Field(default=45, ge=10, le=1800)
    title: str = Field(default="Short Story Speaker", max_length=120)

class SettingsRequest(BaseModel):
    provider: str
    api_key: str = Field(default="", max_length=1000)
    model: str = Field(default="", max_length=200)

class VoicePreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    engine: str = "kokoro"
    voice_id: str = "hm_omega"
    voice_reference: str | None = None

class ComfySubmitRequest(BaseModel):
    workflow: dict
    server_url: str | None = None
