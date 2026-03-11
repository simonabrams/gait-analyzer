"""
About page: how the app works, FAQ, and privacy.
"""

import streamlit as st

from backend.about_content import render_about_content

st.set_page_config(page_title="About — Gait Analyzer", layout="wide")
st.title("About Gait Analyzer \N{RUNNER}")

render_about_content()
