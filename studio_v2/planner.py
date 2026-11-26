from __future__ import annotations

import json
import re
from typing import Any
from .providers import chat_completion

STYLES = {
    "cinematic": "Cinematic documentary, natural lighting, realistic licensed B-roll, elegant film titles.",
    "islamic_geometry": "Respectful Islamic visual language: mosque architecture, geometric arabesque, manuscripts, landscapes and symbolic light. Do not depict Allah, prophets or angels.",
    "cyberpunk": "Neon cyberpunk motion graphics, glowing lines, dark atmosphere and futuristic typography.",
    "hand_drawn": "Warm hand-drawn storybook, paper texture, ink outlines and simple character silhouettes.",
    "stickman": "Minimal stick-figure explainer, consistent simple characters, strong readable gestures and clean backgrounds.",
    "retro_tv": "Retro television broadcast graphics, CRT texture, scanlines and vintage typography.",
    "pixel_art": "Pixel theatre, 16-bit pixel art, chunky silhouettes and carefully limited palette.",
    "clay": "Clay-like stop-motion look, tactile handmade shapes and soft studio lighting.",
    "3d_motion": "3D-inspired motion design, dimensional typography, soft shadows and layered depth.",
    "kinetic_type": "Bold kinetic typography, high-contrast editorial layouts and precise text animation.",
}

def _sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?।؟])\s+|\n+", text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])

def _split_balanced(text: str, target_words: int = 24) -> list[str]:
    sentences = _sentences(text)
    groups: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in sentences:
        current.append(sentence)
        count += len(sentence.split())
        if count >= target_words:
            groups.append(" ".join(current))
            current, count = [], 0
    if current:
        if groups and count < 7:
            groups[-1] += " " + " ".join(current)
        else:
            groups.append(" ".join(current))
    return groups

def _safe_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:].lstrip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].lstrip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].rstrip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The selected model did not return a JSON storyboard. Try a different model or paste a full script.")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("The model response is not a storyboard object.")
    return value

