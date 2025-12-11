from typing import Optional
from database.connection import get_db
from database.models import Config


class ConfigRepository:
    @staticmethod
    async def get_config() -> Optional[Config]:
        """Get the bot configuration."""
        db = await get_db()
        cursor = await db.execute('SELECT * FROM config WHERE id = 1')
        row = await cursor.fetchone()
        if row:
            return Config(
                id=row['id'],
                group_chat_id=row['group_chat_id'],
                info_message_id=row['info_message_id'],
                message_thread_id=row['message_thread_id'] if 'message_thread_id' in row.keys() else None,
                bot_username=row['bot_username'] if 'bot_username' in row.keys() else None,
                created_at=row['created_at']
            )
        return None

    @staticmethod
    async def set_config(
        group_chat_id: int,
        info_message_id: Optional[int] = None,
        message_thread_id: Optional[int] = None,
        bot_username: Optional[str] = None
    ) -> Config:
        """Set or update bot configuration."""
        db = await get_db()
        await db.execute('''
            INSERT INTO config (id, group_chat_id, info_message_id, message_thread_id, bot_username)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                group_chat_id = excluded.group_chat_id,
                info_message_id = COALESCE(excluded.info_message_id, config.info_message_id),
                message_thread_id = COALESCE(excluded.message_thread_id, config.message_thread_id),
                bot_username = COALESCE(excluded.bot_username, config.bot_username)
        ''', (group_chat_id, info_message_id, message_thread_id, bot_username))
        await db.commit()
        return Config(id=1, group_chat_id=group_chat_id, info_message_id=info_message_id)

    @staticmethod
    async def update_info_message(message_id: int, message_thread_id: Optional[int] = None):
        """Update the info message ID and thread ID."""
        db = await get_db()
        await db.execute(
            'UPDATE config SET info_message_id = ?, message_thread_id = ? WHERE id = 1',
            (message_id, message_thread_id)
        )
        await db.commit()
