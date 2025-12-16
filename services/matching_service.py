import logging
import random
from datetime import datetime
from typing import List, Tuple, Set, Dict
from telegram import Bot
from telegram.error import BadRequest
from database.models import User
from database.repositories import UserRepository, MatchRepository, ConfigRepository
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class MatchingService:
    @staticmethod
    async def execute_monthly_matching(bot: Bot) -> Dict:
        """Execute the monthly matching process."""
        month_year = datetime.now().strftime("%Y-%m")
        month_name = datetime.now().strftime("%B %Y")

        # Atomic check-and-create to prevent race conditions
        round_obj = await MatchRepository.create_round_atomic(month_year)
        if round_obj is None:
            # Round already exists, get it and return status
            existing_round = await MatchRepository.get_current_round(month_year)
            logger.info(f"Matching already done for {month_year}")
            return {
                'status': 'already_done',
                'month_year': month_year,
                'total_subscribers': existing_round.total_subscribers,
                'total_pairs': existing_round.total_pairs,
                'dms_sent': 0
            }

        # Get all subscribers
        subscribers = await UserRepository.get_all_subscribers()
        total_subscribers = len(subscribers)

        if total_subscribers < 2:
            logger.info(f"Not enough subscribers for matching: {total_subscribers}")
            # Update round stats even if not enough subscribers
            await MatchRepository.update_round_stats(round_obj.id, total_subscribers, 0)
            return {
                'status': 'not_enough',
                'month_year': month_year,
                'total_subscribers': total_subscribers,
                'total_pairs': 0,
                'dms_sent': 0
            }

        # Get historical pairs to avoid
        historical_pairs = await MatchRepository.get_historical_pairs()

        # Generate matches
        matches = await MatchingService._generate_matches(subscribers, historical_pairs)

        # Update the round stats (round was created atomically above)
        await MatchRepository.update_round_stats(round_obj.id, total_subscribers, len(matches))

        # Save matches and send notifications
        dms_sent = 0
        for match_group in matches:
            if len(match_group) == 2:
                user1, user2 = match_group
                match_obj = await MatchRepository.create_match(
                    round_id=round_obj.id,
                    user1_id=user1.user_id,
                    user2_id=user2.user_id
                )
                # Add to history
                await MatchRepository.add_to_history(user1.user_id, user2.user_id, round_obj.id)

                # Send notifications
                if await NotificationService.send_match_notification(
                    bot, user1, [user2], month_name, match_obj.id
                ):
                    dms_sent += 1
                if await NotificationService.send_match_notification(
                    bot, user2, [user1], month_name, match_obj.id
                ):
                    dms_sent += 1

            elif len(match_group) == 3:
                user1, user2, user3 = match_group
                match_obj = await MatchRepository.create_match(
                    round_id=round_obj.id,
                    user1_id=user1.user_id,
                    user2_id=user2.user_id,
                    user3_id=user3.user_id
                )
                # Add all pairs to history
                await MatchRepository.add_to_history(user1.user_id, user2.user_id, round_obj.id)
                await MatchRepository.add_to_history(user1.user_id, user3.user_id, round_obj.id)
                await MatchRepository.add_to_history(user2.user_id, user3.user_id, round_obj.id)

                # Send notifications
                if await NotificationService.send_match_notification(
                    bot, user1, [user2, user3], month_name, match_obj.id
                ):
                    dms_sent += 1
                if await NotificationService.send_match_notification(
                    bot, user2, [user1, user3], month_name, match_obj.id
                ):
                    dms_sent += 1
                if await NotificationService.send_match_notification(
                    bot, user3, [user1, user2], month_name, match_obj.id
                ):
                    dms_sent += 1

        logger.info(f"Matching complete for {month_year}: {len(matches)} pairs, {dms_sent} DMs sent")

        # Post announcement to group
        await MatchingService._post_group_announcement(bot, month_name, len(matches))

        return {
            'status': 'success',
            'month_year': month_year,
            'total_subscribers': total_subscribers,
            'total_pairs': len(matches),
            'dms_sent': dms_sent
        }

    @staticmethod
    async def _post_group_announcement(bot: Bot, month_name: str, pairs_count: int):
        """Post matching announcement to the group."""
        config = await ConfigRepository.get_config()
        if not config:
            return

        message = (
            f"☕️ {month_name} Random Coffee matches are out!\n\n"
            f"Check your DMs to see who you've been paired with this month.\n\n"
            f"Happy connecting! 💛"
        )

        try:
            await bot.send_message(
                chat_id=config.group_chat_id,
                text=message,
                message_thread_id=config.message_thread_id
            )
        except BadRequest as e:
            logger.warning(f"Could not post group announcement: {e}")

    @staticmethod
    async def _generate_matches(
        subscribers: List[User],
        historical_pairs: Set[Tuple[int, int]]
    ) -> List[List[User]]:
        """Generate optimal matches avoiding historical pairs."""
        users = subscribers.copy()
        random.shuffle(users)

        matches = []
        unmatched = []

        # Build adjacency: which users can be paired (not in history)
        def can_pair(u1: User, u2: User) -> bool:
            pair = tuple(sorted([u1.user_id, u2.user_id]))
            return pair not in historical_pairs

        # Try to find matches avoiding historical pairs
        used = set()

        for i, user1 in enumerate(users):
            if user1.user_id in used:
                continue

            # Find a partner not in history
            partner = None
            for j, user2 in enumerate(users):
                if i == j or user2.user_id in used:
                    continue
                if can_pair(user1, user2):
                    partner = user2
                    break

            if partner:
                matches.append([user1, partner])
                used.add(user1.user_id)
                used.add(partner.user_id)
            else:
                unmatched.append(user1)

        # Handle unmatched users
        if len(unmatched) >= 2:
            # Pair remaining users even if they've met before
            while len(unmatched) >= 2:
                u1 = unmatched.pop()
                u2 = unmatched.pop()
                matches.append([u1, u2])
                logger.info(f"Repeat match: {u1.user_id} and {u2.user_id}")

        # If one person left, add to a random existing pair
        if len(unmatched) == 1 and matches:
            lonely_user = unmatched[0]
            random_match = random.choice(matches)
            random_match.append(lonely_user)
            logger.info(f"Created triple: added {lonely_user.user_id} to existing pair")

        return matches
