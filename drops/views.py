import math
import asyncio
from contextlib import suppress

import discord

import database as db
import emojis
from embed_assets import image_filename_for_drop
from embeds import build_drop_embed, build_participants_embed
from permissions import can_manage_drops


PARTICIPANTS_PER_PAGE = 10
BUTTON_NOTICE_DELETE_AFTER = 10
_BUTTON_NOTICE_MESSAGES = {}
_BUTTON_NOTICE_TASKS = {}
_PARTICIPANTS_MESSAGES = {}


def notice_key(interaction: discord.Interaction, drop_id: int):
    return (int(interaction.user.id), int(drop_id))


async def delete_button_notice_later(key, message):
    await asyncio.sleep(BUTTON_NOTICE_DELETE_AFTER)
    if _BUTTON_NOTICE_MESSAGES.get(key) is not message:
        return
    with suppress(discord.HTTPException, discord.NotFound):
        await message.delete()
    _BUTTON_NOTICE_MESSAGES.pop(key, None)
    _BUTTON_NOTICE_TASKS.pop(key, None)


def schedule_button_notice_delete(key, message):
    old_task = _BUTTON_NOTICE_TASKS.pop(key, None)
    if old_task:
        old_task.cancel()
    _BUTTON_NOTICE_TASKS[key] = asyncio.create_task(delete_button_notice_later(key, message))


async def send_button_notice(interaction: discord.Interaction, drop_id: int, message: str):
    key = notice_key(interaction, drop_id)
    previous = _BUTTON_NOTICE_MESSAGES.get(key)
    if previous:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        try:
            await previous.edit(content=message, embed=None, view=None)
            schedule_button_notice_delete(key, previous)
            return
        except (discord.HTTPException, discord.NotFound):
            _BUTTON_NOTICE_MESSAGES.pop(key, None)

    if not interaction.response.is_done():
        await interaction.response.send_message(message, ephemeral=True)
        notice = await interaction.original_response()
    else:
        notice = await interaction.followup.send(message, ephemeral=True, wait=True)

    _BUTTON_NOTICE_MESSAGES[key] = notice
    schedule_button_notice_delete(key, notice)


class DropPublicView(discord.ui.View):
    def __init__(self, drop_id: int):
        super().__init__(timeout=None)
        self.drop_id = int(drop_id)
        self.add_item(JoinDropButton(self.drop_id))
        self.add_item(LeaveDropButton(self.drop_id))
        self.add_item(ParticipantsButton(self.drop_id))


class JoinDropButton(discord.ui.Button):
    def __init__(self, drop_id: int):
        super().__init__(
            label="Entrar",
            style=discord.ButtonStyle.success,
            emoji=emojis.JOIN,
            custom_id=f"drops:join:{int(drop_id)}",
        )
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        result = db.add_entry(
            self.drop_id,
            interaction.user.id,
            getattr(interaction.user, "display_name", interaction.user.name),
        )

        messages = {
            "joined": "Listo, entraste al Drop.",
            "already": "Ya estas participando en este Drop.",
            "blocked": "No puedes entrar a este Drop.",
            "closed": "Este Drop ya no esta activo.",
        }

        await send_button_notice(interaction, self.drop_id, messages.get(result, "No pude agregarte."))
        await refresh_source_message(interaction, self.drop_id)


class LeaveDropButton(discord.ui.Button):
    def __init__(self, drop_id: int):
        super().__init__(
            label="Salir",
            style=discord.ButtonStyle.secondary,
            emoji=emojis.BLOCKED,
            custom_id=f"drops:leave:{int(drop_id)}",
        )
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        removed = db.remove_entry(self.drop_id, interaction.user.id, actor_id=interaction.user.id, reason="self_leave")
        text = "Saliste del Drop." if removed else "No estabas participando en este Drop."
        await send_button_notice(interaction, self.drop_id, text)
        await refresh_source_message(interaction, self.drop_id)


class ParticipantsButton(discord.ui.Button):
    def __init__(self, drop_id: int):
        super().__init__(
            label="Participantes",
            style=discord.ButtonStyle.primary,
            emoji=emojis.TICKET,
            custom_id=f"drops:participants:{int(drop_id)}",
        )
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        drop = db.get_drop(self.drop_id)
        if not drop:
            await interaction.response.send_message("No encontre ese Drop.", ephemeral=True)
            return
        view = ParticipantsView(self.drop_id, page=0, manager=can_manage_drops(interaction))
        key = notice_key(interaction, self.drop_id)
        previous = _PARTICIPANTS_MESSAGES.get(key)
        if previous:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            try:
                await previous.edit(embed=view.embed(), view=view, content=None)
                return
            except (discord.HTTPException, discord.NotFound):
                _PARTICIPANTS_MESSAGES.pop(key, None)

        if not interaction.response.is_done():
            await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)
            message = await interaction.original_response()
        else:
            message = await interaction.followup.send(embed=view.embed(), view=view, ephemeral=True, wait=True)
        _PARTICIPANTS_MESSAGES[key] = message


