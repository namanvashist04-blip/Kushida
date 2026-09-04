"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: api/server.py (FastAPI Backend, WebSockets & Spotify OAuth)
================================================================================
"""

import asyncio
import logging
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

import discord
import wavelink

from config import (
    API_HOST,
    API_PORT,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    SPOTIFY_SCOPE,
    HEX_DEEP_SPACE,
    HEX_VIOLET,
    HEX_ICE_BLUE,
)
from database import db_manager

logger = logging.getLogger("kushida.api")

# FastAPI App Instance
app = FastAPI(
    title="Kushida Luxury Music API",
    description="High-performance REST API and WebSocket gateway for Discord Bot Remote Control.",
    version="2.0.0"
)

# CORS Configuration (Permissive for Local Web Remote & Dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bot reference injected by main.py
bot_instance: Optional[discord.Bot] = None


def set_bot_instance(bot: discord.Bot) -> None:
    """Inject the running Discord bot instance into the API context."""
    global bot_instance
    bot_instance = bot


# ------------------------------------------------------------------------------
# PYDANTIC REQUEST & RESPONSE SCHEMAS
# ------------------------------------------------------------------------------
class PlayRequest(BaseModel):
    query: str = Field(..., description="Song name, YouTube URL, or Spotify link")
    voice_channel_id: Optional[int] = Field(None, description="Target Voice Channel ID (optional if bot already in VC)")

class VolumeRequest(BaseModel):
    volume: int = Field(..., ge=0, le=200, description="Volume percentage 0 - 200")

class SeekRequest(BaseModel):
    position_ms: int = Field(..., ge=0, description="Seek target in milliseconds")

class FilterRequest(BaseModel):
    preset: str = Field(..., description="Filter name: bassboost, nightcore, 8d, vaporwave, reset")

class ReorderRequest(BaseModel):
    from_index: int = Field(..., ge=0)
    to_index: int = Field(..., ge=0)


# ------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------
def _get_player_or_404(guild_id: int) -> wavelink.Player:
    """Retrieve player for a given guild ID or raise 404."""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Discord bot is still initializing.")

    guild = bot_instance.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail=f"Guild {guild_id} not found.")

    player = getattr(guild, "voice_client", None)
    if not player or not isinstance(player, wavelink.Player):
        raise HTTPException(status_code=404, detail=f"No active music player in guild {guild_id}.")

    return player


# ------------------------------------------------------------------------------
# 1. BOT & GUILD STATUS ROUTES
# ------------------------------------------------------------------------------
@app.get("/api/status")
async def get_general_status():
    """Returns general bot health, latency, uptime, and guild counts."""
    if not bot_instance:
        return {"status": "starting", "bot_ready": False}

    active_players = sum(
        1 for g in bot_instance.guilds
        if g.voice_client and isinstance(g.voice_client, wavelink.Player) and g.voice_client.playing
    )

    return {
        "status": "online",
        "bot_ready": bot_instance.is_ready(),
        "latency_ms": round(bot_instance.latency * 1000, 2),
        "guild_count": len(bot_instance.guilds),
        "active_players": active_players,
        "user": str(bot_instance.user) if bot_instance.user else "Kushida#0000"
    }


@app.get("/api/guilds")
async def list_bot_guilds():
    """List all Discord servers the bot is in, along with their active VC status."""
    if not bot_instance:
        return []

    result = []
    for g in bot_instance.guilds:
        player = g.voice_client
        is_playing = False
        track_title = None

        if player and isinstance(player, wavelink.Player) and player.current:
            is_playing = player.playing
            track_title = player.current.title

        result.append({
            "id": g.id,
            "name": g.name,
            "icon_url": g.icon.url if g.icon else None,
            "member_count": g.member_count,
            "has_player": player is not None,
            "is_playing": is_playing,
            "current_track": track_title
        })
    return result


@app.get("/api/status/{guild_id}")
async def get_guild_player_status(guild_id: int):
    """Get detailed live player information for a specific guild."""
    player = _get_player_or_404(guild_id)

    track_data = None
    if player.current:
        track = player.current
        track_data = {
            "title": track.title,
            "author": getattr(track, "author", "Unknown"),
            "duration_ms": getattr(track, "length", 0),
            "position_ms": player.position,
            "artwork_url": getattr(track, "artwork_url", None),
            "uri": getattr(track, "uri", None),
        }

    queue_mode_name = "normal"
    if hasattr(player.queue, "mode"):
        if player.queue.mode == wavelink.QueueMode.loop:
            queue_mode_name = "track"
        elif player.queue.mode == wavelink.QueueMode.loop_all:
            queue_mode_name = "queue"

    return {
        "guild_id": guild_id,
        "connected": player.connected,
        "playing": player.playing,
        "paused": player.paused,
        "volume": player.volume,
        "position_ms": player.position,
        "loop_mode": queue_mode_name,
        "queue_count": len(player.queue),
        "current_track": track_data
    }


@app.get("/api/queue/{guild_id}")
async def get_guild_queue(guild_id: int):
    """Retrieve full queued tracks for a guild."""
    player = _get_player_or_404(guild_id)

    tracks = []
    for idx, t in enumerate(player.queue):
        tracks.append({
            "index": idx,
            "title": t.title,
            "author": getattr(t, "author", "Unknown"),
            "duration_ms": getattr(t, "length", 0),
            "artwork_url": getattr(t, "artwork_url", None),
            "uri": getattr(t, "uri", None),
        })

    return {
        "guild_id": guild_id,
        "total_tracks": len(tracks),
        "tracks": tracks
    }


# ------------------------------------------------------------------------------
# 2. REMOTE PLAYBACK CONTROL ROUTES
# ------------------------------------------------------------------------------
@app.post("/api/control/{guild_id}/play")
async def remote_play(guild_id: int, payload: PlayRequest):
    """Queue and play a track remotely from the Web Dashboard."""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    guild = bot_instance.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")

    player: Optional[wavelink.Player] = getattr(guild, "voice_client", None)

    # If no player, connect to voice channel
    if not player or not player.connected:
        vc = None
        if payload.voice_channel_id:
            vc = guild.get_channel(payload.voice_channel_id)

        # If not specified, pick first voice channel with members
        if not vc:
            for c in guild.voice_channels:
                if len(c.members) > 0:
                    vc = c
                    break

        if not vc and guild.voice_channels:
            vc = guild.voice_channels[0]

        if not vc:
            raise HTTPException(status_code=400, detail="No suitable voice channel found to connect.")

        player = await vc.connect(cls=wavelink.Player)

    # Search and queue track
    search_results = await wavelink.Playable.search(payload.query)
    if not search_results:
        raise HTTPException(status_code=404, detail="No tracks found for query.")

    if isinstance(search_results, wavelink.Playlist):
        added = await player.queue.put_wait(search_results)
        msg = f"Added playlist '{search_results.name}' ({added} tracks) to queue."
    else:
        track = search_results[0]
        await player.queue.put_wait(track)
        msg = f"Added '{track.title}' to queue."

    if not player.playing:
        next_track = player.queue.get()
        await player.play(next_track)

    return {"success": True, "message": msg}


@app.post("/api/control/{guild_id}/pause")
async def remote_pause_toggle(guild_id: int):
    """Toggle pause state."""
    player = _get_player_or_404(guild_id)
    new_state = not player.paused
    await player.pause(new_state)
    return {"success": True, "paused": new_state}


@app.post("/api/control/{guild_id}/skip")
async def remote_skip(guild_id: int):
    """Skip to next track."""
    player = _get_player_or_404(guild_id)
    await player.skip()
    return {"success": True, "message": "Skipped track."}


@app.post("/api/control/{guild_id}/previous")
async def remote_previous(guild_id: int):
    """Play previous track from history."""
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    audio_cog = bot_instance.get_cog("Audio")
    if not audio_cog:
        raise HTTPException(status_code=500, detail="Audio engine unavailable")

    success = await audio_cog.play_previous_track(guild_id)
    if not success:
        raise HTTPException(status_code=400, detail="No previous track found in history")

    return {"success": True, "message": "Replaying previous track."}


@app.post("/api/control/{guild_id}/volume")
async def remote_set_volume(guild_id: int, payload: VolumeRequest):
    """Set volume level (0-200%)."""
    player = _get_player_or_404(guild_id)
    await player.set_volume(payload.volume)
    return {"success": True, "volume": payload.volume}


@app.post("/api/control/{guild_id}/seek")
async def remote_seek(guild_id: int, payload: SeekRequest):
    """Seek to specific millisecond timestamp."""
    player = _get_player_or_404(guild_id)
    if not player.current:
        raise HTTPException(status_code=400, detail="No track playing to seek.")
    await player.seek(payload.position_ms)
    return {"success": True, "position_ms": payload.position_ms}


@app.post("/api/control/{guild_id}/shuffle")
async def remote_shuffle(guild_id: int):
    """Shuffle the upcoming queue."""
    player = _get_player_or_404(guild_id)
    if len(player.queue) < 2:
        raise HTTPException(status_code=400, detail="Not enough tracks to shuffle.")
    player.queue.shuffle()
    return {"success": True, "message": "Queue shuffled."}


@app.post("/api/control/{guild_id}/filter")
async def remote_set_filter(guild_id: int, payload: FilterRequest):
    """Apply audio filter preset."""
    player = _get_player_or_404(guild_id)
    filters: wavelink.Filters = player.filters
    preset = payload.preset.lower()

    if preset == "bassboost":
        filters.reset()
        bass_bands = [(0, 0.30), (1, 0.25), (2, 0.20), (3, 0.15), (4, 0.10)]
        filters.equalizer.set(bands=bass_bands)
    elif preset == "nightcore":
        filters.reset()
        filters.timescale.set(pitch=1.25, speed=1.25, rate=1.0)
    elif preset == "8d":
        filters.reset()
        filters.rotation.set(rotation_hz=0.2)
    elif preset == "vaporwave":
        filters.reset()
        filters.timescale.set(pitch=0.8, speed=0.85, rate=1.0)
    elif preset == "reset":
        filters.reset()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown filter: {preset}")

    await player.set_filters(filters)
    return {"success": True, "applied_filter": preset}


@app.post("/api/control/{guild_id}/reorder")
async def remote_reorder_queue(guild_id: int, payload: ReorderRequest):
    """Swap or move a track position in the queue."""
    player = _get_player_or_404(guild_id)
    q_len = len(player.queue)
    if payload.from_index >= q_len or payload.to_index >= q_len:
        raise HTTPException(status_code=400, detail="Index out of bounds")

    player.queue.swap(payload.from_index, payload.to_index)
    return {"success": True, "message": f"Swapped positions {payload.from_index} and {payload.to_index}"}


@app.delete("/api/control/{guild_id}/queue/{index}")
async def remote_delete_queue_item(guild_id: int, index: int):
    """Remove a track at a specific index from the queue."""
    player = _get_player_or_404(guild_id)
    if index < 0 or index >= len(player.queue):
        raise HTTPException(status_code=400, detail="Invalid queue index")

    player.queue.delete(index)
    return {"success": True, "message": f"Removed track at index {index}"}


# ------------------------------------------------------------------------------
# 3. REAL-TIME WEBSOCKET ROUTE (1-Second Synchronized Heartbeat)
# ------------------------------------------------------------------------------
@app.websocket("/ws/{guild_id}")
async def websocket_player_sync(websocket: WebSocket, guild_id: int):
    """
    WebSocket endpoint that synchronizes playback state, timestamps, and controls
    with connected Web Remote Dashboard clients every 1 second.
    """
    await websocket.accept()
    logger.info(f"WebSocket client connected for guild {guild_id}")

    try:
        while True:
            # Check bot & player state
            if bot_instance and bot_instance.is_ready():
                guild = bot_instance.get_guild(guild_id)
                if guild and guild.voice_client and isinstance(guild.voice_client, wavelink.Player):
                    p: wavelink.Player = guild.voice_client

                    track_info = None
                    if p.current:
                        track_info = {
                            "title": p.current.title,
                            "author": getattr(p.current, "author", "Unknown"),
                            "duration_ms": getattr(p.current, "length", 0),
                            "position_ms": p.position,
                            "artwork_url": getattr(p.current, "artwork_url", None),
                            "uri": getattr(p.current, "uri", None),
                        }

                    payload = {
                        "type": "SYNC_STATE",
                        "timestamp": int(time.time()),
                        "guild_id": guild_id,
                        "playing": p.playing,
                        "paused": p.paused,
                        "volume": p.volume,
                        "position_ms": p.position,
                        "queue_count": len(p.queue),
                        "track": track_info
                    }
                    await websocket.send_json(payload)
                else:
                    await websocket.send_json({
                        "type": "IDLE",
                        "guild_id": guild_id,
                        "message": "No active voice session in this guild."
                    })
            else:
                await websocket.send_json({"type": "WAITING_BOT"})

            # Sync interval: 1 second
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for guild {guild_id}")
    except Exception as e:
        logger.error(f"WebSocket error in guild {guild_id}: {e}")
        try:
            await websocket.close()
        except:
            pass


# ------------------------------------------------------------------------------
# 4. SPOTIFY OAUTH AUTHENTICATION ROUTES
# ------------------------------------------------------------------------------
def _create_spotify_oauth(user_id: int) -> SpotifyOAuth:
    """Instantiate Spotify OAuth handler with user state."""
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        state=str(user_id),
        show_dialog=True
    )


@app.get("/api/spotify/login")
async def spotify_login(user_id: int = Query(..., description="Discord User ID")):
    """Generates Spotify OAuth authorization URL."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Spotify API credentials are not configured in .env."
        )

    sp_oauth = _create_spotify_oauth(user_id)
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}


