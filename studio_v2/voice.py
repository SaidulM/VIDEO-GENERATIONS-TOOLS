from __future__ import annotations

from pathlib import Path
import base64
import gc
import re
import numpy as np

GEMINI_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]

def _split_text(text: str, max_chars: int = 2500) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("Narration is empty.")
    parts = []
    while len(text) > max_chars:
        cut = max(text.rfind(mark, 0, max_chars) for mark in (".", "?", "!", "।", "؟", ",", " "))
        if cut < max_chars * 0.45:
            cut = max_chars
        else:
            cut += 1
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts

def synthesize_gemini(text: str, api_key: str, output_path: str | Path,
                      voice: str = "Kore", style: str = "Warm, clear, natural Hindi/Hinglish narrator."):
    if not api_key:
        raise ValueError("Enter a Google Gemini API key. Get one from https://aistudio.google.com/apikey")
    if voice not in GEMINI_VOICES:
        raise ValueError("Choose a valid Gemini TTS voice.")
    try:
        from google import genai
        import soundfile as sf
    except Exception as exc:
        raise RuntimeError("Google Gen AI SDK or SoundFile is missing. Run the Colab dependency cell again.") from exc
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    chunks = _split_text(text)
    wav_payloads = []
    for idx, chunk in enumerate(chunks, 1):
        try:
            interaction = client.interactions.create(
                model="gemini-3.8-flash-tts",
                input=[{
                    "type": "user_input",
                    "content": [{
                        "type": "text",
                        "text": chunk,
                        "annotations": [{"type": "speech_metadata", "style": style}],
                    }],
                }],
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice}]},
            )
            audio_value = interaction.output_audio.data
            audio_bytes = base64.b64decode(audio_value) if isinstance(audio_value, str) else bytes(audio_value)
            if not audio_bytes:
                raise RuntimeError("No audio bytes were returned.")
            wav_payloads.append(audio_bytes)
        except Exception as exc:
            raise RuntimeError(f"Gemini TTS failed on chunk {idx}/{len(chunks)}: {exc}") from exc
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if len(wav_payloads) == 1 and wav_payloads[0][:4] == b"RIFF":
        target.write_bytes(wav_payloads[0])
    else:
        import io
        arrays, sample_rate = [], None
        for part in wav_payloads:
            if part[:4] == b"RIFF":
                data, sr = sf.read(io.BytesIO(part), dtype="float32")
            else:
                data = np.frombuffer(part, dtype=np.int16).astype(np.float32) / 32768.0
                sr = 24000
            if sample_rate and sr != sample_rate:
                raise RuntimeError("Gemini TTS chunks returned inconsistent sample rates.")
            sample_rate = sr
            arrays.append(data.reshape(-1))
            arrays.append(np.zeros(int(sr * 0.14), dtype=np.float32))
        if arrays and len(arrays) > 1:
            arrays.pop()
        sf.write(str(target), np.concatenate(arrays), sample_rate or 24000)
    return str(target)

def synthesize_chatterbox(text: str, output_path: str | Path,
                          voice_reference: str | None = None,
                          consent_confirmed: bool = False,
                          exaggeration: float = 0.5, cfg_weight: float = 0.5):
    if voice_reference and not consent_confirmed:
        raise ValueError("Confirm that the sample is your own voice or you have permission to use it, and that you will not create a deceptive impersonation.")
    try:
        import torch
        import soundfile as sf
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except Exception as exc:
        raise RuntimeError("Chatterbox is not installed. Run the optional Chatterbox install cell in Colab, restart if asked, then try again.") from exc
    if not torch.cuda.is_available():
        raise RuntimeError("Chatterbox requires a Colab GPU in this studio. Select Runtime → Change runtime type → GPU.")
    model = None
    try:
        model = ChatterboxMultilingualTTS.from_pretrained(device=torch.device("cuda"), t3_model="v3")
        if voice_reference:
            reference = Path(voice_reference)
            if not reference.is_file():
                raise ValueError("The selected authorized voice sample is missing.")
            model.prepare_conditionals(str(reference), exaggeration=float(exaggeration))
        samples = []
        chunks = _split_text(text, 230)
        for part in chunks:
            audio = model.generate(
                part, language_id="hi", exaggeration=float(exaggeration),
                cfg_weight=float(cfg_weight), temperature=0.8,
            )
            samples.append(audio.detach().float().cpu().numpy().reshape(-1))
            if len(samples) < len(chunks):
                samples.append(np.zeros(int(model.sr * 0.12), dtype=np.float32))
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), np.concatenate(samples), int(model.sr))
        return str(out)
    finally:
        if model is not None:
            try:
                for name in ("t3", "s3gen", "ve"):
                    getattr(model, name).to("cpu")
            except Exception:
                pass
            del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def synthesize_voice(text: str, engine: str, output_path: str | Path, **settings):
    if engine == "gemini":
        return synthesize_gemini(
            text, settings.get("api_key", ""), output_path,
            settings.get("voice", "Kore"),
            settings.get("style", "Warm, natural, expressive narrator."),
        )
    if engine == "chatterbox":
        return synthesize_chatterbox(
            text, output_path,
            settings.get("voice_reference"),
            settings.get("consent_confirmed", False),
            settings.get("exaggeration", 0.5),
            settings.get("cfg_weight", 0.5),
        )
    if engine == "none":
        return None
    raise ValueError(f"Unknown voice engine: {engine}")
