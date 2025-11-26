"""
This file handles telegram token reading from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def get_token():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables. Please create a .env file with your bot token.")
    return token