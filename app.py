"""
Streamlit entry point for Gait Analyzer. Wraps the existing pipeline;
does not modify pose_extractor, metrics, heuristics, visualizer, dashboard, reporter.
"""

import os
import tempfile
import streamlit as st

from backend.about_content import render_about_content

FILMING_TIPS = """
- **Side view only** — film the runner from the left or right, not front or back.
- **Camera height** — roughly hip height so hip, knee, and ankle are in a clear line.
- **Distance** — 10–20 feet (3–6 m) so the full stride is in frame.
- **Full body in frame** — head to feet for best scaling and metrics.
- **5–10+ strides** — at least 15–30 seconds of steady-state running.
- **Stable shot** — use a tripod; good lighting and minimal occlusion help.
"""

METRIC_CONFIG = [
    ("Cadence", "cadence_avg", 170, "spm", True),
    ("Vertical Oscillation", "vertical_osc_avg_cm", 10, "cm", False),
    ("Knee Angle", "knee_angle_strike_avg_deg", 15, "°", True),
]
PASS_FAIL_ROW = [
    ("Cadence (spm)", "cadence_avg", "≥170", lambda v: v is not None and v >= 170),
    ("Vertical osc (cm)", "vertical_osc_avg_cm", "≤10", lambda v: v is not None and v <= 10),
    ("Knee @ strike (°)", "knee_angle_strike_avg_deg", "≥15", lambda v: v is not None and v >= 15),
    ("Foot strike (cm)", "foot_strike_position_avg_cm", "≤10", lambda v: v is not None and v <= 10),
    ("Trunk lean (°)", "trunk_lean_avg_deg", "≤15", lambda v: v is not None and v <= 15),
]


def _cleanup_previous_temp():
    if "analysis_temp_paths" in st.session_state and st.session_state.analysis_temp_paths:
        for p in st.session_state.analysis_temp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass
        st.session_state.analysis_temp_paths = []


