import asyncio
import traceback

import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import APPLICATION_ID, DISCORD_TOKEN, GUILD_ID
from drops.commands import drop_group
from drops.scheduler import drop_watch_loop
from drops.views import DropPublicView


intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=APPLICATION_ID or None,
)

COMMANDS_SYNCED = False
WATCH_LOOP_STARTED = False


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


bot.tree.on_error = on_app_command_error


@bot.event
async def on_ready():
    global COMMANDS_SYNCED, WATCH_LOOP_STARTED

    db.init_db()
    for drop in db.get_active_drops():
        bot.add_view(DropPublicView(int(drop["id"])))

    if not COMMANDS_SYNCED:
        bot.tree.add_command(drop_group)
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        COMMANDS_SYNCED = True
        print(f"[DROPS] Comandos sincronizados: {[command.name for command in synced]}")

    if not WATCH_LOOP_STARTED:
        asyncio.create_task(drop_watch_loop(bot))
        WATCH_LOOP_STARTED = True

    print(f"[DROPS] Bot listo: {bot.user}")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("Falta DISCORD_TOKEN en .env")
    bot.run(DISCORD_TOKEN)

