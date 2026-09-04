"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/system.py (System & Setup Commands: Slash & Prefix)
================================================================================
"""

import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import time
import logging
import wavelink
from typing import Optional

from database import db_manager
from config import HEX_VIOLET, HEX_ICE_BLUE, HEX_ROSE, HEX_EMERALD

logger = logging.getLogger("kushida.system")


class System(commands.Cog):
    """System & Setup commands matching the target specification."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------------------------------------------------------
    # 1. JOIN (Slash: /join | Prefix: -join, -j)
    # --------------------------------------------------------------------------
    async def _do_join(self, ctx) -> Optional[discord.VoiceChannel]:
        author = ctx.author
        if not author.voice or not author.voice.channel:
            msg = "❌ You must be connected to a voice channel first!"
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return None

        channel = author.voice.channel
        player: Optional[wavelink.Player] = ctx.guild.voice_client

        if player and player.connected:
            if player.channel.id == channel.id:
                msg = f"ℹ️ Already connected to **{channel.name}**."
                if isinstance(ctx, discord.ApplicationContext):
                    await ctx.respond(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return channel
            await player.move_to(channel)
        else:
            player = await channel.connect(cls=wavelink.Player)

        # Set active text channel for updates
        player.text_channel = ctx.channel

        embed = discord.Embed(
            title="🔊 Connected",
            description=f"Joined **{channel.name}** and ready to play!",
            color=HEX_EMERALD
        )
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)
        return channel

    @slash_command(name="join", description="Connect bot to your voice channel.")
    async def join_slash(self, ctx: discord.ApplicationContext):
        await self._do_join(ctx)

    @commands.command(name="join", aliases=["j"], help="Bot ko voice channel mein bulayein.")
    async def join_prefix(self, ctx: commands.Context):
        await self._do_join(ctx)

    # --------------------------------------------------------------------------
    # 2. LEAVE (Slash: /leave | Prefix: -leave, -dc)
    # --------------------------------------------------------------------------
    async def _do_leave(self, ctx):
        player: Optional[wavelink.Player] = ctx.guild.voice_client
        if not player or not player.connected:
            msg = "❌ Bot is not currently connected to any voice channel."
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        channel_name = player.channel.name if player.channel else "Voice Channel"
        player.queue.clear()
        await player.disconnect()

        embed = discord.Embed(
            title="👋 Disconnected",
            description=f"Left **{channel_name}** and cleared the queue.",
            color=HEX_ROSE
        )
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="leave", description="Disconnect bot from the voice channel.")
    async def leave_slash(self, ctx: discord.ApplicationContext):
        await self._do_leave(ctx)

    @commands.command(name="leave", aliases=["dc", "disconnect"], help="Bot ko voice channel se bahar nikalein.")
    async def leave_prefix(self, ctx: commands.Context):
        await self._do_leave(ctx)

    # --------------------------------------------------------------------------
    # 3. 24/7 MODE (Slash: /247 | Prefix: -247, -24/7)
    # --------------------------------------------------------------------------
    async def _do_247(self, ctx):
        guild_id = ctx.guild.id
        current_state = await db_manager.get_guild_247(guild_id)
        new_state = not current_state
        await db_manager.set_guild_247(guild_id, new_state)

        status_text = "🟢 **Enabled**" if new_state else "🔴 **Disabled**"
        desc = (
            f"24/7 Mode is now {status_text}!\n\n"
            + ("Bot will remain in the voice channel 24/7 even if no one is listening."
               if new_state else
               "Bot will automatically disconnect after inactivity when idle.")
        )
        embed = discord.Embed(title="⏰ 24/7 Mode Toggle", description=desc, color=HEX_VIOLET if new_state else HEX_ROSE)
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="247", description="Toggle 24/7 mode (stay in voice channel permanently).")
    async def mode_247_slash(self, ctx: discord.ApplicationContext):
        await self._do_247(ctx)

    @commands.command(name="247", aliases=["24/7"], help="Bot ko hamesha VC mein rakhne ke liye toggle karein.")
    async def mode_247_prefix(self, ctx: commands.Context):
        await self._do_247(ctx)

    # --------------------------------------------------------------------------
    # 4. PREFIX (Slash: /prefix <new> | Prefix: -prefix <new>)
    # --------------------------------------------------------------------------
    async def _do_prefix(self, ctx, new_prefix: str):
        new_prefix = new_prefix.strip()
        if not new_prefix or len(new_prefix) > 5:
            msg = "❌ Prefix must be between 1 and 5 characters long!"
            if isinstance(ctx, discord.ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        guild_id = ctx.guild.id
        await db_manager.set_guild_prefix(guild_id, new_prefix)
        if hasattr(self.bot, "prefix_cache"):
            self.bot.prefix_cache[guild_id] = new_prefix

        embed = discord.Embed(
            title="⚙️ Prefix Updated",
            description=f"Server command prefix has been changed to: `{new_prefix}`\n\nExample: `{new_prefix}play`, `{new_prefix}help`",
            color=HEX_ICE_BLUE
        )
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="prefix", description="Change the bot prefix for this server.")
    async def prefix_slash(
        self,
        ctx: discord.ApplicationContext,
        new_prefix: Option(str, "New prefix symbol (e.g. -, !, ?)", required=True)
    ):
        await self._do_prefix(ctx, new_prefix)

    @commands.command(name="prefix", aliases=["setprefix"], help="Server prefix change karein.")
    async def prefix_prefix(self, ctx: commands.Context, new_prefix: str = None):
        if not new_prefix:
            curr = await db_manager.get_guild_prefix(ctx.guild.id)
            await ctx.send(f"ℹ️ Current server prefix is: `{curr}`. Use `{curr}prefix <new>` to change it.")
            return
        await self._do_prefix(ctx, new_prefix)

    # --------------------------------------------------------------------------
    # 5. HELP (Slash: /help | Prefix: -help, -h)
    # --------------------------------------------------------------------------
    async def _do_help(self, ctx):
        prefix = "-"
        if ctx.guild:
            prefix = await db_manager.get_guild_prefix(ctx.guild.id)

        embed = discord.Embed(
            title="🎵 Kushida Music Bot — Command Guide",
            description=(
                f"Use commands with Slash **`/`** or Prefix **`{prefix}`**.\n"
                f"Web Remote: **[Click to open Remote Control](http://localhost:8501)**\n"
                f"───────────────────────────────"
            ),
            color=HEX_VIOLET
        )

        music_cmds = (
            f"`{prefix}play` ya `/play` — Gaana chalane ke liye (Song name ya URL)\n"
            f"`{prefix}skip` ya `/skip` — Current gaana skip karne ke liye (`-s`)\n"
            f"`{prefix}stop` ya `/stop` — Music band karne & poori queue clear karne ke liye\n"
            f"`{prefix}pause` ya `/pause` — Gaane ko pause karne ke liye\n"
            f"`{prefix}resume` ya `/resume` — Paused gaana resume karne ke liye (`-r`)\n"
            f"`{prefix}queue` ya `/queue` — Upcoming gaano ki list dekhne ke liye (`-q`)\n"
            f"`{prefix}nowplaying` ya `/nowplaying` — Current gaane ki details (`-np`)\n"
            f"`{prefix}volume` ya `/volume` — Aawaz kam/tez karne ke liye (`-v <0-200>`)\n"
            f"`{prefix}shuffle` ya `/shuffle` — Queue ke gaano ko mix karne ke liye\n"
            f"`{prefix}loop` ya `/loop` — Song ya queue repeat par lagane ke liye\n"
            f"`{prefix}clearqueue` ya `/clearqueue` — Aage ki queue hatane ke liye (`-cq`)\n"
            f"`{prefix}lyrics` ya `/lyrics` — Chal rahe gaane ke lyrics dekhne ke liye (`-ly`)"
        )
        embed.add_field(name="🎵 Music Commands", value=music_cmds, inline=False)

        system_cmds = (
            f"`{prefix}join` ya `/join` — Bot ko voice channel mein bulayein (`-j`)\n"
            f"`{prefix}leave` ya `/leave` — Bot ko voice channel se bahar nikalein (`-dc`)\n"
            f"`{prefix}247` ya `/247` — 24/7 VC mode toggle karein (`-24/7`)\n"
            f"`{prefix}prefix` ya `/prefix` — Server ka symbol change karein\n"
            f"`{prefix}help` ya `/help` — Sabhi commands ki list dekhne ke liye (`-h`)\n"
            f"`{prefix}ping` ya `/ping` — Bot response time & speed check karein\n"
            f"`{prefix}invite` ya `/invite` — Bot ko apne server mein add karne ka link"
        )
        embed.add_field(name="⚙️ System & Setup Commands", value=system_cmds, inline=False)

        embed.set_footer(text="Kushida Luxury Sound System • 24/7 High Fidelity Audio")
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="help", description="Show all available Kushida bot commands.")
    async def help_slash(self, ctx: discord.ApplicationContext):
        await self._do_help(ctx)

    @commands.command(name="help", aliases=["h"], help="Bot ki sabhi commands ki list.")
    async def help_prefix(self, ctx: commands.Context):
        await self._do_help(ctx)

    # --------------------------------------------------------------------------
    # 6. PING (Slash: /ping | Prefix: -ping)
    # --------------------------------------------------------------------------
    async def _do_ping(self, ctx):
        start_t = time.perf_counter()
        ws_ping = round(self.bot.latency * 1000)

        embed = discord.Embed(title="🏓 Pong!", color=HEX_ICE_BLUE)
        embed.add_field(name="🌐 Discord Gateway", value=f"`{ws_ping} ms`", inline=True)

        try:
            node = wavelink.Pool.get_node()
            if node and node.status == wavelink.NodeStatus.CONNECTED:
                embed.add_field(name="🎵 Lavalink Node", value=f"`Connected ({node.identifier})`", inline=True)
            else:
                embed.add_field(name="🎵 Lavalink Node", value="`Reconnecting...`", inline=True)
        except Exception:
            embed.add_field(name="🎵 Lavalink Node", value="`Offline`", inline=True)

        end_t = time.perf_counter()
        roundtrip = round((end_t - start_t) * 1000)
        embed.add_field(name="⚡ API Roundtrip", value=f"`{roundtrip} ms`", inline=True)

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="ping", description="Check bot latency and gateway connection speed.")
    async def ping_slash(self, ctx: discord.ApplicationContext):
        await self._do_ping(ctx)

    @commands.command(name="ping", help="Bot latency aur response speed check karein.")
    async def ping_prefix(self, ctx: commands.Context):
        await self._do_ping(ctx)

    # --------------------------------------------------------------------------
    # 7. INVITE (Slash: /invite | Prefix: -invite)
    # --------------------------------------------------------------------------
    async def _do_invite(self, ctx):
        client_id = self.bot.user.id if self.bot.user else "1545396774884352041"
        invite_url = (
            f"https://discord.com/oauth2/authorize?client_id={client_id}"
            f"&permissions=8&scope=bot%20applications.commands"
        )
        embed = discord.Embed(
            title="🔗 Invite Kushida to Your Server",
            description=(
                f"Kushida ko kisi bhi server mein add karne ke liye neeche diye link par click karein:\n\n"
                f"👉 **[Click Here to Invite Kushida]({invite_url})**\n\n"
                f"*Permissions: Administrator / Voice & Slash Commands enabled.*"
            ),
            color=HEX_VIOLET
        )
        if self.bot.user and self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        if isinstance(ctx, discord.ApplicationContext):
            await ctx.respond(embed=embed)
        else:
            await ctx.send(embed=embed)

    @slash_command(name="invite", description="Get the invite link to add Kushida to your server.")
    async def invite_slash(self, ctx: discord.ApplicationContext):
        await self._do_invite(ctx)

    @commands.command(name="invite", help="Bot invite link paane ke liye.")
    async def invite_prefix(self, ctx: commands.Context):
        await self._do_invite(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(System(bot))
