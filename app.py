import logging
import asyncio
import fcntl
import os
import sys
import signal
import atexit
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

# PID file to prevent multiple instances
PID_FILE = '/tmp/random_coffee_bot.pid'

# File descriptor for PID file lock (kept open to maintain lock)
_pid_fd = None


def cleanup_pid():
    """Remove PID file on exit."""
    global _pid_fd
    try:
        if _pid_fd is not None:
            os.close(_pid_fd)
            _pid_fd = None
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        logger.warning(f"Error cleaning up PID file: {e}")


def check_single_instance():
    """Ensure only one instance using atomic file locking."""
    global _pid_fd
    try:
        # Open file for read/write, create if doesn't exist
        _pid_fd = os.open(PID_FILE, os.O_CREAT | os.O_RDWR, 0o644)

        # Try to acquire exclusive lock (non-blocking)
        fcntl.flock(_pid_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # We got the lock - truncate and write our PID
        os.ftruncate(_pid_fd, 0)
        os.write(_pid_fd, str(os.getpid()).encode())
        os.fsync(_pid_fd)  # Ensure PID is written to disk

        # Register cleanup handlers
        atexit.register(cleanup_pid)
        signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))

        logger.info(f"Bot starting with PID {os.getpid()} (lock acquired)")

    except (OSError, IOError) as e:
        # Failed to acquire lock - another instance is running
        if _pid_fd is not None:
            try:
                # Try to read the PID of the running instance
                os.lseek(_pid_fd, 0, os.SEEK_SET)
                existing_pid = os.read(_pid_fd, 100).decode().strip()
                os.close(_pid_fd)
                _pid_fd = None
                logger.error(f"Bot already running with PID {existing_pid}. Exiting.")
            except Exception:
                logger.error(f"Bot already running (could not read PID). Exiting.")
        else:
            logger.error(f"Could not acquire lock on PID file: {e}")
        sys.exit(1)


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
    # Ensure single instance
    check_single_instance()

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
