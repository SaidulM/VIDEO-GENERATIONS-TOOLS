from __future__ import annotations
import json, math, subprocess, tempfile, uuid
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
from .config import OUTPUTS
from .tts import synthesize

SIZE={"short":(1080,1920),"long":(1920,1080)}
THEMES={
 "cinematic":((12,20,37),(42,55,78),(225,177,95),(250,247,238)),
 "islamic_geometry":((8,43,39),(18,78,67),(223,190,114),(250,247,232)),
 "cyberpunk":((15,8,41),(38,18,76),(0,240,220),(250,245,255)),
 "clay":((120,78,64),(207,145,104),(251,213,155),(255,249,236)),
 "3d":((26,44,76),(79,112,149),(246,192,116),(249,250,255)),
 "minimal":((25,28,32),(52,58,65),(245,206,111),(250,250,246))
}
def font(size,bold=False):
    for name in (["DejaVuSans-Bold.ttf","arialbd.ttf"] if bold else ["DejaVuSans.ttf","arial.ttf"]):
        try: return ImageFont.truetype(name,size)
        except OSError: pass
    return ImageFont.load_default()

def wrap(draw,text,fnt,max_width):
    lines=[]; current=""
    for word in str(text).split():
        candidate=(current+" "+word).strip()
        if draw.textbbox((0,0),candidate,font=fnt)[2] <= max_width or not current: current=candidate
        else: lines.append(current); current=word
    if current: lines.append(current)
    return lines

