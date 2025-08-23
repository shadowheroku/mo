import random
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.enums import ChatMemberStatus

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ===== CONFIGURATION =====
OWNER_ID = 8429156335  # Replace with your Telegram ID
DEFAULT_BALANCE = 1000
MIN_BET_AMOUNT = 100
DAILY_REWARD = 100
PROMOTION_COST = 1_000_000
TITLE_CHANGE_COST = 100_000

# File paths
DATA_DIR = Path("monic_data")
BALANCE_FILE = DATA_DIR / "balance.json"
DAILY_FILE = DATA_DIR / "daily.json"
SEASON_FILE = DATA_DIR / "season.json"
PROMOTIONS_FILE = DATA_DIR / "promotions.json"
MINES_GAMES_FILE = DATA_DIR / "mines_games.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# ===== DATA MANAGEMENT =====
class DataManager:
    @staticmethod
    def load_json(file_path: Path, default=None):
        """Load JSON data from file"""
        try:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return default if default is not None else {}

    @staticmethod
    def save_json(file_path: Path, data):
        """Save data to JSON file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except IOError:
            return False

# ===== GLOBAL DATA STORAGE =====
user_balance = DataManager.load_json(BALANCE_FILE, {})
daily_claim = DataManager.load_json(DAILY_FILE, {})
season_info = DataManager.load_json(SEASON_FILE, {"season_start": datetime.now().isoformat()})
promotions = DataManager.load_json(PROMOTIONS_FILE, {})
mines_games = DataManager.load_json(MINES_GAMES_FILE, {})

# ===== UTILITY FUNCTIONS =====
def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

def format_number(number: int) -> str:
    """Format numbers with commas for better readability"""
    return f"{number:,}"

def get_user_balance(user_id: str) -> int:
    """Get user balance with default fallback"""
    return user_balance.get(user_id, DEFAULT_BALANCE)

def update_user_balance(user_id: str, amount: int) -> int:
    """Update user balance and return new balance"""
    current_balance = get_user_balance(user_id)
    new_balance = max(0, current_balance + amount)
    user_balance[user_id] = new_balance
    DataManager.save_json(BALANCE_FILE, user_balance)
    return new_balance

def spend_user_balance(user_id: str, amount: int) -> bool:
    """Spend user balance if they have enough coins"""
    if get_user_balance(user_id) < amount:
        return False
    update_user_balance(user_id, -amount)
    return True

def can_claim_daily(user_id: str) -> tuple:
    """Check if user can claim daily reward and return time left if not"""
    now = datetime.now()
    last_claim_str = daily_claim.get(user_id)
    
    if not last_claim_str:
        return True, None
    
    try:
        last_claim = datetime.fromisoformat(last_claim_str)
        time_since_last_claim = now - last_claim
        
        if time_since_last_claim < timedelta(hours=24):
            time_left = timedelta(hours=24) - time_since_last_claim
            return False, time_left
        return True, None
    except (ValueError, TypeError):
        return True, None

# ===== MINES GAME FUNCTIONS =====
def generate_mines_board(size: int = 5, num_mines: int = 5) -> List[str]:
    """Generate a mines game board"""
    board = ["💣"] * num_mines + ["💎"] * (size * size - num_mines)
    random.shuffle(board)
    return board

def render_mines_board(board: List[str], revealed: set, game_id: str = None, 
                      show_all: bool = False) -> InlineKeyboardMarkup:
    """Render the mines game board as inline keyboard"""
    size = 5
    buttons = []
    
    for row in range(size):
        button_row = []
        for col in range(size):
            idx = row * size + col
            if show_all or idx in revealed:
                button_row.append(InlineKeyboardButton(board[idx], callback_data="mines_ignore"))
            else:
                button_row.append(InlineKeyboardButton("⬜", callback_data=f"mines_{game_id}_{idx}"))
        buttons.append(button_row)
    
    if game_id and not show_all:
        buttons.append([
            InlineKeyboardButton("💰 Withdraw", callback_data=f"mines_withdraw_{game_id}"),
            InlineKeyboardButton("🎲 New Game", callback_data="mines_new")
        ])
    
    return InlineKeyboardMarkup(buttons)

def get_mines_multiplier(num_mines: int) -> float:
    """Get multiplier based on number of mines"""
    if num_mines <= 3:
        return 1.0
    elif num_mines <= 6:
        return 1.5
    elif num_mines <= 10:
        return 2.0
    else:
        return 2.5

def generate_game_id() -> str:
    """Generate a unique game ID"""
    return str(random.randint(10000, 99999))

# ===== COMMAND HANDLERS =====
@Gojo.on_message(command("mines"))
async def mines_start(c: Gojo, m: Message):
    """Start a new mines game"""
    args = m.text.split()
    
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        return await m.reply_text(
            "**🎮 Mines Game**\n\n"
            "**Usage:** `/mines <amount> <mines>`\n"
            "• **Amount:** Bet amount (min 100 coins)\n"
            "• **Mines:** Number of mines (3-24)\n\n"
            "**Example:** `/mines 500 5`"
        )
    
    amount, num_mines = int(args[1]), int(args[2])
    user_id = str(m.from_user.id)
    user_name = m.from_user.first_name
    
    # Validate input
    if amount < MIN_BET_AMOUNT:
        return await m.reply_text(f"❌ Minimum bet is {format_number(MIN_BET_AMOUNT)} coins!")
    
    if get_user_balance(user_id) < amount:
        return await m.reply_text(
            f"❌ Not enough coins!\n"
            f"💳 Your balance: {format_number(get_user_balance(user_id))} coins\n"
            f"🎯 Needed: {format_number(amount)} coins"
        )
    
    if num_mines < 3 or num_mines > 24:
        return await m.reply_text("❌ Number of mines must be between 3 and 24!")
    
    # Create game
    game_id = generate_game_id()
    board = generate_mines_board(5, num_mines)
    multiplier = get_mines_multiplier(num_mines)
    
    mines_games[game_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "amount": amount,
        "mines": num_mines,
        "board": board,
        "revealed": set(),
        "multiplier": multiplier,
        "reward": 0,
        "start_time": datetime.now().isoformat()
    }
    
    # Save game data
    DataManager.save_json(MINES_GAMES_FILE, mines_games)
    
    # Deduct bet amount
    spend_user_balance(user_id, amount)
    
    await m.reply_text(
        f"🎮 **Mines Game Started**\n\n"
        f"**Player:** {escape_markdown(user_name)}\n"
        f"**Bet:** {format_number(amount)} coins\n"
        f"**Mines:** {num_mines}\n"
        f"**Multiplier:** {multiplier}x\n"
        f"**Game ID:** `{game_id}`\n\n"
        f"Click on a tile to reveal what's underneath!",
        reply_markup=render_mines_board(board, set(), game_id)
    )

@Gojo.on_callback_query(filters.regex(r"^mines_(\d+)_(\d+)$"))
async def mines_reveal(c: Gojo, q: CallbackQuery):
    """Handle mines game tile reveal"""
    _, game_id, idx_str = q.data.split("_")
    idx = int(idx_str)
    
    if game_id not in mines_games:
        await q.answer("❌ Game expired or not found!", show_alert=True)
        await q.message.edit_reply_markup(render_mines_board([], set(), show_all=True))
        return
    
    game = mines_games[game_id]
    
    # Check if this is the right user
    if str(q.from_user.id) != game["user_id"]:
        await q.answer("⚠️ This is not your game!", show_alert=True)
        return
    
    # Check if already revealed
    if idx in game["revealed"]:
        await q.answer("Already revealed!", show_alert=True)
        return
    
    # Reveal tile
    game["revealed"].add(idx)
    cell = game["board"][idx]
    
    if cell == "💣":  # Mine hit - game over
        # Update message
        await q.message.edit_text(
            f"💥 **Game Over!**\n\n"
            f"**Player:** {escape_markdown(game['user_name'])}\n"
            f"**Bet:** {format_number(game['amount'])} coins\n"
            f"**Mines:** {game['mines']}\n"
            f"**Result:** Hit a mine! 💣\n\n"
            f"💸 Lost: {format_number(game['amount'])} coins\n"
            f"💳 New Balance: {format_number(get_user_balance(game['user_id']))}",
            reply_markup=render_mines_board(game["board"], game["revealed"], show_all=True)
        )
        # Remove game
        if game_id in mines_games:
            del mines_games[game_id]
            DataManager.save_json(MINES_GAMES_FILE, mines_games)
    
    else:  # Gem found
        gem_reward = int(game["amount"] * game["multiplier"])
        game["reward"] += gem_reward
        game["multiplier"] *= 0.95  # Slight reduction in multiplier
        
        # Check if all safe cells are revealed
        safe_cells = 25 - game["mines"]
        if len(game["revealed"]) == safe_cells:
            # Player won!
            update_user_balance(game["user_id"], game["reward"])
            
            await q.message.edit_text(
                f"🎉 **You Won!**\n\n"
                f"**Player:** {escape_markdown(game['user_name'])}\n"
                f"**Bet:** {format_number(game['amount'])} coins\n"
                f"**Mines:** {game['mines']}\n"
                f"**Result:** Cleared all safe cells! 🏆\n\n"
                f"💰 **Won:** {format_number(game['reward'])} coins\n"
                f"💳 **New Balance:** {format_number(get_user_balance(game['user_id']))}",
                reply_markup=render_mines_board(game["board"], game["revealed"], show_all=True)
            )
            
            # Remove game
            if game_id in mines_games:
                del mines_games[game_id]
                DataManager.save_json(MINES_GAMES_FILE, mines_games)
        else:
            # Continue game
            await q.message.edit_text(
                f"💎 **Gem Found!**\n\n"
                f"**Player:** {escape_markdown(game['user_name'])}\n"
                f"**Bet:** {format_number(game['amount'])} coins\n"
                f"**Mines:** {game['mines']}\n"
                f"**Reward:** {format_number(gem_reward)} coins\n"
                f"**Total:** {format_number(game['reward'])} coins\n"
                f"**Multiplier:** {game['multiplier']:.2f}x\n\n"
                f"Keep going or withdraw your earnings!",
                reply_markup=render_mines_board(game["board"], game["revealed"], game_id)
            )
            
            # Save game state
            DataManager.save_json(MINES_GAMES_FILE, mines_games)
    
    await q.answer()

@Gojo.on_callback_query(filters.regex(r"^mines_withdraw_(\d+)$"))
async def mines_withdraw(c: Gojo, q: CallbackQuery):
    """Handle mines game withdrawal"""
    game_id = q.data.split("_")[-1]
    
    if game_id not in mines_games:
        await q.answer("❌ Game expired or not found!", show_alert=True)
        return
    
    game = mines_games[game_id]
    
    # Check if this is the right user
    if str(q.from_user.id) != game["user_id"]:
        await q.answer("⚠️ This is not your game!", show_alert=True)
        return
    
    # Add reward to user balance
    update_user_balance(game["user_id"], game["reward"])
    
    await q.message.edit_text(
        f"💰 **Withdrawn!**\n\n"
        f"**Player:** {escape_markdown(game['user_name'])}\n"
        f"**Bet:** {format_number(game['amount'])} coins\n"
        f"**Mines:** {game['mines']}\n"
        f"**Withdrawn:** {format_number(game['reward'])} coins\n"
        f"💳 **New Balance:** {format_number(get_user_balance(game['user_id']))}",
        reply_markup=render_mines_board(game["board"], game["revealed"], show_all=True)
    )
    
    # Remove game
    if game_id in mines_games:
        del mines_games[game_id]
        DataManager.save_json(MINES_GAMES_FILE, mines_games)
    
    await q.answer()

@Gojo.on_callback_query(filters.regex(r"^mines_new$"))
async def mines_new_game(c: Gojo, q: CallbackQuery):
    """Start a new mines game from callback"""
    await q.message.delete()
    await mines_start(c, q.message)

@Gojo.on_message(command("balance"))
async def balance_cmd(c: Gojo, m: Message):
    """Check user balance"""
    user_id = str(m.from_user.id)
    balance = get_user_balance(user_id)
    
    # Check if user is promoted
    title = ""
    if user_id in promotions:
        title = f" | {promotions[user_id].get('title', 'Coin Master')}"
    
    await m.reply_text(
        f"💳 **Balance Report**\n\n"
        f"**User:** {escape_markdown(m.from_user.first_name)}{title}\n"
        f"**Coins:** {format_number(balance)}\n\n"
        f"Earn more coins by playing games or claiming daily rewards!"
    )

@Gojo.on_message(command("daily"))
async def daily_cmd(c: Gojo, m: Message):
    """Claim daily reward"""
    user_id = str(m.from_user.id)
    user_name = m.from_user.first_name
    
    can_claim, time_left = can_claim_daily(user_id)
    
    if not can_claim:
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        return await m.reply_text(
            f"⏳ **Daily Reward Already Claimed**\n\n"
            f"**Next claim in:** {hours}h {minutes}m\n\n"
            f"Come back later to claim your next reward!"
        )
    
    # Claim daily reward
    new_balance = update_user_balance(user_id, DAILY_REWARD)
    daily_claim[user_id] = datetime.now().isoformat()
    DataManager.save_json(DAILY_FILE, daily_claim)
    
    await m.reply_text(
        f"🎁 **Daily Reward Claimed!**\n\n"
        f"**User:** {escape_markdown(user_name)}\n"
        f"**Reward:** {format_number(DAILY_REWARD)} coins\n"
        f"**New Balance:** {format_number(new_balance)}\n\n"
        f"Come back tomorrow for another reward!"
    )

@Gojo.on_message(command("mgive"))
async def mgive_cmd(c: Gojo, m: Message):
    """Give coins to another user"""
    user_id = str(m.from_user.id)
    user_balance_val = get_user_balance(user_id)
    
    # Parse command arguments
    if m.reply_to_message:
        # Command format: /mgive <amount> (as reply to user)
        if len(m.command) != 2 or not m.command[1].isdigit():
            return await m.reply_text(
                "**Usage:** Reply to a user's message with `/mgive <amount>`\n\n"
                "**Example:** `/mgive 500` (as a reply to someone's message)"
            )
        
        target_user = m.reply_to_message.from_user
        amount = int(m.command[1])
    else:
        # Command format: /mgive @username amount
        if len(m.command) != 3 or not m.command[2].isdigit():
            return await m.reply_text(
                "**Usage:** `/mgive @username <amount>`\n\n"
                "**Example:** `/mgive @username 500`"
            )
        
        try:
            target_user = await c.get_users(m.command[1])
        except:
            return await m.reply_text("❌ User not found!")
        
        amount = int(m.command[2])
    
    # Validate amount
    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")
    
    if user_balance_val < amount:
        return await m.reply_text(
            f"❌ Not enough coins!\n"
            f"💳 Your balance: {format_number(user_balance_val)}\n"
            f"🎯 Needed: {format_number(amount)}"
        )
    
    if target_user.id == m.from_user.id:
        return await m.reply_text("❌ You can't send coins to yourself!")
    
    # Transfer coins
    spend_user_balance(user_id, amount)
    target_new_balance = update_user_balance(str(target_user.id), amount)
    
    await m.reply_text(
        f"✅ **Coins Sent Successfully!**\n\n"
        f"**From:** {escape_markdown(m.from_user.first_name)}\n"
        f"**To:** {escape_markdown(target_user.first_name)}\n"
        f"**Amount:** {format_number(amount)} coins\n\n"
        f"💳 Your new balance: {format_number(get_user_balance(user_id))}\n"
        f"👤 Their new balance: {format_number(target_new_balance)}"
    )

@Gojo.on_message(command("mgift"))
async def mgift_cmd(c: Gojo, m: Message):
    """Owner command to gift coins to users"""
    if m.from_user.id != OWNER_ID:
        return await m.reply_text("❌ Only the bot owner can use this command!")
    
    if not m.reply_to_message:
        return await m.reply_text(
            "**Usage:** Reply to a user's message with `/mgift <amount>`\n\n"
            "**Example:** `/mgift 1000` (as a reply)"
        )
    
    if len(m.command) != 2 or not m.command[1].isdigit():
        return await m.reply_text(
            "**Usage:** `/mgift <amount>` (as a reply to user)\n\n"
            "**Example:** `/mgift 1000`"
        )
    
    amount = int(m.command[1])
    target_user = m.reply_to_message.from_user
    
    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")
    
    # Gift coins
    target_new_balance = update_user_balance(str(target_user.id), amount)
    
    await m.reply_text(
        f"🎁 **Coins Gifted!**\n\n"
        f"**To:** {escape_markdown(target_user.first_name)}\n"
        f"**Amount:** {format_number(amount)} coins\n"
        f"**New Balance:** {format_number(target_new_balance)}"
    )

@Gojo.on_message(command("take"))
async def take_cmd(c: Gojo, m: Message):
    """Take coins from a user (owner only)"""
    if m.from_user.id != OWNER_ID:
        return await m.reply_text("❌ Only the bot owner can use this command!")
    
    if not m.reply_to_message:
        return await m.reply_text(
            "**Usage:** Reply to a user's message with `/take <amount>`\n\n"
            "**Example:** `/take 500` (as a reply)"
        )
    
    if len(m.command) != 2 or not m.command[1].isdigit():
        return await m.reply_text(
            "**Usage:** `/take <amount>` (as a reply to user)\n\n"
            "**Example:** `/take 500`"
        )
    
    amount = int(m.command[1])
    target_user = m.reply_to_message.from_user
    target_user_id = str(target_user.id)
    
    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")
    
    current_balance = get_user_balance(target_user_id)
    if amount > current_balance:
        amount = current_balance  # Take all coins if amount exceeds balance
    
    # Take coins
    new_balance = update_user_balance(target_user_id, -amount)
    
    await m.reply_text(
        f"⚡ **Coins Taken!**\n\n"
        f"**From:** {escape_markdown(target_user.first_name)}\n"
        f"**Amount:** {format_number(amount)} coins\n"
        f"**New Balance:** {format_number(new_balance)}"
    )

@Gojo.on_message(command("top"))
async def top_cmd(c: Gojo, m: Message):
    """Show top coin collectors"""
    if not user_balance:
        return await m.reply_text("No users have collected coins yet!")
    
    # Get top 10 users
    top_users = sorted(user_balance.items(), key=lambda x: x[1], reverse=True)[:10]
    
    leaderboard = "🏆 **Top Coin Collectors**\n\n"
    
    for i, (user_id, coins) in enumerate(top_users, 1):
        try:
            user = await c.get_users(int(user_id))
            name = escape_markdown(user.first_name)
        except:
            name = f"User {user_id}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        leaderboard += f"{medal} {name} - {format_number(coins)} coins\n"
    
    await m.reply_text(leaderboard)

@Gojo.on_message(command("mpromote"))
async def mpromote_cmd(c: Gojo, m: Message):
    """Promote user to Coin Master"""
    user_id = str(m.from_user.id)
    user_name = m.from_user.first_name
    
    # Check if already promoted
    if user_id in promotions:
        promo_data = promotions[user_id]
        return await m.reply_text(
            f"⭐ **Already a Coin Master!**\n\n"
            f"**User:** {escape_markdown(user_name)}\n"
            f"**Title:** {promo_data.get('title', 'Coin Master')}\n"
            f"**Spent:** {format_number(promo_data.get('coins_spent', 0))} coins\n\n"
            f"Use `/mtitle <new_title>` to change your title!"
        )
    
    # Check balance
    if not spend_user_balance(user_id, PROMOTION_COST):
        return await m.reply_text(
            f"❌ Not enough coins for promotion!\n\n"
            f"**Required:** {format_number(PROMOTION_COST)} coins\n"
            f"**Your Balance:** {format_number(get_user_balance(user_id))} coins\n\n"
            f"Play games and claim daily rewards to earn more coins!"
        )
    
    # Add promotion
    promotions[user_id] = {
        "title": "Coin Master",
        "coins_spent": PROMOTION_COST,
        "promoted_at": datetime.now().isoformat()
    }
    DataManager.save_json(PROMOTIONS_FILE, promotions)
    
    # Try to promote in chat
    promotion_success = True
    try:
        await c.promote_chat_member(
            chat_id=m.chat.id,
            user_id=int(user_id),
            can_delete_messages=True,
            can_pin_messages=True,
            can_manage_chat=True
        )
    except RPCError as e:
        promotion_success = False
        # Refund coins if promotion failed
        update_user_balance(user_id, PROMOTION_COST)
        del promotions[user_id]
        DataManager.save_json(PROMOTIONS_FILE, promotions)
        
        await m.reply_text(
            f"❌ **Promotion Failed!**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"Your coins have been refunded."
        )
        return
    
    if promotion_success:
        await m.reply_text(
            f"🎉 **Congratulations!**\n\n"
            f"**User:** {escape_markdown(user_name)}\n"
            f"**New Role:** Coin Master\n"
            f"**Cost:** {format_number(PROMOTION_COST)} coins\n"
            f"**New Balance:** {format_number(get_user_balance(user_id))}\n\n"
            f"You can now delete and pin messages in this chat!\n"
            f"Use `/mtitle <title>` to customize your title."
        )

@Gojo.on_message(command("mtitle"))
async def mtitle_cmd(c: Gojo, m: Message):
    """Change Coin Master title"""
    user_id = str(m.from_user.id)
    
    # Check if user is promoted
    if user_id not in promotions:
        return await m.reply_text(
            "❌ **You are not a Coin Master!**\n\n"
            f"Become a Coin Master with `/mpromote` for {format_number(PROMOTION_COST)} coins."
        )
    
    # Check command format
    if len(m.command) < 2:
        return await m.reply_text(
            "**Usage:** `/mtitle <new_title>`\n\n"
            "**Example:** `/mtitle Diamond Miner`\n\n"
            f"Title change costs {format_number(TITLE_CHANGE_COST)} coins."
        )
    
    new_title = m.text.split(maxsplit=1)[1].strip()
    
    # Validate title length
    if len(new_title) > 20:
        return await m.reply_text("❌ Title must be 20 characters or less!")
    
    # Check if user has enough coins
    if not spend_user_balance(user_id, TITLE_CHANGE_COST):
        return await m.reply_text(
            f"❌ Not enough coins for title change!\n\n"
            f"**Required:** {format_number(TITLE_CHANGE_COST)} coins\n"
            f"**Your Balance:** {format_number(get_user_balance(user_id))} coins"
        )
    
    # Update title
    promotions[user_id]["title"] = new_title
    DataManager.save_json(PROMOTIONS_FILE, promotions)
    
    await m.reply_text(
        f"✅ **Title Updated!**\n\n"
        f"**New Title:** {new_title}\n"
        f"**Cost:** {format_number(TITLE_CHANGE_COST)} coins\n"
        f"**New Balance:** {format_number(get_user_balance(user_id))}"
    )

# ===== HELP COMMAND =====
@Gojo.on_message(command("monichelp"))
async def monic_help(c: Gojo, m: Message):
    """Show help for Monic commands"""
    help_text = """
