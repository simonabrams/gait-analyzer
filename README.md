# Gait Analyzer

Analyzes running gait from a side-view video using MediaPipe Pose and rule-based heuristics. Produces an annotated video, metrics dashboard, structured JSON results, and a text report with recommendations.

- **Phase 2 (Streamlit):** Single-page app in the repo root (`app.py`, `streamlit run app.py`).
- **Phase 3 (Full-stack):** Next.js frontend + FastAPI backend + Celery + PostgreSQL + Redis + Cloudflare R2. Run history, progress charts, and shareable run links.

---

## Phase 3: Full-stack (Next.js + FastAPI)

### Project structure

- `frontend/` — Next.js 14 (App Router), TypeScript, Tailwind, Recharts, react-dropzone.
- `backend/` — FastAPI, SQLAlchemy, Celery worker, R2 storage; reuses `pose_extractor`, `metrics`, `heuristics`, `visualizer`, `dashboard`, `reporter`, `job_runner`.

### Quick start (local testing, no R2)

You need **Docker** (Desktop or Engine) and **Python** with backend deps. From the repo root:

```bash
pip install -r backend/requirements.txt
```

Then run (uses `docker compose` or `docker-compose`):

```bash
./scripts/run-local.sh
```

In another terminal, start the frontend:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, upload a video (MP4/MOV) and set height — uploads use local disk (Docker volume) so no Cloudflare R2 is needed.

### Local development (step by step)

1. **Start Postgres and Redis:**

   ```bash
   docker-compose up -d postgres redis
   ```

2. **Apply migrations** (install backend deps first: `pip install -r backend/requirements.txt`):

   ```bash
   cd backend && alembic upgrade head && cd ..
   ```

   `DATABASE_URL` defaults to `postgresql://postgres:postgres@localhost:5432/gait_analyzer`.

3. **Start API and worker** (uses local storage by default so uploads work without R2):

   ```bash
   docker-compose up api worker
   ```

   API: http://localhost:8000. Docs: http://localhost:8000/docs.

4. **Frontend** (separate terminal):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Optional: copy `frontend/.env.local.example` to `frontend/.env.local` and set `NEXT_PUBLIC_API_URL=http://localhost:8000` if your API is elsewhere.

5. **R2 (optional):** To use Cloudflare R2 instead of local disk, set `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` on the API and worker, and do **not** set `LOCAL_STORAGE_PATH` (or remove it from docker-compose).

### Environment variables

| Variable | Where | Description |
|----------|--------|-------------|
| `DATABASE_URL` | API, worker | PostgreSQL URL (e.g. `postgresql://user:pass@host:5432/db`) |
| `REDIS_URL` | API, worker | Redis URL (e.g. `redis://localhost:6379/0`) |
| `CORS_ORIGINS` | API | Allowed frontend origins (e.g. `http://localhost:3000`) |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` | API, worker | Cloudflare R2 (S3-compatible) |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend API base URL (e.g. `https://your-api.onrender.com`) |
| `GAIT_MAX_FRAMES` | Worker | Max frames to process (e.g. `900` ≈ 30 s at 30 fps). Reduces memory use. |
| `GAIT_MAX_WIDTH` | Worker | Max frame width in pixels (e.g. `1280`). Reduces memory use. |

### Worker OOM / stalled runs

If the worker is killed with **signal 9 (SIGKILL)** or **WorkerLostError**, the OS likely ran out of memory (OOM). The run will stay in "processing" because the worker never got to update the DB. To avoid this:

- The worker runs with **concurrency 1** (`-c 1`) so only one video is processed at a time.
- Set **GAIT_MAX_FRAMES** and **GAIT_MAX_WIDTH** on the worker (e.g. in `docker-compose.yml`) to cap memory; defaults in the stack are 900 frames and 1280 px width.
- Use shorter or lower-resolution videos. If it still OOMs, lower `GAIT_MAX_FRAMES` (e.g. `450`) or `GAIT_MAX_WIDTH` (e.g. `854`).

### Deployment

- **Backend (Render):** Use `render.yaml` to create the web service (API), private service (Celery worker), and PostgreSQL. Create a **Redis** instance in the Render dashboard and set `REDIS_URL` for both API and worker. Set R2 and `CORS_ORIGINS` (your Vercel frontend URL) in the dashboard. After first deploy, run Alembic migrations (e.g. via a one-off job or locally with `DATABASE_URL` pointing at Render).
- **Frontend (Vercel):** Deploy the `frontend/` directory. Set `NEXT_PUBLIC_API_URL` to the Render API URL. The run result page (`/runs/[id]`) is server-rendered for shareable link previews (og:title, og:description).

