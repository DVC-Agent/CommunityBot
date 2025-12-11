from typing import Optional, List
from datetime import datetime
from database.connection import get_db
from database.models import User


class UserRepository:
    @staticmethod
    async def get_user(user_id: int) -> Optional[User]:
        """Get user by ID."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return User(
                user_id=row['user_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                is_subscribed=bool(row['is_subscribed']),
                subscribed_at=row['subscribed_at'],
                can_receive_dm=bool(row['can_receive_dm']),
                created_at=row['created_at']
            )
        return None

    @staticmethod
    async def create_or_update_user(
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Create or update a user."""
        db = await get_db()
        await db.execute('''
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, users.username),
                first_name = COALESCE(excluded.first_name, users.first_name),
                last_name = COALESCE(excluded.last_name, users.last_name)
        ''', (user_id, username, first_name, last_name))
        await db.commit()
        return await UserRepository.get_user(user_id)

    @staticmethod
    async def subscribe_user(user_id: int) -> bool:
        """Subscribe a user to Random Coffee."""
        db = await get_db()
        await db.execute('''
            UPDATE users
            SET is_subscribed = TRUE, subscribed_at = ?
            WHERE user_id = ?
        ''', (datetime.now().isoformat(), user_id))
        await db.commit()
        return True

    @staticmethod
    async def unsubscribe_user(user_id: int) -> bool:
        """Unsubscribe a user from Random Coffee."""
        db = await get_db()
        await db.execute('''
            UPDATE users
            SET is_subscribed = FALSE
            WHERE user_id = ?
        ''', (user_id,))
        await db.commit()
        return True

    @staticmethod
    async def get_all_subscribers() -> List[User]:
        """Get all subscribed users."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM users WHERE is_subscribed = TRUE'
        )
        rows = await cursor.fetchall()
        return [
            User(
                user_id=row['user_id'],
                username=row['username'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                is_subscribed=bool(row['is_subscribed']),
                subscribed_at=row['subscribed_at'],
                can_receive_dm=bool(row['can_receive_dm']),
                created_at=row['created_at']
            )
            for row in rows
        ]

    @staticmethod
    async def get_subscriber_count() -> int:
        """Get count of subscribed users."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT COUNT(*) as count FROM users WHERE is_subscribed = TRUE'
        )
        row = await cursor.fetchone()
        return row['count'] if row else 0

    @staticmethod
    async def set_can_receive_dm(user_id: int, can_receive: bool):
        """Update user's DM capability."""
        db = await get_db()
        await db.execute(
            'UPDATE users SET can_receive_dm = ? WHERE user_id = ?',
            (can_receive, user_id)
        )
        await db.commit()
