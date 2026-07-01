import asyncio
from datetime import datetime, timedelta, timezone

import discord

import database as db
from config import DROP_CHECK_INTERVAL_SECONDS, DROP_ENDING_SOON_SECONDS
from drops.service import conclude_drop, show_ending_soon_message


async def drop_watch_loop(client: discord.Client):
    await client.wait_until_ready()
    while not client.is_closed():
        ending_until = (datetime.now(timezone.utc) + timedelta(seconds=DROP_ENDING_SOON_SECONDS)).isoformat()
        for drop in db.get_ending_soon_drops(ending_until):
            try:
                await show_ending_soon_message(client, int(drop["id"]))
            except Exception as err:
                print(f"[DROPS] Error mostrando cierre de Drop #{drop['id']}: {err}")

        for drop in db.get_due_drops():
            try:
                await conclude_drop(client, int(drop["id"]), status="ended")
            except Exception as err:
                print(f"[DROPS] Error cerrando Drop #{drop['id']}: {err}")
        await asyncio.sleep(DROP_CHECK_INTERVAL_SECONDS)
