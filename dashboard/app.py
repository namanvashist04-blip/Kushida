"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: dashboard/app.py (Streamlit Premium Web Remote — Spotify-Like UI)
  ACCESS: Any Discord server member can open this link and control the bot.
================================================================================
"""

import streamlit as st
import requests
import time
import os
import json

# Page Configuration
st.set_page_config(
    page_title="Kushida — Luxury Web Remote",
    page_icon="🌌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# ------------------------------------------------------------------------------
# 1. LUXURY CSS — PREMIUM SPOTIFY-LIKE DARK THEME
# ------------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ===== GLOBAL RESET ===== */
    .stApp {
        background: linear-gradient(180deg, #0d0d12 0%, #111118 50%, #0a0a10 100%) !important;
        color: #f4f4f5 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    .stApp > header { background: transparent !important; }
    #MainMenu, footer, .stDeployButton { display: none !important; }

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111118, #0d0d14) !important;
        border-right: 1px solid rgba(107, 33, 168, 0.15) !important;
    }

    /* ===== HERO HEADER ===== */
    .hero-header {
        background: linear-gradient(135deg, rgba(107, 33, 168, 0.15) 0%, rgba(56, 189, 248, 0.08) 50%, rgba(16, 185, 129, 0.05) 100%);
        border: 1px solid rgba(107, 33, 168, 0.2);
        border-radius: 20px;
        padding: 28px 36px;
        margin-bottom: 24px;
        backdrop-filter: blur(20px);
    }
    .hero-title {
        font-size: 28px; font-weight: 900; color: #fff;
        background: linear-gradient(135deg, #c084fc, #38bdf8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0; letter-spacing: -0.5px;
    }
    .hero-sub { font-size: 13px; color: #71717a; margin-top: 4px; }

    /* ===== GLASS CARD ===== */
    .glass-card {
        background: linear-gradient(135deg, rgba(24, 24, 38, 0.7), rgba(18, 18, 28, 0.85));
        border: 1px solid rgba(107, 33, 168, 0.2);
        border-radius: 16px;
        padding: 24px 28px;
        backdrop-filter: blur(16px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.03);
        margin-bottom: 16px;
    }

    /* ===== NOW PLAYING CARD ===== */
    .np-card {
        background: linear-gradient(145deg, rgba(107, 33, 168, 0.12) 0%, rgba(24, 24, 38, 0.75) 40%, rgba(56, 189, 248, 0.06) 100%);
        border: 1px solid rgba(107, 33, 168, 0.25);
        border-radius: 20px;
        padding: 32px;
        backdrop-filter: blur(20px);
        box-shadow: 0 12px 48px rgba(107, 33, 168, 0.15), inset 0 1px 0 rgba(255,255,255,0.04);
        margin-bottom: 20px;
    }
    .np-title {
        font-size: 24px; font-weight: 800; color: #ffffff;
        margin: 0; line-height: 1.2;
        text-shadow: 0 2px 10px rgba(107, 33, 168, 0.3);
    }
    .np-artist {
        font-size: 15px; font-weight: 500; color: #a78bfa;
        margin: 6px 0 0 0;
    }
    .np-idle {
        text-align: center; padding: 40px 20px;
    }
    .np-idle-icon { font-size: 52px; margin-bottom: 12px; }
    .np-idle-text { font-size: 18px; font-weight: 600; color: #52525b; }
    .np-idle-sub { font-size: 13px; color: #3f3f46; margin-top: 6px; }

    /* ===== PILL BADGES ===== */
    .pill {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-size: 11px; font-weight: 700; margin-right: 6px; margin-top: 12px;
        letter-spacing: 0.3px; text-transform: uppercase;
    }
    .pill-violet { background: rgba(107, 33, 168, 0.2); border: 1px solid rgba(168, 85, 247, 0.3); color: #c084fc; }
    .pill-blue { background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.25); color: #38bdf8; }
    .pill-green { background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); color: #10b981; }
    .pill-rose { background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.25); color: #f43f5e; }

    /* ===== PROGRESS BAR ===== */
    .progress-wrap { margin: 20px 0 8px 0; }
    .progress-track {
        width: 100%; height: 5px; background: rgba(255,255,255,0.08);
        border-radius: 10px; overflow: hidden;
    }
    .progress-fill {
        height: 100%; border-radius: 10px;
        background: linear-gradient(90deg, #6b21a8, #a855f7, #38bdf8);
        transition: width 1s linear;
    }
    .progress-time {
        display: flex; justify-content: space-between; margin-top: 6px;
        font-size: 12px; color: #52525b; font-weight: 600; font-variant-numeric: tabular-nums;
    }

    /* ===== BUTTONS ===== */
    div.stButton > button {
        background: rgba(24, 24, 38, 0.8) !important;
        color: #e4e4e7 !important;
        border: 1px solid rgba(107, 33, 168, 0.25) !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        backdrop-filter: blur(8px) !important;
    }
    div.stButton > button:hover {
        background: rgba(107, 33, 168, 0.35) !important;
        border-color: #a855f7 !important;
        color: #fff !important;
        box-shadow: 0 0 20px rgba(107, 33, 168, 0.4) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7, #06b6d4) !important;
        border: 2px solid #38bdf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.8) !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0369a1, #0891b2) !important;
        box-shadow: 0 0 28px rgba(56, 189, 248, 1.0) !important;
    }

    /* ===== QUEUE ITEMS ===== */
    .q-item {
        background: rgba(24, 24, 36, 0.5);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 6px;
        display: flex; align-items: center;
        transition: background 0.2s;
    }
    .q-item:hover { background: rgba(107, 33, 168, 0.1); border-color: rgba(107, 33, 168, 0.2); }
    .q-num { color: #52525b; font-weight: 700; font-size: 13px; min-width: 28px; }
    .q-title { color: #e4e4e7; font-weight: 600; font-size: 14px; }
    .q-meta { color: #71717a; font-size: 12px; }

    /* ===== SECTION TITLES ===== */
    .section-title {
        font-size: 16px; font-weight: 800; color: #a1a1aa;
        text-transform: uppercase; letter-spacing: 1.5px;
        margin-bottom: 16px; padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }

    /* ===== SEARCH BOX ===== */
    .stTextInput > div > div > input {
        background: rgba(24, 24, 38, 0.7) !important;
        border: 1px solid rgba(107, 33, 168, 0.25) !important;
        border-radius: 12px !important;
        color: #e4e4e7 !important;
        font-weight: 500 !important;
        padding: 12px 16px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 2px rgba(107, 33, 168, 0.2) !important;
    }

    /* ===== SLIDER ===== */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: #a855f7 !important;
    }
    .stSlider [data-baseweb="slider"] > div:first-child > div {
        background: linear-gradient(90deg, #6b21a8, #38bdf8) !important;
    }

    /* ===== STATUS INDICATOR ===== */
    .status-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 8px; animation: pulse 2s infinite;
    }
    .status-online { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
    .status-offline { background: #f43f5e; box-shadow: 0 0 8px rgba(244, 63, 94, 0.5); }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def api(endpoint, method="GET", data=None):
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=1.5)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=1.5)
        elif method == "DELETE":
            r = requests.delete(url, timeout=1.5)
        else:
            return None
        return r.json() if r.status_code in [200, 201] else None
    except:
        return None

def fmt(ms):
    if not ms or ms < 0: return "0:00"
    s = int(ms // 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ------------------------------------------------------------------------------
# 3. HEADER
# ------------------------------------------------------------------------------
st.markdown("""
<div class="hero-header">
    <div style="display:flex; align-items:center; justify-content:space-between;">
        <div>
            <div class="hero-title">🌌 KUSHIDA</div>
            <div class="hero-sub">Luxury Discord Music System • Web Remote Control</div>
        </div>
        <div style="text-align:right;">
            <div class="hero-sub">Anyone in the voice channel can control playback</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 4. STATUS BAR & GUILD SELECTION
