from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from pyrogram.types import Message

# 🎲 Generic function to send dice and reply with score
async def send_game(c: Gojo, m: Message, emoji: str = "🎲"):
    x = await c.send_dice(m.chat.id, emoji)
    score = x.dice.value
    await m.reply_text(f"Hey {m.from_user.mention}, your score is: {score}", quote=True)



@Gojo.on_message(command("dart"))
async def dart_cmd(c: Gojo, m: Message):
    await send_game(c, m, "🎯")

@Gojo.on_message(command("basket"))
async def basket_cmd(c: Gojo, m: Message):
    await send_game(c, m, "🏀")

@Gojo.on_message(command("jackpot"))
async def jackpot_cmd(c: Gojo, m: Message):
    await send_game(c, m, "🎰")

@Gojo.on_message(command("ball"))
async def ball_cmd(c: Gojo, m: Message):
    await send_game(c, m, "🎳")

@Gojo.on_message(command("football"))
async def football_cmd(c: Gojo, m: Message):
    await send_game(c, m, "⚽")

__PLUGIN__ = "ɢᴀᴍᴇs"

__HELP__ = """
🎮 **ᴘʟᴀʏ ᴍɪɴɪ ɢᴀᴍᴇs ᴡɪᴛʜ ᴇᴍᴏᴊɪ ᴅɪᴄᴇ!**
  
`/dart` - ᴅᴀʀᴛ 🎯  
`/basket` - ʙᴀsᴋᴇᴛʙᴀʟʟ 🏀  
`/ball` - ʙᴏᴡʟɪɴɢ 🎳  
`/football` - ғᴏᴏᴛʙᴀʟʟ ⚽  
`/jackpot` - sʟᴏᴛ ᴍᴀᴄʜɪɴᴇ 🎰
"""

