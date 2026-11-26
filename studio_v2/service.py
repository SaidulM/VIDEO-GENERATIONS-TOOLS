from __future__ import annotations

from pathlib import Path
import json
import uuid

from .planner import create_storyboard
from .stock import search_stock, download_stock
from .voice import synthesize_voice
from .captions import transcribe_or_estimate
from .composer import build_project, render_project

class StudioJob:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def new_job_dir(self) -> Path:
        path = self.base_dir / uuid.uuid4().hex[:10]
        path.mkdir(parents=True, exist_ok=True)
        return path

    def draft(self, **kwargs):
        return create_storyboard(**kwargs)

    def search_scene_footage(self, storyboard: dict, provider: str, api_key: str):
        for scene in storyboard.get("scenes", []):
            query = scene.get("stock_query") or scene.get("visual_prompt") or scene.get("narration")
            results = search_stock(provider, str(query), api_key, storyboard["aspect_ratio"])
            scene["stock_results"] = results
            if results and not scene.get("selected_stock_id"):
                scene["selected_stock_id"] = results[0]["id"]
        return storyboard

    def download_selected_footage(self, storyboard: dict, job_dir: str | Path):
        folder = Path(job_dir) / "stock"
        for scene in storyboard.get("scenes", []):
            selected = scene.get("selected_stock_id")
            result = next((x for x in scene.get("stock_results", []) if x.get("id") == selected), None)
            if result:
                scene["stock_file"] = download_stock(result, folder)
                scene["stock_credit"] = {
                    "source": result.get("source"),
                    "creator": result.get("creator"),
                    "url": result.get("credit_url"),
                }
        return storyboard

    def make_voice(self, text: str, engine: str, output_path: str | Path, **settings):
        return synthesize_voice(text, engine, output_path, **settings)

    def render(self, storyboard: dict, job_dir: str | Path, style: str, aspect_ratio: str,
               duration_seconds: int, voice_path: str | None, music_path: str | None,
               caption_style: str = "bold", whisper_timing: bool = True, progress=None):
        job_dir = Path(job_dir)
        job_dir.mkdir(parents=True, exist_ok=True)
        narration = storyboard.get("script") or " ".join(s.get("narration", "") for s in storyboard.get("scenes", []))
        captions, _, caption_note = transcribe_or_estimate(voice_path, narration, whisper_timing)
        project = build_project(
            job_dir, storyboard, style, aspect_ratio, duration_seconds,
            voice_path, music_path, captions, caption_style,
        )
        output = job_dir / "short-story.mp4"
        video = render_project(project["project_dir"], output, progress)
        manifest = {
            "title": storyboard.get("title"),
            "format": aspect_ratio,
            "duration_seconds": round(project["duration"], 3),
            "renderer": "HyperFrames CLI",
            "visual_pipeline": "Pexels/Pixabay stock footage and/or HTML/CSS/GSAP motion graphics",
            "caption_timing": caption_note,
            "scene_credits": [
                s.get("stock_credit") for s in storyboard.get("scenes", [])
                if s.get("stock_credit")
            ],
            "ai_generated_video": False,
            "note": "This mode edits free stock footage and code-generated motion graphics; it does not claim to generate photorealistic AI video clips.",
        }
        (job_dir / "render_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {
            "video": str(video),
            "srt": str(job_dir / "captions.srt"),
            "timestamps": str(job_dir / "timestamps.json"),
            "storyboard": str(job_dir / "storyboard.json"),
            "manifest": str(job_dir / "render_manifest.json"),
            "duration": round(project["duration"], 3),
            "caption_note": caption_note,
        }
