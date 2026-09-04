"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/settings.py (All 6 Server & DJ Slash Commands)
================================================================================
"""

import logging
from typing import Optional
import discord
from discord.ext import commands
from discord.commands import slash_command, Option, default_permissions
import wavelink

from config import HEX_DEMON_PURPLE, HEX_DEMON_ACCENT, HEX_DEMON_RED, HEX_EMERALD
from database import db_manager
from utils.luxury_ui import MusicControlView, LuxuryEmbedBuilder

logger = logging.getLogger("demon.settings")


class SettingsCog(commands.Cog, name="Settings & DJ"):
    """All 6 Server Settings & DJ Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._view: Optional[MusicControlView] = None

    @property
    def persistent_view(self) -> MusicControlView:
        if self._view is None:
            self._view = MusicControlView()
        return self._view

    # --------------------------------------------------------------------------
    # 1. /247 (and alias /24-7)
    # --------------------------------------------------------------------------
    @slash_command(name="247", description="♾️ Toggle 24/7 mode (Bot stays connected to VC indefinitely)")
    @default_permissions(administrator=True)
    async def toggle_247(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ You need Administrator permission to use this command.", ephemeral=True)

        current = await db_manager.get_guild_247(ctx.guild.id)
        new_state = not current
        await db_manager.set_guild_247(ctx.guild.id, new_state)

        player: Optional[wavelink.Player] = ctx.voice_client
        if new_state:
            if ctx.author.voice and ctx.author.voice.channel:
                vc = ctx.author.voice.channel
                await db_manager.set_guild_247_channel(ctx.guild.id, vc.id)
                if not player or not player.connected:
                    try:
                        await vc.connect(cls=wavelink.Player)
                    except Exception:
                        pass
            embed = discord.Embed(
                title="♾️ 24/7 Mode Enabled",
                description="Demon Music will remain connected to your voice channel indefinitely, even when idle.",
                color=HEX_EMERALD
            )
        else:
            await db_manager.set_guild_247_channel(ctx.guild.id, None)
            embed = discord.Embed(
                title="⏸️ 24/7 Mode Disabled",
                description="Demon Music will now automatically disconnect after inactivity when the queue is finished.",
                color=HEX_DEMON_RED
            )

        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 2. /musicpanel
    # --------------------------------------------------------------------------
    @slash_command(name="musicpanel", description="🎛️ Spawn a dedicated persistent interactive music control panel")
    @default_permissions(manage_channels=True)
    async def musicpanel(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.manage_channels and not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ You need Manage Channels permission.", ephemeral=True)

        player: Optional[wavelink.Player] = ctx.voice_client
        if player and player.current:
            embed = LuxuryEmbedBuilder.now_playing(player, player.current)
        else:
            embed = discord.Embed(
                title="DEMON MUSIC TERMINAL",
                description="No music is currently playing.\nUse `/play <query>` to queue your favorite songs!",
                color=HEX_DEMON_PURPLE
            )
            embed.set_footer(text="Persistent Remote Control Panel • 24/7 Audio Engine")

        view = self.persistent_view
        msg = await ctx.channel.send(embed=embed, view=view)
        await db_manager.set_panel_message_id(ctx.guild.id, ctx.channel.id, msg.id)
        await ctx.respond(f"✅ Spawned persistent music control panel in {ctx.channel.mention}!", ephemeral=True)

    # --------------------------------------------------------------------------
    # 3. /setprefix [prefix]
    # --------------------------------------------------------------------------
    @slash_command(name="setprefix", description="⚙️ Check or change bot command prefix instructions")
    async def setprefix(
        self,
        ctx: discord.ApplicationContext,
        prefix: Option(str, "New prefix or inquiry", required=False, default="-")
    ):
        embed = discord.Embed(
            title="⚙️ Command Interface Notice",
            description=(
                "⚡ **Demon Music is built exclusively for Discord Slash Commands (`/`)!**\n\n"
                "• All 67 commands are available directly by typing `/`.\n"
                "• Auto-complete, interactive buttons, and modals are powered via Slash commands.\n"
                "• Try typing `/play`, `/help`, or `/queue` to get started!"
            ),
            color=HEX_DEMON_PURPLE
        )
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 4. /adddj [role]
    # --------------------------------------------------------------------------
    @slash_command(name="adddj", description="🎧 Add a role to the DJ role permissions list")
    @default_permissions(manage_roles=True)
    async def adddj(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Discord role to add as DJ", required=True)
    ):
        if not ctx.author.guild_permissions.manage_roles and not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ You need Manage Roles permission.", ephemeral=True)

        success = await db_manager.add_dj_role(ctx.guild.id, role.id)
        if success:
            await ctx.respond(f"🎧 Added {role.mention} to DJ roles!")
        else:
            await ctx.respond(f"⚠️ {role.mention} is already registered as a DJ role.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 5. /removedj [role]
    # --------------------------------------------------------------------------
    @slash_command(name="removedj", description="❌ Remove a role from the DJ role permissions list")
    @default_permissions(manage_roles=True)
    async def removedj(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Discord role to remove from DJ", required=True)
    ):
        if not ctx.author.guild_permissions.manage_roles and not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ You need Manage Roles permission.", ephemeral=True)

        success = await db_manager.remove_dj_role(ctx.guild.id, role.id)
        if success:
            await ctx.respond(f"❌ Removed {role.mention} from DJ roles.")
        else:
            await ctx.respond(f"⚠️ {role.mention} was not found in the DJ list.", ephemeral=True)

    # --------------------------------------------------------------------------
    # 6. /toggledj
    # --------------------------------------------------------------------------
    @slash_command(name="toggledj", description="🔒 Toggle DJ-Only mode (Restricts skip, stop, filters to DJs/Admins)")
    @default_permissions(administrator=True)
    async def toggledj(self, ctx: discord.ApplicationContext):
        if not ctx.author.guild_permissions.administrator:
            return await ctx.respond("❌ You need Administrator permission.", ephemeral=True)

        current = await db_manager.get_dj_only(ctx.guild.id)
        new_state = not current
        await db_manager.set_dj_only(ctx.guild.id, new_state)

        state_text = "ENABLED" if new_state else "DISABLED"
        embed = discord.Embed(
            title="🔒 DJ-Only Mode",
            description=f"DJ-Only mode has been **{state_text}**.\nWhen enabled, only users with configured DJ roles or Administrators can control playback.",
            color=HEX_DEMON_PURPLE if new_state else HEX_MUTED
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(SettingsCog(bot))
