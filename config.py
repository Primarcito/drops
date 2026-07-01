import os

from dotenv import load_dotenv


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
APPLICATION_ID = int(os.getenv("APPLICATION_ID", "0") or 0)
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)

DATA_DIR = os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "."
DB_PATH = os.path.join(DATA_DIR, "drops.db")

COLOR_PANEL = 0x2F80ED
COLOR_SUCCESS = 0x27AE60
COLOR_WARNING = 0xF2C94C
COLOR_ERROR = 0xEB5757
COLOR_DONE = 0x9B51E0

DROP_CHECK_INTERVAL_SECONDS = 30

