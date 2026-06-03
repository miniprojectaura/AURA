# 🧥 AI Fashion Designer

**AI-Powered Personal Fashion Designer** — A multi-agent conversational AI platform for personalized fashion design, virtual try-on, and intelligent product recommendations with full Telugu/Hindi/English voice support.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter Mobile App                     │
│              (Riverpod + WebSocket + Drift)              │
└─────────────┬───────────────────────────────┬───────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────┐   ┌───────────────────────────┐
│   FastAPI Backend        │   │  WebSocket Gateway        │
│   (REST + GraphQL)       │   │  (Bidirectional Streaming)│
└───────────┬─────────────┘   └─────────────┬─────────────┘
            │                               │
            ▼                               ▼
┌───────────────────────────────────────────────────────────┐
│                   LangGraph Agent Mesh                     │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │
│  │ Master   │→│ Fashion   │→│ Product │→│ Body        │  │
│  │ Agent    │  │ Designer  │  │ Matcher │  │ Analyzer   │  │
│  └─────────┘  └──────────┘  └────────┘  └────────────┘  │
└───────────────────────┬───────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌────────────┐ ┌──────────────┐
│ Groq LLM     │ │ HF Inference│ │ Ollama Local │
│ (Primary)    │ │ (Vision/SD) │ │ (Fallback)   │
└──────────────┘ └────────────┘ └──────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Node.js 20+ (for tooling)
- Flutter 3.24+ (for mobile app)

### 1. Clone and Setup

```bash
git clone https://github.com/YOUR_USERNAME/fashion-ai.git
cd fashion-ai
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Services

```bash
docker compose up -d
```

### 3. Run API Server

```bash
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Run Database Migrations

```bash
cd services/api
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 5. Verify

```bash
curl http://localhost:8000/health
# Opens Swagger docs
open http://localhost:8000/docs
```

## 📁 Project Structure

```
fashion-ai/
├── services/api/           # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # REST endpoints
│   │   ├── agents/         # LangGraph agent mesh
│   │   ├── auth/           # JWT authentication
│   │   ├── middleware/     # Rate limiting, circuit breakers
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic v2 schemas
│   │   ├── services/       # Business logic services
│   │   ├── workers/        # Celery tasks
│   │   └── utils/          # Logging, helpers
│   ├── alembic/            # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── apps/mobile/            # Flutter mobile app
├── training/               # ML training scripts
├── data/                   # Datasets
├── evals/                  # Evaluation benchmarks
├── infra/                  # Infrastructure configs
│   ├── prometheus/
│   └── grafana/
├── tests/                  # Test suite
├── docker-compose.yml      # Local development stack
├── .github/workflows/      # CI/CD pipeline
└── .env.example
```

## 🔑 Key Features

- **Multilingual Voice Chat**: Telugu, Hindi, English with Whisper v3 + Kokoro TTS
- **AI Outfit Generation**: SDXL + ControlNet with cultural awareness
- **3D Body Avatar**: SMPL-X reconstruction from 2 photos
- **Virtual Try-On**: Kolors VTON for realistic garment visualization
- **Smart Product Search**: FashionCLIP hybrid vector + BM25 search
- **Tailoring Guides**: AI-generated construction patterns
- **Free Tier Deployment**: Runs on Render + Supabase + Cloudflare R2

## 📊 Monitoring

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Flower** (Celery): http://localhost:5555
- **API Docs**: http://localhost:8000/docs

## 📝 License

MIT License
