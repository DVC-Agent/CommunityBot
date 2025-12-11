# Random Coffee Bot - End-to-End Testing Guide

## Prerequisites

1. Bot is running (`python3 app.py`)
2. You have access to a Telegram group where you're admin
3. You have 2-3 test Telegram accounts (or friends to help test)
4. Bot token is configured in `.env`

---

## Test 1: Bot Setup in Group

### Steps:
1. Add the bot to your Telegram group
2. Send `/setup` in the group

### Expected Result:
- Bot posts a message:
  ```
  Welcome to Random Coffee!

  Every month on the 1st, you'll be randomly matched with someone
  from this community for a casual 1-on-1 chat.

  Click the button below to join and start making connections!

  You can leave anytime by clicking the button again.
  ```
- Message has a "Join Random Coffee" button
- Bot replies: "Random Coffee has been set up!"

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT * FROM config;"
```
Should show your group's chat_id.

---

## Test 2: User Subscription (Join)

### Steps:
1. **First**, start a private chat with the bot (click bot name → Start)
2. Go back to the group
3. Click "Join Random Coffee" button

### Expected Result:
- Bot sends you a DM:
  ```
  Welcome to Random Coffee!

  You're now subscribed and will be matched with someone
  on the 1st of next month.

  I'll send you a message with your match's details when it's time!
  ```
- Popup shows: "You've joined Random Coffee! Check your DMs."

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT user_id, username, first_name, is_subscribed FROM users;"
```

---

## Test 3: User Subscription (Without Starting Bot First)

### Steps:
1. Use a different account that has NOT started the bot
2. Click "Join Random Coffee" button

### Expected Result:
- Popup shows: "Please start a private chat with me first! Click on my name and press 'Start', then try again."
- User is NOT added to subscribers

---

## Test 4: User Unsubscribe (Leave)

### Steps:
1. With a subscribed user, click "Join Random Coffee" button again

### Expected Result:
- Popup shows: "You've left Random Coffee. You can rejoin anytime!"
- Bot sends DM: "You've been removed from Random Coffee..."

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT user_id, is_subscribed FROM users WHERE user_id = YOUR_ID;"
```
Should show `is_subscribed = 0`

---

## Test 5: Check Status (Admin)

### Steps:
1. Send `/status` in group or DM

### Expected Result:
```
Random Coffee Status
====================
Active Subscribers: X

No matching rounds yet.
```

---

## Test 6: List Subscribers (Admin)

### Steps:
1. Have 2+ users subscribe
2. Send `/subscribers`

### Expected Result:
```
Random Coffee Subscribers (2):

- John Doe (@johndoe)
- Jane Smith (@janesmith)
```

---

## Test 7: Force Match (Manual Matching)

### Prerequisites:
- At least 2 subscribed users

### Steps:
1. Send `/force_match` in group or DM

### Expected Result:
- Bot replies: "Starting manual matching..."
- Bot replies with results:
  ```
  Matching complete!
  Subscribers: 2
  Pairs created: 1
  DMs sent: 2
  ```
- Each subscriber receives a DM:
  ```
  Hey [Name]! Your Random Coffee match for December 2024 is ready!

  You're matched with: [Partner Name] (@username)

  Learn more about them in People Book:
  https://platform.davidovs.com/people

  Reach out and schedule your coffee chat!

  [Request Different Match]
  ```

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT * FROM matching_rounds;"
sqlite3 random_coffee.db "SELECT * FROM matches;"
sqlite3 random_coffee.db "SELECT * FROM match_history;"
```

---

## Test 8: Duplicate Matching Prevention

### Steps:
1. Run `/force_match` again in the same month

### Expected Result:
- Bot replies:
  ```
  Matching complete!
  Subscribers: 2
  Pairs created: 1
  DMs sent: 0
  ```
- Status shows `already_done` (no new DMs sent)

---

## Test 9: Follow-up Response (Yes)

### Steps:
1. After receiving match notification, simulate follow-up by manually triggering or waiting for 7th
2. When you receive "Did you meet?" message, click "Yes"

### Expected Result:
- Message updates to: "Awesome! Glad you connected! See you next month."

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT * FROM follow_ups;"
sqlite3 random_coffee.db "SELECT * FROM meeting_streaks;"
```
Should show `response = 'yes'` and `consecutive_misses = 0`

---

## Test 10: Follow-up Response (No)

### Steps:
1. Click "No" on follow-up question

### Expected Result:
- Message updates to: "No worries! Life gets busy. Hope you can connect next time!"

### Verify in Database:
```bash
sqlite3 random_coffee.db "SELECT * FROM meeting_streaks WHERE user_id = YOUR_ID;"
```
Should show `consecutive_misses = 1`

---

## Test 11: My Status Command

### Steps:
1. Send `/mystatus` in private chat with bot

### Expected Result (if subscribed):
```
You're currently subscribed to Random Coffee!

