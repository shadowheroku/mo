import json
import subprocess
from pyrogram import filters
from pyrogram.types import Message
from Powers.bot_class import Gojo

# Function to run the CLI speedtest
def run_speedtest_cli():
    try:
        # Run Ookla's official CLI with JSON output
        result = subprocess.run(
            ["speedtest", "--accept-license", "--accept-gdpr", "-f", "json"],
            capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr.strip() or str(e)}

@Gojo.on_message(filters.command("speedtest"))
async def speedtest_handler(client, message: Message):
    msg = await message.reply_text("🚀 Running speed test... Please wait...")

    data = run_speedtest_cli()

    if "error" in data:
        await msg.edit_text(f"❌ Error running speedtest:\n`{data['error']}`")
        return

    download = round(data["download"]["bandwidth"] * 8 / 1_000_000, 2)  # Mbps
    upload = round(data["upload"]["bandwidth"] * 8 / 1_000_000, 2)      # Mbps
    ping = round(data["ping"]["latency"], 2)                            # ms
    isp = data.get("isp", "Unknown ISP")
    server_name = data["server"]["name"]
    country = data["server"]["country"]

    result_text = (
        "📡 **Speedtest Results**\n\n"
        f"💨 **Download:** `{download} Mbps`\n"
        f"📤 **Upload:** `{upload} Mbps`\n"
        f"📶 **Ping:** `{ping} ms`\n"
        f"🏢 **ISP:** `{isp}`\n"
        f"🌐 **Server:** `{server_name}, {country}`\n"
    )

    await msg.edit_text(result_text)

__PLUGIN__ = "Speedtest"
__HELP__ = """
📡 **Speedtest (CLI Version)**

`/speedtest` — Runs an internet speed test using Ookla's official CLI and shows download, upload, ping, ISP, and server.

⚠️ Requires Ookla's speedtest CLI to be installed:
• Debian/Ubuntu:
`sudo apt install curl -y && curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash && sudo apt install speedtest`
"""
