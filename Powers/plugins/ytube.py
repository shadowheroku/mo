import os
import wget
import asyncio
from pyrogram.enums import ParseMode as PM
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from youtubesearchpython import SearchVideos
from yt_dlp import YoutubeDL

from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command
from Powers.utils.cmd_senders import send_cmd
from Powers.utils.msg_types import Types

# Support button
SUPPORT_CHAT = "Shadowchathq"
BUTTON = [[InlineKeyboardButton("ꜱᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}")]]


def get_text(message: Message) -> str | None:
    """Extract text from a command message"""
    if not message.text:
        return None
    parts = message.text.split(None, 1)
    return parts[1] if len(parts) > 1 else None


@Gojo.on_message(command(["yt", "video"]))
async def yt_video_cmd(c: Gojo, m: Message):
    query = get_text(m)
    await m.delete()

    mention = f"[{m.from_user.first_name}](tg://user?id={m.from_user.id})"

    status = await c.send_message(m.chat.id, "🔍 Searching, please wait...")

    if not query:
        await status.edit("😴 No song found.\n\n» Maybe you typed it wrong?")
        await asyncio.sleep(60)
        await status.delete()
        return

    # 🔎 Search video
    search = SearchVideos(query, offset=1, mode="dict", max_results=1)
    result = search.result()
    if not result or "search_result" not in result or not result["search_result"]:
        await status.edit("❌ Couldn't find anything on YouTube.")
        await asyncio.sleep(60)
        await status.delete()
        return

    info = result["search_result"][0]
    video_url = info["link"]
    video_title = info["title"]
    video_id = info["id"]
    video_channel = info["channel"]
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    # Download thumbnail
    thumb_file = wget.download(thumbnail_url)

    # Create cookies content directly in code
    cookies_content = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	FALSE	1790413715	HSID	ALZ5C0Px7v3KlQH8T
