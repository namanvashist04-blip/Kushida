"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/music.py (All 21 Music Slash Commands)
================================================================================
"""

import asyncio
import logging
import random
import re
import urllib.parse
from typing import Optional, List, Dict, Any

import aiohttp
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import wavelink

from config import (
    HEX_DEMON_PURPLE,
    HEX_DEMON_RED,
    HEX_DEMON_ACCENT,
    HEX_EMERALD,
    HEX_MUTED,
    PB_FILL,
    PB_HEAD,
    PB_EMPTY,
    PB_LENGTH,
)
from database import db_manager
from utils.luxury_ui import LuxuryEmbedBuilder, MusicControlView, format_ms

logger = logging.getLogger("demon.music")


async def is_dj_or_admin(ctx: discord.ApplicationContext) -> bool:
    """Helper to check DJ/Admin permission if DJ-only mode is active."""
    if not ctx.guild:
        return True
    if ctx.author.guild_permissions.administrator:
        return True
    dj_only = await db_manager.get_dj_only(ctx.guild.id)
    if not dj_only:
        return True
    dj_roles = await db_manager.get_dj_roles(ctx.guild.id)
    if not dj_roles:
        return True
    author_role_ids = [r.id for r in ctx.author.roles]
    if any(rid in dj_roles for rid in author_role_ids):
        return True
    return False


def make_progress_bar(position_ms: int, duration_ms: int, length: int = PB_LENGTH) -> str:
    """Render sleek Discord progress bar."""
    if duration_ms <= 0:
        return f"{PB_HEAD}{PB_EMPTY * (length - 1)}"
    fraction = min(max(position_ms / duration_ms, 0.0), 1.0)
    filled = int(fraction * length)
    empty = length - filled - 1
    if empty < 0:
        empty = 0
    return f"{PB_FILL * filled}{PB_HEAD}{PB_EMPTY * empty}"


class MusicCog(commands.Cog, name="Music"):
    """All 21 Core Music Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.history: Dict[int, List[wavelink.Playable]] = {}
        self.autoplay_enabled: Dict[int, bool] = {}
        self._view: Optional[MusicControlView] = None

    @property
    def persistent_view(self) -> MusicControlView:
        if self._view is None:
            self._view = MusicControlView()
        return self._view

    # --------------------------------------------------------------------------
    # WAVELINK EVENT LISTENERS
    # --------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        logger.info(f"Lavalink Node '{payload.node.identifier}' is READY! (Resumed: {payload.resumed})")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player = payload.player
        track: wavelink.Playable = payload.track

        if not player or not player.guild:
            return

        guild_id = player.guild.id
        if guild_id not in self.history:
            self.history[guild_id] = []
        self.history[guild_id].append(track)
        if len(self.history[guild_id]) > 50:
            self.history[guild_id].pop(0)

        # Log to Database
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

        await self._render_or_update_panel(player, track)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: wavelink.Player = payload.player
        if not player or not player.guild:
            return

        guild_id = player.guild.id
        if not player.queue.is_empty and not player.playing:
            try:
                next_track = player.queue.get()
                await player.play(next_track)
            except Exception as e:
                logger.error(f"Error auto-advancing track: {e}")
        elif player.queue.is_empty:
            # Check autoplay
            if self.autoplay_enabled.get(guild_id, False) and payload.track:
                try:
                    query = f"{payload.track.author} {payload.track.title} mix"
                    search_res = await wavelink.Playable.search(query)
                    if search_res:
                        rec = search_res[0] if not isinstance(search_res, wavelink.Playlist) else search_res.tracks[0]
                        rec.requester_id = self.bot.user.id
                        rec.requester_name = "Autoplay"
                        await player.play(rec)
                        return
                except Exception as ex:
                    logger.error(f"Autoplay recommendation error: {ex}")

            # Check 24/7 setting
            is_247 = await db_manager.get_guild_247(guild_id)
            if not is_247:
                logger.info(f"Queue empty and 24/7 disabled for guild {guild_id}.")

    async def _render_or_update_panel(self, player: wavelink.Player, track: wavelink.Playable) -> None:
        try:
            guild = player.guild
            coords = await db_manager.get_panel_message_id(guild.id)
            if coords:
                old_channel = guild.get_channel(coords[0])
                if old_channel:
                    try:
                        old_msg = await old_channel.fetch_message(coords[1])
                        await old_msg.delete()
                    except Exception:
                        pass

            embed = LuxuryEmbedBuilder.now_playing(player, track)
            target_channel = getattr(player, "text_channel", None)
            if not target_channel:
                candidates = [tc for tc in guild.text_channels if tc.permissions_for(guild.me).send_messages]
                for c in candidates:
                    if any(k in c.name.lower() for k in ["music", "bot", "sound", "song", "command", "general"]):
                        target_channel = c
                        break
                if not target_channel and candidates:
                    target_channel = candidates[0]

            if target_channel:
                player.text_channel = target_channel
                new_msg = await target_channel.send(embed=embed, view=self.persistent_view)
                await db_manager.set_panel_message_id(guild.id, target_channel.id, new_msg.id)
        except Exception as e:
            logger.error(f"Error updating panel in guild {player.guild.id}: {e}")

    async def play_previous_track(self, guild_id: int) -> bool:
        guild = self.bot.get_guild(guild_id)
        if not guild or not guild.voice_client:
            return False
        player: wavelink.Player = guild.voice_client
        history = self.history.get(guild_id, [])
        if len(history) < 2:
            return False
        history.pop()  # current
        prev_track = history.pop()  # previous
        await player.play(prev_track)
        return True


    # ==========================================================================
    # 1. /play [query] (and alias /p)
    # ==========================================================================
    @slash_command(name="play", description="🎵 Play a song, playlist, or stream (Name, YouTube, Spotify, SoundCloud)")
    async def play(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Song title, artist, YouTube / Spotify / SoundCloud URL", required=True)
    ):
        await self._do_play(ctx, query)

    @slash_command(name="p", description="🎵 Shortcut for /play")
    async def p(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Song title, artist, or URL", required=True)
    ):
        await self._do_play(ctx, query)

    async def _do_play(self, ctx: discord.ApplicationContext, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)

        await ctx.defer()
        target_vc = ctx.author.voice.channel
        player: Optional[wavelink.Player] = ctx.voice_client

        if not player or not player.connected:
            if player:
                try:
                    await player.disconnect(force=True)
                except Exception:
                    pass
            try:
                player = await target_vc.connect(cls=wavelink.Player, timeout=15)
            except Exception as e:
                logger.error(f"Voice connect error: {e}")
                return await ctx.followup.send(f"❌ Could not connect to **{target_vc.name}**. Please check bot voice permissions.")
        elif player.channel.id != target_vc.id:
            try:
                await player.move_to(target_vc)
            except Exception:
                pass

        player.text_channel = ctx.channel

        clean_query = query.strip()
        if "music.youtube.com" in clean_query:
            clean_query = clean_query.replace("music.youtube.com", "www.youtube.com")

        try:
            search_results = await wavelink.Playable.search(clean_query)
        except Exception as e:
            logger.warning(f"Error loading tracks for '{clean_query}': {e}")
            return await ctx.followup.send(
                "❌ **Audio Load Error:** Could not resolve track.\n"
                "• Playlists must be Public or Unlisted.\n"
                "• Try searching with the song name directly: `/play faded alan walker`"
            )

        if not search_results:
            return await ctx.followup.send(f"🔍 No results found for: `{clean_query}`")

        if isinstance(search_results, wavelink.Playlist):
            playlist: wavelink.Playlist = search_results
            for t in playlist.tracks:
                t.requester_id = ctx.author.id
                t.requester_name = ctx.author.display_name

            if not player.playing:
                first_track = playlist.tracks[0]
                for t in playlist.tracks[1:]:
                    await player.queue.put_wait(t)
                await player.play(first_track)
            else:
                for t in playlist.tracks:
                    await player.queue.put_wait(t)

            embed = discord.Embed(
                title="📑 Playlist Queued",
                description=f"Added **{len(playlist.tracks)} tracks** from **{playlist.name}**",
                color=HEX_DEMON_PURPLE
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            return await ctx.followup.send(embed=embed)

        track: wavelink.Playable = search_results[0]
        track.requester_id = ctx.author.id
        track.requester_name = ctx.author.display_name

        if not player.playing:
            await player.play(track)
            embed = discord.Embed(
                title="▶️ Now Playing",
                description=f"**[{track.title}]({getattr(track, 'uri', '')})**\nBy `{getattr(track, 'author', 'Unknown')}`",
                color=HEX_DEMON_PURPLE
            )
            if hasattr(track, "artwork") and track.artwork:
                embed.set_thumbnail(url=track.artwork)
            embed.set_footer(text=f"Duration: {format_ms(getattr(track, 'length', 0))} | Requested by {ctx.author.display_name}")
            return await ctx.followup.send(embed=embed)
        else:
            await player.queue.put_wait(track)
            embed = discord.Embed(
                title="📥 Added to Queue",
                description=f"**[{track.title}]({getattr(track, 'uri', '')})**\nPosition #{player.queue.count}",
                color=HEX_DEMON_ACCENT
            )
            if hasattr(track, "artwork") and track.artwork:
                embed.set_thumbnail(url=track.artwork)
            embed.set_footer(text=f"Duration: {format_ms(getattr(track, 'length', 0))} | Requested by {ctx.author.display_name}")
            return await ctx.followup.send(embed=embed)

    # ==========================================================================
    # 2. /pause
    # ==========================================================================
    @slash_command(name="pause", description="⏸️ Pause currently playing music")
    async def pause(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active. Only DJs or Admins can pause.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.playing:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)
        if player.paused:
            return await ctx.respond("⚠️ Playback is already paused. Use `/resume`.", ephemeral=True)
        await player.pause(True)
        await ctx.respond("⏸️ **Playback paused.**")

    # ==========================================================================
    # 3. /resume
    # ==========================================================================
    @slash_command(name="resume", description="▶️ Resume paused music")
    async def resume(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active. Only DJs or Admins can resume.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)
        if not player.paused:
            return await ctx.respond("⚠️ Playback is already running.", ephemeral=True)
        await player.pause(False)
        await ctx.respond("▶️ **Playback resumed.**")

    # ==========================================================================
    # 4. /skip
    # ==========================================================================
    @slash_command(name="skip", description="⏭️ Skip current playing song")
    async def skip(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active. Only DJs or Admins can skip.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.playing:
            return await ctx.respond("❌ Nothing is playing to skip.", ephemeral=True)
        current = player.current
        await player.skip(force=True)
        await ctx.respond(f"⏭️ Skipped: **{current.title if current else 'Track'}**")

    # ==========================================================================
    # 5. /skipto [position]
    # ==========================================================================
    @slash_command(name="skipto", description="⏩ Jump directly to a track in queue by its position number")
    async def skipto(
        self,
        ctx: discord.ApplicationContext,
        position: Option(int, "Position in queue (e.g. 3)", required=True, min_value=1)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.respond("❌ Queue is currently empty.", ephemeral=True)
        if position > player.queue.count:
            return await ctx.respond(f"❌ Position `{position}` out of range. Current queue length: `{player.queue.count}`", ephemeral=True)

        for _ in range(position - 1):
            player.queue.get()
        target_track = player.queue.get()
        await player.play(target_track)
        await ctx.respond(f"⏩ Jumped to position #{position}: **{target_track.title}**")

    # ==========================================================================
    # 6. /previous
    # ==========================================================================
    @slash_command(name="previous", description="⏮️ Play the previously played song")
    async def previous(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player:
            return await ctx.respond("❌ Bot is not in voice.", ephemeral=True)

        history = self.history.get(ctx.guild.id, [])
        if len(history) < 2:
            return await ctx.respond("❌ No previous track in history.", ephemeral=True)

        history.pop()  # current
        prev_track = history.pop()  # previous
        await player.play(prev_track)
        await ctx.respond(f"⏮️ Replaying previous track: **{prev_track.title}**")

    # ==========================================================================
    # 7. /stop
    # ==========================================================================
    @slash_command(name="stop", description="⏹️ Stop playback and clear the queue")
    async def stop(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player:
            return await ctx.respond("❌ Bot is not playing.", ephemeral=True)

        player.queue.clear()
        await player.stop()

        is_247 = await db_manager.get_guild_247(ctx.guild.id)
        if not is_247:
            await player.disconnect()
            await ctx.respond("⏹️ **Playback stopped, queue cleared, and disconnected.**")
        else:
            await ctx.respond("⏹️ **Playback stopped and queue cleared.** (24/7 mode active - remaining in VC)")

    # ==========================================================================
    # 8. /queue [page]
    # ==========================================================================
    @slash_command(name="queue", description="📜 View the upcoming queue list")
    async def queue(
        self,
        ctx: discord.ApplicationContext,
        page: Option(int, "Page number", required=False, default=1, min_value=1)
    ):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            return await ctx.respond("📭 The queue is currently empty.", ephemeral=True)

        tracks = list(player.queue)
        items_per_page = 10
        total_pages = max(1, (len(tracks) + items_per_page - 1) // items_per_page)

        if page > total_pages:
            page = total_pages

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_tracks = tracks[start_idx:end_idx]

        embed = discord.Embed(
            title=f"📜 Queue for {ctx.guild.name}",
            color=HEX_DEMON_PURPLE
        )

        if player.current:
            pos_str = format_ms(int(player.position))
            dur_str = format_ms(int(getattr(player.current, "length", 0)))
            embed.add_field(
                name="▶️ Now Playing",
                value=f"**[{player.current.title}]({getattr(player.current, 'uri', '')})**\n`{pos_str} / {dur_str}` | Req: `{getattr(player.current, 'requester_name', 'Unknown')}`",
                inline=False
            )

        if page_tracks:
            lines = []
            for i, t in enumerate(page_tracks, start=start_idx + 1):
                d_str = format_ms(int(getattr(t, "length", 0)))
                r_name = getattr(t, "requester_name", "Unknown")
                lines.append(f"`#{i:02d}` **[{t.title}]({getattr(t, 'uri', '')})** — `{d_str}` ({r_name})")
            embed.description = "\n".join(lines)
        else:
            embed.description = "_No more songs in upcoming queue._"

        embed.set_footer(text=f"Page {page}/{total_pages} | Total in queue: {player.queue.count}")
        await ctx.respond(embed=embed)

    # ==========================================================================
    # 9. /clearqueue
    # ==========================================================================
    @slash_command(name="clearqueue", description="🗑️ Clear all upcoming songs without stopping current track")
    async def clearqueue(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.respond("❌ Queue is already empty.", ephemeral=True)
        count = player.queue.count
        player.queue.clear()
        await ctx.respond(f"🗑️ Cleared **{count} songs** from the upcoming queue.")

    # ==========================================================================
    # 10. /nowplaying (and alias /np)
    # ==========================================================================
    @slash_command(name="nowplaying", description="🎶 Display detailed information about the currently playing song")
    async def nowplaying(self, ctx: discord.ApplicationContext):
        await self._do_nowplaying(ctx)

    @slash_command(name="np", description="🎶 Shortcut for /nowplaying")
    async def np(self, ctx: discord.ApplicationContext):
        await self._do_nowplaying(ctx)

    async def _do_nowplaying(self, ctx: discord.ApplicationContext):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)

        track = player.current
        pos_ms = int(player.position)
        dur_ms = int(getattr(track, "length", 0))
        bar = make_progress_bar(pos_ms, dur_ms)

        embed = discord.Embed(
            title=track.title,
            url=getattr(track, "uri", ""),
            color=HEX_DEMON_PURPLE
        )
        if hasattr(track, "artwork") and track.artwork:
            embed.set_thumbnail(url=track.artwork)

        embed.add_field(name="Artist", value=f"`{getattr(track, 'author', 'Unknown')}`", inline=True)
        embed.add_field(name="Requested By", value=f"`{getattr(track, 'requester_name', 'Unknown')}`", inline=True)
        embed.add_field(name="Volume", value=f"`{player.volume}%`", inline=True)
        embed.add_field(name="Progress", value=f"`{format_ms(pos_ms)}` {bar} `{format_ms(dur_ms)}`", inline=False)

        await ctx.respond(embed=embed)

    # ==========================================================================
    # 11. /volume [level]
    # ==========================================================================
    @slash_command(name="volume", description="🔊 Adjust player playback volume (1-150%)")
    async def volume(
        self,
        ctx: discord.ApplicationContext,
        level: Option(int, "Volume percentage (1 - 150)", required=True, min_value=1, max_value=150)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        await player.set_volume(level)
        await ctx.respond(f"🔊 Volume set to **{level}%**")

    # ==========================================================================
    # 12. /loop [mode]
    # ==========================================================================
    @slash_command(name="loop", description="🔁 Set loop mode (Off, Track, Queue)")
    async def loop(
        self,
        ctx: discord.ApplicationContext,
        mode: Option(str, "Select loop mode", choices=["Off", "Track", "Queue"], required=True)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player:
            return await ctx.respond("❌ Bot is not in voice.", ephemeral=True)

        if mode == "Off":
            player.queue.mode = wavelink.QueueMode.normal
            await ctx.respond("➡️ Loop disabled (`Normal mode`).")
        elif mode == "Track":
            player.queue.mode = wavelink.QueueMode.loop
            await ctx.respond("🔂 Looping **current track**.")
        elif mode == "Queue":
            player.queue.mode = wavelink.QueueMode.loop_all
            await ctx.respond("🔁 Looping **entire queue**.")

    # ==========================================================================
    # 13. /shuffle
    # ==========================================================================
    @slash_command(name="shuffle", description="🔀 Shuffle upcoming queue using Fisher-Yates algorithm")
    async def shuffle(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.respond("❌ Queue is empty. Nothing to shuffle.", ephemeral=True)

        player.queue.shuffle()
        await ctx.respond(f"🔀 Shuffled **{player.queue.count} tracks** in the queue.")

    # ==========================================================================
    # 14. /seek [time]
    # ==========================================================================
    @slash_command(name="seek", description="⏩ Seek to a specific timestamp in the current song (e.g. 01:30 or seconds)")
    async def seek(
        self,
        ctx: discord.ApplicationContext,
        time: Option(str, "Timestamp (e.g. 01:45 or 105)", required=True)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)

        target_ms = 0
        clean = time.strip()
        if ":" in clean:
            parts = clean.split(":")
            if len(parts) == 2:
                target_ms = (int(parts[0]) * 60 + int(parts[1])) * 1000
            elif len(parts) == 3:
                target_ms = (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
        else:
            target_ms = int(clean) * 1000

        dur_ms = int(getattr(player.current, "length", 0))
        if target_ms > dur_ms:
            return await ctx.respond("❌ Timestamp exceeds track duration.", ephemeral=True)

        await player.seek(target_ms)
        await ctx.respond(f"⏩ Seeked to **{format_ms(target_ms)}**")

    # ==========================================================================
    # 15. /forward [seconds]
    # ==========================================================================
    @slash_command(name="forward", description="⏩ Fast-forward current song by N seconds")
    async def forward(
        self,
        ctx: discord.ApplicationContext,
        seconds: Option(int, "Seconds to jump forward (e.g. 15)", required=True, min_value=1)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)

        new_pos = int(player.position) + (seconds * 1000)
        dur_ms = int(getattr(player.current, "length", 0))
        new_pos = min(new_pos, dur_ms)
        await player.seek(new_pos)
        await ctx.respond(f"⏩ Forwarded **+{seconds}s** (Position: `{format_ms(new_pos)}`)")

    # ==========================================================================
    # 16. /backward [seconds]
    # ==========================================================================
    @slash_command(name="backward", description="⏪ Rewind current song by N seconds")
    async def backward(
        self,
        ctx: discord.ApplicationContext,
        seconds: Option(int, "Seconds to rewind (e.g. 15)", required=True, min_value=1)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)

        new_pos = max(0, int(player.position) - (seconds * 1000))
        await player.seek(new_pos)
        await ctx.respond(f"⏪ Rewound **-{seconds}s** (Position: `{format_ms(new_pos)}`)")

    # ==========================================================================
    # 17. /remove [position]
    # ==========================================================================
    @slash_command(name="remove", description="❌ Remove a song from the queue by its index")
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        position: Option(int, "Position number in queue to remove", required=True, min_value=1)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.respond("❌ Queue is currently empty.", ephemeral=True)
        if position > player.queue.count:
            return await ctx.respond(f"❌ Position `{position}` does not exist. Queue has `{player.queue.count}` songs.", ephemeral=True)

        tracks = list(player.queue)
        removed_track = tracks.pop(position - 1)
        player.queue.clear()
        for t in tracks:
            await player.queue.put_wait(t)

        await ctx.respond(f"🗑️ Removed #{position}: **{removed_track.title}**")

    # ==========================================================================
    # 18. /join
    # ==========================================================================
    @slash_command(name="join", description="🔊 Summon bot to your current voice channel")
    async def join(self, ctx: discord.ApplicationContext):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.respond("❌ You must be connected to a voice channel first!", ephemeral=True)

        target_vc = ctx.author.voice.channel
        player: Optional[wavelink.Player] = ctx.voice_client

        if player and player.connected:
            if player.channel.id == target_vc.id:
                return await ctx.respond(f"🔊 Already connected to **{target_vc.name}**.")
            await player.move_to(target_vc)
            return await ctx.respond(f"🔊 Moved to **{target_vc.name}**.")

        try:
            player = await target_vc.connect(cls=wavelink.Player, timeout=15)
            player.text_channel = ctx.channel
            await ctx.respond(f"🔊 Successfully joined **{target_vc.name}**!")
        except Exception as e:
            logger.error(f"Error joining channel: {e}")
            await ctx.respond(f"❌ Could not join **{target_vc.name}**: `{e}`", ephemeral=True)

    # ==========================================================================
    # 19. /leave
    # ==========================================================================
    @slash_command(name="leave", description="🚪 Disconnect the bot from voice channel")
    async def leave(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not in any voice channel.", ephemeral=True)

        player.queue.clear()
        await player.disconnect(force=True)
        await ctx.respond("👋 **Disconnected from voice channel.**")

    # ==========================================================================
    # 20. /autoplay
    # ==========================================================================
    @slash_command(name="autoplay", description="🔄 Toggle autoplay recommendations when queue finishes")
    async def autoplay(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)

        guild_id = ctx.guild.id
        current = self.autoplay_enabled.get(guild_id, False)
        new_state = not current
        self.autoplay_enabled[guild_id] = new_state

        status_text = "ENABLED" if new_state else "DISABLED"
        await ctx.respond(f"🔄 Autoplay has been **{status_text}** for this server.")

    # ==========================================================================
    # 21. /lyrics [song]
    # ==========================================================================
    @slash_command(name="lyrics", description="📜 Fetch lyrics for currently playing song or specified query")
    async def lyrics(
        self,
        ctx: discord.ApplicationContext,
        song: Option(str, "Song title and artist (optional)", required=False, default=None)
    ):
        await ctx.defer()
        query = song
        if not query:
            player: Optional[wavelink.Player] = ctx.voice_client
            if player and player.current:
                clean_title = re.sub(r"\(.*?\)|\[.*?\]|official|video|audio|lyrics", "", player.current.title, flags=re.IGNORECASE)
                query = f"{clean_title.strip()} {getattr(player.current, 'author', '')}".strip()
            else:
                return await ctx.followup.send("❌ No song playing. Please specify a song name: `/lyrics Bohemian Rhapsody`")

        async with aiohttp.ClientSession() as session:
            try:
                url = f"https://lrclib.net/api/search?q={urllib.parse.quote(query)}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and isinstance(data, list):
                            hit = data[0]
                            lyrics_text = hit.get("plainLyrics") or hit.get("syncedLyrics")
                            if lyrics_text:
                                embed = discord.Embed(
                                    title=f"📜 {hit.get('trackName', query)}",
                                    description=lyrics_text[:4000],
                                    color=HEX_DEMON_PURPLE
                                )
                                embed.set_author(name=hit.get("artistName", "Unknown Artist"))
                                embed.set_footer(text="Lyrics provided by lrclib.net")
                                return await ctx.followup.send(embed=embed)
            except Exception as e:
                logger.error(f"Error fetching lyrics: {e}")

        await ctx.followup.send(f"❌ Could not find lyrics for: **{query}**")


def setup(bot: commands.Bot):
    bot.add_cog(MusicCog(bot))
