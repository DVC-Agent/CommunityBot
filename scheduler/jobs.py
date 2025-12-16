import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from services.matching_service import MatchingService
from services.inactivity_service import InactivityService
from services.notification_service import NotificationService
from database.repositories import MatchRepository, FollowUpRepository, UserRepository

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [60, 120, 300]  # Seconds: 1 min, 2 min, 5 min


async def monthly_matching_job(bot: Bot):
    """Job: Run monthly matching on the 1st of each month with retry logic."""
    logger.info("Starting monthly matching job")
    for attempt in range(MAX_RETRIES):
        try:
            result = await MatchingService.execute_monthly_matching(bot)
            logger.info(f"Monthly matching result: {result}")
            return  # Success
        except Exception as e:
            logger.error(f"Monthly matching attempt {attempt + 1}/{MAX_RETRIES} failed: {e}", exc_info=True)
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.critical(f"Monthly matching failed after {MAX_RETRIES} attempts")


async def monthly_followup_job(bot: Bot):
    """Job: Send follow-up questions on the 7th of each month with retry logic."""
    logger.info("Starting monthly follow-up job")
    for attempt in range(MAX_RETRIES):
        try:
            # Get current round
            month_year = datetime.now().strftime("%Y-%m")
            current_round = await MatchRepository.get_current_round(month_year)

            if not current_round:
                logger.info("No matching round for current month, skipping follow-ups")
                return

            # Get all matches for this round
            matches = await MatchRepository.get_matches_for_round(current_round.id)
            logger.info(f"Sending follow-ups for {len(matches)} matches")

            sent = 0
            for match in matches:
                # Get user objects
                user1 = await UserRepository.get_user(match.user1_id)
                user2 = await UserRepository.get_user(match.user2_id)
                user3 = await UserRepository.get_user(match.user3_id) if match.user3_id else None

                if user1 and user2:
                    # Send to user1 (if not already sent)
                    existing1 = await FollowUpRepository.get_followup(match.id, user1.user_id)
                    if not existing1:
                        partner_name = NotificationService.format_user_name(user2)
                        if user3:
                            partner_name += f" and {NotificationService.format_user_name(user3)}"

                        if await NotificationService.send_followup_question(bot, user1, partner_name, match.id):
                            await FollowUpRepository.create_followup(match.id, user1.user_id)
                            sent += 1

                    # Send to user2 (if not already sent)
                    existing2 = await FollowUpRepository.get_followup(match.id, user2.user_id)
                    if not existing2:
                        partner_name = NotificationService.format_user_name(user1)
                        if user3:
                            partner_name += f" and {NotificationService.format_user_name(user3)}"

                        if await NotificationService.send_followup_question(bot, user2, partner_name, match.id):
                            await FollowUpRepository.create_followup(match.id, user2.user_id)
                            sent += 1

                    # Send to user3 if triple (if not already sent)
                    if user3:
                        existing3 = await FollowUpRepository.get_followup(match.id, user3.user_id)
                        if not existing3:
                            partner_name = f"{NotificationService.format_user_name(user1)} and {NotificationService.format_user_name(user2)}"
                            if await NotificationService.send_followup_question(bot, user3, partner_name, match.id):
                                await FollowUpRepository.create_followup(match.id, user3.user_id)
                                sent += 1

            logger.info(f"Sent {sent} follow-up messages")
            return  # Success

        except Exception as e:
            logger.error(f"Monthly follow-up attempt {attempt + 1}/{MAX_RETRIES} failed: {e}", exc_info=True)
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.critical(f"Monthly follow-up failed after {MAX_RETRIES} attempts")


async def inactivity_check_job(bot: Bot):
    """Job: Remove inactive users (3+ consecutive misses) with retry logic."""
    logger.info("Starting inactivity check job")
    for attempt in range(MAX_RETRIES):
        try:
            # First, process any unanswered follow-ups
            auto_nos = await InactivityService.process_unanswered_followups()
            logger.info(f"Auto-marked {auto_nos} unanswered follow-ups as 'no'")

            # Then check for inactive users
            result = await InactivityService.check_and_remove_inactive(bot)
            logger.info(f"Inactivity check result: {result}")
            return  # Success

        except Exception as e:
            logger.error(f"Inactivity check attempt {attempt + 1}/{MAX_RETRIES} failed: {e}", exc_info=True)
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logger.critical(f"Inactivity check failed after {MAX_RETRIES} attempts")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Set up the scheduler with all jobs."""
    global _scheduler

    _scheduler = AsyncIOScheduler()

    # Monthly matching: 1st of every month at 10:00
    _scheduler.add_job(
        monthly_matching_job,
        CronTrigger(day=1, hour=10, minute=0),
        args=[bot],
        id='monthly_matching',
        name='Monthly Random Coffee Matching',
        replace_existing=True,
        max_instances=1,  # Prevent concurrent runs
        misfire_grace_time=3600,  # Allow 1 hour late execution
        coalesce=True  # Combine missed runs into one
    )

    # Monthly follow-up: 7th of every month at 10:00 (1 week after matching)
    _scheduler.add_job(
        monthly_followup_job,
        CronTrigger(day=7, hour=10, minute=0),
        args=[bot],
        id='monthly_followup',
        name='Monthly Follow-up',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True
    )

    # Inactivity check: 1st of every month at 10:30 (after matching)
    _scheduler.add_job(
        inactivity_check_job,
        CronTrigger(day=1, hour=10, minute=30),
        args=[bot],
        id='inactivity_check',
        name='Monthly Inactivity Check',
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,
        coalesce=True
    )

    _scheduler.start()
    logger.info("Scheduler started with jobs: monthly_matching, monthly_followup, inactivity_check")

    return _scheduler


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler shut down")
