from __future__ import annotations
from .config import env, put_local_setting

PROVIDERS = {
    "openrouter": {"label":"OpenRouter","base_url":"https://openrouter.ai/api/v1","key_env":"OPENROUTER_API_KEY","default_model":"openrouter/free"},
    "groq": {"label":"Groq","base_url":"https://api.groq.com/openai/v1","key_env":"GROQ_API_KEY","default_model":"llama-3.3-70b-versatile"},
    "deepseek": {"label":"DeepSeek","base_url":"https://api.deepseek.com","key_env":"DEEPSEEK_API_KEY","default_model":"deepseek-chat"},
    "gemini": {"label":"Google Gemini","base_url":"https://generativelanguage.googleapis.com/v1beta/openai/","key_env":"GEMINI_API_KEY","default_model":"gemini-2.5-flash"},
    "openai": {"label":"OpenAI","base_url":"https://api.openai.com/v1","key_env":"OPENAI_API_KEY","default_model":"gpt-4.1-mini"},
    "ollama": {"label":"Ollama (local)","base_url":"http://localhost:11434/v1","key_env":"OLLAMA_API_KEY","default_model":"qwen2.5:3b"},
}


def current_provider():
    value = env("DEFAULT_LLM_PROVIDER", "openrouter").lower()
    return value if value in PROVIDERS else "openrouter"


def public_provider_list():
    selected = current_provider()
    selected_model = env("DEFAULT_LLM_MODEL", PROVIDERS[selected]["default_model"])
    return [{
        "id": key, "label": item["label"], "base_url": item["base_url"],
        "default_model": item["default_model"], "configured": bool(env(item["key_env"])),
        "selected": key == selected,
        "model": selected_model if key == selected else item["default_model"],
    } for key, item in PROVIDERS.items()]


def provider_credentials(provider: str, model_override: str | None = None):
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider.")
    item = PROVIDERS[provider]
    api_key = env(item["key_env"])
    if provider == "ollama" and not api_key:
        api_key = "ollama"
    if not api_key:
        raise ValueError(f"{item['label']} API key is not configured. Open Settings and save it.")
    model = (model_override or env("DEFAULT_LLM_MODEL") or item["default_model"]).strip()
    if not model:
        raise ValueError("A model ID is required.")
    return item["base_url"], api_key, model


def save_provider_settings(provider: str, api_key: str, model: str):
    if provider not in PROVIDERS:
        raise ValueError("Unsupported provider.")
    item = PROVIDERS[provider]
    if provider != "ollama":
        if not api_key.strip():
            raise ValueError("An API key is required for this hosted provider.")
        put_local_setting(item["key_env"], api_key.strip())
    put_local_setting("DEFAULT_LLM_PROVIDER", provider)
    put_local_setting("DEFAULT_LLM_MODEL", model.strip() or item["default_model"])
