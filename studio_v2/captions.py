from __future__ import annotations

from pathlib import Path
import json
import re
import soundfile as sf

def timestamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def _fallback_segments(text: str, duration: float) -> list[dict]:
    sentences = [x.strip() for x in re.split(r"(?<=[.!?।؟])\s+|\n+", text) if x.strip()]
    if not sentences:
        sentences = [text.strip()] if text.strip() else []
    weights = [max(1, len(x.split())) for x in sentences]
    total = sum(weights) or 1
    cursor, output = 0.0, []
    for i, (sentence, weight) in enumerate(zip(sentences, weights)):
        end = duration if i == len(sentences) - 1 else cursor + duration * weight / total
        output.append({"start": cursor, "end": end, "text": sentence})
        cursor = end
    return output

def transcribe_or_estimate(audio_path: str | Path | None, text: str, use_whisper: bool = True) -> tuple[list[dict], float, str]:
    duration = 0.0
    if audio_path and Path(audio_path).is_file():
        duration = float(sf.info(str(audio_path)).duration)
    if use_whisper and audio_path:
        try:
            from faster_whisper import WhisperModel
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            model = WhisperModel("tiny", device=device, compute_type=compute_type)
            segments, _ = model.transcribe(
                str(audio_path), beam_size=1, word_timestamps=True,
                vad_filter=True, language=None,
            )
            result = []
            for segment in segments:
                words = getattr(segment, "words", None) or []
                if words:
                    for offset in range(0, len(words), 5):
                        group = words[offset:offset + 5]
                        phrase = "".join(w.word for w in group).strip()
                        if phrase:
                            result.append({"start": float(group[0].start), "end": float(group[-1].end), "text": phrase})
                elif segment.text.strip():
                    result.append({"start": float(segment.start), "end": float(segment.end), "text": segment.text.strip()})
            if result:
                return result, duration or max(x["end"] for x in result), "faster-whisper tiny (word-timestamp mode)"
            note = "Whisper returned no words; using estimated sentence timings."
        except Exception as exc:
            note = f"Whisper timing unavailable; using estimated sentence timings ({exc})."
    else:
        note = "Sentence-level estimated timings; install faster-whisper for audio-aligned captions."
    duration = duration or max(
        3.0,
        sum(max(1, len(x.split())) for x in re.split(r"(?<=[.!?।؟])\s+", text) if x) / 2.7,
    )
    return _fallback_segments(text, duration), duration, note

def write_srt(segments: list[dict], path: str | Path) -> str:
    rows = []
    for idx, seg in enumerate(segments, 1):
        rows.append(f"{idx}\n{timestamp(seg['start'])} --> {timestamp(seg['end'])}\n{seg['text']}\n")
    Path(path).write_text("\n".join(rows), encoding="utf-8")
    return str(path)

def write_timestamps(segments: list[dict], duration: float, path: str | Path) -> str:
    payload = {
        "duration_seconds": round(duration, 3),
        "segments": [
            {"index": i, "start_seconds": round(x["start"], 3), "end_seconds": round(x["end"], 3), "text": x["text"]}
            for i, x in enumerate(segments, 1)
        ],
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)
