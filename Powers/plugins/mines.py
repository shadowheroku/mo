import random
import json
import os
from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── ESCAPE MARKDOWN ───
def escape_markdown(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"""
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

# ─── FILE PATHS ───
BALANCE_FILE = "monic_balance.json"
DAILY_FILE = "monic_daily.json"
SEASON_FILE = "monic_season.json"
PROMOTIONS_FILE = "monic_promotions.json"

# ─── STORAGE ───
mines_games = {}     # {game_id: {user, amount, mines, board, revealed, multiplier, reward}}
user_balance = {}    # {user_id: balance}
daily_claim = {}     # {user_id: last_claim_iso}
season_info = {}     # {"season_start": timestamp}
promotions = {}      # {user_id: {"title": str, "coins_spent": int}}

OWNER_ID = 8429156335  # replace with your Telegram ID

# ─── JSON LOAD/SAVE ───
def load_json(file_path, default=None):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

def load_balance():
    global user_balance
    user_balance = load_json(BALANCE_FILE, {})

def save_balance():
    save_json(BALANCE_FILE, user_balance)

def load_daily():
    global daily_claim
    daily_claim = load_json(DAILY_FILE, {})

def save_daily():
    save_json(DAILY_FILE, daily_claim)

def load_season():
    global season_info
    season_info = load_json(SEASON_FILE, {"season_start": datetime.now().isoformat()})

def save_season():
    save_json(SEASON_FILE, season_info)

def load_promotions():
    global promotions
    promotions = load_json(PROMOTIONS_FILE, {})

def save_promotions():
    save_json(PROMOTIONS_FILE, promotions)

# ─── MINES GAME HELPERS ───
def generate_board(size=5, num_mines=5):
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

def get_multiplier(num_mines):
    if num_mines <= 3: return 1.0
    if num_mines <= 6: return 1.5
    if num_mines <= 10: return 2.0
    return 2.5

def next_game_id():
    return str(random.randint(10000, 99999))

# ─── MINES GAME COMMAND ───
@Gojo.on_message(command("mines"))
async def mines_start(c: Gojo, m: Message):
    load_balance()
    args = m.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        return await m.reply_text("Usage: /mines <amount> <mines>")

    amount = int(args[1])
    num_mines = int(args[2])
    user = str(m.from_user.id)

    if amount < 100:
        return await m.reply_text("❌ Minimum bet is 100 coins!")
    if user_balance.get(user, 1000) < amount:
        return await m.reply_text(f"❌ Not enough coins! Balance: {user_balance.get(user,1000)}")
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
        "multiplier": get_multiplier(num_mines),
        "reward": 0
    }

    await m.reply_text(
        f"🎮 **Mines Game**\nBet: {amount} coins | Mines: {num_mines}\nGame ID: {game_id}\nPick a cell!",
        reply_markup=render_board(board, set(), game_id=game_id)
    )

# ─── MINES PLAY CALLBACK ───
@Gojo.on_callback_query(filters.regex(r"mines_(\d+)"))
async def mines_play(c: Gojo, q: CallbackQuery):
    idx = int(q.data.split("_")[1])
    game_id = None
    for gid, g in mines_games.items():
        if g["user"] == str(q.from_user.id):
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
        await q.message.edit_text(
            f"💥 Boom! You hit a mine!\nYou lost {game['amount']} coins.\nBalance: {user_balance[user]}",
            reply_markup=render_board(game["board"], game["revealed"], show_all=True)
        )
        del mines_games[game_id]
    else:
        gem_reward = int(game["amount"] * game["multiplier"])
        game["reward"] += gem_reward
        game["multiplier"] *= 0.7
        await q.message.edit_text(
            f"💎 You revealed a gem!\nReward: {gem_reward} | Total: {game['reward']} coins\nMultiplier: {game['multiplier']:.2f}",
            reply_markup=render_board(game["board"], game["revealed"], game_id=game_id)
        )
        if len(game["revealed"]) == 25 - game["mines"]:
            user_balance[user] = user_balance.get(user, 1000) + game["reward"]
            save_balance()
            await q.message.edit_text(
                f"🎉 All safe cells cleared!\nYou won {game['reward']} coins!\nBalance: {user_balance[user]}",
                reply_markup=render_board(game["board"], game["revealed"], show_all=True)
            )
            del mines_games[game_id]

# ─── WITHDRAW BUTTON ───
@Gojo.on_callback_query(filters.regex(r"mines_withdraw_(\d+)"))
async def mines_withdraw(c: Gojo, q: CallbackQuery):
    game_id = q.data.split("_")[-1]
    if game_id not in mines_games:
        return await q.answer("⚠️ Game not found!", show_alert=True)

    game = mines_games[game_id]
    user = str(q.from_user.id)
    if user != game["user"]:
        return await q.answer("⚠️ This is not your game!", show_alert=True)

    user_balance[user] = user_balance.get(user, 1000) + game["reward"]
    save_balance()
    await q.message.edit_text(
        f"💰 You withdrew {game['reward']} coins!\nBalance: {user_balance[user]}",
        reply_markup=render_board(game["board"], game["revealed"], show_all=True)
    )
    del mines_games[game_id]

# ─── COINS & DAILY COMMANDS ───
@Gojo.on_message(command("balance"))
async def balance(c: Gojo, m: Message):
    load_balance()
    user = str(m.from_user.id)
    await m.reply_text(f"💰 Balance: {user_balance.get(user,1000)} coins")

@Gojo.on_message(command("daily"))
async def daily(c: Gojo, m: Message):
    load_balance()
    load_daily()
    user = str(m.from_user.id)
    now = datetime.now()
    last = datetime.fromisoformat(daily_claim.get(user, "1970-01-01T00:00:00"))
    if now - last < timedelta(hours=24):
        remain = timedelta(hours=24) - (now - last)
        return await m.reply_text(f"⏳ Already claimed! Come back in {remain}")
    user_balance[user] = user_balance.get(user, 1000) + 100
    daily_claim[user] = now.isoformat()
    save_balance()
    save_daily()
    await m.reply_text("🎁 You claimed 100 daily coins!")

# ─── GIVE / OWNER GIFT / TAKE ───
@Gojo.on_message(command("mgive"))
async def mgive(c: Gojo, m: Message):
    load_balance()
    sender = str(m.from_user.id)
    args = m.text.split()
    if m.reply_to_message:
        target = m.reply_to_message.from_user
        if len(args) != 2 or not args[1].isdigit():
            return await m.reply_text("Usage: /mgive <amount> (reply to user)")
        amount = int(args[1])
    else:
        if len(args) != 3 or not args[2].isdigit():
            return await m.reply_text("Usage: /mgive @user amount")
        try:
            target = await c.get_users(args[1])
        except:
            return await m.reply_text("⚠️ User not found")
        amount = int(args[2])

    if amount <= 0:
        return await m.reply_text("❌ Amount must be > 0")
    if user_balance.get(sender,1000) < amount:
        return await m.reply_text(f"❌ Not enough coins! Balance: {user_balance.get(sender,1000)}")

    user_balance[sender] -= amount
    user_balance[str(target.id)] = user_balance.get(str(target.id), 1000) + amount
    save_balance()
    await m.reply_text(f"✅ Sent {amount} coins to {escape_markdown(target.first_name)}!\n💰 Your balance: {user_balance[sender]}")

@Gojo.on_message(command("mgift"))
async def mgift(c: Gojo, m: Message):
    load_balance()
    if m.from_user.id != OWNER_ID:
        return await m.reply_text("⚠️ Only owner can use this command")
    if not m.reply_to_message:
        return await m.reply_text("Reply to user's message to gift coins")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /mgift <amount> (reply)")
    target = m.reply_to_message.from_user
    amount = int(args[1])
    user_balance[str(target.id)] = user_balance.get(str(target.id), 1000) + amount
    save_balance()
    await m.reply_text(f"🎁 Gave {amount} coins to {escape_markdown(target.first_name)}!")

@Gojo.on_message(command("take"))
async def take(c: Gojo, m: Message):
    load_balance()
    if not m.reply_to_message:
        return await m.reply_text("Reply to a user's message to take coins")
    args = m.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return await m.reply_text("Usage: /take <amount> (reply)")
    target = m.reply_to_message.from_user
    user_balance[str(target.id)] = max(user_balance.get(str(target.id),1000) - int(args[1]),0)
    save_balance()
    await m.reply_text(f"❌ Removed {args[1]} coins from {escape_markdown(target.first_name)}!")

# ─── TOP COLLECTORS ───
@Gojo.on_message(command("top"))
async def top_collectors(c: Gojo, m: Message):
    load_balance()
    if not user_balance:
        return await m.reply_text("No collectors yet!")
    top = sorted(user_balance.items(), key=lambda x:x[1], reverse=True)[:10]
    msg = "**🏆 Top Monic Collectors**\n\n"
    for i, (uid, coins) in enumerate(top, 1):
        user_obj = await c.get_users(int(uid))
        msg += f"{i}. {escape_markdown(user_obj.first_name)} - {coins} coins\n"
    await m.reply_text(msg)

# ─── PROMOTE COMMAND ───
@Gojo.on_message(command("mpromote"))
async def mpromote(c: Gojo, m: Message):
    load_balance()
    load_promotions()
    user = str(m.from_user.id)
    cost = 10_00_000

    if user_balance.get(user, 1000) < cost:
        return await m.reply_text(f"❌ Not enough coins! Need {cost}")

    # Deduct coins
    user_balance[user] -= cost
    save_balance()

    # Save promotion info
    promotions[user] = {"title": "Coin Master", "coins_spent": cost}
    save_promotions()

    # Promote user with only delete & pin permissions
    try:
        await c.promote_chat_member(
            chat_id=m.chat.id,
            user_id=int(user),
            is_anonymous=False,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=True,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=True,
            can_promote_members=False,
            can_manage_video_chats=False,
            can_manage_chat=False
        )
    except Exception as e:
        return await m.reply_text(f"⚠️ Failed to promote: {e}")

    await m.reply_text("🏆 You are now a **Coin Master**!\nYou can delete and pin messages in this group.")


# ─── SET TITLE ───
@Gojo.on_message(command("mtitle"))
async def mtitle(c: Gojo, m: Message):
    load_balance()
    load_promotions()
    user = str(m.from_user.id)
    if user not in promotions:
        return await m.reply_text("⚠️ Must be a Coin Master first (/mpromote)")
    args = m.text.split(maxsplit=1)
    if len(args) != 2:
        return await m.reply_text("Usage: /mtitle <title>")
    title_cost = 1_00_000
    if user_balance.get(user,1000) < title_cost:
        return await m.reply_text(f"❌ Not enough coins! Title cost: {title_cost}")
    user_balance[user] -= title_cost
    promotions[user]["title"] = args[1]
    save_balance()
    save_promotions()
    await m.reply_text(f"✅ Your admin title is now: {args[1]}")

# ─── PLUGIN INFO ───
__PLUGIN__ = "mines"
_DISABLE_CMDS_ = ["mines"]
__HELP__ = """
🎮 Mines Game
• /mines <amount> <mines> → Start a Mines game (min 100 coins)
• /balance → Check your coins
• /daily → Claim 100 coins daily
• /mgive → Give coins to someone (reply)
• /mgift → Owner can gift coins
• /take → Take coins from a user (reply)
• /top → Top collectors
• /mpromote → Become Coin Master
• /mtitle → Set Coin Master title

💡 Withdraw anytime using 💰 Withdraw button.
💣 Hitting a bomb ends the game and reveals all cells.
"""
