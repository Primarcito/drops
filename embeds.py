from datetime import datetime, timezone

import discord

from config import COLOR_DONE, COLOR_ERROR, COLOR_PANEL, COLOR_SUCCESS, COLOR_WARNING
import emojis


def unix_ts(iso_text: str) -> int:
    dt = datetime.fromisoformat(iso_text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def status_label(status: str) -> str:
    return {
        "active": f"{emojis.DROPS} Activo",
        "ended": f"{emojis.WINNER} Finalizado",
        "cancelled": f"{emojis.BLOCKED} Cancelado",
    }.get(status, status)


def status_color(status: str) -> int:
    return {
        "active": COLOR_PANEL,
        "ended": COLOR_DONE,
        "cancelled": COLOR_ERROR,
    }.get(status, COLOR_WARNING)


def build_drop_embed(drop, participant_count: int, winners=None) -> discord.Embed:
    status = drop["status"]
    ends_at = unix_ts(drop["ends_at"])
    winners = winners or []

    embed = discord.Embed(
        title=f"{emojis.PRIZE} {drop['prize']}",
        description=f"Anfitrion: <@{drop['creator_id']}>",
        color=status_color(status),
    )
    embed.add_field(name=f"{emojis.TICKET} Participantes", value=str(participant_count), inline=True)
    embed.add_field(name=f"{emojis.WINNER} Ganadores", value=str(drop["winner_count"]), inline=True)
    embed.add_field(name="Estado", value=status_label(status), inline=True)

    if status == "active":
        embed.add_field(name="Finaliza", value=f"<t:{ends_at}:R> - <t:{ends_at}:f>", inline=False)

    requirements = (drop["requirements_text"] or "").strip()
    if requirements:
        embed.add_field(name="Requisitos", value=requirements[:1000], inline=False)

    if winners:
        winner_text = "\n".join(f"{emojis.WINNER} <@{row['user_id']}>" for row in winners)
        embed.add_field(name=f"{emojis.WINNER} Ganador(es)", value=winner_text[:1000], inline=False)

    embed.set_footer(text=f"Drop #{drop['id']}")
    return embed


def build_participants_embed(drop, entries, page: int, total: int, per_page: int) -> discord.Embed:
    total_pages = max(1, (total + per_page - 1) // per_page)
    embed = discord.Embed(
        title=f"{emojis.TICKET} Participantes de Drop #{drop['id']}",
        color=COLOR_PANEL,
    )
    if entries:
        start = page * per_page + 1
        lines = [
            f"`{index}.` <@{row['user_id']}> - `{row['username']}`"
            for index, row in enumerate(entries, start=start)
        ]
        embed.description = "\n".join(lines)
    else:
        embed.description = "No hay participantes activos."

    embed.set_footer(text=f"Pagina {page + 1}/{total_pages} | Total: {total}")
    return embed


def build_result_text(drop, winners) -> str:
    if winners:
        mentions = ", ".join(f"<@{row['user_id']}>" for row in winners)
        return f"{emojis.WINNER} Drop #{drop['id']} finalizado. Ganador(es): {mentions}"
    return f"{emojis.BLOCKED} Drop #{drop['id']} finalizado sin participantes suficientes."


def build_winner_embed(drop, winners) -> discord.Embed:
    if winners:
        description = "\n".join(f"{emojis.WINNER} <@{row['user_id']}>" for row in winners)
    else:
        description = f"{emojis.BLOCKED} No hubo participantes suficientes."

    embed = discord.Embed(
        title=f"{emojis.PRIZE} {drop['prize']} - Sorteo finalizado",
        description=description,
        color=COLOR_SUCCESS if winners else COLOR_WARNING,
    )
    embed.set_footer(text=f"Drop #{drop['id']}")
    return embed
