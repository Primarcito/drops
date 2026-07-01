import asyncio

import discord

import database as db
from config import DROP_CHECK_INTERVAL_SECONDS
from drops.service import conclude_drop


async def drop_watch_loop(client: discord.Client):
    await client.wait_until_ready()
    while not client.is_closed():
        for drop in db.get_due_drops():
            try:
                await conclude_drop(client, int(drop["id"]), status="ended")
            except Exception as err:
                print(f"[DROPS] Error cerrando Drop #{drop['id']}: {err}")
        await asyncio.sleep(DROP_CHECK_INTERVAL_SECONDS)

