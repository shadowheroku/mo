import sys
from platform import system

from Powers import LOGGER
from Powers.bot_class import Gojo


def setup_uvloop():
    """Try to setup uvloop if available and not on Windows."""
    if system() == "Windows":
        LOGGER.info("Windows system detected, skipping uvloop setup.")
        return

    try:
        import uvloop
        uvloop.install()
        LOGGER.info("uvloop installed and enabled successfully.")
    except ImportError:
        LOGGER.warning("uvloop not installed. Running without it.")
    except Exception as e:
        LOGGER.error(f"Failed to enable uvloop: {e}")


def main():
    setup_uvloop()
    try:
        Gojo().run()
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped manually (KeyboardInterrupt).")
        sys.exit(0)
    except Exception as e:
        LOGGER.error(f"Bot crashed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
