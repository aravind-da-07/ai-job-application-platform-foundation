"""
Streamlit dashboard entry point.

Foundation phase note: this ships only a Home page that confirms the
dashboard can start, read settings, and reach the API's health
endpoint. Applications / Candidate / Job Queue / Scheduler /
Authentication / Analytics / Logs / Settings pages are added in the
Automation phase once there is real data to display — the multi-page
navigation structure is left minimal here to avoid shipping empty
placeholder pages.

Run with:
    streamlit run src/dashboard/app.py
"""

from __future__ import annotations

import httpx
import streamlit as st

from src.shared.config.settings import get_settings

st.set_page_config(page_title="AI Job Application Platform", layout="wide")

settings = get_settings()

st.title("AI Job Application Platform")
st.caption(f"Environment: {settings.environment.value}")

st.subheader("System Status")

api_base_url = f"http://localhost:{settings.api_port}{settings.api_prefix}"
try:
    response = httpx.get(f"{api_base_url}/health", timeout=5.0)
    health = response.json()
    status = health.get("data", {}).get("status", "unknown")
    if status == "healthy":
        st.success(f"API is healthy ({api_base_url})")
    else:
        st.warning(f"API is reachable but reports status: {status}")
    st.json(health)
except httpx.RequestError as exc:
    st.error(f"Could not reach the API at {api_base_url}: {exc}")
    st.info("Start the API first: `uvicorn src.api.main:app --reload`")

st.divider()
st.info(
    "This is the Foundation-phase dashboard. Applications, Candidate, Job "
    "Queue, Scheduler, Analytics, and Logs pages will be added as their "
    "underlying modules are implemented."
)
