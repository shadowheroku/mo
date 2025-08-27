import random
import json
import os
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
import asyncio
# ─── ESCAPE MARKDOWN ───
def escape_markdown(text: str, version: int = 2) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)
# Add to your imports
import time

# Add to your storage section
give_cooldowns = {}  # {user_id: last_give_timestamp}
# ─── FILE PATHS ───
BALANCE_FILE = "monic_balance.json"
DAILY_FILE = "monic_daily.json"
SEASON_FILE = "monic_season.json"
PROMOTIONS_FILE = "monic_promotions.json"

# ─── STORAGE ───
mines_games = {}  # {game_id: {user, amount, mines, board, revealed, multiplier, reward}}
user_balance = {}  # loaded from JSON
daily_claim = {}   # daily claim timestamps
season_data = {}   # season information
user_promotions = {} # user promotion data

# ─── JSON LOAD/SAVE ───
def load_balance():
    global user_balance
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, "r") as f:
            user_balance = json.load(f)
    else:
        user_balance = {}

def save_balance():
    with open(BALANCE_FILE, "w") as f:
        json.dump(user_balance, f)

def load_daily():
    global daily_claim
    if os.path.exists(DAILY_FILE):
        with open(DAILY_FILE, "r") as f:
            daily_claim = json.load(f)
    else:
        daily_claim = {}

def save_daily():
    with open(DAILY_FILE, "w") as f:
        json.dump(daily_claim, f)

def load_season():
    global season_data
    if os.path.exists(SEASON_FILE):
        with open(SEASON_FILE, "r") as f:
            season_data = json.load(f)
    else:
        # Initialize with current month and year
        now = datetime.now()
        season_data = {
            "current_season": f"{now.year}-{now.month}",
            "last_reset": now.isoformat(),
            "next_reset": (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),
            "notified": False
        }
        save_season()

def save_season():
    with open(SEASON_FILE, "w") as f:
        json.dump(season_data, f)

def load_promotions():
    global user_promotions
    if os.path.exists(PROMOTIONS_FILE):
        with open(PROMOTIONS_FILE, "r") as f:
            user_promotions = json.load(f)
    else:
        user_promotions = {}

def save_promotions():
    with open(PROMOTIONS_FILE, "w") as f:
        json.dump(user_promotions, f)

