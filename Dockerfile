# MathMate (geo-draw) production image: the FastAPI server serving the built React app.
#
#   docker compose up -d --build        (see docker-compose.yml)

# 1. Web app -------------------------------------------------------------------------------
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2. Python packages (pycairo and friends compile against the -dev libraries) --------------
FROM python:3.12-slim-bookworm AS python-deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config libcairo2-dev libpango1.0-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
# The legacy Streamlit UI and the test client are not needed to serve the app.
RUN grep -vE '^(streamlit|httpx2)' /tmp/requirements.txt > /tmp/requirements-prod.txt \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-prod.txt

# 3. Runtime -------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm
# Manim renders through Cairo/Pango, draws labels with system fonts, and needs FFmpeg for
# videos. No LaTeX: every label is Text.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data && chown app:app /data

# PYTHONPATH: the Manim render subprocess imports geo_draw from the generated scene.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GEO_DRAW_DATA_DIR=/data \
    PYTHONPATH=/app
COPY --from=python-deps /opt/venv /opt/venv

WORKDIR /app
COPY geo_draw/ geo_draw/
COPY api/ api/
COPY --from=web /web/dist web/dist

USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
# One worker only: running jobs, their SSE streams and the "being drawn" markers live in
# this process's memory. X-Forwarded-For is only believed from the proxies listed in
# FORWARDED_ALLOW_IPS (uvicorn's default: localhost only; docker-compose.traefik.yml sets the
# Docker networks). Never "*": uvicorn would then take the leftmost, client-forgeable address,
# and the per-IP limits would be easy to dodge.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
