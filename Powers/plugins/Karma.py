# Karma Module for Gojo client (Pyrogram)
# ========================
# Features:
# • Upvote using "+", "+1", "thanks", etc. (in a reply)
# • Downvote using "-", "-1" (in a reply)
# • /karmastat [ON|OFF] – toggle per-chat (admin only)
# • /karma – reply: show that user's karma; no reply: show top 10
# • Aliases: /kstat, /k
# • Cooldown: prevents spam karma farming
# • Safe DB operations with context managers

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Tuple

from pyrogram import filters, enums
from pyrogram.types import Message
from Powers.bot_class import Gojo

# ========================
# CONFIG & DB
# ========================
DB_DIR = Path(os.getenv("GOJO_DB_DIR", "data"))
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "karma.db"

COOLDOWN_SECONDS = 30  # prevent karma spam by same user

UPVOTE_PATTERNS = [
    r"^\s*\+\s*$",
    r"^\s*\+1\s*$",
    r"thanks", r"thank\s*you", r"thx", r"tysm", r"good\s+job", r"well\s+done",
    r"kudos", r"nice", r"great", r"awesome", r"gg", r"legend",
    r"👍", r"❤️", r"love\s+it",
]

DOWNVOTE_PATTERNS = [
    r"^\s*-\s*$",
    r"^\s*-1\s*$",
    r"bad", r"terrible", r"trash", r"worst", r"noob",
    r"👎",
]

UPVOTE_REGEX = re.compile("|".join(UPVOTE_PATTERNS), re.IGNORECASE)
DOWNVOTE_REGEX = re.compile("|".join(DOWNVOTE_PATTERNS), re.IGNORECASE)


