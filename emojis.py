import os


def custom_emoji(name: str, fallback: str) -> str:
    emoji_id = os.getenv(f"EMOJI_{name.upper()}_ID")
    if emoji_id:
        return f"<:{name}:{emoji_id}>"
    return fallback


DROPS = custom_emoji("drops_drops", "\N{WRAPPED PRESENT}")
PRIZE = custom_emoji("drops_prize", "\N{WRAPPED PRESENT}")
TICKET = custom_emoji("drops_ticket", "\N{ADMISSION TICKETS}")
COIN = custom_emoji("drops_coin", "\N{COIN}")
WINNER = custom_emoji("drops_winner", "\N{GLOWING STAR}")
REROLL = custom_emoji("drops_reroll", "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}")
JOIN = custom_emoji("drops_join", "\N{WHITE HEAVY CHECK MARK}")
BLOCKED = custom_emoji("drops_blocked", "\N{NO ENTRY SIGN}")

