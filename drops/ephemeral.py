import asyncio
from contextlib import suppress

import discord


_EPHEMERAL_MESSAGES = {}
_EPHEMERAL_DELETE_TASKS = {}


def ephemeral_key(interaction: discord.Interaction, scope: str):
    guild_id = getattr(interaction.guild, "id", None)
    channel_id = getattr(interaction.channel, "id", None)
    return (int(interaction.user.id), str(guild_id), str(channel_id))


async def _delete_later(key, message, delay: int):
    await asyncio.sleep(delay)
    if _EPHEMERAL_MESSAGES.get(key) is not message:
        return
    with suppress(discord.HTTPException, discord.NotFound):
        await message.delete()
    _EPHEMERAL_MESSAGES.pop(key, None)
    _EPHEMERAL_DELETE_TASKS.pop(key, None)


def _schedule_delete(key, message, delay: int | None):
    old_task = _EPHEMERAL_DELETE_TASKS.pop(key, None)
    if old_task:
        old_task.cancel()
    if delay:
        _EPHEMERAL_DELETE_TASKS[key] = asyncio.create_task(_delete_later(key, message, delay))


async def _acknowledge_without_new_message(interaction: discord.Interaction):
    if interaction.response.is_done():
        return
    with suppress(discord.HTTPException, discord.InteractionResponded):
        await interaction.response.defer(ephemeral=True)


async def _delete_original_response(interaction: discord.Interaction):
    with suppress(discord.HTTPException, discord.NotFound):
        await interaction.delete_original_response()


def _can_use_original_ephemeral_response(interaction: discord.Interaction) -> bool:
    return interaction.type in {
        discord.InteractionType.application_command,
        discord.InteractionType.modal_submit,
    }


def _is_component_interaction(interaction: discord.Interaction) -> bool:
    return interaction.type == discord.InteractionType.component


async def _forget_previous(key, previous):
    old_task = _EPHEMERAL_DELETE_TASKS.pop(key, None)
    if old_task:
        old_task.cancel()
    _EPHEMERAL_MESSAGES.pop(key, None)
    if previous:
        with suppress(discord.HTTPException, discord.NotFound):
            await previous.delete()


async def upsert_ephemeral(
    interaction: discord.Interaction,
    *,
    scope: str,
    content: str | None = None,
    embed: discord.Embed | None = None,
    view: discord.ui.View | None = None,
    delete_after: int | None = None,
    prefer_current_response: bool = False,
):
    key = ephemeral_key(interaction, scope)
    previous = _EPHEMERAL_MESSAGES.get(key)

    if prefer_current_response or _is_component_interaction(interaction):
        await _forget_previous(key, previous)
        previous = None

    if previous:
        already_acknowledged = interaction.response.is_done()
        if not already_acknowledged:
            await _acknowledge_without_new_message(interaction)
        try:
            await previous.edit(content=content, embed=embed, view=view)
            _schedule_delete(key, previous, delete_after)
            if already_acknowledged and _can_use_original_ephemeral_response(interaction):
                await _delete_original_response(interaction)
            return previous
        except (discord.HTTPException, discord.NotFound):
            _EPHEMERAL_MESSAGES.pop(key, None)

    if not interaction.response.is_done():
        await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=True)
        message = await interaction.original_response()
    elif _can_use_original_ephemeral_response(interaction):
        try:
            message = await interaction.edit_original_response(content=content, embed=embed, view=view)
        except (discord.HTTPException, discord.NotFound):
            message = await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=True,
                wait=True,
            )
    else:
        message = await interaction.followup.send(
            content=content,
            embed=embed,
            view=view,
            ephemeral=True,
            wait=True,
        )

    _EPHEMERAL_MESSAGES[key] = message
    _schedule_delete(key, message, delete_after)
    return message
