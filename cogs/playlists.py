"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/playlists.py (All 12 Custom Playlist Slash Commands)
================================================================================
"""

import io
import json
import logging
import random
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import wavelink

from config import HEX_DEMON_PURPLE, HEX_DEMON_ACCENT, HEX_DEMON_RED
from database import db_manager
from utils.luxury_ui import format_ms

logger = logging.getLogger("demon.playlists")


class PlaylistsCog(commands.Cog, name="Playlists"):
    """All 12 Custom Playlist Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------------------------------------------------------
    # 1. /pl-create [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-create", description="📁 Create a new custom personal playlist")
    async def pl_create(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of the new playlist", required=True)
    ):
        success = await db_manager.create_playlist(ctx.author.id, name)
        if success:
            await ctx.respond(f"✅ Created custom playlist: **{name}**")
        else:
            await ctx.respond(f"❌ A playlist named **{name}** already exists in your library.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 2. /pl-delete [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-delete", description="🗑️ Delete a personal playlist")
    async def pl_delete(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of the playlist to delete", required=True)
    ):
        deleted = await db_manager.delete_playlist(ctx.author.id, name)
        if deleted:
            await ctx.respond(f"🗑️ Deleted playlist: **{name}**")
        else:
            await ctx.respond(f"❌ Playlist **{name}** not found.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 3. /pl-list
    # --------------------------------------------------------------------------
    @slash_command(name="pl-list", description="📋 List all your personal custom playlists")
    async def pl_list(self, ctx: discord.ApplicationContext):
        playlists = await db_manager.get_user_playlists(ctx.author.id)
        if not playlists:
            return await ctx.respond("📭 You don't have any custom playlists yet. Create one with `/pl-create <name>`.", ephemeral=True)

        embed = discord.Embed(
            title=f"📋 Playlists for {ctx.author.display_name}",
            color=HEX_DEMON_PURPLE
        )
        lines = []
        for p in playlists:
            created = str(p["created_at"])[:10]
            lines.append(f"• **{p['name']}** — `{p['track_count']} songs` (Created: {created})")

        embed.description = "\n".join(lines)
        embed.set_footer(text="Play any playlist with: /pl-play <name>")
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 4. /pl-info [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-info", description="🔍 View tracks and playtime in a playlist")
    async def pl_info(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of the playlist", required=True)
    ):
        pl = await db_manager.get_playlist(ctx.author.id, name)
        if not pl:
            return await ctx.respond(f"❌ Playlist **{name}** was not found.", ephemeral=True)

        tracks = pl["tracks"]
        total_ms = sum(t.get("duration", 0) for t in tracks)

        embed = discord.Embed(
            title=f"📁 Playlist: {pl['name']}",
            description=f"Total Songs: **{len(tracks)}** | Total Duration: **{format_ms(total_ms)}**",
            color=HEX_DEMON_PURPLE
        )

        lines = []
        for i, t in enumerate(tracks[:20], 1):
            dur = format_ms(t.get("duration", 0))
            lines.append(f"`#{i:02d}` **{t.get('title', 'Unknown')}** — `{dur}` ({t.get('author', 'Unknown')})")

        if len(tracks) > 20:
            lines.append(f"_...and {len(tracks) - 20} more tracks_")

        embed.add_field(name="Tracks", value="\n".join(lines) if lines else "_Playlist is empty._", inline=False)
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 5. /pl-play [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-play", description="▶️ Load and play a custom playlist")
    async def pl_play(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of playlist to play", required=True)
    ):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)

        pl = await db_manager.get_playlist(ctx.author.id, name)
        if not pl or not pl["tracks"]:
            return await ctx.respond(f"❌ Playlist **{name}** does not exist or has no songs.", ephemeral=True)

        await ctx.defer()
        target_vc = ctx.author.voice.channel
        player: Optional[wavelink.Player] = ctx.voice_client

        if not player or not player.connected:
            player = await target_vc.connect(cls=wavelink.Player, timeout=15)
        player.text_channel = ctx.channel

        tracks_data = pl["tracks"]
        queued_count = 0

        for t_info in tracks_data:
            uri = t_info.get("uri") or f"{t_info.get('title')} {t_info.get('author')}"
            try:
                res = await wavelink.Playable.search(uri)
                if res:
                    track = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                    track.requester_id = ctx.author.id
                    track.requester_name = ctx.author.display_name
                    if not player.playing and queued_count == 0:
                        await player.play(track)
                    else:
                        await player.queue.put_wait(track)
                    queued_count += 1
            except Exception as e:
                logger.warning(f"Failed to queue playlist track: {e}")

        await ctx.followup.send(f"▶️ Loaded and queued **{queued_count} songs** from playlist **{name}**!")

    # --------------------------------------------------------------------------
    # 6. /pl-playshuffle [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-playshuffle", description="🔀 Load and play a custom playlist shuffled")
    async def pl_playshuffle(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Name of playlist to play shuffled", required=True)
    ):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)

        pl = await db_manager.get_playlist(ctx.author.id, name)
        if not pl or not pl["tracks"]:
            return await ctx.respond(f"❌ Playlist **{name}** does not exist or has no songs.", ephemeral=True)

        await ctx.defer()
        target_vc = ctx.author.voice.channel
        player: Optional[wavelink.Player] = ctx.voice_client

        if not player or not player.connected:
            player = await target_vc.connect(cls=wavelink.Player, timeout=15)
        player.text_channel = ctx.channel

        tracks_data = list(pl["tracks"])
        random.shuffle(tracks_data)
        queued_count = 0

        for t_info in tracks_data:
            uri = t_info.get("uri") or f"{t_info.get('title')} {t_info.get('author')}"
            try:
                res = await wavelink.Playable.search(uri)
                if res:
                    track = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                    track.requester_id = ctx.author.id
                    track.requester_name = ctx.author.display_name
                    if not player.playing and queued_count == 0:
                        await player.play(track)
                    else:
                        await player.queue.put_wait(track)
                    queued_count += 1
            except Exception as e:
                logger.warning(f"Failed to queue track: {e}")

        await ctx.followup.send(f"🔀 Shuffled and queued **{queued_count} songs** from playlist **{name}**!")

    # --------------------------------------------------------------------------
    # 7. /pl-savecurrent [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-savecurrent", description="💾 Save currently playing song to a custom playlist")
    async def pl_savecurrent(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Playlist name to save to", required=True)
    ):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or not player.current:
            return await ctx.respond("❌ Nothing is currently playing.", ephemeral=True)

        track = player.current
        track_dict = {
            "title": track.title,
            "author": getattr(track, "author", "Unknown"),
            "uri": getattr(track, "uri", ""),
            "duration": getattr(track, "length", 0)
        }

        success = await db_manager.add_track_to_playlist(ctx.author.id, name, track_dict)
        if success:
            await ctx.respond(f"💾 Added **{track.title}** to playlist **{name}**!")
        else:
            await ctx.respond(f"❌ Playlist **{name}** was not found. Create it first using `/pl-create {name}`.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 8. /pl-savequeue [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-savequeue", description="💾 Save the entire current queue into a custom playlist")
    async def pl_savequeue(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Playlist name to save queue to", required=True)
    ):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or (not player.current and player.queue.is_empty):
            return await ctx.respond("❌ No active tracks or queue to save.", ephemeral=True)

        tracks_to_add = []
        if player.current:
            tracks_to_add.append({
                "title": player.current.title,
                "author": getattr(player.current, "author", "Unknown"),
                "uri": getattr(player.current, "uri", ""),
                "duration": getattr(player.current, "length", 0)
            })
        for t in player.queue:
            tracks_to_add.append({
                "title": t.title,
                "author": getattr(t, "author", "Unknown"),
                "uri": getattr(t, "uri", ""),
                "duration": getattr(t, "length", 0)
            })

        success, added_count = await db_manager.add_tracks_to_playlist(ctx.author.id, name, tracks_to_add)
        if success:
            await ctx.respond(f"💾 Added **{added_count} tracks** from queue into playlist **{name}**!")
        else:
            await ctx.respond(f"❌ Playlist **{name}** not found. Create it first with `/pl-create {name}`.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 9. /pl-removetrack [name] [track_number]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-removetrack", description="❌ Remove a track by its position from a saved playlist")
    async def pl_removetrack(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Playlist name", required=True),
        track_number: Option(int, "Track number to remove", required=True, min_value=1)
    ):
        removed = await db_manager.remove_track_from_playlist(ctx.author.id, name, track_number)
        if removed:
            await ctx.respond(f"🗑️ Removed #{track_number} **{removed.get('title', 'Track')}** from playlist **{name}**.")
        else:
            await ctx.respond(f"❌ Could not remove track #{track_number} from **{name}**. Check `/pl-info {name}`.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 10. /pl-removeduplicate [name]
    # --------------------------------------------------------------------------
    @slash_command(name="pl-removeduplicate", description="🧹 Remove duplicate tracks from a custom playlist")
    async def pl_removeduplicate(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, "Playlist name to deduplicate", required=True)
    ):
        count = await db_manager.remove_duplicates_from_playlist(ctx.author.id, name)
        if count > 0:
            await ctx.respond(f"🧹 Removed **{count} duplicate tracks** from playlist **{name}**.")
        else:
            await ctx.respond(f"✨ No duplicate songs found in playlist **{name}**.")

    # --------------------------------------------------------------------------
    # 11. /sp-play [spotify_link]
    # --------------------------------------------------------------------------
    @slash_command(name="sp-play", description="🟢 Play a Spotify playlist, album, or track link directly")
    async def sp_play(
        self,
        ctx: discord.ApplicationContext,
        spotify_link: Option(str, "Spotify URL (Track, Album, or Playlist)", required=True)
    ):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)

        await ctx.defer()
        target_vc = ctx.author.voice.channel
        player: Optional[wavelink.Player] = ctx.voice_client

        if not player or not player.connected:
            player = await target_vc.connect(cls=wavelink.Player, timeout=15)
        player.text_channel = ctx.channel

        try:
            results = await wavelink.Playable.search(spotify_link.strip())
            if not results:
                return await ctx.followup.send("❌ Could not resolve Spotify link. Ensure it is public.")

            if isinstance(results, wavelink.Playlist):
                for t in results.tracks:
                    t.requester_id = ctx.author.id
                    t.requester_name = ctx.author.display_name
                if not player.playing:
                    first = results.tracks[0]
                    for t in results.tracks[1:]:
                        await player.queue.put_wait(t)
                    await player.play(first)
                else:
                    for t in results.tracks:
                        await player.queue.put_wait(t)
                await ctx.followup.send(f"🟢 Loaded **{len(results.tracks)} tracks** from Spotify collection: **{results.name}**")
            else:
                track = results[0]
                track.requester_id = ctx.author.id
                track.requester_name = ctx.author.display_name
                if not player.playing:
                    await player.play(track)
                else:
                    await player.queue.put_wait(track)
                await ctx.followup.send(f"🟢 Loaded Spotify track: **{track.title}**")
        except Exception as e:
            logger.error(f"Spotify play error: {e}")
            await ctx.followup.send(f"❌ Error loading Spotify link: `{e}`")

    # --------------------------------------------------------------------------
    # 12. /sp-savequeue
    # --------------------------------------------------------------------------
    @slash_command(name="sp-savequeue", description="📤 Export current queue into a downloadable JSON/text file")
    async def sp_savequeue(self, ctx: discord.ApplicationContext):
        player: Optional[wavelink.Player] = ctx.voice_client
        if not player or (not player.current and player.queue.is_empty):
            return await ctx.respond("❌ No active queue to export.", ephemeral=True)

        data = {
            "guild": ctx.guild.name,
            "exported_by": ctx.author.display_name,
            "current_track": {
                "title": player.current.title if player.current else None,
                "author": getattr(player.current, "author", None),
                "uri": getattr(player.current, "uri", None),
                "duration_ms": getattr(player.current, "length", 0)
            } if player.current else None,
            "queue": [
                {
                    "title": t.title,
                    "author": getattr(t, "author", "Unknown"),
                    "uri": getattr(t, "uri", ""),
                    "duration_ms": getattr(t, "length", 0)
                } for t in player.queue
            ]
        }

        json_bytes = json.dumps(data, indent=2).encode("utf-8")
        file = discord.File(io.BytesIO(json_bytes), filename="queue_export.json")
        await ctx.respond("📤 **Current queue exported successfully:**", file=file)


def setup(bot: commands.Bot):
    bot.add_cog(PlaylistsCog(bot))
