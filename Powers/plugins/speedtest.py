import speedtest
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo


def run_speedtest():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download()  # bits/sec
    upload_speed = st.upload()      # bits/sec
    ping_result = st.results.ping
    server_name = st.results.server.get("name", "Unknown")
    country = st.results.server.get("country", "Unknown")
    isp = st.results.client.get("isp", "Unknown ISP")

    return download_speed, upload_speed, ping_result, server_name, country, isp


@Gojo.on_message(filters.command("speedtest"))
async def speedtest_handler(client, message: Message):
    msg = await message.reply_text("🚀 Running speed test... Please wait...")

    try:
        download_speed, upload_speed, ping_result, server_name, country, isp = run_speedtest()

        # Convert to Mbps
        download_mbps = round(download_speed / 1_000_000, 2)
        upload_mbps = round(upload_speed / 1_000_000, 2)

        result_text = (
            "📡 **Speedtest Results**\n\n"
            f"💨 **Download:** `{download_mbps} Mbps`\n"
            f"📤 **Upload:** `{upload_mbps} Mbps`\n"
            f"📶 **Ping:** `{ping_result} ms`\n"
            f"🏢 **ISP:** `{isp}`\n"
            f"🌐 **Server:** `{server_name}, {country}`\n"
        )

        await msg.edit_text(result_text)

    except Exception as e:
        await msg.edit_text(f"❌ Error running speedtest:\n`{e}`")


__PLUGIN__ = "Speedtest"
__HELP__ = """
📡 **Speedtest (speedtest-cli)**

`/speedtest` — Runs an internet speed test and shows download, upload, ping, ISP, and server info.

⚠️ Requires `speedtest-cli`:
```bash
pip install speedtest-cli
"""
