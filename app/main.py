from __future__ import annotations
import json, uuid
from pathlib import Path
from urllib.parse import urlparse
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .config import FRONTEND, OUTPUTS, env
from .providers import public_provider_list, save_provider_settings, PROVIDERS
from .schemas import DraftRequest, RenderRequest, SettingsRequest, VoicePreviewRequest, ComfySubmitRequest
from .storyboard import create_storyboard
from .tts import voice_catalog
from .renderer import render_video, preview_voice
from .skills import load_skills

app=FastAPI(title="Short Story Studio",version="0.1.0")
FRONTEND.mkdir(exist_ok=True)
app.mount("/static",StaticFiles(directory=str(FRONTEND)),name="static")
app.mount("/outputs",StaticFiles(directory=str(OUTPUTS)),name="outputs")

@app.get("/",response_class=HTMLResponse)
def home():
    path=FRONTEND/"index.html"
    if not path.exists(): return HTMLResponse("<h1>Short Story Studio</h1><p>Frontend is not installed.</p>",status_code=503)
    return HTMLResponse(path.read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    return {"status":"ok","app":"Short Story Studio","providers":public_provider_list(),"voices":voice_catalog(),"skills":[{"id":s["id"],"name":s["name"],"description":s["description"]} for s in load_skills()]}

@app.get("/api/providers")
def providers(): return public_provider_list()

@app.post("/api/settings")
def settings(data:SettingsRequest):
    try: save_provider_settings(data.provider,data.api_key,data.model)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {"saved":True,"providers":public_provider_list(),"message":"Settings saved locally. API keys are not returned."}

@app.post("/api/draft")
def draft(data:DraftRequest):
    try:
        result=create_storyboard(data.topic,data.script,data.scene_notes,data.style,data.language,data.format,data.provider,data.model)
        return result
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/voice-preview")
def voice_preview(data:VoicePreviewRequest):
    try: return preview_voice(data.text,data.engine,data.voice_id,data.voice_reference)
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/render")
def render(data:RenderRequest):
    try:
        result=render_video(data.storyboard,data.style,data.format,data.voice_engine,data.voice_id,data.voice_reference,data.captions,data.caption_style,data.target_seconds,data.title)
        return result
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/comfyui/submit")
def comfy_submit(data:ComfySubmitRequest,request:Request):
    base=(data.server_url or env("COMFYUI_URL","http://127.0.0.1:8188")).rstrip("/")
    parsed=urlparse(base)
    if parsed.scheme not in {"http","https"} or not parsed.netloc:
        raise HTTPException(400,"Invalid ComfyUI URL.")
    # Prevent obvious public-host SSRF. Use a private tunnel only on a trusted network.
    host=parsed.hostname or ""
    if not (host in {"localhost","127.0.0.1","::1"} or host.startswith(("192.168.","10.","172.16.")) or host.endswith(".trycloudflare.com")):
        raise HTTPException(400,"ComfyUI URL must be localhost, a private LAN address or a trusted trycloudflare tunnel.")
    try:
        response=requests.post(base+"/prompt",json={"prompt":data.workflow},timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise HTTPException(502,"ComfyUI request failed: "+str(exc))

@app.get("/api/comfyui/history/{prompt_id}")
def comfy_history(prompt_id:str):
    base=env("COMFYUI_URL","http://127.0.0.1:8188").rstrip("/")
    try:
        response=requests.get(base+"/history/"+prompt_id,timeout=20); response.raise_for_status()
        return response.json()
    except requests.RequestException as exc: raise HTTPException(502,"ComfyUI history request failed: "+str(exc))

@app.get("/api/download/{job_id}")
def download(job_id:str):
    path=OUTPUTS/job_id/"video.mp4"
    if not path.exists(): raise HTTPException(404,"Video not found.")
    return FileResponse(path,media_type="video/mp4",filename="short-story.mp4")
