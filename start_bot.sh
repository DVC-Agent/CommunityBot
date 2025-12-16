#!/bin/bash
# Start Random Coffee Bot
# This script ensures clean startup by killing any existing instances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="/tmp/random_coffee_bot.pid"

echo "Starting Random Coffee Bot..."

# Kill existing instance if running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing bot (PID: $OLD_PID)..."
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Also kill any orphan Python processes running app.py
pkill -f "Python.*app.py" 2>/dev/null
sleep 1

# Start the bot
cd "$SCRIPT_DIR"
python3 app.py
