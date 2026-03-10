FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

ENV PYTHONPATH=/app

# Migrate, start Celery worker in background, then API (single container for plans without separate worker).
CMD ["sh", "-c", "(cd backend && alembic upgrade head) && celery -A backend.worker worker -l info & exec uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
