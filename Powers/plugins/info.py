import os
import asyncio
from datetime import datetime
from traceback import format_exc

from pyrogram import enums
from pyrogram.errors import (
    EntityBoundsInvalid, 
    MediaCaptionTooLong, 
    RPCError,
    PeerIdInvalid,
    UsernameInvalid,
    UsernameNotOccupied,
    ChannelInvalid,
    ChatAdminRequired,
    FloodWait
)
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.users import GetFullUser
from pyrogram.raw.types import Channel, UserFull
from pyrogram.types import Message

from Powers import BDB_URI, LOGGER, OWNER_ID
from Powers.bot_class import Gojo
from Powers.database.antispam_db import GBan
from Powers.database.approve_db import Approve
from Powers.supports import get_support_staff
from Powers.utils.custom_filters import command
from Powers.utils.extract_user import extract_user

gban_db = GBan()

if BDB_URI:
    from Powers.plugins import bday_info

async def count(c: Gojo, chat_id):
    """Count admins, bots, and banned members in a chat"""
    try:
        # Get administrators
        administrators = []
        async for admin in c.get_chat_members(
            chat_id=chat_id, 
            filter=enums.ChatMembersFilter.ADMINISTRATORS
        ):
            administrators.append(admin)
        
        # Get bots
        bots = []
        async for bot in c.get_chat_members(
            chat_id=chat_id, 
            filter=enums.ChatMembersFilter.BOTS
        ):
            bots.append(bot)

        # Get banned members
        banned = []
        async for banned_member in c.get_chat_members(
            chat_id, 
            filter=enums.ChatMembersFilter.BANNED
        ):
            banned.append(banned_member)

        # Count bot admins
        bot_admin_count = 0
        admin_ids = {admin.user.id for admin in administrators}
        for bot in bots:
            if bot.user.id in admin_ids:
                bot_admin_count += 1

        return len(bots), len(administrators), bot_admin_count, len(banned)
    
    except (PeerIdInvalid, ChannelInvalid, ChatAdminRequired):
        return "Not in chat", "Not in chat", "Not in chat", "Not in chat"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await count(c, chat_id)
    except Exception as e:
        LOGGER.error(f"Error counting chat members: {e}")
        return "Error", "Error", "Error", "Error"


async def user_info(c: Gojo, user_id, already=False):
    """Get comprehensive information about a user"""
    try:
        # Get user full information
        user_all = await c.invoke(GetFullUser(id=await c.resolve_peer(user_id)))
        user = await c.get_users(user_id)
        
        if user.is_deleted:
            return "❌ **Deleted Account**\nThis user has deleted their account.", None

        full_user = user_all.full_user
        
        # Check if user is GBanned
        gbanned, reason_gban = gban_db.get_gban(user.id)
        
        # Get support staff information
        SUPPORT_STAFF = get_support_staff()
        
        # Process birthday information
        dob = None
        if full_user.birthday:
            dob = datetime(
                int(full_user.birthday.year), 
                int(full_user.birthday.month), 
                int(full_user.birthday.day)
            ).strftime("%d %B %Y")
        elif BDB_URI:
            try:
                if result := bday_info.find_one({"user_id": user_id}):
                    u_dob = datetime.strptime(result["dob"], "%d/%m/%Y")
                    day = u_dob.day
                    formatted = u_dob.strftime("%B %Y")
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    dob = f"{day}{suffix} {formatted}"
            except Exception:
                pass

        # Determine user role/type
        user_role = "User"
        if user_id == c.me.id:
            user_role = "Bot"
        elif user_id == OWNER_ID:
            user_role = "Owner"
        elif user_id in get_support_staff("dev"):
            user_role = "Developer"
        elif user_id in get_support_staff("sudo"):
            user_role = "Sudo User"
        elif user_id in get_support_staff("whitelist"):
            user_role = "Whitelisted User"

        # Get last seen status
        last_seen = "Unknown"
        if user.status:
            if user.status == enums.UserStatus.RECENTLY:
                last_seen = "Recently"
            elif user.status == enums.UserStatus.LAST_WEEK:
                last_seen = "Last Week"
            elif user.status == enums.UserStatus.LAST_MONTH:
                last_seen = "Last Month"
            elif user.status == enums.UserStatus.LONG_AGO:
                last_seen = "Long Ago"
            elif user.status == enums.UserStatus.ONLINE:
                last_seen = "Online"
            elif user.status == enums.UserStatus.OFFLINE:
                try:
                    last_seen = datetime.fromtimestamp(user.status.date).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    last_seen = "Offline"

        # Build information caption
        caption = f"""
👤 **USER INFORMATION**

**🆔 User ID:** `{user.id}`
**👤 Mention:** {user.mention}
**📛 Full Name:** `{user.first_name or 'No first name'} {user.last_name or ''}`.strip()
**🔗 Username:** @{user.username if user.username else 'None'}
**📝 Bio:** `{full_user.about or 'No bio available'}`

**🎂 Birthday:** {dob or 'Not set'}
**👥 Role:** {user_role}
**🔒 GBanned:** {'Yes' if gbanned else 'No'}
"""

        if gbanned:
            caption += f"**📋 GBan Reason:** `{reason_gban}`\n"

        caption += f"""
**🌐 DC ID:** {user.dc_id or 'Unknown'}
**✅ Verified:** {'Yes' if user.is_verified else 'No'}
**🚫 Restricted:** {'Yes' if user.is_restricted else 'No'}
**⚠️ Scam:** {'Yes' if user.is_scam else 'No'}
**❌ Fake:** {'Yes' if user.is_fake else 'No'}
**🤖 Bot:** {'Yes' if user.is_bot else 'No'}
**👀 Last Seen:** {last_seen}
"""

        return caption, user.photo.big_file_id if user.photo else None

    except (PeerIdInvalid, UsernameInvalid, UsernameNotOccupied):
        return "❌ **User Not Found**\nThe specified user could not be found.", None
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await user_info(c, user_id, already)
    except Exception as e:
        LOGGER.error(f"Error getting user info: {e}")
        return f"❌ **Error**\nFailed to fetch user information: {str(e)}", None


