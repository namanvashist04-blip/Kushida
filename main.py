"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: main.py (Bot Core, 67 Slash Commands Cogs, Wavelink NodePool & FastAPI Background Server)
================================================================================
"""

import asyncio
import logging
import os
import sys
import threading
from typing import Dict, Any, Optional

import uvicorn

# Guarantee py-cord presence in cloud environments
try:
    import discord
    if not hasattr(discord, "Bot") or not hasattr(discord, "commands"):
        import subprocess
        print("[DEMON BOOT] Restoring py-cord library...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "discord.py"], capture_output=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "py-cord"], capture_output=True)
        import importlib
        importlib.reload(discord)
except Exception:
    pass

import discord
from discord.ext import commands
import wavelink

from config import (
    BOT_NAME,
    BOT_TOKEN,
    BOT_STATUS,
    LAVALINK_URI,
    LAVALINK_PASSWORD,
    LAVALINK_IDENTIFIER,
    API_HOST,
    API_PORT,
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
logger = logging.getLogger("demon.core")

# ------------------------------------------------------------------------------
# DISCORD BOT INITIALIZATION (Slash Commands Exclusively)
# ------------------------------------------------------------------------------
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(
    intents=intents,
    help_command=None,
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
    """Triggered when the bot connects to Discord Gateway."""
    banner = r"""
  ____  _____ __  __  ___  _   _   __  __ _   _ ____ ___ ____ 
 |  _ \| ____|  \/  |/ _ \| \ | | |  \/  | | | / ___|_ _/ ___|
 | | | |  _| | |\/| | | | |  \| | | |\/| | | | \___ \| | |    
 | |_| | |___| |  | | |_| | |\  | | |  | | |_| |___) | | |___ 
 |____/|_____|_|  |_|\___/|_| \_| |_|  |_|\___/|____/___\____|
         -- DEMON MUSIC TERMINAL 24/7 AUDIO CLOUD --
    """
    print(banner)
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
                inactive_player_timeout=None
            )
        ]
        await wavelink.Pool.connect(nodes=nodes, client=bot)
        logger.info(f"Wavelink Pool connecting to Lavalink node: {LAVALINK_URI}")

        # 4. Auto-reconnect 24/7 Guilds to their Voice Channels
        async def _reconnect_247():
            await asyncio.sleep(3)
            for guild in bot.guilds:
                try:
                    is_247 = await db_manager.get_guild_247(guild.id)
                    if is_247:
                        vc_id = await db_manager.get_guild_247_channel(guild.id)
                        vc = guild.get_channel(vc_id) if vc_id else None
                        if not vc and guild.voice_channels:
                            vc = guild.voice_channels[0]
                        if vc:
                            player = getattr(guild, "voice_client", None)
                            if not player or not player.connected:
                                await vc.connect(cls=wavelink.Player)
                                logger.info(f"⏰ 24/7 Mode: Auto-reconnected to '{vc.name}' in '{guild.name}'")
                except Exception as e:
                    logger.error(f"Error restoring 24/7 VC for guild {guild.id}: {e}")

        asyncio.create_task(_reconnect_247())

    except Exception as e:
        logger.error(f"Failed to connect to Lavalink node at {LAVALINK_URI}: {e}")
        logger.warning("Playback commands will retry upon execution.")

    logger.info("⚡ Demon Music 24/7 Core Engine is Active")


# ------------------------------------------------------------------------------
# GLOBAL SLASH COMMAND ERROR HANDLER
# ------------------------------------------------------------------------------
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: Exception):
    """Graceful error catching for all slash commands."""
    logger.error(f"Slash Command Error in /{ctx.command.name}: {error}", exc_info=True)

    try:
        if isinstance(error, commands.CommandOnCooldown):
            msg = f"⏳ Please wait {error.retry_after:.1f}s before using this command again."
        elif isinstance(error, commands.MissingPermissions):
            msg = "❌ You do not have permission to use this command."
        elif isinstance(error, wavelink.WavelinkException):
            msg = f"⚠️ Audio Engine Error: `{str(error)[:100]}`"
        else:
            msg = f"❌ An error occurred: `{str(error)[:100]}`"

        if ctx.response.is_done():
            await ctx.followup.send(msg)
        else:
            await ctx.respond(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Could not send error response to interaction: {e}")


# ------------------------------------------------------------------------------
# EXTENSION (COG) LOADER — ALL 67 COMMANDS IN 5 COGS
# ------------------------------------------------------------------------------
def load_all_cogs():
    """Load all 5 cogs containing the complete 67 slash commands."""
    extensions = [
        "cogs.music",      # 21 Music Commands
        "cogs.filters",    # 15 Audio DSP Filters
        "cogs.playlists",  # 12 Custom Playlists
        "cogs.settings",   # 6 Server & DJ Settings
        "cogs.info"        # 13 Info & Utilities
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
    logger.info(f"Starting Demon Music Terminal Web Server on {API_HOST}:{API_PORT}...")
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
        logger.critical("FATAL: BOT_TOKEN is missing in `.env` file! Please configure your token.")
        sys.exit(1)

    # 1. Start FastAPI server thread (Terminal Web UI + REST + WebSocket)
    start_background_api()

    # 2. Load all 5 Cogs (67 Slash Commands)
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
