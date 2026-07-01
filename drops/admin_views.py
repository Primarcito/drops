import discord

import database as db
import emojis
from drops.image_validation import validate_drop_image
from drops.service import refresh_public_message, conclude_drop
from drops.service import update_public_drop_photo
from drops.views import ParticipantsView
from embeds import build_reroll_content
from permissions import can_manage_drop_participants, can_manage_drops


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
        if can_manage_drops(interaction):
            return True
        await interaction.response.send_message("No tienes permiso para administrar Drops.", ephemeral=True)
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
        drop = db.get_drop(self.drop_id)
        if not drop or drop["status"] != "ended":
            await self.refresh_panel(interaction, notice="Solo puedes hacer reroll de un Drop finalizado.")
            return

        await interaction.response.defer()
        previous_winners = db.get_winners(self.drop_id)
        exclude_ids = [row["user_id"] for row in previous_winners]
        next_index = db.latest_reroll_index(self.drop_id) + 1
        winners = db.draw_winners(
            self.drop_id,
            drop["winner_count"],
            reroll_index=next_index,
            exclude_user_ids=exclude_ids,
        )
        await refresh_public_message(interaction.client, self.drop_id)

        content = build_reroll_content(drop, winners)
        if content:
            try:
                channel = interaction.client.get_channel(int(drop["channel_id"])) or await interaction.client.fetch_channel(int(drop["channel_id"]))
                await channel.send(content)
            except (discord.HTTPException, ValueError, TypeError):
                pass
            await self.refresh_panel(interaction, notice="Reroll publicado.")
        else:
            await self.refresh_panel(interaction, notice="No quedan participantes disponibles para reroll.")


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
            await interaction.response.send_message("Sube una imagen para actualizar la foto.", ephemeral=True)
            return

        attachment = attachments[0]
        ok, extension, image_error = validate_drop_image(attachment)
        if not ok:
            await interaction.response.send_message(image_error, ephemeral=True)
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
            await interaction.followup.send(f"No pude subir esa imagen: `{err}`", ephemeral=True)
            return

        if not updated:
            await interaction.followup.send("No pude encontrar el mensaje publico de ese Drop.", ephemeral=True)
            return

        await interaction.followup.send(f"Foto actualizada para Drop #{self.drop_id}.", ephemeral=True)