# ------------------------------------------------------------------------------
status = api("/api/status")
guilds = api("/api/guilds") or []

col_status, col_guild = st.columns([2, 1])

with col_status:
    if status and status.get("status") == "online":
        st.markdown(
            f'<span class="status-dot status-online"></span>'
            f'<span style="color:#10b981;font-weight:700;">SYSTEM ONLINE</span>'
            f'<span style="color:#52525b;"> • {status.get("latency_ms", 0)}ms • {status.get("user", "")}</span>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="status-dot status-offline"></span>'
            '<span style="color:#f43f5e;font-weight:700;">API DISCONNECTED</span>'
            '<span style="color:#52525b;"> • Start main.py to connect</span>',
            unsafe_allow_html=True
        )

with col_guild:
    if guilds:
        guild_map = {f"🎵 {g['name']}": g["id"] for g in guilds}
        sel = st.selectbox("Server", list(guild_map.keys()), label_visibility="collapsed")
        guild_id = guild_map[sel]
    else:
        st.info("No Discord servers found")
        guild_id = None

if not guild_id:
    st.stop()


# Fetch player state
ps = api(f"/api/status/{guild_id}")

# Layout: Main Player | Side Panel
main_col, side_col = st.columns([1.6, 1], gap="large")


# ------------------------------------------------------------------------------
# 5. NOW PLAYING CARD (CENTER STAGE)
# ------------------------------------------------------------------------------
with main_col:
    if ps and ps.get("current_track"):
        track = ps["current_track"]
        pos = ps.get("position_ms", 0)
        dur = track.get("duration_ms", 1)
        pct = min(max(pos / dur if dur > 0 else 0, 0), 1.0)

        st.markdown('<div class="np-card">', unsafe_allow_html=True)

        # Album Art + Track Info
        art_col, info_col = st.columns([1, 2.5])
        with art_col:
            art = track.get("artwork_url")
            if not art and track.get("uri"):
                import re
                yt_m = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", track["uri"])
                if yt_m:
                    art = f"https://img.youtube.com/vi/{yt_m.group(1)}/hqdefault.jpg"
            if art and art.startswith("http"):
                st.image(art, use_container_width=True)
            else:
                st.markdown("""
                <div style="width:100%; aspect-ratio:1; border-radius:14px; background:linear-gradient(135deg, #181824, #0d0d14); display:flex; align-items:center; justify-content:center; border:1px solid rgba(107,33,168,0.3); font-size:48px;">
                    🌌
                </div>
                """, unsafe_allow_html=True)

        with info_col:
            st.markdown(f'<div class="np-title">{track["title"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="np-artist">{track["author"]}</div>', unsafe_allow_html=True)

            # Status Pills
            vol = ps.get("volume", 100)
            loop = ps.get("loop_mode", "normal")
            loop_label = {"normal": "OFF", "track": "TRACK", "queue": "QUEUE"}.get(loop, "OFF")
            paused = ps.get("paused", False)

            pills_html = (
                f'<span class="pill pill-violet">🔊 {vol}%</span>'
                f'<span class="pill pill-blue">🔁 {loop_label}</span>'
                f'<span class="pill pill-green">📑 {ps.get("queue_count", 0)} QUEUED</span>'
            )
            if paused:
                pills_html += '<span class="pill pill-rose">⏸ PAUSED</span>'
            st.markdown(pills_html, unsafe_allow_html=True)

        # Progress Bar
        st.markdown(f"""
        <div class="progress-wrap">
            <div class="progress-track"><div class="progress-fill" style="width:{pct*100:.1f}%"></div></div>
            <div class="progress-time"><span>{fmt(pos)}</span><span>{fmt(dur)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # Idle State
        st.markdown("""
        <div class="np-card">
            <div class="np-idle">
                <div class="np-idle-icon">🌌</div>
                <div class="np-idle-text">No track is playing</div>
                <div class="np-idle-sub">Search a song below or use /play on Discord to start streaming</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # PLAYBACK CONTROLS
    # --------------------------------------------------------------------------
    st.markdown('<div class="section-title">🎛️ Playback Controls</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        if st.button("⏮ Prev", use_container_width=True):
            api(f"/api/control/{guild_id}/previous", "POST")
            st.rerun()
    with c2:
        is_paused = bool(ps and ps.get("paused"))
        play_label = "▶️ Resume" if is_paused else "⏸ Pause"
        play_type = "primary" if is_paused else "secondary"
        if st.button(play_label, type=play_type, use_container_width=True, key="btn_pause_resume"):
            api(f"/api/control/{guild_id}/pause", "POST")
            st.rerun()
    with c3:
        if st.button("⏭ Next", use_container_width=True):
            api(f"/api/control/{guild_id}/skip", "POST")
            st.rerun()
    with c4:
        if st.button("🔀 Shuffle", use_container_width=True):
            api(f"/api/control/{guild_id}/shuffle", "POST")
            st.rerun()
    with c5:
        if st.button("⏹ Stop", use_container_width=True):
            api(f"/api/control/{guild_id}/stop", "POST")
            st.rerun()
    with c6:
        if st.button("🔄 Sync", use_container_width=True):
            st.rerun()

    # Volume Slider
    vol_val = ps.get("volume", 100) if ps else 100
    new_vol = st.slider("🔊 Master Volume", 0, 200, vol_val, 5, label_visibility="visible")
    if new_vol != vol_val:
        api(f"/api/control/{guild_id}/volume", "POST", {"volume": new_vol})

    # --------------------------------------------------------------------------
    # STUDIO AUDIO FILTERS
    # --------------------------------------------------------------------------
    st.markdown('<div class="section-title">🎧 Studio Filter Presets</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    filter_map = {
        "🔊 Bass+": "bassboost",
        "⚡ Nightcore": "nightcore",
        "🎧 8D Spatial": "8d",
        "🌊 Vaporwave": "vaporwave",
        "✨ Reset": "reset"
    }
    active_filter = (ps.get("active_filter") or "reset").lower() if ps else "reset"
    for col, (label, preset) in zip([fc1, fc2, fc3, fc4, fc5], filter_map.items()):
        with col:
            is_active = (preset.lower() == active_filter)
            btn_type = "primary" if is_active else "secondary"
            btn_label = f"✨ {label}" if is_active else label
            if st.button(btn_label, type=btn_type, use_container_width=True, key=f"f_{preset}"):
                api(f"/api/control/{guild_id}/filter", "POST", {"preset": preset})
                st.toast(f"Applied {label}!")
                st.rerun()


# ------------------------------------------------------------------------------
# 6. SIDE PANEL — SEARCH + QUEUE
# ------------------------------------------------------------------------------
with side_col:
    # Search & Push
    st.markdown('<div class="section-title">🔍 Stream to Voice Channel</div>', unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)

    query = st.text_input("Search", placeholder="Song name, artist, or YouTube URL...", label_visibility="collapsed")
    if st.button("🚀 Push to Discord VC", type="primary", use_container_width=True):
        if query.strip():
            res = api(f"/api/control/{guild_id}/play", "POST", {"query": query.strip()})
            if res and res.get("success"):
                st.success(res.get("message", "Queued!"))
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to queue. Is bot connected to a VC?")
        else:
            st.warning("Enter a song name or URL")
    st.markdown('</div>', unsafe_allow_html=True)

    # Quick Vibe Buttons
    st.markdown('<div class="section-title">🌌 Quick Vibes</div>', unsafe_allow_html=True)

    vibes = [
        ("🌊 Lo-Fi Chill", "lo-fi beats chill study"),
        ("⚡ Phonk Drift", "phonk drift music playlist"),
        ("🌃 Late Night Synth", "synthwave retrowave night drive"),
        ("💪 Gym Hype", "workout motivation hype music"),
        ("🎮 Gaming Mode", "gaming music epic orchestral"),
        ("☕ Coffee Jazz", "jazz cafe acoustic warm"),
    ]
    vc1, vc2 = st.columns(2)
    for i, (lbl, q) in enumerate(vibes):
        with vc1 if i % 2 == 0 else vc2:
            if st.button(lbl, use_container_width=True, key=f"vibe_{i}"):
                api(f"/api/control/{guild_id}/play", "POST", {"query": q})
                st.toast(f"Queued {lbl}!")
                st.rerun()

    # Queue Manager
    st.markdown('<div class="section-title">📑 Up Next</div>', unsafe_allow_html=True)

    queue_data = api(f"/api/queue/{guild_id}")
    if queue_data and queue_data.get("tracks"):
        tracks = queue_data["tracks"]
        for t in tracks[:8]:
            idx = t["index"]
            title = t["title"][:32] + "..." if len(t["title"]) > 32 else t["title"]
            dur = fmt(t.get("duration_ms", 0))

            st.markdown(f"""
            <div class="q-item">
                <span class="q-num">{idx + 1:02d}</span>
                <div style="flex:1; margin-left:12px;">
                    <div class="q-title">{title}</div>
                    <div class="q-meta">{t['author']} • {dur}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            qc1, qc2 = st.columns(2)
            with qc1:
                if idx > 0 and st.button("▲ Move Up", key=f"up_{idx}", use_container_width=True):
                    api(f"/api/control/{guild_id}/reorder", "POST", {"from_index": idx, "to_index": idx - 1})
                    st.rerun()
            with qc2:
                if st.button("✕ Remove", key=f"del_{idx}", use_container_width=True):
                    api(f"/api/control/{guild_id}/queue/{idx}", "DELETE")
                    st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center; padding:24px; color:#3f3f46;">
            <div style="font-size:28px; margin-bottom:8px;">📑</div>
            <div style="font-size:13px; font-weight:600;">Queue is empty</div>
            <div style="font-size:12px; color:#27272a;">Search above or use /play on Discord</div>
        </div>
        """, unsafe_allow_html=True)


# Auto-refresh toggle (bottom)
st.markdown("---")
col_ref, col_info = st.columns([1, 2])
with col_ref:
    live = st.checkbox("🔄 Auto Refresh", value=False)
    if live:
        time.sleep(2)
        st.rerun()
with col_info:
    st.caption("Anyone in the Discord voice channel can use this web remote • Powered by Kushida v2.0")
