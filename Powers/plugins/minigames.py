import random
from datetime import datetime
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ParseMode as PM

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.cmd_senders import send_cmd


# ─── STORAGE ───
rps_emojis = {"rock": "🪨", "paper": "📜", "scissors": "✂️"}
trivia_questions = [
    {"q": "What’s the capital of Japan?", "a": ["Tokyo", "Beijing", "Seoul", "Bangkok"], "c": 0},
    {"q": "Who founded Microsoft?", "a": ["Steve Jobs", "Bill Gates", "Mark Zuckerberg", "Elon Musk"], "c": 1},
    {"q": "Which is the largest planet?", "a": ["Earth", "Jupiter", "Mars", "Saturn"], "c": 1},
]
guess_words = ["python", "telegram", "gojo", "database", "network", "engineer"]

xo_games = {}  # {chat_id: {board: [...], turn: user_id, players: [id1, id2]}}


# ─── ROCK PAPER SCISSORS ───
@Gojo.on_message(command("rps") & filters.group)
async def rock_paper_scissors(c: Gojo, m: Message):
    btns = [
        [InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
         InlineKeyboardButton("📜 Paper", callback_data="rps_paper"),
         InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors")]
    ]
    await m.reply_text(
        "**🎮 Rock-Paper-Scissors**\n\nChoose your move:",
        reply_markup=InlineKeyboardMarkup(btns)
    )


@Gojo.on_callback_query(filters.regex(r"rps_(rock|paper|scissors)"))
async def rps_choice(c: Gojo, q: CallbackQuery):
    user_choice = q.data.split("_")[1]
    bot_choice = random.choice(list(rps_emojis.keys()))

    if user_choice == bot_choice:
        result = "🤝 It's a Tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "scissors" and bot_choice == "paper") or \
         (user_choice == "paper" and bot_choice == "rock"):
        result = "🎉 You Win!"
    else:
        result = "😢 You Lose!"

    await q.message.edit_text(
        f"**Rock-Paper-Scissors**\n\n"
        f"👤 You: {rps_emojis[user_choice]}\n"
        f"🤖 Bot: {rps_emojis[bot_choice]}\n\n"
        f"**Result:** {result}"
    )
    await q.answer()


# ─── TRIVIA ───
@Gojo.on_message(command("trivia") & filters.group)
async def trivia(c: Gojo, m: Message):
    q = random.choice(trivia_questions)
    btns = [
        [InlineKeyboardButton(f"{idx+1}. {ans}", callback_data=f"trivia_{q['a'].index(ans)}_{q['c']}")]
        for idx, ans in enumerate(q["a"])
    ]
    await m.reply_text(
        f"**❓ Trivia Time**\n\n{q['q']}",
        reply_markup=InlineKeyboardMarkup(btns)
    )


@Gojo.on_callback_query(filters.regex(r"trivia_(\d+)_(\d+)"))
async def trivia_answer(c: Gojo, q: CallbackQuery):
    choice, correct = map(int, q.data.split("_")[1:])
    if choice == correct:
        txt = "✅ Correct! Smart brain 🧠"
    else:
        txt = "❌ Wrong! Better luck next time 😅"

    await q.message.edit_text(f"{q.message.text}\n\n{txt}")
    await q.answer()


# ─── GUESS THE WORD ───
@Gojo.on_message(command("guess") & filters.group)
async def guess_word(c: Gojo, m: Message):
    word = random.choice(guess_words)
    masked = "".join(["_" for _ in word])
    c.guess_game = {"word": word, "progress": masked, "tries": 6, "used": []}

    await m.reply_text(
        f"**🔤 Guess the Word**\n\nWord: `{masked}`\nTries left: 6\n\nReply with a letter!"
    )


@Gojo.on_message(filters.reply & filters.group)
async def guess_letter(c: Gojo, m: Message):
    if not hasattr(c, "guess_game"):
        return
    game = c.guess_game
    letter = m.text.lower()

    if not letter.isalpha() or len(letter) != 1:
        return

    if letter in game["used"]:
        await m.reply_text("⚠️ Letter already used.")
        return

    game["used"].append(letter)
    if letter in game["word"]:
        new_progress = "".join([letter if game["word"][i] == letter else game["progress"][i] for i in range(len(game["word"]))])
        game["progress"] = new_progress
        if "_" not in new_progress:
            await m.reply_text(f"🎉 You guessed the word: `{game['word']}`")
            delattr(c, "guess_game")
        else:
            await m.reply_text(f"✅ Correct!\n\nWord: `{new_progress}`\nTries left: {game['tries']}")
    else:
        game["tries"] -= 1
        if game["tries"] <= 0:
            await m.reply_text(f"💀 Game Over! Word was: `{game['word']}`")
            delattr(c, "guess_game")
        else:
            await m.reply_text(f"❌ Wrong!\n\nWord: `{game['progress']}`\nTries left: {game['tries']}")


# ─── XO (Tic Tac Toe) ───
@Gojo.on_message(command("xo") & filters.group)
async def start_xo(c: Gojo, m: Message):
    if m.reply_to_message:
        p1, p2 = m.from_user.id, m.reply_to_message.from_user.id
        xo_games[m.chat.id] = {"board": [" "]*9, "turn": p1, "players": [p1, p2]}
        await send_xo(m.chat.id, m)
    else:
        await m.reply_text("Reply to someone to start XO!")


async def send_xo(chat_id, m: Message):
    game = xo_games[chat_id]
    symbols = {game["players"][0]: "❌", game["players"][1]: "⭕"}
    board = game["board"]
    btns = []
    for i in range(0, 9, 3):
        btns.append([
            InlineKeyboardButton(board[i] if board[i] != " " else "⬜", callback_data=f"xo_{i}")
            for i in range(i, i+3)
        ])
    turn_user = game["turn"]
    await m.reply_text(
        f"🎮 **Tic Tac Toe**\nTurn: {m.chat.get_member(turn_user).user.mention}\nSymbol: {symbols[turn_user]}",
        reply_markup=InlineKeyboardMarkup(btns)
    )


@Gojo.on_callback_query(filters.regex(r"xo_(\d)"))
async def xo_move(c: Gojo, q: CallbackQuery):
    chat_id = q.message.chat.id
    if chat_id not in xo_games:
        return await q.answer("Game ended!", show_alert=True)

    game = xo_games[chat_id]
    idx = int(q.data.split("_")[1])
    if game["board"][idx] != " ":
        return await q.answer("Invalid move!", show_alert=True)

    user = q.from_user.id
    if user != game["turn"]:
        return await q.answer("Not your turn!", show_alert=True)

    symbol = "❌" if user == game["players"][0] else "⭕"
    game["board"][idx] = symbol
    game["turn"] = game["players"][0] if user == game["players"][1] else game["players"][1]

    winner = check_winner(game["board"])
    if winner:
        await q.message.edit_text(f"🎉 {q.from_user.mention} wins with {symbol}!")
        del xo_games[chat_id]
    elif " " not in game["board"]:
        await q.message.edit_text("🤝 It's a draw!")
        del xo_games[chat_id]
    else:
        await send_xo(chat_id, q.message)
    await q.answer()


def check_winner(board):
    wins = [(0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return True
    return False


__PLUGIN__ = "minigames"
_DISABLE_CMDS_ = ["rps", "trivia", "guess", "xo"]

__HELP__ = """
**🎮 Mini Games**
• /rps → Play Rock-Paper-Scissors
• /trivia → Answer Trivia Questions
• /guess → Guess the Word
• /xo [reply to user] → Start Tic Tac Toe
"""
