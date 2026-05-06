# ── Stage 1: builder ─────────────────────────────────────────────────────────
# Installs build tools and Python deps into a prefix dir.
# Nothing from this stage reaches the final image except /install and /kronos/model.
FROM python:3.11 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Clone only the model/ subdirectory (sparse checkout keeps the layer small)
RUN git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/shiyu-coder/Kronos /kronos \
    && cd /kronos && git sparse-checkout set model

# Install Python deps into an isolated prefix so we copy only the installed
# files — no pip cache, no build tools — into the final stage.
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: final runtime ────────────────────────────────────────────────────
# Full image with everything needed for SSL verification.
FROM python:3.11 AS final

# curl for the HEALTHCHECK only
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python packages (no compilers, no git)
COPY --from=builder /install /usr/local

# Kronos model package (renamed to avoid shadowing stdlib 'model')
COPY --from=builder /kronos/model /app/model

WORKDIR /app

# Application code is copied last — most frequently changed layer
COPY app/ ./app/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    HF_HUB_DISABLE_SSL_VERIFY=1 \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

EXPOSE 8000

# Allow up to 120 s for the model to load before health checks begin
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Single worker — Kronos model is not thread-safe for concurrent inference
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
