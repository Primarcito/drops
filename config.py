import os

from dotenv import load_dotenv


load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN", "")


def parse_id_list(value: str) -> list[int]:
    ids = []
    for raw_id in (value or "").replace(";", ",").split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        ids.append(int(raw_id))
    return ids


GUILD_IDS = parse_id_list(os.getenv("GUILD_IDS") or os.getenv("GUILD_ID", ""))

DATA_DIR = os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "."
DB_PATH = os.path.join(DATA_DIR, "drops.db")

COLOR_PANEL = 0x2F80ED
COLOR_SUCCESS = 0x27AE60
COLOR_WARNING = 0xF2C94C
COLOR_ERROR = 0xEB5757
COLOR_DONE = 0x9B51E0

DROP_CHECK_INTERVAL_SECONDS = 30
