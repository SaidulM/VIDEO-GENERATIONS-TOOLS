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
    voice_engine: str = "none"
    voice_id: str = "chatterbox-v3"
    voice_reference: str | None = None
    exaggeration: float = Field(default=0.5, ge=0.25, le=2.0)
    cfg_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    temperature: float = Field(default=0.8, ge=0.05, le=2.0)
    visual_engine: str = "motion_cards"
    captions: bool = True
    caption_style: str = "bold"
    target_seconds: int = Field(default=45, ge=10, le=1800)
    title: str = Field(default="Short Story Speaker", max_length=120)

    @field_validator("visual_engine")
    @classmethod
    def valid_visual_engine(cls, value):
        if value not in {"motion_cards", "animatediff"}:
            raise ValueError("Visual engine must be motion_cards or animatediff.")
        return value

class SettingsRequest(BaseModel):
    provider: str
    api_key: str = Field(default="", max_length=1000)
    model: str = Field(default="", max_length=200)

class VoicePreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    engine: str = "chatterbox"
    voice_id: str = "chatterbox-v3"
    voice_reference: str | None = None
    exaggeration: float = Field(default=0.5, ge=0.25, le=2.0)
    cfg_weight: float = Field(default=0.5, ge=0.0, le=1.0)
    temperature: float = Field(default=0.8, ge=0.05, le=2.0)

class ComfySubmitRequest(BaseModel):
    workflow: dict
    server_url: str | None = None
