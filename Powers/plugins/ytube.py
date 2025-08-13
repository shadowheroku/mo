import os
import re
import time
import tempfile
import wget
from yt_dlp import YoutubeDL
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Your raw cookies pasted here
YOUTUBE_COOKIES = """# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1789394960	HSID	A6ZfyYUep0Np9MQw1
.youtube.com	TRUE	/	TRUE	1789394960	SSID	Agye2vfnm-dkrucAt
.youtube.com	TRUE	/	FALSE	1789394960	APISID	kz7E2afizJqVhEVm/AO-71rWNJbOrr03lY
.youtube.com	TRUE	/	TRUE	1789394960	SAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-1PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1777881466	LOGIN_INFO	AFmmF2swRAIgDG6w06DO6jzGmopZi4YYYaDhOoEY4gB5zstRy3l5-zkCIHcUr0KOk-7uvH446znpbL79FTkyI348bB0GXULReZdc:QUQ3MjNmeVpIUXUzSXhOV0l1aHRNMFV2dVE0ckJjRG15VnFPVnNRWEh3UUpGQnpyX1RNZDZtRkduZ0pxclducjMzOVEwcWI2dWJPY3BnSnNSd2U0NHRmQlJJYjljY29hcV9iemhKblhUVDN0NGdIQzdOcUVWZmd6M3NtQ20wU1hoUUtsVS1zWENUcDNuU2E2YkM1dU9rREI2NWVDbXB3OVhR
.youtube.com	TRUE	/	FALSE	1779724239	_ga	GA1.1.1034053585.1745164239
.youtube.com	TRUE	/	TRUE	1789663650	PREF	f4=4000000&f6=40000000&tz=Asia.Calcutta&f7=150&repeat=NONE&autoplay=true
.youtube.com	TRUE	/	FALSE	1779724472	_ga_VCGEPY40VB	GS1.1.1745164238.1.1.1745164471.60.0.0
.youtube.com	TRUE	/	FALSE	1789394960	SID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsV1dE2o6KB33rpb_7g4EETTwACgYKASgSARESFQHGX2Miuat42fzbV_FlDrWm7uO5uhoVAUF8yKpdsOfPj1S0UexoyV_vrSKm0076
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-1PSID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsVXiz1bbBKw2CtB1qgIa3yMwACgYKATsSARESFQHGX2Mi4Bb47FQb7KtwstoGlnPu5BoVAUF8yKospSKEGprHVlU1MWg9X8OY0076
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PSID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsVD9L5Es1hvyFBrrSUHltu1AACgYKAeASARESFQHGX2Mi3-d_L7JlUeEUkEoBBNB7ixoVAUF8yKqmRh47rBnVkvAEjDwFQBOi0076
.youtube.com	TRUE	/	TRUE	1755104250	CONSISTENCY	AKreu9u6y9wMKQxS36AddNUQnO_A_Ji8iUBznXoJRZfmhLqSR4wznXPTK-sjZvwEsLYIgwAX8RMPQEb8L8thCMiNHEg5UTsE84DnHOJ0WrSzjP9MbqE5yJ2nNqj6RCEGkOAgUvbMIgQao-5M1qmC5aH3
.youtube.com	TRUE	/	TRUE	1770914851	NID	525=FiuPHv4oT9_PoH-OX2BVcjJM6JkLnfzyZeamY6iTPu_wrO_vSzMRp6rctM3_PZsJ_H0AcU31EsdtE2qPtwyc8okVQzBK01EV_fLkeIxdxznMJx1mo1iz-Bf392ntybskV_KNnkaVceUJZrS3AHVJ4mYjG3yCcKsE2lDsZWZQnMrB6ZkHk_HL4mQ6VuIqXcBmPWE9ozfc3YgcLpGLTUqR8S0XHQU3rgg
.youtube.com	TRUE	/	TRUE	1786639653	__Secure-1PSIDTS	sidts-CjEB5H03Pym5VB0yk-lhUcNllQ2TBVEkBE9aupm4S3YtXudIh8D7_cO__7lgwWZSmOt3EAA
.youtube.com	TRUE	/	TRUE	1786639653	__Secure-3PSIDTS	sidts-CjEB5H03Pym5VB0yk-lhUcNllQ2TBVEkBE9aupm4S3YtXudIh8D7_cO__7lgwWZSmOt3EAA
.youtube.com	TRUE	/	FALSE	1786639654	SIDCC	AKEyXzWRiBQUuUGhFjAmPQ9ZhA263WMPAx13CppF0Z9SwRHQPXgF-hc1zY0Ko5nqqI_nBxneTGs
.youtube.com	TRUE	/	TRUE	1786639654	__Secure-1PSIDCC	AKEyXzULMeYwnSxB-cU27TiFSRqgy0pwmymtM5W84wGwSJ9foj4DTYrawABESxhhIU-Rsvk1Tno
.youtube.com	TRUE	/	TRUE	1786639654	__Secure-3PSIDCC	AKEyXzXG1B63d3j3C2_Nq3xrM3CZIxg4yQLB4xK0txA3MApixBfqWsugCmuYSWiOGtqKGeFkitM
.youtube.com	TRUE	/	TRUE	1770655654	VISITOR_INFO1_LIVE	PXh3lLWceIU
.youtube.com	TRUE	/	TRUE	1770655654	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgKQ%3D%3D
.youtube.com	TRUE	/	TRUE	0	YSC	faZFj2ZfkW8
.youtube.com	TRUE	/	TRUE	1770655647	__Secure-ROLLOUT_TOKEN	CPWMs-mStNuj7gEQtImonuWvjAMY8fL4zJ6IjwM%3D
"""