.youtube.com	TRUE	/	TRUE	1790413715	SSID	AMhSLS2ToFPTmfkF8
.youtube.com	TRUE	/	FALSE	1790413715	APISID	D-LfWHhFjPgOmyib/AWkhvGbbe3ud5zhjF
.youtube.com	TRUE	/	TRUE	1790413715	SAPISID	Ik2u3X8MkSt0Qi9Y/AIULJ7J3luewczSA0
.youtube.com	TRUE	/	TRUE	1790413715	__Secure-1PAPISID	Ik2u3X8MkSt0Qi9Y/AIULJ7J3luewczSA0
.youtube.com	TRUE	/	TRUE	1790413715	__Secure-3PAPISID	Ik2u3X8MkSt0Qi9Y/AIULJ7J3luewczSA0
.youtube.com	TRUE	/	TRUE	1790413717	PREF	f4=4000000&f6=40000000&tz=Asia.Calcutta
.youtube.com	TRUE	/	TRUE	1786531289	LOGIN_INFO	AFmmF2swRQIgUi7vRGyMnXAELvYehLLbVJWvF7dxxReoJy-CAdQFZ1QCIQCL0gOVmR-_CIjmM2b2cOG-F-zkU8troZXRmPLQjlsNHg:QUQ3MjNmd3d0T2tjdjREbmUtNl9ZRWdCSU5GUXIxRkc4LVZ5WlUyVG5aX3ppNnBlb3A0NmhGSG1HeHMwWnRSdzhtbkhZNXBFUEtHNFFfOGh1cy0temV4X1RKLTZ4bTdvcm4tSVRGNDJkaDh2SlFfWHRHaW13WDhjdk1aZ2czUDh0a1NoVWItbmp2R2tiS3E0OTE0TU5PUHJfcGRENGhFWHdB
.youtube.com	TRUE	/	FALSE	1790413715	SID	g.a0000ggnLhnJKu_gLFYBExpJiJWJEJU-hqFssT6_n_BI2vKLkhUW3WtIr2KXSphwvPD_iA3wJwACgYKAT4SARQSFQHGX2Miy-Hzr7AJBWQCGTSUnWBWnxoVAUF8yKqehsVWbi7DM3ohv0qgF3030076
.youtube.com	TRUE	/	TRUE	1790413715	__Secure-1PSID	g.a0000ggnLhnJKu_gLFYBExpJiJWJEJU-hqFssT6_n_BI2vKLkhUWO7ltMJJxMAS2U3J1L3V_0AACgYKAQgSARQSFQHGX2Mik8hsLASEV6VT1KutYS47wxoVAUF8yKo7FhOsIZ6AQeFYdIVv6UyF0076
.youtube.com	TRUE	/	TRUE	1790413715	__Secure-3PSID	g.a0000ggnLhnJKu_gLFYBExpJiJWJEJU-hqFssT6_n_BI2vKLkhUWaKoNnMPHuYOMZAZ4iZ0JkgACgYKAcgSARQSFQHGX2MiBlI7iXl6pSSeDA0wS1GePxoVAUF8yKoeAckC0Z62WbqHN3EBMCu80076
.youtube.com	TRUE	/	FALSE	1755853721	ST-tladcw	session_logininfo=AFmmF2swRQIgUi7vRGyMnXAELvYehLLbVJWvF7dxxReoJy-CAdQFZ1QCIQCL0gOVmR-_CIjmM2b2cOG-F-zkU8troZXRmPLQjlsNHg%3AQUQ3MjNmd3d0T2tjdjREbmUtNl9ZRWdCSU5GUXIxRkc4LVZ5WlUyVG5aX3ppNnBlb3A0NmhGSG1HeHMwWnRSdzhtbkhZNXBFUEtHNFFfOGh1cy0temV4X1RKLTZ4bTdvcm4tSVRGNDJkaDh2SlFfWHRHaW13WDhjdk1aZ2czUDh0a1NoVWItbmp2R2tiS3E0OTE0TU5PUHJfcGRENGhFWHdB
.youtube.com	TRUE	/	FALSE	1755853724	ST-3opvp5	session_logininfo=AFmmF2swRQIgUi7vRGyMnXAELvYehLLbVJWvF7dxxReoJy-CAdQFZ1QCIQCL0gOVmR-_CIjmM2b2cOG-F-zkU8troZXRmPLQjlsNHg%3AQUQ3MjNmd3d0T2tjdjREbmUtNl9ZRWdCSU5GUXIxRkc4LVZ5WlUyVG5aX3ppNnBlb3A0NmhGSG1HeHMwWnRSdzhtbkhZNXBFUEtHNFFfOGh1cy0temV4X1RKLTZ4bTdvcm4tSVRGNDJkaDh2SlFfWHRHaW13WDhjdk1aZ2czUDh0a1NoVWItbmp2R2tiS3E0OTE0TU5PUHJfcGRENGhFWHdB
.youtube.com	TRUE	/	FALSE	1755853722	ST-xuwub9	session_logininfo=AFmmF2swRQIgUi7vRGyMnXAELvYehLLbVJWvF7dxxReoJy-CAdQFZ1QCIQCL0gOVmR-_CIjmM2b2cOG-F-zkU8troZXRmPLQjlsNHg%3AQUQ3MjNmd3d0T2tjdjREbmUtNl9ZRWdCSU5GUXIxRkc4LVZ5WlUyVG5aX3ppNnBlb3A0NmhGSG1HeHMwWnRSdzhtbkhZNXBFUEtHNFFfOGh1cy0temV4X1RKLTZ4bTdvcm4tSVRGNDJkaDh2SlFfWHRHaW13WDhjdk1aZ2czUDh0a1NoVWItbmp2R2tiS3E0OTE0TU5PUHJfcGRENGhFWHdB
.youtube.com	TRUE	/	TRUE	1787389719	__Secure-1PSIDTS	sidts-CjEB5H03P4d3_XRWwSKbcC1SmShkTKMchEWz8e0JB8pGYYLzlDkyJ36rtzL9qrn4LiV7EAA
.youtube.com	TRUE	/	TRUE	1787389719	__Secure-3PSIDTS	sidts-CjEB5H03P4d3_XRWwSKbcC1SmShkTKMchEWz8e0JB8pGYYLzlDkyJ36rtzL9qrn4LiV7EAA
.youtube.com	TRUE	/	FALSE	1787389720	SIDCC	AKEyXzWQ1yScKr7VGF0WWJnyKImD-1NWv极hURzFYRfGrPfjYaAQ-UOgn-s37TIG4N_FOzWWY
.youtube.com	TRUE	/	TRUE	1787389720	__Secure-1PSIDCC	AKEyXzUfJo3K0U极er5sGQ_F3ztjTutoFGEYfIFNFZcUQ9SqT8qvCJl96LpOI4NY0y9XApdmJH
.youtube.com	TRUE极	/	TRUE	1787389720	__Secure-3PSIDCC	AKEyXzVHCTQiD3unuY1koQkYX-kO4f-pLPZg-K_ynnBWMlwN0h4m4FbvZ9uuRCMNwbc2L84l
.youtube.com	TRUE	/	TRUE	1771405720	VISITOR_INFO1_LIVE	ULQtIK6wyzY
.youtube.com	TRUE	/	TRUE	1771405720	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgGw%3D%3D
.youtube.com	TRUE	/	TRUE	0	YSC	JFMimREF7H8
.youtube.com	TRUE	/	TRUE	1771405715	__Secure-ROLLOUT_TOKEN	CNbPrM_Ot53OYxCFiJDSia2OAxj_063oiJ6PAw%3D%3D"""

    # Create a temporary cookies file
    cookies_file = "temp_cookies.txt"
    with open(cookies_file, "w") as f:
        f.write(cookies_content)

    opts = {
        "format": "best",
        "addmetadata": True,
        "key": "FFmpegMetadata",
        "prefer_ffmpeg": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "cookiefile": cookies_file,  # ✅ Use the temporary cookies file
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "outtmpl": "%(id)s.mp4",
        "quiet": True,
    }

    try:
        with YoutubeDL(opts) as ytdl:
            data = ytdl.extract_info(video_url, download=True)
    except Exception as e:
        await status.edit(f"**Failed to download.**\n\nError: `{str(e)}`")
        # Clean up cookies file
        if os.path.exists(cookies_file):
            os.remove(cookies_file)
        await asyncio.sleep(60)
        await status.delete()
        return

    file_path = f"{data['id']}.mp4"
    caption = (
        f"❄ **Title:** [{video_title}]({video_url})\n"
        f"💫 **Channel:** {video_channel}\n"
        f"✨ **Searched:** `{query}`\n"
        f"🥀 **Requested by:** {mention}"
    )

    try:
        sent_msg = await (await send_cmd(c, Types.VIDEO))(
            m.chat.id,
            file_path,
            caption,
            parse_mode=PM.MARKDOWN,
            thumb=thumb_file,
            reply_markup=InlineKeyboardMarkup(BUTTON),
        )
        
        # Delete the success message after 60 seconds
        await asyncio.sleep(60)
        await sent_msg.delete()
        
    except Exception as e:
        await status.edit(f"⚠️ Failed to upload.\n\nError: `{str(e)}`")
        # Clean up cookies file
        if os.path.exists(cookies_file):
            os.remove(cookies_file)
        await asyncio.sleep(60)
        await status.delete()
        return

    await status.delete()

    # Cleanup
    for f in (thumb_file, file_path, cookies_file):
        if f and os.path.exists(f):
            os.remove(f)


__PLUGIN__ = "yt_video"

_DISABLE_CMDS_ = ["yt", "video"]

__HELP__ = """
**YouTube Video Downloader** 🎥

• /yt <query>  
   Search & download a YouTube video  

• /video <query>  
   Same as `/yt`
"""