Subscribed since: 2024-12-10T...

You'll be matched on the 1st of next month.
```

### Expected Result (if not subscribed):
```
You're not currently subscribed to Random Coffee.
Join via the button in the group chat!
```

---

## Test 12: Match History (No Repeat Matches)

### Prerequisites:
- 4+ subscribers
- Run matching twice (in different months)

### Steps:
1. Subscribe 4 users: A, B, C, D
2. Run `/force_match` → Creates pairs (e.g., A-B, C-D)
3. Delete the current month's round to simulate new month:
   ```bash
   sqlite3 random_coffee.db "DELETE FROM matching_rounds WHERE month_year = '2024-12';"
   ```
4. Run `/force_match` again

### Expected Result:
- New pairs should be different (e.g., A-C, B-D or A-D, B-C)
- Check match_history to confirm no repeat pairs

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM match_history;"
```

---

## Test 13: Odd Number of Subscribers (Triple)

### Prerequisites:
- Exactly 3 subscribers

### Steps:
1. Ensure only 3 users are subscribed
2. Run `/force_match`

### Expected Result:
- 1 match created with all 3 users (triple)
- All 3 receive DM mentioning the other 2:
  ```
  You're in a group of 3 this month:
  - User A (@usera)
  - User B (@userb)
  ```

### Verify:
```bash
sqlite3 random_coffee.db "SELECT * FROM matches WHERE user3_id IS NOT NULL;"
```

---

## Test 14: Not Enough Subscribers

### Prerequisites:
- Only 1 subscriber

### Steps:
1. Run `/force_match`

### Expected Result:
- Bot replies:
  ```
  Matching complete!
  Subscribers: 1
  Pairs created: 0
  DMs sent: 0
  ```

---

## Test 15: Blocked Bot (Can't DM)

### Steps:
1. Subscribe a user
2. Have that user block the bot
3. Run `/force_match`

### Expected Result:
- Matching completes but DM fails for blocked user
- User's `can_receive_dm` is set to `false`

### Verify:
```bash
sqlite3 random_coffee.db "SELECT user_id, can_receive_dm FROM users;"
```

---

## Test 16: Inactivity Removal

### Prerequisites:
- User with 3+ consecutive misses

### Steps:
1. Manually set streak in database:
   ```bash
   sqlite3 random_coffee.db "INSERT OR REPLACE INTO meeting_streaks (user_id, consecutive_misses, last_updated_month) VALUES (YOUR_USER_ID, 3, '2024-11');"
   ```
2. Trigger inactivity check (or wait for 1st of month)

### Expected Result:
- User is unsubscribed
- User receives DM:
  ```
  Hi [Name],

  You've been automatically removed from Random Coffee because
  you haven't been able to meet for 3 consecutive months.

  No hard feelings! You can rejoin anytime by clicking the button
  in the group chat.

  See you next time!
  ```

### Verify:
```bash
sqlite3 random_coffee.db "SELECT is_subscribed FROM users WHERE user_id = YOUR_USER_ID;"
```
Should show `0`

---

## Test 17: Request Different Match

### Steps:
1. After receiving match notification, click "Request Different Match"

### Expected Result:
- Message updates with: "[Rematch requested - an admin will review your request]"

---

## Database Inspection Commands

```bash
# All tables overview
sqlite3 random_coffee.db ".tables"

# Config
sqlite3 random_coffee.db "SELECT * FROM config;"

# Users
sqlite3 random_coffee.db "SELECT * FROM users;"

# Subscribers only
sqlite3 random_coffee.db "SELECT * FROM users WHERE is_subscribed = 1;"

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
rm random_coffee.db
```

---

## Scheduler Testing

To test scheduled jobs manually, add a temporary admin command or use Python:

```python
# In Python console
import asyncio
from scheduler.jobs import monthly_matching_job, monthly_followup_job, inactivity_check_job

# You'll need the bot instance
# This is easier done via /force_match command
```

---

## Checklist Summary

| # | Test | Status |
|---|------|--------|
| 1 | Bot setup in group | ⬜ |
| 2 | User subscription (join) | ⬜ |
| 3 | Join without starting bot | ⬜ |
| 4 | User unsubscribe | ⬜ |
| 5 | Check status | ⬜ |
| 6 | List subscribers | ⬜ |
| 7 | Force match | ⬜ |
| 8 | Duplicate matching prevention | ⬜ |
| 9 | Follow-up Yes | ⬜ |
| 10 | Follow-up No | ⬜ |
| 11 | My status command | ⬜ |
| 12 | No repeat matches | ⬜ |
| 13 | Odd subscribers (triple) | ⬜ |
| 14 | Not enough subscribers | ⬜ |
| 15 | Blocked bot handling | ⬜ |
| 16 | Inactivity removal | ⬜ |
| 17 | Request different match | ⬜ |
