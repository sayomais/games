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
TOKEN = os.environ.get("7749164155:AAF7vnOvDMTPrbEhnZn6IPA0ehptV4ojHxU")
ADMIN_IDS = [int(admin_id) for admin_id in os.environ.get("6440962840", "").split(",") if admin_id]

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
    {
        "question": "What is 2 + 2?",
        "options": ["3", "4", "5", "22"],
        "answer": 1,  # 4
    },
    {
        "question": "Who wrote 'Romeo and Juliet'?",
        "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
        "answer": 1,  # William Shakespeare
    },
    {
        "question": "What is the largest ocean on Earth?",
        "options": ["Atlantic Ocean", "Indian Ocean", "Arctic Ocean", "Pacific Ocean"],
        "answer": 3,  # Pacific Ocean
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

def award_random_points(user_id, base_amount=10, multiplier_range=(1, 5)):
    """Award random points to a user with a chance for bonus"""
    user = get_user(user_id)
    
    # Base points
    multiplier = random.randint(*multiplier_range)
    points = base_amount * multiplier
    
    # Lucky bonus (10% chance)
    if random.random() < 0.1:
        bonus = random.randint(1, 5) * 10
        points += bonus
        bonus_msg = f"\n🍀 Lucky bonus: +{bonus} credits!"
    else:
        bonus_msg = ""
    
    # Premium bonus
    if is_premium(user_id):
        premium_bonus = points // 2  # 50% bonus for premium
        points += premium_bonus
        premium_msg = f"\n💎 Premium bonus: +{premium_bonus} credits!"
    else:
        premium_msg = ""
    
    user["credits"] += points
    user["total_earnings"] += points
    update_user(user_id, user)
    
    return points, f"{bonus_msg}{premium_msg}"

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    welcome_message = (
        f"🎮 Welcome to the Game Bot, {user.first_name}!\n\n"
        f"You have {user_data['credits']} credits to start.\n"
        f"Use /help to see available commands.\n\n"
        f"💎 Premium Features:\n"
        f"- Double credits rewards\n"
        f"- Exclusive games\n"
        f"- Reduced game costs\n"
        f"- Priority support\n\n"
        f"Win games to earn premium status!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
        [InlineKeyboardButton("💰 Check Credits", callback_data="credits")],
        [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_user_admin = is_admin(user_id)
    
    help_message = (
        "📚 Game Bot Commands\n\n"
        "Basic Commands:\n"
        "/start - Initialize the bot\n"
        "/games - Show available games\n"
        "/credits - Check your credit balance\n"
        "/daily - Claim daily reward\n"
        "/stats - View your statistics\n"
        "/help - Show this help message\n\n"
        "Game Commands:\n"
        "/dice - Roll the dice game\n"
        "/number - Number guessing game\n"
        "/quiz - Trivia quiz game\n"
        "/rps - Rock Paper Scissors\n"
    )
    
    if is_premium(user_id):
        help_message += (
            "\nPremium Games:\n"
            "/slots - Premium slots game\n"
            "/blackjack - Premium blackjack game\n"
        )
    
    if is_user_admin:
        help_message += (
            "\n🔑 Admin Commands:\n"
            "/givepremium <username> <days> - Give premium status\n"
            "/revokepremium <username> - Revoke premium status\n"
            "/addcredits <username> <amount> - Add credits\n"
            "/stats_global - View bot statistics\n"
        )
    
    await update.message.reply_text(help_message)

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    premium_status = "💎 Premium" if is_premium(user_id) else "Free"
    
    premium_expiry = ""
    if user_data["is_premium"] and user_data["premium_expiry"]:
        expiry_date = datetime.fromisoformat(user_data["premium_expiry"])
        premium_expiry = f"\nPremium expires: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
    
    message = (
        f"💰 Your Credits: {user_data['credits']}\n"
        f"🎯 Status: {premium_status}{premium_expiry}\n\n"
        f"Daily Rewards:\n"
        f"- Free users: 50 credits\n"
        f"- Premium users: 100 credits\n\n"
        f"Use /games to start earning more credits!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
        [InlineKeyboardButton("🎁 Claim Daily", callback_data="daily")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    message = "🎮 Available Games:\n\n"
    
    # Free games
    message += "Free Games:\n"
    for game, details in GAMES.items():
        if details.get("premium_only", False):
            continue
        cost = details["premium_cost"] if is_user_premium else details["cost"]
        message += f"/{game} - Cost: {cost} credits\n"
    
    # Premium games
    if is_user_premium:
        message += "\n💎 Premium Games:\n"
        for game, details in GAMES.items():
            if details.get("premium_only", False):
                message += f"/{game} - Cost: {details['premium_cost']} credits\n"
    else:
        message += "\n💎 Premium Games (unlock with premium status):\n"
        for game, details in GAMES.items():
            if details.get("premium_only", False):
                message += f"/{game} - Requires premium\n"
    
    message += f"\n💰 Your Credits: {user_data['credits']}"
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 Dice", callback_data="play_dice"),
            InlineKeyboardButton("🔢 Number", callback_data="play_number"),
        ],
        [
            InlineKeyboardButton("❓ Quiz", callback_data="play_quiz"),
            InlineKeyboardButton("✂️ RPS", callback_data="play_rps"),
        ],
    ]
    
    if is_user_premium:
        keyboard.append([
            InlineKeyboardButton("🎰 Slots", callback_data="play_slots"),
            InlineKeyboardButton("♠️ Blackjack", callback_data="play_blackjack"),
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    
    # Check if user has claimed daily reward today
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id_str in daily_claims and daily_claims[user_id_str] == today:
        await update.message.reply_text(
            "You've already claimed your daily reward today. Come back tomorrow!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")
            ]])
        )
        return
    
    # Give daily reward based on premium status
    user_data = get_user(user_id)
    reward = 100 if is_premium(user_id) else 50
    user_data["credits"] += reward
    user_data["total_earnings"] += reward
    update_user(user_id, user_data)
    
    # Update daily claim
    daily_claims[user_id_str] = today
    save_data()
    
    await update.message.reply_text(
        f"✅ Daily reward claimed!\n\n"
        f"You received {reward} credits.\n"
        f"Current balance: {user_data['credits']} credits.\n\n"
        f"{'💎 Premium bonus applied!' if is_premium(user_id) else '💡 Tip: Premium users get double daily rewards!'}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
        ])
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    win_rate = 0
    if user_data["games_played"] > 0:
        win_rate = (user_data["games_won"] / user_data["games_played"]) * 100
    
    message = (
        f"📊 Your Statistics\n\n"
        f"Games Played: {user_data['games_played']}\n"
        f"Games Won: {user_data['games_won']}\n"
        f"Win Rate: {win_rate:.1f}%\n"
        f"Total Earnings: {user_data['total_earnings']} credits\n"
        f"Current Balance: {user_data['credits']} credits\n"
        f"Status: {'💎 Premium' if is_premium(user_id) else 'Free'}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

# Admin commands
async def give_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⚠️ You are not authorized to use admin commands.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /givepremium <username> <days>")
        return
    
    target_username = context.args[0].replace("@", "")
    days = int(context.args[1])
    
    # Find user by username
    target_user_id = None
    for uid, data in users.items():
        if data.get("username") == target_username:
            target_user_id = uid
            break
    
    if not target_user_id:
        await update.message.reply_text(f"⚠️ User {target_username} not found.")
        return
    
    # Update user's premium status
    user_data = get_user(int(target_user_id))
    user_data["is_premium"] = True
    
    expiry_date = datetime.now() + timedelta(days=days)
    user_data["premium_expiry"] = expiry_date.isoformat()
    
    update_user(int(target_user_id), user_data)
    
    await update.message.reply_text(f"✅ Gave {days} days of premium to @{target_username}")
    
    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=f"🎉 You have been given {days} days of premium status by an admin!"
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

async def revoke_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⚠️ You are not authorized to use admin commands.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /revokepremium <username>")
        return
    
    target_username = context.args[0].replace("@", "")
    
    # Find user by username
    target_user_id = None
    for uid, data in users.items():
        if data.get("username") == target_username:
            target_user_id = uid
            break
    
    if not target_user_id:
        await update.message.reply_text(f"⚠️ User {target_username} not found.")
        return
    
    # Update user's premium status
    user_data = get_user(int(target_user_id))
    user_data["is_premium"] = False
    user_data["premium_expiry"] = None
    
    update_user(int(target_user_id), user_data)
    
    await update.message.reply_text(f"✅ Revoked premium from @{target_username}")
    
    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="⚠️ Your premium status has been revoked by an admin."
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⚠️ You are not authorized to use admin commands.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcredits <username> <amount>")
        return
    
    target_username = context.args[0].replace("@", "")
    amount = int(context.args[1])
    
    # Find user by username
    target_user_id = None
    for uid, data in users.items():
        if data.get("username") == target_username:
            target_user_id = uid
            break
    
    if not target_user_id:
        await update.message.reply_text(f"⚠️ User {target_username} not found.")
        return
    
    # Update user's credits
    user_data = get_user(int(target_user_id))
    user_data["credits"] += amount
    user_data["total_earnings"] += amount
    
    update_user(int(target_user_id), user_data)
    
    await update.message.reply_text(f"✅ Added {amount} credits to @{target_username}")
    
    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text=f"🎉 You have been given {amount} credits by an admin!"
        )
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")