async def chat_info(c: Gojo, chat_id, already=False):
    """Get comprehensive information about a chat"""
    try:
        if not already:
            chat = await c.get_chat(chat_id)
        else:
            chat = chat_id

        # Get full chat information
        try:
            chat_r = await c.resolve_peer(chat.id)
            full_chat = await c.invoke(GetFullChannel(channel=chat_r))
            usernames = getattr(full_chat.chats[0], 'usernames', [])
        except Exception:
            usernames = []
            full_chat = None

        # Count members
        total_bot, total_admin, total_bot_admin, total_banned = await count(c, chat.id)

        # Build information caption
        caption = f"""
🏢 **CHAT INFORMATION**

**🆔 Chat ID:** `{chat.id}`
**📛 Title:** {chat.title}
**📊 Type:** {str(chat.type).split('.')[-1].title()}
**🌐 DC ID:** {chat.dc_id or 'Unknown'}

**🔗 Usernames:** {' '.join([f'@{u}' for u in usernames]) if usernames else '@' + chat.username if chat.username else 'None'}
**👥 Members:** {chat.members_count or 'Unknown'}
**⚜️ Administrators:** {total_admin}
**🤖 Bots:** {total_bot}
**🚫 Banned Users:** {total_banned}
**🤖 Admin Bots:** {total_bot_admin}

**⚠️ Scam:** {'Yes' if chat.is_scam else 'No'}
**❌ Fake:** {'Yes' if chat.is_fake else 'No'}
**🔒 Restricted:** {'Yes' if chat.is_restricted else 'No'}
**🛡️ Protected Content:** {'Yes' if chat.has_protected_content else 'No'}

**📝 Description:**\n`{chat.description or 'No description available'}`
"""

        if chat.linked_chat:
            caption += f"**🔗 Linked Chat:** `{chat.linked_chat.id}`\n"

        return caption, chat.photo.big_file_id if chat.photo else None

    except (PeerIdInvalid, UsernameInvalid, UsernameNotOccupied, ChannelInvalid):
        return "❌ **Chat Not Found**\nThe specified chat could not be found.", None
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await chat_info(c, chat_id, already)
    except Exception as e:
        LOGGER.error(f"Error getting chat info: {e}")
        return f"❌ **Error**\nFailed to fetch chat information: {str(e)}", None


