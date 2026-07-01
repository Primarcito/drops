import discord

import database as db
from embeds import build_drop_embed, build_result_text
from drops.views import DropPublicView


async def refresh_public_message(client: discord.Client, drop_id: int):
    drop = db.get_drop(drop_id)
    if not drop or not drop["message_id"]:
        return

    try:
        channel = client.get_channel(int(drop["channel_id"])) or await client.fetch_channel(int(drop["channel_id"]))
        message = await channel.fetch_message(int(drop["message_id"]))
    except (discord.HTTPException, ValueError, TypeError):
        return

    participant_count = db.count_entries(drop_id)
    winners = db.get_winners(drop_id)
    view = DropPublicView(drop_id) if drop["status"] == "active" else None
    await message.edit(embed=build_drop_embed(drop, participant_count, winners), view=view)


async def conclude_drop(client: discord.Client, drop_id: int, status: str = "ended"):
    drop = db.get_drop(drop_id)
    if not drop or drop["status"] != "active":
        return []

    winners = []
    if status == "ended":
        winners = db.draw_winners(drop_id, drop["winner_count"], reroll_index=0)
    db.mark_drop_status(drop_id, status)
    await refresh_public_message(client, drop_id)

    if status == "ended" and drop["channel_id"]:
        try:
            channel = client.get_channel(int(drop["channel_id"])) or await client.fetch_channel(int(drop["channel_id"]))
            await channel.send(build_result_text(db.get_drop(drop_id), winners))
        except (discord.HTTPException, ValueError, TypeError):
            pass

    return winners

