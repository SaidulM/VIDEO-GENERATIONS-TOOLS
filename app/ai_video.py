from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile


BASE_MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
MOTION_REPO = "ByteDance/AnimateDiff-Lightning"
MOTION_FILE = "animatediff_lightning_4step_diffusers.safetensors"

STYLE_PROMPTS = {
    "cinematic": "cinematic documentary footage, natural lighting, realistic textures, anamorphic composition",
    "islamic_geometry": "cinematic footage, intricate Islamic geometric architecture, arabesque patterns, no people, respectful non-figurative symbolism",
    "cyberpunk": "cyberpunk cinematic scene, neon reflections, futuristic atmosphere, volumetric lighting",
    "clay": "claymation stop-motion aesthetic, handcrafted clay materials, soft studio lighting",
    "3d": "high-quality 3D animated film aesthetic, detailed materials, cinematic lighting",
    "minimal": "minimal editorial cinematic footage, elegant composition, restrained palette, natural motion",
}


def gpu_status():
    try:
        import torch
        available = bool(torch.cuda.is_available())
        if not available:
            return {"available": False, "device": "CPU", "vram_gb": 0.0}
        props = torch.cuda.get_device_properties(0)
        return {
            "available": True,
            "device": props.name,
            "vram_gb": round(props.total_memory / (1024 ** 3), 2),
        }
    except Exception:
        return {"available": False, "device": "PyTorch not installed", "vram_gb": 0.0}


@lru_cache(maxsize=1)
def _load_animatediff_pipeline():
    import torch
    from diffusers import AnimateDiffPipeline, EulerDiscreteScheduler, MotionAdapter
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file

    status = gpu_status()
    if not status["available"]:
        raise RuntimeError("AnimateDiff-Lightning needs a CUDA GPU. Switch to Colab GPU; do not try this on your CPU-only laptop.")
    if status["vram_gb"] < 12:
        raise RuntimeError(
            f"Detected {status['vram_gb']} GB VRAM. This preset is designed for a 12 GB+ GPU; "
            "use CPU motion graphics or a higher-memory Colab GPU."
        )

    dtype = torch.float16
    adapter = MotionAdapter()
    checkpoint = hf_hub_download(repo_id=MOTION_REPO, filename=MOTION_FILE)
    state = load_file(checkpoint, device="cpu")
    adapter.load_state_dict(state)
    adapter.to(dtype=dtype)

    pipe = AnimateDiffPipeline.from_pretrained(
        BASE_MODEL,
        motion_adapter=adapter,
        torch_dtype=dtype,
        use_safetensors=True,
    )
    pipe.scheduler = EulerDiscreteScheduler.from_config(
        pipe.scheduler.config,
        timestep_spacing="trailing",
        beta_schedule="linear",
    )
    pipe.enable_vae_slicing()
    pipe.enable_attention_slicing()
    # Accelerate moves modules on demand to fit a modest Colab GPU.
    pipe.enable_model_cpu_offload()
    return pipe


def generate_scene_clip(
    prompt: str,
    output_path: str | Path,
    style: str = "cinematic",
    seed: int = 42,
    frames: int = 16,
):
    """Generate a short portrait AI clip using AnimateDiff-Lightning 4-step."""
    if not prompt.strip():
        raise ValueError("A visual prompt is required for AI footage.")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    import torch
    pipe = _load_animatediff_pipeline()
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["cinematic"])
    full_prompt = (
        f"{prompt.strip()}, {style_prompt}, coherent camera movement, consistent subject, "
        "no text, no watermark, high visual quality"
    )
    generator = torch.Generator(device="cpu").manual_seed(int(seed))
    try:
        result = pipe(
            prompt=full_prompt,
            negative_prompt="text, watermark, logo, deformed, flicker, duplicate subject, distorted anatomy",
            height=640,
            width=384,
            num_frames=max(8, min(int(frames), 16)),
            num_inference_steps=4,
            guidance_scale=1.0,
            generator=generator,
        )
    except torch.cuda.OutOfMemoryError as exc:
        torch.cuda.empty_cache()
        raise RuntimeError(
            "AnimateDiff ran out of GPU memory. Reduce scene count or switch to CPU motion graphics. "
            "The app will not silently replace AI footage with a template."
        ) from exc

    clip_frames = result.frames[0]
    ffmpeg = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    work = Path(tempfile.mkdtemp(prefix="animatediff-", dir=str(output.parent)))
    try:
        for index, frame in enumerate(clip_frames):
            frame.save(work / f"frame_{index:05d}.png")
        command = [
            ffmpeg, "-y", "-framerate", "8", "-i", str(work / "frame_%05d.png"),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output),
        ]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=240)
        if proc.returncode != 0:
            raise RuntimeError("Could not encode AnimateDiff frames: " + proc.stderr[-1000:])
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return {"path": str(output), "frames": len(clip_frames), "fps": 8, "model": "AnimateDiff-Lightning 4-step"}
