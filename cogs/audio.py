"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/audio.py (Wavelink 3.x Audio Engine, Playback & Spotify Sync)
================================================================================
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup, slash_command
from discord import Option, OptionChoice

import wavelink
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import (
    HEX_DEEP_SPACE,
    HEX_VIOLET,
    HEX_ICE_BLUE,
    HEX_EMERALD,
    HEX_ROSE,
    ICON_DISC,
    ICON_PLAY,
    ICON_PAUSE,
    ICON_NEXT,
    ICON_STOP,
    ICON_SPOTIFY,
    ICON_AI,
    ICON_TIMER,
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI,
    API_BASE_URL,
)
from database import db_manager
from utils.luxury_ui import (
    LuxuryEmbedBuilder,
    MusicControlView,
    format_ms,
    DynamicColorEngine,
)

logger = logging.getLogger("kushida.audio")


class Audio(commands.Cog):
    """
    Luxury Audio Cog powered by Wavelink 3.x (Lavalink v4).
    Features lag-free streaming, studio-grade filters, fadeout sleep timer, and Spotify sync.
    """

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        # Internal track history per guild: guild_id -> list of played Playables
        self.history: Dict[int, List[wavelink.Playable]] = {}
        # Active sleep timer tasks: guild_id -> asyncio.Task
        self.sleep_tasks: Dict[int, asyncio.Task] = {}
        # Cached persistent control view instance
        self.persistent_view = MusicControlView()

    # --------------------------------------------------------------------------
    # 1. WAVELINK EVENT LISTENERS (3.x Payload Architecture)
    # --------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        """Fired when Lavalink node connects and is ready."""
        logger.info(
            f"Lavalink Node '{payload.node.identifier}' is READY! (Resumed: {payload.resumed})"
        )

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        """Triggered on track start. Logs to DB and refreshes persistent control panel."""
        player: wavelink.Player = payload.player
        track: wavelink.Playable = payload.track

        if not player or not player.guild:
            return

        guild_id = player.guild.id

        # Maintain history stack
        if guild_id not in self.history:
            self.history[guild_id] = []
        self.history[guild_id].append(track)
        if len(self.history[guild_id]) > 50:
            self.history[guild_id].pop(0)

        # Log to async SQLite database for user stats and VibeMatch
        requester_id = getattr(track, "requester_id", None)
        if requester_id:
            await db_manager.log_listen(
                user_id=requester_id,
                guild_id=guild_id,
                track_title=track.title,
                artist=getattr(track, "author", "Unknown Artist"),
                uri=getattr(track, "uri", ""),
                duration_ms=getattr(track, "length", 0)
            )

        # Refresh or post Persistent UI Panel
        await self._render_or_update_panel(player, track)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        """Triggered when track ends."""
        player: wavelink.Player = payload.player
        logger.debug(f"Track '{payload.track.title}' finished with reason: {payload.reason}")

        # If queue is empty and not playing, clean up panel
        if player and player.queue.is_empty and not player.playing:
            # Let it linger for a bit or update embed
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload) -> None:
        """Handles stream errors gracefully."""
        player: wavelink.Player = payload.player
        track: wavelink.Playable = payload.track
        logger.error(f"Playback exception on track '{track.title}': {payload.exception}")

        coords = await db_manager.get_panel_message_id(player.guild.id)
        if coords:
            channel = player.guild.get_channel(coords[0])
            if channel:
                err_embed = discord.Embed(
                    title="⚠️ Playback Stream Issue",
                    description=f"Could not decode audio stream for **{track.title}**. Skipping to next...",
                    color=HEX_ROSE
                )
                await channel.send(embed=err_embed, delete_after=10)

    # --------------------------------------------------------------------------
    # 2. PERSISTENT PANEL MANAGER
    # --------------------------------------------------------------------------
    async def _render_or_update_panel(self, player: wavelink.Player, track: wavelink.Playable) -> None:
        """Updates the existing control embed in-place or creates a new one cleanly."""
        try:
            guild = player.guild
            coords = await db_manager.get_panel_message_id(guild.id)

            embed = LuxuryEmbedBuilder.now_playing(player, track)
            view = self.persistent_view

            if coords:
                channel_id, message_id = coords
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        existing_msg = await channel.fetch_message(message_id)
                        await existing_msg.edit(embed=embed, view=view)
                        return
                    except discord.NotFound:
                        pass  # Message was deleted, we'll post a fresh one

            # Post fresh panel in the active text channel
            channel = getattr(player, "text_channel", None) or guild.text_channels[0]
            new_msg = await channel.send(embed=embed, view=view)
            await db_manager.set_panel_message_id(guild.id, channel.id, new_msg.id)

        except Exception as e:
            logger.error(f"Error rendering persistent panel in guild {player.guild.id}: {e}")

    # --------------------------------------------------------------------------
    # 3. HELPER: PLAY PREVIOUS TRACK
    # --------------------------------------------------------------------------
    async def play_previous_track(self, guild_id: int) -> bool:
        """Pops and replays the previous track from history."""
        guild = self.bot.get_guild(guild_id)
        if not guild or not guild.voice_client:
            return False

        player: wavelink.Player = guild.voice_client
        guild_history = self.history.get(guild_id, [])

        if len(guild_history) < 2:
            return False

        # Pop current, and get previous
        guild_history.pop()  # Remove current
        prev_track = guild_history.pop()  # Get previous

        # Put current to front of queue, play previous
        await player.play(prev_track)
        return True

    # --------------------------------------------------------------------------
    # 4. HELPER: GRADUAL SLEEP TIMER (Fadeout)
    # --------------------------------------------------------------------------
    async def start_sleep_timer(self, guild_id: int, minutes: int) -> None:
        """
        Schedules a sleep timer that gently fades volume from current % to 0
        over the final 30 seconds before disconnecting.
        """
        # Cancel any existing sleep timer task
        if guild_id in self.sleep_tasks and not self.sleep_tasks[guild_id].done():
            self.sleep_tasks[guild_id].cancel()

        async def _timer_worker():
            try:
                total_wait_sec = minutes * 60
                fade_duration_sec = 30

                if total_wait_sec > fade_duration_sec:
                    await asyncio.sleep(total_wait_sec - fade_duration_sec)

                guild = self.bot.get_guild(guild_id)
                if not guild or not guild.voice_client:
                    return

                player: wavelink.Player = guild.voice_client
                start_vol = player.volume
                steps = 30

                # 30-second smooth fadeout
                for step in range(steps):
                    fraction = (steps - step - 1) / steps
                    new_vol = int(start_vol * fraction)
                    if player.connected:
                        await player.set_volume(new_vol)
                    await asyncio.sleep(1.0)

                # Final disconnect
                if player.connected:
                    player.queue.clear()
                    await player.disconnect()
                    logger.info(f"Sleep timer executed: Disconnected guild {guild_id}")

            except asyncio.CancelledError:
                logger.info(f"Sleep timer cancelled for guild {guild_id}")

        task = asyncio.create_task(_timer_worker())
        self.sleep_tasks[guild_id] = task

    # --------------------------------------------------------------------------
    # 5. HELPER: SPOTIFY SAVE TO LIKED SONGS
    # --------------------------------------------------------------------------
    async def save_track_for_user(self, user_id: int, track: wavelink.Playable) -> Dict[str, Any]:
        """
        Saves the track to user's Spotify 'Liked Songs' via spotipy.
        Prompts authentication link if user has not linked Spotify.
        """
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            return {"success": False, "message": "⚠️ Spotify API credentials are not configured in the bot's `.env`."}

        creds = await db_manager.get_spotify_token(user_id)
        if not creds:
            auth_url = f"{API_BASE_URL}/api/spotify/login?user_id={user_id}"
            return {
                "success": False,
                "message": (
                    f"🔗 **Spotify Not Linked!**\n"
                    f"Click here to authorize Kushida to save songs to your library:\n"
                    f"[👉 **Connect Spotify Account**]({auth_url})"
                )
            }

        # Handle token expiration & refresh
        access_token = creds["spotify_access_token"]
        expires_at = creds["spotify_expires_at"]
        refresh_token = creds["spotify_refresh_token"]

        if time.time() > (expires_at - 60):
            try:
                sp_oauth = SpotifyOAuth(
                    client_id=SPOTIFY_CLIENT_ID,
                    client_secret=SPOTIFY_CLIENT_SECRET,
                    redirect_uri=SPOTIFY_REDIRECT_URI
                )
                new_token_info = sp_oauth.refresh_access_token(refresh_token)
                access_token = new_token_info["access_token"]
                await db_manager.save_spotify_token(
                    user_id=user_id,
                    access_token=access_token,
                    refresh_token=new_token_info.get("refresh_token", refresh_token),
                    expires_at=new_token_info["expires_at"]
                )
            except Exception as e:
                logger.error(f"Failed to refresh Spotify token for user {user_id}: {e}")
                auth_url = f"{API_BASE_URL}/api/spotify/login?user_id={user_id}"
                return {
                    "success": False,
                    "message": f"⚠️ Spotify token expired. Please [**re-authorize here**]({auth_url})."
                }

        # Search track on Spotify and save
        try:
            sp = spotipy.Spotify(auth=access_token)
            clean_title = track.title.split("(")[0].split("[")[0].strip()
            author = getattr(track, "author", "")
            q = f"{clean_title} {author}".strip()

            results = sp.search(q=q, type="track", limit=1)
            items = results.get("tracks", {}).get("items", [])

            if not items:
                # Retry with title only
                results = sp.search(q=clean_title, type="track", limit=1)
                items = results.get("tracks", {}).get("items", [])

            if not items:
                return {"success": False, "message": f"❌ Could not match **{track.title}** on Spotify."}

            spotify_track = items[0]
            sp.current_user_saved_tracks_add(tracks=[spotify_track["id"]])

            sp_title = spotify_track["name"]
            sp_artist = spotify_track["artists"][0]["name"]
            sp_url = spotify_track["external_urls"]["spotify"]

            return {
                "success": True,
                "message": f"💚 **Saved to Spotify Liked Songs!**\n[**{sp_title}** by `{sp_artist}`]({sp_url})"
            }
        except Exception as e:
            logger.error(f"Spotify API save error for user {user_id}: {e}")
            return {"success": False, "message": f"❌ Spotify error: `{str(e)}`"}

    # --------------------------------------------------------------------------
    # 6. SLASH COMMANDS
    # --------------------------------------------------------------------------
    @slash_command(name="play", description="Stream a song, playlist, or URL in ultra-high quality.")
    async def play_command(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Song title, artist, YouTube, or SoundCloud link", required=True)
    ):
        """Slash command to search and queue audio."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)
            return

        await ctx.defer()

        # Connect or fetch player
        player: wavelink.Player
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            player = ctx.voice_client

        # Store caller text channel for panel updates
        player.text_channel = ctx.channel

        # Search playable tracks
        search_results: wavelink.Search = await wavelink.Playable.search(query)
        if not search_results:
            await ctx.respond(f"❌ No audio results found for `{query}`.", ephemeral=True)
            return

        if isinstance(search_results, wavelink.Playlist):
            for t in search_results.tracks:
                setattr(t, "requester_id", ctx.author.id)
            added = await player.queue.put_wait(search_results)
            embed = discord.Embed(
                title="📑 Playlist Queued",
                description=f"Added **{search_results.name}** (`{added} tracks`) to the queue.",
                color=HEX_VIOLET
            )
            await ctx.respond(embed=embed)
        else:
            track: wavelink.Playable = search_results[0]
            setattr(track, "requester_id", ctx.author.id)
            await player.queue.put_wait(track)

            if not player.playing:
                await ctx.respond(f"🎵 Starting playback for **{track.title}**...")
            else:
                embed = discord.Embed(
                    title="➕ Track Queued",
                    description=f"Added **{track.title}** to the queue.\n`{getattr(track, 'author', 'Unknown')}` • `{format_ms(getattr(track, 'length', 0))}`",
                    color=HEX_ICE_BLUE
                )
                if getattr(track, "artwork_url", None):
                    embed.set_thumbnail(url=track.artwork_url)
                await ctx.respond(embed=embed)

        # Start playback if currently idle
        if not player.playing and not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)

    @slash_command(name="pause", description="Pause or resume current playback.")
    async def pause_command(self, ctx: discord.ApplicationContext):
        """Toggle pause."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)
            return

        if player.paused:
            await player.pause(False)
            await ctx.respond("▶️ Resumed playback.")
        else:
            await player.pause(True)
            await ctx.respond("⏸️ Paused playback.")

    @slash_command(name="skip", description="Skip the current track.")
    async def skip_command(self, ctx: discord.ApplicationContext):
        """Skip current track."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.playing:
            await ctx.respond("❌ Nothing is currently playing to skip.", ephemeral=True)
            return

        await player.skip()
        await ctx.respond("⏭️ Skipped current track.")

    @slash_command(name="previous", description="Replay the previous track from history.")
    async def previous_command(self, ctx: discord.ApplicationContext):
        """Play previous track."""
        success = await self.play_previous_track(ctx.guild.id)
        if success:
            await ctx.respond("⏮️ Replaying previous track.")
        else:
            await ctx.respond("❌ No previous track found in history.", ephemeral=True)

    @slash_command(name="stop", description="Stop playback, clear queue, and disconnect.")
    async def stop_command(self, ctx: discord.ApplicationContext):
        """Stop and disconnect."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            await ctx.respond("❌ Bot is not connected to a voice channel.", ephemeral=True)
            return

        player.queue.clear()
        await player.disconnect()
        await ctx.respond("⏹️ Playback stopped and disconnected.")

    @slash_command(name="queue", description="View the current upcoming queue.")
    async def queue_command(
        self,
        ctx: discord.ApplicationContext,
        page: Option(int, "Queue page number", default=1, min_value=1, required=False)
    ):
        """Show paginated queue."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            await ctx.respond("❌ The queue is completely empty.", ephemeral=True)
            return

        embed = LuxuryEmbedBuilder.queue_embed(player, page=page)
        await ctx.respond(embed=embed)

    @slash_command(name="volume", description="Set audio volume (0-200%).")
    async def volume_command(
        self,
        ctx: discord.ApplicationContext,
        volume: Option(int, "Volume level percentage", min_value=0, max_value=200, required=True)
    ):
        """Set volume."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            await ctx.respond("❌ Bot is not in a voice channel.", ephemeral=True)
            return

        await player.set_volume(volume)
        await ctx.respond(f"🔊 Volume set to **{volume}%**.")

    @slash_command(name="seek", description="Seek to a specific timestamp in the current track.")
    async def seek_command(
        self,
        ctx: discord.ApplicationContext,
        seconds: Option(int, "Timestamp in seconds", min_value=0, required=True)
    ):
        """Seek position."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.playing:
            await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)
            return

        pos_ms = seconds * 1000
        await player.seek(pos_ms)
        await ctx.respond(f"⏩ Seeked to `{format_ms(pos_ms)}`.")

    @slash_command(name="filter", description="Apply studio-grade audio filter presets.")
    async def filter_command(
        self,
        ctx: discord.ApplicationContext,
        preset: Option(
            str,
            "Filter preset to apply",
            choices=["bassboost", "nightcore", "8d", "vaporwave", "reset"],
            required=True
        )
    ):
        """Apply Wavelink Filters."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            await ctx.respond("❌ Bot is not in a voice channel.", ephemeral=True)
            return

        filters: wavelink.Filters = player.filters
        preset = preset.lower()

        if preset == "bassboost":
            filters.reset()
            bass_bands = [(0, 0.30), (1, 0.25), (2, 0.20), (3, 0.15), (4, 0.10)]
            filters.equalizer.set(bands=bass_bands)
            desc = "🔊 **Bassboost** applied: Low frequencies amplified."
        elif preset == "nightcore":
            filters.reset()
            filters.timescale.set(pitch=1.25, speed=1.25, rate=1.0)
            desc = "⚡ **Nightcore** applied: 1.25x Speed & Pitch."
        elif preset == "8d":
            filters.reset()
            filters.rotation.set(rotation_hz=0.2)
            desc = "🎧 **8D Audio** applied: Rotating spatial surround."
        elif preset == "vaporwave":
            filters.reset()
            filters.timescale.set(pitch=0.80, speed=0.85, rate=1.0)
            desc = "🌊 **Vaporwave** applied: Slowed & Reverb ambience."
        elif preset == "reset":
            filters.reset()
            desc = "✨ **Filters Reset**: Crystal clear studio audio."
        else:
            await ctx.respond("❌ Unknown filter preset.", ephemeral=True)
            return

        await player.set_filters(filters)
        embed = discord.Embed(title="🎛️ Audio Processing", description=desc, color=HEX_VIOLET)
        await ctx.respond(embed=embed)

    @slash_command(name="sleep", description="Set sleep timer with 30s volume fadeout before disconnect.")
    async def sleep_command(
        self,
        ctx: discord.ApplicationContext,
        minutes: Option(int, "Minutes until gentle disconnect", min_value=1, max_value=360, required=True)
    ):
        """Schedule sleep timer."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            await ctx.respond("❌ Bot is not connected to a voice channel.", ephemeral=True)
            return

        await self.start_sleep_timer(ctx.guild.id, minutes)
        await ctx.respond(
            f"💤 **Sleep Timer Set:** Music will gently fade to 0% and disconnect in **{minutes} minutes**."
        )

    @slash_command(name="nowplaying", description="Show or re-send the luxury persistent music panel.")
    async def nowplaying_command(self, ctx: discord.ApplicationContext):
        """Re-send the luxury persistent music panel."""
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)
            return

        player.text_channel = ctx.channel
        embed = LuxuryEmbedBuilder.now_playing(player, player.current, requested_by=ctx.author)
        msg = await ctx.respond(embed=embed, view=self.persistent_view)
        # Store message ID for persistent in-place edits
        if hasattr(msg, "id"):
            await db_manager.set_panel_message_id(ctx.guild.id, ctx.channel.id, msg.id)


def setup(bot: discord.Bot):
    """Cog loader for Pycord."""
    bot.add_cog(Audio(bot))
