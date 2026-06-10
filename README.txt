# Telegram Bot

## Files
- bot/bot.py        — Main bot + Flask admin panel
- bot/database.py   — SQLite database (users, buttons, admins)
- bot/templates/    — HTML admin panel pages

## Setup
1. Install Python 3.11+
2. pip install -r bot/requirements.txt
3. Set environment variables (see .env.example)
4. Run: python3 bot/bot.py

## Environment Variables
TELEGRAM_BOT_TOKEN  — From @BotFather on Telegram
TELEGRAM_ADMIN_ID   — Your Telegram numeric ID (send /myid to your bot)
ADMIN_PASSWORD      — Web panel password (default: admin123)
SESSION_SECRET      — Random secret for Flask sessions

## Web Admin Panel
  /dashboard  — Stats overview
  /users      — User list, grant/remove premium
  /buttons    — Manage bot reply buttons
  /broadcast  — Send message to all users