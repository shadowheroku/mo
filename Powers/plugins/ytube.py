import os
import tempfile
from pyrogram import filters
from Powers.bot_class import Gojo
import yt_dlp

# ========================
# EMBEDDED COOKIES
# ========================
YOUTUBE_COOKIES = """# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	FALSE	1789394960	HSID	A6ZfyYUep0Np9MQw1
.youtube.com	TRUE	/	TRUE	1789394960	SSID	Agye2vfnm-dkrucAt
.youtube.com	TRUE	/	FALSE	1789394960	APISID	kz7E2afizJqVhEVm/AO-71rWNJbOrr03lY
.youtube.com	TRUE	/	TRUE	1789394960	SAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-1PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PAPISID	7fJ-lvyh4STWCBvz/Adsi-bKLNu39ch5Wh
.youtube.com	TRUE	/	TRUE	1777881466	LOGIN_INFO	AFmmF2swRAIgDG6w06DO6jzGmopZi4YYYaDhOoEY4gB5zstRy3l5-zkCIHcUr0KOk-7uvH446znpbL79FTkyI348bB0GXULReZdc:QUQ3MjNmeVpIUXUzSXhOV0l1aHRNMFV2dVE0ckJjRG15VnFPVnNRWEh3UUpGQnpyX1RNZDZtRkduZ0pxclducjMzOVEwcWI2dWJPY3BnSnNSd2U0NHRmQlJJYjljY29hcV9iemhKblhUVDN0NGdIQzdOcUVWZmd6M3NtQ20wU1hoUUtsVS1zWENUcDNuU2E2YkM1dU9rREI2NWVDbXB3OVhR
.youtube.com	TRUE	/	FALSE	1779724239	_ga	GA1.1.1034053585.1745164239
.youtube.com	TRUE	/	TRUE	1789855256	PREF	f4=4000000&f6=40000000&tz=Asia.Calcutta&f7=150&repeat=NONE&autoplay=true
.youtube.com	TRUE	/	FALSE	1779724472	_ga_VCGEPY40VB	GS1.1.1745164238.1.1.1745164471.60.0.0
.youtube.com	TRUE	/	FALSE	1789394960	SID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsV1dE2o6KB33rpb_7g4EETTwACgYKASgSARESFQHGX2Miuat42fzbV_FlDrWm7uO5uhoVAUF8yKpdsOfPj1S0UexoyV_vrSKm0076
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-1PSID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsVXiz1bbBKw2CtB1qgIa3yMwACgYKATsSARESFQHGX2Mi4Bb47FQb7KtwstoGlnPu5BoVAUF8yKospSKEGprHVlU1MWg9X8OY0076
.youtube.com	TRUE	/	TRUE	1789394960	__Secure-3PSID	g.a0000AjzvmDVdcaAaK1FXG6J6NdEurHHeyqSwjCWLIYz3KFegHsVD9L5Es1hvyFBrrSUHltu1AACgYKAeASARESFQHGX2Mi3-d_L7JlUeEUkEoBBNB7ixoVAUF8yKqmRh47rBnVkvAEjDwFQBOi0076
.youtube.com	TRUE	/	TRUE	1771056471	NID	525=R5THx5Igk50aIGTP4p4AHjBqtGdzdqbby6beJCLl2aCzCnWTKX2hNFTudc-awHTuze4VSbbEU2FuttpqoJGq6YwjtGb0a-YEKwDU35HAX11v6nmOBhPzTmnGxoHrhaU3Nyb6Xp1t7jwPSAMJ0K2T6SMcAsZTiORvCEn9duMNraNphZjktCkmpn7Mj1XX8ZtP2XukeX-2lEPefJal-Wi5waY5QyI6kww
.youtube.com	TRUE	/	TRUE	1786831258	__Secure-1PSIDTS	sidts-CjEB5H03PwnFKALCoYQL_pSvZ10mPFmFAifOLflhgblxUEzLNcXpmOKPN6y6rfO2ij2XEAA
.youtube.com	TRUE	/	TRUE	1786831258	__Secure-3PSIDTS	sidts-CjEB5H03PwnFKALCoYQL_pSvZ10mPFmFAifOLflhgblxUEzLNcXpmOKPN6y6rfO2ij2XEAA
.youtube.com	TRUE	/	FALSE	1786831259	SIDCC	AKEyXzXlD6OwP6c2sHGYZi14_C4iSRn5c1GNgKkCqvgvLabk99-Fqb5YgFWioBEqHTn0nDtGVy4
.youtube.com	TRUE	/	TRUE	1786831259	__Secure-1PSIDCC	AKEyXzUeTujLwbJLVsJrWhGWyixxsNnenwoYvNW-T882zog8Fb9-QsoKKV6CDRrZtfbtdsadlMY
.youtube.com	TRUE	/	TRUE	1786831259	__Secure-3PSIDCC	AKEyXzXYJCas3G6a8ryvg18O7CiT5Dbc-0ketIUsMpMN0pA993n8djvns-dx9HpjsAZ26wT9mlM
.youtube.com	TRUE	/	TRUE	1770847259	VISITOR_INFO1_LIVE	PXh3lLWceIU
.youtube.com	TRUE	/	TRUE	1770847259	VISITOR_PRIVACY_METADATA	CgJJThIEGgAgKQ%3D%3D
.youtube.com	TRUE	/	TRUE	1770795819	__Secure-ROLLOUT_TOKEN	CPWMs-mStNuj7gEQtImonuWvjAMYyfnJ4qiMjwM%3D
.youtube.com	TRUE	/	TRUE	0	YSC	FnjdGE5OoDM
"""
# ========================
# BOT COMMAND
# ========================
@Gojo.on_message(filters.command("yt", prefixes="."))
async def youtube_download(c, m):
    if len(m.command) < 2:
        return await m.reply_text("⚠️ Please provide a YouTube link.")

    url = m.command[1]
    status = await m.reply_text("📥 Downloading YouTube video...")

    try:
        # Write cookies to a temporary file in memory
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt") as f:
            f.write(YOUTUBE_COOKIES)
            cookies_path = f.name

        # yt-dlp options for max speed
        ydl_opts = {
            "cookiefile": cookies_path,
            "format": "bestvideo+bestaudio/best",  # Best quality
            "merge_output_format": "mp4",          # Merge into MP4
            "noplaylist": True,                    # Single video only
            "quiet": True,                         # Less console output
            "outtmpl": "%(title)s.%(ext)s"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        await m.reply_video(video=file_path, caption=f"🎬 {info.get('title')}")
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Failed:\n`{e}`")

    finally:
        # Cleanup
        try:
            os.remove(cookies_path)
        except:
            pass


__PLUGIN__ = "YouTube Downloader"
__HELP__ = """
Send a YouTube link and I’ll download it using your embedded login cookies.
"""
