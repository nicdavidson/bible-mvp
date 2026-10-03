FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos '' --home /home/appuser appuser && \
    apt-get update && apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The ~370MB DB gets its own layer, before code, so code-only deploys reuse it
# instead of re-pushing it. The entrypoint syncs it to the volume when the manifest sha changes.
COPY data/bible.db data/db-manifest.json data/

COPY data/reading-plan-*.json data/
COPY scripts/ scripts/
COPY backend/ backend/
COPY frontend/ frontend/

# Inject git commit hash for service worker / asset cache busting
ARG SW_VERSION=dev
RUN sed -i "s/__SW_VERSION__/${SW_VERSION}/g" frontend/static/sw.js frontend/index.html

EXPOSE 8000

# Entrypoint runs as root for DB sync, then drops to appuser for uvicorn
CMD ["sh", "scripts/entrypoint.sh"]
