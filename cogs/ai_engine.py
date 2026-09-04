"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: cogs/ai_engine.py (Gemini LLM Contextual Search, Moods & VibeMatch)
================================================================================
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any
import discord
from discord.ext import commands
from discord.commands import slash_command
from discord import Option

import wavelink
import google.generativeai as genai

from config import (
    GEMINI_API_KEY,
    HEX_VIOLET,
    HEX_ICE_BLUE,
    HEX_ROSE,
    HEX_GOLD,
    ICON_AI,
    ICON_VIBE,
    ICON_DISC,
)
from database import db_manager
from utils.luxury_ui import LuxuryEmbedBuilder

logger = logging.getLogger("kushida.ai_engine")


class AIEngine(commands.Cog):
    """
    AI-powered contextual search, mood queue generator, and social vibe analytics.
    Backed by Google Generative AI (Gemini 2.0 / 1.5).
    """

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.model = None
        self._init_gemini()

    def _init_gemini(self) -> None:
        """Initialize Google Generative AI SDK."""
        if GEMINI_API_KEY:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                # Use gemini-1.5-flash or gemini-2.0-flash for ultra-fast, zero-latency inference
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("Google Generative AI Engine configured successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI: {e}")
                self.model = None
        else:
            logger.warning("GEMINI_API_KEY not configured. AI features will run in heuristic fallback mode.")

    # --------------------------------------------------------------------------
    # 1. /find [query] — CONTEXTUAL & LYRIC SONG MATCHER
    # --------------------------------------------------------------------------
    @slash_command(
        name="find",
        description="Search songs by lyrics (e.g., 'I tried so hard') or abstract context ('sad Naruto song')."
    )
    async def find_command(
        self,
        ctx: discord.ApplicationContext,
        query: Option(str, "Lyrics, movie scene, anime moment, or abstract description", required=True)
    ):
        """Identifies exact track name and artist from vague descriptions or lyrics using Gemini."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)
            return

        await ctx.defer()

        identified_track = None
        identified_artist = None

        if self.model:
            prompt = f"""
You are an elite music encyclopedic AI. Given the following natural language query, lyrics snippet, or abstract description, identify the EXACT music track title and primary artist.

Query: "{query}"

Respond strictly in valid JSON with no markdown backticks, in this exact format:
{{"title": "Track Title", "artist": "Artist Name", "confidence": "high"}}
"""
            try:
                response = self.model.generate_content(prompt)
                raw_text = response.text.strip()
                # Clean possible code fence
                clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
                data = json.loads(clean_json)
                identified_track = data.get("title")
                identified_artist = data.get("artist")
            except Exception as e:
                logger.error(f"Gemini AI /find error: {e}")

        # Fallback to raw query if AI failed or unconfigured
        search_query = f"{identified_track} {identified_artist}" if (identified_track and identified_artist) else query

        # Connect or fetch player
        player: wavelink.Player
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            player = ctx.voice_client

        player.text_channel = ctx.channel

        # Search Wavelink
        search_results: wavelink.Search = await wavelink.Playable.search(search_query)
        if not search_results:
            await ctx.respond(f"❌ AI matched `{search_query}`, but could not stream it from audio providers.", ephemeral=True)
            return

        track: wavelink.Playable = search_results[0]
        setattr(track, "requester_id", ctx.author.id)
        await player.queue.put_wait(track)

        embed = discord.Embed(
            title=f"{ICON_AI} AI Contextual Match",
            description=(
                f"**Identified:** `{track.title}` by `{getattr(track, 'author', 'Unknown')}`\n"
                f"**Original Query:** *\"{query}\"*"
            ),
            color=HEX_VIOLET
        )
        if getattr(track, "artwork_url", None):
            embed.set_thumbnail(url=track.artwork_url)

        await ctx.respond(embed=embed)

        if not player.playing and not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)

    # --------------------------------------------------------------------------
    # 2. /random [mood] — DYNAMIC MOOD QUEUE GENERATOR
    # --------------------------------------------------------------------------
    @slash_command(
        name="random",
        description="Generate an instant curated queue of 5 tracks tailored to a specific mood."
    )
    async def random_mood_command(
        self,
        ctx: discord.ApplicationContext,
        mood: Option(
            str,
            "Select an audio vibe",
            choices=["Energetic", "Chill", "Phonk", "Late Night", "Happy", "Lo-Fi", "Synthwave"],
            required=True
        )
    ):
        """Generates dynamic queues based on selected mood."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)
            return

        await ctx.defer()
        await self._generate_and_queue_ai_playlist(ctx, context_type="mood", value=mood)

    # --------------------------------------------------------------------------
    # 3. /vibe [scenario] — SCENARIO QUEUE GENERATOR
    # --------------------------------------------------------------------------
    @slash_command(
        name="vibe",
        description="Curate an atmospheric 5-track playlist for your current real-world activity."
    )
    async def vibe_scenario_command(
        self,
        ctx: discord.ApplicationContext,
        scenario: Option(
            str,
            "Select your current activity",
            choices=["Gym / Workout", "Late Night Drive", "Deep Coding / Focus", "Gaming Session", "Study Session"],
            required=True
        )
    ):
        """Generates dynamic queues based on selected scenario."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("❌ You must join a voice channel first!", ephemeral=True)
            return

        await ctx.defer()
        await self._generate_and_queue_ai_playlist(ctx, context_type="scenario", value=scenario)

    # --------------------------------------------------------------------------
    # 4. HELPER: GENERATE & QUEUE AI PLAYLIST
    # --------------------------------------------------------------------------
    async def _generate_and_queue_ai_playlist(self, ctx: discord.ApplicationContext, context_type: str, value: str) -> None:
        """Invokes Gemini LLM to curate 5 tracks, searches them on Lavalink, and pushes them to queue."""
        suggested_songs = []

        if self.model:
            prompt = f"""