@app.get("/api/spotify/callback", response_class=HTMLResponse)
async def spotify_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    """Handles Spotify OAuth callback and stores credentials in SQLite."""
    if not state:
        raise HTTPException(status_code=400, detail="Missing Discord user state in callback.")

    try:
        user_id = int(state)
        sp_oauth = _create_spotify_oauth(user_id)
        token_info = sp_oauth.get_access_token(code, check_cache=False)

        if not token_info or "access_token" not in token_info:
            raise HTTPException(status_code=400, detail="Failed to retrieve Spotify access token.")

        access_token = token_info["access_token"]
        refresh_token = token_info.get("refresh_token", "")
        expires_at = token_info.get("expires_at", time.time() + 3600)

        # Fetch Spotify User ID
        sp = spotipy.Spotify(auth=access_token)
        sp_user = sp.current_user()
        sp_user_id = sp_user.get("id") if sp_user else None

        # Save to async SQLite DB
        await db_manager.save_spotify_token(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            spotify_user_id=sp_user_id
        )

        # Return luxury confirmation page
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Kushida — Spotify Connected</title>
            <style>
                body {{
                    background: #0d0d12;
                    color: #ffffff;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                .card {{
                    background: #181820;
                    border: 1px solid #6b21a8;
                    border-radius: 16px;
                    padding: 40px;
                    text-align: center;
                    max-width: 450px;
                    box-shadow: 0 10px 30px rgba(107, 33, 168, 0.3);
                }}
                h1 {{ color: #10b981; margin-bottom: 10px; font-size: 26px; }}
                p {{ color: #a1a1aa; line-height: 1.6; }}
                .badge {{
                    background: #27272a;
                    color: #38bdf8;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-size: 13px;
                    display: inline-block;
                    margin-top: 15px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>💚 Spotify Connected!</h1>
                <p>Your Spotify account has been successfully linked with <strong>Kushida Luxury Sound</strong>.</p>
                <p>You can now click the <strong>💚 Save to Spotify</strong> button on Discord to instantly like any currently playing track.</p>
                <div class="badge">You can close this window now.</div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error handling Spotify OAuth callback: {e}")
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="background: #0d0d12; color: #f43f5e; font-family: sans-serif; text-align: center; padding-top: 100px;">
            <h2>❌ Authentication Failed</h2>
            <p style="color: #a1a1aa;">{str(e)}</p>
        </body>
        </html>
        """
