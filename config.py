"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
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
# BOT & APPLICATION IDENTITY
# ------------------------------------------------------------------------------
BOT_NAME: str = "Demon Music"
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_PREFIX: str = os.getenv("BOT_PREFIX", "-")
BOT_STATUS: str = os.getenv("BOT_STATUS", "/play | /help")

# ------------------------------------------------------------------------------
# LAVALINK / WAVELINK CONFIGURATION
# ------------------------------------------------------------------------------
LAVALINK_HOST: str = os.getenv("LAVALINK_HOST", "lava-v4.millohost.my.id")
LAVALINK_PORT: int = int(os.getenv("LAVALINK_PORT", "443"))
LAVALINK_PASSWORD: str = os.getenv("LAVALINK_PASSWORD", "https://discord.gg/mjS5J2K3ep")
LAVALINK_SECURE: bool = os.getenv("LAVALINK_SECURE", "true").lower() == "true"
LAVALINK_IDENTIFIER: str = os.getenv("LAVALINK_IDENTIFIER", "DemonMusic-Millohost")

LAVALINK_URI: str = f"{'https' if LAVALINK_SECURE else 'http'}://{LAVALINK_HOST}:{LAVALINK_PORT}"

# ------------------------------------------------------------------------------
# FASTAPI & RENDER PORT BINDING
# ------------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
# Render sets the PORT env variable automatically
API_PORT: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
API_BASE_URL: str = os.getenv("API_BASE_URL", f"http://127.0.0.1:{API_PORT}")
DASHBOARD_PORT: int = API_PORT
DASHBOARD_URL: str = os.getenv("DASHBOARD_URL", API_BASE_URL)

# ------------------------------------------------------------------------------
# DATABASE & STORAGE
# ------------------------------------------------------------------------------
DB_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "kushida.db"))

# ------------------------------------------------------------------------------
# TOP.GG VOTE WEBHOOK SETTINGS
# ------------------------------------------------------------------------------
TOPGG_AUTH: str = os.getenv("TOPGG_AUTH", "demon-music-auth-secret")

# ------------------------------------------------------------------------------
# SPOTIFY API (OAUTH & RESOLUTION)
# ------------------------------------------------------------------------------
SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI: str = os.getenv(
    "SPOTIFY_REDIRECT_URI", f"{API_BASE_URL}/api/spotify/callback"
)
SPOTIFY_SCOPE: str = "user-library-modify user-library-read user-read-private"

# ------------------------------------------------------------------------------
# LUXURY DESIGN LANGUAGE TOKENS & ACCENTS
# Matching Demon Music Terminal (Dark Luxury Purple/Red/Pink)
# ------------------------------------------------------------------------------
HEX_DEMON_BG = 0x0E0B16          # Deep Obsidian
HEX_DEMON_PURPLE = 0x9333EA      # Electric Purple
HEX_DEMON_RED = 0xEF4444         # Crimson Glow
HEX_DEMON_ACCENT = 0xA855F7      # Neon Lilac
HEX_EMERALD = 0x10B981          # Connected Emerald
HEX_MUTED = 0x64748B            # Muted Slate

HEX_DEEP_SPACE = 0x0D0D12
HEX_VIOLET = 0x9333EA
HEX_ICE_BLUE = 0x38BDF8
HEX_ROSE = 0xEF4444
HEX_GOLD = 0xF59E0B

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
PB_HEAD = "🔘"
PB_EMPTY = "─"
PB_LENGTH = 14