# YouTube link pattern
YT_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+"

@Gojo.on_message(filters.regex(YT_REGEX))
async def yt_auto_download(c: Gojo, m: Message):
    url = re.search(YT_REGEX, m.text).group(0)
    user_mention = m.from_user.mention

    status = await m.reply_text("🔍 **Fetching YouTube video...**")

    try:
        # Save cookies to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as cookie_file:
            cookie_file.write(YOUTUBE_COOKIES.encode("utf-8"))
            cookie_path = cookie_file.name

        # Thumbnail fetching
        video_id = None
        if "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]
        elif "youtube.com" in url and "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        thumb_path = None
        if video_id:
            thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            thumb_path = wget.download(thumb_url)

        # yt-dlp options
        opts = {
            "format": "best",
            "addmetadata": True,
            "key": "FFmpegMetadata",
            "prefer_ffmpeg": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "cookiefile": cookie_path,
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            "outtmpl": "%(id)s.mp4",
            "quiet": True,
        }

        with YoutubeDL(opts) as ytdl:
            info = ytdl.extract_info(url, download=True)

        file_path = f"{info['id']}.mp4"
        caption = (
            f"🎬 **Title:** [{info['title']}]({url})\n"
            f"📺 **Channel:** {info.get('uploader', 'Unknown')}\n"
            f"🙋 **Requested by:** {user_mention}\n"
            f"📥 **Downloaded by:** {c.me.mention}"
        )

        await c.send_video(
            m.chat.id,
            video=open(file_path, "rb"),
            duration=int(info["duration"]),
            file_name=str(info["title"]),
            thumb=thumb_path if thumb_path else None,
            caption=caption,
            supports_streaming=True
        )

    except Exception as e:
        await status.edit(f"❌ **Failed to download video:** `{e}`")
        return
    finally:
        if os.path.exists(cookie_path):
            os.remove(cookie_path)

    await status.delete()

    # Cleanup
    for file in [file_path, thumb_path]:
        if file and os.path.exists(file):
            os.remove(file)

__PLUGIN__ = "youtube"
__HELP__ = """
**🎥 Auto YouTube Video Downloader**
• Just send any YouTube link in chat — it will be downloaded and sent automatically.
"""
