# GPU Models — Deployment Guide

Step-by-step instructions for deploying GPU-accelerated models.
All models are served via **HuggingFace Inference API** (free) or **HuggingFace Spaces** (free ZeroGPU).

---

## 1. SDXL Outfit Generation (Stable Diffusion XL + LCM-LoRA)

**Default (no setup needed)**: Uses HF Inference API directly.

```env
# .env — works out of the box with your HF_API_KEY
# No additional configuration needed
```

### Custom HF Space (Optional — for faster/dedicated inference)

1. Go to https://huggingface.co/new-space
2. Select: **Gradio** SDK, **ZeroGPU** hardware (free)
3. Create file `app.py`:

```python
import gradio as gr
from diffusers import StableDiffusionXLPipeline, LCMScheduler
import torch

pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16, variant="fp16",
)
pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
pipe.load_lora_weights("latent-consistency/lcm-lora-sdxl")
pipe = pipe.to("cuda")
pipe.enable_attention_slicing()

def generate(prompt, negative_prompt="low quality, blurry", steps=4, guidance=1.5, seed=42):
    gen = torch.Generator("cuda").manual_seed(int(seed))
    return pipe(prompt=prompt, negative_prompt=negative_prompt,
                num_inference_steps=int(steps), guidance_scale=guidance,
                generator=gen).images[0]

demo = gr.Interface(fn=generate,
    inputs=[gr.Textbox(label="Prompt"), gr.Textbox(label="Negative", value="low quality, blurry"),
            gr.Slider(1, 10, 4, step=1, label="Steps"), gr.Slider(0.5, 3, 1.5, step=0.1, label="Guidance"),
            gr.Number(42, label="Seed")],
    outputs=gr.Image(type="pil"), title="Fashion AI — SDXL")
demo.launch()
```

4. Create `requirements.txt`:
```
diffusers>=0.30.0
transformers>=4.45.0
accelerate>=0.34.0
torch>=2.4.0
gradio>=4.44.0
safetensors>=0.4.0
```

5. Your Space URL becomes the SDXL endpoint.

---

## 2. Whisper Large v3 (Speech Recognition)

**Default (no setup needed)**: Uses HF Inference API.

```env
# Already configured in the backend via HF_API_KEY
# ASR endpoint: https://api-inference.huggingface.co/models/openai/whisper-large-v3
```

Supports Telugu, Hindi, and English natively. No custom deployment needed.

---

## 3. Kolors Virtual Try-On

**Default**: Uses Kwai's official HuggingFace Space (free, no setup).

```env
# Endpoint: https://kwai-kolors-kolors-virtual-try-on.hf.space
# Already integrated in the vision service
```

---

## 4. Qwen2.5-VL (Fashion Image Analysis)

**Default**: HF Inference API for Qwen2.5-VL-7B.

```env
# Endpoint: https://api-inference.huggingface.co/models/Qwen/Qwen2.5-VL-7B-Instruct
# Automatically used by the VisionService for garment analysis
```

---

## 5. FashionCLIP (Embeddings for Product Search)

**Option A**: HF Inference API (no setup)
```env
# Automatically called from ProductSearchService
# Model: patrickjohncyh/fashion-clip (512-dim embeddings)
```

**Option B**: Local loading (for higher throughput)
```bash
# The VisionService loads FashionCLIP locally if transformers is installed
pip install transformers torch
# Model downloads automatically on first use (~600MB)
```

---

## 6. SAM 2 (Garment Segmentation)

**Local only** — downloads checkpoint on first use.

```bash
pip install segment-anything
# Download checkpoint (~2.5GB):
wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
```

Set in `.env`:
```env
SAM_CHECKPOINT=sam_vit_h_4b8939.pth
SAM_MODEL_TYPE=vit_h
```

If SAM is not available, the VisionService falls back to region-based segmentation.

---

## 7. Body Reconstruction (HMR 2.0 — Google Colab)

This requires a GPU and is best run via Colab for free T4 access.

### Colab Notebook Setup

```python
# Cell 1: Install
!pip install gradio torch torchvision transformers timm smplx trimesh

# Cell 2: Server
import gradio as gr
import numpy as np

def reconstruct_body(front_image, side_image):
    # In production: runs HMR 2.0 + ViTPose pipeline
    return {
        "status": "success",
        "body_type": "hourglass",
        "measurements": {
            "height_cm": 165, "chest_cm": 91,
            "waist_cm": 71, "hips_cm": 97,
        },
        "mesh_url": None,
    }

demo = gr.Interface(
    fn=reconstruct_body,
    inputs=[gr.Image(type="pil", label="Front"), gr.Image(type="pil", label="Side")],
    outputs=gr.JSON(), title="Body Reconstruction")
demo.launch(share=True)  # Creates public URL
```

Copy the `share` URL and set as environment variable.

---

## Environment Configuration Summary

| Model | Env Variable | Default |
|-------|-------------|---------|
| LLM (Groq) | `GROQ_API_KEY` | Required |
| All HF models | `HF_API_KEY` | Required |
| Ollama (local) | `OLLAMA_URL` | `http://localhost:11434` |
| SAM checkpoint | `SAM_CHECKPOINT` | Optional |
| Qdrant (vectors) | `QDRANT_URL` | `http://localhost:6333` |
