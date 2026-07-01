from pathlib import Path

import discord


ASSET_DIR = Path(__file__).resolve().parent / "assets" / "discord" / "embeds"

BANNERS = {
    "active": [
        "drops-active.png",
        "drops-active-alt.png",
        "drops-active-trophy.png",
        "drops-active-wheel.png",
    ],
    "winner": "drops-winner.png",
    "ended": "drops-ended.png",
}


def row_value(row, key: str, default=None):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def prize_image_filename(drop) -> str | None:
    filename = row_value(drop, "prize_image_filename")
    return filename or None


def banner_kind_for_drop(drop, winners=None) -> str | None:
    status = row_value(drop, "status")
    winners = winners or []
    if status == "active":
        return "active"
    if status == "ended":
        return "winner" if winners else "ended"
    if status == "cancelled":
        return "ended"
    return None


def banner_variant_index(drop, total: int) -> int:
    drop_id = row_value(drop, "id", 0) or 0
    try:
        return (int(drop_id) - 1) % max(1, int(total))
    except (TypeError, ValueError):
        return 0


def banner_filename(kind: str, drop=None) -> str | None:
    filenames = BANNERS.get(kind)
    if isinstance(filenames, (list, tuple)):
        if not filenames:
            return None
        filename = filenames[banner_variant_index(drop, len(filenames))]
    else:
        filename = filenames
    if not filename:
        return None
    if not (ASSET_DIR / filename).exists():
        return None
    return filename


def banner_file(kind: str, drop=None) -> discord.File | None:
    filename = banner_filename(kind, drop=drop)
    if not filename:
        return None
    return discord.File(ASSET_DIR / filename, filename=filename)


def image_filename_for_drop(drop, winners=None) -> str | None:
    custom_filename = prize_image_filename(drop)
    if custom_filename:
        return custom_filename
    return banner_filename(banner_kind_for_drop(drop, winners), drop=drop)


def image_file_for_drop(drop, winners=None) -> discord.File | None:
    if prize_image_filename(drop):
        return None
    return banner_file(banner_kind_for_drop(drop, winners), drop=drop)
