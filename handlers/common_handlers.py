import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database.repositories import UserRepository, ConfigRepository

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command, including deep link for joining Random Coffee."""

    user = update.effective_user

    # Check if this is a deep link with "join" parameter
    if context.args and context.args[0] == "join":
        await _handle_join(update, context, user)
        return

    # Regular /start - show welcome message
    message = (
        "☕️ Welcome to DVC Random Coffee!\n\n"
        "I help connect our community through meaningful 1-on-1 conversations.\n\n"
        "If you're here to join, click the button in your group chat!\n\n"
        "For admins: Use /setup in a group to get started."
    )
    await update.message.reply_text(message)


async def _handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    """Handle join deep link - subscribe user to Random Coffee."""

    # Create or update user
    db_user = await UserRepository.create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # Check if already subscribed
    if db_user and db_user.is_subscribed:
        keyboard = [[InlineKeyboardButton("Leave Random Coffee", callback_data="leave_coffee")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"Hey {user.first_name}! 👋\n\n"
            "You're already part of DVC Random Coffee.\n\n"
            "Sit tight — your next match will arrive on the 1st of the month!\n\n"
            "If you'd like to opt out, click below.",
            reply_markup=reply_markup
        )
        return

    # Subscribe the user
    await UserRepository.subscribe_user(user.id)
    await UserRepository.set_can_receive_dm(user.id, True)

    subscriber_count = await UserRepository.get_subscriber_count()

    # Update the group message with new count
    await _update_group_message(context, subscriber_count)

    keyboard = [[InlineKeyboardButton("Leave Random Coffee", callback_data="leave_coffee")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎉 You're in, {user.first_name}!\n\n"
        f"Welcome to DVC Random Coffee. On the 1st of each month, "
        f"I'll send you your match right here.\n\n"
        f"Get ready to meet someone new from our community!\n\n"
        f"☕️ {subscriber_count} members joined so far",
        reply_markup=reply_markup
    )


async def _update_group_message(context: ContextTypes.DEFAULT_TYPE, subscriber_count: int):
    """Update the join message in the group with new participant count."""
    config = await ConfigRepository.get_config()
    if not config or not config.info_message_id or not config.bot_username:
        return

    keyboard = [[InlineKeyboardButton(
        f"☕️ Join Random Coffee ({subscriber_count} joined)" if subscriber_count > 0 else "☕️ Join Random Coffee",
        url=f"https://t.me/{config.bot_username}?start=join"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.edit_message_reply_markup(
            chat_id=config.group_chat_id,
            message_id=config.info_message_id,
            reply_markup=reply_markup
        )
    except BadRequest as e:
        logger.warning(f"Could not update group message: {e}")
