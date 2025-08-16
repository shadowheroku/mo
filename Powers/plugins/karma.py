import json
import time
import asyncio
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
DB_FILE = "karma.json"
COOLDOWN = 30  # seconds between votes to prevent spam
lock = asyncio.Lock()  # prevent race conditions

# ===== DATABASE HELPERS =====
def load_karma():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_karma(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def get_karma(user_id: int):
    async with lock:
        data = load_karma()
        return data.get(str(user_id), {}).get("karma", 0)

async def update_karma(user_id: int, change: int):
    async with lock:
        data = load_karma()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {"karma": 0, "last_vote": 0}
        data[uid]["karma"] += change
        save_karma(data)
        return data[uid]["karma"]

async def can_vote(user_id: int):
    async with lock:
        data = load_karma()
        uid = str(user_id)
        now = time.time()
        if uid not in data:
            data[uid] = {"karma": 0, "last_vote": now}
            save_karma(data)
            return True
        last_vote = data[uid].get("last_vote", 0)
        return now - last_vote >= COOLDOWN

async def set_last_vote(user_id: int):
    async with lock:
        data = load_karma()
        uid = str(user_id)
        now = time.time()
        if uid not in data:
            data[uid] = {"karma": 0, "last_vote": now}
        else:
            data[uid]["last_vote"] = now
        save_karma(data)

# ===== COMMANDS =====
@Gojo.on_message(filters.command("karma") & filters.group)
async def karma_info(c, m):
    user = m.reply_to_message.from_user if m.reply_to_message else m.from_user
    karma = await get_karma(user.id)
    await m.reply_text(f"💫 Karma of {user.mention}: **{karma}**")

@Gojo.on_message(filters.command("topkarma") & filters.group)
async def top_karma(c, m):
    async with lock:
        data = load_karma()
    if not data:
        await m.reply_text("No karma data yet.")
        return

    top_users = sorted(data.items(), key=lambda x: x[1]["karma"], reverse=True)[:10]
    text = "🏆 **Top Karma Users:**\n\n"
    for i, (uid, info) in enumerate(top_users, start=1):
        try:
            user = await c.get_users(int(uid))
            text += f"{i}. {user.first_name}: {info['karma']}\n"
        except:
            text += f"{i}. Unknown User ({uid}): {info['karma']}\n"
    await m.reply_text(text)

# ===== KARMA VIA + / - REPLIES =====
@Gojo.on_message(filters.group & filters.reply & filters.text)
async def karma_vote(c, m):
    voter = m.from_user
    target_msg = m.reply_to_message
    if not target_msg or not target_msg.from_user:
        return
    target_user = target_msg.from_user

    if voter.id == target_user.id:
        await m.reply_text("❌ You cannot vote for yourself!")
        return

    if not await can_vote(voter.id):
        await m.reply_text(f"⏱️ Wait {COOLDOWN} seconds before voting again.")
        return

    if m.text.strip() == "+":
        karma = await update_karma(target_user.id, 1)
        await m.reply_text(f"👍 {target_user.mention} gained 1 karma! Total: {karma}")
    elif m.text.strip() == "-":
        karma = await update_karma(target_user.id, -1)
        await m.reply_text(f"👎 {target_user.mention} lost 1 karma! Total: {karma}")
    else:
        return  # ignore other messages

    await set_last_vote(voter.id)

# ===== METADATA =====
__PLUGIN__ = "Super Fast Karma System (+/- Voting)"
__HELP__ = """
💫 **Super Fast Karma System**

• Reply with `+` to give karma
• Reply with `-` to remove karma
• /karma → Check user's karma
• /topkarma → Show top 10 users
• Anti-self-voting & cooldown prevents spam
• Uses JSON for lightning-fast performance
"""
