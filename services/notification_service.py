import logging
from typing import List, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest
from database.models import User, Match
from database.repositories import UserRepository

logger = logging.getLogger(__name__)

PEOPLE_BOOK_URL = "https://platform.davidovs.com/people"


class NotificationService:
    @staticmethod
    def format_user_name(user: User) -> str:
        """Format user's display name."""
        name = user.first_name or "Someone"
        if user.last_name:
            name += f" {user.last_name}"
        return name

    @staticmethod
    def format_user_mention(user: User) -> str:
        """Format user mention with username if available."""
        name = NotificationService.format_user_name(user)
        if user.username:
            return f"{name} (@{user.username})"
        return name

    @staticmethod
    async def send_match_notification(
        bot: Bot,
        user: User,
        match_partners: List[User],
        month_name: str,
        match_id: int
    ) -> bool:
        """Send match notification to a user."""
        if len(match_partners) == 1:
            partner = match_partners[0]
            message = (
                f"☕️ Your {month_name} Coffee Match is here!\n\n"
                f"Hey {user.first_name}! You've been matched with:\n\n"
                f"👤 {NotificationService.format_user_mention(partner)}\n\n"
                f"Learn more about them in People Book:\n{PEOPLE_BOOK_URL}\n\n"
                f"Reach out and schedule your chat — new connections start with one conversation! 💛"
            )
        else:
            partners_text = "\n".join(
                f"👤 {NotificationService.format_user_mention(p)}"
                for p in match_partners
            )
            message = (
                f"☕️ Your {month_name} Coffee Match is here!\n\n"
                f"Hey {user.first_name}! You're in a group of 3 this month:\n\n"
                f"{partners_text}\n\n"
                f"Learn more about them in People Book:\n{PEOPLE_BOOK_URL}\n\n"
                f"Schedule a group chat — great conversations often start as three! 💛"
            )

        keyboard = [[
            InlineKeyboardButton(
                "Request Different Match",
                callback_data=f"request_rematch_{match_id}"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=message,
                reply_markup=reply_markup
            )
            return True
        except Forbidden:
            logger.warning(f"User {user.user_id} has blocked the bot")
            await UserRepository.set_can_receive_dm(user.user_id, False)
            return False
        except BadRequest as e:
            logger.error(f"Failed to send DM to {user.user_id}: {e}")
            return False

    @staticmethod
    async def send_followup_question(
        bot: Bot,
        user: User,
        partner_name: str,
        match_id: int
    ) -> bool:
        """Send follow-up question to a user."""
        message = (
            f"👋 Hey {user.first_name}!\n\n"
            f"Did you get a chance to connect with {partner_name} for your Random Coffee chat?"
        )

        keyboard = [
            [
                InlineKeyboardButton("Yes, we met! ✅", callback_data=f"followup_yes_{match_id}"),
                InlineKeyboardButton("Not yet ❌", callback_data=f"followup_no_{match_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await bot.send_message(
                chat_id=user.user_id,
                text=message,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to send follow-up to {user.user_id}: {e}")
            return False

    @staticmethod
    async def send_removal_notification(bot: Bot, user: User) -> bool:
        """Notify user they've been removed due to inactivity."""
        message = (
            f"👋 Hey {user.first_name},\n\n"
            "We noticed you haven't been able to connect for the past 3 months, "
            "so we've paused your Random Coffee matches.\n\n"
            "No worries — you can rejoin anytime from the group chat when you're ready!\n\n"
            "See you soon ☕️"
        )

        try:
            await bot.send_message(chat_id=user.user_id, text=message)
            return True
        except (Forbidden, BadRequest):
            return False

    @staticmethod
    async def send_rematch_confirmation(
        bot: Bot,
        user: User,
        new_partner: User
    ) -> bool:
        """Notify user about their new match after rematch."""
        message = (
            f"🔄 Good news, {user.first_name}!\n\n"
            f"You've been rematched with:\n\n"
            f"👤 {NotificationService.format_user_mention(new_partner)}\n\n"
            f"Learn more about them in People Book:\n{PEOPLE_BOOK_URL}\n\n"
            f"Enjoy your coffee chat! ☕️"
        )

        try:
            await bot.send_message(chat_id=user.user_id, text=message)
            return True
        except (Forbidden, BadRequest):
            return False
