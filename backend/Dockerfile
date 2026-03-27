FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

RUN mkdir -p /tmp/matplotlib /tmp/fontconfig

RUN useradd --no-create-home --shell /bin/false appuser && chown -R appuser /app
USER appuser

ENV PYTHONPATH=/app
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV FC_CACHEDIR=/tmp/fontconfig

# Run migrations then start the API. Celery worker runs as a separate Render service (see render.yaml).
CMD ["sh", "-c", "(cd backend && alembic upgrade head) && exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
