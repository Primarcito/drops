import io

import discord

import database as db
from embed_assets import image_file_for_drop, image_filename_for_drop
from embeds import build_drop_embed, build_winner_content
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
    file = image_file_for_drop(drop, winners) if drop["status"] != "active" else None
    image_filename = file.filename if file else image_filename_for_drop(drop, winners)
    edit_kwargs = dict(
        embed=build_drop_embed(drop, participant_count, winners, image_filename=image_filename),
        view=view,
    )
    if file:
        edit_kwargs["attachments"] = [file]
    await message.edit(**edit_kwargs)


async def update_public_drop_photo(
    client: discord.Client,
    drop_id: int,
    image_bytes: bytes,
    filename: str,
    actor_id=None,
):
    drop = db.get_drop(drop_id)
    if not drop or not drop["message_id"]:
        return False

    try:
        channel = client.get_channel(int(drop["channel_id"])) or await client.fetch_channel(int(drop["channel_id"]))
        message = await channel.fetch_message(int(drop["message_id"]))
    except (discord.HTTPException, ValueError, TypeError):
        return False

    winners = db.get_winners(drop_id)
    participant_count = db.count_entries(drop_id)
    view = DropPublicView(drop_id) if drop["status"] == "active" else None
    file = discord.File(io.BytesIO(image_bytes), filename=filename)
    await message.edit(
        embed=build_drop_embed(drop, participant_count, winners, image_filename=filename),
        view=view,
        attachments=[file],
    )
    db.set_drop_image(drop_id, filename, actor_id=actor_id)
    return True


async def conclude_drop(client: discord.Client, drop_id: int, status: str = "ended"):
    drop = db.get_drop(drop_id)
    if not drop or drop["status"] != "active":
        return []

    winners = []
    if status == "ended":
        winners = db.draw_winners(drop_id, drop["winner_count"], reroll_index=0)
    db.mark_drop_status(drop_id, status)
    await refresh_public_message(client, drop_id)

    if status == "ended" and winners and drop["channel_id"]:
        try:
            channel = client.get_channel(int(drop["channel_id"])) or await client.fetch_channel(int(drop["channel_id"]))
            finished_drop = db.get_drop(drop_id)
            content = build_winner_content(finished_drop, winners)
            if content:
                await channel.send(content)
        except (discord.HTTPException, ValueError, TypeError):
            pass

    return winners