def make_card(path,index,total,scene,style,title,captions,caption_style,width,height):
    top,bottom,accent,fg=THEMES.get(style,THEMES["cinematic"])
    image=Image.new("RGB",(width,height)); pixels=image.load()
    for y in range(height):
        t=y/max(1,height-1); c=tuple(int(top[k]*(1-t)+bottom[k]*t) for k in range(3))
        for x in range(width): pixels[x,y]=c
    draw=ImageDraw.Draw(image,"RGBA"); unit=min(width,height); spacing=max(45,unit//10)
    if style=="islamic_geometry":
        for off in range(-height,width,spacing):
            draw.line((off,0,off+height,height),fill=(*accent,35),width=3)
            draw.line((off,height,off+height,0),fill=(*accent,35),width=3)
        cx,cy=width//2,height//3; radius=unit//4
        for angle in range(0,360,30):
            rad=math.radians(angle)
            draw.line((cx,cy,cx+int(radius*math.cos(rad)),cy+int(radius*math.sin(rad))),fill=(*accent,70),width=2)
    elif style in ("cyberpunk","3d"):
        for n in range(8):
            pad=int(unit*(.06+n*.045))
            draw.rounded_rectangle((pad,pad*2,width-pad,height-pad),radius=unit//12,outline=(*accent,max(18,95-n*8)),width=3)
        for x in range(0,width,spacing): draw.line((x,0,x,height),fill=(*accent,16),width=1)
    elif style=="clay":
        for n in range(7):
            x=(n*193+80)%width; y=(n*311+160)%height; r=unit*(.04+(n%3)*.025)
            draw.ellipse((x-r,y-r,x+r,y+r),fill=(*accent,22),outline=(*accent,70),width=4)
    else:
        draw.ellipse((width*.55,height*.06,width*1.15,height*.55),outline=(*accent,42),width=5)
    margin=int(width*.09); small=font(max(22,int(unit*.024))); head=font(max(32,int(unit*.055)),True); body=font(max(28,int(unit*.041)),True)
    draw.text((margin,int(height*.07)),"SHORT STORY SPEAKER",font=small,fill=(*fg,190))
    draw.text((margin,int(height*.11)),f"{index+1:02d} / {total:02d}",font=small,fill=(*accent,255))
    headline=str(scene.get("on_screen_text") or scene.get("narration") or title)
    y=int(height*.26)
    for line in wrap(draw,headline,head,width-2*margin)[:4]:
        draw.text((margin,y),line,font=head,fill=(*fg,255),stroke_width=1,stroke_fill=(0,0,0,80)); y+=int(unit*.075)
    visual=str(scene.get("visual_prompt") or "")[:120]; y=int(height*.53)
    for line in wrap(draw,visual,small,width-2*margin)[:3]:
        draw.text((margin,y),line,font=small,fill=(*fg,175)); y+=int(unit*.04)
    if captions:
        lines=wrap(draw,str(scene.get("narration") or ""),body,width-2*margin)[:5]
        line_h=int(unit*(.054 if caption_style=="minimal" else .062)); box_h=line_h*len(lines)+int(unit*.05)
        box_y=height-box_h-int(height*.09)
        draw.rounded_rectangle((margin//2,box_y,width-margin//2,height-int(height*.065)),radius=int(unit*.025),fill=(0,0,0,175),outline=(*accent,145),width=2)
        y=box_y+int(unit*.025)
        for line in lines:
            draw.text((margin,y),line,font=body,fill=(*accent,255) if caption_style=="highlight" else (*fg,255)); y+=line_h
    draw.text((margin,height-int(height*.035),),str(title)[:75],font=small,fill=(*fg,170))
    image.save(path)

def stamp(seconds):
    ms=int(round(seconds*1000)); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def render_video(storyboard,style="cinematic",project_format="short",voice_engine="none",
                 voice_id="hm_omega",voice_reference=None,captions=True,caption_style="bold",
                 target_seconds=45,title=None):
    scenes=storyboard.get("scenes") or []
    if not scenes: raise ValueError("Storyboard has no scenes.")
    job_id=uuid.uuid4().hex[:12]; out=OUTPUTS/job_id; out.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix=job_id+"-",dir=str(OUTPUTS)))
    width,height=SIZE.get(project_format,SIZE["short"])
    narration=str(storyboard.get("full_narration") or " ".join(str(s.get("narration","")) for s in scenes))
    voice=None; audio=temp/"voice.wav"
    if voice_engine!="none": voice=synthesize(narration,audio,voice_engine,voice_id,"hi",voice_reference)
    duration=float(target_seconds)
    if voice:
        try:
            import soundfile as sf
            duration=float(sf.info(str(audio)).duration)
        except Exception: pass
    weights=[max(1,len(str(s.get("narration","")).split())) for s in scenes]
    total=sum(weights); ffmpeg=__import__("imageio_ffmpeg").get_ffmpeg_exe()
    segments=[]; manifest=[]; cursor=0.0
    for i,(scene,weight) in enumerate(zip(scenes,weights)):
        seconds=duration*weight/total; img=temp/f"scene-{i:02d}.png"; clip=temp/f"clip-{i:02d}.mp4"
        make_card(img,i,len(scenes),scene,style,title or storyboard.get("title","Short Story Speaker"),captions,caption_style,width,height)
        frames=max(1,int(math.ceil(seconds*30)))
        vf=f"scale={width}:{height},zoompan=z='min(zoom+0.0005,1.06)':d=1:s={width}x{height}:fps=30,format=yuv420p"
        cmd=[ffmpeg,"-y","-loop","1","-i",str(img),"-t",f"{seconds:.3f}","-vf",vf,"-r","30","-frames:v",str(frames),"-an","-c:v","libx264","-preset","ultrafast","-crf","24",str(clip)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=max(180,int(seconds*20)))
        if p.returncode: raise RuntimeError("FFmpeg scene render failed: "+p.stderr[-900:])
        segments.append(clip); manifest.append({"scene_id":scene.get("id",f"scene-{i+1}"),"start_seconds":round(cursor,3),"end_seconds":round(cursor+seconds,3),"duration_seconds":round(seconds,3),"narration":scene.get("narration",""),"visual_prompt":scene.get("visual_prompt","")}); cursor+=seconds
    concat_file=temp/"concat.txt"
    concat_file.write_text("".join("file '"+p.as_posix()+"'\n" for p in segments),encoding="utf-8")
    silent=temp/"silent.mp4"
    p=subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(concat_file),"-c","copy",str(silent)],capture_output=True,text=True,timeout=300)
    if p.returncode: raise RuntimeError("FFmpeg could not join scenes: "+p.stderr[-900:])
    final=out/"video.mp4"
    cmd=[ffmpeg,"-y","-i",str(silent)]
    if voice: cmd += ["-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest"]
    else: cmd += ["-c:v","copy"]
    cmd += ["-movflags","+faststart",str(final)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    if p.returncode: raise RuntimeError("FFmpeg final mux failed: "+p.stderr[-900:])
    narration_parts=[s.strip() for s in __import__("re").split(r"(?<=[.!?।])\s+|\n+",narration) if s.strip()] or [narration]
    word_counts=[max(1,len(s.split())) for s in narration_parts]; word_total=sum(word_counts); t=0; srt=[]; caps=[]
    for i,(part,w) in enumerate(zip(narration_parts,word_counts),1):
        end=min(duration,t+duration*w/word_total)
        srt.append(f"{i}\n{stamp(t)} --> {stamp(end)}\n{part}\n")
        caps.append({"index":i,"start_seconds":round(t,3),"end_seconds":round(end,3),"text":part}); t=end
    (out/"captions.srt").write_text("\n".join(srt),encoding="utf-8")
    (out/"storyboard.json").write_text(json.dumps(storyboard,ensure_ascii=False,indent=2),encoding="utf-8")
    times={"format":project_format,"width":width,"height":height,"fps":30,"duration_seconds":round(duration,3),"scenes":manifest,"caption_segments":caps}
    (out/"timestamps.json").write_text(json.dumps(times,ensure_ascii=False,indent=2),encoding="utf-8")
    meta={"job_id":job_id,"created_at":datetime.now(timezone.utc).isoformat(),"renderer":"Pillow + FFmpeg motion cards","style":style,"voice":voice or {"engine":"none"},"captions_burned_in":bool(captions),"note":"Template motion graphics; not photorealistic generated footage."}
    (out/"render_manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"job_id":job_id,"video_url":f"/outputs/{job_id}/video.mp4","captions_url":f"/outputs/{job_id}/captions.srt","timestamps_url":f"/outputs/{job_id}/timestamps.json","storyboard_url":f"/outputs/{job_id}/storyboard.json","manifest_url":f"/outputs/{job_id}/render_manifest.json","duration_seconds":round(duration,3)}

def preview_voice(text,engine,voice_id,voice_reference=None):
    job=uuid.uuid4().hex[:12]; path=OUTPUTS/job/"preview.wav"; path.parent.mkdir(parents=True,exist_ok=True)
    result=synthesize(text,path,engine,voice_id,"hi",voice_reference)
    if not result: raise ValueError("Select a voice engine to preview.")
    return {"audio_url":f"/outputs/{job}/preview.wav"}
