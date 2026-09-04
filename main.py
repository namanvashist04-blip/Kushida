"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: main.py (Bot Core, Cog Loading, Wavelink NodePool & FastAPI Background Server)
================================================================================
"""

import asyncio
import logging
import os
import sys
import threading
import uvicorn
import discord
from discord.ext import commands

import wavelink

from config import (
    BOT_TOKEN,
    BOT_STATUS,
    LAVALINK_URI,
    LAVALINK_PASSWORD,
    LAVALINK_IDENTIFIER,
    API_HOST,
    API_PORT,
    DASHBOARD_PORT,
    DASHBOARD_URL,
    API_BASE_URL,
)
from database import db_manager
from utils.luxury_ui import MusicControlView
from api.server import app as fastapi_app, set_bot_instance

# ------------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("kushida.core")

# ------------------------------------------------------------------------------
# DISCORD BOT INITIALIZATION
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
# Note: Slash commands and UI views do not require message_content privileged intent!

bot = discord.Bot(
    intents=intents,
    activity=discord.Activity(
        type=discord.ActivityType.listening,
        name=BOT_STATUS
    )
)

# Inject bot instance into FastAPI context
set_bot_instance(bot)


# ------------------------------------------------------------------------------
# BOT LIFECYCLE & WAVELINK 3.x SETUP
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    """Triggered when the bot is connected to Discord Gateway."""
    ascii_banner = r"""
  _  ___   _ ____  _   _ ___ ____    _    
 | |/ / | | / ___|| | | |_ _|  _ \  / \   
 | ' /| | | \___ \| |_| || || | | |/ _ \  
 | . \| |_| |___) |  _  || || |_| / ___ \ 
 |_|\_\\___/|____/|_| |_|___|____/_/   \_\
        -- LUXURY DISCORD AUDIO & REMOTE --
    """
    print(ascii_banner)
    logger.info(f"✨ Logged in as: {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} Discord guilds.")

    # 1. Initialize SQLite Database Schema
    try:
        await db_manager.init_db()
        logger.info("Database schema initialized and ready.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}")

    # 2. Register Persistent Discord UI Views
    try:
        bot.add_view(MusicControlView())
        logger.info("Persistent Music Control UI Views registered.")
    except Exception as e:
        logger.error(f"Failed to register persistent views: {e}")

    # 3. Connect to Wavelink 3.x Node Pool
    try:
        nodes = [
            wavelink.Node(
                uri=LAVALINK_URI,
                password=LAVALINK_PASSWORD,
                identifier=LAVALINK_IDENTIFIER,
                inactive_player_timeout=300
            )
        ]
        await wavelink.Pool.connect(nodes=nodes, client=bot)
        logger.info(f"Wavelink Pool connecting to Lavalink node: {LAVALINK_URI}")
    except Exception as e:
        logger.error(f"Failed to connect to Lavalink node at {LAVALINK_URI}: {e}")
        logger.warning("Playback commands will retry upon execution.")

    logger.info(f"🌐 Web Remote Dashboard: {DASHBOARD_URL}")
    logger.info(f"⚡ FastAPI Backend API: {API_BASE_URL}/docs")


# ------------------------------------------------------------------------------
# GLOBAL SLASH COMMAND ERROR HANDLER
# ------------------------------------------------------------------------------
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: Exception):
    """Graceful error catching for all slash commands."""
    logger.error(f"Slash Command Error in /{ctx.command.name}: {error}", exc_info=True)

    try:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(f"⏳ Please wait {error.retry_after:.1f}s before using this command again.", ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.respond("❌ You do not have permission to use this command.", ephemeral=True)
        elif isinstance(error, wavelink.WavelinkException):
            await ctx.respond(f"⚠️ Audio Engine Error: `{str(error)}`", ephemeral=True)
        else:
            msg = f"❌ An unexpected error occurred: `{str(error)}`"
            if ctx.response.is_done():
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.respond(msg, ephemeral=True)
    except Exception:
        pass


# ------------------------------------------------------------------------------
# EXTENSION (COG) LOADER
# ------------------------------------------------------------------------------
def load_all_cogs():
    """Load core modular cogs."""
    extensions = [
        "cogs.audio",
        "cogs.ai_engine"
    ]
    for ext in extensions:
        try:
            bot.load_extension(ext)
            logger.info(f"Loaded Cog Extension: {ext}")
        except Exception as e:
            logger.error(f"Failed to load extension {ext}: {e}", exc_info=True)


# ------------------------------------------------------------------------------
# FASTAPI BACKGROUND SERVER LAUNCHER
# ------------------------------------------------------------------------------
def run_fastapi_server():
    """Runs FastAPI in a dedicated background daemon thread with Uvicorn."""
    logger.info(f"Starting FastAPI background server on {API_HOST}:{API_PORT}...")
    uvicorn.run(
        fastapi_app,
        host=API_HOST,
        port=API_PORT,
        log_level="warning",
        access_log=False
    )


def start_background_api():
    """Spawns FastAPI background thread."""
    api_thread = threading.Thread(target=run_fastapi_server, daemon=True, name="FastAPI-Server-Thread")
    api_thread.start()
    logger.info("FastAPI background thread spawned successfully.")


# ------------------------------------------------------------------------------
# MAIN EXECUTION ENTRY POINT
# ------------------------------------------------------------------------------
def main():
    """Application Bootstrapper."""
    if not BOT_TOKEN:
        logger.critical(
            "FATAL: BOT_TOKEN is missing in `.env` file! Please configure your token before running."
        )
        sys.exit(1)

    # 1. Start FastAPI server thread
    start_background_api()

    # 2. Load all Cogs
    load_all_cogs()

    # 3. Start Discord Bot Gateway Loop
    try:
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("FATAL: Invalid Discord Bot Token supplied in `.env`.")
    except Exception as e:
        logger.critical(f"FATAL: Discord Bot crashed with exception: {e}", exc_info=True)


if __name__ == "__main__":
    main()
