# Gait Analyzer

Analyzes running gait from a side-view video using MediaPipe Pose and rule-based heuristics. Produces an annotated video, metrics dashboard, structured JSON results, and a text report with recommendations.

## Requirements

- Python 3.10+
- See `requirements.txt` for dependencies (MediaPipe, OpenCV, NumPy, Matplotlib)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

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

## Extending to a web app

The code is structured so that:

- **Pose extraction** (`pose_extractor.py`) takes a list of frames and returns landmark data (no file I/O).
- **Metrics** (`metrics.py`) and **heuristics** (`heuristics.py`) take that data plus `height_cm` (and FPS) and return a results dict.
- **Visualizer**, **dashboard**, and **reporter** consume the results dict only.

So a FastAPI or Streamlit app can: accept an uploaded video and user height, run the same pipeline in memory, and return or stream the JSON, annotated frames, dashboard image, and report without changing these modules.
