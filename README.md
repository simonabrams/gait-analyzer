# Gait Analyzer

Analyzes running gait from a side-view video using MediaPipe Pose and rule-based heuristics. Produces an annotated video, metrics dashboard, structured JSON results, and a text report with recommendations.

## Requirements

- Python 3.10+
- See `requirements.txt` for dependencies (MediaPipe, OpenCV, NumPy, Matplotlib, Streamlit)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Web app (recommended)

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

**Notes:** On the free tier, the app may sleep after inactivity; the first request after that can be slow. The Dockerfile is already set up to run Streamlit on port 8501; Render maps that for you.

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
