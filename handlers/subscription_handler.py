import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import Forbidden, BadRequest
from database.repositories import UserRepository, ConfigRepository

logger = logging.getLogger(__name__)


async def _update_subscription_message(query, subscriber_count: int):
    """Update the subscription message with current participant count."""
    keyboard = [[InlineKeyboardButton(
        f"☕️ Join Random Coffee ({subscriber_count} joined)",
        callback_data="join_coffee"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            text=(
                "✨ DVC Random Coffee — Connecting Our Community ✨\n\n"
                "Every month, get matched with another DVC member for a casual chat.\n\n"
                "Click below to join and start making new connections!"
            ),
            reply_markup=reply_markup
        )
    except BadRequest as e:
        # Message not modified or already deleted - safe to ignore
        logger.debug(f"Could not update subscription message: {e}")


async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user joining/leaving Random Coffee."""
    query = update.callback_query
    user = query.from_user

    db_user = await UserRepository.create_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if db_user and db_user.is_subscribed:
        await UserRepository.unsubscribe_user(user.id)
        subscriber_count = await UserRepository.get_subscriber_count()
        await _update_subscription_message(query, subscriber_count)
        await query.answer("You've left Random Coffee")
        logger.info(f"User {user.id} ({user.username}) left Random Coffee")
        return

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                f"🎉 You're in, {user.first_name}!\n\n"
                "Welcome to DVC Random Coffee. On the 1st of each month, "
                "I'll send you your match right here.\n\n"
                "Get ready to meet someone new from our community!"
            )
        )
    except Forbidden:
        await query.answer(
            "Please start a chat with me first!\n\n"
            "1. Click on my name above\n"
            "2. Press 'Start'\n"
            "3. Come back and click Join again",
            show_alert=True
        )
        logger.warning(f"User {user.id} ({user.username}) has not started bot chat")
        return

    await UserRepository.subscribe_user(user.id)
    await UserRepository.set_can_receive_dm(user.id, True)

    subscriber_count = await UserRepository.get_subscriber_count()
    await _update_subscription_message(query, subscriber_count)

    await query.answer("You're in! Check your DMs ☕️")
    logger.info(f"User {user.id} ({user.username}) joined Random Coffee (total: {subscriber_count})")


async def leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user leaving Random Coffee."""
    query = update.callback_query
    user = query.from_user

    await UserRepository.unsubscribe_user(user.id)

    subscriber_count = await UserRepository.get_subscriber_count()
    await _update_group_message_count(context, subscriber_count)

    await query.edit_message_text(
        "👋 You've left DVC Random Coffee.\n\n"
        "We'll miss you! You can rejoin anytime from the group chat."
    )

    logger.info(f"User {user.id} ({user.username}) left Random Coffee")


async def _update_group_message_count(context: ContextTypes.DEFAULT_TYPE, subscriber_count: int):
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
        # Message not modified or bot lacks permission - safe to ignore
        logger.debug(f"Could not update group message count: {e}")


async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's subscription status (for DM use)."""
    if update.effective_chat.type != 'private':
        await update.message.reply_text("Please use this command in a private chat with me.")
        return

    user_id = update.effective_user.id
    db_user = await UserRepository.get_user(user_id)

    if not db_user:
        await update.message.reply_text(
            "You haven't joined DVC Random Coffee yet.\n\n"
            "Head to the group chat and click the Join button!"
        )
        return

    if db_user.is_subscribed:
        await update.message.reply_text(
            "☕️ You're part of DVC Random Coffee!\n\n"
            "Your next match will arrive on the 1st of the month.\n\n"
            "Get ready to connect!"
        )
    else:
        await update.message.reply_text(
            "You're not currently in DVC Random Coffee.\n\n"
            "Head to the group chat and click Join to get started!"
        )
