import logging
from datetime import datetime
from telegram import Bot
from database.repositories import UserRepository, FollowUpRepository
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

INACTIVITY_THRESHOLD = 3  # Consecutive misses before removal


class InactivityService:
    @staticmethod
    async def process_followup_response(user_id: int, response: str) -> None:
        """Process a follow-up response and update streak."""
        month_year = datetime.now().strftime("%Y-%m")

        if response == 'yes':
            await FollowUpRepository.reset_streak(user_id, month_year)
            logger.info(f"User {user_id} met their match - streak reset")
        else:
            await FollowUpRepository.increment_miss(user_id, month_year)
            streak = await FollowUpRepository.get_streak(user_id)
            logger.info(f"User {user_id} missed meeting - consecutive misses: {streak.consecutive_misses if streak else 1}")

    @staticmethod
    async def check_and_remove_inactive(bot: Bot) -> dict:
        """Check for inactive users and remove them."""
        inactive_user_ids = await FollowUpRepository.get_inactive_users(INACTIVITY_THRESHOLD)

        removed = 0
        notified = 0

        for user_id in inactive_user_ids:
            user = await UserRepository.get_user(user_id)
            if not user:
                continue

            # Remove from subscribers
            await UserRepository.unsubscribe_user(user_id)
            removed += 1

            # Reset their streak
            await FollowUpRepository.reset_streak(user_id, datetime.now().strftime("%Y-%m"))

            # Send notification
            if await NotificationService.send_removal_notification(bot, user):
                notified += 1

            logger.info(f"Removed inactive user {user_id}")

        return {
            'removed': removed,
            'notified': notified
        }

    @staticmethod
    async def process_unanswered_followups() -> int:
        """Process follow-ups that weren't answered (assume 'no')."""
        unanswered = await FollowUpRepository.get_unanswered_followups()
        processed = 0

        for followup in unanswered:
            await FollowUpRepository.record_response(
                followup.match_id,
                followup.user_id,
                'no'  # Assume no meeting
            )
            await InactivityService.process_followup_response(followup.user_id, 'no')
            processed += 1
            logger.info(f"Auto-marked follow-up as 'no' for user {followup.user_id}")

        return processed
