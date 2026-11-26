from __future__ import annotations

from pathlib import Path
import html
import json
import shutil
import uuid

import ipywidgets as W
from IPython.display import display, HTML, Audio, Video, FileLink, clear_output

from .providers import LLM_PROVIDERS, VIDEO_SOURCES, provider_info, list_models, test_text_provider
from .planner import STYLES
from .service import StudioJob
from .voice import GEMINI_VOICES

DASHBOARD_CSS = """
<style>
.ss-wrap{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#e8edf7;background:#0c1220;border:1px solid #27334b;border-radius:22px;padding:22px;margin:8px 0}
.ss-header{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:6px 4px 20px;border-bottom:1px solid #28334a}
.ss-brand{font-size:24px;font-weight:850;letter-spacing:-.04em;color:#fff}
.ss-brand span{color:#8fc7ff}
.ss-sub{font-size:12px;color:#91a1bb;letter-spacing:.16em;text-transform:uppercase;margin-bottom:8px}
.ss-pill{border:1px solid #31577b;color:#a8d6ff;border-radius:999px;padding:7px 11px;font-size:11px;font-weight:700}
.ss-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:16px 0}
.ss-stat{background:#141e30;border:1px solid #2a3850;border-radius:13px;padding:13px}
.ss-stat b{font-size:17px;color:#fff;display:block}
.ss-stat small{color:#94a4bd;font-size:11px}
.ss-note{background:#142337;border-left:3px solid #63b9e8;border-radius:8px;padding:11px 13px;color:#c2d8eb;font-size:12px;line-height:1.5;margin:10px 0}
.ss-warn{background:#2a2116;border-left-color:#d9a34b;color:#ecd7b6}
.ss-section{font-weight:800;color:#fff;font-size:17px;margin:4px 0 8px}
.ss-muted{font-size:12px;color:#91a1bb;line-height:1.55}
.ss-footer{font-size:11px;color:#72829c;border-top:1px solid #28334a;margin-top:18px;padding-top:14px}
</style>
"""

