# app.py
import streamlit as st
import requests
import json

# ------------------------------------------
# CONFIG
# ------------------------------------------
API_BASE = "https://youtube-research-agent-1-gz7b.onrender.com"   # Change to your deployed FastAPI URL

st.set_page_config(page_title="YouTube Research Agent", layout="wide")


# ------------------------------------------
# Backend helpers
# ------------------------------------------
def call_backend(query: str):
    """Calls /query endpoint"""
    try:
        resp = requests.post(f"{API_BASE}/query", json={"query": query}, timeout=200)
        if resp.status_code != 200:
            st.error(f"Backend Error {resp.status_code}: {resp.text}")
            return None
        return resp.json()
    except Exception as e:
        st.error(f"Request failed: {str(e)}")
        return None


def export_from_backend(payload: dict, fmt="html"):
    """Calls /export endpoint and returns raw bytes"""
    try:
        resp = requests.post(
            f"{API_BASE}/export?format={fmt}",
            json=payload,
            timeout=200
        )
        if resp.status_code == 200:
            return resp.content
        else:
            st.error(f"Export failed ({resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        st.error(f"Export request failed: {str(e)}")
        return None


# ------------------------------------------------------
# UI
# ------------------------------------------------------
st.title("📊 YouTube Research Agent")
st.markdown("""
Analyze any YouTube channel.  
""")

query = st.text_input("Enter channel handle / URL / name", placeholder="e.g., @dhruvrathee or Dhruv Rathee")
run_btn = st.button("🔍 Analyze Channel")

if run_btn:
    if not query.strip():
        st.warning("Please type a channel name or handle.")
        st.stop()

    with st.spinner("Running analysis..."):
        data = call_backend(query)

    if not data:
        st.stop()

    # Extract data
    channel = data.get("channel", {})
    videos = data.get("videos", [])
    analysis = data.get("analysis", {})
    semantic_used = data.get("semantic_used", 0)

    # ------------------------------------------------------
    # Channel Summary
    # ------------------------------------------------------
    st.header(channel.get("snippet", {}).get("title", "Channel"))

    c_snip = channel.get("snippet", {})
    c_stats = channel.get("statistics", {})

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Description:** {c_snip.get('description', 'N/A')}")
        st.write(f"**Country:** {c_snip.get('country', 'N/A')}")

    with col2:
        st.write(f"**Subscribers:** {c_stats.get('subscriberCount', 'N/A')}")
        st.write(f"**Total Views:** {c_stats.get('viewCount', 'N/A')}")
        st.write(f"**Total Videos:** {c_stats.get('videoCount', 'N/A')}")
        st.write(f"**Semantic Items Used:** {semantic_used}")

    st.markdown("---")

    # ------------------------------------------------------
    # Video List
    # ------------------------------------------------------
    st.subheader("🎥 Video Metadata (sample)")

    if videos:
        st.dataframe(videos)
    else:
        st.info("No videos fetched.")

    st.markdown("---")

    # ------------------------------------------------------
    # LLM Analysis Report
    # ------------------------------------------------------
    st.subheader("🧠 AI Channel Analysis")

    report = analysis.get("report") if isinstance(analysis, dict) else analysis

    if isinstance(report, dict):
        st.write("### Executive Summary")
        st.write(report.get("executive_summary", "Not Available"))

        st.write("### Key Metrics")
        st.json(report.get("metrics", {}))

        st.write("### Themes")
        st.json(report.get("themes", []))

        st.write("### Recommendations")
        st.json(report.get("recommendations", []))

        st.write("### Engagement Insights")
        st.json(report.get("engagement_insights", []))

        st.write("### Trends")
        st.json(report.get("trends", {}))
    else:
        st.write(report)

    st.markdown("---")

    # ------------------------------------------------------
    # Semantic Neighbors
    # ------------------------------------------------------
    st.subheader("🔎 Top Semantic Matches (HNSW)")

    neighbors = analysis.get("seed_neighbors") or analysis.get("neighbors") or []
    if neighbors:
        st.json(neighbors)
    else:
        st.info("No semantic neighbors identified.")

    st.markdown("---")

    # ------------------------------------------------------
    # EXPORT SECTION — FIXED (NO PAGE REFRESH)
    # ------------------------------------------------------
    st.subheader("📥 Export Report")

    export_payload = {
        "channel": channel,
        "analysis": analysis
    }

    # Fetch all export formats in advance
    html_bytes = export_from_backend(export_payload, "html")
    txt_bytes = export_from_backend(export_payload, "txt")
    docx_bytes = export_from_backend(export_payload, "docx")

    colA, colB, colC = st.columns(3)

    with colA:
        if docx_bytes:
            st.download_button(
                label="⬇ Download DOCX",
                data=docx_bytes,
                file_name=f"{c_snip.get('title', 'report')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    with colB:
        if html_bytes:
            st.download_button(
                label="⬇ Download HTML",
                data=html_bytes,
                file_name=f"{c_snip.get('title', 'report')}.html",
                mime="text/html"
            )

    with colC:
        if txt_bytes:
            st.download_button(
                label="⬇ Download TXT",
                data=txt_bytes,
                file_name=f"{c_snip.get('title', 'report')}.txt",
                mime="text/plain"
            )
