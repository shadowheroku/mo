import logging
import sys
import asyncio
from Powers.bot_class import Gojo

# ─── LOGGER ───
logger = logging.getLogger("Gojo_Satoru")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# ─── MAIN ───
async def main():
    bot = Gojo()
    try:
        await bot.start()
        logger.info("✅ Gojo bot started successfully.")
        await idle()  # Keeps bot running
    except Exception as e:
        logger.error(f"❌ Bot crashed with error: {e}", exc_info=True)
    finally:
        await bot.stop()
        logger.info("🛑 Gojo bot stopped.")

if __name__ == "__main__":
    from pyrogram import idle

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
