import asyncio
from pyrogram.types import Message
from pyrogram.enums import ChatType, ChatMemberStatus
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command


@Gojo.on_message(command("tagall"))
async def tag_all_members(c: Gojo, m: Message):
    """Mention all members in batches of 5 with bullet points and delay"""
    try:
        # Check if the command is used in a group
        if m.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return await m.reply_text("❌ This command only works in groups!")

        # Check if user is admin
        try:
            user = await m.chat.get_member(m.from_user.id)
            if user.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await m.reply_text("❌ You need to be an admin to use this command.")
        except Exception as e:
            return await m.reply_text(f"⚠️ Failed to check your permissions: {e}")

        # Check if message is a reply or has text
        if not m.reply_to_message and len(m.command) == 1:
            return await m.reply_text("ℹ️ Reply to a message or provide text to mention others!")

        # Extract query / reply mode
        query = ""
        reply_mode = False
        if len(m.command) > 1:
            query = " ".join(m.command[1:])
        elif m.reply_to_message:
            reply_mode = True

        # Send initial processing message
        processing_msg = await m.reply_text("🔄 Fetching members...")

        # Fetch all members
        members = []
        try:
            async for member in c.get_chat_members(m.chat.id):
                if not member.user.is_bot and not member.user.is_deleted:
                    members.append(member.user)
        except Exception as e:
            return await processing_msg.edit_text(f"⚠️ Failed to fetch members: {e}")

        if not members:
            return await processing_msg.edit_text("❌ No members available to tag!")

        # Create batches of 5 members
        batch_size = 5
        member_batches = [members[i:i + batch_size] for i in range(0, len(members), batch_size)]

        await processing_msg.delete()

        # Send batches one by one
        total = len(members)
        done = 0
        first_msg = None

        for idx, batch in enumerate(member_batches, start=1):
            batch_text = f"📢 **Tagging Members ({done + 1}–{done + len(batch)}/{total})**\n\n"

            # If text provided → show in every batch
            if query:
                batch_text += f"💬 **Message:** {query}\n\n"

            # Add mentions
            for user in batch:
                batch_text += f"• [{user.first_name}](tg://user?id={user.id})\n"

            try:
                sent = await c.send_message(
                    m.chat.id,
                    batch_text,
                    disable_web_page_preview=True,
                    reply_to_message_id=m.reply_to_message.id if reply_mode else None
                )
                if first_msg is None:
                    first_msg = sent
            except Exception as e:
                await c.send_message(m.chat.id, f"⚠️ Failed to send batch {idx}: {e}")

            done += len(batch)
            await asyncio.sleep(1.5)  # 1.5 second delay between batches

        # Send completion message
        if first_msg:
            await c.send_message(
                m.chat.id,
                f"✅ All {total} members tagged successfully!",
                reply_to_message_id=first_msg.id if not reply_mode else m.reply_to_message.id
            )

    except Exception as e:
        await m.reply_text(f"⚠️ An unexpected error occurred: {str(e)}")


__PLUGIN__ = "ᴛᴀɢᴀʟʟ"

__HELP__ = """
**👥 Advanced Member Tagger**

`/tagall` - Tags all members in batches
• 5 mentions per message
• 1.5s delay between batches
• Bullet point formatting
• Custom text appears in every batch
• Reply mode: bot replies to the same message for every batch

**Requirements:**
- Must be used in groups/supergroups
- User must be an admin

**Usage:**
- `/tagall Hello everyone!` → tags all with custom text in every batch
- Reply to a message with `/tagall` → tags all while replying to that message in every batch
"""
