import os
import re
import yt_dlp
import asyncio
import requests
from pyrogram import filters
from Powers.bot_class import Gojo

# ===== CONFIG =====
COOKIES_TEXT = """# Netscape HTTP Cookie File
# Paste your Pinterest cookies below
.pinterest.com	TRUE	/	TRUE	1782670886	_auth	1
.pinterest.com	TRUE	/	FALSE	1777902651	_b	"AYZ5sDiC74hIaaZcWcK4t5uLyuRCzisB3PpzvvSAMOsthhRKL2tqk9HKijTtwW59ee4="
in.pinterest.com	FALSE	/	TRUE	1774878652	csrftoken	971f340896d23f92af410c88f175424e
.pinterest.com	TRUE	/	TRUE	1779966933	ar_debug	1
.pinterest.com	TRUE	/	TRUE	1775852828	_pinterest_cm	"TWc9PSZmQ0VHWTZ0WVB5S2NpK0FObjZVWTFGcVNYVWtwRGxYeWsxRmJGb0tpMm1aanZCYTB6NGhhbm9qNlMzREkyNUJBK2RqeUJTRXQyeGZ4cEVzeGhwakY3dWJkZjhvaTlBUkpCT3BpWFNUM0xENk1GRmhoZzVTN2JxQ0tERFJ5Z3F4cHpzZjkvNDh5LytCdnE0MEJ0VXpPYkxyVU9PekVYWmlvckhpZ2R3V0tzQU4rZFlYSXVNc1RyT1pkbjk2TjI1QjYmaWdRWTc5NGRjZXErTHQ3cXFaZFc1MnpxVHpnPQ=="
in.pinterest.com	FALSE	/	TRUE	1780567637	ar_debug	1
.pinterest.com	TRUE	/	TRUE	1782670886	_pinterest_sess	TWc9PSZQYmIvVkRMeTZtY0tVMFBuOFVVa3pGcjg1VWtmbTIvT2M5aS9xNlVSbit5WWpJYkpKdDNxbmVxSEZrZi9mUDY2ZGhEelJMZUc2ZHorRlFRTGtYeXBtQk0rRlVWUXJ1djlVRnVZT2hkdWJkdGhiMlJuZWIzNEVsS3NGYlFHY2JMeTlPeG1xZlI3K2JtNmF5V0hndVZoMGJVUHlWa0Nyd1J2eHJScWxtVldDbkJhMTJSSnRjQmR5a3FVVWdWb0NRbmZHK2U2Y05oRG5Lc3N5Zm82bThiWnV1YXlLcTZObDRaTUZpZEhVODlxbFljK2RhZkw0L29HRWU1bUlrNEViei8xN1VnaXJvaE5iclJIbmZzVXE1cys4bnhkcFVvWk42dlA5aDh6c0pVSllxWkVNUnBNQjNpTWRaWjlNZWszczNFaEN1TGtCY2tmVDlIdEplcVYvMEg3V3V5eXJJa0tzUDhxVzExWVFQVCswZFplN1BmdFNsRGtmMzEyRmF4S0liMm43V0ppQVNyL3Q4bXZxei82SHlUQi9DR29KdzczVm9OMDVIbGRaZ0czdUVGL0JvQ1U0WnNZM3E1azZVck55YXZ0OHV3NzZYSTIzOVVqR1NxMW51UVVMR0F4djhPZFdNTjFNYWtEUHZnMkw2bzFBVmxUTUlsd2p5T1JORUhSRUlSZWdFYVdldm9CZFdVN1plaHI4ejRxaXN1SHNiSk5yWUcvOC9VWkwxaEpkRmJMUG9zNElJa3pEQUttUUlYUS9USnFsVE10MlVjck5KT0gyTWZCVWFEN0hJcm9MRTVqL050R2lwaURsckFhWWZ1ZDJSY2FWbi9rTHA2dlJZdnR0L011SlpuRThEQ2FaZ3ZwUlRrMnhhQktkRGVic0VLV2JpbHUwOHZ2WTdQUGtTdlJ6RWtDaDVDZ3RXbGhseFYyWVVsaElBLytMOE9DdVVJT3RNQnczNnhWcWdYN3V2S2NneDBiVDJJWE40SWE3djd5MWxlQktLUUY5VWFFcXZqNFJwa2srREg5UG8xM2diTEFQTGI0aS9sekJ6V0RNVFJoc1pVZDVBT2xUZmlyNjV5eTVCVmdBa1Z1aXgyYWlIcnJhQkRPUmR5L1VQY0FDaTJPUVlJUG1pWnZqWnNiMENsb3kxSlFJdEhoQlJ4U0R6ZzNPd1BNWWZVbjc0SVBua01RVTA4cnEzNUNXTFNXbnQrQWU0VTkwTDdEWlNFQ09aem9hekhpTDJsV0hCaW50R0lEYzVxR0FJcmxiUGsySkxPL1Y0dFpkN25sY040Z0pYeXNlcGxCb1htcHljUU1DbzA4elNZTEIvQ1ArSmNhcTVmR3BGYWg3WTloeDFvU2wwcUVWNEdDeW9YSHllMklIcDhWYjZHQ0FMRm1ySDY1SFB0UkdwOUR5b0NvZ3JyU1RKRVIwWm1PNkM3bjRRcDNSN2pDNHBaUmVNT2d2N2RoVlU1SWtSZ1hzS2lUeGxtNEtRYm1GSC9yUU9CZ0o3Y2V1SDE1cWc3MW1GV1QydWtJUlVmd1duczhpMlR0elQxanFqT0Jhc2g0dGNiZWthUkd3RE93czRJYm9uaWhHeUs3Ni96YjFsK20yQzlxT1UzRnBhQ0d1MVBuRFIxdUlVZkhSclpyLzEwNlI0cUR3TUNXMlR0Z1h0ZWVRYWhPeXV6UWQ4MGlidm02NHAra2xhTkVIZHFmY2NGeml5c1h6cndJSzNHdjIzUSs5ZEFTUzR0aVk5a1EvZkJCRkxXRUhkRFUyZkpaSkd1V2VLNFpCaDd2L1JRd2dBNGMmT3R6eS95N2VQSkE4OFBIWGw1Wi9ZTzZDSGxjPQ==
"""

