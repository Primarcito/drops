import math

import discord

import database as db
import emojis
from drops.ephemeral import upsert_ephemeral
from embeds import build_drop_logs_embed
from permissions import can_use_drop_admin_panel


LOGS_PER_PAGE = 5


class DropLogsView(discord.ui.View):
    def __init__(self, guild_id, page: int = 0):
        super().__init__(timeout=300)
        self.guild_id = str(guild_id)
        self.page = int(page)
        self.notice = None
        self.sync_children()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if can_use_drop_admin_panel(interaction):
            return True
        await upsert_ephemeral(
            interaction,
            scope="drop:logs",
            content="No tienes permiso para ver los logs de sorteos.",
        )
        return False

    def total(self) -> int:
        return db.count_drop_history(self.guild_id)

    def total_pages(self) -> int:
        return max(1, math.ceil(self.total() / LOGS_PER_PAGE))

    def rows(self):
        return db.list_drop_history(
            self.guild_id,
            limit=LOGS_PER_PAGE,
            offset=self.page * LOGS_PER_PAGE,
        )

    def embed(self, notice: str | None = None):
        if notice is not None:
            self.notice = notice
        return build_drop_logs_embed(
            self.rows(),
            self.page,
            self.total(),
            LOGS_PER_PAGE,
            notice=self.notice,
        )

    def sync_children(self):
        self.clear_items()
        self.add_item(LogsPreviousPageButton())
        self.add_item(LogsNextPageButton())
        self.add_item(ClearLogsButton())
        self.update_button_states()

    def update_button_states(self):
        total_pages = self.total_pages()
        self.page = min(max(0, self.page), total_pages - 1)
        for item in self.children:
            if isinstance(item, LogsPreviousPageButton):
                item.disabled = self.page <= 0
            elif isinstance(item, LogsNextPageButton):
                item.disabled = self.page >= total_pages - 1
            elif isinstance(item, ClearLogsButton):
                item.disabled = self.total() <= 0

    async def refresh(self, interaction: discord.Interaction, notice: str | None = None):
        self.sync_children()
        await interaction.response.edit_message(embed=self.embed(notice=notice), view=self)


class LogsPreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Anterior", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.page -= 1
        await self.view.refresh(interaction)


class LogsNextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Siguiente", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        self.view.page += 1
        await self.view.refresh(interaction)


class ClearLogsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Limpiar logs", style=discord.ButtonStyle.danger, emoji=emojis.BLOCKED)

    async def callback(self, interaction: discord.Interaction):
        cleared = db.clear_drop_history(self.view.guild_id)
        self.view.page = 0
        await self.view.refresh(interaction, notice=f"Logs limpiados: {cleared}. El contador de Drops no se reinicia.")
