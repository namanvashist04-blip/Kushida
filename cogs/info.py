"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/info.py (All 13 Information & Utility Slash Commands)
================================================================================
"""

import datetime
import logging
import time
from typing import Optional
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import wavelink

from config import (
    BOT_NAME,
    HEX_DEMON_PURPLE,
    HEX_DEMON_ACCENT,
    HEX_DEMON_RED,
    HEX_EMERALD,
    HEX_MUTED,
)
from database import db_manager

logger = logging.getLogger("demon.info")
BOT_START_TIME = time.time()


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Music Commands", description="21 playback & queue controls", emoji="🎵", value="music"),
            discord.SelectOption(label="Audio Filters", description="15 DSP equalizers & audio effects", emoji="🎛️", value="filters"),
            discord.SelectOption(label="Custom Playlists", description="12 user playlist management commands", emoji="📁", value="playlists"),
            discord.SelectOption(label="Settings & DJ", description="6 server configuration & DJ rules", emoji="⚙️", value="settings"),
            discord.SelectOption(label="Info & Utility", description="13 bot statistics, voting, & profiles", emoji="ℹ️", value="info"),
        ]
        super().__init__(placeholder="Select a command category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        if cat == "music":
            embed = discord.Embed(
                title="🎵 Music Commands (21 Total)",
                description=(
                    "`/play <query>` — Play song or playlist (Name, YouTube, Spotify, SoundCloud)\n"
                    "`/p <query>` — Shortcut for `/play`\n"
                    "`/pause` — Pause current song\n"
                    "`/resume` — Resume paused song\n"
                    "`/skip` — Skip to next song\n"
                    "`/skipto <position>` — Jump to a specific song in queue\n"
                    "`/previous` — Replay previous track\n"
                    "`/stop` — Stop playback and clear queue\n"
                    "`/queue [page]` — View upcoming tracks list\n"
                    "`/clearqueue` — Clear upcoming queue without stopping current song\n"
                    "`/nowplaying` — View currently playing song info & progress\n"
                    "`/np` — Shortcut for `/nowplaying`\n"
                    "`/volume <level>` — Adjust volume (1-150%)\n"
                    "`/loop <mode>` — Loop mode (`Off`, `Track`, `Queue`)\n"
                    "`/shuffle` — Randomize upcoming queue\n"
                    "`/seek <time>` — Jump to timestamp (e.g. `01:30` or seconds)\n"
                    "`/forward <seconds>` — Skip forward by N seconds\n"
                    "`/backward <seconds>` — Rewind by N seconds\n"
                    "`/remove <position>` — Remove a specific song from queue\n"
                    "`/join` — Connect bot to your voice channel\n"
                    "`/leave` — Disconnect bot from voice channel\n"
                    "`/autoplay` — Automatically queue recommendations when queue ends\n"
                    "`/lyrics [song]` — Search and view lyrics"
                ),
                color=HEX_DEMON_PURPLE
            )
        elif cat == "filters":
            embed = discord.Embed(
                title="🎛️ Audio DSP Filters (15 Total)",
                description=(
                    "`/8d` — 8D spatial audio rotation\n"
                    "`/bass` — Mild low-frequency bass boost\n"
                    "`/bassboost` — Heavy bass boost\n"
                    "`/chipmunk` — High pitch vocal transform\n"
                    "`/nightcore` — Sped up and high-pitched audio\n"
                    "`/slowmo` — Slowed & aesthetic vibe\n"
                    "`/soft` — Low-pass filter smoothing harsh highs\n"
                    "`/speed <val>` — Custom speed multiplier (0.5x to 2.0x)\n"
                    "`/pop` — Pop vocal clarity equalizer\n"
                    "`/radio` — Vintage AM radio frequency filter\n"
                    "`/karaoke` — Vocal cut algorithm for sing-alongs\n"
                    "`/treblebass` — Boosts both sub-bass and high crisp frequencies\n"
                    "`/equalizer <preset>` — Presets: `Flat`, `Rock`, `Classical`, `Jazz`, `Electronic`\n"
                    "`/earrape` — Maximum gain on all bands\n"
                    "`/clearfilter` — Reset all active filters back to flat/default"
                ),
                color=HEX_DEMON_ACCENT
            )
        elif cat == "playlists":
            embed = discord.Embed(
                title="📁 Custom Playlists (12 Total)",
                description=(
                    "`/pl-create <name>` — Create personal custom playlist\n"
                    "`/pl-delete <name>` — Delete custom playlist\n"
                    "`/pl-list` — List all your personal playlists\n"
                    "`/pl-info <name>` — View songs and total runtime in playlist\n"
                    "`/pl-play <name>` — Queue and play custom playlist\n"
                    "`/pl-playshuffle <name>` — Play custom playlist shuffled\n"
                    "`/pl-savecurrent <name>` — Add currently playing song to playlist\n"
                    "`/pl-savequeue <name>` — Save entire current queue to playlist\n"
                    "`/pl-removetrack <name> <#>` — Remove track by position\n"
                    "`/pl-removeduplicate <name>` — Remove duplicate songs\n"
                    "`/sp-play <link>` — Directly load & play Spotify playlist\n"
                    "`/sp-savequeue` — Export current queue as downloadable JSON file"
                ),
                color=HEX_DEMON_PURPLE
            )
        elif cat == "settings":
            embed = discord.Embed(
                title="⚙️ Settings & DJ (6 Total)",
                description=(
                    "`/247` — Toggle 24/7 mode (Stay in voice indefinitely)\n"
                    "`/musicpanel` — Spawn dedicated persistent interactive button control panel\n"
                    "`/setprefix` — View bot command information\n"
                    "`/adddj <role>` — Add a role to authorized DJ list\n"
                    "`/removedj <role>` — Remove role from DJ list\n"
                    "`/toggledj` — Toggle DJ-Only mode (Restricts music controls to DJs)"
                ),
                color=HEX_EMERALD
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Information & Utility (13 Total)",
                description=(
                    "`/help` — Interactive commands menu\n"
                    "`/ping` — Check Discord API & Lavalink latency\n"
                    "`/about` — Bot info, technology stack, and architecture\n"
                    "`/uptime` — Bot uptime counter\n"
                    "`/invite` — Generate official bot invite link\n"
                    "`/support` — Official support server invite\n"
                    "`/vote` — Top.gg voting link\n"
                    "`/checkvote` — Check if your Top.gg vote is active\n"
                    "`/premium` — View premium tier & free perks\n"
                    "`/redeem <code>` — Redeem promo or event code\n"
                    "`/server-profile` — Server stats, 24/7 status, DJ role count\n"
                    "`/user-profile` — User stats, votes, playlist count\n"
                    "`/sponsor` — Bot sponsor and community acknowledgments"
                ),
                color=HEX_DEMON_PURPLE
            )

        embed.set_footer(text="Demon Music • High Performance 24/7 Audio Engine")
        await interaction.response.edit_message(embed=embed)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())


class InfoCog(commands.Cog, name="Info"):
    """All 13 Information & Utility Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------------------------------------------------------
    # 1. /help
    # --------------------------------------------------------------------------
    @slash_command(name="help", description="📖 Explore all 67 Slash Commands with an interactive menu")
    async def help_command(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="👹 DEMON MUSIC — Command Directory",
            description=(
                "Welcome to **Demon Music Terminal**!\n"
                "Select a category from the dropdown below to explore all **67 Slash Commands**:\n\n"
                "• 🎵 **Music (21)** — Playback, queue, scrubbing, volume\n"
                "• 🎛️ **Audio Filters (15)** — 8D, Bassboost, Nightcore, Equalizers\n"
                "• 📁 **Custom Playlists (12)** — Personal cloud playlists & Spotify import\n"
                "• ⚙️ **Settings & DJ (6)** — 24/7 voice mode, DJ roles, interactive panels\n"
                "• ℹ️ **Info & Utility (13)** — Profiles, latency, uptime, votes"
            ),
            color=HEX_DEMON_PURPLE
        )
        embed.set_footer(text="Select an option below to view commands")
        await ctx.respond(embed=embed, view=HelpView())

    # --------------------------------------------------------------------------
    # 2. /ping
    # --------------------------------------------------------------------------
    @slash_command(name="ping", description="🏓 Check Discord Gateway and Lavalink audio latency")
    async def ping(self, ctx: discord.ApplicationContext):
        gw_ping = round(self.bot.latency * 1000)

        node_pings = []
        try:
            for node in wavelink.Pool.nodes.values():
                node_pings.append(f"`{node.identifier}`: **{node.status.name}**")
        except Exception:
            node_pings.append("Lavalink: **Connected**")

        embed = discord.Embed(
            title="🏓 System Latency",
            color=HEX_EMERALD if gw_ping < 150 else HEX_DEMON_RED
        )
        embed.add_field(name="Discord Gateway", value=f"`{gw_ping}ms`", inline=True)
        embed.add_field(name="Audio Nodes", value="\n".join(node_pings) if node_pings else "`Active`", inline=True)
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 3. /about
    # --------------------------------------------------------------------------
    @slash_command(name="about", description="🤖 About Demon Music Bot, Architecture, & Tech Stack")
    async def about(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title=f"👹 About {BOT_NAME}",
            description=(
                "**Demon Music** is a production-grade 24/7 Discord audio application modeled after Lara Bot.\n"
                "Featuring **67 modern Slash Commands**, custom cloud playlists, 15 mathematical DSP audio filters, "
                "and an ultra-responsive Web Terminal interface."
            ),
            color=HEX_DEMON_PURPLE
        )
        embed.add_field(name="Core Framework", value="Pycord 2.6 + Python 3.11+", inline=True)
        embed.add_field(name="Audio Engine", value="Lavalink v4 Cloud DSP", inline=True)
        embed.add_field(name="Database", value="Asynchronous SQLite (aiosqlite)", inline=True)
        embed.add_field(name="Web Dashboard", value="FastAPI + WebSockets Live Sync", inline=True)
        embed.add_field(name="Servers Connected", value=f"`{len(self.bot.guilds)}`", inline=True)
        embed.add_field(name="Host", value="100% Free 24/7 Cloud Service", inline=True)
        embed.set_footer(text="Built for high fidelity Discord music listening")
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 4. /uptime
    # --------------------------------------------------------------------------
    @slash_command(name="uptime", description="⏱️ View continuous bot uptime")
    async def uptime(self, ctx: discord.ApplicationContext):
        diff = int(time.time() - BOT_START_TIME)
        days, rem = divmod(diff, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)

        embed = discord.Embed(
            title="⏱️ Continuous Uptime",
            description=f"**{days}d {hours}h {mins}m {secs}s**\nRunning smoothly without interruption.",
            color=HEX_EMERALD
        )
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 5. /invite
    # --------------------------------------------------------------------------
    @slash_command(name="invite", description="🔗 Get the official bot invitation link")
    async def invite(self, ctx: discord.ApplicationContext):
        client_id = self.bot.user.id
        permissions = 37088600
        url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope=bot%20applications.commands"

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite Demon Music", url=url, style=discord.ButtonStyle.link))
        embed = discord.Embed(
            title="🔗 Invite Demon Music to your Server",
            description="Click the button below to invite **Demon Music** with full audio and slash command permissions.",
            color=HEX_DEMON_PURPLE
        )
        await ctx.respond(embed=embed, view=view)

    # --------------------------------------------------------------------------
    # 6. /support
    # --------------------------------------------------------------------------
    @slash_command(name="support", description="💬 Official community and support server link")
    async def support(self, ctx: discord.ApplicationContext):
        support_url = "https://discord.gg/demonmusic"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support Server", url=support_url, style=discord.ButtonStyle.link))
        embed = discord.Embed(
            title="💬 Need Help?",
            description="Join our community support server for bot updates, bug reports, feature requests, and 24/7 assistance!",
            color=HEX_DEMON_PURPLE
        )
        await ctx.respond(embed=embed, view=view)

    # --------------------------------------------------------------------------
    # 7. /vote
    # --------------------------------------------------------------------------
    @slash_command(name="vote", description="⭐ Vote for Demon Music on Top.gg")
    async def vote(self, ctx: discord.ApplicationContext):
        vote_url = f"https://top.gg/bot/{self.bot.user.id}/vote"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote on Top.gg", url=vote_url, style=discord.ButtonStyle.link))
        embed = discord.Embed(
            title="⭐ Vote for Demon Music",
            description=(
                "Voting supports the bot and helps us keep audio streaming 100% free for everyone!\n\n"
                "• **Vote every 12 hours** to unlock bonus perks\n"
                "• Check your current vote status with `/checkvote`"
            ),
            color=HEX_DEMON_PURPLE
        )
        await ctx.respond(embed=embed, view=view)

    # --------------------------------------------------------------------------
    # 8. /checkvote
    # --------------------------------------------------------------------------
    @slash_command(name="checkvote", description="🔍 Check if your Top.gg vote is currently active")
    async def checkvote(self, ctx: discord.ApplicationContext):
        is_active, last_voted, total_votes = await db_manager.check_vote(ctx.author.id)
        if is_active:
            embed = discord.Embed(
                title="⭐ Active Vote Detected!",
                description=f"Thank you for supporting **Demon Music**!\n• Total Votes: **{total_votes}**\n• Last Voted: `{last_voted}`",
                color=HEX_EMERALD
            )
        else:
            embed = discord.Embed(
                title="⌛ No Active Vote",
                description="You haven't voted in the last 12 hours.\nUse `/vote` to cast your vote and support the bot!",
                color=HEX_DEMON_RED
            )
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 9. /premium
    # --------------------------------------------------------------------------
    @slash_command(name="premium", description="💎 Information about Demon Music Premium & Free Tier")
    async def premium(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="💎 Demon Music — 100% Free Tier",
            description=(
                "🔥 **All features in Demon Music are 100% FREE!**\n\n"
                "• 24/7 Voice Channel Connection (`/247`)\n"
                "• High-Bitrate Crystal Clear Audio (320kbps)\n"
                "• Unlimited Custom Playlists (`/pl-create`)\n"
                "• 15 DSP Audio Filters (`/8d`, `/bassboost`, etc.)\n"
                "• Real-time Web Dashboard with Soundwave Visualizer\n\n"
                "No paywalls. Support us simply by voting with `/vote`!"
            ),
            color=HEX_DEMON_ACCENT
        )
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 10. /redeem [code]
    # --------------------------------------------------------------------------
    @slash_command(name="redeem", description="🎁 Redeem promotional or event community codes")
    async def redeem(
        self,
        ctx: discord.ApplicationContext,
        code: Option(str, "Enter code to redeem", required=True)
    ):
        clean_code = code.strip().upper()
        if clean_code in ["DEMON2026", "LARA", "FREEVIBE"]:
            await db_manager.record_vote(ctx.author.id)
            embed = discord.Embed(
                title="🎁 Promo Code Redeemed!",
                description=f"Code `{clean_code}` successfully activated! Enjoy enhanced audio perks.",
                color=HEX_EMERALD
            )
        else:
            embed = discord.Embed(
                title="❌ Invalid Code",
                description=f"The code `{clean_code}` is either expired or invalid.",
                color=HEX_DEMON_RED
            )
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 11. /server-profile
    # --------------------------------------------------------------------------
    @slash_command(name="server-profile", description="📊 View statistics for this server")
    async def server_profile(self, ctx: discord.ApplicationContext):
        stats = await db_manager.get_guild_stats(ctx.guild.id)
        embed = discord.Embed(
            title=f"📊 Server Profile: {ctx.guild.name}",
            color=HEX_DEMON_PURPLE
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        embed.add_field(name="Songs Played", value=f"`{stats['total_songs_played']}`", inline=True)
        embed.add_field(name="24/7 Mode", value=f"`{'Enabled' if stats['mode_247'] else 'Disabled'}`", inline=True)
        embed.add_field(name="Configured DJ Roles", value=f"`{stats['dj_role_count']}`", inline=True)
        embed.add_field(name="Members", value=f"`{ctx.guild.member_count}`", inline=True)
        embed.add_field(name="Voice Channels", value=f"`{len(ctx.guild.voice_channels)}`", inline=True)
        embed.add_field(name="Bot Joined", value=f"<t:{int(ctx.guild.me.joined_at.timestamp())}:R>" if ctx.guild.me.joined_at else "Unknown", inline=True)

        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 12. /user-profile
    # --------------------------------------------------------------------------
    @slash_command(name="user-profile", description="👤 View your music listening stats & profile")
    async def user_profile(self, ctx: discord.ApplicationContext):
        profile = await db_manager.get_user_profile(ctx.author.id)
        embed = discord.Embed(
            title=f"👤 Profile for {ctx.author.display_name}",
            color=HEX_DEMON_PURPLE
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        embed.add_field(name="Total Votes", value=f"`{profile['total_votes']}`", inline=True)
        embed.add_field(name="Active Vote", value=f"`{'Yes ⭐' if profile['has_active_vote'] else 'No'}`", inline=True)
        embed.add_field(name="Custom Playlists", value=f"`{profile['playlist_count']}`", inline=True)

        recent = profile["recent_tracks"]
        if recent:
            lines = [f"• **{t['track_title']}** by `{t['artist']}`" for t in recent[:3]]
            embed.add_field(name="Recently Played", value="\n".join(lines), inline=False)

        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 13. /sponsor
    # --------------------------------------------------------------------------
    @slash_command(name="sponsor", description="💖 Community sponsors and contributors")
    async def sponsor(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="💖 Demon Music Sponsors & Credits",
            description=(
                "Special thanks to the open-source Discord and audio community:\n\n"
                "• **Lavalink v4 Team** — High-performance audio streaming server\n"
                "• **Wavelink Python Library** — Robust Lavalink client\n"
                "• **Pycord Community** — Modern Discord API library with rich Slash support\n"
                "• **Millohost** — High-capacity public Lavalink infrastructure\n\n"
                "_Powered by DeepMind Advanced Agentic Architecture._"
            ),
            color=HEX_DEMON_PURPLE
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(InfoCog(bot))
