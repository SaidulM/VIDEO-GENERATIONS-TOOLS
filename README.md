# Short Story Studio — Video Generations Tools

A **Colab-first, low-cost creator workspace** for Short Story Speaker. Enter a topic or paste your Hinglish script, create an editable scene plan, preview the voice, choose a visual style, render a YouTube Short and export MP4/SRT/timestamps.

## The lightweight setup

| Task | Engine | Where it runs |
|---|---|---|
| Script/storyboard | OpenRouter, Groq, Gemini, DeepSeek, OpenAI or template mode | Cloud API or CPU |
| Hindi narration / voice cloning | Chatterbox Multilingual V3 (500M) | Colab GPU recommended |
| AI visual clips | AnimateDiff-Lightning 4-step + Stable Diffusion 1.5 | Colab GPU, optional |
| Motion graphics and final assembly | Pillow + FFmpeg | CPU laptop or Colab |
| Subtitles and timestamp export | Python/SRT | CPU laptop or Colab |

No LTX-2.5, Wan 2.2 14B, or other 20B+ video model is installed. There are no model weights in this Git repository. Checkpoints download to the Colab runtime only when an optional model is used; they are not added to GitHub or your laptop.

## Important hardware truth

The older laptop previously described (i3, 8 GB RAM, no dedicated GPU) can run the editor, storyboard templates, motion-card renderer, captions and FFmpeg assembly. It is **not suitable for AnimateDiff diffusion inference or practical Chatterbox voice cloning**. Chatterbox can technically run on CPU but will be very slow.

Use Google Colab for the optional GPU tasks. Free Colab GPU allocation is not guaranteed; hardware and usage limits vary. If a GPU is not assigned, the notebook still runs the CPU motion-graphics workflow. If a model runs out of memory, reduce the number of generated scenes or use motion cards. The app never silently switches an AI-video request to template cards.

### Colab workflow

