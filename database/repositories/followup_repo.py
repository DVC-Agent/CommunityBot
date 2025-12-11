from typing import Optional, List
from datetime import datetime
from database.connection import get_db
from database.models import FollowUp, MeetingStreak


class FollowUpRepository:
    @staticmethod
    async def create_followup(match_id: int, user_id: int) -> FollowUp:
        """Create a follow-up record when question is sent."""
        db = await get_db()
        cursor = await db.execute('''
            INSERT INTO follow_ups (match_id, user_id, question_sent_at)
            VALUES (?, ?, ?)
            ON CONFLICT(match_id, user_id) DO UPDATE SET
                question_sent_at = excluded.question_sent_at
        ''', (match_id, user_id, datetime.now().isoformat()))
        await db.commit()
        return FollowUp(
            id=cursor.lastrowid,
            match_id=match_id,
            user_id=user_id,
            question_sent_at=datetime.now()
        )

    @staticmethod
    async def record_response(match_id: int, user_id: int, response: str):
        """Record user's response to follow-up."""
        db = await get_db()
        await db.execute('''
            UPDATE follow_ups
            SET response = ?, responded_at = ?
            WHERE match_id = ? AND user_id = ?
        ''', (response, datetime.now().isoformat(), match_id, user_id))
        await db.commit()

    @staticmethod
    async def get_followup(match_id: int, user_id: int) -> Optional[FollowUp]:
        """Get follow-up for a specific match and user."""
        db = await get_db()
        cursor = await db.execute('''
            SELECT * FROM follow_ups
            WHERE match_id = ? AND user_id = ?
        ''', (match_id, user_id))
        row = await cursor.fetchone()
        if row:
            return FollowUp(
                id=row['id'],
                match_id=row['match_id'],
                user_id=row['user_id'],
                question_sent_at=row['question_sent_at'],
                response=row['response'],
                responded_at=row['responded_at']
            )
        return None

    @staticmethod
    async def get_pending_followups_for_round(round_id: int) -> List[dict]:
        """Get matches that need follow-up (7+ days old, no question sent yet)."""
        db = await get_db()
        cursor = await db.execute('''
            SELECT m.id as match_id, m.user1_id, m.user2_id, m.user3_id, m.created_at
            FROM matches m
            WHERE m.round_id = ?
            AND datetime(m.created_at) <= datetime('now', '-7 days')
            AND NOT EXISTS (
                SELECT 1 FROM follow_ups f
                WHERE f.match_id = m.id
            )
        ''', (round_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    async def get_unanswered_followups() -> List[FollowUp]:
        """Get follow-ups that haven't been answered."""
        db = await get_db()
        cursor = await db.execute('''
            SELECT * FROM follow_ups
            WHERE response IS NULL
            AND datetime(question_sent_at) <= datetime('now', '-7 days')
        ''')
        rows = await cursor.fetchall()
        return [
            FollowUp(
                id=row['id'],
                match_id=row['match_id'],
                user_id=row['user_id'],
                question_sent_at=row['question_sent_at'],
                response=row['response'],
                responded_at=row['responded_at']
            )
            for row in rows
        ]

    # Meeting Streaks
    @staticmethod
    async def get_streak(user_id: int) -> Optional[MeetingStreak]:
        """Get user's meeting streak."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM meeting_streaks WHERE user_id = ?',
            (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return MeetingStreak(
                user_id=row['user_id'],
                consecutive_misses=row['consecutive_misses'],
                last_updated_month=row['last_updated_month']
            )
        return None

    @staticmethod
    async def increment_miss(user_id: int, month_year: str):
        """Increment consecutive misses for a user."""
        db = await get_db()
        await db.execute('''
            INSERT INTO meeting_streaks (user_id, consecutive_misses, last_updated_month)
            VALUES (?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                consecutive_misses = meeting_streaks.consecutive_misses + 1,
                last_updated_month = excluded.last_updated_month
        ''', (user_id, month_year))
        await db.commit()

    @staticmethod
    async def reset_streak(user_id: int, month_year: str):
        """Reset consecutive misses for a user (they met)."""
        db = await get_db()
        await db.execute('''
            INSERT INTO meeting_streaks (user_id, consecutive_misses, last_updated_month)
            VALUES (?, 0, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                consecutive_misses = 0,
                last_updated_month = excluded.last_updated_month
        ''', (user_id, month_year))
        await db.commit()

    @staticmethod
    async def get_inactive_users(threshold: int = 3) -> List[int]:
        """Get users with consecutive misses >= threshold."""
        db = await get_db()
        cursor = await db.execute('''
            SELECT ms.user_id
            FROM meeting_streaks ms
            JOIN users u ON ms.user_id = u.user_id
            WHERE ms.consecutive_misses >= ?
            AND u.is_subscribed = TRUE
        ''', (threshold,))
        rows = await cursor.fetchall()
        return [row['user_id'] for row in rows]