### API routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/runs` | Create run (multipart: file, height_cm) |
| GET | `/api/runs/{id}/status` | Poll status and progress |
| GET | `/api/runs/{id}` | Full run detail + signed video/dashboard URLs |
| GET | `/api/runs` | List runs (for history + charts) |
| DELETE | `/api/runs/{id}` | Delete run and R2 objects |

---

## Phase 2: Streamlit (legacy)

### Requirements

- Python 3.10+
- See `requirements.txt` for dependencies (MediaPipe, OpenCV, NumPy, Matplotlib, Streamlit)

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Usage

Run the Streamlit app locally:

```bash
streamlit run app.py
```

Then open the URL shown in the terminal (usually http://localhost:8501). Upload a video, set your height, and click **Analyze**. Results appear in tabs: annotated video, dashboard chart, and text report with download buttons.

### CLI

```bash
python analyze_gait.py --video path/to/run.mp4 --height 175
```

| Option | Description |
|--------|-------------|
| `--video` | Path to MP4 or MOV file (required) |
| `--height` | Runner height in cm, used to scale distances (required) |
| `--output-dir` | Where to write outputs (default: same directory as the video) |

**Example with custom output directory:**

```bash
python analyze_gait.py --video ~/Videos/treadmill.mp4 --height 175 --output-dir ./results
```

## Deploying to Streamlit Cloud

To run the app as a public web app on [Streamlit Cloud](https://streamlit.io/cloud):

1. Push this project to a **public** GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, then connect the repository and branch.
4. Set **Main file path** to `app.py`.
5. Leave **Advanced settings** as default (no environment variables are required for the basic version).

**Note:** Streamlit Cloud’s free tier has a **1 GB memory limit**. The app warns if an uploaded video is over 200 MB; very large videos may cause the app to run out of memory. For best results, use videos under 200 MB and under a few minutes.

**Video analysis on Cloud:** The Cloud environment may lack system libraries (e.g. for OpenCV/MediaPipe), so **Analyze** can fail with an environment error. The app will still load so you can view About and use the UI; for full video analysis, run the app locally or deploy with Docker (below).

### Deploy with Docker (full video analysis)

The app’s Dockerfile installs the system libraries OpenCV and MediaPipe need, so **Analyze** works in the cloud. You can deploy without installing Docker on your computer by using a host that builds from GitHub.

---

#### Option A: Deploy to Render (no Docker on your machine)

1. **Push your app to GitHub** (if it’s not already there).
   - Create a repo, push your `gait-analyzer` code, and ensure the Dockerfile and `app.py` are in the repo root (or the root of the folder you push).

2. **Sign up at [Render](https://render.com)** and log in (e.g. with GitHub).

3. **Create a new Web Service**
   - Dashboard → **New +** → **Web Service**.
   - Connect your GitHub account if asked, then select the **gait-analyzer** repository (and the branch that has the Dockerfile, usually `main`).

4. **Configure the service**
   - **Name:** e.g. `gait-analyzer`.
   - **Region:** pick one close to you.
   - **Root Directory:** leave blank if the app and Dockerfile are in the repo root; otherwise set it to the folder that contains `app.py` and the Dockerfile.
   - **Runtime:** **Docker** (Render will use your Dockerfile).
   - **Instance type:** Free is enough to try; for heavier video use, a paid instance is more reliable.

5. **Deploy**
   - Click **Create Web Service**. Render will build the image from your Dockerfile and start the app. When it’s done, you’ll get a URL like `https://gait-analyzer-xxxx.onrender.com`.

6. **Use the app**
   - Open that URL in your browser. Upload a video, set height, and click **Analyze**; video analysis should work.

**Notes:** On the free tier, the app may sleep after inactivity; the first request after that can be slow. The Dockerfile runs Streamlit on port 10000 so Render’s proxy can reach it (Render’s default for Docker web services is port 10000). If you see **502 Bad Gateway**, the service may still be starting (retry after a minute), or it may have run out of memory during analysis—try a shorter/smaller video or lower `GAIT_MAX_FRAMES` / `GAIT_MAX_WIDTH`.

**If the instance runs out of memory** when analyzing a video, the app limits input to **450 frames (~15 sec)** and **854px width** by default so it fits in ~512 MB–1 GB RAM. You can override this with environment variables (e.g. in Render: **Environment** tab):
- `GAIT_MAX_FRAMES` — max frames to process (default `450`). Lower it (e.g. `300`) if you still get OOM.
- `GAIT_MAX_WIDTH` — max frame width in pixels (default `854`). Lower it (e.g. `640`) to use less memory.

For a **2 GB RAM instance** (e.g. Render Standard), set `GAIT_MAX_FRAMES=300` and `GAIT_MAX_WIDTH=640` in the service environment to avoid out-of-memory errors. For longer or full-resolution analysis, use a larger instance or run the app locally (no limits).

**Log warnings:** You may see TensorFlow Lite or MediaPipe messages such as "Feedback manager requires a model with a single signature inference" or "NORM_RECT without IMAGE_DIMENSIONS". The app letterboxes each frame to square before pose detection to satisfy MediaPipe’s requirements and reduce the NORM_RECT warning; the annotated output video may be square (letterboxed). The "feedback manager" message is harmless and can be ignored.

---

#### Option B: Run with Docker on your computer (test locally)

Use this to run the same setup as in the cloud on your own machine.

1. **Install Docker**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Mac or Windows (includes Docker Engine). For Linux, install [Docker Engine](https://docs.docker.com/engine/install/) for your distro.
   - Open Docker Desktop (or start the Docker service) so the daemon is running.

2. **Open a terminal** in the project folder (the one that contains `app.py` and the Dockerfile).

3. **Build the image**

   ```bash
   docker build -t gait-analyzer .
   ```

   This reads the Dockerfile and builds an image named `gait-analyzer`. The first time may take a few minutes.

4. **Run the container**

   ```bash
   docker run -p 8501:8501 gait-analyzer
   ```

   This starts the app inside a container and maps port 8501 to your machine.

5. **Open the app**
   - In your browser go to **http://localhost:8501**. Upload a video and run an analysis to confirm everything works.

6. **Stop the app**
   - In the terminal press **Ctrl+C** once. The container will stop.

To run again later, use the same `docker run` command; you only need to run `docker build` again if you change the Dockerfile or requirements.

## Outputs

All files are written next to the video (or in `--output-dir`):

| File | Description |
|------|-------------|
| `results.json` | Full metrics, per-stride data, flags, and recommendations (source of truth) |
| `<name>_annotated.mp4` | Video with skeleton overlay and live metrics; joints involved in flagged issues shown in red |
| `<name>_dashboard.png` | Multi-panel chart: cadence, vertical oscillation, knee angle at strike, summary score |
| `<name>_report.txt` | Plain-text summary and recommendations (also printed to the console) |

## Video capture tips

### Orientation and camera position

- **Side view only.** The runner must be filmed from the **side** (left or right), not front or back. All metrics assume a lateral view.
- **Camera height:** Roughly **hip height** so the hip, knee, and ankle are in a clear line. Too high or too low distorts angles.
- **Distance:** About **10–20 feet (3–6 m)** so the full stride is in frame without the person being too small. Avoid wide-angle distortion by not standing too close.

### What must be in frame

- **Full body is recommended.** Vertical oscillation and real-world distances (cm) are scaled using your height, estimated from hip-to-head in the frame. If the head or hip is cropped, scaling is less accurate.
- **Waist-down can work** for cadence, foot strike, and knee angle if you only need those. Trunk lean and reliable vertical oscillation need the torso and preferably the head in frame. For best results, capture **head to feet**.

### Length and content

- **At least 5–10 full strides** (e.g. 15–30 seconds at normal running pace) so averages and trends are meaningful. More strides improve the summary.
- **Steady-state running:** Avoid the first few steps after starting or right before stopping. Capture a period of consistent pace.
- **Single runner, clear view:** One person in frame, minimal occlusion. Plain background helps pose detection.

### Technical quality

- **Stable shot:** Use a tripod or fixed mount. Shake makes landmark detection noisier.
- **Good lighting:** Enough light so the body silhouette is clear; avoid strong backlight or heavy shadows.
- **Format:** MP4 or MOV; common frame rates (24–60 fps) are fine. Higher fps can improve timing; the tool uses the video’s reported FPS.

## Metrics and thresholds

The report and JSON flag issues when:

| Metric | Target | Flagged when |
|--------|--------|--------------|
| Cadence | ≥ 170 spm | Below 170 steps per minute |
| Vertical oscillation | ≤ 10 cm | Above 10 cm |
| Knee flexion at foot strike | ≥ 15° | Below 15° |
| Overstriding | ≤ 10 cm | Foot strike >10 cm ahead of hip (COM) |
| Trunk lean | ≤ 15° | Forward lean above 15° |

Stride is defined as **left foot strike to next left foot strike**; foot strikes are detected from ankle landmark motion.

The Streamlit app (`app.py`) and `job_runner.py` wrap the same pipeline: pose extraction → metrics → heuristics → visualizer → dashboard → reporter. No changes to those modules are required; the web app calls them with uploaded video and user height.
