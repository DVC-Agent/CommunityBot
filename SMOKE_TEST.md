# DVC Random Coffee Bot — End-to-End Smoke Test

## Prerequisites

- [ ] Bot is running (`python3 app.py`)
- [ ] You have a Telegram group where you're admin
- [ ] You have 2+ test Telegram accounts (or friends to help)
- [ ] Bot token is configured in `.env`

---

## Test 1: Bot Setup

### Steps:
1. Add the bot to your Telegram group
2. Go to the topic/channel where you want Random Coffee
3. Send `/setup`

### Expected:
- [ ] Bot posts the DVC welcome message with ☕️ Join button
- [ ] No extra confirmation message
- [ ] Message appears in the correct topic

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM config;"
```
Should show: `group_chat_id`, `info_message_id`, `message_thread_id`, `bot_username`

---

## Test 2: User Joins (First User)

### Steps:
1. Click "☕️ Join Random Coffee" button in group
2. Bot DM should open automatically

### Expected:
- [ ] Bot DM opens with join confirmation
- [ ] Message: "🎉 You're in, {name}! Welcome to DVC Random Coffee..."
- [ ] Shows "☕️ 1 members joined so far"
- [ ] "Leave Random Coffee" button appears
- [ ] Group button updates to "☕️ Join Random Coffee (1 joined)"

### Verify:
```bash
sqlite3 random_coffee.db "SELECT user_id, username, first_name, is_subscribed FROM users;"
```

---

## Test 3: User Joins (Second User)

### Steps:
1. Use different Telegram account
2. Click "☕️ Join Random Coffee" button

### Expected:
- [ ] Same flow as Test 2
- [ ] Shows "☕️ 2 members joined so far"
- [ ] Group button updates to "☕️ Join Random Coffee (2 joined)"

### Verify:
```bash
sqlite3 random_coffee.db "SELECT COUNT(*) FROM users WHERE is_subscribed = 1;"
```
Should show: `2`

---

## Test 4: Already Subscribed User Clicks Join Again

### Steps:
1. With subscribed user, click the group join button again

### Expected:
- [ ] Bot DM opens
- [ ] Message: "Hey {name}! 👋 You're already part of DVC Random Coffee..."
- [ ] Shows "Leave Random Coffee" button

---

## Test 5: User Leaves

### Steps:
1. In bot DM, click "Leave Random Coffee" button

### Expected:
- [ ] Message changes to "👋 You've left DVC Random Coffee..."
- [ ] No popup
- [ ] Group button count decreases

### Verify:
```bash
sqlite3 random_coffee.db "SELECT user_id, is_subscribed FROM users;"
```
User should show `is_subscribed = 0`

---

## Test 6: User Rejoins

### Steps:
1. Click "☕️ Join Random Coffee" in group again

### Expected:
- [ ] User is subscribed again
- [ ] Welcome message shown
- [ ] Count increases

---

## Test 7: Admin Status Command

### Steps:
1. Send `/status` in group or DM

### Expected:
- [ ] Shows subscriber count
- [ ] Shows last matching round (if any)

---

## Test 8: Admin Subscribers Command

### Steps:
1. Send `/subscribers`

### Expected:
- [ ] Lists all subscribed users with names and usernames

---

## Test 9: Force Match (2 Users)

### Prerequisites:
- Exactly 2 subscribed users

### Steps:
1. Send `/force_match`

### Expected:
- [ ] Bot replies "Starting manual matching..."
- [ ] Bot replies with results: "Subscribers: 2, Pairs created: 1, DMs sent: 2"
- [ ] Both users receive match DM:
  - "☕️ Your {month} Coffee Match is here!"
  - Shows partner name with 👤
  - Shows People Book link
  - Has "Request Different Match" button

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM matching_rounds;"
sqlite3 random_coffee.db "SELECT * FROM matches;"
sqlite3 random_coffee.db "SELECT * FROM match_history;"
```

---

## Test 10: Force Match — Duplicate Prevention

### Steps:
1. Run `/force_match` again in the same month

### Expected:
- [ ] Bot replies with "DMs sent: 0" (already matched this month)

---

## Test 11: Force Match (3 Users — Triple)

### Prerequisites:
- Exactly 3 subscribed users

### Steps:
1. Delete current month's round:
   ```bash
   sqlite3 random_coffee.db "DELETE FROM matching_rounds;"
   ```
2. Run `/force_match`

### Expected:
- [ ] Creates 1 match with all 3 users (triple)
- [ ] All 3 receive DM mentioning the other 2
- [ ] Message says "You're in a group of 3 this month"

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM matches WHERE user3_id IS NOT NULL;"
```

---

## Test 12: Match History (No Repeat)

### Prerequisites:
- 4+ subscribed users
- Previous match history exists

### Steps:
1. Clear current round:
   ```bash
   sqlite3 random_coffee.db "DELETE FROM matching_rounds;"
   sqlite3 random_coffee.db "DELETE FROM matches;"
   ```
2. Run `/force_match`

### Expected:
- [ ] New pairs are different from history
- [ ] Check match_history table for no duplicates

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM match_history;"
```

