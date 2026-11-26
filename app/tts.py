from __future__ import annotations

from pathlib import Path
import gc
import re

_CHATTERBOX_MODEL = None
_CHATTERBOX_DEVICE = None


def voice_catalog():
    """Small UI catalog; checkpoint weights are intentionally not imported here."""
    try:
        import chatterbox  # noqa: F401
        installed = True
    except Exception:
        installed = False
    return [
        {
            "id": "chatterbox-v3",
            "label": "Chatterbox Multilingual V3 — built-in Hindi voice",
            "engine": "chatterbox",
            "installed": installed,
            "cloning": False,
            "languages": 23,
        },
        {
            "id": "reference",
            "label": "Chatterbox V3 — clone my authorized voice sample",
            "engine": "chatterbox",
            "installed": installed,
            "cloning": True,
            "languages": 23,
        },
        {
            "id": "none",
            "label": "No narration — captions only",
            "engine": "none",
            "installed": True,
            "cloning": False,
        },
    ]


def _text_chunks(text: str, max_chars: int = 250) -> list[str]:
    """Split long narration into natural chunks so TTS VRAM use stays bounded."""
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
        part, text = text[:cut].strip(), text[cut:].strip()
        if part:
            chunks.append(part)
    if text:
        chunks.append(text)
    return chunks


def load_chatterbox(device: str = "cuda"):
    """Load Chatterbox V3 lazily and retain only one model instance."""
    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    try:
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except Exception as exc:
        raise RuntimeError(
            "Chatterbox is not installed. In a fresh Colab GPU runtime run: "
            "pip install -r requirements-colab.txt"
        ) from exc

    if device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError(
            "This lightweight profile runs Chatterbox on a CUDA GPU, not on an older CPU-only laptop. "
            "Open the Colab notebook and select a GPU runtime. You can still render motion graphics locally."
        )

    if _CHATTERBOX_MODEL is not None and _CHATTERBOX_DEVICE == device:
        return _CHATTERBOX_MODEL
    if _CHATTERBOX_MODEL is not None:
        unload_chatterbox()

    try:
        _CHATTERBOX_MODEL = ChatterboxMultilingualTTS.from_pretrained(
            device=torch.device(device),
            t3_model="v3",
        )
        _CHATTERBOX_DEVICE = device
        return _CHATTERBOX_MODEL
    except Exception as exc:
        _CHATTERBOX_MODEL = None
        _CHATTERBOX_DEVICE = None
        torch.cuda.empty_cache()
        raise RuntimeError(
            "Chatterbox V3 could not load its model files. Check internet access, Colab GPU allocation "
            "and available GPU RAM."
        ) from exc


def unload_chatterbox():
    """Remove the TTS model from GPU memory before optional video diffusion runs."""
    global _CHATTERBOX_MODEL, _CHATTERBOX_DEVICE
    model = _CHATTERBOX_MODEL
    _CHATTERBOX_MODEL = None
    _CHATTERBOX_DEVICE = None
    if model is not None:
        try:
            for attribute in ("t3", "s3gen", "ve"):
                module = getattr(model, attribute, None)
                if module is not None:
                    module.to("cpu")
            conditionals = getattr(model, "conds", None)
            if conditionals is not None:
                conditionals.to("cpu")
            model.device = "cpu"
        except Exception:
            pass
        del model
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


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

    reference_path = None
    if voice_reference:
        reference_path = Path(voice_reference)
        if not reference_path.is_file():
            raise ValueError("The selected voice reference file was not found. Upload it again.")

    try:
        import numpy as np
        import soundfile as sf
        import torch
    except Exception as exc:
        raise RuntimeError(
            "Chatterbox runtime dependencies are missing. Use the Colab notebook and install requirements-colab.txt."
        ) from exc

    selected_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = load_chatterbox(selected_device)
    try:
        if reference_path is not None:
            try:
                model.prepare_conditionals(
                    str(reference_path),
                    exaggeration=float(exaggeration),
                )
            except Exception as exc:
                raise RuntimeError(
                    "Could not read the voice sample. Use a clean 5–10 second, single-speaker WAV/MP3/M4A recording."
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
                raise RuntimeError(
                    f"Chatterbox failed on narration chunk {index + 1}/{len(chunks)}: {exc}"
                ) from exc
            samples = (
                wav.detach().float().cpu().numpy().reshape(-1)
                if hasattr(wav, "detach")
                else np.asarray(wav).reshape(-1)
            )
            if samples.size:
                audio_parts.append(samples.astype(np.float32))
                if index < len(chunks) - 1:
                    audio_parts.append(np.zeros(int(model.sr * 0.12), dtype=np.float32))

        if not audio_parts:
            raise RuntimeError("Chatterbox returned no audio.")
        audio = np.concatenate(audio_parts)
        sample_rate = int(model.sr)
        sf.write(str(target), audio, sample_rate)
        return {
            "path": str(target),
            "sample_rate": sample_rate,
            "engine": "chatterbox-v3",
            "voice": "reference" if reference_path else "built-in",
            "chunks": len(chunks),
            "device": selected_device,
        }
    finally:
        unload_chatterbox()


def preview_voice(
    text: str,
    output_path: str | Path,
    voice_reference: str | None = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    temperature: float = 0.8,
):
    preview_text = (text.strip() or "Assalamu alaikum. Aaj ki kahani mein ek aham sabaq hai.")[:250]
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
        device="cuda",
    )