def create_storyboard(topic: str, script: str, scene_notes: str, style: str,
                      language: str, aspect_ratio: str, duration_seconds: int,
                      provider: str | None = None, api_key: str | None = None,
                      model: str | None = None, base_url: str | None = None) -> dict[str, Any]:
    style_prompt = STYLES.get(style)
    if not style_prompt:
        raise ValueError("Choose a supported visual style.")
    if aspect_ratio not in {"9:16", "16:9"}:
        raise ValueError("Video ratio must be 9:16 or 16:9.")
    if duration_seconds < 10 or duration_seconds > 600:
        raise ValueError("Duration must be between 10 and 600 seconds.")
    if not script.strip() and not topic.strip():
        raise ValueError("Enter a topic or paste a script.")

    if script.strip():
        chunks = _split_balanced(script)
        if not chunks:
            raise ValueError("The supplied script is empty.")
        scenes = []
        notes = [x.strip() for x in scene_notes.splitlines() if x.strip()]
        for idx, narration in enumerate(chunks):
            hint = notes[idx] if idx < len(notes) else ""
            query = " ".join(re.findall(r"[A-Za-z0-9\u0980-\u09FF']+", hint or narration)[:8])
            scenes.append({
                "id": f"scene-{idx+1:02d}",
                "narration": narration,
                "on_screen_text": (narration.split(".")[0] if narration else "")[:70],
                "visual_prompt": hint or f"{style_prompt} Visual idea based on: {narration[:220]}",
                "stock_query": query or topic or "cinematic atmosphere",
                "duration_seconds": 5,
                "stock_results": [],
                "stock_file": None,
                "stock_credit": None,
            })
        storyboard = {
            "title": topic.strip() or "Short Story Speaker",
            "hook": scenes[0]["on_screen_text"],
            "script": script.strip(),
            "language": language,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "target_duration_seconds": duration_seconds,
            "scenes": scenes,
            "generation_mode": "script-preserving",
        }
        if provider and api_key and model:
            try:
                prompt = {
                    "role": "user",
                    "content": (
                        "You are a visual director for a respectful Islamic/motivational YouTube Shorts channel. "
                        "Return only JSON: {scenes:[{id,visual_prompt,stock_query,on_screen_text}]}. "
                        "Use the supplied scene IDs exactly. Do not rewrite, add, remove, translate, shorten or quote narration. "
                        "Avoid depicting Allah, prophets or angels. Make the visuals varied, specific and filmable. "
                        f"Style: {style_prompt}\nScene source data:\n"
                        + json.dumps([{"id": s["id"], "narration": s["narration"]} for s in scenes], ensure_ascii=False)
                    ),
                }
                raw = chat_completion(provider, api_key, model, [prompt], base_url)
                refined = _safe_json(raw).get("scenes", [])
                by_id = {str(x.get("id")): x for x in refined if isinstance(x, dict)}
                for scene in scenes:
                    patch = by_id.get(scene["id"], {})
                    for key in ("visual_prompt", "stock_query", "on_screen_text"):
                        if patch.get(key):
                            scene[key] = str(patch[key])[:1200]
                storyboard["generation_mode"] = f"{provider}:{model}"
            except Exception as exc:
                storyboard["planner_note"] = f"Visual prompt refinement was skipped: {exc}"
        return storyboard

    if not provider or not api_key or not model:
        raise ValueError("For topic-only creation, choose an LLM provider, enter its API key and select a model. Pasting a script works without an LLM.")
    prompt = f"""
You are a professional short-form documentary director and scriptwriter for Short Story Speaker, a Hindi/Hinglish Islamic and motivational Shorts channel.
Create an original {duration_seconds}-second video plan.
Topic: {topic}
Language: {language}
Aspect ratio: {aspect_ratio}
Visual style: {style} — {style_prompt}
Optional scene directions: {scene_notes or "None"}.

Return ONLY valid JSON, with this schema:
{{
 "title":"short title",
 "hook":"first on-screen hook",
 "script":"complete narration",
 "scenes":[
  {{"id":"scene-01","narration":"exact spoken lines for this scene","on_screen_text":"short readable text","visual_prompt":"specific shot direction","stock_query":"short stock-footage search phrase","duration_seconds":5}}
 ]
}}
Rules: use 4–9 scenes; total spoken script should fit the requested duration; narration must be in the chosen language and sound natural; start with a strong 1–2 second hook; end with a concise takeaway. Do not invent Qur'an or Hadith quotes, references, rulings or historical facts. If a religious claim has no supplied source, phrase it as general reflection, not as an attributed quotation. Do not depict Allah, prophets or angels. Visual prompts should use architecture, landscapes, prayer spaces, books without fabricated scripture, hands, everyday life and symbolic light. Keep stock queries short and search-friendly. Do not include markdown fences.
"""
    raw = chat_completion(provider, api_key, model, [{"role": "user", "content": prompt}], base_url, 0.55)
    data = _safe_json(raw)
    scenes_in = data.get("scenes")
    if not isinstance(scenes_in, list) or not scenes_in:
        raise ValueError("The model returned no scenes. Try another model or a more specific topic.")
    scenes = []
    for idx, row in enumerate(scenes_in[:12]):
        if not isinstance(row, dict) or not str(row.get("narration", "")).strip():
            continue
        scenes.append({
            "id": str(row.get("id") or f"scene-{idx+1:02d}"),
            "narration": str(row["narration"]).strip(),
            "on_screen_text": str(row.get("on_screen_text") or "")[:90],
            "visual_prompt": str(row.get("visual_prompt") or "")[:1200],
            "stock_query": str(row.get("stock_query") or topic)[:160],
            "duration_seconds": max(2, min(20, int(row.get("duration_seconds") or 5))),
            "stock_results": [],
            "stock_file": None,
            "stock_credit": None,
        })
    if not scenes:
        raise ValueError("The model returned invalid scene narration.")
    script_result = str(data.get("script") or " ".join(s["narration"] for s in scenes))
    return {
        "title": str(data.get("title") or topic)[:120],
        "hook": str(data.get("hook") or scenes[0]["on_screen_text"])[:120],
        "script": script_result,
        "language": language,
        "style": style,
        "aspect_ratio": aspect_ratio,
        "target_duration_seconds": duration_seconds,
        "scenes": scenes,
        "generation_mode": f"{provider}:{model}",
    }
