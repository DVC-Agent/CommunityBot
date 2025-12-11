import aiosqlite
import os
from typing import Optional

DATABASE_PATH = os.getenv('DATABASE_PATH', './random_coffee.db')

_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Get or create database connection."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DATABASE_PATH)
        _db.row_factory = aiosqlite.Row
    return _db


async def close_db():
    """Close database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def init_db():
    """Initialize database with schema."""
    db = await get_db()

    await db.executescript('''
        -- Bot configuration (single row for single community)
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY DEFAULT 1,
            group_chat_id INTEGER NOT NULL,
            info_message_id INTEGER,
            message_thread_id INTEGER,
            bot_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (id = 1)
        );

        -- Users who have interacted with the bot
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_subscribed BOOLEAN DEFAULT FALSE,
            subscribed_at TIMESTAMP,
            can_receive_dm BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Monthly matching rounds
        CREATE TABLE IF NOT EXISTS matching_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_subscribers INTEGER DEFAULT 0,
            total_pairs INTEGER DEFAULT 0
        );

        -- Individual matches within a round
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            round_id INTEGER NOT NULL,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            user3_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (round_id) REFERENCES matching_rounds(id),
            FOREIGN KEY (user1_id) REFERENCES users(user_id),
            FOREIGN KEY (user2_id) REFERENCES users(user_id),
            FOREIGN KEY (user3_id) REFERENCES users(user_id)
        );

        -- Historical record of all pairings (to prevent repeat matches)
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id_1 INTEGER NOT NULL,
            user_id_2 INTEGER NOT NULL,
            match_date DATE NOT NULL,
            round_id INTEGER,
            FOREIGN KEY (user_id_1) REFERENCES users(user_id),
            FOREIGN KEY (user_id_2) REFERENCES users(user_id),
            FOREIGN KEY (round_id) REFERENCES matching_rounds(id)
        );

        -- Index for faster history lookups
        CREATE INDEX IF NOT EXISTS idx_match_history_users
        ON match_history(user_id_1, user_id_2);

        -- Follow-up responses
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            question_sent_at TIMESTAMP,
            response TEXT,
            responded_at TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(match_id, user_id)
        );

        -- Tracking consecutive missed meetings for inactivity management
        CREATE TABLE IF NOT EXISTS meeting_streaks (
            user_id INTEGER PRIMARY KEY,
            consecutive_misses INTEGER DEFAULT 0,
            last_updated_month TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    ''')

    await db.commit()


class Database:
    """Context manager for database operations."""

    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None

    async def __aenter__(self) -> aiosqlite.Connection:
        self.db = await get_db()
        return self.db

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            await self.db.commit()