# =============== DB INIT ===============
def _init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS karma (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                score   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cooldown (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                last_time INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        con.commit()


_init_db()


# =============== DB HELPERS ===============
def is_enabled(chat_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT enabled FROM settings WHERE chat_id = ?", (chat_id,))
        row = cur.fetchone()
        return True if row is None else bool(row[0])


def set_enabled(chat_id: int, enabled: bool) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO settings(chat_id, enabled) VALUES(?, ?)\n             ON CONFLICT(chat_id) DO UPDATE SET enabled = excluded.enabled",
            (chat_id, 1 if enabled else 0),
        )
        con.commit()


def add_karma(chat_id: int, user_id: int, delta: int) -> int:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO karma(chat_id, user_id, score) VALUES(?, ?, 0)\n             ON CONFLICT(chat_id, user_id) DO NOTHING",
            (chat_id, user_id),
        )
        con.execute(
            "UPDATE karma SET score = score + ? WHERE chat_id = ? AND user_id = ?",
            (delta, chat_id, user_id),
        )
        cur = con.execute(
            "SELECT score FROM karma WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        score = cur.fetchone()[0]
        con.commit()
        return score


def get_karma(chat_id: int, user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT score FROM karma WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def get_top(chat_id: int, limit: int = 10) -> List[Tuple[int, int]]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT user_id, score FROM karma WHERE chat_id = ? ORDER BY score DESC, user_id ASC LIMIT ?",
            (chat_id, limit),
        )
        rows = cur.fetchall()
        return [(int(u), int(s)) for (u, s) in rows]


def check_cooldown(chat_id: int, user_id: int) -> bool:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT last_time FROM cooldown WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = cur.fetchone()
        if row and now - row[0] < COOLDOWN_SECONDS:
            return False
        con.execute(
            "INSERT INTO cooldown(chat_id, user_id, last_time) VALUES(?, ?, ?)\n             ON CONFLICT(chat_id, user_id) DO UPDATE SET last_time = excluded.last_time",
            (chat_id, user_id, now),
        )
        con.commit()
        return True


# =============== UTIL ===============
def _extract_target_user(msg: Message) -> Optional[int]:
    if msg.reply_to_message:
        if msg.reply_to_message.from_user and not msg.reply_to_message.from_user.is_bot:
            return msg.reply_to_message.from_user.id
    return None


# =============== HANDLERS ===============
@Gojo.on_message(filters.command(["karmastat"]) & filters.group)
async def karmastat_toggle(_, m: Message):
    if not m.from_user:
        return

    try:
        member = await m.chat.get_member(m.from_user.id)
        if member.status not in (enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR):
            return await m.reply_text("Only admins can toggle Karma in this chat.")
    except Exception:
        return await m.reply_text("Couldn't verify permissions right now.")

    arg = (m.text.split(maxsplit=1)[1].strip().lower() if len(m.command) > 1 else "").strip()
    if arg in ("on", "enable", "enabled", "true", "1"):
        set_enabled(m.chat.id, True)
        return await m.reply_text("✅ Karma system is now ON in this chat.")
    if arg in ("off", "disable", "disabled", "false", "0"):
        set_enabled(m.chat.id, False)
        return await m.reply_text("🚫 Karma system is now OFF in this chat.")

    status = "ON" if is_enabled(m.chat.id) else "OFF"
    await m.reply_text(f"Karma is currently **{status}** here.\nUsage: `/karmastat ON` or `/karmastat OFF`", quote=True)


@Gojo.on_message(filters.command(["karma"]) & filters.group)
async def karma_cmd(_, m: Message):
    if not is_enabled(m.chat.id):
        return await m.reply_text("Karma is OFF in this chat. Ask an admin to `/karmastat ON`.", quote=True)

    if m.reply_to_message and m.reply_to_message.from_user and not m.reply_to_message.from_user.is_bot:
        uid = m.reply_to_message.from_user.id
        score = get_karma(m.chat.id, uid)
        return await m.reply_text(
            f"{m.reply_to_message.from_user.mention} has **{score}** karma here.",
            quote=True,
        )

    top = get_top(m.chat.id, 10)
    if not top:
        return await m.reply_text("No karma data yet. Reply with `+` or `-` to start!", quote=True)

    lines = ["🏆 **Top 10 Karma**"]
    for idx, (uid, score) in enumerate(top, 1):
        try:
            u = await _.get_users(uid)
            name = u.mention if u else f"`{uid}`"
        except Exception:
            name = f"`{uid}`"
        lines.append(f"**{idx}.** {name} — **{score}**")

    await m.reply_text("\n".join(lines), quote=True, disable_web_page_preview=True)


@Gojo.on_message(filters.group & filters.text & filters.reply)
async def karma_catcher(_, m: Message):
    if not is_enabled(m.chat.id):
        return
    if not m.from_user or m.from_user.is_bot:
        return

    target_id = _extract_target_user(m)
    if not target_id or target_id == m.from_user.id:
        return

    if not check_cooldown(m.chat.id, m.from_user.id):
        return  # cooldown active

    text = m.text or ""
    delta = 0
    if UPVOTE_REGEX.search(text):
        delta += 1
    if DOWNVOTE_REGEX.search(text):
        delta -= 1

    if delta == 0:
        return

    new_score = add_karma(m.chat.id, target_id, delta)
    try:
        target = await _.get_users(target_id)
        mention = target.mention if target else f"user `{target_id}`"
    except Exception:
        mention = f"user `{target_id}`"

    arrow = "▲" if delta > 0 else "▼"
    await m.reply_text(f"{arrow} {mention} now has **{new_score}** karma.", quote=True)


@Gojo.on_message(filters.command(["kstat"]) & filters.group)
async def karmastat_alias(_, m: Message):
    m.text = "/karmastat" + (" " + " ".join(m.command[1:]) if len(m.command) > 1 else "")
    await karmastat_toggle(_, m)


@Gojo.on_message(filters.command(["k"]) & filters.group)
async def karma_alias(_, m: Message):
    await karma_cmd(_, m)



