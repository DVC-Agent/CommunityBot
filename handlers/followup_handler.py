import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import FollowUpRepository, MatchRepository, UserRepository
from services.inactivity_service import InactivityService

logger = logging.getLogger(__name__)


async def followup_response_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle follow-up Yes/No response."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("_")

    if len(parts) != 3:
        logger.error(f"Invalid followup callback data: {data}")
        return

    try:
        response = parts[1]
        match_id = int(parts[2])
        user_id = query.from_user.id

        await FollowUpRepository.record_response(match_id, user_id, response)
        await InactivityService.process_followup_response(user_id, response)

        if response == "yes":
            await query.edit_message_text(
                "🎉 Amazing! Glad you connected!\n\n"
                "See you next month for another great conversation. ☕️"
            )
        else:
            await query.edit_message_text(
                "No worries — life gets busy!\n\n"
                "Hopefully you'll get a chance to connect next month. 💛"
            )

        logger.info(f"User {user_id} responded '{response}' to match {match_id}")
    except ValueError as e:
        logger.error(f"Invalid match_id in callback data: {data}", exc_info=True)
    except Exception as e:
        logger.error(f"Error processing followup response: {e}", exc_info=True)


async def request_rematch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rematch request."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("_")

    if len(parts) != 3:
        logger.error(f"Invalid rematch callback data: {data}")
        return

    try:
        match_id = int(parts[2])
        user_id = query.from_user.id

        await query.edit_message_text(
            query.message.text + "\n\n"
            "📝 Rematch requested — we'll review and get back to you!"
        )

        logger.info(f"User {user_id} requested rematch for match {match_id}")
    except ValueError as e:
        logger.error(f"Invalid match_id in rematch callback data: {data}", exc_info=True)
    except Exception as e:
        logger.error(f"Error processing rematch request: {e}", exc_info=True)
