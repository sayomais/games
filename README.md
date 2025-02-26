# Telegram Game Bot

A powerful Telegram bot with multiple games, credit system, and premium features.

## Features

- Multiple games: Dice, Number Guessing, Quiz, Rock Paper Scissors, Slots, Blackjack
- Credit system for in-game economy
- Premium user status that can be earned by winning games
- Random point rewards and bonuses
- Admin commands for managing users and credits

## Setup

1. Create a new bot with BotFather on Telegram and get your bot token
2. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `ADMIN_IDS`: Comma-separated list of admin user IDs (e.g., "123456789,987654321")
3. Install dependencies: `pip install -r requirements.txt`
4. Run the bot: `python bot.py`

## Commands

### User Commands
- `/start` - Initialize the bot
- `/help` - Show available commands
- `/games` - Show available games
- `/credits` - Check your credit balance
- `/daily` - Claim daily reward
- `/stats` - View your statistics

### Game Commands
- `/dice` - Roll the dice game
- `/number` - Number guessing game
- `/quiz` - Trivia quiz game
- `/rps` - Rock Paper Scissors
- `/slots` - Premium slots game
- `/blackjack` - Premium blackjack game

### Admin Commands
- `/givepremium <username> <days>` - Give premium status
- `/revokepremium <username>` - Revoke premium status
- `/addcredits <username> <amount>` - Add credits
- `/stats_global` - View bot statistics

## Premium Features

- Double credits rewards
- Exclusive games (Slots, Blackjack)
- Reduced game costs
- Random bonus points
- No daily limits

## Deployment

You can deploy this bot on any platform that supports Python, such as:
- Vercel
- Heroku
- PythonAnywhere
- AWS Lambda
- Google Cloud Functions

Make sure to set up the appropriate environment variables on your hosting platform.

