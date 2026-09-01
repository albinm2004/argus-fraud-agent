# Argus webhook receiver -- deployable container.
#
# Builds the FastAPI service (app/webhook_receiver.py). The trained models
# under models/ are copied in (they're small and already committed to git),
# but the raw IEEE-CIS dataset is NOT baked in -- it's ~700MB and gitignored
# for a reason. Without it, the receiver still starts and correctly verifies
# signatures / normalizes events; it just can't score (see the feature-store
# scope note in app/webhook_receiver.py -- this degrades gracefully rather
# than crashing). To enable scoring, mount data/raw/ieee-fraud-detection at
# runtime (see the `docker run` example below) or bake it into a derived
# image if you control where it's deployed.
#
# Build:  docker build -t argus-webhook-receiver .
# Run:    docker run --rm -p 8000:8000 --env-file .env argus-webhook-receiver
# Run with real scoring (mount the dataset from the host):
#         docker run --rm -p 8000:8000 --env-file .env \
#           -v "$(pwd)/data/raw:/app/data/raw" argus-webhook-receiver

FROM python:3.11-slim

WORKDIR /app

# System deps for xgboost/pandas wheels on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ agents/
COPY app/ app/
COPY config.py .
COPY models/ models/

# NOT copied: .env (secrets -- pass via --env-file or -e at runtime),
# data/raw and data/processed (gitignored, large -- mount if scoring is
# needed), tests/, scripts/, docs/ (not needed to run the service).

ENV PYTHONPATH=/app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.webhook_receiver:app", "--host", "0.0.0.0", "--port", "8000"]