@Gojo.on_message(command(["info", "whois"]))
async def info_func(c: Gojo, message: Message):
    """Handle /info and /whois commands"""
    if message.reply_to_message and message.reply_to_message.sender_chat:
        await message.reply_text("ℹ️ This is a channel, not a user. Use `/chinfo` to get channel information.")
        return

    try:
        user, _, user_name = await extract_user(c, message)
    except Exception as e:
        await message.reply_text(f"❌ Failed to extract user: {str(e)}")
        LOGGER.error(f"Error extracting user: {e}\n{format_exc()}")
        return

    m = await message.reply_text(f"🔍 Fetching information for {'@' + user_name if user_name else 'user'}...")

    try:
        info_caption, photo_id = await user_info(c, user)
    except Exception as e:
        await m.edit_text(f"❌ Error fetching user information: {str(e)}")
        LOGGER.error(f"Error in user_info: {e}\n{format_exc()}")
        return

    # Get user status in current chat if applicable
    if message.chat.type != enums.ChatType.PRIVATE:
        try:
            member = await message.chat.get_member(user)
            status = str(member.status).split(".")[-1].title()
            
            # Check if user is approved
            if status == "Member" and Approve(message.chat.id).check_approve(user):
                status = "Member (Approved)"
                
            info_caption += f"\n**💬 Current Chat Status:** {status}"
        except Exception:
            pass  # Skip if we can't get member status

    # Send the information
    if not photo_id:
        await m.delete()
        await asyncio.sleep(1)
        return await message.reply_text(info_caption, disable_web_page_preview=True)

    try:
        photo = await c.download_media(photo_id)
        await m.delete()
        await asyncio.sleep(1)
        
        try:
            await message.reply_photo(photo, caption=info_caption, quote=False)
        except MediaCaptionTooLong:
            # If caption is too long, send photo and text separately
            sent_photo = await message.reply_photo(photo, quote=False)
            await sent_photo.reply_text(info_caption)
        except EntityBoundsInvalid:
            # If entity bounds are invalid, send text only
            await message.reply_text(info_caption, disable_web_page_preview=True)
        
        # Clean up downloaded photo
        if os.path.exists(photo):
            os.remove(photo)
            
    except Exception as e:
        await m.edit_text(f"❌ Error sending information: {str(e)}")
        LOGGER.error(f"Error sending user info: {e}\n{format_exc()}")


@Gojo.on_message(command(["chinfo", "chatinfo", "chat_info"]))
async def chat_info_func(c: Gojo, message: Message):
    """Handle /chinfo, /chatinfo, and /chat_info commands"""
    chat_input = None
    
    # Determine which chat to get info for
    if len(message.command) > 1:
        chat_input = message.command[1]
    elif message.reply_to_message and message.reply_to_message.sender_chat:
        chat_input = message.reply_to_message.sender_chat.id
    else:
        chat_input = message.chat.id

    m = await message.reply_text("🔍 Fetching chat information...")

    try:
        info_caption, photo_id = await chat_info(c, chat_input)
    except Exception as e:
        await m.edit_text(f"❌ Error fetching chat information: {str(e)}")
        LOGGER.error(f"Error in chat_info: {e}\n{format_exc()}")
        return

    # Send the information
    if not photo_id:
        await m.delete()
        await asyncio.sleep(1)
        return await message.reply_text(info_caption, disable_web_page_preview=True)

    try:
        photo = await c.download_media(photo_id)
        await m.delete()
        await asyncio.sleep(1)
        
        try:
            await message.reply_photo(photo, caption=info_caption, quote=False)
        except MediaCaptionTooLong:
            # If caption is too long, send photo and text separately
            sent_photo = await message.reply_photo(photo, quote=False)
            await sent_photo.reply_text(info_caption)
        except EntityBoundsInvalid:
            # If entity bounds are invalid, send text only
            await message.reply_text(info_caption, disable_web_page_preview=True)
        
        # Clean up downloaded photo
        if os.path.exists(photo):
            os.remove(photo)
            
    except Exception as e:
        await m.edit_text(f"❌ Error sending information: {str(e)}")
        LOGGER.error(f"Error sending chat info: {e}\n{format_exc()}")


__PLUGIN__ = "ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ"
__alt_name__ = ["info", "chinfo", "whois", "chatinfo"]

__HELP__ = """
**📊 Information Module**

• /info or /whois [username|id|reply] - Get detailed information about a user
• /chinfo or /chatinfo [username|id|reply] - Get detailed information about a chat/channel

**Examples:**
- `/info @username` - Get info about a user
- `/info` (reply to a message) - Get info about the replied user
- `/chinfo @channelname` - Get info about a channel
- `/chinfo` (in a group) - Get info about the current group
"""
