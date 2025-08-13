import os
import re
import yt_dlp
import asyncio
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
COOKIES_TEXT = """# Netscape HTTP Cookie File
.instagram.com	TRUE	/	TRUE	1777919447	datr	143pZ1hYClbcexl_gUXN3Pal
.instagram.com	TRUE	/	TRUE	1774895498	ig_did	60AE72B3-FADF-4895-AB50-0F0393CB9FD8
.instagram.com	TRUE	/	TRUE	1774895447	ig_nrcb	1
.instagram.com	TRUE	/	TRUE	1779637219	ps_l	1
.instagram.com	TRUE	/	TRUE	1779637219	ps_n	1
.instagram.com	TRUE	/	TRUE	1781798892	mid	aCS_7QALAAHzdnVO36G_4nmAqE1e
.instagram.com	TRUE	/	TRUE	1789651699	csrftoken	Ul6BXwt15N6lKAjGxyx9p9LGCYAxonVw
.instagram.com	TRUE	/	TRUE	1762867699	ds_user_id	70808632711
.instagram.com	TRUE	/	TRUE	1755696498	dpr	1.25
.instagram.com	TRUE	/	TRUE	1755696498	wd	1536x695
.instagram.com	TRUE	/	TRUE	1755600820	ig_direct_region_hint	"EAG\05470808632711\0541786532020:01fe1f4bd9d8d1909a6f0198c673a815a80184dafee3a9672a9f7e5d83afb54e342d0510"
.instagram.com	TRUE	/	TRUE	0	rur	"HIL\05470808632711\0541786627701:01fe2ed3df0d5a7b88a6724de023b481bfacbc88577aacc9497d9cfd5ca72ab551a900e7"
.instagram.com	TRUE	/	TRUE	1786627699	sessionid	70808632711%3AxRnDEvMHeyi86d%3A21%3AAYdZ3EHIFH_lwcZsN45_PyS4QLPAh24iBnjP3HJ1UA
"""

COOKIES_FILE = "instagram_cookies.txt"
with open(COOKIES_FILE, "w", encoding="utf-8") as f:
    f.write(COOKIES_TEXT.strip() + "\n")

# Regex to match Instagram URLs (supports query params)
INSTAGRAM_REGEX = re.compile(
    r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[A-Za-z0-9_-]+(?:\?[^\s]*)?)"
)

@Gojo.on_message(filters.regex(INSTAGRAM_REGEX))
async def insta_downloader(c, m):
    match = INSTAGRAM_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "insta_reel.mp4"

    status = await m.reply_text("📥 Downloading Instagram reel/post...")

    try:
        ydl_opts = {
            "outtmpl": temp_file,
            "format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "cookiefile": COOKIES_FILE,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        caption = (
            f"🎬 **Title:** {info.get('title', 'Unknown')}\n"
            f"👤 **Uploader:** {info.get('uploader', 'Unknown')}\n"
            f"📅 **Upload Date:** {info.get('upload_date', 'Unknown')}\n"
            f"🔗 **Original Link:** {url}\n\n"
            f"🤖 **Downloaded by:** @{c.me.username}"
        )

        sent_msg = await m.reply_video(video=temp_file, caption=caption)
        await status.delete()

        # Wait 30 seconds, then delete the sent video
        await asyncio.sleep(30)
        await sent_msg.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed to download:\n`{e}`")

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Plugin metadata
__PLUGIN__ = "Instagram Downloader"

__HELP__ = """
• Send an Instagram reel/post link (in groups or private) — I’ll download and send it to you with details.
• Works for public and private content if cookies are valid.
• Sent media will auto-delete after 30 seconds.
"""
