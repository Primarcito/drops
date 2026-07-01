import discord

import database as db
from embed_assets import banner_file, banner_filename
from embeds import build_drop_embed, build_winner_content, build_winner_embed
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
    image_filename = banner_filename("active") if drop["status"] == "active" else None
    await message.edit(
        embed=build_drop_embed(drop, participant_count, winners, image_filename=image_filename),
        view=view,
    )


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
            finished_drop = db.get_drop(drop_id)
            kind = "winner" if winners else "ended"
            file = banner_file(kind)
            kwargs = {
                "embed": build_winner_embed(
                    finished_drop,
                    winners,
                    image_filename=file.filename if file else banner_filename(kind),
                )
            }
            content = build_winner_content(finished_drop, winners)
            if content:
                kwargs["content"] = content
            if file:
                kwargs["file"] = file
            await channel.send(**kwargs)
        except (discord.HTTPException, ValueError, TypeError):
            pass

    return winners
