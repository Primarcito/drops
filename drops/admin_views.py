import discord

import database as db
import emojis
from drops.ephemeral import upsert_ephemeral
from drops.image_validation import validate_drop_image
from drops.service import conclude_drop, reroll_drop
from drops.service import update_public_drop_photo
from drops.views import ParticipantsView
from permissions import can_manage_drop_participants, can_use_drop_admin_panel


def build_admin_panel_embed(drop_id: int, notice: str | None = None) -> discord.Embed:
    drop = db.get_drop(drop_id)
    if not drop:
        embed = discord.Embed(
            title="Drop no encontrado",
            description=f"No encontre el Drop #{drop_id}.",
            color=0xEB5757,
        )
        if notice:
            embed.add_field(name="Ultima accion", value=notice[:1000], inline=False)
        return embed

    participants = db.count_entries(drop_id)
    winners = db.get_winners(drop_id)
    status = {
        "active": f"{emojis.DROPS} Activo",
        "ended": f"{emojis.WINNER} Finalizado",
        "cancelled": f"{emojis.BLOCKED} Cancelado",
    }.get(drop["status"], drop["status"])

    embed = discord.Embed(
        title=f"Panel Drop #{drop['id']}",
        description=f"{emojis.PRIZE} **{drop['prize']}**",
        color=0x2F80ED,
    )
    embed.add_field(name=f"{emojis.TICKET} Participantes", value=str(participants), inline=True)
    embed.add_field(name=f"{emojis.WINNER} Sortea", value=str(drop["winner_count"]), inline=True)
    embed.add_field(name="Estado", value=status, inline=True)
    if winners:
        winner_text = "\n".join(f"<@{row['user_id']}>" for row in winners[-10:])
        embed.add_field(name="Ganadores registrados", value=winner_text[:1000], inline=False)
    if notice:
        embed.add_field(name="Ultima accion", value=notice[:1000], inline=False)
    embed.set_footer(text="Panel privado de administracion")
    return embed


class DropAdminPanelView(discord.ui.View):
    def __init__(self, drop_id: int):
        super().__init__(timeout=300)
        self.drop_id = int(drop_id)
        self.sync_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if can_use_drop_admin_panel(interaction):
            return True
        await upsert_ephemeral(
            interaction,
            scope=f"drop:{self.drop_id}:panel",
            content="No tienes permiso para administrar Drops.",
        )
        return False

    def sync_buttons(self):
        drop = db.get_drop(self.drop_id)
        status = drop["status"] if drop else None
        for child in self.children:
            if getattr(child, "label", None) == "Finalizar":
                child.disabled = status != "active"
            elif getattr(child, "label", None) == "Cancelar":
                child.disabled = status != "active"
            elif getattr(child, "label", None) == "Reroll":
                child.disabled = status != "ended"

    async def refresh_panel(self, interaction: discord.Interaction, notice: str | None = None):
        self.sync_buttons()
        embed = build_admin_panel_embed(self.drop_id, notice=notice)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Participantes", style=discord.ButtonStyle.primary, emoji=emojis.TICKET, row=0)
    async def participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ParticipantsView(
            self.drop_id,
            page=0,
            manager=can_manage_drop_participants(interaction),
            return_to_panel=True,
        )
        await interaction.response.edit_message(embed=view.embed(notice="Vista de participantes abierta."), view=view)

    @discord.ui.button(label="Finalizar", style=discord.ButtonStyle.success, emoji=emojis.WINNER, row=0)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        winners = await conclude_drop(interaction.client, self.drop_id, status="ended")
        if winners:
            await self.refresh_panel(interaction, notice=f"Drop #{self.drop_id} finalizado.")
        else:
            await self.refresh_panel(interaction, notice=f"Drop #{self.drop_id} finalizado sin ganadores.")

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji=emojis.BLOCKED, row=0)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await conclude_drop(interaction.client, self.drop_id, status="cancelled")
        await self.refresh_panel(interaction, notice=f"Drop #{self.drop_id} cancelado.")

    @discord.ui.button(label="Foto", style=discord.ButtonStyle.secondary, emoji=emojis.PRIZE, row=1)
    async def photo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DropPhotoModal(self.drop_id))

    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.secondary, emoji=emojis.REROLL, row=1)
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        _, notice = await reroll_drop(interaction.client, self.drop_id)
        await self.refresh_panel(interaction, notice=notice)


class DropPhotoModal(discord.ui.Modal):
    def __init__(self, drop_id: int):
        super().__init__(title=f"Foto Drop #{drop_id}")
        self.drop_id = int(drop_id)
        self.upload = discord.ui.FileUpload(required=True, min_values=1, max_values=1)
        self.add_item(
            discord.ui.Label(
                text="Foto del premio",
                description="PNG, JPG, WEBP o GIF. Max 10 MB.",
                component=self.upload,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        attachments = self.upload.values
        if not attachments:
            await upsert_ephemeral(
                interaction,
                scope=f"drop:{self.drop_id}:photo",
                content="Sube una imagen para actualizar la foto.",
            )
            return

        attachment = attachments[0]
        ok, extension, image_error = validate_drop_image(attachment)
        if not ok:
            await upsert_ephemeral(interaction, scope=f"drop:{self.drop_id}:photo", content=image_error)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            image_bytes = await attachment.read()
            filename = f"drops-premio-{self.drop_id}.{extension}"
            updated = await update_public_drop_photo(
                interaction.client,
                self.drop_id,
                image_bytes,
                filename,
                actor_id=interaction.user.id,
            )
        except discord.HTTPException as err:
            await upsert_ephemeral(
                interaction,
                scope=f"drop:{self.drop_id}:photo",
                content=f"No pude subir esa imagen: `{err}`",
            )
            return

        if not updated:
            await upsert_ephemeral(
                interaction,
                scope=f"drop:{self.drop_id}:photo",
                content="No pude encontrar el mensaje publico de ese Drop.",
            )
            return

        await upsert_ephemeral(
            interaction,
            scope=f"drop:{self.drop_id}:photo",
            content=f"Foto actualizada para Drop #{self.drop_id}.",
        )
