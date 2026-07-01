from pathlib import Path

import discord


ASSET_DIR = Path(__file__).resolve().parent / "assets" / "discord" / "embeds"

BANNERS = {
    "active": "drops-active.png",
    "winner": "drops-winner.png",
    "ended": "drops-ended.png",
}


def banner_filename(kind: str) -> str | None:
    filename = BANNERS.get(kind)
    if not filename:
        return None
    if not (ASSET_DIR / filename).exists():
        return None
    return filename


def banner_file(kind: str) -> discord.File | None:
    filename = banner_filename(kind)
    if not filename:
        return None
    return discord.File(ASSET_DIR / filename, filename=filename)

