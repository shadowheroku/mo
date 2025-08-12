import speedtest
import humanize
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo
from Powers.utils.custom_filters import command

# Function to run the speed test
def run_speedtest():
    st = speedtest.Speedtest()
    st.get_best_server()
    download_speed = st.download()
    upload_speed = st.upload()
    ping_result = st.results.ping

    return download_speed, upload_speed, ping_result

@Gojo.on_message(filters.command("speedtest"))
async def speedtest_handler(client, message: Message):
    msg = await message.reply_text("🚀 Running speed test... Please wait.")

    try:
        download_speed, upload_speed, ping_result = run_speedtest()

        # Convert speeds to human-readable format
        download_human = humanize.naturalsize(download_speed, binary=True)
        upload_human = humanize.naturalsize(upload_speed, binary=True)

        result_text = (
            "📡 **Speedtest Results**\n\n"
            f"💨 **Download:** `{download_human}/s`\n"
            f"📤 **Upload:** `{upload_human}/s`\n"
            f"📶 **Ping:** `{ping_result} ms`\n"
        )

        await msg.edit_text(result_text)

    except Exception as e:
        await msg.edit_text(f"❌ Error running speedtest:\n`{e}`")

__PLUGIN__ = "Speedtest"
__HELP__ = """
📡 **Speedtest**

`/speedtest` — Runs an internet speed test and shows download, upload, and ping.

Example:
`/speedtest`
"""
