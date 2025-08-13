import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.raw.functions.messages import DeleteHistory
from Powers.bot_class import Gojo

# ─── USERBOT SESSION CONFIG ───
# Replace with your own userbot session string and API credentials
# Or load them from env/config
API_ID = 23212132       # your api_id
API_HASH = "1c17efa86bdef8f806ed70e81b473c20"
SESSION_STRING = "BQGvJ_0Adt6lmVaTljo96G9YV0xaOi0O26V2utMXtqO1d9cySnNMh1KCQh2oqT2rxMwDjTj274JF5QDUOF1wO21nH52TvrOuqDvnuZbiOsKM7o4XeTS5CLmwJFAP0IKDvAvEgCnfVGLBGuaOJEijZNaP4nhFvtMP_sMLYjLATOsJHZLEkdz4PkJyfQZCMTV6MSR1D7BFnythV1VTBRA7qIjqYenmEZzGVHXGy4DaetN-BbDwJZmf2QIIZx90Q2-zvFl_z7-2srBWXcOYYDT5pZ1UkwtX71c1hChhmuFJHhLejZz0PWoTUyVr35GRto9J5QU4D0xGvdTaw8qi7m7qe5Gk4IZkjQAAAAHdw02OAA"

# Create userbot client
userbot = Client(
    name="userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

# Track available assistants
assistants = {1: userbot}

@Gojo.on_message(filters.command("sg"))
async def sg_cmd(c: Gojo, m: Message):
    # Check usage
    if not (len(m.text.split()) > 1 or m.reply_to_message):
        return await m.reply_text("⚠️ **Usage:** `/sg` username | user_id | reply to a user")

    # Determine target user
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
    else:
        target_id = m.text.split()[1]

    # Processing message
    status = await m.reply_text("🔍 **Running Sangmata lookup...**")

    # Try to get the user object
    try:
        user = await c.get_users(target_id)
    except Exception:
        return await status.edit("❌ **Invalid user specified!**")

    # Pick which Sangmata bot to use
    sg_bot = random.choice(["sangmata_bot", "sangmata_beta_bot"])

    if 1 in assistants:
        ubot = assistants[1]
    else:
        return await status.edit("❌ **Userbot not found in assistants!**")

    # Ensure userbot is connected
    if not ubot.is_connected:
        await ubot.start()

    # Send user ID to Sangmata
    try:
        send_msg = await ubot.send_message(sg_bot, str(user.id))
        await send_msg.delete()
    except Exception as e:
        return await status.edit(f"❌ **Failed to contact Sangmata:** `{e}`")

    await asyncio.sleep(1)  # Give Sangmata time to respond

    # Search for Sangmata's reply
    async for stalk in ubot.search_messages(send_msg.chat.id):
        if stalk and stalk.text:
            result = (
                f"🕵️ **Sangmata Info for {user.mention}**\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"{stalk.text}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🔍 _Powered by @MonicRobot _"
            )
            await m.reply_text(result)
            break
    else:
        await m.reply_text("😔 **Sangmata returned no data.**")

    # Clean chat history with Sangmata
    try:
        user_info = await ubot.resolve_peer(sg_bot)
        await ubot.send(DeleteHistory(peer=user_info, max_id=0, revoke=True))
    except Exception:
        pass

    await status.delete()

__PLUGIN__ = "sangmata"
__HELP__ = """
**🕵️ Sangmata Command 🕵️**
• `/sg` username / user_id / reply  
   Get a user’s past names & usernames using Sangmata.
"""
