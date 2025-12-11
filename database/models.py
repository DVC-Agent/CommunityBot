from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_subscribed: bool = False
    subscribed_at: Optional[datetime] = None
    can_receive_dm: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Config:
    id: int
    group_chat_id: int
    info_message_id: Optional[int] = None
    message_thread_id: Optional[int] = None
    bot_username: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class MatchingRound:
    id: int
    month_year: str
    executed_at: Optional[datetime] = None
    total_subscribers: int = 0
    total_pairs: int = 0


@dataclass
class Match:
    id: int
    round_id: int
    user1_id: int
    user2_id: int
    user3_id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class MatchHistory:
    id: int
    user_id_1: int
    user_id_2: int
    match_date: datetime
    round_id: Optional[int] = None


@dataclass
class FollowUp:
    id: int
    match_id: int
    user_id: int
    question_sent_at: Optional[datetime] = None
    response: Optional[str] = None
    responded_at: Optional[datetime] = None


@dataclass
class MeetingStreak:
    user_id: int
    consecutive_misses: int = 0
    last_updated_month: Optional[str] = None