class ParticipantsView(discord.ui.View):
    def __init__(self, drop_id: int, page: int = 0, manager: bool = False, return_to_panel: bool = False):
        super().__init__(timeout=180)
        self.drop_id = int(drop_id)
        self.page = int(page)
        self.manager = bool(manager)
        self.return_to_panel = bool(return_to_panel)
        self.notice = None
        self.sync_children()

    def total(self) -> int:
        return db.count_entries(self.drop_id)

    def total_pages(self) -> int:
        return max(1, math.ceil(self.total() / PARTICIPANTS_PER_PAGE))

    def entries(self):
        return db.list_entries(
            self.drop_id,
            limit=PARTICIPANTS_PER_PAGE,
            offset=self.page * PARTICIPANTS_PER_PAGE,
        )

    def embed(self, notice: str | None = None):
        if notice is not None:
            self.notice = notice
        drop = db.get_drop(self.drop_id)
        return build_participants_embed(
            drop,
            self.entries(),
            self.page,
            self.total(),
            PARTICIPANTS_PER_PAGE,
            notice=self.notice,
        )

    def sync_children(self):
        self.clear_items()
        if self.manager:
            entries = self.entries()
            if entries:
                self.add_item(RemoveParticipantSelect(self.drop_id, entries))
                self.add_item(BlockParticipantSelect(self.drop_id, entries))
        self.add_item(PreviousPageButton())
        self.add_item(NextPageButton())
        if self.return_to_panel:
            self.add_item(BackToPanelButton(self.drop_id))
        self.update_button_states()

    def update_button_states(self):
        total_pages = self.total_pages()
        self.page = min(max(0, self.page), total_pages - 1)
        for item in self.children:
            if isinstance(item, PreviousPageButton):
                item.disabled = self.page <= 0
            elif isinstance(item, NextPageButton):
                item.disabled = self.page >= total_pages - 1

    async def refresh(self, interaction: discord.Interaction, notice: str | None = None):
        self.sync_children()
        await interaction.response.edit_message(embed=self.embed(notice=notice), view=self)


class PreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Anterior", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.page -= 1
        await self.view.refresh(interaction)


class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Siguiente", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.page += 1
        await self.view.refresh(interaction)


class BackToPanelButton(discord.ui.Button):
    def __init__(self, drop_id: int):
        super().__init__(label="Panel", style=discord.ButtonStyle.secondary, emoji=emojis.DROPS)
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        from drops.admin_views import DropAdminPanelView, build_admin_panel_embed

        view = DropAdminPanelView(self.drop_id)
        await interaction.response.edit_message(
            embed=build_admin_panel_embed(self.drop_id, notice="Volviste al panel."),
            view=view,
        )


class RemoveParticipantSelect(discord.ui.Select):
    def __init__(self, drop_id: int, entries):
        options = [
            discord.SelectOption(
                label=str(row["username"])[:100],
                value=str(row["user_id"]),
                description=f"ID: {row['user_id']}"[:100],
            )
            for row in entries[:25]
        ]
        super().__init__(
            placeholder="Quitar participante de esta pagina",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        if not can_manage_drops(interaction):
            await interaction.response.send_message("No tienes permiso para quitar participantes.", ephemeral=True)
            return

        user_id = self.values[0]
        removed = db.remove_entry(self.drop_id, user_id, actor_id=interaction.user.id, reason="removed_from_panel")
        await refresh_public_from_client(interaction.client, self.drop_id)

        if not removed:
            await self.view.refresh(interaction, notice="Ese usuario ya no estaba participando.")
            return

        await self.view.refresh(interaction, notice="Participante quitado.")


class BlockParticipantSelect(discord.ui.Select):
    def __init__(self, drop_id: int, entries):
        self.usernames = {str(row["user_id"]): str(row["username"]) for row in entries}
        options = [
            discord.SelectOption(
                label=str(row["username"])[:100],
                value=str(row["user_id"]),
                description=f"ID: {row['user_id']}"[:100],
            )
            for row in entries[:25]
        ]
        super().__init__(
            placeholder="Bloquear participante de esta pagina",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.drop_id = int(drop_id)

    async def callback(self, interaction: discord.Interaction):
        if not can_manage_drops(interaction):
            await interaction.response.send_message("No tienes permiso para bloquear participantes.", ephemeral=True)
            return

        user_id = self.values[0]
        db.block_entry(
            self.drop_id,
            user_id,
            self.usernames.get(user_id, user_id),
            actor_id=interaction.user.id,
            reason="blocked_from_panel",
        )
        await refresh_public_from_client(interaction.client, self.drop_id)
        await self.view.refresh(interaction, notice="Participante bloqueado.")


async def refresh_source_message(interaction: discord.Interaction, drop_id: int):
    drop = db.get_drop(drop_id)
    if not drop:
        return
    participant_count = db.count_entries(drop_id)
    winners = db.get_winners(drop_id)
    try:
        await interaction.message.edit(
            embed=build_drop_embed(
                drop,
                participant_count,
                winners,
                image_filename=image_filename_for_drop(drop, winners),
            ),
            view=DropPublicView(drop_id) if drop["status"] == "active" else None,
        )
    except discord.HTTPException:
        pass


async def refresh_public_from_client(client: discord.Client, drop_id: int):
    drop = db.get_drop(drop_id)
    if not drop or not drop["message_id"]:
        return
    try:
        channel = client.get_channel(int(drop["channel_id"])) or await client.fetch_channel(int(drop["channel_id"]))
        message = await channel.fetch_message(int(drop["message_id"]))
        participant_count = db.count_entries(drop_id)
        winners = db.get_winners(drop_id)
        await message.edit(
            embed=build_drop_embed(
                drop,
                participant_count,
                winners,
                image_filename=image_filename_for_drop(drop, winners),
            ),
            view=DropPublicView(drop_id) if drop["status"] == "active" else None,
        )
    except (discord.HTTPException, ValueError, TypeError):
        pass
