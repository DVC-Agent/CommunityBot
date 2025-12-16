# DVC Community Bot

A Telegram bot that facilitates monthly "Random Coffee" matches within a community. Members are randomly paired each month for casual conversations, helping build connections across the community.

## Features

- **Monthly Matching**: Automatically pairs subscribers on the 1st of each month
- **No Repeat Matches**: Tracks match history to avoid pairing the same people twice
- **Follow-up Tracking**: Sends "Did you meet?" questions after 1 week
- **Inactivity Management**: Auto-removes users after 3 consecutive missed meetings
- **Admin Controls**: Setup, force match, view subscribers, and status commands

## Commands

### Admin Commands
| Command | Description |
|---------|-------------|
| `/setup` | Post the join message in a group chat |
| `/status` | View subscriber count and last matching round |
| `/force_match` | Manually trigger monthly matching |
| `/subscribers` | List all subscribed users |
| `/test_followup` | Manually trigger follow-up messages |

### User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot / join via deep link |
| `/mystatus` | Check your subscription status |

## Setup

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 2. Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID (for admin access)

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=your_user_id_here
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python app.py
```

Or use the startup script:
```bash
./start_bot.sh
```

## Deployment

### Railway (Recommended)

1. Fork this repository
2. Create account at [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Add environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_USER_IDS`
5. Deploy!

### Manual Server

```bash
# Clone the repo
git clone https://github.com/DVC-Agent/CommunityBot.git
cd CommunityBot

# Setup
cp .env.example .env
# Edit .env with your values

# Install deps
pip install -r requirements.txt

# Run with systemd or supervisord for production
python app.py
```

## How It Works

### Monthly Flow

```
1st of month     7th of month      End of month
     │                │                  │
     ▼                ▼                  ▼
  Matching  →   Follow-up sent  →  Inactivity check
     │                │                  │
     ▼                ▼                  ▼
  DMs sent      "Did you meet?"     Remove inactive
  to pairs       Yes / No           (3+ misses)
```

### User Journey

1. User clicks "Join Random Coffee" button in group
2. Bot sends welcome DM (verifies bot access)
3. User is subscribed
4. On 1st of month: receives match notification
5. On 7th of month: receives follow-up question
6. Cycle repeats monthly

## Database

Uses SQLite with the following tables:
- `config` - Bot configuration (group chat ID, message IDs)
- `users` - User profiles and subscription status
- `matching_rounds` - Monthly matching round records
- `matches` - Individual match pairs/triples
- `match_history` - Historical pairs (prevents repeats)
- `follow_ups` - Follow-up responses
- `meeting_streaks` - Consecutive missed meetings tracker

## Project Structure

```
CommunityBot/
├── app.py                    # Main entry point
├── handlers/
│   ├── admin_handler.py      # Admin commands
│   ├── subscription_handler.py # Join/leave logic
│   ├── followup_handler.py   # Follow-up responses
│   └── common_handlers.py    # /start command
├── services/
│   ├── matching_service.py   # Matching algorithm
│   ├── notification_service.py # Message sending
│   └── inactivity_service.py # Inactivity tracking
├── scheduler/
│   └── jobs.py               # Scheduled jobs
├── database/
│   ├── connection.py         # SQLite connection
│   ├── models.py             # Data models
│   └── repositories/         # Database operations
├── requirements.txt
├── Procfile                  # Railway deployment
└── .env.example              # Environment template
```

## License

MIT
