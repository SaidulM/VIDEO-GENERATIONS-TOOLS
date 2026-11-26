from __future__ import annotations
import uuid
from pathlib import Path
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from .config import FRONTEND, OUTPUTS, UPLOADS, env
from .providers import public_provider_list, save_provider_settings
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
    if not path.exists(): return HTMLResponse("<h1>Short Story Studio</h1><p>Frontend missing.</p>",status_code=503)
    return HTMLResponse(path.read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    return {"status":"ok","app":"Short Story Studio","providers":public_provider_list(),"voices":voice_catalog(),
            "skills":[{"id":s["id"],"name":s["name"],"description":s["description"]} for s in load_skills()]}

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
        return create_storyboard(data.topic,data.script,data.scene_notes,data.style,data.language,data.format,data.provider,data.model)
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/upload-voice")
async def upload_voice(file:UploadFile=File(...)):
    suffix=Path(file.filename or "").suffix.lower()
    if suffix not in {".wav",".mp3",".m4a",".flac",".ogg"}: raise HTTPException(400,"Upload WAV, MP3, M4A, FLAC or OGG audio.")
    content=await file.read()
    if len(content)>15*1024*1024: raise HTTPException(413,"Voice reference must be 15 MB or smaller.")
    name=uuid.uuid4().hex+suffix; path=UPLOADS/name; path.write_bytes(content)
    return {"voice_reference":str(path),"filename":file.filename}

@app.post("/api/voice-preview")
def voice_preview(data:VoicePreviewRequest):
    try: return preview_voice(data.text,data.engine,data.voice_id,data.voice_reference)
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/render")
def render(data:RenderRequest):
    try:
        return render_video(data.storyboard,data.style,data.format,data.voice_engine,data.voice_id,data.voice_reference,
                           data.captions,data.caption_style,data.target_seconds,data.title)
    except Exception as exc: raise HTTPException(400,str(exc))

@app.post("/api/comfyui/submit")
def comfy_submit(data:ComfySubmitRequest):
    base=(data.server_url or env("COMFYUI_URL","http://127.0.0.1:8188")).rstrip("/")
    from urllib.parse import urlparse
    parsed=urlparse(base); host=parsed.hostname or ""
    if parsed.scheme not in {"http","https"} or not parsed.netloc: raise HTTPException(400,"Invalid ComfyUI URL.")
    if not (host in {"localhost","127.0.0.1","::1"} or host.startswith(("192.168.","10.","172.16.")) or host.endswith(".trycloudflare.com")):
        raise HTTPException(400,"ComfyUI URL must be localhost, a private LAN address or a trusted trycloudflare tunnel.")
    try:
        response=requests.post(base+"/prompt",json={"prompt":data.workflow},timeout=30); response.raise_for_status()
        return response.json()
    except requests.RequestException as exc: raise HTTPException(502,"ComfyUI request failed: "+str(exc))

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