async def stats_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⚠️ You are not authorized to use admin commands.")
        return
    
    total_users = len(users)
    premium_users = sum(1 for uid, data in users.items() if data.get("is_premium", False))
    total_credits = sum(data.get("credits", 0) for data in users.values())
    total_games = sum(data.get("games_played", 0) for data in users.values())
    
    message = (
        f"📊 Bot Statistics\n\n"
        f"Total Users: {total_users}\n"
        f"Premium Users: {premium_users}\n"
        f"Total Credits: {total_credits}\n"
        f"Average Credits: {total_credits // total_users if total_users else 0}\n"
        f"Total Games Played: {total_games}\n"
    )
    
    await update.message.reply_text(message)

# Game implementations
async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    # Check if user has enough credits
    game_cost = GAMES["dice"]["premium_cost"] if is_user_premium else GAMES["dice"]["cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Generate target number
    target = random.randint(1, 6)
    games[user_id] = {
        "type": "dice",
        "target": target,
        "attempts": 0,
        "max_attempts": 3,
        "cost": game_cost
    }
    
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="guess_1"),
            InlineKeyboardButton("2", callback_data="guess_2"),
            InlineKeyboardButton("3", callback_data="guess_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="guess_4"),
            InlineKeyboardButton("5", callback_data="guess_5"),
            InlineKeyboardButton("6", callback_data="guess_6"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎲 Dice Game Started!\n\n"
        f"I'm thinking of a number between 1 and 6.\n"
        f"You have 3 attempts to guess it.\n"
        f"Cost: {game_cost} credits\n\n"
        f"Select a number to guess:",
        reply_markup=reply_markup
    )

async def number_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    # Check if user has enough credits
    game_cost = GAMES["number"]["premium_cost"] if is_user_premium else GAMES["number"]["cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Generate target number
    target = random.randint(1, 100)
    games[user_id] = {
        "type": "number",
        "target": target,
        "attempts": 0,
        "max_attempts": 5,
        "cost": game_cost
    }
    
    await update.message.reply_text(
        f"🔢 Number Guessing Game Started!\n\n"
        f"I'm thinking of a number between 1 and 100.\n"
        f"You have 5 attempts to guess it.\n"
        f"Cost: {game_cost} credits\n\n"
        f"Type a number between 1 and 100 to guess:"
    )

async def quiz_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    # Check if user has enough credits
    game_cost = GAMES["quiz"]["premium_cost"] if is_user_premium else GAMES["quiz"]["cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Select random question
    question_data = random.choice(QUIZ_QUESTIONS)
    games[user_id] = {
        "type": "quiz",
        "question": question_data["question"],
        "options": question_data["options"],
        "answer": question_data["answer"],
        "cost": game_cost
    }
    
    # Create keyboard with options
    keyboard = []
    for i, option in enumerate(question_data["options"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"answer_{i}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"❓ Quiz Game Started!\n\n"
        f"{question_data['question']}\n"
        f"Cost: {game_cost} credits\n\n"
        f"Select your answer:",
        reply_markup=reply_markup
    )

async def rps_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    # Check if user has enough credits
    game_cost = GAMES["rps"]["premium_cost"] if is_user_premium else GAMES["rps"]["cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    games[user_id] = {
        "type": "rps",
        "cost": game_cost
    }
    
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("📄 Paper", callback_data="rps_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✂️ Rock Paper Scissors Game Started!\n\n"
        f"Cost: {game_cost} credits\n\n"
        f"Make your choice:",
        reply_markup=reply_markup
    )

async def slots_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Check if user is premium
    if not is_premium(user_id):
        await update.message.reply_text(
            "⭐ This is a premium game!\n\n"
            "You need to be a premium user to play slots.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
        return
    
    # Check if user has enough credits
    game_cost = GAMES["slots"]["premium_cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Generate slot results
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    
    # Calculate winnings
    winnings = 0
    
    if result[0] == result[1] == result[2]:
        # All three match - big win
        if result[0] == "7️⃣":
            winnings = game_cost * 50  # Jackpot
        elif result[0] == "💎":
            winnings = game_cost * 20
        else:
            winnings = game_cost * 10
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        # Two match - small win
        winnings = game_cost * 2
    
    # Update credits if won
    if winnings > 0:
        user_data["credits"] += winnings
        user_data["total_earnings"] += winnings
        user_data["games_won"] += 1
        update_user(user_id, user_data)
    
    # Result message
    result_str = " | ".join(result)
    
    if winnings > 0:
        message = (
            f"🎰 Slots Result\n\n"
            f"{result_str}\n\n"
            f"🎉 You won {winnings} credits!"
        )
    else:
        message = (
            f"🎰 Slots Result\n\n"
            f"{result_str}\n\n"
            f"😢 You lost {game_cost} credits."
        )
    
    keyboard = [
        [InlineKeyboardButton("🎰 Spin Again", callback_data="play_slots")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def blackjack_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    # Check if user is premium
    if not is_premium(user_id):
        await update.message.reply_text(
            "⭐ This is a premium game!\n\n"
            "You need to be a premium user to play blackjack.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
        return
    
    # Check if user has enough credits
    game_cost = GAMES["blackjack"]["premium_cost"]
    
    if user_data["credits"] < game_cost:
        await update.message.reply_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Initialize blackjack game
    deck = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"] * 4
    random.shuffle(deck)
    
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    
    games[user_id] = {
        "type": "blackjack",
        "deck": deck,
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "cost": game_cost,
        "status": "playing"
    }
    
    # Calculate initial scores
    player_score = calculate_blackjack_score(player_hand)
    dealer_score = calculate_blackjack_score([dealer_hand[0], "?"])
    
    # Check for natural blackjack
    if player_score == 21:
        return await end_blackjack(update, context, user_id, "blackjack")
    
    keyboard = [
        [
            InlineKeyboardButton("🎯 Hit", callback_data="bj_hit"),
            InlineKeyboardButton("🛑 Stand", callback_data="bj_stand"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"♠️ Blackjack Game Started!\n\n"
        f"Your hand: {' '.join(player_hand)} (Score: {player_score})\n"
        f"Dealer shows: {dealer_hand[0]} ?\n\n"
        f"What would you like to do?",
        reply_markup=reply_markup
    )

def calculate_blackjack_score(hand):
    score = 0
    aces = 0
    
    for card in hand:
        if card == "?":
            continue
        elif card in ["J", "Q", "K"]:
            score += 10
        elif card == "A":
            aces += 1
            score += 11
        else:
            score += int(card)
    
    # Adjust for aces
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    
    return score

async def end_blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, result):
    game = games.pop(user_id, None)
    if not game:
        return
    
    user_data = get_user(user_id)
    
    player_score = calculate_blackjack_score(game["player_hand"])
    dealer_score = calculate_blackjack_score(game["dealer_hand"])
    
    winnings = 0
    
    if result == "blackjack":
        winnings = int(game["cost"] * 2.5)  # Blackjack pays 3:2
        message = (
            f"♠️ Blackjack Result\n\n"
            f"Your hand: {' '.join(game['player_hand'])} (Score: {player_score})\n"
            f"Dealer's hand: {' '.join(game['dealer_hand'])} (Score: {dealer_score})\n\n"
            f"🎉 BLACKJACK! You won {winnings} credits!"
        )
    elif result == "win":
        winnings = game["cost"] * 2
        message = (
            f"♠️ Blackjack Result\n\n"
            f"Your hand: {' '.join(game['player_hand'])} (Score: {player_score})\n"
            f"Dealer's hand: {' '.join(game['dealer_hand'])} (Score: {dealer_score})\n\n"
            f"🎉 You won {winnings} credits!"
        )
    elif result == "push":
        winnings = game["cost"]  # Return the bet
        message = (
            f"♠️ Blackjack Result\n\n"
            f"Your hand: {' '.join(game['player_hand'])} (Score: {player_score})\n"
            f"Dealer's hand: {' '.join(game['dealer_hand'])} (Score: {dealer_score})\n\n"
            f"🤝 Push! Your bet of {winnings} credits has been returned."
        )
    else:  # lose
        message = (
            f"♠️ Blackjack Result\n\n"
            f"Your hand: {' '.join(game['player_hand'])} (Score: {player_score})\n"
            f"Dealer's hand: {' '.join(game['dealer_hand'])} (Score: {dealer_score})\n\n"
            f"😢 You lost {game['cost']} credits."
        )
    
    # Update credits if won
    if winnings > 0:
        user_data["credits"] += winnings
        user_data["total_earnings"] += winnings
        
        if result != "push":
            user_data["games_won"] += 1
        
        update_user(user_id, user_data)
    
    keyboard = [
        [InlineKeyboardButton("♠️ Play Again", callback_data="play_blackjack")],
        [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Check if this is a callback query or a message
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id, text=message, reply_markup=reply_markup)

# Callback query handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    await query.answer()
    
    if data == "menu":
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
            [InlineKeyboardButton("💰 Check Credits", callback_data="credits")],
            [InlineKeyboardButton("🎁 Claim Daily", callback_data="daily")],
            [InlineKeyboardButton("📊 My Stats", callback_data="stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎮 Game Bot - Main Menu", reply_markup=reply_markup)
    
    elif data == "games":
        user_data = get_user(user_id)
        is_user_premium = is_premium(user_id)
        
        message = "🎮 Available Games:\n\n"
        
        # Free games
        message += "Free Games:\n"
        for game, details in GAMES.items():
            if details.get("premium_only", False):
                continue
            cost = details["premium_cost"] if is_user_premium else details["cost"]
            message += f"/{game} - Cost: {cost} credits\n"
        
        # Premium games
        if is_user_premium:
            message += "\n💎 Premium Games:\n"
            for game, details in GAMES.items():
                if details.get("premium_only", False):
                    message += f"/{game} - Cost: {details['premium_cost']} credits\n"
        else:
            message += "\n💎 Premium Games (unlock with premium status):\n"
            for game, details in GAMES.items():
                if details.get("premium_only", False):
                    message += f"/{game} - Requires premium\n"
        
        message += f"\n💰 Your Credits: {user_data['credits']}"
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Dice", callback_data="play_dice"),
                InlineKeyboardButton("🔢 Number", callback_data="play_number"),
            ],
            [
                InlineKeyboardButton("❓ Quiz", callback_data="play_quiz"),
                InlineKeyboardButton("✂️ RPS", callback_data="play_rps"),
            ],
        ]
        
        if is_user_premium:
            keyboard.append([
                InlineKeyboardButton("🎰 Slots", callback_data="play_slots"),
                InlineKeyboardButton("♠️ Blackjack", callback_data="play_blackjack"),
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    elif data == "credits":
        user_data = get_user(user_id)
        
        premium_status = "💎 Premium" if is_premium(user_id) else "Free"
        
        premium_expiry = ""
        if user_data["is_premium"] and user_data["premium_expiry"]:
            expiry_date = datetime.fromisoformat(user_data["premium_expiry"])
            premium_expiry = f"\nPremium expires: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
        
        message = (
            f"💰 Your Credits: {user_data['credits']}\n"
            f"🎯 Status: {premium_status}{premium_expiry}\n\n"
            f"Daily Rewards:\n"
            f"- Free users: 50 credits\n"
            f"- Premium users: 100 credits\n\n"
            f"Use /games to start earning more credits!"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
            [InlineKeyboardButton("🎁 Claim Daily", callback_data="daily")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    elif data == "daily":
        user_id_str = str(user_id)
        
        # Check if user has claimed daily reward today
        today = datetime.now().strftime("%Y-%m-%d")
        if user_id_str in daily_claims and daily_claims[user_id_str] == today:
            await query.edit_message_text(
                "You've already claimed your daily reward today. Come back tomorrow!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")
                ]])
            )
            return
        
        # Give daily reward based on premium status
        user_data = get_user(user_id)
        reward = 100 if is_premium(user_id) else 50
        user_data["credits"] += reward
        user_data["total_earnings"] += reward
        update_user(user_id, user_data)
        
        # Update daily claim
        daily_claims[user_id_str] = today
        save_data()
        
        await query.edit_message_text(
            f"✅ Daily reward claimed!\n\n"
            f"You received {reward} credits.\n"
            f"Current balance: {user_data['credits']} credits.\n\n"
            f"{'💎 Premium bonus applied!' if is_premium(user_id) else '💡 Tip: Premium users get double daily rewards!'}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Play Games", callback_data="games")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
    
    elif data == "stats":
        user_data = get_user(user_id)
        
        win_rate = 0
        if user_data["games_played"] > 0:
            win_rate = (user_data["games_won"] / user_data["games_played"]) * 100
        
        message = (
            f"📊 Your Statistics\n\n"
            f"Games Played: {user_data['games_played']}\n"
            f"Games Won: {user_data['games_won']}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Total Earnings: {user_data['total_earnings']} credits\n"
            f"Current Balance: {user_data['credits']} credits\n"
            f"Status: {'💎 Premium' if is_premium(user_id) else 'Free'}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    # Game start callbacks
    elif data.startswith("play_"):
        game_type = data.split("_")[1]
        
        if game_type == "dice":
            await handle_play_dice(query, context)
        elif game_type == "number":
            await handle_play_number(query, context)
        elif game_type == "quiz":
            await handle_play_quiz(query, context)
        elif game_type == "rps":
            await handle_play_rps(query, context)
        elif game_type == "slots":
            await handle_play_slots(query, context)
        elif game_type == "blackjack":
            await handle_play_blackjack(query, context)
    
    # Game action callbacks
    elif data.startswith("guess_"):
        guess = int(data.split("_")[1])
        await handle_dice_guess(query, context, guess)
    
    elif data.startswith("answer_"):
        answer_idx = int(data.split("_")[1])
        await handle_quiz_answer(query, context, answer_idx)
    
    elif data.startswith("rps_"):
        choice = data.split("_")[1]
        await handle_rps_choice(query, context, choice)
    
    elif data.startswith("bj_"):
        action = data.split("_")[1]
        await handle_blackjack_action(query, context, action)

# Game callback handlers
async def handle_play_dice(query, context):
    user_id = query.from_user.id
    user_data = get_user(user_id)
    is_user_premium = is_premium(user_id)
    
    # Check if user has enough credits
    game_cost = GAMES["dice"]["premium_cost"] if is_user_premium else GAMES["dice"]["cost"]
    
    if user_data["credits"] < game_cost:
        await query.edit_message_text(
            f"You don't have enough credits to play. You need {game_cost} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Claim Daily Reward", callback_data="daily")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")],
            ])
        )
        return
    
    # Deduct credits
    user_data["credits"] -= game_cost
    user_data["games_played"] += 1
    update_user(user_id, user_data)
    
    # Generate target number
    target = random.randint(1, 6)
    games[user_id] = {
        "type": "dice",
        "target": target,
        "attempts": 0,
        "max_attempts": 3,
        "cost": game_cost
    }
    
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="guess_1"),
            InlineKeyboardButton("2", callback_data="guess_2"),
            InlineKeyboardButton("3", callback_data="guess_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="guess_4"),
            InlineKeyboardButton("5", callback_data="guess_5"),
            InlineKeyboardButton("6", callback_data="guess_6"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🎲 Dice Game Started!\n\n"
        f"I'm thinking of a number between 1 and 6.\n"
        f"You have 3 attempts to guess it.\n"
        f"Cost: {game_cost} credits\n\n"
        f"Select a number to guess:",
        reply_markup=reply_markup
    )

async def handle_dice_guess(query, context, guess):
    user_id = query.from_user.id
    
    if user_id not in games or games[user_id]["type"] != "dice":
        await query.edit_message_text(
            "No active dice game found. Start a new game with /dice",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Games", callback_data="games")
            ]])
        )
        return
    
    game = games[user_id]
    game["attempts"] += 1
    
    if guess == game["target"]:
        # Win
        reward = game["cost"] * 3
        user_data = get_user(user_id)
        user_data["credits"] += reward
        user_data["total_earnings"] += reward
        user_data["games_won"] += 1
        update_user(user_id, user_data)
        
        # Check for premium upgrade
        await check_premium_upgrade(query, context, user_id)
        
        # Award random bonus points
        bonus_points, bonus_msg = award_random_points(user_id)
        
        del games[user_id]
        
        await query.edit_message_text(
            f"🎉 Congratulations! You guessed correctly: {guess}\n\n"
            f"You won {reward} credits!\n"
            f"+ {bonus_points} bonus points!{bonus_msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Play Again", callback_data="play_dice")],
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
    elif game["attempts"] >= game["max_attempts"]:
        # Game over
        del games[user_id]
        
        await query.edit_message_text(
            f"Game Over! You've used all your attempts.\n"
            f"The correct number was {game['target']}.\n\n"
            f"You lost {game['cost']} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Try Again", callback_data="play_dice")],
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
    else:
        # Continue
        keyboard = [
            [
                InlineKeyboardButton("1", callback_data="guess_1"),
                InlineKeyboardButton("2", callback_data="guess_2"),
                InlineKeyboardButton("3", callback_data="guess_3"),
            ],
            [
                InlineKeyboardButton("4", callback_data="guess_4"),
                InlineKeyboardButton("5", callback_data="guess_5"),
                InlineKeyboardButton("6", callback_data="guess_6"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Wrong guess! The number is {guess < game['target'] and 'higher' or 'lower'} than {guess}.\n\n"
            f"Attempts left: {game['max_attempts'] - game['attempts']}\n\n"
            f"Try again with a number between 1 and 6:",
            reply_markup=reply_markup
        )

# Similar handlers for other games...

async def check_premium_upgrade(query, context, user_id):
    """Check if user qualifies for premium upgrade after winning"""
    user_data = get_user(user_id)
    
    # If already premium, do nothing
    if is_premium(user_id):
        return
    
    # Check win streak or other conditions for premium
    if user_data["games_won"] >= 10 and random.random() < 0.2:  # 20% chance after 10 wins
        # Award premium status
        user_data["is_premium"] = True
        expiry_date = datetime.now() + timedelta(days=3)  # 3 days of premium
        user_data["premium_expiry"] = expiry_date.isoformat()
        update_user(user_id, user_data)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 Congratulations! You've been awarded 3 days of premium status for your winning streak!\n\n"
                 f"Enjoy premium benefits until {expiry_date.strftime('%Y-%m-%d %H:%M')}!"
        )

# Main function
def main():
    """Start the bot."""
    # Load saved data
    load_data()
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("credits", credits_command))
    application.add_handler(CommandHandler("games", games_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Game commands
    application.add_handler(CommandHandler("dice", dice_game))
    application.add_handler(CommandHandler("number", number_game))
    application.add_handler(CommandHandler("quiz", quiz_game))
    application.add_handler(CommandHandler("rps", rps_game))
    application.add_handler(CommandHandler("slots", slots_game))
    application.add_handler(CommandHandler("blackjack", blackjack_game))
    
    # Admin commands
    application.add_handler(CommandHandler("givepremium", give_premium))
    application.add_handler(CommandHandler("revokepremium", revoke_premium))
    application.add_handler(CommandHandler("addcredits", add_credits))
    application.add_handler(CommandHandler("stats_global", stats_global))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for number guessing game
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for games like number guessing"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in games:
        return
    
    game = games[user_id]
    
    if game["type"] == "number":
        try:
            guess = int(text)
            await handle_number_guess(update, context, guess)
        except ValueError:
            await update.message.reply_text("Please enter a valid number between 1 and 100.")

async def handle_number_guess(update: Update, context: ContextTypes.DEFAULT_TYPE, guess):
    user_id = update.effective_user.id
    
    if user_id not in games or games[user_id]["type"] != "number":
        await update.message.reply_text(
            "No active number game found. Start a new game with /number",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Games", callback_data="games")
            ]])
        )
        return
    
    game = games[user_id]
    game["attempts"] += 1
    
    if guess == game["target"]:
        # Win
        reward = game["cost"] * 4  # Higher reward for harder game
        user_data = get_user(user_id)
        user_data["credits"] += reward
        user_data["total_earnings"] += reward
        user_data["games_won"] += 1
        update_user(user_id, user_data)
        
        # Check for premium upgrade
        await check_premium_upgrade(update, context, user_id)
        
        # Award random bonus points
        bonus_points, bonus_msg = award_random_points(user_id)
        
        del games[user_id]
        
        await update.message.reply_text(
            f"🎉 Congratulations! You guessed correctly: {guess}\n\n"
            f"You won {reward} credits!\n"
            f"+ {bonus_points} bonus points!{bonus_msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Play Again", callback_data="play_number")],
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
    elif game["attempts"] >= game["max_attempts"]:
        # Game over
        del games[user_id]
        
        await update.message.reply_text(
            f"Game Over! You've used all your attempts.\n"
            f"The correct number was {game['target']}.\n\n"
            f"You lost {game['cost']} credits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Try Again", callback_data="play_number")],
                [InlineKeyboardButton("🔙 Back to Games", callback_data="games")],
            ])
        )
    else:
        # Continue
        hint = "higher" if guess < game["target"] else "lower"
        
        await update.message.reply_text(
            f"Wrong guess! The number is {hint} than {guess}.\n\n"
            f"Attempts left: {game['max_attempts'] - game['attempts']}\n\n"
            f"Try again with a number between 1 and 100:"
        )

if __name__ == "__main__":
    main()

