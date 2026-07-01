from datetime import datetime, timezone

import discord

from config import COLOR_DONE, COLOR_ERROR, COLOR_PANEL, COLOR_WARNING
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


def build_drop_embed(drop, participant_count: int, winners=None, image_filename: str | None = None) -> discord.Embed:
    status = drop["status"]
    ends_at = unix_ts(drop["ends_at"])
    winners = winners or []

    embed = discord.Embed(
        title=f"{emojis.PRIZE} {drop['prize']}",
        description=f"Anfitrion: <@{drop['creator_id']}>",
        color=status_color(status),
    )
    embed.add_field(name=f"{emojis.TICKET} Participantes", value=str(participant_count), inline=True)

    if status == "ended":
        if winners:
            field_name = f"{emojis.WINNER} Ganador" if len(winners) == 1 else f"{emojis.WINNER} Ganadores"
            winner_text = "\n".join(f"<@{row['user_id']}>" for row in winners)
            embed.add_field(name=field_name, value=winner_text[:1000], inline=True)
        else:
            embed.add_field(name="Resultado", value="Sin ganador", inline=True)
    elif status == "cancelled":
        embed.add_field(name="Resultado", value="Cancelado", inline=True)
    else:
        embed.add_field(name=f"{emojis.WINNER} Ganadores", value=str(drop["winner_count"]), inline=True)

    embed.add_field(name="Estado", value=status_label(status), inline=True)

    if status == "active":
        embed.add_field(name="Finaliza", value=f"<t:{ends_at}:R> - <t:{ends_at}:f>", inline=False)

    requirements = (drop["requirements_text"] or "").strip()
    if requirements:
        embed.add_field(name="Requisitos", value=requirements[:1000], inline=False)

    if image_filename:
        embed.set_image(url=f"attachment://{image_filename}")

    embed.set_footer(text=f"Drop #{drop['id']}")
    return embed


def build_participants_embed(
    drop,
    entries,
    page: int,
    total: int,
    per_page: int,
    notice: str | None = None,
    manager: bool = False,
) -> discord.Embed:
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
        embed.description = "No hay participantes activos para quitar."

    if notice:
        embed.add_field(name="Ultima accion", value=notice[:1000], inline=False)

    if not manager:
        embed.add_field(
            name="Permisos",
            value="Puedes ver la lista, pero solo los roles autorizados pueden quitar o bloquear participantes.",
            inline=False,
        )
    elif total == 0:
        embed.add_field(
            name="Acciones",
            value="Cuando haya participantes activos apareceran los menus para quitar o bloquear.",
            inline=False,
        )

    embed.set_footer(text=f"Pagina {page + 1}/{total_pages} | Total: {total}")
    return embed


def build_drop_logs_embed(rows, page: int, total: int, per_page: int, notice: str | None = None) -> discord.Embed:
    total_pages = max(1, (total + per_page - 1) // per_page)
    embed = discord.Embed(
        title=f"{emojis.DROPS} Logs de sorteos",
        color=COLOR_PANEL,
    )

    if rows:
        lines = []
        for row in rows:
            status = status_label(row["status"])
            winners = row["winner_ids"] or ""
            winner_text = ", ".join(f"<@{winner_id}>" for winner_id in winners.split(",") if winner_id)
            if not winner_text:
                winner_text = "Sin ganador"
            ended_at = row["ended_at"] or row["created_at"]
            timestamp = f"<t:{unix_ts(ended_at)}:R>" if ended_at else "Sin fecha"
            lines.append(
                f"**Drop #{row['id']}** - {row['prize']}\n"
                f"{status} | {row['participant_count']} participantes | {timestamp}\n"
                f"{emojis.WINNER} {winner_text}"
            )
        embed.description = "\n\n".join(lines)[:4000]
    else:
        embed.description = "No hay logs visibles de sorteos finalizados."

    if notice:
        embed.add_field(name="Ultima accion", value=notice[:1000], inline=False)

    embed.set_footer(text=f"Pagina {page + 1}/{total_pages} | Total: {total}")
    return embed


def build_winner_content(drop, winners) -> str | None:
    if not winners:
        return None

    mentions = ", ".join(f"<@{row['user_id']}>" for row in winners)
    if len(winners) == 1:
        return f"{emojis.WINNER} Felicidades {mentions}, ganaste **{drop['prize']}**!"

    return f"{emojis.WINNER} Felicidades {mentions}, ganaron **{drop['prize']}**!"


def build_reroll_content(drop, winners) -> str | None:
    if not winners:
        return None

    mentions = ", ".join(f"<@{row['user_id']}>" for row in winners)
    if len(winners) == 1:
        return f"{emojis.REROLL} Reroll de Drop #{drop['id']}: {mentions} gano **{drop['prize']}**!"

    return f"{emojis.REROLL} Reroll de Drop #{drop['id']}: {mentions} ganaron **{drop['prize']}**!"
