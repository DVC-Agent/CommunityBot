import logging
import asyncio
from handlers.common_handlers import start
from handlers.coffee_handler import coffee, stop_poll, poll_answer_handler
from handlers.config_handler import get_token
from handlers.admin_handler import setup, status, force_match, subscribers, test_followup
from handlers.subscription_handler import join_callback, leave_callback, my_status
from handlers.followup_handler import followup_response_callback, request_rematch_callback

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler
)

from database.connection import init_db, close_db
from scheduler.jobs import setup_scheduler, shutdown_scheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

TOKEN = get_token()


async def post_init(application: Application) -> None:
    """Initialize database and scheduler after application starts."""
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    logger.info("Setting up scheduler...")
    setup_scheduler(application.bot)
    logger.info("Scheduler set up")


async def post_shutdown(application: Application) -> None:
    """Clean up on shutdown."""
    logger.info("Shutting down scheduler...")
    shutdown_scheduler()

    logger.info("Closing database connection...")
    await close_db()
    logger.info("Cleanup complete")


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it bot's token.
    application = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Original handlers (legacy poll-based feature)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("coffee", coffee))
    application.add_handler(CallbackQueryHandler(stop_poll, pattern='^stop_poll$'))
    application.add_handler(PollAnswerHandler(poll_answer_handler))

    # Admin handlers
    application.add_handler(CommandHandler("setup", setup))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("force_match", force_match))
    application.add_handler(CommandHandler("subscribers", subscribers))
    application.add_handler(CommandHandler("test_followup", test_followup))

    # User handlers
    application.add_handler(CommandHandler("mystatus", my_status))

    # Subscription callbacks
    application.add_handler(CallbackQueryHandler(join_callback, pattern='^join_coffee$'))
    application.add_handler(CallbackQueryHandler(leave_callback, pattern='^leave_coffee$'))

    # Follow-up callbacks
    application.add_handler(CallbackQueryHandler(
        followup_response_callback,
        pattern='^followup_(yes|no)_\\d+$'
    ))

    # Rematch request callback
    application.add_handler(CallbackQueryHandler(
        request_rematch_callback,
        pattern='^request_rematch_\\d+$'
    ))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
