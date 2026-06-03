# 🚀 MASTER DEPLOYMENT GUIDE — AI Fashion Designer

**Follow these steps in exact order. Each step has the exact commands to run. No thinking required.**

---

## TABLE OF CONTENTS

| Phase | What | Time |
|-------|------|------|
| [Phase 1](#phase-1--prerequisites) | Install prerequisites | 15 min |
| [Phase 2](#phase-2--get-free-api-keys) | Get free API keys (no credit card) | 10 min |
| [Phase 3](#phase-3--configure-environment) | Configure `.env` file | 5 min |
| [Phase 4](#phase-4--run-locally-with-docker) | Run full stack locally with Docker | 5 min |
| [Phase 5](#phase-5--verify-everything-works) | Smoke test all endpoints | 5 min |
| [Phase 6](#phase-6--generate-training-data) | Generate & clean finetuning data | 2 min |
| [Phase 7](#phase-7--finetune-models-on-colab) | Finetune 4 models on free Colab T4 | 80 min |
| [Phase 8](#phase-8--deploy-finetuned-models-to-ollama) | Deploy GGUF models to Ollama | 10 min |
| [Phase 9](#phase-9--run-evaluation) | Evaluate model quality | 2 min |
| [Phase 10](#phase-10--deploy-to-production) | Deploy backend to Render (free) | 15 min |
| [Phase 11](#phase-11--deploy-databases) | Set up Supabase + Qdrant Cloud (free) | 10 min |
| [Phase 12](#phase-12--build-flutter-app) | Build Flutter mobile APK | 10 min |
| [Phase 13](#phase-13--post-deployment-setup) | Monitoring, analytics, keep-alive | 10 min |

**Total: ~3 hours from zero to fully deployed**

---

## PHASE 1 — Prerequisites

Install these tools on your machine. Skip any you already have.

### 1.1 Docker Desktop
```
Download: https://docs.docker.com/get-docker/
→ Install → Restart machine → Open Docker Desktop → Wait for "Docker is running"
```

### 1.2 Python 3.11+
```
Download: https://www.python.org/downloads/
→ Install → ☑ Check "Add to PATH" during setup
→ Verify: python --version
```

### 1.3 Git
```
Download: https://git-scm.com/downloads
→ Verify: git --version
```

### 1.4 Flutter 3.x (for mobile app — optional if you only want the backend)
```
Download: https://docs.flutter.dev/get-started/install
→ Follow the platform-specific instructions
→ Verify: flutter doctor
```

### 1.5 Node.js 18+ (for WebSocket testing tool)
```
Download: https://nodejs.org/
→ Verify: node --version
```

### 1.6 Ollama (for local LLM — optional but recommended)
```
Download: https://ollama.ai/download
→ Install → Verify: ollama --version
→ Pull a base model: ollama pull llama3.2:3b
```

---

## PHASE 2 — Get Free API Keys

**All free. No credit card required for any of these.**

### 2.1 Groq API Key (Primary LLM — 394 tokens/sec, free)
```
1. Go to https://console.groq.com
2. Sign up with Google/GitHub
3. Go to "API Keys" → "Create API Key"
4. Copy the key (starts with gsk_...)
5. Save it — you'll paste it in Phase 3
```

### 2.2 HuggingFace API Token (AI models — free)
```
1. Go to https://huggingface.co/join
2. Create account
3. Go to https://huggingface.co/settings/tokens
4. Click "New token" → Name: "fashion-ai" → Type: "Read"
5. Copy the token (starts with hf_...)
6. Save it — you'll paste it in Phase 3
```

### 2.3 (OPTIONAL) Langfuse — LLM observability (free, 50K traces/month)
```
1. Go to https://langfuse.com → Sign up
2. Create a project → Go to Settings → API Keys
3. Copy Public Key and Secret Key
```

### 2.4 (OPTIONAL) PostHog — Analytics (free, 1M events/month)
```
1. Go to https://posthog.com → Sign up
2. Create project → Go to Settings → Project API Key
3. Copy the API key
```

---

## PHASE 3 — Configure Environment

### 3.1 Copy the template
```bash
cd fashion-ai
cp .env.example .env
```

### 3.2 Edit `.env` — fill in ONLY these values (rest are pre-filled defaults)

Open `.env` in any text editor and change these lines:

```env
# REQUIRED — paste your Groq key from Phase 2.1
GROQ_API_KEY=gsk_paste_your_actual_key_here

# REQUIRED — paste your HuggingFace token from Phase 2.2
HF_API_KEY=hf_paste_your_actual_token_here

# REQUIRED — generate a random secret (run this command and paste the output):
#   python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=paste_the_64_char_hex_string_here
```

**Everything else (DATABASE_URL, REDIS_URL, QDRANT_URL, OLLAMA_URL) uses localhost defaults that work with Docker Compose. Don't change them for local dev.**

---

## PHASE 4 — Run Locally with Docker

### 4.1 Start all 11 services
```bash
cd fashion-ai
docker compose up -d
```

This starts: API, PostgreSQL, Redis, Qdrant, Ollama, MinIO, Celery Worker, Celery Beat, Flower, Prometheus, Grafana.

### 4.2 Wait for healthy (takes ~30-60 seconds)
```bash
docker compose ps
```

Expected output — all services should show `healthy` or `running`:
```
NAME              STATUS
api               Up (healthy)
postgres          Up (healthy)
redis             Up (healthy)
qdrant            Up
ollama            Up
minio             Up
celery_worker     Up
celery_beat       Up
flower            Up
prometheus        Up
grafana           Up
```

### 4.3 Check API logs
```bash
docker compose logs -f api
```
Look for: `Application startup complete` and `Uvicorn running on http://0.0.0.0:8000`

### 4.4 Access points (open in browser)
```
API Swagger:     http://localhost:8000/docs
Health check:    http://localhost:8000/health
Grafana:         http://localhost:3000      (login: admin / admin)
Prometheus:      http://localhost:9090
Qdrant:          http://localhost:6333/dashboard
MinIO Console:   http://localhost:9001      (login: minioadmin / minioadmin)
Celery Flower:   http://localhost:5555
```

---

## PHASE 5 — Verify Everything Works

Run these commands one by one. Every one should succeed.

### 5.1 Health check
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"healthy","version":"1.0.0","services":{"database":"connected","redis":"connected","qdrant":"connected"}}`

### 5.2 Register a test user
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@fashionai.com","password":"TestPass123!","display_name":"Test User"}'
```
Expected: JSON with `access_token`, `refresh_token`, and `user` object.

**Copy the `access_token` value — you need it for the next steps.**

### 5.3 Set the token as a variable (replace with your actual token)
```bash
# Linux/Mac:
export TOKEN="eyJ...paste_your_token_here..."

# Windows PowerShell:
$TOKEN = "eyJ...paste_your_token_here..."
```

### 5.4 Create a chat session
```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language":"en"}'
```

### 5.5 Classify an intent
```bash
curl -X POST http://localhost:8000/api/v1/chat/classify \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Design a red lehenga for my wedding"}'
```
Expected: `{"intent":"design_request","confidence":0.9...,"parameters":{...}}`

### 5.6 Test WebSocket chat (install wscat first)
```bash
npm install -g wscat

wscat -c "ws://localhost:8000/api/v1/chat/ws/test-session?token=$TOKEN"
```
Then type:
```json
{"type":"message","content":"Hello! Design a blue silk saree for a wedding","language":"en"}
```
You should see `response_start`, `response_chunk`, and `response_end` messages streaming back.

### 5.7 Check Prometheus metrics
```bash
curl http://localhost:8000/metrics | head -20
```

### 5.8 Verify unauthenticated request is blocked
```bash
curl http://localhost:8000/api/v1/chat/sessions
```
Expected: `401 Unauthorized`

**If all 8 checks pass, your local deployment is working. ✅**

---

## PHASE 6 — Generate Training Data

This runs locally. No GPU needed.

### 6.1 Generate 1,200 synthetic training samples
```bash
cd fashion-ai
python training/scripts/generate_synthetic_data.py
```
Expected output:
```
✅ intent_classifier: 500 samples
✅ design_agent: 300 samples
✅ tailor_agent: 200 samples
✅ style_agent: 200 samples
✅ combined: 1200 samples
```

### 6.2 Clean, deduplicate, filter, and split into train/val/test
```bash
python training/scripts/data_pipeline.py
```
Expected: Each dataset is deduped, quality-filtered, toxicity-filtered, and split into `data/processed/`.

### 6.3 Verify processed data exists
```bash
# Linux/Mac:
ls data/processed/

# Windows:
dir data\processed\
```
You should see `*_train.jsonl`, `*_val.jsonl`, `*_test.jsonl` for each model.

---

## PHASE 7 — Finetune Models on Colab

**This runs on Google Colab with a free T4 GPU. ~80 minutes total.**

### 7.1 Upload data to Google Drive

1. Go to https://drive.google.com
2. Create folder: `fashion-ai-training`
3. Upload the entire `data/processed/` folder into it
4. Upload the entire `training/configs/` folder into it
5. Upload the file `training/scripts/train_model.py` into it

### 7.2 Open Google Colab

1. Go to https://colab.research.google.com
2. Click **+ New Notebook**
3. Go to **Runtime → Change runtime type → T4 GPU** → Save

### 7.3 Run these cells in order

**Cell 1 — Mount Drive & install dependencies (~3 min)**
```python
from google.colab import drive
drive.mount('/content/drive')

!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps "trl<0.9.0" peft accelerate bitsandbytes
!pip install datasets pyyaml
print("✅ Dependencies installed!")
```

**Cell 2 — Copy files from Drive**
```python
import shutil, os

src = "/content/drive/MyDrive/fashion-ai-training"
dst = "/content/fashion-ai"

for subdir in ["data/processed", "training/configs", "training/scripts"]:
    os.makedirs(f"{dst}/{subdir}", exist_ok=True)

# Copy processed data
for f in os.listdir(f"{src}/processed"):
    shutil.copy2(f"{src}/processed/{f}", f"{dst}/data/processed/{f}")

# Copy configs
for f in os.listdir(f"{src}/configs"):
    shutil.copy2(f"{src}/configs/{f}", f"{dst}/training/configs/{f}")

# Copy training script
shutil.copy2(f"{src}/train_model.py", f"{dst}/training/scripts/train_model.py")

print("✅ Files copied!")
print(f"Data: {os.listdir(f'{dst}/data/processed/')}")
```

**Cell 3 — Train Intent Classifier (~15 min)**
```python
%cd /content/fashion-ai
!python training/scripts/train_model.py --config training/configs/intent_classifier.yaml
```

**Cell 4 — Train Design Agent (~25 min)**
```python
!python training/scripts/train_model.py --config training/configs/design_agent.yaml
```

**Cell 5 — Train Tailor Agent (~20 min)**
```python
!python training/scripts/train_model.py --config training/configs/tailor_agent.yaml
```

**Cell 6 — Save models back to Drive**
```python
import shutil, os

output_dir = "/content/fashion-ai/outputs"
drive_output = "/content/drive/MyDrive/fashion-ai-training/outputs"

if os.path.exists(output_dir):
    shutil.copytree(output_dir, drive_output, dirs_exist_ok=True)
    print("✅ Models saved to Google Drive!")
    for root, dirs, files in os.walk(drive_output):
        for f in files:
            if f.endswith(".gguf"):
                path = os.path.join(root, f)
                size_mb = os.path.getsize(path) / (1024*1024)
                print(f"  📦 {f} ({size_mb:.0f} MB)")
else:
    print("❌ No outputs directory found")
```

---

## PHASE 8 — Deploy Finetuned Models to Ollama

### 8.1 Download GGUF files from Google Drive

1. Go to Google Drive → `fashion-ai-training/outputs/`
2. Download all `*.gguf` files to a local folder (e.g., `~/fashion-models/`)

### 8.2 Create Modelfiles

Create these 3 files in the same folder as the GGUF files:

**File: `Modelfile.intent`**
```
FROM ./intent_classifier/gguf/unsloth.Q4_K_M.gguf

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 300

SYSTEM """You are an intent classifier for a fashion AI assistant.
Classify messages into: greeting, design_request, product_search, style_advice,
body_scan, virtual_tryon, wardrobe_manage, tailoring, feedback, general_chat.
Respond with JSON: {"intent": "...", "confidence": 0.0-1.0, "language": "en|hi|te", "parameters": {...}}"""
```

**File: `Modelfile.design`**
```
FROM ./design_agent/gguf/unsloth.Q4_K_M.gguf

PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER num_predict 800

SYSTEM """You are an expert Indian fashion designer. Create detailed outfit designs
with SDXL prompts, fabric notes, and cost estimates. Respond in JSON format."""
```

**File: `Modelfile.tailor`**
```
FROM ./tailor_agent/gguf/unsloth.Q4_K_M.gguf

PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER num_predict 1000

SYSTEM """You are a master Indian tailor. Provide detailed tailoring guides
with exact yardage, construction steps, and fabric recommendations. Respond in JSON."""
```

### 8.3 Register models with Ollama

```bash
cd ~/fashion-models/   # (or wherever your GGUF + Modelfile files are)

ollama create fashion-intent -f Modelfile.intent
ollama create fashion-design -f Modelfile.design
ollama create fashion-tailor -f Modelfile.tailor
```

### 8.4 Verify models are loaded
```bash
ollama list
```
Expected: `fashion-intent`, `fashion-design`, `fashion-tailor` in the list.

### 8.5 Quick test
```bash
ollama run fashion-intent "I want to buy a red saree for a wedding"
```
Expected: JSON with `{"intent": "product_search", ...}`

### 8.6 Restart Docker to pick up new Ollama models
```bash
cd fashion-ai
docker compose restart api
```

---

## PHASE 9 — Run Evaluation

### 9.1 Run full evaluation suite
```bash
cd fashion-ai
python evals/evaluate_models.py --all
```

Expected output:
```
📊 Intent Classifier: Accuracy 95%+, F1 90%+
📊 Design Agent: JSON Validity 95%+, Completeness 90%+
📊 Tailor Agent: Yardage Plausible 95%+
📊 G-EVAL: Overall 3.5+/5.0
```

Results saved to `data/processed/evaluation_report.json`.

---

## PHASE 10 — Deploy to Production

### 10.1 Push code to GitHub
```bash
cd fashion-ai
git init
git add .
git commit -m "Initial commit — AI Fashion Designer"
git remote add origin https://github.com/YOUR_USERNAME/fashion-ai.git
git push -u origin main
```

### 10.2 Deploy backend to Render.com (free)

1. Go to https://render.com → Sign up with GitHub
2. Click **New** → **Web Service**
3. Connect your `fashion-ai` repo
4. Configure:
   - **Name**: `fashion-ai-api`
   - **Root Directory**: `services/api`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free
5. Click **Advanced** → **Add Environment Variables** → add ALL variables from your `.env` file
   - **Important**: Change `DATABASE_URL` to your Supabase URL (from Phase 11)
   - **Important**: Change `REDIS_URL` to your Redis Cloud URL (or leave blank — app degrades gracefully)
   - **Important**: Change `QDRANT_URL` to your Qdrant Cloud URL (from Phase 11)
6. Click **Create Web Service**
7. Wait for build to complete (~5 min)
8. Your API is live at: `https://fashion-ai-api.onrender.com`

### 10.3 Verify production deployment
```bash
curl https://fashion-ai-api.onrender.com/health
curl https://fashion-ai-api.onrender.com/docs
```

---

## PHASE 11 — Deploy Databases

### 11.1 Supabase (PostgreSQL — free, 500MB)

1. Go to https://supabase.com → Sign up → **New Project**
2. Name: `fashion-ai`, Password: (generate a strong one), Region: closest to you
3. Wait for project to be created (~2 min)
4. Go to **Settings → Database → Connection string → URI**
5. Copy the connection string. It looks like:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
6. In Render, update `DATABASE_URL`:
   ```
   postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
   (Note: change `postgresql://` to `postgresql+asyncpg://` for async driver)

7. Also update `DATABASE_URL_SYNC` with the original string (keep `postgresql://`).

### 11.2 Qdrant Cloud (Vector DB — free, 1GB)

1. Go to https://cloud.qdrant.io → Sign up
2. Click **Create Cluster** → Free tier → Choose region
3. Copy the **URL** (like `https://xyz-abc.aws.cloud.qdrant.io:6333`)
4. Copy the **API Key**
5. In Render, update:
   - `QDRANT_URL` = the URL from step 3
   - `QDRANT_API_KEY` = the key from step 4

### 11.3 Redis (optional — app works without it)

**Option A**: Use Render's built-in Redis (if available on your plan)

**Option B**: Use Upstash Redis (free, 10K commands/day)
1. Go to https://upstash.com → Sign up
2. Create Redis database → Copy the `redis://...` connection string
3. In Render, update `REDIS_URL`

**Option C**: Leave `REDIS_URL` empty — the app detects this and runs without cache.

### 11.4 Redeploy Render after database changes
```
In Render dashboard → your service → Manual Deploy → Deploy latest commit
```

---

## PHASE 12 — Build Flutter App

### 12.1 Update API base URL

Edit `apps/mobile/lib/services/api_service.dart`:
```dart
// Change this line:
const String _baseUrl = 'http://10.0.2.2:8000';

// To your production URL:
const String _baseUrl = 'https://fashion-ai-api.onrender.com';
```

### 12.2 Install dependencies
```bash
cd fashion-ai/apps/mobile
flutter pub get
```

### 12.3 Run on emulator or connected device
```bash
flutter run
```

### 12.4 Build release APK (Android)
```bash
flutter build apk --release
```
Output: `build/app/outputs/flutter-apk/app-release.apk`

### 12.5 Build for iOS (requires Mac + Xcode)
```bash
flutter build ios --release
```

---

## PHASE 13 — Post-Deployment Setup

### 13.1 Keep Render alive (free tier sleeps after 15 min)

1. Go to https://uptimerobot.com → Sign up (free)
2. Click **Add Monitor**:
   - Type: HTTP(s)
   - URL: `https://fashion-ai-api.onrender.com/health`
   - Interval: 5 minutes
3. Save — this pings your API every 5 min to prevent sleep

### 13.2 Set up Grafana dashboards (local only)

1. Open http://localhost:3000 (login: admin/admin)
2. Dashboards are auto-provisioned:
   - **System Health**: API latency, error rates, uptime
   - **AI Performance**: Agent routing, LLM latency, intent distribution

### 13.3 Set up Langfuse (optional — LLM observability)

1. Go to https://langfuse.com → Create project
2. Copy Public Key and Secret Key
3. Add to Render environment:
   - `LANGFUSE_PUBLIC_KEY`
   - `LANGFUSE_SECRET_KEY`
4. Redeploy — all LLM calls are now traced

### 13.4 Set up PostHog (optional — product analytics)

1. Go to https://posthog.com → Create project
2. Copy API key
3. Add to Render: `POSTHOG_API_KEY`
4. Redeploy

---

## ✅ DEPLOYMENT COMPLETE — CHECKLIST

Use this to verify everything is working:

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | API is live | `curl https://YOUR-APP.onrender.com/health` | `{"status":"healthy"}` |
| 2 | Swagger UI loads | Open `https://YOUR-APP.onrender.com/docs` | Interactive API docs |
| 3 | Can register | POST `/api/v1/auth/register` | Returns JWT token |
| 4 | Can chat (WebSocket) | Connect to `/api/v1/chat/ws/...` | Streaming responses |
| 5 | Intent classification works | POST `/api/v1/chat/classify` | Returns intent + params |
| 6 | Auth is enforced | GET `/api/v1/chat/sessions` (no token) | 401 Unauthorized |
| 7 | Flutter app connects | Run `flutter run` → send message | Gets AI response |
| 8 | Finetuned models loaded | `ollama list` | Shows fashion-* models |
| 9 | Training data generated | Check `data/processed/` | 5 datasets with train/val/test |
| 10 | Evaluation passing | `python evals/evaluate_models.py --all` | Accuracy 95%+ |
| 11 | Keep-alive working | Check UptimeRobot | Green/up status |
| 12 | Grafana dashboards | Open `localhost:3000` | Charts with data |

---

## TROUBLESHOOTING

| Problem | Fix |
|---------|-----|
| `docker compose up` fails | Make sure Docker Desktop is running. Try `docker compose down -v` then `up -d` |
| API returns 500 errors | Check logs: `docker compose logs api`. Usually missing env vars |
| `GROQ_API_KEY` not working | Verify at https://console.groq.com → API Keys. Key must start with `gsk_` |
| Render deploys but API crashes | Check Render logs. Most common: wrong `DATABASE_URL` format. Must use `postgresql+asyncpg://` |
| WebSocket won't connect | Render free tier doesn't support WebSocket. Use REST endpoints instead, or upgrade to paid |
| Colab runs out of memory | Reduce `per_device_train_batch_size` to 1 in the YAML config |
| `flutter pub get` fails | Run `flutter clean` then `flutter pub get` again |
| Ollama model create fails | Check GGUF file is complete (not truncated). Re-download from Drive |
| Redis not connecting | Leave `REDIS_URL` blank — the app works without Redis cache |
| Qdrant not connecting | Leave `QDRANT_API_KEY` blank for local. For cloud, double-check the URL includes port |

---

## ARCHITECTURE DIAGRAM

```
                    ┌────────────────────┐
                    │   Flutter Mobile   │
                    │   (5 screens)      │
                    └────────┬───────────┘
                             │ REST + WebSocket
                             ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │            LangGraph Master Agent                  │  │
│  │  ┌──────────┐    ┌──────────────────────────────┐  │  │
│  │  │ Intent   │───►│ 10 Specialist Agents         │  │  │
│  │  │Classifier│    │ Design, Product, Tailor,     │  │  │
│  │  └──────────┘    │ Style, Greeting, General,    │  │  │
│  │                  │ Feedback, BodyScan, TryOn,   │  │  │
│  │                  │ Wardrobe                     │  │  │
│  │                  └──────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Services: LLM · Vision · ASR · TTS · Search ·          │
│            Moderation · Storage · Cache                   │
└──────────┬──────────┬──────────┬──────────┬──────────────┘
           │          │          │          │
    ┌──────▼───┐ ┌────▼────┐ ┌──▼───┐ ┌───▼────┐
    │PostgreSQL│ │  Qdrant │ │Redis │ │ Ollama │
    │(Supabase)│ │ (Cloud) │ │      │ │(Local) │
    └──────────┘ └─────────┘ └──────┘ └────────┘
```

---

## COST SUMMARY

| Service | Monthly Cost | Notes |
|---------|:---:|-------|
| Groq API | $0 | 30 RPM, 100K tokens/day |
| HuggingFace | $0 | Rate-limited inference |
| Render | $0 | Free tier, auto-sleep |
| Supabase | $0 | 500MB PostgreSQL |
| Qdrant Cloud | $0 | 1GB vector storage |
| Google Colab | $0 | Free T4 GPU for training |
| UptimeRobot | $0 | 50 monitors |
| Langfuse | $0 | 50K traces/month |
| PostHog | $0 | 1M events/month |
| **TOTAL** | **$0/month** | **No credit card required** |
