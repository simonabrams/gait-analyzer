"""
Shared About and FAQ content for the main app sidebar and the About page.
"""


def render_about_content():
    import streamlit as st
    st.markdown("""
    Gait Analyzer helps you understand your running form by looking at a short video of you running from the side.
    It gives you simple feedback on things like your step rate (cadence), how much you bounce, and how your knee and posture look at foot strike—with plain-English tips when something might be worth improving.
    """)
    st.markdown("**How it works**")
    st.markdown("""
    1. **You upload a video** — A short clip of yourself running, filmed from the side (e.g. 15–30 seconds), with your full body in frame.

    2. **The app finds your body in each frame** — It uses an on-device body-tracking model to detect key points (shoulders, hips, knees, ankles, etc.) in every frame. No human ever watches your video.

    3. **It measures your gait** — From those points it computes metrics such as:
    - **Cadence** — how many steps per minute (many runners aim for around 170+).
    - **Vertical oscillation** — how much your torso moves up and down (less is often more efficient).
    - **Knee angle at foot strike** — a bit of bend at landing can help reduce impact.

    4. **You get results** — An annotated video (skeleton overlay), charts, and a short report with recommendations. You can download everything to your own device; nothing is kept on our servers.
    """)
    st.markdown("## FAQ ##")
    st.markdown("**Are my videos stored?**")
    st.markdown("""
    No. Your video is only used while your analysis is running. It is held temporarily in memory (and in a short-lived temporary file) only for the duration of that run. When you start a new analysis or leave the app, those temporary files are removed. We do not save, archive, or have access to your videos after your session.
    """)
    st.markdown("**How is the video analyzed?**")
    st.markdown("""
    The analysis runs on the same servers that host this app. A standard body-tracking model (Google's MediaPipe Pose) runs on each frame to detect body landmarks. From those landmarks, we compute gait metrics and compare them to simple, evidence-based targets. The logic is fully automated; no one views or reviews your video.
    """)
    st.markdown("**Is my data private?**")
    st.markdown("""
    Yes. Your video is not stored permanently. It is not shared with third parties. The processing happens in the same environment that serves the app; results are shown only to you in your browser. If you download the report or annotated video, those files exist only on your device. We do not collect or retain personal data from your uploads or results.
    """)
    st.markdown("**Who can see my analysis?**")
    st.markdown("""
    Only you. Analyses are not saved on our side. Each time you run the app you see only the results of your current (or most recent) run in that browser session. There is no account or history of past analyses stored by us.
    """)
    st.markdown("**Can I use this for medical or training decisions?**")
    st.markdown("""
    This app is for general fitness and curiosity only. It is not a medical or clinical tool. Do not use it to diagnose injury or replace advice from a doctor or qualified coach. When in doubt, consult a healthcare or sports professional.
    """)