class ColabStudio:
    def __init__(self, work_dir: str | Path, export_dir: str | Path | None = None):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir = Path(export_dir) if export_dir else self.work_dir / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.engine = StudioJob(self.work_dir / "jobs")
        self.state = {"storyboard": None, "job_dir": None, "voice_path": None, "music_path": None, "result": None}
        self._create_widgets()
        self._wire_events()

    def _create_widgets(self):
        self.provider = W.Dropdown(
            options=[(v["label"], k) for k, v in LLM_PROVIDERS.items()],
            value="openrouter", description="LLM Provider",
            layout=W.Layout(width="100%"),
        )
        self.llm_key = W.Password(description="API Key", placeholder="Key stays in this Colab session", layout=W.Layout(width="100%"))
        self.model = W.Dropdown(options=[("openrouter/free", "openrouter/free")], value="openrouter/free",
                                description="Model", layout=W.Layout(width="100%"))
        self.custom_model = W.Text(description="Exact model ID (optional override)", placeholder="Paste a model ID if it is not in the list", layout=W.Layout(width="100%"))
        self.free_only = W.Checkbox(value=True, description="Free models only (OpenRouter)")
        self.custom_url = W.Text(description="Base URL", placeholder="Custom endpoint or Cloudflare Account ID URL", layout=W.Layout(width="100%"))
        self.load_models_btn = W.Button(description="Load models + test key", icon="plug", button_style="info")
        self.provider_status = W.HTML(value='<span style="color:#8294ae">API key not tested. Pasted scripts do not need an LLM.</span>')

        self.topic = W.Text(description="Topic", placeholder="Example: 3 powerful lessons from Jumuah", layout=W.Layout(width="100%"))
        self.script = W.Textarea(description="Script", placeholder="Paste your complete Roman Hinglish / Hindi / Bengali script here. This text is preserved as the narration.", layout=W.Layout(width="100%", height="170px"))
        self.scene_notes = W.Textarea(description="Scene notes", placeholder="Optional: Scene 1 — dawn at a quiet mosque courtyard\nScene 2 — close-up of prayer beads and a Quran stand", layout=W.Layout(width="100%", height="80px"))
        self.language = W.Dropdown(options=[("Roman Hinglish","hinglish"),("Hindi","hindi"),("Bengali","bengali"),("English","english")], value="hinglish", description="Language")
        self.aspect = W.ToggleButtons(options=[("Shorts · 9:16","9:16"),("Long · 16:9","16:9")], value="9:16", description="Format")
        self.style = W.Dropdown(options=[(v,k) for k,v in [
            ("Cinematic documentary","cinematic"),
            ("Islamic geometric","islamic_geometry"),
            ("Cyberpunk neon","cyberpunk"),
            ("Hand-drawn storybook","hand_drawn"),
            ("Stickman explainer","stickman"),
            ("Retro TV / CRT","retro_tv"),
            ("Pixel theatre","pixel_art"),
            ("Clay-like motion","clay"),
            ("3D-inspired motion","3d_motion"),
            ("Kinetic typography","kinetic_type"),
        ]], value="cinematic", description="Visual style", layout=W.Layout(width="100%"))
        self.duration = W.IntSlider(value=45, min=15, max=180, step=5, description="Target sec",
                                    continuous_update=False, style={"description_width":"initial"}, layout=W.Layout(width="100%"))
        self.plan_btn = W.Button(description="Create scene plan", button_style="primary", icon="magic")
        self.plan_status = W.HTML(value='<span style="color:#91a1bb">Paste a script for keyless scene splitting, or configure a text model for topic-to-script.</span>')

        self.stock_provider = W.Dropdown(options=[
            ("Pexels Video API","pexels"),
            ("Pixabay Video API","pixabay"),
            ("Motion graphics only","motion"),
        ], value="motion", description="Footage source", layout=W.Layout(width="100%"))
        self.stock_key = W.Password(description="Stock API Key", placeholder="Pexels or Pixabay key", layout=W.Layout(width="100%"))
        self.search_stock_btn = W.Button(description="Search B-roll for scenes", icon="search")
        self.prepare_stock_btn = W.Button(description="Download selected clips", icon="download")
        self.stock_status = W.HTML(value='<span style="color:#91a1bb">Use motion graphics without an API key, or add a free Pexels/Pixabay key for real footage.</span>')
        self.scene_editor = W.VBox([])
        self.scene_widgets = []

        self.voice_engine = W.Dropdown(options=[
            ("Gemini 3.8 Flash TTS · hosted free tier","gemini"),
            ("Chatterbox V3 · experimental open-source model on Colab GPU","chatterbox"),
            ("No narration · captions only","none"),
        ], value="gemini", description="Voice engine", layout=W.Layout(width="100%"))
        self.voice_key = W.Password(description="Gemini API Key", placeholder="Google AI Studio API key", layout=W.Layout(width="100%"))
        self.voice_name = W.Dropdown(options=GEMINI_VOICES, value="Kore", description="Voice", layout=W.Layout(width="100%"))
        self.voice_style = W.Text(value="Warm, expressive, natural Hindi/Hinglish documentary narrator. Clear diction, moderate pace, emotional but restrained.", description="Delivery", layout=W.Layout(width="100%"))
        self.voice_file = W.FileUpload(accept=".wav,.mp3,.m4a,.flac,.ogg,audio/*", multiple=False, description="Upload your voice sample")
        self.voice_consent = W.Checkbox(value=False, description="This is my voice or I have permission; no deceptive impersonation.")
        self.voice_exaggeration = W.FloatSlider(value=0.5, min=0.25, max=2.0, step=0.05, description="Expression", continuous_update=False)
        self.voice_cfg = W.FloatSlider(value=0.5, min=0.0, max=1.0, step=0.05, description="Guidance", continuous_update=False)
        self.preview_voice_btn = W.Button(description="Generate voice preview", icon="play", button_style="info")
        self.voice_status = W.HTML(value='<span style="color:#91a1bb">Preview a short sample before generating the full narration.</span>')
        self.voice_output = W.Output()

        self.music_file = W.FileUpload(accept=".mp3,.wav,.m4a,.ogg,audio/*", multiple=False, description="Optional background music")
        self.caption_style = W.Dropdown(options=[("Bold subtitle box","bold"),("Gold highlight","gold"),("Minimal subtitle","minimal")], value="bold", description="Caption style")
        self.whisper_timing = W.Checkbox(value=False, description="Use Whisper audio timing for captions (first render downloads tiny model)")
        self.render_btn = W.Button(description="Render final video", icon="film", button_style="success", disabled=True)
        self.render_status = W.HTML(value='<span style="color:#91a1bb">Create a scene plan first.</span>')
        self.render_output = W.Output()
        self.output_links = W.Output()

        self.tabs = W.Tab()
        self.tabs.children = [
            W.VBox([
                W.HTML('<div class="ss-section">01 · Your story</div>'),
                self.topic, self.script, self.scene_notes,
                W.HBox([self.language, self.aspect]),
                self.style, self.duration, self.plan_btn, self.plan_status,
                W.HTML('<div class="ss-note">Paste script: split into scenes without changing your narration. Topic only: an LLM API key and model are required to draft the script.</div>'),
            ], layout=W.Layout(gap="8px")),
            W.VBox([
                W.HTML('<div class="ss-section">02 · Scene board and footage</div>'),
                self.scene_editor,
                self.stock_provider, self.stock_key,
                W.HBox([self.search_stock_btn, self.prepare_stock_btn]),
                self.stock_status,
                W.HTML('<div class="ss-note">Pexels/Pixabay return licensed stock clips, not AI-generated video. <a href="https://www.pexels.com" target="_blank">Pexels</a> · <a href="https://pixabay.com" target="_blank">Pixabay</a>. Keep source/creator credits in the manifest. API quotas and caching rules apply.</div>'),
            ], layout=W.Layout(gap="8px")),
            W.VBox([
                W.HTML('<div class="ss-section">03 · Voice studio</div>'),
                self.voice_engine, self.voice_name, self.voice_key, self.voice_style,
                self.voice_file, self.voice_consent, self.voice_exaggeration, self.voice_cfg,
                self.preview_voice_btn, self.voice_status, self.voice_output,
                W.HTML('<div class="ss-note ss-warn">Gemini TTS is a hosted free-tier option, not an open-source model. Its free-tier content may be used by Google to improve products. Chatterbox is an experimental open-source research option; its upstream is retired/no longer maintained. Use only your own/authorized sample and a Colab GPU.</div>'),
            ], layout=W.Layout(gap="8px")),
            W.VBox([
                W.HTML('<div class="ss-section">04 · Export</div>'),
                self.music_file, self.caption_style, self.whisper_timing,
                self.render_btn, self.render_status, self.render_output, self.output_links,
            ], layout=W.Layout(gap="8px")),
            W.VBox([
                W.HTML('<div class="ss-section">05 · API connections</div>'),
                self.provider, self.llm_key, self.model, self.custom_model, self.free_only, self.custom_url,
                self.load_models_btn, self.provider_status,
                W.HTML('<div class="ss-note">Cloudflare Free plan includes 10,000 Neurons/day; set the Base URL with your Account ID. Grok/xAI and OpenAI APIs are paid. API keys stay in notebook memory only and are never written to GitHub files. No automatic provider/model switching is performed.</div>'),
                W.HTML('<div class="ss-muted">Key links: OpenRouter · Groq · Gemini · DeepSeek · Pexels · Pixabay. Free models and API quotas can change.</div>'),
            ], layout=W.Layout(gap="8px")),
        ]
        for i, title in enumerate(["Create","Scenes","Voice","Export","API & Models"]):
            self.tabs.set_title(i, title)

    def _wire_events(self):
        self.provider.observe(self._provider_changed, names="value")
        self.load_models_btn.on_click(self._on_load_models)
        self.plan_btn.on_click(self._on_plan)
        self.search_stock_btn.on_click(self._on_search_stock)
        self.prepare_stock_btn.on_click(self._on_prepare_stock)
        self.voice_engine.observe(self._voice_engine_changed, names="value")
        self.preview_voice_btn.on_click(self._on_preview_voice)
        self.render_btn.on_click(self._on_render)
        self._provider_changed({"new": self.provider.value})
        self._voice_engine_changed({"new": self.voice_engine.value})

    def _provider_changed(self, change):
        key = change["new"]
        info = provider_info(key)
        options = info["models"] or [("Manual model ID", "")]
        self.model.options = options
        self.model.value = info["default_model"] or (info["models"][0] if info["models"] else "")
        self.custom_model.value = ""
        self.custom_url.layout.display = "block" if key in {"custom", "cloudflare"} else "none"
        if key == "cloudflare":
            self.custom_url.placeholder = "https://api.cloudflare.com/client/v4/accounts/YOUR_ACCOUNT_ID/ai/v1"
        else:
            self.custom_url.placeholder = "Custom OpenAI-compatible base URL"
        self.free_only.layout.display = "block" if key == "openrouter" else "none"
        self.provider_status.value = '<span style="color:#91a1bb">' + html.escape(info["free_note"]) + "</span>"

    def _voice_engine_changed(self, change):
        engine = change["new"]
        gemini = engine == "gemini"
        chatterbox = engine == "chatterbox"
        self.voice_key.layout.display = "block" if gemini else "none"
        self.voice_name.layout.display = "block" if gemini else "none"
        self.voice_file.layout.display = "block" if chatterbox else "none"
        self.voice_consent.layout.display = "block" if chatterbox else "none"
        self.voice_exaggeration.layout.display = "block" if chatterbox else "none"
        self.voice_cfg.layout.display = "block" if chatterbox else "none"

    def _provider_settings(self):
        provider = self.provider.value
        info = provider_info(provider)
        base_url = self.custom_url.value.strip() if provider in {"custom", "cloudflare"} else info["base_url"]
        return provider, self.llm_key.value.strip(), self.model.value or "", base_url

    def _on_load_models(self, _):
        with self.render_output:
            clear_output()
        try:
            provider, key, selected, base = self._provider_settings()
            selected = self.custom_model.value.strip() or selected
            manual_model = self.custom_model.value.strip()
            try:
                models = list_models(provider, key, base, self.free_only.value)
            except Exception as catalogue_error:
                if not manual_model:
                    raise RuntimeError(
                        f"Could not load this provider's model catalogue: {catalogue_error}. "
                        "Enter an exact model ID in the override field and press again to test it."
                    ) from catalogue_error
                models = [manual_model]
            if not models and manual_model:
                models = [manual_model]
            if not models:
                raise RuntimeError("The provider returned no model IDs. Enter an exact model ID in the override field.")
            self.model.options = models
            chosen = manual_model or (selected if selected in models else models[0])
            self.model.value = chosen if chosen in models else models[0]
            if chosen not in models:
                self.custom_model.value = chosen
            answer = test_text_provider(provider, key, chosen, base)
            self.provider_status.value = '<span style="color:#80e0aa">Connected · selected model replied: ' + html.escape(answer) + '</span>'
        except Exception as exc:
            self.provider_status.value = '<span style="color:#ffb4a2">' + html.escape(str(exc)) + '</span>'

    def _on_plan(self, _):
        self.plan_btn.disabled = True
        self.plan_status.value = '<span style="color:#91caff">Building an editable scene plan…</span>'
        try:
            provider, key, model, base = self._provider_settings()
            model = self.custom_model.value.strip() or model
            use_llm = bool(key and model)
            storyboard = self.engine.draft(
                topic=self.topic.value,
                script=self.script.value,
                scene_notes=self.scene_notes.value,
                style=self.style.value,
                language=self.language.value,
                aspect_ratio=self.aspect.value,
                duration_seconds=self.duration.value,
                provider=provider if use_llm else None,
                api_key=key if use_llm else None,
                model=model if use_llm else None,
                base_url=base if use_llm else None,
            )
            self.state["storyboard"] = storyboard
            self.state["job_dir"] = self.engine.new_job_dir()
            self.state["voice_path"] = None
            self._make_scene_editor()
            self.render_btn.disabled = False
            self.plan_status.value = (
                '<span style="color:#80e0aa">Storyboard ready · '
                + str(len(storyboard["scenes"])) + " scenes · "
                + html.escape(storyboard["generation_mode"]) + "</span>"
            )
            if storyboard.get("planner_note"):
                self.plan_status.value += '<div class="ss-note">' + html.escape(storyboard["planner_note"]) + "</div>"
            self.tabs.selected_index = 1
        except Exception as exc:
            self.plan_status.value = '<span style="color:#ffb4a2">' + html.escape(str(exc)) + "</span>"
        finally:
            self.plan_btn.disabled = False

    def _make_scene_editor(self):
        storyboard = self.state["storyboard"]
        self.scene_widgets = []
        cards = []
        for index, scene in enumerate(storyboard["scenes"]):
            narration = W.Textarea(value=scene["narration"], description="Narration",
                                   layout=W.Layout(width="100%", height="85px"))
            screen = W.Text(value=scene.get("on_screen_text",""), description="On-screen text",
                            layout=W.Layout(width="100%"))
            visual = W.Textarea(value=scene.get("visual_prompt",""), description="Visual direction",
                                layout=W.Layout(width="100%", height="70px"))
            query = W.Text(value=scene.get("stock_query",""), description="Stock search",
                           layout=W.Layout(width="100%"))
            stock = W.Dropdown(options=[("Motion graphic background only","")], value="",
                               description="Selected clip", layout=W.Layout(width="100%"))
            self.scene_widgets.append({"narration":narration,"screen":screen,"visual":visual,"query":query,"stock":stock})
            cards.append(W.VBox([
                W.HTML(f'<div style="font-weight:800;color:#8fc7ff;margin:8px 0">SCENE {index+1:02d}</div>'),
                narration, screen, visual, query, stock,
            ], layout=W.Layout(border="1px solid #2a3850", padding="10px", border_radius="12px", margin="6px 0")))
        self.scene_editor.children = cards

    def _sync_scenes(self):
        storyboard = self.state.get("storyboard")
        if not storyboard:
            raise ValueError("Create a scene plan first.")
        for scene, widgets in zip(storyboard["scenes"], self.scene_widgets):
            scene["narration"] = widgets["narration"].value.strip()
            scene["on_screen_text"] = widgets["screen"].value.strip()
            scene["visual_prompt"] = widgets["visual"].value.strip()
            scene["stock_query"] = widgets["query"].value.strip()
            scene["selected_stock_id"] = widgets["stock"].value or None
        storyboard["scenes"] = [s for s in storyboard["scenes"] if s["narration"]]
        if not storyboard["scenes"]:
            raise ValueError("At least one scene must contain narration.")
        storyboard["script"] = "\n".join(s["narration"] for s in storyboard["scenes"])
        return storyboard

    def _on_search_stock(self, _):
        self.stock_provider.disabled = True
        self.search_stock_btn.disabled = True
        try:
            storyboard = self._sync_scenes()
            if self.stock_provider.value == "motion":
                self.stock_status.value = '<span style="color:#91a1bb">Motion graphics only: no stock API is used.</span>'
                return
            self.engine.search_scene_footage(storyboard, self.stock_provider.value, self.stock_key.value.strip())
            for scene, widgets in zip(storyboard["scenes"], self.scene_widgets):
                results = scene.get("stock_results", [])
                options = [("Motion graphics background", "")]
                options.extend((f'{x["source"]} · {x["title"]} · {x["duration"]}s', x["id"]) for x in results)
                widgets["stock"].options = options
                if scene.get("selected_stock_id"):
                    widgets["stock"].value = scene["selected_stock_id"]
            found = sum(len(s.get("stock_results", [])) for s in storyboard["scenes"])
            self.stock_status.value = f'<span style="color:#80e0aa">Found {found} footage options. Review the scene dropdowns, then download selected clips.</span>'
        except Exception as exc:
            self.stock_status.value = '<span style="color:#ffb4a2">' + html.escape(str(exc)) + "</span>"
        finally:
            self.stock_provider.disabled = False
            self.search_stock_btn.disabled = False

    def _on_prepare_stock(self, _):
        self.prepare_stock_btn.disabled = True
        try:
            storyboard = self._sync_scenes()
            count = 0
            for scene, widgets in zip(storyboard["scenes"], self.scene_widgets):
                scene["selected_stock_id"] = widgets["stock"].value or None
            self.engine.download_selected_footage(storyboard, self.state["job_dir"])
            count = sum(1 for s in storyboard["scenes"] if s.get("stock_file"))
            self.stock_status.value = f'<span style="color:#80e0aa">Downloaded {count} selected clips. Other scenes will use code-generated motion graphics.</span>'
        except Exception as exc:
            self.stock_status.value = '<span style="color:#ffb4a2">' + html.escape(str(exc)) + "</span>"
        finally:
            self.prepare_stock_btn.disabled = False

    def _uploaded_file(self, widget, folder: Path, label: str):
        value = widget.value
        if not value:
            return None
        if isinstance(value, dict):
            item = next(iter(value.values()))
        else:
            item = value[0]
        name = Path(item.get("name", label)).name
        content = bytes(item["content"])
        path = folder / f"{uuid.uuid4().hex[:8]}-{name}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def _gemini_voice_key(self):
        if self.voice_key.value.strip():
            return self.voice_key.value.strip()
        if self.provider.value == "gemini":
            return self.llm_key.value.strip()
        return ""

    def _on_preview_voice(self, _):
        self.preview_voice_btn.disabled = True
        with self.voice_output:
            clear_output()
            try:
                storyboard = self._sync_scenes()
                engine = self.voice_engine.value
                if engine == "none":
                    raise ValueError("Choose Gemini TTS or Chatterbox to preview a voice.")
                preview_text = " ".join(s["narration"] for s in storyboard["scenes"])[:320]
                output = Path(self.state["job_dir"]) / "voice-preview.wav"
                settings = {}
                if engine == "gemini":
                    settings = {"api_key": self._gemini_voice_key(), "voice": self.voice_name.value, "style": self.voice_style.value}
                elif engine == "chatterbox":
                    reference = self._uploaded_file(self.voice_file, Path(self.state["job_dir"]) / "voice", "reference.wav")
                    settings = {
                        "voice_reference": reference,
                        "consent_confirmed": self.voice_consent.value,
                        "exaggeration": self.voice_exaggeration.value,
                        "cfg_weight": self.voice_cfg.value,
                    }
                path = self.engine.make_voice(preview_text, engine, output, **settings)
                self.state["voice_preview_path"] = path
                display(Audio(filename=path))
                self.voice_status.value = '<span style="color:#80e0aa">Voice preview ready. Listen before rendering the full narration.</span>'
            except Exception as exc:
                self.voice_status.value = '<span style="color:#ffb4a2">' + html.escape(str(exc)) + '</span>'
                display(HTML('<div class="ss-note ss-warn">' + html.escape(str(exc)) + '</div>'))
        self.preview_voice_btn.disabled = False

    def _on_render(self, _):
        self.render_btn.disabled = True
        self.render_status.value = '<span style="color:#91caff">Preparing your video project…</span>'
        with self.render_output:
            clear_output()
        with self.output_links:
            clear_output()
        try:
            storyboard = self._sync_scenes()
            missing_stock = [s["id"] for s in storyboard["scenes"] if s.get("selected_stock_id") and not s.get("stock_file")]
            if missing_stock:
                raise ValueError("Some scenes have a selected stock clip that has not been downloaded. Go to Scenes and click Download selected clips.")
            job_dir = Path(self.state["job_dir"])
            engine = self.voice_engine.value
            voice_path = None
            if engine != "none":
                voice_out = job_dir / "narration.wav"
                settings = {}
                if engine == "gemini":
                    settings = {"api_key": self.voice_key.value.strip(), "voice": self.voice_name.value, "style": self.voice_style.value}
                elif engine == "chatterbox":
                    reference = self._uploaded_file(self.voice_file, job_dir / "voice", "reference.wav")
                    settings = {
                        "voice_reference": reference,
                        "consent_confirmed": self.voice_consent.value,
                        "exaggeration": self.voice_exaggeration.value,
                        "cfg_weight": self.voice_cfg.value,
                    }
                voice_path = self.engine.make_voice(storyboard["script"], engine, voice_out, **settings)
                self.state["voice_path"] = voice_path
            music_path = self._uploaded_file(self.music_file, job_dir / "music", "music.mp3")
            def stage(message):
                self.render_status.value = '<span style="color:#91caff">' + html.escape(message) + '</span>'
            result = self.engine.render(
                storyboard=storyboard,
                job_dir=job_dir,
                style=self.style.value,
                aspect_ratio=self.aspect.value,
                duration_seconds=self.duration.value,
                voice_path=voice_path,
                music_path=music_path,
                caption_style=self.caption_style.value,
                whisper_timing=self.whisper_timing.value,
                progress=stage,
            )
            self.state["result"] = result
            video_path = Path(result["video"])
            export_video = self.export_dir / video_path.name
            shutil.copy2(video_path, export_video)
            for key in ("srt","timestamps","storyboard","manifest"):
                src = Path(result[key])
                shutil.copy2(src, self.export_dir / src.name)
            self.render_status.value = '<span style="color:#80e0aa">Render complete · ' + str(result["duration"]) + ' sec</span>'
            with self.render_output:
                display(Video(filename=str(export_video), embed=True, width=360))
                display(HTML('<div class="ss-note">MP4 rendered by HyperFrames. Stock-footage scenes are credited in the manifest; no photorealistic AI video is claimed.</div>'))
            with self.output_links:
                display(HTML("<b>Export files</b>"))
                for path in [export_video, self.export_dir / "captions.srt", self.export_dir / "timestamps.json",
                             self.export_dir / "storyboard.json", self.export_dir / "render_manifest.json"]:
                    if path.exists():
                        display(FileLink(str(path)))
                display(HTML('<div class="ss-muted">Saved in: ' + html.escape(str(self.export_dir)) + '</div>'))
        except Exception as exc:
            self.render_status.value = '<span style="color:#ffb4a2">Render failed: ' + html.escape(str(exc)) + '</span>'
            with self.render_output:
                display(HTML('<div class="ss-note ss-warn">' + html.escape(str(exc)) + '</div>'))
        finally:
            self.render_btn.disabled = False

    def display(self):
        display(HTML(DASHBOARD_CSS + """
        <div class="ss-wrap">
          <div class="ss-header">
            <div><div class="ss-sub">SHORT STORY SPEAKER · COLAB WORKSPACE</div>
            <div class="ss-brand">Short Story <span>Studio</span> <small style="font-size:12px;color:#91a1bb">V2</small></div>
            <div class="ss-muted">Script → scene board → footage → voice preview → MP4</div></div>
            <div class="ss-pill">NOTEBOOK SESSION · LOCAL RUNTIME</div>
          </div>
          <div class="ss-grid">
            <div class="ss-stat"><b>10 Styles</b><small>Stickman, Islamic, cinematic, cyberpunk…</small></div>
            <div class="ss-stat"><b>2 Free stock APIs</b><small>Pexels + Pixabay</small></div>
            <div class="ss-stat"><b>HyperFrames</b><small>HTML/CSS/GSAP → MP4</small></div>
          </div>
          <div class="ss-note">This dashboard runs inside the Colab notebook; it does not start a permanent web server. When the Colab runtime stops, the session and in-memory API keys stop too.</div>
        </div>
        """))
        display(self.tabs)
        display(HTML('<div class="ss-footer">API keys are memory-only · No silent provider switching · Check Islamic references before publishing</div>'))