---

## Test 13: Follow-up Response — Yes

### Steps:
1. After receiving match, simulate follow-up or wait for 7th
2. When "Did you connect?" message arrives, click "Yes, we met! ✅"

### Expected:
- [ ] Message changes to "🎉 Amazing! Glad you connected!"
- [ ] User's streak resets to 0

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM follow_ups;"
sqlite3 random_coffee.db "SELECT * FROM meeting_streaks;"
```

---

## Test 14: Follow-up Response — No

### Steps:
1. Click "Not yet ❌" on follow-up question

### Expected:
- [ ] Message changes to "No worries — life gets busy! 💛"
- [ ] User's consecutive_misses increases by 1

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM meeting_streaks;"
```

---

## Test 15: Request Different Match

### Steps:
1. After receiving match DM, click "Request Different Match"

### Expected:
- [ ] Message updates with "📝 Rematch requested — we'll review and get back to you!"

---

## Test 16: My Status Command

### Steps:
1. In bot DM, send `/mystatus`

### Expected (subscribed):
- [ ] "☕️ You're part of DVC Random Coffee!"

### Expected (not subscribed):
- [ ] "You're not currently in DVC Random Coffee..."

---

## Test 17: Not Enough Subscribers

### Prerequisites:
- Only 1 subscriber

### Steps:
1. Run `/force_match`

### Expected:
- [ ] "Subscribers: 1, Pairs created: 0, DMs sent: 0"

---

## Test 18: Inactivity Removal (Manual Test)

### Steps:
1. Set a user's streak to 3:
   ```bash
   sqlite3 random_coffee.db "INSERT OR REPLACE INTO meeting_streaks (user_id, consecutive_misses, last_updated_month) VALUES (USER_ID, 3, '2024-11');"
   ```
2. Trigger inactivity check (or wait for 1st of month)

### Expected:
- [ ] User is unsubscribed
- [ ] User receives: "👋 Hey {name}, We noticed you haven't been able to connect..."

### Verify:
```bash
sqlite3 random_coffee.db "SELECT is_subscribed FROM users WHERE user_id = USER_ID;"
```

---

## Quick Database Commands

```bash
# Check all tables
sqlite3 random_coffee.db ".tables"

# Config
sqlite3 random_coffee.db "SELECT * FROM config;"

# All users
sqlite3 random_coffee.db "SELECT * FROM users;"

# Subscribers only
sqlite3 random_coffee.db "SELECT * FROM users WHERE is_subscribed = 1;"

# Subscriber count
sqlite3 random_coffee.db "SELECT COUNT(*) FROM users WHERE is_subscribed = 1;"

# Matching rounds
sqlite3 random_coffee.db "SELECT * FROM matching_rounds;"

# Matches
sqlite3 random_coffee.db "SELECT * FROM matches;"

# Match history
sqlite3 random_coffee.db "SELECT * FROM match_history;"

# Follow-ups
sqlite3 random_coffee.db "SELECT * FROM follow_ups;"

# Meeting streaks
sqlite3 random_coffee.db "SELECT * FROM meeting_streaks;"

# Reset database (careful!)
rm random_coffee.db && python3 app.py
```

---

## Checklist Summary

| # | Test | Status |
|---|------|--------|
| 1 | Bot setup | ⬜ |
| 2 | First user joins | ⬜ |
| 3 | Second user joins | ⬜ |
| 4 | Already subscribed clicks join | ⬜ |
| 5 | User leaves | ⬜ |
| 6 | User rejoins | ⬜ |
| 7 | Admin /status | ⬜ |
| 8 | Admin /subscribers | ⬜ |
| 9 | Force match (2 users) | ⬜ |
| 10 | Duplicate match prevention | ⬜ |
| 11 | Triple match (3 users) | ⬜ |
| 12 | Match history no repeat | ⬜ |
| 13 | Follow-up Yes | ⬜ |
| 14 | Follow-up No | ⬜ |
| 15 | Request different match | ⬜ |
| 16 | /mystatus command | ⬜ |
| 17 | Not enough subscribers | ⬜ |
| 18 | Inactivity removal | ⬜ |

---

## Scheduled Jobs (Automatic)

These run automatically but can be tested manually:

| Job | Schedule | Test Command |
|-----|----------|--------------|
| Monthly Match | 1st @ 10:00 | `/force_match` |
| Follow-up | 7th @ 10:00 | Manual DB insert |
| Inactivity | 1st @ 10:30 | Manual DB insert |

---

## Common Issues

**Bot can't send DM:**
- User needs to start bot first (click bot → Start)

**Button count not updating:**
- Check `config` table has `bot_username` set
- Run `/setup` again

**Match not working:**
- Need at least 2 subscribers
- Check if already matched this month

**Database locked:**
- Stop the bot, run query, restart bot
