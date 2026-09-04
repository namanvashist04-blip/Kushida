"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/filters.py (All 15 Audio Filter Slash Commands)
================================================================================
"""

import logging
from typing import Optional
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import wavelink

from config import HEX_DEMON_PURPLE, HEX_DEMON_ACCENT
from database import db_manager

logger = logging.getLogger("demon.filters")


async def is_dj_or_admin(ctx: discord.ApplicationContext) -> bool:
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
    return any(rid in dj_roles for rid in author_role_ids)


class FiltersCog(commands.Cog, name="Filters"):
    """All 15 DSP Audio Filter Slash Commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_player(self, ctx: discord.ApplicationContext) -> Optional[wavelink.Player]:
        return ctx.voice_client

    # --------------------------------------------------------------------------
    # 1. /8d
    # --------------------------------------------------------------------------
    @slash_command(name="8d", description="🎧 Toggle 8D spatial audio rotation")
    async def filter_8d(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.rotation.set(rotation_hz=0.2)
        await player.set_filters(filters)
        await ctx.respond("🎧 **8D Audio Filter Applied!** (Enjoy with headphones)")

    # --------------------------------------------------------------------------
    # 2. /bass
    # --------------------------------------------------------------------------
    @slash_command(name="bass", description="🔊 Mild low-frequency bass enhancement")
    async def filter_bass(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[
            {"band": 0, "gain": 0.15},
            {"band": 1, "gain": 0.12},
            {"band": 2, "gain": 0.08},
        ])
        await player.set_filters(filters)
        await ctx.respond("🔊 **Bass Boost (Mild) Applied.**")

    # --------------------------------------------------------------------------
    # 3. /bassboost
    # --------------------------------------------------------------------------
    @slash_command(name="bassboost", description="💥 Heavy sub-bass boost")
    async def filter_bassboost(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[
            {"band": 0, "gain": 0.60},
            {"band": 1, "gain": 0.50},
            {"band": 2, "gain": 0.40},
            {"band": 3, "gain": 0.35},
        ])
        await player.set_filters(filters)
        await ctx.respond("💥 **Heavy Bassboost Applied!**")

    # --------------------------------------------------------------------------
    # 4. /chipmunk
    # --------------------------------------------------------------------------
    @slash_command(name="chipmunk", description="🐿️ High pitch vocal transformation")
    async def filter_chipmunk(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.timescale.set(speed=1.05, pitch=1.35, rate=1.25)
        await player.set_filters(filters)
        await ctx.respond("🐿️ **Chipmunk Filter Applied.**")

    # --------------------------------------------------------------------------
    # 5. /nightcore
    # --------------------------------------------------------------------------
    @slash_command(name="nightcore", description="🌙 Sped up and high-pitched audio")
    async def filter_nightcore(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.timescale.set(speed=1.2, pitch=1.25, rate=1.0)
        await player.set_filters(filters)
        await ctx.respond("🌙 **Nightcore Filter Applied.**")

    # --------------------------------------------------------------------------
    # 6. /slowmo
    # --------------------------------------------------------------------------
    @slash_command(name="slowmo", description="⏳ Slowed & aesthetic vibe")
    async def filter_slowmo(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.timescale.set(speed=0.85, pitch=0.85, rate=1.0)
        await player.set_filters(filters)
        await ctx.respond("⏳ **Slowed & Aesthetic Filter Applied.**")

    # --------------------------------------------------------------------------
    # 7. /soft
    # --------------------------------------------------------------------------
    @slash_command(name="soft", description="☁️ Low-pass filter smoothing out harsh highs")
    async def filter_soft(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.low_pass.set(smoothing=20.0)
        await player.set_filters(filters)
        await ctx.respond("☁️ **Soft Filter Applied.**")

    # --------------------------------------------------------------------------
    # 8. /speed [value]
    # --------------------------------------------------------------------------
    @slash_command(name="speed", description="⚡ Custom speed multiplier (0.5x to 2.0x)")
    async def filter_speed(
        self,
        ctx: discord.ApplicationContext,
        value: Option(float, "Speed multiplier (e.g. 1.25)", required=True, min_value=0.5, max_value=2.0)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.timescale.set(speed=value)
        await player.set_filters(filters)
        await ctx.respond(f"⚡ **Playback Speed set to {value}x.**")

    # --------------------------------------------------------------------------
    # 9. /pop
    # --------------------------------------------------------------------------
    @slash_command(name="pop", description="🎤 Pop equalizer preset for vocal clarity")
    async def filter_pop(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[
            {"band": 0, "gain": -0.05},
            {"band": 1, "gain": 0.05},
            {"band": 2, "gain": 0.10},
            {"band": 3, "gain": 0.15},
            {"band": 4, "gain": 0.10},
            {"band": 5, "gain": 0.05},
        ])
        await player.set_filters(filters)
        await ctx.respond("🎤 **Pop Vocal Equalizer Applied.**")

    # --------------------------------------------------------------------------
    # 10. /radio
    # --------------------------------------------------------------------------
    @slash_command(name="radio", description="📻 Vintage AM radio effect")
    async def filter_radio(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[
            {"band": 0, "gain": -0.25},
            {"band": 1, "gain": -0.20},
            {"band": 2, "gain": 0.15},
            {"band": 3, "gain": 0.30},
            {"band": 4, "gain": 0.15},
            {"band": 11, "gain": -0.20},
            {"band": 12, "gain": -0.25},
        ])
        await player.set_filters(filters)
        await ctx.respond("📻 **Vintage Radio Filter Applied.**")

    # --------------------------------------------------------------------------
    # 11. /karaoke
    # --------------------------------------------------------------------------
    @slash_command(name="karaoke", description="🎙️ Vocal attenuation algorithm for sing-along")
    async def filter_karaoke(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        await player.set_filters(filters)
        await ctx.respond("🎙️ **Karaoke Vocal Cut Applied.**")

    # --------------------------------------------------------------------------
    # 12. /treblebass
    # --------------------------------------------------------------------------
    @slash_command(name="treblebass", description="🎸 Boost both sub-bass and high crisp frequencies")
    async def filter_treblebass(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[
            {"band": 0, "gain": 0.30},
            {"band": 1, "gain": 0.25},
            {"band": 2, "gain": 0.15},
            {"band": 10, "gain": 0.15},
            {"band": 11, "gain": 0.25},
            {"band": 12, "gain": 0.30},
        ])
        await player.set_filters(filters)
        await ctx.respond("🎸 **Treble & Bass Boost Applied.**")

    # --------------------------------------------------------------------------
    # 13. /equalizer [preset]
    # --------------------------------------------------------------------------
    @slash_command(name="equalizer", description="🎛️ Select custom band profiles")
    async def filter_equalizer(
        self,
        ctx: discord.ApplicationContext,
        preset: Option(str, "Preset profile", choices=["Flat", "Rock", "Classical", "Jazz", "Electronic"], required=True)
    ):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        if preset == "Flat":
            filters.equalizer.reset()
        elif preset == "Rock":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.20},
                {"band": 1, "gain": 0.15},
                {"band": 2, "gain": -0.05},
                {"band": 7, "gain": 0.10},
                {"band": 11, "gain": 0.20},
            ])
        elif preset == "Classical":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.15},
                {"band": 1, "gain": 0.10},
                {"band": 6, "gain": -0.05},
                {"band": 11, "gain": 0.15},
            ])
        elif preset == "Jazz":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.10},
                {"band": 1, "gain": 0.15},
                {"band": 3, "gain": 0.05},
                {"band": 8, "gain": 0.10},
            ])
        elif preset == "Electronic":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.35},
                {"band": 1, "gain": 0.25},
                {"band": 2, "gain": 0.10},
                {"band": 10, "gain": 0.20},
                {"band": 12, "gain": 0.30},
            ])

        await player.set_filters(filters)
        await ctx.respond(f"🎛️ **Equalizer Preset set to: {preset}**")

    # --------------------------------------------------------------------------
    # 14. /earrape
    # --------------------------------------------------------------------------
    @slash_command(name="earrape", description="⚠️ Maximum equalizer gain (distorted/loud)")
    async def filter_earrape(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = player.filters or wavelink.Filters()
        filters.equalizer.set(bands=[{"band": i, "gain": 0.8} for i in range(15)])
        await player.set_filters(filters)
        await ctx.respond("⚠️ **Earrape Filter Applied!** (Lower your Discord volume!)")

    # --------------------------------------------------------------------------
    # 15. /clearfilter
    # --------------------------------------------------------------------------
    @slash_command(name="clearfilter", description="🔄 Reset all active filters and equalizers back to standard flat audio")
    async def filter_clear(self, ctx: discord.ApplicationContext):
        if not await is_dj_or_admin(ctx):
            return await ctx.respond("❌ DJ Mode is active.", ephemeral=True)
        player = self._get_player(ctx)
        if not player or not player.connected:
            return await ctx.respond("❌ Bot is not connected to voice.", ephemeral=True)

        filters = wavelink.Filters()
        filters.reset()
        await player.set_filters(filters)
        await ctx.respond("🔄 **All filters reset to flat/default audio.**")


def setup(bot: commands.Bot):
    bot.add_cog(FiltersCog(bot))