Generate a curated list of exactly 5 high-quality, popular, and diverse songs perfectly suited for the following {context_type}: "{value}".

Respond strictly in valid JSON format with no additional text or markdown formatting:
[
  {{"title": "Song Title", "artist": "Artist Name"}},
  {{"title": "Song Title", "artist": "Artist Name"}},
  {{"title": "Song Title", "artist": "Artist Name"}},
  {{"title": "Song Title", "artist": "Artist Name"}},
  {{"title": "Song Title", "artist": "Artist Name"}}
]
"""
            try:
                response = self.model.generate_content(prompt)
                raw_text = response.text.strip()
                clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
                suggested_songs = json.loads(clean_json)
            except Exception as e:
                logger.error(f"Gemini playlist generation error: {e}")

        # Fallback default presets if LLM is unavailable
        if not suggested_songs:
            fallback_presets = {
                "Energetic": [("Can't Hold Us", "Macklemore"), ("Levels", "Avicii"), ("Titanium", "David Guetta")],
                "Chill": [("Sunset Lover", "Petit Biscuit"), ("Resonance", "HOME"), ("Coffee", "beabadoobee")],
                "Phonk": [("Murder In My Mind", "KORDHELL"), ("Metamorphosis", "INTERWORLD"), ("RAVE", "Dxrk")],
                "Late Night": [("Midnight City", "M83"), ("After Hours", "The Weeknd"), ("Starboy", "The Weeknd")],
                "Deep Coding / Focus": [("Solaris", "Kiasmos"), ("Weightless", "Marconi Union"), ("Daylight", "Disasterpeace")],
                "Gym / Workout": [("Till I Collapse", "Eminem"), ("Stronger", "Kanye West"), ("Remember the Name", "Fort Minor")],
            }
            preset = fallback_presets.get(value, [("Starboy", "The Weeknd"), ("Resonance", "HOME")])
            suggested_songs = [{"title": t, "artist": a} for t, a in preset]

        # Connect voice
        player: wavelink.Player
        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            player = ctx.voice_client

        player.text_channel = ctx.channel

        queued_titles = []
        for item in suggested_songs:
            q = f"{item['title']} {item['artist']}"
            res = await wavelink.Playable.search(q)
            if res:
                track = res[0]
                setattr(track, "requester_id", ctx.author.id)
                await player.queue.put_wait(track)
                queued_titles.append(f"`{track.title[:35]}` by `{getattr(track, 'author', 'Unknown')}`")

        # Auto-start if idle
        if not player.playing and not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)

        lines = "\n".join([f"• {t}" for t in queued_titles])
        embed = discord.Embed(
            title=f"{ICON_VIBE} {value} — Curated Vibe",
            description=f"Generated and queued **{len(queued_titles)} tracks**:\n\n{lines}",
            color=HEX_ICE_BLUE
        )
        embed.set_footer(text="Kushida AI Vibe Engine • Google Gemini")
        await ctx.respond(embed=embed)

    # --------------------------------------------------------------------------
    # 5. /vibematch — SOCIAL MUSIC TASTE ANALYTICS
    # --------------------------------------------------------------------------
    @slash_command(
        name="vibematch",
        description="Analyze server listening history to find the two users with the most resonant music taste."
    )
    async def vibematch_command(self, ctx: discord.ApplicationContext):
        """Analyzes SQLite listening history in this guild to match two users with highest similarity."""
        await ctx.defer()

        result = await db_manager.calculate_vibe_match(ctx.guild.id)
        if not result:
            embed = discord.Embed(
                title="🌌 Musical Vibe Compatibility",
                description=(
                    "Not enough listening history accumulated in this server yet!\n"
                    "Play more tracks using `/play` or the Web Dashboard to unlock server vibe matching."
                ),
                color=HEX_VIOLET
            )
            await ctx.respond(embed=embed)
            return

        u1_id = result["user_1"]
        u2_id = result["user_2"]
        match_pct = result["match_percentage"]
        shared_artists = result["shared_artists"]

        u1 = ctx.guild.get_member(u1_id)
        u2 = ctx.guild.get_member(u2_id)

        u1_name = u1.display_name if u1 else f"User {u1_id}"
        u2_name = u2.display_name if u2 else f"User {u2_id}"

        u1_avatar = u1.display_avatar.url if u1 else ""
        u2_avatar = u2.display_avatar.url if u2 else ""

        embed = LuxuryEmbedBuilder.vibe_match_embed(
            u1_name=u1_name,
            u2_name=u2_name,
            u1_avatar=u1_avatar,
            u2_avatar=u2_avatar,
            match_pct=match_pct,
            shared_artists=shared_artists
        )

        # Mention the users in the content
        content = f"✨ **Cosmic Resonance Found!** {u1.mention if u1 else u1_name} × {u2.mention if u2 else u2_name}"
        await ctx.respond(content=content, embed=embed)


def setup(bot: discord.Bot):
    """Cog loader for Pycord."""
    bot.add_cog(AIEngine(bot))
