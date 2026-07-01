import asyncio
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import APPLICATION_ID, DISCORD_TOKEN, GUILD_IDS
from drops.commands import sorteo_group
from drops.scheduler import drop_watch_loop
from drops.views import DropPublicView


intents = discord.Intents.default()
intents.members = True


SYNC_VERSION = "sorteo-setup-hook-v3"


class DropsBot(commands.Bot):
    async def setup_hook(self):
        db.init_db()
        for drop in db.get_active_drops():
            self.add_view(DropPublicView(int(drop["id"])))

        await sync_application_commands(self)
        asyncio.create_task(drop_watch_loop(self))


bot = DropsBot(
    command_prefix="!",
    intents=intents,
    application_id=APPLICATION_ID or None,
)


async def send_interaction_error(interaction: discord.Interaction, message: str):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    traceback.print_exception(type(original), original, original.__traceback__)
    await send_interaction_error(interaction, f"Ocurrio un error: `{original}`")


async def sync_application_commands(client: commands.Bot):
    print(f"[DROPS] Sync version: {SYNC_VERSION} | GUILD_IDS={GUILD_IDS or 'global'}")

    client.tree.clear_commands(guild=None)
    client.tree.add_command(sorteo_group)
    global_synced = await client.tree.sync()
    global_fetched = await client.tree.fetch_commands()

    if GUILD_IDS:
        synced_by_guild = {}
        for guild_id in GUILD_IDS:
            guild = discord.Object(id=guild_id)
            try:
                client.tree.clear_commands(guild=guild)
                client.tree.add_command(sorteo_group, guild=guild)
                synced = await client.tree.sync(guild=guild)
                fetched = await client.tree.fetch_commands(guild=guild)
                synced_by_guild[guild_id] = {
                    "synced": [command.name for command in synced],
                    "discord": [command.name for command in fetched],
                }
            except discord.HTTPException as err:
                synced_by_guild[guild_id] = {"error": f"{err.status}: {err.text}"}

        print(
            "[DROPS] Comandos de servidor sincronizados: "
            f"{synced_by_guild} | Globales: synced={len(global_synced)} "
            f"discord={[command.name for command in global_fetched]}"
        )
        return

    print(
        "[DROPS] Comandos globales sincronizados: "
        f"synced={[command.name for command in global_synced]} "
        f"discord={[command.name for command in global_fetched]}"
    )


bot.tree.on_error = on_app_command_error


@bot.event
async def on_ready():
    print(f"[DROPS] Bot listo: {bot.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("Falta TOKEN o DISCORD_TOKEN en las variables de entorno")
    bot.run(DISCORD_TOKEN)