COOKIES_FILE = "pinterest_cookies.txt"
with open(COOKIES_FILE, "w", encoding="utf-8") as f:
    f.write(COOKIES_TEXT.strip() + "\n")


PINTEREST_REGEX = re.compile(
    r"(https?:\/\/(?:www\.)?(?:pin\.it\/[A-Za-z0-9]+|pinterest\.com\/pin\/\d+))"
)

def resolve_pinterest_url(short_url: str) -> str:
    """Resolve pin.it short URL to real Pinterest URL."""
    try:
        r = requests.head(short_url, allow_redirects=True, timeout=10)
        return r.url
    except Exception:
        return short_url

@Gojo.on_message(filters.regex(PINTEREST_REGEX))
async def pinterest_downloader(c, m):
    match = PINTEREST_REGEX.search(m.text or "")
    if not match:
        return

    url = match.group(1)
    if "pin.it" in url:
        url = resolve_pinterest_url(url)

    temp_file = "pinterest_dl.%(ext)s"
    status = await m.reply_text("📥 Downloading Pinterest content...")

    try:
        ydl_opts = {
            "outtmpl": temp_file,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": COOKIES_FILE,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.pinterest.com/",
            },
            # Critical format selection update:
            "format": "(bestvideo[vcodec^=avc1][height<=1080][ext=mp4]/bestvideo[ext=mp4]/bestvideo)+(bestaudio[ext=m4a]/bestaudio)/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "retries": 3,
            "ignoreerrors": False,
            "extractor_args": {
                "pinterest": {
                    "skip": ["dash"],  # Skip problematic formats
                }
            },
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise Exception("No downloadable content found")
            
            file_path = ydl.prepare_filename(info)
            ext = info.get("ext", "mp4").lower()

        caption = f"📌 **Source:** [Original Pin]({url})\n🤖 **Via:** @{c.me.username}"

        if ext in ["mp4", "webm", "mov"]:
            await m.reply_video(video=file_path, caption=caption)
        elif ext in ["jpg", "jpeg", "png", "webp"]:
            await m.reply_photo(photo=file_path, caption=caption)
        else:
            await m.reply_document(document=file_path, caption=caption)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"I can only downloads video posts of pintrest")
        return
    finally:
        # Cleanup
        for f in os.listdir():
            if f.startswith("pinterest_dl."):
                try:
                    os.remove(f)
                except:
                    pass
# Updated plugin metadata
__PLUGIN__ = "Pinterest Video Downloader"
__HELP__ = """
🎥 Download videos from Pinterest:

• Send me any Pinterest video link
• Supports MP4, WebM, MOV formats
• Works with private videos (needs valid cookies)

⚠️ I only download videos - image pins will be rejected!
"""
