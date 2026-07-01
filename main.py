import asyncio
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import DISCORD_TOKEN, GUILD_IDS
from drops.commands import sorteo_group
from drops.ephemeral import upsert_ephemeral
from drops.scheduler import drop_watch_loop
from drops.views import DropPublicView


intents = discord.Intents.default()


SYNC_VERSION = "sorteo-multi-guild-copy-v6"


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
)


async def send_interaction_error(interaction: discord.Interaction, message: str):
    try:
        await upsert_ephemeral(interaction, scope="global:error", content=message)
    except discord.HTTPException as err:
        print(f"[DROPS] No pude responder error de interaccion: {err}")


async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    print(
        "[DROPS] Error en comando: "
        f"command={getattr(interaction.command, 'qualified_name', None)} "
        f"guild_id={getattr(interaction.guild, 'id', None)} "
        f"user_id={getattr(interaction.user, 'id', None)}"
    )
    traceback.print_exception(type(original), original, original.__traceback__)
    await send_interaction_error(interaction, f"Ocurrio un error: `{original}`")


async def sync_application_commands(client: commands.Bot):
    print(
        f"[DROPS] Sync version: {SYNC_VERSION} | "
        f"application_id={client.application_id} | GUILD_IDS={GUILD_IDS or 'global'}"
    )

    client.tree.clear_commands(guild=None)
    client.tree.add_command(sorteo_group)

    if GUILD_IDS:
        global_synced = await client.tree.sync()
        global_fetched = await client.tree.fetch_commands()

        synced_by_guild = {}
        for guild_id in GUILD_IDS:
            guild = discord.Object(id=guild_id)
            try:
                client.tree.clear_commands(guild=guild)
                client.tree.copy_global_to(guild=guild)
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
            f"{synced_by_guild} | Globales: synced={[command.name for command in global_synced]} "
            f"discord={[command.name for command in global_fetched]} | "
            f"local_global={[command.name for command in client.tree.get_commands()]}"
        )
        return

    global_synced = await client.tree.sync()
    global_fetched = await client.tree.fetch_commands()
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
