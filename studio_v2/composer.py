from __future__ import annotations

from pathlib import Path
import html
import json
import shutil
import subprocess

from .captions import write_srt, write_timestamps

HYPERFRAMES_VERSION = "0.9.98"

STYLE_CSS = {
    "cinematic": "background:radial-gradient(circle at 78% 22%,#38547b 0,transparent 38%),linear-gradient(140deg,#070d1b,#17263a 55%,#080a12);",
    "islamic_geometry": "background:repeating-conic-gradient(from 15deg at 50% 50%,#0d3f37 0deg 12deg,#125246 12deg 24deg,#0b302c 24deg 36deg);",
    "cyberpunk": "background:radial-gradient(circle at 75% 22%,#ee25e4 0,transparent 20%),radial-gradient(circle at 15% 80%,#04d6d0 0,transparent 25%),linear-gradient(145deg,#07051c,#140b36 58%,#050614);",
    "hand_drawn": "background:radial-gradient(circle at 80% 20%,#eed5ad 0,transparent 30%),linear-gradient(135deg,#ece1c8,#d9c49d 55%,#b58a6c);",
    "stickman": "background:linear-gradient(145deg,#fbfaf3,#e8e9e5);",
    "retro_tv": "background:repeating-linear-gradient(0deg,#171c23 0 4px,#202a32 4px 8px);",
    "pixel_art": "background:linear-gradient(135deg,#101d3a,#31245b 50%,#111a31);",
    "clay": "background:radial-gradient(circle at 70% 22%,#f1c99d 0,transparent 26%),linear-gradient(140deg,#a86349,#d49b73 55%,#744a47);",
    "3d_motion": "background:radial-gradient(circle at 75% 24%,#7796c4 0,transparent 35%),linear-gradient(145deg,#101a34,#334f7a 58%,#0a1023);",
    "kinetic_type": "background:linear-gradient(140deg,#101114,#272a31 58%,#0b0c10);",
}

PALETTES = {
    "cinematic": ("#f7f3eb", "#e8b76a", "#121a28"),
    "islamic_geometry": ("#f8f1df", "#e0bd75", "#0c3d35"),
    "cyberpunk": ("#f8f3ff", "#23e7df", "#170e36"),
    "hand_drawn": ("#2b1d19", "#9d543a", "#f5e7c9"),
    "stickman": ("#15191e", "#2678d6", "#faf9f3"),
    "retro_tv": ("#e3e9ef", "#8fb9cd", "#121820"),
    "pixel_art": ("#f5edff", "#d6a8ff", "#182044"),
    "clay": ("#fff4e5", "#f4c28d", "#70443d"),
    "3d_motion": ("#f7f7ff", "#90b7ed", "#13213c"),
    "kinetic_type": ("#fbf8f0", "#f2bd61", "#131416"),
}

def _scene_duration(scene: dict, total_words: int, total_seconds: float) -> float:
    weight = max(1, len(str(scene.get("narration", "")).split()))
    return total_seconds * weight / max(1, total_words)

