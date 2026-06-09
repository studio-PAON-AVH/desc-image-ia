# Production Dockerfile for the Florence-2 captioning microservice.
# Note: service name is florence2_large but loads Florence-2-base — intentional.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY mission-apprentissage/backend/models/model2/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /tmp/requirements.txt

# Florence-2 ships custom modeling code; trust_remote_code is required.
RUN python -c "\
from transformers import AutoProcessor, AutoModelForCausalLM;\
AutoProcessor.from_pretrained('microsoft/Florence-2-base', trust_remote_code=True);\
AutoModelForCausalLM.from_pretrained('microsoft/Florence-2-base', torch_dtype='auto', trust_remote_code=True)"

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 app \
 && useradd  --system --uid 10001 --gid app --home /app --shell /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser:app /opt/hf-cache /opt/hf-cache

WORKDIR /app
COPY --chown=appuser:app mission-apprentissage/backend/utils.py /app/utils.py
COPY --chown=appuser:app mission-apprentissage/backend/models/model2/florence2_large.py /app/florence2_large.py

USER appuser:app

EXPOSE 8000
STOPSIGNAL SIGTERM

# start_period 120s : Florence-2 JIT-compile du custom code au premier forward pass
HEALTHCHECK --interval=15s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -fsS http://localhost:8000/ || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "florence2_large:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", \
     "--timeout-graceful-shutdown", "30"]
