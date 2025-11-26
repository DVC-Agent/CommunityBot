from telegram import Update
from telegram.ext import (
    ContextTypes,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """"""

    message = """ Hi! This is Random Coffee 😎

I will help you meet and organize meetings with interesting people in your chat.

To create an event, use the /coffee command along with the date.

Example: /coffee July 30

Minimum number of participants required for Random Coffee is 4 people.
Only the event creator can stop the poll.

Happy networking!
    """

    await update.message.reply_text(message)

    