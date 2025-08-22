import random
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ParseMode as PM
from pyrogram.helpers import escape_markdown

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command


# ─── STORAGE ───
xo_games = {}  # {chat_id: {"board": list, "p1": id, "p2": id/"bot", "turn": id, "symbols": {id: "❌/⭕"}}}


# ─── HELPER TO GET NAME ───
async def get_name(c, uid):
    if uid == "bot":
        return "🤖 Bot"
    u = await c.get_users(uid)
    return f"**{escape_markdown(u.first_name, version=2)}**"


# ─── START GAME ───
@Gojo.on_message(command("xo") & filters.group)
async def xo_start(c: Gojo, m: Message):
    if m.reply_to_message:  # challenge user
        p1 = m.from_user.id
        p2 = m.reply_to_message.from_user.id
        if p1 == p2:
            return await m.reply_text("⚠️ You cannot play against yourself!")

        xo_games[m.chat.id] = {
            "board": [" "]*9,
            "p1": p1,
            "p2": p2,
            "turn": p1,
            "symbols": {p1: "❌", p2: "⭕"}
        }
        txt = f"🎮 **Tic-Tac-Toe**\n\n{await get_name(c, p1)} vs {await get_name(c, p2)}"
    else:  # play vs bot
        p1 = m.from_user.id
        p2 = "bot"
        xo_games[m.chat.id] = {
            "board": [" "]*9,
            "p1": p1,
            "p2": p2,
            "turn": p1,
            "symbols": {p1: "❌", p2: "⭕"}
        }
        txt = f"🎮 **Tic-Tac-Toe**\n\n{await get_name(c, p1)} vs 🤖 Bot"

    await send_board(c, m.chat.id, m, txt)


# ─── BUILD BOARD UI ───
def make_board(board):
    btns = []
    for i in range(0, 9, 3):
        row = [
            InlineKeyboardButton(board[j] if board[j] != " " else "⬜", callback_data=f"xo_{j}")
            for j in range(i, i+3)
        ]
        btns.append(row)
    return InlineKeyboardMarkup(btns)


async def send_board(c, chat_id, m: Message, header: str):
    game = xo_games[chat_id]
    turn_user = game["turn"]
    turn_name = await get_name(c, turn_user)
    text = f"{header}\n\nTurn: {turn_name} ({game['symbols'][turn_user]})"
    await m.reply_text(text, reply_markup=make_board(game["board"]), parse_mode=PM.MARKDOWN)


# ─── CALLBACK MOVES ───
@Gojo.on_callback_query(filters.regex(r"xo_(\d)"))
async def xo_move(c: Gojo, q: CallbackQuery):
    chat_id = q.message.chat.id
    if chat_id not in xo_games:
        return await q.answer("⚠️ No active XO game!", show_alert=True)

    game = xo_games[chat_id]
    idx = int(q.data.split("_")[1])
    user = q.from_user.id

    # not a player
    if user not in [game["p1"], game["p2"]] and game["p2"] != "bot":
        return await q.answer("This game isn’t for you!", show_alert=True)

    # not your turn
    if user != game["turn"] and game["turn"] != "bot":
        return await q.answer("Wait for your turn!", show_alert=True)

    # invalid move
    if game["board"][idx] != " ":
        return await q.answer("Cell already taken!", show_alert=True)

    # place move
    game["board"][idx] = game["symbols"][user]
    await q.answer(f"You placed {game['symbols'][user]}")

    # check winner
    winner = check_winner(game["board"])
    if winner:
        winner_name = await get_name(c, user)
        await q.message.edit_text(
            f"🎉 {winner_name} wins with {game['symbols'][user]}!\n\nGame Over.",
            reply_markup=make_board(game["board"]),
            parse_mode=PM.MARKDOWN
        )
        del xo_games[chat_id]
        return
    elif " " not in game["board"]:
        await q.message.edit_text(
            "🤝 It's a draw!\n\nGame Over.",
            reply_markup=make_board(game["board"]),
            parse_mode=PM.MARKDOWN
        )
        del xo_games[chat_id]
        return

    # switch turn
    if game["p2"] == "bot":
        # bot move
        game["turn"] = "bot"
        bot_move = bot_ai(game["board"])
        game["board"][bot_move] = game["symbols"]["bot"]

        # check bot win
        if check_winner(game["board"]):
            await q.message.edit_text(
                f"🤖 Bot wins with {game['symbols']['bot']}!\n\nGame Over.",
                reply_markup=make_board(game["board"]),
                parse_mode=PM.MARKDOWN
            )
            del xo_games[chat_id]
            return
        elif " " not in game["board"]:
            await q.message.edit_text(
                "🤝 It's a draw!\n\nGame Over.",
                reply_markup=make_board(game["board"]),
                parse_mode=PM.MARKDOWN
            )
            del xo_games[chat_id]
            return

        # back to player
        game["turn"] = game["p1"]
    else:
        game["turn"] = game["p1"] if user == game["p2"] else game["p2"]

    # update board
    header = f"🎮 **Tic-Tac-Toe**\n\n{await get_name(c, game['p1'])} vs {await get_name(c, game['p2'])}"
    await q.message.edit_text(
        f"{header}\n\nTurn: {await get_name(c, game['turn'])} ({game['symbols'][game['turn']]})",
        reply_markup=make_board(game["board"]),
        parse_mode=PM.MARKDOWN
    )


# ─── GAME LOGIC ───
def check_winner(board):
    wins = [(0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return True
    return False


def bot_ai(board):
    """Simple bot AI: try winning, blocking, else random"""
    # winning move
    for i in range(9):
        if board[i] == " ":
            board[i] = "⭕"
            if check_winner(board):
                board[i] = " "
                return i
            board[i] = " "
    # block move
    for i in range(9):
        if board[i] == " ":
            board[i] = "❌"
            if check_winner(board):
                board[i] = " "
                return i
            board[i] = " "
    # random
    return random.choice([i for i in range(9) if board[i] == " "])


__PLUGIN__ = "xo"
_DISABLE_CMDS_ = ["xo"]

__HELP__ = """
**🎮 Tic-Tac-Toe**
• `/xo` → Play with Bot  
• Reply `/xo` → Challenge another user  
"""
