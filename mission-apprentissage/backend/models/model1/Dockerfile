# Production Dockerfile for the BLIP (Salesforce) captioning microservice.
# Build context: parent of mission-apprentissage/ (same as current compose).

# ---------- Stage 1: builder ----------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache

# Build toolchain only needed here; discarded with the stage.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Dependencies first (cache-friendly)
COPY mission-apprentissage/backend/models/model1/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /tmp/requirements.txt

# Pre-download model weights into the HF cache dir.
# This layer is invalidated only if requirements.txt changes, not on app edits.
RUN python -c "\
from transformers import BlipProcessor, BlipForConditionalGeneration;\
BlipProcessor.from_pretrained('Salesforce/blip-image-captioning-large');\
BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-large')"

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# curl for healthcheck; tini for clean PID 1 signal handling.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser:app /opt/hf-cache /opt/hf-cache

WORKDIR /app
COPY --chown=appuser:app mission-apprentissage/backend/utils.py /app/utils.py
COPY --chown=appuser:app mission-apprentissage/backend/models/model1/saleforce_cpu_large.py /app/saleforce_cpu_large.py

USER appuser:app

EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=15s --timeout=10s --start-period=90s --retries=5 \
  CMD curl -fsS http://localhost:8000/ || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "saleforce_cpu_large:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", \
     "--timeout-graceful-shutdown", "30"]
