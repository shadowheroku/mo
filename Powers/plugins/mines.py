import random
import json
import os
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# ─── ESCAPE MARKDOWN ───
def escape_markdown(text: str, version: int = 2) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"""
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)

# ─── FILE PATHS ───
BALANCE_FILE = "monic_balance.json"

# ─── STORAGE ───
mines_games = {}  # {game_id: {user, amount, mines, board, revealed, multiplier, reward}}
user_balance = {}  # loaded from JSON

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
    if num_mines <= 3: return 2.0
    if num_mines <= 6: return 3.0
    if num_mines <= 10: return 4.0
    return 5.0

def next_game_id():
    return str(random.randint(10000, 99999))

# ─── START GAME ───
@Gojo.on_message(command("mines"))
async def mines_start(c: Gojo, m: Message):
    load_balance()
    args = m.text.split()
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        return await m.reply_text("Usage: /mines amount number_of_mines")

    amount = int(args[1])
    num_mines = int(args[2])
    user = str(m.from_user.id)

    if amount < 100:
        return await m.reply_text("❌ Minimum bet is 100 monic coins!")
    if user_balance.get(user, 1000) < amount:
        return await m.reply_text(f"❌ Not enough monic coins! Balance: {user_balance.get(user,1000)}")
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

    await m.reply_text(
        f"🎮 **Mines Game**\n\nBet: {amount} monic coins | Mines: {num_mines}\nGame ID: {game_id}\nPick a cell!",
        reply_markup=render_board(board, set(), game_id=game_id)
    )

# ─── HANDLE MOVES ───
@Gojo.on_callback_query(filters.regex(r"mines_(\d+)"))
async def mines_play(c: Gojo, q: CallbackQuery):
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
        await q.message.edit_text(
            f"💥 Boom! You hit a mine!\nYou lost {game['amount']} monic coins.\nBalance: {user_balance[user]}",
            reply_markup=render_board(game["board"], game["revealed"], show_all=True)
        )
        del mines_games[game_id]
    else:
        # reward per gem
        gem_reward = int(game["amount"] * game["multiplier"])
        game["reward"] += gem_reward
        game["multiplier"] *= 0.85  # reduce multiplier
        await q.message.edit_text(
            f"💎 You revealed a gem!\nReward for this gem: {gem_reward} coins\nTotal: {game['reward']} coins\nMultiplier now: {game['multiplier']:.2f}",
            reply_markup=render_board(game["board"], game["revealed"], game_id=game_id)
        )

        # all safe cells revealed
        safe_cells = 25 - game["mines"]
        if len(game["revealed"]) == safe_cells:
            user_balance[user] = user_balance.get(user, 1000) + game["reward"]
            save_balance()
            await q.message.edit_text(
                f"🎉 Congratulations! You cleared all safe cells!\nYou won {game['reward']} monic coins!\nBalance: {user_balance[user]}",
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

# ─── BALANCE COMMAND ───
@Gojo.on_message(command("balance"))
async def balance(c: Gojo, m: Message):
    load_balance()
    user = str(m.from_user.id)
    bal = user_balance.get(user, 1000)
    await m.reply_text(f"💰 Balance: {bal} monic coins")

# ─── TOP COMMAND ───
@Gojo.on_message(command("top"))
async def top_collectors(c: Gojo, m: Message):
    load_balance()
    if not user_balance:
        return await m.reply_text("No collectors yet!")
    top = sorted(user_balance.items(), key=lambda x: x[1], reverse=True)[:10]
    msg = "**🏆 Top Monic Collectors**\n\n"
    for i, (uid, coins) in enumerate(top, 1):
        user_obj = await c.get_users(int(uid))
        msg += f"{i}. {escape_markdown(user_obj.first_name)} - {coins} monic coins\n"
    await m.reply_text(msg)

__PLUGIN__ = "mines"
_DISABLE_CMDS_ = ["mines"]
__HELP__ = """
🎮 Mines Game
• /mines <amount> <mines> → Start a Mines game (min 100 coins)
• /balance → Check your monic coins
• /top → Top collectors of monic coins

💡 You can withdraw anytime using the 💰 Withdraw button to collect your current winnings.
💣 Hitting a bomb ends the game and reveals all cells.
"""
