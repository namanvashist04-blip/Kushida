"""
================================================================================
  KUSHIDA — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: database.py (Async SQLite Manager via aiosqlite)
================================================================================
"""

import aiosqlite
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger("kushida.database")


class DatabaseManager:
    """
    High-performance, asynchronous SQLite database manager.
    Handles user profiles, listening history, Spotify OAuth tokens, and vibe matching stats.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initialize database schema with required tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

            # 1. Users & Spotify Auth Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    spotify_access_token TEXT,
                    spotify_refresh_token TEXT,
                    spotify_expires_at REAL,
                    spotify_user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Listening History Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS listening_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    track_title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    uri TEXT,
                    duration_ms INTEGER DEFAULT 0,
                    played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Guild Settings Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    default_volume INTEGER DEFAULT 100,
                    last_text_channel_id INTEGER,
                    persistent_panel_id INTEGER,
                    prefix TEXT DEFAULT '-',
                    mode_247 INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Ensure columns exist if table was already created
            try:
                await db.execute("ALTER TABLE guild_settings ADD COLUMN prefix TEXT DEFAULT '-';")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE guild_settings ADD COLUMN mode_247 INTEGER DEFAULT 0;")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE guild_settings ADD COLUMN voice_channel_id INTEGER;")
            except Exception:
                pass

            # Indexes for ultra-fast queries and VibeMatch analytics
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_user ON listening_history(user_id);
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_guild ON listening_history(guild_id);
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_artist ON listening_history(artist);
            """)

            await db.commit()
            logger.info("Database schema initialized successfully.")

    # --------------------------------------------------------------------------
    # LISTENING HISTORY METHODS
    # --------------------------------------------------------------------------
    async def log_listen(
        self,
        user_id: int,
        guild_id: int,
        track_title: str,
        artist: str,
        uri: Optional[str] = None,
        duration_ms: int = 0
    ) -> None:
        """Record a played track into listening history."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO listening_history (user_id, guild_id, track_title, artist, uri, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, guild_id, track_title, artist, uri or "", duration_ms)
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log listen for user {user_id}: {e}")

    async def get_user_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent tracks played by a user."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT track_title, artist, uri, duration_ms, played_at
                FROM listening_history
                WHERE user_id = ?
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_guild_top_artists(self, guild_id: int, limit: int = 10) -> List[Tuple[str, int]]:
        """Return the most listened artists in a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT artist, COUNT(*) as play_count
                FROM listening_history
                WHERE guild_id = ? AND artist != 'Unknown Artist' AND artist != ''
                GROUP BY artist
                ORDER BY play_count DESC
                LIMIT ?
                """,
                (guild_id, limit)
            )
            return await cursor.fetchall()

    # --------------------------------------------------------------------------
    # SPOTIFY OAUTH TOKEN METHODS
    # --------------------------------------------------------------------------
    async def save_spotify_token(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: float,
        spotify_user_id: Optional[str] = None
    ) -> None:
        """Store or update a user's Spotify OAuth credentials."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, spotify_access_token, spotify_refresh_token, spotify_expires_at, spotify_user_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    spotify_access_token = excluded.spotify_access_token,
                    spotify_refresh_token = excluded.spotify_refresh_token,
                    spotify_expires_at = excluded.spotify_expires_at,
                    spotify_user_id = COALESCE(excluded.spotify_user_id, users.spotify_user_id),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, access_token, refresh_token, expires_at, spotify_user_id)
            )
            await db.commit()
            logger.info(f"Updated Spotify credentials for user {user_id}")

    async def get_spotify_token(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a user's Spotify OAuth credentials."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT user_id, spotify_access_token, spotify_refresh_token, spotify_expires_at, spotify_user_id
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            if row and row["spotify_access_token"]:
                return dict(row)
            return None

    # --------------------------------------------------------------------------
    # GUILD SETTINGS METHODS
    # --------------------------------------------------------------------------
    async def set_panel_message_id(self, guild_id: int, channel_id: int, message_id: int) -> None:
        """Save persistent panel message coordinates."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO guild_settings (guild_id, last_text_channel_id, persistent_panel_id, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    last_text_channel_id = excluded.last_text_channel_id,
                    persistent_panel_id = excluded.persistent_panel_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (guild_id, channel_id, message_id)
            )
            await db.commit()

    async def get_panel_message_id(self, guild_id: int) -> Optional[Tuple[int, int]]:
        """Get (channel_id, message_id) of the guild's persistent music panel."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT last_text_channel_id, persistent_panel_id FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            if row and row[0] and row[1]:
                return (row[0], row[1])
            return None

    # --------------------------------------------------------------------------
    # GUILD PREFIX & 24/7 SETTINGS
    # --------------------------------------------------------------------------
    async def get_guild_prefix(self, guild_id: int) -> str:
        """Fetch custom command prefix for a guild (defaults to '-')."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT prefix FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            logger.error(f"Error fetching prefix for guild {guild_id}: {e}")
        return "-"

    async def set_guild_prefix(self, guild_id: int, prefix: str) -> None:
        """Save custom command prefix for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, prefix)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    prefix = excluded.prefix,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, prefix))
            await db.commit()

    async def get_guild_247(self, guild_id: int) -> bool:
        """Check if 24/7 mode is enabled for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT mode_247 FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row and row[0] is not None:
                    return bool(row[0])
        except Exception as e:
            logger.error(f"Error fetching 247 mode for guild {guild_id}: {e}")
        return False

    async def set_guild_247(self, guild_id: int, enabled: bool) -> None:
        """Enable or disable 24/7 mode for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, mode_247)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    mode_247 = excluded.mode_247,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, 1 if enabled else 0))
            await db.commit()

    async def get_guild_247_channel(self, guild_id: int) -> Optional[int]:
        """Fetch saved 24/7 voice channel ID for a guild."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT voice_channel_id FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            logger.error(f"Error fetching 247 voice channel for guild {guild_id}: {e}")
        return None

    async def set_guild_247_channel(self, guild_id: int, channel_id: Optional[int]) -> None:
        """Save active 24/7 voice channel ID for a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, voice_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    voice_channel_id = excluded.voice_channel_id,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, channel_id))
            await db.commit()

    # --------------------------------------------------------------------------
    # SOCIAL VIBEMATCH ANALYTICS
    # --------------------------------------------------------------------------
    async def calculate_vibe_match(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze listening history in the guild to find the pair of users with
        the highest musical vibe compatibility (Cosine similarity over artist vectors).
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Fetch all user-artist listen counts in this guild
            cursor = await db.execute(
                """
                SELECT user_id, artist, COUNT(*) as count
                FROM listening_history
                WHERE guild_id = ? AND artist != '' AND artist != 'Unknown Artist'
                GROUP BY user_id, artist
                """,
                (guild_id,)
            )
            rows = await cursor.fetchall()

            if not rows:
                return None

            # Build user -> {artist: count} profile
            user_profiles: Dict[int, Dict[str, int]] = {}
            for user_id, artist, count in rows:
                if user_id not in user_profiles:
                    user_profiles[user_id] = {}
                user_profiles[user_id][artist] = count

            users = list(user_profiles.keys())
            if len(users) < 2:
                return None

            # Calculate pairwise Cosine similarity
            import math

            best_score = -1.0
            best_pair = (users[0], users[1])
            shared_artists_best: List[str] = []

            for i in range(len(users)):
                for j in range(i + 1, len(users)):
                    u1, u2 = users[i], users[j]
                    p1, p2 = user_profiles[u1], user_profiles[u2]

                    # All unique artists
                    all_artists = set(p1.keys()).union(set(p2.keys()))
                    dot_product = 0.0
                    mag1 = 0.0
                    mag2 = 0.0

                    shared = []
                    for artist in all_artists:
                        v1 = p1.get(artist, 0)
                        v2 = p2.get(artist, 0)
                        dot_product += v1 * v2
                        mag1 += v1 * v1
                        mag2 += v2 * v2
                        if v1 > 0 and v2 > 0:
                            shared.append(artist)

                    if mag1 > 0 and mag2 > 0:
                        similarity = dot_product / (math.sqrt(mag1) * math.sqrt(mag2))
                        if similarity > best_score:
                            best_score = similarity
                            best_pair = (u1, u2)
                            shared_artists_best = shared

            if best_score <= 0.0:
                return None

            return {
                "user_1": best_pair[0],
                "user_2": best_pair[1],
                "match_percentage": round(best_score * 100, 1),
                "shared_artists": shared_artists_best[:5]
            }


# Singleton database instance
db_manager = DatabaseManager()
