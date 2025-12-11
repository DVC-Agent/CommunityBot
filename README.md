i# Random Coffee Telegram Bot

## Overview

Random Coffee Telegram Bot is a simple bot designed to facilitate networking between users in a group chat specializing in a particular topic, such as software development or chats to discuss a particular technology, etc.

Any member of the chat can organize an event with a specified date. The bot will randomly create pairs among the participants, the format and time of the meeting are determined by the users themselves.

## Setup

### 1. Create Your Bot
1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token you receive

### 2. Configure Bot Settings
1. In @BotFather, send `/setprivacy`
2. Select your bot
3. Choose **Disable** (so the bot can see messages in groups)

### 3. Install and Run
```bash
# Clone the repository
git clone https://github.com/Vladoverx/RandomCoffeeTelegramBot
cd RandomCoffeeTelegramBot

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your bot token

# Run the bot
python app.py
```

### 4. Add Bot to Your Group
1. Add your bot to a Telegram group or supergroup
2. Make sure the bot has admin rights (or at least permission to send messages and polls)

## How to Use

1. **Start the bot**: In your group chat, use command `/start`
2. **Create an event**: Use `/coffee [date]` to create an event poll
   - Example: `/coffee July 30`
3. **Get matches**: Once you have at least 4 participants, the event creator can stop the poll, and the bot will automatically pair participants
4. **Enjoy networking**: Start chatting with your matched partner(s)

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, open an issue or submit a pull request.
