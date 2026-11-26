# V2 architecture

## Design goal
Notebook-native, on-demand Colab session. No persistent web server and no large video diffusion checkpoint in the default path.

## Production pipeline
1. LLM adapter or keyless script splitter produces an editable storyboard.
2. Each scene has narration, on-screen text, visual direction and a searchable stock-footage phrase.
3. Pexels or Pixabay can return candidate video clips. The creator selects one clip per scene; approved assets are downloaded with source/creator references saved in the project manifest.
4. Voice adapter creates a preview and final narration (Gemini TTS hosted service or optional Chatterbox V3 on a Colab GPU).
5. Faster-Whisper optionally produces word-group timestamp captions; sentence-level estimated timing remains the keyless fallback.
6. The composition builder writes timed HTML with CSS and GSAP; HyperFrames lints it and renders an MP4.
7. The dashboard previews the MP4 and exports SRT, timestamp JSON, storyboard JSON and the render manifest.

## UI/runtime
- ipywidgets and embedded CSS create dashboard panels inside Colab.
- Keys live only in the running Python kernel memory.
- Colab Drive mount is optional for output persistence.
- All external calls are explicit and errors are displayed. No automatic model/provider switching.
- Chatterbox, Whisper and large browser assets are installed only when requested.

## Provider adapters
- LLM: OpenRouter, Groq, Gemini, Cloudflare Workers AI, DeepSeek, xAI, OpenAI and any OpenAI-compatible endpoint.
- Stock clips: Pexels and Pixabay.
- TTS: Gemini 3.8 Flash TTS and Chatterbox V3.
- Renderer: HyperFrames CLI (Apache-2.0) plus HTML/CSS/GSAP and FFmpeg.

## Important scope
The free-first pipeline generates motion graphics and edits real stock footage. It does not claim that stock clips or code animations are photorealistic AI-generated text-to-video. A separate AI video model backend can be added only when a reliable free/credit budget or a dedicated GPU runtime is selected.
