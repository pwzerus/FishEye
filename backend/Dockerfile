# FishEye API (FastAPI). Built by docker-compose.yml at the repo root.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
# Dependencies first, so editing app code doesn't reinstall them.
COPY requirements.txt requirements-semantic.txt ./
RUN pip install -r requirements.txt -r requirements-semantic.txt

COPY app ./app

# Ask's semantic model (docs/adr/0025, 0029), fetched at build time at the
# commit that was reviewed, then compressed to int8. The uncompressed copy
# is deleted: the app uses the int8 file, and it saves 470 MB of image.
ARG E5_REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
RUN python -m app.cli.fetch_embedding_model --revision "$E5_REVISION" \
    && rm -rf models/multilingual-e5-small/onnx/model.onnx models/multilingual-e5-small/.cache

# Run as an unprivileged user. /app/media holds uploaded photos and is a
# volume in docker-compose.yml, so it must exist and be writable by it.
RUN useradd --create-home --uid 10001 fisheye \
    && mkdir -p /app/media \
    && chown fisheye /app/media \
    && chown -R fisheye /app/models
USER fisheye

EXPOSE 8000
# Seed the three demo lakes (a no-op once any data exists), then serve.
# Tables are created by the app's own startup; the seed creates them too.
CMD ["sh", "-c", "python -m app.data_import.seed_tx_lakes && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
