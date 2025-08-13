import random
from typing import Optional

from pyrogram import filters
from pyrogram.types import Message, InputMediaPhoto
from PIL import Image, ImageDraw
import requests
from io import BytesIO

from Powers.bot_class import Gojo
from pyrogram import filters

def command(commands: str or list, prefixes: str or list = "/", case_sensitive: bool = False):
    """
    Decorator for creating command filters.
    
    Args:
        commands (str or list): Command or list of commands
        prefixes (str or list): Prefix or list of prefixes (default: "/")
        case_sensitive (bool): Whether commands are case sensitive (default: False)
    """
    if isinstance(commands, str):
        commands = [commands]
    if isinstance(prefixes, str):
        prefixes = [prefixes]

    async def func(flt, _, message):
        text = message.text or message.caption or ""
        if not text:
            return False

        text = text.split()
        if not text:
            return False

        command_parts = text[0].lower() if not flt.case_sensitive else text[0]
        command_parts = command_parts.lstrip(flt.prefixes[0])

        for command in flt.commands:
            cmd = command.lower() if not flt.case_sensitive else command
            if command_parts == cmd:
                return True

        return False

    return filters.create(
        func,
        "CustomCommandFilter",
        commands=commands,
        prefixes=prefixes,
        case_sensitive=case_sensitive
    )

from typing import Union, Optional
from pyrogram.types import Message, User

async def extract_user(client, message: Message) -> Union[int, str, None]:
    """
    Extract user ID or username from a message.
    
    Args:
        client: Pyrogram client
        message: Message object
        
    Returns:
        Union[int, str, None]: User ID, username, or None if not found
    """
    # If replied to message
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id if user else None

    # If command has arguments
    if len(message.command) > 1:
        user = message.command[1]
        
        # Check if it's a user ID
        if user.isdigit():
            return int(user)
        
        # Check if it's a username
        if user.startswith("@"):
            try:
                user_obj = await client.get_users(user)
                return user_obj.id
            except Exception:
                return None
    
    # If no user specified, return the message author
    return message.from_user.id if message.from_user else None

async def get_user_photo(user_id: int, client: Gojo) -> Optional[BytesIO]:
    try:
        photos = [photo async for photo in client.get_chat_photos(user_id, limit=1)]
        if not photos:
            return None
            
        photo = await client.download_media(photos[0].file_id, in_memory=True)
        return photo
    except Exception:
        return None

async def create_waifu_image(waifu_photo: BytesIO, user_name: str) -> BytesIO:
    # Base template (you can replace with your own)
    template = Image.open("couplepic.jpg")  # You should provide this
    
    # Process waifu photo
    waifu_img = Image.open(waifu_photo)
    waifu_img = waifu_img.resize((400, 400))
    
    # Create circular mask
    mask = Image.new("L", (400, 400), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 400, 400), fill=255)
    
    # Composite images
    template.paste(waifu_img, (200, 100), mask)
    
    # Add text
    draw = ImageDraw.Draw(template)
    draw.text((400, 550), f"{user_name}'s Waifu", fill="white", font_size=40, anchor="mm")
    
    # Save to bytes
    output = BytesIO()
    template.save(output, format="PNG")
    output.seek(0)
    return output

async def create_couple_image(user1_photo: BytesIO, user2_photo: BytesIO, user1_name: str, user2_name: str) -> BytesIO:
    # Base template (you can replace with your own)
    template = Image.open("assets/couple_template.png")  # You should provide this
    
    # Process user photos
    user1_img = Image.open(user1_photo).resize((300, 300))
    user2_img = Image.open(user2_photo).resize((300, 300))
    
    # Create circular masks
    mask = Image.new("L", (300, 300), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, 300, 300), fill=255)
    
    # Composite images
    template.paste(user1_img, (150, 150), mask)
    template.paste(user2_img, (550, 150), mask)
    
    # Add text
    draw = ImageDraw.Draw(template)
    draw.text((400, 500), f"Today's Couple\n{user1_name} 💖 {user2_name}", 
              fill="white", font_size=40, anchor="mm", align="center")
    
    # Save to bytes
    output = BytesIO()
    template.save(output, format="PNG")
    output.seek(0)
    return output

@Gojo.on_message(command("waifu"))
async def waifu_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        await m.reply_text("This command only works in groups!")
        return
    
    # Get random member (excluding bots)
    members = [
        member.user 
        async for member in chat.get_members() 
        if not member.user.is_bot and member.user.id != m.from_user.id
    ]
    
    if not members:
        await m.reply_text("Couldn't find anyone to be your waifu 😢")
        return
    
    waifu = random.choice(members)
    waifu_photo = await get_user_photo(waifu.id, c)
    
    if not waifu_photo:
        await m.reply_text(
            f"✨ {m.from_user.mention} your waifu is {waifu.mention}! ✨\n"
            "(They don't have a profile photo though 😅)"
        )
        return
    
    # Create waifu image
    image = await create_waifu_image(waifu_photo, m.from_user.first_name)
    
    # Send the image
    await m.reply_photo(
        photo=image,
        caption=f"✨ {m.from_user.mention} your waifu is {waifu.mention}! ✨"
    )

@Gojo.on_message(command("couple"))
async def couple_cmd(c: Gojo, m: Message):
    chat = m.chat
    if chat.type == "private":
        await m.reply_text("This command only works in groups!")
        return
    
    # Get random members (excluding bots and same user)
    members = [
        member.user 
        async for member in chat.get_members() 
        if not member.user.is_bot
    ]
    
    if len(members) < 2:
        await m.reply_text("Need at least 2 members to form a couple!")
        return
    
    # Get two distinct random members
    user1, user2 = random.sample(members, 2)
    while user1.id == user2.id:
        user2 = random.choice(members)
    
    # Get profile photos
    user1_photo = await get_user_photo(user1.id, c)
    user2_photo = await get_user_photo(user2.id, c)
    
    if not user1_photo or not user2_photo:
        await m.reply_text(
            f"✨ Today's couple is {user1.mention} 💖 {user2.mention}! ✨\n"
            "(One or both don't have profile photos though 😅)"
        )
        return
    
    # Create couple image
    image = await create_couple_image(user1_photo, user2_photo, user1.first_name, user2.first_name)
    
    # Send the image
    await m.reply_photo(
        photo=image,
        caption=f"✨ Today's couple is {user1.mention} 💖 {user2.mention}! ✨"
    )

__PLUGIN__ = "waifu_couple"
__HELP__ = """
**Waifu/Couple Commands**

• `/waifu` - Choose a random member as your waifu/husbando
• `/couple` - Choose two random members as today's couple
"""
