from os import getcwd, path

from prettyconf import Configuration
from prettyconf.loaders import EnvFile, Environment

env_file = f"{getcwd()}/.env"
config = Configuration(loaders=[Environment(), EnvFile(filename=env_file)])
is_env = path.isfile(env_file)


class Config:
    """Config class for variables."""

    LOGGER = True
    BOT_TOKEN = config("BOT_TOKEN", default=None)
    API_ID = int(config("API_ID", default="123"))
    API_HASH = config("API_HASH", default=None)
    OWNER_ID = int(config("OWNER_ID", default=1344569458))
    MESSAGE_DUMP = int(config("MESSAGE_DUMP", default="0"))  # if not given owner id will be msg dump :)
    DEV_USERS = [
        int(i)
        for i in config(
            "DEV_USERS",
            default="",
        ).split(None)
    ]
    SUDO_USERS = [
        int(i)
        for i in config(
            "SUDO_USERS",
            default="",
        ).split(None)
    ]
    WHITELIST_USERS = [
        int(i)
        for i in config(
            "WHITELIST_USERS",
            default=""
        ).split(None)
    ]
    # CHROME_BIN = config("CHROME_BIN", "/app/.apt/usr/bin/google-chrome")
    # CHROME_DRIVER = config("CHROME_DRIVER", default="/app/.chromedriver/bin/chromedriver")
    GENIUS_API_TOKEN = config("GENIUS_API", default=None)
    # AuDD_API = config("AuDD_API",default=None)
    RMBG_API = config("RMBG_API", default=None)
    DB_URI = config("DB_URI", default=None)
    DB_NAME = config("DB_NAME", default="gojo_satarou")
    BDB_URI = config("BDB_URI", default=None)
    NO_LOAD = config("NO_LOAD", default="").split()
    PREFIX_HANDLER = config("PREFIX_HANDLER", default="/").split()
    SUPPORT_GROUP = config("SUPPORT_GROUP", default="gojo_bots_network")
    SUPPORT_CHANNEL = config("SUPPORT_CHANNEL", default="gojo_bots_network")
    WORKERS = int(config("WORKERS", default=16))
    TIME_ZONE = config("TIME_ZONE", default='Asia/Kolkata')
    BOT_USERNAME = ""  # Leave it as it is
    BOT_ID = ""  # Leave it as it is
    BOT_NAME = ""  # Leave it as it is


class Development:
    """Development class for variables."""

    # Fill in these vars if you want to use Traditional method of deploying
    LOGGER = True
    BOT_TOKEN = "7847667702:AAF9rw9I-pf7gJsNxDlFOhKD_S23tg3Fs6I"
    API_ID = 23212132  # Your APP_ID from Telegram
    API_HASH = "1c17efa86bdef8f806ed70e81b473c20"  # Your APP_HASH from Telegram
    OWNER_ID = 8429156335  # Your telegram user id defult to mine
    MESSAGE_DUMP = -1002800777153  # Your Private Group ID for logs if not passed your owner id will be msg dump
    DEV_USERS = [8473262774]
    SUDO_USERS = [7732844436]
    WHITELIST_USERS = []
    DB_URI = "mongodb+srv://ryumasgod:ryumasgod@cluster0.ojfkovp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"  # Your mongo DB URI
    DB_NAME = "MONICDB"  # Your DB name
    NO_LOAD = []
    GENIUS_API_TOKEN = "X-ke3wy7wtBF1zlX1NZZF8zPSu7redVunzR2_gkCs6fnQBTchX472V-YYERdFi9-"
    RMBG_API = "mHgMmpSvffqE8Ap5mUeDrqWt"
    PREFIX_HANDLER = ["!", "/", "$"]
    SUPPORT_GROUP = "ShadowsHQ"
    SUPPORT_CHANNEL = "ShadowBotsHQ"
    VERSION = "VERSION"
    TIME_ZONE = 'Asia/Kolkata'
    BDB_URI = "mongodb+srv://ryumasgod:ryumasgod@cluster0.ojfkovp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    WORKERS = 8
    # CHROME_BIN = "/app/.apt/usr/bin/google-chrome"
    # CHROME_DRIVER = "/app/.chromedriver/bin/chromedriver"
