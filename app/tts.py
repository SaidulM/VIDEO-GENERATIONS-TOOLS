from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re


def voice_catalog():
    try:
        import chatterbox  # noqa: F401
        installed = True
    except Exception:
        installed = False
    return [
        {
            "id": "chatterbox-v3",
            "label": "Chatterbox Multilingual V3 — Hindi",
            "engine": "chatterbox",
            "installed": installed,
            "cloning": True,
            "languages": 23,
            "note": "Upload a voice sample you own to clone it, or use the built-in speaker.",
        },
        {
            "id": "none",
            "label": "No narration — captions only",
            "engine": "none",
            "installed": True,
            "cloning": False,
        },
    ]


_CHATTERBOX_MODEL = None
_CHATTERBOX_DEVICE = None


def load_chatterbox(device: str = "cuda"):
    """Load Chatterbox only when requested; cache it for the current process."""
    try:
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except Exception as exc:
        raise RuntimeError(
            "Chatterbox is not installed in this runtime. In Colab run: pip install -r requirements-colab.txt"
        ) from exc

    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "No CUDA GPU is available. Use a Colab GPU runtime for Chatterbox, or choose No narration. "
            "CPU inference is possible but very slow on an older laptop."
        )
    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    selected = torch.device(device)
    if _CHATTERBOX_MODEL is not None and _CHATTERBOX_DEVICE == device:
        return _CHATTERBOX_MODEL
    if _CHATTERBOX_MODEL is not None:
        unload_chatterbox()
    try:
        _CHATTERBOX_MODEL = ChatterboxMultilingualTTS.from_pretrained(device=selected, t3_model="v3")
        _CHATTERBOX_DEVICE = device
        return _CHATTERBOX_MODEL
    except Exception as exc:
        _CHATTERBOX_MODEL = None
        _CHATTERBOX_DEVICE = None
        raise RuntimeError(
            "Chatterbox V3 could not load its model assets. Check the Colab GPU, internet access and available RAM/VRAM."
        ) from exc


def _text_chunks(text: str, max_chars: int = 260) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise ValueError("Narration text is empty.")
    chunks: list[str] = []
    while len(text) > max_chars:
        cut = max(text.rfind(mark, 0, max_chars) for mark in (".", "?", "!", ",", "।", " "))
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        part = text[:cut].strip()
        if part:
            chunks.append(part)
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks


def synthesize(
    text: str,
    output_path: str | Path,
    engine: str = "chatterbox",
    voice_id: str = "chatterbox-v3",
    language: str = "hi",
    voice_reference: str | None = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    temperature: float = 0.8,
    device: str | None = None,
):
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if engine == "none":
        return None
    if engine not in {"chatterbox", "chatterbox-v3"}:
        raise ValueError("Unsupported voice engine. Choose Chatterbox V3 or No narration.")

    import numpy as np
    import soundfile as sf
    import torch

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = load_chatterbox(selected_device)

    # The selected reference must belong to the user or be explicitly licensed/authorized.
    if voice_reference:
        reference = Path(voice_reference)
        if not reference.is_file():
            raise ValueError("The selected voice reference file was not found. Upload it again.")
        try:
            model.prepare_conditionals(str(reference), exaggeration=float(exaggeration))
        except Exception as exc:
            raise RuntimeError(
                "Could not read the voice sample. Use a clean 5–10 second WAV/MP3 recording with one speaker."
            ) from exc

    chunks = _text_chunks(text)
    audio_parts = []
    for index, part in enumerate(chunks):
        try:
            wav = model.generate(
                part,
                language_id=language,
                exaggeration=float(exaggeration),
                cfg_weight=float(cfg_weight),
                temperature=float(temperature),
            )
        except Exception as exc:
            raise RuntimeError(f"Chatterbox failed while generating narration chunk {index + 1}/{len(chunks)}: {exc}") from exc
        samples = wav.detach().float().cpu().numpy().reshape(-1) if hasattr(wav, "detach") else np.asarray(wav).reshape(-1)
        if samples.size:
            audio_parts.append(samples.astype(np.float32))
            if index < len(chunks) - 1:
                audio_parts.append(np.zeros(int(model.sr * 0.12), dtype=np.float32))

    if not audio_parts:
        raise RuntimeError("Chatterbox returned no audio.")
    audio = np.concatenate(audio_parts)
    sf.write(str(target), audio, int(model.sr))
    unload_chatterbox()
    return {
        "path": str(target),
        "sample_rate": int(model.sr),
        "engine": "chatterbox-v3",
        "voice": "reference" if voice_reference else "built-in",
        "chunks": len(chunks),
        "device": selected_device,
    }


def unload_chatterbox():
    """Release the cached TTS model from GPU memory after preview/render."""
    global _CHATTERBOX_MODEL
    model = _CHATTERBOX_MODEL
    if model is None:
        return
    try:
        for name in ("t3", "s3gen", "ve"):
            module = getattr(model, name, None)
            if module is not None:
                module.to("cpu")
        conditionals = getattr(model, "conds", None)
        if conditionals is not None:
            conditionals.to("cpu")
        model.device = "cpu"
    except Exception:
        pass
    _CHATTERBOX_MODEL = None
    try:
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def preview_voice(
    text: str,
    output_path: str | Path,
    voice_reference: str | None = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    temperature: float = 0.8,
):
    preview_text = text.strip()[:260] or "Assalamu alaikum. Aaj ki kahani mein ek aham sabaq hai."
    return synthesize(
        preview_text,
        output_path,
        engine="chatterbox",
        voice_id="chatterbox-v3",
        language="hi",
        voice_reference=voice_reference,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        temperature=temperature,
    )
