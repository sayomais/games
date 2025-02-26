import os
import random
import json
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.environ.get("BOT_TOKEN")  # Set your bot token in environment variables
ADMIN_IDS = [int(admin_id) for admin_id in os.environ.get("ADMIN_IDS", "").split(",") if admin_id]

# Data storage (in a real application, use a database)
users = {}
games = {}
daily_claims = {}

# Game configurations
GAMES = {
    "dice": {"cost": 10, "premium_cost": 5},
    "number": {"cost": 15, "premium_cost": 7},
    "quiz": {"cost": 20, "premium_cost": 10},
    "rps": {"cost": 10, "premium_cost": 5},  # Rock Paper Scissors
    "slots": {"cost": 25, "premium_cost": 12, "premium_only": True},
    "blackjack": {"cost": 50, "premium_cost": 25, "premium_only": True},
}

# Quiz questions
QUIZ_QUESTIONS = [
    {
        "question": "What is the capital of France?",
        "options": ["London", "Berlin", "Paris", "Madrid"],
        "answer": 2,  # Paris (0-indexed)
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "options": ["Venus", "Mars", "Jupiter", "Saturn"],
        "answer": 1,  # Mars
    },
]

# Save and load data functions
def save_data():
    with open("users.json", "w") as f:
        json.dump(users, f)
    with open("daily_claims.json", "w") as f:
        json.dump(daily_claims, f)

def load_data():
    global users, daily_claims
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
        with open("daily_claims.json", "r") as f:
            daily_claims = json.load(f)
    except FileNotFoundError:
        users = {}
        daily_claims = {}

# Helper functions
def get_user(user_id):
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "credits": 100,
            "is_premium": False,
            "premium_expiry": None,
            "games_played": 0,
            "games_won": 0,
            "total_earnings": 0,
        }
    return users[user_id_str]

def update_user(user_id, data):
    user_id_str = str(user_id)
    users[user_id_str].update(data)
    save_data()

def is_premium(user_id):
    user = get_user(user_id)
    if not user["is_premium"]:
        return False
    
    if user["premium_expiry"] is None:
        return True
    
    expiry = datetime.fromisoformat(user["premium_expiry"])
    if expiry > datetime.now():
        return True
    
    # Premium expired
    user["is_premium"] = False
    update_user(user_id, user)
    return False

def is_admin(user_id):
    return user_id in ADMIN_IDS

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)  # Ensure user exists
    
    welcome_message = (
        f"🎮 Welcome to the Game Bot, {user.first_name}!\n\n"
        "Use /help to see available commands."
    )
    
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "📚 Game Bot Commands\n"
        "/start - Start the bot\n"
        "/games - Show available games\n"
        "/credits - Check your balance\n"
        "/daily - Claim daily reward\n"
        "/stats - View statistics\n"
        "/help - Show help message"
    )
    await update.message.reply_text(help_message)

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    premium_status = "💎 Premium" if is_premium(user_id) else "Free"
    
    message = f"💰 Your Credits: {user_data['credits']}\n🎯 Status: {premium_status}"
    
    await update.message.reply_text(message)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    
    if daily_claims.get(str(user_id)) == today:
        await update.message.reply_text("You've already claimed your daily reward today.")
        return
    
    reward = 100 if is_premium(user_id) else 50
    user_data = get_user(user_id)
    user_data["credits"] += reward
    update_user(user_id, user_data)
    
    daily_claims[str(user_id)] = today
    save_data()
    
    await update.message.reply_text(f"✅ You received {reward} credits.")

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🎮 Available Games:\n"
    for game, details in GAMES.items():
        cost = details["premium_cost"] if is_premium(update.effective_user.id) else details["cost"]
        message += f"/{game} - Cost: {cost} credits\n"
    
    await update.message.reply_text(message)

# Game handlers
async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    game_cost = GAMES["dice"]["premium_cost"] if is_premium(user_id) else GAMES["dice"]["cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text("Not enough credits!")
        return
    
    user_data["credits"] -= game_cost
    update_user(user_id, user_data)
    
    dice_roll = random.randint(1, 6)
    win = dice_roll > 3  # 50% chance to win
    if win:
        reward = game_cost * 2
        user_data["credits"] += reward
        user_data["games_won"] += 1
        await update.message.reply_text(f"🎲 You rolled {dice_roll} and won {reward} credits!")
    else:
        await update.message.reply_text(f"🎲 You rolled {dice_roll} and lost!")
    
    user_data["games_played"] += 1
    update_user(user_id, user_data)

# Main function
def main():
    load_data()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("credits", credits_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("games", games_command))
    application.add_handler(CommandHandler("dice", dice_game))
    
    application.run_polling()

if __name__ == "__main__":
    main()