1. Open the notebook: [Launch Short Story Studio in Google Colab](https://colab.research.google.com/github/SaidulM/VIDEO-GENERATIONS-TOOLS/blob/main/notebooks/colab_studio.ipynb).
2. Run the setup cells. Select Runtime → Change runtime type → T4 GPU only if Google makes one available.
3. Optionally mount Google Drive so your uploaded voice samples and finished MP4/SRT files persist.
4. Install optional AI packages in the notebook. Checkpoints remain in the temporary Colab VM and load on first use.
5. Use the notebook-native controls: script, storyboard, scene editor, voice preview, visual style, AI video selection and export.

The notebook does **not** run a separate web server. Google documents restrictions on using free managed runtimes as general-purpose web hosting and on creating deepfakes. Only use voice-reference generation for your own voice or a voice you have permission to use, and only where the platform rules allow that use. Do not generate deceptive impersonations.

## AI voice: Chatterbox Multilingual V3

- 500M-parameter multilingual TTS model with Hindi support and reference-audio voice cloning.
- Preview narration before final rendering.
- Expression, guidance and temperature controls are exposed in the interface.
- Use a clean, single-speaker 5–10 second recording in WAV/MP3/M4A/FLAC/OGG for voice cloning. A built-in speaker can be used without uploading a reference.
- The Chatterbox upstream project has been marked as retired research/no longer maintained. The code is MIT-licensed, but check the exact model card and terms before monetized use.
- The built-in voice is not a clone of the user. A custom voice clone requires an authorized reference recording.

Install only in Colab or a suitable GPU environment:

    pip install -r requirements-colab.txt

The model loads only when you preview or render voice. The renderer releases its TTS model from GPU memory before moving on to AI video generation.

## AI footage: AnimateDiff-Lightning

The optional AI footage path uses:

- Stable Diffusion 1.5 as the base image model.
- ByteDance AnimateDiff-Lightning 4-step motion adapter (about 908 MB).
- Diffusers for loading and inference.
- FFmpeg for scene assembly and narration muxing.

This is much smaller than the 66 GiB LTX-2.5 bundle, but it still downloads several GB of weights into the Colab runtime. The current preset is designed for a CUDA GPU with about 12 GB or more VRAM. It creates short clips per scene, not a full-length single-pass video. Expect occasional flicker or imperfect motion and review each scene. AI footage is optional; CPU motion graphics do not download any video model.

License note: Stable Diffusion 1.5 and AnimateDiff-Lightning use CreativeML OpenRAIL-M terms, not MIT. Review those terms before publishing or monetizing generated outputs.

## Windows CPU quick start

Install Python 3.11 (64-bit), Git and FFmpeg. Double-click setup_windows.bat once, then start_windows.bat.

Or use CMD:

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env.local
    uvicorn app.main:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. The local app is designed for CPU editing and motion graphics. Select No narration on an older CPU-only laptop. Chatterbox/AnimateDiff controls are optional and need a supported GPU environment.

## LLM providers

The local app and Colab notebook support OpenRouter, Groq, DeepSeek, Gemini, OpenAI and local Ollama in the web app. Exact model IDs are configurable. For hosted providers, enter the API key and model ID shown in that provider's dashboard. Free quotas and model catalogs can change; an API key does not guarantee unlimited free generation.

| Provider | OpenAI-compatible base URL |
|---|---|
| OpenRouter | https://openrouter.ai/api/v1 |
| Groq | https://api.groq.com/openai/v1 |
| DeepSeek | https://api.deepseek.com |
| Gemini | https://generativelanguage.googleapis.com/v1beta/openai/ |
| OpenAI | https://api.openai.com/v1 |
| Ollama | http://localhost:11434/v1 |

Keys saved from the local UI go to the git-ignored .env.local file. Never commit secrets to GitHub.

## Visual styles

Cinematic documentary, Islamic geometry, cyberpunk, clay-like, 3D-inspired and minimal editorial. These styles change the prompt direction and motion-card palette. AI-video results depend on model output; the style name is not a guarantee of a particular level of realism.

## Add-on skills

Add a folder under skills/ with a SKILL.md. The planner includes installed skill instructions when it creates an LLM storyboard. Skills are prompt instructions, not arbitrary executable Python plug-ins. Included skills:
- Islamic Shorts Story Editor
- Cinematic Visual Shot Designer

## Islamic-content safeguards

The planner must not invent Qur'an quotations, Hadith wording, verse numbers, narrator chains, rulings or historical claims. Add exact references in your script and verify them before publishing. Default visual guidance avoids depicting Allah, prophets or angels; use symbolic environments, architecture, landscapes, geometry and licensed calligraphy. Review generated scripts, captions and visuals before publishing.

## Output files

Each render creates workspace/outputs/<job-id>/ with:
- video.mp4
- captions.srt
- timestamps.json
- storyboard.json
- render_manifest.json

The Colab notebook optionally copies outputs and voice profiles into Google Drive. Colab's temporary runtime may disconnect; download/export files before it ends.

## Tests

    pip install -r requirements.txt
    python -m compileall -q app tests
    python -m pytest -q

GitHub Actions checks Python compilation and tests. GitHub Actions is not a free GPU video-rendering server.

## Upstream projects and model references

- Chatterbox (MIT code; Hindi multilingual V3): https://github.com/resemble-ai/chatterbox
- Chatterbox Hindi model card: https://huggingface.co/ResembleAI/Chatterbox-Multilingual-hi
- AnimateDiff-Lightning (CreativeML OpenRAIL-M): https://huggingface.co/ByteDance/AnimateDiff-Lightning
- AnimateDiff official implementation: https://github.com/guoyww/AnimateDiff
- Diffusers: https://github.com/huggingface/diffusers
- Stable Diffusion 1.5 model card: https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5
- FFmpeg: https://ffmpeg.org/

## License

This application's source code is MIT licensed. Chatterbox, Stable Diffusion, AnimateDiff and any downloaded checkpoints have separate licenses and terms. Follow each model's terms.
