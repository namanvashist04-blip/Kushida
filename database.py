"""
================================================================================
  DEMON MUSIC — LUXURY DISCORD MUSIC ARCHITECTURE
  MODULE: database.py (Async SQLite Manager via aiosqlite)
================================================================================
"""

import aiosqlite
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from config import DB_PATH

logger = logging.getLogger("demon.database")


class DatabaseManager:
    """
    High-performance, asynchronous SQLite database manager.
    Handles user profiles, listening history, custom playlists, DJ roles, 24/7 mode, and Top.gg voting.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        """Initialize database schema with required tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA synchronous=NORMAL;")

            # 1. Users Table
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
                    voice_channel_id INTEGER,
                    text_channel_id INTEGER,
                    dj_roles TEXT DEFAULT '[]',
                    dj_only INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migrations for guild_settings
            cols_to_add = [
                ("prefix", "TEXT DEFAULT '-'"),
                ("mode_247", "INTEGER DEFAULT 0"),
                ("voice_channel_id", "INTEGER"),
                ("text_channel_id", "INTEGER"),
                ("dj_roles", "TEXT DEFAULT '[]'"),
                ("dj_only", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in cols_to_add:
                try:
                    await db.execute(f"ALTER TABLE guild_settings ADD COLUMN {col_name} {col_type};")
                except Exception:
                    pass

            # 4. Custom Playlists Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS custom_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    tracks TEXT NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 5. User Votes Table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_votes (
                    user_id INTEGER PRIMARY KEY,
                    last_voted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_votes INTEGER DEFAULT 1
                );
            """)

            # Indexes for ultra-fast queries
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON listening_history(user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_guild ON listening_history(guild_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_history_artist ON listening_history(artist);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pl_user ON custom_playlists(user_id);")

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

    async def get_guild_history(self, guild_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent tracks played in a guild."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT track_title, artist, uri, duration_ms, played_at
                FROM listening_history
                WHERE guild_id = ?
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (guild_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_guild_stats(self, guild_id: int) -> Dict[str, Any]:
        """Get stats for /server-profile."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM listening_history WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()
            total_songs = row[0] if row else 0

            cursor = await db.execute(
                "SELECT mode_247, dj_roles FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            settings_row = await cursor.fetchone()
            mode_247 = bool(settings_row[0]) if settings_row and settings_row[0] else False
            dj_roles = json.loads(settings_row[1]) if settings_row and settings_row[1] else []

            return {
                "total_songs_played": total_songs,
                "mode_247": mode_247,
                "dj_role_count": len(dj_roles)
            }

    # --------------------------------------------------------------------------
    # GUILD SETTINGS & DJ
    # --------------------------------------------------------------------------
    async def get_guild_prefix(self, guild_id: int) -> str:
        """Fetch command prefix for a guild (defaults to '-')."""
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
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, voice_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    voice_channel_id = excluded.voice_channel_id,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, channel_id))
            await db.commit()

    async def get_dj_roles(self, guild_id: int) -> List[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT dj_roles FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row and row[0]:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Error fetching dj roles for guild {guild_id}: {e}")
        return []

    async def add_dj_role(self, guild_id: int, role_id: int) -> bool:
        roles = await self.get_dj_roles(guild_id)
        if role_id in roles:
            return False
        roles.append(role_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, dj_roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    dj_roles = excluded.dj_roles,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, json.dumps(roles)))
            await db.commit()
        return True

    async def remove_dj_role(self, guild_id: int, role_id: int) -> bool:
        roles = await self.get_dj_roles(guild_id)
        if role_id not in roles:
            return False
        roles.remove(role_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, dj_roles)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    dj_roles = excluded.dj_roles,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, json.dumps(roles)))
            await db.commit()
        return True

    async def get_dj_only(self, guild_id: int) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("SELECT dj_only FROM guild_settings WHERE guild_id = ?", (guild_id,))
                row = await cursor.fetchone()
                if row and row[0] is not None:
                    return bool(row[0])
        except Exception as e:
            logger.error(f"Error fetching dj_only for guild {guild_id}: {e}")
        return False

    async def set_dj_only(self, guild_id: int, enabled: bool) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO guild_settings (guild_id, dj_only)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    dj_only = excluded.dj_only,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, 1 if enabled else 0))
            await db.commit()

    async def set_panel_message_id(self, guild_id: int, channel_id: int, message_id: int) -> None:
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
    # CUSTOM PLAYLISTS METHODS
    # --------------------------------------------------------------------------
    async def create_playlist(self, user_id: int, name: str) -> bool:
        """Create a new personal playlist. Returns False if already exists."""
        clean_name = name.strip()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM custom_playlists WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                (user_id, clean_name)
            )
            if await cursor.fetchone():
                return False
            await db.execute(
                "INSERT INTO custom_playlists (user_id, name, tracks) VALUES (?, ?, '[]')",
                (user_id, clean_name)
            )
            await db.commit()
            return True

    async def delete_playlist(self, user_id: int, name: str) -> bool:
        """Delete playlist by name."""
        clean_name = name.strip()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM custom_playlists WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                (user_id, clean_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_user_playlists(self, user_id: int) -> List[Dict[str, Any]]:
        """List all playlists owned by user."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, name, tracks, created_at FROM custom_playlists WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            res = []
            for r in rows:
                tracks = json.loads(r["tracks"])
                res.append({
                    "id": r["id"],
                    "name": r["name"],
                    "track_count": len(tracks),
                    "created_at": r["created_at"]
                })
            return res

    async def get_playlist(self, user_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Get full playlist with all tracks."""
        clean_name = name.strip()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, name, tracks, created_at FROM custom_playlists WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                (user_id, clean_name)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "name": row["name"],
                "tracks": json.loads(row["tracks"]),
                "created_at": row["created_at"]
            }

    async def add_track_to_playlist(self, user_id: int, name: str, track: Dict[str, Any]) -> bool:
        """Append a track dict {title, uri, author, duration} to playlist."""
        clean_name = name.strip()
        pl = await self.get_playlist(user_id, clean_name)
        if not pl:
            return False
        tracks = pl["tracks"]
        tracks.append(track)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE custom_playlists SET tracks = ? WHERE id = ?",
                (json.dumps(tracks), pl["id"])
            )
            await db.commit()
            return True

    async def add_tracks_to_playlist(self, user_id: int, name: str, new_tracks: List[Dict[str, Any]]) -> Tuple[bool, int]:
        """Append multiple track dicts to playlist."""
        clean_name = name.strip()
        pl = await self.get_playlist(user_id, clean_name)
        if not pl:
            return False, 0
        tracks = pl["tracks"]
        tracks.extend(new_tracks)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE custom_playlists SET tracks = ? WHERE id = ?",
                (json.dumps(tracks), pl["id"])
            )
            await db.commit()
            return True, len(new_tracks)

    async def remove_track_from_playlist(self, user_id: int, name: str, index: int) -> Optional[Dict[str, Any]]:
        """Remove track at 1-based index."""
        clean_name = name.strip()
        pl = await self.get_playlist(user_id, clean_name)
        if not pl:
            return None
        tracks = pl["tracks"]
        if index < 1 or index > len(tracks):
            return None
        removed = tracks.pop(index - 1)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE custom_playlists SET tracks = ? WHERE id = ?",
                (json.dumps(tracks), pl["id"])
            )
            await db.commit()
            return removed

    async def remove_duplicates_from_playlist(self, user_id: int, name: str) -> int:
        """Remove duplicate tracks based on URI and title. Returns count of removed items."""
        clean_name = name.strip()
        pl = await self.get_playlist(user_id, clean_name)
        if not pl:
            return 0
        tracks = pl["tracks"]
        unique_tracks = []
        seen_keys = set()
        removed_count = 0
        for t in tracks:
            key = t.get("uri") or t.get("title", "")
            if key in seen_keys:
                removed_count += 1
            else:
                seen_keys.add(key)
                unique_tracks.append(t)
        if removed_count > 0:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE custom_playlists SET tracks = ? WHERE id = ?",
                    (json.dumps(unique_tracks), pl["id"])
                )
                await db.commit()
        return removed_count

    # --------------------------------------------------------------------------
    # TOP.GG VOTING & USER PROFILE
    # --------------------------------------------------------------------------
    async def record_vote(self, user_id: int) -> None:
        """Record or update a user's vote."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_votes (user_id, last_voted, total_votes)
                VALUES (?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_voted = CURRENT_TIMESTAMP,
                    total_votes = user_votes.total_votes + 1
            """, (user_id,))
            await db.commit()

    async def check_vote(self, user_id: int) -> Tuple[bool, Optional[str], int]:
        """Check if user has voted within 12 hours. Returns (is_active, last_voted, total_votes)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT last_voted, total_votes FROM user_votes WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return False, None, 0
            last_voted_str, total_votes = row[0], row[1]
            try:
                last_voted = datetime.fromisoformat(last_voted_str.replace(" ", "T"))
                is_active = (datetime.utcnow() - last_voted) < timedelta(hours=12)
                return is_active, last_voted_str, total_votes
            except Exception:
                return False, last_voted_str, total_votes

    async def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """Get stats for /user-profile."""
        is_active, last_voted, total_votes = await self.check_vote(user_id)
        playlists = await self.get_user_playlists(user_id)
        history = await self.get_user_history(user_id, limit=5)
        return {
            "user_id": user_id,
            "has_active_vote": is_active,
            "total_votes": total_votes,
            "playlist_count": len(playlists),
            "recent_tracks": history
        }


# Singleton database instance
db_manager = DatabaseManager()