🎮 **Monic Bot Help** 🎮

**💰 Economy Commands:**
• /balance - Check your coin balance
• /daily - Claim daily coins (every 24h)
• /mgive <amount> - Give coins to another user
• /top - Show top coin collectors

**🎲 Games:**
• /mines <amount> <mines> - Start a mines game
  Example: `/mines 500 5` - Bet 500 coins with 5 mines

**⭐ Coin Master Commands:**
• /mpromote - Become a Coin Master (1M coins)
• /mtitle <title> - Change your Coin Master title

**👑 Owner Commands:**
• /mgift <amount> - Gift coins to a user
• /take <amount> - Take coins from a user

**💡 Tips:**
• Play mines games to multiply your coins
• Claim daily rewards regularly
• Be careful - hitting a mine loses your bet!
• Withdraw your earnings anytime during a game
    """
    
    await m.reply_text(help_text)

# ===== PLUGIN INFO =====
__PLUGIN__ = "Mines"
_DISABLE_CMDS_ = ["mines"]
__HELP__ = """
🎮 Monic Economy & Games System

• /mines <amount> <mines> - Start a Mines game
• /balance - Check your coins
• /daily - Claim 100 coins daily
• /mgive - Give coins to someone
• /mgift - Owner can gift coins
• /take - Take coins from a user
• /top - Top collectors
• /mpromote - Become Coin Master
• /mtitle - Set Coin Master title

💡 Withdraw anytime using 💰 Withdraw button.
💣 Hitting a bomb ends the game and reveals all cells.
"""
