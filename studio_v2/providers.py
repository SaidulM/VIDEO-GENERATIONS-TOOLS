from __future__ import annotations

from typing import Any
import requests

LLM_PROVIDERS: dict[str, dict[str, Any]] = {
    "openrouter": {
        "label": "OpenRouter · free models available",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/free",
        "key_url": "https://openrouter.ai/keys",
        "models": ["openrouter/free"],
        "free_note": "Free model IDs and daily limits vary. Filter the model list to :free models.",
    },
    "groq": {
        "label": "Groq · developer/free tier",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "key_url": "https://console.groq.com/keys",
        "models": ["llama-3.3-70b-versatile"],
        "free_note": "Free developer limits depend on the model and account.",
    },
    "gemini": {
        "label": "Google Gemini API · free tier on eligible models",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-3.8-flash",
        "key_url": "https://aistudio.google.com/apikey",
        "models": ["gemini-3.8-flash", "gemini-3.8-flash-lite"],
        "free_note": "Some models have a free tier. Free-tier data may be used to improve Google products.",
    },
    "deepseek": {
        "label": "DeepSeek · API (check current account pricing)",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "key_url": "https://platform.deepseek.com/api_keys",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "free_note": "Do not assume paid API models are free; check your account pricing.",
    },
    "openai": {
        "label": "OpenAI · paid API",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4.1-mini",
        "key_url": "https://platform.openai.com/api-keys",
        "models": ["gpt-4.1-mini", "gpt-4.1"],
        "free_note": "API usage is billed separately from ChatGPT plans.",
    },
    "cloudflare": {
        "label": "Cloudflare Workers AI · 10,000 free neurons/day",
        "base_url": "",
        "default_model": "@cf/meta/llama-3.2-1b-instruct",
        "key_url": "https://dash.cloudflare.com/",
        "models": [
            "@cf/meta/llama-3.2-1b-instruct",
            "@cf/meta/llama-3.2-3b-instruct",
            "@cf/openai/gpt-oss-20b",
        ],
        "free_note": "Free Workers plan includes 10,000 Neurons/day. Add your Cloudflare Account ID in the Base URL. Model usage consumes neurons and the allowance can run out.",
    },
    "xai": {
        "label": "xAI Grok · paid API",
        "base_url": "https://api.x.ai/v1",
        "default_model": "",
        "key_url": "https://console.x.ai/",
        "models": [],
        "free_note": "Grok API is paid. Load models from your account before use.",
    },
    "custom": {
        "label": "Custom OpenAI-compatible endpoint",
        "base_url": "",
        "default_model": "",
        "key_url": "",
        "models": [],
        "free_note": "Enter the base URL, model ID and a key from your selected provider.",
    },
}

VIDEO_SOURCES = {
    "pexels": {
        "label": "Pexels Video API · free stock footage",
        "key_url": "https://www.pexels.com/api/",
        "note": "Free stock footage, subject to Pexels API limits and terms.",
    },
    "pixabay": {
        "label": "Pixabay Video API · free stock footage",
        "key_url": "https://pixabay.com/api/docs/",
        "note": "Free stock footage; follow Pixabay API caching and usage rules.",
    },
    "motion": {
        "label": "Code-generated motion graphics · no API key",
        "key_url": "",
        "note": "Deterministic HTML/CSS/GSAP animations. No AI footage model is involved.",
    },
}

def provider_info(provider: str) -> dict[str, Any]:
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider}")
    return LLM_PROVIDERS[provider].copy()

def list_models(provider: str, api_key: str, base_url: str | None = None, free_only: bool = False) -> list[str]:
    info = provider_info(provider)
    endpoint = (base_url or info["base_url"]).rstrip("/")
    if provider in {"custom", "cloudflare"} and not endpoint:
        raise ValueError("Enter the OpenAI-compatible base URL first. For Cloudflare, include your Account ID in the URL.")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    if provider == "gemini":
        headers["x-goog-api-key"] = api_key
    if provider != "custom" and not api_key:
        raise ValueError("Enter the provider API key before loading its models.")
    if provider == "cloudflare":
        return list(info["models"])
    try:
        response = requests.get(endpoint + "/models", headers=headers, timeout=(10, 30))
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") or payload.get("models") or []
        models: list[str] = []
        for row in rows:
            mid = row.get("id") or row.get("name") or ""
            mid = str(mid).removeprefix("models/")
            if not mid:
                continue
            if free_only and provider == "openrouter":
                pricing = row.get("pricing") or {}
                free = mid.endswith(":free") or (
                    str(pricing.get("prompt", "")) in {"0", "0.0"}
                    and str(pricing.get("completion", "")) in {"0", "0.0"}
                )
                if not free:
                    continue
            models.append(mid)
        if provider == "openrouter" and free_only and "openrouter/free" not in models:
            models.insert(0, "openrouter/free")
        return sorted(set(models), key=lambda x: (x != info["default_model"], x.lower()))
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not load the model catalogue from {provider}. Check the key and endpoint. Details: {exc}") from exc

def test_text_provider(provider: str, api_key: str, model: str, base_url: str | None = None) -> str:
    if not api_key:
        raise ValueError("API key is empty.")
    if not model:
        raise ValueError("Choose a model ID.")
    from openai import OpenAI
    info = provider_info(provider)
    endpoint = (base_url or info["base_url"]).rstrip("/")
    client = OpenAI(base_url=endpoint, api_key=api_key, timeout=45, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with exactly: connection_ok"}],
        max_tokens=20,
    )
    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        raise RuntimeError("The provider accepted the request but returned an empty answer.")
    return answer[:100]

def chat_completion(provider: str, api_key: str, model: str, messages: list[dict[str, str]],
                    base_url: str | None = None, temperature: float = 0.35) -> str:
    if not api_key or not model:
        raise ValueError("An API key and model ID are required for topic-to-script generation.")
    from openai import OpenAI
    info = provider_info(provider)
    endpoint = (base_url or info["base_url"]).rstrip("/")
    client = OpenAI(base_url=endpoint, api_key=api_key, timeout=120, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=5000,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The selected model returned an empty response.")
    return str(content)
