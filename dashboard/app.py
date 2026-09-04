"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: dashboard/app.py (Streamlit Web Remote Dashboard & Terminal)
================================================================================
"""

import streamlit as st
import requests
import time
import os

# Page Configuration
st.set_page_config(
    page_title="Kushida — Luxury Web Remote",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ------------------------------------------------------------------------------
# 1. LUXURY CUSTOM CSS STYLING (Deep Space Black & Neon Accents)
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global Reset & Deep Space Background */
    .stApp {
        background: #0d0d12 !important;
        color: #f4f4f5 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #12121a !important;
        border-right: 1px solid rgba(107, 33, 168, 0.25) !important;
    }

    /* Cards and Glass Panels */
    .luxury-card {
        background: linear-gradient(135deg, rgba(24, 24, 32, 0.85), rgba(18, 18, 24, 0.95));
        border: 1px solid rgba(107, 33, 168, 0.35);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(107, 33, 168, 0.15);
        margin-bottom: 20px;
    }

    .now-playing-title {
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 4px;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
    }

    .now-playing-artist {
        font-size: 16px;
        color: #38bdf8;
        font-weight: 500;
        margin-bottom: 16px;
    }

    /* Badge Pills */
    .pill-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
        background: rgba(107, 33, 168, 0.2);
        border: 1px solid rgba(107, 33, 168, 0.4);
        color: #c084fc;
    }

    .pill-badge-blue {
        background: rgba(56, 189, 248, 0.15);
        border: 1px solid rgba(56, 189, 248, 0.35);
        color: #38bdf8;
    }

    .pill-badge-green {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #10b981;
    }

    /* Streamlit Button Overrides */
    div.stButton > button {
        background: #181824 !important;
        color: #f4f4f5 !important;
        border: 1px solid rgba(107, 33, 168, 0.4) !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: #6b21a8 !important;
        color: #ffffff !important;
        border-color: #a855f7 !important;
        box-shadow: 0 0 15px rgba(107, 33, 168, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* Primary Buttons */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6b21a8, #4c1d95) !important;
        border: 1px solid #a855f7 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 15px rgba(107, 33, 168, 0.4) !important;
    }

    /* Queue Item Card */
    .queue-row {
        background: rgba(24, 24, 32, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #6b21a8, #38bdf8) !important;
    }

    /* Sliders */
    div[data-baseweb="slider"] {
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 2. HELPER FUNCTIONS & API CALLERS
# ------------------------------------------------------------------------------
def fetch_api(endpoint: str, method: str = "GET", json_data: dict = None):
    """Generic API requester."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=3)
        elif method == "POST":
            resp = requests.post(url, json=json_data, timeout=3)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=3)
        else:
            return None

        if resp.status_code in [200, 201]:
            return resp.json()
        return None
    except Exception:
        return None