# ─── SEASON MANAGEMENT ───
async def check_season_reset(c: Gojo):
    load_season()
    now = datetime.now()
    next_reset = datetime.fromisoformat(season_data["next_reset"])
    
    # Check if we need to reset (it's the first day of the month)
    if now >= next_reset:
        # Reset all balances to 1000
        load_balance()
        for user_id in user_balance:
            user_balance[user_id] = 1000
        save_balance()
        
        # Update season data
        season_data["current_season"] = f"{now.year}-{now.month}"
        season_data["last_reset"] = now.isoformat()
        season_data["next_reset"] = (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
        season_data["notified"] = False
        save_season()
        
        # Notify all users about the new season
        await notify_new_season(c)
        
        return True
    
    # Check if we need to send a notification (one day before reset)
    elif not season_data["notified"] and now >= next_reset - timedelta(days=1):
        season_data["notified"] = True
        save_season()
        await notify_season_warning(c, next_reset)
        
    return False

async def notify_new_season(c: Gojo):
    # Notify all users with a balance about the new season
    load_balance()
    for user_id in user_balance:
        try:
            await c.send_message(
                int(user_id),
                "🎉 **New Season Started!**\n\nAll player balances have been reset to 1000 monic coins. "
                "Start collecting again to climb the leaderboard! 🏆"
            )
        except:
            pass  # User might have blocked the bot or never started a chat
    
    # Also send to groups where the bot is active (you might want to customize this)
    # This is a placeholder - you might want to store group IDs somewhere
    group_ids = []  # Add your group IDs here if needed

async def notify_season_warning(c: Gojo, reset_time):
    # Notify all users with a balance about the upcoming reset
    load_balance()
    for user_id in user_balance:
        try:
            await c.send_message(
                int(user_id),
                "⚠️ **Season Ending Tomorrow!**\n\nAll player balances will be reset to 1000 monic coins. "
                "Spend your coins or enjoy them while they last! The new season starts tomorrow."
            )
        except:
            pass  # User might have blocked the bot or never started a chat

# ─── HELPERS ───
def generate_board(size, num_mines):
    board = ["💣"] * num_mines + ["💎"] * (size*size - num_mines)
    random.shuffle(board)
    return board

def render_board(board, revealed, show_all=False, game_id=None):
    size = 5
    buttons = []
    for r in range(size):
        row = []
        for c in range(size):
            idx = r*size + c
            if show_all or idx in revealed:
                row.append(InlineKeyboardButton(board[idx], callback_data="mines_ignore"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"mines_{idx}"))
        buttons.append(row)

    if game_id and not show_all:
        buttons.append([InlineKeyboardButton("💰 Withdraw", callback_data=f"mines_withdraw_{game_id}")])
    return InlineKeyboardMarkup(buttons)

def get_initial_multiplier(num_mines):
    # Extremely low multipliers - very difficult
    if num_mines <= 3: return 0.3    # Very low reward for few mines
    if num_mines <= 6: return 0.5    # Minimal reward
    if num_mines <= 10: return 0.7   # Still very low
    if num_mines <= 15: return 0.9   # Slightly better but still low
    if num_mines <= 20: return 1.1   # Barely above original bet
    return 1.3                       # Minimal profit even for high risk
    
def next_game_id():
    return str(random.randint(10000, 99999))

# ─── START GAME ───
@Gojo.on_message(command("mines"))
async def mines_start(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    args = m.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        return await m.reply_text("Usage: /mines amount number_of_mines")

    amount = int(args[1])
    num_mines = int(args[2])
    user = str(m.from_user.id)

    if amount < 100:
        return await m.reply_text("❌ Minimum bet is 100 monic coins!")
    
    # Format balance for display
    user_bal = user_balance.get(user, 1000)
    formatted_balance = f"{user_bal:,}"
    if user_bal < amount:
        return await m.reply_text(f"❌ Not enough monic coins! Balance: ₼{formatted_balance}")
    
    if num_mines < 3 or num_mines > 24:
        return await m.reply_text("❌ Mines must be between 3 and 24")

    board = generate_board(5, num_mines)
    game_id = next_game_id()
    mines_games[game_id] = {
        "user": user,
        "amount": amount,
        "mines": num_mines,
        "board": board,
        "revealed": set(),
        "multiplier": get_initial_multiplier(num_mines),
        "reward": 0
    }

    # Format amount for display
    formatted_amount = f"{amount:,}"
    
    await m.reply_text(
        f"🎮 **Mines Game**\n\nBet: ₼{formatted_amount} | Mines: {num_mines}\nGame ID: {game_id}\nPick a cell!",
        reply_markup=render_board(board, set(), game_id=game_id)
    )

# ─── HANDLE MOVES ───
@Gojo.on_callback_query(filters.regex(r"mines_(\d+)"))
async def mines_play(c: Gojo, q: CallbackQuery):
    await check_season_reset(c)
    idx = int(q.data.split("_")[1])
    game_id = None
    for gid, g in mines_games.items():
        if q.from_user.id == int(g["user"]):
            game_id = gid
            break
    if not game_id:
        return await q.answer("⚠️ You have no active Mines game!", show_alert=True)

    game = mines_games[game_id]
    user = str(q.from_user.id)
    if idx in game["revealed"]:
        return await q.answer("Already revealed!", show_alert=True)

    game["revealed"].add(idx)
    cell = game["board"][idx]
    load_balance()

    if cell == "💣":
        user_balance[user] = user_balance.get(user, 1000) - game["amount"]
        save_balance()
        
        # Format amounts for display
        formatted_amount = f"{game['amount']:,}"
        new_balance = user_balance[user]
        formatted_balance = f"{new_balance:,}"
        
        await q.message.edit_text(
            f"💥 Boom! You hit a mine!\nYou lost ₼{formatted_amount}.\nBalance: ₼{formatted_balance}",
            reply_markup=render_board(game["board"], game["revealed"], show_all=True)
        )
        del mines_games[game_id]
    else:
        # Profit per gem (not including original bet)
        gem_profit = int(game["amount"] * game["multiplier"])
        game["reward"] += gem_profit
        game["multiplier"] *= 0.7  # even lower multiplier
        
        # Format amounts for display
        formatted_gem_profit = f"{gem_profit:,}"
        formatted_reward = f"{game['reward']:,}"
        
        await q.message.edit_text(
            f"💎 You revealed a gem!\nProfit from this gem: ₼{formatted_gem_profit}\nTotal profit: ₼{formatted_reward}\nMultiplier now: {game['multiplier']:.2f}",
            reply_markup=render_board(game["board"], game["revealed"], game_id=game_id)
        )

        # all safe cells revealed
        safe_cells = 25 - game["mines"]
        if len(game["revealed"]) == safe_cells:
            # Return original bet + profit
            user_balance[user] = user_balance.get(user, 1000) + game["amount"] + game["reward"]
            save_balance()
            
            # Format amounts for display
            formatted_reward = f"{game['reward']:,}"
            formatted_total = f"{game['amount'] + game['reward']:,}"
            new_balance = user_balance[user]
            formatted_balance = f"{new_balance:,}"
            
            await q.message.edit_text(
                f"🎉 Congratulations! You cleared all safe cells!\n"
                f"You won ₼{formatted_reward} profit!\n"
                f"Total returned: ₼{formatted_total}\n"
                f"Balance: ₼{formatted_balance}",
                reply_markup=render_board(game["board"], game["revealed"], show_all=True)
            )
            del mines_games[game_id]

# ─── WITHDRAW BUTTON ───
@Gojo.on_callback_query(filters.regex(r"mines_withdraw_(\d+)"))
async def mines_withdraw(c: Gojo, q: CallbackQuery):
    await check_season_reset(c)
    game_id = q.data.split("_")[-1]
    if game_id not in mines_games:
        return await q.answer("⚠️ Game not found!", show_alert=True)
    
    game = mines_games[game_id]
    user = str(q.from_user.id)
    if user != game["user"]:
        return await q.answer("⚠️ This is not your game!", show_alert=True)

    # Count how many gems have been revealed
    gems_revealed = 0
    for idx in game["revealed"]:
        if game["board"][idx] == "💎":
            gems_revealed += 1

    # Require at least 3 gems to withdraw
    if gems_revealed < 3:
        return await q.answer("⚠️ You need to reveal at least 3 gems before withdrawing!", show_alert=True)

    user_balance[user] = user_balance.get(user, 1000) + game["reward"]
    save_balance()
    
    # Format amounts for display
    formatted_reward = f"{game['reward']:,}"
    new_balance = user_balance[user]
    formatted_balance = f"{new_balance:,}"
    
    await q.message.edit_text(
        f"💰 You withdrew ₼{formatted_reward}!\nGems revealed: {gems_revealed}\nBalance: ₼{formatted_balance}",
        reply_markup=render_board(game["board"], game["revealed"], show_all=True)
    )
    del mines_games[game_id]

# ─── BALANCE COMMAND ───
@Gojo.on_message(command(["balance", "bal"]))
async def balance(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_vault()
    
    user = str(m.from_user.id)
    bal = user_balance.get(user, 1000)
    vault = user_vault.get(user, 0)
    total = bal + vault
    
    # Format numbers with comma separators for international system
    formatted_bal = f"{bal:,}"
    formatted_vault = f"{vault:,}"
    formatted_total = f"{total:,}"
    
    # Simple approach with spacing to make copying easier
    await m.reply_text(
        f"Current coins: ₼{formatted_bal}\n"
        f"Vault amount: ₼{formatted_vault}/100,000\n"
    )
# ─── DAILY COMMAND ───
@Gojo.on_message(command("daily"))
async def daily(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_daily()
    user = str(m.from_user.id)
    now = datetime.now()
    last = datetime.fromisoformat(daily_claim.get(user, "1970-01-01T00:00:00"))
    if now - last < timedelta(hours=24):
        remain = timedelta(hours=24) - (now - last)
        return await m.reply_text(f"⏳ Already claimed! Come back in {remain}")
    
    daily_amount = 1000
    user_balance[user] = user_balance.get(user, 1000) + daily_amount
    daily_claim[user] = now.isoformat()
    save_balance()
    save_daily()
    
    # Format the amount with comma separators
    formatted_amount = f"{daily_amount:,}"
    await m.reply_text(f"🎁 You claimed ₼{formatted_amount} !")

# ─── GIVE COMMAND ───
# Add to your imports
@Gojo.on_message(command("mgive"))
async def mgive(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    args = m.text.split()
    sender = str(m.from_user.id)
    
    # Check if user is replying to someone
    if not m.reply_to_message:
        return await m.reply_text("❌ You must reply to a user's message to give coins!")
    
    # Check cooldown (30 minutes = 1800 seconds)
    current_time = time.time()
    if sender in give_cooldowns:
        time_since_last_give = current_time - give_cooldowns[sender]
        if time_since_last_give < 1800:  # 30 minutes
            remaining_time = 1800 - time_since_last_give 
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            return await m.reply_text(f"⏳ You can give coins again in {minutes}m {seconds}s")

    if user_balance.get(sender, 1000) <= 0:
        return await m.reply_text("❌ You have no coins to send!")

    # Only allow replying to a user
    target = m.reply_to_message.from_user
    if len(args) != 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /mgive <amount> (reply to a user)")
    amount = int(args[1])

    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")

    sender_balance = user_balance.get(sender, 1000)
    
    # Calculate maximum allowed amount (50% of balance)
    max_allowed = sender_balance // 2
    
    if amount > max_allowed:
        formatted_max = f"{max_allowed:,}"
        return await m.reply_text(f"❌ You can only give up to 50% of your coins! Maximum: ₼{formatted_max}")

    if sender_balance < amount:
        formatted_balance = f"{sender_balance:,}"
        return await m.reply_text(f"❌ Not enough coins! Your balance: ₼{formatted_balance}")

    # Transfer coins
    user_balance[sender] -= amount
    user_balance[str(target.id)] = user_balance.get(str(target.id), 1000) + amount
    save_balance()
    
    # Update cooldown
    give_cooldowns[sender] = current_time
    
    # Format amounts with comma separators (copyable format)
    formatted_amount = f"{amount:,}"
    new_balance = user_balance[sender]
    formatted_new_balance = f"{new_balance:,}"
    
    # Create copyable coin amounts using monospace formatting
    await m.reply_text(
        f"✅ Sent `₼{formatted_amount}` to {escape_markdown(target.first_name)}!\n"
        f"💰 Your new balance: `₼{formatted_new_balance}`\n\n"
        f"⏰ Next gift available in 30 minutes",
    )

# ─── OWNER GIFT COMMAND ───
OWNER_ID = 8429156335  # replace with your id # your Telegram ID

@Gojo.on_message(command("mgift"))
async def mgift(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    if m.from_user.id != OWNER_ID:
        return await m.reply_text("⚠️ Only the owner can use this command.")

    if not m.reply_to_message:
        return await m.reply_text("Reply to a user's message to gift coins.")

    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /mgift <amount> (reply to a user)")

    target = m.reply_to_message.from_user
    amount = int(args[1])

    user_balance[str(target.id)] = user_balance.get(str(target.id), 1000) + amount
    save_balance()
    
    # Format the amount with comma separators
    formatted_amount = f"{amount:,}"
    await m.reply_text(f"🎁 Gave ₼{formatted_amount} to {escape_markdown(target.first_name)}!")

# ─── TAKE COMMAND ───
@Gojo.on_message(command("take"))
async def take(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    
    # Owner check
    if m.from_user.id != OWNER_ID:
        return await m.reply_text("⚠️ Only the owner can use this command.")

    args = m.text.split()

    # Case 1: Reply to a user
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        if len(args) != 2 or not args[1].isdigit():
            return await m.reply_text("Usage: /take <amount> (reply to a user)")
        amount = int(args[1])

    # Case 2: Mention username or ID
    else:
        if len(args) != 3 or not args[2].isdigit():
            return await m.reply_text("Usage: /take @user amount")
        try:
            target = await c.get_users(args[1])
        except:
            return await m.reply_text("⚠️ Could not find that user.")
        amount = int(args[2])

    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")

    # Check if target has enough coins
    target_balance = user_balance.get(str(target.id), 1000)
    if target_balance < amount:
        formatted_balance = f"{target_balance:,}"
        return await m.reply_text(f"❌ {escape_markdown(target.first_name)} only has ₼{formatted_balance} coins!")

    # Remove coins
    user_balance[str(target.id)] = max(target_balance - amount, 0)
    save_balance()
    
    # Format the amount with comma separators
    formatted_amount = f"{amount:,}"
    await m.reply_text(f"❌ Removed ₼{formatted_amount} from {escape_markdown(target.first_name)}'s balance!")

# ─── TOP COMMAND ───
@Gojo.on_message(command("top"))
async def top_collectors(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    if not user_balance:
        return await m.reply_text("No collectors yet!")
    
    top = sorted(user_balance.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Create the message with international number formatting
    msg = "**🏆 Top Monic Collectors**\n\n"
    for i, (uid, coins) in enumerate(top, 1):
        try:
            user_obj = await c.get_users(int(uid))
            formatted_coins = f"{coins:,}"
            msg += f"{i}. {escape_markdown(user_obj.first_name)} - ₼{formatted_coins}\n"
        except:
            formatted_coins = f"{coins:,}"
            msg += f"{i}. Unknown User - ₼{formatted_coins}\n"
    
    # Try to send with an image
        # Try to send with a local image
    try:
        # Make sure the file exists in your bot directory
        await m.reply_photo(
            photo="leaderboard.jpg",
            caption=msg
        )
    except:
        await m.reply_text(msg)

# ─── PROMOTE COMMAND ───
@Gojo.on_message(command("mpromote"))
async def mpromote(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_promotions()
    
    if not m.chat.type in ["group", "supergroup"]:
        return await m.reply_text("This command can only be used in groups!")
    
    user = str(m.from_user.id)
    PROMOTION_COST = 1000000  # 10 lakh coins
    
    if user_balance.get(user, 1000) < PROMOTION_COST:
        return await m.reply_text(f"❌ You need ₼{PROMOTION_COST}  to promote yourself to Coin Master!")
    
    # Check if user is already promoted
    if user_promotions.get(user, {}).get("promoted", False):
        return await m.reply_text("❌ You are already promoted to Coin Master!")
    
    # Check if user is admin in the group
    try:
        member = await m.chat.get_member(m.from_user.id)
        if not member.privileges:
            return await m.reply_text("❌ You need to be an admin in this group to use this command!")
    except:
        return await m.reply_text("❌ You need to be an admin in this group to use this command!")
    
    # Deduct coins and promote
    user_balance[user] -= PROMOTION_COST
    save_balance()
    
    # Store promotion data
    if user not in user_promotions:
        user_promotions[user] = {}
    
    user_promotions[user]["promoted"] = True
    user_promotions[user]["title"] = "Coin Master"
    user_promotions[user]["promoted_date"] = datetime.now().isoformat()
    save_promotions()
    
    # Try to change the admin title
    try:
        await c.promote_chat_member(
            m.chat.id,
            m.from_user.id,
            privileges=member.privileges  # Keep existing privileges
        )
        
        await c.set_administrator_title(
            m.chat.id,
            m.from_user.id,
            "Coin Master"
        )
        
        await m.reply_text("🎉 Congratulations! You've been promoted to Coin Master!")
    except Exception as e:
        await m.reply_text(f"❌ Failed to set admin title: {e}")

# ─── TITLE COMMAND ───
@Gojo.on_message(command("mtitle"))
async def mtitle(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_promotions()
    
    if not m.chat.type in ["group", "supergroup"]:
        return await m.reply_text("This command can only be used in groups!")
    
    args = m.text.split(maxsplit=1)
    if len(args) < 2:
        return await m.reply_text("Usage: /mtitle <custom_title>")
    
    new_title = args[1].strip()
    if len(new_title) > 16:
        return await m.reply_text("❌ Title must be 16 characters or less!")
    
    user = str(m.from_user.id)
    TITLE_CHANGE_COST = 100000  # 1 lakh coins
    
    # Check if user is promoted
    if not user_promotions.get(user, {}).get("promoted", False):
        return await m.reply_text("❌ You need to be promoted to Coin Master first! Use /mpromote")
    
    if user_balance.get(user, 1000) < TITLE_CHANGE_COST:
        return await m.reply_text(f"❌ You need {TITLE_CHANGE_COST} coins to change your title!")
    
    # Check if user is admin in the group
    try:
        member = await m.chat.get_member(m.from_user.id)
        if not member.privileges:
            return await m.reply_text("❌ You need to be an admin in this group to use this command!")
    except:
        return await m.reply_text("❌ You need to be an admin in this group to use this command!")
    
    # Deduct coins and change title
    user_balance[user] -= TITLE_CHANGE_COST
    save_balance()
    
    # Update title in promotions data
    user_promotions[user]["title"] = new_title
    save_promotions()
    
    # Try to change the admin title
    try:
        await c.set_administrator_title(
            m.chat.id,
            m.from_user.id,
            new_title
        )
        
        await m.reply_text(f"✅ Your admin title has been changed to '{new_title}'!")
    except Exception as e:
        await m.reply_text(f"❌ Failed to change admin title: {e}")

# ─── SEASON COMMAND ───
@Gojo.on_message(command("mseason"))
async def mseason(c: Gojo, m: Message):
    load_season()
    next_reset = datetime.fromisoformat(season_data["next_reset"])
    time_until_reset = next_reset - datetime.now()
    
    days = time_until_reset.days
    hours = time_until_reset.seconds // 3600
    minutes = (time_until_reset.seconds % 3600) // 60
    
    await m.reply_text(
        f"🌿 **Current Season:** {season_data['current_season']}\n"
        f"⏰ **Season ends in:** {days} days, {hours} hours, {minutes} minutes\n"
        f"🔄 **All balances will be reset to 1000 coins when the season ends**"
    )


@Gojo.on_message(command("bet"))
async def bet_command(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    
    args = m.text.split()
    if len(args) != 3:
        return await m.reply_text("Usage: /bet [amount] [heads/tails]")
    
    user = str(m.from_user.id)
    current_balance = user_balance.get(user, 1000)
    
    # Parse amount
    try:
        amount = int(args[1])
        if amount < 10:
            return await m.reply_text("Minimum bet is 10 coins!")
        
        # Format balance for display
        formatted_balance = f"{current_balance:,}"
        if amount > current_balance:
            return await m.reply_text(f"Insufficient balance! You have: ₼{formatted_balance}")
    except ValueError:
        return await m.reply_text("Please enter a valid number for the bet amount")
    
    # Parse choice
    choice = args[2].lower()
    if choice not in ["heads", "h", "tails", "t"]:
        return await m.reply_text("Please choose either 'heads' or 'tails'")
    
    # Convert shorthand to full word
    user_choice = "heads" if choice in ["h", "heads"] else "tails"
    
    # Flip the coin
    result = random.choice(["heads", "tails"])
    
    # Format amount for display
    formatted_amount = f"{amount:,}"
    
    # Determine win/loss
    if user_choice == result:
        # Win - 2x payout
        win_amount = amount
        user_balance[user] = current_balance + win_amount
        save_balance()
        
        # Format win amount for display
        formatted_win = f"{win_amount:,}"
        await m.reply_text(
            f"The coin landed on {result}!\n"
            f"You won ₼{formatted_win}!"
        )
    else:
        # Lose
        user_balance[user] = current_balance - amount
        save_balance()
        
        await m.reply_text(
            f"The coin landed on {result}!\n"
            f"You lost ₼{formatted_amount}!"
        )

@Gojo.on_message(command(["dice", "roll"]))
async def dice_cmd(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    
    args = m.text.split()
    if len(args) != 3:
        return await m.reply_text("Usage: /dice [amount] [odd/even/o/e]")
    
    user = str(m.from_user.id)
    current_balance = user_balance.get(user, 1000)
    
    # Parse amount
    try:
        amount = int(args[1])
        if amount < 10:
            return await m.reply_text("Minimum bet is 10 coins!")
        
        # Format balance for display
        formatted_balance = f"{current_balance:,}"
        if amount > current_balance:
            return await m.reply_text(f"Insufficient balance! You have: ₼{formatted_balance}")
    except ValueError:
        return await m.reply_text("Please enter a valid number for the bet amount")
    
    # Parse choice
    choice = args[2].lower()
    if choice not in ["odd", "o", "even", "e"]:
        return await m.reply_text("Please choose either 'odd' or 'even'")
    
    # Convert shorthand to full word
    user_choice = "odd" if choice in ["o", "odd"] else "even"
    
    # Send Telegram dice animation using send_dice
    try:
        dice_message = await c.send_dice(m.chat.id, "🎲")
        dice_roll = dice_message.dice.value
    except AttributeError:
        # Fallback if dice animation doesn't work
        dice_roll = random.randint(1, 6)
        await m.reply_text(f"🎲 Dice rolled: {dice_roll}")
    
    # Wait for 5 seconds before showing the result
    await asyncio.sleep(3.8)
    
    dice_emojis = {
        1: "⚀",
        2: "⚁", 
        3: "⚂",
        4: "⚃",
        5: "⚄",
        6: "⚅"
    }
    dice_emoji = dice_emojis[dice_roll]
    result = "odd" if dice_roll % 2 == 1 else "even"
    
    # Format amount for display
    formatted_amount = f"{amount:,}"
    
    # Determine win/loss
    if user_choice == result:
        # Win - 2x payout
        win_amount = amount
        user_balance[user] = current_balance + win_amount
        save_balance()
        
        # Format win amount for display
        formatted_win = f"{win_amount:,}"
        await m.reply_text(
            f"Damn. You're lucky! \n"
            f"You win ₼{formatted_win}!"
        )
    else:
        # Lose
        user_balance[user] = current_balance - amount
        save_balance()
        
        await m.reply_text(
            f"Better luck next time! \n"
            f"You lost ₼{formatted_amount}"
        )

# Add to your existing imports
VAULT_FILE = "monic_vault.json"

# Add to your storage section
user_vault = {}  # user vault data

# Add to JSON load/save functions
def load_vault():
    global user_vault
    if os.path.exists(VAULT_FILE):
        with open(VAULT_FILE, "r") as f:
            user_vault = json.load(f)
    else:
        user_vault = {}

def save_vault():
    with open(VAULT_FILE, "w") as f:
        json.dump(user_vault, f)

# Add to initialization
load_vault()

# Add vault commands
@Gojo.on_message(command("mdeposit"))
async def mdeposit(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_vault()
    
    args = m.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /mdeposit amount")
    
    user = str(m.from_user.id)
    amount = int(args[1])
    current_balance = user_balance.get(user, 1000)
    
    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")
    
    # Format balance for display
    formatted_balance = f"{current_balance:,}"
    if current_balance < amount:
        return await m.reply_text(f"❌ Not enough coins! Your balance: ₼{formatted_balance}")
    
    # Check vault capacity (1 lakh = 100,000)
    vault_balance = user_vault.get(user, 0)
    if vault_balance + amount > 100000:
        formatted_vault = f"{vault_balance:,}"
        return await m.reply_text(f"❌ Vault capacity exceeded! Maximum is ₼100,000. Current vault: ₼{formatted_vault}")
    
    # Transfer from balance to vault
    user_balance[user] = current_balance - amount
    user_vault[user] = vault_balance + amount
    
    save_balance()
    save_vault()
    
    # Format amounts for display
    formatted_amount = f"{amount:,}"
    new_balance = user_balance[user]
    formatted_new_balance = f"{new_balance:,}"
    
    await m.reply_text(
        f"✅ Deposited ₼{formatted_amount} to your vault!\n\n"
        f"💰 Balance: ₼{formatted_new_balance}\n"
    )
    
@Gojo.on_message(command("mdraw"))
async def mdraw(c: Gojo, m: Message):
    await check_season_reset(c)
    load_balance()
    load_vault()
    
    args = m.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /mdraw amount")
    
    user = str(m.from_user.id)
    amount = int(args[1])
    vault_balance = user_vault.get(user, 0)
    
    if amount <= 0:
        return await m.reply_text("❌ Amount must be greater than 0!")
    
    # Format vault balance for display
    formatted_vault = f"{vault_balance:,}"
    if vault_balance < amount:
        return await m.reply_text(f"❌ Not enough coins in vault! Your vault: ₼{formatted_vault}")
    
    # Transfer from vault to balance
    user_vault[user] = vault_balance - amount
    user_balance[user] = user_balance.get(user, 1000) + amount
    
    save_balance()
    save_vault()
    
    # Format amounts for display
    formatted_amount = f"{amount:,}"
    new_balance = user_balance[user]
    formatted_new_balance = f"{new_balance:,}"
    
    await m.reply_text(
        f"✅ Withdrew ₼{formatted_amount} from your vault!\n\n"
        f"💰 Balance: ₼{formatted_new_balance}\n"
    )
    
# Initialize data on bot start
load_season()
load_balance()
load_daily()
load_promotions()

__PLUGIN__ = "ᴍɪɴᴇs ɢᴀᴍᴇ"
_DISABLE_CMDS_ = ["mines"]

__HELP__ = """
🎮 ᴍɪɴᴇs ɢᴀᴍᴇ
• /mines <amount> <mines> → sᴛᴀʀᴛ ᴀ ᴍɪɴᴇs ɢᴀᴍᴇ (ᴍɪɴ 100 ᴄᴏɪɴs)
• /bet <amount> <heads/tails> → ᴄᴏɪɴ ᴘʟɪᴘ ʙᴇᴛᴛɪɴɢ ɢᴀᴍᴇ
• /balance → ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴍᴏɴɪᴄ ᴄᴏɪɴs
• /daily → ᴄʟᴀɪᴍ 100 ᴄᴏɪɴs ᴅᴀɪʟʏ
• /mgive → ɢɪᴠᴇ ᴄᴏɪɴs ᴛᴏ sᴏᴍᴇᴏɴᴇ ғʀᴏᴍ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ (ʀᴇᴘʟʏ ᴛᴏ ᴛʜᴇɪʀ ᴍᴇssᴀɢᴇ)
• /mgift → ᴏᴡɴᴇʀ ᴄᴀɴ ɢɪғᴛ ᴄᴏɪɴs ᴛᴏ ᴀɴʏᴏɴᴇ
• /take → ʀᴇᴍᴏᴠᴇ ᴄᴏɪɴs ғʀᴏᴍ ᴀ ᴜsᴇʀ (ʀᴇᴘʟʏ)
• /top → ᴛᴏᴘ ᴄᴏʟʟᴇᴄᴛᴏʀs ᴏꜰ ᴍᴏɴɪᴄ ᴄᴏɪɴs
• /mpromote → ᴘʀᴏᴍᴏᴛᴇ ʏᴏᴜʀsᴇʟғ ᴛᴏ ᴄᴏɪɴ ᴍᴀsᴛᴇʀ (ᴄᴏsᴛs 10 ʟᴀᴋʜ ᴄᴏɪɴs, ɢʀᴏᴜᴘ ᴀᴅᴍɪɴ ᴏɴʟʏ)
• /mtitle <title> → ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ᴀᴅᴍɪɴ ᴛɪᴛʟᴇ (ᴄᴏsᴛs 1 ʟᴀᴋʜ ᴄᴏɪɴs, ʀᴇqᴜɪʀᴇs ᴘʀᴏᴍᴏᴛɪᴏɴ)
• /mseason → ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ sᴇᴀsᴏɴ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ

💡 ʏᴏᴜ ᴄᴀɴ ᴡɪᴛʜᴅʀᴀᴡ ᴀɴʏᴛɪᴍᴇ ᴜsɪɴɢ ᴛʜᴇ 💰 ᴡɪᴛʜᴅʀᴀᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴄᴏʟʟᴇᴄᴛ ʏᴏᴜʀ ᴄᴜʀʀᴇɴᴛ ᴡɪɴɴɪɴɢs.
💣 ʜɪᴛᴛɪɴɢ ᴀ ʙᴏᴍʙ ᴇɴᴅs ᴛʜᴇ ɢᴀᴍᴇ ᴀɴᴅ ʀᴇᴠᴇᴀʟs ᴀʟʟ ᴄᴇʟʟs.
🌿 sᴇᴀsᴏɴs ʀᴇsᴇᴛ ᴍᴏɴᴛʜʟʏ - ᴀʟʟ ʙᴀʟᴀɴᴄᴇs ᴀʀᴇ sᴇᴛ ᴛᴏ 1000 ᴀᴛ ᴛʜᴇ sᴛᴀʀᴛ ᴏꜰ ᴇᴀᴄʜ ɴᴇᴡ sᴇᴀsᴏɴ
"""

