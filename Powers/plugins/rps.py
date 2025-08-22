import random
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

# ─── STORAGE ───
rps_emojis = {"rock": "🪨", "paper": "📜", "scissors": "✂️"}
rps_games = {}  # {chat_id: {"p1": id, "p2": id/bot, "moves": {id: choice}}}


# ─── START GAME ───
@Gojo.on_message(command("rps") & filters.group)
async def rps_start(c: Gojo, m: Message):
    if m.reply_to_message:  # play with another user
        p1 = m.from_user.id
        p2 = m.reply_to_message.from_user.id
        if p1 == p2:
            return await m.reply_text("⚠️ You cannot challenge yourself!")
        rps_games[m.chat.id] = {"p1": p1, "p2": p2, "moves": {}}
        txt = f"🎮 **Rock–Paper–Scissors**\n\n{m.from_user.mention} challenged {m.reply_to_message.from_user.mention}!\n\nChoose your moves 👇"
    else:  # play with bot
        p1 = m.from_user.id
        rps_games[m.chat.id] = {"p1": p1, "p2": "bot", "moves": {}}
        txt = f"🎮 **Rock–Paper–Scissors**\n\n{m.from_user.mention} vs 🤖 Bot\n\nChoose your move 👇"

    btns = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data="rps_rock"),
            InlineKeyboardButton("📜 Paper", callback_data="rps_paper"),
            InlineKeyboardButton("✂️ Scissors", callback_data="rps_scissors"),
        ]
    ]
    await m.reply_text(txt, reply_markup=InlineKeyboardMarkup(btns))


# ─── HANDLE MOVES ───
@Gojo.on_callback_query(filters.regex(r"rps_(rock|paper|scissors)"))
async def rps_play(c: Gojo, q: CallbackQuery):
    chat_id = q.message.chat.id
    if chat_id not in rps_games:
        return await q.answer("⚠️ No active RPS game here!", show_alert=True)

    game = rps_games[chat_id]
    move = q.data.split("_")[1]

    # check valid player
    if q.from_user.id not in [game["p1"], game["p2"]]:
        return await q.answer("This game isn’t for you!", show_alert=True)

    # record move
    if q.from_user.id in game["moves"]:
        return await q.answer("You already played!", show_alert=True)

    game["moves"][q.from_user.id] = move
    await q.answer(f"You chose {rps_emojis[move]}")

    # bot auto move
    if game["p2"] == "bot":
        bot_move = random.choice(list(rps_emojis.keys()))
        game["moves"]["bot"] = bot_move

    # check if both played
    if len(game["moves"]) == 2:
        p1, p2 = game["p1"], game["p2"]
        m1, m2 = game["moves"][p1], game["moves"][p2]

        # decide winner
        def winner(u1, c1, u2, c2):
            if c1 == c2:
                return None
            elif (c1 == "rock" and c2 == "scissors") or \
                 (c1 == "scissors" and c2 == "paper") or \
                 (c1 == "paper" and c2 == "rock"):
                return u1
            else:
                return u2

        win = winner(p1, m1, p2, m2)

        if p2 == "bot":
            p2_name = "🤖 Bot"
        else:
            p2_name = (await c.get_users(p2)).mention

        result = (
            f"🎮 **Rock–Paper–Scissors**\n\n"
            f"{(await c.get_users(p1)).mention}: {rps_emojis[m1]}\n"
            f"{p2_name}: {rps_emojis[m2]}\n\n"
        )
        if not win:
            result += "🤝 It's a Tie!"
        elif win == p1:
            result += f"🎉 Winner: {(await c.get_users(p1)).mention}"
        else:
            result += f"🎉 Winner: {p2_name}"

        await q.message.edit_text(result, parse_mode=PM.MARKDOWN)
        del rps_games[chat_id]


__PLUGIN__ = "rps"
_DISABLE_CMDS_ = ["rps"]

__HELP__ = """
**🎮 Rock–Paper–Scissors**
• `/rps` → Play with Bot
• Reply `/rps` → Challenge another player
"""
