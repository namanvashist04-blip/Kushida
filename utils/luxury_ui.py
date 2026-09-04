"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: utils/luxury_ui.py (Persistent Views, Luxury Embeds, Color Engine)
================================================================================
"""

import math
import logging
from typing import Optional, Any
import discord
from discord.ui import View, Button, Modal, InputText, button
from discord import ButtonStyle, InputTextStyle
import wavelink

from config import (
    HEX_DEEP_SPACE,
    HEX_VIOLET,
    HEX_ICE_BLUE,
    HEX_EMERALD,
    HEX_ROSE,
    HEX_GOLD,
    HEX_MUTED,
    ICON_DISC,
    ICON_PLAY,
    ICON_PAUSE,
    ICON_NEXT,
    ICON_PREV,
    ICON_STOP,
    ICON_SHUFFLE,
    ICON_REPEAT,
    ICON_REPEAT_ONE,
    ICON_VOLUME_UP,
    ICON_VOLUME_DOWN,
    ICON_SPOTIFY,
    ICON_AI,
    ICON_VIBE,
    ICON_TIMER,
    DASHBOARD_URL,
    PB_FILL,
    PB_HEAD,
    PB_EMPTY,
    PB_LENGTH,
)
from database import db_manager

logger = logging.getLogger("kushida.luxury_ui")


# ------------------------------------------------------------------------------
# 1. LUXURY COLOR & VIBE ENGINE
# ------------------------------------------------------------------------------
class DynamicColorEngine:
    """Dynamically calculates an ethereal accent color based on track title and artist vibes."""

    MOOD_COLOR_MAP = {
        # High Energy / Phonk / Fast
        ("phonk", "drift", "hardstyle", "rock", "metal", "rage", "hype", "energy"): HEX_ROSE,
        # Chill / Lo-Fi / Ambient / Rain
        ("lo-fi", "lofi", "chill", "ambient", "sleep", "rain", "piano", "study", "relax"): HEX_ICE_BLUE,
        # Neon Synth / Cyber / Night / Wave
        ("synthwave", "retrowave", "night", "dark", "cyber", "vaporwave", "future"): HEX_VIOLET,
        # Acoustic / Jazz / Warm / Classical
        ("acoustic", "jazz", "soul", "guitar", "classical", "coffee", "sunset", "warm"): HEX_GOLD,
        # Energetic Electronic / EDM / Dance
        ("edm", "dance", "electronic", "house", "techno", "club", "dubstep"): HEX_EMERALD,
    }

    @classmethod
    def resolve_track_color(cls, title: str, artist: str = "") -> int:
        """Determines the ambient embed color for a given track."""
        text = f"{title} {artist}".lower()
        for keywords, color in cls.MOOD_COLOR_MAP.items():
            if any(kw in text for kw in keywords):
                return color
        return HEX_VIOLET  # Default signature luxury violet


# ------------------------------------------------------------------------------
# 2. STRING & PROGRESS BAR FORMATTERS
# ------------------------------------------------------------------------------
def format_ms(milliseconds: int) -> str:
    """Format milliseconds into a sleek MM:SS or HH:MM:SS timestamp string."""
    if not milliseconds or milliseconds < 0:
        return "00:00"

    total_seconds = int(milliseconds // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def generate_luxury_progress_bar(position_ms: int, duration_ms: int, length: int = PB_LENGTH) -> str:
    """
    Renders an animated-style text progress bar:
    Example: 01:24 ━━━●━━━━━━━━━━━━ 03:45
    """
    if duration_ms <= 0:
        return f"`00:00` {PB_FILL * (length // 2)}{PB_HEAD}{PB_EMPTY * (length // 2)} `LIVE / ∞`"

    progress = min(max(position_ms / duration_ms, 0.0), 1.0)
    pos_idx = int(round(progress * (length - 1)))

    bar_chars = []
    for i in range(length):
        if i == pos_idx:
            bar_chars.append(PB_HEAD)
        elif i < pos_idx:
            bar_chars.append(PB_FILL)
        else:
            bar_chars.append(PB_EMPTY)

    bar_str = "".join(bar_chars)
    current_str = format_ms(position_ms)
    total_str = format_ms(duration_ms)

    return f"`{current_str}` {bar_str} `{total_str}`"


# ------------------------------------------------------------------------------
# 3. LUXURY EMBED BUILDERS
# ------------------------------------------------------------------------------
class LuxuryEmbedBuilder:
    """Constructs zero-clutter, minimalist, pill-styled Discord embeds."""

    @staticmethod
    def now_playing(player: wavelink.Player, track: wavelink.Playable, requested_by: Optional[discord.Member | discord.User] = None) -> discord.Embed:
        """Builds the main persistent luxury music panel embed."""
        color = DynamicColorEngine.resolve_track_color(track.title, getattr(track, "author", ""))
        embed = discord.Embed(color=color)

        # Title / Track header
        author_name = getattr(track, "author", "Unknown Artist")
        track_title = track.title if len(track.title) <= 55 else f"{track.title[:52]}..."

        embed.title = f"{ICON_DISC}  {track_title}"
        if hasattr(track, "uri") and track.uri:
            embed.url = track.uri

        # Pill Status Indicators (Volume, Loop Mode, Filter, Queue count)
        vol_pct = player.volume
        vol_badge = f"`🔊 {vol_pct}%`"

        queue_mode = getattr(player.queue, "mode", wavelink.QueueMode.normal)
        if queue_mode == wavelink.QueueMode.loop:
            loop_badge = f"`{ICON_REPEAT_ONE} Track`"
        elif queue_mode == wavelink.QueueMode.loop_all:
            loop_badge = f"`{ICON_REPEAT} Queue`"
        else:
            loop_badge = f"`🔁 Off`"

        q_count = len(player.queue)
        queue_badge = f"`📑 {q_count} in queue`"

        # Active audio filter detection
        filter_badge = "`✨ Pure HQ`"
        try:
            if hasattr(player, "filters") and player.filters:
                ts = getattr(player.filters, "timescale", None)
                rot = getattr(player.filters, "rotation", None)
                eq = getattr(player.filters, "equalizer", None)

                if ts and getattr(ts, "speed", 1.0) and getattr(ts, "speed", 1.0) > 1.0:
                    filter_badge = "`⚡ Nightcore`"
                elif rot and getattr(rot, "rotation_hz", 0) and getattr(rot, "rotation_hz", 0) > 0:
                    filter_badge = "`🎧 8D Audio`"
                elif eq and hasattr(eq, "raw") and eq.raw and any(band[1] > 0.1 for band in eq.raw):
                    filter_badge = "`🔊 Bassboost`"
        except Exception:
            filter_badge = "`✨ Pure HQ`"

        # Construct minimalist pill row
        pills = f"{vol_badge}  {loop_badge}  {queue_badge}  {filter_badge}"

        # Progress bar
        current_pos = getattr(player, "position", 0)
        duration = getattr(track, "length", 0)
        progress_bar = generate_luxury_progress_bar(current_pos, duration)

        # Body description
        embed.description = (
            f"**Artist:** `{author_name}`\n"
            f"{pills}\n\n"
            f"{progress_bar}"
        )

        # High-res Thumbnail / Album Artwork
        artwork_url = getattr(track, "artwork_url", None)
        if artwork_url:
            embed.set_thumbnail(url=artwork_url)

        # Requester Footer
        if requested_by:
            avatar_url = requested_by.display_avatar.url if hasattr(requested_by, "display_avatar") else None
            embed.set_footer(
                text=f"Requested by {requested_by.display_name} • Kushida Luxury Sound",
                icon_url=avatar_url
            )
        else:
            embed.set_footer(text="Kushida Luxury Sound System • 24/7 Ethereal Audio")

        return embed

    @staticmethod
    def queue_embed(player: wavelink.Player, page: int = 1, per_page: int = 8) -> discord.Embed:
        """Renders a paginated, sleek queue overview."""
        embed = discord.Embed(title="📑 Current Audio Queue", color=HEX_VIOLET)

        current = player.current
        if current:
            embed.add_field(
                name="Now Playing",
                value=f"**{current.title}**\n`{getattr(current, 'author', 'Unknown')}` • `{format_ms(getattr(current, 'length', 0))}`",
                inline=False
            )

        queue_list = list(player.queue)
        total_tracks = len(queue_list)

        if not queue_list:
            embed.description = "*Queue is currently empty. Use `/play` or the web dashboard to add tracks.*"
            embed.set_footer(text="Kushida Luxury Sound")
            return embed

        total_pages = max(1, math.ceil(total_tracks / per_page))
        page = min(max(1, page), total_pages)

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_tracks = queue_list[start_idx:end_idx]

        lines = []
        for i, t in enumerate(page_tracks, start=start_idx + 1):
            dur = format_ms(getattr(t, "length", 0))
            author = getattr(t, "author", "Unknown")
            title_clean = t.title[:45] + "..." if len(t.title) > 45 else t.title
            lines.append(f"`{i:02d}.` **{title_clean}**\n     `{author}` • `{dur}`")

        embed.description = "\n\n".join(lines)
        embed.set_footer(text=f"Page {page}/{total_pages} • {total_tracks} tracks queued • Kushida Luxury Sound")
        return embed

    @staticmethod
    def vibe_match_embed(u1_name: str, u2_name: str, u1_avatar: str, u2_avatar: str, match_pct: float, shared_artists: list) -> discord.Embed:
        """Renders the luxury VibeMatch social compatibility card."""
        embed = discord.Embed(
            title="🌌 Musical Vibe Compatibility",
            description=f"Audio frequency analysis between **{u1_name}** and **{u2_name}**:",
            color=HEX_VIOLET
        )
        embed.add_field(
            name="💎 Harmony Score",
            value=f"```ansi\n\u001b[1;35m{match_pct}% Sonic Resonance\u001b[0m\n```",
            inline=False
        )
        if shared_artists:
            artist_pills = " • ".join([f"`{a}`" for a in shared_artists])
            embed.add_field(name="✨ Shared Top Artists", value=artist_pills, inline=False)

        embed.set_thumbnail(url=u1_avatar)
        embed.set_footer(text="Kushida AI Vibe Engine • Powered by SQLite Analytics")
        return embed


# ------------------------------------------------------------------------------
# 4. SLEEP TIMER MODAL (Pycord UI Modal)
# ------------------------------------------------------------------------------
class SleepTimerModal(Modal):
    """Modal for custom sleep timer duration input."""

    def __init__(self, player: wavelink.Player):
        super().__init__(title="💤 Set Sleep Timer")
        self.player = player
        self.minutes_input = InputText(
            label="Duration in Minutes",
            placeholder="e.g. 15, 30, 45, 60",
            style=InputTextStyle.short,
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.minutes_input)

    async def callback(self, interaction: discord.Interaction):
        val = self.minutes_input.value.strip()
        try:
            mins = int(val)
            if mins <= 0 or mins > 360:
                await interaction.response.send_message("❌ Please enter a duration between 1 and 360 minutes.", ephemeral=True)
                return

            # Schedule fadeout sleep task on audio cog
            cog = interaction.client.get_cog("Audio")
            if cog and hasattr(cog, "start_sleep_timer"):
                await cog.start_sleep_timer(self.player.guild.id, mins)
                await interaction.response.send_message(
                    f"💤 **Sleep Timer Set:** Music will gently fade out and disconnect in **{mins} minutes**.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("❌ Audio engine unavailable.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid whole number for minutes.", ephemeral=True)


# ------------------------------------------------------------------------------
# 5. PERSISTENT INTERACTIVE MUSIC CONTROL VIEW (Pycord View)
# ------------------------------------------------------------------------------
class MusicControlView(View):
    """
    Persistent, luxury control view for Discord music embeds.
    Permissions: ANY user in the voice channel can interact.
    Pycord Button signature: (self, button: discord.ui.Button, interaction: discord.Interaction)
    """

    def __init__(self):
        super().__init__(timeout=None)
        # Add Link button in __init__ (URL buttons cannot have callback decorators)
        self.add_item(
            Button(
                label="Web Remote",
                style=ButtonStyle.link,
                emoji="🌐",
                url=DASHBOARD_URL,
                row=2
            )
        )

    def _get_player(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Safely fetch active Wavelink player for this guild."""
        if not interaction.guild or not interaction.guild.voice_client:
            return None
        return interaction.guild.voice_client

    async def _ensure_voice_member(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Verify user is in the same voice channel before executing controls."""
        player = self._get_player(interaction)
        if not player or not player.connected:
            await interaction.response.send_message("❌ Bot is not currently active in a voice channel.", ephemeral=True)
            return None

        # Check if caller is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must join the voice channel to use music controls.", ephemeral=True)
            return None

        if interaction.user.voice.channel.id != player.channel.id:
            await interaction.response.send_message("❌ You must be in the same voice channel as Kushida to use controls.", ephemeral=True)
            return None

        return player

    # --------------------------------------------------------------------------
    # ROW 1: PLAYBACK & VOLUME CONTROLS
    # --------------------------------------------------------------------------
    @button(label="Vol -", style=ButtonStyle.secondary, emoji="🔉", custom_id="kushida:vol_down", row=0)
    async def vol_down_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        new_vol = max(0, player.volume - 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(f"🔉 Volume decreased to **{new_vol}%**", ephemeral=True)
        await self.refresh_panel(player)

    @button(label="Prev", style=ButtonStyle.secondary, emoji="⏮️", custom_id="kushida:prev", row=0)
    async def prev_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        cog = interaction.client.get_cog("Audio")
        if cog and hasattr(cog, "play_previous_track"):
            success = await cog.play_previous_track(player.guild.id)
            if success:
                await interaction.response.send_message("⏮️ Returning to previous track...", ephemeral=True)
            else:
                await interaction.response.send_message("❌ No previous track found in history.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Previous track unavailable.", ephemeral=True)

    @button(label="Play/Pause", style=ButtonStyle.primary, emoji="⏯️", custom_id="kushida:play_pause", row=0)
    async def play_pause_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        if player.paused:
            await player.pause(False)
            await interaction.response.send_message("▶️ Resumed playback.", ephemeral=True)
        else:
            await player.pause(True)
            await interaction.response.send_message("⏸️ Paused playback.", ephemeral=True)

        await self.refresh_panel(player)

    @button(label="Next", style=ButtonStyle.secondary, emoji="⏭️", custom_id="kushida:next", row=0)
    async def next_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        if not player.playing and player.queue.is_empty:
            await interaction.response.send_message("❌ Queue is empty.", ephemeral=True)
            return

        await player.skip()
        await interaction.response.send_message("⏭️ Skipped to next track.", ephemeral=True)

    @button(label="Vol +", style=ButtonStyle.secondary, emoji="🔊", custom_id="kushida:vol_up", row=0)
    async def vol_up_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        new_vol = min(200, player.volume + 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(f"🔊 Volume increased to **{new_vol}%**", ephemeral=True)
        await self.refresh_panel(player)

    # --------------------------------------------------------------------------
    # ROW 2: QUEUE & EXTENDED CONTROLS
    # --------------------------------------------------------------------------
    @button(label="Shuffle", style=ButtonStyle.secondary, emoji="🔀", custom_id="kushida:shuffle", row=1)
    async def shuffle_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        if player.queue.is_empty or len(player.queue) < 2:
            await interaction.response.send_message("❌ Not enough tracks in queue to shuffle.", ephemeral=True)
            return

        player.queue.shuffle()
        await interaction.response.send_message("🔀 Queue shuffled smoothly.", ephemeral=True)
        await self.refresh_panel(player)

    @button(label="Loop", style=ButtonStyle.secondary, emoji="🔁", custom_id="kushida:loop", row=1)
    async def loop_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        current_mode = getattr(player.queue, "mode", wavelink.QueueMode.normal)
        if current_mode == wavelink.QueueMode.normal:
            player.queue.mode = wavelink.QueueMode.loop
            mode_str = "Looping Current Track 🔂"
        elif current_mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.loop_all
            mode_str = "Looping Entire Queue 🔁"
        else:
            player.queue.mode = wavelink.QueueMode.normal
            mode_str = "Looping Disabled ➡️"

        await interaction.response.send_message(f"🔁 Loop Mode: **{mode_str}**", ephemeral=True)
        await self.refresh_panel(player)

    @button(label="Sleep Timer", style=ButtonStyle.secondary, emoji="💤", custom_id="kushida:sleep", row=1)
    async def sleep_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        modal = SleepTimerModal(player)
        await interaction.response.send_modal(modal)

    @button(label="Stop", style=ButtonStyle.danger, emoji="⏹️", custom_id="kushida:stop", row=1)
    async def stop_btn(self, btn: Button, interaction: discord.Interaction):
        player = await self._ensure_voice_member(interaction)
        if not player:
            return

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message("⏹️ Playback stopped and disconnected.", ephemeral=True)

    # --------------------------------------------------------------------------
    # ROW 3: SPOTIFY & DASHBOARD
    # --------------------------------------------------------------------------
    @button(label="Save to Spotify", style=ButtonStyle.success, emoji="💚", custom_id="kushida:save_spotify", row=2)
    async def spotify_save_btn(self, btn: Button, interaction: discord.Interaction):
        player = self._get_player(interaction)
        if not player or not player.current:
            await interaction.response.send_message("❌ No track is currently playing to save.", ephemeral=True)
            return

        # Defer to allow Spotify API lookup
        await interaction.response.defer(ephemeral=True)

        cog = interaction.client.get_cog("Audio")
        if cog and hasattr(cog, "save_track_for_user"):
            result = await cog.save_track_for_user(interaction.user.id, player.current)
            await interaction.followup.send(result["message"], ephemeral=True)
        else:
            await interaction.followup.send("❌ Spotify service integration unavailable.", ephemeral=True)

    # --------------------------------------------------------------------------
    # REFRESH HELPER
    # --------------------------------------------------------------------------
    async def refresh_panel(self, player: wavelink.Player) -> None:
        """Silently edit the persistent panel embed to reflect updated state."""
        try:
            if not player or not player.current:
                return

            coords = await db_manager.get_panel_message_id(player.guild.id)
            if not coords:
                return

            channel_id, message_id = coords
            channel = player.guild.get_channel(channel_id)
            if not channel:
                return

            try:
                msg = await channel.fetch_message(message_id)
                new_embed = LuxuryEmbedBuilder.now_playing(player, player.current)
                await msg.edit(embed=new_embed, view=self)
            except discord.NotFound:
                pass
        except Exception as e:
            logger.debug(f"Panel refresh skipped: {e}")
