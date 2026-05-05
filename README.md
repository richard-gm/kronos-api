# Kronos API

A containerised REST API that wraps the [Kronos](https://github.com/shiyu-coder/Kronos) foundation model for financial candlestick forecasting. Fetches OHLCV data from Alpaca, runs inference, and writes directional signals to Supabase.

## What it does

- `POST /score/portfolio` — scores all configured tickers, writes results to Supabase
- `POST /score/stock` — on-demand score for any single ticker
- `GET /health` — liveness check

Scores are stored in a `kronos_scores` Supabase table and read by the [options-tracker](https://github.com/richard-gm/options-tracker) frontend.

## Prerequisites

- Docker Desktop (Mac) or Docker Engine (Linux)
- [Alpaca](https://alpaca.markets) account (free paper trading works)
- [Supabase](https://supabase.com) project with `schema.sql` applied

## Quick start

```bash
# 1. Apply schema to your Supabase project (SQL Editor)
#    → paste contents of schema.sql

# 2. Configure environment
cp .env.example .env
# Edit .env with your keys

# 3. Build and run
docker compose build
docker compose up -d

# 4. Verify
curl http://localhost:8000/health

# 5. Score your portfolio
curl -X POST http://localhost:8000/score/portfolio \
  -H "X-Api-Key: your-key"
```

## Environment variables

See `.env.example` for the full list. Required:

| Variable | Description |
|---|---|
| `API_KEY` | Secret key for `X-Api-Key` header |
| `ALPACA_API_KEY` | Alpaca API key |
| `ALPACA_SECRET_KEY` | Alpaca secret key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `PORTFOLIO_TICKERS` | Comma-separated tickers to score |

## Kronos model options

| Model | Params | RAM | ~Time (20 stocks, CPU) |
|---|---|---|---|
| `NeoQuasar/Kronos-mini` | 4.1M | ~1 GB | ~3 min |
| `NeoQuasar/Kronos-small` | 24.7M | ~2 GB | ~8 min |
| `NeoQuasar/Kronos-base` | 102.3M | ~4 GB | ~30 min |

Model weights are downloaded from HuggingFace on first run (~600 MB) and cached in a Docker volume — subsequent starts are instant.

## Platform compatibility

### macOS (M-series — current setup)

`docker-compose.yml` uses `platform: linux/arm64`. Docker Desktop on macOS runs a Linux VM; **Metal/MPS GPU acceleration is not available inside containers**. Inference runs on CPU, which is fast enough for twice-weekly batch runs.

```yaml
# docker-compose.yml — macOS M-series
platform: linux/arm64
```

### Linux (AMD64 — for cloud or native Linux machines)

Remove or change the `platform` line:

```yaml
# docker-compose.yml — Linux AMD64
platform: linux/amd64   # or remove the line entirely
```

Also consider switching to the CPU-only PyTorch index in `requirements.txt` to reduce image size from ~3 GB to ~1.5 GB:

```
# requirements.txt — Linux AMD64 (CPU only, no CUDA)
torch>=2.3.0 --extra-index-url https://download.pytorch.org/whl/cpu
```

For GPU-enabled cloud instances (GCP with T4, AWS g4dn), use the standard `torch` line and ensure the instance has CUDA drivers installed. Update `KRONOS_MODEL` to `Kronos-base` for better accuracy.

### Multi-platform builds (build once, run anywhere)

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/richard-gm/kronos-api:latest \
  --push .
```

## Cloud deployment

See `.github/workflows/deploy.yml` for commented-out pipelines for:

- **Modal** — serverless GPU, pay-per-second (~£1/month for twice-weekly runs)
- **GCP Cloud Run** — managed containers, good free tier
- **AWS ECS Fargate** — managed containers, EU-West-2 region

For all cloud targets, change `platform` to `linux/amd64` and rebuild.

## Future improvements

- [ ] GitHub Actions: activate one of the cloud deployment options in `deploy.yml`
- [ ] Linux AMD64 CPU-only requirements file for smaller cloud images
- [ ] Telegram trigger: store API key + URL in NanoClaw vault → call from agent
- [ ] Modal deployment script (`app/modal_app.py`) for GPU-accelerated inference
- [ ] Fine-tune Kronos on your specific portfolio using the repo's `finetune/` pipeline
- [ ] Historical score tracking (keep all runs, not just latest per ticker)
- [ ] Webhook alert when signal flips direction between runs
