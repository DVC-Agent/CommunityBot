import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.repositories import ConfigRepository, UserRepository, MatchRepository

logger = logging.getLogger(__name__)

# Admin user IDs (can be configured via environment variable)
import os
ADMIN_IDS = set(map(int, os.getenv('ADMIN_USER_IDS', '').split(','))) if os.getenv('ADMIN_USER_IDS') else set()


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    # If no admins configured, allow anyone (for initial setup)
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS


async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Initialize the bot in a group chat and post the join message."""
    if update.effective_chat.type == 'private':
        await update.message.reply_text(
            "This command should be used in a group chat to set up Random Coffee."
        )
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Only admins can set up Random Coffee.")
        return

    chat_id = update.effective_chat.id
    # Get topic ID if in a forum/topic
    message_thread_id = update.message.message_thread_id

    # Get bot username for deep link
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    # Get current subscriber count
    subscriber_count = await UserRepository.get_subscriber_count()

    # Create the join message with deep link button
    keyboard = [[InlineKeyboardButton(
        f"☕️ Join Random Coffee ({subscriber_count} joined)" if subscriber_count > 0 else "☕️ Join Random Coffee",
        url=f"https://t.me/{bot_username}?start=join"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = await update.effective_chat.send_message(
        text=(
            "✨ Introducing DVC Random Coffee — Connecting Our Community Worldwide ✨\n\n"
            "At DVC, we believe the strongest networks grow through unexpected conversations. "
            "To help build more horizontal connections across our global community, we're launching "
            "Random Coffee — a simple, fun way to meet someone new each month.\n\n"
            "Every month, our bot will match you with another DVC member.\n"
            "Your only \"task\": hop on a short call sometime during the week and get to know each other "
            "— founder to LP, engineer to operator, investor to investor. "
            "New ideas, collaborations, and friendships often start with just one conversation.\n\n"
            "If you're in, simply click the button below to receive your Match of the Month:\n\n"
            "Let's keep strengthening the fabric of our community — one coffee chat at a time. ☕️💛"
        ),
        reply_markup=reply_markup,
        message_thread_id=message_thread_id
    )

    # Save config with all info needed to update the message later
    await ConfigRepository.set_config(
        group_chat_id=chat_id,
        info_message_id=message.message_id,
        message_thread_id=message_thread_id,
        bot_username=bot_username
    )

    logger.info(f"Random Coffee setup in chat {chat_id} by user {update.effective_user.id}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current Random Coffee status."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Only admins can view status.")
        return

    config = await ConfigRepository.get_config()
    if not config:
        await update.message.reply_text(
            "Random Coffee is not set up yet. Use /setup in a group chat first."
        )
        return

    subscriber_count = await UserRepository.get_subscriber_count()
    latest_round = await MatchRepository.get_latest_round()

    status_text = (
        f"Random Coffee Status\n"
        f"{'=' * 20}\n"
        f"Active Subscribers: {subscriber_count}\n"
    )

    if latest_round:
        status_text += (
            f"\nLast Matching Round: {latest_round.month_year}\n"
            f"Pairs Created: {latest_round.total_pairs}\n"
        )
    else:
        status_text += "\nNo matching rounds yet.\n"

    await update.message.reply_text(status_text)


async def force_match(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger matching (for testing)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Only admins can force matching.")
        return

    from services.matching_service import MatchingService

    admin_user_id = update.effective_user.id
    is_group = update.effective_chat.type != 'private'

    # Send status update to admin via DM if command was in group
    async def send_admin_message(text: str):
        if is_group:
            try:
                await context.bot.send_message(chat_id=admin_user_id, text=text)
            except Exception as e:
                logger.warning(f"Could not DM admin: {e}")
        else:
            await update.message.reply_text(text)

    await send_admin_message("Starting manual matching...")

    try:
        result = await MatchingService.execute_monthly_matching(context.bot)
        await send_admin_message(
            f"✅ Matching complete!\n\n"
            f"Subscribers: {result['total_subscribers']}\n"
            f"Pairs created: {result['total_pairs']}\n"
            f"DMs sent: {result['dms_sent']}"
        )
    except Exception as e:
        logger.error(f"Force match failed: {e}")
        await send_admin_message(f"❌ Matching failed: {str(e)}")


async def subscribers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all subscribers."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Only admins can view subscribers.")
        return

    users = await UserRepository.get_all_subscribers()

    if not users:
        await update.message.reply_text("No subscribers yet.")
        return

    user_list = []
    for user in users:
        name = user.first_name or "Unknown"
        if user.last_name:
            name += f" {user.last_name}"
        username = f" (@{user.username})" if user.username else ""
        dm_status = "" if user.can_receive_dm else " [DM blocked]"
        user_list.append(f"- {name}{username}{dm_status}")

    await update.message.reply_text(
        f"Random Coffee Subscribers ({len(users)}):\n\n" + "\n".join(user_list)
    )


async def test_followup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger follow-up messages (for testing)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Only admins can trigger follow-ups.")
        return

    from scheduler.jobs import monthly_followup_job

    admin_user_id = update.effective_user.id
    is_group = update.effective_chat.type != 'private'

    async def send_admin_message(text: str):
        if is_group:
            try:
                await context.bot.send_message(chat_id=admin_user_id, text=text)
            except Exception as e:
                logger.warning(f"Could not DM admin: {e}")
        else:
            await update.message.reply_text(text)

    await send_admin_message("Starting follow-up job...")

    try:
        await monthly_followup_job(context.bot)
        await send_admin_message("✅ Follow-up job completed!")
    except Exception as e:
        logger.error(f"Follow-up test failed: {e}")
        await send_admin_message(f"❌ Follow-up failed: {str(e)}")