def main():
    st.set_page_config(page_title="Gait Analyzer", layout="wide")
    st.title("Gait Analyzer \N{RUNNER}")

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "analysis_temp_paths" not in st.session_state:
        st.session_state.analysis_temp_paths = []

    with st.sidebar:
        st.subheader("Inputs")
        video_file = st.file_uploader(
            "Upload your run video",
            type=["mp4", "mov"],
            help="Filmed from the side, full body visible, 10–20 feet away.",
        )
        height_cm = st.number_input(
            "Height (cm)",
            min_value=100,
            max_value=250,
            value=175,
            step=1,
        )
        analyze_clicked = st.button(
            "Analyze",
            type="primary",
            disabled=(video_file is None),
        )
        with st.expander("Filming tips"):
            st.markdown(FILMING_TIPS)
        with st.expander("About & FAQ"):
            render_about_content()

    if video_file is not None and video_file.size > 200 * 1024 * 1024:
        st.warning(
            "This video is over 200 MB. Streamlit Cloud's free tier has a 1 GB memory limit; "
            "large uploads may cause the app to run out of memory."
        )

    if analyze_clicked and video_file is not None:
        _cleanup_previous_temp()
        video_path = None
        max_frames = None
        max_width = None
        try:
            nf = int(os.environ.get("GAIT_MAX_FRAMES", "450"))
            nw = int(os.environ.get("GAIT_MAX_WIDTH", "854"))
            max_frames = nf if nf > 0 else None
            max_width = nw if nw > 0 else None
        except ValueError:
            max_frames = 450
            max_width = 854
        try:
            from backend.job_runner import run_analysis
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_file.getvalue())
                video_path = tmp.name
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            with st.spinner("Analyzing your gait..."):
                def on_progress(percent, message):
                    progress_bar.progress(min(percent / 100.0, 1.0))
                    status_placeholder.caption(message)

                out = run_analysis(
                    video_path,
                    float(height_cm),
                    progress_callback=on_progress,
                    max_frames=max_frames,
                    max_width=max_width,
                )
            progress_bar.progress(1.0)
            status_placeholder.caption("Done.")
            st.session_state.analysis_result = out
            st.session_state.analysis_temp_paths = out.get("temp_paths", [])
        except MemoryError:
            st.error(
                "The server ran out of memory analyzing this video. Try a shorter clip (e.g. 15–20 seconds), "
                "a lower resolution, or run the app locally for longer videos."
            )
            st.session_state.analysis_result = None
        except Exception as e:
            is_env_error = isinstance(e, (ImportError, OSError)) or (
                getattr(e, "msg", "") or str(e)
            ).find("libGL") != -1
            if is_env_error:
                st.error(
                    "Video analysis isn't available in this environment (missing system libraries). "
                    "Run the app locally for full functionality: `streamlit run app.py`"
                )
            else:
                st.error("Analysis failed. Please check your video and try again.")
            with st.expander("Error details"):
                st.exception(e)
            st.session_state.analysis_result = None
        finally:
            if video_path and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                except OSError:
                    pass

    result = st.session_state.analysis_result
    if result is None:
        st.info("Upload a video and click **Analyze** to run gait analysis.")
        return

    if result.get("truncated"):
        n = result.get("frames_used", 0)
        st.info(
            f"Video was limited to {n} frames (~{n // 30:.0f} sec at 30 fps) and reduced resolution to avoid running out of memory. "
            "For full-length analysis, run the app locally or set `GAIT_MAX_FRAMES` / `GAIT_MAX_WIDTH` in your environment."
        )

    results = result["results"]
    summary = results.get("summary", {})
    flags = results.get("flags", [])

    tab1, tab2, tab3 = st.tabs(["Video", "Dashboard", "Report"])

    with tab1:
        ann_path = result.get("annotated_video_path")
        if ann_path and os.path.exists(ann_path):
            st.video(ann_path)
            with open(ann_path, "rb") as f:
                st.download_button(
                    "Download annotated video (MP4)",
                    data=f.read(),
                    file_name="gait_annotated.mp4",
                    mime="video/mp4",
                    key="dl_video",
                )

    with tab2:
        dash_path = result.get("dashboard_path")
        if dash_path and os.path.exists(dash_path):
            st.image(dash_path, use_container_width=True)
            with open(dash_path, "rb") as f:
                st.download_button(
                    "Download dashboard (PNG)",
                    data=f.read(),
                    file_name="gait_dashboard.png",
                    mime="image/png",
                    key="dl_dashboard",
                )
        col1, col2, col3 = st.columns(3)
        for i, (label, key, target, unit, higher_is_better) in enumerate(METRIC_CONFIG):
            val = summary.get(key)
            col = [col1, col2, col3][i % 3]
            if val is not None:
                delta = (val - target) if higher_is_better else (target - val)
                delta_str = f"{delta:+.1f} vs target"
                col.metric(
                    label,
                    f"{val} {unit}",
                    delta_str,
                    delta_color="normal" if delta >= 0 else "inverse",
                )
            else:
                col.metric(label, "—", "No data")

    with tab3:
        for f in flags:
            metric_name = f.get("metric", "Issue")
            st.markdown(f"**{metric_name}**")
            st.warning(f.get("recommendation", ""), icon="⚠️")
            st.caption(f"Value: {f.get('value')}, threshold: {f.get('threshold')}")
        if not flags:
            st.success("No issues flagged. Metrics within target ranges.")

        rows = []
        for label, key, target_str, is_pass in PASS_FAIL_ROW:
            val = summary.get(key)
            rows.append({
                "Metric": label,
                "Value": val if val is not None else "—",
                "Target": target_str,
                "Pass": "Yes" if is_pass(val) else "No",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        res_path = result.get("results_path")
        rep_path = result.get("report_path")
        c1, c2 = st.columns(2)
        if res_path and os.path.exists(res_path):
            with open(res_path, "rb") as f:
                c1.download_button(
                    "Download results.json",
                    data=f.read(),
                    file_name="results.json",
                    mime="application/json",
                    key="dl_json",
                )
        if rep_path and os.path.exists(rep_path):
            with open(rep_path, "r") as f:
                c2.download_button(
                    "Download report (.txt)",
                    data=f.read(),
                    file_name="gait_report.txt",
                    mime="text/plain",
                    key="dl_txt",
                )


if __name__ == "__main__":
    main()
