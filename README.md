# Short Story Studio — Video Generations Tools

Prompt-to-video workstation for the Short Story Speaker channel. Paste a topic or script, generate an editable storyboard, select a visual style and narration voice, preview the voice, then render a vertical MP4 with captions, an SRT file and timestamp JSON.

## Included in this first release

- FastAPI web app with prompt/script editor, optional scene notes and editable scene plan.
- LLM provider selector: OpenRouter, Groq, DeepSeek, Gemini, OpenAI and local Ollama. The exact model ID is selected by the user; no silent model switching.
- Deterministic storyboard mode when no LLM key is configured. It is labelled as template mode, not passed off as AI.
- Motion-graphic renderer based on Pillow and FFmpeg with cinematic, Islamic geometric, cyberpunk, clay-like, 3D-inspired and minimal themes.
- Optional Hindi Kokoro TTS with voice preview. Hindi voice IDs: hm_omega, hm_psi, hf_alpha, hf_beta.
- Experimental Chatterbox multilingual adapter for Hindi voice-reference conditioning; it is optional and upstream is archived.
- ComfyUI API workflow submit/history endpoints for GPU-based image/video generation on a separate machine or Colab.
- Drop-in prompt skills: add a folder with SKILL.md under skills/ and restart.
- Short 9:16 and long-form 16:9 profiles. Short is the primary workflow; long-form is a starter profile to review.

> This repository stores application code and configuration, not AI checkpoint weights. Model files are downloaded separately by their own runtimes. GitHub Actions runs tests, not GPU video inference.

## Hardware and free-tier reality

The previously described laptop (older i3, 8 GB RAM, no dedicated GPU specified) can run the lightweight editor and template-based FFmpeg motion graphics, but it is not suitable for modern local video diffusion or heavy voice cloning.

There is no single free model that reliably generates cinematic realistic video, natural Hindi voice cloning, soundtrack and final edits on every device. Hosted free tiers are rate-limited and may change. A provider API key does not mean unlimited free usage.

- Kokoro-82M is the recommended lightweight Hindi TTS starting point. It has four fixed Hindi voices and does not clone a user's voice.
- Chatterbox Multilingual supports Hindi and voice-reference conditioning, but its upstream repository was archived in August 2026. It is optional and experimental. Verify the specific checkpoint license before monetized use.
- LTX-2.5 supports native multi-shot video and synchronized audio/video. The code repository is Apache-2.0, but the weights use the LTX-2.x Community License, not an OSI-approved open-source license. The listed full model bundle is about 66 GiB. Standard configuration recommends 80 GB VRAM; the low-VRAM path is described for 32 GB GPUs. This is not a default for an 8 GB laptop or a typical free Colab T4.
- Wan2.2's 14B text-to-video recipe calls for an 80 GB GPU. Smaller variants exist but need separate evaluation.
- No model or provider is silently substituted after an error. The app reports an actionable error.

## Windows quick start

Install Python 3.11 (64-bit), Git and FFmpeg. Ensure the command ffmpeg -version works.

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    copy .env.example .env.local
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. In Settings, select a provider, enter its key and exact model ID, and save. Keys are stored in the ignored local .env.local file; never commit it.

For local Kokoro Hindi voice synthesis:

    pip install -r requirements-tts.txt

The first generation downloads model assets. Hindi pronunciation works best with Devanagari input; Roman Hinglish may need pronunciation review.

## Google Colab

Open notebooks/colab_studio.ipynb in Colab. The notebook installs the lightweight application and exposes its UI through the notebook. Colab storage is temporary; download output files before disconnecting. A GPU runtime does not guarantee enough VRAM for LTX or Wan.

## Providers

| Provider | OpenAI-compatible base URL | Notes |
|---|---|---|
| OpenRouter | https://openrouter.ai/api/v1 | Free model variants are rate-limited; openrouter/free can route to an eligible model |
| Groq | https://api.groq.com/openai/v1 | Hosted inference; quotas and models can change |
| DeepSeek | https://api.deepseek.com | Choose a model ID available to your account |
| Gemini | https://generativelanguage.googleapis.com/v1beta/openai/ | Gemini OpenAI-compatible endpoint |
| OpenAI | https://api.openai.com/v1 | API usage may be paid |
| Ollama | http://localhost:11434/v1 | Local model server; hardware-dependent |

Use the model ID currently shown in your provider dashboard. The app does not guess model IDs.

## Voice

Kokoro local voices are preset, lightweight and previewable. They do not clone a user's voice. Chatterbox is optional, much heavier, supports Hindi and reference-audio conditioning upstream, but is archived; use only a recording you own or have permission to use. A future hosted TTS adapter can be added without changing the renderer.

## Realistic B-roll with ComfyUI

Run ComfyUI on a suitable GPU machine or hosted GPU, export a workflow in API format, then call POST /api/comfyui/submit with the workflow JSON and X-ComfyUI-URL header. The endpoint submits the workflow and returns its prompt ID. Query GET /api/comfyui/history/{prompt_id}. It does not download checkpoints or rewrite incompatible workflows. Do not expose an unauthenticated ComfyUI server publicly.

## Islamic-content safeguards

The storyboard planner must not invent Qur'an quotations, Hadith wording, verse numbers, narrator chains, scholarly rulings or historical claims. Add exact references in your script and verify them before publishing. Default visuals avoid depicting Allah, prophets or angels; use symbolic environments, architecture, landscapes, geometric art and licensed calligraphy. Review script and visuals before publishing.

## Add-on skills

Create a new folder in skills/ with a SKILL.md file. The app reads installed skill text and includes it in storyboard planning. Skills are prompt instructions, not executable Python modules. Example future skills: Quran reference checking, B-roll shot design, long-form editing, subtitle styling.

## Output

Each render writes to workspace/outputs/<job-id>/:
- video.mp4
- captions.srt
- timestamps.json
- storyboard.json
- render_manifest.json

Workspace and local secrets are git-ignored.

## Tests

    pip install -r requirements.txt
    pytest -q

## Model and project references

- Motion Canvas, MIT TypeScript animation library/editor: https://github.com/motion-canvas/motion-canvas
- LTX-2 / LTX-2.5: https://github.com/Lightricks/LTX-2
- LTX-2.5 model card/license: https://huggingface.co/Lightricks/LTX-2.5
- Wan2.2: https://github.com/Wan-Video/Wan2.2
- Kokoro TTS: https://github.com/hexgrad/kokoro
- Chatterbox TTS, archived: https://github.com/resemble-ai/chatterbox
- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- ComfyUI: https://github.com/Comfy-Org/ComfyUI

## License

This application code is MIT licensed. Model weights, datasets, workflows, fonts and media assets have separate terms. Verify all terms before commercial or monetized use.
