"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/audio.py (Wavelink 3.x Music Engine: Dual Slash & Prefix)
================================================================================
"""

import asyncio
import logging
import re
import urllib.parse
from typing import Optional, Dict, Any, List
import aiohttp
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import wavelink

from config import (
    HEX_VIOLET,
    HEX_ICE_BLUE,
    HEX_EMERALD,
    HEX_ROSE,
)
from database import db_manager
from utils.luxury_ui import (
    LuxuryEmbedBuilder,
    MusicControlView,
    format_ms,
)

logger = logging.getLogger("kushida.audio")


class Audio(commands.Cog):
    """
    Music Commands cog for Kushida.
    Features: play, skip, stop, pause, resume, queue, nowplaying, volume,
              shuffle, loop, clearqueue, lyrics (both Slash and Prefix).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.history: Dict[int, List[wavelink.Playable]] = {}
        self._view: Optional[MusicControlView] = None

    @property
    def persistent_view(self) -> MusicControlView:
        """Lazy instantiation of persistent view inside running event loop."""
        if self._view is None:
            self._view = MusicControlView()
        return self._view

    # --------------------------------------------------------------------------
    # WAVELINK EVENT LISTENERS
    # --------------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        """Fired when Lavalink node connects and is ready."""
        logger.info(f"Lavalink Node '{payload.node.identifier}' is READY! (Resumed: {payload.resumed})")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        """Triggered on track start. Logs to DB and refreshes persistent control panel."""
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

        # Log to async SQLite database
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
        """Triggered when track ends. Automatically advances queue if needed."""
        player: wavelink.Player = payload.player
        logger.debug(f"Track '{payload.track.title}' finished with reason: {payload.reason}")

        if player and not player.queue.is_empty and not player.playing:
            try:
                next_track = player.queue.get()
                await player.play(next_track)
            except Exception as e:
                logger.error(f"Error auto-advancing track: {e}")
        elif player and player.queue.is_empty:
            # Check 24/7 setting before ever disconnecting
            is_247 = await db_manager.get_guild_247(player.guild.id)
            if not is_247:
                logger.info(f"Queue ended in guild {player.guild.id}. 24/7 is disabled.")

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
    # PERSISTENT PANEL MANAGER
    # --------------------------------------------------------------------------
    async def _render_or_update_panel(self, player: wavelink.Player, track: wavelink.Playable) -> None:
        """Updates the existing control embed in-place or creates a new one cleanly."""
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
            view = self.persistent_view

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
                new_msg = await target_channel.send(embed=embed, view=view)
                await db_manager.set_panel_message_id(guild.id, target_channel.id, new_msg.id)

        except Exception as e:
            logger.error(f"Error rendering persistent panel in guild {player.guild.id}: {e}")

    async def play_previous_track(self, guild_id: int) -> bool:
        """Pops and replays the previous track from history."""
        guild = self.bot.get_guild(guild_id)
        if not guild or not guild.voice_client:
            return False

        player: wavelink.Player = guild.voice_client
        guild_history = self.history.get(guild_id, [])

        if len(guild_history) < 2:
            return False

        guild_history.pop()  # Remove current
        prev_track = guild_history.pop()  # Get previous
        await player.play(prev_track)
        return True

    # --------------------------------------------------------------------------
    # 1. PLAY (Slash: /play | Prefix: -play, -p)
    # --------------------------------------------------------------------------
    async def _do_play(self, ctx, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            msg = "❌ You must be connected to a voice channel first!"
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.defer()

        # Connect or get player
        player: wavelink.Player
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            player = ctx.voice_client

        player.text_channel = ctx.channel

        # Search tracks
        search_results: wavelink.Search = await wavelink.Playable.search(query)
        if not search_results:
            err = f"❌ No audio results found for `{query}`."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(err, ephemeral=True)
            else:
                await ctx.send(err)
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
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(embed=embed)
            else:
                await ctx.send(embed=embed)
        else:
            track: wavelink.Playable = search_results[0]
            setattr(track, "requester_id", ctx.author.id)
            await player.queue.put_wait(track)

            if not player.playing:
                msg = f"🎵 Starting playback for **{track.title}**..."
                if isinstance(ctx, discord.ApplicationContext):
                    await ctx.respond(msg)
                else:
                    await ctx.send(msg)
            else:
                embed = discord.Embed(
                    title="➕ Track Queued",
                    description=f"Added **{track.title}** to the queue.\n`{getattr(track, 'author', 'Unknown')}` • `{format_ms(getattr(track, 'length', 0))}`",
                    color=HEX_ICE_BLUE
                )
                if getattr(track, "artwork_url", None):
                    embed.set_thumbnail(url=track.artwork_url)
                if isinstance(ctx, discord.ApplicationContext):
                    await ctx.respond(embed=embed)
                else:
                    await ctx.send(embed=embed)

        if not player.playing and not player.queue.is_empty:
            if player.paused:
                await player.pause(False)
            next_track = player.queue.get()
            await player.play(next_track)

    @slash_command(name="play", description="Gaana chalane ke liye (Song ka naam ya link dalein).")
    async def play_slash(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Song title, artist name, YouTube or Spotify link", required=True)
    ):
        await self._do_play(ctx, query)

    @commands.command(name="play", aliases=["p"], help="Gaana chalayein.")
    async def play_prefix(self, ctx: commands.Context, *, query: str = None):
        if not query:
            await ctx.send("❌ Please provide a song name or link! Example: `-play despacito`")
            return
        await self._do_play(ctx, query)

    # --------------------------------------------------------------------------
    # 2. SKIP (Slash: /skip | Prefix: -skip, -s)
    # --------------------------------------------------------------------------
    async def _do_skip(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.playing:
            msg = "❌ Nothing is currently playing to skip."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        await player.skip()
        msg = "⏭️ Skipped current track."
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="skip", description="Current chal rahe gaane ko skip karne ke liye.")
    async def skip_slash(self, ctx: discord.ApplicationContext):
        await self._do_skip(ctx)

    @commands.command(name="skip", aliases=["s"], help="Current gaane ko skip karein.")
    async def skip_prefix(self, ctx: commands.Context):
        await self._do_skip(ctx)

    # --------------------------------------------------------------------------
    # 3. STOP (Slash: /stop | Prefix: -stop)
    # --------------------------------------------------------------------------
    async def _do_stop(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            msg = "❌ Bot is not connected to a voice channel."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        player.queue.clear()
        await player.disconnect()
        msg = "⏹️ Music stopped, queue cleared, and bot disconnected."
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="stop", description="Music band karne aur poori queue delete karne ke liye.")
    async def stop_slash(self, ctx: discord.ApplicationContext):
        await self._do_stop(ctx)

    @commands.command(name="stop", help="Music band karein aur queue clear karein.")
    async def stop_prefix(self, ctx: commands.Context):
        await self._do_stop(ctx)

    # --------------------------------------------------------------------------
    # 4. PAUSE (Slash: /pause | Prefix: -pause)
    # --------------------------------------------------------------------------
    async def _do_pause(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected or not player.playing:
            msg = "❌ Nothing is currently playing."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        if player.paused:
            msg = "⏸️ Playback is already paused. Use `/resume` or `-resume` to continue."
        else:
            await player.pause(True)
            msg = "⏸️ Paused playback."

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="pause", description="Gaane ko kuch der rokne (pause) ke liye.")
    async def pause_slash(self, ctx: discord.ApplicationContext):
        await self._do_pause(ctx)

    @commands.command(name="pause", help="Gaane ko pause karein.")
    async def pause_prefix(self, ctx: commands.Context):
        await self._do_pause(ctx)

    # --------------------------------------------------------------------------
    # 5. RESUME (Slash: /resume | Prefix: -resume, -r)
    # --------------------------------------------------------------------------
    async def _do_resume(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            msg = "❌ Bot is not connected to a voice channel."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        if not player.paused:
            msg = "▶️ Playback is already running."
        else:
            await player.pause(False)
            msg = "▶️ Resumed playback."

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="resume", description="Pause kiye gaye gaane ko fir se chalu karne ke liye.")
    async def resume_slash(self, ctx: discord.ApplicationContext):
        await self._do_resume(ctx)

    @commands.command(name="resume", aliases=["r"], help="Paused gaana chalu karein.")
    async def resume_prefix(self, ctx: commands.Context):
        await self._do_resume(ctx)

    # --------------------------------------------------------------------------
    # 6. QUEUE (Slash: /queue | Prefix: -queue, -q)
    # --------------------------------------------------------------------------
    async def _do_queue(self, ctx, page: int = 1):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            msg = "❌ The queue is completely empty."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        embed = LuxuryEmbedBuilder.queue_embed(player, page=page)
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="queue", description="Line mein lage aage ke sabhi gaano ki list dekhne ke liye.")
    async def queue_slash(
        self,
        ctx: discord.ApplicationContext,
        page: Option(int, "Page number", default=1, min_value=1, required=False)
    ):
        await self._do_queue(ctx, page)

    @commands.command(name="queue", aliases=["q"], help="Upcoming gaano ki list dekhein.")
    async def queue_prefix(self, ctx: commands.Context, page: int = 1):
        await self._do_queue(ctx, page)

    # --------------------------------------------------------------------------
    # 7. NOWPLAYING (Slash: /nowplaying | Prefix: -nowplaying, -np)
    # --------------------------------------------------------------------------
    async def _do_nowplaying(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            msg = "❌ Nothing is currently playing."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        player.text_channel = ctx.channel
        embed = LuxuryEmbedBuilder.now_playing(player, player.current, requested_by=ctx.author)
        view = self.persistent_view

        if isinstance(ctx, discord.ApplicationContext):
            msg_obj = await ctx.respond(embed=embed, view=view)
        else:
            msg_obj = await ctx.send(embed=embed, view=view)

        if hasattr(msg_obj, "id"):
            await db_manager.set_panel_message_id(ctx.guild.id, ctx.channel.id, msg_obj.id)

    @slash_command(name="nowplaying", description="Abhi kaun sa gaana chal raha hai, uski details dekhne ke liye.")
    async def nowplaying_slash(self, ctx: discord.ApplicationContext):
        await self._do_nowplaying(ctx)

    @commands.command(name="nowplaying", aliases=["np"], help="Current gaane ki details dekhein.")
    async def nowplaying_prefix(self, ctx: commands.Context):
        await self._do_nowplaying(ctx)

    # --------------------------------------------------------------------------
    # 8. VOLUME (Slash: /volume | Prefix: -volume, -v)
    # --------------------------------------------------------------------------
    async def _do_volume(self, ctx, volume: int):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            msg = "❌ Bot is not in a voice channel."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        vol_clamped = max(0, min(200, volume))
        await player.set_volume(vol_clamped)
        msg = f"🔊 Volume set to **{vol_clamped}%**."
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="volume", description="Bot ki aawaz kam ya tez karne ke liye (e.g., /volume 50).")
    async def volume_slash(
        self,
        ctx: discord.ApplicationContext,
        volume: Option(int, "Volume level (0-200)", min_value=0, max_value=200, required=True)
    ):
        await self._do_volume(ctx, volume)

    @commands.command(name="volume", aliases=["v"], help="Volume kam ya tez karein (e.g., -v 50).")
    async def volume_prefix(self, ctx: commands.Context, volume: int = None):
        if volume is None:
            player: Optional[wavelink.Player] = ctx.voice_client
            curr = player.volume if player else 100
            await ctx.send(f"🔊 Current volume is **{curr}%**. Use `-v <0-200>` to change it.")
            return
        await self._do_volume(ctx, volume)

    # --------------------------------------------------------------------------
    # 9. SHUFFLE (Slash: /shuffle | Prefix: -shuffle)
    # --------------------------------------------------------------------------
    async def _do_shuffle(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or len(player.queue) < 2:
            msg = "❌ Need at least 2 tracks in queue to shuffle."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        player.queue.shuffle()
        msg = f"🔀 Shuffled **{len(player.queue)}** upcoming tracks."
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="shuffle", description="Queue ke gaano ko aage-piche (mix) karne ke liye.")
    async def shuffle_slash(self, ctx: discord.ApplicationContext):
        await self._do_shuffle(ctx)

    @commands.command(name="shuffle", help="Queue ko mix karein.")
    async def shuffle_prefix(self, ctx: commands.Context):
        await self._do_shuffle(ctx)

    # --------------------------------------------------------------------------
    # 10. LOOP (Slash: /loop | Prefix: -loop)
    # --------------------------------------------------------------------------
    async def _do_loop(self, ctx, mode: Optional[str] = None):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.connected:
            msg = "❌ Bot is not in a voice channel."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        curr_mode = getattr(player.queue, "mode", wavelink.QueueMode.normal)
        if mode:
            m = mode.lower().strip()
            if m in ["track", "song", "1"]:
                player.queue.mode = wavelink.QueueMode.loop
                status = "🔂 **Track Loop** (Current song repeat)"
            elif m in ["queue", "all"]:
                player.queue.mode = wavelink.QueueMode.loop_all
                status = "🔁 **Queue Loop** (Entire queue repeat)"
            else:
                player.queue.mode = wavelink.QueueMode.normal
                status = "➡️ **Loop Disabled** (Normal playback)"
        else:
            # Cycle loop mode
            if curr_mode == wavelink.QueueMode.normal:
                player.queue.mode = wavelink.QueueMode.loop
                status = "🔂 **Track Loop** (Current song repeat)"
            elif curr_mode == wavelink.QueueMode.loop:
                player.queue.mode = wavelink.QueueMode.loop_all
                status = "🔁 **Queue Loop** (Entire queue repeat)"
            else:
                player.queue.mode = wavelink.QueueMode.normal
                status = "➡️ **Loop Disabled** (Normal playback)"

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(f"🔁 Loop Mode: {status}")
        else:
            await ctx.send(f"🔁 Loop Mode: {status}")

    @slash_command(name="loop", description="Current gaane ya poori queue ko repeat par lagane ke liye.")
    async def loop_slash(
        self,
        ctx: discord.ApplicationContext,
        mode: Option(str, "Loop mode: off, track, queue", choices=["off", "track", "queue"], required=False, default=None)
    ):
        await self._do_loop(ctx, mode)

    @commands.command(name="loop", help="Song ya queue repeat karein.")
    async def loop_prefix(self, ctx: commands.Context, mode: str = None):
        await self._do_loop(ctx, mode)

    # --------------------------------------------------------------------------
    # 11. CLEARQUEUE (Slash: /clearqueue | Prefix: -clearqueue, -cq)
    # --------------------------------------------------------------------------
    async def _do_clearqueue(self, ctx):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or player.queue.is_empty:
            msg = "❌ The queue is already empty."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        count = len(player.queue)
        player.queue.clear()
        msg = f"🗑️ Cleared **{count} tracks** from the queue. Currently playing song was not stopped."
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(msg)
        else:
            await ctx.send(msg)

    @slash_command(name="clearqueue", description="Bina song roke, aage ke saare gaane list se hatane ke liye.")
    async def clearqueue_slash(self, ctx: discord.ApplicationContext):
        await self._do_clearqueue(ctx)

    @commands.command(name="clearqueue", aliases=["cq"], help="Aage ki saari queue clear karein.")
    async def clearqueue_prefix(self, ctx: commands.Context):
        await self._do_clearqueue(ctx)

    # --------------------------------------------------------------------------
    # 12. LYRICS (Slash: /lyrics | Prefix: -lyrics, -ly)
    # --------------------------------------------------------------------------
    async def _fetch_lyrics(self, query: str) -> Optional[Dict[str, str]]:
        """Query LRCLIB free lyrics API."""
        clean = re.sub(r'[\(\[].*?[\)\]]', '', query).strip()
        encoded = urllib.parse.quote(clean)
        url = f"https://lrclib.net/api/search?q={encoded}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"User-Agent": "Kushida/2.0"}, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and isinstance(data, list) and len(data) > 0:
                            item = data[0]
                            lyrics_text = item.get("plainLyrics") or item.get("syncedLyrics")
                            if lyrics_text:
                                return {
                                    "title": item.get("trackName", clean),
                                    "artist": item.get("artistName", "Unknown"),
                                    "lyrics": lyrics_text
                                }
        except Exception as e:
            logger.error(f"Error fetching lyrics for '{clean}': {e}")
        return None

    async def _do_lyrics(self, ctx, query: Optional[str] = None):
        player: Optional[wavelink.Player] = ctx.voice_client

        search_term = query
        if not search_term:
            if player and player.current:
                clean_title = re.sub(r'[\(\[].*?[\)\]]', '', player.current.title).strip()
                search_term = f"{clean_title} {getattr(player.current, 'author', '')}".strip()
            else:
                msg = "❌ No song is currently playing. Please specify a song name! (e.g. `/lyrics believer`)"
                if isinstance(ctx, discord.ApplicationContext):
                    await ctx.respond(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.defer()

        result = await self._fetch_lyrics(search_term)
        if not result:
            err = f"❌ Could not find lyrics for **{search_term}**."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(err)
            else:
                await ctx.send(err)
            return

        lyrics_text = result["lyrics"]
        if len(lyrics_text) > 3900:
            lyrics_text = lyrics_text[:3900] + "\n\n...[Lyrics truncated]..."

        embed = discord.Embed(
            title=f"📜 Lyrics — {result['title']}",
            description=lyrics_text,
            color=HEX_VIOLET
        )
        embed.set_footer(text=f"Artist: {result['artist']} • Kushida Luxury Sound")

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="lyrics", description="Chal rahe gaane ke lyrics (bol) screen par dekhne ke liye.")
    async def lyrics_slash(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Song title (optional, defaults to now playing song)", required=False, default=None)
    ):
        await self._do_lyrics(ctx, query)

    @commands.command(name="lyrics", aliases=["ly"], help="Gaane ke lyrics dekhein.")
    async def lyrics_prefix(self, ctx: commands.Context, *, query: str = None):
        await self._do_lyrics(ctx, query)


def setup(bot: commands.Bot):
    """Cog loader for Pycord."""
    bot.add_cog(Audio(bot))
