import os


DEFAULT_EMOJI_IDS = {
    "drops_blocked": "1521696873784803499",
    "drops_coin": "1521696875412197486",
    "drops_drops": "1521696876926210170",
    "drops_join": "1521696878612185128",
    "drops_prize": "1521696880189505606",
    "drops_reroll": "1521696881930010685",
    "drops_ticket": "1521696883620188374",
    "drops_winner": "1521696885923123210",
}


def custom_emoji(name: str, fallback: str) -> str:
    emoji_id = os.getenv(f"EMOJI_{name.upper()}_ID") or DEFAULT_EMOJI_IDS.get(name)
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
