# Finetuning Guide — AI Fashion Designer

Complete step-by-step guide to finetune all 4 AI models for the Fashion Designer system.
No thinking required — just follow each step exactly.

---

## Overview

| Model | Purpose | Base Model | Training Data | Time (Free T4) |
|-------|---------|-----------|---------------|----------------|
| Intent Classifier | Route user messages to correct agent | Llama 3.2 3B | 500 ShareGPT pairs | ~15 min |
| Design Agent | Generate outfit designs with SDXL prompts | Llama 3.2 3B | 300 pairs | ~25 min |
| Tailor Agent | Fabric/yardage/construction guides | Llama 3.2 3B | 200 pairs | ~20 min |
| Style Agent | Personalized fashion advice | Llama 3.2 3B | 200 pairs | ~20 min |

**Total time: ~80 minutes on free Google Colab T4 GPU**

---

## Prerequisites

1. **Google Account** — for Colab access (free)
2. **HuggingFace Account** — for model downloads (free, https://huggingface.co)
3. **Ollama installed locally** — for model deployment (free, https://ollama.ai)

---

## Step 1: Generate Training Data (Local — No GPU Needed)

```bash
# From the project root
cd fashion-ai

# Generate 1,200 synthetic training samples
python training/scripts/generate_synthetic_data.py

# Expected output:
# ✅ intent_classifier: 500 samples → data/synthetic/intent_classifier_train.jsonl
# ✅ design_agent: 300 samples → data/synthetic/design_agent_train.jsonl
# ✅ tailor_agent: 200 samples → data/synthetic/tailor_agent_train.jsonl
# ✅ style_agent: 200 samples → data/synthetic/style_agent_train.jsonl
# ✅ combined: 1200 samples → data/synthetic/combined_train.jsonl
```

## Step 2: Clean and Split Data (Local — No GPU Needed)

```bash
python training/scripts/data_pipeline.py

# Expected output per dataset:
# ✅ Dedup, fuzzy dedup, quality filter, toxicity filter
# ✅ Split: train (85%) / val (10%) / test (5%)
# ✅ Output: data/processed/{name}_train.jsonl, _val.jsonl, _test.jsonl
```

## Step 3: Upload Data to Google Drive

1. Go to https://drive.google.com
2. Create folder: `fashion-ai-training`
3. Upload the entire `data/processed/` directory
4. Upload the `training/configs/` directory
5. Upload `training/scripts/train_model.py`

## Step 4: Open Google Colab

1. Go to https://colab.research.google.com
2. Click **New Notebook**
3. Go to **Runtime → Change runtime type → T4 GPU**
4. Run the cells below in order:

### Cell 1: Mount Drive & Install Dependencies

```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Install Unsloth (optimized for Colab)
!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps "trl<0.9.0" peft accelerate bitsandbytes
!pip install datasets pyyaml

print("✅ Dependencies installed!")
```

### Cell 2: Copy Files from Drive

```python
import shutil
import os

# Copy training data
src = "/content/drive/MyDrive/fashion-ai-training"
dst = "/content/fashion-ai"

os.makedirs(f"{dst}/data/processed", exist_ok=True)
os.makedirs(f"{dst}/training/configs", exist_ok=True)
os.makedirs(f"{dst}/training/scripts", exist_ok=True)

# Copy processed data
for f in os.listdir(f"{src}/processed"):
    shutil.copy2(f"{src}/processed/{f}", f"{dst}/data/processed/{f}")

# Copy configs
for f in os.listdir(f"{src}/configs"):
    shutil.copy2(f"{src}/configs/{f}", f"{dst}/training/configs/{f}")

# Copy training script
shutil.copy2(f"{src}/train_model.py", f"{dst}/training/scripts/train_model.py")

print("✅ Files copied!")
print(f"Training data: {os.listdir(f'{dst}/data/processed/')}")
```

### Cell 3: Train Intent Classifier (~15 min)

```python
%cd /content/fashion-ai

!python training/scripts/train_model.py \
    --config training/configs/intent_classifier.yaml

# Expected output:
# [1/6] Loading model with Unsloth 4-bit quantization...
# [2/6] Applying LoRA adapters...
# [3/6] Loading training data...
# [4/6] Configuring SFT Trainer...
# [5/6] Starting training...
#   Loss: 0.XXXX
# [6/6] Exporting to GGUF format...
# ✅ Training complete!
```

### Cell 4: Train Design Agent (~25 min)

```python
!python training/scripts/train_model.py \
    --config training/configs/design_agent.yaml
```

### Cell 5: Train Tailor Agent (~20 min)

```python
!python training/scripts/train_model.py \
    --config training/configs/tailor_agent.yaml
```

### Cell 6: Copy Models Back to Drive

```python
import shutil

# Copy all outputs back to Drive
output_dir = "/content/fashion-ai/outputs"
drive_output = "/content/drive/MyDrive/fashion-ai-training/outputs"

if os.path.exists(output_dir):
    shutil.copytree(output_dir, drive_output, dirs_exist_ok=True)
    print("✅ Models saved to Google Drive!")
    
    # List GGUF files
    for root, dirs, files in os.walk(drive_output):
        for f in files:
            if f.endswith(".gguf"):
                path = os.path.join(root, f)
                size_mb = os.path.getsize(path) / (1024*1024)
                print(f"  📦 {f} ({size_mb:.0f} MB)")
```

## Step 5: Deploy to Ollama (Local)

### Download GGUF files from Google Drive

1. Go to Google Drive → `fashion-ai-training/outputs/`
2. Download the `*.gguf` files for each model

### Create Ollama Modelfiles

**File: `Modelfile.intent` (save locally)**
```
FROM ./intent_classifier-q4_k_m.gguf

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 300

SYSTEM """You are an intent classifier for a fashion AI assistant.
Classify messages into: greeting, design_request, product_search, style_advice,
body_scan, virtual_tryon, wardrobe_manage, tailoring, feedback, general_chat.
Respond with JSON: {"intent": "...", "confidence": 0.0-1.0, "language": "en|hi|te", "parameters": {...}}"""
```

**File: `Modelfile.design` (save locally)**
```
FROM ./design_agent-q4_k_m.gguf

PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER num_predict 800

SYSTEM """You are an expert Indian fashion designer. Create detailed outfit designs
with SDXL prompts, fabric notes, and cost estimates. Respond in JSON format."""
```

**File: `Modelfile.tailor` (save locally)**
```
FROM ./tailor_agent-q4_k_m.gguf

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_predict 1000

SYSTEM """You are a master Indian tailor. Provide detailed tailoring guides
with exact yardage, construction steps, and fabric recommendations. Respond in JSON."""
```

### Register Models with Ollama

```bash
# Create each model (run from the directory containing GGUF + Modelfile files)
ollama create fashion-intent -f Modelfile.intent
ollama create fashion-design -f Modelfile.design
ollama create fashion-tailor -f Modelfile.tailor

# Verify
ollama list

# Test
ollama run fashion-intent "Design a red lehenga for a wedding"
ollama run fashion-design "I want a blue silk saree for a corporate event"
ollama run fashion-tailor "How much fabric for a saree blouse?"
```

### Update `.env` to Use Finetuned Models

```bash
# In your .env file, update:
OLLAMA_URL=http://localhost:11434

# The backend will automatically use the finetuned Ollama models
# when Groq is unavailable or when you configure model routing.
```

## Step 6: Run Evaluation

```bash
# Back on your local machine
cd fashion-ai

# Run the full evaluation suite
python evals/evaluate_models.py --all

# Expected output:
# 📊 Evaluating Intent Classifier...
#   Accuracy: 95.0%+
#   Macro F1: 90.0%+
#
# 📊 Evaluating Design Agent Quality...
#   JSON Validity: 95.0%+
#   Completeness: 90.0%+
#
# 📊 Evaluating Tailor Agent Accuracy...
#   Yardage Plausible: 95.0%+
#
# 📊 G-EVAL Scoring...
#   Overall: 3.5+/5.0
```

## Step 7: Continuous Improvement

### Auto-Retrain Pipeline (GitHub Actions)

The project includes `.github/workflows/retrain.yml` which:
1. Triggers weekly or when new training data is pushed
2. Runs the data pipeline
3. Trains models on Colab via API (or on a self-hosted runner with GPU)
4. Runs evaluation
5. Deploys if eval metrics exceed thresholds

### Adding More Training Data

```bash
# Add real user conversations (anonymized) to augment synthetic data:
# 1. Export conversations from PostgreSQL
# 2. Anonymize (remove PII, replace names)
# 3. Convert to ShareGPT format
# 4. Add to data/raw/
# 5. Re-run pipeline:

python training/scripts/data_pipeline.py
```

### Monitoring Model Drift

The Grafana dashboards at `http://localhost:3000` track:
- Intent classification distribution over time
- Average response quality scores
- User feedback (thumbs up/down ratio)
- Latency percentiles (p50, p95, p99)

When drift is detected (>10% shift in intent distribution), the retrain pipeline triggers automatically.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `CUDA out of memory` | Reduce `per_device_train_batch_size` to 1, increase `gradient_accumulation_steps` to 16 |
| `Unsloth not found` | Re-run: `pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"` |
| `GGUF export fails` | Ensure `merge_adapters: true` in config, try q8_0 quantization first |
| `Ollama create fails` | Ensure GGUF file path is correct and file is complete (check file size) |
| `Model quality low` | Increase training epochs to 8, increase LoRA rank to 32, add more training data |
| `Training too slow` | Enable `packing: true` in data config, use bf16 instead of fp16 |
