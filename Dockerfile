# SMART Mock Interview - local application image.
#   docker build -t smart-mock-interview:local .
# Lean by design: no PyTorch, no FAISS, no model weights, no credentials, no Docker client, no code-execution sandbox.
# What works in this image: the Flask app, /demo, the 666-question corpus, static code check, recorded-result display, health/metrics.
# What needs optional pieces: legacy BERT/Bi-LSTM scorers (build-arg INSTALL_ML=1 + a model volume), live Qwen evaluation (a separate Ollama service).
# NOT a production image: no TLS, no authentication, in-memory legacy sessions (single process). See docs/MLOPS.md.
ARG PYTHON_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_IMAGE}

ARG INSTALL_ML=0
ARG SMART_GIT_COMMIT=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SMART_GIT_COMMIT=${SMART_GIT_COMMIT} \
    SMART_HOST=0.0.0.0 \
    SMART_PORT=5000 \
    SMART_FORBID_MODEL_TRAINING=1 \
    SMART_DEMO_DATA_DIR=/app/results/demo_sessions \
    HF_HOME=/hf-cache

# unprivileged user; fixed uid so a bind-mounted volume can be chown'ed predictably
RUN groupadd --system --gid 10001 smart \
 && useradd --system --uid 10001 --gid smart --home-dir /home/smart --create-home --shell /usr/sbin/nologin smart

WORKDIR /app

# 1. dependency layers change rarely -> cached
COPY requirements-docker.lock requirements-docker-ml.txt ./
RUN pip install -r requirements-docker.lock \
 && if [ "$INSTALL_ML" = "1" ]; then pip install -r requirements-docker-ml.txt; fi

# 2. application code and the small, version-controlled data (see .dockerignore for what is excluded)
COPY main/ ./main/
COPY src/ ./src/
COPY report_delivery/ ./report_delivery/
COPY data/ ./data/
COPY scripts/healthcheck.py ./scripts/healthcheck.py

# 3. the only writable location: session files, generated reports (mount a volume here to keep them)
# (/hf-cache is where an INSTALL_ML=1 build looks for the embedding model; mount a volume there. Nothing is downloaded into the image.)
RUN mkdir -p /app/results/demo_sessions /hf-cache && chown -R smart:smart /app/results /hf-cache

USER smart
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "scripts/healthcheck.py"]

# single process, several threads: legacy interview sessions live in process memory
CMD ["python", "-m", "waitress", "--listen=0.0.0.0:5000", "--threads=8", "--ident=smart-mock-interview", "main.app:app"]
