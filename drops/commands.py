from datetime import datetime, timezone

import discord
from discord import app_commands

import database as db
from drops.service import conclude_drop, refresh_public_message
from drops.timeparse import parse_duration
from drops.views import ParticipantsView, DropPublicView
from embeds import build_drop_embed
from permissions import can_manage_drops


drop_group = app_commands.Group(name="drops", description="Sistema de sorteos dinamicos")


async def require_manager(interaction: discord.Interaction) -> bool:
    if can_manage_drops(interaction):
        return True
    await interaction.response.send_message("No tienes permiso para administrar Drops.", ephemeral=True)
    return False


def active_drop_or_error(drop_id: int):
    drop = db.get_drop(drop_id)
    if not drop:
        return None, "No encontre ese Drop."
    return drop, None


@drop_group.command(name="crear", description="Crea un nuevo Drop en este canal")
@app_commands.describe(
    premio="Premio del sorteo",
    duracion="Duracion: 30m, 2h, 1d, 1h30m",
    ganadores="Cantidad de ganadores",
    requisitos="Reglas o requisitos visibles en el embed",
)
async def create_drop(
    interaction: discord.Interaction,
    premio: str,
    duracion: str,
    ganadores: app_commands.Range[int, 1, 25] = 1,
    requisitos: str = "",
):
    if not await require_manager(interaction):
        return
    if not interaction.guild or not interaction.channel:
        await interaction.response.send_message("Este comando solo funciona dentro de un servidor.", ephemeral=True)
        return

    try:
        ends_at = datetime.now(timezone.utc) + parse_duration(duracion)
    except ValueError as err:
        await interaction.response.send_message(str(err), ephemeral=True)
        return

    drop_id = db.create_drop(
        interaction.guild.id,
        interaction.channel.id,
        interaction.user.id,
        premio,
        ganadores,
        ends_at,
        requisitos,
    )
    drop = db.get_drop(drop_id)
    embed = build_drop_embed(drop, participant_count=0)
    await interaction.response.send_message(embed=embed, view=DropPublicView(drop_id))
    message = await interaction.original_response()
    db.set_drop_message(drop_id, message.id)


@drop_group.command(name="participantes", description="Muestra participantes activos de un Drop")
@app_commands.describe(drop_id="ID del Drop")
async def participants(interaction: discord.Interaction, drop_id: int):
    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return

    view = ParticipantsView(drop_id, page=0, manager=can_manage_drops(interaction))
    await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)


@drop_group.command(name="quitar", description="Quita un participante de un Drop")
@app_commands.describe(drop_id="ID del Drop", usuario="Usuario a quitar", motivo="Motivo visible solo en logs internos")
async def remove_participant(
    interaction: discord.Interaction,
    drop_id: int,
    usuario: discord.Member,
    motivo: str = "",
):
    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return

    removed = db.remove_entry(drop_id, usuario.id, actor_id=interaction.user.id, reason=motivo or "removed_by_staff")
    await refresh_public_message(interaction.client, drop_id)
    if removed:
        await interaction.response.send_message(f"{usuario.mention} fue quitado del Drop #{drop_id}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{usuario.mention} no estaba participando en ese Drop.", ephemeral=True)


@drop_group.command(name="bloquear", description="Quita y bloquea a un usuario para que no vuelva a entrar al Drop")
@app_commands.describe(drop_id="ID del Drop", usuario="Usuario a bloquear", motivo="Motivo visible solo en logs internos")
async def block_participant(
    interaction: discord.Interaction,
    drop_id: int,
    usuario: discord.Member,
    motivo: str = "",
):
    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return

    db.block_entry(
        drop_id,
        usuario.id,
        getattr(usuario, "display_name", usuario.name),
        actor_id=interaction.user.id,
        reason=motivo or "blocked_by_staff",
    )
    await refresh_public_message(interaction.client, drop_id)
    await interaction.response.send_message(f"{usuario.mention} fue bloqueado del Drop #{drop_id}.", ephemeral=True)


@drop_group.command(name="finalizar", description="Finaliza un Drop y elige ganador(es)")
@app_commands.describe(drop_id="ID del Drop")
async def finish_drop(interaction: discord.Interaction, drop_id: int):
    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return
    if drop["status"] != "active":
        await interaction.response.send_message("Ese Drop ya no esta activo.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    winners = await conclude_drop(interaction.client, drop_id, status="ended")
    if winners:
        await interaction.followup.send(f"Drop #{drop_id} finalizado con {len(winners)} ganador(es).", ephemeral=True)
    else:
        await interaction.followup.send(f"Drop #{drop_id} finalizado sin ganadores.", ephemeral=True)


@drop_group.command(name="cancelar", description="Cancela un Drop sin elegir ganadores")
@app_commands.describe(drop_id="ID del Drop")
async def cancel_drop(interaction: discord.Interaction, drop_id: int):
    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return
    if drop["status"] != "active":
        await interaction.response.send_message("Ese Drop ya no esta activo.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    await conclude_drop(interaction.client, drop_id, status="cancelled")
    await interaction.followup.send(f"Drop #{drop_id} cancelado.", ephemeral=True)


@drop_group.command(name="reroll", description="Vuelve a elegir ganador(es) de un Drop finalizado")
@app_commands.describe(drop_id="ID del Drop")
async def reroll_drop(interaction: discord.Interaction, drop_id: int):
    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return
    if drop["status"] != "ended":
        await interaction.response.send_message("Solo puedes hacer reroll de un Drop finalizado.", ephemeral=True)
        return

    previous_winners = db.get_winners(drop_id)
    exclude_ids = [row["user_id"] for row in previous_winners]
    next_index = db.latest_reroll_index(drop_id) + 1
    winners = db.draw_winners(drop_id, drop["winner_count"], reroll_index=next_index, exclude_user_ids=exclude_ids)
    await refresh_public_message(interaction.client, drop_id)

    if not winners:
        await interaction.response.send_message("No quedan participantes disponibles para reroll.", ephemeral=True)
        return

    mentions = ", ".join(f"<@{row['user_id']}>" for row in winners)
    await interaction.response.send_message(f"Reroll de Drop #{drop_id}: {mentions}")

