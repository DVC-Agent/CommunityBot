import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import ContextTypes


async def coffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Creating random coffee session with date of event passed along with command"""
    date_of_event = context.args[:] if context.args else None

    if date_of_event:
        poll_question = f"Random Coffee {' '.join(date_of_event)}!\nWill you participate?"

        options = ["Yes ☕️", "Can't make it 😔"]

        # Get message_thread_id for supergroups with topics
        message_thread_id = update.message.message_thread_id

        # Send message with poll
        poll_message = await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            message_thread_id=message_thread_id,
            question=poll_question,
            options=options,
            is_anonymous=False,
            reply_markup=InlineKeyboardMarkup.from_row([
                InlineKeyboardButton("Stop Poll", callback_data="stop_poll")
            ])  # Add an inline button to stop the poll
        )

        # Save poll data for later use
        poll_data = {
            poll_message.poll.id: {
                "chat_id": update.effective_chat.id,
                "message_id": poll_message.message_id,
                "message_thread_id": message_thread_id,
                "creator_id": update.message.from_user.id,
                "users_in": []
            }
        }
        context.bot_data.update(poll_data)
        

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle a users poll vote
    user voted option_id == 0 -> add user to the list
    user retracted/user changed vote -> remove user from the list
    """
    answer = update.poll_answer
    
    poll_data = context.bot_data[answer.poll_id]
    user = answer.user
    selected_options = answer.option_ids
    
    participants = poll_data["users_in"]
    
    if 0 in selected_options:
        if user not in participants:  # Add user if not already in
            participants.append(user)
            poll_data["users_in"] = participants
            context.bot_data.update(poll_data)
    else:  # User retracted or changed their vote
        if user in participants:  # Remove user if present
            participants.remove(user)
            poll_data["users_in"] = participants
            context.bot_data.update(poll_data)
            
            
async def stop_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Stop the poll and save details about poll and participants into database
    """
    query = update.callback_query
    poll_id = query.message.poll.id
    
    # Get the poll data from bot_data
    poll_data = context.bot_data[poll_id]

    if poll_data:
        # Check if the user trying to stop the poll is the creator
        if query.from_user.id == poll_data["creator_id"]:
            # Stop the poll
            await context.bot.stop_poll(
                chat_id=poll_data["chat_id"],
                message_id=poll_data["message_id"]
            )

            # Inform users that the poll has been stopped
            await query.answer("Poll stopped.")

            if len(poll_data["users_in"]) > 3:
                # Trigger the generate_matches function
                await generate_matches(update, context, poll_data["users_in"], poll_data["message_thread_id"])
            else:
                # Send a message indicating there are not enough users to hold a session
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    message_thread_id=poll_data["message_thread_id"],
                    text="Not enough participants to proceed."
                )

        else:
            # If the user is not the creator, inform them they cannot stop the poll
            await query.answer("You are not the poll creator.", show_alert=True)

    else:
        # If no poll data found, inform that the poll may have already been stopped
        await query.answer("This poll may have already been stopped.", show_alert=True)

          
async def generate_matches(update: Update, context: ContextTypes.DEFAULT_TYPE, users_list: list[User], message_thread_id: int = None):
    """
    Get information about participants from poll in form of list
    Shuffle users from list and make pairs
    If number of users is odd randomly add last user to already created pair
    """

    participants = users_list

    # Shuffle users
    random.shuffle(participants)

    # Pair up users
    pairs = []
    while len(participants) >= 2:
        pair = (participants.pop().username, participants.pop().username)
        pairs.append(pair)

    # If there's an odd number of users, randomly add one user to an existing pair
    if participants:
        random_pair_index = random.randint(0, len(pairs) - 1)
        pairs[random_pair_index] += (participants.pop().username,)

    # Format and send message with pairs
    message_text = "Here are your matches:\n\n"
    for pair in pairs:
        message_text += " - ".join(f"@{username}" for username in pair) + "\n"

    message_text += "\nEnjoy your time together! 😉"
    # Send the message to the chat
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=message_thread_id,
        text=message_text
    )
        