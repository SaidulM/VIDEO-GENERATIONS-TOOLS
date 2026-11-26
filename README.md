# Short Story Studio — Video Generations Tools

Prompt-to-video workstation for the Short Story Speaker channel. Paste a topic or script, generate an editable storyboard, select a visual style and narration voice, preview the voice, then render a vertical MP4 with captions, an SRT file and timestamp JSON.

## Included

- FastAPI web app with prompt/script editor, optional scene notes and editable scene plan.
- LLM provider selector: OpenRouter, Groq, DeepSeek, Gemini, OpenAI and local Ollama. Exact model ID is selected by the user; no silent model switching.
- Template storyboard mode when no LLM key is configured. It is labelled as template mode.
- Pillow + FFmpeg motion-graphic renderer: cinematic, Islamic geometric, cyberpunk, clay-like, 3D-inspired and minimal themes.
- Optional Hindi Kokoro TTS with four previewable preset voices.
- Experimental Chatterbox multilingual adapter for Hindi voice-reference conditioning; optional, larger and archived upstream.
- ComfyUI API workflow submit/history endpoints for GPU-based generation on another machine or Colab.
- Drop-in prompt skills in skills/<skill-name>/SKILL.md.
- Short 9:16 and long-form 16:9 profiles. Short is primary; long is a starter profile.

> Repository contains app code, not AI checkpoint weights. Model weights are downloaded by their own runtimes. GitHub Actions tests code; it does not perform GPU inference.

## Hardware and free-tier reality

Your previously described older i3 / 8 GB laptop can run the editor and template FFmpeg motion graphics, but not modern local video diffusion or heavy voice cloning. There is no single free model that generates photorealistic video, natural Hindi voice cloning, soundtrack and edits on every computer. Hosted free tiers are rate-limited and can change.

- Kokoro-82M is the recommended lightweight local Hindi TTS start. Four fixed Hindi voices; no voice cloning.
- Chatterbox multilingual supports Hindi and reference audio, but upstream was archived in August 2026. Experimental; check checkpoint terms before monetized use.
- LTX-2.5 offers multi-shot synchronized video/audio. Code repo is Apache-2.0; weights use the LTX-2.x Community License, not OSI-approved open-source. Full bundle is about 66 GiB; standard setup recommends 80 GB VRAM, with a low-VRAM path described for 32 GB GPUs. Not suitable for the 8 GB laptop or typical free Colab T4.
- Wan2.2 14B text-to-video recipe calls for an 80 GB GPU. Smaller variants require separate evaluation.
- No provider/model is silently switched after an error.

## Windows quick start

Install Python 3.11 (64-bit), Git and FFmpeg. Double-click setup_windows.bat once, then start_windows.bat. Or use CMD:

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env.local
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. In Settings, choose a provider, enter its API key and exact model ID, then save. Keys are written to ignored local .env.local; never commit it.

For local Kokoro Hindi voice synthesis, run pip install -r requirements-tts.txt. First generation downloads model assets. Hindi pronunciation is best with Devanagari; Roman Hinglish may need review.

## Google Colab

Open notebooks/colab_studio.ipynb in Colab. It installs the lightweight application. The Colab session is temporary; download output before disconnecting. GPU runtime does not guarantee enough VRAM for LTX or Wan.

## LLM providers

| Provider | Base URL | Notes |
|---|---|---|
| OpenRouter | https://openrouter.ai/api/v1 | Free variants rate-limited; openrouter/free routes to an eligible model |
| Groq | https://api.groq.com/openai/v1 | Hosted inference; quotas/catalog change |
| DeepSeek | https://api.deepseek.com | Choose a model ID available to your account |
| Gemini | https://generativelanguage.googleapis.com/v1beta/openai/ | OpenAI-compatible endpoint |
| OpenAI | https://api.openai.com/v1 | API usage may be paid |
| Ollama | http://localhost:11434/v1 | Local server; hardware-dependent |

Enter the exact model ID currently shown in your provider dashboard.

## Voice

Kokoro preset Hindi voices: hm_omega, hm_psi, hf_alpha, hf_beta. They do not clone your voice. Chatterbox requires a reference recording you own or have permission to use. The Chatterbox adapter is experimental and upstream archived. Future hosted TTS adapters can be added without changing the renderer.

## Realistic B-roll with ComfyUI

Run ComfyUI on a suitable GPU machine or hosted GPU. Export a workflow in API format and POST its JSON to /api/comfyui/submit; check /api/comfyui/history/{prompt_id}. This endpoint queues a workflow; it does not install checkpoints or rewrite incompatible workflows. Keep ComfyUI private and trusted.

## Islamic-content safeguards

The planner must not invent Qur'an quotations, Hadith wording, verse numbers, narrator chains, rulings or historical claims. Add exact references in your script and verify them before publishing. Default visuals avoid depictions of Allah, prophets and angels; use symbolic environments, architecture, landscapes, geometry and licensed calligraphy. Review generated scripts and visuals before publishing.

## Add-on skills

Add a folder under skills/ with a SKILL.md. Restart the server; its instructions are loaded into storyboard planning. Skills are prompt instructions, not executable plugins. Included: Islamic Shorts Story Editor and Cinematic Visual Shot Designer.

## Output

Each render creates workspace/outputs/<job-id>/ with video.mp4, captions.srt, timestamps.json, storyboard.json and render_manifest.json. Workspace and secrets are git-ignored.

## Tests

    pip install -r requirements.txt
    python -m compileall -q app tests
    python -m pytest -q

## References

- Motion Canvas (MIT): https://github.com/motion-canvas/motion-canvas
- LTX-2 / LTX-2.5: https://github.com/Lightricks/LTX-2
- LTX-2.5 model card/license: https://huggingface.co/Lightricks/LTX-2.5
- Wan2.2: https://github.com/Wan-Video/Wan2.2
- Kokoro TTS: https://github.com/hexgrad/kokoro
- Chatterbox TTS, archived: https://github.com/resemble-ai/chatterbox
- Faster-Whisper: https://github.com/SYSTRAN/faster-whisper
- ComfyUI: https://github.com/Comfy-Org/ComfyUI

## License

Application code is MIT licensed. Model weights, datasets, workflows, fonts and media have separate terms. Verify them before commercial or monetized use.
