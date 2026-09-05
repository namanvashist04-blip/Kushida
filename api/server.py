"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: api/server.py (FastAPI Backend, WebSockets & Demon Terminal UI)
================================================================================
"""

import asyncio
import logging
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

import discord
import wavelink
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import (
    API_HOST,
    API_PORT,
    TOPGG_AUTH,
    HEX_DEMON_BG,
    HEX_DEMON_PURPLE,
    HEX_DEMON_RED,
)
from database import db_manager

logger = logging.getLogger("demon.api")
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title="Demon Music Terminal API",
    description="High-performance REST API and WebSocket gateway for Demon Music Bot remote control.",
    version="3.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files from web/
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Bot Instance reference
bot_instance: Any = None


def set_bot_instance(bot: Any) -> None:
    global bot_instance
    bot_instance = bot


def _get_active_player() -> Optional[wavelink.Player]:
    if not bot_instance:
        return None
    for g in bot_instance.guilds:
        p = getattr(g, "voice_client", None)
        if p and isinstance(p, wavelink.Player) and p.connected:
            return p
    return None


# ------------------------------------------------------------------------------
# 1. FRONTEND TERMINAL DASHBOARD
# ------------------------------------------------------------------------------
@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>Demon Music Terminal is loading...</h1>")


# ------------------------------------------------------------------------------
# 2. TOP.GG VOTE WEBHOOK
# ------------------------------------------------------------------------------
@app.post("/vote")
@app.post("/api/vote")
async def handle_topgg_vote(request: Request, authorization: Optional[str] = Header(None)):
    """Receives and records Top.gg voting webhooks."""
    if TOPGG_AUTH and authorization != TOPGG_AUTH:
        raise HTTPException(status_code=401, detail="Unauthorized vote webhook.")

    try:
        payload = await request.json()
        user_id_str = payload.get("user")
        if user_id_str:
            user_id = int(user_id_str)
            await db_manager.record_vote(user_id)
            logger.info(f"Top.gg vote recorded for user: {user_id}")
            return {"status": "success", "user": user_id}
    except Exception as e:
        logger.error(f"Error processing vote webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ignored"}


# ------------------------------------------------------------------------------
# 3. PLAYBACK CONTROL SCHEMAS & ROUTES
# ------------------------------------------------------------------------------
class PlayPayload(BaseModel):
    query: str
    guild_id: Optional[int] = None

class VolumePayload(BaseModel):
    volume: int
    guild_id: Optional[int] = None

class PausePayload(BaseModel):
    paused: bool
    guild_id: Optional[int] = None

class SeekPayload(BaseModel):
    position_ms: int
    guild_id: Optional[int] = None


@app.post("/api/play")
async def api_play(payload: PlayPayload):
    player = _get_active_player()
    if not player or not bot_instance:
        raise HTTPException(status_code=404, detail="No active voice channel connection found.")

    async def _action():
        tracks = await wavelink.Playable.search(payload.query)
        if not tracks:
            return {"success": False, "message": "No tracks found"}
        t = tracks[0] if not isinstance(tracks, wavelink.Playlist) else tracks.tracks[0]
        t.requester_name = "Web Terminal"
        if not player.playing:
            await player.play(t)
        else:
            await player.queue.put_wait(t)
        return {"success": True, "title": t.title}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


@app.post("/api/pause")
async def api_pause(payload: PausePayload):
    player = _get_active_player()
    if not player or not bot_instance:
        return {"success": False}

    async def _action():
        await player.pause(payload.paused)
        return {"success": True, "paused": player.paused}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


@app.post("/api/skip")
async def api_skip():
    player = _get_active_player()
    if not player or not bot_instance:
        return {"success": False}

    async def _action():
        await player.skip(force=True)
        return {"success": True}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


@app.post("/api/volume")
async def api_volume(payload: VolumePayload):
    player = _get_active_player()
    if not player or not bot_instance:
        return {"success": False}

    async def _action():
        await player.set_volume(payload.volume)
        return {"success": True, "volume": player.volume}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


@app.post("/api/seek")
async def api_seek(payload: SeekPayload):
    player = _get_active_player()
    if not player or not bot_instance:
        return {"success": False}

    async def _action():
        await player.seek(payload.position_ms)
        return {"success": True, "position": payload.position_ms}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


@app.post("/api/clearqueue")
async def api_clearqueue():
    player = _get_active_player()
    if not player:
        return {"success": False}
    player.queue.clear()
    return {"success": True}


@app.post("/api/shuffle")
async def api_shuffle():
    player = _get_active_player()
    if not player:
        return {"success": False}
    player.queue.shuffle()
    return {"success": True}


@app.post("/api/leave")
async def api_leave():
    player = _get_active_player()
    if not player or not bot_instance:
        return {"success": False}

    async def _action():
        await player.disconnect(force=True)
        return {"success": True}

    fut = asyncio.run_coroutine_threadsafe(_action(), bot_instance.loop)
    return await asyncio.wrap_future(fut)


# ------------------------------------------------------------------------------
# 4. WEBSOCKET GATEWAY FOR LIVE TERMINAL SYNCHRONIZATION
# ------------------------------------------------------------------------------
@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Terminal UI WebSocket connected.")

    try:
        while True:
            player = _get_active_player()
            if player and player.connected:
                curr_info = None
                if player.current:
                    curr_info = {
                        "title": player.current.title,
                        "author": getattr(player.current, "author", "Unknown"),
                        "duration_ms": getattr(player.current, "length", 0),
                        "artwork": getattr(player.current, "artwork", None),
                        "uri": getattr(player.current, "uri", "")
                    }

                queue_list = [
                    {
                        "title": t.title,
                        "author": getattr(t, "author", "Unknown"),
                        "duration_ms": getattr(t, "length", 0),
                        "artwork": getattr(t, "artwork", None)
                    }
                    for t in list(player.queue)[:20]
                ]

                data = {
                    "type": "PLAYER_UPDATE",
                    "guild_name": player.guild.name if player.guild else "Demon's Realm",
                    "channel_name": player.channel.name if player.channel else "Music Lounge",
                    "playing": player.playing,
                    "paused": player.paused,
                    "volume": player.volume,
                    "position_ms": int(player.position),
                    "current": curr_info,
                    "queue": queue_list
                }
                await websocket.send_json(data)
            else:
                await websocket.send_json({
                    "type": "IDLE",
                    "guild_name": "Demon's Realm",
                    "channel_name": "Music Lounge"
                })

            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("Terminal UI WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
