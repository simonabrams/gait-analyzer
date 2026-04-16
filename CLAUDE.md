# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Frontend (Next.js)
```bash
cd frontend
npm run dev       # Start dev server (port 3000)
npm run build     # Production build
npm run lint      # ESLint
```

### Backend (Python/FastAPI)
```bash
# Run full stack locally via Docker Compose
docker compose up

# Backend tests
pytest backend/tests/ -v

# Run a single test file
pytest backend/tests/test_metrics.py -v

# Test with coverage
pytest backend/tests/ -v --cov=backend --cov-report=term-missing

# Lint
ruff check backend/
```

### Database migrations
```bash
cd backend
alembic upgrade head       # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
```

## Architecture

This is a full-stack gait analysis app that processes side-view running videos to extract biomechanical metrics.

**Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Clerk auth, deployed to Vercel.

**Backend:** FastAPI + Celery worker, PostgreSQL, Redis, deployed to Render via `render.yaml`.

**Storage:** Cloudflare R2 (S3-compatible) for videos and images; local disk for dev.

### Video Processing Pipeline
```
Upload → API stores raw video → Celery task enqueued
→ Worker: video_preprocessor → pose_extractor (MediaPipe) → metrics → heuristics
→ visualizer (annotated video) → dashboard (Matplotlib PNG) → reporter (text)
→ upload outputs to R2 → update DB status=complete
```

Each pipeline step is a separate module in `backend/`. The `job_runner.py` orchestrates all steps.

### Authentication
- Clerk JWT (RS256) via JWKS endpoint, verified in `backend/main.py` via `_verify_jwt()`
- Dev mode: unset `CLERK_JWKS_URL` → all requests become `"dev-user"` (no auth check)
- Frontend: `middleware.ts` protects `/runs` (list only); `/runs/[id]` is intentionally public for sharing

### Key Design Decisions
- **Worker concurrency = 1**: Prevents OOM when processing long/large videos
- **Presigned URLs**: R2 assets served via 1-hour presigned URLs, cached 30 min in `TTLCache` in `main.py`
- **GAIT_MAX_FRAMES** (default 900) and **GAIT_MAX_WIDTH** (default 1280): Env vars that limit video dimensions to manage memory
- **API rewrites**: `frontend/next.config.js` rewrites `/api/*` to `$NEXT_PUBLIC_API_URL` (falls back to `localhost:8000`)

### Frontend Routes
| Route | Auth | Purpose |
|-------|------|---------|
| `/` | Public | Upload video + height |
| `/about` | Public | Info page |
| `/runs` | **Protected** | User's run history + charts |
| `/runs/[id]` | Public | Run detail — shareable link |

### Backend API Routes
| Method | Path | Purpose |
|--------|------|---------|
| `POST /api/runs` | Create run (multipart: file, height_cm) |
| `GET /api/runs/{id}/status` | Poll status + progress_pct |
| `GET /api/runs/{id}` | Full run detail + presigned URLs |
| `GET /api/runs` | List user's runs |
| `DELETE /api/runs/{id}` | Delete run + R2 objects |

### Database Schema
The `Run` table (UUID primary key) stores: `user_id` (Clerk), `status` enum (`processing`/`complete`/`failed`), `progress_pct`, `height_cm`, `results_json` (JSONB), R2 object keys, `preprocessing_meta`, `recorded_at`.

### Custom Theme
Dark-first UI with Tailwind custom tokens: primary green `#00C896`, dark background `#0F0F0F`, secondary `#1A1A1A`.
