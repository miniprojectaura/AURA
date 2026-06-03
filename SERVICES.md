# External Services — AI Fashion Designer

All external services, their free tier limits, and sign-up URLs.

**Total monthly cost at MVP scale: $0**

| # | Service | Category | Free Tier | Card Required | Sign-Up | Env Variable |
|---|---------|----------|-----------|:---:|---------|-------------|
| 1 | **Groq** | LLM Inference | 30 RPM, 100K tok/day, Llama 3.3 70B | ❌ | [console.groq.com](https://console.groq.com) | `GROQ_API_KEY` |
| 2 | **Hugging Face** | AI Models | Rate-limited inference, unlimited repos | ❌ | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | `HF_API_KEY` |
| 3 | **Supabase** | Database + Auth | 500MB Postgres, 50K MAU, RLS | ❌ | [supabase.com](https://supabase.com) | `SUPABASE_URL`, `SUPABASE_KEY` |
| 4 | **Qdrant Cloud** | Vector DB | 1GB storage, ~5M vectors | ❌ | [cloud.qdrant.io](https://cloud.qdrant.io) | `QDRANT_URL`, `QDRANT_API_KEY` |
| 5 | **Cloudflare R2** | Object Storage | 10GB free, zero egress | ❌ | [dash.cloudflare.com](https://dash.cloudflare.com) | `R2_ENDPOINT`, `R2_ACCESS_KEY` |
| 6 | **Render** | Hosting | 512MB RAM, auto-sleep, free HTTPS | ❌ | [render.com](https://render.com) | Deploy target |
| 7 | **Firebase FCM** | Push Notifications | Unlimited push messages | ❌ | [console.firebase.google.com](https://console.firebase.google.com) | `FCM_SERVER_KEY` |
| 8 | **PostHog** | Analytics | 1M events/month | ❌ | [posthog.com](https://posthog.com) | `POSTHOG_API_KEY` |
| 9 | **Langfuse** | LLM Observability | 50K traces/month | ❌ | [langfuse.com](https://langfuse.com) | `LANGFUSE_PUBLIC_KEY` |
| 10 | **Ollama** | Local LLM | Unlimited (self-hosted) | ❌ | [ollama.ai](https://ollama.ai) | `OLLAMA_URL` |
| 11 | **PostgreSQL** | Database | Unlimited (Docker) | ❌ | `docker pull postgres:16-alpine` | `DATABASE_URL` |
| 12 | **Redis** | Cache | Unlimited (Docker) | ❌ | `docker pull redis:7-alpine` | `REDIS_URL` |
| 13 | **Prometheus** | Metrics | Unlimited (self-hosted) | ❌ | `docker pull prom/prometheus` | Auto-configured |
| 14 | **Grafana** | Dashboards | Unlimited (self-hosted) | ❌ | `docker pull grafana/grafana` | Auto-configured |
| 15 | **MinIO** | Object Storage | Unlimited (self-hosted) | ❌ | `docker pull minio/minio` | Auto-configured |
| 16 | **Unsloth** | Finetuning | Unlimited (Colab T4) | ❌ | [colab.research.google.com](https://colab.research.google.com) | N/A |
| 17 | **DeepEval** | LLM Evaluation | Unlimited (local) | ❌ | `pip install deepeval` | N/A |
| 18 | **Kokoro-82M** | TTS | Unlimited (Apache 2.0, local) | ❌ | `pip install kokoro` | N/A |
| 19 | **NudeNet** | NSFW Detection | Unlimited (local) | ❌ | `pip install nudenet` | N/A |
| 20 | **Detoxify** | Text Toxicity | Unlimited (local) | ❌ | `pip install detoxify` | N/A |
| 21 | **Semgrep** | SAST Security | Unlimited (CE) | ❌ | [semgrep.dev](https://semgrep.dev) | N/A |
| 22 | **GitHub Actions** | CI/CD | 2000 min/month | ❌ | [github.com](https://github.com) | N/A |

## Notes

- All 22 services are free-tier and require **no credit card**.
- Self-hosted services (10-15) run via Docker Compose locally.
- Local ML models (18-20) run on CPU, no GPU required for inference.
- Groq provides 394 tokens/second on Llama 3.3 70B — faster than any paid API.
- Qdrant Cloud's 1GB free tier holds ~5M fashion product embeddings (512-dim).
