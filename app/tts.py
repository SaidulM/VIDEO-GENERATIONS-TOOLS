from __future__ import annotations
from pathlib import Path
import numpy as np

KOKORO_VOICES = [
    {"id":"hm_omega","label":"Hindi male — Omega"},
    {"id":"hm_psi","label":"Hindi male — Psi"},
    {"id":"hf_alpha","label":"Hindi female — Alpha"},
    {"id":"hf_beta","label":"Hindi female — Beta"},
]

def voice_catalog():
    try:
        import kokoro  # noqa
        kokoro_ready = True
    except Exception:
        kokoro_ready = False
    rows = [{**voice,"engine":"kokoro","installed":kokoro_ready,"cloning":False} for voice in KOKORO_VOICES]
    try:
        import chatterbox  # noqa
        chatterbox_ready = True
    except Exception:
        chatterbox_ready = False
    rows.append({"id":"reference","label":"Chatterbox multilingual — permitted reference voice",
                 "engine":"chatterbox","installed":chatterbox_ready,"cloning":True,"experimental":True})
    rows.append({"id":"none","label":"No narration — captions only","engine":"none","installed":True,"cloning":False})
    return rows

def synthesize(text, output_path, engine, voice_id="hm_omega", language="hi", voice_reference=None):
    target = Path(output_path)
    target.parent.mkdir(parents=True,exist_ok=True)
    if engine == "none":
        return None
    if engine == "kokoro":
        try:
            from kokoro import KPipeline
            import soundfile as sf
        except Exception as exc:
            raise RuntimeError("Kokoro is not installed. Run pip install -r requirements-tts.txt.") from exc
        lang_code = "h" if language.lower().startswith(("hi","hing","roman")) else "a"
        pipeline = KPipeline(lang_code=lang_code)
        valid = {item["id"] for item in KOKORO_VOICES}
        voice = voice_id if voice_id in valid else "hm_omega"
        chunks = [np.asarray(audio,dtype=np.float32) for _,_,audio in pipeline(text,voice=voice)]
        if not chunks:
            raise RuntimeError("Kokoro returned no audio. Check language and voice settings.")
        audio_data = np.concatenate(chunks)
        sf.write(str(target),audio_data,24000)
        return {"path":str(target),"sample_rate":24000,"engine":"kokoro","voice":voice}
    if engine == "chatterbox":
        if not voice_reference:
            raise ValueError("Chatterbox requires a reference recording that you own or are authorized to use.")
        try:
            import torch
            import soundfile as sf
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except Exception as exc:
            raise RuntimeError("Chatterbox is not installed. It is an experimental, archived optional engine.") from exc
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        audio = model.generate(text,language_id="hi",audio_prompt_path=voice_reference)
        samples = audio.squeeze().detach().cpu().numpy() if hasattr(audio,"detach") else np.asarray(audio).squeeze()
        sample_rate = int(getattr(model,"sr",24000))
        sf.write(str(target),samples,sample_rate)
        return {"path":str(target),"sample_rate":sample_rate,"engine":"chatterbox","voice":"reference"}
    raise ValueError("Unsupported voice engine.")
