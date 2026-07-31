FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    libgles2 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

RUN mkdir -p /tmp/matplotlib /tmp/fontconfig

# Pre-create the local-storage mount point owned by appuser: Docker seeds a
# named volume from whatever exists at its mount path in the image on first
# attach, so this is what makes /data/local_storage writable by appuser
# instead of defaulting to root ownership (see docker-compose.yml's
# local_storage volume, used only in local dev — prod uses R2).
RUN mkdir -p /data/local_storage && \
    useradd --no-create-home --shell /bin/false appuser && \
    chown -R appuser /app /data/local_storage
USER appuser

ENV PYTHONPATH=/app
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV FC_CACHEDIR=/tmp/fontconfig

# Run migrations then start the API. Celery worker runs as a separate Render service (see render.yaml).
CMD ["sh", "-c", "(cd backend && alembic upgrade head) && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
