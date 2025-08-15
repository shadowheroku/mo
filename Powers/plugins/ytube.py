import re
import asyncio
import yt_dlp
from pyrogram import filters
from Powers.bot_class import Gojo
import tempfile

# Minimal cookie set directly in code
YOUTUBE_COOKIES_CONTENT = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1789394960	HSID	A6ZfyYUep0Np9MQw1
.youtube.com	TRUE	/	TRUE	1789394960	SSID	Agye2vfnm-dkrucAt
.youtube.com	TRUE	/	FALSE	1789394960	APISID	kz7E2afizJqVhEVm/AO-71rWNJbOrr03lY
.youtube.com	TRUE	/	TRUE	1789394960	SAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	SID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsV1dE2o6KB33rpb_7g4EETTwACgYKASgSARESFQHGX2Miuat42fzbV_FlDrWm7uO5uhoVAUF8yKpdsOfPj1S0UexoyV_vrSKm0076
"""

# Save cookies to a temp file at runtime
def get_cookie_file():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(YOUTUBE_COOKIES_CONTENT.encode())
    tmp.flush()
    return tmp.name

# Regex for YouTube URLs
YOUTUBE_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+)"
)

async def download_youtube(url):
    cookie_file = get_cookie_file()
    ydl_opts = {
        "cookiefile": cookie_file,
        "format": "best",
        "outtmpl": "%(title)s.%(ext)s",
        "quiet": True,
    }
    loop = asyncio.get_event_loop()
    def _run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("url"), info.get("title")
    return await loop.run_in_executor(None, _run)

@Gojo.on_message(filters.regex(YOUTUBE_REGEX))
async def youtube_downloader(c, m):
    match = YOUTUBE_REGEX.search(m.text or "")
    if not match:
        return
    url = match.group(1)
    status = await m.reply_text("📥 Fetching YouTube video...")
    try:
        video_url, title = await download_youtube(url)
        await m.reply_video(video=video_url, caption=f"🎬 **{title}**\n🔗 {url}")
        await status.delete()
    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")

__PLUGIN__ = "YouTube Downloader"
__HELP__ = """
Send a YouTube link and I’ll download it using your embedded login cookies.
"""
