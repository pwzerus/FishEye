# FishEye API (FastAPI). Built by docker-compose.yml at the repo root.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
# Dependencies first, so editing app code doesn't reinstall them.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user. /app/media holds uploaded photos and is a
# volume in docker-compose.yml, so it must exist and be writable by it.
RUN useradd --create-home --uid 10001 fisheye \
    && mkdir -p /app/media \
    && chown fisheye /app/media
USER fisheye

EXPOSE 8000
# Seed the three demo lakes (a no-op once any data exists), then serve.
# Tables are created by the app's own startup; the seed creates them too.
CMD ["sh", "-c", "python -m app.data_import.seed_tx_lakes && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
