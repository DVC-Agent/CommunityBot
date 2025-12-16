import logging
from typing import Optional, List, Set, Tuple
from datetime import datetime
from database.connection import get_db
from database.models import Match, MatchingRound, MatchHistory

logger = logging.getLogger(__name__)


class MatchRepository:
    @staticmethod
    async def create_round(month_year: str, total_subscribers: int, total_pairs: int) -> MatchingRound:
        """Create a new matching round."""
        db = await get_db()
        cursor = await db.execute('''
            INSERT INTO matching_rounds (month_year, total_subscribers, total_pairs)
            VALUES (?, ?, ?)
        ''', (month_year, total_subscribers, total_pairs))
        await db.commit()
        return MatchingRound(
            id=cursor.lastrowid,
            month_year=month_year,
            total_subscribers=total_subscribers,
            total_pairs=total_pairs
        )

    @staticmethod
    async def create_round_atomic(month_year: str) -> Optional[MatchingRound]:
        """
        Atomically create a round if it doesn't exist.
        Returns the new round if created, None if already exists.
        Uses INSERT OR IGNORE for atomic check-and-insert.
        """
        db = await get_db()
        cursor = await db.execute('''
            INSERT OR IGNORE INTO matching_rounds (month_year, total_subscribers, total_pairs)
            VALUES (?, 0, 0)
        ''', (month_year,))
        await db.commit()

        if cursor.rowcount == 0:
            # Round already existed
            logger.info(f"Matching round for {month_year} already exists")
            return None

        # Get the newly created round
        round_obj = await MatchRepository.get_current_round(month_year)
        logger.info(f"Created new matching round for {month_year} with id {round_obj.id}")
        return round_obj

    @staticmethod
    async def update_round_stats(round_id: int, total_subscribers: int, total_pairs: int):
        """Update the stats for a matching round."""
        db = await get_db()
        await db.execute('''
            UPDATE matching_rounds SET total_subscribers = ?, total_pairs = ?
            WHERE id = ?
        ''', (total_subscribers, total_pairs, round_id))
        await db.commit()

    @staticmethod
    async def get_current_round(month_year: str) -> Optional[MatchingRound]:
        """Get the round for a specific month."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM matching_rounds WHERE month_year = ?',
            (month_year,)
        )
        row = await cursor.fetchone()
        if row:
            return MatchingRound(
                id=row['id'],
                month_year=row['month_year'],
                executed_at=row['executed_at'],
                total_subscribers=row['total_subscribers'],
                total_pairs=row['total_pairs']
            )
        return None

    @staticmethod
    async def get_latest_round() -> Optional[MatchingRound]:
        """Get the most recent matching round."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM matching_rounds ORDER BY executed_at DESC LIMIT 1'
        )
        row = await cursor.fetchone()
        if row:
            return MatchingRound(
                id=row['id'],
                month_year=row['month_year'],
                executed_at=row['executed_at'],
                total_subscribers=row['total_subscribers'],
                total_pairs=row['total_pairs']
            )
        return None

    @staticmethod
    async def create_match(
        round_id: int,
        user1_id: int,
        user2_id: int,
        user3_id: Optional[int] = None
    ) -> Match:
        """Create a match within a round."""
        db = await get_db()
        cursor = await db.execute('''
            INSERT INTO matches (round_id, user1_id, user2_id, user3_id)
            VALUES (?, ?, ?, ?)
        ''', (round_id, user1_id, user2_id, user3_id))
        await db.commit()
        return Match(
            id=cursor.lastrowid,
            round_id=round_id,
            user1_id=user1_id,
            user2_id=user2_id,
            user3_id=user3_id
        )

    @staticmethod
    async def get_matches_for_round(round_id: int) -> List[Match]:
        """Get all matches for a round."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM matches WHERE round_id = ?',
            (round_id,)
        )
        rows = await cursor.fetchall()
        return [
            Match(
                id=row['id'],
                round_id=row['round_id'],
                user1_id=row['user1_id'],
                user2_id=row['user2_id'],
                user3_id=row['user3_id'],
                created_at=row['created_at']
            )
            for row in rows
        ]

    @staticmethod
    async def get_match_by_id(match_id: int) -> Optional[Match]:
        """Get a match by ID."""
        db = await get_db()
        cursor = await db.execute(
            'SELECT * FROM matches WHERE id = ?',
            (match_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Match(
                id=row['id'],
                round_id=row['round_id'],
                user1_id=row['user1_id'],
                user2_id=row['user2_id'],
                user3_id=row['user3_id'],
                created_at=row['created_at']
            )
        return None

    @staticmethod
    async def add_to_history(user_id_1: int, user_id_2: int, round_id: int):
        """Add a pair to match history (always store with smaller ID first)."""
        db = await get_db()
        # Ensure consistent ordering
        if user_id_1 > user_id_2:
            user_id_1, user_id_2 = user_id_2, user_id_1
        await db.execute('''
            INSERT OR IGNORE INTO match_history (user_id_1, user_id_2, match_date, round_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id_1, user_id_2, datetime.now().date().isoformat(), round_id))
        await db.commit()

    @staticmethod
    async def get_historical_pairs() -> Set[Tuple[int, int]]:
        """Get all historical pairs as a set of tuples."""
        db = await get_db()
        cursor = await db.execute('SELECT user_id_1, user_id_2 FROM match_history')
        rows = await cursor.fetchall()
        return {(row['user_id_1'], row['user_id_2']) for row in rows}

    @staticmethod
    async def have_been_matched(user_id_1: int, user_id_2: int) -> bool:
        """Check if two users have been matched before."""
        # Ensure consistent ordering
        if user_id_1 > user_id_2:
            user_id_1, user_id_2 = user_id_2, user_id_1
        db = await get_db()
        cursor = await db.execute('''
            SELECT 1 FROM match_history
            WHERE user_id_1 = ? AND user_id_2 = ?
            LIMIT 1
        ''', (user_id_1, user_id_2))
        row = await cursor.fetchone()
        return row is not None

    @staticmethod
    async def get_user_match_for_round(user_id: int, round_id: int) -> Optional[Match]:
        """Get the match for a specific user in a round."""
        db = await get_db()
        cursor = await db.execute('''
            SELECT * FROM matches
            WHERE round_id = ?
            AND (user1_id = ? OR user2_id = ? OR user3_id = ?)
        ''', (round_id, user_id, user_id, user_id))
        row = await cursor.fetchone()
        if row:
            return Match(
                id=row['id'],
                round_id=row['round_id'],
                user1_id=row['user1_id'],
                user2_id=row['user2_id'],
                user3_id=row['user3_id'],
                created_at=row['created_at']
            )
        return None
