import random
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command


# ─── ESCAPE MARKDOWN ───
def escape_markdown(text: str, version: int = 2) -> str:
    if version == 1:
        escape_chars = r"_*`["
    elif version == 2:
        escape_chars = r"_*[]()~`>#+-=|{}.!"
    else:
        raise ValueError("Markdown version must be 1 or 2")
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)


# ─── STORAGE ───
xo_games = {}  # {chat_id: {p1, p2, board, turn, symbols, players}}


# ─── HELPER TO GET NAME ───
async def get_name(c, uid):
    if uid == "bot":
        return "🤖 Bot"
    u = await c.get_users(uid)
    return f"{escape_markdown(u.first_name, version=2)}"


# ─── FORMAT BOARD ───
def render_board(board):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(board[r * 3 + c], callback_data=f"xo_{r*3+c}")
            for c in range(3)
        ] for r in range(3)
    ])


# ─── CHECK WINNER ───
def check_winner(board):
    wins = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    for a, b, c in wins:
        if board[a] == board[b] == board[c] and board[a] in ["❌", "⭕"]:
            return board[a]
    if all(cell in ["❌", "⭕"] for cell in board):
        return "draw"
    return None


# ─── START GAME ───
@Gojo.on_message(command("xo") & filters.group)
async def xo_start(c: Gojo, m: Message):
    if m.reply_to_message:  # play with another user
        p1 = m.from_user.id
        p2 = m.reply_to_message.from_user.id
        if p1 == p2:
            return await m.reply_text("⚠️ You cannot challenge yourself!")
        players = {p1: "❌", p2: "⭕"}
        txt = f"🎮 **Tic-Tac-Toe**\n\n{await get_name(c, p1)} challenged {await get_name(c, p2)}!"
    else:  # play with bot
        p1 = m.from_user.id
        p2 = "bot"
        players = {p1: "❌", p2: "⭕"}
        txt = f"🎮 **Tic-Tac-Toe**\n\n{await get_name(c, p1)} vs 🤖 Bot"

    xo_games[m.chat.id] = {
        "p1": p1,
        "p2": p2,
        "board": ["⬜"] * 9,
        "turn": p1,
        "players": players
    }

    await m.reply_text(
        f"{txt}\n\n❌ goes first!",
        reply_markup=render_board(["⬜"] * 9)
    )


# ─── HANDLE MOVES ───
@Gojo.on_callback_query(filters.regex(r"xo_(\d)"))
async def xo_play(c: Gojo, q: CallbackQuery):
    chat_id = q.message.chat.id
    if chat_id not in xo_games:
        return await q.answer("⚠️ No active XO game here!", show_alert=True)

    game = xo_games[chat_id]
    pos = int(q.data.split("_")[1])
    uid = q.from_user.id

    if game["board"][pos] in ["❌", "⭕"]:
        return await q.answer("That cell is already taken!", show_alert=True)

    if uid != game["turn"] and not (uid != game["p1"] and game["p2"] == "bot" and game["turn"] == game["p1"]):
        return await q.answer("Not your turn!", show_alert=True)

    # mark move
    symbol = game["players"][game["turn"]]
    game["board"][pos] = symbol

    # check winner
    result = check_winner(game["board"])
    if result:
        if result == "draw":
            txt = "🤝 It's a Draw!"
        else:
            winner = [pid for pid, sym in game["players"].items() if sym == result][0]
            txt = f"🎉 Winner: {await get_name(c, winner)}"
        await q.message.edit_text(
            f"🎮 **Tic-Tac-Toe**\n\n{txt}",
            reply_markup=render_board(game["board"])
        )
        del xo_games[chat_id]
        return

    # switch turn
    game["turn"] = game["p2"] if game["turn"] == game["p1"] else game["p1"]

    # bot move
    if game["p2"] == "bot" and game["turn"] == "bot":
        free = [i for i, cell in enumerate(game["board"]) if cell == "⬜"]
        bot_pos = random.choice(free)
        game["board"][bot_pos] = game["players"]["bot"]

        result = check_winner(game["board"])
        if result:
            if result == "draw":
                txt = "🤝 It's a Draw!"
            else:
                winner = [pid for pid, sym in game["players"].items() if sym == result][0]
                txt = f"🎉 Winner: {await get_name(c, winner)}"
            await q.message.edit_text(
                f"🎮 **Tic-Tac-Toe**\n\n{txt}",
                reply_markup=render_board(game["board"])
            )
            del xo_games[chat_id]
            return

        game["turn"] = game["p1"]

    await q.message.edit_text(
        f"🎮 **Tic-Tac-Toe**\n\nTurn: {game['players'][game['turn']]} {await get_name(c, game['turn'])}",
        reply_markup=render_board(game["board"])
    )


__PLUGIN__ = "xo"
_DISABLE_CMDS_ = ["xo"]

__HELP__ = """
🎮 Tic-Tac-Toe
• /xo → Play with Bot  
• Reply /xo → Challenge another player  
"""