def build_project(job_dir: str | Path, storyboard: dict, style: str, aspect_ratio: str,
                  target_seconds: int, voice_path: str | None, music_path: str | None,
                  caption_segments: list[dict], caption_style: str = "bold") -> dict[str, str]:
    job = Path(job_dir)
    project = job / "hyperframes_project"
    assets = project / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    scenes = storyboard.get("scenes") or []
    if not scenes:
        raise ValueError("There are no scenes to render.")
    total_words = sum(max(1, len(str(scene.get("narration", "")).split())) for scene in scenes)
    if voice_path and Path(voice_path).is_file():
        import soundfile as sf
        total_duration = float(sf.info(voice_path).duration)
    else:
        total_duration = float(target_seconds)

    style_background = STYLE_CSS.get(style, STYLE_CSS["cinematic"])
    foreground, accent, dark = PALETTES.get(style, PALETTES["cinematic"])
    media_tags: list[str] = []
    graphic_tags: list[str] = []
    caption_tags: list[str] = []
    gsap_lines: list[str] = []
    cursor = 0.0

    for index, scene in enumerate(scenes):
        duration = _scene_duration(scene, total_words, total_duration)
        start = cursor
        title = str(scene.get("on_screen_text") or scene.get("narration") or storyboard.get("title", ""))[:90]
        visual = str(scene.get("visual_prompt") or "")[:160]
        stock_path = scene.get("stock_file")
        if stock_path and Path(stock_path).is_file():
            local_video = assets / f"scene-{index+1:02d}.mp4"
            if Path(stock_path).resolve() != local_video.resolve():
                shutil.copy2(stock_path, local_video)
            media_tags.append(
                f'<video id="footage-{index}" class="clip" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0" src="assets/{local_video.name}" muted loop playsinline></video>'
            )
        else:
            graphic_tags.append(
                f'<div id="visual-{index}" class="clip scene-bg" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="0">'
                f'<div class="orb orb-a"></div><div class="orb orb-b"></div><div class="grid-lines"></div></div>'
            )
        safe_title, safe_visual = html.escape(title), html.escape(visual)
        graphic_tags.append(
            f'<div id="shade-{index}" class="clip shade" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="1"></div>'
        )
        graphic_tags.append(
            f'<div id="scene-title-{index}" class="clip scene-title" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="2">'
            f'<div class="kicker">SHORT STORY SPEAKER <span>•</span> {index+1:02d}/{len(scenes):02d}</div>'
            f'<h1>{safe_title}</h1><p>{safe_visual}</p></div>'
        )
        gsap_lines.append(
            f'tl.fromTo("#scene-title-{index}",{{opacity:0,y:75,filter:"blur(10px)"}},{{opacity:1,y:0,filter:"blur(0px)",duration:0.75,ease:"power3.out"}},{start+0.15:.3f});'
        )
        gsap_lines.append(
            f'tl.fromTo("#shade-{index}",{{opacity:0}},{{opacity:1,duration:0.4,ease:"none"}},{start:.3f});'
        )
        cursor += duration

    for index, segment in enumerate(caption_segments):
        start = max(0.0, float(segment["start"]))
        end = min(total_duration, max(start + 0.12, float(segment["end"])))
        if end <= start:
            continue
        safe_text = html.escape(str(segment["text"]))
        caption_tags.append(
            f'<div id="caption-{index}" class="clip caption caption-{caption_style}" data-start="{start:.3f}" data-duration="{end-start:.3f}" data-track-index="5">'
            f'<span>{safe_text}</span></div>'
        )
        gsap_lines.append(
            f'tl.fromTo("#caption-{index}",{{opacity:0,y:28}},{{opacity:1,y:0,duration:0.18,ease:"power2.out"}},{start:.3f});'
        )

    audio_tags: list[str] = []
    if voice_path and Path(voice_path).is_file():
        voice_file = assets / "narration.wav"
        shutil.copy2(voice_path, voice_file)
        audio_tags.append(
            f'<audio id="narration" class="clip" data-start="0" data-duration="{total_duration:.3f}" data-track-index="8" src="assets/{voice_file.name}" data-volume="1"></audio>'
        )
    if music_path and Path(music_path).is_file():
        music_file = assets / f"music{Path(music_path).suffix or '.mp3'}"
        shutil.copy2(music_path, music_file)
        audio_tags.append(
            f'<audio id="music" class="clip" data-start="0" data-duration="{total_duration:.3f}" data-track-index="9" src="assets/{music_file.name}" data-volume="0.13" loop></audio>'
        )

    hook = html.escape(str(storyboard.get("hook") or storyboard.get("title") or ""))
    root_css = f"""
    html,body{{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden;background:{dark};font-family:Arial,'Noto Sans',sans-serif;color:{foreground};}}
    #root{{position:relative;width:{width}px;height:{height}px;overflow:hidden;isolation:isolate;{style_background}}}
    .clip{{position:absolute;inset:0;width:100%;height:100%;box-sizing:border-box;}}
    video{{object-fit:cover;z-index:0;}}
    .scene-bg{{overflow:hidden;z-index:0;background:{style_background}}}
    .orb{{position:absolute;border-radius:50%;filter:blur(2px);opacity:.3;}}
    .orb-a{{width:55%;height:42%;right:-12%;top:10%;background:{accent};}}
    .orb-b{{width:42%;height:34%;left:-18%;bottom:8%;background:{foreground};opacity:.12;}}
    .grid-lines{{position:absolute;inset:0;opacity:.11;background-image:linear-gradient(rgba(255,255,255,.4) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.4) 1px,transparent 1px);background-size:70px 70px;}}
    .shade{{z-index:1;background:linear-gradient(180deg,rgba(0,0,0,.12),rgba(0,0,0,.25) 42%,rgba(0,0,0,.78));}}
    .scene-title{{z-index:2;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;padding:{int(width*.09)}px;}}
    .kicker{{font-size:{int(width*.028)}px;letter-spacing:.22em;font-weight:800;color:{accent};margin-bottom:{int(width*.07)}px;}}
    h1{{font-size:{int(width*.096)}px;line-height:1.02;letter-spacing:-.045em;margin:0 0 {int(width*.05)}px;font-weight:900;max-width:90%;text-shadow:0 5px 26px rgba(0,0,0,.23);}}
    .scene-title p{{font-size:{int(width*.034)}px;line-height:1.35;max-width:84%;opacity:.78;margin:0;}}
    .caption{{z-index:4;inset:auto {int(width*.06)}px {int(height*.105)}px;height:auto;min-height:{int(height*.065)}px;display:flex;justify-content:center;align-items:center;text-align:center;}}
    .caption span{{background:rgba(5,8,15,.83);border:2px solid {accent};border-radius:20px;padding:{int(width*.026)}px {int(width*.042)}px;color:white;font-size:{int(width*.046)}px;line-height:1.18;font-weight:900;text-shadow:0 2px 4px #000;max-width:95%;}}
    .caption-minimal span{{background:rgba(0,0,0,.48);border:0;}}
    .caption-gold span{{color:{accent};}}
    .hook{{z-index:3;left:{int(width*.07)}px;right:{int(width*.07)}px;top:{int(height*.055)}px;bottom:auto;height:auto;display:flex;justify-content:center;}}
    .hook span{{font-size:{int(width*.026)}px;letter-spacing:.12em;font-weight:800;color:{accent};text-transform:uppercase;text-align:center;}}
    """
    hook_tag = (
        f'<div id="hook" class="clip hook" data-start="0" '
        f'data-duration="{min(3.5,total_duration):.3f}" data-track-index="6"><span>{hook}</span></div>'
    )
    gsap_lines.insert(0, 'tl.fromTo("#hook",{opacity:0,y:-25},{opacity:1,y:0,duration:0.55,ease:"power2.out"},0);')
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width={width},initial-scale=1">
<title>{html.escape(str(storyboard.get("title","Short Story Speaker")))}</title>
<style>{root_css}</style>
</head><body>
<div id="root" data-composition-id="root" data-start="0" data-width="{width}" data-height="{height}" data-fps="30">
{''.join(media_tags)}{''.join(graphic_tags)}{''.join(caption_tags)}{hook_tag}{''.join(audio_tags)}
</div>
<script>
const tl = gsap.timeline({{paused:true}});
{''.join(gsap_lines)}
window.__timelines = window.__timelines || {{}};
window.__timelines["root"] = tl;
</script>
</body></html>"""
    (project / "index.html").write_text(html_doc, encoding="utf-8")
    (project / "meta.json").write_text(json.dumps({
        "name": str(storyboard.get("title", "Short Story Speaker")),
        "description": "Generated by Short Story Studio v2",
        "width": width,
        "height": height,
        "fps": 30,
        "duration": round(total_duration, 3),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    srt_path = write_srt(caption_segments, job / "captions.srt")
    timestamps_path = write_timestamps(caption_segments, total_duration, job / "timestamps.json")
    return {
        "project_dir": str(project),
        "duration": total_duration,
        "srt": srt_path,
        "timestamps": timestamps_path,
    }

def render_project(project_dir: str | Path, output_path: str | Path, progress=None,
                   timeout_seconds: int = 1800) -> str:
    project = Path(project_dir).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("Node.js/npm is missing. Run the Colab Setup cell and confirm Node.js 22+ is installed.")
    base_cmd = [npx, "--yes", f"hyperframes@{HYPERFRAMES_VERSION}"]
    if progress:
        progress("Checking HyperFrames Chromium runtime…")
    ensure = subprocess.run(
        base_cmd + ["browser", "ensure"], cwd=project,
        capture_output=True, text=True, timeout=timeout_seconds,
    )
    if ensure.returncode != 0:
        detail = (ensure.stderr or ensure.stdout)[-2500:]
        raise RuntimeError("HyperFrames could not prepare Chromium: " + detail)
    if progress:
        progress("Checking the composition…")
    lint = subprocess.run(
        base_cmd + ["lint", "--json"], cwd=project,
        capture_output=True, text=True, timeout=timeout_seconds,
    )
    if lint.returncode != 0:
        detail = (lint.stderr or lint.stdout)[-4000:]
        raise RuntimeError("HyperFrames composition validation failed. No silent fallback was used. " + detail)
    if progress:
        progress("Rendering MP4 with HyperFrames…")
    local_output = project / "render.mp4"
    render = subprocess.run(
        base_cmd + ["render", "--output", str(local_output)],
        cwd=project, capture_output=True, text=True, timeout=timeout_seconds,
    )
    if render.returncode != 0 or not local_output.exists() or local_output.stat().st_size < 1024:
        detail = (render.stderr or render.stdout)[-5000:]
        raise RuntimeError("HyperFrames render failed. The job is not marked complete. " + detail)
    shutil.copy2(local_output, output)
    return str(output)
