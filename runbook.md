# Kronos API Runbook

Operational documentation for running and troubleshooting the Kronos API.

## Issues and Solutions

### Issue: SSL Certificate Verification Failures in Docker

**Symptoms:**
- Container fails to start with error: `SSL: CERTIFICATE_VERIFY_FAILED`
- Model download hangs or times out
- Errors like `HTTP 503` or `Could not resolve path` in logs

**Root Cause:**
Docker container on macOS has SSL verification issues when downloading from HuggingFace due to:
1. Incomplete CA certificates in minimal base images
2. HuggingFace's Xet protocol interfering with redirects
3. Docker networking stack not properly trusting system CAs

**Solution: Use Local Model Files**

Instead of downloading at runtime, pre-download model files to a local directory and mount into the container:

```bash
# 1. Create directories
mkdir -p models/tokenizer models/kronos-small

# 2. Download tokenizer files (use -k to bypass SSL)
cd models/tokenizer
for f in .gitattributes README.md config.json model.safetensors; do
  curl -k -L "https://huggingface.co/NeoQuasar/Kronos-Tokenizer-base/resolve/main/$f" -o "$f"
done

# 3. Download model files
cd ../kronos-small
for f in .gitattributes README.md config.json model.safetensors; do
  curl -k -L "https://huggingface.co/NeoQuasar/Kronos-small/resolve/main/$f" -o "$f"
done
```

Update `.env` to use local paths:
```bash
KRONOS_MODEL=/models/kronos-small
KRONOS_TOKENIZER=/models/tokenizer
```

The `docker-compose.yml` already mounts `./models` to `/models`.

---

### Issue: Container Keeps Restarting

**Symptoms:**
- `docker ps` shows container in restart loop
- `docker logs` shows exit code 3 or startup failure

**Diagnosis:**
```bash
docker logs kronos-api-kronos-1
docker compose ps
```

**Common Causes:**
1. Missing or invalid `.env` variables
2. Model loading failure (wrong path or corrupted files)
3. Out of memory (check `docker stats`)

**Solution:**
1. Check `.env` matches `.env.example`
2. Verify model files downloaded completely (check file sizes)
3. Increase memory allocation in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 6G
```

---

### Issue: Slow Inference on CPU

**Symptoms:**
- `/score/portfolio` takes >10 minutes for 20 stocks

**Solution:**
1. Use smaller model: `KRONOS_MODEL=/models/kronos-small` (25M params) vs base (102M)
2. For twice-weekly batch runs, CPU is acceptable
3. For production, deploy to cloud with GPU (Modal, GCP, AWS)

---

## Operational Commands

### Start/Stop
```bash
# Start
docker compose up -d

# Stop
docker compose down

# Restart
docker compose restart
```

### View Logs
```bash
# All logs
docker compose logs -f

# Just API logs
docker logs kronos-api-kronos-1 -f
```

### Verify Health
```bash
curl http://localhost:8000/health
```

### Trigger Scoring
```bash
curl -X POST http://localhost:8000/score/portfolio \
  -H "X-Api-Key: your-key"
```

---

## File Locations

| Path | Description |
|---|---|
| `./models/` | Local model/tokenizer files |
| `docker-compose.yml` | Container config |
| `.env` | Environment variables |
| `app/kronos_model.py` | Model loading logic |
| `app/main.py` | FastAPI app |

---

## Useful Debugging Commands

```bash
# Check container status
docker compose ps

# Check resource usage
docker stats

# Shell into container
docker exec -it kronos-api-kronos-1 /bin/bash

# Check available memory
docker exec -it kronos-api-kronos-1 free -h

# List mounted models
docker exec -it kronos-api-kronos-1 ls -la /models/
```