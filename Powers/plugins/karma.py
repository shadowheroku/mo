import sqlite3
import time
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
DB_FILE = "karma.db"
COOLDOWN = 30  # seconds between votes to prevent spam

# ===== DATABASE SETUP =====
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS karma (
    user_id INTEGER PRIMARY KEY,
    karma INTEGER DEFAULT 0,
    last_vote REAL DEFAULT 0
)
""")
conn.commit()

# ===== HELPERS =====
def get_karma(user_id):
    c.execute("SELECT karma FROM karma WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

def update_karma(user_id, change):
    c.execute("INSERT OR IGNORE INTO karma (user_id, karma, last_vote) VALUES (?, ?, ?)",
              (user_id, 0, 0))
    c.execute("UPDATE karma SET karma = karma + ? WHERE user_id=?", (change, user_id))
    conn.commit()
    return get_karma(user_id)

def can_vote(user_id):
    c.execute("SELECT last_vote FROM karma WHERE user_id=?", (user_id,))
    row = c.fetchone()
    now = time.time()
    if not row:
        c.execute("INSERT INTO karma (user_id, karma, last_vote) VALUES (?, ?, ?)", (user_id, 0, now))
        conn.commit()
        return True
    last_vote = row[0]
    if now - last_vote >= COOLDOWN:
        return True
    return False

def set_last_vote(user_id):
    now = time.time()
    c.execute("UPDATE karma SET last_vote=? WHERE user_id=?", (now, user_id))
    conn.commit()

# ===== COMMANDS =====
@Gojo.on_message(filters.command("karma") & filters.group)
async def karma_info(c, m):
    if len(m.command) > 1:
        try:
            user = m.reply_to_message.from_user if not m.entities else await c.get_users(m.command[1])
        except:
            user = m.from_user
    else:
        user = m.reply_to_message.from_user if m.reply_to_message else m.from_user

    karma = get_karma(user.id)
    await m.reply_text(f"💫 Karma of {user.mention}: **{karma}**")

@Gojo.on_message(filters.command("topkarma") & filters.group)
async def top_karma(c, m):
    c.execute("SELECT user_id, karma FROM karma ORDER BY karma DESC LIMIT 10")
    rows = c.fetchall()
    if not rows:
        await m.reply_text("No karma data yet.")
        return
    text = "🏆 **Top Karma Users:**\n\n"
    for i, (user_id, karma) in enumerate(rows, start=1):
        try:
            user = await c.get_users(user_id)
            text += f"{i}. {user.first_name}: {karma}\n"
        except:
            text += f"{i}. Unknown User ({user_id}): {karma}\n"
    await m.reply_text(text)

# ===== KARMA VIA + / - REPLIES =====
@Gojo.on_message(filters.group & filters.reply & filters.text)
async def karma_vote(c, m):
    voter = m.from_user
    target_msg = m.reply_to_message
    if not target_msg or not target_msg.from_user:
        return
    target_user = target_msg.from_user

    # Prevent self-voting
    if voter.id == target_user.id:
        await m.reply_text("❌ You cannot vote for yourself!")
        return

    # Cooldown check
    if not can_vote(voter.id):
        await m.reply_text(f"⏱️ Wait {COOLDOWN} seconds before voting again.")
        return

    # Determine vote
    if m.text.strip() == "+":
        change = 1
        karma = update_karma(target_user.id, change)
        await m.reply_text(f"👍 {target_user.mention} gained 1 karma! Total: {karma}")
    elif m.text.strip() == "-":
        change = -1
        karma = update_karma(target_user.id, change)
        await m.reply_text(f"👎 {target_user.mention} lost 1 karma! Total: {karma}")

    set_last_vote(voter.id)

# ===== METADATA =====
__PLUGIN__ = "Advanced Karma System (+/- Voting)"
__HELP__ = """
💫 **Advanced Karma System**

• Reply with `+` to give karma
• Reply with `-` to remove karma
• /karma [@user] → Check user's karma
• /topkarma → Show top 10 users
• Anti-self-voting & cooldown prevents spam
"""
