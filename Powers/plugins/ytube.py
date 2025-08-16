import os
import re
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
COOKIES_FILE = "youtube_cookies.txt"

# Write embedded YouTube cookies to a file
COOKIES_TEXT = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	FALSE	1789394960	HSID	A6ZfyYUep0Np9MQw1
.youtube.com	TRUE	/	TRUE	1789394960	SSID	Agye2vfnm-dkrucAt
.youtube.com	TRUE	/	FALSE	1789394960	APISID	kz7E2afizJqVhEVm/AO-71rWNJbOrr03lY
.youtube.com	TRUE	/	TRUE	1789394960	SAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-1PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1777881466	LOGIN_INFO	AFmmF2swRAIgDG6w06DO6jzGmopZi4YYYaDhOoEY4gB5zstRy3l5-zkCIHcUr0KOk-7uvH446znpbL79FTkyI348bB0GXULReZdc:QUQ3MjNmeVpIUXUzSXhOV0l1aHRNMFV2dVE0ckJjRG15VnFPVnNRWEh3UUpGQnpyX1RNZDZtRkduZ0pxclducjMzOVEwcWI2dWJPY3BnSnNSd2U0NHRmQlJJYjljY29hcV9iemhKblhUVDN0NGdIQzdOcUVWZmd6M3NtQ20wU1hoUUtsVS1zWENUcDNuU2E2YkM1dU9rREI2NWVDbXB3OVhR
"""  # Add more cookies if needed

with open(COOKIES_FILE, "w", encoding="utf-8") as f:
    f.write(COOKIES_TEXT.strip() + "\n")

# Regex for YouTube URLs
YOUTUBE_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?youtube\.com\/watch\?v=[\w\-]+|https?:\/\/youtu\.be\/[\w\-]+)"
)

@Gojo.on_message(filters.regex(YOUTUBE_REGEX))
async def youtube_downloader(c, m):
    match = YOUTUBE_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    temp_file = "youtube_dl.%(ext)s"
    status = await m.reply_text("📥 Downloading YouTube video...")

    try:
        ydl_opts = {
            "outtmpl": temp_file,
            "quiet": True,
            "no_warnings": True,
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
            "retries": 3,
            "ignoreerrors": False,
            "cookiefile": COOKIES_FILE,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.youtube.com/",
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("No downloadable content found")

            file_path = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4").lower()

        caption = f"▶️ **Source:** [YouTube]({url})\n🤖 **Via:** @{c.me.username}"

        if ext in ["mp4", "webm", "mov"]:
            await m.reply_video(video=file_path, caption=caption)
        else:
            await m.reply_document(document=file_path, caption=caption)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"⚠️ Failed: {str(e)}")
    finally:
        for f in os.listdir():
            if f.startswith("youtube_dl."):
                try:
                    os.remove(f)
                except:
                    pass

# Metadata
__PLUGIN__ = "YouTube Downloader (With Cookies)"
__HELP__ = """
▶️ Download YouTube videos using embedded cookies:

• Send any YouTube link
• Works for public, age-restricted, and private videos (if your account has access)
• Downloads in best video+audio quality
"""
