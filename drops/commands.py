from datetime import datetime, timezone

import discord
from discord import app_commands

import database as db
from embed_assets import banner_file, banner_filename
from drops.admin_views import DropAdminPanelView, build_admin_panel_embed
from drops.timeparse import parse_duration
from drops.views import DropPublicView
from embeds import build_drop_embed
from permissions import can_manage_drops


sorteo_group = app_commands.Group(name="sorteo", description="Sistema de sorteos dinamicos")


async def send_private(interaction: discord.Interaction, message: str):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def require_manager(interaction: discord.Interaction) -> bool:
    if can_manage_drops(interaction):
        return True
    await send_private(interaction, "No tienes permiso para administrar Drops.")
    return False


def active_drop_or_error(drop_id: int):
    drop = db.get_drop(drop_id)
    if not drop:
        return None, "No encontre ese Drop."
    return drop, None


def normalize_requirements(text: str) -> str:
    value = (text or "").strip()
    if value.lower() in {"-", "no", "none", "ninguno", "ninguna", "sin requisitos"}:
        return ""
    return value


@sorteo_group.command(name="crear", description="Crea un nuevo sorteo en este canal")
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
    ganadores: app_commands.Range[int, 1, 25],
    requisitos: str = "",
):
    print(
        "[DROPS] /sorteo crear recibido: "
        f"guild_id={getattr(interaction.guild, 'id', None)} "
        f"channel_id={getattr(interaction.channel, 'id', None)} "
        f"user_id={getattr(interaction.user, 'id', None)}"
    )
    await interaction.response.defer(thinking=True)

    if not await require_manager(interaction):
        return
    if not interaction.guild or not interaction.channel:
        await interaction.followup.send("Este comando solo funciona dentro de un servidor.", ephemeral=True)
        return

    try:
        ends_at = datetime.now(timezone.utc) + parse_duration(duracion)
    except ValueError as err:
        await interaction.followup.send(str(err), ephemeral=True)
        return

    drop_id = db.create_drop(
        interaction.guild.id,
        interaction.channel.id,
        interaction.user.id,
        premio,
        ganadores,
        ends_at,
        normalize_requirements(requisitos),
    )
    drop = db.get_drop(drop_id)
    file = banner_file("active", drop=drop)
    embed = build_drop_embed(
        drop,
        participant_count=0,
        image_filename=file.filename if file else banner_filename("active", drop=drop),
    )
    if file:
        message = await interaction.followup.send(embed=embed, view=DropPublicView(drop_id), file=file, wait=True)
    else:
        message = await interaction.followup.send(embed=embed, view=DropPublicView(drop_id), wait=True)
    db.set_drop_message(drop_id, message.id)
    print(f"[DROPS] Sorteo creado: drop_id={drop_id} message_id={message.id} guild_id={interaction.guild.id}")


@sorteo_group.command(name="panel", description="Abre el panel privado de administracion de un sorteo")
@app_commands.describe(drop_id="ID del sorteo")
async def admin_panel(interaction: discord.Interaction, drop_id: int):
    print(
        "[DROPS] /sorteo panel recibido: "
        f"drop_id={drop_id} guild_id={getattr(interaction.guild, 'id', None)} "
        f"user_id={getattr(interaction.user, 'id', None)}"
    )
    await interaction.response.defer(ephemeral=True, thinking=True)

    if not await require_manager(interaction):
        return

    drop, error = active_drop_or_error(drop_id)
    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    await interaction.followup.send(
        embed=build_admin_panel_embed(drop_id),
        view=DropAdminPanelView(drop_id),
        ephemeral=True,
    )
