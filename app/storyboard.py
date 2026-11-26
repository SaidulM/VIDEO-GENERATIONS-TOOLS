from __future__ import annotations
import json
import re
from openai import OpenAI
from .providers import provider_credentials
from .skills import skill_context

ISLAMIC_RULES = """
For Islamic educational content, never invent Qur'an quotations, Hadith wording,
verse numbers, narrator chains, scholarly rulings or historical claims. Preserve
references supplied by the user and mark unverified claims in review_notes.
Do not depict Allah, prophets or angels. Prefer architecture, landscapes,
books, symbolic lighting, geometric art and licensed calligraphy. Use suspense
hooks, clear story progression and conversational Roman Hinglish. Do not add
Arabic scripture unless the user supplied exact text and asked for it.
"""

def split_sentences(text):
    parts = re.split(r"(?<=[.!?।])\s+|\n+", text.strip())
    return [item.strip() for item in parts if item.strip()]

def template_storyboard(topic, script, scene_notes, style, language, project_format):
    source = script.strip() or topic.strip()
    if not source:
        raise ValueError("Enter a topic or paste a script first.")
    sentences = split_sentences(source) or [source]
    if len(sentences) == 1 and len(source.split()) > 35:
        words = source.split()
        chunk = max(12, min(28, len(words)//4 or 12))
        sentences = [" ".join(words[i:i+chunk]) for i in range(0,len(words),chunk)]
    notes = [line.strip("-• \t") for line in scene_notes.splitlines() if line.strip()]
    max_scenes = 8 if project_format == "short" else 24
    scenes = []
    for index, line in enumerate(sentences[:max_scenes]):
        role = "hook" if index == 0 else ("closing" if index == min(len(sentences),max_scenes)-1 else "story")
        scenes.append({
            "id":f"scene-{index+1:02d}","role":role,"narration":line,
            "visual_prompt":notes[index] if index < len(notes) else f"Symbolic {style} visual related to: {line[:160]}. No religious figures.",
            "on_screen_text":line[:90],"duration_hint":5 if project_format == "short" else 15
        })
    return {"title":topic.strip()[:100] or "Short Story Speaker","hook":scenes[0]["narration"][:180],
            "language":language,"format":project_format,"style":style,"scenes":scenes,
            "full_narration":"\n".join(scene["narration"] for scene in scenes),
            "review_notes":["Template storyboard: no LLM was called. Verify all claims and references before publishing."],
            "generation_mode":"template"}

def create_storyboard(topic, script, scene_notes, style, language, project_format, provider, model):
    if not (topic.strip() or script.strip()):
        raise ValueError("Enter a topic or paste a script first.")
    provider_name = provider or "openrouter"
    try:
        base_url, api_key, model_id = provider_credentials(provider_name, model)
    except ValueError:
        return template_storyboard(topic,script,scene_notes,style,language,project_format)
    client = OpenAI(base_url=base_url,api_key=api_key,timeout=90,max_retries=1)
    system = f"""
Create an editable storyboard JSON for a YouTube video.
{ISLAMIC_RULES}
Return ONLY JSON with keys title, hook, language, format, style, scenes,
full_narration, review_notes. Each scene requires id, role, narration,
visual_prompt, on_screen_text, duration_hint. Make 5-8 scenes for Shorts and
8-24 for a long-form draft. If a script is supplied, preserve its meaning and
do not add unsupported claims. Style: {style}. Format: {project_format}.
Language: {language}. Scene notes: {scene_notes or "None supplied; create a coherent sequence."}
Installed skills:
{skill_context()}
"""
    user = f"TOPIC:\n{topic}\n\nSCRIPT:\n{script}\n\nCreate the scene plan from the supplied source."
    response = client.chat.completions.create(
        model=model_id, temperature=0.4, response_format={"type":"json_object"},
        messages=[{"role":"system","content":system},{"role":"user","content":user}]
    )
    raw = response.choices[0].message.content or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The selected LLM returned invalid JSON. Try again or select another model.") from exc
    scenes = data.get("scenes")
    if not isinstance(scenes,list) or not scenes:
        raise RuntimeError("The LLM response contained no scenes.")
    clean = []
    for index, scene in enumerate(scenes[:(8 if project_format=="short" else 24)]):
        if not isinstance(scene,dict):
            continue
        narration = str(scene.get("narration","")).strip()
        if narration:
            clean.append({
                "id":str(scene.get("id") or f"scene-{index+1:02d}")[:50],
                "role":str(scene.get("role") or "story")[:40],
                "narration":narration[:1800],
                "visual_prompt":str(scene.get("visual_prompt") or "Symbolic cinematic scene; no religious figures.")[:1000],
                "on_screen_text":str(scene.get("on_screen_text") or narration[:90])[:180],
                "duration_hint":float(scene.get("duration_hint") or 5)
            })
    if not clean:
        raise RuntimeError("The LLM response contained no usable narration.")
    data["scenes"] = clean
    data["full_narration"] = "\n".join(item["narration"] for item in clean)
    data["generation_mode"] = f"llm:{provider_name}/{model_id}"
    data.setdefault("review_notes",[])
    data["review_notes"].append("Verify all Islamic references and factual claims against primary sources before publishing.")
    return data
