# Deploy Guide — AI Fashion Designer

Exact CLI commands to get the app running locally and deployed to production.

---

## Prerequisites

```bash
# Docker Desktop (Windows/Mac) or Docker Engine (Linux)
# https://docs.docker.com/get-docker/

# Python 3.11+
# https://www.python.org/downloads/

# Flutter 3.x (for mobile app)
# https://docs.flutter.dev/get-started/install

# Ollama (optional — for local LLM)
# https://ollama.ai/download

# Git
# https://git-scm.com/downloads
```

---

## 1. Quick Start (Docker — Recommended)

```bash
# Clone repo
git clone <your-repo> fashion-ai && cd fashion-ai

# Copy and fill environment
cp .env.example .env
# Edit .env and add at minimum:
#   GROQ_API_KEY=gsk_...        (https://console.groq.com → API Keys)
#   HF_API_KEY=hf_...           (https://huggingface.co/settings/tokens)
#   JWT_SECRET_KEY=$(openssl rand -hex 32)

# Start all 10 services
docker compose up -d

# Check everything is healthy
docker compose ps
docker compose logs -f api

# Endpoints:
#   API:        http://localhost:8000
#   Swagger:    http://localhost:8000/docs
#   Grafana:    http://localhost:3000 (admin/admin)
#   Prometheus: http://localhost:9090
#   Qdrant:     http://localhost:6333/dashboard
#   MinIO:      http://localhost:9001 (minioadmin/minioadmin)
```

## 2. Smoke Tests

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"healthy","version":"1.0.0","services":{"database":"connected",...}}

# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"SecurePass123!","display_name":"Test User"}'
# → {"access_token":"eyJ...","refresh_token":"...","user":{...}}

# Use the token for authenticated requests:
TOKEN="eyJ..."  # Copy from above response

# Create chat session
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language":"en"}'

# Send message via WebSocket (use wscat or websocat)
npm install -g wscat
wscat -c "ws://localhost:8000/api/v1/chat/ws/test-session?token=$TOKEN"
# Type: {"type":"message","content":"Design a red lehenga for wedding","language":"en"}

# Search products
curl -X POST http://localhost:8000/api/v1/search/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"red silk saree under 5000","limit":5}'

# Check Prometheus metrics
curl http://localhost:8000/metrics | head -20
```

## 3. Run Backend Without Docker

```bash
cd services/api

# Create virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  # Windows

# Install deps
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 4. Run Flutter Mobile App

```bash
cd apps/mobile  # (if Flutter app exists)
# OR build from the Flutter source files in the project

flutter pub get
flutter analyze
flutter run  # Starts on connected device/emulator

# Build release APK
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

## 5. Generate Training Data & Run Evaluation

```bash
# Generate synthetic training data
python training/scripts/generate_synthetic_data.py

# Clean and split
python training/scripts/data_pipeline.py

# Run evaluation
python evals/evaluate_models.py --all
```

## 6. Deploy to Production

### Backend → Render.com (Free)

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repo
3. Configure:
   - **Root Directory**: `services/api`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance**: Free
4. Add all environment variables from `.env`

### Database → Supabase (Free)

1. Go to https://supabase.com → New Project
2. Copy the connection string from Settings → Database
3. Set `DATABASE_URL` in Render environment

### Vector DB → Qdrant Cloud (Free)

1. Go to https://cloud.qdrant.io → Create Cluster
2. Copy URL and API key
3. Set `QDRANT_URL` and `QDRANT_API_KEY` in Render environment

### Keep Render Alive

1. Go to https://uptimerobot.com (free)
2. Add HTTP monitor: `https://your-app.onrender.com/health`
3. Check interval: 5 minutes

---

## Architecture

```
┌──────────────┐    WebSocket/REST     ┌───────────────────────────────┐
│  Flutter App │◄──────────────────────►│       FastAPI Backend         │
│  (Mobile)    │                        │                               │
└──────────────┘                        │  ┌─────────────────────────┐  │
                                        │  │   LangGraph Master Agent │  │
                                        │  │                         │  │
                                        │  │  ┌──────┐ ┌──────────┐ │  │
                                        │  │  │Intent│→│Specialist│ │  │
                                        │  │  │Class.│ │  Agents  │ │  │
                                        │  │  └──────┘ └──────────┘ │  │
                                        │  └─────────────────────────┘  │
                                        │                               │
                                        │  Services:                    │
                                        │  • LLM (Groq → Ollama)       │
                                        │  • Vision (CLIP/SAM/Qwen-VL) │
                                        │  • ASR (Whisper)              │
                                        │  • TTS (Kokoro-82M)          │
                                        │  • Product Search (Qdrant)   │
                                        │  • Content Moderation        │
                                        │  • Storage (R2/MinIO)        │
                                        └───────────┬───────────────────┘
                                                    │
                                   ┌────────────────┼────────────────┐
                                   │                │                │
                            ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼─────┐
                            │  PostgreSQL  │  │   Qdrant    │  │   Redis   │
                            │  (Supabase)  │  │  (Vectors)  │  │  (Cache)  │
                            └─────────────┘  └─────────────┘  └───────────┘
```
