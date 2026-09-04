"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: config.py (Centralized Configuration & Theme Constants)
================================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------------------------
# DISCORD BOT SETTINGS
# ------------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_PREFIX: str = os.getenv("BOT_PREFIX", "-")
BOT_STATUS: str = os.getenv("BOT_STATUS", "-help | /help")

# ------------------------------------------------------------------------------
# LAVALINK / WAVELINK CONFIGURATION
# ------------------------------------------------------------------------------
LAVALINK_HOST: str = os.getenv("LAVALINK_HOST", "lava-v4.millohost.my.id")
LAVALINK_PORT: int = int(os.getenv("LAVALINK_PORT", "443"))
LAVALINK_PASSWORD: str = os.getenv("LAVALINK_PASSWORD", "https://discord.gg/mjS5J2K3ep")
LAVALINK_SECURE: bool = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
LAVALINK_IDENTIFIER: str = os.getenv("LAVALINK_IDENTIFIER", "Kushida-Millohost-01")

# Node URI constructed cleanly
LAVALINK_URI: str = f"{'https' if LAVALINK_SECURE else 'http'}://{LAVALINK_HOST}:{LAVALINK_PORT}"

# ------------------------------------------------------------------------------
# FASTAPI & WEB DASHBOARD SETTINGS
# ------------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8501"))
DASHBOARD_URL: str = os.getenv("DASHBOARD_URL", f"http://127.0.0.1:{DASHBOARD_PORT}")
API_BASE_URL: str = os.getenv("API_BASE_URL", f"http://127.0.0.1:{API_PORT}")

# ------------------------------------------------------------------------------
# DATABASE SETTINGS
# ------------------------------------------------------------------------------
DB_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "kushida.db"))

# ------------------------------------------------------------------------------
# AI ENGINE (GEMINI / OPENAI)
# ------------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

# ------------------------------------------------------------------------------
# SPOTIFY API (OAUTH & LIKED SONGS)
# ------------------------------------------------------------------------------
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI: str = os.getenv(
    "SPOTIFY_REDIRECT_URI", f"{API_BASE_URL}/api/spotify/callback"
)
SPOTIFY_SCOPE: str = "user-library-modify user-library-read user-read-private"

# ------------------------------------------------------------------------------
# LUXURY DESIGN LANGUAGE TOKENS & ACCENTS
# Strict: Premium dark aesthetics, Deep space black, Neon accents
# ------------------------------------------------------------------------------
HEX_DEEP_SPACE = 0x0D0D12       # Deep Space Black
HEX_VIOLET = 0x6B21A8           # Elegant Neon Violet
HEX_ICE_BLUE = 0x38BDF8         # Ethereal Ice Blue
HEX_EMERALD = 0x10B981          # Neon Emerald
HEX_ROSE = 0xF43F5E             # Neon Rose / High Energy
HEX_GOLD = 0xF59E0B             # Warm Amber / Ethereal Gold
HEX_MUTED = 0x27272A            # Muted Charcoal

# Visual UI Icons & Emojis
ICON_DISC = "💿"
ICON_PLAY = "▶️"
ICON_PAUSE = "⏸️"
ICON_NEXT = "⏭️"
ICON_PREV = "⏮️"
ICON_STOP = "⏹️"
ICON_SHUFFLE = "🔀"
ICON_REPEAT = "🔁"
ICON_REPEAT_ONE = "🔂"
ICON_VOLUME_UP = "🔊"
ICON_VOLUME_DOWN = "🔉"
ICON_MUTE = "🔇"
ICON_SPOTIFY = "💚"
ICON_AI = "✨"
ICON_VIBE = "🌌"
ICON_TIMER = "💤"
ICON_FIRE = "🔥"
ICON_WAVE = "🌊"
ICON_DASHBOARD = "🌐"

# Custom Progress Bar Characters
PB_FILL = "━"
PB_HEAD = "●"
PB_EMPTY = "━"
PB_LENGTH = 16