def format_ms(milliseconds: int) -> str:
    """Format milliseconds into MM:SS."""
    if not milliseconds or milliseconds < 0:
        return "00:00"
    total_sec = int(milliseconds // 1000)
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{m:02d}:{s:02d}"


# ------------------------------------------------------------------------------
# 3. SIDEBAR: SERVER / GUILD SELECTION & SYSTEM HEALTH
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🌌 **KUSHIDA** `v2.0`")
    st.caption("Luxury Discord Music & Web Remote Control")

    st.markdown("---")

    # Fetch bot status
    status_data = fetch_api("/api/status")
    if status_data and status_data.get("status") == "online":
        st.markdown(f"🟢 **System Online** • `{status_data.get('latency_ms', 0)}ms`")
        st.caption(f"Active Players: **{status_data.get('active_players', 0)}** • Bot: `{status_data.get('user', '')}`")
    else:
        st.error("🔴 **API Disconnected** • Check if `main.py` is running.")

    st.markdown("---")
    st.subheader("Discord Servers")

    guilds = fetch_api("/api/guilds") or []
    if not guilds:
        st.info("No servers found. Invite Kushida to a server!")
        selected_guild_id = None
    else:
        guild_options = {g["name"]: g["id"] for g in guilds}
        selected_guild_name = st.selectbox("Select Active Server", list(guild_options.keys()))
        selected_guild_id = guild_options[selected_guild_name]

    st.markdown("---")
    st.subheader("✨ AI Mood Shortcuts")
    st.caption("Push curated vibe queues to VC")

    mood_col1, mood_col2 = st.columns(2)
    with mood_col1:
        if st.button("🌊 Lo-Fi Chill", use_container_width=True):
            if selected_guild_id:
                fetch_api(f"/api/control/{selected_guild_id}/play", "POST", {"query": "Lo-Fi Beats to Relax"})
                st.toast("Queued Lo-Fi Chill!")
        if st.button("⚡ Phonk Hype", use_container_width=True):
            if selected_guild_id:
                fetch_api(f"/api/control/{selected_guild_id}/play", "POST", {"query": "Phonk Drift Best"})
                st.toast("Queued Phonk Drift!")
    with mood_col2:
        if st.button("🌃 Late Night", use_container_width=True):
            if selected_guild_id:
                fetch_api(f"/api/control/{selected_guild_id}/play", "POST", {"query": "Late Night Synthwave"})
                st.toast("Queued Late Night Synth!")
        if st.button("💪 Gym Beast", use_container_width=True):
            if selected_guild_id:
                fetch_api(f"/api/control/{selected_guild_id}/play", "POST", {"query": "Workout Hype Motivation"})
                st.toast("Queued Gym Beats!")

    # Auto refresh toggle
    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Live Polling (Every 3s)", value=True)
    if auto_refresh:
        time.sleep(3)
        st.rerun()


# ------------------------------------------------------------------------------
# 4. MAIN PANEL: NOW PLAYING & PLAYBACK CONTROLS
# ------------------------------------------------------------------------------
st.title("🎛️ **Audio Control Center**")

if not selected_guild_id:
    st.warning("Please select a Discord server from the sidebar.")
    st.stop()

# Fetch Guild Player State
player_status = fetch_api(f"/api/status/{selected_guild_id}")

col_left, col_right = st.columns([1.4, 1.0])

with col_left:
    st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)

    if player_status and player_status.get("current_track"):
        track = player_status["current_track"]
        pos_ms = player_status.get("position_ms", 0)
        dur_ms = track.get("duration_ms", 1)
        progress_val = min(max(pos_ms / dur_ms if dur_ms > 0 else 0.0, 0.0), 1.0)

        # Header Row: Artwork + Details
        art_col, info_col = st.columns([1, 2])
        with art_col:
            art_url = track.get("artwork_url") or "https://placehold.co/400x400/0d0d12/6b21a8?text=Kushida"
            st.image(art_url, use_container_width=True)

        with info_col:
            st.markdown(f"<div class='now-playing-title'>{track['title']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='now-playing-artist'>by {track['author']}</div>", unsafe_allow_html=True)

            # Badges
            vol_val = player_status.get("volume", 100)
            loop_val = player_status.get("loop_mode", "off")
            st.markdown(
                f"<span class='pill-badge'>🔊 {vol_val}%</span>"
                f"<span class='pill-badge pill-badge-blue'>🔁 {loop_val.upper()}</span>"
                f"<span class='pill-badge pill-badge-green'>⚡ Lavalink v4 HQ</span>",
                unsafe_allow_html=True
            )

        # Progress Bar & Time Stamps
        st.markdown("<br>", unsafe_allow_html=True)
        st.progress(progress_val)
        time_left_col, time_right_col = st.columns(2)
        with time_left_col:
            st.caption(f"⏱️ `{format_ms(pos_ms)}`")
        with time_right_col:
            st.caption(f"<div style='text-align: right;'>`{format_ms(dur_ms)}` ⏳</div>", unsafe_allow_html=True)

    else:
        st.markdown("<div class='now-playing-title'>No Track Active</div>", unsafe_allow_html=True)
        st.caption("Voice channel is idle. Search a song below to begin streaming.")
        st.progress(0.0)

    st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # PLAYBACK CONTROL BUTTONS
    # --------------------------------------------------------------------------
    btn_c1, btn_c2, btn_c3, btn_c4, btn_c5, btn_c6 = st.columns(6)

    with btn_c1:
        if st.button("⏮️ Prev", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/previous", "POST")
            st.rerun()

    with btn_c2:
        is_paused = player_status.get("paused", False) if player_status else False
        play_label = "▶️ Resume" if is_paused else "⏸️ Pause"
        if st.button(play_label, type="primary", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/pause", "POST")
            st.rerun()

    with btn_c3:
        if st.button("⏭️ Next", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/skip", "POST")
            st.rerun()

    with btn_c4:
        if st.button("🔀 Shuffle", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/shuffle", "POST")
            st.toast("Queue shuffled!")
            st.rerun()

    with btn_c5:
        if st.button("⏹️ Stop", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/stop", "POST")
            st.rerun()

    with btn_c6:
        if st.button("🔄 Sync", use_container_width=True):
            st.rerun()

    # Volume & Filters
    st.markdown("<br>", unsafe_allow_html=True)
    vol_slider = st.slider(
        "Master Volume",
        min_value=0,
        max_value=200,
        value=player_status.get("volume", 100) if player_status else 100,
        step=5
    )
    if vol_slider != (player_status.get("volume", 100) if player_status else 100):
        fetch_api(f"/api/control/{selected_guild_id}/volume", "POST", {"volume": vol_slider})

    # Studio Audio Filters
    st.subheader("🎛️ Studio Filter Presets")
    f_c1, f_c2, f_c3, f_c4, f_c5 = st.columns(5)
    with f_c1:
        if st.button("🔊 Bassboost", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/filter", "POST", {"preset": "bassboost"})
            st.toast("Applied Bassboost!")
    with f_c2:
        if st.button("⚡ Nightcore", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/filter", "POST", {"preset": "nightcore"})
            st.toast("Applied Nightcore!")
    with f_c3:
        if st.button("🎧 8D Spatial", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/filter", "POST", {"preset": "8d"})
            st.toast("Applied 8D Spatial Audio!")
    with f_c4:
        if st.button("🌊 Vaporwave", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/filter", "POST", {"preset": "vaporwave"})
            st.toast("Applied Vaporwave!")
    with f_c5:
        if st.button("✨ Reset Filters", use_container_width=True):
            fetch_api(f"/api/control/{selected_guild_id}/filter", "POST", {"preset": "reset"})
            st.toast("Audio Filters Reset to HQ Studio!")


# ------------------------------------------------------------------------------
# 5. RIGHT COLUMN: REMOTE SEARCH & QUEUE MANAGER
# ------------------------------------------------------------------------------
with col_right:
    # Remote Song Search & Pusher
    st.markdown("<div class='luxury-card'>", unsafe_allow_html=True)
    st.subheader("🔍 Push Music to VC")
    search_query = st.text_input("Enter Track Name, Artist, or YouTube URL", placeholder="e.g. Starboy - The Weeknd")

    if st.button("🚀 Stream to Discord VC", type="primary", use_container_width=True):
        if search_query.strip():
            res = fetch_api(f"/api/control/{selected_guild_id}/play", "POST", {"query": search_query.strip()})
            if res and res.get("success"):
                st.success(res.get("message", "Queued successfully!"))
                st.rerun()
            else:
                st.error("Failed to queue song. Ensure bot is connected to a voice channel.")
        else:
            st.warning("Please enter a song name or URL.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Queue Manager
    st.subheader("📑 Upcoming Queue")
    queue_data = fetch_api(f"/api/queue/{selected_guild_id}")

    if queue_data and queue_data.get("tracks"):
        tracks = queue_data["tracks"]
        st.caption(f"**{len(tracks)} tracks** waiting in line")

        for t in tracks[:10]:
            idx = t["index"]
            title_short = t["title"][:30] + "..." if len(t["title"]) > 30 else t["title"]
            dur = format_ms(t.get("duration_ms", 0))

            q_col1, q_col2, q_col3, q_col4 = st.columns([0.6, 3, 0.6, 0.6])
            with q_col1:
                st.write(f"`{idx + 1:02d}`")
            with q_col2:
                st.write(f"**{title_short}**\n`{t['author']}` • `{dur}`")
            with q_col3:
                # Move Up
                if idx > 0:
                    if st.button("▲", key=f"up_{idx}", use_container_width=True):
                        fetch_api(f"/api/control/{selected_guild_id}/reorder", "POST", {"from_index": idx, "to_index": idx - 1})
                        st.rerun()
            with q_col4:
                # Remove
                if st.button("✕", key=f"del_{idx}", use_container_width=True):
                    fetch_api(f"/api/control/{selected_guild_id}/queue/{idx}", "DELETE")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("Queue is empty. Use the search bar above to queue songs.")
