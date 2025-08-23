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


# ─── STORAGE ───
xo_games = {}  # {chat_id: {"board": list, "p1": id, "p2": id/"bot", "turn": id, "msg_id": int}}


# ─── HELPERS ───
def render_board(board):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(board[i], callback_data=f"xo_{i}")
            for i in range(j, j + 3)
        ] for j in range(0, 9, 3)
    ])


def check_winner(board):
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6)
    ]
    for a, b, c in wins:
        if board[a] == board[b] == board[c] and board[a] != "⬜":
            return True
    return False


def is_full(board):
    return all(cell != "⬜" for cell in board)


# ─── START GAME ───
@Gojo.on_message(command("xo"))
async def xo_start(_, m: Message):
    if m.chat.id in xo_games:
        return await m.reply_text("❌ A game is already running here!")

    if not m.reply_to_message:
        return await m.reply_text("⚡ Reply to someone with /xo to challenge them!")

    p1 = m.from_user.id
    p2 = m.reply_to_message.from_user.id

    board = ["⬜"] * 9
    turn = random.choice([p1, p2])

    msg = await m.reply_text(
        f"🎮 **XO Game Started!**\n\n"
        f"❇️ {m.from_user.mention} vs {m.reply_to_message.from_user.mention}\n"
        f"👉 Turn: {m.from_user.mention if turn == p1 else m.reply_to_message.from_user.mention}",
        reply_markup=render_board(board)
    )

    xo_games[m.chat.id] = {
        "board": board,
        "p1": p1,
        "p2": p2,
        "turn": turn,
        "msg_id": msg.id
    }


# ─── HANDLE MOVES ───
@Gojo.on_callback_query(filters.regex("^xo_"))
async def xo_move(_, cq: CallbackQuery):
    chat_id = cq.message.chat.id
    game = xo_games.get(chat_id)

    if not game or cq.message.id != game["msg_id"]:
        return await cq.answer("This game is not active!", show_alert=True)

    user = cq.from_user.id
    if user != game["turn"]:
        return await cq.answer("Not your turn!", show_alert=True)

    pos = int(cq.data.split("_")[1])
    if game["board"][pos] != "⬜":
        return await cq.answer("Cell already taken!", show_alert=True)

    mark = "❌" if user == game["p1"] else "⭕"
    game["board"][pos] = mark

    if check_winner(game["board"]):
        await cq.message.edit_text(
            f"🏆 {cq.from_user.mention} wins!\n\nGame Over.",
            reply_markup=render_board(game["board"])
        )
        del xo_games[chat_id]
        return

    if is_full(game["board"]):
        await cq.message.edit_text(
            "🤝 It's a draw!\n\nGame Over.",
            reply_markup=render_board(game["board"])
        )
        del xo_games[chat_id]
        return

    # Switch turn
    game["turn"] = game["p1"] if user == game["p2"] else game["p2"]

    await cq.message.edit_text(
        f"🎮 XO Game\n👉 Turn: {cq.message.chat.get_member(game['turn']).user.mention}",
        reply_markup=render_board(game["board"])
    )
