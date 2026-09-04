# 🌌 Kushida — Luxury Discord Music System & Web Remote Dashboard

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Pycord](https://img.shields.io/badge/Pycord-v2.6-5865F2?style=for-the-badge&logo=discord)
![Lavalink](https://img.shields.io/badge/Lavalink-v4-red?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?style=for-the-badge&logo=streamlit)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-AI-8E75C2?style=for-the-badge&logo=google)

**Kushida** is an elite, production-ready Discord music system and real-time web control terminal built with a minimalist, luxury dark aesthetic. Engineered with **Pycord**, **Wavelink 3.x (Lavalink v4)**, **aiosqlite**, **FastAPI**, **Streamlit**, **Google Gemini AI**, and **Spotify OAuth**.

---

## ✨ Features

- 💎 **Luxury Persistent Music Panel**: Zero channel spam. Single persistent embed with dynamic vibe colors, pill badges, and animated-style progress bar (`01:24 ━━━●━━━━━━━━━━━━ 03:45`).
- 🎛️ **Full Voice Channel Control**: Interactive buttons for Play/Pause, Next, Prev, Volume, Shuffle, Looping, Stop, and Sleep Timer. Any member in the VC can use controls (no DJ lockouts).
- 🧠 **AI Contextual & Lyric Search (`/find`)**: Search songs by obscure lyrics (*"I tried so hard and got so far"*) or abstract contexts (*"the sad song from Naruto"*). Powered by Google Gemini.
- 🌌 **AI Mood & Scenario Queues (`/random`, `/vibe`)**: Instant 5-track queues for Phonk, Lo-Fi, Synthwave, Deep Coding, Gym, or Late Night Drive.
- 🔮 **Social VibeMatch (`/vibematch`)**: Analyzes server listening history via SQLite to calculate musical compatibility and match the top two resonant users.
- 💚 **Real-World Spotify Sync**: Click "Save to Spotify" on Discord to automatically save the currently playing track to your personal Spotify *Liked Songs* via OAuth.
- 💤 **30s Smooth Fadeout Sleep Timer (`/sleep`)**: Gently ramps down volume over 30 seconds before disconnecting.
- 🎛️ **Studio Audio Filters (`/filter`)**: Native hardware DSP filters: `bassboost`, `nightcore`, `8d` spatial audio, and `vaporwave`.
- 🌐 **Web Remote Control Dashboard**: High-tech Streamlit web remote syncing in real-time. Features remote search, visual queue manager (reorder/delete), volume sliders, and filter triggers.

---

## 📁 Architecture Overview

```
Kushida/
├── main.py                  # Bot entry point, Cog loader & FastAPI background thread
├── config.py                # Environment configuration & luxury color tokens
├── database.py              # Async SQLite database manager (aiosqlite)
├── cogs/
│   ├── audio.py             # Wavelink 3.x audio engine, playback & Spotify sync
│   └── ai_engine.py         # Google Gemini contextual search, mood queues & VibeMatch
├── utils/
│   └── luxury_ui.py         # Discord persistent views, embeds, dynamic color logic
├── api/
│   └── server.py            # FastAPI REST & WebSocket endpoints
├── dashboard/
│   └── app.py               # Streamlit Luxury Web Remote Control Terminal
├── docker-compose.yml       # One-click Lavalink v4 audio server
├── application.yml          # Lavalink v4 engine configuration
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

---

## 🚀 Quick Setup Guide

### 1. Prerequisites
- **Python 3.10+**
- **Docker** (or Java 17+ if running Lavalink manually)
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/)) — *Free*
- Spotify Client ID & Secret ([Spotify Developer Dashboard](https://developer.spotify.com/dashboard)) — *Free*

### 2. Installation

Clone and install dependencies:
```bash
git clone https://github.com/your-username/Kushida.git
cd Kushida
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 4. Start Lavalink Audio Server
Using Docker (Recommended):
```bash
docker compose up -d
```

*(Or download `Lavalink.jar` and run `java -jar Lavalink.jar`)*

### 5. Launch Kushida Bot & API
```bash
python main.py
```

### 6. Launch Web Remote Dashboard
In a separate terminal:
```bash
streamlit run dashboard/app.py
```
Open **`http://localhost:8501`** in your browser to access the Web Control Panel.

---

## 🕹️ Discord Slash Commands

| Command | Description |
| :--- | :--- |
| `/play <query>` | Stream a song, playlist, or URL in studio quality |
| `/pause` | Toggle pause / resume |
| `/skip` | Skip the current track |
| `/previous` | Replay previous track from history |
| `/stop` | Stop playback, clear queue, and disconnect |
| `/queue [page]` | View the upcoming paginated queue |
| `/volume <0-200>` | Adjust master playback volume |
| `/seek <seconds>` | Jump to specific timestamp |
| `/filter <preset>` | Apply studio filter: `bassboost`, `nightcore`, `8d`, `vaporwave`, `reset` |
| `/sleep <minutes>` | Set sleep timer with 30s gentle volume fadeout |
| `/nowplaying` | Display the interactive luxury control panel |
| `/find <query>` | Contextual & lyric AI search (Gemini) |
| `/random <mood>` | Curate 5-track queue for a mood (Chill, Phonk, Synthwave, etc.) |
| `/vibe <scenario>` | Curate 5-track queue for an activity (Gym, Coding, Night Drive) |
| `/vibematch` | Social server compatibility analytics |

---

## 🌐 24/7 Production Deployment

To run Kushida 24/7 on a Linux VPS / Cloud server (Ubuntu/Debian):

### Using PM2 Process Manager:
```bash
# Install PM2
npm install -g pm2

# Start Bot + API
pm2 start main.py --name "kushida-bot" --interpreter python3

# Start Web Dashboard
pm2 start "streamlit run dashboard/app.py --server.port 8501 --server.headless true" --name "kushida-dashboard"

# Save process list for auto-boot
pm2 save
pm2 startup
```

---

## 🛡️ License
Distributed under the **MIT License**. Built with elegance for modern music communities.
